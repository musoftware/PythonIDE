"""Language servers that live in the IDE's private tools folder (no admin, no system PATH changes).

radide/lsp.py asks ``server_command(language)`` first; when it returns an argv the server is used,
with ``server_env(language)`` added to its environment. Everything is portable and installed under
``%LOCALAPPDATA%\\RADIDE\\tools\\<tool>`` by ``install(language)`` (Tools > Language Servers...):

    go          gopls                     go install golang.org/x/tools/gopls@latest   (GOBIN = tools\\gopls)
    ruby        ruby-lsp (or solargraph)  gem install ruby-lsp   (GEM_HOME = tools\\ruby-gems)
    lua         lua-language-server       official GitHub release zip (sha256 checked)  -> tools\\lua-language-server
    powershell  PowerShell Editor Services official GitHub release zip (sha256 checked) -> tools\\pses (LSP + DAP)
    perl        PLS (Perl Language Server) cpanm PLS into tools\\perl-pls (Linux / macOS only: PLS needs fork(), missing on Windows)
                (toolchains\\strawberry, portable zip) - or Perl::LanguageServer when found on PATH

The Go / Ruby / Perl toolchains are looked up on PATH first, then in ``%LOCALAPPDATA%\\RADIDE\\toolchains``.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

LOCAL = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"
TOOLS = LOCAL / "tools"
TOOLCHAINS = LOCAL / "toolchains"
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

GOPLS_DIR = TOOLS / "gopls"
GEM_HOME = TOOLS / "ruby-gems"
LUA_LS_DIR = TOOLS / "lua-language-server"
PSES_DIR = TOOLS / "pses"
PERL_LS_DIR = TOOLS / "perl-pls"

# official release archives (pinned: version, URL, sha256 published on the GitHub release page)
RELEASES = {
    "lua": ("3.19.2", "https://github.com/LuaLS/lua-language-server/releases/download/3.19.2/"
                      "lua-language-server-3.19.2-win32-x64.zip",
            "4a3dc851b3b31e7b75a23f645d1ba4a2137579a55f5fa4edbb17a3e2a6254044"),
    "powershell": ("v4.7.0", "https://github.com/PowerShell/PowerShellEditorServices/releases/download/v4.7.0/"
                             "PowerShellEditorServices.zip",
                   "5084f0326cc88539e9d880b08f6c52ce5be4672bb8ecee8921e35f8895a6b9d7"),
}

NAMES = {"go": "gopls", "ruby": "ruby-lsp", "lua": "lua-language-server",
         "powershell": "PowerShell Editor Services", "perl": "PLS (Perl Language Server)",
         "asm": "asm-lsp"}          # assembly (rad-asm-* editors): radide/asm_intel/lsp.py


# ====================================================================== toolchains
def _which(*names: str) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return ""


def _first(*paths: Path) -> str:
    for p in paths:
        if p.is_file():
            return str(p)
    return ""


def find_go() -> str:
    return _which("go") or _first(TOOLCHAINS / "go" / "bin" / ("go" + EXE))


def find_ruby() -> str:
    return _which("ruby") or _first(TOOLCHAINS / "ruby" / "bin" / ("ruby" + EXE))


def find_perl() -> str:
    """A native Windows perl (Strawberry); Git's MSYS perl cannot build CPAN modules."""
    return _first(TOOLCHAINS / "strawberry" / "perl" / "bin" / ("perl" + EXE)) or _which("perl") or \
        _first(Path(r"C:\Strawberry\perl\bin\perl.exe"))


def find_powershell() -> str:
    """pwsh (PowerShell 7) when installed, else Windows PowerShell 5.1 (PSES supports both)."""
    return _which("pwsh") or _first(TOOLS / "pwsh" / ("pwsh" + EXE)) or _which("powershell") or \
        _first(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" /
               "powershell.exe")


def ruby_default_gem_dir(ruby: str) -> str:
    try:
        r = subprocess.run([ruby, "-e", "print Gem.default_dir"], capture_output=True, text=True, timeout=30,
                           creationflags=NO_WINDOW)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def gem_env(ruby: str = "") -> dict:
    """GEM_HOME = the IDE's private gem folder; GEM_PATH also keeps the toolchain's bundled gems
    (rbs, prism, debug ship precompiled with RubyInstaller - nothing needs a C compiler)."""
    ruby = ruby or find_ruby()
    paths = [str(GEM_HOME)]
    d = ruby_default_gem_dir(ruby) if ruby else ""
    if d:
        paths.append(d)
    env = {"GEM_HOME": str(GEM_HOME), "GEM_PATH": os.pathsep.join(paths)}
    if ruby:
        env["PATH"] = str(Path(ruby).parent) + os.pathsep + os.environ.get("PATH", "")
    return env


# ====================================================================== servers
def find_gopls() -> str:
    return _which("gopls") or _first(GOPLS_DIR / ("gopls" + EXE), Path.home() / "go" / "bin" / ("gopls" + EXE))


def find_lua_ls() -> str:
    return _which("lua-language-server") or _first(LUA_LS_DIR / "bin" / ("lua-language-server" + EXE))


def find_pses() -> str:
    """Start-EditorServices.ps1 of PowerShell Editor Services ('' = not installed)."""
    return _first(PSES_DIR / "PowerShellEditorServices" / "Start-EditorServices.ps1")


def find_pls() -> str:
    """PLS script (bin/pls) installed by cpanm into PERL_LS_DIR."""
    return _first(PERL_LS_DIR / "bin" / "pls")


def _ruby_script(name: str) -> str:
    return _first(GEM_HOME / "bin" / name)


# PSES needs a console of its own (QProcess starts children without one on Windows): its attach
# (Enter-PSHostProcess) hangs and the language server stops answering after initialize. The relay starts it in a new, hidden console and copies the
# DAP bytes between its own stdin/stdout and PSES.
PSES_RELAY = r"""
import subprocess, sys, threading
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 0
p = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)
try:                       # PSES dies with the relay (job object, kill on close) - no orphans
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.OpenProcess.restype = wintypes.HANDLE
    class LIMIT(ctypes.Structure):
        _fields_ = [("a", ctypes.c_int64), ("b", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                    ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]
    class EXT(ctypes.Structure):
        _fields_ = [("basic", LIMIT), ("io", ctypes.c_uint64 * 6), ("p1", ctypes.c_size_t),
                    ("p2", ctypes.c_size_t), ("p3", ctypes.c_size_t), ("p4", ctypes.c_size_t)]
    job = k.CreateJobObjectW(None, None)
    info = EXT()
    info.basic.LimitFlags = 0x2000
    k.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    h = k.OpenProcess(0x0101, False, p.pid)
    k.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(h))
except Exception:
    pass
def up():
    try:
        while True:
            b = sys.stdin.buffer.read1(65536)
            if not b:
                break
            p.stdin.write(b)
            p.stdin.flush()
    except OSError:
        pass
    try:
        p.stdin.close()
    except OSError:
        pass
threading.Thread(target=up, daemon=True).start()
while True:
    b = p.stdout.read1(65536)
    if not b:
        break
    sys.stdout.buffer.write(b)
    sys.stdout.buffer.flush()
sys.exit(p.wait())
"""


def pses_args(stdio_mode: str = "-Stdio", session_file: Path | None = None) -> list[str]:
    """powershell argv that starts PSES (language server: -Stdio; debug adapter: -Stdio -DebugServiceOnly)."""
    logs = TOOLS / "pses" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    session_file = session_file or logs / f"session-{os.getpid()}.json"
    args = [find_powershell(), "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", find_pses(), "-HostName", "RAD IDE", "-HostProfileId", "RADIDE", "-HostVersion", "1.0.0",
            "-BundledModulesPath", str(PSES_DIR), "-LogPath", str(logs / "pses.log"), "-LogLevel", os.environ.get("RADIDE_PSES_LOGLEVEL", "Warning"),
            "-SessionDetailsPath", str(session_file), "-FeatureFlags", "@()"]
    return args + stdio_mode.split()


def server_command(language: str) -> list[str] | None:
    """argv of the server for *language* found in the IDE's tools folder (or PATH), else None."""
    if language == "asm" or language.startswith("rad-asm"):
        from .asm_intel import lsp as asm_lsp
        return asm_lsp.server_command()
    if language == "go":
        p = find_gopls()
        return [p] if p else None
    if language == "lua":
        p = find_lua_ls()
        return [p] if p else None
    if language == "ruby":
        ruby = find_ruby()
        for name, extra in (("ruby-lsp", []), ("solargraph", ["stdio"])):
            s = _ruby_script(name)
            if s and ruby:
                return [ruby, s, *extra]
        p = _which("ruby-lsp")
        if p:
            return [p]
        p = _which("solargraph")
        return [p, "stdio"] if p else None
    if language == "powershell":
        if find_pses() and find_powershell():
            argv = pses_args("-Stdio")
            return [sys.executable, "-u", "-c", PSES_RELAY, *argv] if os.name == "nt" else argv
        return None
    if language == "perl":
        perl = find_perl()
        if os.name == "nt":                  # PLS / Perl::LanguageServer need fork(): not on Windows
            return None
        if perl and find_pls():
            return [perl, find_pls()]
        p = _which("pls")
        if p:
            return [p]
        if perl and _perl_has(perl, "Perl::LanguageServer"):
            return [perl, "-MPerl::LanguageServer", "-e", "Perl::LanguageServer::run"]
        return None
    return None


_PERL_MODS: dict[tuple[str, str], bool] = {}


def _perl_has(perl: str, module: str) -> bool:
    key = (perl, module)
    if key not in _PERL_MODS:
        try:
            r = subprocess.run([perl, f"-M{module}", "-e", "1"], capture_output=True, timeout=20,
                               creationflags=NO_WINDOW)
            _PERL_MODS[key] = r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            _PERL_MODS[key] = False
    return _PERL_MODS[key]


def server_env(language: str) -> dict | None:
    """Extra environment variables for the server process (None = none)."""
    if language == "ruby":
        return gem_env()
    if language == "perl" and find_pls():
        lib = PERL_LS_DIR / "lib" / "perl5"
        perl = find_perl()
        env = {"PERL5LIB": str(lib) + os.pathsep + os.environ.get("PERL5LIB", "")}
        if perl:
            env["PATH"] = str(Path(perl).parent) + os.pathsep + os.environ.get("PATH", "")
        return env
    if language == "go":
        go = find_go()
        if go and not shutil.which("go"):    # gopls runs `go list` / `go env`: give it the private toolchain
            return {"PATH": str(Path(go).parent) + os.pathsep + os.environ.get("PATH", ""), "GOTOOLCHAIN": "local"}
    return None


def initialization_options(language: str) -> dict:
    if language == "powershell":
        return {"enableProfileLoading": False}
    return {}


def workspace_settings() -> dict:
    """workspace/configuration answers (by section) for these servers."""
    return {
        "Lua": {"runtime": {"version": "Lua 5.4"}, "diagnostics": {"globals": ["radcall", "Form", "Me"]},
                "telemetry": {"enable": False}, "workspace": {"checkThirdParty": False}},
        "powershell": {"scriptAnalysis": {"enable": True}, "codeFormatting": {"preset": "OTBS"}},
        "gopls": {"ui.semanticTokens": False},
    }


# ====================================================================== status / install
def status() -> list[dict]:
    """[{language, name, found (argv or None), hint, installable}] for the Language Servers dialog."""
    out = []
    for lang in ("go", "ruby", "lua", "powershell", "perl", "asm"):
        argv = server_command(lang)
        out.append({"language": lang, "name": NAMES[lang], "found": argv, "hint": install_hint(lang),
                    "installable": can_install(lang)})
    return out


def install_hint(language: str) -> str:
    return {
        "go": "go install golang.org/x/tools/gopls@latest (needs Go: toolchains\\go)",
        "ruby": "gem install ruby-lsp into tools\\ruby-gems (needs Ruby: toolchains\\ruby)",
        "lua": "official lua-language-server release zip -> tools\\lua-language-server",
        "powershell": "official PowerShellEditorServices release zip -> tools\\pses",
        "perl": "cpanm PLS into tools\\perl-pls (Linux / macOS - PLS needs fork())",
        "asm": "cargo install asm-lsp (official crate) into tools\\asm-lsp - the built-in assembly IntelliSense "
               "works without it",
    }.get(language, "")


def can_install(language: str) -> str:
    """'' when install(language) can run here, else the reason it cannot."""
    if language == "asm":
        from .asm_intel import lsp as asm_lsp
        return asm_lsp.can_install()
    if language == "go":
        return "" if find_go() else "Go was not found"
    if language == "ruby":
        return "" if find_ruby() else "Ruby was not found"
    if language == "perl":
        perl = find_perl()
        if os.name == "nt":
            return "PLS needs fork(), which Windows perl lacks - the Perl plugin's IntelliSense is used"
        return "" if perl else "perl was not found"
    if language in RELEASES:
        return "" if os.name == "nt" else "the pinned release is the Windows build"
    return "unknown language"


def _run(argv: list[str], env: dict | None, log, cwd: str | None = None) -> bool:
    log("> " + " ".join(argv))
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, **(env or {})), cwd=cwd, creationflags=NO_WINDOW, timeout=3600)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"failed: {e}")
        return False
    log(((p.stdout or "") + (p.stderr or "")).strip()[-4000:])
    return p.returncode == 0


def download_verified(url: str, sha256: str, dest: Path, log=print) -> bool:
    """Download *url* to *dest* and check its sha256 (deleted when it does not match)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
    if h.hexdigest().lower() != sha256.lower():
        dest.unlink(missing_ok=True)
        log(f"Checksum mismatch for {url} - removed")
        return False
    log(f"sha256 OK ({sha256[:16]}...)")
    return True


def _install_zip(language: str, target: Path, log) -> bool:
    version, url, sha = RELEASES[language]
    tmp = TOOLS / "_download" / Path(url).name
    if not download_verified(url, sha, tmp, log):
        return False
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    with zipfile.ZipFile(tmp) as z:
        for m in z.namelist():                       # no absolute paths / .. in the archive
            if m.startswith(("/", "\\")) or ".." in Path(m).parts:
                log(f"unsafe path in archive: {m}")
                return False
        z.extractall(target)
    tmp.unlink(missing_ok=True)
    (target / "RADIDE-SOURCE.json").write_text(json.dumps({"version": version, "url": url, "sha256": sha}, indent=1),
                                               encoding="utf-8")
    log(f"Installed {NAMES[language]} {version} into {target}")
    return True


def install(language: str, log=print) -> bool:
    """Install the server for *language* into the IDE's tools folder (blocking - run it in a thread)."""
    why = can_install(language)
    if why:
        log(f"Cannot install {NAMES.get(language, language)}: {why}")
        return False
    if language == "asm":
        from .asm_intel import lsp as asm_lsp
        return asm_lsp.install(log)
    if language == "go":
        GOPLS_DIR.mkdir(parents=True, exist_ok=True)
        env = {"GOBIN": str(GOPLS_DIR), "GOPATH": str(GOPLS_DIR / "gopath"), "GOCACHE": str(GOPLS_DIR / "gocache"),
               "GOTOOLCHAIN": "local"}
        ok = _run([find_go(), "install", "golang.org/x/tools/gopls@latest"], env, log)
        shutil.rmtree(GOPLS_DIR / "gocache", ignore_errors=True)       # build cache only
        return ok and bool(find_gopls())
    if language == "ruby":
        ruby = find_ruby()
        gem = _first(Path(ruby).parent / "gem.cmd", Path(ruby).parent / "gem.bat", Path(ruby).parent / "gem")
        argv = [gem] if gem.endswith((".cmd", ".bat")) else [ruby, gem or "gem"]
        GEM_HOME.mkdir(parents=True, exist_ok=True)
        # --conservative: keep the bundled precompiled rbs instead of building a newer one (needs a C compiler)
        return _run(argv + ["install", "ruby-lsp", "--no-document", "--conservative"], gem_env(ruby), log) \
            and bool(_ruby_script("ruby-lsp"))
    if language == "lua":
        return _install_zip("lua", LUA_LS_DIR, log)
    if language == "powershell":
        return _install_zip("powershell", PSES_DIR, log)
    if language == "perl":
        perl = find_perl()
        cpanm = _first(Path(perl).parent / "cpanm.bat", Path(perl).parent / "cpanm")
        if not cpanm:
            log("cpanm was not found next to perl")
            return False
        env = {"PATH": os.pathsep.join([str(Path(perl).parent), str(Path(perl).parents[2] / "c" / "bin"),
                                        os.environ.get("PATH", "")])}
        argv = [cpanm] if cpanm.endswith(".bat") else [perl, cpanm]
        return _run(argv + ["--notest", "--local-lib-contained", str(PERL_LS_DIR), "PLS"], env, log) \
            and bool(find_pls())
    return False
