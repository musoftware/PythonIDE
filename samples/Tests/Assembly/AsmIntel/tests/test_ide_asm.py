"""IDE test of the assembly editor intelligence: opens .asm / .S files in the real IDE (offscreen, QSettings
organization RADIDE-TEST, cleared afterwards) and checks the Monaco grammar, completions, hover, signature help,
outline, document symbols and Ctrl+click definition.

Run:  python samples/Tests/Assembly/AsmIntel/tests/test_ide_asm.py
Screenshots (widget.grab() of the editor only) go to %TEMP%/radide-asm-intel/.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
ROOT = SAMPLE.parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(tempfile.gettempdir()) / "radide-asm-intel"
OUT.mkdir(parents=True, exist_ok=True)

import PyQt6.QtWebEngineWidgets  # noqa: E402,F401 - must be imported before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-asm-intel")
app = QApplication(sys.argv[:1])
QSettings().clear()

from radide.app import MainWindow  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def pump(sec: float = 0.5) -> None:
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.02)


def wait(cond, timeout: float = 20.0) -> bool:
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.05)
    return False


def js(ed, expr: str, timeout: float = 10.0):
    box = {}
    ed.page().runJavaScript(f"(function(){{try{{return {expr};}}catch(e){{return 'ERR:'+e;}}}})()",
                            lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def js_async(ed, code: str, timeout: float = 10.0):
    """Run *code* that sets window.__radTestOut, then read it."""
    js(ed, "(window.__radTestOut = undefined, 1)")
    ed.page().runJavaScript(code)
    v = None
    if wait(lambda: js(ed, "window.__radTestOut === undefined ? null : JSON.stringify(window.__radTestOut)", 2)
            is not None, timeout):
        v = json.loads(js(ed, "JSON.stringify(window.__radTestOut)"))
    return v


def capture(ed, fn_name: str, *args):
    """Call ed._complete / ed._signature / ed._hover and return what is sent to radResolve."""
    sent = []
    orig = ed._js
    ed._js = lambda code: sent.append(code)
    try:
        getattr(ed, fn_name)(*args)
    finally:
        ed._js = orig
    for code in sent:
        if code.startswith("radResolve("):
            payload = code[len("radResolve("):].split(",", 1)[1].rsplit(");", 1)[0]
            return json.loads(payload)
    return None


killer = QTimer()
killer.timeout.connect(lambda: QApplication.activeModalWidget() and QApplication.activeModalWidget().close())
killer.start(300)

w = MainWindow()
w.resize(1400, 900)
w.show()
pump(4)

try:
    from radide.monaco_editor import MonacoEditor
    from radide.languages import get_plugin

    # -------------------------------------------------------------- 1. NASM file through File > Open
    nasm = SAMPLE / "nasm" / "main.asm"
    ed = w.open_any_file(nasm)
    check("open main.asm gives a Monaco editor", isinstance(ed, MonacoEditor), repr(ed))
    wait(lambda: ed._ready, 30)
    pump(1.5)
    check("plugin is assembly-aware", getattr(ed.plugin, "asm_intel", False), repr(ed.plugin))
    check("language id rad-asm-nasm", ed.language_id() == "rad-asm-nasm", ed.language_id())
    check("Monaco model uses the Monarch grammar",
          js(ed, "radEditor.getModel().getLanguageId()") == "rad-asm-nasm",
          str(js(ed, "radEditor.getModel().getLanguageId()")))
    toks = js(ed, "JSON.stringify(monaco.editor.tokenize('    mov rax, [msg] ; hi', 'rad-asm-nasm')[0]"
                  ".map(t => t.type))")
    toks = json.loads(toks) if isinstance(toks, str) and toks.startswith("[") else []
    check("tokens: instruction / register / comment",
          any("keyword" in t for t in toks) and any("variable.predefined" in t for t in toks)
          and any("comment" in t for t in toks), str(toks))
    raw = js(ed, "JSON.stringify(['bits 64', 'section .data', 'extern ExitProcess', '    resd 1'].map(l => "
                 "monaco.editor.tokenize(l, 'rad-asm-nasm')[0].map(t => t.type)))")
    dt = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
    check("directives at column 0 are highlighted", len(dt) == 4 and all("type" in (t[0] if t[0] else t[1])
                                                                          for t in dt), str(dt))
    color = js(ed, "(() => { const s = [...document.querySelectorAll('.view-line span span')]"
                   ".find(e => e.textContent === 'bits'); return s ? getComputedStyle(s).color : ''; })()")
    check("rendered colour of a directive differs from plain text", color not in ("", "rgb(0, 0, 0)"), str(color))
    lines = ed.text().split("\n")
    ln = lines.index("    call    show_message")
    items = capture(ed, "_complete", 1, ln, 4) or []
    labels = {i["label"] for i in items}
    check("completions at mnemonic position (instructions, macros, snippets)",
          {"mov", "SQUARE", "call64"} <= labels, str(sorted(labels)[:20]))
    check("snippet items carry insertText + snippet flag",
          any(i.get("snippet") and i.get("insertText") for i in items if i["label"] == "call64"))
    items = capture(ed, "_complete", 2, ln, len("    call    ")) or []
    labels = {i["label"] for i in items}
    check("completions after call: labels + Win32 API", {"show_message", "MessageBoxA", "CreateFileA"} <= labels)
    cf = next((i for i in items if i["label"] == "CreateFileA"), {})
    check("API completion adds 'extern' automatically", bool(cf.get("additionalTextEdits")), json.dumps(cf)[:200])
    hl = lines.index("    call    MessageBoxA")
    hov = capture(ed, "_hover", 3, "MessageBoxA", 0, 0, hl, 12) or ""
    check("hover on MessageBoxA shows signature + Win64 registers", "rcx" in hov and "MessageBoxA(" in hov, hov[:200])
    hov = capture(ed, "_hover", 4, "lea", 0, 0, lines.index("    lea     rdx, [line]"), 5) or ""
    check("hover on LEA shows the instruction doc", "**LEA**" in hov, hov[:120])
    sl = lines.index("    lea     r8, [title]")
    sig = capture(ed, "_signature", 5, sl, len("    lea     r8, ")) or {}
    check("signature help for the register set-up of MessageBoxA",
          isinstance(sig, dict) and sig.get("label", "").startswith("MessageBoxA(") and sig.get("activeParameter") == 2,
          str(sig)[:200])
    # Monaco's document symbols (breadcrumbs / Ctrl+Shift+O) through the radAsm channel object
    syms = js_async(ed, "radChannel.objects.radAsm.symbols(r => { window.__radTestOut = JSON.parse(r); });")
    names = [s["name"] for s in (syms or [])]
    check("radAsm.symbols returns sections", ".text" in names and ".data" in names, str(names))
    jl = lines.index("    jl      .loop")
    d = js_async(ed, f"radChannel.objects.radAsm.definition({jl}, 13, r => {{ window.__radTestOut = r; }});")
    check("Ctrl+click definition of .loop (same file)", d == lines.index(".loop:"), str(d))
    # every dialect's grammar compiles and tokenizes (registered in this page from the Python spec)
    from radide.asm_intel.monarch import language_spec
    samples = {"masm": "    mov eax, offset szText ; c", "fasm": "  .next: mov [shown], eax ; c",
               "gas": "    movq $60, %rax   # c"}
    for dia, line in samples.items():
        spec = language_spec(dia, dia == "gas")
        js(ed, f"(radRegisterMonarch({json.dumps(spec)}), 1)")
        raw = js(ed, f"JSON.stringify(monaco.editor.tokenize({json.dumps(line)}, '{spec['id']}')[0].map(t => t.type))")
        tt = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
        check(f"{dia} grammar tokenizes", any("keyword" in t for t in tt) and any("comment" in t for t in tt) and
              (dia != "gas" or any("variable.predefined" in t for t in tt)), str(tt))
    # Document Outline dock follows the editor
    w.tabs.setCurrentWidget(ed.parent() if w.tabs.indexOf(ed.parent()) >= 0 else w.tabs.currentWidget())
    pump(1.2)
    co = getattr(w, "code_outline", None)
    if co is not None and callable(getattr(w, "refresh_code_outline", None)):
        w.refresh_code_outline()
        pump(0.5)
        tops = [co.topLevelItem(i).text(0) for i in range(co.topLevelItemCount())]
        check("Document Outline shows the sections", any(".text" in t for t in tops), str(tops))
    pump(1.0)
    ed.grab().save(str(OUT / "nasm_editor.png"))

    # -------------------------------------------------------------- 2. GAS file in a non-assembly plugin (overlay)
    gas = SAMPLE / "gas" / "hello_win.S"
    ed2 = MonacoEditor(get_plugin("python-tk"), gas)
    ed2.resize(900, 600)
    ed2.setText(gas.read_text(encoding="utf-8"))
    ed2.show()
    wait(lambda: ed2._ready, 30)
    pump(1.5)
    check("overlay wraps the python plugin for a .S file", getattr(ed2.plugin, "asm_intel", False) and
          ed2.plugin.id == "python-tk", repr(ed2.plugin))
    check("GAS language id", ed2.language_id() == "rad-asm-gas", ed2.language_id())
    gl = ed2.text().split("\n")
    pl = gl.index("    call    printf")
    hov = capture(ed2, "_hover", 6, "printf", 0, 0, pl, 12) or ""
    check("hover on printf (CRT, Win64)", "printf" in hov and "Microsoft x64" in hov, hov[:160])
    items = capture(ed2, "_complete", 7, pl, 4) or []
    check("GAS completions include directives", any(i["label"] == ".globl" for i in items))
    ed2.grab().save(str(OUT / "gas_overlay_editor.png"))
    ed2.close()
finally:
    w.close()
    pump(1)
    QSettings().clear()
    QSettings().sync()

failed = [r for r in RESULTS if not r[1]]
print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed; screenshots in {OUT}")
os._exit(1 if failed else 0)
