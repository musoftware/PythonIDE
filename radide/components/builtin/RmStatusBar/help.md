# RmStatusBar

Modern status bar with panels: text, progress, zoom; spring panels fill the rest.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmStatusBar1, RmStatusBar2 ...

**Default size:** 400 x 26 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "" | Caption. |
| Panels | multiline | (see the designer) | JSON [{Text, Name, Width (0 = spring), Kind: Text|Progress|Zoom, Value, Image}] or a;b;c. |
| AccentBar | bool | false | Accent-coloured bar. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **PanelClick**.

- **PanelClick** - A panel was clicked (EventItem / EventIndex).
- **ValueChanged** - The zoom changed.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `SetPanelText(panel, text)` - Text of a panel (name or index).
- `GetPanelText(panel)` - Text of a panel.
- `SetPanelValue(panel, value)` - Value of a progress / zoom panel.
- `GetPanelValue(panel)` - Value of a panel.

## Example (C, GUI Bridge API)

```c
rad_set("RmStatusBar1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmStatusBar1.Style = "Office"
```

## بالعربية

شريط حالة حديث بلوحات: نص وتقدم وتكبير؛ اللوحات المرنة تملأ الباقي.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: PanelClick، ValueChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
