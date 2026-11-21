"""Panel - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every Panel;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, _colors = g.p, g.n, g.master, g.out, g.colors
    out.append(f"self.{n} = tk.Frame({master}, {', '.join(_colors(p, fg=False) or ['bd=0'])})")
