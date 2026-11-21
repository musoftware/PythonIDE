"""Retro QA - regression smoke: the retro / NASA additions leave the existing languages alone.

* Existing project types still create, open and run (Ctrl+F5): Python console, C, NASM x64 assembly, Fortran
  (modern, free form), VB (BASIC) console.
* Open Folder detection: the samples HelloPython / HelloC / HelloRing are still detected as before (not as DOS,
  AGC, ROM or retro projects); a DOS folder / an AGC folder / loose ROMs are detected as the new types.
* Editors: a NASM .asm keeps the x86 assembly plugin (the retro 6502 guard only applies to retro projects),
  .f90 opens with the modern Fortran plugin, .py with Python; .exe / .dll / .pdf are not grabbed as ROMs
  (the ROM hex editor opens only ROM / patch extensions or unknown binaries).

    python samples/Tests/Retro/QA/e2e_regression.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "retro_qa_regression")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait  # noqa: E402

from radide.languages import get_plugin, plugin_for_file  # noqa: E402

REPO = Path(qh.ROOT)
WORK = Path(qh.WORK) / "retro_qa_regression"

RUNS = [   # plugin id, template (None = first), text expected in the output
    ("python-tk", None, ""),
    ("c-bridge", None, ""),
    ("asm-nasm", None, ""),
    ("fortran-bridge", None, ""),
    ("vb-basic", None, ""),
]


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    w = qh.window()
    # ---- existing languages run
    for pid, tpl, proof in RUNS:
        plugin = get_plugin(pid)
        if plugin is None:
            print(f"SKIP {pid}: plugin not present")
            continue
        tpls = plugin.project_templates() if hasattr(plugin, "project_templates") else []
        tpl = tpl or (tpls[0][0] if tpls else "")
        folder = WORK / pid
        try:
            name = pid.replace("-", "_").title().replace("_", "")
            if hasattr(plugin, "create_new_project"):
                plugin.create_new_project(folder, name, tpl)
            else:                                   # classic RAD project with Form1 (New Project default)
                from radide.workspace import create_project
                create_project(folder, name, pid).save()
        except Exception as e:  # noqa: BLE001
            check(f"{pid}: create project", False, repr(e))
            continue
        w.open_project(folder, ask=False)
        pump(1.5)
        check(f"{pid}: opens with its own plugin", w.project is not None and w.project.language == pid,
              getattr(w.project, "language", None))
        w.output.clear()
        w.run_project(debug=False)
        s = w.session
        ok = s is not None
        if ok:      # a console program ends; a form keeps running: give it time to build and start
            wait(lambda: not s.running(), 45)
            pump(2)
            ok = s.running() or s.proc.exitCode() == 0 if hasattr(s, "proc") else True
        out = w.output.toPlainText()
        check(f"{pid}: Ctrl+F5 builds and starts it (no retro tool involved, no error)",
              ok and "radide.retro" not in out and "radide.agc" not in out and "Traceback" not in out
              and "*** Error" not in out, out[-800:])
        if s is not None and s.running():
            s.stop()
    # ---- Open Folder detection
    from radide import project_detect as PD
    for name, bad in (("HelloPython", ("retro", "dos", "agc", "rom")), ("HelloC", ("retro", "dos", "agc")),
                      ("HelloRing", ("retro", "dos", "agc"))):
        f = REPO / "samples" / name
        if not f.is_dir():
            continue
        d = PD.detect(f)
        kinds = [str(getattr(c, "language", "") or getattr(c, "kind", "")) for c in sorted(d.candidates(), key=lambda c: -c.confidence)][:3]
        top = kinds[0] if kinds else str(d)
        check(f"Open Folder: {name} still detected as before ({top})", top and not any(b in top.lower() for b in bad),
              kinds)
    dosf = REPO / "samples" / "Tests" / "Retro" / "DosProgramFolder"
    d = PD.detect(dosf)
    kinds = [str(getattr(c, "language", "") or getattr(c, "kind", "")) for c in sorted(d.candidates(), key=lambda c: -c.confidence)][:3]
    check("Open Folder: a DOS program folder -> DOS Program", kinds and "dos" in kinds[0].lower(), kinds)
    agcf = WORK / "agcfolder"
    shutil.copytree(REPO / "samples" / "Tests" / "Retro" / "AGC" / "HelloDSKY", agcf)
    (agcf / "project.radproj").unlink(missing_ok=True)
    d = PD.detect(agcf)
    kinds = [str(getattr(c, "language", "") or getattr(c, "kind", "")) for c in sorted(d.candidates(), key=lambda c: -c.confidence)][:3]
    check("Open Folder: a folder of .agc sources -> Apollo AGC", kinds and "agc" in kinds[0].lower(), kinds)
    # ---- editors / file routing
    from radide.retro.rom.hexdoc import HexDocument
    py = WORK / "x.py"
    py.write_text("print(1)\n", encoding="utf-8")
    f90 = WORK / "x.f90"
    f90.write_text("program x\nprint *, 1\nend program x\n", encoding="utf-8")
    asm = WORK / "x.asm"
    asm.write_text("section .text\nglobal main\nmain:\n    xor eax, eax\n    ret\n", encoding="utf-8")
    check(".py -> Python plugin", "python" in getattr(plugin_for_file(py), "id", ""), getattr(plugin_for_file(py), "id", None))
    check(".f90 -> modern Fortran plugin (not fortran-legacy)", getattr(plugin_for_file(f90), "id", "") == "fortran-bridge",
          getattr(plugin_for_file(f90), "id", None))
    w.open_project(WORK / "asm-nasm", ask=False) if (WORK / "asm-nasm").is_dir() else None
    pump(1)
    ed = w.open_any_file(asm)
    pump(2)
    ed = w.tabs.currentWidget()
    edp = getattr(ed, "plugin", None) or getattr(getattr(ed, "editor", None), "plugin", None)
    check(".asm in a NASM project keeps the x86 plugin (not the retro 6502 one)",
          edp is not None and not getattr(edp, "retro_dev", False), repr(edp))
    exe = Path(sys.executable)
    w.open_any_file(exe)
    pump(1)
    cur = w.tabs.currentWidget()
    check("python.exe is not opened as a ROM document", not (isinstance(cur, HexDocument) and
                                                           getattr(cur, "info", None) is not None and
                                                           "ROM" in str(getattr(cur.info, "system", ""))),
          type(cur).__name__)
    qh.finish(w)


if __name__ == "__main__":
    main()
