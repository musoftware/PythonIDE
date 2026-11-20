"""VB6 code -> Python (python-tk or python-qt RAD IDE forms) by rules.

The VB6 source is parsed with the bundled interpreter's parser (radide/runtimes/vbparse.py) and every
statement is emitted as Python.  Controls are accessed with the toolkit's own API (``self.Text1_var.get()``
for Tk, ``self.Text1.text()`` for Qt); VB6 semantics Python lacks (Val, CStr, MsgBox return codes, 1-based
Mid/InStr, file channels, Collection, Err) come from vb6compat.py which is copied into the project.

Everything that is not certain is reported (vbcommon.Notes): "approx" for rules whose behaviour can differ
(On Error Resume Next, twips, ByRef parameters ...) and "manual" for code kept as comments (GoTo, RaiseEvent,
Declare with structures, cross-form control access ...), always with file:line of the original.
"""
from __future__ import annotations

import re

from ..controls import CONTROL_TYPES, FORM_EVENTS, event_args
from ..importers.exe.dotnet import pystr
from ..runtimes import vbparse
from .vbcommon import FormInfo, ModInfo, Notes, ProjectContext, comments_of, event_handler_names, proc_ranges, \
    strip_suffix, vb_event_to_neutral

PY_KEYWORDS = {"and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif",
               "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda",
               "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield", "None",
               "True", "False", "self", "print", "len", "str", "int", "float", "list", "dict", "type",
               "object", "range", "input", "id", "max", "min", "sum", "abs", "round", "open", "file", "e"}

# vb6compat functions with the same name as in VB6 (lower-case VB name -> Python name)
COMPAT_FUNCS = {n.lower(): n for n in (
    "CStr Str Val CInt CLng CByte CDbl CSng CCur CDec CBool CVar CDate Int Fix Round Sgn Sqr Exp Log Sin Cos Tan "
    "Atn Hex Oct IsNumeric IsEmpty IsNull IsArray IsDate Choose RGB QBColor Len Left Right Mid InStr InStrRev "
    "Replace Split Join UCase LCase Trim LTrim RTrim Space String StrReverse StrComp StrConv Chr ChrW Asc AscW "
    "IIf Abs Format FormatNumber FormatCurrency Array UBound LBound MsgBox InputBox DoEvents Beep Shell Now Date Time Timer "
    "Year Month Day Hour Minute Second Weekday DateSerial TimeSerial DateAdd DateDiff Environ Command CurDir "
    "ChDir MkDir RmDir Kill FileCopy FileLen Dir FreeFile EOF LOF Rnd Randomize End").split()}
FUNC_KIND = {"cstr": "str", "str": "str", "val": "num", "cint": "int", "clng": "int", "cbyte": "int", "cdbl": "float",
             "csng": "float", "ccur": "float", "cbool": "bool", "int": "int", "fix": "int", "len": "int",
             "left": "str", "right": "str", "mid": "str", "instr": "int", "instrrev": "int", "replace": "str",
             "split": "list", "join": "str", "ucase": "str", "lcase": "str", "trim": "str", "ltrim": "str",
             "rtrim": "str", "space": "str", "string": "str", "chr": "str", "chrw": "str", "asc": "int",
             "format": "str", "hex": "str", "oct": "str", "isnumeric": "bool", "ubound": "int", "lbound": "int",
             "msgbox": "int", "inputbox": "str", "rnd": "float", "freefile": "int", "eof": "bool", "now": "date",
             "date": "date", "time": "date", "timer": "float", "strreverse": "str", "array": "list",
             "rgb": "int", "sgn": "int", "round": "num", "dir": "str", "environ": "str"}
COMPAT_NAMES = {n.lower(): n for n in (
    "vbCrLf vbNewLine vbCr vbLf vbTab vbNullString vbNullChar vbBack vbOKOnly vbOKCancel vbAbortRetryIgnore "
    "vbYesNoCancel vbYesNo vbRetryCancel vbCritical vbQuestion vbExclamation vbInformation vbDefaultButton1 "
    "vbDefaultButton2 vbDefaultButton3 vbOK vbCancel vbAbort vbRetry vbIgnore vbYes vbNo vbBlack vbRed vbGreen "
    "vbYellow vbBlue vbMagenta vbCyan vbWhite vbUnchecked vbChecked vbGrayed vbModal vbModeless vbBinaryCompare "
    "vbTextCompare vbKeyReturn vbKeyEscape vbKeyBack vbKeyTab vbKeySpace vbKeyDelete vbKeyLeft vbKeyUp "
    "vbKeyRight vbKeyDown vbUpperCase vbLowerCase vbProperCase vbSunday vbMonday App Err").split()}
TYPE_DEFAULT = {"string": '""', "integer": "0", "long": "0", "byte": "0", "single": "0.0", "double": "0.0",
                "currency": "0.0", "decimal": "0.0", "boolean": "False", "date": "None", "variant": "None",
                "object": "None", "longlong": "0", "longptr": "0"}
TYPE_KIND = {"string": "str", "integer": "int", "long": "int", "byte": "int", "longlong": "int", "single": "float",
             "double": "float", "currency": "float", "decimal": "float", "boolean": "bool", "date": "date",
             "collection": "obj"}
DEFAULT_PROP = {"TextBox": "text", "Label": "caption", "CheckBox": "value", "RadioButton": "value",
                "ListBox": "text", "ComboBox": "text", "GroupBox": "caption", "TrackBar": "value",
                "NumericUpDown": "value", "ProgressBar": "value", "Button": "value", "Timer": "enabled",
                "PictureBox": "picture", "Panel": "picture"}
P_OR, P_AND, P_NOT, P_CMP, P_BOR, P_BXOR, P_BAND, P_ADD, P_MUL, P_UNARY, P_POW, P_ATOM = \
    2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 16


class Untranslatable(Exception):
    pass


def type_base(typ: str) -> str:
    t = (typ or "variant").lower()
    if t.startswith("new:"):
        t = t[4:]
    if t.startswith("string*"):
        return "string"
    return t


def code_part(text: str) -> str:
    """The code of a .frm/.cls/.ctl with the header (VERSION, Object=, Begin ... End) blanked out
    (line numbers are kept so that the report can point to the original file)."""
    lines = text.replace("\r\n", "\n").split("\n")
    depth, i, out = 0, 0, []
    started = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        low = s.lower()
        if not started and (low.startswith("version ") or low.startswith("object ") or low.startswith("object=")):
            out.append("")
            continue
        if re.match(r"begin(property)?\b", low):
            depth += 1
            started = True
            out.append("")
            continue
        if depth:
            if re.match(r"end(property)?$", low):
                depth -= 1
            out.append("")
            continue
        if low.startswith("attribute vb_"):
            out.append("")
            continue
        out.append(ln)
    return "\n".join(out)


class PyTranslator:
    """Translate one VB6 code module (form / standard module / class) to Python."""

    def __init__(self, ctx: ProjectContext, toolkit: str, file: str, text: str, notes: Notes,
                 form: FormInfo | None = None, mod: ModInfo | None = None):
        self.ctx, self.qt, self.file = ctx, toolkit == "qt", file
        self.text = text
        self.notes = notes
        self.form = form
        self.mod = mod
        self.kind = mod.kind if mod is not None else ("frm" if form is not None else "bas")
        self.comments = comments_of(text)
        self.done_comments: set[int] = set()
        self.imports: set[str] = set()           # "import X" lines
        self.fields: dict[str, tuple] = {}       # module-level variables: lower -> (display, type, is_array)
        self.consts: dict[str, str] = {}
        self.procs: dict[str, tuple] = {}        # lower -> (display, kind)
        self.stats = {"rules": 0, "approx": 0, "manual": 0}
        # per procedure
        self.locals: dict[str, tuple] = {}
        self.proc = None
        self.with_stack: list[str] = []
        self.tmp = 0
        self.globals_used: set[str] = set()
        self.param_alias: dict[str, str] = {}

    # ------------------------------------------------------------------ helpers
    def note(self, level, line, text):
        self.notes.add(level, self.file, line, text)
        if level in self.stats:
            self.stats[level] += 1

    def spell(self, lower: str, raw: str = "") -> str:
        s = strip_suffix(raw) if raw else self.ctx.spell(lower)
        return s + "_" if s in PY_KEYWORDS else s

    def new_tmp(self, base="_t") -> str:
        self.tmp += 1
        return f"{base}{self.tmp}"

    def comments_before(self, line: int) -> list[str]:
        out = []
        for ln in sorted(k for k in self.comments if k < line and k not in self.done_comments):
            if self.proc_start <= ln:
                text, whole = self.comments[ln]
                if whole:
                    out.append(f"# {text}" if text else "#")
                self.done_comments.add(ln)
        return out

    def trailing(self, line: int) -> str:
        c = self.comments.get(line)
        if c and not c[1] and line not in self.done_comments:
            self.done_comments.add(line)
            return f"  # {c[0]}"
        return ""

    # ------------------------------------------------------------------ resolution
    def ctl(self, lower: str):
        if self.form is None:
            return None
        return self.form.controls.get(lower)

    def ctl_array(self, lower: str):
        if self.form is None:
            return None
        return self.form.arrays.get(lower)

    def var_kind(self, typ: str, is_array=False):
        if is_array:
            return "list"
        return TYPE_KIND.get(type_base(typ))

    def resolve(self, lower: str, raw: str = ""):
        """(code, kind, what) for a bare identifier."""
        if lower in self.param_alias:
            return self.param_alias[lower], None, "local"
        if self.proc is not None and lower == self.proc.name.split(":")[-1] and self.proc.kind in ("function", "get"):
            return "_ret", None, "ret"
        if lower in self.locals:
            disp, typ, arr = self.locals[lower]
            return disp, self.var_kind(typ, arr), "local"
        if self.form is not None:
            c = self.ctl(lower)
            if c is not None:
                return f"self.{c.name}", f"ctl:{c.type}", "control"
            a = self.ctl_array(lower)
            if a is not None:
                return f"self.{a[0]}", "ctlarray", "ctlarray"
        if lower in self.fields:
            disp, typ, arr = self.fields[lower]
            if self.kind == "bas":
                return disp, self.var_kind(typ, arr), "modvar"
            return f"self.{disp}", self.var_kind(typ, arr), "field"
        if lower in self.consts:
            c = self.consts[lower]
            return (c[0], c[1], "const") if isinstance(c, tuple) else (c, None, "const")
        ev = getattr(self, "event_names", {}).get(lower)
        if ev is not None:
            return f"self.{ev[0]}", None, "proc"
        if lower in self.procs:
            disp, pk = self.procs[lower]
            return (disp if self.kind == "bas" else f"self.{disp}"), None,                 ("prop" if pk in ("get", "let", "set") else "proc")
        if lower == "me" or lower == "form":
            return "self", "form", "form"
        if lower in COMPAT_NAMES:
            return COMPAT_NAMES[lower], None, "compat"
        if lower in COMPAT_FUNCS:
            return COMPAT_FUNCS[lower], FUNC_KIND.get(lower), "func"
        # Public members of standard modules
        pm = self.ctx.public_member(lower)
        if pm is not None and (self.mod is None or pm[0] is not self.mod):
            mi, disp, what, typ = pm
            self.imports.add(f"import {mi.name}")
            kind = self.var_kind(typ, what == "array") if what in ("var", "array") else None
            return f"{mi.name}.{disp}", kind, "modproc" if what in ("proc", "declare") else "modmember"
        if lower in self.ctx.forms:
            return self.ctx.forms[lower].name, "formclass", "formclass"
        mi = self.ctx.modules.get(lower)
        if mi is not None:
            if mi.kind == "cls":
                self.imports.add(f"from {mi.name} import {mi.name}")
                return mi.name, "class", "class"
            self.imports.add(f"import {mi.name}")
            return mi.name, "module", "module"
        return self.spell(lower, raw), None, "unknown"

    # ------------------------------------------------------------------ expressions
    def wrap(self, e, need):
        code, _k, prec = e
        return f"({code})" if prec < need else code

    def ex(self, node) -> str:
        return self.exp(node)[0]

    def exp(self, node):
        """(code, kind, precedence)."""
        k = node[0]
        line = node[1]
        if k == "num":
            v = node[2]
            return (repr(v) if isinstance(v, float) else str(v)), ("float" if isinstance(v, float) else "int"), \
                P_ATOM if not str(v).startswith("-") else P_UNARY
        if k == "str":
            return pystr(node[2]), "str", P_ATOM
        if k == "bool":
            return ("True" if node[2] else "False"), "bool", P_ATOM
        if k in ("nothing", "empty"):
            return "None", None, P_ATOM
        if k == "date":
            return f"CDate({pystr(node[2])})", "date", P_ATOM
        if k == "paren":
            code, kind, _p = self.exp(node[2])
            return f"({code})", kind, P_ATOM
        if k == "me":
            return "self", "form", P_ATOM
        if k == "name":
            code, kind, what = self.resolve(node[2], node[3] if len(node) > 3 else "")
            if what == "control":
                c = self.ctl(node[2])
                prop = DEFAULT_PROP.get(c.type)
                if prop:
                    got = self.ctl_get(c, prop, line)
                    return got[0], got[1], P_ATOM
            if what in ("proc", "modproc"):
                return f"{code}()", kind, P_ATOM
            if what == "func" and node[2] in ("now", "date", "time", "timer", "rnd", "freefile", "doevents",
                                              "beep", "command", "curdir", "dir", "randomize", "end"):
                return f"{code}()", kind, P_ATOM
            return code, kind, P_ATOM
        if k == "member":
            return self.member(node)
        if k == "call":
            return self.call(node)
        if k == "binop":
            return self.binop(node)
        if k == "unop":
            op = node[2]
            inner = self.exp(node[3])
            if op == "-":
                return f"-{self.wrap(inner, P_UNARY)}", inner[1], P_UNARY
            if inner[1] == "int":
                return f"~{self.wrap(inner, P_UNARY)}", "int", P_UNARY
            return f"not {self.wrap(inner, P_NOT)}", "bool", P_NOT
        if k == "new":
            cls = node[2].split(".")[-1]
            low = cls.lower()
            if low == "collection":
                return "Collection()", "obj", P_ATOM
            if self.ctx.is_class(low):
                mi = self.ctx.modules[low]
                if self.mod is None or mi is not self.mod:
                    self.imports.add(f"from {mi.name} import {mi.name}")
                return f"{mi.name}()", "obj", P_ATOM
            if low in ("dictionary",):
                return "{}", "dict", P_ATOM
            raise Untranslatable(f"New {node[2]} (COM object)")
        if k == "typeof":
            raise Untranslatable("TypeOf ... Is")
        if k == "withobj":
            if not self.with_stack:
                raise Untranslatable("'.member' outside With")
            return self.with_stack[-1], None, P_ATOM
        if k == "missing":
            return "None", None, P_ATOM
        if k == "named":
            return f"{self.spell(node[2])}={self.ex(node[3])}", None, P_ATOM
        raise Untranslatable(f"expression {k}")

    def as_str(self, e, need=P_ADD + 1) -> str:
        code, kind, _prec = e
        if kind == "str":
            return self.wrap(e, need)
        return f"CStr({code})"

    def binop(self, node):
        op, a, b = node[2], node[3], node[4]
        ea, eb = self.exp(a), self.exp(b)
        if op == "&" or (op == "+" and (ea[1] == "str" or eb[1] == "str")):
            return f"{self.as_str(ea, P_ADD)} + {self.as_str(eb, P_ADD)}", "str", P_ADD
        if op in ("+", "-"):
            kind = "int" if ea[1] == eb[1] == "int" else ("float" if {ea[1], eb[1]} <= {"int", "float"} else None)
            return f"{self.wrap(ea, P_ADD)} {op} {self.wrap(eb, P_ADD + 1)}", kind, P_ADD
        if op == "*":
            kind = "int" if ea[1] == eb[1] == "int" else ("float" if {ea[1], eb[1]} <= {"int", "float"} else None)
            return f"{self.wrap(ea, P_MUL)} * {self.wrap(eb, P_MUL + 1)}", kind, P_MUL
        if op == "/":
            return f"{self.wrap(ea, P_MUL)} / {self.wrap(eb, P_MUL + 1)}", "float", P_MUL
        if op == "\\":
            x = ea[0] if ea[1] == "int" else f"CInt({ea[0]})"
            y = eb[0] if eb[1] == "int" else f"CInt({eb[0]})"
            x = self.wrap((x, "int", ea[2] if ea[1] == "int" else P_ATOM), P_MUL)
            y = self.wrap((y, "int", eb[2] if eb[1] == "int" else P_ATOM), P_MUL + 1)
            return f"{x} // {y}", "int", P_MUL
        if op == "mod":
            return f"{self.wrap(ea, P_MUL)} % {self.wrap(eb, P_MUL + 1)}", "int", P_MUL
        if op == "^":
            return f"{self.wrap(ea, P_POW + 1)} ** {self.wrap(eb, P_POW)}", "float", P_POW
        if op in ("=", "<>", "<", ">", "<=", ">=", "is"):
            pyop = {"=": "==", "<>": "!=", "is": "is"}.get(op, op)
            if op == "is" and b[0] == "nothing":
                return f"{self.wrap(ea, P_CMP + 1)} is None", "bool", P_CMP
            x, y = ea, eb
            # VB compares a number with numeric text as numbers: Text1.Text = 5 -> Val(...) == 5
            if {ea[1], eb[1]} & {"int", "float", "num"} and "str" in (ea[1], eb[1]) and op != "is":
                if ea[1] == "str":
                    x = (f"Val({ea[0]})", "num", P_ATOM)
                else:
                    y = (f"Val({eb[0]})", "num", P_ATOM)
            return f"{self.wrap(x, P_CMP + 1)} {pyop} {self.wrap(y, P_CMP + 1)}", "bool", P_CMP
        if op == "like":
            return f"Like({ea[0]}, {eb[0]})", "bool", P_ATOM
        if op in ("and", "or", "xor"):
            bitwise = ea[1] == "int" or eb[1] == "int"
            if op == "xor":
                if bitwise:
                    return f"{self.wrap(ea, P_BXOR)} ^ {self.wrap(eb, P_BXOR + 1)}", "int", P_BXOR
                return f"bool({ea[0]}) != bool({eb[0]})", "bool", P_CMP
            if bitwise:
                pop, prec = ("&", P_BAND) if op == "and" else ("|", P_BOR)
                return f"{self.wrap(ea, prec)} {pop} {self.wrap(eb, prec + 1)}", "int", prec
            prec = P_AND if op == "and" else P_OR
            return f"{self.wrap(ea, prec)} {op} {self.wrap(eb, prec + 1)}", "bool", prec
        if op in ("eqv", "imp"):
            raise Untranslatable(f"operator {op.capitalize()}")
        raise Untranslatable(f"operator {op}")

    # ------------------------------------------------------------------ objects
    def var_type(self, node) -> str | None:
        """Declared VB type (lower, without New) of a variable node, or None."""
        if node[0] != "name":
            return None
        low = node[2]
        entry = self.locals.get(low) or (self.fields.get(low) if low not in self.locals else None)
        if not entry or entry[2]:
            return None
        return type_base(entry[1] or "")

    def var_class(self, node):
        """ModInfo of the VB6 class a variable is declared with (Dim st As New CStack)."""
        t = self.var_type(node)
        if t and self.ctx.is_class(t):
            return self.ctx.modules[t]
        return None

    def obj_ref(self, node):
        """What *node* refers to as an object: ("control", CtlInfo) | ("element", code, type) |
        ("form",) | ("formclass", name) | ("module", name) | ("class", name) | ("compat", name) | ("expr", e)."""
        k = node[0]
        if k == "me":
            return ("form",)
        if k == "withobj":
            if not self.with_stack:
                raise Untranslatable("'.member' outside With")
            w = self.with_stack[-1]
            if isinstance(w, tuple):
                return w
            return ("expr", (w, None, P_ATOM))
        if k == "name":
            code, kind, what = self.resolve(node[2], node[3] if len(node) > 3 else "")
            if what == "control":
                return ("control", self.ctl(node[2]))
            if what == "form":
                return ("form",)
            if what == "formclass":
                return ("formclass", code)
            if what == "module":
                return ("module", code)
            if what == "class":
                return ("class", code)
            if what == "compat" and code in ("App", "Err"):
                return ("compat", code)
            if node[2] in ("screen", "printer", "clipboard", "debug", "forms"):
                return ("vbglobal", node[2])
            return ("expr", (code, kind, P_ATOM))
        if k == "call" and node[2][0] == "name":
            a = self.ctl_array(node[2][2])
            if a is not None and len(node[3]) == 1 and self.resolve(node[2][2])[2] == "ctlarray":
                idx = self.ex(node[3][0])
                return ("element", f"self.{a[0]}[{idx}]", a[1])
        if k == "member" and node[2][0] == "me":
            c = self.ctl(node[3])
            if c is not None:
                return ("control", c)
            a = self.ctl_array(node[3])
            if a is not None:
                return ("expr", (f"self.{a[0]}", "ctlarray", P_ATOM))
        return ("expr", self.exp(node))

    def member(self, node):
        obj, prop, raw = node[2], node[3], node[4]
        ref = self.obj_ref(obj)
        line = node[1]
        if ref[0] == "control":
            got = self.ctl_get(ref[1], prop, line)
            return got[0], got[1], P_ATOM
        if ref[0] == "element":
            self.note("approx", line, f"control array element property .{raw} read with vb_get()")
            return f"vb_get({ref[1]}, {pystr(raw)})", None, P_ATOM
        if ref[0] == "form":
            if self.form is not None:
                c = self.ctl(prop)
                if c is not None:
                    return self.exp(("name", line, prop, raw))
                if prop in self.fields or prop in self.procs:
                    return self.exp(("name", line, prop, raw))
            return self.form_get(prop, raw, line)
        if ref[0] == "module":
            mi = self.ctx.modules[ref[1].lower()]
            m = mi.members.get(prop)
            disp = m[0] if m else self.spell(prop, raw)
            if m and m[1] in ("proc", "declare"):
                return f"{ref[1]}.{disp}()", None, P_ATOM
            return f"{ref[1]}.{disp}", None, P_ATOM
        if ref[0] == "compat":
            if ref[1] == "App":
                if prop in ("path", "exename", "title", "previnstance", "major", "minor", "revision"):
                    return f"App.{ {'path': 'Path', 'exename': 'EXEName', 'title': 'Title', 'previnstance': 'PrevInstance', 'major': 'Major', 'minor': 'Minor', 'revision': 'Revision'}[prop]}", \
                        ("str" if prop in ("path", "exename", "title") else None), P_ATOM
            if ref[1] == "Err":
                attr = {"number": "Number", "description": "Description", "source": "Source"}.get(prop)
                if attr:
                    return f"Err.{attr}", ("int" if attr == "Number" else "str"), P_ATOM
            raise Untranslatable(f"{ref[1]}.{raw}")
        if ref[0] == "formclass":
            raise Untranslatable(f"access to another form's members ({ref[1]}.{raw})")
        if ref[0] == "vbglobal":
            raise Untranslatable(f"{ref[1].capitalize()}.{raw}")
        if ref[0] == "class":
            raise Untranslatable(f"class member {ref[1]}.{raw}")
        e = ref[1]
        cls = self.var_class(obj)
        if cls is not None:                     # obj.Method of a VB6 class instance: a Function without ()
            m = cls.members.get(prop)
            if m and m[1] == "proc":
                return f"{self.wrap(e, P_ATOM)}.{m[0]}()", None, P_ATOM
            if m:
                return f"{self.wrap(e, P_ATOM)}.{m[0]}", None, P_ATOM
        if e[1] == "ctlarray":
            if prop == "count":
                return f"len({e[0]})", "int", P_ATOM
            if prop in ("ubound", "lbound"):
                return f"{'max' if prop == 'ubound' else 'min'}({e[0]})", "int", P_ATOM
        if e[1] == "obj" and prop == "count":
            return f"{self.wrap(e, P_ATOM)}.Count", "int", P_ATOM
        return f"{self.wrap(e, P_ATOM)}.{self.spell(prop, raw)}", None, P_ATOM

    def form_get(self, prop, raw, line):
        if prop == "caption":
            return ("self.windowTitle()" if self.qt else "self.root.title()"), "str", P_ATOM
        if prop == "name":
            return pystr(self.form.name if self.form else ""), "str", P_ATOM
        if prop in ("width", "height", "left", "top", "scalewidth", "scaleheight"):
            self.note("approx", line, f"Me.{raw} (twips) read from the window size")
            base = prop.replace("scale", "")
            if self.qt:
                fn = {"width": "width()", "height": "height()", "left": "x()", "top": "y()"}[base]
                return f"twips(self.{fn})", "int", P_ATOM
            fn = {"width": "width", "height": "height", "left": "x", "top": "y"}[base]
            return f"twips(self.root.winfo_{fn}())", "int", P_ATOM
        if prop in ("hwnd",):
            return ("int(self.winId())" if self.qt else "self.root.winfo_id()"), "int", P_ATOM
        raise Untranslatable(f"Me.{raw}")

    # ------------------------------------------------------------------ control properties
    def ctl_get(self, c, prop, line):
        """(code, kind) reading VB property *prop* (lower) of control *c*."""
        s, t = f"self.{c.name}", c.type
        q = self.qt
        if prop == "simpletext" and t == "Label":          # MSComctlLib.StatusBar imported as a Label
            prop = "caption"
        if t == "Timer":
            if prop == "enabled":
                return (f"{s}.isActive()" if q else f"{s}.Enabled"), "bool"
            if prop == "interval":
                return (f"{s}.interval()" if q else f"{s}.Interval"), "int"
        if prop in ("text", "caption"):
            if t == "TextBox":
                if c.multiline:
                    return (f"{s}.toPlainText()" if q else f"{s}.get(\"1.0\", \"end-1c\")"), "str"
                return (f"{s}.text()" if q else f"{s}_var.get()"), "str"
            if t == "ComboBox":
                return (f"{s}.currentText()" if q else f"{s}_var.get()"), "str"
            if t == "ListBox":
                if q:
                    return f"({s}.currentItem().text() if {s}.currentItem() else \"\")", "str"
                return f"({s}.get({s}.curselection()[0]) if {s}.curselection() else \"\")", "str"
            if t == "GroupBox":
                return (f"{s}.title()" if q else f"{s}.cget(\"text\")"), "str"
            if t in ("Label", "Button", "CheckBox", "RadioButton", "LinkLabel"):
                return (f"{s}.text()" if q else f"{s}.cget(\"text\")"), "str"
        if prop == "value":
            if t == "CheckBox":
                return (f"int({s}.isChecked())" if q else f"int({s}_var.get())"), "int"
            if t == "RadioButton":
                return (f"{s}.isChecked()" if q else f"(self._radio.get() == {pystr(c.name)})"), "bool"
            if t in ("TrackBar", "NumericUpDown"):
                return (f"{s}.value()" if q else f"{s}_var.get()"), "int"
            if t == "ProgressBar":
                return (f"{s}.value()" if q else f"{s}[\"value\"]"), "int"
            if t == "Button":
                return "False", "bool"
        if prop == "enabled":
            return (f"{s}.isEnabled()" if q else f"(str({s}.cget(\"state\")) != \"disabled\")"), "bool"
        if prop == "visible":
            return (f"{s}.isVisible()" if q else f"bool({s}.winfo_ismapped())"), "bool"
        if prop == "listcount":
            if t == "ListBox":
                return (f"{s}.count()" if q else f"{s}.size()"), "int"
            if t == "ComboBox":
                return (f"{s}.count()" if q else f"len({s}.cget(\"values\"))"), "int"
        if prop == "listindex":
            if t == "ListBox":
                return (f"{s}.currentRow()" if q else f"({s}.curselection()[0] if {s}.curselection() else -1)"), "int"
            if t == "ComboBox":
                return (f"{s}.currentIndex()" if q else f"{s}.current()"), "int"
        if prop in ("min", "max") and t in ("TrackBar", "NumericUpDown", "ProgressBar"):
            if q:
                return f"{s}.{'minimum' if prop == 'min' else 'maximum'}()", "int"
        if prop == "name":
            return pystr(c.array or c.name), "str"
        if prop == "index" and c.array:
            return str(c.index), "int"
        if prop in ("left", "top", "width", "height"):
            self.note("approx", line, f"{c.name}.{prop.capitalize()} in twips (VB6 ScaleMode) - converted from pixels")
        elif prop not in ("tag", "backcolor", "forecolor"):
            self.note("approx", line, f"{c.name}.{self.ctx.spell(prop)} read with the generic helper vb_get()")
        return f"vb_get({s}, {pystr(self.ctx.spell(prop))})", None

    def ctl_set(self, c, prop, v, vkind, line) -> list[str]:
        s, t, q = f"self.{c.name}", c.type, self.qt
        if prop == "simpletext" and t == "Label":          # MSComctlLib.StatusBar imported as a Label
            prop = "caption"
        sv = v if vkind == "str" else f"CStr({v})"
        lit = v in ("True", "False")
        if t == "Timer":
            if prop == "enabled":
                if q:
                    if lit:
                        return [f"{s}.{'start' if v == 'True' else 'stop'}()"]
                    return [f"{s}.start() if {v} else {s}.stop()"]
                return [f"{s}.Enabled = {v}"]
            if prop == "interval":
                return [f"{s}.setInterval(int({v}))" if q else f"{s}.Interval = {v}"]
        if prop in ("text", "caption"):
            if t == "TextBox":
                if c.multiline:
                    return [f"{s}.setPlainText({sv})"] if q else \
                        [f"{s}.delete(\"1.0\", \"end\")", f"{s}.insert(\"1.0\", {sv})"]
                return [f"{s}.setText({sv})" if q else f"{s}_var.set({v})"]
            if t == "ComboBox":
                return [f"{s}.setCurrentText({sv})" if q else f"{s}_var.set({v})"]
            if t == "GroupBox":
                return [f"{s}.setTitle({sv})" if q else f"{s}.config(text={v})"]
            if t in ("Label", "Button", "CheckBox", "RadioButton", "LinkLabel"):
                return [f"{s}.setText({sv})" if q else f"{s}.config(text={v})"]
        if prop == "value":
            if t == "CheckBox":
                return [f"{s}.setChecked(bool({v}))" if q else f"{s}_var.set(bool({v}))"]
            if t == "RadioButton":
                if q:
                    return [f"{s}.setChecked(bool({v}))"]
                return [f"self._radio.set({pystr(c.name)})"] if v == "True" else \
                    [f"if {v}:", f"    self._radio.set({pystr(c.name)})"]
            if t in ("TrackBar", "NumericUpDown"):
                return [f"{s}.setValue(int({v}))" if q else f"{s}_var.set({v})"]
            if t == "ProgressBar":
                return [f"{s}.setValue(int({v}))" if q else f"{s}[\"value\"] = {v}"]
            if t == "Button":
                return [f"{s}.click()" if q else f"{s}.invoke()"] if v == "True" else \
                    [f"if {v}:", f"    {s}.{'click' if q else 'invoke'}()"]
        if prop == "enabled":
            if q:
                return [f"{s}.setEnabled(bool({v}))" if not lit else f"{s}.setEnabled({v})"]
            if lit:
                return [f"{s}.config(state={pystr('normal' if v == 'True' else 'disabled')})"]
            return [f"{s}.config(state=\"normal\" if {v} else \"disabled\")"]
        if prop == "visible":
            if q:
                return [f"{s}.setVisible(bool({v}))" if not lit else f"{s}.setVisible({v})"]
            if lit:
                return [f"{s}.place(**self._places[{pystr(c.name)}])" if v == "True" else f"{s}.place_forget()"]
            return [f"if {v}:", f"    {s}.place(**self._places[{pystr(c.name)}])", "else:", f"    {s}.place_forget()"]
        if prop == "listindex":
            if t == "ListBox":
                if q:
                    return [f"{s}.setCurrentRow(int({v}))"]
                return [f"vb_set({s}, \"ListIndex\", {v})"]
            if t == "ComboBox":
                return [f"{s}.setCurrentIndex(int({v}))" if q else f"{s}.current({v})"]
        if prop in ("backcolor", "forecolor"):
            if not q:
                return [f"{s}.config({'bg' if prop == 'backcolor' else 'fg'}=to_css({v}))"]
        if prop in ("min", "max") and t in ("TrackBar", "NumericUpDown", "ProgressBar") and q:
            return [f"{s}.{'setMinimum' if prop == 'min' else 'setMaximum'}(int({v}))"]
        if prop in ("left", "top", "width", "height"):
            self.note("approx", line, f"{c.name}.{prop.capitalize()} in twips (VB6 ScaleMode) - converted to pixels")
        elif prop not in ("tag", "backcolor", "forecolor"):
            self.note("approx", line, f"{c.name}.{self.ctx.spell(prop)} set with the generic helper vb_set()")
        return [f"vb_set({s}, {pystr(self.ctx.spell(prop))}, {v})"]

    def ctl_method(self, c, method, args, line):
        """Code (expression) of control method call c.Method args."""
        s, t, q = f"self.{c.name}", c.type, self.qt
        a = [self.exp(x) for x in args]
        if method == "additem":
            item = a[0][0] if a[0][1] == "str" else f"CStr({a[0][0]})"
            if len(a) > 1:
                return f"vb_call({s}, \"AddItem\", {item}, {a[1][0]})"
            if q:
                return f"{s}.addItem({item})"
            if t == "ComboBox":
                return f"{s}.config(values=(*{s}.cget(\"values\"), {item}))"
            return f"{s}.insert(\"end\", {item})"
        if method == "removeitem":
            if q:
                return f"{s}.takeItem({a[0][0]})" if t == "ListBox" else f"{s}.removeItem({a[0][0]})"
            return f"{s}.delete({a[0][0]})" if t == "ListBox" else f"vb_call({s}, \"RemoveItem\", {a[0][0]})"
        if method == "clear":
            if q:
                return f"{s}.clear()"
            if t == "ListBox":
                return f"{s}.delete(0, \"end\")"
            if t == "ComboBox":
                return f"{s}.config(values=())"
            if t == "TextBox":
                return f"{s}.delete(\"1.0\", \"end\")" if c.multiline else f"{s}_var.set(\"\")"
        if method == "setfocus":
            return f"{s}.setFocus()" if q else f"{s}.focus_set()"
        if method == "refresh":
            return f"{s}.update()" if q else f"{s}.update_idletasks()"
        if method == "list" and len(a) == 1:
            if q:
                return f"{s}.item({a[0][0]}).text()" if t == "ListBox" else f"{s}.itemText({a[0][0]})"
            return f"{s}.get({a[0][0]})" if t == "ListBox" else f"{s}.cget(\"values\")[{a[0][0]}]"
        if method == "selected" and len(a) == 1 and t == "ListBox":
            return f"{s}.item({a[0][0]}).isSelected()" if q else f"{s}.selection_includes({a[0][0]})"
        if method == "zorder":
            return f"{s}.raise_()" if q else f"{s}.lift()"
        if method == "move":
            props = ["Left", "Top", "Width", "Height"]
            self.note("approx", line, f"{c.name}.Move (twips) converted to pixels")
            return "; ".join(f"vb_set({s}, \"{props[i]}\", {x[0]})" for i, x in enumerate(a[:4]))
        self.note("approx", line, f"{c.name}.{self.ctx.spell(method)} called with the generic helper vb_call()")
        return f"vb_call({s}, {pystr(self.ctx.spell(method))}{''.join(', ' + x[0] for x in a)})"

    # ------------------------------------------------------------------ calls
    def args_code(self, args) -> str:
        return ", ".join(self.ex(a) for a in args)

    def call(self, node):
        func, args, line = node[2], node[3], node[1]
        if func[0] == "name":
            low = func[2]
            code, kind, what = self.resolve(low, func[3] if len(func) > 3 else "")
            if what == "func":
                return self.builtin(low, args, line)
            if what in ("proc", "modproc", "class"):
                return f"{code}({self.args_code(args)})", None, P_ATOM
            if what == "ctlarray":
                a = self.ctl_array(low)
                if len(args) == 1:
                    elem = f"self.{a[0]}[{self.ex(args[0])}]"
                    prop = DEFAULT_PROP.get(a[1])
                    if prop:
                        return f"vb_get({elem}, {pystr(prop.capitalize())})", None, P_ATOM
                    return elem, None, P_ATOM
            if what in ("local", "field", "modvar") and args and self.var_type(func) == "collection":
                return f"{code}({self.args_code(args)})", None, P_ATOM      # Collection: c(2) / c("key")
            if what in ("local", "field", "modvar", "modmember", "ret", "unknown") and args:
                if what == "ret":
                    # recursive call of the function itself
                    disp = self.procs.get(low, (self.spell(low),))[0]
                    return (f"{disp}({self.args_code(args)})" if self.kind == "bas"
                            else f"self.{disp}({self.args_code(args)})"), None, P_ATOM
                if what == "unknown" and not (kind == "list"):
                    self.note("approx", line, f"'{self.spell(low)}' is not declared in the project - "
                                              "translated as a function call")
                    return f"{code}({self.args_code(args)})", None, P_ATOM
                idx = "".join(f"[{self.ex(a)}]" for a in args)
                return f"{code}{idx}", None, P_ATOM
            return f"{code}({self.args_code(args)})", None, P_ATOM
        if func[0] == "member":
            obj, method, raw = func[2], func[3], func[4]
            ref = self.obj_ref(obj)
            if ref[0] == "control":
                return self.ctl_method(ref[1], method, args, line), None, P_ATOM
            if ref[0] == "element":
                self.note("approx", line, f"control array element method .{raw} called with vb_call()")
                return f"vb_call({ref[1]}, {pystr(raw)}{''.join(', ' + self.ex(a) for a in args)})", None, P_ATOM
            if ref[0] == "form":
                if self.form is not None and (method in self.procs):
                    return f"self.{self.procs[method][0]}({self.args_code(args)})", None, P_ATOM
                return self.form_method(method, raw, args, line), None, P_ATOM
            if ref[0] == "formclass":
                raise Untranslatable(f"{ref[1]}.{raw} used in an expression")
            if ref[0] == "module":
                mi = self.ctx.modules[ref[1].lower()]
                m = mi.members.get(method)
                disp = m[0] if m else self.spell(method, raw)
                if m and m[1] in ("var", "array"):
                    return f"{ref[1]}.{disp}" + "".join(f"[{self.ex(a)}]" for a in args), None, P_ATOM
                return f"{ref[1]}.{disp}({self.args_code(args)})", None, P_ATOM
            if ref[0] == "compat":
                if ref[1] == "Err" and method in ("raise", "clear"):
                    return f"Err.{method.capitalize()}({self.args_code(args)})", None, P_ATOM
                raise Untranslatable(f"{ref[1]}.{raw}")
            if ref[0] == "vbglobal":
                if ref[1] == "clipboard":
                    if method == "settext":
                        return (f"QApplication.clipboard().setText({self.ex(args[0])})" if self.qt else
                                f"(self.root.clipboard_clear(), self.root.clipboard_append({self.ex(args[0])}))"), \
                            None, P_ATOM
                    if method == "gettext":
                        return ("QApplication.clipboard().text()" if self.qt else "self.root.clipboard_get()"), \
                            "str", P_ATOM
                    if method == "clear":
                        return ("QApplication.clipboard().clear()" if self.qt else "self.root.clipboard_clear()"), \
                            None, P_ATOM
                raise Untranslatable(f"{ref[1].capitalize()}.{raw}")
            if ref[0] == "class":
                raise Untranslatable(f"{ref[1]}.{raw}")
            e = ref[1]
            if e[1] == "obj" and method == "item":
                return f"{self.wrap(e, P_ATOM)}.Item({self.args_code(args)})", None, P_ATOM
            return f"{self.wrap(e, P_ATOM)}.{self.spell(method, raw)}({self.args_code(args)})", None, P_ATOM
        # a(i)(j) / obj(i).x
        inner = self.exp(func)
        return f"{self.wrap(inner, P_ATOM)}" + "".join(f"[{self.ex(a)}]" for a in args), None, P_ATOM

    def builtin(self, low, args, line):
        a = [self.exp(x) for x in args]
        name = COMPAT_FUNCS[low]
        kind = FUNC_KIND.get(low)
        if low == "iif" and len(a) == 3:
            return f"({a[1][0]} if {a[0][0]} else {a[2][0]})", None, P_ATOM
        if low == "len" and a and a[0][1] == "str":
            return f"len({a[0][0]})", "int", P_ATOM
        if low in ("ucase", "lcase") and a and a[0][1] == "str":
            return f"{self.wrap(a[0], P_ATOM)}.{'upper' if low == 'ucase' else 'lower'}()", "str", P_ATOM
        if low == "left" and a and a[0][1] == "str" and len(a) == 2:
            return f"{self.wrap(a[0], P_ATOM)}[:{a[1][0]}]", "str", P_ATOM
        if low == "abs":
            return f"abs({a[0][0]})", None, P_ATOM
        if low == "msgbox":
            if any(x[0] == "named" for x in args):
                raise Untranslatable("MsgBox with named arguments")
        if low == "end":
            return "End()", None, P_ATOM
        return f"{name}({', '.join(x[0] for x in a)})", kind, P_ATOM

    def form_method(self, method, raw, args, line):
        q = self.qt
        if method == "hide":
            return "self.hide()" if q else "self.root.withdraw()"
        if method == "show":
            return "self.show()" if q else "self.root.deiconify()"
        if method in ("refresh", "repaint"):
            return "self.update()" if q else "self.root.update_idletasks()"
        if method == "move":
            raise Untranslatable("Me.Move")
        if method == "setfocus":
            return "self.activateWindow()" if q else "self.root.focus_force()"
        if method == "cls":
            raise Untranslatable("Me.Cls (form graphics)")
        if method == "print":
            self.note("approx", line, "Me.Print (text drawn on the form) written to the console with print()")
            return f"print({self.args_code(args)})"
        raise Untranslatable(f"Me.{raw}")

    def other_form_lines(self, form, method, raw, args, line) -> list[str]:
        """Form2.Show [vbModal] / Form2.Hide as statements (the instance is kept in self._Form2)."""
        fv = f"self._{form}"
        if method == "show":
            modal = bool(args) and self.ex(args[0]) in ("vbModal", "1")
            out = [f"from {form} import {form}"]
            if self.qt:
                out.append(f"{fv} = {form}()")
                if modal:
                    out += ["from PySide6.QtCore import Qt",
                            f"{fv}.setWindowModality(Qt.WindowModality.ApplicationModal)"]
                out.append(f"{fv}.show()")
            else:
                out.append(f"{fv} = {form}(self.root)")
                if modal:
                    out.append(f"self.root.wait_window({fv}.root)")
            if modal:
                self.note("approx", line, f"{form}.Show vbModal: the code after Show continues when the window "
                                          f"closes ({'application-modal window' if self.qt else 'wait_window'})")
            return out
        if method == "hide":
            return [f"if getattr(self, {pystr('_' + form)}, None) is not None:",
                    f"    {fv}.{'hide()' if self.qt else 'root.withdraw()'}"]
        raise Untranslatable(f"{form}.{raw}")

    # ------------------------------------------------------------------ statements
    def block(self, stmts) -> list[str]:
        out = []
        for s in stmts:
            out += self.stmt(s)
        return out or ["pass"]

    def stmt(self, s) -> list[str]:
        line = s[1]
        pre = self.comments_before(line)
        try:
            lines = self._stmt(s)
            if s[0] not in ("nop", "label", "if", "select", "for", "foreach", "do", "with"):
                self.stats["rules"] += 1
        except Untranslatable as e:
            lines = self.manual(s, str(e))
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            lines = self.manual(s, f"unsupported construct ({type(e).__name__}: {e})")
        if lines:
            lines[0] += self.trailing(line)
        return pre + lines

    def src_line(self, line: int) -> str:
        lines = self.text.replace("\r\n", "\n").split("\n")
        return lines[line - 1].strip() if 0 < line <= len(lines) else ""

    def manual(self, s, why) -> list[str]:
        line = s[1]
        src = self.src_line(line)
        self.note("manual", line, f"{why}: `{src}`")
        self.stats["manual"] += 1
        return [f"# TODO (VB6, {self.file}:{line}): {src}", f"pass  # not translated: {why}"]

    def assign_target(self, target, value, line) -> list[str]:
        e = self.exp(value)
        v, vkind = e[0], e[1]
        k = target[0]
        if k == "name":
            low = target[2]
            code, kind, what = self.resolve(low, target[3] if len(target) > 3 else "")
            if what == "control":
                c = self.ctl(low)
                prop = DEFAULT_PROP.get(c.type, "text")
                return self.ctl_set(c, prop, v, vkind, line)
            if what in ("proc", "modproc", "func", "compat", "formclass", "module", "class"):
                raise Untranslatable(f"assignment to {what} '{code}'")
            typ = None
            if what == "local":
                typ = self.locals.get(low, (None, None, False))
                typ = None if typ[2] else typ[1]
            elif what in ("field", "modvar"):
                f = self.fields[low]
                typ = None if f[2] else f[1]
                if what == "modvar":
                    self.globals_used.add(code)
            elif what == "ret":
                typ = getattr(self.proc, "_ret_type", None)
            elif what == "unknown":
                self.locals[low] = (code, "variant", False)
            if low in self.param_alias and self.param_alias[low] == "e.Cancel":
                return [f"e.Cancel = {v}" if v in ("True", "False") else f"e.Cancel = bool({v})"]
            return [f"{code} = {self.convert_to(typ, e)}"]
        if k == "member":
            obj, prop, raw = target[2], target[3], target[4]
            ref = self.obj_ref(obj)
            if ref[0] == "control":
                return self.ctl_set(ref[1], prop, v, vkind, line)
            if ref[0] == "element":
                self.note("approx", line, f"control array element property .{raw} set with vb_set()")
                return [f"vb_set({ref[1]}, {pystr(raw)}, {v})"]
            if ref[0] == "form":
                if self.form is not None and (self.ctl(prop) or prop in self.fields):
                    return self.assign_target(("name", line, prop, raw), value, line)
                if prop == "caption":
                    sv = v if vkind == "str" else f"CStr({v})"
                    return [f"self.setWindowTitle({sv})" if self.qt else f"self.root.title({v})"]
                if prop == "backcolor":
                    return [f"vb_set(self, \"BackColor\", {v})" if self.qt else f"self.root.config(bg=to_css({v}))"]
                if prop in ("width", "height"):
                    self.note("approx", line, f"Me.{raw} (twips) set as the window size in pixels")
                    if self.qt:
                        return [f"self.resize({'px(' + v + ')' if prop == 'width' else 'self.width()'}, "
                                f"{'px(' + v + ')' if prop == 'height' else 'self.height()'})"]
                    w = f"px({v})" if prop == "width" else "self.root.winfo_width()"
                    h = f"px({v})" if prop == "height" else "self.root.winfo_height()"
                    return [f"self.root.geometry(f\"{{{w}}}x{{{h}}}\")"]
                raise Untranslatable(f"Me.{raw} =")
            if ref[0] == "module":
                mi = self.ctx.modules[ref[1].lower()]
                m = mi.members.get(prop)
                return [f"{ref[1]}.{m[0] if m else self.spell(prop, raw)} = {v}"]
            if ref[0] == "compat" and ref[1] == "App" and prop == "title":
                return [f"App.Title = {v}"]
            if ref[0] in ("formclass",):
                raise Untranslatable(f"setting a property of another form ({ref[1]}.{raw})")
            if ref[0] in ("vbglobal", "compat", "class"):
                raise Untranslatable(f"{ref[1]}.{raw} =")
            return [f"{self.wrap(ref[1], P_ATOM)}.{self.spell(prop, raw)} = {v}"]
        if k == "call":
            func = target[2]
            if func[0] == "name":
                low = func[2]
                code, kind, what = self.resolve(low)
                if what == "ctlarray" and len(target[3]) == 1:
                    a = self.ctl_array(low)
                    prop = DEFAULT_PROP.get(a[1], "text")
                    self.note("approx", line, f"control array {a[0]}(i) default property set with vb_set()")
                    return [f"vb_set(self.{a[0]}[{self.ex(target[3][0])}], {pystr(prop.capitalize())}, {v})"]
                if what in ("local", "field", "modvar", "modmember", "unknown"):
                    if what == "modvar":
                        self.globals_used.add(code)
                    idx = "".join(f"[{self.ex(a)}]" for a in target[3])
                    return [f"{code}{idx} = {v}"]
                if low == "mid":
                    raise Untranslatable("Mid statement")
            if func[0] == "member" and func[3] == "list":
                ref = self.obj_ref(func[2])
                if ref[0] == "control":
                    raise Untranslatable(f"{ref[1].name}.List(i) = ...")
            inner = self.ex(target)
            return [f"{inner} = {v}"]
        raise Untranslatable("assignment target")

    def convert_to(self, typ, e) -> str:
        """VB converts a value to the declared type on assignment (n = Text1.Text)."""
        code, kind, _p = e
        if typ is None:
            return code
        base = type_base(typ)
        tk = TYPE_KIND.get(base)
        if tk == "int" and kind not in ("int",):
            return f"CInt({code})"
        if tk == "float" and kind not in ("int", "float", "num"):
            return f"CDbl({code})"
        if tk == "str" and kind != "str":
            return f"CStr({code})"
        if tk == "bool" and kind not in ("bool",):
            return f"CBool({code})"
        return code

    def default_value(self, typ, bounds, line):
        base = type_base(typ)
        if typ and typ.lower().startswith("new:"):
            init = self.exp(("new", line, typ[4:]))[0]
        elif base in TYPE_DEFAULT:
            init = TYPE_DEFAULT[base]
        elif base == "collection":
            init = "None"
        elif self.udt(base):
            init = f"{self.udt(base)}()"
        else:
            init = "None"
        if bounds is None:
            return init
        if not bounds:
            return "[]"
        uppers = []
        for lo, hi in bounds:
            if lo is not None:
                lo_code = self.ex(lo)
                if lo_code not in ("0", "1"):
                    self.note("approx", line, f"array lower bound {lo_code} - Python lists start at 0")
            uppers.append(self.ex(hi))
        if len(uppers) == 1 and init in ('""', "0", "0.0", "False", "None"):
            u = uppers[0]
            n = str(int(u) + 1) if u.isdigit() else f"{u} + 1"
            return f"[{init}] * ({n})"
        return f"dim_array({init}, {', '.join(uppers)})" if init in ('""', "0", "0.0", "False", "None") else \
            f"[{init} for _ in range({uppers[0]} + 1)]"

    def udt(self, base: str):
        for mi in self.ctx.modules.values():
            m = mi.members.get(base)
            if m and m[1] == "type":
                if mi is not self.mod:
                    self.imports.add(f"from {mi.name} import {m[0]}")
                return m[0]
        return None

    def _stmt(self, s) -> list[str]:
        k, line = s[0], s[1]
        q = self.qt
        if k == "nop":
            return []
        if k in ("assign", "set"):
            return self.assign_target(s[2], s[3], line)
        if k == "callstmt":
            call = s[2]
            func, args = call[2], call[3]
            if func[0] == "member" and func[2][0] == "name":
                ref = self.obj_ref(func[2])
                if ref[0] == "formclass":
                    return self.other_form_lines(ref[1], func[3], func[4], args, line)
            if func[0] == "name":
                low = func[2]
                code, kind, what = self.resolve(low)
                if what == "func" and low in COMPAT_FUNCS:
                    return [self.builtin(low, args, line)[0]]
                if what == "control":
                    raise Untranslatable("control used as a statement")
                if what in ("local", "field", "modvar") and not args:
                    return [code]
            return [self.exp(call)[0]]
        if k in ("dim", "static"):
            out = []
            for nm, bounds, typ in s[2]:
                disp = self.spell(nm)
                self.locals[nm] = (disp, typ, bounds is not None)
                if k == "static":
                    self.note("approx", line, f"Static {disp} became a normal local variable (its value is not "
                                              "kept between calls)")
                out.append(f"{disp} = {self.default_value(typ, bounds, line)}")
            return out
        if k == "const":
            out = []
            for nm, e in s[2]:
                disp = self.spell(nm)
                self.locals[nm] = (disp, "variant", False)
                out.append(f"{disp} = {self.ex(e)}")
            return out
        if k == "redim":
            out = []
            for nm, bounds, typ in s[2]:
                code, kind, what = self.resolve(nm)
                if what == "unknown":
                    self.locals[nm] = (code, typ, True)
                elif what == "modvar":
                    self.globals_used.add(code)
                init = TYPE_DEFAULT.get(type_base(typ), "None")
                uppers = ", ".join(self.ex(hi) for _lo, hi in bounds or [])
                if s[3]:
                    out.append(f"{code} = redim({code}, {init}, {uppers}, preserve=True)")
                else:
                    out.append(f"{code} = dim_array({init}, {uppers})")
            return out
        if k == "if":
            out = []
            for i, (cond, body) in enumerate(s[2]):
                c = self.cond(cond)
                out.append(f"{'if' if i == 0 else 'elif'} {c}:")
                out += self.indent(self.block(body))
            if s[3]:
                out.append("else:")
                out += self.indent(self.block(s[3]))
            return out
        if k == "select":
            subj = self.exp(s[2])
            out = []
            if re.fullmatch(r"[\w.]+", subj[0]) and "(" not in subj[0]:
                var = subj[0]
            else:
                var = self.new_tmp("_sel")
                out.append(f"{var} = {subj[0]}")
            for i, (tests, body) in enumerate(s[3]):
                conds = []
                for t in tests:
                    if t[0] == "eq":
                        v = self.exp(t[1])
                        conds.append(f"{var} == {self.wrap(v, P_CMP + 1)}")
                    elif t[0] == "range":
                        conds.append(f"{self.wrap(self.exp(t[1]), P_CMP + 1)} <= {var} <= "
                                     f"{self.wrap(self.exp(t[2]), P_CMP + 1)}")
                    else:
                        op = {"=": "==", "<>": "!="}.get(t[1], t[1])
                        conds.append(f"{var} {op} {self.wrap(self.exp(t[2]), P_CMP + 1)}")
                out.append(f"{'if' if i == 0 else 'elif'} {' or '.join(conds)}:")
                out += self.indent(self.block(body))
            if s[4]:
                out.append("else:" if s[3] else "if True:")
                out += self.indent(self.block(s[4]))
            return out
        if k == "for":
            var, start, stop, step, body = s[2], s[3], s[4], s[5], s[6]
            code, kind, what = self.resolve(var)
            if what == "unknown":
                self.locals[var] = (code, "long", False)
            elif what == "modvar":
                self.globals_used.add(code)
            a, b = self.exp(start), self.exp(stop)
            if step is None:
                stepc, stepk = "1", "int"
            else:
                se = self.exp(step)
                stepc, stepk = se[0], se[1]
            ints = a[1] in ("int", None, "num") and b[1] in ("int", None, "num") and stepk == "int"
            if ints and re.fullmatch(r"-?\d+", stepc):
                st = int(stepc)
                bb = b[0]
                if re.fullmatch(r"-?\d+", bb):
                    end = str(int(bb) + (1 if st > 0 else -1))
                elif st > 0 and bb.endswith(" - 1") and b[2] == P_ADD:
                    end = bb[:-4]
                else:
                    end = f"{self.wrap(b, P_ADD)} {'+' if st > 0 else '-'} 1"
                if a[1] != "int" or b[1] != "int":
                    if not re.fullmatch(r"-?\d+", a[0]):
                        a = (f"int({a[0]})", "int", P_ATOM)
                    if not re.fullmatch(r"-?\d+", bb):
                        end = f"int({b[0]}) {'+' if st > 0 else '-'} 1"
                rng = f"range({a[0]}, {end})" if st == 1 else f"range({a[0]}, {end}, {st})"
                head = f"for {code} in {rng}:"
            else:
                head = f"for {code} in vb_for({a[0]}, {b[0]}, {stepc}):"
            return [head] + self.indent(self.block(body))
        if k == "foreach":
            var, coll, body = s[2], s[3], s[4]
            code, kind, what = self.resolve(var)
            if what == "unknown":
                self.locals[var] = (code, "variant", False)
            ce = self.exp(coll)
            src = f"{ce[0]}.values()" if ce[1] == "ctlarray" else ce[0]
            return [f"for {code} in {src}:"] + self.indent(self.block(body))
        if k == "do":
            pre, post, body = s[2], s[3], s[4]
            inner = self.block(body)
            if pre is not None:
                c = self.cond(pre[1])
                head = f"while {c}:" if pre[0] == "while" else f"while not ({c}):"
                out = [head] + self.indent(inner)
            else:
                out = ["while True:"] + self.indent(inner if inner != ["pass"] else [])
                if post is not None:
                    c = self.cond(post[1])
                    out += self.indent([f"if not ({c}):" if post[0] == "while" else f"if {c}:", "    break"])
                elif inner == ["pass"]:
                    out.append("    pass")
            return out
        if k == "with":
            ref = self.obj_ref(s[2])
            out = []
            if ref[0] in ("control", "element", "form", "module", "compat", "formclass", "vbglobal", "class"):
                self.with_stack.append(ref)
            else:
                code = ref[1][0]
                if re.fullmatch(r"[\w.]+", code):
                    self.with_stack.append(code)
                else:
                    t = self.new_tmp("_w")
                    out.append(f"{t} = {code}")
                    self.with_stack.append(t)
            try:
                out += self.block(s[3])
            finally:
                self.with_stack.pop()
            return out
        if k == "exit":
            what = s[2]
            if what in ("for", "do"):
                return ["break"]
            if what in ("sub", "property"):
                return ["return"] if self.proc is None or self.proc.kind not in ("function", "get") else \
                    ["return _ret"]
            if what == "function":
                return ["return _ret"]
            raise Untranslatable(f"Exit {what}")
        if k == "end":
            return ["End()"]
        if k == "stop":
            self.note("approx", line, "Stop became breakpoint()")
            return ["breakpoint()"]
        if k == "unload":
            tgt = s[2]
            if tgt[0] == "me" or (tgt[0] == "name" and self.form is not None and tgt[2] == self.form.name.lower()):
                return ["self.close()" if q else "self.root.destroy()"]
            if tgt[0] == "name" and tgt[2] in self.ctx.forms:
                f = self.ctx.forms[tgt[2]].name
                self.note("approx", line, f"Unload {f}: closes the instance this form opened with {f}.Show")
                return [f"if getattr(self, {pystr('_' + f)}, None) is not None:",
                        f"    self._{f}.{'close()' if q else 'root.destroy()'}"]
            raise Untranslatable("Unload of a control array element")
        if k == "loadform":
            raise Untranslatable("Load (form / control array element)")
        if k == "debugprint":
            items = [self.exp(a) for a in s[3]]
            if not items:
                return ["print()"]
            if len(items) == 1:
                return [f"print({items[0][0]})"]
            return ["print(" + " + ".join(self.as_str(x) for x in items) + ")"]
        if k == "open":
            path, mode, num = self.ex(s[2]), s[3], self.ex(s[5])
            if mode in ("binary", "random"):
                self.note("approx", line, f"Open For {mode.capitalize()}: Get/Put are not translated")
            return [f"FileOpen({num}, {path}, {pystr(mode)})"]
        if k == "close":
            return [f"FileClose({', '.join(self.ex(n) for n in s[2])})"]
        if k == "fprint":
            num = self.ex(s[2])
            items = s[3]
            parts = []
            newline = True
            for i, (e, sep) in enumerate(items):
                parts.append(f"({self.ex(e) if e is not None else 'None'}, {pystr(sep)})")
                if i == len(items) - 1 and sep in (";", ","):
                    newline = False
            return [f"FilePrint({num}{''.join(', ' + p for p in parts)}{'' if newline else ', newline=False'})"]
        if k == "fwrite":
            num = self.ex(s[2])
            vals = [self.ex(e) for e, _sep in s[3] if e is not None]
            return [f"FileWrite({num}{''.join(', ' + v for v in vals)})"]
        if k == "flineinput":
            num = self.ex(s[2])
            return self.assign_raw(s[3], f"LineInput({num})", "str", line)
        if k == "finput":
            num = self.ex(s[2])
            out = []
            for t in s[3]:
                out += self.assign_raw(t, f"FileInput({num})", None, line)
            return out
        if k == "rename":
            return [f"Name({self.ex(s[2])}, {self.ex(s[3])})"]
        if k == "errorstmt":
            return [f"Err.Raise({self.ex(s[2])})"]
        if k == "erase":
            out = []
            for nm in s[2]:
                code = self.resolve(nm)[0]
                out.append(f"{code} = [type(x)() if x is not None else None for x in {code}]")
            self.note("approx", line, "Erase: array elements reset to their empty value")
            return out
        if k == "label":
            return []
        if k in ("goto", "gosub", "return", "ongoto"):
            raise Untranslatable(f"{k.capitalize()} (no equivalent in Python - restructure the code)")
        if k == "resume":
            raise Untranslatable("Resume outside an error handler")
        if k == "onerror":
            raise Untranslatable("On Error inside a block")
        if k == "raiseevent":
            raise Untranslatable("RaiseEvent (class events)")
        if k in ("fget", "fput", "fseek"):
            raise Untranslatable("binary/random file access (Get/Put/Seek)")
        raise Untranslatable(f"statement {k}")

    def assign_raw(self, target, code, kind, line) -> list[str]:
        if target[0] == "name":
            low = target[2]
            c, k2, what = self.resolve(low)
            if what == "control":
                return self.ctl_set(self.ctl(low), DEFAULT_PROP.get(self.ctl(low).type, "text"), code, kind, line)
            if what == "unknown":
                self.locals[low] = (c, "variant", False)
            if what == "modvar":
                self.globals_used.add(c)
            typ = None
            if what == "local":
                typ = self.locals[low][1]
            elif what in ("field", "modvar"):
                typ = self.fields[low][1]
            return [f"{c} = {self.convert_to(typ, (code, kind, P_ATOM))}"]
        if target[0] == "member":
            ref = self.obj_ref(target[2])
            if ref[0] == "control":
                return self.ctl_set(ref[1], target[3], code, kind, line)
        return [f"{self.ex(target)} = {code}"]

    def cond(self, node) -> str:
        e = self.exp(node)
        return e[0]

    @staticmethod
    def indent(lines, n=1) -> list[str]:
        pad = "    " * n
        return [pad + ln if ln else ln for ln in lines]

    # ------------------------------------------------------------------ procedures
    def proc_body(self, proc, prelude: list[str]) -> list[str]:
        """Python body lines of a procedure (On Error handled at the top level)."""
        body = list(proc.body)
        out = list(prelude)
        if proc.kind in ("function", "get"):
            out.append(f"_ret = {TYPE_DEFAULT.get(type_base(getattr(proc, '_ret_type', None) or 'variant'), 'None')}")
        # On Error at the top level of the procedure
        i_err = next((i for i, st in enumerate(body) if st[0] == "onerror"), None)
        if i_err is None:
            out += self.block(body) if body else []
        else:
            st = body[i_err]
            out += [ln for s2 in body[:i_err] for ln in self.stmt(s2)]
            rest = body[i_err + 1:]
            if st[2] == "next":
                self.note("approx", st[1], "On Error Resume Next: each following statement is wrapped in "
                                           "try/except (errors inside a block skip the rest of that block)")
                for s2 in rest:
                    lines = self.stmt(s2)
                    if not lines or all(ln.lstrip().startswith("#") for ln in lines) or s2[0] in ("dim", "const",
                                                                                                  "label", "nop"):
                        out += lines
                        continue
                    out += ["try:"] + self.indent(lines) + ["except Exception as _e:  # On Error Resume Next",
                                                           "    Err.set(_e)"]
            elif st[2] == "0":
                out += self.block(rest)
            else:
                label = st[2]
                j = next((j for j, s2 in enumerate(rest) if s2[0] == "label" and s2[2] == label), None)
                if j is None:
                    out += self.manual(st, f"On Error GoTo {label} (label not found at the top level)")
                    out += self.block(rest)
                else:
                    main, handler = rest[:j], rest[j + 1:]
                    # "Exit Sub" just before the handler label is the normal end of the procedure
                    handler = [h for h in handler if not (h[0] == "resume" and h[2] in ("", "next"))] \
                        if any(h[0] == "resume" for h in handler) else handler
                    if any(h[0] == "resume" for h in rest[j + 1:]):
                        self.note("approx", st[1], f"On Error GoTo {self.ctx.spell(label)}: 'Resume'/'Resume Next' in the handler "
                                                   "end the procedure instead of resuming")
                    else:
                        self.note("rules", st[1], f"On Error GoTo {self.ctx.spell(label)} became try/except")
                    out += ["try:"] + self.indent(self.block(main)) + \
                        ["except Exception as _e:  # On Error GoTo " + self.ctx.spell(label), "    Err.set(_e)"] + \
                        self.indent(self.block(handler) if handler else ["pass"])
        if proc.kind in ("function", "get"):
            out.append("return _ret")
        return out

    def proc_params(self, proc, skip=0) -> list[str]:
        out = []
        for p in proc.params[skip:]:
            disp = self.spell(p.name)
            self.locals[p.name] = (disp, p.typ, p.is_array)
            if p.paramarray:
                out.append(f"*{disp}")
            elif p.optional:
                out.append(f"{disp}={self.ex(p.default) if p.default is not None else TYPE_DEFAULT.get(type_base(p.typ), 'None')}")
            else:
                out.append(disp)
        return out

    def byref_check(self, proc) -> None:
        names = {p.name for p in proc.params if p.byref and not p.paramarray}
        if not names:
            return
        assigned = set()

        def walk(st):
            if isinstance(st, tuple):
                if st and st[0] in ("assign", "set") and isinstance(st[2], tuple) and st[2][0] == "name" and \
                        st[2][2] in names:
                    assigned.add(st[2][2])
                for x in st:
                    walk(x)
            elif isinstance(st, list):
                for x in st:
                    walk(x)
        walk(proc.body)
        for n in sorted(assigned):
            self.note("approx", proc.line, f"ByRef parameter '{self.ctx.spell(n)}' of {proc.display} is assigned - "
                                           "Python passes values: return it or use a list if callers need it")

    def start_proc(self, proc):
        self.proc = proc
        self.locals = {}
        self.param_alias = {}
        self.globals_used = set()
        self.with_stack = []
        rng = next((r for r in self.ranges if r[0] == proc.line), None)
        self.proc_start = proc.line
        self.proc_end = rng[1] if rng else proc.line
        # comments between the previous procedure (or the last declaration) and this one belong to it
        prev_end = max([r[1] for r in self.ranges if r[1] < proc.line] +
                       [ln for ln in getattr(self, "decl_lines", ()) if ln < proc.line] or [0])
        self.proc_start = prev_end + 1

    def fallback_proc(self, proc, why, header: str, indent: int) -> list[str]:
        rng = next((r for r in self.ranges if r[0] == proc.line), (proc.line, proc.line, ""))
        src = self.text.replace("\r\n", "\n").split("\n")[rng[0] - 1:rng[1]]
        self.note("manual", proc.line, f"{proc.display}: could not be translated ({why}) - kept as VB6 comments")
        self.stats["manual"] += 1
        pad = "    " * indent
        return [pad + header] + [pad + "    # VB6: " + ln for ln in src] + [pad + "    pass", ""]


# ============================================================================ module-level drivers
def _collect_module_decls(tr: PyTranslator, mod) -> list[str]:
    """Module-level Dim/Const/Type/Enum/Declare -> Python lines (no indentation) and fills tr.fields."""
    out = []
    for d in mod.decls:
        if d[0] in ("dim", "static"):
            for nm, bounds, typ in d[2]:
                tr.fields[nm] = (tr.spell(nm), typ, bounds is not None)
    for d in mod.decls:
        line = d[1]
        tr.proc_start = 0
        if d[0] in ("dim", "static"):
            for nm, bounds, typ in d[2]:
                out.append(f"{tr.spell(nm)} = {tr.default_value(typ, bounds, line)}" + tr.trailing(line))
        elif d[0] == "const":
            for nm, e in d[2]:
                disp = tr.spell(nm)
                ck = None
                try:
                    ce = tr.exp(e)
                    ck = ce[1]
                    out.append(f"{disp} = {ce[0]}" + tr.trailing(line))
                except Untranslatable as ex:
                    out.append(f"{disp} = None  # TODO: {ex}")
                    tr.note("manual", line, f"Const {disp}: {ex}")
                tr.consts[nm] = (disp if tr.kind == "bas" else f"self.{disp}", ck)
        elif d[0] == "enum":
            tr.note("rules", line, f"Enum {tr.spell(d[2])} became module constants")
            val = -1
            for mname, v in d[3]:
                disp = tr.spell(mname)
                if isinstance(v, tuple) and v[0] != "binop":
                    code = tr.ex(v)
                    val = int(code) if re.fullmatch(r"-?\d+", code) else val + 1
                    out.append(f"{disp} = {code}")
                else:
                    val += 1
                    out.append(f"{disp} = {val}")
                tr.consts[mname] = disp if tr.kind == "bas" else f"self.{disp}"
        elif d[0] == "type":
            name = tr.spell(d[2])
            tr.note("rules", line, f"Type {name} became a Python class")
            out += ["", "", f"class {name}:", f"    \"\"\"VB6 user-defined type {name}.\"\"\"", "",
                    "    def __init__(self):"]
            for m in d[3]:
                mname, typ = m[0], m[1]
                bounds = m[2] if len(m) > 2 else None
                out.append(f"        self.{tr.spell(mname)} = {tr.default_value(typ, bounds, line)}")
            out.append("")
    for dec in mod.declares:
        lib = dec.lib.lower().replace(".dll", "")
        disp = tr.spell(dec.name)
        out.append(f"{disp} = ctypes.windll.{lib}.{dec.alias}  # Declare {dec.kind.capitalize()} {disp} Lib "
                   f"\"{dec.lib}\"")
        tr.imports.add("import ctypes")
        tr.consts[dec.name.lower()] = disp if tr.kind == "bas" else f"self.{disp}"
        tr.note("approx", dec.line, f"Declare {disp} (Win32 API) bound with ctypes - argument/return types "
                                    "are not declared (strings and structures need ctypes types)")
    return out


def _proc_header(tr: PyTranslator, proc, self_arg: bool, name: str | None = None, extra_params=None) -> str:
    params = tr.proc_params(proc)
    if extra_params is not None:
        params = extra_params
    return f"def {name or tr.spell(proc.name.split(':')[-1], proc.display)}({', '.join((['self'] if self_arg else []) + params)}):"


def translate_form_code(ctx: ProjectContext, form: FormInfo, text: str, toolkit: str, file: str,
                        notes: Notes) -> dict:
    """Translate the code of a VB6 form.  Returns {"members": [class body lines, indented 4],
    "handlers": [python handler names], "imports": set, "stats": {...}, "load": bool}."""
    code = code_part(text)
    tr = PyTranslator(ctx, toolkit, file, code, notes, form=form, mod=ctx.modules.get(form.name.lower()))
    tr.ranges = proc_ranges(code)
    try:
        mod = vbparse.parse_module(code, form.name, file)
    except vbparse.VBSyntaxError as e:
        notes.add("manual", file, e.line, f"VB6 code could not be parsed ({e.msg}) - kept as comments")
        body = ["    # VB6 code (not translated - syntax error at line %d):" % e.line] + \
            ["    # " + ln for ln in code.split("\n") if ln.strip()]
        return {"members": body, "handlers": [], "imports": set(), "stats": {"rules": 0, "approx": 0, "manual": 1},
                "load": False}
    members: list[str] = []
    tr.proc_start = 0
    tr.decl_lines = [d[1] for d in mod.decls]
    first = min([r[0] for r in tr.ranges] or [10 ** 9])
    for ln, (ctext, whole) in sorted(tr.comments.items()):
        if whole and ln < first and ln < max(tr.decl_lines or [0]):
            members.append(f"    # {ctext}")
            tr.done_comments.add(ln)
    decls = _collect_module_decls(tr, mod)
    for p in mod.procs.values():
        tr.procs[p.name.split(":")[-1]] = (tr.spell(p.name.split(":")[-1], p.display), p.kind)
    if decls:
        members += ["    # ---- form-level variables of the VB6 form", *["    " + ln if ln else "" for ln in decls], ""]
    for low, (aname, atype, items) in sorted(form.arrays.items()):
        elems = ", ".join(f"{i}: self.{c.name}" for i, c in sorted(items.items()))
        members += ["    @property", f"    def {aname}(self):",
                    f"        \"\"\"VB6 control array {aname}({', '.join(str(i) for i in sorted(items))}).\"\"\"",
                    f"        return {{{elems}}}", ""]
        notes.add("rules", file, 0, f"control array {aname} ({len(items)} {atype}s) became a dict property "
                                    f"self.{aname}[index]")
    handlers: list[str] = []
    has_load = False
    tr.event_names = event_handler_names(form, mod, form.name)
    for p in mod.procs.values():
        base = p.name.split(":")[-1]
        tr.start_proc(p)
        ctrl, _, vbev = base.rpartition("_")
        lines: list[str] = []
        try:
            if p.kind != "sub" and p.kind != "function":
                raise Untranslatable("Property procedures in a form")
            target = None           # ("form"|"ctl"|"array", info, neutral)
            if ctrl and p.kind == "sub":
                if ctrl == "form" or ctrl == "mdiform":
                    neutral = vb_event_to_neutral("Form", vbev)
                    if neutral:
                        target = ("form", None, neutral)
                elif form.controls.get(ctrl):
                    c = form.controls[ctrl]
                    neutral = vb_event_to_neutral(c.type, vbev)
                    if neutral:
                        target = ("ctl", c, neutral)
                elif form.arrays.get(ctrl):
                    a = form.arrays[ctrl]
                    neutral = vb_event_to_neutral(a[1], vbev)
                    if neutral:
                        target = ("array", a, neutral)
            if target is None:
                tr.byref_check(p)
                if p.kind == "function":
                    p._ret_type = _ret_type_of(code, p)
                header = _proc_header(tr, p, True)
                lines = ["    " + header] + tr.indent(tr.proc_body(p, []), 2)
            else:
                kind, info, neutral = target
                args_kind = event_args(neutral)
                prelude, alias = _event_prelude(tr, p, neutral, 1 if kind == "array" else 0)
                tr.param_alias.update(alias)
                if kind == "form":
                    hname = f"{form.name}_{neutral}"
                    wired = neutral in FORM_EVENTS
                    if neutral == "Load":
                        has_load = True
                elif kind == "ctl":
                    hname = f"{info.name}_{neutral}"
                    wired = neutral in CONTROL_TYPES[info.type].all_events()
                else:
                    aname, atype, items = info
                    hname = f"{aname}_{neutral}"
                    wired = neutral in CONTROL_TYPES[atype].all_events()
                if kind == "array":
                    idx = tr.spell(p.params[0].name) if p.params else "Index"
                    tr.locals[p.params[0].name if p.params else "index"] = (idx, "integer", False)
                    sig = f"def {hname}(self, {idx}{', e' if args_kind else ''}):"
                    lines = ["    " + sig] + tr.indent(tr.proc_body(p, prelude), 2)
                    for i, c in sorted(info[2].items()):
                        en = f"{c.name}_{neutral}"
                        lines += ["", f"    def {en}(self{', e' if args_kind else ''}):",
                                  f"        self.{hname}({i}{', e' if args_kind else ''})"]
                        handlers.append(en)
                else:
                    sig = f"def {hname}(self{', e' if args_kind else ''}):"
                    lines = ["    " + sig] + tr.indent(tr.proc_body(p, prelude), 2)
                    handlers.append(hname)
                if not wired:
                    notes.add("manual", file, p.line, f"event {p.display} has no {toolkit} equivalent in RAD IDE - "
                                                      f"translated as method {hname}() but nothing calls it")
                if p.name.split(":")[-1].endswith("_unload") and any(x.name == "cancel" for x in p.params):
                    tr.note("rules", p.line, "Form_Unload Cancel = True became e.Cancel = True (FormClosing)")
        except Untranslatable as e:
            lines = tr.fallback_proc(p, str(e), _safe_header(tr, p), 1)
        members += lines + [""]
    leftover = [ln for ln in sorted(tr.comments) if ln not in tr.done_comments and tr.comments[ln][1]
                and ln > max([r[1] for r in tr.ranges] or [0])]
    for ln in leftover:
        members.append(f"    # {tr.comments[ln][0]}")
    return {"members": members, "handlers": handlers, "imports": tr.imports, "stats": tr.stats, "load": has_load}


def _safe_header(tr, p) -> str:
    try:
        return _proc_header(tr, p, tr.kind != "bas")
    except Exception:  # noqa: BLE001
        return f"def {strip_suffix(p.display or p.name)}(self, *args):"


def _ret_type_of(text: str, proc) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    if 0 < proc.line <= len(lines):
        m = re.search(r"\)\s*As\s+(\w+)", lines[proc.line - 1], re.I)
        if m:
            return m.group(1).lower()
    return "variant"


def _event_prelude(tr: PyTranslator, p, neutral: str, skip: int):
    """Lines that define the VB6 event parameters from the Python EventArgs, and name aliases."""
    params = [x.name for x in p.params[skip:]]
    prelude, alias = [], {}
    if not params:
        return prelude, alias
    if neutral == "KeyPress" and params:
        n = tr.spell(params[0])
        prelude.append(f"{n} = ord(e.KeyChar) if e.KeyChar else 0")
        tr.locals[params[0]] = (n, "integer", False)
        tr.note("approx", p.line, "KeyPress: setting KeyAscii (e.g. KeyAscii = 0) does not change the key typed")
    elif neutral in ("KeyDown", "KeyUp"):
        n = tr.spell(params[0])
        prelude.append(f"{n} = e.KeyCode")
        tr.locals[params[0]] = (n, "integer", False)
        if len(params) > 1:
            prelude.append(f"{tr.spell(params[1])} = 0")
            tr.locals[params[1]] = (tr.spell(params[1]), "integer", False)
        tr.note("approx", p.line, f"{neutral}: KeyCode is the toolkit's key code (Tk keysym / Qt key), "
                                  "not always the VB6 vbKey constant; Shift is 0")
    elif neutral in ("MouseDown", "MouseUp", "MouseMove"):
        names = [tr.spell(x) for x in params]
        vals = ["e.Button", "0", "twips(e.X)", "twips(e.Y)"][:len(names)]
        prelude.append(f"{', '.join(names)} = {', '.join(vals)}")
        for x in params:
            tr.locals[x] = (tr.spell(x), "variant", False)
        tr.note("approx", p.line, f"{neutral}: Button numbers follow the toolkit; X/Y converted to twips")
    elif neutral == "FormClosing":
        alias[params[0]] = "e.Cancel"
        for extra in params[1:]:
            prelude.append(f"{tr.spell(extra)} = 0")
            tr.locals[extra] = (tr.spell(extra), "integer", False)
    else:
        for x in params:
            prelude.append(f"{tr.spell(x)} = None  # VB6 event parameter (no equivalent)")
            tr.locals[x] = (tr.spell(x), "variant", False)
        tr.note("approx", p.line, f"{p.display}: event parameters have no equivalent and are None")
    return prelude, alias


def translate_module(ctx: ProjectContext, mi: ModInfo, text: str, toolkit: str, notes: Notes) -> tuple[str, dict]:
    """A .bas module -> Python module text."""
    tr = PyTranslator(ctx, toolkit, mi.file, text, notes, mod=mi)
    tr.kind = "bas"
    tr.ranges = proc_ranges(text)
    try:
        mod = vbparse.parse_module(text, mi.name, mi.file)
    except vbparse.VBSyntaxError as e:
        notes.add("manual", mi.file, e.line, f"VB6 module could not be parsed ({e.msg}) - kept as comments")
        return (f'"""VB6 module {mi.name} (not translated: syntax error at line {e.line})."""\n\n' +
                "\n".join("# " + ln for ln in text.splitlines()) + "\n"), {"rules": 0, "approx": 0, "manual": 1}
    for p in mod.procs.values():
        tr.procs[p.name.split(":")[-1]] = (tr.spell(p.name.split(":")[-1], p.display), p.kind)
    tr.proc_start = 0
    tr.decl_lines = [d[1] for d in mod.decls]
    head_comments = []
    for ln, c in sorted(tr.comments.items()):
        if c[1] and ln < max(tr.decl_lines or [0]):
            head_comments.append(f"# {c[0]}")
            tr.done_comments.add(ln)
    decls = _collect_module_decls(tr, mod)
    body: list[str] = []
    for p in mod.procs.values():
        tr.start_proc(p)
        tr.byref_check(p)
        try:
            if p.kind not in ("sub", "function"):
                raise Untranslatable("Property procedures in a standard module")
            if p.kind == "function":
                p._ret_type = _ret_type_of(text, p)
            header = _proc_header(tr, p, False)
            inner = tr.proc_body(p, [])
            if tr.globals_used:
                inner.insert(0, "global " + ", ".join(sorted(tr.globals_used)))
            lines = [header] + tr.indent(inner)
        except Untranslatable as e:
            lines = tr.fallback_proc(p, str(e), _safe_header(tr, p), 0)
        body += ["", ""] + lines
    for ln in sorted(tr.comments):
        tr.done_comments.add(ln)
    imports = sorted(tr.imports - {f"import {mi.name}"})
    out = [f'"""{mi.name} - migrated from the VB6 module {mi.file} by RAD IDE (rules translation)."""',
           "from vb6compat import *  # noqa: F401,F403 - VB6 functions (Val, MsgBox, Format, ...)"]
    out += imports
    out += [""] + head_comments + decls + body
    return "\n".join(out).rstrip() + "\n", tr.stats


def translate_class(ctx: ProjectContext, mi: ModInfo, text: str, toolkit: str, notes: Notes) -> tuple[str, dict]:
    """A .cls class module -> Python class (Property Get/Let/Set -> property)."""
    code = code_part(text)
    tr = PyTranslator(ctx, toolkit, mi.file, code, notes, mod=mi)
    tr.kind = "cls"
    tr.ranges = proc_ranges(code)
    try:
        mod = vbparse.parse_module(code, mi.name, mi.file)
    except vbparse.VBSyntaxError as e:
        notes.add("manual", mi.file, e.line, f"VB6 class could not be parsed ({e.msg}) - kept as comments")
        return (f"class {mi.name}:\n    \"\"\"VB6 class (not translated).\"\"\"\n" +
                "\n".join("    # " + ln for ln in code.splitlines()) + "\n"), {"rules": 0, "approx": 0, "manual": 1}
    for p in mod.procs.values():
        base = p.name.split(":")[-1]
        tr.procs[base] = (tr.spell(base, p.display), p.kind)
    tr.proc_start = 0
    tr.decl_lines = [d[1] for d in mod.decls]
    decls = _collect_module_decls(tr, mod)
    members = ["    def __init__(self):"]
    members += ["        self." + ln if re.match(r"\w+ = ", ln) else "        " + ln for ln in decls
                if ln and not ln.startswith(("class ", "    ", '"'))] or []
    init = mod.procs.get("class_initialize")
    if init is not None:
        members.append("        self.Class_Initialize()")
    if len(members) == 1:
        members.append("        pass")
    members.append("")
    props: dict[str, dict] = {}
    for p in mod.procs.values():
        base = p.name.split(":")[-1]
        tr.start_proc(p)
        tr.byref_check(p)
        try:
            if p.kind in ("function", "get"):
                p._ret_type = _ret_type_of(code, p)
            if p.kind in ("get", "let", "set"):
                disp = tr.spell(base, p.display)
                fname = f"_{p.kind}_{disp}"
                header = _proc_header(tr, p, True, name=fname)
                props.setdefault(disp, {})[p.kind] = fname
            else:
                header = _proc_header(tr, p, True)
            lines = ["    " + header] + tr.indent(tr.proc_body(p, []), 2)
        except Untranslatable as e:
            lines = tr.fallback_proc(p, str(e), _safe_header(tr, p), 1)
        members += lines + [""]
    for disp, kinds in props.items():
        setter = kinds.get("let") or kinds.get("set")
        members.append(f"    {disp} = property({kinds.get('get', 'None')}{', ' + setter if setter else ''})")
    if mod.events:
        notes.add("manual", mi.file, 0, f"class {mi.name} declares events ({', '.join(mod.events)}) - "
                                        "RaiseEvent/WithEvents are not translated")
    imports = sorted(tr.imports - {f"from {mi.name} import {mi.name}"})
    out = [f'"""{mi.name} - migrated from the VB6 class {mi.file} by RAD IDE (rules translation)."""',
           "from vb6compat import *  # noqa: F401,F403", *imports, "", "",
           f"class {mi.name}:", f"    \"\"\"VB6 class module {mi.name}.\"\"\"", ""] + members
    return "\n".join(out).rstrip() + "\n", tr.stats
