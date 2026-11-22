// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// RmSideBar, RmRibbon, RmStatusBar.
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
    /// <summary>Vertical side bar with groups and items (images, badges), collapsible to icons.</summary>
    [DefaultEvent("ItemClick")]
    public class RmSideBar : RmControl
    {
        protected override AccessibleRole RmRole { get { return AccessibleRole.Outline; } }
        string itemsSpec = "", selected = "";
        List<RmItem> items = new List<RmItem>();
        bool collapsed;
        int expandedWidth = 220, scroll;
        double widthAnim = -1;
        readonly List<Tuple<Rectangle, RmItem, bool>> hits = new List<Tuple<Rectangle, RmItem, bool>>();
        readonly ToolTip tip = new ToolTip();
        string tipFor = "";

        public event EventHandler<RmItemEventArgs> ItemClick;
        public event EventHandler CollapsedChanged;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        public RmSideBar() { Size = new Size(220, 360); TabStop = true; SetStyle(ControlStyles.Selectable, true); }

        /// <summary>JSON [{Text, Image, Items: [{Text, Name, Image, Count}]}] or "Group:a,b;Group2:c" or "a;b;c".</summary>
        [Category("Data"), DefaultValue("")]
        public string Items { get { return itemsSpec; } set { itemsSpec = value ?? ""; items = RmItem.Parse(itemsSpec); foreach (var g in items) g.Expanded = true; Invalidate(); } }

        [Category("Behavior"), DefaultValue("")]
        public string SelectedItem { get { return selected; } set { selected = value ?? ""; Invalidate(); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool Collapsed
        {
            get { return collapsed; }
            set
            {
                if (collapsed == value) return;
                if (value) expandedWidth = Width;
                collapsed = value;
                widthAnim = Width;
                if (!IsHandleCreated) Width = collapsed ? S(48) : expandedWidth; else Animate();
                var h = CollapsedChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        public void Toggle() { Collapsed = !Collapsed; }

        public void SelectItem(string name) { SelectedItem = name; }

        protected internal override IList<RmAccessibleItem> AccessibleItems()
        {
            var l = new List<RmAccessibleItem>();
            foreach (var h in hits.ToList())
            {
                if (h.Item2 == null) { l.Add(new RmAccessibleItem(collapsed ? "Expand" : "Collapse", h.Item1, Toggle)); continue; }
                var it = h.Item2;
                if (h.Item3) l.Add(new RmAccessibleItem(it.Text, h.Item1, () => { it.Expanded = !it.Expanded; Invalidate(); }, AccessibleRole.OutlineButton));
                else l.Add(new RmAccessibleItem(it.Text, h.Item1, () => ClickItem(it), AccessibleRole.ListItem) { Selected = it.Key == selected });
            }
            return l;
        }

        public void SetCount(string name, int count) { var it = Find(name); if (it != null) { it.Count = count; Invalidate(); } }
        public void SetBadge(string name, int count) { SetCount(name, count); }
        public void SetItemText(string name, string text) { var it = Find(name); if (it != null) { it.Text = text ?? ""; Invalidate(); } }

        bool showToggle = true;

        [Category("Appearance"), DefaultValue(true), Description("The collapse button at the top.")]
        public bool ShowToggle { get { return showToggle; } set { showToggle = value; Invalidate(); } }

        public void AddItem(string group, string text, string image = "")
        {
            var g = items.FirstOrDefault(x => x.Text == group && x.Items.Count > 0) ?? (group.Length > 0 ? null : null);
            var it = new RmItem(text) { Image = image ?? "" };
            if (g == null && group.Length > 0) { g = new RmItem(group) { Expanded = true }; items.Add(g); }
            if (g != null) g.Items.Add(it); else items.Add(it);
            Invalidate();
        }

        RmItem Find(string name) { return items.Concat(items.SelectMany(i => i.All())).FirstOrDefault(i => i.Key == name || i.Text == name); }

        protected override bool AnimateMore()
        {
            if (widthAnim < 0) return false;
            double target = collapsed ? S(48) : expandedWidth;
            widthAnim += (target - widthAnim) * 0.3;
            if (Math.Abs(target - widthAnim) < 1) widthAnim = target;
            int w = (int)widthAnim;
            if (Rtl && Dock == DockStyle.None) Left += Width - w;
            Width = w;
            if (widthAnim == target) { widthAnim = -1; return false; }
            return true;
        }

        int Row { get { return S(36); } }

        protected override void OnMouseWheel(MouseEventArgs e)
        {
            base.OnMouseWheel(e);
            int content = hits.Count == 0 ? 0 : hits.Max(h => h.Item1.Bottom) + scroll;
            scroll = Math.Max(0, Math.Min(Math.Max(0, content - Height + S(8)), scroll - Math.Sign(e.Delta) * Row));
            Invalidate();
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            Invalidate();
            var h = hits.FirstOrDefault(x => x.Item1.Contains(e.Location));
            var name = h != null && h.Item2 != null && collapsed ? h.Item2.Text : "";
            if (name != tipFor) { tipFor = name; tip.SetToolTip(this, name); }
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (e.Button != MouseButtons.Left) return;
            foreach (var h in hits)
            {
                if (!h.Item1.Contains(e.Location)) continue;
                if (h.Item2 == null) { Toggle(); return; }
                if (h.Item3) { h.Item2.Expanded = !h.Item2.Expanded; Invalidate(); return; }
                ClickItem(h.Item2);
                return;
            }
        }

        /// <summary>Selects an item and raises ItemClick (from code: RmSideBar1.Call("PerformClick", "mnuSales")).</summary>
        public void PerformClick(string name) { var it = Find(name); if (it != null) ClickItem(it); }

        void ClickItem(RmItem it)
        {
            if (!it.Enabled) return;
            selected = it.Key;
            Invalidate();
            var all = items.SelectMany(i => i.Items.Count > 0 ? i.Items : new List<RmItem> { i }).ToList();
            RmItemEventArgs.Raise(this, ItemClick, new RmItemEventArgs(it.Key, all.IndexOf(it), it.Text, it));
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            hits.Clear();
            var back = BackColor.A == 255 ? BackColor : (t.Dark ? RmDraw.Blend(t.Window, Color.Black, 0.25) : t.Name == "Office" ? RmDraw.Blend(t.Window, t.Accent, 0.05) : RmDraw.Blend(t.Window, Color.Black, 0.035));
            using (var b = new SolidBrush(back)) g.FillRectangle(b, ClientRectangle);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            var fore = Fore(t);
            // hamburger
            int y = S(8) - scroll;
            if (showToggle)
            {
                var hb = M(new Rectangle(S(6), S(6), S(36), S(32)));
                if (hb.Contains(PointToClient(MousePosition))) RmDraw.Box(g, hb, t.Hot, Color.Empty, 0, Sf(t.Radius));
                RmImages.Draw(g, "icon:menu", null, Rectangle.Inflate(hb, -S(8), -S(7)), fore);
                hits.Add(Tuple.Create(hb, (RmItem)null, false));
                y = S(44) - scroll;
            }
            bool narrow = Width < S(90);
            Action<RmItem, int> drawItem = (it, indent) =>
            {
                var r = new Rectangle(S(4), y, Width - S(8), Row - S(2));
                if (!it.Visible) return;
                var mr = M(r);
                bool sel = it.Key == selected, hot = mr.Contains(PointToClient(MousePosition));
                if (sel) RmDraw.Box(g, mr, RmDraw.Alpha(t.Accent, t.Dark ? 80 : 38), Color.Empty, 0, Sf(t.Radius));
                else if (hot) RmDraw.Box(g, mr, t.Hot, Color.Empty, 0, Sf(t.Radius));
                if (sel) RmDraw.Box(g, M(new Rectangle(r.X, r.Y + S(8), S(3), r.Height - S(16))), t.Accent, Color.Empty, 0, Sf(1.5f));
                int x = narrow ? (Width - S(20)) / 2 : S(14) + (narrow ? 0 : indent);
                var ir = M(new Rectangle(x, r.Y + (r.Height - S(20)) / 2, S(20), S(20)));
                var c = it.Enabled ? (sel ? (t.Dark ? RmDraw.Blend(t.Accent, Color.White, 0.5) : t.Accent) : fore) : t.DisabledText;
                bool img = RmImages.Draw(g, it.Image, null, ir, c, it.Enabled);
                if (!img && narrow) RmDraw.Text(g, it.Text.Length > 0 ? it.Text.Substring(0, 1) : "", Font, ir, c, ContentAlignment.MiddleCenter);
                if (!narrow)
                {
                    int tx = x + (img || it.Image.Length > 0 ? S(30) : 0);
                    using (var f = sel ? new Font(Font, FontStyle.Bold) : null)
                        RmDraw.Text(g, it.Text, f ?? Font, M(new Rectangle(tx, r.Y, r.Right - tx - S(40), r.Height)), it.Enabled ? fore : t.DisabledText, ContentAlignment.MiddleLeft, Rtl);
                }
                if (it.Count != 0)
                {
                    var s = it.Count > 99 ? "99+" : it.Count.ToString(CultureInfo.InvariantCulture);
                    using (var f = new Font(Font.FontFamily, Font.Size * 0.85f, FontStyle.Bold))
                    {
                        int bw = Math.Max(S(18), RmDraw.Measure(s, f).Width + S(4));
                        var br = narrow ? M(new Rectangle(ir.Right - S(6), ir.Y - S(5), bw, S(16))) : M(new Rectangle(r.Right - bw - S(8), r.Y + (r.Height - S(18)) / 2, bw, S(18)));
                        RmDraw.Box(g, br, t.Accent, Color.Empty, 0, br.Height / 2f);
                        RmDraw.Text(g, s, f, br, t.AccentText, ContentAlignment.MiddleCenter);
                    }
                }
                hits.Add(Tuple.Create(mr, it, false));
                y += Row;
            };
            foreach (var it in items)
            {
                if (it.Items.Count == 0) { drawItem(it, 0); continue; }
                if (!narrow)
                {
                    var hr = M(new Rectangle(S(4), y, Width - S(8), S(28)));
                    using (var f = new Font(Font.FontFamily, Font.Size * 0.9f, FontStyle.Bold))
                        RmDraw.Text(g, it.Text.ToUpperInvariant(), f, Rectangle.Inflate(hr, -S(10), 0), t.SubtleText, ContentAlignment.MiddleLeft, Rtl);
                    RmDraw.Chevron(g, M(new Rectangle(Width - S(28), y, S(20), S(28))), t.SubtleText, Sf(1.3f), it.Expanded, false, false);
                    hits.Add(Tuple.Create(hr, it, true));
                    y += S(28);
                }
                else { using (var p = new Pen(RmDraw.Alpha(t.Border, 100))) g.DrawLine(p, S(10), y + S(4), Width - S(10), y + S(4)); y += S(8); }
                if (it.Expanded || narrow) foreach (var k in it.Items) drawItem(k, 0);
            }
            using (var p = new Pen(RmDraw.Alpha(t.Border, 140))) { int x = Rtl ? 0 : Width - 1; g.DrawLine(p, x, 0, x, Height); }
        }
    }

    /// <summary>Ribbon: application button, tabs, groups of large / small buttons, check items and combos, a quick
    /// access toolbar and collapse. Tabs = JSON [{Text, Groups: [{Text, Items: [{Text, Name, Image, Kind}]}]}],
    /// Kind = Large (default for the first items) / Small / Check / Combo / Separator.</summary>
    [DefaultEvent("ItemClick")]
    public class RmRibbon : RmControl
    {
        protected override AccessibleRole RmRole { get { return AccessibleRole.ToolBar; } }
        string tabsSpec = "", quick = "", appText = "File", appMenu = "";
        List<RmItem> tabs = new List<RmItem>(), quickItems = new List<RmItem>(), appItems = new List<RmItem>();
        int selTab, expandedH;
        bool collapsed;
        readonly List<Tuple<Rectangle, RmItem, string>> hits = new List<Tuple<Rectangle, RmItem, string>>();
        Point mouse = new Point(-1, -1);
        RmItem down;
        readonly ToolTip tip = new ToolTip();
        string tipFor = "";

        public event EventHandler<RmItemEventArgs> ItemClick;
        public event EventHandler TabChanged;
        public event EventHandler CollapsedChanged;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        public RmRibbon() { Size = new Size(640, 130); Dock = DockStyle.Top; }

        [Category("Data"), DefaultValue("")]
        public string Tabs { get { return tabsSpec; } set { tabsSpec = value ?? ""; tabs = RmItem.Parse(tabsSpec); selTab = Math.Min(selTab, Math.Max(0, tabs.Count - 1)); Invalidate(); } }

        /// <summary>Quick access toolbar: JSON [{Name, Image, Text}] or "icon:save;icon:undo" (names = the image names).</summary>
        [Category("Data"), DefaultValue("")]
        public string QuickAccess
        {
            get { return quick; }
            set
            {
                quick = value ?? "";
                quickItems = RmItem.Parse(quick);
                foreach (var q in quickItems) if (q.Image.Length == 0 && RmImages.IsGlyph(q.Text)) { q.Image = q.Text; q.Name = q.Name == q.Text ? q.Text.Replace("icon:", "") : q.Name; }
                Invalidate();
            }
        }

        [Category("Appearance"), DefaultValue("File")]
        public string AppButtonText { get { return appText; } set { appText = value ?? ""; Invalidate(); } }

        /// <summary>Application menu items (JSON or ';' list); without it the app button raises ItemClick "AppButton".</summary>
        [Category("Data"), DefaultValue("")]
        public string AppMenu { get { return appMenu; } set { appMenu = value ?? ""; appItems = RmItem.Parse(appMenu); } }

        [Category("Behavior"), DefaultValue(false)]
        public bool Collapsed
        {
            get { return collapsed; }
            set
            {
                if (collapsed == value) return;
                if (value) expandedH = Height;
                collapsed = value;
                Height = collapsed ? TabTop + TabH + S(2) : (expandedH > TabTop + TabH ? expandedH : FullHeight);
                Invalidate();
                var h = CollapsedChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Category("Behavior"), DefaultValue(0)]
        public int SelectedTab
        {
            get { return selTab; }
            set
            {
                var v = Math.Max(0, Math.Min(tabs.Count - 1, value));
                if (v == selTab) return;
                selTab = v; Invalidate();
                var h = TabChanged; if (h != null) h(this, EventArgs.Empty);
            }
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string SelectedTabText { get { return selTab >= 0 && selTab < tabs.Count ? tabs[selTab].Text : ""; } }

        public override string Text { get { return SelectedTabText; } set { base.Text = value; } }

        int TabTop { get { return 0; } }
        int TabH { get { return S(28); } }
        int BodyH { get { return S(96); } }
        int FullHeight { get { return TabTop + TabH + BodyH + S(2); } }
        int QaW { get { return quickItems.Count * S(26); } }

        RmItem Find(string name) { return tabs.SelectMany(t => t.All()).Concat(quickItems).Concat(appItems).FirstOrDefault(i => i.Key == name || i.Name == name); }

        public void SetChecked(string name, bool value) { var it = Find(name); if (it != null) { it.Checked = value; Invalidate(); } }
        public bool GetChecked(string name) { var it = Find(name); return it != null && it.Checked; }
        public void SetEnabled(string name, bool value) { var it = Find(name); if (it != null) { it.Enabled = value; Invalidate(); } }
        public void SetItemText(string name, string text) { var it = Find(name); if (it != null) { it.Text = text ?? ""; Invalidate(); } }
        public string GetItemText(string name) { var it = Find(name); return it != null ? it.Text : ""; }
        public void SelectTab(int index) { SelectedTab = index; }

        protected internal override IList<RmAccessibleItem> AccessibleItems()
        {
            var l = new List<RmAccessibleItem>();
            foreach (var h in hits.ToList())
            {
                var it = h.Item2;
                switch (h.Item3)
                {
                    case "tab": l.Add(new RmAccessibleItem(it.Text, h.Item1, () => { SelectedTab = tabs.IndexOf(it); if (collapsed) Collapsed = false; }, AccessibleRole.PageTab) { Selected = tabs.IndexOf(it) == selTab }); break;
                    case "app": l.Add(new RmAccessibleItem(appText, h.Item1, () => { if (appItems.Count == 0) Raise("AppButton", appText, null); }, AccessibleRole.ButtonMenu)); break;
                    case "collapse": l.Add(new RmAccessibleItem(collapsed ? "Expand the ribbon" : "Collapse the ribbon", h.Item1, ToggleCollapsed)); break;
                    case "combo": l.Add(new RmAccessibleItem(it.Key, h.Item1, null, AccessibleRole.ComboBox) { Value = it.Text }); break;
                    default:
                        l.Add(new RmAccessibleItem(string.IsNullOrEmpty(it.Text) || h.Item3 == "quick" ? it.Key : it.Text, h.Item1, () => Activate(it),
                                                   it.Kind.Equals("Check", StringComparison.OrdinalIgnoreCase) ? AccessibleRole.CheckButton : AccessibleRole.PushButton) { Checked = it.Checked });
                        break;
                }
            }
            return l;
        }
        public void ToggleCollapsed() { Collapsed = !Collapsed; }
        public void Toggle() { Collapsed = !Collapsed; }
        /// <summary>Value of a combo / check item (combo: its text; check: True / False).</summary>
        public void SetValue(string name, string value)
        {
            var it = Find(name);
            if (it == null) return;
            if (it.Kind.Equals("Check", StringComparison.OrdinalIgnoreCase)) it.Checked = RmItem.Bool(value); else { it.Text = value ?? ""; it.Value = value ?? ""; }
            Invalidate();
        }
        public string GetValue(string name)
        {
            var it = Find(name);
            if (it == null) return "";
            return it.Kind.Equals("Check", StringComparison.OrdinalIgnoreCase) ? (it.Checked ? "True" : "False") : it.Text;
        }

        /// <summary>Clicks an item by name (raises ItemClick; check items toggle).</summary>
        public void PerformClick(string name) { var it = Find(name); if (it != null) Activate(it); }

        void Activate(RmItem it)
        {
            if (!it.Enabled) return;
            if (it.Kind.Equals("Check", StringComparison.OrdinalIgnoreCase)) it.Checked = !it.Checked;
            Invalidate();
            Raise(it.Key, it.Text, it);
        }

        void Raise(string name, string text, RmItem it)
        {
            RmItemEventArgs.Raise(this, ItemClick, new RmItemEventArgs(name, -1, text, it));
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            mouse = e.Location; Invalidate();
            var h = hits.FirstOrDefault(x => x.Item1.Contains(e.Location));
            var s = h != null && h.Item2 != null ? (h.Item2.ToolTip.Length > 0 ? h.Item2.ToolTip : (h.Item3 == "quick" ? h.Item2.Text.Replace("icon:", "") : "")) : "";
            if (s != tipFor) { tipFor = s; tip.SetToolTip(this, s); }
        }

        protected override void OnMouseLeave(EventArgs e) { mouse = new Point(-1, -1); base.OnMouseLeave(e); }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e);
            var h = hits.FirstOrDefault(x => x.Item1.Contains(e.Location));
            down = h != null ? h.Item2 : null;
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            if (e.Button != MouseButtons.Left) return;
            var h = hits.FirstOrDefault(x => x.Item1.Contains(e.Location));
            if (h == null) return;
            switch (h.Item3)
            {
                case "tab": SelectedTab = tabs.IndexOf(h.Item2); if (collapsed) Collapsed = false; break;
                case "collapse": ToggleCollapsed(); break;
                case "app":
                    if (appItems.Count == 0) { Raise("AppButton", appText, null); break; }
                    var menu = new ContextMenuStrip { Renderer = new RmMenuRenderer(Theme), RightToLeft = RightToLeft };
                    foreach (var it in appItems)
                    {
                        if (it.Text == "-") { menu.Items.Add(new ToolStripSeparator()); continue; }
                        var k = it;
                        menu.Items.Add(new ToolStripMenuItem(it.Text, null, (s, a) => Raise(k.Key, k.Text, k)) { Enabled = it.Enabled });
                    }
                    menu.Show(this, new Point(h.Item1.X, h.Item1.Bottom));
                    break;
                case "combo":
                    {
                        var it = h.Item2;
                        if (!it.Enabled) break;
                        var m = new ContextMenuStrip { Renderer = new RmMenuRenderer(Theme), RightToLeft = RightToLeft };
                        foreach (var opt in it.Items.Count > 0 ? it.Items.Select(x => x.Text) : RmScript.Split(it.ExtraStr("Options")))
                        {
                            var o = opt;
                            m.Items.Add(new ToolStripMenuItem(o, null, (s, a) => { it.Text = o; it.Value = o; Invalidate(); Raise(it.Key, o, it); }) { Checked = o == it.Text });
                        }
                        m.Show(this, new Point(h.Item1.X, h.Item1.Bottom));
                        break;
                    }
                default:
                    if (h.Item2 != null && h.Item2 == down) Activate(h.Item2);
                    break;
            }
            down = null;
        }

        protected override void OnMouseDoubleClick(MouseEventArgs e)
        {
            base.OnMouseDoubleClick(e);
            if (e.Y >= TabTop && e.Y < TabTop + TabH && hits.Any(x => x.Item3 == "tab" && x.Item1.Contains(e.Location))) ToggleCollapsed();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            hits.Clear();
            bool office = t.Name == "Office";
            Color tabBar = office ? t.Accent : (t.Dark ? RmDraw.Blend(t.Window, Color.Black, 0.25) : t.Window);
            Color body = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.04) : (t.Name == "Light" ? Color.FromArgb(250, 250, 250) : t.Surface);
            Color tabFore = office ? t.AccentText : t.WindowText;
            using (var b = new SolidBrush(tabBar)) g.FillRectangle(b, 0, 0, Width, TabTop + TabH);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            // quick access toolbar: right end of the tab row, before the collapse button
            int x = Width - S(34) - QaW;
            foreach (var q in quickItems)
            {
                var r = M(new Rectangle(x, TabTop + S(3), S(24), TabH - S(6)));
                if (r.Contains(mouse)) RmDraw.Box(g, r, RmDraw.Alpha(tabFore, 40), Color.Empty, 0, Sf(t.Radius));
                RmImages.Draw(g, q.Image, null, Rectangle.Inflate(r, -S(4), -S(3)), tabFore, q.Enabled);
                hits.Add(Tuple.Create(r, q, "quick"));
                x += S(26);
            }
            // app button + tabs
            x = S(4);
            int ty = TabTop;
            if (appText.Length > 0)
            {
                int w = RmDraw.Measure(appText, Font).Width + S(28);
                var r = M(new Rectangle(x, ty + S(2), w, TabH - S(2)));
                Color ab = office ? RmDraw.Blend(t.Accent, Color.Black, 0.15) : t.Accent;
                RmDraw.Box(g, r, RmDraw.Blend(ab, Color.White, r.Contains(mouse) ? 0.12 : 0), Color.Empty, 0, Sf(t.Radius));
                RmDraw.Text(g, appText, Font, r, t.AccentText, ContentAlignment.MiddleCenter, Rtl);
                hits.Add(Tuple.Create(r, (RmItem)null, "app"));
                x += w + S(6);
            }
            for (int i = 0; i < tabs.Count; i++)
            {
                int w = RmDraw.Measure(tabs[i].Text, Font).Width + S(24);
                var r = M(new Rectangle(x, ty + S(2), w, TabH - S(2)));
                bool sel = i == selTab && !collapsed;
                if (sel)
                {
                    using (var path = RmDraw.Round(new RectangleF(r.X, r.Y, r.Width, r.Height + Sf(6)), Sf(t.Radius)))
                    using (var b = new SolidBrush(body)) g.FillPath(b, path);
                }
                else if (r.Contains(mouse)) RmDraw.Box(g, r, RmDraw.Alpha(tabFore, 30), Color.Empty, 0, Sf(t.Radius));
                RmDraw.Text(g, tabs[i].Text, Font, r, sel ? (office ? t.Accent : t.WindowText) : tabFore, ContentAlignment.MiddleCenter, Rtl);
                if (sel && t.Name == "Metro") using (var b = new SolidBrush(t.Accent)) g.FillRectangle(b, r.X + S(6), r.Bottom - S(3), r.Width - S(12), S(3));
                hits.Add(Tuple.Create(r, tabs[i], "tab"));
                x += w + S(2);
            }
            var cr = M(new Rectangle(Width - S(28), ty + S(4), S(22), TabH - S(8)));
            if (cr.Contains(mouse)) RmDraw.Box(g, cr, RmDraw.Alpha(tabFore, 40), Color.Empty, 0, Sf(t.Radius));
            RmDraw.Chevron(g, cr, tabFore, Sf(1.4f), collapsed);
            hits.Add(Tuple.Create(cr, (RmItem)null, "collapse"));
            if (collapsed || selTab < 0 || selTab >= tabs.Count) return;
            // body
            var br = new Rectangle(0, ty + TabH, Width, Height - ty - TabH);
            using (var b = new SolidBrush(body)) g.FillRectangle(b, br);
            using (var p = new Pen(RmDraw.Alpha(t.Border, 160))) g.DrawLine(p, 0, Height - 1, Width, Height - 1);
            x = S(4);
            int top = br.Y + S(4), capH = S(18), areaH = br.Height - capH - S(6);
            foreach (var grp in tabs[selTab].Items)
            {
                int gx = x;
                var cols = Columns(grp.Items, areaH);
                int gw = 0;
                foreach (var col in cols) gw += col.Item1 + S(2);
                int capW = RmDraw.Measure(grp.Text, Font).Width + S(16);
                gw = Math.Max(gw, capW);
                int cx = gx + S(4) + Math.Max(0, (gw - cols.Sum(c => c.Item1 + S(2))) / 2);
                foreach (var col in cols)
                {
                    int cy = top;
                    foreach (var it in col.Item2)
                    {
                        bool large = col.Item3;
                        int h = large ? areaH : Math.Min(S(26), areaH / 3);
                        var r = M(new Rectangle(cx, cy, col.Item1, h));
                        DrawItem(g, t, it, r, large);
                        cy += h + (large ? 0 : S(2));
                    }
                    cx += col.Item1 + S(2);
                }
                var cap = M(new Rectangle(gx, br.Bottom - capH - S(3), gw + S(8), capH));
                RmDraw.Text(g, grp.Text, Font, cap, t.SubtleText, ContentAlignment.MiddleCenter, Rtl);
                x = gx + gw + S(10);
                using (var p = new Pen(RmDraw.Alpha(t.Border, 140))) { int sx = Rtl ? Width - x + S(2) : x - S(2); g.DrawLine(p, sx, top + S(2), sx, br.Bottom - S(6)); }
            }
        }

        /// <summary>Layout of a group: (width, items, large) per column - large items take a column each, small ones stack by 3.</summary>
        List<Tuple<int, List<RmItem>, bool>> Columns(List<RmItem> items, int areaH)
        {
            var cols = new List<Tuple<int, List<RmItem>, bool>>();
            List<RmItem> stack = null;
            for (int i = 0; i < items.Count; i++)
            {
                var it = items[i];
                if (!it.Visible) continue;
                var kind = it.Kind.ToLowerInvariant();
                bool large = kind == "large" || (kind.Length == 0 && it.Image.Length > 0 && i == 0);
                if (kind == "separator" || it.Text == "-") { stack = null; continue; }
                if (large)
                {
                    stack = null;
                    int w = Math.Max(S(52), WrapWidth(it.Text) + S(12));
                    cols.Add(Tuple.Create(w, new List<RmItem> { it }, true));
                    continue;
                }
                if (stack == null || stack.Count >= 3) { stack = new List<RmItem>(); cols.Add(Tuple.Create(0, stack, false)); }
                stack.Add(it);
            }
            for (int i = 0; i < cols.Count; i++)
                if (!cols[i].Item3)
                {
                    int w = cols[i].Item2.Max(it => SmallWidth(it));
                    cols[i] = Tuple.Create(w, cols[i].Item2, false);
                }
            return cols;
        }

        int WrapWidth(string s)
        {
            var words = (s ?? "").Split(' ');
            if (words.Length <= 1) return RmDraw.Measure(s, Font).Width;
            int best = int.MaxValue;
            for (int k = 1; k < words.Length; k++)
                best = Math.Min(best, Math.Max(RmDraw.Measure(string.Join(" ", words.Take(k)), Font).Width, RmDraw.Measure(string.Join(" ", words.Skip(k)), Font).Width));
            return best;
        }

        int SmallWidth(RmItem it)
        {
            var kind = it.Kind.ToLowerInvariant();
            if (kind == "combo") { int n; return S(int.TryParse(it.ExtraStr("Width"), out n) ? n : 120); }
            return RmDraw.Measure(it.Text, Font).Width + S(kind == "check" ? 30 : (it.Image.Length > 0 ? 32 : 14));
        }

        void DrawItem(Graphics g, RmTheme t, RmItem it, Rectangle r, bool large)
        {
            var kind = it.Kind.ToLowerInvariant();
            bool hot = r.Contains(mouse) && it.Enabled, pressed = hot && down == it && MouseButtons == MouseButtons.Left;
            var fore = it.Enabled ? t.WindowText : t.DisabledText;
            if (kind == "combo")
            {
                var box = new Rectangle(r.X, r.Y + S(2), r.Width, r.Height - S(4));
                RmDraw.Box(g, box, t.Input, hot ? t.HotBorder : t.Border, 1, Sf(t.Radius));
                RmDraw.Text(g, it.Text, Font, new Rectangle(box.X + S(6), box.Y, box.Width - S(26), box.Height), it.Enabled ? t.InputText : t.DisabledText, ContentAlignment.MiddleLeft, Rtl);
                RmDraw.Chevron(g, Rtl ? new Rectangle(box.X, box.Y, S(20), box.Height) : new Rectangle(box.Right - S(20), box.Y, S(20), box.Height), t.SubtleText, Sf(1.3f));
                hits.Add(Tuple.Create(r, it, "combo"));
                return;
            }
            if (hot || pressed || (it.Checked && kind != "check"))
                RmDraw.Box(g, r, pressed ? t.Pressed : it.Checked && !hot ? RmDraw.Alpha(t.Accent, 45) : t.Hot, hot ? t.HotBorder : RmDraw.Alpha(t.Accent, 120), 1, Sf(t.Radius));
            if (kind == "check")
            {
                int b = S(14);
                var box = Rtl ? new Rectangle(r.Right - b - S(4), r.Y + (r.Height - b) / 2, b, b) : new Rectangle(r.X + S(4), r.Y + (r.Height - b) / 2, b, b);
                RmDraw.Box(g, box, it.Checked ? t.Accent : t.Input, it.Checked ? t.Accent : t.Border, 1, Math.Min(Sf(t.Radius), S(3)));
                if (it.Checked) RmDraw.Check(g, box, t.AccentText, Sf(1.6f));
                RmDraw.Text(g, it.Text, Font, Rtl ? new Rectangle(r.X, r.Y, r.Width - b - S(10), r.Height) : new Rectangle(box.Right + S(6), r.Y, r.Right - box.Right - S(6), r.Height), fore, ContentAlignment.MiddleLeft, Rtl);
            }
            else if (large)
            {
                int s = S(32);
                RmImages.Draw(g, it.Image, null, new Rectangle(r.X + (r.Width - s) / 2, r.Y + S(6), s, s), it.Enabled ? (it.Image.StartsWith("icon:") ? t.Accent : fore) : t.DisabledText, it.Enabled);
                RmDraw.Text(g, it.Text, Font, new Rectangle(r.X + S(2), r.Y + s + S(10), r.Width - S(4), r.Height - s - S(12)), fore, ContentAlignment.TopCenter, Rtl, true);
            }
            else
            {
                int s = S(16);
                bool img = it.Image.Length > 0;
                var ir = Rtl ? new Rectangle(r.Right - s - S(5), r.Y + (r.Height - s) / 2, s, s) : new Rectangle(r.X + S(5), r.Y + (r.Height - s) / 2, s, s);
                if (img) RmImages.Draw(g, it.Image, null, ir, fore, it.Enabled);
                int tx = img ? s + S(10) : S(6);
                RmDraw.Text(g, it.Text, Font, Rtl ? new Rectangle(r.X, r.Y, r.Width - tx, r.Height) : new Rectangle(r.X + tx, r.Y, r.Width - tx, r.Height), fore, ContentAlignment.MiddleLeft, Rtl);
            }
            hits.Add(Tuple.Create(r, it, "item"));
        }
    }

    /// <summary>Modern status bar with panels: text, progress and zoom. Panels = "Ready;Line 1" or JSON
    /// [{Text, Name, Kind: Text|Progress|Zoom, Width (-1 = spring), Value}].</summary>
    [DefaultEvent("PanelClick")]
    public class RmStatusBar : RmControl
    {
        protected override AccessibleRole RmRole { get { return AccessibleRole.StatusBar; } }
        string spec = "";
        List<RmItem> panels = new List<RmItem>();
        readonly List<Rectangle> rects = new List<Rectangle>();
        Point mouse = new Point(-1, -1);

        public event EventHandler<RmItemEventArgs> PanelClick;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;
        public event EventHandler ZoomChanged;
        /// <summary>The zoom (or a progress panel value set by the user) changed.</summary>
        public event EventHandler ValueChanged;

        bool accentBar;

        [Category("Appearance"), DefaultValue(false), Description("The bar is painted in the accent colour.")]
        public bool AccentBar { get { return accentBar; } set { accentBar = value; Invalidate(); } }

        public RmStatusBar() { Size = new Size(400, 26); Dock = DockStyle.Bottom; }

        [Category("Data"), DefaultValue("")]
        public string Panels { get { return spec; } set { spec = value ?? ""; panels = RmItem.Parse(spec); Invalidate(); } }

        public override string Text { get { return panels.Count > 0 ? panels[0].Text : base.Text; } set { if (panels.Count > 0) { panels[0].Text = value ?? ""; Invalidate(); } else base.Text = value; } }

        RmItem Panel(string nameOrIndex)
        {
            int i;
            if (int.TryParse(nameOrIndex, NumberStyles.Integer, CultureInfo.InvariantCulture, out i)) return i >= 0 && i < panels.Count ? panels[i] : null;
            return panels.FirstOrDefault(p => p.Key == nameOrIndex || p.Text == nameOrIndex);
        }

        protected internal override IList<RmAccessibleItem> AccessibleItems()
        {
            Measure();
            var l = new List<RmAccessibleItem>();
            for (int i = 0; i < panels.Count && i < rects.Count; i++)
            {
                var p = panels[i]; int k = i;
                l.Add(new RmAccessibleItem(p.Text.Length > 0 ? p.Text : p.Key, rects[i], () => { var h = PanelClick; if (h != null) h(this, new RmItemEventArgs(p.Key, k, p.Text, p)); }, AccessibleRole.StatusBar) { Value = p.Value });
            }
            return l;
        }

        public void SetPanelText(string panel, string text) { var p = Panel(panel); if (p != null) { p.Text = text ?? ""; Invalidate(); } }
        public string GetPanelText(string panel) { var p = Panel(panel); return p != null ? p.Text : ""; }
        public void SetPanelValue(string panel, int value) { var p = Panel(panel); if (p != null) { p.Value = value.ToString(CultureInfo.InvariantCulture); Invalidate(); } }
        public int GetPanelValue(string panel) { var p = Panel(panel); int v; return p != null && int.TryParse(p.Value, out v) ? v : 0; }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int Zoom
        {
            get { var p = panels.FirstOrDefault(x => x.Kind.Equals("Zoom", StringComparison.OrdinalIgnoreCase)); int v; return p != null && int.TryParse(p.Value, out v) ? v : 100; }
            set { var p = panels.FirstOrDefault(x => x.Kind.Equals("Zoom", StringComparison.OrdinalIgnoreCase)); if (p != null) { p.Value = Math.Max(10, Math.Min(500, value)).ToString(CultureInfo.InvariantCulture); Invalidate(); var h = ZoomChanged; if (h != null) h(this, EventArgs.Empty); var v = ValueChanged; if (v != null) v(this, EventArgs.Empty); } }
        }

        void Measure()
        {
            rects.Clear();
            int fixedW = 0, springs = 0;
            var widths = new List<int>();
            foreach (var p in panels)
            {
                int w;
                if (!int.TryParse(p.ExtraStr("Width", ""), NumberStyles.Integer, CultureInfo.InvariantCulture, out w))
                    w = p.Kind.Equals("Zoom", StringComparison.OrdinalIgnoreCase) ? 170 : p.Kind.Equals("Progress", StringComparison.OrdinalIgnoreCase) ? 140 : (panels.IndexOf(p) == 0 ? -1 : (int)(RmDraw.Measure(p.Text, Font).Width / (DeviceDpi / 96f)) + 24);
                if (w < 0) springs++; else fixedW += S(w);
                widths.Add(w);
            }
            int rest = Math.Max(0, Width - fixedW), x = 0;
            foreach (var w0 in widths)
            {
                int w = w0 < 0 ? rest / Math.Max(1, springs) : S(w0);
                rects.Add(M(new Rectangle(x, 0, w, Height)));
                x += w;
            }
        }

        protected override void OnMouseMove(MouseEventArgs e) { mouse = e.Location; Invalidate(); base.OnMouseMove(e); }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            Measure();
            for (int i = 0; i < rects.Count; i++)
            {
                if (!rects[i].Contains(e.Location)) continue;
                var p = panels[i];
                if (p.Kind.Equals("Zoom", StringComparison.OrdinalIgnoreCase))
                {
                    var r = rects[i];
                    if (e.X < r.X + S(26)) Zoom = Zoom - 10; else if (e.X > r.Right - S(26)) Zoom = Zoom + 10;
                }
                RmItemEventArgs.Raise(this, PanelClick, new RmItemEventArgs(p.Key, i, p.Text, p));
                return;
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            var t = Theme;
            Measure();
            bool office = t.Name == "Office" || accentBar;
            var back = BackColor.A == 255 ? BackColor : office ? t.Accent : (t.Dark ? RmDraw.Blend(t.Window, Color.Black, 0.25) : RmDraw.Blend(t.Window, Color.Black, 0.04));
            var fore = office ? t.AccentText : Fore(t);
            using (var b = new SolidBrush(back)) g.FillRectangle(b, ClientRectangle);
            if (!office) using (var p = new Pen(RmDraw.Alpha(t.Border, 160))) g.DrawLine(p, 0, 0, Width, 0);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            for (int i = 0; i < panels.Count; i++)
            {
                var p = panels[i];
                var r = rects[i];
                if (r.Contains(mouse)) using (var b = new SolidBrush(RmDraw.Alpha(fore, 22))) g.FillRectangle(b, r);
                var kind = p.Kind.ToLowerInvariant();
                if (kind == "progress")
                {
                    int v; int.TryParse(p.Value, out v);
                    var tr = new Rectangle(r.X + S(8), r.Y + (r.Height - S(6)) / 2, r.Width - S(16), S(6));
                    RmDraw.Box(g, tr, RmDraw.Alpha(fore, 50), Color.Empty, 0, t.Radius == 0 ? 0 : S(3));
                    int fw = tr.Width * Math.Max(0, Math.Min(100, v)) / 100;
                    if (fw > 0) RmDraw.Box(g, Rtl ? new Rectangle(tr.Right - fw, tr.Y, fw, tr.Height) : new Rectangle(tr.X, tr.Y, fw, tr.Height), office ? t.AccentText : t.Accent, Color.Empty, 0, t.Radius == 0 ? 0 : S(3));
                }
                else if (kind == "zoom")
                {
                    int z = Zoom;
                    RmDraw.Text(g, "−", Font, new Rectangle(r.X, r.Y, S(24), r.Height), fore, ContentAlignment.MiddleCenter);
                    RmDraw.Text(g, "+", Font, new Rectangle(r.Right - S(24), r.Y, S(24), r.Height), fore, ContentAlignment.MiddleCenter);
                    var tr = new Rectangle(r.X + S(26), r.Y + r.Height / 2 - S(1), r.Width - S(90), S(2));
                    using (var b = new SolidBrush(RmDraw.Alpha(fore, 120))) g.FillRectangle(b, tr);
                    float f = Math.Max(0, Math.Min(1, (z - 10) / 290f));
                    float kx = tr.X + tr.Width * f;
                    using (var b = new SolidBrush(fore)) g.FillRectangle(b, kx - S(2), r.Y + S(7), S(4), r.Height - S(14));
                    RmDraw.Text(g, z.ToString(CultureInfo.InvariantCulture) + "%", Font, new Rectangle(tr.Right + S(2), r.Y, S(40), r.Height), fore, ContentAlignment.MiddleCenter);
                }
                else
                {
                    int x = S(8);
                    if (p.Image.Length > 0) { RmImages.Draw(g, p.Image, null, M2(new Rectangle(r.X + x, r.Y + (r.Height - S(16)) / 2, S(16), S(16)), r), fore); x += S(22); }
                    RmDraw.Text(g, p.Text, Font, M2(new Rectangle(r.X + x, r.Y, r.Width - x - S(6), r.Height), r), fore, ContentAlignment.MiddleLeft, Rtl);
                }
                if (i < panels.Count - 1) using (var pen = new Pen(RmDraw.Alpha(fore, 50))) { int sx = Rtl ? r.X : r.Right - 1; g.DrawLine(pen, sx, S(5), sx, Height - S(5)); }
            }
        }

        Rectangle M2(Rectangle r, Rectangle within) { return Rtl ? new Rectangle(within.Right - (r.X - within.X) - r.Width, r.Y, r.Width, r.Height) : r; }
    }
}
