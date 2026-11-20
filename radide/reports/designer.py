"""Report Designer document (PyQt6): bands on a page, a toolbox of report items, the field list, a property
grid and a live Preview tab (the runtime's QtReportViewer). Edits the ``.rpt.json`` definition in place."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from PyQt6.QtCore import QMimeData, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont, QKeySequence, QPainter, QPen, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QTabWidget, QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import theme
from . import radreport as R

MIME_FIELD = "application/x-radreport-field"
CAP = 18          # band caption height (screen px)
GUT = 22          # left gutter (px)
TOP = 10
HANDLE = 6
TOOLS = [("Pointer", None), ("Text", "text"), ("Field", "field"), ("Expression", "expression"),
         ("Line", "line"), ("Box", "box"), ("Image", "image"), ("Barcode", "barcode"), ("QR Code", "qr"),
         ("Chart", "chart"), ("Page N of M", "pagenum"), ("Date", "date")]
DEFAULT_SIZE = {"text": (120, 18), "field": (100, 18), "expression": (100, 18), "line": (200, 4), "box": (120, 40),
                "image": (80, 60), "barcode": (140, 30), "qr": (60, 60), "chart": (240, 150),
                "pagenum": (120, 16), "date": (100, 16)}
FORMATS = ["", "N2", "N0", "F2", "C2", "P0", "D5", "yyyy-MM-dd", "dd/MM/yyyy", "yyyy-MM-dd HH:mm", "#,##0.00"]


def new_item(kind: str, x: float, y: float, w: float | None = None, h: float | None = None, rtl=False) -> dict:
    dw, dh = DEFAULT_SIZE.get(kind, (100, 18))
    it = {"x": round(x, 1), "y": round(y, 1), "w": round(w or dw, 1), "h": round(h or dh, 1)}
    al = "right" if rtl else "left"
    if kind == "text":
        it.update(type="text", text="Text", align=al)
    elif kind == "field":
        it.update(type="field", field="", align=al)
    elif kind == "expression":
        it.update(type="expression", expression="Sum('Amount')", format="N2", align="right")
    elif kind == "line":
        it.update(type="line", lineWidth=1, lineColor="#000000")
    elif kind == "box":
        it.update(type="box", lineWidth=1, lineColor="#000000", fill="")
    elif kind == "image":
        it.update(type="image", image="", keepAspect=True)
    elif kind == "barcode":
        it.update(type="barcode", barcodeType="code128", text="12345678", showText=True)
    elif kind == "qr":
        it.update(type="barcode", barcodeType="qr", text="https://example.com")
    elif kind == "chart":
        it.update(type="chart", chartType="bar", category="", valueField="", aggregate="sum", title="Chart")
    elif kind == "pagenum":
        it.update(type="text", text="Page {PageNumber} of {TotalPages}", align="right" if not rtl else "left",
                  fontSize=8)
    elif kind == "date":
        it.update(type="text", text="{Today():yyyy-MM-dd}", align=al, fontSize=8)
    return it


def design_op(it: dict, ox: float, oy: float, defn: dict) -> dict | None:
    """The op the designer draws for an item (placeholders instead of data)."""
    x, y = ox + float(it.get("x", 0)), oy + float(it.get("y", 0))
    w, h = float(it.get("w", 80)), float(it.get("h", 18))
    t = it.get("type")
    f = defn.get("font") or {}
    if t in ("text", "field", "expression"):
        text = it.get("text", "") if t == "text" else (f"[{it.get('field') or '?'}]" if t == "field"
                                                      else "=" + str(it.get("expression") or ""))
        rtl = it.get("rtl")
        if rtl in (None, "", "auto"):
            rtl = True if defn.get("rightToLeft") else None
        return {"op": "text", "x": x, "y": y, "w": w, "h": h, "text": text,
                "font": it.get("fontName") or f.get("name") or "Segoe UI",
                "size": float(it.get("fontSize") or f.get("size") or 10), "bold": bool(it.get("bold")),
                "italic": bool(it.get("italic")), "underline": bool(it.get("underline")),
                "color": it.get("color") or ("#1F5FAF" if t != "text" else "#000000"), "back": it.get("back") or "",
                "align": it.get("align") or "left", "valign": it.get("valign") or "middle", "rtl": rtl,
                "wrap": bool(it.get("wrap")), "bw": float(it.get("border") or 0),
                "bc": it.get("borderColor") or "#000000", "pad": 2}
    if t == "line":
        lw = float(it.get("lineWidth") or 1)
        col = it.get("lineColor") or "#000000"
        if it.get("diagonal"):
            return {"op": "line", "x1": x, "y1": y, "x2": x + w, "y2": y + h, "lw": lw, "color": col}
        if w >= h:
            return {"op": "line", "x1": x, "y1": y + h / 2, "x2": x + w, "y2": y + h / 2, "lw": lw, "color": col,
                    "style": it.get("lineStyle")}
        return {"op": "line", "x1": x + w / 2, "y1": y, "x2": x + w / 2, "y2": y + h, "lw": lw, "color": col,
                "style": it.get("lineStyle")}
    if t == "box":
        return {"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": it.get("fill") or "",
                "bw": float(it.get("lineWidth", 1) or 0), "bc": it.get("lineColor") or "#000000",
                "radius": float(it.get("radius") or 0)}
    if t == "image":
        return {"op": "image", "x": x, "y": y, "w": w, "h": h, "path": it.get("_abs", ""),
                "keep": it.get("keepAspect", True)}
    if t == "barcode":
        val = "12345678" if it.get("field") or "{" in str(it.get("text", "")) else str(it.get("text") or "123")
        return {"op": "barcode", "x": x, "y": y, "w": w, "h": h, "kind": it.get("barcodeType") or "code128",
                "value": val, "showText": bool(it.get("showText", True)), "color": it.get("color") or "#000000"}
    if t == "chart":
        return {"op": "chart", "x": x, "y": y, "w": w, "h": h, "kind": it.get("chartType") or "bar",
                "labels": ["A", "B", "C", "D"], "values": [4, 7, 3, 5], "title": it.get("title", ""),
                "font": it.get("fontName") or "Segoe UI", "size": float(it.get("fontSize") or 8),
                "showValues": bool(it.get("showValues", True)), "color": it.get("color") or ""}
    return None


# =============================================================================== canvas
class DesignCanvas(QWidget):
    selectionChanged = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, designer: "ReportDesigner"):
        super().__init__()
        self.d = designer
        self.zoom = 1.0
        self.snap = True
        self.tool: str | None = None
        self.sel: list[tuple[dict, dict]] = []        # (band, item)
        self.sel_band: tuple | None = None            # (kind, level, band)
        self._mode = ""
        self._start = QPointF()
        self._orig: list[tuple[dict, dict, dict]] = []
        self._handle = -1
        self._rubber: QRectF | None = None
        self._band_drag = None
        self._undo_pushed = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)

    @property
    def defn(self) -> dict:
        return self.d.defn

    def scale(self) -> float:
        return self.zoom * 96.0 / 72.0

    # ------------------------------------------------------------ geometry
    def layout(self):
        """[(kind, level, band, caption QRectF, body QRectF)]"""
        s = self.scale()
        pw, _ph = R.page_size(self.defn)
        ml, _mt, mr, _mb = R.margins(self.defn)
        cw = (pw - ml - mr) * s
        out, y = [], TOP
        for kind, level, band in R.all_bands(self.defn):
            cap = QRectF(GUT, y, cw, CAP)
            body = QRectF(GUT, y + CAP, cw, max(0.0, float(band.get("height") or 0)) * s)
            out.append((kind, level, band, cap, body))
            y += CAP + body.height()
        return out

    def sizeHint(self):
        lay = self.layout()
        h = (lay[-1][4].bottom() if lay else 200) + 40
        w = (lay[0][3].right() if lay else 400) + GUT + 20
        return QSize(int(w), int(h))

    def relayout(self):
        hint = self.sizeHint()
        self.setMinimumSize(hint)
        self.resize(max(hint.width(), self.parentWidget().width() if self.parentWidget() else 0), hint.height())
        self.update()

    def band_at(self, pos: QPointF):
        for kind, level, band, cap, body in self.layout():
            if cap.contains(pos):
                return kind, level, band, cap, body, "caption"
            if body.contains(pos):
                return kind, level, band, cap, body, "body"
        return None

    def item_rect(self, body: QRectF, it: dict) -> QRectF:
        s = self.scale()
        return QRectF(body.x() + float(it.get("x", 0)) * s, body.y() + float(it.get("y", 0)) * s,
                      max(2.0, float(it.get("w", 0)) * s), max(2.0, float(it.get("h", 0)) * s))

    def body_of(self, band: dict) -> QRectF | None:
        for _k, _l, b, _c, body in self.layout():
            if b is band:
                return body
        return None

    def item_at(self, pos: QPointF):
        for _kind, _level, band, _cap, body in reversed(self.layout()):
            if not body.adjusted(-3, -3, 3, 3).contains(pos):
                continue
            for it in reversed(band.get("items") or []):
                if self.item_rect(body, it).adjusted(-2, -2, 2, 2).contains(pos):
                    return band, it
        return None

    def handles(self, r: QRectF) -> list[QRectF]:
        pts = [r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(), QPointF(r.right(), r.center().y()),
               r.bottomRight(), QPointF(r.center().x(), r.bottom()), r.bottomLeft(), QPointF(r.left(), r.center().y())]
        return [QRectF(p.x() - HANDLE / 2, p.y() - HANDLE / 2, HANDLE, HANDLE) for p in pts]

    def _snap(self, v: float) -> float:
        return round(v / 4.0) * 4.0 if self.snap else round(v, 1)

    # ------------------------------------------------------------ painting
    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        s = self.scale()
        lay = self.layout()
        if not lay:
            return
        right = lay[0][3].right()
        cap_f = QFont("Segoe UI")
        cap_f.setPixelSize(11)
        for kind, level, band, cap, body in lay:
            selected = self.sel_band is not None and self.sel_band[2] is band
            p.fillRect(cap, QColor(theme.color("highlight") if selected else theme.color("header")))
            p.setPen(QColor(theme.color("highlight_text") if selected else theme.color("header_text")))
            p.setFont(cap_f)
            p.drawText(cap.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter.value),
                       "▼ " + R.band_title(self.defn, kind, level) +
                       (f"   ({band.get('height', 0)} pt)" if band.get("height") else "   (hidden - drag to open)"))
            p.fillRect(body, QColor(band.get("back") or "#FFFFFF"))
            # grid
            if self.snap and s * 8 >= 6:
                p.setPen(QPen(QColor("#D8D8D8"), 1))
                step = 8 * s
                yy = body.top()
                while yy < body.bottom():
                    xx = body.left()
                    while xx < body.right():
                        p.drawPoint(QPointF(xx, yy))
                        xx += step
                    yy += step
            p.save()
            p.setClipRect(body.adjusted(0, 0, 1, 1))
            p.translate(body.topLeft())
            for it in band.get("items") or []:
                op = design_op(self.d.resolved(it), 0, 0, self.defn)
                if op is not None:
                    R.paint_page(p, {"ops": [op]}, s)
            p.restore()
            p.setPen(QPen(QColor("#B0B0B0"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for it in band.get("items") or []:
                if it.get("type") in ("text", "field", "expression", "image", "barcode", "chart") and \
                        not it.get("border"):
                    p.drawRect(self.item_rect(body, it))
            p.setPen(QPen(QColor(theme.color("border")), 1))
            p.drawLine(QPointF(body.left(), body.bottom()), QPointF(right, body.bottom()))
        # selection
        p.setPen(QPen(QColor("#316AC5"), 1))
        for band, it in self.sel:
            body = self.body_of(band)
            if body is None:
                continue
            r = self.item_rect(body, it)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
            if len(self.sel) == 1:
                p.setBrush(QColor("#FFFFFF"))
                for h in self.handles(r):
                    p.drawRect(h)
        if self._rubber is not None:
            p.setPen(QPen(QColor("#316AC5"), 1, Qt.PenStyle.DotLine))
            p.setBrush(QColor(49, 106, 197, 40))
            p.drawRect(self._rubber.normalized())
        p.end()

    # ------------------------------------------------------------ selection
    def select(self, items: list[tuple[dict, dict]], band=None):
        self.sel = items
        self.sel_band = band
        self.update()
        self.selectionChanged.emit()

    def select_all(self):
        band = self.sel_band[2] if self.sel_band else (self.sel[0][0] if self.sel else None)
        if band is None:
            band = self.defn["bands"]["detail"]
        self.select([(band, it) for it in band.get("items") or []])

    # ------------------------------------------------------------ mouse
    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position()
        self._start = pos
        self._undo_pushed = False
        if e.button() != Qt.MouseButton.LeftButton:
            hit = self.item_at(pos)
            if hit is not None and hit not in [(b, i) for b, i in self.sel]:
                self.select([hit])
            return
        # band resize grip (bottom edge of a body)
        for kind, level, band, cap, body in self.layout():
            if abs(pos.y() - body.bottom()) <= 3 and body.left() <= pos.x() <= body.right() + GUT:
                self._mode = "band"
                self._band_drag = (band, float(band.get("height") or 0))
                return
        if len(self.sel) == 1:
            band, it = self.sel[0]
            body = self.body_of(band)
            if body is not None:
                for i, h in enumerate(self.handles(self.item_rect(body, it))):
                    if h.adjusted(-2, -2, 2, 2).contains(pos):
                        self._mode = "resize"
                        self._handle = i
                        self._orig = [(band, it, dict(it))]
                        return
        hb = self.band_at(pos)
        if self.tool and hb is not None and hb[5] == "body":
            self._mode = "create"
            self._create_band = hb
            self._rubber = QRectF(pos, pos)
            return
        hit = self.item_at(pos)
        if hit is not None:
            mods = e.modifiers()
            cur = list(self.sel)
            if mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                if any(i is hit[1] for _b, i in cur):
                    cur = [(b, i) for b, i in cur if i is not hit[1]]
                else:
                    cur.append(hit)
                self.select(cur)
                return
            if not any(i is hit[1] for _b, i in cur):
                self.select([hit])
            self._mode = "move"
            self._orig = [(b, i, dict(i)) for b, i in self.sel]
            return
        if hb is not None and hb[5] == "caption":
            self.select([], (hb[0], hb[1], hb[2]))
            return
        if hb is not None:
            self._mode = "rubber"
            self._rubber = QRectF(pos, pos)
            self._rubber_band = hb
            self.select([], None)
            return
        self.select([], None)

    def mouseMoveEvent(self, e):
        pos = e.position()
        s = self.scale()
        if not self._mode:
            cur = Qt.CursorShape.ArrowCursor
            for _k, _l, _b, _c, body in self.layout():
                if abs(pos.y() - body.bottom()) <= 3 and body.left() <= pos.x() <= body.right() + GUT:
                    cur = Qt.CursorShape.SplitVCursor
            if cur == Qt.CursorShape.ArrowCursor and len(self.sel) == 1:
                band, it = self.sel[0]
                body = self.body_of(band)
                if body is not None:
                    for i, h in enumerate(self.handles(self.item_rect(body, it))):
                        if h.adjusted(-2, -2, 2, 2).contains(pos):
                            cur = (Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeVerCursor,
                                   Qt.CursorShape.SizeBDiagCursor, Qt.CursorShape.SizeHorCursor)[i % 4]
            if cur == Qt.CursorShape.ArrowCursor and self.tool:
                cur = Qt.CursorShape.CrossCursor
            self.setCursor(cur)
            return
        dx, dy = (pos.x() - self._start.x()) / s, (pos.y() - self._start.y()) / s
        if self._mode in ("move", "resize", "band") and not self._undo_pushed and (abs(dx) + abs(dy)) * s > 2:
            self.d.push_undo()
            self._undo_pushed = True
        if self._mode == "band":
            band, h0 = self._band_drag
            band["height"] = max(0.0, self._snap(h0 + dy))
            self.relayout()
            self.changed.emit()
        elif self._mode == "move" and self._undo_pushed:
            for band, it, o in self._orig:
                it["x"] = max(0.0, self._snap(o["x"] + dx))
                it["y"] = max(0.0, self._snap(o["y"] + dy))
            self.update()
            self.changed.emit()
        elif self._mode == "resize" and self._undo_pushed:
            band, it, o = self._orig[0]
            x0, y0, x1, y1 = o["x"], o["y"], o["x"] + o["w"], o["y"] + o["h"]
            hd = self._handle
            if hd in (0, 6, 7):
                x0 = self._snap(x0 + dx)
            if hd in (2, 3, 4):
                x1 = self._snap(x1 + dx)
            if hd in (0, 1, 2):
                y0 = self._snap(y0 + dy)
            if hd in (4, 5, 6):
                y1 = self._snap(y1 + dy)
            it["x"], it["y"] = max(0.0, min(x0, x1 - 2)), max(0.0, min(y0, y1 - 2))
            it["w"], it["h"] = max(2.0, abs(x1 - x0)), max(2.0, abs(y1 - y0))
            self.update()
            self.changed.emit()
        elif self._mode in ("rubber", "create"):
            self._rubber = QRectF(self._start, pos)
            self.update()

    def mouseReleaseEvent(self, e):
        mode, self._mode = self._mode, ""
        s = self.scale()
        if mode == "create":
            kind, level, band, cap, body, _w = self._create_band
            r = (self._rubber or QRectF()).normalized()
            self._rubber = None
            x, y = (r.x() - body.x()) / s, (r.y() - body.y()) / s
            w, h = (r.width() / s, r.height() / s) if r.width() > 6 else (None, None)
            self.add_item(band, new_item(self.tool, self._snap(max(0, x)), self._snap(max(0, y)), w, h,
                                         bool(self.defn.get("rightToLeft"))))
            if not (e.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.d.set_tool(None)
        elif mode == "rubber":
            r = (self._rubber or QRectF()).normalized()
            self._rubber = None
            band, body = self._rubber_band[2], self._rubber_band[4]
            picked = [(band, it) for it in band.get("items") or [] if r.intersects(self.item_rect(body, it))]
            if picked:
                self.select(picked)
            else:
                self.select([], self._rubber_band[:3])
        elif mode == "move" and self._undo_pushed:
            # dropped over another band: the items move there
            target = self.band_at(e.position())
            if target is not None and len(self.sel) >= 1 and target[2] is not self.sel[0][0]:
                tb, tbody = target[2], target[4]
                moved = []
                for band, it in self.sel:
                    if it in band.get("items", []):
                        r = self.item_rect(self.body_of(band), it)
                        band["items"].remove(it)
                        it["y"] = max(0.0, self._snap((r.y() - tbody.y()) / s))
                        tb.setdefault("items", []).append(it)
                        moved.append((tb, it))
                self.select(moved)
            self.selectionChanged.emit()
        elif mode in ("resize", "band"):
            self.selectionChanged.emit()
        self.update()

    def mouseDoubleClickEvent(self, e):
        hit = self.item_at(e.position())
        if hit is None:
            return
        band, it = hit
        key = {"text": "text", "field": "field", "expression": "expression", "barcode": "text",
               "chart": "title"}.get(it.get("type"))
        if key is None:
            return
        if it.get("type") == "field":
            cols = self.d.columns
            if cols:
                v, ok = QInputDialog.getItem(self, "Field", "Field:", cols,
                                             max(0, cols.index(it["field"])) if it.get("field") in cols else 0,
                                             True)
            else:
                v, ok = QInputDialog.getText(self, "Field", "Field name:", text=it.get("field", ""))
        else:
            v, ok = QInputDialog.getMultiLineText(self, "Edit", key.capitalize() + ":", str(it.get(key, "")))
        if ok:
            self.d.push_undo()
            it[key] = v
            self.update()
            self.changed.emit()
            self.selectionChanged.emit()

    def contextMenuEvent(self, e):
        m = QMenu(self)
        if self.sel:
            m.addAction("Delete", self.delete_selection)
            m.addAction("Duplicate\tCtrl+D", self.duplicate)
            m.addSeparator()
            m.addAction("Bring to Front", lambda: self.order(True))
            m.addAction("Send to Back", lambda: self.order(False))
            if len(self.sel) > 1:
                sub = m.addMenu("Align")
                for t, k in (("Lefts", "left"), ("Rights", "right"), ("Tops", "top"), ("Bottoms", "bottom"),
                             ("Same Width", "width"), ("Same Height", "height")):
                    sub.addAction(t, lambda k=k: self.align(k))
        hb = self.band_at(e.pos().toPointF())
        if hb is not None:
            m.addSeparator()
            m.addAction(f"Select all in {R.band_title(self.defn, hb[0], hb[1])}",
                        lambda: self.select([(hb[2], it) for it in hb[2].get("items") or []]))
            m.addAction("Band Properties", lambda: self.select([], hb[:3]))
        m.addSeparator()
        m.addAction("Insert Group...", self.d.edit_groups)
        m.addAction("Report Properties", lambda: self.select([], None))
        m.exec(e.globalPos())

    # ------------------------------------------------------------ edits
    def add_item(self, band: dict, it: dict, push=True):
        if push:
            self.d.push_undo()
        names = {i.get("name") for _k, _l, b in R.all_bands(self.defn) for i in b.get("items") or []}
        base = it.get("type", "item").capitalize()
        n = 1
        while f"{base}{n}" in names:
            n += 1
        it.setdefault("name", f"{base}{n}")
        band.setdefault("items", []).append(it)
        if float(it["y"]) + float(it["h"]) > float(band.get("height") or 0):
            band["height"] = float(it["y"]) + float(it["h"])
            self.relayout()
        self.select([(band, it)])
        self.changed.emit()

    def delete_selection(self):
        if not self.sel:
            return
        self.d.push_undo()
        for band, it in self.sel:
            if it in band.get("items", []):
                band["items"].remove(it)
        self.select([])
        self.changed.emit()

    def duplicate(self):
        if not self.sel:
            return
        self.d.push_undo()
        out = []
        for band, it in self.sel:
            c = copy.deepcopy(it)
            c.pop("name", None)
            c["x"] = float(c.get("x", 0)) + 8
            c["y"] = float(c.get("y", 0)) + 4
            self.add_item(band, c, push=False)
            out.append((band, c))
        self.select(out)

    def copy_selection(self):
        from PyQt6.QtWidgets import QApplication
        if self.sel:
            QApplication.clipboard().setText(json.dumps({"radreport-items": [it for _b, it in self.sel]}))

    def paste(self):
        from PyQt6.QtWidgets import QApplication
        try:
            data = json.loads(QApplication.clipboard().text())
            items = data["radreport-items"]
        except (ValueError, KeyError, TypeError):
            return
        band = self.sel[0][0] if self.sel else (self.sel_band[2] if self.sel_band else self.defn["bands"]["detail"])
        self.d.push_undo()
        out = []
        for it in items:
            c = copy.deepcopy(it)
            c.pop("name", None)
            self.add_item(band, c, push=False)
            out.append((band, c))
        self.select(out)

    def nudge(self, dx, dy, resize=False):
        if not self.sel:
            return
        self.d.push_undo()
        for _b, it in self.sel:
            if resize:
                it["w"] = max(2.0, float(it["w"]) + dx)
                it["h"] = max(2.0, float(it["h"]) + dy)
            else:
                it["x"] = max(0.0, float(it["x"]) + dx)
                it["y"] = max(0.0, float(it["y"]) + dy)
        self.update()
        self.changed.emit()
        self.selectionChanged.emit()

    def order(self, front: bool):
        self.d.push_undo()
        for band, it in self.sel:
            items = band.get("items", [])
            if it in items:
                items.remove(it)
                items.append(it) if front else items.insert(0, it)
        self.update()
        self.changed.emit()

    def align(self, how: str):
        if len(self.sel) < 2:
            return
        self.d.push_undo()
        ref = self.sel[0][1]
        for _b, it in self.sel[1:]:
            if how == "left":
                it["x"] = ref["x"]
            elif how == "right":
                it["x"] = float(ref["x"]) + float(ref["w"]) - float(it["w"])
            elif how == "top":
                it["y"] = ref["y"]
            elif how == "bottom":
                it["y"] = float(ref["y"]) + float(ref["h"]) - float(it["h"])
            elif how == "width":
                it["w"] = ref["w"]
            elif how == "height":
                it["h"] = ref["h"]
        self.update()
        self.changed.emit()

    def keyPressEvent(self, e):
        k = e.key()
        step = 1.0 if e.modifiers() & Qt.KeyboardModifier.ControlModifier else 4.0
        resize = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        moves = {Qt.Key.Key_Left: (-step, 0), Qt.Key.Key_Right: (step, 0), Qt.Key.Key_Up: (0, -step),
                 Qt.Key.Key_Down: (0, step)}
        if k in moves and self.sel:
            self.nudge(*moves[k], resize=resize)
        elif k == Qt.Key.Key_Delete:
            self.delete_selection()
        elif k == Qt.Key.Key_Escape:
            self.d.set_tool(None)
            self.select([])
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------ drag & drop of fields
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_FIELD):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_FIELD) and self.band_at(e.position()) is not None:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        hb = self.band_at(e.position())
        if hb is None:
            return
        data = json.loads(bytes(e.mimeData().data(MIME_FIELD)).decode("utf-8"))
        s = self.scale()
        x = self._snap(max(0, (e.position().x() - hb[4].x()) / s))
        y = self._snap(max(0, (e.position().y() - hb[4].y()) / s))
        it = new_item(data.get("kind", "field"), x, y, rtl=bool(self.defn.get("rightToLeft")))
        it.update({k: v for k, v in data.items() if k != "kind"})
        self.add_item(hb[2], it)
        e.acceptProposedAction()


# =============================================================================== property grid
def _rtl_text(v):
    return {True: "Right to left", False: "Left to right"}.get(v, "Auto")


class PropertyGrid(QTableWidget):
    edited = pyqtSignal(str)

    def __init__(self, designer: "ReportDesigner"):
        super().__init__(0, 2)
        self.d = designer
        self.setHorizontalHeaderLabels(["Property", "Value"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(22)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.target: dict | None = None
        self.title = ""

    def show_for(self, target: dict | None, specs: list[tuple], title: str):
        self.target, self.title = target, title
        self.clearContents()
        self.setRowCount(len(specs))
        for row, spec in enumerate(specs):
            key, label, kind = spec[0], spec[1], spec[2]
            extra = spec[3] if len(spec) > 3 else ()
            it = QTableWidgetItem(label)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it.setToolTip(key)
            self.setItem(row, 0, it)
            self.setCellWidget(row, 1, self._editor(target, key, kind, extra))

    def _set(self, target, key, value):
        self.d.push_undo()
        if value is None or value == "":
            if key in ("text", "field", "expression", "name", "query", "title"):
                target[key] = ""
            else:
                target.pop(key, None)
        else:
            target[key] = value
        self.edited.emit(key)

    def _editor(self, t, key, kind, extra):
        v = t.get(key) if t is not None else None
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(v if v is not None else (extra[0] if extra else False)))
            w.toggled.connect(lambda on: self._set(t, key, bool(on)))
            return w
        if kind in ("num", "int"):
            w = QDoubleSpinBox()
            w.setRange(-10000, 100000)
            w.setDecimals(0 if kind == "int" else 1)
            w.setValue(float(v if v is not None else (extra[0] if extra else 0)))
            w.setKeyboardTracking(False)
            w.valueChanged.connect(lambda x: self._set(t, key, int(x) if kind == "int" else round(x, 1)))
            return w
        if kind == "enum":
            w = QComboBox()
            w.addItems(list(extra))
            cur = str(v if v is not None else extra[0])
            if kind == "enum" and key == "rtl":
                cur = _rtl_text(v)
            w.setCurrentText(cur)
            if key == "rtl":
                w.currentTextChanged.connect(lambda s: self._set(t, key, {"Right to left": True,
                                                                          "Left to right": False}.get(s)))
            else:
                w.currentTextChanged.connect(lambda s: self._set(t, key, s))
            return w
        if kind in ("field", "format", "font"):
            w = QFontComboBox() if kind == "font" else QComboBox()
            w.setEditable(True)
            if kind == "field":
                w.addItems([""] + list(self.d.columns))
            elif kind == "format":
                w.addItems(FORMATS)
            w.setCurrentText(str(v or ""))
            w.lineEdit().editingFinished.connect(lambda: self._set(t, key, w.currentText()))
            w.activated.connect(lambda _i: self._set(t, key, w.currentText()))
            return w
        if kind == "color":
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(2)
            b = QPushButton(str(v or "(none)"))
            b.setStyleSheet(f"text-align:left; padding-left:4px; border-left: 14px solid {v};" if v else
                            "text-align:left; padding-left:4px;")

            def pick():
                c = QColorDialog.getColor(QColor(v or "#000000"), self, "Colour")
                if c.isValid():
                    self._set(t, key, c.name().upper())
                    self.d.refresh_props()
            b.clicked.connect(pick)
            x = QToolButton()
            x.setText("x")
            x.setToolTip("No colour")
            x.clicked.connect(lambda: (self._set(t, key, ""), self.d.refresh_props()))
            h.addWidget(b, 1)
            h.addWidget(x)
            return w
        if kind == "file":
            b = QPushButton(str(v or "(none)") + "   ...")
            b.setStyleSheet("text-align:left; padding-left:4px;")

            def pick_file():
                f, _ = QFileDialog.getOpenFileName(self, "Image", str(self.d.folder),
                                                   "Images (*.png *.jpg *.jpeg *.gif *.bmp);;All files (*)")
                if f:
                    try:
                        rel = Path(f).resolve().relative_to(Path(self.d.folder).resolve()).as_posix()
                    except ValueError:
                        rel = f
                    self._set(t, key, rel)
                    self.d.refresh_props()
            b.clicked.connect(pick_file)
            return b
        if kind == "margins":
            w = QLineEdit(", ".join(str(round(float(x), 1)) for x in (v or [36, 36, 36, 36])))
            w.setToolTip("left, top, right, bottom in points (72 = 1 inch)")

            def apply_m():
                try:
                    nums = [float(x) for x in w.text().replace(";", ",").split(",")]
                    if len(nums) == 4:
                        self._set(t, key, nums)
                except ValueError:
                    pass
            w.editingFinished.connect(apply_m)
            return w
        w = QLineEdit(str(v if v is not None else ""))
        w.editingFinished.connect(lambda: str(t.get(key, "") if t else "") != w.text() and
                                  self._set(t, key, w.text()))
        return w


FONT_SPECS = [("fontName", "Font", "font"), ("fontSize", "Font size (0 = default)", "num", (0,)), ("bold", "Bold", "bool"),
              ("italic", "Italic", "bool"), ("underline", "Underline", "bool"), ("color", "Fore colour", "color"),
              ("back", "Back colour", "color"), ("align", "Align", "enum", ("left", "center", "right", "justify")),
              ("valign", "Vertical align", "enum", ("middle", "top", "bottom")),
              ("rtl", "Text direction", "enum", ("Auto", "Right to left", "Left to right")),
              ("wrap", "Word wrap", "bool"), ("border", "Border width", "num"), ("borderColor", "Border colour", "color")]
GEO = [("name", "(Name)", "str"), ("x", "Left", "num"), ("y", "Top", "num"), ("w", "Width", "num"),
       ("h", "Height", "num")]


def item_specs(it: dict) -> list[tuple]:
    t = it.get("type")
    vis = [("visibleIf", "Visible if (expression)", "str")]
    if t == "text":
        return GEO + [("text", "Text ({expressions})", "str")] + FONT_SPECS + vis
    if t == "field":
        return GEO + [("field", "Field", "field"), ("format", "Format", "format"), ("hideZero", "Hide zero", "bool")] \
            + FONT_SPECS + vis
    if t == "expression":
        return GEO + [("expression", "Expression", "str"), ("format", "Format", "format"),
                      ("hideZero", "Hide zero", "bool")] + FONT_SPECS + vis
    if t == "line":
        return GEO + [("lineWidth", "Line width", "num", (1,)), ("lineColor", "Line colour", "color"),
                      ("lineStyle", "Style", "enum", ("solid", "dash", "dot")), ("diagonal", "Diagonal", "bool")] + vis
    if t == "box":
        return GEO + [("fill", "Fill colour", "color"), ("lineWidth", "Border width", "num", (1,)),
                      ("lineColor", "Border colour", "color"), ("radius", "Corner radius", "num")] + vis
    if t == "image":
        return GEO + [("image", "Image file", "file"), ("imageField", "Image field (path / BLOB)", "field"),
                      ("keepAspect", "Keep aspect ratio", "bool", (True,))] + vis
    if t == "barcode":
        return GEO + [("barcodeType", "Symbology", "enum", ("code128", "ean13", "ean8", "code39", "upca", "qr")),
                      ("text", "Value ({expressions})", "str"), ("field", "Value field", "field"),
                      ("showText", "Show text", "bool", (True,)), ("color", "Colour", "color")] + vis
    if t == "chart":
        return GEO + [("chartType", "Chart type", "enum", ("bar", "line", "pie")), ("title", "Title", "str"),
                      ("category", "Category field", "field"), ("valueField", "Value field", "field"),
                      ("aggregate", "Aggregate", "enum", ("sum", "count", "avg", "min", "max")),
                      ("scope", "Data", "enum", ("band", "report")), ("fontSize", "Font size", "num", (8,)),
                      ("showValues", "Show values", "bool", (True,)), ("color", "Bar colour", "color")] + vis
    return GEO


def band_specs(kind: str) -> list[tuple]:
    out = [("height", "Height (pt)", "num"), ("back", "Back colour", "color"),
           ("visibleIf", "Visible if (expression)", "str")]
    if kind == "reportHeader":
        out.append(("newPageAfter", "New page after", "bool"))
    if kind in ("pageHeader", "pageFooter"):
        out.append(("skipFirstPage", "Not on first page", "bool"))
    if kind == "detail":
        out.append(("alternateColor", "Alternate row colour", "color"))
    return out


GROUP_SPECS = [("name", "Group name", "str"), ("field", "Group by field", "field"),
               ("expression", "Group by expression", "str"), ("sort", "Sort", "enum", ("asc", "desc")),
               ("newPage", "New page for each group", "bool"), ("repeatHeader", "Repeat header on new page", "bool"),
               ("keepTogether", "Keep group together", "bool")]
REPORT_SPECS = [("name", "(Name)", "str"), ("title", "Title", "str"), ("rightToLeft", "Right to left (Arabic)", "bool"),
                ("mirrorLayout", "Mirror layout (RTL)", "bool"), ("currency", "Currency symbol (C format)", "str"),
                ("filter", "Filter (expression)", "str"), ("sortByGroups", "Sort rows by groups", "bool", (True,))]
PAGE_SPECS = [("size", "Paper", "enum", tuple(R.PAPER)), ("orientation", "Orientation", "enum",
                                                         ("Portrait", "Landscape")),
              ("margins", "Margins (L, T, R, B)", "margins")]
FONT_DEF_SPECS = [("name", "Default font", "font"), ("size", "Default size", "num", (10,))]


# =============================================================================== dialogs
class DataSourceDialog(QDialog):
    """Data source: SQL query on a connection, CSV / JSON file, a Data panel dataset or none."""

    def __init__(self, parent, ds: dict, folder: Path, connections: list[dict], datasets: list[dict],
                 params: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Report Data Source")
        self.resize(640, 520)
        self.folder = Path(folder)
        self.connections = connections
        self.datasets = datasets
        self.params = params or {}
        self.result_ds = dict(ds or {"type": "none"})
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(["None (data given by code: SetData)", "SQL query", "CSV / JSON file", "Data panel dataset"])
        form.addRow("Type:", self.kind)
        lay.addLayout(form)
        self.stack = QStackedWidget()
        self.stack.addWidget(QLabel("The program gives the rows: ReportViewer1.SetData(rows)  (a list of dicts)."))
        # SQL
        w = QWidget()
        f = QFormLayout(w)
        self.conn = QComboBox()
        for c in connections:
            self.conn.addItem(f"{c.get('name')}  ({c.get('kind')})", c)
        self.conn.addItem("SQLite file...", None)
        self.conn.activated.connect(self._conn_pick)
        f.addRow("Connection:", self.conn)
        self.tables = QComboBox()
        self.tables.activated.connect(lambda _i: self.tables.currentText() and self.sql.setPlainText(
            f"SELECT * FROM \"{self.tables.currentText()}\""))
        f.addRow("Tables:", self.tables)
        self.sql = QPlainTextEdit()
        self.sql.setPlaceholderText("SELECT ... FROM ... WHERE Id = :Id   (:Name = report parameter)")
        f.addRow("Query:", self.sql)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("MySQL / PostgreSQL only - not saved in the report")
        f.addRow("Password:", self.password)
        self.stack.addWidget(w)
        # file
        w = QWidget()
        f = QFormLayout(w)
        row = QHBoxLayout()
        self.file = QLineEdit()
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        row.addWidget(self.file, 1)
        row.addWidget(b)
        f.addRow("File:", row)
        self.root = QLineEdit()
        self.root.setPlaceholderText("JSON: dotted path to the list (optional)")
        f.addRow("Root:", self.root)
        self.stack.addWidget(w)
        # dataset
        w = QWidget()
        f = QFormLayout(w)
        self.dataset = QComboBox()
        for d in datasets:
            self.dataset.addItem(f"{d.get('name')}  ({d.get('file')}, form {d.get('form', '')})", d)
        f.addRow("Dataset:", self.dataset)
        if not datasets:
            f.addRow(QLabel("No datasets: add JSON / CSV sources in the Data panel of a form."))
        self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)
        self.kind.currentIndexChanged.connect(self.stack.setCurrentIndex)
        row = QHBoxLayout()
        test = QPushButton("Test")
        test.clicked.connect(self.test)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        row.addWidget(test)
        row.addWidget(self.info, 1)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._load(self.result_ds)

    def _load(self, ds):
        t = ds.get("type", "none")
        idx = {"none": 0, "inline": 0, "sql": 1, "csv": 2, "json": 2, "dataset": 3}.get(t, 0)
        self.kind.setCurrentIndex(idx)
        self.stack.setCurrentIndex(idx)
        if t == "sql":
            c = ds.get("connection") or {}
            for i in range(self.conn.count()):
                d = self.conn.itemData(i)
                if d and d.get("name") == c.get("name") and d.get("kind") == c.get("kind"):
                    self.conn.setCurrentIndex(i)
                    break
            else:
                if c:
                    self.conn.insertItem(0, f"{c.get('path') or c.get('database')}  ({c.get('kind')})", c)
                    self.conn.setCurrentIndex(0)
            self.sql.setPlainText(ds.get("query", ""))
            self._fill_tables()
        elif t in ("csv", "json"):
            self.file.setText(ds.get("file", ""))
            self.root.setText(ds.get("root", ""))
        elif t == "dataset":
            for i in range(self.dataset.count()):
                if (self.dataset.itemData(i) or {}).get("name") == ds.get("name"):
                    self.dataset.setCurrentIndex(i)

    def _rel(self, path: str) -> str:
        try:
            return Path(path).resolve().relative_to(self.folder.resolve()).as_posix()
        except ValueError:
            return str(path)

    def _conn_pick(self, _i=0):
        if self.conn.currentData() is None:
            f, _ = QFileDialog.getOpenFileName(self, "SQLite database", str(self.folder),
                                               "SQLite (*.db *.sqlite *.sqlite3 *.db3);;All files (*)")
            if not f:
                return
            c = {"name": Path(f).stem, "kind": "sqlite", "path": self._rel(f)}
            self.conn.insertItem(0, f"{c['path']}  (sqlite)", c)
            self.conn.setCurrentIndex(0)
        self._fill_tables()

    def _fill_tables(self):
        self.tables.clear()
        c = self.conn.currentData()
        if not c or c.get("kind") != "sqlite":
            return
        try:
            db = R.connect(c, str(self.folder))
            names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') "
                                              "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            db.close()
            self.tables.addItems([""] + names)
        except Exception as e:  # noqa: BLE001
            self.info.setText(str(e))

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Data file", str(self.folder), "Data (*.csv *.json);;All files (*)")
        if f:
            self.file.setText(self._rel(f))

    def build(self) -> dict:
        i = self.kind.currentIndex()
        if i == 1:
            c = dict(self.conn.currentData() or {})
            c.pop("password", None)
            c.pop("remember_password", None)
            return {"type": "sql", "connection": c, "query": self.sql.toPlainText().strip()}
        if i == 2:
            f = self.file.text().strip()
            return {"type": "json" if f.lower().endswith(".json") else "csv", "file": f,
                    "root": self.root.text().strip()}
        if i == 3:
            d = dict(self.dataset.currentData() or {})
            return {"type": "dataset", "name": d.get("name", ""), "file": d.get("file", ""),
                    "root": d.get("root", "")}
        return {"type": "none"}

    def test(self) -> bool:
        try:
            cols, rows = R.fetch(self.build(), str(self.folder), self.params, self.password.text() or None, limit=50)
        except Exception as e:  # noqa: BLE001
            theme.role(self.info, "error")
            self.info.setText(str(e))
            return False
        theme.role(self.info, "success")
        self.info.setText(f"OK - {len(cols)} fields: {', '.join(cols[:12])}{' ...' if len(cols) > 12 else ''}"
                          f" ({len(rows)} sample rows)")
        return True

    def _ok(self):
        self.result_ds = self.build()
        self.accept()


class ParametersDialog(QDialog):
    def __init__(self, parent, params: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("Report Parameters")
        self.resize(560, 300)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Use them as :Name in the SQL query and Parameters.Name in expressions. "
                             "Code: ReportViewer1.Parameters[\"Name\"] = value"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Default", "Prompt"])
        self.table.horizontalHeader().setStretchLastSection(True)
        for p in params:
            self._add(p)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        a = QPushButton("Add")
        a.clicked.connect(lambda: self._add({"name": f"Param{self.table.rowCount() + 1}", "type": "str"}))
        d = QPushButton("Remove")
        d.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        row.addWidget(a)
        row.addWidget(d)
        row.addStretch(1)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add(self, p):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(str(p.get("name", ""))))
        cb = QComboBox()
        cb.addItems(["str", "int", "float", "date", "bool"])
        cb.setCurrentText(str(p.get("type") or "str"))
        self.table.setCellWidget(r, 1, cb)
        self.table.setItem(r, 2, QTableWidgetItem("" if p.get("default") is None else str(p.get("default"))))
        self.table.setItem(r, 3, QTableWidgetItem(str(p.get("prompt", ""))))

    def params(self) -> list[dict]:
        out = []
        for r in range(self.table.rowCount()):
            name = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            if not name.isidentifier():
                continue
            d = self.table.item(r, 2).text().strip() if self.table.item(r, 2) else ""
            out.append({"name": name, "type": self.table.cellWidget(r, 1).currentText(),
                        "default": R._convert(d) if d else None,
                        "prompt": self.table.item(r, 3).text() if self.table.item(r, 3) else ""})
        return out


class GroupsDialog(QDialog):
    def __init__(self, parent, groups: list[dict], columns: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Report Groups")
        self.resize(620, 300)
        self.groups = [copy.deepcopy(g) for g in groups]
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Rows are grouped (and sorted) by these fields, outermost first. Each group has a "
                             "header and a footer band - put Sum(...) / Count() totals in the footer."))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Group by field", "New page", "Repeat header", "Keep together"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.columns = columns
        for g in self.groups:
            self._add(g)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, fn in (("Add", lambda: self._add(R.new_group(columns[0] if columns else ""), new=True)),
                         ("Remove", self._remove), ("Up", lambda: self._move(-1)), ("Down", lambda: self._move(1))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add(self, g, new=False):
        if new:
            self.groups.append(g)
        r = self.table.rowCount()
        self.table.insertRow(r)
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItems(self.columns)
        cb.setCurrentText(g.get("field", ""))
        self.table.setCellWidget(r, 0, cb)
        for c, key in ((1, "newPage"), (2, "repeatHeader"), (3, "keepTogether")):
            chk = QCheckBox()
            chk.setChecked(bool(g.get(key)))
            self.table.setCellWidget(r, c, chk)

    def _sync(self):
        for r, g in enumerate(self.groups):
            g["field"] = self.table.cellWidget(r, 0).currentText().strip()
            if not g.get("name") or g["name"].startswith("Group_"):
                g["name"] = f"Group_{g['field'] or r + 1}"
            for c, key in ((1, "newPage"), (2, "repeatHeader"), (3, "keepTogether")):
                g[key] = self.table.cellWidget(r, c).isChecked()

    def _remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.groups):
            self._sync()
            del self.groups[r]
            self._rebuild()

    def _move(self, d):
        r = self.table.currentRow()
        if 0 <= r < len(self.groups) and 0 <= r + d < len(self.groups):
            self._sync()
            self.groups[r], self.groups[r + d] = self.groups[r + d], self.groups[r]
            self._rebuild()
            self.table.setCurrentCell(r + d, 0)

    def _rebuild(self):
        self.table.setRowCount(0)
        for g in self.groups:
            self._add(g)

    def result_groups(self) -> list[dict]:
        self._sync()
        return [g for g in self.groups if g.get("field") or g.get("expression")]


# =============================================================================== field list / toolbox
class FieldList(QTreeWidget):
    insertRequested = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setToolTip("Drag a field onto a band, or double-click it to add a column (header + detail)")
        self.itemDoubleClicked.connect(self._dbl)

    def fill(self, columns: list[str], params: list[dict]):
        self.clear()
        f = QTreeWidgetItem(self, ["Fields"])
        for c in columns:
            it = QTreeWidgetItem(f, [c])
            it.setData(0, Qt.ItemDataRole.UserRole, {"kind": "field", "field": c})
        p = QTreeWidgetItem(self, ["Parameters"])
        for prm in params:
            it = QTreeWidgetItem(p, [prm.get("name", "")])
            it.setData(0, Qt.ItemDataRole.UserRole, {"kind": "expression", "expression": f"Parameters.{prm['name']}",
                                                     "format": ""})
        s = QTreeWidgetItem(self, ["Special fields"])
        for label, data in (("Page N of M", {"kind": "pagenum"}), ("Print date", {"kind": "date"}),
                            ("Record count", {"kind": "expression", "expression": "RecordCount", "format": ""}),
                            ("Row number", {"kind": "expression", "expression": "RowNumber", "format": ""}),
                            ("Report title", {"kind": "text", "text": "{ReportTitle}"})):
            it = QTreeWidgetItem(s, [label])
            it.setData(0, Qt.ItemDataRole.UserRole, data)
        self.expandAll()

    def mimeData(self, items):
        data = items[0].data(0, Qt.ItemDataRole.UserRole) if items else None
        if not data:
            return QMimeData()
        m = QMimeData()
        m.setData(MIME_FIELD, json.dumps(data).encode("utf-8"))
        return m

    def startDrag(self, actions):
        it = self.currentItem()
        if it is None or not it.data(0, Qt.ItemDataRole.UserRole):
            return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData([it]))
        drag.exec(Qt.DropAction.CopyAction)

    def _dbl(self, it, _c):
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.insertRequested.emit(dict(data))


# =============================================================================== the document
class ReportDesigner(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()

    def __init__(self, path, connections_fn=None, datasets_fn=None, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.folder = self.path.parent
        self.connections_fn = connections_fn or (lambda: [])
        self.datasets_fn = datasets_fn or (lambda: [])
        self.defn = R.load_definition(self.path) if self.path.exists() else R.new_report(
            self.path.name.replace(".rpt.json", ""))
        self.columns: list[str] = []
        self.password: str | None = None
        self._undo: list[str] = []
        self._redo: list[str] = []
        self._modified = False
        self._viewer = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        tb = QToolBar()
        tb.setIconSize(tb.iconSize() * 0.8)
        st = self.style()
        sp = st.StandardPixmap
        tb.addAction(st.standardIcon(sp.SP_DialogSaveButton), "Save", self.save)
        tb.addSeparator()
        self.a_undo = tb.addAction(st.standardIcon(sp.SP_ArrowBack), "Undo", self.undo)
        self.a_redo = tb.addAction(st.standardIcon(sp.SP_ArrowForward), "Redo", self.redo)
        tb.addSeparator()
        tb.addAction("Data Source...", self.edit_data_source)
        tb.addAction("Parameters...", self.edit_parameters)
        tb.addAction("Groups...", self.edit_groups)
        tb.addSeparator()
        self.zoom = QComboBox()
        self.zoom.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom.setCurrentText("100%")
        self.zoom.currentTextChanged.connect(self._zoom)
        tb.addWidget(QLabel(" Zoom "))
        tb.addWidget(self.zoom)
        self.a_snap = tb.addAction("Snap to grid")
        self.a_snap.setCheckable(True)
        self.a_snap.setChecked(True)
        self.a_snap.toggled.connect(self._snap)
        tb.addSeparator()
        tb.addAction(st.standardIcon(sp.SP_MediaPlay), "Preview", lambda: self.tabs.setCurrentIndex(1))
        lay.addWidget(tb)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.South)
        lay.addWidget(self.tabs, 1)
        # design page
        design = QSplitter(Qt.Orientation.Horizontal)
        left = QSplitter(Qt.Orientation.Vertical)
        self.toolbox = QListWidget()
        for label, kind in TOOLS:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, kind)
            self.toolbox.addItem(it)
        self.toolbox.setCurrentRow(0)
        self.toolbox.currentItemChanged.connect(
            lambda it, _p: self.set_tool(it.data(Qt.ItemDataRole.UserRole) if it else None, from_box=True))
        self.fields = FieldList()
        self.fields.insertRequested.connect(self.insert_column)
        left.addWidget(self._titled("Report Items", self.toolbox))
        left.addWidget(self._titled("Field List", self.fields))
        design.addWidget(left)
        self.canvas = DesignCanvas(self)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        theme.role(self.scroll, "stage")
        design.addWidget(self.scroll)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.prop_title = QLabel("Report")
        theme.role(self.prop_title, "heading")
        self.props = PropertyGrid(self)
        self.props.edited.connect(self._prop_edited)
        self.help = QLabel("")
        self.help.setWordWrap(True)
        theme.role(self.help, "help")
        rl.addWidget(self.prop_title)
        rl.addWidget(self.props, 1)
        rl.addWidget(self.help)
        design.addWidget(right)
        design.setSizes([170, 700, 280])
        design.setStretchFactor(1, 1)
        self.tabs.addTab(design, "Design")
        self.preview_host = QWidget()
        QVBoxLayout(self.preview_host).setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(self.preview_host, "Preview")
        self.tabs.currentChanged.connect(self._tab)
        self.status = QLabel("")
        theme.role(self.status, "muted")
        lay.addWidget(self.status)
        self.canvas.selectionChanged.connect(self.refresh_props)
        self.canvas.changed.connect(lambda: self.set_modified(True))
        for seq, fn in ((QKeySequence.StandardKey.Undo, self.undo), (QKeySequence.StandardKey.Redo, self.redo),
                        (QKeySequence.StandardKey.Save, self.save), (QKeySequence.StandardKey.Copy,
                                                                     self.canvas.copy_selection),
                        (QKeySequence.StandardKey.Paste, self.canvas.paste),
                        (QKeySequence.StandardKey.SelectAll, self.canvas.select_all),
                        (QKeySequence("Ctrl+D"), self.canvas.duplicate)):
            sc = QShortcut(seq, self.canvas)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(fn)
        self._update_actions()
        QTimer.singleShot(0, self.canvas.relayout)
        QTimer.singleShot(0, self.refresh_fields)
        self.refresh_props()

    @staticmethod
    def _titled(title, w):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)
        lbl = QLabel(" " + title)
        theme.role(lbl, "heading")
        v.addWidget(lbl)
        v.addWidget(w, 1)
        return box

    # ------------------------------------------------------------ state
    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, on: bool):
        if on != self._modified:
            self._modified = on
            self.modifiedChanged.emit(on)
        self._update_actions()

    def resolved(self, it: dict) -> dict:
        if it.get("type") == "image" and it.get("image"):
            it = dict(it)
            it["_abs"] = R._resolve(it["image"], str(self.folder))
        return it

    def push_undo(self):
        self._undo.append(json.dumps(self.defn, ensure_ascii=False))
        del self._undo[:-100]
        self._redo.clear()
        self._update_actions()

    def _restore(self, text):
        d = json.loads(text)
        self.defn.clear()
        self.defn.update(d)
        self.canvas.select([], None)
        self.canvas.relayout()
        self.set_modified(True)
        self.refresh_fields(fetch=False)

    def undo(self):
        if self._undo:
            self._redo.append(json.dumps(self.defn, ensure_ascii=False))
            self._restore(self._undo.pop())
        self._update_actions()

    def redo(self):
        if self._redo:
            self._undo.append(json.dumps(self.defn, ensure_ascii=False))
            self._restore(self._redo.pop())
        self._update_actions()

    def _update_actions(self):
        self.a_undo.setEnabled(bool(self._undo))
        self.a_redo.setEnabled(bool(self._redo))

    def save(self) -> bool:
        try:
            R.save_definition(self.defn, self.path)
        except OSError as e:
            QMessageBox.warning(self, "Report", f"Cannot save {self.path.name}:\n{e}")
            return False
        self.set_modified(False)
        self.saved.emit()
        return True

    def maybe_close(self) -> bool:
        if not self._modified:
            return True
        r = QMessageBox.question(self, "Report", f"Save changes to {self.path.name}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return True

    # ------------------------------------------------------------ tools
    def set_tool(self, kind, from_box=False):
        self.canvas.tool = kind
        if not from_box:
            self.toolbox.blockSignals(True)
            for i in range(self.toolbox.count()):
                if self.toolbox.item(i).data(Qt.ItemDataRole.UserRole) == kind:
                    self.toolbox.setCurrentRow(i)
            self.toolbox.blockSignals(False)
        self.status.setText("Click or drag in a band to place the item (Ctrl keeps the tool)." if kind else "")

    def _zoom(self, text):
        try:
            self.canvas.zoom = int(text.rstrip("%")) / 100.0
        except ValueError:
            return
        self.canvas.relayout()

    def _snap(self, on):
        self.canvas.snap = on
        self.canvas.update()

    # ------------------------------------------------------------ properties
    def refresh_props(self):
        c = self.canvas
        if len(c.sel) == 1:
            it = c.sel[0][1]
            self.prop_title.setText(f"  {it.get('name', '')}  ({it.get('type')})")
            self.props.show_for(it, item_specs(it), it.get("name", ""))
            self.help.setText(self._help_for(it.get("type")))
        elif len(c.sel) > 1:
            self.prop_title.setText(f"  {len(c.sel)} items")
            self.props.show_for(None, [], "")
            self.help.setText("Right-click to align; arrows move (Shift+arrows resize).")
        elif c.sel_band is not None:
            kind, level, band = c.sel_band
            self.prop_title.setText("  " + R.band_title(self.defn, kind, level))
            specs = band_specs(kind)
            self.props.show_for(band, specs, kind)
            if kind in ("groupHeader", "groupFooter"):
                g = self.defn["groups"][level]
                n = self.props.rowCount()
                self.props.setRowCount(n + len(GROUP_SPECS))
                for i, spec in enumerate(GROUP_SPECS):
                    lbl = QTableWidgetItem(spec[1])
                    lbl.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.props.setItem(n + i, 0, lbl)
                    self.props.setCellWidget(n + i, 1, self.props._editor(g, spec[0], spec[2],
                                                                          spec[3] if len(spec) > 3 else ()))
            self.help.setText("Drag the band's bottom edge to change its height. Height 0 hides the band.")
        else:
            self.prop_title.setText("  Report: " + str(self.defn.get("name", "")))
            specs = REPORT_SPECS
            self.props.show_for(self.defn, specs, "report")
            pg = self.defn.setdefault("page", {})
            fnt = self.defn.setdefault("font", {})
            n = self.props.rowCount()
            extra = [(pg, s) for s in PAGE_SPECS] + [(fnt, s) for s in FONT_DEF_SPECS]
            self.props.setRowCount(n + len(extra))
            for i, (tgt, spec) in enumerate(extra):
                lbl = QTableWidgetItem(spec[1])
                lbl.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.props.setItem(n + i, 0, lbl)
                self.props.setCellWidget(n + i, 1, self.props._editor(tgt, spec[0], spec[2],
                                                                      spec[3] if len(spec) > 3 else ()))
            ds = self.defn.get("dataSource") or {}
            self.help.setText(f"Data: {self._ds_text(ds)}. Click a band caption for band properties.")

    @staticmethod
    def _help_for(t):
        return {"text": "Text with {expressions}: {Customer}, {Sum('Amount'):N2}, Page {PageNumber} of {TotalPages}.",
                "field": "A field of the data. Format: N2 = 1,234.50  C2 = currency  P0 = percent  "
                         "yyyy-MM-dd = date.",
                "expression": "Python-like: Qty * Price, Sum('Amount'), Count(), Avg('X'), Max('X'), "
                              "RunningSum('Amount'), IIf(Qty > 5, 'Big', ''), Parameters.Name.",
                "barcode": "Code 128 / EAN / Code 39 (python-barcode) or QR (qrcode).",
                "chart": "Groups the rows of the band (group footer: the group; report footer: all) by the "
                         "category field.",
                "image": "A file of the project, or a field holding a path or a BLOB."}.get(t, "")

    def _prop_edited(self, key):
        self.set_modified(True)
        self.canvas.relayout()
        if key in ("type", "size", "orientation", "margins", "rightToLeft") or self.props.target is self.defn:
            QTimer.singleShot(0, self.refresh_props)

    @staticmethod
    def _ds_text(ds):
        t = ds.get("type", "none")
        if t == "sql":
            c = ds.get("connection") or {}
            return f"SQL on {c.get('name') or c.get('path') or c.get('database')} ({c.get('kind')})"
        if t in ("csv", "json", "dataset"):
            return f"{t} {ds.get('file', '')}"
        return "none (SetData from code)"

    # ------------------------------------------------------------ data
    def params(self) -> dict:
        return {p["name"]: p.get("default") for p in self.defn.get("parameters") or [] if p.get("name")}

    def refresh_fields(self, fetch=True):
        if fetch:
            ds = self.defn.get("dataSource") or {}
            if ds.get("type", "none") != "none":
                try:
                    self.columns, _rows = R.fetch(ds, str(self.folder), self.params(), self.password, limit=20)
                    self.status.setText(f"{len(self.columns)} fields from {self._ds_text(ds)}")
                except Exception as e:  # noqa: BLE001
                    self.status.setText(f"Data source: {e}")
        self.fields.fill(self.columns, self.defn.get("parameters") or [])

    def edit_data_source(self):
        dlg = DataSourceDialog(self, self.defn.get("dataSource") or {}, self.folder, self.connections_fn(),
                               self.datasets_fn(), self.params())
        if dlg.exec():
            self.push_undo()
            self.defn["dataSource"] = dlg.result_ds
            if dlg.password.text():
                self.password = dlg.password.text()
            self.set_modified(True)
            self.refresh_fields()
            self.refresh_props()

    def edit_parameters(self):
        dlg = ParametersDialog(self, self.defn.get("parameters") or [])
        if dlg.exec():
            self.push_undo()
            self.defn["parameters"] = dlg.params()
            self.set_modified(True)
            self.refresh_fields(fetch=False)

    def edit_groups(self):
        old = self.defn.get("groups") or []
        dlg = GroupsDialog(self, old, self.columns)
        if dlg.exec():
            self.push_undo()
            self.defn["groups"] = dlg.result_groups()
            for g in self.defn["groups"]:
                g.setdefault("header", {"height": 24, "items": []})
                g.setdefault("footer", {"height": 24, "items": []})
                if not g["header"].get("items") and g.get("field"):
                    g["header"]["items"].append(new_item("text", 0, 3, 300, 18, bool(self.defn.get("rightToLeft"))))
                    g["header"]["items"][-1].update(name=f"txt{g['name']}", bold=True,
                                                    text=f"{g['field']}: {{Fields[{g['field']!r}]}}")
            self.canvas.select([], None)
            self.canvas.relayout()
            self.set_modified(True)

    def insert_column(self, data: dict):
        """Double-click in the field list: a column = header label in the page header + field in the detail."""
        b = self.defn["bands"]
        rtl = bool(self.defn.get("rightToLeft"))
        if data.get("kind") != "field":
            band = b["pageFooter"] if data.get("kind") in ("pagenum", "date") else b["reportHeader"]
            it = new_item(data.get("kind", "text"), 0, 2, rtl=rtl)
            it.update({k: v for k, v in data.items() if k != "kind"})
            self.canvas.add_item(band, it)
            return
        det = b.setdefault("detail", {"height": 20, "items": []})
        x = max([float(i.get("x", 0)) + float(i.get("w", 0)) for i in det.get("items") or []] + [0])
        pw, _ = R.page_size(self.defn)
        ml, _t, mr, _b = R.margins(self.defn)
        if x + 60 > pw - ml - mr:
            x = 0
        self.push_undo()
        hd = new_item("text", x, 2, 100, 18, rtl)
        hd.update(text=data["field"], bold=True)
        self.canvas.add_item(b.setdefault("pageHeader", {"height": 24, "items": []}), hd, push=False)
        fl = new_item("field", x, 0, 100, 18, rtl)
        fl["field"] = data["field"]
        self.canvas.add_item(det, fl, push=False)

    # ------------------------------------------------------------ preview
    def _tab(self, i):
        if i != 1:
            return
        try:
            if self._viewer is None:
                self._viewer = R._qt_viewer_class()(self.preview_host)
                self.preview_host.layout().addWidget(self._viewer)
            rpt = R.Report(copy.deepcopy(self.defn), base_dir=str(self.folder))
            rpt.path = str(self.path)
            rpt.Password = self.password
            if self._viewer.Report is not None:
                for k, v in self._viewer.Parameters.items():
                    if k in rpt.Parameters:
                        rpt.Parameters[k] = v
            self._viewer.SetReport(rpt)
            if rpt.errors:
                self.status.setText("Expression errors: " + "; ".join(rpt.errors[:3]))
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Preview: {e}")


# =============================================================================== add report (wizard)
class AddReportDialog(QDialog):
    """Project > Add Report: a blank report or a ready-made table report from a data source."""

    def __init__(self, parent, folder: Path, connections: list[dict], datasets: list[dict], name: str = "Report1"):
        super().__init__(parent)
        self.setWindowTitle("Add Report")
        self.resize(560, 560)
        self.folder = Path(folder)
        self.connections, self.datasets = connections, datasets
        self.ds: dict = {"type": "none"}
        self.columns: list[str] = []
        self.rows: list[dict] = []
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(name)
        form.addRow("Name:", self.name)
        self.title = QLineEdit("")
        self.title.setPlaceholderText("Report title (default: the name)")
        form.addRow("Title:", self.title)
        self.kind = QComboBox()
        self.kind.addItems(["Report Wizard (table with groups and totals)", "Blank report"])
        form.addRow("Template:", self.kind)
        row = QHBoxLayout()
        self.ds_label = QLabel("(no data source)")
        b = QPushButton("Data Source...")
        b.clicked.connect(self.pick_ds)
        row.addWidget(self.ds_label, 1)
        row.addWidget(b)
        form.addRow("Data:", row)
        lay.addLayout(form)
        lay.addWidget(QLabel("Fields (in column order):"))
        self.fields = QListWidget()
        lay.addWidget(self.fields, 1)
        form2 = QFormLayout()
        self.group = QComboBox()
        form2.addRow("Group by:", self.group)
        self.totals = QCheckBox("Totals for number fields")
        self.totals.setChecked(True)
        self.chart = QCheckBox("Add a bar chart in the report footer")
        self.rtl = QCheckBox("Right to left (Arabic)")
        self.landscape = QCheckBox("Landscape")
        for w in (self.totals, self.chart, self.rtl, self.landscape):
            form2.addRow("", w)
        lay.addLayout(form2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.kind.currentIndexChanged.connect(lambda i: [w.setEnabled(i == 0) for w in
                                                         (self.fields, self.group, self.totals, self.chart)])

    def pick_ds(self):
        dlg = DataSourceDialog(self, self.ds, self.folder, self.connections, self.datasets)
        if not dlg.exec():
            return
        self.ds = dlg.result_ds
        self.ds_label.setText(ReportDesigner._ds_text(self.ds))
        try:
            self.columns, self.rows = R.fetch(self.ds, str(self.folder), {}, dlg.password.text() or None, limit=100)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Data source", str(e))
            self.columns, self.rows = [], []
        self.fields.clear()
        for c in self.columns:
            it = QListWidgetItem(c)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.fields.addItem(it)
        self.group.clear()
        self.group.addItems(["(none)"] + self.columns)

    def _ok(self):
        n = self.name.text().strip()
        if not n.replace("_", "a").isalnum() or (self.folder / f"{n}.rpt.json").exists():
            QMessageBox.warning(self, "Add Report", f"'{n}' is not a valid new report name.")
            return
        self.accept()

    def definition(self) -> dict:
        from . import wizard_report
        name = self.name.text().strip()
        title = self.title.text().strip() or name
        if self.kind.currentIndex() == 1 or not self.columns:
            d = R.new_report(name)
            d["title"] = title
            d["dataSource"] = self.ds
            d["rightToLeft"] = d["mirrorLayout"] = self.rtl.isChecked()
            if self.landscape.isChecked():
                d["page"]["orientation"] = "Landscape"
            return d
        cols = [self.fields.item(i).text() for i in range(self.fields.count())
                if self.fields.item(i).checkState() == Qt.CheckState.Checked]
        grp = self.group.currentText() if self.group.currentIndex() > 0 else ""
        return wizard_report(name, title, self.ds, cols or self.columns, self.rows, grp, self.totals.isChecked(),
                             self.rtl.isChecked(), self.landscape.isChecked(), self.chart.isChecked())


__all__ = ["ReportDesigner", "AddReportDialog", "DataSourceDialog", "DesignCanvas", "new_item", "design_op"]
