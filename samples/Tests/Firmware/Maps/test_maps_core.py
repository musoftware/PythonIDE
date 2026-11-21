"""Calibration maps core tests (no Qt): map finder on synthetic firmware, data types, editing operations,
ori/mod differences, compare / copy between binaries, map pack JSON / CSV, A2L import + export round trip,
TunerStudio ini / msq (synthetic, plus the real rusEFI ini when download_rusefi.py has fetched it).

    python samples/Tests/Firmware/Maps/test_maps_core.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from radide.firmware.maps import a2l, ops, tsini  # noqa: E402
from radide.firmware.maps.finder import find_maps, smoothness, value_profile  # noqa: E402
from radide.firmware.maps.model import (DTYPES, AxisDef, MapDef, MapPack, encode_array, map_to_tsv,  # noqa: E402
                                        pack_from_csv, pack_to_csv, parse_tsv, read_array)
from radide.firmware.maps.synth import build_image  # noqa: E402
from radide.retro.rom.buffer import HexBuffer  # noqa: E402
from sample_ecu import build_sample_bin  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def same_map(found: MapDef, want: MapDef) -> bool:
    return (found.address, found.cols, found.rows, found.dtype, found.endian) == \
        (want.address, want.cols, want.rows, want.dtype, want.endian) and \
        (want.rows == 1 or found.order == want.order)


# ====================================================================== finder
def test_finder():
    for seed in (1, 2, 3, 4, 5):
        img, maps = build_image(seed)
        t = time.time()
        cands = find_maps(img)
        dt = time.time() - t
        top = cands[:len(maps)]
        missing = [m.name for m in maps if not any(same_map(c.mapdef, m) for c in top)]
        check(f"finder seed {seed}: all {len(maps)} embedded maps are the top {len(maps)} ({dt:.1f}s)", not missing,
              f"missing {missing}; top = {[c.label() + ' ' + c.layout for c in cands[:len(maps) + 3]]}")
        # axes found at the right place
        ok_axes = True
        for m in maps:
            c = next((c for c in top if same_map(c.mapdef, m)), None)
            if c is None:
                continue
            if c.mapdef.x_axis.address != m.x_axis.address or (m.rows > 1 and c.mapdef.y_axis.address !=
                                                                 m.y_axis.address):
                ok_axes = False
        check(f"finder seed {seed}: axis addresses of every found map are right", ok_axes)
    # a bigger image: speed
    img, maps = build_image(7, size=0x100000)
    t = time.time()
    cands = find_maps(img)
    dt = time.time() - t
    check(f"finder 1 MB image in {dt:.1f}s (< 20 s) and finds the maps", dt < 20 and
          all(any(same_map(c.mapdef, m) for c in cands[:len(maps)]) for m in maps), f"{dt:.1f}s")
    # random bytes alone: nothing scores like a real map
    rnd = np.random.default_rng(9).integers(0, 256, 0x20000, dtype=np.uint8).tobytes()
    best = find_maps(rnd)
    check("finder on random bytes: no candidate scores 80+", not best or best[0].score < 80,
          [c.label() for c in best[:3]])
    check("finder on 0xFF fill: nothing found", not find_maps(b"\xff" * 0x8000))
    # smoothness metric
    z = np.add.outer(np.linspace(0, 50, 8), np.linspace(0, 100, 10))
    noise = np.random.default_rng(3).integers(0, 256, (8, 10)).astype(float)
    check("smoothness: surface > 0.8, noise < 0.4", smoothness(z) > 0.8 and smoothness(noise) < 0.4,
          (smoothness(z), smoothness(noise)))
    mins, maxs, per = value_profile(img, "u8", "le", 0, len(img), 1000)
    check("2D view profile: 1000 buckets, min <= max", len(mins) <= 1000 and np.all(mins <= maxs) and per >= 1)


# ====================================================================== model / types
def test_model():
    ok = True
    for dt in DTYPES:
        for en in ("le", "be"):
            vals = np.array([0, 1, 2, 100]) if dt[0] == "u" else np.array([-3, 0, 5, 100])
            if dt[0] == "f":
                vals = np.array([-1.5, 0.25, 3.0, 1e3])
            b = encode_array(vals, dt, en)
            back = read_array(b, 0, len(vals), dt, en)
            ok &= np.allclose(back, vals)
    check("every data type / byte order encodes and reads back", ok)
    check("integers clamp to the type range", list(read_array(encode_array([-5, 300], "u8"), 0, 2, "u8")) == [0, 255])
    data = bytearray(64)
    m = MapDef("T", 8, cols=3, rows=2, dtype="u16", endian="be", order="col", factor=0.5, offset=-10)
    z = np.array([[0.0, 5.0, 10.0], [-10.0, 20.5, 30.0]])
    data[8:8 + m.nbytes()] = m.encode_phys(z)
    check("column-order map: phys round trip through the bytes", np.allclose(m.phys(data), z), m.phys(data))
    check("column order stores Y fastest", read_array(data, 8, 2, "u16", "be").tolist() == [20.0, 0.0])
    check("quantize: phys rounds to factor steps", np.allclose(m.quantize([[1.2, 1.3, 0], [0, 0, 0]])[0, :2],
                                                               [1.0, 1.5]))
    m.x_axis = AxisDef("rpm", 40, 3, "u8", factor=100, unit="1/min")
    m.y_axis = AxisDef("load", values=[10, 20], count=2)
    pack = MapPack("p", [m], base_address=0x80000000)
    tmp = Path(tempfile.mkdtemp()) / "x.maps.json"
    pack.save(tmp)
    back = MapPack.load(tmp)
    check("map pack JSON round trip", back.to_dict() == pack.to_dict() and back.base_address == 0x80000000,
          (back.to_dict(), pack.to_dict()))
    csv_back = pack_from_csv(pack_to_csv(pack))
    a, b = pack.maps[0].to_dict(), csv_back.maps[0].to_dict()
    a.pop("source"), b.pop("source")
    check("map list CSV round trip", a == b, (a, b))
    text = map_to_tsv(m, data)
    grid = parse_tsv(text)
    check("map as Excel text: axis row + Y column", len(grid) == 3 and grid[0][1:] == [0.0, 0.0, 0.0] and
          grid[1][0] == 10.0, grid)
    check("parse_tsv: decimal comma and blanks", parse_tsv("1,5\t\t3\n") == [[1.5, None, 3.0]], parse_tsv("1,5\t\t3\n"))


# ====================================================================== editing operations
def test_ops():
    z = np.arange(12, dtype=float).reshape(3, 4)
    all_ = ops.full_mask(z)
    r = ops.rect_mask(z, 0, 1, 1, 2)
    check("set value in a selection", ops.set_value(z, r, 7)[r].tolist() == [7] * 4 and ops.set_value(z, r, 7)[2, 3] == 11)
    check("add", np.allclose(ops.add(z, all_, 2.5), z + 2.5))
    check("add percent +10%", np.allclose(ops.add_percent(z, all_, 10), z * 1.1))
    check("percent -50% only in the selection", ops.add_percent(z, r, -50)[0, 1] == 0.5 and
          ops.add_percent(z, r, -50)[0, 0] == 0)
    check("multiply", np.allclose(ops.multiply(z, all_, 3), z * 3))
    row = np.array([[0.0, 9, 9, 9, 40]])
    check("interpolate a row", np.allclose(ops.interpolate(row, ops.full_mask(row)), [[0, 10, 20, 30, 40]]))
    col = np.array([[0.0], [5], [5], [30]])
    check("interpolate a column", np.allclose(ops.interpolate(col, ops.full_mask(col)).ravel(), [0, 10, 20, 30]))
    sq = np.zeros((3, 3))
    sq[0, 0], sq[0, 2], sq[2, 0], sq[2, 2] = 0, 20, 40, 60
    bi = ops.interpolate(sq, ops.full_mask(sq), "2d")
    check("interpolate bilinear from the corners", np.isclose(bi[1, 1], 30) and np.isclose(bi[0, 1], 10), bi)
    hz = ops.interpolate(z.copy(), ops.full_mask(z), "h")
    check("interpolate horizontally keeps linear rows", np.allclose(hz, z))
    spike = np.zeros((3, 3))
    spike[1, 1] = 9
    sm = ops.smooth(spike, ops.full_mask(spike))
    check("smooth: 3x3 average (edges padded)", np.isclose(sm[1, 1], 1.0) and np.isclose(sm[0, 0], 1.0), sm)
    pz, pm = ops.paste(z, "100\t200\n300\t\n", 1, 1)
    check("paste a block at (1,1) (blank cells keep)", pz[1, 1] == 100 and pz[1, 2] == 200 and pz[2, 1] == 300 and
          pz[2, 2] == z[2, 2] and pm.sum() == 3)
    check("copy text of a selection", ops.copy_text(z, r) == "1\t2\n5\t6\n", repr(ops.copy_text(z, r)))
    # write-back with undo
    img, maps = build_image(2)
    buf = HexBuffer(img)
    m = maps[0]                              # KF_BOSCH8: u8, factor 0.75
    before = m.phys(buf.data)
    changed = ops.apply(buf, m, ops.add_percent(before, ops.full_mask(before), 10))
    after = m.phys(buf.data)
    expect = np.clip(np.rint(before * 1.1 / 0.75), 0, 255) * 0.75
    check("write-back +10% (rounded to the raw resolution)", changed and np.allclose(after, expect),
          (after[0, :4], expect[0, :4]))
    check("write-back is one undo step", len(buf.undo_stack) == 1)
    buf.undo()
    check("undo restores the map", np.allclose(m.phys(buf.data), before))
    buf.redo()
    check("redo applies it again", np.allclose(m.phys(buf.data), expect))
    m16 = maps[1]                            # s16 with factor 0.1
    z16 = m16.phys(buf.data)
    ops.apply(buf, m16, ops.set_value(z16, ops.rect_mask(z16, 0, 0, 0, 0), -12.34))
    check("signed 16-bit cell set to -12.34 -> -12.3 (factor 0.1)", np.isclose(m16.phys(buf.data)[0, 0], -12.3))
    big = ops.set_value(before, ops.full_mask(before), 1e6)
    ops.apply(buf, m, big)
    check("values beyond the type clamp to its maximum", np.allclose(m.raw(buf.data), 255))


# ====================================================================== differences / compare
def test_diff():
    img, maps = build_image(3)
    pack = MapPack("p", maps)
    mod = bytearray(img)
    m = maps[0]
    z = m.phys(mod)
    z[2, 3] += 7.5
    z[4, 5] -= 3
    ops.apply(mod, m, z)
    mod[0x100:0x104] = b"\x01\x02\x03\x04"
    ch = ops.changed_maps(pack, img, mod)
    check("changed maps: exactly the edited one", [d["map"].name for d in ch] == [m.name], ch)
    check("changed cells counted (2)", ch and ch[0]["cells"] == 2, ch)
    check("cell diff mask marks the two cells", ops.cell_diff(m, img, mod).sum() == 2 and
          ops.cell_diff(m, img, mod)[2, 3])
    un = ops.unmapped_changes(pack, img, mod)
    check("change outside the maps listed as a range", un == [(0x100, 0x104)], un)
    check("diff ranges", ops.diff_ranges(b"abcdef", b"abXdeY") == [(2, 3), (5, 6)])
    # B: the same maps shifted by 0x40 with other values -> locate + copy map to A
    b = bytearray(len(img))
    b[0x40:] = img[:-0x40]
    mb = m.copy()
    mb.address += 0x40
    zb = mb.phys(b)
    zb += 1.5
    ops.apply(b, mb, zb)
    delta = ops.locate_in(m, img, b)
    check("locate a map in another version (shifted by 0x40)", delta == 0x40, delta)
    a = HexBuffer(img)
    shifted = m.copy()
    shifted.address += 0x40
    for ax in (shifted.x_axis, shifted.y_axis):
        if ax.stored:
            ax.address = int(ax.address) + 0x40
    ok = ops.copy_map(shifted, b, a, delta=-0x40)
    check("copy map from B to A", ok and np.allclose(m.phys(a.data), shifted.phys(b)))


# ====================================================================== A2L
def test_a2l():
    data, exp = build_sample_bin()
    res = a2l.load_a2l(HERE / "sample_ecu.a2l", data)
    pack = res.pack
    check("A2L: base address from the FLASH memory segment", pack.base_address == 0x80000000, hex(pack.base_address))
    check("A2L: 2 memory segments, little endian module", len(res.segments) == 2 and res.byte_order == "le")
    names = [m.name for m in pack.maps]
    check("A2L: supported characteristics imported (ASCII skipped, CUBOID reported)",
          names == ["KFZW", "KFLAMBDA", "KLTEMP", "CWLAMBDA", "ATAB", "KFF32", "KLAL", "SWMODE"] and
          any("CUBOID" in w for w in res.warnings) and any("TAB_VERB" in w for w in res.warnings), (names, res.warnings))
    for name, e in exp.items():
        m = pack.get(name)
        if m is None:
            check(f"A2L {name}", False, "missing")
            continue
        ok = m.address == e["address"] and np.allclose(m.phys(data), np.array(e["z"]), atol=1e-6)
        if "cols" in e:
            ok &= (m.cols, m.rows) == (e["cols"], e["rows"])
        if "x" in e:
            ok &= np.allclose(m.x_values(data), e["x"])
        if "y" in e:
            ok &= np.allclose(m.y_values(data), e["y"])
        for k in ("x_address", "y_address"):
            if k in e:
                ax = m.x_axis if k[0] == "x" else m.y_axis
                ok &= ax.address == e[k]
        check(f"A2L {name}: address, shape, axes and physical values", ok,
              (m.to_dict(), m.phys(data)[:1], e))
    k = pack.get("KFZW")
    check("A2L: folders from FUNCTION / DEF_CHARACTERISTIC", k.folder == "Ignition" and
          pack.get("KLTEMP").folder == "Mixture")
    check("A2L: RAT_FUNC conversion -> factor 40 on the rpm axis", k.x_axis.factor == 40 and k.x_axis.unit == "1/min")
    check("A2L: COLUMN_DIR + MSB_FIRST", pack.get("KFLAMBDA").order == "col" and pack.get("KFLAMBDA").endian == "be")
    check("A2L: FORMAT -> decimals", k.digits == 1)
    nodata = a2l.load_a2l(HERE / "sample_ecu.a2l").pack.get("KFZW")
    check("A2L without the binary: maximum axis sizes (16x12)", (nodata.cols, nodata.rows) == (16, 12) and
          nodata.address == 0x1000 + 2 + 16 + 12)
    # export -> import round trip
    text = a2l.export_a2l(pack, segment_size=len(data))
    back = a2l.parse_a2l(text, data)
    diffs = []
    for a_, b_ in zip(pack.maps, back.pack.maps):
        da, db = a_.to_dict(), b_.to_dict()
        for key in ("source", "lower", "upper", "description"):
            da.pop(key, None)
            db.pop(key, None)
        if da != db:
            diffs.append((da, db))
    check("A2L export -> import round trip (same maps, axes, conversions, folders)",
          not diffs and len(back.pack.maps) == len(pack.maps) and back.pack.base_address == 0x80000000 and
          not back.warnings, diffs[:2] or back.warnings)
    same_vals = all(np.allclose(a_.phys(data), b_.phys(data)) for a_, b_ in zip(pack.maps, back.pack.maps))
    check("A2L round trip: values read identically", same_vals)
    # errors
    for bad, what in (("/begin PROJECT P \"\"\n /begin MODULE M \"\"\n", "unclosed"),
                      ("/begin PROJECT P \"\" /end MODULE", "wrong end")):
        try:
            a2l.parse_a2l(bad)
            check(f"A2L error: {what}", False, "no error")
        except a2l.A2LError:
            check(f"A2L error: {what} -> A2LError", True)
    # finder + A2L agree on the Bosch-style KFZW record
    found = find_maps(data)
    check("finder also finds KFZW (Bosch header) in the A2L sample",
          any(c.mapdef.address == 0x1010 and (c.mapdef.cols, c.mapdef.rows) == (8, 6) for c in found),
          [c.label() for c in found[:5]])


# ====================================================================== TunerStudio ini / msq
INI = """
[MegaTune]
   signature = "synthetic-ecu 1.0"
[Constants]
   endianness = little
   nPages = 2
   pageSize = 512, 64
page = 1
   reqFuel = scalar, U16, 0, "ms", 0.001, 0, 0, 30, 3
   rpmBins = array, U08, 2, [6], "RPM", 100, 0, 0, 25500, 0
   mapBins = array, U08, 8, [4], "kPa", 2, 0, 0, 510, 0
   veTable = array, U08, 12, [6x4], "%", 1, 0, 0, 255, 0
   cltBins = array, S16, 36, [5], "C", 0.1, 0, -40, 150, 1
   cltCorr = array, U16, 46, [5], "%", 0.1, 0, 0, 200, 1
   unitsAfr = array, U08, 56, [3], {afrUnits}, {useLambda ? 0.1 : 1}, 0, 0, 255, 1
#if NEVER
   ghost = array, U08, 60, [2], "", 1, 0, 0, 1, 0
#else
   real = array, U08, 60, [2], "", 1, 0, 0, 255, 0
#endif
page = 2
   idleTable = array, F32, 0, [4], "%", 1, 0, 0, 100, 1
[TableEditor]
   table = veTbl, veMap, "VE Table", 1
      xBins = rpmBins, rpm
      yBins = mapBins, map
      zBins = veTable
[CurveEditor]
   curve = cltCurve, "Coolant correction"
      xBins = cltBins, clt
      yBins = cltCorr
"""

MSQ = """<?xml version="1.0" encoding="UTF-8"?>
<msq xmlns="http://www.msefi.com/:msq"><page number="0">
<constant name="reqFuel" units="ms" digits="3">7.25</constant>
<constant name="rpmBins" rows="6" cols="1">500 1000 2000 3000 4500 6500</constant>
<constant name="mapBins" rows="4" cols="1">40 80 120 200</constant>
<constant name="veTable" rows="4" cols="6">
 40 45 50 55 60 62
 50 55 60 65 70 72
 60 65 70 75 80 82
 70 75 80 85 90 92 </constant>
<constant name="cltBins" rows="5" cols="1">-40 0 30 70 110</constant>
<constant name="cltCorr" rows="5" cols="1">160 130 110 100 100</constant>
<constant name="idleTable" rows="4" cols="1">35.5 30 25 20.25</constant>
<constant name="note">"text"</constant>
</page></msq>"""


def test_tsini():
    res = tsini.parse_ini(INI)
    check("ini: signature, endianness, 2 pages (page 2 after page 1)", res.signature == "synthetic-ecu 1.0" and
          res.endian == "le" and res.page_base == {1: 0, 2: 512}, (res.signature, res.page_base))
    ve = res.pack.get("veTable")
    check("ini: VE table 6x4 with rpm / map bins", ve is not None and (ve.cols, ve.rows) == (6, 4) and
          ve.x_axis.name == "rpmBins" and ve.x_axis.address == 2 and ve.y_axis.address == 8 and
          ve.folder == "Tables", ve and ve.to_dict())
    cc = res.pack.get("cltCorr")
    check("ini: curve with its X bins", cc is not None and cc.kind == "curve" and cc.x_axis.address == 36 and
          cc.factor == 0.1)
    check("ini: #if / #else (ghost skipped, real kept)", "ghost" not in res.fields and "real" in res.fields)
    check("ini: expression scale imports as 1 with a note", res.fields["unitsAfr"].scale == 1.0 and
          res.fields["unitsAfr"].notes)
    check("ini: bins used by tables are not listed twice", res.pack.get("rpmBins") is None and
          res.pack.get("idleTable") is not None)
    img, written = tsini.msq_to_image(res, tsini.msq_values(MSQ))
    check("msq -> pages image (576 bytes, 7 values written)", len(img) == 576 and len(written) == 7, written)
    check("msq image: VE table / bins / curve read back through the map pack",
          np.allclose(ve.phys(img)[3], [70, 75, 80, 85, 90, 92]) and np.allclose(ve.x_values(img), [500, 1000, 2000,
                                                                                                    3000, 4500, 6500])
          and np.allclose(cc.phys(img), [[160, 130, 110, 100, 100]]) and np.allclose(cc.x_values(img),
                                                                                     [-40, 0, 30, 70, 110]),
          (ve.phys(img), ve.x_values(img)))
    idle = res.pack.get("idleTable")
    check("msq image: float table on page 2", idle.address == 512 and np.allclose(idle.phys(img), [[35.5, 30, 25, 20.25]]))
    rq = res.fields["reqFuel"]
    check("msq image: scalar with scale 0.001", read_array(img, rq.offset, 1, "u16")[0] == 7250)
    # the real rusEFI ini (GPL, downloaded by download_rusefi.py)
    from download_rusefi import default_dir
    d = default_dir()
    ini_path = d / "rusefi_f407-discovery.ini"
    if os.environ.get("RUSEFI_DOWNLOAD") == "1" and not ini_path.is_file():
        from download_rusefi import download
        download(d)
    if ini_path.is_file():
        t = time.time()
        r = tsini.load_ini(ini_path)
        dt = time.time() - t
        ve = r.pack.get("veTable")
        ign = r.pack.get("ignitionTable")
        check(f"rusEFI ini parsed in {dt:.2f}s: VE + ignition tables 16x16 with bins",
              ve is not None and ign is not None and (ve.cols, ve.rows) == (16, 16) and ve.x_axis.name == "veRpmBins"
              and ve.y_axis.name == "veLoadBins" and ign.dtype == "s16" and len(r.pack) > 100,
              (ve and ve.to_dict(), len(r.pack)))
        cr = r.pack.get("crankingCycleBaseFuel")
        check("rusEFI ini: non-square table 8x4 (x = cranking cycles, y = coolant)",
              cr is not None and (cr.cols, cr.rows) == (8, 4) and cr.x_axis.count == 8 and cr.y_axis.count == 4)
        vals = tsini.msq_values(d / "clt_idle_prev.msq")
        check("rusEFI msq parsed (manIdlePosition, 16 coolant bins)", vals.get("manIdlePosition") == 50.0 and
              len(vals.get("cltIdleCorrBins", [])) == 16)
        img, written = tsini.msq_to_image(r, vals)
        check("rusEFI msq (older firmware) -> image: renamed / resized values are skipped, image = all pages",
              "cltIdleCorrBins" not in written and len(img) == sum(s for _p, s in r.pages), written)
        a2l_text = a2l.export_a2l(r.pack)
        back = a2l.parse_a2l(a2l_text)
        check("rusEFI map pack -> A2L -> map pack keeps every map", len(back.pack) == len(r.pack) and
              back.pack.get("veTable").cols == 16, (len(back.pack), len(r.pack), back.warnings[:3]))
    else:
        print("SKIP rusEFI ini (run download_rusefi.py or set RUSEFI_DOWNLOAD=1)")


def main():
    for fn in (test_finder, test_model, test_ops, test_diff, test_a2l, test_tsini):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} raised", False, e)
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
