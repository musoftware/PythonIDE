"""PNG export / import of pixel blocks (Pillow).  Import quantises every pixel to the nearest colour of the
current colour slots, so a picture drawn in any paint program comes back as valid tile data."""
from __future__ import annotations

from pathlib import Path

from .palettes import RGB, nearest


def block_to_image(block: list[list[int]], colors: list[RGB], aspect: int = 1, scale: int = 1):
    from PIL import Image
    h = len(block)
    w = len(block[0]) if h else 0
    img = Image.new("RGBA", (max(1, w * aspect), max(1, h)), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(block):
        for x, v in enumerate(row):
            if v < 0:
                continue
            c = colors[v % len(colors)]
            for a in range(aspect):
                px[x * aspect + a, y] = (c[0], c[1], c[2], 255)
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    return img


def export_png(path, block, colors: list[RGB], aspect: int = 1, scale: int = 1) -> Path:
    path = Path(path)
    block_to_image(block, colors, aspect, scale).save(path, "PNG")
    return path


def image_to_block(img, colors: list[RGB], width: int, height: int, aspect: int = 1) -> list[list[int]]:
    """Quantise *img* (any mode) to *colors*; the image is scaled to ``width*aspect x height`` first when its
    size differs by an integer factor, otherwise its top-left part is used.  Transparent pixels -> slot 0."""
    from PIL import Image
    img = img.convert("RGBA")
    tw, th = width * aspect, height
    if (img.width, img.height) != (tw, th) and img.width % tw == 0 and img.height % th == 0 \
            and img.width // tw == img.height // th:
        img = img.resize((tw, th), Image.NEAREST)
    px = img.load()
    cache: dict[tuple, int] = {}
    out = []
    for y in range(height):
        row = []
        for x in range(width):
            sx = x * aspect
            if sx >= img.width or y >= img.height:
                row.append(0)
                continue
            c = px[sx, y]
            if c[3] < 128:
                row.append(0)
                continue
            key = c[:3]
            if key not in cache:
                cache[key] = nearest(key, colors)
            row.append(cache[key])
        out.append(row)
    return out


def import_png(path, colors: list[RGB], width: int, height: int, aspect: int = 1) -> list[list[int]]:
    from PIL import Image
    with Image.open(path) as img:
        return image_to_block(img, colors, width, height, aspect)
