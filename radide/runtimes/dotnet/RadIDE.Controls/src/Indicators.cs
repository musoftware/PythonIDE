// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// RmProgress, RmGauge, RmTile.
#nullable disable
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    public enum RmProgressKind { Bar, Circle, Marquee }
    public enum RmGaugeKind { Circular, Linear }
    public enum RmTileSize { Small, Medium, Wide, Large }

    /// <summary>Linear / circular / marquee progress with a smooth value animation.</summary>
    [DefaultProperty("Value")]
    public class RmProgress : RmControl
    {
        int min, max = 100, val;
        double shown, marquee;
        RmProgressKind kind = RmProgressKind.Bar;
        bool showText;

        protected override AccessibleRole RmRole { get { return AccessibleRole.ProgressBar; } }
        protected override string RmAccessibleName { get { return string.IsNullOrEmpty(Text) ? Name : Text; } }
        protected override string RmAccessibleValue { get { return val.ToString(System.Globalization.CultureInfo.InvariantCulture); } }

        public RmProgress() { Size = new Size(200, 8); SetStyle(ControlStyles.Selectable, false); TabStop = false; }

        [Category("Behavior"), DefaultValue(0)]
        public int Value { get { return val; } set { val = Math.Max(min, Math.Min(max, value)); Animate(); } }

        [Category("Behavior"), DefaultValue(0)]
        public int Minimum { get { return min; } set { min = value; if (max < min) max = min; Value = val; } }

        [Category("Behavior"), DefaultValue(100)]
        public int Maximum { get { return max; } set { max = Math.Max(min, value); Value = val; } }

        [Category("Appearance"), DefaultValue(RmProgressKind.Bar)]
        public RmProgressKind Kind { get { return kind; } set { kind = value; Animate(); Invalidate(); } }

        [Category("Appearance"), DefaultValue(false)]
        public bool ShowText { get { return showText; } set { showText = value; Invalidate(); } }

        public void Increment(int by) { Value = val + by; }

        string textFormat = "";

        /// <summary>Text of ShowText: {0} = value, {1} = maximum, {2} = percent ("" = "{2}%").</summary>
        [Category("Appearance"), DefaultValue("")]
        public string TextFormat { get { return textFormat; } set { textFormat = value ?? ""; Invalidate(); } }

        string Caption()
        {
            int pct = (int)Math.Round(Frac * 100);
            if (textFormat.Length == 0) return pct.ToString(CultureInfo.InvariantCulture) + "%";
            try { return string.Format(CultureInfo.InvariantCulture, textFormat, (int)Math.Round(shown), max, pct); } catch (FormatException) { return textFormat; }
        }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); shown = val; if (kind == RmProgressKind.Marquee) Animate(); }
        protected override void OnVisibleChanged(EventArgs e) { base.OnVisibleChanged(e); if (Visible) Animate(); }

        protected override bool AnimateMore()
        {
            shown += (val - shown) * 0.25;
            if (Math.Abs(val - shown) < 0.05) shown = val;
            if (kind == RmProgressKind.Marquee) { marquee = (marquee + 0.012) % 1.0; return Visible && IsHandleCreated; }
            return shown != val;
        }

        double Frac { get { return max == min ? 0 : (shown - min) / (max - min); } }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Color track = t.Dark ? RmDraw.Blend(t.Face, Color.White, 0.08) : RmDraw.Blend(t.Border, t.Window, 0.5);
            Color bar = Enabled ? t.Accent : t.DisabledText;
            if (HasFore) bar = ForeColor;
            if (kind == RmProgressKind.Circle)
            {
                float d = Math.Min(Width, Height) - Sf(4), w = Math.Max(Sf(3), d / 10f);
                var r = new RectangleF((Width - d) / 2f + w / 2, (Height - d) / 2f + w / 2, d - w, d - w);
                using (var p = new Pen(track, w)) g.DrawEllipse(p, r);
                using (var p = new Pen(bar, w) { StartCap = LineCap.Round, EndCap = LineCap.Round })
                {
                    float sweep = (float)(360 * Frac);
                    if (sweep > 0.5f) g.DrawArc(p, r, -90, Rtl ? -sweep : sweep);
                }
                if (showText) RmDraw.Text(g, Caption(), Font, ClientRectangle, Fore(t), ContentAlignment.MiddleCenter);
                return;
            }
            int textW = showText && kind == RmProgressKind.Bar ? RmDraw.Measure("100%", Font).Width + S(6) : 0;
            int h = Math.Min(Height, Math.Max(S(4), showText ? Height : Height));
            var tr = new Rectangle(Rtl ? textW : 0, (Height - h) / 2, Width - textW, h);
            float rad = t.Radius == 0 ? 0 : h / 2f;
            RmDraw.Box(g, tr, track, Color.Empty, 0, rad);
            if (kind == RmProgressKind.Marquee)
            {
                int w = tr.Width / 3;
                int x = (int)(tr.X - w + (tr.Width + w) * marquee);
                if (Rtl) x = tr.Right - (x - tr.X) - w;
                var clip = g.Clip;
                using (var path = RmDraw.Round(tr, rad)) g.SetClip(path);
                RmDraw.Box(g, new Rectangle(x, tr.Y, w, tr.Height), bar, Color.Empty, 0, rad);
                g.Clip = clip;
                return;
            }
            int fw = (int)(tr.Width * Frac);
            if (fw > 0) RmDraw.Box(g, Rtl ? new Rectangle(tr.Right - fw, tr.Y, fw, tr.Height) : new Rectangle(tr.X, tr.Y, fw, tr.Height), bar, Color.Empty, 0, rad);
            if (textW > 0)
                RmDraw.Text(g, Caption(), Font,
                            Rtl ? new Rectangle(0, 0, textW, Height) : new Rectangle(Width - textW, 0, textW, Height), Fore(t), ContentAlignment.MiddleRight, Rtl);
        }
    }

    /// <summary>Circular (240 degrees) or linear gauge with coloured ranges and an animated needle.</summary>
    [DefaultProperty("Value")]
    public class RmGauge : RmControl
    {
        double min, max = 100, val, shown;
        string ranges = "", unit = "";
        RmGaugeKind kind = RmGaugeKind.Circular;
        List<Tuple<double, double, Color>> bands = new List<Tuple<double, double, Color>>();

        public RmGauge() { Size = new Size(160, 140); TabStop = false; SetStyle(ControlStyles.Selectable, false); }

        protected override AccessibleRole RmRole { get { return AccessibleRole.ProgressBar; } }
        protected override string RmAccessibleValue { get { return val.ToString(System.Globalization.CultureInfo.InvariantCulture); } }

        [Category("Behavior"), DefaultValue(0d)]
        public double Value { get { return val; } set { val = Math.Max(min, Math.Min(max, value)); Animate(); } }

        [Category("Behavior"), DefaultValue(0d)]
        public double Minimum { get { return min; } set { min = value; if (max < min) max = min; Value = val; } }

        [Category("Behavior"), DefaultValue(100d)]
        public double Maximum { get { return max; } set { max = Math.Max(min, value); Value = val; } }

        [Category("Appearance"), DefaultValue(""), Description("Coloured ranges: \"0-60:#2E7D32;60-80:#F9A825;80-100:#C62828\".")]
        public string Ranges
        {
            get { return ranges; }
            set
            {
                ranges = value ?? "";
                bands.Clear();
                foreach (var part in RmScript.Split(ranges))
                {
                    var colon = part.IndexOf(':');
                    var span = colon > 0 ? part.Substring(0, colon) : part;
                    var dash = span.IndexOf('-', 1);
                    double a, b;
                    if (dash > 0 && double.TryParse(span.Substring(0, dash), NumberStyles.Float, CultureInfo.InvariantCulture, out a) &&
                        double.TryParse(span.Substring(dash + 1), NumberStyles.Float, CultureInfo.InvariantCulture, out b))
                        bands.Add(Tuple.Create(a, b, colon > 0 ? RmDraw.Parse(part.Substring(colon + 1)) : Color.Empty));
                }
                Invalidate();
            }
        }

        [Category("Appearance"), DefaultValue("")]
        public string Unit { get { return unit; } set { unit = value ?? ""; Invalidate(); } }

        [Category("Appearance"), DefaultValue(RmGaugeKind.Circular)]
        public RmGaugeKind Kind { get { return kind; } set { kind = value; Invalidate(); } }

        string title = "";
        int decimals = -1;
        bool showTicks = true;

        [Category("Appearance"), DefaultValue("")]
        public string Title { get { return title; } set { title = value ?? ""; Invalidate(); } }

        [Category("Appearance"), DefaultValue(-1), Description("Decimals of the value text (-1 = automatic).")]
        public int Decimals { get { return decimals; } set { decimals = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue(true)]
        public bool ShowTicks { get { return showTicks; } set { showTicks = value; Invalidate(); } }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); shown = val; }

        protected override bool AnimateMore()
        {
            shown += (val - shown) * 0.18;
            if (Math.Abs(val - shown) < (max - min) / 2000.0) shown = val;
            return shown != val;
        }

        Color ValueColor(RmTheme t)
        {
            foreach (var b in bands) if (val >= b.Item1 && val <= b.Item2 && !b.Item3.IsEmpty) return b.Item3;
            return t.Accent;
        }

        string ValueText { get { return Math.Round(shown, decimals >= 0 ? Math.Min(decimals, 6) : max - min <= 20 ? 1 : 0).ToString(CultureInfo.InvariantCulture) + (unit.Length > 0 ? " " + unit : ""); } }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Color track = t.Dark ? RmDraw.Blend(t.Face, Color.White, 0.08) : RmDraw.Blend(t.Border, t.Window, 0.55);
            Func<double, double> F = v => max == min ? 0 : Math.Max(0, Math.Min(1, (v - min) / (max - min)));
            if (kind == RmGaugeKind.Linear)
            {
                int th = S(10);
                var tr = new Rectangle(S(6), Height / 2 - th / 2, Width - S(12), th);
                RmDraw.Box(g, tr, track, Color.Empty, 0, t.Radius == 0 ? 0 : th / 2f);
                foreach (var b in bands)
                {
                    int x0 = (int)(tr.X + tr.Width * F(b.Item1)), x1 = (int)(tr.X + tr.Width * F(b.Item2));
                    var br = new Rectangle(x0, tr.Y + th - S(3), x1 - x0, S(3));
                    using (var bb = new SolidBrush(RmDraw.Alpha(b.Item3.IsEmpty ? t.Accent : b.Item3, 200))) g.FillRectangle(bb, M(br));
                }
                int fw = (int)(tr.Width * F(shown));
                RmDraw.Box(g, M(new Rectangle(tr.X, tr.Y, fw, th - S(3))), ValueColor(t), Color.Empty, 0, t.Radius == 0 ? 0 : (th - S(3)) / 2f);
                RmDraw.Text(g, ValueText, Font, new Rectangle(0, 0, Width, tr.Y - S(2)), Fore(t), ContentAlignment.BottomCenter, Rtl);
                RmDraw.Text(g, min.ToString(CultureInfo.InvariantCulture), Font, M(new Rectangle(tr.X, tr.Bottom + S(2), Width / 2, Font.Height)), t.SubtleText, ContentAlignment.TopLeft);
                RmDraw.Text(g, max.ToString(CultureInfo.InvariantCulture), Font, M(new Rectangle(Width / 2, tr.Bottom + S(2), Width / 2 - S(6), Font.Height)), t.SubtleText, ContentAlignment.TopRight);
                return;
            }
            float size = Math.Min(Width, Height * 1.15f) - Sf(8);
            float w = Math.Max(Sf(6), size / 11f);
            var rect = new RectangleF((Width - size) / 2f + w / 2, Sf(4) + w / 2, size - w, size - w);
            const float start = 150, sweep = 240;
            using (var p = new Pen(track, w) { StartCap = LineCap.Round, EndCap = LineCap.Round }) g.DrawArc(p, rect, start, sweep);
            foreach (var b in bands)
            {
                float a0 = (float)(start + sweep * F(b.Item1)), a1 = (float)(start + sweep * F(b.Item2));
                var inner = RectangleF.Inflate(rect, -w * 0.9f, -w * 0.9f);
                using (var p = new Pen(RmDraw.Alpha(b.Item3.IsEmpty ? t.Accent : b.Item3, 210), Math.Max(2, w / 3f))) g.DrawArc(p, inner, a0, Math.Max(0.5f, a1 - a0));
            }
            if (showTicks)
                using (var tp = new Pen(RmDraw.Alpha(t.SubtleText, 150), Sf(1)))
                {
                    float rOut = rect.Width / 2 - w * 1.5f, rIn = rOut - Sf(5);
                    float tcx = rect.X + rect.Width / 2, tcy = rect.Y + rect.Height / 2;
                    for (int k = 0; k <= 10; k++)
                    {
                        double a = (start + sweep * k / 10.0) * Math.PI / 180;
                        if (rIn <= 0) break;
                        g.DrawLine(tp, tcx + (float)Math.Cos(a) * rOut, tcy + (float)Math.Sin(a) * rOut, tcx + (float)Math.Cos(a) * rIn, tcy + (float)Math.Sin(a) * rIn);
                    }
                }
            float vs = (float)(sweep * F(shown));
            if (vs > 0.3f) using (var p = new Pen(ValueColor(t), w) { StartCap = LineCap.Round, EndCap = LineCap.Round }) g.DrawArc(p, rect, start, vs);
            // needle
            float cx = rect.X + rect.Width / 2, cy = rect.Y + rect.Height / 2, len = rect.Width / 2 - w * 1.4f;
            double ang = (start + vs) * Math.PI / 180;
            using (var p = new Pen(t.WindowText, Sf(2.2f)) { EndCap = LineCap.Round, StartCap = LineCap.Round })
                g.DrawLine(p, cx, cy, cx + (float)(Math.Cos(ang) * len), cy + (float)(Math.Sin(ang) * len));
            float hub = Sf(5);
            using (var b = new SolidBrush(t.WindowText)) g.FillEllipse(b, cx - hub, cy - hub, 2 * hub, 2 * hub);
            using (var bf = new Font(Font.FontFamily, Math.Max(8f, Font.Size * 1.5f), FontStyle.Bold))
            {
                RmDraw.Text(g, ValueText, bf, new Rectangle(0, (int)(cy + rect.Height * 0.16f), Width, bf.Height + S(4)), Fore(t), ContentAlignment.MiddleCenter, Rtl);
                if (title.Length > 0)
                    RmDraw.Text(g, title, Font, new Rectangle(0, (int)(cy + rect.Height * 0.16f) + bf.Height + S(2), Width, Font.Height + S(2)), t.SubtleText, ContentAlignment.MiddleCenter, Rtl);
            }
        }
    }

    /// <summary>Metro tile: colour, title, count badge and an image; hover brightens, press shrinks.</summary>
    [DefaultEvent("Click")]
    public class RmTile : RmControl
    {
        string title = "", image = "";
        int count;
        Color tileColor = Color.Empty;
        RmTileSize tileSize = RmTileSize.Medium;

        protected override AccessibleRole RmRole { get { return AccessibleRole.PushButton; } }

        public RmTile() { Size = new Size(150, 150); TabStop = true; SetStyle(ControlStyles.Selectable, true); Cursor = Cursors.Hand; }

        [Category("Appearance"), DefaultValue("")]
        public string Title { get { return title; } set { title = value ?? ""; Invalidate(); } }

        [Category("Appearance"), DefaultValue(0)]
        public int Count { get { return count; } set { count = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue("")]
        public string Image { get { return image; } set { image = value ?? ""; Invalidate(); } }

        [Category("Appearance")]
        public Color TileColor { get { return tileColor; } set { tileColor = value; Invalidate(); } }
        public bool ShouldSerializeTileColor() { return !tileColor.IsEmpty; }

        /// <summary>Content layout (the .form property "Size"): Small = image only, Medium, Wide, Large.</summary>
        [Category("Appearance"), DefaultValue(RmTileSize.Medium)]
        public RmTileSize TileSize { get { return tileSize; } set { tileSize = value; Invalidate(); } }

        public void PerformClick() { OnClick(EventArgs.Empty); }

        protected override void OnKeyDown(KeyEventArgs e) { if (e.KeyCode == Keys.Space || e.KeyCode == Keys.Enter) PerformClick(); base.OnKeyDown(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Color c = tileColor.IsEmpty ? t.Accent : tileColor;
            c = RmDraw.Blend(RmDraw.Blend(c, Color.White, 0.12 * hover), Color.Black, 0.12 * press);
            float shrink = Sf(3) * (float)press;
            var r = new RectangleF(shrink, shrink, Width - 2 * shrink - 1, Height - 2 * shrink - 1);
            RmDraw.Box(g, r, c, hover > 0 ? RmDraw.Alpha(Color.White, (int)(90 * hover)) : Color.Empty, Sf(2), Sf(t.Radius));
            var fore = HasFore ? ForeColor : RmDraw.Contrast(c);
            int pad = S(10);
            if (tileSize == RmTileSize.Small)
            {
                int s = (int)(Math.Min(r.Width, r.Height) * 0.55f);
                if (!RmImages.Draw(g, image, null, new Rectangle((Width - s) / 2, (Height - s) / 2, s, s), fore))
                    RmDraw.Text(g, title, Font, Rectangle.Round(r), fore, ContentAlignment.MiddleCenter, Rtl, true);
            }
            else
            {
                int s = tileSize == RmTileSize.Large ? S(64) : S(40);
                var ir = tileSize == RmTileSize.Wide ? M(new Rectangle(pad, (Height - s) / 2 - S(8), s, s)) : new Rectangle((Width - s) / 2, Math.Max(pad, (int)(Height * 0.36f) - s / 2), s, s);
                RmImages.Draw(g, image, null, ir, fore);
                using (var tf = new Font(Font.FontFamily, Font.Size, FontStyle.Regular))
                    RmDraw.Text(g, title, tf, new Rectangle(pad, Height - pad - Font.Height - S(2), Width - 2 * pad - (count != 0 ? S(36) : 0), Font.Height + S(4)), fore, ContentAlignment.BottomLeft, Rtl);
                if (count != 0)
                {
                    using (var cf = new Font(Font.FontFamily, Font.Size * (tileSize == RmTileSize.Medium ? 1.6f : 2.2f), FontStyle.Bold))
                    {
                        var cr = tileSize == RmTileSize.Medium ? new Rectangle(pad, Height - pad - Font.Height - S(2), Width - 2 * pad, Font.Height + S(4))
                                                               : new Rectangle(pad, pad, Width - 2 * pad, cf.Height + S(4));
                        RmDraw.Text(g, count.ToString(CultureInfo.InvariantCulture), tileSize == RmTileSize.Medium ? Font : cf, cr, fore,
                                    tileSize == RmTileSize.Medium ? ContentAlignment.BottomRight : ContentAlignment.TopRight, Rtl);
                    }
                }
            }
            FocusCue(g, Rectangle.Inflate(Rectangle.Round(r), -S(3), -S(3)), t, Sf(t.Radius));
        }
    }
}
