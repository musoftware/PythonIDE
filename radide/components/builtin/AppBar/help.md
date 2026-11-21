# AppBar

Material top app bar with a title and action buttons.

**Kind:** visual control. **Toolbox:** Mobile. **New name:** AppBar1, AppBar2 ...

**Default size:** 360 x 56 dp.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | Title | Text shown in the bar. |
| Actions | list | search;more_vert | Action buttons separated by ; - a Material icon name (search, share ...) or a word. Each raises <AppBar>_Click with e.Action. |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - Occurs when the control is clicked.

See docs/COMPONENTS.md for how component packages work.
