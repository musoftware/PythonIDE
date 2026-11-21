"""Firmware formats + analysis core tests (no Qt, no network): synthetic images built by RAD IDE only.

    python samples/Tests/Firmware/Formats/test_formats_core.py

Covers: Intel HEX / S-record / ELF / raw round trips (gaps, start address, 16/24/32-bit S-records, extended
segment / linear HEX, ELF32/64 LE/BE with symbols), split / interleave / byte swap / cut / merge, entropy regions,
fill areas, strings + identification tags, CPU + base address detection for 10 CPU families (with and without
vector tables, at other bases), Capstone listings + cross references to calibration tables, the CLI and the
Firmware Analysis project model (read-only original + SHA-256).
"""
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.firmware.formats import MemoryMap, Symbol, detect_format, dumps, load, load_bytes, save  # noqa: E402
from radide.firmware.formats import elf, ihex, split, srec  # noqa: E402
from radide.firmware.analysis import arch, disasm, entropy, fill, strings  # noqa: E402
from radide.firmware.analysis.synth import ARCHES, make_image  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:400]}]"), flush=True)
    return bool(cond)


def sample_map() -> MemoryMap:
    rnd = random.Random(7)
    m = MemoryMap()
    m.add(0x08000000, bytes(rnd.randrange(256) for _ in range(5000)), "flash")
    m.add(0x08010000, bytes(rnd.randrange(256) for _ in range(777)), "cal")       # gap before
    m.add(0x0801FFF0, bytes(range(40)), "cross64k")                               # crosses a 64 KB boundary
    m.start = 0x08000101
    return m


def test_containers(tmp: Path):
    m = sample_map()
    check("memmap: 3 segments, 2 gaps", len(m.segments) == 3 and len(m.gaps()) == 2, m.describe())
    for fmt in ("ihex", "srec", "elf"):
        blob = dumps(m, fmt)
        m2 = load_bytes(blob)
        check(f"{fmt}: detect_format", detect_format(blob[:4096]) == fmt)
        check(f"{fmt}: round trip bytes + addresses", m2 == m, m2.describe())
        check(f"{fmt}: start address kept", m2.start == m.start, m2.start)
    # raw: flat with fill
    flat = dumps(m, "raw", fill=0xEE)
    check("raw: flat size = span", len(flat) == m.span())
    check("raw: gap filled", flat[5000] == 0xEE and flat[0x10000 - 1] == 0xEE)
    # files + extensions
    for ext, fmt in ((".hex", "ihex"), (".s37", "srec"), (".elf", "elf"), (".bin", "raw")):
        p = save(m, tmp / f"img{ext}")
        m3 = load(p, base=0x08000000 if fmt == "raw" else 0)
        same = (m3 == m) if fmt != "raw" else (m3.to_flat() == m.to_flat())
        check(f"save/load {ext}", same)
    # S-record address widths
    small = MemoryMap.from_bytes(b"\x01\x02\x03" * 100, 0x1000)
    t = srec.dumps(small)
    check("srec: S19 for 16-bit addresses", "\nS1" in t and "\nS9" in t, t[:80])
    t = srec.dumps(MemoryMap.from_bytes(b"\x00" * 64, 0x123456))
    check("srec: S28 for 24-bit addresses", "\nS2" in t and "\nS8" in t)
    t = srec.dumps(m)
    check("srec: S37 for 32-bit addresses", "\nS3" in t and "\nS7" in t and "\nS5" in t)
    check("srec: S0 header kept", srec.parse(srec.dumps(small, header="RADIDE")).header == "RADIDE")
    # Intel HEX extended segment address (02) + start segment (03)
    rec = [":020000021000EC", ":0400000001020304F2", ":0400000312345678E5", ":00000001FF"]
    hm = ihex.parse("\n".join(rec))
    check("ihex: type 02 segment address", hm.segments[0].address == 0x10000 and bytes(hm.segments[0].data) == b"\x01\x02\x03\x04",
          hm.describe())
    check("ihex: type 03 start CS:IP", hm.start == (0x1234 << 4) + 0x5678 and "start_cs_ip" in hm.meta)
    check("ihex: 03 written back", ":0400000312345678E5" in ihex.dumps(hm))
    bad = rec[1][:-2] + "00"
    try:
        ihex.parse(rec[0] + "\n" + bad)
        check("ihex: checksum error detected", False)
    except ValueError:
        check("ihex: checksum error detected", True)
    try:
        srec.parse("S1130000" + "00" * 16 + "00")
        check("srec: checksum error detected", False)
    except ValueError:
        check("srec: checksum error detected", True)
    # ELF variants
    for is64 in (False, True):
        for be in (False, True):
            mm = sample_map()
            mm.symbols = [Symbol("reset_handler", 0x08000100, 32, "func"), Symbol("cal_table", 0x08010000, 64, "object")]
            blob = elf.dumps(mm, machine=20 if be else 40, big_endian=be, is64=is64)
            back = elf.parse(blob)
            names = {s.name for s in back.symbols}
            check(f"elf{64 if is64 else 32}{'be' if be else 'le'}: segments + symbols", back == mm and
                  {"reset_handler", "cal_table"} <= names and back.meta["arch"] == ("ppc" if be else "arm"),
                  (back.describe(), names))
    # overlap: later data wins, touching segments merge
    m4 = MemoryMap()
    m4.add(0x100, b"\xAA" * 16)
    m4.add(0x108, b"\xBB" * 16)
    m4.add(0x118, b"\xCC" * 8)
    check("memmap: overlap + touching merge", len(m4.segments) == 1 and m4.read(0x107, 2) == b"\xAA\xBB" and
          m4.read(0x118, 1) == b"\xCC", m4.describe())
    try:
        m4.read(0x50, 4)
        check("memmap: read in gap raises", False)
    except KeyError:
        check("memmap: read in gap raises", True)
    check("memmap: relocate", m4.relocate(0x1000).min_address == 0x1100)


def test_split(tmp: Path):
    rnd = random.Random(3)
    data = bytes(rnd.randrange(256) for _ in range(4096))
    even, odd = split.deinterleave(data)
    check("deinterleave even/odd", even == data[0::2] and odd == data[1::2])
    check("interleave inverse", split.interleave([even, odd]) == data)
    e16, o16 = split.deinterleave(data, 2, 2)
    check("deinterleave 16-bit words", e16[:4] == data[0:2] + data[4:6] and split.interleave([e16, o16], 2) == data)
    q = split.deinterleave(data, 4, 1)
    check("4-way interleave round trip", split.interleave(q) == data)
    check("byteswap 16", split.byteswap(b"\x01\x02\x03\x04") == b"\x02\x01\x04\x03")
    check("byteswap 32", split.byteswap(b"\x01\x02\x03\x04", 4) == b"\x04\x03\x02\x01")
    check("byteswap twice = identity", split.byteswap(split.byteswap(data, 4), 4) == data)
    check("wordswap", split.wordswap(b"\x01\x02\x03\x04") == b"\x03\x04\x01\x02")
    parts = split.split_sizes(data, [1024, 0])
    check("split sizes + concat", len(parts) == 2 and len(parts[0]) == 1024 and split.concat(parts) == data)
    check("split equal", split.split_equal(data, 4)[3] == data[3072:])
    # internal + external flash merge with a gap
    internal = MemoryMap.from_bytes(data[:2048], 0x80000000)
    external = MemoryMap.from_bytes(data[2048:], 0x80100000)
    merged = split.merge_maps([(internal, 0), (external, 0)])
    check("merge maps: gap kept", len(merged.segments) == 2 and merged.gaps() == [(0x80000800, 0x80100000)])
    check("overlaps none", split.overlaps([(internal, 0), (external, 0)]) == [])
    check("overlaps found", split.overlaps([(internal, 0), (internal, 0x100)]) != [])
    p = save(merged, tmp / "merged.s37")
    check("merged image saved as S37 round trip", load(p) == merged)


def test_analysis():
    im = make_image("ppc")
    data = im.bytes()
    prof = entropy.entropy_profile(data, 512)
    check("entropy profile length", len(prof) == len(data) // 512)
    check("entropy: fill block = 0", min(prof) < 0.01)
    regs = entropy.classify(data, 512, prof)
    kinds = entropy.summary(regs)
    check("entropy classes: empty + code + calibration", {"empty", "code", "calibration"} <= set(kinds), kinds)
    code = [r for r in regs if r.kind == "code"]
    check("code region covers the functions", any(r.start <= im.functions[10] - im.base < r.end for r in code),
          [(hex(r.start), hex(r.end)) for r in code[:4]])
    cal = [r for r in regs if r.kind == "calibration"]
    tab = next(t for t in im.tables if t.kind == "map")
    check("calibration region covers a map", any(r.start <= tab.address - im.base < r.end for r in cal),
          ([(hex(r.start), hex(r.end)) for r in cal[:4]], hex(tab.address)))
    rnd = os.urandom(8192)
    check("random block classed compressed/encrypted-like", entropy.classify_block(rnd) == "random")
    fa = fill.find_fill(data)
    check("fill areas: 0xFF tail found", any(f.pattern == b"\xff" and f.size > 4096 for f in fa), [f.label for f in fa])
    pat = b"\x00" * 300 + b"\xde\xad" * 400 + b"\x12" * 10
    fp = fill.find_fill(pat)
    check("fill areas: 2-byte pattern", any(f.pattern == b"\xde\xad" for f in fp), [(f.label, f.size) for f in fp])
    ss = strings.find_strings(data + "UNICODE TEXT".encode("utf-16le") + b"\0\0")
    texts = {s.text for s in ss}
    check("strings: ASCII", "RADIDE SYNTHETIC ECU" in texts)
    check("strings: UTF-16LE", any(s.encoding == "utf-16le" and "UNICODE TEXT" in s.text for s in ss))
    ids = {s.text: s.tags for s in strings.identification(ss)}
    check("identification: part-number-like", "part-number-like" in ids.get("X 123 456 78 90", ()), ids)
    check("identification: number-like", "number-like" in ids.get("SW 1234567890", ()), ids)
    check("identification: version-like", "version-like" in ids.get("V1.02.003", ()), ids)
    check("identification: date-like", "date-like" in ids.get("BUILD 2026-11-21", ()), ids)


ALT_BASE = {"arm-thumb": 0x00400000, "ppc": 0x00800000, "ppc-vle": 0x01000000, "tricore": 0xA0000000,
            "sh2": 0x00020000, "m68k": 0x00040000}


def test_detection():
    for a in ARCHES:
        for variant in ("default", "no-vectors", "other-base"):
            if variant == "other-base" and a not in ALT_BASE:
                continue
            im = make_image(a, base=ALT_BASE[a] if variant == "other-base" else None, seed=11)
            data = bytearray(im.bytes())
            if variant == "no-vectors":
                data[:0x100] = b"\xff" * 0x100
            d = arch.detect(bytes(data))
            ok_cpu = d.best is not None and d.best.arch == a
            check(f"detect {a} ({variant}): CPU", ok_cpu and d.best.confidence >= 0.5,
                  [(g.arch, g.confidence) for g in d.arches[:3]])
            check(f"detect {a} ({variant}): base 0x{im.base:X}", d.base is not None and d.base.base == im.base and
                  d.base.confidence >= 0.5, [(hex(b.base), b.confidence) for b in d.bases[:3]])
    rnd = random.Random(5)
    noise = bytes(rnd.randrange(256) for _ in range(65536))
    g = arch.guess_arch(noise)
    check("random bytes: no confident CPU", not g or g[0].confidence < 0.5, [(x.arch, x.confidence) for x in g[:3]])
    flat = bytes([0xFF]) * 65536
    check("erased flash: no CPU", arch.guess_arch(flat) == [] or arch.guess_arch(flat)[0].confidence < 0.3)


def test_disassembly():
    for a, dis in (("arm-thumb", "arm-thumb"), ("ppc", "ppc"), ("tricore", "tricore"), ("sh2", "sh2"),
                   ("m68k", "m68k"), ("hc12", "hc12")):
        im = make_image(a, seed=2)
        mm = MemoryMap.from_bytes(im.bytes(), im.base)
        f = im.functions[5]
        text = disasm.listing(mm, dis, f, 0x60)
        lines = disasm.disassemble(mm, dis, f, 0x60)
        valid = sum(1 for ln in lines if not ln.mnemonic.startswith("."))
        check(f"listing {a}: decodes", valid >= len(lines) * 0.9 and len(lines) >= 8, text[:300])
        first = {"arm-thumb": "push", "ppc": "stwu", "sh2": "mov.l", "m68k": "link", "hc12": "pshx"}.get(a)
        if first:
            check(f"listing {a}: prologue '{first}'", lines[0].mnemonic.startswith(first), lines[0].mnemonic)
        start = im.base + 0x400 if a in ("sh2", "m68k") else im.base + 0x100
        idx = disasm.build_xrefs(mm, dis, [(start, im.base + im.code_end)])
        full = sum(1 for t, srcs in im.xrefs.items() if set(srcs) <= {s for s, _k in idx.to(t)})
        check(f"xrefs {a}: every calibration table reference found", full == len(im.xrefs),
              f"{full}/{len(im.xrefs)}")
        called = [fn for fn in im.functions[1:] if any(k == "call" for _s, k in idx.to(fn))]
        if a != "sh2":            # SH calls go through registers (JSR @Rn)
            check(f"xrefs {a}: call targets", len(called) >= 10, len(called))
    from radide.firmware.analysis import sleigh as _sl
    if _sl.available():         # VLE / C166 / V850 / 8051: built-in SLEIGH backend (samples/Tests/Firmware/Sleigh)
        check("VLE: built-in SLEIGH backend", disasm.backend("ppc-vle") == "sleigh", disasm.backend("ppc-vle"))
    else:
        check("VLE unsupported without pypcode, with a reason", not disasm.supported("ppc-vle") and
              "pypcode" in disasm.unsupported_reason("ppc-vle"))
    from radide.firmware.disasm import disassemble as short
    im = make_image("arm-thumb")
    rows = short(im.bytes(), im.base, "arm-thumb", im.functions[0], 10)
    check("radide.firmware.disasm.disassemble (workbench API)", len(rows) == 10 and rows[0][0] == im.functions[0]
          and rows[0][2].startswith("push"), rows[:2])


def test_cli_and_project(tmp: Path):
    py = sys.executable
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    img = tmp / "cli_tricore.bin"

    def run(*args):
        return subprocess.run([py, "-m", "radide.firmware.analysis", *map(str, args)], capture_output=True,
                              text=True, env=env, cwd=str(tmp), timeout=300)
    r = run("synth", "tricore", img)
    check("cli synth", r.returncode == 0 and img.is_file(), r.stderr)
    r = run("info", img)
    check("cli info: TriCore + base", r.returncode == 0 and "TriCore" in r.stdout and "0x80000000" in r.stdout,
          r.stdout[-600:] + r.stderr)
    r = run("convert", img, tmp / "cli.s19", "--base", "0x80000000")
    check("cli convert to S-record", r.returncode == 0 and load(tmp / "cli.s19").min_address == 0x80000000, r.stderr)
    r = run("deinterleave", img, tmp / "e.bin", tmp / "o.bin")
    r2 = run("interleave", tmp / "e.bin", tmp / "o.bin", tmp / "back.bin")
    check("cli deinterleave / interleave", r.returncode == 0 and r2.returncode == 0 and
          (tmp / "back.bin").read_bytes() == img.read_bytes())
    r = run("merge", tmp / "m.hex", f"{tmp / 'e.bin'}@0x80000000", f"{tmp / 'o.bin'}@0x80100000")
    check("cli merge with addresses", r.returncode == 0 and len(load(tmp / "m.hex").segments) == 2, r.stdout + r.stderr)
    im = make_image("tricore")
    r = run("disasm", img, "--arch", "tricore", "--base", "0x80000000", "--start", hex(im.functions[0]),
            "--length", "0x40")
    check("cli disasm", r.returncode == 0 and "ret" in r.stdout, r.stdout[:300] + r.stderr)
    t = im.tables[2]
    r = run("xrefs", img, hex(t.address), "--arch", "tricore", "--base", "0x80000000")
    check("cli xrefs to a map", r.returncode == 0 and f"reference(s) to 0x{t.address:X}" in r.stdout and
          not r.stdout.startswith("0 reference"), r.stdout[-300:])
    # project model
    from radide.firmware.analysis.project import FirmwareProject, new_project
    folder = tmp / "proj"
    fp = new_project(folder, "Proj")
    dst = fp.set_original(img)
    check("project: original copied + read-only", dst.is_file() and not os.access(dst, os.W_OK))
    check("project: SHA-256 recorded", len(fp.sha256) == 64 and fp.verify()[0])
    fp2 = FirmwareProject.load(folder)
    check("project: CPU + base stored", fp2.arch == "tricore" and fp2.base == 0x80000000, (fp2.arch, hex(fp2.base)))
    w = fp2.make_working_copy()
    check("project: working copy is a separate file", w.is_file() and w.read_bytes() == img.read_bytes() and
          w.resolve() != dst.resolve())
    fp2.set_label(0x80000100, "reset_handler", "entry", "func")
    check("project: labels", [x.name for x in fp2.labels()] == ["reset_handler"])
    r = run("build", folder)
    check("cli build: verify + report", r.returncode == 0 and (folder / "build" / "analysis.txt").is_file() and
          "intact" in r.stdout, r.stdout[-400:] + r.stderr)
    os.chmod(dst, 0o666)
    dst.write_bytes(b"tampered")
    r = run("build", folder)
    check("cli build: tampered original refused", r.returncode != 0 and "changed" in r.stdout, r.stdout[-300:])


def main():
    with tempfile.TemporaryDirectory(prefix="radide-fw-") as d:
        tmp = Path(d)
        test_containers(tmp)
        test_split(tmp)
        test_analysis()
        test_detection()
        test_disassembly()
        test_cli_and_project(tmp)
        for p in tmp.rglob("*"):
            try:
                os.chmod(p, 0o666)
            except OSError:
                pass
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
