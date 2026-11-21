"""Arabic programming courses (radide/tutorials/<course>/course.json + NN-slug.md lessons).

* ``courses()``                 - every course folder with a course.json (BASIC first, then C++, then the rest).
* ``Lesson.items()``            - the lesson as a list of ("md", text) and ("block", Block) parts.
* ``make_project(block, dest)`` - turns a runnable block into a RAD IDE project (vb-basic console / form,
                                  cpp-bridge console program or cpp-bridge form with the controls the code uses).
* ``check(block, files)``       - runs the learner's code headless and compares it with the expected result
                                  (the "تحقق" button of the lesson viewer).

Block kinds (fence info strings) are described in vb-basic/README.md: ``vb run``, ``vb form run``,
``vb exercise`` / ``vb solution`` (also with ``form``), ``cpp run``, ``cpp exercise`` / ``cpp solution``,
``text output`` (expected output), ``text input`` (stdin), ``quiz`` (JSON), ``'#file: Name.ext`` lines split a
block into files.  Hidden ``<!-- test: {...} -->`` comments give InputBox answers / clicks for the checks.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
COURSE_ORDER = ("vb-basic", "cpp")
FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.M | re.S)
TEST = re.compile(r"<!--\s*test:\s*(\{.*?\})\s*-->\s*$", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
FILE_MARK = re.compile(r"^\s*(?:'|//|#|!)\s*#file:\s*(\S+)\s*$")
CODE_LANGS = {"vb": "vb", "basic": "vb", "vba": "vb", "cpp": "cpp", "c++": "cpp", "ring": "ring", "python": "py", "py": "py"}
# C / Rust / Go / Fortran lessons: radide/tutorials/native.py
NATIVE = ("c", "rust", "go", "fortran")
CODE_LANGS.update({"c": "c", "rust": "rust", "rs": "rust", "go": "go", "golang": "go", "fortran": "fortran", "f90": "fortran"})
# Ruby / Lua / Perl / PowerShell / Dart lessons: radide/tutorials/scripting.py
SCRIPT = ("ruby", "lua", "perl", "powershell", "dart")
CODE_LANGS.update({"ruby": "ruby", "rb": "ruby", "lua": "lua", "perl": "perl", "pl": "perl", "powershell": "powershell",
                   "ps1": "powershell", "pwsh": "powershell", "dart": "dart"})
# C# / Java lessons: radide/tutorials/csjava_support.py
CSJAVA = ("cs", "java")
CODE_LANGS.update({"csharp": "cs", "cs": "cs", "c#": "cs", "java": "java"})
# PHP lessons (php run = CLI script, php web run = web pages served by php -S): radide/tutorials/php_support.py
PHPL = ("php",)
CODE_LANGS.update({"php": "php"})
# Flutter screens / pygame scenes (guides flutter-mobile, games): radide/tutorials/flutter_support.py, game_support.py
MOBGAME = ("flutter", "game")
CODE_LANGS.update({"flutter": "flutter", "game": "game"})
# JavaScript / TypeScript lessons (Node.js console + GUI Bridge forms): radide/tutorials/js_support.py
JSL = ("js", "ts")
CODE_LANGS.update({"js": "js", "javascript": "js", "node": "js", "ts": "ts", "typescript": "ts"})
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def runs_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "RADIDE" / "tutorial-runs"


# ===================================================================== model
@dataclass
class Block:
    index: int                    # n-th fenced block of the lesson (0-based)
    info: str
    lang: str                     # vb | cpp | text | quiz | other
    role: str                     # run | exercise | solution | output | input | quiz | plain
    code: str
    line: int = 0
    form: bool = False
    spec: dict | None = None      # hidden test comment
    expected: str | None = None   # following ```text output
    stdin: str | None = None      # following ```text input
    quiz: dict | None = None
    solution: "Block | None" = None     # exercise -> its solution block
    compile_error: bool = False

    @property
    def runnable(self) -> bool:
        if self.lang in NATIVE or self.lang in SCRIPT or self.lang in CSJAVA or self.lang in PHPL or self.lang in JSL:
            return self.role in ("run", "solution")
        if self.lang in MOBGAME:
            return self.role in ("run", "solution")
        return self.lang in ("vb", "cpp", "ring", "py") and self.role in ("run", "solution")

    @property
    def gui(self) -> bool:
        """A C++ GUI Bridge block (Form1.cpp with event handlers)."""
        if self.lang in NATIVE:
            from .native import is_gui
            return is_gui(self)
        if self.lang in CSJAVA:
            from .csjava_support import is_gui as _cj_gui
            return _cj_gui(self)
        return self.lang == "cpp" and ("radgui.hpp" in self.code or bool(re.search(r"\bvoid\s+\w+_(Click|Load)\s*\(",
                                                                                   self.code)))

    def check_target(self) -> "Block":
        """The block whose expected output / input / test spec an exercise is checked against."""
        return self.solution if self.role == "exercise" and self.solution is not None else self

    def reads_stdin(self) -> bool:
        if self.lang in JSL:
            from .js_support import reads_stdin as _js_stdin
            return _js_stdin(self)
        if self.lang in PHPL:
            from .php_support import reads_stdin as _php_stdin
            return _php_stdin(self)
        if self.lang in SCRIPT:
            from .scripting import reads_stdin
            return not self.form and reads_stdin(self.lang, self.code)
        if self.lang in NATIVE:
            from .native import reads_stdin
            return reads_stdin(self)
        if self.lang in CSJAVA:
            from .csjava_support import reads_stdin as _cj_stdin
            return not self.gui and _cj_stdin(self)
        if self.lang == "py":
            return not self.form and bool(re.search(r"\binput\s*\(", self.code))
        if self.lang == "ring":
            return not self.form and bool(re.search(r"^\s*give\b", self.code, re.M | re.I))
        return self.lang == "cpp" and bool(re.search(r"\bstd::cin\b|\bcin\s*>>|\bgetline\s*\(|\bscanf\s*\(", self.code))


@dataclass
class Lesson:
    course: "Course"
    id: str
    file: str
    title_ar: str
    minutes: int = 0
    number: int = 0

    @property
    def path(self) -> Path:
        return self.course.folder / self.file

    def text(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def items(self) -> list[tuple[str, object]]:
        return parse(self.text())

    def blocks(self) -> list[Block]:
        return [b for k, b in self.items() if k == "block"]

    def heading(self) -> str:
        m = re.search(r"^#\s+(.+)$", self.text(), re.M)
        return m.group(1).strip() if m else self.title_ar


@dataclass
class Course:
    id: str
    folder: Path
    title_ar: str
    title_en: str
    language: str
    level: str = ""
    description_ar: str = ""
    lessons: list[Lesson] = field(default_factory=list)

    def lesson(self, lesson_id: str) -> Lesson | None:
        return next((x for x in self.lessons if x.id == lesson_id), None)

    def code_lang(self) -> str:
        return "cpp" if self.language.startswith("cpp") else "vb"


def load_course(folder: Path) -> Course | None:
    try:
        data = json.loads((folder / "course.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    c = Course(data.get("id", folder.name), folder, data.get("title_ar", folder.name),
               data.get("title_en", folder.name), data.get("language", ""), data.get("level", ""),
               data.get("description_ar", ""))
    for n, x in enumerate(data.get("lessons", []), 1):
        if (folder / x.get("file", "")).is_file():
            c.lessons.append(Lesson(c, x["id"], x["file"], x.get("title_ar", x["id"]), int(x.get("minutes", 0)), n))
    return c


def courses(root: Path | None = None) -> list[Course]:
    root = root or HERE
    out = [c for c in (load_course(d) for d in sorted(root.iterdir()) if (d / "course.json").is_file()) if c]
    rank = {cid: i for i, cid in enumerate(COURSE_ORDER)}
    return sorted(out, key=lambda c: (rank.get(c.id, 99), c.id))


def course(course_id: str) -> Course | None:
    return next((c for c in courses() if c.id == course_id), None)


CHM_NAMES = {"vb-basic": "RADIDE_BASIC_ar.chm", "cpp": "RADIDE_CPP_ar.chm"}


def chm_file(course_id: str) -> str:
    """The CHM file name of a course in docs/chm (tools/build_chm.py, Help > Help Files (CHM))."""
    return CHM_NAMES.get(course_id) or f"RADIDE_{re.sub(r'[^A-Za-z0-9]+', '_', course_id).upper()}_ar.chm"


# ===================================================================== parsing
def _classify(info: str) -> tuple[str, str, bool]:
    words = info.split()
    if not words:
        return "other", "plain", False
    head = words[0].lower()
    if head == "quiz":
        return "quiz", "quiz", False
    if head in ("text", "output"):
        if head == "output" or "output" in words[1:]:
            return "text", "output", False
        if "input" in words[1:]:
            return "text", "input", False
        return "text", "plain", False
    lang = CODE_LANGS.get(head, "other")
    rest = set(w.lower() for w in words[1:])
    role = "plain"
    for r in ("run", "exercise", "solution"):
        if r in rest:
            role = r
    return lang, role, "form" in rest


def parse(md: str) -> list[tuple[str, object]]:
    """Split a lesson into Markdown parts and Blocks; expected output / stdin / solutions are attached."""
    items: list[tuple[str, object]] = []
    blocks: list[Block] = []
    pos = 0
    for n, m in enumerate(FENCE.finditer(md)):
        before = md[pos:m.start()]
        spec, compile_error = None, False
        tail = before.rstrip()
        k = tail.rfind("<!--")
        if k >= 0 and tail.endswith("-->"):
            t = TEST.match(tail[k:])
            if t:
                try:
                    spec = json.loads(t.group(1))
                except ValueError:
                    spec = None
            compile_error = "compile-error" in tail[k:]
        text = COMMENT.sub("", before)
        if text.strip():
            items.append(("md", text))
        lang, role, form = _classify(m.group(1).strip())
        b = Block(n, m.group(1).strip(), lang, role, m.group(2), md.count("\n", 0, m.start()) + 1, form, spec,
                  compile_error=compile_error)
        if lang == "quiz":
            try:
                q = json.loads(b.code)
                if isinstance(q, dict) and {"question", "choices", "answer"} <= set(q):
                    b.quiz = q
            except ValueError:
                pass
        items.append(("block", b))
        blocks.append(b)
        pos = m.end()
    rest = COMMENT.sub("", md[pos:])
    if rest.strip():
        items.append(("md", rest))
    # attach output / input to the code block before them, exercises to their solutions
    for i, b in enumerate(blocks):
        if b.lang in ("vb", "cpp", "ring", "py", *NATIVE, *SCRIPT, *CSJAVA, *PHPL, *JSL, *MOBGAME) and b.role in ("run", "solution", "exercise"):
            for nxt in blocks[i + 1:]:
                if nxt.lang in ("vb", "cpp", "ring", "py", "quiz", *NATIVE, *SCRIPT, *CSJAVA, *PHPL, *JSL, *MOBGAME):
                    break
                if nxt.role == "output" and b.expected is None:
                    b.expected = nxt.code
                elif nxt.role == "input" and b.stdin is None:
                    b.stdin = nxt.code
        if b.role == "exercise":
            for nxt in blocks[i + 1:]:
                if nxt.lang == b.lang and nxt.role == "solution":
                    b.solution = nxt
                    break
                if nxt.lang == b.lang and nxt.role in ("exercise", "run"):
                    break
    return items


def split_files(code: str, default: str) -> dict[str, str]:
    """'#file: Name.ext (VB) or // #file: name.cpp (C++) lines split a block into files."""
    files: dict[str, str] = {}
    name, cur = default, []
    for ln in code.splitlines():
        mm = FILE_MARK.match(ln)
        if mm:
            if any(x.strip() for x in cur):
                files[name] = "\n".join(cur) + "\n"
            name, cur = mm.group(1), []
            continue
        cur.append(ln)
    if any(x.strip() for x in cur):
        files[name] = "\n".join(cur) + "\n"
    return files


def default_file(block: Block) -> str:
    if block.lang == "flutter":
        from .flutter_support import default_file as flutter_default
        return flutter_default(block)
    if block.lang == "game":
        return "Scene.py"
    if block.lang in JSL:
        from .js_support import default_file as js_default
        return js_default(block)
    if block.lang in PHPL:
        from .php_support import default_file as php_default
        return php_default(block)
    if block.lang in SCRIPT:
        from .scripting import default_file as script_default
        return script_default(block.lang, block.form)
    if block.lang in NATIVE:
        from .native import default_file as native_default
        return native_default(block)
    if block.lang in CSJAVA:
        from .csjava_support import default_file as cj_default
        return cj_default(block)
    if block.lang == "vb":
        return "Form1.frm" if block.form else "Module1.bas"
    if block.lang == "ring":
        return "Form1.ring" if block.form else "main.ring"
    if block.lang == "py":
        return "Form1.py" if block.form else "main.py"
    return "Form1.cpp" if block.gui else "main.cpp"


def block_files(block: Block, code: str | None = None) -> dict[str, str]:
    if block.lang in SCRIPT:         # also -- #file: (Lua)
        from .scripting import split_files as script_split
        return script_split(block.code if code is None else code, default_file(block))
    return split_files(block.code if code is None else code, default_file(block))


# ===================================================================== projects
def run_folder(course_id: str, lesson_id: str, block_index: int) -> Path:
    return runs_root() / course_id / f"{lesson_id}-{block_index}"


def _clean(dest: Path) -> None:
    if dest.exists():
        for p in dest.iterdir():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    p.unlink()
                except OSError:
                    pass
    dest.mkdir(parents=True, exist_ok=True)


def make_project(block: Block, dest: Path, code: str | None = None, name: str = "Lesson"):
    """Write *block* (or the learner's *code* for it) as a RAD IDE project in *dest* (emptied first)."""
    _clean(dest)
    if block.lang == "vb":
        return _make_vb(block_files(block, code), dest, name)
    if block.lang == "cpp":
        files = block_files(block, code)
        if block.gui:
            return _make_cpp_gui(files, dest, name)
        return _make_cpp_console(files, dest, name)
    if block.lang == "ring":
        from . import ring_support as R
        files = block_files(block, code)
        target = block.check_target()
        return (R.make_form(files, dest, name, target.spec) if block.form or target.form
                else R.make_console(files, dest, name))
    if block.lang == "py":
        from .pyrun import make_py_project
        return make_py_project(block, block_files(block, code), dest, name)
    if block.lang in NATIVE:
        from . import native
        return native.make_project(block, block_files(block, code), dest, name)
    if block.lang in SCRIPT:
        from . import scripting
        target = block.check_target()
        return scripting.make_project(block.lang, block_files(block, code), dest, name, block.form or target.form,
                                      target.spec)
    if block.lang in CSJAVA:
        from . import csjava_support
        return csjava_support.make_project(block, block_files(block, code), dest, name)
    if block.lang in PHPL:
        from . import php_support
        return php_support.make_project(block, block_files(block, code), dest, name)
    if block.lang in JSL:
        from . import js_support
        return js_support.make_project(block, block_files(block, code), dest, name)
    if block.lang in MOBGAME:
        from . import flutter_support, game_support
        mod = flutter_support if block.lang == "flutter" else game_support
        return mod.make_project(block_files(block, code), block.check_target().spec, dest, name)
    raise ValueError(f"block '{block.info}' cannot be run")


def _make_vb(files: dict[str, str], dest: Path, name: str):
    """The same as make_project() of vb-basic/tools/check_lessons.py (and File > Import VB6 for .frm text)."""
    from ..importers.python_import import ImportReport
    from ..importers.vb6_import import _FrmConverter, parse_frm
    from ..model import Project
    project = Project(dest, name, "vb-basic")
    for fname, text in files.items():
        if fname.lower().endswith(".frm"):
            root, body = parse_frm(text)
            form = _FrmConverter(ImportReport(), fname).convert(root)
            form.save(project.form_path(form.name))
            (dest / f"{form.name}.bas").write_text(body, encoding="utf-8")
            project.forms.append(form.name)
            if not project.startup:
                project.startup = form.name
        else:
            (dest / fname).write_text(text, encoding="utf-8")
            project.modules.append(fname)
    if not project.startup:
        project.startup = "Sub Main"
    project.save()
    return project


def _make_cpp_console(files: dict[str, str], dest: Path, name: str):
    """A cpp-bridge project without forms and with its own main(): it runs as a plain console program."""
    from ..model import Project
    project = Project(dest, name, "cpp-bridge")
    for fname, text in files.items():
        (dest / fname).write_text(text, encoding="utf-8")
        if fname.lower().endswith((".cpp", ".cc", ".cxx")):
            project.modules.append(fname)
    project.save()
    _copy_bridge_client(dest)
    return project


CONTROL_PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"),
                    ("lst", "ListBox"), ("cbo", "ComboBox"), ("cmb", "ComboBox"), ("chk", "CheckBox"),
                    ("opt", "RadioButton"), ("rdo", "RadioButton"), ("tmr", "Timer"), ("pic", "PictureBox"),
                    ("prg", "ProgressBar"), ("grp", "GroupBox"))


def gui_controls(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls a C++ form's code uses: names in rad::set("lblX", ...) / handlers."""
    names: list[str] = []
    for m in re.finditer(r'"([a-z]{3}[A-Z]\w*)"|\bvoid\s+([a-z]{3}[A-Z]\w*)_\w+\s*\(', code):
        n = m.group(1) or m.group(2)
        if n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = next((t for p, t in CONTROL_PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n))
    return out


def _make_cpp_gui(files: dict[str, str], dest: Path, name: str):
    """A cpp-bridge Windows Application: Form1 with the controls the code uses (in a column), Form1.cpp."""
    from ..model import Form
    from ..workspace import create_project
    project = create_project(dest, name, "cpp-bridge")
    code = files.get("Form1.cpp") or next(iter(files.values()), "")
    form = Form.load(project.form_path("Form1"))
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
    form.save(project.form_path("Form1"))
    for fname, text in files.items():
        (dest / fname).write_text(text, encoding="utf-8")
        if fname != "Form1.cpp" and fname.lower().endswith((".cpp", ".cc")) and fname not in project.modules:
            project.modules.append(fname)
    project.save()
    return project


def _copy_bridge_client(dest: Path) -> None:
    try:
        from ..languages import get_plugin
        plugin = get_plugin("cpp-bridge")
        for fname, src in plugin.client_files().items():
            if not (dest / fname).exists():
                shutil.copyfile(src, dest / fname)
    except Exception:  # noqa: BLE001 - the plugin copies them again when it builds
        pass


# ===================================================================== checks ("تحقق")
@dataclass
class CheckResult:
    ok: bool
    output: str = ""
    expected: str | None = None
    problems: list[str] = field(default_factory=list)
    note: str = ""


def norm(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return lines


def gpp() -> str | None:
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "toolchains" / "mingw64" / "bin" / "g++.exe"
    if cand.is_file():
        return str(cand)
    try:
        from ..languages import get_plugin
        g = get_plugin("cpp-bridge").gcc()
        if g:
            return g
    except Exception:  # noqa: BLE001
        pass
    return shutil.which("g++")


def run_cpp_console(files: dict[str, str], stdin: str | None, work: Path, timeout: int = 15) -> tuple[bool, str]:
    """Compile with g++ -std=gnu++17 (like the IDE) and run with *stdin*; (built, output or build errors)."""
    compiler = gpp()
    if not compiler:
        return False, "g++ غير موجود (ثبّت MinGW في %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)"
    _clean(work)
    sources = []
    for fname, text in files.items():
        (work / fname).write_text(text, encoding="utf-8")
        if fname.lower().endswith((".cpp", ".cc", ".cxx")):
            sources.append(fname)
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get("PATH", ""))
    r = subprocess.run([compiler, "-std=gnu++17", "-O1", "-fno-diagnostics-color", "-o", "a.exe", *sources,
                        "-static"], cwd=work, env=env, capture_output=True, creationflags=NO_WINDOW)
    if r.returncode:
        return False, (r.stdout + r.stderr).decode("utf-8", "replace")
    try:
        r = subprocess.run([str(work / "a.exe")], input=(stdin or "").encode("utf-8"), cwd=work, env=env,
                           capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return True, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    return True, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def run_vb(files: dict[str, str], spec: dict | None, work: Path, timeout: int = 30) -> dict:
    """Run a BASIC project headless (InputBox answers / clicks from *spec*) with the child runner of
    vb-basic/tools/check_lessons.py; returns its result dict (output, msgbox, values, error, fatal).
    *files* = None runs the project already in *work*."""
    if files:
        _clean(work)
        _make_vb(files, work, "Lesson")
    spec = dict(spec or {})
    sp, rp = work / "_spec.json", work / "_result.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    if rp.exists():
        rp.unlink()
    runner = HERE / "vb-basic" / "tools" / "check_lessons.py"
    try:
        subprocess.run([sys.executable, str(runner), "--child", str(work), str(sp), str(rp)], cwd=str(work),
                       timeout=spec.get("timeout", timeout), capture_output=True, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return {"fatal": "انتهت المهلة: هل في البرنامج حلقة لا تنتهي؟", "output": ""}
    if not rp.exists():
        return {"fatal": "توقف البرنامج دون نتيجة", "output": ""}
    return json.loads(rp.read_text(encoding="utf-8"))


def check(block: Block, code: str | None = None, folder: Path | None = None, work: Path | None = None) -> CheckResult:
    """Run the learner's version of *block* (an exercise: its starter code edited; or any runnable block) and
    compare it with the expected output / the hidden test of the solution.  *folder* = a project folder the
    learner edited in the IDE (its files are used instead of *code*)."""
    target = block.check_target()
    work = work or Path(tempfile.mkdtemp(prefix="radtut-check-"))
    expected = target.expected
    if block.lang == "cpp":
        files = _project_files(folder, ".cpp") if folder else block_files(block, code)
        if block.gui or target.gui:
            ok, out = _build_only(files, work)
            return CheckResult(ok, out, None, [] if ok else ["فشل البناء"],
                               "نجح البناء. هذا برنامج بواجهة رسومية: اضغط «جرّبه» وجرّب الأزرار بنفسك." if ok else "")
        built, out = run_cpp_console(files, target.stdin, work)
        if not built:
            return CheckResult(False, out, expected, ["فشل البناء (أخطاء الترجمة بالأسفل)"])
        if expected is None and target is not block and target.code.strip():
            _b, expected = run_cpp_console(block_files(target), target.stdin, work.parent / (work.name + "-sol"))
        ok = expected is not None and norm(out) == norm(expected)
        return CheckResult(ok, out, expected, [] if ok else ["المخرجات لا تطابق المطلوب"])
    if block.lang == "vb":
        if folder:
            _clean(work)
            for p in Path(folder).iterdir():
                if p.is_file() and not p.name.startswith("_"):
                    shutil.copyfile(p, work / p.name)
            files = None
        else:
            files = block_files(block, code)
        spec = target.spec or {}
        r = run_vb(files, spec, work)
        problems = []
        if r.get("fatal"):
            problems.append("خطأ: " + str(r["fatal"]))
        got_err, want_err = r.get("error"), spec.get("error")
        if want_err is None and got_err:
            problems.append(f"خطأ تشغيل {got_err.get('number')}: {got_err.get('description')} "
                            f"(السطر {got_err.get('line')})")
        elif want_err is not None and (not got_err or got_err.get("number") != want_err):
            problems.append(f"كان متوقعًا خطأ التشغيل رقم {want_err}")
        if expected is None and target is not block and not spec.get("expect") and "msgbox" not in spec:
            expected = run_vb(block_files(target), spec, work.parent / (work.name + "-sol")).get("output")
        if expected is not None and norm(r.get("output", "")) != norm(expected):
            problems.append("المخرجات لا تطابق المطلوب")
        if "msgbox" in spec and r.get("msgbox") != spec["msgbox"]:
            problems.append("رسائل MsgBox: المتوقع " + " | ".join(spec["msgbox"]) + " ، الناتج " +
                            " | ".join(r.get("msgbox") or []))
        for k, v in (spec.get("expect") or {}).items():
            got = (r.get("values") or {}).get(k)
            if str(v).startswith("re:") and got is not None and re.fullmatch(str(v)[3:], got):
                continue
            if got != str(v):
                problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
        if expected is None and not spec.get("expect") and "msgbox" not in spec and not problems:
            return CheckResult(True, r.get("output", ""), None, [], "يعمل البرنامج بلا أخطاء.")
        out = r.get("output", "")
        if r.get("msgbox"):
            out += ("\n" if out else "") + "\n".join(f"[MsgBox] {m}" for m in r["msgbox"])
        return CheckResult(not problems, out, expected, problems)
    if block.lang == "ring":
        from . import ring_support as R
        return R.check(block, code, folder, work, norm, CheckResult, block_files)
    if block.lang == "py":
        from .pyrun import check_py
        files = _project_files(folder, ".py") if folder else block_files(block, code)
        return check_py(block, files, work)
    if block.lang in NATIVE:
        from . import native
        files = native.project_files(block.lang, folder) if folder else block_files(block, code)
        return native.check(block, files, work)
    if block.lang in SCRIPT:
        from . import scripting
        return scripting.check(block, code, folder, work)
    if block.lang in CSJAVA:
        from . import csjava_support
        return csjava_support.check(block, code, folder, work, norm, CheckResult, block_files)
    if block.lang in PHPL:
        from . import php_support
        return php_support.check(block, code, folder, work, norm, CheckResult, block_files)
    if block.lang in JSL:
        from . import js_support
        return js_support.check(block, code, folder, work, norm, CheckResult, block_files)
    if block.lang in MOBGAME:
        from . import flutter_support, game_support
        mod = flutter_support if block.lang == "flutter" else game_support
        return mod.check(block, code, folder, work, norm, CheckResult)
    return CheckResult(False, "", None, ["هذه الكتلة لا تُشغَّل"])


def _project_files(folder: Path, ext: str) -> dict[str, str]:
    out = {}
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in (ext, ".h", ".hpp") and not p.name.startswith(("_rad", "radgui")):
            out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


def _build_only(files: dict[str, str], work: Path) -> tuple[bool, str]:
    """GUI blocks: build as a cpp-bridge project with the IDE's own build command."""
    from ..languages import get_plugin
    _clean(work)
    proj = _make_cpp_gui(files, work, "Check")
    plugin = get_plugin("cpp-bridge")
    for fname, src in plugin.client_files().items():
        shutil.copyfile(src, work / fname)
    main = plugin.main_source(proj)
    if main:
        (work / main[0]).write_text(main[1], encoding="utf-8")
    cmd = plugin.build_command(work, proj)
    if not cmd:
        return False, "لا يوجد مترجم C++"
    r = subprocess.run(cmd, shell=True, cwd=work, capture_output=True, creationflags=NO_WINDOW)
    return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")


def search(query: str) -> list[tuple[Course, Lesson, str]]:
    """Lessons whose title or text contain *query* (case-insensitive), with a short snippet."""
    q = query.strip().lower()
    out = []
    if not q:
        return out
    for c in courses():
        for les in c.lessons:
            text = COMMENT.sub("", les.text())
            low = text.lower()
            i = low.find(q)
            if q in les.title_ar.lower() or i >= 0:
                s = text[max(0, i - 40): i + len(q) + 60].replace("\n", " ") if i >= 0 else les.title_ar
                out.append((c, les, s.strip()))
    return out


__all__ = ["Block", "CheckResult", "Course", "Lesson", "check", "chm_file", "course", "courses", "gui_controls",
           "make_project",
           "parse", "run_folder", "runs_root", "search", "split_files"]
