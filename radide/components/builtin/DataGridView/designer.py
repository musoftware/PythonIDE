"""DataGridView on the design surface: the Columns headers and the Rows ("a|b;c|d")."""
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from radide.components.classic import apply_classic, prepare
from radide.controls import split_items, split_rows


def create(parent, props, ctx):
    w = QTableWidget(parent)
    w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    w.verticalHeader().setDefaultSectionSize(20)
    return prepare(w)


def _grid(w, p, ctx):
    cols = split_items(p.get("Columns", "")) or ["Column1"]
    rows = split_rows(p.get("Rows", ""))
    w.clear()
    w.setColumnCount(len(cols))
    w.setHorizontalHeaderLabels(cols)
    w.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, cell in enumerate(row[:len(cols)]):
            w.setItem(r, c, QTableWidgetItem(cell))
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_grid)
