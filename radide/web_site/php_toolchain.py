"""PHP toolchains: every installed PHP, the PHP version of each website project, and Composer.

- **Portable PHP** - official NTS x64 zips from windows.php.net (``releases.json`` gives the newest patch
  of each series and its SHA256, checked before extracting) into
  ``%LOCALAPPDATA%\\RADIDE\\toolchains\\php\\<series>`` (e.g. ``php\\8.4``) with a generated ``php.ini`` next to
  ``php.exe`` (PHP reads it from there) that sets ``extension_dir`` and enables the extensions Laravel /
  CodeIgniter / Symfony need. No installer, no admin, no PATH or registry changes. ``toolchain.json`` in the
  folder records the URL, version and checksum.
- **Detection** (:func:`detect_installs`) - the toolchains folder, ``C:\\tools\\php*``, every ``php.exe`` on
  PATH, XAMPP / Laragon / WAMP / Scoop folders and the interpreter configured in Tools > Options. The real
  version is read from each binary (folder names lie: ``C:\\tools\\php83`` may hold PHP 8.5), cached by
  path + size + mtime in ``toolchains\\php\\detected.json``.
- **Per-project PHP** - ``project.radproj`` ``"web": {"php": ...}``: ``"auto"`` = the newest installed PHP that
  satisfies the project's ``composer.json`` ``require.php``; ``"8.4"`` / ``"8.4.28"`` = the newest install of
  that version; anything else = a path to ``php.exe``. Missing = the interpreter configured in Tools > Options,
  else ``auto``. Used by the dev server, the PHP debugger (Xdebug DLL matched to that PHP), Composer and
  intelephense (``intelephense.environment.phpVersion``).
- **Composer** - the official ``composer.phar`` (getcomposer.org, SHA256 verified) in
  ``toolchains\\composer`` with a ``composer.bat`` shim. :func:`composer_argv` runs it with the project's PHP.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
USER_AGENT = "RAD-IDE (portable toolchain installer)"
TOOLCHAINS = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "RADIDE" / "toolchains"
PHP_ROOT = TOOLCHAINS / "php"
COMPOSER_DIR = TOOLCHAINS / "composer"
COMPOSER_PHAR = COMPOSER_DIR / "composer.phar"
COMPOSER_BAT = COMPOSER_DIR / "composer.bat"
CACHE_FILE = PHP_ROOT / "detected.json"

PHP_RELEASES_JSON = "https://windows.php.net/downloads/releases/releases.json"
PHP_RELEASES_BASE = "https://windows.php.net/downloads/releases/"
PHP_ARCHIVES_BASE = "https://windows.php.net/downloads/releases/archives/"
COMPOSER_VERSIONS = "https://getcomposer.org/versions"
COMPOSER_BASE = "https://getcomposer.org"
CACERT_URL = "https://curl.se/ca/cacert.pem"

# what Laravel 11/12, CodeIgniter 4, Symfony and the RAD IDE database tools need
INI_EXTENSIONS = ("openssl", "mbstring", "fileinfo", "curl", "pdo_sqlite", "sqlite3", "pdo_mysql", "mysqli",
                  "pdo_pgsql", "pgsql", "intl", "zip", "gd", "sodium", "exif", "bz2", "gettext")
SERIES_OFFERED = ("8.5", "8.4", "8.3", "8.2")      # Install PHP... list (newest first)


# ============================================================================ versions
def vtuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3])


def series_of(v: str) -> str:
    t = vtuple(v)
    return f"{t[0]}.{t[1]}" if len(t) >= 2 else str(v)


def _constraint_ok(version: tuple[int, ...], constraint: str) -> bool:
    """Composer-style ``require.php`` check (enough for real projects): ``^8.2``, ``~8.1.0``, ``>=8.1 <8.4``,
    ``8.2.*``, ``^7.4 || ^8.0``. An unparsable constraint is treated as satisfied."""
    constraint = (constraint or "").strip()
    if not constraint or constraint == "*":
        return True
    v = (tuple(version) + (0, 0, 0))[:3]

    def one(term: str) -> bool:
        term = term.strip()
        m = re.match(r"^(\^|~|>=|<=|>|<|==|=|!=)?\s*v?(\d+(?:\.(?:\d+|\*))*)$", term)
        if not m:
            return True
        op, raw = m.group(1) or "", m.group(2)
        parts = raw.split(".")
        if "*" in parts:
            fixed = [int(p) for p in parts[:parts.index("*")]]
            return list(v[:len(fixed)]) == fixed
        nums = [int(p) for p in parts]
        b = (tuple(nums) + (0, 0, 0))[:3]
        if op == "^":
            if b[0] > 0:
                return b <= v < (b[0] + 1, 0, 0)
            return b <= v < (0, b[1] + 1, 0)
        if op == "~":
            upper = (b[0] + 1, 0, 0) if len(nums) <= 2 else (b[0], b[1] + 1, 0)
            return b <= v < upper
        if op in ("", "=", "=="):
            return list(v[:len(nums)]) == nums
        return {">=": v >= b, "<=": v <= b, ">": v > b, "<": v < b, "!=": v != b}[op]

    for alt in re.split(r"\s*\|\|?\s*", constraint):
        alt = re.sub(r"(>=|<=|!=|==|>|<|=|\^|~)\s+", r"\1", alt.strip())      # ">= 8.1" -> ">=8.1"
        terms = [t for t in re.split(r"[\s,]+", alt) if t]
        if terms and all(one(t) for t in terms):
            return True
    return False


def project_php_constraint(folder) -> str:
    """``require.php`` of the project's composer.json ("" when there is none)."""
    try:
        data = json.loads((Path(folder) / "composer.json").read_text(encoding="utf-8"))
        return str((data.get("require") or {}).get("php") or "")
    except (OSError, ValueError, AttributeError):
        return ""


# ============================================================================ detection
@dataclass
class PhpInstall:
    path: str
    version: str            # "8.4.28"
    ts: bool = False
    bits: int = 64
    source: str = ""        # "RAD IDE toolchain", "C:\\tools", "PATH", ...

    @property
    def series(self) -> str:
        return series_of(self.version)

    @property
    def label(self) -> str:
        return f"PHP {self.version} {'TS' if self.ts else 'NTS'} x{'64' if self.bits == 64 else '86'}" \
               f" - {self.path}" + (f"  [{self.source}]" if self.source else "")


_CACHE: dict | None = None
_DETECTED: tuple[float, list[PhpInstall]] | None = None


def _load_cache() -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE = {}
    return _CACHE


def _save_cache() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(_CACHE or {}, indent=1), encoding="utf-8")
    except OSError:
        pass


def probe(php: str) -> PhpInstall | None:
    """Version / thread safety / bitness of one php executable (cached by path + size + mtime)."""
    try:
        st = Path(php).stat()
    except OSError:
        return None
    key = str(Path(php).resolve()).lower()
    stamp = f"{st.st_size}:{int(st.st_mtime)}"
    cache = _load_cache()
    hit = cache.get(key)
    if isinstance(hit, dict) and hit.get("stamp") == stamp and hit.get("version"):
        return PhpInstall(str(Path(php).resolve()), hit["version"], bool(hit.get("ts")), int(hit.get("bits") or 64))
    try:
        out = subprocess.run([php, "-n", "-r", "echo PHP_VERSION,'|',PHP_ZTS,'|',PHP_INT_SIZE*8;"],
                             capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW,
                             stdin=subprocess.DEVNULL).stdout.strip()
        ver, zts, bits = out.splitlines()[-1].split("|")
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None
    cache[key] = {"stamp": stamp, "version": ver, "ts": zts == "1", "bits": int(bits or 64)}
    _save_cache()
    return PhpInstall(str(Path(php).resolve()), ver, zts == "1", int(bits or 64))


def _candidates(extra=()) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for p in extra:
        if p:
            out.append((str(p), "configured"))
    if PHP_ROOT.is_dir():
        out += [(str(p), "RAD IDE toolchain") for p in sorted(PHP_ROOT.glob("*/php.exe"))]
    for base, src in ((Path(r"C:\tools"), r"C:\tools"), (Path(r"C:\laragon\bin\php"), "Laragon"),
                      (Path(r"C:\wamp64\bin\php"), "WAMP"), (Path(r"C:\wamp\bin\php"), "WAMP"),
                      (Path.home() / "scoop" / "apps", "Scoop")):
        try:
            if base.is_dir():
                for d in base.glob("php*"):
                    for exe in (d / "php.exe", d / "current" / "php.exe"):
                        if exe.is_file():
                            out.append((str(exe), src))
        except OSError:
            pass
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and (Path(d) / "php.exe").is_file():
            out.append((str(Path(d) / "php.exe"), "PATH"))
    for h in (r"C:\php\php.exe", r"C:\xampp\php\php.exe", r"C:\Program Files\PHP\php.exe"):
        if Path(h).is_file():
            out.append((h, "XAMPP" if "xampp" in h.lower() else "folder"))
    return out


def detect_installs(extra=(), refresh: bool = False) -> list[PhpInstall]:
    """Every PHP found on this machine, newest version first (NTS before TS for the same version)."""
    global _DETECTED
    if not refresh and not extra and _DETECTED and time.time() - _DETECTED[0] < 30:
        return list(_DETECTED[1])
    seen: dict[str, PhpInstall] = {}
    for path, src in _candidates(extra):
        try:
            key = str(Path(path).resolve()).lower()
        except OSError:
            continue
        if key in seen:
            if seen[key].source in ("PATH", "configured") and src not in ("PATH", "configured"):
                seen[key].source = src
            continue
        inst = probe(path)
        if inst is not None:
            inst.source = src
            seen[key] = inst
    found = sorted(seen.values(), key=lambda i: (vtuple(i.version), not i.ts, i.bits), reverse=True)
    if not extra:
        _DETECTED = (time.time(), found)
    return list(found)


def newest(constraint: str = "", installs=None) -> PhpInstall | None:
    installs = detect_installs() if installs is None else installs
    ok = [i for i in installs if i.bits == 64 and _constraint_ok(vtuple(i.version), constraint)]
    return ok[0] if ok else (installs[0] if installs and not constraint else None)


def resolve(spec: str = "auto", folder=None, fallback: str = "") -> str:
    """The php.exe of a ``web.php`` value (see the module docstring), "" when nothing matches."""
    spec = str(spec or "").strip()
    if not spec:
        if fallback and Path(fallback).exists():
            return fallback
        spec = "auto"
    if spec.lower() == "auto":
        inst = newest(project_php_constraint(folder) if folder else "")
        return inst.path if inst else (fallback if fallback and Path(fallback).exists() else "")
    if re.fullmatch(r"\d+(\.\d+){0,2}", spec):
        parts = spec.split(".")
        for i in detect_installs():
            if i.version.split(".")[:len(parts)] == parts and i.bits == 64:
                return i.path
        return ""
    p = Path(os.path.expandvars(spec))
    if p.is_dir():
        p = p / "php.exe"
    if not p.is_absolute() and folder:
        p = Path(folder) / p
    return str(p) if p.is_file() else ""


def project_php(project, fallback: str = "") -> str:
    """The PHP of a website project (``web.php``), *fallback* = the interpreter from Tools > Options."""
    spec = ""
    try:
        from .project import web_config
        spec = str(web_config(project).get("php") or "")
    except Exception:  # noqa: BLE001 - not a website project
        spec = ""
    return resolve(spec, getattr(project, "folder", None), fallback)


def configured_php(settings=None) -> str:
    """The PHP chosen in Tools > Options (interpreter/php-web, else interpreter/php), "" when none."""
    try:
        if settings is None:
            from ..app import ide_settings
            settings = ide_settings()
        val = settings.value("interpreter/php-web", "") or settings.value("interpreter/php", "") or ""
        return str(val) if val and Path(str(val)).exists() else ""
    except Exception:  # noqa: BLE001 - no Qt application / settings
        return ""


def php_for_folder(folder, settings=None) -> str:
    """The PHP of the project in *folder* (project.radproj ``web.php``) - for tools that only know a folder
    (intelephense's root, a terminal). Non-website folders: the configured / PATH PHP."""
    folder = Path(folder) if folder else None
    fallback = configured_php(settings)
    if folder is not None:
        try:
            data = json.loads((folder / "project.radproj").read_text(encoding="utf-8"))
            web = data.get("web") if isinstance(data.get("web"), dict) else None
            if web is not None or data.get("kind") == "website":
                return resolve(str((web or {}).get("php") or ""), folder, fallback)
        except (OSError, ValueError, AttributeError):
            pass
        if (folder / "composer.json").is_file() and not fallback:
            return resolve("auto", folder)
    return fallback or shutil.which("php") or resolve("auto", folder)


def php_version(php: str) -> str:
    inst = probe(php) if php else None
    return inst.version if inst else ""


# ============================================================================ download helpers
def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _download(url: str, target: Path, log=None, sha256: str = "") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if log:
        log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = target.with_suffix(target.suffix + ".part")
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
    if sha256 and h.hexdigest().lower() != sha256.lower():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"SHA256 mismatch for {url}: expected {sha256}, got {h.hexdigest()}")
    if sha256 and log:
        log(f"SHA256 verified: {sha256}")
    tmp.replace(target)
    return target


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    root = dest.resolve()
    for name in zf.namelist():
        out = (dest / name).resolve()
        if not str(out).lower().startswith(str(root).lower()):
            raise RuntimeError(f"unsafe path in archive: {name}")
    zf.extractall(dest)


# ============================================================================ PHP install
def php_release(series: str) -> dict:
    """{"version", "url", "sha256", "file"} of the newest NTS x64 zip of a PHP series."""
    data = json.loads(_get(PHP_RELEASES_JSON, 30).decode("utf-8"))
    rel = data.get(series)
    if not isinstance(rel, dict):
        raise RuntimeError(f"windows.php.net has no PHP {series} release")
    for key, build in rel.items():
        if key.startswith("nts-") and key.endswith("-x64") and isinstance(build, dict) and "zip" in build:
            z = build["zip"]
            return {"version": rel.get("version", ""), "file": z["path"], "sha256": z.get("sha256", ""),
                    "url": PHP_RELEASES_BASE + z["path"]}
    raise RuntimeError(f"no NTS x64 zip for PHP {series}")


def write_php_ini(folder: Path, dev: bool = True) -> Path:
    """php.ini next to php.exe: extension_dir + the extensions that exist in ext\\, dev-friendly errors."""
    folder = Path(folder)
    ext = folder / "ext"
    lines = ["; php.ini generated by RAD IDE (radide/web_site/php_toolchain.py) - edit freely,",
             "; 'Tools > PHP > Rewrite php.ini' regenerates it.", "[PHP]",
             f'extension_dir = "{ext}"', "memory_limit = 512M", "max_execution_time = 120",
             "post_max_size = 64M", "upload_max_filesize = 64M", "date.timezone = UTC",
             'variables_order = "EGPCS"', "realpath_cache_size = 4096K",
             f"display_errors = {'On' if dev else 'Off'}", "display_startup_errors = On" if dev else "",
             "error_reporting = E_ALL", "log_errors = Off", "zend.assertions = 1" if dev else "",
             "", "; extensions (Laravel / CodeIgniter / Symfony / RAD IDE databases)"]
    for name in INI_EXTENSIONS:
        if (ext / f"php_{name}.dll").is_file():
            lines.append(f"extension={name}")
    if (ext / "php_opcache.dll").is_file():
        lines += ["", "[opcache]", "zend_extension=opcache", "opcache.enable=1", "opcache.enable_cli=0",
                  "opcache.validate_timestamps=1", "opcache.revalidate_freq=0"]
    cacert = TOOLCHAINS / "cacert" / "cacert.pem"
    if cacert.is_file():
        lines += ["", "[curl]", f'curl.cainfo = "{cacert}"', "[openssl]", f'openssl.cafile = "{cacert}"']
    ini = folder / "php.ini"
    ini.write_text("\n".join(ln for ln in lines if ln is not None) + "\n", encoding="utf-8")
    return ini


def install_cacert(log=None) -> Path:
    """curl's Mozilla CA bundle (SHA256 from cacert.pem.sha256) - PHP on Windows ships none."""
    dest = TOOLCHAINS / "cacert" / "cacert.pem"
    if dest.is_file() and time.time() - dest.stat().st_mtime < 90 * 86400:
        return dest
    sha = _get(CACERT_URL + ".sha256", 30).decode("ascii", "replace").split()[0]
    return _download(CACERT_URL, dest, log, sha)


def install_php(series: str = "8.4", log=None) -> str:
    """Download the newest official PHP <series> NTS x64 into toolchains\\php\\<series>; returns php.exe."""
    rel = php_release(series)
    if not rel["sha256"]:
        raise RuntimeError(f"windows.php.net publishes no SHA256 for {rel['file']}")
    dest = PHP_ROOT / series
    exe = dest / "php.exe"
    info = dest / "toolchain.json"
    try:
        if exe.is_file() and json.loads(info.read_text(encoding="utf-8")).get("version") == rel["version"]:
            if log:
                log(f"PHP {rel['version']} is already installed in {dest}")
            return str(exe)
    except (OSError, ValueError):
        pass
    try:
        install_cacert(log)
    except Exception as e:  # noqa: BLE001 - optional
        if log:
            log(f"(CA bundle not downloaded: {e})")
    zpath = _download(rel["url"], TOOLCHAINS / "_download" / rel["file"], log, rel["sha256"])
    tmp = PHP_ROOT / f".{series}.new"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(zpath) as zf:
        _safe_extract(zf, tmp)
    if not (tmp / "php.exe").is_file():
        raise RuntimeError("php.exe is missing from the archive")
    old_ini = dest / "php.ini"
    keep_ini = old_ini.read_text(encoding="utf-8") if old_ini.is_file() and "generated by RAD IDE" \
        not in old_ini.read_text(encoding="utf-8", errors="replace") else None
    if dest.exists():
        shutil.rmtree(dest)
    tmp.rename(dest)
    if keep_ini is not None:
        (dest / "php.ini").write_text(keep_ini, encoding="utf-8")          # the user's own edits win
    else:
        write_php_ini(dest)
    info.write_text(json.dumps({"tool": "php", "version": rel["version"], "url": rel["url"],
                                "sha256": rel["sha256"], "build": "NTS x64",
                                "installed": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2), encoding="utf-8")
    zpath.unlink(missing_ok=True)
    global _DETECTED
    _DETECTED = None
    if log:
        log(f"PHP {rel['version']} installed: {exe}")
    return str(exe)


def installed_toolchains() -> list[dict]:
    out = []
    for f in sorted(PHP_ROOT.glob("*/toolchain.json")) if PHP_ROOT.is_dir() else []:
        try:
            out.append({**json.loads(f.read_text(encoding="utf-8")), "folder": str(f.parent)})
        except (OSError, ValueError):
            pass
    return out


# ============================================================================ Composer
def install_composer(log=None) -> str:
    """The newest stable composer.phar (SHA256 verified) + composer.bat; returns composer.bat."""
    data = json.loads(_get(COMPOSER_VERSIONS, 30).decode("utf-8"))
    stable = data["stable"][0]
    url = COMPOSER_BASE + stable["path"]
    sha = _get(url + ".sha256sum", 30).decode("ascii", "replace").split()[0]
    info = COMPOSER_DIR / "toolchain.json"
    try:
        if COMPOSER_PHAR.is_file() and json.loads(info.read_text(encoding="utf-8")).get("version") == \
                stable["version"]:
            write_composer_shim()
            if log:
                log(f"Composer {stable['version']} is already installed")
            return str(COMPOSER_BAT)
    except (OSError, ValueError):
        pass
    _download(url, COMPOSER_PHAR, log, sha)
    info.write_text(json.dumps({"tool": "composer", "version": stable["version"], "url": url, "sha256": sha,
                                "installed": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2), encoding="utf-8")
    write_composer_shim()
    if log:
        log(f"Composer {stable['version']} installed: {COMPOSER_BAT}")
    return str(COMPOSER_BAT)


def write_composer_shim() -> Path:
    """composer.bat: runs composer.phar with %RADIDE_COMPOSER_PHP% (set by the IDE to the project's PHP),
    else the newest toolchain PHP (its php.ini is known to enable openssl / zip / ...), else php on PATH."""
    installs = detect_installs()
    best = newest(installs=[i for i in installs if i.source == "RAD IDE toolchain"]) or newest(installs=installs)
    default = best.path if best else "php"
    COMPOSER_DIR.mkdir(parents=True, exist_ok=True)
    COMPOSER_BAT.write_text(
        "@echo off\r\n"
        "rem Composer shim generated by RAD IDE\r\n"
        "setlocal\r\n"
        'set "RAD_PHP=%RADIDE_COMPOSER_PHP%"\r\n'
        f'if "%RAD_PHP%"=="" set "RAD_PHP={default}"\r\n'
        'if not exist "%RAD_PHP%" set "RAD_PHP=php"\r\n'
        '"%RAD_PHP%" "%~dp0composer.phar" %*\r\n', encoding="ascii")
    return COMPOSER_BAT


def find_composer() -> str:
    """composer.bat of the toolchain, else composer on PATH / ComposerSetup, else ""."""
    if COMPOSER_PHAR.is_file():
        if not COMPOSER_BAT.is_file():
            write_composer_shim()
        return str(COMPOSER_BAT)
    found = shutil.which("composer")
    if found:
        return found
    for h in (r"C:\ProgramData\ComposerSetup\bin\composer.bat",
              str(Path(os.environ.get("APPDATA", "")) / "Composer" / "vendor" / "bin" / "composer.bat")):
        if Path(h).exists():
            return h
    return ""


def composer_argv(args: list[str], php: str = "") -> list[str]:
    """argv that runs Composer with *php* (the project's PHP) - [] when Composer is not installed."""
    if COMPOSER_PHAR.is_file() and php and Path(php).is_file():
        try:   # a PHP without openssl / zip / mbstring in its php.ini: enable them for this run
            from ..languages.php_web import extension_args
            extra = extension_args(php)
        except Exception:  # noqa: BLE001
            extra = []
        return [php, *extra, str(COMPOSER_PHAR), *args]
    tool = find_composer()
    return [tool, *args] if tool else []


def composer_env(php: str = "") -> dict:
    env = dict(os.environ)
    if php:
        env["RADIDE_COMPOSER_PHP"] = php
        env["PATH"] = str(Path(php).parent) + os.pathsep + env.get("PATH", "")
    env.setdefault("COMPOSER_NO_INTERACTION", "1")
    return env


def intelephense_version(php: str) -> str:
    """"8.4.0" style value for intelephense.environment.phpVersion."""
    v = vtuple(php_version(php)) if php else ()
    return f"{v[0]}.{v[1]}.0" if len(v) >= 2 else ""


def summary() -> dict:
    return {"installs": [asdict(i) | {"series": i.series} for i in detect_installs()],
            "toolchains": installed_toolchains(), "composer": find_composer()}


if __name__ == "__main__":                          # python -m radide.web_site.php_toolchain [series...]
    import sys
    for s in sys.argv[1:] or ["8.4"]:
        if s == "composer":
            print(install_composer(print))
        else:
            print(install_php(s, print))
    for i in detect_installs(refresh=True):
        print(i.label)
