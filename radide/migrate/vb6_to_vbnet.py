"""VB6 -> VB.NET Windows Forms (an SDK-style Visual Studio project built with ``dotnet build``).

Like the Visual Basic 2005 Upgrade Wizard: forms become Form1.vb + Form1.Designer.vb (InitializeComponent
generated from the neutral .form model), the VB6 code is re-emitted from the vbparse AST with the VB.NET
changes (Caption -> Text, Value -> Checked/CheckState, AddItem -> Items.Add, event procedures with
sender/e and Handles, control arrays -> arrays of controls + one handler with Handles for every element,
Wend -> End While, Print # -> PrintLine, Open -> FileOpen, Set dropped, explicit ByRef, Type -> Structure,
Property Get/Let -> Property ... End Property).  On Error / GoTo / Resume stay (VB.NET still has them).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..controls import CONTROL_TYPES, menu_names
from ..runtimes import vbparse
from .vbcommon import FormInfo, Notes, ProjectContext, comments_of, event_handler_names, proc_ranges, read_text, \
    strip_suffix, vb_event_to_neutral
from .vb6_to_python import DEFAULT_PROP, Untranslatable, code_part

WF_TYPE = {"Button": "Button", "Label": "Label", "TextBox": "TextBox", "CheckBox": "CheckBox",
           "RadioButton": "RadioButton", "ListBox": "ListBox", "ComboBox": "ComboBox", "GroupBox": "GroupBox",
           "Panel": "Panel", "PictureBox": "PictureBox", "ProgressBar": "ProgressBar",
           "NumericUpDown": "NumericUpDown", "TrackBar": "TrackBar", "Timer": "Timer", "TabControl": "TabControl",
           "DateTimePicker": "DateTimePicker", "LinkLabel": "LinkLabel", "MenuStrip": "MenuStrip",
           "TreeView": "TreeView", "ListView": "ListView", "DataGridView": "DataGridView", "StatusBar": "Label",
           "ActiveX": "Panel", "ToolStrip": "ToolStrip"}
WF_EVENT_ARGS = {"KeyPress": "KeyPressEventArgs", "KeyDown": "KeyEventArgs", "KeyUp": "KeyEventArgs",
                 "MouseDown": "MouseEventArgs", "MouseUp": "MouseEventArgs", "MouseMove": "MouseEventArgs",
                 "FormClosing": "FormClosingEventArgs", "FormClosed": "FormClosedEventArgs"}
VB_TYPE = {"integer": "Integer", "long": "Integer", "byte": "Byte", "single": "Single", "double": "Double",
           "currency": "Decimal", "decimal": "Decimal", "string": "String", "boolean": "Boolean", "date": "Date",
           "variant": "Object", "object": "Object", "collection": "Collection", "longlong": "Long",
           "longptr": "IntPtr"}
FUNC_MAP = {"left": "Strings.Left", "right": "Strings.Right", "date": "Today", "time": "TimeOfDay",
            "timer": "DateAndTime.Timer", "doevents": "Application.DoEvents", "sqr": "Math.Sqrt",
            "atn": "Math.Atan", "sgn": "Math.Sign", "log": "Math.Log", "exp": "Math.Exp", "sin": "Math.Sin",
            "cos": "Math.Cos", "tan": "Math.Tan", "abs": "Math.Abs", "rnd": "Rnd", "len": "Len"}
NAME_MAP = {"vbchecked": "1", "vbunchecked": "0", "vbgrayed": "2", "vbmodal": "True", "vbmodeless": "False"}


def vbstr(s: str) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def vb_type(typ: str) -> str:
    t = (typ or "variant").lower()
    if t.startswith("new:"):
        return "New " + _cls(t[4:])
    if t.startswith("string*"):
        return "String"
    return VB_TYPE.get(t, _cls(t))


def _cls(t: str) -> str:
    return t[:1].upper() + t[1:] if t else "Object"


class VBNetTranslator:
    def __init__(self, ctx: ProjectContext, file: str, text: str, notes: Notes, form: FormInfo | None = None,
                 kind: str = "frm"):
        self.ctx, self.file, self.text, self.notes, self.form, self.kind = ctx, file, text, notes, form, kind
        self.comments = comments_of(text)
        self.done: set[int] = set()
        self.locals: dict = {}
        self.fields: dict = {}
        self.procs: dict = {}
        self.with_stack: list = []
        self.proc = None
        self.proc_start = 0
        self.alias: dict = {}
        self.lines_src = text.replace("\r\n", "\n").split("\n")
        self.ranges = proc_ranges(text)
        self.decl_lines: list = []

    def note(self, level, line, text):
        self.notes.add(level, self.file, line, text)

    def spell(self, low, raw="") -> str:
        return strip_suffix(raw) if raw else self.ctx.spell(low)

    # ------------------------------------------------------------------ comments
    def comments_before(self, line):
        out = []
        for ln in sorted(k for k in self.comments if k < line and k not in self.done):
            if ln >= self.proc_start:
                t, whole = self.comments[ln]
                if whole:
                    out.append(f"'{(' ' + t) if t else ''}")
                self.done.add(ln)
        return out

    def trailing(self, line):
        c = self.comments.get(line)
        if c and not c[1] and line not in self.done:
            self.done.add(line)
            return f"  ' {c[0]}"
        return ""

    # ------------------------------------------------------------------ names
    def ctl(self, low):
        return self.form.controls.get(low) if self.form else None

    def arr(self, low):
        return self.form.arrays.get(low) if self.form else None

    def name(self, low, raw=""):
        if low in self.alias:
            return self.alias[low]
        if self.proc is not None and low == self.proc.name.split(":")[-1] and self.proc.kind in ("function", "get"):
            return self.spell(low, raw)
        if low in self.locals:
            return self.locals[low]
        c = self.ctl(low)
        if c is not None:
            return c.name
        if low in NAME_MAP:
            return NAME_MAP[low]
        return self.spell(low, raw)

    # ------------------------------------------------------------------ expressions
    def ex(self, n) -> str:
        k = n[0]
        if k == "num":
            v = n[2]
            return repr(v) if isinstance(v, float) else str(v)
        if k == "str":
            return vbstr(n[2])
        if k == "bool":
            return "True" if n[2] else "False"
        if k == "nothing":
            return "Nothing"
        if k == "empty":
            return "Nothing"
        if k == "date":
            return f"#{n[2]}#"
        if k == "paren":
            return f"({self.ex(n[2])})"
        if k == "me":
            return "Me"
        if k == "name":
            low = n[2]
            c = self.ctl(low)
            if c is not None and low not in self.locals:
                prop = DEFAULT_PROP.get(c.type)
                return self.prop_get(c.name, c.type, prop or "text", n[1])
            if low in FUNC_MAP and low in ("date", "time", "timer", "doevents"):
                return FUNC_MAP[low] + ("()" if low == "doevents" else "")
            if low == "now":
                return "Now"
            if low == "freefile":
                return "FreeFile()"
            return self.name(low, n[3] if len(n) > 3 else "")
        if k == "member":
            return self.member(n)
        if k == "call":
            return self.call(n)
        if k == "binop":
            op = n[2]
            a, b = self.ex(n[3]), self.ex(n[4])
            vop = {"mod": "Mod", "and": "And", "or": "Or", "xor": "Xor", "like": "Like", "is": "Is",
                   "eqv": "=", "imp": "Or"}.get(op, op)
            if op == "imp":
                return f"(Not ({a}) Or ({b}))"
            return f"{a} {vop} {b}"
        if k == "unop":
            return f"-{self.ex(n[3])}" if n[2] == "-" else f"Not {self.ex(n[3])}"
        if k == "new":
            return f"New {_cls(n[2].split('.')[-1])}()"
        if k == "typeof":
            return f"TypeOf {self.ex(n[2])} Is {_cls(n[3])}"
        if k == "withobj":
            return ""
        if k == "missing":
            return ""
        if k == "named":
            return f"{self.spell(n[2])}:={self.ex(n[3])}"
        raise Untranslatable(f"expression {k}")

    def prop_get(self, name, t, prop, line) -> str:
        p = prop.lower()
        if p == "simpletext" and t == "Label":
            p = "text"
        if p in ("caption", "text"):
            return f"{name}.Text"
        if p == "value":
            if t == "CheckBox":
                return f"CInt({name}.CheckState)"
            if t == "RadioButton":
                return f"{name}.Checked"
            return f"{name}.Value"
        if p == "listcount":
            return f"{name}.Items.Count"
        if p == "listindex":
            return f"{name}.SelectedIndex"
        if p in ("left", "top", "width", "height"):
            self.note("approx", line, f"{name}.{prop.capitalize()}: VB6 twips -> pixels * 15")
            return f"({name}.{prop.capitalize()} * 15)"
        if p == "tag":
            return f"{name}.Tag"
        if p == "tooltiptext":
            raise Untranslatable("ToolTipText (use a ToolTip component)")
        return f"{name}.{self.ctx.spell(p)}"

    def prop_set(self, name, t, prop, v, line) -> str:
        p = prop.lower()
        if p == "simpletext" and t == "Label":
            p = "text"
        if p in ("caption", "text"):
            return f"{name}.Text = {v}"
        if p == "value":
            if t == "CheckBox":
                return f"{name}.CheckState = CType({v}, CheckState)"
            if t == "RadioButton":
                return f"{name}.Checked = {v}"
            if t == "Button":
                return f"If {v} Then {name}.PerformClick()"
            return f"{name}.Value = {v}"
        if p == "listindex":
            return f"{name}.SelectedIndex = {v}"
        if p in ("left", "top", "width", "height"):
            self.note("approx", line, f"{name}.{prop.capitalize()}: VB6 twips -> pixels (/ 15)")
            return f"{name}.{prop.capitalize()} = CInt(({v}) / 15)"
        if p in ("backcolor", "forecolor"):
            return f"{name}.{prop[:-5].capitalize()}Color = ColorTranslator.FromOle({v})"
        return f"{name}.{self.ctx.spell(p)} = {v}"

    def target_obj(self, obj):
        """('ctl', name, type) | ('form',) | ('elem', code, type) | ('expr', code)."""
        if obj[0] == "me":
            return ("form",)
        if obj[0] == "withobj":
            return self.with_stack[-1] if self.with_stack else ("expr", "")
        if obj[0] == "name":
            c = self.ctl(obj[2])
            if c is not None and obj[2] not in self.locals:
                return ("ctl", c.name, c.type)
            if obj[2] == "app":
                return ("app",)
        if obj[0] == "call" and obj[2][0] == "name" and self.arr(obj[2][2]) and len(obj[3]) == 1:
            a = self.arr(obj[2][2])
            return ("elem", f"{a[0]}({self.ex(obj[3][0])})", a[1])
        if obj[0] == "member" and obj[2][0] == "me":
            c = self.ctl(obj[3])
            if c is not None:
                return ("ctl", c.name, c.type)
        return ("expr", self.ex(obj))

    def member(self, n) -> str:
        obj, prop, raw = n[2], n[3], n[4]
        t = self.target_obj(obj)
        if t[0] in ("ctl", "elem"):
            return self.prop_get(t[1], t[2], prop, n[1])
        if t[0] == "form":
            if prop == "caption":
                return "Me.Text"
            c = self.ctl(prop)
            if c is not None:
                return c.name
            if prop in ("width", "height", "left", "top"):
                self.note("approx", n[1], f"Me.{raw}: VB6 twips -> pixels * 15")
                return f"(Me.{prop.capitalize()} * 15)"
            return f"Me.{self.spell(prop, raw)}"
        if t[0] == "app":
            got = {"path": "Application.StartupPath", "title": "Application.ProductName",
                   "exename": "IO.Path.GetFileNameWithoutExtension(Application.ExecutablePath)",
                   "major": "CInt(Application.ProductVersion.Split(\".\"c)(0))",
                   "minor": "CInt(Application.ProductVersion.Split(\".\"c)(1))",
                   "revision": "CInt(Application.ProductVersion.Split(\".\"c)(2))",
                   "previnstance": "False"}.get(prop)
            if got is None:
                raise Untranslatable(f"App.{raw}")
            return got
        if obj[0] == "name" and obj[2] in ("screen", "printer", "clipboard"):
            if obj[2] == "clipboard" and prop in ("gettext",):
                return "Clipboard.GetText()"
            raise Untranslatable(f"{obj[2].capitalize()}.{raw}")
        return f"{t[1]}.{self.spell(prop, raw)}"

    def args(self, args) -> str:
        return ", ".join(self.ex(a) for a in args)

    def call(self, n) -> str:
        func, args = n[2], n[3]
        if func[0] == "name":
            low = func[2]
            a = self.arr(low)
            if a is not None and low not in self.locals:
                if len(args) == 1:
                    prop = DEFAULT_PROP.get(a[1], "text")
                    return self.prop_get(f"{a[0]}({self.ex(args[0])})", a[1], prop, n[1])
            if low in FUNC_MAP:
                return f"{FUNC_MAP[low]}({self.args(args)})"
            if low == "iif":
                return f"IIf({self.args(args)})"
            if low in ("loadpicture", "createobject"):
                raise Untranslatable(f"{self.spell(low)}()")
            ev = getattr(self, "event_names", {}).get(low)
            if ev is not None:
                h, kind, nev = ev
                args_t = WF_EVENT_ARGS.get(nev, "EventArgs")
                if args_t != "EventArgs":
                    raise Untranslatable(f"direct call of the event procedure {self.spell(low)}")
                if kind == "array" and args:
                    aname = h.rsplit("_", 1)[0]
                    return f"{h}({aname}({self.ex(args[0])}), EventArgs.Empty)"
                return f"{h}(Nothing, EventArgs.Empty)"
            if low == "format":
                return f"Format({self.args(args)})"
            return f"{self.name(low, func[3] if len(func) > 3 else '')}({self.args(args)})"
        if func[0] == "member":
            obj, meth, raw = func[2], func[3], func[4]
            t = self.target_obj(obj)
            if t[0] in ("ctl", "elem"):
                return self.ctl_method(t[1], t[2], meth, args, n[1])
            if t[0] == "form":
                if meth in ("hide", "show", "refresh"):
                    return f"Me.{_cls(meth)}()"
                return f"Me.{self.spell(meth, raw)}({self.args(args)})"
            if obj[0] == "name" and obj[2] in self.ctx.forms and meth in ("show", "hide"):
                f = self.ctx.forms[obj[2]].name
                if meth == "show":
                    modal = bool(args) and self.ex(args[0]) in ("True", "1")
                    return f"Call New {f}().{'ShowDialog' if modal else 'Show'}()"
                raise Untranslatable(f"{f}.Hide")
            if obj[0] == "name" and obj[2] == "err" and meth in ("raise", "clear"):
                return f"Err.{_cls(meth)}({self.args(args)})"
            if obj[0] == "name" and obj[2] == "clipboard":
                if meth == "settext":
                    return f"Clipboard.SetText({self.args(args)})"
                if meth == "clear":
                    return "Clipboard.Clear()"
            return f"{t[1]}.{self.spell(meth, raw)}({self.args(args)})"
        return f"{self.ex(func)}({self.args(args)})"

    def ctl_method(self, name, t, meth, args, line) -> str:
        a = [self.ex(x) for x in args]
        if meth == "additem":
            return f"{name}.Items.Insert({a[1]}, {a[0]})" if len(a) > 1 else f"{name}.Items.Add({a[0]})"
        if meth == "removeitem":
            return f"{name}.Items.RemoveAt({a[0]})"
        if meth == "clear":
            return f"{name}.Items.Clear()" if t in ("ListBox", "ComboBox") else f"{name}.Clear()"
        if meth == "list":
            return f"{name}.Items({a[0]}).ToString()"
        if meth == "selected":
            return f"{name}.GetSelected({a[0]})"
        if meth == "setfocus":
            return f"{name}.Focus()"
        if meth == "refresh":
            return f"{name}.Refresh()"
        if meth == "zorder":
            return f"{name}.BringToFront()"
        if meth == "move":
            self.note("approx", line, f"{name}.Move: VB6 twips -> pixels")
            return f"{name}.SetBounds({', '.join(f'CInt(({x}) / 15)' for x in a[:4])})"
        return f"{name}.{self.ctx.spell(meth)}({', '.join(a)})"

    # ------------------------------------------------------------------ statements
    def block(self, stmts, ind=1) -> list[str]:
        out = []
        for s in stmts:
            out += ["    " * ind + ln if ln else "" for ln in self.stmt(s)]
        return out

    def stmt(self, s) -> list[str]:
        line = s[1]
        pre = self.comments_before(line)
        try:
            lines = self._stmt(s)
        except (Untranslatable, KeyError, IndexError, TypeError) as e:
            src = self.lines_src[line - 1].strip() if 0 < line <= len(self.lines_src) else ""
            self.note("manual", line, f"{e}: `{src}`")
            lines = [f"' TODO (VB6, {self.file}:{line}): {src}"]
        if lines:
            lines[0] += self.trailing(line)
        return pre + lines

    def assign(self, target, value, line) -> list[str]:
        v = self.ex(value)
        if target[0] == "name":
            low = target[2]
            if low in self.alias:
                return [f"{self.alias[low]} = {v}"]
            c = self.ctl(low)
            if c is not None and low not in self.locals:
                return [self.prop_set(c.name, c.type, DEFAULT_PROP.get(c.type, "text"), v, line)]
            return [f"{self.name(low, target[3] if len(target) > 3 else '')} = {v}"]
        if target[0] == "member":
            t = self.target_obj(target[2])
            prop, raw = target[3], target[4]
            if t[0] in ("ctl", "elem"):
                return [self.prop_set(t[1], t[2], prop, v, line)]
            if t[0] == "form":
                if prop == "caption":
                    return [f"Me.Text = {v}"]
                if prop in ("width", "height", "left", "top"):
                    self.note("approx", line, f"Me.{raw}: VB6 twips -> pixels")
                    return [f"Me.{prop.capitalize()} = CInt(({v}) / 15)"]
                return [f"Me.{self.spell(prop, raw)} = {v}"]
            return [f"{t[1]}.{self.spell(prop, raw)} = {v}"]
        if target[0] == "call" and target[2][0] == "name" and target[2][2] == "mid":
            raise Untranslatable("Mid statement")
        if target[0] == "call" and target[2][0] == "name" and self.arr(target[2][2]) and len(target[3]) == 1:
            a = self.arr(target[2][2])
            return [self.prop_set(f"{a[0]}({self.ex(target[3][0])})", a[1], DEFAULT_PROP.get(a[1], "text"), v,
                                  line)]
        return [f"{self.ex(target)} = {v}"]

    def dims(self, items, kw="Dim") -> list[str]:
        out = []
        for nm, bounds, typ in items:
            disp = self.spell(nm)
            self.locals[nm] = disp
            t = vb_type(typ)
            if bounds is None:
                out.append(f"{kw} {disp} As {t}")
            elif not bounds:
                out.append(f"{kw} {disp}() As {t}")
            else:
                ups = []
                for lo, hi in bounds:
                    if lo is not None and self.ex(lo) not in ("0",):
                        self.note("approx", 0, f"array {disp}: lower bound {self.ex(lo)} - VB.NET arrays start at 0")
                    ups.append(self.ex(hi))
                out.append(f"{kw} {disp}({', '.join(ups)}) As {t.replace('New ', '')}")
        return out

    def _stmt(self, s) -> list[str]:
        k, line = s[0], s[1]
        if k == "nop":
            return []
        if k in ("assign", "set"):
            return self.assign(s[2], s[3], line)
        if k == "callstmt":
            call = s[2]
            func = call[2]
            if func[0] == "name" and func[2] == "randomize":
                return ["Randomize()"]
            code = self.ex(call)
            return [code]
        if k in ("dim", "static"):
            return self.dims(s[2], "Dim" if k == "dim" else "Static")
        if k == "const":
            return [f"Const {self.spell(nm)} = {self.ex(e)}" for nm, e in s[2]]
        if k == "redim":
            out = []
            for nm, bounds, typ in s[2]:
                out.append(f"ReDim {'Preserve ' if s[3] else ''}{self.name(nm)}"
                           f"({', '.join(self.ex(hi) for _lo, hi in bounds)})")
            return out
        if k == "if":
            out = []
            for i, (cond, body) in enumerate(s[2]):
                out.append(f"{'If' if i == 0 else 'ElseIf'} {self.ex(cond)} Then")
                out += self.block(body)
            if s[3]:
                out.append("Else")
                out += self.block(s[3])
            return out + ["End If"]
        if k == "select":
            out = [f"Select Case {self.ex(s[2])}"]
            for tests, body in s[3]:
                parts = []
                for t in tests:
                    if t[0] == "eq":
                        parts.append(self.ex(t[1]))
                    elif t[0] == "range":
                        parts.append(f"{self.ex(t[1])} To {self.ex(t[2])}")
                    else:
                        parts.append(f"Is {t[1]} {self.ex(t[2])}")
                out.append(f"    Case {', '.join(parts)}")
                out += self.block(body, 2)
            if s[4]:
                out.append("    Case Else")
                out += self.block(s[4], 2)
            return out + ["End Select"]
        if k == "for":
            step = f" Step {self.ex(s[5])}" if s[5] is not None else ""
            return [f"For {self.name(s[2])} = {self.ex(s[3])} To {self.ex(s[4])}{step}"] + self.block(s[6]) + \
                ["Next"]
        if k == "foreach":
            return [f"For Each {self.name(s[2])} In {self.ex(s[3])}"] + self.block(s[4]) + ["Next"]
        if k == "do":
            pre, post = s[2], s[3]
            head = "Do" + (f" {_cls(pre[0])} {self.ex(pre[1])}" if pre else "")
            tail = "Loop" + (f" {_cls(post[0])} {self.ex(post[1])}" if post else "")
            if pre and pre[0] == "while" and not post and self.lines_src[line - 1].strip().lower().startswith("while"):
                return [f"While {self.ex(pre[1])}"] + self.block(s[4]) + ["End While"]
            return [head] + self.block(s[4]) + [tail]
        if k == "with":
            t = self.target_obj(s[2])
            if t[0] in ("ctl", "elem", "form"):
                self.with_stack.append(t)
                try:
                    return self.block(s[3], 0)
                finally:
                    self.with_stack.pop()
            self.with_stack.append(("expr", ""))
            try:
                return [f"With {t[1]}"] + self.block(s[3]) + ["End With"]
            finally:
                self.with_stack.pop()
        if k == "exit":
            return [f"Exit {_cls(s[2])}"]
        if k == "end":
            return ["End"]
        if k == "stop":
            return ["Stop"]
        if k == "unload":
            if s[2][0] == "me":
                return ["Me.Close()"]
            raise Untranslatable("Unload of another form / control")
        if k == "loadform":
            raise Untranslatable("Load statement")
        if k == "debugprint":
            return [f"Debug.WriteLine({' & '.join(self.ex(a) for a in s[3]) or chr(34) * 2})"]
        if k == "open":
            mode = {"input": "Input", "output": "Output", "append": "Append", "binary": "Binary",
                    "random": "Random"}.get(s[3], "Input")
            return [f"FileOpen({self.ex(s[5])}, {self.ex(s[2])}, OpenMode.{mode})"]
        if k == "close":
            return [f"FileClose({', '.join(self.ex(n) for n in s[2])})"]
        if k == "fprint":
            num = self.ex(s[2])
            items = s[3]
            trailing = bool(items) and items[-1][1] in (";", ",")
            groups, cur = [], []
            for e, sep in items:
                if e is not None:
                    cur.append(self.ex(e))
                if sep == "," or (sep == "" and e is not None):
                    groups.append(" & ".join(cur) if cur else '""')
                    cur = []
            if cur:
                groups.append(" & ".join(cur))
            fn = "Print" if trailing else "PrintLine"
            return [f"{fn}({num}{''.join(', ' + g for g in groups)})"]
        if k == "fwrite":
            return [f"WriteLine({self.ex(s[2])}{''.join(', ' + self.ex(e) for e, _sep in s[3] if e is not None)})"]
        if k == "flineinput":
            return [f"{self.ex(s[3])} = LineInput({self.ex(s[2])})"]
        if k == "finput":
            return [f"Input({self.ex(s[2])}, {self.ex(t)})" for t in s[3]]
        if k == "rename":
            return [f"Rename({self.ex(s[2])}, {self.ex(s[3])})"]
        if k == "errorstmt":
            return [f"Err.Raise({self.ex(s[2])})"]
        if k == "erase":
            return [f"Erase {', '.join(self.name(n) for n in s[2])}"]
        if k == "label":
            return [f"{self.ctx.spell(s[2]) if not s[2].isdigit() else 'L' + s[2]}:"]
        if k == "goto":
            return [f"GoTo {self.ctx.spell(s[2]) if not s[2].isdigit() else 'L' + s[2]}"]
        if k == "onerror":
            if s[2] == "next":
                return ["On Error Resume Next"]
            if s[2] == "0":
                return ["On Error GoTo 0"]
            return [f"On Error GoTo {self.ctx.spell(s[2]) if not s[2].isdigit() else 'L' + s[2]}"]
        if k == "resume":
            return ["Resume Next" if s[2] == "next" else f"Resume {self.ctx.spell(s[2])}" if s[2] else "Resume"]
        if k in ("gosub", "return", "ongoto"):
            raise Untranslatable("GoSub/Return (not in VB.NET)")
        if k == "raiseevent":
            return [f"RaiseEvent {self.spell(s[2])}({self.args(s[3])})"]
        if k in ("fget", "fput", "fseek"):
            name = {"fget": "FileGet", "fput": "FilePut", "fseek": "Seek"}[k]
            if k == "fseek":
                return [f"Seek({self.ex(s[2])}, {self.ex(s[3])})"]
            pos = f", {self.ex(s[3])}" if s[3] is not None else ""
            return [f"{name}({self.ex(s[2])}, {self.ex(s[4])}{pos})"]
        raise Untranslatable(f"statement {k}")

    # ------------------------------------------------------------------ procedures
    def params(self, proc, skip=0) -> str:
        out = []
        for p in proc.params[skip:]:
            disp = self.spell(p.name)
            self.locals[p.name] = disp
            t = vb_type(p.typ)
            s = ("ByVal " if not p.byref else "ByRef ")
            if p.paramarray:
                s = "ParamArray "
                out.append(f"{s}{disp}() As Object")
                continue
            if p.optional:
                dv = self.ex(p.default) if p.default is not None else \
                    {"String": '""', "Boolean": "False", "Object": "Nothing", "Date": "Nothing"}.get(t, "0")
                out.append(f"Optional {s}{disp}{'()' if p.is_array else ''} As {t} = {dv}")
            else:
                out.append(f"{s}{disp}{'()' if p.is_array else ''} As {t}")
        return ", ".join(out)

    def start(self, proc):
        self.proc = proc
        self.locals = {}
        self.alias = {}
        self.with_stack = []
        prev = max([r[1] for r in self.ranges if r[1] < proc.line] + [x for x in self.decl_lines if x < proc.line]
                   or [0])
        self.proc_start = prev + 1


def _ret_type(text_lines, proc) -> str:
    if 0 < proc.line <= len(text_lines):
        m = re.search(r"\)\s*As\s+(\w+)", text_lines[proc.line - 1], re.I)
        if m:
            return vb_type(m.group(1))
    return "Object"


def _decls(tr: VBNetTranslator, mod, public_default="Private") -> list[str]:
    out = []
    for d in mod.decls:
        line = d[1]
        if d[0] in ("dim", "static"):
            for item in tr.dims(d[2], "Public" if d[3] else public_default):
                out.append(item + tr.trailing(line))
            for nm, _b, _t in d[2]:
                tr.fields[nm] = tr.spell(nm)
                tr.locals.pop(nm, None)
        elif d[0] == "const":
            for nm, e in d[2]:
                out.append(f"{'Public' if d[3] else 'Private'} Const {tr.spell(nm)} = {tr.ex(e)}{tr.trailing(line)}")
        elif d[0] == "enum":
            out.append(f"Public Enum {tr.spell(d[2])}")
            for mname, v in d[3]:
                out.append(f"    {tr.spell(mname)}" + (f" = {tr.ex(v)}" if isinstance(v, tuple) and v[0] != "binop"
                                                        else ""))
            out.append("End Enum")
        elif d[0] == "type":
            out.append(f"Public Structure {tr.spell(d[2])}")
            for m in d[3]:
                if len(m) > 2:
                    tr.note("approx", line, f"fixed array {tr.spell(m[0])} in Type {tr.spell(d[2])}: initialise it "
                                            "with ReDim before use")
                    out.append(f"    Public {tr.spell(m[0])}() As {vb_type(m[1])}")
                else:
                    out.append(f"    Public {tr.spell(m[0])} As {vb_type(m[1])}")
            out.append("End Structure")
            tr.note("rules", line, f"Type {tr.spell(d[2])} became a Structure")
    for dec in mod.declares:
        params = ", ".join(f"{'ByVal ' if not p.byref else 'ByRef '}{tr.spell(p.name)} As {vb_type(p.typ)}"
                           for p in dec.params)
        ret = f" As {vb_type(dec.ret)}" if dec.kind == "function" else ""
        out.append(f"{'Public' if dec.public else 'Private'} Declare Auto {_cls(dec.kind)} {tr.spell(dec.name)} Lib "
                   f"\"{dec.lib}\"{' Alias ' + vbstr(dec.alias) if dec.alias and dec.alias.lower() != dec.name else ''}"
                   f" ({params}){ret}")
        tr.note("approx", dec.line, f"Declare {tr.spell(dec.name)}: Long -> Integer; check String/structure arguments")
    tr.locals = {}
    return out


def form_code_vbnet(ctx: ProjectContext, fi: FormInfo, text: str, file: str, notes: Notes) -> tuple[str, int]:
    """Form1.vb (the code) for a VB6 form.  Returns (text, number of handlers)."""
    code = code_part(text)
    tr = VBNetTranslator(ctx, file, code, notes, fi, "frm")
    try:
        mod = vbparse.parse_module(code, fi.name, file)
    except vbparse.VBSyntaxError as e:
        notes.add("manual", file, e.line, f"VB6 code could not be parsed ({e.msg}) - kept as comments")
        return (f"Public Class {fi.name}\n" + "\n".join("    ' " + ln for ln in code.splitlines() if ln.strip()) +
                "\nEnd Class\n"), 0
    tr.decl_lines = [d[1] for d in mod.decls]
    tr.event_names = event_handler_names(fi, mod, fi.name)
    menu_items = {n.lower(): n for c in fi.form.controls if c.type == "MenuStrip"
                  for n in menu_names(c.props.get("Items", []))}
    for p in mod.procs.values():
        base = p.name.split(":")[-1]
        ctrl, _, vbev = base.rpartition("_")
        if p.kind == "sub" and vbev == "click" and ctrl in menu_items and base not in tr.event_names:
            tr.event_names[base] = (f"{menu_items[ctrl]}_Click", "menu", "Click")
    out = [f"Public Class {fi.name}", ""]
    first = min([r[0] for r in tr.ranges] or [10 ** 9])
    for ln, (c, whole) in sorted(tr.comments.items()):
        if whole and ln < first and ln < max(tr.decl_lines or [0]):
            out.append(f"    ' {c}")
            tr.done.add(ln)
    out += ["    " + ln for ln in _decls(tr, mod)]
    n_handlers = 0
    # control arrays: arrays of controls filled in the constructor
    arrays = sorted(fi.arrays.items())
    if arrays:
        out.append("")
        for low, (aname, atype, items) in arrays:
            out.append(f"    Private {aname}() As {WF_TYPE.get(atype, 'Control')}")
        out += ["", "    Public Sub New()", "        InitializeComponent()"]
        for low, (aname, atype, items) in arrays:
            n = max(items) + 1
            elems = ", ".join(items[i].name if i in items else "Nothing" for i in range(n))
            out.append(f"        {aname} = New {WF_TYPE.get(atype, 'Control')}() {{{elems}}}")
            notes.add("rules", file, 0, f"control array {aname} became an array of {len(items)} controls "
                                        "(one handler with Handles for every element)")
        out.append("    End Sub")
    lines_src = code.replace("\r\n", "\n").split("\n")
    for p in mod.procs.values():
        base = p.name.split(":")[-1]
        tr.start(p)
        ctrl, _, vbev = base.rpartition("_")
        body_pre: list[str] = []
        try:
            target = None
            if p.kind == "sub" and ctrl and base in tr.event_names and tr.event_names[base][1] == "menu":
                target = ("menu", "Click", menu_items[ctrl])
            elif p.kind == "sub" and ctrl:
                if ctrl in ("form", "mdiform"):
                    nev = vb_event_to_neutral("Form", vbev)
                    if nev:
                        target = ("form", nev)
                elif fi.controls.get(ctrl):
                    c = fi.controls[ctrl]
                    nev = vb_event_to_neutral(c.type, vbev)
                    if nev:
                        target = ("ctl", nev, c)
                elif fi.arrays.get(ctrl):
                    a = fi.arrays[ctrl]
                    nev = vb_event_to_neutral(a[1], vbev)
                    if nev:
                        target = ("arr", nev, a)
            if target is None:
                kw = {"sub": "Sub", "function": "Function"}.get(p.kind)
                if kw is None:
                    raise Untranslatable("Property procedures in a form")
                head = f"{'Public' if p.public else 'Private'} {kw} {strip_suffix(p.display)}({tr.params(p)})"
                if kw == "Function":
                    head += f" As {_ret_type(lines_src, p)}"
                out += ["", "    " + head] + tr.block(p.body, 2) + [f"    End {kw}"]
                continue
            nev = target[1]
            ev_args = WF_EVENT_ARGS.get(nev, "EventArgs")
            wf_ev = {"Tick": "Tick", "GotFocus": "Enter", "LostFocus": "Leave"}.get(nev, nev)
            skip = 0
            if target[0] == "form":
                hname = f"{fi.name}_{nev}"
                handles = f"MyBase.{wf_ev}" if nev in ("Load", "Activated", "Deactivate", "Resize", "Click") \
                    else f"Me.{wf_ev}"
            elif target[0] == "ctl":
                hname = f"{target[2].name}_{nev}"
                handles = f"{target[2].name}.{wf_ev}"
            elif target[0] == "menu":
                hname = f"{target[2]}_Click"
                handles = f"{target[2]}.Click"
            else:
                aname, atype, items = target[2]
                hname = f"{aname}_{nev}"
                handles = ", ".join(f"{items[i].name}.{wf_ev}" for i in sorted(items))
                idx = tr.spell(p.params[0].name) if p.params else "Index"
                tr.locals[p.params[0].name if p.params else "index"] = idx
                body_pre.append(f"Dim {idx} As Integer = Array.IndexOf({aname}, sender)")
                skip = 1
            params = [x.name for x in p.params[skip:]]
            if nev == "KeyPress" and params:
                kn = tr.spell(params[0])
                tr.locals[params[0]] = kn
                body_pre.append(f"Dim {kn} As Integer = AscW(e.KeyChar)")
                p._post = [f"If {kn} = 0 Then e.Handled = True Else If {kn} <> AscW(e.KeyChar) Then e.KeyChar = "
                           f"ChrW({kn})"]
                tr.note("rules", p.line, "KeyPress(KeyAscii): KeyAscii = 0 sets e.Handled (key swallowed)")
            elif nev in ("KeyDown", "KeyUp") and params:
                tr.locals[params[0]] = tr.spell(params[0])
                body_pre.append(f"Dim {tr.spell(params[0])} As Integer = e.KeyCode")
                if len(params) > 1:
                    tr.locals[params[1]] = tr.spell(params[1])
                    body_pre.append(f"Dim {tr.spell(params[1])} As Integer = CInt(e.Modifiers) \\ 65536")
            elif nev in ("MouseDown", "MouseUp", "MouseMove") and params:
                vals = ["CInt(e.Button) \\ 1048576", "CInt(Control.ModifierKeys) \\ 65536", "e.X * 15", "e.Y * 15"]
                for x, v in zip(params, vals):
                    tr.locals[x] = tr.spell(x)
                    body_pre.append(f"Dim {tr.spell(x)} As Single = {v}")
                tr.note("approx", p.line, f"{nev}: X/Y converted to twips, Button from MouseButtons")
            elif nev == "FormClosing" and params:
                tr.alias[params[0]] = "e.Cancel"
                for x in params[1:]:
                    tr.locals[x] = tr.spell(x)
                    body_pre.append(f"Dim {tr.spell(x)} As Integer = 0")
            elif params:
                for x in params:
                    tr.locals[x] = tr.spell(x)
                    body_pre.append(f"Dim {tr.spell(x)} As Object = Nothing")
                tr.note("approx", p.line, f"{p.display}: event parameters have no VB.NET equivalent")
            head = f"Private Sub {hname}(sender As Object, e As {ev_args}) Handles {handles}"
            body = ["        " + b for b in body_pre] + tr.block(p.body, 2) + \
                ["        " + b for b in getattr(p, "_post", [])]
            out += ["", "    " + head] + body + ["    End Sub"]
            n_handlers += 1
        except Untranslatable as e:
            rng = next((r for r in tr.ranges if r[0] == p.line), (p.line, p.line, ""))
            notes.add("manual", file, p.line, f"{p.display}: not translated ({e}) - kept as comments")
            out += ["", f"    ' TODO (VB6): {p.display} was not translated"] + \
                ["    ' " + ln for ln in lines_src[rng[0] - 1:rng[1]]]
    out += ["", "End Class"]
    return "\n".join(out) + "\n", n_handlers


def module_vbnet(ctx: ProjectContext, name: str, text: str, kind: str, file: str, notes: Notes) -> str:
    code = code_part(text) if kind == "cls" else text
    tr = VBNetTranslator(ctx, file, code, notes, None, kind)
    try:
        mod = vbparse.parse_module(code, name, file)
    except vbparse.VBSyntaxError as e:
        notes.add("manual", file, e.line, f"VB6 code could not be parsed ({e.msg}) - kept as comments")
        return f"Module {name}\n" + "\n".join("    ' " + ln for ln in code.splitlines()) + "\nEnd Module\n"
    tr.decl_lines = [d[1] for d in mod.decls]
    lines_src = code.replace("\r\n", "\n").split("\n")
    out = [f"Public {'Class' if kind == 'cls' else 'Module'} {name}", ""]
    out += ["    " + ln for ln in _decls(tr, mod, "Private")]
    props: dict[str, dict] = {}
    for p in mod.procs.values():
        tr.start(p)
        try:
            if p.kind in ("get", "let", "set"):
                props.setdefault(strip_suffix(p.display), {})[p.kind] = p
                continue
            kw = "Function" if p.kind == "function" else "Sub"
            head = f"{'Public' if p.public else 'Private'} {kw} {strip_suffix(p.display)}({tr.params(p)})"
            if kw == "Function":
                head += f" As {_ret_type(lines_src, p)}"
            if kind == "cls" and p.name in ("class_initialize",):
                head = "Public Sub New()"
            if kind == "cls" and p.name in ("class_terminate",):
                head = "Protected Overrides Sub Finalize()"
                tr.note("approx", p.line, "Class_Terminate became Finalize (runs at garbage collection)")
            body = tr.block(p.body, 2)
            if kind == "bas" and p.name == "main":
                # VB6 Sub Main shows the first form and returns; .NET needs Application.Run for the message loop
                for i, ln in enumerate(body):
                    m = re.match(r"^(\s*)Call New (\w+)\(\)\.Show\(\)\s*$", ln)
                    if m:
                        body[i] = f"{m.group(1)}Application.Run(New {m.group(2)}())"
                        tr.note("rules", p.line, f"Sub Main: {m.group(2)}.Show became Application.Run(New "
                                                 f"{m.group(2)}()) (the message loop of the program)")
                        break
                head = "Public Sub Main()"
                body = ["        Application.EnableVisualStyles()"] + body
            out += ["", "    " + head] + body + [f"    End {kw}"]
        except Untranslatable as e:
            notes.add("manual", file, p.line, f"{p.display}: not translated ({e})")
    for pname, kinds in props.items():
        g = kinds.get("get")
        st = kinds.get("let") or kinds.get("set")
        typ = _ret_type(lines_src, g) if g else (vb_type(st.params[-1].typ) if st and st.params else "Object")
        ro = "ReadOnly " if g and not st else ("WriteOnly " if st and not g else "")
        out += ["", f"    Public {ro}Property {pname}() As {typ}"]
        if g:
            tr.start(g)
            out += ["        Get"] + tr.block(g.body, 3) + ["        End Get"]
        if st:
            tr.start(st)
            pv = st.params[-1] if st.params else None
            if pv is not None:
                tr.locals[pv.name] = tr.spell(pv.name)
            out += [f"        Set(ByVal {tr.spell(pv.name) if pv else 'value'} As {typ})"] + tr.block(st.body, 3) + \
                ["        End Set"]
        out.append("    End Property")
        notes.add("rules", file, (g or st).line, f"Property Get/Let {pname} became a VB.NET Property")
    out += ["", f"End {'Class' if kind == 'cls' else 'Module'}"]
    return "\n".join(out) + "\n"


# ============================================================================ designer + project
def _color(c: str) -> str:
    c = str(c or "")
    if not c.startswith("#") or len(c) < 7:
        return ""
    return f"System.Drawing.Color.FromArgb(CType(CType({int(c[1:3], 16)}, Byte), Integer), CType(CType(" \
           f"{int(c[3:5], 16)}, Byte), Integer), CType(CType({int(c[5:7], 16)}, Byte), Integer))"


def designer_vb(form) -> str:
    """Form1.Designer.vb (InitializeComponent) for a neutral form."""
    ctrls = [c for c in form.controls if c.type in WF_TYPE]
    has_timer = any(c.type == "Timer" for c in ctrls)
    L = ["<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>", f"Partial Class {form.name}",
         "    Inherits System.Windows.Forms.Form", "",
         "    'Form overrides dispose to clean up the component list.",
         "    <System.Diagnostics.DebuggerNonUserCode()>",
         "    Protected Overrides Sub Dispose(disposing As Boolean)", "        Try",
         "            If disposing AndAlso components IsNot Nothing Then", "                components.Dispose()",
         "            End If", "        Finally", "            MyBase.Dispose(disposing)", "        End Try",
         "    End Sub", "", "    'Required by the Windows Form Designer",
         "    Private components As System.ComponentModel.IContainer", "",
         "    'NOTE: The following procedure is required by the Windows Form Designer",
         "    'It can be modified using the Windows Form Designer.",
         "    'Do not modify it using the code editor.",
         "    <System.Diagnostics.DebuggerStepThrough()>", "    Private Sub InitializeComponent()"]
    B = "        "
    if has_timer:
        L.append(B + "Me.components = New System.ComponentModel.Container()")
    for c in ctrls:
        t = WF_TYPE[c.type]
        if c.type == "Timer":
            L.append(B + f"Me.{c.name} = New System.Windows.Forms.Timer(Me.components)")
        else:
            L.append(B + f"Me.{c.name} = New System.Windows.Forms.{t}()")
    menu_lines, menu_fields = _menu_items(form, ctrls)
    L += [B + ln for ln in menu_lines[0]]
    containers = [c for c in ctrls if c.ctype.container]
    for c in containers:
        L.append(B + f"Me.{c.name}.SuspendLayout()")
    L.append(B + "Me.SuspendLayout()")
    tab = 0
    for c in ctrls:
        p = c.props
        L += [B + "'", B + f"'{c.name}", B + "'"]
        s = f"{B}Me.{c.name}"
        if c.type == "Timer":
            L.append(f"{s}.Interval = {max(1, int(p.get('Interval', 100) or 100))}")
            if p.get("Enabled"):
                L.append(f"{s}.Enabled = True")
            continue
        if c.type == "MenuStrip":
            L += [B + ln for ln in menu_lines[1].get(c.name, [])]
            L.append(f"{s}.Location = New System.Drawing.Point(0, 0)")
            L.append(f"{s}.Name = {vbstr(c.name)}")
            continue
        for ch in form.children(c.name):
            L.append(f"{s}.Controls.Add(Me.{ch.name})")
        if c.type == "Label" and not p.get("AutoSize"):
            L.append(f"{s}.AutoSize = False")
        L.append(f"{s}.Location = New System.Drawing.Point({int(p.get('Left', 0))}, {int(p.get('Top', 0))})")
        L.append(f"{s}.Name = {vbstr(c.name)}")
        L.append(f"{s}.Size = New System.Drawing.Size({int(p.get('Width', 75))}, {int(p.get('Height', 23))})")
        L.append(f"{s}.TabIndex = {int(p.get('TabIndex', tab) or tab)}")
        tab += 1
        if "Text" in p and c.type not in ("ListBox", "ProgressBar", "TrackBar", "NumericUpDown", "Panel",
                                          "PictureBox", "TabControl"):
            L.append(f"{s}.Text = {vbstr(p.get('Text', ''))}")
        if p.get("Enabled") is False:
            L.append(f"{s}.Enabled = False")
        if p.get("Visible") is False:
            L.append(f"{s}.Visible = False")
        for key, prop in (("BackColor", "BackColor"), ("ForeColor", "ForeColor")):
            col = _color(p.get(key))
            if col:
                L.append(f"{s}.{prop} = {col}")
        if p.get("FontBold") or (p.get("FontSize") and int(p.get("FontSize")) != 9) or \
                (p.get("FontName") and p.get("FontName") not in ("Segoe UI", "MS Sans Serif")):
            style = "System.Drawing.FontStyle.Bold" if p.get("FontBold") else "System.Drawing.FontStyle.Regular"
            L.append(f"{s}.Font = New System.Drawing.Font({vbstr(p.get('FontName') or 'Segoe UI')}, "
                     f"{float(p.get('FontSize') or 9)}!, {style})")
        if c.type == "Label":
            al = {"Left": "TopLeft", "Center": "TopCenter", "Right": "TopRight"}.get(p.get("TextAlign"), "TopLeft")
            if al != "TopLeft":
                L.append(f"{s}.TextAlign = System.Drawing.ContentAlignment.{al}")
        if c.type == "TextBox":
            if p.get("Multiline"):
                L += [f"{s}.Multiline = True", f"{s}.ScrollBars = System.Windows.Forms.ScrollBars.Vertical"]
            if p.get("ReadOnly"):
                L.append(f"{s}.ReadOnly = True")
            if p.get("PasswordChar"):
                L.append(f"{s}.PasswordChar = {vbstr(p['PasswordChar'][:1])}c")
            if int(p.get("MaxLength", 0) or 0):
                L.append(f"{s}.MaxLength = {int(p['MaxLength'])}")
        if c.type in ("CheckBox", "RadioButton") and p.get("Checked"):
            L.append(f"{s}.Checked = True")
        if c.type in ("ListBox", "ComboBox") and p.get("Items"):
            L.append(f"{s}.Items.AddRange(New Object() {{{', '.join(vbstr(i) for i in p['Items'])}}})")
        if c.type == "ComboBox" and p.get("DropDownStyle") == "DropDownList":
            L.append(f"{s}.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList")
        if c.type in ("ProgressBar", "TrackBar", "NumericUpDown"):
            L += [f"{s}.Minimum = {int(p.get('Minimum', 0) or 0)}", f"{s}.Maximum = {int(p.get('Maximum', 100) or 100)}"]
            if int(p.get("Value", 0) or 0):
                L.append(f"{s}.Value = {int(p['Value'])}")
        if c.type == "Button" and p.get("UseVisualStyleBackColor", True):
            L.append(f"{s}.UseVisualStyleBackColor = True")
    fp = form.props
    L += [B + "'", B + f"'{form.name}", B + "'",
          B + "Me.AutoScaleDimensions = New System.Drawing.SizeF(96.0!, 96.0!)",
          B + "Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Dpi",
          B + f"Me.ClientSize = New System.Drawing.Size({int(fp.get('Width', 400))}, {int(fp.get('Height', 300))})"]
    for c in reversed([c for c in ctrls if not c.parent and c.type not in ("Timer",)]):
        L.append(B + f"Me.Controls.Add(Me.{c.name})")
    menu = next((c for c in ctrls if c.type == "MenuStrip"), None)
    if menu is not None:
        L.append(B + f"Me.MainMenuStrip = Me.{menu.name}")
    if fp.get("FormBorderStyle") in ("FixedSingle", "FixedDialog", "FixedToolWindow", "None", "Fixed3D"):
        L.append(B + f"Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.{fp['FormBorderStyle']}")
        L.append(B + "Me.MaximizeBox = False")
    col = _color(fp.get("BackColor"))
    if col:
        L.append(B + f"Me.BackColor = {col}")
    L.append(B + f"Me.Name = {vbstr(form.name)}")
    if fp.get("StartPosition") == "CenterScreen":
        L.append(B + "Me.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen")
    L.append(B + f"Me.Text = {vbstr(fp.get('Text', form.name))}")
    for c in containers:
        L.append(B + f"Me.{c.name}.ResumeLayout(False)")
    L += [B + "Me.ResumeLayout(False)", B + "Me.PerformLayout()", "", "    End Sub", ""]
    for c in ctrls:
        t = WF_TYPE[c.type]
        L.append(f"    Friend WithEvents {c.name} As System.Windows.Forms.{t}")
    L += [f"    Friend WithEvents {n} As System.Windows.Forms.{t}" for n, t in menu_fields]
    L.append("End Class")
    return "\n".join(L) + "\n"


VBPROJ = """<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>{tfm}</TargetFramework>
    <RootNamespace>{name}</RootNamespace>
    <StartupObject>{startup_object}</StartupObject>
    <UseWindowsForms>true</UseWindowsForms>
    <OptionStrict>Off</OptionStrict>
    <OptionExplicit>On</OptionExplicit>
    <OptionInfer>On</OptionInfer>
    <AssemblyTitle>{title}</AssemblyTitle>
    <Product>{title}</Product>
    <Version>{version}</Version>
  </PropertyGroup>

  <ItemGroup>
    <Import Include="System.Data" />
    <Import Include="System.Drawing" />
    <Import Include="System.Windows.Forms" />
  </ItemGroup>

</Project>
"""

PROGRAM = """Friend Module Program

    <STAThread()>
    Friend Sub Main(args As String())
        Application.SetHighDpiMode(HighDpiMode.SystemAware)
        Application.EnableVisualStyles()
        Application.SetCompatibleTextRenderingDefault(False)
        Application.Run(New {startup}())
    End Sub

End Module
"""


def _tfm() -> str:
    import subprocess
    try:
        out = subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True, timeout=30).stdout
        majors = sorted({int(m) for m in re.findall(r"^(\d+)\.", out, re.M)})
        if majors:
            return f"net{max(m for m in majors if m >= 6) if any(m >= 6 for m in majors) else 8}.0-windows"
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return "net8.0-windows"


def write_vbnet_project(src, dest: Path, notes: Notes, stats: dict, progress, opts) -> Path:
    from .engine import _ident, vb6_context
    ctx = vb6_context(src)
    name = _ident(src.name, "Project")
    for sf in src.forms:
        progress(f"Form {sf.name} -> {sf.name}.vb + {sf.name}.Designer.vb ...")
        fi = ctx.forms[sf.name.lower()]
        code, nh = form_code_vbnet(ctx, fi, sf.code, sf.file.name, notes)
        (dest / f"{sf.name}.vb").write_text(code, encoding="utf-8")
        (dest / f"{sf.name}.Designer.vb").write_text(designer_vb(sf.form), encoding="utf-8")
        stats["forms"] += 1
        stats["controls"] += len(sf.form.controls)
        stats["handlers"] += nh
        notes.add("exact", sf.file.name, 0, f"form {sf.name}: {len(sf.form.controls)} control(s) -> "
                                            f"{sf.name}.Designer.vb (InitializeComponent)")
    for mname, p, kind in src.modules:
        progress(f"Module {p.name} ...")
        from .engine import _vb_name
        vbn = mname if kind == "bas" else _vb_name(p) or mname
        (dest / f"{vbn}.vb").write_text(module_vbnet(ctx, vbn, read_text(p), kind, p.name, notes), encoding="utf-8")
        stats["modules"] += 1
        notes.add("rules", p.name, 0, f"{'module' if kind == 'bas' else 'class'} {vbn} -> {vbn}.vb")
    vbp = src.extra.get("vbp") or {}
    main_mod = None
    if src.startup == "Sub Main":
        for mname, p, kind in src.modules:
            if kind == "bas" and re.search(r"^\s*(?:Public\s+|Private\s+)?Sub\s+Main\s*\(", read_text(p), re.I | re.M):
                main_mod = mname
                break
    if main_mod:
        startup_object = f"{name}.{main_mod}"
        notes.add("rules", f"{main_mod}.vb", 0, f"the program starts with Sub Main of {main_mod} (like the VB6 project)")
    else:
        startup = src.startup if src.startup and src.startup != "Sub Main" else \
            (src.forms[0].name if src.forms else "Form1")
        (dest / "Program.vb").write_text(PROGRAM.format(startup=startup), encoding="utf-8")
        startup_object = f"{name}.Program"
    title = vbp.get("title") or vbp.get("name") or name
    version = _vbp_version(src.path) if src.path.suffix.lower() == ".vbp" else "1.0.0"
    proj = dest / f"{name}.vbproj"
    proj.write_text(VBPROJ.format(tfm=_tfm(), name=name, title=title, startup_object=startup_object,
                                  version=version), encoding="utf-8")
    notes.add("info", proj.name, 0, "build with `dotnet build` (or open it in Visual Studio / with File > Open Project)")
    return proj


def _vbp_version(vbp: Path) -> str:
    text = read_text(vbp)
    parts = []
    for key in ("MajorVer", "MinorVer", "RevisionVer"):
        m = re.search(rf"^\s*{key}\s*=\s*(\d+)", text, re.I | re.M)
        parts.append(m.group(1) if m else "0")
    if parts == ["0", "0", "0"]:
        parts[0] = "1"
    return ".".join(parts)


def build_check(proj: Path, timeout: int = 600) -> tuple[bool, str]:
    """dotnet build of a migrated project (used by the tests and the wizard's 'Build now' option)."""
    import subprocess
    try:
        r = subprocess.run(["dotnet", "build", str(proj), "-nologo", "-v", "q", "-clp:NoSummary"],
                           capture_output=True, text=True, timeout=timeout, cwd=str(proj.parent))
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout + r.stderr)[-6000:]


__all__ = ["write_vbnet_project", "designer_vb", "form_code_vbnet", "module_vbnet", "build_check", "CONTROL_TYPES"]


def _menu_items(form, ctrls):
    """((creation lines, {menu strip: property lines}), [(field, type)]) for the MenuStrip items."""
    create, props, fields = [], {}, []
    seq = [0]

    def walk(items, owner):
        names = []
        lines = props.setdefault(owner, [])
        for it in items or []:
            if it.get("Text") == "-":
                seq[0] += 1
                nm = f"ToolStripSeparator{seq[0]}"
                create.append(f"Me.{nm} = New System.Windows.Forms.ToolStripSeparator()")
                fields.append((nm, "ToolStripSeparator"))
                names.append(nm)
                continue
            nm = it.get("Name") or f"ToolStripMenuItem{len(fields) + 1}"
            create.append(f"Me.{nm} = New System.Windows.Forms.ToolStripMenuItem()")
            fields.append((nm, "ToolStripMenuItem"))
            names.append(nm)
            lines.append(f"Me.{nm}.Name = {vbstr(nm)}")
            lines.append(f"Me.{nm}.Text = {vbstr(it.get('Text', nm))}")
            if it.get("Items"):
                sub = walk(it["Items"], owner)
                lines.append(f"Me.{nm}.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() "
                             f"{{{', '.join('Me.' + x for x in sub)}}})")
        return names

    for c in ctrls:
        if c.type != "MenuStrip":
            continue
        top = walk(c.props.get("Items", []), c.name)
        props.setdefault(c.name, []).append(f"Me.{c.name}.Items.AddRange(New System.Windows.Forms.ToolStripItem() "
                                            f"{{{', '.join('Me.' + x for x in top)}}})")
    return (create, props), fields
