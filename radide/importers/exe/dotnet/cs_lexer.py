"""Tokenizer of the C-like languages (C# / Java) read by the .NET and Java importers."""
from __future__ import annotations

import re


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
