"""Recursive-descent parser of C# (and the Java subset java.py reads) into a small tuple AST."""
from __future__ import annotations

import re

from .cs_lexer import _unescape, ParseError, Tok, tokenize


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
