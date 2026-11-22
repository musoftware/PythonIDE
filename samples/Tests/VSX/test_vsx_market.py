"""VSX market end-to-end test - real Open VSX (https://open-vsx.org), real downloads, real MainWindow.

Checks: engines.vscode ranges, safe .vsix unpacking (path traversal / absolute / symlink refused), nls
localisation (Arabic), search + paging + categories, the Extensions view (search "dracula", details page with
README and contributions), install a theme / a snippet pack / a grammar pack / an extension with dependencies,
uninstall (dependency kept while needed, orphans removed), Install from VSIX (+ dependency from Open VSX),
enable / disable events, update check + update, offline cache.

    python samples\\Tests\\VSX\\test_vsx_market.py [out_dir] [--onscreen]

Everything is installed into a scratch folder (RADIDE_VSX_ROOT); QSettings use RADIDE-TEST.
"""
import os
import shutil
import sys
import tempfile
import time
import zipfile

ONSCREEN = "--onscreen" in sys.argv
if ONSCREEN:
    sys.argv.remove("--onscreen")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_vsx_out_")
os.makedirs(OUT, exist_ok=True)
WORK = tempfile.mkdtemp(prefix="radide_vsx_")
os.environ["RADIDE_VSX_ROOT"] = os.path.join(WORK, "vsx")
os.environ.pop("RADIDE_VSX_REGISTRY", None)

__import__("PyQt6.QtWebEngineWidgets")                         # before QApplication
from pathlib import Path  # noqa: E402
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()

from radide import vsx  # noqa: E402
from radide.vsx import manager as M, package as P, registry as R  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def pump(sec=0.05):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


def wait(cond, timeout=90.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.02)
    return False


def shot(w, name):
    pump(0.3)
    w.grab().save(os.path.join(OUT, name))


# --------------------------------------------------------------------- 1. offline unit checks
for rng, ok in [("^1.82.0", True), ("^1.91.0", False), ("*", True), (">=1.60.0", True), ("~1.90.0", True),
                ("1.90.x", True), ("^1.94.0-20240918", False), ("0.10.x", True), (">=1.5 <2", True),
                ("^1.89.0-20240415", True), ("^2.0.0", False)]:
    check(f"engine {rng} vs 1.90.0", R.engine_compatible(rng, "1.90.0") == ok)      # the range parser
for rng, ok in [("^1.101.0", True), ("^1.147.0", True), ("^1.148.0", False), ("^1.94.0", True)]:
    check(f"engine {rng} vs {vsx.API_LEVEL}", R.engine_compatible(rng, vsx.API_LEVEL) == ok)   # the emulated level

evil_dir = Path(WORK) / "evil"
evil_dir.mkdir()
for label, member in [("traversal", "extension/../../evil.txt"), ("absolute", "extension//abs.txt"),
                      ("device", "extension/CON.txt")]:
    vf = evil_dir / f"{label}.vsix"
    with zipfile.ZipFile(vf, "w") as z:
        z.writestr("extension/package.json", '{"publisher":"x","name":"y","version":"1.0.0"}')
        z.writestr(member, "boom")
    try:
        P.safe_extract(vf, evil_dir / f"out-{label}")
        check(f"unsafe vsix refused ({label})", False)
    except P.VsixError as e:
        check(f"unsafe vsix refused ({label})", not (evil_dir / f"out-{label}").exists()
              and not (Path(WORK).parent / "evil.txt").exists(), str(e))
vf = evil_dir / "symlink.vsix"
with zipfile.ZipFile(vf, "w") as z:
    z.writestr("extension/package.json", '{"publisher":"x","name":"y","version":"1.0.0"}')
    zi = zipfile.ZipInfo("extension/link")
    zi.external_attr = (0o120777 << 16)
    z.writestr(zi, "C:/Windows")
try:
    P.safe_extract(vf, evil_dir / "out-link")
    check("unsafe vsix refused (symlink)", False)
except P.VsixError as e:
    check("unsafe vsix refused (symlink)", True, str(e))

hello_src = Path(HERE) / "hello-vsx" / "extension"
hello_vsix = P.pack_vsix(hello_src, Path(WORK) / "radide-tests.hello-vsx-1.0.0.vsix")
m_en = P.read_vsix_manifest(hello_vsix, "en")
m_ar = P.read_manifest(hello_src, "ar")
check("nls English", m_en.display_name == "Hello VSX (RAD IDE test)", m_en.display_name)
check("nls Arabic", m_ar.display_name.startswith("مرحبا"), m_ar.display_name)
check("nls nested (theme label)", m_ar.contributes["themes"][0]["label"] == "مرحبا داكن")
check("manifest deps", m_en.extension_dependencies == ["dracula-theme.theme-dracula"])

# --------------------------------------------------------------------- 2. registry
page = R.search("dracula", size=10)
ids = [f"{e['namespace']}.{e['name']}".lower() for e in page.extensions]
check("search dracula", page.total > 5 and "dracula-theme.theme-dracula" in ids, f"{page.total} results")
p2 = R.search("dracula", offset=5, size=5)
check("search paging", [f"{e['namespace']}.{e['name']}".lower() for e in p2.extensions] == ids[5:10] or
      (p2.offset == 5 and len(p2.extensions) > 0))
pt = R.search("", category="Themes", size=5, sort_by="downloads")
check("search category Themes", all("Themes" in (R.details(e["namespace"], e["name"]).get("categories") or [])
                                    for e in pt.extensions[:2]), str(len(pt.extensions)))
e_old = R.pick_version("redhat.vscode-yaml")
check("pick compatible older version", e_old is not None and
      R.engine_compatible(e_old["engines"]["vscode"]), e_old and e_old.get("version"))

# --------------------------------------------------------------------- 3. IDE + Extensions view
from radide.app import MainWindow  # noqa: E402
from radide.features import vsx_market  # noqa: E402
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: print("WARNING BOX:", a[2:] if len(a) > 2 else a))
QMessageBox.information = staticmethod(lambda *a, **k: None)

events = []
vsx.on_installed.connect(lambda e: events.append(("installed", e.id)))
vsx.on_removed.connect(lambda e: events.append(("removed", e.id)))
vsx.on_enabled.connect(lambda e, on: events.append(("enabled" if on else "disabled", e.id)))

win = MainWindow()
win.resize(1400, 900)
win.show()
pump(1.0)
check("menu action registered", getattr(win, "a_vsx_extensions", None) is not None)
from radide.features import workbench  # noqa: E402
check("workbench view registered", any(s.id == "extensions" for s in workbench.registered_views()))
vsx_market.show_view(win)
view = win.vsx_view
check("view shown", win.dock_vsx.isVisible())
check("popular list loads", wait(lambda: view.market.count() > 5, 60), str(view.market.count()))
view.search.setText("dracula")
view.do_search()
check("view search dracula", wait(lambda: any(
    view.market.item(i).data(0x0100) == "dracula-theme.theme-dracula" for i in range(view.market.count())), 60))
check("load more item", any(view.market.item(i).data(0x0100) == "__more__" for i in range(view.market.count())))
win.dock_vsx.resize(380, 800)
shot(win.dock_vsx, "01_search_dracula.png")

entry = next(c.property("vsxEntry") for c in (view.market.itemWidget(view.market.item(i))
                                               for i in range(view.market.count()))
             if getattr(c, "ext_id", "") == "dracula-theme.theme-dracula")
page_ = vsx_market.open_details(win, "dracula-theme.theme-dracula", entry, view)
check("details README", wait(lambda: "Dracula" in page_.readme.toPlainText() and
                             page_.contrib.topLevelItemCount() > 0, 60))
check("details contributions: themes supported",
      any("Color themes" in page_.contrib.topLevelItem(i).text(0) and "Supported" in page_.contrib.topLevelItem(i).text(1)
          for i in range(page_.contrib.topLevelItemCount())))
shot(page_, "02_details_dracula.png")

# install theme through the view
view.install("dracula-theme.theme-dracula", "2.24.2")        # an older version: tests the update later
check("install theme (view)", wait(lambda: vsx.get("dracula-theme.theme-dracula") is not None and
                                    "dracula-theme.theme-dracula" not in view._busy, 120))
d = vsx.get("dracula-theme.theme-dracula")
check("theme files unpacked", d is not None and d.contributes_list("themes") and
      d.file(d.contributes_list("themes")[0]["path"]).is_file())
check("installed event", ("installed", "dracula-theme.theme-dracula") in events)
check("details buttons after install", wait(lambda: any(
    page_.actions.itemAt(i).widget() and page_.actions.itemAt(i).widget().text() == "Uninstall"
    for i in range(page_.actions.count())), 10))

# snippet pack + grammar pack + extension with dependencies
for eid in ("xabikos.javascriptsnippets", "dunstontc.viml", "mtxr.sqltools-driver-sqlite"):
    view.install(eid)
    check(f"install {eid}", wait(lambda eid=eid: vsx.get(eid) is not None and eid not in view._busy, 180))
sn = vsx.get("xabikos.javascriptsnippets")
check("snippet pack contributes snippets", sn and len(sn.contributes_list("snippets")) > 0)
vi = vsx.get("dunstontc.viml")
check("grammar pack contributes grammars", vi and vi.contributes_list("grammars") and vi.contributes_list("languages"))
dep = vsx.get("mtxr.sqltools")
check("dependency installed", dep is not None and dep.source == "dependency" and
      "mtxr.sqltools-driver-sqlite" in dep.dependency_of, dep and dep.dependency_of)
try:
    M.uninstall("mtxr.sqltools")
    check("uninstall refused while needed", False)
except M.InstallError as e:
    check("uninstall refused while needed", True, str(e))
view.tabs.setCurrentWidget(view.installed)
shot(win.dock_vsx, "03_installed.png")
view.uninstall("mtxr.sqltools-driver-sqlite")
check("uninstall + orphan dependency removed", vsx.get("mtxr.sqltools-driver-sqlite") is None and
      vsx.get("mtxr.sqltools") is None and not (Path(vsx.root()) / "mtxr.sqltools-0.28.6").exists())
check("removed events", ("removed", "mtxr.sqltools") in events)

# Install from VSIX (dependency dracula already installed)
view.install_from_vsix(str(hello_vsix))
check("install from VSIX", wait(lambda: vsx.get("radide-tests.hello-vsx") is not None, 60))
hv = vsx.get("radide-tests.hello-vsx")
check("vsix: source + files", hv and hv.source == "vsix" and hv.icon_path and hv.readme_path, hv and hv.source)
check("vsix: dependency recorded",
      "radide-tests.hello-vsx" in (vsx.get("dracula-theme.theme-dracula").dependency_of or []))
# enable / disable
view.set_enabled("radide-tests.hello-vsx", False)
check("disable", not vsx.get("radide-tests.hello-vsx").enabled and
      "radide-tests.hello-vsx" not in [e.id for e in vsx.list_enabled()])
view.set_enabled("radide-tests.hello-vsx", True)
check("enable events", ("disabled", "radide-tests.hello-vsx") in events and
      ("enabled", "radide-tests.hello-vsx") in events)
hp = vsx_market.open_details(win, "radide-tests.hello-vsx", None, view)
pump(0.5)
check("local details README", "tiny" in hp.readme.toPlainText())
shot(hp, "04_details_local.png")

# update check + update
view.check_updates(show=True)
check("update found", wait(lambda: "dracula-theme.theme-dracula" in view._updates, 90),
      str(list(view._updates)))
shot(win.dock_vsx, "05_updates.png")
old_folder = vsx.get("dracula-theme.theme-dracula").folder
view.install("dracula-theme.theme-dracula", view._updates["dracula-theme.theme-dracula"].get("version"))
check("update installed", wait(lambda: R.newer(vsx.get("dracula-theme.theme-dracula").version, "2.24.2") and
                               "dracula-theme.theme-dracula" not in view._busy, 120),
      vsx.get("dracula-theme.theme-dracula").version)
check("old version folder removed", not (Path(vsx.root()) / old_folder).exists())

# offline cache
os.environ["RADIDE_VSX_REGISTRY"] = "https://offline.invalid"
try:
    R.search("dracula", size=10)
    check("offline: unknown host reports an error", False)
except R.RegistryError:
    check("offline: unknown host reports an error", True)
os.environ.pop("RADIDE_VSX_REGISTRY")
url_d = f"{R.base_url()}/api/dracula-theme/theme-dracula"
import urllib.request  # noqa: E402
_orig = urllib.request.urlopen
urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError("network down"))
try:
    for f in P.cache_dir("json").iterdir():          # make every cached answer stale
        os.utime(f, (time.time() - 86400, time.time() - 86400))
    dd = R.get_json(url_d, ttl=0)
    check("offline details from cache", dd.get("name") == "theme-dracula")
    pg = R.search("dracula", size=10)
    check("offline search from cache", pg.offline and pg.extensions, str(pg.offline))
finally:
    urllib.request.urlopen = _orig

# uninstall everything
for e in list(vsx.list_installed()):
    if vsx.get(e.id):
        try:
            M.uninstall(e.id, force=True)
        except M.InstallError:
            pass
check("uninstall all", not vsx.list_installed(), str(vsx.list_installed()))
print("restart required:", vsx.restart_required())

win.close()
pump(0.3)
QSettings().clear()
shutil.rmtree(WORK, ignore_errors=True)
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed; screenshots in {OUT}")
sys.exit(1 if failed else 0)
