"""Writes the RAD Modern (Rm*) component packages: radide/components/builtin/Rm*/ (component.json, designer.py,
runtime/rmtk_<Name>.py, help.md in English + Arabic) from the table below (docs/plans/MODERN_CONTROLS.md).

    .venv\\Scripts\\python tools/gen_rm_packages.py

Run it again after changing the table; the packages are regenerated (hand edits there are overwritten).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILTIN = ROOT / "radide" / "components" / "builtin"
CATEGORY = "Modern (RAD)"
STYLES = ["Inherit", "Light", "Dark", "Office", "Metro"]

LOOK = [("Style", "enum", "Inherit", "Appearance", "Theme of this control: Inherit = the form's / application's Theme.", STYLES),
        ("AccentColor", "color", "", "Appearance", "Accent colour (empty = the theme's accent).")]
EVENT_ITEM = [("EventItem", "str", "", "Data", "Name of the item of the last item event (ItemClick, NodeClick ...).",
               None, {"browsable": False, "designOnly": False}),
              ("EventIndex", "int", -1, "Data", "Index of the item of the last item event.", None, {"browsable": False})]

# name: dict(desc, ar, kind, size, text, props, events, methods, order, help, help_ar, default_event)
SPEC: dict[str, dict] = {
    "RmButton": dict(
        desc="Modern button: default / accent / outline / flat / link, image + text, split drop-down.",
        ar="زر حديث: عادي / مميز / محدد / مسطح / رابط، صورة ونص، وقائمة منسدلة.",
        size=(110, 32), text=True, default_event="Click",
        props=[("Text", "str", "Button", "Appearance", "Caption."),
               ("Kind", "enum", "Default", "Appearance", "Look of the button.", ["Default", "Accent", "Outline", "Flat", "Link"]),
               ("Image", "str", "", "Appearance", "Image file or a built-in glyph name (save, open, mail, settings ...)."),
               ("ImagePosition", "enum", "Left", "Appearance", "Where the image goes.", ["Left", "Top", "Right"]),
               ("CornerRadius", "int", -1, "Appearance", "Corner radius in pixels (-1 = the theme's)."),
               ("DropDownItems", "list", "", "Behavior", "Items of the split drop-down: a;b;c or JSON [{Text, Name}].")],
        events=[("Click", "The button was clicked (or Space / Enter)."),
                ("DropDownItemClicked", "An item of the drop-down was picked (EventItem = its Name).")],
        methods=[("PerformClick", "PerformClick()", "Raises Click."), ("ShowDropDown", "ShowDropDown()", "Opens the drop-down.")]),
    "RmToggle": dict(
        desc="On / off switch with animated knob.", ar="مفتاح تشغيل / إيقاف بمقبض متحرك.",
        size=(150, 26), text=True, default_event="CheckedChanged",
        props=[("Text", "str", "Toggle", "Appearance", "Caption next to the switch."),
               ("Checked", "bool", False, "Behavior", "On / off."),
               ("OnText", "str", "", "Appearance", "Caption while on (empty = Text)."),
               ("OffText", "str", "", "Appearance", "Caption while off (empty = Text)."),
               ("CheckAlign", "enum", "Left", "Appearance", "Side of the switch.", ["Left", "Right"])],
        events=[("CheckedChanged", "Checked changed."), ("Click", "The switch was clicked.")],
        methods=[("Toggle", "Toggle()", "Switches Checked.")]),
    "RmCheckBox": dict(
        desc="Themed check box with an indeterminate state.", ar="مربع اختيار بمظهر حديث مع حالة غير محددة.",
        size=(150, 24), text=True, default_event="CheckedChanged",
        props=[("Text", "str", "CheckBox", "Appearance", "Caption."),
               ("Checked", "bool", False, "Behavior", "Checked or not."),
               ("Indeterminate", "bool", False, "Behavior", "Shows the third (mixed) state."),
               ("CheckAlign", "enum", "Left", "Appearance", "Side of the box.", ["Left", "Right"])],
        events=[("CheckedChanged", "Checked / Indeterminate changed."), ("Click", "The box was clicked.")],
        methods=[("Toggle", "Toggle()", "Switches Checked.")]),
    "RmRadioButton": dict(
        desc="Themed radio button (one checked per container).", ar="زر اختيار واحد بمظهر حديث (واحد فقط في الحاوية).",
        size=(150, 24), text=True, default_event="CheckedChanged",
        props=[("Text", "str", "Option", "Appearance", "Caption."),
               ("Checked", "bool", False, "Behavior", "Checked (the others of the same container are cleared)."),
               ("CheckAlign", "enum", "Left", "Appearance", "Side of the circle.", ["Left", "Right"])],
        events=[("CheckedChanged", "Checked changed."), ("Click", "The button was clicked.")],
        methods=[]),
    "RmTextBox": dict(
        desc="Text box with watermark, clear button, icon, validation border, password and multi-line modes.",
        ar="مربع نص بنص إرشادي وزر مسح وأيقونة وإطار تحقق ووضع كلمة مرور ومتعدد الأسطر.",
        size=(200, 30), text=True, default_event="TextChanged",
        props=[("Text", "str", "", "Appearance", "The text."),
               ("Watermark", "str", "", "Appearance", "Grey hint shown while the box is empty."),
               ("Icon", "str", "", "Appearance", "Glyph name or image at the left (search, user, mail ...)."),
               ("ShowClear", "bool", False, "Behavior", "Shows an x that clears the text."),
               ("PasswordChar", "str", "", "Behavior", "Character shown instead of the text (e.g. *)."),
               ("MultiLine", "bool", False, "Behavior", "Several lines."),
               ("ReadOnly", "bool", False, "Behavior", "The user cannot change the text."),
               ("ErrorText", "str", "", "Behavior", "Not empty = red border and error icon (validation)."),
               ("MaxLength", "int", 0, "Behavior", "Maximum characters (0 = no limit).")],
        events=[("TextChanged", "The text changed."), ("KeyPress", "A character was typed (e.KeyChar).", "key"),
                ("IconClick", "The icon was clicked.")],
        methods=[("Clear", "Clear()", "Empties the text."), ("SelectAll", "SelectAll()", "Selects all the text."),
                 ("AppendText", "AppendText(text)", "Adds text at the end."), ("Focus", "Focus()", "Moves the focus to the box.")]),
    "RmComboBox": dict(
        desc="Themed combo box with item images and watermark.", ar="قائمة منسدلة بمظهر حديث مع صور للعناصر ونص إرشادي.",
        size=(180, 30), text=True, default_event="SelectedIndexChanged",
        props=[("Items", "list", "Item 1;Item 2;Item 3", "Data", "Items: a;b;c or JSON [{Text, Image}]."),
               ("SelectedIndex", "int", -1, "Behavior", "Index of the selected item (-1 = none)."),
               ("Watermark", "str", "", "Appearance", "Hint shown while nothing is selected."),
               ("DropDownStyle", "enum", "DropDownList", "Behavior", "DropDown = the user can also type.", ["DropDownList", "DropDown"])],
        events=[("SelectedIndexChanged", "Another item was selected."), ("TextChanged", "The text changed.")],
        methods=[("AddItem", "AddItem(text)", "Adds an item; returns its index."), ("RemoveItem", "RemoveItem(index)", "Removes an item."),
                 ("Clear", "Clear()", "Removes every item."), ("List", "List(index)", "Text of an item."),
                 ("IndexOf", "IndexOf(text)", "Index of an item (-1 = none)."), ("ShowDropDown", "ShowDropDown()", "Opens the list.")]),
    "RmSlider": dict(
        desc="Track bar with a value tip.", ar="شريط تمرير مع تلميح للقيمة.",
        size=(200, 44), text=False, default_event="ValueChanged",
        props=[("Value", "int", 0, "Behavior", "Current value."), ("Minimum", "int", 0, "Behavior", "Lowest value."),
               ("Maximum", "int", 100, "Behavior", "Highest value."), ("TickFrequency", "int", 0, "Appearance", "Tick every n (0 = none)."),
               ("SmallChange", "int", 1, "Behavior", "Arrow keys / wheel step."), ("LargeChange", "int", 10, "Behavior", "Page Up / Down step."),
               ("ShowValue", "bool", False, "Appearance", "Always show the value above the thumb.")],
        events=[("ValueChanged", "Value changed.")], methods=[]),
    "RmProgress": dict(
        desc="Linear, circular or marquee progress indicator.", ar="مؤشر تقدم خطي أو دائري أو متحرك.",
        size=(200, 8), text=False, default_event="Click",
        props=[("Value", "int", 0, "Behavior", "Current value."), ("Minimum", "int", 0, "Behavior", "Lowest value."),
               ("Maximum", "int", 100, "Behavior", "Highest value."),
               ("Kind", "enum", "Bar", "Appearance", "Bar, Circle or Marquee (busy).", ["Bar", "Circle", "Marquee"]),
               ("ShowText", "bool", False, "Appearance", "Shows the percentage."),
               ("TextFormat", "str", "", "Appearance", "Text with {0} = percent, e.g. \"{0}% done\".")],
        events=[], methods=[("Increment", "Increment(step)", "Adds step (1 by default) to Value.")]),
    "RmGauge": dict(
        desc="Circular dial or linear gauge with coloured ranges.", ar="عداد دائري أو خطي بنطاقات ملونة.",
        size=(150, 140), text=False, default_event="Click",
        props=[("Value", "float", 0, "Behavior", "Current value."), ("Minimum", "float", 0, "Behavior", "Lowest value."),
               ("Maximum", "float", 100, "Behavior", "Highest value."),
               ("Ranges", "str", "0-60:#2E7D32;60-80:#F9A825;80-100:#C62828", "Appearance", "Coloured ranges from-to:#colour;..."),
               ("Unit", "str", "", "Appearance", "Unit after the value (km/h, %, °C)."),
               ("Title", "str", "", "Appearance", "Caption under the value."),
               ("Kind", "enum", "Circular", "Appearance", "Circular dial or Linear scale.", ["Circular", "Linear"]),
               ("Decimals", "int", 0, "Appearance", "Decimals of the value."), ("ShowTicks", "bool", True, "Appearance", "Draws ticks.")],
        events=[], methods=[]),
    "RmPanel": dict(
        desc="Rounded / shadowed / gradient card that holds controls, optional title bar.",
        ar="بطاقة بحواف مستديرة وظل وتدرج تحتوي عناصر، مع شريط عنوان اختياري.",
        kind="container", size=(240, 160), text=False, default_event="Click",
        props=[("Title", "str", "", "Appearance", "Title bar text (empty = none)."),
               ("CornerRadius", "int", -1, "Appearance", "Corner radius (-1 = the theme's)."),
               ("Shadow", "bool", False, "Appearance", "Drop shadow."),
               ("GradientTo", "color", "", "Appearance", "Second colour of a vertical gradient (empty = none)."),
               ("BorderColor", "color", "", "Appearance", "Border colour (empty = the theme's).")],
        events=[], methods=[]),
    "RmGroupPanel": dict(
        desc="Collapsible group with a header (container).", ar="مجموعة قابلة للطي برأس (حاوية).",
        kind="container", size=(240, 140), text=False, default_event="CollapsedChanged",
        props=[("Title", "str", "Group", "Appearance", "Header text."), ("Collapsed", "bool", False, "Behavior", "Only the header is shown.")],
        events=[("CollapsedChanged", "Collapsed changed.")],
        methods=[("Toggle", "Toggle()", "Collapses / expands."), ("Expand", "Expand()", "Shows the content."),
                 ("Collapse", "Collapse()", "Hides the content.")]),
    "RmTabStrip": dict(
        desc="Modern tabs (top / left / bottom, closable, overflow arrows); children live on the pages (TabPage).",
        ar="تبويبات حديثة (أعلى / يسار / أسفل، قابلة للإغلاق، أسهم عند الزحام)؛ العناصر توضع على الصفحات.",
        kind="container", size=(320, 200), text=False, default_event="SelectedIndexChanged",
        props=[("TabPages", "list", "Page 1;Page 2", "Data", "Tabs: a;b;c or JSON [{Text, Name, Image}]."),
               ("SelectedIndex", "int", 0, "Behavior", "Page shown (click a tab in the designer to edit it)."),
               ("TabPosition", "enum", "Top", "Appearance", "Where the tabs are.", ["Top", "Left", "Bottom"]),
               ("Closable", "bool", False, "Behavior", "Tabs have a close button (TabClosing)."),
               ("AutoClose", "bool", True, "Behavior", "The close button removes the tab (False = only TabClosing).")],
        events=[("SelectedIndexChanged", "Another tab was selected."), ("TabClosing", "A tab's close button was pressed (EventItem / EventIndex).")],
        methods=[("AddTab", "AddTab(text)", "Adds a tab; returns its index."), ("RemoveTab", "RemoveTab(index)", "Removes a tab."),
                 ("TabCaption", "TabCaption(index, text)", "Gets / sets the caption of a tab."), ("SelectTab", "SelectTab(name)", "Shows a tab.")]),
    "RmNavigationPane": dict(
        desc="Navigation pane with page buttons and a header (container, Outlook style).",
        ar="لوحة تنقل بأزرار صفحات ورأس (حاوية، بأسلوب Outlook).",
        kind="container", size=(200, 300), text=False, default_event="SelectedIndexChanged",
        props=[("Pages", "list", "Mail;Calendar;Contacts", "Data", "Pages: a;b;c or JSON [{Text, Image}]."),
               ("SelectedIndex", "int", 0, "Behavior", "Page shown.")],
        events=[("SelectedIndexChanged", "Another page was selected.")], methods=[]),
    "RmSideBar": dict(
        desc="Vertical side bar with groups and items, badges and an icon-only collapsed mode.",
        ar="شريط جانبي رأسي بمجموعات وعناصر وشارات ووضع مطوي بالأيقونات فقط.",
        size=(200, 320), text=True, default_event="ItemClick",
        props=[("Text", "str", "", "Appearance", "Title next to the menu button."),
               ("Items", "multiline", '[{"Text":"Home","Image":"home"},{"Text":"Mail","Image":"mail","Count":3},{"Text":"Settings","Image":"settings"}]',
                "Data", "JSON [{Text, Name, Image, Count, Items:[...]}] (an item with Items is a group) or a;b;c."),
               ("SelectedItem", "str", "", "Behavior", "Name of the selected item."),
               ("Collapsed", "bool", False, "Behavior", "Narrow, icons only."),
               ("ShowToggle", "bool", True, "Appearance", "Shows the menu button that collapses the bar.")],
        events=[("ItemClick", "An item was clicked (EventItem = its Name, EventIndex)."), ("CollapsedChanged", "Collapsed changed.")],
        methods=[("SelectItem", "SelectItem(name)", "Selects an item."), ("SetBadge", "SetBadge(name, count)", "Badge number (0 = none)."),
                 ("SetItemText", "SetItemText(name, text)", "Changes an item's text."), ("Toggle", "Toggle()", "Collapses / expands.")]),
    "RmStatusBar": dict(
        desc="Modern status bar with panels: text, progress, zoom; spring panels fill the rest.",
        ar="شريط حالة حديث بلوحات: نص وتقدم وتكبير؛ اللوحات المرنة تملأ الباقي.",
        size=(400, 26), text=True, default_event="PanelClick",
        props=[("Panels", "multiline", '[{"Text":"Ready"},{"Text":"Ln 1","Width":90},{"Kind":"Zoom","Value":100}]', "Data",
                "JSON [{Text, Name, Width (0 = spring), Kind: Text|Progress|Zoom, Value, Image}] or a;b;c."),
               ("AccentBar", "bool", False, "Appearance", "Accent-coloured bar.")],
        events=[("PanelClick", "A panel was clicked (EventItem / EventIndex)."), ("ValueChanged", "The zoom changed.")],
        methods=[("SetPanelText", "SetPanelText(panel, text)", "Text of a panel (name or index)."),
                 ("GetPanelText", "GetPanelText(panel)", "Text of a panel."),
                 ("SetPanelValue", "SetPanelValue(panel, value)", "Value of a progress / zoom panel."),
                 ("GetPanelValue", "GetPanelValue(panel)", "Value of a panel.")]),
    "RmRibbon": dict(
        desc="Ribbon: application button, quick access toolbar, tabs, groups, large / small buttons, toggles, combos, drop-downs.",
        ar="شريط Ribbon: زر التطبيق وشريط الوصول السريع وتبويبات ومجموعات وأزرار كبيرة وصغيرة وأزرار تبديل وقوائم.",
        size=(600, 154), text=False, default_event="ItemClick",
        props=[("Tabs", "multiline", json.dumps([{"Text": "Home", "Groups": [{"Text": "Clipboard", "Items": [
                    {"Text": "Paste", "Name": "btnPaste", "Image": "paste", "Size": "Large"},
                    {"Text": "Cut", "Name": "btnCut", "Image": "cut"}, {"Text": "Copy", "Name": "btnCopy", "Image": "copy"}]}]},
                    {"Text": "View", "Groups": [{"Text": "Show", "Items": [{"Text": "Grid", "Name": "chkGrid", "Image": "grid", "Kind": "Check"}]}]}]),
                "Data", "JSON tabs [{Text, Groups:[{Text, Items:[{Text, Name, Image, Size: Large|Small, Kind: Button|Check|Combo|DropDown, Items}]}]}]."),
               ("QuickAccess", "list", "save;undo;redo", "Data", "Quick access buttons: item names or glyphs (a;b;c)."),
               ("AppMenu", "multiline", "", "Data", "Items of the application button's menu (JSON / a;b;c; empty = ItemClick AppButton)."),
               ("AppButtonText", "str", "File", "Appearance", "Caption of the application button (empty = none)."),
               ("SelectedTab", "int", 0, "Behavior", "Index of the tab shown."),
               ("Collapsed", "bool", False, "Behavior", "Only the tab row is shown.")],
        events=[("ItemClick", "A ribbon item was clicked (EventItem = its Name, EventIndex)."), ("TabChanged", "Another tab was selected."),
                ("CollapsedChanged", "Collapsed changed.")],
        methods=[("SetChecked", "SetChecked(name, checked)", "Checks a Check item."), ("GetChecked", "GetChecked(name)", "Is it checked?"),
                 ("SetEnabled", "SetEnabled(name, enabled)", "Enables / disables an item."),
                 ("SetItemText", "SetItemText(name, text)", "Changes an item's caption."),
                 ("SetValue", "SetValue(name, text)", "Text of a Combo item."), ("GetValue", "GetValue(name)", "Text of a Combo item."),
                 ("SelectTab", "SelectTab(name)", "Shows a tab."), ("Toggle", "Toggle()", "Collapses / expands.")]),
    "RmGrid": dict(
        desc="Advanced grid: typed columns, sorting, filter row, grouping, frozen columns, editing, alternating rows.",
        ar="جدول متقدم: أعمدة بأنواع، ترتيب، صف تصفية، تجميع، أعمدة مثبتة، تحرير، صفوف متناوبة.",
        size=(360, 200), text=False, default_event="CellClick",
        props=[("Columns", "multiline", "Name;Age:Number:60;Active:Check:60", "Data",
                "Columns: Name;Age:Number:60 (header:type:width) or JSON [{Text, Type, Width, Frozen, ReadOnly, Items}]; "
                "types Text, Number, Check, Combo, Date, Image, Progress, Button."),
               ("Rows", "multiline", "Mona|31|True;Ali|25|False", "Data", "Rows separated by ; with cells separated by |, or JSON [[...]]."),
               ("ReadOnly", "bool", False, "Behavior", "No editing."), ("AllowSort", "bool", True, "Behavior", "Click a header to sort."),
               ("AllowFilter", "bool", False, "Behavior", "Filter row under the header."),
               ("GroupBy", "str", "", "Behavior", "Column name whose values group the rows (empty = no groups)."),
               ("SelectionMode", "enum", "FullRowSelect", "Behavior", "Selection.", ["FullRowSelect", "CellSelect", "MultiRow"]),
               ("AlternatingRows", "bool", True, "Appearance", "Every other row tinted."),
               ("RowHeight", "int", 28, "Appearance", "Row height in pixels.")],
        events=[("CellClick", "A cell was clicked (EventRow / EventColumn)."), ("CellDoubleClick", "A cell was double-clicked."),
                ("CellValueChanged", "The user changed a cell (EventRow / EventColumn)."), ("SelectionChanged", "The selection changed."),
                ("ButtonCellClick", "A Button cell was clicked (EventRow / EventColumn)."), ("ColumnHeaderClick", "A header was clicked.")],
        methods=[("AddRow", "AddRow(\"a;b;c\")", "Adds a row (cells separated by ; or |); returns its index."),
                 ("InsertRow", "InsertRow(index, cells)", "Inserts a row."), ("RemoveRow", "RemoveRow(index)", "Removes a row."),
                 ("Clear", "Clear()", "Removes every row."), ("GetCell", "GetCell(row, column)", "Value of a cell (column = index or name)."),
                 ("SetCell", "SetCell(row, column, value)", "Changes a cell."), ("GetRow", "GetRow(row)", "Cells of a row separated by |."),
                 ("SortBy", "SortBy(column, descending)", "Sorts."), ("SetFilter", "SetFilter(column, text)", "Filters a column."),
                 ("ClearFilter", "ClearFilter()", "Removes the filters."), ("SetColumnWidth", "SetColumnWidth(column, width)", "Column width."),
                 ("BeginEdit", "BeginEdit(row, column)", "Edits a cell."), ("EnsureVisible", "EnsureVisible(row)", "Scrolls to a row.")]),
    "RmListView": dict(
        desc="Modern list: Details (columns), Tiles and Cards views with images.", ar="قائمة حديثة: تفاصيل (أعمدة) وبلاطات وبطاقات مع صور.",
        size=(300, 200), text=False, default_event="ItemClick",
        props=[("Columns", "list", "Name;Size;Modified", "Data", "Column headers a;b;c (Cards show them as labels)."),
               ("Items", "multiline", '[{"Text":"Report.docx","Image":"file","SubItems":["12 KB","Today"]}]', "Data",
                "JSON [{Text, Image, SubItems:[...]}] or rows a|b;c|d."),
               ("View", "enum", "Details", "Appearance", "How items are shown.", ["Details", "Tiles", "Cards"]),
               ("SelectedIndex", "int", -1, "Behavior", "Selected item (-1 = none)."),
               ("RowHeight", "int", 0, "Appearance", "Row / tile height (0 = automatic).")],
        events=[("ItemClick", "An item was clicked (EventItem = its text, EventIndex)."), ("ItemActivate", "Double-click / Enter on an item."),
                ("SelectedIndexChanged", "The selection changed.")],
        methods=[("AddItem", "AddItem(\"text;sub1;sub2\")", "Adds an item."), ("RemoveItem", "RemoveItem(index)", "Removes an item."),
                 ("Clear", "Clear()", "Removes every item."), ("List", "List(index)", "Text of an item."),
                 ("SetItemImage", "SetItemImage(index, image)", "Image of an item.")]),
    "RmTreeView": dict(
        desc="Themed tree with images, check boxes and lazy nodes.", ar="شجرة بمظهر حديث مع صور ومربعات اختيار وعقد تُحمّل عند الطلب.",
        size=(220, 260), text=False, default_event="NodeClick",
        props=[("Nodes", "multiline", '[{"Text":"Root","Image":"folder","Expanded":true,"Nodes":[{"Text":"Child 1"},{"Text":"Child 2"}]}]', "Data",
                "JSON [{Text, Name, Image, Expanded, Checked, Lazy, Nodes:[...]}] or a;b;c."),
               ("CheckBoxes", "bool", False, "Appearance", "Check boxes on the nodes."),
               ("ShowLines", "bool", True, "Appearance", "Connecting lines."),
               ("SelectedNode", "str", "", "Behavior", "Name of the selected node.")],
        events=[("NodeClick", "A node was clicked (EventItem = its Name)."), ("NodeDoubleClick", "A node was double-clicked."),
                ("NodeExpanding", "A node opens (lazy nodes: add the children with AddNode here)."),
                ("NodeCollapsed", "A node closed."), ("NodeChecked", "A node's check box changed."),
                ("SelectedIndexChanged", "Another node was selected.")],
        methods=[("AddNode", "AddNode(parent, text, name, image)", "Adds a node (parent \"\" = root); returns its name."),
                 ("RemoveNode", "RemoveNode(name)", "Removes a node."), ("Clear", "Clear()", "Removes every node."),
                 ("ExpandNode", "ExpandNode(name)", "Opens a node."), ("CollapseNode", "CollapseNode(name)", "Closes a node."),
                 ("ExpandAll", "ExpandAll()", "Opens every node."), ("CollapseAll", "CollapseAll()", "Closes every node."),
                 ("SetChecked", "SetChecked(name, checked)", "Checks a node and its children."), ("GetChecked", "GetChecked(name)", "Is it checked?"),
                 ("SelectNode", "SelectNode(name)", "Selects a node."), ("GetNodeText", "GetNodeText(name)", "Text of a node."),
                 ("SetNodeText", "SetNodeText(name, text)", "Changes a node's text."), ("SetNodeImage", "SetNodeImage(name, image)", "Changes a node's image.")]),
    "RmDatePicker": dict(
        desc="Date box with a drop-down calendar (locale month names).", ar="مربع تاريخ مع تقويم منسدل (أسماء الشهور حسب لغة النظام).",
        size=(170, 30), text=False, default_event="ValueChanged",
        props=[("Value", "str", "", "Behavior", "The date yyyy-MM-dd (empty = today)."),
               ("Format", "str", "Short", "Appearance", "Short, Long, ISO or a pattern such as dd/MM/yyyy."),
               ("MinDate", "str", "", "Behavior", "Earliest date (yyyy-MM-dd)."), ("MaxDate", "str", "", "Behavior", "Latest date (yyyy-MM-dd).")],
        events=[("ValueChanged", "The date changed.")],
        methods=[("AddDays", "AddDays(n)", "Moves the date by n days."), ("AddMonths", "AddMonths(n)", "Moves the date by n months."),
                 ("Today", "Today()", "Sets today's date."), ("ShowDropDown", "ShowDropDown()", "Opens the calendar."),
                 ("FormatDate", "FormatDate(date, format)", "A date as text.")]),
    "RmTimePicker": dict(
        desc="Time box with hour / minute / second segments.", ar="مربع وقت بأجزاء الساعة والدقيقة والثانية.",
        size=(120, 30), text=False, default_event="ValueChanged",
        props=[("Value", "str", "12:00:00", "Behavior", "The time HH:mm:ss (empty = now)."),
               ("Format", "str", "HH:mm", "Appearance", "HH:mm, HH:mm:ss or hh:mm tt (12 hours)."),
               ("ShowSeconds", "bool", False, "Appearance", "Shows the seconds.")],
        events=[("ValueChanged", "The time changed.")], methods=[]),
    "RmCalendar": dict(
        desc="Month calendar (locale month and day names, keyboard).", ar="تقويم شهري (أسماء الشهور والأيام حسب لغة النظام، لوحة المفاتيح).",
        size=(250, 230), text=False, default_event="ValueChanged",
        props=[("Value", "str", "", "Behavior", "Selected date yyyy-MM-dd (empty = today)."),
               ("MinDate", "str", "", "Behavior", "Earliest date."), ("MaxDate", "str", "", "Behavior", "Latest date.")],
        events=[("ValueChanged", "Another day was selected.")],
        methods=[("AddDays", "AddDays(n)", "Moves the date by n days."), ("AddMonths", "AddMonths(n)", "Moves the date by n months."),
                 ("Today", "Today()", "Selects today.")]),
    "RmTile": dict(
        desc="Metro tile: title, count, image, colour.", ar="بلاطة Metro: عنوان وعدد وصورة ولون.",
        size=(150, 150), text=False, default_event="Click",
        props=[("Title", "str", "Tile", "Appearance", "Caption at the bottom."), ("Count", "str", "", "Appearance", "Big number / text at the top right."),
               ("Image", "str", "", "Appearance", "Glyph name or image."), ("TileColor", "color", "", "Appearance", "Background (empty = accent)."),
               ("Size", "enum", "Medium", "Appearance", "Small 70, Medium 150, Wide 310x150, Large 310 (pixels).", ["Small", "Medium", "Wide", "Large"])],
        events=[("Click", "The tile was clicked.")], methods=[]),
    "RmDockPanel": dict(
        desc="Docking host: RmDockWindow children dock left / right / top / bottom / fill, tab, float and auto-hide.",
        ar="مضيف إرساء: نوافذ RmDockWindow ترسو يساراً / يميناً / أعلى / أسفل / ملء، وتتبوّب وتطفو وتختفي تلقائياً.",
        kind="container", size=(500, 320), text=False, default_event="ActiveWindowChanged",
        props=[("Layout", "multiline", "", "Behavior", "Saved layout (JSON from SaveLayout) applied at start.")],
        events=[("WindowClosed", "A window was closed (EventItem = its name)."), ("ActiveWindowChanged", "Another window became active.")],
        methods=[("SaveLayout", "SaveLayout()", "The layout as JSON."), ("LoadLayout", "LoadLayout(json)", "Applies a layout."),
                 ("ShowWindow", "ShowWindow(name)", "Shows a closed window."), ("CloseWindow", "CloseWindow(name)", "Closes a window."),
                 ("DockWindow", "DockWindow(name, side)", "Docks a window (Left, Right, Top, Bottom, Fill, Float)."),
                 ("Refresh", "Refresh()", "Lays the windows out again.")]),
    "RmDockWindow": dict(
        desc="A dockable tool window (container) inside an RmDockPanel.", ar="نافذة أدوات قابلة للإرساء (حاوية) داخل RmDockPanel.",
        kind="container", size=(200, 200), text=False, default_event="Click",
        props=[("Title", "str", "Window", "Appearance", "Caption of the title bar."),
               ("DockSide", "enum", "Left", "Behavior", "Where it docks.", ["Left", "Right", "Top", "Bottom", "Fill", "Float"]),
               ("AutoHide", "bool", False, "Behavior", "Collapsed to a side tab that slides out."),
               ("DockSize", "int", 0, "Behavior", "Docked width / height (0 = the designer size).")],
        events=[], methods=[]),
    "RmToast": dict(
        desc="Notification that slides in at a screen corner (Info / Success / Warning / Error).",
        ar="إشعار يظهر في زاوية الشاشة (معلومة / نجاح / تحذير / خطأ).",
        kind="nonvisual", size=(0, 0), text=False, default_event="Click",
        props=[("Position", "enum", "BottomRight", "Behavior", "Screen corner.", ["BottomRight", "TopRight", "BottomLeft", "TopLeft", "BottomCenter", "TopCenter"]),
               ("Duration", "int", 3000, "Behavior", "Milliseconds shown (0 = until clicked)."),
               ("ToastWidth", "int", 340, "Appearance", "Width in pixels.")],
        events=[("Click", "A toast was clicked (EventItem = its title).")],
        methods=[("Show", "Show(title, text, kind, ms)", "Shows a toast; kind Info, Success, Warning or Error."),
                 ("CloseAll", "CloseAll()", "Closes the toasts.")]),
    "RmSuperTooltip": dict(
        desc="Rich tooltips (title, image, text, footer) attached to controls.", ar="تلميحات غنية (عنوان وصورة ونص وتذييل) تُربط بالعناصر.",
        kind="nonvisual", size=(0, 0), text=False, default_event="",
        props=[("Delay", "int", 500, "Behavior", "Milliseconds before the tip shows."), ("MaxWidth", "int", 320, "Appearance", "Width limit."),
               ("Duration", "int", 8000, "Behavior", "Milliseconds shown (0 = until the mouse leaves).")],
        events=[],
        methods=[("SetToolTip", "SetToolTip(control, title, text, footer, image)", "Attaches a tip to a control (by name)."),
                 ("Show", "Show(control)", "Shows the control's tip now."), ("Hide", "Hide()", "Hides the tip."),
                 ("RemoveToolTip", "RemoveToolTip(control)", "Removes a control's tip.")]),
    "RmBalloonTip": dict(
        desc="Balloon tips that point at a control.", ar="تلميحات بالونية تشير إلى عنصر.",
        kind="nonvisual", size=(0, 0), text=False, default_event="",
        props=[("Delay", "int", 500, "Behavior", "Milliseconds before a hover tip shows."), ("MaxWidth", "int", 320, "Appearance", "Width limit."),
               ("Duration", "int", 0, "Behavior", "Milliseconds a hover tip stays (0 = until the mouse leaves).")],
        events=[],
        methods=[("Show", "Show(control, title, text, ms)", "Points a balloon at a control."),
                 ("SetToolTip", "SetToolTip(control, title, text)", "Hover balloon of a control."), ("Hide", "Hide()", "Hides the balloon.")]),
    "RmMessageBox": dict(
        desc="Themed message box / task dialog: Show returns the pressed button.", ar="صندوق رسالة / حوار مهام بالمظهر الحديث: Show تعيد الزر المضغوط.",
        kind="nonvisual", size=(0, 0), text=False, default_event="",
        props=[], events=[],
        methods=[("Show", "Show(text, title, buttons, icon, heading)",
                  "Shows the box; buttons OK, OKCancel, YesNo, YesNoCancel, RetryCancel, AbortRetryIgnore or \"Save;Don't Save;Cancel\"; "
                  "icon Info, Success, Warning, Error, Question; returns the button's text.")]),
}

ORDER = ["RmButton", "RmToggle", "RmCheckBox", "RmRadioButton", "RmTextBox", "RmComboBox", "RmSlider", "RmProgress", "RmGauge",
         "RmTile", "RmPanel", "RmGroupPanel", "RmTabStrip", "RmSideBar", "RmNavigationPane", "RmRibbon", "RmStatusBar", "RmGrid",
         "RmListView", "RmTreeView", "RmDatePicker", "RmTimePicker", "RmCalendar", "RmDockPanel", "RmDockWindow", "RmToast",
         "RmSuperTooltip", "RmBalloonTip", "RmMessageBox"]
ITEM_EVENTS = {"RmButton", "RmSideBar", "RmStatusBar", "RmRibbon", "RmGrid", "RmListView", "RmTreeView", "RmTabStrip", "RmDockPanel",
               "RmToast"}
PAGED = {"RmTabStrip", "RmNavigationPane"}

AR_HELP = """
## بالعربية

{ar}

- يظهر في صندوق الأدوات تحت **Modern (RAD)** ويعمل في كل مشاريع سطح المكتب: داخل بيئة التطوير (Tk) وفي الملف التنفيذي
  الأصلي لمشاريع C / C++ / Fortran (وحدات radforms المكتوبة بلغة C، ملف exe واحد مستقل بلا Python).
- الخاصية **Style** تختار السمة (Inherit = سمة النموذج، Light / Dark / Office / Metro) و **AccentColor** لون التمييز.
- عند اتجاه النموذج من اليمين لليسار (RightToLeft) يُعكس التخطيط تلقائياً ويُكتب النص العربي صحيحاً.
{ar_events}
"""


def manifest(name: str, s: dict) -> dict:
    props = []
    for p in s["props"] + LOOK + (EVENT_ITEM if name in ITEM_EVENTS else []):
        name_, typ, default, cat, desc = p[:5]
        choices = p[5] if len(p) > 5 else None
        extra = p[6] if len(p) > 6 else {}
        if name_ == "Text":
            continue                     # the common Text property (hasText)
        d = {"name": name_, "type": typ, "default": default, "category": cat, "description": desc}
        if choices:
            d["choices"] = choices
        d.update({k: v for k, v in extra.items() if k == "browsable"})
        props.append(d)
    text_default = next((p[2] for p in s["props"] if p[0] == "Text"), None)
    m = {"schemaVersion": 1, "name": name, "version": "1.0.0", "publisher": "RAD IDE",
         "description": s["desc"], "category": CATEGORY, "order": 3000 + ORDER.index(name) * 10, "builtin": True, "prefix": name,
         "defaultSize": list(s["size"]), "kind": s.get("kind", "visual"), "hasText": bool(s.get("text")),
         "commonEvents": s.get("kind") != "nonvisual"}
    if text_default is not None:
        m["overrides"] = {"Text": text_default}
    if s.get("default_event"):
        m["defaultEvent"] = s["default_event"]
    m["properties"] = props
    m["events"] = []
    for e in s["events"]:
        ev = {"name": e[0], "description": e[1]}
        if len(e) > 2:
            ev["args"] = e[2]
        m["events"].append(ev)
    m["methods"] = [{"name": n, "signature": sig, "description": d} for n, sig, d in s["methods"]]
    m["targets"] = {"python-tk": {"file": f"runtime/rmtk_{name}.py", "class": name,
                                  "notes": "also draws the control for VB6 (vb-basic) and every GUI Bridge language; native C / C++ / "
                                           "Fortran exes use radforms/controls/rm_*.c"}}
    m["designer"] = "designer.py"
    m["help"] = "help.md"
    return m


DESIGNER = '''"""{name} on the design surface: radide/components/rmpaint.py draws every Rm* control like the native runtime."""
from radide.components.rmpaint import paint_control{extra_import}


def paint(painter, rect, props, ctx):
    paint_control("{name}", painter, rect, props, ctx)
{extra}'''

TAB_AT = '''

def tab_at(props, x, y, w, h):
    """Page clicked in the designer (the designer shows that page): -1 = none."""
    return _tab_at({{**props, "_type": "{name}"}}, x, y, w, h)
'''

RUNTIME = '''"""{name} - python-tk runtime of the {name} component package (the classes live in ../../_rmkit/rmkit_tk.py,
shared by every Rm* package). Also used for VB6 forms and every GUI Bridge language run inside the IDE."""
import os as _os
import sys as _sys

_KIT = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_rmkit"))
if _KIT not in _sys.path:
    _sys.path.append(_KIT)

from rmkit_tk import {name}  # noqa: E402

__all__ = ["{name}"]
'''


def help_md(name: str, s: dict, m: dict) -> str:
    kind = {"visual": "visual control", "container": "container (holds other controls)", "nonvisual": "component (no window)"}[m["kind"]]
    L = [f"# {name}", "", s["desc"], "",
         f"**Kind:** {kind}. **Toolbox:** {CATEGORY}. **New name:** {name}1, {name}2 ...", "",
         f"**Default size:** {s['size'][0]} x {s['size'][1]} pixels." if m["kind"] != "nonvisual" else
         "Shown in the component tray under the form.", "",
         "Part of the RAD Modern controls (docs/plans/MODERN_CONTROLS.md): the same names in every language. Native C / C++ / "
         "Fortran builds draw it with the radforms module (one standalone exe, no Python); inside the IDE the python-tk runtime draws it.",
         "", "## Properties", ""]
    if m["kind"] != "nonvisual":
        L.append("Besides the common properties (Name, Left, Top, Width, Height, colours, font, Enabled, Visible, Anchor, Dock ...):")
        L.append("")
    L += ["| Property | Type | Default | Description |", "|---|---|---|---|"]
    if m.get("hasText"):
        L.append(f"| Text | str | {json.dumps(m.get('overrides', {}).get('Text', ''))} | {next((p[4] for p in s['props'] if p[0] == 'Text'), 'Caption.')} |")
    for p in m["properties"]:
        d = p["default"]
        dv = json.dumps(d) if not isinstance(d, str) or len(d) < 40 else "(see the designer)"
        choices = f" ({', '.join(p['choices'])})" if p.get("choices") else ""
        L.append(f"| {p['name']} | {p['type']} | {dv} | {p['description']}{choices} |")
    if m["events"]:
        L += ["", "## Events", ""]
        if m.get("defaultEvent"):
            L += [f"Double-clicking the control in the designer writes the handler of **{m['defaultEvent']}**.", ""]
        L += [f"- **{e['name']}** - {e['description']}" for e in m["events"]]
        if name in ITEM_EVENTS:
            L += ["", "Item events also put the item into **EventItem** / **EventIndex** (grid: **EventRow** / **EventColumn**) - "
                  "read them in the handler in any language. In a native C program `rad_arg(0)` / `rad_arg(1)` give the same "
                  "values (item name and index; grid: row and column)."]
    if m["methods"]:
        L += ["", "## Methods", ""]
        L += [f"- `{x['signature']}` - {x['description']}" for x in m["methods"]]
    L += ["", "## Example (C, GUI Bridge API)", "", "```c"]
    L += example_c(name, s)
    L += ["```", "", "## Example (VB / BASIC)", "", "```vb"]
    L += example_vb(name, s)
    L += ["```"]
    evs = [e["name"] for e in m["events"]]
    ar_events = ("- الأحداث: " + "، ".join(evs) + ".") if evs else ""
    L.append(AR_HELP.format(ar=s["ar"], ar_events=ar_events))
    L.append("See docs/COMPONENTS.md for component packages and docs/NATIVE_BUILD.md (\"Modern controls (Rm*)\") for the C ABI.")
    return "\n".join(L) + "\n"


def example_c(name, s):
    ex = {
        "RmButton": ['void RmButton1_Click(void) { rad_set("lblOut", "Text", "clicked"); }'],
        "RmToggle": ['void RmToggle1_CheckedChanged(void) { rad_set("lblOut", "Text", rad_get("RmToggle1", "Checked")); }'],
        "RmToast": ['rad_call("RmToast1", "Show", "Saved\\tThe file was saved.\\tSuccess\\t3000");'],
        "RmMessageBox": ['const char *r = rad_call("RmMessageBox1", "Show", "Save the changes?\\tApp\\tYesNoCancel\\tQuestion");'],
        "RmGrid": ['rad_call("RmGrid1", "AddRow", "Sara;28;True");', 'void RmGrid1_CellClick(void) { int row = (int)rad_num(rad_arg(0)); }'],
        "RmRibbon": ['void RmRibbon1_ItemClick(void) {', '    const char *item = rad_arg(0);     /* or rad_get("RmRibbon1", "EventItem") */', '}'],
        "RmTreeView": ['void RmTreeView1_NodeExpanding(void) {', '    rad_call("RmTreeView1", "AddNode", "\\tChild\\tc1\\tfile"); /* parent name in rad_arg(0) */', '}'],
        "RmSideBar": ['void RmSideBar1_ItemClick(void) { rad_set("lblOut", "Text", rad_arg(0)); }'],
    }
    return ex.get(name, [f'rad_set("{name}1", "Style", "Dark");   /* any property: rad_set / rad_get */'])


def example_vb(name, s):
    ex = {
        "RmButton": ["Private Sub RmButton1_Click()", '    lblOut.Caption = "clicked"', "End Sub"],
        "RmToast": ['RmToast1.Show "Saved", "The file was saved.", "Success", 3000'],
        "RmMessageBox": ['If RmMessageBox1.Show("Save the changes?", "App", "YesNo", "Question") = "Yes" Then Save'],
        "RmGrid": ['RmGrid1.AddRow "Sara;28;True"', "Private Sub RmGrid1_CellClick()", "    MsgBox RmGrid1.GetCell(RmGrid1.EventRow, 0)", "End Sub"],
        "RmRibbon": ["Private Sub RmRibbon1_ItemClick()", "    Select Case RmRibbon1.EventItem", '    Case "btnPaste": Paste', "    End Select", "End Sub"],
    }
    return ex.get(name, [f'{name}1.Style = "Office"'])


def main():
    for name in ORDER:
        s = SPEC[name]
        d = BUILTIN / name
        (d / "runtime").mkdir(parents=True, exist_ok=True)
        m = manifest(name, s)
        (d / "component.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        extra_import = ", tab_at as _tab_at" if name in PAGED else ""
        extra = TAB_AT.format(name=name) if name in PAGED else ""
        (d / "designer.py").write_text(DESIGNER.format(name=name, extra_import=extra_import, extra=extra), encoding="utf-8")
        (d / "runtime" / f"rmtk_{name}.py").write_text(RUNTIME.format(name=name), encoding="utf-8")
        (d / "help.md").write_text(help_md(name, s, m), encoding="utf-8")
    print(f"{len(ORDER)} packages written to {BUILTIN}")


if __name__ == "__main__":
    main()
