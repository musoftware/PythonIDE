"""Native build of "VB6 (BASIC)" projects: VB6 -> FreeBASIC -> one small Win32 exe without Python.

    translate   radide/deploy/native/vb6fb (the IDE's VB parser, static types, Variant runtime)
    forms       plain Win32 windows/controls (rt/vbrt_forms.bi): comctl32 v6 visual styles manifest,
                system-DPI aware, Unicode (Arabic) text, menus, timers, common dialogs, MsgBox / InputBox
    compiler    FreeBASIC 1.10.1 for Windows (32-bit, GPL compiler / LGPL runtime with the static-link
                exception), downloaded once from the official SourceForge page into
                %LOCALAPPDATA%\\RADIDE\\tools\\freebasic-win (SHA-256 checked) - -gen gcc -O 2 -Wc -Os
    result      dist\\<exe>.exe (+ the project's data files); pictures are embedded as resources.

FreeBASIC's own runtime is linked statically: the exe imports Windows system DLLs only.
Anything the translator cannot handle is returned by check() (or raised as NativeUnsupported by build())
with file(line) reasons, and Publish falls back to the bundled VB runtime (vbrun).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import NativeUnsupported

LANGS = ("vb-basic",)
NAME = "native Win32 exe (VB6 -> FreeBASIC)"

FB_URL = "https://downloads.sourceforge.net/project/fbc/FreeBASIC-1.10.1/Binaries-Windows/FreeBASIC-1.10.1-win32.zip"
FB_SHA256 = "a3730a8b2b9f4236c81d897a1dc570243f6bc3158c427d51d8e20e6b037c6ffd"
FB_SHA1 = "30043d3429b429473fdaa22a25ef9ce757ace645"
FB_PAGE = "https://sourceforge.net/projects/fbc/files/FreeBASIC-1.10.1/Binaries-Windows/"
RT_DIR = Path(__file__).resolve().parent / "vb6fb" / "rt"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CODE_EXT = {".bas", ".form", ".frm", ".frx", ".cls", ".ctl", ".vbp", ".vbw", ".radproj", ".radsln", ".iss", ".spec",
            ".py", ".pyc", ".md", ".log"}


# ------------------------------------------------------------------ the compiler
def fb_dir() -> Path:
    from ...retro.dos import toolchain
    return toolchain.tools_root() / "freebasic-win"


def find_fbc() -> str:
    env = os.environ.get("RADIDE_FBC_WIN")
    if env and Path(env).is_file():
        return env
    exe = fb_dir() / "fbc.exe"
    return str(exe) if exe.is_file() and (fb_dir() / "lib" / "win32").is_dir() else ""


def ensure_fbc(log=print, download: bool = True) -> str:
    exe = find_fbc()
    if exe or not download:
        return exe
    from ...retro.dos import toolchain
    rel = toolchain.Release("freebasic-win", "FreeBASIC for Windows (32-bit)", "1.10.1", FB_URL, FB_SHA256, FB_PAGE,
                            "GPL-2.0+ (compiler) / LGPL-2.1+ with static-link exception (runtime)", "zip",
                            strip="FreeBASIC-1.10.1-win32/",
                            include=("fbc.exe", "bin/", "inc/", "lib/", "readme.txt", "changelog.txt"),
                            sha1=FB_SHA1, size_mb=33, exe="fbc.exe")
    log("FreeBASIC for Windows is missing - downloading the official build (one time only, 33 MB)")
    tmp = toolchain.tools_root() / "_download" / Path(FB_URL).name
    if not (tmp.is_file() and toolchain._sha256(tmp) == FB_SHA256):
        if not toolchain.download_verified(FB_URL, FB_SHA256, tmp, log, FB_SHA1):
            log(f"Download FreeBASIC yourself from {FB_PAGE} and unpack it into {fb_dir()}")
            return ""
    target = fb_dir()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    try:
        ok = toolchain._extract_zip(rel, tmp, target, log)
    except Exception as e:  # noqa: BLE001
        log(f"Unpacking failed: {e}")
        ok = False
    if not ok:
        return ""
    import json
    (target / "RADIDE-SOURCE.json").write_text(json.dumps(
        {"tool": rel.key, "title": rel.title, "version": rel.version, "url": FB_URL, "sha256": FB_SHA256,
         "licence": rel.licence, "page": FB_PAGE}, indent=1), encoding="utf-8")
    return find_fbc()


# ------------------------------------------------------------------ contract
def _translate(folder, project, cfg):
    from .vb6fb import translate_project
    exe = find_fbc()
    return translate_project(folder, project, str(Path(exe).parent) if exe else None, cfg)


def check(folder, project, cfg) -> list[str]:
    reasons = []
    upd = getattr(cfg, "update", None)
    if upd is not None and getattr(upd, "enabled", False):
        reasons.append("the update check (Publish > Updates) is only built into the Python-based program")
    tr = _translate(Path(folder), project, cfg)
    return reasons + list(tr.reasons)


def _manifest(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9.]", "", name) or "App"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="RADIDE.{ident}" version="1.0.0.0" processorArchitecture="x86"/>
  <dependency><dependentAssembly>
    <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0"
                      processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
  </dependentAssembly></dependency>
  <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
    <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
  </windowsSettings></application>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>
    <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
  </requestedPrivileges></security></trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1"><application>
    <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
    <supportedOS Id="{{1f676c76-80e1-4239-95bb-83d0f6d0da78}}"/>
    <supportedOS Id="{{35138b9a-5d96-4fbd-8e2d-a2440225f93a}}"/>
  </application></compatibility>
</assembly>
"""


def _rc_str(s: str) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def _resources(folder: Path, cfg, gen: Path, images: list, log, icon_hint: str = "") -> Path:
    from ..build import make_icon
    (gen / "app.manifest").write_text(_manifest(cfg.exe_base()), encoding="utf-8")
    lines = ['1 24 "app.manifest"']
    ico = None
    try:
        ico = make_icon(folder, cfg, gen, log)
    except Exception as e:  # noqa: BLE001
        log(f"Icon: {e}")
    if ico is None and icon_hint:          # the startup form's icon
        p = folder / icon_hint
        if p.suffix.lower() == ".ico" and p.is_file():
            ico = p
        elif p.is_file():
            try:
                from PIL import Image
                img = Image.open(p).convert("RGBA")
                side = max(img.size)
                sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
                ico = gen / "form.ico"
                sq.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            except Exception as e:  # noqa: BLE001
                log(f"Icon {icon_hint}: {e}")
    if ico is not None:
        shutil.copy2(ico, gen / "app.ico")
        lines.append('1 ICON "app.ico"')
    for k, img in enumerate(images):
        p = (folder / img)
        if p.is_file():
            dst = gen / f"img{k}{p.suffix.lower()}"
            shutil.copy2(p, dst)
            lines.append(f'{res_name(img)} 10 "{dst.name}"')
    try:
        nums = [int(n) for n in cfg.numeric_version().split(".")][:4]
    except Exception:  # noqa: BLE001
        nums = [1, 0, 0, 0]
    nums = (nums + [0, 0, 0, 0])[:4]
    v = ",".join(str(n) for n in nums)
    app = cfg.app_name or cfg.exe_base()
    strings = {"CompanyName": cfg.publisher or app, "FileDescription": app, "FileVersion": cfg.version,
               "InternalName": cfg.exe_base(), "OriginalFilename": cfg.exe_base() + ".exe", "ProductName": app,
               "ProductVersion": cfg.version, "LegalCopyright": f"(c) {cfg.publisher}" if cfg.publisher else ""}
    lines += ["1 VERSIONINFO", f"FILEVERSION {v}", f"PRODUCTVERSION {v}", "FILEOS 0x40004", "FILETYPE 0x1", "BEGIN",
              '  BLOCK "StringFileInfo"', "  BEGIN", '    BLOCK "040904B0"', "    BEGIN"]
    lines += [f'      VALUE "{k}", {_rc_str(val)}' for k, val in strings.items()]
    lines += ["    END", "  END", '  BLOCK "VarFileInfo"', "  BEGIN", '    VALUE "Translation", 0x409, 1200', "  END",
              "END"]
    rc = gen / "app.rc"
    rc.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rc


def res_name(path: str) -> str:
    """Resource name of an embedded picture (rt/vbrt_image.bi VBImageRes computes the same)."""
    out = []
    for b in path.replace("/", "\\").encode("utf-8"):
        if 97 <= b <= 122:
            b -= 32
        out.append(chr(b) if 48 <= b <= 57 or 65 <= b <= 90 else "_")
    return "IMG_" + "".join(out)


_ERR_RX = re.compile(r"^(.*?)\((\d+)\)\s*(error|warning)\s*\d*(?:\(\d+\))?:\s*(.*)$", re.I)


def map_errors(text: str, main: Path, line_map: dict) -> list[str]:
    """fbc messages about the generated file -> 'File.bas(line): message' of the VB source."""
    out = []
    for raw in text.splitlines():
        m = _ERR_RX.match(raw.strip())
        if not m or m.group(3).lower() != "error":
            continue
        f, ln, msg = m.group(1), int(m.group(2)), m.group(4)
        if Path(f).name.lower() == main.name.lower():
            src = None
            for k in range(ln, 0, -1):
                if k in line_map:
                    src = line_map[k]
                    break
            where = f"{src[0]}({src[1]})" if src else f"{main.name}({ln})"
            out.append(f"{where}: FreeBASIC: {msg}")
        else:
            out.append(f"{Path(f).name}({ln}): FreeBASIC runtime: {msg}")
    return out[:20]


def build(folder, project, cfg, work, log):
    from ..build import BuildResult, data_entries
    folder = Path(folder)
    fbc = ensure_fbc(log)
    if not fbc:
        raise NativeUnsupported("FreeBASIC for Windows could not be downloaded")
    from .vb6fb import translate_project
    tr = translate_project(folder, project, str(Path(fbc).parent), cfg)
    if tr.reasons:
        raise NativeUnsupported(tr.reasons)
    gen = Path(work) / "native_vb6"
    shutil.rmtree(gen, ignore_errors=True)
    gen.mkdir(parents=True, exist_ok=True)
    for bi in RT_DIR.glob("*.bi"):
        shutil.copy2(bi, gen / bi.name)
    base = re.sub(r"[^\w\-]", "_", cfg.exe_base()) or "app"
    main = gen / f"{base}.bas"
    main.write_text(tr.source, encoding="utf-8")
    rc = _resources(folder, cfg, gen, tr.images, log, tr.icon)
    exe = gen / f"{base}.exe"
    cmd = [fbc, "-s", "gui", "-gen", "gcc", "-O", "2", "-Wc", "-Os", "-x", str(exe), main.name, rc.name]
    log("> " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd))
    try:
        p = subprocess.run(cmd, cwd=str(gen), capture_output=True, text=True, errors="replace", timeout=600,
                           creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as e:
        raise NativeUnsupported(f"fbc could not run: {e}") from None
    text = (p.stdout or "") + (p.stderr or "")
    for line in text.splitlines():
        if line.strip():
            log(line)
    if p.returncode != 0 or not exe.is_file():
        errs = map_errors(text, main, tr.line_map) or [f"fbc failed (exit code {p.returncode})"]
        raise NativeUnsupported(errs)
    dist = Path(work) / "dist" / cfg.exe_base()
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    final = dist / (cfg.exe_base() + ".exe")
    shutil.copy2(exe, final)
    embedded = {Path(i).parts[0].lower() for i in tr.images if i}
    for item in data_entries(folder, cfg, skip_ext=CODE_EXT):
        if item.name.lower() in embedded and item.is_file():
            continue
        if item.name in ("Publish",) or item.name.lower() == "_original_vb6":
            continue
        if item.is_dir():
            shutil.copytree(item, dist / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dist / item.name)
    size = final.stat().st_size
    log(f"Native exe: {final.name} - {size / 1024:.0f} KB, no Python (FreeBASIC source: {main})")
    return BuildResult(dist, final.name, "native", [f"Native exe without Python ({size // 1024} KB)."])


__all__ = ["LANGS", "NAME", "build", "check", "ensure_fbc", "find_fbc", "map_errors"]
