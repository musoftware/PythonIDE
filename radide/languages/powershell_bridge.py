"""PowerShell language plugin (GUI Bridge; Windows PowerShell 5.1 or PowerShell 7 "pwsh").

Project folder: Form1.ps1 (handlers), Form1_designer.ps1 (generated control objects), modules (*.ps1).
<project>/_build/powershell holds the client (Rad.ps1) and the generated entry program RadMain.ps1, which
syntax-checks and dot-sources the project files, then dispatches bridge events to functions by name.
Packages: PowerShell Gallery modules, installed for the current user.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from ..model import Form, Project
from . import _refs_dotnet_java as refs
from .base import Completion, PackageManager
from .bridgebase import CLIENTS, BridgeLanguagePlugin

CLIENT_DIR = CLIENTS / "powershell"
BUILD_DIR = "_build/powershell"
WINPS = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

PS_KEYWORDS = """begin break catch class continue data do dynamicparam else elseif end enum exit filter finally
    for foreach function if in param process return switch throw trap try until using while
    -eq -ne -gt -ge -lt -le -like -notlike -match -notmatch -replace -contains -notcontains -in -notin
    -and -or -not -xor -is -isnot -as -split -join -f $true $false $null $_ $args $this $PSScriptRoot""".split()

RAD_HELPERS = {
    "MsgBox": "MsgBox <text> - message box, returns 1",
    "InputBox": "InputBox <prompt> - ask for a text",
    "RadSet": "RadSet <obj> <prop> <value> - e.g. RadSet lblOut Caption \"Hi\"",
    "RadGet": "RadGet <obj> <prop> - read a property as text",
    "RadInvoke": "RadInvoke <obj> <method> [args...] - e.g. RadInvoke lstLog AddItem \"x\"",
    "RadShow": "RadShow <form> - show another form", "RadHide": "RadHide <form> - hide a form",
    "RadEnd": "RadEnd - close the program",
    "radcall": "radcall \"Module.function\" arg1 arg2 - call a function of a project module (any language)",
    "RadToNumber": "RadToNumber <text> - text to a number", "RadToBool": "RadToBool <text> - \"True\"/\"1\" -> $true",
}
CMDLETS = """Write-Host Write-Output Write-Error Write-Warning Get-Date Get-Content Set-Content Add-Content Get-ChildItem
    Get-Item Test-Path Join-Path Split-Path New-Object Select-Object Where-Object ForEach-Object Sort-Object
    Measure-Object Group-Object Format-Table Out-String ConvertTo-Json ConvertFrom-Json Invoke-RestMethod
    Invoke-WebRequest Start-Process Get-Process Start-Sleep Import-Module Get-Random""".split()
CONTROL_MEMBERS = {
    "Text": "Text (get/set)", "Caption": "Caption (get/set)", "Value": "Value (get/set)",
    "Enabled": "Enabled [bool]", "Visible": "Visible [bool]", "Left": "Left [int]", "Top": "Top [int]",
    "Width": "Width [int]", "Height": "Height [int]", "BackColor": "BackColor", "ForeColor": "ForeColor",
    "ListIndex": "ListIndex [int]", "ListCount": "ListCount [int] (read only)", "Interval": "Interval [int]",
    "AddItem": "AddItem(item)", "RemoveItem": "RemoveItem(index)", "Clear": "Clear()", "List": "List(index)",
    "SetFocus": "SetFocus()", "Move": "Move(left, top, width, height)", "ShowDialog": "ShowDialog() - OK/Cancel",
    "Get": "Get(prop)", "Set": "Set(prop, value)", "Call": "Call(method, args...)", "Show": "Show()",
    "Hide": "Hide()",
}
EVENT_MEMBERS = {"X": "int", "Y": "int", "Button": "int", "KeyCode": "int", "KeyChar": "string",
                 "Sender": "control name", "Name": "event name", "Args": "raw args"}


def powershell() -> str:
    for n in ("pwsh", "powershell"):
        p = shutil.which(n)
        if p:
            return p
    return str(WINPS) if WINPS.exists() else ""


def ps_command(script: Path, *args: str) -> list[str]:
    return [powershell() or "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), *args]


def _quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def project_files(folder: Path) -> list[str]:
    """Files RadMain dot-sources: modules, then each form's designer and code."""
    folder = Path(folder)
    try:
        project = Project.load(folder)
        forms, modules = project.forms, [m for m in project.modules if m.lower().endswith(".ps1")]
    except (OSError, ValueError, KeyError):
        files = sorted(p.name for p in folder.glob("*.ps1") if not p.name.lower().endswith(".ref.ps1"))
        forms = [f[:-4] for f in files if f"{f[:-4]}.form" in {p.name for p in folder.glob("*.form")}]
        modules = [f for f in files if f[:-4] not in forms and not f.endswith("_designer.ps1")]
    # reference proxies (<Lib>.ref.ps1, Add Reference) first: modules and forms may use them
    out = [p.name for p in sorted(folder.glob("*.ref.ps1"))]
    out += [m for m in modules if m not in out]
    for f in forms:
        out += [f"{f}_designer.ps1", f"{f}.ps1"]
    return out


def ensure_build_dir(folder: Path) -> Path:
    b = Path(folder) / BUILD_DIR
    b.mkdir(parents=True, exist_ok=True)
    src, dst = CLIENT_DIR / "Rad.ps1", b / "Rad.ps1"
    if not dst.exists() or dst.read_bytes() != src.read_bytes():
        shutil.copy2(src, dst)
    main = (CLIENT_DIR / "RadMain.ps1").read_text(encoding="utf-8").replace(
        "<#FILES#>", ", ".join(_quote(f) for f in project_files(folder)))
    target = b / "RadMain.ps1"
    # UTF-8 with BOM: Windows PowerShell 5.1 reads BOM-less scripts in the ANSI code page
    data = "\ufeff" + main
    if not target.exists() or target.read_text(encoding="utf-8") != data:
        target.write_text(data, encoding="utf-8")
    return target


class PowerShellBridgePlugin(BridgeLanguagePlugin):
    id = "powershell-bridge"
    display_name = "PowerShell (GUI Bridge)"
    code_ext = ".ps1"
    tool_names = ["pwsh", "powershell"]
    tool_hints = [str(WINPS)]
    install_hint = "PowerShell is part of Windows; PowerShell 7: winget install Microsoft.PowerShell"
    case_sensitive = False
    line_comments = ["#"]
    block_comment = ("<#", "#>")
    string_quotes = ['"', "'"]
    keywords = PS_KEYWORDS
    builtins = list(RAD_HELPERS) + CMDLETS
    handler_regex = r"^\s*function\s+(?:global:|script:)?(\w+_\w+)\b"
    package_manager = PackageManager(
        name="PowerShell Gallery", tool="powershell",
        list_cmd=ps_command(CLIENT_DIR / "radpkg.ps1", "list"),
        search_cmd=ps_command(CLIENT_DIR / "radpkg.ps1", "search", "{query}"),
        install_cmd=ps_command(CLIENT_DIR / "radpkg.ps1", "install", "{name}@{version}"),
        uninstall_cmd=ps_command(CLIENT_DIR / "radpkg.ps1", "uninstall", "{name}"),
        init_cmd=None, manifest="",
        search_url="https://www.powershellgallery.com/packages?q={query}")

    def tool(self) -> str:
        return powershell()

    # ------------------------------------------------------------ code templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"# Event handlers for {n}. A handler is a function named <Control>_<Event>;\n"
                f"# $e has X, Y, Button, KeyCode, KeyChar. Use $script:name for variables kept between events.\n"
                f"# Controls are objects made in {n}_designer.ps1:  $lblOut.Text = \"Hi\";  $lstLog.AddItem(\"x\")\n"
                f"# Helpers: MsgBox \"text\", InputBox \"prompt\", RadSet/RadGet/RadInvoke obj ..., RadShow Form2, RadEnd,\n"
                f"#          radcall \"Module.function\" arg1 arg2 - call a function of a project module.\n\n"
                f"function {n}_Load($e) {{\n"
                f"    # runs when the form is shown\n"
                f"}}\n")

    def generate_designer(self, form: Form, user_code: str) -> str:
        n = form.name
        L = [f"# AUTO-GENERATED by RAD IDE from {n}.form - do not edit (changes will be lost).",
             "# The form is drawn by the IDE (GUI Bridge); these objects talk to its controls.",
             f"$script:{n} = New-RadControl {_quote(n)}"]
        for c in form.controls:
            if c.type == "MenuStrip" or not re.fullmatch(r"[A-Za-z_]\w*", c.name):
                continue
            L.append(f"$script:{c.name} = New-RadControl {_quote(n + '.' + c.name)}   # {c.type}")
        return "\n".join(L) + "\n"

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*function\s+(?:global:|script:)?{re.escape(name)}\b", re.I)

    def add_handler(self, code, name, form, args=None):
        text = code.rstrip("\n")
        lines = (text + "\n\n").splitlines() if text else []
        lines += [f"function {name}($e) {{", "    ", "}"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def module_template(self, name: str) -> str:
        return (f"# Module {name}. Its functions can be used by every form (they are loaded first)\n"
                f"# and by other languages of the project through the RAD Hub:\n"
                f"#     radcall(\"{name}.Add\", 2, 3)    (Python/C#/Java syntax; in PowerShell: radcall \"{name}.Add\" 2 3)\n"
                f"# Arguments and results are JSON values. Return a one-item list with: return ,@($x)\n"
                f"# Gallery modules: Project > Packages (Install-Module -Scope CurrentUser), then Import-Module.\n\n"
                f"function Add($a, $b) {{\n"
                f"    return $a + $b\n"
                f"}}\n")

    def on_file_removed(self, code: str, filename: str) -> str:
        return code

    # ------------------------------------------------------------ References (CONTRACTS 7.2)
    def exported_functions(self, path: Path, text: str) -> list:
        """Top-level functions of a library .ps1 (names starting with _ and X_Event handlers skipped)."""
        return refs.ps_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>.ref.ps1`` (loaded before the project's files): functions ``<Lib>.<Name>`` and an
        object ``$<Lib>`` with the same methods - ``MathLib.Add 2 3`` or ``$MathLib.Add(2, 3)``."""
        return refs.ps_proxy(lib, functions)

    def example_function(self, name: str) -> str:
        return ("# Adds two numbers.\n"
                "function Add($a, $b) {\n"
                "    return $a + $b\n"
                "}\n")

    def library_template(self, name: str) -> str:
        return (f"# Class Library {name}. Its functions are the library's public functions (names starting\n"
                f"# with _ stay private): a project that references {name} (Add Reference) calls them natively -\n"
                f"#     {name}.Add 2 3  or  ${name}.Add(2, 3) in PowerShell,  {name}.Add(2, 3) in C#/Python/Java\n"
                f"# Arguments and results are JSON values. Return a one-item list with: return ,@($x)\n\n"
                f"{self.example_function(name)}\n"
                f"# Returns a greeting.\n"
                f"function Greet($name) {{\n"
                f"    return \"Hello, $name!\"\n"
                f"}}\n")

    # ------------------------------------------------------------ run
    def prepare(self, folder: Path, project: Project) -> None:
        ensure_build_dir(folder)

    def build_command(self, folder: Path, project: Project) -> str | None:
        return None             # RadMain.ps1 checks the syntax itself before running

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return ps_command(Path(folder).resolve() / BUILD_DIR / "RadMain.ps1")

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        main = ensure_build_dir(Path(folder).resolve())
        return ps_command(main, "-Worker", Path(module_file).stem)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        names = names or {}
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\$(?:script:)?(\w+)\.\w*$", before)
        if m:
            obj = m.group(1)
            if obj.lower() == "e":
                return [Completion(k, "property", d) for k, d in EVENT_MEMBERS.items()]
            if obj in names or obj.lower() in {n.lower() for n in names}:
                return [Completion(k, "method" if "(" in d else "property", d) for k, d in CONTROL_MEMBERS.items()]
            if path:
                return [Completion(n, "method", d) for n, d in refs.proxy_members(Path(path).parent, obj, "ps")]
            return []
        m = re.search(r"(?:^|[\s(;|=])([A-Za-z_]\w*)\.[\w-]*$", before)
        if m and path:      # MathLib.Add 2 3 (reference proxy functions)
            members = refs.proxy_members(Path(path).parent, m.group(1), "ps")
            if members:
                return [Completion(n, "function", d) for n, d in members]
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in RAD_HELPERS.items()]
        out += [Completion(c, "function") for c in CMDLETS]
        out += [Completion(f"${n}", "control", t) for n, t in names.items()]
        seen = {c.name.lower() for c in out}
        for w in re.findall(r"\$?[A-Za-z_][\w-]{2,}", code):
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(Completion(w, "variable"))
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(\w+)\s+[^|;]*$", before) or re.search(r"(\w+)\s*$", before)
        if m:
            for k, d in RAD_HELPERS.items():
                if k.lower() == m.group(1).lower():
                    return d
        return ""


PLUGIN = PowerShellBridgePlugin()
