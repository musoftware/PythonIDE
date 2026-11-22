"""Check family "designer": the form designer round trip in the real IDE.

  add           a Button is added on the designer surface (FormDocument.add_control) and shown
  rename        Properties Name -> btnQa; the form and the code follow (rename_symbol)
  double_click  double-click (goto_event) creates the Click handler stub in the language and opens it
  events_tab    Properties > Events lists the control's events and shows the handler (bold) - the VB6 Events tab
                was empty in a release build
  save_reopen   Save All, close the solution, open the project again: the control and the handler are there
"""
from __future__ import annotations

import traceback

from radide.model import Form  # noqa: F401 - imported here so a frozen build fails loudly if it is missing


def run(h, r, pl, project, folder) -> None:
    sub = r.sub
    k = "designer."
    w = h.w
    if not getattr(w.project, "forms", None):
        sub[k + "add"] = "SKIP: this template has no form"
        return
    if not w.project.form_path("Form1").is_file():
        sub[k + "add"] = "SKIP: this language has its own designer (screens / widgets), not .form files"
        return
    try:
        w.open_designer("Form1")
        h.pump(1)
        doc = w._doc("Form1")
        dv = w.designers.get("Form1")
        before = len(doc.form.controls)
        ctrl = doc.add_control("Button", 200, 140)
        h.pump(0.5)
        shown = dv is not None and any(getattr(x, "ctrl", None) is ctrl or getattr(x, "name", "") == ctrl.name
                                       for x in getattr(getattr(dv, "surface", dv), "children", lambda: [])())
        sub[k + "add"] = (f"PASS - {ctrl.name} added" + ("" if shown else " (surface widget not inspected)")
                          if len(doc.form.controls) == before + 1 else "FAIL: the control was not added")
        old = ctrl.name
        doc.set_prop(ctrl, "Name", "btnQa")
        h.pump(0.5)
        ok_name = doc.form.find("btnQa") is not None
        sub[k + "rename"] = f"PASS - {old} -> btnQa" if ok_name else f"FAIL: rename {old} -> btnQa did not apply"
        w.goto_event("Form1", ctrl, "Click")
        h.pump(1.5)
        ed = w.codeviews["Form1"].editor
        h.wait(lambda: getattr(ed, "_ready", True), 40)
        h.pump(0.5)
        handler = pl.handler_for(doc.form, ctrl, "Click")
        line = pl.find_handler(ed.text(), handler)
        tab = w.tabs.currentWidget() is w.codeviews["Form1"]
        sub[k + "double_click"] = (f"PASS - {handler} at line {line + 1}" + ("" if tab else " (code tab not current)")
                                   if line >= 0 else f"FAIL: no {handler} stub in {pl.code_file('Form1')}")
        # Properties > Events for the selected control
        w.open_designer("Form1")
        h.pump(0.5)
        doc.select(ctrl)
        h.pump(0.5)
        props = w.properties
        props.tabs.setCurrentIndex(1)
        h.pump(0.5)
        rows = props.events.rowCount()
        names = [props.events.item(i, 0).text() for i in range(rows) if props.events.item(i, 0)]
        shown_handler = [props.events.item(i, 1).text() for i in range(rows)
                         if props.events.item(i, 1) and props.events.item(i, 1).text()]
        if rows and "Click" in names and handler in shown_handler:
            sub[k + "events_tab"] = f"PASS - {rows} events, Click -> {handler}"
        elif rows:
            sub[k + "events_tab"] = f"FAIL: {rows} events but the Click handler is not shown ({shown_handler[:3]})"
        else:
            sub[k + "events_tab"] = "FAIL: Properties > Events is empty"
        props.tabs.setCurrentIndex(0)
        # save + reopen
        w.save_all()
        h.pump(0.5)
        h.open_project(folder)
        f2 = Form.load(w.project.form_path("Form1"))
        code = (folder / pl.code_file("Form1")).read_text(encoding="utf-8")
        ok = f2.find("btnQa") is not None and pl.find_handler(code, handler) >= 0
        sub[k + "save_reopen"] = "PASS - btnQa and its handler are saved" if ok else \
            f"FAIL: after reopen control={'yes' if f2.find('btnQa') else 'no'} " \
            f"handler={'yes' if pl.find_handler(code, handler) >= 0 else 'no'}"
    except Exception as e:  # noqa: BLE001
        sub[k + "error"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
