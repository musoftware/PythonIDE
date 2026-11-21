"""Retro dev slice - every New Project template (no Qt): create, build with the real toolchain, check the output
(iNES header, Game Boy checksums, PRG load address, TAP blocks), put a mistake in and check the Error List row
(file + line), then disassemble the built ROM back into a project and check the rebuild is byte-identical.
Also the editor support: completions, hover, go to definition, outline, Monarch grammar.

    python samples/Tests/Retro/Dev/check_templates.py [--offline]
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.languages import get_plugin  # noqa: E402
from radide.retro.dev import toolchain  # noqa: E402
from radide.retro.dev.build import Builder  # noqa: E402
from radide.retro.dev.templates import TEMPLATES  # noqa: E402

RESULTS: list[tuple[str, str]] = []
OFFLINE = "--offline" in sys.argv
WORK = Path(tempfile.mkdtemp(prefix="radide-retro-tpl-"))
NEEDS = {"retro-atari2600": "dasm", "retro-nes": "ca65", "retro-gameboy": "rgbasm", "retro-c64": "ca65",
         "retro-zx": "sjasmplus"}
MISTAKE = {"dasm": ("        ldq #1\n", None), "ca65": ("        ldq #1\n", None), "rgbds": ("        ld q, 1\n", None),
           "sjasmplus": ("        ld q,1\n", None), "c": ("int broken = ;\n", None)}


def check(name, cond, detail=""):
    RESULTS.append((name, "PASS" if cond else "FAIL"))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:700]}]"), flush=True)
    return bool(cond)


def skip(name, why):
    RESULTS.append((name, "SKIP"))
    print(f"SKIP {name}  ({why})", flush=True)


def output_checks(tid: str, out: Path) -> None:
    data = out.read_bytes()
    if tid == "a2600_kernel":
        check("2600 template: 4K cartridge, reset vector -> $F000", len(data) == 4096 and data[-4:-2] == b"\x00\xf0")
    elif tid.startswith("nes"):
        check(f"{tid}: iNES header, 32K PRG + 8K CHR", data[:4] == b"NES\x1a" and len(data) == 16 + 32768 + 8192,
              len(data))
    elif tid == "gb_asm":
        from radide.retro.cpu.romfmt import gb_global_checksum, gb_header_checksum
        check("GB template: rgbfix logo + header / global checksums", data[0x104] == 0xCE and
              data[0x14D] == gb_header_checksum(data) and
              (data[0x14E] << 8 | data[0x14F]) == gb_global_checksum(data))
    elif tid.startswith("c64"):
        check(f"{tid}: PRG loads at $0801 with SYS line", data[:2] == b"\x01\x08" and b"\x9e" in data[2:16], data[:16])
    elif tid == "zx_asm":
        from radide.retro.cpu.romfmt import tap_blocks
        bl = tap_blocks(data)
        check("ZX template: TAP = BASIC loader + CODE at 32768", len(bl) == 4 and bl[2][1] == 3 and
              int.from_bytes(bl[2][14:16], "little") == 32768)


def test_templates() -> None:
    from radide.retro.dev.fromrom import create_project
    for pid, ts in TEMPLATES.items():
        plugin = get_plugin(pid)
        for t in ts:
            if t.settings.get("lang") == "acme":
                if not toolchain.find("acme"):
                    skip(f"{t.id}: build", "acme.exe not in PATH (ACME is not downloaded)")
                    continue
            need = NEEDS[pid] if t.settings.get("lang") != "c" else "cl65"
            if not toolchain.find(need) and (OFFLINE or not toolchain.ensure(need, lambda _t: None)):
                skip(f"{t.id}: build", f"{need} not available")
                continue
            folder = WORK / t.id
            project = plugin.create_new_project(folder, "Demo" + t.id.split("_")[0].title(), t.id)
            check(f"{t.id}: project created with the template's files", all((folder / f).is_file() for f, _ in t.files)
                  and project.extra.get("retro", {}).get("system") == plugin.system)
            log: list[str] = []
            b = Builder(folder, log=log.append)
            ok = b.build()
            check(f"{t.id}: builds with no errors / warnings", ok and not b.diags,
                  [d.to_dict() for d in b.diags] or "\n".join(log)[-1200:])
            if not ok:
                continue
            output_checks(t.id, b.out_path)
            # disassemble the ROM we just built and rebuild it
            rt = WORK / f"{t.id}_disasm"
            rom_copy = WORK / f"{t.id}{b.out_path.suffix}"
            shutil.copy2(b.out_path, rom_copy)
            res = create_project(rom_copy, rt, log=lambda _t: None)
            check(f"{t.id}: disassembled ROM rebuilds byte-identical", res.build_ok and (res.identical or {}).get("same"),
                  res.summary())
            # a mistake -> Error List row with file and line
            main = folder / t.settings["main"]
            text = main.read_text(encoding="utf-8")
            kind = "c" if t.settings.get("lang") == "c" else plugin.dialect
            bad_line = text.count("\n") + 1
            main.write_text(text + MISTAKE[kind][0], encoding="utf-8")
            b2 = Builder(folder, log=lambda _t: None)
            ok2 = b2.build()
            rows = [d for d in b2.diags if d.severity == "Error"]
            check(f"{t.id}: a mistake fails the build with an Error List row at {main.name}:{bad_line}",
                  not ok2 and any(Path(d.file).name == main.name and d.line == bad_line for d in rows),
                  [d.to_dict() for d in b2.diags])
            main.write_text(text, encoding="utf-8")


def test_intel() -> None:
    p = get_plugin("retro-atari2600")
    folder = WORK / "intel"
    p.create_new_project(folder, "IntelDemo", "a2600_kernel")
    path = folder / "main.asm"
    code = path.read_text(encoding="utf-8")
    lines = code.splitlines()
    names = {c.name for c in p.completions(code, 0, 0, path)}
    check("2600 completions: mnemonics, TIA / RIOT registers, project labels and equates",
          {"lda", "sta", "WSYNC", "TIM64T", "SetHorizPos", "PlayerX", "VSYNC"} <= names, sorted(names)[:40])
    ln = next(i for i, s in enumerate(lines) if "sta WSYNC" in s)
    h = p.hover(code, ln, lines[ln].index("sta") + 1, path)
    check("hover on sta: modes, opcodes, cycles", "$8D" in h and "zero page" in h and "Flags" in h, h)
    h = p.hover(code, ln, lines[ln].index("WSYNC") + 2, path)
    check("hover on WSYNC: hardware description", "$0002" in h and "scanline" in h, h)
    ln2 = next(i for i, s in enumerate(lines) if "jsr SetHorizPos" in s)
    d = p.definition(code, ln2, lines[ln2].index("SetHorizPos") + 3, path)
    check("go to definition of SetHorizPos", d and lines[d[1]].startswith("SetHorizPos"), d)
    ln3 = next(i for i, s in enumerate(lines) if "sta COLUBK" in s)
    d2 = p.definition(code, ln3, lines[ln3].index("COLUBK") + 2, path)
    check("go to definition into atari2600.h", d2 and Path(d2[0]).name == "atari2600.h", d2)
    h = p.hover("        lda #$84\n", 0, 14, path)
    check("hover on a number: hex / decimal / binary", "132" in h and "%10000100" in h, h)
    syms = [s["name"] for s in p.document_symbols(code)]
    check("outline: labels and equates", "Reset" in syms and "ScanLoop" in syms and "PlayerX" in syms, syms[:20])
    spec = p.monaco_language(path)
    check("Monarch grammar for DASM", spec["id"] == "rad-retro-dasm" and "lda" in spec["monarch"]["instructions"] and
          "WSYNC" in spec["monarch"]["hardware"])
    refs = p.references(code, ln2, lines[ln2].index("SetHorizPos") + 3, path)
    check("find all references of SetHorizPos", refs and len(refs) >= 2, refs)
    tip = p.calltip("        lda ", 0, 12, path)
    check("signature help lists the addressing modes", "immediate" in tip and "absolute" in tip, tip)
    gb = get_plugin("retro-gameboy")
    h = gb.hover("        ldh a, [rLY]\n", 0, 18, None)
    check("Game Boy hover on rLY", "$FF44" in h and "scanline" in h, h)
    h = gb.hover("        ldh a, [rLY]\n", 0, 9, None)
    check("Game Boy hover on ldh: T-states", "cycles" in h.lower() and "$E0" in h, h)
    zx = get_plugin("retro-zx")
    h = zx.hover("        djnz loop\n", 0, 9, None)
    check("Z80 hover on djnz", "B = B - 1" in h and "13/8" in h, h)
    h = zx.hover("        out ($FE),a\n", 0, 15, None)
    check("ZX hover on port $FE: border / keyboard", "border" in h, h)
    nes = get_plugin("retro-nes")
    names = {c.name for c in nes.completions(".segment \"CODE\"\n        ", 1, 8, None)}
    check("NES completions: PPU registers and ca65 directives", {"PPUCTRL", "OAMDMA", ".segment", "lda"} <= names)
    spec = gb.monaco_language(Path("x.asm"))
    check("Monarch grammar for RGBDS (SM83 instructions)", spec["id"] == "rad-retro-rgbds" and
          "ldh" in spec["monarch"]["instructions"])


def main() -> int:
    test_intel()
    test_templates()
    shutil.rmtree(WORK, ignore_errors=True)
    p = sum(r == "PASS" for _, r in RESULTS)
    f = [n for n, r in RESULTS if r == "FAIL"]
    s = sum(r == "SKIP" for _, r in RESULTS)
    print(f"{p}/{len(RESULTS)} passed, {s} skipped; FAILED: {f or 'none'}")
    return 1 if f else 0


if __name__ == "__main__":
    raise SystemExit(main())
