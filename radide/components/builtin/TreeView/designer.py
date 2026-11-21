"""TreeView on the design surface: the Nodes ("Root;Root/Child") as an expanded tree."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from radide.components.classic import apply_classic, prepare
from radide.controls import tree_paths


def create(parent, props, ctx):
    w = QTreeWidget(parent)
    w.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return prepare(w)


def _nodes(w, p, ctx):
    w.clear()
    w.setHeaderHidden(True)
    w.setColumnCount(1)
    items = {}
    for path, text in tree_paths(p.get("Nodes", "")):
        parent = items.get(path.rpartition("/")[0])
        it = QTreeWidgetItem([text])
        (parent.addChild(it) if parent is not None else w.addTopLevelItem(it))
        items[path] = it
    if not items:
        w.addTopLevelItem(QTreeWidgetItem([ctx.name]))
    w.expandAll()


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_nodes)
