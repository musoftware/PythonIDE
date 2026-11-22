"""Native C / C++ / Fortran builds with radforms (radide/deploy/native/win32_c.py) + the radforms ABI.

    .venv\\Scripts\\python samples/Tests/Native/test_native_c.py [scratch folder]

1. C, C++ and Fortran FormsDemo (two forms, menu, timer, list, combo, check / radio buttons, multi-line
   text, message box, Arabic text) are published with radide.deploy.build.build(): the kind is "native",
   one exe, no Python (no python*.dll, no _internal), size limits, only Windows system DLLs imported.
   Each exe is started and driven with Win32 messages (controls found by their "radforms.name"
   property): events change the labels, Form2 opens and writes back, the RADFUNC module runs in process,
   closing Form1 ends the process. Only the processes started here are touched.
2. libradforms.a + the HandlesAbi demo (handles API, rf_run_events callback, ButtonX module, controls
   made at run time, custom events, themes, FormClosing cancel, owner-drawn pixels via PrintWindow).
   With Visual Studio installed: radforms.lib (MSVC) links the same demo.
3. radforms_api.json is up to date and every ABI function is in the library; fallbacks: an unsupported
   control / a RAD Hub reference make check() give reasons (the build falls back to the GUI Bridge);
   the Fortran native module keeps the radgui API.
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
from radide.deploy.native import radforms_gen as rg, win32_c  # noqa: E402
from radide.model import Project  # noqa: E402

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_native_c_"))
SCRATCH.mkdir(parents=True, exist_ok=True)
SYSTEM_DLLS = {"kernel32", "user32", "gdi32", "comctl32", "comdlg32", "shell32", "ole32", "oleaut32", "uxtheme",
               "dwmapi", "gdiplus", "advapi32", "ws2_32", "msvcrt", "ucrtbase", "shlwapi", "version", "winmm",
               "imm32", "d2d1", "dwrite", "winspool", "bcrypt", "ntdll"}
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


# ------------------------------------------------------------------ 1. FormsDemo C / C++ / Fortran
LIMITS = {"C": 150_000, "Cpp": 700_000, "Fortran": 1_500_000}


def publish(lang: str) -> Path | None:
    src = HERE / lang / "FormsDemo"
    out = SCRATCH / f"publish_{lang}"
    shutil.rmtree(out, ignore_errors=True)
    cfg = PublishConfig(app_name=f"FormsDemo{lang}", version="1.2.3", publisher="RAD IDE tests", output_dir=str(out))
    log = []
    try:
        res = build.build(src, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        ok(f"{lang}: build", False, f"{e}\n" + "\n".join(log[-15:]))
        return None
    exe = res.dist / res.exe
    ok(f"{lang}: native kind", res.kind == "native" and not res.python_based, res.kind + " " + "\n".join(log[-8:]))
    ok(f"{lang}: exe exists", exe.is_file())
    files = [p.name.lower() for p in res.dist.rglob("*")]
    ok(f"{lang}: no Python inside", not any(n.startswith("python") and n.endswith(".dll") for n in files)
       and "_internal" not in files, ", ".join(files[:10]))
    ok(f"{lang}: only the exe (no DLLs)", not any(n.endswith(".dll") for n in files), ", ".join(files))
    size = exe.stat().st_size if exe.is_file() else 0
    ok(f"{lang}: size {size // 1024} KB <= {LIMITS[lang] // 1024} KB", 0 < size <= LIMITS[lang])
    sysok, bad = system_only(exe)
    ok(f"{lang}: imports only system DLLs", sysok, ", ".join(bad))
    leftovers = [p.name for p in src.iterdir() if p.name.startswith(("_rad", "radgui"))]
    ok(f"{lang}: the project folder is left clean", not leftovers, ", ".join(leftovers))
    print(f"   {lang} exe: {size:,} bytes", flush=True)
    return exe if exe.is_file() else None


def drive_forms_demo(lang: str, exe: Path):
    p = w.start(exe)
    f = None
    try:
        f = w.form_window(p.pid, "Form1")
        if not ok(f"{lang}: Form1 shown", f):
            return
        c = w.wait(lambda: (lambda d: d if "lblOut" in d and "lstLog" in d else None)(w.children(f)))
        ok(f"{lang}: controls found by name", c and {"txtA", "cmdAdd", "chkBig", "optTwo", "cboColor", "txtNotes",
                                                    "prgTicks", "grpPick"} <= set(c), sorted(c or []))
        if not c:
            return
        t = lambda name: w.get_text(c[name])  # noqa: E731
        ok(f"{lang}: Load ran", w.wait(lambda: t("lblOut") == "ready"), t("lblOut"))
        ok(f"{lang}: multi-line text", t("txtNotes") == "line 1\r\nline 2", repr(t("txtNotes")))
        w.set_text(c["txtA"], "2")
        ok(f"{lang}: TextChanged", w.wait(lambda: t("lblEcho") == "2"), t("lblEcho"))
        w.set_text(c["txtB"], "3")
        w.click(c["cmdAdd"])
        ok(f"{lang}: Click + rad_get_num + rad_set", w.wait(lambda: t("lblOut") == "5"), t("lblOut"))
        n = w.wait(lambda: w.user32.SendMessageW(c["lstLog"], w.LB_GETCOUNT, 0, 0) == 2 and 2)
        last = w.list_item(c["lstLog"], 1) if n else ""
        want = "2 + 3 = 5" if lang == "Fortran" else "2 x 3 = 6"
        ok(f"{lang}: AddItem ({'RADFUNC in process' if lang != 'Fortran' else 'list'})", last == want, last)
        w.click(c["chkBig"])
        ok(f"{lang}: CheckedChanged + FontSize", w.wait(lambda: t("lblOut") == "big"), t("lblOut"))
        w.user32.SendMessageW(c["cboColor"], w.CB_SETCURSEL, 1, 0)
        w.user32.PostMessageW(f, w.WM_COMMAND, (w.CBN_SELCHANGE << 16) | (w.user32.GetDlgCtrlID(c["cboColor"]) & 0xFFFF),
                              c["cboColor"])
        ok(f"{lang}: SelectedIndexChanged", w.wait(lambda: t("lblOut") == "Green"), t("lblOut"))
        if lang == "C":
            w.click(c["optTwo"])
            ok(f"{lang}: radio CheckedChanged", w.wait(lambda: t("lblEcho") == "True"), t("lblEcho"))
            ok(f"{lang}: radio group exclusive",
               w.user32.SendMessageW(c["optOne"], w.BM_GETCHECK, 0, 0) == 0 and
               w.user32.SendMessageW(c["optTwo"], w.BM_GETCHECK, 0, 0) == 1)
        t1 = w.wait(lambda: int(t("lblTicks") or 0) >= 3 and int(t("lblTicks")))
        time.sleep(0.4)
        ok(f"{lang}: Timer ticks", t1 and int(t("lblTicks") or 0) > t1, t("lblTicks"))
        w.click(c["cmdShow2"])
        f2 = w.form_window(p.pid, "Form2", 5)
        if ok(f"{lang}: Form2 shown (rad_show)", f2):
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
        ok(f"{lang}: Arabic text (UTF-8 -> UTF-16)", w.wait(lambda: t("lblOut") == "مرحبا بالعالم"), t("lblOut"))
        w.menu_command(f, (0, 0))
        f2 = w.form_window(p.pid, "Form2", 5)
        ok(f"{lang}: menu item Click", f2 and w.user32.IsWindowVisible(f2))
    finally:
        ok(f"{lang}: closing Form1 ends the program", w.stop(p, f))


# ------------------------------------------------------------------ 2. static library + handles ABI demo
def nomanifest(cc: str, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "e.c").write_text("\n", encoding="utf-8")
    subprocess.run([cc, "-c", str(folder / "e.c"), "-o", str(folder / "default-manifest.o")], check=True,
                   env=rg._tool_env(cc))
    return folder


def abi_tests():
    tc = win32_c.toolchain("c-bridge")
    out = SCRATCH / "abi"
    shutil.rmtree(out, ignore_errors=True)
    lib = rg.build_static_lib(out / "lib", tc["cc"], log=lambda s: None)
    ok("libradforms.a built", lib.is_file() and (out / "lib" / "radforms.h").is_file())
    nm = Path(tc["cc"]).with_name("nm.exe")
    syms = subprocess.run([str(nm), "-g", "--defined-only", str(lib)], capture_output=True, text=True).stdout
    defined = {ln.split()[-1] for ln in syms.splitlines() if " T " in ln}
    api = rg.api_description()
    missing = [f["name"] for f in api["functions"] if f["name"] not in defined]
    ok("every RF_API function is defined in the library", not missing, ", ".join(missing))
    ok("modules: rfmod_buttonx + rf_modules_register_all", {"rfmod_buttonx", "rf_modules_register_all"} <= defined)
    saved = json.loads(rg.API_JSON.read_text(encoding="utf-8")) if rg.API_JSON.is_file() else None
    ok("radforms_api.json is up to date", saved == json.loads(json.dumps(api)))
    ok("api json: callback signature (handle, event id, args, user)",
       any(cb["name"] == "rf_event_fn" and [p["type"] for p in cb["params"]] ==
           ["rf_handle", "int", "rf_event_args*", "void*"] for cb in api["callbacks"]))
    ok("api json: ButtonX module class", any(c["name"] == "ButtonX" and not c["builtin"] for c in api["classes"]))
    rc = rg.write_resources(out / "res", None, out, PublishConfig(app_name="AbiDemo"), gui=False)
    res = rg.compile_resources(tc["windres"], rc, log=lambda s: None)
    exe = out / "abi_demo.exe"
    cmd = [tc["cc"], "-B", str(nomanifest(tc["cc"], out / "nomf")) + os.sep, "-std=gnu11", "-Os", "-s", "-mwindows",
           "-ffunction-sections", "-Wl,--gc-sections", "-I", str(out / "lib"),
           str(HERE / "C" / "HandlesAbi" / "abi_demo.c"), str(res), "-L", str(out / "lib"), "-lradforms", "-static",
           *win32_c.WIN_LIBS, "-o", str(exe)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=rg._tool_env(tc["cc"]))
    if not ok("abi_demo links against libradforms.a", r.returncode == 0 and exe.is_file(), r.stdout + r.stderr):
        return
    size = exe.stat().st_size
    ok(f"abi_demo size {size // 1024} KB <= 150 KB", size <= 150_000)
    sysok, bad = system_only(exe)
    ok("abi_demo imports only system DLLs", sysok, ", ".join(bad))
    drive_abi(exe, "gcc")
    msvc = rg.build_msvc_lib(out / "msvc", log=lambda s: None)
    if msvc is None:
        print("   (Visual Studio C++ tools not installed: MSVC library skipped)")
        return
    from radide.languages.c_bridge import VS_INSTALLER, find_vcvars
    mexe = out / "msvc" / "abi_msvc.exe"
    bat = out / "msvc" / "link.bat"
    bat.write_text(f'@echo off\r\nset "PATH={VS_INSTALLER};%PATH%"\r\ncall "{find_vcvars()}" >nul\r\n'
                   f'cl /nologo /O1 /MT /utf-8 /I "{out / "msvc"}" "{HERE / "C" / "HandlesAbi" / "abi_demo.c"}" '
                   f'"{msvc}" /Fe:"{mexe}" /link /SUBSYSTEM:WINDOWS /ENTRY:mainCRTStartup /MANIFEST:EMBED '
                   f'/MANIFESTINPUT:"{out / "res" / "app.manifest"}"\r\n', encoding="utf-8")
    r = subprocess.run(["cmd", "/c", str(bat)], cwd=str(out / "msvc"), capture_output=True, text=True, errors="replace")
    if ok("radforms.lib (MSVC, /Zl) links the demo", mexe.is_file(), r.stdout + r.stderr):
        sysok, bad = system_only(mexe)
        ok("MSVC demo imports only system DLLs (static CRT)", sysok, ", ".join(bad))
        drive_abi(mexe, "msvc")


def drive_abi(exe: Path, tag: str):
    p = w.start(exe)
    f = None
    try:
        f = w.form_window(p.pid, "Main")
        c = w.wait(lambda: (lambda d: d if "bx2" in d else None)(w.children(f))) if f else None
        if not ok(f"{tag} abi: form + run-time control bx2", c):
            return
        info = c["lblInfo"]
        ok(f"{tag} abi: Load callback (abi version, rf_type, rf_create)",
           w.wait(lambda: w.get_text(info) == "abi 1, Form Main, bx2 ButtonX"), w.get_text(info))
        px = w.grab_pixels(c["bx1"], [(0.5, 0.15), (0.5, 0.85)])
        blueish = all(b > 150 and b > r + 60 for r, g, b in px)
        ok(f"{tag} abi: owner-drawn ButtonX painted (accent)", blueish, str(px))
        w.mouse_click(c["bx1"])
        ok(f"{tag} abi: Click + custom event (rf_raise)",
           w.wait(lambda: w.get_text(info) == "bx1 clicked 1 | custom event Clicked2 (custom)"), w.get_text(info))
        w.set_text(c["txtIn"], "abc")
        ok(f"{tag} abi: TextChanged + rf_prop_get", w.wait(lambda: w.get_text(info) == "typed: abc"), w.get_text(info))
        w.mouse_click(c["bx2"])
        ok(f"{tag} abi: theme Dark", w.wait(lambda: w.get_text(info) == "theme Dark"), w.get_text(info))
        time.sleep(0.3)
        bg = w.grab_pixels(f, [(330, 180)])[0]
        ok(f"{tag} abi: dark form background", max(bg) < 80, str(bg))
        w.user32.PostMessageW(f, w.WM_CLOSE, 0, 0)
        ok(f"{tag} abi: FormClosing cancel keeps the form",
           w.wait(lambda: w.get_text(info) == "close cancelled") and p.poll() is None, w.get_text(info))
    finally:
        ok(f"{tag} abi: second close ends the program", w.stop(p, f))


# ------------------------------------------------------------------ 3. checks / fallbacks
def check_tests():
    tmp = SCRATCH / "unsupported"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(HERE / "C" / "FormsDemo", tmp)
    form = json.loads((tmp / "Form2.form").read_text(encoding="utf-8"))
    form["controls"].append({"type": "ListView", "props": {"Name": "lvw1", "Left": 1, "Top": 1}})
    (tmp / "Form2.form").write_text(json.dumps(form), encoding="utf-8")
    pr = Project.load(tmp)
    reasons = win32_c.check(tmp, pr, PublishConfig())
    ok("unsupported control -> reason (falls back)", any("ListView" in r for r in reasons), str(reasons))
    ok("fallback kind of c-bridge is the GUI Bridge", build.fallback_kind("c-bridge") == "bridge")
    ok("auto build kind of c-bridge is native", build.detect_kind(Project.load(HERE / "C" / "FormsDemo"),
                                                                   PublishConfig()) == "native")
    (tmp / "Form1.c").write_text((tmp / "Form1.c").read_text(encoding="utf-8") +
                                 '\nvoid x_Click(void) { radcall("PyLib.hello", "[]"); }\n', encoding="utf-8")
    reasons = win32_c.check(tmp, Project.load(tmp), PublishConfig())
    ok("radcall to another project -> reason", any("PyLib.hello" in r for r in reasons), str(reasons))
    (tmp / "Form1.c").write_text((tmp / "Form1.c").read_text(encoding="utf-8") +
                                 '\nvoid y_Click(void) { rad_set("lblOut", "Blink", "1"); }\n', encoding="utf-8")
    reasons = win32_c.check(tmp, Project.load(tmp), PublishConfig())
    ok("unknown property in code -> reason", any("Blink" in r for r in reasons), str(reasons))
    mod = win32_c.fortran_native_module()
    ok("Fortran native module keeps the radgui API",
       all(s in mod for s in ("module radgui", "rad_line_in", "rad_native_handlers", "function rad_get",
                              "subroutine rad_call", "function radcall")) and "read(*, '(A)'" not in mod)
    text, images = rg.description(Project.load(HERE / "C" / "FormsDemo"), HERE / "C" / "FormsDemo")
    ok("form description: forms, menu, place, timer", text.startswith("RADF\t1") and "\nF\tForm2" in text and
       "\nM\t1\tmnuExit\tExit" in text and "\nC\tTimer\ttmrTick\t" in text and "\nL\t" in text)


def main():
    for lang in ("C", "Cpp", "Fortran"):
        exe = publish(lang)
        if exe is not None:
            drive_forms_demo(lang, exe)
    abi_tests()
    check_tests()
    failed = [n for n, good, _ in results if not good]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for n in failed:
        print("  FAILED:", n)
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
