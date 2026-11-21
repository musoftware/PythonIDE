"""The VS2022 .NET windows in Arabic + the Dark theme (qh.py harness, QSettings "RADIDE-TEST", widget.grab).

Opens a temp copy of samples/Tests/DotNet/SolutionVS2022 with the UI language set to Arabic and the Dark theme,
opens every new .NET window (New Project wizard, Reference Manager, NuGet project + solution documents, Package
Manager Console, NuGet options, Configuration Manager, Project Dependencies, Solution Property Pages, Project
Properties document, Launch Profiles, Publish, Object Browser, Test Explorer, Configure Code Analysis), takes a
screenshot of each and checks: the window is right-to-left, its main buttons are translated, and the strings the
translator saw but could not translate (i18n.missing()) contain no .NET UI text.

    python samples/Tests/DotNet/EndToEnd/test_arabic_dark.py
"""
import os
import re
import shutil
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QA_NAME", "dotnet-ar-dark")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, finish, pump, shot  # noqa: E402
from PyQt6.QtCore import QSettings, Qt  # noqa: E402
from PyQt6.QtWidgets import QAbstractButton, QApplication, QLabel  # noqa: E402

QSettings().setValue("options/ui_language", "ar")
QSettings().setValue("options/theme", "Dark")
QSettings().sync()

base = Path(qh.WORK) / "dotnet-ar-dark"
shutil.rmtree(base, ignore_errors=True)
shutil.copytree(HERE.parent / "SolutionVS2022", base / "Shop", ignore=shutil.ignore_patterns("bin", "obj", ".vs"))
SLN = base / "Shop" / "SolutionVS2022.sln"

from radide import i18n  # noqa: E402
from radide.foreign import vs_ui  # noqa: E402

w = qh.window()
ARABIC = re.compile(r"[؀-ۿ]")
SEEN = {}


def texts(widget):
    out = []
    for c in [widget] + widget.findChildren(QAbstractButton) + widget.findChildren(QLabel):
        try:
            t = i18n.shown(c) if hasattr(c, "text") else ""
        except Exception:  # noqa: BLE001
            t = ""
        if t and c.isVisibleTo(widget):
            out.append(t)
    return out


def look(name, widget, must=()):
    """Screenshot + RTL + translated-buttons check of one window."""
    try:
        widget.show()
        pump(0.6)
        shot(widget, f"ar_dark_{name}")
        rtl = widget.layoutDirection() == Qt.LayoutDirection.RightToLeft or \
            QApplication.layoutDirection() == Qt.LayoutDirection.RightToLeft
        tx = texts(widget)
        arabic = [t for t in tx if ARABIC.search(t)]
        SEEN[name] = tx
        check(f"{name}: right-to-left", rtl)
        check(f"{name}: shows Arabic text", len(arabic) >= 1, tx[:30])
        for m in must:
            check(f"{name}: '{m}' translated", not any(t.replace("&", "") == m for t in tx), tx[:40])
    except Exception:  # noqa: BLE001
        check(f"{name}: opens", False, traceback.format_exc()[-1200:])


def safe(name, fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        check(f"{name}: opens", False, traceback.format_exc()[-1200:])
        return None


check("UI language is Arabic", i18n.language() == "ar")
vs_ui.open_in_window(w, SLN)
pump(2)
check("solution opened", w.sln is not None and len(w.sln.all_projects()) == 4)
app_p = w.sln.project("App")
shot(w, "ar_dark_main")

from radide.dotnet.templates import wizard as WZ  # noqa: E402
wz = safe("wizard", lambda: WZ.show_wizard(w, add_to=w.sln, exec_=False))
if wz:
    look("new_project_wizard", wz, must=("Next", "Cancel"))
    wz.close()

dlg = safe("refmgr", lambda: vs_ui.add_reference_dialog(w, app_p, "projects", exec_=False))
if dlg:
    look("reference_manager", dlg, must=("OK", "Cancel", "Browse..."))
    dlg.close()

from radide.features import nuget_ide  # noqa: E402
pv = safe("nuget", lambda: nuget_ide.manage_project(w, app_p))
if pv:
    pv.show_preview = False
    qh.wait(lambda: pv.busy == 0 and not pv._running, 60)
    look("nuget_project", pv, must=("Browse", "Installed", "Updates", "Install"))
sv = safe("nuget_sln", lambda: nuget_ide.manage_solution(w))
if sv:
    qh.wait(lambda: sv.busy == 0 and not sv._running, 60)
    look("nuget_solution", sv, must=("Consolidate",))
pmc = safe("pmc", lambda: nuget_ide.show_console(w))
if pmc:
    look("package_manager_console", pmc)
try:
    from radide.dotnet.nuget import options_ui
    od = options_ui.package_sources_dialog(w, exec_=False)
except Exception:  # noqa: BLE001
    od = None
if od is not None and hasattr(od, "show"):
    look("nuget_options", od, must=("OK", "Cancel"))
    od.close()

from radide.dotnet.sln import dialogs as D  # noqa: E402
cm = safe("cfgmgr", lambda: D.configuration_manager(w, w.sln, exec_=False))
if cm:
    look("configuration_manager", cm, must=("Close",))
    cm.close()
pd = safe("deps", lambda: D.project_dependencies(w, w.sln, "App", exec_=False))
if pd:
    look("project_dependencies", pd, must=("OK", "Cancel"))
    pd.close()
spp = safe("spp", lambda: D.solution_property_pages(w, w.sln, exec_=False))
if spp:
    look("solution_property_pages", spp, must=("Single startup project", "Multiple startup projects"))
    spp.close()
props = safe("props", lambda: vs_ui.project_properties(w, app_p))
if props:
    pump(0.5)
    look("project_properties", props, must=())
from radide.dotnet.sln import properties as P  # noqa: E402
lp = safe("launch", lambda: P.launch_profiles_dialog(w, app_p, exec_=False))
if lp:
    look("launch_profiles", lp)
    lp.close()
pub = safe("publish", lambda: D.publish_dialog(w, app_p, exec_=False))
if pub:
    look("publish", pub, must=("Publish",))
    pub.close()
from radide.dotnet.refs.object_browser import show_object_browser  # noqa: E402
ob = safe("ob", lambda: show_object_browser(w))
if ob:
    w.dock_object_browser.resize(1000, 420)
    look("object_browser", w.dock_object_browser)
w.dock_tests.show()
look("test_explorer", w.dock_tests)
try:
    from radide.dotnet.tools import ui as DUI
    cca = DUI.configure_code_analysis(w, w.sln.project("App"), exec_=False)
except Exception:  # noqa: BLE001
    cca = None
if cca is not None:
    look("configure_code_analysis", cca, must=("OK", "Cancel"))
    cca.close()
shot(w, "ar_dark_main_after")

# menus: the new .NET commands are translated
from radide.features import solution_ui  # noqa: E402
root_menu = solution_ui.build_menu(w, w.solution.topLevelItem(0))
eng = []


def walk(m):
    for a in m.actions():
        t = i18n.shown(a).replace("&", "")
        if t and not ARABIC.search(t) and re.search(r"[A-Za-z]{3,}", t) and not re.search(r"\.(sln|slnx)\b|NuGet$", t):
            eng.append(t)
        if a.menu() is not None:
            walk(a.menu())


DATA = {p.name for p in w.sln.all_projects()} | {"Debug", "Release", "Any CPU", "x64", "x86"}
walk(root_menu)
eng = [t for t in eng if t not in DATA]
check("solution context menu fully translated", not eng, eng)

# only strings written in the .NET modules' own source (not template names, package descriptions, rule titles)
SRC = ""
for f in list((Path(qh.ROOT) / "radide" / "dotnet").rglob("*.py")) + [
        Path(qh.ROOT) / "radide" / "features" / "nuget_ide.py", Path(qh.ROOT) / "radide" / "features" /
        "dotnet_tooling.py"]:
    SRC += f.read_text(encoding="utf-8", errors="replace")


def ours(m):
    head = re.split(r"\{|\n|<", m)[0].strip()
    return len(head) >= 4 and (repr(head)[1:-1] in SRC or head in SRC)


def content(m):
    # user data and product content, not UI: project / folder / file names, template list rows (name + description
    # + tags), framework names, proper nouns
    return ("\n" in m or (" " not in m and ("." in m or m.islower())) or m in DATA or m.split("  ")[0] in DATA
            or m in ("Visual Studio", "src", "tests"))


miss = [m for m in i18n.missing() if ours(m) and len(m) < 160 and not content(m)]
print("UNTRANSLATED .NET strings seen:", len(miss))
for m in miss:
    print("   MISSING:", m)
check("no untranslated .NET UI strings seen (i18n.missing)", len(miss) == 0, miss[:40])
finish(w)
