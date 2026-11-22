# RmToggle

On / off switch with animated knob.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmToggle1, RmToggle2 ...

**Default size:** 150 x 26 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "Toggle" | Caption next to the switch. |
| Checked | bool | false | On / off. |
| OnText | str | "" | Caption while on (empty = Text). |
| OffText | str | "" | Caption while off (empty = Text). |
| CheckAlign | enum | "Left" | Side of the switch. (Left, Right) |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **CheckedChanged**.

- **CheckedChanged** - Checked changed.
- **Click** - The switch was clicked.

## Methods

- `Toggle()` - Switches Checked.

## Example (C, GUI Bridge API)

```c
void RmToggle1_CheckedChanged(void) { rad_set("lblOut", "Text", rad_get("RmToggle1", "Checked")); }
```

## Example (VB / BASIC)

```vb
RmToggle1.Style = "Office"
```

## بالعربية

مفتاح تشغيل / إيقاف بمقبض متحرك.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: CheckedChanged، Click.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
