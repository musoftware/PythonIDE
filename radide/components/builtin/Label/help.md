# Label

Displays read-only text.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** Label1, Label2 ...

**Default size:** 60 x 17 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| TextAlign | enum | Left | Values: Left, Center, Right. |
| DataSource | dbref | "" | The data source (Data Sources window) the control is bound to. |
| DataMember | dbref | "" | The bound column (Column or Source.Column); ListBox / ComboBox: the Source.Column that receives the selected item's ValueMember. |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - Occurs when the control is clicked.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `VB.Label`.
Imported from: `comctllib.statusbar`, `msadodclib.adodc`, `MSComctlLib.StatusBar`, `vb.data`, `VB.Label` (`msadodclib.adodc`, `MSComctlLib.StatusBar`, `vb.data` approximated).

See docs/COMPONENTS.md for how component packages work.
