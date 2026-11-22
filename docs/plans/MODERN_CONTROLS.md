# Modern controls suite (RAD Modern) - shared specification

A DevComponents / DotNetBar-like set of modern desktop controls, **our own design** (no copied look, assets
or names of commercial suites), available in every desktop project of RAD IDE:

| Implementation | Used by | Where |
|---|---|---|
| native C modules on radforms (`rf_register_class`, owner-drawn, themes) | C, C++, Fortran, VB6 (FreeBASIC), and later Go / Rust / Lua / JS / Ruby through the C ABI | `radide/runtimes/native/radforms/controls/rm_*.c` |
| managed .NET WinForms library `RadIDE.Controls` (C#, own source in the repo) | C#, VB.NET, PowerShell native builds (merged into the single-file exe) | `radide/runtimes/dotnet/RadIDE.Controls/` |
| component packages (Toolbox, Properties, design-time drawing, Python/Tk preview fallback) | the form designer of every desktop language | `radide/components/builtin/Rm*/` |

Both implementations follow this document: same control type names, property names, value types, defaults,
event names and argument fields, so one `.form` behaves the same whatever language the project uses.

## Common to every control
- Type names start with `Rm` (RAD Modern). Common props of visual controls (Left, Top, Width, Height, Anchor,
  Dock, Visible, Enabled, TabIndex, ToolTip, FontName, FontSize, FontBold, FontItalic, BackColor, ForeColor) as
  in radide/controls.py COMMON_PROPS.
- `Style` (string): `Inherit` (default - the form's / application theme), `Light`, `Dark`, `Office`, `Metro`.
  Form-level `Theme` property picks the theme for the form (radforms already has Light / Dark / Office /
  Metro). `AccentColor` (colour, "" = theme accent).
- Hover / press animations (theme `anim_ms`), focus cues, keyboard access, DPI-aware metrics, RTL mirroring
  when the form's `RightToLeft` is on (Arabic).
- List-like props are strings separated by `;` (as elsewhere in the IDE); nested items (ribbon, menus, nav
  items, tree nodes) are JSON arrays of objects `{Text, Name, Image, Items, ...}` like MenuStrip Items.
- Events use the IDE's neutral event names (Click, DoubleClick, SelectedIndexChanged, ValueChanged, TextChanged,
  ...); item-level events add `ItemName` / `Index` in the event args.

## Controls (v1)
| Type | What it is | Key props | Events |
|---|---|---|---|
| RmButton | modern button (flat / rounded / accent / outline), image + text, split drop-down | Text, Image, ImagePosition (Left/Top/Right), Kind (Default/Accent/Outline/Flat/Link), CornerRadius, DropDownItems | Click, DropDownItemClicked |
| RmToggle | on/off switch | Checked, OnText, OffText | CheckedChanged |
| RmTextBox | text box with watermark, clear button, icon, validation border | Text, Watermark, Icon, ShowClear, PasswordChar, MultiLine, ReadOnly, ErrorText | TextChanged, KeyPress, IconClick |
| RmComboBox | themed combo with images and watermark | Items, SelectedIndex, Watermark, DropDownStyle | SelectedIndexChanged, TextChanged |
| RmCheckBox / RmRadioButton | themed check / radio | Text, Checked (RmCheckBox also Indeterminate) | CheckedChanged |
| RmProgress | linear / circular / marquee progress | Value, Minimum, Maximum, Kind (Bar/Circle/Marquee), ShowText | - |
| RmSlider | track bar with value tip | Value, Minimum, Maximum, TickFrequency | ValueChanged |
| RmGauge | circular / linear gauge with ranges | Value, Minimum, Maximum, Ranges ("0-60:#2E7D32;60-80:#F9A825;80-100:#C62828"), Unit | - |
| RmPanel | rounded / shadowed / gradient panel, optional title bar (container) | Title, CornerRadius, Shadow, GradientTo, BorderColor | - |
| RmGroupPanel | collapsible group with header (container) | Title, Collapsed | CollapsedChanged |
| RmTabStrip | modern tabs (top / left / bottom, closable, overflow) with pages (container) | TabPages, SelectedIndex, TabPosition, Closable | SelectedIndexChanged, TabClosing |
| RmSideBar | vertical side bar with groups and items (Outlook / VS Code style) | Items (groups + items with images), SelectedItem, Collapsed | ItemClick, CollapsedChanged |
| RmNavigationPane | navigation pane with header buttons and pages (container) | Pages, SelectedIndex | SelectedIndexChanged |
| RmRibbon | ribbon: application button, tabs, groups, large/small buttons, combo, check items, quick access toolbar, collapse | Tabs (JSON), QuickAccess, Collapsed, AppButtonText | ItemClick (ItemName), TabChanged |
| RmStatusBar | modern status bar with panels (text, progress, zoom) | Panels | PanelClick |
| RmGrid | advanced grid: columns with types (Text, Number, Check, Combo, Date, Image, Progress, Button), sorting, filtering row, grouping by column, frozen columns, editing, alternating rows, selection modes | Columns (JSON), Rows, ReadOnly, AllowSort, AllowFilter, GroupBy, SelectionMode | CellClick, CellValueChanged, SelectionChanged, ButtonCellClick |
| RmTreeView | themed tree with images, check boxes, lazy nodes | Nodes (JSON), CheckBoxes, ShowLines | NodeClick, NodeExpanding, NodeChecked |
| RmListView | modern list (details / tiles / cards) | Columns, Items, View | ItemClick, ItemActivate |
| RmDatePicker / RmTimePicker / RmCalendar | modern date / time pickers and month calendar | Value, Format, MinDate, MaxDate | ValueChanged |
| RmTile | Metro tile (title, count, image, colour), tile panel container | Title, Count, Image, TileColor, Size (Small/Medium/Wide/Large) | Click |
| RmDockPanel | docking host: tool windows that dock / tab / float / auto-hide inside the form (container of RmDockWindow) | Layout (JSON) | WindowClosed, ActiveWindowChanged |
| RmDockWindow | a dockable window (container) | Title, DockSide, AutoHide | - |
| RmToast | notification (non-visual): `Show(title, text, kind, ms)` bottom-right, kinds Info/Success/Warning/Error | Position, Duration | Click |
| RmBalloonTip / RmSuperTooltip | rich tooltips with title, image, footer (non-visual, attaches to controls) | - | - |
| RmMessageBox | themed message box / task dialog (non-visual) | - | - |

Methods called from code use the IDE's control-method mechanism (e.g. `RmToast1.Show("Saved", "Done",
"Success", 3000)`, `RmGrid1.AddRow("a;b;c")`, `RmRibbon1.SetChecked("btnBold", True)`), documented per control
in its package `help.md`.

## Design time
Each control is a component package under `radide/components/builtin/Rm<Name>/` (component.json with the
props / events / methods of this table, designer drawing that looks like the runtime, help.md in English +
Arabic, a Python/Tk runtime fallback so `Run` inside the IDE works for languages without a native preview).
Toolbox category: "Modern (RAD)".

## Builds
- Native builders (`win32_c.py`, `vb6_freebasic.py`) link only the rm modules a project uses; the exe stays
  one standalone file.
- .NET builder (`dotnet_winforms.py`) maps `Rm*` types through `radide/deploy/native/dotnet/controls.json`
  (or a `RadIDE.Controls.controls.json` next to it) to `RadIDE.Controls.*` and references the library project
  (ProjectReference, merged into the single file).
- A project that uses an `Rm*` control without an implementation for its language falls back to the bridge
  build with the reason in the Output (never a wrong form).
