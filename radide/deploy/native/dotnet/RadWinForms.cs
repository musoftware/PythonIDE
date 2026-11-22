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
    /// <summary>FormClosing: set true to keep the form open.</summary>
    public bool Cancel;

    public static RadEvent Parse(string sender, string name, string args)
    {
        var e = new RadEvent { Sender = sender, Name = name, Args = args ?? "" };
        var p = e.Args.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        Func<int, int> I = i => { int v; return i < p.Length && int.TryParse(p[i], NumberStyles.Integer, CultureInfo.InvariantCulture, out v) ? v : 0; };
        e.X = I(0); e.Y = I(1); e.Button = I(2); e.KeyCode = I(3);
        e.KeyChar = p.Length > 4 ? p[4] : "";
        return e;
    }

    internal string MakeArgs()
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
        protected readonly ToolTip Tips = new ToolTip();
        internal bool Closing2;

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

        internal int ClientHeight() { return ClientSize.Height - MenuHeight(); }

        internal void SetClientHeight(int h) { ClientSize = new Size(ClientSize.Width, h + MenuHeight()); }

        internal void SetBack(Color c)
        {
            BackColor = c.IsEmpty ? SystemColors.Control : c;
            Client.BackColor = BackColor;
        }

        internal string TipFor(Control c) { return Tips.GetToolTip(c) ?? ""; }

        internal void SetTip(Control c, string text) { Tips.SetToolTip(c, text); }

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

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            Fire(RadName, "Load", null);
        }

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
                        break;
                    case "SelectedIndexChanged":
                        if (c is ListBox) ((ListBox)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is ComboBox) ((ComboBox)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is TabControl) ((TabControl)c).SelectedIndexChanged += (s, a) => Fire(owner, ev, null);
                        break;
                    case "ValueChanged":
                        if (c is NumericUpDown) ((NumericUpDown)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is TrackBar) ((TrackBar)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        else if (c is DateTimePicker) ((DateTimePicker)c).ValueChanged += (s, a) => Fire(owner, ev, null);
                        break;
                    case "Tick":
                        if (target is Timer) ((Timer)target).Tick += (s, a) => Fire(owner, ev, null);
                        break;
                    default:
                        // a control of a referenced library (controls.json "events"): any EventHandler-shaped event
                        var info = target.GetType().GetEvent(ev);
                        if (info != null && info.EventHandlerType == typeof(EventHandler))
                            info.AddEventHandler(target, new EventHandler((s, a) => Fire(owner, ev, null)));
                        break;
                }
            }
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
            startup = GetForm(startupForm);
            Application.Run(startup);
            return 0;
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

        static bool IsShown(object o)
        {
            bool v;
            return !shown.TryGetValue(o, out v) || v;
        }

        /// <summary>a control that is hidden at design time (Visible = False)</summary>
        public static void MarkHidden(object o) { shown[o] = false; }

        public static string GetProp(string path, string prop)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return ""; }
            try { return Get(o, path, (prop ?? "").Trim().ToLowerInvariant()); }
            catch (Exception ex) { Warn(path + "." + prop + ": " + ex.Message); return ""; }
        }

        public static void SetProp(string path, string prop, string value)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return; }
            try { Set(o, (prop ?? "").Trim().ToLowerInvariant(), value ?? ""); }
            catch (Exception ex) { Warn(path + "." + prop + ": " + ex.Message); }
        }

        public static string CallMethod(string path, string method, string[] args)
        {
            var o = Resolve(path);
            if (o == null) { Warn("unknown object '" + path + "'"); return ""; }
            try { return Call(o, path, (method ?? "").Trim().ToLowerInvariant(), args ?? new string[0]); }
            catch (Exception ex) { Warn(path + "." + method + ": " + ex.Message); return ""; }
        }

        static void Warn(string msg)
        {
            try { Console.Error.WriteLine("[rad] " + msg); } catch (Exception) { }
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
                    if (c is Form) { ((Form)c).Show(); ((Form)c).Activate(); } else Set(o, "visible", "True");
                    return "";
                case "hide":
                    if (c is Form) ((Form)c).Hide(); else Set(o, "visible", "False");
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
