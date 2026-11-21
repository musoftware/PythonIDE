"""TextBox - python-tk code generation (the IDE's Tkinter generator calls ``emit(g)`` for every TextBox;
see radide/components/codegen.py ``builtin_emit``).

``g``: p (properties), n (name), master (parent expression), used (events with a handler), out (lines
to append to), native (events this code wires), opts (Tk options, starts with the font), ev(event) (handler
callback expression), align, font(p), colors(p, fg=True), ANCHOR, JUSTIFY, split_items, split_rows,
tree_paths.
"""


def emit(g):
    p, n, master, used, out, native = g.p, g.n, g.master, g.used, g.out, g.native
    opts, ev, align, _colors, JUSTIFY = g.opts, g.ev, g.align, g.colors, g.JUSTIFY
    if p.get("Multiline"):
        opts += ["wrap=\"word\"", "undo=True"] + _colors(p)
        out.append(f"self.{n} = tk.Text({master}, {', '.join(opts)})")
        out.append(f"self.{n}.insert(\"1.0\", {p['Text']!r})")
        out.append(f"self.{n}.edit_modified(False)")
        if "TextChanged" in used:
            out.append(f"self.{n}.bind(\"<<Modified>>\", lambda _e: (self.{n}.edit_modified(False), "
                       f"{ev('TextChanged')}()))")
        native.add("TextChanged")
        if p.get("ReadOnly"):
            out.append(f"self.{n}.configure(state=\"disabled\")")
    else:
        out.append(f"self.{n}_var = tk.StringVar(value={p['Text']!r})")
        opts += [f"textvariable=self.{n}_var", f"justify={JUSTIFY[align]!r}"] + _colors(p)
        if p.get("PasswordChar"):
            opts.append(f"show={str(p['PasswordChar'])[:1]!r}")
        if p.get("ReadOnly"):
            opts.append("state=\"readonly\"")
        out.append(f"self.{n} = tk.Entry({master}, {', '.join(opts)})")
        if int(p.get("MaxLength") or 0) > 0:
            m = int(p["MaxLength"])
            out.append(f"self.{n}_var.trace_add(\"write\", lambda *_: len(self.{n}_var.get()) > {m} "
                       f"and self.{n}_var.set(self.{n}_var.get()[:{m}]))")
        if "TextChanged" in used:
            out.append(f"self.{n}_var.trace_add(\"write\", {ev('TextChanged')})")
        native.add("TextChanged")
