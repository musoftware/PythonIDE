"""TreeView - python-qt (PySide6) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    p, n, out, tree_paths = g.p, g.n, g.out, g.tree_paths
    out.append(f"self.{n}.setHeaderHidden(True)")
    nodes = tree_paths(p.get("Nodes", ""))
    if nodes:
        out.append(f"_fill_tree(self.{n}, {nodes!r})")
