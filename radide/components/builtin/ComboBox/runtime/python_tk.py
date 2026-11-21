"""ComboBox - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every ComboBox;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, used, out = g.p, g.n, g.master, g.used, g.out
    native, opts, ev, split_items = g.native, g.opts, g.ev, g.split_items
    items = split_items(p["Items"])
    state = "readonly" if p.get("DropDownStyle", "DropDownList") == "DropDownList" else "normal"
    out.append(f"self.{n}_var = tk.StringVar()")
    opts += [f"values={items!r}", f"state={state!r}", f"textvariable=self.{n}_var"]
    out.append(f"self.{n} = ttk.Combobox({master}, {', '.join(opts)})")
    out.append(f"self.{n}.bind(\"<<ComboboxSelected>>\", {ev('SelectedIndexChanged')})")
    if "TextChanged" in used:
        out.append(f"self.{n}_var.trace_add(\"write\", {ev('TextChanged')})")
    native |= {"SelectedIndexChanged", "TextChanged"}
