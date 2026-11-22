# RmPanel

Rounded / shadowed / gradient card that holds controls, optional title bar.

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmPanel1, RmPanel2 ...

**Default size:** 240 x 160 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | "" | Title bar text (empty = none). |
| CornerRadius | int | -1 | Corner radius (-1 = the theme's). |
| Shadow | bool | false | Drop shadow. |
| GradientTo | color | "" | Second colour of a vertical gradient (empty = none). |
| BorderColor | color | "" | Border colour (empty = the theme's). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Example (C, GUI Bridge API)

```c
rad_set("RmPanel1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmPanel1.Style = "Office"
```

## بالعربية

بطاقة بحواف مستديرة وظل وتدرج تحتوي عناصر، مع شريط عنوان اختياري.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.


See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
