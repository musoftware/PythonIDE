# RmGrid

Advanced grid: typed columns, sorting, filter row, grouping, frozen columns, editing, alternating rows.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmGrid1, RmGrid2 ...

**Default size:** 360 x 200 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Columns | multiline | "Name;Age:Number:60;Active:Check:60" | Columns: Name;Age:Number:60 (header:type:width) or JSON [{Text, Type, Width, Frozen, ReadOnly, Items}]; types Text, Number, Check, Combo, Date, Image, Progress, Button. |
| Rows | multiline | "Mona|31|True;Ali|25|False" | Rows separated by ; with cells separated by |, or JSON [[...]]. |
| ReadOnly | bool | false | No editing. |
| AllowSort | bool | true | Click a header to sort. |
| AllowFilter | bool | false | Filter row under the header. |
| GroupBy | str | "" | Column name whose values group the rows (empty = no groups). |
| SelectionMode | enum | "FullRowSelect" | Selection. (FullRowSelect, CellSelect, MultiRow) |
| AlternatingRows | bool | true | Every other row tinted. |
| RowHeight | int | 28 | Row height in pixels. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **CellClick**.

- **CellClick** - A cell was clicked (EventRow / EventColumn).
- **CellDoubleClick** - A cell was double-clicked.
- **CellValueChanged** - The user changed a cell (EventRow / EventColumn).
- **SelectionChanged** - The selection changed.
- **ButtonCellClick** - A Button cell was clicked (EventRow / EventColumn).
- **ColumnHeaderClick** - A header was clicked.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `AddRow("a;b;c")` - Adds a row (cells separated by ; or |); returns its index.
- `InsertRow(index, cells)` - Inserts a row.
- `RemoveRow(index)` - Removes a row.
- `Clear()` - Removes every row.
- `GetCell(row, column)` - Value of a cell (column = index or name).
- `SetCell(row, column, value)` - Changes a cell.
- `GetRow(row)` - Cells of a row separated by |.
- `SortBy(column, descending)` - Sorts.
- `SetFilter(column, text)` - Filters a column.
- `ClearFilter()` - Removes the filters.
- `SetColumnWidth(column, width)` - Column width.
- `BeginEdit(row, column)` - Edits a cell.
- `EnsureVisible(row)` - Scrolls to a row.

## Example (C, GUI Bridge API)

```c
rad_call("RmGrid1", "AddRow", "Sara;28;True");
void RmGrid1_CellClick(void) { int row = (int)rad_num(rad_arg(0)); }
```

## Example (VB / BASIC)

```vb
RmGrid1.AddRow "Sara;28;True"
Private Sub RmGrid1_CellClick()
    MsgBox RmGrid1.GetCell(RmGrid1.EventRow, 0)
End Sub
```

## بالعربية

جدول متقدم: أعمدة بأنواع، ترتيب، صف تصفية، تجميع، أعمدة مثبتة، تحرير، صفوف متناوبة.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: CellClick، CellDoubleClick، CellValueChanged، SelectionChanged، ButtonCellClick، ColumnHeaderClick.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
