"""VS Code "when" clause evaluation (menus, commandPalette, enablement) against a context dict.

Supports: true/false, keys (undefined -> falsy), !, &&, ||, ( ), == / != / === / !==, < <= > >=,
=~ /regex/flags, "key in otherKey", "key not in otherKey", quoted strings and numbers."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"""\s*(?:
    (?P<op>===|!==|==|!=|<=|>=|&&|\|\||=~|[!()<>])|
    (?P<regex>/(?:\\.|[^/\\])+/[a-z]*)|
    (?P<str>'[^']*'|"[^"]*")|
    (?P<word>[^\s!()<>=&|'"]+)
)""", re.X)


def _tokens(expr: str) -> list[tuple[str, str]]:
    out = []
    pos = 0
    expr = expr or ""
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            if expr[pos:].strip():
                pos += 1
                continue
            break
        pos = m.end()
        for kind in ("op", "regex", "str", "word"):
            if m.group(kind) is not None:
                out.append((kind, m.group(kind)))
                break
    return out


class _Parser:
    def __init__(self, toks, ctx):
        self.t = toks
        self.i = 0
        self.ctx = ctx

    def peek(self, k=0):
        return self.t[self.i + k] if self.i + k < len(self.t) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse_or(self):
        v = self.parse_and()
        while self.peek() == ("op", "||"):
            self.take()
            r = self.parse_and()
            v = v or r
        return v

    def parse_and(self):
        v = self.parse_not()
        while self.peek() == ("op", "&&"):
            self.take()
            r = self.parse_not()
            v = v and r
        return v

    def parse_not(self):
        if self.peek() == ("op", "!"):
            self.take()
            return not self.parse_not()
        return self.parse_cmp()

    def value(self, tok):
        kind, text = tok
        if kind == "str":
            return text[1:-1]
        if kind == "word":
            if text == "true":
                return True
            if text == "false":
                return False
            if re.fullmatch(r"-?\d+(\.\d+)?", text):
                return float(text)
            return self.ctx.get(text)
        return None

    def literal(self, tok):
        kind, text = tok
        if kind == "str":
            return text[1:-1]
        if text in ("true", "false"):
            return text == "true"
        if re.fullmatch(r"-?\d+(\.\d+)?", text or ""):
            return float(text)
        return text            # right side of == is a literal (VS Code semantics)

    def parse_cmp(self):
        if self.peek() == ("op", "("):
            self.take()
            v = self.parse_or()
            if self.peek() == ("op", ")"):
                self.take()
            return v
        left_tok = self.take()
        left = self.value(left_tok)
        kind, op = self.peek()
        if kind == "op" and op in ("==", "!=", "===", "!==", "<", "<=", ">", ">="):
            self.take()
            right = self.literal(self.take())
            if op in ("==", "==="):
                return _eq(left, right)
            if op in ("!=", "!=="):
                return not _eq(left, right)
            try:
                lf, rf = float(left), float(right)
            except (TypeError, ValueError):
                return False
            return {"<": lf < rf, "<=": lf <= rf, ">": lf > rf, ">=": lf >= rf}[op]
        if kind == "op" and op == "=~":
            self.take()
            rk, rt = self.take()
            if rk != "regex":
                return False
            body, _, flags = rt[1:].rpartition("/")
            try:
                return bool(re.search(body, str(left or ""), re.I if "i" in flags else 0))
            except re.error:
                return False
        if kind == "word" and op == "in":
            self.take()
            coll = self.value(self.take())
            return _contains(coll, left)
        if kind == "word" and op == "not" and self.peek(1) == ("word", "in"):
            self.take()
            self.take()
            coll = self.value(self.take())
            return not _contains(coll, left)
        return bool(left)


def _eq(a, b) -> bool:
    if isinstance(b, float) and not isinstance(a, bool):
        try:
            return float(a) == b
        except (TypeError, ValueError):
            return False
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b) if isinstance(b, bool) else str(a).lower() == str(b).lower()
    return str(a if a is not None else "") == str(b)


def _contains(coll, item) -> bool:
    if isinstance(coll, (list, tuple, set)):
        return item in coll
    if isinstance(coll, dict):
        return item in coll
    return False


def evaluate(expr, ctx: dict) -> bool:
    """True when the when clause holds (an empty clause holds)."""
    if expr is None or (isinstance(expr, str) and not expr.strip()):
        return True
    if isinstance(expr, bool):
        return expr
    try:
        return bool(_Parser(_tokens(str(expr)), ctx or {}).parse_or())
    except Exception:  # noqa: BLE001 - a broken clause hides nothing
        return True


__all__ = ["evaluate"]
