"""Lesson blocks of the Assembly course (radide/tutorials/assembly).

Fence info strings (shared format: vb-basic/README.md, assembly/README.md):

* ```` ```asm run ```` - a NASM x64 Windows console program (``global main``, C runtime functions such as
  ``printf`` / ``puts`` / ``scanf`` declared with ``extern``).  Built with ``nasm -f win64`` and linked with gcc
  (MinGW-w64); ``text input`` after it is its stdin, ``text output`` the expected output.
* ```` ```asm form run ```` - the code of a GUI Bridge form (handlers ``<Control>_<Event>``), opened as a project
  of the Assembly language plugin; checked by assembling it.
* ```` ```asm16 run ```` - an 8086 / DOS program (``org 100h``, ``int 21h``) for the 8086 teaching emulator;
  checked with the emulator's headless runner when it is installed (docs/ASSEMBLY.md).
* ``exercise`` / ``solution`` as in the other courses; ``; #file: name.asm`` splits a block into files.
* hidden ``<!-- test: {"norun": true} -->``: only assemble and link (programs that open a MessageBox / window).
"""
from __future__ import annotations

import importlib
import os
import re
import subprocess
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
EXE = ".exe" if os.name == "nt" else ""
LANGS = ("asm", "asm16")
MISSING_NASM = "NASM غير موجود: نزّله من Tools (أو ضع nasm.exe في %LOCALAPPDATA%\\RADIDE\\tools\\nasm)"
MISSING_GCC = "gcc غير موجود (ثبّت MinGW في %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)"
MISSING_EMU = "محاكي 8086 غير مثبت في هذه النسخة من الـ IDE"


# ===================================================================== block facts
def is_gui(block) -> bool:
    return block.lang == "asm" and bool(block.form)


def reads_stdin(block) -> bool:
    if block.lang == "asm16":                 # DOS key / line input, emu8086.inc readers, BIOS keyboard
        return bool(re.search(r"\bmov\s+ah\s*,\s*(0?1h|1|0?ah|0x0?1|0x0a)\s*(;|$)|\bSCAN_NUM\b|\bGET_STRING\b|"
                              r"\bint\s+16h\b", block.code, re.I | re.M))
    return bool(re.search(r"^\s*extern\s+[\w,\s]*\b(scanf|getchar|gets|fgets)\b", block.code, re.I | re.M))


def default_file(block) -> str:
    if block.lang == "asm16":
        return "main.asm"
    return "Form1.asm" if is_gui(block) else "main.asm"


# ===================================================================== tools
def nasm() -> str:
    from ..foreign.asm_folder import find_tool
    return find_tool("nasm")


def gcc() -> str:
    from ..foreign.asm_folder import find_tool
    return find_tool("gcc")


def _env() -> dict:
    env = dict(os.environ)
    root = str(Path(__file__).resolve().parents[2])           # python -m radide.asm.build (forms)
    env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    g = gcc()
    if g:
        env["PATH"] = str(Path(g).parent) + os.pathsep + env.get("PATH", "")
    return env


def _sh(cmd, cwd: Path, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, env=_env(), capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return 1, "<<انتهت مهلة البناء>>"
    except OSError as e:
        return 1, str(e)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def _write(dest: Path, files: dict[str, str]) -> None:
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def build_console(files: dict[str, str], work: Path, link: bool = True) -> tuple[Path | None, str]:
    """nasm -f win64 every .asm (except %include'd .inc), then gcc links them; (exe or None, messages)."""
    n = nasm()
    if not n:
        return None, MISSING_NASM
    work = Path(work).resolve()
    _write(work, files)
    objs, log = [], []
    for fname in files:
        if not fname.lower().endswith((".asm", ".nasm")):
            continue
        obj = work / (Path(fname).stem + ".obj")
        code, out = _sh([n, "-f", "win64", "-g", "-F", "cv8", f"-I{work}{os.sep}", "-o", str(obj), fname], work)
        log.append(out)
        if code:
            return None, "".join(log)
        objs.append(str(obj))
    if not link:
        return work, "".join(log)
    g = gcc()
    if not g:
        return None, MISSING_GCC
    exe = work / ("a" + EXE)
    code, out = _sh([g, "-o", exe.name, *objs, "-lkernel32", "-luser32", "-lgdi32"], work)
    log.append(out)
    if code or not exe.exists():
        return None, "".join(log)
    return exe, "".join(log)


def run_console(files: dict[str, str], stdin: str | None, work: Path, timeout: int = 15) -> tuple[bool, str]:
    from . import _clean
    _clean(work)
    exe, out = build_console(files, work)
    if exe is None:
        return False, out
    try:
        r = subprocess.run([str(exe)], input=(stdin or "").encode("utf-8"), cwd=work, env=_env(),
                           capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return True, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    text = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    if r.returncode not in (0, None) and r.returncode & 0xC0000000 == 0xC0000000:
        text += f"\n<<توقف البرنامج بخطأ 0x{r.returncode & 0xFFFFFFFF:08X} (مثل وصول خاطئ للذاكرة)>>"
    return True, text


# ===================================================================== 8086 emulator
def emulator():
    """The 8086 teaching emulator (radide/emu8086: ``run_source(text, keys=...)``), or None."""
    try:
        m = importlib.import_module("radide.emu8086")
    except Exception:  # noqa: BLE001
        return None
    return m if callable(getattr(m, "run_source", None)) else None


def run_emu(source: str, stdin: str | None, max_steps: int = 2_000_000) -> tuple[bool, str]:
    """Assemble and run an 8086 program headless; stdin lines are typed on the keyboard (Enter = CR)."""
    m = emulator()
    if m is None:
        return False, MISSING_EMU
    keys = (stdin or "").replace("\r\n", "\n").replace("\n", "\r")
    try:
        r = m.run_source(source, keys=keys, max_steps=max_steps)
    except Exception as e:  # noqa: BLE001
        return False, f"خطأ في المحاكي: {e}"
    if r.get("errors"):
        return False, "\n".join(str(e) for e in r["errors"])
    out = str(r.get("output") or "")
    if not r.get("ok"):
        why = r.get("message") or r.get("reason") or "?"
        return False, out + f"\n<<توقف البرنامج في المحاكي: {why}>>"
    return True, out


# ===================================================================== projects ("جرّبه")
def _asm_plugin():
    """The NASM plugin (radide/languages/asm_nasm.py, id asm-nasm), else any .asm plugin, else None."""
    try:
        from ..languages import get_plugin, plugins_for_ext
        try:
            return get_plugin("asm-nasm")
        except KeyError:
            cands = plugins_for_ext(".asm")
            return cands[0] if cands else None
    except Exception:  # noqa: BLE001
        return None


def _emu_plugin():
    """The language plugin of 8086 emulator projects, when one is installed."""
    try:
        from ..languages import get_plugin
        return get_plugin("emu8086")             # radide/languages/emu8086.py
    except Exception:  # noqa: BLE001
        return None


def gui_controls(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls an assembly form's code names: rad_* macro arguments and handlers."""
    from . import CONTROL_PREFIXES
    names: list[str] = []
    rx = r"^\s*(?:rad_\w+|handler)\s+([a-z]{3}[A-Z]\w*?)(?:_[A-Z]\w*)?\s*(?:,|$)"
    for m in re.finditer(rx, code, re.M):
        if m.group(1) not in names:
            names.append(m.group(1))
    out = []
    for n in names:
        typ = next((t for p, t in CONTROL_PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n))
    return out


def _layout(form, code: str) -> None:
    """Form1 gets the controls the code names, in a column (like the other courses' forms)."""
    form.controls[:] = []                  # the template's controls make room for the lesson's
    y = 12
    for typ, cname in gui_controls(code):
        try:
            c = form.add(typ, 12, y)
        except KeyError:
            continue
        c.props["Name"] = cname
        if typ == "Label":
            c.props.update(Width=360, Text="")
        elif typ in ("TextBox", "ComboBox"):
            c.props["Width"] = 200
            if typ == "TextBox":
                c.props["Text"] = ""
        elif typ == "Button":
            c.props.update(Text=cname[3:], Width=140)
        elif typ == "ListBox":
            c.props.update(Width=260, Height=110)
            y += 80
        elif typ in ("CheckBox", "RadioButton"):
            c.props.update(Text=cname[3:], Width=200)
        y += 34
    try:
        form.props["Height"] = max(240, y + 60)
        form.props["Width"] = max(int(form.props.get("Width", 400)), 420)
    except (TypeError, ValueError):
        pass


def _make_form_project(plugin, files: dict[str, str], dest: Path, name: str, spec: dict | None = None):
    from ..model import Form
    project = plugin.create_new_project(dest, name, "nasm_forms")
    fname = project.forms[0] if project.forms else "Form1"
    code = files.get(f"{fname}.asm") or next(iter(files.values()), "")
    form = Form.load(project.form_path(fname))
    _layout(form, code)
    for cname, props in ((spec or {}).get("form") or {}).get("controls", {}).items():
        c = next((x for x in form.controls if x.props.get("Name") == cname), None)
        if c is not None:
            c.props.update(props)
    form.props.update({k: v for k, v in ((spec or {}).get("form") or {}).items() if k != "controls"})
    form.save(project.form_path(fname))
    _write(dest, files)
    (dest / plugin.designer_file(fname)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    for f in files:
        if f != f"{fname}.asm" and f.lower().endswith(".asm") and f not in project.modules:
            project.modules.append(f)
    project.save()
    return project


def make_project(block, files: dict[str, str], dest: Path, name: str):
    """A project of the Assembly language plugin (console / Windows Forms), an 8086 emulator project, or,
    without the plugin, a folder that opens in place as Assembly sources (radide/foreign/asm_folder.py)."""
    target = block.check_target()
    if block.lang == "asm16":
        _write(dest, files)
        plugin = _emu_plugin()
        if plugin is not None:
            try:
                return plugin.create_new_project(dest, name, "asm86_com")      # keeps our main.asm
            except Exception:  # noqa: BLE001 - the folder still opens in place (asm_folder: 8086 target)
                pass
        return None
    plugin = _asm_plugin()
    if plugin is None:
        _write(dest, files)
        return None
    if is_gui(block) or is_gui(target):
        return _make_form_project(plugin, files, dest, name, target.spec)
    _write(dest, files)
    project = plugin.create_new_project(dest, name, "nasm_console_x64")    # keeps our main.asm
    for fname in files:
        if fname.lower().endswith((".asm", ".inc")) and fname not in project.modules:
            project.modules.append(fname)
    project.startup = "main"
    project.save()
    return project


def project_files(folder: Path) -> dict[str, str]:
    out = {}
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in (".asm", ".inc") and not p.name.startswith(("_rad", "radgui")) \
                and "_designer" not in p.name:
            out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


# ===================================================================== checks ("تحقق")
def build_gui(files: dict[str, str], work: Path, spec: dict | None = None) -> tuple[bool, str]:
    """Form blocks: the plugin's own build when it is installed, else assemble the code (syntax check)."""
    from . import _clean
    _clean(work)
    plugin = _asm_plugin()
    note = ""
    if plugin is not None:
        try:
            from ..model import Project
            _make_form_project(plugin, files, work, "Check", spec)
            project = Project.load(work)
            if hasattr(plugin, "prepare"):
                plugin.prepare(work, project)
            main = plugin.main_source(project) if hasattr(plugin, "main_source") else None
            if main:
                (work / main[0]).write_text(main[1], encoding="utf-8")
            cmd = plugin.build_command(work, project)
            if cmd:
                r = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=work, env=_env(), capture_output=True,
                                   timeout=300, creationflags=NO_WINDOW)
                return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - fall back to assembling the code
            note = f"(بناء المشروع غير متاح: {e})\n"
    out_dir, out = build_console(files, work, link=False)
    return out_dir is not None, note + out


def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    target = block.check_target()
    files = project_files(folder) if folder else block_files(block, code)
    spec = target.spec or {}
    expected = target.expected
    if block.lang == "asm16":
        src = files.get("main.asm") or next(iter(files.values()), "")
        ok, out = run_emu(src, target.stdin)
        if not ok:
            return CheckResult(False, out, expected, ["تعذّر تشغيل البرنامج في المحاكي"])
        if expected is None and target is not block and target.code.strip():
            _ok, expected = run_emu(next(iter(block_files(target).values()), ""), target.stdin)
        if expected is None:
            return CheckResult(True, out, None, [], "يعمل البرنامج في المحاكي بلا أخطاء.")
        good = norm(out) == norm(expected)
        return CheckResult(good, out, expected, [] if good else ["المخرجات لا تطابق المطلوب"])
    if is_gui(block) or is_gui(target):
        ok, out = build_gui(files, work, spec)
        return CheckResult(ok, out, None, [] if ok else ["فشل البناء"],
                           "نجح البناء. هذا برنامج بواجهة رسومية: اضغط «جرّبه» وجرّب الأزرار بنفسك." if ok else "")
    if spec.get("norun"):
        from . import _clean
        _clean(work)
        exe, out = build_console(files, work)
        return CheckResult(exe is not None, out, None, [] if exe else ["فشل البناء"],
                           "نجح البناء والربط. هذا البرنامج يفتح نافذة: اضغط «جرّبه» لتراها." if exe else "")
    built, out = run_console(files, target.stdin, work)
    if not built:
        return CheckResult(False, out, expected, ["فشل البناء (أخطاء التجميع أو الربط بالأسفل)"])
    if expected is None and target is not block and target.code.strip():
        _b, expected = run_console(block_files(target), target.stdin, work.parent / (work.name + "-sol"))
    if expected is None:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    ok = norm(out) == norm(expected)
    return CheckResult(ok, out, expected, [] if ok else ["المخرجات لا تطابق المطلوب"])


def assemble_only(files: dict[str, str], work: Path) -> tuple[bool, str]:
    """Exercises: the starter code must at least assemble (it may not link or print the right thing yet)."""
    from . import _clean
    _clean(work)
    d, out = build_console(files, work, link=False)
    return d is not None, out


def available() -> dict:
    return {"nasm": nasm(), "gcc": gcc(), "emulator": bool(emulator()), "plugin": getattr(_asm_plugin(), "id", "")}


__all__ = ["LANGS", "available", "assemble_only", "build_console", "check", "default_file", "emulator",
           "is_gui", "make_project", "project_files", "reads_stdin", "run_console", "run_emu"]
