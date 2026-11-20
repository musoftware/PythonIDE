"""Lazarus projects (.lpi / .lpr) opened in place + the Free Pascal / Lazarus toolchain.

* ``read_lpi(path)``  - units, forms (.lfm), main source and the target of a Lazarus project.
* Toolchain: ``find_lazarus()``, ``find_fpc()``, ``find_delphi()`` and ``install_toolchain()`` which
  downloads the official Lazarus + FPC Windows installer from SourceForge and unpacks it with
  innoextract (portable, no admin, nothing registered) into ``%LOCALAPPDATA%\\RADIDE\\toolchains\\lazarus``.
* ``build(info)`` / ``run(info)``: ``lazbuild`` for .lpi projects, ``fpc -Mdelphi`` for VCL-free Delphi
  programs, ``dcc32/dcc64`` when a Delphi installation is present. VCL/FMX applications cannot be
  built without Delphi (reported, with the migration offer).

Command line (used by the IDE's Run, output goes to the Output window)::

    python -m radide.foreign.lazarus run   <project file> [args...]
    python -m radide.foreign.lazarus build <project file>
    python -m radide.foreign.lazarus install
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LAZARUS_VERSION = "4.8"
FPC_VERSION = "3.2.2"
INSTALLER = f"lazarus-{LAZARUS_VERSION}-fpc-{FPC_VERSION}-win64.exe"
INSTALLER_URL = ("https://sourceforge.net/projects/lazarus/files/Lazarus%20Windows%2064%20bits/"
                 f"Lazarus%20{LAZARUS_VERSION}/{INSTALLER}/download")
INNOEXTRACT_URL = "https://github.com/dscharrer/innoextract/releases/download/1.9/innoextract-1.9-windows.zip"


def _local() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RADIDE"


def toolchain_dir() -> Path:
    return _local() / "toolchains" / "lazarus"


# =============================================================================== project file

def read_lpi(path: Path):
    """PascalProjectInfo of a Lazarus .lpi file."""
    from .delphi import PascalProjectInfo, make_units
    path = Path(path).resolve()
    root = ET.parse(path).getroot()
    po = root.find("ProjectOptions")
    if po is None:
        raise ValueError(f"{path.name} is not a Lazarus project (no ProjectOptions)")
    title = _val(po.find("General/Title")) or path.stem
    files: list[str] = []
    forms: dict[str, str] = {}
    units = po.find("Units")
    for u in (list(units) if units is not None else []):
        fn = _val(u.find("Filename"))
        if not fn:
            continue
        part = _val(u.find("IsPartOfProject"))
        if part and part.lower() != "true":
            continue
        files.append(fn)
        cn = _val(u.find("ComponentName"))
        if cn:
            forms[fn.lower()] = cn
    main = next((f for f in files if f.lower().endswith((".lpr", ".dpr", ".pp", ".pas")) and
                 not forms.get(f.lower()) and f.lower().endswith((".lpr", ".dpr"))), "")
    if not main:
        main = next((f for f in files if f.lower().endswith((".lpr", ".dpr"))), path.stem + ".lpr")
    target = ""
    co = root.find("CompilerOptions")
    if co is not None:
        target = _val(co.find("Target/Filename"))
    info = PascalProjectInfo("lazarus", path, (path.parent / main).resolve(), path.stem, title=title,
                             target=target)
    info.units, info.others = make_units(path.parent, [f for f in files if f != main], lazarus=True)
    info.main_form = _main_form(info)
    return info


def read_lpr(path: Path):
    """A bare .lpr (no .lpi next to it): its uses clause (``unit in 'file'`` and units of the folder)."""
    from .delphi import read_program
    lpi = Path(path).with_suffix(".lpi")
    if lpi.is_file():
        return read_lpi(lpi)
    return read_program(Path(path), "lazarus")


def _val(el) -> str:
    return el.get("Value", "") if el is not None else ""


def _main_form(info) -> str:
    try:
        src = info.main_source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return info.units[0].key if info.units else ""
    m = re.search(r"Application\.CreateForm\s*\(\s*\w+\s*,\s*(\w+)\s*\)", src, re.I)
    if m:
        for u in info.units:
            if u.form_name.lower() == m.group(1).lower():
                return u.key
    return info.units[0].key if info.units else ""


# =============================================================================== toolchain

def find_lazarus() -> Path | None:
    """Folder of a Lazarus installation (lazbuild.exe)."""
    cands = [toolchain_dir()]
    lb = shutil.which("lazbuild")
    if lb:
        cands.insert(0, Path(lb).parent)
    cands += [Path(r"C:\lazarus"), Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Lazarus"]
    for c in cands:
        if (c / "lazbuild.exe").is_file() or (c / "lazbuild").is_file():
            return c
    return None


def find_fpc() -> Path | None:
    exe = shutil.which("fpc")
    if exe and "\\WindowsApps\\" not in exe:
        return Path(exe)
    laz = find_lazarus()
    roots = ([laz / "fpc"] if laz else []) + [Path(r"C:\FPC")]
    for r in roots:
        for f in sorted(r.glob("*/bin/*/fpc.exe"), reverse=True):
            return f
    return None


def find_delphi() -> Path | None:
    """dcc64/dcc32 of an installed Delphi (PATH, then the BDS registry keys)."""
    for name in ("dcc64", "dcc32"):
        exe = shutil.which(name)
        if exe:
            return Path(exe)
    if sys.platform == "win32":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for base in (r"Software\Embarcadero\BDS", r"Software\WOW6432Node\Embarcadero\BDS"):
                    try:
                        k = winreg.OpenKey(hive, base)
                    except OSError:
                        continue
                    vers = []
                    i = 0
                    while True:
                        try:
                            vers.append(winreg.EnumKey(k, i))
                        except OSError:
                            break
                        i += 1
                    for v in sorted(vers, key=lambda s: [int(x) for x in re.findall(r"\d+", s)], reverse=True):
                        try:
                            root = winreg.QueryValueEx(winreg.OpenKey(k, v), "RootDir")[0]
                        except OSError:
                            continue
                        for name in ("dcc64.exe", "dcc32.exe"):
                            p = Path(root) / "bin" / name
                            if p.is_file():
                                return p
        except Exception:  # noqa: BLE001
            pass
    return None


def toolchain_status() -> str:
    laz, fpc, dcc = find_lazarus(), find_fpc(), find_delphi()
    return (f"Lazarus: {laz or 'not found'}\nFree Pascal: {fpc or 'not found'}\n"
            f"Delphi compiler: {dcc or 'not found (Delphi is a commercial product - not downloadable)'}")


def _download(url: str, dest: Path, log) -> None:
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    if have:
        req.add_header("Range", f"bytes={have}-")
    with urllib.request.urlopen(req, timeout=60) as r:
        mode = "ab" if have and r.status == 206 else "wb"
        total = int(r.headers.get("Content-Length") or 0) + (have if mode == "ab" else 0)
        done = have if mode == "ab" else 0
        step = 0
        with open(part, mode) as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total and done * 10 // total > step:
                    step = done * 10 // total
                    log(f"  {done >> 20} / {total >> 20} MB")
    part.replace(dest)


def install_toolchain(log=print) -> Path:
    """Download + unpack Lazarus/FPC (portable). Returns the Lazarus folder."""
    target = toolchain_dir()
    if (target / "lazbuild.exe").is_file():
        _configure(target, log)
        return target
    dl = _local() / "tools" / "_download" / "lazarus"
    inst = dl / INSTALLER
    if not inst.is_file() or inst.stat().st_size < 100_000_000:
        log(f"Downloading {INSTALLER} (about 220 MB) from SourceForge ...")
        _download(INSTALLER_URL, inst, log)
    ie = _local() / "tools" / "innoextract" / "innoextract.exe"
    if not ie.is_file():
        log("Downloading innoextract ...")
        z = ie.parent / "innoextract.zip"
        _download(INNOEXTRACT_URL, z, log)
        import zipfile
        with zipfile.ZipFile(z) as zf:
            zf.extractall(ie.parent)
    tmp = target.parent / "_lazarus_extract"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    log("Checking and unpacking the installer (innoextract) ...")
    r = subprocess.run([str(ie), "-s", "-d", str(tmp), str(inst)], capture_output=True, text=True)
    if r.returncode != 0 or not (tmp / "app" / "lazbuild.exe").is_file():
        raise RuntimeError(f"innoextract failed: {r.stderr or r.stdout}")
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.move(str(tmp / "app"), str(target))
    shutil.rmtree(tmp, ignore_errors=True)
    _configure(target, log)
    log(f"Lazarus {LAZARUS_VERSION} + FPC {FPC_VERSION} ready in {target}")
    return target


def _configure(laz: Path, log=print) -> None:
    """What the installer would do: fpc.cfg next to fpc.exe and a private Lazarus config folder."""
    fpc = next(iter(sorted((laz / "fpc").glob("*/bin/*/fpc.exe"))), None)
    if fpc is None:
        raise RuntimeError(f"fpc.exe not found under {laz / 'fpc'}")
    cfg = fpc.parent / "fpc.cfg"
    if not cfg.is_file():
        base = fpc.parent.parent.parent                      # ...\fpc\3.2.2
        mk = fpc.parent / "fpcmkcfg.exe"
        r = subprocess.run([str(mk), "-d", f"basepath={base}", "-o", str(cfg)], capture_output=True, text=True)
        if r.returncode != 0 or not cfg.is_file():
            cfg.write_text(f"-Fu{base}\\units\\$fpctarget\n-Fu{base}\\units\\$fpctarget\\*\n"
                           f"-Fu{base}\\units\\$fpctarget\\rtl\n-FD{fpc.parent}\n", encoding="ascii")
        log(f"Wrote {cfg}")
    pcp = laz / "config"
    env = pcp / "environmentoptions.xml"
    if not env.is_file():
        pcp.mkdir(parents=True, exist_ok=True)
        text = (laz / "environmentoptions.xml").read_text(encoding="utf-8") if \
            (laz / "environmentoptions.xml").is_file() else ""
        if not text:
            text = ('<?xml version="1.0"?>\n<CONFIG>\n  <EnvironmentOptions>\n'
                    '    <LazarusDirectory Value="%LazDir%"/>\n    <CompilerFilename Value="%FpcBinDir%\\fpc.exe"/>\n'
                    '  </EnvironmentOptions>\n</CONFIG>\n')
        text = text.replace("%LazDir%", str(laz)).replace("%FpcBinDir%", str(fpc.parent)) \
            .replace("%Temp%", os.environ.get("TEMP", str(laz)))
        env.write_text(text, encoding="utf-8")


# =============================================================================== build / run

def _say(log, text: str) -> None:
    log(text)


def build(info, log=print) -> Path | None:
    """Build a PascalProjectInfo. Returns the executable or None (the reason is logged)."""
    if info.kind == "lazarus" and info.file.suffix.lower() == ".lpi":
        return _build_lazbuild(info, log)
    if info.kind == "delphi":
        dcc = find_delphi()
        if dcc is not None:
            return _build_dcc(info, dcc, log)
        if info.uses_vcl():
            _say(log, f"*** {info.name} is a Delphi {info.framework or 'VCL'} application: it needs Delphi "
                      "(Embarcadero) to build, which is not installed.\n"
                      "    Use Pascal > Migrate Delphi project to Lazarus (or File > Migrate...) to get a copy "
                      "that the free Lazarus compiler builds.")
            return None
    return _build_fpc(info, log)


def _run(cmd: list[str], cwd: Path, log) -> int:
    _say(log, "> " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for raw in p.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            _say(log, line)
    return p.wait()


def _build_lazbuild(info, log) -> Path | None:
    laz = find_lazarus()
    if laz is None:
        _say(log, "*** lazbuild was not found. Pascal > Download Free Pascal + Lazarus installs it "
                  "(portable, about 220 MB).")
        return None
    fpc = find_fpc()
    cmd = [str(laz / "lazbuild.exe")]
    if (laz / "config").is_dir():
        cmd.append(f"--pcp={laz / 'config'}")
    cmd.append(f"--lazarusdir={laz}")
    if fpc is not None:
        cmd.append(f"--compiler={fpc}")
    cmd.append(str(info.file))
    if _run(cmd, info.file.parent, log) != 0:
        _say(log, "*** Build failed")
        return None
    return _find_exe(info)


def _find_exe(info) -> Path | None:
    folder = info.file.parent
    if info.target:
        t = info.target.replace("$(TargetCPU)", "x86_64").replace("$(TargetOS)", "win64")
        p = (folder / t)
        for cand in (p, p.with_suffix(".exe")) if p.suffix.lower() != ".exe" else (p,):
            if cand.is_file():
                return cand
    stem = info.main_source.stem
    for cand in (folder / f"{stem}.exe", folder / f"{info.file.stem}.exe"):
        if cand.is_file():
            return cand
    exes = sorted(folder.rglob("*.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
    return exes[0] if exes else None


_NS_RX = re.compile(r"\b(?:System|Winapi|Vcl|Data|Xml|Soap|Web|Datasnap)\.(\w+(?:\.\w+)*)\b")
_NS_KEEP = {"Generics.Collections": "Generics.Collections", "Generics.Defaults": "Generics.Defaults"}


def _strip_namespaces(text: str) -> str:
    """FPC 3.2 has no unit scopes: System.SysUtils -> SysUtils (only inside uses clauses)."""
    def fix_uses(m):
        body = _NS_RX.sub(lambda n: _NS_KEEP.get(n.group(1), n.group(1).split(".")[-1]
                                                  if not n.group(1).startswith("Generics") else n.group(1)),
                          m.group(2))
        return m.group(1) + body + ";"
    return re.sub(r"(\buses\b)(.*?);", fix_uses, text, flags=re.I | re.S)


def _build_fpc(info, log) -> Path | None:
    fpc = find_fpc()
    if fpc is None:
        _say(log, "*** Free Pascal (fpc) was not found. Pascal > Download Free Pascal + Lazarus installs it "
                  "(portable, about 220 MB).")
        return None
    from .delphi import state_dir
    work = state_dir(info.file) / "fpcbuild"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    src_dir = info.main_source.parent
    copied = []
    for f in [info.main_source] + [u.pas for u in info.units] + list(info.others):
        if f.suffix.lower() in (".pas", ".pp", ".dpr", ".lpr", ".inc") and f.is_file():
            t = f.read_bytes().decode("utf-8", errors="replace") if _is_utf8(f) else \
                f.read_bytes().decode("cp1252", errors="replace")
            (work / f.name).write_text(_strip_namespaces(t), encoding="utf-8")
            copied.append(f.name)
    for inc in src_dir.glob("*.inc"):
        if inc.name not in copied:
            shutil.copy2(inc, work / inc.name)
    for res in src_dir.glob("*.res"):
        shutil.copy2(res, work / res.name)
    out = src_dir / ("Win64" if info.kind == "delphi" else "") / ("Debug" if info.kind == "delphi" else "")
    out.mkdir(parents=True, exist_ok=True)
    mode = "-Mdelphi" if info.kind == "delphi" else "-Mobjfpc"
    cmd = [str(fpc), mode, "-Sh" if info.kind == "delphi" else "-Sh", f"-FE{out}", f"-FU{work}",
           f"-Fu{work}", f"-Fi{work}", "-g", str(work / info.main_source.name)]
    if not any((work / r.name).exists() for r in src_dir.glob("*.res")):
        # {$R *.res} needs a resource file: create an empty one
        txt = (work / info.main_source.name).read_text(encoding="utf-8")
        if re.search(r"\{\$R\s+\*\.res\}", txt, re.I):
            (work / (info.main_source.stem + ".res")).write_bytes(
                b"\x00\x00\x00\x00\x20\x00\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00" + b"\x00" * 16)
    if _run(cmd, work, log) != 0:
        _say(log, "*** Build failed")
        return None
    exe = out / (info.main_source.stem + ".exe")
    return exe if exe.is_file() else None


def _is_utf8(p: Path) -> bool:
    try:
        p.read_bytes().decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _build_dcc(info, dcc: Path, log) -> Path | None:
    cmd = [str(dcc), "-B", "-NSSystem;Xml;Data;Datasnap;Web;Soap;Winapi;Vcl;Vcl.Imaging;Vcl.Samples",
           str(info.main_source)]
    if _run(cmd, info.main_source.parent, log) != 0:
        _say(log, "*** Build failed")
        return None
    exe = info.main_source.with_suffix(".exe")
    return exe if exe.is_file() else _find_exe(info)


def load_info(path: Path):
    from .delphi import load_project_info
    return load_project_info(Path(path))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

    def log(t):
        print(t, flush=True)
    if cmd == "install":
        install_toolchain(log)
        print(toolchain_status())
        return 0
    if cmd == "status":
        print(toolchain_status())
        return 0
    if cmd in ("build", "run") and len(argv) >= 2:
        info = load_info(Path(argv[1]))
        exe = build(info, log)
        if exe is None:
            return 1
        log(f"Built {exe}")
        if cmd == "build":
            return 0
        log(f"------ Running {exe.name} ------")
        r = subprocess.run([str(exe)] + argv[2:], cwd=str(exe.parent))
        log(f"------ {exe.name} exited with code {r.returncode} ------")
        return r.returncode
    print(__doc__)
    return 2


def register() -> None:
    from ..features.foreign_projects import register_format
    from .delphi import open_pascal, probe_lazarus
    register_format([".lpi", ".lpr"], open_pascal, "Lazarus project", folder_probe=probe_lazarus,
                    name="lazarus", priority=5)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
