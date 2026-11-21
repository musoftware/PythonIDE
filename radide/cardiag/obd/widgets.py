"""Painted widgets of the scan tool: a round gauge, a time-series graph and the MIL (check-engine) lamp.
Colours come from the widget palette, so they follow the IDE's light / dark theme."""
from __future__ import annotations

import math
from collections import deque

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

SERIES_COLORS = ["#2f7ed8", "#e4572e", "#29a35a", "#a05cd6", "#d6a400", "#14a3b8", "#d94f8a", "#6b8e23"]


def _tr(text: str) -> str:
    try:
        from ...i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def fmt(v, digits=None) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        a = abs(v)
        d = digits if digits is not None else (0 if a >= 1000 else 1 if a >= 100 else 2)
        s = f"{v:.{d}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(v)


class Gauge(QWidget):
    """Round dial: 270° arc, value text, unit, label; a red band near the top of the range."""

    def __init__(self, label="", unit="", lo=0.0, hi=100.0, parent=None):
        super().__init__(parent)
        self.label, self.unit, self.lo, self.hi = label, unit, float(lo), float(hi if hi > lo else lo + 1)
        self.value: float | None = None
        self.vmin: float | None = None
        self.vmax: float | None = None
        self.red_from: float | None = None
        self.setMinimumSize(150, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):  # noqa: N802 - Qt API
        return QSize(190, 190)

    def set_value(self, v) -> None:
        self.value = v
        if v is not None:
            self.vmin = v if self.vmin is None else min(self.vmin, v)
            self.vmax = v if self.vmax is None else max(self.vmax, v)
        self.update()

    def reset(self) -> None:
        self.value = self.vmin = self.vmax = None
        self.update()

    def _angle(self, v: float) -> float:
        f = (min(max(v, self.lo), self.hi) - self.lo) / (self.hi - self.lo)
        return 225.0 - 270.0 * f

    def paintEvent(self, _e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        fg = pal.color(pal.ColorRole.WindowText)
        base = pal.color(pal.ColorRole.Base)
        mid = pal.color(pal.ColorRole.Mid)
        acc = pal.color(pal.ColorRole.Highlight)
        side = min(self.width(), self.height()) - 12
        r = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        p.setPen(QPen(mid, 1))
        p.setBrush(base)
        p.drawEllipse(r)
        arc = r.adjusted(side * 0.09, side * 0.09, -side * 0.09, -side * 0.09)
        w = max(4.0, side * 0.06)
        p.setPen(QPen(mid, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawArc(arc, int(-45 * 16), int(270 * 16))
        if self.red_from is not None and self.red_from < self.hi:
            a0 = self._angle(self.red_from)
            p.setPen(QPen(QColor("#d64545"), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(arc, int(-45 * 16), int((a0 + 45) * 16))
        if self.value is not None:
            a = self._angle(self.value)
            p.setPen(QPen(acc, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(arc, int(a * 16), int((225 - a) * 16))
        # ticks + scale numbers
        c = r.center()
        rad = arc.width() / 2
        f = QFont(self.font())
        f.setPointSizeF(max(6.0, side / 26))
        p.setFont(f)
        p.setPen(QPen(fg, 1))
        for i in range(6):
            v = self.lo + (self.hi - self.lo) * i / 5
            ang = math.radians(self._angle(v))
            p1 = QPointF(c.x() + math.cos(ang) * (rad - w), c.y() - math.sin(ang) * (rad - w))
            p2 = QPointF(c.x() + math.cos(ang) * (rad - w * 2), c.y() - math.sin(ang) * (rad - w * 2))
            p.drawLine(p1, p2)
            tp = QPointF(c.x() + math.cos(ang) * (rad - w * 3.6), c.y() - math.sin(ang) * (rad - w * 3.6))
            p.drawText(QRectF(tp.x() - 30, tp.y() - 8, 60, 16), Qt.AlignmentFlag.AlignCenter, fmt(float(v), 0))
        # needle
        if self.value is not None:
            ang = math.radians(self._angle(self.value))
            tip = QPointF(c.x() + math.cos(ang) * (rad - w * 1.2), c.y() - math.sin(ang) * (rad - w * 1.2))
            p.setPen(QPen(QColor("#d64545"), max(2.0, side / 90)))
            p.drawLine(c, tip)
        p.setBrush(fg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(c, side * 0.025, side * 0.025)
        # texts
        p.setPen(fg)
        fv = QFont(self.font())
        fv.setPointSizeF(max(8.0, side / 11))
        fv.setBold(True)
        p.setFont(fv)
        p.drawText(QRectF(r.left(), c.y() + side * 0.10, r.width(), side * 0.16), Qt.AlignmentFlag.AlignCenter,
                   fmt(self.value))
        f2 = QFont(self.font())
        f2.setPointSizeF(max(6.5, side / 24))
        p.setFont(f2)
        p.drawText(QRectF(r.left(), c.y() + side * 0.25, r.width(), side * 0.1), Qt.AlignmentFlag.AlignCenter,
                   self.unit)
        p.drawText(QRectF(r.left() + side * 0.15, c.y() - side * 0.30, r.width() - side * 0.3, side * 0.12),
                   Qt.AlignmentFlag.AlignCenter, self.label)
        p.end()


class Plot(QWidget):
    """Scrolling time graph of several channels; each one is scaled to its own range (shown in the legend)."""

    def __init__(self, parent=None, window: float = 60.0):
        super().__init__(parent)
        self.window = window
        self.series: dict = {}      # key -> {"label", "unit", "lo", "hi", "pts": deque[(t, v)], "color"}
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_channels(self, chans: list[tuple]) -> None:
        """chans: [(key, label, unit, lo, hi)] - keeps the points of channels that stay."""
        old = self.series
        self.series = {}
        for i, (k, lab, unit, lo, hi) in enumerate(chans):
            s = old.get(k) or {"pts": deque(maxlen=5000)}
            s.update(label=lab, unit=unit, lo=float(lo), hi=float(hi if hi > lo else lo + 1),
                     color=SERIES_COLORS[i % len(SERIES_COLORS)])
            self.series[k] = s
        self.update()

    def add(self, key, t: float, v) -> None:
        s = self.series.get(key)
        if s is not None and v is not None:
            s["pts"].append((t, float(v)))

    def clear(self) -> None:
        for s in self.series.values():
            s["pts"].clear()
        self.update()

    def paintEvent(self, _e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.color(pal.ColorRole.Base))
        fg = pal.color(pal.ColorRole.WindowText)
        grid = pal.color(pal.ColorRole.Mid)
        legend_h = 18 * ((len(self.series) + 1) // 2) + 6
        area = QRectF(44, 8, self.width() - 56, self.height() - 30 - legend_h)
        if area.width() < 20 or area.height() < 20:
            p.end()
            return
        p.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
        for i in range(5):
            y = area.top() + area.height() * i / 4
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
        tmax = max((s["pts"][-1][0] for s in self.series.values() if s["pts"]), default=0.0)
        t0 = tmax - self.window
        p.setPen(fg)
        f = QFont(self.font())
        f.setPointSizeF(7.5)
        p.setFont(f)
        for i in range(5):
            tt = t0 + self.window * i / 4
            x = area.left() + area.width() * i / 4
            p.drawText(QRectF(x - 30, area.bottom() + 2, 60, 14), Qt.AlignmentFlag.AlignCenter, f"{max(tt, 0):.0f} s")
        p.drawText(QRectF(0, area.top() - 6, 40, 14), Qt.AlignmentFlag.AlignRight, "100%")
        p.drawText(QRectF(0, area.bottom() - 8, 40, 14), Qt.AlignmentFlag.AlignRight, "0%")
        for s in self.series.values():
            pts = [(t, v) for t, v in s["pts"] if t >= t0]
            if len(pts) < 2:
                continue
            path = QPainterPath()
            for i, (t, v) in enumerate(pts):
                x = area.left() + (t - t0) / self.window * area.width()
                fy = (min(max(v, s["lo"]), s["hi"]) - s["lo"]) / (s["hi"] - s["lo"])
                y = area.bottom() - fy * area.height()
                path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
            p.setPen(QPen(QColor(s["color"]), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        # legend
        y = area.bottom() + 20
        col_w = (self.width() - 20) / 2
        for i, s in enumerate(self.series.values()):
            x = 10 + (i % 2) * col_w
            yy = y + (i // 2) * 18
            p.fillRect(QRectF(x, yy + 4, 14, 8), QColor(s["color"]))
            last = fmt(s["pts"][-1][1]) if s["pts"] else "-"
            p.setPen(fg)
            p.drawText(QRectF(x + 18, yy, col_w - 22, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{s['label']}: {last} {s['unit']}  ({fmt(s['lo'], 0)} - {fmt(s['hi'], 0)})")
        p.end()


class MilLamp(QWidget):
    """The check-engine lamp: amber when on, grey when off, unknown = outline only."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state: bool | None = None
        self.setFixedSize(30, 22)

    def set_state(self, on: bool | None) -> None:
        self.state = on
        self.setToolTip(_tr("MIL (check engine lamp): ON") if on else _tr("MIL (check engine lamp): OFF")
                        if on is False else _tr("MIL: unknown"))
        self.update()

    def paintEvent(self, _e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        col = QColor("#f2a900") if self.state else pal.color(pal.ColorRole.Mid)
        p.setPen(QPen(col.darker(130) if self.state else col, 1.5))
        p.setBrush(col if self.state else Qt.BrushStyle.NoBrush)
        # a simple engine silhouette
        path = QPainterPath()
        path.moveTo(5, 8)
        path.lineTo(9, 8)
        path.lineTo(9, 5)
        path.lineTo(17, 5)
        path.lineTo(17, 8)
        path.lineTo(22, 8)
        path.lineTo(25, 11)
        path.lineTo(27, 11)
        path.lineTo(27, 16)
        path.lineTo(25, 16)
        path.lineTo(22, 19)
        path.lineTo(8, 19)
        path.lineTo(5, 15)
        path.lineTo(2, 15)
        path.lineTo(2, 11)
        path.lineTo(5, 11)
        path.closeSubpath()
        p.drawPath(path)
        p.end()
