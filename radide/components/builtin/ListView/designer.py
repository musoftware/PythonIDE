"""ListView on the design surface: Columns and Items (rows "a|b;c|d"), Details or List view."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from radide.components.classic import apply_classic, prepare
from radide.controls import split_items, split_rows


def create(parent, props, ctx):
    w = QTreeWidget(parent)
    w.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return prepare(w)


def _items(w, p, ctx):
    w.clear()
    cols = split_items(p.get("Columns", "")) or ["Column1"]
    details = p.get("View", "Details") == "Details"
    w.setColumnCount(len(cols) if details else 1)
    w.setHeaderLabels(cols if details else cols[:1])
    w.setHeaderHidden(not details)
    w.setRootIsDecorated(False)
    for row in split_rows(p.get("Items", "")):
        w.addTopLevelItem(QTreeWidgetItem(row if details else row[:1]))


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_items)
