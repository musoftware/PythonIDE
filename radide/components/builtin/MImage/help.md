# MImage

Shows a picture.

**Kind:** visual control. **Toolbox:** Mobile. **New name:** Image1, Image2 ...

**Default size:** 160 x 120 dp.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Image | file | "" | Image file (asset) - .png / .jpg. |
| Fit | enum | Cover | How the picture fills the box. Values: Cover, Contain, Fill, FitWidth, FitHeight, None. |

## Events

Double-clicking the control in the designer writes the handler of **Tap**.

- **Tap** - The user tapped the control (MListView / Drawer: e.Index = the item).

See docs/COMPONENTS.md for how component packages work.
