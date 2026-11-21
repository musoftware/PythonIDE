"""TabControl - python-qt (PySide6) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    p, n, out, split_items = g.p, g.n, g.out, g.split_items
    pages = split_items(p.get("TabPages", "")) or ["TabPage1"]
    for i, title in enumerate(pages):
        out += [f"self.{n}_Page{i} = QWidget()",
                f"self.{n}.addTab(self.{n}_Page{i}, {title!r})"]
    idx = int(p.get("SelectedIndex") or 0)
    if 0 < idx < len(pages):
        out.append(f"self.{n}.setCurrentIndex({idx})")
