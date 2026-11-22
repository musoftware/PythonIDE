"""Shared pieces of the E2E journeys: environment (build, portable copy, hidden desktop), IDE start-up, and the
"hello app" flow every desktop language goes through (new project -> Toolbox -> Properties -> handler ->
IntelliSense -> F5 -> click in the running program -> stop -> publish -> run the published exe)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from radauto import IDE, AutomationError, Report, Skip, check

HERE = Path(__file__).resolve().parent


@dataclass
class Env:
    scratch: Path
    onedir: Path | None = None          # the built onedir (dist/RADIDE) - copied, never run in place
    setup: Path | None = None           # RADIDE-x.y.z-setup-win64.exe
    desktop: str = "RADIDE_E2E"
    app: Path | None = None             # portable copy: <scratch>/app/RADIDE/RADIDE.exe
    source: bool = False                # run `python -m radide` instead (developing journeys)
    out: Path = field(default=None)     # reports / screenshots

    def exe(self) -> list[str] | str:
        if self.source:
            repo = HERE.parent.parent.parent
            return [str(repo / ".venv" / "Scripts" / "python.exe"), "-m", "radide", "--new-window"]
        return str(self.app / "RADIDE.exe")


def robocopy(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["robocopy", str(src), str(dst), "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1",
                        "/W:1", "/XD", "settings"], capture_output=True, text=True)
    if r.returncode >= 8:
        raise RuntimeError(f"robocopy failed ({r.returncode}): {r.stdout[-2000:]}")


def portable_copy(env: Env, fresh: bool = False) -> Path:
    """<scratch>/app/RADIDE = the onedir + portable.flag (settings in <copy>/settings, never the user's)."""
    if env.source:
        return None
    dst = env.scratch / "app" / "RADIDE"
    if fresh and (dst / "settings").exists():
        shutil.rmtree(dst / "settings", ignore_errors=True)
    if not (dst / "RADIDE.exe").is_file() or fresh:
        robocopy(env.onedir, dst)
    (dst / "portable.flag").write_text("E2E portable copy\n", encoding="utf-8")
    env.app = dst
    return dst


def launch(env: Env, name: str, extra_env: dict | None = None, exe=None, offscreen: bool = True) -> IDE:
    e = {"RADIDE_NO_UPDATE_CHECK": "1", "RADIDE_SETTINGS_ORG": "RADIDE-TEST-E2E"}
    if os.environ.get("RADIDE_E2E_LIVE_COMMANDS", "1") != "0":
        # the automation commands of this checkout replace the build's own (radide/automation/__init__.py):
        # harness fixes need no rebuild; the IDE code under test is still the build's
        e["RADIDE_AUTOMATION_PLUGINS"] = str(HERE.parent.parent.parent / "radide" / "automation")
    e.update(extra_env or {})
    logs = env.scratch / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    ide = IDE.launch(exe or env.exe(), desktop=env.desktop, env_extra=e, scratch=env.scratch / "ide",
                     log_path=logs / f"{name}-{int(time.time())}.log", offscreen=offscreen, timeout=240)
    ide.call("auto_dialogs", rules=[{"match": "save changes to", "button": "Save"}])
    return ide


# ------------------------------------------------------------------------------------------------ checks
ERROR_RX = re.compile(r"\*\*\* (Internal error|Error)|Traceback \(most recent call last\)|ModuleNotFoundError|"
                      r"ImportError|No module named", re.I)


def output_errors(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ERROR_RX.search(ln)]


def no_internal_errors(ide: IDE, since: int = 0) -> str:
    t = ide.output()[since:]
    errs = output_errors(t)
    check(not errs, "errors in Output: " + " | ".join(errs[:5]))
    return "Output clean"


def pe_imports(exe: Path) -> list[str]:
    try:
        import pefile
        pe = pefile.PE(str(exe), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        names = [e.dll.decode(errors="replace").lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
        pe.close()
        return names
    except Exception:  # noqa: BLE001
        return []


def no_python_inside(exe: Path) -> str:
    """A native exe: no python3x.dll next to it or imported, no PyInstaller archive marker."""
    folder = exe.parent
    py = [p.name for p in folder.rglob("python3*.dll")] + [p.name for p in folder.rglob("*.pyd")]
    check(not py, f"Python files next to the exe: {py[:5]}")
    imps = pe_imports(exe)
    check(not any(i.startswith("python") for i in imps), f"imports Python: {imps}")
    data = exe.read_bytes()
    check(b"MEI\x0c\x0b\x0a\x0b\x0e" not in data, "PyInstaller archive inside")
    return f"{exe.stat().st_size // 1024} KB, imports {', '.join(imps[:6])}"


# ------------------------------------------------------------------------------------------------ program UI
def find_kids(ide: IDE, hwnd: int) -> list[dict]:
    return ide.call("win32_children", hwnd=hwnd)


def wait_window(ide: IDE, title: str, pid: int | None = None, timeout: float = 240) -> dict:
    def f():
        ws = ide.call("win32_windows", title=title, pid=pid)
        ws = [w for w in ws if w["rect"][2] > 60 and w["rect"][3] > 40]
        return ws[0] if ws else None
    return ide.wait_for(f, timeout, step=1.0, desc=f"window {title!r}")


def edit_like(kids: list[dict]) -> list[dict]:
    """Text boxes: Win32 Edit / RichEdit, Tk entries (TkChild of an edit's height), Qt has no child HWNDs."""
    out = [k for k in kids if k["cls"].lower() in ("edit",) or k["cls"].lower().startswith("richedit")
           or (k["cls"].lower().startswith("windowsforms") and "edit" in k["cls"].lower())]
    return out or [k for k in kids if k["cls"] == "TkChild" and 16 <= k["rect"][3] <= 30]


def button_like(kids: list[dict]) -> list[dict]:
    return [k for k in kids if k["cls"].lower() == "button" or ("button" in k["cls"].lower()
                                                                 and k["cls"].lower().startswith("windowsforms"))]


def wait_title(ide: IDE, hwnd: int, want: str, timeout: float = 20) -> str:
    """The handler sets the form caption: the window title proves the click ran the user's code."""
    return ide.wait_for(lambda: (lambda t: t if want in t else None)(ide.call("win32_text", hwnd=hwnd)["text"]),
                        timeout, step=0.5, desc=f"window title {want!r}")


def window_texts(ide: IDE, hwnd: int) -> list[str]:
    return [k["text"] for k in find_kids(ide, hwnd)] + [ide.call("win32_text", hwnd=hwnd)["text"]]


def drive_hello(ide: IDE, rep: Report, w: dict, value: str, label: str) -> str:
    """Type *value* into the program's first text box, click its first button; *label* = expected label text."""
    hwnd = w["hwnd"]
    kids = find_kids(ide, hwnd)
    eds, bts = edit_like(kids), button_like(kids)
    if eds and bts:
        e = eds[0]["hwnd"]
        ide.call("win32_click", hwnd=e)
        ide.call("win32_key", hwnd=e, keys="Home, Shift+End, Delete")
        ide.call("win32_type", hwnd=e, value=value)
        ide.call("win32_click", hwnd=bts[0]["hwnd"])
    else:                                    # one HWND (Qt, owner-drawn): click by the designer coordinates
        r = w["rect"]
        ide.call("win32_click", hwnd=hwnd, x=24 + 8 + 37, y=24 + 31 + 11)
    time.sleep(1.0)
    rep.shot("program after click", hwnd=hwnd)
    return f"{len(eds)} edits, {len(bts)} buttons"


@dataclass
class Lang:
    id: str                       # plugin id (New Project dialog)
    title: str                    # short name for reports
    code: str                     # handler body (one or more lines, indented by the editor's auto-indent)
    text_prop: str = "Text"       # Button / Form caption property
    publish: str = "native"       # native | publish | none
    intellisense: str = ""        # what to type to see a member list ('lblOut.')
    marker: str = "E2E-CLICK"     # printed by the handler (seen in Output under F5)
    needs: tuple = ()             # executables that must exist (SKIP otherwise)
    run_timeout: float = 300
    publish_timeout: float = 900
    template: str = "windows"


def have_tool(name: str) -> bool:
    if shutil.which(name):
        return True
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE"
    return any(local.glob(f"**/{name}.exe")) if local.is_dir() else False


def published_exe_from_output(text: str) -> Path | None:
    hits = re.findall(r"(?:succeeded|Published|published|Native exe)[^\n]*?([A-Za-z]:\\[^\n]*?\.exe)", text)
    for h in reversed(hits):
        p = Path(h.strip().rstrip("=").strip())
        if p.is_file():
            return p
    return None


def hello_journey(env: Env, ide: IDE, rep: Report, L: Lang, root: Path) -> None:
    """The whole user flow for one desktop language (steps are reported one by one)."""
    name = "E2E" + re.sub(r"\W", "", L.title)
    title = f"E2E {L.title}"
    st: dict = {}
    missing = [t for t in L.needs if not have_tool(t)]
    steps = ["new project", "toolbox", "properties", "handler stub", "intellisense", "type code", "save",
             "F5 run", "program window", "click in program", "stop"]
    steps += (["Build Native Exe", "native exe runs on its own + click", "no python inside"]
              if L.publish == "native" else [])
    steps += ["Publish installer (Inno)", "install per-user", "installed app runs + click", "uninstall"]
    if missing:
        rep.skip_rest([f"{L.title}: {s}" for s in steps], f"toolchain missing: {', '.join(missing)}")
        return
    P = f"{L.title}: "

    def new():
        info = ide.call("new_project", language=L.id, name=name, location=str(root), template=L.template)
        check(info and info["language"] == L.id, f"project {info}")
        st["project"] = info
        return info["folder"]
    if not rep.step(P + "new project", new, shot=True):
        rep.skip_rest([P + s for s in steps[1:]], "no project")
        return

    def toolbox():
        ide.call("designer_place", type="Button", x=24, y=24, name="btnGreet")
        ide.call("designer_place", type="TextBox", x=24, y=72, w=180, h=24, name="txtName")
        ide.call("designer_place", type="Label", x=24, y=120, w=220, h=24, name="lblOut")
        names = [c["name"] for c in ide.call("designer_controls")["controls"]]
        check({"btnGreet", "txtName", "lblOut"} <= set(names), f"controls {names}")
        return names
    rep.step(P + "toolbox", toolbox, shot=True)

    def props():
        ide.call("set_property", name="btnGreet", prop=L.text_prop, value="Greet")
        ide.call("set_property", name="", prop=L.text_prop, value=title)
        ide.call("set_property", name="lblOut", prop=L.text_prop, value="...")
        v = ide.call("get_property", name="btnGreet", prop=L.text_prop)
        check(v == "Greet", f"btnGreet.{L.text_prop} = {v!r}")
        return v
    rep.step(P + "properties", props)

    def stub():
        ide.call("designer_dclick", name="btnGreet")
        t = ide.call("editor_text")
        lines = [i + 1 for i, ln in enumerate(t["text"].splitlines()) if "btnGreet" in ln and
                 ("click" in ln.lower())]
        check(lines, "no btnGreet click handler in the code:\n" + t["text"][-1500:])
        st["stub_line"] = lines[0]
        st["code_before"] = t["text"]
        return f"line {lines[0]} ({t['engine']})"
    if not rep.step(P + "handler stub", stub, shot=True):
        rep.skip_rest([P + s for s in steps[4:]], "no handler")
        return

    def body_line() -> int:
        """The first line inside the handler (the stub's own empty / pass / TODO line)."""
        text = ide.call("editor_text")["text"].splitlines()
        i = st["stub_line"]                       # 1-based line of the handler header
        while i < len(text) and text[i - 1].rstrip().endswith(("(", ",")):
            i += 1
        if i < len(text) and text[i - 1].rstrip().endswith("{") is False and text[i].strip() == "{":
            i += 1                               # brace on its own line
        return i + 1

    def intellisense():
        if not L.intellisense:
            raise Skip("no member list check for this language")
        ln = body_line()
        ide.call("editor_goto", line=ln, col=200)
        ide.call("editor_key", keys="Return") if ide.call("editor_text")["text"].splitlines()[ln - 1].strip() else None
        ide.call("editor_type", text=L.intellisense)
        c = ide.call("completion", wait_ms=8000)
        rep.shot(P + "intellisense")
        ide.call("editor_key", keys="Escape")
        # remove what was typed (the real code comes next)
        t = ide.call("editor_text")
        lines = t["text"].splitlines()
        lines = [x for x in lines if x.strip() != L.intellisense.strip()]
        ide.call("editor_set_text", text="\n".join(lines) + "\n")
        check(c.get("visible") and c.get("items"), f"no IntelliSense list: {c}")
        return c["items"][:8]
    rep.step(P + "intellisense", intellisense)

    def typecode():
        ln = body_line()
        text = ide.call("editor_text")["text"].splitlines()
        cur = text[ln - 1] if ln - 1 < len(text) else ""
        indent = re.match(r"\s*", cur).group(0) if cur.strip() else (re.match(r"\s*", text[st["stub_line"] - 1]).group(0) + "    ")
        body = [indent + x for x in L.code.splitlines()]
        if cur.strip() in ("", "pass", "// TODO", "' TODO") or "TODO" in cur:
            text[ln - 1:ln] = body
        else:
            text[ln - 1:ln - 1] = body
        ide.call("editor_set_text", text="\n".join(text) + "\n")
        t = ide.call("editor_text")["text"]
        check(L.marker in t, "code not in the editor")
        return f"{len(body)} lines at {ln}"
    rep.step(P + "type code", typecode, shot=True)

    def save():
        check(ide.call("save_all"), "save_all failed")
        folder = Path(st["project"]["folder"])
        hits = [p for p in folder.rglob("*") if p.is_file() and p.suffix not in (".form", ".radproj", ".json")
                and L.marker in p.read_text(encoding="utf-8", errors="ignore")]
        check(hits, "the handler code is not in any file on disk")
        return hits[0].name
    rep.step(P + "save", save)

    def run():
        ide.call("output", clear=True)
        ide.call("key", keys="F5", async_=True)
        ide.wait_for(lambda: ide.call("run_state")["running"] or "------" in ide.output(), 60, desc="session")
        return ide.call("run_state")
    if not rep.step(P + "F5 run", run):
        rep.skip_rest([P + s for s in steps[8:]], "F5 did not start")
        return

    def window():
        w = wait_window(ide, title, timeout=L.run_timeout)
        st["win"] = w
        rep.shot(P + "program", hwnd=w["hwnd"])
        return f"{w['cls']} {w['rect']}"
    ok = rep.step(P + "program window", window)

    def click():
        info = drive_hello(ide, rep, st["win"], "World", "Hello, World")
        title_now = wait_title(ide, st["win"]["hwnd"], "E2E-CLICK Hello, World")
        return f"{info}; window title: {title_now!r}"
    if ok:
        rep.step(P + "click in program", click)
    else:
        rep.skip_rest([P + "click in program"], "no window")
        st["fail_out"] = ide.output()[-3000:]

    def stop():
        ide.call("trigger", path="Debug/Stop Debugging") if ide.call("run_state")["running"] else None
        ide.wait_for(lambda: not ide.call("run_state")["running"], 30, desc="stopped")
        return "stopped"
    rep.step(P + "stop", stop)

    if L.publish == "none":
        rep.skip_rest([P + s for s in steps[11:]], "no publish for this language")
        return
    if L.publish == "native":
        native_steps(ide, rep, L, st, title, P)
    installer_steps(env, ide, rep, L, st, title, P, name)


def run_and_drive(ide: IDE, rep: Report, exe: Path, title: str, value: str, P: str, what: str) -> str:
    r = ide.call("start_process", argv=[str(exe)], cwd=str(exe.parent))
    w = None
    try:
        w = wait_window(ide, title, timeout=120, pid=None)
        rep.shot(P + what, hwnd=w["hwnd"])
        drive_hello(ide, rep, w, value, "")
        t = wait_title(ide, w["hwnd"], f"E2E-CLICK Hello, {value}")
    finally:                                   # never leave the exe running (it locks the next build)
        if w is not None:
            ide.try_call("win32_close", hwnd=w["hwnd"])
        try:
            ide.wait_for(lambda: ide.call("process_status", pid=r["pid"])["returncode"] is not None, 15,
                         desc="exe closed")
        except Exception:  # noqa: BLE001
            ide.try_call("win32_kill", pid=r["pid"])
    return f"pid {r['pid']}: title after click {t!r}"


def native_steps(ide: IDE, rep: Report, L: Lang, st: dict, title: str, P: str) -> None:
    def build():
        ide.call("output", clear=True)
        ide.call("trigger", path="Build/Build Native Exe")
        txt = ide.wait_output(["Build Native Exe succeeded", "Build Native Exe failed", "========== Build failed"],
                              timeout=L.publish_timeout)
        check("succeeded" in txt.split("==========")[-2] if txt.count("==========") >= 2 else "succeeded" in txt,
              "native build failed: " + txt[-2500:])
        exe = published_exe_from_output(txt)
        check(exe is not None, "no exe in the output: " + txt[-1500:])
        st["exe"] = exe
        return f"{exe.name} {exe.stat().st_size // 1024} KB"
    if not rep.step(P + "Build Native Exe", build):
        rep.skip_rest([P + "native exe runs + click", P + "no python inside"], "no native exe")
        return
    rep.step(P + "native exe runs on its own + click", lambda: run_and_drive(ide, rep, st["exe"], title, "Native", P,
                                                                           "native exe"))
    rep.step(P + "no python inside", lambda: no_python_inside(st["exe"]))


def installer_steps(env: Env, ide: IDE, rep: Report, L: Lang, st: dict, title: str, P: str, name: str) -> None:
    names = ["Publish installer (Inno)", "install per-user", "installed app runs + click", "uninstall"]

    def publish():
        ide.call("output", clear=True)
        ide.call("trigger", path="Build/Publish / Create Installer...")
        ide.wait_dialog("Publish", timeout=30)
        rep.shot(P + "publish dialog", sel={"dialog": "Publish"})
        ide.call("press", button="Publish", dialog="Publish")
        txt = ide.wait_output(["Publish succeeded", "Publish failed", "Publish canceled"], timeout=L.publish_timeout)
        m = re.search(r"Publish succeeded: (.+?\.exe)", txt)
        check(m and Path(m.group(1).strip()).is_file(), "publish failed: " + txt[-2500:])
        st["setup"] = Path(m.group(1).strip())
        return f"{st['setup'].name} {st['setup'].stat().st_size // 1024} KB"
    if not rep.step(P + names[0], publish):
        rep.skip_rest([P + n for n in names[1:]], "no setup")
        return
    inst = env.scratch / "installed" / name

    def install():
        shutil.rmtree(inst, ignore_errors=True)
        r = subprocess.run([str(st["setup"]), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                            f"/DIR={inst}", "/TASKS=", f"/LOG={env.scratch / 'logs' / (name + '-setup.log')}"],
                           timeout=600)
        check(r.returncode == 0, f"setup exit {r.returncode}")
        exes = sorted([p for p in inst.rglob("*.exe") if not p.name.lower().startswith("unins")],
                      key=lambda p: (len(p.relative_to(inst).parts), -p.stat().st_size))
        check(exes, f"no exe installed in {inst}")
        st["installed_exe"] = exes[0]
        check(any(inst.glob("unins*.exe")), "no uninstaller")
        return str(exes[0].relative_to(inst))
    if not rep.step(P + names[1], install):
        rep.skip_rest([P + n for n in names[2:]], "not installed")
        return
    rep.step(P + names[2], lambda: run_and_drive(ide, rep, st["installed_exe"], title, "Setup", P, "installed app"))

    def uninstall():
        un = sorted(inst.glob("unins*.exe"))[-1]
        r = subprocess.run([str(un), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300)
        check(r.returncode == 0, f"uninstaller exit {r.returncode}")
        ok = False
        for _ in range(30):
            if not st["installed_exe"].exists():
                ok = True
                break
            time.sleep(1)
        check(ok, f"{st['installed_exe']} still there after uninstall")
        return "removed"
    rep.step(P + names[3], uninstall)


def real_python() -> str:
    """A real python.exe for the programs the IDE starts (the one running this harness, not a venv shim)."""
    import sys
    base = Path(getattr(sys, "_base_executable", "") or sys.executable)
    return str(base if base.is_file() else Path(sys.executable))


def wait_file_text(path: Path, want: str, timeout: float = 300) -> str:
    end = time.monotonic() + timeout
    last = ""
    while time.monotonic() < end:
        try:
            last = path.read_text(encoding="utf-8").strip()
            if want in last:
                return last
        except OSError:
            pass
        time.sleep(1)
    raise AssertionError(f"{path} = {last!r}, expected {want!r}")
