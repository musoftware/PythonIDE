"""Native WinForms build (radide/deploy/native/dotnet_winforms.py) - C# and PowerShell projects become a small
.NET exe without Python; the exe is started and driven with UI Automation + window messages.

    .venv\\Scripts\\python samples/Tests/Native/test_native_dotnet.py

Projects: samples/Tests/Native/CSharp/NativeCs and PowerShell/NativePs (two forms, menu, buttons, text box,
label, check box, list box, timer, a module called directly and through radcall). Each is copied to a temp folder,
built with radide.deploy.build.build() (kind auto -> native), checked for Python files, run and driven:
Load, TextChanged (WM_SETTEXT), Click (BM_CLICK), CheckBox, ListBox count, Timer ticks, menu (UIA Invoke),
Show/Hide of Form2, Set("Form1.lblOut") from Form2, End(). Also: the SDK variant (size comparison), check()
reasons and the fallback to the bridge build (the bridge builder is stubbed, nothing slow runs).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import _win as W  # noqa: E402
from radide.deploy import build as B  # noqa: E402
from radide.deploy import config as C  # noqa: E402
from radide.deploy.native import builder_for, dotnet_winforms as D  # noqa: E402
from radide.model import Form, Project  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = []
SIZES = {}


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:500]}]"), flush=True)
    return bool(cond)


def copy_project(src: Path, tmp: Path) -> Path:
    dst = tmp / src.name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("Publish", "_build", "__pycache__"))
    return dst


def no_python(dist: Path) -> list[str]:
    bad = []
    for f in dist.rglob("*"):
        n = f.name.lower()
        if (n.startswith("python") and n.endswith(".dll")) or n.endswith((".pyd", ".pyc", ".pyz")) or n == "_internal":
            bad.append(str(f.relative_to(dist)))
    return bad


def drive(exe: Path, tag: str) -> None:
    uia = W.UIA()
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        main = W.wait(lambda: next((h for h in W.top_windows(p.pid) if W.text(h) == "Native test"), 0), 30)
        if not check(f"{tag}: main window 'Native test' appears", main, W.top_windows(p.pid)):
            return
        root = uia.root(main)
        h = {n: uia.hwnd(root, n) for n in ("lblOut", "txtName", "btnGreet", "chkShout", "lblEcho", "lstLog",
                                             "lblCount", "btnStart", "lblTicks", "btnForm2", "btnClose")}
        check(f"{tag}: every control found by AutomationId (= control Name)", all(h.values()),
              [k for k, v in h.items() if not v])
        check(f"{tag}: Form1_Load ran (lblOut = Loaded)", W.wait(lambda: W.text(h["lblOut"]) == "Loaded", 5),
              W.text(h["lblOut"]))
        check(f"{tag}: design values (txtName World, list has 1 item)",
              W.text(h["txtName"]) == "World" and W.list_count(h["lstLog"]) == 1,
              (W.text(h["txtName"]), W.list_count(h["lstLog"])))
        W.set_text(h["txtName"], "Ali")
        check(f"{tag}: TextChanged handler (lblEcho = echo:Ali)",
              W.wait(lambda: W.text(h["lblEcho"]) == "echo:Ali", 5), W.text(h["lblEcho"]))
        W.click(h["btnGreet"])
        check(f"{tag}: Click handler + module call (lblOut = Hello, Ali!)",
              W.wait(lambda: W.text(h["lblOut"]) == "Hello, Ali!", 5), W.text(h["lblOut"]))
        check(f"{tag}: AddItem + ListCount (2 items)",
              W.list_count(h["lstLog"]) == 2 and W.text(h["lblCount"]) == "2 items",
              (W.list_count(h["lstLog"]), W.text(h["lblCount"])))
        W.click(h["chkShout"])
        W.click(h["btnGreet"])
        check(f"{tag}: CheckBox Value + radcall (HELLO, ALI!)",
              W.wait(lambda: W.text(h["lblOut"]) == "HELLO, ALI!", 5), W.text(h["lblOut"]))
        W.click(h["btnStart"])
        check(f"{tag}: Timer ticks 5 times then stops",
              W.wait(lambda: W.text(h["lblTicks"]) == "5", 10), W.text(h["lblTicks"]))
        time.sleep(0.4)
        check(f"{tag}: timer disabled after 5", W.text(h["lblTicks"]) == "5", W.text(h["lblTicks"]))
        check(f"{tag}: program still running before the menu test", p.poll() is None, p.poll())
        ok = uia.invoke_menu(root, ["File", "Hello"])
        check(f"{tag}: menu File > Hello (lblOut = Menu clicked)",
              ok and W.wait(lambda: W.text(h["lblOut"]) == "Menu clicked", 5), W.text(h["lblOut"]))
        W.click(h["btnForm2"])
        f2 = W.wait(lambda: next((x for x in W.top_windows(p.pid) if W.text(x) == "Second form"), 0), 10)
        check(f"{tag}: Show(\"Form2\") opens the second form", f2, [W.text(x) for x in W.top_windows(p.pid)])
        if f2:
            r2 = uia.root(f2)
            msg, back = uia.hwnd(r2, "lblMsg"), uia.hwnd(r2, "btnBack")
            check(f"{tag}: Form2_Load ran", W.wait(lambda: W.text(msg) == "Form2 loaded", 5), W.text(msg) if msg else "")
            W.click(back)
            check(f"{tag}: Form2 sets Form1.lblOut and hides itself",
                  W.wait(lambda: W.text(h["lblOut"]) == "From Form2" and f2 not in W.top_windows(p.pid), 5),
                  (W.text(h["lblOut"]), [W.text(x) for x in W.top_windows(p.pid)]))
        W.click(h["btnClose"])
        try:
            code = p.wait(10)
        except subprocess.TimeoutExpired:
            code = None
        check(f"{tag}: End() closes the program (exit code 0)", code == 0, code)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait(5)


def build_project(src: Path, tmp: Path, tag: str):
    folder = copy_project(src, tmp)
    cfg = C.load(folder, folder.name)
    lines: list[str] = []
    res = B.build(folder, cfg, log=lines.append)
    check(f"{tag}: auto build kind is native ({res.kind})", res.kind.startswith("native-"), "\n".join(lines[-15:]))
    exe = res.dist / res.exe
    check(f"{tag}: exe exists", exe.is_file(), exe)
    bad = no_python(res.dist)
    check(f"{tag}: no Python in the program folder (no python*.dll, _internal, .pyd)", not bad, bad)
    check(f"{tag}: not python_based", res.python_based is False)
    check(f"{tag}: data file copied next to the exe", (res.dist / "readme.txt").is_file())
    size = exe.stat().st_size
    SIZES[f"{tag} {res.kind}"] = size
    limit = 90 * 1024 * 1024 if res.kind == "native-standalone" else 200 * 1024
    check(f"{tag}: exe size {size / 1024:.1f} KB within the limit of its kind", size < limit, size)
    check(f"{tag}: one exe (+ data), nothing else in the folder",
          sorted(f.name for f in res.dist.iterdir()) == sorted([res.exe, "readme.txt"]), list(res.dist.iterdir()))
    return folder, cfg, res


def test_csharp(tmp: Path):
    folder, cfg, res = build_project(HERE / "CSharp" / "NativeCs", tmp, "C#")
    check("C#: default target is standalone (self-contained single file)", res.kind == "native-standalone", res.kind)
    drive(res.dist / res.exe, "C# standalone")
    project = Project.load(folder)
    for variant, kind in (("netfx", "native-net48"), ("framework", "native-sdk")):
        lines: list[str] = []
        r = D.build(folder, project, cfg, tmp / f"work_{variant}", lines.append, variant=variant)
        exe = r.dist / r.exe
        SIZES[f"C# {r.kind}"] = exe.stat().st_size
        check(f"C#: {variant} variant builds ({r.kind}, {exe.stat().st_size / 1024:.1f} KB)", r.kind == kind, lines[-5:])
        drive(exe, f"C# {variant}")
    check("C#: sizes netfx < framework < standalone",
          SIZES["C# native-net48"] < SIZES["C# native-sdk"] < SIZES["C# native-standalone"], SIZES)


def test_powershell(tmp: Path):
    folder, cfg, res = build_project(HERE / "PowerShell" / "NativePs", tmp, "PowerShell")
    drive(res.dist / res.exe, "PowerShell")


def test_check_and_fallback(tmp: Path):
    check("builder_for csharp-bridge / powershell-bridge is dotnet_winforms",
          builder_for("csharp-bridge") is D and builder_for("powershell-bridge") is D)
    folder = copy_project(HERE / "CSharp" / "NativeCs", tmp / "fb")
    form = Form.load(folder / "Form1.form")
    form.add("TreeView", 10, 250).props["Name"] = "tvTree"
    form.extra["storyboards"] = [{"Name": "sb1"}]
    form.save(folder / "Form1.form")
    project = Project.load(folder)
    cfg = C.load(folder, folder.name)
    reasons = D.check(folder, project, cfg)
    check("check(): TreeView is a reason", any("TreeView" in r and "tvTree" in r for r in reasons), reasons)
    check("check(): storyboards are a reason", any("storyboards" in r for r in reasons), reasons)
    called = []
    saved = B.BUILDERS["bridge"]
    B.BUILDERS["bridge"] = lambda *a, **k: called.append(a) or B.BuildResult(folder, "x.exe", "bridge")
    try:
        lines: list[str] = []
        res = B.build(folder, cfg, log=lines.append)
    finally:
        B.BUILDERS["bridge"] = saved
    check("fallback: the bridge build is used and the reasons are logged",
          res.kind == "bridge" and called and any("TreeView" in l for l in lines), lines[-8:])
    # code the .NET Framework cannot compile (ranges) -> the SDK build is used
    if D._sdk_dirs():
        import json
        folder2 = copy_project(HERE / "CSharp" / "NativeCs", tmp / "ranges")
        helper = folder2 / "Helper.cs"
        helper.write_text(helper.read_text(encoding="utf-8").replace(
            "Greet(name).ToUpperInvariant();", "Greet(name).ToUpperInvariant()[..];"), encoding="utf-8")
        pub = json.loads((folder2 / "publish.json").read_text(encoding="utf-8"))
        pub["dotnet_target"] = "netfx"
        (folder2 / "publish.json").write_text(json.dumps(pub), encoding="utf-8")
        lines = []
        res2 = B.build(folder2, C.load(folder2, folder2.name), log=lines.append)
        check("target netfx + C# 8 ranges (not on .NET Framework) -> falls back to the framework build",
              res2.kind == "native-sdk", lines[-10:])


def test_control_map(tmp: Path):
    """The .form type -> .NET type table is data: a project map adds TreeView without touching the generator."""
    import json
    cmap = D.control_map()
    check("control map: built-in table loaded (Button -> System.Windows.Forms.Button)",
          cmap["Button"]["type"] == "System.Windows.Forms.Button" and "TreeView" not in cmap)
    folder = copy_project(HERE / "CSharp" / "NativeCs", tmp / "map")
    form = Form.load(folder / "Form1.form")
    tv = form.add("TreeView", 10, 230)
    tv.props.update({"Name": "tvTree", "Width": 150, "Height": 60})
    form.save(folder / "Form1.form")
    (folder / "dotnet.controls.json").write_text(json.dumps({"controls": {
        "TreeView": {"type": "System.Windows.Forms.TreeView", "props": {"Nodes": "Tag"}, "events": ["AfterSelect"]}}}),
        encoding="utf-8")
    project = Project.load(folder)
    cfg = C.load(folder, folder.name)
    check("control map: project map makes TreeView supported", not D.check(folder, project, cfg), D.check(folder, project, cfg))
    lines: list[str] = []
    r = D.build(folder, project, cfg, tmp / "mapwork", lines.append, variant="netfx")
    gen = (tmp / "mapwork" / "native-dotnet" / "src" / "RadForms.g.cs").read_text(encoding="utf-8-sig")
    check("control map: generic emitter writes the mapped type", "new global::System.Windows.Forms.TreeView()" in gen
          and 'this.Register("tvTree", this.tvTree);' in gen, gen[:300])
    check("control map: the exe builds with the mapped control", (r.dist / r.exe).is_file(), lines[-5:])


def main():
    tmp = Path(tempfile.mkdtemp(prefix="radnative_dotnet_"))
    try:
        test_csharp(tmp)
        test_powershell(tmp)
        test_check_and_fallback(tmp)
        test_control_map(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nSizes:")
    for k, v in SIZES.items():
        print(f"  {k}: {v / 1024:.1f} KB")
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
