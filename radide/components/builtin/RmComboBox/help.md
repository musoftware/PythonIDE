# RmComboBox

Themed combo box with item images and watermark.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmComboBox1, RmComboBox2 ...

**Default size:** 180 x 30 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Text | str | "" | Caption. |
| Items | list | "Item 1;Item 2;Item 3" | Items: a;b;c or JSON [{Text, Image}]. |
| SelectedIndex | int | -1 | Index of the selected item (-1 = none). |
| Watermark | str | "" | Hint shown while nothing is selected. |
| DropDownStyle | enum | "DropDownList" | DropDown = the user can also type. (DropDownList, DropDown) |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - Another item was selected.
- **TextChanged** - The text changed.

## Methods

- `AddItem(text)` - Adds an item; returns its index.
- `RemoveItem(index)` - Removes an item.
- `Clear()` - Removes every item.
- `List(index)` - Text of an item.
- `IndexOf(text)` - Index of an item (-1 = none).
- `ShowDropDown()` - Opens the list.

## Example (C, GUI Bridge API)

```c
rad_set("RmComboBox1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmComboBox1.Style = "Office"
```

## بالعربية

قائمة منسدلة بمظهر حديث مع صور للعناصر ونص إرشادي.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: SelectedIndexChanged، TextChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
