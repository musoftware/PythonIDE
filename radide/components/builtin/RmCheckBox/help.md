# RmCheckBox

Themed check box with an indeterminate state.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmCheckBox1, RmCheckBox2 ...

**Default size:** 150 x 24 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "CheckBox" | Caption. |
| Checked | bool | false | Checked or not. |
| Indeterminate | bool | false | Shows the third (mixed) state. |
| CheckAlign | enum | "Left" | Side of the box. (Left, Right) |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **CheckedChanged**.

- **CheckedChanged** - Checked / Indeterminate changed.
- **Click** - The box was clicked.

## Methods

- `Toggle()` - Switches Checked.

## Example (C, GUI Bridge API)

```c
rad_set("RmCheckBox1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmCheckBox1.Style = "Office"
```

## بالعربية

مربع اختيار بمظهر حديث مع حالة غير محددة.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: CheckedChanged، Click.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
