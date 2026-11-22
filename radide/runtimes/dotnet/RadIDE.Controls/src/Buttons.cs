// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// RmButton, RmToggle, RmCheckBox, RmRadioButton.
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
    public enum RmButtonKind { Default, Accent, Outline, Flat, Link }
    public enum RmCheckAlign { Left, Right }
    public enum RmImagePosition { Left, Top, Right }

    /// <summary>Modern button: Default / Accent / Outline / Flat / Link, rounded, image + text, optional split drop-down.</summary>
    [DefaultEvent("Click"), ToolboxItem(true)]
    public class RmButton : RmControl, IButtonControl
    {
        RmButtonKind kind = RmButtonKind.Default;
        RmImagePosition imagePos = RmImagePosition.Left;
        string image = "", dropDown = "";
        int radius = -1;
        Image imageObj;
        bool arrowDown, isDefault;
        List<RmItem> items = new List<RmItem>();

        public event EventHandler<RmItemEventArgs> DropDownItemClicked;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        protected override AccessibleRole RmRole { get { return AccessibleRole.PushButton; } }

        public RmButton() { Size = new Size(100, 32); TabStop = true; SetStyle(ControlStyles.Selectable | ControlStyles.StandardClick, true); }

        [Category("Appearance"), DefaultValue(RmButtonKind.Default)]
        public RmButtonKind Kind { get { return kind; } set { kind = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue(""), Description("Image file (relative to the program) or a glyph: icon:save, icon:home ...")]
        public string Image { get { return image; } set { image = value ?? ""; Invalidate(); } }

        [Category("Appearance"), DefaultValue(null)]
        public Image ImageObject { get { return imageObj; } set { imageObj = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue(RmImagePosition.Left)]
        public RmImagePosition ImagePosition { get { return imagePos; } set { imagePos = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue(-1), Description("-1 = the theme radius.")]
        public int CornerRadius { get { return radius; } set { radius = value; Invalidate(); } }

        [Category("Behavior"), DefaultValue(""), Description("Split drop-down items: \"Item1;Item2\" or a JSON array of {Text, Name, Image}.")]
        public string DropDownItems { get { return dropDown; } set { dropDown = value ?? ""; items = RmItem.Parse(dropDown); Invalidate(); } }

        [Category("Behavior"), DefaultValue(DialogResult.None)]
        public DialogResult DialogResult { get; set; }

        public void NotifyDefault(bool value) { isDefault = value; Invalidate(); }

        public void PerformClick() { if (Enabled) OnClick(EventArgs.Empty); }

        int ArrowWidth { get { return items.Count > 0 ? S(22) : 0; } }

        Rectangle ArrowRect { get { return M(new Rectangle(ClientSize.Width - ArrowWidth, 0, ArrowWidth, ClientSize.Height)); } }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            arrowDown = items.Count > 0 && ArrowRect.Contains(e.Location);
            base.OnMouseDown(e);
            if (arrowDown) ShowDropDown();
        }

        protected override void OnClick(EventArgs e)
        {
            if (arrowDown) { arrowDown = false; return; }
            var f = FindForm();
            if (f != null && DialogResult != DialogResult.None) f.DialogResult = DialogResult;
            base.OnClick(e);
        }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Space || e.KeyCode == Keys.Enter) { PerformClick(); e.Handled = true; }
            else if (e.KeyCode == Keys.Down && e.Alt && items.Count > 0) ShowDropDown();
            base.OnKeyDown(e);
        }

        protected override bool IsInputKey(Keys k) { return k == Keys.Enter || base.IsInputKey(k); }

        /// <summary>Opens the split drop-down menu.</summary>
        public void ShowDropDown()
        {
            var menu = new ContextMenuStrip { RightToLeft = RightToLeft, Renderer = new RmMenuRenderer(Theme) };
            for (int i = 0; i < items.Count; i++)
            {
                var it = items[i];
                if (it.Text == "-") { menu.Items.Add(new ToolStripSeparator()); continue; }
                var mi = new ToolStripMenuItem(it.Text) { Enabled = it.Enabled, Checked = it.Checked, Tag = i };
                var idx = i;
                mi.Click += (s, a) => RaiseItem(it, idx);
                menu.Items.Add(mi);
            }
            menu.Closed += (s, a) => BeginInvoke((Action)(() => menu.Dispose()));
            menu.Show(this, new Point(Rtl ? Width : 0, Height), Rtl ? ToolStripDropDownDirection.BelowLeft : ToolStripDropDownDirection.BelowRight);
        }

        /// <summary>Clicks a drop-down item by name (raises DropDownItemClicked).</summary>
        public void ClickItem(string name)
        {
            for (int i = 0; i < items.Count; i++) if (items[i].Key == name || items[i].Text == name) { RaiseItem(items[i], i); return; }
        }

        void RaiseItem(RmItem it, int idx)
        {
            RmItemEventArgs.Raise(this, DropDownItemClicked, new RmItemEventArgs(it.Key, idx, it.Text, it));
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            float rad = radius >= 0 ? Sf(radius) : Sf(t.Radius);
            var r = new RectangleF(0.5f, 0.5f, Width - 1f, Height - 1f);
            Color fill, border, fore;
            double h = hover, p = press;
            switch (kind)
            {
                case RmButtonKind.Accent:
                    fill = RmDraw.Blend(RmDraw.Blend(t.Accent, Color.White, 0.12 * h), Color.Black, 0.15 * p);
                    border = fill; fore = t.AccentText; break;
                case RmButtonKind.Outline:
                    fill = RmDraw.Alpha(t.Accent, (int)(28 * h + 50 * p));
                    border = t.Accent; fore = t.Dark ? RmDraw.Blend(t.Accent, Color.White, 0.45) : t.Accent; break;
                case RmButtonKind.Flat:
                    fill = h + p > 0 ? RmDraw.Alpha(RmDraw.Blend(t.Hot, t.Pressed, p), (int)(255 * Math.Max(h, p))) : Color.Empty;
                    border = Color.Empty; fore = Fore(t); break;
                case RmButtonKind.Link:
                    fill = Color.Empty; border = Color.Empty;
                    fore = RmDraw.Blend(t.Dark ? RmDraw.Blend(t.Accent, Color.White, 0.4) : t.Accent, t.WindowText, 0.25 * h); break;
                default:
                    fill = RmDraw.Blend(RmDraw.Blend(t.Face, t.Hot, h), t.Pressed, p);
                    border = RmDraw.Blend(t.Border, t.HotBorder, Math.Max(h, isDefault ? 0.7 : 0)); fore = t.FaceText; break;
            }
            if (!Enabled) { fore = t.DisabledText; if (kind == RmButtonKind.Accent) { fill = RmDraw.Blend(t.Face, t.Accent, 0.35); border = fill; fore = RmDraw.Blend(t.AccentText, fill, 0.35); } }
            if (HasFore && Enabled) fore = ForeColor;
            if (BackColor.A == 255 && kind != RmButtonKind.Link && kind != RmButtonKind.Flat) { fill = RmDraw.Blend(RmDraw.Blend(BackColor, Color.White, 0.12 * h), Color.Black, 0.15 * p); border = fill; }
            g.SmoothingMode = SmoothingMode.AntiAlias;
            RmDraw.Box(g, r, fill, border, Sf(t.BorderWidth), rad);
            var content = new Rectangle(S(6), S(3), Width - S(12) - ArrowWidth, Height - S(6));
            if (Rtl) content.X = S(6) + ArrowWidth;
            if (items.Count > 0)
            {
                var ar = ArrowRect;
                using (var pen = new Pen(RmDraw.Alpha(fore, 70)))
                    g.DrawLine(pen, Rtl ? ar.Right : ar.X, S(6), Rtl ? ar.Right : ar.X, Height - S(6));
                RmDraw.Chevron(g, ar, fore, Sf(1.4f));
            }
            bool hasImg = imageObj != null || image.Length > 0;
            int isz = imagePos == RmImagePosition.Top ? Math.Min(S(32), Math.Max(S(16), content.Height - Font.Height - S(4))) : Math.Min(S(20), content.Height);
            var ts = RmDraw.Measure(Text, Font);
            if (hasImg && imagePos == RmImagePosition.Top)
            {
                int total = isz + (Text.Length > 0 ? S(2) + ts.Height : 0);
                int y = content.Y + (content.Height - total) / 2;
                RmImages.Draw(g, image, imageObj, new Rectangle(content.X + (content.Width - isz) / 2, y, isz, isz), fore, Enabled);
                RmDraw.Text(g, Text, Font, new Rectangle(content.X, y + isz + S(2), content.Width, ts.Height), fore, ContentAlignment.MiddleCenter, Rtl);
            }
            else if (hasImg)
            {
                bool imgRight = (imagePos == RmImagePosition.Right) != Rtl;
                int gap = Text.Length > 0 ? S(6) : 0;
                int total = Math.Min(content.Width, isz + gap + ts.Width);
                int x = content.X + (content.Width - total) / 2;
                var ir = new Rectangle(imgRight ? x + total - isz : x, content.Y + (content.Height - isz) / 2, isz, isz);
                RmImages.Draw(g, image, imageObj, ir, fore, Enabled);
                var tr = new Rectangle(imgRight ? x : x + isz + gap, content.Y, Math.Max(0, total - isz - gap), content.Height);
                RmDraw.Text(g, Text, Font, tr, fore, ContentAlignment.MiddleCenter, Rtl);
            }
            else
            {
                var f = kind == RmButtonKind.Link && hover > 0.5 ? new Font(Font, FontStyle.Underline) : Font;
                RmDraw.Text(g, Text, f, content, fore, ContentAlignment.MiddleCenter, Rtl);
                if (!ReferenceEquals(f, Font)) f.Dispose();
            }
            FocusCue(g, new Rectangle(S(3), S(3), Width - S(7), Height - S(7)), t, Math.Max(0, rad - S(2)));
        }
    }

    /// <summary>On / off switch with an animated knob.</summary>
    [DefaultEvent("CheckedChanged"), DefaultProperty("Checked")]
    public class RmToggle : RmControl
    {
        bool chk;
        double pos;
        string onText = "On", offText = "Off";

        public event EventHandler CheckedChanged;

        protected override AccessibleRole RmRole { get { return AccessibleRole.CheckButton; } }

        RmCheckAlign checkAlign = RmCheckAlign.Left;

        /// <summary>Side of the box / switch (Right = after the text); mirrored when RightToLeft.</summary>
        [Category("Appearance"), DefaultValue(RmCheckAlign.Left)]
        public RmCheckAlign CheckAlign { get { return checkAlign; } set { checkAlign = value; Invalidate(); } }

        bool BoxRight { get { return (checkAlign == RmCheckAlign.Right) != Rtl; } }

        public RmToggle() { Size = new Size(90, 26); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior"), DefaultValue(false), Bindable(true)]
        public bool Checked
        {
            get { return chk; }
            set
            {
                if (chk == value) return;
                chk = value;
                if (!IsHandleCreated) pos = chk ? 1 : 0;
                Animate();
                var h = CheckedChanged;
                if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Category("Appearance"), DefaultValue("On")]
        public string OnText { get { return onText; } set { onText = value ?? ""; Invalidate(); } }

        [Category("Appearance"), DefaultValue("Off")]
        public string OffText { get { return offText; } set { offText = value ?? ""; Invalidate(); } }

        /// <summary>Value as the IDE's neutral protocol sees it (= Checked).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public bool Value { get { return Checked; } set { Checked = value; } }

        public void Toggle() { Checked = !Checked; }
        public void PerformClick() { OnClick(EventArgs.Empty); }

        protected override bool AnimateMore()
        {
            pos = RmAnimator.Step(pos, chk ? 1 : 0, Theme.AnimMs * 2);
            return pos != (chk ? 1 : 0);
        }

        protected override void OnClick(EventArgs e) { if (Enabled) Checked = !Checked; base.OnClick(e); }

        protected override void OnKeyDown(KeyEventArgs e) { if (e.KeyCode == Keys.Space) { Checked = !Checked; e.Handled = true; } base.OnKeyDown(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            int th = Math.Min(Height - S(4), S(22)), tw = (int)(th * 1.9);
            var track = BoxRight ? new Rectangle(Width - tw - S(2), (Height - th) / 2, tw, th) : new Rectangle(S(2), (Height - th) / 2, tw, th);
            double p = pos;
            Color off = t.Dark ? RmDraw.Blend(t.Face, Color.White, 0.08) : RmDraw.Blend(t.Border, t.Window, 0.35);
            Color fill = RmDraw.Blend(off, t.Accent, p);
            if (!Enabled) fill = RmDraw.Blend(fill, t.Window, 0.5);
            fill = RmDraw.Blend(fill, Color.White, 0.08 * hover);
            float rad = t.Radius == 0 ? 0 : th / 2f;
            RmDraw.Box(g, track, fill, Color.Empty, 0, rad);
            int k = th - S(6);
            double x = Rtl ? track.Right - S(3) - k - (tw - k - S(6)) * p : track.X + S(3) + (tw - k - S(6)) * p;   // on = towards the reading end
            var knob = new RectangleF((float)x, track.Y + S(3), k, k);
            using (var sh = new SolidBrush(Color.FromArgb(40, 0, 0, 0))) if (rad > 0) g.FillEllipse(sh, knob.X, knob.Y + 1, k, k);
            RmDraw.Box(g, knob, Color.White, Color.Empty, 0, rad > 0 ? k / 2f : 0);
            var text = chk ? onText : offText;
            var tr = BoxRight ? new Rectangle(0, 0, Math.Max(0, track.X - S(8)), Height)
                              : new Rectangle(track.Right + S(8), 0, Math.Max(0, Width - track.Right - S(8)), Height);
            RmDraw.Text(g, text, Font, tr, Fore(t), ContentAlignment.MiddleLeft, Rtl);
            FocusCue(g, Rectangle.Inflate(track, S(2), S(2)), t, rad + S(2));
        }
    }

    /// <summary>Themed check box (Checked + Indeterminate).</summary>
    [DefaultEvent("CheckedChanged"), DefaultProperty("Checked")]
    public class RmCheckBox : RmControl
    {
        bool chk, indet;
        double anim;

        public event EventHandler CheckedChanged;

        protected override AccessibleRole RmRole { get { return AccessibleRole.CheckButton; } }

        RmCheckAlign checkAlign = RmCheckAlign.Left;

        /// <summary>Side of the box / switch (Right = after the text); mirrored when RightToLeft.</summary>
        [Category("Appearance"), DefaultValue(RmCheckAlign.Left)]
        public RmCheckAlign CheckAlign { get { return checkAlign; } set { checkAlign = value; Invalidate(); } }

        bool BoxRight { get { return (checkAlign == RmCheckAlign.Right) != Rtl; } }

        public RmCheckBox() { Size = new Size(120, 24); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior"), DefaultValue(false)]
        public bool Checked
        {
            get { return chk; }
            set { if (chk == value && !indet) return; chk = value; indet = false; Animate(); var h = CheckedChanged; if (h != null) h(this, EventArgs.Empty); }
        }

        [Category("Behavior"), DefaultValue(false), Description("The third state (a dash); a click clears it.")]
        public bool Indeterminate { get { return indet; } set { indet = value; Invalidate(); } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public bool Value { get { return Checked; } set { Checked = value; } }

        protected override bool AnimateMore() { anim = RmAnimator.Step(anim, chk ? 1 : 0, Theme.AnimMs); return anim != (chk ? 1 : 0); }

        public void Toggle() { Checked = !Checked; }
        public void PerformClick() { OnClick(EventArgs.Empty); }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public CheckState CheckState
        {
            get { return indet ? CheckState.Indeterminate : chk ? CheckState.Checked : CheckState.Unchecked; }
            set { if (value == CheckState.Indeterminate) Indeterminate = true; else Checked = value == CheckState.Checked; }
        }

        protected override void OnClick(EventArgs e) { if (Enabled) Checked = indet ? true : !Checked; base.OnClick(e); }

        protected override void OnKeyDown(KeyEventArgs e) { if (e.KeyCode == Keys.Space) { Checked = !Checked; e.Handled = true; } base.OnKeyDown(e); }

        protected override void OnHandleCreated(EventArgs e) { anim = chk ? 1 : 0; base.OnHandleCreated(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            int b = S(16);
            var box = BoxRight ? new Rectangle(Width - b - S(2), (Height - b) / 2, b, b) : new Rectangle(S(2), (Height - b) / 2, b, b);
            float rad = Math.Min(Sf(t.Radius), b / 3f);
            bool on = chk || indet;
            Color fill = on ? RmDraw.Blend(t.Input, t.Accent, Math.Max(anim, indet ? 1 : 0)) : RmDraw.Blend(t.Input, t.Hot, hover);
            Color border = on ? t.Accent : RmDraw.Blend(t.Border, t.HotBorder, hover);
            if (!Enabled) { fill = RmDraw.Blend(fill, t.Window, 0.5); border = t.DisabledText; }
            RmDraw.Box(g, box, fill, border, Sf(1), rad);
            if (indet) using (var p = new Pen(t.AccentText, Sf(2)) { StartCap = LineCap.Round, EndCap = LineCap.Round })
                g.DrawLine(p, box.X + b * 0.28f, box.Y + b / 2f, box.Right - b * 0.28f, box.Y + b / 2f);
            else if (anim > 0.05) RmDraw.Check(g, box, RmDraw.Alpha(t.AccentText, (int)(255 * anim)), Sf(1.8f));
            var tr = BoxRight ? new Rectangle(0, 0, box.X - S(6), Height) : new Rectangle(box.Right + S(6), 0, Width - box.Right - S(6), Height);
            RmDraw.Text(g, Text, Font, tr, Fore(t), ContentAlignment.MiddleLeft, Rtl);
            FocusCue(g, Rectangle.Inflate(box, S(2), S(2)), t, rad + 2);
        }
    }

    /// <summary>Themed radio button; siblings with the same parent are exclusive.</summary>
    [DefaultEvent("CheckedChanged"), DefaultProperty("Checked")]
    public class RmRadioButton : RmControl
    {
        bool chk;
        double anim;

        public event EventHandler CheckedChanged;

        protected override AccessibleRole RmRole { get { return AccessibleRole.RadioButton; } }

        RmCheckAlign checkAlign = RmCheckAlign.Left;

        /// <summary>Side of the box / switch (Right = after the text); mirrored when RightToLeft.</summary>
        [Category("Appearance"), DefaultValue(RmCheckAlign.Left)]
        public RmCheckAlign CheckAlign { get { return checkAlign; } set { checkAlign = value; Invalidate(); } }

        bool BoxRight { get { return (checkAlign == RmCheckAlign.Right) != Rtl; } }

        public RmRadioButton() { Size = new Size(120, 24); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        [Category("Behavior"), DefaultValue(false)]
        public bool Checked
        {
            get { return chk; }
            set
            {
                if (chk == value) return;
                chk = value;
                if (chk && Parent != null)
                    foreach (var r in Parent.Controls.OfType<RmRadioButton>()) if (r != this) r.Checked = false;
                Animate();
                var h = CheckedChanged;
                if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public bool Value { get { return Checked; } set { Checked = value; } }

        protected override bool AnimateMore() { anim = RmAnimator.Step(anim, chk ? 1 : 0, Theme.AnimMs); return anim != (chk ? 1 : 0); }

        protected override void OnClick(EventArgs e) { if (Enabled) Checked = true; base.OnClick(e); }

        protected override void OnKeyDown(KeyEventArgs e) { if (e.KeyCode == Keys.Space) { Checked = true; e.Handled = true; } base.OnKeyDown(e); }

        protected override void OnHandleCreated(EventArgs e) { anim = chk ? 1 : 0; base.OnHandleCreated(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            int b = S(16);
            var box = BoxRight ? new Rectangle(Width - b - S(2), (Height - b) / 2, b, b) : new Rectangle(S(2), (Height - b) / 2, b, b);
            Color border = chk ? t.Accent : RmDraw.Blend(t.Border, t.HotBorder, hover);
            if (!Enabled) border = t.DisabledText;
            using (var br = new SolidBrush(RmDraw.Blend(t.Input, t.Hot, chk ? 0 : hover))) g.FillEllipse(br, box);
            using (var p = new Pen(border, Sf(chk ? 1.6f : 1f))) g.DrawEllipse(p, box.X + 0.5f, box.Y + 0.5f, b - 1, b - 1);
            if (anim > 0.02)
            {
                float d = (b - S(8)) * (float)anim;
                using (var br = new SolidBrush(Enabled ? t.Accent : t.DisabledText)) g.FillEllipse(br, box.X + (b - d) / 2f, box.Y + (b - d) / 2f, d, d);
            }
            var tr = BoxRight ? new Rectangle(0, 0, box.X - S(6), Height) : new Rectangle(box.Right + S(6), 0, Width - box.Right - S(6), Height);
            RmDraw.Text(g, Text, Font, tr, Fore(t), ContentAlignment.MiddleLeft, Rtl);
            FocusCue(g, Rectangle.Inflate(box, S(2), S(2)), t, b);
        }
    }

    /// <summary>Menu renderer in the theme colours (drop-downs of buttons, ribbon, combo, side bar).</summary>
    public class RmMenuRenderer : ToolStripProfessionalRenderer
    {
        readonly RmTheme t;
        public RmMenuRenderer(RmTheme theme) : base(new RmColorTable(theme)) { t = theme; RoundedEdges = false; }

        protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e)
        {
            e.TextColor = e.Item.Enabled ? (e.Item.Selected && t.Name == "Metro" ? t.AccentText : t.WindowText) : t.DisabledText;
            base.OnRenderItemText(e);
        }

        protected override void OnRenderArrow(ToolStripArrowRenderEventArgs e) { e.ArrowColor = t.WindowText; base.OnRenderArrow(e); }
    }

    public class RmColorTable : ProfessionalColorTable
    {
        readonly RmTheme t;
        public RmColorTable(RmTheme theme) { t = theme; UseSystemColors = false; }
        Color Menu { get { return t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.05) : t.Surface; } }
        public override Color ToolStripDropDownBackground { get { return Menu; } }
        public override Color ImageMarginGradientBegin { get { return Menu; } }
        public override Color ImageMarginGradientMiddle { get { return Menu; } }
        public override Color ImageMarginGradientEnd { get { return Menu; } }
        public override Color MenuBorder { get { return t.Border; } }
        public override Color MenuItemBorder { get { return t.Name == "Metro" ? t.Accent : t.HotBorder; } }
        public override Color MenuItemSelected { get { return t.Name == "Metro" ? t.Accent : t.Hot; } }
        public override Color MenuItemSelectedGradientBegin { get { return MenuItemSelected; } }
        public override Color MenuItemSelectedGradientEnd { get { return MenuItemSelected; } }
        public override Color MenuItemPressedGradientBegin { get { return t.Pressed; } }
        public override Color MenuItemPressedGradientEnd { get { return t.Pressed; } }
        public override Color SeparatorDark { get { return t.Border; } }
        public override Color SeparatorLight { get { return Menu; } }
        public override Color CheckBackground { get { return RmDraw.Alpha(t.Accent, 60); } }
        public override Color CheckSelectedBackground { get { return RmDraw.Alpha(t.Accent, 90); } }
        public override Color CheckPressedBackground { get { return RmDraw.Alpha(t.Accent, 120); } }
        public override Color ToolStripBorder { get { return t.Border; } }
        public override Color ToolStripGradientBegin { get { return t.Window; } }
        public override Color ToolStripGradientMiddle { get { return t.Window; } }
        public override Color ToolStripGradientEnd { get { return t.Window; } }
        public override Color MenuStripGradientBegin { get { return t.Window; } }
        public override Color MenuStripGradientEnd { get { return t.Window; } }
        public override Color StatusStripGradientBegin { get { return t.Window; } }
        public override Color StatusStripGradientEnd { get { return t.Window; } }
        public override Color ButtonSelectedHighlight { get { return t.Hot; } }
        public override Color ButtonSelectedGradientBegin { get { return t.Hot; } }
        public override Color ButtonSelectedGradientEnd { get { return t.Hot; } }
        public override Color ButtonSelectedBorder { get { return t.HotBorder; } }
        public override Color ButtonPressedGradientBegin { get { return t.Pressed; } }
        public override Color ButtonPressedGradientEnd { get { return t.Pressed; } }
    }
}
