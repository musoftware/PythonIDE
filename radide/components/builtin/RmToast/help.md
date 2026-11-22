# RmToast

Notification that slides in at a screen corner (Info / Success / Warning / Error).

**Kind:** component (no window). **Toolbox:** Modern (RAD). **New name:** RmToast1, RmToast2 ...

Shown in the component tray under the form.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

| Property | Type | Default | Description |
|---|---|---|---|
| Position | enum | "BottomRight" | Screen corner. (BottomRight, TopRight, BottomLeft, TopLeft, BottomCenter, TopCenter) |
| Duration | int | 3000 | Milliseconds shown (0 = until clicked). |
| ToastWidth | int | 340 | Width in pixels. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - A toast was clicked (EventItem = its title).

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `Show(title, text, kind, ms)` - Shows a toast; kind Info, Success, Warning or Error.
- `CloseAll()` - Closes the toasts.

## Example (C, GUI Bridge API)

```c
rad_call("RmToast1", "Show", "Saved\tThe file was saved.\tSuccess\t3000");
```

## Example (VB / BASIC)

```vb
RmToast1.Show "Saved", "The file was saved.", "Success", 3000
```

## بالعربية

إشعار يظهر في زاوية الشاشة (معلومة / نجاح / تحذير / خطأ).

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: Click.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
