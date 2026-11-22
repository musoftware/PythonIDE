# RmGroupPanel

Collapsible group with a header (container).

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmGroupPanel1, RmGroupPanel2 ...

**Default size:** 240 x 140 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | "Group" | Header text. |
| Collapsed | bool | false | Only the header is shown. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **CollapsedChanged**.

- **CollapsedChanged** - Collapsed changed.

## Methods

- `Toggle()` - Collapses / expands.
- `Expand()` - Shows the content.
- `Collapse()` - Hides the content.

## Example (C, GUI Bridge API)

```c
rad_set("RmGroupPanel1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmGroupPanel1.Style = "Office"
```

## بالعربية

مجموعة قابلة للطي برأس (حاوية).

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: CollapsedChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
