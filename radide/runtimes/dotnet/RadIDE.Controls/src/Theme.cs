// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Themes: the same colour tables as radforms' rf_theme (Light / Dark / Office / Metro), so a program looks the
// same whether it was published natively in C or in .NET.
#nullable disable
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    /// <summary>Per-control theme choice: Inherit = the application theme (RmThemeManager.Current).</summary>
    public enum RmStyle { Inherit, Light, Dark, Office, Metro }

    /// <summary>A colour table + metrics (rf_theme of radforms).</summary>
    public sealed class RmTheme
    {
        public string Name = "Light";
        public bool Dark;
        public Color Window, WindowText, Face, FaceText, Border, Hot, HotBorder, Pressed, Accent, AccentText,
            DisabledText, Selection, SelectionText, Input, InputText;
        public int Radius = 3, BorderWidth = 1, Padding = 6, AnimMs = 120;
        public string FontName = "Segoe UI";
        public float FontSize = 9f;

        public RmTheme Clone() { return (RmTheme)MemberwiseClone(); }

        /// <summary>A copy whose accent colours are replaced (AccentColor property).</summary>
        public RmTheme WithAccent(Color accent)
        {
            if (accent.IsEmpty) return this;
            var t = Clone();
            t.Accent = accent;
            t.HotBorder = accent;
            t.Selection = accent;
            if (Name == "Metro") t.Pressed = accent;
            t.AccentText = RmDraw.Luma(accent) > 0.6 ? Color.Black : Color.White;
            return t;
        }

        /// <summary>Back colour of a "card" surface (panel, tile area, popups) a bit apart from Window.</summary>
        public Color Surface { get { return Dark ? RmDraw.Blend(Window, Color.White, 0.06) : (Name == "Light" ? Color.White : Face); } }
        public Color SubtleText { get { return RmDraw.Blend(WindowText, Window, 0.4); } }
        public Color HeaderBack { get { return Name == "Office" ? Accent : (Dark ? RmDraw.Blend(Window, Color.Black, 0.25) : RmDraw.Blend(Window, Color.Black, 0.03)); } }
        public Color HeaderText { get { return Name == "Office" ? AccentText : WindowText; } }
    }

    /// <summary>Application theme: RmThemeManager.SetTheme("Dark"); AccentColor; ThemeChanged repaints every control.</summary>
    public static class RmThemeManager
    {
        static readonly Dictionary<string, RmTheme> themes = new Dictionary<string, RmTheme>(StringComparer.OrdinalIgnoreCase);
        static RmTheme current;
        static Color accent = Color.Empty;

        /// <summary>Raised after the theme or the accent colour changed.</summary>
        public static event EventHandler ThemeChanged;

        static RmThemeManager()
        {
            var t = new RmTheme { Name = "Light", Radius = 3 };
            Set(t, 240, 240, 240, 0, 0, 0, 225, 225, 225, 0, 0, 0, 173, 173, 173, 229, 241, 251, 0, 120, 215, 204, 228, 247,
                0, 120, 215, 255, 255, 255, 160, 160, 160, 0, 120, 215, 255, 255, 255, 255, 255, 255, 0, 0, 0);
            Define(t);
            t = new RmTheme { Name = "Dark", Dark = true, Radius = 4 };
            Set(t, 32, 32, 32, 240, 240, 240, 51, 51, 51, 240, 240, 240, 85, 85, 85, 69, 69, 69, 0, 120, 215, 90, 90, 90,
                0, 120, 215, 255, 255, 255, 120, 120, 120, 0, 95, 184, 255, 255, 255, 25, 25, 25, 240, 240, 240);
            Define(t);
            t = new RmTheme { Name = "Office", Radius = 2 };          // Office 2016 blue
            Set(t, 243, 243, 243, 38, 38, 38, 255, 255, 255, 38, 38, 38, 171, 171, 171, 213, 225, 242, 43, 87, 154, 163, 189, 227,
                43, 87, 154, 255, 255, 255, 165, 165, 165, 43, 87, 154, 255, 255, 255, 255, 255, 255, 38, 38, 38);
            Define(t);
            t = new RmTheme { Name = "Metro", Radius = 0, BorderWidth = 2 };   // flat, square
            Set(t, 255, 255, 255, 30, 30, 30, 230, 230, 230, 30, 30, 30, 204, 204, 204, 218, 218, 218, 0, 120, 215, 0, 120, 215,
                0, 120, 215, 255, 255, 255, 170, 170, 170, 0, 120, 215, 255, 255, 255, 255, 255, 255, 30, 30, 30);
            Define(t);
            current = themes["Light"];
        }

        static void Set(RmTheme t, params int[] v)
        {
            Func<int, Color> c = i => Color.FromArgb(v[i], v[i + 1], v[i + 2]);
            t.Window = c(0); t.WindowText = c(3); t.Face = c(6); t.FaceText = c(9); t.Border = c(12); t.Hot = c(15);
            t.HotBorder = c(18); t.Pressed = c(21); t.Accent = c(24); t.AccentText = c(27); t.DisabledText = c(30);
            t.Selection = c(33); t.SelectionText = c(36); t.Input = c(39); t.InputText = c(42);
        }

        /// <summary>Add (or replace) a theme by its Name.</summary>
        public static void Define(RmTheme theme) { if (theme != null && !string.IsNullOrEmpty(theme.Name)) themes[theme.Name] = theme; }

        public static IEnumerable<string> Names { get { return themes.Keys; } }

        public static RmTheme Get(string name)
        {
            RmTheme t;
            return name != null && themes.TryGetValue(name, out t) ? t : themes["Light"];
        }

        /// <summary>The application theme with the application accent colour.</summary>
        public static RmTheme Current { get { return current.WithAccent(accent); } }

        public static string CurrentName { get { return current.Name; } }

        public static Color AccentColor
        {
            get { return accent; }
            set { accent = value; Changed(); }
        }

        public static void SetTheme(string name)
        {
            current = Get(name);
            Changed();
        }

        /// <summary>Theme of a control: its Style (or Inherit = application theme) and its AccentColor.</summary>
        public static RmTheme Resolve(RmStyle style, Color controlAccent)
        {
            var t = style == RmStyle.Inherit ? current : Get(style.ToString());
            t = t.WithAccent(accent);
            return t.WithAccent(controlAccent);
        }

        static void Changed()
        {
            var h = ThemeChanged;
            if (h != null) h(null, EventArgs.Empty);
            foreach (Form f in Application.OpenForms) { ApplyToForm(f); f.Invalidate(true); }
        }

        // ------------------------------------------------------------------ forms
        sealed class Orig { public Color Back, Fore; public bool AmbientBack, AmbientFore, VisualStyle; }
        static readonly Dictionary<Control, Orig> original = new Dictionary<Control, Orig>();

        /// <summary>Form property Theme (generated code / Me.Theme = "Dark"): sets the application theme ("" or Inherit
        /// keeps it) and colours the form and its standard controls (labels, edits, lists ...); "Light" restores them.</summary>
        public static void ApplyFormTheme(Form form, string theme)
        {
            if (!string.IsNullOrEmpty(theme) && !theme.Equals("Inherit", StringComparison.OrdinalIgnoreCase) && !theme.Equals(current.Name, StringComparison.OrdinalIgnoreCase))
            {
                current = Get(theme);
                Changed();
            }
            if (form != null) ApplyToForm(form);
        }

        /// <summary>Colours a form and its standard (non-Rm) controls with the application theme.</summary>
        public static void ApplyToForm(Form form)
        {
            if (form == null || form.IsDisposed) return;
            var t = Current;
            DarkTitleBar(form, t.Dark);
            Walk(form, t);
        }

        static void Walk(Control c, RmTheme t)
        {
            if (!(c is IRmThemed))
            {
                Orig o;
                if (!original.TryGetValue(c, out o))
                {
                    var p = c.Parent;
                    o = new Orig { Back = c.BackColor, Fore = c.ForeColor, AmbientBack = p != null && c.BackColor == p.BackColor && !(c is TextBoxBase) && !(c is ListBox) && !(c is ComboBox),
                                   AmbientFore = p != null && c.ForeColor == p.ForeColor, VisualStyle = c is ButtonBase && ((ButtonBase)c).UseVisualStyleBackColor };
                    original[c] = o;
                    c.Disposed += (s, a) => original.Remove((Control)s);
                }
                bool light = t.Name == "Light";
                bool input = c is TextBoxBase || c is ListBox || c is ComboBox || c is NumericUpDown || c is TreeView || c is ListView || c is DataGridView;
                bool button = c is ButtonBase && !(c is CheckBox) && !(c is RadioButton);
                if (input)
                {
                    c.BackColor = light ? o.Back : t.Input;
                    c.ForeColor = light ? o.Fore : t.InputText;
                }
                else if (button)
                {
                    var b = (ButtonBase)c;
                    if (light) { b.BackColor = o.Back; b.ForeColor = o.Fore; b.UseVisualStyleBackColor = o.VisualStyle; }
                    else { b.UseVisualStyleBackColor = false; b.BackColor = t.Face; b.ForeColor = t.FaceText; }
                }
                else
                {
                    if (o.AmbientBack) c.ResetBackColor();
                    else if (!light && IsDefaultBack(o.Back)) c.BackColor = t.Window;
                    else if (light) c.BackColor = o.Back;
                    if (o.AmbientFore) c.ResetForeColor();
                    else if (!light && IsDefaultFore(o.Fore)) c.ForeColor = t.WindowText;
                    else if (light) c.ForeColor = o.Fore;
                }
            }
            else c.Invalidate();
            foreach (Control k in c.Controls) Walk(k, t);
        }

        static bool IsDefaultBack(Color c) { return c == SystemColors.Control || c == SystemColors.Window || c == Color.Transparent || c.ToArgb() == SystemColors.Control.ToArgb(); }
        static bool IsDefaultFore(Color c) { return c == SystemColors.ControlText || c == SystemColors.WindowText || c.ToArgb() == Color.Black.ToArgb(); }

        [DllImport("dwmapi.dll")]
        static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

        /// <summary>Dark title bar on Windows 10 1809+ / 11 (DWMWA_USE_IMMERSIVE_DARK_MODE).</summary>
        public static void DarkTitleBar(Form f, bool dark)
        {
            try
            {
                if (!f.IsHandleCreated) { f.HandleCreated += (s, a) => DarkTitleBar(f, Current.Dark); return; }
                int v = dark ? 1 : 0;
                if (DwmSetWindowAttribute(f.Handle, 20, ref v, 4) != 0) DwmSetWindowAttribute(f.Handle, 19, ref v, 4);
            }
            catch (Exception) { }
        }
    }

    /// <summary>Marks the controls that paint themselves from the theme (the form walker leaves them alone).</summary>
    public interface IRmThemed
    {
        RmStyle Style { get; set; }
        Color AccentColor { get; set; }
    }
}
