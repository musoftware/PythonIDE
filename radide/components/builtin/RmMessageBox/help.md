# RmMessageBox

Themed message box / task dialog: Show returns the pressed button.

**Kind:** component (no window). **Toolbox:** Modern (RAD). **New name:** RmMessageBox1, RmMessageBox2 ...

Shown in the component tray under the form.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

| Property | Type | Default | Description |
|---|---|---|---|
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Methods

- `Show(text, title, buttons, icon, heading)` - Shows the box; buttons OK, OKCancel, YesNo, YesNoCancel, RetryCancel, AbortRetryIgnore or "Save;Don't Save;Cancel"; icon Info, Success, Warning, Error, Question; returns the button's text.

## Example (C, GUI Bridge API)

```c
const char *r = rad_call("RmMessageBox1", "Show", "Save the changes?\tApp\tYesNoCancel\tQuestion");
```

## Example (VB / BASIC)

```vb
If RmMessageBox1.Show("Save the changes?", "App", "YesNo", "Question") = "Yes" Then Save
```

## بالعربية

صندوق رسالة / حوار مهام بالمظهر الحديث: Show تعيد الزر المضغوط.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.


See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
