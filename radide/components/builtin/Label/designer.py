"""Label on the design surface (create the Qt widget, apply the properties - radide/components/classic.py)."""
from PyQt6.QtWidgets import QLabel

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QLabel(parent))


def apply(w, props, ctx):
    apply_classic(w, props, ctx)
