"""The one-time safety / legal notice of the ECU tools (shown once per user; acceptance kept in QSettings
under SETTINGS_KEY, shared by every firmware feature - the ECU project and the ECU workbench)."""
from __future__ import annotations

SETTINGS_KEY = "firmware/safetyNoticeAccepted"
TITLE = "Vehicle software notice"
TEXT = ("Edits to vehicle / control-unit software can affect safety, warranty and emissions legality.\n\n"
        "- Always keep the original file (RAD IDE keeps it read-only in the project).\n"
        "- Only work on units you own or are authorised to service.\n"
        "- Follow the laws of your country (road-worthiness, emissions and type approval).\n\n"
        "RAD IDE provides general analysis and calibration editing tools. It has no immobiliser, emissions-"
        "system or odometer functions.")
ACCEPT = "I understand"


def _settings():
    from PyQt6.QtCore import QCoreApplication, QSettings
    org = QCoreApplication.organizationName() or "RADIDE"
    return QSettings(org, QCoreApplication.applicationName() or org)


def accepted() -> bool:
    try:
        v = _settings().value(SETTINGS_KEY, False)
    except Exception:  # noqa: BLE001 - no Qt: treat as not accepted
        return False
    return v in (True, "true", "1", 1)


_LISTENERS: list = []          # weak references to "hide your notice bar" callbacks (one notice for every view)


def on_accepted(widget) -> None:
    """Hide *widget* (a notice bar) as soon as the notice is accepted anywhere (modal dialog or another bar)."""
    import weakref
    _LISTENERS.append(weakref.ref(widget))


def set_accepted(value: bool = True) -> None:
    try:
        _settings().setValue(SETTINGS_KEY, bool(value))
    except Exception:  # noqa: BLE001
        pass
    if not value:
        return
    for ref in list(_LISTENERS):
        w = ref()
        try:
            if w is not None:
                w.setVisible(False)
        except RuntimeError:            # the Qt widget is gone
            w = None
        if w is None:
            _LISTENERS.remove(ref)


def ensure_accepted(parent=None, tr=None) -> bool:
    """Show the notice once (modal); returns True when the user has accepted it (now or before)."""
    if accepted():
        return True
    from PyQt6.QtWidgets import QMessageBox
    t = tr or (lambda s: s)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(t(TITLE))
    box.setText(t(TEXT))
    ok = box.addButton(t(ACCEPT), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(ok)
    box.setObjectName("firmwareSafetyNotice")
    box.exec()
    if box.clickedButton() is ok:
        set_accepted(True)
        return True
    return False


__all__ = ["SETTINGS_KEY", "TITLE", "TEXT", "ACCEPT", "accepted", "set_accepted", "ensure_accepted",
           "on_accepted"]
