"""C# language plugin (GUI Bridge + .NET SDK).

The project folder holds the user's files (Form1.cs, Form1_designer.cs, Helpers.cs ...).
A small console project is kept in <project>/_build/csharp:
    RadApp.csproj   compiles ../../*.cs + the client (Rad.cs, RadMain.cs); also the NuGet manifest
    bin/RadApp.dll  the program ("dotnet RadApp.dll", or "--worker <Module>" for the RAD Hub)
Builds are skipped when nothing changed and use --no-restore when the packages are already restored.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..model import Form, Project
from . import _refs_dotnet_java as refs
from .base import Completion, PackageManager
from .bridgebase import CLIENTS, BridgeLanguagePlugin

CLIENT_DIR = CLIENTS / "csharp"
RADCS = CLIENT_DIR / "radcs.py"
BUILD_DIR = "_build/csharp"
CSPROJ = "RadApp.csproj"
CLIENT_SOURCES = ("Rad.cs", "RadMain.cs")

CSPROJ_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">
  <!-- RAD IDE build project. Compiles the project's *.cs files; NuGet packages are added here
       (Project > Packages, or: dotnet add _build/csharp/RadApp.csproj package <Name>). -->
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>{tfm}</TargetFramework>
    <AssemblyName>RadApp</AssemblyName>
    <RootNamespace>RadApp</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <LangVersion>latest</LangVersion>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <OutDir>bin/</OutDir>
    <UseAppHost>false</UseAppHost>
    <GenerateDocumentationFile>false</GenerateDocumentationFile>
    <SatelliteResourceLanguages>en</SatelliteResourceLanguages>
    <NoWarn>$(NoWarn);CS0168;CS0219;CS8981</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="../../*.cs" />
    <Compile Include="Rad.cs;RadMain.cs" />
  </ItemGroup>
</Project>
"""

CS_KEYWORDS = """abstract as base bool break byte case catch char checked class const continue decimal default
    delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit
    in int interface internal is lock long namespace new null object operator out override params private
    protected public readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this
    throw true try typeof uint ulong unchecked unsafe ushort using virtual void volatile while var dynamic
    async await partial record get set value nameof when yield global""".split()

RAD_HELPERS = {
    "MsgBox": "MsgBox(object text) - message box, returns 1",
    "InputBox": "InputBox(object prompt) - ask for a text",
    "Set": "Set(string obj, string prop, object value) - set a property: Set(\"lblOut\", \"Caption\", \"Hi\")",
    "Get": "Get(string obj, string prop) - read a property as text",
    "GetNumber": "GetNumber(string obj, string prop) - read a property as a number",
    "Call": "Call(string obj, string method, params object[] args) - e.g. Call(\"lstLog\", \"AddItem\", \"x\")",
    "Show": "Show(string form) - show another form",
    "Hide": "Hide(string form) - hide a form",
    "End": "End() - close the program",
    "radcall": "radcall(\"Module.function\", args...) - call a function of a project module (any language)",
    "ToInt": "ToInt(string s) - text to int (0 when not a number)",
    "ToNumber": "ToNumber(string s) - text to double",
    "ToBool": "ToBool(string s) - \"True\"/\"1\" -> true",
}
CONTROL_MEMBERS = {
    "Text": "string Text { get; set; }", "Caption": "string Caption { get; set; }",
    "Value": "string Value { get; set; }", "Enabled": "bool Enabled { get; set; }",
    "Visible": "bool Visible { get; set; }", "Left": "int Left", "Top": "int Top", "Width": "int Width",
    "Height": "int Height", "BackColor": "string BackColor", "ForeColor": "string ForeColor",
    "ListIndex": "int ListIndex { get; set; }", "ListCount": "int ListCount { get; }",
    "Interval": "int Interval", "AddItem": "AddItem(object item)", "RemoveItem": "RemoveItem(int index)",
    "Clear": "Clear()", "List": "string List(int index)", "SetFocus": "SetFocus()",
    "Move": "Move(int left, int top, int width, int height)", "ShowDialog": "string ShowDialog() - OK/Cancel",
    "Call": "string Call(string method, params object[] args)", "Show": "Show()", "Hide": "Hide()",
}
EVENT_MEMBERS = {"X": "int", "Y": "int", "Button": "int", "KeyCode": "int", "KeyChar": "string",
                 "Sender": "string - control name", "Name": "string - event name", "Args": "string - raw args"}


# ====================================================================== build helpers
def dotnet() -> str:
    p = shutil.which("dotnet")
    if p:
        return p
    for h in (r"C:\Program Files\dotnet\dotnet.exe", os.path.expanduser(r"~\.dotnet\dotnet.exe")):
        if Path(h).exists():
            return h
    return ""


_TFM: str | None = None


def target_framework() -> str:
    global _TFM
    if _TFM is None:
        _TFM = "net8.0"
        exe = dotnet()
        if exe:
            try:
                out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout
                m = re.match(r"\s*(\d+)\.", out)
                if m and int(m.group(1)) >= 6:
                    _TFM = f"net{m.group(1)}.0"
            except (OSError, subprocess.SubprocessError):
                pass
    return _TFM


def build_dir(folder: Path) -> Path:
    return Path(folder) / BUILD_DIR


def program_dll(folder: Path) -> Path:
    return build_dir(folder) / "bin" / "RadApp.dll"


def ensure_build_dir(folder: Path) -> Path:
    """Create _build/csharp with the csproj (kept: it holds the NuGet packages) and fresh client sources."""
    b = build_dir(folder)
    b.mkdir(parents=True, exist_ok=True)
    proj = b / CSPROJ
    if not proj.exists():
        proj.write_text(CSPROJ_TEMPLATE.format(tfm=target_framework()), encoding="utf-8")
    for name in CLIENT_SOURCES:
        src, dst = CLIENT_DIR / name, b / name
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copy2(src, dst)
    gi = b / ".gitignore"
    if not gi.exists():
        gi.write_text("bin/\nobj/\n.inputs\n", encoding="utf-8")
    return proj


def _inputs(folder: Path) -> list[Path]:
    b = build_dir(folder)
    return sorted(Path(folder).glob("*.cs")) + [b / n for n in CLIENT_SOURCES] + [b / CSPROJ]


def _fingerprint(folder: Path) -> str:
    """Hash of the names and contents of every build input (saving an unchanged file keeps it)."""
    h = hashlib.sha1()
    for p in _inputs(folder):
        h.update(p.name.encode("utf-8") + b"|")
        if p.exists():
            h.update(p.read_bytes())
        h.update(b"|")
    return h.hexdigest()


def up_to_date(folder: Path) -> bool:
    stamp = build_dir(folder) / ".inputs"
    return program_dll(folder).exists() and stamp.exists() and \
        stamp.read_text(encoding="utf-8").strip() == _fingerprint(folder)


def build(folder: Path, out=None, force: bool = False) -> int:
    """Build the project if needed; build messages go to *out* (a text stream). Returns the exit code."""
    out = out or sys.stdout
    folder = Path(os.path.abspath(folder))
    exe = dotnet()
    if not exe:
        print("C#: the .NET SDK was not found. Install it from https://dotnet.microsoft.com/download "
              "(winget install Microsoft.DotNet.SDK.9) and restart the IDE.", file=out, flush=True)
        return 1
    proj = ensure_build_dir(folder)
    if not force and up_to_date(folder):
        print("C#: up to date", file=out, flush=True)
        return 0
    assets = build_dir(folder) / "obj" / "project.assets.json"
    cmd = [exe, "build", str(proj), "-nologo", "-v", "q", "-clp:NoSummary"]
    if assets.exists() and assets.stat().st_mtime >= proj.stat().st_mtime:
        cmd.append("--no-restore")
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1",
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1")
    r = subprocess.run(cmd, cwd=str(folder), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    seen, lines = set(), []
    for line in (r.stdout + r.stderr).splitlines():
        line = re.sub(r"\s+\[[^\[\]]*\.csproj\]\s*$", "", line).rstrip()
        if not line or line in seen or line.startswith("Workload updates are available"):
            continue
        seen.add(line)
        lines.append(line)
    text = "\n".join(lines)
    if text:
        print(text, file=out, flush=True)
    if r.returncode == 0:
        (build_dir(folder) / ".inputs").write_text(_fingerprint(folder), encoding="utf-8")
    return r.returncode


def _split_pkg(spec: str) -> tuple[str, str]:
    m = re.match(r"^\s*([^\s@:]+)\s*(?:[@: ]\s*(\S+))?\s*$", spec or "")
    return (m.group(1), m.group(2) or "") if m else (spec.strip(), "")


def packages(folder: Path, action: str, spec: str = "") -> int:
    exe = dotnet()
    if not exe:
        print("NuGet: the .NET SDK (dotnet) was not found.", file=sys.stderr)
        return 1
    folder = Path(os.path.abspath(folder))
    proj = ensure_build_dir(folder)
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
    if action == "list":
        assets = build_dir(folder) / "obj" / "project.assets.json"
        if not assets.exists() or assets.stat().st_mtime < proj.stat().st_mtime:
            subprocess.run([exe, "restore", str(proj), "-v", "q"], cwd=str(folder), env=env,
                           capture_output=True)
        return subprocess.call([exe, "list", str(proj), "package"], cwd=str(folder), env=env)
    name, version = _split_pkg(spec)
    if not name:
        print("NuGet: no package name given", file=sys.stderr)
        return 2
    if action in ("add", "install"):
        cmd = [exe, "add", str(proj), "package", name] + (["--version", version] if version else [])
    elif action in ("remove", "uninstall"):
        cmd = [exe, "remove", str(proj), "package", name]
    else:
        print(f"NuGet: unknown action '{action}'", file=sys.stderr)
        return 2
    return subprocess.call(cmd, cwd=str(folder), env=env)


def cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, folder = argv[0], Path(argv[1])
    if cmd == "build":
        quiet = "--quiet" in argv
        return build(folder, sys.stderr if quiet else sys.stdout, force="--force" in argv)
    if cmd == "init":
        print(f"Created {ensure_build_dir(folder)}")
        return 0
    if cmd == "pkg" and len(argv) >= 3:
        return packages(folder, argv[2], argv[3] if len(argv) > 3 else "")
    print(f"unknown command: {' '.join(argv)}", file=sys.stderr)
    return 2


def _ident(name: str) -> str:
    return f"@{name}" if name in CS_KEYWORDS else name


# ====================================================================== plugin
class CSharpBridgePlugin(BridgeLanguagePlugin):
    id = "csharp-bridge"
    display_name = "C# (GUI Bridge, .NET)"
    code_ext = ".cs"
    tool_names = ["dotnet"]
    tool_hints = [r"C:\Program Files\dotnet\dotnet.exe"]
    install_hint = "Install the .NET SDK: winget install Microsoft.DotNet.SDK.9"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    keywords = CS_KEYWORDS
    builtins = list(RAD_HELPERS) + ["Console", "Math", "String", "Convert", "DateTime", "TimeSpan", "List",
                                    "Dictionary", "Environment", "File", "Path", "Directory", "Task",
                                    "RadControl", "RadEvent", "Exception"]
    handler_regex = (r"^\s*(?:(?:public|private|internal|protected|static|async)\s+)+"
                     r"(?:void|Task)\s+(\w+_\w+)\s*\(")
    package_manager = PackageManager(
        name="NuGet", tool="dotnet",
        list_cmd=[sys.executable, str(RADCS), "pkg", ".", "list"],
        search_cmd=["dotnet", "package", "search", "{query}", "--take", "30"],
        install_cmd=[sys.executable, str(RADCS), "pkg", ".", "add", "{name}@{version}"],
        uninstall_cmd=[sys.executable, str(RADCS), "pkg", ".", "remove", "{name}"],
        init_cmd=[sys.executable, str(RADCS), "init", "."],
        manifest=f"{BUILD_DIR}/{CSPROJ}",
        search_url="https://www.nuget.org/packages?q={query}")

    # ------------------------------------------------------------ code templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. A handler is a static method named <Control>_<Event>\n"
                f"// (optionally taking RadEvent e: e.X, e.Y, e.Button, e.KeyCode, e.KeyChar).\n"
                f"// Controls are fields generated in {n}_designer.cs:  lblOut.Text = \"Hi\";  lstLog.AddItem(\"x\");\n"
                f"// Helpers: MsgBox(text), InputBox(prompt), Set/Get/Call(obj, ...), Show(\"Form2\"), End(),\n"
                f"//          radcall(\"Module.function\", args...) - call a function of a project module.\n"
                f"public static partial class {n}\n"
                f"{{\n"
                f"    static void {n}_Load(RadEvent e)\n"
                f"    {{\n"
                f"        // runs when the form is shown\n"
                f"    }}\n"
                f"}}\n")

    def generate_designer(self, form: Form, user_code: str) -> str:
        n = form.name
        L = [f"// AUTO-GENERATED by RAD IDE from {n}.form - do not edit (changes will be lost).",
             "// The form is drawn by the IDE (GUI Bridge); these fields talk to its controls.",
             f"public static partial class {n}",
             "{",
             f"    /// <summary>The form itself ({n}).</summary>",
             f"    public static readonly RadControl Me = new RadControl(\"{n}\");"]
        for c in form.controls:
            if c.type == "MenuStrip" or not re.fullmatch(r"[A-Za-z_]\w*", c.name):
                continue
            L.append(f"    public static readonly RadControl {_ident(c.name)} = new RadControl(\"{n}.{c.name}\");"
                     f"  // {c.type}")
        L += ["}", ""]
        return "\n".join(L)

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, r"^\s*(?:(?:public|private|internal|protected|static|async)\s+)+"
                                     rf"(?:void|Task)\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        idx = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip() == "}"), None)
        stub = [f"    static void {name}(RadEvent e)", "    {", "        ", "    }"]
        if idx is None:     # no class found: create one
            lines += ["", f"public static partial class {form.name}", "{"] + stub + ["}"]
            return "\n".join(lines) + "\n", len(lines) - 3
        if idx > 0 and lines[idx - 1].strip() not in ("{", ""):
            stub.insert(0, "")
        lines[idx:idx] = stub
        return "\n".join(lines) + "\n", idx + len(stub) - 2

    def module_template(self, name: str) -> str:
        return (f"// Module {name}. Its public static methods can be used by every form ({name}.Add(2, 3))\n"
                f"// and by other languages of the project through the RAD Hub:\n"
                f"//     radcall(\"{name}.Add\", 2, 3)      (same syntax in C#, Python, Ring, Java, ...)\n"
                f"// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.\n"
                f"public static class {name}\n"
                f"{{\n"
                f"    public static double Add(double a, double b) => a + b;\n"
                f"}}\n")

    # ------------------------------------------------------------ References (CONTRACTS 7.2)
    def exported_functions(self, path: Path, text: str) -> list:
        """Public static methods of the class named like the file (``public static class MathLib`` in
        MathLib.cs). Typed: proxies in typed languages keep double/int/long/string/bool."""
        return refs.cs_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>.ref.cs``: ``public static class <Lib>`` whose methods forward to the RAD Hub, so the
        consumer writes ``MathLib.Add(2, 3)``. The build compiles every *.cs of the project folder."""
        return refs.cs_proxy(lib, functions)

    def example_function(self, name: str) -> str:
        """One example public method (goes inside the library class, see library_template)."""
        return ("    /// <summary>Adds two numbers.</summary>\n"
                "    public static double Add(double a, double b) => a + b;\n")

    def library_template(self, name: str) -> str:
        cls = _ident(re.sub(r"\W", "_", name))
        return (f"// Class Library {name}. Its public static methods are the library's public functions:\n"
                f"// a project that references {name} (Add Reference) calls them as native code -\n"
                f"//     {name}.Add(2, 3)   in C#, Python, Java, JavaScript ...   {name}_Add(2, 3) in Ring\n"
                f"// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.\n"
                f"public static class {cls}\n"
                f"{{\n"
                f"{self.example_function(name)}"
                f"\n"
                f"    /// <summary>Returns a greeting.</summary>\n"
                f"    public static string Greet(string name) => $\"Hello, {{name}}!\";\n"
                f"}}\n")

    # ------------------------------------------------------------ build / run
    def tool(self) -> str:
        return dotnet()

    def prepare(self, folder: Path, project: Project) -> None:
        ensure_build_dir(folder)

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{sys.executable}" "{RADCS}" build "{Path(os.path.abspath(folder))}"'

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [dotnet() or "dotnet", str(program_dll(Path(os.path.abspath(folder))))]

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(os.path.abspath(folder))
        if build(folder, sys.stderr) != 0 or not program_dll(folder).exists():
            msg = f"C# worker: building {folder.name} failed (see the build output)"
            return [sys.executable, "-c", f"import sys; sys.stderr.write({msg!r} + '\\n'); sys.exit(1)"]
        return [dotnet() or "dotnet", str(program_dll(folder)), "--worker", Path(module_file).stem]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        names = names or {}
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(\w+)\.\w*$", before)
        if m:
            obj = m.group(1)
            if obj == "Rad":
                return [Completion(k, "function", d) for k, d in RAD_HELPERS.items()]
            if obj in names or obj == "Me":
                return [Completion(k, "property" if "(" not in d else "method", d)
                        for k, d in CONTROL_MEMBERS.items()]
            if obj == "e":
                return [Completion(k, "property", d) for k, d in EVENT_MEMBERS.items()]
            if path:
                return [Completion(n, "function", d) for n, d in refs.proxy_members(Path(path).parent, obj, "cs")]
            return []
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in RAD_HELPERS.items()]
        out += [Completion(b, "class") for b in self.builtins if b not in RAD_HELPERS]
        if path:
            out += [Completion(p.name[:-7], "module", "reference (Add Reference)")
                    for p in Path(path).parent.glob("*.ref.cs")]
        out += [Completion(n, "control", t) for n, t in names.items()]
        seen = {c.name for c in out}
        for w in re.findall(r"[A-Za-z_]\w{2,}", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    def hover(self, code, line, col, path, names=None):
        """The GUI Bridge helper / control member under the mouse: csharp-ls answers nothing for them while it
        loads the project (and the editor then asks the plugin)."""
        lines = code.splitlines()
        text = lines[line] if 0 <= line < len(lines) else ""
        for m in re.finditer(r"(?:(\w+)\.)?(\w+)", text):
            if m.start(2) <= col <= m.end(2):
                obj, fn = m.group(1), m.group(2)
                if obj and (obj in (names or {}) or obj == "Me"):
                    return CONTROL_MEMBERS.get(fn, "")
                return RAD_HELPERS.get(fn, "")
        return ""

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(?:(\w+)\.)?(\w+)\s*\([^()]*$", before)
        if not m:
            return ""
        obj, fn = m.group(1), m.group(2)
        if obj and (obj in (names or {}) or obj == "Me"):
            return CONTROL_MEMBERS.get(fn, "")
        if obj and path:
            for n, d in refs.proxy_members(Path(path).parent, obj, "cs"):
                if n == fn:
                    return d
        return RAD_HELPERS.get(fn, "")


PLUGIN = CSharpBridgePlugin()
