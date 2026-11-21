"""Test Explorer adapter for .NET (xUnit, NUnit, MSTest - C# and VB), replacing the source-scan-only
``radide.testing.DotnetAdapter`` while keeping its id ("dotnet"):

* discovery: ``dotnet vstest <test.dll> --ListFullyQualifiedTests`` for every built test project (the real
  test cases, NUnit [TestCase] rows included) merged with a source scan (file / line of each test, and the
  tests of projects that are not built yet)
* grouping like Visual Studio: Project > Namespace > Class > Test (> data rows)
* runs per project with ``--filter`` (escaped), live results from the console logger while it runs and the
  full results (messages, stack traces, output, durations) from the TRX file
* code coverage with coverlet ("XPlat Code Coverage", Cobertura) when the project references it
* Debug: radide/dotnet/tools/ui.py debug_tests (VSTEST_HOST_DEBUG + netcoredbg attach)
"""
from __future__ import annotations

import re
import shutil
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

from ... import testing as T
from . import sdk

TEST_ATTR_CS = re.compile(r"\[\s*(?:[\w.]+\.)?(Fact|Theory|Test|TestCase|TestCaseSource|TestMethod|DataTestMethod|"
                          r"SkippableFact|Property)\b")
TEST_ATTR_VB = re.compile(r"<\s*(?:[\w.]+\.)?(Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)\b", re.I)
LIVE = re.compile(r"^\s*(Passed|Failed|Skipped)\s+(.+?)(?:\s+\[([\d.]+\s*(?:ms|s|m))(?:\s*\d+\s*ms)?\])?\s*$")


def _escape_filter(value: str) -> str:
    return re.sub(r"([\\()&|=!~])", r"\\\1", value)


def _dur(text: str | None) -> float | None:
    if not text:
        return None
    m = re.match(r"([\d.]+)\s*(ms|s|m)", text.strip())
    if not m:
        return None
    v = float(m.group(1))
    return v / 1000 if m.group(2) == "ms" else v * 60 if m.group(2) == "m" else v


def parse_cobertura(path: Path) -> dict:
    cov: dict[str, T.FileCoverage] = {}
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return cov
    sources = [Path(s.text.strip()) for s in root.iter("source") if s.text and s.text.strip()]
    for cls in root.iter("class"):
        fn = cls.get("filename", "")
        if not fn:
            continue
        p = Path(fn)
        if not p.is_absolute():
            p = next((s / fn for s in sources if (s / fn).exists()), sources[0] / fn if sources else p)
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        fc = cov.setdefault(key, T.FileCoverage())
        for ln in cls.iter("line"):
            try:
                n, hits = int(ln.get("number", "0")), int(ln.get("hits", "0"))
            except ValueError:
                continue
            (fc.covered if hits > 0 else fc.missed).add(n)
            cc = ln.get("condition-coverage", "")
            if ln.get("branch") == "True" or ln.get("branch") == "true":
                if cc and not cc.startswith("100%") and hits > 0:
                    fc.partial.add(n)
    for fc in cov.values():
        fc.missed -= fc.covered
    return cov


class DotnetTestAdapter(T.DotnetAdapter):
    id = "dotnet"
    name = ".NET (xUnit / NUnit / MSTest)"
    language = "csharp"
    supports_debug = True
    supports_coverage = True

    def __init__(self, root, win=None):
        super().__init__(root, win)
        self._live_buf = ""
        self.projects: dict[str, Path] = {}       # project name -> project file

    @staticmethod
    def test_projects(root) -> list[Path]:
        root = Path(root)
        cands = []
        slns = sorted(root.glob("*.sln")) + sorted(root.glob("*.slnx"))
        for s in slns:
            cands += sdk.solution_projects(s)
        if not cands:
            cands = sdk.find_projects(root, 200)
        out = []
        for p in dict.fromkeys(cands):
            text = sdk.text(p)
            if re.search(r"xunit|nunit|MSTest|Microsoft\.NET\.Test\.Sdk|<IsTestProject>\s*true", text, re.I):
                out.append(Path(p))
        return out

    @classmethod
    def detect(cls, root):
        return bool(cls.test_projects(root))

    # ---------------------------------------------------------------- discovery
    def _scan_sources(self, proj: Path) -> list[T.TestItem]:
        out = []
        folder = proj.parent
        vb = proj.suffix.lower() == ".vbproj"
        pats = [r".*\.vb"] if vb else [r".*\.cs"]
        for f in T._files(folder, pats, 3000):
            text = T._read(f)
            if not (TEST_ATTR_VB if vb else TEST_ATTR_CS).search(text):
                continue
            ns, cls, pending = "", "", False
            file_ns = ""
            for n, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                m = re.match(r"namespace\s+([\w.]+)\s*(;)?", s, re.I)
                if m:
                    ns = m.group(1)
                    if m.group(2):
                        file_ns = ns
                if vb:
                    m = re.match(r"(?:<[^>]*>\s*)*(?:Public\s+|Friend\s+|NotInheritable\s+|Partial\s+)*(?:Class|Module)\s+(\w+)",
                                 s, re.I)
                else:
                    m = re.match(r"(?:\[[^\]]*\]\s*)*(?:public\s+|internal\s+|sealed\s+|static\s+|partial\s+|abstract\s+)*"
                                 r"(?:class|record)\s+(\w+)", s)
                if m:
                    cls = m.group(1)
                if (TEST_ATTR_VB if vb else TEST_ATTR_CS).search(s):
                    pending = True
                if pending:
                    fm = (re.search(r"\bSub\s+(\w+)\s*\(", s, re.I) if vb else
                          re.search(r"\b(?:void|Task|ValueTask|async\s+Task|async\s+ValueTask|async\s+void)\s+(\w+)\s*\(", s))
                    if fm:
                        use_ns = ns or file_ns
                        fq = ".".join(x for x in (use_ns, cls, fm.group(1)) if x)
                        it = self.item(fq, fm.group(1), f, n, ".".join(x for x in (use_ns, cls) if x))
                        it.namespace, it.cls, it.method, it.project = use_ns, cls, fm.group(1), proj.stem
                        out.append(it)
                        pending = False
        return out

    def _list_fq(self, proj: Path) -> list[str] | None:
        """Fully qualified test names from the built assembly (None = not built / stale / failed)."""
        try:
            from ...foreign.msbuild import MSBuildProject, guess_target_path
            target = guess_target_path(MSBuildProject.load(proj), "Debug")
        except Exception:  # noqa: BLE001
            return None
        if not target.is_file():
            return None
        newest = 0.0
        for f in T._files(proj.parent, [r".*\.(cs|vb|fs|csproj|vbproj|fsproj)"], 3000):
            try:
                newest = max(newest, f.stat().st_mtime)
            except OSError:
                pass
        if newest > target.stat().st_mtime + 1:
            return None
        out_file = self.tmp / f"list-{proj.stem}.txt"
        try:
            out_file.unlink()
        except OSError:
            pass
        code, text = sdk.run([sdk.dotnet() or "dotnet", "vstest", str(target), "--ListFullyQualifiedTests",
                              f"--ListTestsTargetPath:{out_file}"], cwd=target.parent, timeout=180)
        if not out_file.is_file():
            return None
        return [ln.strip() for ln in out_file.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]

    def discover(self):
        projs = self.test_projects(self.root)
        self.projects = {p.stem: p for p in projs}
        results: dict[Path, tuple[list, list | None]] = {}

        def one(p):
            try:
                results[p] = (self._scan_sources(p), self._list_fq(p))
            except Exception:  # noqa: BLE001 - one broken project must not hide the others
                results[p] = ([], None)
        threads = [threading.Thread(target=one, args=(p,), daemon=True) for p in projs]
        for t in threads:
            t.start()
        for t in threads:
            t.join(300)
        out = []
        for p in projs:
            scanned, listed = results.get(p, ([], None))
            if not listed:
                out += scanned
                continue
            by_fq = {it.id: it for it in scanned}
            seen = set()
            for fq in listed:
                base = re.sub(r"\(.*$", "", fq)
                src = by_fq.get(base)
                head, _, last = base.rpartition(".")
                ns, _, cls = head.rpartition(".")
                name = fq[len(head) + 1:] if head else fq
                it = self.item(fq, name, src.file if src else "", src.line if src else 0, head)
                it.namespace, it.cls, it.method, it.project = ns, cls, last, p.stem
                it.case = "(" in fq
                out.append(it)
                seen.add(base)
            for it in scanned:                     # tests added since the last build
                if it.id not in seen:
                    out.append(it)
        return out

    def group_path(self, it) -> list[tuple[str, str]]:
        """Project > Namespace > Class (> method for data rows), like Visual Studio's Test Explorer."""
        proj = getattr(it, "project", "") or "Tests"
        ns = getattr(it, "namespace", None)
        cls = getattr(it, "cls", None)
        if ns is None and cls is None:
            head = it.suite or ""
            ns, _, cls = head.rpartition(".")
        path = [(f"dn:p:{proj}", proj)]
        if ns:
            path.append((f"dn:n:{proj}:{ns}", ns))
        if cls:
            path.append((f"dn:c:{proj}:{ns}.{cls}", cls))
        if getattr(it, "case", False):
            m = getattr(it, "method", "") or it.name.split("(")[0]
            path.append((f"dn:m:{proj}:{ns}.{cls}.{m}", m))
        return path

    # ---------------------------------------------------------------- running
    def _project_of(self, it) -> Path | None:
        name = getattr(it, "project", "")
        if name and name in self.projects:
            return self.projects[name]
        if not self.projects:
            self.projects = {p.stem: p for p in self.test_projects(self.root)}
        if it.file:
            return sdk.owning_project(Path(it.file), list(self.projects.values()))
        return None

    def filter_for(self, items) -> str:
        parts = []
        for i in items:
            parts.append(f"FullyQualifiedName={_escape_filter(i.id)}")
        return "|".join(parts)

    def run_argv(self, proj: Path, items, resdir: Path, coverage=False) -> list[str]:
        argv = [sdk.dotnet() or "dotnet", "test", str(proj), "--nologo", "--logger", "trx;LogFileName=results.trx",
                "--logger", "console;verbosity=normal", "--results-directory", str(resdir)]
        if items:
            argv += ["--filter", self.filter_for(items)]
        if coverage:
            argv += ["--collect", "XPlat Code Coverage"]
        return argv

    def plan(self, items, coverage=False, debug=False):
        resdir = self.tmp / "trx"
        if resdir.exists():
            shutil.rmtree(resdir, ignore_errors=True)
        groups: dict[Path, list] = {}
        if items:
            for it in items:
                p = self._project_of(it)
                if p is not None:
                    groups.setdefault(p, []).append(it)
        else:
            for p in self.test_projects(self.root):
                groups[p] = []
        steps = []
        for n, (proj, sel) in enumerate(groups.items()):
            steps.append(T.Step(self.run_argv(proj, sel, resdir / str(n), coverage), self.root, dict(sdk.QUIET_ENV),
                                f"dotnet test {proj.name}"))
        self._live_buf = ""

        def parse(_text):
            out = []
            for p in resdir.glob("**/*.trx"):
                out += T.parse_trx(p)
            return out

        def cov():
            res = {}
            for p in resdir.glob("**/coverage.cobertura.xml"):
                for k, fc in parse_cobertura(p).items():
                    old = res.get(k)
                    if old is None:
                        res[k] = fc
                    else:
                        old.covered |= fc.covered
                        old.missed = (old.missed | fc.missed) - old.covered
                        old.partial |= fc.partial
            root = str(self.root).lower()
            return {k: v for k, v in res.items() if k.lower().startswith(root)} or res
        return T.RunPlan(steps, parse, coverage=cov if coverage else (lambda: {}), tmp=self.tmp)

    def live_results(self, chunk: str) -> list[T.Result]:
        """Results printed by the console logger while the run is going on."""
        self._live_buf += chunk
        lines = self._live_buf.split("\n")
        self._live_buf = lines.pop()
        out = []
        for ln in lines:
            m = LIVE.match(ln.rstrip("\r"))
            if not m:
                continue
            st = {"Passed": "passed", "Failed": "failed", "Skipped": "skipped"}[m.group(1)]
            name = m.group(2).strip()
            head = name.split("(")[0]
            short = name[head.rfind(".") + 1:] if "." in head else name
            out.append(T.Result(id=name, state=st, duration=_dur(m.group(3)), name=short))
        return out

    def debug(self, explorer, keys):
        from .ui import debug_tests
        return debug_tests(explorer, self, keys)


def install() -> None:
    """Put the adapter into radide.testing.ADAPTERS in place of the source-scan one."""
    for i, cls in enumerate(T.ADAPTERS):
        if cls is T.DotnetAdapter or getattr(cls, "id", "") == "dotnet":
            T.ADAPTERS[i] = DotnetTestAdapter
            break
    else:
        T.ADAPTERS.append(DotnetTestAdapter)


__all__ = ["DotnetTestAdapter", "parse_cobertura", "install"]
