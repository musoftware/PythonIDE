# RmDockPanel

Docking host: RmDockWindow children dock left / right / top / bottom / fill, tab, float and auto-hide.

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmDockPanel1, RmDockPanel2 ...

**Default size:** 500 x 320 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Layout | multiline | "" | Saved layout (JSON from SaveLayout) applied at start. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **ActiveWindowChanged**.

- **WindowClosed** - A window was closed (EventItem = its name).
- **ActiveWindowChanged** - Another window became active.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `SaveLayout()` - The layout as JSON.
- `LoadLayout(json)` - Applies a layout.
- `ShowWindow(name)` - Shows a closed window.
- `CloseWindow(name)` - Closes a window.
- `DockWindow(name, side)` - Docks a window (Left, Right, Top, Bottom, Fill, Float).
- `Refresh()` - Lays the windows out again.

## Example (C, GUI Bridge API)

```c
rad_set("RmDockPanel1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmDockPanel1.Style = "Office"
```

## بالعربية

مضيف إرساء: نوافذ RmDockWindow ترسو يساراً / يميناً / أعلى / أسفل / ملء، وتتبوّب وتطفو وتختفي تلقائياً.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: WindowClosed، ActiveWindowChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
