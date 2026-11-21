"""Command line of the firmware analysis tools (used by the Firmware Analysis project's Build / Run and tests).

    python -m radide.firmware.analysis info FILE [--base 0x8000000] [--arch arm-thumb]
    python -m radide.firmware.analysis convert IN OUT [--fill FF] [--base ADDR] [--format ihex|srec|elf|raw]
    python -m radide.firmware.analysis deinterleave IN OUT_EVEN OUT_ODD [--width 1]
    python -m radide.firmware.analysis interleave EVEN ODD OUT [--width 1]
    python -m radide.firmware.analysis byteswap IN OUT [--width 2|4] [--words]
    python -m radide.firmware.analysis split IN OUTPREFIX --sizes 0x80000,0  /  --parts 2
    python -m radide.firmware.analysis merge OUT IN1[@ADDR] IN2[@ADDR] ... [--fill FF]
    python -m radide.firmware.analysis disasm FILE --arch ARCH [--base ADDR] [--start ADDR] [--length N]
    python -m radide.firmware.analysis xrefs FILE ADDRESS --arch ARCH [--base ADDR]
    python -m radide.firmware.analysis ghidra FILE [--arch ARCH] [--base ADDR] [--out DIR]
    python -m radide.firmware.analysis synth ARCH OUT [--base ADDR] [--seed N]
    python -m radide.firmware.analysis build PROJECT_FOLDER       (Firmware Analysis project: verify + report)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _int(s: str) -> int:
    return int(s, 0)


def _load(path, base):
    from ..formats import load
    return load(path, base=base or 0)


def cmd_info(a) -> int:
    from .report import analyze
    mm = _load(a.file, a.base)
    print(analyze(mm, arch=a.arch or "").text())
    return 0


def cmd_convert(a) -> int:
    from ..formats import save
    mm = _load(a.input, a.base)
    p = save(mm, a.output, a.format or "", fill=a.fill)
    print(f"Wrote {p} ({p.stat().st_size:,} bytes)")
    return 0


def cmd_deinterleave(a) -> int:
    from ..formats.split import deinterleave
    data = Path(a.input).read_bytes()
    even, odd = deinterleave(data, 2, a.width)
    Path(a.even).write_bytes(even)
    Path(a.odd).write_bytes(odd)
    print(f"Wrote {a.even} and {a.odd} ({len(even):,} bytes each)")
    return 0


def cmd_interleave(a) -> int:
    from ..formats.split import interleave
    out = interleave([Path(a.even).read_bytes(), Path(a.odd).read_bytes()], a.width)
    Path(a.output).write_bytes(out)
    print(f"Wrote {a.output} ({len(out):,} bytes)")
    return 0


def cmd_byteswap(a) -> int:
    from ..formats.split import byteswap, wordswap
    data = Path(a.input).read_bytes()
    out = wordswap(data) if a.words else byteswap(data, a.width)
    Path(a.output).write_bytes(out)
    print(f"Wrote {a.output}")
    return 0


def cmd_split(a) -> int:
    from ..formats.split import split_equal, split_sizes
    data = Path(a.input).read_bytes()
    parts = split_equal(data, a.parts) if a.parts else split_sizes(data, [int(x, 0) for x in a.sizes.split(",")])
    for i, p in enumerate(parts):
        out = Path(f"{a.prefix}_{i}.bin")
        out.write_bytes(p)
        print(f"Wrote {out} ({len(p):,} bytes)")
    return 0


def cmd_merge(a) -> int:
    from ..formats import save
    from ..formats.split import merge_maps, overlaps
    maps = []
    for spec in a.inputs:
        path, _at, addr = spec.partition("@")
        mm = _load(path, int(addr, 0) if addr else 0)
        maps.append((mm, 0))
    ov = overlaps(maps)
    if ov:
        print("warning: overlapping ranges " + ", ".join(f"0x{x:X}-0x{y:X}" for x, y in ov[:5]), file=sys.stderr)
    m = merge_maps(maps)
    p = save(m, a.output, fill=a.fill)
    print(f"Wrote {p}: " + "; ".join(m.describe()))
    return 0


def cmd_disasm(a) -> int:
    from .disasm import listing, pcode_listing
    mm = _load(a.file, a.base)
    start = a.start if a.start is not None else mm.min_address
    if a.pcode:
        print(pcode_listing(mm, a.arch, start, max(1, a.length // 4)))
    else:
        print(listing(mm, a.arch, start, a.length))
    return 0


def cmd_xrefs(a) -> int:
    from .disasm import build_xrefs
    mm = _load(a.file, a.base)
    idx = build_xrefs(mm, a.arch)
    hits = idx.to(a.address, a.size)
    for src, kind in hits:
        print(f"0x{src:08X}  {kind}")
    print(f"{len(hits)} reference(s) to 0x{a.address:X} ({idx.instructions:,} instructions scanned)")
    return 0


def cmd_ghidra(a) -> int:
    from . import ghidra
    from .report import analyze
    mm = _load(a.file, a.base)
    res = analyze(mm, arch=a.arch or "")
    arch = a.arch or res.arch
    base = a.base if a.base is not None else res.base
    out = Path(a.out or Path(a.file).with_suffix(".ghidra"))
    out.mkdir(parents=True, exist_ok=True)
    raw = mm.meta.get("format") != "elf"
    binary = Path(a.file)
    if raw and mm.meta.get("format") != "raw":
        binary = out / "image.bin"
        binary.write_bytes(mm.to_flat())
        base = mm.min_address
    r = ghidra.analyze(binary, out, arch, base, raw, res.entry_points(), max_decompile=a.max, progress=print)
    if r.error:
        print("error:", r.error, file=sys.stderr)
        return 1
    (out / "decompiled.c").write_text(r.c_text(), encoding="utf-8")
    print(f"{len(r.functions)} functions, {len(r.decompiled)} decompiled ({r.language}, {r.seconds:.0f} s) "
          f"-> {out / 'decompiled.c'}")
    return 0


def cmd_synth(a) -> int:
    from .synth import make_image
    im = make_image(a.arch, base=a.base, seed=a.seed)
    Path(a.output).write_bytes(im.bytes())
    print(f"Wrote {a.output}: {a.arch}, base 0x{im.base:X}, {len(im.functions)} functions, {len(im.tables)} tables")
    return 0


def cmd_build(a) -> int:
    from .project import FirmwareProject
    folder = Path(a.folder)
    fp = FirmwareProject.load(folder)
    ok, msg = fp.verify()
    print(msg)
    if not ok:
        return 1
    res = fp.refresh()
    fp.save()
    out = folder / "build" / "analysis.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(res.text() + "\n", encoding="utf-8")
    print(res.text())
    print(f"\nReport written to {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m radide.firmware.analysis", description="Firmware analysis tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p.add_argument("--base", type=_int)
    p.add_argument("--arch", default="")
    p.set_defaults(fn=cmd_info)
    p = sub.add_parser("convert")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--fill", type=lambda s: int(s, 16), default=0xFF)
    p.add_argument("--base", type=_int)
    p.add_argument("--format", default="")
    p.set_defaults(fn=cmd_convert)
    p = sub.add_parser("deinterleave")
    p.add_argument("input")
    p.add_argument("even")
    p.add_argument("odd")
    p.add_argument("--width", type=int, default=1)
    p.set_defaults(fn=cmd_deinterleave)
    p = sub.add_parser("interleave")
    p.add_argument("even")
    p.add_argument("odd")
    p.add_argument("output")
    p.add_argument("--width", type=int, default=1)
    p.set_defaults(fn=cmd_interleave)
    p = sub.add_parser("byteswap")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--width", type=int, default=2)
    p.add_argument("--words", action="store_true")
    p.set_defaults(fn=cmd_byteswap)
    p = sub.add_parser("split")
    p.add_argument("input")
    p.add_argument("prefix")
    p.add_argument("--sizes", default="")
    p.add_argument("--parts", type=int, default=0)
    p.set_defaults(fn=cmd_split)
    p = sub.add_parser("merge")
    p.add_argument("output")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--fill", type=lambda s: int(s, 16), default=0xFF)
    p.set_defaults(fn=cmd_merge)
    p = sub.add_parser("disasm")
    p.add_argument("file")
    p.add_argument("--arch", required=True)
    p.add_argument("--base", type=_int)
    p.add_argument("--start", type=_int)
    p.add_argument("--length", type=_int, default=0x100)
    p.add_argument("--pcode", action="store_true", help="p-code under every instruction (SLEIGH CPUs)")
    p.set_defaults(fn=cmd_disasm)
    p = sub.add_parser("xrefs")
    p.add_argument("file")
    p.add_argument("address", type=_int)
    p.add_argument("--arch", required=True)
    p.add_argument("--base", type=_int)
    p.add_argument("--size", type=_int, default=1)
    p.set_defaults(fn=cmd_xrefs)
    p = sub.add_parser("ghidra")
    p.add_argument("file")
    p.add_argument("--arch", default="")
    p.add_argument("--base", type=_int)
    p.add_argument("--out", default="")
    p.add_argument("--max", type=int, default=200)
    p.set_defaults(fn=cmd_ghidra)
    p = sub.add_parser("synth")
    p.add_argument("arch")
    p.add_argument("output")
    p.add_argument("--base", type=_int)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(fn=cmd_synth)
    p = sub.add_parser("build")
    p.add_argument("folder")
    p.set_defaults(fn=cmd_build)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
