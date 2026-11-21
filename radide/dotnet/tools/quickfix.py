"""Light-bulb quick actions of RAD IDE for C# / VB (added next to the language server's own code actions):

* unknown type -> "using System.Text;" / "System.Text.StringBuilder" (fully qualify) - from the type index of
  the assemblies the project really compiles against (radide/dotnet/tools/metadata.py), so the suggestion is
  always a real public type
* a type declared in another project of the solution -> "Add reference to 'Calc' and using Calc;"
* a well-known NuGet type -> "Install package 'Newtonsoft.Json'" (a short curated map: nuget.org has no
  reliable type-name search any more, so nothing is guessed from search results)
* "Search NuGet.org for 'Foo'..." -> the NuGet Package Manager with the name filled in

Pure functions here; radide/dotnet/tools/ui.py turns them into menu entries and applies them."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import metadata, sdk

# well-known types of popular packages: type -> (package, namespace)
KNOWN_PACKAGES = {
    "JsonConvert": ("Newtonsoft.Json", "Newtonsoft.Json"),
    "JObject": ("Newtonsoft.Json", "Newtonsoft.Json.Linq"),
    "JArray": ("Newtonsoft.Json", "Newtonsoft.Json.Linq"),
    "JToken": ("Newtonsoft.Json", "Newtonsoft.Json.Linq"),
    "JsonProperty": ("Newtonsoft.Json", "Newtonsoft.Json"),
    "IMediator": ("MediatR", "MediatR"),
    "IRequest": ("MediatR", "MediatR"),
    "IRequestHandler": ("MediatR", "MediatR"),
    "AbstractValidator": ("FluentValidation", "FluentValidation"),
    "IMapper": ("AutoMapper", "AutoMapper"),
    "Profile": ("AutoMapper", "AutoMapper"),
    "SqliteConnection": ("Microsoft.Data.Sqlite", "Microsoft.Data.Sqlite"),
    "SqlConnection": ("Microsoft.Data.SqlClient", "Microsoft.Data.SqlClient"),
    "SqlCommand": ("Microsoft.Data.SqlClient", "Microsoft.Data.SqlClient"),
    "NpgsqlConnection": ("Npgsql", "Npgsql"),
    "MySqlConnection": ("MySqlConnector", "MySqlConnector"),
    "DbContext": ("Microsoft.EntityFrameworkCore", "Microsoft.EntityFrameworkCore"),
    "DbSet": ("Microsoft.EntityFrameworkCore", "Microsoft.EntityFrameworkCore"),
    "ModelBuilder": ("Microsoft.EntityFrameworkCore", "Microsoft.EntityFrameworkCore"),
    "Log": ("Serilog", "Serilog"),
    "LoggerConfiguration": ("Serilog", "Serilog"),
    "RestClient": ("RestSharp", "RestSharp"),
    "RestRequest": ("RestSharp", "RestSharp"),
    "Policy": ("Polly", "Polly"),
    "HtmlDocument": ("HtmlAgilityPack", "HtmlAgilityPack"),
    "CsvReader": ("CsvHelper", "CsvHelper"),
    "CsvWriter": ("CsvHelper", "CsvHelper"),
    "XLWorkbook": ("ClosedXML", "ClosedXML.Excel"),
    "Mock": ("Moq", "Moq"),
    "It": ("Moq", "Moq"),
    "Substitute": ("NSubstitute", "NSubstitute"),
    "Fact": ("xunit", "Xunit"),
    "FactAttribute": ("xunit", "Xunit"),
    "Theory": ("xunit", "Xunit"),
    "TestFixture": ("NUnit", "NUnit.Framework"),
    "TestClass": ("MSTest.TestFramework", "Microsoft.VisualStudio.TestTools.UnitTesting"),
    "Dapper": ("Dapper", "Dapper"),
    "SqlMapper": ("Dapper", "Dapper"),
    "Faker": ("Bogus", "Bogus"),
    "Image": ("SixLabors.ImageSharp", "SixLabors.ImageSharp"),
    "ObservableObject": ("CommunityToolkit.Mvvm", "CommunityToolkit.Mvvm.ComponentModel"),
    "RelayCommand": ("CommunityToolkit.Mvvm", "CommunityToolkit.Mvvm.Input"),
    "ObservablePropertyAttribute": ("CommunityToolkit.Mvvm", "CommunityToolkit.Mvvm.ComponentModel"),
    "IHost": ("Microsoft.Extensions.Hosting", "Microsoft.Extensions.Hosting"),
    "Host": ("Microsoft.Extensions.Hosting", "Microsoft.Extensions.Hosting"),
    "ServiceCollection": ("Microsoft.Extensions.DependencyInjection", "Microsoft.Extensions.DependencyInjection"),
    "IConfiguration": ("Microsoft.Extensions.Configuration.Abstractions", "Microsoft.Extensions.Configuration"),
    "ConfigurationBuilder": ("Microsoft.Extensions.Configuration", "Microsoft.Extensions.Configuration"),
    "ILogger": ("Microsoft.Extensions.Logging.Abstractions", "Microsoft.Extensions.Logging"),
    "ILoggerFactory": ("Microsoft.Extensions.Logging", "Microsoft.Extensions.Logging"),
    "YamlDotNet": ("YamlDotNet", "YamlDotNet.Serialization"),
    "Deserializer": ("YamlDotNet", "YamlDotNet.Serialization"),
    "MessagePackSerializer": ("MessagePack", "MessagePack"),
    "ProtoContract": ("protobuf-net", "ProtoBuf"),
}

# implicit global usings of the SDKs (ImplicitUsings=enable)
IMPLICIT = {
    "Microsoft.NET.Sdk": ["System", "System.Collections.Generic", "System.IO", "System.Linq", "System.Net.Http",
                          "System.Threading", "System.Threading.Tasks"],
    "Microsoft.NET.Sdk.Web": ["System.Net.Http.Json", "Microsoft.AspNetCore.Builder", "Microsoft.AspNetCore.Hosting",
                              "Microsoft.AspNetCore.Http", "Microsoft.AspNetCore.Routing",
                              "Microsoft.Extensions.Configuration", "Microsoft.Extensions.DependencyInjection",
                              "Microsoft.Extensions.Hosting", "Microsoft.Extensions.Logging"],
    "Microsoft.NET.Sdk.Worker": ["Microsoft.Extensions.Configuration", "Microsoft.Extensions.DependencyInjection",
                                 "Microsoft.Extensions.Hosting", "Microsoft.Extensions.Logging"],
    "WindowsForms": ["System.Drawing", "System.Windows.Forms"],
}

_TYPE_DECL = re.compile(r"\b(?:class|struct|interface|enum|record(?:\s+(?:class|struct))?|delegate\s+[\w<>\[\],.?\s]+?)"
                        r"\s+(\w+)")
_NS_DECL = re.compile(r"^\s*namespace\s+([\w.]+)", re.M)
_USING = re.compile(r"^\s*(?:global\s+)?using\s+(?!static\b)(?!\w+\s*=)([\w.]+)\s*;", re.M)
_IMPORTS = re.compile(r"^\s*Imports\s+([\w.]+)\s*$", re.M | re.I)
_INDEX: dict[str, metadata.TypeIndex] = {}


@dataclass
class Fix:
    kind: str                      # using | qualify | project | package | search
    title: str
    namespace: str = ""
    type_name: str = ""
    package: str = ""
    project: str = ""              # project file to reference
    extra: dict = field(default_factory=dict)


def index_for(project: Path | None) -> metadata.TypeIndex:
    key = str(project or "").lower()
    idx = _INDEX.get(key)
    if idx is None:
        idx = metadata.project_index(project)
        _INDEX[key] = idx
    return idx


def file_usings(text: str, path: Path | None = None, project: Path | None = None) -> set[str]:
    """Namespaces visible in a file: its usings / Imports, the project's global usings, implicit usings and the
    file's own namespace (and its parents)."""
    found = set(_USING.findall(text)) | set(_IMPORTS.findall(text))
    for ns in _NS_DECL.findall(text):
        parts = ns.split(".")
        found |= {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    if project is not None:
        ptext = sdk.text(project)
        if re.search(r"<ImplicitUsings>\s*(enable|true)", ptext, re.I):
            m = re.search(r'Sdk="([^"]+)"', ptext)
            sdk_name = m.group(1) if m else "Microsoft.NET.Sdk"
            found |= set(IMPLICIT["Microsoft.NET.Sdk"]) | set(IMPLICIT.get(sdk_name, []))
            if re.search(r"<UseWindowsForms>\s*true", ptext, re.I):
                found |= set(IMPLICIT["WindowsForms"])
        found |= set(re.findall(r'<Using\s+Include="([\w.]+)"\s*/>', ptext))
        for g in (Path(project).parent / "obj").glob("**/*.GlobalUsings.g.cs"):
            found |= set(re.findall(r"global using (?:global::)?([\w.]+);", sdk.text(g)))
            break
    return found


def solution_types(projects: list[Path], exclude: Path | None = None, limit_files: int = 4000) -> dict:
    """{type name: [(namespace, project file)]} declared in the source files of the solution's projects."""
    out: dict[str, list] = {}
    n = 0
    for proj in projects:
        if exclude is not None and Path(proj).resolve() == Path(exclude).resolve():
            continue
        ext = ".vb" if str(proj).lower().endswith(".vbproj") else ".cs"
        for f in Path(proj).parent.rglob(f"*{ext}"):
            if any(part in ("bin", "obj") for part in f.parts):
                continue
            n += 1
            if n > limit_files:
                return out
            text = sdk.text(f)
            nss = _NS_DECL.findall(text)
            ns = nss[0] if nss else ""
            for t in _TYPE_DECL.findall(text):
                out.setdefault(t, []).append((ns, str(proj)))
    return out


def references_project(project: Path, other: Path) -> bool:
    text = sdk.text(project)
    return Path(other).name.lower() in text.lower() and "projectreference" in text.lower()


def fixes_for(word: str, text: str, path: Path, project: Path | None = None,
              solution_projects: list[Path] | None = None, diagnostics: list[str] | None = None) -> list[Fix]:
    """Quick actions for the identifier *word* in *text* (file *path*)."""
    word = (word or "").strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", word) or not word[0].isupper():
        return []
    project = project or sdk.project_for_file(path)
    visible = file_usings(text, path, project)
    vb = Path(path).suffix.lower() == ".vb"
    out: list[Fix] = []
    idx = index_for(project)
    cands = idx.lookup(word) or idx.lookup(word + "Attribute")
    if cands and not any(ns in visible for ns, _a in cands):
        for ns, asm in cands[:6]:
            if not ns:
                continue
            out.append(Fix("using", f"Imports {ns}" if vb else f"using {ns};", ns, word, extra={"assembly": asm}))
        for ns, _asm in cands[:3]:
            if ns:
                out.append(Fix("qualify", f"{ns}.{word}", ns, word))
    if not cands and project is not None:
        sol = [Path(p) for p in (solution_projects or []) if str(p).lower().endswith((".csproj", ".vbproj"))]
        own = solution_types([project]).get(word, [])
        if own:
            for ns, _p in own[:3]:
                if ns and ns not in visible:
                    out.append(Fix("using", f"using {ns};" if not vb else f"Imports {ns}", ns, word))
            return out
        decls = solution_types(sol, exclude=project).get(word, [])
        if decls and all(references_project(project, Path(p)) and (not ns or ns in visible) for ns, p in decls):
            return out                                   # already reachable: nothing to fix
        for ns, proj in decls[:3]:
            pname = Path(proj).stem
            if references_project(project, Path(proj)):
                if ns and ns not in visible:
                    out.append(Fix("using", f"using {ns};" if not vb else f"Imports {ns}", ns, word))
                continue
            title = f"Add reference to '{pname}'" + (f" and '{('Imports ' if vb else 'using ')}{ns}{'' if vb else ';'}'"
                                                      if ns and ns not in visible else "")
            out.append(Fix("project", title, ns if ns not in visible else "", word, project=proj))
    if not cands and word in KNOWN_PACKAGES:
        pkg, ns = KNOWN_PACKAGES[word]
        out.append(Fix("package", f"Install package '{pkg}'" + (f" and add 'using {ns};'" if ns not in visible and not vb
                                                                 else ""), ns if ns not in visible else "", word,
                       package=pkg))
    if not cands:
        out.append(Fix("search", f"Search NuGet.org for '{word}'...", "", word))
    return out


def using_edit(text: str, ns: str, vb: bool = False) -> list:
    """[[l1, c1, l2, c2, new]] inserting the directive in sorted position (System first) of the top block."""
    lines = text.split("\n")
    rx = re.compile(r"^\s*Imports\s+([\w.]+)", re.I) if vb else re.compile(r"^\s*using\s+(?!static\b)([\w.]+)\s*;")
    directive = f"Imports {ns}" if vb else f"using {ns};"
    block = [(i, m.group(1)) for i, ln in enumerate(lines) if (m := rx.match(ln))]
    block = [b for b in block if not re.match(r"^\s*global\s", lines[b[0]])]
    if any(n == ns for _i, n in block):
        return []

    def key(n):
        return (0 if n == "System" or n.startswith("System.") else 1, n.lower())
    if block:
        first_block = []
        for i, n in block:
            if first_block and i != first_block[-1][0] + 1:
                break
            first_block.append((i, n))
        ins = first_block[-1][0] + 1
        for i, n in first_block:
            if key(ns) < key(n):
                ins = i
                break
        indent = re.match(r"^\s*", lines[first_block[0][0]]).group(0)
        return [[ins, 0, ins, 0, indent + directive + "\n"]]
    # no directives yet: after leading comments / #nullable, before the first code line
    ins = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(("//", "#", "/*", "*", "'")) or not s:
            continue
        ins = i
        break
    return [[ins, 0, ins, 0, directive + "\n" + ("\n" if lines and lines[ins].strip() else "")]]


__all__ = ["Fix", "fixes_for", "using_edit", "file_usings", "index_for", "solution_types", "KNOWN_PACKAGES"]
