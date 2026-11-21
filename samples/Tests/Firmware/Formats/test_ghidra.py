"""Analyze in Ghidra (headless) on synthetic images - skipped when Ghidra / a JDK is not installed.

    python samples/Tests/Firmware/Formats/test_ghidra.py [--rusefi]

Thumb (Cortex-M, base 0x08000000), PowerPC (base 0x00800000), TriCore (0x80000000) and an ELF built from the
Thumb image; --rusefi also runs the real rusEFI image (a few minutes).
"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from radide.firmware.analysis import ghidra  # noqa: E402
from radide.firmware.analysis.report import analyze  # noqa: E402
from radide.firmware.analysis.synth import make_image  # noqa: E402
from radide.firmware.formats import MemoryMap, Symbol, elf, load  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def run_synth(arch: str, base: int, work: Path):
    im = make_image(arch, base=base, seed=4, n_funcs=120)
    p = work / f"{arch}.bin"
    p.write_bytes(im.bytes())
    res = analyze(load(p))
    check(f"{arch}: detected before Ghidra", res.arch == arch and res.base == base, (res.arch, hex(res.base)))
    r = ghidra.analyze(p, work / arch, arch, base, True, res.entry_points() or [im.entry], max_decompile=15,
                       timeout=900)
    check(f"{arch}: Ghidra ran ({r.language}, {r.seconds:.0f} s)", not r.error, r.error + r.log[-600:])
    addrs = {f.address for f in r.functions}
    check(f"{arch}: functions at the right addresses (base 0x{base:X})", im.entry in addrs and
          all(base <= a < base + im.size for a in addrs), (hex(im.entry), sorted(hex(a) for a in addrs)[:8]))
    check(f"{arch}: decompiled C", len(r.decompiled) >= 1 and "{" in r.c_text(), r.c_text()[:300])
    return r


def main() -> int:
    ok, info = ghidra.available()
    if not ok:
        print("SKIP:", info)
        return 0
    print("Ghidra:", info)
    with tempfile.TemporaryDirectory(prefix="radide-ghidra-") as d:
        work = Path(d)
        run_synth("arm-thumb", 0x08000000, work)
        run_synth("ppc", 0x00800000, work)
        run_synth("tricore", 0x80000000, work)
        # ELF: Ghidra's own loader takes the addresses and symbols from the file
        im = make_image("arm-thumb", seed=4, n_funcs=120)
        mm = MemoryMap.from_bytes(im.bytes(), im.base, ".text")
        mm.segments[0].flags = "rx"
        mm.start = im.entry | 1
        mm.symbols = [Symbol("reset_handler", im.entry | 1, 16, "func")]
        ep = work / "thumb.elf"
        ep.write_bytes(elf.dumps(mm, machine=40, flags=0x05000000))
        r = ghidra.analyze(ep, work / "elf", "arm-thumb", None, False, [], max_decompile=5, timeout=900)
        check(f"ELF: Ghidra ELF loader ({r.language})", not r.error and any(f.name == "reset_handler"
                                                                              for f in r.functions),
              r.error + str([f.name for f in r.functions[:10]]))
        if "--rusefi" in sys.argv:
            from download_rusefi import ensure
            folder = ensure()
            if folder is None:
                print("SKIP rusEFI: offline")
            else:
                res = analyze(load(folder / "rusefi.bin"))
                r = ghidra.analyze(folder / "rusefi.bin", work / "rusefi", res.arch, res.base, True,
                                   res.entry_points(), max_decompile=10, timeout=1800)
                check(f"rusEFI: Ghidra ({r.seconds:.0f} s, {len(r.functions)} functions)",
                      not r.error and len(r.functions) > 200, r.error)
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
