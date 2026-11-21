"""ActiveX - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ActiveX;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, _font = g.p, g.n, g.master, g.out, g.font
    text = f"ActiveX: {p.get('ProgID', '')}" + "\nActiveX controls need the Python (PySide6) language"
    out.append(f"self.{n} = tk.Label({master}, text={text!r}, relief=\"groove\", bg=\"#ffffff\", "
               f"fg=\"#606060\", wraplength={max(40, int(p['Width']) - 8)}, font={_font(p)})")
