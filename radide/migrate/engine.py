"""Migration engine: read a foreign project, preview the mapping, write the migrated project + report.

    src = load_source(path)                       # .vbp/.frm, .sln/.csproj/.vbproj, .dpr/.lpi, .ui, folder
    rows = plan(src, "python-tk")                 # preview: forms, controls, handlers, unsupported items
    res = migrate(src, Options("python-tk", dest), progress=print)
    res.project_file / res.report_path / res.notes

Targets: "keep" (same language as a RAD IDE project), any language plugin id (python-tk, python-qt, vb-basic,
csharp-bridge, ...) and "vbnet" (a Visual Studio VB.NET WinForms project, buildable with ``dotnet build``).

Other foreign adapters can feed the wizard: register_format(..., migrate_source=callable(path) ->
MigrationSource) in radide.features.foreign_projects.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..controls import CONTROL_TYPES, event_args
from ..model import Form, Project
from .vbcommon import FormInfo, Notes, ProjectContext, proc_ranges, read_text

RUNTIME = Path(__file__).with_name("runtime")
REPORT = "MIGRATION_REPORT.md"
SKIP_DIRS = {"bin", "obj", ".vs", ".git", "node_modules", "_original", ".radide", "__pycache__"}


# ============================================================================ source model
@dataclass
class SourceForm:
    name: str
    form: Form
    file: Path                                   # file with the form definition (.frm, .Designer.cs, .dfm ...)
    code_file: Path | None = None                # file with the event code
    code: str = ""                               # text of code_file
    # neutral handler (Button1_Click / Form1_Load) -> (method name, original source of the method, line)
    handlers: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@dataclass
class MigrationSource:
    kind: str                  # vb6 | winforms-cs | winforms-vb | delphi | lazarus | qt-ui | foreign
    language: str              # vb6 | csharp | vbnet | pascal | none
    name: str
    path: Path
    folder: Path
    forms: list = field(default_factory=list)            # [SourceForm]
    modules: list = field(default_factory=list)          # [(name, Path, kind)] kind: bas | cls | cs | vb | pas
    startup: str = ""
    notes: Notes = field(default_factory=Notes)
    extra: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return {"vb6": "Visual Basic 6 project", "winforms-cs": "Windows Forms (C#) project",
                "winforms-vb": "Windows Forms (VB.NET) project", "delphi": "Delphi project",
                "lazarus": "Lazarus project", "qt-ui": "Qt Designer form"}.get(self.kind, self.kind)

    def files(self) -> list[Path]:
        out = [self.path] if self.path.is_file() else []
        for f in self.forms:
            for p in (f.file, f.code_file, *(f.extra.get("files") or [])):
                if p and Path(p) not in out:
                    out.append(Path(p))
        for _n, p, _k in self.modules:
            if p not in out:
                out.append(p)
        return out


@dataclass
class Options:
    target: str                      # "keep" | plugin id | "vbnet"
    dest: Path
    mode: str = "copy"               # copy | inplace
    code: str = "rules"              # rules | rules+ai | comments
    keep_original: bool = True


@dataclass
class MigrationResult:
    ok: bool
    folder: Path
    project_file: Path | None
    report_path: Path | None
    report: str
    notes: Notes
    target: str
    stats: dict = field(default_factory=dict)


class MigrationError(Exception):
    pass


# ============================================================================ loading
def detect(path) -> Path | None:
    """The project file to migrate for a file or folder (None when nothing is recognised)."""
    p = Path(path)
    if p.is_file():
        return p
    if not p.is_dir():
        return None
    for pat in ("*.vbp", "*.sln", "*.slnx", "*.csproj", "*.vbproj", "*.dproj", "*.dpr", "*.lpi", "*.pro"):
        hits = sorted(p.glob(pat))
        if hits:
            return hits[0]
    frm = sorted(p.glob("*.frm"))
    if frm:
        return frm[0]
    try:
        from ..features import foreign_projects as fp
        hit = fp.probe_folder(p)
        if hit:
            return hit[1]
    except Exception:  # noqa: BLE001
        pass
    return None


def supported_patterns() -> list[tuple[str, str]]:
    """(description, glob patterns) of the sources the wizard can read."""
    out = [("Visual Basic 6 project", "*.vbp *.frm"), ("Visual Studio solution / project", "*.sln *.csproj *.vbproj"),
           ("Delphi / Lazarus project", "*.dproj *.dpr *.lpi *.lpr"), ("Qt Designer form", "*.ui")]
    try:
        from ..features import foreign_projects as fp
        for f in fp.formats():
            if f.extra.get("migrate_source"):
                out.append((f.description, " ".join(("*" + e) if e.startswith(".") else e for e in f.extensions)))
    except Exception:  # noqa: BLE001
        pass
    return out


def load_source(path) -> MigrationSource:
    p = detect(path)
    if p is None:
        raise MigrationError(f"No project found in {path}")
    ext = p.suffix.lower()
    # adapters registered by other modules (radide.features.foreign_projects)
    try:
        from ..features import foreign_projects as fp
        fmt = fp.find_format(p)
        hook = fmt.extra.get("migrate_source") if fmt is not None else None
        if callable(hook) and ext not in (".vbp", ".frm", ".sln", ".csproj", ".vbproj"):
            src = hook(p)
            if src is not None:
                return src
    except Exception:  # noqa: BLE001 - fall back to the built-in readers
        pass
    if ext in (".vbp", ".frm"):
        return load_vb6(p)
    if ext in (".sln", ".slnx"):
        return load_sln(p)
    if ext == ".csproj":
        return load_csproj(p)
    if ext == ".vbproj":
        return load_vbproj(p)
    if ext in (".dproj", ".dpr", ".lpi", ".lpr", ".dfm", ".lfm"):
        return load_pascal(p)
    if ext in (".ui", ".pyproject", ".pro"):
        return load_qt_ui(p)
    raise MigrationError(f"{p.name}: this kind of project cannot be migrated yet "
                         "(it can still be opened in place with File > Open Project)")


# ---------------------------------------------------------------------------- VB6
def load_vb6(path: Path) -> MigrationSource:
    from ..importers.python_import import ImportReport
    from ..importers.vb6_import import _FrmConverter, parse_frm, parse_vbp
    if path.suffix.lower() == ".vbp":
        info = parse_vbp(path)
    else:
        info = {"forms": [path.name], "modules": [], "classes": [], "objects": [], "startup": "", "name": path.stem}
    base = path.parent
    src = MigrationSource("vb6", "vb6", re.sub(r"\W", "_", info["name"]) or "VB6Project", path, base)
    for obj in info["objects"]:
        src.notes.add("info", path.name, 0, f"references the ActiveX library {obj}")
    ctx = ProjectContext()
    for rel in info["forms"]:
        fp = (base / rel.replace("\\", "/")).resolve()
        if not fp.exists():
            src.notes.add("manual", path.name, 0, f"form file not found: {rel}")
            continue
        text = read_text(fp)
        root, _code = parse_frm(text)
        if root is None:
            src.notes.add("manual", fp.name, 0, "no form definition found")
            continue
        rep = ImportReport()
        form = _FrmConverter(rep, fp.name).convert(root)
        for w in rep.warnings:
            src.notes.add("approx" if "approximation" in w else "manual", fp.name, 0, w)
        sf = SourceForm(form.name, form, fp, fp, text)
        frx = fp.with_suffix(".frx")
        if frx.exists():
            sf.extra["files"] = [frx]
        for a, b, name in proc_ranges(text):
            lines = text.replace("\r\n", "\n").split("\n")[a - 1:b]
            ctrl, _, ev = name.rpartition("_")
            sf.extra.setdefault("procs", {})[name] = ("\n".join(lines), a)
        src.forms.append(sf)
        ctx.forms[form.name.lower()] = FormInfo.of(form, fp.name)
    for kind, key in (("bas", "modules"), ("cls", "classes")):
        for rel in info[key]:
            fp = (base / rel.replace("\\", "/")).resolve()
            if not fp.exists():
                src.notes.add("manual", path.name, 0, f"{'module' if kind == 'bas' else 'class'} file not found: {rel}")
                continue
            src.modules.append((fp.stem, fp, kind))
    st = info.get("startup") or ""
    names = {f.name.lower(): f.name for f in src.forms}
    src.startup = names.get(st.lower(), "") if st.lower() != "sub main" else "Sub Main"
    if not src.startup and src.forms:
        src.startup = src.forms[0].name
    if path.suffix.lower() == ".vbp":
        m = re.search(r'^\s*Title\s*=\s*"([^"]*)"', read_text(path), re.I | re.M)
        info["title"] = m.group(1) if m else info["name"]
    src.extra["vbp"] = info
    return src


def vb6_context(src: MigrationSource) -> ProjectContext:
    ctx = ProjectContext()
    for sf in src.forms:
        ctx.forms[sf.name.lower()] = FormInfo.of(sf.form, sf.file.name)
    for name, p, kind in src.modules:
        ctx.add_module(name if kind == "bas" else _vb_name(p) or name, kind, read_text(p), p.name)
    for sf in src.forms:
        from .vb6_to_python import code_part
        ctx.add_module(sf.name, "frm", code_part(sf.code), sf.file.name)
    vbp = src.extra.get("vbp") or {}
    ctx.title = vbp.get("title") or vbp.get("name") or src.name
    return ctx


def _vb_name(p: Path) -> str:
    m = re.search(r'^\s*Attribute\s+VB_Name\s*=\s*"([^"]+)"', read_text(p), re.I | re.M)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------- .NET
def _project_files(folder: Path, ext: str) -> list[Path]:
    out = []
    for f in sorted(folder.rglob(f"*{ext}")):
        if any(part.lower() in SKIP_DIRS for part in f.relative_to(folder).parts[:-1]):
            continue
        out.append(f)
    return out


def load_sln(path: Path) -> MigrationSource:
    text = read_text(path)
    projs = re.findall(r'Project\("\{[^}]+\}"\)\s*=\s*"([^"]+)",\s*"([^"]+\.(?:cs|vb)proj)"', text, re.I)
    if path.suffix.lower() == ".slnx":
        projs = [(Path(p).stem, p) for p in re.findall(r'Path="([^"]+\.(?:cs|vb)proj)"', text, re.I)]
    if not projs:
        raise MigrationError(f"{path.name}: no C# / VB.NET project in the solution")
    best, others = None, []
    for name, rel in projs:
        p = (path.parent / rel.replace("\\", "/")).resolve()
        if not p.exists():
            continue
        try:
            s = load_csproj(p) if p.suffix.lower() == ".csproj" else load_vbproj(p)
        except MigrationError:
            continue
        if best is None and s.forms:
            best = s
        else:
            others.append(name)
    if best is None:
        raise MigrationError(f"{path.name}: no Windows Forms project with forms in the solution")
    if others:
        best.notes.add("info", path.name, 0, "the solution has other projects (migrate them one by one): " +
                       ", ".join(others))
    best.extra["solution"] = path
    return best


def load_csproj(path: Path) -> MigrationSource:
    from ..importers.exe import dotnet
    from .cs_qt import rewrite_tryparse
    folder = path.parent
    src = MigrationSource("winforms-cs", "csharp", path.stem, path, folder)
    classes, startup = [], ""
    for f in _project_files(folder, ".cs"):
        text = read_text(f)
        m = re.search(r"Application\.Run\s*\(\s*new\s+([\w.]+)\s*\(", text)
        if m:
            startup = m.group(1).split(".")[-1]
        classes += dotnet.find_classes(text, f)
    merged: dict = {}
    files: dict = {}
    for c in classes:
        files.setdefault(c.name, []).append(c.file)
        if c.name in merged:
            merged[c.name].body += "\n" + c.body
            merged[c.name].base = merged[c.name].base or c.base
        else:
            merged[c.name] = dotnet.WinFormsClass(c.name, c.base, c.body, c.file)
    form_classes = [c for c in merged.values() if re.search(r"\bvoid\s+InitializeComponent\s*\(", c.body) and
                    (c.base.split(".")[-1] in ("Form", "UserControl") or "Controls.Add" in c.body or
                     "ClientSize" in c.body)]
    all_forms = {c.name for c in form_classes}
    if not form_classes:
        if re.search(r"<UseWPF>\s*true", read_text(path), re.I):
            raise MigrationError(f"{path.name} is a WPF project - its XAML windows cannot be migrated yet "
                                 "(open it in place with File > Open Project)")
        raise MigrationError(f"{path.name}: no Windows Forms form found")
    for c in form_classes:
        c.body, n_tp = rewrite_tryparse(c.body)
        try:
            parsed = dotnet.parse_winforms(c, all_forms)
        except Exception as e:  # noqa: BLE001
            src.notes.add("manual", Path(c.file).name if c.file else c.name, 0,
                          f"{c.name}: InitializeComponent could not be read ({e})")
            continue
        if parsed is None:
            continue
        form_dict, wiring, notes = parsed
        form = Form.from_dict(form_dict)
        code_file = next((f for f in files.get(c.name, []) if f and not f.name.lower().endswith(".designer.cs")),
                         c.file)
        designer = next((f for f in files.get(c.name, []) if f and f.name.lower().endswith(".designer.cs")), c.file)
        sf = SourceForm(c.name, form, designer, code_file, read_text(code_file) if code_file else "")
        sf.extra.update(cls=c, wiring=wiring, all_forms=all_forms, files=[f for f in files.get(c.name, []) if f])
        resx = Path(code_file).with_suffix(".resx") if code_file else None
        if resx and resx.exists():
            sf.extra["files"].append(resx)
        methods = {m["name"]: m for m in dotnet.class_methods(c.body)}
        for h, meth in wiring.items():
            if isinstance(meth, str) and meth in methods:
                m = methods[meth]
                sf.handlers[h] = (meth, m["header"] + " {" + m["body"] + "}", _line_of(sf.code, m["header"]))
        for n in notes:
            src.notes.add("approx", designer.name, 0, n)
        src.forms.append(sf)
    others = [c for c in merged.values() if c not in form_classes and c.name not in
              ("Program", "Resources", "Settings", "ApplicationConfiguration")]
    for c in others:
        if c.file:
            src.modules.append((c.name, Path(c.file), "cs"))
    src.startup = startup if startup in all_forms else (src.forms[0].name if src.forms else "")
    return src


def _line_of(text: str, snippet: str) -> int:
    i = text.find(snippet.strip().split("(")[0]) if snippet else -1
    return text.count("\n", 0, i) + 1 if i >= 0 else 0


def load_vbproj(path: Path) -> MigrationSource:
    from .vbnet import load_vb_form, parse_vb_classes
    folder = path.parent
    src = MigrationSource("winforms-vb", "vbnet", path.stem, path, folder)
    startup = ""
    proj = read_text(path)
    m = re.search(r"<StartupObject>([^<]+)</StartupObject>", proj)
    myapp = folder / "My Project" / "Application.myapp"
    if myapp.exists():
        m2 = re.search(r"<MainForm>([^<]+)</MainForm>", read_text(myapp))
        if m2:
            startup = m2.group(1).split(".")[-1]
    if m and not startup and m.group(1).strip().lower() != "sub main":
        startup = m.group(1).split(".")[-1]
    for f in _project_files(folder, ".vb"):
        if f.name.lower().endswith(".designer.vb"):
            continue
        text = read_text(f)
        mm = re.search(r"Application\.Run\s*\(\s*New\s+([\w.]+)", text, re.I)
        if mm and not startup:
            startup = mm.group(1).split(".")[-1]
        designer = f.with_name(f.stem + ".Designer.vb")
        if not designer.exists():
            for c in parse_vb_classes(text, f.name):
                if c.name.lower() not in ("program",) and not re.search(r"^\s*(?:Friend\s+|Public\s+)?Module\s+Program",
                                                                        text, re.I | re.M):
                    src.modules.append((c.name, f, "vb"))
                    break
            continue
        cls, form_dict, wiring, notes = load_vb_form(f, designer)
        if cls is None or form_dict is None:
            src.notes.add("manual", f.name, 0, "; ".join(notes) or "not a form")
            continue
        form = Form.from_dict(form_dict)
        sf = SourceForm(cls.name, form, designer, f, text)
        sf.extra.update(vbclass=cls, wiring=wiring, files=[f, designer])
        resx = f.with_suffix(".resx")
        if resx.exists():
            sf.extra["files"].append(resx)
        for meth in cls.methods:
            for h, mname in wiring.items():
                if mname == meth.name:
                    sf.handlers[h] = (meth.name, "\n".join(t for _l, t in meth.body), meth.line)
        for n in notes:
            src.notes.add("approx", f.name, 0, n)
        src.forms.append(sf)
    if not src.forms:
        raise MigrationError(f"{path.name}: no Windows Forms form found")
    names = {f.name.lower(): f.name for f in src.forms}
    src.startup = names.get(startup.lower(), src.forms[0].name)
    return src


# ---------------------------------------------------------------------------- Delphi / Lazarus / Qt
def load_pascal(path: Path) -> MigrationSource:
    from ..foreign import delphi, pascal_forms as pf
    if path.suffix.lower() in (".dfm", ".lfm"):
        units = [(path.stem, path.with_suffix(".pas"), path)]
        kind, name, folder = ("lazarus" if path.suffix.lower() == ".lfm" else "delphi"), path.stem, path.parent
        main_form = ""
    else:
        info = delphi.load_project_info(path)
        units = [(u.form_name or u.pas.stem, u.pas, u.form_file) for u in info.units if u.form_file]
        kind, name, folder, main_form = info.kind, info.name, info.file.parent, info.main_form
    src = MigrationSource(kind, "pascal", re.sub(r"\W", "_", name), path, folder)
    for fname, pas, ffile in units:
        data = Path(ffile).read_bytes()
        text = pf.binary_dfm_to_text(data) if pf.is_binary_dfm(data) else data.decode("utf-8", errors="replace")
        form, linfo = pf.dfm_to_form(pf.parse_dfm(text), kind == "lazarus")
        code = read_text(pas) if pas and Path(pas).exists() else ""
        sf = SourceForm(form.name, form, Path(ffile), Path(pas) if pas else None, code)
        sf.extra["files"] = [p for p in (Path(ffile), Path(pas) if pas else None) if p]
        for comp, evs in (linfo.events or {}).items():
            for neutral, handler in evs.items():
                owner = comp or form.name
                body, line = _pascal_method(code, handler)
                sf.handlers[f"{owner}_{neutral}"] = (handler, body, line)
        for comp, cls in (linfo.unknown or {}).items():
            src.notes.add("manual", Path(ffile).name, 0, f"component {comp} ({cls}) has no RAD IDE equivalent")
        src.forms.append(sf)
    if not src.forms:
        raise MigrationError(f"{path.name}: no form found")
    names = {f.name.lower(): f.name for f in src.forms}
    src.startup = names.get((main_form or "").lower(), src.forms[0].name)
    return src


def _pascal_method(code: str, name: str) -> tuple[str, int]:
    m = re.search(rf"^\s*procedure\s+\w+\.{re.escape(name)}\b.*?^\s*end;", code, re.I | re.M | re.S)
    if not m:
        return "", 0
    return m.group(0).strip("\n"), code.count("\n", 0, m.start()) + 1


def load_qt_ui(path: Path) -> MigrationSource:
    """A Qt Designer .ui form, or every .ui of a Qt / PySide project (.pyproject, .pro)."""
    from ..foreign import qt_ui
    uis = [path] if path.suffix.lower() == ".ui" else sorted(path.parent.rglob("*.ui"))
    uis = [u for u in uis if not any(p.lower() in SKIP_DIRS for p in u.relative_to(path.parent).parts[:-1])]
    if not uis:
        raise MigrationError(f"{path.name}: no Qt Designer .ui form found")
    src = MigrationSource("qt-ui", "none", path.stem, path, path.parent)
    used = set()
    for ui in uis:
        form, _ctx = qt_ui.read_ui(ui, live=False)
        name = _ident(form.props.get("Name") or ui.stem, "Form")
        while name.lower() in used:
            name += "_"
        used.add(name.lower())
        form.props["Name"] = name
        src.forms.append(SourceForm(name, form, ui, None, "", extra={"files": [ui]}))
        src.notes.add("info", ui.name, 0, "a Qt Designer form has no event code - the form is migrated; the "
                                          "project's Python/C++ code stays in _original for reference")
    for f in sorted(path.parent.glob("*.py")) + sorted(path.parent.glob("*.cpp")):
        src.modules.append((f.stem, f, "py" if f.suffix == ".py" else "cpp"))
    src.startup = src.forms[0].name
    return src


# ============================================================================ targets & preview
def targets_for(src: MigrationSource) -> list[tuple[str, str, str]]:
    """(target id, label, how the code is converted)."""
    from ..languages import all_plugins
    rules = {"vb6": {"python-tk", "python-qt", "vb-basic", "vbnet"},
             "csharp": {"python-tk", "python-qt"},
             "vbnet": {"python-tk", "python-qt", "vb-basic"}}.get(src.language, set())
    out = [("keep", f"Keep the language - {keep_target(src)[1]}", "exact" if src.language == "vb6" else "rules")]
    preferred = ["python-tk", "python-qt", "vb-basic", "csharp-bridge"]
    if src.language == "vb6":
        preferred.insert(3, "vbnet")
    labels = {p.id: p.display_name for p in all_plugins()}
    labels["vbnet"] = "VB.NET Windows Forms (Visual Studio project, .vbproj)"
    for pid in preferred:
        if pid in labels:
            out.append((pid, labels[pid], "rules" if pid in rules else "comments + AI"))
    for p in all_plugins():
        if p.id in preferred or not getattr(p, "new_code", None):
            continue
        if getattr(p, "kind", "") in ("website",) or p.id.endswith("-web") or p.id in ("static-web", "python-django",
                                                                                       "python-flask",
                                                                                       "python-fastapi"):
            continue
        out.append((p.id, p.display_name, "comments + AI"))
    return out


def keep_target(src: MigrationSource) -> tuple[str, str]:
    return {"vb6": ("vb-basic", "Visual Basic 6 (BASIC) - the VB6 code runs as it is"),
            "csharp": ("csharp-bridge", "C# (GUI Bridge, .NET)"),
            "vbnet": ("vb-basic", "Visual Basic (BASIC) - VB.NET code rewritten as VB6"),
            "pascal": ("python-tk", "Pascal is not a RAD IDE language - forms to Python (Tkinter)")}.get(
        src.language, ("python-tk", "Python (Tkinter)"))


def resolve_target(src: MigrationSource, target: str) -> str:
    return keep_target(src)[0] if target == "keep" else target


@dataclass
class PlanRow:
    section: str       # Forms | Controls | Events | Modules | Notes
    item: str
    mapping: str
    status: str        # exact | rules | approx | ai | manual | info


def plan(src: MigrationSource, target: str) -> list[PlanRow]:
    target = resolve_target(src, target)
    rows: list[PlanRow] = []
    code_how = "rules" if target in {"vb6": {"python-tk", "python-qt", "vb-basic", "vbnet"},
                                     "csharp": {"python-tk", "python-qt", "csharp-bridge"},
                                     "vbnet": {"python-tk", "python-qt", "vb-basic"}}.get(src.language, set()) \
        else "manual"
    for sf in src.forms:
        f = sf.form
        rows.append(PlanRow("Forms", sf.name, f"{sf.file.name} -> {sf.name}.form "
                                              f"({f.props.get('Width')}x{f.props.get('Height')}, "
                                              f"{len(f.controls)} controls){' [startup]' if sf.name == src.startup else ''}",
                            "exact"))
        for c in f.controls:
            arr = c.props.get("ArrayName")
            rows.append(PlanRow("Controls", f"{sf.name}.{c.name}",
                                f"{c.type}{' (control array ' + str(arr) + ')' if arr else ''}",
                                "exact" if c.type != "ActiveX" else "manual"))
        handlers = sf.handlers or {k: v for k, v in (sf.extra.get("procs") or {}).items()}
        for h in handlers:
            rows.append(PlanRow("Code", f"{sf.name}.{h}", f"code -> {target}",
                                "exact" if (src.language == "vb6" and target == "vb-basic") else code_how))
    for name, p, kind in src.modules:
        rows.append(PlanRow("Modules", name, f"{p.name} ({kind}) -> {target}",
                            "exact" if (src.language == "vb6" and target == "vb-basic") else
                            code_how if kind in ("bas", "cls", "vb") else "manual"))
    for n in src.notes.items:
        rows.append(PlanRow("Notes", n.where(), n.text, n.level))
    return rows


# ============================================================================ migrate
def migrate(src: MigrationSource, opts: Options, progress=None) -> MigrationResult:
    progress = progress or (lambda _s: None)
    target = resolve_target(src, opts.target)
    dest = Path(opts.dest)
    if opts.mode == "inplace":
        dest = src.folder
    notes = Notes()
    notes.extend(src.notes)
    stats = {"forms": 0, "controls": 0, "handlers": 0, "modules": 0}
    if opts.mode != "inplace":
        if dest.exists() and any(dest.iterdir()):
            raise MigrationError(f"The folder {dest} is not empty - choose a new folder")
        dest.mkdir(parents=True, exist_ok=True)
    started = time.time()
    progress(f"Migrating {src.label} '{src.name}' to {target} ...")
    if target == "vbnet":
        from .vb6_to_vbnet import write_vbnet_project
        if src.language != "vb6":
            raise MigrationError("VB.NET output is available for VB6 projects")
        if opts.mode == "inplace":
            _check_inplace(dest, [REPORT, "Program.vb", f"{_ident(src.name, 'Project')}.vbproj"] +
                           [f"{sf.name}{x}" for sf in src.forms for x in (".vb", ".Designer.vb")] +
                           [f"{n}.vb" for n, _p, _k in src.modules])
        project_file = write_vbnet_project(src, dest, notes, stats, progress, opts)
    else:
        planned = _planned_files(src, target)
        if opts.mode == "inplace":
            _check_inplace(dest, planned)
        project_file = _write_rad_project(src, target, dest, notes, stats, progress, opts)
    if opts.keep_original and opts.mode != "inplace":
        _copy_original(src, dest / "_original", progress)
        notes.add("exact", "_original", 0, "the original project files were copied to _original/ for reference")
    report = report_markdown(src, target, dest, project_file, notes, stats, time.time() - started, opts)
    rp = dest / REPORT
    rp.write_text(report, encoding="utf-8")
    progress("Done.")
    return MigrationResult(True, dest, project_file, rp, report, notes, target, stats)


def _write_form(form: Form, path: Path) -> None:
    """Write the neutral .form JSON (never through model.FORM_STORES: a foreign-project store could take
    the path for a native form file of the original project and overwrite it)."""
    Path(path).write_text(json.dumps(form.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def _check_inplace(dest: Path, planned: list[str]) -> None:
    clash = [n for n in planned if (dest / n).exists()]
    if clash:
        raise MigrationError("In-place migration would overwrite files of the project: " +
                             ", ".join(clash[:8]) + " - migrate into a new folder instead")
    try:
        from .. import model
        claimed = [n for n in planned if n.endswith(".form") and model._form_store(dest / n) is not None]
    except Exception:  # noqa: BLE001
        claimed = []
    if claimed:
        raise MigrationError("In place, the IDE would take " + ", ".join(claimed[:5]) + " for the native forms of "
                             "the original project (opened in place) - migrate into a new folder instead")


def _planned_files(src: MigrationSource, target: str) -> list[str]:
    from ..languages import get_plugin
    plugin = get_plugin(target)
    out = [Project.FILE, REPORT]
    for sf in src.forms:
        out += [f"{sf.name}.form", plugin.code_file(sf.name), plugin.designer_file(sf.name)]
    for name, _p, _k in src.modules:
        out.append(name + plugin.code_ext)
    return out


def _copy_original(src: MigrationSource, orig: Path, progress) -> None:
    progress("Copying the original files to _original ...")
    orig.mkdir(parents=True, exist_ok=True)
    for f in src.files():
        try:
            rel = f.resolve().relative_to(src.folder.resolve())
        except ValueError:
            rel = Path(f.name)
        (orig / rel).parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(f, orig / rel)
        except OSError:
            pass


def _ident(name: str, fallback: str = "Item") -> str:
    s = re.sub(r"\W", "_", str(name or "")).strip("_")
    return (s if not s[:1].isdigit() else f"{fallback}_{s}") or fallback


def _insert_body(code: str, line: int, body: list[str]) -> str:
    lines = code.splitlines()
    if not (0 <= line < len(lines)):
        return code
    cur = lines[line]
    indent = cur[:len(cur) - len(cur.lstrip())] if cur.strip() else cur
    if not indent:
        prev = lines[line - 1] if line > 0 else ""
        indent = prev[:len(prev) - len(prev.lstrip())] + "    "
    new = [indent + b if b else "" for b in body]
    if cur.strip() in ("pass", ""):
        lines[line:line + 1] = new
    else:
        lines[line:line] = new
    return "\n".join(lines) + "\n"


DATA_EXTS = (".mdb", ".accdb", ".mdw", ".db", ".sqlite", ".sqlite3", ".dbf")


def _copy_data_files(src, dest: Path, notes) -> None:
    """Databases of the VB6 program (App.Path & "/x.mdb", "/data/x.mdb" ...) are copied to the same place."""
    base = src.folder.resolve()
    n = 0
    for f in base.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in DATA_EXTS or f.name.lower() == "thumbs.db":
            continue
        try:
            rel = f.resolve().relative_to(base)
        except ValueError:
            continue
        if len(rel.parts) > 4 or n >= 50:
            continue
        out = dest / rel
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        n += 1
        notes.add("exact", str(rel), 0, f"database {rel} copied next to the program (App.Path)")


def _write_rad_project(src, target, dest, notes, stats, progress, opts) -> Path:
    from ..languages import get_plugin
    plugin = get_plugin(target)
    if src.language == "vb6" and target == "vb-basic":
        return _vb6_keep(src, dest, notes, stats, progress)
    if opts.code == "comments":
        notes.add("info", src.path.name, 0, "event code kept as comments (option 'Keep the original code as "
                                            "comments only')")
    project = Project(dest, _ident(src.name, "Project"), target)
    python = target in ("python-tk", "python-qt")
    toolkit = "qt" if target == "python-qt" else "tk"
    ctx = vb6_context(src) if src.language == "vb6" and python else None
    startup = src.startup if src.startup != "Sub Main" else ""
    if src.startup == "Sub Main":
        startup = _sub_main_form(src, notes) or (src.forms[0].name if src.forms else "")
    for sf in src.forms:
        progress(f"Form {sf.name} ...")
        form = sf.form
        is_startup = sf.name == startup or (not startup and not project.forms)
        code = None
        if opts.code == "comments":
            pass                                   # the original code as comments only (generic writer)
        elif python and src.language == "vb6":
            code = _vb6_form_python(ctx, sf, toolkit, plugin, is_startup, notes)
        elif python and src.language == "csharp":
            code = _cs_form_python(sf, target, plugin, notes, opts, progress)
        elif python and src.language == "vbnet":
            code = _vbnet_form_python(sf, toolkit, plugin, is_startup, notes)
        elif target == "vb-basic" and src.language == "vbnet":
            code = _vbnet_form_vb6(sf, notes)
        elif target == "csharp-bridge" and src.language == "csharp":
            from .cs_bridge import cs_form_to_bridge
            code = cs_form_to_bridge(sf, plugin, is_startup, notes)
        if code is None:
            code = _generic_form_code(src, sf, target, plugin, is_startup, notes, opts, progress)
        elif opts.code == "rules+ai":
            code = _ai_fix(src, sf, target, code, notes, progress)
        _write_form(form, project.form_path(sf.name))
        (dest / plugin.code_file(sf.name)).write_text(code, encoding="utf-8")
        try:
            (dest / plugin.designer_file(sf.name)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            notes.add("manual", f"{sf.name}.form", 0, f"designer code not generated ({e}) - open the form and save it")
        project.forms.append(sf.name)
        stats["forms"] += 1
        stats["controls"] += len(form.controls)
        stats["handlers"] += len(sf.handlers or sf.extra.get("procs") or {})
        notes.add("exact", sf.file.name, 0, f"form {sf.name}: {len(form.controls)} control(s) with positions, sizes, "
                                            "texts, fonts and colours")
        if is_startup and not project.startup:
            project.startup = sf.name
    if project.forms and not project.startup:
        project.startup = project.forms[0]
    if project.startup and len(project.forms) > 1:
        try:
            sfp = dest / plugin.code_file(project.startup)
            text = sfp.read_text(encoding="utf-8")
            for f in project.forms:
                if f != project.startup:
                    text = plugin.on_form_added(text, f)
            sfp.write_text(text, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    # modules
    for name, p, kind in src.modules:
        progress(f"Module {p.name} ...")
        text = read_text(p)
        out_name = None
        if opts.code == "comments":
            pass
        elif python and kind in ("bas", "cls") and ctx is not None:
            from .vb6_to_python import translate_class, translate_module
            mi = ctx.modules.get((name if kind == "bas" else _vb_name(p) or name).lower())
            if mi is not None:
                code, _st = (translate_module if kind == "bas" else translate_class)(ctx, mi, text, toolkit, notes)
                out_name = f"{mi.name}.py"
                (dest / out_name).write_text(code, encoding="utf-8")
                notes.add("rules", p.name, 0, f"{'module' if kind == 'bas' else 'class'} {mi.name} -> {out_name}")
        elif target == "vb-basic" and kind == "vb":
            out_name = f"{_ident(name)}.bas"
            (dest / out_name).write_text(_vbnet_module_vb6(p, notes), encoding="utf-8")
        if out_name is None:
            out_name = f"{_ident(name)}{plugin.code_ext}"
            cm = plugin.line_comments[0] if getattr(plugin, "line_comments", None) else "#"
            body = "\n".join(f"{cm} {ln}" if ln.strip() else "" for ln in text.splitlines())
            head = plugin.module_template(_ident(name)) if hasattr(plugin, "module_template") else ""
            (dest / out_name).write_text(f"{head}{cm} ---- original {p.name} (translate it to {target}) ----\n"
                                         f"{body}\n", encoding="utf-8")
            notes.add("manual", p.name, 1, f"{p.name} kept as comments in {out_name} - translate it")
        project.modules.append(out_name)
        stats["modules"] += 1
    if python and src.language in ("vb6", "vbnet"):
        for rt in ("vb6compat.py", "vb6format.py"):
            shutil.copy2(RUNTIME / rt, dest / rt)
            if rt not in project.modules:
                project.modules.append(rt)
        if src.language == "vb6":               # ADO / DAO for database programs (CreateObject / OpenDatabase)
            shutil.copy2(Path(__file__).resolve().parent.parent / "runtimes" / "vbado.py", dest / "vbado.py")
            if "vbado.py" not in project.modules:
                project.modules.append("vbado.py")
            _copy_data_files(src, dest, notes)
        notes.add("info", "vb6compat.py", 0, "vb6compat.py + vb6format.py: VB6 functions used by the translated code "
                                             "(Val, CStr, Format, MsgBox, file channels, Collection ...)")
    project.save()
    return dest / Project.FILE


def _sub_main_form(src, notes) -> str:
    for name, p, kind in src.modules:
        if kind != "bas":
            continue
        text = read_text(p)
        m = re.search(r"^\s*(?:Public\s+|Private\s+)?Sub\s+Main\s*\(\s*\)(.*?)^\s*End\s+Sub", text, re.I | re.M | re.S)
        if m:
            line = text.count("\n", 0, m.start()) + 1
            fm = re.search(r"\b(\w+)\.Show\b", m.group(1))
            names = {f.name.lower(): f.name for f in src.forms}
            form = names.get(fm.group(1).lower(), "") if fm else ""
            notes.add("manual", p.name, line, "the VB6 project starts with Sub Main: the RAD IDE project starts with "
                                              f"form {form or '(first form)'} - call {name}.Main from its Load event "
                                              "if Sub Main does more than showing it")
            return form
    return ""


# ---------------------------------------------------------------------------- per-source writers
def _assemble_python(plugin, form: Form, is_startup: bool, members: list[str], imports: set,
                     app_title: str = "") -> str:
    code = plugin.new_code(form, is_startup)
    # drop the empty Load stub when the translation provides one
    if any(m.strip().startswith(f"def {form.name}_Load(") for m in members):
        i = plugin.find_handler(code, f"{form.name}_Load")
        if i >= 0:
            lines = code.splitlines()
            j = i + 1
            while j < len(lines) and (lines[j].strip() in ("pass", "") or lines[j].startswith("        ")):
                j += 1
            del lines[i:j]
            code = "\n".join(lines) + "\n"
    marker = '    """Write your event handlers here."""\n'
    block = "\n" + "\n".join(members).rstrip() + "\n"
    if marker in code:
        code = code.replace(marker, marker + block, 1)
    else:
        idx = code.find("\n\nif __name__")
        code = code[:idx] + "\n" + block + code[idx:] if idx >= 0 else code + block
    lines = code.split("\n")
    # imports after the designer import (the user code imports the designer first)
    k = next((i for i, ln in enumerate(lines) if ln.startswith("from ") and "_designer import" in ln), 0)
    extra = ["from vb6compat import *  # noqa: F401,F403 - VB6 functions (Val, MsgBox, Format, file I/O ...)"] + \
        sorted(i for i in imports if i)
    if app_title:
        extra += ["", f"App.Title = {json.dumps(app_title)}  # VB6 App.Title (default title of MsgBox / InputBox)"]
    lines[k + 1:k + 1] = extra
    code = "\n".join(lines)
    code = re.sub(r"\n{3,}(    (?:def|@property))", r"\n\n\1", code)
    code = re.sub(r"\n{4,}", "\n\n\n", code)
    code = re.sub(r"\n+if __name__ ==", "\n\n\nif __name__ ==", code)
    return code


def _vb6_form_python(ctx, sf: SourceForm, toolkit, plugin, is_startup, notes) -> str:
    from .vb6_to_python import translate_form_code
    fi = ctx.forms[sf.name.lower()]
    r = translate_form_code(ctx, fi, sf.code, toolkit, sf.file.name, notes)
    imports = {i for i in r["imports"] if not i.endswith(f"import {sf.name}")}
    code = _assemble_python(plugin, sf.form, is_startup, r["members"], imports, ctx.title)
    sf.extra["stats"] = r["stats"]
    st = r["stats"]
    notes.add("rules", sf.file.name, 0, f"{sf.name}: {st.get('rules', 0)} statement(s) translated by rules, "
                                        f"{st.get('manual', 0)} left as TODO")
    try:
        compile(code, plugin.code_file(sf.name), "exec")
    except SyntaxError as e:
        notes.add("manual", plugin.code_file(sf.name), e.lineno or 0, f"generated code has a syntax error: {e.msg}")
    return code


def _cs_form_python(sf: SourceForm, target, plugin, notes, opts, progress) -> str | None:
    from ..importers.exe import dotnet
    from .cs_qt import QtEmitter, TkEmitter, qt_code_fixups
    cls, wiring = sf.extra.get("cls"), sf.extra.get("wiring") or {}
    if cls is None:
        return None
    em = QtEmitter if target == "python-qt" else TkEmitter
    tr = dotnet.translate_form_class(cls, sf.form.to_dict(), wiring, sf.extra.get("all_forms") or {sf.name}, target,
                                     emitter_cls=em)
    code = tr["code"]
    if target == "python-qt":
        code = qt_code_fixups(code)
    fname = sf.code_file.name if sf.code_file else sf.file.name
    for meth, status in tr["methods"]:
        line = _line_of(sf.code, meth.split(" ")[0] + "(")
        if status == "rules":
            notes.add("rules", fname, line, f"{meth} translated to Python by rules")
        else:
            notes.add("manual", fname, line, f"{meth}: some C# lines are kept as '# C#:' comments - rewrite them")
    t, u = tr["stats"]
    sf.extra["stats"] = {"rules": t, "approx": 0, "manual": u}
    try:
        compile(code, plugin.code_file(sf.name), "exec")
    except SyntaxError as e:
        notes.add("manual", plugin.code_file(sf.name), e.lineno or 0, f"generated code has a syntax error: {e.msg}")
    return code


def _vbnet_vb6_text(sf: SourceForm, notes: Notes) -> tuple[str, dict]:
    from .vbnet import vbnet_form_to_vb6
    tmp = Notes()
    text, linemap = vbnet_form_to_vb6(sf.extra["vbclass"], sf.form.to_dict(), sf.extra.get("wiring") or {},
                                      sf.code_file.name, tmp)
    notes.extend(tmp)
    return text, linemap


def _vbnet_form_vb6(sf: SourceForm, notes: Notes) -> str:
    text, _lm = _vbnet_vb6_text(sf, notes)
    notes.add("rules", sf.code_file.name, 0, f"{sf.name}: VB.NET code rewritten as VB6 (runs on the bundled interpreter)")
    return text


def _vbnet_form_python(sf: SourceForm, toolkit, plugin, is_startup, notes) -> str:
    from .vb6_to_python import translate_form_code
    text, linemap = _vbnet_vb6_text(sf, notes)
    ctx = ProjectContext()
    fi = FormInfo.of(sf.form, sf.code_file.name)
    ctx.forms[sf.name.lower()] = fi
    ctx.add_module(sf.name, "frm", text, sf.code_file.name)
    tmp = Notes()
    r = translate_form_code(ctx, fi, text, toolkit, sf.code_file.name, tmp)
    for n in tmp.items:                     # line numbers of the intermediate VB6 -> the .vb file
        notes.add(n.level, n.file, linemap.get(n.line, 0) if n.line else 0, n.text)
    code = _assemble_python(plugin, sf.form, is_startup, r["members"], r["imports"])
    sf.extra["stats"] = r["stats"]
    st = r["stats"]
    notes.add("rules", sf.code_file.name, 0, f"{sf.name}: VB.NET -> VB6 -> Python: {st.get('rules', 0)} statement(s) "
                                             f"translated by rules, {st.get('manual', 0)} left as TODO")
    try:
        compile(code, plugin.code_file(sf.name), "exec")
    except SyntaxError as e:
        notes.add("manual", plugin.code_file(sf.name), e.lineno or 0, f"generated code has a syntax error: {e.msg}")
    return code


def _vbnet_module_vb6(p: Path, notes: Notes) -> str:
    from .vbnet import VbNetToVb6, parse_vb_classes
    text = read_text(p)
    out = [f'Attribute VB_Name = "{_ident(p.stem)}"', "Option Explicit", ""]
    for c in parse_vb_classes(text, p.name):
        conv = VbNetToVb6({}, c.name, p.name, notes, {m.name for m in c.methods})
        for ln, f in c.fields:
            out.append(re.sub(r"^(?:Private|Public|Friend|Shared|\s)+", "Public ", f))
            del ln
        for m in c.methods:
            is_fn = m.kind == "function"
            head = f"Public {'Function' if is_fn else 'Sub'} {m.name}({m.params})" + \
                (f" As {conv.vb6_type(m.ret)}" if is_fn and m.ret else "")
            out += ["", head] + [t for _l, t in conv.body(m, is_fn)] + [f"End {'Function' if is_fn else 'Sub'}"]
    notes.add("rules", p.name, 0, f"module {p.stem} rewritten as VB6")
    return "\n".join(out) + "\n"


def _vb6_keep(src: MigrationSource, dest: Path, notes: Notes, stats: dict, progress) -> Path:
    """VB6 -> vb-basic: the existing importer (the VB code runs as it is on the bundled interpreter)."""
    from ..importers.vb6_import import import_vb6
    progress("Importing the VB6 project (code kept as it is) ...")
    rep = import_vb6(src.path, dest, "vb-basic")
    for w in rep.warnings:
        notes.add("approx" if "approximation" in w else "info", src.path.name, 0, w)
    stats.update(forms=rep.forms, controls=rep.controls, handlers=rep.handlers, modules=len(src.modules))
    notes.add("exact", src.path.name, 0, f"{rep.forms} form(s) and {len(src.modules)} module(s): the VB6 code is "
                                         "kept exactly as it was (it runs on the bundled VB6 interpreter)")
    orig = dest / "_original_vb6"
    if orig.exists() and not any(orig.iterdir()):
        orig.rmdir()
    return dest / Project.FILE


def _generic_form_code(src, sf: SourceForm, target, plugin, is_startup, notes, opts, progress) -> str:
    """Any target: the form + one handler per original event; the original code as comments (+ AI)."""
    code = plugin.new_code(sf.form, is_startup)
    cm = plugin.line_comments[0] if getattr(plugin, "line_comments", None) else "#"
    handlers = dict(sf.handlers)
    if not handlers and sf.extra.get("procs"):
        from .vbcommon import vb_event_to_neutral
        for name, (body, line) in sf.extra["procs"].items():
            ctrl, _, ev = name.rpartition("_")
            c = sf.form.find(ctrl) if ctrl.lower() != "form" else None
            ctype = "Form" if ctrl.lower() == "form" else (c.type if c else None)
            neutral = vb_event_to_neutral(ctype, ev) if ctype else None
            if neutral:
                handlers[f"{sf.name if ctype == 'Form' else c.name}_{neutral}"] = (name, body, line)
    fname = sf.code_file.name if sf.code_file else sf.file.name
    lang_name = {"vb6": "VB6", "csharp": "C#", "vbnet": "VB.NET", "pascal": "Pascal"}.get(src.language, src.language)
    for handler, (meth, body, line) in handlers.items():
        owner, _, event = handler.rpartition("_")
        ctrl = sf.form.find(owner) if owner != sf.name else None
        if owner != sf.name and ctrl is None:
            continue
        hname = plugin.handler_for(sf.form, ctrl, event)
        new_body = None
        if opts.code == "rules+ai" and body.strip():
            new_body = _ai_handler(body, lang_name, target, sf, progress)
            if new_body:
                notes.add("ai", fname, line, f"{meth} translated to {target} by AI - review it")
        if new_body is None:
            new_body = [f"{cm} TODO: translate the original {lang_name} code of {meth} ({fname}:{line})"] + \
                [f"{cm} {ln.rstrip()}" if ln.strip() else cm for ln in body.splitlines()]
            if plugin.code_ext == ".py":
                new_body.append("pass")
            if body.strip():
                notes.add("manual", fname, line, f"{meth} kept as {lang_name} comments in {hname} - translate it")
        try:
            i = plugin.find_handler(code, hname)
            if i >= 0:
                lines = code.splitlines()
                code = _insert_body(code, i + 1, new_body) if i + 1 < len(lines) else code
            else:
                code, bl = plugin.add_handler(code, hname, sf.form, event_args(event))
                code = _insert_body(code, bl, new_body)
        except Exception as e:  # noqa: BLE001
            notes.add("manual", fname, line, f"{meth}: could not add the handler {hname} ({e})")
    return code


def _ai_available() -> tuple[bool, str]:
    try:
        from .. import ai
        p, model = ai.default("edit")
        ok, why = p.available()
        return ok, (f"{p.name}{' / ' + model if model else ''}" if ok else why)
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _ai_handler(body: str, lang_name: str, target: str, sf: SourceForm, progress) -> list[str] | None:
    from ..importers.exe.base import ai_translate
    ctrls = ", ".join(f"{c.name} ({c.type})" for c in sf.form.controls)
    ctx = (f"Target: the body of one event handler in a RAD IDE {target} form. Controls: {ctrls}. Answer with "
           "the statements of the body only (no function header).")
    code, who = ai_translate(body, lang_name, target, ctx, progress)
    if not code:
        return None
    import textwrap
    return textwrap.dedent(code.expandtabs(4)).strip("\n").splitlines()


def _ai_fix(src, sf: SourceForm, target, code: str, notes: Notes, progress) -> str:
    """rules+ai: let the AI rewrite the generated code when the rules left TODO / C# comment lines."""
    if not re.search(r"# TODO \(VB6|# C#:|' TODO \(VB\.NET\)", code):
        return code
    ok, who = _ai_available()
    if not ok:
        notes.add("info", sf.name, 0, f"AI translation not used: {who}")
        return code
    if not target.startswith("python"):
        return code
    from ..importers.exe.base import ai_translate
    ctx = (f"This is a RAD IDE {target} form class translated by rules from {src.language}. Rewrite ONLY the lines "
           "marked '# TODO (VB6' or '# C#:' (the original code is in the comment) and return the WHOLE file. Keep "
           "every method name and signature.")
    new, who = ai_translate(code, "partly translated Python", "Python", ctx, progress)
    if new and f"class {sf.name}" in new:
        try:
            compile(new, f"{sf.name}.py", "exec")
            notes.add("ai", sf.name, 0, f"{sf.name}: lines the rules could not translate were rewritten by AI ({who}) "
                                        "- review them")
            return new
        except SyntaxError as e:
            notes.add("info", sf.name, 0, f"the AI answer did not compile ({e}); the rules translation is kept")
    else:
        notes.add("info", sf.name, 0, f"AI translation not used: {who}")
    return code


# ============================================================================ report
LEVEL_TITLES = [("exact", "Exact (copied without change)"), ("rules", "Converted by rules"),
                ("approx", "Converted by rules - approximate (check the behaviour)"), ("ai", "Converted by AI"),
                ("manual", "Manual TODO"), ("info", "Notes")]


def report_markdown(src, target, dest, project_file, notes: Notes, stats: dict, seconds: float, opts) -> str:
    L = [f"# Migration report - {src.name}", "",
         f"- Source: **{src.label}** `{src.path}`",
         f"- Target: **{target}**{' (VB.NET Windows Forms, Visual Studio project)' if target == 'vbnet' else ''}",
         f"- Project: `{project_file}`" if project_file else "- Project: (not written)",
         f"- Mode: {opts.mode}, code: {opts.code}",
         f"- Forms: {stats.get('forms', 0)}, controls: {stats.get('controls', 0)}, "
         f"event handlers: {stats.get('handlers', 0)}, modules: {stats.get('modules', 0)}",
         f"- Time: {seconds:.1f} s", ""]
    counts = {lv: len(notes.of(lv)) for lv, _t in LEVEL_TITLES}
    L += ["| Exact | Rules | Approximate | AI | Manual TODO |", "|---|---|---|---|---|",
          f"| {counts['exact']} | {counts['rules']} | {counts['approx']} | {counts['ai']} | {counts['manual']} |", ""]
    for level, title in LEVEL_TITLES:
        items = notes.of(level)
        if not items:
            continue
        L += [f"## {title}", ""]
        for n in items:
            where = f"`{n.where()}` " if n.file else ""
            L.append(f"- {where}{n.text}")
        L.append("")
    L += ["## Files", "", f"- `{REPORT}` - this report"]
    if opts.keep_original and opts.mode != "inplace":
        L.append("- `_original/` - the original project files, for reference")
    if target in ("python-tk", "python-qt") and src.language in ("vb6", "vbnet"):
        L.append("- `vb6compat.py`, `vb6format.py` - VB6 runtime helpers used by the translated code")
    L.append("")
    return "\n".join(L)


def result_json(res: MigrationResult) -> str:
    return json.dumps({"ok": res.ok, "folder": str(res.folder), "project": str(res.project_file or ""),
                       "report": str(res.report_path or ""), "target": res.target, "stats": res.stats,
                       "notes": [n.__dict__ for n in res.notes.items]}, indent=2)


__all__ = ["MigrationSource", "SourceForm", "Options", "MigrationResult", "MigrationError", "load_source", "plan",
           "migrate", "targets_for", "keep_target", "detect", "supported_patterns", "CONTROL_TYPES"]
