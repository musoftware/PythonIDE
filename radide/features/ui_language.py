"""The IDE's display language: Tools > Options > Environment > Language and Tools > Language.

English or العربية (Arabic, right-to-left).  The switch is live: menus, tool bars, docked
windows, dialogs and the Start Page are translated at once (radide/i18n), the layout turns
right-to-left while code editors and the form designer stay left-to-right, and switching back
to English restores every original text.  The choice is saved in "options/ui_language".
"""
from __future__ import annotations

from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QApplication, QComboBox, QMessageBox

from .. import i18n


def current(win) -> str:
    return i18n.saved_language(win.settings)


def language_combo(win) -> QComboBox:
    """The Language box of Tools > Options > Environment (its items are never translated)."""
    box = QComboBox()
    box.setProperty("i18n_skip", True)
    for code, name in i18n.available():
        box.addItem(name, code)
    box.setCurrentIndex(max(0, box.findData(current(win))))
    box.setToolTip("The language of the IDE's menus, windows and dialogs. "
                   "Your code and your forms are not changed.")
    return box


def apply_language(win, lang: str, notify: bool = True) -> None:
    """Save and apply a display language (live)."""
    lang = lang if lang in dict(i18n.LANGUAGES) else "en"
    old = current(win)
    win.settings.setValue(i18n.SETTING, lang)
    win.settings.sync()
    app = QApplication.instance()
    if lang == i18n.language() and lang == old:
        return
    i18n.set_language(app, lang)
    _sync_menu(win)
    try:
        win.statusBar().showMessage(f"Display language: {dict(i18n.LANGUAGES)[lang]}", 5000)
    except Exception:  # noqa: BLE001
        pass
    if notify and lang != old:
        QMessageBox.information(
            win, "Language",
            "The display language was changed. Windows that are already open were translated; "
            "a few texts are updated the next time the IDE starts.")


def _sync_menu(win) -> None:
    for a in getattr(win, "_ui_lang_actions", []):
        a.setChecked(a.data() == i18n.language())


def _add_menu(win) -> None:
    tools = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Tools"), None)
    if tools is None:
        return
    m = tools.addMenu("&Language")
    m.menuAction().setObjectName("ui_language_menu")
    group = QActionGroup(m)
    win._ui_lang_actions = []
    for code, name in i18n.available():
        a = m.addAction(name)
        a.setData(code)
        a.setCheckable(True)
        a.setObjectName(f"ui_language_{code}")
        group.addAction(a)
        a.triggered.connect(lambda _=False, c=code: apply_language(win, c))
        win._ui_lang_actions.append(a)
    _sync_menu(win)


def _mark_user_content(win) -> None:
    """Lists that show identifiers or the user's data keep their items in English."""
    for name in ("locals", "callstack", "toolbox", "properties", "solution_props"):
        w = getattr(win, name, None)
        if w is not None:
            try:
                w.setProperty("i18n_skip_items", True)
            except RuntimeError:
                pass


def install(win) -> None:
    _mark_user_content(win)
    _add_menu(win)
    lang = current(win)
    if lang != "en":
        i18n.set_language(QApplication.instance(), lang)
        _sync_menu(win)


__all__ = ["apply_language", "language_combo", "current"]
