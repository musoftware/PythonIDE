"""Small drawn icons for tool bars, dialogs and the Start Page (no image files, no trademark logos).

    icons.icon("step_into")            -> QIcon (16 px, crisp on high-DPI screens)
    icons.badge("WP", "#21759B", 40)   -> a rounded letter badge (like the New Project dialog's)
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

BLUE, DARK, RED, GREEN = "#2F72D6", "#7A7A7A", "#D13438", "#2E9E4F"
_CACHE: dict[tuple, QIcon] = {}
# generic letter badges for web site / app templates (no trademark logos)
TEMPLATE_BADGES = {"php-empty": ("PHP", "#777BB3"), "php-starter": ("PHP", "#4F5D95"),
                   "php-sqlite-app": ("DB", "#0F80CC"), "html-bootstrap": ("H5", "#7952B3"),
                   "static-empty": ("H5", "#E34F26"), "node-empty": ("N", "#3C873A"),
                   "node-express": ("Ex", "#3C873A"), "laravel": ("Lv", "#E8473C"),
                   "wordpress": ("WP", "#21759B")}


def _arrow_head(p: QPainter, tip: QPointF, dx: float, dy: float, size: float = 3.2):
    """A filled arrow head at *tip* pointing in direction (dx, dy) (unit vector)."""
    nx, ny = -dy, dx
    back = QPointF(tip.x() - dx * size, tip.y() - dy * size)
    p.drawPolygon(QPolygonF([tip, QPointF(back.x() + nx * size * 0.8, back.y() + ny * size * 0.8),
                             QPointF(back.x() - nx * size * 0.8, back.y() - ny * size * 0.8)]))


def _code_lines(p: QPainter, x0=2.0, ys=(3.0, 13.5)):
    p.save()
    p.setPen(QPen(QColor("#9A9A9A"), 1.2))
    for y in ys:
        p.drawLine(QPointF(x0, y), QPointF(x0 + 5, y))
    p.restore()


def _step_into(p):
    _code_lines(p)
    pen = QPen(QColor(BLUE), 1.6)
    p.setPen(pen)
    path = QPainterPath(QPointF(12, 2.5))
    path.lineTo(12, 10)
    p.drawPath(path)
    p.setBrush(QColor(BLUE))
    _arrow_head(p, QPointF(12, 13.5), 0, 1)
    p.setPen(QPen(QColor(DARK), 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(6, 8.5), 1.6, 1.6)


def _step_over(p):
    _code_lines(p, 4.5, (13.5,))
    pen = QPen(QColor(BLUE), 1.6)
    p.setPen(pen)
    path = QPainterPath(QPointF(2.5, 10))
    path.cubicTo(3, 1.5, 12.5, 1.5, 13, 8)
    p.drawPath(path)
    p.setBrush(QColor(BLUE))
    _arrow_head(p, QPointF(13.2, 11.5), 0.05, 1)
    p.setPen(QPen(QColor(DARK), 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(8, 13), 1.6, 1.6)


def _step_out(p):
    _code_lines(p)
    pen = QPen(QColor(BLUE), 1.6)
    p.setPen(pen)
    p.drawLine(QPointF(12, 13.5), QPointF(12, 6))
    p.setBrush(QColor(BLUE))
    _arrow_head(p, QPointF(12, 2.5), 0, -1)
    p.setPen(QPen(QColor(DARK), 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(6, 8.5), 1.6, 1.6)


def _breakpoint(p):
    p.setPen(QPen(QColor("#A4262C"), 1))
    p.setBrush(QColor(RED))
    p.drawEllipse(QPointF(8, 8), 5.5, 5.5)


def _design(p):
    p.setPen(QPen(QColor(DARK), 1.1))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRect(QRectF(1.5, 2.5, 13, 11))
    p.fillRect(QRectF(2, 3, 12, 2.5), QColor(BLUE))
    p.fillRect(QRectF(3.5, 7, 4, 5), QColor("#F0C419"))
    p.fillRect(QRectF(9, 7, 4, 1.5), QColor("#9A9A9A"))
    p.fillRect(QRectF(9, 10, 4, 1.5), QColor("#9A9A9A"))


def _split(p):
    p.setPen(QPen(QColor(DARK), 1.1))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRect(QRectF(1.5, 2.5, 13, 11))
    p.fillRect(QRectF(2, 3, 12, 4.5), QColor("#DCE6F5"))
    p.drawLine(QPointF(1.5, 8), QPointF(14.5, 8))
    p.setPen(QPen(QColor(BLUE), 1.1))
    for y in (10, 12):
        p.drawLine(QPointF(3.5, y), QPointF(11, y))


def _console(p):
    p.setPen(QPen(QColor("#202020"), 1))
    p.setBrush(QColor("#1E1E1E"))
    p.drawRoundedRect(QRectF(1, 2, 14, 12), 1.5, 1.5)
    p.setPen(QPen(QColor("#E0E0E0"), 1.4))
    p.drawPolyline(QPolygonF([QPointF(3.5, 6), QPointF(6, 8), QPointF(3.5, 10)]))
    p.drawLine(QPointF(7.5, 11), QPointF(11.5, 11))


def _open_file(p):
    p.setPen(QPen(QColor(DARK), 1))
    p.setBrush(QColor("#FFFFFF"))
    p.drawPolygon(QPolygonF([QPointF(3, 1.5), QPointF(10, 1.5), QPointF(13, 4.5), QPointF(13, 14.5),
                             QPointF(3, 14.5)]))
    p.setPen(QPen(QColor(BLUE), 1))
    for y in (7, 9.5, 12):
        p.drawLine(QPointF(5, y), QPointF(11, y))


def _close_solution(p):
    p.setPen(QPen(QColor(DARK), 1))
    p.setBrush(QColor("#F0C419"))
    p.drawPolygon(QPolygonF([QPointF(1.5, 4), QPointF(6, 4), QPointF(7.5, 5.5), QPointF(14.5, 5.5),
                             QPointF(14.5, 13.5), QPointF(1.5, 13.5)]))
    p.setPen(QPen(QColor(RED), 1.6))
    p.drawLine(QPointF(9, 8), QPointF(13, 12))
    p.drawLine(QPointF(13, 8), QPointF(9, 12))


def _save(p):
    p.setPen(QPen(QColor("#1B3F7A"), 1))
    p.setBrush(QColor("#3B6FC1"))
    p.drawRect(QRectF(2, 2, 12, 12))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRect(QRectF(4.5, 2, 7, 4.5))
    p.setBrush(QColor("#D8E2F2"))
    p.drawRect(QRectF(4, 9, 8, 5))


_PAINTERS = {"step_into": _step_into, "step_over": _step_over, "step_out": _step_out,
             "breakpoint": _breakpoint, "design": _design, "split": _split, "console": _console,
             "open_file": _open_file, "close_solution": _close_solution, "save": _save}


def icon(name: str, size: int = 16) -> QIcon:
    """A drawn 16 x 16 icon (rendered at 1x and 2x)."""
    key = (name, size)
    if key in _CACHE:
        return _CACHE[key]
    fn = _PAINTERS.get(name)
    ic = QIcon()
    if fn is None:
        return ic
    for scale in (1, 2):
        pm = QPixmap(size * scale, size * scale)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(size * scale / 16.0, size * scale / 16.0)
        fn(p)
        p.end()
        pm.setDevicePixelRatio(scale)
        ic.addPixmap(pm)
    _CACHE[key] = ic
    return ic


def badge(text: str, colour: str, size: int = 40, fg: str = "#FFFFFF") -> QIcon:
    """Rounded square with one to three letters - generic, theme-neutral template icons."""
    key = ("badge", text, colour, size, fg)
    if key in _CACHE:
        return _CACHE[key]
    ic = QIcon()
    for scale in (1, 2):
        pm = QPixmap(size * scale, size * scale)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(scale, scale)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colour))
        r = max(4, size // 6)
        p.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), r, r)
        p.setPen(QColor(fg))
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(max(7, int(size * (0.42 if len(text) <= 2 else 0.32))))
        p.setFont(f)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
        p.end()
        pm.setDevicePixelRatio(scale)
        ic.addPixmap(pm)
    _CACHE[key] = ic
    return ic


def template_badge(template_id: str, size: int = 40) -> QIcon | None:
    b = TEMPLATE_BADGES.get(template_id)
    return badge(b[0], b[1], size) if b else None


__all__ = ["icon", "badge", "template_badge", "TEMPLATE_BADGES"]
