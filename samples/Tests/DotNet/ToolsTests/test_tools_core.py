"""Core checks of radide/dotnet/tools (no IDE window): run with  python samples/Tests/DotNet/ToolsTests/test_tools_core.py

Works on a temp copy of samples/Tests/DotNet/ToolsSolution (never edited in place). Needs the .NET SDK 8+ and,
for the first run, nuget.org to restore xunit / NUnit / MSTest; ilspycmd for the decompiler check."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SAMPLE = ROOT / "samples" / "Tests" / "DotNet" / "ToolsSolution"
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def main():
    from radide import testing as T
    from radide.dotnet import decompile
    from radide.dotnet.tools import analyzers, cleanup, cli, diagnostics, editorconfig as EC, metadata, quickfix, sdk
    from radide.dotnet.tools.testing import DotnetTestAdapter, install, parse_cobertura

    work = Path(tempfile.mkdtemp(prefix="radide-dntools-"))
    sol = work / "ToolsSolution"
    shutil.copytree(SAMPLE, sol, ignore=shutil.ignore_patterns("bin", "obj", "TestResults"))
    print("work:", sol)
    code, out = sdk.run([sdk.dotnet(), "build", str(sol / "ToolsSolution.sln"), "-nologo", "-v:q"], cwd=sol, timeout=900)
    check("solution builds (dotnet build)", code == 0, out[-800:])

    # ---------------------------------------------------------------- Test Explorer adapter
    install()
    check("adapter registered in place of the source-scan one", DotnetTestAdapter in T.ADAPTERS and
          T.DotnetAdapter not in T.ADAPTERS)
    a = DotnetTestAdapter(sol)
    items = a.discover()
    ids = {i.id for i in items}
    check("vstest discovery: xUnit + NUnit cases + MSTest", {"Calc.XTests.CalculatorTests.Add_TwoNumbers_ReturnsSum",
                                                            "Calc.NTests.CalculatorTests.Add_Cases(1,1,2)",
                                                            "Calc.MTests.CalculatorTests.Divide_ByZero_Throws"} <= ids,
          sorted(ids))
    fail = next(i for i in items if i.name == "Add_IntentionalFailure")
    check("source location of a discovered test", fail.file.endswith("CalculatorTests.cs") and fail.line == 23,
          (fail.file, fail.line))
    gp = a.group_path(next(i for i in items if i.id.endswith("Add_Cases(2,2,4)")))
    check("grouping project > namespace > class > method", [t for _k, t in gp] ==
          ["Calc.NTests", "Calc.NTests", "CalculatorTests", "Add_Cases"], gp)
    plan = a.plan(None)
    check("one dotnet test step per test project", len(plan.steps) == 3, [s.title for s in plan.steps])
    log = ""
    live = []
    for s in plan.steps:
        r = subprocess.run(s.argv, cwd=str(s.cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, **s.env}, timeout=900)
        log += r.stdout + r.stderr
        live += a.live_results(r.stdout)
    results = plan.parse(log)
    pairs, rest = T.match_results(items, results, sol)
    states = {}
    for it, res in pairs:
        states.setdefault(it.id, []).append(res.state)
    check("TRX results for all three frameworks", len(results) >= 9 and not rest, (len(results), rest))
    check("failed test reported with message + stack trace",
          "failed" in states.get("Calc.XTests.CalculatorTests.Add_IntentionalFailure", []) and
          any("CalculatorTests.cs:line" in r.message for r in results if "IntentionalFailure" in r.id))
    check("live results parsed from the console logger", any(r.state == "failed" for r in live) and
          sum(r.state == "passed" for r in live) >= 8, live[:3])
    sel = [i for i in items if i.id.endswith("Add_Cases(2,2,4)")]
    p2 = a.plan(sel)
    check("--filter escapes NUnit data rows", p2.steps and "Add_Cases\\(2,2,4\\)" in " ".join(p2.steps[0].argv),
          p2.steps[0].argv if p2.steps else None)
    r = subprocess.run(p2.steps[0].argv, cwd=str(sol), capture_output=True, text=True, timeout=600)
    res2 = p2.parse(r.stdout)
    check("running one selected data row", len(res2) == 1 and res2[0].state == "passed", res2)
    p3 = a.plan([i for i in items if i.id.startswith("Calc.XTests")], coverage=True)
    r = subprocess.run(p3.steps[0].argv, cwd=str(sol), capture_output=True, text=True, timeout=600)
    cov = p3.coverage()
    calc = [k for k in cov if k.lower().endswith("calculator.cs")]
    check("code coverage (coverlet, Cobertura) for Calculator.cs", calc and cov[calc[0]].covered, list(cov)[:5])
    _ = parse_cobertura

    # ---------------------------------------------------------------- analyzers / generators
    proj = sol / "Calc" / "Calc.csproj"
    t0 = time.time()
    data = analyzers.project_analyzers(sol / "Calc.XTests" / "Calc.XTests.csproj")
    names = {x["name"]: x for x in data["analyzers"]}
    check("analyzers listed (SDK + framework + package)", "Microsoft.CodeAnalysis.NetAnalyzers" in names and
          "xunit.analyzers" in names and "System.Text.RegularExpressions.Generator" in names, list(names))
    check("rules with default severities", any(r["id"] == "CA1822" for r in names["Microsoft.CodeAnalysis.NetAnalyzers"]
                                               ["rules"]) and len(names["xunit.analyzers"]["rules"]) > 50)
    check("source generators detected", "System.Text.RegularExpressions.Generator.RegexGenerator" in
          names["System.Text.RegularExpressions.Generator"]["generators"])
    print(f"  (analyzers in {time.time() - t0:.1f} s)")
    code, out = sdk.run(analyzers.emit_generated_argv(proj), cwd=proj.parent, timeout=600)
    gen = analyzers.generated_files(proj)
    files = [f for g in gen.values() for fs in g.values() for f in fs]
    check("generated files from obj/**/generated (RegexGenerator)", any("RegexGenerator" in f.name for f in files),
          gen)

    # ---------------------------------------------------------------- .editorconfig
    ec = sol / ".editorconfig"
    conf = EC.rule_severities(sol / "Calc" / "Messy.cs")
    check(".editorconfig severities read", conf.get("CA1822") == "warning", conf)
    EC.set_severity(ec, "CA1822", "error")
    EC.set_severity(ec, "IDE0005", "suggestion")
    conf = EC.rule_severities(sol / "Calc" / "Messy.cs")
    check(".editorconfig severity edited in place", conf.get("CA1822") == "error" and conf.get("IDE0005") == "suggestion"
          and ec.read_text().count("[*.cs]") == 1, ec.read_text())
    EC.set_severity(ec, "IDE0005", None)
    check("severity reset to default removes the key", "IDE0005" not in ec.read_text())
    check("editor options from .editorconfig", EC.editor_options(sol / "Calc" / "Messy.cs") ==
          {"insertSpaces": True, "indentSize": 4, "tabSize": 4, "insertFinalNewline": True},
          EC.editor_options(sol / "Calc" / "Messy.cs"))
    check("effective severity: configured > default", EC.effective_severity("CA1822", "Performance", "Info", True,
                                                                            conf) == "error")

    # ---------------------------------------------------------------- Run Code Analysis -> diagnostics
    code, out = sdk.run(diagnostics.analysis_argv(sol / "ToolsSolution.sln"), cwd=sol, timeout=900)
    diags = diagnostics.parse_build_output(out)
    ca = [d for d in diags if d.id == "CA1822" and d.file.endswith("Messy.cs")]
    check("Run Code Analysis reports CA1822 (as error, from .editorconfig)", ca and ca[0].severity == "Error",
          [(d.severity, d.id, Path(d.file).name) for d in diags][:10])
    check("diag id from an Error List row", diagnostics.diag_id("CA1822: Member 'Counter' ...") == "CA1822" and
          diagnostics.help_url("CA1822").endswith("/ca1822"))
    EC.set_severity(ec, "CA1822", "warning")

    # ---------------------------------------------------------------- Remove and Sort Usings + Code Cleanup
    messy = sol / "Calc" / "Messy.cs"
    new, removed, err = cleanup.organize_usings(messy)
    check("Remove and Sort Usings (compiler CS8019): all 4 implicit/unused usings removed",
          new is not None and len(removed) == 4 and "using" not in new.split("namespace")[0], (removed, err))
    text2 = messy.read_text().replace("return 42;", "return new StringBuilder().Length;")
    new2, removed2, err2 = cleanup.organize_usings(messy, text2)
    check("a used namespace is kept", new2 is not None and "using System.Text;" in new2 and len(removed2) == 3,
          (removed2, err2))
    before = messy.read_text()
    code, out = sdk.run(cleanup.format_argv(proj, "whitespace", [messy]), cwd=proj.parent, timeout=600)
    after = messy.read_text()
    check("Code Cleanup (dotnet format whitespace) changes the document", code == 0 and after != before and
          "    public int Twice(int a)" in after, out[-500:])

    # ---------------------------------------------------------------- decompiler
    if decompile.find_ilspycmd():
        rt = metadata.shared_framework_dirs("net9.0")
        corelib = rt[0] / "System.Private.CoreLib.dll" if rt else None
        txt = decompile.decompile_to_text(corelib, "System.Text.StringBuilder", install=False)
        check("decompile a BCL type (ilspycmd -t)", "class StringBuilder" in txt and "Append" in txt, txt[:200])
        f = decompile.decompiled_file(corelib, "System.Collections.Generic.List<T>")
        check("decompiled file cached as .cs (generic name)", f.is_file() and "List`1" in f.name and
              "#region Assembly" in f.read_text(encoding="utf-8"))
    else:
        check("decompile a BCL type (ilspycmd not installed - skipped)", True)

    # ---------------------------------------------------------------- metadata + quick fixes
    idx = quickfix.index_for(sol / "Calc.XTests" / "Calc.XTests.csproj")
    check("type index: framework + package types", idx.lookup("StringBuilder") and idx.lookup("Assert")
          and idx.raw_name("System.Collections.Generic", "List", True) == "List`1")
    test_file = sol / "Calc.XTests" / "CalculatorTests.cs"
    fx = quickfix.fixes_for("StringBuilder", test_file.read_text(), test_file,
                            solution_projects=sdk.solution_projects(sol / "ToolsSolution.sln"))
    check("light bulb: using System.Text;", fx and fx[0].kind == "using" and fx[0].namespace == "System.Text",
          [(f.kind, f.title) for f in fx])
    calc_file = sol / "Calc" / "Calculator.cs"
    fx2 = quickfix.fixes_for("CalculatorTests", calc_file.read_text(), calc_file,
                             solution_projects=sdk.solution_projects(sol / "ToolsSolution.sln"))
    check("light bulb: add reference to a solution project", any(f.kind == "project" for f in fx2),
          [(f.kind, f.title) for f in fx2])
    fx3 = quickfix.fixes_for("RestClient", calc_file.read_text(), calc_file)
    check("light bulb: install a known package", any(f.kind == "package" and f.package == "RestSharp" for f in fx3),
          [(f.kind, f.title) for f in fx3])
    edit = quickfix.using_edit(test_file.read_text(), "System.Text")
    check("using inserted in sorted position", edit == [[0, 0, 0, 0, "using System.Text;\n"]], edit)

    # ---------------------------------------------------------------- dotnet CLI submenu
    class P:
        def target(self, c):
            return sol / "ToolsSolution.sln"

        def _project_file(self, c):
            return proj

        def solution(self, c):
            return None

        def _reload(self, c):
            pass
    sub = cli.cli_submenu(P(), None)

    def flat(m):
        out = []
        for x in m.items:
            out += flat(x) if hasattr(x, "items") else [getattr(x, "id", "")]
        return out
    ids = flat(sub)
    check("dotnet CLI submenu: restore/clean/build/test/pack/publish/format/watch/secrets/tools/workloads",
          {"cli-restore", "cli-clean", "cli-build", "cli-test", "cli-pack", "cli-publish", "cli-format", "cli-watch",
           "cli-secrets-init", "cli-tool-restore", "cli-workload-list", "cli-workload-install"} <= set(ids), ids)

    shutil.rmtree(work, ignore_errors=True)
    ok = sum(1 for _n, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
