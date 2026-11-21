"""StarRating - custom Properties window editors.

``EDITORS`` maps the ``editor`` ids used in component.json to editor objects. An editor has either

* ``create(parent, value, commit, ctx) -> QWidget`` (+ optional ``set_value(widget, value, ctx)``): an inline
  editor that lives in the value cell and calls ``commit(new_value)``; or
* ``edit(parent, value, ctx) -> new value | None``: a modal editor opened by the cell's "..." button.

``ctx`` has ``name`` (property), ``props`` (the control's values), ``control``, ``form``, ``project_folder``,
``propdef`` and ``package``.
"""
from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSpinBox, QVBoxLayout, QWidget

_DESIGNER = None


def _star_path(rect, shape):
    """The same drawing as the designer (designer.py next to this file)."""
    global _DESIGNER
    if _DESIGNER is None:
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location("_starrating_designer",
                                                      pathlib.Path(__file__).with_name("designer.py"))
        _DESIGNER = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_DESIGNER)
    return _DESIGNER.star_path(rect, shape)


class StarPicker(QWidget):
    """Clickable stars: click a star to set the value, click the first selected star again for 0."""
    valueChanged = pyqtSignal(int)

    def __init__(self, value=0, count=5, color="#FFB400", parent=None):
        super().__init__(parent)
        self.value, self.count, self.color = int(value or 0), int(count or 5), color
        self.setMinimumHeight(18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click a star to set the rating")

    def set_value(self, v):
        self.value = max(0, min(self.count, int(v or 0)))
        self.update()

    def _size(self):
        return max(8, min(self.height() - 4, 16))

    def mousePressEvent(self, e):
        s = self._size() + 2
        i = int(e.position().x() // s) + 1
        if 1 <= i <= self.count:
            new = 0 if i == self.value == 1 else i
            self.set_value(new)
            self.valueChanged.emit(self.value)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size()
        for i in range(self.count):
            c = QColor(self.color) if i < self.value else QColor("#C8CDD5")
            p.setPen(QPen(c.darker(130), 1))
            p.setBrush(c)
            p.drawPath(_star_path(QRectF(2 + i * (s + 2), (self.height() - s) / 2, s, s), "Star"))
        p.setPen(QColor("#404040"))
        p.drawText(QRectF(4 + self.count * (s + 2), 0, 40, self.height()), Qt.AlignmentFlag.AlignVCenter,
                   str(self.value))
        p.end()


class StarsEditor:
    """Inline editor of StarRating.Value (the stars themselves)."""

    def create(self, parent, value, commit, ctx):
        props = getattr(ctx, "props", {}) or {}
        w = StarPicker(value, props.get("MaxStars", 5), props.get("StarColor") or "#FFB400", parent)
        w.valueChanged.connect(commit)
        return w

    def set_value(self, widget, value, ctx):
        props = getattr(ctx, "props", {}) or {}
        widget.count = max(1, int(props.get("MaxStars", 5) or 5))
        widget.color = props.get("StarColor") or "#FFB400"
        widget.set_value(value)


def edit_value_dialog(parent, value, ctx):
    """A modal editor (example of the second editor style): a number box."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Star Rating Value")
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("Rating:"))
    spin = QSpinBox()
    spin.setRange(0, int((getattr(ctx, "props", {}) or {}).get("MaxStars", 5) or 5))
    spin.setValue(int(value or 0))
    lay.addWidget(spin)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)
    return spin.value() if dlg.exec() else None


EDITORS = {"starrating.stars": StarsEditor(), "starrating.dialog": edit_value_dialog}
