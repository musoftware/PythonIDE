"""WinForms forms of Visual Studio VB.NET projects, opened IN PLACE (Form1.Designer.vb + Form1.vb).

The engine (statement spans, neutral model, minimal patching, .resx) is shared with winforms_cs.py;
this module is the VB.NET dialect: statements are logical lines (``_`` and implicit continuation),
expressions are translated to C# text only to be *read* by the shared parser, and new code is written
in VB syntax (``Me.Button1 = New System.Windows.Forms.Button()``, ``Friend WithEvents``, ``Handles``).
"""
from __future__ import annotations

import bisect
import re
from pathlib import Path

from ..controls import FORM_EVENTS
from ..languages.base import RunSpec
from .winforms_cs import (EVENT_SIG, EVENT_TO_NET, CSharpDialect, Stmt, WinFormsCSPlugin, _code_file_of,
                          handler_signature, new_code_text, new_designer_text, render_form)

# ============================================================================ VB -> C# (for reading only)
_TOK = re.compile(r"""
    (?P<ws>[ \t]+|\s*_[ \t]*\r?\n\s*|\r?\n\s*) |
    (?P<chr>"(?:[^"]|"")"[cC](?!\w)) |
    (?P<str>"(?:[^"]|"")*") |
    (?P<num>&[hH][0-9A-Fa-f]+[SILUsilu%&]*|&[oO][0-7]+|\d+\.\d*(?:[eE][+-]?\d+)?[!#@FRDfrd]?|\.\d+[!#@FRDfrd]?|\d+(?:[eE][+-]?\d+)?[!#@%&SILUFRDsilufrd]*) |
    (?P<id>\[\w+\]|[A-Za-z_]\w*) |
    (?P<op><>|<=|>=|:=|&=|\+=|-=|[-+*/\\^&=<>(){}.,:!?]) |
    (?P<other>.)
""", re.X | re.S)

_KW = {"true": "true", "false": "false", "nothing": "null", "me": "this", "mybase": "base", "myclass": "this",
       "or": "|", "and": "&", "orelse": "||", "andalso": "&&", "not": "!", "mod": "%", "xor": "^",
       "new": "new", "is": "==", "isnot": "!="}
_CONV = {"cbyte": "byte", "cint": "int", "clng": "long", "cshort": "short", "csng": "float", "cdbl": "double",
         "cdec": "decimal", "cstr": "string", "cbool": "bool", "cchar": "char", "cuint": "uint", "cobj": "object"}
_TYPES = {"integer": "int", "string": "string", "object": "object", "byte": "byte", "single": "float",
          "double": "double", "boolean": "bool", "decimal": "decimal", "long": "long", "short": "short",
          "char": "char"}


def _tokens(s: str) -> list[tuple[str, str]]:
    out = []
    for m in _TOK.finditer(s):
        k = m.lastgroup
        if k == "ws":
            continue
        out.append((k, m.group(0)))
    return out


def _vb_str_to_cs(tok: str) -> str:
    body = tok[1:-1].replace('""', '"')
    return '"' + body.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _num(tok: str) -> str:
    t = tok
    if t[:2].lower() == "&h":
        return "0x" + re.sub(r"[SILUsilu%&]+$", "", t[2:])
    if t[:2].lower() == "&o":
        return str(int(t[2:], 8))
    m = re.match(r"^([\d.eE+-]+)([!#@%&A-Za-z]*)$", t)
    if not m:
        return t
    n, suf = m.group(1), m.group(2).upper()
    if suf in ("!", "F"):
        return n + "F"
    if suf in ("@", "D"):
        return n + "M"
    if suf in ("#", "R"):
        return n + "D"
    return n


def _match(toks, i) -> int:
    """Index of the ')' / '}' closing toks[i]."""
    depth = 0
    for j in range(i, len(toks)):
        v = toks[j][1]
        if v in ("(", "{"):
            depth += 1
        elif v in (")", "}"):
            depth -= 1
            if depth == 0:
                return j
    return len(toks) - 1


def _split_args(toks) -> list[list]:
    out, cur, depth = [], [], 0
    for t in toks:
        v = t[1]
        if v in ("(", "{"):
            depth += 1
        elif v in (")", "}"):
            depth -= 1
        if v == "," and depth == 0:
            out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur or out:
        out.append(cur)
    return out


def _type_text(toks) -> str:
    s = "".join(t[1] for t in toks).replace("Global.", "")
    s = re.sub(r"\(Of\s*", "<", s, flags=re.I)
    return _TYPES.get(s.lower(), s)


def conv_expr(toks) -> str:
    out: list[str] = []
    i = 0
    n = len(toks)
    while i < n:
        k, v = toks[i]
        low = v.lower()
        if k == "str":
            out.append(_vb_str_to_cs(v))
        elif k == "chr":
            c = v[1:-2].replace('""', '"')
            out.append("'\\''" if c == "'" else "'\\\\'" if c == "\\" else f"'{c}'")
        elif k == "num":
            out.append(_num(v))
        elif k == "id" and low == "global" and i + 1 < n and toks[i + 1][1] == ".":
            i += 2
            continue
        elif k == "id" and low in ("ctype", "directcast", "trycast") and i + 1 < n and toks[i + 1][1] == "(":
            j = _match(toks, i + 1)
            args = _split_args(toks[i + 2:j])
            if len(args) == 2:
                inner, typ = conv_expr(args[0]), _type_text(args[1])
                out.append(f"(({typ})({inner}))" if low != "trycast" else f"({inner} as {typ})")
            else:
                out.append("(" + conv_expr(toks[i + 2:j]) + ")")
            i = j + 1
            continue
        elif k == "id" and low in _CONV and i + 1 < n and toks[i + 1][1] == "(":
            j = _match(toks, i + 1)
            out.append(f"(({_CONV[low]})({conv_expr(toks[i + 2:j])}))")
            i = j + 1
            continue
        elif k == "id" and low == "gettype" and i + 1 < n and toks[i + 1][1] == "(":
            j = _match(toks, i + 1)
            out.append(f"typeof({_type_text(toks[i + 2:j])})")
            i = j + 1
            continue
        elif k == "id" and low in ("chrw", "chr") and i + 1 < n and toks[i + 1][1] == "(":
            j = _match(toks, i + 1)
            inner = conv_expr(toks[i + 2:j])
            try:
                c = chr(int(inner, 0))
                out.append("'\\''" if c == "'" else "'\\\\'" if c == "\\" else
                           f"'\\u{ord(c):04x}'" if not c.isprintable() else f"'{c}'")
            except ValueError:
                out.append(f"((char)({inner}))")
            i = j + 1
            continue
        elif k == "id" and low == "new":
            # New T(args) {..}  /  New T() {items} (array)
            j = i + 1
            typ = []
            while j < n and (toks[j][0] == "id" or toks[j][1] == "."):
                typ.append(toks[j])
                j += 1
            tname = _type_text(typ)
            if j < n and toks[j][1] == "(" and j + 1 < n and toks[j + 1][1] == ")" and j + 2 < n and \
                    toks[j + 2][1] == "{":
                e = _match(toks, j + 2)
                items = _split_args(toks[j + 3:e])
                out.append(f"new {tname}[] {{" + ", ".join(conv_expr(x) for x in items if x) + "}")
                i = e + 1
                continue
            if j < n and toks[j][1] == "(":
                e = _match(toks, j)
                args = _split_args(toks[j + 1:e])
                out.append(f"new {tname}(" + ", ".join(conv_expr(x) for x in args if x) + ")")
                i = e + 1
                continue
            out.append(f"new {tname}()")
            i = j
            continue
        elif k == "id" and low in _KW:
            out.append(_KW[low])
        elif k == "id" and v.startswith("["):
            out.append(v[1:-1])
        elif k == "op" and v == "<>":
            out.append("!=")
        elif k == "op" and v == "&":
            out.append("+")
        elif k == "op" and v in ("(", ")", "{", "}", ".", ","):
            out.append(v)
        else:
            out.append(v)
        i += 1
    # join with spaces where needed
    s = ""
    for t in out:
        if s and (s[-1].isalnum() or s[-1] in "_'\"") and (t[0].isalnum() or t[0] in "_'\"("):
            if t[0] == "(" and s[-1].isalnum():
                s += t
                continue
            s += " "
        s += t if t not in ("|", "&", "||", "&&", "==", "!=", "%", "^", "=", "+") else f" {t} "
    return s


MAX_STATEMENT = 100_000     # chars: no designer statement gets near this (a corrupted / generated file)


def vb_to_cs(stmt: str) -> str | None:
    """One VB statement (designer subset) -> C# text for the shared parser; None = not understood."""
    if len(stmt) > MAX_STATEMENT:
        return None
    try:
        return _vb_to_cs(stmt)
    except RecursionError:      # expressions nested thousands of levels deep
        return None


def _vb_to_cs(stmt: str) -> str | None:
    s = _strip_comment(stmt).strip()
    if not s:
        return None
    m = re.match(r"(?is)^AddHandler\s+(.+?),\s*AddressOf\s+(.+)$", s)
    if m:
        return f"{conv_expr(_tokens(m.group(1)))} += {conv_expr(_tokens(m.group(2)))};"
    m = re.match(r"(?is)^Dim\s+(\w+)\s+As\s+New\s+([\w.]+)\s*(\(.*\))?$", s)
    if m:
        return f"{_type_text(_tokens(m.group(2)))} {m.group(1)} = new {m.group(2)}{conv_expr(_tokens(m.group(3) or '()'))};"
    m = re.match(r"(?is)^Dim\s+(\w+)\s+As\s+([\w.]+)\s*=\s*(.+)$", s)
    if m:
        return f"{_type_text(_tokens(m.group(2)))} {m.group(1)} = {conv_expr(_tokens(m.group(3)))};"
    if re.match(r"(?i)^(RemoveHandler|With|End|If|For|Next|Dim|Call|Try|Catch)\b", s):
        if s.lower().startswith("call "):
            s = s[5:]
        else:
            return None
    toks = _tokens(s)
    # assignment at depth 0
    depth = 0
    for i, (k, v) in enumerate(toks):
        if v in ("(", "{"):
            depth += 1
        elif v in (")", "}"):
            depth -= 1
        elif v == "=" and depth == 0:
            return f"{conv_expr(toks[:i])} = {conv_expr(toks[i + 1:])};"
        elif v in ("+=", "&=", "-=") and depth == 0:
            return None
    return conv_expr(toks) + ";"


def _strip_comment(s: str) -> str:
    out = []
    i = 0
    in_str = False
    while i < len(s):
        c = s[i]
        if c == '"':
            in_str = not in_str
        elif c == "'" and not in_str:
            break
        elif not in_str and s[i:i + 4].upper() == "REM " and (i == 0 or not s[i - 1].isalnum()):
            break
        out.append(c)
        i += 1
    text = "".join(out)
    return re.sub(r"[ \t]+_[ \t]*\r?\n", " ", text)


class _IncrementalStrip:
    """_strip_comment(s[start:j]) for a growing j: upto(j) -> (bracket depth, rstripped tail). Each char
    is scanned once (the rules are those of _strip_comment; the tail is taken from the last 4000 chars)."""

    def __init__(self, s: str, start: int):
        self.s, self.i, self.in_str, self.stopped = s, start, False, False
        self.start = start
        self.out: list[str] = []
        self.depth = 0

    def upto(self, j: int) -> tuple[int, str]:
        s, out = self.s, self.out
        i, in_str = self.i, self.in_str
        while not self.stopped and i < j:
            c = s[i]
            if c == '"':
                in_str = not in_str
            elif c == "'" and not in_str:
                self.stopped = True
                break
            elif not in_str and c in "rR" and s[i:min(i + 4, j)].upper() == "REM " and \
                    (i == self.start or not s[i - 1].isalnum()):
                self.stopped = True
                break
            out.append(c)
            if c in "({":
                self.depth += 1
            elif c in ")}":
                self.depth -= 1
            i += 1
        self.i, self.in_str = i, in_str
        tail = re.sub(r"[ \t]+_[ \t]*\r?\n", " ", "".join(out[-4000:])).rstrip()
        return self.depth, tail


# ============================================================================ dialect
class VBDialect(CSharpDialect):
    lang = "vb"
    ext = ".vb"
    comment = "'"

    def find_class(self, text: str, name_hint: str = ""):
        rx = re.compile(r"(?im)^[ \t]*(?:(?:Partial|Public|Friend|Private|NotInheritable|MustInherit|Protected)"
                        r"\s+)*Class\s+(\w+)[^\n]*\n")
        for m in rx.finditer(text):
            if name_hint and m.group(1).lower() != name_hint.lower():
                continue
            e = re.compile(r"(?im)^[ \t]*End\s+Class\b").search(text, m.end())
            if e:
                return m.group(1), m.end(), e.start(), m.start()
        m = rx.search(text)
        if m:
            e = re.compile(r"(?im)^[ \t]*End\s+Class\b").search(text, m.end())
            if e:
                return m.group(1), m.end(), e.start(), m.start()
        return None

    def find_ic(self, text: str, b0: int, b1: int):
        m = re.compile(r"(?im)^[ \t]*(?:(?:Private|Public|Friend|Protected|Overridable|Overrides)\s+)*"
                       r"Sub\s+InitializeComponent\s*\(\s*\)[^\n]*\n").search(text, b0, b1)
        if not m:
            return None
        e = re.compile(r"(?im)^[ \t]*End\s+Sub\b").search(text, m.end(), b1)
        if not e:
            return None
        return m.end(), e.start()

    def split(self, text: str, b0: int, b1: int) -> list[Stmt]:
        out: list[Stmt] = []
        i = b0
        while i < b1:
            # one physical line (plus continuations)
            j = text.find("\n", i)
            j = b1 if j < 0 or j > b1 else j + 1
            line = text[i:j]
            stripped = line.strip()
            if not stripped:
                i = j
                continue
            s0 = i + (len(line) - len(line.lstrip()))
            if stripped.startswith("'") or stripped.upper().startswith("REM "):
                kind = "comment"
            elif stripped.startswith("#"):
                kind = "directive"
            else:
                kind = "code"
                # continuation: trailing " _" or open brackets / trailing comma / operator
                strip = _IncrementalStrip(text, s0)
                while j < b1:
                    # = _strip_comment(text[s0:j]) and its bracket depth, without re-scanning the lines
                    # already joined (an unclosed "(" in a corrupted file made this quadratic)
                    depth, tail = strip.upto(j)
                    if re.search(r"(\s_|,|\{|\(|\b(Or|And|OrElse|AndAlso)|[&+=])$", tail) or depth > 0:
                        k = text.find("\n", j)
                        j = b1 if k < 0 or k > b1 else k + 1
                        continue
                    break
            s1 = j
            while s1 > s0 and text[s1 - 1] in "\r\n":
                s1 -= 1
            st = self._stmt(text, s0, s1, b0, b1, kind)
            out.append(st)
            i = j
        return out

    def to_cs(self, stmt_text: str) -> str | None:
        return vb_to_cs(stmt_text)

    def field_decls(self, text: str, b0: int, b1: int, ic_span) -> dict:
        out = {}
        rx = re.compile(r"(?im)^[ \t]*(?:(?:Friend|Private|Public|Protected|Dim|Shared|ReadOnly)\s+)+"
                        r"(?:WithEvents\s+)?(\w+)\s+As\s+(?:New\s+)?([\w.]+(?:\(Of [^)]*\))?)[^\n]*\n?")
        subs = []
        head = re.compile(r"(?im)^[ \t]*(?:(?:Private|Public|Protected|Friend|Overrides|Overridable|Shared|Async|"
                          r"Partial|Overloads|Shadows|ReadOnly|WriteOnly|Iterator)\s+)*(Sub|Function|Property)\s+\w+")
        ends: dict[str, tuple[list, list]] = {}      # kind -> (starts, ends) of its "End <kind>" lines
        for m in head.finditer(text, b0, b1):
            kind = m.group(1).lower()
            if kind not in ends:      # found once, then bisected: thousands of headers without an "End Sub"
                found = [(e.start(), e.end()) for e in    # (a corrupted file) made this quadratic
                         re.compile(rf"(?im)^[ \t]*End\s+{m.group(1)}\b").finditer(text, b0, b1)]
                ends[kind] = ([a for a, _ in found], [b for _, b in found])
            starts, stops = ends[kind]
            k = bisect.bisect_left(starts, m.end())
            if k < len(starts):
                subs.append((m.start(), stops[k]))
        for m in rx.finditer(text, b0, b1):
            if any(a <= m.start() < b for a, b in subs):
                continue
            out[m.group(1)] = (m.group(2), m.start(), m.end())
        return out

    # ---------------------------------------------------------------- emission
    def lit_str(self, s: str) -> str:
        parts = re.split(r"(\r\n|\n|\r|\t)", s)
        out = []
        for p in parts:
            if p in ("\r\n",):
                out.append("Global.Microsoft.VisualBasic.ChrW(13) & Global.Microsoft.VisualBasic.ChrW(10)")
            elif p in ("\n", "\r", "\t"):
                out.append(f"Global.Microsoft.VisualBasic.ChrW({ord(p)})")
            elif p or not out:
                out.append('"' + p.replace('"', '""') + '"')
        return " & ".join(x for x in out if x) or '""'

    def lit_char(self, s: str) -> str:
        c = (s or "\0")[:1]
        return '"' + c.replace('"', '""') + '"c'

    def lit_bool(self, b: bool) -> str:
        return "True" if b else "False"

    def lit_float(self, v: float) -> str:
        s = repr(float(v))
        return s + "!"

    def new(self, typ: str, args: str = "") -> str:
        return f"New {typ}({args})"

    def enum_or(self, parts: list[str], typ: str) -> str:
        if len(parts) == 1:
            return parts[0]
        return f"CType(({' Or '.join(parts)}), {typ})" if self.style.qualified else " Or ".join(parts)

    def new_array(self, typ: str, items: list[str], ind: str) -> str:
        return f"New {typ}() {{" + ", ".join(items) + "}"

    def assign(self, target: str, value: str) -> str:
        return f"{target} = {value}"

    def call(self, target: str, args: str = "") -> str:
        return f"{target}({args})"

    def wire(self, owner_expr: str, event: str, handler: str, delegate: str) -> str:
        return f"AddHandler {owner_expr}.{event}, AddressOf {handler}"

    def field_decl(self, name: str, typ: str) -> str:
        return f"Friend WithEvents {name} As {typ}"

    def comment_line(self, text: str) -> str:
        sp = " " if getattr(getattr(self, "style", None), "comment_space", False) else ""
        return f"'{sp}{text}"

    def resources_decl(self, cls: str) -> str:
        t = "System.ComponentModel.ComponentResourceManager"
        return f"Dim resources As {t} = New {t}(GetType({cls}))"

    def get_object(self, key: str, typ: str) -> str:
        return f"CType(resources.GetObject({self.lit_str(key)}), {typ})"

    def components_new(self) -> str:
        return f"{self.style.me}components = New System.ComponentModel.Container()"

    @staticmethod
    def field_insert_point(doc, nl: str):
        """VS puts the WithEvents fields after InitializeComponent's End Sub, before End Class."""
        text = doc.text
        line_start = text.rfind("\n", 0, doc.b1) + 1
        cls_line = text.rfind("\n", 0, doc.cls_start) + 1
        ind = re.match(r"[ \t]*", text[cls_line:]).group(0) + "    "
        return line_start, "", ind


VB_TEMPLATE = """<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>\r
Partial Class {name}\r
    Inherits System.Windows.Forms.Form\r
\r
    'Form overrides dispose to clean up the component list.\r
    <System.Diagnostics.DebuggerNonUserCode()>\r
    Protected Overrides Sub Dispose(disposing As Boolean)\r
        Try\r
            If disposing AndAlso components IsNot Nothing Then\r
                components.Dispose()\r
            End If\r
        Finally\r
            MyBase.Dispose(disposing)\r
        End Try\r
    End Sub\r
\r
    'Required by the Windows Form Designer\r
    Private components As System.ComponentModel.IContainer\r
\r
    'NOTE: The following procedure is required by the Windows Form Designer\r
    'It can be modified using the Windows Form Designer.  \r
    'Do not modify it using the code editor.\r
    <System.Diagnostics.DebuggerStepThrough()>\r
    Private Sub InitializeComponent()\r
        components = New System.ComponentModel.Container()\r
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font\r
        Me.ClientSize = New System.Drawing.Size(800, 450)\r
        Me.Text = "{name}"\r
    End Sub\r
\r
End Class\r
"""


# ============================================================================ code-behind (Form1.vb)
def handles_map(code: str, form_name: str) -> dict[str, str]:
    """'Owner.Event' -> method for every `Sub X(...) Handles a.b, c.d` of the code file."""
    out = {}
    rx = re.compile(r"(?im)^[ \t]*(?:(?:Private|Public|Protected|Friend|Shared|Async|Overridable)\s+)*Sub\s+"
                    r"(\w+)\s*\([^)]*\)\s*Handles\s+([^\r\n']+)")
    for m in rx.finditer(code):
        for part in m.group(2).split(","):
            part = part.strip()
            if "." not in part:
                continue
            owner, ev = part.rsplit(".", 1)
            if owner.lower() in ("me", "mybase", "myclass"):
                owner = form_name
            out[f"{owner}.{ev}"] = m.group(1)
    return out


def find_handler_vb(code: str, name: str) -> int:
    rx = re.compile(rf"(?i)^\s*(?:(?:Private|Public|Protected|Friend|Shared|Async)\s+)*Sub\s+{re.escape(name)}\b")
    for i, ln in enumerate(code.splitlines()):
        if rx.search(ln):
            return i
    return -1


def add_event_handler_vb(code: str, form_name: str, method: str, owner: str, event: str) -> tuple[str, int]:
    """`Private Sub m(sender As Object, e As EventArgs) Handles Owner.Event` before End Class."""
    nl = "\r\n" if "\r\n" in code else "\n"
    args = handler_signature(event)
    who = "MyBase" if owner in ("", form_name) else owner
    m = None
    for mm in re.finditer(r"(?im)^[ \t]*(?:(?:Public|Partial|Friend|Private)\s+)*Class\s+(\w+)", code):
        if mm.group(1).lower() == form_name.lower() or m is None:
            m = mm
    end = re.compile(r"(?im)^[ \t]*End\s+Class\b").search(code, m.end()) if m else None
    sig = f"Private Sub {method}(sender As Object, e As {args}) Handles {who}.{event}"
    if end is None:
        code = code.rstrip("\r\n") + nl + f"Public Class {form_name}{nl}{nl}    {sig}{nl}{nl}    End Sub{nl}End Class{nl}"
        return code, code.count("\n") - 2
    cls_ind = re.match(r"[ \t]*", code[code.rfind("\n", 0, m.start()) + 1:]).group(0)
    ind = cls_ind + "    "
    before = code[:end.start()]
    sep = "" if before.rstrip("\r\n").endswith(tuple("\r\n")) or before.rstrip(" \t").endswith(nl + nl) else nl
    if re.search(r"Class\s+\w+[^\n]*\n\s*$", before):
        sep = ""
    stub = f"{sep}{ind}{sig}{nl}{ind}    {nl}{ind}End Sub{nl}"
    if not before.endswith("\n"):
        stub = nl + stub
    new = before + stub + code[end.start():]
    line = before.count("\n") + stub.count("\n") - 1
    return new, line


class WinFormsVBPlugin(WinFormsCSPlugin):
    id = "winforms-vb"
    display_name = "VB.NET WinForms (Visual Studio project)"
    code_ext = ".vb"
    keywords = ("AddHandler AddressOf Alias And AndAlso As Boolean ByRef Byte ByVal Call Case Catch CBool CByte "
                "CChar CDate CDbl CDec Char CInt Class CLng CObj Const Continue CSByte CShort CSng CStr CType "
                "Date Decimal Declare Default Delegate Dim DirectCast Do Double Each Else ElseIf End Enum Erase "
                "Error Event Exit False Finally For Friend Function Get GetType Global GoTo Handles If "
                "Implements Imports In Inherits Integer Interface Is IsNot Let Lib Like Long Loop Me Mod Module "
                "MustInherit MustOverride MyBase MyClass Namespace New Next Not Nothing Object Of On Operator "
                "Option Optional Or OrElse Overloads Overridable Overrides ParamArray Partial Private Property "
                "Protected Public RaiseEvent ReadOnly ReDim RemoveHandler Resume Return Select Set Shadows "
                "Shared Short Single Static Step Stop String Structure Sub SyncLock Then Throw To True Try "
                "TryCast TypeOf UInteger ULong UShort Using When While With WithEvents WriteOnly Xor").split()
    case_sensitive = False
    line_comments = ["'"]
    block_comment = None
    string_quotes = ['"']
    dialect_lang = "vb"

    def events_for(self, ctrl):
        if ctrl is None:
            return list(FORM_EVENTS)
        return super().events_for(ctrl)

    def rename_symbol(self, code: str, old: str, new: str) -> str:
        return re.sub(rf"(?i)\b{re.escape(old)}\b", new, code)

    def find_handler(self, code: str, name: str) -> int:
        return find_handler_vb(code, name)

    def add_handler(self, code: str, name: str, form, args: str | None = None) -> tuple[str, int]:
        pend = self._pending.get(name)
        owner, event = (pend[1], pend[2]) if pend else (name.rsplit("_", 1) + [""])[:2]
        out = add_event_handler_vb(code, form.name, name, owner, event)
        wf = form.extra.setdefault("winforms", {})
        wf.setdefault("events", {})[f"{owner}.{event}"] = name      # Handles clause = the wiring
        return out

    def generate_designer(self, form, user_code: str) -> str:
        if (form.extra.get("winforms") or {}).get("designer"):
            text, _rep, _r = render_form(form, user_code)
            return text
        return new_designer_text(form, "vb")

    def new_code(self, form, is_startup: bool) -> str:
        return new_code_text(form, "vb")

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(interpreter or "dotnet", ["run"], folder)


PLUGIN = WinFormsVBPlugin()
__all__ = ["PLUGIN", "VBDialect", "vb_to_cs", "handles_map", "add_event_handler_vb", "find_handler_vb",
           "EVENT_SIG", "EVENT_TO_NET", "_code_file_of"]
