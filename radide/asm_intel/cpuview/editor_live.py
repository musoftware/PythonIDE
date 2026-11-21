"""The assembly source editor while debugging (and while editing):

* **jump arrows** in the gutter for jmp / jcc / loop / call whose target label is in the same file (always on);
  the arrow of the current conditional jump is red when it will be taken, grey and dashed when not;
* **register highlighting**: put the caret on a register and every read (blue) / write (orange) of that register
  (al / ax / eax / rax are one register) inside the same procedure is marked, also in the overview ruler;
* **inline values** after each executed line, e.g. ``; rax=0x5  rbx=0x7  ZF=1`` (while debugging);
* **register hover** with the live value in hex / unsigned / signed / characters (while debugging) - Monaco merges
  it with the instruction / register documentation of radide/asm_intel.

Everything is drawn by a small script injected into the editor page (``JS``); Python pushes the data:
``push_static(ed)`` (arrows, register references, procedures - recomputed when the text changes),
``set_inline(ed, {line: text})``, ``set_registers(ed, {...})``, ``set_taken(ed, line, taken)``, ``clear_live(ed)``.
A copy of what was pushed stays in ``ed._radcpu`` (tests, the CPU view).
"""
from __future__ import annotations

import json

from . import analysis as A

JS = r"""(function () {
  if (window.__radCpu) return;
  const ed = window.radEditor;
  if (!ed || !window.monaco) return;
  window.__radCpu = true;
  const st = { arrows: [], refs: [], procs: [], inline: {}, regs: {}, taken: null, hi: [], inl: [], fam: '' };
  window.radCpuState = st;
  const css = document.createElement('style');
  css.textContent = `
    .rad-reg-r { background: rgba(70, 140, 255, 0.28); border-radius: 2px; }
    .rad-reg-w { background: rgba(255, 140, 0, 0.38); border-radius: 2px; }
    .rad-reg-rw { background: rgba(255, 140, 0, 0.28); border-bottom: 2px solid rgba(70, 140, 255, 0.8); }
    .rad-cpu-inline { color: #2e8b57 !important; font-style: italic; opacity: 0.95; }
    .vs-dark .rad-cpu-inline, .hc-black .rad-cpu-inline { color: #7fd17f !important; }
  `;
  document.head.appendChild(css);
  const cv = document.createElement('canvas');
  cv.className = 'rad-cpu-arrows';
  cv.style.position = 'absolute'; cv.style.top = '0px'; cv.style.pointerEvents = 'none'; cv.style.zIndex = 6;
  ed.getDomNode().appendChild(cv);
  const COLORS = { jmp: '#8a8a8a', jcc: '#d08000', loop: '#2a9d8f', call: '#4a7fd0' };
  let lanesWanted = -1;
  function draw() {
    const li = ed.getLayoutInfo();
    const lanes = st.arrows.reduce((m, a) => Math.max(m, a.lane + 1), 0);
    const want = Math.min(8, lanes) * 5 + 10;
    if (want !== lanesWanted) { lanesWanted = want; ed.updateOptions({ lineDecorationsWidth: want }); setTimeout(draw, 0); return; }
    const w = li.decorationsWidth, h = li.height, dpr = window.devicePixelRatio || 1;
    cv.style.left = li.decorationsLeft + 'px';
    cv.style.width = w + 'px'; cv.style.height = h + 'px';
    cv.width = Math.max(1, Math.round(w * dpr)); cv.height = Math.max(1, Math.round(h * dpr));
    const c = cv.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    const lh = ed.getOption(monaco.editor.EditorOption.lineHeight);
    const top = ed.getScrollTop();
    const n = ed.getModel().getLineCount();
    const yOf = l => ed.getTopForLineNumber(Math.min(n, l + 1)) - top + lh / 2;
    const right = Math.min(w - 2, want - 2);
    st.arrows.forEach(a => {
      const x = Math.max(2, right - 4 - a.lane * 5);
      const y1 = yOf(a.src), y2 = yOf(a.dst);
      if ((y1 < -lh && y2 < -lh) || (y1 > h + lh && y2 > h + lh)) return;
      let color = COLORS[a.kind] || '#888', dash = [];
      if (st.taken && st.taken.line === a.src) {
        color = st.taken.taken ? '#e02020' : '#9a9a9a';
        if (!st.taken.taken) dash = [3, 2];
      }
      c.strokeStyle = color; c.fillStyle = color; c.lineWidth = (st.taken && st.taken.line === a.src) ? 2 : 1.2;
      c.setLineDash(dash);
      c.beginPath(); c.moveTo(right, y1); c.lineTo(x, y1); c.lineTo(x, y2); c.lineTo(right - 3, y2); c.stroke();
      c.setLineDash([]);
      c.beginPath(); c.moveTo(right, y2); c.lineTo(right - 4, y2 - 3); c.lineTo(right - 4, y2 + 3); c.closePath(); c.fill();
    });
    st.drawn = (st.drawn || 0) + 1;
  }
  st.draw = draw;
  ed.onDidScrollChange(draw);
  ed.onDidLayoutChange(draw);
  ed.onDidChangeModelContent(() => setTimeout(draw, 0));

  function highlight() {
    const p = ed.getPosition();
    if (!p) return;
    const line = p.lineNumber - 1, col = p.column - 1;
    const hit = st.refs.find(r => r[0] === line && r[1] <= col && col <= r[2]);
    if (!hit) { st.hi = ed.deltaDecorations(st.hi, []); st.fam = ''; return; }
    const fam = hit[3];
    let lo = 0, hi = 1 << 30;
    st.procs.forEach(pr => { if (pr[0] <= line && line <= pr[1] && pr[1] - pr[0] < hi - lo) { lo = pr[0]; hi = pr[1]; } });
    const list = st.refs.filter(r => r[3] === fam && r[0] >= lo && r[0] <= hi).map(r => ({
      range: new monaco.Range(r[0] + 1, r[1] + 1, r[0] + 1, r[2] + 1),
      options: { inlineClassName: 'rad-reg-' + r[4],
                 overviewRuler: { color: r[4] === 'r' ? 'rgba(70,140,255,0.8)' : 'rgba(255,140,0,0.9)', position: 4 },
                 hoverMessage: { value: (r[4] === 'r' ? 'read' : r[4] === 'w' ? 'written' : 'read + written') } } }));
    st.hi = ed.deltaDecorations(st.hi, list);
    st.fam = fam; st.hiCount = list.length;
  }
  st.highlight = highlight;
  ed.onDidChangeCursorPosition(highlight);

  function inline() {
    const m = ed.getModel();
    const n = m.getLineCount();
    const list = Object.keys(st.inline).map(k => +k).filter(l => l >= 0 && l < n).map(l => {
      const col = m.getLineMaxColumn(l + 1);
      return { range: new monaco.Range(l + 1, col, l + 1, col),
               options: { after: { content: '    ; ' + st.inline[l], inlineClassName: 'rad-cpu-inline' },
                          showIfCollapsed: true } };
    });
    st.inl = ed.deltaDecorations(st.inl, list);
  }

  window.radCpuSetStatic = function (arrows, refs, procs) {
    st.arrows = arrows || []; st.refs = refs || []; st.procs = procs || [];
    draw(); highlight();
  };
  window.radCpuSetInline = function (map) { st.inline = map || {}; inline(); };
  window.radCpuSetRegs = function (regs) { st.regs = regs || {}; };
  window.radCpuSetTaken = function (t) { st.taken = t; draw(); };

  const lang = ed.getModel().getLanguageId();
  monaco.languages.registerHoverProvider(lang, {
    provideHover: function (model, pos) {
      if (model !== ed.getModel()) return null;
      const w = model.getWordAtPosition(pos);
      if (!w) return null;
      const r = st.regs[w.word.toLowerCase().replace(/^%/, '')];
      if (!r) return null;
      return { range: new monaco.Range(pos.lineNumber, w.startColumn, pos.lineNumber, w.endColumn),
               contents: [{ value: r.md }] };
    } });
  setTimeout(draw, 50);
})();"""


def is_asm_editor(ed) -> bool:
    return bool(getattr(getattr(ed, "plugin", None), "asm_intel", False))


def dialect_of(ed) -> str:
    plugin = getattr(ed, "plugin", None)
    dia = getattr(plugin, "asm_dialect", "") or ""
    if dia:
        return dia
    try:
        from ..index import detect_dialect
        return detect_dialect(getattr(ed, "path", None), ed.text(), plugin)
    except Exception:  # noqa: BLE001
        return "nasm"


def _state(ed) -> dict:
    st = getattr(ed, "_radcpu", None)
    if st is None:
        st = {"arrows": [], "refs": [], "procs": [], "inline": {}, "regs": {}, "taken": None}
        try:
            ed._radcpu = st
        except Exception:  # noqa: BLE001
            pass
    return st


def inject(ed) -> None:
    ed._js(JS)


def static_data(text: str, dialect: str) -> tuple[list, list, list]:
    jumps = A.source_jumps(text, dialect)
    arrows = [{"src": j.src, "dst": j.dst, "kind": j.kind, "lane": lane, "label": j.label}
              for j, lane in A.arrow_lanes(jumps)]
    refs = [[r.line, r.col, r.end, r.family, r.kind] for r in A.register_refs(text, dialect)]
    procs = [[a, b] for a, b, _n in A.proc_ranges(text, dialect)]
    return arrows, refs, procs


def push_static(ed) -> None:
    if not is_asm_editor(ed):
        return
    try:
        arrows, refs, procs = static_data(ed.text(), dialect_of(ed))
    except Exception as e:  # noqa: BLE001 - analysis must never break the editor
        print(f"[cpu view] source analysis failed: {e}")
        return
    st = _state(ed)
    st.update(arrows=arrows, refs=refs, procs=procs)
    ed._js(f"window.radCpuSetStatic && radCpuSetStatic({json.dumps(arrows)}, {json.dumps(refs)}, "
           f"{json.dumps(procs)});")


def set_inline(ed, mapping: dict[int, str]) -> None:
    st = _state(ed)
    st["inline"] = {int(k): v for k, v in mapping.items() if v}
    ed._js(f"window.radCpuSetInline && radCpuSetInline({json.dumps({str(k): v for k, v in st['inline'].items()})});")


def register_hover_data(fam: dict[str, int], prev_fam: dict[str, int] | None, bits: int, lang: str = "en") -> dict:
    """{'eax': {'md': markdown, 'hex': ...}} for every register name whose family has a value."""
    from .. import isa
    from .texts import T
    out = {}
    for name, reg in isa.REGISTERS.items():
        if reg.family not in fam or reg.size > 64 or name in ("st",):
            continue
        if bits == 16 and reg.size > 16:
            continue
        v = A.sub_value(name, fam)
        if v is None:
            continue
        f = A.value_formats(v, reg.size)
        md = (f"**{name.upper()}** = `{f['hex']}`  \n{T('hover_dec')}: `{f['dec']}` · {T('hover_signed')}: "
              f"`{f['signed']}` · {T('hover_char')}: `{f['char']}`")
        if prev_fam is not None and reg.family in prev_fam:
            old = A.sub_value(name, prev_fam)
            if old is not None and old != v:
                md += f"  \n⚠ {T('hover_changed', old=A.fmt_hex(old))}"
        out[name] = {"md": md, **f}
    return out


def set_registers(ed, data: dict) -> None:
    st = _state(ed)
    st["regs"] = data
    ed._js(f"window.radCpuSetRegs && radCpuSetRegs({json.dumps(data)});")


def set_taken(ed, line: int | None, taken: bool | None) -> None:
    st = _state(ed)
    st["taken"] = None if line is None or taken is None else {"line": int(line), "taken": bool(taken)}
    ed._js(f"window.radCpuSetTaken && radCpuSetTaken({json.dumps(st['taken'])});")


def clear_live(ed) -> None:
    try:
        set_inline(ed, {})
        set_registers(ed, {})
        set_taken(ed, None, None)
    except RuntimeError:          # the editor is closing
        pass


class LiveSession:
    """Inline values of one debug session: the line executed before each stop gets the values after it."""

    def __init__(self):
        self.prev: tuple | None = None            # (editor, line) of the previous stop
        self.prev_fam: dict[str, int] | None = None
        self.editors: set = set()

    def on_stop(self, ed, line: int, snap, lang: str = "en") -> None:
        """ed / line (0-based) of the new stop; snap: backend.Snapshot."""
        dialect = dialect_of(ed) if ed is not None else "nasm"
        if self.prev is not None:
            ped, pline = self.prev
            try:
                text = ped.text(pline)
                val = A.inline_values(text, dialect_of(ped), snap.fam, snap.flags)
                if val:
                    st = _state(ped)
                    mapping = dict(st.get("inline") or {})
                    mapping[pline] = val
                    set_inline(ped, mapping)
            except RuntimeError:
                pass
        if ed is not None:
            self.editors.add(ed)
            set_registers(ed, register_hover_data(snap.fam, self.prev_fam, snap.bits, lang))
            taken = None
            try:
                masked = A.mask(ed.text(line), dialect)[0]
                ins = A.instruction_of(masked, line)
                if ins is not None and (ins.mnemonic in A.JCC or ins.mnemonic in A.LOOPS):
                    taken = A.jump_taken(ins.mnemonic, snap.flags, snap.fam, snap.bits)
            except Exception:  # noqa: BLE001
                taken = None
            set_taken(ed, line, taken)
        self.prev = (ed, line) if ed is not None else None
        self.prev_fam = dict(snap.fam)

    def finish(self) -> None:
        for ed in list(self.editors):
            clear_live(ed)
        self.editors.clear()
        self.prev = None
        self.prev_fam = None
