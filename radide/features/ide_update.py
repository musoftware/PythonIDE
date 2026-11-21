"""Updating RAD IDE itself (radide/deploy/update.py is for the user's apps).

Help > Check for Updates...            the latest GitHub release (tags v<version>); "Update Now" downloads the
                                       setup (or the portable zip), checks it against SHA256SUMS.txt, closes
                                       the IDE (the normal close: unsaved files are asked about first), installs
                                       it silently into the same folder and starts the new version.
Help > Install Another Version...      any published release - also an older one, to go back when a new
                                       version has a problem (the installer accepts a downgrade).
Help > Restore Previous Version        portable builds: the folder replaced by the last update is kept as
                                       <folder>_previous and can be put back.
Help > Check for Updates Automatically once a day, a few seconds after start-up (release builds only).

How each kind of installation is updated
  installed  RADIDE-<ver>-setup-win64.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /DIR=<install dir>
             /CURRENTUSER or /ALLUSERS (from where it is installed) /RELAUNCH=1 /LOG=<updates>\\setup-<ver>.log.
             The setup deletes the old program files first ([InstallDelete] {app}\\_internal) and keeps
             settings, extensions and tasks (same AppId, previous folder, previous tasks).
  portable   RADIDE-<ver>-portable-win64.zip: a PowerShell helper waits for the IDE to exit, moves the
             folder to <folder>_previous, unpacks the new build, copies settings\\ and portable.flag back,
             restores the old folder if anything fails, and starts RADIDE.exe.
  source     a git checkout: there is nothing to install - "git pull" (offered when git is available).

RADIDE_UPDATE_API (an URL of a releases list in GitHub's JSON format) replaces the GitHub API - for tests
and mirrors. Downloads and logs go to %LOCALAPPDATA%\\RADIDE\\updates (portable: settings\\updates).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from .. import __version__
from ..paths import GITHUB_REPO

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=40"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
UA = "RAD-IDE-updater"
CHECK_INTERVAL = 24 * 3600
DETACHED = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ============================================================================ versions
def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10); pre-release suffixes are ignored."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", str(text or ""))
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def newer(latest: str, current: str = __version__) -> bool:
    a, b = parse_version(latest), parse_version(current)
    n = max(len(a), len(b))
    return bool(a) and a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


# ============================================================================ releases
def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - https GitHub API or RADIDE_UPDATE_API
        return json.loads(r.read().decode("utf-8"))


def _release(data: dict) -> dict:
    tag = data.get("tag_name") or ""
    return {"tag": tag, "version": ".".join(map(str, parse_version(tag))), "url": data.get("html_url") or RELEASES_URL,
            "name": data.get("name") or tag, "body": data.get("body") or "",
            "date": (data.get("published_at") or "")[:10], "prerelease": bool(data.get("prerelease")),
            "assets": [(a.get("name", ""), a.get("browser_download_url", ""), a.get("size", 0))
                       for a in data.get("assets") or []]}


def releases(timeout: float = 15, include_prerelease: bool = False) -> list[dict]:
    """Published releases, newest version first."""
    url = os.environ.get("RADIDE_UPDATE_API") or RELEASES_API
    data = _get_json(url, timeout)
    if isinstance(data, dict):
        data = [data]
    out = [_release(d) for d in data if isinstance(d, dict) and not d.get("draft")]
    out = [r for r in out if r["version"] and (include_prerelease or not r["prerelease"])]
    out.sort(key=lambda r: parse_version(r["version"]), reverse=True)
    return out


def latest_release(timeout: float = 15) -> dict:
    """{"tag", "version", "url", "name", "body", "date", "assets": [(name, url, size)]} of the latest release."""
    if os.environ.get("RADIDE_UPDATE_API"):
        rels = releases(timeout)
        if not rels:
            raise RuntimeError("no release published yet")
        return rels[0]
    return _release(_get_json(API_URL, timeout))


# ============================================================================ this installation
def install_kind() -> str:
    """'installed' (setup), 'portable' (zip with portable.flag) or 'source' (python -m radide)."""
    from .. import paths
    if not paths.frozen():
        return "source"
    return "portable" if paths.portable() else "installed"


def app_dir() -> Path:
    from .. import paths
    return paths.install_dir()


def updates_dir() -> Path:
    from .. import paths
    d = paths.user_data_dir() / "updates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def asset_for(rel: dict, kind: str) -> tuple[str, str, int] | None:
    want = "-portable-win64.zip" if kind == "portable" else "-setup-win64.exe"
    return next((a for a in rel["assets"] if a[0].lower().endswith(want)), None)


def sums_asset(rel: dict) -> tuple[str, str, int] | None:
    return next((a for a in rel["assets"] if a[0].upper() == "SHA256SUMS.TXT"), None)


# ============================================================================ download + verify
class Cancelled(Exception):
    pass


def download(url: str, dest: Path, progress=None, cancelled=lambda: False, timeout: float = 30) -> Path:
    """Download to dest (via dest.part). progress(done, total)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as f:  # noqa: S310
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            if cancelled():
                raise Cancelled()
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if total and part.stat().st_size != total:
        part.unlink(missing_ok=True)
        raise OSError(f"incomplete download ({part.stat().st_size if part.exists() else 0} of {total} bytes)")
    os.replace(part, dest)
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_hash(sums_text: str, name: str) -> str:
    for line in sums_text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == name:
            return parts[0].lower()
    return ""


def fetch_verified(rel: dict, kind: str, progress=None, cancelled=lambda: False) -> Path:
    """Download the setup / portable zip of a release into updates_dir() and check its SHA-256."""
    asset = asset_for(rel, kind)
    if asset is None:
        raise RuntimeError(f"release {rel['tag']} has no {'portable zip' if kind == 'portable' else 'setup'} file")
    name, url, _size = asset
    sums = sums_asset(rel)
    if sums is None:
        raise RuntimeError(f"release {rel['tag']} has no SHA256SUMS.txt - the download cannot be checked")
    sums_path = download(sums[1], updates_dir() / f"SHA256SUMS-{rel['version']}.txt", cancelled=cancelled)
    want = expected_hash(sums_path.read_text("utf-8", "replace"), name)
    if not want:
        raise RuntimeError(f"{name} is not listed in SHA256SUMS.txt")
    dest = updates_dir() / name
    if not (dest.is_file() and sha256(dest) == want):
        download(url, dest, progress, cancelled)
    got = sha256(dest)
    if got != want:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"{name}: SHA-256 mismatch (expected {want[:16]}..., got {got[:16]}...) - not installed")
    return dest


# ============================================================================ install
def all_users_install(folder: Path) -> bool:
    pf = [os.environ.get(k) for k in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    f = str(folder.resolve()).lower()
    return any(p and f.startswith(str(Path(p).resolve()).lower() + os.sep) for p in pf)


def setup_command(setup: Path, folder: Path, version: str, relaunch: bool = True) -> list[str]:
    log = updates_dir() / f"setup-{version}.log"
    return [str(setup), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/CLOSEAPPLICATIONS",
            "/ALLUSERS" if all_users_install(folder) else "/CURRENTUSER", f"/DIR={folder}", f"/LOG={log}",
            f"/RELAUNCH={1 if relaunch else 0}"]


_PORTABLE_PS1 = r"""
param([string]$Zip, [string]$Dir, [int]$WaitPid, [int]$Relaunch, [string]$Log)
$ErrorActionPreference = 'Stop'
function Say($t) { Add-Content -LiteralPath $Log -Value ("{0:u} {1}" -f (Get-Date), $t) -Encoding UTF8 }
Say "portable update: $Zip -> $Dir"
if ($WaitPid -gt 0) { try { Wait-Process -Id $WaitPid -Timeout 300 -ErrorAction Stop } catch { } }
Start-Sleep -Milliseconds 500
$prev = "$Dir`_previous"
$new = "$Dir`_new"
try {
  if (Test-Path -LiteralPath $new) { Remove-Item -LiteralPath $new -Recurse -Force }
  Expand-Archive -LiteralPath $Zip -DestinationPath $new -Force
  $inner = Get-ChildItem -LiteralPath $new -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'RADIDE.exe') } | Select-Object -First 1
  $src = if (Test-Path (Join-Path $new 'RADIDE.exe')) { $new } elseif ($inner) { $inner.FullName } else { throw 'RADIDE.exe not found in the zip' }
  if (Test-Path -LiteralPath $prev) { Remove-Item -LiteralPath $prev -Recurse -Force }
  Move-Item -LiteralPath $Dir -Destination $prev
  try {
    Move-Item -LiteralPath $src -Destination $Dir
    foreach ($keep in 'settings', 'portable.flag') {
      $p = Join-Path $prev $keep
      if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $Dir $keep) -Recurse -Force }
    }
  } catch {
    Say "failed, restoring the previous version: $_"
    if (Test-Path -LiteralPath $Dir) { Remove-Item -LiteralPath $Dir -Recurse -Force }
    Move-Item -LiteralPath $prev -Destination $Dir
    throw
  }
  if (Test-Path -LiteralPath $new) { Remove-Item -LiteralPath $new -Recurse -Force -ErrorAction SilentlyContinue }
  Say 'done'
} catch { Say "ERROR: $_" }
if ($Relaunch -eq 1) { Start-Process -FilePath (Join-Path $Dir 'RADIDE.exe') -WorkingDirectory $Dir }
"""

_RESTORE_PS1 = r"""
param([string]$Dir, [int]$WaitPid, [int]$Relaunch, [string]$Log)
$ErrorActionPreference = 'Stop'
function Say($t) { Add-Content -LiteralPath $Log -Value ("{0:u} {1}" -f (Get-Date), $t) -Encoding UTF8 }
if ($WaitPid -gt 0) { try { Wait-Process -Id $WaitPid -Timeout 300 -ErrorAction Stop } catch { } }
Start-Sleep -Milliseconds 500
$prev = "$Dir`_previous"; $bad = "$Dir`_replaced"
try {
  if (Test-Path -LiteralPath $bad) { Remove-Item -LiteralPath $bad -Recurse -Force }
  Move-Item -LiteralPath $Dir -Destination $bad
  Move-Item -LiteralPath $prev -Destination $Dir
  $s = Join-Path $bad 'settings'
  if (Test-Path -LiteralPath $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $Dir 'settings') -Recurse -Force }
  Move-Item -LiteralPath $bad -Destination $prev
  Say 'previous version restored'
} catch { Say "ERROR: $_" }
if ($Relaunch -eq 1) { Start-Process -FilePath (Join-Path $Dir 'RADIDE.exe') -WorkingDirectory $Dir }
"""


def _ps_command(script: str, args: list[str], name: str) -> list[str]:
    p = updates_dir() / name
    p.write_text(script, encoding="utf-8-sig")
    return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-File", str(p), *args]


def portable_command(zip_path: Path, folder: Path, version: str, wait_pid: int, relaunch: bool = True) -> list[str]:
    log = updates_dir() / f"portable-{version}.log"
    return _ps_command(_PORTABLE_PS1, ["-Zip", str(zip_path), "-Dir", str(folder), "-WaitPid", str(wait_pid),
                                       "-Relaunch", "1" if relaunch else "0", "-Log", str(log)], "portable-update.ps1")


def restore_command(folder: Path, wait_pid: int, relaunch: bool = True) -> list[str]:
    log = updates_dir() / "restore-previous.log"
    return _ps_command(_RESTORE_PS1, ["-Dir", str(folder), "-WaitPid", str(wait_pid),
                                      "-Relaunch", "1" if relaunch else "0", "-Log", str(log)], "restore-previous.ps1")


def previous_portable() -> Path | None:
    p = app_dir().with_name(app_dir().name + "_previous")
    return p if install_kind() == "portable" and (p / "RADIDE.exe").is_file() else None


def spawn(cmd: list[str]) -> subprocess.Popen:
    """Start the installer / helper so that it outlives the IDE."""
    flags = DETACHED | (NO_WINDOW if cmd[0].lower().startswith("powershell") else 0)
    return subprocess.Popen(cmd, creationflags=flags, close_fds=True, cwd=str(updates_dir()),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ============================================================================ UI
def _tr(text: str) -> str:
    try:
        from ..i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def _settings():
    from .. import paths
    try:
        return paths.qsettings()
    except Exception:  # noqa: BLE001
        from PyQt6.QtCore import QSettings
        return QSettings()


def _markdown(text: str) -> str:
    try:
        import markdown
        return markdown.markdown(text or "")
    except Exception:  # noqa: BLE001
        import html
        return "<pre>" + html.escape(text or "") + "</pre>"


def _run_bg(fn, done):
    from .vsx_market import run_bg
    run_bg(fn, done)


def check_for_updates(parent=None, silent: bool = False) -> dict | None:
    """Help > Check for Updates (silent=True: the start-up check - says nothing unless there is an update)."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QMessageBox
    if not silent:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        rel = latest_release()
    except Exception as e:  # noqa: BLE001 - offline, rate limited, no release yet (404)
        if not silent:
            QApplication.restoreOverrideCursor()
            QMessageBox.information(parent, _tr("Check for Updates"),
                                    f"RAD IDE {__version__}\n\n" + _tr("Could not read the latest release from GitHub:")
                                    + f"\n{e}\n\n{_tr('Releases')}: {RELEASES_URL}")
        return None
    if not silent:
        QApplication.restoreOverrideCursor()
    st = _settings()
    st.setValue("updates/last_check", int(time.time()))
    if newer(rel["tag"]):
        if silent and st.value("updates/skip", "") == rel["version"]:
            return rel
        UpdateDialog(parent, rel).exec()
    elif not silent:
        QMessageBox.information(parent, _tr("Check for Updates"),
                                _tr("RAD IDE {0} is up to date (latest release: {1}).").format(
                                    __version__, rel["tag"] or "-"))
    return rel


def _dialog_base():
    from PyQt6.QtWidgets import QDialog
    return QDialog


class UpdateDialog(_dialog_base()):
    """What is new + Update Now / Skip This Version / Later / Release Page."""

    def __init__(self, parent, rel: dict, title: str | None = None):
        from PyQt6.QtWidgets import QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout
        super().__init__(parent)
        self.rel = rel
        self.setWindowTitle(title or _tr("Update Available"))
        self.resize(620, 480)
        lay = QVBoxLayout(self)
        kind = install_kind()
        down = newer(__version__, rel["version"])
        head = (_tr("RAD IDE {0} is available (you have {1}).") if not down else
                _tr("Install RAD IDE {0} (you have {1}) - this goes back to an older version.")).format(
            rel["version"], __version__)
        lab = QLabel(f"<h3>{head}</h3>")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setHtml(_markdown(rel.get("body") or _tr("(no release notes)")))
        lay.addWidget(notes, 1)
        info = {"installed": _tr("The IDE closes (you are asked to save your work first), the new version is "
                                 "installed in the same folder and starts again. Settings, extensions and "
                                 "projects are kept. If it has a problem, Help > Install Another Version... "
                                 "puts the previous version back."),
                "portable": _tr("The IDE closes, the new version replaces this folder (your settings folder is "
                                "kept) and starts again. The old folder is kept as a backup: Help > Restore "
                                "Previous Version puts it back."),
                "source": _tr("This copy runs from the source code: update it with git pull "
                              "(or download the setup from the release page).")}[kind]
        il = QLabel(info)
        il.setWordWrap(True)
        lay.addWidget(il)
        bb = QDialogButtonBox()
        if kind != "source":
            self.b_update = bb.addButton(_tr("Update Now") if not down else _tr("Install This Version"),
                                         QDialogButtonBox.ButtonRole.AcceptRole)
            self.b_update.clicked.connect(self._update)
        elif shutil.which("git"):
            bb.addButton(_tr("Run git pull"), QDialogButtonBox.ButtonRole.AcceptRole).clicked.connect(self._git_pull)
        if not down:
            bb.addButton(_tr("Skip This Version"), QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self._skip)
        bb.addButton(_tr("Release Page"), QDialogButtonBox.ButtonRole.HelpRole).clicked.connect(self._page)
        bb.addButton(_tr("Later"), QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self.reject)
        lay.addWidget(bb)

    def _page(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(self.rel["url"]))

    def _skip(self):
        _settings().setValue("updates/skip", self.rel["version"])
        self.reject()

    def _git_pull(self):
        from PyQt6.QtWidgets import QMessageBox
        r = subprocess.run(["git", "pull", "--ff-only"], cwd=str(app_dir()), capture_output=True, text=True,
                           creationflags=NO_WINDOW)
        QMessageBox.information(self, "git pull", (r.stdout + r.stderr).strip() or "done")
        self.accept()

    def _update(self):
        if install_release(self.parent(), self.rel, self):
            self.accept()


def install_release(win, rel: dict, owner=None) -> bool:
    """Download + verify, then close the IDE and install. True when the IDE is closing for it."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
    kind = install_kind()
    if kind == "source":
        return False
    parent = owner or win
    dlg = QProgressDialog(_tr("Downloading RAD IDE {0}...").format(rel["version"]), _tr("Cancel"), 0, 100, parent)
    dlg.setWindowTitle(_tr("Update"))
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(0)
    state = {"done": 0, "total": 0, "cancel": False, "res": None, "err": None, "finished": False}
    dlg.canceled.connect(lambda: state.update(cancel=True))

    def work():
        return fetch_verified(rel, kind, lambda d, t: state.update(done=d, total=t), lambda: state["cancel"])

    def done(res, err):
        state.update(res=res, err=err, finished=True)
    _run_bg(work, done)
    while not state["finished"]:
        QApplication.processEvents()
        if state["total"]:
            dlg.setMaximum(100)
            dlg.setValue(int(state["done"] * 100 / state["total"]))
            dlg.setLabelText(_tr("Downloading RAD IDE {0}...").format(rel["version"])
                             + f"\n{state['done'] / 1048576:.1f} / {state['total'] / 1048576:.1f} MB")
        time.sleep(0.03)
    dlg.close()
    if state["err"] is not None:
        if not isinstance(state["err"], Cancelled):
            QMessageBox.warning(parent, _tr("Update"), _tr("The update could not be downloaded:") + f"\n{state['err']}")
        return False
    file = state["res"]
    folder = app_dir()
    cmd = (portable_command(file, folder, rel["version"], os.getpid()) if kind == "portable"
           else setup_command(file, folder, rel["version"]))
    if QMessageBox.question(parent, _tr("Update"),
                            _tr("RAD IDE {0} is downloaded and checked. Close the IDE and install it now?").format(
                                rel["version"])) != QMessageBox.StandardButton.Yes:
        return False
    return close_and_run(win, cmd)


def close_and_run(win, cmd: list[str]) -> bool:
    """Close the main window the normal way (it asks about unsaved work) and start cmd when the IDE quits."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    started = {"p": None}

    def go():
        if started["p"] is None:
            started["p"] = spawn(cmd)
    app.aboutToQuit.connect(go)
    if win is not None:
        win.close()
        if win.isVisible():                     # the user cancelled closing: no update
            try:
                app.aboutToQuit.disconnect(go)
            except TypeError:
                pass
            return False
    for w in QApplication.topLevelWidgets():    # other top-level windows (tool windows, a second main window)
        if w.isVisible() and w is not win:
            w.close()
    go()
    app.quit()
    return True


class VersionsDialog(_dialog_base()):
    """Help > Install Another Version...: every release, to update or to go back."""

    def __init__(self, win):
        from PyQt6.QtWidgets import (QDialogButtonBox, QLabel, QTextBrowser, QTreeWidget, QTreeWidgetItem,
                                     QVBoxLayout)
        super().__init__(win)
        self.win = win
        self.setWindowTitle(_tr("Install Another Version"))
        self.resize(720, 520)
        lay = QVBoxLayout(self)
        lab = QLabel(_tr("Pick a version to install. Going back to an older version keeps your settings, "
                         "extensions and projects.") + f"  ({_tr('current')}: {__version__})")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_tr("Version"), _tr("Date"), _tr("Name")])
        self.tree.setRootIsDecorated(False)
        lay.addWidget(self.tree, 1)
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(True)
        lay.addWidget(self.notes, 1)
        bb = QDialogButtonBox()
        self.b_install = bb.addButton(_tr("Install"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.b_install.setEnabled(False)
        self.b_install.clicked.connect(self._install)
        bb.addButton(QDialogButtonBox.StandardButton.Close).clicked.connect(self.reject)
        lay.addWidget(bb)
        self.rels: list[dict] = []
        self.tree.currentItemChanged.connect(self._sel)
        self.tree.itemDoubleClicked.connect(lambda *_a: self._install())
        self._item_cls = QTreeWidgetItem
        self.notes.setPlainText(_tr("Reading the releases..."))
        _run_bg(lambda: releases(include_prerelease=True), self._loaded)

    def _loaded(self, rels, err):
        if err is not None:
            self.notes.setPlainText(_tr("Could not read the releases:") + f" {err}\n\n{RELEASES_URL}")
            return
        self.rels = rels or []
        for r in self.rels:
            mark = "  ✓" if r["version"] == ".".join(map(str, parse_version(__version__))) else ""
            it = self._item_cls([r["version"] + mark + ("  (pre-release)" if r["prerelease"] else ""), r["date"],
                                 r["name"]])
            self.tree.addTopLevelItem(it)
        self.notes.setPlainText("" if self.rels else _tr("No release is published yet."))
        if self.rels:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _sel(self, cur, _prev):
        i = self.tree.indexOfTopLevelItem(cur) if cur is not None else -1
        if 0 <= i < len(self.rels):
            r = self.rels[i]
            self.notes.setHtml(_markdown(r["body"] or _tr("(no release notes)")))
            self.b_install.setEnabled(install_kind() != "source" and r["version"] != ".".join(
                map(str, parse_version(__version__))))

    def _install(self):
        cur = self.tree.currentItem()
        i = self.tree.indexOfTopLevelItem(cur) if cur is not None else -1
        if 0 <= i < len(self.rels) and self.b_install.isEnabled():
            if install_release(self.win, self.rels[i], self):
                self.accept()


def install_another_version(win) -> None:
    VersionsDialog(win).exec()


def restore_previous(win) -> None:
    from PyQt6.QtWidgets import QMessageBox
    prev = previous_portable()
    if prev is None:
        QMessageBox.information(win, _tr("Restore Previous Version"),
                                _tr("There is no previous version to restore. Installed copies use "
                                    "Help > Install Another Version... instead."))
        return
    if QMessageBox.question(win, _tr("Restore Previous Version"),
                            _tr("Close the IDE and put back the version that the last update replaced?")) \
            == QMessageBox.StandardButton.Yes:
        close_and_run(win, restore_command(app_dir(), os.getpid()))


# ============================================================================ start-up check + menu
def auto_check_enabled() -> bool:
    v = _settings().value("updates/auto", True)
    return v not in (False, "false", "0", 0)


def schedule_startup_check(win, delay_ms: int = 8000) -> bool:
    """Once a day, release builds only, never in tests."""
    from PyQt6.QtCore import QCoreApplication, QTimer
    if os.environ.get("RADIDE_NO_UPDATE_CHECK") == "1" or os.environ.get("RADIDE_NO_BROWSER") == "1":
        return False
    if (QCoreApplication.organizationName() or "").startswith("RADIDE-TEST") or install_kind() == "source":
        return False
    if not auto_check_enabled():
        return False
    try:
        last = int(_settings().value("updates/last_check", 0) or 0)
    except (TypeError, ValueError):
        last = 0
    if time.time() - last < CHECK_INTERVAL:
        return False

    def run():
        def done(rel, err):
            if err is not None or not rel:
                return
            _settings().setValue("updates/last_check", int(time.time()))
            if newer(rel["tag"]) and _settings().value("updates/skip", "") != rel["version"]:
                try:
                    UpdateDialog(win, rel).exec()
                except RuntimeError:
                    pass
        _run_bg(latest_release, done)
    QTimer.singleShot(delay_ms, run)
    return True


def install_menu(win, menu) -> None:
    """Help menu entries beside Check for Updates..."""
    from PyQt6.QtGui import QAction
    a = QAction(_tr("Install Another &Version..."), win)
    a.triggered.connect(lambda: install_another_version(win))
    menu.addAction(a)
    if install_kind() == "portable":
        r = QAction(_tr("Restore &Previous Version"), win)
        r.triggered.connect(lambda: restore_previous(win))
        r.setEnabled(previous_portable() is not None)
        menu.addAction(r)
    auto = QAction(_tr("Check for Updates &Automatically"), win)
    auto.setCheckable(True)
    auto.setChecked(auto_check_enabled())
    auto.toggled.connect(lambda on: _settings().setValue("updates/auto", bool(on)))
    menu.addAction(auto)


__all__ = ["API_URL", "RELEASES_URL", "check_for_updates", "latest_release", "releases", "newer", "parse_version",
           "install_kind", "fetch_verified", "setup_command", "portable_command", "restore_command",
           "install_release", "install_another_version", "restore_previous", "schedule_startup_check",
           "install_menu"]
