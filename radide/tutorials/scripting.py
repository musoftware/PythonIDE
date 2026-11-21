"""Tutorial blocks of the scripting GUI-Bridge languages: Ruby, Lua, Perl, PowerShell and Dart.

Fence info strings (the same roles as vb-basic/README.md): ``ruby run`` / ``lua run`` / ``perl run`` /
``powershell run`` / ``dart run`` = a console script (``main.<ext>``, read from ``text input`` as stdin);
``<lang> form run`` = the event handlers of ``Form1`` (``Form1.<ext>``): the form gets the controls the code
names (``btnX``, ``txtX``, ``lblX``, ``lstX`` ... like the C++ GUI blocks), and ``<lang> exercise`` /
``<lang> solution`` (also with ``form``).  ``#file: name.ext`` lines (``-- #file:`` in Lua, ``// #file:`` in
Dart) split a block into several files.

Form blocks are checked headless with a small GUI Bridge host (``run_form``): the program gets the events
of the hidden test comment and answers GET/CALL/INPUT/MSGBOX from it, e.g.
``<!-- test: {"set": {"txtName.Text": "Sara"}, "events": ["btnHello.Click"],
"expect": {"lblOut.Text": "Hello, Sara"}, "msgbox": ["..."], "inputs": ["..."]} -->``.
"""
from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# language -> (plugin id, extension, display name, Pygments lexer)
LANGS = {
    "ruby": ("ruby-bridge", ".rb", "Ruby", "ruby"),
    "lua": ("lua-bridge", ".lua", "Lua", "lua"),
    "perl": ("perl-bridge", ".pl", "Perl", "perl"),
    "powershell": ("powershell-bridge", ".ps1", "PowerShell", "powershell"),
    "dart": ("dart-bridge", ".dart", "Dart", "dart"),
}
ALIASES = {"ruby": "ruby", "rb": "ruby", "lua": "lua", "perl": "perl", "pl": "perl", "powershell": "powershell",
           "ps1": "powershell", "pwsh": "powershell", "dart": "dart"}
FILE_MARK = re.compile(r"^\s*(?:#|--|//)\s*#?file:\s*(\S+)\s*$")
STDIN_RX = {
    "ruby": r"\bgets\b|\bSTDIN\b|\$stdin",
    "lua": r"\bio\.read\b|io\.stdin|io\.lines\s*\(\s*\)",
    "perl": r"<STDIN>|<>",
    "powershell": r"\[Console\]::(ReadLine|In)\b",
    "dart": r"\bstdin\.",
}


def is_lang(lang: str) -> bool:
    return lang in LANGS


def plugin(lang: str):
    from ..languages import get_plugin
    return get_plugin(LANGS[lang][0])


def ext(lang: str) -> str:
    return LANGS[lang][1]


def default_file(lang: str, form: bool) -> str:
    return ("Form1" if form else "main") + ext(lang)


def split_files(code: str, default: str) -> dict[str, str]:
    files: dict[str, str] = {}
    name, cur = default, []
    for ln in code.splitlines():
        m = FILE_MARK.match(ln)
        if m and "." in m.group(1):
            if any(x.strip() for x in cur):
                files[name] = "\n".join(cur) + "\n"
            name, cur = m.group(1), []
            continue
        cur.append(ln)
    if any(x.strip() for x in cur):
        files[name] = "\n".join(cur) + "\n"
    return files


def reads_stdin(lang: str, code: str) -> bool:
    return bool(re.search(STDIN_RX.get(lang, r"$^"), code))


# ===================================================================== projects
CONTROL_PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"),
                    ("lst", "ListBox"), ("cbo", "ComboBox"), ("chk", "CheckBox"), ("opt", "RadioButton"),
                    ("tmr", "Timer"), ("prg", "ProgressBar"), ("pic", "PictureBox"))


def form_controls(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls a form's code names: btnGo, txtName, lblOut, lstLog ..."""
    out, seen = [], set()
    for m in re.finditer(r"\b((btn|cmd|txt|lbl|lst|cbo|chk|opt|tmr|prg|pic)[A-Z]\w*)", code):
        name = m.group(1)
        name = re.sub(r"_(Click|Load|Tick|TextChanged|Change|KeyPress|DblClick|SelectedIndexChanged|CheckedChanged)$",
                      "", name)
        if name in seen:
            continue
        seen.add(name)
        out.append((dict(CONTROL_PREFIXES)[m.group(2)], name))
    return out


def make_project(lang: str, files: dict[str, str], dest: Path, name: str, form: bool, spec: dict | None = None):
    """A <lang>-bridge project: a console script (``main.<ext>`` as the only module, no forms: the plugin runs
    it as a plain console program) or Form1 with the controls its code uses."""
    from ..model import Form, Project
    pid = LANGS[lang][0]
    if not form:
        project = Project(dest, name, pid)
        for fname, text in files.items():
            p = dest / fname
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            if fname.lower().endswith(ext(lang)) and fname not in project.modules:
                project.modules.append(fname)
        main = default_file(lang, False)
        if main in project.modules:                       # the script that runs first
            project.modules.remove(main)
            project.modules.insert(0, main)
        project.save()
        return project
    from ..workspace import create_project
    project = create_project(dest, name, pid)
    fname = default_file(lang, True)
    code = files.get(fname) or next(iter(files.values()), "")
    captions = (spec or {}).get("captions", {})
    form_model = Form.load(project.form_path("Form1"))
    y = 12
    for typ, cname in form_controls(code):
        try:
            c = form_model.add(typ, 12, y)
        except KeyError:
            continue
        c.props["Name"] = cname
        if typ == "Label":
            c.props["Width"], c.props["Text"] = 380, captions.get(cname, "")
        elif typ in ("TextBox", "ComboBox"):
            c.props["Width"] = 220
            if typ == "TextBox":
                c.props["Text"] = captions.get(cname, "")
        elif typ == "Button":
            c.props["Text"], c.props["Width"] = captions.get(cname, cname[3:]), 140
        elif typ == "ListBox":
            c.props["Width"], c.props["Height"] = 300, 120
            y += 90
        elif typ in ("CheckBox", "RadioButton"):
            c.props["Text"], c.props["Width"] = captions.get(cname, cname[3:]), 220
        y += 36
    try:
        form_model.props["Height"] = max(int(form_model.props.get("Height", 300)), y + 60)
        form_model.props["Width"] = max(int(form_model.props.get("Width", 400)), 440)
    except (TypeError, ValueError):
        pass
    form_model.save(project.form_path("Form1"))
    for f, text in files.items():
        p = dest / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        if f != fname and f.lower().endswith(ext(lang)) and f not in project.modules:
            project.modules.append(f)
    pl = plugin(lang)                     # the designer file the IDE writes on save (PowerShell: control objects)
    (dest / pl.designer_file("Form1")).write_text(pl.generate_designer(form_model, code), encoding="utf-8")
    project.save()
    return project


def _env(tool: str) -> dict:
    env = dict(os.environ)
    if tool and Path(tool).is_absolute():
        env["PATH"] = str(Path(tool).parent) + os.pathsep + env.get("PATH", "")
    return env


def program(lang: str, folder: Path):
    """(argv, env) of the project in *folder* exactly as the IDE starts it (plugin.prepare + run_command)."""
    from ..model import Project
    pl = plugin(lang)
    project = Project.load(folder)
    pl.prepare(folder, project)
    tool = pl.tool()
    if not tool:
        raise RuntimeError(f"{pl.display_name}: {pl.install_hint}")
    env = _env(tool)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return pl.run_command(folder, project), env


# ===================================================================== running
def run_console(lang: str, files: dict[str, str] | None, stdin: str | None, work: Path,
                timeout: int = 60) -> tuple[bool, str]:
    """Run a console block (files=None: the project already in *work*); (finished, stdout + stderr)."""
    if files is not None:
        _clean(work)
        make_project(lang, files, work, "Lesson", False)
    try:
        argv, env = program(lang, work)
    except RuntimeError as e:
        return False, str(e)
    try:
        r = subprocess.run(argv, input=(stdin or "").encode("utf-8"), cwd=work, env=env, capture_output=True,
                           timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return False, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"
    return True, (r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))


class _Host:
    """A headless GUI Bridge host (CONTRACTS 1): properties live in a dict, lists in lists."""

    ALIAS = {"caption": "text"}

    def __init__(self, spec: dict):
        self.props: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        for k, v in (spec.get("set") or {}).items():
            self._put(k, v)
        for k, v in (spec.get("lists") or {}).items():
            self.lists[k.lower()] = [str(x) for x in v]
        self.inputs = [str(x) for x in spec.get("inputs") or []]
        self.msgbox: list[str] = []
        self.output: list[str] = []

    @staticmethod
    def _obj(obj: str) -> str:
        parts = obj.split(".")
        return parts[-1].lower()

    def _key(self, obj: str, prop: str) -> str:
        prop = prop.lower()
        return f"{self._obj(obj)}.{self.ALIAS.get(prop, prop)}"

    def _put(self, key: str, value) -> None:
        obj, _, prop = key.rpartition(".")
        self.props[self._key(obj, prop)] = str(value)

    def get(self, obj: str, prop: str) -> str:
        o, p = self._obj(obj), prop.lower()
        if p == "listcount":
            return str(len(self.lists.get(o, [])))
        return self.props.get(self._key(obj, prop), "")

    def call(self, obj: str, method: str, args: list[str]) -> str:
        o, m = self._obj(obj), method.lower()
        items = self.lists.setdefault(o, [])
        if m == "additem":
            items.append(args[0] if args else "")
        elif m == "clear":
            items.clear()
        elif m == "removeitem" and args:
            try:
                items.pop(int(float(args[0])))
            except (ValueError, IndexError):
                pass
        elif m == "list" and args:
            try:
                return items[int(float(args[0]))]
            except (ValueError, IndexError):
                return ""
        return ""

    def values(self) -> dict[str, str]:
        out = dict(self.props)
        for o, items in self.lists.items():
            out[f"{o}.items"] = "|".join(items)
            out[f"{o}.listcount"] = str(len(items))
        return out


def run_form(lang: str, files: dict[str, str] | None, spec: dict | None, work: Path, timeout: int = 60) -> dict:
    """Run a form block headless: Form1_Load, then the events of *spec*; returns {output, msgbox, values,
    fatal}.  files=None: the project already in *work*."""
    spec = dict(spec or {})
    if files is not None:
        _clean(work)
        make_project(lang, files, work, "Lesson", True, spec)
    try:
        argv, env = program(lang, work)
    except RuntimeError as e:
        return {"fatal": str(e), "output": ""}
    host = _Host(spec)
    try:
        proc = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    except OSError as e:
        return {"fatal": str(e), "output": ""}
    lines: queue.Queue = queue.Queue()
    err: list[str] = []

    def reader():
        for raw in proc.stdout:
            lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        lines.put(None)

    def ereader():
        for raw in proc.stderr:
            err.append(raw.decode("utf-8", "replace").rstrip("\r\n"))
    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=ereader, daemon=True).start()

    def send(text: str) -> None:
        try:
            proc.stdin.write((text + "\n").encode("utf-8"))
            proc.stdin.flush()
        except OSError:
            pass

    fatal = None
    ended = False

    def event(obj: str, ev: str) -> bool:
        nonlocal fatal, ended
        send(f"EVENT {obj} {ev}")
        while True:
            try:
                line = lines.get(timeout=timeout)
            except queue.Empty:
                fatal = f"the program did not answer {obj}_{ev} within {timeout} s"
                return False
            if line is None:
                ended = True
                return False
            cmd, _, rest = line.partition(" ")
            up = cmd.upper()
            if up == "DONE":
                return True
            if up == "END":
                ended = True
                return False
            if up == "SET":
                o, p, v = (rest.split(" ", 2) + ["", ""])[:3]
                host.props[host._key(o, p)] = v
            elif up == "GET":
                o, p = (rest.split(" ", 1) + [""])[:2]
                send(host.get(o, p.strip()))
            elif up == "CALL":
                o, m, a = (rest.split(" ", 2) + ["", ""])[:3]
                send(host.call(o, m, a.split("\t") if a else []))
            elif up == "MSGBOX":
                host.msgbox.append(rest)
                send("1")
            elif up == "INPUT":
                send(host.inputs.pop(0) if host.inputs else "")
            elif up in ("SHOW", "HIDE"):
                pass
            else:
                host.output.append(line)

    try:
        if event("Form1", "Load"):
            for e in spec.get("events") or []:
                if isinstance(e, dict):                 # {"set": {...}} between events
                    for k, v in e.get("set", {}).items():
                        host._put(k, v)
                    continue
                obj, _, ev = str(e).partition(".")
                if not event(obj, ev or "Click"):
                    break
        if not ended:
            send("QUIT")
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        if proc.poll() is None:
            proc.kill()
    # the reader thread may still be draining
    while True:
        try:
            line = lines.get(timeout=2)
        except queue.Empty:
            break
        if line is None:
            break
        if line.split(" ", 1)[0].upper() not in ("DONE", "END", "SET", "GET", "CALL", "MSGBOX", "INPUT"):
            host.output.append(line)
    errors = [ln for ln in err if ln.strip()]
    return {"output": "\n".join(host.output), "msgbox": host.msgbox, "values": host.values(), "fatal": fatal,
            "stderr": "\n".join(errors)}


def _clean(dest: Path) -> None:
    from . import _clean as clean
    clean(dest)


def _copy_project(folder: Path, work: Path) -> None:
    import shutil
    _clean(work)
    for p in Path(folder).iterdir():
        if p.name.startswith(("_rad", "_build", ".dart_tool")) or p.name in ("rad.rb", "radworker.rb", "rad.lua",
                                                                              "RadGUI.pm", "radgui.dart"):
            continue
        if p.is_dir():
            shutil.copytree(p, work / p.name, dirs_exist_ok=True)
        else:
            shutil.copyfile(p, work / p.name)


def check(block, code: str | None, folder: Path | None, work: Path):
    """The "تحقق" button for a Ruby / Lua / Perl / PowerShell / Dart block (see radide.tutorials.check)."""
    from . import CheckResult, block_files, norm
    target = block.check_target()
    lang = block.lang
    form = block.form or target.form
    if folder:
        _copy_project(folder, work)
        files = None
    else:
        files = block_files(block, code)
    expected = target.expected
    sol_work = work.parent / (work.name + "-sol")
    if not form:
        ok, out = run_console(lang, files, target.stdin, work)
        if not ok:
            return CheckResult(False, out, expected, ["لم ينتهِ البرنامج"])
        if expected is None and target is not block and target.code.strip():
            _ok, expected = run_console(lang, block_files(target), target.stdin, sol_work)
        if expected is None:
            return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
        good = norm(out) == norm(expected)
        return CheckResult(good, out, expected, [] if good else ["المخرجات لا تطابق المطلوب"])
    spec = target.spec or {}
    r = run_form(lang, files, spec, work)
    problems = []
    if r.get("fatal"):
        problems.append("خطأ: " + str(r["fatal"]))
    if re.search(r"error|exception|خطأ", r.get("stderr", ""), re.I):
        problems.append("خطأ أثناء التشغيل: " + r["stderr"][-600:])
    if expected is None and target is not block and not spec.get("expect") and "msgbox" not in spec:
        expected = run_form(lang, block_files(target), spec, sol_work).get("output")
    if expected is not None and norm(r.get("output", "")) != norm(expected):
        problems.append("المخرجات لا تطابق المطلوب")
    if "msgbox" in spec and r.get("msgbox") != spec["msgbox"]:
        problems.append("رسائل MsgBox: المتوقع " + " | ".join(spec["msgbox"]) + " ، الناتج " +
                        " | ".join(r.get("msgbox") or []))
    values = r.get("values") or {}
    for k, v in (spec.get("expect") or {}).items():
        obj, _, prop = k.rpartition(".")
        key = f"{obj.split('.')[-1].lower()}.{_Host.ALIAS.get(prop.lower(), prop.lower())}"
        got = values.get(key)
        if str(v).startswith("re:") and got is not None and re.fullmatch(str(v)[3:], got):
            continue
        if got != str(v):
            problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
    out = r.get("output", "")
    if r.get("msgbox"):
        out += ("\n" if out else "") + "\n".join(f"[MsgBox] {m}" for m in r["msgbox"])
    if expected is None and not spec.get("expect") and "msgbox" not in spec and not problems:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء. اضغط «جرّبه» وجرّب الأزرار بنفسك.")
    return CheckResult(not problems, out, expected, problems)


__all__ = ["ALIASES", "LANGS", "check", "default_file", "form_controls", "is_lang", "make_project", "program", "reads_stdin",
           "run_console", "run_form", "split_files"]
