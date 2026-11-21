"""ProgressBar - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ProgressBar;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out = g.p, g.n, g.master, g.out
    out.append(f"self.{n} = ttk.Progressbar({master}, maximum={int(p['Maximum'])}, "
               f"value={int(p['Value'])})")
