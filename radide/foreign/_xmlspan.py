"""XML with source spans, for writers that must PRESERVE the original file byte for byte.

``parse(data: bytes) -> XNode`` builds a light tree whose nodes know where their start tag, content
and end tag are in the original bytes (expat byte offsets). ``Patch`` collects replacements on
those spans and applies them, so everything that is not edited (comments, unknown elements and
attributes, formatting, entity spelling, attribute order) stays exactly as it was.
"""
from __future__ import annotations

import re
from xml.parsers import expat


class XNode:
    __slots__ = ("tag", "attrib", "children", "parent", "s", "se", "es", "e", "text", "empty")

    def __init__(self, tag: str, attrib: dict, parent: "XNode | None", s: int):
        self.tag, self.attrib, self.parent, self.s = tag, attrib, parent, s
        self.children: list[XNode] = []
        self.se = self.es = self.e = s
        self.text = ""
        self.empty = False

    def __repr__(self):
        return f"<XNode {self.tag} {self.attrib.get('name', '')}>"

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def find(self, tag: str, **attrs) -> "XNode | None":
        for c in self.children:
            if c.tag == tag and all(c.attrib.get(k) == v for k, v in attrs.items()):
                return c
        return None

    def findall(self, tag: str) -> list["XNode"]:
        return [c for c in self.children if c.tag == tag]

    def iter(self, tag: str | None = None):
        if tag is None or self.tag == tag:
            yield self
        for c in self.children:
            yield from c.iter(tag)

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent


def _tag_end(data: bytes, i: int) -> int:
    """Index just after the '>' of the tag that starts at *i* (quotes respected)."""
    q = None
    n = len(data)
    while i < n:
        c = data[i]
        if q is not None:
            if c == q:
                q = None
        elif c in (0x22, 0x27):
            q = c
        elif c == 0x3E:
            return i + 1
        i += 1
    return n


def parse(data: bytes) -> XNode:
    p = expat.ParserCreate()
    p.buffer_text = True
    p.ordered_attributes = True
    stack: list[XNode] = []
    root_holder: list[XNode] = []

    def start(tag, attrs):
        s = p.CurrentByteIndex
        node = XNode(tag, dict(zip(attrs[::2], attrs[1::2])), stack[-1] if stack else None, s)
        node.se = _tag_end(data, s)
        node.empty = data[node.se - 2:node.se] == b"/>"
        if stack:
            stack[-1].children.append(node)
        else:
            root_holder.append(node)
        stack.append(node)

    def end(tag):
        node = stack.pop()
        if node.empty:
            node.es = node.e = node.se
        else:
            node.es = p.CurrentByteIndex
            node.e = _tag_end(data, node.es)

    def chars(text):
        if stack:
            stack[-1].text += text

    p.StartElementHandler = start
    p.EndElementHandler = end
    p.CharacterDataHandler = chars
    p.Parse(data, True)
    if not root_holder:
        raise ValueError("empty XML document")
    return root_holder[0]


def escape_text(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(s: str) -> str:
    return escape_text(s).replace('"', "&quot;").replace("\n", "&#xa;").replace("\r", "&#xd;")


class Patch:
    """Non-overlapping byte replacements on the original document."""

    def __init__(self, data: bytes, newline: bytes | None = None):
        self.data = data
        self.edits: list[tuple[int, int, bytes]] = []
        self.nl = newline or (b"\r\n" if b"\r\n" in data else b"\n")

    def replace(self, s: int, e: int, new) -> None:
        if isinstance(new, str):
            new = new.encode("utf-8")
        self.edits.append((s, e, new))

    def insert(self, at: int, new) -> None:
        self.replace(at, at, new)

    def apply(self) -> bytes:
        out = self.data
        last = None
        for s, e, new in sorted(self.edits, key=lambda x: (x[0], x[1]), reverse=True):
            if last is not None and e > last:
                raise ValueError("overlapping XML edits")
            out = out[:s] + new + out[e:]
            last = s
        return out

    # ---------------------------------------------------------------- helpers
    def indent_at(self, pos: int) -> bytes:
        """Whitespace between the start of the line and *pos*."""
        ls = self.data.rfind(b"\n", 0, pos) + 1
        ws = self.data[ls:pos]
        return ws if not ws.strip() else b""

    def child_indent(self, node: XNode) -> bytes:
        if node.children:
            return self.indent_at(node.children[0].s)
        base = self.indent_at(node.s)
        unit = self._unit()
        return base + unit

    def _unit(self) -> bytes:
        m = re.search(rb"\n([ \t]+)<", self.data)       # the first indented element: a child of the root
        if not m:
            return b" "
        return m.group(1)[:1] if m.group(1)[:1] == b"\t" else m.group(1)

    def set_text(self, node: XNode, value: str) -> None:
        if node.empty:
            start = self.data[node.s:node.se - 2].rstrip()
            self.replace(node.s, node.e, start + b">" + escape_text(value).encode() + f"</{node.tag}>".encode())
        else:
            self.replace(node.se, node.es, escape_text(value))

    def set_attr(self, node: XNode, key: str, value: str) -> None:
        tag = self.data[node.s:node.se]
        rx = re.compile(rb"(\s" + re.escape(key.encode()) + rb'\s*=\s*)(["\'])(.*?)\2', re.S)
        m = rx.search(tag)
        if m:
            new = tag[:m.start(3)] + escape_attr(value).encode() + tag[m.end(3):]
        else:
            close = tag.rfind(b"/>") if node.empty else tag.rfind(b">")
            new = tag[:close].rstrip() + f' {key}="{escape_attr(value)}"'.encode() + tag[close:]
        self.replace(node.s, node.se, new)

    def remove(self, node: XNode) -> None:
        """Remove an element together with the indentation/newline in front of it."""
        s = node.s
        ls = self.data.rfind(b"\n", 0, s)
        if ls >= 0 and not self.data[ls + 1:s].strip():
            s = ls - 1 if ls > 0 and self.data[ls - 1:ls] == b"\r" else ls
        self.replace(s, node.e, b"")

    def append_child(self, parent: XNode, xml_lines: list[str], before: XNode | None = None) -> None:
        """Insert an element (given as lines without indentation, nested lines indented with ONE
        space per level) as the last child of *parent* (or before the child *before*)."""
        ind = self.child_indent(parent)
        unit = self._unit()
        body = self.nl.join(ind + _reindent(line, unit).encode("utf-8") for line in xml_lines)
        if before is not None:
            self.insert(before.s, body.lstrip() + self.nl + self.indent_at(before.s))
            return
        if parent.empty:
            open_tag = self.data[parent.s:parent.se - 2].rstrip() + b">"
            close = self.indent_at(parent.s)
            self.replace(parent.s, parent.e, open_tag + self.nl + body + self.nl + close +
                         f"</{parent.tag}>".encode())
            return
        # after the last non-space byte before the end tag
        i = parent.es
        while i > parent.se and self.data[i - 1:i] in (b" ", b"\t", b"\n", b"\r"):
            i -= 1
        self.insert(i, self.nl + body)


def _reindent(line: str, unit: bytes) -> str:
    n = len(line) - len(line.lstrip(" "))
    return unit.decode() * n + line[n:]
