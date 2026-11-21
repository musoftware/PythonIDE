"""TabControl - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every TabControl;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, used, out, native, split_items = g.p, g.n, g.master, g.used, g.out, g.native, g.split_items
    pages = split_items(p.get("TabPages", "")) or ["TabPage1"]
    out.append(f"self.{n} = ttk.Notebook({master})")
    out.append(f"self.{n}_pages = []")
    out.append(f"for _text in {pages!r}:")
    out.append(f"    _page = tk.Frame(self.{n}, bd=0, highlightthickness=0"
               + (f", bg=\"{p['BackColor']}\"" if p.get("BackColor") else "") + ")")
    out.append(f"    self.{n}.add(_page, text=_text)")
    out.append(f"    self.{n}_pages.append(_page)")
    sel = int(p.get("SelectedIndex", 0) or 0)
    if 0 < sel < len(pages):
        out.append(f"self.{n}.select({sel})")
    if "SelectedIndexChanged" in used:
        out.append(f"self._bind_tabs(self.{n}, \"{n}_SelectedIndexChanged\")")
    native.add("SelectedIndexChanged")
