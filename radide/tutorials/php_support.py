"""Lesson blocks of the PHP courses (php-web, the Laravel and CodeIgniter guides).

Fence info strings (see vb-basic/README.md for the shared format):

* ```` ```php run ```` - a PHP command-line script (``php main.php``).  ``text input`` after it is its stdin,
  ``text output`` the expected output.  "جرّبه" opens it as a PHP project without forms (the GUI Bridge runs
  such a project as a plain console program, output in the Output window).
* ```` ```php web run ```` - one or more pages of a web site (``// #file: name.php`` splits the block, the
  default file is ``index.php``; sub folders such as ``// #file: inc/db.php`` are allowed).  "جرّبه" opens it
  as a **PHP Web Site** project and runs it (the dev server + the Preview + the Requests window).  The check
  starts ``php -S`` on a free port, sends the requests of the hidden test comment (one cookie jar, so sessions
  work; redirects are followed) and compares the body of the **last** response with ``text output``::

      <!-- test: {"requests": [{"path": "/form.php"},
                               {"method": "POST", "path": "/form.php", "data": {"name": "Sara"}}],
                  "all": false, "start": "form.php"} -->

  ``"all": true`` compares the bodies of every request (joined by a new line); without a test comment the
  block requests ``/`` once.  ``"start"`` is the start page of the project "جرّبه" opens.  A form value
  ``"{{field:csrf}}"`` is the value of that (hidden) field in the previous response, and ``"mask":
  {"<regex>": "<text>"}`` replaces random parts of the output (tokens) before the comparison.
* ``exercise`` / ``solution`` work as in the other courses (``php exercise`` / ``php web exercise`` ...).
"""
from __future__ import annotations

import http.cookiejar
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LANGS = ("php",)
ALIASES = {"php": "php"}
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
STDIN_RX = r"\bSTDIN\b|\breadline\s*\(|php://stdin"
SKIP_FILES = {"_radmain.php", "radgui.php", "radworker.php", "project.radproj"}


# ===================================================================== block facts
def is_web(block) -> bool:
    return "web" in block.info.lower().split()[1:]


def default_file(block) -> str:
    return "index.php" if is_web(block) else "main.php"


def reads_stdin(block) -> bool:
    return block.lang == "php" and not is_web(block) and bool(re.search(STDIN_RX, block.code))


def tag(block) -> str:
    """The label of the block bar in the lesson viewer."""
    return "PHP (صفحة ويب)" if is_web(block) else "PHP"


# ===================================================================== tools
def php_exe() -> str | None:
    """The newest portable PHP of the IDE (%LOCALAPPDATA%\\RADIDE\\toolchains\\php\\<ver>), else php on PATH."""
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "toolchains" / "php"
    exe = "php.exe" if os.name == "nt" else "php"
    if base.is_dir():
        def ver(p: Path):
            return tuple(int(x) for x in re.findall(r"\d+", p.name)[:3]) or (0,)
        for d in sorted((d for d in base.iterdir() if d.is_dir()), key=ver, reverse=True):
            if (d / exe).is_file():
                return str(d / exe)
    return shutil.which("php")


def _clean(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)


def _write(files: dict[str, str], dest: Path) -> None:
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))           # keep the lesson's LF line ends


def _main_file(files: dict[str, str]) -> str:
    if "main.php" in files:
        return "main.php"
    return next((f for f in files if f.lower().endswith(".php")), next(iter(files), "main.php"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_page(files: dict[str, str], spec: dict | None) -> str:
    spec = spec or {}
    if spec.get("start"):
        return str(spec["start"]).lstrip("/")
    reqs = spec.get("requests") or []
    if reqs:
        path = urllib.parse.urlsplit(str(reqs[0].get("path", "/"))).path.lstrip("/")
        if path and path in files:
            return path
    return "index.php" if "index.php" in files else next(iter(files), "index.php")


# ===================================================================== projects ("جرّبه")
def make_project(block, files: dict[str, str], dest: Path, name: str = "Lesson"):
    from ..model import Project
    if is_web(block) or is_web(block.check_target()):
        from ..web_site.project import WEBSITE
        _write(files, dest)
        (dest / "data").mkdir(exist_ok=True)
        start = _start_page(files, block.check_target().spec)
        project = Project(dest, name, "php-web", [], "", [], {}, WEBSITE, [], {},
                          {"web": {"root": ".", "start": start, "port": 0, "live_reload": True}})
        project.save()
        return project
    project = Project(dest, name, "php")
    _write(files, dest)
    project.modules.append(_main_file(files))          # the other files are require'd by the main script
    project.save()
    return project


# ===================================================================== running
def run_cli(files: dict[str, str], stdin: str | None, work: Path, timeout: int = 20) -> tuple[bool, str]:
    """php main.php with *stdin*; (started, stdout + stderr)."""
    php = php_exe()
    if not php:
        return False, "PHP غير موجود (ثبّته من Tools > PHP Versions...)"
    work = Path(work).resolve()
    _clean(work)
    _write(files, work)
    try:
        r = subprocess.run([php, "-d", "display_errors=stderr", "-d", "log_errors=0", "-d", "error_reporting=E_ALL",
                            _main_file(files)], input=(stdin or "").encode("utf-8"), cwd=work,
                           capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return True, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    return True, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def run_web(files: dict[str, str], spec: dict | None, work: Path, timeout: int = 20) -> tuple[bool, str]:
    """Serve *files* with php -S and send the requests of *spec*; (served, body of the last response)."""
    php = php_exe()
    if not php:
        return False, "PHP غير موجود (ثبّته من Tools > PHP Versions...)"
    spec = dict(spec or {})
    work = Path(work).resolve()
    _clean(work)
    _write(files, work)
    (work / "data").mkdir(exist_ok=True)
    sessions = work / "_sessions"
    sessions.mkdir(exist_ok=True)
    port = _free_port()
    argv = [php, "-d", "display_errors=1", "-d", "error_reporting=E_ALL", "-d", "log_errors=0",
            "-d", f"session.save_path={sessions}", "-S", f"127.0.0.1:{port}", "-t", str(work)]
    proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    try:
        end = time.time() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                if time.time() > end or proc.poll() is not None:
                    return False, "تعذّر تشغيل خادم PHP المدمج (php -S)"
                time.sleep(0.1)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        bodies = []
        for rq in spec.get("requests") or [{"path": "/"}]:
            path = str(rq.get("path", "/"))
            url = f"http://127.0.0.1:{port}/{path.lstrip('/')}"
            data = rq.get("data")
            if isinstance(data, dict) and bodies:          # "{{field:csrf}}" = that hidden field of the last page
                data = {k: _field(bodies[-1], v) for k, v in data.items()}
            method = str(rq.get("method") or ("POST" if data is not None else "GET")).upper()
            body = urllib.parse.urlencode(data, doseq=True).encode("utf-8") if data is not None else None
            req = urllib.request.Request(url, data=body, method=method)
            if body is not None:
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            try:
                with opener.open(req, timeout=timeout) as resp:
                    raw = resp.read()
            except urllib.error.HTTPError as e:
                raw = e.read()
            except (urllib.error.URLError, OSError) as e:
                return False, f"فشل الطلب {method} {path}: {e}"
            bodies.append(raw.decode("utf-8", "replace"))
        shown = bodies if spec.get("all") else bodies[-1:]
        out = "\n".join(shown)
        for rx, repl in (spec.get("mask") or {}).items():     # random values (CSRF tokens ...) -> fixed text
            out = re.sub(rx, repl, out)
        return True, out
    finally:
        proc.kill()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            pass


def _field(page: str, value):
    """``{{field:name}}`` -> the value of the form field *name* in *page* (e.g. a CSRF token)."""
    m = re.fullmatch(r"\{\{field:([\w\[\]-]+)\}\}", value) if isinstance(value, str) else None
    if not m:
        return value
    name = re.escape(m.group(1))
    hit = re.search(r'name="' + name + r'"[^>]*?value="([^"]*)"', page) or \
        re.search(r'value="([^"]*)"[^>]*?name="' + name + r'"', page)
    return hit.group(1) if hit else ""


def _project_files(folder: Path) -> dict[str, str]:
    out = {}
    for p in sorted(Path(folder).rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and p.name not in SKIP_FILES and not rel.startswith(("data/", "_sessions/", ".radide")) \
                and p.suffix.lower() in (".php", ".html", ".css", ".js", ".json", ".txt", ".sql", ".csv"):
            out[rel] = p.read_text(encoding="utf-8", errors="replace")
    return out


def run_block(block, files: dict[str, str], work: Path) -> tuple[bool, str]:
    target = block.check_target()
    if is_web(block) or is_web(target):
        return run_web(files, target.spec, work)
    return run_cli(files, target.stdin, work)


def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    """The "تحقق" button: run the learner's version and compare it with the expected output."""
    target = block.check_target()
    files = _project_files(folder) if folder else block_files(block, code)
    ok, out = run_block(block, files, work)
    if not ok:
        return CheckResult(False, out, target.expected, ["تعذّر التشغيل"])
    expected = target.expected
    if expected is None and target is not block and target.code.strip():
        _ok, expected = run_block(target, block_files(target), work.parent / (work.name + "-sol"))
    if expected is None:
        bad = re.search(r"\b(Parse error|Fatal error|Uncaught)\b", out)
        return CheckResult(not bad, out, None, ["خطأ في البرنامج"] if bad else [],
                           "" if bad else "يعمل البرنامج بلا أخطاء.")
    good = norm(out) == norm(expected)
    return CheckResult(good, out, expected, [] if good else ["المخرجات لا تطابق المطلوب"])


__all__ = ["check", "default_file", "is_web", "make_project", "php_exe", "reads_stdin", "run_block", "run_cli",
           "run_web", "tag"]
