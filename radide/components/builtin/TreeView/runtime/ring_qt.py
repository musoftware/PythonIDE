"""TreeView - ring-qt (RingQt) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    q, p, n, out, tree_paths = g.q, g.p, g.n, g.out, g.tree_paths
    out.append(f"{n}.setHeaderHidden(true)")
    var: dict[str, str] = {}
    for k, (path, text) in enumerate(tree_paths(p.get("Nodes", "")), 1):
        v = var[path] = f"oNode{k}"
        parent = var.get(path.rpartition("/")[0])
        out += [f"{v} = new qTreeWidgetItem()", f"{v}.setText(0, {q(text)})",
                f"{parent}.addChild({v})" if parent else f"{n}.addTopLevelItem({v})"]
    if var:
        out.append(f"{n}.expandAll()")
