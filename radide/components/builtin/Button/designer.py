"""Button on the design surface (create the Qt widget, apply the properties - radide/components/classic.py)."""
from PyQt6.QtWidgets import QPushButton

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QPushButton(parent))


def _rules(p):
    align = p.get("TextAlign", "Center")
    return [f"text-align:{align.lower()};"] if align != "Center" else []


def apply(w, props, ctx):
    apply_classic(w, props, ctx, rules=_rules)
