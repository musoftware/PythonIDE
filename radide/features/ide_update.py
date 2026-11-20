"""Help > Check for Updates: compares radide.__version__ with the latest GitHub release of RAD IDE
(https://api.github.com/repos/musoftware/PythonIDE/releases/latest, tags v<version>) and offers the
release page with the setup and portable downloads. (radide/deploy/update.py is for the user's apps.)"""
from __future__ import annotations

import json
import re
import urllib.request

from .. import __version__
from ..paths import GITHUB_REPO

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10); pre-release suffixes are ignored."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", str(text or ""))
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def newer(latest: str, current: str = __version__) -> bool:
    a, b = parse_version(latest), parse_version(current)
    n = max(len(a), len(b))
    return bool(a) and a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def latest_release(timeout: float = 15) -> dict:
    """{"tag", "version", "url", "name", "body", "assets": [(name, url, size)]} of the latest release."""
    req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "RAD-IDE-update-check"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https URL
        data = json.loads(r.read().decode("utf-8"))
    tag = data.get("tag_name") or ""
    return {"tag": tag, "version": ".".join(map(str, parse_version(tag))), "url": data.get("html_url") or RELEASES_URL,
            "name": data.get("name") or tag, "body": data.get("body") or "",
            "assets": [(a.get("name", ""), a.get("browser_download_url", ""), a.get("size", 0))
                       for a in data.get("assets") or []]}


def check_for_updates(parent=None) -> dict | None:
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtWidgets import QApplication, QMessageBox
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        rel = latest_release()
    except Exception as e:  # noqa: BLE001 - offline, rate limited, no release yet (404)
        QApplication.restoreOverrideCursor()
        QMessageBox.information(parent, "Check for Updates",
                                f"RAD IDE {__version__}\n\nCould not read the latest release from GitHub:\n{e}\n\n"
                                f"Releases: {RELEASES_URL}")
        return None
    QApplication.restoreOverrideCursor()
    if newer(rel["tag"]):
        files = "".join(f"<li>{n} ({s / 1048576:.1f} MB)</li>" for n, _u, s in rel["assets"])
        box = QMessageBox(QMessageBox.Icon.Information, "Check for Updates",
                          f"<p>RAD IDE <b>{rel['version']}</b> is available (you have {__version__}).</p>"
                          + (f"<ul>{files}</ul>" if files else "") + "<p>Open the release page to download it?</p>",
                          QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close, parent)
        if box.exec() == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(QUrl(rel["url"]))
    else:
        QMessageBox.information(parent, "Check for Updates",
                                f"RAD IDE {__version__} is up to date (latest release: {rel['tag'] or '-'}).")
    return rel


__all__ = ["API_URL", "RELEASES_URL", "check_for_updates", "latest_release", "newer", "parse_version"]
