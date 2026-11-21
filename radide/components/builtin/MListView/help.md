# MListView

A scrolling list of tiles; e.Index tells which row was tapped.

**Kind:** visual control. **Toolbox:** Mobile. **New name:** ListView1, ListView2 ...

**Default size:** 360 x 240 dp.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Items | list | Item 1&#124;First item;Item 2&#124;Second item;Item 3&#124;Third item | Rows separated by ; with fields separated by &#124; (matching ItemTemplate). |
| ItemTemplate | str | title&#124;subtitle | Fields of a row: title, subtitle, icon, trailing - separated by &#124; (e.g. icon&#124;title&#124;subtitle). |

## Events

Double-clicking the control in the designer writes the handler of **Tap**.

- **Tap** - The user tapped the control (MListView / Drawer: e.Index = the item).

See docs/COMPONENTS.md for how component packages work.
