"""Painting helpers: fonts and TextStyle, rounded-rect paths, gradients, shadows, images, BoxDecoration,
borders, shapes and the network / asset image cache."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QImage, QLinearGradient, QPainter, QPainterPath,
                         QPen, QRadialGradient)

from .. import iconfont
from .. import model as M
from .core import Ctx, num, radii, align, enum_val, color


# ================================================================================ fonts
_fonts_loaded = False


def default_font() -> str:
    """Roboto from the Flutter SDK (Flutter's default font on Android / the web), else Segoe UI."""
    global _fonts_loaded
    from PyQt6.QtGui import QFontDatabase
    if not _fonts_loaded:
        _fonts_loaded = True
        sdk = iconfont._sdk()
        if sdk is not None:
            folder = sdk / "bin" / "cache" / "artifacts" / "material_fonts"
            for p in sorted(folder.glob("roboto-*.ttf")):
                QFontDatabase.addApplicationFont(str(p))
    fams = set(QFontDatabase.families())
    return "Roboto" if "Roboto" in fams else "Segoe UI"


_WEIGHTS = {"w100": 100, "w200": 200, "w300": 300, "w400": 400, "w500": 500, "w600": 600, "w700": 700,
            "w800": 800, "w900": 900, "normal": 400, "bold": 700}


def make_font(style: dict, ctx: Ctx) -> QFont:
    fam = style.get("googleFont") or style.get("fontFamily") or ctx.font_family
    f = QFont(str(fam))
    if fam != ctx.font_family:
        f.setFamilies([str(fam), ctx.font_family])
    size = num(style.get("fontSize"), 14.0) * ctx.text_scale
    f.setPixelSize(max(1, int(round(size))))
    w = _WEIGHTS.get(enum_val(style.get("fontWeight"), "normal"), 400)
    f.setWeight(QFont.Weight(w))
    if enum_val(style.get("fontStyle")) == "italic":
        f.setItalic(True)
    ls = num(style.get("letterSpacing"))
    if ls:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, ls)
    deco = enum_val(style.get("decoration"))
    if deco == "underline":
        f.setUnderline(True)
    elif deco == "lineThrough":
        f.setStrikeOut(True)
    elif deco == "overline":
        f.setOverline(True)
    return f


def merge_style(base: dict, extra) -> dict:
    out = dict(base)
    if isinstance(extra, dict) and not M.is_code(extra):
        for k, v in extra.items():
            if v is not None and not M.is_code(v):
                out[k] = v
    return out


# ============================================================================= painting
def rrect_path(r: QRectF, rad: tuple | None, circle: bool = False) -> QPainterPath:
    path = QPainterPath()
    if circle:
        path.addEllipse(r)
        return path
    if not rad or not any(rad):
        path.addRect(r)
        return path
    tl, tr, br, bl = (min(x, r.width() / 2, r.height() / 2) for x in rad)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    path.moveTo(x + tl, y)
    path.lineTo(x + w - tr, y)
    path.arcTo(x + w - 2 * tr, y, 2 * tr, 2 * tr, 90, -90) if tr else path.lineTo(x + w, y)
    path.lineTo(x + w, y + h - br)
    path.arcTo(x + w - 2 * br, y + h - 2 * br, 2 * br, 2 * br, 0, -90) if br else path.lineTo(x + w, y + h)
    path.lineTo(x + bl, y + h)
    path.arcTo(x, y + h - 2 * bl, 2 * bl, 2 * bl, 270, -90) if bl else path.lineTo(x, y + h)
    path.lineTo(x, y + tl)
    path.arcTo(x, y, 2 * tl, 2 * tl, 180, -90) if tl else path.lineTo(x, y)
    path.closeSubpath()
    return path


def gradient_brush(g: dict, r: QRectF, ctx: Ctx) -> QBrush | None:
    if not isinstance(g, dict) or M.is_code(g):
        return None
    cols = [color(c, ctx) for c in g.get("colors") or []]
    cols = [c for c in cols if c is not None]
    if not cols:
        return None
    stops = g.get("stops") or []
    if len(stops) != len(cols) or not all(isinstance(s, (int, float)) for s in stops):
        stops = [i / max(1, len(cols) - 1) for i in range(len(cols))]
    t = g.get("type", "linear")
    cx, cy = r.center().x(), r.center().y()

    def pt(a):
        ax, ay = align(a, (0.0, 0.0))
        return QPointF(cx + ax * r.width() / 2, cy + ay * r.height() / 2)
    if t == "radial":
        grad = QRadialGradient(pt(g.get("center", "Alignment.center")),
                               num(g.get("radius"), 0.5) * min(r.width(), r.height()))
    elif t == "sweep":
        grad = QConicalGradient(pt(g.get("center", "Alignment.center")), 0)
    else:
        grad = QLinearGradient(pt(g.get("begin", "Alignment.centerLeft")), pt(g.get("end", "Alignment.centerRight")))
    for s, c in zip(stops, cols):
        grad.setColorAt(max(0.0, min(1.0, float(s))), c)
    return QBrush(grad)


def paint_shadows(p: QPainter, path: QPainterPath, shadows, ctx: Ctx) -> None:
    if not isinstance(shadows, list):
        return
    for s in shadows:
        if not isinstance(s, dict) or M.is_code(s):
            continue
        col = color(s.get("color"), ctx, QColor(0, 0, 0, 60))
        blur = max(0.0, num(s.get("blur"), 0.0))
        spread = num(s.get("spread"), 0.0)
        off = s.get("offset") if isinstance(s.get("offset"), list) else [0, 0]
        dx, dy = num(off[0], 0.0) if off else 0.0, num(off[1], 0.0) if len(off) > 1 else 0.0
        drop_shadow(p, path, col, blur, spread, dx, dy)


def drop_shadow(p: QPainter, path: QPainterPath, col: QColor, blur: float, spread: float, dx: float,
                dy: float) -> None:
    """A blurred shadow: the shape drawn small and scaled up smoothly (QPainter has no blur filter)."""
    base = path
    if spread > 0:
        st = QPainterPathStrokerCompat(spread * 2)
        base = path.united(st.createStroke(path))
    p.save()
    p.translate(dx, dy)
    p.setPen(Qt.PenStyle.NoPen)
    if blur < 1.5:
        p.setBrush(col)
        p.drawPath(base)
        p.restore()
        return
    br = base.boundingRect().adjusted(-blur * 1.5, -blur * 1.5, blur * 1.5, blur * 1.5)
    k = max(1.0, blur / 2.5)                     # downscale factor
    sw, sh = max(2, int(br.width() / k) + 2), max(2, int(br.height() / k) + 2)
    if sw * sh > 4_000_000:
        p.setBrush(col)
        p.drawPath(base)
        p.restore()
        return
    img = QImage(sw, sh, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    q = QPainter(img)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.scale(1 / k, 1 / k)
    q.translate(-br.x(), -br.y())
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(col)
    q.drawPath(base)
    q.end()
    # one more smooth down/up pass softens the edge like a gaussian
    img = img.scaled(max(1, sw // 2), max(1, sh // 2), Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(br, img)
    p.restore()


def QPainterPathStrokerCompat(width: float):
    from PyQt6.QtGui import QPainterPathStroker
    s = QPainterPathStroker()
    s.setWidth(max(0.01, width))
    s.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    s.setCapStyle(Qt.PenCapStyle.RoundCap)
    return s


def paint_image(p: QPainter, r: QRectF, img: QImage | None, fit: str, al=(0.0, 0.0), clip_path=None,
                tint: QColor | None = None, opacity: float = 1.0) -> None:
    p.save()
    if clip_path is not None:
        p.setClipPath(clip_path, Qt.ClipOperation.IntersectClip)
    else:
        p.setClipRect(r, Qt.ClipOperation.IntersectClip)
    if opacity < 1:
        p.setOpacity(p.opacity() * opacity)
    if img is None or img.isNull():
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#FFB8C4D6"))
        g.setColorAt(1, QColor("#FF8A9BB5"))
        p.fillRect(r, QBrush(g))
        s = min(r.width(), r.height(), 48.0) * 0.6
        if s > 6:
            iconfont.draw(p, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s), "image",
                          QColor(255, 255, 255, 200))
        p.restore()
        return
    iw, ih = img.width(), img.height()
    fit = fit or "contain"
    if fit == "fill":
        dw, dh = r.width(), r.height()
    elif fit == "cover":
        k = max(r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    elif fit == "fitWidth":
        k = r.width() / iw
        dw, dh = r.width(), ih * k
    elif fit == "fitHeight":
        k = r.height() / ih
        dw, dh = iw * k, r.height()
    elif fit in ("none",):
        dw, dh = iw, ih
    elif fit == "scaleDown":
        k = min(1.0, r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    else:
        k = min(r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    x = r.x() + (r.width() - dw) * (al[0] + 1) / 2
    y = r.y() + (r.height() - dh) * (al[1] + 1) / 2
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(x, y, dw, dh), img)
    if tint is not None:
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(x, y, dw, dh), tint)
    p.restore()


def paint_decoration(p: QPainter, r: QRectF, dec: dict, ctx: Ctx) -> None:
    if not isinstance(dec, dict) or M.is_code(dec):
        return
    circle = enum_val(dec.get("shape")) == "circle"
    if circle:
        d = min(r.width(), r.height())
        r = QRectF(r.center().x() - d / 2, r.center().y() - d / 2, d, d)
    path = rrect_path(r, radii(dec.get("borderRadius")), circle)
    paint_shadows(p, path, dec.get("boxShadow"), ctx)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    c = color(dec.get("color"), ctx)
    if c is not None:
        p.setBrush(c)
        p.drawPath(path)
    gb = gradient_brush(dec.get("gradient"), r, ctx)
    if gb is not None:
        p.setBrush(gb)
        p.drawPath(path)
    img = dec.get("image")
    if isinstance(img, dict) and not M.is_code(img):
        q = ctx.images.get(img.get("source", "asset"), img.get("src", ""), ctx.folder) if ctx.images else None
        paint_image(p, r, q, enum_val(img.get("fit"), "cover") if img.get("fit") else "none",
                    align(img.get("alignment"), (0.0, 0.0)), path, opacity=num(img.get("opacity"), 1.0))
    p.restore()
    paint_border(p, r, dec.get("border"), radii(dec.get("borderRadius")), circle, ctx)


def paint_border(p: QPainter, r: QRectF, b, rad, circle: bool, ctx: Ctx) -> None:
    if not isinstance(b, dict) or M.is_code(b):
        return
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    sides = [k for k in ("top", "right", "bottom", "left") if isinstance(b.get(k), dict)]
    if not sides:
        w = num(b.get("width"), 1.0)
        if w > 0:
            p.setPen(QPen(color(b.get("color"), ctx, QColor("#FF000000")), w))
            p.drawPath(rrect_path(r.adjusted(w / 2, w / 2, -w / 2, -w / 2),
                                  tuple(max(0.0, x - w / 2) for x in rad) if rad else None, circle))
        p.restore()
        return
    for k in sides:
        s = b[k]
        w = num(s.get("width"), 1.0)
        if w <= 0:
            continue
        p.setPen(QPen(color(s.get("color"), ctx, QColor("#FF000000")), w, cap=Qt.PenCapStyle.FlatCap))
        h = w / 2
        if k == "top":
            p.drawLine(QPointF(r.left(), r.top() + h), QPointF(r.right(), r.top() + h))
        elif k == "bottom":
            p.drawLine(QPointF(r.left(), r.bottom() - h), QPointF(r.right(), r.bottom() - h))
        elif k == "left":
            p.drawLine(QPointF(r.left() + h, r.top()), QPointF(r.left() + h, r.bottom()))
        else:
            p.drawLine(QPointF(r.right() - h, r.top()), QPointF(r.right() - h, r.bottom()))
    p.restore()


def shape_path(shape, r: QRectF, default_radius: float | tuple = 0.0) -> QPainterPath:
    """ShapeBorder JSON -> path."""
    if isinstance(shape, dict) and not M.is_code(shape):
        t = shape.get("type", "rounded")
        if t == "circle":
            d = min(r.width(), r.height())
            return rrect_path(QRectF(r.center().x() - d / 2, r.center().y() - d / 2, d, d), None, True)
        if t == "stadium":
            return rrect_path(r, (min(r.width(), r.height()) / 2,) * 4)
        return rrect_path(r, radii(shape.get("radius")) or (0.0,) * 4)
    rad = default_radius if isinstance(default_radius, tuple) else (float(default_radius),) * 4
    return rrect_path(r, rad)


def shape_side(shape, ctx: Ctx):
    if isinstance(shape, dict) and isinstance(shape.get("side"), dict):
        s = shape["side"]
        return color(s.get("color"), ctx, QColor("#FF000000")), num(s.get("width"), 1.0)
    return None


# =============================================================================== images
class ImageCache(QObject):
    """Asset images from the project folder and network images (downloaded once, asynchronously)."""
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: dict[str, QImage | None] = {}
        self._nam = None
        self._pending: set[str] = set()
        self.offline = False

    def get(self, source: str, src: str, folder: Path | None) -> QImage | None:
        if not src or not isinstance(src, str):
            return None
        if source == "network" or src.startswith(("http://", "https://")):
            if src in self._cache:
                return self._cache[src]
            self._fetch(src)
            return None
        p = Path(src)
        if not p.is_absolute() and folder is not None:
            p = Path(folder) / src
        if not p.is_file() and folder is not None and (Path(folder) / p.name).is_file():
            p = Path(folder) / p.name           # template artwork kept flat next to the template
        key = str(p)
        if key not in self._cache:
            img = QImage(key) if p.is_file() else QImage()
            self._cache[key] = None if img.isNull() else img
        return self._cache[key]

    def _fetch(self, url: str) -> None:
        if self.offline or url in self._pending:
            return
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
        except ImportError:
            self._cache[url] = None
            return
        if self._nam is None:
            self._nam = QNetworkAccessManager(self)
        self._pending.add(url)
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setTransferTimeout(15000)
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, u=url: self._done(r, u))

    def _done(self, reply, url: str) -> None:
        self._pending.discard(url)
        img = QImage()
        try:
            data = reply.readAll()
            img.loadFromData(bytes(data))
        finally:
            reply.deleteLater()
        self._cache[url] = None if img.isNull() else img
        if not img.isNull():
            self.changed.emit()

    def pending(self) -> int:
        return len(self._pending)
