# RmTreeView

Themed tree with images, check boxes and lazy nodes.

**Kind:** visual control. **Toolbox:** Modern (RAD). **New name:** RmTreeView1, RmTreeView2 ...

**Default size:** 220 x 260 pixels.

Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.

## Properties

Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):

| Property | Type | Default | Description |
|---|---|---|---|
| Nodes | multiline | (see the designer) | JSON [{Text, Name, Image, Expanded, Checked, Lazy, Nodes:[...]}] or a;b;c. |
| CheckBoxes | bool | false | Check boxes on the nodes. |
| ShowLines | bool | true | Connecting lines. |
| SelectedNode | str | "" | Name of the selected node. |
| Style | enum | "Inherit" | Theme of this control: Inherit = the form's / application's Theme. (Inherit, Light, Dark, Office, Metro) |
| AccentColor | color | "" | Accent colour (empty = the theme's accent). |
| EventItem | str | "" | Name of the item of the last item event (ItemClick, NodeClick ...). |
| EventIndex | int | -1 | Index of the item of the last item event. |

## Events

Double-clicking the control in the designer writes the handler of **NodeClick**.

- **NodeClick** - A node was clicked (EventItem = its Name).
- **NodeDoubleClick** - A node was double-clicked.
- **NodeExpanding** - A node opens (lazy nodes: add the children with AddNode here).
- **NodeCollapsed** - A node closed.
- **NodeChecked** - A node's check box changed.
- **SelectedIndexChanged** - Another node was selected.

Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same values (item name and index; grid: row and column).

## Methods

- `AddNode(parent, text, name, image)` - Adds a node (parent "" = root); returns its name.
- `RemoveNode(name)` - Removes a node.
- `Clear()` - Removes every node.
- `ExpandNode(name)` - Opens a node.
- `CollapseNode(name)` - Closes a node.
- `ExpandAll()` - Opens every node.
- `CollapseAll()` - Closes every node.
- `SetChecked(name, checked)` - Checks a node and its children.
- `GetChecked(name)` - Is it checked?
- `SelectNode(name)` - Selects a node.
- `GetNodeText(name)` - Text of a node.
- `SetNodeText(name, text)` - Changes a node's text.
- `SetNodeImage(name, image)` - Changes a node's image.

## Example (C, GUI Bridge API)

```c
void RmTreeView1_NodeExpanding(void) {
    rad_call("RmTreeView1", "AddNode", "\tChild\tc1\tfile"); /* parent name in rad_arg(0) */
}
```

## Example (VB / BASIC)

```vb
RmTreeView1.Style = "Office"
```

## بالعربية

شجرة بمظهر حديث مع صور ومربعات اختيار وعقد تُحمّل عند الطلب.

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
- الأحداث: NodeClick، NodeDoubleClick، NodeExpanding، NodeCollapsed، NodeChecked، SelectedIndexChanged.

See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md ("Modern controls (Rm*)") for the C ABI.
