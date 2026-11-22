"""Native Rust / Go / Lua builds with radforms (radide/deploy/native/rust_native.py, go_native.py,
script_embed.py).

    .venv\\Scripts\\python samples/Tests/Native/test_native_rust_go_lua.py [scratch folder]

1. Rust, Go and Lua FormsDemo (the forms of samples/Tests/Native/C/FormsDemo: two forms, menu, timer, list,
   combo, check / radio buttons, multi-line text, message box, Arabic text; a module called from a form)
   are published with radide.deploy.build.build(): kind "native", one exe, no Python, size limits, only
   Windows system DLLs (+ the UCRT api sets) imported, the project folder untouched. Each exe is started
   and driven with Win32 messages; closing Form1 ends the process. Only processes started here are touched.
2. A copy of a fresh Rust WinForms project (like a new "RustApp1": Form1 + Button1) builds natively and
   its window appears; with RAD_TEST_USER_RUST=<folder> that project is copied to scratch and tested too
   (the folder itself is never changed). The x86_64-pc-windows-gnu Rust target (MinGW link) is tested
   when rustup has it.
3. Fallbacks: radcall / unknown property / C module make check() give reasons; the native client variants
   keep the bridge API; the bridge clients tell the user to use the IDE or Publish when started alone.
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import winauto as w  # noqa: E402
from radide.deploy import build  # noqa: E402
from radide.deploy.build import _pe_imports  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.deploy.native import go_native, rust_native, script_embed  # noqa: E402
from radide.model import Project  # noqa: E402

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_native_rgl_"))
SCRATCH.mkdir(parents=True, exist_ok=True)
SYSTEM_DLLS = {"kernel32", "user32", "gdi32", "comctl32", "comdlg32", "shell32", "ole32", "oleaut32", "uxtheme",
               "dwmapi", "gdiplus", "advapi32", "ws2_32", "msvcrt", "ucrtbase", "shlwapi", "version", "winmm",
               "imm32", "d2d1", "dwrite", "winspool", "bcrypt", "bcryptprimitives", "ntdll", "userenv", "secur32",
               "crypt32", "powrprof", "synchronization"}
SYSTEM_DLLS |= {"iphlpapi", "dbghelp"}          # node.exe
LIMITS = {"Rust": 450_000, "Go": 2_600_000, "Lua": 400_000, "JS": 110_000_000, "TS": 110_000_000}
TITLES = {"JS": "Native JavaScript demo (npm) [fs ok]", "TS": "Native TypeScript demo (npm) [fs ok]"}
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail: str = "") -> bool:
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    return bool(cond)


def system_only(exe: Path) -> tuple[bool, list[str]]:
    dlls = _pe_imports(exe)
    bad = [d for d in dlls if d.lower().removesuffix(".dll") not in SYSTEM_DLLS
           and not d.lower().startswith("api-ms-win-")]
    return bool(dlls) and not bad, bad


def snapshot(folder: Path) -> dict:
    return {str(p.relative_to(folder)): p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()}


# ------------------------------------------------------------------ 1. FormsDemo
def publish(lang: str, src: Path | None = None, out_name: str = "") -> Path | None:
    src = src or HERE / lang / "FormsDemo"
    out = SCRATCH / (out_name or f"publish {lang}")          # a space in the path on purpose
    shutil.rmtree(out, ignore_errors=True)
    cfg = PublishConfig(app_name=f"FormsDemo{lang}", version="1.2.3", publisher="RAD IDE tests", output_dir=str(out))
    before = snapshot(src)
    log: list[str] = []
    t = time.time()
    try:
        res = build.build(src, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        ok(f"{lang}: build", False, f"{e}\n" + "\n".join(log[-25:]))
        return None
    exe = res.dist / res.exe
    ok(f"{lang}: native kind", res.kind == "native" and not res.python_based, res.kind + "\n" + "\n".join(log[-12:]))
    ok(f"{lang}: exe exists", exe.is_file())
    files = [p.name.lower() for p in res.dist.rglob("*")]
    ok(f"{lang}: no Python inside", not any(n.startswith("python") and n.endswith(".dll") for n in files)
       and "_internal" not in files, ", ".join(files[:10]))
    ok(f"{lang}: only the exe (no DLLs, no sources)",
       [n for n in files if n not in ("readme.md", "node.js-license.txt")] == [exe.name.lower()], ", ".join(files))
    if lang in ("JS", "TS"):
        ok(f"{lang}: Node.js licence next to the exe", (res.dist / "Node.js-LICENSE.txt").is_file())
    size = exe.stat().st_size if exe.is_file() else 0
    ok(f"{lang}: size {size // 1024} KB <= {LIMITS[lang] // 1024} KB", 0 < size <= LIMITS[lang])
    sysok, bad = system_only(exe)
    ok(f"{lang}: imports only system DLLs", sysok, ", ".join(bad))
    ok(f"{lang}: the project folder is left unchanged", snapshot(src) == before)
    print(f"   {lang} exe: {size:,} bytes, built in {time.time() - t:.1f} s", flush=True)
    return exe if exe.is_file() else None


def child_pids(pid: int) -> list[int]:
    """Processes started by *pid* (the Node exe starts its radforms host)."""
    import ctypes
    from ctypes import wintypes as wt

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k.CreateToolhelp32Snapshot(2, 0)
    e = PE32()
    e.dwSize = ctypes.sizeof(PE32)
    out = []
    if k.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            if e.th32ParentProcessID == pid:
                out.append(e.th32ProcessID)
            if not k.Process32NextW(snap, ctypes.byref(e)):
                break
    k.CloseHandle(snap)
    return out


def window_pid(p, lang: str) -> int:
    """The process that owns the forms: the exe itself, or (Node) its radforms host."""
    if lang not in ("JS", "TS"):
        return p.pid
    return w.wait(lambda: next(iter(child_pids(p.pid)), 0), 15) or p.pid


def drive_forms_demo(lang: str, exe: Path):
    p = proc = w.start(exe)
    f = None
    hosts: list[int] = []
    try:
        wpid = window_pid(p, lang)
        hosts = [wpid] if wpid != p.pid else []
        if lang in ("JS", "TS"):
            ok(f"{lang}: the radforms host process runs", hosts)
        f = w.form_window(wpid, "Form1", 20)
        if not ok(f"{lang}: Form1 shown", f):
            return
        title = TITLES.get(lang, f"Native {lang} demo")
        ok(f"{lang}: Form1 caption" + (" (npm package + fs from Load)" if lang in TITLES else ""),
           w.wait(lambda: w.get_text(f) == title), w.get_text(f))
        p = type("P", (), {"pid": wpid})()                       # windows / dialogs belong to wpid
        c = w.wait(lambda: (lambda d: d if "lblOut" in d and "lstLog" in d else None)(w.children(f)))
        ok(f"{lang}: controls found by name", c and {"txtA", "cmdAdd", "chkBig", "optTwo", "cboColor", "txtNotes",
                                                    "prgTicks", "grpPick"} <= set(c), sorted(c or []))
        if not c:
            return
        t = lambda name: w.get_text(c[name])  # noqa: E731
        ok(f"{lang}: Load ran", w.wait(lambda: t("lblOut") == "ready"), t("lblOut"))
        ok(f"{lang}: Load AddItem", w.list_item(c["lstLog"], 0) == "Form1 loaded", w.list_item(c["lstLog"], 0))
        ok(f"{lang}: multi-line text", t("txtNotes") == "line 1\r\nline 2", repr(t("txtNotes")))
        w.set_text(c["txtA"], "2")
        ok(f"{lang}: TextChanged + get", w.wait(lambda: t("lblEcho") == "2"), t("lblEcho"))
        w.set_text(c["txtB"], "3")
        w.click(c["cmdAdd"])
        ok(f"{lang}: Click + get_num + set", w.wait(lambda: t("lblOut") == "5"), t("lblOut"))
        n = w.wait(lambda: w.user32.SendMessageW(c["lstLog"], w.LB_GETCOUNT, 0, 0) == 2 and 2)
        last = w.list_item(c["lstLog"], 1) if n else ""
        ok(f"{lang}: module function + list AddItem", last == "2 x 3 = 6", last)
        w.click(c["chkBig"])
        ok(f"{lang}: CheckedChanged + FontSize", w.wait(lambda: t("lblOut") == "big"), t("lblOut"))
        w.user32.SendMessageW(c["cboColor"], w.CB_SETCURSEL, 1, 0)
        w.user32.PostMessageW(f, w.WM_COMMAND, (w.CBN_SELCHANGE << 16) | (w.user32.GetDlgCtrlID(c["cboColor"]) & 0xFFFF),
                              c["cboColor"])
        ok(f"{lang}: SelectedIndexChanged", w.wait(lambda: t("lblOut") == "Green"), t("lblOut"))
        w.click(c["optTwo"])
        ok(f"{lang}: radio CheckedChanged", w.wait(lambda: t("lblEcho") == "True"), t("lblEcho"))
        t1 = w.wait(lambda: int(t("lblTicks") or 0) >= 3 and int(t("lblTicks")))
        time.sleep(0.4)
        ok(f"{lang}: Timer ticks", t1 and int(t("lblTicks") or 0) > t1, t("lblTicks"))
        w.click(c["cmdShow2"])
        f2 = w.form_window(p.pid, "Form2", 5)
        if ok(f"{lang}: second form shown", f2):
            c2 = w.children(f2)
            ok(f"{lang}: Form2_Load ran", w.wait(lambda: w.get_text(c2["txt2"]) == "from Form2 Load"))
            w.set_text(c2["txt2"], "back to Form1")
            w.click(c2["cmdClose2"])
            ok(f"{lang}: Form2 writes Form1.lblOut and hides",
               w.wait(lambda: t("lblOut") == "back to Form1" and not w.user32.IsWindowVisible(f2)), t("lblOut"))
        w.click(c["cmdMsg"])
        dlg = w.dialog_of(p.pid)
        if ok(f"{lang}: MsgBox shown", dlg):
            w.click_dialog_button(dlg)
            ok(f"{lang}: handler continues after MsgBox", w.wait(lambda: t("lblOut") == "msg done"), t("lblOut"))
        w.click(c["cmdArabic"])
        ok(f"{lang}: Arabic text", w.wait(lambda: t("lblOut") == "مرحبا بالعالم"), t("lblOut"))
        ok(f"{lang}: Arabic button caption", t("cmdArabic") == "عربي", t("cmdArabic"))
        w.menu_command(f, (0, 0))
        f2 = w.form_window(p.pid, "Form2", 5)
        ok(f"{lang}: menu item Click", f2 and w.user32.IsWindowVisible(f2))
    finally:
        ok(f"{lang}: closing Form1 ends the program", w.stop(proc, f))
        for h in hosts:                                   # the host we started (through the exe) must end too
            gone = w.wait(lambda: h not in child_pids(proc.pid) and not _alive(h), 8)
            if not ok(f"{lang}: the radforms host ends with the program", gone):
                subprocess.run(["taskkill", "/PID", str(h), "/F"], capture_output=True)


def _alive(pid: int) -> bool:
    import ctypes
    k = ctypes.WinDLL("kernel32")
    h = k.OpenProcess(0x1000 | 0x00100000, False, pid)      # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
    if not h:
        return False
    try:
        return k.WaitForSingleObject(h, 0) == 0x102            # WAIT_TIMEOUT = still running
    finally:
        k.CloseHandle(h)


# ------------------------------------------------------------------ 2. Rust WinForms project like RustApp1
FORM_RUSTAPP = {"version": 2, "props": {"Name": "Form1", "Text": "Form1", "Width": 400, "Height": 300,
                                       "StartPosition": "CenterScreen", "FormBorderStyle": "Sizable"},
                "controls": [{"type": "Button", "props": {"Name": "Button1", "Text": "Button1", "Left": 48, "Top": 80,
                                                          "Width": 75, "Height": 23, "TabIndex": 0}}]}


def new_rust_app(folder: Path):
    """A project as File > New Project (Rust WinForms) makes it, prepared once by the IDE's normal run."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "Form1.form").write_text(json.dumps(FORM_RUSTAPP, indent=2), encoding="utf-8")
    (folder / "project.radproj").write_text(json.dumps({"name": "RustApp1", "language": "rust-bridge",
                                                        "forms": ["Form1"], "startup": "Form1", "modules": []}),
                                            encoding="utf-8")
    from radide.languages import get_plugin
    from radide.model import Form
    plugin = get_plugin("rust-bridge")
    (folder / "Form1.rs").write_text(plugin.new_code(Form.load(folder / "Form1.form"), True) +
                                     '\npub fn Button1_Click() {\n    set("Button1", "Text", "clicked");\n}\n',
                                     encoding="utf-8")
    plugin.prepare(folder, Project.load(folder))            # radgui.rs, _radmain.rs, Cargo.toml


def rust_app_tests():
    app = SCRATCH / "RustApp1"
    new_rust_app(app)
    exe = publish("Rust", app, "publish RustApp1")
    if exe is None:
        return
    p = w.start(exe)
    f = None
    try:
        f = w.form_window(p.pid, "Form1")
        ok("RustApp1: window appears (no IDE)", f and w.user32.IsWindowVisible(f))
        c = w.children(f) if f else {}
        if ok("RustApp1: Button1 exists", "Button1" in c):
            w.click(c["Button1"])
            ok("RustApp1: Button1_Click runs", w.wait(lambda: w.get_text(c["Button1"]) == "clicked"),
               w.get_text(c["Button1"]))
    finally:
        ok("RustApp1: closes", w.stop(p, f))
    user = os.environ.get("RAD_TEST_USER_RUST", "")
    if user and Path(user).is_dir():
        copy = SCRATCH / "user_rust_copy"
        shutil.rmtree(copy, ignore_errors=True)
        shutil.copytree(user, copy, ignore=shutil.ignore_patterns("_build", "Publish", "target"))
        uexe = publish("Rust", copy, "publish user rust")
        if uexe is not None:
            pr = Project.load(copy)
            p = w.start(uexe)
            f = None
            try:
                f = w.form_window(p.pid, pr.startup or pr.forms[0])
                ok(f"user project {Path(user).name}: window appears", f)
            finally:
                ok(f"user project {Path(user).name}: closes", w.stop(p, f))


def rust_gnu_test():
    cargo = rust_native.find_cargo()
    if rust_native.GNU not in rust_native._targets(cargo):
        print("   (rustup has no x86_64-pc-windows-gnu target: GNU link not tested)")
        return
    import radide.languages.c_bridge as cb
    saved = cb.find_vcvars
    cb.find_vcvars = lambda: ""                  # as on a PC without Visual C++
    try:
        exe = publish("Rust", HERE / "Rust" / "FormsDemo", "publish Rust gnu")
    finally:
        cb.find_vcvars = saved
    if exe is not None:
        p = w.start(exe)
        f = None
        try:
            f = w.form_window(p.pid, "Form1")
            c = w.children(f) if f else {}
            ok("Rust gnu: Load ran", f and w.wait(lambda: w.get_text(c["lblOut"]) == "ready"))
        finally:
            ok("Rust gnu: closes", w.stop(p, f))


# ------------------------------------------------------------------ 3. checks / fallbacks
def check_tests():
    cfg = PublishConfig()
    for lang, mod, file, code, word in [
            ("Rust", rust_native, "Form1.rs", '\npub fn x_Click() { let _ = radcall("PyLib.hello", &[]); }\n', "radcall"),
            ("Rust", rust_native, "Form1.rs", '\npub fn y_Click() { set("lblOut", "Blink", 1); }\n', "Blink"),
            ("Go", go_native, "Form1.go", '\nfunc x_Click() { radcall("PyLib.hello") }\n', "radcall"),
            ("Go", go_native, "Form1.go", '\nfunc y_Click() { Set("lblOut", "Blink", 1) }\n', "Blink"),
            ("Lua", script_embed, "Form1.lua", '\nfunction x_Click() radcall("PyLib.hello") end\n', "radcall"),
            ("Lua", script_embed, "Form1.lua", '\nlocal socket = require("socket")\n', "socket"),
            ("Lua", script_embed, "Form1.lua", '\nfunction y_Click() rad.set("lblOut", "Blink", 1) end\n', "Blink")]:
        tmp = SCRATCH / f"check_{lang}"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(HERE / lang / "FormsDemo", tmp)
        ok(f"{lang}: demo passes check()", mod.check(tmp, Project.load(tmp), cfg) == [],
           str(mod.check(tmp, Project.load(tmp), cfg)))
        (tmp / file).write_text((tmp / file).read_text(encoding="utf-8") + code, encoding="utf-8")
        reasons = mod.check(tmp, Project.load(tmp), cfg)
        ok(f"{lang}: {word} -> reason (falls back to the bridge build)", any(word in r for r in reasons), str(reasons))
    for lang in ("rust-bridge", "go-bridge", "lua-bridge"):
        ok(f"{lang}: auto build kind is native",
           build.detect_kind(Project.load(HERE / {"rust-bridge": "Rust", "go-bridge": "Go", "lua-bridge": "Lua"}[lang]
                                          / "FormsDemo"), cfg) == "native")
    rs = rust_native.native_radgui()
    ok("Rust native radgui keeps the API", all(f"pub fn {n}(" in rs for n in (
        "set", "get", "get_num", "call", "msgbox", "input", "show", "hide", "end", "print", "num", "str",
        "event_args", "event_arg", "next_event", "done", "radcall", "worker_main")) and "pub enum Json" in rs
       and "TcpStream" not in rs and "rad_next_event" in rs)
    ok("Go native radlib keeps the API", all(f"func {n}(" in go_native.RADLIB_NATIVE for n in (
        "Set", "Get", "GetNum", "Call", "MsgBox", "Input", "Show", "Hide", "End", "radcall", "radcallE", "radRun"))
       and 'import "C"' in go_native.RADLIB_NATIVE)
    lua = script_embed.native_rad_lua()
    ok("Lua native rad.lua keeps the API", all(s in lua for s in ("function rad.set(", "function rad.call(",
                                                                  "function rad.run()", "rad.ui =", "_G.ui",
                                                                  "json.decode")))
    toml = rust_native.cargo_toml('[package]\nname = "x"\nedition = "2021"\n\n[dependencies]\nrand = "0.8"\n\n'
                                  '[[bin]]\nname = "radapp"\npath = "_radmain.rs"\n', "x")
    ok("Rust Cargo.toml keeps [dependencies], one bin, size profile",
       'rand = "0.8"' in toml and toml.count("[[bin]]") == 1 and 'opt-level = "z"' in toml and 'panic = "abort"'
       in toml and "_radmain.rs" not in toml)
    pk = script_embed.pack({"a.lua": b"x=1", "b/c.lua": "-- عربي".encode()})
    ok("Lua script pack format", pk.startswith(b"a.lua\x003\x00x=1b/c.lua\x00"))
    # the bridge clients started without the IDE say how to get a standalone exe
    rsrc = (REPO / "radide" / "runtimes" / "clients" / "rust" / "radgui.rs").read_text(encoding="utf-8")
    gsrc = (REPO / "radide" / "runtimes" / "clients" / "go" / "radlib.go").read_text(encoding="utf-8")
    ok("bridge clients explain a start without the IDE", "Build Native Exe" in rsrc and "Build Native Exe" in gsrc)


def js_copy(lang: str) -> Path:
    """A scratch copy of the JS / TS demo with its npm dependency installed (node_modules is git-ignored:
    the vendored package is copied like `npm install` of a file: dependency does)."""
    dst = SCRATCH / f"{lang}_project"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(HERE / lang / "FormsDemo", dst)
    shutil.copytree(dst / "vendor" / "rad-shout", dst / "node_modules" / "rad-shout")
    return dst


def js_tests():
    from radide.deploy.native import node_sea
    for lang in ("JS", "TS"):
        src = js_copy(lang)
        exe = publish(lang, src, f"publish {lang}")
        if exe is None:
            continue
        host = exe.parents[2] / "native_node" / "radhost.exe"
        if ok(f"{lang}: radforms host built", host.is_file()):
            sysok, bad = system_only(host)
            ok(f"{lang}: host {host.stat().st_size // 1024} KB, only system DLLs", sysok and host.stat().st_size < 400_000,
               ", ".join(bad))
        data = exe.read_bytes()
        import struct
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        ok(f"{lang}: exe is Node.js with the SEA blob, fuse set, GUI subsystem",
           "NODE_SEA_BLOB".encode("utf-16-le") in data and (node_sea.SEA_FUSE + ":1").encode() in data
           and struct.unpack_from("<H", data, pe + 24 + 68)[0] == 2)
        drive_forms_demo(lang, exe)
        ok(f"{lang}: fs wrote next to the exe", (exe.parent / "fs_check.txt").is_file())
    # check() fallbacks
    cfg = PublishConfig()
    base = js_copy("JS")
    ok("JS: demo passes check()", node_sea.check(base, Project.load(base), cfg) == [],
       str(node_sea.check(base, Project.load(base), cfg)))
    for what, edit, word in [
            ("radcall", lambda d: _append(d / "Form1.js", '\nfunction x_Click(e) { radcall("PyLib.hello"); }\n'), "radcall"),
            ("missing npm package", lambda d: _append(d / "Form1.js", "\nconst lp = require('left-pad');\n"), "left-pad"),
            ("native addon", lambda d: (_append(d / "Form1.js", "\nconst nat = require('natpkg');\n"),
                                        (d / "node_modules" / "natpkg").mkdir(parents=True),
                                        (d / "node_modules" / "natpkg" / "index.js").write_text("module.exports=1"),
                                        (d / "node_modules" / "natpkg" / "addon.node").write_bytes(b"MZ")), "addon"),
            ("ES import", lambda d: _append(d / "Strings.js", "\nimport x from 'rad-shout';\n"), "import"),
            ("unknown property", lambda d: _append(d / "Form1.js", "\nfunction y_Click(e) { set('lblOut', 'Blink', 1); }\n"),
             "Blink")]:
        d = js_copy("JS")
        edit(d)
        reasons = node_sea.check(d, Project.load(d), cfg)
        ok(f"JS: {what} -> reason (falls back to the bridge build)", any(word in r for r in reasons), str(reasons))
    ok("javascript / typescript: auto build kind is native",
       build.detect_kind(Project.load(base), cfg) == "native" and
       build.detect_kind(Project.load(HERE / "TS" / "FormsDemo"), cfg) == "native")
    js = node_sea.native_client()
    ok("JS native client keeps the API and the loader", all(s in js for s in (
        "function set(", "function get(", "function call(", "function msgbox(", "const ui = new Proxy",
        "function runMain(", "writeLine('NEXT')", "radNativeRequire", "fs.readSync(RAD_FD"))
       and "fs.readSync(0," not in js)


def _append(p: Path, text: str):
    p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")


def main():
    only = os.environ.get("RAD_TEST_ONLY", "")
    for lang in ("Rust", "Go", "Lua"):
        if only and only != lang:
            continue
        exe = publish(lang)
        if exe is not None:
            drive_forms_demo(lang, exe)
    if not only or only == "JS":
        js_tests()
    if only:
        failed = [n for n, good, _ in results if not good]
        print(f"\n{len(results) - len(failed)}/{len(results)} passed")
        return len(failed)
    rust_app_tests()
    rust_gnu_test()
    check_tests()
    failed = [n for n, good, _ in results if not good]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for n in failed:
        print("  FAILED:", n)
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
