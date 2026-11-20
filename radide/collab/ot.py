"""Plain-text operational transformation used *between Python and the Monaco page* of one editor.

The documents themselves are CRDTs (pycrdt / Yjs, see textdoc.py) - they converge between IDEs no matter
the order in which updates arrive.  But the Monaco model lives in a web page and talks to Python through an
asynchronous QWebChannel: a keystroke typed in the page and a remote edit sent by Python can cross each
other.  That two-party link is reconciled with the Jupiter algorithm (Nichols et al. 1995, the algorithm
behind Google Wave / Jupyter's early collaboration): each side counts the operations it generated and the
ones it received, and transforms incoming operations against its own not-yet-acknowledged ones.  Python is
the "server" side and wins insertion ties.  The JavaScript twin lives in js.py and uses the same rules.

Operations are lists of primitives, positions in Unicode code points:
    ("i", pos, text)      insert text at pos
    ("d", pos, count)     delete count characters starting at pos
A list is applied in order (each primitive sees the text left by the previous one).
"""
from __future__ import annotations

Prim = tuple
Ops = list


def apply(text: str, ops: Ops) -> str:
    for op in ops:
        if op[0] == "i":
            p = max(0, min(op[1], len(text)))
            text = text[:p] + op[2] + text[p:]
        else:
            p = max(0, min(op[1], len(text)))
            text = text[:p] + text[p + op[2]:]
    return text


def _t1(a: Prim, b: Prim, a_wins: bool) -> Ops:
    """a transformed so that it applies after b (both were made on the same text)."""
    if a[0] == "i":
        if b[0] == "i":
            if a[1] < b[1] or (a[1] == b[1] and a_wins):
                return [a]
            return [("i", a[1] + len(b[2]), a[2])]
        bp, bn = b[1], b[2]                      # b deletes
        if a[1] <= bp:
            return [a]
        if a[1] >= bp + bn:
            return [("i", a[1] - bn, a[2])]
        return [("i", bp, a[2])]
    ap, an = a[1], a[2]                          # a deletes
    if b[0] == "i":
        bp, L = b[1], len(b[2])
        if bp <= ap:
            return [("d", ap + L, an)]
        if bp >= ap + an:
            return [a]
        k = bp - ap                              # the insertion lands inside the deleted range: split
        return [("d", ap, k), ("d", ap + L, an - k)]
    bp, bn = b[1], b[2]
    if ap + an <= bp:
        return [a]
    if ap >= bp + bn:
        return [("d", ap - bn, an)]
    overlap = min(ap + an, bp + bn) - max(ap, bp)
    n = an - overlap
    return [("d", min(ap, bp), n)] if n > 0 else []


def xform(A: Ops, B: Ops, a_wins: bool) -> tuple[Ops, Ops]:
    """(A', B'): A' = A after B, B' = B after A, so that apply(apply(s, A), B') == apply(apply(s, B), A')."""
    A = [p for p in A if not _noop(p)]
    B = [p for p in B if not _noop(p)]
    if not A or not B:
        return A, B
    if len(A) == 1 and len(B) == 1:
        return _t1(A[0], B[0], a_wins), _t1(B[0], A[0], not a_wins)
    if len(A) > 1:
        a1, b1 = xform(A[:1], B, a_wins)
        rest, b2 = xform(A[1:], b1, a_wins)
        return a1 + rest, b2
    a1, b1 = xform(A, B[:1], a_wins)
    a2, rest = xform(a1, B[1:], a_wins)
    return a2, b1 + rest


def _noop(p: Prim) -> bool:
    return (p[0] == "i" and not p[2]) or (p[0] == "d" and p[2] <= 0)


def diff(old: str, new: str) -> Ops:
    """A minimal single-range edit turning old into new (common prefix / suffix)."""
    if old == new:
        return []
    n = min(len(old), len(new))
    s = 0
    while s < n and old[s] == new[s]:
        s += 1
    e = 0
    while e < n - s and old[len(old) - 1 - e] == new[len(new) - 1 - e]:
        e += 1
    ops: Ops = []
    if len(old) - e - s > 0:
        ops.append(("d", s, len(old) - e - s))
    if len(new) - e - s > 0:
        ops.append(("i", s, new[s:len(new) - e]))
    return ops


def transform_index(i: int, ops: Ops, after: bool = True) -> int:
    """Where position i ends up after ops (cursor mapping)."""
    for op in ops:
        if op[0] == "i":
            if op[1] < i or (op[1] == i and after):
                i += len(op[2])
        else:
            if op[1] < i:
                i -= min(op[2], i - op[1])
    return i


class Jupiter:
    """One end of a Jupiter link.  `wins` decides insertion ties (exactly one end must win)."""

    def __init__(self, wins: bool):
        self.wins = wins
        self.my = 0             # operations generated here
        self.other = 0          # operations received from the other end
        self.outgoing: list[list] = []      # [index, ops] not yet acknowledged

    def generate(self, ops: Ops) -> dict:
        """A local operation (already applied here) -> the message for the other end."""
        msg = {"ops": [list(p) for p in ops], "my": self.my, "other": self.other}
        self.outgoing.append([self.my, list(ops)])
        self.my += 1
        return msg

    def receive(self, msg: dict) -> Ops:
        """A message from the other end -> the operations to apply here."""
        ops = [tuple(p) for p in msg["ops"]]
        acked = int(msg["other"])
        self.outgoing = [e for e in self.outgoing if e[0] >= acked]
        for e in self.outgoing:
            ops, e[1] = xform(ops, e[1], not self.wins)
        self.other += 1
        return ops
