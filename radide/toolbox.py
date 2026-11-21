"""Toolbox: pick a control and click (or drag) it onto the form, VB style."""
from __future__ import annotations

from PyQt6.QtCore import QMimeData, QObject, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from .controls import CONTROL_TYPES
from .mobile.controls import MOBILE_CONTROL_TYPES
from .mobile.render import mobile_tool_icon

MIME = "application/x-radide-control"
POINTER = "Pointer"
MOBILE_HEADER = "Mobile"                 # Toolbox group captions shown for phone forms
CLASSIC_HEADER = "Common Controls"


class ToolState(QObject):
    changed = pyqtSignal(object)   # str | None

    def __init__(self):
        super().__init__()
        self.current: str | None = None

    def set(self, tool: str | None) -> None:
        self.current = tool
        self.changed.emit(tool)

    # mobile forms (CONTRACTS 10.1): the shown designer says whether it is a phone form
    modeChanged = pyqtSignal(bool, object)      # mobile, enabled control types (set) | None
    mobile = False
    supported = None

    def set_mode(self, mobile: bool, supported=None) -> None:
        mobile = bool(mobile)
        supported = set(supported) if (mobile and supported) else None
        if mobile == self.mobile and supported == self.supported:
            return
        self.mobile, self.supported = mobile, supported
        self.modeChanged.emit(mobile, supported)

    # designer profile of the shown form's language plugin (``plugin.designer_profile``), e.g. a
    # WinForms form of an opened Visual Studio project: {"labels": {type: shown name},
    # "allowed": set of control types | None}.  None = the IDE's own control names.
    profileChanged = pyqtSignal(object)
    profile = None

    def set_profile(self, profile) -> None:
        if profile is self.profile:
            return
        self.profile = profile
        self.profileChanged.emit(profile)

    # language plugin id of the shown form: component packages without a runtime for it are greyed
    # (radide/components/targets.py)
    targetChanged = pyqtSignal(object)
    target = None

    def set_target(self, target) -> None:
        if target == self.target:
            return
        self.target = target
        self.targetChanged.emit(target)


TOOL_STATE = ToolState()


def control_icon(type_name: str) -> QIcon:
    """Small drawn icons, so the app needs no image files."""
    icon = package_icon(type_name)          # a component package's own icon file
    if icon is not None:
        return icon
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#3c3c3c"))
    p.setPen(pen)
    f = QFont("Segoe UI", 7, QFont.Weight.Bold)
    p.setFont(f)
    if type_name in MOBILE_CONTROL_TYPES:
        p.end()
        return mobile_tool_icon(type_name)
    if type_name == POINTER:
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF([QPointF(6, 2), QPointF(6, 16), QPointF(9, 13),
                                 QPointF(12, 18), QPointF(14, 17), QPointF(11, 12), QPointF(15, 12)]))
    elif type_name == "Button":
        p.setBrush(QColor("#e8e8e8"))
        p.drawRoundedRect(1, 5, 18, 10, 2, 2)
        p.drawText(1, 5, 18, 10, Qt.AlignmentFlag.AlignCenter, "ab")
    elif type_name == "Label":
        p.setFont(QFont("Times New Roman", 12, QFont.Weight.Bold))
        p.drawText(0, 0, 20, 20, Qt.AlignmentFlag.AlignCenter, "A")
    elif type_name == "TextBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 5, 18, 10)
        p.drawText(3, 5, 16, 10, Qt.AlignmentFlag.AlignVCenter, "ab|")
    elif type_name == "CheckBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(4, 4, 12, 12)
        p.setPen(QPen(QColor("#1e8f1e"), 2))
        p.drawPolyline(QPolygonF([QPointF(6, 10), QPointF(9, 13), QPointF(14, 6)]))
    elif type_name == "RadioButton":
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(3, 3, 14, 14)
        p.setBrush(QColor("#1e5fbf"))
        p.drawEllipse(7, 7, 6, 6)
    elif type_name == "ListBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(2, 2, 16, 16)
        for y in (6, 10, 14):
            p.drawLine(5, y, 15, y)
    elif type_name == "ComboBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 5, 18, 10)
        p.setBrush(QColor("#d0d0d0"))
        p.drawRect(12, 5, 7, 10)
        p.drawText(12, 5, 7, 10, Qt.AlignmentFlag.AlignCenter, "▾")
    elif type_name == "PictureBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(2, 3, 16, 14)
        p.setBrush(QColor("#3c9b3c"))
        p.drawPolygon(QPolygonF([QPointF(3, 16), QPointF(8, 9), QPointF(12, 14), QPointF(17, 16)]))
        p.setBrush(QColor("#f0c419"))
        p.drawEllipse(12, 5, 4, 4)
    elif type_name == "ProgressBar":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 6, 18, 8)
        p.fillRect(2, 7, 10, 7, QColor("#2fb12f"))
    elif type_name == "NumericUpDown":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 4, 18, 12)
        p.drawText(2, 4, 10, 12, Qt.AlignmentFlag.AlignCenter, "12")
        p.drawLine(13, 4, 13, 16)
        p.drawLine(13, 10, 19, 10)
    elif type_name == "TrackBar":
        p.drawLine(2, 10, 18, 10)
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(8, 5, 4, 10)
    elif type_name == "Panel":
        p.setPen(QPen(QColor("#3c3c3c"), 1, Qt.PenStyle.DashLine))
        p.drawRect(2, 3, 16, 14)
    elif type_name == "GroupBox":
        p.drawRect(2, 6, 16, 12)
        p.fillRect(4, 3, 9, 6, QColor("#f0f0f0"))
        p.drawText(4, 1, 12, 9, Qt.AlignmentFlag.AlignLeft, "xy")
    elif type_name == "Timer":
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(2, 2, 16, 16)
        p.drawLine(10, 10, 10, 5)
        p.drawLine(10, 10, 14, 10)
    elif type_name == "MenuStrip":
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(1, 3, 18, 5)
        p.setBrush(QColor("#ffffff"))
        p.drawRect(3, 8, 10, 10)
        for y in (11, 14):
            p.drawLine(5, y, 11, y)
    else:
        _draw_new_icon(p, type_name)
    p.end()
    return QIcon(pm)


def _draw_new_icon(p: QPainter, type_name: str) -> None:
    """Icons of the controls added with the second control set (tabs, trees, grids, dialogs...)."""
    white, dark = QColor("#ffffff"), QColor("#3c3c3c")
    if type_name == "TabControl":
        p.setBrush(white)
        p.drawRect(2, 6, 16, 12)
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(2, 2, 7, 4)
        p.setBrush(white)
        p.drawRect(9, 3, 6, 3)
    elif type_name == "TreeView":
        p.drawLine(4, 4, 4, 15)
        p.drawLine(4, 9, 9, 9)
        p.drawLine(4, 15, 9, 15)
        p.setBrush(QColor("#f0c419"))
        for x, y in ((2, 2), (9, 7), (9, 13)):
            p.drawRect(x, y, 5, 4)
    elif type_name == "ListView":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.fillRect(2, 3, 17, 4, QColor("#dfe8f6"))
        for y in (10, 14):
            p.fillRect(3, y - 1, 3, 3, QColor("#4a78c2"))
            p.drawLine(8, y, 17, y)
    elif type_name == "DataGridView":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.fillRect(2, 3, 17, 4, QColor("#dfe8f6"))
        for x in (7, 13):
            p.drawLine(x, 2, x, 18)
        for y in (7, 12):
            p.drawLine(1, y, 19, y)
    elif type_name == "DateTimePicker":
        p.setBrush(white)
        p.drawRect(2, 4, 16, 14)
        p.fillRect(3, 5, 15, 4, QColor("#d9542b"))
        for x in (5, 9, 13):
            for y in (11, 15):
                p.fillRect(x, y - 1, 2, 2, dark)
    elif type_name == "LinkLabel":
        f = QFont("Segoe UI", 9)
        f.setUnderline(True)
        p.setFont(f)
        p.setPen(QColor("#0066cc"))
        p.drawText(0, 0, 20, 20, Qt.AlignmentFlag.AlignCenter, "A")
    elif type_name == "StatusBar":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.setBrush(QColor("#d4d0c8"))
        p.drawRect(1, 13, 18, 5)
        p.drawLine(12, 13, 12, 18)
    elif type_name == "ToolStrip":
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(1, 5, 18, 10)
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(3, 7, 5, 6)
        p.setBrush(QColor("#2fb12f"))
        p.drawRect(10, 7, 5, 6)
    elif type_name in ("OpenFileDialog", "FolderBrowserDialog"):
        p.setBrush(QColor("#f0c419"))
        p.drawPolygon(QPolygonF([QPointF(2, 6), QPointF(8, 6), QPointF(10, 8), QPointF(18, 8),
                                 QPointF(18, 17), QPointF(2, 17)]))
        if type_name == "OpenFileDialog":
            p.setBrush(white)
            p.drawRect(6, 2, 8, 9)
    elif type_name == "SaveFileDialog":
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(3, 3, 14, 14)
        p.setBrush(white)
        p.drawRect(6, 3, 8, 5)
        p.drawRect(5, 11, 10, 6)
    elif type_name == "ColorDialog":
        for i, c in enumerate(("#d9542b", "#2fb12f", "#4a78c2", "#f0c419")):
            p.setBrush(QColor(c))
            p.drawRect(2 + (i % 2) * 8, 2 + (i // 2) * 8, 7, 7)
    elif type_name == "FontDialog":
        p.setFont(QFont("Times New Roman", 11, QFont.Weight.Bold))
        p.drawText(0, 0, 13, 20, Qt.AlignmentFlag.AlignCenter, "A")
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(9, 4, 11, 16, Qt.AlignmentFlag.AlignCenter, "a")
    elif type_name == "ActiveX":
        p.setBrush(white)
        p.drawRect(2, 2, 16, 16)
        p.setPen(QColor("#d9542b"))
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.drawText(2, 2, 16, 16, Qt.AlignmentFlag.AlignCenter, "OCX")


# ---------------------------------------------------------------------------- component packages
# Item roles of the items this Toolbox makes (features may add their own items, e.g. user controls)
TB_ROLE = Qt.ItemDataRole.UserRole + 11       # "header" | "item" | "pointer"
CAT_ROLE = Qt.ItemDataRole.UserRole + 12      # Toolbox group of the item / header
HIDDEN_KEY = "toolbox/hidden_components"      # QSettings: control types hidden with Choose Items
COLLAPSED_KEY = "toolbox/collapsed_groups"
_ICON_CACHE: dict = {}


def package_icon(type_name: str) -> QIcon | None:
    """The icon file of a component package (None = no icon file: drawn icons are used)."""
    try:
        from .components import package_of
        pkg = package_of(type_name)
    except Exception:  # noqa: BLE001
        return None
    path = pkg.icon_path if pkg is not None and not pkg.builtin else None
    if path is None:
        return None
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError:
        return None
    if key not in _ICON_CACHE:
        icon = QIcon(str(path))
        _ICON_CACHE[key] = icon if not icon.isNull() else None
    return _ICON_CACHE[key]


def _component_icon() -> QIcon:
    """Generic icon of a component package without an icon file (a puzzle piece)."""
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#3c3c3c")))
    p.setBrush(QColor("#8FB8E8"))
    p.drawRoundedRect(3, 5, 13, 12, 2, 2)
    p.drawEllipse(7, 1, 6, 6)
    p.drawEllipse(13, 8, 6, 6)
    p.end()
    return QIcon(pm)


def _hidden_types() -> set[str]:
    try:
        from PyQt6.QtCore import QSettings
        v = QSettings().value(HIDDEN_KEY, [])
        return set(v if isinstance(v, list) else ([v] if v else []))
    except Exception:  # noqa: BLE001
        return set()


def set_hidden_types(names) -> None:
    from PyQt6.QtCore import QSettings
    QSettings().setValue(HIDDEN_KEY, sorted(set(names)))


def toolbox_groups(names) -> list[tuple[str, list[str]]]:
    """[(category, [control types])] in Toolbox order (VS 2005 groups first, package groups after)."""
    from .components import CATEGORY_ORDER, MISSING_CATEGORY
    groups: dict[str, list[str]] = {}
    for n in names:
        t = CONTROL_TYPES.get(n)
        if t is None or t.category == MISSING_CATEGORY:
            continue
        cat = t.category or ("Components" if t.nonvisual else "General")
        groups.setdefault(cat, []).append(n)

    def key(cat):
        if cat in CATEGORY_ORDER:
            return (0, CATEGORY_ORDER.index(cat), "")
        return (2 if cat == "General" else 1, 0, cat.lower())
    for cat, items in groups.items():
        pkgs = [getattr(CONTROL_TYPES[n], "package", None) for n in items]
        if any(p is not None and not p.builtin for p in pkgs):        # package groups: by order, then name
            items.sort(key=lambda n: (getattr(getattr(CONTROL_TYPES[n], "package", None), "order", 1000), n.lower()))
    return [(cat, groups[cat]) for cat in sorted(groups, key=key)]


class Toolbox(QListWidget):
    """VS-style Toolbox: Pointer, then the controls in collapsible groups (categories of the component
    packages' manifests), a search box, "Choose Items..." to hide/show controls. Features may insert their
    own items (they keep them; this class only rebuilds the items it marks with TB_ROLE)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(20, 20))
        self.setDragEnabled(True)
        self.setSpacing(1)
        # names are elided to the dock's width - never a horizontal scroll bar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setUniformItemSizes(True)
        from PyQt6.QtWidgets import QLineEdit
        self.search = QLineEdit(self)
        self.search.setObjectName("toolboxSearch")
        self.search.setPlaceholderText("Search Toolbox")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported))
        self.setViewportMargins(0, 26, 0, 0)
        self._headers: dict[str, QListWidgetItem] = {}
        self._collapsed: set[str] = set()
        try:
            from PyQt6.QtCore import QSettings
            v = QSettings().value(COLLAPSED_KEY, [])
            self._collapsed = set(v if isinstance(v, list) else ([v] if v else []))
        except Exception:  # noqa: BLE001
            pass
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemClicked.connect(self._on_clicked)
        self.rebuild()
        self.currentItemChanged.connect(self._on_current)
        TOOL_STATE.changed.connect(self._on_tool_reset)
        TOOL_STATE.modeChanged.connect(self._on_mode)
        TOOL_STATE.profileChanged.connect(lambda _p: self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported))
        TOOL_STATE.targetChanged.connect(lambda _t: self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported))
        try:
            from .components import REGISTRY
            REGISTRY.on_change(self._registry_changed)
        except Exception:  # noqa: BLE001
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.search.setGeometry(cr.x() + 2, cr.y() + 2, max(20, cr.width() - 4), 22)

    def _registry_changed(self) -> None:
        from PyQt6.QtCore import QThread, QTimer
        try:
            if QThread.currentThread() is self.thread():
                self.rebuild()
            else:
                QTimer.singleShot(0, self, self.rebuild)
        except RuntimeError:              # the Toolbox was deleted
            pass

    def _make_header(self, text: str, cat: str) -> QListWidgetItem:
        it = QListWidgetItem(text)
        f = it.font()
        f.setBold(True)
        it.setFont(f)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setSizeHint(QSize(10, 22))
        it.setData(TB_ROLE, "header")
        it.setData(CAT_ROLE, cat)
        return it

    def rebuild(self) -> None:
        """(Re)create this Toolbox's items from CONTROL_TYPES (after packages were installed / removed)."""
        current = TOOL_STATE.current
        self.blockSignals(True)
        foreign = []
        for row in reversed(range(self.count())):
            it = self.item(row)
            if it.data(TB_ROLE):
                self.takeItem(row)
            else:
                foreign.insert(0, self.takeItem(row))
        self._headers = {}
        pointer = QListWidgetItem(control_icon(POINTER), POINTER)
        pointer.setData(Qt.ItemDataRole.UserRole, POINTER)
        pointer.setData(TB_ROLE, "pointer")
        pointer.setSizeHint(QSize(10, 24))
        self.addItem(pointer)
        for it in foreign:                   # e.g. "<Project> Components" (user controls) right under Pointer
            self.addItem(it)
        mobile = [n for n in CONTROL_TYPES if n in MOBILE_CONTROL_TYPES]
        classic = [n for n in CONTROL_TYPES if n not in MOBILE_CONTROL_TYPES and not self._foreign_type(n)]
        groups = [(MOBILE_HEADER, mobile)] + toolbox_groups(classic)
        for cat, names in groups:
            if not names:
                continue
            head = self._make_header(cat, cat)
            self._headers[cat] = head
            self.addItem(head)
            for name in names:
                it = QListWidgetItem(self._icon(name), self._label(name))
                it.setData(Qt.ItemDataRole.UserRole, name)
                it.setData(TB_ROLE, "item")
                it.setData(CAT_ROLE, cat)
                it.setToolTip(self._tooltip(name))
                it.setSizeHint(QSize(10, 24))          # the row is as wide as the list, the text elides
                self.addItem(it)
        self.setCurrentRow(0)
        self.blockSignals(False)
        self._update_headers()
        self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported)
        if current is not None and current in CONTROL_TYPES:
            self.select_tool(current)

    @staticmethod
    def _foreign_type(name: str) -> bool:
        """User controls get their own group from radide/features/user_controls.py."""
        try:
            from .usercontrols import USER_CONTROLS
            return name in USER_CONTROLS
        except ImportError:
            return False

    @staticmethod
    def _icon(name: str) -> QIcon:
        icon = package_icon(name)
        if icon is not None:
            return icon
        t = CONTROL_TYPES.get(name)
        pkg = getattr(t, "package", None) if t is not None else None
        if pkg is not None and not pkg.builtin:
            return _component_icon()
        return control_icon(name)

    @staticmethod
    def _label(name: str) -> str:
        t = CONTROL_TYPES.get(name)
        pkg = getattr(t, "package", None) if t is not None else None
        return pkg.display_name if pkg is not None and not pkg.builtin else name

    @staticmethod
    def _tooltip(name: str) -> str:
        ctype = CONTROL_TYPES.get(name)
        text = f"{name}: {ctype.description}" if ctype is not None and ctype.description else name
        pkg = getattr(ctype, "package", None) if ctype is not None else None
        if pkg is not None and not pkg.builtin:
            text += f"\n{pkg.summary()}"
            if pkg.publisher:
                text += f" - {pkg.publisher}"
            try:                  # targets with / without a runtime (radide/components/targets.py)
                from .components.targets import support_text
                sup = support_text(pkg)
                if sup:
                    text += "\n" + sup
            except Exception:  # noqa: BLE001
                pass
        return text

    @staticmethod
    def _target_ok(name: str) -> tuple[bool, str]:
        """(usable, reason): a component package without a runtime for the shown form's language is greyed."""
        target = TOOL_STATE.target
        ctype = CONTROL_TYPES.get(name)
        pkg = getattr(ctype, "package", None) if ctype is not None else None
        if not target or pkg is None or pkg.builtin:
            return True, ""
        try:
            from .components.targets import supports
            if supports(pkg, target):
                return True, ""
        except Exception:  # noqa: BLE001
            return True, ""
        return False, (f"{name}: no runtime for {target} - the generated program would show a placeholder."
                       f"\n{Toolbox._tooltip(name)}")

    def select_tool(self, name: str) -> bool:
        for row in range(self.count()):
            it = self.item(row)
            if it.data(Qt.ItemDataRole.UserRole) == name and it.data(TB_ROLE) == "item":
                self.blockSignals(True)
                self.setCurrentRow(row)
                self.blockSignals(False)
                return True
        return False

    def _update_headers(self) -> None:
        for cat, head in self._headers.items():
            if head is None or head.data(CAT_ROLE) != cat:
                continue
            arrow = "\u25b8 " if cat in self._collapsed and not self.search.text().strip() else "\u25be "
            head.setText(arrow + cat)

    def toggle_group(self, cat: str) -> None:
        if cat in self._collapsed:
            self._collapsed.discard(cat)
        else:
            self._collapsed.add(cat)
        try:
            from PyQt6.QtCore import QSettings
            QSettings().setValue(COLLAPSED_KEY, sorted(self._collapsed))
        except Exception:  # noqa: BLE001
            pass
        self._update_headers()
        self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported)

    def _on_clicked(self, item) -> None:
        if item is not None and item.data(TB_ROLE) == "header":
            self.toggle_group(item.data(CAT_ROLE))

    def _on_mode(self, mobile: bool, supported) -> None:
        """Desktop forms: the classic controls only.  Phone forms: the Mobile group first and the
        Windows-only classic controls greyed (not available in mobile apps). The search box and collapsed
        groups filter the list; controls hidden with Choose Items are not shown."""
        from .mobile.controls import supported_controls
        allowed = set(supported) if supported else supported_controls(None)
        hidden = _hidden_types()
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        prof = TOOL_STATE.profile if not mobile else None
        visible_in: dict[str, int] = {}
        for row in range(self.count()):
            it = self.item(row)
            role = it.data(TB_ROLE)
            name = it.data(Qt.ItemDataRole.UserRole)
            if role is None:
                if name is None and not it.data(Qt.ItemDataRole.UserRole + 7):   # an old-style caption
                    it.setHidden(not mobile)
                continue                                   # items of features manage themselves
            if role in ("header", "pointer"):
                continue
            cat = it.data(CAT_ROLE)
            ctype = CONTROL_TYPES.get(name)
            desc = self._tooltip(name)
            if name in MOBILE_CONTROL_TYPES:
                hide = not mobile
                ok = True
            else:
                hide = False
                ok = not mobile or name in allowed
            tok, why = self._target_ok(name)
            if mobile and not ok and tok and TOOL_STATE.target and getattr(
                    getattr(ctype, "package", None), "builtin", True) is False:
                ok = True                                  # a package with a runtime for this mobile toolkit
            label =(prof.get("labels") or {}).get(name, self._label(name)) if prof else self._label(name)
            if it.text() != label:
                it.setText(label)
            if prof and prof.get("allowed") is not None and name not in prof["allowed"]:
                hide = True                                # e.g. no such control in Windows Forms
            if name in hidden or ctype is None:
                hide = True
            if query:
                hay = f"{name} {label} {ctype.description if ctype else ''} {cat}".lower()
                if query not in hay:
                    hide = True
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
                        if ok else Qt.ItemFlag.NoItemFlags)
            it.setToolTip(desc if ok else f"{name}: Windows only - not available in mobile apps.")
            if ok and not tok:                             # no runtime for the form's language: greyed
                it.setFlags(Qt.ItemFlag.NoItemFlags)
                it.setToolTip(why)
            if not hide:
                visible_in[cat] = visible_in.get(cat, 0) + 1
            if not hide and cat in self._collapsed and not query:
                hide = True
            it.setHidden(hide)
        for cat, head in self._headers.items():
            if head is None or head.data(CAT_ROLE) != cat:
                continue
            if cat == MOBILE_HEADER:
                head.setHidden(not mobile or not visible_in.get(cat))
            else:
                head.setHidden(not visible_in.get(cat))
        self._update_headers()
        if TOOL_STATE.current is not None and (TOOL_STATE.current not in CONTROL_TYPES or
                                               (mobile and TOOL_STATE.current not in allowed) or
                                               (not mobile and TOOL_STATE.current in MOBILE_CONTROL_TYPES)):
            TOOL_STATE.set(None)

    def _menu(self, pos) -> None:
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction("Choose &Items...", self.choose_items)
        m.addAction("Install Component &Package...", self.install_package)
        m.addSeparator()
        m.addAction("&Expand All", lambda: self._set_all_collapsed(False))
        m.addAction("&Collapse All", lambda: self._set_all_collapsed(True))
        m.addAction("&Show All Items", self.show_all)
        m.exec(self.viewport().mapToGlobal(pos))

    def _set_all_collapsed(self, on: bool) -> None:
        self._collapsed = {c for c in self._headers if c != MOBILE_HEADER} if on else set()
        self.toggle_group("\0")                       # saves and refreshes ("\0" is not a group)
        self._collapsed.discard("\0")

    def show_all(self) -> None:
        set_hidden_types([])
        self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported)

    def choose_items(self):
        from .components.ui import ChooseItemsDialog
        dlg = ChooseItemsDialog(self)
        if dlg.exec():
            self.rebuild()
        return dlg

    def install_package(self):
        from .components.ui import install_package_dialog
        return install_package_dialog(self)

    def _on_current(self, item, _prev):
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        TOOL_STATE.set(None if name == POINTER else name)

    def _on_tool_reset(self, tool):
        if tool is None and self.currentRow() != 0:
            self.blockSignals(True)
            self.setCurrentRow(0)
            self.blockSignals(False)

    def startDrag(self, actions):
        item = self.currentItem()
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name is None or name == POINTER:
            return
        mime = QMimeData()
        mime.setData(MIME, name.encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(item.icon().pixmap(20, 20))
        drag.exec(Qt.DropAction.CopyAction)
