"""DataGridView - python-qt (PySide6) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    p, n, t, out, split_items = g.p, g.n, g.t, g.out, g.split_items
    split_rows = g.split_rows
    cols = split_items(p.get("Columns", ""))
    rows = split_rows(p.get("Items" if t == "ListView" else "Rows", ""))
    if t == "ListView" and p.get("View") == "List":
        cols, rows = cols[:1] or [""], [r[:1] for r in rows]
        out.append(f"self.{n}.horizontalHeader().hide()")
    out.append(f"_fill_table(self.{n}, {cols!r}, {rows!r})")
    out.append(f"self.{n}.horizontalHeader().setStretchLastSection(True)")
    if t == "ListView":
        out += [f"self.{n}.verticalHeader().hide()",
                f"self.{n}.setShowGrid(False)",
                f"self.{n}.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)",
                f"self.{n}.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)",
                f"self.{n}.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)"]
    elif p.get("ReadOnly"):
        out.append(f"self.{n}.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)")
