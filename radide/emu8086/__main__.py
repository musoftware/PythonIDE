"""python -m radide.emu8086 main.asm [--keys TEXT] [--screen] [--listing] [--max-steps N] [--lang ar]

Assembles and runs an 8086 program headless; prints the program output (or the final text screen).
Exit code: the program's exit code, 2 for assembly errors, 3 when it stopped for another reason.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m radide.emu8086")
    ap.add_argument("file")
    ap.add_argument("--keys", default="", help="keyboard input (\\n = Enter)")
    ap.add_argument("--screen", action="store_true", help="print the final 80x25 screen instead of the output")
    ap.add_argument("--listing", action="store_true", help="print the assembly listing")
    ap.add_argument("--max-steps", type=int, default=5_000_000)
    ap.add_argument("--lang", default="en")
    a = ap.parse_args(argv)
    from .assembler import assemble
    from .machine import Machine
    path = Path(a.file)
    prog = assemble(path.read_text(encoding="utf-8", errors="replace"), str(path))
    for d in prog.warnings:
        print(f"{path.name}({d.line}): warning: {d.text(a.lang)}", file=sys.stderr)
    if not prog.ok:
        for d in prog.errors:
            print(f"{Path(d.file).name}({d.line}): error: {d.text(a.lang)}", file=sys.stderr)
        return 2
    if a.listing:
        for f, line, seg, off, data, src in prog.listing:
            print(f"{seg:04X}:{off:04X}  {data[:8].hex(' ').upper():<24} {src}")
    m = Machine()
    m.lang = a.lang
    m.record_history = False
    m.load(prog)
    m.feed_keys(a.keys.replace("\\n", "\r"))
    info = m.run(a.max_steps)
    sys.stdout.write(m.screen_text() + "\n" if a.screen else m.output)
    for note in m.log:
        print(note, file=sys.stderr)
    if info.reason == "exit":
        return m.exit_code & 0xFF
    print(f"\n[{info.reason}] {info.message}", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
