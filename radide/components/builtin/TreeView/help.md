# TreeView

A hierarchy of nodes.

**Kind:** visual control. **Toolbox:** Common Controls. **New name:** TreeView1, TreeView2 ...

**Default size:** 121 x 97 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Nodes | list | "" | Nodes separated by ; - use / for children (Root;Root/Child;Root/Child2). |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - The selected item changes.
- **DoubleClick** - Occurs when the control is double-clicked.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `MSComctlLib.TreeView`.
Imported from: `comctllib.treeview`, `MSComctlLib.TreeView`.

See docs/COMPONENTS.md for how component packages work.
