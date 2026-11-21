"""Public entry points of the runtime checks: ``check`` (Check by running), ``explain_line`` and ``prepare``.

    res = check(text, path)                         # the whole program from its entry point
    res = check(text, path, proc_line=42)           # only the procedure that contains line 42
    res = check(text, path, lines=(10, 20))         # only the selected lines (a snippet)
    info = explain_line(text, path, 37)             # registers / flags before -> after for line 37

* 16-bit DOS sources (``abi_of`` = dos16, or radide/emu8086/detect) run in the IDE's 8086 emulator
  (radide/asm_sim/emu16.py).
* NASM sources for Windows x64 / x86 and Linux x86-64 / i386 are assembled with NASM into an object file,
  linked in memory (radide/asm_sim/objload.py) and run in Unicorn (radide/asm_sim/x86run.py). Other project
  modules that define a ``global`` the file declares ``extern`` are assembled and linked with it.
* MASM / FASM / GNU as sources get ``status = "unsupported"`` with an explanation (their programs still run in
  the native debugger).
* Without the ``unicorn`` package the 32 / 64-bit checks answer ``status = "unavailable"``
  (``install_unicorn()`` installs it from PyPI on request).
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import objload as L
from .model import SimResult

ENTRY_NAMES = ("main", "_main", "wmain", "WinMain", "_WinMain@16", "wWinMain", "start", "_start", "Start",
               "WinMainCRTStartup", "mainCRTStartup")


def unicorn_available() -> bool:
    try:
        from .x86run import available
        return available()
    except Exception:  # noqa: BLE001
        return False


def install_unicorn(log=print) -> bool:
    """pip install unicorn (official PyPI) into the IDE's own Python."""
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                            "--index-url", "https://pypi.org/simple", "unicorn>=2.0", "capstone>=5.0"],
                           capture_output=True, text=True, timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log((r.stdout or "")[-2000:] + (r.stderr or "")[-2000:])
        if r.returncode != 0:
            return False
        import importlib
        import radide.asm_sim.x86run as XR
        importlib.invalidate_caches()
        importlib.reload(XR)
        return XR.available()
    except Exception as e:  # noqa: BLE001
        log(f"pip failed: {e}")
        return False


def _dialect_abi(text: str, path) -> tuple[str, str]:
    try:
        from ..asm_intel.index import abi_of, detect_dialect
        dia = detect_dialect(path, text)
        abi = abi_of(text, dia, path)
    except Exception:  # noqa: BLE001
        dia, abi = "nasm", "win64"
    try:
        from ..emu8086.detect import is_dos16_source
        if abi != "dos16" and is_dos16_source(text):
            abi = "dos16"
    except Exception:  # noqa: BLE001
        pass
    return dia, abi


def _fmt_for(abi: str, text: str, dialect: str, path) -> str:
    if abi == "win64":
        return "win64"
    if abi == "sysv":
        return "elf64"
    try:
        from ..asm_intel.index import target_os
        if target_os(text, dialect, path) == "linux":
            return "elf32"
    except Exception:  # noqa: BLE001
        pass
    return "win32"


def _project_entry(path) -> str:
    try:
        from ..asm_intel.index import project_asm_settings
        return str(project_asm_settings(path).get("entry", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _extra_modules(text: str, path) -> list[Path]:
    """Other sources of the project that define a global this file declares extern."""
    if not path:
        return []
    wanted = set()
    for m in re.finditer(r"^\s*extern\s+([^;\n]+)", text, re.I | re.M):
        for n in m.group(1).split(","):
            n = n.strip().split(":")[0].strip()
            if n:
                wanted.add(n)
    if not wanted:
        return []
    try:
        from ..asm_intel.index import project_files
        files = project_files(path)
    except Exception:  # noqa: BLE001
        return []
    out = []
    me = Path(path).resolve()
    for f in files:
        try:
            if f.resolve() == me or f.suffix.lower() not in (".asm", ".nasm") or f.name.startswith("_rad"):
                continue
            t = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        defs = set()
        for m in re.finditer(r"^\s*global\s+([^;\n]+)", t, re.I | re.M):
            defs.update(x.strip().split(":")[0].strip() for x in m.group(1).split(","))
        if defs & wanted:
            out.append(f)
    return out[:20]


@dataclass
class Prepared:
    """An assembled + linked program (or the reason it could not be prepared)."""
    result: SimResult | None = None         # set when preparing failed
    img: L.Image | None = None
    abi: str = ""
    dialect: str = ""
    path: str = ""
    text: str = ""
    warnings: list = field(default_factory=list)


def prepare(text: str, path=None, download: bool = True, log=None) -> Prepared:
    path = str(path or "snippet.asm")
    dia, abi = _dialect_abi(text, path)
    p = Prepared(abi=abi, dialect=dia, path=path, text=text)
    if abi == "dos16":
        return p
    if dia != "nasm":
        from ..asm_intel.directives import DIALECT_NAMES
        name = DIALECT_NAMES.get(dia, dia)
        p.result = SimResult(status="unsupported", abi=abi,
                             note_en=f"Check by running supports NASM and 16-bit (8086) programs; this file is {name}. "
                                     "Use the debugger (F5) and the CPU windows for it.",
                             note_ar=f"الفحص بالتشغيل يدعم برامج NASM و 8086 (16 بت)؛ وهذا الملف بصيغة {name}. "
                                     "استخدم المصحح (F5) ونوافذ المعالج معه.")
        return p
    if not unicorn_available():
        p.result = SimResult(status="unavailable", abi=abi,
                             note_en="The checks of 32 / 64-bit programs need the Unicorn engine (pip package "
                                     "'unicorn'). Click 'Install Unicorn' in the Assembly Checks window.",
                             note_ar="فحص برامج 32 و 64 بت يحتاج محرك Unicorn (حزمة pip باسم unicorn). اضغط "
                                     "'تثبيت Unicorn' في نافذة فحوص الأسمبلي.")
        return p
    fmt = _fmt_for(abi, text, dia, path)
    out = L.assemble_nasm(text, path, fmt, download=download, log=log)
    if not out.ok:
        r = SimResult(status="asm_error", abi=abi)
        r.errors = [f"line {ln}: {msg}" if ln else msg for ln, msg in out.errors]
        if out.tool_missing:
            r.note_en, r.note_ar = "NASM is not installed (Tools > Assembly Toolchains...).", \
                "برنامج NASM غير مثبت (Tools > Assembly Toolchains...)."
        else:
            r.note_en = "Fix the assembler errors first: " + "; ".join(r.errors[:3])
            r.note_ar = "أصلح أخطاء التجميع أولاً: " + "; ".join(r.errors[:3])
        p.result = r
        return p
    objs = [out.obj]
    for f in _extra_modules(text, path):
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        o2 = L.assemble_nasm(t, str(f), fmt, download=False)
        if o2.ok:
            objs.append(o2.obj)
    try:
        p.img = L.link(objs)
    except L.LoadError as e:
        p.result = SimResult(status="error", abi=abi, note_en=str(e), note_ar=str(e))
        return p
    p.warnings = out.warnings
    return p


def _entry(p: Prepared, proc_line: int | None, lines: tuple | None):
    """(entry address, name, stop range) or (None, reason_en, reason_ar)."""
    img = p.img
    if lines:
        addrs = [a for l1 in range(lines[0], lines[1] + 1) for a in img.addresses_of(p.path, l1)]
        if not addrs:
            return None, "The selected lines contain no instructions.", "الأسطر المحددة لا تحتوي على تعليمات.", None
        rows = [r for r in img.line_rows if lines[0] <= r[3] <= lines[1] and r[2] == p.path]
        hi = max(a + n for a, n, _f, _l in rows)
        return min(addrs), f"lines {lines[0]}-{lines[1]}", "", (min(addrs), hi)
    if proc_line:
        addrs = []
        for ln in range(proc_line, proc_line + 400):
            addrs = img.addresses_of(p.path, ln)
            if addrs:
                break
        if not addrs:
            return None, "No instruction at or after this line.", "لا توجد تعليمة في هذا السطر أو بعده.", None
        lab = img.proc_of(min(addrs))
        if lab is None:
            return None, "This line is not inside a procedure.", "هذا السطر ليس داخل إجراء.", None
        return lab.addr, lab.name, "", None
    names = [n for n in (_project_entry(p.path),) if n] + list(ENTRY_NAMES)
    for n in names:
        if n in img.globals:
            return img.globals[n], n, "", None
        lab = img.label_named(n)
        if lab is not None and lab.code:
            return lab.addr, lab.name, "", None
    code = [lab for lab in img.labels if lab.code and "." not in lab.name.lstrip(".")]
    exported = [lab for lab in code if lab.is_global]
    if exported and not any(lab.name in ENTRY_NAMES for lab in code):
        names = ", ".join(lab.name for lab in exported[:5])
        return (None, f"This file has no main / start: it is a module of procedures ({names}). Put the cursor in "
                      "one of them and use 'Check This Procedure' (give its arguments in the Registers box).",
                f"هذا الملف بلا main أو start: إنه وحدة إجراءات ({names}). ضع المؤشر داخل أحدها واستخدم "
                "'افحص هذا الإجراء' (واكتب معاملاته في مربع المسجلات).", None)
    if code:
        return code[0].addr, code[0].name, "", None
    if img.line_rows:
        return img.line_rows[0][0], "start", "", None
    return None, "The program has no instructions.", "البرنامج لا يحتوي على تعليمات.", None


def check(text: str, path=None, stdin: str = "5\n", proc_line: int | None = None, lines: tuple | None = None,
          max_steps: int = 1_000_000, timeout: float = 15.0, download: bool = True, init_regs=None,
          log=None) -> SimResult:
    p = prepare(text, path, download=download, log=log)
    if p.abi == "dos16":
        from .emu16 import check16
        res, _tr = check16(text, p.path, stdin=stdin, max_steps=min(max_steps, 300_000),
                           start_line=lines[0] if lines else None, stop_lines=lines)
        return res
    if p.result is not None:
        return p.result
    return run_prepared(p, stdin, proc_line, lines, max_steps, timeout, init_regs)


def run_prepared(p: Prepared, stdin: str = "5\n", proc_line=None, lines=None, max_steps=1_000_000, timeout=15.0,
                 init_regs=None, trace_addrs=None):
    from .x86run import Runner
    entry, name, reason_ar, stop = _entry(p, proc_line, lines)
    if entry is None:
        return SimResult(status="error", abi=p.abi, note_en=name, note_ar=reason_ar)
    runner = Runner(p.img, p.abi, stdin=stdin, max_steps=max_steps, timeout=timeout, entry=entry, entry_name=name,
                    stop_outside=stop, trace_addrs=trace_addrs, init_regs=init_regs)
    res = runner.run()
    res.entry = name
    if trace_addrs is not None:
        res.traces = runner.traces                      # type: ignore[attr-defined]
        res.runner = runner                             # type: ignore[attr-defined]
    return res


# ============================================================================ explain
def explain_line(text: str, path, line: int, stdin: str = "5\n", iteration: int = -1, proc_line=None,
                 max_steps: int = 300_000, download: bool = True, init_regs=None) -> dict:
    """Run the program again recording line *line*; explain its execution number *iteration* (-1 = last).

    Returns {"ok", "status", "note_en/ar", "line", "count", "iteration", "steps": [explain dicts of the
    instructions of that line], "flags": flag_table of the state after}."""
    from . import explain as E
    p = prepare(text, path, download=download)
    src = text.splitlines()
    out = {"ok": False, "line": line, "count": 0, "iteration": 0, "steps": [], "status": "", "note_en": "",
           "note_ar": "", "source": src[line - 1].strip() if 0 < line <= len(src) else ""}
    if p.abi == "dos16":
        from .emu16 import check16
        res, traces = check16(text, p.path, stdin=stdin, max_steps=max_steps, trace_lines=[line])
        lst = traces.get(line, [])
        out["status"] = res.status
        if not lst:
            mn = E.split_instruction(_clean_source(out["source"]))[0]
            if not mn or mn in ("org", "db", "dw", "dd", "proc", "endp", "segment", "ends", "assume", "end", "equ"):
                out["note_en"] = "This line has no instruction to explain (a label, data or directive)."
                out["note_ar"] = "هذا السطر لا يحتوي على تعليمة لشرحها (عنوان أو بيانات أو توجيه)."
            else:
                out["note_en"], out["note_ar"] = _not_run(res)
                out["steps"].append(E.explain_step(_clean_source(out["source"]), None))
            return out
        t = lst[iteration] if -len(lst) <= iteration < len(lst) else lst[-1]
        out.update(ok=True, count=len(lst), iteration=t["iteration"])
        nxt = _next_source_instruction(src, line)
        info = E.explain_step(out["source"], t["before"], t["after"], [(a, n, o, v) for a, n, o, v in t["writes"]],
                              bits=16, next_ins=nxt)
        out["steps"].append(info)
        out["flags"] = E.flag_table((t["after"] or t["before"]).get("eflags", 0))
        return out
    if p.result is not None:
        out["status"] = p.result.status
        out["note_en"], out["note_ar"] = p.result.note_en, p.result.note_ar
        return out
    addrs = p.img.addresses_of(p.path, line)
    if not addrs:
        out["note_en"] = "This line has no instruction to explain (a label, data or directive)."
        out["note_ar"] = "هذا السطر لا يحتوي على تعليمة لشرحها (عنوان أو بيانات أو توجيه)."
        mn = E.split_instruction(out["source"])[0]
        if mn:
            info = E.explain_step(out["source"], None)
            out["steps"].append(info)
        return out
    res = run_prepared(p, stdin, proc_line, None, max_steps, 10.0, trace_addrs=addrs, init_regs=init_regs)
    if res.status == "error" and proc_line is None:            # a module without main: run the line's procedure
        res = run_prepared(p, stdin, line, None, max_steps, 10.0, trace_addrs=addrs, init_regs=init_regs)
    traces = getattr(res, "traces", {})
    runner = getattr(res, "runner", None)
    out["status"] = res.status
    first = traces.get(min(addrs), [])
    if not first:
        out["note_en"], out["note_ar"] = _not_run(res)
        info = E.explain_step(out["source"], None)
        out["steps"].append(info)
        return out
    idx = iteration if -len(first) <= iteration < len(first) else -1
    out.update(ok=True, count=len(first), iteration=first[idx].iteration)
    bits = p.img.bits
    rows = sorted(a for a in addrs)
    nxt_src = ""
    for a in rows:
        lst = traces.get(a, [])
        if not lst:
            continue
        t = lst[idx] if -len(lst) <= idx < len(lst) else lst[-1]
        ins = runner._decode(a) if runner is not None else None
        text_ins = f"{ins.mnemonic} {ins.op_str}".strip() if ins is not None else out["source"]
        if len(rows) == 1:
            text_ins = _clean_source(out["source"]) or text_ins
            nxt_src = _next_source_instruction(src, line)
        nxt = ""
        if ins is not None and runner is not None:
            n2 = runner._decode(a + ins.size)
            nxt = f"{n2.mnemonic} {n2.op_str}" if n2 is not None else ""
        if len(rows) == 1 and nxt_src:
            nxt = nxt_src
        info = E.explain_step(text_ins, t.before, t.after, t.writes, t.reads, bits=bits, next_ins=nxt,
                              describe_addr=p.img.describe)
        out["steps"].append(info)
    last = traces.get(rows[-1], [])
    if last:
        t = last[idx] if -len(last) <= idx < len(last) else last[-1]
        out["flags"] = E.flag_table((t.after or t.before).get("eflags", 0))
    return out


def _clean_source(s: str) -> str:
    s = s.split(";", 1)[0].strip()
    s = re.sub(r"^[A-Za-z_.?$@][\w.?$@]*:\s*", "", s)
    return s


def _next_source_instruction(src: list[str], line: int) -> str:
    for k in range(line, min(len(src), line + 6)):
        s = _clean_source(src[k])
        if s and not s.endswith(":"):
            return s
    return ""


def _not_run(res: SimResult) -> tuple[str, str]:
    if res.status in ("asm_error", "unavailable", "unsupported", "error"):
        return res.note_en, res.note_ar
    return ("This line was not executed in the run (the program did not reach it: "
            + res.summary("en") + ").",
            "هذا السطر لم يُنفَّذ في التشغيل (لم يصل إليه البرنامج: " + res.summary("ar") + ").")
