# RmTimePicker

Time box with hour / minute / second segments.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmTimePicker1, RmTimePicker2 ...

**Default size:** 120 x 30 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Value | str | "12:00:00" | The time HH:mm:ss (empty = now). |
| Format | str | "HH:mm" | HH:mm, HH:mm:ss or hh:mm tt (12 hours). |
| ShowSeconds | bool | false | Shows the seconds. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **ValueChanged**.

- **ValueChanged** - The time changed.

## Example (C, GUI Bridge API)

```c
rad_set("RmTimePicker1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmTimePicker1.Style = "Office"
```

## بالعربية

مربع وقت بأجزاء الساعة والدقيقة والثانية.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: ValueChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
