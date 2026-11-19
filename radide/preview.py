"""Qt widgets used to *preview* neutral controls on the design surface."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGraphicsOpacityEffect, QGroupBox,
                             QLabel, QLineEdit, QListWidget, QPlainTextEdit, QProgressBar,
                             QPushButton, QRadioButton, QSlider, QSpinBox, QWidget)

from .controls import split_items
from .model import Control

_FACTORY = {
    "Button": QPushButton, "Label": QLabel, "TextBox": QLineEdit,
    "CheckBox": QCheckBox, "RadioButton": QRadioButton,
    "ListBox": QListWidget, "ComboBox": QComboBox,
    "Panel": QFrame, "GroupBox": QGroupBox, "PictureBox": QLabel,
    "ProgressBar": QProgressBar, "NumericUpDown": QSpinBox,
    "TrackBar": lambda parent: QSlider(Qt.Orientation.Horizontal, parent),
}
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
    w.setProperty("rad_root", str(root) if root else "")
    if isinstance(w, QRadioButton):
        w.setAutoExclusive(False)
    apply_props(w, ctrl)
    w.show()
    return w


def apply_props(w: QWidget, ctrl: Control) -> None:
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    w.setGeometry(int(p["Left"]), int(p["Top"]), max(4, int(p["Width"])), max(4, int(p["Height"])))
    align = ALIGN.get(p.get("TextAlign", ""), None)
    if isinstance(w, QGroupBox):
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
    if ctrl.type == "Button" and p.get("TextAlign", "Center") != "Center":
        rules.append(f"text-align:{p['TextAlign'].lower()};")
    sel = f"#{w.objectName()}"
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
