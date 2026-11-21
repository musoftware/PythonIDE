"""ReportViewer - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ReportViewer;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, used, out, native, ev = g.p, g.n, g.master, g.used, g.out, g.native, g.ev
    rf = str(p.get("ReportFile") or "")
    out.append(f"self.{n} = _TkReportViewer({master}, ReportFile={f'self._res({rf!r})' if rf else repr('')}, "
               f"Zoom={int(p.get('Zoom') or 100)}, ShowToolbar={bool(p.get('ShowToolbar', True))}, "
               f"AutoLoad={bool(p.get('AutoLoad', True))})")
    if "PageChanged" in used:
        out.append(f"self.{n}.on_page_changed = {ev('PageChanged')}")
    native.add("PageChanged")
