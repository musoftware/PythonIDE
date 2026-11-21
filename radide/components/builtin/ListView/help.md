# ListView

A list of items with columns.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** ListView1, ListView2 ...

**Default size:** 200 x 97 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Columns | list | Column1;Column2 | Column headers separated by ; |
| Items | list | "" | Rows separated by ; with cells separated by &#124; (a&#124;b;c&#124;d). |
| View | enum | Details | Details shows columns with headers. Values: Details, List. |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - The selected item changes.
- **DoubleClick** - Occurs when the control is double-clicked.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `MSComctlLib.ListView`.
Imported from: `comctllib.listview`, `MSComctlLib.ListView`.

See docs/COMPONENTS.md for how component packages work.
