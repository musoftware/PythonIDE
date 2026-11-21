# ReportViewer

Shows a report (.rpt.json): pages, zoom, print, export to PDF / HTML / CSV / Excel. Code: Parameters["X"] = 1, SetData(rows), Refresh(), Print().

**Kind:** visual control. **Toolbox:** Reporting. **New name:** ReportViewer1, ReportViewer2 ...

**Default size:** 400 x 300 pixels.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| ReportFile | file | "" | The report to show (a .rpt.json file of the project). |
| Zoom | int | 100 | Zoom in percent. |
| ShowToolbar | bool | true | Show the page / zoom / print / export bar. |
| AutoLoad | bool | true | Run the report when the form opens (False: call Refresh()). |

## Events

Double-clicking the control in the designer writes the handler of **PageChanged**.

- **PageChanged** - The report viewer shows another page.
- the common mouse, keyboard and focus events (Click, MouseDown, KeyDown, GotFocus ...).

See docs/COMPONENTS.md for how component packages work.
