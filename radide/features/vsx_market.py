"""Extensions view - VS Code extensions from Open VSX (https://open-vsx.org) and .vsix files.

Activity Bar "Extensions" (Ctrl+Shift+X), View > Extensions, Tools > VS Code Extensions (Open VSX)...
  * Marketplace: search box, category + sort, cards (icon, name, publisher, downloads, rating, Install),
    paging ("Load more"), offline results from the cache when the network is down.
  * Installed: VS Code extensions (enable / disable / uninstall / update) and the RAD IDE extensions
    (radide/extensions - managed in their own dialog).
  * Updates: newer compatible versions on Open VSX (checked in the background once per session).
  * Details tab (editor area): README (markdown), changelog, the contributions and which of them RAD IDE
    supports, dependencies / extension pack, version picker.
  * "Restart required" banner when an extension with code changed (Reload the extension host).
The engine is radide/vsx (package / registry / manager); contrib and host subsystems listen to its events."""
from __future__ import annotations

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QKeySequence, QPixmap
from PyQt6.QtWidgets import (QComboBox, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSizePolicy,
                             QTabWidget, QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .. import theme
from .. import vsx
from ..vsx import manager as M
from ..vsx import package as P
from ..vsx import registry as R

PAGE = 30
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="vsx")


def _tr(s: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(s)
    except Exception:  # noqa: BLE001
        return s


# ============================================================================ background work
class _Bus(QObject):
    done = pyqtSignal(object, object, object)      # callback, result, error


_bus: _Bus | None = None


def run_bg(fn, done=None) -> None:
    """fn() on a worker thread; done(result, error) on the GUI thread."""
    global _bus
    if _bus is None:
        _bus = _Bus()
        _bus.done.connect(lambda cb, r, e: cb(r, e) if cb else None)
    bus = _bus

    def work():
        try:
            r, e = fn(), None
        except Exception as ex:  # noqa: BLE001
            r, e = None, ex
        try:
            bus.done.emit(done, r, e)
        except RuntimeError:          # the bus is gone (application quit)
            pass
    _pool.submit(work)


def run_bg_progress(parent, title: str, fn, done=None, name: str = "") -> None:
    """run_bg with a status-bar task (radide/progress.py): fn(progress, log) gets a progress(done, total)
    callback (download bytes) and a log(text) callback that becomes the task's status line."""
    from .. import progress
    task = progress.track(title, parent)

    def work():
        try:
            return fn(lambda d, t: task.reporter.bytes(d, t, name), task.reporter.set_text)
        finally:
            task.complete()
    run_bg(work, done)


_icon_cache: dict[str, QPixmap] = {}


def load_icon(url_or_path, label: QLabel, size: int) -> None:
    """Show an extension icon (registry URL or local file) in a label, loaded in the background."""
    key = f"{url_or_path}@{size}"
    placeholder = theme_icon(size)
    label.setPixmap(_icon_cache.get(key, placeholder))
    if not url_or_path or key in _icon_cache:
        return

    def fetch():
        if isinstance(url_or_path, Path):
            return url_or_path.read_bytes()
        return R.binary(url_or_path, kind="icons")

    def show(data, err):
        if err or not data:
            return
        pm = QPixmap()
        if not pm.loadFromData(data):
            return
        pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        _icon_cache[key] = pm
        try:
            label.setPixmap(pm)
        except RuntimeError:          # the card was deleted meanwhile
            pass
    run_bg(fetch, show)


def theme_icon(size: int) -> QPixmap:
    try:
        from .workbench import make_icon
        return make_icon("puzzle", theme.current().get("muted", "#888"), size).pixmap(size, size)
    except Exception:  # noqa: BLE001
        return QPixmap(size, size)


def fmt_count(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.0f}K"
    return str(n)


def stars(r) -> str:
    try:
        r = float(r)
    except (TypeError, ValueError):
        return ""
    full = int(round(r))
    return "★" * full + "☆" * (5 - full) + f" {r:.1f}"


def entry_id(d: dict) -> str:
    return f"{d.get('namespace', '')}.{d.get('name', '')}".lower()


# ============================================================================ cards
class ExtCard(QFrame):
    """One extension in a list: icon, name, publisher, stats, description, action button."""
    action = pyqtSignal(str, str)       # ext id, action name
    opened = pyqtSignal(str)

    def __init__(self, ext_id: str, title: str, publisher: str, desc: str, icon, stats: str = "",
                 version: str = "", parent=None):
        super().__init__(parent)
        self.ext_id = ext_id
        self.setObjectName("vsxCard")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 5)
        lay.setSpacing(8)
        self.icon = QLabel()
        self.icon.setFixedSize(40, 40)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        load_icon(icon, self.icon, 40)
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(1)
        top = QHBoxLayout()
        self.title = QLabel(f"<b>{_esc(title)}</b>" + (f" <span style='color:gray'>{_esc(version)}</span>"
                                                        if version else ""))
        self.title.setTextFormat(Qt.TextFormat.RichText)
        top.addWidget(self.title, 1)
        self.stats = QLabel(stats)
        theme.role(self.stats, "muted")
        top.addWidget(self.stats)
        col.addLayout(top)
        self.desc = QLabel(desc or "")
        self.desc.setWordWrap(False)
        self.desc.setMinimumWidth(10)
        self.desc.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.desc.setToolTip(desc or "")
        col.addWidget(self.desc)
        bot = QHBoxLayout()
        self.pub = QLabel(publisher)
        theme.role(self.pub, "muted")
        bot.addWidget(self.pub, 1)
        for lb in (self.title, self.desc, self.pub):     # extension content ("Go", "Snippets" ...) stays as published
            lb.setProperty("i18n_skip", True)
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(4)
        bot.addLayout(self.buttons)
        col.addLayout(bot)
        lay.addLayout(col, 1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def add_button(self, text: str, name: str, primary: bool = False) -> QPushButton:
        b = QPushButton(_tr(text))
        b.setProperty("vsxAction", name)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(22)
        if primary:
            b.setDefault(False)
            b.setObjectName("vsxPrimary")
        b.clicked.connect(lambda: self.action.emit(self.ext_id, name))
        self.buttons.addWidget(b)
        return b

    def set_busy(self, text: str) -> None:
        for i in range(self.buttons.count()):
            w = self.buttons.itemAt(i).widget()
            if w is not None:
                w.setEnabled(False)
        self.stats.setText(text)

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self.opened.emit(self.ext_id)
        super().mousePressEvent(e)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================================ the view
class ExtensionsView(QWidget):
    """The Extensions side view."""

    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.setObjectName("vsxExtensionsView")
        self._offset = 0
        self._total = 0
        self._query_seq = 0
        self._busy: dict[str, str] = {}
        self._updates: dict[str, dict] = {}
        self._updates_checked = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_tr("Search Extensions in Open VSX"))
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.do_search)
        self._debounce = QTimer(self, singleShot=True, interval=450)
        self._debounce.timeout.connect(self.do_search)
        self.search.textEdited.connect(lambda *_: self._debounce.start())
        row.addWidget(self.search, 1)
        self.more = QToolButton()
        self.more.setText("…")
        self.more.setToolTip(_tr("More Actions"))
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.more)
        menu.addAction(_tr("Install from VSIX..."), self.install_from_vsix)
        menu.addAction(_tr("Check for Extension Updates"), lambda: self.check_updates(show=True))
        menu.addAction(_tr("Update All Extensions"), self.update_all)
        menu.addSeparator()
        menu.addAction(_tr("RAD IDE Extensions..."), self.open_rad_extensions)
        menu.addAction(_tr("Open Extensions Folder"), self.open_folder)
        menu.addAction(_tr("Clear Marketplace Cache"), self.clear_cache)
        self.more.setMenu(menu)
        row.addWidget(self.more)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItem(_tr("All categories"), "")
        for c in R.CATEGORIES:
            self.category.addItem(_tr(c), c)
        self.category.currentIndexChanged.connect(lambda *_: self.do_search())
        row2.addWidget(self.category, 1)
        self.sort = QComboBox()
        for key, text in (("relevance", "Relevance"), ("downloads", "Most downloads"), ("rating", "Rating"),
                          ("date", "Recently published")):
            self.sort.addItem(_tr(text), key)
        self.sort.currentIndexChanged.connect(lambda *_: self.do_search())
        row2.addWidget(self.sort, 1)
        lay.addLayout(row2)
        # restart banner
        self.banner = QFrame()
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(6, 3, 6, 3)
        self.banner_text = QLabel()
        self.banner_text.setWordWrap(True)
        bl.addWidget(self.banner_text, 1)
        self.banner_btn = QPushButton(_tr("Reload"))
        self.banner_btn.clicked.connect(self.reload_host)
        bl.addWidget(self.banner_btn)
        theme.role(self.banner, "banner")
        self.banner.hide()
        lay.addWidget(self.banner)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.market = self._list()
        self.installed = self._list()
        self.updates = self._list()
        self.tabs.addTab(self.market, _tr("Marketplace"))
        self.tabs.addTab(self.installed, _tr("Installed"))
        self.tabs.addTab(self.updates, _tr("Updates"))
        self.tabs.currentChanged.connect(self._tab_changed)
        lay.addWidget(self.tabs, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        theme.role(self.status, "muted")
        lay.addWidget(self.status)
        vsx.on_changed.connect(self._on_changed)
        self.destroyed.connect(lambda *_: vsx.on_changed.disconnect(self._on_changed))
        self.refresh_installed()
        self._update_banner()
        QTimer.singleShot(0, self.do_search)
        QTimer.singleShot(3000, lambda: self.check_updates(show=False))

    # ------------------------------------------------------------------ language
    def changeEvent(self, e):  # noqa: N802
        # the texts here are translated when they are made (cards, headers, menus): Tools > Language rebuilds them
        # (radide/i18n switches the layout direction with the language; Qt's LanguageChange only comes when
        # a Qt translation file is (un)installed)
        if e.type() in (QEvent.Type.LanguageChange, QEvent.Type.LayoutDirectionChange):
            if not getattr(self, "_retranslate_queued", False):
                self._retranslate_queued = True
                QTimer.singleShot(0, self.retranslate)
        super().changeEvent(e)

    def retranslate(self) -> None:
        self._retranslate_queued = False
        try:
            self.search.setPlaceholderText(_tr("Search Extensions in Open VSX"))
            self.more.setToolTip(_tr("More Actions"))
            en = ["Install from VSIX...", "Check for Extension Updates", "Update All Extensions", None,
                  "RAD IDE Extensions...", "Open Extensions Folder", "Clear Marketplace Cache"]
            for a, t in zip(self.more.menu().actions(), en):
                if t and not a.isSeparator():
                    a.setText(_tr(t))
            self.category.setItemText(0, _tr("All categories"))
            for i in range(1, self.category.count()):
                self.category.setItemText(i, _tr(self.category.itemData(i) or ""))
            sorts = {"relevance": "Relevance", "downloads": "Most downloads", "rating": "Rating",
                     "date": "Recently published"}
            for i in range(self.sort.count()):
                self.sort.setItemText(i, _tr(sorts.get(self.sort.itemData(i), self.sort.itemText(i))))
            self.banner_btn.setText(_tr("Reload"))
            self.tabs.setTabText(0, _tr("Marketplace"))
            for i in range(self.market.count()):
                if self.market.item(i).data(Qt.ItemDataRole.UserRole) == "__more__":
                    w = self.market.itemWidget(self.market.item(i))
                    if isinstance(w, QPushButton):
                        w.setText(_tr("Load more"))
            if self._total:
                self.status.setText(_tr("{} extensions").replace("{}", str(self._total)))
            else:
                self.status.clear()
            self._on_changed()
        except RuntimeError:
            pass

    def _list(self) -> QListWidget:
        lw = QListWidget()
        lw.setProperty("i18n_skip_items", True)
        lw.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        lw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        lw.setSpacing(1)
        return lw

    # ------------------------------------------------------------------ marketplace
    def do_search(self, append: bool = False) -> None:
        self._debounce.stop()
        if not append:
            self._offset = 0
        self._query_seq += 1
        seq = self._query_seq
        q, cat, sort = self.search.text().strip(), self.category.currentData() or "", self.sort.currentData()
        ext_id = q[1:] if q.startswith("@id:") else ""
        self.status.setText(_tr("Searching Open VSX..."))
        offset = self._offset

        def work():
            if ext_id:
                ns, name = R.split_id(ext_id)
                d = R.details(ns, name)
                return R.SearchPage([d], 1, 0)
            return R.search(q, cat, offset, PAGE, sort)

        def done(page, err):
            if seq != self._query_seq:
                return
            if err:
                self.status.setText(_tr("Open VSX is not reachable") + f": {err}")
                if not append:
                    self.market.clear()
                return
            if not append:
                self.market.clear()
            else:
                self._drop_more_item()
            for d in page.extensions:
                self._add_market_card(d)
            self._offset = offset + len(page.extensions)
            self._total = page.total
            if self._offset < self._total:
                self._add_more_item()
            msg = _tr("{} extensions").replace("{}", str(page.total))
            if page.offline:
                msg += " - " + _tr("offline (cached results)")
            self.status.setText(msg)
        run_bg(work, done)

    def _add_market_card(self, d: dict) -> None:
        eid = entry_id(d)
        stats = "  ".join(x for x in ("⤓ " + fmt_count(d.get("downloadCount")) if d.get("downloadCount")
                                      else "", stars(d.get("averageRating"))) if x)
        card = ExtCard(eid, d.get("displayName") or d.get("name", ""), d.get("namespace", ""),
                       d.get("description", ""), (d.get("files") or {}).get("icon"), stats)
        card.setProperty("vsxEntry", d)
        self._card_buttons(card, eid)
        card.action.connect(self._card_action)
        card.opened.connect(lambda i, d=d: self.open_details(i, d))
        self._add_card(self.market, card)

    def _card_buttons(self, card: ExtCard, eid: str) -> None:
        if eid in self._busy:
            card.set_busy(self._busy[eid])
            return
        inst = vsx.get(eid)
        if inst is None:
            card.add_button("Install", "install", True)
        else:
            if eid in self._updates:
                card.add_button("Update", "update", True)
            card.add_button("Disable" if inst.enabled else "Enable", "toggle")
            card.add_button("Uninstall", "uninstall")

    def _add_card(self, lw: QListWidget, card: QWidget) -> None:
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole, getattr(card, "ext_id", ""))
        it.setSizeHint(QSize(100, card.sizeHint().height() + 4))
        lw.addItem(it)
        lw.setItemWidget(it, card)

    def _add_more_item(self) -> None:
        b = QPushButton(_tr("Load more"))
        b.clicked.connect(lambda: self.do_search(append=True))
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole, "__more__")
        it.setSizeHint(QSize(100, 30))
        self.market.addItem(it)
        self.market.setItemWidget(it, b)

    def _drop_more_item(self) -> None:
        for i in range(self.market.count() - 1, -1, -1):
            if self.market.item(i).data(Qt.ItemDataRole.UserRole) == "__more__":
                self.market.takeItem(i)

    # ------------------------------------------------------------------ installed / updates
    def refresh_installed(self) -> None:
        self.installed.clear()
        exts = vsx.list_installed()
        hdr = QLabel(f"<b>{_tr('VS Code extensions')}</b> ({len(exts)})")
        self._add_header(self.installed, hdr)
        for e in exts:
            card = self._installed_card(e)
            self._add_card(self.installed, card)
        if not exts:
            self._add_header(self.installed, QLabel(_tr("No VS Code extensions installed yet - search the "
                                                         "Marketplace or use Install from VSIX.")))
        # RAD IDE's own extensions (radide/extensions)
        try:
            from .. import extensions as X
            own = list(X.installed())
        except Exception:  # noqa: BLE001
            own = []
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(4, 8, 4, 2)
        rl.addWidget(QLabel(f"<b>{_tr('RAD IDE extensions')}</b>" + (f" ({len(own)})" if own else "")), 1)
        b = QPushButton(_tr("Manage..."))
        b.clicked.connect(self.open_rad_extensions)
        rl.addWidget(b)
        self._add_header(self.installed, row)
        for x in own:
            name = getattr(x, "name", None) or getattr(x, "id", None) or str(x)
            off = "" if getattr(x, "enabled", True) else " (" + _tr("Disabled") + ")"
            own_label = QLabel("  • " + _esc(str(name)) + off)
            own_label.setProperty("i18n_skip", True)
            self._add_header(self.installed, own_label)
        self.tabs.setTabText(1, _tr("Installed") + f" ({len(exts)})")

    def _installed_card(self, e: P.Extension) -> ExtCard:
        badge = "" if e.enabled else _tr("Disabled")
        if e.id in vsx.restart_required():
            badge = (badge + "  " if badge else "") + _tr("Restart required")
        card = ExtCard(e.id, e.label, e.publisher, e.description, e.icon_path, badge, e.version)
        if not e.enabled:
            card.setEnabled(True)
            card.title.setStyleSheet("color: gray")
        self._card_buttons(card, e.id)
        card.action.connect(self._card_action)
        card.opened.connect(lambda i: self.open_details(i, None))
        return card

    def _add_header(self, lw: QListWidget, w: QWidget) -> None:
        it = QListWidgetItem()
        it.setFlags(Qt.ItemFlag.NoItemFlags)
        it.setSizeHint(QSize(100, max(22, w.sizeHint().height() + 2)))
        lw.addItem(it)
        lw.setItemWidget(it, w)

    def refresh_updates(self) -> None:
        self.updates.clear()
        for eid, entry in sorted(self._updates.items()):
            e = vsx.get(eid)
            if e is None:
                continue
            card = ExtCard(eid, e.label, e.publisher, e.description, e.icon_path,
                           f"{e.version} → {entry.get('version')}")
            if eid in self._busy:
                card.set_busy(self._busy[eid])
            else:
                card.add_button("Update", "update", True)
            card.action.connect(self._card_action)
            card.opened.connect(lambda i: self.open_details(i, None))
            self._add_card(self.updates, card)
        if not self._updates:
            self._add_header(self.updates, QLabel(_tr("All extensions are up to date.") if self._updates_checked
                                                  else _tr("Not checked yet.")))
        n = len(self._updates)
        self.tabs.setTabText(2, _tr("Updates") + (f" ({n})" if n else ""))

    def check_updates(self, show: bool = False) -> None:
        if not vsx.list_installed():
            self._updates_checked = True
            self.refresh_updates()
            return
        self.status.setText(_tr("Checking for extension updates..."))

        def done(res, err):
            if err:
                self.status.setText(_tr("Update check failed") + f": {err}")
                return
            self._updates_checked = True
            self._updates = {e.id: entry for e, entry in res}
            self.refresh_updates()
            self.refresh_installed()
            self.status.setText(_tr("{} updates available").replace("{}", str(len(res))) if res
                                else _tr("All extensions are up to date."))
            if show:
                self.tabs.setCurrentWidget(self.updates)
        run_bg(lambda: M.check_updates(), done)

    def _tab_changed(self, i: int) -> None:
        if self.tabs.widget(i) is self.updates and not self._updates_checked:
            self.check_updates()

    def _on_changed(self) -> None:
        try:
            self.refresh_installed()
            self.refresh_updates()
            self._refresh_market_buttons()
            self._update_banner()
        except RuntimeError:
            pass
        for page in list(_details.values()):
            try:
                page._changed()
            except RuntimeError:
                pass

    def _refresh_market_buttons(self) -> None:
        for i in range(self.market.count()):
            card = self.market.itemWidget(self.market.item(i))
            if isinstance(card, ExtCard):
                while card.buttons.count():
                    w = card.buttons.takeAt(0).widget()
                    if w is not None:
                        w.deleteLater()
                d = card.property("vsxEntry") or {}
                card.stats.setText("  ".join(x for x in ("⤓ " + fmt_count(d.get("downloadCount"))
                                                         if d.get("downloadCount") else "",
                                                         stars(d.get("averageRating"))) if x))
                self._card_buttons(card, card.ext_id)

    # ------------------------------------------------------------------ actions
    def _card_action(self, eid: str, name: str) -> None:
        if name == "install":
            self.install(eid)
        elif name == "update":
            self.install(eid, (self._updates.get(eid) or {}).get("version"))
        elif name == "toggle":
            e = vsx.get(eid)
            if e is not None:
                self.set_enabled(eid, not e.enabled)
        elif name == "uninstall":
            self.uninstall(eid)

    def install(self, eid: str, version: str | None = None, force: bool = False) -> None:
        self._busy[eid] = _tr("Installing...")
        self._on_changed()
        log = self._log

        def done(res, err):
            self._busy.pop(eid, None)
            if isinstance(err, M.InstallError) and "API level" in str(err) and not force:
                self._on_changed()
                if QMessageBox.question(self, _tr("Install Extension"),
                                        str(err) + "\n\n" + _tr("Install the latest version anyway? Themes, "
                                                                "grammars and snippets usually work.")) \
                        == QMessageBox.StandardButton.Yes:
                    self.install(eid, version, True)
                return
            if err:
                self._on_changed()
                self.status.setText(_tr("Install failed") + f": {err}")
                self._log(f"[vsx] install {eid} failed: {err}")
                QMessageBox.warning(self, _tr("Install Extension"), f"{eid}\n\n{err}")
                return
            self._updates.pop(eid, None)
            names = ", ".join(f"{e.label} {e.version}" for e in res) or eid
            self.status.setText(_tr("Installed") + f": {names}")
            self._log(f"[vsx] installed {names}")
            self._on_changed()
        run_bg_progress(self.win, _tr("Installing...") + f" {eid}",
                        lambda prog, say: M.install(eid, version, force=force, progress=prog,
                                                    log=lambda t: (say(str(t)), log(t))), done, eid)

    def uninstall(self, eid: str) -> None:
        e = vsx.get(eid)
        if e is None:
            return
        deps = M.dependents(eid)
        force = False
        if deps:
            if QMessageBox.question(self, _tr("Uninstall Extension"),
                                    _tr("These extensions use {}:").replace("{}", e.label) + "\n" +
                                    "\n".join(deps) + "\n\n" + _tr("Uninstall anyway?")) \
                    != QMessageBox.StandardButton.Yes:
                return
            force = True
        try:
            removed = M.uninstall(eid, force=force)
        except (M.InstallError, P.VsixError) as ex:
            QMessageBox.warning(self, _tr("Uninstall Extension"), str(ex))
            return
        self._updates.pop(eid, None)
        self.status.setText(_tr("Uninstalled") + ": " + ", ".join(removed))
        self._log(f"[vsx] uninstalled {', '.join(removed)}")

    def set_enabled(self, eid: str, on: bool) -> None:
        try:
            M.set_enabled(eid, on)
        except M.InstallError as ex:
            QMessageBox.warning(self, _tr("Extensions"), str(ex))

    def update_all(self) -> None:
        self.status.setText(_tr("Updating extensions..."))
        log = self._log

        def done(res, err):
            self._updates = {} if not err else self._updates
            self.status.setText(_tr("Update failed") + f": {err}" if err else
                                _tr("{} extensions updated").replace("{}", str(len(res or []))))
            self._on_changed()
        run_bg_progress(self.win, "Updating extensions...",
                        lambda prog, say: M.update_all(progress=prog, log=lambda t: (say(str(t)), log(t))), done)

    def install_from_vsix(self, path: str | None = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, _tr("Install from VSIX"), "",
                                                  "VS Code extensions (*.vsix);;All files (*)")
        if not path:
            return
        self.status.setText(_tr("Installing...") + f" {Path(path).name}")
        log = self._log

        def done(res, err):
            if err:
                self.status.setText(_tr("Install failed") + f": {err}")
                QMessageBox.warning(self, _tr("Install from VSIX"), f"{Path(path).name}\n\n{err}")
                return
            names = ", ".join(f"{e.label} {e.version}" for e in res)
            self.status.setText(_tr("Installed") + f": {names}")
            self._log(f"[vsx] installed from VSIX: {names}")
            self.tabs.setCurrentWidget(self.installed)
        run_bg_progress(self.win, _tr("Installing...") + f" {Path(path).name}",
                        lambda prog, say: M.install_vsix_file(path, progress=prog,
                                                              log=lambda t: (say(str(t)), log(t))), done)

    def open_rad_extensions(self) -> None:
        try:
            from .extensions import show_extensions
            show_extensions(self.win)
        except Exception as ex:  # noqa: BLE001
            QMessageBox.warning(self, _tr("Extensions"), str(ex))

    def open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(vsx.root())))

    def clear_cache(self) -> None:
        import shutil
        shutil.rmtree(P.cache_dir(), ignore_errors=True)
        _icon_cache.clear()
        self.status.setText(_tr("Marketplace cache cleared"))

    def reload_host(self) -> None:
        vsx.request_reload()
        if not M._host_available():
            QMessageBox.information(self, _tr("Restart required"),
                                    _tr("Restart RAD IDE to apply the extension changes."))
        self._update_banner()

    def _update_banner(self) -> None:
        pend = vsx.restart_required()
        if not pend:
            self.banner.hide()
            return
        self.banner_text.setText(_tr("Restart required") + ": " + ", ".join(sorted(pend)))
        self.banner_btn.setText(_tr("Reload") if M._host_available() else _tr("OK"))
        self.banner.show()

    def _log(self, msg: str) -> None:
        try:
            self.win.log(msg)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ details
    def open_details(self, eid: str, entry: dict | None) -> None:
        open_details(self.win, eid, entry, view=self)


# ============================================================================ details tab
_details: dict[str, "DetailsPage"] = {}


def open_details(win, eid: str, entry: dict | None = None, view: ExtensionsView | None = None):
    page = _details.get(eid)
    try:
        if page is not None:
            page.isVisible()
    except RuntimeError:
        page = None
    if page is None:
        page = DetailsPage(win, eid, entry, view)
        _details[eid] = page
        page.destroyed.connect(lambda *_: _details.pop(eid, None))
    title = _tr("Extension") + ": " + page.title_text()
    show = getattr(win, "_show_tab", None)
    tabs = getattr(win, "tabs", None)
    if callable(show):
        show(page, title)
    elif tabs is not None:
        tabs.setCurrentIndex(tabs.addTab(page, title))
    else:
        page.show()
    return page


class DetailsPage(QWidget):
    """README / changelog / contributions / dependencies of one extension, with its actions."""

    def __init__(self, win, eid: str, entry: dict | None, view: ExtensionsView | None):
        super().__init__()
        self.win = win
        self.eid = eid
        self.entry = entry or {}
        self.view = view
        self.manifest: dict = {}
        self.setObjectName("vsxDetails")
        self.setProperty("i18n_skip", False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 8)
        head = QHBoxLayout()
        self.icon = QLabel()
        self.icon.setFixedSize(96, 96)
        head.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        self.name = QLabel()
        self.name.setTextFormat(Qt.TextFormat.RichText)
        self.name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.name)
        self.meta = QLabel()
        theme.role(self.meta, "muted")
        self.meta.setTextFormat(Qt.TextFormat.RichText)
        self.meta.setOpenExternalLinks(True)
        col.addWidget(self.meta)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        for lb in (self.name, self.meta, self.desc):     # extension content: never through the UI translator
            lb.setProperty("i18n_skip", True)
        col.addWidget(self.desc)
        self.compat = QLabel()
        self.compat.setWordWrap(True)
        col.addWidget(self.compat)
        self.actions = QHBoxLayout()
        self.actions.setAlignment(Qt.AlignmentFlag.AlignLeft)
        col.addLayout(self.actions)
        head.addLayout(col, 1)
        lay.addLayout(head)
        self.tabs = QTabWidget()
        self.readme = self._browser()
        self.changelog = self._browser()
        self.contrib = QTreeWidget()
        self.contrib.setHeaderLabels([_tr("Contribution"), _tr("RAD IDE"), _tr("Notes")])
        self.contrib.setRootIsDecorated(False)
        self.contrib.setProperty("i18n_skip_items", True)
        self.deps = QTreeWidget()
        self.deps.setHeaderLabels([_tr("Extension"), _tr("Kind"), _tr("Status")])
        self.deps.setRootIsDecorated(False)
        self.deps.itemDoubleClicked.connect(lambda it, _c: open_details(self.win, it.text(0), None, self.view))
        self.tabs.addTab(self.readme, _tr("Details"))
        self.tabs.addTab(self.changelog, _tr("Changelog"))
        self.tabs.addTab(self.contrib, _tr("Feature Contributions"))
        self.tabs.addTab(self.deps, _tr("Dependencies"))
        lay.addWidget(self.tabs, 1)
        vsx.on_changed.connect(self._changed)
        self.destroyed.connect(lambda *_: vsx.on_changed.disconnect(self._changed))
        self.populate()

    def changeEvent(self, e):  # noqa: N802
        if e.type() in (QEvent.Type.LanguageChange, QEvent.Type.LayoutDirectionChange):
            def again():
                try:
                    self.contrib.setHeaderLabels([_tr("Contribution"), _tr("RAD IDE"), _tr("Notes")])
                    self.deps.setHeaderLabels([_tr("Extension"), _tr("Kind"), _tr("Status")])
                    for i, t in enumerate(("Details", "Changelog", "Feature Contributions", "Dependencies")):
                        self.tabs.setTabText(i, _tr(t))
                    self._changed()
                except RuntimeError:
                    pass
            QTimer.singleShot(0, again)
        super().changeEvent(e)

    def _browser(self) -> QTextBrowser:
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setProperty("i18n_skip", True)
        b.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        return b

    def title_text(self) -> str:
        e = vsx.get(self.eid)
        if e is not None:
            return e.label
        return self.entry.get("displayName") or self.entry.get("name") or self.eid

    def _changed(self) -> None:
        try:
            self._build_actions()
            self._header()
        except RuntimeError:
            pass

    def populate(self) -> None:
        inst = vsx.get(self.eid)
        self._header()
        self._build_actions()
        if inst is not None:
            self._show_local(inst)
        if inst is None or not self.entry:
            self._fetch_remote(load_docs=inst is None)

    def _header(self) -> None:
        inst = vsx.get(self.eid)
        d = self.entry
        label = inst.label if inst else (d.get("displayName") or d.get("name") or self.eid)
        version = inst.version if inst else d.get("version", "")
        self.name.setText(f"<span style='font-size:18pt;font-weight:600'>{_esc(label)}</span>"
                          f" &nbsp;<span style='color:gray'>{_esc(version)}</span>")
        bits = [_esc(inst.publisher if inst else d.get("namespace", "")), _esc(self.eid)]
        if d.get("downloadCount"):
            bits.append("⤓ " + fmt_count(d.get("downloadCount")))
        if d.get("averageRating"):
            bits.append(stars(d.get("averageRating")))
        repo = (inst.repository if inst else "") or d.get("repository") or ""
        if repo:
            repo = re.sub(r"^git\+", "", repo)
            bits.append(f"<a href='{_esc(repo)}'>{_tr('Repository')}</a>")
        if d.get("license") or (inst and inst.license):
            bits.append(_esc(d.get("license") or inst.license))
        if inst is not None:
            bits.append(_tr("Installed") + ("" if inst.enabled else " (" + _tr("Disabled") + ")"))
        self.meta.setText(" &nbsp;|&nbsp; ".join(b for b in bits if b))
        self.desc.setText((inst.description if inst else "") or d.get("description", ""))
        load_icon(inst.icon_path if inst and inst.icon_path else (d.get("files") or {}).get("icon"), self.icon, 96)
        eng = (inst.engine_vscode if inst else "") or (d.get("engines") or {}).get("vscode", "")
        if eng and not R.engine_compatible(eng):
            self.compat.setText("⚠ " + _tr("Needs VS Code {0}; RAD IDE emulates the API level {1}.")
                                .replace("{0}", eng).replace("{1}", R.api_level()))
            theme.role(self.compat, "note")
        else:
            self.compat.setText("")

    def _clear_actions(self) -> None:
        while self.actions.count():
            w = self.actions.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def _btn(self, text: str, fn) -> QPushButton:
        b = QPushButton(_tr(text))
        b.clicked.connect(fn)
        self.actions.addWidget(b)
        return b

    def _build_actions(self) -> None:
        self._clear_actions()
        v = self.view or _view(self.win)
        inst = vsx.get(self.eid)
        if v is None:
            return
        if v._busy.get(self.eid):
            lbl = QLabel(v._busy[self.eid])
            self.actions.addWidget(lbl)
            return
        if inst is None:
            self._btn("Install", lambda: v.install(self.eid))
        else:
            if self.eid in v._updates:
                self._btn("Update to {}".replace("{}", v._updates[self.eid].get("version", "")),
                          lambda: v.install(self.eid, v._updates[self.eid].get("version")))
            self._btn("Disable" if inst.enabled else "Enable", lambda: v.set_enabled(self.eid, not inst.enabled))
            self._btn("Uninstall", lambda: v.uninstall(self.eid))
            if inst.path:
                self._btn("Open Folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(inst.path))))
        other = QToolButton()
        other.setText(_tr("Install Another Version..."))
        other.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(other)
        menu.aboutToShow.connect(lambda: self._fill_versions(menu))
        other.setMenu(menu)
        self.actions.addWidget(other)

    def _fill_versions(self, menu: QMenu) -> None:
        if menu.actions():
            return
        menu.addAction(_tr("Loading...")).setEnabled(False)

        def done(entries, err):
            menu.clear()
            if err or not entries:
                menu.addAction(str(err or _tr("No versions"))).setEnabled(False)
                return
            seen = set()
            v = self.view or _view(self.win)
            for e in entries:
                ver = e.get("version", "")
                if ver in seen or not R._platform_ok(e, R.target_platform()):
                    continue
                seen.add(ver)
                ok = R.engine_compatible((e.get("engines") or {}).get("vscode", ""))
                a = menu.addAction(ver + ("" if ok else "  (" + _tr("needs VS Code") + " " +
                                          (e.get("engines") or {}).get("vscode", "") + ")"))
                a.triggered.connect(lambda _c=False, ver=ver, ok=ok: v and v.install(self.eid, ver, not ok))
                if len(seen) >= 40:
                    break
        run_bg(lambda: R.all_versions(self.eid), done)

    def _show_local(self, inst: P.Extension) -> None:
        if inst.path:
            self.readme.setSearchPaths([str(inst.path)])
            self.changelog.setSearchPaths([str(inst.path)])
        self._set_md(self.readme, inst.readme() or inst.description)
        self._set_md(self.changelog, inst.changelog() or _tr("No changelog."))
        self.manifest = inst.package_json
        self._fill_contrib(inst.contributes, inst.has_code, inst.activation_events)
        self._fill_deps(inst.extension_dependencies, inst.extension_pack)

    def _fetch_remote(self, load_docs: bool) -> None:
        eid = self.eid

        def work():
            ns, name = R.split_id(eid)
            d = self.entry if self.entry.get("files", {}).get("manifest") else R.details(ns, name)
            files = d.get("files") or {}
            out = {"entry": d}
            if load_docs:
                out["readme"] = R.text(files.get("readme", "")) if files.get("readme") else ""
                out["changelog"] = R.text(files.get("changelog", "")) if files.get("changelog") else ""
                try:
                    out["manifest"] = R.get_json(files["manifest"]) if files.get("manifest") else {}
                except R.RegistryError:
                    out["manifest"] = {}
            return out

        def done(res, err):
            try:
                if err:
                    if load_docs:
                        self.readme.setPlainText(_tr("Could not load the details") + f": {err}")
                    return
                self.entry = res["entry"]
                self._header()
                if load_docs:
                    self._set_md(self.readme, res.get("readme") or self.entry.get("description", ""))
                    self._set_md(self.changelog, res.get("changelog") or _tr("No changelog."))
                    man = res.get("manifest") or {}
                    self.manifest = man
                    nls_free = P.localize(man, {})
                    self._fill_contrib(nls_free.get("contributes") or {}, bool(man.get("main") or man.get("browser")),
                                       man.get("activationEvents") or [])
                    deps = [f"{x.get('namespace')}.{x.get('extension')}".lower()
                            for x in self.entry.get("dependencies") or [] if isinstance(x, dict)]
                    pack = [f"{x.get('namespace')}.{x.get('extension')}".lower()
                            for x in self.entry.get("bundledExtensions") or [] if isinstance(x, dict)]
                    self._fill_deps(deps or P._ids(man.get("extensionDependencies")),
                                    pack or P._ids(man.get("extensionPack")))
                self._build_actions()
                self._prefetch_images(res.get("readme") or "")
            except RuntimeError:
                pass
        run_bg(work, done)

    def _set_md(self, browser: QTextBrowser, text: str) -> None:
        text = re.sub(r"<img\s[^>]*>", "", text or "", flags=re.I)        # raw HTML badges
        text = re.sub(r"!\[([^\]]*)\]\((https?://[^)]+)\)", lambda m: self._img(m), text)
        browser.setMarkdown(text)

    def _img(self, m) -> str:
        url = m.group(2)
        cf = R._cache_file(url, "images")
        if cf.is_file() and cf.stat().st_size and not url.lower().endswith(".svg"):
            return f"![{m.group(1)}]({QUrl.fromLocalFile(str(cf)).toString()})"
        return ""            # remote / svg images are left out (badges)

    def _prefetch_images(self, md: str) -> None:
        urls = [u for u in re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", md or "")
                if not u.lower().endswith(".svg") and "shields.io" not in u and "badge" not in u.lower()][:8]
        missing = [u for u in urls if not R._cache_file(u, "images").is_file()]
        if not missing:
            return

        def work():
            for u in missing:
                try:
                    R.binary(u, kind="images")
                except R.RegistryError:
                    pass
            return md

        def done(_r, _e):
            try:
                if vsx.get(self.eid) is None:
                    self._set_md(self.readme, md)
            except RuntimeError:
                pass
        run_bg(work, done)

    def _fill_contrib(self, contributes: dict, has_code: bool, activation: list) -> None:
        self.contrib.clear()
        ok_c = theme.current().get("success", "#087F23")
        bad_c = theme.current().get("error", "#C42B1C")
        for _key, label, ok, note in M.support_summary(contributes=contributes, has_code=has_code):
            m = re.match(r"^(.*) \((\d+)\)$", label)
            label = f"{_tr(m.group(1))} ({m.group(2)})" if m else _tr(label)
            it = QTreeWidgetItem([label, "✔ " + _tr("Supported") if ok else "✖ " + _tr("Not supported"),
                                  _tr(note) if note else ""])
            it.setForeground(1, QColor(ok_c if ok else bad_c))
            self.contrib.addTopLevelItem(it)
        if activation and has_code:
            it = QTreeWidgetItem([_tr("Activation events"), "", ", ".join(map(str, activation[:12]))])
            self.contrib.addTopLevelItem(it)
        if not self.contrib.topLevelItemCount():
            self.contrib.addTopLevelItem(QTreeWidgetItem([_tr("No contributions"), "", ""]))
        for i in range(3):
            self.contrib.resizeColumnToContents(i)

    def _fill_deps(self, deps: list, pack: list) -> None:
        self.deps.clear()
        for kind, ids in ((_tr("Dependency"), deps), (_tr("Extension pack"), pack)):
            for i in ids:
                inst = vsx.get(i)
                self.deps.addTopLevelItem(QTreeWidgetItem([i, kind, (_tr("Installed") + f" {inst.version}")
                                                           if inst else _tr("Not installed")]))
        if not self.deps.topLevelItemCount():
            self.deps.addTopLevelItem(QTreeWidgetItem([_tr("No dependencies"), "", ""]))
        self.deps.resizeColumnToContents(0)


# ============================================================================ installation
def _view(win) -> ExtensionsView | None:
    return getattr(win, "vsx_view", None)


def _dock(win) -> QDockWidget:
    dock = getattr(win, "dock_vsx", None)
    if dock is None:
        dock = QDockWidget("Extensions", win)
        dock.setObjectName("dock_vsx_extensions")
        view = ExtensionsView(win)
        win.vsx_view = view
        dock.setWidget(view)
        win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        dock.hide()
        win.dock_vsx = dock
    return dock


def show_view(win) -> None:
    dock = _dock(win)
    wb = getattr(win, "workbench", None)
    if wb is not None:
        try:
            wb.reveal_view("extensions")
        except Exception:  # noqa: BLE001
            pass
    dock.show()
    dock.raise_()
    view = _view(win)
    if view is not None:
        view.search.setFocus()


def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == title and a.menu() is not None:
            return a.menu()
    return None


def install(win) -> None:
    if os.environ.get("RADIDE_NO_VSX"):
        return
    vsx.init_gui()
    act = QAction("E&xtensions (VS Code)", win)
    act.setShortcut(QKeySequence("Ctrl+Shift+X"))
    act.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    act.setStatusTip("Browse and install VS Code extensions from Open VSX")
    act.triggered.connect(lambda: show_view(win))
    win.a_vsx_extensions = act
    view_menu = _menu(win, "View")
    if view_menu is not None:
        view_menu.addAction(act)
    tools = _menu(win, "Tools")
    tact = QAction("VS Code Extensions (Open VSX)...", win)
    tact.triggered.connect(lambda: show_view(win))
    vact = QAction("Install Extension from VSIX...", win)
    vact.triggered.connect(lambda: (_dock(win), _view(win).install_from_vsix()))
    win.a_vsx_install_vsix = vact
    if tools is not None:
        anchor = getattr(win, "a_extensions", None)
        acts = tools.actions()
        nxt = None
        if anchor in acts and acts.index(anchor) + 1 < len(acts):
            nxt = acts[acts.index(anchor) + 1]
        if nxt is not None:
            tools.insertAction(nxt, tact)
            tools.insertAction(nxt, vact)
        else:
            tools.addAction(tact)
            tools.addAction(vact)
    win.addAction(act)
    try:
        from . import workbench
        workbench.register_view("extensions", "Extensions", icon="puzzle", factory=lambda w: _dock(w),
                                modes=("vscode", "agent"), area="side", order=52,
                                tooltip="Extensions (Ctrl+Shift+X)")
    except Exception as ex:  # noqa: BLE001
        win.log(f"[vsx] workbench view: {ex}")
    try:
        from . import command_palette as cp
        cp.register_command("vsx.show", "Extensions: Show Extensions", lambda: show_view(win), "Extensions",
                            "Ctrl+Shift+X")
        cp.register_command("vsx.installVsix", "Extensions: Install from VSIX...", vact.trigger, "Extensions")
        cp.register_command("vsx.checkUpdates", "Extensions: Check for Extension Updates",
                            lambda: (show_view(win), _view(win).check_updates(show=True)), "Extensions")
        cp.register_command("vsx.updateAll", "Extensions: Update All Extensions",
                            lambda: (_dock(win), _view(win).update_all()), "Extensions")
    except Exception as ex:  # noqa: BLE001
        win.log(f"[vsx] commands: {ex}")
    threading.Thread(target=P.clean_trash, daemon=True).start()


__all__ = ["ExtensionsView", "DetailsPage", "install", "show_view", "open_details", "run_bg"]
