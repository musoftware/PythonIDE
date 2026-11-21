"""C# and Java blocks of the Arabic courses (radide/tutorials/csharp, radide/tutorials/java).

Block kinds (fence info strings, see vb-basic/README.md for the shared format):

* ```` ```csharp run ```` / ```` ```java run ```` - a console program.  "جرّبه" writes it as a real project of
  the other IDEs and opens it IN PLACE: C# = an SDK-style ``Lesson.csproj`` + ``Program.cs`` (Visual Studio
  project, radide/foreign/vs_solution.py: dotnet build / run, netcoredbg); Java = an Eclipse project
  (``.project`` + ``.classpath``, radide/foreign/java_ide.py: javac / java, JDWP).
* ```` ```csharp form run ```` / ```` ```java form run ```` - the code of ``Form1`` of a GUI Bridge project
  (csharp-bridge / java-bridge): handlers ``static void btnX_Click(RadEvent e)``; the form gets the controls the
  code uses (names with the prefixes btn/txt/lbl/lst/cbo/chk/opt/tmr/...).
* ``exercise`` / ``solution`` (also with ``form``), ``text output``, ``text input``, ``// #file: Name.ext``.
* Hidden ``<!-- test: {...} -->`` before a form block: ``{"set": {"txtName.Text": "Ali"}, "events":
  ["btnHello Click"], "input": ["answer"], "expect": {"lblOut.Text": "..."}, "msgbox": ["..."]}``.  The check
  builds the bridge program and drives it through the GUI Bridge protocol with a headless host (Form1 Load
  first, then the events), so the handlers really run.

Console programs print UTF-8: C# projects get ``RadUtf8.cs`` (a module initializer that sets
``Console.OutputEncoding``), Java runs with ``-Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8``.
"""
from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
UTF8_CS = "RadUtf8.cs"
UTF8_CS_TEXT = """// RAD IDE tutorials: Console uses UTF-8, so Arabic text shows correctly in the Output window, and numbers
// are written with a "." decimal point on every Windows language (invariant culture).
// In your own console programs write:  Console.OutputEncoding = System.Text.Encoding.UTF8;
using System.Globalization;
using System.Runtime.CompilerServices;

static class RadUtf8
{
    [ModuleInitializer]
    internal static void Init()
    {
        try { Console.OutputEncoding = new System.Text.UTF8Encoding(false); } catch { }
        try { Console.InputEncoding = new System.Text.UTF8Encoding(false); } catch { }
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
    }
}
"""
CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>{tfm}</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <RootNamespace>{name}</RootNamespace>
  </PropertyGroup>

</Project>
"""
ECLIPSE_PROJECT = """<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name>{name}</name>
	<comment>RAD IDE tutorial project</comment>
	<projects>
	</projects>
	<buildSpec>
		<buildCommand>
			<name>org.eclipse.jdt.core.javabuilder</name>
			<arguments>
			</arguments>
		</buildCommand>
	</buildSpec>
	<natures>
		<nature>org.eclipse.jdt.core.javanature</nature>
	</natures>
</projectDescription>
"""
ECLIPSE_CLASSPATH = """<?xml version="1.0" encoding="UTF-8"?>
<classpath>
	<classpathentry kind="src" path="src"/>
	<classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER"/>
	<classpathentry kind="output" path="bin"/>
</classpath>
"""
PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"), ("lst", "ListBox"),
            ("cbo", "ComboBox"), ("cmb", "ComboBox"), ("chk", "CheckBox"), ("opt", "RadioButton"),
            ("rdo", "RadioButton"), ("tmr", "Timer"), ("pic", "PictureBox"), ("prg", "ProgressBar"),
            ("grp", "GroupBox"), ("num", "NumericUpDown"))
CTRL_RX = re.compile(r"\b((?:%s)[A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])" % "|".join(p for p, _t in PREFIXES))
PLUGIN_ID = {"cs": "csharp-bridge", "java": "java-bridge"}


# ===================================================================== blocks
def is_gui(block) -> bool:
    if block.form:
        return True
    return bool(re.search(r"\bRadEvent\b|\bstatic\s+void\s+\w+_(?:Click|Load)\s*\(", block.code))


def reads_stdin(block) -> bool:
    if block.lang == "cs":
        return bool(re.search(r"Console\.(?:ReadLine|Read|ReadKey)\s*\(", block.code))
    return bool(re.search(r"\bScanner\s*\(\s*System\.in|System\.in\b|readLine\s*\(", block.code))


def java_main_class(code: str) -> str:
    m = re.search(r"public\s+(?:final\s+)?(?:class|record|enum|interface)\s+(\w+)", code)
    return m.group(1) if m else "Main"


def default_file(block) -> str:
    if block.lang == "cs":
        return "Form1.cs" if is_gui(block) else "Program.cs"
    return "Form1.java" if is_gui(block) else f"{java_main_class(block.code)}.java"


# ===================================================================== projects
def tfm() -> str:
    try:
        from ..languages.csharp_bridge import target_framework
        return target_framework()
    except Exception:  # noqa: BLE001
        return "net8.0"


def make_cs_console(files: dict[str, str], dest: Path, name: str = "Lesson") -> Path:
    """An SDK-style Visual Studio console project (opened in place by the IDE)."""
    dest.mkdir(parents=True, exist_ok=True)
    proj = dest / f"{name}.csproj"
    proj.write_text(CSPROJ.format(tfm=tfm(), name=name), encoding="utf-8")
    (dest / UTF8_CS).write_text(UTF8_CS_TEXT, encoding="utf-8")
    for fname, text in files.items():
        (dest / fname).write_text(text, encoding="utf-8")
    return proj


def make_java_console(files: dict[str, str], dest: Path, name: str = "Lesson") -> Path:
    """An Eclipse Java project (src/ + bin/), opened in place by the IDE and built with javac."""
    src = dest / "src"
    src.mkdir(parents=True, exist_ok=True)
    (dest / ".project").write_text(ECLIPSE_PROJECT.format(name=name), encoding="utf-8")
    (dest / ".classpath").write_text(ECLIPSE_CLASSPATH, encoding="utf-8")
    for fname, text in files.items():
        (src / fname).write_text(text, encoding="utf-8")
    return dest / ".project"


def controls_in(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls a form's code uses (txtName.Text, btnOk_Click, Get("lblX", ...))."""
    names: list[str] = []
    for m in CTRL_RX.finditer(code):
        n = m.group(1)
        if n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = next((t for p, t in PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n))
    return out


def make_gui(lang: str, files: dict[str, str], dest: Path, name: str = "Lesson", spec: dict | None = None):
    """A csharp-bridge / java-bridge Windows Application: Form1 with the controls its code uses (one column)."""
    from ..languages import get_plugin
    from ..model import Form
    from ..workspace import create_project
    plugin_id = PLUGIN_ID[lang]
    project = create_project(dest, name, plugin_id)
    plugin = get_plugin(plugin_id)
    ext = ".cs" if lang == "cs" else ".java"
    code = files.get("Form1" + ext) or next(iter(files.values()), "")
    form = Form.load(project.form_path("Form1"))
    texts = dict((spec or {}).get("controls") or {})
    y = 12
    for typ, cname in controls_in(code):
        try:
            c = form.add(typ, 12, y)
        except KeyError:                       # a control type this IDE build does not have
            continue
        c.props["Name"] = cname
        if typ == "Label":
            c.props["Width"] = 360
            c.props["Text"] = ""
        elif typ in ("TextBox", "ComboBox"):
            c.props["Width"] = 220
            if typ == "TextBox":
                c.props["Text"] = ""
        elif typ == "Button":
            c.props["Text"] = cname[3:]
            c.props["Width"] = 130
        elif typ == "ListBox":
            c.props["Width"] = 300
            c.props["Height"] = 120
            y += 90
        elif typ in ("CheckBox", "RadioButton"):
            c.props["Text"] = cname[3:]
            c.props["Width"] = 220
        elif typ == "Timer":
            c.props["Interval"] = 1000
        if cname in texts:
            c.props["Text"] = texts[cname]
        y += 34 if typ != "Timer" else 0
    try:
        form.props["Height"] = max(int(form.props.get("Height", 300)), y + 60)
    except (TypeError, ValueError):
        pass
    form.save(project.form_path("Form1"))
    for fname, text in files.items():
        (dest / fname).write_text(text, encoding="utf-8")
        if fname != "Form1" + ext and fname.endswith(ext) and fname not in project.modules:
            project.modules.append(fname)
    (dest / plugin.designer_file("Form1")).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    project.save()
    return project


def make_project(block, files: dict[str, str], dest: Path, name: str = "Lesson"):
    target = block.check_target()
    if is_gui(block) or is_gui(target):
        return make_gui(block.lang, files, dest, name, target.spec)
    if block.lang == "cs":
        return make_cs_console(files, dest, name)
    return make_java_console(files, dest, name)


# ===================================================================== tools
def dotnet() -> str:
    try:
        from ..languages.csharp_bridge import dotnet as _d
        return _d()
    except Exception:  # noqa: BLE001
        return shutil.which("dotnet") or ""


def jdk_tool(name: str) -> str:
    try:
        from ..languages.java_bridge import _tool
        return _tool(name)
    except Exception:  # noqa: BLE001
        return shutil.which(name) or ""


DOTNET_ENV = {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1", "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
              "DOTNET_CLI_UI_LANGUAGE": "en"}
TIMEOUT_NOTE = "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟>>"


def _clean_build_output(text: str) -> str:
    seen, lines = set(), []
    for ln in text.splitlines():
        ln = re.sub(r"\s+\[[^\[\]]*\.csproj\]\s*$", "", ln).rstrip()
        if not ln or ln in seen or ln.startswith("Workload updates are available") or "dotnet workload" in ln:
            continue
        seen.add(ln)
        lines.append(ln)
    return "\n".join(lines)


def run_cs_console(files: dict[str, str], stdin: str | None, work: Path, timeout: int = 20) -> tuple[bool, str]:
    """dotnet build + run the console program; (built, output or build errors)."""
    exe = dotnet()
    if not exe:
        return False, ".NET SDK غير موجود (ثبّته: winget install Microsoft.DotNet.SDK.9)"
    work = Path(work).resolve()
    _reset(work, keep=("obj",))
    make_cs_console(files, work, "Lesson")
    env = dict(os.environ, **DOTNET_ENV)
    r = subprocess.run([exe, "build", "Lesson.csproj", "-nologo", "-v", "q", "-clp:NoSummary", "-o", "out"],
                       cwd=work, env=env, capture_output=True, creationflags=NO_WINDOW)
    if r.returncode:
        return False, _clean_build_output((r.stdout + r.stderr).decode("utf-8", "replace"))
    try:
        r = subprocess.run([exe, str(work / "out" / "Lesson.dll")], input=(stdin or "").encode("utf-8"), cwd=work,
                           env=env, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return True, TIMEOUT_NOTE
    return True, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


JAVA_FLAGS = ["-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8",
              "-Dsun.stdout.encoding=UTF-8", "-Dsun.stderr.encoding=UTF-8", "-Duser.language=en",
              "-XX:TieredStopAtLevel=1", "-XX:+UseSerialGC"]


def run_java_console(files: dict[str, str], stdin: str | None, work: Path, timeout: int = 20) -> tuple[bool, str]:
    """javac + java the console program (main class = the class with main of the first file)."""
    javac, java = jdk_tool("javac"), jdk_tool("java")
    if not javac or not java:
        return False, "لا يوجد JDK (ثبّته: winget install EclipseAdoptium.Temurin.17.JDK)"
    work = Path(work).resolve()
    _reset(work)
    make_java_console(files, work, "Lesson")
    src, out = work / "src", work / "bin"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, JAVA_TOOL_OPTIONS="-Duser.language=en")
    r = subprocess.run([javac, "-encoding", "UTF-8", "-nowarn", "-d", str(out), *files], cwd=src, env=env,
                       capture_output=True, creationflags=NO_WINDOW)
    if r.returncode:
        return False, _drop_picked((r.stdout + r.stderr).decode("utf-8", "replace"))
    main = next((Path(f).stem for f, t in files.items() if re.search(r"static\s+void\s+main\s*\(", t)),
                Path(next(iter(files))).stem)
    pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", files.get(main + ".java", ""), re.M)
    cls = f"{pkg.group(1)}.{main}" if pkg else main
    try:
        r = subprocess.run([java, *JAVA_FLAGS, "-cp", str(out), cls], input=(stdin or "").encode("utf-8"), cwd=work,
                           env=env, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return True, TIMEOUT_NOTE
    return True, _drop_picked(r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))


def _drop_picked(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("Picked up JAVA_TOOL_OPTIONS"))


def _reset(work: Path, keep: tuple[str, ...] = ()) -> None:
    work.mkdir(parents=True, exist_ok=True)
    for p in work.iterdir():
        if p.name in keep:
            continue
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except OSError:
                pass


# ===================================================================== GUI Bridge (headless host)
def build_gui(lang: str, folder: Path) -> tuple[bool, str, list[str]]:
    """Build a bridge project with the IDE's own build; (ok, build output, program argv)."""
    import io
    buf = io.StringIO()
    if lang == "cs":
        from ..languages import csharp_bridge as CB
        rc = CB.build(folder, buf, force=True)
        return rc == 0, _clean_build_output(buf.getvalue()), [CB.dotnet() or "dotnet", str(CB.program_dll(folder))]
    from ..languages import java_bridge as JB
    rc = JB.build(folder, buf, force=True)
    return rc == 0, _drop_picked(buf.getvalue()), JB.java_command(folder)


class FakeHost:
    """Drives a GUI Bridge program like radide/runtimes/bridge.py does, without drawing anything."""

    def __init__(self, argv: list[str], cwd: Path, spec: dict, timeout: float = 20):
        self.spec = spec
        self.timeout = timeout
        self.props: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.output: list[str] = []
        self.msgbox: list[str] = []
        self.inputs = list(spec.get("input") or [])
        self.ended = False
        for k, v in (spec.get("set") or {}).items():
            self.props[self._key(k)] = str(v)
        for k, v in (spec.get("items") or {}).items():
            self.lists[k.lower()] = [str(x) for x in v]
        env = dict(os.environ, **DOTNET_ENV)
        self.proc = subprocess.Popen(argv, cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, env=env, creationflags=NO_WINDOW)
        self.q: queue.Queue = queue.Queue()
        self.err: list[str] = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()

    @staticmethod
    def _key(path: str) -> str:
        parts = path.split(".")
        if len(parts) >= 3:                     # Form1.lblOut.Text
            parts = parts[1:]
        return ".".join(parts).lower()

    @staticmethod
    def _obj(path: str) -> str:
        parts = path.split(".")
        return (parts[-1] if len(parts) > 1 else parts[0]).lower()

    def _read(self):
        for raw in self.proc.stdout:
            self.q.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        self.q.put(None)

    def _read_err(self):
        for raw in self.proc.stderr:
            ln = raw.decode("utf-8", "replace").rstrip("\r\n")
            if not ln.startswith("Picked up JAVA_TOOL_OPTIONS"):
                self.err.append(ln)

    def send(self, line: str):
        try:
            self.proc.stdin.write((line + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except OSError:
            self.ended = True

    def get(self, obj: str, prop: str) -> str:
        o, p = self._obj(obj), prop.lower()
        if o in self.lists:
            items = self.lists[o]
            if p == "listcount":
                return str(len(items))
            if p == "listindex":
                return self.props.get(f"{o}.listindex", "-1")
            if p == "text" and f"{o}.text" not in self.props:
                i = int(self.props.get(f"{o}.listindex", "-1") or -1)
                return items[i] if 0 <= i < len(items) else ""
        if p in ("enabled", "visible") and f"{o}.{p}" not in self.props:
            return "True"
        if p == "listcount":
            return "0"
        if p == "listindex" and f"{o}.listindex" not in self.props:
            return "-1"
        return self.props.get(f"{o}.{p}", "")

    def call(self, obj: str, method: str, args: list[str]) -> str:
        o, m = self._obj(obj), method.lower()
        items = self.lists.setdefault(o, [])
        if m == "additem":
            items.append(args[0] if args else "")
        elif m == "clear":
            items.clear()
            self.props.pop(f"{o}.listindex", None)
        elif m == "removeitem" and args:
            i = int(float(args[0]))
            if 0 <= i < len(items):
                items.pop(i)
        elif m == "list" and args:
            i = int(float(args[0]))
            return items[i] if 0 <= i < len(items) else ""
        return ""

    def event(self, obj: str, ev: str, args: str = "") -> bool:
        """Send one EVENT and serve the program's commands until DONE; False when it ended / timed out."""
        if self.ended:
            return False
        self.send(f"EVENT {obj} {ev} {args}".rstrip())
        while True:
            try:
                line = self.q.get(timeout=self.timeout)
            except queue.Empty:
                self.output.append("<<انتهت المهلة: البرنامج لم ينهِ الحدث>>")
                self.ended = True
                return False
            if line is None:
                self.ended = True
                return False
            cmd, _, rest = line.partition(" ")
            up = cmd.upper()
            if up == "DONE":
                return True
            if up == "END":
                self.send("QUIT")
                self.ended = True
                return False
            if up == "SET":
                o, p, v = (rest.split(" ", 2) + ["", ""])[:3]
                self.props[f"{self._obj(o)}.{p.lower()}"] = v
            elif up == "GET":
                o, p = (rest.split(" ", 1) + [""])[:2]
                self.send(self.get(o, p.strip()))
            elif up == "CALL":
                o, m, a = (rest.split(" ", 2) + ["", ""])[:3]
                self.send(self.call(o, m, a.split("\t") if a else []))
            elif up == "MSGBOX":
                self.msgbox.append(rest)
                self.send("1")
            elif up == "INPUT":
                self.send(self.inputs.pop(0) if self.inputs else "")
            elif up in ("SHOW", "HIDE"):
                pass
            else:
                self.output.append(line)

    def run(self) -> None:
        if not self.spec.get("noload"):
            self.event("Form1", "Load")
        for e in self.spec.get("events") or []:
            parts = str(e).split(" ", 2)
            if len(parts) == 1:
                parts.append("Click")
            if not self.event(*parts):
                break
        self.close()

    def close(self):
        if self.proc.poll() is None:
            self.send("QUIT")
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    def value(self, path: str) -> str:
        k = self._key(path)
        o, _, p = k.partition(".")
        if p in ("listcount",) or (o in self.lists and p in ("items",)):
            return str(len(self.lists.get(o, []))) if p == "listcount" else "|".join(self.lists.get(o, []))
        return self.get(o, p)


def run_gui(lang: str, folder: Path, spec: dict) -> dict:
    ok, out, argv = build_gui(lang, folder)
    if not ok:
        return {"built": False, "build": out}
    host = FakeHost(argv, folder, spec)
    host.run()
    values = {k: host.value(k) for k in (spec.get("expect") or {})}
    return {"built": True, "output": "\n".join(host.output), "msgbox": host.msgbox, "values": values,
            "stderr": "\n".join(host.err), "build": out}


# ===================================================================== check ("تحقق")
def _project_files(folder: Path, lang: str) -> dict[str, str]:
    ext = ".cs" if lang == "cs" else ".java"
    out = {}
    roots = [Path(folder), Path(folder) / "src"]
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.iterdir()):
            if p.is_file() and p.suffix.lower() == ext and not p.name.endswith("_designer" + ext) \
                    and p.name != UTF8_CS and not p.name.startswith("_"):
                out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    """Run the learner's version of *block* and compare with the expected output / the hidden test."""
    target = block.check_target()
    expected = target.expected
    lang = block.lang
    files = _project_files(folder, lang) if folder else block_files(block, code)
    if is_gui(block) or is_gui(target):
        spec = dict(target.spec or {})
        work = Path(work).resolve()
        _reset(work)
        make_gui(lang, files, work / "proj", "Check", spec)
        r = run_gui(lang, work / "proj", spec)
        if not r["built"]:
            return CheckResult(False, r["build"], None, ["فشل البناء (أخطاء الترجمة بالأسفل)"])
        problems = []
        if r["stderr"].strip() and "Error in" in r["stderr"]:
            problems.append("خطأ أثناء تشغيل معالج حدث: " + r["stderr"].strip().splitlines()[0])
        for k, v in (spec.get("expect") or {}).items():
            got = r["values"].get(k)
            if str(v).startswith("re:") and got is not None and re.fullmatch(str(v)[3:], got):
                continue
            if got != str(v):
                problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
        if "msgbox" in spec and r["msgbox"] != spec["msgbox"]:
            problems.append("رسائل MsgBox: المتوقع " + " | ".join(spec["msgbox"]) + " ، الناتج " +
                            " | ".join(r["msgbox"]))
        if expected is not None and norm(r["output"]) != norm(expected):
            problems.append("المخرجات لا تطابق المطلوب")
        out = r["output"]
        if r["msgbox"]:
            out += ("\n" if out else "") + "\n".join(f"[MsgBox] {m}" for m in r["msgbox"])
        if r["stderr"].strip():
            out += ("\n" if out else "") + r["stderr"].strip()
        if not spec.get("expect") and "msgbox" not in spec and expected is None and not problems:
            return CheckResult(True, out, None, [], "نجح البناء ويعمل النموذج بلا أخطاء. اضغط «جرّبه» وجرّب "
                                                    "الأزرار بنفسك.")
        return CheckResult(not problems, out, expected, problems)
    runner = run_cs_console if lang == "cs" else run_java_console
    built, out = runner(files, target.stdin, work)
    if not built:
        return CheckResult(False, out, expected, ["فشل البناء (أخطاء الترجمة بالأسفل)"])
    if expected is None and target is not block and target.code.strip():
        _b, expected = runner(block_files(target), target.stdin, work.parent / (work.name + "-sol"))
    ok = expected is not None and norm(out) == norm(expected)
    if expected is None:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    return CheckResult(ok, out, expected, [] if ok else ["المخرجات لا تطابق المطلوب"])


__all__ = ["FakeHost", "check", "controls_in", "default_file", "is_gui", "make_cs_console", "make_gui",
           "make_java_console", "make_project", "reads_stdin", "run_cs_console", "run_gui", "run_java_console"]
