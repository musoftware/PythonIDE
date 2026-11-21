# BottomNav

Bottom navigation bar to switch between the main screens.

**Kind:** visual control. **Toolbox:** Mobile. **New name:** BottomNav1, BottomNav2 ...

**Default size:** 360 x 80 dp.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Items | list | Home;Search;Profile | Destinations separated by ; |
| SelectedIndex | int | 0 | Selected destination (0 = first). |

## Events

Double-clicking the control in the designer writes the handler of **Changed**.

- **Changed** - The value changed (Switch, Slider, TextField, BottomNav / TabBar index).

See docs/COMPONENTS.md for how component packages work.
