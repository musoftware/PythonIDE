"""The document behind every retro game designer (pure Python, no Qt).

A design is one JSON file (``.a26scr`` / ``.nesscr`` / ``.gbmap`` / ``.m13scr``)::

    {"format": "radide-game-design", "version": 1, "system": "nes", "name": "Level1",
     "settings": {...}, "palette": [...], "tiles": [...], "sprites": {...},
     "layers": [{"name": "Nametable", "kind": "tiles", "w": 64, "h": 30, "cw": 8, "ch": 8, "data": "<zlib+b64>"}],
     "objects": [{"name": "Hero", "kind": "sprite", "x": 40, "y": 120, ...}]}

* **layers** are grids of byte cells (``w`` x ``h`` cells of ``cw`` x ``ch`` system pixels). The kind says what a
  cell means: ``tiles`` (tile number), ``playfield`` (Atari 2600 PF bit), ``linecolor`` (a colour per scan line),
  ``attributes`` (NES palette 0-3 per 16x16 metatile), ``bitmap`` (a palette index per pixel) and
  ``collision`` (game-logic flags that the generators export as a table).
* **tiles** are 8x8 (or 16x16 for mode 13h) pixel blocks of palette slots; **sprites** are named pixel images.
* **objects** are placed things (players, missiles, sprites) whose properties the Properties grid edits.

Snapshots (:meth:`Design.snapshot`) are cheap immutable copies used by undo / redo.
"""
from __future__ import annotations

import base64
import copy
import json
import zlib
from dataclasses import dataclass, field
from pathlib import Path

FORMAT = "radide-game-design"
VERSION = 1


def pack(data: bytes) -> str:
    return base64.b64encode(zlib.compress(bytes(data), 9)).decode("ascii")


def unpack(text: str, size: int | None = None) -> bytearray:
    try:
        out = bytearray(zlib.decompress(base64.b64decode(text or "")))
    except (ValueError, zlib.error):
        out = bytearray()
    if size is not None:
        out = (out + bytearray(max(0, size - len(out))))[:size]
    return out


@dataclass
class Layer:
    name: str
    kind: str                    # tiles | playfield | linecolor | attributes | bitmap | collision
    w: int
    h: int
    cw: int = 8                  # cell size in system pixels
    ch: int = 8
    data: bytearray = field(default_factory=bytearray)
    visible: bool = True
    locked: bool = False
    fill: int = 0                # value of a cleared cell

    def __post_init__(self):
        n = self.w * self.h
        if len(self.data) != n:
            self.data = (bytearray(self.data) + bytearray([self.fill]) * n)[:n]

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.data[y * self.w + x]
        return self.fill

    def set(self, x: int, y: int, v: int) -> bool:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        i = y * self.w + x
        v &= 0xFF
        if self.data[i] == v:
            return False
        self.data[i] = v
        return True

    def row(self, y: int) -> bytes:
        return bytes(self.data[y * self.w:(y + 1) * self.w])

    def resize(self, w: int, h: int) -> None:
        old, ow, oh = self.data, self.w, self.h
        self.w, self.h = w, h
        self.data = bytearray([self.fill]) * (w * h)
        for y in range(min(h, oh)):
            n = min(w, ow)
            self.data[y * w:y * w + n] = old[y * ow:y * ow + n]

    def flood(self, x: int, y: int, v: int) -> int:
        """4-way flood fill; returns the number of cells changed."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return 0
        src = self.get(x, y)
        v &= 0xFF
        if src == v:
            return 0
        todo, n = [(x, y)], 0
        while todo:
            cx, cy = todo.pop()
            if 0 <= cx < self.w and 0 <= cy < self.h and self.data[cy * self.w + cx] == src:
                self.data[cy * self.w + cx] = v
                n += 1
                todo.extend(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)))
        return n

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "w": self.w, "h": self.h, "cw": self.cw, "ch": self.ch,
                "visible": self.visible, "locked": self.locked, "fill": self.fill, "data": pack(self.data)}

    @classmethod
    def from_dict(cls, d: dict) -> "Layer":
        w, h = int(d.get("w", 1)), int(d.get("h", 1))
        return cls(str(d.get("name", "Layer")), str(d.get("kind", "tiles")), w, h, int(d.get("cw", 8)),
                   int(d.get("ch", 8)), unpack(d.get("data", ""), w * h), bool(d.get("visible", True)),
                   bool(d.get("locked", False)), int(d.get("fill", 0)))


@dataclass
class Design:
    system: str                                  # a2600 | nes | gb | dos13h
    name: str = "Screen1"
    settings: dict = field(default_factory=dict)
    palette: list = field(default_factory=list)  # system specific (indices or [r, g, b])
    tiles: list = field(default_factory=list)    # list[bytearray]  (tile pixels, palette slots)
    tile_w: int = 8
    tile_h: int = 8
    sprites: dict = field(default_factory=dict)  # name -> {"w", "h", "pixels": bytearray, ...}
    layers: list = field(default_factory=list)   # list[Layer]
    objects: list = field(default_factory=list)  # list[dict]

    # ------------------------------------------------------------ lookup
    def layer(self, name_or_kind: str) -> Layer | None:
        for lay in self.layers:
            if lay.name == name_or_kind:
                return lay
        for lay in self.layers:
            if lay.kind == name_or_kind:
                return lay
        return None

    def objects_of(self, kind: str) -> list[dict]:
        return [o for o in self.objects if o.get("kind") == kind]

    def object(self, name: str) -> dict | None:
        return next((o for o in self.objects if o.get("name") == name), None)

    def unique_name(self, base: str) -> str:
        names = {o.get("name") for o in self.objects} | set(self.sprites)
        i = 1
        while f"{base}{i}" in names:
            i += 1
        return f"{base}{i}"

    def tile(self, index: int) -> bytearray:
        if 0 <= index < len(self.tiles):
            return self.tiles[index]
        return bytearray(self.tile_w * self.tile_h)

    # ------------------------------------------------------------ (de)serialisation
    def to_dict(self) -> dict:
        return {"format": FORMAT, "version": VERSION, "system": self.system, "name": self.name,
                "settings": copy.deepcopy(self.settings), "palette": copy.deepcopy(self.palette),
                "tile_w": self.tile_w, "tile_h": self.tile_h,
                "tiles": [pack(t) for t in self.tiles],
                "sprites": {k: {**{kk: vv for kk, vv in v.items() if kk != "pixels"}, "pixels": pack(v["pixels"])}
                            for k, v in self.sprites.items()},
                "layers": [lay.to_dict() for lay in self.layers],
                "objects": copy.deepcopy(self.objects)}

    @classmethod
    def from_dict(cls, d: dict) -> "Design":
        if d.get("format") != FORMAT:
            raise ValueError("not a RAD IDE game design file")
        tw, th = int(d.get("tile_w", 8)), int(d.get("tile_h", 8))
        sprites = {}
        for k, v in (d.get("sprites") or {}).items():
            w, h = int(v.get("w", 8)), int(v.get("h", 8))
            sprites[k] = {**{kk: vv for kk, vv in v.items() if kk != "pixels"}, "w": w, "h": h,
                          "pixels": unpack(v.get("pixels", ""), w * h)}
        return cls(str(d.get("system", "")), str(d.get("name", "Screen1")), dict(d.get("settings") or {}),
                   list(d.get("palette") or []), [unpack(t, tw * th) for t in d.get("tiles") or []], tw, th,
                   sprites, [Layer.from_dict(x) for x in d.get("layers") or []],
                   [dict(o) for o in d.get("objects") or []])

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "Design":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # ------------------------------------------------------------ undo support
    def snapshot(self) -> dict:
        """An independent copy of the whole state (byte arrays become immutable bytes)."""
        return {"settings": copy.deepcopy(self.settings), "palette": copy.deepcopy(self.palette),
                "tiles": [bytes(t) for t in self.tiles], "tile_w": self.tile_w, "tile_h": self.tile_h,
                "sprites": {k: {**{kk: copy.deepcopy(vv) for kk, vv in v.items() if kk != "pixels"},
                                "pixels": bytes(v["pixels"])} for k, v in self.sprites.items()},
                "layers": [(lay.name, lay.kind, lay.w, lay.h, lay.cw, lay.ch, bytes(lay.data), lay.visible,
                            lay.locked, lay.fill) for lay in self.layers],
                "objects": copy.deepcopy(self.objects), "name": self.name}

    def restore(self, snap: dict) -> None:
        self.settings = copy.deepcopy(snap["settings"])
        self.palette = copy.deepcopy(snap["palette"])
        self.tiles = [bytearray(t) for t in snap["tiles"]]
        self.tile_w, self.tile_h = snap["tile_w"], snap["tile_h"]
        self.sprites = {k: {**copy.deepcopy({kk: vv for kk, vv in v.items() if kk != "pixels"}),
                            "pixels": bytearray(v["pixels"])} for k, v in snap["sprites"].items()}
        self.layers = [Layer(n, k, w, h, cw, ch, bytearray(d), vis, lk, fl)
                       for (n, k, w, h, cw, ch, d, vis, lk, fl) in snap["layers"]]
        self.objects = copy.deepcopy(snap["objects"])
        self.name = snap.get("name", self.name)


def ident(name: str, default: str = "Screen") -> str:
    """*name* as an assembler / C / BASIC identifier."""
    out = "".join(ch if ch.isalnum() and ch.isascii() else "_" for ch in str(name)).strip("_")
    if not out:
        out = default
    if out[0].isdigit():
        out = "_" + out
    return out


def chunks(seq, n: int):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def byte_lines(data, directive: str, per_line: int = 16, fmt: str = "${:02X}", indent: str = "    ") -> list[str]:
    """Data bytes as assembler lines (``.byte $00,$01`` / ``db $00`` ...)."""
    return [f"{indent}{directive} " + ",".join(fmt.format(b & 0xFF) for b in part)
            for part in chunks(data, per_line)]
