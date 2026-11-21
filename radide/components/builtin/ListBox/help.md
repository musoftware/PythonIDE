# ListBox

A list of items to choose from.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** ListBox1, ListBox2 ...

**Default size:** 120 x 95 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Items | list | "" | Items separated by ; |
| DataSource | dbref | "" | The data source (Data Sources window) the control is bound to. |
| DisplayMember | dbref | "" | The column whose values the list shows. |
| ValueMember | dbref | "" | The column that is the value of an item (usually the key). |
| DataMember | dbref | "" | The bound column (Column or Source.Column); ListBox / ComboBox: the Source.Column that receives the selected item's ValueMember. |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - The selected item changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `VB.ListBox`.
Imported from: `msdatalistlib.datalist`, `msdblib.dblist`, `vb.dirlistbox`, `vb.filelistbox`, `VB.ListBox` (`msdatalistlib.datalist`, `msdblib.dblist`, `vb.dirlistbox`, `vb.filelistbox` approximated).

See docs/COMPONENTS.md for how component packages work.
