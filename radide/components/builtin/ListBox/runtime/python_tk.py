"""ListBox - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ListBox;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native = g.p, g.n, g.master, g.out, g.native
    opts, ev, _colors, split_items = g.opts, g.ev, g.colors, g.split_items
    opts += ["exportselection=False"] + _colors(p)
    out.append(f"self.{n} = tk.Listbox({master}, {', '.join(opts)})")
    for it in split_items(p["Items"]):
        out.append(f"self.{n}.insert(tk.END, {it!r})")
    out.append(f"self.{n}.bind(\"<<ListboxSelect>>\", {ev('SelectedIndexChanged')})")
    native.add("SelectedIndexChanged")
