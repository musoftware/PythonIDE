# ActiveX

Hosts a Windows ActiveX (COM) control.

**Kind:** visual control. **Toolbox:** Components. **New name:** ActiveX1, ActiveX2 ...

**Default size:** 100 x 50 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| ProgID | str | Shell.Explorer.2 | COM ProgID of the ActiveX control (e.g. Shell.Explorer.2, MSCAL.Calendar). |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - Occurs when the control is clicked.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

See docs/COMPONENTS.md for how component packages work.
