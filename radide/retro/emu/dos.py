"""Old MS-DOS programs and games in DOSBox-X, and legacy DOS development (no Qt in here).

* ``scan_dos_folder(folder)`` finds the DOS executables of a folder (MZ files that are not Windows programs,
  .COM, .BAT) and guesses the one to start (GAME.EXE / the only .EXE / INSTALL last ...).
* ``DosSettings`` is the ``"dos"`` block of a DOS Program's project.radproj (program, CPU cycles, memory,
  machine, sound card, extra mounts, build command); ``make_conf(...)`` writes a DOSBox-X .conf from it.
* ``dos_process(target)`` -> RetroProcess running DOSBox-X with that .conf (radide/retro/emu/launch.py).
* Legacy development: sources in Turbo Pascal / Free Pascal, Turbo C / Open Watcom C, QBasic / QuickBASIC and
  8086 assembly. RAD IDE does not ship any DOS compiler: NASM (free, BSD) builds .COM files on the host;
  for the others the user points the project at a folder with the compiler they own or a free one
  (Free Pascal go32v2 - GPL/LGPL, Open Watcom - Sybase Open Watcom Public Licence, FreeBASIC DOS - GPL); that
  folder is mounted as T: and the build runs inside DOSBox-X. ``LEGACY`` lists the commands used.

Nothing here touches the user's files except the generated ``.radide/dosbox-x.conf`` and build logs.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .manager import config_dir, find, missing_hint

SKIP_START = re.compile(r"^(install|setup|uninst|config|setsound|sound|patch|readme|catalog|order|deice|pkunzip|"
                        r"lha|arj|unzip|dos4gw|cwsdpmi|loadfix|himem|emm386)", re.I)
PREFER_START = re.compile(r"^(game|play|start|run|main|go)\b", re.I)

CYCLES = ["auto", "max", "fixed 3000", "fixed 8000", "fixed 20000", "fixed 50000"]
MACHINES = ["svga_s3", "vgaonly", "ega", "cga", "tandy", "hercules", "pcjr"]
SOUND = ["sb16", "sbpro2", "sb1", "gus", "none"]


@dataclass
class DosSettings:
    program: str = ""                   # relative path of the .EXE / .COM / .BAT to start ("" = DOS prompt)
    args: str = ""
    cycles: str = "auto"
    machine: str = "svga_s3"
    memsize: int = 16                   # MB
    sound: str = "sb16"
    gus: bool = False
    mounts: list = field(default_factory=list)   # [{"drive": "D", "path": "...", "type": "cdrom"|"dir"|"floppy"}]
    toolchain: str = ""                 # folder with a DOS compiler (mounted as T:)
    build: str = ""                     # DOS command line that builds the program (run before it)
    exit_after: bool = True             # leave DOSBox-X when the program ends
    fullscreen: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> "DosSettings":
        d = dict(d or {})
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        return asdict(self)


# ====================================================================== folder scan
def is_dos_mz(data: bytes) -> bool:
    """MZ executable without a Windows / OS2 (PE / NE / LE / LX) header."""
    if data[:2] not in (b"MZ", b"ZM"):
        return False
    if len(data) >= 0x40:
        off = int.from_bytes(data[0x3C:0x40], "little")
        if 0x40 <= off < len(data) - 2 and data[off:off + 2] in (b"PE", b"NE", b"LE", b"LX"):
            return False
    return True


def _head(p: Path, n: int = 0x10000) -> bytes:
    try:
        with open(p, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def scan_dos_folder(folder, max_depth: int = 2) -> dict:
    """{"exes": [...], "coms": [...], "bats": [...], "start": best guess, "sources": {kind: [...]},
    "windows_exes": n} - paths relative to *folder*, '/' separated."""
    folder = Path(folder)
    out = {"exes": [], "coms": [], "bats": [], "start": "", "sources": {}, "windows_exes": 0}
    base_depth = len(folder.parts)
    for p in sorted(folder.rglob("*")):
        if len(p.parts) - base_depth > max_depth + 1 or not p.is_file():
            continue
        if any(part.startswith(".radide") for part in p.parts[base_depth:]):
            continue
        rel = p.relative_to(folder).as_posix()
        ext = p.suffix.lower()
        if ext == ".exe":
            if is_dos_mz(_head(p)):
                out["exes"].append(rel)
            else:
                out["windows_exes"] += 1
        elif ext == ".com":
            out["coms"].append(rel)
        elif ext == ".bat":
            out["bats"].append(rel)
        kind = SOURCE_KINDS.get(ext)
        if kind:
            out["sources"].setdefault(kind, []).append(rel)
    out["start"] = guess_start(out["exes"] + out["coms"] + out["bats"])
    return out


def guess_start(programs: list) -> str:
    if not programs:
        return ""
    top = [p for p in programs if "/" not in p] or programs
    pref = [p for p in top if PREFER_START.match(Path(p).stem)]
    if pref:
        return pref[0]
    rest = [p for p in top if not SKIP_START.match(Path(p).stem)]
    exes = [p for p in rest if p.lower().endswith((".exe", ".com"))]
    return (exes or rest or top)[0]


def looks_like_dos_program(folder) -> tuple[float, dict]:
    """(confidence 0..1, scan) that *folder* is an old DOS program / game rather than a modern project."""
    info = scan_dos_folder(folder)
    n = len(info["exes"]) + len(info["coms"])
    if n == 0:
        return 0.0, info
    conf = 0.6 + min(0.3, 0.1 * n)
    if info["windows_exes"] > n:
        conf -= 0.4
    return max(0.0, min(conf, 0.92)), info


# ====================================================================== legacy development
SOURCE_KINDS = {".pas": "pascal", ".bas": "basic", ".c": "c", ".asm": "asm"}

# kind -> (title, [(tool exe, build command template)], notes). {src} = file name, {stem} = 8.3 stem.
LEGACY = {
    "pascal": ("Turbo Pascal / Free Pascal", [("TPC.EXE", "TPC {src}"), ("BPC.EXE", "BPC {src}"),
                                              ("PPC386.EXE", "PPC386 {src}"), ("FPC.EXE", "FPC {src}")],
               "Turbo Pascal 7 (yours) or Free Pascal for DOS (go32v2, free: freepascal.org)."),
    "c": ("Turbo C / Borland C / Open Watcom", [("TCC.EXE", "TCC {src}"), ("BCC.EXE", "BCC {src}"),
                                                ("WCL.EXE", "WCL -bt=dos {src}")],
          "Turbo C 2.01 / Borland C++ (yours) or Open Watcom (free: github.com/open-watcom)."),
    "basic": ("QBasic / QuickBASIC / FreeBASIC", [("QB.EXE", "QB /RUN {src}"), ("QBASIC.EXE", "QBASIC /RUN {src}"),
                                                  ("BC.EXE", "BC {src};"), ("FBC.EXE", "FBC {src}")],
              "QBasic / QuickBASIC (yours: Microsoft software, not redistributable) or FreeBASIC for DOS (free)."),
    "asm": ("8086 assembly", [("TASM.EXE", "TASM {src}"), ("MASM.EXE", "MASM {src};"), ("NASM.EXE", "NASM -f bin -o {stem}.COM {src}")],
            "NASM builds .COM files on Windows (downloaded by RAD IDE); TASM / MASM run inside DOSBox-X."),
}


def find_toolchain_exe(folder, kind: str) -> tuple[str, str]:
    """(relative exe path inside *folder*, build template) of the first compiler of *kind* found."""
    folder = Path(folder) if folder else None
    if not folder or not folder.is_dir():
        return "", ""
    files = {p.name.upper(): p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".exe"}
    for exe, tmpl in LEGACY.get(kind, ("", [], ""))[1]:
        if exe in files:
            return files[exe].relative_to(folder).as_posix(), tmpl
    return "", ""


def build_command(settings: DosSettings, source: str) -> tuple[str, str]:
    """(DOS commands that build *source* inside DOSBox-X, problem text). Uses settings.build when set."""
    src = Path(source)
    if settings.build:
        return settings.build.format(src=src.name.upper(), stem=src.stem.upper()[:8]), ""
    kind = SOURCE_KINDS.get(src.suffix.lower(), "")
    if not kind:
        return "", f"Do not know how to build {src.name}."
    exe, tmpl = find_toolchain_exe(settings.toolchain, kind)
    if not exe:
        title, _tools, note = LEGACY[kind]
        return "", (f"No {title} compiler found. Set the project's DOS toolchain folder (Project > DOS Settings) "
                    f"to a folder with one: {note}")
    tdir = str(Path(exe).parent).replace("/", "\\")
    path_cmd = f"SET PATH=T:\\{tdir};%PATH%" if tdir not in ("", ".") else "SET PATH=T:\\;%PATH%"
    return path_cmd + "\n" + tmpl.format(src=src.name.upper(), stem=src.stem.upper()[:8]), ""


def build_com_with_nasm(source, log=print) -> str:
    """Assemble an 8086 .asm into a .COM next to it with NASM on Windows ("" on failure)."""
    import subprocess
    try:
        from ...asm.toolchain import ensure
        nasm = ensure("nasm", log)
    except Exception as e:  # noqa: BLE001 - the assembly support is optional here
        log(f"NASM is not available: {e}")
        return ""
    if not nasm:
        return ""
    src = Path(source)
    out = src.with_suffix(".COM")
    r = subprocess.run([nasm, "-f", "bin", "-o", str(out), str(src)], capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        log((r.stderr or r.stdout).strip())
        return ""
    return str(out)


# ====================================================================== DOSBox-X configuration
def _q(path) -> str:
    return '"' + str(path).replace('"', '') + '"'


def make_conf(folder, settings: DosSettings, *, pre: str = "", log_file: str = "", title: str = "",
              output_redirect: str = "") -> str:
    """The text of a DOSBox-X .conf that mounts *folder* as C: and starts settings.program."""
    folder = Path(folder)
    lines = ["# generated by RAD IDE - DOS Program (edit Project > DOS Settings instead of this file)",
             "[sdl]", "autolock=false", f"fullscreen={'true' if settings.fullscreen else 'false'}",
             "showmenu=true", "", "[dosbox]", f"title={title or folder.name}", f"machine={settings.machine}",
             f"memsize={int(settings.memsize)}", "fastbioslogo=true", "startbanner=false", "", "[cpu]", "core=auto",
             "cputype=auto", f"cycles={settings.cycles}", "", "[sblaster]",
             f"sbtype={settings.sound if settings.sound.startswith('sb') else 'none'}", "", "[gus]",
             f"gus={'true' if settings.gus or settings.sound == 'gus' else 'false'}", "", "[speaker]",
             "pcspeaker=true", ""]
    if log_file:
        lines += ["[log]", f"logfile={log_file}", ""]
    auto = ["[autoexec]", "@echo off", f"mount c {_q(folder)}"]
    if settings.toolchain and Path(settings.toolchain).is_dir():
        auto.append(f"mount t {_q(settings.toolchain)}")
    for m in settings.mounts or []:
        drive, path, kind = str(m.get("drive", "D"))[:1].upper(), m.get("path", ""), m.get("type", "dir")
        if not path:
            continue
        if kind == "cdrom" and str(path).lower().endswith((".iso", ".cue")):
            auto.append(f"imgmount {drive} {_q(path)} -t iso")
        elif kind == "floppy" and str(path).lower().endswith((".img", ".ima")):
            auto.append(f"imgmount {drive} {_q(path)} -t floppy")
        else:
            auto.append(f"mount {drive} {_q(path)}" + (" -t cdrom" if kind == "cdrom" else ""))
    auto.append("c:")
    if pre:
        auto += pre.splitlines()
    prog = settings.program.replace("/", "\\")
    if prog:
        d, _, exe = prog.rpartition("\\")
        if d:
            auto.append(f"cd \\{d}")
        call = "call " if exe.lower().endswith(".bat") else ""
        auto.append(f"{call}{exe}" + (f" {settings.args}" if settings.args else "")
                    + (f" > {output_redirect}" if output_redirect else ""))
        if settings.exit_after:
            auto.append("exit")
    return "\n".join(lines + auto) + "\n"


def conf_path(folder) -> Path:
    d = Path(folder) / ".radide"
    d.mkdir(parents=True, exist_ok=True)
    return d / "dosbox-x.conf"


def write_conf(folder, settings: DosSettings, **kw) -> Path:
    p = conf_path(folder)
    p.write_text(make_conf(folder, settings, **kw), encoding="utf-8")
    return p


def dosbox_args(conf: Path, *, silent: bool = False, time_limit: int = 0) -> list:
    args = ["-conf", str(conf), "-nopromptfolder", "-fastlaunch"]
    if silent:
        args += ["-silent"]
    if time_limit:
        args += ["-time-limit", str(int(time_limit))]
    return args


def dos_process(target, debug: bool = False, settings: DosSettings | None = None, **opts):
    """RetroProcess running *target* (a DOS program file, or a folder with project.radproj's "dos" block)."""
    from .launch import EmuError, RetroProcess
    exe = find("dosbox-x")
    if not exe:
        raise EmuError(missing_hint("dosbox-x"))
    target = Path(target)
    if target.is_dir():
        folder = target
        if settings is None:
            settings = DosSettings.from_dict(_project_dos_block(folder))
            if not settings.program:
                settings.program = scan_dos_folder(folder)["start"]
    else:
        folder = target.parent
        settings = settings or DosSettings.from_dict(_project_dos_block(folder))
        settings.program = target.name
    for k in ("cycles", "machine", "memsize", "sound", "args", "exit_after"):
        if k in opts:
            setattr(settings, k, opts[k])
    conf = write_conf(folder, settings, pre=opts.get("pre", ""), output_redirect=opts.get("redirect", ""),
                      log_file=opts.get("log_file", ""))
    args = dosbox_args(conf, silent=bool(opts.get("silent")), time_limit=int(opts.get("time_limit", 0)))
    config_dir("dosbox-x")
    proc = RetroProcess("dosbox-x", exe, args, str(target), "dos", debug, cwd=str(Path(exe).parent),
                        minimized=bool(opts.get("minimized")))
    proc.conf = str(conf)
    return proc


def _project_dos_block(folder) -> dict:
    import json
    try:
        d = json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
        return d.get("dos") or {}
    except (OSError, ValueError):
        return {}


__all__ = ["CYCLES", "DosSettings", "LEGACY", "MACHINES", "SOUND", "build_com_with_nasm", "build_command",
           "conf_path", "dos_process", "dosbox_args", "find_toolchain_exe", "guess_start", "is_dos_mz",
           "looks_like_dos_program", "make_conf", "scan_dos_folder", "write_conf"]
