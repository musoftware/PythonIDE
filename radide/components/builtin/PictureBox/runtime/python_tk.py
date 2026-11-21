"""PictureBox - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every PictureBox;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, opts, _colors = g.p, g.n, g.master, g.out, g.opts, g.colors
    opts = _colors(p, fg=False) or ["bd=0"]
    out.append(f"self.{n} = tk.Label({master}, {', '.join(opts)})")
    if p.get("Image"):
        out.append(f"self.{n}_image = tk.PhotoImage(file=self._res({p['Image']!r}))")
        out.append(f"self.{n}.configure(image=self.{n}_image)")
