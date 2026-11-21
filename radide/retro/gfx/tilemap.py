"""Simple tile maps (NES nametables, Game Boy background maps, generic byte maps) and metatiles.

A map is ``width x height`` cells; each cell holds a tile number and a palette number (0-3, used for the
NES attribute table).  Maps are saved as ``.rtmap`` JSON documents next to the project and exported as
assembler / C data or written into a ROM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

KINDS = {
    "nes": ("NES nametable (32x30 + attributes)", 32, 30),
    "gb": ("Game Boy BG map (32x32)", 32, 32),
    "raw": ("Generic byte map", 16, 16),
}

ASM_SYNTAX = {"ca65": ".byte", "dasm": ".byte", "rgbds": "db", "nasm": "db", "acme": "!byte", "wla": ".db"}


@dataclass
class TileMap:
    width: int = 32
    height: int = 30
    kind: str = "nes"
    cells: list[int] = field(default_factory=list)
    pal: list[int] = field(default_factory=list)
    metatiles: list[list[int]] = field(default_factory=list)     # [top-left, top-right, bottom-left, bottom-right]
    tileset: dict = field(default_factory=dict)                  # {"file", "offset", "format", "slots"}

    def __post_init__(self):
        n = self.width * self.height
        self.cells = (list(self.cells) + [0] * n)[:n]
        self.pal = (list(self.pal) + [0] * n)[:n]

    @classmethod
    def new(cls, kind: str = "nes", width: int | None = None, height: int | None = None) -> "TileMap":
        _n, w, h = KINDS.get(kind, KINDS["raw"])
        return cls(width or w, height or h, kind)

    # ------------------------------------------------------------ cells
    def get(self, x: int, y: int) -> int:
        return self.cells[y * self.width + x]

    def set(self, x: int, y: int, tile: int, pal: int | None = None) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        i = y * self.width + x
        changed = self.cells[i] != (tile & 0xFF) or (pal is not None and self.pal[i] != (pal & 3))
        self.cells[i] = tile & 0xFF
        if pal is not None:
            self.pal[i] = pal & 3
        return changed

    def get_pal(self, x: int, y: int) -> int:
        return self.pal[y * self.width + x]

    def place_metatile(self, index: int, x: int, y: int, pal: int | None = None) -> None:
        tl, tr, bl, br = self.metatiles[index]
        for dx, dy, t in ((0, 0, tl), (1, 0, tr), (0, 1, bl), (1, 1, br)):
            self.set(x + dx, y + dy, t, pal)

    def fill(self, tile: int) -> None:
        self.cells = [tile & 0xFF] * (self.width * self.height)

    # ------------------------------------------------------------ binary forms
    def attribute_table(self) -> bytes:
        """NES attribute table (64 bytes) for a 32x30 map: one byte per 4x4 tiles, 2 bits per 2x2 quadrant
        (bits 0-1 top-left, 2-3 top-right, 4-5 bottom-left, 6-7 bottom-right).  The palette of the top-left
        cell of each quadrant is used."""
        out = bytearray(64)
        for ay in range(8):
            for ax in range(8):
                v = 0
                for q, (qx, qy) in enumerate(((0, 0), (2, 0), (0, 2), (2, 2))):
                    x, y = ax * 4 + qx, ay * 4 + qy
                    if x < self.width and y < self.height:
                        v |= (self.get_pal(x, y) & 3) << (q * 2)
                out[ay * 8 + ax] = v
        return bytes(out)

    def set_attributes(self, attr: bytes) -> None:
        for ay in range(8):
            for ax in range(8):
                v = attr[ay * 8 + ax] if ay * 8 + ax < len(attr) else 0
                for q, (qx, qy) in enumerate(((0, 0), (2, 0), (0, 2), (2, 2))):
                    p = (v >> (q * 2)) & 3
                    for dy in range(2):
                        for dx in range(2):
                            x, y = ax * 4 + qx + dx, ay * 4 + qy + dy
                            if x < self.width and y < self.height:
                                self.pal[y * self.width + x] = p

    def to_bytes(self) -> bytes:
        data = bytes(self.cells)
        if self.kind == "nes" and (self.width, self.height) == (32, 30):
            data += self.attribute_table()
        return data

    @classmethod
    def from_bytes(cls, data: bytes, kind: str = "nes", width: int | None = None,
                   height: int | None = None) -> "TileMap":
        m = cls.new(kind, width, height)
        n = m.width * m.height
        m.cells = list(data[:n]) + [0] * max(0, n - len(data))
        if kind == "nes" and (m.width, m.height) == (32, 30) and len(data) >= n + 64:
            m.set_attributes(data[n:n + 64])
        return m

    # ------------------------------------------------------------ metatiles
    def build_metatiles(self) -> tuple[list[list[int]], list[int]]:
        """Split the map into 2x2 blocks: (unique metatile definitions, metatile map of width/2 x height/2)."""
        defs: list[list[int]] = []
        index: dict[tuple, int] = {}
        mmap = []
        for my in range(self.height // 2):
            for mx in range(self.width // 2):
                x, y = mx * 2, my * 2
                key = (self.get(x, y), self.get(x + 1, y), self.get(x, y + 1), self.get(x + 1, y + 1))
                if key not in index:
                    index[key] = len(defs)
                    defs.append(list(key))
                mmap.append(index[key])
        return defs, mmap

    # ------------------------------------------------------------ export
    def export_asm(self, label: str = "Map", syntax: str = "ca65", per_line: int | None = None,
                   metatiles: bool = False) -> str:
        d = ASM_SYNTAX.get(syntax, ".byte")
        colon = ":"
        per_line = per_line or (self.width if not metatiles else self.width // 2)
        lines = [f"; {label}: {self.width}x{self.height} {KINDS.get(self.kind, ('map',))[0]}"]

        def table(name: str, vals: list[int], n: int):
            lines.append(f"{name}{colon}")
            for i in range(0, len(vals), n):
                lines.append(f"    {d} " + ",".join(f"${v:02X}" if syntax != "nasm" else f"0x{v:02X}"
                                                   for v in vals[i:i + n]))
        if metatiles:
            defs, mmap = self.build_metatiles()
            lines.append(f"; {len(defs)} metatiles (top-left, top-right, bottom-left, bottom-right)")
            table(f"{label}_Metatiles", [t for m in defs for t in m], 4)
            table(f"{label}_MetaMap", mmap, per_line)
        else:
            table(label, list(self.cells), per_line)
            if self.kind == "nes" and (self.width, self.height) == (32, 30):
                table(f"{label}_Attr", list(self.attribute_table()), 8)
        return "\n".join(lines) + "\n"

    def export_c(self, label: str = "map", metatiles: bool = False) -> str:
        def arr(name, vals, n):
            body = ",\n".join("    " + ", ".join(f"0x{v:02X}" for v in vals[i:i + n]) for i in range(0, len(vals), n))
            return f"const unsigned char {name}[{len(vals)}] = {{\n{body}\n}};\n"
        out = f"/* {label}: {self.width}x{self.height} tile map */\n"
        if metatiles:
            defs, mmap = self.build_metatiles()
            out += arr(f"{label}_metatiles", [t for m in defs for t in m], 4)
            out += arr(f"{label}_metamap", mmap, max(1, self.width // 2))
        else:
            out += arr(label, list(self.cells), self.width)
            if self.kind == "nes" and (self.width, self.height) == (32, 30):
                out += arr(f"{label}_attr", list(self.attribute_table()), 8)
        return out

    # ------------------------------------------------------------ document
    def to_json(self) -> dict:
        return {"format": "radide-tilemap", "version": 1, "kind": self.kind, "width": self.width,
                "height": self.height, "cells": self.cells, "pal": self.pal, "metatiles": self.metatiles,
                "tileset": self.tileset}

    @classmethod
    def from_json(cls, d: dict) -> "TileMap":
        return cls(int(d.get("width", 32)), int(d.get("height", 30)), d.get("kind", "nes"),
                   list(d.get("cells", [])), list(d.get("pal", [])), [list(m) for m in d.get("metatiles", [])],
                   dict(d.get("tileset", {})))

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_json(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "TileMap":
        return cls.from_json(json.loads(Path(path).read_text(encoding="utf-8")))
