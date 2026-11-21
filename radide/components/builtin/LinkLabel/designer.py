"""LinkLabel on the design surface: underlined text in LinkColor."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QLabel(parent))


def text_label(w, p, ctx):
    w.setText(str(p.get("Text", "")))
    w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


def _rules(p):
    return [f"color:{p.get('LinkColor') or '#0066CC'}; text-decoration:underline;"]


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=text_label, rules=_rules)
