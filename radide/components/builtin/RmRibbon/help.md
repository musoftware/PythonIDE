# RmRibbon

Ribbon: application button, quick access toolbar, tabs, groups, large / small buttons, toggles, combos, drop-downs.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmRibbon1, RmRibbon2 ...

**Default size:** 600 x 154 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Tabs | multiline | (see the designer) | JSON tabs [{Text, Groups:[{Text, Items:[{Text, Name, Image, Size: Large|Small, Kind: Button|Check|Combo|DropDown, Items}]}]}]. |
| QuickAccess | list | "save;undo;redo" | Quick access buttons: item names or glyphs (a;b;c). |
| AppMenu | multiline | "" | Items of the application button's menu (JSON / a;b;c; empty = ItemClick AppButton). |
| AppButtonText | str | "File" | Caption of the application button (empty = none). |
| SelectedTab | int | 0 | Index of the tab shown. |
| Collapsed | bool | false | Only the tab row is shown. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **ItemClick**.

- **ItemClick** - A ribbon item was clicked (EventItem = its Name, EventIndex).
- **TabChanged** - Another tab was selected.
- **CollapsedChanged** - Collapsed changed.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `SetChecked(name, checked)` - Checks a Check item.
- `GetChecked(name)` - Is it checked?
- `SetEnabled(name, enabled)` - Enables / disables an item.
- `SetItemText(name, text)` - Changes an item's caption.
- `SetValue(name, text)` - Text of a Combo item.
- `GetValue(name)` - Text of a Combo item.
- `SelectTab(name)` - Shows a tab.
- `Toggle()` - Collapses / expands.

## Example (C, GUI Bridge API)

```c
void RmRibbon1_ItemClick(void) {
    const char *item = rad_arg(0);     /* or rad_get("RmRibbon1", "EventItem") */
}
```

## Example (VB / BASIC)

```vb
Private Sub RmRibbon1_ItemClick()
    Select Case RmRibbon1.EventItem
    Case "btnPaste": Paste
    End Select
End Sub
```

## بالعربية

شريط Ribbon: زر التطبيق وشريط الوصول السريع وتبويبات ومجموعات وأزرار كبيرة وصغيرة وأزرار تبديل وقوائم.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: ItemClick، TabChanged، CollapsedChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
