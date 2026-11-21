"""Virtual AGC toolchain for RAD IDE: yaYUL (the AGC assembler) and yaAGC (the AGC emulator).

Virtual AGC (https://www.ibiblio.org/apollo, https://github.com/virtualagc/virtualagc, GPL v2 or later, by
Ron Burkey and contributors) publishes no Windows binaries on its GitHub releases, so RAD IDE builds the two
programs from the official source with the MinGW-w64 gcc it already uses for C:

1. the file list of ``yaYUL/`` and ``yaAGC/`` (plus ``Tools/checkdec.c``) at the pinned commit comes from the
   GitHub API; every file is downloaded from raw.githubusercontent.com and checked against the git blob SHA-1
   the API reports (a changed file is refused); the SHA-256 of every file is written to ``manifest.json``;
2. ``gcc`` builds ``yaYUL.exe`` and ``yaAGC.exe`` into %LOCALAPPDATA%\\RADIDE\\tools\\virtualagc\\bin.

Everything is portable (no admin, no installer, no PATH change). The programs are used as external tools.

    python -m radide.agc.toolchain status
    python -m radide.agc.toolchain install        # download + build (what Tools > Apollo AGC > Virtual AGC does)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = "virtualagc/virtualagc"
COMMIT = "fdf0f05d19032575eb73143ab502fa77d4605788"        # 2026-10-24 (yaYUL / yaAGC unchanged since July)
API = "https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
SOURCE_DIRS = ["yaYUL", "yaAGC"]
EXTRA_FILES = ["Tools/checkdec.c", "LICENSE.txt"]
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

YAAGC_SOURCES = ["main.c", "agc_cli.c", "agc_simulator.c", "agc_debugger.c", "agc_gdbmi.c", "agc_disassembler.c",
                 "agc_help.c", "nbfgets.c", "agc_symtab.c", "NormalizeSourceName.c", "agc_engine_init.c",
                 "agc_engine.c", "agc_utilities.c", "rfopen.c", "Backtrace.c", "SocketAPI.c",
                 "DecodeDigitalDownlink.c", "../Tools/checkdec.c", "random.c", "regex.c"]


def root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "RADIDE" / "tools" / "virtualagc"


def bin_dir() -> Path:
    return root() / "bin"


def find(tool: str) -> str:
    """Path of yaYUL / yaAGC (RAD IDE's build first, then PATH, then a Virtual AGC installation), or ""."""
    name = {"yayul": "yaYUL", "yaagc": "yaAGC"}.get(tool.lower(), tool)
    p = bin_dir() / (name + EXE)
    if p.is_file():
        return str(p)
    w = shutil.which(name)
    if w:
        return w
    for base in (Path.home() / "VirtualAGC" / "bin", Path("C:/VirtualAGC/bin")):
        q = base / (name + EXE)
        if q.is_file():
            return str(q)
    return ""


def status() -> dict:
    man = root() / "manifest.json"
    info = {"yaYUL": find("yayul"), "yaAGC": find("yaagc"), "commit": "", "root": str(root())}
    if man.is_file():
        try:
            info["commit"] = json.loads(man.read_text(encoding="utf-8")).get("commit", "")
        except (OSError, ValueError):
            pass
    return info


def gcc() -> str:
    try:
        from ..languages.c_bridge import find_native
        return find_native(["gcc"])
    except Exception:  # noqa: BLE001
        return shutil.which("gcc") or ""


# ============================================================================ download
def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def list_dir(path: str, ref: str = COMMIT, repo: str = REPO) -> list[dict]:
    """[{name, path, sha, size, type}] of a repository folder at *ref* (GitHub contents API)."""
    data = json.loads(_get(API.format(repo=repo, path=path, ref=ref)).decode("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"{path}: not a folder")
    return [{"name": d["name"], "path": d["path"], "sha": d["sha"], "size": d.get("size", 0), "type": d["type"]}
            for d in data]


def fetch_file(entry: dict, dest: Path, ref: str = COMMIT, repo: str = REPO) -> str:
    """Download one file and check its git blob SHA-1; returns the SHA-256."""
    data = _get(RAW.format(repo=repo, ref=ref, path=entry["path"]), timeout=120)
    if entry.get("sha") and _blob_sha(data) != entry["sha"]:
        raise RuntimeError(f"{entry['path']}: content does not match the repository (git SHA {entry['sha'][:10]})")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def download_sources(log=print) -> Path:
    src = root() / "src"
    manifest = {"repo": REPO, "commit": COMMIT, "files": {}}
    entries = []
    for d in SOURCE_DIRS:
        log(f"Listing {d}/ at {COMMIT[:10]} ...")
        entries += [e for e in list_dir(d) if e["type"] == "file" and not e["name"].endswith((".tsv", ".py"))]
    for path in EXTRA_FILES:
        folder, _, name = path.rpartition("/")
        hit = next((e for e in list_dir(folder) if e["name"] == name), None)
        if hit is not None:
            entries.append(hit)
    for i, e in enumerate(entries, 1):
        sha = fetch_file(e, src / e["path"])
        manifest["files"][e["path"]] = sha
        if i % 10 == 0 or i == len(entries):
            log(f"  {i}/{len(entries)} files")
    (root() / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return src


# ============================================================================ build
def build_commands(src: Path, cc: str) -> list[tuple[str, list[str], Path]]:
    """(name, argv, working folder) for yaYUL and yaAGC."""
    out = bin_dir()
    yayul = sorted(p.name for p in (src / "yaYUL").glob("*.c"))
    nver = '-DNVER="rad-ide"'
    cmds = [("yaYUL", [cc, "-O2", "-w", nver, "-o", str(out / ("yaYUL" + EXE))] + yayul + ["-lm"], src / "yaYUL")]
    agc = [cc, "-O2", "-w", "-std=gnu99", "-fcommon", "-DGDBMI", "-DSTDC_HEADERS", nver,
           "-o", str(out / ("yaAGC" + EXE))]
    if os.name == "nt":
        agc.insert(3, "-DWIN32")
    agc += [f for f in YAAGC_SOURCES if os.name == "nt" or f != "regex.c"]
    agc += ["-lpthread", "-lm"] + (["-lws2_32"] if os.name == "nt" else [])
    cmds.append(("yaAGC", agc, src / "yaAGC"))
    return cmds


def build(src: Path | None = None, log=print) -> bool:
    src = Path(src or (root() / "src"))
    cc = gcc()
    if not cc:
        log("gcc was not found: install the MinGW-w64 toolchain of the C support first "
            "(%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64).")
        return False
    bin_dir().mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(Path(cc).parent) + os.pathsep + env.get("PATH", "")
    ok = True
    for name, argv, cwd in build_commands(src, cc):
        log(f"Building {name} ...")
        r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env, creationflags=NO_WINDOW)
        if r.returncode != 0:
            ok = False
            log(f"*** {name} failed:\n{(r.stderr or r.stdout)[-3000:]}")
        else:
            log(f"  {name} -> {bin_dir() / (name + EXE)}")
    if ok:
        (root() / "README_RADIDE.txt").write_text(
            "Virtual AGC (yaYUL, yaAGC) built by RAD IDE from the official source\n"
            f"https://github.com/{REPO} at commit {COMMIT}.\n"
            "Licence: GNU GPL v2 or later (see src/LICENSE.txt); the AGC flight software is public domain.\n"
            "Website: https://www.ibiblio.org/apollo\n", encoding="utf-8")
    return ok


def install(log=print) -> bool:
    try:
        src = download_sources(log)
    except Exception as e:  # noqa: BLE001 - network / GitHub errors are shown to the user
        log(f"*** Download failed: {e}")
        return False
    return build(src, log)


# ============================================================================ yaYUL errors
def parse_yayul_output(text: str) -> list[tuple[str, str, int, str]]:
    """(severity, file, line, message) from yaYUL's stderr (``FILE:LINE: Fatal Error: ...`` / ``Warning``)."""
    import re
    out = []
    for m in re.finditer(r"^(?P<file>[^:\n]+?):(?P<line>\d+):\s*(?P<sev>Fatal Error|Error|Warning):\s*(?P<msg>.*)$",
                         text, re.M):
        sev = "Warning" if m.group("sev") == "Warning" else "Error"
        out.append((sev, m.group("file").strip(), int(m.group("line")), m.group("msg").strip()))
    return out


def yayul_command(source: str, extra: str = "") -> list[str]:
    exe = find("yayul")
    return [exe] + (extra.split() if extra else []) + [source] if exe else []


def yaagc_command(rope: str, port: int = 19697, debug: bool = False, symtab: str = "") -> list[str]:
    exe = find("yaagc")
    if not exe:
        return []
    argv = [exe, f"--port={port}"]
    if debug:
        argv += ["--fullname"] + ([f"--symbols={symtab}"] if symtab else [])
    else:
        argv.append("--nodebug")
    return argv + [rope]


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "install":
        return 0 if install() else 1
    if cmd == "build":
        return 0 if build() else 1
    print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
