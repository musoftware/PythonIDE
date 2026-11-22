"""Accessibility of the programs the IDE produces.

1. Native radforms exe (C, samples/Tests/Accessibility/NativeForm, published with radide.deploy.build): started and
   driven with window messages only (never the user's keyboard or mouse):
     * tab order = TabIndex (the controls are listed out of order in the .form on purpose)
     * Space / Enter activate the focused button / check box, Alt+O (a button's "&OK"), Alt+N (a label's "&Name:"
       moves the focus to the next field), Space on an Rm toggle
     * UI Automation (comtypes, the MSAA proxy screen readers use): standard controls named by their text / label,
       a list named by code (AccessibleName / AccessibleDescription), the Rm controls with name + control type
       (button, check box with toggle state, slider and progress bar with their value, the text box by its watermark)
2. RadIDE.Controls (.NET, radide/runtimes/dotnet/RadIDE.Controls): the accessible objects of the Rm classes - roles,
   names (a text box is named by AccessibleName / watermark / Name, not by its content) and values - read by
   UI Automation from a small WinForms program built against the library (skipped when no .NET SDK is installed).

Only the processes this test starts are touched. Exit code = failures.

    .venv\\Scripts\\python samples\\Tests\\Accessibility\\test_native_a11y.py [scratch folder]
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes as wt
from pathlib import Path

os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "samples" / "Tests" / "Native"))

import winauto as w  # noqa: E402

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_a11y_native_"))
SCRATCH.mkdir(parents=True, exist_ok=True)
RESULTS: list[tuple[str, bool, str]] = []
T0 = time.time()

WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_SYSKEYDOWN, WM_SYSKEYUP, WM_SYSCHAR = 0x100, 0x101, 0x102, 0x104, 0x105, 0x106
VK_TAB, VK_RETURN, VK_SPACE, VK_SHIFT, VK_MENU = 0x09, 0x0D, 0x20, 0x10, 0x12
BM_GETCHECK = 0xF0
# UIA control types
CT = {"Button": 50000, "CheckBox": 50002, "ComboBox": 50003, "Edit": 50004, "List": 50008, "ProgressBar": 50012,
      "Slider": 50015, "Text": 50020, "Group": 50026, "Pane": 50033, "Custom": 50025}


def check(name: str, ok, detail="") -> bool:
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:600]}]" if detail and not ok else ""), flush=True)
    return bool(ok)


def info(t: str) -> None:
    print("INFO " + t, flush=True)


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hwndActive", wt.HWND), ("hwndFocus", wt.HWND),
                ("hwndCapture", wt.HWND), ("hwndMenuOwner", wt.HWND), ("hwndMoveSize", wt.HWND),
                ("hwndCaret", wt.HWND), ("rcCaret", wt.RECT)]


user32 = w.user32
user32.GetGUIThreadInfo.argtypes = [wt.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetParent.argtypes = [wt.HWND]
user32.GetParent.restype = wt.HWND
user32.GetNextDlgTabItem.argtypes = [wt.HWND, wt.HWND, wt.BOOL]
user32.GetNextDlgTabItem.restype = wt.HWND


def focus_of(hwnd: int) -> int:
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    gi = GUITHREADINFO()
    gi.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not user32.GetGUIThreadInfo(tid, ctypes.byref(gi)):
        return 0
    return int(gi.hwndFocus or 0)


def set_focus(form: int, h: int) -> None:
    """Focus a control of the started program the way a click would, without touching the user's foreground window:
    attach to its input queue for the SetFocus call (the program's window does not have to be in front)."""
    k32 = ctypes.windll.kernel32
    tid = user32.GetWindowThreadProcessId(form, None)
    me = k32.GetCurrentThreadId()
    attached = user32.AttachThreadInput(me, tid, True)
    try:
        user32.SetFocus(wt.HWND(h))
    finally:
        if attached:
            user32.AttachThreadInput(me, tid, False)
    time.sleep(0.15)


def moved_from(form: int, old: int, timeout: float = 2.0) -> int:
    """The focus once it left *old* (the program processes the posted keys asynchronously)."""
    f = w.wait(lambda: (lambda x: x if x and x != old else None)(focus_of(form)), timeout) or focus_of(form)
    time.sleep(0.1)
    return focus_of(form) or f


def owner_name(h: int, form: int) -> str:
    """radforms name of a window or of its nearest named parent (the edit inside an Rm text box)."""
    while h and h != form:
        n = w.rf_name(h)
        if n:
            return n
        h = int(user32.GetParent(h) or 0)
    return ""


def post_key(h: int, vk: int, shift: bool = False) -> None:
    if shift:                  # the dialog manager reads GetKeyState(VK_SHIFT): set it in the program's input state
        shift_tab(h)
        return
    user32.PostMessageW(h, WM_KEYDOWN, vk, 1)
    if vk == VK_SPACE:
        user32.PostMessageW(h, WM_CHAR, 0x20, 1)
    user32.PostMessageW(h, WM_KEYUP, vk, 0xC0000001)


def shift_tab(h: int) -> None:
    """Shift+Tab: while attached to the program's input queue (shared key state - not the user's foreground
    program) Shift is marked down, Tab is posted and processed, then Shift is released again."""
    k32 = ctypes.windll.kernel32
    tid = user32.GetWindowThreadProcessId(h, None)
    me = k32.GetCurrentThreadId()
    attached = user32.AttachThreadInput(me, tid, True)
    state = (ctypes.c_ubyte * 256)()
    try:
        user32.GetKeyboardState(state)
        state[VK_SHIFT] = 0x80
        user32.SetKeyboardState(state)
        user32.PostMessageW(h, WM_KEYDOWN, VK_TAB, 1)
        user32.PostMessageW(h, WM_KEYUP, VK_TAB, 0xC0000001)
        time.sleep(0.25)
    finally:
        state[VK_SHIFT] = 0
        user32.SetKeyboardState(state)
        if attached:
            user32.AttachThreadInput(me, tid, False)


def post_alt(h: int, ch: str) -> None:
    """Alt+<letter> as the dialog manager sees it (WM_SYSCHAR with the context bit)."""
    vk = ord(ch.upper())
    user32.PostMessageW(h, WM_SYSKEYDOWN, vk, 0x20000001)
    user32.PostMessageW(h, WM_SYSCHAR, ord(ch.lower()), 0x20000001)
    user32.PostMessageW(h, WM_SYSKEYUP, vk, 0xE0000001)


def uia():
    import comtypes.client
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as U
    return U, comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=U.IUIAutomation)


def legacy(U, el):
    try:
        return el.GetCurrentPattern(U.UIA_LegacyIAccessiblePatternId).QueryInterface(U.IUIAutomationLegacyIAccessiblePattern)
    except Exception:  # noqa: BLE001
        return None


def el_info(U, auto, h: int) -> dict:
    el = auto.ElementFromHandle(h)
    lg = legacy(U, el)
    out = {"name": el.CurrentName or "", "type": int(el.CurrentControlType), "help": el.CurrentHelpText or "",
           "value": "", "state": 0, "desc": "", "focusable": bool(el.CurrentIsKeyboardFocusable)}
    if lg is not None:
        try:
            out["value"] = lg.CurrentValue or ""
            out["state"] = int(lg.CurrentState)
            out["desc"] = lg.CurrentDescription or ""
            out["role"] = int(lg.CurrentRole)
        except Exception:  # noqa: BLE001
            pass
    return out


# =========================================================================== 1. native radforms exe
def build_native() -> Path | None:
    from radide.deploy import build
    from radide.deploy.config import PublishConfig
    src = SCRATCH / "NativeForm"
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(HERE / "NativeForm", src)
    out = SCRATCH / "publish_native"
    shutil.rmtree(out, ignore_errors=True)
    cfg = PublishConfig(app_name="NativeForm", version="1.0.0", publisher="Musoftware", output_dir=str(out))
    log: list[str] = []
    try:
        res = build.build(src, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        check("native: build", False, f"{e}\n" + "\n".join(log[-20:]))
        return None
    exe = res.dist / res.exe
    check("native: one native exe (radforms, no Python)", res.kind == "native" and exe.is_file(), res.kind + "\n" + "\n".join(log[-10:]))
    return exe if exe.is_file() else None


def native_tests() -> None:
    exe = build_native()
    if exe is None:
        return
    proc = w.start(exe)
    form = None
    try:
        form = w.form_window(proc.pid, "Form1", 15)
        check("native: the form window opened", form)
        if not form:
            return
        time.sleep(0.6)
        c = w.wait(lambda: (lambda d: d if len(d) >= 10 else None)(w.children(form)), 8) or w.children(form)
        check("native: controls found by name", {"btnOK", "txtName", "chkAgree", "lstItems", "rmSave", "tgDark",
                                                 "slVolume", "pbLoad", "rmSearch"} <= set(c), sorted(c))
        # ---------------------------------------------------------------- tab order = TabIndex
        expected = ["txtName", "chkAgree", "btnOK", "lstItems", "rmSave", "tgDark", "slVolume", "rmSearch"]
        set_focus(form, c["txtName"])
        start = focus_of(form)
        check("native: the first field takes the focus", owner_name(start, form) == "txtName",
              (start, owner_name(start, form)))
        # the order of the dialog manager (GetNextDlgTabItem - what IsDialogMessage uses for Tab / Shift+Tab)
        seq, h = ["txtName"], c["txtName"]
        for _ in range(len(expected)):
            h = int(user32.GetNextDlgTabItem(form, h, False) or 0)
            seq.append(owner_name(h, form))
        check("native: Tab order follows TabIndex (not the order in the .form), the label and progress bar are skipped",
              seq == expected + ["txtName"], seq)
        back, h = ["txtName"], c["txtName"]
        for _ in range(3):
            h = int(user32.GetNextDlgTabItem(form, h, True) or 0)
            back.append(owner_name(h, form))
        check("native: Shift+Tab order is the reverse", back == ["txtName", "rmSearch", "slVolume", "tgDark"], back)

        def key_moves(start: str, want: str, shift: bool) -> str:
            """A Tab posted to the program (its message loop runs IsDialogMessage). Retried when another program's
            window took the activation meanwhile (busy test machines): the focus is set again first."""
            got = ""
            for _ in range(3):
                set_focus(form, c[start])
                post_key(c[start], VK_TAB, shift=shift)
                got = owner_name(moved_from(form, c[start]), form)
                if got == want:
                    break
            return got
        got = key_moves("txtName", "chkAgree", False)
        check("native: a Tab key moves the focus to the next field", got == "chkAgree", got)
        got = key_moves("txtName", "rmSearch", True)
        check("native: a Shift+Tab key moves the focus back (to the edit of RmTextBox)", got == "rmSearch", got)
        # ---------------------------------------------------------------- activation with keys
        set_focus(form, c["chkAgree"])
        post_key(c["chkAgree"], VK_SPACE)
        ok = w.wait(lambda: user32.SendMessageW(c["chkAgree"], BM_GETCHECK, 0, 0) == 1, 3)
        check("native: Space toggles the focused check box", ok, user32.SendMessageW(c["chkAgree"], BM_GETCHECK, 0, 0))
        set_focus(form, c["btnOK"])
        post_key(c["btnOK"], VK_SPACE)
        check("native: Space presses the focused button (Click)", w.wait(lambda: w.get_text(c["lblOut"]) == "OK 1", 3),
              w.get_text(c["lblOut"]))
        post_key(c["btnOK"], VK_RETURN)
        check("native: Enter presses the focused button", w.wait(lambda: w.get_text(c["lblOut"]) == "OK 2", 3),
              w.get_text(c["lblOut"]))
        set_focus(form, c["txtName"])
        post_alt(focus_of(form) or c["txtName"], "o")
        check("native: Alt+O (button '&OK') clicks it from another field", w.wait(lambda: w.get_text(c["lblOut"]) == "OK 3", 3),
              w.get_text(c["lblOut"]))
        moved = False
        for _ in range(3):
            set_focus(form, c["lstItems"])
            post_alt(c["lstItems"], "n")
            moved = w.wait(lambda: owner_name(focus_of(form), form) == "txtName", 2)
            if moved:
                break
        check("native: Alt+N (label '&Name:') moves the focus to the text box after it", moved, owner_name(focus_of(form), form))
        set_focus(form, c["rmSave"])
        post_key(c["rmSave"], VK_SPACE)
        check("native: Space presses the focused RmButton", w.wait(lambda: w.get_text(c["lblOut"]) == "saved", 3),
              w.get_text(c["lblOut"]))
        set_focus(form, c["tgDark"])
        post_key(c["tgDark"], VK_SPACE)
        check("native: Space switches the focused RmToggle (CheckedChanged -> True)",
              w.wait(lambda: w.get_text(c["lblOut"]) == "True", 3), w.get_text(c["lblOut"]))
        toggled = w.get_text(c["lblOut"]) == "True"
        # ---------------------------------------------------------------- UI Automation
        try:
            U, auto = uia()
        except Exception as e:  # noqa: BLE001
            check("native: UI Automation available (comtypes)", False, e)
            return
        I = {n: el_info(U, auto, c[n]) for n in ("btnOK", "txtName", "chkAgree", "lstItems", "rmSave", "tgDark",
                                                 "slVolume", "pbLoad", "rmSearch")}
        check("UIA: button '&OK' -> Button 'OK'", I["btnOK"]["type"] == CT["Button"] and I["btnOK"]["name"] == "OK", I["btnOK"])
        check("UIA: check box -> CheckBox 'I agree'", I["chkAgree"]["type"] == CT["CheckBox"] and I["chkAgree"]["name"] == "I agree",
              I["chkAgree"])
        check("UIA: text box named by its label ('Name')", I["txtName"]["type"] == CT["Edit"] and
              I["txtName"]["name"].rstrip(":") == "Name", I["txtName"])
        check("UIA: list named by code (AccessibleName)", I["lstItems"]["type"] == CT["List"] and
              I["lstItems"]["name"] == "Items list", I["lstItems"])
        check("UIA: list description (AccessibleDescription)", "Pick one item" in (I["lstItems"]["desc"] + I["lstItems"]["help"]),
              I["lstItems"])
        check("UIA: RmButton -> Button 'Save'", I["rmSave"]["type"] == CT["Button"] and I["rmSave"]["name"] == "Save", I["rmSave"])
        check("UIA: RmToggle -> CheckBox 'Dark mode'", I["tgDark"]["type"] == CT["CheckBox"] and I["tgDark"]["name"] == "Dark mode",
              I["tgDark"])
        check("UIA: RmToggle reports its checked state", bool(I["tgDark"]["state"] & 0x10) == toggled, hex(I["tgDark"]["state"]))
        check("UIA: RmSlider -> Slider with its value", I["slVolume"]["type"] == CT["Slider"] and I["slVolume"]["value"] == "35"
              and I["slVolume"]["name"] == "slVolume", I["slVolume"])
        check("UIA: RmProgress -> ProgressBar with its value", I["pbLoad"]["type"] == CT["ProgressBar"] and
              I["pbLoad"]["value"] == "60", I["pbLoad"])
        check("UIA: RmTextBox named by its watermark", I["rmSearch"]["name"] == "Search", I["rmSearch"])
        inner = next((h for h in [user32.FindWindowExW(c["rmSearch"], None, "Edit", None)] if h), 0)
        if inner:
            ii = el_info(U, auto, inner)
            check("UIA: the edit inside RmTextBox (focus target) is named too", ii["name"] == "Search" and ii["type"] == CT["Edit"], ii)
        set_focus(form, c["tgDark"])
        post_key(c["tgDark"], VK_SPACE)
        time.sleep(0.4)
        w.wait(lambda: w.get_text(c["lblOut"]) == ("False" if toggled else "True"), 3)
        now = w.get_text(c["lblOut"]) == "True"
        st = el_info(U, auto, c["tgDark"])["state"]
        check("UIA: the toggle state follows the control (switched again)", bool(st & 0x10) == now and now != toggled,
              (hex(st), now, toggled))
        named = [n for n, v in I.items() if v["name"]]
        info("UIA names: " + ", ".join(f"{n}={I[n]['name']!r}" for n in named))
    finally:
        w.stop(proc, form)


# =========================================================================== 2. RadIDE.Controls (.NET)
CS_PROGRAM = r"""
using System;
using System.Drawing;
using System.Windows.Forms;
using RadIDE.Controls;

static class Program
{
    [STAThread]
    static void Main()
    {
        Application.EnableVisualStyles();
        var f = new Form { Text = "RmA11y", Name = "FormA11y", ClientSize = new Size(560, 300) };
        var lbl = new Label { Name = "lblOut", Text = "ready", Location = new Point(10, 260), Size = new Size(300, 20) };
        var b = new RmButton { Name = "rmSave", Text = "Save", Location = new Point(10, 10), Size = new Size(120, 32), TabIndex = 0 };
        b.Click += (s, e) => lbl.Text = "saved";
        var t = new RmToggle { Name = "tgDark", Text = "Dark mode", Location = new Point(150, 14), Size = new Size(160, 26), TabIndex = 1 };
        var tb = new RmTextBox { Name = "rmSearch", Watermark = "Search", Location = new Point(10, 60), Size = new Size(200, 30), TabIndex = 2 };
        tb.Text = "typed content";
        var sl = new RmSlider { Name = "slVolume", Location = new Point(10, 110), Size = new Size(220, 46), TabIndex = 3 };
        sl.Value = 35;
        var pb = new RmProgress { Name = "pbLoad", Location = new Point(260, 120), Size = new Size(200, 20) };
        pb.Value = 60;
        var gg = new RmGauge { Name = "ggCpu", Location = new Point(260, 160), Size = new Size(90, 90) };
        gg.Value = 42;
        var dp = new RmDatePicker { Name = "dpWhen", Location = new Point(10, 170), Size = new Size(160, 30), TabIndex = 4 };
        dp.Value = new DateTime(2026, 11, 22);
        var cb = new RmCheckBox { Name = "chkAgree", Text = "I agree", Location = new Point(10, 215), Size = new Size(160, 26), TabIndex = 5 };
        f.Controls.AddRange(new Control[] { b, t, tb, sl, pb, gg, dp, cb, lbl });
        Application.Run(f);
    }
}
"""


def dotnet_tests() -> None:
    dotnet = shutil.which("dotnet")
    if not dotnet:
        info(".NET part skipped: no dotnet SDK on PATH")
        return
    lib = REPO / "radide" / "runtimes" / "dotnet" / "RadIDE.Controls"
    work = SCRATCH / "RmA11y"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    (work / "Program.cs").write_text(CS_PROGRAM, encoding="utf-8")
    (work / "RmA11y.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWindowsForms>true</UseWindowsForms>
    <Nullable>disable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="Program.cs" />
    <Compile Include="{lib / 'src'}\\*.cs" />
  </ItemGroup>
</Project>
""", encoding="utf-8")
    r = subprocess.run([dotnet, "build", "-c", "Release", "-nologo", "-v", "q", "-o", str(work / "out")], cwd=str(work),
                       capture_output=True, text=True, timeout=600)
    exe = work / "out" / "RmA11y.exe"
    if not check(".NET: a WinForms program builds with RadIDE.Controls", r.returncode == 0 and exe.is_file(),
                 (r.stdout + r.stderr)[-1500:]):
        return
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        sys.path.insert(0, str(REPO / "samples" / "Tests" / "Native"))
        import _win as W
        main = W.wait(lambda: next((h for h in W.top_windows(proc.pid) if W.text(h) == "RmA11y"), None), 30)
        check(".NET: the window opened", main)
        if not main:
            return
        time.sleep(1.0)
        U, auto = uia()
        root = auto.ElementFromHandle(main)

        def by_id(aid):
            cond = auto.CreatePropertyCondition(U.UIA_AutomationIdPropertyId, aid)
            try:
                el = root.FindFirst(U.TreeScope_Descendants, cond)
            except Exception:  # noqa: BLE001
                return None
            return el if el else None

        def inf(aid):
            el = by_id(aid)
            if el is None:
                return {}
            lg = legacy(U, el)
            d = {"name": el.CurrentName or "", "type": int(el.CurrentControlType)}
            try:
                d["value"] = lg.CurrentValue or ""
                d["state"] = int(lg.CurrentState)
            except Exception:  # noqa: BLE001
                d["value"], d["state"] = "", 0
            return d
        I = {n: inf(n) for n in ("rmSave", "tgDark", "rmSearch", "slVolume", "pbLoad", "ggCpu", "dpWhen", "chkAgree")}
        check(".NET UIA: RmButton -> Button 'Save'", I["rmSave"].get("type") == CT["Button"] and I["rmSave"].get("name") == "Save", I["rmSave"])
        check(".NET UIA: RmToggle -> CheckBox 'Dark mode'", I["tgDark"].get("type") == CT["CheckBox"] and
              I["tgDark"].get("name") == "Dark mode", I["tgDark"])
        check(".NET UIA: RmCheckBox -> CheckBox 'I agree'", I["chkAgree"].get("type") == CT["CheckBox"] and
              I["chkAgree"].get("name") == "I agree", I["chkAgree"])
        check(".NET UIA: RmTextBox named by its watermark, not by its content", I["rmSearch"].get("name") == "Search", I["rmSearch"])
        inner = None
        el = by_id("rmSearch")
        if el is not None:
            cond = auto.CreatePropertyCondition(U.UIA_ControlTypePropertyId, CT["Edit"])
            inner = el.FindFirst(U.TreeScope_Descendants, cond)
        check(".NET UIA: the inner edit of RmTextBox (focus target) is named 'Search'", inner is not None and inner.CurrentName == "Search",
              inner.CurrentName if inner else None)
        check(".NET UIA: RmSlider -> Slider with value 35", I["slVolume"].get("type") == CT["Slider"] and I["slVolume"].get("value") == "35",
              I["slVolume"])
        check(".NET UIA: RmProgress -> ProgressBar with value 60", I["pbLoad"].get("type") == CT["ProgressBar"] and
              I["pbLoad"].get("value") == "60", I["pbLoad"])
        check(".NET UIA: RmGauge -> ProgressBar with value 42", I["ggCpu"].get("type") == CT["ProgressBar"] and
              I["ggCpu"].get("value") == "42", I["ggCpu"])
        check(".NET UIA: RmDatePicker -> ComboBox whose value is the date", I["dpWhen"].get("type") == CT["ComboBox"] and
              "2026" in I["dpWhen"].get("value", "") and I["dpWhen"].get("name") == "dpWhen", I["dpWhen"])
    finally:
        try:
            proc.terminate()
            proc.wait(10)
        except Exception:  # noqa: BLE001
            proc.kill()


native_tests()
dotnet_tests()
fails = [r for r in RESULTS if not r[1]]
print(f"\nAccessibility / produced programs: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed, {len(fails)} failed "
      f"({time.time() - T0:.0f} s)", flush=True)
for n, _ok, d in fails:
    print(f"  FAILED: {n}  {d[:300]}")
sys.exit(len(fails))
