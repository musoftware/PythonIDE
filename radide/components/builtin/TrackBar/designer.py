"""TrackBar on the design surface (a horizontal QSlider)."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSlider

from radide.components.classic import apply_classic, prepare


def create(parent, props, ctx):
    return prepare(QSlider(Qt.Orientation.Horizontal, parent))


def apply(w, props, ctx):
    apply_classic(w, props, ctx)
