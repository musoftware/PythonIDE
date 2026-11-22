# RmListView

Modern list: Details (columns), Tiles and Cards views with images.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmListView1, RmListView2 ...

**Default size:** 300 x 200 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Columns | list | "Name;Size;Modified" | Column headers a;b;c (Cards show them as labels). |
| Items | multiline | (see the designer) | JSON [{Text, Image, SubItems:[...]}] or rows a|b;c|d. |
| View | enum | "Details" | How items are shown. (Details, Tiles, Cards) |
| SelectedIndex | int | -1 | Selected item (-1 = none). |
| RowHeight | int | 0 | Row / tile height (0 = automatic). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **ItemClick**.

- **ItemClick** - An item was clicked (EventItem = its text, EventIndex).
- **ItemActivate** - Double-click / Enter on an item.
- **SelectedIndexChanged** - The selection changed.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `AddItem("text;sub1;sub2")` - Adds an item.
- `RemoveItem(index)` - Removes an item.
- `Clear()` - Removes every item.
- `List(index)` - Text of an item.
- `SetItemImage(index, image)` - Image of an item.

## Example (C, GUI Bridge API)

```c
rad_set("RmListView1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmListView1.Style = "Office"
```

## بالعربية

قائمة حديثة: تفاصيل (أعمدة) وبلاطات وبطاقات مع صور.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: ItemClick، ItemActivate، SelectedIndexChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
