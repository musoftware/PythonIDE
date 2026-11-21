"""Build a retro project and run the ROM: ``python -m radide.retro.dev.run <project folder>`` (no Qt in here).

Running goes through the emulator slice: ``radide.retro.emu.run_rom(path, system)`` (Stella for the 2600, Mesen
for the NES, mGBA for the Game Boy, VICE for the C64 - downloaded only on request with Tools > Retro >
Emulators). The ZX Spectrum (not in that list) uses the program named in the RADIDE_ZX_EMULATOR environment
variable, a Fuse / ZEsarUX found in PATH, or the program Windows associates with .tap files.
The process waits for the emulator so the IDE's Stop button ends both.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .build import Builder
from .systems import SYSTEMS


def run_rom(path, system_id: str, log=print):
    """Start *path* in an emulator for *system_id* (our ids: atari2600 / nes / gameboy / c64 / zx).
    Returns an object with ``alive()`` / ``stop()`` / ``wait()`` or None when nothing could be started."""
    sysd = SYSTEMS[system_id]
    if sysd.emu_system:
        try:
            from ..emu import run_rom as emu_run
        except Exception as e:  # noqa: BLE001 - the emulator slice is optional
            log(f"The retro emulator support is not available ({e}).")
            return None
        try:
            return emu_run(str(path), system=sysd.emu_system)
        except Exception as e:  # noqa: BLE001 - EmuError: no emulator installed ...
            log(f"Could not start an emulator for {sysd.title}: {e}")
            log("Install one with Tools > Retro > Emulators... (Stella, Mesen, mGBA, VICE), then press F5 again.")
            return None
    exe = os.environ.get("RADIDE_ZX_EMULATOR", "") or shutil.which("fuse") or shutil.which("zesarux") or \
        shutil.which("fuse-sdl") or ""
    if exe:
        return _Proc(subprocess.Popen([exe, str(path)], cwd=str(Path(path).parent)))
    if os.name == "nt":
        try:
            os.startfile(str(path))                       # type: ignore[attr-defined]
            log(f"Opened {Path(path).name} with the program associated with .tap files.")
            return None
        except OSError as e:
            log(f"No ZX Spectrum emulator found ({e}). Set RADIDE_ZX_EMULATOR to Fuse / ZEsarUX / Spectaculator.")
            return None
    log("No ZX Spectrum emulator found: install Fuse (fuse in PATH) or set RADIDE_ZX_EMULATOR.")
    return None


def _as_popen(proc):
    from types import SimpleNamespace
    return SimpleNamespace(popen=getattr(proc, "p", None))


class _Proc:
    def __init__(self, p: subprocess.Popen):
        self.p = p

    def alive(self) -> bool:
        return self.p.poll() is None

    def wait(self, timeout=None):
        return self.p.wait(timeout)

    def stop(self, timeout: float = 5.0) -> None:
        if self.alive():
            self.p.terminate()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m radide.retro.dev.run <project folder> [--build-only]")
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    b = Builder(Path(argv[0]), log=lambda t: print(t, flush=True))
    ok = b.build()
    errs = sum(d.severity == "Error" for d in b.diags)
    warns = sum(d.severity == "Warning" for d in b.diags)
    print(f"{'Build succeeded' if ok else 'Build failed'}: {b.out_path.name if ok else ''} "
          f"({errs} errors, {warns} warnings)", flush=True)
    if not ok:
        return 1
    if "--build-only" in argv:
        return 0
    proc = run_rom(b.out_path, b.system.id, log=lambda t: print(t, flush=True))
    if proc is None:
        return 0
    print(f"Running {b.out_path.name} ({b.system.title}) - close the emulator or press Stop to end.", flush=True)
    try:        # the IDE's Stop kills this runner: a job object closes the emulator with it (Windows)
        from ..emu.launch import tie_to_this_process
        tie_to_this_process(proc if getattr(proc, "popen", None) is not None else _as_popen(proc))
    except Exception:  # noqa: BLE001 - best effort
        pass
    try:
        while proc.alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.stop()
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
