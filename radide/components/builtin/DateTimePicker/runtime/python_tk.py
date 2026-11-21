"""DateTimePicker - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every DateTimePicker;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, out, native, opts, ev, _colors = g.p, g.n, g.master, g.out, g.native, g.opts, g.ev, g.colors
    opts += [f"fmt={p.get('Format', 'Short')!r}", f"on_change={ev('ValueChanged')}"] + _colors(p)
    out.append(f"self.{n} = _DatePicker({master}, {str(p.get('Value') or '')!r}, {', '.join(opts)})")
    native.add("ValueChanged")
