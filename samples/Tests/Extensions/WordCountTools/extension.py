"""Word Count Tools - an example RAD IDE extension (see docs/PLUGIN_API.md)."""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel, QMessageBox, QPlainTextEdit

from .counting import count, describe

_state = {}


def activate(api):
    api.add_action("Tools/Word Count", "Count Words in Active File", lambda: _show(api),
                   shortcut="Ctrl+Alt+W", status_tip="Lines, words and characters of the active file")
    api.add_action("Tools/Word Count", "Scratch Notes", lambda: _state["dock"].show())

    notes = QPlainTextEdit()
    notes.setPlaceholderText("Notes kept between sessions (saved by the Word Count Tools extension)")
    notes.setPlainText(str(api.settings.value("notes", "") or ""))
    notes.textChanged.connect(lambda: api.settings.setValue("notes", notes.toPlainText()))
    dock = api.add_dock("Scratch Notes", notes, area="right", object_name="ext_wordcount_notes")
    dock.hide()

    label = QLabel("")
    api.theme.role(label, "muted")              # follows the IDE theme
    label.setAccessibleName("Word count of the active file")
    api.add_status_widget(label)

    timer = QTimer()
    timer.timeout.connect(lambda: _update(api, label))
    timer.start(1500)
    api.on_dispose(timer.stop)
    _state.update(dock=dock, label=label, timer=timer)
    _update(api, label)
    api.log("ready - Tools > Word Count")


def _update(api, label):
    text = api.current_editor_text()
    label.setText("" if text is None else f"{count(text)['words']} words")


def _show(api):
    text = api.current_editor_text()
    if text is None:
        QMessageBox.information(api.win, "Word Count", "Open a code file first.")
        return
    QMessageBox.information(api.win, "Word Count", describe(count(text)))


def deactivate():
    _state.clear()
