// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Containers: RmPanel, RmGroupPanel, RmTabStrip, RmNavigationPane (pages = RmPage), RmDockPanel + RmDockWindow.
#nullable disable
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Linq;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    /// <summary>Themed, double-buffered container base. BackColor (when not set) is the theme surface, so child
    /// controls inherit it (ambient property) and follow theme changes.</summary>
    [ToolboxItem(false)]
    public class RmContainer : Panel, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty, back = Color.Empty;
        protected Point mouse = new Point(-1, -1);

        public RmContainer()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.ResizeRedraw | ControlStyles.SupportsTransparentBackColor, true);
            RmThemeManager.ThemeChanged += OnTheme;
            Font = new Font("Segoe UI", 9f);
        }

        protected override void Dispose(bool disposing) { RmThemeManager.ThemeChanged -= OnTheme; base.Dispose(disposing); }

        void OnTheme(object s, EventArgs e) { if (!IsDisposed) { ThemeChanged(); OnBackColorChanged(EventArgs.Empty); Invalidate(true); } }

        protected virtual void ThemeChanged() { }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get { return style; } set { style = value; ThemeChanged(); OnBackColorChanged(EventArgs.Empty); Invalidate(true); } }

        [Category("Appearance")]
        public Color AccentColor { get { return accent; } set { accent = value; ThemeChanged(); Invalidate(true); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        /// <summary>The colour of the body (children inherit it).</summary>
        protected virtual Color ThemeBack(RmTheme t) { return t.Window; }

        public override Color BackColor { get { return back.IsEmpty ? ThemeBack(Theme) : back; } set { back = value; OnBackColorChanged(EventArgs.Empty); Invalidate(true); } }
        public bool ShouldSerializeBackColor() { return !back.IsEmpty; }
        public override void ResetBackColor() { BackColor = Color.Empty; }
        protected bool HasBack { get { return !back.IsEmpty; } }

        protected int S(float v) { return (int)Math.Round(v * Math.Max(1f, DeviceDpi / 96f)); }
        protected float Sf(float v) { return v * Math.Max(1f, DeviceDpi / 96f); }
        protected bool Rtl { get { return RightToLeft == RightToLeft.Yes; } }
        protected Rectangle M(Rectangle r) { return Rtl ? new Rectangle(ClientSize.Width - r.Right, r.Y, r.Width, r.Height) : r; }

        protected Color Surface()
        {
            for (var p = Parent; p != null; p = p.Parent) if (p.BackColor.A == 255) return p.BackColor;
            return Theme.Window;
        }

        protected override void OnMouseMove(MouseEventArgs e) { mouse = e.Location; Invalidate(); base.OnMouseMove(e); }
        protected override void OnMouseLeave(EventArgs e) { mouse = new Point(-1, -1); Invalidate(); base.OnMouseLeave(e); }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    /// <summary>Rounded / shadowed / gradient panel with an optional title bar.</summary>
    public class RmPanel : RmContainer
    {
        string title = "";
        int radius = -1;
        bool shadow;
        Color gradientTo = Color.Empty, borderColor = Color.Empty;

        public RmPanel() { Size = new Size(240, 160); }

        [Category("Appearance"), DefaultValue("")]
        public string Title { get { return title; } set { title = value ?? ""; UpdatePadding(); Invalidate(); } }

        [Category("Appearance"), DefaultValue(-1)]
        public int CornerRadius { get { return radius; } set { radius = value; Invalidate(); } }

        [Category("Appearance"), DefaultValue(false)]
        public bool Shadow { get { return shadow; } set { shadow = value; UpdatePadding(); Invalidate(); } }

        [Category("Appearance")]
        public Color GradientTo { get { return gradientTo; } set { gradientTo = value; Invalidate(); } }
        public bool ShouldSerializeGradientTo() { return !gradientTo.IsEmpty; }

        [Category("Appearance")]
        public Color BorderColor { get { return borderColor; } set { borderColor = value; Invalidate(); } }
        public bool ShouldSerializeBorderColor() { return !borderColor.IsEmpty; }

        protected override Color ThemeBack(RmTheme t) { return t.Surface; }

        int TitleH { get { return title.Length > 0 ? S(30) : 0; } }

        void UpdatePadding() { int s = shadow ? S(4) : 0; Padding = new Padding(s + S(1), TitleH + s + S(1), s + S(1), s + S(1)); }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            using (var b = new SolidBrush(Surface())) g.FillRectangle(b, ClientRectangle);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            float rad = radius >= 0 ? Sf(radius) : Sf(Math.Max(t.Radius, t.Radius == 0 ? 0 : 6));
            int s = shadow ? S(4) : 0;
            var r = new RectangleF(s + 0.5f, s * 0.5f + 0.5f, Width - 2 * s - 1, Height - 2 * s - 1);
            if (shadow) RmDraw.Shadow(g, r, rad, s, t.Dark);
            var body = BackColor;
            if (!gradientTo.IsEmpty && r.Width > 0 && r.Height > 0)
                using (var path = RmDraw.Round(r, rad)) using (var lg = new LinearGradientBrush(r, body, gradientTo, LinearGradientMode.Vertical)) g.FillPath(lg, path);
            else RmDraw.Box(g, r, body, Color.Empty, 0, rad);
            if (title.Length > 0)
            {
                var tr = new RectangleF(r.X, r.Y, r.Width, TitleH);
                using (var path = RmDraw.Round(new RectangleF(r.X, r.Y, r.Width, TitleH + rad * 2), rad))
                {
                    var clip = g.Clip;
                    g.SetClip(tr);
                    using (var b = new SolidBrush(t.HeaderBack)) g.FillPath(b, path);
                    g.Clip = clip;
                }
                using (var bf = new Font(Font, FontStyle.Bold))
                    RmDraw.Text(g, title, bf, new Rectangle((int)r.X + S(10), (int)r.Y, (int)r.Width - S(20), TitleH), t.HeaderText, ContentAlignment.MiddleLeft, Rtl);
                using (var p = new Pen(RmDraw.Alpha(t.Border, 120))) g.DrawLine(p, r.X, r.Y + TitleH, r.Right, r.Y + TitleH);
            }
            var bc = borderColor.IsEmpty ? (shadow ? Color.Empty : t.Border) : borderColor;
            RmDraw.Box(g, r, Color.Empty, bc, Sf(1), rad);
        }
    }

    /// <summary>Collapsible group with a header.</summary>
    public class RmGroupPanel : RmContainer
    {
        string title = "";
        bool collapsed;
        int expandedHeight;

        public event EventHandler CollapsedChanged;

        public RmGroupPanel() { Size = new Size(240, 160); expandedHeight = 160; UpdatePadding(); }

        [Category("Appearance"), DefaultValue("")]
        public string Title { get { return title; } set { title = value ?? ""; Invalidate(); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool Collapsed
        {
            get { return collapsed; }
            set
            {
                if (collapsed == value) return;
                if (value) expandedHeight = Height;
                collapsed = value;
                Height = collapsed ? HeaderH + 1 : Math.Max(expandedHeight, HeaderH + 1);
                foreach (Control c in Controls) c.Visible = !collapsed;
                Invalidate();
                var h = CollapsedChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        public void Toggle() { Collapsed = !Collapsed; }
        public void Expand() { Collapsed = false; }
        public void Collapse() { Collapsed = true; }

        int HeaderH { get { return S(30); } }

        void UpdatePadding() { Padding = new Padding(S(1), HeaderH, S(1), S(1)); }

        protected override void OnResize(EventArgs e) { base.OnResize(e); if (!collapsed) expandedHeight = Height; }

        protected override Color ThemeBack(RmTheme t) { return t.Surface; }

        protected override void OnMouseUp(MouseEventArgs e) { base.OnMouseUp(e); if (e.Y < HeaderH && e.Button == MouseButtons.Left) Toggle(); }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            using (var b = new SolidBrush(Surface())) g.FillRectangle(b, ClientRectangle);
            float rad = Sf(t.Radius);
            var r = new RectangleF(0.5f, 0.5f, Width - 1, Height - 1);
            RmDraw.Box(g, r, BackColor, t.Border, Sf(1), rad);
            bool hot = mouse.Y >= 0 && mouse.Y < HeaderH;
            var hr = new RectangleF(1, 1, Width - 2, HeaderH - 1);
            using (var b = new SolidBrush(hot ? RmDraw.Blend(t.HeaderBack, t.Hot, 0.6) : t.HeaderBack))
            using (var path = RmDraw.Round(new RectangleF(hr.X, hr.Y, hr.Width, collapsed ? hr.Height : hr.Height + rad * 2), rad))
            {
                var clip = g.Clip; g.SetClip(hr);
                g.SmoothingMode = SmoothingMode.AntiAlias; g.FillPath(b, path);
                g.Clip = clip;
            }
            var chev = M(new Rectangle(S(6), 0, S(20), HeaderH));
            RmDraw.Chevron(g, chev, t.HeaderText, Sf(1.5f), !collapsed, collapsed && !Rtl, collapsed && Rtl);
            using (var bf = new Font(Font, FontStyle.Bold))
                RmDraw.Text(g, title, bf, M(new Rectangle(S(28), 0, Width - S(36), HeaderH)), t.HeaderText, ContentAlignment.MiddleLeft, Rtl);
            if (!collapsed) using (var p = new Pen(RmDraw.Alpha(t.Border, 120))) g.DrawLine(p, 1, HeaderH, Width - 2, HeaderH);
        }
    }

    /// <summary>A page of RmTabStrip / RmNavigationPane (children of the page are positioned inside it).</summary>
    [ToolboxItem(false)]
    public class RmPage : RmContainer
    {
        string image = "";
        public RmPage() { }
        public RmPage(string text) { Text = text; }

        /// <summary>The host places the page (also when right-to-left): layout mirroring leaves its position alone.</summary>
        [Browsable(false)]
        public bool RadNoMirror { get { return true; } }

        [Category("Appearance"), DefaultValue("")]
        public string Image { get { return image; } set { image = value ?? ""; if (Parent != null) Parent.Invalidate(); } }

        protected override Color ThemeBack(RmTheme t)
        {
            var host = Parent as RmContainer;
            return host != null && Parent.BackColor.A == 255 ? Parent.BackColor : t.Window;
        }

        protected override void OnTextChanged(EventArgs e) { base.OnTextChanged(e); if (Parent != null) Parent.Invalidate(); }
    }

    public enum RmTabPosition { Top, Left, Bottom }

    /// <summary>Base of the page hosts: pages as RmPage children, SelectedIndex, GetPage(i).</summary>
    [ToolboxItem(false)]
    public class RmPagedContainer : RmContainer
    {
        protected readonly List<RmPage> pages = new List<RmPage>();
        int sel = -1;

        public event EventHandler SelectedIndexChanged;

        [Browsable(false)]
        public IList<RmPage> Pages2 { get { return pages; } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int PageCount { get { return pages.Count; } }

        protected void SetPageTexts(IList<RmItem> items)
        {
            for (int i = 0; i < items.Count; i++)
            {
                var p = i < pages.Count ? pages[i] : AddPageInternal(items[i].Text);
                p.Text = items[i].Text;
                p.Name = string.IsNullOrEmpty(p.Name) ? "page" + i.ToString(CultureInfo.InvariantCulture) : p.Name;
                p.Image = items[i].Image;
            }
            while (pages.Count > items.Count && pages.Count > 0 && pages[pages.Count - 1].Controls.Count == 0) RemovePageAt(pages.Count - 1);
            if (sel < 0 && pages.Count > 0) SelectedIndex = 0;
            if (sel >= pages.Count) SelectedIndex = pages.Count - 1;
            LayoutPages();
        }

        RmPage AddPageInternal(string text)
        {
            var p = new RmPage(text) { Visible = false };
            pages.Add(p);
            Controls.Add(p);
            return p;
        }

        /// <summary>Adds a page and returns its index.</summary>
        public int AddPage(string text) { AddPageInternal(text); LayoutPages(); if (sel < 0) SelectedIndex = 0; Invalidate(); return pages.Count - 1; }

        public void RemovePageAt(int index)
        {
            if (index < 0 || index >= pages.Count) return;
            var p = pages[index];
            pages.RemoveAt(index);
            Controls.Remove(p);
            p.Dispose();
            if (sel >= pages.Count) sel = pages.Count - 1;
            ShowSelected();
            Invalidate();
        }

        /// <summary>Page i (created when missing) - the generated code adds a page's controls with GetPage(i).Controls.Add.</summary>
        public RmPage GetPage(int index)
        {
            while (pages.Count <= index) AddPageInternal("Page" + (pages.Count + 1).ToString(CultureInfo.InvariantCulture));
            if (sel < 0) SelectedIndex = 0;
            LayoutPages();
            return pages[Math.Max(0, index)];
        }

        /// <summary>Adds a control to page i; its Location is relative to the container's top-left corner (as in
        /// the designer) and becomes relative to the page.</summary>
        public void AddToPage(int index, Control c)
        {
            var page = GetPage(index);
            var pb = PageBounds();
            var loc = c.Location;
            page.Controls.Add(c);
            c.Location = new Point(loc.X - pb.X, loc.Y - pb.Y);
        }

        public string PageText(int index) { return index >= 0 && index < pages.Count ? pages[index].Text : ""; }

        [Category("Behavior"), DefaultValue(-1)]
        public int SelectedIndex
        {
            get { return sel; }
            set
            {
                var v = pages.Count == 0 ? -1 : Math.Max(0, Math.Min(pages.Count - 1, value));
                if (v == sel) return;
                sel = v;
                ShowSelected();
                Invalidate();
                var h = SelectedIndexChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string SelectedText { get { return PageText(sel); } }

        public override string Text { get { return sel >= 0 ? PageText(sel) : base.Text; } set { base.Text = value; } }

        void ShowSelected()
        {
            for (int i = 0; i < pages.Count; i++) pages[i].Visible = i == sel;
            if (sel >= 0) pages[sel].BringToFront();
        }

        protected virtual Rectangle PageBounds() { return ClientRectangle; }

        protected void LayoutPages() { var r = PageBounds(); foreach (var p in pages) p.Bounds = r; OnLayoutPages(); }

        /// <summary>After the pages were placed (the tab strip places its header).</summary>
        protected virtual void OnLayoutPages() { }

        protected override void OnResize(EventArgs e) { base.OnResize(e); LayoutPages(); }
        protected override void OnRightToLeftChanged(EventArgs e) { base.OnRightToLeftChanged(e); LayoutPages(); }

        protected override void OnControlAdded(ControlEventArgs e)
        {
            base.OnControlAdded(e);
            var p = e.Control as RmPage;
            if (p != null && !pages.Contains(p)) { pages.Add(p); p.Visible = pages.Count - 1 == sel; LayoutPages(); if (sel < 0) SelectedIndex = 0; }
            else if (p == null && pages.Count > 0 && sel >= 0 && !DesignMode && !(e.Control is RmControl && e.Control.Name.Length == 0 && e.Control.GetType().IsNested))
            {   // a control added to the host itself (from code) goes onto the selected page, same position on screen
                var c = e.Control;
                var loc = c.Location;
                var pb = PageBounds();
                pages[sel].Controls.Add(c);
                c.Location = new Point(Math.Max(0, loc.X - pb.X), Math.Max(0, loc.Y - pb.Y));
            }
        }
    }

    /// <summary>Modern tabs (top / left / bottom, closable, overflow menu) with pages.</summary>
    [DefaultEvent("SelectedIndexChanged")]
    public class RmTabStrip : RmPagedContainer
    {
        string tabPages = "";
        RmTabPosition pos = RmTabPosition.Top;
        bool closable;
        readonly List<Rectangle> tabRects = new List<Rectangle>();
        Rectangle moreRect;
        double indicator = -1;

        public event EventHandler<RmItemEventArgs> TabClosing;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;
        readonly RmTabHeader header;

        public RmTabStrip()
        {
            header = new RmTabHeader(this);
            Controls.Add(header);
            Size = new Size(320, 220);
        }

        /// <summary>The strip with the tabs is a child control: its tabs are accessible items (UI Automation on .NET 8
        /// lists the child windows of a container, not its own items), and it paints / handles the mouse for the strip.</summary>
        sealed class RmTabHeader : RmControl
        {
            readonly RmTabStrip o;
            public RmTabHeader(RmTabStrip owner) { o = owner; TabStop = false; SetStyle(ControlStyles.Selectable, false); Name = ""; }
            public bool RadNoMirror { get { return true; } }
            protected override void OnRightToLeftChanged(EventArgs e) { base.OnRightToLeftChanged(e); o.LayoutPages(); }
            Point Off { get { return Location; } }
            protected override void OnPaintBackground(PaintEventArgs e) { }
            protected override void OnPaint(PaintEventArgs e) { e.Graphics.TranslateTransform(-Left, -Top); o.PaintStrip(e.Graphics); }
            protected override void OnMouseMove(MouseEventArgs e) { o.mouse = new Point(e.X + Left, e.Y + Top); Invalidate(); base.OnMouseMove(e); }
            protected override void OnMouseLeave(EventArgs e) { o.mouse = new Point(-1, -1); Invalidate(); base.OnMouseLeave(e); }
            protected override void OnMouseUp(MouseEventArgs e) { base.OnMouseUp(e); o.StripClick(e.Button, new Point(e.X + Left, e.Y + Top)); }
            protected override AccessibleRole RmRole { get { return AccessibleRole.PageTabList; } }
            protected internal override IList<RmAccessibleItem> AccessibleItems()
            {
                o.Measure();
                var l = new List<RmAccessibleItem>();
                for (int i = 0; i < o.pages.Count; i++)
                {
                    int k = i;
                    var r = i < o.tabRects.Count ? o.tabRects[i] : Rectangle.Empty;
                    r.Offset(-Left, -Top);
                    l.Add(new RmAccessibleItem(o.pages[i].Text, r, () => o.SelectedIndex = k, AccessibleRole.PageTab) { Selected = i == o.SelectedIndex });
                }
                return l;
            }
        }

        Rectangle StripRect { get { return pos == RmTabPosition.Left ? M(new Rectangle(0, 0, StripW, Height)) : pos == RmTabPosition.Top ? new Rectangle(0, 0, Width, StripH) : new Rectangle(0, Height - StripH, Width, StripH); } }

        protected override void OnLayoutPages()
        {
            if (header == null) return;
            header.Bounds = StripRect;
            header.BringToFront();
        }

        protected override void OnInvalidated(InvalidateEventArgs e) { base.OnInvalidated(e); if (header != null) header.Invalidate(); }

        /// <summary>Page titles: "Page1;Page2" (or a JSON array of {Text, Image}).</summary>
        [Category("Behavior"), DefaultValue("")]
        public string TabPages { get { return tabPages; } set { tabPages = value ?? ""; SetPageTexts(RmItem.Parse(tabPages)); } }

        [Category("Appearance"), DefaultValue(RmTabPosition.Top)]
        public RmTabPosition TabPosition { get { return pos; } set { pos = value; LayoutPages(); Invalidate(); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool Closable { get { return closable; } set { closable = value; Invalidate(); } }

        int StripH { get { return S(34); } }
        int StripW { get { return S(140); } }

        protected override Rectangle PageBounds()
        {
            switch (pos)
            {
                case RmTabPosition.Left: return M(new Rectangle(StripW, 0, Math.Max(0, Width - StripW), Height));
                case RmTabPosition.Bottom: return new Rectangle(0, 0, Width, Math.Max(0, Height - StripH));
                default: return new Rectangle(0, StripH, Width, Math.Max(0, Height - StripH));
            }
        }

        void Measure()
        {
            tabRects.Clear();
            moreRect = Rectangle.Empty;
            if (pos == RmTabPosition.Left)
            {
                for (int i = 0; i < pages.Count; i++) tabRects.Add(M(new Rectangle(0, S(4) + i * S(34), StripW, S(34))));
                return;
            }
            int y = pos == RmTabPosition.Top ? 0 : Height - StripH, x = S(4), avail = Width - S(36);
            for (int i = 0; i < pages.Count; i++)
            {
                int w = RmDraw.Measure(pages[i].Text, Font).Width + S(28) + (closable ? S(18) : 0) + (pages[i].Image.Length > 0 ? S(20) : 0);
                if (x + w > avail && i > 0 && moreRect.IsEmpty) moreRect = M(new Rectangle(Width - S(32), y + S(4), S(28), StripH - S(8)));
                tabRects.Add(x + w > avail && i > 0 ? Rectangle.Empty : M(new Rectangle(x, y, w, StripH)));
                x += w;
            }
        }

        Rectangle CloseRect(Rectangle tab)
        {
            int s = S(16);
            return Rtl ? new Rectangle(tab.X + S(8), tab.Y + (tab.Height - s) / 2, s, s) : new Rectangle(tab.Right - s - S(8), tab.Y + (tab.Height - s) / 2, s, s);
        }

        bool autoClose = true;

        [Category("Behavior"), DefaultValue(true), Description("The close button removes the tab after TabClosing (False: only the event).")]
        public bool AutoClose { get { return autoClose; } set { autoClose = value; } }

        /// <summary>Closes tab i (raises TabClosing; Cancel keeps it).</summary>
        public bool CloseTab(int index)
        {
            if (index < 0 || index >= pages.Count) return false;
            var a = new RmItemEventArgs(pages[index].Name, index, pages[index].Text);
            RmItemEventArgs.Raise(this, TabClosing, a);
            if (a.Cancel || !autoClose) return false;
            RemovePageAt(index);
            return true;
        }

        public int AddTab(string text) { return AddPage(text); }
        public void RemoveTab(int index) { RemovePageAt(index); }
        public void SelectTab(int index) { SelectedIndex = index; }
        /// <summary>Caption of tab i; with text: sets it.</summary>
        public string TabCaption(int index, string text = null)
        {
            if (index < 0 || index >= pages.Count) return "";
            if (text != null) pages[index].Text = text;
            return pages[index].Text;
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int TabCount { get { return pages.Count; } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string SelectedTab { get { return SelectedText; } set { for (int i = 0; i < pages.Count; i++) if (pages[i].Text == value) SelectedIndex = i; } }

        void StripClick(MouseButtons button, Point p)
        {
            Measure();
            if (!moreRect.IsEmpty && moreRect.Contains(p))
            {
                var menu = new ContextMenuStrip { Renderer = new RmMenuRenderer(Theme), RightToLeft = RightToLeft };
                for (int i = 0; i < pages.Count; i++) { int k = i; menu.Items.Add(new ToolStripMenuItem(pages[i].Text, null, (s, a) => SelectedIndex = k) { Checked = i == SelectedIndex }); }
                menu.Show(this, new Point(moreRect.X, moreRect.Bottom));
                return;
            }
            for (int i = 0; i < tabRects.Count; i++)
            {
                if (!tabRects[i].Contains(p)) continue;
                if (button == MouseButtons.Middle && closable) { CloseTab(i); return; }
                if (closable && CloseRect(tabRects[i]).Contains(p)) { CloseTab(i); return; }
                if (button == MouseButtons.Left) SelectedIndex = i;
                return;
            }
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            using (var b = new SolidBrush(BackColor)) e.Graphics.FillRectangle(b, ClientRectangle);
        }

        void PaintStrip(Graphics g)
        {
            var t = Theme;
            Measure();
            var strip = StripRect;
            using (var b = new SolidBrush(t.HeaderBack.IsEmpty ? t.Window : (t.Name == "Office" ? RmDraw.Blend(t.Window, t.Accent, 0.06) : t.HeaderBack))) g.FillRectangle(b, strip);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle selRect = Rectangle.Empty;
            for (int i = 0; i < tabRects.Count; i++)
            {
                var r = tabRects[i];
                if (r.IsEmpty) continue;
                bool sel = i == SelectedIndex, hot = r.Contains(mouse);
                if (sel) selRect = r;
                if (hot && !sel) RmDraw.Box(g, Rectangle.Inflate(r, -S(2), -S(4)), t.Hot, Color.Empty, 0, Sf(t.Radius));
                if (sel && t.Name == "Metro") RmDraw.Box(g, r, RmDraw.Alpha(t.Accent, 30), Color.Empty, 0, 0);
                var content = Rectangle.Inflate(r, -S(12), 0);
                if (closable) { if (Rtl) { content.X += S(18); } content.Width -= S(18); }
                if (pages[i].Image.Length > 0)
                {
                    var ir = Rtl ? new Rectangle(content.Right - S(16), r.Y + (r.Height - S(16)) / 2, S(16), S(16)) : new Rectangle(content.X, r.Y + (r.Height - S(16)) / 2, S(16), S(16));
                    RmImages.Draw(g, pages[i].Image, null, ir, sel ? t.Accent : t.SubtleText);
                    if (!Rtl) content.X += S(20); content.Width -= S(20);
                }
                using (var f = sel ? new Font(Font, FontStyle.Bold) : null)
                    RmDraw.Text(g, pages[i].Text, f ?? Font, content, sel ? t.WindowText : t.SubtleText, pos == RmTabPosition.Left ? ContentAlignment.MiddleLeft : ContentAlignment.MiddleCenter, Rtl);
                if (closable)
                {
                    var cr = CloseRect(r);
                    if (cr.Contains(mouse)) RmDraw.Box(g, cr, t.Pressed, Color.Empty, 0, cr.Width / 2f);
                    if (sel || hot) RmDraw.Cross(g, cr, t.SubtleText, Sf(1.3f));
                }
            }
            if (!moreRect.IsEmpty) RmDraw.Chevron(g, moreRect, t.WindowText, Sf(1.5f));
            if (!selRect.IsEmpty)
            {   // animated selection indicator
                double target = pos == RmTabPosition.Left ? selRect.Y : selRect.X;
                if (indicator < 0) indicator = target;
                if (Math.Abs(indicator - target) > 0.5) { indicator += (target - indicator) * 0.35; RmAnimator.Run(() => { Invalidate(); return false; }); } else indicator = target;
                using (var b = new SolidBrush(t.Accent))
                {
                    if (pos == RmTabPosition.Left) g.FillRectangle(b, Rtl ? selRect.Right - S(3) : selRect.X, (float)indicator + S(6), S(3), selRect.Height - S(12));
                    else g.FillRectangle(b, (float)indicator + S(8), pos == RmTabPosition.Top ? selRect.Bottom - S(3) : selRect.Y, selRect.Width - S(16), S(3));
                }
            }
            using (var p = new Pen(RmDraw.Alpha(t.Border, 140)))
            {
                if (pos == RmTabPosition.Top) g.DrawLine(p, 0, StripH - 1, Width, StripH - 1);
                else if (pos == RmTabPosition.Bottom) g.DrawLine(p, 0, Height - StripH, Width, Height - StripH);
                else { int x = Rtl ? Width - StripW : StripW - 1; g.DrawLine(p, x, 0, x, Height); }
            }
        }
    }

    /// <summary>Navigation pane (Outlook style): a header with the page title, page content, and the page buttons at the bottom.</summary>
    [DefaultEvent("SelectedIndexChanged")]
    public class RmNavigationPane : RmPagedContainer
    {
        string pagesSpec = "";

        public RmNavigationPane() { Size = new Size(220, 320); }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string SelectedPage { get { return SelectedText; } set { for (int i = 0; i < pages.Count; i++) if (pages[i].Text == value) SelectedIndex = i; } }

        /// <summary>"Mail;Calendar;Contacts" or a JSON array of {Text, Image}.</summary>
        [Category("Behavior"), DefaultValue("")]
        public string Pages { get { return pagesSpec; } set { pagesSpec = value ?? ""; SetPageTexts(RmItem.Parse(pagesSpec)); } }

        int HeaderH { get { return S(34); } }
        int ButtonH { get { return S(36); } }

        protected override Rectangle PageBounds() { return new Rectangle(1, HeaderH, Math.Max(0, Width - 2), Math.Max(0, Height - HeaderH - ButtonH * pages.Count - 1)); }

        Rectangle ButtonRect(int i) { return new Rectangle(1, Height - 1 - ButtonH * (pages.Count - i), Width - 2, ButtonH); }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            for (int i = 0; i < pages.Count; i++) if (ButtonRect(i).Contains(e.Location)) { SelectedIndex = i; return; }
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            using (var b = new SolidBrush(BackColor)) g.FillRectangle(b, ClientRectangle);
            using (var b = new SolidBrush(t.HeaderBack)) g.FillRectangle(b, 0, 0, Width, HeaderH);
            using (var bf = new Font(Font.FontFamily, Font.Size * 1.2f, FontStyle.Bold))
                RmDraw.Text(g, SelectedText, bf, M(new Rectangle(S(10), 0, Width - S(20), HeaderH)), t.HeaderText, ContentAlignment.MiddleLeft, Rtl);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            for (int i = 0; i < pages.Count; i++)
            {
                var r = ButtonRect(i);
                bool sel = i == SelectedIndex, hot = r.Contains(mouse);
                var back = sel ? RmDraw.Alpha(t.Accent, t.Dark ? 70 : 40) : hot ? t.Hot : (t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.03) : RmDraw.Blend(t.Window, Color.Black, 0.02));
                using (var b = new SolidBrush(back)) g.FillRectangle(b, r);
                using (var p = new Pen(RmDraw.Alpha(t.Border, 120))) g.DrawLine(p, r.X, r.Y, r.Right, r.Y);
                if (sel) using (var b = new SolidBrush(t.Accent)) g.FillRectangle(b, Rtl ? r.Right - S(3) : r.X, r.Y, S(3), r.Height);
                int x = S(12);
                if (pages[i].Image.Length > 0) { RmImages.Draw(g, pages[i].Image, null, M(new Rectangle(x, r.Y + (r.Height - S(18)) / 2, S(18), S(18))), sel ? t.Accent : t.WindowText); x += S(26); }
                using (var f = sel ? new Font(Font, FontStyle.Bold) : null)
                    RmDraw.Text(g, pages[i].Text, f ?? Font, M(new Rectangle(x, r.Y, Width - x - S(8), r.Height)), t.WindowText, ContentAlignment.MiddleLeft, Rtl);
            }
            RmDraw.Box(g, new RectangleF(0.5f, 0.5f, Width - 1, Height - 1), Color.Empty, t.Border, 1, 0);
        }
    }

    // ====================================================================== docking
    public enum RmDockSide { Left, Right, Top, Bottom, Fill, Float }

    /// <summary>A dockable tool window (its children are positioned inside its body).</summary>
    public class RmDockWindow : RmContainer
    {
        string title = "";
        RmDockSide side = RmDockSide.Left;
        bool autoHide;
        internal Form floatForm;
        internal bool closed;

        public RmDockWindow() { Size = new Size(200, 200); }

        /// <summary>The dock panel places the window: layout mirroring leaves its position alone.</summary>
        [Browsable(false)]
        public bool RadNoMirror { get { return true; } }

        [Category("Appearance"), DefaultValue("")]
        public string Title { get { return title; } set { title = value ?? ""; Host(); } }

        [Category("Behavior"), DefaultValue(RmDockSide.Left)]
        public RmDockSide DockSide { get { return side; } set { side = value; Host(); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool AutoHide { get { return autoHide; } set { autoHide = value; Host(); } }

        int dockSize;

        /// <summary>Width (left / right) or height (top / bottom) of its side in 96-DPI pixels; 0 = the panel's Layout.</summary>
        [Category("Layout"), DefaultValue(0)]
        public int DockSize { get { return dockSize; } set { dockSize = Math.Max(0, value); Host(); } }

        [Browsable(false)]
        public bool IsClosed { get { return closed; } }

        void Host() { var h = DockHost; if (h != null) h.PerformDockLayout(); }

        internal RmDockPanel DockHost { get { return Parent as RmDockPanel ?? (floatForm != null ? floatForm.Tag as RmDockPanel : null); } }

        public string DisplayTitle { get { return title.Length > 0 ? title : Name; } }

        public void CloseWindow() { var h = DockHost; if (h != null) h.CloseWindow(this); }
        public void ShowWindow() { var h = DockHost; if (h != null) h.ShowWindow(this); }

        protected override Color ThemeBack(RmTheme t) { return t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.04) : (t.Name == "Light" ? Color.White : t.Window); }
    }

    /// <summary>Docking host: RmDockWindow children dock (Left / Right / Top / Bottom, tabbed when they share a side),
    /// fill the centre (document tabs), float (double-click the title) or auto-hide (pin button) inside the form.</summary>
    [DefaultEvent("ActiveWindowChanged")]
    public class RmDockPanel : RmContainer
    {
        readonly List<RmDockWindow> windows = new List<RmDockWindow>();
        readonly Dictionary<RmDockSide, int> sizes = new Dictionary<RmDockSide, int> { { RmDockSide.Left, 220 }, { RmDockSide.Right, 220 }, { RmDockSide.Top, 140 }, { RmDockSide.Bottom, 160 } };
        readonly Dictionary<RmDockSide, int> active = new Dictionary<RmDockSide, int>();
        readonly Dictionary<RmDockSide, Rectangle> regions = new Dictionary<RmDockSide, Rectangle>();
        readonly List<Tuple<Rectangle, RmDockWindow>> tabHits = new List<Tuple<Rectangle, RmDockWindow>>();
        readonly List<Tuple<Rectangle, RmDockWindow, string>> buttons = new List<Tuple<Rectangle, RmDockWindow, string>>();
        string layout = "";
        RmDockWindow activeWindow, popup;
        RmDockSide? dragSplit;
        bool inLayout;

        public event EventHandler<RmItemEventArgs> WindowClosed;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;
        public event EventHandler<RmItemEventArgs> ActiveWindowChanged;

        public RmDockPanel() { Size = new Size(520, 360); }

        [Category("Layout"), DefaultValue(""), Description("JSON: {\"Left\": 220, \"Right\": 220, \"Top\": 140, \"Bottom\": 160, \"Windows\": {\"name\": {\"DockSide\": \"Right\", \"AutoHide\": true}}}.")]
        [RmName("Layout")]
        public string LayoutJson
        {
            get { return layout; }
            set { layout = value ?? ""; ApplyLayout(layout); }
        }

        [Browsable(false)]
        public IList<RmDockWindow> Windows { get { return windows; } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string ActiveWindow { get { return activeWindow != null ? activeWindow.Name : ""; } set { var w = Find(value); if (w != null) Activate(w); } }

        int HeaderH { get { return S(26); } }
        int TabH { get { return S(24); } }
        int StripW { get { return S(24); } }
        int Splitter { get { return S(5); } }

        RmDockWindow Find(string name) { return windows.FirstOrDefault(w => string.Equals(w.Name, name, StringComparison.OrdinalIgnoreCase) || w.Title == name); }

        void ApplyLayout(string json)
        {
            if (string.IsNullOrEmpty(json)) { PerformDockLayout(); return; }
            Dictionary<string, object> d;
            try { d = RmJson.Parse(json) as Dictionary<string, object>; } catch (Exception) { d = null; }
            if (d == null) return;
            foreach (var side in new[] { RmDockSide.Left, RmDockSide.Right, RmDockSide.Top, RmDockSide.Bottom })
            {
                object v;
                if (d.TryGetValue(side.ToString(), out v) && v is double) sizes[side] = (int)(double)v;
            }
            object wins;
            if (d.TryGetValue("Windows", out wins) && wins is Dictionary<string, object>)
                foreach (var kv in (Dictionary<string, object>)wins)
                {
                    var w = Find(kv.Key);
                    var props = kv.Value as Dictionary<string, object>;
                    if (w == null || props == null) continue;
                    object v;
                    if (props.TryGetValue("DockSide", out v)) { try { w.DockSide = (RmDockSide)Enum.Parse(typeof(RmDockSide), RmItem.Str(v), true); } catch (ArgumentException) { } }
                    if (props.TryGetValue("AutoHide", out v)) w.AutoHide = RmItem.Bool(v);
                    if (props.TryGetValue("Closed", out v) && RmItem.Bool(v)) w.closed = true;
                }
            PerformDockLayout();
        }

        /// <summary>The current layout as JSON (sizes, sides, auto-hide, closed windows) - give it to Layout to restore.</summary>
        public string SaveLayout()
        {
            var d = new Dictionary<string, object>();
            foreach (var kv in sizes) d[kv.Key.ToString()] = (double)kv.Value;
            var w = new Dictionary<string, object>();
            foreach (var x in windows)
                w[x.Name] = new Dictionary<string, object> { { "DockSide", x.DockSide.ToString() }, { "AutoHide", x.AutoHide }, { "Closed", x.closed } };
            d["Windows"] = w;
            return RmJson.Write(d);
        }

        protected override void OnControlAdded(ControlEventArgs e)
        {
            base.OnControlAdded(e);
            var w = e.Control as RmDockWindow;
            if (w != null && !windows.Contains(w)) { windows.Add(w); w.GotFocus += (s, a) => Activate(w); w.MouseDown += (s, a) => Activate(w); }
            if (!inLayout) PerformDockLayout();
        }

        protected override void OnResize(EventArgs e) { base.OnResize(e); PerformDockLayout(); }

        IEnumerable<RmDockWindow> On(RmDockSide side, bool autoHidden) { return windows.Where(w => !w.closed && w.DockSide == side && w.AutoHide == autoHidden && w.floatForm == null); }

        /// <summary>Re-arranges the regions (called when windows / sizes change).</summary>
        public void PerformDockLayout()
        {
            if (inLayout) return;
            inLayout = true;
            try
            {
                regions.Clear();
                var area = ClientRectangle;
                // auto-hide strips
                foreach (var side in new[] { RmDockSide.Left, RmDockSide.Right, RmDockSide.Top, RmDockSide.Bottom })
                {
                    if (!On(side, true).Any()) continue;
                    var s = Mirror(side);
                    if (s == RmDockSide.Left) { area.X += StripW; area.Width -= StripW; }
                    else if (s == RmDockSide.Right) area.Width -= StripW;
                    else if (s == RmDockSide.Top) { area.Y += StripW; area.Height -= StripW; }
                    else area.Height -= StripW;
                }
                foreach (var side in new[] { RmDockSide.Top, RmDockSide.Bottom, RmDockSide.Left, RmDockSide.Right })
                {
                    if (!On(side, false).Any()) continue;
                    int own = On(side, false).Select(x => x.DockSize).DefaultIfEmpty(0).Max();
                    int sz = S(own > 0 ? own : sizes[side]);
                    var s = Mirror(side);
                    Rectangle r;
                    if (s == RmDockSide.Left) { sz = Math.Min(sz, area.Width - S(60)); r = new Rectangle(area.X, area.Y, sz, area.Height); area.X += sz + Splitter; area.Width -= sz + Splitter; }
                    else if (s == RmDockSide.Right) { sz = Math.Min(sz, area.Width - S(60)); r = new Rectangle(area.Right - sz, area.Y, sz, area.Height); area.Width -= sz + Splitter; }
                    else if (s == RmDockSide.Top) { sz = Math.Min(sz, area.Height - S(60)); r = new Rectangle(area.X, area.Y, area.Width, sz); area.Y += sz + Splitter; area.Height -= sz + Splitter; }
                    else { sz = Math.Min(sz, area.Height - S(60)); r = new Rectangle(area.X, area.Bottom - sz, area.Width, sz); area.Height -= sz + Splitter; }
                    regions[side] = r;
                }
                regions[RmDockSide.Fill] = area;
                foreach (var w in windows)
                {
                    if (w.closed) { w.Visible = false; continue; }
                    if (w.floatForm != null) continue;
                    if (w.AutoHide && w.DockSide != RmDockSide.Fill) { w.Visible = w == popup; if (w == popup) PlacePopup(w); continue; }
                    var side = w.DockSide == RmDockSide.Float ? RmDockSide.Fill : w.DockSide;
                    Rectangle reg;
                    if (!regions.TryGetValue(side, out reg)) { w.Visible = false; continue; }
                    var list = On(w.DockSide, false).ToList();
                    if (side == RmDockSide.Fill) list = windows.Where(x => !x.closed && x.floatForm == null && (x.DockSide == RmDockSide.Fill || x.DockSide == RmDockSide.Float)).ToList();
                    int act;
                    if (!active.TryGetValue(side, out act) || act >= list.Count) act = 0;
                    int tabs = list.Count > 1 ? TabH : 0;
                    bool header = side != RmDockSide.Fill;
                    var body = side == RmDockSide.Fill ? new Rectangle(reg.X, reg.Y + tabs, reg.Width, reg.Height - tabs)
                                                       : new Rectangle(reg.X, reg.Y + HeaderH, reg.Width, reg.Height - HeaderH - tabs);
                    if (!header && tabs == 0) body = reg;
                    w.Bounds = body;
                    w.Visible = list.IndexOf(w) == act;
                }
                Invalidate();
            }
            finally { inLayout = false; }
        }

        RmDockSide Mirror(RmDockSide s)
        {
            if (!Rtl) return s;
            return s == RmDockSide.Left ? RmDockSide.Right : s == RmDockSide.Right ? RmDockSide.Left : s;
        }

        void PlacePopup(RmDockWindow w)
        {
            int sz = S(sizes.ContainsKey(w.DockSide) ? sizes[w.DockSide] : 220);
            var s = Mirror(w.DockSide);
            Rectangle r;
            if (s == RmDockSide.Left) r = new Rectangle(StripW, HeaderH, sz, Height - HeaderH);
            else if (s == RmDockSide.Right) r = new Rectangle(Width - StripW - sz, HeaderH, sz, Height - HeaderH);
            else if (s == RmDockSide.Top) r = new Rectangle(0, StripW + HeaderH, Width, sz);
            else r = new Rectangle(0, Height - StripW - sz, Width, sz);
            w.Bounds = r;
            w.BringToFront();
        }

        public void Activate(RmDockWindow w)
        {
            if (w == null) return;
            if (w.closed) { ShowWindow(w); return; }
            var side = w.DockSide == RmDockSide.Float ? RmDockSide.Fill : w.DockSide;
            var list = side == RmDockSide.Fill ? windows.Where(x => !x.closed && x.floatForm == null && (x.DockSide == RmDockSide.Fill || x.DockSide == RmDockSide.Float)).ToList() : On(side, false).ToList();
            var i = list.IndexOf(w);
            if (i >= 0) active[side] = i;
            if (w.AutoHide) { popup = w; }
            bool changed = activeWindow != w;
            activeWindow = w;
            PerformDockLayout();
            if (changed) RmItemEventArgs.Raise(this, ActiveWindowChanged, new RmItemEventArgs(w.Name, windows.IndexOf(w), w.DisplayTitle));
        }

        public void CloseWindow(RmDockWindow w)
        {
            if (w == null || w.closed) return;
            if (w.floatForm != null) DockWindow(w);
            w.closed = true;
            if (popup == w) popup = null;
            PerformDockLayout();
            RmItemEventArgs.Raise(this, WindowClosed, new RmItemEventArgs(w.Name, windows.IndexOf(w), w.DisplayTitle));
        }

        public void ShowWindow(RmDockWindow w) { if (w == null) return; w.closed = false; Activate(w); }

        public void ShowWindow(string name) { ShowWindow(Find(name)); }
        public void CloseWindow(string name) { CloseWindow(Find(name)); }
        public void DockWindow(string name) { DockWindow(Find(name)); }
        public void LoadLayout(string json) { LayoutJson = json; }
        public new void Refresh() { PerformDockLayout(); base.Refresh(); }

        /// <summary>Methods by window name (from code: RmDockPanel1.Call("CloseWindowByName", "dwOutput")).</summary>
        public void CloseWindowByName(string name) { CloseWindow(Find(name)); }
        public void ShowWindowByName(string name) { ShowWindow(Find(name)); }
        public void FloatWindowByName(string name) { FloatWindow(Find(name)); }
        public void DockWindowByName(string name) { DockWindow(Find(name)); }
        public void SetAutoHide(string name, bool on) { var w = Find(name); if (w != null) { w.AutoHide = on; if (popup == w) popup = null; PerformDockLayout(); } }

        /// <summary>Moves a window into a floating tool window (double-click its title); closing that re-docks it.</summary>
        public void FloatWindow(RmDockWindow w)
        {
            if (w == null || w.floatForm != null) return;
            var f = new Form
            {
                Text = w.DisplayTitle, FormBorderStyle = FormBorderStyle.SizableToolWindow, ShowInTaskbar = false, Tag = this,
                StartPosition = FormStartPosition.Manual, BackColor = w.BackColor, RightToLeft = RightToLeft, RightToLeftLayout = Rtl
            };
            var screen = PointToScreen(new Point(w.Left + S(30), w.Top + S(30)));
            f.Bounds = new Rectangle(screen, new Size(Math.Max(S(200), w.Width), Math.Max(S(150), w.Height + HeaderH)));
            w.floatForm = f;
            Controls.Remove(w);
            w.Dock = DockStyle.Fill;
            w.Visible = true;
            f.Controls.Add(w);
            f.FormClosing += (s, a) => { if (a.CloseReason == CloseReason.UserClosing) { a.Cancel = true; DockWindow(w); } };
            RmThemeManager.DarkTitleBar(f, Theme.Dark);
            f.Show(FindForm());
            PerformDockLayout();
        }

        public void DockWindow(RmDockWindow w)
        {
            if (w == null || w.floatForm == null) return;
            var f = w.floatForm;
            w.floatForm = null;
            f.Controls.Remove(w);
            w.Dock = DockStyle.None;
            if (w.DockSide == RmDockSide.Float) w.DockSide = RmDockSide.Fill;
            inLayout = true; Controls.Add(w); inLayout = false;
            f.Hide();
            BeginInvoke((Action)(() => f.Dispose()));
            PerformDockLayout();
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e);
            foreach (var kv in regions)
            {
                if (kv.Key == RmDockSide.Fill) continue;
                var r = kv.Value;
                var s = Mirror(kv.Key);
                Rectangle sp = s == RmDockSide.Left ? new Rectangle(r.Right, r.Y, Splitter, r.Height) : s == RmDockSide.Right ? new Rectangle(r.X - Splitter, r.Y, Splitter, r.Height)
                             : s == RmDockSide.Top ? new Rectangle(r.X, r.Bottom, r.Width, Splitter) : new Rectangle(r.X, r.Y - Splitter, r.Width, Splitter);
                if (sp.Contains(e.Location)) { dragSplit = kv.Key; Capture = true; return; }
            }
            if (popup != null && !popup.Bounds.Contains(e.Location)) { popup = null; PerformDockLayout(); }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            if (dragSplit.HasValue)
            {
                var side = dragSplit.Value;
                var r = regions.ContainsKey(side) ? regions[side] : Rectangle.Empty;
                float sc = DeviceDpi / 96f;
                var s = Mirror(side);
                int v = s == RmDockSide.Left ? e.X - r.X : s == RmDockSide.Right ? r.Right - e.X : s == RmDockSide.Top ? e.Y - r.Y : r.Bottom - e.Y;
                sizes[side] = Math.Max(60, (int)(v / sc));
                PerformDockLayout();
                return;
            }
            bool split = false;
            foreach (var kv in regions)
            {
                if (kv.Key == RmDockSide.Fill) continue;
                var r = kv.Value; var s = Mirror(kv.Key);
                Rectangle sp = s == RmDockSide.Left ? new Rectangle(r.Right, r.Y, Splitter, r.Height) : s == RmDockSide.Right ? new Rectangle(r.X - Splitter, r.Y, Splitter, r.Height)
                             : s == RmDockSide.Top ? new Rectangle(r.X, r.Bottom, r.Width, Splitter) : new Rectangle(r.X, r.Y - Splitter, r.Width, Splitter);
                if (sp.Contains(e.Location)) { Cursor = s == RmDockSide.Left || s == RmDockSide.Right ? Cursors.VSplit : Cursors.HSplit; split = true; }
            }
            if (!split) Cursor = Cursors.Default;
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (dragSplit.HasValue) { dragSplit = null; Capture = false; return; }
            foreach (var b in buttons)
                if (b.Item1.Contains(e.Location))
                {
                    if (b.Item3 == "close") CloseWindow(b.Item2);
                    else if (b.Item3 == "pin") { b.Item2.AutoHide = !b.Item2.AutoHide; popup = null; PerformDockLayout(); }
                    return;
                }
            foreach (var tb in tabHits)
                if (tb.Item1.Contains(e.Location)) { if (tb.Item2.AutoHide) { popup = popup == tb.Item2 ? null : tb.Item2; activeWindow = tb.Item2; PerformDockLayout(); } else Activate(tb.Item2); return; }
            foreach (var kv in regions)
                if (kv.Key != RmDockSide.Fill && new Rectangle(kv.Value.X, kv.Value.Y, kv.Value.Width, HeaderH).Contains(e.Location))
                {
                    var w = windows.FirstOrDefault(x => x.Visible && x.DockSide == kv.Key && !x.AutoHide && x.floatForm == null);
                    if (w != null) Activate(w);
                }
        }

        protected override void OnMouseDoubleClick(MouseEventArgs e)
        {
            base.OnMouseDoubleClick(e);
            foreach (var kv in regions)
                if (kv.Key != RmDockSide.Fill && new Rectangle(kv.Value.X, kv.Value.Y, kv.Value.Width, HeaderH).Contains(e.Location))
                {
                    var w = windows.FirstOrDefault(x => x.Visible && x.DockSide == kv.Key && !x.AutoHide && x.floatForm == null);
                    if (w != null) FloatWindow(w);
                    return;
                }
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            tabHits.Clear();
            buttons.Clear();
            using (var b = new SolidBrush(t.Dark ? RmDraw.Blend(t.Window, Color.Black, 0.2) : RmDraw.Blend(t.Window, Color.Black, 0.06))) g.FillRectangle(b, ClientRectangle);
            foreach (var kv in regions)
            {
                var side = kv.Key;
                var r = kv.Value;
                var list = side == RmDockSide.Fill ? windows.Where(x => !x.closed && x.floatForm == null && (x.DockSide == RmDockSide.Fill || x.DockSide == RmDockSide.Float)).ToList() : On(side, false).ToList();
                if (list.Count == 0) continue;
                var vis = list.FirstOrDefault(x => x.Visible) ?? list[0];
                using (var b = new SolidBrush(vis.BackColor)) g.FillRectangle(b, r);
                if (side != RmDockSide.Fill)
                {
                    bool act = activeWindow != null && list.Contains(activeWindow);
                    var hr = new Rectangle(r.X, r.Y, r.Width, HeaderH);
                    using (var b = new SolidBrush(act ? t.Accent : t.HeaderBack)) g.FillRectangle(b, hr);
                    var fore = act ? t.AccentText : t.HeaderText;
                    var close = Rtl ? new Rectangle(hr.X + S(4), hr.Y + S(4), HeaderH - S(8), HeaderH - S(8)) : new Rectangle(hr.Right - HeaderH + S(4), hr.Y + S(4), HeaderH - S(8), HeaderH - S(8));
                    var pin = Rtl ? new Rectangle(close.Right + S(2), close.Y, close.Width, close.Height) : new Rectangle(close.X - close.Width - S(2), close.Y, close.Width, close.Height);
                    foreach (var br in new[] { close, pin }) if (br.Contains(mouse)) RmDraw.Box(g, br, RmDraw.Alpha(fore, 40), Color.Empty, 0, Sf(t.Radius));
                    RmDraw.Cross(g, close, fore, Sf(1.3f));
                    RmImages.Draw(g, "icon:pin", null, Rectangle.Inflate(pin, -S(2), -S(2)), fore);
                    buttons.Add(Tuple.Create(close, vis, "close"));
                    buttons.Add(Tuple.Create(pin, vis, "pin"));
                    RmDraw.Text(g, vis.DisplayTitle, Font, Rtl ? new Rectangle(pin.Right + S(4), hr.Y, hr.Width - (pin.Right - hr.X) - S(12), hr.Height)
                                                              : new Rectangle(hr.X + S(8), hr.Y, pin.X - hr.X - S(12), hr.Height), fore, ContentAlignment.MiddleLeft, Rtl);
                }
                if (list.Count > 1)
                {   // tabs: at the bottom of a side region, at the top of the centre
                    int y = side == RmDockSide.Fill ? r.Y : r.Bottom - TabH;
                    int x = r.X;
                    foreach (var w in list)
                    {
                        int tw = Math.Min(S(160), RmDraw.Measure(w.DisplayTitle, Font).Width + S(20));
                        var tr = M2(new Rectangle(x, y, tw, TabH), r);
                        bool on = w.Visible;
                        using (var b = new SolidBrush(on ? w.BackColor : (tr.Contains(mouse) ? t.Hot : t.HeaderBack))) g.FillRectangle(b, tr);
                        if (on) using (var b = new SolidBrush(t.Accent)) g.FillRectangle(b, tr.X, side == RmDockSide.Fill ? tr.Bottom - S(2) : tr.Y, tr.Width, S(2));
                        RmDraw.Text(g, w.DisplayTitle, Font, tr, on ? t.WindowText : t.SubtleText, ContentAlignment.MiddleCenter, Rtl);
                        tabHits.Add(Tuple.Create(tr, w));
                        x += tw + 1;
                    }
                }
            }
            // auto-hide strips
            foreach (var side in new[] { RmDockSide.Left, RmDockSide.Right, RmDockSide.Top, RmDockSide.Bottom })
            {
                var list = On(side, true).ToList();
                if (list.Count == 0) continue;
                var s = Mirror(side);
                bool vert = s == RmDockSide.Left || s == RmDockSide.Right;
                int pos = S(4);
                foreach (var w in list)
                {
                    int len = RmDraw.Measure(w.DisplayTitle, Font).Width + S(20);
                    Rectangle tr = s == RmDockSide.Left ? new Rectangle(0, pos, StripW, len) : s == RmDockSide.Right ? new Rectangle(Width - StripW, pos, StripW, len)
                                 : s == RmDockSide.Top ? new Rectangle(pos, 0, len, StripW) : new Rectangle(pos, Height - StripW, len, StripW);
                    bool on = popup == w;
                    using (var b = new SolidBrush(on ? t.Accent : tr.Contains(mouse) ? t.Hot : t.HeaderBack)) g.FillRectangle(b, tr);
                    var fore = on ? t.AccentText : t.HeaderText;
                    if (vert)
                    {
                        var st = g.Save();
                        g.TranslateTransform(tr.X + tr.Width / 2f, tr.Y + tr.Height / 2f);
                        g.RotateTransform(90);
                        RmDraw.Text(g, w.DisplayTitle, Font, new Rectangle(-tr.Height / 2, -tr.Width / 2, tr.Height, tr.Width), fore, ContentAlignment.MiddleCenter);
                        g.Restore(st);
                    }
                    else RmDraw.Text(g, w.DisplayTitle, Font, tr, fore, ContentAlignment.MiddleCenter, Rtl);
                    tabHits.Add(Tuple.Create(tr, w));
                    pos += len + S(4);
                }
            }
        }

        Rectangle M2(Rectangle r, Rectangle within) { return Rtl ? new Rectangle(within.Right - (r.X - within.X) - r.Width, r.Y, r.Width, r.Height) : r; }
    }
}
