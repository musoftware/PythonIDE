# RmTile

Metro tile: title, count, image, colour.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmTile1, RmTile2 ...

**Default size:** 150 x 150 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Title | str | "Tile" | Caption at the bottom. |
| Count | str | "" | Big number / text at the top right. |
| Image | str | "" | Glyph name or image. |
| TileColor | color | "" | Background (empty = accent). |
| Size | enum | "Medium" | Small 70, Medium 150, Wide 310x150, Large 310 (pixels). (Small, Medium, Wide, Large) |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |

## Events

Double-clicking the control in the designer writes the handler of **Click**.

- **Click** - The tile was clicked.

## Example (C, GUI Bridge API)

```c
rad_set("RmTile1", "Style", "Dark");   /* any property: rad_set / rad_get */
```

## Example (VB / BASIC)

```vb
RmTile1.Style = "Office"
```

## بالعربية

بلاطة Metro: عنوان وعدد وصورة ولون.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: Click.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
