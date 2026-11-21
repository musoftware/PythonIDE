"""Create a project from a template like Visual Studio 2022 (no Qt here).

Paths follow VS's "Configure your new project" page:

* new solution, "Place solution and project in the same directory" OFF:
  ``<location>/<solution>/<solution>.sln`` + ``<location>/<solution>/<project>/<project>.csproj``
* new solution, the box ON: ``<location>/<project>/<project>.sln`` + ``<location>/<project>/<project>.csproj``
* add to the open solution: ``<location>/<project>/<project>.csproj`` (location defaults to the .sln folder)

CLI templates run ``dotnet new <short name> -lang <C#|VB|F#> -n <name> -o <dir> [--framework ...] [options]``;
RAD IDE's templates are written by ``writers.write``. The project is then listed in the .sln / .slnx
(``radide.foreign.vs_solution`` models: byte-preserving text edits; shared projects without configuration
lines, like VS).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import catalog as C
from . import writers as W

INVALID = re.compile(r'[\\/:*?"<>|]')
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


@dataclass
class NewProjectRequest:
    template: C.TemplateInfo
    name: str
    location: Path
    solution_name: str = ""
    same_dir: bool = False                       # "Place solution and project in the same directory"
    framework: str = ""
    options: dict = field(default_factory=dict)  # template parameter name -> value (str / bool)
    solution: Path | None = None                 # add to this .sln/.slnx (None = create a new solution)
    create_solution: bool = True                 # False: a lone project (File > New > Project without .sln)
    solution_format: str = "sln"                 # sln | slnx


@dataclass
class NewProjectResult:
    project_file: Path | None
    solution_file: Path | None
    log: str = ""


def validate_name(name: str) -> str:
    """'' when *name* is a valid project / solution name, else the message VS shows."""
    n = (name or "").strip()
    if not n:
        return "Project name cannot be empty."
    if INVALID.search(n) or n.endswith(".") or n.startswith(" "):
        return f"Project name '{n}' contains characters that are not allowed: \\ / : * ? \" < > |"
    if n.lower() in RESERVED:
        return f"'{n}' is a reserved name."
    if len(n) > 200:
        return "Project name is too long."
    return ""


def paths_for(req: NewProjectRequest) -> tuple[Path, Path | None]:
    """(project folder, solution file or None) for a request."""
    loc = Path(req.location)
    if req.template.kind == "solution":
        sname = req.solution_name or req.name
        sf = loc / sname / f"{sname}.{req.solution_format}"
        return sf.parent, sf
    if req.solution is not None:
        return loc / req.name, Path(req.solution)
    if not req.create_solution:
        return loc / req.name, None
    if req.same_dir:
        d = loc / req.name
        return d, d / f"{req.name}.{req.solution_format}"
    sname = req.solution_name or req.name
    return loc / sname / req.name, loc / sname / f"{sname}.{req.solution_format}"


def cli_argv(req: NewProjectRequest, out: Path) -> list[str]:
    t = req.template
    argv = ["new", t.short_name, "-n", req.name, "-o", str(out)]
    if t.language:
        argv += ["-lang", t.language]
    fwp = t.framework_param
    if req.framework and fwp is not None:
        argv += [fwp.option or "--framework", req.framework]
    for p in t.params:
        if p is fwp or p.name not in req.options:
            continue
        v = req.options[p.name]
        if p.kind == "bool":
            b = v if isinstance(v, bool) else str(v).lower() == "true"
            if b != (str(p.default).lower() == "true"):
                argv += [p.option or f"--{p.name}", "true" if b else "false"]
        elif v not in (None, "") and str(v) != str(p.default):
            argv += [p.option or f"--{p.name}", str(v)]
    return argv


def _new_solution(sf: Path, log: list[str]) -> Path:
    sf.parent.mkdir(parents=True, exist_ok=True)
    if sf.is_file():
        return sf
    code, out = C.run_dotnet(["new", "sln", "-n", sf.stem, "-o", str(sf.parent)]
                             + (["--format", sf.suffix.lstrip(".")] if sf.suffix.lower() == ".slnx" else []),
                             cwd=sf.parent)
    log.append(out.strip())
    hit = sf if sf.is_file() else next(iter(sorted(sf.parent.glob(f"{sf.stem}.sln*"))), None)
    if code != 0 or hit is None:                 # no SDK: write the empty solution VS writes
        sf.write_bytes(_EMPTY_SLN.replace("\n", "\r\n").encode("utf-8-sig"))
        hit = sf
    return hit


_EMPTY_SLN = """
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
EndGlobal
"""


def add_to_solution(sf: Path, project_file: Path) -> None:
    from ...foreign.vs_solution import load_solution_model
    model = load_solution_model(sf)
    if project_file.suffix.lower() == ".shproj":
        from ..shared.model import SharedProject, add_to_solution as add_shared
        add_shared(model, SharedProject(project_file))
        return
    have = {(model.folder / e.path).resolve() for e in model.entries}
    if project_file.resolve() in have:
        return
    if not model.configs and model.path.suffix.lower() == ".sln":
        _ensure_configs(model)
    model.add_project(project_file)
    model.save()


def _ensure_configs(model) -> None:
    """`dotnet new sln` writes no configuration section: add VS's Debug/Release | Any CPU."""
    text, nl = model.file.text, model.file.newline
    g = re.search(r"^Global[ \t]*\r?\n", text, re.M)
    if g is None:
        text = text.rstrip() + nl + "Global" + nl + "EndGlobal" + nl
        g = re.search(r"^Global[ \t]*\r?\n", text, re.M)
    block = (f"\tGlobalSection(SolutionConfigurationPlatforms) = preSolution{nl}\t\tDebug|Any CPU = Debug|Any CPU{nl}"
             f"\t\tRelease|Any CPU = Release|Any CPU{nl}\tEndGlobalSection{nl}")
    model.file.text = text[:g.end()] + block + text[g.end():]
    model.parse()


def create(req: NewProjectRequest, log=None) -> NewProjectResult:
    """Create the project (and the solution). Raises ValueError with VS's message on bad input."""
    msgs: list[str] = []
    say = log or (lambda s: None)
    t = req.template
    if t.kind == "solution":
        err = validate_name(req.solution_name or req.name)
        if err:
            raise ValueError(err.replace("Project", "Solution"))
        _d, sf = paths_for(req)
        if sf.exists():
            raise ValueError(f"The solution '{sf}' already exists.")
        sf = _new_solution(sf, msgs)
        say("\n".join(m for m in msgs if m))
        return NewProjectResult(None, sf, "\n".join(msgs))
    err = validate_name(req.name)
    if err:
        raise ValueError(err)
    pdir, sf = paths_for(req)
    if pdir.exists() and any(pdir.glob(f"{req.name}.*proj")):
        raise ValueError(f"The project '{pdir / req.name}' already exists.")
    if pdir.exists() and req.solution is None and not req.same_dir and any(pdir.iterdir()):
        raise ValueError(f"The directory '{pdir}' is not empty.")
    if sf is not None and req.solution is None and sf.exists():
        raise ValueError(f"The solution '{sf}' already exists.")
    if t.source == "rad":
        pf = W.write(t.key, pdir, req.name, req.framework)
        msgs.append(f"The template \"{t.name}\" was created successfully (RAD IDE).")
    else:
        pdir.parent.mkdir(parents=True, exist_ok=True)
        argv = cli_argv(req, pdir)
        msgs.append("> dotnet " + " ".join(f'"{a}"' if " " in a else a for a in argv))
        code, out = C.run_dotnet(argv, cwd=pdir.parent, timeout=600)
        msgs.append(out.strip())
        pf = next(iter(sorted(pdir.glob(f"{req.name}.*proj"))), None) if pdir.exists() else None
        if pf is None and pdir.exists():
            pf = next(iter(sorted(pdir.glob("*.*proj"))), None)
        if code != 0 or pf is None:
            say("\n".join(m for m in msgs if m))
            raise ValueError(f"dotnet new {t.short_name} failed:\n{out.strip()[-1500:]}")
    if sf is not None:
        if req.solution is None:
            sf = _new_solution(sf, msgs)
        add_to_solution(sf, pf)
        msgs.append(f"Added {pf.name} to {sf.name}")
    say("\n".join(m for m in msgs if m))
    return NewProjectResult(pf, sf, "\n".join(msgs))


__all__ = ["NewProjectRequest", "NewProjectResult", "validate_name", "paths_for", "cli_argv", "create",
           "add_to_solution"]
