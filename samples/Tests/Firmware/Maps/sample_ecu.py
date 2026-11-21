"""The 64 KB synthetic calibration image described by sample_ecu.a2l (base address 0x80000000).

``build_sample_bin()`` -> (bytes, expected) where *expected* holds the physical values the A2L import must read.
Run it directly to write sample_ecu.bin next to this file (not committed: it is rebuilt by the tests).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def build_sample_bin():
    img = bytearray(b"\xff" * 0x10000)
    exp = {}
    # KFZW: Bosch-style record at 0x1000: nx=8, ny=6, X (raw*40 rpm), Y (raw*0.75 %), values row order
    x = np.array([10, 20, 35, 50, 75, 100, 130, 160])            # 400 .. 6400 1/min
    y = np.array([20, 40, 60, 90, 120, 160])                       # 15 .. 120 %
    z = (np.add.outer(np.linspace(60, 20, 6), np.linspace(0, 60, 8)) + 64).round().astype(int)
    rec = bytes([8, 6]) + bytes(x.tolist()) + bytes(y.tolist()) + bytes(z.ravel().tolist())
    img[0x1000:0x1000 + len(rec)] = rec
    exp["KFZW"] = {"address": 0x1010, "cols": 8, "rows": 6, "x": (x * 40).tolist(), "y": (y * 0.75).tolist(),
                   "z": (z * 0.75 - 48).tolist(), "x_address": 0x1002, "y_address": 0x100A}
    # KFLAMBDA: big-endian SWORD values, column order (Y fastest), COM_AXIS SNM16_X / SNL12_Y
    xs = np.array([800, 1200, 1600, 2000, 2500, 3000, 3500, 4200, 5000, 6000])
    ys = np.array([20, 40, 60, 80, 100, 130, 160, 200])            # raw (x0.75 %)
    lam = (10000 - np.outer(np.linspace(0, 1200, 8), np.ones(10)) + np.linspace(0, 300, 10)[None, :]).round()
    img[0x1100:0x1100 + 160] = lam.T.astype(">i2").tobytes()       # column order: column by column
    img[0x1200:0x1200 + 20] = xs.astype(">u2").tobytes()
    img[0x1220:0x1220 + 16] = ys.astype(">u2").tobytes()
    exp["KFLAMBDA"] = {"address": 0x1100, "cols": 10, "rows": 8, "x": xs.tolist(), "y": (ys * 0.75).tolist(),
                       "z": (lam * 0.0001).tolist(), "x_address": 0x1200, "y_address": 0x1220}
    # KLTEMP: SWORD LE curve, fixed axis -40..120 step 20
    kl = np.array([300, 240, 180, 120, 70, 30, 0, -10, -20])
    img[0x1300:0x1300 + 18] = kl.astype("<i2").tobytes()
    exp["KLTEMP"] = {"address": 0x1300, "cols": 9, "rows": 1, "x": list(range(-40, 121, 20)), "z": [kl.tolist()]}
    # CWLAMBDA: UBYTE value, raw 2*phys
    img[0x1400] = 150
    exp["CWLAMBDA"] = {"address": 0x1400, "z": [[75.0]]}
    # ATAB: 16 ULONG
    at = np.arange(16, dtype=np.uint32) * 1000 + 7
    img[0x1410:0x1410 + 64] = at.astype("<u4").tobytes()
    exp["ATAB"] = {"address": 0x1410, "cols": 16, "rows": 1, "z": [at.astype(float).tolist()]}
    # KFF32: float32 6x5, fixed axes (list / 0,4,8,12,16)
    ff = np.outer(np.linspace(1, 2, 5), np.linspace(0.5, 1.5, 6)).astype(np.float32)
    img[0x1500:0x1500 + 120] = ff.astype("<f4").tobytes()
    exp["KFF32"] = {"address": 0x1500, "cols": 6, "rows": 5, "x": [0, 10, 25, 50, 75, 100], "y": [0, 4, 8, 12, 16],
                    "z": ff.astype(float).tolist()}
    # KLAL: n=8 (byte) at 0x1600, word axis aligned to 0x1602, word values at 0x1612
    ax = np.array([100, 200, 400, 800, 1600, 3200, 6400, 12800])
    vals = np.array([5, 9, 14, 20, 27, 35, 44, 54])
    img[0x1600] = 8
    img[0x1601] = 0xAA                                             # alignment pad byte
    img[0x1602:0x1602 + 16] = ax.astype("<u2").tobytes()
    img[0x1612:0x1612 + 16] = vals.astype("<u2").tobytes()
    exp["KLAL"] = {"address": 0x1612, "cols": 8, "rows": 1, "x": ax.tolist(), "z": [vals.tolist()], "x_address": 0x1602}
    img[0x1700] = 1
    img[0x1800:0x1810] = b"RADIDE-DEMO-0001"
    img[0x10000 - 4:] = struct.pack("<I", 0x12345678)
    return bytes(img), exp


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "sample_ecu.bin"
    data, _ = build_sample_bin()
    out.write_bytes(data)
    print(f"wrote {out} ({len(data)} bytes)")
