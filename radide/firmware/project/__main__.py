"""Command line of ECU projects (the project's Build and the tests use it):

    python -m radide.firmware.project build   <folder>            working copy + checksums -> output + report
    python -m radide.firmware.project verify  <folder>            check the checksum blocks of the working copy
    python -m radide.firmware.project correct <folder>            recalculate them inside the working copy
    python -m radide.firmware.project diff    <folder> [a] [b]    a / b: original, work, build or a version id
    python -m radide.firmware.project report  <folder> [out.txt|out.html]
    python -m radide.firmware.project find    <file> [--confirm other.bin]   checksum finder
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
    from ..checksum.blocks import hx, report
    from .model import EcuProject, EcuProjectError
    try:
        if cmd == "find":
            from ..checksum.finder import find
            data = Path(rest[0]).read_bytes()
            others = [Path(rest[i + 1]).read_bytes() for i, a in enumerate(rest) if a == "--confirm"]
            r = find(data, confirm_with=others)
            for c in r.candidates:
                _say(f"{c.score:6.2f}  {c.describe()}")
            for n in r.notes:
                _say("note: " + n)
            return 0
        ep = EcuProject.load(Path(rest[0] if rest else "."))
        if cmd == "build":
            res = ep.build(log=_say)
            return 1 if res.problems else 0
        if cmd == "verify":
            res = ep.verify_checksums()
            _say(report(res))
            return 0 if all(r.ok for r in res) else 1
        if cmd == "correct":
            _say(report(ep.correct_work()))
            return 0
        if cmd == "diff":
            a = rest[1] if len(rest) > 1 else "original"
            b = rest[2] if len(rest) > 2 else "work"
            d = ep.diff(a, b)
            _say(f"{d.a} -> {d.b}: {d.summary()}")
            for m in d.maps:
                _say("  map " + m.line())
            for s, e in d.ranges[:200]:
                _say(f"  {hx(s)}-{hx(e - 1)} ({e - s} bytes)")
            return 0
        if cmd == "report":
            from .report import modification_report, modification_report_html
            data = ep.work_bytes()
            res = ep.verify_checksums(data)
            out = Path(rest[1]) if len(rest) > 1 else None
            text = (modification_report_html if out is not None and out.suffix.lower() in (".html", ".htm")
                    else modification_report)(ep, data, res)
            if out is None:
                _say(text)
            else:
                out.write_text(text, encoding="utf-8")
                _say(f"Report written: {out}")
            return 0
    except (EcuProjectError, OSError, ValueError) as e:
        _say(f"*** {e}")
        return 1
    _say(f"Unknown command '{cmd}'\n\n" + __doc__.strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
