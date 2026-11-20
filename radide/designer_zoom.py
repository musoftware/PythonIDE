"""Designer zoom (25% - 400%) for forms, user controls and phone frames.

At 100% the designer shows its widgets directly.  Any other zoom puts the designer's content widget
into a QGraphicsView (a QGraphicsProxyWidget scaled by the zoom factor): the previews, the selection
overlay, drag & drop from the Toolbox and the mouse gestures keep working unchanged in form coordinates
(Qt maps the events through the scale).  Ctrl+mouse wheel zooms; the View > Zoom menu and the zoom box
in the status bar (radide/features/designer_zoom_ui.py) call DesignerView.set_zoom()."""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

LEVELS = (25, 33, 50, 67, 75, 90, 100, 110, 125, 150, 175, 200, 250, 300, 400)
MIN_ZOOM, MAX_ZOOM = 0.25, 4.0


class ZoomHost(QGraphicsView):
    """Shows the designer's content widget scaled."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.setScene(QGraphicsScene(self))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setAcceptDrops(True)
        from .theme import color
        self.setStyleSheet(f"QGraphicsView {{ background:{color('designer_back')}; border:none; }}")
        self.proxy = None

    def embed(self, content) -> None:
        self.proxy = self.scene().addWidget(content)
        self.proxy.setAcceptDrops(True)

    def release(self):
        """Give the content widget back (to show it at 100% without the graphics view)."""
        if self.proxy is None:
            return None
        w = self.proxy.widget()
        self.proxy.setWidget(None)
        self.scene().removeItem(self.proxy)
        self.proxy = None
        return w

    def fit(self) -> None:
        if self.proxy is None:
            return
        z = self.view.zoom
        w = self.proxy.widget()
        size = w.size() if w is not None else self.proxy.size().toSize()
        self.resetTransform()
        self.scale(z, z)
        self.scene().setSceneRect(0, 0, size.width(), size.height())
        self.setFixedSize(int(math.ceil(size.width() * z)) + 1, int(math.ceil(size.height() * z)) + 1)
        self.centerOn(0, 0)
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)

    def wheelEvent(self, e):
        if wheel(self.view, e):
            return
        e.ignore()                       # the designer's scroll area scrolls


def clamp(factor: float) -> float:
    return max(MIN_ZOOM, min(MAX_ZOOM, float(factor)))


def set_zoom(view, factor: float) -> None:
    z = clamp(factor)
    if abs(z - 1.0) < 1e-3:
        z = 1.0
    view.zoom = z
    host = getattr(view, "_zoom_host", None)
    if z == 1.0 and host is not None:            # back to the plain widgets
        view.takeWidget()
        content = host.release()
        view._zoom_host = None
        host.deleteLater()
        if content is not None:
            view.setWidget(content)
            content.show()
    elif z != 1.0 and host is None:
        content = view.takeWidget()
        host = ZoomHost(view)
        host.embed(content)
        view._zoom_host = host
        view.setWidget(host)
    view.layout_form()
    try:
        view.overlay.setFocus()
    except RuntimeError:
        pass
    cb = getattr(view, "zoomChangedHook", None)
    if cb is not None:
        cb(z)


def step(view, direction: int) -> None:
    """Next / previous zoom level (direction +1 / -1)."""
    cur = round(view.zoom * 100)
    if direction > 0:
        nxt = next((lv for lv in LEVELS if lv > cur), LEVELS[-1])
    else:
        nxt = next((lv for lv in reversed(LEVELS) if lv < cur), LEVELS[0])
    set_zoom(view, nxt / 100)


def wheel(view, e) -> bool:
    """Ctrl+wheel zooms the designer; returns True when the event was used."""
    if not (e.modifiers() & Qt.KeyboardModifier.ControlModifier):
        return False
    dy = e.angleDelta().y()
    if dy:
        step(view, 1 if dy > 0 else -1)
    e.accept()
    return True
