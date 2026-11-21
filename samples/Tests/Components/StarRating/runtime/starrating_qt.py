"""StarRating - python-qt (PySide6) runtime of the StarRating component package.

Copied into the project by RAD IDE. The generated form code does::

    self.Rating1 = StarRating(parent, Value=3, MaxStars=5, ...)
    self.Rating1.rad_bind("ValueChanged", callback)

Use it from code like any control: ``self.Rating1.Value = 4``, ``self.Rating1.Reset()``.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


def _padding(value):
    nums = [int(float(x)) for x in str(value or "0").replace(",", " ").split() if x.strip()] or [0]
    if len(nums) == 1:
        nums = nums * 4
    elif len(nums) == 2:
        nums = nums * 2
    elif len(nums) == 3:
        nums.append(nums[1])
    return nums[:4]


class StarRating(QWidget):
    valueChanged = Signal(int)

    def __init__(self, parent=None, Value=0, MaxStars=5, ReadOnly=False, StarColor="#FFB400",
                 EmptyColor="#C8CDD5", Shape="Star", Spacing=4, Padding="2, 2, 2, 2", ShowValue=False,
                 BackColor="", ForeColor="", FontName="Segoe UI", FontSize=9, FontBold=False, FontItalic=False,
                 Enabled=True, **_ignored):
        super().__init__(parent)
        self._handlers = {}
        self._max = max(1, min(10, int(MaxStars)))
        self._value = max(0, min(self._max, int(Value)))
        self.ReadOnly = bool(ReadOnly)
        self._star, self._empty = QColor(StarColor or "#FFB400"), QColor(EmptyColor or "#C8CDD5")
        self._shape, self._spacing, self._padding = Shape, int(Spacing), _padding(Padding)
        self._show_value = bool(ShowValue)
        self._back = QColor(BackColor) if BackColor else None
        self._fore = QColor(ForeColor or "#404040")
        f = QFont(FontName or "Segoe UI", int(FontSize or 9))
        f.setBold(bool(FontBold))
        f.setItalic(bool(FontItalic))
        self.setFont(f)
        self.setEnabled(bool(Enabled))
        self.HoverValue = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ------------------------------------------------------------ events
    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event, *args):
        fn = self._handlers.get(event)
        if fn is not None:
            fn(*args)

    # ------------------------------------------------------------ properties
    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        v = max(0, min(self._max, int(v or 0)))
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(v)
            self._raise("ValueChanged")

    @property
    def MaxStars(self):
        return self._max

    @MaxStars.setter
    def MaxStars(self, n):
        self._max = max(1, min(10, int(n)))
        self._value = min(self._value, self._max)
        self.update()

    @property
    def StarColor(self):
        return self._star.name()

    @StarColor.setter
    def StarColor(self, c):
        self._star = QColor(c)
        self.update()

    @property
    def Enabled(self):
        return self.isEnabled()

    @Enabled.setter
    def Enabled(self, on):
        self.setEnabled(bool(on))
        self.update()

    # ------------------------------------------------------------ methods
    def Reset(self):
        self.Value = 0

    def SetValue(self, value):
        self.Value = value

    # ------------------------------------------------------------ drawing / input
    def _cells(self):
        left, top, right, bottom = self._padding
        text_w = 34 if self._show_value else 0
        h = self.height() - top - bottom
        size = max(4.0, min(h, (self.width() - left - right - text_w - self._spacing * (self._max - 1)) / self._max))
        return [QRectF(left + i * (size + self._spacing), top + (h - size) / 2, size, size)
                for i in range(self._max)]

    def _path(self, r):
        path = QPainterPath()
        if self._shape == "Circle":
            path.addEllipse(r.adjusted(1, 1, -1, -1))
        elif self._shape == "Square":
            path.addRoundedRect(r.adjusted(1, 1, -1, -1), 2, 2)
        else:
            cx, cy, outer = r.center().x(), r.center().y(), min(r.width(), r.height()) / 2
            for i in range(10):
                rad = outer if i % 2 == 0 else outer * 0.45
                a = -math.pi / 2 + i * math.pi / 5
                pt = QPointF(cx + rad * math.cos(a), cy + rad * math.sin(a))
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            path.closeSubpath()
        return path

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._back is not None:
            p.fillRect(self.rect(), self._back)
        cells = self._cells()
        for i, r in enumerate(cells):
            on = i < self._value
            if not self.isEnabled():
                c = QColor("#B0B0B0") if on else QColor("#E0E0E0")
            elif not on and not self.ReadOnly and i < self.HoverValue:
                c = self._star.lighter(130)
            else:
                c = self._star if on else self._empty
            p.setPen(QPen(c.darker(130), 1))
            p.setBrush(c)
            p.drawPath(self._path(r))
        if self._show_value and cells:
            p.setPen(self._fore)
            x = cells[-1].right() + self._spacing
            p.drawText(QRectF(x, 0, 40, self.height()), Qt.AlignmentFlag.AlignVCenter, f"{self._value}/{self._max}")
        p.end()

    def _star_at(self, x):
        for i, r in enumerate(self._cells()):
            if r.left() <= x < r.right() + self._spacing:
                return i + 1
        return 0

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self.ReadOnly or not self.isEnabled():
            return
        i = self._star_at(e.position().x())
        if i:
            self.Value = 0 if i == self._value == 1 else i

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        i = self._star_at(e.position().x())
        if i != self.HoverValue:
            self.HoverValue = i
            self.update()
            self._raise("Hover")

    def leaveEvent(self, e):
        super().leaveEvent(e)
        if self.HoverValue:
            self.HoverValue = 0
            self.update()
            self._raise("Hover")
