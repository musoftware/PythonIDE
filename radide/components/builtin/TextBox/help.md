# TextBox

Lets the user enter text.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** TextBox1, TextBox2 ...

**Default size:** 100 x 20 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Multiline | bool | false | Allow several lines of text. |
| ReadOnly | bool | false |  |
| PasswordChar | str | "" | Character shown instead of the text (e.g. *). |
| MaxLength | int | 0 | Maximum characters (0 = no limit). |
| DataSource | dbref | "" | The data source (Data Sources window) the control is bound to. |
| DataMember | dbref | "" | The bound column (Column or Source.Column); ListBox / ComboBox: the Source.Column that receives the selected item's ValueMember. |

## Events

Double-clicking the control in the designer writes the handler of **TextChanged**.

- **TextChanged** - The Text property value changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `VB.TextBox`.
Imported from: `msmask.maskedbox`, `richtextlib.richtextbox`, `VB.TextBox` (`msmask.maskedbox` approximated).

See docs/COMPONENTS.md for how component packages work.
