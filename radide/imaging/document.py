"""The image being edited: one or more *frames* (an icon has one frame per size: 16, 32, 48 ...),
each made of *layers* (QImage ARGB32). Undo / redo keep snapshots of the frames (icons are small).

File formats: .ico / .cur keep every frame (layers are flattened when saving); .png / .bmp / .gif /
.jpg save the current frame. Frames and layers of the editing session are not stored in the file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter

from . import ico

ICON_EXTS = (".ico", ".cur")
RASTER_EXTS = (".png", ".bmp", ".gif", ".jpg", ".jpeg")


def blank(w: int, h: int) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    return img


@dataclass
class Layer:
    name: str
    image: QImage
    visible: bool = True
    opacity: float = 1.0

    def copy(self) -> "Layer":
        return Layer(self.name, self.image.copy(), self.visible, self.opacity)


@dataclass
class Frame:
    layers: list[Layer] = field(default_factory=list)
    hotspot: tuple[int, int] = (0, 0)

    @property
    def width(self) -> int:
        return self.layers[0].image.width()

    @property
    def height(self) -> int:
        return self.layers[0].image.height()

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}, 32 bit"

    def copy(self) -> "Frame":
        return Frame([la.copy() for la in self.layers], self.hotspot)

    def composite(self) -> QImage:
        if len(self.layers) == 1 and self.layers[0].visible and self.layers[0].opacity >= 1:
            return self.layers[0].image.copy()
        out = blank(self.width, self.height)
        p = QPainter(out)
        for la in self.layers:
            if la.visible:
                p.setOpacity(la.opacity)
                p.drawImage(0, 0, la.image)
        p.end()
        return out


class ImageDocument(QObject):
    changed = pyqtSignal()              # pixels changed
    structureChanged = pyqtSignal()     # frames / layers added, removed, reordered
    modifiedChanged = pyqtSignal(bool)

    MAX_UNDO = 100

    def __init__(self, path: Path | None = None, parent=None):
        super().__init__(parent)
        self.path: Path | None = Path(path) if path else None
        self.frames: list[Frame] = []
        self.current = 0                # frame index
        self.layer = 0                  # active layer index in the current frame
        self.cursor = False
        self._undo: list[tuple] = []
        self._redo: list[tuple] = []
        self._modified = False
        if self.path is not None and self.path.exists():
            self.load(self.path)

    # ---------------------------------------------------------------- creation
    @classmethod
    def new_icon(cls, sizes=(16, 32, 48), cursor: bool = False) -> "ImageDocument":
        d = cls()
        d.cursor = cursor
        d._icon = True
        d.frames = [Frame([Layer("Layer 1", blank(s, s))]) for s in sorted(set(sizes), reverse=True)]
        d.current = 0
        return d

    @classmethod
    def new_image(cls, w: int, h: int, background: QColor | None = None) -> "ImageDocument":
        d = cls()
        img = blank(w, h)
        if background is not None:
            img.fill(background)
        d.frames = [Frame([Layer("Background" if background is not None else "Layer 1", img)])]
        return d

    @property
    def is_icon(self) -> bool:
        if self.path is not None:
            return self.path.suffix.lower() in ICON_EXTS
        return self.cursor or len(self.frames) > 1 or getattr(self, "_icon", False)

    # ---------------------------------------------------------------- access
    @property
    def frame(self) -> Frame:
        return self.frames[self.current]

    @property
    def active_layer(self) -> Layer:
        f = self.frame
        self.layer = max(0, min(self.layer, len(f.layers) - 1))
        return f.layers[self.layer]

    @property
    def image(self) -> QImage:
        return self.active_layer.image

    def composite(self) -> QImage:
        return self.frame.composite()

    def pixel(self, x: int, y: int, merged: bool = False) -> QColor:
        img = self.composite() if merged else self.image
        if 0 <= x < img.width() and 0 <= y < img.height():
            return img.pixelColor(x, y)
        return QColor(0, 0, 0, 0)

    def set_pixel(self, x: int, y: int, color: QColor) -> None:
        """Without an undo step: call checkpoint() once before a stroke."""
        img = self.image
        if 0 <= x < img.width() and 0 <= y < img.height():
            img.setPixelColor(QPoint(x, y), color)
            self._touch()

    # ---------------------------------------------------------------- undo
    def _state(self):
        return ([f.copy() for f in self.frames], self.current, self.layer)

    def checkpoint(self) -> None:
        self._undo.append(self._state())
        del self._undo[:-self.MAX_UNDO]
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._state())
            self._restore(self._undo.pop())

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._state())
            self._restore(self._redo.pop())

    def _restore(self, st) -> None:
        self.frames, self.current, self.layer = st
        self.current = min(self.current, len(self.frames) - 1)
        self.structureChanged.emit()
        self._touch()

    def _touch(self) -> None:
        self.changed.emit()
        self.set_modified(True)

    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, m: bool) -> None:
        if m != self._modified:
            self._modified = m
            self.modifiedChanged.emit(m)

    def notify(self) -> None:
        """After direct painting into self.image (QPainter): repaint + modified."""
        self._touch()

    # ---------------------------------------------------------------- frames
    def select_frame(self, i: int) -> None:
        if 0 <= i < len(self.frames) and i != self.current:
            self.current = i
            self.layer = min(self.layer, len(self.frame.layers) - 1)
            self.structureChanged.emit()
            self.changed.emit()

    def add_frame(self, w: int, h: int, from_current: bool = True) -> int:
        """A new image type (size). With *from_current* it starts as the current frame resampled."""
        self.checkpoint()
        if from_current and self.frames:
            src = ico.qimage_to_pil(self.composite())
            if w == h:
                img = ico.pil_to_qimage(ico.resample(src, w))
            else:
                from PIL import Image
                img = ico.pil_to_qimage(src.resize((w, h), Image.Resampling.LANCZOS))
        else:
            img = blank(w, h)
        self.frames.append(Frame([Layer("Layer 1", img)]))
        self.frames.sort(key=lambda f: -f.width * f.height)
        self.current = next(i for i, f in enumerate(self.frames) if f.layers[0].image is img)
        self.layer = 0
        self.structureChanged.emit()
        self._touch()
        return self.current

    def remove_frame(self, i: int) -> None:
        if len(self.frames) <= 1 or not 0 <= i < len(self.frames):
            return
        self.checkpoint()
        del self.frames[i]
        self.current = min(self.current, len(self.frames) - 1)
        self.layer = 0
        self.structureChanged.emit()
        self._touch()

    def generate_sizes(self, sizes=(16, 24, 32, 48, 64, 256), source: int | None = None) -> None:
        """Every icon size made from one frame (default: the largest), replacing frames of those sizes;
        the source frame itself is kept as drawn."""
        self.checkpoint()
        src_i = self.current if source is None else source
        src_frame = self.frames[src_i]
        src = ico.qimage_to_pil(src_frame.composite())
        keep = [f for f in self.frames if (f.width, f.height) not in {(s, s) for s in sizes} or f is src_frame]
        have = {(f.width, f.height) for f in keep}
        for s in sizes:
            if (s, s) not in have:
                keep.append(Frame([Layer("Layer 1", ico.pil_to_qimage(ico.resample(src, s)))]))
        keep.sort(key=lambda f: -f.width * f.height)
        self.frames = keep
        self.current = self.frames.index(src_frame)
        self.layer = 0
        self.structureChanged.emit()
        self._touch()

    def import_image(self, path: Path, all_sizes: bool = False) -> None:
        """Put a picture file into the current frame (scaled to fit), or make every frame from it."""
        from PIL import Image
        src = Image.open(path)
        src.load()
        src = src.convert("RGBA")
        self.checkpoint()
        targets = self.frames if all_sizes else [self.frame]
        for f in targets:
            if f.width == f.height:
                img = ico.pil_to_qimage(ico.resample(src, f.width))
            else:
                img = ico.pil_to_qimage(src.resize((f.width, f.height), Image.Resampling.LANCZOS))
            f.layers = [Layer("Layer 1", img)]
        self.layer = 0
        self.structureChanged.emit()
        self._touch()

    def resize_canvas(self, w: int, h: int, scale: bool) -> None:
        """Image > Resize: scale the pixels or change the canvas size (anchored top-left)."""
        from PyQt6.QtCore import Qt
        self.checkpoint()
        for la in self.frame.layers:
            if scale:
                la.image = la.image.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.FastTransformation)
            else:
                img = blank(w, h)
                p = QPainter(img)
                p.drawImage(0, 0, la.image)
                p.end()
                la.image = img
        self.structureChanged.emit()
        self._touch()

    # ---------------------------------------------------------------- layers
    def add_layer(self) -> None:
        self.checkpoint()
        f = self.frame
        f.layers.insert(self.layer + 1, Layer(f"Layer {len(f.layers) + 1}", blank(f.width, f.height)))
        self.layer += 1
        self.structureChanged.emit()
        self._touch()

    def remove_layer(self) -> None:
        f = self.frame
        if len(f.layers) <= 1:
            return
        self.checkpoint()
        del f.layers[self.layer]
        self.layer = max(0, self.layer - 1)
        self.structureChanged.emit()
        self._touch()

    def move_layer(self, delta: int) -> None:
        f = self.frame
        j = self.layer + delta
        if not 0 <= j < len(f.layers):
            return
        self.checkpoint()
        f.layers[self.layer], f.layers[j] = f.layers[j], f.layers[self.layer]
        self.layer = j
        self.structureChanged.emit()
        self._touch()

    def merge_down(self) -> None:
        f = self.frame
        if self.layer == 0:
            return
        self.checkpoint()
        top, below = f.layers[self.layer], f.layers[self.layer - 1]
        p = QPainter(below.image)
        p.setOpacity(top.opacity if top.visible else 0)
        p.drawImage(0, 0, top.image)
        p.end()
        del f.layers[self.layer]
        self.layer -= 1
        self.structureChanged.emit()
        self._touch()

    def set_layer_visible(self, i: int, on: bool) -> None:
        f = self.frame
        if 0 <= i < len(f.layers) and f.layers[i].visible != on:
            self.checkpoint()
            f.layers[i].visible = on
            self._touch()

    # ---------------------------------------------------------------- files
    def load(self, path: Path) -> None:
        path = Path(path)
        ext = path.suffix.lower()
        if ext in ICON_EXTS:
            frames, cursor = ico.load(path)
            self.cursor = cursor
            self.frames = [Frame([Layer("Layer 1", ico.pil_to_qimage(f.image))], f.hotspot) for f in frames]
            self.frames.sort(key=lambda f: -f.width * f.height)
        else:
            from PIL import Image
            img = Image.open(path)
            img.load()
            self.frames = [Frame([Layer("Layer 1", ico.pil_to_qimage(img.convert("RGBA")))])]
        self.path = path
        self.current = 0
        self.layer = 0
        self._undo.clear()
        self._redo.clear()
        self.structureChanged.emit()
        self.changed.emit()
        self.set_modified(False)

    def save(self, path: Path | None = None) -> Path:
        path = Path(path or self.path)
        if path is None:
            raise ValueError("no file name")
        ext = path.suffix.lower()
        if ext in ICON_EXTS:
            frames = []
            for f in self.frames:
                if f.width > 256 or f.height > 256:
                    continue
                frames.append(ico.IconFrame(ico.qimage_to_pil(f.composite()), f.hotspot))
            if not frames:
                raise ValueError("an icon needs an image of 256x256 or smaller")
            ico.save(path, frames, cursor=ext == ".cur")
        else:
            img = ico.qimage_to_pil(self.composite())
            opaque = img.getchannel("A").getextrema()[0] == 255
            if ext in (".jpg", ".jpeg") or (ext == ".bmp" and opaque):
                from PIL import Image
                bg = Image.new("RGB", img.size, (255, 255, 255))   # JPEG has no alpha: white behind
                bg.paste(img, mask=img.getchannel("A"))
                img = bg
            img.save(path)
        self.path = path
        self.set_modified(False)
        return path

    def export_pngs(self, folder: Path, stem: str) -> list[Path]:
        """Every frame as <stem>_<w>x<h>.png."""
        out = []
        for f in self.frames:
            p = Path(folder) / f"{stem}_{f.width}x{f.height}.png"
            ico.qimage_to_pil(f.composite()).save(p)
            out.append(p)
        return out
