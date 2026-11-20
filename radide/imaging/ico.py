"""Read and write Windows icons (.ico) and cursors (.cur) with several sizes.

Writing is done here (Pillow cannot write .cur and writes every .ico frame as PNG): frames smaller than
256 px are stored as classic 32-bit BMP (BGRA + AND mask - understood by every Windows version, Tk's
``iconbitmap`` and old tools), 256 px frames as PNG (the Vista+ convention). Reading uses Pillow's ICO
decoder for each frame so 1/4/8/24/32-bit and PNG frames all load.
"""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

PNG_SIG = b"\x89PNG\r\n\x1a\n"


@dataclass
class IconFrame:
    image: Image.Image              # RGBA
    hotspot: tuple[int, int] = (0, 0)   # cursors only

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size


# ---------------------------------------------------------------------- writing
def _dib(img: Image.Image) -> bytes:
    """A 32-bit BMP frame: BITMAPINFOHEADER (height doubled), bottom-up BGRA pixels, 1-bit AND mask."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.tobytes("raw", "BGRA")
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)]
    xor = b"".join(reversed(rows))
    mask_stride = ((w + 31) // 32) * 4
    alpha = img.getchannel("A").tobytes()
    mask = bytearray()
    for y in range(h - 1, -1, -1):
        row = bytearray(mask_stride)
        base = y * w
        for x in range(w):
            if alpha[base + x] == 0:
                row[x >> 3] |= 0x80 >> (x & 7)
        mask += row
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, len(xor) + len(mask), 0, 0, 0, 0)
    return header + xor + bytes(mask)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def encode(frames: list[IconFrame], cursor: bool = False) -> bytes:
    """The bytes of an .ico (or .cur when *cursor*) holding *frames* (largest first is not required)."""
    if not frames:
        raise ValueError("an icon needs at least one image")
    frames = sorted(frames, key=lambda f: f.size[0] * f.size[1])
    for f in frames:
        w, h = f.size
        if w > 256 or h > 256 or w < 1 or h < 1:
            raise ValueError(f"icon images must be 1..256 pixels (got {w}x{h})")
    blobs = [(_png(f.image) if max(f.size) >= 256 else _dib(f.image)) for f in frames]
    out = bytearray(struct.pack("<HHH", 0, 2 if cursor else 1, len(frames)))
    offset = 6 + 16 * len(frames)
    for f, blob in zip(frames, blobs):
        w, h = f.size
        a, b = (f.hotspot if cursor else (1, 32))
        out += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, a, b, len(blob), offset)
        offset += len(blob)
    for blob in blobs:
        out += blob
    return bytes(out)


def save(path: str | Path, frames: list[IconFrame], cursor: bool | None = None) -> Path:
    path = Path(path)
    if cursor is None:
        cursor = path.suffix.lower() == ".cur"
    path.write_bytes(encode(frames, cursor))
    return path


# ---------------------------------------------------------------------- reading
def decode(data: bytes) -> tuple[list[IconFrame], bool]:
    """(frames, is_cursor) of an .ico / .cur file's bytes."""
    if len(data) < 6:
        raise ValueError("not an icon file")
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or kind not in (1, 2) or count == 0:
        raise ValueError("not an icon file")
    frames: list[IconFrame] = []
    for i in range(count):
        w, h, colors, _r, a, b, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        blob = data[offset:offset + size]
        if blob.startswith(PNG_SIG):
            img = Image.open(io.BytesIO(blob))
            img.load()
        else:
            bpp = struct.unpack_from("<H", blob, 14)[0] if len(blob) >= 16 else 32
            single = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", w, h, colors, 0, 1, bpp,
                                                                 len(blob), 22) + blob
            img = Image.open(io.BytesIO(single))
            img.load()
        frames.append(IconFrame(img.convert("RGBA"), (a, b) if kind == 2 else (0, 0)))
    return frames, kind == 2


def load(path: str | Path) -> tuple[list[IconFrame], bool]:
    return decode(Path(path).read_bytes())


def sizes(path: str | Path) -> list[tuple[int, int]]:
    return [f.size for f in load(path)[0]]


# ---------------------------------------------------------------------- helpers
def resample(img: Image.Image, size: int) -> Image.Image:
    """*img* fitted into a size x size square (aspect kept, transparent padding). Small sizes use a
    two-step downscale so thin lines survive."""
    img = img.convert("RGBA")
    w, h = img.size
    if (w, h) == (size, size):
        return img.copy()
    scale = size / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    if scale >= 1 and w <= 64:
        small = img.resize((nw, nh), Image.Resampling.NEAREST)      # pixel art stays crisp when enlarged
    else:
        small = img.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(small, ((size - nw) // 2, (size - nh) // 2))
    return out


def make_icon(src: Image.Image, sizes_: tuple[int, ...] = (16, 24, 32, 48, 64, 256)) -> list[IconFrame]:
    return [IconFrame(resample(src, s)) for s in sizes_]


def qimage_to_pil(qimg) -> Image.Image:
    from PyQt6.QtGui import QImage
    q = qimg.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = q.width(), q.height()
    ptr = q.constBits()
    ptr.setsize(q.sizeInBytes())
    data = bytes(ptr)
    return Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", q.bytesPerLine(), 1).copy()


def pil_to_qimage(img: Image.Image):
    from PyQt6.QtGui import QImage
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    q = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    return q.convertToFormat(QImage.Format.Format_ARGB32)        # copy: *data* goes away


__all__ = ["IconFrame", "encode", "save", "decode", "load", "sizes", "resample", "make_icon",
           "qimage_to_pil", "pil_to_qimage"]
