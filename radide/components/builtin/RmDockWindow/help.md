# RmDockWindow

A dockable tool window (container) inside an RmDockPanel.

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmDockWindow1, RmDockWindow2 ...

**Default size:** 200 x 200 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | "Window" | Caption of the title bar. |
| DockSide | enum | "Left" | Where it docks. (Left, Right, Top, Bottom, Fill, Float) |
| AutoHide | bool | false | Collapsed to a side tab that slides out. |
| DockSize | int | 0 | Docked width / height (0 = the designer size). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Example (C, GUI Bridge API)

```c
rad_set("RmDockWindow1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmDockWindow1.Style = "Office"
```

## بالعربية

نافذة أدوات قابلة للإرساء (حاوية) داخل RmDockPanel.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.


See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
