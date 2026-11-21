"""Upgrade / downgrade / portable update of the real RAD IDE release files (radide/features/ide_update.py).

    python samples/Tests/Release/test_upgrade.py <scratch> <new setup.exe> <new portable.zip> <old setup.exe>

A local HTTP server plays GitHub (RADIDE_UPDATE_API): a release list with the new version's setup, zip and
SHA256SUMS.txt. LOCALAPPDATA points into <scratch> so the downloads and logs stay there. Steps:
  1. install the OLD setup silently into <scratch>/inst (/CURRENTUSER, no tasks) and plant a stale module
  2. updater: fetch_verified() downloads + checks the new setup; setup_command() upgrades in place
     -> VERSION.txt is the new version, the stale module is gone, the uninstall entry shows the new version,
        the user's file next to the program survives, the new RADIDE.exe starts and shows its window
  3. a tampered download is refused (SHA-256 mismatch)
  4. rollback: the OLD setup over the new one -> old version again
  5. portable: unpack the zip, add settings, portable_command() -> new folder, settings kept, _previous
     kept; restore_command() puts the previous folder back
  6. the Install Another Version dialog lists the releases (offscreen, RADIDE-TEST settings)
  7. uninstall -> folder and uninstall entry removed
Exit code = number of failures."""
from __future__ import annotations

import ctypes
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import winreg
import zipfile
from pathlib import Path

SCRATCH = Path(sys.argv[1]) / "upgrade_test"
NEW_SETUP, NEW_ZIP, OLD_SETUP = (Path(a).resolve() for a in sys.argv[2:5])
REPO = Path(__file__).resolve().parents[3]
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["LOCALAPPDATA"] = str(SCRATCH / "localappdata")
os.environ["RADIDE_NO_BROWSER"] = "1"
sys.path.insert(0, str(REPO))
APP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6C2E8F4A-3B71-4D0E-9A5C-7F1D2E8B4A90}_is1"
RESULTS = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def version_of(name: str) -> str:
    import re
    m = re.search(r"RADIDE-(\d+\.\d+\.\d+)", name)
    return m.group(1) if m else ""


NEW_V, OLD_V = version_of(NEW_SETUP.name), version_of(OLD_SETUP.name)


def reg_version() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY) as k:
            return winreg.QueryValueEx(k, "DisplayVersion")[0]
    except OSError:
        return None


def reg_location() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY) as k:
            return winreg.QueryValueEx(k, "InstallLocation")[0]
    except OSError:
        return None


existing = reg_location()
if existing and not existing.lower().startswith(str(SCRATCH).lower()):
    print(f"RAD IDE is already installed for this user in {existing} - the test would replace it; stopped.")
    sys.exit(1)

# ------------------------------------------------------------------ fake GitHub
SERVE = SCRATCH / "serve"
SERVE.mkdir()
for f in (NEW_SETUP, NEW_ZIP):
    os.link(f, SERVE / f.name) if f.drive == SERVE.drive else shutil.copy2(f, SERVE / f.name)
from radide.features import ide_update as U  # noqa: E402

(SERVE / "SHA256SUMS.txt").write_text(f"{U.sha256(NEW_SETUP)}  {NEW_SETUP.name}\n{U.sha256(NEW_ZIP)}  {NEW_ZIP.name}\n")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SERVE), **kw)

    def log_message(self, *a):
        pass


httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"


def rel_json(v, files, body):
    return {"tag_name": f"v{v}", "name": f"RAD IDE {v}", "body": body, "draft": False, "prerelease": False,
            "published_at": "2026-11-22T00:00:00Z", "html_url": f"{base}/v{v}",
            "assets": [{"name": n, "browser_download_url": f"{base}/{n}", "size": (SERVE / n).stat().st_size}
                       for n in files]}


(SERVE / "releases.json").write_text(json.dumps([
    rel_json(NEW_V, [NEW_SETUP.name, NEW_ZIP.name, "SHA256SUMS.txt"], "## New\n- updater"),
    rel_json(OLD_V, ["SHA256SUMS.txt"], "first release")]))
os.environ["RADIDE_UPDATE_API"] = f"{base}/releases.json"

INST = SCRATCH / "inst"


def run(cmd, timeout=900):
    t = time.time()
    r = subprocess.run(cmd, timeout=timeout)
    return r.returncode, time.time() - t


# ------------------------------------------------------------------ 1. old version
code, dt = run([str(OLD_SETUP), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={INST}",
                "/TASKS=", f"/LOG={SCRATCH / 'install-old.log'}"])
check(code == 0 and (INST / "RADIDE.exe").is_file(), f"install {OLD_V} silently ({dt:.0f} s)", code)
check(reg_version() == OLD_V, "uninstall entry shows the old version", reg_version())
stale = INST / "_internal" / "radide" / "zz_stale_module_from_old_build.py"
stale.write_text("raise SystemExit('stale')\n")
mine = INST / "my-notes.txt"
mine.write_text("user file next to the program\n")

# ------------------------------------------------------------------ 2. upgrade through the updater
rels = U.releases()
check([r["version"] for r in rels] == [NEW_V, OLD_V], "release list from the update API", [r["version"] for r in rels])
check(U.newer(rels[0]["tag"], OLD_V), f"{NEW_V} is newer than {OLD_V}")
setup = U.fetch_verified(rels[0], "installed")
check(setup.is_file() and U.sha256(setup) == U.sha256(NEW_SETUP), "setup downloaded + SHA-256 verified", setup)
cmd = U.setup_command(setup, INST, NEW_V, relaunch=False)
check("/CURRENTUSER" in cmd and f"/DIR={INST}" in cmd and "/RELAUNCH=0" in cmd, "setup command line", cmd)
code, dt = run(cmd)
check(code == 0, f"silent upgrade to {NEW_V} ({dt:.0f} s)", code)
ver = (INST / "VERSION.txt").read_text().strip() if (INST / "VERSION.txt").is_file() else ""
check(ver == NEW_V, "VERSION.txt after the upgrade", ver)
check(not stale.exists(), "old program files removed first (stale module gone)")
check(mine.is_file(), "the user's own file in the folder is kept")
check(reg_version() == NEW_V, "uninstall entry shows the new version", reg_version())
check((U.updates_dir() / f"setup-{NEW_V}.log").is_file(), "setup log written in the updates folder")

# the upgraded IDE starts (its own settings: RADIDE_NO_UPDATE_CHECK keeps it from checking GitHub)
env = dict(os.environ, RADIDE_NO_UPDATE_CHECK="1")
env.pop("RADIDE_UPDATE_API", None)
p = subprocess.Popen([str(INST / "RADIDE.exe")], env=env)
user32 = ctypes.windll.user32
found = {"hwnd": 0}


def find_window():
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _l):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == p.pid and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if "RAD IDE" in buf.value:
                found["hwnd"] = hwnd
                return False
        return True
    user32.EnumWindows(EnumProc(cb), 0)
    return found["hwnd"]


end = time.time() + 120
while time.time() < end and p.poll() is None and not find_window():
    time.sleep(1)
check(found["hwnd"] and p.poll() is None, f"upgraded RADIDE.exe {NEW_V} starts and shows its window",
      p.poll())
if p.poll() is None:
    user32.PostMessageW(found["hwnd"], 0x0010, 0, 0)      # WM_CLOSE
    try:
        p.wait(30)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(10)

# ------------------------------------------------------------------ 3. tampered download
bad = json.loads(json.dumps(rels[0]))
(SERVE / "tampered.exe").write_bytes(b"MZ not the real setup")
bad["assets"] = [(NEW_SETUP.name, f"{base}/tampered.exe", 21), ("SHA256SUMS.txt", f"{base}/SHA256SUMS.txt", 1)]
(U.updates_dir() / NEW_SETUP.name).unlink(missing_ok=True)
try:
    U.fetch_verified(bad, "installed")
    check(False, "tampered download refused")
except RuntimeError as e:
    check("SHA-256 mismatch" in str(e) and not (U.updates_dir() / NEW_SETUP.name).exists(),
          "tampered download refused and deleted", e)

# ------------------------------------------------------------------ 4. rollback
code, dt = run([str(OLD_SETUP), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={INST}"])
ver = (INST / "VERSION.txt").read_text().strip() if (INST / "VERSION.txt").is_file() else ""
check(code == 0 and reg_version() == OLD_V and (ver in (OLD_V, "")), f"rollback to {OLD_V} ({dt:.0f} s)",
      (code, reg_version(), ver))

# ------------------------------------------------------------------ 5. portable update + restore
PORT = SCRATCH / "portable" / "RADIDE"
with zipfile.ZipFile(NEW_ZIP) as z:
    z.extractall(SCRATCH / "portable_unz")
src = next(p.parent for p in (SCRATCH / "portable_unz").rglob("RADIDE.exe"))
PORT.parent.mkdir(parents=True)
shutil.move(str(src), str(PORT))
(PORT / "settings").mkdir(exist_ok=True)
(PORT / "settings" / "RADIDE.ini").write_text("[General]\nkept=yes\n")
(PORT / "_internal" / "zz_portable_stale.txt").write_text("old")
zip_dl = U.fetch_verified(rels[0], "portable")
code, dt = run(U.portable_command(zip_dl, PORT, NEW_V, wait_pid=0, relaunch=False))
plog = U.updates_dir() / f"portable-{NEW_V}.log"
check(code == 0 and "done" in (plog.read_text("utf-8-sig") if plog.is_file() else ""),
      f"portable update ({dt:.0f} s)", plog.read_text("utf-8-sig")[-300:] if plog.is_file() else code)
check((PORT / "RADIDE.exe").is_file() and not (PORT / "_internal" / "zz_portable_stale.txt").exists(),
      "portable folder replaced by the new build")
check((PORT / "settings" / "RADIDE.ini").is_file() and "kept=yes" in (PORT / "settings" / "RADIDE.ini").read_text(),
      "portable settings kept")
prev = PORT.with_name("RADIDE_previous")
check((prev / "_internal" / "zz_portable_stale.txt").is_file(), "previous portable folder kept as RADIDE_previous")
code, dt = run(U.restore_command(PORT, wait_pid=0, relaunch=False))
check((PORT / "_internal" / "zz_portable_stale.txt").is_file() and (prev / "RADIDE.exe").is_file(),
      "Restore Previous Version swaps the folders back")

# ------------------------------------------------------------------ 6. versions dialog
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
QSettings().clear()
dlg = U.VersionsDialog(None)
end = time.time() + 20
while time.time() < end and dlg.tree.topLevelItemCount() < 2:
    app.processEvents()
    time.sleep(0.05)
check(dlg.tree.topLevelItemCount() == 2, "Install Another Version lists the releases",
      [dlg.tree.topLevelItem(i).text(0) for i in range(dlg.tree.topLevelItemCount())])
dlg.grab().save(str(SCRATCH / "versions_dialog.png"))
ud = U.UpdateDialog(None, rels[0])
ud.grab().save(str(SCRATCH / "update_dialog.png"))
check(U.schedule_startup_check(None) is False, "no start-up check in tests")
QSettings().clear()

# ------------------------------------------------------------------ 7. uninstall
unins = sorted(INST.glob("unins*.exe"))
code, dt = run([str(unins[-1]), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]) if unins else (-1, 0)
end = time.time() + 60
while time.time() < end and (reg_version() or (INST / "RADIDE.exe").exists()):
    time.sleep(1)
check(code == 0 and reg_version() is None and not (INST / "RADIDE.exe").exists(), "uninstall removes the program",
      (code, reg_version()))

httpd.shutdown()
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; files in {SCRATCH}", flush=True)
sys.exit(len(fails))
