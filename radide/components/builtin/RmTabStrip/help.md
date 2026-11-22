# RmTabStrip

Modern tabs (top / left / bottom, closable, overflow arrows); children live on the pages (TabPage).

**Kind:** container (holds other controls). **Toolbox:** Modern (RAD). **New name:** RmTabStrip1, RmTabStrip2 ...

**Default size:** 320 x 200 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| TabPages | list | "Page 1;Page 2" | Tabs: a;b;c or JSON [{Text, Name, Image}]. |
| SelectedIndex | int | 0 | Page shown (click a tab in the designer to edit it). |
| TabPosition | enum | "Top" | Where the tabs are. (Top, Left, Bottom) |
| Closable | bool | false | Tabs have a close button (TabClosing). |
| AutoClose | bool | true | The close button removes the tab (False = only TabClosing). |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **SelectedIndexChanged**.

- **SelectedIndexChanged** - Another tab was selected.
- **TabClosing** - A tab's close button was pressed (EventItem / EventIndex).

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `AddTab(text)` - Adds a tab; returns its index.
- `RemoveTab(index)` - Removes a tab.
- `TabCaption(index, text)` - Gets / sets the caption of a tab.
- `SelectTab(name)` - Shows a tab.

## Example (C, GUI Bridge API)

```c
rad_set("RmTabStrip1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmTabStrip1.Style = "Office"
```

## بالعربية

تبويبات حديثة (أعلى / يسار / أسفل، قابلة للإغلاق، أسهم عند الزحام)؛ العناصر توضع على الصفحات.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: SelectedIndexChanged، TabClosing.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
