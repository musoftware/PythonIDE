"""Python emitter: parsed C# statements / expressions (cs_parser) -> Python lines for a python-tk form class
(subclassed with Swing rules by java.py, reused by radide.migrate.cs_qt), plus the C# format-string helpers."""
from __future__ import annotations

import re

from .common import py_ident, PY_RESERVED, pystr
from .cs_lexer import ParseError
from .cs_parser import Parser


# ============================================================================ Python emitter
class Untranslatable(Exception):
    pass


COLOR_NAMES = {
    "black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000", "blue": "#0000FF",
    "yellow": "#FFFF00", "gray": "#808080", "grey": "#808080", "darkgray": "#A9A9A9", "lightgray": "#D3D3D3",
    "silver": "#C0C0C0", "maroon": "#800000", "navy": "#000080", "purple": "#800080", "teal": "#008080",
    "olive": "#808000", "lime": "#00FF00", "aqua": "#00FFFF", "cyan": "#00FFFF", "fuchsia": "#FF00FF",
    "magenta": "#FF00FF", "orange": "#FFA500", "darkorange": "#FF8C00", "pink": "#FFC0CB", "brown": "#A52A2A",
    "gold": "#FFD700", "darkblue": "#00008B", "darkred": "#8B0000", "darkgreen": "#006400",
    "lightblue": "#ADD8E6", "lightgreen": "#90EE90", "lightyellow": "#FFFFE0", "lightpink": "#FFB6C1",
    "steelblue": "#4682B4", "royalblue": "#4169E1", "dodgerblue": "#1E90FF", "skyblue": "#87CEEB",
    "crimson": "#DC143C", "indigo": "#4B0082", "violet": "#EE82EE", "khaki": "#F0E68C", "beige": "#F5F5DC",
    "ivory": "#FFFFF0", "lavender": "#E6E6FA", "salmon": "#FA8072", "tomato": "#FF6347", "coral": "#FF7F50",
    "chocolate": "#D2691E", "tan": "#D2B48C", "wheat": "#F5DEB3", "seagreen": "#2E8B57",
    "forestgreen": "#228B22", "limegreen": "#32CD32", "darkslategray": "#2F4F4F", "slategray": "#708090",
    "dimgray": "#696969", "gainsboro": "#DCDCDC", "whitesmoke": "#F5F5F5", "aliceblue": "#F0F8FF",
    "honeydew": "#F0FFF0", "mintcream": "#F5FFFA", "azure": "#F0FFFF", "cornflowerblue": "#6495ED",
    "midnightblue": "#191970", "firebrick": "#B22222", "orangered": "#FF4500", "yellowgreen": "#9ACD32",
    "darkcyan": "#008B8B", "darkmagenta": "#8B008B", "darkviolet": "#9400D3", "goldenrod": "#DAA520",
    "control": "#F0F0F0", "window": "#FFFFFF", "controltext": "#000000", "windowtext": "#000000",
    "highlight": "#0078D7", "highlighttext": "#FFFFFF", "info": "#FFFFE1", "transparent": "",
}

TYPE_KIND = {"int": "int", "long": "int", "short": "int", "byte": "int", "uint": "int", "ulong": "int",
             "Integer": "int", "Long": "int", "Int32": "int", "Int64": "int", "Int16": "int",
             "double": "float", "float": "float", "decimal": "float", "Double": "float", "Float": "float",
             "Single": "float", "Decimal": "float",
             "string": "str", "String": "str", "char": "str", "Character": "str",
             "bool": "bool", "boolean": "bool", "Boolean": "bool"}
DEFAULTS = {"int": "0", "float": "0.0", "str": '""', "bool": "False", "list": "[]", "dict": "{}"}
CS_FMT = {"F": "f", "N": ",f", "D": "d", "P": "%", "E": "e", "X": "X", "C": ",.2f", "G": "g"}

P_ATOM, P_UNARY, P_MUL, P_ADD, P_SHIFT, P_BAND, P_BXOR, P_BOR, P_CMP, P_NOT, P_AND, P_OR, P_COND = \
    16, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2
PY_OPS = {"*": P_MUL, "/": P_MUL, "//": P_MUL, "%": P_MUL, "+": P_ADD, "-": P_ADD, "<<": P_SHIFT, ">>": P_SHIFT,
          "&": P_BAND, "^": P_BXOR, "|": P_BOR, "==": P_CMP, "!=": P_CMP, "<": P_CMP, ">": P_CMP, "<=": P_CMP,
          ">=": P_CMP, "is": P_CMP, "is not": P_CMP, "in": P_CMP, "and": P_AND, "or": P_OR}


def cs_format_spec(fmt: str) -> str:
    """C# numeric/date format ('F2', 'N0', '0.00', 'HH:mm') -> Python format spec."""
    fmt = fmt.strip()
    m = re.fullmatch(r"([FfNnDdPpEeXxCcGg])(\d*)", fmt)
    if m:
        k, digits = m.group(1).upper(), m.group(2)
        if k == "D":
            return f"0{digits}d" if digits else "d"
        if k == "X":
            return f"0{digits}{'X' if m.group(1) == 'X' else 'x'}" if digits else "X"
        if k == "C":
            return f",.{digits or 2}f"
        if k == "P":
            return f".{digits or 2}%"
        if k == "G":
            return "g"
        return f"{CS_FMT[k][:-1]}.{digits if digits else 2}{CS_FMT[k][-1]}"
    m = re.fullmatch(r"#?,?#*0*(\.(0+|#+))?", fmt)
    if m and fmt:
        dec = len(m.group(2)) if m.group(2) else 0
        return ("," if "," in fmt else "") + f".{dec}f"
    return ""


def cs_date_format(fmt: str) -> str:
    rep = [("yyyy", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("dddd", "%A"),
           ("ddd", "%a"), ("dd", "%d"), ("HH", "%H"), ("hh", "%I"), ("mm", "%M"), ("ss", "%S"), ("tt", "%p")]
    out, i = "", 0
    while i < len(fmt):
        for a, b in rep:
            if fmt.startswith(a, i):
                out += b
                i += len(a)
                break
        else:
            out += fmt[i]
            i += 1
    return out


class PyEmitter:
    """Translate parsed C#-like statements into Python lines for a python-tk form class.

    ctx: controls {name: neutral type}, multiline {names}, form (name), fields {name: kind},
    methods {names}, menus {names}.  Subclasses (Java/Swing) override ``call_rule`` / ``member_rule``.
    """
    LANG = "C#"
    FORM_MEMBERS = {"Text", "Width", "Height", "Left", "Top", "BackColor", "ForeColor", "Close", "Hide", "Show",
                    "Controls", "ClientSize", "Size", "Location", "Refresh", "Invalidate", "Name", "Visible",
                    "Enabled", "Cursor", "WindowState", "TopMost", "Opacity", "Activate", "BringToFront",
                    "Focus", "ActiveControl", "ShowDialog", "DialogResult", "Font", "Icon", "MinimumSize"}

    def __init__(self, controls: dict | None = None, form: str = "Form1", fields: dict | None = None,
                 methods: set | None = None, multiline: set | None = None, menus: set | None = None,
                 forms: set | None = None):
        self.controls = dict(controls or {})
        self.form = form
        self.fields = dict(fields or {})
        self.methods = set(methods or ())
        self.multiline = set(multiline or ())
        self.menus = set(menus or ())
        self.forms = set(forms or ())
        self.locals: list[dict] = [{}]
        self.imports: set[str] = set()
        self.untranslated = 0
        self.translated = 0
        self._tmp = 0

    # ------------------------------------------------------------------ scopes
    def local_kind(self, name):
        for scope in reversed(self.locals):
            if name in scope:
                return scope[name]
        return False

    def is_local(self, name):
        return any(name in s for s in self.locals)

    def declare(self, name, kind):
        self.locals[-1][name] = kind

    def kind_of_type(self, typ: str | None):
        if not typ:
            return None
        base = typ.split("<")[0].split(".")[-1]
        if typ.endswith("[]") or base in ("List", "ArrayList", "IList", "IEnumerable", "ICollection",
                                           "Collection", "Stack", "Queue", "LinkedList", "HashSet", "Set",
                                           "ObservableCollection"):
            return "list"
        if base in ("Dictionary", "Hashtable", "IDictionary", "HashMap", "Map", "SortedDictionary", "TreeMap"):
            return "dict"
        if base == "StringBuilder":
            return "sb"
        if base == "Random":
            return "random"
        return TYPE_KIND.get(base)

    # ------------------------------------------------------------------ statements
    def body(self, stmts, indent: int = 2) -> list[str]:
        lines = []
        for s in stmts:
            lines += self.stmt(s, indent)
        if not any(ln.strip() and not ln.strip().startswith("#") for ln in lines):
            lines.append("    " * indent + "pass")
        return lines

    def stmt(self, s, ind: int) -> list[str]:
        pad = "    " * ind
        try:
            out = self._stmt(s, ind)
            if s[0] not in ("block", "empty", "if", "for", "foreach", "while", "do", "switch", "try", "using"):
                self.translated += 1
            return out
        except Untranslatable as e:
            self.untranslated += 1
            src = self.source_of(s)
            note = f"  # ({e})" if str(e) else ""
            lines = [pad + f"# {self.LANG}: " + ln for ln in src.splitlines() if ln.strip()] or \
                [pad + f"# {self.LANG}: ?"]
            if note:
                lines[-1] += note
            return lines

    def source_of(self, s) -> str:
        if s[0] in ("raw",):
            return s[1]
        if s[0] in ("expr", "decl", "return", "throw"):
            return s[-1]
        if s[0] in ("if", "for", "foreach", "switch"):
            return s[-1] + " (...)"
        return s[0]

    def _stmt(self, s, ind):
        pad = "    " * ind
        kind = s[0]
        if kind == "raw":
            raise Untranslatable("")
        if kind == "empty":
            return []
        if kind == "block":
            out = []
            for x in s[1]:
                out += self.stmt(x, ind)
            return out
        if kind == "expr":
            return [pad + ln for ln in self.expr_stmt(s[1])]
        if kind == "decl":
            out = []
            k = self.kind_of_type(s[1])
            for name, init in s[2]:
                pname = py_ident(name)
                if init is None:
                    self.declare(name, k)
                    out.append(f"{pad}{pname} = {DEFAULTS.get(k, 'None')}")
                    continue
                code, ik = self.ex(init)
                self.declare(name, k or ik)
                out.append(f"{pad}{pname} = {code}")
            return out
        if kind == "if":
            out = []
            node = s
            first = True
            while True:
                cond = self.cond_code(node[1])
                out.append(f"{pad}{'if' if first else 'elif'} {cond}:")
                out += self.scoped(node[2], ind + 1)
                first = False
                other = node[3]
                if other is None:
                    break
                inner = other[1][0] if other[0] == "block" and len(other[1]) == 1 else None
                if inner is not None and inner[0] == "if":
                    node = inner
                    continue
                out.append(f"{pad}else:")
                out += self.scoped(other, ind + 1)
                break
            return out
        if kind == "while":
            return [f"{pad}while {self.cond_code(s[1])}:"] + self.scoped(s[2], ind + 1)
        if kind == "do":
            body = self.scoped(s[1], ind + 1)
            body = [ln for ln in body if ln.strip() != "pass"]
            return [f"{pad}while True:"] + body + [f"{pad}    if not ({self.cond_code(s[2])}):",
                                                   f"{pad}        break"]
        if kind == "for":
            return self.for_stmt(s, ind)
        if kind == "foreach":
            coll, ck = self.ex(s[3])
            self.locals.append({s[2]: self.kind_of_type(s[1]) if s[1] != "var" else ("str" if ck == "str" else None)})
            body = self.body(s[4][1] if s[4][0] == "block" else [s[4]], ind + 1)
            self.locals.pop()
            return [f"{pad}for {py_ident(s[2])} in {coll}:"] + body
        if kind == "switch":
            return self.switch_stmt(s, ind)
        if kind == "try":
            out = [f"{pad}try:"] + self.scoped(s[1], ind + 1)
            for typ, name, block in s[2]:
                exc = self.exception_type(typ)
                self.locals.append({name: "exc"} if name else {})
                out.append(f"{pad}except {exc}" + (f" as {py_ident(name)}:" if name else ":"))
                out += self.body(block[1], ind + 1)
                self.locals.pop()
            if s[3] is not None:
                out.append(f"{pad}finally:")
                out += self.scoped(s[3], ind + 1)
            if not s[2] and s[3] is None:
                out.append(f"{pad}finally:")
                out.append(f"{pad}    pass")
            return out
        if kind == "using":
            out = []
            if s[2]:
                out.append(f"{pad}# {self.LANG}: {s[1]} ({s[2]})")
                if s[1] == "using" and "=" in s[2]:
                    try:
                        p = Parser(s[2] + ";", self.LANG == "Java")
                        out += self.stmt(p.statement(), ind)
                    except ParseError:
                        pass
            return out + self.scoped(s[3], ind)
        if kind == "return":
            if s[1] is None:
                return [pad + "return"]
            return [pad + "return " + self.ex(s[1])[0]]
        if kind == "break":
            return [pad + "break"]
        if kind == "continue":
            return [pad + "continue"]
        if kind == "throw":
            if s[1] is None:
                return [pad + "raise"]
            e = s[1]
            if e[0] == "new":
                exc = self.exception_type(e[1])
                args = ", ".join(self.ex(a)[0] for a in e[2][:1])
                return [f"{pad}raise {exc}({args})"]
            return [pad + "raise " + self.ex(e)[0]]
        raise Untranslatable("")

    def scoped(self, stmt, ind):
        self.locals.append({})
        try:
            return self.body(stmt[1] if stmt[0] == "block" else [stmt], ind)
        finally:
            self.locals.pop()

    def exception_type(self, typ):
        if not typ:
            return "Exception"
        names = []
        for t in typ.split("|"):
            b = t.split(".")[-1]
            names.append({"FormatException": "ValueError", "NumberFormatException": "ValueError",
                          "InvalidCastException": "TypeError", "ArgumentException": "ValueError",
                          "ArgumentNullException": "ValueError", "ArgumentOutOfRangeException": "IndexError",
                          "IndexOutOfRangeException": "IndexError", "ArrayIndexOutOfBoundsException": "IndexError",
                          "DivideByZeroException": "ZeroDivisionError", "ArithmeticException": "ArithmeticError",
                          "OverflowException": "OverflowError", "KeyNotFoundException": "KeyError",
                          "NullReferenceException": "AttributeError", "NullPointerException": "AttributeError",
                          "FileNotFoundException": "FileNotFoundError", "IOException": "OSError",
                          "DirectoryNotFoundException": "FileNotFoundError",
                          "UnauthorizedAccessException": "PermissionError",
                          "NotImplementedException": "NotImplementedError",
                          "InvalidOperationException": "RuntimeError"}.get(b, "Exception"))
        names = list(dict.fromkeys(names))
        return names[0] if len(names) == 1 else "(" + ", ".join(names) + ")"

    def for_stmt(self, s, ind):
        pad = "    " * ind
        init, cond, iters, body = s[1], s[2], s[3], s[4]
        # for (int i = a; i < b; i++)  ->  for i in range(a, b)
        var = start = None
        if len(init) == 1 and init[0][0] == "decl" and len(init[0][2]) == 1 and init[0][2][0][1] is not None:
            var, start = init[0][2][0]
        elif len(init) == 1 and init[0][0] == "expr" and init[0][1][0] == "assign" and init[0][1][1] == "=" \
                and init[0][1][2][0] == "name":
            var, start = init[0][1][2][1], init[0][1][3]
        step = None
        if var and len(iters) == 1:
            it = iters[0]
            if it[0] in ("postinc", "preinc") and it[2] == ("name", var):
                step = 1 if it[1] == "++" else -1
            elif it[0] == "assign" and it[2] == ("name", var) and it[1] in ("+=", "-=") and it[3][0] == "num":
                n = int(self.ex(it[3])[0])
                step = n if it[1] == "+=" else -n
        if var and step and cond is not None and cond[0] == "bin" and cond[2] == ("name", var) and \
                cond[1] in ("<", "<=", ">", ">="):
            self.locals.append({var: "int"})
            a = self.ex(start)[0]
            b = self.ex(cond[3])[0]
            if cond[1] == "<=":
                b = self._plus(b, 1)
            elif cond[1] == ">=":
                b = self._plus(b, -1)
            if step == 1 and cond[1] in ("<", "<="):
                rng = f"range({b})" if a == "0" else f"range({a}, {b})"
            else:
                rng = f"range({a}, {b}, {step})"
            lines = [f"{pad}for {py_ident(var)} in {rng}:"] + self.body(body[1] if body[0] == "block" else [body],
                                                                       ind + 1)
            self.locals.pop()
            return lines
        # general form -> while loop
        out = []
        self.locals.append({})
        for st in init:
            out += self.stmt(st, ind)
        c = self.cond_code(cond) if cond is not None else "True"
        out.append(f"{pad}while {c}:")
        inner = self.body(body[1] if body[0] == "block" else [body], ind + 1)
        inner = [ln for ln in inner if ln.strip() != "pass"]
        for it in iters:
            inner += [f"{pad}    {ln}" for ln in self.expr_stmt(it)]
        if not inner:
            inner = [f"{pad}    pass"]
        out += inner
        self.locals.pop()
        return out

    @staticmethod
    def _plus(code: str, n: int) -> str:
        if re.fullmatch(r"-?\d+", code):
            return str(int(code) + n)
        m = re.fullmatch(r"(.*) - 1", code)
        if m and n == 1:
            return m.group(1)
        return f"{code} + {n}" if n > 0 else f"{code} - {-n}"

    def switch_stmt(self, s, ind):
        pad = "    " * ind
        val, _k = self.ex(s[1])
        out = []
        if not re.fullmatch(r"[\w.]+", val):
            self._tmp += 1
            tmp = f"_value{self._tmp if self._tmp > 1 else ''}"
            out.append(f"{pad}{tmp} = {val}")
            val = tmp
        first = True
        default = None
        for labels, body in s[2]:
            body = [b for b in body if b[0] != "break"]
            real = [lb for lb in labels if lb is not None]
            if None in labels and not real:
                default = body
                continue
            conds = " or ".join(f"{val} == {self.ex(lb)[0]}" for lb in real)
            out.append(f"{pad}{'if' if first else 'elif'} {conds}:")
            out += self.body(body, ind + 1)
            first = False
            if None in labels:
                default = body
        if default is not None:
            if first:
                out += self.body(default, ind)
            else:
                out.append(f"{pad}else:")
                out += self.body(default, ind + 1)
        return out

    def cond_code(self, node) -> str:
        code, _k = self.ex(node)
        if code.startswith("(") and code.endswith(")") and self._balanced(code[1:-1]):
            code = code[1:-1]
        return code

    @staticmethod
    def _balanced(s: str) -> bool:
        depth = 0
        for ch in s:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth < 0:
                    return False
        return depth == 0

    # ------------------------------------------------------------------ expression statements
    def expr_stmt(self, e) -> list[str]:
        if e[0] in ("postinc", "preinc"):
            target = e[2]
            setter = self.try_setter(target, None)
            if setter is not None:
                cur = self.ex(target)[0]
                return self.try_setter(target, f"{cur} {'+' if e[1] == '++' else '-'} 1")
            return [f"{self.ex(target)[0]} {'+=' if e[1] == '++' else '-='} 1"]
        if e[0] == "assign":
            return self.assign_stmt(e)
        if e[0] == "call":
            special = self.call_stmt_rule(e)
            if special is not None:
                return special
        if e[0] == "lambda":
            raise Untranslatable("lambda")
        code, _k = self.ex(e)
        return [code]

    def assign_stmt(self, e):
        op, target, value = e[1], e[2], e[3]
        # event wiring at run time:  btn.Click += handler
        if op in ("+=", "-=") and target[0] == "member" and target[2] in EVENT_MAP and \
                self.ctrl_of(target[1]) is not None:
            raise Untranslatable("event wiring at run time")
        if op == "=":
            vcode, vk = self.ex(value)
            setter = self.try_setter(target, vcode, vk)
            if setter is not None:
                return setter
            tcode, _tk = self.ex_target(target, vk)
            return [f"{tcode} = {vcode}"]
        bop = op[:-1]
        if op == "??=":
            tcode = self.ex(target)[0]
            return [f"if {tcode} is None:", f"    {tcode} = {self.ex(value)[0]}"]
        cur, ck = self.ex(target)
        vcode, vk = self.ex(value)
        if bop == "+" and (ck == "str" or vk == "str"):
            if ck != "str":
                cur = f"str({cur})"
            if vk != "str":
                vcode = f"str({vcode})"
        if bop == "/" and ck == "int" and vk == "int":
            bop = "//"
        setter = self.try_setter(target, f"{cur} {bop} {self.wrap(vcode, PY_OPS.get(bop, P_ADD), True)}", ck)
        if setter is not None:
            return setter
        if target[0] == "member" and target[2] == "Text" and self.ctrl_of(target[1]):
            raise Untranslatable("")
        tcode = self.ex(target)[0]
        return [f"{tcode} {bop}= {vcode}"]

    def ex_target(self, target, vk=None):
        if target[0] == "name" and not self.is_local(target[1]) and target[1] not in self.fields and \
                target[1] not in self.controls:
            # an undeclared name assigned: a field of the form (VB.NET module-level variables ...)
            if target[1] in self.FORM_MEMBERS:
                raise Untranslatable("form property")
            self.declare(target[1], vk)
            return py_ident(target[1]), vk
        return self.ex(target)

    # ------------------------------------------------------------------ controls
    def ctrl_of(self, node) -> str | None:
        """Control name when *node* is a control reference (txtName / this.txtName)."""
        if node[0] == "name" and node[1] in self.controls and not self.is_local(node[1]):
            return node[1]
        if node[0] == "member" and node[1] in (("name", "this"), ("name", "base"), ("name", "Me")) and \
                node[2] in self.controls:
            return node[2]
        return None

    def is_form(self, node) -> bool:
        return node in (("name", "this"), ("name", "base"), ("name", "Me"), ("name", "MyBase"))

    def try_setter(self, target, vcode, vk=None) -> list[str] | None:
        """python-tk code that sets a control / form property, or None."""
        if target[0] == "name" and target[1] in self.FORM_MEMBERS and not self.is_local(target[1]) and \
                target[1] not in self.fields:
            target = ("member", ("name", "this"), target[1], False)
        if target[0] != "member":
            return None
        obj, prop = target[1], target[2]
        if self.is_form(obj) and (prop in self.fields or prop in self.controls or prop in self.methods):
            return None                                   # this.field = ... -> plain assignment
        if vcode is None:
            return [] if self.ctrl_of(obj) or self.is_form(obj) else None
        if self.is_form(obj):
            return self.form_setter(prop, vcode)
        name = self.ctrl_of(obj)
        if name is None:
            if obj[0] == "member" and obj[2] in ("Font",) and self.ctrl_of(obj[1]):
                raise Untranslatable("font property")
            return None
        t = self.controls[name]
        s = f"self.{name}"
        if t in ("Timer",):
            if prop in ("Enabled", "Interval"):
                return [f"{s}.{prop} = {vcode}"]
            return None
        if prop == "Text":
            if t == "TextBox" and name in self.multiline:
                return [f"{s}.delete(\"1.0\", \"end\")", f"{s}.insert(\"1.0\", {vcode})"]
            if t in ("TextBox", "ComboBox"):
                return [f"{s}_var.set({vcode})"]
            if t in ("ListBox", "NumericUpDown", "TrackBar"):
                raise Untranslatable("")
            return [f"{s}.config(text={vcode})"]
        if prop == "Checked" and t == "CheckBox":
            return [f"{s}_var.set({vcode})"]
        if prop == "Checked" and t == "RadioButton":
            return [f"self._radio.set({pystr(name)} if {vcode} else \"\")"]
        if prop == "Value" and t in ("NumericUpDown", "TrackBar"):
            return [f"{s}_var.set({vcode})"]
        if prop == "Value" and t == "ProgressBar":
            return [f"{s}[\"value\"] = {vcode}"]
        if prop in ("Maximum", "Minimum") and t == "ProgressBar" and prop == "Maximum":
            return [f"{s}[\"maximum\"] = {vcode}"]
        if prop in ("Maximum", "Minimum") and t in ("NumericUpDown", "TrackBar"):
            return [f"{s}.config({'to' if prop == 'Maximum' else 'from_'}={vcode})"]
        if prop == "Enabled":
            if vcode in ("True", "False"):
                return [f"{s}.config(state={pystr('normal' if vcode == 'True' else 'disabled')})"]
            return [f"{s}.config(state=\"normal\" if {vcode} else \"disabled\")"]
        if prop == "Visible":
            return [f"if {vcode}:", f"    {s}.place(**self._places[{pystr(name)}])", "else:",
                    f"    {s}.place_forget()"] if not re.fullmatch(r"True|False", vcode) else \
                [f"{s}.place(**self._places[{pystr(name)}])" if vcode == "True" else f"{s}.place_forget()"]
        if prop in ("BackColor", "ForeColor"):
            return [f"{s}.config({'bg' if prop == 'BackColor' else 'fg'}={vcode})"]
        if prop in ("Left", "Top", "Width", "Height"):
            key = {"Left": "x", "Top": "y", "Width": "width", "Height": "height"}[prop]
            return [f"self._places[{pystr(name)}][{pystr(key)}] = {vcode}",
                    f"{s}.place(**self._places[{pystr(name)}])"]
        if prop == "SelectedIndex" and t == "ListBox":
            return [f"{s}.selection_clear(0, \"end\")", f"if {vcode} >= 0:",
                    f"    {s}.selection_set({vcode})", f"    {s}.see({vcode})"]
        if prop == "SelectedIndex" and t == "ComboBox":
            return [f"{s}.current({vcode})"]
        if prop in ("SelectedItem", "SelectedText") and t == "ComboBox":
            return [f"{s}_var.set({vcode})"]
        if prop == "ReadOnly" and t == "TextBox":
            return [f"{s}.config(state=\"readonly\" if {vcode} else \"normal\")"]
        if prop == "PasswordChar" and t == "TextBox":
            return [f"{s}.config(show={vcode})"]
        if prop == "Image" and t == "PictureBox":
            raise Untranslatable("images")
        if prop in ("Focus",):
            return None
        raise Untranslatable(f"{t}.{prop}")

    def form_setter(self, prop, vcode):
        if prop == "Text":
            return [f"self.root.title({vcode})"]
        if prop == "BackColor":
            return [f"self.root.config(bg={vcode})"]
        if prop in ("Width", "Height"):
            w = vcode if prop == "Width" else "self.root.winfo_width()"
            h = vcode if prop == "Height" else "self.root.winfo_height()"
            return [f"self.root.geometry(f\"{{{w}}}x{{{h}}}\")"]
        if prop == "TopMost":
            return [f"self.root.attributes(\"-topmost\", {vcode})"]
        if prop == "Visible":
            return [f"self.root.deiconify() if {vcode} else self.root.withdraw()"]
        if prop == "WindowState":
            return [f"self.root.state({vcode})"]
        if prop == "Cursor":
            return [f"self.root.config(cursor={vcode})"]
        if prop == "Opacity":
            return [f"self.root.attributes(\"-alpha\", {vcode})"]
        raise Untranslatable(f"Form.{prop}")

    def control_get(self, name: str, prop: str):
        t = self.controls[name]
        s = f"self.{name}"
        if t == "Timer":
            if prop in ("Enabled", "Interval"):
                return f"{s}.{prop}", ("bool" if prop == "Enabled" else "int")
            return None
        if prop == "Text":
            if t == "TextBox" and name in self.multiline:
                return f"{s}.get(\"1.0\", \"end-1c\")", "str"
            if t in ("TextBox", "ComboBox"):
                return f"{s}_var.get()", "str"
            if t == "NumericUpDown":
                return f"str({s}_var.get())", "str"
            if t == "ListBox":
                return f"({s}.get({s}.curselection()[0]) if {s}.curselection() else \"\")", "str"
            return f"{s}.cget(\"text\")", "str"
        if prop == "Checked" and t == "CheckBox":
            return f"{s}_var.get()", "bool"
        if prop == "Checked" and t == "RadioButton":
            return f"(self._radio.get() == {pystr(name)})", "bool"
        if prop == "Value" and t in ("NumericUpDown", "TrackBar"):
            return f"{s}_var.get()", "int"
        if prop == "Value" and t == "ProgressBar":
            return f"{s}[\"value\"]", "float"
        if prop == "Maximum" and t == "ProgressBar":
            return f"{s}[\"maximum\"]", "float"
        if prop == "SelectedIndex" and t == "ListBox":
            return f"({s}.curselection()[0] if {s}.curselection() else -1)", "int"
        if prop == "SelectedIndex" and t == "ComboBox":
            return f"{s}.current()", "int"
        if prop in ("SelectedItem", "SelectedValue") and t == "ListBox":
            return f"({s}.get({s}.curselection()[0]) if {s}.curselection() else None)", None
        if prop in ("SelectedItem", "SelectedValue", "SelectedText") and t == "ComboBox":
            return f"{s}_var.get()", "str"
        if prop == "Enabled":
            return f"(str({s}.cget(\"state\")) != \"disabled\")", "bool"
        if prop == "Visible":
            return f"bool({s}.winfo_ismapped())", "bool"
        if prop in ("Width", "Height"):
            return f"{s}.winfo_{prop.lower()}()", "int"
        if prop in ("Left", "Top"):
            return f"self._places[{pystr(name)}][{pystr('x' if prop == 'Left' else 'y')}]", "int"
        if prop in ("BackColor", "ForeColor"):
            return f"{s}.cget({pystr('bg' if prop == 'BackColor' else 'fg')})", "str"
        if prop == "Name":
            return pystr(name), "str"
        if prop == "TextLength":
            return f"len({self.control_get(name, 'Text')[0]})", "int"
        if prop == "Lines" and t == "TextBox":
            return f"{self.control_get(name, 'Text')[0]}.splitlines()", "list"
        if prop == "Focused":
            return f"({s}.focus_get() is {s})", "bool"
        return None

    def items_call(self, name: str, method: str, args: list):
        t = self.controls[name]
        s = f"self.{name}"
        a = [self.ex(x)[0] for x in args]
        if t == "ListBox":
            if method == "Add":
                return f"{s}.insert(\"end\", {a[0]})", None
            if method == "AddRange":
                return f"{s}.insert(\"end\", *{a[0]})", None
            if method == "Clear":
                return f"{s}.delete(0, \"end\")", None
            if method == "RemoveAt":
                return f"{s}.delete({a[0]})", None
            if method == "Remove":
                return f"{s}.delete(list({s}.get(0, \"end\")).index({a[0]}))", None
            if method == "Insert":
                return f"{s}.insert({a[0]}, {a[1]})", None
            if method == "Contains":
                return f"({a[0]} in {s}.get(0, \"end\"))", "bool"
            if method == "IndexOf":
                return f"list({s}.get(0, \"end\")).index({a[0]})", "int"
        if t == "ComboBox":
            if method == "Add":
                return f"{s}.config(values=(*{s}.cget(\"values\"), {a[0]}))", None
            if method == "AddRange":
                return f"{s}.config(values=(*{s}.cget(\"values\"), *{a[0]}))", None
            if method == "Clear":
                return f"{s}.config(values=())", None
            if method == "Contains":
                return f"({a[0]} in {s}.cget(\"values\"))", "bool"
            if method == "RemoveAt":
                return f"{s}.config(values=[v for i, v in enumerate({s}.cget(\"values\")) if i != {a[0]}])", None
        raise Untranslatable(f"{t}.Items.{method}")

    def items_get(self, name: str):
        t = self.controls[name]
        if t == "ListBox":
            return f"self.{name}.get(0, \"end\")", "list"
        if t == "ComboBox":
            return f"self.{name}.cget(\"values\")", "list"
        raise Untranslatable(f"{t}.Items")

    # ------------------------------------------------------------------ expressions
    def wrap(self, code_prec, need: int, right=False):
        if isinstance(code_prec, str):
            return code_prec
        code, prec = code_prec
        if prec < need or (right and prec == need):
            return f"({code})"
        return code

    def ex(self, node) -> tuple[str, str | None]:
        code, kind, _p = self.exp(node)
        return code, kind

    def exp(self, node):
        """(code, kind, precedence)."""
        tag = node[0]
        if tag == "str":
            return pystr(node[1]), "str", P_ATOM
        if tag == "num":
            return self.number(node[1])
        if tag == "const":
            return {"true": "True", "false": "False", "null": "None"}[node[1]], \
                {"true": "bool", "false": "bool"}.get(node[1]), P_ATOM
        if tag == "istr":
            return self.fstring(node[1]), "str", P_ATOM
        if tag == "paren":
            code, kind, prec = self.exp(node[1])
            return code, kind, prec
        if tag == "name":
            return self.name(node[1])
        if tag == "member":
            return self.member(node)
        if tag == "call":
            return self.call(node)
        if tag == "index":
            obj = node[1]
            if obj[0] == "member" and obj[2] == "Items" and self.ctrl_of(obj[1]):
                name = self.ctrl_of(obj[1])
                lst, _k = self.items_get(name)
                return f"{lst}[{self.ex(node[2][0])[0]}]", None, P_ATOM
            o, ok, op_ = self.exp(obj)
            idx = ", ".join(self.ex(a)[0] for a in node[2])
            return f"{self.wrap((o, op_), P_ATOM)}[{idx}]", ("str" if ok == "str" else None), P_ATOM
        if tag == "unary":
            code, kind, prec = self.exp(node[2])
            if node[1] == "!":
                if prec == P_NOT and code.startswith("not "):          # !!x / !string.IsNullOrEmpty(x)
                    return f"bool({code[4:]})", "bool", P_ATOM
                return f"not {self.wrap((code, prec), P_NOT)}", "bool", P_NOT
            if node[1] == "-":
                return f"-{self.wrap((code, prec), P_UNARY)}", kind, P_UNARY
            if node[1] == "~":
                return f"~{self.wrap((code, prec), P_UNARY)}", kind, P_UNARY
            return code, kind, prec
        if tag in ("preinc", "postinc"):
            raise Untranslatable("++/-- inside an expression")
        if tag == "bin":
            return self.binop(node)
        if tag == "cond":
            c = self.wrap(self.exp(node[1])[::2], P_OR)
            a = self.exp(node[2])
            b = self.exp(node[3])
            return f"{self.wrap((a[0], a[2]), P_OR)} if {c} else {self.wrap((b[0], b[2]), P_COND)}", \
                a[1] or b[1], P_COND
        if tag == "cast":
            return self.cast(node[1], node[2])
        if tag == "new":
            return self.new(node)
        if tag == "newarr":
            items = node[3]
            if items is None:
                size = self.ex(node[2])[0] if node[2] is not None else "0"
                k = self.kind_of_type(node[1])
                return f"[{DEFAULTS.get(k, 'None')}] * {size}", "list", P_MUL
            return "[" + ", ".join(self.ex(x)[0] for x in items) + "]", "list", P_ATOM
        if tag == "tuple":
            return "(" + ", ".join(self.ex(x)[0] for x in node[1]) + ("," if len(node[1]) == 1 else "") + ")", \
                None, P_ATOM
        if tag == "assign":
            raise Untranslatable("assignment inside an expression")
        if tag == "is":
            x, typ, name = node[2], node[3], node[4]
            if name:
                raise Untranslatable("pattern matching")
            pyt = {"str": "str", "int": "int", "float": "float", "bool": "bool"}.get(self.kind_of_type(typ) or "")
            if node[1] == "as":
                return self.ex(x)[0], None, P_ATOM
            if pyt:
                return f"isinstance({self.ex(x)[0]}, {pyt})", "bool", P_ATOM
            raise Untranslatable("type test")
        if tag == "special":
            if node[1] == "nameof":
                return pystr(node[2].split(".")[-1]), "str", P_ATOM
            if node[1] == "default":
                return DEFAULTS.get(self.kind_of_type(node[2]), "None"), self.kind_of_type(node[2]), P_ATOM
            raise Untranslatable(node[1])
        if tag == "lambda":
            if node[2][0] == "block":
                raise Untranslatable("lambda with a block body")
            self.locals.append({p: None for p in node[1]})
            body = self.ex(node[2])[0]
            self.locals.pop()
            return f"lambda {', '.join(py_ident(p) for p in node[1])}: {body}", None, 0
        if tag == "out":
            raise Untranslatable("out/ref argument")
        raise Untranslatable(tag)

    def number(self, text: str):
        t = text.replace("_", "")
        low = t.lower()
        if low.startswith("0x"):
            return str(int(re.sub(r"[uUlL]+$", "", t), 16)), "int", P_ATOM
        if low.startswith("0b"):
            return re.sub(r"[uUlL]+$", "", t), "int", P_ATOM
        suffix = re.search(r"[fFdDmMlLuU]+$", t)
        body = t[:suffix.start()] if suffix else t
        if (suffix and suffix.group(0).lower() in ("f", "d", "m")) or "." in body or "e" in body.lower():
            if "." not in body and "e" not in body.lower():
                body += ".0"
            return body, "float", P_ATOM
        return body, "int", P_ATOM

    def fstring(self, parts) -> str:
        out = []
        for p in parts:
            if isinstance(p, str):
                out.append(p.replace("{", "{{").replace("}", "}}").replace("\\", "\\\\").replace("\n", "\\n")
                           .replace('"', '\\"'))
                continue
            node, fmt, _raw = p
            if node[0] == "rawexpr":
                raise Untranslatable("interpolated string")
            code, _k = self.ex(node)
            code = code.replace('"', "'")
            spec = cs_format_spec(fmt) if fmt else ""
            if fmt and not spec:
                spec = cs_date_format(fmt) if re.search(r"[yMdHhms]", fmt) else ""
            out.append("{" + code + (":" + spec if spec else "") + "}")
        return 'f"' + "".join(out) + '"'

    def name(self, n: str):
        if n in ("this", "base", "Me", "MyBase"):
            return "self", None, P_ATOM
        k = self.local_kind(n)
        if k is not False:
            return py_ident(n), k, P_ATOM
        if n in self.controls:
            return f"self.{n}", "control", P_ATOM
        if n in self.fields:
            return f"self.{n}", self.fields[n], P_ATOM
        if n in self.methods:
            return f"self.{n}", None, P_ATOM
        if n in ("string", "String"):
            return "str", None, P_ATOM
        if n in ("int", "Integer"):
            return "int", None, P_ATOM
        if n == "e":
            return "e", None, P_ATOM
        if n in self.FORM_MEMBERS:
            got = self.member(("member", ("name", "this"), n, False))
            return got
        return n, None, P_ATOM

    def member(self, node):
        obj, prop = node[1], node[2]
        if self.is_form(obj):
            if prop in self.controls:
                return f"self.{prop}", "control", P_ATOM
            if prop in self.fields:
                return f"self.{prop}", self.fields[prop], P_ATOM
            if prop in self.methods:
                return f"self.{prop}", None, P_ATOM
            if prop == "Text":
                return "self.root.title()", "str", P_ATOM
            if prop in ("Width", "Height"):
                return f"self.root.winfo_{prop.lower()}()", "int", P_ATOM
            if prop == "Name":
                return pystr(self.form), "str", P_ATOM
            raise Untranslatable(f"Form.{prop}")
        name = self.ctrl_of(obj)
        if name is not None:
            got = self.control_get(name, prop)
            if got is not None:
                return got[0], got[1], P_ATOM
            if prop == "Items":
                code, k = self.items_get(name)
                return code, k, P_ATOM
            raise Untranslatable(f"{self.controls[name]}.{prop}")
        # Items.Count, Text.Length ...
        if obj[0] == "member" and obj[2] == "Items" and self.ctrl_of(obj[1]):
            cname = self.ctrl_of(obj[1])
            if prop == "Count":
                t = self.controls[cname]
                return (f"self.{cname}.size()" if t == "ListBox" else f"len(self.{cname}.cget(\"values\"))"), \
                    "int", P_ATOM
        if obj[0] == "member" and obj[2] == "SelectedItems" and self.ctrl_of(obj[1]) and prop == "Count":
            return f"len(self.{self.ctrl_of(obj[1])}.curselection())", "int", P_ATOM
        static = self.static_member(obj, prop)
        if static is not None:
            return static
        code, kind, prec = self.exp(obj)
        if prop in ("Length", "Count") and kind in ("str", "list", "dict", "sb", None):
            return f"len({code})", "int", P_ATOM
        if kind == "exc" and prop == "Message":
            return f"str({code})", "str", P_ATOM
        if kind == "sb" and prop == "Length":
            return f"len({code})", "int", P_ATOM
        if kind == "dict" and prop in ("Keys", "Values"):
            return f"{code}.{prop.lower()}()", "list", P_ATOM
        if kind == "datetime":
            attr = {"Year": "year", "Month": "month", "Day": "day", "Hour": "hour", "Minute": "minute",
                    "Second": "second", "DayOfWeek": "weekday()", "Date": "date()"}.get(prop)
            if attr:
                return f"{code}.{attr}", "int", P_ATOM
        if obj == ("name", "e") and prop in ("KeyCode", "KeyChar", "X", "Y", "Button", "Delta", "Cancel"):
            return f"e.{prop}", None, P_ATOM
        if obj == ("name", "e") and prop == "KeyValue":
            return "e.KeyCode", None, P_ATOM
        return f"{self.wrap((code, prec), P_ATOM)}.{prop}", None, P_ATOM

    def static_member(self, obj, prop):
        """Members of static classes: Color.Red, Math.PI, string.Empty, DateTime.Now, Environment.NewLine."""
        if obj[0] != "name" or self.is_local(obj[1]) or obj[1] in self.controls or obj[1] in self.fields:
            q = None
            if obj[0] == "member" and obj[1][0] == "name":          # System.Drawing.Color.Red
                q = obj[2]
            if q is None:
                return None
            cls = q
        else:
            cls = obj[1]
        if cls in ("Color", "SystemColors", "Colors"):
            hexv = COLOR_NAMES.get(prop.lower())
            if hexv is not None:
                return pystr(hexv), "str", P_ATOM
            return pystr(prop.lower()), "str", P_ATOM
        if cls == "Math" or cls == "MathF":
            if prop == "PI":
                self.imports.add("import math")
                return "math.pi", "float", P_ATOM
            if prop == "E":
                self.imports.add("import math")
                return "math.e", "float", P_ATOM
        if cls in ("string", "String") and prop == "Empty":
            return '""', "str", P_ATOM
        if cls == "Environment" and prop == "NewLine":
            return '"\\n"', "str", P_ATOM
        if cls in ("DateTime", "LocalDateTime") and prop in ("Now", "Today"):
            self.imports.add("import datetime")
            return ("datetime.datetime.now()" if prop == "Now" else "datetime.date.today()"), "datetime", P_ATOM
        if cls == "DialogResult":
            return pystr(prop), "str", P_ATOM
        if cls in ("int", "Int32", "Integer") and prop in ("MaxValue", "MAX_VALUE"):
            return "2147483647", "int", P_ATOM
        if cls in ("int", "Int32", "Integer") and prop in ("MinValue", "MIN_VALUE"):
            return "-2147483648", "int", P_ATOM
        if cls == "Keys":
            return pystr(prop), "str", P_ATOM
        if cls == "Application" and prop in ("StartupPath", "ExecutablePath"):
            self.imports.add("import os")
            self.imports.add("import sys")
            return "os.path.dirname(os.path.abspath(sys.argv[0]))", "str", P_ATOM
        if cls == "MessageBoxButtons" or cls == "MessageBoxIcon":
            return pystr(prop), "str", P_ATOM
        if cls in ("FormWindowState",):
            return pystr({"Maximized": "zoomed", "Minimized": "iconic", "Normal": "normal"}.get(prop, prop)), \
                "str", P_ATOM
        if cls == "Cursors":
            return pystr({"WaitCursor": "watch", "Default": "", "Hand": "hand2", "IBeam": "xterm",
                          "Cross": "crosshair"}.get(prop, "")), "str", P_ATOM
        return None

    def binop(self, node):
        op, a, b = node[1], node[2], node[3]
        if op == "??":
            ac, _ak, ap = self.exp(a)
            bc, bk, bp = self.exp(b)
            return f"{self.wrap((ac, ap), P_OR)} if {self.wrap((ac, ap), P_CMP)} is not None else " \
                   f"{self.wrap((bc, bp), P_COND)}", bk, P_COND
        if op in ("==", "!=") and (b == ("const", "null") or a == ("const", "null")):
            x = a if b == ("const", "null") else b
            xc, _xk, xp = self.exp(x)
            return f"{self.wrap((xc, xp), P_CMP)} {'is' if op == '==' else 'is not'} None", "bool", P_CMP
        ac, ak, ap = self.exp(a)
        bc, bk, bp = self.exp(b)
        pyop = {"&&": "and", "||": "or", ">>>": ">>"}.get(op, op)
        kind = None
        if op == "+":
            if ak == "str" or bk == "str":
                if ak != "str":
                    ac, ap = f"str({ac})", P_ATOM
                if bk != "str":
                    bc, bp = f"str({bc})", P_ATOM
                kind = "str"
            elif ak == "int" and bk == "int":
                kind = "int"
            elif ak in ("int", "float") and bk in ("int", "float"):
                kind = "float"
        elif op in ("-", "*", "%"):
            kind = "int" if ak == bk == "int" else ("float" if {ak, bk} <= {"int", "float"} else None)
        elif op == "/":
            if ak == "int" and bk == "int":
                pyop, kind = "//", "int"
            else:
                kind = "float" if {ak, bk} <= {"int", "float"} else None
        elif op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
            kind = "bool"
        elif op in ("&", "|", "^") and (ak == "bool" or bk == "bool"):
            pyop = {"&": "and", "|": "or", "^": "!="}[op]
            kind = "bool"
        prec = PY_OPS[pyop]
        return f"{self.wrap((ac, ap), prec)} {pyop} {self.wrap((bc, bp), prec, True)}", kind, prec

    def cast(self, typ, x):
        code, kind, prec = self.exp(x)
        k = self.kind_of_type(typ)
        if k == "int":
            return (code if kind == "int" else f"int({code})"), "int", P_ATOM
        if k == "float":
            return (code if kind == "float" else f"float({code})"), "float", P_ATOM
        if k == "str":
            return (code if kind == "str" else f"str({code})"), "str", prec if kind == "str" else P_ATOM
        if k == "bool":
            return f"bool({code})", "bool", P_ATOM
        return code, kind, prec

    def new(self, node):
        typ, args, init = node[1], node[2], node[3]
        base = typ.split("<")[0].split(".")[-1]
        a = [self.ex(x)[0] for x in args]
        if base in ("List", "ArrayList", "Collection", "LinkedList", "ObservableCollection", "Stack", "Queue"):
            items = [self.ex(x)[0] for x in init or [] if x[0] != "prop"]
            if a and not items and not re.fullmatch(r"\d+", a[0]):
                return f"list({a[0]})", "list", P_ATOM
            return "[" + ", ".join(items) + "]", "list", P_ATOM
        if base in ("HashSet",):
            return ("set(" + (a[0] if a else "") + ")"), "list", P_ATOM
        if base in ("Dictionary", "Hashtable", "SortedDictionary", "HashMap", "TreeMap"):
            pairs = []
            for x in init or []:
                if x[0] == "tuple" and len(x[1]) == 2:
                    pairs.append(f"{self.ex(x[1][0])[0]}: {self.ex(x[1][1])[0]}")
                elif x[0] == "kv":
                    pairs.append(f"{self.ex(x[1])[0]}: {self.ex(x[2])[0]}")
            return "{" + ", ".join(pairs) + "}", "dict", P_ATOM
        if base == "StringBuilder":
            return (a[0] if a else '""'), "sb", P_ATOM
        if base == "Random":
            self.imports.add("import random")
            return "random.Random(" + ", ".join(a) + ")", "random", P_ATOM
        if base in ("String", "string") and len(a) == 2:
            return f"{a[0]} * {a[1]}", "str", P_MUL
        if base == "DateTime" and a:
            self.imports.add("import datetime")
            return "datetime.datetime(" + ", ".join(a) + ")", "datetime", P_ATOM
        if base in ("Exception", "ArgumentException", "InvalidOperationException", "FormatException"):
            return f"{self.exception_type(base)}({', '.join(a)})", None, P_ATOM
        if base in self.forms:
            return f"{base}()", "form", P_ATOM
        if base in ("Point", "Size") and len(a) == 2:
            return f"({a[0]}, {a[1]})", None, P_ATOM
        if base == "Font":
            return "(" + ", ".join(a[:2]) + ")", None, P_ATOM
        raise Untranslatable(f"new {base}")

    # ------------------------------------------------------------------ calls
    def call_stmt_rule(self, e):
        """Calls that become one or more statements (None = use the expression form)."""
        func = e[1]
        if func[0] == "member" and func[2] in ("Show",) and func[1][0] == "name" and func[1][1] in self.forms:
            return [f"{func[1][1]}()"]
        if func[0] == "member" and func[2] == "AppendText" and self.ctrl_of(func[1]):
            name = self.ctrl_of(func[1])
            arg = self.ex(e[2][0])[0]
            if name in self.multiline:
                return [f"self.{name}.insert(\"end\", {arg})"]
            return [f"self.{name}_var.set(self.{name}_var.get() + {arg})"]
        return None

    def call(self, node):
        func, args = node[1], node[2]
        if func[0] == "name":
            n = func[1]
            if not self.is_local(n):
                if n in self.methods:
                    return f"self.{py_ident(n) if n in PY_RESERVED else n}({self.arglist(args)})", None, P_ATOM
                if n in ("Close", "Dispose"):
                    return "self.root.destroy()", None, P_ATOM
                if n == "Hide":
                    return "self.root.withdraw()", None, P_ATOM
                if n in ("Show", "Activate", "BringToFront"):
                    return "self.root.deiconify()", None, P_ATOM
                if n in ("Refresh", "Invalidate", "Update", "SuspendLayout", "ResumeLayout", "PerformLayout"):
                    return "self.root.update_idletasks()", None, P_ATOM
                if n == "MsgBox":
                    return self.msgbox(args, vb=True)
                if n in ("InitializeComponent",):
                    raise Untranslatable("InitializeComponent")
                if n in ("Val",):
                    return f"float({self.ex(args[0])[0]})", "float", P_ATOM
                if n in ("CStr",):
                    return f"str({self.ex(args[0])[0]})", "str", P_ATOM
                if n in ("CInt", "CLng"):
                    return f"int({self.ex(args[0])[0]})", "int", P_ATOM
                if n in ("CDbl", "CSng", "CDec"):
                    return f"float({self.ex(args[0])[0]})", "float", P_ATOM
            return f"{self.ex(func)[0]}({self.arglist(args)})", None, P_ATOM
        if func[0] == "member":
            got = self.call_rule(func[1], func[2], args)
            if got is not None:
                return got
            obj_code, ok, op_ = self.exp(func[1])
            return f"{self.wrap((obj_code, op_), P_ATOM)}.{func[2]}({self.arglist(args)})", None, P_ATOM
        code = self.ex(func)[0]
        return f"{code}({self.arglist(args)})", None, P_ATOM

    def arglist(self, args):
        return ", ".join(self.ex(a)[0] for a in args)

    def msgbox(self, args, vb=False):
        self.imports.add("from tkinter import messagebox")
        a = [self.ex(x)[0] for x in args]
        msg = a[0] if a else '""'
        if not args or self.ex(args[0])[1] != "str":
            msg = f"str({msg})"
        title = '""'
        buttons, icon = "", ""
        rest = list(args[1:])
        if vb:          # MsgBox(prompt, buttons, title)
            if rest:
                buttons = self._enum_text(rest[0])
            if len(rest) > 1:
                title = self.ex(rest[1])[0]
        else:
            if rest:
                title = self.ex(rest[0])[0]
            if len(rest) > 1:
                buttons = self._enum_text(rest[1])
            if len(rest) > 2:
                icon = self._enum_text(rest[2])
        ask = None
        b = buttons.lower()
        if "yesnocancel" in b:
            ask = "askyesnocancel"
        elif "yesno" in b:
            ask = "askyesno"
        elif "okcancel" in b:
            ask = "askokcancel"
        elif "retrycancel" in b:
            ask = "askretrycancel"
        i = icon.lower() + " " + b
        if ask == "askyesnocancel":
            return f"{{True: \"Yes\", False: \"No\", None: \"Cancel\"}}[messagebox.askyesnocancel({title}, {msg})]", \
                "str", P_ATOM
        if ask:
            yes, no = {"askyesno": ("Yes", "No"), "askokcancel": ("OK", "Cancel"),
                       "askretrycancel": ("Retry", "Cancel")}[ask]
            return f"(\"{yes}\" if messagebox.{ask}({title}, {msg}) else \"{no}\")", "str", P_ATOM
        fn = "showerror" if ("error" in i or "stop" in i or "critical" in i or "hand" in i) else \
            "showwarning" if ("warning" in i or "exclamation" in i) else "showinfo"
        return f"messagebox.{fn}({title}, {msg})", "str", P_ATOM

    @staticmethod
    def _enum_text(node) -> str:
        parts = []

        def walk(n):
            if n[0] == "member":
                parts.append(n[2])
            elif n[0] == "bin":
                walk(n[2])
                walk(n[3])
            elif n[0] == "name":
                parts.append(n[1])
            elif n[0] == "num":
                v = int(n[1]) if n[1].isdigit() else 0
                parts.append({1: "OKCancel", 4: "YesNo", 3: "YesNoCancel", 5: "RetryCancel", 16: "Critical",
                              48: "Exclamation", 64: "Information"}.get(v & 7, "") +
                             {16: "Critical", 32: "Question", 48: "Exclamation", 64: "Information"}.get(v & 0x70, ""))
        walk(node)
        return " ".join(parts)

    def call_rule(self, obj, method, args):
        """Rules for obj.method(args); None = generic call."""
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        n = len(args)
        # ---- controls
        if obj[0] == "member" and obj[2] == "Items" and self.ctrl_of(obj[1]):
            code, kind = self.items_call(self.ctrl_of(obj[1]), method, args)
            return code, kind, P_ATOM
        cname = self.ctrl_of(obj)
        if cname is not None:
            t = self.controls[cname]
            s = f"self.{cname}"
            if method == "Focus" or method == "Select" and n == 0:
                return f"{s}.focus_set()", None, P_ATOM
            if method == "Clear" and t == "TextBox":
                if cname in self.multiline:
                    return f"{s}.delete(\"1.0\", \"end\")", None, P_ATOM
                return f"{s}_var.set(\"\")", None, P_ATOM
            if method == "SelectAll" and t == "TextBox":
                return f"{s}.select_range(0, \"end\")", None, P_ATOM
            if method in ("Start", "Stop") and t == "Timer":
                return f"{s}.{method}()", None, P_ATOM
            if method == "Hide":
                return f"{s}.place_forget()", None, P_ATOM
            if method == "Show":
                return f"{s}.place(**self._places[{pystr(cname)}])", None, P_ATOM
            if method in ("Refresh", "Invalidate", "Update"):
                return f"{s}.update_idletasks()", None, P_ATOM
            if method == "BringToFront":
                return f"{s}.lift()", None, P_ATOM
            if method == "SendToBack":
                return f"{s}.lower()", None, P_ATOM
            if method == "PerformClick":
                return f"{s}.invoke()", None, P_ATOM
            if method == "Increment" and t == "ProgressBar":
                return f"{s}.step({a(0)})", None, P_ATOM
            if method == "PerformStep" and t == "ProgressBar":
                return f"{s}.step()", None, P_ATOM
            if method == "ShowDialog" and t in ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog",
                                                "FolderBrowserDialog"):
                return f"{s}.ShowDialog()", "str", P_ATOM
            if method == "ToString" and n == 0:
                return self.ex(obj)
            raise Untranslatable(f"{t}.{method}()")
        # ---- the form itself
        if self.is_form(obj):
            if method in ("Close", "Dispose"):
                return "self.root.destroy()", None, P_ATOM
            if method == "Hide":
                return "self.root.withdraw()", None, P_ATOM
            if method in self.methods:
                return f"self.{method}({self.arglist(args)})", None, P_ATOM
            if method in ("Show", "Activate", "BringToFront"):
                return "self.root.deiconify()", None, P_ATOM
            if method in ("Refresh", "Invalidate", "Update"):
                return "self.root.update_idletasks()", None, P_ATOM
            raise Untranslatable(f"Form.{method}()")
        static = self.static_call(obj, method, args)
        if static is not None:
            return static
        # ---- instance methods by receiver kind
        code, kind, prec = self.exp(obj)
        oc = self.wrap((code, prec), P_ATOM)
        if method == "ToString":
            if n == 0:
                return (code, "str", prec) if kind == "str" else (f"str({code})", "str", P_ATOM)
            fmt = args[0][1] if args[0][0] == "str" else None
            if fmt is not None:
                spec = cs_format_spec(fmt)
                if spec:
                    return f"format({code}, {pystr(spec)})", "str", P_ATOM
                if kind == "datetime" or re.search(r"[yMdHhms]", fmt):
                    return f"{oc}.strftime({pystr(cs_date_format(fmt))})", "str", P_ATOM
            raise Untranslatable("ToString(format)")
        if kind == "sb":
            if method in ("Append", "AppendLine"):
                raise Untranslatable("StringBuilder")
        if kind == "list" or kind is None and method in ("Add", "AddRange", "RemoveAt", "Insert"):
            if method == "Add":
                return f"{oc}.append({a(0)})", None, P_ATOM
            if method == "AddRange":
                return f"{oc}.extend({a(0)})", None, P_ATOM
            if method == "RemoveAt":
                return f"del {oc}[{a(0)}]", None, P_ATOM
            if method == "Insert":
                return f"{oc}.insert({a(0)}, {a(1)})", None, P_ATOM
        if kind == "list":
            if method == "Clear":
                return f"{oc}.clear()", None, P_ATOM
            if method == "Contains":
                return f"{a(0)} in {code}", "bool", P_CMP
            if method == "IndexOf":
                return f"{oc}.index({a(0)})", "int", P_ATOM
            if method == "Remove":
                return f"{oc}.remove({a(0)})", None, P_ATOM
            if method == "Sort":
                return f"{oc}.sort()", None, P_ATOM
            if method == "Reverse":
                return f"{oc}.reverse()", None, P_ATOM
            if method == "ToArray" or method == "ToList":
                return f"list({code})", "list", P_ATOM
            if method == "Count" and n == 0:
                return f"len({code})", "int", P_ATOM
        if kind == "dict":
            if method in ("ContainsKey", "containsKey"):
                return f"{a(0)} in {code}", "bool", P_CMP
            if method == "Add":
                return f"{oc}[{a(0)}] = {a(1)}" if False else f"{oc}.__setitem__({a(0)}, {a(1)})", None, P_ATOM
            if method == "Remove":
                return f"{oc}.pop({a(0)}, None)", None, P_ATOM
            if method == "Clear":
                return f"{oc}.clear()", None, P_ATOM
        if kind == "random":
            if method == "Next":
                if n == 0:
                    return f"{oc}.randrange(2147483647)", "int", P_ATOM
                if n == 1:
                    return f"{oc}.randrange({a(0)})", "int", P_ATOM
                return f"{oc}.randrange({a(0)}, {a(1)})", "int", P_ATOM
            if method == "NextDouble":
                return f"{oc}.random()", "float", P_ATOM
        if kind == "datetime":
            if method in ("AddDays", "AddHours", "AddMinutes", "AddSeconds"):
                unit = method[3:].lower()
                return f"{oc} + datetime.timedelta({unit}={a(0)})", "datetime", P_ADD
        # string methods (receiver kind str or unknown)
        if kind in ("str", None):
            got = self.string_method(code, oc, kind, method, args)
            if got is not None:
                return got
        if method == "Equals" and n == 1:
            return f"{oc} == {a(0)}", "bool", P_CMP
        if method == "CompareTo" and n == 1:
            return f"(({oc} > {a(0)}) - ({oc} < {a(0)}))", "int", P_ATOM
        if method == "GetType":
            return f"type({code})", None, P_ATOM
        if kind not in (None, "str") or method[:1].isupper():
            if kind is None and method in ("Invoke", "BeginInvoke", "Dispose"):
                raise Untranslatable(f".{method}()")
        return None

    def string_method(self, code, oc, kind, method, args):
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        n = len(args)
        simple = {"Trim": "strip", "TrimStart": "lstrip", "TrimEnd": "rstrip", "ToUpper": "upper",
                  "ToUpperInvariant": "upper", "ToLower": "lower", "ToLowerInvariant": "lower",
                  "trim": "strip", "toUpperCase": "upper", "toLowerCase": "lower", "strip": "strip"}
        if method in simple and (n == 0 or method.startswith("Trim")):
            if n:
                chars = "".join(self.ex(x)[0].strip("\"'") for x in args)
                return f"{oc}.{simple[method]}({pystr(chars)})", "str", P_ATOM
            return f"{oc}.{simple[method]}()", "str", P_ATOM
        if kind != "str" and method not in ("Contains", "StartsWith", "EndsWith", "Substring", "Replace",
                                            "Split", "IndexOf", "PadLeft", "PadRight", "Insert", "Remove",
                                            "Equals", "LastIndexOf", "contains", "startsWith", "endsWith",
                                            "substring", "replace", "split", "indexOf", "isEmpty", "length",
                                            "equals", "equalsIgnoreCase", "charAt"):
            return None
        if method in ("Contains", "contains") and n == 1:
            return f"{self.wrap(self.exp(args[0])[::2], P_CMP + 1)} in {oc}", "bool", P_CMP
        if method in ("StartsWith", "startsWith"):
            return f"{oc}.startswith({a(0)})", "bool", P_ATOM
        if method in ("EndsWith", "endsWith"):
            return f"{oc}.endswith({a(0)})", "bool", P_ATOM
        if method in ("IndexOf", "indexOf"):
            return f"{oc}.find({', '.join(a(i) for i in range(n))})", "int", P_ATOM
        if method in ("LastIndexOf", "lastIndexOf"):
            return f"{oc}.rfind({a(0)})", "int", P_ATOM
        if method in ("Replace", "replace") and n == 2:
            return f"{oc}.replace({a(0)}, {a(1)})", "str", P_ATOM
        if method in ("Split", "split"):
            if n == 0:
                return f"{oc}.split()", "list", P_ATOM
            first = args[0]
            if first[0] == "newarr" and first[3]:
                first = first[3][0]
            sep = self.ex(first)[0]
            return f"{oc}.split({sep})", "list", P_ATOM
        if method == "Substring":
            if n == 1:
                return f"{oc}[{a(0)}:]", "str", P_ATOM
            start = a(0)
            end = a(1) if start == "0" else self._sum(start, a(1))
            return f"{oc}[{start}:{end}]", "str", P_ATOM
        if method == "substring":
            return (f"{oc}[{a(0)}:]" if n == 1 else f"{oc}[{a(0)}:{a(1)}]"), "str", P_ATOM
        if method == "PadLeft":
            return f"{oc}.rjust({', '.join(a(i) for i in range(n))})", "str", P_ATOM
        if method == "PadRight":
            return f"{oc}.ljust({', '.join(a(i) for i in range(n))})", "str", P_ATOM
        if method == "Insert" and n == 2 and kind == "str":
            return f"{oc}[:{a(0)}] + {a(1)} + {oc}[{a(0)}:]", "str", P_ADD
        if method in ("Equals", "equals") and n == 1:
            return f"{oc} == {a(0)}", "bool", P_CMP
        if method == "equalsIgnoreCase":
            return f"{oc}.lower() == {self.wrap(self.exp(args[0])[::2], P_ATOM)}.lower()", "bool", P_CMP
        if method == "isEmpty":
            return f"len({code}) == 0", "bool", P_CMP
        if method == "length" and n == 0:
            return f"len({code})", "int", P_ATOM
        if method == "charAt":
            return f"{oc}[{a(0)}]", "str", P_ATOM
        if method == "Remove" and kind == "str":
            if n == 1:
                return f"{oc}[:{a(0)}]", "str", P_ATOM
            return f"{oc}[:{a(0)}] + {oc}[{self._sum(a(0), a(1))}:]", "str", P_ADD
        return None

    @staticmethod
    def _sum(x: str, y: str) -> str:
        if re.fullmatch(r"-?\d+", x) and re.fullmatch(r"-?\d+", y):
            return str(int(x) + int(y))
        return f"{x} + {y}"

    def static_call(self, obj, method, args):
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        n = len(args)
        cls = None
        if obj[0] == "name" and not self.is_local(obj[1]) and obj[1] not in self.controls and \
                obj[1] not in self.fields:
            cls = obj[1]
        elif obj[0] == "member" and obj[1][0] in ("name", "member"):
            cls = obj[2]
        if cls is None:
            return None
        if cls in ("MessageBox", "Interaction") and method in ("Show", "MsgBox"):
            return self.msgbox(args, vb=(method == "MsgBox"))
        if cls == "Application" and method == "Exit":
            return "self.root.destroy()", None, P_ATOM
        if cls == "Application" and method == "DoEvents":
            return "self.root.update()", None, P_ATOM
        if cls == "Environment" and method == "Exit":
            self.imports.add("import sys")
            return f"sys.exit({a(0) if n else ''})", None, P_ATOM
        if cls == "Convert" or cls == "Conversions":
            to = method[2:] if method.startswith("To") else method
            if to in ("Int32", "Int16", "Int64", "Integer", "Long", "Short", "Byte", "UInt32"):
                return f"int({a(0)})", "int", P_ATOM
            if to in ("Double", "Decimal", "Single"):
                return f"float({a(0)})", "float", P_ATOM
            if to == "String":
                return f"str({a(0)})", "str", P_ATOM
            if to == "Boolean":
                return f"bool({a(0)})", "bool", P_ATOM
            if to == "Char":
                return f"chr({a(0)})", "str", P_ATOM
        if cls in ("int", "Int32", "long", "Int64", "short", "Int16", "byte") and method == "Parse":
            return f"int({a(0)})", "int", P_ATOM
        if cls in ("double", "Double", "decimal", "Decimal", "float", "Single") and method == "Parse":
            return f"float({a(0)})", "float", P_ATOM
        if cls in ("bool", "Boolean") and method == "Parse":
            return f"({a(0)}.strip().lower() == \"true\")", "bool", P_ATOM
        if cls in ("string", "String"):
            if method in ("IsNullOrEmpty",):
                return f"not {self.wrap(self.exp(args[0])[::2], P_NOT)}", "bool", P_NOT
            if method == "IsNullOrWhiteSpace":
                return f"not ({a(0)} or \"\").strip()", "bool", P_NOT
            if method == "Format" or method == "format":
                if args and args[0][0] == "str":
                    fmt = args[0][1]
                    if method == "format":
                        fmt = re.sub(r"%(\.\d+)?[sdf]", "{}", fmt)
                    fmt = re.sub(r"\{(\d+)(?:,(-?\d+))?(?::([^}]+))?\}",
                                 lambda m: "{" + m.group(1) + (":" + (cs_format_spec(m.group(3)) or "")
                                                                if m.group(3) else "") + "}", fmt)
                    rest = ", ".join(a(i) for i in range(1, n))
                    return f"{pystr(fmt)}.format({rest})", "str", P_ATOM
            if method == "Join" or method == "join":
                rest = a(1) if n == 2 else "[" + ", ".join(a(i) for i in range(1, n)) + "]"
                return f"{a(0)}.join(map(str, {rest}))", "str", P_ATOM
            if method == "Concat":
                return " + ".join(f"str({a(i)})" for i in range(n)), "str", P_ADD
            if method == "valueOf":
                return f"str({a(0)})", "str", P_ATOM
            if method in ("Compare", "CompareOrdinal"):
                return f"(({a(0)} > {a(1)}) - ({a(0)} < {a(1)}))", "int", P_ATOM
        if cls in ("Math", "MathF"):
            simple = {"Max": "max", "Min": "min", "Abs": "abs", "Round": "round"}
            if method in simple:
                return f"{simple[method]}({self.arglist(args)})", None, P_ATOM
            mm = {"Sqrt": "sqrt", "Pow": "pow", "Floor": "floor", "Ceiling": "ceil", "Sin": "sin", "Cos": "cos",
                  "Tan": "tan", "Log": "log", "Log10": "log10", "Exp": "exp", "Atan": "atan", "Atan2": "atan2",
                  "Truncate": "trunc"}
            if method in mm:
                self.imports.add("import math")
                return f"math.{mm[method]}({self.arglist(args)})", "float", P_ATOM
        if cls == "Console" and method in ("WriteLine", "Write"):
            return (f"print({self.arglist(args)})" if method == "WriteLine" else
                    f"print({self.arglist(args)}, end=\"\")"), None, P_ATOM
        if cls == "Debug" and method in ("WriteLine", "Print", "Write"):
            return f"print({self.arglist(args)})", None, P_ATOM
        if cls == "Thread" and method == "Sleep":
            self.imports.add("import time")
            return f"time.sleep({a(0)} / 1000)", None, P_ATOM
        if cls == "Color" and method == "FromArgb":
            vals = [a(i) for i in range(n)]
            if n >= 3:
                r, g, b = vals[-3:]
                if all(re.fullmatch(r"\d+", v) for v in (r, g, b)):
                    return pystr(f"#{int(r):02X}{int(g):02X}{int(b):02X}"), "str", P_ATOM
                return f"\"#%02X%02X%02X\" % ({r}, {g}, {b})", "str", P_MUL
        if cls == "Color" and method == "FromName":
            return f"{a(0)}.lower()", "str", P_ATOM
        if cls == "File":
            if method == "ReadAllText":
                return f"open({a(0)}, encoding=\"utf-8\").read()", "str", P_ATOM
            if method == "WriteAllText":
                return f"open({a(0)}, \"w\", encoding=\"utf-8\").write({a(1)})", None, P_ATOM
            if method == "AppendAllText":
                return f"open({a(0)}, \"a\", encoding=\"utf-8\").write({a(1)})", None, P_ATOM
            if method == "Exists":
                self.imports.add("import os")
                return f"os.path.isfile({a(0)})", "bool", P_ATOM
            if method == "ReadAllLines":
                return f"open({a(0)}, encoding=\"utf-8\").read().splitlines()", "list", P_ATOM
            if method == "Delete":
                self.imports.add("import os")
                return f"os.remove({a(0)})", None, P_ATOM
        if cls == "Directory" and method == "Exists":
            self.imports.add("import os")
            return f"os.path.isdir({a(0)})", "bool", P_ATOM
        if cls == "Path":
            self.imports.add("import os")
            if method == "Combine":
                return f"os.path.join({self.arglist(args)})", "str", P_ATOM
            if method == "GetFileName":
                return f"os.path.basename({a(0)})", "str", P_ATOM
            if method == "GetExtension":
                return f"os.path.splitext({a(0)})[1]", "str", P_ATOM
            if method == "GetDirectoryName":
                return f"os.path.dirname({a(0)})", "str", P_ATOM
        if cls == "Process" and method == "Start":
            self.imports.add("import os")
            return f"os.startfile({a(0)})", None, P_ATOM
        if cls == "Char" or cls == "char":
            m = {"IsDigit": "isdigit", "IsLetter": "isalpha", "IsUpper": "isupper", "IsLower": "islower",
                 "IsWhiteSpace": "isspace", "IsLetterOrDigit": "isalnum", "ToUpper": "upper",
                 "ToLower": "lower"}.get(method)
            if m:
                return f"{self.wrap(self.exp(args[0])[::2], P_ATOM)}.{m}()", \
                    ("bool" if method.startswith("Is") else "str"), P_ATOM
        if cls == "Operators" and method == "CompareString":
            return f"(({a(0)} > {a(1)}) - ({a(0)} < {a(1)}))", "int", P_ATOM
        if cls in ("Strings",):
            m = {"Trim": "strip", "UCase": "upper", "LCase": "lower"}.get(method)
            if m:
                return f"{a(0)}.{m}()", "str", P_ATOM
            if method == "Len":
                return f"len({a(0)})", "int", P_ATOM
        if cls in ("Interaction",) and method == "InputBox":
            self.imports.add("from tkinter import simpledialog")
            title = a(1) if n > 1 else '""'
            return f"(simpledialog.askstring({title}, {a(0)}) or \"\")", "str", P_ATOM
        return None


# WinForms event -> RAD IDE event (PyEmitter reads it; winforms_reader.parse_winforms maps the event wiring)
EVENT_MAP = {"Click": "Click", "DoubleClick": "DoubleClick", "TextChanged": "TextChanged",
             "CheckedChanged": "CheckedChanged", "SelectedIndexChanged": "SelectedIndexChanged",
             "SelectedValueChanged": "SelectedIndexChanged", "ValueChanged": "ValueChanged",
             "Scroll": "ValueChanged", "Tick": "Tick", "Load": "Load", "Shown": "Activated",
             "Activated": "Activated", "Deactivate": "Deactivate", "Resize": "Resize", "SizeChanged": "Resize",
             "FormClosing": "FormClosing", "FormClosed": "FormClosed", "KeyDown": "KeyDown", "KeyUp": "KeyUp",
             "KeyPress": "KeyPress", "MouseDown": "MouseDown", "MouseUp": "MouseUp", "MouseMove": "MouseMove",
             "MouseClick": "Click", "MouseDoubleClick": "DoubleClick", "MouseEnter": "MouseEnter",
             "MouseLeave": "MouseLeave", "MouseWheel": "MouseWheel", "Enter": "GotFocus", "GotFocus": "GotFocus",
             "Leave": "LostFocus", "LostFocus": "LostFocus", "LinkClicked": "Click",
             "CellValueChanged": "CellChanged", "AfterSelect": "SelectedIndexChanged"}
