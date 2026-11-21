# TabControl

Pages of controls selected with tabs. Click a tab in the designer to edit it.

**Kind:** container (hosts other controls). **Toolbox:** Containers. **New name:** TabControl1, TabControl2 ...

**Default size:** 200 x 100 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| TabPages | list | TabPage1;TabPage2 | Page captions separated by ; |
| SelectedIndex | int | 0 | Index of the page shown (0 = first). |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - The selected item changes.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

## VB6

Written to a VB6 .frm as `TabDlg.SSTab`.
Imported from: `comctllib.tabstrip`, `mscomctllib.tabstrip`, `TabDlg.SSTab` (`comctllib.tabstrip`, `mscomctllib.tabstrip` approximated).

See docs/COMPONENTS.md for how component packages work.
