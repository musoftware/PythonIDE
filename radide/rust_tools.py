"""Rust toolchain helpers shared by the Rust features (no Qt in here).

* ``rust_analyzer()``         - the REAL rust-analyzer binary: ``rustup which rust-analyzer`` (the component of
                                the active toolchain), then ~/.rustup/toolchains/*/bin, then PATH. The
                                ``~/.cargo/bin/rust-analyzer.exe`` rustup proxy is only used when it works
                                (without the component it prints "Unknown binary" and exits).
* ``ra_initialization_options(root)`` - rust-analyzer settings used by radide/lsp.py (build scripts, proc
                                macros, check on save with clippy, inlay hints, own target dir so IDE builds
                                never wait on the analyzer's cargo lock).
* ``workspace_root(path)``    - the folder a single rust-analyzer serves (the cargo workspace root).
* ``cargo_metadata(root)``    - ``cargo metadata --no-deps`` (packages, targets, workspace members).
* GNU target (debugging with gdb): ``gnu_env()``, ``RUST_GNU``.
* ``crates_search(query)``    - crates.io API search (name, newest version, description, downloads).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

EXE = ".exe" if os.name == "nt" else ""
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RUST_GNU = "x86_64-pc-windows-gnu"
INSTALL_HINT = "rustup component add rust-analyzer rust-src"

_RA_CACHE: dict[str, tuple[float, str]] = {}


def rustup_home() -> Path:
    return Path(os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")))


def cargo_home() -> Path:
    return Path(os.environ.get("CARGO_HOME", str(Path.home() / ".cargo")))


def find_cargo() -> str:
    p = shutil.which("cargo")
    if p:
        return p
    c = cargo_home() / "bin" / ("cargo" + EXE)
    return str(c) if c.exists() else ""


def find_rustup() -> str:
    p = shutil.which("rustup")
    if p:
        return p
    c = cargo_home() / "bin" / ("rustup" + EXE)
    return str(c) if c.exists() else ""


def _run(argv: list[str], cwd=None, timeout: float = 20) -> tuple[int, str, str]:
    try:
        r = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", creationflags=NOWIN)
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def _works(exe: str) -> bool:
    code, out, _err = _run([exe, "--version"], timeout=15)
    return code == 0 and "rust-analyzer" in out


def rust_analyzer(refresh: bool = False) -> str:
    """Path of a working rust-analyzer, or "" (cached for a minute; refresh=True asks again)."""
    hit = _RA_CACHE.get("ra")
    if hit and not refresh and time.monotonic() - hit[0] < 60:
        return hit[1]
    found = ""
    override = os.environ.get("RADIDE_RUST_ANALYZER", "")
    if override and Path(override).is_file():
        found = override
    rustup = find_rustup()
    if not found and rustup:
        code, out, _err = _run([rustup, "which", "rust-analyzer"], timeout=15)
        cand = out.strip().splitlines()[-1].strip() if code == 0 and out.strip() else ""
        if cand and Path(cand).is_file():
            found = cand
    if not found:
        for cand in sorted(rustup_home().glob(f"toolchains/*/bin/rust-analyzer{EXE}"), reverse=True):
            if "stable" in cand.parts[-3]:
                found = str(cand)
                break
        else:
            cands = sorted(rustup_home().glob(f"toolchains/*/bin/rust-analyzer{EXE}"))
            found = str(cands[-1]) if cands else ""
    if not found:
        p = shutil.which("rust-analyzer")
        if p and _works(p):                       # the rustup proxy works only with the component installed
            found = p
    _RA_CACHE["ra"] = (time.monotonic(), found)
    return found


def rust_src_installed() -> bool:
    return any(rustup_home().glob("toolchains/*/lib/rustlib/src/rust/library/std"))


def install_rust_analyzer(log=print) -> bool:
    """rustup component add rust-analyzer rust-src (blocking - run it in a thread)."""
    rustup = find_rustup()
    if not rustup:
        log("rustup was not found - install Rust from https://rustup.rs")
        return False
    argv = [rustup, "component", "add", "rust-analyzer", "rust-src"]
    log("> " + " ".join(argv))
    code, out, err = _run(argv, timeout=900)
    log((out + err).strip())
    _RA_CACHE.clear()
    return code == 0 and bool(rust_analyzer(True))


# ---------------------------------------------------------------- settings
def _setting(key: str, default):
    try:
        from PyQt6.QtCore import QSettings
        v = QSettings().value(f"rust/{key}", default)
    except Exception:  # noqa: BLE001
        return default
    if isinstance(default, bool):
        return v in (True, "true", "1", 1)
    return v


def check_command() -> str:
    """'clippy' (default) or 'check' - what rust-analyzer runs on save."""
    return str(_setting("checkCommand", "clippy") or "clippy")


def inlay_hints_enabled() -> bool:
    return bool(_setting("inlayHints", True))


def format_on_save() -> bool:
    return bool(_setting("formatOnSave", False))


def ra_settings() -> dict:
    """The ``rust-analyzer`` settings object (initializationOptions and workspace/configuration)."""
    hints = inlay_hints_enabled()
    return {
        "cargo": {"buildScripts": {"enable": True}, "allTargets": True, "targetDir": True},
        "procMacro": {"enable": True, "attributes": {"enable": True}},
        "checkOnSave": True,
        "check": {"command": check_command(), "allTargets": True},
        "diagnostics": {"enable": True, "experimental": {"enable": False}},
        "completion": {"autoimport": {"enable": True}, "callable": {"snippets": "fill_arguments"},
                       "postfix": {"enable": True}, "fullFunctionSignatures": {"enable": True}},
        "imports": {"granularity": {"group": "module"}, "prefix": "plain"},
        "inlayHints": {"typeHints": {"enable": hints}, "parameterHints": {"enable": hints},
                       "chainingHints": {"enable": hints}, "closingBraceHints": {"enable": False},
                       "closureReturnTypeHints": {"enable": "never"}, "lifetimeElisionHints": {"enable": "never"},
                       "renderColons": True, "maxLength": 25},
        "hover": {"documentation": {"enable": True}, "actions": {"enable": False}},
        "lens": {"enable": False},
        "rustfmt": {"extraArgs": []},
        "files": {"excludeDirs": ["_build", ".radide", ".radide_backup"]},
    }


def ra_initialization_options(root=None) -> dict:
    return ra_settings()


# ---------------------------------------------------------------- cargo
def find_manifest(path) -> Path | None:
    """The nearest Cargo.toml at or above *path*."""
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        if (d / "Cargo.toml").is_file():
            return d / "Cargo.toml"
    return None


def _is_workspace_manifest(manifest: Path) -> bool:
    try:
        text = manifest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return re.search(r"^\s*\[workspace\]", text, re.M) is not None


def workspace_root(path) -> Path:
    """The cargo workspace root that contains *path* (the topmost Cargo.toml with [workspace] above the
    nearest manifest), else the nearest manifest's folder, else *path* itself."""
    p = Path(path).resolve()
    near = find_manifest(p)
    if near is None:
        return p if p.is_dir() else p.parent
    root = near.parent
    for d in near.parent.parents:
        m = d / "Cargo.toml"
        if m.is_file() and _is_workspace_manifest(m):
            root = d
    return root


_META_CACHE: dict[str, tuple[float, dict]] = {}


def cargo_metadata(root, refresh: bool = False) -> dict:
    """``cargo metadata --no-deps --format-version 1`` of the manifest in *root* ({} when cargo fails).
    Cached until a Cargo.toml under *root* changes."""
    root = Path(root).resolve()
    manifest = root / "Cargo.toml" if root.is_dir() else root
    key = os.path.normcase(str(manifest))
    stamp = 0.0
    try:
        stamp = manifest.stat().st_mtime
        for m in manifest.parent.glob("*/Cargo.toml"):
            stamp = max(stamp, m.stat().st_mtime)
        for m in manifest.parent.glob("*/*/Cargo.toml"):
            stamp = max(stamp, m.stat().st_mtime)
    except OSError:
        pass
    hit = _META_CACHE.get(key)
    if hit and not refresh and hit[0] == stamp:
        return hit[1]
    cargo = find_cargo()
    data: dict = {}
    if cargo and manifest.is_file():
        code, out, _err = _run([cargo, "metadata", "--no-deps", "--format-version", "1", "--manifest-path",
                                str(manifest)], cwd=manifest.parent, timeout=60)
        if code == 0:
            try:
                data = json.loads(out)
            except ValueError:
                data = {}
    if not data and manifest.is_file():
        data = _metadata_from_toml(manifest)
    _META_CACHE[key] = (stamp, data)
    return data


def _metadata_from_toml(manifest: Path) -> dict:
    """A small stand-in for cargo metadata when cargo is missing/broken (src/main.rs, src/bin, examples ...)."""
    try:
        import tomllib
        doc = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        doc = {}
    root = manifest.parent
    packages, members = [], []

    def pkg_of(mdir: Path, d: dict) -> dict:
        name = (d.get("package") or {}).get("name") or mdir.name
        targets = []
        if (mdir / "src" / "main.rs").exists():
            targets.append({"name": name, "kind": ["bin"], "src_path": str(mdir / "src" / "main.rs")})
        if (mdir / "src" / "lib.rs").exists():
            targets.append({"name": name.replace("-", "_"), "kind": ["lib"], "src_path": str(mdir / "src" / "lib.rs")})
        for kind, sub in (("bin", "src/bin"), ("example", "examples"), ("test", "tests"), ("bench", "benches")):
            for f in sorted((mdir / sub).glob("*.rs")):
                targets.append({"name": f.stem, "kind": [kind], "src_path": str(f)})
        deps = [{"name": k, "req": v if isinstance(v, str) else (v.get("version", "*") if isinstance(v, dict) else "*"),
                 "kind": None} for k, v in (d.get("dependencies") or {}).items()]
        pid = f"path+file:///{mdir.as_posix()}#{name}"
        return {"name": name, "version": (d.get("package") or {}).get("version", "0.0.0"), "id": pid,
                "manifest_path": str(mdir / "Cargo.toml"), "targets": targets, "dependencies": deps}
    if "package" in doc:
        p = pkg_of(root, doc)
        packages.append(p)
        members.append(p["id"])
    for pat in (doc.get("workspace") or {}).get("members", []):
        for mdir in sorted(root.glob(pat)):
            mf = mdir / "Cargo.toml"
            if mf.is_file():
                try:
                    import tomllib
                    d = tomllib.loads(mf.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    d = {}
                p = pkg_of(mdir, d)
                packages.append(p)
                members.append(p["id"])
    return {"packages": packages, "workspace_members": members, "workspace_root": str(root),
            "target_directory": str(root / "target")}


def target_dir(meta: dict, root) -> Path:
    return Path(meta.get("target_directory") or (Path(root) / "target"))


# ---------------------------------------------------------------- GNU target (gdb debugging)
def gnu_installed() -> bool:
    return any(rustup_home().glob(f"toolchains/*/lib/rustlib/{RUST_GNU}/lib"))


def mingw_gcc() -> str:
    try:
        from .bridgedebug import mingw_gcc as _gcc
        return _gcc() or ""
    except Exception:  # noqa: BLE001
        return shutil.which("x86_64-w64-mingw32-gcc") or shutil.which("gcc") or ""


def gnu_env() -> dict:
    """Environment that lets an MSVC-host rustup link the x86_64-pc-windows-gnu target with WinLibs gcc."""
    env: dict = {}
    if os.name != "nt":
        return env
    gcc = mingw_gcc()
    if gcc:
        env["CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER"] = gcc
        env["PATH"] = str(Path(gcc).parent) + os.pathsep + os.environ.get("PATH", "")
    return env


def debug_missing() -> str:
    """Why F5 cannot debug a Rust program here ('' = ready)."""
    try:
        from .bridgedebug import find_gdb
        gdb = find_gdb()
    except Exception:  # noqa: BLE001
        gdb = shutil.which("gdb") or ""
    if not gdb:
        return "gdb was not found (WinLibs in %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)"
    if os.name == "nt" and not gnu_installed():
        return f"the GNU target is missing: rustup target add {RUST_GNU}"
    if os.name == "nt" and not mingw_gcc():
        return "a MinGW gcc (WinLibs) is needed to link the GNU target"
    return ""


# ---------------------------------------------------------------- crates.io
def crates_search(query: str, per_page: int = 25) -> list[tuple[str, str, str]]:
    """(name, newest version, description) from the crates.io API (sorted by relevance)."""
    import urllib.parse
    import urllib.request
    url = ("https://crates.io/api/v1/crates?per_page=%d&q=%s" % (per_page, urllib.parse.quote(query)))
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE-crates-search", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for c in data.get("crates", []):
        desc = (c.get("description") or "").strip().replace("\n", " ")
        dl = c.get("downloads")
        if dl:
            desc = f"{desc}  ({dl:,} downloads)"
        out.append((c.get("name", ""), c.get("max_stable_version") or c.get("max_version") or "", desc))
    return out


# ---------------------------------------------------------------- cargo test output
TEST_LINE = re.compile(r"^test (\S+) \.\.\. (ok|FAILED|ignored)", re.M)


def parse_test_output(text: str) -> list[tuple[str, str]]:
    """[(test path, 'ok'|'FAILED'|'ignored')] from libtest output."""
    return TEST_LINE.findall(text)
