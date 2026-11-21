# SaveFileDialog

Asks the user where to save a file: ShowDialog() returns "OK" or "Cancel".

**Kind:** component (shown in the component tray below the form, not on it). **Toolbox:** Dialogs. **New name:** SaveFileDialog1, SaveFileDialog2 ...

## Properties

Besides Name:

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | Save As |  |
| Filter | str | All files&#124;*.* | Pairs of description&#124;pattern, e.g. Text files&#124;*.txt&#124;All&#124;*.* |
| FileName | str | "" | The chosen file (after ShowDialog). |
| InitialDirectory | str | "" |  |

## VB6

Written to a VB6 .frm as `MSComDlg.CommonDialog`.

See docs/COMPONENTS.md for how component packages work.
