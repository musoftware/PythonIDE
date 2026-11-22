# RmGauge

Circular dial or linear gauge with coloured ranges.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmGauge1, RmGauge2 ...

**Default size:** 150 x 140 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Value | float | 0 | Current value. |
| Minimum | float | 0 | Lowest value. |
| Maximum | float | 100 | Highest value. |
| Ranges | str | (see the designer) | Coloured ranges from-to:#colour;... |
| Unit | str | "" | Unit after the value (km/h, %, °C). |
| Title | str | "" | Caption under the value. |
| Kind | enum | "Circular" | Circular dial or Linear scale. (Circular, Linear) |
| Decimals | int | 0 | Decimals of the value. |
| ShowTicks | bool | true | Draws ticks. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Example (C, GUI Bridge API)

```c
rad_set("RmGauge1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmGauge1.Style = "Office"
```

## بالعربية

عداد دائري أو خطي بنطاقات ملونة.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.


See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
