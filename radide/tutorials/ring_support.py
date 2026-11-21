"""Ring blocks of the tutorials (course "ring"): projects, headless checks and highlighting.

Block kinds (see ring/README.md):

* ```` ```ring run ````        a console program -> a "Ring (Console / Web / Library)" project (ring-app) with
                               main.ring as its startup file, run like ``ring main.ring`` (```text input = stdin).
* ```` ```ring form run ````   the code file of a RingQt form (Form1.ring: ``load "Form1_designer.ring"`` + the
                               event handlers) -> a ring-qt project whose Form1 holds the controls the code uses
                               (names with a VB prefix: btn, txt, lbl, lst, cbo, chk, opt, tmr, prg ...), laid out
                               in a column; the hidden test comment can give captions / sizes:
                               ``{"form": {"Text": "...", "controls": {"btnHello": {"Text": "...", "Left": 10}}}}``.
* ``exercise`` / ``solution``  as for the other courses (``ring exercise``, ``ring form solution`` ...).

Hidden ``<!-- test: {...} -->`` keys used by check():
  ``norun``  only compile (``ring file -norun``): games, network examples, programs that need a window.
  ``do``     form blocks: Ring statements run after Form1_Create(), e.g. ``["txtName.setText('Ali')",
             "btnHello_Click()"]`` (the form is never shown: QT_QPA_PLATFORM=offscreen).
  ``expect`` form blocks: {"Ring expression": "expected text"}, e.g. {"lblResult.text()": "Hello Ali"}.
  ``error``  a run-time error is expected (its text, e.g. "R24"); the output before it is still compared.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
MARK = "@@RADTUT@@ "
PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"), ("lst", "ListBox"),
            ("cbo", "ComboBox"), ("chk", "CheckBox"), ("opt", "RadioButton"), ("tmr", "Timer"),
            ("prg", "ProgressBar"), ("grp", "GroupBox"), ("num", "NumericUpDown"), ("trk", "TrackBar"))
RX_NAME = re.compile(r"\b(?:" + "|".join(p for p, _t in PREFIXES) + r")[A-Z][A-Za-z0-9]*")
RX_ERROR = re.compile(r"Error \([A-Z]\d+\)")


# ===================================================================== interpreter
def ring_exe() -> str | None:
    try:
        from ..languages import get_plugin
        exe = get_plugin("ring-qt").find_interpreter("")
        if exe:
            return exe
    except Exception:  # noqa: BLE001
        pass
    for cand in (r"C:\ring\ring\bin\ring.exe", r"C:\ring\bin\ring.exe"):
        if Path(cand).is_file():
            return cand
    return shutil.which("ring")


def _env() -> dict:
    return dict(os.environ, QT_QPA_PLATFORM="offscreen")


def run_ring(args: list[str], cwd: Path, stdin: str | None = None, timeout: int = 20) -> tuple[bool, str]:
    """(finished, output) of ``ring <args>`` in *cwd*."""
    exe = ring_exe()
    if not exe:
        return False, "لم يُعثر على مفسّر Ring (ثبّت Ring في C:\\ring)"
    try:
        r = subprocess.run([exe, *args], cwd=str(cwd), input=(stdin or "").encode("utf-8"), capture_output=True,
                           timeout=timeout, env=_env(), creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return False, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    out = (r.stdout + r.stderr).decode("utf-8", "replace").replace("\r\n", "\n")
    return True, out


# ===================================================================== projects
def controls(code: str, spec: dict | None = None) -> list[tuple[str, str]]:
    """(type, name) of the controls a form's code uses, then the extra ones of the test spec."""
    names: list[str] = []
    for m in RX_NAME.finditer(code):
        if m.group(0) not in names:
            names.append(m.group(0))
    extra = ((spec or {}).get("form") or {}).get("controls") or {}
    for n in extra:
        if n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = (extra.get(n) or {}).get("Type") or next((t for p, t in PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n))
    return out


def _clean(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)


def make_console(files: dict[str, str], dest: Path, name: str):
    from ..model import Project
    _clean(dest)
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    first = "main.ring" if "main.ring" in files else next(iter(files))
    modules = [first] + [f for f in files if f.endswith(".ring") and f != first]
    project = Project(dest, name, "ring-app", [], first[:-5], modules)
    project.save()
    return project


def make_form(files: dict[str, str], dest: Path, name: str, spec: dict | None = None):
    """A ring-qt Windows Application: Form1 with the controls the code uses, Form1.ring = the block."""
    from ..languages import get_plugin
    from ..model import Form
    from ..workspace import create_project
    _clean(dest)
    project = create_project(dest, name, "ring-qt")
    plugin = get_plugin("ring-qt")
    code = files.get("Form1.ring") or next(iter(files.values()), "")
    fspec = (spec or {}).get("form") or {}
    form = Form.load(project.form_path("Form1"))
    for k in ("Text", "Width", "Height", "BackColor"):
        if k in fspec:
            form.props[k] = fspec[k]
    y, width = 12, 0
    extra = fspec.get("controls") or {}
    for typ, cname in controls(code, spec):
        try:
            c = form.add(typ, 12, y)
        except KeyError:                       # a control type this IDE build does not have
            continue
        c.props["Name"] = cname
        step = 34
        if typ == "Label":
            c.props.update(Width=360, Text="")
        elif typ == "TextBox":
            c.props.update(Width=220, Text="")
        elif typ == "ComboBox":
            c.props["Width"] = 220
        elif typ == "Button":
            c.props.update(Text=cname[3:], Width=140, Height=30)
            step = 40
        elif typ == "ListBox":
            c.props.update(Width=280, Height=130)
            step = 140
        elif typ in ("CheckBox", "RadioButton"):
            c.props.update(Text=cname[3:], Width=220)
        elif typ == "ProgressBar":
            c.props["Width"] = 280
        elif typ == "Timer":
            step = 0
        for k, v in (extra.get(cname) or {}).items():
            if k != "Type":
                c.props[k] = v
        if typ != "Timer":
            try:
                y = max(y + step, int(c.props.get("Top", 0)) + int(c.props.get("Height", 24)) + 10)
                width = max(width, int(c.props.get("Left", 0)) + int(c.props.get("Width", 100)) + 24)
            except (TypeError, ValueError):
                y += step
    try:
        if "Height" not in fspec:
            form.props["Height"] = max(200, y + 20)
        if "Width" not in fspec:
            form.props["Width"] = max(320, width)
    except (TypeError, ValueError):
        pass
    form.save(project.form_path("Form1"))
    for fname, text in files.items():
        (dest / fname).write_text(text, encoding="utf-8")
        if fname != "Form1.ring" and fname.endswith(".ring") and fname not in project.modules:
            project.modules.append(fname)
    (dest / plugin.designer_file("Form1")).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    project.save()
    return project


# ===================================================================== checks
def _ring_files(folder: Path) -> list[str]:
    return sorted(f.name for f in folder.glob("*.ring")
                  if not f.name.startswith("_") and not f.stem.endswith("_designer"))


def run_form(folder: Path, spec: dict | None, timeout: int = 25) -> tuple[bool, str, dict]:
    """Create Form1 headless, run the spec's ``do`` statements, evaluate the ``expect`` expressions.
    (finished, program output without the markers, {expression: value})."""
    from ..languages.ring_qt import write_runtime
    spec = spec or {}
    write_runtime(folder)
    files = _ring_files(folder)
    files.sort(key=lambda f: f != "Form1.ring")
    lines = ["# generated by the RAD IDE tutorials - safe to delete"]
    lines += [f'load "{f}"' for f in files]
    lines += ["", "func main", "    oApp = new qApp", "    Form1_Create()"]
    lines += ["    " + s for s in spec.get("do", [])]
    for i, expr in enumerate(spec.get("expect") or {}):
        lines.append(f'    see "{MARK}{i}=" + ({expr}) + nl')
    (folder / "_radtut_test.ring").write_text("\n".join(lines) + "\n", encoding="utf-8")
    done, out = run_ring(["_radtut_test.ring"], folder, None, timeout)
    values, keep = {}, []
    exprs = list(spec.get("expect") or {})
    for ln in out.split("\n"):
        if ln.startswith(MARK):
            k, _s, v = ln[len(MARK):].partition("=")
            if k.isdigit() and int(k) < len(exprs):
                values[exprs[int(k)]] = v
        else:
            keep.append(ln)
    return done, "\n".join(keep), values


def syntax_only(files: dict[str, str], work: Path, form: bool) -> tuple[bool, str]:
    if form:
        make_form(files, work, "Check")
    else:
        make_console(files, work, "Check")
    main = "Form1.ring" if form else ("main.ring" if "main.ring" in files else next(iter(files)))
    _d, out = run_ring([main, "-norun"], work)
    return not RX_ERROR.search(out), out


def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    """The Ring branch of radide.tutorials.check()."""
    target = block.check_target()
    spec = target.spec or {}
    expected = target.expected
    form = block.form or target.form
    if folder:
        files = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in Path(folder).glob("*.ring")
                 if not p.name.startswith("_") and not p.stem.endswith("_designer")}
    else:
        files = block_files(block, code)
    if spec.get("norun"):
        ok, out = syntax_only(files, work, form)
        return CheckResult(ok, out, None, [] if ok else ["أخطاء في الكود (بالأسفل)"],
                           "الكود سليم. هذا البرنامج يفتح نافذة أو يحتاج الإنترنت: اضغط «جرّبه» لتراه يعمل." if ok else "")
    problems = []
    values: dict = {}
    if form:
        make_form(files, work, "Check", spec)
        done, out, values = run_form(work, spec)
    else:
        make_console(files, work, "Check")
        main = "main.ring" if "main.ring" in files else next(iter(files))
        done, out = run_ring([main], work, target.stdin)
    if not done:
        problems.append(out.strip())
    err = RX_ERROR.search(out)
    if err and not spec.get("error"):
        problems.append("خطأ أثناء التشغيل (التفاصيل في الناتج)")
    elif spec.get("error") and (not err or spec["error"] not in out):
        problems.append(f"كان متوقعًا خطأ التشغيل {spec['error']}")
    if expected is not None:
        got = norm(out)
        if spec.get("error") and err:            # compare only what was printed before the error
            got = norm(out[:err.start()].rsplit("\n", 1)[0])
        if got != norm(expected):
            problems.append("المخرجات لا تطابق المطلوب")
    for k, v in (spec.get("expect") or {}).items():
        if values.get(k) != str(v):
            problems.append(f"{k}: المتوقع «{v}» والناتج «{values.get(k)}»")
    if values:
        out = out.rstrip("\n") + ("\n" if out.strip() else "") + "\n".join(f"{k} = {v}" for k, v in values.items())
    if expected is None and not spec.get("expect") and not problems:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    return CheckResult(not problems, out, expected, problems)


# ===================================================================== highlighting
def lexer():
    """A small Pygments lexer for Ring (Pygments has none)."""
    from pygments.lexer import RegexLexer, words
    from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String, Text

    class RingLexer(RegexLexer):
        name, aliases = "Ring", ["ring"]
        flags = re.IGNORECASE | re.MULTILINE
        kw = ("again", "and", "but", "bye", "call", "case", "catch", "class", "def", "do", "done", "else", "elseif",
              "end", "endclass", "endfor", "endfunc", "endif", "endpackage", "endswitch", "endtry", "endwhile",
              "exit", "for", "from", "func", "function", "get", "give", "if", "import", "in", "load", "loop", "new",
              "next", "not", "off", "ok", "on", "or", "other", "package", "private", "put", "return", "see",
              "step", "switch", "to", "try", "while", "break", "continue", "self", "this", "foreach", "elif")
        tokens = {"root": [
            (r"#.*?$|//.*?$", Comment.Single),
            (r"/\*[\s\S]*?\*/", Comment.Multiline),
            (r'"[^"]*"|\'[^\']*\'|`[^`]*`', String),
            (words(kw, prefix=r"\b", suffix=r"\b"), Keyword),
            (words(("true", "false", "nl", "null", "tab", "cr"), prefix=r"\b", suffix=r"\b"), Keyword.Constant),
            (r"\b\d+(\.\d+)?\b", Number),
            (r"\b[A-Za-z_]\w*(?=\s*\()", Name.Function),
            (r"[A-Za-z_]\w*", Name),
            (r"[-+*/%=<>!&|^~:]+", Operator),
            (r"[\[\](){},.;]", Punctuation),
            (r"\s+", Text),
        ]}
    return RingLexer()
