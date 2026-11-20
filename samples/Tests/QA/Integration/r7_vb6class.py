"""QA: VB6 class-module program (samples/Tests/VB6/BankClasses copy) opened and run (Ctrl+F5 and F5) in the IDE."""
import os, shutil
os.environ.setdefault("QA_NAME", "iqa_vb6class")
from qh import *  # noqa
from pathlib import Path
d = Path(WORK) / "BankClasses"; shutil.rmtree(d, ignore_errors=True)
shutil.copytree(Path(ROOT) / "samples/Tests/VB6/BankClasses", d)
w = window()
w.open_project(d, ask=False); pump(2)
check("project opened", w.project is not None and w.project.name, w.project)
print("language", w.project.language, "modules", w.project.modules)
for dbg in (False, True):
    w.output.clear(); w.run_project(debug=dbg)
    ok = wait(lambda: w.session is None, 120)
    out = w.output.toPlainText()
    tag = "F5" if dbg else "Ctrl+F5"
    check(f"{tag}: program finished", ok, out[-300:])
    for line in ("Error 1000 in CAccount.Owner: Owner name is required", "Total: 420.50",
                 "AC002: overdraft of 79.50 refused", "Records: 3", "5! = 120"):
        check(f"{tag}: output has {line!r}", line in out, out[-600:])
    check(f"{tag}: no Traceback", "Traceback" not in out, out[-600:])
# open a class module in the code editor
w.open_module("CBank.cls") if hasattr(w, "open_module") else None
pump(2); shot(w, "vb6_bankclasses")
finish(w)
