# RmButton

Modern button: default / accent / outline / flat / link, image + text, split drop-down.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmButton1, RmButton2 ...

**Default size:** 110 x 32 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "Button" | Caption. |
| Kind | enum | "Default" | Look of the button. (Default, Accent, Outline, Flat, Link) |
| Image | str | "" | Image file or a built-in glyph name (save, open, mail, settings ...). |
| ImagePosition | enum | "Left" | Where the image goes. (Left, Top, Right) |
| CornerRadius | int | -1 | Corner radius in pixels (-1 = the theme's). |
| DropDownItems | list | "" | Items of the split drop-down: a;b;c or JSON [{Text, Name}]. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - The button was clicked (or Space / Enter).
- **DropDownItemClicked** - An item of the drop-down was picked (EventItem = its Name).

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `PerformClick()` - Raises Click.
- `ShowDropDown()` - Opens the drop-down.

## Example (C, GUI Bridge API)

```c
void RmButton1_Click(void) { rad_set("lblOut", "Text", "clicked"); }
```

## Example (VB / BASIC)

```vb
Private Sub RmButton1_Click()
    lblOut.Caption = "clicked"
End Sub
```

## بالعربية

زر حديث: عادي / مميز / محدد / مسطح / رابط، صورة ونص، وقائمة منسدلة.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: Click، DropDownItemClicked.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
