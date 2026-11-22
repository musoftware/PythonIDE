"""VB6 (BASIC) -> native exe (FreeBASIC) end-to-end test.

    .venv\\Scripts\\python samples\\Tests\\Native\\VB6\\test_native_vb6.py [--only Name] [--keep]

1. every project here is published with radide.deploy.build.build(): the result must be the native kind,
   one exe without Python (no python*.dll, no _internal) that imports Windows system DLLs only;
2. the same user actions (scenarios.py) are replayed on the exe (Win32 messages, ctypes) and on the IDE's
   VB runtime (vbrun_driver.py): Debug.Print output and the texts read back must be identical;
3. forms: the rectangle of every control of the startup form in the running exe (GetWindowRect of its
   window, relative to the client area, at 96 DPI) is compared with the .form geometry and with the
   designer (DesignerView offscreen, QSettings RADIDE-TEST); pictures: designer (widget.grab) and exe
   (PrintWindow of that window only) are saved next to the report;
4. projects the translator cannot handle report file(line) reasons (Publish falls back to vbrun).
Only processes started here are closed.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["RADIDE_NO_BROWSER"] = "1"

from scenarios import SCENARIOS  # noqa: E402
import winutil as W  # noqa: E402

PROJECTS = ["HelloVB", "ControlsGallery", "MultiForm", "ArabicForm", "AnchorsDock", "VB_Form", "BASIC_Form",
            "BASIC_Console", "Debug_VB_Expand"]
UNSUPPORTED = {"LanguageFeatures": ROOT / "samples" / "Tests" / "VB6" / "LanguageFeatures",
               "BankClasses": ROOT / "samples" / "Tests" / "VB6" / "BankClasses",
               "RatingBar_VB": ROOT / "samples" / "Tests" / "Components" / "RatingBar_VB",
               "Variants_VB6": HERE / "Variants_VB6"}
SYSTEM_DLLS = {"kernel32.dll", "user32.dll", "gdi32.dll", "comctl32.dll", "comdlg32.dll", "shell32.dll",
               "advapi32.dll", "ole32.dll", "oleaut32.dll", "msvcrt.dll", "uxtheme.dll", "gdiplus.dll",
               "shlwapi.dll", "winmm.dll", "ntdll.dll"}
RESULTS: dict = {"pass": 0, "fail": 0, "lines": []}
_APP = None


def ok(cond, what):
    RESULTS["pass" if cond else "fail"] += 1
    line = ("ok   " if cond else "FAIL ") + what
    RESULTS["lines"].append(line)
    print(line, flush=True)
    return cond


# ------------------------------------------------------------------ build
def build(name, out_root: Path):
    from radide.deploy import build as B
    from radide.deploy.config import PublishConfig
    cfg = PublishConfig()
    cfg.app_name = name
    cfg.output_dir = str(out_root / name)
    cfg.make_installer = False
    log = []
    res = B.build(HERE / name, cfg, log=log.append)
    gen = out_root / name / "build" / "native_vb6"
    return res, log, gen


def imports(exe: Path) -> list[str]:
    import pefile
    pe = pefile.PE(str(exe), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    names = [e.dll.decode().lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
    pe.close()
    return names


def control_ids(gen: Path) -> dict:
    """'Form1.txtName' -> runtime id (from the generated FreeBASIC Consts)."""
    out = {}
    src = next(gen.glob("*.bas")).read_text(encoding="utf-8")
    for m in re.finditer(r"^Const (CTL|MNU|FRM)_(\w+?) = (\d+)$", src, re.M):
        out[m.group(2).lower()] = int(m.group(3))
    for m in re.finditer(r"^Dim Shared CTL_(\w+)__arr\((-?\d+) To (-?\d+)\) As Long = \{(.*)\}$", src, re.M):
        lo = int(m.group(2))
        for k, c in enumerate(x.strip() for x in m.group(4).split(",")):
            if c != "0":
                out[f"{m.group(1)}({lo + k})".lower()] = out[c.split("_", 1)[1].lower()]
    return out


# ------------------------------------------------------------------ native driver
class Native:
    def __init__(self, exe: Path, gen: Path, startup: str):
        self.p = subprocess.Popen([str(exe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(exe.parent))
        self.ids = control_ids(gen)
        self.startup = startup
        self.top = W.wait_window(self.p.pid)
        self.reads: list[str] = []

    def hwnd(self, spec):
        form = self.startup
        if "." in spec:
            form, spec = spec.split(".", 1)
        key = f"{form}_{spec}".lower()
        if spec == form or key not in self.ids and spec in (self.startup,):
            return self.top, "form"
        cid = 1000 + self.ids[key]
        for top in W.windows_of(self.p.pid):
            for c in W.children(top):
                if W.u.GetDlgCtrlID(c) == cid and W.cls(c) != "RADVBBox":
                    return c, W.cls(c)
            for c in W.children(top):
                if W.u.GetDlgCtrlID(c) == cid:
                    return c, W.cls(c)
        raise KeyError(spec)

    def run(self, steps):
        for st in steps:
            kind = st[0]
            if kind == "wait":
                time.sleep(st[1])
                continue
            if kind == "menu":
                W.u.SendMessageW(self.top, 0x0111, 1000 + self.ids[f"{self.startup}_{st[1]}".lower()], 0)
                continue
            h, klass = self.hwnd(st[1])
            if kind == "set":
                W.set_text(h, st[2])
            elif kind == "click":
                W.click(h)
            elif kind == "select":
                lb = klass.lower() == "listbox"
                W.u.SendMessageW(h, 0x0186 if lb else 0x014E, st[2], 0)
                W.u.SendMessageW(W.u.GetParent(h), 0x0111, (W.u.GetDlgCtrlID(h) & 0xFFFF) | (1 << 16), h)
            elif kind == "read":
                if klass == "form":
                    self.reads.append(W.text(h))
                elif klass.lower() == "listbox":
                    n = W.u.SendMessageW(h, 0x018B, 0, 0)
                    items = []
                    for i in range(n):
                        ln = W.u.SendMessageW(h, 0x018A, i, 0)
                        import ctypes
                        b = ctypes.create_unicode_buffer(ln + 1)
                        W.u.SendMessageW(h, 0x0189, i, ctypes.addressof(b))
                        items.append(b.value)
                    self.reads.append("|".join(items))
                else:
                    self.reads.append(W.text(h))
            elif kind == "modal":
                W.u.PostMessageW(h, 0x00F5, 0, 0)
                time.sleep(0.5)
                self.run(st[2])
                time.sleep(0.3)
            time.sleep(0.03)

    def finish(self):
        W.u.PostMessageW(self.top, 0x0010, 0, 0)          # WM_CLOSE: the program ends itself
        try:
            out, err = self.p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            W.close(self.p)
            out, err = self.p.communicate()
        return out.decode("utf-8", "replace").replace("\r\n", "\n").rstrip("\n").split("\n") if out else []


def scenario(name, res, gen, startup):
    steps = SCENARIOS.get(name)
    if name == "BASIC_Form":
        steps = [("read", "lblWelcome"), ("read", "txtA"), ("read", "Form1")]
    if not steps:
        return
    ref = subprocess.run([sys.executable, str(HERE / "vbrun_driver.py"), str(HERE / name), name, json.dumps(steps)],
                         capture_output=True, timeout=120, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    try:
        want = json.loads(ref.stdout.decode("utf-8").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        ok(False, f"{name}: vbrun reference failed: {ref.stderr.decode('utf-8', 'replace')[-500:]}")
        return
    n = Native(res.dist / res.exe, gen, startup)
    try:
        time.sleep(0.4)
        n.run(steps)
        time.sleep(0.2)
    finally:
        debug = n.finish()
    debug = [d for d in debug if d and not d.startswith(("queryunload", "unload main"))]
    ok(n.reads == want["reads"], f"{name}: texts read back match vbrun {n.reads if n.reads != want['reads'] else ''}"
       + (f" (vbrun {want['reads']})" if n.reads != want["reads"] else ""))
    ok(debug == want["debug"], f"{name}: Debug.Print output matches vbrun"
       + (f" native={debug} vbrun={want['debug']}" if debug != want["debug"] else f" ({len(debug)} lines)"))


# ------------------------------------------------------------------ geometry / pictures
def designer_rects(project: Path, form_name: str, png: Path) -> dict:
    from PyQt6.QtCore import QCoreApplication, QPoint, QSettings
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName("RADIDE-TEST")
    QCoreApplication.setApplicationName("RADIDE-TEST-native-vb6")
    global _APP
    app = _APP = QApplication.instance() or QApplication(sys.argv)
    QSettings().clear()
    from radide.designer import DesignerView
    from radide.document import FormDocument
    from radide.model import Form
    path = project / f"{form_name}.form"
    doc = FormDocument(Form.load(path), path)
    view = DesignerView(doc)
    view.resize(1400, 1000)
    view.show()
    app.processEvents()
    out = {}
    for c in doc.form.visual():
        w = view.previews.get(id(c))
        if w is None or not w.isVisibleTo(view.surface):
            continue
        p = w.mapTo(view.surface, QPoint(0, 0))
        out[c.name] = (p.x(), p.y(), w.width(), w.height())
    view.surface.grab().save(str(png))
    view.close()
    app.processEvents()
    return out


def model_rects(project: Path, form_name: str) -> dict:
    from radide.layout import place_specs
    from radide.model import Form
    f = Form.load(project / f"{form_name}.form")
    specs = place_specs(f)
    out = {}
    for c in f.visual():
        x, y = f.abs_pos(c)
        pl = specs.get(c.name)
        w, h = int(c.props.get("Width", 0)), int(c.props.get("Height", 0))
        if pl is not None and c.parent == "":
            r = pl.rect(int(f.props["Width"]), int(f.props["Height"]))
            x, y, w, h = r
        out[c.name] = (x, y, w, h, c.type, c.parent, c.props.get("Visible", True),
                       c.props.get("TabPage"))
    return out


def native_rects(exe: Path, gen: Path, form_name: str, png: Path) -> tuple[dict, float]:
    import ctypes
    ids = control_ids(gen)
    p = subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(exe.parent))
    out = {}
    try:
        top = W.wait_window(p.pid)
        time.sleep(0.6)
        dc = W.u.GetDC(0)
        dpi = W.g.GetDeviceCaps(dc, 90)
        W.u.ReleaseDC(0, dc)
        ox, oy = W.client_origin(top)
        kids = W.children(top)
        for key, cid in ids.items():
            if not key.startswith(form_name.lower() + "_"):
                continue
            name = key[len(form_name) + 1:]
            hs = [c for c in kids if W.u.GetDlgCtrlID(c) == 1000 + cid]
            if not hs:
                continue
            h = next((c for c in hs if W.cls(c) == "RADVBBox"), hs[0])
            x, y, w, hh = W.rect(h)
            if W.cls(h).lower() == "edit":                   # NumericUpDown: the arrows are a sibling
                for c in kids:
                    if W.cls(c).lower() == "msctls_updown32" and W.u.SendMessageW(c, 0x0400 + 106, 0, 0) == h:
                        bx, by, bw, bh = W.rect(c)
                        w = bx + bw - x
            vis = bool(W.u.IsWindowVisible(h))
            sc = 96 / dpi
            out[name] = (round((x - ox) * sc), round((y - oy) * sc), round(w * sc), round(hh * sc), W.cls(h), vis)
        cw, ch = W.client_size(top)
        img = W.capture(top, str(png))
        # the client area only (same picture area as the designer surface)
        wx, wy, _, _ = W.rect(top)
        img.crop((ox - wx, oy - wy, ox - wx + cw, oy - wy + ch)).save(str(png))
    finally:
        W.close(p)
    return out, dpi


def picture_diff(a: Path, b: Path) -> float:
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    diff = ImageChops.difference(ia, ib).convert("L")
    hist = diff.histogram()
    return sum(i * n for i, n in enumerate(hist)) / (ia.size[0] * ia.size[1] * 255) * 100


def geometry(name, res, gen, form_name, report_dir: Path):
    project = HERE / name
    if not (project / f"{form_name}.form").is_file():
        return
    model = model_rects(project, form_name)
    des = designer_rects(project, form_name, report_dir / f"{name}_designer.png")
    nat, dpi = native_rects(res.dist / res.exe, gen, form_name, report_dir / f"{name}_native.png")
    worst, diffs = 0, []
    for cname, (x, y, w, h, typ, parent, visible, page) in model.items():
        if not visible or typ in ("Timer",):
            continue
        n = nat.get(cname.lower())
        if n is None:
            diffs.append(f"{cname}: no window")
            continue
        tol_h = 40 if typ == "ComboBox" else 2       # a ComboBox's height comes from its font
        dx, dy, dw, dh = abs(n[0] - x), abs(n[1] - y), abs(n[2] - w), abs(n[3] - h)
        if dx > 1 or dy > 1 or dw > 2 or dh > tol_h:
            diffs.append(f"{cname} ({typ}): form {x},{y} {w}x{h} exe {n[0]},{n[1]} {n[2]}x{n[3]}")
        worst = max(worst, dx, dy, dw, dh if typ != "ComboBox" else 0)
        d = des.get(cname)
        if d is not None and (abs(d[0] - x) > 1 or abs(d[1] - y) > 1):
            diffs.append(f"{cname}: designer draws it at {d[0]},{d[1]} (form {x},{y})")
    ok(not diffs, f"{name}: {len(model)} controls of {form_name} at the designer's place and size "
                  f"(max {worst} px, screen {dpi} dpi)" + ("" if not diffs else ": " + "; ".join(diffs[:8])))
    pd = picture_diff(report_dir / f"{name}_designer.png", report_dir / f"{name}_native.png")
    RESULTS["lines"].append(f"     {name}: designer vs exe picture difference {pd:.1f}% (pictures in {report_dir})")
    print(RESULTS["lines"][-1])


def native_events(name, res, gen):
    """Events with arguments driven with real window messages (keyboard, mouse, scroll, tabs, close)."""
    import ctypes
    if name == "ControlsGallery":
        n = Native(res.dist / res.exe, gen, "Form1")
        try:
            time.sleep(0.4)
            ed, _ = n.hwnd("txtName")
            W.set_text(ed, "a")
            W.u.SendMessageW(ed, 0x00B1, 1, 1)                      # EM_SETSEL: caret at the end
            W.u.SendMessageW(ed, 0x0102, ord("b"), 0)               # WM_CHAR 'b' -> KeyPress makes it 'B'
            n.run([("read", "txtName"), ("read", "lblStatus")])
            pic, _ = n.hwnd("picLogo")
            W.u.SendMessageW(pic, 0x0201, 1, (20 << 16) | 10)       # WM_LBUTTONDOWN at 10,20 -> MouseDown
            W.u.SendMessageW(pic, 0x0202, 0, (20 << 16) | 10)
            lst, _ = n.hwnd("lstLog")
            W.u.SendMessageW(lst, 0x0186, 0, 0)
            W.u.SendMessageW(W.u.GetParent(lst), 0x0111, (W.u.GetDlgCtrlID(lst) & 0xFFFF) | (2 << 16), lst)  # LBN_DBLCLK
            trk, _ = n.hwnd("trkLevel")
            W.u.SendMessageW(trk, 0x0405, 1, 12)                    # TBM_SETPOS 12
            W.u.SendMessageW(W.u.GetParent(trk), 0x0114, 0, trk)    # WM_HSCROLL -> Change
            n.run([("read", "lblStatus")])
            upd, _ = n.hwnd("updCount")
            W.set_text(upd, "7")                                    # NumericUpDown -> Change
            n.run([("read", "lblStatus")])
            prg, _ = n.hwnd("prgDone")
            pos = W.u.SendMessageW(prg, 0x0408, 0, 0)               # PBM_GETPOS
            tab, _ = n.hwnd("tabMain")
            W.u.SendMessageW(tab, 0x0201, 1, (10 << 16) | 75)       # click the "Second" tab header
            W.u.SendMessageW(tab, 0x0202, 0, (10 << 16) | 75)
            time.sleep(0.2)
            reads = n.reads
        finally:
            debug = n.finish()
        ok(reads[:2] == ["aB", "typed aB"], f"ControlsGallery: KeyPress changes KeyAscii (a + 'b' -> {reads[:2]})")
        ok("mouse 1 10,20" in debug, "ControlsGallery: MouseDown(Button, Shift, X, Y) on a PictureBox -> 'mouse 1 10,20'")
        ok("dbl ready" in debug, "ControlsGallery: ListBox DblClick")
        ok(len(reads) > 2 and reads[2] == "level=12", f"ControlsGallery: TrackBar Change -> {reads[2:3]}")
        ok(len(reads) > 3 and reads[3] == "count=7" and pos == 70,
           f"ControlsGallery: NumericUpDown Change -> {reads[3:4]}, ProgressBar.Value set to {pos}")
        ok("tab 0->1" in debug, f"ControlsGallery: TabControl Click(PreviousTab) -> {[d for d in debug if d.startswith('tab')]}")
    if name == "MultiForm":
        n = Native(res.dist / res.exe, gen, "Form1")
        try:
            time.sleep(0.4)
            n.run([("click", "chkKeep")])
            W.u.SendMessageW(n.top, 0x0010, 0, 0)                   # WM_CLOSE -> QueryUnload Cancel = 1
            time.sleep(0.2)
            still = n.p.poll() is None and bool(W.u.IsWindow(n.top))
            n.run([("read", "lblResult"), ("click", "chkKeep")])
            reads = n.reads
        finally:
            debug = n.finish()
        ok(still and reads[0] == "refused", f"MultiForm: QueryUnload Cancel keeps the form open ({reads[0]})")
        ok(debug == ["queryunload 0", "queryunload 0", "unload main"] and n.p.returncode == 0,
           f"MultiForm: closing runs QueryUnload(UnloadMode 0) then Unload and ends the program {debug}")


def resize_check(res, gen):
    """AnchorsDock: Width/Height grow from code; anchored / docked controls follow (designer rules)."""
    n = Native(res.dist / res.exe, gen, "Form1")
    try:
        time.sleep(0.4)
        n.run([("click", "cmdRight")])
        time.sleep(0.3)
    finally:
        out = n.finish()
    from radide.layout import place_specs
    from radide.model import Form
    f = Form.load(HERE / "AnchorsDock" / "Form1.form")
    sp = place_specs(f)
    cw, ch = 500, 350
    want = [cw, ch, sp["txtWide"].rect(cw, ch)[2], sp["lstFill"].rect(cw, ch)[3], sp["cmdCorner"].rect(cw, ch)[0],
            sp["cmdCorner"].rect(cw, ch)[1]]
    got = [int(float(x)) for x in out[0].split("	")] if out else []
    ok(got == want, f"AnchorsDock: after Me.Width/Height += 100/50 the anchored controls are at {got} (designer rules {want})")


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[argv.index("--only") + 1] if "--only" in argv else ""
    keep = "--keep" in argv
    work = Path(tempfile.mkdtemp(prefix="radide_native_vb6_"))
    report = work / "report"
    report.mkdir()
    print("work:", work)
    sizes = {}
    try:
        for name in PROJECTS:
            if only and only != name:
                continue
            t = time.time()
            res, log, gen = build(name, work)
            if not ok(res.kind == "native", f"{name}: built as {res.kind} in {time.time() - t:.1f}s"):
                print("\n".join(l for l in log if l.startswith("  - ") or "error" in l.lower())[:3000])
                continue
            exe = res.dist / res.exe
            sizes[name] = exe.stat().st_size
            files = [p.name.lower() for p in res.dist.rglob("*")]
            ok(not any(f.startswith("python") and f.endswith(".dll") for f in files) and "_internal" not in files,
               f"{name}: no Python in the program folder ({len(files)} files, exe {sizes[name] // 1024} KB)")
            imp = imports(exe)
            ok(all(d in SYSTEM_DLLS for d in imp), f"{name}: imports Windows DLLs only: {', '.join(imp)}")
            proj = json.loads((HERE / name / "project.radproj").read_text(encoding="utf-8"))
            startup = proj.get("startup") or ""
            if proj.get("forms") and startup in proj["forms"]:
                scenario(name, res, gen, startup)
                native_events(name, res, gen)
                geometry(name, res, gen, startup, report)
                if name == "AnchorsDock":
                    resize_check(res, gen)
            else:
                p = subprocess.run([str(exe)], capture_output=True, timeout=30, cwd=str(res.dist))
                got = p.stdout.decode("utf-8", "replace").replace("\r\n", "\n").rstrip("\n")
                ref = subprocess.run([sys.executable, "-m", "radide.runtimes.vbrun", str(HERE / name)], cwd=str(ROOT),
                                     capture_output=True, timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                want = ref.stdout.decode("utf-8", "replace").replace("\r\n", "\n").rstrip("\n")
                ok(got == want, f"{name}: Sub Main output matches vbrun" + ("" if got == want else f"\n  native={got!r}\n  vbrun ={want!r}"))
        if not only:
            from radide.deploy.native import vb6_freebasic as N
            from radide.deploy.config import PublishConfig
            from radide.model import Project
            for nm, folder in UNSUPPORTED.items():
                reasons = N.check(folder, Project.load(folder), PublishConfig())
                ok(bool(reasons) and all(re.match(r"^[\w.]+(\(\d+\))?: ", r) or r.startswith("the update") for r in reasons),
                   f"{nm}: not translatable -> {len(reasons)} file(line) reasons, e.g. {reasons[0] if reasons else ''}")
    finally:
        print("\n".join(f"  {k}: {v // 1024} KB" for k, v in sizes.items()))
        print(f"\n{RESULTS['pass']}/{RESULTS['pass'] + RESULTS['fail']} checks passed")
        (report / "results.txt").write_text("\n".join(RESULTS["lines"]) + "\n\nsizes:\n" +
                                           "\n".join(f"{k}: {v} bytes" for k, v in sizes.items()), encoding="utf-8")
        try:
            from PyQt6.QtCore import QCoreApplication, QSettings
            if QCoreApplication.instance() is not None:
                QSettings().clear()
        except ImportError:
            pass
        if not keep:
            dst = HERE / "_last_report"
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(report, dst)
            shutil.rmtree(work, ignore_errors=True)
    return 0 if RESULTS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
