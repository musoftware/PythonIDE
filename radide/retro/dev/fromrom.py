"""Disassemble a ROM / program file into a buildable retro project (no Qt in here).

``create_project(rom, folder, name, system=None, base=None, entry=None, undocumented=False)``:

1. loads the file (radide/retro/cpu/romfmt.py) and traces its code (radide/retro/cpu/disasm.py, with the
   project's ``hints.json`` when re-disassembling),
2. writes the source for the system's assembler (DASM / ca65 + a generated linker configuration / RGBDS /
   sjasmplus), the data files (CHR ROM ...), a copy of the original in ``rom/`` and ``hints.json``,
3. builds it and compares the result with the original byte for byte (``rebuild check``).

Only the user's own file is read; nothing is downloaded except the assembler itself.
``python -m radide.retro.dev.fromrom <rom> <folder> [system]`` does the same from a console.
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..cpu import disasm, romfmt
from ..cpu.disasm import Hints
from .systems import SYSTEMS

HINTS_TEMPLATE = {
    "_help": "Hints for 'Re-disassemble with hints': code = addresses where code starts that the tracer did not "
             "reach (jump tables, code called through pointers); data = [first, last] address ranges that are "
             "data although the tracer took them for code; labels = names for addresses; comments = a comment "
             "line above an address; undocumented = follow the 6502 undocumented opcodes; jump_tables = "
             "[first, last, \"word\" | \"rts\" (address-1, the push + RTS trick), optional hi-byte table] - every "
             "entry becomes code; auto_tables = find the RTS / JMP (indirect) dispatchers automatically. Addresses "
             "in hex; \"bank:addr\" label keys name an address in one bank only.",
    "code": [], "data": [], "labels": {}, "comments": {}, "undocumented": False, "jump_tables": [],
    "auto_tables": True,
}


@dataclass
class Result:
    folder: Path
    project: object
    image: romfmt.RomImage
    dis: disasm.Disassembly
    main: str
    build_ok: bool = False
    identical: dict | None = None
    log: list = field(default_factory=list)

    def summary(self) -> str:
        st = self.dis.stats()
        same = self.identical or {}
        lines = [f"{self.image.title}: {self.image.name}",
                 f"{st['instructions']} instructions ({st['code_bytes']} code bytes), {st['data_bytes']} data bytes, "
                 f"{st['labels']} labels, {st['equates']} hardware names"]
        if not self.build_ok:
            lines.append("Rebuild: the assembler failed (see the Output window / Error List)")
        elif same.get("same"):
            lines.append(f"Rebuild check: byte-identical ({same.get('size', 0)} bytes)")
        else:
            lines.append(f"Rebuild check: DIFFERENT - {same.get('reason', '?')}")
        if self.dis.conflicts:
            lines.append(f"{len(self.dis.conflicts)} tracing conflict(s), e.g. {self.dis.conflicts[0]}")
        return "\n".join(lines)


def _header(img: romfmt.RomImage, sysd, source_name: str) -> str:
    info = "\n".join(f";   {k}: {v}" for k, v in img.info.items() if not k.startswith("_") and k != "SHA-1")
    return (f"; {img.name} - disassembled by RAD IDE ({sysd.title}, {sysd.dialect})\n"
            f"; Source file: {source_name} (a copy is in rom/), SHA-1 {img.sha1}\n{info}\n"
            f"; Building this file gives back the original bytes: F5 / Build prints the rebuild check, and\n"
            f"; Tools > Retro > Retro Development > Rebuild Check compares again. Code the tracer did not reach\n"
            f"; stays data (.byte): add hints in hints.json and use Re-disassemble with Hints (same menu), or\n"
            f"; simply edit the code - it is ordinary {sysd.dialect} source.\n")


def render_source(img: romfmt.RomImage, dis: disasm.Disassembly, sysd) -> tuple[str, dict[str, str]]:
    """(main source, {extra text file: content}) for the system's assembler."""
    d = sysd.dialect
    eq = dis.render_equates(d)
    out = [_header(img, sysd, img.file_name or img.name)]
    extra: dict[str, str] = {}
    if img.system == "atari2600":
        out.append("        processor 6502\n")
        if eq:
            out.append("; ---- hardware registers and RAM used by the program\n" + eq + "\n")
        segs = img.segments
        if len(segs) == 1:
            out.append(f"        seg code\n        org ${segs[0].base:04X}\n")
            out.append(dis.render_segment(segs[0], d))
        else:
            for s in segs:
                out.append(f"\n; ================================ bank {s.bank} (4K, runs at $F000)\n"
                           f"        seg bank{s.bank}\n        org ${s.bank * 0x1000:04X}\n        rorg $F000\n")
                out.append(dis.render_segment(s, d))
        return "\n".join(out) + "\n", extra
    if img.system in ("nes", "c64", "6502"):
        out.append('.setcpu "6502"\n')
        if eq:
            out.append("; ---- hardware registers used by the program\n" + eq + "\n")
        mem, segs_cfg = [], []
        for s in img.segments:
            name = s.name
            out.append(f'\n.segment "{name}"')
            out.append(dis.render_segment(s, d, address_comments=s.trace))
            mem.append(f"    M_{name}: start = ${s.base:04X}, size = ${len(s.data):04X}, type = ro, file = %O;")
            segs_cfg.append(f"    {name}: load = M_{name}, type = ro;")
        for fname, blob in img.extras.items():
            seg = {"chr.bin": "CHARS", "tail.bin": "TAIL"}.get(fname, fname.split(".")[0].upper())
            out.append(f'\n.segment "{seg}"\n        .incbin "{fname}"')
            mem.append(f"    M_{seg}: start = $0000, size = ${len(blob):04X}, type = ro, file = %O;")
            segs_cfg.append(f"    {seg}: load = M_{seg}, type = ro;")
        extra[f"{img.system}.cfg"] = ("# Memory map generated by RAD IDE for the disassembly of " + img.name +
                                      "\nMEMORY {\n" + "\n".join(mem) + "\n}\nSEGMENTS {\n" +
                                      "\n".join(segs_cfg) + "\n}\n")
        return "\n".join(out) + "\n", extra
    if img.system == "gameboy":
        if eq:
            out.append("; ---- hardware registers used by the program\n" + eq + "\n")
        for s in img.segments:
            if s.bank == 0:
                out.append('\nSECTION "ROM Bank $000", ROM0[$0000]')
            else:
                out.append(f'\nSECTION "ROM Bank ${s.bank:03X}", ROMX[$4000], BANK[{s.bank}]')
            out.append(dis.render_segment(s, d))
        return "\n".join(out) + "\n", extra
    # zx / z80
    if eq:
        out.append("; ---- ROM routines and system variables used by the program\n" + eq + "\n")
    for s in img.segments:
        out.append(f"\n        ORG ${s.base:04X}")
        out.append(dis.render_segment(s, d))
    return "\n".join(out) + "\n", extra


def disassemble(img: romfmt.RomImage, hints: Hints | None = None, undocumented: bool | None = None):
    return disasm.analyze(img.segments, img.cpu, img.system, hints, undocumented)


def _system_for(img: romfmt.RomImage):
    sid = {"6502": "c64", "z80": "zx"}.get(img.system, img.system)
    return SYSTEMS[sid]


def create_project(rom, folder, name: str | None = None, system: str | None = None, base: int | None = None,
                   entry: int | None = None, undocumented: bool = False, build: bool = True, log=print,
                   hints: Hints | None = None) -> Result:
    from ...model import Project
    rom = Path(rom)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    img = romfmt.load(rom, system, base, entry)
    if img.system == "6502":
        raise ValueError("raw 6502 binaries: choose Atari 2600 (2K/4K ROM), NES (.nes) or C64 (.prg)")
    sysd = _system_for(img)
    name = name or rom.stem
    hints = hints or Hints.load(folder / "hints.json")
    dis = disassemble(img, hints, undocumented or hints.undocumented)
    src, extra = render_source(img, dis, sysd)
    ext = {"dasm": ".asm", "ca65": ".s", "rgbds": ".asm", "sjasmplus": ".asm"}[sysd.dialect]
    main = "main" + ext
    (folder / main).write_text(src, encoding="utf-8")
    for fname, text in extra.items():
        (folder / fname).write_text(text, encoding="utf-8")
    for fname, blob in img.extras.items():
        (folder / fname).write_bytes(blob)
    (folder / "rom").mkdir(exist_ok=True)
    orig = folder / "rom" / rom.name
    if rom.resolve() != orig.resolve():
        shutil.copy2(rom, orig)
    if not (folder / "hints.json").exists():
        (folder / "hints.json").write_text(json.dumps(HINTS_TEMPLATE, indent=1), encoding="utf-8")
    settings = {"system": sysd.id, "lang": "asm", "main": main, "output": f"{name}{sysd.rom_ext}",
                "original": f"rom/{rom.name}", "disassembly": {"source": rom.name, "sha1": img.sha1,
                                                                 "system": img.system}}
    if base is not None:
        settings["disassembly"]["base"] = base
    if entry is not None:
        settings["disassembly"]["entry"] = entry
    if extra:
        settings["cfg"] = next(iter(extra))
    if sysd.id == "gameboy":
        settings["fix"] = False
    if sysd.id == "zx":
        code = b"".join(s.data for s in img.segments)
        (folder / "rom" / "code.bin").write_bytes(code)
        settings.update({"original": "rom/code.bin", "compare_what": "code", "org": img.segments[0].base})
        start = next((a for s in img.segments for a, n in s.entries if n == "Start"), img.segments[0].base)
        settings["entry"] = start
        if rom.suffix.lower() != ".tap":
            settings["output"] = f"{name}.bin"
    elif img.compare and img.compare != (0, len(img.data)):
        settings["compare"] = list(img.compare)
    mods = [main] + list(extra)
    project = Project(folder, name, sysd.plugin, [], Path(main).stem, mods)
    project.extra["retro"] = settings
    project.save()
    if not (folder / ".gitignore").exists():
        (folder / ".gitignore").write_text("_build/\n*.o\n", encoding="utf-8")
    res = Result(folder, project, img, dis, main)
    if build:
        from .build import Builder
        b = Builder(folder, project, log=lambda t: (res.log.append(t), log(t)))
        res.build_ok = b.build()
        if res.build_ok:
            res.identical = b.compare() if not settings.get("original") else \
                json.loads((folder / "_build" / "diagnostics.json").read_text(encoding="utf-8")).get("identical")
    return res


def redisassemble(folder, log=print) -> Result:
    """Disassemble the project's original again with its hints.json (main source saved as *.bak first)."""
    from ...model import Project
    folder = Path(folder)
    project = Project.load(folder)
    s = (project.extra or {}).get("retro") or {}
    d = s.get("disassembly") or {}
    src = folder / "rom" / d.get("source", Path(s.get("original", "")).name)
    if not src.is_file():
        raise FileNotFoundError(f"the original ROM is not in {folder / 'rom'}")
    main = folder / s.get("main", "main.asm")
    if main.is_file():
        shutil.copy2(main, main.with_suffix(main.suffix + ".bak"))
    return create_project(src, folder, project.name, d.get("system"), d.get("base"), d.get("entry"), log=log)


# ============================================================================ hints editing (editor / hex view)
HINT_KINDS = ("code", "data", "word_table", "rts_table", "label", "comment")


def hints_file(folder) -> Path:
    return Path(folder) / "hints.json"


def load_hints_dict(folder) -> dict:
    p = hints_file(folder)
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        d = {}
    for k, v in HINTS_TEMPLATE.items():
        d.setdefault(k, json.loads(json.dumps(v)))
    return d


def add_hint(folder, kind: str, start: int, end: int | None = None, text: str = "") -> dict:
    """Add one hint to the project's hints.json and return the new dict.

    kind: ``code`` (code starts at *start*), ``data`` (*start*..*end* is data), ``word_table`` / ``rts_table``
    (*start*..*end* is a jump table of addresses / addresses-1), ``label`` / ``comment`` (*text* at *start*)."""
    if kind not in HINT_KINDS:
        raise ValueError(f"unknown hint kind {kind!r}")
    d = load_hints_dict(folder)
    a = f"{start & 0xFFFF:04X}"
    e = f"{(end if end is not None else start) & 0xFFFF:04X}"
    if kind == "code":
        lst = [str(x).upper().lstrip("$") for x in d["code"]]
        if a not in lst:
            d["code"].append(a)
        d["data"] = [r for r in d["data"] if not (int(str(r[0]), 16) <= start <= int(str(r[1]), 16))]
    elif kind == "data":
        d["data"].append([a, e])
        d["code"] = [c for c in d["code"] if not (start <= int(str(c), 16) <= (end if end is not None else start))]
    elif kind in ("word_table", "rts_table"):
        if end is None or end <= start:
            end = start + 1
            e = f"{end & 0xFFFF:04X}"
        d["jump_tables"] = [t for t in d["jump_tables"] if str(t[0]).upper() != a]
        d["jump_tables"].append([a, e, "rts" if kind == "rts_table" else "word"])
    elif kind == "label":
        from ..cpu.labels import clean_name
        name = clean_name(text)
        if not name:
            raise ValueError("a label needs a name")
        d["labels"][a] = name
    else:
        d["comments"][a] = text
    hints_file(folder).write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def import_labels(folder, label_file, overwrite: bool = False) -> tuple[int, str]:
    """Merge a ca65 .dbg / RGBDS .sym / Mesen .mlb / FCEUX .nl file into hints.json -> (names added, kind)."""
    from ...model import Project
    from ..cpu.labels import merge_into_hints, read_labels
    folder = Path(folder)
    image = None
    try:
        s = (Project.load(folder).extra or {}).get("retro") or {}
        d = s.get("disassembly") or {}
        src = folder / "rom" / d.get("source", Path(s.get("original", "")).name)
        if src.is_file():
            image = romfmt.load(src, d.get("system"), d.get("base"), d.get("entry"))
    except Exception:  # noqa: BLE001 - labels with CPU addresses still work without the image
        image = None
    ls = read_labels(label_file, image)
    return merge_into_hints(hints_file(folder), ls, overwrite), ls.source


def address_of_line(text: str) -> int | None:
    """The address in a disassembly source line's ``; 1234`` comment (None when the line has none)."""
    import re
    m = re.search(r";\s*([0-9A-Fa-f]{4})(?![0-9A-Fa-f])", text)
    return int(m.group(1), 16) if m else None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print("usage: python -m radide.retro.dev.fromrom <rom file> <project folder> [system] [base hex]")
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    system = argv[2] if len(argv) > 2 else None
    base = int(argv[3], 16) if len(argv) > 3 else None
    res = create_project(argv[0], argv[1], system=system, base=base)
    print(res.summary())
    return 0 if res.build_ok and (res.identical or {}).get("same") else 1


if __name__ == "__main__":
    raise SystemExit(main())
