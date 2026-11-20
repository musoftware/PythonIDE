"""Visual Studio solutions and projects opened IN PLACE (.sln, .slnx, .csproj, .vbproj, .fsproj, .vcxproj).

Nothing is written into the user's folder except intended edits: no project.radproj, no .radsln.
IDE-only state (startup project, active configuration/platform) lives in
``%APPDATA%\\RADIDE\\foreign\\<name>-<hash>`` (``radide.foreign._others_base.state_dir``).

* ``SlnModel`` / ``SlnxModel`` - parse a solution (projects, solution folders, solution items,
  configurations, project configuration mapping) and edit it as text (add/remove a project)
  keeping everything else byte-identical.
* ``VsProject``  - a ``radide.model.Project`` built from an MSBuild project
  (``radide.foreign.msbuild.MSBuildProject``): code files are modules, WinForms forms
  (Form1.cs + Form1.Designer.cs) are forms designed through radide/foreign/winforms_cs.py
  (FORM_STORES: the Designer file is the source of truth), and it draws a Visual Studio like
  Solution Explorer subtree (Dependencies/References, folders, Form1.cs > Form1.Designer.cs +
  Form1.resx, vcxproj filters).
* ``VsPlugin``   - per-project language plugin: NuGet packages through ``dotnet add package`` (SDK)
  or a format-preserving PackageReference edit (legacy), and Run/Debug through
  ``make_session``: build with ``dotnet build`` (SDK) or Visual Studio's MSBuild (vswhere; legacy
  .NET Framework and C++), run the output, debug .NET (Core/5+) with netcoredbg (breakpoints
  in .cs/.vb/.fs).
* ``VsSolution`` - a ``radide.solution.Solution`` around the .sln/.slnx: Set as StartUp
  Project, Configuration/Platform (toolbar combos), Build/Rebuild/Clean Solution, solution
  folders in the Solution Explorer.
* Add New Item (class, interface, Windows Form, User Control, VB module, F# file, C++ source /
  header), Add Existing Item, New Folder, Exclude from Project, Add Reference (projects of the
  solution, framework assemblies, browse for a .dll), Manage NuGet Packages, project Properties.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..languages.base import LanguagePlugin, PackageManager, RunSpec
from ..model import Project
from ..solution import Solution, SolutionProject
from . import msbuild as MB
from .msbuild import MSBuildProject, TextFile, ms_path, norm_rel

PROJECT_EXTS = (".csproj", ".vbproj", ".fsproj", ".vcxproj")
SOLUTION_EXTS = (".sln", ".slnx")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BASE_PLUGIN = {"C#": "csharp-bridge", "VB": "vb-basic", "F#": "csharp-bridge", "C++": "cpp-bridge"}
LANG_NAME = {"C#": "C#", "VB": "VB.NET", "F#": "F#", "C++": "C++"}


def state_dir(native: Path) -> Path:
    try:
        from ._others_base import state_dir as sd
        return sd(native)
    except Exception:  # noqa: BLE001 - same layout without the shared helper
        root = Path(os.environ.get("RADIDE_FOREIGN_STATE") or
                    Path(os.environ.get("APPDATA") or Path.home()) / "RADIDE" / "foreign")
        h = hashlib.sha1(os.path.normcase(str(Path(native).resolve())).encode()).hexdigest()[:16]
        d = root / f"{Path(native).name}-{h}"
        d.mkdir(parents=True, exist_ok=True)
        return d


# ====================================================================== solution files
@dataclass
class SlnEntry:
    name: str
    path: str                      # relative to the solution folder, forward slashes
    type_guid: str = ""
    guid: str = ""
    parent: str = ""               # guid of the solution folder that holds it
    items: list[str] = field(default_factory=list)       # solution items (folders only)

    @property
    def is_folder(self) -> bool:
        return self.type_guid.upper() == MB.FOLDER_GUID

    @property
    def is_project(self) -> bool:
        return not self.is_folder and Path(self.path).suffix.lower() in PROJECT_EXTS


_PROJ_RX = re.compile(r'^Project\("(\{[^}]+\})"\)\s*=\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"(\{[^}]+\})"\s*$')


class SlnModel:
    """A classic .sln file (text format 12.00)."""

    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.file = TextFile.read(self.path)
        self.parse()

    @property
    def folder(self) -> Path:
        return self.path.parent

    def parse(self) -> None:
        lines = self.file.text.splitlines()
        self.entries: list[SlnEntry] = []
        self.configs: list[str] = []                 # "Debug|Any CPU"
        self.project_cfg: dict[tuple[str, str], tuple[str, bool]] = {}   # (guid, sol cfg) -> (proj cfg, build)
        cur: SlnEntry | None = None
        section = ""
        for raw in lines:
            line = raw.strip()
            m = _PROJ_RX.match(line)
            if m:
                cur = SlnEntry(m.group(2), norm_rel(m.group(3)), m.group(1).upper(), m.group(4).upper())
                self.entries.append(cur)
                continue
            if line == "EndProject":
                cur = None
                continue
            if line.startswith("ProjectSection(") or line.startswith("GlobalSection("):
                section = line[line.find("(") + 1: line.find(")")]
                continue
            if line in ("EndProjectSection", "EndGlobalSection"):
                section = ""
                continue
            if "=" not in line:
                continue
            left, right = (x.strip() for x in line.split("=", 1))
            if section == "SolutionItems" and cur is not None:
                cur.items.append(norm_rel(left))
            elif section == "SolutionConfigurationPlatforms":
                if left not in self.configs:
                    self.configs.append(left)
            elif section == "ProjectConfigurationPlatforms":
                m2 = re.match(r"(\{[^}]+\})\.(.+?)\.(ActiveCfg|Build\.0)$", left)
                if m2:
                    key = (m2.group(1).upper(), m2.group(2))
                    pc, build = self.project_cfg.get(key, ("", False))
                    if m2.group(3) == "ActiveCfg":
                        pc = right
                    else:
                        build = True
                    self.project_cfg[key] = (pc, build)
            elif section == "NestedProjects":
                child = next((e for e in self.entries if e.guid == left.upper()), None)
                if child is not None:
                    child.parent = right.upper()

    # queries
    def projects(self) -> list[SlnEntry]:
        return [e for e in self.entries if e.is_project]

    def folders(self) -> list[SlnEntry]:
        return [e for e in self.entries if e.is_folder]

    def folder_path(self, entry: SlnEntry) -> list[str]:
        """Names of the solution folders above *entry* (outermost first)."""
        out, seen = [], set()
        p = entry.parent
        while p and p not in seen:
            seen.add(p)
            f = next((e for e in self.entries if e.guid == p), None)
            if f is None:
                break
            out.insert(0, f.name)
            p = f.parent
        return out

    def configurations(self) -> list[str]:
        return list(dict.fromkeys(c.split("|")[0] for c in self.configs)) or ["Debug", "Release"]

    def platforms(self) -> list[str]:
        return list(dict.fromkeys(c.split("|")[1] for c in self.configs if "|" in c)) or ["Any CPU"]

    def project_config(self, entry: SlnEntry, cfg: str, plat: str) -> tuple[str, str, bool]:
        pc, build = self.project_cfg.get((entry.guid, f"{cfg}|{plat}"), ("", True))
        if not pc:
            return cfg, plat, True
        c, _, p = pc.partition("|")
        return c, p, build

    # edits
    def add_project(self, project_file: Path, folder_guid: str = "") -> SlnEntry:
        proj = MSBuildProject.load(project_file)
        rel = os.path.relpath(Path(project_file).resolve(), self.folder)
        key = proj.language + ("-sdk" if proj.is_sdk and proj.language != "C++" else "")
        tguid = MB.TYPE_GUIDS.get(key, MB.TYPE_GUIDS["C#"])
        if proj.language in ("C#", "VB", "F#") and not proj.is_sdk:
            tguid = MB.TYPE_GUIDS[proj.language]
        if proj.is_sdk and proj.language in ("C#", "VB", "F#"):
            tguid = MB.TYPE_GUIDS[proj.language]          # what 'dotnet sln add' writes
        guid = (proj.prop("ProjectGuid") or "{" + str(uuid.uuid4()).upper() + "}").upper()
        nl = self.file.newline
        text = self.file.text
        block = f'Project("{tguid}") = "{proj.name}", "{ms_path(rel)}", "{guid}"{nl}EndProject{nl}'
        m = re.search(r"^Global\s*$", text, re.M)
        at = m.start() if m else len(text)
        text = text[:at] + block + text[at:]
        cfg_lines = []
        for sc in self.configs or ["Debug|Any CPU", "Release|Any CPU"]:
            c, _, p = sc.partition("|")
            pp = MB.project_platform(p, proj)
            pp = "Any CPU" if pp == "AnyCPU" else pp
            cfg_lines.append(f"\t\t{guid}.{sc}.ActiveCfg = {c}|{pp}")
            cfg_lines.append(f"\t\t{guid}.{sc}.Build.0 = {c}|{pp}")
        sec = re.search(r"^\s*GlobalSection\(ProjectConfigurationPlatforms\)[^\n]*\n(.*?)^\s*EndGlobalSection",
                        text, re.M | re.S)
        if sec:
            at = sec.end(1)
            text = text[:at] + nl.join(cfg_lines) + nl + text[at:]
        else:
            sc = re.search(r"^\s*GlobalSection\(SolutionConfigurationPlatforms\).*?EndGlobalSection[^\n]*\n",
                           text, re.M | re.S)
            if sc:
                blockc = f"\tGlobalSection(ProjectConfigurationPlatforms) = postSolution{nl}" + \
                    nl.join(cfg_lines) + f"{nl}\tEndGlobalSection{nl}"
                text = text[:sc.end()] + blockc + text[sc.end():]
        if folder_guid:
            nest = f"\t\t{guid} = {folder_guid.upper()}"
            sec = re.search(r"^\s*GlobalSection\(NestedProjects\)[^\n]*\n(.*?)^\s*EndGlobalSection", text, re.M | re.S)
            if sec:
                text = text[:sec.end(1)] + nest + nl + text[sec.end(1):]
        self.file.text = text
        self.parse()
        return next(e for e in self.entries if e.guid == guid)

    def remove_project(self, guid: str) -> bool:
        guid = guid.upper()
        text = self.file.text
        rx = re.compile(r'^Project\("\{[^}]+\}"\)\s*=\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"' + re.escape(guid) +
                        r'"\s*\r?\n.*?^EndProject[ \t]*\r?\n', re.M | re.S | re.I)
        new = rx.sub("", text, count=1)
        if new == text:
            return False
        new = re.sub(r"^[ \t]*" + re.escape(guid) + r"[^\n]*\n", "", new, flags=re.M | re.I)
        self.file.text = new
        self.parse()
        return True

    def save(self) -> bool:
        return self.file.save()


class SlnxModel(SlnModel):
    """The XML solution format (.slnx, VS 17.13+ / .NET 9.0.200+)."""

    def parse(self) -> None:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", self.file.text).encode("utf-8"))
        self.entries, self.configs, self.project_cfg = [], [], {}
        builds = [b.get("Name") for b in root.iter("BuildType")] or ["Debug", "Release"]
        plats = [p.get("Name") for c in root.iter("Configurations") for p in c.iter("Platform")]
        plats = plats or ["Any CPU"]
        self.configs = [f"{b}|{p}" for b in builds for p in plats]

        def walk(el, parent_guid):
            for ch in el:
                if ch.tag == "Folder":
                    name = ch.get("Name", "").strip("/")
                    g = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "slnx:" + name)).upper() + "}"
                    e = SlnEntry(name.split("/")[-1], name, MB.FOLDER_GUID, g, parent_guid)
                    e.items = [norm_rel(f.get("Path", "")) for f in ch if f.tag == "File"]
                    self.entries.append(e)
                    walk(ch, g)
                elif ch.tag == "Project":
                    p = norm_rel(ch.get("Path", ""))
                    g = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "slnx:" + p.lower())).upper() + "}"
                    self.entries.append(SlnEntry(Path(p).stem, p, ch.get("Type", ""), g, parent_guid))
        walk(root, "")

    def add_project(self, project_file: Path, folder_guid: str = "") -> SlnEntry:
        rel = os.path.relpath(Path(project_file).resolve(), self.folder).replace("\\", "/")
        text, nl = self.file.text, self.file.newline
        m = re.search(r"\n([ \t]+)<(?:Project|Folder|Configurations)\b", text)
        indent = m.group(1) if m else "  "
        line = f'{indent}<Project Path="{MB.xml_escape(rel)}" />'
        end = text.rfind("</Solution>")
        ls = text.rfind("\n", 0, end) + 1
        self.file.text = text[:ls] + line + nl + text[ls:]
        self.parse()
        return next(e for e in self.entries if e.path.lower() == norm_rel(rel).lower())

    def remove_project(self, guid: str) -> bool:
        e = next((x for x in self.entries if x.guid == guid.upper()), None)
        if e is None:
            return False
        rx = re.compile(r'^[ \t]*<Project\b[^>]*Path="' + r"[\\/]".join(re.escape(p) for p in re.split(r"[\\/]", e.path))
                        + r'"[^>]*?(?:/>|>.*?</Project>)[ \t]*\r?\n', re.M | re.S | re.I)
        new = rx.sub("", self.file.text, count=1)
        if new == self.file.text:
            return False
        self.file.text = new
        self.parse()
        return True


def load_solution_model(path: Path) -> SlnModel:
    return SlnxModel(path) if Path(path).suffix.lower() == ".slnx" else SlnModel(path)


# ====================================================================== templates (Add New Item)
def _file_scoped(project: MSBuildProject) -> bool:
    for f in project.code_files()[:20]:
        try:
            t = (project.folder / f).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if re.search(r"^\s*namespace\s+[\w.]+\s*;", t, re.M):
            return True
        if re.search(r"^\s*namespace\s+[\w.]+\s*\{?\s*$", t, re.M):
            return False
    return project.is_sdk


def _ns_for(project: MSBuildProject, rel_dir: str) -> str:
    ns = project.root_namespace
    for part in [p for p in rel_dir.replace("\\", "/").split("/") if p]:
        ns += "." + re.sub(r"\W", "_", part)
    return ns


def _cs_wrap(project: MSBuildProject, ns: str, body: str, usings: list[str]) -> str:
    use = "".join(f"using {u};\n" for u in usings) + ("\n" if usings else "")
    if _file_scoped(project):
        return f"{use}namespace {ns};\n\n{body}"
    inner = "".join(("    " + ln if ln.strip() else ln) for ln in body.splitlines(True))
    return f"{use}namespace {ns}\n{{\n{inner}}}\n"


CS_DESIGNER = '''partial class {name}
{{
    /// <summary>
    ///  Required designer variable.
    /// </summary>
    private System.ComponentModel.IContainer components = null;

    /// <summary>
    ///  Clean up any resources being used.
    /// </summary>
    /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
    protected override void Dispose(bool disposing)
    {{
        if (disposing && (components != null))
        {{
            components.Dispose();
        }}
        base.Dispose(disposing);
    }}

    #region {kind} Designer generated code

    /// <summary>
    ///  Required method for Designer support - do not modify
    ///  the contents of this method with the code editor.
    /// </summary>
    private void InitializeComponent()
    {{
        this.components = new System.ComponentModel.Container();
        this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
{size}
    }}

    #endregion
}}
'''

VB_DESIGNER = '''<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class {name}
    Inherits {base}

    'Form overrides dispose to clean up the component list.
    <System.Diagnostics.DebuggerNonUserCode()>
    Protected Overrides Sub Dispose(disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    'Required by the Windows Form Designer
    Private components As System.ComponentModel.IContainer

    'NOTE: The following procedure is required by the Windows Form Designer
    'It can be modified using the Windows Form Designer.
    'Do not modify it using the code editor.
    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        components = New System.ComponentModel.Container()
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
{size}
    End Sub

End Class
'''

ITEM_TEMPLATES = {
    "C#": [("Class", ".cs"), ("Interface", ".cs"), ("Windows Form", ".cs"), ("User Control", ".cs"),
           ("Enum", ".cs"), ("Code File", ".cs"), ("Text File", ".txt"), ("JSON File", ".json")],
    "VB": [("Class", ".vb"), ("Module", ".vb"), ("Interface", ".vb"), ("Windows Form", ".vb"),
           ("User Control", ".vb"), ("Code File", ".vb"), ("Text File", ".txt")],
    "F#": [("Source File", ".fs"), ("Script File", ".fsx"), ("Text File", ".txt")],
    "C++": [("C++ File (.cpp)", ".cpp"), ("Header File (.h)", ".h"), ("Text File", ".txt")],
}


def new_item_files(project: MSBuildProject, template: str, rel_dir: str, name: str) -> list[tuple[str, str, str, dict]]:
    """[(relative path, text, item kind, metadata)] for Add > New Item."""
    lang = project.language
    rel_dir = rel_dir.strip("/").replace("\\", "/")
    pre = f"{rel_dir}/" if rel_dir else ""
    ext = dict(ITEM_TEMPLATES.get(lang, [])).get(template, "")
    base = re.sub(r"\.(cs|vb|fs|fsx|cpp|h|txt|json)$", "", name, flags=re.I)
    out: list[tuple[str, str, str, dict]] = []
    ns = _ns_for(project, rel_dir)
    legacy = not project.is_sdk
    if lang == "C#":
        win = ["System", "System.Windows.Forms"] if legacy else []
        if template in ("Windows Form", "User Control"):
            kind_base = "Form" if template == "Windows Form" else "UserControl"
            body = (f"public partial class {base} : {kind_base}\n{{\n    public {base}()\n    {{\n"
                    f"        InitializeComponent();\n    }}\n}}\n")
            size = (f'        this.ClientSize = new System.Drawing.Size(800, 450);\n        this.Text = "{base}";'
                    if kind_base == "Form" else "")
            des = CS_DESIGNER.format(name=base, size=size.rstrip(),
                                     kind="Windows Form" if kind_base == "Form" else "Component")
            if not size:
                des = des.replace("\n\n    }\n\n    #endregion", "\n    }\n\n    #endregion")
            out.append((f"{pre}{base}.cs", _cs_wrap(project, ns, body, win), "Compile",
                        {"SubType": kind_base} if legacy else {}))
            out.append((f"{pre}{base}.Designer.cs", _cs_wrap(project, ns, des, []), "Compile",
                        {"DependentUpon": f"{base}.cs"} if legacy else {}))
        elif template in ("Class", "Interface", "Enum", "Code File"):
            kw = {"Class": "internal class", "Interface": "internal interface", "Enum": "internal enum"}.get(template)
            usings = ["System", "System.Collections.Generic", "System.Linq", "System.Text"] if legacy else []
            body = f"{kw} {base}\n{{\n}}\n" if kw else ""
            out.append((f"{pre}{base}.cs", _cs_wrap(project, ns, body, usings) if kw else "", "Compile", {}))
    elif lang == "VB":
        if template in ("Windows Form", "User Control"):
            b = "System.Windows.Forms.Form" if template == "Windows Form" else "System.Windows.Forms.UserControl"
            size = (f'        Me.ClientSize = New System.Drawing.Size(800, 450)\n        Me.Text = "{base}"'
                    if template == "Windows Form" else "")
            des = VB_DESIGNER.format(name=base, base=b, size=size)
            if not size:
                des = des.replace("\n\n    End Sub", "\n    End Sub")
            out.append((f"{pre}{base}.vb", f"Public Class {base}\n\nEnd Class\n", "Compile",
                        {"SubType": "Form" if template == "Windows Form" else "UserControl"} if legacy else {}))
            out.append((f"{pre}{base}.Designer.vb", des, "Compile", {"DependentUpon": f"{base}.vb"} if legacy else {}))
        elif template == "Module":
            out.append((f"{pre}{base}.vb", f"Module {base}\n\nEnd Module\n", "Compile", {}))
        elif template == "Interface":
            out.append((f"{pre}{base}.vb", f"Public Interface {base}\n\nEnd Interface\n", "Compile", {}))
        elif template == "Class":
            out.append((f"{pre}{base}.vb", f"Public Class {base}\n\nEnd Class\n", "Compile", {}))
        else:
            out.append((f"{pre}{base}.vb", "", "Compile", {}))
    elif lang == "F#":
        if template == "Source File":
            out.append((f"{pre}{base}.fs", f"module {base}\n\nlet hello name =\n    printfn \"Hello %s\" name\n",
                        "Compile", {}))
        elif template == "Script File":
            out.append((f"{pre}{base}.fsx", "", "None", {}))
    elif lang == "C++":
        if template.startswith("C++"):
            out.append((f"{pre}{base}.cpp", "", "ClCompile", {}))
        elif template.startswith("Header"):
            out.append((f"{pre}{base}.h", "#pragma once\n", "ClInclude", {}))
    if not out and ext:
        kind = "None"
        if template == "Text File" and lang == "C++":
            kind = "Text"
        out.append((f"{pre}{base}{ext}", "", kind, {}))
    return out


def _style_of(project: MSBuildProject) -> tuple[str, bool]:
    """(newline, bom) that new code files of the project should use (like the existing ones)."""
    for f in project.code_files()[:10]:
        try:
            raw = (project.folder / f).read_bytes()
        except OSError:
            continue
        return ("\r\n" if b"\r\n" in raw or b"\n" not in raw else "\n"), raw.startswith(b"\xef\xbb\xbf")
    return "\r\n", True


# ====================================================================== the plugin (per project)
class VsPlugin(LanguagePlugin):
    """Language plugin of one Visual Studio project (registered lazily while it is open)."""
    foreign = True
    supports_debug = True

    def __init__(self, project: "VsProject"):
        self.vsproject = project
        ms = project.ms
        h = hashlib.sha1(os.path.normcase(str(ms.path)).encode()).hexdigest()[:8]
        self.id = f"vs-{ms.language.replace('#', 'sharp').replace('+', 'p').lower()}-{h}"
        self.display_name = f"{LANG_NAME.get(ms.language, ms.language)} (Visual Studio project)"
        self.code_ext = ""
        try:
            from ..languages import get_plugin
            self.base = get_plugin(BASE_PLUGIN.get(ms.language, "csharp-bridge"))
        except Exception:  # noqa: BLE001
            self.base = None
        for attr in ("keywords", "builtins", "case_sensitive", "line_comments", "block_comment", "string_quotes"):
            if self.base is not None:
                setattr(self, attr, getattr(self.base, attr))
        self.package_manager = self._nuget(ms) if ms.language != "C++" else None

    @staticmethod
    def _nuget(ms: MSBuildProject) -> PackageManager:
        proj, script = str(ms.path), str(Path(MB.__file__).resolve())
        listing = [sys.executable, script, "packages", proj]
        if MB.uses_dotnet_cli(ms):
            install = ["dotnet", "add", proj, "package", "{name}", "--version", "{version}"]
            uninstall = ["dotnet", "remove", proj, "package", "{name}"]
        else:                                # legacy: PackageReference written in place (restored by MSBuild)
            install = [sys.executable, script, "add-package", proj, "{name}", "{version}"]
            uninstall = [sys.executable, script, "remove-package", proj, "{name}"]
        return PackageManager(name="NuGet", tool="dotnet", list_cmd=listing,
                              search_cmd=["dotnet", "package", "search", "{query}", "--take", "30"],
                              install_cmd=install, uninstall_cmd=uninstall, init_cmd=None,
                              manifest=ms.path.name, search_url="https://www.nuget.org/packages?q={query}")

    @staticmethod
    def for_project(project: "VsProject") -> "VsPlugin":
        from .. import languages
        languages.all_plugins()
        p = VsPlugin(project)
        languages._PLUGINS[p.id] = p
        return p

    # files
    def code_file(self, form_name: str) -> str:
        return self.vsproject.form_code.get(form_name, f"{form_name}{self.vsproject.ms.code_ext}")

    def designer_file(self, form_name: str) -> str:
        return str(self.vsproject.state / "generated" / f"{form_name}.txt")

    def generate_designer(self, form, user_code: str) -> str:
        return ""

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def completions(self, *a, **kw):
        return self.base.completions(*a, **kw) if self.base is not None else []

    def calltip(self, *a, **kw):
        return self.base.calltip(*a, **kw) if self.base is not None else None

    # run / debug
    def find_interpreter(self, configured: str = "") -> str:
        return MB.find_dotnet() or MB.find_msbuild() or sys.executable

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(interpreter or "dotnet", [], Path(folder))

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    def make_session(self, win, spec, debug: bool):
        sln = win.sln if isinstance(win.sln, VsSolution) else None
        return make_run_session(win, self.vsproject, debug, sln)


class _FormsPlugin:
    """Wraps radide/foreign/winforms_cs.py's plugin for one project: forms in sub folders
    (code_file = the real relative path), and the generic "designer file" of the IDE goes to the
    IDE state folder - the native Designer file is written by the form store (byte-preserving)."""

    @staticmethod
    def make(base, project: "VsProject"):
        cls = type(f"VsForms_{type(base).__name__}", (type(base),), {
            "code_file": lambda self, n: project.form_code.get(n, f"{n}{base.code_ext}"),
            "designer_file": lambda self, n: str(project.state / "generated" / f"{n}.designer.txt"),
        })
        p = cls()
        h = hashlib.sha1(os.path.normcase(str(project.ms.path)).encode()).hexdigest()[:8]
        p.id = f"{base.id}-{h}"
        from .. import languages
        languages._PLUGINS[p.id] = p
        return p


# ====================================================================== the project
class VsProject(Project):
    """A Visual Studio project (MSBuild file) as a RAD IDE Project - project.radproj is never written."""

    def __init__(self, ms: MSBuildProject, solution: "VsSolution | None" = None, name: str = ""):
        Project.__init__(self, ms.folder, name or ms.name, "")
        self.ms = ms
        self.native = ms.path
        self.solution_ref = solution
        self.foreign = True
        self.state = state_dir(ms.path)
        (self.state / "generated").mkdir(parents=True, exist_ok=True)
        self.form_code: dict[str, str] = {}          # form name -> code file (relative)
        self.form_designer: dict[str, str] = {}      # form name -> Designer file (relative)
        self.plugin = VsPlugin.for_project(self)
        self.language = self.plugin.id
        self.kind = "library" if ms.is_library else "app"
        self.extra = {"foreign": "visual-studio"}
        self._styles: dict[str, tuple[bytes, str, float]] = {}
        self._watch_mtime = self._mtime()
        self.scan()
        self.startup = self.name             # never a form name: Run uses this project's plugin
        self.notes: list[str] = []

    # ------------------------------------------------------------------ scanning
    def _mtime(self) -> float:
        try:
            return self.ms.path.stat().st_mtime_ns
        except OSError:
            return 0

    def scan(self) -> None:
        """(Re)build modules and forms from the project file."""
        ms = self.ms
        files = ms.files()
        self.items = files
        rels = [f.rel for f in files]
        self.form_code, self.form_designer = {}, {}
        self.forms, self.form_languages = [], {}
        forms_ok = ms.language in ("C#", "VB") and (ms.is_windows_app or not ms.is_sdk or
                                                    ms.prop("UseWindowsForms").lower() == "true")
        lowset = {r.lower(): r for r in rels}
        designers = set()
        if forms_ok:
            ext = ms.code_ext
            for r in rels:
                low = r.lower()
                if not low.endswith(".designer" + ext):
                    continue
                code = r[: -len(".designer" + ext)] + ext
                if code.lower() not in lowset:
                    continue
                try:
                    txt = (ms.folder / r).read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    continue
                if "InitializeComponent" not in txt:
                    continue
                name = Path(code).stem
                if name in self.form_code:
                    continue
                self.form_code[name] = lowset[code.lower()]
                self.form_designer[name] = r
                designers.add(r.lower())
        self._forms_plugin = None
        if self.form_code:
            try:
                from . import winforms_cs
                winforms_cs.register_plugins()
                from ..languages import get_plugin
                base = get_plugin("winforms-vb" if ms.language == "VB" else "winforms-cs")
                self._forms_plugin = _FormsPlugin.make(base, self)
            except Exception as e:  # noqa: BLE001 - no designer: the forms stay code files
                self._forms_plugin = None
                self.notes = [f"WinForms designer unavailable ({e}); forms open as code"]
        if self._forms_plugin is not None:
            for name in self.form_code:
                self.forms.append(name)
                self.form_languages[name] = self._forms_plugin.id
        form_code_low = {v.lower() for v in self.form_code.values()} if self._forms_plugin else set()
        text_ext = (".cs", ".vb", ".fs", ".fsx", ".fsi", ".cpp", ".c", ".cc", ".cxx", ".h", ".hpp", ".hxx",
                    ".config", ".json", ".xml", ".txt", ".md", ".settings", ".xaml", ".resx", ".props",
                    ".targets", ".editorconfig", ".sql", ".ps1", ".bat", ".cmd", ".rc", ".def", ".manifest",
                    ".html", ".css", ".js", ".ts", ".yml", ".yaml", ".ini")
        self.modules = [r for r in rels if r.lower().endswith(text_ext) and r.lower() not in form_code_low
                        and not r.lower().endswith(".resx")]
        for r in self.modules:
            self._remember_style(r)
        for r in self.form_code.values():
            self._remember_style(r)

    def form_path(self, form_name: str) -> Path:
        """The form's Designer file: Form.load / Form.save go through the WinForms form store
        (radide/foreign/winforms_cs.py WinFormsStore), which reads and patches it in place."""
        des = self.form_designer.get(form_name)
        if des:
            return self.folder / des
        code = self.form_code.get(form_name)
        base = (self.folder / code).parent if code else self.folder
        return base / f"{form_name}.form"

    def missing_forms(self) -> list[str]:
        return [f for f in self.forms if not (self.folder / self.form_designer.get(f, "")).is_file()]

    def reload(self) -> None:
        self.ms.reload()
        self.kind = "library" if self.ms.is_library else "app"
        self.scan()
        self._watch_mtime = self._mtime()
        try:
            self.plugin.package_manager = VsPlugin._nuget(self.ms) if self.ms.language != "C++" else None
        except Exception:  # noqa: BLE001
            pass

    def changed_on_disk(self) -> bool:
        return self._mtime() != self._watch_mtime

    # ------------------------------------------------------------------ saving
    def _remember_style(self, rel: str) -> None:
        p = self.folder / rel
        if rel in self._styles:
            return
        try:
            raw = p.read_bytes()
            st = p.stat().st_mtime_ns
        except OSError:
            return
        bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        nl = "\r\n" if b"\r\n" in raw else ("\n" if b"\n" in raw else "")
        self._styles[rel] = (bom, nl, st)

    def fix_styles(self) -> list[str]:
        """The IDE writes edited code files as UTF-8 with Windows newlines; give files changed
        since they were opened back their own BOM / newline style (like Visual Studio keeps it)."""
        fixed = []
        for rel, (bom, nl, mt) in list(self._styles.items()):
            p = self.folder / rel
            try:
                now = p.stat().st_mtime_ns
                if now == mt:
                    continue
                raw = p.read_bytes()
            except OSError:
                continue
            body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
            text = body.decode("utf-8", errors="surrogateescape")
            if nl:
                text = text.replace("\r\r\n", "\n").replace("\r\n", "\n")
                text = text.replace("\n", nl)
            data = bom + text.encode("utf-8", errors="surrogateescape")
            if data != raw:
                p.write_bytes(data)
                fixed.append(rel)
            try:
                self._styles[rel] = (bom, nl, p.stat().st_mtime_ns)
            except OSError:
                pass
        return fixed

    def save(self) -> None:
        """Never writes project.radproj: the project file is edited by the actions that change it;
        this keeps the files' encodings and stores IDE-only state."""
        self.fix_styles()
        if self.ms.file.dirty:
            self.ms.save()
            self._watch_mtime = self._mtime()
        data = {"native": str(self.ms.path), "kind": "visual-studio"}
        try:
            (self.state / "ide-state.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------ edits
    def add_new_item(self, template: str, rel_dir: str, name: str) -> list[str]:
        """Create the files of an item template and register them in the project file where the
        project type needs it. Returns the relative paths created. Raises ValueError."""
        files = new_item_files(self.ms, template, rel_dir, name)
        if not files:
            raise ValueError(f"no template '{template}' for {self.ms.language}")
        for rel, _t, _k, _m in files:
            if (self.folder / rel).exists():
                raise ValueError(f"{rel} already exists")
        nl, bom = _style_of(self.ms)
        created = []
        for rel, text, kind, md in files:
            p = self.folder / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = text.replace("\r\n", "\n").replace("\n", nl).encode("utf-8")
            if bom and text and p.suffix.lower() in (".cs", ".vb", ".fs"):
                data = b"\xef\xbb\xbf" + data
            p.write_bytes(data)
            created.append(rel)
            if self.ms.language == "C++":
                if self.ms.add_source(rel, kind if kind in ("ClCompile", "ClInclude", "Text") else ""):
                    MB.add_to_filters(self.ms, rel, kind)
            elif self.ms.needs_compile_entry(rel) or md:
                self.ms.add_source(rel, kind, md or None)
        self.ms.save()
        self.reload()
        return created

    def add_existing_item(self, path: Path, rel_dir: str = "") -> str:
        """Copy (when outside the project folder) and include an existing file."""
        path = Path(path).resolve()
        try:
            rel = path.relative_to(self.folder).as_posix()
        except ValueError:
            target = self.folder / rel_dir / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(path, target)
            rel = target.relative_to(self.folder).as_posix()
        kind = ""
        if self.ms.language == "C++":
            kind = "ClInclude" if rel.lower().endswith((".h", ".hpp", ".hxx")) else "ClCompile"
            if self.ms.add_source(rel, kind):
                MB.add_to_filters(self.ms, rel, kind)
        else:
            implicit = any(f.rel.lower() == rel.lower() for f in self.ms.files())
            if not implicit or self.ms.needs_compile_entry(rel):
                self.ms.add_source(rel, kind)
            for f in self.ms.explicit(None, "Remove"):                  # it was excluded before
                if f.rel.lower() == rel.lower():
                    self.ms.remove_item(f.kind, f.include, "Remove")
        self.ms.save()
        self.reload()
        return rel

    def exclude(self, rel: str) -> bool:
        ok = self.ms.remove_source(rel)
        self.ms.save()
        self.reload()
        return ok

    def add_project_reference(self, other: "VsProject") -> bool:
        ok = self.ms.add_project_reference(other.ms.path, other.ms.prop("ProjectGuid"), other.ms.name)
        self.ms.save()
        self.reload()
        return ok

    def add_assembly_reference(self, name: str, hint: str = "") -> bool:
        if hint:
            try:
                hint = os.path.relpath(hint, self.folder)
            except ValueError:
                pass
        ok = self.ms.add_assembly_reference(name, hint)
        self.ms.save()
        self.reload()
        return ok

    def remove_reference(self, kind: str, include: str) -> bool:
        ok = self.ms.remove_item(kind, include)
        self.ms.save()
        self.reload()
        return ok

    # ------------------------------------------------------------------ Solution Explorer
    def fill_solution_tree(self, win, pi, name: str) -> None:
        from . import vs_ui
        vs_ui.fill_project(win, self, pi, name)

    def build_solution_menu(self, win, item, kind, name):
        from . import vs_ui
        return vs_ui.project_menu(win, self, item, kind, name)

    def on_tree_activate(self, win, item, kind, name) -> None:
        from . import vs_ui
        vs_ui.activate(win, self, item, kind, name)


# ====================================================================== the solution
@dataclass
class VsSolution(Solution):
    """A .sln/.slnx (or a lone project file) in the IDE. save() never writes a .radsln."""
    model: object = None
    configuration: str = "Debug"
    platform: str = "Any CPU"
    state: Path | None = None

    foreign = True

    def save(self, path=None) -> Path:
        data = {"startup": self.startup, "configuration": self.configuration, "platform": self.platform}
        if self.state is not None:
            try:
                (self.state / "ide-state.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            except OSError:
                pass
        if isinstance(self.model, SlnModel) and self.model.file.dirty:
            self.model.save()
        return self.file

    def project(self, name):
        if isinstance(name, Project):
            return name
        e = self.entry(name)
        return self._cache.get(e.name.lower()) if e is not None else None

    def rename(self, new_name: str) -> None:
        raise ValueError("rename the .sln file in Windows Explorer (the IDE does not rename solution files)")

    def configurations(self) -> list[str]:
        if isinstance(self.model, SlnModel):
            return self.model.configurations()
        ps = self.all_projects()
        return ps[0].ms.configuration_names() if ps else ["Debug", "Release"]

    def platforms(self) -> list[str]:
        if isinstance(self.model, SlnModel):
            return self.model.platforms()
        ps = self.all_projects()
        if ps and ps[0].ms.language == "C++":
            return ps[0].ms.platform_names()
        return ["Any CPU"]

    def project_config(self, project: VsProject) -> tuple[str, str]:
        """(configuration, platform) of a project for the active solution configuration."""
        if isinstance(self.model, SlnModel):
            e = next((x for x in self.model.projects() if os.path.normcase(str((self.model.folder / x.path).resolve()))
                      == os.path.normcase(str(project.ms.path))), None)
            if e is not None:
                c, p, _b = self.model.project_config(e, self.configuration, self.platform)
                return c, p
        return self.configuration, self.platform

    # hooks used by radide/features/solution_ui.py and radide/app.py
    def build_solution(self, win, only=None, wait: bool = False):
        from . import vs_ui
        return vs_ui.build(win, self, only=only, wait=wait)

    def build_solution_menu(self, win, item, kind, name):
        from . import vs_ui
        return vs_ui.solution_menu(win, self, item)

    def after_fill_tree(self, win, root) -> None:
        from . import vs_ui
        vs_ui.after_fill(win, self, root)

    def on_tree_activate(self, win, item, kind, name) -> None:
        from . import vs_ui
        vs_ui.activate(win, None, item, kind, name)

    def editor_for_file(self, win, file):
        from . import vs_ui
        return vs_ui.editor_for_file(win, self, file)


def load_vs(path: Path) -> VsSolution:
    """A VsSolution for a .sln/.slnx, a project file, or a folder holding one."""
    path = Path(path).resolve()
    if path.is_dir():
        hit = probe_folder(path)
        if hit is None:
            raise FileNotFoundError(f"no Visual Studio solution or project in {path}")
        path = hit
    ext = path.suffix.lower()
    if ext in SOLUTION_EXTS:
        model = load_solution_model(path)
        sln = VsSolution(path.stem, path.parent, [], "", path, model=model, state=state_dir(path))
        for e in model.projects():
            pf = (model.folder / e.path).resolve()
            if not pf.is_file():
                sln.projects.append(SolutionProject(e.name, os.path.relpath(pf.parent, path.parent)))
                continue
            try:
                ms = MSBuildProject.load(pf)
            except (OSError, ValueError):
                sln.projects.append(SolutionProject(e.name, os.path.relpath(pf.parent, path.parent)))
                continue
            vp = VsProject(ms, sln, e.name)
            vp.sln_entry = e
            _add(sln, vp)
    elif ext in PROJECT_EXTS:
        ms = MSBuildProject.load(path)
        sln = VsSolution(ms.name, path.parent, [], "", path, model=None, state=state_dir(path))
        _add(sln, VsProject(ms, sln))
    else:
        raise FileNotFoundError(f"{path.name} is not a Visual Studio solution or project")
    cfgs, plats = sln.configurations(), sln.platforms()
    sln.configuration = cfgs[0] if cfgs else "Debug"
    sln.platform = plats[0] if plats else "Any CPU"
    if "Any CPU" in plats:
        sln.platform = "Any CPU"
    try:
        st = json.loads((sln.state / "ide-state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        st = {}
    if st.get("configuration") in cfgs:
        sln.configuration = st["configuration"]
    if st.get("platform") in plats:
        sln.platform = st["platform"]
    if st.get("startup") and sln.entry(st["startup"]) is not None:
        sln.startup = sln.entry(st["startup"]).name
    if not sln.startup:
        sp = sln.startup_project()            # first application, like Visual Studio
        sln.startup = sln.name_of(sp) if sp is not None else ""
    return sln


def _add(sln: VsSolution, vp: VsProject) -> None:
    name = vp.name
    i = 2
    while sln.entry(name) is not None:
        name = f"{vp.name} ({i})"
        i += 1
    vp.name = name
    sln.projects.append(SolutionProject(name, os.path.relpath(vp.folder, sln.folder).replace("\\", "/")))
    sln._cache[name.lower()] = vp


def probe_folder(folder: Path) -> Path | None:
    """The .sln (then .slnx, then project file) of a folder: same-named first."""
    folder = Path(folder)
    for exts in ((".sln",), (".slnx",), PROJECT_EXTS):
        try:
            hits = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts)
        except OSError:
            return None
        if hits:
            same = [p for p in hits if p.stem.lower() == folder.name.lower()]
            return (same or hits)[0]
    return None


# ====================================================================== run / debug
def make_run_session(win, project: VsProject, debug: bool, sln: VsSolution | None):
    from . import vs_ui
    return vs_ui.run_session(win, project, debug, sln)


# ====================================================================== File > Open
def open_vs(win, path: Path) -> bool:
    from . import vs_ui
    return vs_ui.open_in_window(win, Path(path))


def install_ui(win) -> None:
    from . import vs_ui
    vs_ui.install(win)


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".sln", ".slnx"], open_vs, "Visual Studio solution", folder_probe=probe_folder,
                    name="vs-solution", priority=10)
    register_format(list(PROJECT_EXTS), open_vs, "Visual Studio project (C#, VB.NET, F#, C++)",
                    name="vs-project", priority=9)
