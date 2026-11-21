"""Label - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every Label;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, opts = g.p, g.n, g.master, g.out, g.opts
    align, _colors, ANCHOR, JUSTIFY = g.align, g.colors, g.ANCHOR, g.JUSTIFY
    opts += [f"text={p['Text']!r}", f"anchor={ANCHOR[align]!r}",
             f"justify={JUSTIFY[align]!r}"] + _colors(p)
    out.append(f"self.{n} = tk.Label({master}, {', '.join(opts)})")
