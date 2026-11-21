"""RatingBar - python-qt (PySide6) runtime of the RatingBar component package."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget


class RatingBar(QWidget):
    def __init__(self, parent=None, Value=3, MaxStars=5, ReadOnly=False, StarColor="#FFB400",
                 EmptyColor="#C8CDD5", Enabled=True, **_ignored):
        super().__init__(parent)
        self._handlers = {}
        self._max = max(1, min(10, int(MaxStars)))
        self._value = max(0, min(self._max, int(Value)))
        self.ReadOnly = bool(ReadOnly)
        self._on, self._off = QColor(StarColor or "#FFB400"), QColor(EmptyColor or "#C8CDD5")
        self.setEnabled(bool(Enabled))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event):
        fn = self._handlers.get(event)
        if fn is not None:
            fn()

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        v = max(0, min(self._max, int(v or 0)))
        if v != self._value:
            self._value = v
            self.update()
            self._raise("ValueChanged")

    @property
    def MaxStars(self):
        return self._max

    @MaxStars.setter
    def MaxStars(self, n):
        self._max = max(1, min(10, int(n)))
        self._value = min(self._value, self._max)
        self.update()

    def Reset(self):
        self.Value = 0

    def SetValue(self, value):
        self.Value = value

    def _star(self):
        return max(6.0, min(self.height() - 2.0, self.width() / self._max - 2.0))

    def paintEvent(self, _e):
        p = QPainter(self)
        s = self._star()
        f = QFont("Segoe UI Symbol")
        f.setPixelSize(int(s))
        p.setFont(f)
        for i in range(self._max):
            on = i < self._value
            c = (self._on if on else self._off) if self.isEnabled() else QColor("#B0B0B0" if on else "#E0E0E0")
            p.setPen(c)
            p.drawText(int(i * (s + 2)), 0, int(s + 2), self.height(), Qt.AlignmentFlag.AlignCenter, "★")
        p.end()

    def mousePressEvent(self, e):
        if self.ReadOnly or not self.isEnabled():
            return
        i = int(e.position().x() // (self._star() + 2)) + 1
        if 1 <= i <= self._max:
            self.Value = 0 if i == self._value == 1 else i
