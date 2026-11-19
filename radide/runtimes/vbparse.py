"""Lexer and parser for a VB6-compatible BASIC dialect.

Produces a tree of tuples: (kind, line, ...). Identifiers are case-insensitive
and stored lower-case (original spelling kept where useful for messages).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


class VBSyntaxError(Exception):
    def __init__(self, msg, line):
        super().__init__(f"line {line}: {msg}")
        self.msg, self.line = msg, line


# ============================================================================ lexer
TOKEN_RX = re.compile(r"""
    (?P<ws>[ \t]+)
  | (?P<cont>[ \t]_[ \t]*(?:'[^\n]*)?\r?\n)
  | (?P<nl>\r?\n)
  | (?P<comment>'[^\n]*)
  | (?P<str>"(?:[^"\n]|"")*")
  | (?P<date>\#[0-9/:\-\s APMapm]+\#)
  | (?P<hex>&[Hh][0-9A-Fa-f]+&?)
  | (?P<oct>&[Oo][0-7]+&?)
  | (?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[%&!#@]?)
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*[$%&!#@]?)
  | (?P<op><>|<=|>=|:=|[-+*/\\^&=<>(),.:;!])
""", re.X)


@dataclass
class Tok:
    kind: str       # num str date id op nl eof
    value: object
    line: int
    raw: str = ""


def tokenize(src: str) -> list[Tok]:
    toks: list[Tok] = []
    line = 1
    pos = 0
    src = src.replace("\r\n", "\n")
    if not src.endswith("\n"):
        src += "\n"
    while pos < len(src):
        m = TOKEN_RX.match(src, pos)
        if not m:
            raise VBSyntaxError(f"unexpected character {src[pos]!r}", line)
        kind = m.lastgroup
        text = m.group()
        pos = m.end()
        if kind == "ws":
            continue
        if kind == "cont":
            line += 1
            continue
        if kind == "comment":
            continue
        if kind == "nl":
            toks.append(Tok("nl", "\n", line))
            line += 1
            continue
        if kind == "str":
            toks.append(Tok("str", text[1:-1].replace('""', '"'), line))
        elif kind == "date":
            toks.append(Tok("date", text[1:-1].strip(), line))
        elif kind == "hex":
            toks.append(Tok("num", int(text[2:].rstrip("&"), 16), line))
        elif kind == "oct":
            toks.append(Tok("num", int(text[2:].rstrip("&"), 8), line))
        elif kind == "num":
            t = text.rstrip("%&!#@")
            toks.append(Tok("num", float(t) if any(c in t for c in ".eE") else int(t), line))
        elif kind == "id":
            low = text.rstrip("$%&!#@").lower()
            if low == "rem":            # Rem comment
                end = src.find("\n", pos)
                pos = end if end >= 0 else len(src)
                continue
            toks.append(Tok("id", low, line, text.rstrip("$%&!#@")))
        else:
            toks.append(Tok("op", text, line))
    toks.append(Tok("nl", "\n", line))
    toks.append(Tok("eof", None, line))
    return toks


# ============================================================================ parser
@dataclass
class Param:
    name: str
    byref: bool = True
    optional: bool = False
    default: object = None
    paramarray: bool = False
    is_array: bool = False


@dataclass
class Proc:
    name: str
    kind: str                     # sub | function | get | let | set
    params: list[Param]
    body: list
    line: int
    public: bool = True
    display: str = ""


@dataclass
class Module:
    name: str
    procs: dict[str, Proc] = field(default_factory=dict)
    decls: list = field(default_factory=list)      # module-level Dim/Const statements
    filename: str = ""


END_WORDS = {"sub", "function", "property", "if", "select", "with", "type", "enum"}


class Parser:
    def __init__(self, toks: list[Tok]):
        self.t = toks
        self.i = 0

    # ------------------------------------------------------------ token helpers
    @property
    def cur(self) -> Tok:
        return self.t[self.i]

    def peek(self, n=1) -> Tok:
        return self.t[min(self.i + n, len(self.t) - 1)]

    def is_id(self, *words) -> bool:
        return self.cur.kind == "id" and (not words or self.cur.value in words)

    def is_op(self, *ops) -> bool:
        return self.cur.kind == "op" and self.cur.value in ops

    def next(self) -> Tok:
        tok = self.cur
        self.i += 1
        return tok

    def expect_id(self, word=None) -> Tok:
        if self.cur.kind != "id" or (word and self.cur.value != word):
            raise VBSyntaxError(f"expected {word or 'identifier'}, found {self.cur.raw or self.cur.value!r}",
                                self.cur.line)
        return self.next()

    def expect_op(self, op) -> Tok:
        if not self.is_op(op):
            raise VBSyntaxError(f"expected {op!r}, found {self.cur.raw or self.cur.value!r}", self.cur.line)
        return self.next()

    def end_of_stmt(self) -> bool:
        return self.cur.kind in ("nl", "eof") or self.is_op(":") or self.is_id("else")

    def skip_nl(self):
        while self.cur.kind == "nl" or self.is_op(":"):
            self.next()

    def eat_stmt_end(self):
        if self.is_op(":") or self.cur.kind == "nl":
            self.next()

    # ------------------------------------------------------------ module
    def parse_module(self, name: str) -> Module:
        mod = Module(name)
        while True:
            self.skip_nl()
            if self.cur.kind == "eof":
                break
            line = self.cur.line
            public = True
            if self.is_id("attribute", "option", "version", "object", "begin"):
                self._skip_line()
                continue
            mods = []
            while self.is_id("public", "private", "friend", "global", "static", "dim"):
                mods.append(self.next().value)
            if "private" in mods:
                public = False
            if self.is_id("sub", "function", "property"):
                proc = self.parse_proc(public)
                mod.procs[proc.name] = proc
                continue
            if self.is_id("declare"):              # API declarations are not supported
                self._skip_line()
                continue
            if self.is_id("type", "enum"):
                mod.decls.append(self.parse_type_or_enum())
                continue
            if self.is_id("const"):
                mod.decls.append(self.parse_const(public))
                continue
            if mods or self.is_id("dim"):
                if self.is_id("dim"):
                    self.next()
                mod.decls.append(self.parse_dim_list(line, public, "dim"))
                continue
            raise VBSyntaxError(f"unexpected {self.cur.raw or self.cur.value!r} at module level", line)
        return mod

    def _skip_line(self):
        while self.cur.kind not in ("nl", "eof"):
            self.next()

    def parse_type_or_enum(self):
        line = self.cur.line
        kind = self.next().value
        name = self.expect_id().value
        members = []
        value = 0
        self.skip_nl()
        while not (self.is_id("end") and self.peek().kind == "id" and self.peek().value == kind):
            mname = self.expect_id().value
            if kind == "enum":
                if self.is_op("="):
                    self.next()
                    value = self.parse_expr()
                members.append((mname, value))
                value = ("binop", line, "+", value, ("num", line, 1))
            else:
                if self.is_op("("):
                    while not self.is_op(")"):
                        self.next()
                    self.next()
                typ = self.parse_as()
                members.append((mname, typ))
            self.skip_nl()
        self.next()
        self.next()
        return ("enum" if kind == "enum" else "type", line, name, members)

    def parse_as(self):
        if self.is_id("as"):
            self.next()
            new = False
            if self.is_id("new"):
                self.next()
                new = True
            typ = self.expect_id().value
            while self.is_op("."):
                self.next()
                typ = self.expect_id().value
            if self.is_op("*"):          # String * 10
                self.next()
                self.next()
            return ("new:" if new else "") + typ
        return "variant"

    def parse_const(self, public=False):
        line = self.cur.line
        self.expect_id("const")
        items = []
        while True:
            name = self.expect_id().value
            self.parse_as()
            self.expect_op("=")
            items.append((name, self.parse_expr()))
            if not self.is_op(","):
                break
            self.next()
        return ("const", line, items, public)

    def parse_dim_list(self, line, public, kind):
        items = []
        while True:
            if self.is_id("withevents"):
                self.next()
            name = self.expect_id().value
            bounds = None
            if self.is_op("("):
                self.next()
                bounds = []
                while not self.is_op(")"):
                    lo = None
                    hi = self.parse_expr()
                    if self.is_id("to"):
                        self.next()
                        lo, hi = hi, self.parse_expr()
                    bounds.append((lo, hi))
                    if self.is_op(","):
                        self.next()
                self.next()
            typ = self.parse_as()
            items.append((name, bounds, typ))
            if not self.is_op(","):
                break
            self.next()
        return (kind, line, items, public)

    def parse_proc(self, public) -> Proc:
        line = self.cur.line
        kw = self.next().value
        kind = kw
        if kw == "property":
            kind = self.expect_id().value          # get / let / set
        name_tok = self.expect_id()
        params = []
        if self.is_op("("):
            self.next()
            while not self.is_op(")"):
                p = Param("")
                while self.is_id("byval", "byref", "optional", "paramarray"):
                    w = self.next().value
                    if w == "byval":
                        p.byref = False
                    elif w == "optional":
                        p.optional = True
                    elif w == "paramarray":
                        p.paramarray = True
                p.name = self.expect_id().value
                if self.is_op("("):
                    self.next()
                    self.expect_op(")")
                    p.is_array = True
                self.parse_as()
                if self.is_op("="):
                    self.next()
                    p.default = self.parse_expr()
                params.append(p)
                if self.is_op(","):
                    self.next()
            self.next()
        if kind in ("function", "get"):
            self.parse_as()
        body = self.parse_block(("end",), ("sub", "function", "property"))
        self.expect_id("end")
        self.next()
        pname = name_tok.value if kind in ("sub", "function") else f"{kind}:{name_tok.value}"
        return Proc(pname, kind, params, body, line, public, name_tok.raw)

    # ------------------------------------------------------------ blocks
    def parse_block(self, enders: tuple, end_follow: tuple = ()) -> list:
        """Statements until one of `enders` (e.g. 'end' followed by 'if')."""
        stmts = []
        while True:
            self.skip_nl()
            if self.cur.kind == "eof":
                raise VBSyntaxError("unexpected end of file (missing End ...?)", self.cur.line)
            if self.is_id(*enders):
                if self.cur.value != "end" or not end_follow:
                    return stmts
                if self.peek().kind == "id" and self.peek().value in end_follow:
                    return stmts
                if self.peek().kind in ("nl", "eof") and "" in end_follow:
                    return stmts
            stmts.append(self.parse_statement())

    def parse_statement(self):
        tok = self.cur
        line = tok.line
        # label  "name:" at statement start
        if tok.kind == "id" and self.peek().kind == "op" and self.peek().value == ":" \
                and tok.value not in ("else",):
            self.next()
            self.next()
            return ("label", line, tok.value)
        if tok.kind == "num" and self.peek().kind in ("nl", "op"):    # line numbers
            self.next()
            return ("label", line, str(tok.value))
        if tok.kind != "id":
            if self.is_op("."):                  # .Prop = x inside With
                return self.parse_simple(line)
            raise VBSyntaxError(f"unexpected {tok.value!r}", line)
        w = tok.value
        handler = getattr(self, f"st_{w}", None)
        if handler is not None:
            return handler(line)
        return self.parse_simple(line)

    # ------------------------------------------------------------ statements
    def st_dim(self, line):
        self.next()
        return self.parse_dim_list(line, False, "dim")

    st_static = st_dim

    def st_private(self, line):
        self.next()
        if self.is_id("const"):
            return self.parse_const()
        return self.parse_dim_list(line, False, "dim")

    st_public = st_private

    def st_const(self, line):
        return self.parse_const()

    def st_redim(self, line):
        self.next()
        preserve = False
        if self.is_id("preserve"):
            self.next()
            preserve = True
        d = self.parse_dim_list(line, False, "redim")
        return ("redim", line, d[2], preserve)

    def st_option(self, line):
        self._skip_line()
        return ("nop", line)

    def st_set(self, line):
        self.next()
        target = self.parse_postfix()
        self.expect_op("=")
        return ("set", line, target, self.parse_expr())

    def st_let(self, line):
        self.next()
        return self.parse_simple(line)

    def st_call(self, line):
        self.next()
        target = self.parse_postfix()
        if target[0] != "call":
            target = ("call", line, target, [])
        return ("callstmt", line, target)

    def st_exit(self, line):
        self.next()
        what = self.expect_id().value
        return ("exit", line, what)

    def st_end(self, line):
        self.next()
        return ("end", line)

    def st_stop(self, line):
        self.next()
        return ("stop", line)

    def st_goto(self, line):
        self.next()
        t = self.next()
        return ("goto", line, str(t.value))

    def st_gosub(self, line):
        self.next()
        t = self.next()
        return ("gosub", line, str(t.value))

    def st_return(self, line):
        self.next()
        return ("return", line)

    def st_on(self, line):
        self.next()
        self.expect_id("error")
        if self.is_id("resume"):
            self.next()
            self.expect_id("next")
            return ("onerror", line, "next")
        self.expect_id("goto")
        t = self.next()
        target = str(t.value)
        return ("onerror", line, "0" if target in ("0", "-1") else target)

    def st_resume(self, line):
        self.next()
        if self.is_id("next"):
            self.next()
            return ("resume", line, "next")
        if not self.end_of_stmt():
            t = self.next()
            return ("resume", line, str(t.value))
        return ("resume", line, "")

    def st_if(self, line):
        self.next()
        cond = self.parse_expr()
        self.expect_id("then")
        if self.cur.kind == "nl" or self.cur.kind == "eof":
            # block If
            branches = []
            body = self.parse_block(("elseif", "else", "end"), ("if",))
            branches.append((cond, body))
            else_body = []
            while True:
                if self.is_id("elseif"):
                    self.next()
                    c = self.parse_expr()
                    self.expect_id("then")
                    branches.append((c, self.parse_block(("elseif", "else", "end"), ("if",))))
                elif self.is_id("else"):
                    self.next()
                    else_body = self.parse_block(("end",), ("if",))
                else:
                    self.expect_id("end")
                    self.expect_id("if")
                    break
            return ("if", line, branches, else_body)
        # single-line If
        then = self._inline_stmts()
        else_body = []
        if self.is_id("else"):
            self.next()
            else_body = self._inline_stmts()
        return ("if", line, [(cond, then)], else_body)

    def _inline_stmts(self):
        out = []
        while not (self.cur.kind in ("nl", "eof") or self.is_id("else")):
            if self.cur.kind == "num":            # If x Then 100  (GoTo line)
                out.append(("goto", self.cur.line, str(self.next().value)))
                continue
            out.append(self.parse_statement())
            if self.is_op(":"):
                self.next()
        return out

    def st_select(self, line):
        self.next()
        self.expect_id("case")
        subject = self.parse_expr()
        cases = []
        else_body = None
        self.skip_nl()
        while True:
            self.skip_nl()
            if self.is_id("end"):
                self.next()
                self.expect_id("select")
                break
            self.expect_id("case")
            if self.is_id("else"):
                self.next()
                else_body = self.parse_block(("case", "end"), ("select",))
                continue
            tests = []
            while True:
                if self.is_id("is"):
                    self.next()
                    op = self.next().value
                    tests.append(("is", op, self.parse_expr()))
                else:
                    a = self.parse_expr()
                    if self.is_id("to"):
                        self.next()
                        tests.append(("range", a, self.parse_expr()))
                    else:
                        tests.append(("eq", a))
                if not self.is_op(","):
                    break
                self.next()
            cases.append((tests, self.parse_block(("case", "end"), ("select",))))
        return ("select", line, subject, cases, else_body or [])

    def st_for(self, line):
        self.next()
        if self.is_id("each"):
            self.next()
            var = self.expect_id().value
            self.expect_id("in")
            coll = self.parse_expr()
            body = self.parse_block(("next",))
            self.next()
            if self.cur.kind == "id" and not self.end_of_stmt():
                self.next()
            return ("foreach", line, var, coll, body)
        var = self.expect_id().value
        self.expect_op("=")
        start = self.parse_expr()
        self.expect_id("to")
        stop = self.parse_expr()
        step = None
        if self.is_id("step"):
            self.next()
            step = self.parse_expr()
        body = self.parse_block(("next",))
        self.next()
        if self.cur.kind == "id":
            self.next()
            while self.is_op(","):       # Next j, i
                self.next()
                self.next()
        return ("for", line, var, start, stop, step, body)

    def st_do(self, line):
        self.next()
        pre = None
        if self.is_id("while", "until"):
            kind = self.next().value
            pre = (kind, self.parse_expr())
        body = self.parse_block(("loop",))
        self.next()
        post = None
        if self.is_id("while", "until"):
            kind = self.next().value
            post = (kind, self.parse_expr())
        return ("do", line, pre, post, body)

    def st_while(self, line):
        self.next()
        cond = self.parse_expr()
        body = self.parse_block(("wend",))
        self.next()
        return ("do", line, ("while", cond), None, body)

    def st_with(self, line):
        self.next()
        obj = self.parse_expr()
        body = self.parse_block(("end",), ("with",))
        self.next()
        self.next()
        return ("with", line, obj, body)

    def st_debug(self, line):
        if self.peek().kind == "op" and self.peek().value == ".":
            self.next()
            self.next()
            what = self.expect_id().value
            args = []
            seps = []
            while not self.end_of_stmt():
                args.append(self.parse_expr())
                if self.is_op(";", ","):
                    seps.append(self.next().value)
            return ("debugprint", line, what, args, seps)
        return self.parse_simple(line)

    def st_print(self, line):
        self.next()
        args = []
        while not self.end_of_stmt():
            args.append(self.parse_expr())
            if self.is_op(";", ","):
                self.next()
        return ("debugprint", line, "print", args, [])

    def st_unload(self, line):
        self.next()
        return ("unload", line, self.parse_expr())

    def st_load(self, line):
        self.next()
        return ("loadform", line, self.parse_expr())

    def st_randomize(self, line):
        self.next()
        if not self.end_of_stmt():
            self.parse_expr()
        return ("callstmt", line, ("call", line, ("name", line, "randomize"), []))

    def st_erase(self, line):
        self.next()
        names = [self.expect_id().value]
        while self.is_op(","):
            self.next()
            names.append(self.expect_id().value)
        return ("erase", line, names)

    def st_mid(self, line):
        return self.parse_simple(line)

    # ------------------------------------------------------------ simple: assignment or call
    def parse_simple(self, line):
        target = self.parse_postfix()
        if self.is_op("="):
            self.next()
            return ("assign", line, target, self.parse_expr())
        if self.end_of_stmt():
            if target[0] == "call":
                return ("callstmt", line, target)
            return ("callstmt", line, ("call", line, target, []))
        # call without parentheses: Foo a, b
        args = []
        if target[0] == "call" and self.is_op(","):     # Foo (a), b
            args = list(target[3])
            target = target[2]
            self.next()
        while not self.end_of_stmt():
            if self.is_op(","):
                args.append(("missing", line))
                self.next()
                continue
            args.append(self.parse_arg())
            if self.is_op(","):
                self.next()
                if self.end_of_stmt():
                    args.append(("missing", line))
        return ("callstmt", line, ("call", line, target, args))

    def parse_arg(self):
        if self.cur.kind == "id" and self.peek().kind == "op" and self.peek().value == ":=":
            name = self.next().value
            self.next()
            return ("named", self.cur.line, name, self.parse_expr())
        if self.is_id("byval"):
            self.next()
        return self.parse_expr()

    # ------------------------------------------------------------ expressions
    BINARY = [
        ("imp",), ("eqv",), ("xor",), ("or",), ("and",),
    ]

    def parse_expr(self):
        return self._logic(0)

    def _logic(self, level):
        ops = ["imp", "eqv", "xor", "or", "and"]
        if level == len(ops):
            return self._not()
        left = self._logic(level + 1)
        while self.is_id(ops[level]):
            line = self.next().line
            left = ("binop", line, ops[level], left, self._logic(level + 1))
        return left

    def _not(self):
        if self.is_id("not"):
            line = self.next().line
            return ("unop", line, "not", self._not())
        return self._compare()

    def _compare(self):
        left = self._concat()
        while self.is_op("=", "<>", "<", ">", "<=", ">=") or self.is_id("like", "is"):
            tok = self.next()
            op = tok.value
            left = ("binop", tok.line, op, left, self._concat())
        return left

    def _concat(self):
        left = self._add()
        while self.is_op("&"):
            line = self.next().line
            left = ("binop", line, "&", left, self._add())
        return left

    def _add(self):
        left = self._mod()
        while self.is_op("+", "-"):
            tok = self.next()
            left = ("binop", tok.line, tok.value, left, self._mod())
        return left

    def _mod(self):
        left = self._intdiv()
        while self.is_id("mod"):
            line = self.next().line
            left = ("binop", line, "mod", left, self._intdiv())
        return left

    def _intdiv(self):
        left = self._mul()
        while self.is_op("\\"):
            line = self.next().line
            left = ("binop", line, "\\", left, self._mul())
        return left

    def _mul(self):
        left = self._unary()
        while self.is_op("*", "/"):
            tok = self.next()
            left = ("binop", tok.line, tok.value, left, self._unary())
        return left

    def _unary(self):
        if self.is_op("-"):
            line = self.next().line
            return ("unop", line, "-", self._unary())
        if self.is_op("+"):
            self.next()
            return self._unary()
        return self._power()

    def _power(self):
        left = self.parse_postfix()
        while self.is_op("^"):
            line = self.next().line
            right = self._unary_power()
            left = ("binop", line, "^", left, right)
        return left

    def _unary_power(self):
        if self.is_op("-"):
            line = self.next().line
            return ("unop", line, "-", self.parse_postfix())
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.is_op("."):
                line = self.next().line
                name = self.next()
                node = ("member", line, node, str(name.value), name.raw or str(name.value))
            elif self.is_op("!"):
                line = self.next().line
                name = self.next()
                node = ("call", line, node, [("str", line, str(name.raw or name.value))])
            elif self.is_op("("):
                line = self.next().line
                args = []
                while not self.is_op(")"):
                    if self.is_op(","):
                        args.append(("missing", line))
                        self.next()
                        continue
                    args.append(self.parse_arg())
                    if self.is_op(","):
                        self.next()
                        if self.is_op(")"):
                            args.append(("missing", line))
                self.next()
                node = ("call", line, node, args)
            else:
                return node

    def parse_primary(self):
        tok = self.cur
        line = tok.line
        if tok.kind == "num":
            self.next()
            return ("num", line, tok.value)
        if tok.kind == "str":
            self.next()
            return ("str", line, tok.value)
        if tok.kind == "date":
            self.next()
            return ("date", line, tok.value)
        if self.is_op("("):
            self.next()
            e = self.parse_expr()
            self.expect_op(")")
            return ("paren", line, e)
        if self.is_op("."):                      # With-member
            self.next()
            name = self.next()
            return ("member", line, ("withobj", line), str(name.value), name.raw or str(name.value))
        if tok.kind == "id":
            w = tok.value
            if w == "new":
                self.next()
                cls = self.expect_id().value
                return ("new", line, cls)
            if w in ("true", "false"):
                self.next()
                return ("bool", line, w == "true")
            if w == "nothing":
                self.next()
                return ("nothing", line)
            if w in ("empty", "null"):
                self.next()
                return ("empty", line)
            if w == "me":
                self.next()
                return ("me", line)
            if w == "typeof":
                self.next()
                obj = self.parse_postfix()
                self.expect_id("is")
                cls = self.expect_id().value
                return ("typeof", line, obj, cls)
            if w == "addressof":
                self.next()
                return ("str", line, self.expect_id().value)
            self.next()
            return ("name", line, w, tok.raw)
        raise VBSyntaxError(f"unexpected {tok.raw or tok.value!r} in expression", line)


def parse_module(src: str, name: str = "Module1", filename: str = "") -> Module:
    mod = Parser(tokenize(src)).parse_module(name)
    mod.filename = filename
    return mod


def parse_expression(src: str):
    p = Parser(tokenize(src))
    e = p.parse_expr()
    return e
