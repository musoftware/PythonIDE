"""Bind an IDE editor to a shared document of a session.

* Monaco (radide/monaco_editor.py): a small script is injected into the page through the existing `rad`
  bridge (editor._js) and talks back through the channel object "collab" (MonacoEditor.channel_objects).
  Local edits leave the page as code-point operations; remote edits enter it as operations too.  The two
  ends are reconciled with the Jupiter algorithm (ot.py) so a keystroke and a remote edit that cross on the
  asynchronous web channel still end up identical.  Remote cursors and selections are Monaco decorations
  (one colour and a name label per participant).
* The built-in editor (QPlainTextEdit): same thread, so a text diff per change is enough.
"""
from __future__ import annotations

import json
import re

from PyQt6.QtCore import QObject, pyqtSlot

from . import ot

CHANNEL = "collab"

JS = r"""
(function () {
  if (window.radCollab) return;
  const ed = window.radEditor, model = ed.getModel();
  const SUR = /[\uD800-\uDFFF]/;
  function cpToU(t, cp) { if (!SUR.test(t)) return Math.min(cp, t.length); let u = 0;
    for (let i = 0; i < cp && u < t.length; i++) { const c = t.charCodeAt(u); u += (c >= 0xD800 && c <= 0xDBFF) ? 2 : 1; }
    return u; }
  function uToCp(t, u) { if (!SUR.test(t)) return u; let n = 0;
    for (let i = 0; i < u && i < t.length; i++) { const c = t.charCodeAt(i); if (!(c >= 0xDC00 && c <= 0xDFFF)) n++; }
    return n; }
  function cpLen(s) { return SUR.test(s) ? Array.from(s).length : s.length; }
  // ---- OT (same rules as radide/collab/ot.py)
  function t1(a, b, aw) {
    if (a[0] === 'i') {
      if (b[0] === 'i') { if (a[1] < b[1] || (a[1] === b[1] && aw)) return [a]; return [['i', a[1] + cpLen(b[2]), a[2]]]; }
      const bp = b[1], bn = b[2];
      if (a[1] <= bp) return [a]; if (a[1] >= bp + bn) return [['i', a[1] - bn, a[2]]]; return [['i', bp, a[2]]];
    }
    const ap = a[1], an = a[2];
    if (b[0] === 'i') { const bp = b[1], L = cpLen(b[2]);
      if (bp <= ap) return [['d', ap + L, an]]; if (bp >= ap + an) return [a];
      const k = bp - ap; return [['d', ap, k], ['d', ap + L, an - k]]; }
    const bp = b[1], bn = b[2];
    if (ap + an <= bp) return [a]; if (ap >= bp + bn) return [['d', ap - bn, an]];
    const ov = Math.min(ap + an, bp + bn) - Math.max(ap, bp), n = an - ov;
    return n > 0 ? [['d', Math.min(ap, bp), n]] : [];
  }
  function noop(p) { return (p[0] === 'i' && !p[2]) || (p[0] === 'd' && p[2] <= 0); }
  function xform(A, B, aw) {
    A = A.filter(p => !noop(p)); B = B.filter(p => !noop(p));
    if (!A.length || !B.length) return [A, B];
    if (A.length === 1 && B.length === 1) return [t1(A[0], B[0], aw), t1(B[0], A[0], !aw)];
    if (A.length > 1) { const [a1, b1] = xform(A.slice(0, 1), B, aw); const [r, b2] = xform(A.slice(1), b1, aw);
      return [a1.concat(r), b2]; }
    const [a1, b1] = xform(A, B.slice(0, 1), aw); const [a2, r] = xform(a1, B.slice(1), aw);
    return [a2, b1.concat(r)];
  }
  const S = { active: false, epoch: 0, my: 0, other: 0, out: [], applying: false, prev: '', decos: [], styles: {} };
  function bridge() { return window.radChannel && window.radChannel.objects.collab; }
  function applyOps(ops) {
    S.applying = true;
    try {
      for (const op of ops) {
        const t = model.getValue(); const u = cpToU(t, op[1]);
        let range;
        if (op[0] === 'i') { const p = model.getPositionAt(u); range = new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column);
          model.applyEdits([{ range: range, text: op[2], forceMoveMarkers: false }]); }
        else { const u2 = cpToU(t, op[1] + op[2]); const p1 = model.getPositionAt(u), p2 = model.getPositionAt(u2);
          model.applyEdits([{ range: new monaco.Range(p1.lineNumber, p1.column, p2.lineNumber, p2.column), text: '' }]); }
      }
    } finally { S.applying = false; S.prev = model.getValue(); }
  }
  ed.onDidChangeModelContent(ev => {
    const cur = model.getValue();
    if (!S.active || S.applying) { S.prev = cur; return; }
    const prev = S.prev; S.prev = cur;
    let ops = [];
    if (ev.isFlush) { ops = [['d', 0, cpLen(prev)], ['i', 0, cur]]; }
    else {
      const ch = ev.changes.slice().sort((a, b) => b.rangeOffset - a.rangeOffset);
      for (const c of ch) {
        const p = uToCp(prev, c.rangeOffset);
        const n = cpLen(prev.substr(c.rangeOffset, c.rangeLength));
        if (n) ops.push(['d', p, n]);
        if (c.text) ops.push(['i', p, c.text]);
      }
    }
    ops = ops.filter(p => !noop(p));
    if (!ops.length) return;
    const msg = { epoch: S.epoch, ops: ops, my: S.my, other: S.other };
    S.out.push([S.my, ops]); S.my++;
    const b = bridge(); if (b) b.jsOps(JSON.stringify(msg));
  });
  ed.onDidChangeCursorSelection(e => {
    if (!S.active) return; const s = e.selection, t = model.getValue();
    const a = uToCp(t, model.getOffsetAt({ lineNumber: s.selectionStartLineNumber, column: s.selectionStartColumn }));
    const h = uToCp(t, model.getOffsetAt({ lineNumber: s.positionLineNumber, column: s.positionColumn }));
    const b = bridge(); if (b) b.jsCursor(S.epoch, a, h);
  });
  function style(id, color, name) {
    const key = id + color + name; if (S.styles[id] === key) return; S.styles[id] = key;
    let el = document.getElementById('rc-style-' + id);
    if (!el) { el = document.createElement('style'); el.id = 'rc-style-' + id; document.head.appendChild(el); }
    const label = String(name).replace(/["\\\n]/g, ' ');
    el.textContent = '.rc-s-' + id + '{background:' + color + '40;}' +
      '.rc-c-' + id + '{border-left:2px solid ' + color + ';margin-left:-1px;position:relative;}' +
      '.rc-c-' + id + '::after{content:"' + label + '";position:absolute;left:-2px;top:-1.15em;font:10px/1.2 Segoe UI,sans-serif;' +
      'background:' + color + ';color:#fff;padding:0 3px;border-radius:2px 2px 2px 0;white-space:nowrap;pointer-events:none;z-index:5;}';
  }
  window.radCollab = {
    start(text, epoch) {
      S.active = false; S.epoch = epoch; S.my = 0; S.other = 0; S.out = [];
      const cur = model.getValue();
      if (cur !== text) {
        const a = Array.from(cur), b = Array.from(text); let s = 0, e = 0;
        while (s < a.length && s < b.length && a[s] === b[s]) s++;
        while (e < a.length - s && e < b.length - s && a[a.length - 1 - e] === b[b.length - 1 - e]) e++;
        const ops = []; if (a.length - e - s > 0) ops.push(['d', s, a.length - e - s]);
        if (b.length - e - s > 0) ops.push(['i', s, b.slice(s, b.length - e).join('')]);
        applyOps(ops);
      }
      S.prev = model.getValue(); S.active = true;
    },
    stop() { S.active = false; S.decos = ed.deltaDecorations(S.decos, []); },
    remote(msg) {
      if (!S.active || msg.epoch !== S.epoch) return;
      let ops = msg.ops; S.out = S.out.filter(e => e[0] >= msg.other);
      for (const e of S.out) { const r = xform(ops, e[1], true); ops = r[0]; e[1] = r[1]; }
      S.other++;
      applyOps(ops);
    },
    cursors(list) {
      const t = model.getValue(), d = [];
      for (const c of list) {
        style(c.id, c.color, c.name);
        const pa = model.getPositionAt(cpToU(t, c.a)), ph = model.getPositionAt(cpToU(t, c.h));
        if (c.a !== c.h) {
          const r = c.a < c.h ? new monaco.Range(pa.lineNumber, pa.column, ph.lineNumber, ph.column)
                              : new monaco.Range(ph.lineNumber, ph.column, pa.lineNumber, pa.column);
          d.push({ range: r, options: { className: 'rc-s-' + c.id, stickiness: 1 } });
        }
        d.push({ range: new monaco.Range(ph.lineNumber, ph.column, ph.lineNumber, ph.column),
                 options: { beforeContentClassName: 'rc-c-' + c.id, stickiness: 1, hoverMessage: { value: c.name } } });
      }
      S.decos = ed.deltaDecorations(S.decos, d);
    },
    reveal(cp) { const p = model.getPositionAt(cpToU(model.getValue(), cp)); ed.revealPositionInCenterIfOutsideViewport(p); },
    value() { return model.getValue(); },
    count() { return S.decos.length; }
  };
})();
"""


class CollabChannel(QObject):
    """Published to the Monaco page as channel object "collab" (one per editor)."""

    def __init__(self, editor):
        super().__init__()
        self.editor = editor

    @pyqtSlot(str)
    def jsOps(self, payload):
        b = getattr(self.editor, "_collab_binding", None)
        if b is not None:
            b._on_js_ops(payload)

    @pyqtSlot(int, int, int)
    def jsCursor(self, epoch, anchor, head):
        b = getattr(self.editor, "_collab_binding", None)
        if b is not None:
            b._on_js_cursor(epoch, anchor, head)


def register_channel() -> None:
    """Must run before editors are created (radide/features/live_share.py install)."""
    try:
        from ..monaco_editor import MonacoEditor
    except Exception:  # noqa: BLE001 - no QtWebEngine: only the built-in editor exists
        return
    MonacoEditor.channel_objects.setdefault(CHANNEL, CollabChannel)


_EPOCH = [0]


def bind(session, path: str, editor):
    """The right binding for this editor (or None)."""
    if getattr(editor, "_extra_objects", None) is not None and CHANNEL in editor._extra_objects:
        return MonacoBinding(session, path, editor)
    if hasattr(editor, "toPlainText") and hasattr(editor, "textChanged") and hasattr(editor, "document"):
        return PlainBinding(session, path, editor)
    return None


class _Binding:
    def __init__(self, session, path: str, editor):
        self.session, self.path, self.editor = session, path, editor
        self.cursors: dict[int, tuple] = {}
        self.local_sel = (0, 0)
        editor._collab_binding = self

    @property
    def doc(self):
        return self.session.docs.get(self.path)

    def set_cursor(self, pid: int, a: int, h: int) -> None:
        if pid == self.session.me:
            return
        self.cursors[pid] = (a, h)
        self._push_cursors()

    def drop_cursor(self, pid: int) -> None:
        if self.cursors.pop(pid, None) is not None:
            self._push_cursors()

    def _push_cursors(self) -> None:
        pass

    def detach(self) -> None:
        if getattr(self.editor, "_collab_binding", None) is self:
            self.editor._collab_binding = None


class MonacoBinding(_Binding):
    def __init__(self, session, path, editor):
        super().__init__(session, path, editor)
        self.jup = ot.Jupiter(wins=True)
        self.epoch = 0
        editor._js(JS)
        self.restart()

    def restart(self) -> None:
        """(Re)start the link from the document's current text (also after a reset)."""
        doc = self.doc
        if doc is None:
            return
        _EPOCH[0] += 1
        self.epoch = _EPOCH[0]
        self.jup = ot.Jupiter(wins=True)
        text = doc.value()
        if not getattr(self.editor, "_ready", True):
            self.editor._text = text          # the page is not loaded yet: it will start with this text
        self.editor._js(f"radCollab.start({json.dumps(text)}, {self.epoch});")

    def remote(self, ops: list) -> None:
        if not ops:
            return
        msg = self.jup.generate(ops)
        msg["epoch"] = self.epoch
        self.editor._js(f"radCollab.remote({json.dumps(msg)});")

    def _on_js_ops(self, payload: str) -> None:
        try:
            msg = json.loads(payload)
        except ValueError:
            return
        if msg.get("epoch") != self.epoch:
            return                                  # made before a reset: the reset already replaced it
        ops = self.jup.receive(msg)
        self.session.local_edit(self.path, ops)

    def _on_js_cursor(self, epoch: int, a: int, h: int) -> None:
        if epoch == self.epoch:
            self.local_sel = (a, h)
            self.session.send_cursor(self.path, a, h)

    def _push_cursors(self) -> None:
        items = []
        for pid, (a, h) in self.cursors.items():
            p = self.session.participant(pid)
            if p is not None:
                items.append({"id": pid, "a": a, "h": h, "color": p.color,
                              "name": re.sub(r"[<>\"'\\]", "", p.name)})
        self.editor._js(f"radCollab.cursors({json.dumps(items)});")

    def reveal(self, cp: int) -> None:
        self.editor._js(f"radCollab.reveal({int(cp)});")

    def detach(self) -> None:
        self.editor._js("window.radCollab && radCollab.stop();")
        super().detach()


class PlainBinding(_Binding):
    """QPlainTextEdit-based editors (radide.editor.CodeEditor)."""

    def __init__(self, session, path, editor):
        super().__init__(session, path, editor)
        self._applying = False
        self._shadow = editor.toPlainText()
        editor.textChanged.connect(self._on_changed)
        editor.cursorPositionChanged.connect(self._on_cursor)
        self.restart()

    def restart(self) -> None:
        doc = self.doc
        if doc is not None and doc.value() != self._shadow:
            self._apply(ot.diff(self._shadow, doc.value()))

    def _u16(self, text: str, cp: int) -> int:
        return len(text[:cp].encode("utf-16-le")) // 2

    def _apply(self, ops) -> None:
        from PyQt6.QtGui import QTextCursor
        self._applying = True
        try:
            for op in ops:
                text = self.editor.toPlainText()
                c = QTextCursor(self.editor.document())
                c.setPosition(self._u16(text, op[1]))
                if op[0] == "i":
                    c.insertText(op[2])
                else:
                    c.setPosition(self._u16(text, op[1] + op[2]), QTextCursor.MoveMode.KeepAnchor)
                    c.removeSelectedText()
        finally:
            self._applying = False
            self._shadow = self.editor.toPlainText()

    def remote(self, ops) -> None:
        self._apply(ops)

    def _on_changed(self) -> None:
        if self._applying or getattr(self.editor, "_collab_binding", None) is not self:
            return
        new = self.editor.toPlainText()
        ops = ot.diff(self._shadow, new)
        self._shadow = new
        if ops:
            self.session.local_edit(self.path, ops)

    def _on_cursor(self) -> None:
        if getattr(self.editor, "_collab_binding", None) is not self:
            return
        c = self.editor.textCursor()
        text = self.editor.toPlainText()

        def cp(u):
            return len(text.encode("utf-16-le")[:2 * u].decode("utf-16-le", errors="ignore"))
        self.local_sel = (cp(c.anchor()), cp(c.position()))
        self.session.send_cursor(self.path, *self.local_sel)

    def reveal(self, cp: int) -> None:
        pass

    def detach(self) -> None:
        for sig, slot in ((self.editor.textChanged, self._on_changed),
                          (self.editor.cursorPositionChanged, self._on_cursor)):
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        super().detach()
