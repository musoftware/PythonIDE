// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// RmTextBox, RmComboBox, RmSlider, RmCalendar, RmDatePicker, RmTimePicker.
#nullable disable
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    static class Native
    {
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr SendMessage(IntPtr h, int msg, IntPtr w, string l);
        public const int EM_SETCUEBANNER = 0x1501;
    }

    /// <summary>Text box with watermark, clear button, icon and a validation border (ErrorText).</summary>
    [DefaultEvent("TextChanged"), DefaultProperty("Text")]
    public class RmTextBox : RmControl
    {
        readonly TextBox box = new TextBox();
        string watermark = "", icon = "", errorText = "", passwordChar = "";
        bool showClear;
        double focus;

        public event EventHandler IconClick;

        public RmTextBox()
        {
            Size = new Size(180, 30);
            box.BorderStyle = BorderStyle.None;
            box.TextChanged += (s, a) => { Invalidate(); OnTextChanged(EventArgs.Empty); };   // the outer Text is the edit's
            box.KeyPress += (s, a) => OnKeyPress(a);
            box.KeyDown += (s, a) => OnKeyDown(a);
            box.KeyUp += (s, a) => OnKeyUp(a);
            box.GotFocus += (s, a) => { Animate(); Invalidate(); };
            box.LostFocus += (s, a) => { Animate(); Invalidate(); };
            box.HandleCreated += (s, a) => Cue();
            box.MouseEnter += (s, a) => OnMouseEnter(a);
            box.MouseLeave += (s, a) => { if (!ClientRectangle.Contains(PointToClient(Cursor.Position))) OnMouseLeave(a); };
            Controls.Add(box);
            SetStyle(ControlStyles.Selectable, false);
            TabStop = false;
            box.TabStop = true;
        }

        /// <summary>The inner edit control.</summary>
        [Browsable(false)]
        public TextBox InnerTextBox { get { return box; } }

        [Category("Appearance"), Localizable(true)]
        public override string Text { get { return box.Text; } set { box.Text = value ?? ""; } }

        [Category("Appearance"), DefaultValue("")]
        public string Watermark { get { return watermark; } set { watermark = value ?? ""; Cue(); Invalidate(); } }

        [Category("Appearance"), DefaultValue(""), Description("Icon at the start: a file or a glyph (icon:search).")]
        public string Icon { get { return icon; } set { icon = value ?? ""; Layout2(); Invalidate(); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool ShowClear { get { return showClear; } set { showClear = value; Layout2(); Invalidate(); } }

        [Category("Behavior"), DefaultValue("")]
        public string PasswordChar
        {
            get { return passwordChar; }
            set { passwordChar = value ?? ""; box.PasswordChar = passwordChar.Length > 0 ? passwordChar[0] : '\0'; }
        }

        [Category("Behavior"), DefaultValue(false)]
        public bool MultiLine
        {
            get { return box.Multiline; }
            set { box.Multiline = value; box.ScrollBars = value ? ScrollBars.Vertical : ScrollBars.None; box.AcceptsReturn = value; Layout2(); }
        }

        [Category("Behavior"), DefaultValue(false)]
        public bool ReadOnly { get { return box.ReadOnly; } set { box.ReadOnly = value; Layout2(); Invalidate(); } }

        [Category("Behavior"), DefaultValue(0)]
        public int MaxLength { get { return box.MaxLength == 32767 ? 0 : box.MaxLength; } set { box.MaxLength = value <= 0 ? 32767 : value; } }

        [Category("Behavior"), DefaultValue(""), Description("Not empty = the input is invalid: red border and the message under the mouse.")]
        public string ErrorText
        {
            get { return errorText; }
            set { errorText = value ?? ""; tip.SetToolTip(box, errorText); tip.SetToolTip(this, errorText); Invalidate(); }
        }
        readonly ToolTip tip = new ToolTip();

        public void Clear() { box.Clear(); }
        public void AppendText(string text) { box.AppendText(text ?? ""); }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int SelStart { get { return box.SelectionStart; } set { box.SelectionStart = Math.Max(0, value); } }
        public void SelectAll() { box.SelectAll(); }
        public new void Focus() { box.Focus(); }

        protected override void OnGotFocus(EventArgs e) { box.Focus(); base.OnGotFocus(e); }

        void Cue()
        {
            if (box.IsHandleCreated && !box.Multiline) Native.SendMessage(box.Handle, Native.EM_SETCUEBANNER, (IntPtr)1, watermark);
        }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); Cue(); Layout2(); }

        protected override void OnFontChanged(EventArgs e) { box.Font = Font; base.OnFontChanged(e); Layout2(); }

        protected override void OnResize(EventArgs e) { base.OnResize(e); Layout2(); }

        protected override void OnRightToLeftChanged(EventArgs e) { box.RightToLeft = RightToLeft; base.OnRightToLeftChanged(e); Layout2(); }

        protected override void ThemeChanged() { Recolor(); }

        void Recolor()
        {
            var t = Theme;
            box.BackColor = BackColor.A == 255 ? BackColor : t.Input;
            box.ForeColor = HasFore ? ForeColor : t.InputText;
        }

        protected override void OnForeColorChanged(EventArgs e) { Recolor(); base.OnForeColorChanged(e); }
        protected override void OnBackColorChanged(EventArgs e) { Recolor(); base.OnBackColorChanged(e); }

        int IconW { get { return icon.Length > 0 ? S(24) : 0; } }
        int ClearW { get { return showClear && !box.ReadOnly ? S(22) : 0; } }

        Rectangle IconRect { get { return M(new Rectangle(S(4), 0, IconW, box.Multiline ? S(26) : Height)); } }
        Rectangle ClearRect { get { return M(new Rectangle(Width - ClearW - S(3), 0, ClearW, box.Multiline ? S(26) : Height)); } }

        void Layout2()
        {
            Recolor();
            int pad = S(8);
            int x = pad + IconW, w = Width - x - pad - ClearW;
            if (box.Multiline) box.SetBounds(Rtl ? Width - x - w : x, S(6), Math.Max(10, w), Math.Max(10, Height - S(12)));
            else
            {
                int h = box.PreferredHeight;
                box.SetBounds(Rtl ? Width - x - w : x, (Height - h) / 2 + 1, Math.Max(10, w), h);
            }
        }

        protected override bool AnimateMore()
        {
            focus = RmAnimator.Step(focus, box.Focused ? 1 : 0, Theme.AnimMs);
            return focus != (box.Focused ? 1 : 0);
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (ClearW > 0 && ClearRect.Contains(e.Location) && box.TextLength > 0) { box.Clear(); box.Focus(); }
            else if (IconW > 0 && IconRect.Contains(e.Location)) { var h = IconClick; if (h != null) h(this, EventArgs.Empty); }
            else box.Focus();
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            Cursor = (ClearW > 0 && ClearRect.Contains(e.Location)) || (IconW > 0 && IconRect.Contains(e.Location) && IconClick != null) ? Cursors.Hand : Cursors.IBeam;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            bool err = errorText.Length > 0;
            Color red = Color.FromArgb(200, 40, 40);
            Color border = err ? red : RmDraw.Blend(RmDraw.Blend(t.Border, t.HotBorder, hover * 0.5), t.Accent, focus);
            var back = BackColor.A == 255 ? BackColor : t.Input;
            if (!Enabled) back = RmDraw.Blend(back, t.Window, 0.5);
            var r = new RectangleF(0.5f, 0.5f, Width - 1, Height - 1);
            RmDraw.Box(g, r, back, border, Sf(t.BorderWidth), Sf(t.Radius));
            if (focus > 0 && t.Name != "Metro")
                using (var p = new Pen(err ? red : t.Accent, Sf(2))) g.DrawLine(p, Sf(t.Radius), Height - Sf(1), Width - Sf(t.Radius), Height - Sf(1));
            if (IconW > 0) RmImages.Draw(g, icon, null, Rectangle.Inflate(IconRect, -S(3), -S(5)), err ? red : t.SubtleText, Enabled);
            if (ClearW > 0 && box.TextLength > 0) RmDraw.Cross(g, ClearRect, RmDraw.Blend(t.SubtleText, t.WindowText, hover), Sf(1.4f));
            if (box.Multiline && box.TextLength == 0 && !box.Focused && watermark.Length > 0)
                RmDraw.Text(g, watermark, Font, box.Bounds, t.SubtleText, ContentAlignment.TopLeft, Rtl);
        }
    }

    /// <summary>Themed combo box with images and a watermark.</summary>
    [DefaultEvent("SelectedIndexChanged")]
    public class RmComboBox : ComboBox, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty;
        string watermark = "", itemsText = "";
        List<RmItem> items = new List<RmItem>();
        bool hot;

        public RmComboBox()
        {
            DrawMode = DrawMode.OwnerDrawFixed;
            FlatStyle = FlatStyle.Flat;
            DropDownStyle = ComboBoxStyle.DropDownList;
            ItemHeight = 22;
            Font = new Font("Segoe UI", 9f);
            RmThemeManager.ThemeChanged += OnTheme;
            Size = new Size(180, 30);
        }

        protected override void Dispose(bool disposing) { RmThemeManager.ThemeChanged -= OnTheme; base.Dispose(disposing); }

        void OnTheme(object s, EventArgs e) { Recolor(); Invalidate(); }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get { return style; } set { style = value; Recolor(); Invalidate(); } }

        [Category("Appearance")]
        public Color AccentColor { get { return accent; } set { accent = value; Invalidate(); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        [Category("Appearance"), DefaultValue("")]
        public string Watermark { get { return watermark; } set { watermark = value ?? ""; Invalidate(); } }

        /// <summary>Items as text: "a;b;c" or a JSON array of {Text, Image}.</summary>
        [Category("Data"), DefaultValue("")]
        public string ItemsText
        {
            get { return itemsText; }
            set
            {
                itemsText = value ?? "";
                items = RmItem.Parse(itemsText);
                BeginUpdate();
                Items.Clear();
                foreach (var it in items) Items.Add(it);
                EndUpdate();
            }
        }

        public void AddItem(string text) { var it = new RmItem(text); items.Add(it); Items.Add(it); }
        public void RemoveItem(int index) { if (index >= 0 && index < Items.Count) Items.RemoveAt(index); }
        public void ClearItems() { Items.Clear(); items.Clear(); }
        public void Clear() { ClearItems(); Text = ""; }
        public string List(int index) { return index >= 0 && index < Items.Count ? GetItemText(Items[index]) : ""; }
        public int IndexOf(string text) { for (int i = 0; i < Items.Count; i++) if (GetItemText(Items[i]) == text) return i; return -1; }
        public void ShowDropDown() { DroppedDown = true; }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public new string SelectedItem { get { return SelectedIndex >= 0 ? GetItemText(Items[SelectedIndex]) : ""; } set { SelectedIndex = IndexOf(value); } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int ListCount { get { return Items.Count; } }

        void Recolor()
        {
            var t = Theme;
            BackColor = t.Input;
            ForeColor = t.InputText;
        }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); Recolor(); ItemHeight = (int)(22 * DeviceDpi / 96f); }
        protected override void OnMouseEnter(EventArgs e) { hot = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { hot = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnGotFocus(EventArgs e) { Invalidate(); base.OnGotFocus(e); }
        protected override void OnLostFocus(EventArgs e) { Invalidate(); base.OnLostFocus(e); }

        protected override void OnDrawItem(DrawItemEventArgs e)
        {
            var t = Theme;
            var g = e.Graphics;
            bool sel = (e.State & DrawItemState.Selected) != 0 && (e.State & DrawItemState.ComboBoxEdit) == 0;
            using (var b = new SolidBrush(sel ? t.Selection : t.Input)) g.FillRectangle(b, e.Bounds);
            if (e.Index < 0) return;
            var o = Items[e.Index];
            var it = o as RmItem;
            string text = it != null ? it.Text : GetItemText(o);
            var r = e.Bounds;
            bool rtl = RightToLeft == RightToLeft.Yes;
            int x = r.X + 4;
            if (it != null && it.Image.Length > 0)
            {
                int s = r.Height - 4;
                var ir = new Rectangle(rtl ? r.Right - 4 - s : x, r.Y + 2, s, s);
                RmImages.Draw(g, it.Image, null, ir, sel ? t.SelectionText : t.InputText, Enabled);
                x += s + 4;
            }
            var tr = rtl ? new Rectangle(r.X + 4, r.Y, r.Right - (x - r.X) - 4, r.Height) : new Rectangle(x, r.Y, r.Right - x - 2, r.Height);
            RmDraw.Text(g, text, Font, tr, sel ? t.SelectionText : (Enabled ? t.InputText : t.DisabledText), ContentAlignment.MiddleLeft, rtl);
        }

        const int WM_PAINT = 0x000F;

        protected override void WndProc(ref Message m)
        {
            base.WndProc(ref m);
            if (m.Msg == WM_PAINT) using (var g = Graphics.FromHwnd(Handle)) PaintFrame(g);
        }

        void PaintFrame(Graphics g)
        {
            var t = Theme;
            bool rtl = RightToLeft == RightToLeft.Yes;
            float sc = DeviceDpi / 96f;
            int aw = (int)(SystemInformation.VerticalScrollBarWidth + 2 * sc);
            var back = Enabled ? t.Input : RmDraw.Blend(t.Input, t.Window, 0.5);
            var surface = Parent != null ? Parent.BackColor : t.Window;
            var cr = ClientRectangle;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            if (DropDownStyle == ComboBoxStyle.DropDownList)
            {
                using (var b = new SolidBrush(surface)) g.FillRectangle(b, cr);
                RmDraw.Box(g, new RectangleF(0.5f, 0.5f, cr.Width - 1, cr.Height - 1), back, Color.Empty, 0, t.Radius * sc);
                var tr = new Rectangle(rtl ? aw : (int)(8 * sc), 0, cr.Width - aw - (int)(8 * sc), cr.Height);
                if (SelectedIndex >= 0)
                {
                    var it = Items[SelectedIndex] as RmItem;
                    if (it != null && it.Image.Length > 0)
                    {
                        int s = cr.Height - (int)(10 * sc);
                        RmImages.Draw(g, it.Image, null, new Rectangle(rtl ? tr.Right - s : tr.X, (cr.Height - s) / 2, s, s), t.InputText, Enabled);
                        if (rtl) tr.Width -= s + 4; else { tr.X += s + 4; tr.Width -= s + 4; }
                    }
                    RmDraw.Text(g, it != null ? it.Text : GetItemText(Items[SelectedIndex]), Font, tr, Enabled ? t.InputText : t.DisabledText, ContentAlignment.MiddleLeft, rtl);
                }
                else if (watermark.Length > 0) RmDraw.Text(g, watermark, Font, tr, t.SubtleText, ContentAlignment.MiddleLeft, rtl);
            }
            else
            {   // editable: the edit child paints the text; cover the native border and button
                using (var p = new Pen(back, 3 * sc)) g.DrawRectangle(p, 1, 1, cr.Width - 3, cr.Height - 3);
                var ar0 = new Rectangle(rtl ? 0 : cr.Width - aw, 0, aw, cr.Height);
                using (var b = new SolidBrush(back)) g.FillRectangle(b, ar0);
            }
            var border = Focused || DroppedDown ? t.Accent : (hot ? t.HotBorder : t.Border);
            RmDraw.Box(g, new RectangleF(0.5f, 0.5f, cr.Width - 1, cr.Height - 1), Color.Empty, border, Math.Max(1, t.BorderWidth * sc), t.Radius * sc);
            var ar = new Rectangle(rtl ? 0 : cr.Width - aw, 0, aw, cr.Height);
            RmDraw.Chevron(g, ar, hot ? t.Accent : t.SubtleText, 1.4f * sc);
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    /// <summary>Track bar with a value tip while dragging.</summary>
    [DefaultEvent("ValueChanged"), DefaultProperty("Value")]
    public class RmSlider : RmControl
    {
        int min, max = 100, val, tick = 10, small = 1;
        bool drag;
        bool showTip = true;

        public event EventHandler ValueChanged;

        public RmSlider() { Size = new Size(200, 36); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior"), DefaultValue(0)]
        public int Value
        {
            get { return val; }
            set
            {
                var v = Math.Max(min, Math.Min(max, value));
                if (v == val) return;
                val = v; Invalidate();
                var h = ValueChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Category("Behavior"), DefaultValue(0)]
        public int Minimum { get { return min; } set { min = value; if (max < min) max = min; Value = val; Invalidate(); } }

        [Category("Behavior"), DefaultValue(100)]
        public int Maximum { get { return max; } set { max = Math.Max(min, value); Value = val; Invalidate(); } }

        [Category("Appearance"), DefaultValue(10), Description("Distance between tick marks (0 = none).")]
        public int TickFrequency { get { return tick; } set { tick = Math.Max(0, value); Invalidate(); } }

        [Category("Behavior"), DefaultValue(1)]
        public int SmallChange { get { return small; } set { small = Math.Max(1, value); } }

        [Category("Appearance"), DefaultValue(true)]
        public bool ShowValueTip { get { return showTip; } set { showTip = value; } }

        int large = 10;
        bool showValue;

        [Category("Behavior"), DefaultValue(10)]
        public int LargeChange { get { return large; } set { large = Math.Max(1, value); } }

        [Category("Appearance"), DefaultValue(false), Description("The value tip is always shown (not only while dragging).")]
        public bool ShowValue { get { return showValue; } set { showValue = value; Invalidate(); } }

        Rectangle Track { get { int k = S(9); return new Rectangle(k + S(2), Height / 2 - S(2), Width - 2 * k - S(4), S(4)); } }

        float Frac { get { return max == min ? 0 : (float)(val - min) / (max - min); } }

        int ThumbX { get { var tr = Track; return Rtl ? (int)(tr.Right - tr.Width * Frac) : (int)(tr.X + tr.Width * Frac); } }

        void FromX(int x)
        {
            var tr = Track;
            float f = Math.Max(0, Math.Min(1, (float)(x - tr.X) / Math.Max(1, tr.Width)));
            if (Rtl) f = 1 - f;
            Value = (int)Math.Round(min + f * (max - min));
        }

        protected override void OnMouseDown(MouseEventArgs e) { base.OnMouseDown(e); if (e.Button == MouseButtons.Left) { drag = true; FromX(e.X); Invalidate(); } }
        protected override void OnMouseMove(MouseEventArgs e) { base.OnMouseMove(e); if (drag) FromX(e.X); }
        protected override void OnMouseUp(MouseEventArgs e) { base.OnMouseUp(e); drag = false; Invalidate(); }
        protected override void OnMouseWheel(MouseEventArgs e) { Value += Math.Sign(e.Delta) * small; base.OnMouseWheel(e); }
        protected override bool IsInputKey(Keys k) { return k == Keys.Left || k == Keys.Right || k == Keys.Up || k == Keys.Down || base.IsInputKey(k); }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            int d = e.KeyCode == Keys.Right || e.KeyCode == Keys.Up ? small : e.KeyCode == Keys.Left || e.KeyCode == Keys.Down ? -small : 0;
            if (Rtl && (e.KeyCode == Keys.Left || e.KeyCode == Keys.Right)) d = -d;
            if (e.KeyCode == Keys.Home) Value = min; else if (e.KeyCode == Keys.End) Value = max; else if (e.KeyCode == Keys.PageUp) Value += large; else if (e.KeyCode == Keys.PageDown) Value -= large;
            if (d != 0) Value += d;
            base.OnKeyDown(e);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            var tr = Track;
            float rad = t.Radius == 0 ? 0 : tr.Height / 2f;
            RmDraw.Box(g, tr, t.Dark ? RmDraw.Blend(t.Face, Color.White, 0.1) : RmDraw.Blend(t.Border, t.Window, 0.3), Color.Empty, 0, rad);
            int tx = ThumbX;
            var filled = Rtl ? new Rectangle(tx, tr.Y, tr.Right - tx, tr.Height) : new Rectangle(tr.X, tr.Y, tx - tr.X, tr.Height);
            if (filled.Width > 0) RmDraw.Box(g, filled, Enabled ? t.Accent : t.DisabledText, Color.Empty, 0, rad);
            if (tick > 0 && max > min && (max - min) / tick <= 100)
                using (var p = new Pen(RmDraw.Alpha(t.SubtleText, 120)))
                    for (int v = min; v <= max; v += tick)
                    {
                        float f = (float)(v - min) / (max - min);
                        float x = Rtl ? tr.Right - tr.Width * f : tr.X + tr.Width * f;
                        g.DrawLine(p, x, tr.Bottom + S(5), x, tr.Bottom + S(8));
                    }
            float k = Sf(9) + Sf(2) * (float)Math.Max(hover, drag ? 1 : 0);
            var knob = new RectangleF(tx - k, Height / 2f - k, 2 * k, 2 * k);
            RmDraw.Box(g, knob, t.Dark ? t.Face : Color.White, Enabled ? t.Accent : t.DisabledText, Sf(2), t.Radius == 0 ? 0 : k);
            if (Focused && ShowFocusCues) RmDraw.Box(g, RectangleF.Inflate(knob, Sf(3), Sf(3)), Color.Empty, RmDraw.Alpha(t.Accent, 90), Sf(1.5f), t.Radius == 0 ? 0 : k + Sf(3));
            if (showValue || showTip && (drag || hover > 0.6))
            {
                var s = val.ToString(CultureInfo.InvariantCulture);
                var sz = RmDraw.Measure(s, Font);
                var tipR = new Rectangle(tx - sz.Width / 2 - S(5), (int)knob.Y - sz.Height - S(4), sz.Width + S(10), sz.Height + S(2));
                if (tipR.Y < 0) return;
                RmDraw.Box(g, tipR, t.Accent, Color.Empty, 0, Sf(3));
                RmDraw.Text(g, s, Font, tipR, t.AccentText, ContentAlignment.MiddleCenter);
            }
        }
    }

    /// <summary>Month calendar.</summary>
    [DefaultEvent("ValueChanged"), DefaultProperty("Value")]
    public class RmCalendar : RmControl
    {
        DateTime value = DateTime.Today, view = new DateTime(DateTime.Today.Year, DateTime.Today.Month, 1);
        DateTime minDate = new DateTime(1753, 1, 1), maxDate = new DateTime(9998, 12, 31);
        Point mouse = new Point(-1, -1);

        public event EventHandler ValueChanged;
        /// <summary>A day was clicked (the drop-down of RmDatePicker closes on it).</summary>
        public event EventHandler DayClicked;

        public RmCalendar() { Size = new Size(240, 230); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior")]
        public DateTime Value
        {
            get { return value; }
            set
            {
                var v = value.Date < minDate ? minDate : value.Date > maxDate ? maxDate : value;
                bool changed = v != this.value;
                this.value = v; view = new DateTime(v.Year, v.Month, 1); Invalidate();
                if (changed) { var h = ValueChanged; if (h != null) h(this, EventArgs.Empty); }
            }
        }
        public bool ShouldSerializeValue() { return value != DateTime.Today; }

        [Category("Behavior")]
        public DateTime MinDate { get { return minDate; } set { minDate = value; Invalidate(); } }
        public bool ShouldSerializeMinDate() { return minDate != new DateTime(1753, 1, 1); }

        [Category("Behavior")]
        public DateTime MaxDate { get { return maxDate; } set { maxDate = value; Invalidate(); } }
        public bool ShouldSerializeMaxDate() { return maxDate != new DateTime(9998, 12, 31); }

        [Browsable(false)]
        public string Format { get; set; }

        public void NextMonth() { view = view.AddMonths(1); Invalidate(); }
        public void AddDays(int days) { Value = value.AddDays(days); }
        public void AddMonths(int months) { Value = value.AddMonths(months); }
        public void Today() { Value = DateTime.Today; }
        public void PreviousMonth() { view = view.AddMonths(-1); Invalidate(); }
        public void GoToToday() { Value = DateTime.Today; }

        static DateTimeFormatInfo Dtf
        {
            get
            {
                var c = CultureInfo.CurrentCulture;
                return c.DateTimeFormat.Calendar is GregorianCalendar ? c.DateTimeFormat : CultureInfo.InvariantCulture.DateTimeFormat;
            }
        }

        int HeaderH { get { return S(32); } }
        Rectangle PrevRect { get { return M(new Rectangle(S(4), S(4), S(26), HeaderH - S(8))); } }
        Rectangle NextRect { get { return M(new Rectangle(Width - S(30), S(4), S(26), HeaderH - S(8))); } }

        Rectangle Cell(int row, int col)
        {
            int top = HeaderH + S(22);
            int cw = (Width - S(8)) / 7, ch = Math.Max(S(16), (Height - top - S(4)) / 6);
            return M(new Rectangle(S(4) + col * cw, top + row * ch, cw, ch));
        }

        DateTime FirstCell()
        {
            int first = (int)Dtf.FirstDayOfWeek;
            int off = ((int)view.DayOfWeek - first + 7) % 7;
            return view.AddDays(-off);
        }

        DateTime? DayAt(Point p)
        {
            var d0 = FirstCell();
            for (int r = 0; r < 6; r++) for (int c = 0; c < 7; c++) if (Cell(r, c).Contains(p)) return d0.AddDays(r * 7 + c);
            return null;
        }

        protected override void OnMouseMove(MouseEventArgs e) { mouse = e.Location; Invalidate(); base.OnMouseMove(e); }
        protected override void OnMouseLeave(EventArgs e) { mouse = new Point(-1, -1); base.OnMouseLeave(e); }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (PrevRect.Contains(e.Location)) { PreviousMonth(); return; }
            if (NextRect.Contains(e.Location)) { NextMonth(); return; }
            var d = DayAt(e.Location);
            if (d.HasValue && d.Value >= minDate && d.Value <= maxDate)
            {
                Value = d.Value.Date + value.TimeOfDay;
                var h = DayClicked; if (h != null) h(this, EventArgs.Empty);
            }
        }

        protected override bool IsInputKey(Keys k) { return k == Keys.Left || k == Keys.Right || k == Keys.Up || k == Keys.Down || base.IsInputKey(k); }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            int d = 0;
            switch (e.KeyCode) { case Keys.Left: d = Rtl ? 1 : -1; break; case Keys.Right: d = Rtl ? -1 : 1; break; case Keys.Up: d = -7; break; case Keys.Down: d = 7; break; }
            if (e.KeyCode == Keys.PageUp) Value = value.AddMonths(-1); else if (e.KeyCode == Keys.PageDown) Value = value.AddMonths(1);
            else if (e.KeyCode == Keys.Enter) { var h = DayClicked; if (h != null) h(this, EventArgs.Empty); }
            if (d != 0) Value = value.AddDays(d);
            base.OnKeyDown(e);
        }

        protected override void OnMouseWheel(MouseEventArgs e) { if (e.Delta > 0) PreviousMonth(); else NextMonth(); base.OnMouseWheel(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            var dtf = Dtf;
            var back = BackColor.A == 255 ? BackColor : t.Surface;
            RmDraw.Box(g, new RectangleF(0.5f, 0.5f, Width - 1, Height - 1), back, t.Border, 1, Sf(t.Radius));
            var title = dtf.GetMonthName(view.Month) + " " + view.Year.ToString(CultureInfo.InvariantCulture);
            using (var bf = new Font(Font, FontStyle.Bold))
                RmDraw.Text(g, title, bf, new Rectangle(0, 0, Width, HeaderH), t.WindowText, ContentAlignment.MiddleCenter, Rtl);
            foreach (var r in new[] { PrevRect, NextRect })
                if (r.Contains(mouse)) RmDraw.Box(g, r, t.Hot, Color.Empty, 0, Sf(t.Radius));
            RmDraw.Chevron(g, PrevRect, t.WindowText, Sf(1.5f), false, Rtl, !Rtl);
            RmDraw.Chevron(g, NextRect, t.WindowText, Sf(1.5f), false, !Rtl, Rtl);
            int first = (int)dtf.FirstDayOfWeek;
            for (int c = 0; c < 7; c++)
            {
                var r = Cell(0, c);
                var name = dtf.GetShortestDayName((DayOfWeek)((first + c) % 7));
                RmDraw.Text(g, name, Font, new Rectangle(r.X, HeaderH, r.Width, S(20)), t.SubtleText, ContentAlignment.MiddleCenter, Rtl);
            }
            var d0 = FirstCell();
            g.SmoothingMode = SmoothingMode.AntiAlias;
            for (int row = 0; row < 6; row++)
                for (int c = 0; c < 7; c++)
                {
                    var d = d0.AddDays(row * 7 + c);
                    var r = Rectangle.Inflate(Cell(row, c), -S(1), -S(1));
                    bool sel = d.Date == value.Date, other = d.Month != view.Month, ok = d >= minDate && d <= maxDate;
                    Color fore = !ok ? t.DisabledText : other ? t.SubtleText : t.WindowText;
                    if (sel) { RmDraw.Box(g, r, t.Accent, Color.Empty, 0, t.Radius == 0 ? 0 : Math.Min(r.Width, r.Height) / 2f); fore = t.AccentText; }
                    else if (r.Contains(mouse) && ok) RmDraw.Box(g, r, t.Hot, Color.Empty, 0, t.Radius == 0 ? 0 : Math.Min(r.Width, r.Height) / 2f);
                    if (d.Date == DateTime.Today && !sel) RmDraw.Box(g, r, Color.Empty, t.Accent, Sf(1.2f), t.Radius == 0 ? 0 : Math.Min(r.Width, r.Height) / 2f);
                    RmDraw.Text(g, d.Day.ToString(CultureInfo.InvariantCulture), Font, r, fore, ContentAlignment.MiddleCenter);
                }
            FocusCue(g, new Rectangle(S(2), S(2), Width - S(5), Height - S(5)), t, Sf(t.Radius));
        }
    }

    /// <summary>Date picker: the formatted date + a drop-down month calendar.</summary>
    [DefaultEvent("ValueChanged"), DefaultProperty("Value")]
    public class RmDatePicker : RmControl
    {
        DateTime value = DateTime.Today, minDate = new DateTime(1753, 1, 1), maxDate = new DateTime(9998, 12, 31);
        string format = "Short";
        ToolStripDropDown drop;

        public event EventHandler ValueChanged;

        public RmDatePicker() { Size = new Size(160, 30); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior")]
        public DateTime Value
        {
            get { return value; }
            set
            {
                var v = value < minDate ? minDate : value > maxDate ? maxDate : value;
                if (v == this.value) return;
                this.value = v; Invalidate();
                var h = ValueChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }
        public bool ShouldSerializeValue() { return value != DateTime.Today; }

        [Category("Behavior")]
        public DateTime MinDate { get { return minDate; } set { minDate = value; } }
        public bool ShouldSerializeMinDate() { return minDate != new DateTime(1753, 1, 1); }

        [Category("Behavior")]
        public DateTime MaxDate { get { return maxDate; } set { maxDate = value; } }
        public bool ShouldSerializeMaxDate() { return maxDate != new DateTime(9998, 12, 31); }

        [Category("Appearance"), DefaultValue("Short"), Description("Short, Long, Time or a .NET date format (yyyy-MM-dd).")]
        public string Format { get { return format; } set { format = string.IsNullOrEmpty(value) ? "Short" : value; Invalidate(); } }

        public override string Text { get { return Formatted(); } set { DateTime d; if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out d) || DateTime.TryParse(value, out d)) Value = d; } }

        protected virtual string Formatted()
        {
            switch (format.ToLowerInvariant())
            {
                case "short": return value.ToString("d");
                case "long": return value.ToString("D");
                case "time": return value.ToString("t");
                default: try { return value.ToString(format); } catch (FormatException) { return value.ToString("d"); }
            }
        }

        protected virtual string GlyphName { get { return "calendar"; } }

        public void AddDays(int days) { Value = value.AddDays(days); }
        public void AddMonths(int months) { Value = value.AddMonths(months); }
        public void Today() { Value = DateTime.Today + value.TimeOfDay; }
        /// <summary>The value in a .NET date format ("" = the Format property).</summary>
        public string FormatDate(string format = "") { try { return string.IsNullOrEmpty(format) ? Formatted() : value.ToString(format); } catch (FormatException) { return Formatted(); } }

        Rectangle ButtonRect { get { return M(new Rectangle(Width - S(30), 0, S(30), Height)); } }

        public void ShowDropDown()
        {
            var cal = new RmCalendar { Value = value, MinDate = minDate, MaxDate = maxDate, Style = Style, AccentColor = AccentColor, RightToLeft = RightToLeft, Font = Font };
            cal.Size = new Size(S(250), S(240));
            var host = new ToolStripControlHost(cal) { Margin = Padding.Empty, Padding = Padding.Empty, AutoSize = false, Size = cal.Size };
            drop = new ToolStripDropDown { Padding = Padding.Empty, DropShadowEnabled = true };
            drop.Items.Add(host);
            cal.DayClicked += (s, a) => { Value = cal.Value.Date + value.TimeOfDay; drop.Close(); };
            drop.Closed += (s, a) => { var d = drop; drop = null; BeginInvoke((Action)(() => d.Dispose())); Invalidate(); };
            drop.Show(this, new Point(Rtl ? Width - cal.Width : 0, Height));
            cal.Focus();
        }

        protected override void OnMouseUp(MouseEventArgs e) { base.OnMouseUp(e); if (e.Button == MouseButtons.Left && GlyphName == "calendar") ShowDropDown(); }

        protected override bool IsInputKey(Keys k) { return k == Keys.Up || k == Keys.Down || base.IsInputKey(k); }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Down && e.Alt || e.KeyCode == Keys.F4) ShowDropDown();
            else if (e.KeyCode == Keys.Up) Step(1);
            else if (e.KeyCode == Keys.Down) Step(-1);
            base.OnKeyDown(e);
        }

        protected override void OnMouseWheel(MouseEventArgs e) { Step(Math.Sign(e.Delta)); base.OnMouseWheel(e); }

        protected virtual void Step(int d) { Value = value.AddDays(d); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            var back = BackColor.A == 255 ? BackColor : t.Input;
            if (!Enabled) back = RmDraw.Blend(back, t.Window, 0.5);
            var border = Focused || drop != null ? t.Accent : RmDraw.Blend(t.Border, t.HotBorder, hover);
            RmDraw.Box(g, new RectangleF(0.5f, 0.5f, Width - 1, Height - 1), back, border, Sf(t.BorderWidth), Sf(t.Radius));
            var br = ButtonRect;
            if (hover > 0) RmDraw.Box(g, Rectangle.Inflate(br, -S(3), -S(3)), RmDraw.Alpha(t.Hot, (int)(255 * hover)), Color.Empty, 0, Sf(t.Radius));
            PaintButton(g, br, t);
            var tr = Rtl ? new Rectangle(br.Right + S(4), 0, Width - br.Width - S(12), Height) : new Rectangle(S(8), 0, Width - br.Width - S(12), Height);
            RmDraw.Text(g, Formatted(), Font, tr, Enabled ? (HasFore ? ForeColor : t.InputText) : t.DisabledText, ContentAlignment.MiddleLeft, Rtl);
        }

        protected virtual void PaintButton(Graphics g, Rectangle br, RmTheme t)
        {
            RmImages.Draw(g, "icon:" + GlyphName, null, Rectangle.Inflate(br, -S(7), -S(7)), t.SubtleText, Enabled);
        }
    }

    /// <summary>Time picker: hours / minutes (/ seconds) with spin buttons, wheel and arrow keys.</summary>
    public class RmTimePicker : RmDatePicker
    {
        int part;    // 0 = hours, 1 = minutes, 2 = seconds

        public RmTimePicker() { Format = "HH:mm"; Value = DateTime.Today.AddHours(DateTime.Now.Hour).AddMinutes(DateTime.Now.Minute); Size = new Size(120, 30); }

        [Category("Appearance"), DefaultValue("HH:mm")]
        public new string Format { get { return base.Format; } set { base.Format = string.IsNullOrEmpty(value) || value == "Short" || value == "Time" ? "HH:mm" : value; } }

        protected override string GlyphName { get { return "clock"; } }

        [Category("Appearance"), DefaultValue(false)]
        public bool ShowSeconds { get { return base.Format.Contains("s"); } set { base.Format = value ? "HH:mm:ss" : "HH:mm"; } }

        protected override string Formatted() { try { return Value.ToString(base.Format == "Long" ? "HH:mm:ss" : base.Format); } catch (FormatException) { return Value.ToString("HH:mm"); } }

        protected override void Step(int d)
        {
            if (part == 0) Value = Value.AddHours(d); else if (part == 1) Value = Value.AddMinutes(d); else Value = Value.AddSeconds(d);
        }

        protected override bool IsInputKey(Keys k) { return k == Keys.Left || k == Keys.Right || base.IsInputKey(k); }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            int parts = Formatted().Count(c => c == ':') + 1;
            if (e.KeyCode == Keys.Right) part = Math.Min(parts - 1, part + 1);
            else if (e.KeyCode == Keys.Left) part = Math.Max(0, part - 1);
            Invalidate();
            base.OnKeyDown(e);
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            var br = new Rectangle(Rtl ? 0 : Width - S(30), 0, S(30), Height);
            if (br.Contains(e.Location)) Step(e.Y < Height / 2 ? 1 : -1);
            else
            {
                var s = Formatted();
                int w = RmDraw.Measure(s, Font).Width, x = Rtl ? Width - S(8) - e.X : e.X - S(8);
                int parts = s.Count(c => c == ':') + 1;
                part = Math.Max(0, Math.Min(parts - 1, w > 0 ? x * parts / w : 0));
                Invalidate();
            }
            Focus();
            base.OnMouseUp(e);
        }

        protected override void PaintButton(Graphics g, Rectangle br, RmTheme t)
        {
            var up = new Rectangle(br.X, br.Y + S(2), br.Width, br.Height / 2 - S(2));
            var dn = new Rectangle(br.X, br.Y + br.Height / 2, br.Width, br.Height / 2 - S(2));
            RmDraw.Chevron(g, up, t.SubtleText, Sf(1.4f), false);
            RmDraw.Chevron(g, dn, t.SubtleText, Sf(1.4f), true);
            if (Focused)
            {   // underline the part being edited
                var s = Formatted();
                var segs = s.Split(':');
                int x = S(8);
                for (int i = 0; i < segs.Length && i < part; i++) x += RmDraw.Measure(segs[i] + ":", Font).Width - S(6);
                int w = RmDraw.Measure(segs[Math.Min(part, segs.Length - 1)], Font).Width - S(6);
                using (var p = new Pen(t.Accent, Sf(2))) g.DrawLine(p, Rtl ? Width - x - w : x + S(2), Height - S(7), Rtl ? Width - x : x + w + S(2), Height - S(7));
            }
        }
    }
}
