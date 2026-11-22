"""Project files in the IDE (offscreen, QSettings org RADIDE-TEST-NONDEF, widget.grab only).

* open -> Save All without a change: the .form and project.radproj stay byte-identical (an old version 1
  form with CRLF newlines and no trailing newline);
* a broken .form (git merge conflict markers, empty, ANSI Arabic code page, truncated) opens nothing and
  shows a clear error; the file is not changed; the IDE keeps working;
* a form of a newer format version opens with a warning in the Output window;
* files changed outside the IDE: "reload?" -> Yes reloads the designer / the code editor; a document with
  unsaved changes answered No keeps the IDE's version; a change to an unreadable file keeps the IDE's
  version with an error; the IDE's own saves do not ask;
* a read-only .form: Save All fails with a message, the document stays modified, the file is unchanged;
  saving to another (writable) copy works;
* a corrupted project.radproj / .radsln: "Cannot open project" with the reason, no crash.

Run:  .venv\\Scripts\\python samples/Tests/Robustness/Files/test_files_ide.py
"""
import json
import os
import stat
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _nondef_harness import SAMPLES, WORK, check, close_window, copy_tree, finish, gui, main_window, pump  # noqa: E402

app, MSGS, ANSWERS = gui()
from PyQt6.QtWidgets import QMessageBox  # noqa: E402

proj = copy_tree(SAMPLES / "HelloPython", "HelloFiles")
form1 = proj / "Form1.form"
raw_form1 = form1.read_bytes()
good = json.loads(raw_form1)
lines = raw_form1.decode("utf-8").splitlines(keepends=True)
(proj / "Broken.form").write_text("".join(lines[:3]) + "<<<<<<< HEAD\n" + lines[3] + "=======\n" + lines[3] +
                                  ">>>>>>> other\n" + "".join(lines[4:]), encoding="utf-8")
(proj / "Empty.form").write_bytes(b"")
ansi = dict(good, props=dict(good["props"], Name="Ansi", Text="نموذج"))
(proj / "Ansi.form").write_bytes(json.dumps(ansi, ensure_ascii=False, indent=2).encode("cp1256"))
(proj / "Cut.form").write_bytes(raw_form1[: len(raw_form1) // 3])
fut = dict(good, version=42, props=dict(good["props"], Name="Future"), futureThing={"x": 1})
(proj / "Future.form").write_text(json.dumps(fut, indent=2), encoding="utf-8")
for n in ("Broken", "Empty", "Ansi", "Cut", "Future"):
    (proj / f"{n}.py").write_text("# code\n", encoding="utf-8")
pr = json.loads((proj / "project.radproj").read_text(encoding="utf-8"))
pr["forms"] = pr["forms"] + ["Broken", "Empty", "Ansi", "Cut", "Future"]
(proj / "project.radproj").write_text(json.dumps(pr, indent=2), encoding="utf-8")
raw_proj = (proj / "project.radproj").read_bytes()
broken_raw = {n: (proj / f"{n}.form").read_bytes() for n in ("Broken", "Empty", "Ansi", "Cut")}

w = main_window(app)
try:
    w.open_project(proj, ask=False)
    pump(app, 2)
    check("a project with broken forms opens", w.project is not None and w.project.name, MSGS[-2:])
    w.open_designer("Form1")
    pump(app, 1)
    w.open_code("Form1")
    pump(app, 0.5)
    check("Form1 (version 1, CRLF, no trailing newline) opens in the designer", "Form1" in w.designers)
    ok = w.save_all()
    pump(app, 0.5)
    check("open -> Save All without a change: Form1.form is byte-identical", form1.read_bytes() == raw_form1)
    check("open -> Save All without a change: project.radproj is byte-identical", (proj / "project.radproj").read_bytes() == raw_proj)

    # ---- broken forms
    for n, word in (("Broken", "merge conflict"), ("Empty", "empty"), ("Ansi", "UTF-8"), ("Cut", "truncated")):
        MSGS.clear()
        for oname, opener in (("open_designer", w.open_designer), ("open_code", w.open_code)):
            try:
                opener(n)
                crashed = None
            except Exception as e:  # noqa: BLE001
                crashed = e
            pump(app, 0.3)
            check(f"{n}.form via {oname}: no exception escapes", crashed is None, repr(crashed))
        crit = [m for m in MSGS if m[0] == "critical"]
        check(f"{n}.form: a clear error is shown ('{word}')", crit and word.lower() in " ".join(crit[0][1]).lower(), MSGS)
        check(f"{n}.form: no designer / document is created", n not in w.designers and n not in w.docs)
        check(f"{n}.form: the file is not changed", (proj / f"{n}.form").read_bytes() == broken_raw[n])
    w.save_all()
    pump(app, 0.3)
    check("Save All after the failed opens does not touch the broken files",
          all((proj / f"{n}.form").read_bytes() == b for n, b in broken_raw.items()))

    # ---- newer version
    w.open_designer("Future")
    pump(app, 0.8)
    out = w.output.toPlainText()
    check("a form of a newer format opens with a warning in the Output window", "Future" in w.designers and "newer" in out,
          out[-400:])

    # ---- external changes
    fi = w.file_integrity
    doc = w.docs["Form1"]
    d = json.loads(form1.read_text(encoding="utf-8"))
    d["props"]["Text"] = "Changed outside"
    time.sleep(0.05)
    form1.write_text(json.dumps(d, indent=2), encoding="utf-8")
    MSGS.clear()
    ANSWERS["question"] = QMessageBox.StandardButton.Yes
    reloaded = fi.check()
    pump(app, 0.5)
    check("form changed outside the IDE: 'File Modification Detected' asks to reload",
          any(m[0] == "question" and "outside" in " ".join(m[1]) for m in MSGS), MSGS)
    check("... Yes reloads the designer (new caption, not modified)", "Form1" in reloaded and doc.form.props["Text"] == "Changed outside"
          and not doc.modified, (reloaded, doc.form.props.get("Text")))
    cv = w.codeviews["Form1"]
    code_path = proj / "Form1.py"
    code_path.write_text(code_path.read_text(encoding="utf-8") + "\n# edited outside\n", encoding="utf-8")
    MSGS.clear()
    fi.check()
    pump(app, 0.3)
    check("code file changed outside: reloaded into the editor", "# edited outside" in cv.editor.text() and not cv.editor.isModified())

    # dirty document + external change, answered No
    doc.set_prop(None, "Text", "IDE version")
    d["props"]["Text"] = "Outside again"
    form1.write_text(json.dumps(d, indent=2), encoding="utf-8")
    MSGS.clear()
    ANSWERS["question"] = QMessageBox.StandardButton.No
    fi.check()
    pump(app, 0.3)
    check("unsaved changes + external change: the question says the changes would be lost",
          any("unsaved" in " ".join(m[1]) for m in MSGS if m[0] == "question"), MSGS)
    check("... No keeps the IDE's version", doc.form.props["Text"] == "IDE version" and doc.modified)
    w.save_all()
    pump(app, 0.3)
    check("... and Save writes the IDE's version", json.loads(form1.read_text(encoding="utf-8"))["props"]["Text"] == "IDE version")
    MSGS.clear()
    fi.check()
    check("the IDE's own save does not ask to reload", not [m for m in MSGS if m[0] == "question"], MSGS)

    # external change to an unreadable file
    form1.write_text('{"version": 2, "props": {', encoding="utf-8")
    MSGS.clear()
    ANSWERS["question"] = QMessageBox.StandardButton.Yes
    fi.check()
    pump(app, 0.3)
    check("external change to an unreadable .form: an error, the IDE's version is kept",
          any(m[0] == "critical" for m in MSGS) and doc.form.props["Text"] == "IDE version", MSGS)
    doc.set_modified(True)
    w.save_all()
    pump(app, 0.3)
    check("... Save repairs the file with the IDE's version", json.loads(form1.read_text(encoding="utf-8"))["props"]["Text"] == "IDE version")

    # ---- read-only .form
    os.chmod(form1, stat.S_IREAD)
    ro_raw = form1.read_bytes()
    doc.set_prop(None, "Text", "while read-only")
    MSGS.clear()
    n_out = len(w.output.toPlainText())
    ok = w.save_all()
    pump(app, 0.3)
    msg = w.output.toPlainText()[n_out:] + " ".join(" ".join(m[1]) for m in MSGS)
    check("read-only .form: Save All reports the failure", ok is False and "read-only" in msg.lower(), (ok, msg[-300:]))
    check("read-only .form: the file is unchanged and the document stays modified", form1.read_bytes() == ro_raw and doc.modified)
    copy = WORK / "Form1_copy.form"
    doc.form.save(copy)
    check("read-only .form: saving the form to another file (Save As) works",
          json.loads(copy.read_text(encoding="utf-8"))["props"]["Text"] == "while read-only")
    os.chmod(form1, stat.S_IWRITE | stat.S_IREAD)
    w.save_all()
    pump(app, 0.3)

    # ---- corrupted project files
    for label, fname, data in (("project.radproj with merge markers", "project.radproj",
                                b'{\n<<<<<<< HEAD\n  "name": "A",\n=======\n  "name": "B",\n>>>>>>> x\n  "language": "python-tk"\n}'),
                               ("empty project.radproj", "project.radproj", b""),
                               ("truncated .radsln", "Bad.radsln", b'{"name": "Bad", "projects": [')):
        bad = WORK / ("BadProj_" + label.split()[0].replace(".", "_"))
        bad.mkdir(exist_ok=True)
        (bad / fname).write_bytes(data)
        MSGS.clear()
        try:
            w.open_project(bad / fname if fname.endswith(".radsln") else bad, ask=False)
            crashed = None
        except Exception as e:  # noqa: BLE001
            crashed = e
        pump(app, 0.5)
        txt = " ".join(" ".join(m[1]) for m in MSGS)
        check(f"{label}: 'Cannot open project' with the reason, no exception",
              crashed is None and "Cannot open project" in txt and any(k in txt for k in ("merge", "empty", "JSON")),
              (repr(crashed), txt[:300]))
        check(f"{label}: the file is not changed", (bad / fname).read_bytes() == data)
    errs = [l for l in w.output.toPlainText().splitlines() if "Traceback" in l]
    check("no tracebacks in the Output window", not errs, errs[:5])
except Exception:  # noqa: BLE001
    import traceback
    check("the test script runs to the end", False, traceback.format_exc()[-1500:])
finally:
    close_window(app, w)

print("MSGS:", json.dumps(MSGS, ensure_ascii=False)[:800])
finish(app)
