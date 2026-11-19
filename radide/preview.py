"""Qt widgets used to *preview* neutral controls on the design surface."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, QDateTime, QPoint, Qt, QTime
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateTimeEdit, QFrame,
                             QGraphicsOpacityEffect, QGroupBox, QHeaderView, QLabel, QLineEdit,
                             QListWidget, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton,
                             QSlider, QSpinBox, QTabBar, QTableWidget, QTableWidgetItem, QTreeWidget,
                             QTreeWidgetItem, QWidget)

from .controls import TAB_PAGE_X, TAB_PAGE_Y, split_items, split_rows, tree_paths
from .model import Control


class TabControlPreview(QWidget):
    """Design-time TabControl: a tab bar, a page frame and a transparent *client*
    widget (the page area) that hosts the previews of the controls on the pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bar = QTabBar(self)
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.page = QFrame(self)
        self.page.setFrameShape(QFrame.Shape.StyledPanel)
        self.page.setObjectName("rad_page")
        self.page.setStyleSheet("#rad_page { background:#FCFCFE; border:1px solid #919B9C; }")
        self.client = QWidget(self)
        self.client.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.bar.raise_()

    def set_tabs(self, captions: list[str], current: int) -> None:
        self.bar.blockSignals(True)
        while self.bar.count() > len(captions):
            self.bar.removeTab(self.bar.count() - 1)
        for i, text in enumerate(captions):
            if i < self.bar.count():
                self.bar.setTabText(i, text)
            else:
                self.bar.addTab(text)
        if 0 <= current < self.bar.count():
            self.bar.setCurrentIndex(current)
        self.bar.blockSignals(False)
        self._layout()

    def tab_at(self, pos: QPoint) -> int:
        """Index of the tab under *pos* (in this widget's coordinates), or -1."""
        return self.bar.tabAt(pos - self.bar.pos())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout()

    def _layout(self):
        w, h = self.width(), self.height()
        bh = min(self.bar.sizeHint().height(), TAB_PAGE_Y)
        self.bar.setGeometry(2, TAB_PAGE_Y - bh, max(10, w - 4), bh)
        self.page.setGeometry(0, TAB_PAGE_Y - 2, w, max(4, h - TAB_PAGE_Y + 2))
        self.client.setGeometry(TAB_PAGE_X, TAB_PAGE_Y, max(1, w - 2 * TAB_PAGE_X),
                                max(1, h - TAB_PAGE_Y - TAB_PAGE_X))


def _tree(parent):
    w = QTreeWidget(parent)
    w.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return w


def _grid(parent):
    w = QTableWidget(parent)
    w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    w.verticalHeader().setDefaultSectionSize(20)
    return w


def _datetime(parent):
    w = QDateTimeEdit(parent)
    w.setCalendarPopup(True)
    return w


def _label(parent):
    return QLabel(parent)

_FACTORY = {
    "Button": QPushButton, "Label": QLabel, "TextBox": QLineEdit,
    "CheckBox": QCheckBox, "RadioButton": QRadioButton,
    "ListBox": QListWidget, "ComboBox": QComboBox,
    "Panel": QFrame, "GroupBox": QGroupBox, "PictureBox": QLabel,
    "ProgressBar": QProgressBar, "NumericUpDown": QSpinBox,
    "TrackBar": lambda parent: QSlider(Qt.Orientation.Horizontal, parent),
    "TabControl": TabControlPreview, "TreeView": _tree, "ListView": _tree, "DataGridView": _grid,
    "DateTimePicker": _datetime, "LinkLabel": _label, "StatusBar": _label, "ActiveX": _label,
}
DATE_FORMAT = {"Short": "yyyy-MM-dd", "Long": "dddd, dd MMMM yyyy", "Time": "HH:mm:ss"}
ALIGN = {"Left": Qt.AlignmentFlag.AlignLeft, "Center": Qt.AlignmentFlag.AlignHCenter,
         "Right": Qt.AlignmentFlag.AlignRight}
# properties whose change needs a different preview widget class
REBUILD_PROPS = {"Multiline"}


def make_preview(ctrl: Control, parent: QWidget, root: Path | None = None) -> QWidget:
    if ctrl.type == "TextBox" and ctrl.props.get("Multiline"):
        w = QPlainTextEdit(parent)
    else:
        w = _FACTORY[ctrl.type](parent)
    w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    for child in w.findChildren(QWidget):
        child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    w.setProperty("rad_root", str(root) if root else "")
    if isinstance(w, QRadioButton):
        w.setAutoExclusive(False)
    apply_props(w, ctrl)
    w.show()
    return w


def _form_palette(w: QWidget) -> None:
    from .theme import light_form_palette
    pal = light_form_palette()
    for x in [w, *w.findChildren(QWidget)]:
        x.setPalette(pal)


def apply_props(w: QWidget, ctrl: Control) -> None:
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    w.setGeometry(int(p["Left"]), int(p["Top"]), max(4, int(p["Width"])), max(4, int(p["Height"])))
    align = ALIGN.get(p.get("TextAlign", ""), None)
    if ctrl.type in _SPECIAL:
        _SPECIAL[ctrl.type](w, p, ctrl)
    elif isinstance(w, QGroupBox):
        w.setTitle(str(p.get("Text", "")))
    elif isinstance(w, QPlainTextEdit):
        w.setPlainText(str(p.get("Text", "")))
    elif ctrl.type == "PictureBox":
        _set_image(w, p.get("Image", ""), ctrl.name)
    elif hasattr(w, "setText") and "Text" in p:
        w.setText(str(p["Text"]))
    if align is not None and isinstance(w, (QLabel, QLineEdit)):
        w.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    if isinstance(w, (QCheckBox, QRadioButton)):
        w.setChecked(bool(p.get("Checked")))
    if isinstance(w, (QListWidget, QComboBox)):
        w.clear()
        w.addItems(split_items(p.get("Items", "")) or [ctrl.name])
    if isinstance(w, (QProgressBar, QSpinBox, QSlider)):
        w.setRange(int(p.get("Minimum", 0)), int(p.get("Maximum", 100)))
        w.setValue(int(p.get("Value", 0)))
    if isinstance(w, QLineEdit):
        w.setEchoMode(QLineEdit.EchoMode.Password if p.get("PasswordChar") else QLineEdit.EchoMode.Normal)
    f = QFont(p.get("FontName") or "Segoe UI")
    f.setPointSize(max(1, int(p.get("FontSize", 9))))
    f.setBold(bool(p.get("FontBold")))
    f.setItalic(bool(p.get("FontItalic")))
    w.setFont(f)
    rules = []
    if p.get("BackColor"):
        rules.append(f"background-color:{p['BackColor']};")
    if p.get("ForeColor"):
        rules.append(f"color:{p['ForeColor']};")
    if ctrl.type == "Panel" or (ctrl.type == "PictureBox" and not p.get("Image")):
        rules.append("border:1px dashed #7f7f7f;")   # design-time outline (like VB)
    if ctrl.type == "LinkLabel":
        rules.append(f"color:{p.get('LinkColor') or '#0066CC'}; text-decoration:underline;")
    elif ctrl.type == "StatusBar":
        rules.append("border:1px solid #A0A0A0; border-top-color:#808080; padding-left:4px;"
                     + ("" if p.get("BackColor") else "background-color:#ECE9D8;"))
    elif ctrl.type == "ActiveX":
        rules.append("border:1px solid #808080; color:#505050;"
                     + ("" if p.get("BackColor") else "background-color:#ffffff;"))
    if ctrl.type == "Button" and p.get("TextAlign", "Center") != "Center":
        rules.append(f"text-align:{p['TextAlign'].lower()};")
    sel = f"#{w.objectName()}"
    _form_palette(w)       # a designed control always looks like the real (light) program, in any IDE theme
    w.setStyleSheet(f"{sel} {{{''.join(rules)}}}" if rules else "")
    w.setEnabled(bool(p.get("Enabled", True)))
    w.setToolTip(str(p.get("ToolTip", "")))
    # invisible controls stay visible at design time (like VB), but faded
    w.setGraphicsEffect(None)
    if not p.get("Visible", True):
        eff = QGraphicsOpacityEffect(w)
        eff.setOpacity(0.4)
        w.setGraphicsEffect(eff)


def _set_image(w: QLabel, path: str, name: str) -> None:
    root = w.property("rad_root") or ""
    pm = QPixmap()
    if path:
        full = Path(path) if Path(path).is_absolute() else Path(root) / path
        pm = QPixmap(str(full))
    if pm.isNull():
        w.setPixmap(QPixmap())
        w.setText(name)
        w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    else:
        w.setText("")
        w.setPixmap(pm)


# ------------------------------------------------------------------ new controls
def _tabcontrol(w: TabControlPreview, p: dict, _ctrl) -> None:
    w.set_tabs(split_items(p.get("TabPages", "")) or ["TabPage1"], int(p.get("SelectedIndex", 0) or 0))


def _treeview(w: QTreeWidget, p: dict, ctrl) -> None:
    w.clear()
    w.setHeaderHidden(True)
    w.setColumnCount(1)
    items: dict[str, QTreeWidgetItem] = {}
    for path, text in tree_paths(p.get("Nodes", "")):
        parent = items.get(path.rpartition("/")[0])
        it = QTreeWidgetItem([text])
        (parent.addChild(it) if parent is not None else w.addTopLevelItem(it))
        items[path] = it
    if not items:
        w.addTopLevelItem(QTreeWidgetItem([ctrl.name]))
    w.expandAll()


def _listview(w: QTreeWidget, p: dict, _ctrl) -> None:
    w.clear()
    cols = split_items(p.get("Columns", "")) or ["Column1"]
    details = p.get("View", "Details") == "Details"
    w.setColumnCount(len(cols) if details else 1)
    w.setHeaderLabels(cols if details else cols[:1])
    w.setHeaderHidden(not details)
    w.setRootIsDecorated(False)
    for row in split_rows(p.get("Items", "")):
        w.addTopLevelItem(QTreeWidgetItem(row if details else row[:1]))


def _datagrid(w: QTableWidget, p: dict, _ctrl) -> None:
    cols = split_items(p.get("Columns", "")) or ["Column1"]
    rows = split_rows(p.get("Rows", ""))
    w.clear()
    w.setColumnCount(len(cols))
    w.setHorizontalHeaderLabels(cols)
    w.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, cell in enumerate(row[:len(cols)]):
            w.setItem(r, c, QTableWidgetItem(cell))
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def _datetimepicker(w: QDateTimeEdit, p: dict, _ctrl) -> None:
    fmt = p.get("Format", "Short")
    w.setDisplayFormat(DATE_FORMAT.get(fmt, DATE_FORMAT["Short"]))
    value = str(p.get("Value") or "").strip()
    dt = QDateTime.currentDateTime()
    if value:
        d = QDate.fromString(value[:10], "yyyy-MM-dd")
        t = QTime.fromString(value[-8:], "HH:mm:ss")
        if d.isValid():
            dt.setDate(d)
        if t.isValid():
            dt.setTime(t)
    w.setDateTime(dt)


def _text_label(w: QLabel, p: dict, _ctrl) -> None:
    w.setText(str(p.get("Text", "")))
    w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


def _activex(w: QLabel, p: dict, _ctrl) -> None:
    w.setText(f"ActiveX\n{p.get('ProgID', '')}")
    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.setWordWrap(True)


_SPECIAL = {"TabControl": _tabcontrol, "TreeView": _treeview, "ListView": _listview,
            "DataGridView": _datagrid, "DateTimePicker": _datetimepicker, "LinkLabel": _text_label,
            "StatusBar": _text_label, "ActiveX": _activex}
