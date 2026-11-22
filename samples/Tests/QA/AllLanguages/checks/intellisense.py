"""Check family "intellisense": the code editor of a form's event handler (or the startup file of a language
without forms), in the real IDE.

  completion    the plugin's completions AND the editor's pipeline (MonacoEditor._complete = language server +
                plugin fallback/merge) contain the language's message-box helper, and typing "M" in the handler
                body shows Monaco's suggest widget with it (the "Rust: M shows nothing" report)
  hover         hover text for the helper word (language server or plugin)
  signature     signature help / calltip inside the helper's parentheses
  definition    go to definition of the helper (language server or plugin); SKIP when neither offers it
  diagnostics   a deliberate error appears in the Error List (tools.run_checks + language-server providers) or
                as a Monaco error marker; SKIP when the language has no checker and no server
  formatting    Format Document (radide/features/formatting.py) when a formatter is available, else SKIP
"""
from __future__ import annotations

import json
import re
import traceback

# language -> (helper call line, helper word) placed in the Click handler body
SAMPLE = {
    "vb-basic": ('MsgBox("hi")', "MsgBox"),
    "python-tk": ('print("hi")', "print"), "python-qt": ('print("hi")', "print"),
    "ring-qt": ('Form1_Load()', "Form1_Load"),
    "c-bridge": ('rad_msgbox("hi");', "rad_msgbox"), "cpp-bridge": ('rad::msgbox("hi");', "msgbox"),
    "csharp-bridge": ('MsgBox("hi");', "MsgBox"), "powershell-bridge": ('MsgBox("hi")', "MsgBox"),
    "java-bridge": ('msgbox("hi");', "msgbox"), "javascript": ('msgbox("hi");', "msgbox"),
    "typescript": ('msgbox("hi");', "msgbox"), "php": ("rad_msgbox('hi');", "rad_msgbox"),
    "rust-bridge": ('msgbox("hi");', "msgbox"), "go-bridge": ('MsgBox("hi")', "MsgBox"),
    "fortran-bridge": ('call rad_msgbox("hi")', "rad_msgbox"), "lua-bridge": ('rad.msgbox("hi")', "msgbox"),
    "ruby-bridge": ('Rad.msgbox("hi")', "msgbox"), "perl-bridge": ('rad_msgbox("hi");', "rad_msgbox"),
    "dart-bridge": ("Rad.msgbox('hi');", "msgbox"),
}
# a line that is an error in the language (diagnostics)
BROKEN = {"vb-basic": "If Then Then", "python-tk": "def (:", "python-qt": "def (:", "ring-qt": "if x = = 1 {",
          "c-bridge": "int x = ;", "cpp-bridge": "int x = ;", "csharp-bridge": "int x = ;",
          "java-bridge": "int x = ;", "javascript": "let x = ;", "typescript": "let x: number = ;",
          "php": "$x = ;", "rust-bridge": "let x = ;", "go-bridge": "x := ", "fortran-bridge": "x = = 1",
          "lua-bridge": "local x = = 1", "ruby-bridge": "def (", "perl-bridge": "my $x = ;",
          "dart-bridge": "var x = ;", "powershell-bridge": "$x = (", }
HELPER_RX = re.compile(r"msgbox|messagebox|^print$|^see$|^puts$|^echo$", re.I)


def _labels(items) -> list[str]:
    out = []
    for i in items or []:
        lab = i.get("label") if isinstance(i, dict) else getattr(i, "name", str(i))
        if isinstance(lab, dict):
            lab = lab.get("label", "")
        out.append(str(lab))
    return out


def _has(labels, word) -> bool:
    w = word.lower()
    return any(lab.lower().split("(")[0].split("!")[0].strip() in (w, w.split("::")[-1]) or
               lab.lower().startswith(w) for lab in labels)


def run(h, r, pl, project, folder) -> None:
    sub = r.sub
    w = h.w
    key = "intellisense."
    if pl.id not in SAMPLE:
        return generic(h, r, pl, project, folder)
    try:
        from .ide import editor_for_form
        ed, hline, handler = editor_for_form(h)
    except Exception as e:  # noqa: BLE001
        sub[key + "editor"] = f"FAIL: cannot open the handler in the code editor: {e}"
        r.note(traceback.format_exc())
        return
    if hline < 0:
        sub[key + "editor"] = "FAIL: double-click did not create/find the Click handler"
        return
    monaco = type(ed).__name__ == "MonacoEditor"
    text = ed.text()
    lines = text.split("\n")
    body = hline + 1
    while body < len(lines) and lines[body].strip().startswith(("{",)) and pl.id not in ("python-tk", "python-qt"):
        body += 1
    indent = re.match(r"\s*", lines[body] if body < len(lines) else "").group() or "    "
    call, word = SAMPLE[pl.id]
    # ---- 1. completion: type "M" on an empty line of the handler body
    lines.insert(body, indent + "M")
    new = "\n".join(lines)
    ed.setText(new)
    h.pump(0.5)
    col = len(indent) + 1
    try:
        plug = _labels(pl.completions(new, body, col, folder / pl.code_file("Form1"), getattr(ed, "names", None)))
        target = (next((x for x in plug if re.search("msgbox|messagebox", x, re.I)), "") or
                  next((x for x in plug if HELPER_RX.search(x)), "") or
                  next((x for x in plug if x.lower().startswith("m") and len(x) > 2), ""))
        sub[key + "plugin_completion"] = (f"PASS - {len(plug)} items, helper '{target}'" if target else
                                          f"FAIL: plugin.completions after 'M' has no usable item ({len(plug)} items: {plug[:8]})")
        if monaco:
            res = h.capture(ed, "_complete", 9001, body, col) or []
            labs = _labels(res)
            lsp = getattr(ed, "lsp", None)
            ok = target and _has(labs, target.split("(")[0])
            sub[key + "editor_completion"] = (
                f"PASS - {len(labs)} items incl. '{target}' (server: {'yes' if lsp is not None else 'no'})" if ok
                else f"FAIL: editor completion ({len(labs)} items, server {'attached' if lsp else 'none'}) lacks "
                     f"'{target}': {labs[:12]}")
            # the user-level test: Monaco's own suggest widget after typing "M"
            h.js(ed, f"(radEditor.setPosition({{lineNumber: {body + 1}, column: {col}}}), radEditor.focus(), 1)")
            h.js(ed, "(radEditor.getModel().pushEditOperations([], [{range: new monaco.Range("
                     f"{body + 1}, {col - 1}, {body + 1}, {col}), text: ''}}], () => null), 1)")
            h.js(ed, f"(radEditor.setPosition({{lineNumber: {body + 1}, column: {col - 1}}}), 1)")
            h.js(ed, "(radEditor.trigger('keyboard', 'type', {text: 'M'}), 1)")
            rows = []
            for _ in range(40):
                h.pump(0.4)
                raw = h.js(ed, "JSON.stringify([...document.querySelectorAll('.suggest-widget.visible "
                               ".monaco-list-row')].map(e => e.getAttribute('aria-label') || e.textContent))")
                rows = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
                if rows:
                    break
            want = (target or word).split("(")[0]
            typed = "M"
            if rows and not _has(rows, want) and len(want) > 2:
                # a long list (language server): the helper is further down - type more of it, like a user would
                more = want[1:3]
                h.js(ed, f"(radEditor.trigger('keyboard', 'type', {{text: {json.dumps(more)}}}), 1)")
                typed += more
                for _ in range(25):
                    h.pump(0.4)
                    raw = h.js(ed, "JSON.stringify([...document.querySelectorAll('.suggest-widget.visible "
                                   ".monaco-list-row')].map(e => e.getAttribute('aria-label') || e.textContent))")
                    rows = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
                    if _has(rows, want):
                        break
            sub[key + "typing_M"] = (f"PASS - typed {typed!r}: {rows[:6]}" if _has(rows, want) else
                                     f"FAIL: typing {typed!r} in {handler} shows {rows[:10] or 'no suggestions'}")
            h.js(ed, "(radEditor.trigger('keyboard', 'hideSuggestWidget', {}), 1)")
        else:
            sub[key + "editor_completion"] = f"SKIP: classic editor ({type(ed).__name__})"
    except Exception as e:  # noqa: BLE001
        sub[key + "completion"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
    # ---- 2. hover / signature / definition on a helper call
    lines = text.split("\n")
    lines.insert(body, indent + call)
    new = "\n".join(lines)
    ed.setText(new)
    h.pump(0.5)
    wcol = len(indent) + call.index(word.split("::")[-1]) + 1
    path = folder / pl.code_file("Form1")
    try:
        hov = ""
        if monaco:
            hov = h.capture(ed, "_hover", 9002, word, 0, 0, body, wcol) or ""
        if not hov:
            try:
                hov = pl.hover(new, body, wcol, path, getattr(ed, "names", None)) or ""
            except Exception:  # noqa: BLE001
                hov = ""
        offered = getattr(ed, "lsp", None) is not None or type(pl).hover is not type(pl).__mro__[-2].hover
        sub[key + "hover"] = (f"PASS - {str(hov)[:80]!r}" if hov else f"FAIL: no hover text for {word}" if offered
                              else "SKIP: no language server and the plugin offers no hover")
    except Exception as e:  # noqa: BLE001
        sub[key + "hover"] = f"FAIL: {type(e).__name__}: {e}"
    try:
        if "(" in call:
            scol = len(indent) + call.index("(") + 2
            sig = h.capture(ed, "_signature", 9003, body, scol) if monaco else \
                pl.calltip(new, body, scol, path, getattr(ed, "names", None))
            sub[key + "signature"] = f"PASS - {str(sig)[:80]!r}" if sig else \
                f"FAIL: no signature help inside {word}("
        else:
            sub[key + "signature"] = "SKIP: the helper is called without parentheses"
    except Exception as e:  # noqa: BLE001
        sub[key + "signature"] = f"FAIL: {type(e).__name__}: {e}"
    try:
        loc = None
        lsp = getattr(ed, "lsp", None)
        if lsp is not None and callable(getattr(lsp, "definition", None)) and lsp.running():
            box = {}
            lsp.did_change(path, new)
            lsp.definition(path, body, wcol, lambda res: box.setdefault("v", res))
            h.wait(lambda: "v" in box, 25)
            loc = box.get("v")
        if not loc:
            try:
                loc = pl.definition(new, body, wcol, path, getattr(ed, "names", None))
            except Exception:  # noqa: BLE001
                loc = None
        missing_client = [t for t in (pl.client_files() if callable(getattr(pl, "client_files", None)) else {})
                          if not (folder / t).exists()]
        if loc:
            sub[key + "definition"] = f"PASS - {str(loc)[:100]}"
        elif missing_client:
            sub[key + "definition"] = (f"SKIP: the helper library ({', '.join(missing_client[:2])}) is copied into "
                                       "the project on the first run; nothing to jump to before")
        elif lsp is None and type(pl).definition is type(pl).__mro__[-2].definition:
            sub[key + "definition"] = "SKIP: no language server and the plugin has no go-to-definition"
        else:
            sub[key + "definition"] = f"FAIL: no definition for {word}" + ("" if lsp else " (no language server)")
    except Exception as e:  # noqa: BLE001
        sub[key + "definition"] = f"FAIL: {type(e).__name__}: {e}"
    # ---- 3. diagnostics: a deliberate error
    try:
        from radide.tools import run_checks
        lines = text.split("\n")
        lines.insert(body, indent + BROKEN.get(pl.id, "@@@ ;;"))
        bad = "\n".join(lines)
        ed.setText(bad)
        lsp = getattr(ed, "lsp", None)
        if lsp is not None:
            lsp.did_change(path, bad)
        got = ""
        for _ in range(30):
            h.pump(1.0)
            diags = run_checks(w) or []
            errs = [d for d in diags if d.severity == "Error"]
            marks = h.js(ed, "monaco.editor.getModelMarkers({resource: radEditor.getModel().uri})"
                             ".filter(m => m.severity >= 8).length") if monaco else 0
            if errs:
                got = f"Error List: {errs[0].message[:80]} (line {errs[0].line})"
                break
            if isinstance(marks, int) and marks > 0:
                got = f"{marks} Monaco error marker(s) (language server)"
                break
            if lsp is None and _ >= 3:
                break
        if got:
            sub[key + "diagnostics"] = "PASS - " + got
        elif lsp is None:
            sub[key + "diagnostics"] = "SKIP: no checker for this language in the Error List and no language server"
        else:
            sub[key + "diagnostics"] = "FAIL: the deliberate error was not reported (Error List / markers)"
    except Exception as e:  # noqa: BLE001
        sub[key + "diagnostics"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
    # ---- 4. formatting
    try:
        ed.setText(text)
        h.pump(0.3)
        from radide.features import formatting as F
        fid = F.resolve_formatter(w, ed)
        if not fid or fid == "none":
            sub[key + "formatting"] = "SKIP: no formatter offered for this language"
        else:
            ok, msg = F.format_sync(w, ed)
            sub[key + "formatting"] = f"PASS - {fid}" if ok else f"FAIL: {fid}: {str(msg)[:200]}"
    except Exception as e:  # noqa: BLE001
        sub[key + "formatting"] = f"FAIL: {type(e).__name__}: {e}"
    ed.setText(text)
    try:
        w.save_all()
    except Exception:  # noqa: BLE001
        pass


def main_file(project, pl, folder):
    """The code file a language without forms opens first: its startup file or first module of its language."""
    cands = []
    try:
        if project.startup:
            cands.append(folder / pl.code_file(project.startup))
    except Exception:  # noqa: BLE001
        pass
    sf = getattr(pl, "startup_file", None) or getattr(pl, "_startup_file", None)
    if callable(sf):
        try:
            cands.append(folder / sf(folder, project.startup or ""))
        except Exception:  # noqa: BLE001
            pass
    cands += [folder / m for m in project.modules]
    if pl.code_ext:
        cands += sorted(folder.rglob("*" + pl.code_ext))
    for c in cands:
        if c.is_file() and "node_modules" not in c.parts and ".venv" not in c.parts:
            return c
    return None


def generic(h, r, pl, project, folder) -> None:
    """Languages without a form: completion in their main file (plugin + Monaco typing "M" on a new last line)."""
    sub = r.sub
    key = "intellisense."
    path = main_file(project, pl, folder)
    if path is None:
        sub[key + "completion"] = "SKIP: no code file in this template"
        return
    w = h.w
    try:
        ed = w.open_any_file(path)
        h.pump(1)
        if ed is None:
            sub[key + "completion"] = f"FAIL: File > Open did not give an editor for {path.name}"
            return
        if not callable(getattr(ed, "text", None)):
            sub[key + "completion"] = f"SKIP: {path.name} opens in the language's own designer ({type(ed).__name__})"
            return
        if path.suffix.lower() == ".json":
            sub[key + "completion"] = f"SKIP: the project is data ({path.name}); no code file to complete in"
            return
        h.wait(lambda: getattr(ed, "_ready", True), 40)
        h.pump(1)
        text = ed.text()
        lines = text.split("\n")
        new = text.rstrip("\n") + "\nM\n"
        line = len(text.rstrip("\n").split("\n"))
        items = _labels(pl.completions(new, line, 1, path, None))
        sub[key + "plugin_completion"] = (f"PASS - {len(items)} items" if items else
                                          "FAIL: plugin.completions gave nothing after 'M'")
        if type(ed).__name__ != "MonacoEditor":
            sub[key + "typing_M"] = f"SKIP: classic editor ({type(ed).__name__})"
            return
        n = len(lines)
        h.js(ed, f"(radEditor.setPosition({{lineNumber: {n}, column: radEditor.getModel().getLineMaxColumn({n})}}), "
                 "radEditor.focus(), 1)")
        h.js(ed, "(radEditor.trigger('keyboard', 'type', {text: '\\nM'}), 1)")
        rows = []
        for _ in range(40):
            h.pump(0.4)
            raw = h.js(ed, "JSON.stringify([...document.querySelectorAll('.suggest-widget.visible "
                           ".monaco-list-row')].map(e => e.getAttribute('aria-label') || e.textContent))")
            rows = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
            if rows:
                break
        sub[key + "typing_M"] = (f"PASS - {path.name}: {rows[:6]}" if rows else
                                 f"FAIL: typing 'M' in {path.name} ({ed.language_id()}) shows no suggestions")
        h.js(ed, "(radEditor.trigger('keyboard', 'hideSuggestWidget', {}), 1)")
        ed.setText(text)
        try:
            ed.setModified(False)
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        sub[key + "completion"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
