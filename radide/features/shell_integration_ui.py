"""Tools > Options > Environment > "Windows integration": file associations, "Open with", Explorer
context menus, Start Menu / Desktop shortcuts (radide/shell_integration.py) and the single-window
setting (radide/single_instance.py)."""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QVBoxLayout)

KEY = "options/shell_"


def _bool(v, default: bool) -> bool:
    if v is None:
        return default
    return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")


def saved_options(win) -> dict:
    from .. import shell_integration as S
    return {k: _bool(win.settings.value(KEY + k), S.DEFAULT_OPTIONS[k]) for k in S.OPTIONS}


def status_text(st: dict) -> str:
    if not st.get("registered"):
        return "Status: not registered."
    if st.get("stale"):
        return "Status: registered for another location - click Register again."
    return f"Status: registered ({st.get('values', 0)} registry values, {len(st.get('files', []))} shortcuts)."


def windows_group(dlg):
    """(QGroupBox, apply_fn) for the Environment page, or None on other systems."""
    win = dlg.win
    box = QGroupBox("Windows integration")
    lay = QVBoxLayout(box)
    single = QCheckBox("Open files in the running RAD IDE window")
    single.setToolTip("Files opened from Explorer go to the RAD IDE window that is already open "
                      "(start with --new-window for a separate window).")
    single.setChecked(_bool(win.settings.value("options/single_instance"), True))
    lay.addWidget(single)
    if sys.platform != "win32":
        def apply_single():
            win.settings.setValue("options/single_instance", single.isChecked())
        return box, apply_single
    from .. import shell_integration as S
    grid = QGridLayout()
    checks: dict[str, QCheckBox] = {}
    opts = saved_options(win)
    st = S.status()
    if st.get("registered"):
        opts.update({k: bool(st["options"].get(k, opts[k])) for k in S.OPTIONS})
    for i, k in enumerate(S.OPTIONS):
        cb = QCheckBox(S.OPTION_LABELS[k])
        cb.setChecked(opts[k])
        checks[k] = cb
        grid.addWidget(cb, i, 0)
    lay.addLayout(grid)
    status = QLabel(status_text(st))
    status.setWordWrap(True)
    lay.addWidget(status)
    row = QHBoxLayout()
    b_reg = QPushButton("Register")
    b_reg.setToolTip("Write the choices above for your Windows user (no administrator rights needed).")
    b_unreg = QPushButton("Unregister")
    b_unreg.setToolTip("Remove everything RAD IDE registered and restore what it replaced.")
    row.addWidget(b_reg)
    row.addWidget(b_unreg)
    row.addStretch(1)
    lay.addLayout(row)
    note = QLabel("Only your own user account is changed; existing default programs of other file types "
                  "are kept (RAD IDE is added to their \"Open with\" list).")
    note.setWordWrap(True)
    try:
        from .. import theme as T
        T.role(note, "muted")
    except Exception:  # noqa: BLE001
        pass
    lay.addWidget(note)

    def choices() -> dict:
        return {k: cb.isChecked() for k, cb in checks.items()}

    def save():
        for k, v in choices().items():
            win.settings.setValue(KEY + k, v)
        win.settings.setValue("options/single_instance", single.isChecked())

    def refresh():
        cur = S.status()
        status.setText(status_text(cur))
        b_unreg.setEnabled(bool(cur.get("registered")))
        return cur

    def do_register():
        save()
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                cur = S.register(choices())
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(dlg, "Windows integration", f"Registration failed:\n{e}")
            refresh()
            return
        refresh()
        win.log(f"[windows] {S.describe(cur)}")
        QMessageBox.information(dlg, "Windows integration", "RAD IDE is registered with Windows.")

    def do_unregister():
        try:
            S.unregister()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(dlg, "Windows integration", f"Unregistration failed:\n{e}")
        refresh()
        win.log("[windows] RAD IDE's Windows integration was removed")

    def apply():
        save()
        cur = S.status()                         # registered with other choices: register them
        if cur.get("registered") and any(bool(cur["options"].get(k)) != v for k, v in choices().items()):
            try:
                S.register(choices())
            except Exception as e:  # noqa: BLE001
                win.log(f"[windows] registration failed: {e}")
        refresh()

    b_reg.clicked.connect(do_register)
    b_unreg.clicked.connect(do_unregister)
    b_unreg.setEnabled(bool(st.get("registered")))
    dlg.shell_checks, dlg.shell_single, dlg.shell_status = checks, single, status
    dlg.shell_register, dlg.shell_unregister = b_reg, b_unreg
    return box, apply


__all__ = ["windows_group", "saved_options", "status_text"]
