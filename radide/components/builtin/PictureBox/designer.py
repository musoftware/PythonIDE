"""PictureBox on the design surface: the Image (relative to the project folder), else the control name in a
dashed design-time outline."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QLabel(parent))


def set_image(w: QLabel, path: str, name: str) -> None:
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


def _image(w, p, ctx):
    set_image(w, p.get("Image", ""), ctx.name)


def _rules(p):
    return [] if p.get("Image") else ["border:1px dashed #7f7f7f;"]


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_image, rules=_rules)
