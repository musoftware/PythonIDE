"""Widget palette of the Flutter designer: the catalog by category (with icons and search) plus ready-made
snippets (gradient button, rounded input, social login row ...). Items are dragged onto the canvas or the widget
tree, or double-clicked to insert into the selected widget."""
from __future__ import annotations

import copy
import json

from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from . import iconfont
from . import model as M

MIME = "application/x-radide-fwidget"          # {"type": ..., "ctor": ...} or {"node": {...}} or {"move": id}

TYPE_ICONS = {
    "Scaffold": "web_asset", "SafeArea": "security", "Container": "crop_square", "Padding": "padding",
    "Center": "filter_center_focus", "Align": "format_align_center", "Column": "view_column",
    "Row": "table_rows", "Flex": "view_week", "Wrap": "wrap_text", "Stack": "layers", "Positioned": "open_with",
    "Expanded": "open_in_full", "Flexible": "unfold_more", "Spacer": "space_bar", "SizedBox": "crop_free",
    "ConstrainedBox": "fit_screen", "AspectRatio": "aspect_ratio", "FractionallySizedBox": "photo_size_select_large",
    "FittedBox": "fit_screen", "Transform": "rotate_right", "Visibility": "visibility",
    "IntrinsicHeight": "height", "SingleChildScrollView": "swipe_vertical", "ListView": "view_list",
    "GridView": "grid_view", "PageView": "view_carousel", "Text": "text_fields", "SelectableText": "text_format",
    "Icon": "emoji_symbols", "Image": "image", "CircleAvatar": "account_circle", "Divider": "horizontal_rule",
    "VerticalDivider": "more_vert", "Placeholder": "check_box_outline_blank",
    "CircularProgressIndicator": "autorenew", "LinearProgressIndicator": "linear_scale", "Chip": "label",
    "Badge": "notifications_active", "Tooltip": "info_outline", "FlutterLogo": "flutter_dash",
    "TextField": "input", "TextFormField": "edit_note", "Checkbox": "check_box", "Switch": "toggle_on",
    "Slider": "tune", "DropdownButton": "arrow_drop_down_circle", "CheckboxListTile": "checklist",
    "SwitchListTile": "settings_suggest", "Form": "assignment", "InkWell": "touch_app",
    "GestureDetector": "pan_tool", "ElevatedButton": "smart_button", "FilledButton": "smart_button",
    "TextButton": "title", "OutlinedButton": "crop_7_5", "IconButton": "radio_button_checked",
    "MaterialButton": "rectangle", "FloatingActionButton": "add_circle", "AppBar": "web",
    "BottomNavigationBar": "call_to_action", "NavigationBar": "call_to_action", "Drawer": "menu_open",
    "DrawerHeader": "featured_play_list", "TabBar": "tab", "Tab": "tab_unselected", "TabBarView": "view_day",
    "DefaultTabController": "tab", "Card": "credit_card", "ListTile": "list", "ExpansionTile": "expand_more",
    "Material": "layers", "Opacity": "opacity", "ClipRRect": "rounded_corner", "ClipOval": "circle",
    "Hero": "flight_takeoff", "DecoratedBox": "format_paint", "RotatedBox": "screen_rotation",
    "AnimatedContainer": "animation", "AnimatedOpacity": "gradient", "AnimatedSwitcher": "swap_horiz",
    "CupertinoPageScaffold": "phone_iphone", "CupertinoNavigationBar": "web", "CupertinoButton": "smart_button",
    "CupertinoTextField": "input", "CupertinoSwitch": "toggle_on", "CupertinoSlider": "tune",
    "CupertinoActivityIndicator": "autorenew", "CupertinoListTile": "list", "Code": "code",
}


def _tr(text: str) -> str:
    """The UI translation of a palette group / snippet title (the tree items themselves are not translated)."""
    try:
        from ..i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def type_icon(type_: str, size: int = 18, color: str = "#FF3F51B5"):
    return iconfont.icon("Icons." + TYPE_ICONS.get(type_, "widgets"), size, color)


def _component_icon(type_: str):
    """The Toolbox icon of a component package widget (radide/components)."""
    try:
        from ..components import package_of
        pkg = package_of(type_)
        if pkg is not None and pkg.icon_path is not None:
            from PyQt6.QtGui import QIcon
            return QIcon(str(pkg.icon_path))
    except Exception:  # noqa: BLE001
        pass
    return type_icon(type_)


# ----------------------------------------------------------------------------- snippets
def _t(type_, props=None, slots=None, children=None, ctor=None, **extra):
    return M.T(type_, props, slots, children, ctor, **extra)


def _text(s, **style):
    return _t("Text", {"data": s, **({"style": style} if style else {})})


SNIPPETS: list[tuple[str, str, str, dict]] = [
    ("Gradient button", "smart_button", "Rounded button with a gradient (Container + InkWell)",
     _t("InkWell", {"borderRadius": 28}, {"child": _t("Container", {
         "height": 56, "alignment": "Alignment.center",
         "decoration": {"gradient": {"type": "linear", "begin": "Alignment.centerLeft", "end": "Alignment.centerRight",
                                     "colors": ["#FF8F94FB", "#FF4E54C8"]}, "borderRadius": 28,
                        "boxShadow": [{"color": "#554E54C8", "blur": 16, "offset": [0, 8]}]}},
         {"child": _text("Login", color="Colors.white", fontSize=18, fontWeight="FontWeight.w600")})})),
    ("Rounded input", "input", "Filled text field with an icon and rounded corners",
     _t("TextField", {"decoration": {"hintText": "Email", "prefixIcon": "Icons.email_outlined", "filled": True,
                                     "fillColor": "#FFF3F4F8", "border": "outline", "borderRadius": 14,
                                     "borderColor": "#00000000", "focusedBorderColor": "#FF4E54C8"}})),
    ("Password input", "password", "Obscured field with lock and eye icons",
     _t("TextField", {"obscureText": True,
                      "decoration": {"hintText": "Password", "prefixIcon": "Icons.lock_outline",
                                     "suffixIcon": "Icons.visibility_off_outlined", "filled": True,
                                     "fillColor": "#FFF3F4F8", "border": "outline", "borderRadius": 14,
                                     "borderColor": "#00000000"}})),
    ("Gradient header", "gradient", "Tall header with a gradient, rounded bottom and a title",
     _t("Container", {"height": 260, "padding": {"all": 24}, "alignment": "Alignment.bottomLeft",
                      "decoration": {"gradient": {"type": "linear", "begin": "Alignment.topLeft",
                                                  "end": "Alignment.bottomRight",
                                                  "colors": ["#FF8F94FB", "#FF4E54C8"]},
                                     "borderRadius": {"bl": 36, "br": 36}}},
        {"child": _t("Column", {"mainAxisSize": "MainAxisSize.min",
                                "crossAxisAlignment": "CrossAxisAlignment.start"},
                     children=[_text("Welcome back", color="Colors.white", fontSize=32, fontWeight="FontWeight.bold"),
                               _text("Sign in to continue", color="Colors.white70", fontSize=16)])})),
    ("Rounded card", "credit_card", "White card with a soft shadow and padding",
     _t("Container", {"padding": {"all": 20},
                      "decoration": {"color": "#FFFFFFFF", "borderRadius": 20,
                                     "boxShadow": [{"color": "#1A000000", "blur": 24, "offset": [0, 12]}]}},
        {"child": _t("Column", {"crossAxisAlignment": "CrossAxisAlignment.stretch", "spacing": 12},
                     children=[_text("Card title", fontSize=18, fontWeight="FontWeight.w600"),
                               _text("Some supporting text.", color="#FF757575")])})),
    ("Social login row", "group", "Row of round social buttons",
     _t("Row", {"mainAxisAlignment": "MainAxisAlignment.center", "spacing": 16}, children=[
         _t("Container", {"width": 52, "height": 52, "decoration": {"shape": "BoxShape.circle", "color": c}},
            {"child": _t("Icon", {"icon": i, "color": "Colors.white"})})
         for c, i in (("#FFDB4437", "Icons.g_mobiledata"), ("#FF3B5998", "Icons.facebook"),
                      ("#FF000000", "Icons.apple"))])),
    ("Section title", "title", "Title with a 'See all' button",
     _t("Row", {"mainAxisAlignment": "MainAxisAlignment.spaceBetween"},
        children=[_text("Popular", fontSize=20, fontWeight="FontWeight.bold"),
                  _t("TextButton", slots={"child": _text("See all")})])),
    ("Avatar row", "account_circle", "Avatar, name and subtitle",
     _t("Row", {"spacing": 12}, children=[
         _t("CircleAvatar", {"radius": 24, "backgroundImage": {"source": "network",
                                                                "src": "https://picsum.photos/seed/rad/96"}}),
         _t("Column", {"crossAxisAlignment": "CrossAxisAlignment.start", "mainAxisSize": "MainAxisSize.min"},
            children=[_text("Jane Doe", fontSize=16, fontWeight="FontWeight.w600"),
                      _text("Product designer", color="#FF757575")])])),
    ("Image card", "photo", "Picture with rounded corners and a caption",
     _t("Column", {"crossAxisAlignment": "CrossAxisAlignment.start", "spacing": 8, "mainAxisSize": "MainAxisSize.min"},
        children=[_t("ClipRRect", {"borderRadius": 16}, {"child": _t("Image", {
            "src": "https://picsum.photos/seed/card/600/400", "height": 160, "width": "infinity",
            "fit": "BoxFit.cover"}, ctor="network")}),
            _text("Caption", fontSize=16, fontWeight="FontWeight.w600")])),
    ("Stack overlay", "layers", "Background picture with text over it (Stack + Positioned)",
     _t("Stack", children=[
         _t("Container", {"height": 200, "decoration": {"borderRadius": 16, "image": {
             "source": "network", "src": "https://picsum.photos/seed/stack/800/500", "fit": "BoxFit.cover"}}}),
         _t("Positioned", {"left": 16, "bottom": 16},
            {"child": _text("Over the picture", color="Colors.white", fontSize=22, fontWeight="FontWeight.bold")})])),
]


# ------------------------------------------------------------------------------- widget
class PaletteTree(QTreeWidget):
    def __init__(self, palette):
        super().__init__()
        self.palette = palette
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setIconSize(QSize(18, 18))
        self.setIndentation(12)
        self.setRootIsDecorated(True)
        self.setProperty("i18n_skip_items", True)

    def mimeTypes(self):
        return [MIME]

    def startDrag(self, actions):
        it = self.currentItem()
        payload = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        if not payload:
            return
        md = QMimeData()
        md.setData(MIME, json.dumps(payload).encode("utf-8"))
        md.setText(payload.get("type") or "snippet")
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.setPixmap(it.icon(0).pixmap(24, 24))
        drag.exec(Qt.DropAction.CopyAction)


class Palette(QWidget):
    """Signals ``insertRequested(payload)`` on double-click (payload = {"type", "ctor"} or {"node"})."""
    insertRequested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search widgets")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.tree = PaletteTree(self)
        self.tree.itemDoubleClicked.connect(self._dclick)
        lay.addWidget(self.search)
        lay.addWidget(self.tree)
        self._fill()

    def _fill(self):
        try:                                 # installed component packages with a flutter template
            from ..components import dart as _comp_dart
            _comp_dart.sync_catalog()
        except Exception:  # noqa: BLE001
            pass
        self.tree.clear()
        snip = QTreeWidgetItem([_tr("Snippets")])
        f = snip.font(0)
        f.setBold(True)
        snip.setFont(0, f)
        snip.setFlags(Qt.ItemFlag.ItemIsEnabled)
        for title, icon_name, help_, node in SNIPPETS:
            it = QTreeWidgetItem(snip, [_tr(title)])
            it.setIcon(0, iconfont.icon("Icons." + icon_name, 18, "#FF8E24AA"))
            it.setToolTip(0, _tr(help_))
            it.setData(0, Qt.ItemDataRole.UserRole + 1, (title + " " + help_ + " " + _tr(title)).lower())
            it.setData(0, Qt.ItemDataRole.UserRole, {"node": copy.deepcopy(node), "title": title})
        self.tree.addTopLevelItem(snip)
        for cat, types in M.categories().items():
            g = QTreeWidgetItem([_tr(cat)])
            g.setData(0, Qt.ItemDataRole.UserRole + 2, cat)
            g.setFont(0, f)
            g.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for t in types:
                spec = M.CATALOG[t]
                it = QTreeWidgetItem(g, [t])
                it.setIcon(0, _component_icon(t) if getattr(spec, "component", None) else type_icon(t))
                it.setToolTip(0, f"{t} - {spec.help}")
                it.setData(0, Qt.ItemDataRole.UserRole, {"type": t})
                it.setData(0, Qt.ItemDataRole.UserRole + 1, (t + " " + spec.help).lower())
            self.tree.addTopLevelItem(g)
        self.tree.expandAll()
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            if g.data(0, Qt.ItemDataRole.UserRole + 2) in ("Cupertino", "Special", "Animation"):
                g.setExpanded(False)

    def _filter(self, text: str):
        q = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            vis = 0
            for j in range(g.childCount()):
                it = g.child(j)
                hay = it.data(0, Qt.ItemDataRole.UserRole + 1) or it.text(0).lower() + " " + it.toolTip(0).lower()
                ok = not q or q in hay
                it.setHidden(not ok)
                vis += ok
            g.setHidden(vis == 0)
            if q:
                g.setExpanded(True)

    def _dclick(self, item, _col):
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if payload:
            self.insertRequested.emit(dict(payload))
