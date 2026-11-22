# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Run the VB6 business samples (samples/VB6/Business) in RAD IDE's VB6 runtime and drive their workflows.

    .venv\\Scripts\\python samples\\Tests\\VB6Business\\test_vb6_business.py [SampleName ...]

For every sample (each in its own process, on a temporary copy so the .mdb files in the repo stay unchanged):
* designer check - every form loads through the VB6 importer (radide.foreign.vb6_project.NativeVB6) with
  all its controls (no "not available" / "skipped" warnings, control count = Begin blocks in the .frm);
* runtime check - radide.runtimes.vbrun.Runtime loads the project and a scripted user signs in, adds
  records, reads them back from grids/lists, runs the calculations and opens the report / export paths.
MsgBox / InputBox answers are scripted; any VB run-time error fails the sample.  Prints ok/FAIL per check and
exits 0 when everything passed.  QSettings "RADIDE-TEST" is cleared before and after; QT_QPA_PLATFORM=offscreen,
RADIDE_NO_BROWSER=1.  Windows windows are moved off-screen; nothing is captured from the screen.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SAMPLES = ROOT / "samples" / "VB6" / "Business"
NAMES = ["BankManager", "ElectricityBilling", "FinanceLedger", "ScientificCalculator", "ClinicManager",
         "LogicGateLab", "PharmacyStore", "OnlineExam"]
FAILS: list[str] = []
PASSES: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    (PASSES if cond else FAILS).append(msg)
    return bool(cond)


# ============================================================================ child side: a scripted VB6 user
class Driver:
    """Drives a VB6 project loaded by radide.runtimes.vbrun.Runtime without a real user."""

    def __init__(self, vbp: Path):
        sys.path.insert(0, str(ROOT))
        import tkinter
        from radide.runtimes.vbrun import Runtime
        tkinter.Misc.wait_window = lambda self, w=None: None          # vbModal must not block the script
        tkinter.Misc.grab_set = lambda self: None
        self.rt = rt = Runtime(vbp)
        self.folder = vbp.parent
        self.msgs: list[str] = []
        self.answers: list = []          # scripted MsgBox results (vbYes = 6 ...) / InputBox strings
        self.errors: list[str] = []
        self.ended = False

        def msgbox(prompt, buttons, title):
            self.msgs.append(str(prompt))
            print(f"    [MsgBox] {prompt!s}".replace("\r\n", " | ").replace("\n", " | "), flush=True)
            kind = int(buttons) & 7
            if self.answers and kind in (1, 3, 4, 5):
                return self.answers.pop(0)
            return 6 if kind in (3, 4) else 1

        def inputbox(prompt, title, default):
            ans = self.answers.pop(0) if self.answers else default
            print(f"    [InputBox] {prompt} -> {ans!r}", flush=True)
            return ans

        def runtime_error(ex):
            text = f"{getattr(ex, 'module', '')}({getattr(ex, 'line', '')}): {ex.number} {ex.description}"
            self.errors.append(text)
            print("    [RUNTIME ERROR] " + text, flush=True)

        def end():
            self.ended = True
            raise _Ended()
        rt.msgbox, rt.inputbox, rt.runtime_error, rt.end = msgbox, inputbox, runtime_error, end
        rt.fatal = lambda text, filename="", line=0: self.errors.append(text) or print("    [FATAL] " + text)
        rt.load()
        from radide.runtimes.vbrun import Clipboard

        class _Clip(Clipboard):                      # the user's real clipboard is never touched
            text = ""

            def vb_call(self, name, args):
                if name == "settext":
                    _Clip.text = str(args[0])
                elif name == "gettext":
                    return _Clip.text
                elif name == "clear":
                    _Clip.text = ""
                return ""
        rt.interp.objects["clipboard"] = _Clip(rt)
        self.shelled: list[str] = []                 # Shell "notepad ..." is recorded, never started
        rt.interp.builtins["shell"] = lambda *a: self.shelled.append(str(a[0]) if a else "") or 1234

    # -- starting
    def start(self):
        rt = self.rt
        start = (rt.project.startup or "").lower()
        if start in ("sub main", "main") or start not in rt.forms:
            found = rt.interp.find_proc("main", None)
            self._guard(lambda: rt.interp.call_proc(found[0], found[1], []))
        else:
            vf = rt.forms[start]
            self._guard(lambda: (vf.load(), vf.vb_call("show", [])))
        self.offscreen()

    def _guard(self, fn):
        from radide.runtimes.vbinterp import VBRuntimeError
        try:
            return fn()
        except _Ended:
            return None
        except VBRuntimeError as ex:
            self.rt.runtime_error(ex)
        return None

    def offscreen(self):
        for vf in self.rt.forms.values():
            if vf.loaded and vf.ui is not None:
                try:
                    vf.ui.root.geometry("+-4000+-4000")
                except Exception:  # noqa: BLE001
                    pass

    def pump(self, ms=100):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            if self.rt.root is not None:
                try:
                    self.rt.root.update()
                except Exception:  # noqa: BLE001
                    return
            time.sleep(0.005)
        self.offscreen()

    def wait_for(self, cond, timeout_ms=8000):
        end = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < end:
            if cond():
                return True
            self.pump(30)
        return cond()

    # -- forms and controls
    def form(self, name):
        return self.rt.forms[name.lower()]

    def loaded(self, name):
        return self.rt.forms[name.lower()].loaded

    def ctl(self, form, name, index=None):
        vf = self.form(form)
        c = vf.vb_get(name.lower())
        if index is not None:
            c = c.vb_index([index])
        return c

    def get(self, form, name, prop="text", index=None):
        return self._guard(lambda: self.ctl(form, name, index).vb_get(prop.lower()))

    def fprop(self, form, prop):
        """A property of the form itself (Caption, Visible ...)."""
        return self._guard(lambda: self.form(form).vb_get(prop.lower()))

    def set(self, form, name, value, prop="text", index=None):
        self._guard(lambda: self.ctl(form, name, index).vb_set(prop.lower(), value))

    def event(self, form, proc, *args, index=None, event="Click"):
        vf = self.form(form)
        if not vf.loaded:
            vf.load()
        self._guard(lambda: self.rt.run_handler(vf, proc, event, *args, index=index))
        self.pump(20)

    def click(self, form, name, index=None):
        self.event(form, f"{name}_Click", index=index)

    def keypress(self, form, name, ch):
        """Run <name>_KeyPress with KeyAscii = ch; returns the KeyAscii the handler left."""
        from radide.runtimes.vbinterp import Cell
        vf = self.form(form)
        cell = Cell(ord(ch))
        self._guard(lambda: self.rt.interp.call_by_name(vf.name, f"{name}_KeyPress", [cell.value], me=vf,
                                                        arg_cells=[cell]))
        return int(cell.value)

    def call(self, module, proc, *args):
        vf = self.rt.forms.get(module.lower())
        r = self._guard(lambda: self.rt.interp.call_by_name(vf.name if vf else module, proc, list(args), me=vf))
        self.pump(20)
        return r[1] if isinstance(r, tuple) else r

    def value(self, v):
        """A VB value (Field / Variant) as Python."""
        return v.Value if hasattr(v, "Value") and not isinstance(v, (str, int, float)) else v

    def grid(self, form, name):
        """MSFlexGrid cells as a list of rows (header first)."""
        g = self.ctl(form, name)
        rows, cols = int(g.vb_get("rows")), int(g.vb_get("cols"))
        return [[str(g.vb_call("textmatrix", [r, c])) for c in range(cols)] for r in range(rows)]

    def listview(self, form, name):
        lv = self.ctl(form, name)
        w = lv.w
        return [list(map(str, w.item(i, "values"))) for i in w.get_children()]

    def listbox(self, form, name):
        c = self.ctl(form, name)
        if c.type == "ListBox":
            return list(c.w.get(0, "end"))
        return list(c.w.cget("values") or ())

    def query(self, sql):
        """Rows of an SQL query on the sample's own database (through radide/runtimes/vbado.py)."""
        from radide.runtimes import vbado
        conn = None
        cells = list(self.rt.interp.globals.values())
        for st in self.rt.interp.modules.values():
            cells += list(st.vars.values())
        for cell in cells:                           # the program's own connection (sees its own writes)
            v = getattr(cell, "value", None)
            if isinstance(v, vbado.Database):
                v = v._conn
            if isinstance(v, vbado.Connection) and v.State:
                conn = v
                break
        if conn is None:
            mdb = next(self.folder.glob("*.mdb"))
            conn = vbado.Connection(f"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={mdb}")
            conn.Open()
        rs = conn.Execute(sql)
        out = [list(r) for r in rs._rows]
        rs.Close()
        return out


class _Ended(Exception):
    pass


def designer_check(vbp: Path):
    """Every form opens in the designer through the VB6 importer, with every control it declares."""
    sys.path.insert(0, str(ROOT))
    from radide.foreign.vb6_project import NativeVB6
    work = Path(tempfile.mkdtemp(prefix="vb6biz-designer-"))
    try:
        _designer_check(vbp, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _designer_check(vbp: Path, work: Path):
    from radide.foreign.vb6_project import NativeVB6
    native = NativeVB6(vbp, work / "frx")
    proj = native.project()
    names = native.form_names()
    check(len(names) == len(proj.forms) and names, f"{vbp.stem}: designer lists {len(names)} forms")
    from radide.foreign.vb6_project import build_mirror
    from radide.model import Form, Project
    mdir, _n = build_mirror(vbp, work / "mirror")                            # what File > Open Project does
    mp = Project.load(mdir)
    reopened = [Form.load(mp.form_path(n)) for n in mp.forms]
    check(len(reopened) == len(names) and all(f.controls for f in reopened),
          f"{vbp.stem}: File > Open Project mirror has {len(reopened)} editable forms")
    for nf in native.forms.values():
        text = nf.path.read_text(encoding="cp1252", errors="replace")
        head = text.split("Attribute VB_Name")[0]
        begins = [m for m in re.findall(r"^\s*Begin\s+(\S+)\s+(\w+)", head, re.M)[1:]
                  if m[0].lower() != "vb.menu"]
        menus = len(re.findall(r"^\s*Begin\s+VB\.Menu\s", head, re.M))
        form = native.form(nf.name)
        ctrls = [c for c in form.controls if c.type != "MenuStrip"]
        bad = [w for w in nf.warnings if "not available" in w or "skipped" in w or "no equivalent" in w]
        check(len(ctrls) == len(begins) and not bad,
              f"{vbp.stem}/{nf.name}: {len(ctrls)}/{len(begins)} controls in the designer"
              + (f", {menus} menu items" if menus else "") + (f" - {bad}" if bad else ""))
        if menus:
            m = form.menu()
            n = 0
            stack = list(m.props.get("Items", [])) if m else []
            while stack:
                it = stack.pop()
                n += 1
                stack += it.get("Items", [])
            check(n == menus, f"{vbp.stem}/{nf.name}: menu has {n}/{menus} items")


def child(name: str) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    tmp = Path(tempfile.mkdtemp(prefix=f"vb6biz-{name}-"))
    shutil.copytree(SAMPLES / name, tmp / name)
    vbp = next((tmp / name).glob("*.vbp"))
    try:
        designer_check(vbp)
        import scenarios                                   # noqa: E402  (samples/Tests/VB6Business/scenarios.py)
        d = Driver(vbp)
        getattr(scenarios, name)(d, check)
        check(not d.errors, f"{name}: no VB run-time errors" + (f" ({d.errors})" if d.errors else ""))
    finally:
        try:
            from radide.runtimes.vbado import _close_all
            _close_all()
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if FAILS else 0)


# ============================================================================ parent side
def clear_settings():
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        try:
            from PyQt6.QtCore import QSettings
        except ImportError:
            return
    s = QSettings("RADIDE-TEST", "RADIDE-TEST")
    s.clear()
    s.sync()


def main(argv) -> int:
    if len(argv) >= 2 and argv[0] == "--child":
        sys.path.insert(0, str(HERE))
        return child(argv[1])
    names = argv or NAMES
    clear_settings()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", RADIDE_NO_BROWSER="1", PYTHONIOENCODING="utf-8")
    summary = []
    for name in names:
        if not (SAMPLES / name).is_dir():
            check(False, f"{name}: sample folder missing")
            continue
        print(f"=== {name}", flush=True)
        t0 = time.monotonic()
        try:
            p = subprocess.run([sys.executable, __file__, "--child", name], env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=600)
            out, code = (p.stdout or "") + (p.stderr or ""), p.returncode
        except subprocess.TimeoutExpired as ex:
            out, code = str(ex.stdout or ""), -1
        ok = bad = 0
        for line in out.splitlines():
            if line.startswith("ok   "):
                ok += 1
                PASSES.append(line)
            elif line.startswith("FAIL "):
                bad += 1
                FAILS.append(line)
            if line.startswith(("ok", "FAIL", "    [RUNTIME", "    [FATAL", "Traceback", "  File", "    ")) or \
                    "Error" in line:
                print(line, flush=True)
        if code != 0 and bad == 0:
            check(False, f"{name}: child exited with {code}\n" + "\n".join(out.splitlines()[-20:]))
            bad += 1
        summary.append(f"{name}: {ok} passed, {bad} failed ({time.monotonic() - t0:.0f}s)")
    clear_settings()
    print("\n".join(summary))
    print(f"TOTAL: {len(PASSES)} passed, {len(FAILS)} failed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
