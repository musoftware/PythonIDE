"""RAD Modern (Rm*) controls: native radforms modules, component packages, showcase build.

    .venv\\Scripts\\python samples/Tests/Native/test_native_modern.py [scratch folder]

1. samples/Modern/NativeShowcase (C, ribbon + side bar + tabs + grid + gauges + toggles + toast + message box) is
   published with radide.deploy.build.build(): kind "native", one exe (no Python, no DLLs), size limit, only Windows
   system DLLs imported. The exe is started and driven with Win32 messages (controls found by their
   "radforms.name" property) and PrintWindow pixel checks of its own windows (never a screen capture): ribbon
   accent, quick access -> toast window, message box answered with the keyboard, side bar -> grid page, grid check
   cell -> CellValueChanged, dark theme from a toggle, combo box -> Metro theme, timer-driven gauges.
   Only the process started here is touched.
2. Component packages: the 29 Rm* packages load without manifest errors (Toolbox "Modern (RAD)"), have help in
   English and Arabic, draw at design time (rmpaint, QImage offscreen) and generate python-tk code that runs
   (the IDE's Run for Tk / VB6 / GUI Bridge languages); paged containers put children on page(i).
3. Builder: only the rm modules a form uses are linked (+ rm_kit.c), the static library has every module,
   radforms_api.json lists the Rm classes, check() accepts Rm properties / methods in code and still rejects
   unknown ones, the class flags (container / non-visual) are right.
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import winauto as w  # noqa: E402
from radide.deploy import build  # noqa: E402
from radide.deploy.build import _pe_imports  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.deploy.native import radforms_gen as rg, win32_c  # noqa: E402

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_native_modern_"))
SCRATCH.mkdir(parents=True, exist_ok=True)
SHOWCASE = REPO / "samples" / "Modern" / "NativeShowcase"
SYSTEM_DLLS = {"kernel32", "user32", "gdi32", "comctl32", "comdlg32", "shell32", "ole32", "oleaut32", "uxtheme",
               "dwmapi", "gdiplus", "advapi32", "msvcrt", "ucrtbase", "shlwapi", "version", "winmm", "imm32"}
EXE_LIMIT = 450_000
RM_TYPES = ["RmButton", "RmToggle", "RmCheckBox", "RmRadioButton", "RmTextBox", "RmComboBox", "RmSlider", "RmProgress",
            "RmGauge", "RmTile", "RmPanel", "RmGroupPanel", "RmTabStrip", "RmSideBar", "RmNavigationPane", "RmRibbon",
            "RmStatusBar", "RmGrid", "RmListView", "RmTreeView", "RmDatePicker", "RmTimePicker", "RmCalendar",
            "RmDockPanel", "RmDockWindow", "RmToast", "RmSuperTooltip", "RmBalloonTip", "RmMessageBox"]
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail: str = "") -> bool:
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    return bool(cond)


def system_only(exe: Path) -> tuple[bool, list[str]]:
    dlls = _pe_imports(exe)
    bad = [d for d in dlls if d.lower().removesuffix(".dll") not in SYSTEM_DLLS and not d.lower().startswith("api-ms-win-")]
    return bool(dlls) and not bad, bad


def clear_settings():
    from PyQt6.QtCore import QSettings
    QSettings("RADIDE-TEST", "RADIDE-TEST").clear()


# ------------------------------------------------------------------ 1. showcase
def publish() -> Path | None:
    out = SCRATCH / "publish_showcase"
    shutil.rmtree(out, ignore_errors=True)
    cfg = PublishConfig(app_name="NativeShowcase", version="1.0.0", publisher="Musoftware", output_dir=str(out))
    log: list[str] = []
    try:
        res = build.build(SHOWCASE, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        ok("showcase: build", False, f"{e}\n" + "\n".join(log[-15:]))
        return None
    exe = res.dist / res.exe
    ok("showcase: native kind", res.kind == "native" and not res.python_based, res.kind + " " + "\n".join(log[-8:]))
    files = [p.name.lower() for p in res.dist.rglob("*")]
    ok("showcase: only the exe (no Python, no DLLs)", exe.is_file() and not any(n.endswith(".dll") for n in files)
       and "_internal" not in files, ", ".join(files))
    size = exe.stat().st_size if exe.is_file() else 0
    ok(f"showcase: size {size // 1024} KB <= {EXE_LIMIT // 1024} KB", 0 < size <= EXE_LIMIT)
    sysok, bad = system_only(exe)
    ok("showcase: imports only Windows system DLLs", sysok, ", ".join(bad))
    linked = [ln for ln in log if "rm_" in ln and ".c" in ln]
    ok("showcase: rm_tree.c not linked (unused), rm_ribbon.c linked", any("rm_ribbon.c" in ln for ln in linked)
       and not any("rm_tree.c" in ln for ln in linked), "\n".join(linked[:12]))
    leftovers = [p.name for p in SHOWCASE.iterdir() if p.name.startswith(("_rad", "radgui"))]
    ok("showcase: the project folder is left clean", not leftovers, ", ".join(leftovers))
    print(f"   showcase exe: {size:,} bytes", flush=True)
    return exe if exe.is_file() else None


def px(h, x, y):
    return w.grab_pixels(h, [(x, y)])[0]


def dark(c):
    return max(c) < 90


def drive(exe: Path):
    p = w.start(exe)
    f = None
    try:
        f = w.form_window(p.pid, "Form1")
        if not ok("showcase: Form1 shown", f):
            return
        c = w.wait(lambda: (lambda d: d if {"RmRibbon1", "RmGrid1", "RmStatusBar1"} <= set(d) else None)(w.children(f)))
        if not ok("showcase: Rm controls found by name", c, sorted(w.children(f))):
            return
        need = {"RmRibbon1", "RmSideBar1", "RmTabStrip1", "gaCpu", "gaSpeed", "prDisk", "tileMail", "RmGrid1", "tgDark",
                "cboTheme", "slVolume", "txtName", "dpStart", "calMain", "RmStatusBar1", "pnNote"}
        ok("showcase: every control has a window", need <= set(c), sorted(need - set(c)))
        status = lambda: w.get_text(c["RmStatusBar1"])  # noqa: E731
        ok("showcase: Load ran (status text)", w.wait(lambda: "native" in status()), status())
        time.sleep(0.5)
        app = px(c["RmRibbon1"], 10, 26 + 15)
        ok("showcase: ribbon application button painted in the Office accent", app[2] > 120 and app[2] > app[0] + 40, str(app))
        body = px(c["RmRibbon1"], 700, 110)
        ok("showcase: ribbon body light (Office)", min(body) > 200, str(body))
        ok("showcase: dashboard page shown, grid page hidden",
           w.user32.IsWindowVisible(c["gaCpu"]) and not w.user32.IsWindowVisible(c["RmGrid1"]))
        # timer-driven gauges repaint
        pts = [(x, y) for x in range(20, 200, 12) for y in range(20, 180, 12)]
        a = w.grab_pixels(c["gaCpu"], pts)
        time.sleep(1.3)
        b = w.grab_pixels(c["gaCpu"], pts)
        ok("showcase: gauge moves with the timer", a != b)
        # quick access toolbar: 2nd button = btnToast -> a toast window of this process
        w.mouse_click(c["RmRibbon1"], 6 + 26 + 12, 12)
        toast = w.wait(lambda: next((h for h in w.top_windows(p.pid) if w.rf_name(h) == "RmToast1.toast"), None), 5)
        if ok("showcase: quick access -> RmToast window", toast):
            time.sleep(0.5)
            bar = px(toast, 2, 20)
            ok("showcase: success toast has the green bar", bar[1] > 100 and bar[1] > bar[0] + 40 and bar[1] > bar[2] + 40, str(bar))
        # quick access 3rd button = btnAbout -> themed message box, answered with the keyboard
        w.mouse_click(c["RmRibbon1"], 6 + 52 + 12, 12)
        box = w.wait(lambda: next((h for h in w.top_windows(p.pid) if w.rf_name(h) == "RmMessageBox"), None), 5)
        if ok("showcase: RmMessageBox shown (modal)", box):
            ok("showcase: the form is disabled while the box is open", not w.user32.IsWindowEnabled(f))
            w.user32.PostMessageW(box, 0x0100, 0x0D, 0)          # Enter = OK
            ok("showcase: Enter closes it and Show returns OK", w.wait(lambda: status() == "OK"), status())
            ok("showcase: the form is enabled again", w.wait(lambda: w.user32.IsWindowEnabled(f)))
        # side bar: Customers -> grid page
        w.mouse_click(c["RmSideBar1"], 60, 4 + 28 + 34 + 12)
        ok("showcase: side bar ItemClick -> tab strip shows the grid page",
           w.wait(lambda: w.user32.IsWindowVisible(c["RmGrid1"]) and not w.user32.IsWindowVisible(c["gaCpu"])))
        time.sleep(0.4)
        cell = px(c["RmGrid1"], 322, 30 + 14)
        ok("showcase: grid check cell of row 0 is checked (accent)", cell[2] > 120 and cell[2] > cell[0] + 40, str(cell))
        w.mouse_click(c["RmGrid1"], 322, 30 + 14)
        ok("showcase: grid check cell click -> CellValueChanged", w.wait(lambda: status() == "A cell was changed"), status())
        time.sleep(0.3)
        cell = px(c["RmGrid1"], 322, 30 + 14)
        ok("showcase: the check cell is cleared", min(cell) > 180, str(cell))
        # dark mode toggle (on the hidden settings page: keys still reach it)
        w.user32.PostMessageW(c["tgDark"], 0x0100, 0x20, 0)      # Space
        time.sleep(0.8)
        body = px(c["RmRibbon1"], 700, 110)
        ok("showcase: toggle -> Dark theme repaints the ribbon", dark(body), str(body))
        side = px(c["RmSideBar1"], 150, 300)
        ok("showcase: side bar dark too", dark(side), str(side))
        # combo box: Down -> next theme (index 2 Office -> 3 Metro)
        w.user32.PostMessageW(c["cboTheme"], 0x0100, 0x28, 0)    # VK_DOWN
        time.sleep(0.8)
        body = px(c["RmRibbon1"], 700, 110)
        ok("showcase: combo box SelectedIndexChanged -> Metro theme (light again)", min(body) > 200, str(body))
        app = px(c["RmRibbon1"], 10, 26 + 15)
        ok("showcase: Metro accent on the application button", app[2] > 180 and app[0] < 60, str(app))
    finally:
        ok("showcase: closing Form1 ends the program", w.stop(p, f))


# ------------------------------------------------------------------ 2. packages
def packages():
    from radide.components import builtin_packages, is_component_type
    from radide.controls import CONTROL_TYPES, PAGED_TYPES
    pk = builtin_packages()
    rm = [n for n in pk if n.startswith("Rm")]
    ok(f"packages: {len(rm)} Rm* packages", sorted(rm) == sorted(RM_TYPES), str(sorted(set(RM_TYPES) ^ set(rm))))
    errs = {n: pk[n].errors for n in rm if pk[n].errors}
    ok("packages: no manifest errors", not errs, str(errs))
    ok("packages: Toolbox category Modern (RAD)", all(CONTROL_TYPES[n].category == "Modern (RAD)" for n in rm))
    ok("packages: containers / non-visual kinds", CONTROL_TYPES["RmTabStrip"].container and CONTROL_TYPES["RmPanel"].container
       and CONTROL_TYPES["RmToast"].nonvisual and not CONTROL_TYPES["RmGrid"].container)
    ok("packages: class runtime (generated like installed packages)", all(is_component_type(n) for n in rm)
       and not is_component_type("Button"))
    ok("packages: paged containers", {"RmTabStrip", "RmNavigationPane"} <= set(PAGED_TYPES))
    helps = [n for n in rm if not (pk[n].help_path and "بالعربية" in pk[n].help_path.read_text(encoding="utf-8"))]
    ok("packages: help.md in English and Arabic", not helps, ", ".join(helps))
    spec = (REPO / "docs" / "plans" / "MODERN_CONTROLS.md").read_text(encoding="utf-8")
    for t, props in {"RmButton": ["Kind", "ImagePosition", "CornerRadius", "DropDownItems"], "RmGrid": ["Columns", "Rows", "AllowFilter", "GroupBy"],
                     "RmRibbon": ["Tabs", "QuickAccess", "Collapsed", "AppButtonText"], "RmGauge": ["Ranges", "Unit"]}.items():
        names = {p["name"] for p in pk[t].manifest["properties"]}
        ok(f"packages: {t} has the spec properties", set(props) <= names and t in spec, str(set(props) - names))
    # design-time drawing (QImage, offscreen)
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QGuiApplication, QImage, QPainter, QColor
    app = QGuiApplication.instance() or QGuiApplication([])
    from radide.components.rmpaint import paint_control
    blank = []
    for n in rm:
        size = pk[n].manifest["defaultSize"]
        wd, ht = max(60, size[0]), max(40, size[1])
        img = QImage(wd, ht, QImage.Format.Format_RGB32)
        img.fill(QColor("#FF00FF"))
        props = {pr["name"]: pr["default"] for pr in pk[n].manifest["properties"]}
        props.update({"Name": n + "1", "Text": pk[n].manifest.get("overrides", {}).get("Text", "")})
        painter = QPainter(img)
        paint_control(n, painter, QRect(0, 0, wd, ht), props)
        painter.end()
        colors = {img.pixel(x, y) for x in range(0, wd, 4) for y in range(0, ht, 4)}
        if len(colors) < 3 and not CONTROL_TYPES[n].nonvisual:
            blank.append(n)
    ok("packages: every visual Rm control draws at design time", not blank, ", ".join(blank))
    from radide.components import rmpaint
    ok("packages: designer tab click (tab_at) on RmTabStrip / RmNavigationPane",
       rmpaint.tab_at({"TabPages": "One;Two;Three"}, 75, 10, 300, 200) == 1 and
       rmpaint.tab_at({"_type": "RmNavigationPane", "Pages": "A;B;C"}, 20, 200 - 10, 200, 200) == 2)
    del app


def tk_runtime():
    from radide.languages import get_plugin
    from radide.model import Form
    form = Form.load(SHOWCASE / "Form1.form")
    code = get_plugin("python-tk").generate_designer(form, "    def RmRibbon1_ItemClick(self):\n        self.hits.append(self.RmRibbon1.EventItem)\n")
    ok("tk: showcase form generates python-tk code with Rm classes", "RmRibbon(" in code and ".page(1)" in code and
       "RmToast(self.root" in code)
    ns = {"__name__": "rm_tk_test"}
    try:
        exec(compile(code, "<showcase tk>", "exec"), ns)
        cls = ns["Form1Designer"]

        class UI(cls):
            hits: list = []

            def RmRibbon1_ItemClick(self):
                self.hits.append(self.RmRibbon1.EventItem)
        ui = UI(None)
        ui.root.update()
        ui.RmRibbon1._raise("ItemClick", "btnSave", 0)
        ui.RmGrid1.AddRow("Test|Egypt|1|True|Free|5|Details")
        ui.tgDark.Checked = True
        ui.RmTabStrip1.SelectedIndex = 1
        ui.root.update()
        grid_shown = ui.RmTabStrip1._pages[1].winfo_ismapped()
        ok("tk: events reach handlers with EventItem", ui.hits == ["btnSave"], str(ui.hits))
        ok("tk: methods and properties work (AddRow, Checked, SelectedIndex -> page shown)",
           ui.RmGrid1.RowCount == 6 and ui.tgDark.Checked is True and grid_shown)
        ui.root.destroy()
    except Exception:  # noqa: BLE001
        import traceback
        ok("tk: showcase form runs with the Tk runtime", False, traceback.format_exc()[-1500:])


# ------------------------------------------------------------------ 3. builder / ABI
def builder():
    mods = rg.modules_for({"RmButton"})
    ok("builder: RmButton links rm_buttons.c + rm_kit.c only", sorted(m.name for m in mods) == ["rm_buttons.c", "rm_kit.c"],
       str([m.name for m in mods]))
    mods = rg.modules_for(set(RM_TYPES))
    ok("builder: every Rm type has a module", {m.name for m in mods} >= {"rm_kit.c", "rm_buttons.c", "rm_input.c", "rm_progress.c",
                                                                      "rm_panels.c", "rm_bars.c", "rm_notify.c", "rm_ribbon.c",
                                                                      "rm_grid.c", "rm_tree.c", "rm_date.c"})
    mc = rg.module_classes()
    ok("builder: RF_CLASSES of the modules cover the packages", set(RM_TYPES) <= set(mc), str(set(RM_TYPES) - set(mc)))
    api = rg.api_description()
    cls = {c["name"]: c for c in api["classes"]}
    ok("builder: radforms_api.json lists the Rm classes with flags", cls.get("RmTabStrip", {}).get("container") and
       cls.get("RmToast", {}).get("nonvisual") and "Ranges" in cls.get("RmGauge", {}).get("properties", []) and
       "AddRow" in cls.get("RmGrid", {}).get("methods", []))
    saved = json.loads(rg.API_JSON.read_text(encoding="utf-8"))
    ok("builder: radforms_api.json is up to date", saved == json.loads(json.dumps(api)))
    names = {f["name"] for f in api["functions"]}
    ok("builder: new ABI functions (pages, child back, theme lookup, dpi, rtl)",
       {"rf_set_page", "rf_get_page", "rf_set_child_back", "rf_theme_find", "rf_dpi", "rf_rtl"} <= names and api["abi_version"] == 1)
    reasons = rg.code_reasons({"Form1.c": 'rad_set("RmGauge1", "Ranges", "0-50:#00FF00");\nrad_call("RmGrid1", "AddRow", "a;b");\n'
                                          'rad_set("Form1", "Theme", "Dark");'})
    ok("builder: Rm properties / methods / form Theme accepted in code", not reasons, str(reasons))
    reasons = rg.code_reasons({"Form1.c": 'rad_set("RmGauge1", "Sparkle", "1");'})
    ok("builder: unknown properties still rejected", any("Sparkle" in r for r in reasons), str(reasons))
    tc = win32_c.toolchain("c-bridge")
    lib = rg.build_static_lib(SCRATCH / "lib", tc["cc"], log=lambda s: None)
    nm = Path(tc["cc"]).with_name("nm.exe")
    syms = subprocess.run([str(nm), "-g", "--defined-only", str(lib)], capture_output=True, text=True).stdout
    defined = {ln.split()[-1] for ln in syms.splitlines() if " T " in ln}
    ok("builder: libradforms.a has every rm module + rm_kit", {"rfmod_rm_buttons", "rfmod_rm_grid", "rfmod_rm_ribbon", "rfmod_rm_kit",
                                                               "rf_set_page", "rm_popup_run"} <= defined)
    v = rg._val([{"Text": "Home", "Items": [{"Text": "A"}]}])
    ok("builder: nested item props go to the description as JSON", v.startswith("[{") and json.loads(v)[0]["Items"][0]["Text"] == "A")


def main():
    clear_settings()
    try:
        exe = publish()
        if exe is not None:
            drive(exe)
        packages()
        tk_runtime()
        builder()
    finally:
        clear_settings()
    failed = [n for n, good, _ in results if not good]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for n in failed:
        print("  FAILED:", n)
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
