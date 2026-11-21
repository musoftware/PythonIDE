"""Open Folder project detection, through the real IDE (offscreen MainWindow).

python test_open_detect.py [case ...]      (cases: folders of ./cases, built by build_cases.py + real CLIs)
"""
import json
import tempfile
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
HERE = Path(__file__).resolve().parent
CASES = Path(os.environ.get("RADIDE_OPENDETECT_CASES") or (Path(tempfile.gettempdir()) / "radide_opendetect_cases"))
SAMPLES = REPO / "samples"

__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
from radide.app import MainWindow  # noqa: E402
from radide.features import open_detect  # noqa: E402
from radide.single_instance import open_target  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def pump(sec=0.05):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


def wait(cond, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.01)
    try:
        return bool(cond())
    except Exception:  # noqa: BLE001
        return False


# case -> (expected detected kind, expected plugin id or "", expected action, sample radproj to compare)
W = SAMPLES / "Tests" / "Web"
EXPECT = {
    "LaravelNew": ("laravel", "php-web", "create", None),            # composer create-project laravel/laravel
    "DotnetConsole": ("dotnet-csproj", "", "inplace", None),          # dotnet new console
    "DotnetWebApi": ("aspnet", "aspnet-web", "inplace", None),        # dotnet new webapi
    "CargoHello": ("cargo", "rust-cargo", "inplace", None),           # cargo new
    "GoHello": ("go", "go-bridge", "inplace", None),                   # go mod init
    "vite-react": ("vite-react", "node-web", "create", None),         # npm create vite
    "flutter_app": ("flutter", "flutter", "create", None),            # flutter create
    "PhpPlain": ("php", "php-web", "create", None),
    "PhpPublic": ("php", "php-web", "create", None),
    "WordPressSite": ("wordpress", "php-web", "create", None),
    "SymfonyApp": ("symfony", "php-web", "create", None),
    "StaticSite": ("static", "static-web", "create", None),
    "ExpressApi": ("express", "node-web", "create", None),
    "NextApp": ("nextjs", "node-web", "create", None),
    "DjangoSite": ("django", "python-django", "create", None),
    "FlaskMini": ("flask", "python-flask", "create", None),
    "FastApiMini": ("fastapi", "python-fastapi", "create", None),
    "PyTkApp": ("python-tk", "python-tk", "create", None),
    "PyQtApp": ("python-qt", "python-qt", "create", None),
    "PyConsole": ("python", "python-tk", "create", None),
    "PygameGame": ("pygame", "python-tk", "create", None),
    "JupyterNb": ("jupyter", "python-tk", "create", None),
    "LooseC": ("c", "c-bridge", "create", None),
    "LooseCpp": ("cpp", "cpp-bridge", "create", None),
    "MakeProj": ("make-c", "c-bridge", "create", None),
    "LooseCSharp": ("csharp", "csharp-bridge", "inplace", None),
    "LooseJava": ("java", "java-bridge", "inplace", None),
    "RailsApp": ("rails", "rails-web", "create", None),
    "SinatraApp": ("sinatra", "rails-web", "create", None),
    "RubyScripts": ("ruby", "ruby-bridge", "inplace", None),
    "RingProg": ("ring", "ring-app", "create", None),
    "LuaScripts": ("lua", "lua-bridge", "inplace", None),
    "PerlScripts": ("perl", "perl-bridge", "inplace", None),
    "PsScripts": ("powershell", "powershell-bridge", "inplace", None),
    "FortranProg": ("fortran", "fortran-bridge", "create", None),
    "DartPkg": ("dart", "dart-bridge", "inplace", None),
    "GodotGame": ("godot", "godot", "create", None),
    "VbBasModules": ("vb", "vb-basic", "create", None),
    "MavenSpring": ("spring", "spring-web", "create", None),
    "KotlinLoose": ("other.kt", "", "plain", None),
    "VbNetLoose": ("other.vb", "", "plain", None),
    "EmptyFolder": (None, "", "plain", None),
    "MultiRepo": ("multi", "", "create", None),
    "S_LaravelBlog": ("laravel", "php-web", "create", W / "Laravel_Blog"),
    "S_CodeIgniterShop": ("codeigniter", "php-web", "create", W / "CodeIgniter_Shop"),
    "S_DjangoBlog": ("django", "python-django", "create", W / "Django_Blog"),
    "S_FlaskTodo": ("flask", "python-flask", "create", W / "Flask_Todo"),
    "S_FastAPIItems": ("fastapi", "python-fastapi", "create", W / "FastAPI_Items"),
    "S_ExpressSite": ("express", "node-web", "create", W / "ExpressSite_Node"),
    "S_NestJS": ("nestjs", "nestjs-web", "create", W / "NestJS_App"),
    "S_ReactVite": ("vite-react", "node-web", "create", W / "Frontend_React_Vite"),
    "S_ShopSitePhp": ("php", "php-web", "create", W / "ShopSite_PhpSqlite"),
    "S_StaticBootstrap": ("static", "static-web", "create", W / "StaticBootstrapSite"),
    "S_AspNet": ("aspnet", "aspnet-web", "inplace", W / "AspNet_App"),
    "S_HelloCSharp": ("csharp", "csharp-bridge", "create", SAMPLES / "HelloCSharp"),
    "S_HelloPython": ("python-tk", "python-tk", "create", SAMPLES / "HelloPython"),
    "S_VB6Calculator": ("vb6", "", "inplace", None),
    "S_CMakeHello": ("cmake", "", "inplace", None),
    "S_DelphiConsole": ("delphi", "", "inplace", None),
    "S_VsSolution": ("vs-solution", "", "inplace", None),
}


def snapshot(folder: Path) -> dict:
    out = {}
    for dp, dn, fn in os.walk(folder):
        dn[:] = [d for d in dn if d not in ("node_modules", "vendor", ".git")]
        for f in fn:
            p = Path(dp, f)
            try:
                st = p.stat()
                out[p.relative_to(folder).as_posix()] = (st.st_size, st.st_mtime_ns)
            except OSError:
                pass
    return out


def open_case(win, name, override=None):
    """Open Folder through open_target; the dialog is answered by the test hook (None = its default)."""
    folder = CASES / name
    seen = {}

    def hook(det):
        seen["det"] = det
        dlg = open_detect.DetectDialog(det, win)          # the real dialog: its default button and choices
        seen["default"] = dlg.default_action()
        seen["chosen"] = dlg.chosen()
        seen["multi"] = dlg._multi
        seen["buttons"] = {b.text(): b.isEnabled() for b in (dlg.b_create, dlg.b_inplace, dlg.b_plain)}
        dlg.deleteLater()
        return (override or seen["default"], seen["chosen"], False)
    open_detect.TEST_HOOK = hook
    open_detect.LAST.clear()
    open_target(win, folder)
    pump(0.3)
    return folder, seen


def verify_case(win, name):
    exp_kind, exp_lang, exp_action, sample = EXPECT[name]
    folder = CASES / name
    before = snapshot(folder)
    folder, seen = open_case(win, name)
    det = seen.get("det")
    action = open_detect.LAST.get("action")
    if exp_kind is None:
        check(f"{name}: nothing detected -> plain folder workspace", det is None and win.project is not None and
              getattr(win.project, "foreign", False), f"det={det.summary() if det else None}")
        return
    if exp_kind == "multi":
        kinds = sorted(f"{c.kind}@{c.rel(det.root)}" for c in seen.get("chosen", []))
        check(f"{name}: several projects -> list dialog", seen.get("multi"), ", ".join(kinds))
        sln = sorted(folder.glob("*.radsln"))
        check(f"{name}: .radsln with one project per sub-folder", len(sln) == 1 and all(
            (folder / s).joinpath("project.radproj").is_file() for s in ("backend", "mobile", "site")),
            sln[0].read_text(encoding="utf-8").replace("\n", " ")[:200] if sln else "no .radsln")
        langs = sorted(st["project"].language for st in win.project_states())
        check(f"{name}: solution opened with its projects", langs == ["flutter", "php-web", "static-web"], str(langs))
    else:
        cand = seen["chosen"][0] if seen.get("chosen") else None
        check(f"{name}: detected {exp_kind}", cand is not None and cand.kind == exp_kind and
              (cand.language or "") == exp_lang, f"{cand.kind}/{cand.language}: {cand.title}" if cand else
              (det.summary() if det else "no detection"))
        check(f"{name}: default action {exp_action}", action == exp_action, f"action={action} buttons={seen.get('buttons')}")
        rp = folder / "project.radproj"
        if exp_action == "create":
            ok = rp.is_file()
            d = json.loads(rp.read_text(encoding="utf-8")) if ok else {}
            check(f"{name}: project.radproj written (language {exp_lang})", ok and d.get("language") == exp_lang,
                  json.dumps({k: d.get(k) for k in ("language", "kind", "startup", "web") if d.get(k)})[:300])
            if sample is not None:
                ref = json.loads((sample / "project.radproj").read_text(encoding="utf-8"))
                rw, dw = ref.get("web") or {}, d.get("web") or {}
                same = ref.get("language") == d.get("language") and str(ref.get("kind", "app")) == str(
                    d.get("kind", "app")) and (rw.get("root", ".") == dw.get("root", ".")) and \
                    (rw.get("framework") or "") == (dw.get("framework") or "") and \
                    set(ref.get("forms") or []) == set(d.get("forms") or [])
                check(f"{name}: same settings as the original sample project", same,
                      f"ref={ref.get('language')} {rw.get('root')} {rw.get('framework')} forms={ref.get('forms')} | "
                      f"got={d.get('language')} {dw.get('root')} {dw.get('framework')} forms={d.get('forms')}")
            check(f"{name}: IDE opened the created project", win.project is not None and
                  win.project.language == exp_lang and not getattr(win.project, "foreign", False),
                  f"{getattr(win.project, 'language', None)}")
        elif exp_action == "inplace":
            check(f"{name}: opened in place, no project file", not rp.exists() and win.project is not None and
                  (getattr(win.project, "foreign", False) or bool(win.project.extra.get("foreign"))), f"project={getattr(win.project, 'name', None)}")
        else:
            check(f"{name}: plain folder workspace", not rp.exists() and win.project is not None and
                  getattr(win.project, "foreign", False) and win.project.extra.get("foreign") == "vscode",
                  f"{getattr(win.project, 'extra', None)}")
    after = snapshot(folder)
    changed = [k for k, v in before.items() if k in after and after[k] != v]
    gone = [k for k in before if k not in after]
    new = [k for k in after if k not in before]
    allowed = {"project.radproj"}
    new_other = [k for k in new if Path(k).name not in allowed and not k.endswith(".radsln")]
    check(f"{name}: user files untouched", not changed and not gone,
          f"changed={changed[:5]} gone={gone[:5]} new={new_other[:6]}")


# ------------------------------------------------------------------------------------------- runs
def fetch(url, timeout=60):
    box = {}

    def go():
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                box["text"] = r.read().decode("utf-8", "replace")
                box["status"] = r.status
        except Exception as e:  # noqa: BLE001
            box["error"] = str(e)
    t = threading.Thread(target=go, daemon=True)
    t.start()
    wait(lambda: not t.is_alive(), timeout + 5)
    return box


def run_site(win, name, needle, timeout=90):
    win.run_project(debug=False)
    srv = getattr(win, "web_server", None)
    ok = wait(lambda: getattr(win, "web_server", None) is not None and win.web_server.port, 30)
    srv = getattr(win, "web_server", None)
    if not ok or srv is None:
        check(f"{name}: Run serves the site", False, "no DevServer")
        return
    url = srv.start_url()
    res = {}
    end = time.time() + timeout
    while time.time() < end:
        res = fetch(url, 60)
        if needle.lower() in res.get("text", "").lower():
            break
        pump(1.0)
    check(f"{name}: Run serves the site ({url})", needle.lower() in res.get("text", "").lower(),
          res.get("error") or f"status {res.get('status')}: {res.get('text', '')[:120]!r}")
    try:
        win.stop_project()
        srv.stop()
    except Exception:  # noqa: BLE001
        pass
    win.web_server = None
    pump(0.5)


def run_program(win, name, needle, timeout=240):
    win.output.clear()
    win.run_project(debug=False)
    wait(lambda: win.session is not None, 20)
    wait(lambda: needle in win.output.toPlainText() or (win.session is not None and not win.session.running()),
         timeout)
    pump(0.5)
    text = win.output.toPlainText()
    ok = needle in text if len(needle) > 4 else any(ln.strip() == needle for ln in text.splitlines())
    check(f"{name}: Run prints {needle!r}", ok, text.strip()[-300:].replace("\n", " | "))
    try:
        win.stop_project()
    except Exception:  # noqa: BLE001
        pass
    pump(0.3)


RUNS = {
    "PhpPlain": ("site", "Hello from PHP"),
    "StaticSite": ("site", "Hello static"),
    "LaravelNew": ("site", "Laravel"),
    "PyConsole": ("prog", "Hello from Python 42"),
    "DotnetConsole": ("prog", "Hello, World!"),
    "CargoHello": ("prog", "Hello, world!"),
    "LooseCSharp": ("prog", "Hello from loose C#"),
    "GoHello": ("prog", "Hello from Go"),
    "LooseJava": ("prog", "hi"),
    "LooseC": ("prog", "hi"),
    "PerlScripts": ("prog", "hi"),
    "LuaScripts": ("prog", "hi"),
    "DartPkg": ("prog", "hi"),
    "PsScripts": ("prog", "hi"),
    "MultiRepo": ("site", "api"),
}


MODALS = []


def _close_modals():
    w = QApplication.activeModalWidget()
    if w is not None:
        txt = getattr(w, "text", lambda: "")() if hasattr(w, "text") else ""
        MODALS.append(f"{w.windowTitle()}: {txt}")
        print(f"!! modal dialog closed: {w.windowTitle()}: {str(txt)[:300]}", flush=True)
        w.reject() if hasattr(w, "reject") else w.close()


def main():
    only = sys.argv[1:]
    import faulthandler
    faulthandler.enable()
    from PyQt6.QtCore import QTimer
    tm = QTimer()
    tm.timeout.connect(_close_modals)
    tm.start(700)
    win = MainWindow()
    win._confirm_close_project = lambda: True
    names = [n for n in EXPECT if (not only or n in only) and (CASES / n).is_dir()]
    t0 = time.time()
    for n in names:
        try:
            verify_case(win, n)
        except Exception as e:  # noqa: BLE001
            import traceback
            check(f"{n}: no exception", False, f"{e}\n{traceback.format_exc()[-800:]}")
        if n in RUNS:
            mode, needle = RUNS[n]
            try:
                (run_site if mode == "site" else run_program)(win, n, needle)
            except Exception as e:  # noqa: BLE001
                check(f"{n}: run without exception", False, str(e))
    # remembered choice: "don't ask again" -> no dialog the next time
    if not only or "remember" in only:
        n = "KotlinLoose"
        open_detect.remember(win, CASES / n, "plain")
        asked = []
        open_detect.TEST_HOOK = lambda det: asked.append(det) or ("create", None, False)
        open_target(win, CASES / n)
        pump(0.2)
        check("remembered 'don't ask again' choice: no question, plain folder", not asked and
              getattr(win.project, "foreign", False), f"asked={len(asked)}")
        open_detect.remember(win, CASES / n, None)
        # the context menu entry of a folder workspace
        from radide.features.solution_ui import MENU_HOOKS
        from PyQt6.QtWidgets import QMenu
        m = QMenu()
        for h in MENU_HOOKS:
            h(win, None, m)
        texts = [a.text() for a in m.actions()]
        check("folder workspace context menu has 'Detect Project Type...'", "Detect Project Type..." in texts,
              str(texts))
        # Detect Project Type... on a plain folder workspace that holds a project -> create
        n2 = "PhpPlain2"
        import shutil
        shutil.rmtree(CASES / n2, ignore_errors=True)
        shutil.copytree(CASES / "PhpPlain", CASES / n2, ignore=shutil.ignore_patterns("project.radproj"))
        open_detect.remember(win, CASES / n2, "plain")
        open_detect.TEST_HOOK = None
        open_target(win, CASES / n2)
        pump(0.2)
        check("remembered plain folder opened as folder workspace", getattr(win.project, "foreign", False))
        open_detect.TEST_HOOK = lambda det: ("create", None, False)
        win.detect_project_type()
        pump(0.3)
        check("Detect Project Type... creates the project", (CASES / n2 / "project.radproj").is_file() and
              win.project.language == "php-web", str(getattr(win.project, "language", None)))
        # offscreen without a hook: the old behaviour (no dialog, nothing written)
        n3 = "PhpPlain3"
        shutil.rmtree(CASES / n3, ignore_errors=True)
        shutil.copytree(CASES / "PhpPlain", CASES / n3, ignore=shutil.ignore_patterns("project.radproj"))
        open_detect.TEST_HOOK = None
        open_target(win, CASES / n3)
        pump(0.2)
        check("offscreen without a test hook keeps the old behaviour", not (CASES / n3 / "project.radproj").exists()
              and getattr(win.project, "foreign", False))
        # command line path (app.main uses open_target too): the same detection
        open_detect.TEST_HOOK = lambda det: ("create", None, False)
        n3 = "StaticSite2"
        shutil.rmtree(CASES / n3, ignore_errors=True)
        shutil.copytree(CASES / "StaticSite", CASES / n3, ignore=shutil.ignore_patterns("project.radproj"))
        open_target(win, str(CASES / n3))
        pump(0.2)
        check("open_target with a str path (command line / Explorer) creates the project",
              (CASES / n3 / "project.radproj").is_file())
    open_detect.TEST_HOOK = None
    check("no unexpected modal dialog", not MODALS, "; ".join(MODALS)[:500])
    passed = sum(1 for r in results if r[1])
    print(f"\n{passed}/{len(results)} checks passed in {time.time() - t0:.0f} s", flush=True)
    try:
        win.stop_project()
    except Exception:  # noqa: BLE001
        pass
    win.close()
    QSettings().clear()
    (CASES / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    code = main()
    os._exit(code)
