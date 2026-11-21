"""Generate + build a design with its system's toolchain, check the result, and start it in an emulator.

    res = build(design, outdir, log=print, download=False)
    # {"ok": bool, "rom": Path, "log": str, "warnings": [...], "checks": [...], "missing": "" | tool}
    proc = run(res, design.system)            # radide.retro.emu.run_rom (Stella / Mesen / mGBA / DOSBox-X)

Checks after a successful build (no emulator needed):

* Atari 2600: the ROM runs in the 6502 / TIA probe (sim6502.Atari2600Probe): lines per frame must be 262 / 312
  and every kernel line must hold the playfield / colour / graphics values of the design.
* NES: the ROM runs in sim6502.NESProbe: the name tables, attribute tables and palettes the loader writes must
  match the design.
* DOS mode 13h (.COM): the program runs in RAD IDE's 8086 emulator; video memory must match the design.
* Game Boy: the map / tile / sprite data must sit in the ROM at the addresses in the .sym file and the header
  checksum must be valid.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from . import SYSTEMS, EMU_SYSTEM
from .compat import ensure_tool, find_tool, run_in_emulator
from .model import Design, ident

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def build(d: Design, outdir, log=print, download: bool = False) -> dict:
    m = SYSTEMS[d.system]
    out = Path(outdir)
    info = m.generate(d, out)
    res = {"ok": False, "rom": Path(info["rom"]), "log": "", "warnings": list(info.get("warnings", [])),
           "checks": [], "missing": "", "files": info.get("files", [])}
    for w in res["warnings"]:
        log(f"warning: {w}")

    def finder(exe: str) -> str:
        return ensure_tool(exe, log=log, download=True) if download else find_tool(exe)
    custom = getattr(m, "custom_build", None)
    if custom is not None:
        try:
            got = custom(d, out, log=log, download=download)
        except Exception as e:  # noqa: BLE001 - the DOS builder is another slice
            got = (False, None)
            log(f"*** build failed: {e}")
        if got is not None:
            ok, exe = got
            if exe:
                res["rom"] = Path(exe)
            res["ok"] = bool(ok) and res["rom"].is_file()
            if res["ok"]:
                res["checks"] = check(d, res["rom"])
                log(f"Built {res['rom'].name} ({res['rom'].stat().st_size} bytes)")
            return res
    try:
        cmds = m.build_commands(d, out, finder)
    except FileNotFoundError as e:
        res["missing"] = str(e)
        res["log"] = f"{e} was not found - install it from Tools > Retro toolchains (or the DOS tools)."
        log(res["log"])
        return res
    text = []
    for argv, cwd in cmds:
        log("> " + " ".join(Path(argv[0]).name if i == 0 else a for i, a in enumerate(argv)))
        env = dict(os.environ)
        if d.system == "nes":
            home = Path(argv[0]).parent
            env.setdefault("CC65_HOME", str(home.parent if home.name.lower() == "bin" else home))
        try:
            p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=180,
                               creationflags=NO_WINDOW, env=env)
        except (OSError, subprocess.SubprocessError) as e:
            text.append(str(e))
            log(str(e))
            res["log"] = "\n".join(text)
            return res
        chunk = (p.stdout + p.stderr).strip()
        if chunk:
            text.append(chunk)
            for line in chunk.splitlines()[-40:]:
                log("  " + line)
        if p.returncode != 0:
            res["log"] = "\n".join(text)
            log(f"*** build failed (exit code {p.returncode})")
            return res
    res["log"] = "\n".join(text)
    res["ok"] = res["rom"].is_file()
    if res["ok"]:
        try:
            res["checks"] = check(d, res["rom"])
        except Exception as e:  # noqa: BLE001 - a check must never break a build
            res["checks"] = [(False, f"check failed to run: {e}")]
        for ok, msg in res["checks"]:
            log(("  ok   " if ok else "  FAIL ") + msg)
        log(f"Built {res['rom'].name} ({res['rom'].stat().st_size} bytes)")
    return res


# ------------------------------------------------------------------ checks
def check(d: Design, rom: Path) -> list[tuple[bool, str]]:
    fn = {"a2600": check_a2600, "nes": check_nes, "gb": check_gb, "dos13h": check_dos13h}.get(d.system)
    return fn(d, Path(rom)) if fn else []


def check_a2600(d: Design, rom: Path) -> list[tuple[bool, str]]:
    from . import atari2600 as A
    from .sim6502 import Atari2600Probe
    tv = A.TV[d.settings.get("tv", "NTSC")]
    pr = Atari2600Probe(rom.read_bytes())
    frames = pr.run_frames(3)
    out = []
    if len(frames) < 2:
        return [(False, "the ROM did not produce frames (VSYNC) in the 6502 probe")]
    n = [len(f) for f in frames[1:]]
    out.append((all(x == tv["total"] for x in n), f"{n[0]} scan lines per frame (expected {tv['total']})"))
    t = A.kernel_tables(d)
    f = frames[1]
    k0 = 3 + tv["vblank"]
    bad = 0
    for y in range(tv["lines"]):
        if k0 + y >= len(f):
            bad += 1
            continue
        regs = f[k0 + y]["regs"]
        for key, reg in (("PF0T", "PF0"), ("PF1T", "PF1"), ("PF2T", "PF2"), ("BKT", "COLUBK"), ("PFCT", "COLUPF"),
                         ("G0T", "GRP0"), ("G1T", "GRP1")):
            if regs.get(reg, 0) != t[key][y]:
                bad += 1
    out.append((bad == 0, f"kernel lines match the design ({bad} differences)"))
    late = [w for line in f[k0:k0 + tv["lines"]] for w in line["writes"]
            if (w[0] == "PF1" and w[1] > 28) or (w[0] == "PF2" and w[1] > 38) or (w[0] == "WSYNC" and w[1] > 76)]
    out.append((not late, "playfield writes land before the beam reads them"))
    return out


def check_nes(d: Design, rom: Path) -> list[tuple[bool, str]]:
    from . import nes as N
    from .sim6502 import NESProbe
    pr = NESProbe(rom.read_bytes())
    got = pr.run(3)
    out = [(got == 3, f"NMI frames: {got}")]
    n = N.screens(d)
    ok_nt = all(pr.nametable(i) == N.nametable(d, i) for i in range(min(2, n)))
    ok_at = all(pr.attributes(i) == N.attribute_table(d, i) for i in range(min(2, n)))
    out.append((ok_nt, "name tables written by the loader match the design"))
    out.append((ok_at, "attribute tables match the design"))
    out.append((bytes(pr.palette[:16]) == N.palette_bytes(d)[:16], "background palettes loaded"))
    return out


def check_gb(d: Design, rom: Path) -> list[tuple[bool, str]]:
    from . import gameboy as G
    data = rom.read_bytes()
    nm = ident(d.name)
    sym = {}
    sp = rom.with_suffix(".sym")
    if sp.is_file():
        for line in sp.read_text(errors="replace").splitlines():
            mm = re.match(r"([0-9a-fA-F]+):([0-9a-fA-F]+) (\S+)", line)
            if mm:
                sym[mm.group(3)] = int(mm.group(2), 16)
    out = []
    x = 0
    for b in data[0x134:0x14D]:
        x = (x - b - 1) & 0xFF
    out.append((len(data) >= 0x150 and x == data[0x14D], "cartridge header checksum"))
    for label, want in ((f"{nm}_BgMap", G.tilemap(d, "Background")), (f"{nm}_WinMap", G.tilemap(d, "Window")),
                        (f"{nm}_Tiles", G.tiles_2bpp(d)), (f"{nm}_Sprites", G.oam_bytes(d))):
        a = sym.get(label)
        out.append((a is not None and data[a:a + len(want)] == want, f"{label} in the ROM"))
    return out


def check_dos13h(d: Design, rom: Path) -> list[tuple[bool, str]]:
    if rom.suffix.lower() != ".com":
        return []
    from . import mode13h as M
    from ....emu8086.dosexe import load_dos_file
    from ....emu8086.machine import GFX_BASE, Machine
    prog = load_dos_file(rom.read_bytes(), rom.name)
    mach = Machine()
    mach.record_history = False
    mach.load(prog)
    info = mach.run(30_000_000)
    vram = bytes(mach.mem[GFX_BASE:GFX_BASE + 64000])
    want = bytes(M.screen_after_draw(d))
    diff = sum(1 for a, b in zip(vram, want) if a != b)
    return [(info.reason == "input" and mach.video_mode == 0x13, "the .COM switched to mode 13h and waits for a key"),
            (diff == 0, f"video memory matches the design ({diff} pixels differ)")]


def dosbox_shot(exe: Path, timeout: int = 60, log=print) -> bytes | None:
    """Run a generated mode 13h .EXE with ``/SHOT`` in DOSBox-X without a window and return SCREEN.RAW (64000
    bytes) - what the program drew. None when DOSBox-X is missing or the program wrote nothing."""
    from ...dos import dosbox
    exe = Path(exe)
    shot = exe.parent / "SCREEN.RAW"
    try:
        shot.unlink()
    except OSError:
        pass
    run_cfg = dosbox.DosRun(mounts=[("C", exe.parent)], commands=[f"{exe.stem} /SHOT"], cycles="max", memsize=16,
                            sound=False, core="dynamic")
    try:
        dosbox.run_headless(run_cfg, exe.parent / "_build", timeout, name="shot.conf", log=log)
    except FileNotFoundError as e:
        log(str(e))
        return None
    try:
        data = shot.read_bytes()
    except OSError:
        return None
    return data if len(data) == 64000 else None


# ------------------------------------------------------------------ run
def run(res: dict, system: str, log=print):
    rom = res.get("rom")
    if not rom or not Path(rom).is_file():
        log("Nothing to run - build first.")
        return None
    return run_in_emulator(rom, EMU_SYSTEM.get(system, system), log=log)
