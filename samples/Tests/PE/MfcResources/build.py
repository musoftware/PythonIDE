"""Build the MiniMfc test program (32-bit and 64-bit) with MSVC (cl + rc from Visual Studio / Build Tools).

    .venv\\Scripts\\python samples\\Tests\\PE\\MfcResources\\build.py

Writes prebuilt/MiniMfc32.pe and prebuilt/MiniMfc64.pe (the .pe extension keeps them out of the *.exe
ignore rule; the tests copy them to a temp folder as .exe). The icon, bitmaps and manifest in src/ are
generated here when missing. MFC itself is not needed (src/minimfc.cpp re-creates MFC's message maps).
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
OUT = HERE / "prebuilt"

MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="RADIDE.Tests.MiniMfc" version="1.2.3.4"/>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0"
                        processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
    </dependentAssembly>
  </dependency>
</assembly>
"""


def _bmp(w: int, h: int, pixel) -> bytes:
    """24-bit bottom-up BMP file."""
    row = (w * 3 + 3) & ~3
    data = bytearray()
    for y in range(h - 1, -1, -1):
        line = bytearray()
        for x in range(w):
            r, g, b = pixel(x, y)
            line += bytes((b, g, r))
        data += line + b"\0" * (row - len(line))
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    return b"BM" + struct.pack("<IHHI", 14 + 40 + len(data), 0, 0, 54) + info + bytes(data)


def _ico(size: int = 32) -> bytes:
    """32-bit icon with one image."""
    w = h = size
    xor = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            inside = (x - w / 2) ** 2 + (y - h / 2) ** 2 < (w / 2 - 1) ** 2
            xor += bytes((200, 120, 30, 255)) if inside else bytes((0, 0, 0, 0))
    mask = b"\0" * (((w + 31) // 32) * 4 * h)
    hdr = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, len(xor) + len(mask), 0, 0, 0, 0)
    img = hdr + bytes(xor) + mask
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(img), 22) + img


def assets() -> None:
    if not (SRC / "app.ico").exists():
        (SRC / "app.ico").write_bytes(_ico())
    if not (SRC / "logo.bmp").exists():
        (SRC / "logo.bmp").write_bytes(_bmp(48, 24, lambda x, y: (x * 5, y * 10, 160)))
    if not (SRC / "toolbar.bmp").exists():           # 3 buttons of 16 x 15
        (SRC / "toolbar.bmp").write_bytes(_bmp(48, 15, lambda x, y: ((60, 160, 60), (160, 60, 60),
                                                                       (60, 60, 160))[x // 16]))
    if not (SRC / "minimfc.manifest").exists():
        (SRC / "minimfc.manifest").write_text(MANIFEST, encoding="utf-8")


def vcvarsall() -> Path | None:
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / \
        "Microsoft Visual Studio/Installer/vswhere.exe"
    roots = []
    if vswhere.is_file():
        try:
            out = subprocess.run([str(vswhere), "-all", "-products", "*", "-requires",
                                  "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property",
                                  "installationPath"], capture_output=True, text=True, timeout=60).stdout
            roots = [Path(p.strip()) for p in out.splitlines() if p.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass
    for r in roots:
        p = r / "VC/Auxiliary/Build/vcvarsall.bat"
        if p.is_file():
            return p
    return None


def build(arch: str, vcvars: Path) -> Path:
    """arch: x86 / x64"""
    OUT.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"minimfc_{arch}_"))
    for f in SRC.iterdir():
        shutil.copy2(f, work / f.name)
    exe = work / "MiniMfc.exe"
    script = work / "b.cmd"
    script.write_text("\r\n".join([
        "@echo off",
        f'call "{vcvars}" {arch} >nul',
        "rc /nologo /fo minimfc.res minimfc.rc || exit /b 1",
        "cl /nologo /O2 /MT /EHsc /GR /W3 /DUNICODE /D_UNICODE minimfc.cpp minimfc.res "
        "/Fe:MiniMfc.exe /link /SUBSYSTEM:WINDOWS /INCREMENTAL:NO /DYNAMICBASE "
        "user32.lib comctl32.lib kernel32.lib || exit /b 1",
    ]) + "\r\n", encoding="ascii")
    cp = subprocess.run(["cmd", "/c", str(script)], cwd=work, capture_output=True, text=True, errors="replace")
    if cp.returncode != 0 or not exe.is_file():
        raise RuntimeError(f"build {arch} failed:\n{cp.stdout}\n{cp.stderr}")
    dest = OUT / f"MiniMfc{'32' if arch == 'x86' else '64'}.pe"
    shutil.copy2(exe, dest)
    shutil.rmtree(work, ignore_errors=True)
    return dest


def main() -> int:
    assets()
    vc = vcvarsall()
    if vc is None:
        print("MSVC (Visual Studio C++ tools) not found - the prebuilt files are used as they are.")
        return 1
    for arch in ("x86", "x64"):
        p = build(arch, vc)
        print(f"built {p} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
