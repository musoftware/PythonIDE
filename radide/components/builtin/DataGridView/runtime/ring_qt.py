"""DataGridView - ring-qt (RingQt) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    q, p, n, t, out = g.q, g.p, g.n, g.t, g.out
    split_items, split_rows = g.split_items, g.split_rows
    cols = split_items(p.get("Columns", ""))
    rows = split_rows(p.get("Items" if t == "ListView" else "Rows", ""))
    if t == "ListView" and p.get("View") == "List":
        cols, rows = cols[:1] or [""], [r[:1] for r in rows]
        out.append(f"{n}.horizontalHeader().hide()")
    out += [f"{n}.setColumnCount({max([len(cols)] + [len(r) for r in rows])})",
            f"{n}.setRowCount({len(rows)})"]
    out += [f"{n}.setHorizontalHeaderItem({i}, new qTableWidgetItem({q(col)}))"
            for i, col in enumerate(cols)]
    out += [f"{n}.setItem({r}, {k}, new qTableWidgetItem({q(cell)}))"
            for r, row in enumerate(rows) for k, cell in enumerate(row)]
    out.append(f"{n}.horizontalHeader().setStretchLastSection(true)")
    if t == "ListView":
        out += [f"{n}.verticalHeader().hide()", f"{n}.setShowGrid(false)",
                f"{n}.setEditTriggers(0)", f"{n}.setSelectionBehavior(1)    # SelectRows",
                f"{n}.setSelectionMode(1)    # SingleSelection"]
    elif p.get("ReadOnly"):
        out.append(f"{n}.setEditTriggers(0)")
