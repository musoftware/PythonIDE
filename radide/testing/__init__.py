"""Unit-test discovery, running and coverage for every language (Test Explorer back end).

No Qt in here (the dock is radide/features/test_explorer.py). An *adapter* knows one framework:

    a = adapter_for(root)            # or adapters_for(root) -> every framework found in the folder
    a.available() -> (ok, hint)
    items = a.discover()             # list[TestItem] (may run a tool; call it from a worker thread)
    plan = a.plan(selected_items or None, coverage=False, debug=False)   # RunPlan: steps to run
    results = plan.parse(stdout_text)                                     # list[Result]
    cov = plan.coverage()            # {abs path: FileCoverage} or {}

Frameworks: Python pytest / unittest (project .venv), JS/TS jest / vitest / node --test, Go go test,
Rust cargo test, C# dotnet test (xUnit / NUnit / MSTest via TRX), PHP PHPUnit (composer), Dart / Flutter
test, Java JUnit 5 (Maven, or plain javac + the JUnit console launcher), Ring and VB (simple convention:
files test_*.ring / Test*.bas with test functions; assert helpers).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
PYHELPER = HERE / "pyhelper.py"
NODE_REPORTER = HERE / "node_reporter.mjs"
MARK = "@@RADTEST@@"
LOCAL = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE"
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".radide", ".radide_backup",
             "build", "dist", "target", "bin", "obj", ".dart_tool", "vendor", ".pytest_cache", ".idea", ".vs"}
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
JUNIT_VERSION = "1.11.3"
JUNIT_URL = ("https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/"
             f"{JUNIT_VERSION}/junit-platform-console-standalone-{JUNIT_VERSION}.jar")


# ============================================================================ model
@dataclass
class TestItem:
    id: str                       # framework selector (pytest node id, Ns.Class.Method, file::name ...)
    name: str                     # display name
    file: str = ""                # absolute path
    line: int = 0                 # 1-based
    suite: str = ""               # group under the file ("TestCalc", "math > add" ...)
    framework: str = ""
    # live state (filled by results)
    state: str = "unknown"        # unknown | running | passed | failed | skipped | error
    duration: float | None = None
    message: str = ""
    output: str = ""


@dataclass
class Result:
    id: str = ""
    state: str = "passed"
    duration: float | None = None
    message: str = ""
    output: str = ""
    file: str = ""
    line: int = 0
    name: str = ""


@dataclass
class FileCoverage:
    covered: set = field(default_factory=set)
    missed: set = field(default_factory=set)
    partial: set = field(default_factory=set)

    @property
    def statements(self) -> int:
        return len(self.covered | self.missed)

    @property
    def percent(self) -> float:
        n = self.statements
        return 100.0 * len(self.covered) / n if n else 100.0


@dataclass
class Step:
    argv: list
    cwd: Path
    env: dict = field(default_factory=dict)     # extra environment variables
    title: str = ""


@dataclass
class RunPlan:
    steps: list
    parse: Callable[[str], list]
    coverage: Callable[[], dict] = lambda: {}
    tmp: Path | None = None
    debug_program: str = ""                     # debug: python script / module for debugpy
    debug_args: list = field(default_factory=list)
    debug_python: str = ""
    debug_env: dict = field(default_factory=dict)


def work_dir(root: Path) -> Path:
    """A private temp folder per project for report files (the project folder stays clean)."""
    h = hashlib.sha1(str(Path(root).resolve()).lower().encode()).hexdigest()[:10]
    d = Path(tempfile.gettempdir()) / "radide-tests" / h
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run(argv, cwd, timeout=120, env=None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=e, creationflags=NOWIN)


def _files(root: Path, patterns, max_files=3000) -> list[Path]:
    out = []
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if any(re.fullmatch(p, fn, re.I) for p in patterns):
                out.append(Path(dirpath) / fn)
                if len(out) >= max_files:
                    return out
    return sorted(out)


def _read(p: Path) -> str:
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(root: Path, p) -> str:
    try:
        return Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return Path(p).name


def find_exe(*names: str, dirs=()) -> str:
    """PATH first, then the IDE's private tool folders (%LOCALAPPDATA%\\RADIDE\\toolchains|tools)."""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    cands = list(dirs)
    for base in (LOCAL / "toolchains", LOCAL / "tools"):
        if base.is_dir():
            for d in base.iterdir():
                if d.is_dir():
                    cands += [d / "bin", d]
    ext = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)
    for d in cands:
        for n in names:
            for e in ext:
                p = Path(d) / (n + e)
                if p.is_file():
                    return str(p)
    return ""


def cmd_argv(exe: str, *args) -> list:
    """.cmd / .bat shims (npx, phpunit.bat, flutter.bat) must run through cmd.exe."""
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/d", "/c", exe, *args]
    return [exe, *args]


def _markers(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        i = line.find(MARK)
        if i >= 0:
            try:
                out.append(json.loads(line[i + len(MARK):]))
            except ValueError:
                pass
    return out


def _secs(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ============================================================================ report parsers
def parse_junit(path: Path) -> list[Result]:
    """JUnit XML (pytest/phpunit/surefire/JUnit console/many others)."""
    out: list[Result] = []
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return out
    for tc in root.iter("testcase"):
        r = Result(name=tc.get("name", ""), duration=_secs(tc.get("time")), file=tc.get("file", ""),
                   line=int(tc.get("line") or 0))
        cls = tc.get("classname") or tc.get("class") or ""
        r.id = f"{cls}::{r.name}" if cls else r.name
        for tag, state in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            el = tc.find(tag)
            if el is not None:
                r.state = state
                r.message = "\n".join(x for x in (el.get("message", ""), (el.text or "").strip()) if x).strip()
                break
        outs = [(tc.findtext(t) or "").strip() for t in ("system-out", "system-err")]
        r.output = "\n".join(x for x in outs if x)
        r._classname = cls          # type: ignore[attr-defined]
        out.append(r)
    return out


def parse_trx(path: Path) -> list[Result]:
    """Visual Studio TRX (dotnet test --logger trx): xUnit, NUnit and MSTest."""
    out: list[Result] = []
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return out
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    names: dict[str, str] = {}
    for ut in root.iter(ns + "UnitTest"):
        tm = ut.find(ns + "TestMethod")
        ex = ut.find(ns + "Execution")
        if tm is not None:
            cls = (tm.get("className") or "").split(",")[0].strip()
            fq = f"{cls}.{tm.get('name')}" if cls else tm.get("name", "")
            names[ex.get("id") if ex is not None else ut.get("id")] = fq
    for res in root.iter(ns + "UnitTestResult"):
        fq = names.get(res.get("executionId")) or res.get("testName", "")
        st = {"Passed": "passed", "Failed": "failed", "NotExecuted": "skipped", "Error": "error"}.get(
            res.get("outcome", ""), "skipped")
        dur = res.get("duration") or "0:0:0"
        try:
            h, m, s = dur.split(":")
            secs = int(h) * 3600 + int(m) * 60 + float(s)
        except ValueError:
            secs = None
        msg = res.findtext(f"{ns}Output/{ns}ErrorInfo/{ns}Message") or ""
        stack = res.findtext(f"{ns}Output/{ns}ErrorInfo/{ns}StackTrace") or ""
        so = res.findtext(f"{ns}Output/{ns}StdOut") or ""
        name = res.get("testName", fq)
        if "(" in name and "(" not in fq:        # [Theory] cases: keep the arguments in the display name
            fq = fq + name[name.index("("):]
        out.append(Result(id=fq, state=st, duration=secs, message=(msg + "\n" + stack).strip(), output=so,
                          name=name))
    return out


def parse_lcov(path: Path, root: Path) -> dict:
    cov: dict[str, FileCoverage] = {}
    cur = None
    for line in _read(path).splitlines():
        if line.startswith("SF:"):
            p = Path(line[3:].strip())
            if not p.is_absolute():
                p = Path(root) / p
            cur = cov.setdefault(str(p.resolve()), FileCoverage())
        elif line.startswith("DA:") and cur is not None:
            parts = line[3:].split(",")
            try:
                n, hits = int(parts[0]), int(float(parts[1]))
            except (ValueError, IndexError):
                continue
            (cur.covered if hits > 0 else cur.missed).add(n)
        elif line.startswith("BRDA:") and cur is not None:
            parts = line[5:].split(",")
            if len(parts) >= 4 and parts[3] in ("-", "0"):
                try:
                    cur.partial.add(int(parts[0]))
                except ValueError:
                    pass
        elif line.startswith("end_of_record"):
            cur = None
    for fc in cov.values():
        fc.partial &= fc.covered
    return cov


# ============================================================================ adapters
class Adapter:
    id = ""
    name = ""
    language = ""                 # Monaco language id of the test files
    supports_coverage = False
    supports_debug = False

    def __init__(self, root: Path, win=None):
        self.root = Path(root).resolve()
        self.win = win
        self.tmp = work_dir(self.root)

    @classmethod
    def detect(cls, root: Path) -> bool:
        return False

    def available(self) -> tuple[bool, str]:
        return True, ""

    def discover(self) -> list[TestItem]:
        return []

    def plan(self, items: list[TestItem] | None, coverage=False, debug=False) -> RunPlan:
        raise NotImplementedError

    def item(self, id, name, file, line, suite=""):
        return TestItem(id=id, name=name, file=str(file), line=line, suite=suite, framework=self.id)


# ---------------------------------------------------------------------------- Python
_PROBES: dict[str, dict] = {}


def probe_python(python: str) -> dict:
    if python in _PROBES:
        return _PROBES[python]
    try:
        p = _run([python, "-I", str(PYHELPER), "probe"], HERE, timeout=30)
        m = _markers(p.stdout)
        info = m[-1] if m else {}
    except (OSError, subprocess.TimeoutExpired):
        info = {}
    _PROBES[python] = info
    return info


class PythonAdapter(Adapter):
    id = "python"
    name = "Python (pytest / unittest)"
    language = "python"
    supports_coverage = True
    supports_debug = True

    @classmethod
    def detect(cls, root):
        root = Path(root)
        if any((root / f).exists() for f in ("pytest.ini", "conftest.py", "tox.ini")):
            return True
        if "[tool.pytest" in _read(root / "pyproject.toml"):
            return True
        return bool(_files(root, [r"test_.*\.py", r".*_test\.py", r"tests?\.py"], 1))

    def _venv(self) -> str:
        for rel_ in ((".venv", "Scripts", "python.exe"), (".venv", "bin", "python"),
                     ("venv", "Scripts", "python.exe"), ("venv", "bin", "python")):
            p = self.root.joinpath(*rel_)
            if p.is_file():
                return str(p)
        return ""

    def interpreter(self, need=("pytest",)) -> tuple[str, dict, str]:
        """(python, extra env, note). The project's .venv when it has the tools, else the IDE's Python
        with the project (and its .venv's site-packages) on PYTHONPATH."""
        env = {"PYTHONPATH": str(self.root), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        venv = self._venv()
        cands = [venv] if venv else []
        conf = ""
        if self.win is not None:
            try:
                conf = self.win.settings.value("interpreter/python-tk", "") or ""
            except Exception:  # noqa: BLE001
                conf = ""
        if conf and Path(conf).is_file():
            cands.append(conf)
        for py in cands:
            info = probe_python(py)
            if info and all(info.get(n) for n in need):
                return py, env, f"Python {info.get('python')} ({py})"
        ide = sys.executable
        if venv:
            for sp in (Path(venv).parent.parent / "Lib" / "site-packages",
                       *Path(venv).parent.parent.glob("lib/python*/site-packages")):
                if Path(sp).is_dir():
                    env["PYTHONPATH"] += os.pathsep + str(sp)
        why = f" (the project's Python has no {', '.join(need)})" if cands else ""
        return ide, env, f"the IDE's Python {sys.version.split()[0]}{why}"

    def available(self):
        py, _env, _note = self.interpreter(())
        return (bool(py), "" if py else "Python was not found")

    def discover(self):
        py, env, note = self.interpreter(("pytest",))
        info = probe_python(py)
        try:
            p = _run([py, str(PYHELPER), "collect", str(self.root)], self.root, timeout=120, env=env)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"test discovery failed: {e}") from e
        m = _markers(p.stdout)
        if not m or "fatal" in m[-1]:
            raise RuntimeError((m[-1].get("fatal") if m else "") or (p.stdout + p.stderr)[-3000:])
        data = m[-1]
        self.framework = data.get("framework", "pytest" if info.get("pytest") else "unittest")
        self.note = note
        out = []
        for it in data.get("items", []):
            f = it.get("file", "")
            if f and not Path(f).is_absolute():
                f = str(self.root / f)
            tid = it["id"]
            suite = it.get("cls", "")
            name = it.get("name") or tid.rsplit("::", 1)[-1]
            out.append(self.item(tid, name, f, it.get("line", 0), suite))
        self.errors = data.get("errors", [])
        for e in self.errors:
            t = self.item(e.get("id", "<collection>"), "collection error: " + e.get("id", ""),
                          e.get("file", ""), 1, "")
            t.state, t.message = "error", e.get("message", "")
            out.append(t)
        return out

    def plan(self, items, coverage=False, debug=False):
        need = ["pytest"] + (["coverage"] if coverage else []) + (["debugpy"] if debug else [])
        py, env, note = self.interpreter(tuple(need))
        info = probe_python(py)
        mode = "pytest" if info.get("pytest") else "unittest"
        out = self.tmp / "results.json"
        if out.exists():
            out.unlink()
        ids = [i.id for i in items or [] if not i.name.startswith("collection error")]
        args = [str(PYHELPER), mode, str(self.root), str(out), *ids]
        covdata = self.tmp / ".coverage"
        covjson = self.tmp / "coverage.json"
        steps = []
        if coverage and info.get("coverage"):
            for p in (covdata, covjson):
                if p.exists():
                    p.unlink()
            steps.append(Step([py, "-m", "coverage", "run", "--branch", f"--data-file={covdata}",
                               f"--source={self.root}", "--omit=*/.venv/*,*/venv/*,*/site-packages/*", *args],
                              self.root, env, f"coverage run ({note})"))
            steps.append(Step([py, "-m", "coverage", "json", f"--data-file={covdata}", "-o", str(covjson),
                               "--ignore-errors"], self.root, env, "coverage json"))
        else:
            steps.append(Step([py, *args], self.root, env, f"{mode} ({note})"))

        def parse(_text):
            try:
                data = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return []
            return [Result(id=r["id"], state=r.get("state", "passed"), duration=r.get("duration"),
                           message=r.get("message", ""), output=r.get("output", ""), file=r.get("file", ""),
                           line=r.get("line", 0)) for r in data.get("results", [])]

        def cov():
            return coverage_py_json(covjson, self.root) if coverage else {}
        plan = RunPlan(steps, parse, cov, self.tmp)
        plan.debug_program, plan.debug_args, plan.debug_python = str(PYHELPER), args[1:], py
        plan.debug_env = env
        return plan


def coverage_py_json(path: Path, root: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for f, d in (data.get("files") or {}).items():
        p = Path(f)
        if not p.is_absolute():
            p = Path(root) / p
        fc = FileCoverage(set(d.get("executed_lines", [])), set(d.get("missing_lines", [])))
        for a, _b in d.get("missing_branches", []) or []:
            if a in fc.covered:
                fc.partial.add(a)
        out[str(p.resolve())] = fc
    return out


# ---------------------------------------------------------------------------- JavaScript / TypeScript
_JS_TEST = re.compile(r"""^(\s*)(?:test|it)(?:\.(?:only|skip|todo|each\([^)]*\)))?\s*\(\s*(['"`])(.+?)\2""")
_JS_DESCRIBE = re.compile(r"""^(\s*)(?:describe|suite)(?:\.(?:only|skip))?\s*\(\s*(['"`])(.+?)\2""")
_NODE_TEST = re.compile(r"""^(\s*)(?:test|it|t\.test)\s*\(\s*(['"`])(.+?)\2""")


def scan_nested(path: Path, test_rx, group_rx) -> list[tuple[list[str], str, int]]:
    """(group titles, test title, 1-based line) - nesting by indentation (describe / group blocks)."""
    out = []
    stack: list[tuple[int, str]] = []
    for n, line in enumerate(_read(path).splitlines(), 1):
        m = group_rx.match(line) if group_rx else None
        t = test_rx.match(line) if not m else None
        if not (m or t):
            continue
        ind = len((m or t).group(1).expandtabs(4))
        while stack and stack[-1][0] >= ind:
            stack.pop()
        if m:
            stack.append((ind, m.group(3)))
        else:
            out.append(([s for _i, s in stack], t.group(3), n))
    return out


class NodeAdapter(Adapter):
    id = "node"
    language = "javascript"

    @classmethod
    def runner(cls, root: Path) -> str:
        try:
            pkg = json.loads(_read(Path(root) / "package.json") or "{}")
        except ValueError:
            pkg = {}
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        script = (pkg.get("scripts") or {}).get("test", "")
        if "vitest" in deps or "vitest" in script:
            return "vitest"
        if "jest" in deps or "jest" in script:
            return "jest"
        if "node --test" in script or "node:test" in "".join(_read(p)[:4000] for p in cls._test_files(root)[:20]):
            return "node"
        return ""

    @staticmethod
    def _test_files(root):
        return _files(root, [r".*\.(test|spec)\.(js|mjs|cjs|jsx|ts|tsx|mts)", r"test[-_].*\.(js|mjs|cjs)"])

    @classmethod
    def detect(cls, root):
        return bool(cls.runner(root)) and bool(cls._test_files(root))

    def __init__(self, root, win=None):
        super().__init__(root, win)
        self.kind = self.runner(root) or "node"
        self.name = {"jest": "Jest", "vitest": "Vitest", "node": "node --test"}[self.kind]
        self.supports_coverage = self.kind == "jest"

    def _bin(self) -> list[str] | None:
        node = find_exe("node")
        if self.kind == "node":
            return [node] if node else None
        local = {"jest": self.root / "node_modules" / "jest" / "bin" / "jest.js",
                 "vitest": self.root / "node_modules" / "vitest" / "vitest.mjs"}[self.kind]
        if node and local.exists():
            return [node, str(local)]
        npx = find_exe("npx")
        return cmd_argv(npx, "--yes", self.kind) if npx else None

    def available(self):
        if self._bin() is None:
            return False, "Node.js was not found (install Node.js)"
        if self.kind != "node" and not (self.root / "node_modules").is_dir():
            return True, "node_modules is missing: run 'npm install' in the project (Terminal)"
        return True, ""

    def discover(self):
        out = []
        rx = _NODE_TEST if self.kind == "node" else _JS_TEST
        for f in self._test_files(self.root):
            for groups, title, line in scan_nested(f, rx, _JS_DESCRIBE):
                full = " > ".join([*groups, title])
                out.append(self.item(f"{rel(self.root, f)}::{full}", title, f, line, " > ".join(groups)))
        return out

    def plan(self, items, coverage=False, debug=False):
        base = self._bin() or ["node"]
        files = sorted({i.file for i in items}) if items else []
        names = sorted({re.escape(i.name) for i in items}) if items else []
        rep = self.tmp / f"{self.kind}.json"
        if rep.exists():
            rep.unlink()
        if self.kind == "jest":
            argv = [*base, "--json", f"--outputFile={rep}", "--testLocationInResults", "--colors=false", *files]
            if names:
                argv += ["-t", "|".join(names)]
            if coverage:
                argv += ["--coverage", "--coverageReporters=lcov", f"--coverageDirectory={self.tmp / 'jestcov'}"]
        elif self.kind == "vitest":
            argv = [*base, "run", "--reporter=json", f"--outputFile={rep}", *files]
            if names:
                argv += ["-t", "|".join(names)]
        else:
            argv = [*base, "--test", f"--test-reporter={NODE_REPORTER.as_uri()}", "--test-reporter-destination=stdout"]
            if names:
                argv += ["--test-name-pattern", "|".join(names)]
            argv += files or [str(f) for f in self._test_files(self.root)]
        root = self.root

        def parse(text):
            if self.kind == "node":
                return [Result(state=d.get("state", "passed"), duration=d.get("duration"),
                               message=d.get("message", ""), file=_file_url(d.get("file", "")),
                               line=d.get("line", 0), name=d.get("name", "")) for d in _markers(text)]
            try:
                data = json.loads(rep.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return []
            out = []
            for tr in data.get("testResults", []):
                f = tr.get("name") or tr.get("testFilePath", "")
                for a in tr.get("assertionResults", []):
                    full = " > ".join([*a.get("ancestorTitles", []), a.get("title", "")])
                    st = {"passed": "passed", "failed": "failed"}.get(a.get("status"), "skipped")
                    loc = a.get("location") or {}
                    out.append(Result(id=f"{rel(root, f)}::{full}", state=st,
                                      duration=(a.get("duration") or 0) / 1000.0,
                                      message="\n".join(a.get("failureMessages") or []), file=f,
                                      line=loc.get("line", 0), name=a.get("title", "")))
                if not tr.get("assertionResults") and tr.get("message"):
                    out.append(Result(id=f"{rel(root, f)}::<file>", state="error", message=tr["message"], file=f,
                                      line=1, name=Path(f).name))
            return out

        def cov():
            return parse_lcov(self.tmp / "jestcov" / "lcov.info", root) if coverage else {}
        return RunPlan([Step(argv, self.root, {"FORCE_COLOR": "0", "CI": "1"}, self.name)], parse, cov, self.tmp)


def _file_url(f: str) -> str:
    if f.startswith("file:"):
        from urllib.parse import unquote, urlparse
        u = urlparse(f)
        p = unquote(u.path)
        if os.name == "nt" and p.startswith("/") and len(p) > 2 and p[2] == ":":
            p = p[1:]
        return p
    return f


# ---------------------------------------------------------------------------- Go
class GoAdapter(Adapter):
    id = "go"
    name = "go test"
    language = "go"
    supports_coverage = True

    @classmethod
    def detect(cls, root):
        return (Path(root) / "go.mod").exists() and bool(_files(root, [r".*_test\.go"], 1))

    def _go(self):
        return find_exe("go", dirs=[LOCAL / "toolchains" / "go" / "bin"])

    def available(self):
        return (True, "") if self._go() else (False, "Go was not found (install Go)")

    def _module(self) -> str:
        m = re.search(r"^module\s+(\S+)", _read(self.root / "go.mod"), re.M)
        return m.group(1) if m else ""

    def discover(self):
        out = []
        for f in _files(self.root, [r".*_test\.go"]):
            reldir = rel(self.root, f.parent)
            reldir = "." if reldir in ("", f.parent.name) and f.parent == self.root else reldir
            for n, line in enumerate(_read(f).splitlines(), 1):
                m = re.match(r"func\s+(Test\w*|Example\w*|Benchmark\w*)\s*\(", line)
                if m and not m.group(1).startswith("Benchmark"):
                    out.append(self.item(f"{reldir}::{m.group(1)}", m.group(1), f, n, reldir))
        return out

    def plan(self, items, coverage=False, debug=False):
        go = self._go() or "go"
        pkgs = sorted({i.id.split("::")[0] for i in items}) if items else []
        argv = [go, "test", "-json", "-count=1"]
        if items:
            argv += ["-run", "^(" + "|".join(sorted({re.escape(i.name) for i in items})) + ")$"]
        prof = self.tmp / "cover.out"
        if coverage:
            if prof.exists():
                prof.unlink()
            argv += [f"-coverprofile={prof}"]
        argv += ["./" + p if p != "." else "." for p in pkgs] if pkgs else ["./..."]
        module = self._module()
        root = self.root

        def pkg_dir(pkg):
            if module and pkg == module:
                return "."
            if module and pkg.startswith(module + "/"):
                return pkg[len(module) + 1:]
            return pkg

        def parse(text):
            res: dict[str, Result] = {}
            outputs: dict[str, list] = {}
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                t = ev.get("Test")
                if not t:
                    continue
                key = f"{pkg_dir(ev.get('Package', ''))}::{t}"
                act = ev.get("Action")
                if act == "output":
                    outputs.setdefault(key, []).append(ev.get("Output", ""))
                elif act in ("pass", "fail", "skip"):
                    st = {"pass": "passed", "fail": "failed", "skip": "skipped"}[act]
                    out = "".join(outputs.get(key, []))
                    res[key] = Result(id=key, state=st, duration=ev.get("Elapsed"),
                                      message=out if st != "passed" else "", output=out, name=t)
            return list(res.values())

        def cov():
            if not coverage:
                return {}
            out: dict[str, FileCoverage] = {}
            for line in _read(prof).splitlines()[1:]:
                m = re.match(r"(.+):(\d+)\.\d+,(\d+)\.\d+ \d+ (\d+)$", line)
                if not m:
                    continue
                f = m.group(1)
                if module and f.startswith(module + "/"):
                    f = f[len(module) + 1:]
                p = str((root / f).resolve())
                fc = out.setdefault(p, FileCoverage())
                hit = int(m.group(4)) > 0
                for n in range(int(m.group(2)), int(m.group(3)) + 1):
                    (fc.covered if hit else fc.missed).add(n)
            for fc in out.values():
                both = fc.covered & fc.missed
                fc.partial |= both
                fc.missed -= both
            return out
        return RunPlan([Step(argv, self.root, {}, "go test")], parse, cov, self.tmp)


# ---------------------------------------------------------------------------- Rust
class RustAdapter(Adapter):
    id = "rust"
    name = "cargo test"
    language = "rust"

    @classmethod
    def detect(cls, root):
        return (Path(root) / "Cargo.toml").exists()

    def available(self):
        return (True, "") if find_exe("cargo") else (False, "cargo was not found (install Rust with rustup)")

    def discover(self):
        out = []
        for f in _files(self.root, [r".*\.rs"]):
            r = rel(self.root, f)
            parts = Path(r).with_suffix("").parts
            if "src" in parts:          # src/... or <workspace member>/src/...
                mods = [p for p in parts[parts.index("src") + 1:] if p not in ("lib", "main", "mod")]
            else:                       # tests/foo.rs -> its own crate
                mods = []
            stack: list[tuple[int, str]] = []
            pending = False
            depth = 0
            for n, line in enumerate(_read(f).splitlines(), 1):
                s = line.strip()
                m = re.match(r"(?:pub\s+)?mod\s+(\w+)\s*\{", s)
                if m:
                    stack.append((depth, m.group(1)))
                if re.match(r"#\[(tokio::)?test\b", s):
                    pending = True
                elif pending:
                    fm = re.match(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", s)
                    if fm:
                        path = "::".join([*mods, *[x for _d, x in stack], fm.group(1)])
                        out.append(self.item(path, fm.group(1), f, n, "::".join([*mods, *[x for _d, x in stack]])))
                        pending = False
                depth += line.count("{") - line.count("}")
                while stack and depth <= stack[-1][0]:
                    stack.pop()
        return out

    def plan(self, items, coverage=False, debug=False):
        argv = [find_exe("cargo") or "cargo", "test", "--color", "never", "--no-fail-fast", "--"]
        if items:
            argv += [*sorted({i.id for i in items}), "--exact"]
        argv += ["--test-threads=1"]

        def parse(text):
            res = []
            fails: dict[str, str] = {}
            for m in re.finditer(r"^---- (\S+) stdout ----\n(.*?)(?=^---- |\n\n(?:failures|test result):)", text,
                                 re.M | re.S):
                fails[m.group(1)] = m.group(2).strip()
            for m in re.finditer(r"^test (\S+) \.\.\. (ok|FAILED|ignored)", text, re.M):
                st = {"ok": "passed", "FAILED": "failed", "ignored": "skipped"}[m.group(2)]
                res.append(Result(id=m.group(1), state=st, message=fails.get(m.group(1), ""),
                                  name=m.group(1).split("::")[-1]))
            return res
        return RunPlan([Step(argv, self.root, {"CARGO_TERM_COLOR": "never"}, "cargo test")], parse, tmp=self.tmp)


# ---------------------------------------------------------------------------- C# / .NET
class DotnetAdapter(Adapter):
    id = "dotnet"
    name = "dotnet test"
    language = "csharp"

    @staticmethod
    def test_projects(root) -> list[Path]:
        """Project files that reference a test framework (the IDE's own bridge project is never one)."""
        return [p for p in _files(root, [r".*\.csproj", r".*\.fsproj", r".*\.vbproj"], 50)
                if re.search(r"xunit|nunit|MSTest|Microsoft\.NET\.Test\.Sdk", _read(p), re.I)]

    @classmethod
    def detect(cls, root):
        return bool(cls.test_projects(root))

    def available(self):
        return (True, "") if find_exe("dotnet") else (False, "the .NET SDK was not found")

    def discover(self):
        out = []
        for f in _files(self.root, [r".*\.cs"]):
            text = _read(f)
            if not re.search(r"\[(Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)\b", text):
                continue
            ns = ""
            cls = ""
            pending = False
            for n, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                m = re.match(r"namespace\s+([\w.]+)", s)
                if m:
                    ns = m.group(1)
                m = re.match(r"(?:\[[^\]]*\]\s*)*(?:public\s+|internal\s+|sealed\s+|static\s+|partial\s+)*class\s+(\w+)", s)
                if m:
                    cls = m.group(1)
                if re.search(r"\[(Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)\b", s):
                    pending = True
                    if not re.search(r"\b(void|Task)\s+\w+\s*\(", s):
                        continue
                if pending:
                    fm = re.search(r"\b(?:void|Task|async\s+Task)\s+(\w+)\s*\(", s)
                    if fm:
                        fq = ".".join(x for x in (ns, cls, fm.group(1)) if x)
                        out.append(self.item(fq, fm.group(1), f, n, ".".join(x for x in (ns, cls) if x)))
                        pending = False
        return out

    def plan(self, items, coverage=False, debug=False):
        resdir = self.tmp / "trx"
        if resdir.exists():
            shutil.rmtree(resdir, ignore_errors=True)
        steps = []
        for n, proj in enumerate(self.test_projects(self.root)):   # explicit: other .csproj may sit beside it
            argv = [find_exe("dotnet") or "dotnet", "test", str(proj), "--nologo", "--logger",
                    "trx;LogFileName=results.trx", "--results-directory", str(resdir / str(n))]
            if items:
                argv += ["--filter", "|".join(f"FullyQualifiedName={i.id}" for i in items)]
            steps.append(Step(argv, self.root, {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"},
                              f"dotnet test {proj.name}"))

        def parse(_text):
            out = []
            for p in resdir.glob("**/*.trx"):
                out += parse_trx(p)
            return out
        return RunPlan(steps, parse, tmp=self.tmp)


# ---------------------------------------------------------------------------- PHP
class PhpUnitAdapter(Adapter):
    id = "phpunit"
    name = "PHPUnit"
    language = "php"

    @classmethod
    def detect(cls, root):
        root = Path(root)
        return (root / "phpunit.xml").exists() or (root / "phpunit.xml.dist").exists() or \
            "phpunit" in _read(root / "composer.json")

    def _bin(self):
        for p in (self.root / "vendor" / "bin" / "phpunit", self.root / "vendor" / "phpunit" / "phpunit" / "phpunit"):
            if p.exists():
                return [find_exe("php") or "php", str(p)]
        g = find_exe("phpunit")
        return cmd_argv(g) if g else None

    def available(self):
        if not find_exe("php"):
            return False, "PHP was not found"
        if self._bin() is None:
            return False, "PHPUnit is missing: run 'composer require --dev phpunit/phpunit' (Terminal)"
        return True, ""

    def discover(self):
        out = []
        for f in _files(self.root, [r".*Test\.php"]):
            text = _read(f)
            ns = ""
            cls = ""
            pending = False
            for n, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                m = re.match(r"namespace\s+([\w\\]+)\s*;", s)
                if m:
                    ns = m.group(1)
                m = re.match(r"(?:final\s+|abstract\s+)*class\s+(\w+)", s)
                if m:
                    cls = m.group(1)
                if "@test" in s or re.match(r"#\[(\\?PHPUnit\\Framework\\Attributes\\)?Test\]", s):
                    pending = True
                fm = re.match(r"public\s+(?:static\s+)?function\s+(\w+)\s*\(", s)
                if fm and (fm.group(1).startswith("test") or pending):
                    fq = (ns + "\\" + cls) if ns else cls
                    out.append(self.item(f"{fq}::{fm.group(1)}", fm.group(1), f, n, fq))
                    pending = False
        return out

    def plan(self, items, coverage=False, debug=False):
        rep = self.tmp / "phpunit.xml"
        if rep.exists():
            rep.unlink()
        argv = [*(self._bin() or ["phpunit"]), "--log-junit", str(rep), "--colors=never"]
        if items:
            argv += ["--filter", "/(" + "|".join(sorted({re.escape(i.name) for i in items})) + ")$/"]

        def parse(_t):
            res = parse_junit(rep)
            for r in res:
                cls = getattr(r, "_classname", "")
                r.id = f"{cls}::{r.name}"
            return res
        return RunPlan([Step(argv, self.root, {}, "phpunit")], parse, tmp=self.tmp)


# ---------------------------------------------------------------------------- Dart / Flutter
_DART_TEST = re.compile(r"""^(\s*)(?:test|testWidgets)\s*\(\s*(['"])(.+?)\2""")
_DART_GROUP = re.compile(r"""^(\s*)group\s*\(\s*(['"])(.+?)\2""")


class DartAdapter(Adapter):
    id = "dart"
    language = "dart"

    @classmethod
    def detect(cls, root):
        return (Path(root) / "pubspec.yaml").exists() and bool(_files(Path(root) / "test", [r".*_test\.dart"], 1)) \
            if (Path(root) / "test").is_dir() else False

    def __init__(self, root, win=None):
        super().__init__(root, win)
        self.flutter = "flutter:" in _read(self.root / "pubspec.yaml") and "sdk: flutter" in _read(self.root / "pubspec.yaml")
        self.name = "flutter test" if self.flutter else "dart test"
        self.supports_coverage = self.flutter

    def _exe(self):
        return find_exe("flutter" if self.flutter else "dart")

    def available(self):
        return (True, "") if self._exe() else (False, ("Flutter" if self.flutter else "Dart") + " SDK was not found")

    def discover(self):
        out = []
        for f in _files(self.root / "test", [r".*_test\.dart"]):
            for groups, title, line in scan_nested(f, _DART_TEST, _DART_GROUP):
                full = " ".join([*groups, title])
                out.append(self.item(f"{rel(self.root, f)}::{full}", title, f, line, " ".join(groups)))
        return out

    def plan(self, items, coverage=False, debug=False):
        exe = self._exe() or "dart"
        args = ["test", "--machine"] if self.flutter else ["test", "--reporter", "json"]
        if coverage and self.flutter:
            args.append("--coverage")
        if items:
            for i in items:
                args += ["--plain-name", i.id.split("::", 1)[1]] if len(items) == 1 else []
            if len(items) > 1:
                args += ["--name", "^(" + "|".join(re.escape(i.id.split("::", 1)[1]) for i in items) + ")$"]
            args += sorted({rel(self.root, i.file) for i in items})
        argv = cmd_argv(exe, *args)
        root = self.root

        def parse(text):
            tests: dict[int, dict] = {}
            res: dict[int, Result] = {}
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                t = ev.get("type")
                if t == "testStart":
                    tests[ev["test"]["id"]] = ev["test"]
                    ev["_t0"] = ev.get("time", 0)
                    tests[ev["test"]["id"]]["_t0"] = ev.get("time", 0)
                elif t in ("error", "print"):
                    tid = ev.get("testID")
                    r = res.setdefault(tid, Result(state="passed"))
                    if t == "error":
                        r.message += (ev.get("error", "") + "\n" + ev.get("stackTrace", "")).strip() + "\n"
                    else:
                        r.output += ev.get("message", "") + "\n"
                elif t == "testDone":
                    tid = ev.get("testID")
                    info = tests.get(tid, {})
                    if ev.get("hidden") or not info.get("url") and not info.get("root_url"):
                        if ev.get("result") == "success":
                            continue
                    r = res.setdefault(tid, Result())
                    r.state = "skipped" if ev.get("skipped") else {"success": "passed", "failure": "failed"}.get(
                        ev.get("result"), "error")
                    r.duration = (ev.get("time", 0) - info.get("_t0", 0)) / 1000.0
                    url = info.get("root_url") or info.get("url") or ""
                    r.file = _file_url(url)
                    r.line = info.get("root_line") or info.get("line") or 0
                    r.name = info.get("name", "")
                    r.id = f"{rel(root, r.file)}::{r.name}" if r.file else r.name
            return [r for r in res.values() if r.id and not r.id.startswith("loading ")]

        def cov():
            return parse_lcov(root / "coverage" / "lcov.info", root) if coverage and self.flutter else {}
        return RunPlan([Step(argv, self.root, {}, self.name)], parse, cov, self.tmp)


# ---------------------------------------------------------------------------- Java (JUnit 5)
class JavaAdapter(Adapter):
    id = "junit"
    name = "JUnit 5"
    language = "java"

    @classmethod
    def detect(cls, root):
        for f in _files(root, [r".*Test\.java", r"Test.*\.java", r".*Tests\.java"], 20):
            if "@Test" in _read(f):
                return True
        return False

    def junit_jar(self) -> Path:
        return LOCAL / "tools" / "junit" / f"junit-platform-console-standalone-{JUNIT_VERSION}.jar"

    def available(self):
        if (self.root / "pom.xml").exists() and find_exe("mvn"):
            return True, ""
        if not find_exe("javac") or not find_exe("java"):
            return False, "a JDK (javac/java) was not found"
        if not self.junit_jar().exists():
            return True, f"the JUnit console launcher is downloaded on the first run ({JUNIT_URL})"
        return True, ""

    def ensure_jar(self, log=print, reporter=None) -> bool:
        """Download the JUnit console launcher once.  With a radide.progress reporter (worker thread):
        byte progress and Cancel."""
        jar = self.junit_jar()
        if jar.exists():
            return True
        jar.parent.mkdir(parents=True, exist_ok=True)
        log(f"Downloading {JUNIT_URL}")
        if reporter is not None:
            from ..progress import Cancelled, download
            try:
                download(JUNIT_URL, jar, reporter, timeout=120)
                return True
            except Cancelled:
                log("download cancelled")
                return False
            except OSError as e:
                log(f"download failed: {e}")
                return False
        try:
            import urllib.request
            tmp = jar.with_suffix(".part")
            with urllib.request.urlopen(JUNIT_URL, timeout=120) as r, open(tmp, "wb") as f:  # noqa: S310
                shutil.copyfileobj(r, f)
            tmp.replace(jar)
            return True
        except OSError as e:
            log(f"download failed: {e}")
            return False

    def discover(self):
        out = []
        for f in _files(self.root, [r".*\.java"]):
            text = _read(f)
            if "@Test" not in text and "@ParameterizedTest" not in text:
                continue
            pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
            cls = re.search(r"\bclass\s+(\w+)", text)
            fq = ".".join(x for x in ((pkg.group(1) if pkg else ""), (cls.group(1) if cls else f.stem)) if x)
            pending = False
            for n, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if re.match(r"@(Test|ParameterizedTest|RepeatedTest)\b", s):
                    pending = True
                    continue
                if pending:
                    m = re.search(r"\bvoid\s+(\w+)\s*\(", s)
                    if m:
                        out.append(self.item(f"{fq}#{m.group(1)}", m.group(1), f, n, fq))
                        pending = False
        return out

    def plan(self, items, coverage=False, debug=False):
        if (self.root / "pom.xml").exists() and find_exe("mvn"):
            argv = cmd_argv(find_exe("mvn"), "-q", "test")
            if items:
                argv.append("-Dtest=" + ",".join(i.id for i in items))
            reports = self.root / "target" / "surefire-reports"
            steps = [Step(argv, self.root, {}, "mvn test")]
        else:
            jar = self.junit_jar()
            classes = self.tmp / "classes"
            reports = self.tmp / "reports"
            for d in (classes, reports):
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(parents=True, exist_ok=True)
            srcs = [str(f) for f in _files(self.root, [r".*\.java"])]
            argfile = self.tmp / "sources.txt"
            argfile.write_text("\n".join(f'"{s}"'.replace("\\", "/") for s in srcs), encoding="utf-8")
            libs = [str(jar)] + [str(p) for p in (self.root / "lib").glob("*.jar")] + \
                [str(p) for p in (self.root / "libs").glob("*.jar")]
            cp = os.pathsep.join(libs)
            steps = [Step([find_exe("javac") or "javac", "-encoding", "UTF-8", "-g", "-d", str(classes), "-cp", cp,
                           f"@{argfile}"], self.root, {}, "javac"),
                     Step([find_exe("java") or "java", "-jar", str(jar), "execute", "--disable-banner",
                           "--details=tree", "--class-path", os.pathsep.join([str(classes), *libs[1:]]),
                           f"--reports-dir={reports}",
                           *([f"--select-method={i.id}" for i in items] if items else ["--scan-class-path"])],
                          self.root, {}, "JUnit console launcher")]

        def parse(_t):
            out = []
            for p in sorted(reports.glob("*.xml")):
                for r in parse_junit(p):
                    cls = getattr(r, "_classname", "")
                    nm = re.sub(r"\(.*\)$", "", r.name)
                    r.id = f"{cls}#{nm}"
                    r.name = nm
                    out.append(r)
            return out
        return RunPlan(steps, parse, tmp=self.tmp)


# ---------------------------------------------------------------------------- Ring
RING_RUNNER = r'''# generated by RAD IDE Test Explorer
load "{file}"
func main
{calls}
func radtest name
    t0 = clock()
    try
        call name()
        see "@@RADTEST@@" + '{{"id": "{rel}::' + name + '", "state": "passed", "duration": ' + ((clock() - t0) / clockspersecond()) + "}}" + nl
    catch
        msg = substr(substr(cCatchError, "\", "/"), '"', "'")
        msg = substr(msg, nl, " ")
        see "@@RADTEST@@" + '{{"id": "{rel}::' + name + '", "state": "failed", "duration": ' + ((clock() - t0) / clockspersecond()) + ', "message": "' + msg + '"}}' + nl
    done

func assertEqual expected, actual
    if expected != actual
        raise("assertEqual failed: expected <" + expected + "> but was <" + actual + ">")
    ok

func assertTrue cond
    if not cond raise("assertTrue failed") ok
'''


class RingAdapter(Adapter):
    id = "ring"
    name = "Ring tests"
    language = "rad-ring-qt"

    @staticmethod
    def _test_files(root):
        return _files(root, [r"test_.*\.ring", r".*_test\.ring", r"test.*\.ring"])

    @classmethod
    def detect(cls, root):
        return any(re.search(r"^\s*func\s+test\w*", _read(f), re.M | re.I) for f in cls._test_files(root))

    def _ring(self):
        try:
            from ..languages.ring_qt import RingQtPlugin
            return RingQtPlugin().find_interpreter("")
        except Exception:  # noqa: BLE001
            return find_exe("ring")

    def available(self):
        return (True, "") if self._ring() else (False, "the Ring interpreter was not found")

    def discover(self):
        out = []
        for f in self._test_files(self.root):
            for n, line in enumerate(_read(f).splitlines(), 1):
                m = re.match(r"\s*func\s+(test\w*)", line, re.I)
                if m:
                    out.append(self.item(f"{rel(self.root, f)}::{m.group(1)}", m.group(1), f, n, rel(self.root, f)))
        return out

    def plan(self, items, coverage=False, debug=False):
        all_items = items or self.discover()
        steps = []
        for f in sorted({i.file for i in all_items}):
            r = rel(self.root, f)
            names = [i.name for i in all_items if i.file == f]
            text = _read(Path(f))
            body = text if not re.search(r"^\s*func\s+main\b", text, re.M | re.I) else \
                re.sub(r"^\s*func\s+main\b", "func rad_original_main", text, flags=re.M | re.I)
            src_dir = Path(f).parent

            def absolute(m):                       # the copy lives in a temp folder: load "x.ring" by full path
                target = src_dir / m.group(2)
                if not Path(m.group(2)).is_absolute() and target.exists():
                    return f'{m.group(1)}"{target.as_posix()}"'
                return m.group(0)
            body = re.sub(r'^(\s*load\s+)"([^"]+)"', absolute, body, flags=re.M | re.I)
            copy =self.tmp / ("radtest_" + Path(f).name)
            copy.write_text(body, encoding="utf-8")
            runner = self.tmp / ("run_" + Path(f).name)
            runner.write_text(RING_RUNNER.format(file=str(copy).replace("\\", "/"), rel=r,
                                                 calls="\n".join(f'    radtest("{n}")' for n in names)),
                              encoding="utf-8")
            steps.append(Step([self._ring() or "ring", str(runner)], Path(f).parent, {}, f"ring {r}"))

        def parse(text):
            return [Result(id=d.get("id", ""), state=d.get("state", "passed"), duration=_secs(d.get("duration")),
                           message=d.get("message", "")) for d in _markers(text)]
        return RunPlan(steps, parse, tmp=self.tmp)


# ---------------------------------------------------------------------------- VB / BASIC
class VBAdapter(Adapter):
    id = "vb"
    name = "VB tests"
    language = "vb"

    @classmethod
    def detect(cls, root):
        from .vbtest import is_test_module
        return any(is_test_module(p.name) for p in Path(root).glob("*.bas"))

    def discover(self):
        from .vbtest import is_test_module
        out = []
        for f in sorted(self.root.glob("*.bas")):
            if not is_test_module(f.name):
                continue
            for n, line in enumerate(_read(f).splitlines(), 1):
                m = re.match(r"\s*(?:public\s+)?sub\s+(test\w*)\s*\(\s*\)", line, re.I)
                if m:
                    out.append(self.item(f"{f.name}::{m.group(1)}", m.group(1), f, n, f.name))
        return out

    def plan(self, items, coverage=False, debug=False):
        out = self.tmp / "vb.json"
        if out.exists():
            out.unlink()
        from ..paths import python_root      # never _internal of a release build (another Python version)
        ide_root = str(python_root())
        argv = [sys.executable, "-m", "radide.testing.vbtest", str(self.root), str(out), *[i.id for i in items or []]]

        def parse(_t):
            try:
                data = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return []
            return [Result(id=r["id"], state=r["state"], duration=r.get("duration"), message=r.get("message", ""),
                           output=r.get("output", ""), file=r.get("file", ""), line=r.get("line", 0))
                    for r in data.get("results", [])]
        return RunPlan([Step(argv, self.root, {"PYTHONPATH": ide_root}, "VB tests")], parse, tmp=self.tmp)


ADAPTERS = [PythonAdapter, NodeAdapter, GoAdapter, RustAdapter, DotnetAdapter, PhpUnitAdapter, DartAdapter,
            JavaAdapter, RingAdapter, VBAdapter]
try:                                     # Ruby: Rails minitest / RSpec (radide/testing/ruby_tests.py)
    from .ruby_tests import ADAPTERS as _RUBY_ADAPTERS
    ADAPTERS += _RUBY_ADAPTERS
except Exception:  # noqa: BLE001 - a broken adapter module must not hide the others
    pass


def adapters_for(root: Path, win=None) -> list[Adapter]:
    out = []
    for cls in ADAPTERS:
        try:
            if cls.detect(Path(root)):
                out.append(cls(Path(root), win))
        except Exception:  # noqa: BLE001 - a broken detector must not hide the others
            continue
    return out


def adapter_for(root: Path, win=None) -> Adapter | None:
    a = adapters_for(root, win)
    return a[0] if a else None


def match_results(items: list[TestItem], results: list[Result], root: Path) -> tuple[list, list]:
    """Pair results with discovered items: by id, then (file, line), then (file, name), then name.
    Returns ([(item, result)], [unmatched results])."""
    by_id = {i.id: i for i in items}
    by_fl = {}
    by_fn = {}
    by_name: dict[str, list] = {}
    for i in items:
        if i.file:
            k = str(Path(i.file).resolve()).lower() if i.file else ""
            by_fl[(k, i.line)] = i
            by_fn.setdefault((k, i.name), i)
        by_name.setdefault(i.name, []).append(i)
    pairs, rest = [], []
    for r in results:
        it = by_id.get(r.id)
        if it is None and r.id:
            base = re.sub(r"[\[(].*$", "", r.id)            # parametrized cases -> their function
            it = by_id.get(base) if base != r.id else None
        if it is None and r.file:
            k = str(Path(r.file).resolve()).lower()
            it = by_fl.get((k, r.line)) or by_fn.get((k, r.name))
        if it is None and r.name and len(by_name.get(r.name, [])) == 1:
            it = by_name[r.name][0]
        if it is None and r.id and "::" in r.id:          # rust/go: last segment
            last = r.id.split("::")[-1]
            if len(by_name.get(last, [])) == 1:
                it = by_name[last][0]
        if it is None:
            rest.append(r)
        else:
            pairs.append((it, r))
    return pairs, rest


__all__ = ["TestItem", "Result", "FileCoverage", "RunPlan", "Step", "Adapter", "ADAPTERS", "adapters_for",
           "adapter_for", "match_results", "parse_junit", "parse_trx", "parse_lcov", "coverage_py_json",
           "find_exe", "work_dir", "probe_python", "PythonAdapter", "NodeAdapter", "GoAdapter", "RustAdapter",
           "DotnetAdapter", "PhpUnitAdapter", "DartAdapter", "JavaAdapter", "RingAdapter", "VBAdapter"]
