# DateTimePicker

Lets the user pick a date or a time.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** DateTimePicker1, DateTimePicker2 ...

**Default size:** 200 x 20 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Value | str | "" | Date as YYYY-MM-DD (time as HH:MM:SS); empty = today. |
| Format | enum | Short | Short = 2024-01-31, Long = Wednesday, 31 January 2024, Time = 13:45:00. Values: Short, Long, Time. |

## Events

Double-clicking the control in the designer writes the handler of **ValueChanged**.

- **ValueChanged** - The Value property changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `MSComCtl2.DTPicker`.
Imported from: `comct2lib.dtpicker`, `msacal.calendar`, `MSComCtl2.DTPicker`, `mscomctl2.monthview` (`msacal.calendar`, `mscomctl2.monthview` approximated).

See docs/COMPONENTS.md for how component packages work.
