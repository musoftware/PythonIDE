"""The Flutter screen designer (FlutterFlow style): widget tree + palette + device canvas + properties inspector.

``FlutterDesigner(path)`` edits one ``*.fscreen.json`` (docs/FLUTTER_DESIGNER.md). Every edit is a model patch
(model.py) pushed on a QUndoStack; the canvas shows the real Flutter rendering from the preview host (live.py,
selection drawn by the host, clicks reported back) and, while that loads or when Flutter is missing, the fast
approximate Qt renderer (qtpreview.py) with its own selection overlay. Selection is synced both ways (canvas <->
tree <-> inspector). Saving writes the screen and, inside a Flutter project, regenerates its Dart code
(codegen.write_screen): ``lib/screens/<screen>.dart`` + the user's ``<screen>_events.dart``.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from PyQt6.QtCore import QMimeData, QPoint, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QAction, QColor, QDrag, QFont, QFontMetricsF, QImage, QKeySequence, QPainter,
                         QPainterPath, QPen, QUndoCommand, QUndoStack)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
                             QScrollArea, QSplitter, QStackedWidget, QTabWidget, QToolBar, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from . import iconfont
from . import model as M
from . import qtpreview as Q
from .inspector import Inspector
from .palette import MIME, Palette, type_icon

# name, width, height (portrait dp), platform, status bar, bottom inset, frame corner radius
DEVICES = [
    ("Pixel 8", 412, 915, "android", 24, 16, 34),
    ("iPhone 15", 393, 852, "ios", 59, 34, 55),
    ("iPhone 15 Pro Max", 430, 932, "ios", 59, 34, 55),
    ("iPhone SE", 375, 667, "ios", 20, 0, 0),
    ("Galaxy S20", 360, 800, "android", 24, 16, 30),
    ("Small phone", 360, 640, "android", 24, 0, 18),
    ("iPad mini", 744, 1133, "ios", 24, 20, 24),
    ("Android tablet", 800, 1280, "android", 24, 0, 24),
    ("Desktop 1280x800", 1280, 800, "android", 0, 0, 0),
]
ZOOMS = [("Fit", 0.0), ("50%", .5), ("75%", .75), ("100%", 1.0), ("125%", 1.25), ("150%", 1.5), ("200%", 2.0)]
SEL = QColor("#FF1E88E5")
HOVER = QColor("#C01E88E5")
MARGIN = 28


def find_project_folder(path: Path | None) -> Path | None:
    """The Flutter project (folder with pubspec.yaml) that contains *path*."""
    if path is None:
        return None
    for p in [Path(path).resolve().parent, *Path(path).resolve().parents]:
        if (p / "pubspec.yaml").is_file():
            return p
        if p.parent == p:
            break
    return None


def node_label(node: dict, where: M.Where | None) -> str:
    t = node.get("type", "?")
    if node.get("ctor"):
        t += "." + node["ctor"]
    extra = ""
    pr = node.get("props") or {}
    if node.get("type") in ("Text", "SelectableText") and isinstance(pr.get("data"), str):
        d = pr["data"].replace("\n", " ")
        extra = f'  "{d[:28]}{"..." if len(d) > 28 else ""}"'
    elif node.get("type") == "Icon" and isinstance(pr.get("icon"), str):
        extra = "  " + pr["icon"].split(".", 1)[-1]
    elif node.get("type") == "Image" and isinstance(pr.get("src"), str):
        extra = "  " + pr["src"].rsplit("/", 1)[-1][:24]
    elif node.get("type") == "Code":
        extra = "  " + str(pr.get("code", "")).split("\n")[0][:28]
    name = f"  #{node['name']}" if node.get("name") else ""
    slot = f"{where.slot}: " if where is not None and where.slot and where.slot != "child" else ""
    return f"{slot}{t}{name}{extra}"


class _PatchCmd(QUndoCommand):
    def __init__(self, designer, patch: list, text: str):
        super().__init__(text)
        self.d = designer
        self.patch = patch
        self._first = True

    def redo(self):
        if self._first:            # already applied by the model operation
            self._first = False
            return
        M.apply_patch(self.d.screen, self.patch)
        self.d._after_change(self.patch)

    def undo(self):
        inv = M.invert(self.patch)
        M.apply_patch(self.d.screen, inv)
        self.d._after_change(inv)


# =============================================================================== the tree
class WidgetTree(QTreeWidget):
    """Outline of the widget tree: drag & drop to reorder / reparent, palette drops, context menu, keys."""

    def __init__(self, designer):
        super().__init__()
        self.d = designer
        self.setHeaderHidden(True)
        self.setIconSize(QSize(16, 16))
        self.setIndentation(14)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setProperty("i18n_skip_items", True)
        self.items: dict[str, QTreeWidgetItem] = {}
        self._building = False
        self.itemSelectionChanged.connect(self._sel)
        self._known: set[str] = set()

    def rebuild(self):
        self._building = True
        collapsed = {nid for nid, it in self.items.items() if not it.isExpanded() and it.childCount()}
        sel = self.d.selected
        self.clear()
        self.items = {}

        def add(node, parent_item, where):
            it = QTreeWidgetItem([node_label(node, where)])
            it.setIcon(0, type_icon(node.get("type", ""), 16))
            it.setData(0, Qt.ItemDataRole.UserRole, node.get("id"))
            tip = M.CATALOG[node["type"]].help if node.get("type") in M.CATALOG else ""
            if node.get("anim"):
                it.setForeground(0, QColor("#8E24AA"))
                tip += f"\nanimation: {node['anim'].get('type')}"
            if node.get("events"):
                tip += "\nevents: " + ", ".join(f"{k} -> {v}" for k, v in node["events"].items())
            it.setToolTip(0, tip.strip())
            if parent_item is None:
                self.addTopLevelItem(it)
            else:
                parent_item.addChild(it)
            self.items[node["id"]] = it
            for c, w in M._iter_children(node):
                add(c, it, w)
            nid = node.get("id")
            it.setExpanded(nid not in collapsed)
        add(self.d.screen.tree, None, None)
        self._known = set(self.items)
        if sel and sel in self.items:
            self.setCurrentItem(self.items[sel])
            self.scrollToItem(self.items[sel])
        self._building = False

    def select_id(self, nid: str | None):
        self._building = True
        it = self.items.get(nid) if nid else None
        if it is not None:
            self.setCurrentItem(it)
            self.scrollToItem(it)
        else:
            self.clearSelection()
        self._building = False

    def _sel(self):
        if self._building:
            return
        it = self.currentItem()
        if it is not None:
            self.d.select(it.data(0, Qt.ItemDataRole.UserRole), source="tree")

    # ---- drag & drop
    def startDrag(self, actions):
        it = self.currentItem()
        if it is None:
            return
        nid = it.data(0, Qt.ItemDataRole.UserRole)
        if nid == self.d.screen.tree.get("id"):
            return
        md = QMimeData()
        md.setData(MIME, json.dumps({"move": nid}).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.setPixmap(it.icon(0).pixmap(20, 20))
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            super().dragMoveEvent(e)
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(MIME):
            e.ignore()
            return
        payload = json.loads(bytes(e.mimeData().data(MIME)).decode("utf-8"))
        it = self.itemAt(e.position().toPoint())
        pos = self.dropIndicatorPosition()
        e.setDropAction(Qt.DropAction.IgnoreAction)
        e.accept()
        if it is None:
            target, where = self.d.screen.tree.get("id"), None
        else:
            tid = it.data(0, Qt.ItemDataRole.UserRole)
            target, where = tid, None
            if pos in (QAbstractItemView.DropIndicatorPosition.AboveItem,
                       QAbstractItemView.DropIndicatorPosition.BelowItem):
                try:
                    parent, w = self.d.screen.parent_of(tid)
                except KeyError:
                    parent, w = None, None
                if parent is not None and w is not None and w.index is not None:
                    idx = w.index + (1 if pos == QAbstractItemView.DropIndicatorPosition.BelowItem else 0)
                    target, where = parent["id"], M.Where(w.slot, idx)
                elif parent is not None:
                    target, where = parent["id"], None
        QTimer.singleShot(0, lambda: self.d.drop_payload(payload, target, where))

    # ---- menu / keys
    def _menu(self, pt):
        it = self.itemAt(pt)
        if it is not None:
            self.d.select(it.data(0, Qt.ItemDataRole.UserRole), source="tree")
        self.d.context_menu(self.viewport().mapToGlobal(pt))

    def keyPressEvent(self, e):
        if self.d.handle_key(e):
            return
        super().keyPressEvent(e)


# ============================================================================== Qt canvas
class QtCanvas(QWidget):
    """Device frame + the approximate Qt rendering + selection / hover / drop overlay."""

    def __init__(self, designer):
        super().__init__()
        self.d = designer
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setProperty("i18n_skip", True)
        self.root: Q.Box | None = None
        self.bounds: dict[str, QRectF] = {}
        self.ctx: Q.Ctx | None = None
        self.hover: str | None = None
        self.drop_hint: tuple | None = None       # (kind, QRectF dp) kind = "line" | "box"
        self._img: QImage | None = None
        self._img_key = None
        self._press: QPointF | None = None
        self._editor: QLineEdit | None = None
        self.anim_t: float | None = None
        self.images = Q.ImageCache(self)
        self.images.changed.connect(self.relayout)

    # ---- geometry
    def zoom(self) -> float:
        z = self.d.zoom
        if z > 0:
            return z
        vp = self.parentWidget().size() if self.parentWidget() is not None else self.size()
        w, h = self.d.device_size()
        fw = 24 if self.d.frame_on() else 0
        return max(0.2, min((vp.width() - 2 * MARGIN - 2 * fw) / w, (vp.height() - 2 * MARGIN - 2 * fw) / h, 2.0))

    def screen_rect(self) -> QRectF:
        z = self.zoom()
        w, h = self.d.device_size()
        fw = 12 * z if self.d.frame_on() else 0
        return QRectF(MARGIN + fw, MARGIN + fw, w * z, h * z)

    def sizeHint(self):
        z = self.zoom()
        w, h = self.d.device_size()
        fw = 24 * z if self.d.frame_on() else 0
        return QSize(int(w * z + 2 * MARGIN + fw), int(h * z + 2 * MARGIN + fw))

    def to_dp(self, p: QPointF) -> QPointF:
        r, z = self.screen_rect(), self.zoom()
        return QPointF((p.x() - r.x()) / z, (p.y() - r.y()) / z)

    def to_view(self, r: QRectF) -> QRectF:
        s, z = self.screen_rect(), self.zoom()
        return QRectF(s.x() + r.x() * z, s.y() + r.y() * z, r.width() * z, r.height() * z)

    # ---- layout / render
    def relayout(self):
        d = self.d
        w, h = d.device_size()
        dev = d.device()
        top, bottom = (dev[4], dev[5]) if not d.landscape else (0 if dev[3] == "android" else 0, dev[5] // 2)
        ctx = Q.make_ctx(d.screen, d.dark, d.text_scale, d.project_folder(), self.images)
        ctx.show_drawer = d.drawer_shown()
        self.ctx = ctx
        try:
            self.root = Q.render_tree(d.screen, w, h, ctx, pad_top=top, pad_bottom=bottom)
            self.bounds = Q.bounds(self.root)
        except Exception as e:  # noqa: BLE001 - never break the designer
            self.root, self.bounds = None, {}
            d.status(f"Preview error: {e}")
        self._img = None
        self.updateGeometry()
        self.resize(self.sizeHint().expandedTo(self.parentWidget().size() if self.parentWidget() else QSize()))
        self.update()

    def _content(self) -> QImage | None:
        if self.root is None:
            return None
        z = self.zoom()
        dpr = self.devicePixelRatioF() or 1.0
        w, h = self.d.device_size()
        key = (z, dpr, w, h, self.anim_t)
        if self._img is not None and self._img_key == key:
            return self._img
        img = QImage(max(1, int(w * z * dpr)), max(1, int(h * z * dpr)), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("#FFFFFFFF"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(z * dpr, z * dpr)
        self.ctx.anim_t = self.anim_t
        Q.paint_box(p, self.root, self.ctx)
        p.end()
        img.setDevicePixelRatio(dpr)
        self._img, self._img_key = img, key
        return img

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#FF2B2D31") if self.d.dark else QColor("#FFE9EBEF"))
        s = self.screen_rect()
        z = self.zoom()
        dev = self.d.device()
        if self.d.frame_on():
            rad = dev[6] * z
            fw = 12 * z
            frame = s.adjusted(-fw, -fw, fw, fw)
            path = QPainterPath()
            path.addRoundedRect(frame, rad + fw if rad else 18 * z, rad + fw if rad else 18 * z)
            p.setPen(QPen(QColor("#FF5F6368"), 1.5))
            p.setBrush(QColor("#FF1F1F1F"))
            p.drawPath(path)
            clip = QPainterPath()
            clip.addRoundedRect(s, rad, rad)
            p.setClipPath(clip)
        img = self._content()
        if img is not None:
            p.drawImage(s, img)
        self._status_bar(p, s, z, dev)
        p.setClipping(False)
        self._overlay(p)

    def _status_bar(self, p: QPainter, s: QRectF, z: float, dev):
        if not self.d.frame_on() or self.d.landscape or dev[4] <= 0:
            return
        top = dev[4] * z
        light = True
        img = self._img
        if img is not None and img.width() > 4 and img.height() > 4:
            c = img.pixelColor(img.width() // 2, max(1, int(top * img.devicePixelRatio() / 2)))
            light = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) < 140
        col = QColor("#FFFFFFFF") if light else QColor("#FF1D1B20")
        f = QFont("Segoe UI")
        f.setPixelSize(max(6, int(14 * z)))
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(col)
        ios = dev[3] == "ios"
        tx = s.x() + (s.width() * .12 if ios else 16 * z)
        p.drawText(QRectF(tx, s.y(), 80 * z, top), int(Qt.AlignmentFlag.AlignVCenter), "9:41")
        icons = ["signal_cellular_alt", "wifi", "battery_full"]
        x = s.right() - (s.width() * .1 if ios else 12 * z)
        for name in reversed(icons):
            sz = 15 * z
            x -= sz + 3 * z
            iconfont.draw(p, QRectF(x, s.y() + (top - sz) / 2, sz, sz), "Icons." + name, col)
        if ios and dev[4] > 40:                  # dynamic island
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FF000000"))
            p.drawRoundedRect(QRectF(s.center().x() - 62 * z, s.y() + 11 * z, 124 * z, 36 * z), 18 * z, 18 * z)
        elif not ios:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FF000000"))
            p.drawEllipse(QPointF(s.center().x(), s.y() + top / 2), 6 * z, 6 * z)
        if dev[5] > 0:
            hb = QColor(col)
            hb.setAlpha(200)
            p.setBrush(hb)
            bw = (134 if ios else 108) * z
            p.drawRoundedRect(QRectF(s.center().x() - bw / 2, s.bottom() - 8 * z, bw, 4 * z), 2 * z, 2 * z)

    def _overlay(self, p: QPainter):
        sel = self.d.selected
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self.hover and self.hover != sel and self.hover in self.bounds:
            p.setPen(QPen(HOVER, 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.to_view(self.bounds[self.hover]).adjusted(.5, .5, -.5, -.5))
        if sel and sel in self.bounds:
            parent = self.d.parent_id(sel)
            if parent and parent in self.bounds:
                p.setPen(QPen(QColor(30, 136, 229, 90), 1, Qt.PenStyle.DotLine))
                p.drawRect(self.to_view(self.bounds[parent]))
            r = self.to_view(self.bounds[sel])
            p.setPen(QPen(SEL, 2))
            p.setBrush(QColor(30, 136, 229, 22))
            p.drawRect(r.adjusted(1, 1, -1, -1))
            node = self.d.screen.find(sel)
            lab = f"{node.get('type')}  {self.bounds[sel].width():.0f} x {self.bounds[sel].height():.0f}" if node \
                else ""
            f = QFont("Segoe UI")
            f.setPixelSize(11)
            p.setFont(f)
            fm = QFontMetricsF(f)
            tw = fm.horizontalAdvance(lab) + 10
            y = r.y() - 18 if r.y() - 18 > 0 else r.bottom() + 2
            chip = QRectF(r.x(), y, tw, 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(SEL)
            p.drawRoundedRect(chip, 3, 3)
            p.setPen(QColor("#FFFFFFFF"))
            p.drawText(chip, int(Qt.AlignmentFlag.AlignCenter), lab)
        if self.drop_hint is not None:
            kind, r = self.drop_hint
            vr = self.to_view(r)
            p.setPen(QPen(QColor("#FFFF6D00"), 2 if kind == "box" else 3))
            p.setBrush(QColor(255, 109, 0, 30) if kind == "box" else Qt.BrushStyle.NoBrush)
            if kind == "box":
                p.drawRect(vr)
            else:
                p.drawLine(vr.topLeft(), vr.bottomRight())

    # ---- mouse
    def hits_at(self, pos: QPointF) -> list[str]:
        if self.root is None:
            return []
        dp = self.to_dp(pos)
        return Q.hit_test(self.root, dp.x(), dp.y())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            hits = self.hits_at(e.position())
            if hits:
                nid = hits[0]
                if e.modifiers() & Qt.KeyboardModifier.AltModifier and self.d.selected in hits:
                    i = hits.index(self.d.selected)
                    nid = hits[min(i + 1, len(hits) - 1)]
                self.d.select(nid, source="canvas")
            self._press = e.position()
        elif e.button() == Qt.MouseButton.RightButton:
            hits = self.hits_at(e.position())
            if hits:
                self.d.select(hits[0], source="canvas")
            self.d.context_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._press is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if (e.position() - self._press).manhattanLength() > QApplication.startDragDistance():
                self._press = None
                sel = self.d.selected
                if sel and sel != self.d.screen.tree.get("id"):
                    md = QMimeData()
                    md.setData(MIME, json.dumps({"move": sel}).encode("utf-8"))
                    drag = QDrag(self)
                    drag.setMimeData(md)
                    node = self.d.screen.find(sel)
                    drag.setPixmap(type_icon(node.get("type", ""), 24).pixmap(24, 24))
                    drag.exec(Qt.DropAction.MoveAction)
            return
        hits = self.hits_at(e.position())
        h = hits[0] if hits else None
        if h != self.hover:
            self.hover = h
            self.update()

    def mouseReleaseEvent(self, e):
        self._press = None

    def leaveEvent(self, e):
        self.hover = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        hits = self.hits_at(e.position())
        if hits:
            self.d.inline_edit(hits[0])

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.d.step_zoom(1 if e.angleDelta().y() > 0 else -1)
            e.accept()
            return
        super().wheelEvent(e)

    def keyPressEvent(self, e):
        if self.d.handle_key(e):
            return
        super().keyPressEvent(e)

    # ---- drops
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if not e.mimeData().hasFormat(MIME):
            return
        payload = json.loads(bytes(e.mimeData().data(MIME)).decode("utf-8"))
        tgt = self.d.drop_target(self.hits_at(e.position()), self.to_dp(e.position()), payload, self.bounds)
        self.drop_hint = tgt[2] if tgt else None
        self.update()
        if tgt:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.drop_hint = None
        self.update()

    def dropEvent(self, e):
        self.drop_hint = None
        payload = json.loads(bytes(e.mimeData().data(MIME)).decode("utf-8"))
        tgt = self.d.drop_target(self.hits_at(e.position()), self.to_dp(e.position()), payload, self.bounds)
        self.update()
        if not tgt:
            e.ignore()
            return
        e.acceptProposedAction()
        parent, where, _hint, extra = tgt
        QTimer.singleShot(0, lambda: self.d.drop_payload(payload, parent, where, extra))


class LiveBox(QWidget):
    """Holds the live preview's web view; takes the palette / move drops for it (the view itself does not)."""

    def __init__(self, designer, view):
        super().__init__()
        self.d = designer
        self.view = view
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(view)
        self.setAcceptDrops(True)
        view.setAcceptDrops(False)
        QTimer.singleShot(0, self._no_child_drops)
        self.drop_hint = None

    def _no_child_drops(self):
        for w in self.view.findChildren(QWidget):
            w.setAcceptDrops(False)
        fp = self.view.focusProxy()
        if fp is not None:
            fp.setAcceptDrops(False)

    def _scale(self) -> float:
        live = self.d.live
        dr = live.device_rect if live is not None else QRectF()
        w = live.device.get("width", 0) if live is not None else 0
        return dr.width() / w if dr.isValid() and w else 1.0

    def _target(self, e):
        live = self.d.live
        pos = self.view.mapFrom(self, e.position().toPoint())
        pt = QPointF(pos)
        hits = sorted((k for k, r in live.rects.items() if r.contains(pt)),
                      key=lambda k: live.rects[k].width() * live.rects[k].height())
        payload = json.loads(bytes(e.mimeData().data(MIME)).decode("utf-8"))
        k = self._scale()
        dr = live.device_rect
        dp = QPointF((pt.x() - dr.x()) / k, (pt.y() - dr.y()) / k) if dr.isValid() else pt
        rects = {nid: QRectF((r.x() - dr.x()) / k, (r.y() - dr.y()) / k, r.width() / k, r.height() / k)
                 for nid, r in live.rects.items()} if dr.isValid() else dict(live.rects)
        return payload, self.d.drop_target(hits, dp, payload, rects)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if not e.mimeData().hasFormat(MIME) or self.d.live is None:
            e.ignore()
            return
        _p, tgt = self._target(e)
        if tgt:
            self.d.live.hover(tgt[0])
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if self.d.live is None:
            return
        payload, tgt = self._target(e)
        self.d.live.hover(None)
        if not tgt:
            e.ignore()
            return
        e.acceptProposedAction()
        parent, where, _hint, extra = tgt
        QTimer.singleShot(0, lambda: self.d.drop_payload(payload, parent, where, extra))


# ============================================================================== designer
class FlutterDesigner(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal(object)              # Path
    selectionChanged = pyqtSignal(str)
    openCode = pyqtSignal(object, int)      # Path, 1-based line - the IDE opens the user's Dart file there
    message = pyqtSignal(str)

    def __init__(self, path=None, screen: M.Screen | None = None, project_folder=None, live: bool | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("FlutterDesigner")
        self.path = Path(path) if path else None
        if screen is None:
            screen = M.Screen.load(self.path) if self.path and self.path.exists() else M.Screen.new("Screen1")
        self.screen = screen
        self._project = Path(project_folder) if project_folder else find_project_folder(self.path)
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(lambda clean: self.modifiedChanged.emit(not clean))
        self.selected: str | None = None
        self.device_index = 0
        self.landscape = False
        self.dark = False
        self.text_scale = 1.0
        self.zoom = 0.0
        self._frame = True
        self.live = None
        self.live_ready = False
        self._live_wanted = live
        self._clip_fallback: str | None = None
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_end = 0.0
        self._anim_clock = None
        self._build_ui()
        self.tree.rebuild()
        self.select(self.screen.tree.get("id"), source="init")
        QTimer.singleShot(0, self.canvas.relayout)
        if self._want_live():
            QTimer.singleShot(0, self.start_live)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(18, 18))
        lay.addWidget(self.toolbar)
        tb = self.toolbar
        self.a_undo = self.undo_stack.createUndoAction(self, "Undo")
        self.a_undo.setIcon(iconfont.icon("Icons.undo", 18))
        self.a_redo = self.undo_stack.createRedoAction(self, "Redo")
        self.a_redo.setIcon(iconfont.icon("Icons.redo", 18))
        tb.addAction(self.a_undo)
        tb.addAction(self.a_redo)
        tb.addSeparator()
        self.cbo_device = QComboBox()
        for d in DEVICES:
            self.cbo_device.addItem(f"{d[0]}  {d[1]}x{d[2]}")
        self.cbo_device.setToolTip("Device")
        self.cbo_device.currentIndexChanged.connect(self._device_changed)
        tb.addWidget(self.cbo_device)
        self.a_rotate = tb.addAction(iconfont.icon("Icons.screen_rotation", 18), "Rotate", self._rotate)
        self.a_rotate.setToolTip("Portrait / landscape")
        self.a_dark = tb.addAction(iconfont.icon("Icons.dark_mode", 18), "Dark")
        self.a_dark.setCheckable(True)
        self.a_dark.setToolTip("Light / dark theme")
        self.a_dark.toggled.connect(self._dark_changed)
        self.a_frame = tb.addAction(iconfont.icon("Icons.smartphone", 18), "Frame")
        self.a_frame.setCheckable(True)
        self.a_frame.setChecked(True)
        self.a_frame.setToolTip("Device frame")
        self.a_frame.toggled.connect(self._frame_changed)
        self.cbo_scale = QComboBox()
        for s in (0.85, 1.0, 1.15, 1.3, 1.5, 2.0):
            self.cbo_scale.addItem(f"Aa {int(s * 100)}%", s)
        self.cbo_scale.setCurrentIndex(1)
        self.cbo_scale.setToolTip("Text scale (accessibility font size)")
        self.cbo_scale.currentIndexChanged.connect(self._scale_changed)
        tb.addWidget(self.cbo_scale)
        self.cbo_zoom = QComboBox()
        for t, _z in ZOOMS:
            self.cbo_zoom.addItem(t)
        self.cbo_zoom.setToolTip("Zoom (Ctrl+wheel)")
        self.cbo_zoom.currentIndexChanged.connect(self._zoom_changed)
        tb.addWidget(self.cbo_zoom)
        tb.addSeparator()
        self.cbo_render = QComboBox()
        self.cbo_render.addItem("Flutter (live)", "live")
        self.cbo_render.addItem("Qt preview (fast)", "qt")
        self.cbo_render.setToolTip("Live: the real Flutter rendering (preview host, built once per Flutter version)."
                                   "\nQt preview: an instant approximation that works without Flutter.")
        self.cbo_render.currentIndexChanged.connect(self._render_changed)
        tb.addWidget(self.cbo_render)
        self.a_play = tb.addAction(iconfont.icon("Icons.play_arrow", 18), "Play", self.play_animations)
        self.a_play.setToolTip("Play the entrance animations")
        self.a_interact = tb.addAction(iconfont.icon("Icons.touch_app", 18), "Interact")
        self.a_interact.setCheckable(True)
        self.a_interact.setToolTip("Live preview: use the screen like the app (typing, buttons) instead of selecting")
        self.a_interact.toggled.connect(lambda on: self.live is not None and self.live.set_mode(
            "interact" if on else "design"))
        tb.addSeparator()
        self.a_code = tb.addAction(iconfont.icon("Icons.code", 18), "Dart code", self.show_code)
        self.a_code.setToolTip("Show the generated Dart code")
        self.a_save = tb.addAction(iconfont.icon("Icons.save", 18), "Save", self.save)
        self.a_save.setToolTip("Save the screen and regenerate its Dart code")

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QSplitter(Qt.Orientation.Vertical)
        self.palette = Palette()
        self.palette.insertRequested.connect(lambda p: self.insert_payload(p))
        self.tree = WidgetTree(self)
        left.addWidget(self._titled("Palette", self.palette))
        left.addWidget(self._titled("Widget Tree", self.tree))
        left.setSizes([300, 400])
        self.stack = QStackedWidget()
        self.canvas = QtCanvas(self)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setProperty("i18n_skip", True)
        self.stack.addWidget(self.scroll)
        self.live_box: LiveBox | None = None
        self.inspector = Inspector(self)
        split.addWidget(left)
        split.addWidget(self.stack)
        split.addWidget(self._titled("Properties", self.inspector))
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([250, 640, 340])
        self.splitter = split
        lay.addWidget(split, 1)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 2, 6, 2)
        self.lbl_status = QLabel("")
        self.lbl_issues = QLabel("")
        self.lbl_issues.setStyleSheet("color: #B26A00")
        bar.addWidget(self.lbl_status, 1)
        bar.addWidget(self.lbl_issues)
        lay.addLayout(bar)
        self._shortcuts()
        if not self._want_live():
            self.cbo_render.setCurrentIndex(1)

    def _titled(self, title: str, w: QWidget) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lab = QLabel(" " + title)
        lab.setStyleSheet("font-weight:bold; padding:3px; background: palette(midlight);")
        lay.addWidget(lab)
        lay.addWidget(w, 1)
        return box

    def _shortcuts(self):
        def act(seq, fn, text):
            a = QAction(text, self)
            a.setShortcut(QKeySequence(seq))
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            a.triggered.connect(fn)
            self.addAction(a)
            return a
        act("Ctrl+D", self.duplicate_selected, "Duplicate")
        act("Alt+Up", self.select_parent, "Select parent")
        act("Ctrl+Up", lambda: self.move_selected(-1), "Move up")
        act("Ctrl+Down", lambda: self.move_selected(1), "Move down")
        act("F5", self.play_animations, "Play animations")

    # ------------------------------------------------------------------ settings
    def device(self):
        return DEVICES[self.device_index]

    def device_size(self) -> tuple[int, int]:
        d = self.device()
        return (d[2], d[1]) if self.landscape else (d[1], d[2])

    def frame_on(self) -> bool:
        return self._frame and self.device()[3] != "desktop" and self.device()[0] != "Desktop 1280x800"

    def project_folder(self) -> Path | None:
        return self._project

    def scheme(self) -> dict:
        th = self.screen.data.get("theme") or {}
        return Q.color_scheme(th.get("seedColor"), self.dark or th.get("brightness") == "dark")

    def screens_list(self) -> list[tuple[str, str]]:
        out = []
        folder = self.project_folder() or (self.path.parent if self.path else None)
        if folder is not None:
            for p in M.find_screens(folder):
                try:
                    s = M.Screen.load(p)
                except (OSError, ValueError):
                    continue
                if s.name != self.screen.name:
                    out.append((s.name, s.route))
        return out

    def _device_changed(self, i):
        self.device_index = max(0, i)
        self._settings_changed()

    def _rotate(self):
        self.landscape = not self.landscape
        self._settings_changed()

    def _dark_changed(self, on):
        self.dark = on
        self._settings_changed()

    def _frame_changed(self, on):
        self._frame = on
        self._settings_changed()

    def _scale_changed(self, i):
        self.text_scale = float(self.cbo_scale.itemData(i) or 1.0)
        self._settings_changed()

    def _zoom_changed(self, i):
        self.zoom = ZOOMS[max(0, i)][1]
        self._settings_changed()

    def step_zoom(self, step: int):
        cur = self.canvas.zoom()
        vals = [z for _t, z in ZOOMS if z > 0]
        nxt = min(vals, key=lambda z: abs(z - cur))
        i = vals.index(nxt) + step
        i = max(0, min(len(vals) - 1, i))
        self.cbo_zoom.setCurrentIndex(i + 1)

    def _settings_changed(self):
        self.canvas.relayout()
        self._push_device()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.zoom == 0:
            QTimer.singleShot(0, self.canvas.relayout)

    # ------------------------------------------------------------------ live preview
    def _want_live(self) -> bool:
        if self._live_wanted is not None:
            return bool(self._live_wanted)
        try:
            from . import live as LV
            return bool(LV._flutter()[0])
        except Exception:  # noqa: BLE001
            return False

    def start_live(self):
        if self.live is not None:
            return
        try:
            from . import live as LV
            self.live = LV.LivePreview(parent=self)
        except Exception as e:  # noqa: BLE001 - QtWebEngine missing ...
            self.status(f"Live preview unavailable: {e}")
            self.cbo_render.setCurrentIndex(1)
            return
        lv = self.live
        self.live_box = LiveBox(self, lv.view)
        self.stack.addWidget(self.live_box)
        lv.ready.connect(self._live_ready)
        lv.nodeClicked.connect(lambda nid, _m: nid and self.select(nid, source="live"))
        lv.nodeDoubleClicked.connect(lambda nid, _m: nid and self.inline_edit(nid))
        lv.contextRequested.connect(self._live_context)
        lv.statusChanged.connect(self.status)
        lv.issuesChanged.connect(self._live_issues)
        lv.log.connect(lambda lvl, t: lvl == "error" and self.status(f"Preview: {t[:160]}"))
        lv.rendered.connect(lambda _s, ms: self.lbl_status.setToolTip(f"last frame {ms:.0f} ms after the edit"))
        lv.set_screen(self.screen)
        self._push_device()
        lv.start(self.project_folder())

    def _live_ready(self):
        self.live_ready = True
        if self.cbo_render.currentData() == "live" and self.live_box is not None:
            self.stack.setCurrentWidget(self.live_box)
        if self.selected:
            self.live.select(self.selected)

    def _live_context(self, nid, _m):
        if nid:
            self.select(nid, source="live")
        from PyQt6.QtGui import QCursor
        self.context_menu(QCursor.pos())

    def _live_issues(self, issues):
        if issues:
            self.lbl_issues.setText(f"{len(issues)} runtime issue(s)")
            self.lbl_issues.setToolTip("\n".join(f"{i.get('id')}: {i.get('message')}" for i in issues[:30]))
        else:
            self._show_issues()

    def _render_changed(self, _i):
        mode = self.cbo_render.currentData()
        if mode == "live":
            if self.live is None:
                self.start_live()
            if self.live_box is not None and self.live_ready:
                self.stack.setCurrentWidget(self.live_box)
            else:
                self.stack.setCurrentWidget(self.scroll)
        else:
            self.stack.setCurrentWidget(self.scroll)

    def _push_device(self):
        if self.live is None:
            return
        w, h = self.device_size()
        self.live.set_device(w, h, platform=self.device()[3], dark=self.dark, textScale=self.text_scale,
                             frame=self.frame_on(), zoom=self.zoom or None)

    def shutdown(self):
        self._anim_timer.stop()
        if self.live is not None:
            try:
                self.live.shutdown()
            except Exception:  # noqa: BLE001
                pass

    def closeEvent(self, e):
        self.shutdown()
        super().closeEvent(e)

    # ------------------------------------------------------------------ selection
    def select(self, nid: str | None, source: str = ""):
        if nid is not None and self.screen.find(nid) is None:
            nid = None
        changed = nid != self.selected
        old_drawer = self.drawer_shown()
        self.selected = nid
        if source != "tree":
            self.tree.select_id(nid)
        self.inspector.inspect(nid)
        if self.drawer_shown() != old_drawer:
            self.canvas.relayout()
        else:
            self.canvas.update()
        if self.live is not None and source != "live":
            self.live.select(nid, reveal=True)
        if changed and nid:
            node = self.screen.find(nid)
            self.status(f"{node.get('type')} {nid}" + (f"  #{node['name']}" if node.get("name") else ""))
            self.selectionChanged.emit(nid)

    def parent_id(self, nid: str) -> str | None:
        try:
            p, _w = self.screen.parent_of(nid)
        except KeyError:
            return None
        return p.get("id") if p else None

    def drawer_shown(self) -> str | None:
        if not self.selected:
            return None
        path = self.screen.path_of(self.selected)
        root = self.screen.tree
        if root.get("type") != "Scaffold" or len(path) < 2:
            return None
        for which in ("drawer", "endDrawer"):
            if (root.get("slots") or {}).get(which) is path[1]:
                return which
        return None

    def select_parent(self):
        if self.selected:
            p = self.parent_id(self.selected)
            if p:
                self.select(p, source="key")

    # ------------------------------------------------------------------ edits
    def apply(self, fn, *args, text: str = "Edit", select: str | None = None):
        """Run a model operation (it applies itself and returns its patch) and push it on the undo stack."""
        try:
            patch = fn(self.screen, *args)
        except (ValueError, KeyError) as e:
            self.status(str(e).strip("'\""))
            return None
        if not patch:
            return patch
        self.undo_stack.push(_PatchCmd(self, patch, text))
        self._after_change(patch, select)
        return patch

    def apply_many(self, patches: list, text: str):
        """Several already-applied patches as one undo step."""
        patch = [ch for p in patches if p for ch in p]
        if patch:
            self.undo_stack.push(_PatchCmd(self, patch, text))
            self._after_change(patch)
        return patch

    def _after_change(self, patch, select: str | None = None):
        if select is not None:
            self.selected = select
        if self.selected and self.screen.find(self.selected) is None:
            self.selected = None
        self.tree.rebuild()
        self.canvas.relayout()
        self.inspector.inspect(self.selected)
        self.tree.select_id(self.selected)
        self._show_issues()
        if self.live is not None:
            if any(ch.get("op") == "screen" for ch in patch):
                self.live.set_screen(self.screen)
            else:
                self.live.push_patch(patch)
            if select is not None:
                self.live.select(self.selected)

    def _show_issues(self):
        try:
            issues = M.validate(self.screen)
        except Exception:  # noqa: BLE001
            issues = []
        errs = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level == "warning"]
        if issues:
            self.lbl_issues.setText(f"{len(errs)} error(s), {len(warns)} warning(s)")
            self.lbl_issues.setToolTip("\n".join(str(i) for i in issues[:40]))
        else:
            self.lbl_issues.setText("")
            self.lbl_issues.setToolTip("")

    def status(self, text: str):
        self.lbl_status.setText(text)
        self.message.emit(text)

    def is_modified(self) -> bool:
        return not self.undo_stack.isClean()

    def undo(self):
        self.undo_stack.undo()

    def redo(self):
        self.undo_stack.redo()

    # inspector API
    def set_prop(self, nid, key, value):
        return self.apply(M.set_prop, nid, key, value, text=f"Set {key}")

    def set_event(self, nid, event, handler):
        return self.apply(M.set_event, nid, event, handler, text=f"Set {event}")

    def set_anim(self, nid, anim):
        return self.apply(M.set_anim, nid, anim, text="Animation")

    def rename(self, nid, name):
        return self.apply(M.rename, nid, name, text="Rename")

    def set_ctor(self, nid, ctor):
        node = self.screen.find(nid)
        if node is None:
            return None
        patches = [M.set_ctor(self.screen, nid, ctor)]
        spec = M.widget_spec(node["type"], ctor)
        # slots the new constructor does not have are dropped (ElevatedButton.icon has icon + label, not child)
        for s in list((node.get("slots") or {})):
            if spec is not None and s not in spec.slots:
                kid = node["slots"][s]
                if s == "child" and "label" in spec.slots and isinstance(kid, dict):
                    patches.append(M.move(self.screen, kid["id"], nid, M.Where("label")))
                else:
                    patches.append(M.delete(self.screen, kid["id"]) if isinstance(kid, dict) else [])
        if spec is not None:
            for s, ss in spec.slots.items():
                if ss.required and not (node.get("slots") or {}).get(s) and s in ("label", "icon"):
                    tmpl = M.new_node("Icon" if s == "icon" else "Text", self.screen,
                                      props={"icon": "Icons.send"} if s == "icon" else {"data": "Label"})
                    patches.append(M.insert(self.screen, nid, tmpl, M.Where(s)))
        return self.apply_many(patches, "Constructor")

    def set_screen(self, key, value):
        return self.apply(M.set_screen, key, value, text=f"Screen {key}")

    # ------------------------------------------------------------------ tree commands
    def payload_node(self, payload: dict) -> dict | None:
        if payload.get("node"):
            return copy.deepcopy(payload["node"])
        t = payload.get("type")
        if t in M.CATALOG:
            return M.new_node(t, ctor=payload.get("ctor"))
        return None

    def insert_payload(self, payload: dict, parent_id: str | None = None, where: M.Where | None = None):
        """Palette double-click / paste: into the selected widget when it can hold it, else after it."""
        node = self.payload_node(payload)
        if node is None:
            return None
        if parent_id is None:
            parent_id, where = self._insert_place(node)
        if parent_id is None:
            self.status("Select a widget that can hold a child (or a widget inside a Row / Column)")
            return None
        return self._insert(node, parent_id, where)

    def _insert(self, node: dict, parent_id: str, where: M.Where | None):
        parent = self.screen.find(parent_id)
        node = copy.deepcopy(node)
        self.screen.assign_ids(node)
        if parent is not None and node.get("type") in M.CATALOG:
            need = M.CATALOG[node["type"]].parent
            if need and parent.get("type") not in need and parent.get("type") != "Code":
                self.status(f"{node['type']} belongs in {' / '.join(need)}")
        return self.apply(M.insert, parent_id, node, where, text=f"Add {node.get('type')}", select=node["id"])

    def _insert_place(self, node: dict) -> tuple[str | None, M.Where | None]:
        sel = self.selected or self.screen.tree.get("id")
        cur = self.screen.find(sel)
        while cur is not None:
            try:
                w = M.default_where(cur, node.get("type"))
                spec = M.widget_spec(cur["type"], cur.get("ctor"))
                if spec and (spec.children or w.slot is not None):
                    return cur["id"], w
            except ValueError:
                pass
            parent, pw = self.screen.parent_of(cur["id"])
            if parent is not None and pw is not None and pw.index is not None:
                return parent["id"], M.Where(pw.slot, pw.index + 1)
            cur = parent
        return None, None

    def insert_widget(self, type_: str, parent_id: str | None = None, where: M.Where | None = None,
                      ctor: str | None = None, props: dict | None = None):
        payload = {"type": type_, **({"ctor": ctor} if ctor else {})}
        node = self.payload_node(payload)
        if props:
            node.setdefault("props", {}).update(props)
        if parent_id is None:
            parent_id, where = self._insert_place(node)
        return self._insert(node, parent_id, where) if parent_id else None

    def insert_node(self, node: dict, parent_id: str | None = None, where: M.Where | None = None):
        return self.insert_payload({"node": node}, parent_id, where)

    def drop_payload(self, payload: dict, parent_id: str | None, where: M.Where | None = None,
                     extra: dict | None = None):
        """A drop from the palette / tree / canvas onto parent_id (at where)."""
        if parent_id is None:
            return None
        if payload.get("move"):
            nid = payload["move"]
            if nid == parent_id:
                return None
            patches = []
            try:
                if extra and extra.get("positioned"):
                    node = self.screen.find(nid)
                    if node.get("type") == "Positioned":
                        patches.append(M.move(self.screen, nid, parent_id, where))
                        patches.append(M.set_props(self.screen, nid, extra["positioned"]))
                    else:
                        cur_parent = self.parent_id(nid)
                        if cur_parent == parent_id and self.screen.find(cur_parent).get("type") == "Stack":
                            patches.append(M.wrap(self.screen, nid, "Positioned", extra["positioned"]))
                        else:
                            patches.append(M.move(self.screen, nid, parent_id, where))
                            patches.append(M.wrap(self.screen, nid, "Positioned", extra["positioned"]))
                else:
                    patches.append(M.move(self.screen, nid, parent_id, where))
            except (ValueError, KeyError) as e:
                for p in reversed(patches):
                    M.apply_patch(self.screen, M.invert(p))
                self.status(str(e).strip("'\""))
                return None
            p = self.apply_many(patches, "Move")
            self.select(nid, source="drop")
            return p
        node = self.payload_node(payload)
        if node is None:
            return None
        if extra and extra.get("positioned") and node.get("type") != "Positioned":
            node = M.T("Positioned", dict(extra["positioned"]), {"child": node})
        elif extra and extra.get("positioned"):
            node.setdefault("props", {}).update(extra["positioned"])
        return self._insert(node, parent_id, where)

    def drop_target(self, hits: list[str], dp: QPointF, payload: dict, rects: dict):
        """(parent id, Where, hint (kind, QRectF), extra) for a drop at *dp* (device px) or None."""
        moving = payload.get("move")
        node = self.screen.find(moving) if moving else self.payload_node(payload)
        if node is None:
            return None
        blocked = {n.get("id") for n, *_ in M.walk_node(node)} if moving else set()
        ctype = node.get("type")
        for nid in hits:
            if nid in blocked:
                continue
            tgt = self.screen.find(nid)
            if tgt is None:
                continue
            spec = M.widget_spec(tgt["type"], tgt.get("ctor"))
            if spec is None:
                continue
            r = rects.get(nid)
            if spec.children:
                if tgt["type"] == "Stack" and r is not None:
                    pos = {"left": round(max(0.0, dp.x() - r.x())), "top": round(max(0.0, dp.y() - r.y()))}
                    return nid, M.Where(None, len(tgt.get("children") or [])), ("box", r), {"positioned": pos}
                kids = [c for c in tgt.get("children") or []]
                vertical = self._vertical(tgt)
                idx = len(kids)
                line = None
                for i, c in enumerate(kids):
                    cr = rects.get(c.get("id"))
                    if cr is None:
                        continue
                    if (dp.y() < cr.center().y()) if vertical else (dp.x() < cr.center().x()):
                        idx = i
                        line = QRectF(cr.x(), cr.y(), cr.width(), 0) if vertical else \
                            QRectF(cr.x(), cr.y(), 0, cr.height())
                        break
                if line is None and kids:
                    cr = rects.get(kids[-1].get("id"))
                    if cr is not None:
                        line = QRectF(cr.x(), cr.bottom(), cr.width(), 0) if vertical else \
                            QRectF(cr.right(), cr.y(), 0, cr.height())
                if ctype in M.CATALOG and M.CATALOG[ctype].parent and tgt["type"] not in M.CATALOG[ctype].parent:
                    continue
                hint = ("line", line) if line is not None else ("box", r or QRectF())
                return nid, M.Where(None, idx), hint, None
            if tgt.get("type") == "Code":
                continue
            try:
                w = M.default_where(tgt, ctype)
            except ValueError:
                continue
            if w.slot is not None and not (spec.slots[w.slot].multi) and (tgt.get("slots") or {}).get(w.slot):
                continue
            if ctype in M.CATALOG and M.CATALOG[ctype].parent and tgt["type"] not in M.CATALOG[ctype].parent:
                continue
            return nid, w, ("box", r or QRectF()), None
        return None

    @staticmethod
    def _vertical(node: dict) -> bool:
        t = node.get("type")
        pr = node.get("props") or {}
        if t in ("Row", "TabBar"):
            return False
        if t == "Flex":
            return pr.get("direction") == "Axis.vertical"
        if t in ("ListView", "PageView", "Wrap"):
            return pr.get("scrollDirection", pr.get("direction")) not in ("Axis.horizontal",) if t != "Wrap" else \
                pr.get("direction") == "Axis.vertical"
        return True

    def delete_selected(self):
        nid = self.selected
        if not nid or nid == self.screen.tree.get("id"):
            return None
        parent = self.parent_id(nid)
        return self.apply(M.delete, nid, text="Delete", select=parent)

    def duplicate_selected(self):
        nid = self.selected
        if not nid:
            return None
        before = self.screen.ids()
        p = self.apply(M.duplicate, nid, text="Duplicate")
        if p:
            new = [i for i in self.screen.ids() - before]
            node = p[0].get("new") or {}
            self.select(node.get("id") or (new[0] if new else nid), source="dup")
        return p

    def wrap_selected(self, wrapper: str, props: dict | None = None):
        nid = self.selected
        if not nid:
            return None
        before = self.screen.ids()
        p = self.apply(M.wrap, nid, wrapper, props, text=f"Wrap with {wrapper}")
        if p:
            new = p[0]["new"]
            self.select(new.get("id") if isinstance(new, dict) else
                        next(iter(self.screen.ids() - before), nid), source="wrap")
        return p

    def unwrap_selected(self):
        nid = self.selected
        if not nid:
            return None
        node = self.screen.find(nid)
        kids = [c for c, _w in M._iter_children(node)] if node else []
        keep = kids[0]["id"] if kids else None
        return self.apply(M.unwrap, nid, text="Unwrap", select=keep)

    def move_selected(self, step: int):
        nid = self.selected
        if not nid:
            return None
        try:
            parent, w = self.screen.parent_of(nid)
        except KeyError:
            return None
        if parent is None or w is None or w.index is None:
            return None
        lst = (parent.get("slots") or {}).get(w.slot) if w.slot else parent.get("children")
        new = w.index + step
        if not lst or new < 0 or new >= len(lst):
            return None
        return self.apply(M.move, nid, parent["id"], M.Where(w.slot, new + (1 if step > 0 else 0)), text="Move")

    # clipboard
    def copy_selected(self) -> bool:
        node = self.screen.find(self.selected) if self.selected else None
        if node is None or node is self.screen.tree:
            return False
        data = json.dumps(M.strip_ids(node), ensure_ascii=False)
        md = QMimeData()
        md.setData(MIME, json.dumps({"node": json.loads(data)}).encode("utf-8"))
        md.setText(data)
        try:
            QApplication.clipboard().setMimeData(md)
        except Exception:  # noqa: BLE001
            pass
        self._clip_fallback = data
        return True

    def cut_selected(self):
        if self.copy_selected():
            self.delete_selected()

    def paste(self):
        payload = None
        try:
            md = QApplication.clipboard().mimeData()
            if md is not None and md.hasFormat(MIME):
                payload = json.loads(bytes(md.data(MIME)).decode("utf-8"))
            elif md is not None and md.hasText():
                txt = md.text().strip()
                if txt.startswith("{"):
                    payload = {"node": json.loads(txt)}
                elif re.match(r"^[A-Z]\w*(\.\w+)?\(", txt):          # pasted Dart widget code
                    from . import importer
                    payload = {"node": importer.import_expression(txt)}
        except Exception:  # noqa: BLE001
            payload = None
        if payload is None and self._clip_fallback:
            payload = {"node": json.loads(self._clip_fallback)}
        if not payload or not isinstance(payload.get("node"), dict) or "type" not in payload["node"]:
            self.status("Nothing to paste")
            return None
        return self.insert_payload(payload)

    def extract_selected(self, method: str | None = None):
        """Extract to widget (method): the subtree becomes ``Widget _buildX(BuildContext context)`` in the State
        class (screen code.members) and a Code node calling it."""
        nid = self.selected
        node = self.screen.find(nid) if nid else None
        if node is None or node is self.screen.tree:
            return None
        if method is None:
            base = node.get("name") or node.get("type", "Part")
            sug = "_build" + base[:1].upper() + base[1:]
            method, ok = QInputDialog.getText(self, "Extract to widget", "Method name:", text=sug)
            if not ok:
                return None
        method = re.sub(r"\W", "", method or "") or "_buildPart"
        from . import codegen as CG
        try:
            body = CG.TreeGen(CG.GenContext()).node(copy.deepcopy(node)).render()
        except Exception as e:  # noqa: BLE001
            self.status(f"Cannot extract: {e}")
            return None
        code = dict(self.screen.data.get("code") or {})
        members = code.get("members", "")
        members = (members + "\n\n" if members else "") + \
            f"Widget {method}(BuildContext context) {{\n  return {body};\n}}"
        code["members"] = members
        repl = {"id": self.screen.new_id(), "type": "Code", "props": {"code": f"{method}(context)"}}
        p1 = M.set_screen(self.screen, "code", code)
        p2 = M.replace(self.screen, nid, repl)
        self.apply_many([p1, p2], "Extract to widget")
        self.select(repl["id"], source="extract")
        return method

    # ------------------------------------------------------------------ keys / menu
    def handle_key(self, e) -> bool:
        k, mod = e.key(), e.modifiers()
        ctrl = bool(mod & Qt.KeyboardModifier.ControlModifier)
        if k == Qt.Key.Key_Delete:
            self.delete_selected()
            return True
        if ctrl and k == Qt.Key.Key_C:
            self.copy_selected()
            return True
        if ctrl and k == Qt.Key.Key_X:
            self.cut_selected()
            return True
        if ctrl and k == Qt.Key.Key_V:
            self.paste()
            return True
        if ctrl and k == Qt.Key.Key_Z:
            self.undo()
            return True
        if ctrl and k == Qt.Key.Key_Y:
            self.redo()
            return True
        if k == Qt.Key.Key_F2 and self.selected:
            self.inline_edit(self.selected)
            return True
        return False

    def context_menu(self, global_pos: QPoint):
        m = QMenu(self)
        nid = self.selected
        node = self.screen.find(nid) if nid else None
        is_root = node is self.screen.tree
        add = m.addMenu(iconfont.icon("Icons.add", 16), "Add child")
        for cat, types in M.categories().items():
            sub = add.addMenu(cat)
            for t in types:
                sub.addAction(type_icon(t, 16), t, lambda t=t: self.insert_payload({"type": t}))
        wrap = m.addMenu(iconfont.icon("Icons.select_all", 16), "Wrap with...")
        for w in M.WRAPPERS:
            wrap.addAction(type_icon(w, 16), w, lambda w=w: self.wrap_selected(w))
        wrap.setEnabled(node is not None)
        a = m.addAction("Unwrap (keep the child)", self.unwrap_selected)
        a.setEnabled(node is not None and any(True for _ in M._iter_children(node)))
        m.addAction("Extract to widget (method)...", self.extract_selected).setEnabled(node is not None and not is_root)
        m.addSeparator()
        m.addAction("Cut", self.cut_selected).setEnabled(node is not None and not is_root)
        m.addAction("Copy", self.copy_selected).setEnabled(node is not None and not is_root)
        m.addAction("Paste", self.paste)
        m.addAction("Duplicate\tCtrl+D", self.duplicate_selected).setEnabled(node is not None and not is_root)
        m.addAction("Delete\tDel", self.delete_selected).setEnabled(node is not None and not is_root)
        m.addSeparator()
        m.addAction("Move up\tCtrl+Up", lambda: self.move_selected(-1))
        m.addAction("Move down\tCtrl+Down", lambda: self.move_selected(1))
        m.addAction("Select parent\tAlt+Up", self.select_parent).setEnabled(node is not None and not is_root)
        if node is not None and not is_root:
            an = m.addMenu("Animation")
            try:
                from . import animations as AN
                for p in AN.PRESETS:
                    an.addAction(p.label, lambda pid=p.id: self.set_anim(self.selected, AN.make_anim(pid)))
                an.addSeparator()
                kids = [c for c, _w in M._iter_children(node)]
                if len(kids) > 1:
                    an.addAction("Stagger children (fade in up)",
                                 lambda: self.apply(AN.stagger, self.selected, "fade_up", text="Stagger"))
            except Exception:  # noqa: BLE001
                pass
            an.addAction("Remove animation", lambda: self.set_anim(self.selected, None))
            spec = M.CATALOG.get(node.get("type"))
            if spec and spec.events:
                ev = next(iter(spec.events))
                m.addAction(f"Go to {ev} handler", lambda: self.create_handler(self.selected, ev))
        m.exec(global_pos)

    # ------------------------------------------------------------------ inline text edit
    def inline_edit(self, nid: str):
        node = self.screen.find(nid)
        if node is None:
            return
        key = {"Text": "data", "SelectableText": "data", "Tab": "text", "Tooltip": "message"}.get(node.get("type"))
        if key is None:
            self.select(nid, source="canvas")
            return
        rect = None
        host = None
        if self.stack.currentWidget() is self.scroll and nid in self.canvas.bounds:
            rect = self.canvas.to_view(self.canvas.bounds[nid]).toRect()
            host = self.canvas
        elif self.live is not None and nid in self.live.rects and self.live_box is not None:
            rect = self.live.rects[nid].toRect()
            host = self.live.view
        if host is None:
            return
        ed = QLineEdit(host)
        ed.setText(str((node.get("props") or {}).get(key, "")))
        ed.setGeometry(rect.adjusted(-2, -2, 40, 2))
        ed.setMinimumWidth(80)
        ed.selectAll()
        ed.show()
        ed.setFocus()
        done = {"v": False}

        def finish():
            if done["v"]:
                return
            done["v"] = True
            txt = ed.text()
            ed.deleteLater()
            if txt != (node.get("props") or {}).get(key):
                self.set_prop(nid, key, txt)
        ed.editingFinished.connect(finish)

    # ------------------------------------------------------------------ animations
    def play_animations(self):
        if self.live is not None and self.stack.currentWidget() is self.live_box:
            self.live.play()
            return
        self._anim_end = Q.anim_end(self.screen.tree)
        if self._anim_end <= 0:
            self.status("No animations on this screen (Animation section of a widget's properties)")
            return
        from time import perf_counter
        self._anim_clock = perf_counter()
        self.canvas.anim_t = 0.0
        self._anim_timer.start()

    def _anim_tick(self):
        from time import perf_counter
        t = (perf_counter() - self._anim_clock) * 1000
        if t > self._anim_end + 50:
            self._anim_timer.stop()
            self.canvas.anim_t = None
        else:
            self.canvas.anim_t = t
        self.canvas._img = None
        self.canvas.update()

    # ------------------------------------------------------------------ code / handlers
    def generated(self, format_code: bool = True):
        from . import codegen as CG
        user = None
        folder = self.project_folder()
        if folder is not None:
            ep = folder / CG.screen_files(self.screen)[1]
            if ep.exists():
                user = ep.read_text(encoding="utf-8")
        return CG.generate_screen(self.screen, user, format_code=format_code)

    def show_code(self):
        try:
            g = self.generated()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Dart code", f"Code generation failed:\n{e}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Generated Dart - {self.screen.name}")
        dlg.resize(820, 680)
        lay = QVBoxLayout(dlg)
        tabs = QTabWidget()
        for title, text in ((g.designer_path, g.designer_code), (g.events_path, g.events_code)):
            ed = QPlainTextEdit(text)
            ed.setReadOnly(True)
            ed.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            f = ed.font()
            f.setFamily("Consolas")
            f.setPointSize(10)
            ed.setFont(f)
            ed.setProperty("i18n_skip", True)
            tabs.addTab(ed, title)
        lay.addWidget(tabs)
        if g.warnings:
            w = QLabel("\n".join(g.warnings[:10]))
            w.setStyleSheet("color:#B26A00")
            lay.addWidget(w)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def handler_name(self, nid: str, event: str) -> str:
        node = self.screen.find(nid) or {}
        cur = (node.get("events") or {}).get(event)
        if cur and re.match(r"^[A-Za-z_]\w*$", cur):
            return cur
        base = node.get("name") or f"{node.get('type', 'w')}{str(nid).lstrip('w')}"
        base = base[:1].upper() + base[1:]
        ev = event[2:] if event.startswith("on") else event
        name = f"on{base}{ev[:1].upper()}{ev[1:]}"
        used = {h for n, *_ in self.screen.walk() for h in (n.get("events") or {}).values() if h}
        i = 2
        cand = name
        while cand in used and cur != cand:
            cand = f"{name}{i}"
            i += 1
        return cand

    def create_handler(self, nid: str | None, event: str):
        """VB double-click: wire the event to a handler, save + generate, open the user Dart file at it."""
        if not nid:
            return None
        name = self.handler_name(nid, event)
        node = self.screen.find(nid)
        if (node.get("events") or {}).get(event) != name:
            self.set_event(nid, event, name)
        folder = self.project_folder()
        if folder is None or self.path is None:
            self.status(f"{event} -> {name}: save the screen inside a Flutter project to write its code")
            return name
        self.save()
        from . import codegen as CG
        ep = folder / CG.screen_files(self.screen)[1]
        line = 1
        try:
            for i, ln in enumerate(ep.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(rf"\bvoid\s+{re.escape(name)}\s*\(", ln):
                    line = i + 1
                    break
        except OSError:
            pass
        self.openCode.emit(ep, line)
        return name

    # ------------------------------------------------------------------ files
    def save(self, path=None) -> bool:
        if path is not None:
            self.path = Path(path)
            self._project = self._project or find_project_folder(self.path)
        if self.path is None:
            p, _f = QFileDialog.getSaveFileName(
                self, "Save screen", f"{self.screen.name}{M.SCREEN_EXT}", f"Flutter screen (*{M.SCREEN_EXT})")
            if not p:
                return False
            self.path = Path(p)
            self._project = self._project or find_project_folder(self.path)
        try:
            self.screen.save(self.path)
        except OSError as e:
            QMessageBox.warning(self, "Save", f"Cannot save {self.path}:\n{e}")
            return False
        folder = self.project_folder()
        msg = f"Saved {self.path.name}"
        if folder is not None and (folder / "pubspec.yaml").is_file():
            try:
                from . import codegen as CG
                screens = []
                for p in M.find_screens(folder):
                    try:
                        screens.append(self.screen if p.resolve() == self.path.resolve() else M.Screen.load(p))
                    except (OSError, ValueError):
                        pass
                written, warnings = CG.write_screen(folder, self.screen, screens or None)
                if written:
                    msg += " - generated " + ", ".join(written[:4]) + (" ..." if len(written) > 4 else "")
                if warnings:
                    msg += f" ({len(warnings)} warning(s))"
            except Exception as e:  # noqa: BLE001
                msg += f" - code generation failed: {e}"
        self.undo_stack.setClean()
        self.status(msg)
        self.saved.emit(self.path)
        if self.live is not None and self.live.exact is not None:
            self.live.exact_reload()
        return True

    def reload_from_disk(self):
        if self.path and self.path.exists():
            self.screen = M.Screen.load(self.path)
            self.undo_stack.clear()
            self.selected = None
            self._after_change([{"op": "screen", "key": "tree"}])
