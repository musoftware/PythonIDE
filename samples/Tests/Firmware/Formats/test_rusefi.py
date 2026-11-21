"""Formats + analysis on real open-source ECU firmware: rusEFI (GPL-3.0, ARM Cortex-M4, STM32F407), downloaded
from its official GitHub releases into %TEMP%/radide-fw-data (skipped when offline).

    python samples/Tests/Firmware/Formats/test_rusefi.py
"""
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from download_rusefi import ensure  # noqa: E402
from radide.firmware.formats import dumps, load, load_bytes  # noqa: E402
from radide.firmware.analysis import disasm  # noqa: E402
from radide.firmware.analysis.report import analyze  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:500]}]"), flush=True)
    return bool(cond)


def main() -> int:
    folder = ensure()
    if folder is None:
        print("SKIP: rusEFI firmware not available (offline)")
        return 0
    binp, srecp = folder / "rusefi.bin", folder / "rusefi_update.srec"
    # ---- raw image: CPU + base
    mm = load(binp)
    t = time.time()
    res = analyze(mm)
    dt = time.time() - t
    best = res.detection.best
    check("rusEFI .bin: ARM Cortex-M detected", best is not None and best.arch == "arm-thumb" and
          best.confidence >= 0.8, [(g.arch, g.confidence) for g in res.detection.arches[:3]])
    check("rusEFI .bin: Cortex-M vector table found", "arm-thumb" in res.detection.vectors)
    b = res.detection.base
    check("rusEFI .bin: base 0x08000000 (STM32 flash)", b is not None and b.base == 0x08000000 and b.confidence >= 0.8,
          [(hex(x.base), x.confidence, x.reason) for x in res.detection.bases[:3]])
    check(f"rusEFI .bin: analysis time {dt:.1f} s < 20 s", dt < 20)
    kinds = {r.kind for r in res.regions}
    check("rusEFI .bin: code regions", "code" in kinds, kinds)
    texts = [s.text for s in res.strings]
    check("rusEFI .bin: version string found", any("rusEFI" in x for x in texts), texts[:20])
    # ---- S-record: application at 0x08008000
    sm = load(srecp)
    check("rusEFI .srec: parsed, one segment at 0x08008000", sm.min_address == 0x08008000 and len(sm.segments) >= 1,
          sm.describe())
    check("rusEFI .srec: start address", sm.start == 0x08008000, sm.start)
    raw = mm.to_flat()
    flat = sm.to_flat()
    same = sum(1 for i in range(0, len(flat), 64) if raw[0x8000 + i:0x8000 + i + 64] == flat[i:i + 64])
    check("rusEFI .srec matches .bin at offset 0x8000 (>= 99.9% of 64-byte blocks)",
          same >= (len(flat) // 64) * 0.999, f"{same} / {len(flat) // 64}")
    sres = analyze(sm)
    check("rusEFI .srec: Thumb + base from the records", sres.arch == "arm-thumb" and sres.base == 0x08008000,
          (sres.arch, hex(sres.base)))
    # ---- container round trips
    for fmt in ("ihex", "elf", "srec"):
        back = load_bytes(dumps(sm, fmt))
        check(f"rusEFI .srec -> {fmt} -> memory map identical", back == sm and back.start == sm.start)
    # ---- disassembly at the reset handler + references
    mmb = mm.relocate(0x08000000)
    reset = res.detection.vectors["arm-thumb"][0]["reset"]
    lines = disasm.disassemble(mmb, "arm-thumb", reset, 0x40)
    check("rusEFI: reset handler disassembles", len(lines) >= 10 and
          sum(1 for ln in lines if not ln.mnemonic.startswith(".")) >= len(lines) - 1,
          [f"{ln.mnemonic} {ln.ops}" for ln in lines[:8]])
    check("rusEFI: literal-pool references resolved", any(ln.refs for ln in lines))
    t = time.time()
    idx = disasm.build_xrefs(mmb, "arm-thumb", disasm.code_ranges(mmb, res.regions, 0x08000000))
    check(f"rusEFI: cross-reference index ({idx.instructions:,} insns, {time.time() - t:.1f} s)",
          idx.instructions > 50000 and len(idx.refs) > 5000)
    called = [a for a, refs in idx.refs.items() if sum(1 for _s, k in refs if k == "call") >= 5]
    check("rusEFI: functions called from 5+ places", len(called) > 50, len(called))
    # strings are used by code through literal pools (pointer = base + offset)
    ss = [s for s in res.strings if len(s.text) >= 8 and s.encoding == "ascii"]
    used = [s for s in ss if idx.to(0x08000000 + s.offset)]
    check(f"rusEFI: strings referenced by code ({len(used)} of {len(ss)})", len(used) >= len(ss) * 0.15)
    check("rusEFI: a 'rusEFI' message string referenced by code",
          any(idx.to(0x08000000 + s.offset) for s in res.strings if "rusEFI" in s.text))
    # ---- report text
    txt = res.text()
    check("rusEFI: report mentions Cortex-M and 0x08000000", "Cortex-M" in txt and "0x08000000" in txt, txt[:500])
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "report.txt").write_text(txt, encoding="utf-8")
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
