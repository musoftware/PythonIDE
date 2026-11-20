""".NET programs (C# / VB.NET, WinForms) -> RAD IDE project (docs/CONTRACTS.md 10.3).

1. ``ilspycmd`` (the ILSpy command line, a dotnet tool installed into %LOCALAPPDATA%\\RADIDE\\tools)
   decompiles the assembly into a C# project (kept as the import's ``source_dir``).
2. Every WinForms ``Form`` class: ``InitializeComponent`` is read statement by statement and becomes a
   neutral ``.form`` (controls, Location/Size/Text/Font/colours/Anchor/Dock, menus, tool bars, tab pages,
   containers, event wiring).
3. Event handler bodies and the other methods of the form are translated to Python (python-tk) by rules
   for the common WinForms / BCL APIs (MessageBox.Show, Text/Checked/Items..., Convert/Parse, string and
   Math methods, if/for/foreach/while/switch/try).  Lines the rules do not know stay in the code as
   ``# C#: ...`` comments; with ``ai_translate`` the user's AI provider (radide.ai) rewrites the methods
   that still contain such lines.

The C-like parser and the Python emitter below are shared with java.py (Swing rules subclass them).
Only for programs you wrote, own, or may legally analyse.
"""
from __future__ import annotations

import json
import keyword
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .base import BinaryInfo, ImportResult, ai_translate as _base_ai_translate, find_tool, tools_dir

ILSPY_VERSIONS = (None, "9.1.0.7988", "8.2.0.7535")   # newest first; 9.x runs on the .NET 8/9 SDKs


# ============================================================================ shared helpers
def say(progress, text: str) -> None:
    if progress is None:
        return
    try:
        progress(text)
    except TypeError:
        try:
            progress(0, text)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


def run_tool(cmd: list[str], cwd: Path | None = None, timeout: int = 900, env: dict | None = None
             ) -> tuple[int, str]:
    """Run a command without a console window; (exit code, stdout+stderr)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags,
                           env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout} s: {' '.join(cmd[:3])}"
    except OSError as e:
        return -1, str(e)


def download(url: str, dest: Path, progress=None, timeout: int = 120) -> bool:
    """Download *url* to *dest* (atomic rename).  Used only for open-source tools in tools_dir()."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    say(progress, f"Downloading {url.rsplit('/', 1)[-1]} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RADIDE-importer"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as fh:
            shutil.copyfileobj(r, fh)
        if tmp.stat().st_size < 1024:
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, dest)
        return True
    except Exception:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        return False


def ai_rewrite(source: str, source_lang: str, context: str, progress=None) -> tuple[str | None, str]:
    """AI translation through base.ai_translate (CONTRACTS 9.1), never raises."""
    try:
        return _base_ai_translate(source, source_lang, "Python (tkinter)", context, progress)
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def pystr(value: str) -> str:
    """A double-quoted Python string literal."""
    out = repr(value)
    if out.startswith("'") and '"' not in value:
        out = '"' + out[1:-1].replace("\\'", "'") + '"'
    return out


PY_RESERVED = set(keyword.kwlist) | {"str", "int", "len", "list", "dict", "float", "bool", "type", "print",
                                     "max", "min", "abs", "round", "range", "self", "object", "id", "input",
                                     "sum", "format", "map", "next", "iter", "set", "math", "random",
                                     "messagebox", "datetime", "tk"}


def py_ident(name: str) -> str:
    name = name.lstrip("@")
    return name + "_" if name in PY_RESERVED else name


# ============================================================================ tokenizer
class Tok:
    __slots__ = ("kind", "val", "pos", "end")

    def __init__(self, kind, val, pos, end):
        self.kind, self.val, self.pos, self.end = kind, val, pos, end

    def __repr__(self):
        return f"{self.kind}:{self.val!r}"


_OPS = sorted(["<<=", ">>=", ">>>", "...", "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=",
               "%=", "&=", "|=", "^=", "=>", "??", "?.", "::", "->", "<<", "+", "-", "*", "/", "%", "&", "|",
               "^", "!", "~", "<", ">", "=", "?", ":", ".", ",", ";", "(", ")", "[", "]", "{", "}", "@", "#"],
              key=len, reverse=True)
_NUM = re.compile(r"0[xX][0-9a-fA-F_]+[uUlL]*|0[bB][01_]+[uUlL]*|(\d[\d_]*\.?[\d_]*|\.\d[\d_]*)([eE][+-]?\d+)?"
                  r"[fFdDmMlLuU]*")
_ESC = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'", '"': '"', "a": "\a", "b": "\b",
        "f": "\f", "v": "\v"}


class ParseError(Exception):
    pass


def _unescape(body: str) -> str:
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            n = body[i + 1]
            if n in "uU" and i + 6 <= len(body):
                try:
                    out.append(chr(int(body[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            if n == "x":
                m = re.match(r"[0-9a-fA-F]{1,4}", body[i + 2:])
                if m:
                    out.append(chr(int(m.group(0), 16)))
                    i += 2 + len(m.group(0))
                    continue
            out.append(_ESC.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def tokenize(src: str) -> list[Tok]:
    toks: list[Tok] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n\f\ufeff":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "#" and (not toks or src.rfind("\n", 0, i) >= toks[-1].end or not toks):   # preprocessor line
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        # strings: "..", @"..", $"..", $@"..", @$"..", """raw""" (C# 11 / Java text blocks)
        m = re.match(r'(\$@|@\$|\$|@)?"', src[i:i + 3])
        if m:
            prefix = m.group(1) or ""
            j = i + len(m.group(0))
            if src.startswith('""', j) and not prefix.count("@"):        # """ raw / text block
                k = src.find('"""', j + 2)
                k = n if k < 0 else k
                body = src[j + 2:k].strip("\n")
                toks.append(Tok("str", body, i, k + 3))
                i = k + 3
                continue
            verbatim = "@" in prefix
            buf, k, depth = [], j, 0
            while k < n:
                ch = src[k]
                if "$" in prefix and ch == "{":
                    if src.startswith("{{", k) and depth == 0:
                        buf.append("{{")
                        k += 2
                        continue
                    depth += 1
                elif "$" in prefix and ch == "}" and depth:
                    depth -= 1
                if depth == 0:
                    if verbatim and ch == '"':
                        if src.startswith('""', k):
                            buf.append('"')
                            k += 2
                            continue
                        break
                    if not verbatim and ch == "\\":
                        buf.append(src[k:k + 2])
                        k += 2
                        continue
                    if not verbatim and ch == '"':
                        break
                elif ch == '"' and not verbatim:          # string inside an interpolation hole
                    e = k + 1
                    while e < n and src[e] != '"':
                        e += 2 if src[e] == "\\" else 1
                    buf.append(src[k:e + 1])
                    k = e + 1
                    continue
                buf.append(ch)
                k += 1
            raw = "".join(buf)
            if "$" in prefix:
                toks.append(Tok("istr", (raw, verbatim), i, k + 1))
            else:
                toks.append(Tok("str", raw if verbatim else _unescape(raw), i, k + 1))
            i = k + 1
            continue
        if c == "'":
            k = i + 1
            while k < n and src[k] != "'":
                k += 2 if src[k] == "\\" else 1
            toks.append(Tok("char", _unescape(src[i + 1:k]), i, k + 1))
            i = k + 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            m = _NUM.match(src, i)
            toks.append(Tok("num", m.group(0), i, m.end()))
            i = m.end()
            continue
        if c.isalpha() or c == "_" or (c == "@" and i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "_")):
            m = re.compile(r"@?[A-Za-z_\u00c0-\uffff][\w\u00c0-\uffff]*").match(src, i)
            toks.append(Tok("id", m.group(0).lstrip("@"), i, m.end()))
            i = m.end()
            continue
        for op in _OPS:
            if src.startswith(op, i):
                toks.append(Tok("op", op, i, i + len(op)))
                i += len(op)
                break
        else:
            toks.append(Tok("op", c, i, i + 1))
            i += 1
    toks.append(Tok("eof", "", n, n))
    return toks


# ============================================================================ parser
TYPE_KEYWORDS = {"int", "string", "bool", "double", "float", "decimal", "long", "short", "byte", "char", "object",
                 "var", "uint", "ulong", "ushort", "sbyte", "dynamic", "void", "boolean", "String", "Integer",
                 "Double", "Boolean", "Object", "final", "Long", "Float", "Character"}
MODIFIERS = {"const", "final", "static", "readonly", "volatile", "ref", "out", "in", "params", "this", "scoped"}
STMT_KEYWORDS = {"if", "for", "foreach", "while", "do", "switch", "try", "return", "break", "continue", "throw",
                 "using", "lock", "goto", "checked", "unchecked", "fixed", "unsafe", "yield", "else", "case",
                 "default", "catch", "finally", "synchronized"}
BINARY_PREC = [("??",), ("||",), ("&&",), ("|",), ("^",), ("&",), ("==", "!="), ("<", ">", "<=", ">=", "is", "as",
               "instanceof"), ("<<", ">>", ">>>"), ("+", "-"), ("*", "/", "%")]
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", "??="}


class Parser:
    def __init__(self, src: str, java: bool = False):
        self.src = src
        self.t = tokenize(src)
        self.i = 0
        self.java = java

    # ---- token helpers
    @property
    def cur(self) -> Tok:
        return self.t[self.i]

    def peek(self, k=1) -> Tok:
        return self.t[min(self.i + k, len(self.t) - 1)]

    def at(self, val, k=0) -> bool:
        tk = self.peek(k) if k else self.cur
        return tk.val == val and tk.kind in ("op", "id")

    def take(self, val=None) -> Tok:
        tk = self.cur
        if val is not None and not (tk.val == val and tk.kind in ("op", "id")):
            raise ParseError(f"expected {val!r}, found {tk.val!r}")
        self.i += 1
        return tk

    def accept(self, val) -> bool:
        if self.at(val):
            self.i += 1
            return True
        return False

    def text(self, a: int, b: int) -> str:
        return " ".join(self.src[self.t[a].pos:self.t[max(a, b - 1)].end].split())

    # ---- types
    def try_type(self) -> str | None:
        """Parse a type at the cursor; restore and return None when there is none."""
        start = self.i
        try:
            name = self._type()
            return name
        except ParseError:
            self.i = start
            return None

    def _type(self) -> str:
        if self.cur.kind != "id" or self.cur.val in STMT_KEYWORDS or self.cur.val in ("new", "true", "false",
                                                                                       "null", "return"):
            raise ParseError("type")
        if self.cur.val == "(":
            raise ParseError("type")
        parts = [self.take().val]
        while self.at(".") and self.peek().kind == "id":
            self.take(".")
            parts.append(self.take().val)
        name = ".".join(parts)
        if self.at("<"):
            depth, j = 0, self.i
            while True:
                tk = self.t[j]
                if tk.val == "<":
                    depth += 1
                elif tk.val == ">":
                    depth -= 1
                elif tk.val == ">>":
                    depth -= 2
                elif not (tk.kind == "id" or tk.val in (",", ".", "?", "[", "]")):
                    raise ParseError("generic")
                j += 1
                if depth <= 0:
                    break
            name += self.src[self.cur.pos:self.t[j - 1].end].replace(" ", "")
            self.i = j
        while True:
            if self.at("?") and not self.java and self.peek().kind == "id":
                self.take("?")
                continue
            if self.at("[") and self.at("]", 1):
                self.take("[")
                self.take("]")
                name += "[]"
                continue
            if self.at("[") and self.at(",", 1):
                while not self.at("]"):
                    self.take()
                self.take("]")
                name += "[,]"
                continue
            break
        return name

    # ---- statements
    def block_or_statement(self):
        if self.at("{"):
            return self.block()
        return ("block", [self.statement()])

    def block(self):
        self.take("{")
        out = []
        while not self.at("}") and self.cur.kind != "eof":
            out.append(self.statement())
        self.take("}")
        return ("block", out)

    def statements(self) -> list:
        out = []
        while self.cur.kind != "eof":
            out.append(self.statement())
        return out

    def statement(self):
        start = self.i
        try:
            return self._statement()
        except ParseError:
            self.i = start
            return self._skip_raw()

    def _skip_raw(self):
        start, depth = self.i, 0
        while self.cur.kind != "eof":
            v = self.cur.val if self.cur.kind == "op" else None
            if v in ("(", "[", "{"):
                depth += 1
            elif v in (")", "]", "}"):
                if depth == 0:
                    break
                depth -= 1
                if depth == 0 and v == "}" and not self.at(";", 1) and not self.at(")", 1) \
                        and not self.at(",", 1) and not self.at(".", 1):
                    self.take()
                    break
            elif v == ";" and depth == 0:
                self.take()
                break
            self.take()
        if self.i == start:
            self.take()
        return ("raw", self.text(start, self.i))

    def _statement(self):
        tk = self.cur
        start = self.i
        if tk.kind == "op":
            if tk.val == "{":
                return self.block()
            if tk.val == ";":
                self.take()
                return ("empty",)
            if tk.val == "[":            # attribute
                return self._skip_raw()
        if tk.kind == "id":
            v = tk.val
            if v == "if":
                self.take()
                self.take("(")
                cond = self.expr()
                self.take(")")
                then = self.block_or_statement()
                other = None
                if self.accept("else"):
                    other = self.block_or_statement()
                return ("if", cond, then, other, self.text(start, start + 1))
            if v == "while":
                self.take()
                self.take("(")
                cond = self.expr()
                self.take(")")
                return ("while", cond, self.block_or_statement(), "")
            if v == "do":
                self.take()
                body = self.block_or_statement()
                self.take("while")
                self.take("(")
                cond = self.expr()
                self.take(")")
                self.accept(";")
                return ("do", body, cond, "")
            if v == "for":
                return self._for()
            if v == "foreach" or (v == "for" and self.java):
                return self._foreach()
            if v == "switch":
                return self._switch()
            if v == "try":
                return self._try()
            if v == "return":
                self.take()
                e = None if self.at(";") else self.expr()
                self.take(";")
                return ("return", e, self.text(start, self.i))
            if v in ("break", "continue"):
                self.take()
                self.accept(";")
                return (v,)
            if v == "throw":
                self.take()
                e = None if self.at(";") else self.expr()
                self.take(";")
                return ("throw", e, self.text(start, self.i))
            if v in ("using", "lock", "synchronized", "checked", "unchecked", "fixed", "unsafe") and \
                    (self.at("(", 1) or self.at("{", 1)):
                self.take()
                head = None
                if self.accept("("):
                    hs = self.i
                    depth = 0
                    while not (self.at(")") and depth == 0):
                        if self.at("("):
                            depth += 1
                        if self.at(")"):
                            depth -= 1
                        self.take()
                    head = self.text(hs, self.i)
                    self.take(")")
                body = self.block_or_statement()
                return ("using", v, head, body)
            if v in ("goto", "yield"):
                return self._skip_raw()
            if v in ("const", "final", "static", "readonly"):
                self.take()
                return self._statement()
            # local function / declaration / expression
            decl = self._try_decl()
            if decl is not None:
                return decl
        e = self.expr()
        self.take(";")
        return ("expr", e, self.text(start, self.i))

    def _try_decl(self):
        start = self.i
        typ = self.try_type()
        if typ is None:
            return None
        if self.cur.kind == "id" and self.cur.val not in ("is", "as", "in", "instanceof") and \
                (self.at("=", 1) or self.at(";", 1) or self.at(",", 1) or self.at(":", 1) and self.java):
            names = []
            while True:
                name = self.take().val
                init = None
                if self.accept("="):
                    if self.at("{"):           # array initializer  int[] a = {1, 2}
                        init = ("newarr", typ.rstrip("[]"), None, self._init_list())
                    else:
                        init = self.expr()
                names.append((name, init))
                if not self.accept(","):
                    break
            self.take(";")
            return ("decl", typ, names, self.text(start, self.i))
        if self.cur.kind == "id" and self.at("(", 1) and typ not in ("var",):
            # local function: skip it as raw text
            self.i = start
            return None
        self.i = start
        return None

    def _for(self):
        start = self.i
        self.take("for")
        self.take("(")
        # Java enhanced for: for (Type x : coll)
        save = self.i
        typ = self.try_type()
        if typ and self.cur.kind == "id" and self.at(":", 1):
            name = self.take().val
            self.take(":")
            coll = self.expr()
            self.take(")")
            return ("foreach", typ, name, coll, self.block_or_statement(), self.text(start, start + 1))
        self.i = save
        init = []
        if not self.at(";"):
            d = self._try_decl()
            if d is not None:
                init.append(d)
                self.i -= 0
            else:
                while True:
                    init.append(("expr", self.expr(), ""))
                    if not self.accept(","):
                        break
                self.take(";")
        else:
            self.take(";")
        cond = None if self.at(";") else self.expr()
        self.take(";")
        iters = []
        while not self.at(")"):
            iters.append(self.expr())
            if not self.accept(","):
                break
        self.take(")")
        body = self.block_or_statement()
        return ("for", init, cond, iters, body, self.text(start, start + 1))

    def _foreach(self):
        start = self.i
        self.take()
        self.take("(")
        typ = self.try_type() or "var"
        if self.at("("):                      # deconstruction foreach (var (a, b) in x)
            raise ParseError("deconstruction")
        name = self.take().val
        if not (self.accept("in") or self.accept(":")):
            raise ParseError("foreach in")
        coll = self.expr()
        self.take(")")
        return ("foreach", typ, name, coll, self.block_or_statement(), self.text(start, start + 1))

    def _switch(self):
        start = self.i
        self.take("switch")
        self.take("(")
        e = self.expr()
        self.take(")")
        self.take("{")
        cases = []
        while not self.at("}"):
            labels = []
            while self.at("case") or self.at("default"):
                if self.accept("default"):
                    labels.append(None)
                else:
                    self.take("case")
                    labels.append(self.expr())
                    while self.accept(","):          # Java 14 case a, b ->
                        labels.append(self.expr())
                if not (self.accept(":") or self.accept("->")):
                    raise ParseError("case :")
            if not labels:
                raise ParseError("case")
            body = []
            while not (self.at("case") or self.at("default") or self.at("}")):
                body.append(self.statement())
            cases.append((labels, body))
        self.take("}")
        return ("switch", e, cases, self.text(start, start + 1))

    def _try(self):
        self.take("try")
        if self.at("("):                           # Java try-with-resources
            raise ParseError("try-with-resources")
        body = self.block()
        catches, fin = [], None
        while self.accept("catch"):
            typ, name = None, None
            if self.accept("("):
                typ = self._type()
                while self.accept("|"):
                    typ += "|" + self._type()
                if self.cur.kind == "id":
                    name = self.take().val
                self.take(")")
            if self.accept("when"):
                self.take("(")
                self.expr()
                self.take(")")
            catches.append((typ, name, self.block()))
        if self.accept("finally"):
            fin = self.block()
        return ("try", body, catches, fin, "")

    # ---- expressions
    def expr(self):
        return self.assignment()

    def assignment(self):
        # lambda: x => ..., (a, b) => ...
        if self.cur.kind == "id" and (self.at("=>", 1) or self.at("->", 1)):
            params = [self.take().val]
            self.take()
            return ("lambda", params, self._lambda_body())
        if self.at("("):
            j, depth = self.i, 0
            while True:
                tk = self.t[j]
                if tk.val == "(":
                    depth += 1
                elif tk.val == ")":
                    depth -= 1
                    if depth == 0:
                        break
                elif tk.kind == "eof":
                    break
                j += 1
            if self.t[j + 1].val in ("=>", "->") if j + 1 < len(self.t) else False:
                names = [tk.val for tk in self.t[self.i + 1:j] if tk.kind == "id"]
                self.i = j + 2
                # drop types: (object s, EventArgs e) -> ['s', 'e']
                params = names[1::2] if len(names) % 2 == 0 and len(names) > 1 and \
                    any(n[0].isupper() for n in names[0::2]) else names
                return ("lambda", params, self._lambda_body())
        left = self.conditional()
        if self.cur.kind == "op" and self.cur.val in ASSIGN_OPS:
            op = self.take().val
            right = self.assignment()
            return ("assign", op, left, right)
        return left

    def _lambda_body(self):
        if self.at("{"):
            return self.block()
        return self.expr()

    def conditional(self):
        c = self.binary(0)
        if self.at("?"):
            self.take("?")
            a = self.assignment()
            self.take(":")
            b = self.assignment()
            return ("cond", c, a, b)
        return c

    def binary(self, level):
        if level >= len(BINARY_PREC):
            return self.unary()
        left = self.binary(level + 1)
        while True:
            tk = self.cur
            ops = BINARY_PREC[level]
            if tk.kind in ("op", "id") and tk.val in ops:
                op = self.take().val
                if op in ("is", "as", "instanceof"):
                    typ = self._type()
                    name = None
                    if self.cur.kind == "id" and self.cur.val not in ("and", "or"):
                        name = self.take().val
                    left = ("is", op, left, typ, name)
                    continue
                right = self.binary(level + 1) if op != "??" else self.binary(level)
                left = ("bin", op, left, right)
            else:
                return left

    def unary(self):
        tk = self.cur
        if tk.kind == "op" and tk.val in ("!", "-", "+", "~"):
            self.take()
            return ("unary", tk.val, self.unary())
        if tk.kind == "op" and tk.val in ("++", "--"):
            self.take()
            return ("preinc", tk.val, self.unary())
        if tk.kind == "op" and tk.val == "(":
            # cast?  (Type)x
            save = self.i
            self.take("(")
            typ = self.try_type()
            if typ and self.at(")"):
                nxt = self.peek()
                is_cast = (typ.split(".")[-1] in TYPE_KEYWORDS or typ[0].isupper()) and (
                    nxt.kind in ("id", "num", "str", "char", "istr") or nxt.val in ("(", "!", "~")) and \
                    nxt.val not in ("is", "as", "and", "or", "instanceof")
                if is_cast and typ in TYPE_KEYWORDS | {"String"} or is_cast and nxt.val in ("(",) or \
                        is_cast and nxt.kind != "op":
                    self.take(")")
                    return ("cast", typ, self.unary())
            self.i = save
        if tk.kind == "id" and tk.val == "await":
            self.take()
            return self.unary()
        return self.postfix(self.primary())

    def primary(self):
        tk = self.cur
        if tk.kind == "str":
            self.take()
            return ("str", tk.val)
        if tk.kind == "char":
            self.take()
            return ("str", tk.val)
        if tk.kind == "istr":
            self.take()
            return ("istr", self._interp(*tk.val))
        if tk.kind == "num":
            self.take()
            return ("num", tk.val)
        if tk.kind == "op" and tk.val == "(":
            self.take()
            first = self.expr()
            if self.at(","):                         # tuple
                items = [first]
                while self.accept(","):
                    items.append(self.expr())
                self.take(")")
                return ("tuple", items)
            self.take(")")
            return ("paren", first)
        if tk.kind == "id":
            v = tk.val
            if v in ("true", "false", "null"):
                self.take()
                return ("const", v)
            if v == "new":
                return self._new()
            if v in ("typeof", "sizeof", "nameof", "default") and self.at("(", 1):
                self.take()
                self.take("(")
                depth, s = 0, self.i
                while not (self.at(")") and depth == 0):
                    if self.at("("):
                        depth += 1
                    if self.at(")"):
                        depth -= 1
                    self.take()
                inner = self.text(s, self.i)
                self.take(")")
                return ("special", v, inner)
            if v == "default":
                self.take()
                return ("const", "null")
            if v in ("int", "string", "double", "float", "decimal", "long", "bool", "char", "object", "byte",
                     "short", "String", "Integer", "Double", "Boolean"):
                self.take()
                return ("name", v)
            self.take()
            # generic method call  Foo<int>(...)
            if self.at("<"):
                save = self.i
                try:
                    self.i -= 1
                    self._type()
                    if self.at("("):
                        return ("name", v)
                except ParseError:
                    pass
                self.i = save
            return ("name", v)
        if tk.kind == "op" and tk.val == "[":       # collection expression [1, 2]
            self.take()
            items = []
            while not self.at("]"):
                items.append(self.expr())
                if not self.accept(","):
                    break
            self.take("]")
            return ("newarr", "var", None, items)
        raise ParseError(f"unexpected {tk.val!r}")

    def _interp(self, raw: str, verbatim: bool):
        parts, i, buf = [], 0, []
        while i < len(raw):
            c = raw[i]
            if raw.startswith("{{", i):
                buf.append("{")
                i += 2
                continue
            if raw.startswith("}}", i):
                buf.append("}")
                i += 2
                continue
            if c == "{":
                depth, j = 1, i + 1
                while j < len(raw) and depth:
                    if raw[j] == "{":
                        depth += 1
                    elif raw[j] == "}":
                        depth -= 1
                    elif raw[j] == '"':
                        j = raw.find('"', j + 1)
                        if j < 0:
                            j = len(raw)
                    j += 1
                hole = raw[i + 1:j - 1]
                fmt = ""
                m = re.match(r"^(.*?)(?::([^:\"']*))?$", hole, re.S)
                if m and m.group(2) is not None and "?" not in m.group(1):
                    hole, fmt = m.group(1), m.group(2)
                if buf:
                    parts.append(("".join(buf) if verbatim else _unescape("".join(buf))))
                    buf = []
                try:
                    sub = Parser(hole, self.java)
                    parts.append((sub.expr(), fmt, hole))
                except ParseError:
                    parts.append((("rawexpr", hole), fmt, hole))
                i = j
                continue
            buf.append(c)
            i += 1
        if buf:
            parts.append("".join(buf) if verbatim else _unescape("".join(buf)))
        return parts

    def _init_list(self):
        self.take("{")
        items = []
        while not self.at("}"):
            if self.at("{"):
                items.append(("tuple", self._init_list()))
            else:
                items.append(self.expr())
            if not self.accept(","):
                break
        self.take("}")
        return items

    def _new(self):
        self.take("new")
        if self.at("[") and self.at("]", 1):          # new[] { ... }
            self.take("[")
            self.take("]")
            return ("newarr", "var", None, self._init_list())
        if self.at("("):                             # target-typed new()
            typ = ""
        else:
            typ = self._type_no_array()
        if self.at("["):                             # new int[5] / new int[] {...}
            self.take("[")
            size = None if self.at("]") else self.expr()
            while not self.at("]"):
                self.take()
            self.take("]")
            while self.at("[") and self.at("]", 1):
                self.take("[")
                self.take("]")
            items = self._init_list() if self.at("{") else None
            return ("newarr", typ, size, items)
        if typ.endswith("[]"):
            return ("newarr", typ[:-2], None, self._init_list() if self.at("{") else [])
        args = []
        if self.accept("("):
            args = self._args(")")
        init = None
        if self.at("{"):
            if self.java:                            # anonymous class body
                body_start = self.i
                depth = 0
                while True:
                    if self.at("{"):
                        depth += 1
                    elif self.at("}"):
                        depth -= 1
                        if depth == 0:
                            self.take()
                            break
                    self.take()
                return ("anon", typ, args, self.text(body_start, self.i), body_start)
            init = self._object_init()
        return ("new", typ, args, init)

    def _type_no_array(self):
        parts = [self.take().val]
        while self.at(".") and self.peek().kind == "id":
            self.take(".")
            parts.append(self.take().val)
        name = ".".join(parts)
        if self.at("<"):
            depth, s = 0, self.i
            while True:
                if self.at("<"):
                    depth += 1
                elif self.at(">"):
                    depth -= 1
                elif self.at(">>"):
                    depth -= 2
                self.take()
                if depth <= 0:
                    break
            name += self.src[self.t[s].pos:self.t[self.i - 1].end].replace(" ", "")
        if self.at("[") and self.at("]", 1) and self.at("{", 2):
            self.take("[")
            self.take("]")
            name += "[]"
        return name

    def _object_init(self):
        self.take("{")
        items = []
        while not self.at("}"):
            if self.cur.kind == "id" and self.at("=", 1):
                name = self.take().val
                self.take("=")
                items.append(("prop", name, self._init_list() if self.at("{") else self.expr()))
            elif self.at("{"):
                items.append(("tuple", self._init_list()))
            elif self.at("["):
                self.take("[")
                key = self.expr()
                self.take("]")
                self.take("=")
                items.append(("kv", key, self.expr()))
            else:
                items.append(self.expr())
            if not self.accept(","):
                break
        self.take("}")
        return items

    def _args(self, close):
        args = []
        while not self.at(close):
            if self.cur.kind == "id" and self.cur.val in ("out", "ref", "in") and self.peek().kind == "id":
                self.take()
                if self.peek().kind == "id" and self.cur.val in TYPE_KEYWORDS | {"var"} or \
                        self.peek().kind == "id" and not self.at(".", 1) and not self.at(",", 1) and \
                        not self.at(close, 1):
                    self.take()                       # out int x
                args.append(("out", self.take().val))
            elif self.cur.kind == "id" and self.at(":", 1) and not self.java:   # named argument
                self.take()
                self.take(":")
                args.append(self.expr())
            else:
                args.append(self.expr())
            if not self.accept(","):
                break
        self.take(close)
        return args

    def postfix(self, node):
        while True:
            tk = self.cur
            if tk.kind != "op":
                return node
            if tk.val in (".", "?.") and self.peek().kind == "id":
                self.take()
                name = self.take().val
                if self.at("<") and node[0] in ("name", "member"):
                    save = self.i
                    try:
                        self.i -= 1
                        self._type()
                        if not self.at("("):
                            self.i = save
                    except ParseError:
                        self.i = save
                node = ("member", node, name, tk.val == "?.")
            elif tk.val == "::":
                self.take()
                node = ("member", node, self.take().val, False)
            elif tk.val == "(":
                self.take()
                node = ("call", node, self._args(")"))
            elif tk.val == "[" or tk.val == "?" and self.at("[", 1):
                if tk.val == "?":
                    self.take()
                self.take("[")
                node = ("index", node, self._args("]"))
            elif tk.val in ("++", "--"):
                self.take()
                node = ("postinc", tk.val, node)
            elif tk.val == "!" and not self.java and (self.peek().kind == "op" and self.peek().val in
                                                       (".", ")", ";", ",", "]")):
                self.take()                           # null-forgiving x!
            else:
                return node


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


# ============================================================================ WinForms -> .form
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

WINFORMS_TYPES = {
    "Button": "Button", "Label": "Label", "TextBox": "TextBox", "RichTextBox": "TextBox",
    "MaskedTextBox": "TextBox", "CheckBox": "CheckBox", "RadioButton": "RadioButton", "ListBox": "ListBox",
    "CheckedListBox": "ListBox", "ComboBox": "ComboBox", "PictureBox": "PictureBox",
    "ProgressBar": "ProgressBar", "NumericUpDown": "NumericUpDown", "TrackBar": "TrackBar",
    "HScrollBar": "TrackBar", "VScrollBar": "TrackBar", "Panel": "Panel", "FlowLayoutPanel": "Panel",
    "TableLayoutPanel": "Panel", "SplitContainer": "Panel", "GroupBox": "GroupBox", "Timer": "Timer",
    "MenuStrip": "MenuStrip", "MainMenu": "MenuStrip", "ToolStrip": "ToolStrip", "StatusStrip": "StatusBar",
    "StatusBar": "StatusBar", "TabControl": "TabControl", "TreeView": "TreeView", "ListView": "ListView",
    "DataGridView": "DataGridView", "DataGrid": "DataGridView", "DateTimePicker": "DateTimePicker",
    "MonthCalendar": "DateTimePicker", "LinkLabel": "LinkLabel", "OpenFileDialog": "OpenFileDialog",
    "SaveFileDialog": "SaveFileDialog", "ColorDialog": "ColorDialog", "FontDialog": "FontDialog",
    "FolderBrowserDialog": "FolderBrowserDialog", "WebBrowser": "Panel", "DomainUpDown": "ComboBox",
}
APPROX_TYPES = {"FlowLayoutPanel", "TableLayoutPanel", "SplitContainer", "WebBrowser", "MonthCalendar",
                "DomainUpDown", "HScrollBar", "VScrollBar", "CheckedListBox", "RichTextBox", "MaskedTextBox",
                "DataGrid", "MainMenu"}
MENU_ITEM_TYPES = {"ToolStripMenuItem", "ToolStripButton", "ToolStripSeparator", "ToolStripLabel",
                   "ToolStripDropDownButton", "ToolStripSplitButton", "ToolStripStatusLabel", "ToolStripComboBox",
                   "ToolStripTextBox", "MenuItem", "ToolStripProgressBar"}
IGNORED_TYPES = {"ToolTip", "ImageList", "ErrorProvider", "ContextMenuStrip", "BindingSource", "NotifyIcon",
                 "HelpProvider", "BackgroundWorker", "IContainer", "Container", "ComponentResourceManager",
                 "TabPage", "SplitterPanel", "DataGridViewTextBoxColumn", "DataGridViewCheckBoxColumn",
                 "DataGridViewComboBoxColumn", "DataGridViewButtonColumn", "ColumnHeader", "PrintDocument",
                 "PageSetupDialog", "PrintDialog", "PrintPreviewDialog", "FileSystemWatcher", "SerialPort",
                 "EventLog", "Process", "DataSet", "PerformanceCounter", "ServiceController", "ListViewItem",
                 "TreeNode"}
ALIGN_MAP = {"Left": "Left", "Center": "Center", "Right": "Right"}


def _strip_this(node):
    """('member', ('name','this'), 'x') -> 'x'; ('name', 'x') -> 'x'."""
    if node[0] == "member" and node[1][0] == "name" and node[1][1] in ("this", "base", "Me", "MyBase"):
        return node[2]
    if node[0] == "name":
        return node[1]
    return None


def _lit(node):
    """Python value of a literal-ish node (str/num/bool/enum/color/point/size/font) or None."""
    t = node[0]
    if t == "str":
        return node[1]
    if t == "num":
        s = re.sub(r"[fFdDmMlLuU]+$", "", node[1].replace("_", ""))
        try:
            return int(s, 0) if not re.search(r"[.eE]", s) or s.lower().startswith("0x") else float(s)
        except ValueError:
            return None
    if t == "unary" and node[1] == "-":
        v = _lit(node[2])
        return -v if isinstance(v, (int, float)) else None
    if t == "const":
        return {"true": True, "false": False, "null": None}[node[1]]
    if t == "cast" or t == "paren":
        return _lit(node[-1])
    if t == "member":
        return ("enum", _qual(node))
    if t == "bin" and node[1] == "|":
        a, b = _lit(node[2]), _lit(node[3])
        if isinstance(a, tuple) and isinstance(b, tuple):
            return ("enum", a[1] + "|" + b[1])
    if t == "new":
        base = node[1].split(".")[-1]
        args = [_lit(a) for a in node[2]]
        if base in ("Point", "Size", "SizeF", "PointF", "Padding"):
            return (base, *args)
        if base == "Font":
            return ("Font", *args)
        if base in ("decimal", "Decimal"):
            if node[2] and node[2][0][0] == "newarr" and node[2][0][3]:
                return _lit(node[2][0][3][0])
            return args[0] if args else None
    if t == "call" and node[1][0] == "member":
        q = _qual(node[1])
        args = [_lit(a) for a in node[2]]
        if q.endswith("Color.FromArgb"):
            nums = [x for x in args if isinstance(x, int)]
            if len(nums) >= 3:
                r, g, b = nums[-3:]
                return ("color", f"#{r & 255:02X}{g & 255:02X}{b & 255:02X}")
            if len(nums) == 1:
                v = nums[0]
                return ("color", f"#{(v >> 16) & 255:02X}{(v >> 8) & 255:02X}{v & 255:02X}")
        if q.endswith("Color.FromName") and args and isinstance(args[0], str):
            return ("color", COLOR_NAMES.get(args[0].lower(), ""))
    return None


def _mnemonic(text: str) -> str:
    """'&File' -> 'File', 'Save && Exit' -> 'Save & Exit' (Windows access keys)."""
    return re.sub(r"&(.)", lambda m: m.group(1), text) if "&" in text else text


def _qual(node) -> str:
    if node[0] == "name":
        return node[1]
    if node[0] == "member":
        return _qual(node[1]) + "." + node[2]
    return "?"


def _color(v) -> str:
    if isinstance(v, tuple) and v[0] == "color":
        return v[1]
    if isinstance(v, tuple) and v[0] == "enum":
        last = v[1].split(".")[-1]
        if ".SystemColors." in "." + v[1] or v[1].startswith("SystemColors"):
            return ""
        return COLOR_NAMES.get(last.lower(), "")
    return ""


def _enum_last(v) -> str:
    if isinstance(v, tuple) and v[0] == "enum":
        return v[1].split("|")[-1].split(".")[-1]
    return str(v) if v is not None else ""


class WinFormsClass:
    """One decompiled C# class (a Form or UserControl)."""

    def __init__(self, name: str, base: str, body: str, file: Path | None):
        self.name, self.base, self.body, self.file = name, base, body, file


def find_classes(src: str, file: Path | None = None) -> list[WinFormsClass]:
    out = []
    for m in re.finditer(r"\b(?:public\s+|internal\s+|private\s+|sealed\s+|partial\s+|abstract\s+)*class\s+"
                         r"(\w+)\s*(?::\s*([\w.<>, ]+))?\s*\{", src):
        start = m.end() - 1
        end = _match_brace(src, start)
        if end < 0:
            continue
        out.append(WinFormsClass(m.group(1), (m.group(2) or "").split(",")[0].strip(), src[start + 1:end], file))
    return out


def _match_brace(src: str, start: int) -> int:
    """Index of the } that closes the { at *start* (strings and comments skipped)."""
    depth, i, n = 0, start, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            verbatim = i > 0 and src[i - 1] == "@" or i > 1 and src[i - 2:i] in ("$@", "@$")
            j = i + 1
            while j < n:
                if src[j] == "\\" and not verbatim:
                    j += 2
                    continue
                if src[j] == '"':
                    if verbatim and src.startswith('""', j):
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


METHOD_RE = re.compile(
    r"(?m)^[ \t]*((?:(?:public|private|protected|internal|static|virtual|override|async|new|sealed|extern|"
    r"unsafe|partial|final|synchronized|abstract|native|default)\s+)*)(?:<[^>]*>\s*)?([\w.<>\[\],? ]+?)\s+(\w+)\s*"
    r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*(?:where[^{]*|throws[^{]*)?\{")
FIELD_RE = re.compile(r"(?m)^[ \t]*(?:(?:public|private|protected|internal|static|readonly|const|volatile|new|final|"
                      r"transient)\s+)+"
                      r"([\w.<>\[\],? ]+?)\s+(\w+)\s*(?:=\s*([^;]+))?;")


def class_methods(body: str) -> list[dict]:
    """Methods of a class body: [{name, ret, params, body, header}] (nested classes skipped)."""
    out = []
    for m in METHOD_RE.finditer(body):
        ret = m.group(2).strip()
        if ret in ("return", "new", "else", "if", "while", "for", "foreach", "switch", "using", "catch", "lock") or \
                m.group(3) in ("if", "while", "for", "foreach", "switch", "catch", "using", "lock"):
            continue
        # skip methods inside nested types: depth of the match must be 0
        prefix = body[:m.start()]
        if _depth(prefix) != 0:
            continue
        start = m.end() - 1
        end = _match_brace(body, start)
        if end < 0:
            continue
        out.append({"name": m.group(3), "ret": ret, "params": m.group(4).strip(), "body": body[start + 1:end],
                    "header": " ".join(body[m.start():start].split())})
    # constructors
    return out


def _depth(text: str) -> int:
    clean = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', "", text, flags=re.S)
    return clean.count("{") - clean.count("}")


def class_fields(body: str) -> dict[str, tuple[str, str | None]]:
    out = {}
    for m in FIELD_RE.finditer(body):
        if _depth(body[:m.start()]) != 0:
            continue
        typ, name, init = m.group(1).strip(), m.group(2), m.group(3)
        if typ in ("return", "using", "event", "delegate") or "(" in typ:
            continue
        out[name] = (typ, init.strip() if init else None)
    return out


def parse_params(params: str) -> list[tuple[str, str]]:
    out = []
    depth, cur = 0, ""
    for ch in params:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    res = []
    for p in out:
        p = re.sub(r"^\s*(this|ref|out|in|params|final)\s+", "", p.strip())
        p = p.split("=")[0].strip()
        parts = p.rsplit(None, 1)
        if len(parts) == 2:
            res.append((parts[0], parts[1]))
        elif parts:
            res.append(("", parts[0]))
    return res


def parse_winforms(cls: WinFormsClass, all_forms: set[str] | None = None) -> tuple[dict, dict, list] | None:
    """InitializeComponent of *cls* -> (form_dict, wiring {neutral handler: C# method}, notes)."""
    methods = {m["name"]: m for m in class_methods(cls.body)}
    ic = methods.get("InitializeComponent")
    if ic is None:
        return None
    notes: list[str] = []
    p = Parser(ic["body"])
    stmts = p.statements()
    ctrls: dict[str, dict] = {}          # name -> {"wtype", "props", "parent", "order"}
    order: list[str] = []
    menus: dict[str, dict] = {}          # menu item name -> {"Text", "Name", "Items": [names], "type"}
    form = {"Name": cls.name, "Text": cls.name}
    form_extra: dict = {}
    events: list[tuple[str, str, str]] = []     # (owner name or "", event, method)
    tooltips: dict[str, str] = {}
    tabpages: dict[str, dict] = {}       # tab page name -> {"Text", "parent", "index"}
    form_children: list[str] = []
    radio_groups = 0
    del radio_groups

    def target_of(node):
        """Owner of a member chain: ('ctl', name) / ('form', None)."""
        if node[0] == "name" and node[1] in ("this", "base", "Me", "MyBase"):
            return ("form", None)
        n = _strip_this(node)
        if n is not None:
            if n in ctrls or n in menus or n in tabpages:
                return ("ctl", n)
            if node[0] == "name" and n not in ctrls:
                return ("form", None) if n in ("Controls",) else ("ctl", n)
        return (None, None)

    def add_children(parent: str | None, args):
        items = []
        for a in args:
            if a[0] == "newarr":
                items += a[3] or []
            else:
                items.append(a)
        for a in items:
            n = _strip_this(a)
            if n is None:
                continue
            if parent is None:
                form_children.append(n)
                if n in ctrls:
                    ctrls[n]["parent"] = ""
            elif parent in tabpages:
                if n in ctrls:
                    ctrls[n]["parent"] = ("tab", parent)
            elif parent in ctrls:
                if ctrls[parent]["wtype"] == "TabControl" and n in tabpages:
                    tabpages[n]["parent"] = parent
                    tabpages[n]["index"] = sum(1 for t in tabpages.values() if t.get("parent") == parent) - 1
                elif n in ctrls:
                    ctrls[n]["parent"] = parent

    def add_menu_items(owner: str, args):
        items = []
        for a in args:
            if a[0] == "newarr":
                items += a[3] or []
            else:
                items.append(a)
        lst = ctrls[owner]["menu"] if owner in ctrls else menus[owner]["Items"] if owner in menus else None
        if lst is None:
            return
        for a in items:
            n = _strip_this(a)
            if n:
                lst.append(n)

    for st in stmts:
        if st[0] != "expr":
            continue
        e = st[1]
        if e[0] == "assign" and e[1] == "=":
            tgt, val = e[2], e[3]
            # this.x = new T()
            is_field = tgt[0] == "name" or (tgt[0] == "member" and tgt[1] in (("name", "this"), ("name", "Me")))
            if val[0] == "new" and is_field and _strip_this(tgt) is not None and \
                    val[1].split(".")[-1] not in ("Size", "SizeF", "Point", "PointF", "Font", "Padding",
                                                  "Rectangle", "Icon", "Bitmap", "Cursor", "Color"):
                name = _strip_this(tgt)
                wtype = val[1].split(".")[-1].split("<")[0]
                if wtype in MENU_ITEM_TYPES:
                    menus[name] = {"Name": name, "Text": "-" if wtype == "ToolStripSeparator" else name,
                                   "Items": [], "type": wtype}
                elif wtype == "TabPage":
                    tabpages[name] = {"Text": name, "parent": None, "index": 0}
                elif wtype in IGNORED_TYPES:
                    if wtype not in ("IContainer", "Container", "ComponentResourceManager", "TabPage"):
                        notes.append(f"{cls.name}.{name}: {wtype} is not supported - skipped")
                    ctrls.setdefault("__ignored__", {"names": set()})["names"].add(name)
                else:
                    ctrls[name] = {"wtype": wtype, "props": {}, "parent": "", "menu": []}
                    order.append(name)
                continue
            if tgt[0] != "member":
                continue
            owner_node, prop = tgt[1], tgt[2]
            v = _lit(val)
            # nested: this.x.FlatAppearance.BorderSize ... -> ignore deeper chains except Font
            kind, owner = target_of(owner_node)
            if kind == "form":
                form_extra[prop] = v
            elif kind == "ctl":
                if owner in menus:
                    menus[owner][prop] = v
                elif owner in tabpages:
                    tabpages[owner][prop] = v
                elif owner in ctrls:
                    ctrls[owner]["props"][prop] = v
            continue
        if e[0] == "assign" and e[1] == "+=":
            tgt, val = e[2], e[3]
            if tgt[0] == "name":            # "Load += Form1_Load;" - a form event (designer of .NET 6+)
                ev, kind, owner = tgt[1], "form", None
            elif tgt[0] != "member":
                continue
            else:
                ev = tgt[2]
                kind, owner = target_of(tgt[1])
            meth = None
            if val[0] == "new" and val[2]:
                meth = _strip_this(val[2][0]) if val[2][0][0] in ("name", "member") else None
            elif val[0] in ("name", "member"):
                meth = _strip_this(val)
            if meth is None:
                notes.append(f"{cls.name}: event {ev} wired to an inline lambda - left in the C# source")
                continue
            events.append(("" if kind == "form" else owner or "", ev, meth))
            continue
        if e[0] == "call" and e[1][0] == "member":
            func = e[1]
            mname = func[2]
            recv = func[1]
            # x.Controls.Add(y) / base.Controls.Add(y) / Controls.AddRange(...)
            if mname in ("Add", "AddRange") and recv[0] in ("member", "name") and \
                    (recv[0] == "member" and recv[2] in ("Controls", "TabPages") or recv == ("name", "Controls")):
                owner_node = recv[1] if recv[0] == "member" else ("name", "this")
                if recv[0] == "member" and recv[2] in ("Controls",) and owner_node[0] == "member" and \
                        owner_node[2] in ("Panel1", "Panel2"):            # SplitContainer panels
                    owner_node = owner_node[1]
                kind, owner = target_of(owner_node)
                add_children(None if kind == "form" else owner, e[2])
                continue
            if mname in ("Add", "AddRange") and recv[0] == "member" and recv[2] in ("Items", "DropDownItems",
                                                                                    "MenuItems"):
                kind, owner = target_of(recv[1])
                if owner in menus or owner in ctrls and ctrls[owner]["wtype"] in ("MenuStrip", "ToolStrip",
                                                                                  "StatusStrip", "MainMenu",
                                                                                  "ContextMenuStrip"):
                    add_menu_items(owner, e[2])
                    continue
                if owner in ctrls:
                    vals = []
                    for a in e[2]:
                        if a[0] == "newarr":
                            vals += [_lit(x) for x in a[3] or []]
                        else:
                            vals.append(_lit(a))
                    ctrls[owner]["props"].setdefault("__items", []).extend(
                        str(x) for x in vals if isinstance(x, (str, int, float)))
                continue
            if mname == "SetToolTip" and len(e[2]) == 2:
                n = _strip_this(e[2][0])
                v = _lit(e[2][1])
                if n and isinstance(v, str):
                    tooltips[n] = v
                continue
            if mname == "Add" and recv[0] == "member" and recv[2] == "Columns":
                kind, owner = target_of(recv[1])
                if owner in ctrls:
                    v = _lit(e[2][0]) if e[2] else None
                    vals = [_lit(x) for x in e[2]]
                    txt = next((x for x in vals if isinstance(x, str)), None)
                    if txt is None and isinstance(v, str):
                        txt = v
                    ctrls[owner]["props"].setdefault("__columns", []).append(txt or f"Column{len(ctrls[owner]['props'].get('__columns', [])) + 1}")
                continue
            if mname in ("AddRange",) and recv[0] == "member" and recv[2] == "Columns":
                kind, owner = target_of(recv[1])
                if owner in ctrls:
                    ctrls[owner]["props"].setdefault("__colrefs", []).extend(
                        _strip_this(a) for a in (e[2][0][3] if e[2] and e[2][0][0] == "newarr" else e[2]))
                continue
    ctrls.pop("__ignored__", None)

    # ---- build the neutral form
    from ...controls import CONTROL_TYPES, format_anchor
    w, h = 400, 300
    cs = form_extra.get("ClientSize") or form_extra.get("Size")
    if isinstance(cs, tuple) and len(cs) >= 3:
        w, h = int(cs[1] or w), int(cs[2] or h)
        if "ClientSize" not in form_extra:
            w, h = max(100, w - 16), max(80, h - 39)
    form = {"Name": cls.name, "Text": str(form_extra.get("Text") if isinstance(form_extra.get("Text"), str) else
                                           cls.name), "Width": w, "Height": h}
    bc = _color(form_extra.get("BackColor"))
    if bc:
        form["BackColor"] = bc
    sp = _enum_last(form_extra.get("StartPosition"))
    form["StartPosition"] = "CenterScreen" if sp in ("CenterScreen", "CenterParent", "") else "Manual"
    fb = _enum_last(form_extra.get("FormBorderStyle"))
    if fb.startswith("Fixed") or fb == "None":
        form["FormBorderStyle"] = "FixedSingle"
    if form_extra.get("TopMost") is True:
        form["TopMost"] = True
    if _enum_last(form_extra.get("WindowState")) == "Maximized":
        form["WindowState"] = "Maximized"

    controls: list[dict] = []
    menu_height = 0
    used_names: set[str] = set()

    def menu_tree(names: list[str], depth=0) -> list[dict]:
        items = []
        for n in names:
            m = menus.get(n)
            if m is None or depth > 6:
                continue
            text = m.get("Text")
            if not isinstance(text, str):
                text = n
            item = {"Text": "-" if m["type"] == "ToolStripSeparator" else _mnemonic(text), "Name": n}
            if m["Items"]:
                item["Items"] = menu_tree(m["Items"], depth + 1)
            items.append(item)
        return items

    # tab page offsets: children of a TabPage go to the TabControl with props["TabPage"]
    def parent_info(c):
        par = c["parent"]
        if isinstance(par, tuple):
            tp = tabpages.get(par[1], {})
            return tp.get("parent") or "", tp.get("index", 0)
        return par, None

    for n in order:
        c = ctrls[n]
        wt = c["wtype"]
        nt = WINFORMS_TYPES.get(wt)
        if nt is None:
            notes.append(f"{cls.name}.{n}: unknown control type {wt} - became a Panel placeholder")
            nt = "Panel"
        elif wt in APPROX_TYPES:
            notes.append(f"{cls.name}.{n}: {wt} approximated as {nt}")
        ct = CONTROL_TYPES[nt]
        props = ct.default_props(n)
        pr = c["props"]
        loc, size = pr.get("Location"), pr.get("Size")
        if isinstance(loc, tuple) and len(loc) >= 3 and not ct.nonvisual:
            props["Left"], props["Top"] = int(loc[1] or 0), int(loc[2] or 0)
        if isinstance(size, tuple) and len(size) >= 3 and not ct.nonvisual:
            props["Width"], props["Height"] = int(size[1] or 0), int(size[2] or 0)
        if wt in ("MenuStrip", "MainMenu"):
            props["Items"] = menu_tree(c["menu"])
            if isinstance(size, tuple) and _enum_last(pr.get("Dock")) in ("", "Top") and c["parent"] == "":
                menu_height = max(menu_height, int(size[2] or 24))
            elif c["parent"] == "" and wt == "MenuStrip":
                menu_height = max(menu_height, 24)
        elif wt == "ToolStrip":
            props["Items"] = menu_tree(c["menu"])
        elif wt in ("StatusStrip",):
            labels = [menus[x].get("Text") for x in c["menu"] if x in menus]
            props["Text"] = next((t for t in labels if isinstance(t, str)), "Ready")
            props["Dock"] = "Bottom"
        text = pr.get("Text")
        if isinstance(text, str) and "Text" in props:
            props["Text"] = text if nt in ("TextBox", "ComboBox") else _mnemonic(text)
        elif "Text" in props and not isinstance(text, str):
            props["Text"] = "" if nt in ("TextBox", "ComboBox", "StatusBar") else props.get("Text", n)
        font = pr.get("Font")
        if isinstance(font, tuple) and font[0] == "Font" and "FontName" in props:
            if len(font) > 1 and isinstance(font[1], str):
                props["FontName"] = font[1]
            if len(font) > 2 and isinstance(font[2], (int, float)):
                props["FontSize"] = int(round(font[2]))
            style = " ".join(_enum_last(x) if isinstance(x, tuple) else "" for x in font[3:])
            style += " ".join(str(x[1]) for x in font[3:] if isinstance(x, tuple) and x[0] == "enum")
            props["FontBold"] = "Bold" in style
            props["FontItalic"] = "Italic" in style
        for key in ("BackColor", "ForeColor"):
            col = _color(pr.get(key))
            if col and key in props:
                props[key] = col
        if wt == "LinkLabel" and _color(pr.get("LinkColor")):
            props["LinkColor"] = _color(pr.get("LinkColor"))
        anchor = pr.get("Anchor")
        if isinstance(anchor, tuple) and anchor[0] == "enum" and "Anchor" in props:
            edges = {x.split(".")[-1] for x in anchor[1].split("|")}
            props["Anchor"] = format_anchor(edges) if edges - {"None"} else "None"
        dock = _enum_last(pr.get("Dock"))
        if dock in ("Top", "Bottom", "Left", "Right", "Fill") and "Dock" in props and \
                wt not in ("MenuStrip", "ToolStrip", "MainMenu"):
            props["Dock"] = dock
        for key in ("Enabled", "Visible", "Checked", "ReadOnly", "Multiline"):
            if isinstance(pr.get(key), bool) and key in props:
                props[key] = pr[key]
        if pr.get("CheckState") is not None and "Checked" in props:
            props["Checked"] = _enum_last(pr["CheckState"]) == "Checked"
        if isinstance(pr.get("TabIndex"), int) and "TabIndex" in props:
            props["TabIndex"] = pr["TabIndex"]
        if nt == "TextBox":
            if wt == "RichTextBox":
                props["Multiline"] = True
            if isinstance(pr.get("PasswordChar"), str) and pr["PasswordChar"].strip("\0"):
                props["PasswordChar"] = pr["PasswordChar"][:1]
            if pr.get("UseSystemPasswordChar") is True:
                props["PasswordChar"] = "*"
            if isinstance(pr.get("MaxLength"), int) and pr["MaxLength"] < 32767:
                props["MaxLength"] = pr["MaxLength"]
            al = _enum_last(pr.get("TextAlign"))
            if al and "TextAlign" in props:
                props["TextAlign"] = "Center" if al == "Center" else "Right" if al == "Right" else "Left"
        if "TextAlign" in props and nt in ("Label", "Button", "LinkLabel"):
            al = _enum_last(pr.get("TextAlign"))
            if al:
                props["TextAlign"] = "Center" if "Center" in al else "Right" if "Right" in al else "Left"
        for key in ("Minimum", "Maximum", "Value"):
            if isinstance(pr.get(key), (int, float)) and key in props:
                props[key] = int(pr[key])
        if nt == "Timer":
            if isinstance(pr.get("Interval"), int):
                props["Interval"] = pr["Interval"]
            props["Enabled"] = pr.get("Enabled") is True
        if nt in ("ListBox", "ComboBox") and pr.get("__items"):
            props["Items"] = ";".join(x.replace(";", ",") for x in pr["__items"])
        if nt == "ComboBox":
            props["DropDownStyle"] = "DropDownList" if _enum_last(pr.get("DropDownStyle")) == "DropDownList" \
                else "DropDown"
        if nt in ("ListView", "DataGridView"):
            cols = pr.get("__columns") or []
            if not cols and pr.get("__colrefs"):
                cols = [str(r) for r in pr["__colrefs"] if r]
            if cols:
                props["Columns"] = ";".join(str(x) for x in cols)
        if nt == "DateTimePicker":
            fmt = _enum_last(pr.get("Format"))
            if fmt in ("Short", "Long", "Time"):
                props["Format"] = fmt
        if nt == "TabControl":
            pages = sorted((t for t in tabpages.values() if t.get("parent") == n), key=lambda t: t["index"])
            if pages:
                props["TabPages"] = ";".join(str(t.get("Text") if isinstance(t.get("Text"), str) else "Tab")
                                             for t in pages)
        if nt == "OpenFileDialog" or nt == "SaveFileDialog":
            for key in ("Filter", "Title", "FileName", "InitialDirectory"):
                if isinstance(pr.get(key), str):
                    props[key] = pr[key]
        if n in tooltips and "ToolTip" in props:
            props["ToolTip"] = tooltips[n]
        if pr.get("Image") is not None or pr.get("BackgroundImage") is not None:
            notes.append(f"{cls.name}.{n}: image from the program resources not extracted")
        par, page = parent_info(c)
        props["Parent"] = par if par in ctrls else ""
        if page is not None:
            props["TabPage"] = page
        used_names.add(n)
        controls.append({"type": nt, "props": props})

    # menu strip inside the client area in WinForms, outside it (native menu) in RAD IDE
    if menu_height:
        form["Height"] = max(60, form["Height"] - menu_height)
        for c in controls:
            ct = CONTROL_TYPES[c["type"]]
            if not ct.nonvisual and not c["props"].get("Parent") and c["props"].get("Dock", "None") in ("None",):
                c["props"]["Top"] = max(0, int(c["props"]["Top"]) - menu_height)

    # z-order: WinForms Controls.Add order = front first; .form list = back first
    pos = {n: i for i, n in enumerate(form_children)}
    controls.sort(key=lambda c: -pos.get(c["props"]["Name"], -1) if c["props"]["Name"] in pos else 0)
    # containers must come before their children: keep a stable topological order
    names_order = [c["props"]["Name"] for c in controls]
    by_name = {c["props"]["Name"]: c for c in controls}
    ordered, seen = [], set()

    def place(nm, depth=0):
        if nm in seen or depth > 20:
            return
        par = by_name[nm]["props"].get("Parent") or ""
        if par and par in by_name:
            place(par, depth + 1)
        seen.add(nm)
        ordered.append(by_name[nm])
    for nm in names_order:
        place(nm)

    # ---- event wiring: neutral handler name -> C# method
    wiring: dict[str, str] = {}
    menu_names = set(menus)
    for owner, ev, meth in events:
        nev = EVENT_MAP.get(ev)
        if owner == "" or owner == cls.name:
            nev = nev or ev
            handler = f"{cls.name}_{nev}"
        elif owner in menu_names:
            if ev not in ("Click", "ButtonClick"):
                notes.append(f"{cls.name}.{owner}.{ev}: menu event not supported")
                continue
            handler = f"{owner}_Click"
        elif owner in used_names:
            if nev is None:
                notes.append(f"{cls.name}.{owner}.{ev}: event has no RAD IDE equivalent - handler {meth} "
                             "kept as a method")
                continue
            handler = f"{owner}_{nev}"
        else:
            continue
        wiring.setdefault(handler, meth)
    return {"version": 2, "props": form, "controls": ordered}, wiring, notes


# ============================================================================ class -> python-tk user code
def translate_form_class(cls: WinFormsClass, form_dict: dict, wiring: dict, all_forms: set[str],
                         language: str = "python-tk", emitter_cls=None, skip_methods: set | None = None,
                         java: bool = False) -> dict:
    """Build the python-tk user code of one form.

    Returns {"code": str, "handlers": {name: [body lines]}, "methods": [(name, status)],
    "stats": (translated, commented), "csharp": {method: source}, "imports": set}.
    *wiring* maps a neutral handler name to a method name of the class or to ("inline", body source)."""
    from ...languages import get_plugin
    from ...model import Form
    from ...controls import event_args, menu_names as _menu_names
    form = Form.from_dict(form_dict)
    controls = {c.name: c.type for c in form.controls}
    menus = set()
    for c in form.controls:
        if c.type in ("MenuStrip", "ToolStrip"):
            menus |= set(_menu_names(c.props.get("Items", [])))
    multiline = {c.name for c in form.controls if c.type == "TextBox" and c.props.get("Multiline")}
    skip = {"InitializeComponent", "Dispose", "initComponents", "main"} | set(skip_methods or ())
    methods = [m for m in class_methods(cls.body) if m["name"] not in skip]
    ctor = [m for m in methods if m["name"] == cls.name]
    methods = [m for m in methods if m["name"] != cls.name]
    fields_raw = {k: v for k, v in class_fields(cls.body).items() if k not in controls and k != "components"
                  and k not in menus}
    emitter_fields = {}
    emitter_cls = emitter_cls or PyEmitter
    probe = emitter_cls()
    for k, (typ, _init) in fields_raw.items():
        emitter_fields[k] = probe.kind_of_type(typ)
    method_names = {m["name"] for m in methods}
    em = emitter_cls(controls, cls.name, emitter_fields, method_names, multiline, menus, all_forms)

    plugin = get_plugin(language)
    code = plugin.new_code(form, False)
    handlers: dict[str, list[str]] = {}
    status: list[tuple[str, str]] = []
    csharp: dict[str, str] = {}

    def translate(m, params_override=None) -> tuple[list[str], int, int]:
        em.locals = [{}]
        for typ, pname in parse_params(m["params"]):
            em.declare(pname, em.kind_of_type(typ))
        before_t, before_u = em.translated, em.untranslated
        try:
            stmts = Parser(m["body"], java).statements()
            lines = em.body(stmts, 0)
        except Exception as e:  # noqa: BLE001 - keep the C# as comments
            lines = [f"# C#: {ln.strip()}" for ln in m["body"].strip().splitlines() if ln.strip()] + \
                [f"# (could not translate: {e})", "pass"]
            em.untranslated += 1
        return lines, em.translated - before_t, em.untranslated - before_u

    # fields -> class attributes
    field_lines = []
    for k, (typ, init) in fields_raw.items():
        val = DEFAULTS.get(probe.kind_of_type(typ), "None")
        if init:
            try:
                val, _k = em.ex(Parser(init, java).expr())
            except (ParseError, Untranslatable):
                val = f"None  # C#: {init}"
        field_lines.append(f"    {py_ident(k)} = {val}")

    by_name = {m["name"]: m for m in methods}
    handled_methods: dict[str, str] = {}
    handler_blocks: list[tuple[str, list[str], str | None]] = []
    for handler, meth in wiring.items():
        if isinstance(meth, tuple):                     # inline body (lambda / anonymous listener)
            body_src = meth[1]
            only = re.fullmatch(r"\s*(?:(?:\w+\.)?this\.)?(\w+)\s*\(\s*\w*\s*\)\s*;?\s*", body_src)
            if only and only.group(1) in by_name and only.group(1) not in handled_methods:
                meth = only.group(1)                   # e -> btnGreet_Click(): the method IS the handler
            else:
                body, _t, u = translate({"params": "", "body": body_src})
                status.append((handler, "rules" if u == 0 else "partial"))
                csharp[handler] = body_src
                handler_blocks.append((handler, body, None))
                handlers[handler] = body
                continue
        m = by_name.get(meth)
        if m is None:
            continue
        csharp[meth] = m["header"] + " {" + m["body"] + "}"
        if meth in handled_methods:
            body = [f"self.{handled_methods[meth]}()"]
        else:
            body, t, u = translate(m)
            status.append((meth, "rules" if u == 0 else "partial"))
            handled_methods[meth] = handler
        handler_blocks.append((handler, body, meth))
        handlers[handler] = body
    # constructor body (after InitializeComponent) -> Load handler prefix
    if ctor:
        body_text = re.sub(r"\bInitializeComponent\s*\(\s*\)\s*;", "", ctor[0]["body"])
        if body_text.strip():
            lines, t, u = translate({**ctor[0], "body": body_text})
            load = f"{cls.name}_Load"
            prev = handlers.get(load)
            handlers[load] = lines + ([] if prev is None else prev)
            if prev is None:
                handler_blocks.insert(0, (load, lines, None))
            else:
                handler_blocks = [(h, handlers[h] if h == load else b, mm) for h, b, mm in handler_blocks]
            status.append((cls.name + " (constructor)", "rules" if u == 0 else "partial"))
    # other methods -> helper methods
    helper_src = []
    for m in methods:
        if m["name"] in handled_methods and handled_methods[m["name"]] == m["name"]:
            continue
        if m["name"] in handled_methods:
            # handler named differently: keep the original method too (called by the handler)
            pass
        csharp[m["name"]] = m["header"] + " {" + m["body"] + "}"
        params = parse_params(m["params"])
        if m["name"] in handled_methods:
            continue
        lines, t, u = translate(m)
        status.append((m["name"], "rules" if u == 0 else "partial"))
        pnames = [py_ident(p[1]) for p in params]
        is_handler_sig = len(params) == 2 and params[0][0].split(".")[-1] in ("object", "Object") and \
            params[1][0].endswith("EventArgs")
        sig = "self, sender=None, e=None" if is_handler_sig else ", ".join(["self"] + pnames)
        helper_src.append(f"    def {py_ident(m['name']) if m['name'] in PY_RESERVED else m['name']}({sig}):")
        helper_src += ["        " + ln if ln.strip() else "" for ln in lines]
        helper_src.append("")

    # assemble the user code
    for handler, body, _meth in handler_blocks:
        ev = handler.rsplit("_", 1)[-1]
        idx = plugin.find_handler(code, handler)
        if idx >= 0:
            lines = code.splitlines()
            if idx + 1 < len(lines) and lines[idx + 1].strip() == "pass":     # the stub body
                del lines[idx + 1]
            lines[idx + 1:idx + 1] = ["        " + ln if ln.strip() else "" for ln in body]
            code = "\n".join(lines) + "\n"
            continue
        code, line = plugin.add_handler(code, handler, form, event_args(ev))
        lines = code.splitlines()
        if line < len(lines) and lines[line].strip() == "pass":
            lines[line:line + 1] = ["        " + ln if ln.strip() else "" for ln in body]
        else:
            k = plugin.find_handler(code, handler)
            lines[k + 1:k + 2] = ["        " + ln if ln.strip() else "" for ln in body]
        code = "\n".join(lines) + "\n"
    if field_lines:
        code = code.replace('    """Write your event handlers here."""\n',
                            '    """Write your event handlers here."""\n\n    # fields of the original form\n'
                            + "\n".join(field_lines) + "\n", 1)
    if helper_src:
        idx = code.find("\n\nif __name__")
        block = "\n    # ---- methods of the original form ----\n\n" + "\n".join(helper_src).rstrip() + "\n"
        code = code[:idx] + "\n" + block + code[idx:] if idx >= 0 else code + block
    if em.imports:
        imports = sorted(em.imports, key=lambda s: (s.startswith("from"), s))
        first_nl = code.find("\n")
        code = "\n".join(imports) + "\n" + code if first_nl < 0 else \
            code[:first_nl + 1] + "\n".join(imports) + "\n" + code[first_nl + 1:]
    # a Load stub that is still empty is fine; make sure there is no 'pass' after real code
    code = _drop_stray_pass(code)
    return {"code": code, "handlers": handlers, "methods": status, "stats": (em.translated, em.untranslated),
            "csharp": csharp, "imports": set(em.imports)}


def _drop_stray_pass(code: str) -> str:
    lines = code.splitlines()
    out = []
    for i, ln in enumerate(lines):
        if ln.strip() == "pass" and out:
            prev = next((x for x in reversed(out) if x.strip()), "")
            ind = len(ln) - len(ln.lstrip())
            pind = len(prev) - len(prev.lstrip())
            if prev.strip() and not prev.rstrip().endswith(":") and not prev.strip().startswith("#") and \
                    pind == ind:
                continue
        out.append(ln)
    return "\n".join(out) + "\n"


# ============================================================================ result helpers
def set_form_code(res: ImportResult, form: str, code: str, language: str, handlers: dict | None = None) -> None:
    """Record the complete user code of *form* (resources["form_code"], used by the wizard when the project
    language is resources["form_code_language"]) and its handler bodies in the wizard's format
    {"ctrl.Event" / ".Load": [python lines]} (used for the other languages)."""
    res.resources.setdefault("form_code", {})[form] = code
    res.resources["form_code_language"] = language
    if handlers:
        out = {}
        for name, body in handlers.items():
            owner, _, event = name.rpartition("_")
            key = f".{event}" if owner == form else f"{owner}.{event}"
            # the full code is used for *language*; other languages get the rules translation as comments
            out[key] = [("comment", f"({language}) {ln}") for ln in body if ln.strip()] + [("python", "pass")]
        res.handlers[form] = out


def set_startup(res: ImportResult, form: str) -> None:
    res.resources["startup"] = form
    res.resources["startup_form"] = form


# ============================================================================ ilspycmd
def find_ilspycmd() -> str | None:
    return find_tool("ilspycmd")


def install_ilspycmd(progress=None) -> str | None:
    """dotnet tool install --tool-path %LOCALAPPDATA%\\RADIDE\\tools ilspycmd (newest that runs here)."""
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return None
    root = tools_dir()
    root.mkdir(parents=True, exist_ok=True)
    for ver in ILSPY_VERSIONS:
        say(progress, "Installing ilspycmd (ILSpy command line)" + (f" {ver}" if ver else "") + " ...")
        cmd = [dotnet, "tool", "install", "--tool-path", str(root), "ilspycmd"]
        if ver:
            cmd += ["--version", ver]
        rc, out = run_tool(cmd, timeout=600)
        exe = root / ("ilspycmd.exe" if os.name == "nt" else "ilspycmd")
        if exe.exists():
            ok, _o = run_tool([str(exe), "--version"], timeout=120)
            if ok == 0 or "ilspycmd" in _o.lower():
                return str(exe)
            run_tool([dotnet, "tool", "uninstall", "--tool-path", str(root), "ilspycmd"], timeout=300)
    return None


def decompile(assembly: Path, outdir: Path, progress=None) -> tuple[Path | None, str]:
    exe = find_ilspycmd() or install_ilspycmd(progress)
    if not exe:
        return None, ("ilspycmd is not available (needs the .NET SDK: install it from https://dot.net, then "
                      "retry - the importer installs ilspycmd with 'dotnet tool install')")
    outdir.mkdir(parents=True, exist_ok=True)
    say(progress, f"Decompiling {assembly.name} with ILSpy ...")
    rc, out = run_tool([exe, "-p", "-o", str(outdir), str(assembly)], timeout=1800)
    if not any(outdir.rglob("*.cs")):
        rc2, out2 = run_tool([exe, "-o", str(outdir), str(assembly)], timeout=1800)
        out += out2
    if not any(outdir.rglob("*.cs")):
        return None, "ilspycmd produced no C# files:\n" + out[-1500:]
    return outdir, out


def _bundle_extract(path: Path, workdir: Path) -> Path | None:
    """Managed main assembly from a .NET single-file bundle (manifest at the bundle header offset)."""
    import struct
    data = path.read_bytes()
    sig = bytes.fromhex("8b1202b96a612038727b930214d7a03213f5b9e6efae3318ee3b2dce24b36aae")
    i = data.find(sig)
    if i < 8:
        return None
    off = struct.unpack_from("<q", data, i - 8)[0]
    if off <= 0 or off >= len(data):
        return None
    try:
        major, _minor, count = struct.unpack_from("<IIi", data, off)
        p = off + 12

        def read_str(pos):
            n, shift, length = 0, 0, 0
            while True:
                b = data[pos]
                pos += 1
                length |= (b & 0x7F) << shift
                shift += 7
                n += 1
                if not b & 0x80:
                    break
            return data[pos:pos + length].decode("utf-8"), pos + length
        _bid, p = read_str(p)
        if major >= 2:
            p += 8 * 4 + 8      # deps/runtimeconfig offsets+sizes, flags
        out = workdir / "bundle"
        out.mkdir(parents=True, exist_ok=True)
        main = None
        for _ in range(count):
            offset, size = struct.unpack_from("<qq", data, p)
            p += 16
            csize = 0
            if major >= 6:
                csize = struct.unpack_from("<q", data, p)[0]
                p += 8
            ftype = data[p]
            p += 1
            rel, p = read_str(p)
            blob = data[offset:offset + (csize or size)]
            if csize:
                import zlib
                blob = zlib.decompress(blob, -15)
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
            if ftype == 1 and rel.lower() == path.with_suffix(".dll").name.lower():
                main = dest
        return main
    except Exception:  # noqa: BLE001
        return None


# ============================================================================ backend API
def can_handle(info: BinaryInfo) -> bool:
    return getattr(info, "kind", "") == "dotnet"


def run(path, info: BinaryInfo, workdir, progress=None, ai_translate: bool = False) -> ImportResult:
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    d = getattr(info, "details", {}) or {}
    assembly = Path(d["managed_dll"]) if d.get("managed_dll") else path
    if d.get("bundle") and not d.get("managed_dll"):
        say(progress, "Extracting the .NET single-file bundle ...")
        main = _bundle_extract(path, workdir)
        if main is None:
            res.add("error", "Could not read the .NET single-file bundle.")
            return res
        assembly = main
        res.add("info", f"Single-file bundle: main assembly {main.name} extracted.")
    src_dir, log = decompile(assembly, workdir / "csharp", progress)
    if src_dir is None:
        res.add("error", log)
        return res
    res.source_dir = src_dir
    res.add("exact", f"Decompiled {assembly.name} to a C# project with ILSpy ({sum(1 for _ in src_dir.rglob('*.cs'))}"
                     " .cs files) - kept in the project's _original folder.")
    return convert_csharp_tree(src_dir, res, progress, ai_translate)


def convert_csharp_tree(src_dir: Path, res: ImportResult, progress=None, ai_translate: bool = False,
                        language: str = "python-tk") -> ImportResult:
    """Decompiled (or original) C# sources -> forms + Python code in *res*."""
    classes: list[WinFormsClass] = []
    startup = ""
    for f in sorted(src_dir.rglob("*.cs")):
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        m = re.search(r"Application\.Run\s*\(\s*new\s+([\w.]+)\s*\(", text)
        if m:
            startup = m.group(1).split(".")[-1]
        classes += find_classes(text, f)
    # merge partial classes (Form1.cs + Form1.Designer.cs when importing sources)
    merged: dict[str, WinFormsClass] = {}
    for c in classes:
        if c.name in merged:
            merged[c.name].body += "\n" + c.body
            if not merged[c.name].base:
                merged[c.name].base = c.base
        else:
            merged[c.name] = c
    form_classes = [c for c in merged.values() if "InitializeComponent" in c.body and
                    re.search(r"\bvoid\s+InitializeComponent\s*\(", c.body) and
                    (c.base.split(".")[-1] in ("Form", "UserControl") or "Controls.Add" in c.body)]
    all_forms = {c.name for c in form_classes}
    if not form_classes:
        res.add("missing", "No WinForms form found (console, WPF or library assembly) - the C# code is in "
                           "_original; translate it with AI from the editor.")
    if startup and startup in all_forms:
        form_classes.sort(key=lambda c: c.name != startup)
    set_startup(res, startup if startup in all_forms else (form_classes[0].name if form_classes else ""))
    res.resources["form_code_language"] = language
    total_t = total_u = 0
    for cls in form_classes:
        say(progress, f"Reading form {cls.name} ...")
        try:
            parsed = parse_winforms(cls, all_forms)
        except Exception as e:  # noqa: BLE001
            res.add("error", f"{cls.name}: InitializeComponent could not be read ({e})")
            continue
        if parsed is None:
            continue
        form_dict, wiring, notes = parsed
        for n in notes:
            res.add("warn", n)
        res.forms.append((cls.name, form_dict))
        nctl = len(form_dict["controls"])
        res.add("exact", f"Form {cls.name}: {nctl} control(s), title, size, positions, fonts, colours, "
                         f"anchors and {len(wiring)} event handler(s) from InitializeComponent.")
        say(progress, f"Translating the code of {cls.name} to Python ...")
        try:
            tr = translate_form_class(cls, form_dict, wiring, all_forms, language)
        except Exception as e:  # noqa: BLE001
            res.add("error", f"{cls.name}: code translation failed ({e}); the C# stays in _original.")
            continue
        t, u = tr["stats"]
        total_t += t
        total_u += u
        code = tr["code"]
        ai_used = False
        if ai_translate and u:
            partial = [m for m, s in tr["methods"] if s == "partial"]
            ctx = ("Target: a python-tk RAD IDE form class. Controls are self.<Name>; TextBox text is "
                   "self.<Name>_var.get()/set(), Label/Button text self.<Name>.config(text=...), CheckBox "
                   "self.<Name>_var, ListBox is a tk.Listbox. Keep every method name and signature; "
                   "return the WHOLE class file.\nControls: " +
                   ", ".join(f"{c['props']['Name']} ({c['type']})" for c in form_dict["controls"]) +
                   "\nOriginal C# of the methods still marked '# C#:':\n" +
                   "\n\n".join(tr["csharp"].get(m.split(" ")[0], "") for m in partial))
            new, who = ai_rewrite(code, "partly translated Python (C# lines in comments)", ctx, progress)
            if new and "class " + cls.name in new:
                try:
                    compile(new, f"{cls.name}.py", "exec")
                    code = new
                    ai_used = True
                    res.add("ai", f"{cls.name}: {len(partial)} method(s) with untranslated lines rewritten by "
                                  f"AI ({who}).")
                except SyntaxError as e:
                    res.add("warn", f"{cls.name}: the AI answer did not compile ({e}); rules kept.")
            else:
                res.add("warn", f"{cls.name}: AI translation not used - {who}")
        try:
            compile(code, f"{cls.name}.py", "exec")
        except SyntaxError as e:
            res.add("warn", f"{cls.name}.py: generated code has a syntax error at line {e.lineno}: {e.msg}")
        set_form_code(res, cls.name, code, language, tr["handlers"])
        done = [m for m, s in tr["methods"] if s == "rules"]
        part = [m for m, s in tr["methods"] if s == "partial"]
        if done:
            res.add("rules", f"{cls.name}: translated to Python by rules: " + ", ".join(done))
        if part and not ai_used:
            res.add("missing", f"{cls.name}: some lines kept as '# C#:' comments in " + ", ".join(part) +
                               " (enable AI translation or rewrite them).")
    # non-form classes: kept as C# modules for reference, plus AI translation of small ones when allowed
    others = [c for c in merged.values() if c not in form_classes and c.name not in ("Program", "Resources",
                                                                                     "Settings",
                                                                                     "ApplicationConfiguration")]
    for c in others[:40]:
        src = c.file.read_text(encoding="utf-8-sig", errors="replace") if c.file else c.body
        rel = c.file.relative_to(src_dir).as_posix() if c.file else f"{c.name}.cs"
        res.modules.append((rel, src, "csharp"))
    if others:
        res.add("info", f"{len(others)} other class(es) kept as C# for reference: "
                        + ", ".join(c.name for c in others[:12]) + (" ..." if len(others) > 12 else ""))
    res.resources["translation_stats"] = {"statements_translated": total_t, "statements_commented": total_u}
    res.resources["notes"] = ("resources[form_code][<form>] is the complete user code (handlers + fields + helper "
                              "methods) for the form_code_language plugin; handlers holds the bodies for others.")
    return res


def save_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
