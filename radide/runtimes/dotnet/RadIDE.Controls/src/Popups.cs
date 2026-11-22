// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Non-visual components: RmToast, RmSuperTooltip, RmBalloonTip, RmMessageBox.
#nullable disable
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    public enum RmToastPosition { BottomRight, BottomLeft, TopRight, TopLeft, BottomCenter, TopCenter }
    public enum RmToastKind { Info, Success, Warning, Error }

    static class RmKinds
    {
        public static Color Color(string kind, RmTheme t)
        {
            switch ((kind ?? "").ToLowerInvariant())
            {
                case "success": return System.Drawing.Color.FromArgb(46, 160, 67);
                case "warning": return System.Drawing.Color.FromArgb(230, 150, 20);
                case "error": case "critical": return System.Drawing.Color.FromArgb(215, 50, 50);
                case "question": return t.Accent;
                default: return t.Accent;
            }
        }

        public static string Glyph(string kind)
        {
            switch ((kind ?? "").ToLowerInvariant())
            {
                case "success": return "icon:check";
                case "warning": return "icon:warning";
                case "error": case "critical": return "icon:error";
                case "question": return "icon:help";
                default: return "icon:info";
            }
        }

        public static Control FindControl(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            foreach (Form f in Application.OpenForms)
            {
                var hits = f.Controls.Find(name, true);
                if (hits.Length > 0) return hits[0];
            }
            return null;
        }
    }

    /// <summary>A borderless popup window that does not take the focus.</summary>
    class RmPopupForm : Form
    {
        public RmPopupForm()
        {
            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false;
            StartPosition = FormStartPosition.Manual;
            TopMost = true;
            SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            Font = new Font("Segoe UI", 9f);
        }
        protected override bool ShowWithoutActivation { get { return true; } }
        protected override CreateParams CreateParams
        {
            get
            {
                var cp = base.CreateParams;
                cp.ExStyle |= 0x08000000 | 0x00000080;   // WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
                cp.ClassStyle |= 0x00020000;              // CS_DROPSHADOW
                return cp;
            }
        }
        protected float Sc { get { return Math.Max(1f, DeviceDpi / 96f); } }
    }

    class RmToastWindow : RmPopupForm
    {
        public string Title = "", Body = "", Kind = "Info";
        public RmTheme Th;
        public Action OnClickToast;
        public int LifeMs = 3000;
        double alpha;
        DateTime born;
        bool closing, hover;

        public RmToastWindow() { Opacity = 0; Cursor = Cursors.Hand; }

        public void Start()
        {
            born = DateTime.Now;
            RmAnimator.Run(Step);
        }

        bool Step()
        {
            if (IsDisposed) return false;
            if (!closing)
            {
                alpha = Math.Min(1, alpha + 0.12);
                if (!hover && LifeMs > 0 && (DateTime.Now - born).TotalMilliseconds > LifeMs) closing = true;
            }
            else alpha -= 0.1;
            if (alpha <= 0) { Close(); return false; }
            Opacity = Math.Max(0, Math.Min(0.97, alpha));
            return true;
        }

        public void Dismiss() { closing = true; RmAnimator.Run(Step); }

        protected override void OnMouseEnter(EventArgs e) { hover = true; base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { hover = false; born = DateTime.Now; base.OnMouseLeave(e); }
        protected override void OnMouseClick(MouseEventArgs e)
        {
            base.OnMouseClick(e);
            if (new Rectangle(Width - (int)(28 * Sc), 0, (int)(28 * Sc), (int)(28 * Sc)).Contains(e.Location)) { Dismiss(); return; }
            if (OnClickToast != null) OnClickToast();
            Dismiss();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Th;
            var back = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.08) : Color.White;
            var kc = RmKinds.Color(Kind, t);
            using (var b = new SolidBrush(back)) g.FillRectangle(b, ClientRectangle);
            using (var b = new SolidBrush(kc)) g.FillRectangle(b, RightToLeft == RightToLeft.Yes ? Width - (int)(5 * Sc) : 0, 0, (int)(5 * Sc), Height);
            using (var p = new Pen(RmDraw.Alpha(t.Border, 160))) g.DrawRectangle(p, 0, 0, Width - 1, Height - 1);
            bool rtl = RightToLeft == RightToLeft.Yes;
            int s = (int)(28 * Sc);
            var ir = new Rectangle((int)(16 * Sc), (int)(14 * Sc), s, s);
            if (rtl) ir.X = Width - ir.Right;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using (var b = new SolidBrush(RmDraw.Alpha(kc, 40))) g.FillEllipse(b, ir);
            RmImages.Draw(g, RmKinds.Glyph(Kind), null, Rectangle.Inflate(ir, -(int)(5 * Sc), -(int)(5 * Sc)), kc);
            int x = ir.Right + (int)(12 * Sc), w = Width - (int)(16 * Sc) - (int)(56 * Sc) - (int)(28 * Sc);
            var tr = new Rectangle(rtl ? (int)(28 * Sc) : x, (int)(12 * Sc), w, Font.Height + (int)(4 * Sc));
            using (var bf = new Font(Font, FontStyle.Bold)) RmDraw.Text(g, Title, bf, tr, t.WindowText, ContentAlignment.MiddleLeft, rtl);
            var br = new Rectangle(tr.X, tr.Bottom + (int)(2 * Sc), w, Height - tr.Bottom - (int)(14 * Sc));
            RmDraw.Text(g, Body, Font, br, t.SubtleText, ContentAlignment.TopLeft, rtl, true);
            RmDraw.Cross(g, new Rectangle(rtl ? 0 : Width - (int)(28 * Sc), 0, (int)(28 * Sc), (int)(28 * Sc)), t.SubtleText, 1.3f * Sc);
        }
    }

    /// <summary>Notifications: Show(title, text, kind, ms) - Info / Success / Warning / Error, stacked at Position.</summary>
    [DefaultEvent("Click"), ToolboxItem(true)]
    public class RmToast : Component
    {
        static readonly List<RmToastWindow> open = new List<RmToastWindow>();

        public RmToast() { }
        public RmToast(IContainer container) : this() { if (container != null) container.Add(this); }

        public event EventHandler Click;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        [Category("Behavior"), DefaultValue(RmToastPosition.BottomRight)]
        public RmToastPosition Position { get; set; }

        [Category("Behavior"), DefaultValue(3000), Description("Milliseconds a toast stays (0 = until clicked).")]
        public int Duration { get; set; } = 3000;

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get; set; }

        [Category("Appearance"), DefaultValue(RightToLeft.No)]
        public RightToLeft RightToLeft { get; set; }

        [Category("Appearance"), DefaultValue(340), Description("Width of a toast in 96-DPI pixels.")]
        public int ToastWidth { get; set; } = 340;

        [Browsable(false)]
        public int OpenCount { get { return open.Count(w => !w.IsDisposed); } }

        /// <summary>Shows a toast; kind = Info, Success, Warning or Error; ms = 0 uses Duration.</summary>
        public void Show(string title, string text = "", string kind = "Info", int ms = 0)
        {
            var w = new RmToastWindow { Title = title ?? "", Body = text ?? "", Kind = kind ?? "Info", Th = RmThemeManager.Resolve(Style, Color.Empty), LifeMs = ms > 0 ? ms : Duration };
            w.Text = title ?? "";
            w.RightToLeft = RightToLeft;
            w.OnClickToast = () => { EventItem = title ?? ""; EventIndex = open.IndexOf(w); var h = Click; if (h != null) h(this, new RmItemEventArgs(title, open.IndexOf(w), title)); };
            float sc = w.DeviceDpi / 96f;
            if (sc < 1) sc = 1;
            w.Size = new Size((int)(Math.Max(200, ToastWidth) * sc), (int)(84 * sc));
            open.RemoveAll(x => x.IsDisposed);
            open.Add(w);
            w.FormClosed += (s, a) => { open.Remove(w); Restack(); w.Dispose(); };
            Restack();
            w.Show();
            w.Start();
        }

        public void CloseAll() { foreach (var w in open.ToArray()) if (!w.IsDisposed) w.Dismiss(); }

        void Restack()
        {
            var active = Form.ActiveForm;
            var area = active != null ? Screen.FromControl(active).WorkingArea : Screen.PrimaryScreen.WorkingArea;
            int gap = 10, y = 0;
            for (int i = open.Count - 1; i >= 0; i--)
            {
                var w = open[i];
                if (w.IsDisposed) continue;
                int x;
                switch (Position)
                {
                    case RmToastPosition.BottomLeft: case RmToastPosition.TopLeft: x = area.Left + gap; break;
                    case RmToastPosition.BottomCenter: case RmToastPosition.TopCenter: x = area.Left + (area.Width - w.Width) / 2; break;
                    default: x = area.Right - w.Width - gap; break;
                }
                bool top = Position == RmToastPosition.TopLeft || Position == RmToastPosition.TopRight || Position == RmToastPosition.TopCenter;
                w.Location = new Point(x, top ? area.Top + gap + y : area.Bottom - gap - w.Height - y);
                y += w.Height + gap;
            }
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    class RmTipWindow : RmPopupForm
    {
        public string Title = "", Body = "", Footer = "", Image = "";
        public RmTheme Th;
        public bool Balloon;

        public Size Fit(int maxW)
        {
            float sc = Sc;
            int w = (int)(maxW * sc), pad = (int)(10 * sc);
            int img = Image.Length > 0 ? (int)(36 * sc) : 0;
            int textW = w - 2 * pad - img;
            int h = pad;
            using (var bf = new Font(Font, FontStyle.Bold)) if (Title.Length > 0) h += TextRenderer.MeasureText(Title, bf, new Size(textW, 1000), TextFormatFlags.WordBreak).Height + (int)(4 * sc);
            if (Body.Length > 0) h += TextRenderer.MeasureText(Body, Font, new Size(textW, 1000), TextFormatFlags.WordBreak).Height;
            h = Math.Max(h, img + pad);
            if (Footer.Length > 0) h += (int)(10 * sc) + Font.Height;
            h += pad + (Balloon ? (int)(10 * sc) : 0);
            return new Size(w, h);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Th;
            float sc = Sc;
            int pad = (int)(10 * sc), top = Balloon ? (int)(10 * sc) : 0;
            var back = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.08) : Color.White;
            using (var b = new SolidBrush(back)) g.FillRectangle(b, ClientRectangle);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            if (Balloon)
            {
                using (var b = new SolidBrush(Th.Accent)) g.FillRectangle(b, 0, 0, Width, top);
            }
            using (var p = new Pen(RmDraw.Alpha(t.Border, 170))) g.DrawRectangle(p, 0, 0, Width - 1, Height - 1);
            bool rtl = RightToLeft == RightToLeft.Yes;
            int img = Image.Length > 0 ? (int)(36 * sc) : 0;
            if (img > 0) RmImages.Draw(g, Image, null, new Rectangle(rtl ? Width - pad - (int)(28 * sc) : pad, top + pad, (int)(28 * sc), (int)(28 * sc)), t.Accent);
            int x = pad + img, w = Width - 2 * pad - img, y = top + pad;
            if (rtl) x = pad;
            if (Title.Length > 0)
                using (var bf = new Font(Font, FontStyle.Bold))
                {
                    int h = TextRenderer.MeasureText(Title, bf, new Size(w, 1000), TextFormatFlags.WordBreak).Height;
                    RmDraw.Text(g, Title, bf, new Rectangle(x, y, w, h), t.WindowText, ContentAlignment.TopLeft, rtl, true);
                    y += h + (int)(4 * sc);
                }
            if (Body.Length > 0)
            {
                int h = TextRenderer.MeasureText(Body, Font, new Size(w, 1000), TextFormatFlags.WordBreak).Height;
                RmDraw.Text(g, Body, Font, new Rectangle(x, y, w, h), t.SubtleText, ContentAlignment.TopLeft, rtl, true);
            }
            if (Footer.Length > 0)
            {
                int fy = Height - pad - Font.Height;
                using (var p = new Pen(RmDraw.Alpha(t.Border, 140))) g.DrawLine(p, pad, fy - (int)(5 * sc), Width - pad, fy - (int)(5 * sc));
                RmDraw.Text(g, Footer, Font, new Rectangle(pad, fy, Width - 2 * pad, Font.Height), t.SubtleText, ContentAlignment.MiddleLeft, rtl);
            }
        }
    }

    /// <summary>Rich tooltips (title, text, image, footer) attached to controls by name or reference.</summary>
    [ToolboxItem(true)]
    public class RmSuperTooltip : Component
    {
        class Tip { public string Title, Text, Footer, Image; }
        readonly Dictionary<Control, Tip> tips = new Dictionary<Control, Tip>();
        readonly Timer delay = new Timer { Interval = 500 };
        readonly Timer autoHide = new Timer();
        Control pending;
        RmTipWindow window;

        public RmSuperTooltip() { delay.Tick += (s, a) => { delay.Stop(); if (pending != null) Popup(pending, null); }; autoHide.Tick += (s, a) => { autoHide.Stop(); HideTip(); }; }
        public RmSuperTooltip(IContainer container) : this() { if (container != null) container.Add(this); }

        [Category("Behavior"), DefaultValue(500)]
        public int InitialDelay { get { return delay.Interval; } set { delay.Interval = Math.Max(1, value); } }

        /// <summary>Milliseconds before a tip appears (= InitialDelay).</summary>
        [Category("Behavior"), DefaultValue(500)]
        public int Delay { get { return InitialDelay; } set { InitialDelay = value; } }

        /// <summary>Milliseconds a hover tip stays (0 = until the mouse leaves).</summary>
        [Category("Behavior"), DefaultValue(0)]
        public int Duration { get; set; }

        public void SetToolTip(string control, string title, string text = "", string footer = "", string image = "") { SetTooltip(control, title, text, footer, image); }
        public void RemoveToolTip(string control) { RemoveTooltip(control); }
        public void Show(string control, string title, string text = "", int ms = 4000) { ShowTip(control, title, text, ms); }
        public void Hide() { HideTip(); }

        [Category("Behavior"), DefaultValue(320)]
        public int MaxWidth { get; set; } = 320;

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get; set; }

        protected virtual bool Balloon { get { return false; } }

        /// <summary>Attaches a rich tooltip to a control (found by name in the open forms).</summary>
        public void SetTooltip(string control, string title, string text = "", string footer = "", string image = "")
        {
            SetTooltipFor(RmKinds.FindControl(control), title, text, footer, image);
        }

        public void SetTooltipFor(Control c, string title, string text = "", string footer = "", string image = "")
        {
            if (c == null) return;
            if (!tips.ContainsKey(c))
            {
                c.MouseEnter += (s, a) => { pending = c; delay.Stop(); delay.Start(); };
                c.MouseLeave += (s, a) => { delay.Stop(); pending = null; HideTip(); };
                c.MouseDown += (s, a) => { delay.Stop(); HideTip(); };
                c.Disposed += (s, a) => tips.Remove(c);
            }
            tips[c] = new Tip { Title = title ?? "", Text = text ?? "", Footer = footer ?? "", Image = image ?? "" };
        }

        public void RemoveTooltip(string control) { var c = RmKinds.FindControl(control); if (c != null) tips.Remove(c); }

        /// <summary>Shows a tip next to a control now (ms = 0: until the mouse leaves / HideTip).</summary>
        public void ShowTip(string control, string title, string text = "", int ms = 4000)
        {
            var c = RmKinds.FindControl(control);
            if (c == null) return;
            Popup(c, new Tip { Title = title ?? "", Text = text ?? "", Footer = "", Image = "" });
            if (ms > 0) { autoHide.Interval = ms; autoHide.Start(); }
        }

        void Popup(Control c, Tip tip)
        {
            if (tip == null && !tips.TryGetValue(c, out tip)) return;
            HideTip();
            window = new RmTipWindow { Title = tip.Title, Body = tip.Text, Footer = tip.Footer, Image = tip.Image, Th = RmThemeManager.Resolve(Style, Color.Empty), Balloon = Balloon, RightToLeft = c.RightToLeft };
            window.Text = tip.Title;
            window.Size = window.Fit(MaxWidth);
            var p = c.PointToScreen(new Point(0, c.Height + 4));
            var area = Screen.FromControl(c).WorkingArea;
            if (p.X + window.Width > area.Right) p.X = area.Right - window.Width;
            if (p.Y + window.Height > area.Bottom) p.Y = c.PointToScreen(Point.Empty).Y - window.Height - 4;
            window.Location = p;
            window.Show();
            if (tip != null && Duration > 0 && !autoHide.Enabled) { autoHide.Interval = Duration; autoHide.Start(); }
        }

        public void HideTip() { if (window != null) { var w = window; window = null; w.Close(); w.Dispose(); } }

        [Browsable(false)]
        public bool IsShowing { get { return window != null && window.Visible; } }

        protected override void Dispose(bool disposing) { HideTip(); delay.Dispose(); autoHide.Dispose(); base.Dispose(disposing); }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    /// <summary>Balloon-style rich tip (accent band); same methods as RmSuperTooltip (ShowTip for a one-off balloon).</summary>
    [ToolboxItem(true)]
    public class RmBalloonTip : RmSuperTooltip
    {
        public RmBalloonTip() { }
        public RmBalloonTip(IContainer container) : base(container) { }
        protected override bool Balloon { get { return true; } }
    }

    /// <summary>Themed message box / task dialog: Show(text, title, buttons, icon) returns "OK", "Cancel", "Yes", "No", "Retry", "Abort", "Ignore".</summary>
    [ToolboxItem(true)]
    public class RmMessageBox : Component
    {
        public RmMessageBox() { }
        public RmMessageBox(IContainer container) : this() { if (container != null) container.Add(this); }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get; set; }

        [Category("Appearance"), DefaultValue(RightToLeft.No)]
        public RightToLeft RightToLeft { get; set; }

        [Browsable(false)]
        public string LastResult { get; private set; } = "";

        /// <summary>buttons: OK, OKCancel, YesNo, YesNoCancel, RetryCancel, AbortRetryIgnore (or "Save;Don't save;Cancel");
        /// icon: Info, Success, Warning, Error, Question, None.</summary>
        public string Show(string text, string title = "", string buttons = "OK", string icon = "Info")
        {
            LastResult = ShowDialog(text, title, buttons, icon, "", Style, RightToLeft);
            return LastResult;
        }

        /// <summary>Task dialog: a main instruction, the text and buttons.</summary>
        public string ShowTask(string instruction, string text, string title = "", string buttons = "OK", string icon = "Info")
        {
            LastResult = ShowDialog(text, title, buttons, icon, instruction, Style, RightToLeft);
            return LastResult;
        }

        public static string ShowDialog(string text, string title, string buttons, string icon, string instruction, RmStyle style, RightToLeft rtl)
        {
            var t = RmThemeManager.Resolve(style, Color.Empty);
            string[] names;
            switch ((buttons ?? "OK").Replace(" ", "").ToLowerInvariant())
            {
                case "okcancel": names = new[] { "OK", "Cancel" }; break;
                case "yesno": names = new[] { "Yes", "No" }; break;
                case "yesnocancel": names = new[] { "Yes", "No", "Cancel" }; break;
                case "retrycancel": names = new[] { "Retry", "Cancel" }; break;
                case "abortretryignore": names = new[] { "Abort", "Retry", "Ignore" }; break;
                case "ok": case "": names = new[] { "OK" }; break;
                default: names = RmScript.Split(buttons).ToArray(); if (names.Length == 0) names = new[] { "OK" }; break;
            }
            using (var f = new Form())
            {
                var owner = Form.ActiveForm;
                f.Text = string.IsNullOrEmpty(title) ? (owner != null ? owner.Text : "") : title;
                f.FormBorderStyle = FormBorderStyle.FixedDialog; f.MinimizeBox = false; f.MaximizeBox = false; f.ShowInTaskbar = false;
                f.StartPosition = owner != null ? FormStartPosition.CenterParent : FormStartPosition.CenterScreen;
                f.Font = new Font("Segoe UI", 9f);
                f.BackColor = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.04) : Color.White;
                f.ForeColor = t.WindowText;
                f.RightToLeft = rtl; f.RightToLeftLayout = rtl == RightToLeft.Yes;
                f.AutoScaleMode = AutoScaleMode.Dpi;
                f.AutoScaleDimensions = new SizeF(96, 96);
                bool hasIcon = !string.Equals(icon, "None", StringComparison.OrdinalIgnoreCase);
                int x0 = hasIcon ? 68 : 20, w = 380;
                var head = string.IsNullOrEmpty(instruction) ? null : new Label { Text = instruction, AutoSize = false, Left = x0, Top = 18, Width = w - x0 - 16, ForeColor = t.Accent, Font = new Font("Segoe UI", 12f) };
                int y = 20;
                if (head != null) { head.Height = TextRenderer.MeasureText(instruction, head.Font, new Size(head.Width, 1000), TextFormatFlags.WordBreak).Height + 4; f.Controls.Add(head); y = head.Bottom + 6; }
                var body = new Label { Text = text ?? "", AutoSize = false, Left = x0, Top = y, Width = w - x0 - 16, Name = "lblText" };
                body.Height = Math.Max(36, TextRenderer.MeasureText(body.Text, f.Font, new Size(body.Width, 2000), TextFormatFlags.WordBreak).Height + 4);
                f.Controls.Add(body);
                if (hasIcon)
                {
                    var kind = icon;
                    var pic = new Panel { Left = 20, Top = 18, Width = 36, Height = 36, BackColor = Color.Transparent };
                    pic.Paint += (s, a) =>
                    {
                        a.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                        var kc = RmKinds.Color(kind, t);
                        using (var b = new SolidBrush(RmDraw.Alpha(kc, 40))) a.Graphics.FillEllipse(b, 0, 0, pic.Width - 1, pic.Height - 1);
                        RmImages.Draw(a.Graphics, RmKinds.Glyph(kind), null, Rectangle.Inflate(pic.ClientRectangle, -7, -7), kc);
                    };
                    f.Controls.Add(pic);
                }
                int barY = Math.Max(body.Bottom, 60) + 16;
                var bar = new Panel { Left = 0, Top = barY, Width = w, Height = 52, BackColor = t.Dark ? RmDraw.Blend(t.Window, Color.Black, 0.1) : RmDraw.Blend(Color.White, Color.Black, 0.04) };
                f.Controls.Add(bar);
                string result = names[names.Length - 1];
                int bx = w - 16;
                for (int i = names.Length - 1; i >= 0; i--)
                {
                    var n = names[i];
                    int bw = Math.Max(84, TextRenderer.MeasureText(n, f.Font).Width + 24);
                    bx -= bw;
                    var b = new RmButton { Text = n, Left = bx, Top = 11, Width = bw, Height = 30, Kind = i == 0 ? RmButtonKind.Accent : RmButtonKind.Default, Style = style, Name = "btn" + n.Replace(" ", "").Replace("'", "") };
                    b.Click += (s, a) => { result = n; f.DialogResult = DialogResult.OK; f.Close(); };
                    bar.Controls.Add(b);
                    if (i == 0) f.AcceptButton = b;
                    bx -= 8;
                }
                f.ClientSize = new Size(w, bar.Bottom);
                f.KeyPreview = true;
                f.KeyDown += (s, a) => { if (a.KeyCode == Keys.Escape) { result = names.Contains("Cancel") ? "Cancel" : names[names.Length - 1]; f.Close(); } };
                RmThemeManager.DarkTitleBar(f, t.Dark);
                var r = f.ShowDialog(owner);
                if (r != DialogResult.OK && names.Contains("Cancel")) result = "Cancel";
                return result;
            }
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }
}
