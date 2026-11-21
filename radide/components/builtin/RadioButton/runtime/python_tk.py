"""RadioButton - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every RadioButton;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native, opts, ev, _colors = g.p, g.n, g.master, g.out, g.native, g.opts, g.ev, g.colors
    opts += [f"text={p['Text']!r}", "variable=self._radio", f"value={n!r}",
             "anchor=\"w\"", f"command={ev('CheckedChanged')}"] + _colors(p)
    out.append(f"self.{n} = tk.Radiobutton({master}, {', '.join(opts)})")
    if p["Checked"]:
        out.append(f"self._radio.set({n!r})")
    native.add("CheckedChanged")
