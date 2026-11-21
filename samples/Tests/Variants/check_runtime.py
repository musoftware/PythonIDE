"""Run the generated layout-variant runtime for real: python-qt (offscreen), python-tk and vb-basic (vbrun).

    python samples/Tests/Variants/check_runtime.py

Rebuilds the samples (make_samples.py), then each scenario runs in its own process and resizes the
window across the breakpoints (Base >= 1024, Tablet 600-1023, Phone < 600 and back), checking the
geometry of anchored / docked controls, hidden controls, texts, colours, CurrentSizes and the
<Form>_SizeVariantChanged event; the foldable scenarios set RADIDE_POSTURE / RADIDE_HINGE.
Exit code 0 = all passed."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FAILS: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


# --------------------------------------------------------------------------------------------- python-qt
def qt_child() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(HERE / "Variants_Qt_Responsive"))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from Form1 import Form1
    f = Form1()
    f.show()
    folded = os.environ.get("RADIDE_POSTURE") == "half-opened"

    def size(w, h):
        f.resize(w, h)
        end = time.monotonic() + 0.15
        while time.monotonic() < end:
            app.processEvents()

    def g(n):
        return getattr(f, n).geometry().getRect()
    size(1200, 700)
    if folded:
        check(f.CurrentSizes == ["tabletop"], f"qt half-opened 1200 x 700 -> tabletop ({f.CurrentSizes})")
        check(g("lstItems")[3] == 140, f"qt tabletop: the list stays above the fold ({g('lstItems')})")
        size(800, 600)
        check(f.CurrentSizes == ["tablet", "tabletop"], f"qt half-opened 800 x 600 -> tablet + tabletop "
              f"({f.CurrentSizes})")
        check(f.btnSave.text() == "Save changes" and g("lstItems")[3] == 140, "qt: both sizes apply (cascade)")
        os.environ["RADIDE_POSTURE"] = "flat"
        f.ApplySizeVariants()
        check(f.CurrentSizes == ["tablet"] and g("lstItems")[3] == 436,
              f"qt: ApplySizeVariants after unfolding ({f.CurrentSizes}, {g('lstItems')})")
        return
    check(f.CurrentSizes == [], f"qt 1200 x 700: designed size ({f.CurrentSizes})")
    check(g("txtSearch") == (200, 72, 980, 24), f"qt base: search box stretches ({g('txtSearch')})")
    check(g("btnSave") == (1080, 658, 100, 30), f"qt base: Save anchored bottom-right ({g('btnSave')})")
    check(g("pnlSide")[2] == 180 and g("pnlHeader")[2] == 1200, "qt base: docked side / header")
    size(800, 600)
    check(f.CurrentSizes == ["tablet"], f"qt 800 x 600 -> tablet ({f.CurrentSizes})")
    check(f.btnSave.text() == "Save changes" and g("btnSave") == (640, 558, 140, 30),
          f"qt tablet: Save text / geometry ({f.btnSave.text()!r}, {g('btnSave')})")
    check("#0b8a5f" in f.pnlHeader.styleSheet(), "qt tablet: green header")
    size(1000, 600)
    check(g("btnSave") == (840, 558, 140, 30), f"qt tablet at 1000: Save keeps its right anchor ({g('btnSave')})")
    size(420, 700)
    check(f.CurrentSizes == ["phone"], f"qt 420 x 700 -> phone ({f.CurrentSizes})")
    check(not f.pnlSide.isVisible() and not f.lblStatus.isVisible(), "qt phone: side menu + status hidden")
    check(g("txtSearch") == (16, 72, 388, 24) and g("lstItems") == (16, 108, 388, 520),
          f"qt phone: search / list fill the width ({g('txtSearch')}, {g('lstItems')})")
    check(g("btnSave") == (16, 650, 388, 34) and f.btnSave.text() == "Save", "qt phone: Save full width, base text")
    check(f.lblTitle.text() == "Customers (phone)", "qt phone: title text")
    size(380, 640)
    check(g("btnSave") == (16, 590, 348, 34), f"qt phone at 380 x 640: anchors still stretch ({g('btnSave')})")
    size(1300, 800)
    check(f.CurrentSizes == [] and f.pnlSide.isVisible() and f.lblTitle.text() == "Customers"
          and f.btnSave.text() == "Save", "qt back to the designed size: everything restored")
    check(g("txtSearch") == (200, 72, 1080, 24) and g("btnSave") == (1180, 758, 100, 30),
          f"qt restored anchors ({g('txtSearch')}, {g('btnSave')})")
    check("#0b8a5f" not in f.pnlHeader.styleSheet(), "qt: header colour restored")
    check(f.changes >= 3, f"qt: Form1_SizeVariantChanged fired on each change after Load ({f.changes})")


# --------------------------------------------------------------------------------------------- python-tk
def tk_child() -> None:
    sys.path.insert(0, str(HERE / "Variants_Tk_Responsive"))
    from Form1 import Form1
    f = Form1()
    root = f.root
    root.geometry("+-3000+-3000")
    hinge = bool(os.environ.get("RADIDE_HINGE"))

    def size(w, h):
        root.geometry(f"{w}x{h}")
        end = time.monotonic() + 0.2
        while time.monotonic() < end:
            root.update()
            time.sleep(0.005)

    def g(n):
        w = getattr(f, n)
        return w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()
    size(1200, 700)
    if hinge:
        check(f.CurrentSizes == ["tabletop"], f"tk RADIDE_HINGE + half-opened -> tabletop ({f.CurrentSizes})")
        check(f._variants.env["fold"] == "horizontal" and f._variants.env["span"] == "dual",
              f"tk: hinge gives fold / span ({f._variants.env})")
        check(g("lstItems")[3] == 140, f"tk tabletop list ({g('lstItems')})")
        root.destroy()
        return
    check(f.CurrentSizes == [] and g("txtSearch") == (200, 72, 980, 24), f"tk base ({g('txtSearch')})")
    size(800, 600)
    check(f.CurrentSizes == ["tablet"] and f.btnSave.cget("text") == "Save changes"
          and g("btnSave") == (640, 558, 140, 30), f"tk tablet ({g('btnSave')})")
    check(str(f.pnlHeader.cget("bg")).lower() == "#0b8a5f", "tk tablet: green header")
    size(420, 700)
    check(f.CurrentSizes == ["phone"] and f.pnlSide.winfo_manager() == "" and f.lblStatus.winfo_manager() == "",
          "tk phone: side menu + status hidden")
    check(g("txtSearch") == (16, 72, 388, 24) and g("btnSave") == (16, 650, 388, 34),
          f"tk phone geometry ({g('txtSearch')}, {g('btnSave')})")
    check(f.lblTitle.cget("text") == "Customers (phone)", "tk phone title")
    size(1200, 700)
    check(f.CurrentSizes == [] and f.pnlSide.winfo_manager() == "place" and f.lblStatus.winfo_manager() == "place"
          and str(f.pnlHeader.cget("bg")).lower() == "#1f6feb" and f.lblTitle.cget("text") == "Customers",
          "tk back to the designed size: restored")
    check(g("btnSave") == (1080, 658, 100, 30) and g("pnlSide")[2] == 180, f"tk restored anchors ({g('btnSave')})")
    check(f.changes >= 3, f"tk: Form1_SizeVariantChanged fired ({f.changes})")
    root.destroy()


# --------------------------------------------------------------------------------------------- vb-basic
def vb_child() -> None:
    sys.path.insert(0, str(ROOT))
    from radide.runtimes.vbrun import Runtime
    rt = Runtime(HERE / "Variants_VB6")
    rt.load()
    vf = rt.forms["form1"]
    vf.load()
    vf.vb_call("show", [])
    ui, root = vf.ui, rt.root
    top = ui.root
    top.geometry("+-3000+-3000")

    def size(w, h):
        top.geometry(f"{w}x{h}")
        end = time.monotonic() + 0.2
        while time.monotonic() < end:
            root.update()
            time.sleep(0.005)
    size(1200, 700)
    check(ui.CurrentSizes == [] and ui.cmdSave.cget("text") == "Save", "vb base")
    size(800, 600)
    check(ui.CurrentSizes == ["tablet"] and ui.cmdSave.cget("text") == "Save changes"
          and ui.cmdSave.winfo_width() == 140, "vb tablet: Save changes, 140 wide")
    size(420, 700)
    check(ui.CurrentSizes == ["phone"] and ui.pnlSide.winfo_manager() == "" and ui.cmdSave.winfo_x() == 16
          and ui.cmdSave.winfo_width() == 388, "vb phone: side menu hidden, Save full width")
    size(1200, 700)
    check(ui.CurrentSizes == [] and ui.pnlSide.winfo_manager() == "place" and ui.cmdSave.winfo_x() == 1080,
          "vb restored")
    vf.vb_call("unload", []) if hasattr(vf, "vb_call") else None


def run(kind: str, env: dict | None = None) -> None:
    e = dict(os.environ)
    e.update(env or {})
    for k in ("RADIDE_POSTURE", "RADIDE_SPAN", "RADIDE_HINGE"):
        if not (env or {}).get(k):
            e.pop(k, None)
    e.setdefault("QT_QPA_PLATFORM", "offscreen")
    p = subprocess.run([sys.executable, __file__, kind], env=e, capture_output=True, text=True, timeout=180)
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if line.startswith(("ok ", "FAIL")):
            print(line, flush=True)
            if line.startswith("FAIL"):
                FAILS.append(line)
    if p.returncode != 0:
        tail = "\n".join(out.splitlines()[-15:])
        check(False, f"{kind} scenario exited with {p.returncode}:\n{tail}")


def main() -> int:
    if len(sys.argv) > 1:
        {"qt": qt_child, "tk": tk_child, "vb": vb_child}[sys.argv[1]]()
        sys.stdout.flush()
        os._exit(1 if FAILS else 0)
    subprocess.run([sys.executable, str(HERE / "make_samples.py")], check=True)
    run("qt")
    run("qt", {"RADIDE_POSTURE": "half-opened"})
    run("tk")
    run("tk", {"RADIDE_POSTURE": "half-opened", "RADIDE_HINGE": "0,330,1200,0"})
    run("vb")
    print(f"{'ALL OK' if not FAILS else f'{len(FAILS)} FAILED'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
