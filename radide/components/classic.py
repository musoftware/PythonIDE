"""The look shared by the built-in (VB-style) controls on the design surface.

Every built-in package's ``designer.py`` (radide/components/builtin/<Name>/designer.py) builds its own Qt widget
in ``create()`` and calls :func:`apply_classic` from ``apply()``: the common properties (text, alignment,
Checked, Items, Minimum/Maximum/Value, font, colours, Enabled ...) are applied here the same way for every
control, the package adds what only it has:

* ``special(widget, props, ctx)`` - replaces the generic "set the text" step (TabControl tabs, TreeView nodes,
  a PictureBox image ...);
* ``rules`` - extra style-sheet declarations (a Panel's dashed design-time outline, a LinkLabel's colour ...).

Third-party packages may use it too, to look like the built-in controls.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QGroupBox, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
                             QProgressBar, QRadioButton, QSlider, QSpinBox, QWidget)

from ..controls import split_items

ALIGN = {"Left": Qt.AlignmentFlag.AlignLeft, "Center": Qt.AlignmentFlag.AlignHCenter,
         "Right": Qt.AlignmentFlag.AlignRight}


def form_palette(w: QWidget) -> None:
    """A designed control always looks like the real (light) program, in any IDE theme."""
    from ..theme import light_form_palette
    pal = light_form_palette()
    for x in [w, *w.findChildren(QWidget)]:
        x.setPalette(pal)


def prepare(w: QWidget) -> QWidget:
    """Design-time flags of a freshly created preview widget (no focus; the overlay owns the mouse)."""
    w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    for child in w.findChildren(QWidget):
        child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return w


def apply_classic(w: QWidget, p: dict, ctx, special=None, rules=()) -> None:
    """Apply the common properties *p* to the preview widget *w* (see the module doc)."""
    align = ALIGN.get(p.get("TextAlign", ""), None)
    if special is not None:
        special(w, p, ctx)
    elif isinstance(w, QGroupBox):
        w.setTitle(str(p.get("Text", "")))
    elif isinstance(w, QPlainTextEdit):
        w.setPlainText(str(p.get("Text", "")))
    elif hasattr(w, "setText") and "Text" in p:
        w.setText(str(p["Text"]))
    if align is not None and isinstance(w, (QLabel, QLineEdit)):
        w.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    if isinstance(w, (QCheckBox, QRadioButton)):
        w.setChecked(bool(p.get("Checked")))
    if isinstance(w, (QListWidget, QComboBox)):
        w.clear()
        w.addItems(split_items(p.get("Items", "")) or [ctx.name])
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
    css = []
    if p.get("BackColor"):
        css.append(f"background-color:{p['BackColor']};")
    if p.get("ForeColor"):
        css.append(f"color:{p['ForeColor']};")
    css += list(rules(p) if callable(rules) else rules)
    sel = f"#{w.objectName()}"
    form_palette(w)
    w.setStyleSheet(f"{sel} {{{''.join(css)}}}" if css else "")
    w.setEnabled(bool(p.get("Enabled", True)))


__all__ = ["ALIGN", "apply_classic", "form_palette", "prepare"]
