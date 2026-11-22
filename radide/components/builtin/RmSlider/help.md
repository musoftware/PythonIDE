# RmSlider

Track bar with a value tip.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmSlider1, RmSlider2 ...

**Default size:** 200 x 44 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Value | int | 0 | Current value. |
| Minimum | int | 0 | Lowest value. |
| Maximum | int | 100 | Highest value. |
| TickFrequency | int | 0 | Tick every n (0 = none). |
| SmallChange | int | 1 | Arrow keys / wheel step. |
| LargeChange | int | 10 | Page Up / Down step. |
| ShowValue | bool | false | Always show the value above the thumb. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **ValueChanged**.

- **ValueChanged** - Value changed.

## Example (C, GUI Bridge API)

```c
rad_set("RmSlider1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmSlider1.Style = "Office"
```

## بالعربية

شريط تمرير مع تلميح للقيمة.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: ValueChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
