"""Command line of the ROM workbench (used by the ROM Hacking project's Build / Run and by tests):

    python -m radide.retro.rom build  <project folder>
    python -m radide.retro.rom run    <project folder>         (build, then start the emulator)
    python -m radide.retro.rom info   <file>
    python -m radide.retro.rom apply  <rom> <patch> <output>
    python -m radide.retro.rom create <original> <modified> <patch.ips|.bps|.ups>
    python -m radide.retro.rom fixsum <file> [<output>]
"""
from __future__ import annotations

import sys
from pathlib import Path


def _say(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        _say(__doc__.strip())
        return 0
    cmd, rest = args[0], args[1:]
    from .patches import PatchError
    try:
        if cmd in ("build", "run"):
            from .project import RomProject
            rp = RomProject.load(Path(rest[0] if rest else "."))
            out = rp.build(log=_say)
            if cmd == "run":
                from .emulink import RunError, run_rom
                try:
                    run_rom(out, rp.system or None)
                    _say(f"Started the emulator for {out.name}")
                except RunError as e:
                    _say(f"*** Cannot start an emulator: {e}")
                    _say("    (Tools > Retro > Emulators downloads one; the patched ROM is ready in build/)")
                    return 2
            return 0
        if cmd == "info":
            from .detect import detect
            p = Path(rest[0])
            info = detect(p.read_bytes(), p.name)
            for k, v in info.rows:
                _say(f"{k}: {v}")
            for w in info.warnings:
                _say(f"warning: {w}")
            for row in info.listing[:200]:
                _say("  " + " | ".join(row))
            return 0
        if cmd == "apply":
            from .patches import apply_patch
            rom, patch, out = (Path(x) for x in rest[:3])
            if out.resolve() == rom.resolve():
                _say("*** The output must not be the original ROM")
                return 1
            out.write_bytes(apply_patch(rom.read_bytes(), patch.read_bytes()))
            _say(f"Wrote {out}")
            return 0
        if cmd == "create":
            from .patches import create_patch
            a, b, out = (Path(x) for x in rest[:3])
            out.write_bytes(create_patch(a.read_bytes(), b.read_bytes(), out.suffix))
            _say(f"Wrote {out} ({out.stat().st_size:,} bytes)")
            return 0
        if cmd == "fixsum":
            from .detect import fix_checksum
            p = Path(rest[0])
            out = Path(rest[1]) if len(rest) > 1 else p
            data, msg = fix_checksum(p.read_bytes(), p.name)
            out.write_bytes(data)
            _say(msg)
            return 0
    except (PatchError, ValueError, OSError, IndexError) as e:
        _say(f"*** {e}")
        return 1
    _say(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
