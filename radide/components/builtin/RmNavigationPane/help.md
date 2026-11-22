# RmNavigationPane

Navigation pane with page buttons and a header (container, Outlook style).

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmNavigationPane1, RmNavigationPane2 ...

**Default size:** 200 x 300 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Pages | list | "Mail;Calendar;Contacts" | Pages: a;b;c or JSON [{Text, Image}]. |
| SelectedIndex | int | 0 | Page shown. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - Another page was selected.

## Example (C, GUI Bridge API)

```c
rad_set("RmNavigationPane1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmNavigationPane1.Style = "Office"
```

## بالعربية

لوحة تنقل بأزرار صفحات ورأس (حاوية، بأسلوب Outlook).

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: SelectedIndexChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
