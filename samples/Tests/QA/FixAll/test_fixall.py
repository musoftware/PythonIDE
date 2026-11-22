"""Regression checks for the "fix all the problems" round (QA / examples / integration findings).

    .venv\\Scripts\\python samples/Tests/QA/FixAll/test_fixall.py [--slow]

  paths      Rust: cargo target folder in %LOCALAPPDATA%\\RADIDE\\cache\\cargo\\<hash> (deep projects: LNK1104);
             Flutter: a deep project builds in a short mirror (MSBuild FTK1011)
  bridge     the GUI Bridge host: a missing interpreter -> message + exit (no hang); ESC multi-line SET/GET;
             App / Screen / Clipboard objects; CheckBox Checked alias; KeyCode -> numeric virtual-key codes
  clients    multi-line text through the Lua, Perl, Ruby, PowerShell, Dart and Fortran clients (ESC protocol)
  dart       Build > Publish of a Dart bridge program: dart compile exe (no Dart SDK needed on the user's PC)
  size       Python Qt: unused Qt modules / files left out; RingQt: RingQt Light for widgets-only programs
  lsp        Cargo.toml / RadApp.csproj written when a rust-bridge / csharp-bridge project's code is opened
  --slow     also: native Rust publish of a project in a > 200 character folder; Flutter Windows publish there

Real windows of the bridge host appear for a moment (Tk); only processes started here are closed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ["RADIDE_NO_BROWSER"] = "1"
SLOW = "--slow" in sys.argv
OUT = Path(os.environ.get("QA_OUT") or tempfile.mkdtemp(prefix="radide_fixall_"))
OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  - " + str(detail)[:1500]) if detail and not ok else ""),
          flush=True)


def skip(name, why):
    print(f"SKIP {name}  - {why}", flush=True)


NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def run(cmd, cwd=None, inp=None, timeout=180, env=None):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, input=inp, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, env=env, creationflags=NO_WINDOW)


# ====================================================================== paths
def test_paths():
    from radide.languages import rust_bridge as rb
    from radide.paths import user_data_dir
    short = Path(tempfile.gettempdir()) / "rfx_short"
    short.mkdir(exist_ok=True)
    deep = OUT / ("d" * 60) / ("e" * 60) / "RustDeep"
    deep.mkdir(parents=True, exist_ok=True)
    cache = user_data_dir() / "cache" / "cargo"
    d = rb.cargo_cache_dir(deep)
    check("cargo cache folder under %LOCALAPPDATA%\\RADIDE\\cache\\cargo", d.is_dir() and d.parent == cache, d)
    check("cargo cache folder is short (< 80 chars)", len(str(d)) < 80, len(str(d)))
    check("same folder -> same cache folder", rb.cargo_cache_dir(deep) == d)
    check("short project: --target-dir _build", rb.target_dir(short) == "_build")
    check("deep project: --target-dir in the cache", rb.target_dir(deep) == str(d), rb.target_dir(deep))
    cmd = rb.PLUGIN.run_command(deep, None)
    check("deep project: run_command points into the cache", cmd[0].startswith(str(d)), cmd)
    src = (ROOT / "radide" / "deploy" / "native" / "rust_native.py").read_text(encoding="utf-8")
    check("native Rust build: CARGO_TARGET_DIR = cargo_cache_dir", "CARGO_TARGET_DIR=str(tdir)" in src
          and "tdir = cargo_cache_dir(nat)" in src)

    from radide.deploy.build import short_build_mirror
    proj = OUT / ("f" * 70) / ("g" * 70) / "FlutterDeep"
    (proj / "lib").mkdir(parents=True, exist_ok=True)
    (proj / "build" / "windows").mkdir(parents=True, exist_ok=True)
    (proj / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")
    (proj / "pubspec.yaml").write_text("name: x\n", encoding="utf-8")
    (proj / "build" / "windows" / "big.obj").write_text("x", encoding="utf-8")
    logs = []
    m = short_build_mirror(proj, "flutter-test", log=logs.append)
    check("Flutter mirror: short folder", len(str(m)) < 90 and m.is_dir(), m)
    check("Flutter mirror: sources copied", (m / "lib" / "main.dart").is_file() and (m / "pubspec.yaml").is_file())
    check("Flutter mirror: build/ of the project not copied", not (m / "build" / "windows" / "big.obj").exists())
    (m / "build").mkdir(exist_ok=True)
    (m / "build" / "keep.txt").write_text("k", encoding="utf-8")
    (proj / "lib" / "main.dart").unlink()
    (proj / "lib" / "app.dart").write_text("// new\n", encoding="utf-8")
    logs.clear()
    m2 = short_build_mirror(proj, "flutter-test", log=logs.append)
    check("Flutter mirror: same folder again", m2 == m)
    check("Flutter mirror: deleted file removed, new file copied", not (m / "lib" / "main.dart").exists()
          and (m / "lib" / "app.dart").is_file())
    check("Flutter mirror: its own build/ kept (incremental)", (m / "build" / "keep.txt").is_file())
    check("Flutter mirror: only changed files copied", "1 file(s) updated" in " ".join(logs), logs)
    shutil.rmtree(m, ignore_errors=True)
    bsrc = (ROOT / "radide" / "deploy" / "build.py").read_text(encoding="utf-8")
    check("build_flutter uses the mirror for deep projects", 'short_build_mirror(real, "flutter"' in bsrc)


# ====================================================================== bridge host
FORM = {
    "version": 2,
    "props": {"Name": "Form1", "Text": "FixAll", "Width": 360, "Height": 240, "StartPosition": "CenterScreen"},
    "controls": [
        {"type": "TextBox", "props": {"Name": "txtMulti", "Text": "", "Left": 10, "Top": 10, "Width": 200,
                                      "Height": 80, "Multiline": True}},
        {"type": "CheckBox", "props": {"Name": "chkA", "Text": "A", "Left": 10, "Top": 100, "Width": 100,
                                       "Height": 22, "Checked": False}},
        {"type": "Label", "props": {"Name": "lblA", "Text": "", "Left": 10, "Top": 130, "Width": 200,
                                    "Height": 22}},
    ],
}

PROGRAM = r'''
import sys
out = open(sys.argv[1], "w", encoding="utf-8")
def send(s):
    sys.stdout.write(s + "\n"); sys.stdout.flush()
def ask(s):
    send(s); return sys.stdin.readline().rstrip("\r\n")
for line in sys.stdin:
    line = line.rstrip("\r\n")
    if line.startswith("EVENT Form1 Load"):
        send("ESC SET txtMulti Text line1\\nline2\\\\end")
        out.write("multi=" + ask("ESC GET txtMulti Text") + "\n")
        out.write("plain=" + ask("GET txtMulti Text") + "\n")
        send("SET chkA Checked True")
        out.write("value=" + ask("GET chkA Value") + "\n")
        out.write("checked=" + ask("GET chkA Checked") + "\n")
        send("SET Clipboard Text fixall-clip")
        out.write("clip=" + ask("GET Clipboard Text") + "\n")
        out.write("clipcall=" + ask("CALL Clipboard GetText") + "\n")
        out.write("screen=" + ask("GET Screen Width") + "\n")
        out.write("app=" + ask("GET App Title") + "\n")
        out.flush()
        send("END")
    elif line == "QUIT":
        break
out.close()
'''


def make_bridge_project(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project.radproj").write_text(json.dumps({"name": "FixAllBridge", "language": "lua-bridge",
                                                        "forms": ["Form1"], "startup": "Form1", "modules": []}),
                                            encoding="utf-8")
    (folder / "Form1.form").write_text(json.dumps(FORM, indent=2), encoding="utf-8")


def host_env(**kw):
    env = dict(os.environ, RADIDE_TEST_NO_DIALOGS="1", PYTHONIOENCODING="utf-8", **kw)
    for k in ("QT_QPA_PLATFORM", "QT_QPA_FONTDIR"):
        env.pop(k, None)
    return env


def test_bridge():
    from radide.runtimes import bridge as B
    # --- KeyCode
    class Ev:
        def __init__(self, sym, keycode=None):
            self.KeyCode, self.raw = sym, type("R", (), {"keycode": keycode})() if keycode is not None else None
    check("KeyCode: Return -> 13", B.vk_code(Ev("Return")) == 13)
    check("KeyCode: Escape / Tab / BackSpace -> 27 / 9 / 8",
          [B.vk_code(Ev(s)) for s in ("Escape", "Tab", "BackSpace")] == [27, 9, 8])
    check("KeyCode: a -> 65, F5 -> 116, Left -> 37, KP_3 -> 99",
          [B.vk_code(Ev(s)) for s in ("a", "F5", "Left", "KP_3")] == [65, 116, 37, 99])
    check("KeyCode: Tk's Windows keycode wins", B.vk_code(Ev("Return", 13)) == 13 and B.vk_code(Ev("x", 88)) == 88
          if os.name == "nt" else True)
    check("KeyCode: a number stays", B.vk_code(Ev(13)) == 13)
    src = (ROOT / "radide" / "runtimes" / "bridge.py").read_text(encoding="utf-8")
    check("EVENT args send vk_code(e)", "{vk_code(e)}" in src)

    # --- missing interpreter
    proj = OUT / "bridge_missing"
    make_bridge_project(proj)
    t0 = time.time()
    try:
        r = run([sys.executable, "-m", "radide.runtimes.bridge", str(proj), "--", "no_such_runtime_xyz.exe",
                 "main.xyz"], cwd=ROOT, timeout=90, env=host_env(RAD_HANDLERS="Form1_Load"))
        rc, err = r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        rc, err = None, "hung (no answer in 90 s)"
    check("missing interpreter: the host exits (no hang)", rc is not None and time.time() - t0 < 90, err)
    check("missing interpreter: exit code 3", rc == 3, (rc, err[-400:]))
    check("missing interpreter: clear message", "was not found on this computer" in err
          and "no_such_runtime_xyz.exe" in err, err[-400:])
    r = run([sys.executable, "-c", "from radide.runtimes.bridge import missing_runtime_text as m; "
             "print(m('dart'))"], cwd=ROOT)
    check("missing interpreter: names the runtime to install (dart -> Dart SDK)", "Dart SDK" in r.stdout, r.stdout)
    # console mode (no forms)
    cproj = OUT / "bridge_missing_console"
    cproj.mkdir(exist_ok=True)
    (cproj / "project.radproj").write_text(json.dumps({"name": "C", "language": "lua-bridge", "forms": [],
                                                       "modules": ["main.lua"]}), encoding="utf-8")
    try:
        r = run([sys.executable, "-m", "radide.runtimes.bridge", str(cproj), "--", "no_such_runtime_xyz.exe"],
                cwd=ROOT, timeout=60, env=host_env())
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = None
    check("missing interpreter (console program): message + exit 3", rc == 3 and "not found" in r.stderr,
          (rc, r.stderr[-300:]))

    # --- ESC multi-line + App / Screen / Clipboard + Checked (real host, a Python script as the program)
    proj = OUT / "bridge_host"
    make_bridge_project(proj)
    prog = proj / "prog.py"
    prog.write_text(PROGRAM, encoding="utf-8")
    res = proj / "result.txt"
    try:
        r = run([sys.executable, "-m", "radide.runtimes.bridge", str(proj), "--", sys.executable, str(prog),
                 str(res)], cwd=ROOT, timeout=120, env=host_env(RAD_HANDLERS="Form1_Load"))
        err = r.stderr
    except subprocess.TimeoutExpired:
        err = "timeout"
    vals = {}
    if res.is_file():
        for line in res.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            vals[k] = v
    # (a multi-line TextBox answers with vbCrLf line ends, like VB)
    check("ESC SET + ESC GET: multi-line text round trip",
          vals.get("multi", "").replace(r"\r\n", r"\n") == r"line1\nline2\\end", (vals, err[-500:]))
    check("plain GET of multi-line text stays on one line",
          vals.get("plain", "").replace("  ", " ") == "line1 line2\\end", vals)
    check("the host ends with END (no hang)", err != "timeout", err[-300:])
    check("CheckBox: SET Checked True -> Value 1", vals.get("value") == "1", vals)
    check("CheckBox: GET Checked -> True", vals.get("checked") == "True", vals)
    check("Clipboard: SET / GET Clipboard Text", vals.get("clip") == "fixall-clip", vals)
    check("Clipboard: CALL Clipboard GetText", vals.get("clipcall") == "fixall-clip", vals)
    check("Screen: GET Screen Width (twips)", vals.get("screen", "0").isdigit() and int(vals["screen"]) > 1000,
          vals)
    check("App: GET App Title", vals.get("app") == "FixAllBridge", vals)


# ====================================================================== clients
STDIN_REPLY = "x\\ny\\\\z\n"          # escaped answer: x<LF>y\z
EXPECT_SET = r"ESC SET Text1 Text a\nb\\c"
EXPECT_GOT = "GOT[x\ny\\z]"


def client_case(name, folder: Path, cmd, files: dict):
    folder.mkdir(parents=True, exist_ok=True)
    for fn, text in files.items():
        (folder / fn).write_text(text, encoding="utf-8")
    try:
        r = run(cmd, cwd=folder, inp=STDIN_REPLY, timeout=300)
    except subprocess.TimeoutExpired:
        check(f"{name}: client ran", False, "timeout")
        return
    out = r.stdout.replace("\r\n", "\n")
    lines = out.splitlines()
    check(f"{name}: multi-line SET goes as one ESC line", EXPECT_SET in lines, (lines, r.stderr[-600:]))
    check(f"{name}: GET asks with ESC", "ESC GET Text1 Text" in lines, lines)
    check(f"{name}: escaped answer decoded", EXPECT_GOT in (r.stderr.replace("\r\n", "\n") + out), (out, r.stderr[-600:]))
    check(f"{name}: one-line SET unchanged", "SET Text1 Caption one" in lines, lines)


def test_clients():
    from radide.languages import get_plugin
    C = ROOT / "radide" / "runtimes" / "clients"
    base = OUT / "clients"

    lua = get_plugin("lua-bridge").tool()
    if lua:
        d = base / "lua"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(C / "lua" / "rad.lua", d / "rad.lua")
        client_case("Lua", d, [lua, "t.lua"], {"t.lua": (
            'package.path = "./?.lua;" .. package.path\nlocal rad = require("rad")\n'
            'rad.set("Text1", "Caption", "one")\nrad.set("Text1", "Text", "a\\nb\\\\c")\n'
            'local v = rad.get("Text1", "Text")\nio.stderr:write("GOT[" .. v .. "]\\n")\n')})
    else:
        skip("Lua client", "lua not found")

    perl = get_plugin("perl-bridge").tool()
    if perl:
        d = base / "perl"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(C / "perl" / "RadGUI.pm", d / "RadGUI.pm")
        client_case("Perl", d, [perl, "-I.", "t.pl"], {"t.pl": (
            'use strict; use RadGUI;\nrad_set("Text1", "Caption", "one");\nrad_set("Text1", "Text", "a\\nb\\\\c");\n'
            'my $v = rad_get("Text1", "Text");\nprint STDERR "GOT[$v]\\n";\n')})
    else:
        skip("Perl client", "perl not found")

    ruby = get_plugin("ruby-bridge").tool()
    if ruby:
        d = base / "ruby"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(C / "ruby" / "rad.rb", d / "rad.rb")
        client_case("Ruby", d, [ruby, "t.rb"], {"t.rb": (
            'require_relative "rad"\nRad.set("Text1", "Caption", "one")\nRad.set("Text1", "Text", "a\\nb\\\\c")\n'
            'v = Rad.get("Text1", "Text")\nSTDERR.write("GOT[#{v}]\\n")\n')})
    else:
        skip("Ruby client", "ruby not found")

    ps = get_plugin("powershell-bridge").tool() or shutil.which("powershell")
    if ps:
        d = base / "ps"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(C / "powershell" / "Rad.ps1", d / "Rad.ps1")
        # the client reads stdin with its own UTF-8 reader ($script:RadIn) - set up by Rad.ps1 itself
        client_case("PowerShell", d, [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "t.ps1"], {"t.ps1": (
            '. "$PSScriptRoot\\Rad.ps1"\nRadSet Text1 Caption "one"\nRadSet Text1 Text ("a`nb\\c")\n'
            '$v = RadGet Text1 Text\n[Console]::Error.WriteLine("GOT[$v]")\n')})
    else:
        skip("PowerShell client", "powershell not found")

    dart = get_plugin("dart-bridge").tool()
    if dart:
        d = base / "dart"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(C / "dart" / "radgui.dart", d / "radgui.dart")
        (d / "pubspec.yaml").write_text("name: t\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\n", encoding="utf-8")
        client_case("Dart", d, [dart, "run", "t.dart"], {"t.dart": (
            "import 'dart:io';\nimport 'radgui.dart';\n"
            "void main() {\n  Rad.set('Text1', 'Caption', 'one');\n  Rad.set('Text1', 'Text', 'a\\nb\\\\c');\n"
            "  final v = Rad.get('Text1', 'Text');\n  stderr.writeln('GOT[$v]');\n}\n")})
    else:
        skip("Dart client", "dart not found")

    fortran = get_plugin("fortran-bridge").tool() if _has("fortran-bridge") else ""
    if fortran:
        d = base / "fortran"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "radide" / "runtimes" / "radgui.f90", d / "radgui.f90")
        for fn in ("radgui.c", "radgui.h"):          # radcall / worker helpers the module binds to
            shutil.copy2(C / "c" / fn, d / fn)
        (d / "t.f90").write_text(
            "program t\n  use radgui\n  character(len=:), allocatable :: v\n"
            "  call rad_set('Text1', 'Caption', 'one')\n"
            "  call rad_set('Text1', 'Text', 'a' // achar(10) // 'b' // achar(92) // 'c')\n"
            "  v = rad_get('Text1', 'Text')\n  write(0, '(A)') 'GOT[' // v // ']'\nend program t\n",
            encoding="utf-8")
        env = dict(os.environ, PATH=str(Path(fortran).parent) + os.pathsep + os.environ.get("PATH", ""))
        r = run([fortran, "radgui.f90", "t.f90", "radgui.c", "-o", "t.exe", "-static"]
                + (["-lws2_32"] if os.name == "nt" else []), cwd=d, timeout=300, env=env)
        check("Fortran: client compiles", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            r = run([str(d / "t.exe")], cwd=d, inp=STDIN_REPLY, timeout=60, env=env)
            lines = r.stdout.replace("\r\n", "\n").splitlines()
            check("Fortran: multi-line SET goes as one ESC line", EXPECT_SET in lines, lines)
            check("Fortran: GET asks with ESC and decodes the answer", "ESC GET Text1 Text" in lines
                  and EXPECT_GOT in r.stderr.replace("\r\n", "\n"), (lines, r.stderr))
    else:
        skip("Fortran client", "gfortran not found")
    csrc = (ROOT / "radide" / "runtimes" / "native" / "radforms" / "radforms.c").read_text(encoding="utf-8")
    check("radforms rad_command understands ESC (native Fortran / rad_line_out)",
          'strncmp(line, "ESC ", 4) == 0' in csrc and "rf_unesc(raw)" in csrc and "rf_esc(r)" in csrc)


def _has(pid):
    try:
        from radide.languages import get_plugin
        return get_plugin(pid) is not None
    except Exception:  # noqa: BLE001
        return False


# ====================================================================== dart publish
def test_dart_publish():
    from radide.languages import get_plugin
    plugin = get_plugin("dart-bridge")
    if not plugin.tool():
        skip("Dart publish", "dart not found")
        return
    folder = OUT / "DartPub"
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    project = new_project("dart-bridge", folder, "DartPub")
    plugin.prepare(folder, project)
    logs = []
    prog = plugin.publish_command(folder, project, logs.append)
    check("Dart publish: dart compile exe made a native program", prog and Path(prog[0]).is_file()
          and prog[0].lower().endswith(".exe"), (prog, logs[-15:]))
    if prog:
        from radide.deploy.build import _pe_imports
        imps = [x.lower() for x in _pe_imports(Path(prog[0]))]
        check("Dart publish: the exe needs no dart.exe / Dart SDK DLL", imps and not any("dart" in x for x in imps),
              imps)
    src = (ROOT / "radide" / "deploy" / "build.py").read_text(encoding="utf-8")
    check("build_bridge uses plugin.publish_command", 'getattr(plugin, "publish_command", None)' in src)


# ====================================================================== lsp manifests
def new_project(pid, folder, name):
    """Like File > New Project (samples/Tests/QA/AllLanguages/checks/common.py create)."""
    from radide.languages import get_plugin
    from radide.workspace import create_project
    p = get_plugin(pid)
    if callable(getattr(p, "create_new_project", None)):
        return p.create_new_project(folder, name)
    return create_project(folder, name, pid)


def test_lsp():
    from radide.lsp import prepare_manifest
    for pid, lang, mk in (("rust-bridge", "rust", lambda f: f / "Cargo.toml"),
                          ("csharp-bridge", "csharp", lambda f: f / "_build" / "csharp" / "RadApp.csproj")):
        folder = OUT / f"lsp_{pid}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        new_project(pid, folder, "LspProj")
        check(f"{pid}: manifest written when the project is created", mk(folder).is_file())
        mk(folder).unlink()
        wrote = prepare_manifest(lang, folder)
        check(f"{pid}: manifest written when the language server starts", wrote and mk(folder).is_file(),
              list(p.name for p in folder.iterdir()))
    check("other languages untouched", prepare_manifest("python", OUT) is False)


# ====================================================================== publish size
def test_size():
    from radide.deploy import build as B
    proj = OUT / "qt_size"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "Form1.py").write_text("from PySide6.QtWidgets import QApplication, QLabel\n", encoding="utf-8")
    uses = B.qt_features(proj)
    check("Qt: a widgets program uses no heavy Qt feature", uses == set(), uses)
    ex = B.qt_excludes(uses)
    check("Qt: QtQml / QtQuick / QtWebEngineCore excluded from PyInstaller",
          {"PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore"} <= set(ex))
    check("Qt: QtWidgets / QtGui never excluded", not any(e.endswith((".QtWidgets", ".QtGui", ".QtCore")) for e in ex))
    (proj / "Web.py").write_text("from PySide6.QtWebEngineWidgets import QWebEngineView\n", encoding="utf-8")
    uses2 = B.qt_features(proj)
    check("Qt: WebEngine use keeps qml + opengl", {"webengine", "qml", "opengl"} <= uses2, uses2)
    (proj / "Web.py").unlink()
    (OUT / "p_none").mkdir(exist_ok=True)
    check("no Qt at all -> no pruning", B.qt_features(OUT / "p_none") is None)
    dist = OUT / "qt_dist" / "_internal" / "PySide6"
    if dist.parent.parent.exists():
        shutil.rmtree(dist.parent.parent, ignore_errors=True)
    keep = ["Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "QtWidgets.pyd", "plugins/platforms/qwindows.dll",
            "plugins/styles/qmodernwindowsstyle.dll", "plugins/imageformats/qico.dll"]
    drop = ["Qt6Qml.dll", "Qt6QmlModels.dll", "Qt6Quick.dll", "Qt6WebEngineCore.dll", "QtQml.pyd", "QtQuick.pyd",
            "opengl32sw.dll", "translations/qt_de.qm", "qml/QtQuick/x.dll", "plugins/qmltooling/a.dll",
            "Qt6Pdf.dll", "plugins/multimedia/m.dll"]
    for f in keep + drop:
        (dist / f).parent.mkdir(parents=True, exist_ok=True)
        (dist / f).write_bytes(b"x" * 1000)
    B.prune_qt(dist.parent.parent, set(), lambda s: None)
    check("Qt prune: widgets files kept", all((dist / f).exists() for f in keep), [f for f in keep if not (dist / f).exists()])
    check("Qt prune: QML / Quick / WebEngine / opengl32sw / translations removed",
          not any((dist / f).exists() for f in drop), [f for f in drop if (dist / f).exists()])
    rp = OUT / "ring_size"
    rp.mkdir(exist_ok=True)
    (rp / "Form1.ring").write_text('load "guilib.ring"\nwin = new qWidget() { b = new qPushButton(win) }\n',
                                   encoding="utf-8")
    check("RingQt: a widgets program can use RingQt Light", B.ring_light_ok(rp))
    m = B.ring_light_mirror(rp, OUT / "ring_size_light", lambda s: None)
    check("RingQt Light: the build copy loads lightguilib.ring, the project is unchanged",
          'load "lightguilib.ring"' in (m / "Form1.ring").read_text(encoding="utf-8")
          and 'load "guilib.ring"' in (rp / "Form1.ring").read_text(encoding="utf-8"))
    (rp / "Web.ring").write_text("w = new qWebView(win)\n", encoding="utf-8")
    check("RingQt: qWebView needs the full RingQt", not B.ring_light_ok(rp))


# ====================================================================== slow: real deep-folder builds
def test_slow():
    from radide.deploy.build import build
    from radide.deploy.config import PublishConfig
    from radide.languages import get_plugin
    from radide.languages.rust_bridge import find_cargo
    deep_root = OUT / ("deep_" + "x" * 70) / ("y" * 70)
    if find_cargo():
        folder = deep_root / "RustDeepNative"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        new_project("rust-bridge", folder, "RustDeepNative")
        cfg = PublishConfig()
        cfg.kind = "native"
        logs = []
        try:
            res = build(folder, cfg, log=logs.append)
            exe = Path(res.dist) / res.exe
            ok = exe.is_file()
        except Exception as e:  # noqa: BLE001
            ok, exe = False, e
        check(f"native Rust publish in a {len(str(folder))}-character folder (no LNK1104)", ok,
              (exe, "\n".join(logs[-25:])))
    else:
        skip("deep native Rust publish", "cargo not found")
    from radide.languages.flutter import flutter_exe
    if flutter_exe():
        folder = deep_root / "FlutterDeep"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        new_project("flutter", folder, "FlutterDeep")
        cfg = PublishConfig()
        logs = []
        try:
            res = build(folder, cfg, log=logs.append)
            exe = Path(res.dist) / res.exe
            ok = exe.is_file()
        except Exception as e:  # noqa: BLE001
            ok, exe = False, e
        check(f"Flutter Windows publish in a {len(str(folder))}-character folder (no FTK1011)", ok,
              (exe, "\n".join(logs[-25:])))
    else:
        skip("deep Flutter publish", "flutter not found")


if __name__ == "__main__":
    groups = [a for a in sys.argv[1:] if not a.startswith("--")] or ["paths", "bridge", "clients", "dart", "lsp", "size"]
    for g in groups:
        print(f"------ {g}", flush=True)
        try:
            {"paths": test_paths, "bridge": test_bridge, "clients": test_clients, "dart": test_dart_publish,
             "lsp": test_lsp, "size": test_size, "slow": test_slow}[g]()
        except Exception as e:  # noqa: BLE001
            import traceback
            check(f"{g}: no exception", False, traceback.format_exc())
    if SLOW and "slow" not in groups:
        print("------ slow", flush=True)
        test_slow()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed   (scratch: {OUT})")
    sys.exit(len(results) - passed)
