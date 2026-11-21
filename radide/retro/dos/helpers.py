"""Tiny DOS helper programs RAD IDE puts next to a run (no Qt in here).

    RADKEYS.COM  stuff keys into the BIOS keyboard buffer (``RADKEYS 1~q``: "1", Enter, "q";
                 ` = Esc, _ = Space, ^U ^D ^L ^R = arrows; | < > cannot be used on a DOS command line)
    RADSCR.COM   save the screen: text -> C:\\_SCREEN.TXT, mode 13h -> C:\\_SCR13.RAW (pixels + palette)
    RADCAP.COM   resident: saves the last mode 13h frame when the program switches back to text mode

They are original RAD IDE code: the sources are in ``helpers_src/*.ASM`` (JWasm, ``-bin``) and the bytes below are
what JWasm 2.21 produces from them (samples/Tests/Retro/DOSDev/test_dos_toolchains.py re-assembles and compares).
They make captured runs possible: builds and tests run DOSBox-X without a window, feed the program its keys and
read back what it printed with ``PROG > _OUT.TXT`` plus the screen (Crt / conio programs write to the video
memory, not to standard output).
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "helpers_src"

_COM = {
    "RADKEYS.COM": "eNrb18jQJdfAYPS/18L6e3H4GhuFku82nCWfbepKWXfyyry2t0kAMqQZX5vZxAMZCpavdW3iSlWBarXXqNzfyeBhE1oivZMh"
                   "wMalRGQng7eNTwnvTgZfm6ASttfru04Yvd3Celbs9dIdDD5nFQHPSyot",
    "RADSCR.COM": "eNrb4cDQd0BtgSfDIiYmtYVeDItZmNQWtDBwHShl2iDx78AiZqYGOyYm4ZJyEMVewg+imMuYXy5j2MWw4zXzLoYNat1mfgx9"
                  "h/azsXbJMTN187Ewdb9X62JpPsbUwer+6Kv13xK+Ltf/NgolLEBDmf1fvzvOysvVfJzp3+nSS93nG1+ysW6xCTQ+uesp41nF"
                  "yCL/7htbHHaxsZ5V3GJ3VvG1w67jzEYH3u06ybyfjWknA/MbkJm/ttgA1X8Bqi9S6L4ht4NhQd8N40s7GX5tcTirKL/FAahu"
                  "FxsTxIQdDD5nFZ2tYuKDnYNcXf30QiJCGKBcQ2O9IMdwBhAAAIW4Y64=",
    "RADCAP.COM": "eNp7OYOZAQScrWLig52DDI31ghzDGRr+MJSw2jL5l0rrNdixMzKUCgfI7XBg6LuxwJNB3kY4opT5BSuD3n89Zka9Y2zsjIwB"
                  "wYFB4XJ88ruOMxsdeLfrJPP+2Yw7GZjfdLC6P/q1xcb45C4OxrOKRQrdN+R2MCzou2F8aSfDry0OZxXltzgA1e2aDZTdYgfk"
                  "xkdFRkeAzWQ4zDAKRsEIBjsETM8qdsoxM/awsTLuEFDdJQbMJbtWsWxkufxqB4PhWUUAewtApg==",
}


def com_bytes(name: str) -> bytes:
    return zlib.decompress(base64.b64decode(_COM[name.upper()]))


def write_helpers(folder: Path) -> Path:
    """Write the three helpers into *folder* (created); unchanged files are not rewritten."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in _COM:
        data = com_bytes(name)
        p = folder / name
        try:
            if p.is_file() and p.read_bytes() == data:
                continue
        except OSError:
            pass
        p.write_bytes(data)
    return folder


def assemble_sources(jwasm: str, out_dir: Path) -> dict[str, bytes]:
    """Re-assemble helpers_src/*.ASM with JWasm (tests compare the result with the embedded bytes)."""
    import subprocess
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for src in sorted(SRC_DIR.glob("*.ASM")):
        out = out_dir / (src.stem + ".COM")
        subprocess.run([jwasm, "-q", "-bin", f"-Fo={out}", str(src)], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if out.is_file():
            res[out.name] = out.read_bytes()
    return res


# ---------------------------------------------------------------------------- mode 13h capture
def read_mode13(path: Path) -> tuple[bytes, list[tuple[int, int, int]]]:
    """(64000 pixel bytes, 256 RGB colours 0..255) of a _SCR13.RAW file."""
    data = Path(path).read_bytes()
    if len(data) < 64000:
        raise ValueError(f"{path}: {len(data)} bytes, a mode 13h capture has 64000 + 768")
    pixels = data[:64000]
    pal_raw = data[64000:64000 + 768].ljust(768, b"\0")
    pal = [tuple(min(255, (pal_raw[i * 3 + k] & 63) * 255 // 63) for k in range(3)) for i in range(256)]
    return pixels, pal                                           # type: ignore[return-value]


def mode13_png(raw: Path, png: Path) -> Path:
    """Write a _SCR13.RAW capture as a 320x200 PNG (plain zlib, no Qt)."""
    import struct
    pixels, pal = read_mode13(raw)
    rows = b"".join(b"\0" + bytes(c for i in pixels[y * 320:(y + 1) * 320] for c in pal[i]) for y in range(200))

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 200, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    png = Path(png)
    png.write_bytes(data)
    return png


def mode13_stats(raw: Path) -> dict:
    """Colour histogram facts of a capture (tests: "the demo drew something")."""
    pixels, _pal = read_mode13(raw)
    counts: dict[int, int] = {}
    for b in pixels:
        counts[b] = counts.get(b, 0) + 1
    return {"colours": len(counts), "nonzero": 64000 - counts.get(0, 0), "top": sorted(counts.items(),
                                                                                    key=lambda kv: -kv[1])[:8]}


__all__ = ["SRC_DIR", "assemble_sources", "com_bytes", "mode13_png", "mode13_stats", "read_mode13", "write_helpers"]
