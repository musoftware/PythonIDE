# DataGridView

A grid of editable cells.

**Kind:** visual control. **Toolbox:** Data. **New name:** DataGridView1, DataGridView2 ...

**Default size:** 240 x 150 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Columns | list | Column1;Column2 | Column headers separated by ; |
| Rows | list | "" | Rows separated by ; with cells separated by &#124; (a&#124;b;c&#124;d). |
| ReadOnly | bool | false | Prevent editing the cells. |
| DataSource | dbref | "" | The data source (Data Sources window) the control is bound to. |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - The selected item changes.
- **CellChanged** - The user changed the value of a cell.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `MSFlexGridLib.MSFlexGrid`.
Imported from: `msdatagridlib.datagrid`, `msdbgrid.dbgrid`, `MSFlexGridLib.MSFlexGrid`, `mshierarchicalflexgridlib.mshflexgrid` (`msdatagridlib.datagrid`, `msdbgrid.dbgrid` approximated).

See docs/COMPONENTS.md for how component packages work.
