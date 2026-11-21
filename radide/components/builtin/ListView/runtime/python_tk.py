"""ListView - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ListView;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native = g.p, g.n, g.master, g.out, g.native
    ev, _font, split_items, split_rows = g.ev, g.font, g.split_items, g.split_rows
    out.append(f"self.{n} = _ListView({master}, {split_items(p.get('Columns'))!r}, "
               f"{split_rows(p.get('Items'))!r}, view={p.get('View', 'Details')!r}, font={_font(p)})")
    out.append(f"self.{n}.bind(\"<<TreeviewSelect>>\", {ev('SelectedIndexChanged')})")
    native.add("SelectedIndexChanged")
