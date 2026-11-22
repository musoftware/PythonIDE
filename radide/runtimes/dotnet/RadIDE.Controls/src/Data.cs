// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// RmGrid (DataGridView + themed painting, column kinds, filter row, grouping), RmTreeView, RmListView.
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
    /// <summary>Advanced grid: typed columns (Text, Number, Check, Combo, Date, Image, Progress, Button), sorting, a filter
    /// row, grouping by a column, frozen columns, editing, alternating rows, selection modes; themed painting.</summary>
    [DefaultEvent("CellClick")]
    public class RmGrid : DataGridView, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty;
        string columnsSpec = "", rowsSpec = "", groupBy = "", selection = "Row";
        bool allowSort = true, allowFilter;
        readonly List<RmItem> cols = new List<RmItem>();
        readonly Panel filterBar = new Panel();
        readonly List<TextBox> filters = new List<TextBox>();
        readonly HashSet<string> collapsedGroups = new HashSet<string>();
        bool grouping;

        public event EventHandler<RmItemEventArgs> ButtonCellClick;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        public RmGrid()
        {
            DoubleBuffered = true;
            BorderStyle = BorderStyle.None;
            CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal;
            ColumnHeadersBorderStyle = DataGridViewHeaderBorderStyle.None;
            EnableHeadersVisualStyles = false;
            RowHeadersVisible = false;
            AllowUserToResizeRows = false;
            AllowUserToAddRows = false;
            SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
            ColumnHeadersHeight = 32;
            RowTemplate.Height = 28;
            Font = new Font("Segoe UI", 9f);
            Size = new Size(420, 220);
            filterBar.Visible = false;
            filterBar.Height = 28;
            Controls.Add(filterBar);
            RmThemeManager.ThemeChanged += OnTheme;
            Recolor();
        }

        protected override void Dispose(bool disposing) { RmThemeManager.ThemeChanged -= OnTheme; base.Dispose(disposing); }

        void OnTheme(object s, EventArgs e) { Recolor(); Invalidate(); }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get { return style; } set { style = value; Recolor(); } }

        [Category("Appearance")]
        public Color AccentColor { get { return accent; } set { accent = value; Recolor(); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        /// <summary>JSON [{Text, Name, Kind: Text|Number|Check|Combo|Date|Image|Progress|Button, Width, Items, Format, ReadOnly, Frozen}] or "A;B;C".</summary>
        [RmName("Columns"), Category("Data"), DefaultValue("")]
        public string ColumnsJson { get { return columnsSpec; } set { columnsSpec = value ?? ""; BuildColumns(); } }

        /// <summary>JSON [["a", 1], ["b", 2]] or text rows "a;1|b;2" (or one row per line).</summary>
        [RmName("Rows"), Category("Data"), DefaultValue("")]
        public string RowsData { get { return rowsSpec; } set { rowsSpec = value ?? ""; LoadRows(rowsSpec); } }

        [Category("Behavior"), DefaultValue(true)]
        public bool AllowSort { get { return allowSort; } set { allowSort = value; foreach (DataGridViewColumn c in Columns) c.SortMode = value ? DataGridViewColumnSortMode.Automatic : DataGridViewColumnSortMode.NotSortable; } }

        [Category("Behavior"), DefaultValue(false), Description("A row of filter boxes under the header (contains, case-insensitive).")]
        public bool AllowFilter { get { return allowFilter; } set { allowFilter = value; BuildFilters(); } }

        [Category("Behavior"), DefaultValue(""), Description("Column name (or header) to group the rows by; empty = no grouping.")]
        public string GroupBy { get { return groupBy; } set { groupBy = value ?? ""; Regroup(); } }

        /// <summary>Row, MultiRow, Cell, MultiCell (or the DataGridViewSelectionMode names).</summary>
        [RmName("SelectionMode"), Category("Behavior"), DefaultValue("Row")]
        public string SelectionKind
        {
            get { return selection; }
            set
            {
                selection = string.IsNullOrEmpty(value) ? "Row" : value;
                var v = selection.ToLowerInvariant();
                MultiSelect = v.StartsWith("multi") || v.Contains("extended");
                SelectionMode = v.Contains("cell") ? DataGridViewSelectionMode.CellSelect : v.Contains("column") ? DataGridViewSelectionMode.FullColumnSelect : DataGridViewSelectionMode.FullRowSelect;
            }
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int Count { get { return Rows.Cast<DataGridViewRow>().Count(r => !IsGroupRow(r)); } }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int SelectedRow
        {
            get { return CurrentCell != null ? DataIndex(CurrentCell.RowIndex) : -1; }
            set { var r = RowOf(value); if (r >= 0) { ClearSelection(); CurrentCell = this[Math.Max(0, FirstVisibleColumn()), r]; Rows[r].Selected = true; } }
        }

        int FirstVisibleColumn() { foreach (DataGridViewColumn c in Columns) if (c.Visible) return c.Index; return -1; }

        void Recolor()
        {
            var t = Theme;
            var back = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.03) : (t.Name == "Light" ? Color.White : t.Input);
            BackgroundColor = back;
            GridColor = RmDraw.Blend(t.Border, back, 0.45);
            DefaultCellStyle.BackColor = back;
            DefaultCellStyle.ForeColor = t.InputText;
            DefaultCellStyle.SelectionBackColor = RmDraw.Blend(back, t.Selection, t.Dark ? 0.55 : 0.22);
            DefaultCellStyle.SelectionForeColor = t.InputText;
            DefaultCellStyle.Padding = new Padding(4, 0, 4, 0);
            AlternatingRowsDefaultCellStyle.BackColor = alternating ? RmDraw.Blend(back, t.Dark ? Color.White : t.Accent, 0.035) : back;
            ColumnHeadersDefaultCellStyle.BackColor = t.Name == "Office" ? t.Accent : RmDraw.Blend(back, t.Dark ? Color.White : Color.Black, 0.045);
            ColumnHeadersDefaultCellStyle.ForeColor = t.Name == "Office" ? t.AccentText : t.WindowText;
            ColumnHeadersDefaultCellStyle.SelectionBackColor = ColumnHeadersDefaultCellStyle.BackColor;
            ColumnHeadersDefaultCellStyle.Font = new Font(Font, FontStyle.Bold);
            ColumnHeadersDefaultCellStyle.Padding = new Padding(4, 0, 4, 0);
            filterBar.BackColor = back;
            foreach (var f in filters) { f.BackColor = t.Input; f.ForeColor = t.InputText; }
            foreach (Control k in Controls) if (k is ScrollBar) RmNativeTheme.Apply(k, t.Dark);
            Invalidate();
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            float sc = DeviceDpi / 96f;
            ColumnHeadersHeight = (int)(32 * sc) + (allowFilter ? (int)(28 * sc) : 0);
            RowTemplate.Height = (int)(rowHeight * sc);
            foreach (DataGridViewRow r in Rows) r.Height = RowTemplate.Height;
            LayoutFilters();
        }

        void BuildColumns()
        {
            Columns.Clear();
            cols.Clear();
            var spec = columnsSpec.Trim();
            if (spec.StartsWith("[")) cols.AddRange(RmItem.Parse(spec));
            else foreach (var part in RmScript.Split(spec))
                {   // short form "Name;Age:Number:60;Done:Check"
                    var bits = part.Split(':');
                    var it = new RmItem(bits[0].Trim());
                    if (bits.Length > 1) it.Kind = bits[1].Trim();
                    if (bits.Length > 2) it.Extra["Width"] = bits[2].Trim();
                    cols.Add(it);
                }
            foreach (var c in cols)
            {
                DataGridViewColumn col;
                var kind = (c.Kind.Length > 0 ? c.Kind : c.ExtraStr("Type", "Text")).ToLowerInvariant();
                switch (kind)
                {
                    case "check": case "bool": case "checkbox": col = new DataGridViewCheckBoxColumn(); break;
                    case "combo": case "list":
                        var cc = new DataGridViewComboBoxColumn { FlatStyle = FlatStyle.Flat, DisplayStyle = DataGridViewComboBoxDisplayStyle.Nothing };
                        foreach (var o in c.Items.Count > 0 ? c.Items.Select(i => i.Text) : RmScript.Split(c.ExtraStr("Options"))) cc.Items.Add(o);
                        col = cc; break;
                    case "button": col = new DataGridViewButtonColumn { FlatStyle = FlatStyle.Flat, UseColumnTextForButtonValue = c.ExtraStr("ButtonText").Length > 0, Text = c.ExtraStr("ButtonText") }; break;
                    case "image": case "progress": col = new DataGridViewTextBoxColumn { ReadOnly = true }; break;
                    case "number": case "int": case "double":
                        col = new DataGridViewTextBoxColumn { ValueType = typeof(double) };
                        col.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight;
                        if (c.ExtraStr("Format").Length > 0) col.DefaultCellStyle.Format = c.ExtraStr("Format");
                        break;
                    case "date":
                        col = new DataGridViewTextBoxColumn { ValueType = typeof(DateTime) };
                        col.DefaultCellStyle.Format = c.ExtraStr("Format", "d");
                        break;
                    default: col = new DataGridViewTextBoxColumn(); break;
                }
                col.Name = c.Key;
                col.HeaderText = c.Text;
                col.Tag = kind;
                int w;
                if (int.TryParse(c.ExtraStr("Width"), NumberStyles.Integer, CultureInfo.InvariantCulture, out w) && w > 0) col.Width = (int)(w * DeviceDpi / 96f);
                else if (c.ExtraStr("Width") == "-1" || c.ExtraStr("Fill") == "True") col.AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
                if (RmItem.Bool(c.Extra.ContainsKey("ReadOnly") ? c.Extra["ReadOnly"] : false)) col.ReadOnly = true;
                if (RmItem.Bool(c.Extra.ContainsKey("Frozen") ? c.Extra["Frozen"] : false)) col.Frozen = true;
                col.SortMode = allowSort && kind != "button" ? DataGridViewColumnSortMode.Automatic : DataGridViewColumnSortMode.NotSortable;
                Columns.Add(col);
            }
            if (Columns.Count > 0 && Columns.Cast<DataGridViewColumn>().All(c => c.AutoSizeMode != DataGridViewAutoSizeColumnMode.Fill))
                Columns[Columns.Count - 1].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            BuildFilters();
        }

        object Convert2(int col, object v)
        {
            if (col < 0 || col >= Columns.Count) return v;
            var s = v as string;
            if (s == null) return v;
            var kind = Columns[col].Tag as string;
            double d; DateTime dt;
            if ((kind == "number" || kind == "int" || kind == "double") && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d)) return d;
            if (kind == "date" && DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt)) return dt;
            if (kind == "check" || kind == "bool" || kind == "checkbox") return RmItem.Bool(s);
            if (kind == "progress" && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d)) return d;
            return v;
        }

        void LoadRows(string spec)
        {
            Rows.Clear();
            spec = (spec ?? "").Trim();
            if (spec.Length == 0) return;
            if (spec.StartsWith("["))
            {
                object v;
                try { v = RmJson.Parse(spec); } catch (Exception) { return; }
                foreach (var row in (v as List<object>) ?? new List<object>())
                {
                    var arr = row as List<object>;
                    var dict = row as Dictionary<string, object>;
                    if (arr != null) AddRowValues(arr.Select(x => x is double ? (object)x : RmItem.Str(x)).ToArray());
                    else if (dict != null) AddRowValues(Columns.Cast<DataGridViewColumn>().Select(c => { object o; return dict.TryGetValue(c.Name, out o) ? (o is double ? o : RmItem.Str(o)) : (object)""; }).ToArray());
                }
            }
            else foreach (var line in spec.Replace("\r", "").Split(new[] { '\n', ';' }, StringSplitOptions.RemoveEmptyEntries))
                    AddRowValues(line.Split('|').Select(s => (object)s.Trim()).ToArray());       // "a|b|c;d|e|f"
            Regroup();
        }

        int AddRowValues(object[] values)
        {
            while (Columns.Count < values.Length) Columns.Add("Column" + (Columns.Count + 1), "Column" + (Columns.Count + 1));
            var conv = values.Select((v, i) => Convert2(i, v)).ToArray();
            int idx = Rows.Add(conv);
            Rows[idx].Height = RowTemplate.Height;
            ApplyFilterTo(Rows[idx]);
            return idx;
        }

        static string[] Cells(string cells, string[] more)
        {
            var rest = more.Where(x => x != null).ToArray();
            if (rest.Length > 0) return new[] { cells ?? "" }.Concat(rest).ToArray();      // one argument per cell
            cells = cells ?? "";
            return cells.Split(cells.IndexOf('|') >= 0 ? '|' : ';').Select(s => s.Trim()).ToArray();
        }

        /// <summary>Adds a row "a|b|c" or "a;b;c" (or one argument per cell) and returns its index.</summary>
        public int AddRow(string cells, string c2 = null, string c3 = null, string c4 = null, string c5 = null, string c6 = null,
                          string c7 = null, string c8 = null, string c9 = null, string c10 = null)
        {
            int i = AddRowValues(Cells(cells, new[] { c2, c3, c4, c5, c6, c7, c8, c9, c10 }).Select(s => (object)s).ToArray());
            if (groupBy.Length > 0 && !grouping) Regroup();
            return DataIndex(i);
        }

        public void RemoveRow(int index) { var r = RowOf(index); if (r >= 0) { Rows.RemoveAt(r); Regroup(); } }
        public void ClearRows() { Rows.Clear(); }
        public void Clear() { Rows.Clear(); }

        /// <summary>Inserts a row before data row index.</summary>
        public int InsertRow(int index, string cells)
        {
            var vals = Cells(cells, new string[0]).Select((v, k) => Convert2(k, v)).ToArray();
            int at = RowOf(index);
            if (at < 0) return AddRow(cells);
            Rows.Insert(at, vals);
            Rows[at].Height = RowTemplate.Height;
            Regroup();
            return index;
        }

        public void SetFilter(string col, string text) { Filter(col, text); }
        public void ClearFilter() { foreach (var f in filters) f.Text = ""; }
        public void SetColumnWidth(string col, int width) { int c = ColOf(col); if (c >= 0 && c < Columns.Count) { Columns[c].AutoSizeMode = DataGridViewAutoSizeColumnMode.None; Columns[c].Width = (int)(width * DeviceDpi / 96f); } }
        public void BeginEdit(int row, string col) { int r = RowOf(row), c = ColOf(col); if (r >= 0 && c >= 0) { CurrentCell = this[c, r]; BeginEdit(true); } }
        public void EnsureVisible(int row) { int r = RowOf(row); if (r >= 0 && Rows[r].Visible) FirstDisplayedScrollingRowIndex = r; }

        [Category("Appearance"), DefaultValue(true)]
        public bool AlternatingRows { get { return alternating; } set { alternating = value; Recolor(); } }
        bool alternating = true;

        [Category("Appearance"), DefaultValue(28), Description("Row height in 96-DPI pixels.")]
        public int RowHeight { get { return rowHeight; } set { rowHeight = Math.Max(16, value); RowTemplate.Height = (int)(rowHeight * DeviceDpi / 96f); foreach (DataGridViewRow r in Rows) r.Height = RowTemplate.Height; } }
        int rowHeight = 28;

        /// <summary>A column header was clicked (ItemName = column name, Index = column).</summary>
        public event EventHandler<RmItemEventArgs> ColumnHeaderClick;

        int ColOf(string col)
        {
            int i;
            if (int.TryParse(col, NumberStyles.Integer, CultureInfo.InvariantCulture, out i)) return i;
            foreach (DataGridViewColumn c in Columns) if (string.Equals(c.Name, col, StringComparison.OrdinalIgnoreCase) || c.HeaderText == col) return c.Index;
            return -1;
        }

        bool IsGroupRow(DataGridViewRow r) { return r.Tag is string && ((string)r.Tag).StartsWith("\u0001group:"); }

        /// <summary>Data row index -> grid row index (group header rows are skipped).</summary>
        int RowOf(int dataIndex)
        {
            int k = -1;
            foreach (DataGridViewRow r in Rows) { if (IsGroupRow(r)) continue; k++; if (k == dataIndex) return r.Index; }
            return -1;
        }

        int DataIndex(int gridRow)
        {
            if (gridRow < 0 || gridRow >= Rows.Count) return -1;
            int k = -1;
            for (int i = 0; i <= gridRow; i++) if (!IsGroupRow(Rows[i])) k++;
            return IsGroupRow(Rows[gridRow]) ? -1 : k;
        }

        public string GetCell(int row, string col)
        {
            int r = RowOf(row), c = ColOf(col);
            if (r < 0 || c < 0 || c >= Columns.Count) return "";
            return RmScript.ToStr(this[c, r].Value);
        }

        public void SetCell(int row, string col, string value)
        {
            int r = RowOf(row), c = ColOf(col);
            if (r >= 0 && c >= 0 && c < Columns.Count) this[c, r].Value = Convert2(c, value);
        }

        /// <summary>The row as "a|b|c" (like the radforms grid).</summary>
        public string GetRow(int row)
        {
            int r = RowOf(row);
            if (r < 0) return "";
            return string.Join("|", Columns.Cast<DataGridViewColumn>().Select(c => RmScript.ToStr(this[c.Index, r].Value)).ToArray());
        }

        public void SortBy(string col, bool descending = false)
        {
            int c = ColOf(col);
            if (c < 0) return;
            if (groupBy.Length > 0) { Ungroup(); }
            Sort(Columns[c], descending ? ListSortDirection.Descending : ListSortDirection.Ascending);
            if (groupBy.Length > 0) Regroup();
        }

        // ---------------------------------------------------------------- filter row
        void BuildFilters()
        {
            foreach (var f in filters) f.Dispose();
            filters.Clear();
            filterBar.Visible = allowFilter && Columns.Count > 0;
            if (allowFilter)
                foreach (DataGridViewColumn c in Columns)
                {
                    var tb = new TextBox { BorderStyle = BorderStyle.FixedSingle, Tag = c.Index, Font = Font };
                    Native.SendMessage(tb.Handle, Native.EM_SETCUEBANNER, (IntPtr)1, "⌕ " + c.HeaderText);
                    tb.TextChanged += (s, a) => ApplyFilter();
                    filters.Add(tb);
                    filterBar.Controls.Add(tb);
                }
            ColumnHeadersHeight = (int)(32 * DeviceDpi / 96f) + (filterBar.Visible ? (int)(28 * DeviceDpi / 96f) : 0);
            Recolor();
            LayoutFilters();
        }

        void LayoutFilters()
        {
            if (!filterBar.Visible) return;
            int h = (int)(28 * DeviceDpi / 96f);
            filterBar.SetBounds(0, ColumnHeadersHeight - h, ClientSize.Width, h);
            foreach (var tb in filters)
            {
                int c = (int)tb.Tag;
                if (c >= Columns.Count) continue;
                var r = GetColumnDisplayRectangle(c, false);
                tb.Visible = r.Width > 0 && Columns[c].Visible;
                tb.SetBounds(r.X + 1, 2, Math.Max(0, r.Width - 3), h - 4);
            }
        }

        protected override void OnColumnWidthChanged(DataGridViewColumnEventArgs e) { base.OnColumnWidthChanged(e); LayoutFilters(); }
        protected override void OnScroll(ScrollEventArgs e) { base.OnScroll(e); LayoutFilters(); }
        protected override void OnResize(EventArgs e) { base.OnResize(e); LayoutFilters(); }

        /// <summary>Filters a column from code (contains, case-insensitive).</summary>
        public void Filter(string col, string text)
        {
            int c = ColOf(col);
            if (c < 0) return;
            if (!allowFilter) AllowFilter = true;
            var f = filters.FirstOrDefault(x => (int)x.Tag == c);
            if (f != null) f.Text = text ?? "";
        }

        void ApplyFilter()
        {
            CurrentCell = null;
            foreach (DataGridViewRow r in Rows) ApplyFilterTo(r);
        }

        void ApplyFilterTo(DataGridViewRow r)
        {
            if (IsGroupRow(r)) return;
            bool ok = true;
            foreach (var f in filters)
            {
                if (f.Text.Length == 0) continue;
                int c = (int)f.Tag;
                if (c >= Columns.Count) continue;
                var s = RmScript.ToStr(r.Cells[c].Value);
                if (s.IndexOf(f.Text, StringComparison.CurrentCultureIgnoreCase) < 0) { ok = false; break; }
            }
            if (ok && groupBy.Length > 0) { int g = ColOf(groupBy); if (g >= 0 && collapsedGroups.Contains(RmScript.ToStr(r.Cells[g].Value))) ok = false; }
            if (r.Visible != ok) { if (!ok && CurrentCell != null && CurrentCell.RowIndex == r.Index) CurrentCell = null; r.Visible = ok; }
        }

        // ---------------------------------------------------------------- grouping
        void Ungroup()
        {
            for (int i = Rows.Count - 1; i >= 0; i--) if (IsGroupRow(Rows[i])) Rows.RemoveAt(i);
        }

        void Regroup()
        {
            if (grouping) return;
            grouping = true;
            try
            {
                Ungroup();
                int g = ColOf(groupBy);
                if (groupBy.Length == 0 || g < 0) { foreach (DataGridViewRow r in Rows) ApplyFilterTo(r); return; }
                var rows = Rows.Cast<DataGridViewRow>().ToList();
                var ordered = rows.OrderBy(r => RmScript.ToStr(r.Cells[g].Value), StringComparer.CurrentCultureIgnoreCase).ToList();
                var values = ordered.Select(r => r.Cells.Cast<DataGridViewCell>().Select(c => c.Value).ToArray()).ToList();
                Rows.Clear();
                string last = null;
                for (int i = 0; i < values.Count; i++)
                {
                    var key = RmScript.ToStr(values[i][g]);
                    if (key != last)
                    {
                        int count = values.Count(v => RmScript.ToStr(v[g]) == key);
                        int gi = Rows.Add();
                        Rows[gi].Tag = "\u0001group:" + key;
                        Rows[gi].ReadOnly = true;
                        Rows[gi].Height = RowTemplate.Height;
                        Rows[gi].Cells[0].Value = key + "  (" + count.ToString(CultureInfo.InvariantCulture) + ")";
                        last = key;
                    }
                    int ri = Rows.Add(values[i]);
                    Rows[ri].Height = RowTemplate.Height;
                    ApplyFilterTo(Rows[ri]);
                }
            }
            finally { grouping = false; }
        }

        protected override void OnColumnHeaderMouseClick(DataGridViewCellMouseEventArgs e)
        {
            if (e.ColumnIndex >= 0) RmItemEventArgs.Raise(this, ColumnHeaderClick, new RmItemEventArgs(Columns[e.ColumnIndex].Name, e.ColumnIndex, Columns[e.ColumnIndex].HeaderText));
            if (groupBy.Length > 0 && allowSort && e.ColumnIndex >= 0) { SortBy(Columns[e.ColumnIndex].Name, SortOrder == SortOrder.Ascending && SortedColumn == Columns[e.ColumnIndex]); return; }
            base.OnColumnHeaderMouseClick(e);
        }

        protected override void OnCellMouseClick(DataGridViewCellMouseEventArgs e)
        {
            if (e.RowIndex >= 0 && e.RowIndex < Rows.Count && IsGroupRow(Rows[e.RowIndex]))
            {
                var key = ((string)Rows[e.RowIndex].Tag).Substring(7);
                if (!collapsedGroups.Remove(key)) collapsedGroups.Add(key);
                foreach (DataGridViewRow r in Rows) ApplyFilterTo(r);
                InvalidateRow(e.RowIndex);
                return;
            }
            base.OnCellMouseClick(e);
        }

        protected override void OnCellContentClick(DataGridViewCellEventArgs e)
        {
            base.OnCellContentClick(e);
            if (e.RowIndex >= 0 && e.ColumnIndex >= 0 && Columns[e.ColumnIndex] is DataGridViewButtonColumn && !IsGroupRow(Rows[e.RowIndex]))
            {
                RmItemEventArgs.Raise(this, ButtonCellClick, new RmItemEventArgs(Columns[e.ColumnIndex].Name, DataIndex(e.RowIndex), RmScript.ToStr(this[e.ColumnIndex, e.RowIndex].Value)));
            }
        }

        protected override void OnCurrentCellDirtyStateChanged(EventArgs e)
        {
            base.OnCurrentCellDirtyStateChanged(e);
            if (IsCurrentCellDirty && (CurrentCell is DataGridViewCheckBoxCell || CurrentCell is DataGridViewComboBoxCell)) CommitEdit(DataGridViewDataErrorContexts.Commit);
        }

        protected override void OnDataError(bool displayErrorDialogIfNoHandler, DataGridViewDataErrorEventArgs e) { e.ThrowException = false; }

        protected override void OnSortCompare(DataGridViewSortCompareEventArgs e)
        {
            var a = e.CellValue1; var b = e.CellValue2;
            if (a is IComparable && b != null && a.GetType() == b.GetType()) e.SortResult = ((IComparable)a).CompareTo(b);
            else e.SortResult = string.Compare(RmScript.ToStr(a), RmScript.ToStr(b), StringComparison.CurrentCultureIgnoreCase);
            e.Handled = true;
            base.OnSortCompare(e);
        }

        // ---------------------------------------------------------------- painting
        protected override void OnCellPainting(DataGridViewCellPaintingEventArgs e)
        {
            base.OnCellPainting(e);
            if (e.Handled) return;
            var t = Theme;
            var g = e.Graphics;
            bool rtl = RightToLeft == RightToLeft.Yes;
            float sc = DeviceDpi / 96f;
            if (e.RowIndex < 0)
            {
                if (e.ColumnIndex < 0) return;
                e.PaintBackground(e.ClipBounds, false);
                var hr = e.CellBounds;
                var text = Columns[e.ColumnIndex].HeaderText;
                int hh = (int)(32 * sc);
                var tr = new Rectangle(hr.X + (int)(8 * sc), hr.Y, hr.Width - (int)(24 * sc), hh);
                RmDraw.Text(g, text, ColumnHeadersDefaultCellStyle.Font, tr, ColumnHeadersDefaultCellStyle.ForeColor, ContentAlignment.MiddleLeft, rtl);
                if (SortedColumn != null && SortedColumn.Index == e.ColumnIndex)
                    RmDraw.Chevron(g, new Rectangle(rtl ? hr.X + 2 : hr.Right - (int)(20 * sc), hr.Y, (int)(18 * sc), hh), t.Accent, 1.4f * sc, SortOrder == SortOrder.Descending);
                using (var p = new Pen(RmDraw.Alpha(t.Border, 110))) g.DrawLine(p, hr.Right - 1, hr.Y + (int)(8 * sc), hr.Right - 1, hr.Y + hh - (int)(8 * sc));
                e.Handled = true;
                return;
            }
            var row = Rows[e.RowIndex];
            if (IsGroupRow(row))
            {
                var key = ((string)row.Tag).Substring(7);
                var back = RmDraw.Blend(DefaultCellStyle.BackColor, t.Accent, t.Dark ? 0.18 : 0.09);
                using (var b = new SolidBrush(back)) g.FillRectangle(b, e.CellBounds);
                if (e.ColumnIndex == FirstVisibleColumn())
                {
                    var rowRect = GetRowDisplayRectangle(e.RowIndex, false);
                    var st = g.Save();
                    g.SetClip(rowRect);
                    using (var b = new SolidBrush(back)) g.FillRectangle(b, rowRect);
                    bool open = !collapsedGroups.Contains(key);
                    var cr = new Rectangle(rtl ? rowRect.Right - (int)(24 * sc) : rowRect.X + (int)(4 * sc), rowRect.Y, (int)(20 * sc), rowRect.Height);
                    RmDraw.Chevron(g, cr, t.WindowText, 1.4f * sc, open, !open && !rtl, !open && rtl);
                    using (var bf = new Font(Font, FontStyle.Bold))
                        RmDraw.Text(g, RmScript.ToStr(row.Cells[0].Value), bf, new Rectangle(rowRect.X + (int)(28 * sc), rowRect.Y, rowRect.Width - (int)(36 * sc), rowRect.Height), t.WindowText, ContentAlignment.MiddleLeft, rtl);
                    g.Restore(st);
                }
                e.Handled = true;
                return;
            }
            if (e.ColumnIndex < 0) return;
            var kind = Columns[e.ColumnIndex].Tag as string;
            if (kind == "progress" || kind == "image" || kind == "check" || kind == "bool" || kind == "checkbox" || kind == "button")
            {
                e.PaintBackground(e.ClipBounds, (e.State & DataGridViewElementStates.Selected) != 0);
                var r = e.CellBounds;
                g.SmoothingMode = SmoothingMode.AntiAlias;
                if (kind == "progress")
                {
                    double v = 0;
                    if (e.Value is double) v = (double)e.Value; else double.TryParse(RmScript.ToStr(e.Value), NumberStyles.Float, CultureInfo.InvariantCulture, out v);
                    var br = new Rectangle(r.X + (int)(6 * sc), r.Y + r.Height / 2 - (int)(4 * sc), r.Width - (int)(46 * sc), (int)(8 * sc));
                    RmDraw.Box(g, br, RmDraw.Blend(t.Border, DefaultCellStyle.BackColor, 0.5), Color.Empty, 0, t.Radius == 0 ? 0 : 4 * sc);
                    int fw = (int)(br.Width * Math.Max(0, Math.Min(100, v)) / 100);
                    var col = v >= 80 ? Color.FromArgb(46, 125, 50) : v >= 40 ? t.Accent : Color.FromArgb(230, 140, 20);
                    if (fw > 0) RmDraw.Box(g, rtl ? new Rectangle(br.Right - fw, br.Y, fw, br.Height) : new Rectangle(br.X, br.Y, fw, br.Height), col, Color.Empty, 0, t.Radius == 0 ? 0 : 4 * sc);
                    RmDraw.Text(g, Math.Round(v).ToString(CultureInfo.InvariantCulture) + "%", Font, new Rectangle(br.Right + (int)(2 * sc), r.Y, (int)(40 * sc), r.Height), DefaultCellStyle.ForeColor, ContentAlignment.MiddleCenter);
                }
                else if (kind == "image")
                {
                    int s = Math.Min(r.Height - (int)(8 * sc), (int)(20 * sc));
                    RmImages.Draw(g, RmScript.ToStr(e.Value), e.Value as Image, new Rectangle(r.X + (r.Width - s) / 2, r.Y + (r.Height - s) / 2, s, s), t.Accent);
                }
                else if (kind == "button")
                {
                    var br = Rectangle.Inflate(r, -(int)(5 * sc), -(int)(4 * sc));
                    var text = Columns[e.ColumnIndex] is DataGridViewButtonColumn && ((DataGridViewButtonColumn)Columns[e.ColumnIndex]).UseColumnTextForButtonValue ? ((DataGridViewButtonColumn)Columns[e.ColumnIndex]).Text : RmScript.ToStr(e.Value);
                    RmDraw.Box(g, br, t.Accent, Color.Empty, 0, t.Radius * sc);
                    RmDraw.Text(g, text, Font, br, t.AccentText, ContentAlignment.MiddleCenter, rtl);
                }
                else
                {
                    bool on = e.Value is bool ? (bool)e.Value : RmItem.Bool(e.Value);
                    int b = (int)(16 * sc);
                    var box = new Rectangle(r.X + (r.Width - b) / 2, r.Y + (r.Height - b) / 2, b, b);
                    RmDraw.Box(g, box, on ? t.Accent : t.Input, on ? t.Accent : t.Border, 1, Math.Min(t.Radius * sc, b / 3f));
                    if (on) RmDraw.Check(g, box, t.AccentText, 1.8f * sc);
                }
                e.Handled = true;
            }
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    /// <summary>Themed tree with images, check boxes and lazy nodes (NodeExpanding fills them).</summary>
    [DefaultEvent("NodeClick")]
    public class RmTreeView : TreeView, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty;
        string nodesSpec = "";
        TreeNode hotNode;

        public event EventHandler<RmItemEventArgs> NodeClick;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;
        public event EventHandler<RmItemEventArgs> NodeExpanding;
        public event EventHandler<RmItemEventArgs> NodeChecked;
        public event EventHandler<RmItemEventArgs> NodeDoubleClick;
        public event EventHandler<RmItemEventArgs> NodeCollapsed;
        /// <summary>The selected node changed (EventItem = its name).</summary>
        public event EventHandler<RmItemEventArgs> SelectedIndexChanged;

        const string Lazy = "\u0001lazy";

        public RmTreeView()
        {
            DrawMode = TreeViewDrawMode.OwnerDrawAll;
            BorderStyle = BorderStyle.None;
            FullRowSelect = true;
            ShowLines = false;
            HotTracking = true;
            ItemHeight = 26;
            Font = new Font("Segoe UI", 9f);
            Size = new Size(200, 240);
            SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint, true);
            RmThemeManager.ThemeChanged += OnTheme;
            Recolor();
        }

        protected override void Dispose(bool disposing) { RmThemeManager.ThemeChanged -= OnTheme; base.Dispose(disposing); }

        void OnTheme(object s, EventArgs e) { Recolor(); Invalidate(); }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get { return style; } set { style = value; Recolor(); } }

        [Category("Appearance")]
        public Color AccentColor { get { return accent; } set { accent = value; Invalidate(); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        /// <summary>JSON [{Text, Name, Image, Checked, Expanded, Lazy, Nodes: [...]}] or "a;b;Group:c,d".</summary>
        [RmName("Nodes"), Category("Data"), DefaultValue("")]
        public string NodesJson
        {
            get { return nodesSpec; }
            set { nodesSpec = value ?? ""; BeginUpdate(); Nodes.Clear(); foreach (var it in RmItem.Parse(nodesSpec)) Nodes.Add(Make(it)); EndUpdate(); }
        }

        [RmName("SelectedNode"), Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string SelectedName { get { return SelectedNode != null ? SelectedNode.Name : ""; } set { var n = FindNode(value); if (n != null) SelectedNode = n; } }

        public void Clear() { Nodes.Clear(); }
        public new void ExpandAll() { base.ExpandAll(); }
        public new void CollapseAll() { base.CollapseAll(); }
        public void SetChecked(string name, bool value) { SetNodeChecked(name, value); }
        public bool GetChecked(string name) { return GetNodeChecked(name); }
        public void SelectNode(string name) { SelectedName = name; }
        public void SetNodeImage(string name, string image) { var n = FindNode(name); if (n != null) { n.Tag = image ?? ""; Invalidate(); } }

        protected override void OnAfterSelect(TreeViewEventArgs e)
        {
            base.OnAfterSelect(e);
            if (e.Node != null) RmItemEventArgs.Raise(this, SelectedIndexChanged, new RmItemEventArgs(e.Node.Name, e.Node.Index, e.Node.Text));
        }

        protected override void OnAfterCollapse(TreeViewEventArgs e)
        {
            base.OnAfterCollapse(e);
            RmItemEventArgs.Raise(this, NodeCollapsed, new RmItemEventArgs(e.Node.Name, e.Node.Index, e.Node.Text));
        }

        protected override void OnNodeMouseDoubleClick(TreeNodeMouseClickEventArgs e)
        {
            base.OnNodeMouseDoubleClick(e);
            RmItemEventArgs.Raise(this, NodeDoubleClick, new RmItemEventArgs(e.Node.Name, e.Node.Index, e.Node.Text));
        }

        public override string Text { get { return SelectedNode != null ? SelectedNode.Text : ""; } set { } }

        TreeNode Make(RmItem it)
        {
            var n = new TreeNode(it.Text) { Name = it.Key, Checked = it.Checked, Tag = it.Image };
            foreach (var k in it.Items) n.Nodes.Add(Make(k));
            if (RmItem.Bool(it.Extra.ContainsKey("Lazy") ? it.Extra["Lazy"] : false) && it.Items.Count == 0) n.Nodes.Add(new TreeNode("...") { Name = Lazy });
            if (it.Expanded) n.Expand();
            return n;
        }

        TreeNode FindNode(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            var found = Nodes.Find(name, true);
            if (found.Length > 0) return found[0];
            return All(Nodes).FirstOrDefault(n => n.Text == name);
        }

        static IEnumerable<TreeNode> All(TreeNodeCollection nodes) { foreach (TreeNode n in nodes) { yield return n; foreach (var k in All(n.Nodes)) yield return k; } }

        /// <summary>Adds a node under parent (empty = root); returns its name.</summary>
        public string AddNode(string parent, string text, string name = "", string image = "")
        {
            var n = new TreeNode(text) { Name = string.IsNullOrEmpty(name) ? text : name, Tag = image ?? "" };
            var p = FindNode(parent);
            if (p != null)
            {
                foreach (TreeNode k in p.Nodes.Cast<TreeNode>().Where(k => k.Name == Lazy).ToList()) p.Nodes.Remove(k);
                p.Nodes.Add(n);
            }
            else Nodes.Add(n);
            return n.Name;
        }

        public void RemoveNode(string name) { var n = FindNode(name); if (n != null) n.Remove(); }
        public void ClearNodes() { Nodes.Clear(); }
        public void ExpandNode(string name) { var n = FindNode(name); if (n != null) n.Expand(); }
        public void CollapseNode(string name) { var n = FindNode(name); if (n != null) n.Collapse(); }
        public void ExpandAllNodes() { ExpandAll(); }
        public void SetNodeChecked(string name, bool value) { var n = FindNode(name); if (n != null) n.Checked = value; }
        public bool GetNodeChecked(string name) { var n = FindNode(name); return n != null && n.Checked; }
        public void SetNodeText(string name, string text) { var n = FindNode(name); if (n != null) n.Text = text ?? ""; }
        /// <summary>Text of a node ("" when there is no such node).</summary>
        public string GetNodeText(string name) { var n = FindNode(name); return n != null ? n.Text : ""; }

        /// <summary>The checked nodes' names, ';' separated.</summary>
        public string CheckedNodes() { return string.Join(";", All(Nodes).Where(n => n.Checked && n.Name != Lazy).Select(n => n.Name).ToArray()); }

        void Recolor()
        {
            var t = Theme;
            BackColor = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.03) : (t.Name == "Light" ? Color.White : t.Input);
            ForeColor = t.InputText;
            RmNativeTheme.Apply(this, t.Dark);
        }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); ItemHeight = (int)(26 * DeviceDpi / 96f); Recolor(); }

        protected override void OnBeforeExpand(TreeViewCancelEventArgs e)
        {
            base.OnBeforeExpand(e);
            var a = new RmItemEventArgs(e.Node.Name, e.Node.Index, e.Node.Text);
            var h = NodeExpanding;
            RmItemEventArgs.Raise(this, h, a);
            if (a.Cancel) { e.Cancel = true; return; }
            // a lazy node that nobody filled: drop the placeholder
            if (e.Node.Nodes.Count == 1 && e.Node.Nodes[0].Name == Lazy && h == null) e.Node.Nodes.Clear();
        }

        protected override void OnAfterExpand(TreeViewEventArgs e)
        {
            base.OnAfterExpand(e);
            if (e.Node.Nodes.Count == 1 && e.Node.Nodes[0].Name == Lazy) BeginInvoke((Action)(() => { if (e.Node.Nodes.Count == 1 && e.Node.Nodes[0].Name == Lazy) e.Node.Nodes.Clear(); }));
        }

        protected override void OnAfterCheck(TreeViewEventArgs e)
        {
            base.OnAfterCheck(e);
            RmItemEventArgs.Raise(this, NodeChecked, new RmItemEventArgs(e.Node.Name, e.Node.Checked ? 1 : 0, e.Node.Text));
        }

        protected override void OnNodeMouseClick(TreeNodeMouseClickEventArgs e)
        {
            base.OnNodeMouseClick(e);
            if (e.Button != MouseButtons.Left) return;
            var b = e.Node.Bounds;
            float sc = DeviceDpi / 96f;
            int level = e.Node.Level, indentX = (int)(level * Indent + 4 * sc);
            var glyph = new Rectangle(indentX, b.Y, (int)(18 * sc), b.Height);
            if (RightToLeft == RightToLeft.Yes) glyph.X = ClientSize.Width - glyph.Right;
            if (e.Node.Nodes.Count > 0 && glyph.Contains(e.Location)) { e.Node.Toggle(); return; }
            if (CheckBoxes)
            {
                var cb = new Rectangle(indentX + (int)(20 * sc), b.Y, (int)(18 * sc), b.Height);
                if (RightToLeft == RightToLeft.Yes) cb.X = ClientSize.Width - cb.Right;
                if (cb.Contains(e.Location)) { e.Node.Checked = !e.Node.Checked; Invalidate(); return; }
            }
            SelectedNode = e.Node;
            RmItemEventArgs.Raise(this, NodeClick, new RmItemEventArgs(e.Node.Name, e.Node.Index, e.Node.Text));
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            var n = GetNodeAt(e.Location);
            if (n != hotNode) { var old = hotNode; hotNode = n; if (old != null) Invalidate(new Rectangle(0, old.Bounds.Y, Width, old.Bounds.Height)); if (n != null) Invalidate(new Rectangle(0, n.Bounds.Y, Width, n.Bounds.Height)); }
        }

        protected override void OnMouseLeave(EventArgs e) { base.OnMouseLeave(e); hotNode = null; Invalidate(); }

        protected override void OnDrawNode(DrawTreeNodeEventArgs e)
        {
            if (e.Bounds.Height <= 0) return;
            var t = Theme;
            var g = e.Graphics;
            float sc = DeviceDpi / 96f;
            bool rtl = RightToLeft == RightToLeft.Yes;
            var row = new Rectangle(0, e.Bounds.Y, ClientSize.Width, e.Bounds.Height);
            bool sel = (e.State & TreeNodeStates.Selected) != 0, hot = e.Node == hotNode;
            using (var b = new SolidBrush(BackColor)) g.FillRectangle(b, row);
            g.SmoothingMode = SmoothingMode.AntiAlias;
            var hl = Rectangle.Inflate(row, -(int)(3 * sc), -1);
            if (sel) RmDraw.Box(g, hl, RmDraw.Blend(BackColor, t.Selection, t.Dark ? 0.5 : 0.2), Color.Empty, 0, t.Radius * sc);
            else if (hot) RmDraw.Box(g, hl, t.Hot, Color.Empty, 0, t.Radius * sc);
            Func<Rectangle, Rectangle> Mr = r => rtl ? new Rectangle(ClientSize.Width - r.Right, r.Y, r.Width, r.Height) : r;
            int x = (int)(e.Node.Level * Indent + 4 * sc);
            if (ShowLines && e.Node.Level > 0)
                using (var p = new Pen(RmDraw.Alpha(t.Border, 140)) { DashStyle = DashStyle.Dot })
                {
                    var a = Mr(new Rectangle(x - Indent / 2, row.Y, Indent / 2, row.Height / 2));
                    g.DrawLine(p, a.X, row.Y, a.X, row.Y + row.Height / 2); g.DrawLine(p, a.X, row.Y + row.Height / 2, a.Right, row.Y + row.Height / 2);
                }
            if (e.Node.Nodes.Count > 0) RmDraw.Chevron(g, Mr(new Rectangle(x, row.Y, (int)(18 * sc), row.Height)), t.SubtleText, 1.4f * sc, e.Node.IsExpanded, !e.Node.IsExpanded && !rtl, !e.Node.IsExpanded && rtl);
            x += (int)(20 * sc);
            if (CheckBoxes)
            {
                int bsz = (int)(14 * sc);
                var box = Mr(new Rectangle(x + 2, row.Y + (row.Height - bsz) / 2, bsz, bsz));
                RmDraw.Box(g, box, e.Node.Checked ? t.Accent : t.Input, e.Node.Checked ? t.Accent : t.Border, 1, Math.Min(t.Radius * sc, 3 * sc));
                if (e.Node.Checked) RmDraw.Check(g, box, t.AccentText, 1.6f * sc);
                x += (int)(22 * sc);
            }
            var img = e.Node.Tag as string;
            if (!string.IsNullOrEmpty(img))
            {
                int s = (int)(16 * sc);
                RmImages.Draw(g, img, null, Mr(new Rectangle(x, row.Y + (row.Height - s) / 2, s, s)), t.Accent);
                x += s + (int)(6 * sc);
            }
            var tr = Mr(new Rectangle(x, row.Y, ClientSize.Width - x - (int)(4 * sc), row.Height));
            RmDraw.Text(g, e.Node.Text, e.Node.NodeFont ?? Font, tr, ForeColor, ContentAlignment.MiddleLeft, rtl);
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    public enum RmListViewKind { Details, Tiles, Cards, List }

    /// <summary>Modern list: details (columns), tiles or cards.</summary>
    [DefaultEvent("ItemClick")]
    public class RmListView : ListView, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty;
        string columnsSpec = "", itemsSpec = "";
        RmListViewKind kind = RmListViewKind.Details;
        int hot = -1;

        public event EventHandler<RmItemEventArgs> ItemClick;

        /// <summary>Name / index of the item of the last item event (also in the event args).</summary>
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string EventItem { get; set; } = "";
        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int EventIndex { get; set; } = -1;

        public RmListView()
        {
            OwnerDraw = true;
            FullRowSelect = true;
            BorderStyle = BorderStyle.None;
            HeaderStyle = ColumnHeaderStyle.Nonclickable;
            View = View.Details;
            MultiSelect = false;
            Font = new Font("Segoe UI", 9f);
            Size = new Size(320, 220);
            DoubleBuffered = true;
            SmallImageList = new ImageList { ImageSize = new Size(1, 26) };      // row height
            RmThemeManager.ThemeChanged += OnTheme;
            Recolor();
        }

        protected override void Dispose(bool disposing) { RmThemeManager.ThemeChanged -= OnTheme; base.Dispose(disposing); }

        void OnTheme(object s, EventArgs e) { Recolor(); Invalidate(); }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit)]
        public RmStyle Style { get { return style; } set { style = value; Recolor(); } }

        [Category("Appearance")]
        public Color AccentColor { get { return accent; } set { accent = value; Invalidate(); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        /// <summary>"Name;Size;Date" or JSON [{Text, Width}].</summary>
        [RmName("Columns"), Category("Data"), DefaultValue("")]
        public string ColumnsText
        {
            get { return columnsSpec; }
            set
            {
                columnsSpec = value ?? "";
                Columns.Clear();
                foreach (var c in RmItem.Parse(columnsSpec))
                {
                    int w; if (!int.TryParse(c.ExtraStr("Width"), out w)) w = 120;
                    Columns.Add(c.Key, c.Text, (int)(w * DeviceDpi / 96f));
                }
            }
        }

        /// <summary>Rows "a,b,c;d,e,f" or JSON [{Text, Image, SubItems: [..]}] / [["a","b"]].</summary>
        [RmName("Items"), Category("Data"), DefaultValue("")]
        public string ItemsText
        {
            get { return itemsSpec; }
            set
            {
                itemsSpec = value ?? "";
                BeginUpdate();
                Items.Clear();
                var s = itemsSpec.Trim();
                if (s.StartsWith("["))
                {
                    object v;
                    try { v = RmJson.Parse(s); } catch (Exception) { v = null; }
                    foreach (var o in (v as List<object>) ?? new List<object>())
                    {
                        var arr = o as List<object>;
                        if (arr != null) { AddRowValues(arr.Select(RmItem.Str).ToArray(), ""); continue; }
                        var it = RmItem.FromJson(o);
                        if (it == null) continue;
                        var sub = it.Extra.ContainsKey("SubItems") ? ((it.Extra["SubItems"] as List<object>) ?? new List<object>()).Select(RmItem.Str) : Enumerable.Empty<string>();
                        AddRowValues(new[] { it.Text }.Concat(sub).ToArray(), it.Image);
                    }
                }
                else foreach (var row in RmScript.Split(s)) AddRowValues(row.Split(',').Select(x => x.Trim()).ToArray(), "");
                EndUpdate();
            }
        }

        [RmName("View"), Category("Appearance"), DefaultValue(RmListViewKind.Details)]
        public RmListViewKind ViewKind
        {
            get { return kind; }
            set
            {
                kind = value;
                if (kind == RmListViewKind.Details) View = View.Details;
                else if (kind == RmListViewKind.List) View = View.List;
                else { View = View.Tile; TileSize = kind == RmListViewKind.Cards ? new Size((int)(220 * DeviceDpi / 96f), (int)(84 * DeviceDpi / 96f)) : new Size((int)(200 * DeviceDpi / 96f), (int)(52 * DeviceDpi / 96f)); }
                Invalidate();
            }
        }

        void AddRowValues(string[] cells, string image)
        {
            var it = new ListViewItem(cells.Length > 0 ? cells[0] : "") { Tag = image ?? "" };
            for (int i = 1; i < cells.Length; i++) it.SubItems.Add(cells[i]);
            Items.Add(it);
        }

        public int AddRow(string cells) { AddRowValues((cells ?? "").Split(';').Select(x => x.Trim()).ToArray(), ""); return Items.Count - 1; }
        public void AddListItem(string text, string image = "") { AddRowValues(new[] { text }, image); }
        /// <summary>Adds an item: "text", "a|b|c" (sub-items) and an optional image.</summary>
        public int AddItem(string text, string image = "") { AddRowValues((text ?? "").Split(text != null && text.IndexOf('|') >= 0 ? '|' : '\u0001'), image); return Items.Count - 1; }
        public void RemoveItem(int index) { RemoveAt(index); }
        public new void Clear() { Items.Clear(); }
        public string List(int index) { return GetItem(index, 0); }
        public void SetItemImage(int index, string image) { if (index >= 0 && index < Items.Count) { Items[index].Tag = image ?? ""; Invalidate(); } }

        int rowHeight = 26;

        [Category("Appearance"), DefaultValue(26), Description("Row height of the Details view in 96-DPI pixels.")]
        public int RowHeight { get { return rowHeight; } set { rowHeight = Math.Max(16, value); if (IsHandleCreated) SmallImageList.ImageSize = new Size(1, (int)(rowHeight * DeviceDpi / 96f)); } }
        public void RemoveAt(int index) { if (index >= 0 && index < Items.Count) Items.RemoveAt(index); }
        public void ClearItems() { Items.Clear(); }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int SelectedIndex
        {
            get { return SelectedIndices.Count > 0 ? SelectedIndices[0] : -1; }
            set { SelectedItems.Clear(); if (value >= 0 && value < Items.Count) { Items[value].Selected = true; Items[value].Focused = true; Items[value].EnsureVisible(); } }
        }

        [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int Count { get { return Items.Count; } }

        public string GetItem(int index, int column = 0)
        {
            if (index < 0 || index >= Items.Count) return "";
            var it = Items[index];
            return column < it.SubItems.Count ? it.SubItems[column].Text : "";
        }

        public override string Text { get { return SelectedIndex >= 0 ? Items[SelectedIndex].Text : ""; } set { } }

        void Recolor()
        {
            var t = Theme;
            BackColor = t.Dark ? RmDraw.Blend(t.Window, Color.White, 0.03) : (t.Name == "Light" ? Color.White : t.Input);
            ForeColor = t.InputText;
            RmNativeTheme.Apply(this, t.Dark);
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            SmallImageList.ImageSize = new Size(1, (int)(rowHeight * DeviceDpi / 96f));
            Recolor();
            FitColumns();
        }

        protected override void OnResize(EventArgs e) { base.OnResize(e); FitColumns(); }

        /// <summary>Details view: the last column takes the remaining width (no horizontal scroll bar).</summary>
        void FitColumns()
        {
            if (View != View.Details || Columns.Count == 0 || !IsHandleCreated) return;
            int used = 0;
            for (int i = 0; i < Columns.Count - 1; i++) used += Columns[i].Width;
            int rest = ClientSize.Width - used;
            if (rest > 40) Columns[Columns.Count - 1].Width = rest;
            else if (Columns.Count > 1 && ClientSize.Width > 80)
            {   // too narrow: shrink the first column
                Columns[0].Width = Math.Max(40, ClientSize.Width - used + Columns[0].Width - 60);
                Columns[Columns.Count - 1].Width = 60;
            }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            var it = GetItemAt(e.X, e.Y);
            int h = it != null ? it.Index : -1;
            if (h != hot) { hot = h; Invalidate(); }
        }

        protected override void OnMouseLeave(EventArgs e) { base.OnMouseLeave(e); hot = -1; Invalidate(); }

        protected override void OnMouseClick(MouseEventArgs e)
        {
            base.OnMouseClick(e);
            var it = GetItemAt(e.X, e.Y);
            if (it != null) RmItemEventArgs.Raise(this, ItemClick, new RmItemEventArgs(it.Text, it.Index, it.Text));
        }

        protected override void OnDrawColumnHeader(DrawListViewColumnHeaderEventArgs e)
        {
            var t = Theme;
            var back = t.Name == "Office" ? t.Accent : RmDraw.Blend(BackColor, t.Dark ? Color.White : Color.Black, 0.045);
            using (var b = new SolidBrush(back)) e.Graphics.FillRectangle(b, e.Bounds);
            using (var bf = new Font(Font, FontStyle.Bold))
                RmDraw.Text(e.Graphics, e.Header.Text, bf, Rectangle.Inflate(e.Bounds, -6, 0), t.Name == "Office" ? t.AccentText : t.WindowText, ContentAlignment.MiddleLeft, RightToLeft == RightToLeft.Yes);
            using (var p = new Pen(RmDraw.Alpha(t.Border, 110))) e.Graphics.DrawLine(p, e.Bounds.Right - 1, e.Bounds.Y + 6, e.Bounds.Right - 1, e.Bounds.Bottom - 6);
        }

        protected override void OnDrawItem(DrawListViewItemEventArgs e)
        {
            if (View == View.Details) { e.DrawDefault = false; return; }     // the sub-items draw the row
            var t = Theme;
            var g = e.Graphics;
            float sc = DeviceDpi / 96f;
            bool rtl = RightToLeft == RightToLeft.Yes;
            bool sel = e.Item.Selected, hv = e.ItemIndex == hot;
            var r = Rectangle.Inflate(e.Bounds, -(int)(3 * sc), -(int)(3 * sc));
            g.SmoothingMode = SmoothingMode.AntiAlias;
            if (kind == RmListViewKind.Cards)
            {
                RmDraw.Shadow(g, r, t.Radius * sc + 2, 3, t.Dark);
                RmDraw.Box(g, r, t.Surface, sel ? t.Accent : hv ? t.HotBorder : t.Border, sel ? 2 * sc : 1, (t.Radius + 3) * sc);
            }
            else if (sel || hv) RmDraw.Box(g, r, sel ? RmDraw.Blend(BackColor, t.Selection, t.Dark ? 0.5 : 0.2) : t.Hot, Color.Empty, 0, t.Radius * sc);
            int s = kind == RmListViewKind.Cards ? (int)(40 * sc) : (int)(28 * sc);
            var img = e.Item.Tag as string;
            int x = r.X + (int)(10 * sc);
            if (!string.IsNullOrEmpty(img))
            {
                var ir = new Rectangle(x, r.Y + (r.Height - s) / 2, s, s);
                if (rtl) ir.X = r.Right - (ir.X - r.X) - s;
                RmImages.Draw(g, img, null, ir, t.Accent);
                x += s + (int)(10 * sc);
            }
            int lines = Math.Max(1, e.Item.SubItems.Count);
            int lh = Font.Height + (int)(2 * sc);
            int y = r.Y + (r.Height - Math.Min(lines, kind == RmListViewKind.Cards ? 3 : 2) * lh) / 2;
            for (int i = 0; i < e.Item.SubItems.Count && i < (kind == RmListViewKind.Cards ? 3 : 2); i++)
            {
                var tr = new Rectangle(x, y, r.Right - x - (int)(8 * sc), lh);
                if (rtl) tr.X = r.Right - (tr.X - r.X) - tr.Width;
                using (var f = i == 0 ? new Font(Font, FontStyle.Bold) : null)
                    RmDraw.Text(g, e.Item.SubItems[i].Text, f ?? Font, tr, i == 0 ? t.InputText : t.SubtleText, ContentAlignment.MiddleLeft, rtl);
                y += lh;
            }
        }

        protected override void OnDrawSubItem(DrawListViewSubItemEventArgs e)
        {
            var t = Theme;
            var g = e.Graphics;
            float sc = DeviceDpi / 96f;
            bool sel = e.Item.Selected, hv = e.ItemIndex == hot;
            var back = sel ? RmDraw.Blend(BackColor, t.Selection, t.Dark ? 0.5 : 0.2) : hv ? t.Hot : (e.ItemIndex % 2 == 1 ? RmDraw.Blend(BackColor, t.Dark ? Color.White : t.Accent, 0.035) : BackColor);
            using (var b = new SolidBrush(back)) g.FillRectangle(b, e.Bounds);
            var r = Rectangle.Inflate(e.Bounds, -(int)(6 * sc), 0);
            if (e.ColumnIndex == 0)
            {
                var img = e.Item.Tag as string;
                if (!string.IsNullOrEmpty(img))
                {
                    int s = (int)(16 * sc);
                    RmImages.Draw(g, img, null, new Rectangle(r.X, r.Y + (r.Height - s) / 2, s, s), t.Accent);
                    r.X += s + (int)(6 * sc); r.Width -= s + (int)(6 * sc);
                }
            }
            RmDraw.Text(g, e.SubItem.Text, Font, r, t.InputText, ContentAlignment.MiddleLeft, RightToLeft == RightToLeft.Yes);
        }

        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }
}
