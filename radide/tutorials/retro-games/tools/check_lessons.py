"""Checker for the retro-games course: runs every runnable block of radide/tutorials/retro-games.

    python radide/tutorials/retro-games/tools/check_lessons.py            # all lessons
    python radide/tutorials/retro-games/tools/check_lessons.py 03 -v      # lessons whose id starts with 03

Block kinds (fence info strings):

* ``python run`` / ``python exercise`` / ``python solution`` - pure Python (the lesson viewer runs them too);
  output compared with the ``text output`` block after them (radide.tutorials.check).
* ``dasm run`` / ``dasm solution`` - an Atari 2600 program: it replaces main.asm of a new "Atari 2600 Game (DASM)"
  project (radide.retro.dev templates, atari2600.h included) and is built with DASM.  A hidden
  ``<!-- test: {"frames": 4, "hold": "right", "ram": ["$80"], "ramhex": ["$81"], "tia": ["COLUBK"]} -->`` before it runs the cartridge in the course's
  6502 + 2600 simulator (tools/sim2600.py) and prints ``scanlines: N`` (last frame) and ``$80 = V`` lines, which
  must equal the following ``text output`` block.  ``dasm exercise`` must build (and needs a solution).
* ``ca65 run`` - an NES program: replaces main.s of a new "NES Game (ca65 assembly)" project (nes.inc, nes.cfg).
  Built with ca65 + ld65; the iNES header is printed (``iNES: mapper 0, PRG 32 KB, CHR 8 KB``).
* ``rgbds run`` - a Game Boy program: replaces main.asm of a new "Game Boy Game (RGBDS)" project (gb.inc);
  built with rgbasm / rgblink / rgbfix; prints the title and whether the logo and checksums are valid.

Every runnable block needs an expected output; quiz JSON is validated.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402

TEMPLATES = {"dasm": ("retro-atari2600", "a2600_kernel", "main.asm"),
             "ca65": ("retro-nes", "nes_asm", "main.s"),
             "rgbds": ("retro-gameboy", "gb_asm", "main.asm")}


def build_retro(kind: str, code: str, work: Path):
    """New template project with the block as its main file -> (ok, rom path, log text)."""
    from radide.languages import get_plugin
    from radide.retro.dev.build import Builder
    pid, tpl, main = TEMPLATES[kind]
    folder = work / "Lesson"
    shutil.rmtree(folder, ignore_errors=True)
    get_plugin(pid).create_new_project(folder, "Lesson", tpl)
    (folder / main).write_text(code, encoding="utf-8")
    lines: list[str] = []
    b = Builder(folder, log=lines.append)
    ok = b.build()
    errs = [f"{d.file}:{d.line}: {d.severity}: {d.message}" for d in b.diags]
    return ok and b.out_path.is_file(), b.out_path, "\n".join(lines + errs)


def report_2600(rom: Path, spec: dict) -> str:
    from sim2600 import Atari2600
    m = Atari2600(rom.read_bytes())
    hold = spec.get("hold", "")
    m.swcha = 0xFF & ~{"right": 0x80, "left": 0x40, "down": 0x20, "up": 0x10}.get(hold, 0)
    if hold == "fire":
        m.inpt4 = 0
    m.run_frames(int(spec.get("frames", 3)))
    out = []
    lines = m.scanlines()
    out.append(f"scanlines: {lines[-1] if lines else 0}")
    for a in spec.get("ram", []):
        out.append(f"{a} = {m.ram_at(int(a.lstrip('$'), 16))}")
    for a in spec.get("ramhex", []):
        out.append(f"{a} = ${m.ram_at(int(a.lstrip('$'), 16)):02X}")
    for reg in spec.get("tia", []):
        v = m.tia.get(reg)
        out.append(f"{reg} = ${v:02X}" if v is not None else f"{reg} = (never written)")
    return "\n".join(out)


def report_nes(rom: Path) -> str:
    data = rom.read_bytes()
    if data[:4] != b"NES\x1a":
        return "not an iNES file"
    mapper = (data[6] >> 4) | (data[7] & 0xF0)
    return f"iNES: mapper {mapper}, PRG {data[4] * 16} KB, CHR {data[5] * 8} KB"


def report_gb(rom: Path) -> str:
    from radide.retro.rom.detect import detect
    data = rom.read_bytes()
    info = detect(data, rom.name)
    rows = dict(info.rows)
    title = data[0x134:0x144].split(b"\0")[0].decode("ascii", "replace")
    logo_ok = data[0x104:0x134] == _logo(data)
    hc = 0
    for b in data[0x134:0x14D]:
        hc = (hc - b - 1) & 0xFF
    gc = (sum(data) - data[0x14E] - data[0x14F]) & 0xFFFF
    return (f"Game Boy: title {title}, logo {'OK' if logo_ok else 'bad'}, header checksum "
            f"{'OK' if hc == data[0x14D] else 'bad'}, global checksum "
            f"{'OK' if gc == (data[0x14E] << 8 | data[0x14F]) else 'bad'}" + ("" if rows else " (no header rows)"))


def _logo(data: bytes) -> bytes:
    # the logo bitmap itself is not stored here (rgbfix writes it): its CRC32 and byte sum are compared instead
    import zlib
    logo = data[0x104:0x134]
    return logo if sum(logo) == 0x1546 and zlib.crc32(logo) == 0x46195417 else b""


def expected_after(blocks, i):
    for nxt in blocks[i + 1:]:
        if nxt.role == "output" and nxt.lang == "text":
            return nxt.code
        if nxt.lang != "text":
            return None
    return None


def main(argv):
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("retro-games")
    assert course is not None, "course retro-games not found"
    work_root = Path(tempfile.mkdtemp(prefix="retrocourse-"))
    total = failed = 0
    for les in course.lessons:
        if only and not any(les.id.startswith(o) for o in only):
            continue
        blocks = les.blocks()
        for i, b in enumerate(blocks):
            head = b.info.split()[0].lower() if b.info.split() else ""
            role = b.info.split()[1].lower() if len(b.info.split()) > 1 else ""
            if b.lang == "quiz":
                total += 1
                if not b.quiz or not (0 <= int(b.quiz["answer"]) < len(b.quiz["choices"])):
                    failed += 1
                    print(f"FAIL {les.id} #{b.index} (line {b.line}): bad quiz JSON")
                continue
            work = work_root / f"{les.id}-{b.index}"
            work.mkdir(parents=True, exist_ok=True)
            if b.lang == "py" and b.role in ("run", "solution", "exercise"):
                total += 1
                if b.role == "exercise":
                    ok, why = b.solution is not None, "exercise without a solution block"
                    r = None
                else:
                    r = T.check(b, None, None, work)
                    ok = r.ok and b.expected is not None
                    why = "; ".join(r.problems) + ("" if b.expected is not None else " [no expected output]")
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} python {b.role} (line {b.line}) {'' if ok else why}")
                    if not ok and r is not None:
                        print("    --- got ---\n    " + r.output.strip().replace("\n", "\n    "))
                continue
            if head in TEMPLATES and role in ("run", "solution", "exercise"):
                total += 1
                ok, rom, log = build_retro(head, b.code, work)
                got, exp = "", expected_after(blocks, i)
                if ok and role != "exercise":
                    try:
                        got = {"dasm": lambda: report_2600(rom, b.spec or {}), "ca65": lambda: report_nes(rom),
                               "rgbds": lambda: report_gb(rom)}[head]()
                    except Exception as e:  # noqa: BLE001
                        ok, got = False, f"simulator: {e}"
                    ok = ok and exp is not None and T.norm(got) == T.norm(exp)
                if role == "exercise":
                    sol = next((x for x in blocks[i + 1:] if x.info.split()[:2] == [head, "solution"]), None)
                    if sol is None:
                        ok, log = False, "exercise without a solution block"
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} {head} {role} (line {b.line})")
                    if not ok:
                        print("    build log:\n    " + log.strip()[-1500:].replace("\n", "\n    "))
                        print("    --- got ---\n    " + got.replace("\n", "\n    "))
                        print("    --- expected ---\n    " + str(exp).strip().replace("\n", "\n    "))
                continue
    shutil.rmtree(work_root, ignore_errors=True)
    print(f"\n{total - failed}/{total} blocks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
