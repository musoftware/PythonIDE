"""FeatureMatrix on the native .NET WinForms build: animations, visual states and layout variants played by
RadMotion (radide/deploy/native/dotnet/RadWinForms.cs) - no fallback to the bridge build.

    .venv\\Scripts\\python samples/Tests/FeatureMatrix/check_fm_dotnet.py [csharp|powershell|all] [netfx|framework|standalone]

The project (fm_dotnet.write_project) is published with radide.deploy.build.build(); the build must be the native
.NET kind (native-net48 / native-sdk / native-standalone), the generated form must carry the motion records, then
the exe is driven on its own window by fm_drive.drive() (controls found by UI Automation AutomationId = the
WinForms control Name) - once normally (RADIDE_REDUCED_MOTION=0) and once with reduced motion."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent / "Native"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import ctypes  # noqa: E402

import _win as W  # noqa: E402
import fm_dotnet  # noqa: E402
import fm_drive  # noqa: E402
import winauto  # noqa: E402
from radide.deploy import build as B  # noqa: E402
from radide.deploy import config as C  # noqa: E402

_uia = None


def uia():
    global _uia
    if _uia is None:
        _uia = W.UIA()
    return _uia


def automation_id(h) -> str:
    try:
        return str(uia().uia.ElementFromHandle(h).CurrentAutomationId or "")
    except Exception:  # noqa: BLE001
        return ""


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.OpenProcess.restype = ctypes.c_void_p
_k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
_k32.VirtualAllocEx.restype = ctypes.c_void_p
_k32.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
_k32.VirtualFreeEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
_k32.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_SEND = ctypes.windll.user32.SendMessageTimeoutW
_SEND.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                  ctypes.POINTER(ctypes.c_size_t)]
_WM_GETCONTROLNAME = ctypes.windll.user32.RegisterWindowMessageW("WM_GETCONTROLNAME")


def control_names(hwnds, pid: int) -> dict:
    """{hwnd: WinForms Control.Name} with the WM_GETCONTROLNAME message every WinForms control answers (the
    buffer lives in the program's process); fast enough to sample a running load animation."""
    out = {}
    hp = _k32.OpenProcess(0x0008 | 0x0010 | 0x0020, 0, pid)        # VM_OPERATION | VM_READ | VM_WRITE
    if not hp:
        return out
    try:
        n = 512
        buf = _k32.VirtualAllocEx(hp, None, n * 2, 0x3000, 0x04)
        if not buf:
            return out
        try:
            for h in hwnds:
                r = ctypes.c_size_t(0)
                if not _SEND(h, _WM_GETCONTROLNAME, n, buf, 0x0002, 1000, ctypes.byref(r)):
                    continue
                local = ctypes.create_string_buffer(n * 2)
                got = ctypes.c_size_t(0)
                if _k32.ReadProcessMemory(hp, buf, local, n * 2, ctypes.byref(got)):
                    out[h] = local.raw.decode("utf-16-le", "replace").split("\0", 1)[0]
        finally:
            _k32.VirtualFreeEx(hp, buf, 0, 0x8000)
    finally:
        _k32.CloseHandle(hp)
    return out


def _pid(h) -> int:
    pid = ctypes.c_ulong()
    winauto.user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def find_controls(form, names):
    """{name: hwnd} of the form's child windows whose WinForms Control.Name (WM_GETCONTROLNAME; UI Automation
    AutomationId as the fallback) is wanted."""
    out = {}
    hs = []
    cb = winauto.WNDENUMPROC(lambda h, _l: hs.append(h) or True)
    winauto.user32.EnumChildWindows(form, cb, 0)
    by = control_names(hs, _pid(form))
    for h in hs:
        n = by.get(h) or (automation_id(h) if not by else "")
        if n in names:
            out.setdefault(n, h)
    return out


def form_window(pid: int, name: str, timeout=10.0):
    """The program's main form: its top-level window whose Control.Name is the form name."""
    return winauto.wait(lambda: next((h for h, n in control_names(winauto.top_windows(pid), pid).items() if n == name),
                                     None), timeout, 0.02)


def build(key: str, target: str, tmp: Path, rep: fm_drive.Report) -> Path | None:
    folder = fm_dotnet.write_project(key, tmp / f"fm_{key}", target)
    lines: list[str] = []
    res = B.build(folder, C.load(folder, folder.name), log=lines.append)
    log = "\n".join(lines)
    rep.ok("build is the native .NET kind (no fallback)", res.kind.startswith("native-"), (res.kind, lines[-12:]))
    gen = next(iter(folder.glob("_build/**/native-dotnet/src/RadForms.g.cs")), None) or \
        next(iter(tmp.rglob("RadForms.g.cs")), None)
    rep.ok("generated form carries the motion records (UseMotion)", gen is not None and "UseMotion(" in
           gen.read_text(encoding="utf-8-sig"), gen)
    rep.ok("no 'not translated' reason in the build log", "not translated" not in log, [l for l in lines if "translated" in l])
    exe = res.dist / res.exe
    return exe if res.kind.startswith("native-") and exe.is_file() else None


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "csharp"
    target = sys.argv[2] if len(sys.argv) > 2 else "netfx"
    keys = list(fm_dotnet.USER) if which == "all" else [which]
    winauto.form_window = form_window            # WinForms forms have no radforms.name property
    uia()                                        # UI Automation is slow to start: not while the load animation runs
    total = []
    with tempfile.TemporaryDirectory(prefix="fm_dotnet_") as t:
        for key in keys:
            rep = fm_drive.Report(f".NET {key} {target}")
            exe = build(key, target, Path(t), rep)
            if exe is not None:
                fm_drive.drive(exe, rep, find=find_controls)
                fm_drive.drive(exe, rep, env_extra={"RADIDE_REDUCED_MOTION": "1"}, find=find_controls)
            total += rep.rows
            fails = [f for f, ok, _ in rep.rows if not ok]
            print(f"[{rep.target}] {sum(ok for _, ok, _ in rep.rows)}/{len(rep.rows)} passed"
                  + (f"; failing: {fails}" if fails else ""), flush=True)
    ok = sum(1 for _, o, _ in total if o)
    print(f"\n{ok}/{len(total)} passed")
    return 0 if ok == len(total) else 1


if __name__ == "__main__":
    ctypes.windll.user32.SetProcessDPIAware()
    sys.exit(main())
