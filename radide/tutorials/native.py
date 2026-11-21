"""Lesson blocks of the native-language courses: C (gcc), Rust (cargo / rustc), Go and Fortran (gfortran).

Fence info strings (see vb-basic/README.md for the shared format):

* ```` ```c run ```` / ```` ```rust run ```` / ```` ```go run ```` / ```` ```fortran run ```` - a console
  program (its own ``main`` / ``program``); ``text input`` after it is its stdin, ``text output`` the expected
  output.  "جرّبه" opens it as a console project: c-bridge / go-bridge / fortran-bridge without forms (the plugins
  run such projects as plain console programs) or a rust-cargo project (Cargo.toml + src/main.rs).
* ```` ```<lang> form run ```` - Form1 code of a GUI Bridge project (handlers ``<Control>_<Event>``); the
  project gets Form1 with the controls the code names (``lblOut``, ``btnGo`` ...).  Checked by building it.
* Rust blocks that contain a ``// #file: Cargo.toml`` part are cargo projects (crates from crates.io); an
  eframe/egui project is a window, so it is checked by building it.
* ``exercise`` / ``solution`` work as in the other courses; ``// #file: name`` (``! #file:`` in Fortran) splits a
  block into files.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

LANGS = ("c", "rust", "go", "fortran")
ALIASES = {"c": "c", "rust": "rust", "rs": "rust", "go": "go", "golang": "go", "fortran": "fortran",
           "f90": "fortran"}
PLUGIN_IDS = {"c": "c-bridge", "rust": "rust-bridge", "go": "go-bridge", "fortran": "fortran-bridge"}
EXT = {"c": ".c", "rust": ".rs", "go": ".go", "fortran": ".f90"}
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
EXE = ".exe" if os.name == "nt" else ""
STDIN_RX = {
    "c": r"\bscanf\s*\(|\bfgets\s*\(|\bgetchar\s*\(|\bgets\s*\(",
    "rust": r"\bstdin\s*\(",
    "go": r"os\.Stdin|\bfmt\.Scan",
    "fortran": r"(?im)^\s*read\s*(\(\s*\*|\*|\(\s*unit\s*=\s*\*|\(\s*5)",
}


# ===================================================================== block facts
def is_gui(block) -> bool:
    """A form (GUI Bridge) block, or a C block that includes radgui.h."""
    return bool(block.form) or (block.lang == "c" and "radgui.h" in block.code)


def is_cargo(files: dict[str, str]) -> bool:
    return any(Path(f).name == "Cargo.toml" for f in files)


def is_window(block, files: dict[str, str]) -> bool:
    """Programs that open a window (forms, egui): checked by building them."""
    return is_gui(block) or (block.lang == "rust" and any("eframe" in t for t in files.values()))


def reads_stdin(block) -> bool:
    rx = STDIN_RX.get(block.lang)
    return bool(rx and re.search(rx, block.code))


def default_file(block) -> str:
    if is_gui(block):
        return "Form1" + EXT[block.lang]
    return {"c": "main.c", "rust": "src/main.rs", "go": "main.go", "fortran": "main.f90"}[block.lang]


def _norm_files(lang: str, files: dict[str, str]) -> dict[str, str]:
    """Rust console: main.rs / lib.rs / other .rs files of a cargo project live in src/."""
    if lang != "rust":
        return files
    out = {}
    for f, t in files.items():
        if f.endswith(".rs") and "/" not in f and not f.startswith("Form"):
            f = "src/" + f
        out[f] = t
    return out


def _write(dest: Path, files: dict[str, str]) -> None:
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


# ===================================================================== tools
def _plugin(lang: str):
    from ..languages import get_plugin
    return get_plugin(PLUGIN_IDS[lang])


def tool(lang: str) -> str:
    try:
        if lang == "c":
            return _plugin("c").gcc()
        return _plugin(lang).tool()
    except Exception:  # noqa: BLE001
        return ""


def rustc() -> str:
    cargo = tool("rust")
    if cargo:
        cand = Path(cargo).with_name("rustc" + EXE)
        if cand.exists():
            return str(cand)
    return shutil.which("rustc") or ""


MISSING = {
    "c": "gcc غير موجود (ثبّت MinGW في %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)",
    "rust": "Rust غير مثبت (ثبّته من https://rustup.rs ثم أعد تشغيل الـ IDE)",
    "go": "Go غير مثبت (winget install GoLang.Go أو فك ضغط Go في %LOCALAPPDATA%\\RADIDE\\toolchains\\go)",
    "fortran": "gfortran غير موجود (ثبّت MinGW مع gfortran في %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)",
}


def _env(lang: str) -> dict:
    env = dict(os.environ)
    t = tool(lang)
    dirs = [str(Path(t).parent)] if t else []
    try:                                           # gcc (DLLs) for the GNU tools
        from ..languages.c_bridge import find_native
        g = find_native(["gcc"])
        if g:
            dirs.append(str(Path(g).parent))
    except Exception:  # noqa: BLE001
        pass
    env["PATH"] = os.pathsep.join(dirs + [env.get("PATH", "")])
    if lang == "go":
        env.setdefault("GOTOOLCHAIN", "local")
    return env


# ===================================================================== projects ("جرّبه")
def make_project(block, files: dict[str, str], dest: Path, name: str):
    lang = block.lang
    files = _norm_files(lang, files)
    if is_gui(block):
        return make_gui(lang, files, dest, name)
    if lang == "rust":
        return _make_cargo(files, dest, name)
    from ..model import Project
    project = Project(dest, name, PLUGIN_IDS[lang])
    _write(dest, files)
    ext = EXT[lang]
    for fname in files:
        if fname.lower().endswith((ext, ".f95", ".f03", ".f08")) and fname not in project.modules:
            project.modules.append(fname)
    project.save()
    return project


def _make_cargo(files: dict[str, str], dest: Path, name: str):
    from ..languages import get_plugin
    _write(dest, files)
    if not (dest / "Cargo.toml").exists():
        (dest / "Cargo.toml").write_text(f'[package]\nname = "{re.sub(r"[^a-z0-9_]", "_", name.lower())}"\n'
                                         'version = "0.1.0"\nedition = "2021"\n\n[dependencies]\n', encoding="utf-8")
    template = "rust_library" if "src/lib.rs" in files and "src/main.rs" not in files else "rust_console"
    return get_plugin("rust-cargo").create_new_project(dest, name, template)


def make_gui(lang: str, files: dict[str, str], dest: Path, name: str):
    """A GUI Bridge Windows Application: Form1 with the controls its code uses (in a column) + Form1.<ext>."""
    from ..model import Form
    from ..workspace import create_project
    project = create_project(dest, name, PLUGIN_IDS[lang])
    form_file = "Form1" + EXT[lang]
    code = files.get(form_file) or next(iter(files.values()), "")
    form = Form.load(project.form_path("Form1"))
    _layout_controls(form, code)
    form.save(project.form_path("Form1"))
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        if fname == "Cargo.toml" and lang == "rust":
            continue                                   # the rust-bridge plugin manages its Cargo.toml
        p.write_text(text, encoding="utf-8")
        if fname != form_file and fname.lower().endswith(EXT[lang]) and fname not in project.modules:
            project.modules.append(fname)
    project.save()
    if lang == "rust" and "Cargo.toml" in files:       # [dependencies] of the lesson
        deps = re.search(r"(?ms)^\[dependencies\]\s*\n(.*?)(?=^\[|\Z)", files["Cargo.toml"])
        if deps and deps.group(1).strip():
            p = dest / "Cargo.toml"
            p.write_text(f'[package]\nname = "{re.sub(r"[^a-z0-9_]", "_", name.lower())}"\nversion = "0.1.0"\n'
                         f'edition = "2021"\nautobins = false\n\n[dependencies]\n{deps.group(1).strip()}\n',
                         encoding="utf-8")
    return project


def gui_controls(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls a form's code names: "lblX" / 'lblX' strings and <ctl>_<Event> handlers."""
    from . import CONTROL_PREFIXES
    names: list[str] = []
    rx = r"[\"']([a-z]{3}[A-Z]\w*)[\"']|\b(?:void|fn|func|subroutine)\s+([a-z]{3}[A-Z]\w*)_\w+\s*\("
    for m in re.finditer(rx, code):
        n = m.group(1) or m.group(2)
        if n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = next((t for p, t in CONTROL_PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n))
    return out


def _layout_controls(form, code: str) -> None:
    """Controls in a column, like the C++ lessons' forms (see tutorials._make_cpp_gui)."""
    y = 12
    for typ, cname in gui_controls(code):
        try:
            c = form.add(typ, 12, y)
        except KeyError:                       # a control type this IDE build does not have
            continue
        c.props["Name"] = cname
        if typ == "Label":
            c.props["Width"] = 360
            c.props["Text"] = ""
        elif typ in ("TextBox", "ComboBox"):
            c.props["Width"] = 200
            if typ == "TextBox":
                c.props["Text"] = ""
        elif typ == "Button":
            c.props["Text"] = cname[3:]
            c.props["Width"] = 120
        elif typ == "ListBox":
            c.props["Width"] = 260
            c.props["Height"] = 110
            y += 80
        elif typ in ("CheckBox", "RadioButton"):
            c.props["Text"] = cname[3:]
            c.props["Width"] = 200
        y += 34
    try:
        form.props["Height"] = max(int(form.props.get("Height", 300)), y + 60)
    except (TypeError, ValueError):
        pass


# ===================================================================== running (checks)
def _run_exe(exe: Path, stdin: str | None, cwd: Path, env: dict, timeout: int) -> str:
    try:
        r = subprocess.run([str(exe)], input=(stdin or "").encode("utf-8"), cwd=cwd, env=env, capture_output=True,
                           timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    return r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def _sh(cmd, cwd: Path, env: dict, timeout: int = 900, shell: bool = False) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=timeout, shell=shell,
                           creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return 1, "<<انتهت مهلة البناء>>"
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def fortran_order(files: dict[str, str]) -> list[str]:
    """Fortran sources ordered so that a module is compiled before the files that use it."""
    srcs = [f for f in files if f.lower().endswith((".f90", ".f95", ".f03", ".f08", ".f"))]
    defines, uses = {}, {}
    for f in srcs:
        text = re.sub(r"!.*", "", files[f])
        for m in re.findall(r"(?im)^\s*module\s+(?!procedure\b)(\w+)\s*$", text):
            defines[m.lower()] = f
        uses[f] = {u.lower() for u in re.findall(r"(?im)^\s*use\s*(?:,\s*\w+\s*::)?\s*(\w+)", text)}
    out: list[str] = []
    seen: set[str] = set()

    def visit(f):
        if f in seen:
            return
        seen.add(f)
        for u in sorted(uses.get(f, ())):
            if defines.get(u) and defines[u] != f:
                visit(defines[u])
        out.append(f)
    for f in srcs:
        visit(f)
    return out


def build_console(lang: str, files: dict[str, str], work: Path) -> tuple[Path | None, str]:
    """Compile a console block in *work* (already emptied); (exe or None, build messages)."""
    env = _env(lang)
    files = _norm_files(lang, files)
    _write(work, files)
    exe = work / ("a" + EXE)
    if lang == "c":
        gcc = tool("c")
        if not gcc:
            return None, MISSING["c"]
        srcs = [f for f in files if f.lower().endswith(".c")]
        code, out = _sh([gcc, "-std=gnu11", "-O1", "-fno-diagnostics-color", "-o", exe.name, *srcs, "-static",
                         "-lm"], work, env)
    elif lang == "fortran":
        gf = tool("fortran")
        if not gf:
            return None, MISSING["fortran"]
        code, out = _sh([gf, "-O1", "-fno-diagnostics-color", "-J", ".", "-o", exe.name, *fortran_order(files),
                         "-static"], work, env)
    elif lang == "go":
        go = tool("go")
        if not go:
            return None, MISSING["go"]
        if not (work / "go.mod").exists():
            (work / "go.mod").write_text("module lesson\n\ngo 1.21\n", encoding="utf-8")
        code, out = _sh([go, "build", "-o", exe.name, "."], work, env)
    elif lang == "rust":
        if is_cargo(files):
            cargo = tool("rust")
            if not cargo:
                return None, MISSING["rust"]
            target = work.parent / "_cargo-target"
            code, out = _sh([cargo, "build", "--quiet", "--color", "never", "--target-dir", str(target)], work, env)
            if code == 0:
                name = re.search(r'(?m)^name\s*=\s*"([^"]+)"', (work / "Cargo.toml").read_text(encoding="utf-8"))
                built = target / "debug" / ((name.group(1) if name else "lesson") + EXE)
                if built.exists():
                    shutil.copyfile(built, exe)
                else:
                    return None, out + "\n(لم يُنتج cargo ملفًا تنفيذيًا)"
        else:
            rc = rustc()
            if not rc:
                return None, MISSING["rust"]
            main = "src/main.rs" if "src/main.rs" in files else next(iter(files))
            code, out = _sh([rc, "--edition", "2021", "--color", "never", "-o", exe.name, main], work, env)
    else:
        return None, f"unknown language {lang}"
    if code != 0 or not exe.exists():
        return None, out
    return exe, out


def run_console(lang: str, files: dict[str, str], stdin: str | None, work: Path, timeout: int = 20
                ) -> tuple[bool, str]:
    """(built, program output or build errors)."""
    from . import _clean
    _clean(work)
    exe, out = build_console(lang, files, work)
    if exe is None:
        return False, out
    return True, _run_exe(exe, stdin, work, _env(lang), timeout)


def build_gui(lang: str, files: dict[str, str], work: Path) -> tuple[bool, str]:
    """GUI blocks (forms, egui): build the project with the IDE's own build command."""
    from . import _clean
    _clean(work)
    files = _norm_files(lang, files)
    env = _env(lang)
    if lang == "rust" and not any(f.startswith("Form1") for f in files):          # egui / cargo window
        if not tool("rust"):
            return False, MISSING["rust"]
        exe, out = build_console(lang, files, work)
        return exe is not None, out
    if not tool(lang):
        return False, MISSING[lang]
    from ..model import Project
    make_gui(lang, files, work, "Check")
    plugin = _plugin(lang)
    project = Project.load(work)
    plugin.prepare(work, project)
    cmd = plugin.build_command(work, project)
    if not cmd:
        return False, "لا يوجد مترجم"
    code, out = _sh(cmd, work, env, shell=True)
    return code == 0, out


def project_files(lang: str, folder: Path) -> dict[str, str]:
    """The learner's own source files of an opened lesson project (not the generated / client files)."""
    folder = Path(folder)
    skip = {"radgui.c", "radgui.h", "radgui.rs", "radgui.f90", "radlib.go", "radmain_gen.go", "_radmain.c",
            "_radmain.rs", "_radmain.f90"}
    out = {}
    exts = {"c": (".c", ".h"), "rust": (".rs", ".toml"), "go": (".go", ".mod"), "fortran": (".f90",)}[lang]
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if not p.is_file() or p.name in skip or p.name.startswith(("_rad", ".")) or "_designer" in p.name:
            continue
        if rel.split("/")[0] in ("target", "_build", "_radworker") or p.name == "Cargo.lock":
            continue
        if p.suffix.lower() in exts:
            out[rel] = p.read_text(encoding="utf-8", errors="replace")
    return out


def check(block, files: dict[str, str], work: Path):
    """The "تحقق" of a native block (files = the learner's files)."""
    from . import CheckResult, block_files, norm
    target = block.check_target()
    if is_window(block, files) or is_window(target, block_files(target)):
        ok, out = build_gui(block.lang, files, work)
        return CheckResult(ok, out, None, [] if ok else ["فشل البناء"],
                           "نجح البناء. هذا برنامج بواجهة رسومية: اضغط «جرّبه» وجرّب الأزرار بنفسك." if ok else "")
    expected = target.expected
    built, out = run_console(block.lang, files, target.stdin, work)
    if not built:
        return CheckResult(False, out, expected, ["فشل البناء (أخطاء الترجمة بالأسفل)"])
    if expected is None and target is not block and target.code.strip():
        _b, expected = run_console(block.lang, block_files(target), target.stdin, work.parent / (work.name + "-sol"))
    if expected is None:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    ok = norm(out) == norm(expected)
    return CheckResult(ok, out, expected, [] if ok else ["المخرجات لا تطابق المطلوب"])
