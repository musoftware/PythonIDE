# RmSuperTooltip

Rich tooltips (title, image, text, footer) attached to controls.

**Kind:** component (no window). **Toolbox:** Modern (RAD). **New name:** RmSuperTooltip1, RmSuperTooltip2 ...

Shown in the component tray under the form.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

| Property | Type | Default | Description |
|---|---|---|---|
| Delay | int | 500 | Milliseconds before the tip shows. |
| MaxWidth | int | 320 | Width limit. |
| Duration | int | 8000 | Milliseconds shown (0 = until the mouse leaves). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Methods

- `SetToolTip(control, title, text, footer, image)` - Attaches a tip to a control (by name).
- `Show(control)` - Shows the control's tip now.
- `Hide()` - Hides the tip.
- `RemoveToolTip(control)` - Removes a control's tip.

## Example (C, GUI Bridge API)

```c
rad_set("RmSuperTooltip1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmSuperTooltip1.Style = "Office"
```

## بالعربية

تلميحات غنية (عنوان وصورة ونص وتذييل) تُربط بالعناصر.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.


See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
