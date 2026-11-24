// RAD IDE - native WinForms runtime for published C# / PowerShell programs (no Python, no GUI Bridge).
// Compiled into the program by radide/deploy/native/dotnet_winforms.py. It keeps the API of the GUI Bridge
// client (Rad.cs): Set/Get/Call/MsgBox/InputBox/Show/Hide/End/radcall, RadControl (lblOut.Text = "Hi"),
// RadEvent (e.X, e.KeyCode ...), but the forms are real WinForms forms generated from the .form files
// (RadForm_<Name>.InitializeComponent) and the properties are read/written on the controls directly.
// Builds against .NET Framework 4.x (csc) and .NET 8+ (SDK) - keep it to APIs both have.
#nullable disable
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using Timer = System.Windows.Forms.Timer;

/// <summary>Arguments of a GUI event (mouse / key data when the event has them).</summary>
public class RadEvent
{
    public string Sender = "";      // control or form name
    public string Name = "";        // event name (Click, TextChanged, ...)
    public string Args = "";        // raw argument text (as the GUI Bridge sends it)
    public int X, Y, Button, KeyCode, Delta;
    public string KeyChar = "";
    /// <summary>FormClosing / -ing events of library controls (TabClosing ...): set true to cancel.</summary>
    public bool Cancel;
    /// <summary>Item-level events of library controls (ribbon / side bar / status bar items, tabs, nodes, grid
    /// buttons): the item's name and index. Args = "name index" ("row col" for grid cells), as the radforms controls send.</summary>
    public string ItemName = "";
    public int Index = -1;

    public static RadEvent Parse(string sender, string name, string args)
    {
        var e = new RadEvent { Sender = sender, Name = name, Args = args ?? "" };
        var p = e.Args.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        Func<int, int> I = i => { int v; return i < p.Length && int.TryParse(p[i], NumberStyles.Integer, CultureInfo.InvariantCulture, out v) ? v : 0; };
        e.X = I(0); e.Y = I(1); e.Button = I(2); e.KeyCode = I(3);
        e.KeyChar = p.Length > 4 ? p[4] : "";
        return e;
    }

    public string MakeArgs()
    {
        Args = (X + " " + Y + " " + Button + " " + KeyCode + " " + KeyChar).Trim();
        return Args;
    }
}

/// <summary>A control (or form) on a RAD IDE form. Property and method names are VB-style.</summary>
public class RadControl
{
    public string Path { get; private set; }
    public RadControl(string path) { Path = path; }

    public string this[string prop] { get { return Rad.Get(Path, prop); } set { Rad.Set(Path, prop, value); } }

    public string Text { get { return Rad.Get(Path, "Text"); } set { Rad.Set(Path, "Text", value); } }
    public string Caption { get { return Rad.Get(Path, "Caption"); } set { Rad.Set(Path, "Caption", value); } }
    public string Value { get { return Rad.Get(Path, "Value"); } set { Rad.Set(Path, "Value", value); } }
    public bool Enabled { get { return Rad.ToBool(Rad.Get(Path, "Enabled")); } set { Rad.Set(Path, "Enabled", value); } }
    public bool Visible { get { return Rad.ToBool(Rad.Get(Path, "Visible")); } set { Rad.Set(Path, "Visible", value); } }
    public int Left { get { return Rad.ToInt(Rad.Get(Path, "Left")); } set { Rad.Set(Path, "Left", value); } }
    public int Top { get { return Rad.ToInt(Rad.Get(Path, "Top")); } set { Rad.Set(Path, "Top", value); } }
    public int Width { get { return Rad.ToInt(Rad.Get(Path, "Width")); } set { Rad.Set(Path, "Width", value); } }
    public int Height { get { return Rad.ToInt(Rad.Get(Path, "Height")); } set { Rad.Set(Path, "Height", value); } }
    public string BackColor { get { return Rad.Get(Path, "BackColor"); } set { Rad.Set(Path, "BackColor", value); } }
    public string ForeColor { get { return Rad.Get(Path, "ForeColor"); } set { Rad.Set(Path, "ForeColor", value); } }
    public int ListIndex { get { return Rad.ToInt(Rad.Get(Path, "ListIndex")); } set { Rad.Set(Path, "ListIndex", value); } }
    public int ListCount { get { return Rad.ToInt(Rad.Get(Path, "ListCount")); } }
    public int Interval { get { return Rad.ToInt(Rad.Get(Path, "Interval")); } set { Rad.Set(Path, "Interval", value); } }

    public string Call(string method, params object[] args) { return Rad.Call(Path, method, args); }
    public void AddItem(object item) { Rad.Call(Path, "AddItem", item); }
    public void RemoveItem(int index) { Rad.Call(Path, "RemoveItem", index); }
    public void Clear() { Rad.Call(Path, "Clear"); }
    public string List(int index) { return Rad.Call(Path, "List", index); }
    public void SetFocus() { Rad.Call(Path, "SetFocus"); }
    public void Move(int left, int top, int width, int height) { Rad.Call(Path, "Move", left, top, width, height); }
    public string ShowDialog() { return Rad.Call(Path, "ShowDialog"); }
    public void Show() { Rad.Show(Path); }
    public void Hide() { Rad.Hide(Path); }
    public override string ToString() { return Text; }
}

/// <summary>Raised when radcall() cannot find or run the called function.</summary>
public class RadCallException : Exception
{
    public RadCallException(string message) : base(message) { }
}

public static class Rad
{
    /// <summary>Value as text: invariant culture, True/False.</summary>
    public static string Str(object value)
    {
        if (value == null) return "";
        if (value is bool) return (bool)value ? "True" : "False";
        var f = value as IFormattable;
        if (f != null) return f.ToString(null, CultureInfo.InvariantCulture);
        return value.ToString() ?? "";
    }

    public static bool ToBool(string s)
    {
        return s != null && (s.Equals("true", StringComparison.OrdinalIgnoreCase) || s == "1" || s == "-1");
    }

    public static int ToInt(string s)
    {
        double d;
        return double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d) ? (int)Math.Round(d) : 0;
    }

    public static double ToNumber(string s)
    {
        double d;
        return double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d) ? d : 0;
    }

    // ------------------------------------------------------------------ GUI
    public static void Set(string obj, string prop, object value) { RadNative.RadApp.SetProp(obj, prop, Str(value)); }
    public static string Get(string obj, string prop) { return RadNative.RadApp.GetProp(obj, prop); }
    public static double GetNumber(string obj, string prop) { return ToNumber(Get(obj, prop)); }

    public static string Call(string obj, string method, params object[] args)
    {
        return RadNative.RadApp.CallMethod(obj, method, (args ?? new object[0]).Select(Str).ToArray());
    }

    public static int MsgBox(object text) { return RadNative.RadApp.MsgBox(Str(text)); }
    public static string InputBox(object prompt) { return RadNative.RadApp.InputBox(Str(prompt)); }
    public static void Show(string form) { RadNative.RadApp.ShowForm(form, true); }
    public static void Hide(string form) { RadNative.RadApp.ShowForm(form, false); }

    /// <summary>Close the program.</summary>
    public static void End() { RadNative.RadApp.End(); }

    // ------------------------------------------------------------------ project modules
    /// <summary>Call "Module.function" (a public static method of a class of the program).</summary>
    public static object radcall(string function, params object[] args) { return RadNative.RadApp.LocalCall(function, args); }

    public static T radcall<T>(string function, params object[] args)
    {
        var r = RadNative.RadApp.LocalCall(function, args);
        if (r == null) return default(T);
        if (r is T) return (T)r;
        return (T)Convert.ChangeType(r, typeof(T), CultureInfo.InvariantCulture);
    }

    public static object RefCall(string function, params object[] args) { return RadNative.RadApp.LocalCall(function, args); }
}

namespace RadNative
{
    /// <summary>Who runs the handlers: C# static methods (CsHandlers) or PowerShell functions (PsHost).</summary>
    public interface IHandlers
    {
        bool Has(string name);
        void Invoke(string name, RadEvent e);
    }

    /// <summary>Handlers = static methods named Object_Event of the program's classes (like RadMain.cs).</summary>
    public sealed class CsHandlers : IHandlers
    {
        readonly Dictionary<string, MethodInfo> map = new Dictionary<string, MethodInfo>(StringComparer.OrdinalIgnoreCase);

        public CsHandlers(Assembly asm)
        {
            Type[] types;
            try { types = asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).ToArray(); }
            foreach (var type in types)
            {
                if (type.Namespace == "RadNative" || type == typeof(Rad) || type == typeof(RadControl) || type == typeof(RadEvent)) continue;
                foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.DeclaredOnly))
                {
                    if (m.IsSpecialName || m.Name.Contains("<") || !m.Name.Contains("_") || m.GetParameters().Length > 1) continue;
                    if (!map.ContainsKey(m.Name)) map[m.Name] = m;
                }
            }
        }

        public bool Has(string name) { return map.ContainsKey(name); }

        public void Invoke(string name, RadEvent e)
        {
            MethodInfo m;
            if (!map.TryGetValue(name, out m)) return;
            var ps = m.GetParameters();
            try
            {
                // async handlers are not waited for: their continuations run on the UI thread
                m.Invoke(null, ps.Length == 0 ? new object[0] : new object[] { e });
            }
            catch (TargetInvocationException ex)
            {
                RadApp.ReportError(name, ex.InnerException ?? ex);
            }
        }
    }

    /// <summary>Base class of the generated forms (RadForm_Form1 ...).</summary>
    public class RadFormBase : Form
    {
        public readonly string RadName;
        /// <summary>controls, menu items, timers and dialogs by name</summary>
        public readonly Dictionary<string, object> Items = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        /// <summary>the design client area (below the menu)</summary>
        protected readonly Panel Client = new Panel();
        public Panel ClientPanel { get { return Client; } }
        protected readonly ToolTip Tips = new ToolTip();
        public bool Closing2;

        public RadFormBase(string name)
        {
            RadName = name;
            Name = name;
            Client.Name = "";
            Client.Dock = DockStyle.Fill;
            Client.Margin = Padding.Empty;
            Font = new Font("Segoe UI", 9F);
        }

        /// <summary>menu height + design client height</summary>
        protected int MenuHeight()
        {
            return MainMenuStrip != null && MainMenuStrip.Visible ? MainMenuStrip.Height : 0;
        }

        public int ClientHeight() { return ClientSize.Height - MenuHeight(); }

        public void SetClientHeight(int h) { ClientSize = new Size(ClientSize.Width, h + MenuHeight()); }

        public void SetBack(Color c)
        {
            BackColor = c.IsEmpty ? SystemColors.Control : c;
            Client.BackColor = BackColor;
        }

        public string TipFor(Control c) { return Tips.GetToolTip(c) ?? ""; }

        public void SetTip(Control c, string text) { Tips.SetToolTip(c, text); }

        protected void Register(string name, object item)
        {
            if (!string.IsNullOrEmpty(name)) Items[name] = item;
        }

        protected static Font F(string family, float size, bool bold, bool italic)
        {
            var style = (bold ? FontStyle.Bold : FontStyle.Regular) | (italic ? FontStyle.Italic : FontStyle.Regular);
            try { return new Font(string.IsNullOrEmpty(family) ? "Segoe UI" : family, size <= 0 ? 9F : size, style); }
            catch (ArgumentException) { return new Font("Segoe UI", size <= 0 ? 9F : size, style); }
        }

        protected static Image Img(string file)
        {
            try { return Image.FromFile(RadApp.Res(file)); } catch (Exception) { return null; }
        }

        protected static string[] Lines(string items)
        {
            return (items ?? "").Split(';').Select(s => s.Trim()).Where(s => s.Length > 0).ToArray();
        }

        /// <summary>animations / visual states / layout variants of the form (null = it has none)</summary>
        public RadMotion Motion;
        string motionPlan;

        /// <summary>the native_plan records of the form (generated code; only forms that use motion call it)</summary>
        protected void UseMotion(string plan) { motionPlan = plan; }

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            if (!string.IsNullOrEmpty(motionPlan) && Motion == null)
            {
                try { Motion = new RadMotion(this, motionPlan); }
                catch (Exception ex) { RadApp.ReportError(RadName + " (animations)", ex); }
            }
            Fire(RadName, "Load", null);
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            if (Motion != null) Motion.Start();       // "On load" animations and "On timer" triggers
        }

        /// <summary>Begin a storyboard / an animation (its id, e.g. "fx1"); false = none of that name.</summary>
        public bool BeginAnimation(string name) { return Motion != null && Motion.ByName(name, false) > 0; }
        public bool StopAnimation(string name) { return Motion != null && Motion.ByName(name, true) > 0; }
        /// <summary>A visual state of the form (control "") or of one control ("Normal" / "Base" = none).</summary>
        public bool GoToState(string state, string control = "") { return Motion != null && Motion.GoToState(state, control); }
        public bool ApplySizeVariants() { return Motion != null && Motion.Variants(true); }
        public string CurrentSizes { get { return Motion != null ? Motion.CurrentSizes : ""; } }
        public string CurrentState { get { return Motion != null ? Motion.CurrentState : "Normal"; } }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            base.OnFormClosing(e);
            if (e.Cancel) return;
            var ev = new RadEvent { Sender = RadName, Name = "FormClosing" };
            Fire(RadName, "FormClosing", ev);
            if (ev.Cancel) { e.Cancel = true; return; }
            // a secondary form is hidden (it keeps its state, like the GUI Bridge); closing the startup form ends
            if (!RadApp.IsStartup(this) && e.CloseReason == CloseReason.UserClosing && !RadApp.Ending)
            {
                e.Cancel = true;
                Hide();
                Fire(RadName, "FormClosed", null);
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            base.OnFormClosed(e);
            Fire(RadName, "FormClosed", null);
        }

        protected void Fire(string owner, string ev, RadEvent e)
        {
            RadApp.Fire(owner, ev, e);
        }

        static int MouseButton(MouseButtons b)
        {
            return b == MouseButtons.Left ? 1 : b == MouseButtons.Middle ? 2 : b == MouseButtons.Right ? 3 : 0;
        }

        static RadEvent Mouse(string owner, string ev, MouseEventArgs a)
        {
            var e = new RadEvent { Sender = owner, Name = ev, X = a.X, Y = a.Y, Button = MouseButton(a.Button), Delta = a.Delta };
            e.MakeArgs();
            return e;
        }

        /// <summary>Connect the events of a control (or menu item / timer / the form) that have a handler.</summary>
        protected void Wire(object target, string owner, params string[] events)
        {
            foreach (var ev0 in events)
            {
                var ev = ev0;
                if (!RadApp.Has(owner + "_" + ev)) continue;
                var c = target as Control;
                switch (ev)
                {
                    case "Click":
                        if (target is ToolStripItem) ((ToolStripItem)target).Click += (s, a) => Fire(owner, ev, null);
                        else if (c != null) c.Click += (s, a) => Fire(owner, ev, null);
                        else RadRelay.Attach(target, owner, ev);
                        break;
                    case "DoubleClick":
                        if (c != null) c.DoubleClick += (s, a) => Fire(owner, ev, null);
                        break;
                    case "MouseDown": if (c != null) c.MouseDown += (s, a) => Fire(owner, ev, Mouse(owner, ev, a)); break;
                    case "MouseUp": if (c != null) c.MouseUp += (s, a) => Fire(owner, ev, Mouse(owner, ev, a)); break;
                    case "MouseMove": if (c != null) c.MouseMove += (s, a) => Fire(owner, ev, Mouse(owner, ev, a)); break;
                    case "MouseWheel": if (c != null) c.MouseWheel += (s, a) => Fire(owner, ev, Mouse(owner, ev, a)); break;
                    case "MouseEnter": if (c != null) c.MouseEnter += (s, a) => Fire(owner, ev, null); break;
                    case "MouseLeave": if (c != null) c.MouseLeave += (s, a) => Fire(owner, ev, null); break;
                    case "KeyDown":
                    case "KeyUp":
                        if (c != null)
                        {
                            KeyEventHandler h = (s, a) =>
                            {
                                var e = new RadEvent { Sender = owner, Name = ev, KeyCode = a.KeyValue };
                                e.MakeArgs();
                                Fire(owner, ev, e);
                            };
                            if (ev == "KeyDown") c.KeyDown += h; else c.KeyUp += h;
                            if (c is Form) ((Form)c).KeyPreview = true;
                        }
                        break;
                    case "KeyPress":
                        if (c != null)
                        {
                            c.KeyPress += (s, a) =>
                            {
                                var e = new RadEvent { Sender = owner, Name = ev, KeyChar = a.KeyChar.ToString(), KeyCode = a.KeyChar };
                                e.MakeArgs();
                                Fire(owner, ev, e);
                            };
                            if (c is Form) ((Form)c).KeyPreview = true;
                        }
                        break;
                    case "GotFocus": if (c != null) c.GotFocus += (s, a) => Fire(owner, ev, null); break;
                    case "LostFocus": if (c != null) c.LostFocus += (s, a) => Fire(owner, ev, null); break;
                    case "TextChanged": if (c != null) c.TextChanged += (s, a) => Fire(owner, ev, null); break;
                    case "Resize": if (c != null) c.Resize += (s, a) => Fire(owner, ev, null); break;
                    case "Activated": if (c is Form) ((Form)c).Activated += (s, a) => Fire(owner, ev, null); break;
                    case "Deactivate": if (c is Form) ((Form)c).Deactivate += (s, a) => Fire(owner, ev, null); break;
                    case "CheckedChanged":
                        if (c is CheckBox) ((CheckBox)c).CheckedChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is RadioButton) ((RadioButton)c).CheckedChanged += (s, a) => Fire(owner, ev, null);
                        else RadRelay.Attach(target, owner, ev);
                        break;
                    case "SelectedIndexChanged":
                        if (c is ListBox) ((ListBox)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is ComboBox) ((ComboBox)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is TabControl) ((TabControl)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        else RadRelay.Attach(target, owner, ev);
                        break;
                    case "ValueChanged":
                        if (c is NumericUpDown) ((NumericUpDown)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is TrackBar) ((TrackBar)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is DateTimePicker) ((DateTimePicker)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        else RadRelay.Attach(target, owner, ev);
                        break;
                    case "Tick":
                        if (target is Timer) ((Timer)target).Tick += (s, a) => Fire(owner, ev, null);
                        break;
                    default:
                        // a control of a referenced library (controls.json "events"): any (sender, EventArgs)-shaped event
                        RadRelay.Attach(target, owner, ev);
                        break;
                }
            }
        }
    }

    /// <summary>Connects any event of the form (object sender, SomeEventArgs e) - EventHandler, EventHandler&lt;T&gt; or a
    /// WinForms delegate - to a handler. Item data of the event args (ItemName / Index / Text, grid RowIndex /
    /// ColumnIndex) goes into RadEvent; Cancel set by the handler is copied back.</summary>
    public sealed class RadRelay
    {
        readonly string owner, ev;
        RadRelay(string owner, string ev) { this.owner = owner; this.ev = ev; }

        public static bool Attach(object target, string owner, string ev)
        {
            var info = target.GetType().GetEvent(ev);
            if (info == null) return false;
            var invoke = info.EventHandlerType.GetMethod("Invoke");
            var ps = invoke != null ? invoke.GetParameters() : new ParameterInfo[0];
            if (ps.Length != 2 || !typeof(EventArgs).IsAssignableFrom(ps[1].ParameterType) || invoke.ReturnType != typeof(void)) return false;
            var relay = new RadRelay(owner, ev);
            var d = Delegate.CreateDelegate(info.EventHandlerType, relay, typeof(RadRelay).GetMethod("On"), false);
            if (d == null) return false;
            info.AddEventHandler(target, d);
            return true;
        }

        static object P(object o, string name)
        {
            var p = o.GetType().GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
            return p != null && p.GetIndexParameters().Length == 0 ? p.GetValue(o, null) : null;
        }

        public void On(object sender, EventArgs a)
        {
            RadEvent e = null;
            if (a != null && a.GetType() != typeof(EventArgs))
            {
                e = new RadEvent { Sender = owner, Name = ev };
                var item = P(a, "ItemName") as string;
                var idx = P(a, "Index");
                var row = P(a, "RowIndex");
                var col = P(a, "ColumnIndex");
                if (idx is int) e.Index = (int)idx;
                if (!string.IsNullOrEmpty(item)) e.ItemName = item;
                // same argument text as the radforms (C) controls: "name index" for items, "row col" for grid cells
                if (row is int && col is int) { e.X = (int)row; e.Y = (int)col; e.Index = (int)row; e.Args = row + " " + col; }
                else if (item != null || idx is int) e.Args = (e.ItemName.Length > 0 ? e.ItemName : "-") + " " + e.Index.ToString(CultureInfo.InvariantCulture);
                var me = a as MouseEventArgs;
                if (me != null) { e.X = me.X; e.Y = me.Y; e.Delta = me.Delta; e.MakeArgs(); }
            }
            RadApp.Fire(owner, ev, e);
            if (e != null && e.Cancel)
            {
                var cp = a.GetType().GetProperty("Cancel", BindingFlags.Public | BindingFlags.Instance);
                if (cp != null && cp.CanWrite && cp.PropertyType == typeof(bool)) cp.SetValue(a, true, null);
            }
        }
    }

    /// <summary>Animations, visual states and layout variants of a form: the records of radide/motion/native_plan.py
    /// (XR X XT K Q V VL VP, TAB-separated, embedded by the generator) played with the rules of the IDE's Python
    /// runtime and of radforms (radforms_motion.inc): easings, relative keys resolved at Begin, repeat / auto reverse /
    /// count, delay, restore, triggers (load click hover timer after show hide manual), reduced motion, the Visual
    /// State Manager (MouseOver / Pressed / Focused / Disabled + GoToState) and the CSS-like size cascade of layout
    /// variants. Geometry in the records is in logical 96-DPI pixels (scaled by the form's DPI factor).
    /// Program API (Rad.Call / CallMethod on the form): BeginAnimation, StopAnimation, GoToState(state[, control]),
    /// ApplySizeVariants(); properties CurrentSizes, CurrentState; events &lt;Form&gt;_SizeVariantChanged,
    /// &lt;Storyboard&gt;_Completed.</summary>
    public sealed class RadMotion
    {
        const int PNUM = 0, PCOLOR = 1, PBOOL = 2, PTEXT = 3, POTHER = 4;
        const int TLOAD = 0, TCLICK = 1, THOVER = 2, TTIMER = 3, TSHOW = 4, THIDE = 5, TAFTER = 6, TMANUAL = 7;
        const int ELINEAR = 0, EIN = 1, EOUT = 2, EINOUT = 3, ESINE = 4, EBACK = 5, EELASTIC = 6, EBOUNCE = 7;
        const int FOVER = 1, FPRESSED = 2, FFOCUSED = 4, FDISABLED = 8;

        sealed class Key { public int Ms, Ease; public char Kind, Of; public double A, B, D, Rv; public string S, Rs; }

        sealed class Track
        {
            public string Prop;
            public int Pt, LastBool = -1;
            public readonly List<Key> K = new List<Key>();
            public double SNum;
            public string SText;
        }

        sealed class Sb
        {
            public string Fx = "", TName = "", Src = "", After = "";
            public Control C;                  // null = the form
            public int Count = 1, Delay, On = TMANUAL, Interval, Leave, Dur;
            public bool Forever, AutoRev, Restore, Playing, Rev, Hiding, Saved, Pending, HasGeo;
            public readonly List<Track> Tr = new List<Track>();
            public double T0, Pos;
            public Rectangle Bounds0;
            public DockStyle Dock0;
            public Timer DelayTimer, EveryTimer;
        }

        sealed class Q { public Control C; public bool Form; public string State, Prop, Val; }
        sealed class Ap { public Control C; public string Prop, Saved, Val; }
        sealed class Fl { public int Flags; public string Manual = ""; }
        sealed class VSize { public string Id = "", Orient = "", Posture = "", Span = "", Fold = ""; public double MnW, MxW, MnH, MxH; }
        sealed class Vl { public int Size; public Control C; public double[] Pl; }
        sealed class Vp { public int Size; public Control C; public string Prop, Val; }
        sealed class BaseL { public Control C; public double[] Pl; public AnchorStyles Anchor; public DockStyle Dock; }
        sealed class Bp { public Control C; public string Prop, Val; }

        readonly RadFormBase form;
        readonly List<Sb> sbs = new List<Sb>();
        readonly List<Q> qs = new List<Q>();
        readonly List<Ap> aps = new List<Ap>();
        readonly Dictionary<Control, Fl> fls = new Dictionary<Control, Fl>();
        readonly List<VSize> sizes = new List<VSize>();
        readonly List<Vl> vls = new List<Vl>();
        readonly List<Vp> vps = new List<Vp>();
        readonly List<BaseL> bases = new List<BaseL>();
        readonly List<Bp> bps = new List<Bp>();
        readonly Dictionary<Control, double[]> placed = new Dictionary<Control, double[]>();
        readonly Timer frame = new Timer { Interval = 15 };
        static readonly System.Diagnostics.Stopwatch clock = System.Diagnostics.Stopwatch.StartNew();
        bool respect = true, reduced, started, hasCur, closed;
        bool[] cur = new bool[0];
        string state = "";
        double k = 1, designW, designH;
        int quiet;

        public RadMotion(RadFormBase form, string plan)
        {
            this.form = form;
            try { k = form.CurrentAutoScaleDimensions.Width / 96.0; } catch (Exception) { k = 1; }
            if (k <= 0.1) k = 1;
            designW = form.ClientPanel.ClientSize.Width / k;
            designH = form.ClientPanel.ClientSize.Height / k;
            Parse(plan ?? "");
            reduced = respect && ReducedSystem();
            frame.Tick += (s, a) => Guard(OnFrame);
            var hooked = new HashSet<Control>();
            bool formHooked = false;
            foreach (var sb in sbs)
            {
                if (sb.On != TCLICK && sb.On != THOVER) continue;
                if (Ieq(sb.Src, form.RadName) || sb.Src.Length == 0) { if (!formHooked) { formHooked = true; Hook(form.ClientPanel, form.RadName, null, false); } continue; }
                var c = Ctl(sb.Src);
                if (c != null && hooked.Add(c)) Hook(c, c.Name, c, HasStates(c));
            }
            foreach (var q in qs)
                if (q.C != null && hooked.Add(q.C)) Hook(q.C, q.C.Name, q.C, true);
            foreach (var q in qs)                  // controls that start disabled are in their Disabled state
                if (q.C != null && !q.C.Enabled) Flag(q.C, FDISABLED, true);
            if (sizes.Count > 0) form.ClientPanel.SizeChanged += (s, a) => Guard(() => { if (!Variants(true)) Replace(); });
            form.FormClosed += (s, a) => Close();
            Variants(false);
        }

        // ------------------------------------------------------------------ records
        static string Unesc(string s)
        {
            if (s.IndexOf('\\') < 0) return s;
            var b = new StringBuilder(s.Length);
            for (int i = 0; i < s.Length; i++)
            {
                char ch = s[i];
                if (ch == '\\' && i + 1 < s.Length)
                {
                    char n = s[i + 1];
                    if (n == 't') { b.Append('\t'); i++; continue; }
                    if (n == 'n') { b.Append('\n'); i++; continue; }
                    if (n == 'r') { b.Append('\r'); i++; continue; }
                    if (n == '\\') { b.Append('\\'); i++; continue; }
                }
                b.Append(ch);
            }
            return b.ToString();
        }

        static bool Ieq(string a, string b) { return string.Equals(a ?? "", b ?? "", StringComparison.OrdinalIgnoreCase); }

        Control Ctl(string name)
        {
            object o;
            return !string.IsNullOrEmpty(name) && form.Items.TryGetValue(name, out o) ? o as Control : null;
        }

        static double Lim(string s) { return string.IsNullOrEmpty(s) ? -1 : Rad.ToNumber(s); }

        static int EaseOf(string s)
        {
            switch ((s ?? "").ToLowerInvariant())
            {
                case "in": return EIN;
                case "out": return EOUT;
                case "inout": return EINOUT;
                case "sine": return ESINE;
                case "back": return EBACK;
                case "elastic": return EELASTIC;
                case "bounce": return EBOUNCE;
            }
            return ELINEAR;
        }

        static int OnOf(string s)
        {
            string[] n = { "load", "click", "hover", "timer", "show", "hide", "after", "manual" };
            for (int i = 0; i < n.Length; i++) if (Ieq(s, n[i])) return i;
            return TMANUAL;
        }

        static int PType(string p)
        {
            if (Ieq(p, "BackColor") || Ieq(p, "ForeColor")) return PCOLOR;
            if (Ieq(p, "Visible") || Ieq(p, "FontBold") || Ieq(p, "FontItalic") || Ieq(p, "Enabled") || Ieq(p, "Checked")) return PBOOL;
            if (Ieq(p, "Text") || Ieq(p, "Caption")) return PTEXT;
            if (Ieq(p, "Left") || Ieq(p, "Top") || Ieq(p, "Width") || Ieq(p, "Height") || Ieq(p, "FontSize") || Ieq(p, "Opacity") || Ieq(p, "Value")) return PNUM;
            return POTHER;
        }

        static bool IntProp(string p) { return Ieq(p, "Left") || Ieq(p, "Top") || Ieq(p, "Width") || Ieq(p, "Height") || Ieq(p, "FontSize") || Ieq(p, "Value"); }
        static bool Geo(string p) { return Ieq(p, "Left") || Ieq(p, "Top") || Ieq(p, "Width") || Ieq(p, "Height"); }

        static bool BoolText(string s)
        {
            s = (s ?? "").Trim().ToLowerInvariant();
            return s == "1" || s == "-1" || s == "true" || s == "yes" || s == "on";
        }

        void Parse(string plan)
        {
            Sb sb = null;
            foreach (var raw in plan.Split('\n'))
            {
                var line = raw.TrimEnd('\r');
                if (line.Length == 0) continue;
                var f = line.Split('\t').Select(Unesc).ToArray();
                Func<int, string> F = i => i < f.Length ? f[i] : "";
                var kind = F(0);
                if (kind == "XR") respect = BoolText(F(1));
                else if (kind == "X")
                {
                    sb = null;
                    var c = Ctl(F(2));
                    if (F(2).Length > 0 && c == null) continue;
                    sb = new Sb { Fx = F(1), TName = F(2), C = c, Count = Math.Max(1, Rad.ToInt(F(3))), Forever = Rad.ToInt(F(4)) != 0,
                                  AutoRev = Rad.ToInt(F(5)) != 0, Delay = Rad.ToInt(F(6)), Restore = Rad.ToInt(F(7)) != 0 };
                    sbs.Add(sb);
                }
                else if (kind == "XT" && sb != null)
                {
                    sb.On = OnOf(F(1));
                    sb.Src = F(2).Length > 0 ? F(2) : sb.TName;
                    sb.Interval = Rad.ToInt(F(3));
                    sb.After = F(4);
                    sb.Leave = Ieq(F(5), "stop") ? 1 : Ieq(F(5), "none") ? 2 : 0;
                }
                else if (kind == "K" && sb != null)
                {
                    var t = sb.Tr.Count > 0 ? sb.Tr[sb.Tr.Count - 1] : null;
                    if (t == null || !Ieq(t.Prop, F(1)))
                    {
                        t = new Track { Prop = F(1), Pt = PType(F(1)) };
                        if (t.Pt == POTHER) t.Pt = PNUM;
                        sb.Tr.Add(t);
                    }
                    var key = new Key { Ms = Math.Max(0, Rad.ToInt(F(2))), Ease = EaseOf(F(3)), A = Rad.ToNumber(F(5)), B = Rad.ToNumber(F(6)),
                                        D = Rad.ToNumber(F(8)), Of = Ieq(F(7), "Width") ? 'W' : Ieq(F(7), "Height") ? 'H' : '\0' };
                    if (key.Ms > sb.Dur) sb.Dur = key.Ms;
                    var kd = F(4);
                    switch (kd.Length > 0 ? kd[0] : 'n')
                    {
                        case 'c': { int rgb; key.Kind = 'c'; key.A = ParseColor(F(5), out rgb) ? rgb : 0; break; }
                        case 'b': key.Kind = 'b'; key.A = BoolText(F(5)) ? 1 : 0; break;
                        case 's': key.Kind = 's'; key.S = F(5); break;
                        case 'r': key.Kind = 'r'; break;
                        case 'p': key.Kind = 'p'; break;
                        case 'v': key.Kind = 'v'; break;
                        default: key.Kind = 'n'; break;
                    }
                    t.K.Add(key);
                }
                else if (kind == "Q")
                {
                    var c = Ctl(F(1));
                    if (F(1).Length > 0 && c == null) continue;
                    qs.Add(new Q { C = c, Form = c == null, State = F(2), Prop = F(3), Val = F(4) });
                }
                else if (kind == "V")
                {
                    sizes.Add(new VSize { Id = F(1), MnW = Lim(F(2)), MxW = Lim(F(3)), MnH = Lim(F(4)), MxH = Lim(F(5)), Orient = F(6),
                                          Posture = PostureNorm(F(7)), Span = F(8).ToLowerInvariant(), Fold = F(9).ToLowerInvariant() });
                }
                else if (kind == "VL" || kind == "VP")
                {
                    var c = Ctl(F(2));
                    if (F(2).Length > 0 && c == null) continue;
                    int si = sizes.FindIndex(z => Ieq(z.Id, F(1)));
                    if (si < 0) continue;
                    if (kind == "VL")
                    {
                        var p = F(3).Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Select(Rad.ToNumber).ToArray();
                        if (c == null || p.Length != 8 || c.Parent == null) continue;
                        if (!bases.Any(b => b.C == c)) bases.Add(new BaseL { C = c, Pl = BasePlace(c), Anchor = c.Anchor, Dock = c.Dock });
                        vls.Add(new Vl { Size = si, C = c, Pl = p });
                    }
                    else
                    {
                        vps.Add(new Vp { Size = si, C = c, Prop = F(3), Val = F(4) });
                        if (!bps.Any(b => b.C == c && Ieq(b.Prop, F(3)))) bps.Add(new Bp { C = c, Prop = F(3), Val = GetStr(c, F(3)) });
                    }
                }
            }
        }

        // ------------------------------------------------------------------ helpers
        static double Now() { return clock.Elapsed.TotalMilliseconds; }

        void Guard(Action a)
        {
            if (closed) return;
            try { a(); }
            catch (Exception ex) { try { Console.Error.WriteLine("[rad] motion: " + ex.Message); } catch (Exception) { } }
        }

        void Close()
        {
            closed = true;
            frame.Stop();
            foreach (var sb in sbs)
            {
                if (sb.DelayTimer != null) sb.DelayTimer.Stop();
                if (sb.EveryTimer != null) sb.EveryTimer.Stop();
            }
        }

        static bool EnvTrue(string name, out bool set)
        {
            var v = (Environment.GetEnvironmentVariable(name) ?? "").Trim().ToLowerInvariant();
            set = v.Length > 0;
            return v == "1" || v == "true" || v == "yes" || v == "on";
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        static extern bool SystemParametersInfo(uint action, uint param, ref int value, uint ini);

        static bool ReducedSystem()
        {
            bool set;
            var v = EnvTrue("RADIDE_REDUCED_MOTION", out set);
            if (set) return v;
            try
            {
                int on = 1;
                if (SystemParametersInfo(0x1042 /* SPI_GETCLIENTAREAANIMATION */, 0, ref on, 0)) return on == 0;
            }
            catch (Exception) { }
            return false;
        }

        static double Ease(double f, int e)
        {
            switch (e)
            {
                case EIN: return f * f;
                case EOUT: return 1 - (1 - f) * (1 - f);
                case EINOUT: return f < 0.5 ? 2 * f * f : 1 - 2 * (1 - f) * (1 - f);
                case ESINE: return -(Math.Cos(Math.PI * f) - 1) / 2;
                case EBACK: return 1 + 2.70158 * Math.Pow(f - 1, 3) + 1.70158 * Math.Pow(f - 1, 2);
                case EELASTIC:
                    if (f <= 0 || f >= 1) return f >= 1 ? 1.0 : 0.0;
                    return Math.Pow(2, -10 * f) * Math.Sin((f * 10 - 0.75) * (2 * Math.PI / 3)) + 1;
                case EBOUNCE:
                    {
                        double n = 7.5625, d = 2.75;
                        if (f < 1 / d) return n * f * f;
                        if (f < 2 / d) { f -= 1.5 / d; return n * f * f + 0.75; }
                        if (f < 2.5 / d) { f -= 2.25 / d; return n * f * f + 0.9375; }
                        f -= 2.625 / d;
                        return n * f * f + 0.984375;
                    }
            }
            return f;
        }

        static string Num(double d) { return d.ToString("0.####", CultureInfo.InvariantCulture); }

        static bool ParseColor(string s, out int rgb)
        {
            rgb = 0;
            s = (s ?? "").Trim();
            if (s.StartsWith("#"))
            {
                var h = s.Substring(1);
                if (h.Length == 3) h = new string(new[] { h[0], h[0], h[1], h[1], h[2], h[2] });
                if (h.Length == 8) h = h.Substring(2);
                return h.Length == 6 && int.TryParse(h, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out rgb);
            }
            if (s.Length == 0) return false;
            try
            {
                var c = Color.FromName(s);
                if (!c.IsKnownColor && c.A == 0) return false;
                rgb = (c.R << 16) | (c.G << 8) | c.B;
                return true;
            }
            catch (Exception) { return false; }
        }

        static int Pack(Color c) { return (c.R << 16) | (c.G << 8) | c.B; }
        static Color Unpack(int v) { return Color.FromArgb((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF); }
        int Px(double v) { return (int)Math.Floor(v * k + 0.5); }

        // ------------------------------------------------------------------ property access (logical values)
        double GetNum(Control c, string p)
        {
            if (c == null)
            {
                if (Ieq(p, "Opacity")) return form.Opacity;
                if (Ieq(p, "Left")) return form.Left / k;
                if (Ieq(p, "Top")) return form.Top / k;
                if (Ieq(p, "Width")) return form.ClientSize.Width / k;
                if (Ieq(p, "Height")) return form.ClientHeight() / k;
                return Rad.ToNumber(RadApp.GetOn(form, p));
            }
            if (Ieq(p, "Opacity")) return 1.0;
            if (Ieq(p, "Left")) return c.Left / k;
            if (Ieq(p, "Top")) return c.Top / k;
            if (Ieq(p, "Width")) return c.Width / k;
            if (Ieq(p, "Height")) return c.Height / k;
            if (Ieq(p, "FontSize")) return c.Font.SizeInPoints;
            return Rad.ToNumber(RadApp.GetOn(c, p));
        }

        void SetNum(Control c, string p, double v)
        {
            if (Ieq(p, "Opacity"))
            {
                if (c != null) return;              // child windows have no transparency (expand() blends colours)
                form.Opacity = v < 0 ? 0 : v > 1 ? 1 : v;
                return;
            }
            if (c == null)
            {
                if (Ieq(p, "Left")) form.Left = Px(v);
                else if (Ieq(p, "Top")) form.Top = Px(v);
                else if (Ieq(p, "Width")) form.ClientSize = new Size(Math.Max(0, Px(v)), form.ClientSize.Height);
                else if (Ieq(p, "Height")) form.SetClientHeight(Math.Max(0, Px(v)));
                else RadApp.SetOn(form, p, Num(v));
                return;
            }
            if (Ieq(p, "Left")) c.Left = Px(v);
            else if (Ieq(p, "Top")) c.Top = Px(v);
            else if (Ieq(p, "Width")) c.Width = Math.Max(0, Px(v));
            else if (Ieq(p, "Height")) c.Height = Math.Max(0, Px(v));
            else if (IntProp(p)) RadApp.SetOn(c, p, Num(Math.Floor(v + 0.5)));
            else RadApp.SetOn(c, p, Num(v));
        }

        int GetColor(Control c, string p)
        {
            var t = c ?? (Control)form;
            Color col = Ieq(p, "ForeColor") ? t.ForeColor : t.BackColor;
            for (var q = t.Parent; col.A == 0 && q != null; q = q.Parent) col = q.BackColor;   // transparent: what is behind
            return Pack(col);
        }

        int ParentColor(Control c) { return c == null || c.Parent == null ? GetColor(null, "BackColor") : GetColor(c.Parent, "BackColor"); }

        void SetColor(Control c, string p, int rgb)
        {
            var col = Unpack(rgb);
            if (Ieq(p, "ForeColor")) { (c ?? (Control)form).ForeColor = col; return; }
            if (c == null) form.SetBack(col);
            else c.BackColor = col;
        }

        bool GetBool(Control c, string p)
        {
            var t = c ?? (Control)form;
            if (Ieq(p, "Visible")) return c == null ? form.Visible : RadApp.IsShown(c);
            if (Ieq(p, "Enabled")) return t.Enabled;
            if (Ieq(p, "FontBold")) return t.Font.Bold;
            if (Ieq(p, "FontItalic")) return t.Font.Italic;
            return Rad.ToBool(RadApp.GetOn(t, p));
        }

        void SetBool(Control c, string p, bool v)
        {
            quiet++;
            try
            {
                if (Ieq(p, "Visible") && c != null) RadApp.SetVisibleRaw(c, v);
                else RadApp.SetOn(c ?? (Control)form, p, v ? "True" : "False");
            }
            finally { quiet--; }
        }

        string GetText(Control c) { return c == null ? form.Text : RadApp.GetOn(c, "Text"); }

        void SetText(Control c, string v)
        {
            if (c == null) form.Text = v ?? "";
            else RadApp.SetOn(c, "Text", v ?? "");
        }

        /// <summary>a value in the neutral text form of the records (numbers, True / False, #rrggbb, text)</summary>
        string GetStr(Control c, string p)
        {
            switch (PType(p))
            {
                case PNUM: return Num(GetNum(c, p));
                case PCOLOR: return "#" + GetColor(c, p).ToString("x6");
                case PBOOL: return GetBool(c, p) ? "True" : "False";
                case PTEXT: return GetText(c);
            }
            return RadApp.GetOn(c ?? (Control)form, p);
        }

        void SetStr(Control c, string p, string v)
        {
            switch (PType(p))
            {
                case PNUM: SetNum(c, p, Rad.ToNumber(v)); return;
                case PCOLOR: { int rgb; if (ParseColor(v, out rgb)) SetColor(c, p, rgb); return; }
                case PBOOL: SetBool(c, p, BoolText(v)); return;
                case PTEXT: SetText(c, v); return;
            }
            quiet++;
            try { RadApp.SetOn(c ?? (Control)form, p, v ?? ""); } finally { quiet--; }
        }

        // ------------------------------------------------------------------ storyboards
        static void Forget(Sb sb)
        {
            foreach (var t in sb.Tr)
            {
                t.SText = null;
                foreach (var key in t.K) key.Rs = null;
            }
            sb.Saved = false;
        }

        /// <summary>the values at Begin; relative keys made absolute against them (_Storyboard._remember)</summary>
        void Remember(Sb sb)
        {
            if (sb.Saved) return;
            sb.Saved = true;
            sb.HasGeo = false;
            double sw = GetNum(sb.C, "Width"), sh = GetNum(sb.C, "Height");
            foreach (var t in sb.Tr)
            {
                t.LastBool = -1;
                if (sb.C != null && Geo(t.Prop) && !sb.HasGeo)
                {
                    sb.Bounds0 = sb.C.Bounds;          // Stop gives the layout (Anchor / Dock) back
                    sb.Dock0 = sb.C.Dock;
                    sb.HasGeo = true;
                }
                switch (t.Pt)
                {
                    case PCOLOR: t.SNum = GetColor(sb.C, t.Prop); break;
                    case PBOOL: t.SNum = GetBool(sb.C, t.Prop) ? 1 : 0; break;
                    case PTEXT: t.SText = GetText(sb.C) ?? ""; break;
                    default: t.SNum = GetNum(sb.C, t.Prop); break;
                }
                foreach (var key in t.K)
                {
                    key.Rs = null;
                    switch (key.Kind)
                    {
                        case 'p': key.Rv = t.Pt == PCOLOR ? ParentColor(sb.C) : t.SNum; break;
                        case 'r':
                            if (t.Pt == PNUM)
                            {
                                double v = t.SNum * key.A + key.B + (key.Of == 'W' ? key.D * sw : key.Of == 'H' ? key.D * sh : 0);
                                if (IntProp(t.Prop) && !Geo(t.Prop)) v = Math.Floor(v + 0.5);
                                if (Ieq(t.Prop, "Opacity")) v = v < 0 ? 0 : v > 1 ? 1 : v;
                                key.Rv = v;
                            }
                            else if (t.Pt == PTEXT) key.Rs = t.SText ?? "";
                            else key.Rv = t.SNum;          // colours / bools keep their start value
                            break;
                        case 'v':
                            {
                                var s = t.SText ?? "";
                                double fr = key.A < 0 ? 0 : key.A > 1 ? 1 : key.A;
                                key.Rs = s.Substring(0, Math.Min(s.Length, (int)Math.Floor(s.Length * fr + 0.5)));
                                break;
                            }
                        case 's': key.Rs = key.S ?? ""; break;
                        default: key.Rv = key.A; break;    // n / c / b
                    }
                }
            }
        }

        static int MixColor(int a, int b, double fr)
        {
            if (fr >= 1) return b;
            Func<int, int> ch = sh =>
            {
                int x = (a >> sh) & 0xFF, y = (b >> sh) & 0xFF;
                int v = (int)Math.Floor(x + (y - x) * fr + 0.5);
                return v < 0 ? 0 : v > 255 ? 255 : v;
            };
            return (ch(16) << 16) | (ch(8) << 8) | ch(0);
        }

        /// <summary>text between two keys: typed / erased when one is a prefix of the other, else discrete</summary>
        static string MixText(string a, string b, double fr)
        {
            if (fr <= 0) return a;
            int la = a.Length, lb = b.Length;
            var longer = la > lb ? a : b;
            if ((la <= lb && b.StartsWith(a, StringComparison.Ordinal)) || (lb < la && a.StartsWith(b, StringComparison.Ordinal)))
            {
                double x = la + ((double)lb - la) * (fr > 1 ? 1 : fr);
                int n = x < 0 ? 0 : (int)Math.Floor(x + 0.5);
                return longer.Substring(0, Math.Min(n, longer.Length));
            }
            return fr >= 1 ? b : a;
        }

        void Apply(Sb sb, double ms)
        {
            sb.Pos = ms;
            foreach (var t in sb.Tr)
            {
                var kk = t.K;
                if (kk.Count == 0) continue;
                double v0, v1, fr = 1;
                string s0, s1;
                bool lead = kk[0].Ms > 0;            // the start value is the implicit key at 0
                if (ms <= (lead ? 0 : kk[0].Ms))
                {
                    if (lead) { v0 = v1 = t.SNum; s0 = s1 = t.SText ?? ""; }
                    else { v0 = v1 = kk[0].Rv; s0 = s1 = kk[0].Rs ?? ""; }
                }
                else
                {
                    Key k0 = null, k1 = null;
                    for (int j = 0; j < kk.Count; j++)
                        if (ms <= kk[j].Ms) { k1 = kk[j]; k0 = j > 0 ? kk[j - 1] : null; break; }
                    if (k1 == null)
                    {
                        k1 = kk[kk.Count - 1];
                        v0 = v1 = k1.Rv;
                        s0 = s1 = k1.Rs ?? "";
                    }
                    else
                    {
                        int t0 = k0 != null ? k0.Ms : 0;
                        v0 = k0 != null ? k0.Rv : t.SNum;
                        s0 = k0 != null ? (k0.Rs ?? "") : (t.SText ?? "");
                        v1 = k1.Rv;
                        s1 = k1.Rs ?? "";
                        fr = k1.Ms > t0 ? (ms - t0) / (k1.Ms - t0) : 1.0;
                        fr = Ease(fr, k1.Ease);
                    }
                }
                switch (t.Pt)
                {
                    case PCOLOR:
                        SetColor(sb.C, t.Prop, fr <= 0 ? (int)v0 : MixColor((int)v0, (int)v1, fr));
                        break;
                    case PBOOL:
                        {
                            int b = fr >= 1 ? (v1 != 0 ? 1 : 0) : (v0 != 0 ? 1 : 0);
                            if (t.LastBool == b && Ieq(t.Prop, "Visible")) break;   // re-showing every frame re-places
                            t.LastBool = b;
                            SetBool(sb.C, t.Prop, b != 0);
                            break;
                        }
                    case PTEXT:
                        {
                            var w = MixText(s0, s1, fr);
                            if (GetText(sb.C) != w) SetText(sb.C, w);
                            break;
                        }
                    default:
                        SetNum(sb.C, t.Prop, fr <= 0 ? v0 : v0 + (v1 - v0) * fr);
                        break;
                }
            }
        }

        void FrameUpdate()
        {
            bool any = sbs.Any(s => s.Playing);
            if (any && !frame.Enabled && !closed) frame.Start();
            else if (!any && frame.Enabled) frame.Stop();
        }

        void Stop(Sb sb)
        {
            sb.Playing = sb.Rev = false;
            sb.Pos = 0;
            if (sb.Pending) { sb.DelayTimer.Stop(); sb.Pending = false; }
            if (sb.Saved)
            {
                foreach (var t in sb.Tr)
                {
                    if (sb.C != null && Geo(t.Prop) && sb.HasGeo) continue;
                    switch (t.Pt)
                    {
                        case PCOLOR: SetColor(sb.C, t.Prop, (int)t.SNum); break;
                        case PBOOL: SetBool(sb.C, t.Prop, t.SNum != 0); break;
                        case PTEXT: SetText(sb.C, t.SText); break;
                        default: SetNum(sb.C, t.Prop, t.SNum); break;
                    }
                }
                if (sb.C != null && sb.HasGeo)       // the layout takes the control back
                {
                    if (sb.C.Dock != sb.Dock0) sb.C.Dock = sb.Dock0;
                    if (sb.Dock0 == DockStyle.None) sb.C.Bounds = sb.Bounds0;
                }
                Forget(sb);
            }
            FrameUpdate();
        }

        void BeginNow(Sb sb)
        {
            Remember(sb);
            sb.Playing = true;
            sb.Rev = false;
            sb.T0 = Now();
            Apply(sb, 0);
            FrameUpdate();
        }

        bool SameNamePlaying(Sb sb) { return sbs.Any(s => s != sb && s.Playing && Ieq(s.Fx, sb.Fx)); }

        void Fire(string owner, string ev)
        {
            try { form.BeginInvoke((Action)(() => RadApp.Fire(owner, ev, null))); }
            catch (InvalidOperationException) { RadApp.Fire(owner, ev, null); }
        }

        /// <summary>the end of a storyboard: hide / give back / chains / &lt;name&gt;_Completed</summary>
        void Completed(Sb sb)
        {
            sb.Playing = false;
            if (sb.Hiding)
            {
                sb.Hiding = false;
                Stop(sb);
                SetBool(sb.C, "Visible", false);
            }
            else if (sb.Restore) Stop(sb);
            foreach (var s in sbs.ToList())
                if (s.On == TAFTER && Ieq(s.After, sb.Fx)) FxBegin(s);
            if (!SameNamePlaying(sb) && !sb.Fx.StartsWith("_fx_", StringComparison.Ordinal)) Fire(sb.Fx, "Completed");
            FrameUpdate();
        }

        void Finish(Sb sb)
        {
            Remember(sb);
            Apply(sb, sb.AutoRev ? 0 : sb.Dur);
            Completed(sb);
        }

        void Tick(Sb sb)
        {
            double ms = Now() - sb.T0, span, total;
            bool done = false;
            if (!sb.Playing) return;
            if (sb.Rev)
            {
                double pos = sb.Dur - ms;
                if (pos <= 0) { Stop(sb); return; }
                Apply(sb, pos);
                return;
            }
            span = (double)sb.Dur * (sb.AutoRev ? 2 : 1);
            total = span * sb.Count;
            if (span <= 0) { ms = 0; done = true; }
            else if (sb.Forever)
            {
                if (ms >= span) { sb.T0 += Math.Floor(ms / span) * span; ms = ms % span; }
            }
            else if (ms >= total) { ms = span; done = true; }
            else ms = ms % span;
            Apply(sb, ms <= sb.Dur ? ms : span - ms);
            if (done) Completed(sb);
        }

        /// <summary>_RadFx.Begin: reduced motion jumps to the end; a delay shows the first frame, then waits</summary>
        void FxBegin(Sb sb)
        {
            if (reduced)
            {
                if (!sb.Playing) Forget(sb);
                Finish(sb);
                return;
            }
            if (!sb.Playing) Forget(sb);             // start from the values the control has now
            if (sb.Delay > 0)
            {
                Remember(sb);
                Apply(sb, 0);
                sb.Pending = true;
                if (sb.DelayTimer == null)
                {
                    var s0 = sb;
                    sb.DelayTimer = new Timer();
                    sb.DelayTimer.Tick += (s, a) => Guard(() =>
                    {
                        s0.DelayTimer.Stop();
                        if (s0.Pending) { s0.Pending = false; BeginNow(s0); }
                    });
                }
                sb.DelayTimer.Stop();
                sb.DelayTimer.Interval = Math.Max(1, sb.Delay);
                sb.DelayTimer.Start();
            }
            else BeginNow(sb);
        }

        void Reverse(Sb sb)
        {
            if (sb.Pending) { sb.DelayTimer.Stop(); sb.Pending = false; }
            if (reduced) { Stop(sb); return; }
            if (!sb.Saved) return;
            sb.Playing = true;
            sb.Rev = true;
            sb.T0 = Now() - (sb.Dur - (sb.Pos < sb.Dur ? sb.Pos : sb.Dur));
            FrameUpdate();
        }

        /// <summary>BeginAnimation / StopAnimation: a storyboard name or an animation id (fx1 = _fx_fx1)</summary>
        public int ByName(string name, bool stop)
        {
            int n = 0;
            var alt = "_fx_" + (name ?? "");
            foreach (var sb in sbs.ToList())
            {
                if (!Ieq(sb.Fx, name) && !Ieq(alt, sb.Fx)) continue;
                n++;
                if (stop)
                {
                    if (sb.EveryTimer != null) sb.EveryTimer.Stop();
                    sb.Hiding = false;
                    Stop(sb);
                }
                else FxBegin(sb);
            }
            return n;
        }

        void OnFrame()
        {
            foreach (var sb in sbs.ToList())
                if (sb.Playing) Tick(sb);
            FrameUpdate();
        }

        // ------------------------------------------------------------------ visual states
        bool HasStates(Control c) { return qs.Any(q => !q.Form && q.C == c); }

        Fl Flags(Control c, bool create)
        {
            Fl f;
            if (!fls.TryGetValue(c, out f) && create) { f = new Fl(); fls[c] = f; }
            return f;
        }

        void WantAdd(Control c, bool isForm, string st, List<KeyValuePair<string, string>> w)
        {
            foreach (var q in qs)
            {
                if (q.Form != isForm || (!isForm && q.C != c) || !Ieq(q.State, st)) continue;
                int j = w.FindIndex(x => Ieq(x.Key, q.Prop));
                var kv = new KeyValuePair<string, string>(q.Prop, q.Val);
                if (j < 0) w.Add(kv); else w[j] = kv;
            }
        }

        /// <summary>_VisualStates._update: the wanted overrides of a control (null = the form) are applied, the others given back</summary>
        void VsmUpdate(Control c)
        {
            var w = new List<KeyValuePair<string, string>>();
            var fl = c != null ? Flags(c, false) : null;
            if (state.Length > 0) WantAdd(c, c == null, state, w);
            if (c != null && fl != null)
            {
                if (fl.Manual.Length > 0) WantAdd(c, false, fl.Manual, w);
                else if ((fl.Flags & FDISABLED) != 0) WantAdd(c, false, "Disabled", w);
                else
                {
                    if ((fl.Flags & FFOCUSED) != 0) WantAdd(c, false, "Focused", w);
                    if ((fl.Flags & FOVER) != 0) WantAdd(c, false, "MouseOver", w);
                    if ((fl.Flags & FPRESSED) != 0) WantAdd(c, false, "Pressed", w);
                }
            }
            for (int i = 0; i < aps.Count;)             // overrides no longer wanted: the saved value back
            {
                var a = aps[i];
                if (a.C == c && !w.Any(x => Ieq(x.Key, a.Prop)))
                {
                    if (!(c != null && Ieq(a.Prop, "Opacity"))) SetStr(c, a.Prop, a.Saved);
                    aps.RemoveAt(i);
                    continue;
                }
                i++;
            }
            foreach (var kv in w)
            {
                var a = aps.FirstOrDefault(x => x.C == c && Ieq(x.Prop, kv.Key));
                if (a != null && a.Val == kv.Value) continue;
                if (a == null)
                {
                    a = new Ap { C = c, Prop = kv.Key, Saved = GetStr(c, kv.Key) };
                    aps.Add(a);
                }
                a.Val = kv.Value;
                if (!(c != null && Ieq(kv.Key, "Opacity"))) SetStr(c, kv.Key, kv.Value);
            }
        }

        void Flag(Control c, int flag, bool on)
        {
            if (c == null || !HasStates(c)) return;
            var fl = Flags(c, true);
            if (((fl.Flags & flag) != 0) == on) return;
            if (on) fl.Flags |= flag; else fl.Flags &= ~flag;
            VsmUpdate(c);
        }

        bool GoToState(Control c, string st)
        {
            var s = !string.IsNullOrEmpty(st) && !Ieq(st, "Base") ? st : "Normal";
            if (c != null)
            {
                Flags(c, true).Manual = Ieq(s, "Normal") ? "" : s;
                VsmUpdate(c);
                return true;
            }
            if (!Ieq(s, "Normal") && !qs.Any(q => Ieq(q.State, s))) return false;
            state = Ieq(s, "Normal") ? "" : s;
            VsmUpdate(null);
            foreach (var k2 in qs.Where(q => !q.Form).Select(q => q.C).Distinct().ToList()) VsmUpdate(k2);
            return true;
        }

        public bool GoToState(string st, string control)
        {
            Control t = null;
            if (!string.IsNullOrEmpty(control))
            {
                t = Ctl(control);
                if (t == null) return false;
            }
            return GoToState(t, st);
        }

        public string CurrentState { get { return state.Length > 0 ? state : "Normal"; } }

        // ------------------------------------------------------------------ layout variants
        static string PostureNorm(string s)
        {
            var b = new string((s ?? "").Where(ch => ch != '-' && ch != '_' && ch != ' ').ToArray()).ToLowerInvariant();
            switch (b)
            {
                case "halfopened": case "halfopen": case "half": case "tabletop": case "book": return "half-opened";
                case "folded": case "closed": case "fold": case "cover": return "folded";
                case "flat": case "open": case "opened": return "flat";
            }
            return "";
        }

        static void Venv(out string posture, out string span, out string fold)
        {
            posture = PostureNorm(Environment.GetEnvironmentVariable("RADIDE_POSTURE") ?? "");
            var sp = (Environment.GetEnvironmentVariable("RADIDE_SPAN") ?? "").Trim().ToLowerInvariant();
            span = sp == "dual" || sp == "2" || sp == "spanned" ? "dual" : sp.Length > 0 ? "single" : "";
            fold = "";
            var hx = (Environment.GetEnvironmentVariable("RADIDE_HINGE") ?? "").Split(',').Select(x => x.Trim()).ToArray();
            int[] h = new int[4];
            bool hinge = hx.Length == 4 && hx.Select((x, i) => int.TryParse(x, NumberStyles.Integer, CultureInfo.InvariantCulture, out h[i])).All(ok => ok);
            if (hinge && posture != "folded") fold = h[2] <= h[3] ? "vertical" : "horizontal";
            if (span.Length == 0)
                span = posture == "half-opened" || (hinge && posture != "folded" && Math.Min(h[2], h[3]) > 0) ? "dual" : "single";
        }

        static bool Match(VSize s, double w, double h, string posture, string span, string fold)
        {
            if (s.MnW >= 0 && w < s.MnW) return false;
            if (s.MxW >= 0 && w > s.MxW) return false;
            if (s.MnH >= 0 && h < s.MnH) return false;
            if (s.MxH >= 0 && h > s.MxH) return false;
            if (s.Orient.Length > 0 && !s.Orient.ToLowerInvariant().StartsWith(w > h ? "land" : "port")) return false;
            if (s.Posture.Length > 0 && s.Posture != posture) return false;
            if (s.Span.Length > 0 && s.Span != (span.Length > 0 ? span : "single")) return false;
            if (s.Fold.Length > 0 && s.Fold != fold) return false;
            return true;
        }

        /// <summary>the designed place of a control as x y w h rx ry rw rh (logical; rx = share of the container width)
        /// from its Anchor, like the IDE's place specs</summary>
        double[] BasePlace(Control c)
        {
            var p = c.Parent;
            double pw = p.ClientSize.Width / k, ph = p.ClientSize.Height / k;
            double x = c.Left / k, y = c.Top / k, w = c.Width / k, h = c.Height / k;
            var a = c.Anchor;
            var pl = new double[8];
            bool l = (a & AnchorStyles.Left) != 0, r = (a & AnchorStyles.Right) != 0, t = (a & AnchorStyles.Top) != 0, b = (a & AnchorStyles.Bottom) != 0;
            if (l && r) { pl[0] = x; pl[2] = w - pw; pl[6] = 1; }
            else if (r) { pl[0] = x - pw; pl[4] = 1; pl[2] = w; }
            else if (l) { pl[0] = x; pl[2] = w; }
            else { pl[0] = x - pw / 2; pl[4] = 0.5; pl[2] = w; }
            if (t && b) { pl[1] = y; pl[3] = h - ph; pl[7] = 1; }
            else if (b) { pl[1] = y - ph; pl[5] = 1; pl[3] = h; }
            else if (t) { pl[1] = y; pl[3] = h; }
            else { pl[1] = y - ph / 2; pl[5] = 0.5; pl[3] = h; }
            return pl;
        }

        void Place(Control c, double[] pl)
        {
            if (c.Parent == null) return;
            double cw = c.Parent.ClientSize.Width / k, ch = c.Parent.ClientSize.Height / k;
            c.SetBounds(Px(pl[0] + pl[4] * cw), Px(pl[1] + pl[5] * ch), Math.Max(0, Px(pl[2] + pl[6] * cw)), Math.Max(0, Px(pl[3] + pl[7] * ch)));
        }

        void Replace()
        {
            foreach (var kv in placed) Place(kv.Key, kv.Value);
        }

        /// <summary>_RadVariants.update: which sizes apply; restore the designed values, apply the sizes in order</summary>
        public bool Variants(bool notify)
        {
            if (sizes.Count == 0 || closed) return false;
            double cw = form.ClientPanel.ClientSize.Width / k, ch = form.ClientPanel.ClientSize.Height / k;
            if (cw <= 1 || ch <= 1) { cw = designW; ch = designH; }
            string posture, span, fold;
            Venv(out posture, out span, out fold);
            var now = sizes.Select(s => Match(s, cw, ch, posture, span, fold)).ToArray();
            if (hasCur && now.SequenceEqual(cur)) return false;
            bool first = !hasCur;
            cur = now;
            hasCur = true;
            quiet++;
            try
            {
                placed.Clear();
                foreach (var b in bases)
                {
                    if (b.C.Dock != b.Dock) b.C.Dock = b.Dock;
                    if (b.Dock != DockStyle.None) continue;
                    b.C.Anchor = AnchorStyles.Top | AnchorStyles.Left;
                    Place(b.C, b.Pl);
                    b.C.Anchor = b.Anchor;
                }
                foreach (var b in bps) SetStr(b.C, b.Prop, b.Val);
                for (int j = 0; j < sizes.Count; j++)
                {
                    if (!now[j]) continue;
                    foreach (var v in vls) if (v.Size == j) placed[v.C] = v.Pl;
                    foreach (var v in vps) if (v.Size == j && !Ieq(v.Prop, "Visible")) SetStr(v.C, v.Prop, v.Val);
                    foreach (var v in vps) if (v.Size == j && Ieq(v.Prop, "Visible")) SetStr(v.C, v.Prop, v.Val);
                }
                foreach (var kv in placed)            // the size's place replaces the control's anchor layout
                {
                    if (kv.Key.Dock != DockStyle.None) kv.Key.Dock = DockStyle.None;
                    kv.Key.Anchor = AnchorStyles.Top | AnchorStyles.Left;
                    Place(kv.Key, kv.Value);
                }
            }
            finally { quiet--; }
            if (!first && notify) Fire(form.RadName, "SizeVariantChanged");
            return true;
        }

        public string CurrentSizes
        {
            get
            {
                var ids = new List<string>();
                for (int i = 0; i < sizes.Count && i < cur.Length; i++) if (cur[i]) ids.Add(sizes[i].Id);
                return string.Join(",", ids.ToArray());
            }
        }

        // ------------------------------------------------------------------ triggers and automatic states
        void Hook(Control c, string name, Control target, bool states)
        {
            c.Click += (s, a) => Guard(() => Event(name, target, "Click"));
            c.MouseEnter += (s, a) => Guard(() => Event(name, target, "MouseEnter"));
            c.MouseLeave += (s, a) => Guard(() => Event(name, target, "MouseLeave"));
            c.MouseDown += (s, a) => Guard(() => Event(name, target, "MouseDown"));
            c.MouseUp += (s, a) => Guard(() => Event(name, target, "MouseUp"));
            c.GotFocus += (s, a) => Guard(() => Event(name, target, "GotFocus"));
            c.LostFocus += (s, a) => Guard(() => Event(name, target, "LostFocus"));
            if (states && target != null)
                c.EnabledChanged += (s, a) => Guard(() => { if (quiet == 0) Flag(target, FDISABLED, !target.Enabled); });
        }

        void Event(string obj, Control c, string ev)
        {
            if (ev == "Click" || ev == "MouseEnter" || ev == "MouseLeave")
            {
                foreach (var sb in sbs.ToList())
                {
                    if (!Ieq(sb.Src, obj) && !(c == null && sb.Src.Length == 0)) continue;
                    if (sb.On == TCLICK && ev == "Click") FxBegin(sb);
                    else if (sb.On == THOVER && ev == "MouseEnter") FxBegin(sb);
                    else if (sb.On == THOVER && ev == "MouseLeave")
                    {
                        if (sb.Leave == 0) Reverse(sb);
                        else if (sb.Leave == 1) { sb.Hiding = false; Stop(sb); }
                    }
                }
            }
            if (c == null) return;
            switch (ev)
            {
                case "MouseEnter": Flag(c, FOVER, true); break;
                case "MouseLeave": Flag(c, FPRESSED, false); Flag(c, FOVER, false); break;
                case "MouseDown": Flag(c, FPRESSED, true); break;
                case "MouseUp": Flag(c, FPRESSED, false); break;
                case "GotFocus": Flag(c, FFOCUSED, true); break;
                case "LostFocus": Flag(c, FFOCUSED, false); break;
            }
        }

        /// <summary>the form is shown for the first time (after &lt;Form&gt;_Load): "On load" begins, "On timer" timers start</summary>
        public void Start()
        {
            if (started || closed) return;
            started = true;
            Guard(() =>
            {
                foreach (var sb in sbs.ToList())
                {
                    if (sb.On == TLOAD) FxBegin(sb);
                    else if (sb.On == TTIMER && sb.Interval > 0)
                    {
                        var s0 = sb;
                        sb.EveryTimer = new Timer { Interval = sb.Interval };
                        sb.EveryTimer.Tick += (s, a) => Guard(() => FxBegin(s0));
                        sb.EveryTimer.Start();
                    }
                }
            });
        }

        /// <summary>Visible set by the program: "On show" / "On hide" play (true = handled here; hide ends hidden)</summary>
        public bool SetHook(Control c, bool on)
        {
            if (closed || quiet > 0 || c == null) return false;
            if (on == RadApp.IsShown(c)) return false;
            var list = sbs.Where(s => s.C == c && s.On == (on ? TSHOW : THIDE)).ToList();
            if (list.Count == 0) return false;
            Guard(() =>
            {
                if (on) SetBool(c, "Visible", true);
                foreach (var sb in list)
                {
                    if (!on) sb.Hiding = true;
                    FxBegin(sb);
                }
            });
            return true;
        }

        // ------------------------------------------------------------------ the program API (RadApp.CallMethod / GetProp)
        static RadFormBase FormFor(object o, out Control ctl)
        {
            ctl = null;
            var f = o as RadFormBase;
            if (f != null) return f;
            ctl = o as Control;
            return ctl != null ? ctl.FindForm() as RadFormBase : null;
        }

        public static bool TryCall(object o, string method, string[] args, out string r)
        {
            r = null;
            var m = (method ?? "").Trim().ToLowerInvariant();
            if (m != "beginanimation" && m != "stopanimation" && m != "gotostate" && m != "applysizevariants" && m != "currentsizes" && m != "currentstate")
                return false;
            Control ctl;
            var f = FormFor(o, out ctl);
            if (f == null) return false;
            var mo = f.Motion;
            Func<int, string> A = i => args != null && i < args.Length ? args[i] ?? "" : "";
            switch (m)
            {
                case "beginanimation":
                case "stopanimation":
                    r = mo != null && mo.ByName(A(0), m == "stopanimation") > 0 ? "True" : "False";
                    return true;
                case "gotostate":
                    if (mo == null) r = "False";
                    else if (ctl != null) r = mo.GoToState(ctl, A(0)) ? "True" : "False";
                    else r = mo.GoToState(A(0), A(1)) ? "True" : "False";
                    return true;
            }
            if (ctl != null) return false;
            switch (m)
            {
                case "applysizevariants": r = mo != null && mo.Variants(true) ? "True" : "False"; return true;
                case "currentsizes": r = mo != null ? mo.CurrentSizes : ""; return true;
                default: r = mo != null ? mo.CurrentState : "Normal"; return true;
            }
        }

        public static bool TryGet(object o, string prop, out string r)
        {
            r = null;
            var p = (prop ?? "").Trim();
            if (!Ieq(p, "CurrentSizes") && !Ieq(p, "CurrentState")) return false;
            return o is RadFormBase && TryCall(o, p, null, out r);
        }
    }

    /// <summary>A common dialog (OpenFileDialog ...) with the IDE's properties: ShowDialog() -> "OK"/"Cancel".</summary>
    public sealed class RadDialog
    {
        public string Kind;
        public string Title = "", Filter = "All files|*.*", FileName = "", InitialDirectory = "", Color = "#000000",
            FontName = "Segoe UI", SelectedPath = "";
        public float FontSize = 9;

        public string ShowDialog(IWin32Window owner)
        {
            DialogResult r;
            switch (Kind)
            {
                case "OpenFileDialog":
                case "SaveFileDialog":
                    using (FileDialog d = Kind == "OpenFileDialog" ? (FileDialog)new OpenFileDialog() : new SaveFileDialog())
                    {
                        d.Title = Title; d.FileName = FileName; d.InitialDirectory = InitialDirectory;
                        try { d.Filter = Filter; } catch (ArgumentException) { d.Filter = "All files|*.*"; }
                        r = d.ShowDialog(owner);
                        if (r == DialogResult.OK) FileName = d.FileName;
                    }
                    break;
                case "ColorDialog":
                    using (var d = new ColorDialog())
                    {
                        try { d.Color = ColorTranslator.FromHtml(Color); } catch (Exception) { }
                        r = d.ShowDialog(owner);
                        if (r == DialogResult.OK) Color = "#" + d.Color.R.ToString("X2") + d.Color.G.ToString("X2") + d.Color.B.ToString("X2");
                    }
                    break;
                case "FontDialog":
                    using (var d = new FontDialog())
                    {
                        try { d.Font = new Font(FontName, FontSize); } catch (Exception) { }
                        r = d.ShowDialog(owner);
                        if (r == DialogResult.OK) { FontName = d.Font.Name; FontSize = d.Font.SizeInPoints; }
                    }
                    break;
                default:
                    using (var d = new FolderBrowserDialog())
                    {
                        d.SelectedPath = SelectedPath; d.Description = Title;
                        r = d.ShowDialog(owner);
                        if (r == DialogResult.OK) SelectedPath = d.SelectedPath;
                    }
                    break;
            }
            return r == DialogResult.OK ? "OK" : "Cancel";
        }
    }

    /// <summary>The program: forms, handlers and the VB-style property protocol.</summary>
    public static class RadApp
    {
        public static string Title = "";
        public static IHandlers Handlers;
        public static bool Ending;
        static readonly Dictionary<string, Func<RadFormBase>> factories = new Dictionary<string, Func<RadFormBase>>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<string, RadFormBase> forms = new Dictionary<string, RadFormBase>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<object, string> tags = new Dictionary<object, string>();
        static readonly Dictionary<object, bool> shown = new Dictionary<object, bool>();
        static RadFormBase startup;
        /// <summary>optional observer (test builds): every fired event</summary>
        public static Action<string> Trace;

        public static void Register(string name, Func<RadFormBase> make) { factories[name] = make; }

        public static bool IsStartup(RadFormBase f) { return ReferenceEquals(f, startup); }

        public static bool Has(string handler) { return Handlers != null && Handlers.Has(handler); }

        public static string Res(string file)
        {
            if (string.IsNullOrEmpty(file) || System.IO.Path.IsPathRooted(file)) return file;
            return System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, file);
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        static extern bool SetProcessDPIAware();

        public static int Run(string startupForm)
        {
            try { if (Environment.OSVersion.Version.Major >= 6) SetProcessDPIAware(); } catch (Exception) { }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.ThreadException += (s, a) => ReportError("", a.Exception);
            WaitForDebugger();
            startup = GetForm(startupForm);
            Application.Run(startup);
            return 0;
        }

        /// <summary>F5 in the IDE (radide/dotnet/native_run.py) with breakpoints: RAD_WAIT_GO=1, the IDE attaches
        /// netcoredbg, sets the breakpoints and then writes "go" on stdin - only then the forms are created (Form_Load).</summary>
        static void WaitForDebugger()
        {
            if (Environment.GetEnvironmentVariable("RAD_WAIT_GO") != "1") return;
            try { Console.In.ReadLine(); } catch (Exception) { }
        }

        public static RadFormBase GetForm(string name)
        {
            RadFormBase f;
            if (forms.TryGetValue(name, out f) && !f.IsDisposed) return f;
            Func<RadFormBase> make;
            if (!factories.TryGetValue(name, out make)) return null;
            f = make();
            forms[name] = f;
            return f;
        }

        public static void Fire(string owner, string ev, RadEvent e)
        {
            var name = owner + "_" + ev;
            if (Trace != null) Trace(name);
            if (Handlers == null || !Handlers.Has(name)) return;
            if (e == null) e = new RadEvent { Sender = owner, Name = ev };
            try { Handlers.Invoke(name, e); }
            catch (Exception ex) { ReportError(name, ex); }
        }

        public static void ReportError(string where, Exception ex)
        {
            var msg = (string.IsNullOrEmpty(where) ? "" : "Error in " + where + ": ") + ex.GetType().Name + ": " + ex.Message;
            try { Console.Error.WriteLine(msg); } catch (Exception) { }
            MessageBox.Show(msg, string.IsNullOrEmpty(Title) ? "Error" : Title, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        public static void End()
        {
            Ending = true;
            foreach (var f in forms.Values.ToList()) { try { f.Close(); } catch (Exception) { } }
            Application.Exit();
            Environment.Exit(0);
        }

        static IWin32Window Owner()
        {
            return Form.ActiveForm ?? (IWin32Window)startup;
        }

        public static int MsgBox(string text)
        {
            MessageBox.Show(Owner(), text, Title);
            return 1;
        }

        public static string InputBox(string prompt)
        {
            using (var f = new Form())
            {
                f.Text = Title; f.FormBorderStyle = FormBorderStyle.FixedDialog; f.MinimizeBox = false; f.MaximizeBox = false;
                f.StartPosition = FormStartPosition.CenterParent; f.ShowInTaskbar = false; f.Font = new Font("Segoe UI", 9F);
                f.ClientSize = new Size(360, 120);
                var l = new Label { Text = prompt, Left = 10, Top = 10, Width = 340, Height = 40 };
                var t = new TextBox { Left = 10, Top = 55, Width = 340, Name = "txtInput" };
                var ok = new Button { Text = "OK", Left = 194, Top = 86, Width = 75, DialogResult = DialogResult.OK, Name = "btnOK" };
                var cancel = new Button { Text = "Cancel", Left = 275, Top = 86, Width = 75, DialogResult = DialogResult.Cancel, Name = "btnCancel" };
                f.Controls.AddRange(new Control[] { l, t, ok, cancel });
                f.AcceptButton = ok; f.CancelButton = cancel;
                return f.ShowDialog(Owner()) == DialogResult.OK ? t.Text : "";
            }
        }

        public static void ShowForm(string path, bool show)
        {
            var target = Resolve(path);
            if (target is Form) { var f = (Form)target; if (show) { f.Show(); f.Activate(); } else f.Hide(); }
            else if (target != null) SetProp(path, "visible", show ? "True" : "False");
        }

        // ------------------------------------------------------------------ objects
        /// <summary>"Form1", "Form1.lblOut" or "lblOut" (searched in the loaded forms).</summary>
        public static object Resolve(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var parts = path.Split('.');
            if (factories.ContainsKey(parts[0]))
            {
                var f = GetForm(parts[0]);
                if (parts.Length == 1) return f;
                object it;
                return f != null && f.Items.TryGetValue(parts[1], out it) ? it : null;
            }
            foreach (var f in forms.Values)
            {
                object it;
                if (f.Items.TryGetValue(parts[0], out it)) return it;
            }
            foreach (var n in factories.Keys.ToList())       // a control of a form that was not created yet
            {
                var f = GetForm(n);
                object it;
                if (f != null && f.Items.TryGetValue(parts[0], out it)) return it;
            }
            return null;
        }

        static RadFormBase FormOf(object o)
        {
            var c = o as Control;
            return c == null ? null : c.FindForm() as RadFormBase;
        }

        static string Num(double d) { return d.ToString(CultureInfo.InvariantCulture); }
        static string B(bool b) { return b ? "True" : "False"; }

        static Color ToColor(string v)
        {
            v = (v ?? "").Trim();
            if (v.Length == 0) return Color.Empty;
            if (v.StartsWith("#")) { try { return ColorTranslator.FromHtml(v); } catch (Exception) { return Color.Empty; } }
            double d;
            if (double.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out d))
            {
                long n = (long)d;
                if ((n & 0x80000000L) != 0) { try { return ColorTranslator.FromOle((int)n); } catch (Exception) { return Color.Empty; } }
                return Color.FromArgb((int)(n & 0xFF), (int)((n >> 8) & 0xFF), (int)((n >> 16) & 0xFF));
            }
            try { return Color.FromName(v); } catch (Exception) { return Color.Empty; }
        }

        static string FromColor(Color c) { return ColorTranslator.ToOle(c).ToString(CultureInfo.InvariantCulture); }

        public static bool IsShown(object o)
        {
            bool v;
            return !shown.TryGetValue(o, out v) || v;
        }

        /// <summary>Visible of a control without the "On show" / "On hide" animations (RadMotion's own writes)</summary>
        public static void SetVisibleRaw(Control c, bool v)
        {
            shown[c] = v;
            c.Visible = v;
        }

        /// <summary>Visible set by the program: a control with "On show" / "On hide" animations plays them</summary>
        static void SetVisible(object o, bool v)
        {
            var c = o as Control;
            if (c != null && !(c is Form))
            {
                var f = FormOf(c);
                if (f != null && f.Motion != null && f.Motion.SetHook(c, v)) return;
            }
            Set(o, "visible", v ? "True" : "False");
        }

        /// <summary>a property of an object (no path; RadMotion): library controls first, then the common ones</summary>
        public static string GetOn(object o, string prop)
        {
            try
            {
                string r;
                if (Ext.TryGet(o, prop, out r)) return r;
                return Get(o, o is Control ? ((Control)o).Name : "", (prop ?? "").Trim().ToLowerInvariant());
            }
            catch (Exception ex) { Warn(prop + ": " + ex.Message); return ""; }
        }

        public static void SetOn(object o, string prop, string value)
        {
            try
            {
                if (Ext.TrySet(o, prop, value ?? "")) return;
                Set(o, (prop ?? "").Trim().ToLowerInvariant(), value ?? "");
            }
            catch (Exception ex) { Warn(prop + ": " + ex.Message); }
        }

        /// <summary>a control that is hidden at design time (Visible = False)</summary>
        public static void MarkHidden(object o) { shown[o] = false; }

        public static string GetProp(string path, string prop)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return ""; }
            try
            {
                string r;
                if (RadMotion.TryGet(o, prop, out r)) return r;           // CurrentSizes / CurrentState
                if (Ext.TryGet(o, prop, out r)) return r;
                return Get(o, path, (prop ?? "").Trim().ToLowerInvariant());
            }
            catch (Exception ex) { Warn(path + "." + prop + ": " + ex.Message); return ""; }
        }

        public static void SetProp(string path, string prop, string value)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return; }
            try
            {
                if (string.Equals((prop ?? "").Trim(), "visible", StringComparison.OrdinalIgnoreCase) && o is Control && !(o is Form))
                {
                    var f = FormOf(o);
                    if (f != null && f.Motion != null && f.Motion.SetHook((Control)o, Rad.ToBool(value))) return;
                }
                if (Ext.TrySet(o, prop, value ?? "")) return;
                Set(o, (prop ?? "").Trim().ToLowerInvariant(), value ?? "");
            }
            catch (Exception ex) { Warn(path + "." + prop + ": " + ex.Message); }
        }

        public static string CallMethod(string path, string method, string[] args)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return ""; }
            try
            {
                string r;
                // BeginAnimation StopAnimation GoToState ApplySizeVariants CurrentSizes CurrentState
                if (RadMotion.TryCall(o, method, args ?? new string[0], out r)) return r;
                if (Ext.TryCall(o, method, args ?? new string[0], out r)) return r;
                return Call(o, path, (method ?? "").Trim().ToLowerInvariant(), args ?? new string[0]);
            }
            catch (Exception ex) { Warn(path + "." + method + ": " + ex.Message); return ""; }
        }

        static void Warn(string msg)
        {
            try { Console.Error.WriteLine("[rad] " + msg); } catch (Exception) { }
        }

        /// <summary>Objects of control libraries (RadIDE.Controls ...) answer the property protocol themselves through
        /// public RadGet(prop) / RadSet(prop, value) / RadCall(method, args) methods (found by reflection, no reference
        /// needed); null / false = not handled (the common properties below still apply). The form property Theme goes
        /// to RadIDE.Controls.RmThemeManager when the library is part of the program.</summary>
        static class Ext
        {
            static readonly Dictionary<Type, MethodInfo[]> cache = new Dictionary<Type, MethodInfo[]>();

            static MethodInfo[] Of(object o)
            {
                MethodInfo[] m;
                var t = o.GetType();
                if (!cache.TryGetValue(t, out m))
                {
                    m = new[] { t.GetMethod("RadGet", new[] { typeof(string) }), t.GetMethod("RadSet", new[] { typeof(string), typeof(string) }),
                                t.GetMethod("RadCall", new[] { typeof(string), typeof(string[]) }) };
                    cache[t] = m;
                }
                return m;
            }

            static object Inv(MethodInfo m, object o, object[] a)
            {
                try { return m.Invoke(o, a); }
                catch (TargetInvocationException ex) { throw ex.InnerException ?? ex; }
            }

            public static bool TryGet(object o, string prop, out string r)
            {
                r = null;
                if (o is Form && string.Equals(prop, "Theme", StringComparison.OrdinalIgnoreCase)) { r = ThemeCall("CurrentName", null) as string ?? "Light"; return true; }
                var m = Of(o)[0];
                if (m == null) return false;
                r = Inv(m, o, new object[] { prop }) as string;
                return r != null;
            }

            public static bool TrySet(object o, string prop, string value)
            {
                if (o is Form && (string.Equals(prop, "Theme", StringComparison.OrdinalIgnoreCase) || string.Equals(prop, "AccentColor", StringComparison.OrdinalIgnoreCase)))
                {
                    if (string.Equals(prop, "Theme", StringComparison.OrdinalIgnoreCase)) return ThemeCall("ApplyFormTheme", new object[] { o, value }) != null || ThemeType() != null;
                    var t = ThemeType();
                    if (t == null) return false;
                    var p = t.GetProperty("AccentColor");
                    var c = ToColor(value);
                    p.SetValue(null, c, null);
                    return true;
                }
                if (o is Form && string.Equals(prop, "RightToLeft", StringComparison.OrdinalIgnoreCase))
                {
                    var f = (Form)o;
                    var rtl = Rad.ToBool(value) || value.Trim().Equals("Yes", StringComparison.OrdinalIgnoreCase) ? RightToLeft.Yes : RightToLeft.No;
                    if (f.RightToLeft != rtl)
                    {
                        f.RightToLeft = rtl;
                        MirrorLayout(f);
                    }
                    return true;
                }
                var m = Of(o)[1];
                if (m == null) return false;
                var res = Inv(m, o, new object[] { prop, value });
                return res is bool && (bool)res;
            }

            public static bool TryCall(object o, string method, string[] args, out string r)
            {
                r = null;
                var m = Of(o)[2];
                if (m == null) return false;
                r = Inv(m, o, new object[] { method, args }) as string;
                return r != null;
            }

            static Type themeType;
            static bool themeLooked;

            static Type ThemeType()
            {
                if (themeLooked) return themeType;
                themeLooked = true;
                foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    var t = a.GetType("RadIDE.Controls.RmThemeManager", false);
                    if (t != null) { themeType = t; break; }
                }
                return themeType;
            }

            static object ThemeCall(string member, object[] args)
            {
                var t = ThemeType();
                if (t == null) return null;
                if (args == null) { var p = t.GetProperty(member); return p != null ? p.GetValue(null, null) : null; }
                var m = t.GetMethod(member);
                if (m == null) return null;
                m.Invoke(null, args);
                return true;
            }
        }

        /// <summary>Right-to-left forms (Arabic): the layout is mirrored - Left = width - Right, Dock and Anchor Left/Right
        /// swapped - for every control, recursively (controls that place their children themselves, such as the pages of
        /// a tab strip, have a RadNoMirror property and only their children are mirrored).</summary>
        public static void MirrorLayout(Control root)
        {
            var f = root as RadFormBase;
            var host = f != null ? (Control)f.ClientPanel : root;
            host.SuspendLayout();
            foreach (Control c in host.Controls) Mirror(c, host);
            host.ResumeLayout(true);
        }

        static void Mirror(Control c, Control parent)
        {
            bool self = c.GetType().GetProperty("RadNoMirror") != null;
            if (!self)
            {
                if (c.Dock == DockStyle.Left) c.Dock = DockStyle.Right;
                else if (c.Dock == DockStyle.Right) c.Dock = DockStyle.Left;
                else if (c.Dock == DockStyle.None)
                {
                    var a = c.Anchor;
                    bool l = (a & AnchorStyles.Left) != 0, r = (a & AnchorStyles.Right) != 0;
                    if (l != r) c.Anchor = (a & ~(AnchorStyles.Left | AnchorStyles.Right)) | (l ? AnchorStyles.Right : AnchorStyles.Left);
                    c.Left = parent.ClientSize.Width - c.Right;
                }
            }
            if (c.Controls.Count > 0)
            {
                c.SuspendLayout();
                foreach (Control k in c.Controls) Mirror(k, c);
                c.ResumeLayout(true);
            }
        }

        /// <summary>netfx builds embed referenced control libraries as resources "radlib.&lt;Name&gt;.dll" (one exe);
        /// they are loaded from there when the runtime asks for them.</summary>
        public static void LoadEmbedded()
        {
            var exe = Assembly.GetEntryAssembly() ?? typeof(RadApp).Assembly;     // the program (RadIDE.Runtime.dll: not this)
            if (!exe.GetManifestResourceNames().Any(n => n.StartsWith("radlib.", StringComparison.Ordinal))) return;
            var loaded = new Dictionary<string, Assembly>(StringComparer.OrdinalIgnoreCase);
            AppDomain.CurrentDomain.AssemblyResolve += (s, a) =>
            {
                var name = new AssemblyName(a.Name).Name;
                Assembly asm;
                if (loaded.TryGetValue(name, out asm)) return asm;
                using (var st = exe.GetManifestResourceStream("radlib." + name + ".dll"))
                {
                    if (st == null) return null;
                    var ms = new MemoryStream();
                    st.CopyTo(ms);
                    asm = Assembly.Load(ms.ToArray());
                }
                loaded[name] = asm;
                return asm;
            };
        }

        static string Get(object o, string path, string p)
        {
            var timer = o as Timer;
            if (timer != null)
            {
                if (p == "interval") return timer.Interval.ToString(CultureInfo.InvariantCulture);
                if (p == "enabled") return B(timer.Enabled);
                if (p == "name") return path.Split('.').Last();
                return "";
            }
            var dlg = o as RadDialog;
            if (dlg != null)
            {
                switch (p)
                {
                    case "filename": return dlg.FileName;
                    case "title": return dlg.Title;
                    case "filter": return dlg.Filter;
                    case "initialdirectory": return dlg.InitialDirectory;
                    case "color": return dlg.Color;
                    case "fontname": return dlg.FontName;
                    case "fontsize": return Num(dlg.FontSize);
                    case "selectedpath": return dlg.SelectedPath;
                }
                return "";
            }
            var mi = o as ToolStripMenuItem;
            if (mi != null)
            {
                if (p == "text" || p == "caption") return mi.Text;
                if (p == "enabled") return B(mi.Enabled);
                if (p == "visible") return B(mi.Available);
                if (p == "checked" || p == "value") return B(mi.Checked);
                if (p == "name") return mi.Name;
                return "";
            }
            var c = (Control)o;
            string tag;
            switch (p)
            {
                case "name": return c is RadFormBase ? ((RadFormBase)c).RadName : c.Name;
                case "tag": return tags.TryGetValue(o, out tag) ? tag : "";
                case "caption":
                case "text":
                    if (c is ListBox) { var lb = (ListBox)c; return lb.SelectedIndex >= 0 ? Convert.ToString(lb.Items[lb.SelectedIndex], CultureInfo.InvariantCulture) : ""; }
                    if (c is TabControl) { var tc = (TabControl)c; return tc.SelectedTab != null ? tc.SelectedTab.Text : ""; }
                    if (c is NumericUpDown) return Num((double)((NumericUpDown)c).Value);
                    if (c is TrackBar) return Num(((TrackBar)c).Value);
                    if (c is ProgressBar) return Num(((ProgressBar)c).Value);
                    return c.Text;
                case "value":
                    if (c is CheckBox) return ((CheckBox)c).Checked ? "1" : "0";
                    if (c is RadioButton) return B(((RadioButton)c).Checked);
                    if (c is NumericUpDown) return Num((double)((NumericUpDown)c).Value);
                    if (c is TrackBar) return Num(((TrackBar)c).Value);
                    if (c is ProgressBar) return Num(((ProgressBar)c).Value);
                    if (c is DateTimePicker) return ((DateTimePicker)c).Value.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
                    if (c is TabControl) return Num(((TabControl)c).SelectedIndex);
                    return c.Text;
                case "checked":
                    if (c is CheckBox) return B(((CheckBox)c).Checked);
                    if (c is RadioButton) return B(((RadioButton)c).Checked);
                    return "False";
                case "min":
                case "minimum":
                    if (c is NumericUpDown) return Num((double)((NumericUpDown)c).Minimum);
                    if (c is TrackBar) return Num(((TrackBar)c).Minimum);
                    if (c is ProgressBar) return Num(((ProgressBar)c).Minimum);
                    return "0";
                case "max":
                case "maximum":
                    if (c is NumericUpDown) return Num((double)((NumericUpDown)c).Maximum);
                    if (c is TrackBar) return Num(((TrackBar)c).Maximum);
                    if (c is ProgressBar) return Num(((ProgressBar)c).Maximum);
                    return "0";
                case "left": return Num(c is Form ? ((Form)c).Left : c.Left);
                case "top": return Num(c is Form ? ((Form)c).Top : c.Top);
                case "width": return Num(c is RadFormBase ? ((Form)c).ClientSize.Width : c.Width);
                case "height": return Num(c is RadFormBase ? ((RadFormBase)c).ClientHeight() : c.Height);
                case "enabled": return B(c.Enabled);
                case "visible": return B(IsShown(o));
                case "backcolor": return FromColor(c.BackColor);
                case "forecolor": return FromColor(c.ForeColor);
                case "listcount":
                    if (c is ListBox) return Num(((ListBox)c).Items.Count);
                    if (c is ComboBox) return Num(((ComboBox)c).Items.Count);
                    if (c is TabControl) return Num(((TabControl)c).TabCount);
                    return "0";
                case "listindex":
                case "selectedindex":
                    if (c is ListBox) return Num(((ListBox)c).SelectedIndex);
                    if (c is ComboBox) return Num(((ComboBox)c).SelectedIndex);
                    if (c is TabControl) return Num(((TabControl)c).SelectedIndex);
                    return "-1";
                case "newindex":
                    return Num(Rad.ToInt(Get(o, path, "listcount")) - 1);
                case "tab": return c is TabControl ? Num(((TabControl)c).SelectedIndex) : "0";
                case "fontsize":
                case "size": return Num(c.Font.SizeInPoints);
                case "fontbold":
                case "bold": return B(c.Font.Bold);
                case "fontitalic":
                case "italic": return B(c.Font.Italic);
                case "fontname": return c.Font.Name;
                case "tooltiptext":
                    {
                        var f = FormOf(c);
                        return f != null ? f.TipFor(c) : "";
                    }
                case "multiline": return B(c is TextBox && ((TextBox)c).Multiline);
                case "locked":
                case "readonly": return B(c is TextBox && ((TextBox)c).ReadOnly);
                case "hwnd": return c.Handle.ToInt64().ToString(CultureInfo.InvariantCulture);
                case "selstart": return c is TextBox ? Num(((TextBox)c).SelectionStart) : "0";
                case "sellength": return c is TextBox ? Num(((TextBox)c).SelectionLength) : "0";
                case "seltext": return c is TextBox ? ((TextBox)c).SelectedText : "";
                case "windowstate": return c is Form ? ((Form)c).WindowState.ToString() : "";
                case "opacity": return c is Form ? Num(((Form)c).Opacity) : "1";
            }
            Warn("Object doesn't support property '" + p + "' (" + path + ")");
            return "";
        }

        static void Set(object o, string p, string v)
        {
            var timer = o as Timer;
            if (timer != null)
            {
                if (p == "interval") { var i = Rad.ToInt(v); timer.Interval = i > 0 ? i : 1; }
                else if (p == "enabled") timer.Enabled = Rad.ToBool(v);
                return;
            }
            var dlg = o as RadDialog;
            if (dlg != null)
            {
                switch (p)
                {
                    case "filename": dlg.FileName = v; break;
                    case "title": dlg.Title = v; break;
                    case "filter": dlg.Filter = v; break;
                    case "initialdirectory": dlg.InitialDirectory = v; break;
                    case "color": dlg.Color = v; break;
                    case "fontname": dlg.FontName = v; break;
                    case "fontsize": dlg.FontSize = (float)Rad.ToNumber(v); break;
                    case "selectedpath": dlg.SelectedPath = v; break;
                }
                return;
            }
            var mi = o as ToolStripMenuItem;
            if (mi != null)
            {
                if (p == "text" || p == "caption") mi.Text = v;
                else if (p == "enabled") mi.Enabled = Rad.ToBool(v);
                else if (p == "visible") mi.Available = Rad.ToBool(v);
                else if (p == "checked" || p == "value") mi.Checked = Rad.ToBool(v);
                return;
            }
            var c = (Control)o;
            switch (p)
            {
                case "tag": tags[o] = v; return;
                case "caption":
                case "text":
                    if (c is ListBox)
                    {
                        var lb = (ListBox)c;
                        var i = lb.FindStringExact(v);
                        if (i >= 0) lb.SelectedIndex = i;
                        return;
                    }
                    if (c is NumericUpDown || c is TrackBar || c is ProgressBar) { Set(o, "value", v); return; }
                    if (c is TextBox && ((TextBox)c).Multiline) v = v.Replace("\r\n", "\n").Replace("\n", "\r\n");
                    c.Text = v;
                    return;
                case "value":
                    if (c is CheckBox) { var cb = (CheckBox)c; cb.Checked = Rad.ToBool(v) || v.Trim() == "1"; return; }
                    if (c is RadioButton) { if (Rad.ToBool(v)) ((RadioButton)c).Checked = true; return; }
                    if (c is NumericUpDown) { var n = (NumericUpDown)c; n.Value = Math.Max(n.Minimum, Math.Min(n.Maximum, (decimal)Rad.ToNumber(v))); return; }
                    if (c is TrackBar) { var t = (TrackBar)c; t.Value = Math.Max(t.Minimum, Math.Min(t.Maximum, Rad.ToInt(v))); return; }
                    if (c is ProgressBar) { var pb = (ProgressBar)c; pb.Value = Math.Max(pb.Minimum, Math.Min(pb.Maximum, Rad.ToInt(v))); return; }
                    if (c is DateTimePicker) { DateTime d; if (DateTime.TryParse(v, CultureInfo.InvariantCulture, DateTimeStyles.None, out d)) ((DateTimePicker)c).Value = d; return; }
                    if (c is TabControl) { Set(o, "selectedindex", v); return; }
                    c.Text = v;
                    return;
                case "checked":
                    if (c is CheckBox) ((CheckBox)c).Checked = Rad.ToBool(v);
                    else if (c is RadioButton) ((RadioButton)c).Checked = Rad.ToBool(v);
                    return;
                case "min":
                case "minimum":
                    if (c is NumericUpDown) ((NumericUpDown)c).Minimum = (decimal)Rad.ToNumber(v);
                    else if (c is TrackBar) ((TrackBar)c).Minimum = Rad.ToInt(v);
                    else if (c is ProgressBar) ((ProgressBar)c).Minimum = Rad.ToInt(v);
                    return;
                case "max":
                case "maximum":
                    if (c is NumericUpDown) ((NumericUpDown)c).Maximum = (decimal)Rad.ToNumber(v);
                    else if (c is TrackBar) ((TrackBar)c).Maximum = Rad.ToInt(v);
                    else if (c is ProgressBar) ((ProgressBar)c).Maximum = Rad.ToInt(v);
                    return;
                case "left": c.Left = Rad.ToInt(v); return;
                case "top": c.Top = Rad.ToInt(v); return;
                case "width":
                    if (c is RadFormBase) ((Form)c).ClientSize = new Size(Rad.ToInt(v), ((Form)c).ClientSize.Height); else c.Width = Rad.ToInt(v);
                    return;
                case "height":
                    if (c is RadFormBase) ((RadFormBase)c).SetClientHeight(Rad.ToInt(v)); else c.Height = Rad.ToInt(v);
                    return;
                case "enabled": c.Enabled = Rad.ToBool(v); return;
                case "visible":
                    if (c is Form) { if (Rad.ToBool(v)) ((Form)c).Show(); else ((Form)c).Hide(); return; }
                    shown[o] = Rad.ToBool(v);
                    c.Visible = Rad.ToBool(v);
                    return;
                case "backcolor": { var col = ToColor(v); if (c is RadFormBase) ((RadFormBase)c).SetBack(col); else c.BackColor = col.IsEmpty ? SystemColors.Control : col; return; }
                case "forecolor": { var col = ToColor(v); c.ForeColor = col.IsEmpty ? SystemColors.ControlText : col; return; }
                case "listindex":
                case "selectedindex":
                case "tab":
                    {
                        var i = Rad.ToInt(v);
                        if (c is ListBox) ((ListBox)c).SelectedIndex = Math.Max(-1, Math.Min(((ListBox)c).Items.Count - 1, i));
                        else if (c is ComboBox) ((ComboBox)c).SelectedIndex = Math.Max(-1, Math.Min(((ComboBox)c).Items.Count - 1, i));
                        else if (c is TabControl && i >= 0 && i < ((TabControl)c).TabCount) ((TabControl)c).SelectedIndex = i;
                        return;
                    }
                case "fontsize": case "size": c.Font = new Font(c.Font.FontFamily, Math.Max(1f, (float)Rad.ToNumber(v)), c.Font.Style); return;
                case "fontname": try { c.Font = new Font(v, c.Font.SizeInPoints, c.Font.Style); } catch (ArgumentException) { } return;
                case "fontbold": case "bold": c.Font = new Font(c.Font, Rad.ToBool(v) ? c.Font.Style | FontStyle.Bold : c.Font.Style & ~FontStyle.Bold); return;
                case "fontitalic": case "italic": c.Font = new Font(c.Font, Rad.ToBool(v) ? c.Font.Style | FontStyle.Italic : c.Font.Style & ~FontStyle.Italic); return;
                case "tooltiptext": { var f = FormOf(c); if (f != null) f.SetTip(c, v); return; }
                case "locked":
                case "readonly": if (c is TextBox) ((TextBox)c).ReadOnly = Rad.ToBool(v); return;
                case "selstart": if (c is TextBox) ((TextBox)c).SelectionStart = Rad.ToInt(v); return;
                case "sellength": if (c is TextBox) ((TextBox)c).SelectionLength = Rad.ToInt(v); return;
                case "seltext": if (c is TextBox) ((TextBox)c).SelectedText = v; return;
                case "picture":
                case "image":
                    if (c is PictureBox) { try { ((PictureBox)c).Image = v.Length == 0 ? null : Image.FromFile(Res(v)); } catch (Exception ex) { Warn(ex.Message); } }
                    return;
                case "windowstate":
                    if (c is Form) ((Form)c).WindowState = v.ToLowerInvariant().StartsWith("max") ? FormWindowState.Maximized : v.ToLowerInvariant().StartsWith("min") ? FormWindowState.Minimized : FormWindowState.Normal;
                    return;
                case "tabindex": c.TabIndex = Rad.ToInt(v); return;
                case "opacity":
                    if (c is Form) { var op = Rad.ToNumber(v); ((Form)c).Opacity = op < 0 ? 0 : op > 1 ? 1 : op; }
                    return;           // child controls have no transparency
                case "sellengthall": return;
                case "tabstop": case "mousepointer": case "default": case "cancel": case "appearance": case "borderstyle":
                case "sorted": case "alignment": case "autosize": case "wordwrap":
                    return;           // accepted but not applicable (like the GUI Bridge)
            }
            Warn("Object doesn't support property '" + p + "'");
        }

        static string Call(object o, string path, string m, string[] a)
        {
            Func<int, string> A = i => i < a.Length ? a[i] : "";
            var timer = o as Timer;
            if (timer != null)
            {
                if (m == "start") timer.Start();
                else if (m == "stop") timer.Stop();
                else return Get(o, path, m);
                return "";
            }
            var dlg = o as RadDialog;
            if (dlg != null)
            {
                if (m == "showdialog" || m == "show" || m == "showopen" || m == "showsave") return dlg.ShowDialog(Owner());
                return Get(o, path, m);
            }
            if (o is ToolStripMenuItem)
            {
                if (m == "performclick" || m == "click") ((ToolStripMenuItem)o).PerformClick();
                else return Get(o, path, m);
                return "";
            }
            var c = (Control)o;
            switch (m)
            {
                case "additem":
                    {
                        var item = A(0);
                        if (c is ListBox) { var it = ((ListBox)c).Items; if (a.Length > 1) it.Insert(Rad.ToInt(a[1]), item); else it.Add(item); }
                        else if (c is ComboBox) { var it = ((ComboBox)c).Items; if (a.Length > 1) it.Insert(Rad.ToInt(a[1]), item); else it.Add(item); }
                        return "";
                    }
                case "removeitem":
                    {
                        var i = Rad.ToInt(A(0));
                        if (c is ListBox) ((ListBox)c).Items.RemoveAt(i);
                        else if (c is ComboBox) ((ComboBox)c).Items.RemoveAt(i);
                        return "";
                    }
                case "clear":
                    if (c is ListBox) ((ListBox)c).Items.Clear();
                    else if (c is ComboBox) { ((ComboBox)c).Items.Clear(); ((ComboBox)c).Text = ""; }
                    else if (c is TextBox) c.Text = "";
                    return "";
                case "list":
                    {
                        var i = Rad.ToInt(A(0));
                        if (c is ListBox) return Convert.ToString(((ListBox)c).Items[i], CultureInfo.InvariantCulture);
                        if (c is ComboBox) return Convert.ToString(((ComboBox)c).Items[i], CultureInfo.InvariantCulture);
                        return "";
                    }
                case "setfocus": c.Focus(); return "";
                case "refresh": c.Refresh(); return "";
                case "move":
                    {
                        string[] keys = { "left", "top", "width", "height" };
                        for (int i = 0; i < a.Length && i < 4; i++) if (a[i].Length > 0) Set(o, keys[i], a[i]);
                        return "";
                    }
                case "zorder":
                    if (a.Length == 0 || Rad.ToInt(a[0]) == 0) c.BringToFront(); else c.SendToBack();
                    return "";
                case "show":
                    if (c is Form) { ((Form)c).Show(); ((Form)c).Activate(); } else SetVisible(o, true);
                    return "";
                case "hide":
                    if (c is Form) ((Form)c).Hide(); else SetVisible(o, false);
                    return "";
                case "showdialog":
                    if (c is Form) { var f = (Form)c; f.Hide(); return f.ShowDialog(Owner()) == DialogResult.Cancel ? "Cancel" : "OK"; }
                    return "";
                case "close":
                case "unload":
                    if (c is Form) ((Form)c).Close();
                    return "";
                case "performclick":
                case "click":
                    if (c is Button) ((Button)c).PerformClick();
                    else if (c is CheckBox) ((CheckBox)c).Checked = !((CheckBox)c).Checked;
                    else if (c is RadioButton) ((RadioButton)c).Checked = true;
                    return "";
                case "animate":
                    return "";
            }
            return Get(o, path, m);
        }

        // ------------------------------------------------------------------ radcall (project modules)
        /// <summary>"Module.function": a public static method of a class of this program.</summary>
        public static object LocalCall(string function, object[] args)
        {
            args = args ?? new object[0];
            var i = (function ?? "").LastIndexOf('.');
            if (i <= 0) throw new RadCallException("radcall: use \"Module.function\" (got '" + function + "')");
            string cls = function.Substring(0, i), fn = function.Substring(i + 1);
            Type type = null;
            foreach (var t in Assembly.GetEntryAssembly().GetTypes())
                if (string.Equals(t.Name, cls, StringComparison.OrdinalIgnoreCase) || string.Equals(t.FullName, cls, StringComparison.OrdinalIgnoreCase)) { type = t; break; }
            if (type == null) throw new RadCallException(function + ": class '" + cls + "' is not part of this program");
            var cands = type.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .Where(m => string.Equals(m.Name, fn, StringComparison.OrdinalIgnoreCase))
                .OrderBy(m => m.GetParameters().Length == args.Length ? 0 : 1).ToList();
            if (cands.Count == 0) throw new RadCallException(function + ": " + type.Name + " has no public static method '" + fn + "'");
            Exception last = null;
            foreach (var m in cands)
            {
                var ps = m.GetParameters();
                if (ps.Length != args.Length && !(ps.Length > 0 && ps[ps.Length - 1].IsDefined(typeof(ParamArrayAttribute), false))) continue;
                try
                {
                    var call = new object[ps.Length];
                    for (int k = 0; k < ps.Length; k++)
                    {
                        if (k == ps.Length - 1 && ps[k].IsDefined(typeof(ParamArrayAttribute), false) && !(args.Length == ps.Length && args[k] != null && ps[k].ParameterType.IsInstanceOfType(args[k])))
                        {
                            var et = ps[k].ParameterType.GetElementType();
                            var rest = Array.CreateInstance(et, Math.Max(0, args.Length - k));
                            for (int j = k; j < args.Length; j++) rest.SetValue(Conv(args[j], et), j - k);
                            call[k] = rest;
                            break;
                        }
                        call[k] = Conv(args[k], ps[k].ParameterType);
                    }
                    try { return m.Invoke(null, call); }
                    catch (TargetInvocationException ex) { throw new RadCallException(function + ": " + (ex.InnerException ?? ex).Message); }
                }
                catch (InvalidCastException ex) { last = ex; }
                catch (FormatException ex) { last = ex; }
                catch (OverflowException ex) { last = ex; }
            }
            throw new RadCallException(function + ": " + (last != null ? last.Message : "wrong number of arguments (" + args.Length + ")"));
        }

        static object Conv(object v, Type t)
        {
            if (v == null || t == typeof(object) || t.IsInstanceOfType(v)) return v;
            if (t == typeof(string)) return Rad.Str(v);
            return Convert.ChangeType(v, t, CultureInfo.InvariantCulture);
        }
    }
}
