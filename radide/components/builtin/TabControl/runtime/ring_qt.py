"""TabControl - ring-qt (RingQt) code generation: the content of the control (the generator writes its
construction, geometry, font, colours and events, then calls ``emit(g)``; see
radide/components/codegen.py ``builtin_emit``). ``g.out`` is the list of lines to append to.
"""


def emit(g):
    q, p, n, out, pages = g.q, g.p, g.n, g.out, g.pages
    c = g.c
    for i, title in enumerate(pages(c)):
        out += [f"{n}_Page{i} = new qWidget()", f"{n}.addTab({n}_Page{i}, {q(title)})"]
    idx = int(p.get("SelectedIndex") or 0)
    if 0 < idx < len(pages(c)):
        out.append(f"{n}.setCurrentIndex({idx})")
