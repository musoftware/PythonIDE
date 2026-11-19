"""Menu Editor dialog for the MenuStrip component."""
from __future__ import annotations

import copy
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .properties import valid_identifier

EDITABLE = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)


def _auto_name(path_texts: list[str]) -> str:
    words = "".join(re.sub(r"[^0-9A-Za-z]", "", t.title()) for t in path_texts)
    return "mnu" + (words or "Item")


class MenuEditor(QDialog):
    def __init__(self, items: list, taken_names: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Menu Editor")
        self.resize(520, 420)
        self.taken = {n.lower() for n in taken_names}
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Text", "Name"])
        self.tree.setColumnWidth(0, 220)
        self.tree.itemChanged.connect(self._on_changed)
        self._loading = True
        for it in items:
            self.tree.addTopLevelItem(self._make_item(it))
        self.tree.expandAll()
        self._loading = False

        buttons = [("Add Menu", self.add_top), ("Add Item", self.add_child),
                   ("Add Separator", self.add_separator), ("Delete", self.delete),
                   ("Move Up", lambda: self.move(-1)), ("Move Down", lambda: self.move(1))]
        side = QVBoxLayout()
        for text, slot in buttons:
            b = QPushButton(text)
            b.clicked.connect(slot)
            side.addWidget(b)
        side.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(self.tree, 1)
        row.addLayout(side)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Double-click a cell to edit. Use \"-\" as text for a separator."))
        lay.addLayout(row, 1)
        lay.addWidget(box)

    # ------------------------------------------------------------ items
    def _make_item(self, d: dict) -> QTreeWidgetItem:
        it = QTreeWidgetItem([d.get("Text", ""), d.get("Name", "")])
        it.setFlags(EDITABLE)
        for ch in d.get("Items", []):
            it.addChild(self._make_item(ch))
        return it

    def _path(self, it: QTreeWidgetItem) -> list[str]:
        out = []
        while it is not None:
            out.insert(0, it.text(0))
            it = it.parent()
        return out

    def _names(self, exclude=None) -> set[str]:
        out = set()

        def walk(it):
            if it is not exclude and it.text(1):
                out.add(it.text(1).lower())
            for i in range(it.childCount()):
                walk(it.child(i))
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        return out

    def _unique(self, base: str, exclude=None) -> str:
        used = self._names(exclude) | self.taken
        name, i = base, 2
        while name.lower() in used:
            name, i = f"{base}{i}", i + 1
        return name

    def _new(self, text: str, parent: QTreeWidgetItem | None) -> QTreeWidgetItem:
        self._loading = True
        it = QTreeWidgetItem([text, ""])
        it.setFlags(EDITABLE)
        if parent is None:
            self.tree.addTopLevelItem(it)
        else:
            parent.addChild(it)
            parent.setExpanded(True)
        if text != "-":
            it.setText(1, self._unique(_auto_name(self._path(it)), it))
        self._loading = False
        self.tree.setCurrentItem(it)
        if text != "-":
            self.tree.editItem(it, 0)
        return it

    def add_top(self):
        self._new(f"Menu{self.tree.topLevelItemCount() + 1}", None)

    def add_child(self):
        cur = self.tree.currentItem()
        if cur is None or cur.text(0) == "-":
            cur = cur.parent() if cur is not None else None
        if cur is None:
            return self.add_top()
        self._new(f"Item{cur.childCount() + 1}", cur)

    def add_separator(self):
        cur = self.tree.currentItem()
        if cur is None:
            return
        parent = cur if cur.childCount() or cur.parent() is None else cur.parent()
        self._new("-", parent)

    def delete(self):
        cur = self.tree.currentItem()
        if cur is None:
            return
        (cur.parent() or self.tree.invisibleRootItem()).removeChild(cur)

    def move(self, step: int):
        cur = self.tree.currentItem()
        if cur is None:
            return
        parent = cur.parent() or self.tree.invisibleRootItem()
        i = parent.indexOfChild(cur)
        j = i + step
        if 0 <= j < parent.childCount():
            expanded = cur.isExpanded()
            parent.takeChild(i)
            parent.insertChild(j, cur)
            cur.setExpanded(expanded)
            self.tree.setCurrentItem(cur)

    def _on_changed(self, it: QTreeWidgetItem, col: int):
        if self._loading:
            return
        if col == 0:   # re-derive automatic names when text changes
            self._loading = True
            if it.text(0) == "-":
                it.setText(1, "")
            elif not it.text(1) or it.text(1).startswith("mnu"):
                it.setText(1, self._unique(_auto_name(self._path(it)), it))
            self._loading = False

    # ------------------------------------------------------------ result
    def _collect(self, it: QTreeWidgetItem) -> dict:
        d = {"Text": it.text(0)}
        if it.text(0) != "-":
            d["Name"] = it.text(1)
        kids = [self._collect(it.child(i)) for i in range(it.childCount())]
        if kids:
            d["Items"] = kids
        return d

    def items(self) -> list:
        return [self._collect(self.tree.topLevelItem(i)) for i in range(self.tree.topLevelItemCount())]

    def _accept(self):
        seen = set()

        def check(items):
            for d in items:
                if d["Text"] == "-":
                    continue
                n = d.get("Name", "")
                if not valid_identifier(n) or n.lower() in seen or n.lower() in self.taken:
                    raise ValueError(n)
                seen.add(n.lower())
                check(d.get("Items", []))
        try:
            check(self.items())
        except ValueError as e:
            QMessageBox.warning(self, "Menu Editor", f"Invalid or duplicate item name: '{e}'")
            return
        self.accept()


def edit_menu(items: list, taken: set[str], parent=None) -> list | None:
    dlg = MenuEditor(copy.deepcopy(items), taken, parent)
    return dlg.items() if dlg.exec() else None
