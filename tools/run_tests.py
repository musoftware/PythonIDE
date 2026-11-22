r"""One runner for every RAD IDE test script under samples/Tests - discovered automatically.

Quick entry points (run_tests.bat at the repository root offers the same as a menu):
    python tools/run_tests.py smoke              # ~5-10 min: pyflakes + the fastest check of each area
    python tools/run_tests.py changed            # suites related to the files changed vs HEAD (--base main: vs main)
    python tools/run_tests.py area designer      # one or more areas (see "python tools/run_tests.py areas")
    python tools/run_tests.py full               # everything runnable, sequential, HTML + Markdown report
    python tools/run_tests.py list               # what was discovered, grouped by tier
    python tools/run_tests.py check              # registry / tests.json problems (CI runs this)
Classic filters (combine with any of the above, or alone):
    python tools/run_tests.py --tier fast        # a tier ("toolchain" = every toolchain:<name> tier, "all")
    python tools/run_tests.py --only CarDiag --skip "VSX/*"

Discovery: every samples/Tests/**/{test_*,check_*,qa_*,smoke_*,*_test}.py is a test (not All/, not files starting
with "_", not inside node_modules / .venv / __pycache__). Its settings come from, lowest to highest priority:
  1. a guess from the source (downloads -> "network", a compiler -> "toolchain:<x>", otherwise "full" - never
     "fast", a folder promotes its quick tests with tests.json; "[scratch folder]" in the docstring -> the scratch folder is passed as first argument),
  2. "defaults" of tests.json files in the script's folder and its parents (up to samples/Tests),
  3. tools/tests_registry.json (central, curated: tier, args, timeouts, needs, smoke, variants with an "id"),
  4. the script's own entry in the nearest tests.json ("tests": {"test_x.py": {...}, "test_x.py@long": {...}}).
tests.json format:
  {"defaults": {"tier": "full", "area": "e2e", "timeout": 900},
   "tests": {"test_a.py": {"tier": "fast", "smoke": true}, "test_a.py@long": {"args": ["--long"], "tier": "manual"}},
   "ignore": ["test_helper_not_a_test.py"]}
Keys: tier, args ("{scratch}" = the per-test scratch folder), timeout (s), env, needs, note, area, smoke, kind.

Every test runs in its own process, from the repository root, with:
  * its own scratch folder (TEMP / TMP point into it, QA_OUT too);
  * the offscreen Qt environment (QT_QPA_PLATFORM=offscreen, QT_QPA_FONTDIR, RADIDE_NO_BROWSER=1, no GPU,
    PYTHONIOENCODING=utf-8) unless already set;
  * a unique QSettings name: QA_NAME=<slug> (the qh.py harness uses it as the application name) and
    RADIDE_TEST_ORG=RADIDE-TEST-<slug> for tests that read it;
  * a timeout; on Windows the test and everything it started are in a Job Object, so processes it leaves behind
    (dev servers, emulators, debuggers) are ended when it finishes. Nothing else is ever killed.
A failed test is run once more (--retries): when the second run passes it is reported as "flaky" (not a failure).
Reports: results.json, summary.md, report.html, junit.xml and one log per test in --report-dir; with
GITHUB_STEP_SUMMARY set the Markdown summary is appended to it. The exit code is the number of failed tests.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import html as _html
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape, quoteattr as _xml_attr

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "samples" / "Tests"
REGISTRY = Path(__file__).resolve().parent / "tests_registry.json"

# tiers that "all" / "full" do NOT include: they need inputs a plain run cannot give, or another entry runs them
NOT_IN_ALL = {"manual", "covered", "aggregate", "project"}
DISCOVER = re.compile(r"^(test_.+|.+_test|check_.+|qa_.+|smoke_.+)\.py$")
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", ".dart_tool", ".gradle", "build", "dist",
             "target", "bin", "obj"}
TOP_IGNORE = {"All"}                     # archive of old test projects (samples/Tests/All/INDEX.md)

# areas: name -> folders (paths under samples/Tests). A test belongs to every area whose folder contains it, plus
# its own top folder (lower case) and an explicit "area" from the registry / tests.json.
AREAS = {
    "designer": ["Designer", "FlutterDesigner", "Components", "UserControls", "Blend", "Variants", "Motion",
                 "Localization", "Imaging", "DataBinding", "Performance/Designer"],
    "native": ["Native"],
    "vsx": ["VSX"],
    "events": ["Events"],
    "robustness": ["Robustness"],
    "fuzz": ["Fuzz"],
    "a11y": ["Accessibility"],
    "e2e": ["E2E"],
    "crawler": ["Crawler"],
    "features": ["FeatureMatrix", "Coverage"],
    "examples": ["Examples"],
    "languages": ["QA/AllLanguages", "Languages", "Solutions", "ForeignProjects", "OpenFolder", "Examples"],
    "perf": ["Performance"],
    "debugger": ["Debugger", "Assembly/NativeDebug", "QA/AllLanguages"],
    "asm": ["Assembly"],
    "dotnet": ["DotNet", "Tutorials/VisualStudioProjects", "Native/test_native_dotnet.py",
               "Native/test_native_modern_dotnet.py"],
    "firmware": ["Firmware", "PE"],
    "cardiag": ["CarDiag"],
    "retro": ["Retro"],
    "mobile": ["Mobile", "FlutterDesigner"],
    "ui": ["UI", "I18n", "ShellIntegration", "Accessibility", "QA/Integration"],
    "collab": ["Collab"],
    "vb6": ["VB6Business", "VB6Compat", "VB6", "Native/VB6", "Components/RatingBar_VB6Frm"],
    "release": ["Release", "Installer", "Deploy"],
    "tutorials": ["Tutorials"],
}
# "changed": source path (regex, from the repository root) -> areas. Unmapped radide/ changes -> smoke only.
CHANGE_MAP = [
    (r"^radide/(designer|properties|toolbox|layout|document|model|controls|components|blend|undo)", ["designer", "events", "robustness"]),
    (r"^radide/(motion|variants|devices)", ["designer", "mobile"]),
    (r"^radide/(flutter|mobile)", ["mobile"]),
    (r"^radide/(deploy/native|runtimes/native|runtimes/dotnet)", ["native"]),
    (r"^radide/deploy/", ["release", "native"]),
    (r"^radide/(vsx|web/vsx)", ["vsx"]),
    (r"^radide/(asm|asm_intel|asm_lint|asm_sim|emu8086)", ["asm"]),
    (r"^radide/(nativedbg|debug|dap)|^radide/features/(native_debug|debug)", ["debugger"]),
    (r"^radide/(languages|runtimes|foreign|importers)/", ["languages", "events"]),
    (r"^radide/runtimes/(vb|vbrun|vbinterp)|^radide/languages/vb_", ["vb6"]),
    (r"^radide/dotnet", ["dotnet"]),
    (r"^radide/(firmware|pe)/", ["firmware"]),
    (r"^radide/cardiag", ["cardiag"]),
    (r"^radide/retro", ["retro"]),
    (r"^radide/(i18n|theme|shell_integration)|^radide/features/(ui_language|dock_|shell_)", ["ui", "a11y"]),
    (r"^radide/collab", ["collab"]),
    (r"^radide/tutorials", ["tutorials"]),
    (r"^radide/(app|monaco_editor|editor)\.py", ["ui", "e2e", "a11y", "crawler"]),
    (r"^radide/features/", ["ui", "features", "crawler"]),
    (r"^radide/(model|solution|safeio)\.py", ["robustness", "fuzz"]),
    (r"^samples/Examples/", ["examples"]),
    (r"^samples/VB6/", ["vb6"]),
]

GUI_ENV = {
    "QT_QPA_PLATFORM": "offscreen",
    "QT_QPA_FONTDIR": r"C:\Windows\Fonts" if os.name == "nt" else "/usr/share/fonts",
    "RADIDE_NO_BROWSER": "1",
    "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu --disable-gpu-compositing",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",            # the log keeps every line even when a test hangs and is killed
}

SUMMARY_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s+(?:checks?\s+)?passed", re.I)
LINE_RE = re.compile(r"^\s*(PASS|FAIL|SKIP)\b")
_print_lock = threading.Lock()


def say(*a, **k):
    with _print_lock:
        print(*a, **k, flush=True)


# ---------------------------------------------------------------------------------------------------- discovery
class Test:
    def __init__(self, raw: dict, defaults: dict):
        self.raw = raw
        self.path = raw["path"]
        self.id = raw.get("id") or re.sub(r"\.py$", "", self.path)
        self.tier = raw["tier"]
        self.kind = raw.get("kind", "script")
        self.args = list(raw.get("args", []))
        self.env = dict(raw.get("env", {}))
        self.needs = list(raw.get("needs", []))
        self.note = raw.get("note", "")
        self.smoke = bool(raw.get("smoke"))
        self.auto = bool(raw.get("_auto"))
        self.source = raw.get("_source", "")
        self.command = list(raw.get("command", []))
        base = self.tier.split(":")[0]
        self.timeout = int(raw.get("timeout") or defaults.get(self.tier) or defaults.get(base) or 1200)
        areas = {self.family.lower()}
        for name, folders in AREAS.items():
            if any(self.path == f or self.path.startswith(f.rstrip("/") + "/") for f in folders):
                areas.add(name)
        extra = raw.get("area") or []
        areas.update([extra] if isinstance(extra, str) else extra)
        self.areas = sorted(areas)

    @property
    def family(self) -> str:
        return self.path.split("/")[0]

    @property
    def file(self) -> Path:
        return TESTS_DIR / self.path

    def slug(self, n: int) -> str:
        s = re.sub(r"[^A-Za-z0-9]+", "_", Path(self.id).name).strip("_")[:28]
        return f"{n:03d}_{s}"


_NET = re.compile(r"open-vsx\.org|github\.com/.+/releases|urllib\.request\.urlopen|requests\.get\(|--download")
_TOOLCHAINS = [("dotnet", r"\bdotnet (build|new|run|publish)\b|shutil\.which\(\"dotnet\"\)"),
               ("flutter", r"\bflutter (run|test|analyze|build)\b"),
               ("freebasic", r"\bfbc\b|FreeBASIC"), ("dos", r"DOSBox"), ("java", r"\bjavac\b|jpackage"),
               ("rust-go", r"\bcargo (build|run)\b|\bgo build\b")]


def guess(rel: str) -> dict:
    """Settings of a discovered script without any registry entry, guessed from its source."""
    try:
        src = (TESTS_DIR / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        src = ""
    head = src[:6000]
    raw: dict = {"_auto": True}
    tier = "full"           # never "fast" by guess: CI's fast tier only takes scripts someone has timed
    for name, pat in _TOOLCHAINS:
        if re.search(pat, head):
            tier = "toolchain:" + name
            break
    if _NET.search(head) and tier == "full":
        tier = "network"
    raw["tier"] = tier
    if re.search(r"[\[<]scratch( folder| dir)?[\]>]", head, re.I):
        raw["args"] = ["{scratch}"]
    return raw


def _walk_tests() -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(TESTS_DIR):
        rel_dir = Path(dirpath).relative_to(TESTS_DIR).as_posix()
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                             and not (rel_dir == "." and d in TOP_IGNORE))
        for f in sorted(filenames):
            if DISCOVER.match(f) and not f.startswith("_"):
                found.append(f if rel_dir == "." else f"{rel_dir}/{f}")
    return found


class Registry:
    def __init__(self, path: Path = REGISTRY):
        self.problems: list[str] = []
        data = json.loads(path.read_text(encoding="utf-8"))
        self.timeouts = data.get("default_timeouts", {})
        self.central: dict[str, dict] = {}
        self.central_variants: list[dict] = []
        for r in data["tests"]:
            if r.get("id"):
                self.central_variants.append(r)
            else:
                self.central[r["path"]] = r
        self._folder_cache: dict[str, dict | None] = {}

    def folder_json(self, rel_dir: str) -> dict | None:
        if rel_dir not in self._folder_cache:
            p = TESTS_DIR / rel_dir / "tests.json" if rel_dir else TESTS_DIR / "tests.json"
            data = None
            if p.is_file():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except ValueError as e:
                    self.problems.append(f"BAD JSON  {p.relative_to(ROOT).as_posix()}: {e}")
            self._folder_cache[rel_dir] = data
        return self._folder_cache[rel_dir]

    def _chain(self, rel: str) -> list[tuple[str, dict]]:
        """tests.json files from samples/Tests down to the script's folder: [(folder, data)]."""
        parts = rel.split("/")[:-1]
        out = []
        for i in range(len(parts) + 1):
            d = "/".join(parts[:i])
            data = self.folder_json(d)
            if data:
                out.append((d, data))
        return out

    def settings(self, rel: str, key: str | None = None) -> dict | None:
        """Merged settings of one script (key = "test_x.py@variant" for a tests.json variant); None = ignored."""
        raw = guess(rel)
        chain = self._chain(rel)
        for _d, data in chain:
            raw.update(data.get("defaults", {}))
        if rel in self.central:
            raw.update(self.central[rel])
            raw["_auto"] = False
        for d, data in reversed(chain):                    # the nearest tests.json that names the script wins
            name = rel[len(d) + 1:] if d else rel
            if name in data.get("ignore", []):
                return None
            entry = data.get("tests", {}).get(key or name)
            if entry is not None:
                raw.update(entry)
                raw["_auto"] = False
                raw["_source"] = (d + "/" if d else "") + "tests.json"
                break
        raw["path"] = rel
        return raw

    def tests(self) -> list[Test]:
        out: list[Test] = []
        on_disk = _walk_tests()
        pytest_dirs = [p for p, r in self.central.items() if r.get("kind") == "pytest"]
        for rel in sorted(set(on_disk) | set(self.central)):
            if any(rel.startswith(d.rstrip("/") + "/") for d in pytest_dirs):
                continue                                    # part of a sample project's own pytest suite
            if not (TESTS_DIR / rel).exists():
                self.problems.append(f"MISSING  {rel}  (in tools/tests_registry.json, not on disk)")
                continue
            raw = self.settings(rel)
            if raw is not None:
                out.append(Test(raw, self.timeouts))
        # variants: central entries with an "id", tests.json keys "name.py@variant"
        for r in self.central_variants:
            if not (TESTS_DIR / r["path"]).exists():
                self.problems.append(f"MISSING  {r['path']}  (variant {r['id']})")
                continue
            base = self.settings(r["path"]) or {"path": r["path"]}
            out.append(Test(dict(base, **r, _auto=False), self.timeouts))
        for d, data in list(self._folder_cache.items()):
            for key in (data or {}).get("tests", {}):
                if "@" in key:
                    name, var = key.split("@", 1)
                    rel = f"{d}/{name}" if d else name
                    if not (TESTS_DIR / rel).exists():
                        self.problems.append(f"MISSING  {rel}  (variant {key} in {d}/tests.json)")
                        continue
                    raw = self.settings(rel, key)
                    if raw is not None:
                        raw.setdefault("id", re.sub(r"\.py$", "", rel) + "@" + var)
                        if raw["id"] == re.sub(r"\.py$", "", rel):
                            raw["id"] += "@" + var
                        out.append(Test(raw, self.timeouts))
        seen = set()
        for t in out:
            if t.id in seen:
                self.problems.append(f"DUPLICATE id {t.id}")
            seen.add(t.id)
        return out


def lint_test(python: str) -> Test:
    return Test({"path": "lint", "id": "lint/pyflakes", "tier": "lint", "kind": "command",
                 "command": ["{python}", "-m", "pyflakes", "radide", "tools"], "timeout": 900,
                 "note": "pyflakes radide tools (must be clean)"}, {})


def load_registry(path: Path = REGISTRY) -> list[Test]:
    return Registry(path).tests()


def tier_matches(tier: str, wanted: list[str]) -> bool:
    for w in wanted:
        if w == "all":
            if tier not in NOT_IN_ALL:
                return True
        elif w == tier or (":" not in w and tier.startswith(w + ":")):
            return True
    return False


def pattern_matches(t: Test, pats: list[str]) -> bool:
    for p in pats:
        if any(ch in p for ch in "*?["):
            if fnmatch.fnmatch(t.id, p) or fnmatch.fnmatch(t.id, "*" + p + "*"):
                return True
        elif p.lower() in t.id.lower():
            return True
    return False


def select(tests: list[Test], tiers: list[str] | None, only: list[str], skip: list[str]) -> list[Test]:
    out = []
    for t in tests:
        if only:
            # --only picks by name; it still respects an explicit --tier
            if not pattern_matches(t, only) or (tiers and not tier_matches(t.tier, tiers)):
                continue
        elif not tier_matches(t.tier, tiers or ["fast"]):
            continue
        if skip and pattern_matches(t, skip):
            continue
        out.append(t)
    return out


def all_areas(tests: list[Test]) -> dict[str, int]:
    c: dict[str, int] = {}
    for t in tests:
        for a in t.areas:
            c[a] = c.get(a, 0) + 1
    return dict(sorted(c.items()))


def select_areas(tests: list[Test], names: list[str]) -> list[Test]:
    want = {n.lower() for n in names}
    return [t for t in tests if want & set(t.areas) and t.tier not in NOT_IN_ALL]


def changed_files(base: str | None) -> list[str]:
    files: set[str] = set()
    cmds = [["git", "diff", "--name-only", "HEAD"], ["git", "ls-files", "--others", "--exclude-standard"]]
    if base:
        cmds.append(["git", "diff", "--name-only", f"{base}...HEAD"])
    for cmd in cmds:
        try:
            out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
        except Exception:  # noqa: BLE001
            continue
        files.update(ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip())
    return sorted(files)


def select_changed(tests: list[Test], files: list[str]) -> tuple[list[Test], list[str]]:
    areas: set[str] = set()
    direct: set[str] = set()
    smoke = False
    for f in files:
        if f.startswith("samples/Tests/"):
            rel = f[len("samples/Tests/"):]
            folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
            for t in tests:                    # tests in the changed folder (or the changed script itself)
                if t.path == rel or (folder and t.path.startswith(folder + "/")):
                    direct.add(t.id)
            continue
        hit = False
        for pat, names in CHANGE_MAP:
            if re.search(pat, f):
                areas.update(names)
                hit = True
        if f.startswith(("radide/", "tools/")) and not hit:
            smoke = True
        if f.startswith("radide/") or f in ("tools/run_tests.py", "tools/tests_registry.json"):
            smoke = True
    sel = [t for t in tests if t.tier not in NOT_IN_ALL and (
        t.id in direct or (set(t.areas) & areas and tier_matches(t.tier, ["fast", "full"])) or (smoke and t.smoke))]
    return sel, sorted(areas) + (["smoke"] if smoke else [])


def check_registry(tests: list[Test], reg: Registry) -> int:
    for p in reg.problems:
        say(p)
    auto = [t for t in tests if t.auto]
    for t in auto:
        say(f"AUTO  {t.id}  -> tier {t.tier}" + (f" args {' '.join(t.args)}" if t.args else "")
            + "  (guessed; give it an entry in its folder's tests.json or tools/tests_registry.json)")
    tiers = {}
    for t in tests:
        tiers[t.tier] = tiers.get(t.tier, 0) + 1
    say(f"{len(tests)} tests discovered ({len(auto)} with guessed settings), {len(reg.problems)} problem(s); "
        + ", ".join(f"{k}={v}" for k, v in sorted(tiers.items())))
    return len(reg.problems)


# --------------------------------------------------------------------------------------------- process control
class _Job:
    """A Windows Job Object: every process the test starts stays in it, so leftovers can be ended."""

    def __init__(self):
        self.h = None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes
        self.k32 = k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
                                                  wintypes.LPVOID]
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

        class BasicLimit(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class ExtLimit(ctypes.Structure):
            _fields_ = [("Basic", BasicLimit), ("Io", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        class Accounting(ctypes.Structure):
            _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                        ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                        ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                        ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]

        self.Accounting = Accounting
        self.ctypes = ctypes
        h = k32.CreateJobObjectW(None, None)
        if not h:
            return
        info = ExtLimit()
        info.Basic.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info))
        self.h = h

    def assign(self, proc: subprocess.Popen) -> None:
        if self.h:
            self.k32.AssignProcessToJobObject(self.h, int(proc._handle))  # noqa: SLF001

    def active(self) -> int:
        if not self.h:
            return 0
        acc = self.Accounting()
        ok = self.k32.QueryInformationJobObject(self.h, 1, self.ctypes.byref(acc), self.ctypes.sizeof(acc), None)
        return int(acc.ActiveProcesses) if ok else 0

    def terminate(self) -> None:
        if self.h:
            self.k32.TerminateJobObject(self.h, 1)

    def close(self) -> None:
        if self.h:
            self.k32.CloseHandle(self.h)
            self.h = None


def _kill_tree(proc: subprocess.Popen, job: _Job) -> None:
    job.terminate()
    if proc.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            import signal
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass


# ------------------------------------------------------------------------------------------------------ running
def build_command(t: Test, python: str, scratch: Path) -> tuple[list[str], Path]:
    args = [a.replace("{scratch}", str(scratch)) for a in t.args]
    if t.kind == "command":
        return [a.replace("{python}", python) for a in t.command] + args, ROOT
    if t.kind == "pytest":
        return [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(t.file), *args], t.file.parent
    return [python, str(t.file), *args], ROOT


def build_env(t: Test, slug: str, scratch: Path, isolate_temp: bool) -> dict:
    env = dict(os.environ)
    for k, v in GUI_ENV.items():
        env.setdefault(k, v)
    tmp = scratch / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    if isolate_temp:
        env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(tmp)
    env["QA_OUT"] = str(scratch / "qa")
    env["QA_NAME"] = slug
    env["RADIDE_TEST_ORG"] = "RADIDE-TEST-" + slug
    env["RADIDE_TEST_SCRATCH"] = str(scratch)
    env.update({k: str(v).replace("{scratch}", str(scratch)) for k, v in t.env.items()})
    return env


def parse_output(text: str) -> dict:
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m:
            counts[m.group(1)] += 1
    passed = total = None
    for m in SUMMARY_RE.finditer(text):
        passed, total = int(m.group(1)), int(m.group(2))     # the last summary line wins
    if total is None and (counts["PASS"] or counts["FAIL"]):
        passed, total = counts["PASS"], counts["PASS"] + counts["FAIL"]
    fails = [ln.strip()[:300] for ln in text.splitlines() if ln.lstrip().startswith("FAIL")][:30]
    return {"checks_passed": passed, "checks_total": total, "pass_lines": counts["PASS"],
            "fail_lines": counts["FAIL"], "skip_lines": counts["SKIP"], "fail_messages": fails}


def run_once(t: Test, attempt: int, n: int, opts, log_dir: Path) -> dict:
    slug = t.slug(n) + (f"_r{attempt}" if attempt > 1 else "")
    scratch = Path(opts.scratch_root) / slug
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    cmd, cwd = build_command(t, opts.python, scratch)
    env = build_env(t, slug, scratch, not opts.no_isolate_temp)
    log_path = log_dir / (slug + ".log")
    res = {"attempt": attempt, "command": cmd, "cwd": str(cwd), "scratch": str(scratch), "log": str(log_path)}
    if t.kind != "command" and not t.file.exists():
        res.update(status="error", returncode=None, duration=0.0, error=f"script not found: {t.file}")
        log_path.write_text(res["error"] + "\n", encoding="utf-8")
        return res
    flags = 0
    kw = {}
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    job = _Job()
    start = time.monotonic()
    timed_out = False
    chunks: list[str] = []
    with open(log_path, "w", encoding="utf-8", newline="\n") as log:
        log.write(f"# {t.id}  (tier {t.tier}, attempt {attempt}, timeout {t.timeout}s)\n# cwd: {cwd}\n"
                  f"# cmd: {subprocess.list2cmdline(cmd)}\n# scratch: {scratch}\n\n")
        log.flush()
        try:
            proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, creationflags=flags, **kw)
        except OSError as e:
            res.update(status="error", returncode=None, duration=0.0, error=str(e))
            log.write(f"cannot start: {e}\n")
            job.close()
            return res
        job.assign(proc)

        def pump():
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                chunks.append(line)
                log.write(line + "\n")
                if opts.verbose:
                    say(f"  | {line}")
            proc.stdout.close()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=t.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc, job)
            proc.wait(timeout=30)
        leftovers = job.active()
        job.terminate()                  # processes the test started and left running
        reader.join(timeout=15)
        job.close()
        duration = time.monotonic() - start
        log.write(f"\n# exit code {proc.returncode}, {duration:.1f}s"
                  + (", TIMEOUT" if timed_out else "") + (f", {leftovers} leftover process(es) ended" if leftovers else "")
                  + "\n")
    text = "\n".join(chunks)
    info = parse_output(text)
    rc = proc.returncode
    if timed_out:
        status = "timeout"
    elif rc == 0:                        # the contract: exit code = number of failed checks
        status = "passed"
    else:
        status = "failed"
    res.update(status=status, returncode=rc, duration=round(duration, 1), leftover_processes=leftovers,
               tail="\n".join(chunks[-opts.tail:]), **info)
    if status == "passed" and not opts.keep_scratch:
        shutil.rmtree(scratch, ignore_errors=True)
    return res


def run_test(t: Test, n: int, opts, log_dir: Path) -> dict:
    attempts = [run_once(t, 1, n, opts, log_dir)]
    while attempts[-1]["status"] in ("failed", "timeout") and len(attempts) <= opts.retries:
        say(f"  retry {t.id} ({attempts[-1]['status']})")
        attempts.append(run_once(t, len(attempts) + 1, n, opts, log_dir))
    final = dict(attempts[-1])
    if len(attempts) > 1 and final["status"] == "passed":
        final["status"] = "flaky"
    final.update(id=t.id, path=t.path, tier=t.tier, family=t.family, needs=t.needs, note=t.note,
                 timeout=t.timeout, attempts=[{k: a.get(k) for k in ("attempt", "status", "returncode", "duration",
                                                                       "log")} for a in attempts])
    return final


# ------------------------------------------------------------------------------------------------------ reports
FAILING = ("failed", "timeout", "error")


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def totals(results: list[dict]) -> dict:
    c = {s: 0 for s in ("passed", "flaky", "failed", "timeout", "error")}
    for r in results:
        c[r["status"]] = c.get(r["status"], 0) + 1
    c["total"] = len(results)
    c["failures"] = sum(c[s] for s in FAILING)
    return c


def _fmt_checks(r: dict) -> str:
    if r.get("checks_total") is None:
        return "-"
    s = f"{r['checks_passed']}/{r['checks_total']}"
    if r.get("skip_lines"):
        s += f" ({r['skip_lines']} skip)"
    return s


def write_markdown(results: list[dict], meta: dict, path: Path) -> str:
    c = meta["totals"]
    head = "PASSED" if c["failures"] == 0 else "FAILED"
    lines = [f"## RAD IDE tests: {head}",
             "",
             f"Tiers: `{', '.join(meta['tiers'])}` | {c['total']} tests | {c['passed']} passed | {c['flaky']} flaky | "
             f"{c['failed']} failed | {c['timeout']} timed out | {c['error']} errors | {meta['duration']:.0f}s",
             "",
             f"Commit `{meta.get('commit', '')[:10]}` on `{meta.get('branch', '')}`, Python {meta['python_version']}, "
             f"{meta['platform']}",
             "",
             "| Status | Test | Tier | Checks | Time |",
             "|---|---|---|---|---|"]
    order = {"failed": 0, "timeout": 1, "error": 2, "flaky": 3, "passed": 4}
    for r in sorted(results, key=lambda r: (order.get(r["status"], 9), r["id"])):
        lines.append(f"| {r['status'].upper()} | `{r['id']}` | {r['tier']} | {_fmt_checks(r)} | {r['duration']:.0f}s |")
    bad = [r for r in results if r["status"] in FAILING or r["status"] == "flaky"]
    if bad:
        lines += ["", "### Failures and flaky tests", ""]
        for r in bad:
            lines.append(f"<details><summary><b>{r['status'].upper()}</b> {r['id']} (exit {r.get('returncode')}, "
                         f"attempts {len(r['attempts'])})</summary>")
            lines.append("")
            if r.get("fail_messages"):
                lines += ["```text", *r["fail_messages"][:15], "```"]
            if r.get("error"):
                lines += ["", f"Error: {r['error']}"]
            tail = (r.get("tail") or "").splitlines()[-40:]
            if tail:
                lines += ["", "Last lines of the log:", "", "```text", *tail, "```"]
            lines += ["", "</details>", ""]
    md = "\n".join(lines) + "\n"
    path.write_text(md, encoding="utf-8")
    return md


_XML_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _x(s) -> str:
    return _xml_escape(_XML_BAD.sub("?", str(s)))


def _xa(s) -> str:
    return _xml_attr(_XML_BAD.sub("?", str(s)))


def write_junit(results: list[dict], meta: dict, path: Path) -> None:
    c = meta["totals"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<testsuites name="radide" tests="{c["total"]}" failures="{c["failed"] + c["timeout"]}" '
           f'errors="{c["error"]}" time="{meta["duration"]:.1f}">']
    by_tier: dict[str, list[dict]] = {}
    for r in results:
        by_tier.setdefault(r["tier"], []).append(r)
    for tier, rs in by_tier.items():
        f = sum(r["status"] in ("failed", "timeout") for r in rs)
        e = sum(r["status"] == "error" for r in rs)
        tt = sum(r["duration"] for r in rs)
        out.append(f'  <testsuite name={_xa("radide." + tier)} tests="{len(rs)}" failures="{f}" errors="{e}" '
                   f'skipped="0" time="{tt:.1f}" timestamp={_xa(meta["started"])}>')
        for r in rs:
            out.append(f'    <testcase classname={_xa("samples.Tests." + r["family"])} name={_xa(r["id"])} '
                       f'file={_xa("samples/Tests/" + r["path"])} time="{r["duration"]:.1f}">')
            if r["status"] == "flaky":
                out.append('      <properties><property name="flaky" value="true"/></properties>')
            if r["status"] in ("failed", "timeout"):
                msg = (r.get("fail_messages") or [f"exit code {r.get('returncode')}"])[0]
                if r["status"] == "timeout":
                    msg = f"timed out after {r['timeout']}s"
                body = "\n".join(r.get("fail_messages") or [])
                out.append(f'      <failure message={_xa(msg)} type="{r["status"]}">{_x(body)}</failure>')
            elif r["status"] == "error":
                out.append(f'      <error message={_xa(r.get("error", "error"))}/>')
            out.append(f'      <system-out>{_x(r.get("tail", ""))}</system-out>')
            out.append('    </testcase>')
        out.append('  </testsuite>')
    out.append('</testsuites>')
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------------------- main
def write_html(results: list[dict], meta: dict, path: Path) -> None:
    c = meta["totals"]
    e = _html.escape
    order = {"failed": 0, "timeout": 1, "error": 2, "flaky": 3, "passed": 4}
    rows = []
    for r in sorted(results, key=lambda r: (order.get(r["status"], 9), r["id"])):
        log = os.path.relpath(r["log"], path.parent) if r.get("log") else ""
        detail = ""
        if r["status"] != "passed":
            body = "\n".join((r.get("fail_messages") or [])[:15]) + "\n...\n" + "\n".join(
                (r.get("tail") or "").splitlines()[-40:])
            detail = f"<details><summary>details</summary><pre>{e(body)}</pre></details>"
        rows.append(f"<tr class='{r['status']}'><td>{r['status'].upper()}</td><td><code>{e(r['id'])}</code>{detail}"
                    f"</td><td>{e(r['tier'])}</td><td>{e(', '.join(r.get('areas', [])))}</td>"
                    f"<td>{e(_fmt_checks(r))}</td><td>{r['duration']:.0f}s</td>"
                    f"<td><a href='{e(log.replace(os.sep, '/'))}'>log</a></td></tr>")
    state = "PASSED" if c["failures"] == 0 else "FAILED"
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>RAD IDE tests</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
:root {{ --bg:#fff; --fg:#1b1f24; --mut:#656d76; --line:#d0d7de; --ok:#1a7f37; --bad:#cf222e; --warn:#9a6700; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --mut:#8d96a0; --line:#30363d;
  --ok:#3fb950; --bad:#f85149; --warn:#d29922; }} }}
body {{ background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, "Segoe UI", sans-serif; margin:16px; }}
h1 {{ font-size:20px; margin:0 0 4px; }} .mut {{ color:var(--mut); }}
table {{ border-collapse:collapse; width:100%; margin-top:12px; }} td, th {{ border-bottom:1px solid var(--line);
  padding:4px 8px; text-align:left; vertical-align:top; }} pre {{ white-space:pre-wrap; font-size:12px; }}
tr.passed td:first-child {{ color:var(--ok); }} tr.flaky td:first-child {{ color:var(--warn); }}
tr.failed td:first-child, tr.timeout td:first-child, tr.error td:first-child {{ color:var(--bad); font-weight:600; }}
.big {{ font-weight:600; color:{'var(--ok)' if c['failures'] == 0 else 'var(--bad)'}; }}
</style></head><body>
<h1>RAD IDE tests: <span class="big">{state}</span></h1>
<div class="mut">{e(meta.get('command') or ', '.join(meta['tiers']))} | {c['total']} tests | {c['passed']} passed |
{c['flaky']} flaky | {c['failed']} failed | {c['timeout']} timed out | {c['error']} errors | {meta['duration']:.0f}s |
commit {e(meta.get('commit', '')[:10])} on {e(meta.get('branch', ''))} | {e(meta['started'])}</div>
<table><tr><th>Status</th><th>Test</th><th>Tier</th><th>Areas</th><th>Checks</th><th>Time</th><th>Log</th></tr>
{''.join(rows)}</table></body></html>
"""
    path.write_text(page, encoding="utf-8")


def write_reports(results: list[dict], meta: dict, report_dir: Path) -> str:
    meta["totals"] = totals(results)
    (report_dir / "results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=1,
                                                        ensure_ascii=False), encoding="utf-8")
    md = write_markdown(results, meta, report_dir / "summary.md")
    write_junit(results, meta, report_dir / "junit.xml")
    write_html(results, meta, report_dir / "report.html")
    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    return md


def print_list(tests: list[Test], selected: list[Test] | None) -> None:
    by_tier: dict[str, list[Test]] = {}
    for t in tests:
        by_tier.setdefault(t.tier, []).append(t)
    sel = {t.id for t in selected} if selected is not None else None
    for tier in sorted(by_tier, key=lambda x: (x != "fast", x != "full", x)):
        group = by_tier[tier]
        say(f"\n[{tier}]  {len(group)} test(s)")
        for t in group:
            mark = "*" if sel is not None and t.id in sel else " "
            extra = (" " + " ".join(t.args)) if t.args else ""
            flags = (" [smoke]" if t.smoke else "") + (" [auto]" if t.auto else "")
            needs = f"  needs: {', '.join(t.needs)}" if t.needs else ""
            say(f" {mark} {t.id}{extra}  ({t.timeout}s){flags}{needs}")
    say("\nTiers: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_tier.items())) + f"  | total {len(tests)}")
    if sel is not None:
        say(f"{len(sel)} selected (*)")


def merge_reports(sources: list[str], out_dir: Path) -> int:
    """Combine the results.json of several runs (e.g. one per CI tier job) into one set of reports."""
    results, metas = [], []
    for src in sources:
        for p in sorted(Path().glob(src) if any(c in src for c in "*?[") else [Path(src)]):
            for f in (sorted(p.rglob("results.json")) if p.is_dir() else [p] if p.is_file() else []):
                data = json.loads(f.read_text(encoding="utf-8"))
                metas.append(data["meta"])
                results += data["results"]
    if not metas:
        say("--merge: no results.json found")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    tiers = sorted({t for m in metas for t in m.get("tiers", [])})
    meta = dict(metas[0], tiers=tiers, duration=round(sum(m.get("duration", 0) for m in metas), 1),
                merged_from=len(metas), report_dir=str(out_dir), command="merge")
    write_reports(results, meta, out_dir)
    c = meta["totals"]
    say(f"merged {len(metas)} run(s): {c['passed'] + c['flaky']}/{c['total']} passed, {c['failures']} failed "
        f"-> {out_dir}")
    return c["failures"]


COMMANDS = ("smoke", "changed", "area", "areas", "full", "list", "check", "fast")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=COMMANDS, help="smoke | changed | area NAME... | areas | full | "
                                                                "list | check | fast (default: --tier filters)")
    ap.add_argument("names", nargs="*", help="area names for 'area'")
    ap.add_argument("--list", action="store_true", help="show what the command / filters select and exit")
    ap.add_argument("--check", action="store_true", help="same as the 'check' command")
    ap.add_argument("--tier", action="append", default=[],
                    help="tier(s) to run, comma separated: fast (default), full, network, toolchain, toolchain:<name>, "
                         "gui-real, manual, project, all")
    ap.add_argument("--only", action="append", default=[], help="run tests whose id contains this text / matches this "
                                                                "glob (repeatable)")
    ap.add_argument("--skip", action="append", default=[], help="leave out tests matching this (repeatable)")
    ap.add_argument("--base", default=None, help="'changed': also compare HEAD with this branch / commit (e.g. main)")
    ap.add_argument("--no-lint", action="store_true", help="smoke / changed / full: skip the pyflakes step")
    ap.add_argument("--jobs", type=int, default=1, help="tests at a time (default 1: GUI tests share the desktop)")
    ap.add_argument("--retries", type=int, default=1, help="re-runs of a failed test; a pass on re-run = flaky (1)")
    ap.add_argument("--timeout-scale", type=float, default=1.0, help="multiply every timeout (slow machines)")
    ap.add_argument("--python", default=sys.executable, help="interpreter for the tests (default: this one)")
    ap.add_argument("--report-dir", default=None, help="where reports + logs go (default: %%TEMP%%/radide-test-results"
                                                       "/<timestamp>)")
    ap.add_argument("--scratch-root", default=None, help="parent of the per-test scratch folders")
    ap.add_argument("--keep-scratch", action="store_true", help="keep scratch folders of passed tests too")
    ap.add_argument("--no-isolate-temp", action="store_true", help="do not point TEMP/TMP into the scratch folder")
    ap.add_argument("--tail", type=int, default=120, help="log lines kept in the reports per test")
    ap.add_argument("--registry", default=str(REGISTRY), help=argparse.SUPPRESS)
    ap.add_argument("-v", "--verbose", action="store_true", help="stream every test's output")
    ap.add_argument("--open", action="store_true", help="open report.html when done")
    ap.add_argument("--merge", nargs="+", metavar="DIR", help="combine the results.json of earlier runs (folders, "
                                                              "files or globs) into --report-dir and exit")
    opts = ap.parse_args(argv)

    if opts.merge:
        return merge_reports(opts.merge, Path(opts.report_dir or "test-results-merged").resolve())
    reg = Registry(Path(opts.registry))
    tests = reg.tests()
    cmd = opts.command or ""
    if opts.check or cmd == "check":
        return check_registry(tests, reg)
    if cmd == "areas":
        for name, n in all_areas(tests).items():
            say(f"  {name:14s} {n:4d} test(s)" + (f"   ({', '.join(AREAS[name])})" if name in AREAS else ""))
        return 0
    tiers = [x.strip() for v in opts.tier for x in v.split(",") if x.strip()] or None
    lint = False
    label = cmd or "tier " + ",".join(tiers or ["fast"])
    if cmd == "smoke":
        selected = [t for t in tests if t.smoke and t.tier not in NOT_IN_ALL]
        lint = True
    elif cmd == "area":
        if not opts.names:
            say("usage: run_tests.py area NAME [NAME...]   (names: run_tests.py areas)")
            return 2
        selected = select_areas(tests, opts.names)
        if tiers:
            selected = [t for t in selected if tier_matches(t.tier, tiers)]
        if not selected:
            say(f"no test in area(s) {', '.join(opts.names)}; known: {', '.join(all_areas(tests))}")
            return 2
        label = "area " + " ".join(opts.names)
    elif cmd == "changed":
        files = changed_files(opts.base)
        selected, why = select_changed(tests, files)
        lint = True
        say(f"{len(files)} changed file(s) -> {', '.join(why) or 'nothing related'}")
        label = "changed (" + (", ".join(why) or "-") + ")"
    elif cmd == "full":
        selected = [t for t in tests if tier_matches(t.tier, tiers or ["all"])]
        lint = True
    else:                                   # "", "fast", "list": classic --tier / --only / --skip selection
        if cmd == "fast":
            tiers = ["fast"]
        selected = select(tests, tiers, opts.only, opts.skip)
    if cmd in ("smoke", "area", "changed", "full"):
        if opts.only:
            selected = [t for t in selected if pattern_matches(t, opts.only)]
        if opts.skip:
            selected = [t for t in selected if not pattern_matches(t, opts.skip)]
    if lint and not opts.no_lint and not opts.only:
        selected = [lint_test(opts.python)] + selected
    if opts.list or cmd == "list":
        print_list(tests, selected if (cmd not in ("", "list") or tiers or opts.only or opts.skip) else None)
        return 0
    if not selected:
        say("no test selected (see: run_tests.py list)")
        return 0
    for t in selected:
        t.timeout = int(t.timeout * opts.timeout_scale)

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = Path(opts.report_dir or Path(tempfile.gettempdir()) / "radide-test-results" / stamp).resolve()
    log_dir = report_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    opts.scratch_root = str(Path(opts.scratch_root or Path(tempfile.gettempdir()) / "rt" / stamp).resolve())
    Path(opts.scratch_root).mkdir(parents=True, exist_ok=True)

    started = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    say(f"RAD IDE tests: {label}: {len(selected)} selected, jobs {opts.jobs}, retries {opts.retries}\n"
        f"reports: {report_dir}\nscratch: {opts.scratch_root}\n")
    t0 = time.monotonic()
    results: list[dict] = [None] * len(selected)   # type: ignore[list-item]

    def work(i: int) -> None:
        t = selected[i]
        say(f"[{i + 1}/{len(selected)}] {t.id}  ({t.tier}) ...")
        r = run_test(t, i + 1, opts, log_dir)
        r["areas"] = t.areas
        results[i] = r
        say(f"[{i + 1}/{len(selected)}] {r['status'].upper():8s} {t.id}  {_fmt_checks(r)}  {r['duration']:.0f}s"
            + (f"  ({r['leftover_processes']} leftover process(es) ended)" if r.get("leftover_processes") else ""))
        if r["status"] in FAILING:
            for line in (r.get("tail") or "").splitlines()[-25:]:
                say(f"    | {line}")

    interrupted = False
    try:
        if opts.jobs <= 1:
            for i in range(len(selected)):
                work(i)
        else:
            with ThreadPoolExecutor(max_workers=opts.jobs) as ex:
                list(ex.map(work, range(len(selected))))
    except KeyboardInterrupt:
        interrupted = True
        say("\ninterrupted: writing the report of the tests that finished")
    results = [r for r in results if r]

    meta = {"started": started, "duration": round(time.monotonic() - t0, 1), "command": label,
            "tiers": sorted({t.tier for t in selected}), "only": opts.only, "skip": opts.skip,
            "python": opts.python, "python_version": platform.python_version(), "platform": platform.platform(),
            "commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "interrupted": interrupted, "report_dir": str(report_dir)}
    write_reports(results, meta, report_dir)
    c = meta["totals"]
    say(f"\n{c['passed'] + c['flaky']}/{c['total']} passed ({c['flaky']} flaky); {c['failures']} failed "
        f"({c['timeout']} timeout, {c['error']} error); {meta['duration']:.0f}s\n"
        f"report: {report_dir / 'report.html'}")
    if opts.open and os.name == "nt":
        os.startfile(str(report_dir / "report.html"))    # noqa: S606 - the user asked for it
    if not opts.keep_scratch:
        try:
            Path(opts.scratch_root).rmdir()        # only when every scratch folder was removed (all passed)
        except OSError:
            pass
    return c["failures"] + (1 if interrupted and not c["failures"] else 0)


if __name__ == "__main__":
    sys.exit(main())
