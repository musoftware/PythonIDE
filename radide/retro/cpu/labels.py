"""Read label / symbol files of assemblers and emulators and merge them into a disassembly's ``hints.json``
(no Qt in here).

==============  ==========================================================================================
``.dbg``        ca65 / ld65 debug file (``ld65 --dbgfile``): ``sym ... name="X",val=0xC000,...,type=lab``;
                symbols of a ``.proc`` / ``.scope`` get the scope name in front (``Scope_label``)
``.sym``        RGBDS (``rgblink -n``): ``BB:AAAA Name`` (bank:address); also the plain ``AAAA Name`` /
                ``Name = $AAAA`` forms other assemblers write
``.mlb``        Mesen labels: Mesen 1 ``P:1234:Name:comment`` (P = PRG ROM offset, R = RAM, S / W = save /
                work RAM, G = register) and Mesen 2 ``NesPrgRom:1234:Name:comment`` / ``GbPrgRom`` ...
``.nl``         FCEUX name lists (``game.nes.0.nl``, ``game.nes.ram.nl``): ``$C000#Name#comment``
==============  ==========================================================================================

``read_labels(path, image=None) -> LabelSet``. PRG-ROM offsets (Mesen) need the ROM image (radide/retro/cpu/romfmt.py)
to become CPU addresses. ``merge_into_hints(hints_path, labels)`` adds them to ``hints.json`` (``labels``,
``comments``; bank-specific names as ``"bank:addr"`` keys) - Re-disassemble with Hints then uses them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_RESERVED = {"a", "x", "y", "s", "p", "af", "bc", "de", "hl", "sp", "pc", "ix", "iy", "c", "nc", "z", "nz",
             "b", "d", "e", "h", "l"}


@dataclass
class LabelSet:
    labels: dict = field(default_factory=dict)          # addr -> name
    bank_labels: dict = field(default_factory=dict)     # (bank, addr) -> name
    comments: dict = field(default_factory=dict)        # addr -> text
    source: str = ""
    skipped: int = 0

    def __len__(self) -> int:
        return len(self.labels) + len(self.bank_labels)


def clean_name(name: str) -> str:
    """A label name every supported assembler accepts."""
    n = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    if not n:
        return ""
    if n[0].isdigit():
        n = "_" + n
    if n.lower() in _RESERVED:
        n = n + "_"
    return n


def _hex(text: str) -> int:
    t = text.strip().lstrip("$").lower()
    if t.startswith("0x"):
        t = t[2:]
    return int(t, 16)


# ------------------------------------------------------------------ ca65 / ld65 .dbg
def parse_dbg(text: str) -> LabelSet:
    out = LabelSet(source="ca65 .dbg")
    scopes: dict[str, str] = {}
    syms = []
    for line in text.splitlines():
        kind, _sep, rest = line.partition("\t")
        if kind not in ("sym", "scope"):
            continue
        fields = dict(re.findall(r'(\w+)=("[^"]*"|[^,]*)', rest))
        fields = {k: v.strip('"') for k, v in fields.items()}
        if kind == "scope":
            scopes[fields.get("id", "")] = fields.get("name", "")
        else:
            syms.append(fields)
    for f in syms:
        if "val" not in f:
            continue
        name = f.get("name", "")
        if f.get("type") != "lab" or not name or name.startswith(("@", "__", "CPU_")):
            out.skipped += 1                    # constants (type=equ) are not addresses; ca65's own symbols
            continue
        try:
            val = int(f["val"], 0)
        except ValueError:
            continue
        scope = scopes.get(f.get("scope", "0"), "")
        full = clean_name(f"{scope}_{name}" if scope else name)
        if not full:
            continue
        if val in out.labels and not scope and "_" in out.labels[val]:
            out.labels[val] = full                            # a global name wins over a scoped one
        out.labels.setdefault(val, full)
    return out


# ------------------------------------------------------------------ RGBDS .sym (and simple listings)
def parse_sym(text: str) -> LabelSet:
    out = LabelSet(source="symbol file")
    for line in text.splitlines():
        s = line.split(";", 1)[0].strip()
        if not s:
            continue
        m = re.match(r"^([0-9A-Fa-f]{1,4}):([0-9A-Fa-f]{4})\s+(\S+)", s)
        if m:
            bank, addr, name = int(m.group(1), 16), int(m.group(2), 16), clean_name(m.group(3))
            if not name:
                continue
            if 0x4000 <= addr < 0x8000 and bank >= 1:
                out.bank_labels[(bank, addr)] = name
            else:
                out.labels.setdefault(addr, name)
            continue
        m = re.match(r"^(\S+)\s*(?:=|EQU|equ|\.equ)\s*\$?(?:0x)?([0-9A-Fa-f]{1,6})\b", s)
        if m and not m.group(1)[0].isdigit():
            out.labels.setdefault(int(m.group(2), 16), clean_name(m.group(1)))
            continue
        m = re.match(r"^\$?([0-9A-Fa-f]{4,6})\s+\.?(\S+)$", s)
        if m:
            out.labels.setdefault(int(m.group(1), 16), clean_name(m.group(2)))
    return out


# ------------------------------------------------------------------ Mesen .mlb
MESEN_ROM_TYPES = {"P", "NesPrgRom", "GbPrgRom", "SnesPrgRom", "PcePrgRom", "SmsPrgRom", "GbaPrgRom"}
MESEN_CPU_TYPES = {"R", "G", "NesInternalRam", "NesMemory", "GbHighRam", "GbWorkRam", "NesWorkRam", "NesSaveRam",
                   "SnesWorkRam", "Register", "NesRegister", "GbRegister", "S", "W"}
# RAM types whose numbers are offsets in that RAM: (CPU address of offset 0)
MESEN_RAM_BASE = {"R": 0x0000, "NesInternalRam": 0x0000, "G": 0x0000, "NesRegister": 0x0000, "Register": 0x0000,
                  "S": 0x6000, "W": 0x6000, "NesSaveRam": 0x6000, "NesWorkRam": 0x6000, "GbWorkRam": 0xC000,
                  "GbHighRam": 0xFF80, "GbRegister": 0x0000, "NesMemory": 0x0000, "SnesWorkRam": 0x7E0000}


def parse_mlb(text: str, image=None) -> LabelSet:
    out = LabelSet(source="Mesen .mlb")
    for line in text.splitlines():
        parts = line.rstrip("\r\n").split(":", 3)
        if len(parts) < 3:
            continue
        typ, addr_s, name = parts[0].strip(), parts[1].strip(), clean_name(parts[2])
        comment = parts[3].strip() if len(parts) > 3 else ""
        try:
            start = _hex(addr_s.split("-")[0])
        except ValueError:
            continue
        if typ in MESEN_ROM_TYPES:
            loc = prg_offset_to_cpu(image, start) if image is not None else None
            if loc is None:
                out.skipped += 1
                continue
            addr, bank, banked = loc
        elif typ in MESEN_RAM_BASE:
            addr, bank, banked = MESEN_RAM_BASE[typ] + start, 0, False
        else:
            out.skipped += 1
            continue
        if name:
            if banked:
                out.bank_labels[(bank, addr)] = name
            else:
                out.labels.setdefault(addr, name)
        if comment:
            out.comments.setdefault(addr, comment.replace("\\n", " "))
    return out


# ------------------------------------------------------------------ FCEUX .nl
def parse_nl(text: str, bank: int | None = None) -> LabelSet:
    out = LabelSet(source="FCEUX .nl")
    for line in text.splitlines():
        m = re.match(r"^\$([0-9A-Fa-f]{1,4})(?:/([0-9A-Fa-f]+))?#([^#]*)#?(.*)$", line.strip())
        if not m:
            continue
        addr = int(m.group(1), 16)
        name, comment = clean_name(m.group(3)), m.group(4).strip()
        if name:
            if bank is not None and addr >= 0x8000:
                out.bank_labels[(bank, addr)] = name
            else:
                out.labels.setdefault(addr, name)
        if comment:
            out.comments.setdefault(addr, comment.replace("\\", " "))
    return out


# ------------------------------------------------------------------ ROM offsets
def prg_offset_to_cpu(image, prg_off: int):
    """(CPU address, bank, banked?) of a PRG-ROM offset (NES: after the header; other systems: file offset)."""
    from .romfmt import file_to_cpu
    if image is None:
        return None
    file_off = prg_off
    if image.system == "nes" and image.data[:4] == b"NES\x1a":
        file_off = prg_off + 16 + (512 if image.data[6] & 4 else 0)
    loc = file_to_cpu(image, file_off)
    if loc is None:
        return None
    addr, seg = loc
    return addr, seg.bank, not seg.fixed                  # switchable banks: a bank-specific name


def read_labels(path, image=None) -> LabelSet:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    ext = p.suffix.lower()
    if ext == ".dbg":
        return parse_dbg(text)
    if ext == ".mlb":
        return parse_mlb(text, image)
    if ext == ".nl":
        m = re.search(r"\.(\d+|ram)\.nl$", p.name, re.I)
        bank = int(m.group(1)) if m and m.group(1).isdigit() else None
        nes_banks = len([s for s in image.segments if s.trace]) if image is not None else 1
        return parse_nl(text, bank if nes_banks > 1 else None)
    return parse_sym(text)


def merge_into_hints(hints_path, labels: LabelSet, overwrite: bool = False) -> int:
    """Add *labels* to hints.json (kept names win unless *overwrite*); returns how many names were added."""
    hp = Path(hints_path)
    try:
        d = json.loads(hp.read_text(encoding="utf-8")) if hp.is_file() else {}
    except ValueError:
        d = {}
    lab = d.setdefault("labels", {})
    com = d.setdefault("comments", {})
    have = {}
    for k in lab:
        have[str(k).upper().lstrip("$")] = k
    n = 0
    items = [(f"{a:04X}", v) for a, v in sorted(labels.labels.items())] + \
            [(f"{b:02X}:{a:04X}", v) for (b, a), v in sorted(labels.bank_labels.items())]
    for key, name in items:
        old = have.get(key)
        if old is not None and not overwrite:
            continue
        if old is not None:
            lab.pop(old, None)
        lab[key] = name
        n += 1
    for a, text in sorted(labels.comments.items()):
        key = f"{a:04X}"
        if key not in com or overwrite:
            com[key] = text
    hp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return n


LABEL_FILTER = "Label files (*.dbg *.sym *.mlb *.nl *.lbl *.labels);;All files (*)"

__all__ = ["LABEL_FILTER", "LabelSet", "clean_name", "merge_into_hints", "parse_dbg", "parse_mlb", "parse_nl",
           "parse_sym", "prg_offset_to_cpu", "read_labels"]
