"""TreeView - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every TreeView;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native, ev, _font, tree_paths = g.p, g.n, g.master, g.out, g.native, g.ev, g.font, g.tree_paths
    out.append(f"self.{n} = _TreeView({master}, {[path for path, _ in tree_paths(p.get('Nodes'))]!r}, "
               f"font={_font(p)})")
    out.append(f"self.{n}.bind(\"<<TreeviewSelect>>\", {ev('SelectedIndexChanged')})")
    native.add("SelectedIndexChanged")
