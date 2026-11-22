# RmTextBox

Text box with watermark, clear button, icon, validation border, password and multi-line modes.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmTextBox1, RmTextBox2 ...

**Default size:** 200 x 30 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "" | The text. |
| Watermark | str | "" | Grey hint shown while the box is empty. |
| Icon | str | "" | Glyph name or image at the left (search, user, mail ...). |
| ShowClear | bool | false | Shows an x that clears the text. |
| PasswordChar | str | "" | Character shown instead of the text (e.g. *). |
| MultiLine | bool | false | Several lines. |
| ReadOnly | bool | false | The user cannot change the text. |
| ErrorText | str | "" | Not empty = red border and error icon (validation). |
| MaxLength | int | 0 | Maximum characters (0 = no limit). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **TextChanged**.

- **TextChanged** - The text changed.
- **KeyPress** - A character was typed (e.KeyChar).
- **IconClick** - The icon was clicked.

## Methods

- `Clear()` - Empties the text.
- `SelectAll()` - Selects all the text.
- `AppendText(text)` - Adds text at the end.
- `Focus()` - Moves the focus to the box.

## Example (C, GUI Bridge API)

```c
rad_set("RmTextBox1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmTextBox1.Style = "Office"
```

## بالعربية

مربع نص بنص إرشادي وزر مسح وأيقونة وإطار تحقق ووضع كلمة مرور ومتعدد الأسطر.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: TextChanged، KeyPress، IconClick.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
