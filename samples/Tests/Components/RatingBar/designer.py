"""RatingBar - how the control is drawn on the RAD IDE design surface (same drawing as StarRating).

Only ``paint()`` is needed: the IDE gives a QPainter, the control's rectangle and its property values.
(A package could instead define create(parent, props, ctx) -> QWidget and apply(widget, props, ctx).)
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen


def _padding(value):
    nums = [int(float(x)) for x in str(value or "0").replace(",", " ").split() if x.strip()]
    nums = nums or [0]
    if len(nums) == 1:
        nums = nums * 4
    elif len(nums) == 2:
        nums = nums * 2
    elif len(nums) == 3:
        nums.append(nums[1])
    return nums[:4]


def star_path(rect: QRectF, shape: str) -> QPainterPath:
    path = QPainterPath()
    if shape == "Circle":
        path.addEllipse(rect.adjusted(1, 1, -1, -1))
        return path
    if shape == "Square":
        path.addRoundedRect(rect.adjusted(1, 1, -1, -1), 2, 2)
        return path
    cx, cy = rect.center().x(), rect.center().y()
    outer = min(rect.width(), rect.height()) / 2
    inner = outer * 0.45
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / 5
        pt = QPointF(cx + r * math.cos(a), cy + r * math.sin(a))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    return path


def paint(painter, rect, props, ctx):
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    if props.get("BackColor"):
        painter.fillRect(rect, QColor(props["BackColor"]))
    left, top, right, bottom = _padding(props.get("Padding"))
    count = max(1, min(10, int(props.get("MaxStars", 5) or 5)))
    value = max(0, min(count, int(props.get("Value", 0) or 0)))
    spacing = max(0, int(props.get("Spacing", 4) or 0))
    caption = str(props.get("Caption") or "")
    h = rect.height() - top - bottom - (14 if caption else 0)
    text_w = 34 if props.get("ShowValue") else 0
    avail = rect.width() - left - right - text_w
    size = max(4.0, min(h, (avail - spacing * (count - 1)) / count))
    on, off = QColor(props.get("StarColor") or "#FFB400"), QColor(props.get("EmptyColor") or "#C8CDD5")
    enabled = props.get("Enabled", True)
    for i in range(count):
        r = QRectF(rect.x() + left + i * (size + spacing), rect.y() + top + (h - size) / 2, size, size)
        color = on if i < value else off
        if not enabled:
            color = QColor("#B0B0B0") if i < value else QColor("#E0E0E0")
        painter.setPen(QPen(color.darker(130), 1))
        painter.setBrush(color)
        painter.drawPath(star_path(r, props.get("Shape", "Star")))
    painter.setPen(QColor(props.get("ForeColor") or "#404040"))
    painter.setFont(QFont(props.get("FontName") or "Segoe UI", max(6, int(props.get("FontSize", 9) or 9))))
    if text_w:
        x = rect.x() + left + count * (size + spacing)
        painter.drawText(QRectF(x, rect.y() + top, text_w, h), Qt.AlignmentFlag.AlignVCenter, f"{value}/{count}")
    if caption:
        painter.setPen(QColor("#7A869A"))
        painter.drawText(QRectF(rect.x() + left, rect.bottom() - bottom - 14, rect.width(), 14),
                         Qt.AlignmentFlag.AlignLeft, caption.splitlines()[0])
