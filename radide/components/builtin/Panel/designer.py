"""Panel on the design surface: a frame with a dashed design-time outline (like VB)."""
from PyQt6.QtWidgets import QFrame

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QFrame(parent))


def apply(w, props, ctx):
    apply_classic(w, props, ctx, rules=["border:1px dashed #7f7f7f;"])
