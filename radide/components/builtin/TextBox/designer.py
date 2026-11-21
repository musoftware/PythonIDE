"""TextBox on the design surface: a QLineEdit, or a QPlainTextEdit when Multiline (a Multiline change rebuilds
the preview: "rebuildPreview" in component.json)."""
from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QPlainTextEdit(parent) if props.get("Multiline") else QLineEdit(parent))


def apply(w, props, ctx):
    apply_classic(w, props, ctx)
