"""ActiveX on the design surface: a white box showing the ProgID."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QLabel(parent))


def _progid(w, p, ctx):
    w.setText(f"ActiveX\n{p.get('ProgID', '')}")
    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.setWordWrap(True)


def _rules(p):
    return ["border:1px solid #808080; color:#505050;" + ("" if p.get("BackColor") else "background-color:#ffffff;")]


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_progid, rules=_rules)
