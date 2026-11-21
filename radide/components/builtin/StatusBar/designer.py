"""StatusBar on the design surface: a sunken bar with the text on the left."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QLabel(parent))


def _text(w, p, ctx):
    w.setText(str(p.get("Text", "")))
    w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


def _rules(p):
    return ["border:1px solid #A0A0A0; border-top-color:#808080; padding-left:4px;"
            + ("" if p.get("BackColor") else "background-color:#ECE9D8;")]


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_text, rules=_rules)
