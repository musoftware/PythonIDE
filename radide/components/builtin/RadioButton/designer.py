"""RadioButton on the design surface (not auto-exclusive: each one shows its own Checked value)."""
from PyQt6.QtWidgets import QRadioButton

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    w = prepare(QRadioButton(parent))
    w.setAutoExclusive(False)
    return w


def apply(w, props, ctx):
    apply_classic(w, props, ctx)
