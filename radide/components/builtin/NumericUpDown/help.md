# NumericUpDown

A number with up/down arrows.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** NumericUpDown1, NumericUpDown2 ...

**Default size:** 120 x 20 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Minimum | int | 0 |  |
| Maximum | int | 100 |  |
| Value | int | 0 |  |

## Events

Double-clicking the control in the designer writes the handler of **ValueChanged**.

- **ValueChanged** - The Value property changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `MSComCtl2.UpDown`.
Imported from: `comct2lib.updown`, `MSComCtl2.UpDown`.

See docs/COMPONENTS.md for how component packages work.
