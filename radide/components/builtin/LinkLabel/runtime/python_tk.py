"""LinkLabel - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every LinkLabel;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native, opts, ev, _colors = g.p, g.n, g.master, g.out, g.native, g.opts, g.ev, g.colors
    style = " ".join(s for s, on in (("bold", p.get("FontBold")), ("italic", p.get("FontItalic")),
                                     ("underline", True)) if on)
    font = f"({(p.get('FontName') or 'Segoe UI')!r}, {int(p.get('FontSize', 9))}, {style!r})"
    opts = [f"font={font}", f"text={p['Text']!r}", "anchor=\"w\"", "cursor=\"hand2\"",
            f"fg=\"{p.get('LinkColor') or '#0066CC'}\""] + _colors(p, fg=False)
    out.append(f"self.{n} = tk.Label({master}, {', '.join(opts)})")
    out.append(f"self.{n}.bind(\"<ButtonRelease-1>\", lambda _e: {ev('Click')}(), add=\"+\")")
    native.add("Click")
