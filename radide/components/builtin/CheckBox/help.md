# CheckBox

An on/off option.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** CheckBox1, CheckBox2 ...

**Default size:** 90 x 20 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Checked | bool | false |  |
| DataSource | dbref | "" | The data source (Data Sources window) the control is bound to. |
| DataMember | dbref | "" | The bound column (Column or Source.Column); ListBox / ComboBox: the Source.Column that receives the selected item's ValueMember. |

## Events

Double-clicking the control in the designer writes the handler of **CheckedChanged**.

- **CheckedChanged** - The Checked property value changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `VB.CheckBox`.
Imported from: `VB.CheckBox`.

See docs/COMPONENTS.md for how component packages work.
