"""Delphi projects (.dpr / .dproj / .groupproj) - and the shared Pascal adapter used by Lazarus
projects (radide/foreign/lazarus.py) - opened IN PLACE.

The native files stay authoritative: no project.radproj is written into the user's folder.
IDE-only state (startup unit) lives in ``%APPDATA%\\RADIDE\\foreign\\<hash>``.

* Solution Explorer: one project per .dpr/.dproj/.lpi (a .groupproj gives a solution with several);
  every unit with a form (.dfm/.lfm/.fmx next to the .pas) is a form, other units, the program file
  and include files are code modules.
* Designer: the form file is read into the neutral model (radide/foreign/pascal_forms.py) and written
  back preserving everything the designer does not change (byte-identical when nothing changed).
* Code: .pas units in the Monaco editor (Pascal highlighting), encoding and line endings kept.
  Double-click on a control creates ``procedure TForm1.Button1Click(Sender: TObject);`` (declaration +
  implementation) and ``OnClick = Button1Click`` in the form file.
* Build/Run (F5): radide/foreign/lazarus.py (lazbuild / fpc -Mdelphi / dcc when Delphi is present).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from . import pascal_forms as pf

LANG_ID = "pascal"
FORM_EXTS = (".dfm", ".lfm", ".fmx", ".xfm")


# =============================================================================== project model

@dataclass
class PasUnit:
    key: str                 # IDE form/module key: path of the unit relative to the folder, no extension
    pas: Path
    form_file: Path | None = None
    form_name: str = ""      # frmMain
    form_class: str = ""     # TfrmMain


@dataclass
class PascalProjectInfo:
    kind: str                         # "delphi" | "lazarus"
    file: Path                        # .dproj / .dpr / .lpi / .lpr
    main_source: Path                 # .dpr / .lpr
    name: str
    title: str = ""
    target: str = ""                  # Lazarus Target/Filename
    framework: str = ""               # Delphi FrameworkType (VCL / FMX)
    units: list[PasUnit] = field(default_factory=list)       # units with a form
    others: list[Path] = field(default_factory=list)         # units without form, .inc ...
    main_form: str = ""

    def uses_vcl(self) -> bool:
        """True for a Delphi GUI application (VCL / FireMonkey): it needs Delphi to build."""
        if self.framework.upper() in ("VCL", "FMX"):
            return True
        if self.units:
            return True
        try:
            src = _read_text(self.main_source)[0]
        except OSError:
            return False
        return re.search(r"\buses\b[^;]*\b(Vcl\.Forms|FMX\.Forms|Forms)\b", src, re.I | re.S) is not None


def _rel_key(folder: Path, pas: Path) -> str:
    try:
        rel = os.path.relpath(pas, folder)
    except ValueError:
        rel = str(pas)
    rel = rel.replace("\\", "/")
    return rel[: -len(Path(rel).suffix)] if Path(rel).suffix else rel


def _form_header(path: Path) -> tuple[str, str]:
    try:
        data = path.read_bytes()[:4096]
    except OSError:
        return "", ""
    if pf.is_binary_dfm(data):
        try:
            text = pf.binary_dfm_to_text(path.read_bytes())
        except Exception:  # noqa: BLE001
            return "", ""
    else:
        text = data.decode("utf-8", errors="replace")
    m = re.search(r"^\s*(?:object|inherited|inline)\s+(\w+)\s*:\s*(\w+)", text, re.I | re.M)
    return (m.group(1), m.group(2)) if m else ("", "")


def make_units(folder: Path, files: list[str], lazarus: bool) -> tuple[list[PasUnit], list[Path]]:
    """Split project files into units with a form and other code files."""
    units, others = [], []
    order = (".lfm", ".dfm", ".fmx", ".xfm") if lazarus else (".dfm", ".fmx", ".lfm", ".xfm")
    for f in files:
        p = (folder / f.replace("\\", os.sep)).resolve()
        if p.suffix.lower() in FORM_EXTS:
            continue
        ff = next((p.with_suffix(e) for e in order if p.with_suffix(e).is_file()), None)
        if ff is not None and p.suffix.lower() in (".pas", ".pp"):
            name, cls = _form_header(ff)
            units.append(PasUnit(_rel_key(folder, p), p, ff, name, cls))
        elif p.suffix.lower() in (".pas", ".pp", ".inc", ".dpr", ".lpr", ".dpk", ".lpk"):
            others.append(p)
    return units, others


_USES_IN_RX = re.compile(r"([A-Za-z_][\w.]*)\s+in\s+'([^']+)'(?:\s*\{([^}]*)\})?", re.I)


def _uses_files(src: str) -> list[str]:
    m = re.search(r"\buses\b(.*?);", src, re.I | re.S)
    if not m:
        return []
    return [x.group(2) for x in _USES_IN_RX.finditer(m.group(1))]


def read_program(path: Path, kind: str = "delphi") -> PascalProjectInfo:
    """A .dpr / .lpr alone: units listed with ``in 'file.pas'`` (+ units of the folder for .lpr)."""
    path = Path(path).resolve()
    src = _read_text(path)[0]
    files = _uses_files(src)
    if kind == "lazarus":            # Lazarus programs list units by name only: take the folder's units
        names = re.search(r"\buses\b(.*?);", src, re.I | re.S)
        listed = {w.lower() for w in re.findall(r"[A-Za-z_]\w*", re.sub(r"\{.*?\}|//[^\n]*", "",
                                                                       names.group(1) if names else ""))}
        for p in sorted(path.parent.glob("*.pas")) + sorted(path.parent.glob("*.pp")):
            if p.stem.lower() in listed and p.name not in files:
                files.append(p.name)
    info = PascalProjectInfo(kind, path, path, path.stem, title=path.stem)
    info.units, info.others = make_units(path.parent, files, lazarus=kind == "lazarus")
    info.main_form = _main_form_of(src, info)
    return info


def _main_form_of(src: str, info: PascalProjectInfo) -> str:
    m = re.search(r"Application\.CreateForm\s*\(\s*\w+\s*,\s*(\w+)\s*\)", src, re.I)
    if m:
        for u in info.units:
            if u.form_name.lower() == m.group(1).lower():
                return u.key
    return info.units[0].key if info.units else ""


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def read_dproj(path: Path) -> PascalProjectInfo:
    path = Path(path).resolve()
    root = ET.parse(path).getroot()
    main, framework, files = "", "", []
    for el in root.iter():
        t = _strip_ns(el.tag)
        if t == "MainSource" and el.text and el.text.strip().lower().endswith((".dpr", ".dpk")) and not main:
            main = el.text.strip()
        elif t == "FrameworkType" and el.text and not framework:
            framework = el.text.strip()
        elif t == "DCCReference" and el.get("Include"):
            files.append(el.get("Include"))
    if not main:
        main = path.with_suffix(".dpr").name
    msrc = (path.parent / main).resolve()
    if msrc.is_file():
        for f in _uses_files(_read_text(msrc)[0]):     # units only listed in the .dpr
            if f.lower() not in {x.lower() for x in files}:
                files.append(f)
    info = PascalProjectInfo("delphi", path, msrc, path.stem, title=path.stem, framework=framework)
    info.units, info.others = make_units(path.parent, files, lazarus=False)
    info.main_form = _main_form_of(_read_text(msrc)[0] if msrc.is_file() else "", info)
    return info


def read_groupproj(path: Path) -> list[PascalProjectInfo]:
    path = Path(path).resolve()
    root = ET.parse(path).getroot()
    out = []
    for el in root.iter():
        if _strip_ns(el.tag) == "Projects" and el.get("Include"):
            p = (path.parent / el.get("Include").replace("\\", os.sep)).resolve()
            if p.is_file():
                out.append(load_project_info(p))
    return out


def load_project_info(path: Path) -> PascalProjectInfo:
    ext = path.suffix.lower()
    if ext == ".dproj":
        return read_dproj(path)
    if ext == ".lpi":
        from .lazarus import read_lpi
        return read_lpi(path)
    if ext == ".lpr":
        from .lazarus import read_lpr
        return read_lpr(path)
    if ext in (".dpr", ".dpk"):
        dproj = path.with_suffix(".dproj")
        return read_dproj(dproj) if dproj.is_file() else read_program(path, "delphi")
    raise ValueError(f"{path.name}: not a Delphi/Lazarus project")


def state_dir(project_file: Path) -> Path:
    """IDE-only state of a foreign project, outside the user's folder."""
    from ..paths import roaming_dir          # <install>\settings for a portable build
    base = roaming_dir() / "foreign"
    h = hashlib.sha1(os.path.normcase(str(Path(project_file).resolve())).encode("utf-8")).hexdigest()[:16]
    d = base / h
    d.mkdir(parents=True, exist_ok=True)
    return d


# =============================================================================== text files

def _read_text(path: Path) -> tuple[str, dict]:
    """(text, fmt): fmt = {"enc", "bom", "nl"} so that a write gives the same bytes back."""
    data = Path(path).read_bytes()
    bom = b""
    if data.startswith(b"\xef\xbb\xbf"):
        bom, data, enc = data[:3], data[3:], "utf-8"
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        bom, enc = data[:2], "utf-16"
        data = data
    else:
        try:
            data.decode("utf-8")
            enc = "utf-8"
        except UnicodeDecodeError:
            enc = "cp1252"
    text = data.decode(enc)
    if enc == "utf-16":
        bom = b""
        text = text.lstrip("﻿")
    nl = "\r\n" if "\r\n" in text else "\n"
    return text, {"enc": enc, "bom": bom, "nl": nl}


def _encode(text: str, fmt: dict) -> tuple[bytes, str]:
    """Bytes for *text* in the file's format; falls back to UTF-8 + BOM when the code page cannot
    hold the text (returns a note then)."""
    enc = fmt.get("enc", "utf-8")
    note = ""
    try:
        data = text.encode(enc)
    except UnicodeEncodeError:
        data = b"\xef\xbb\xbf" + text.encode("utf-8")
        note = f"the text does not fit code page {enc}: saved as UTF-8 with BOM (Delphi 2009+ / Lazarus read it)"
        fmt.update(enc="utf-8", bom=b"")
        return data, note
    return (fmt.get("bom") or b"") + data, note


# =============================================================================== the IDE project

def make_project(info: PascalProjectInfo):
    from ..model import Project

    class _PascalProject(Project):
        foreign = True
        foreign_kind = info.kind

        def __init__(self, info: PascalProjectInfo):
            folder = info.file.parent
            forms = [u.key for u in info.units]
            mods = []
            for p in [info.main_source] + list(info.others):
                k = os.path.relpath(p, folder).replace("\\", "/") if p.is_file() else None
                if k and k not in mods:
                    mods.append(k)
            super().__init__(folder, info.name, LANG_ID, forms, info.main_form or (forms[0] if forms else ""),
                             mods)
            self.info = info
            self.native_file = info.file
            self.lazarus = info.kind == "lazarus"
            self._units = {u.key: u for u in info.units}
            self._forms: dict[str, dict] = {}
            self._fmt: dict[str, dict] = {}
            self.notes: list[str] = []
            self._load_state()

        # ------------------------------------------------------------- state outside the folder
        def _state_file(self) -> Path:
            return state_dir(self.native_file) / "state.json"

        def _load_state(self) -> None:
            try:
                d = json.loads(self._state_file().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return
            if d.get("startup") in self.forms:
                self.startup = d["startup"]

        def save(self) -> None:          # never writes project.radproj into the user's folder
            try:
                self._state_file().write_text(json.dumps({"startup": self.startup,
                                                          "file": str(self.native_file)}), encoding="utf-8")
            except OSError:
                pass

        # ------------------------------------------------------------- forms
        def form_path(self, form_name: str) -> Path:
            u = self._units.get(form_name)
            if u is not None and u.form_file is not None:
                return u.form_file
            return self.folder / f"{form_name}{'.lfm' if self.lazarus else '.dfm'}"

        def unit(self, key: str) -> PasUnit | None:
            return self._units.get(key)

        def load_form(self, key: str):
            path = self.form_path(key)
            raw = path.read_bytes()
            converted = False
            if pf.is_binary_dfm(raw):
                text, fmt = pf.binary_dfm_to_text(raw), {"enc": "cp1252", "bom": b"", "nl": "\r\n"}
                converted = True
                self.log(f"*** Warning: {path.name} is a BINARY form file - it is shown as text; when you change "
                         "the form it is saved in text format (Delphi and Lazarus read both).")
            else:
                text, fmt = _read_text(path)
            lazarus = path.suffix.lower() == ".lfm" or (self.lazarus and path.suffix.lower() != ".dfm")
            root = pf.parse_dfm(text)
            form, info = pf.dfm_to_form(root, lazarus)
            form.extra["pascal_class"] = root.cls
            form.extra["pascal_dialect"] = "lazarus" if lazarus else "delphi"
            self._forms[key] = {"text": text, "fmt": fmt, "base": pf.deep(form.to_dict()),
                                "lazarus": lazarus, "binary": converted}
            if info.unknown:
                self.log(f"{path.name}: components kept as they are (not designable here): " +
                         ", ".join(f"{n}: {c}" for n, c in info.unknown.items()))
            return form

        def save_form(self, key: str, form, code: str | None, code_modified: bool, form_modified: bool):
            """Write the form file (only what changed) and the unit. Returns the new unit text when it
            changed here (fields / uses / handlers added), else None."""
            st = self._forms.get(key)
            u = self._units.get(key)
            pas = u.pas if u is not None else self.folder / f"{key}.pas"
            if code is None:
                code = self.read_code(pas)
            orig_code = code
            new_code = code
            if st is not None:
                new = form.to_dict()
                same = json.dumps({"p": new["props"], "c": new["controls"]}, sort_keys=True) == \
                    json.dumps({"p": st["base"]["props"], "c": st["base"]["controls"]}, sort_keys=True)
                if not same or code_modified:
                    w = pf.FormWriter(st["text"], st["lazarus"], code)
                    out = w.apply(st["base"], new, handler_exists=lambda n: pf.has_method(new_code, n))
                    cls = form.extra.get("pascal_class") or pf.form_class_of(code)
                    plan = w.plan
                    new_code = pf.add_fields(new_code, cls, plan.new_fields)
                    new_code = pf.remove_fields(new_code, cls, plan.gone_fields)
                    new_code = pf.add_uses(new_code, pf.units_for_classes(new_code, plan.used_classes,
                                                                         st["lazarus"]))
                    for n in plan.notes:
                        self.log(f"{self.form_path(key).name}: {n}")
                    if out != st["text"] or (st.get("binary") and not same):
                        data, note = _encode(out.replace("\r\n", "\n").replace("\n", st["fmt"]["nl"]), st["fmt"])
                        if note:
                            self.log(f"{self.form_path(key).name}: {note}")
                        self.form_path(key).write_bytes(data)
                        st["binary"] = False
                    st["text"] = out
                    self._rebase(key, form, out)
            if new_code != orig_code or code_modified or not pas.exists():
                self.write_code(pas, new_code)
            return new_code if new_code != orig_code else None

        def _rebase(self, key: str, form, text: str) -> None:
            """After a save: identities = current names, base = what is on disk now."""
            st = self._forms[key]
            root = pf.parse_dfm(text)
            names = {o.name.lower() for o in root.walk()}
            for c in form.controls:
                if c.name.lower() in names:
                    c.props["_dfm"] = c.name
                else:
                    c.props.pop("_dfm", None)
            _f, info = pf.dfm_to_form(root, st["lazarus"])
            form.extra["pascal_events"] = info.events
            st["base"] = pf.deep(form.to_dict())

        # ------------------------------------------------------------- code files
        def _key_of(self, path: Path) -> str:
            return os.path.normcase(str(Path(path).resolve()))

        def read_code(self, path) -> str:
            path = Path(path)
            if not path.is_file():
                return ""
            text, fmt = _read_text(path)
            self._fmt[self._key_of(path)] = fmt
            return text.replace("\r\n", "\n")

        def write_code(self, path, text: str) -> None:
            path = Path(path)
            fmt = self._fmt.get(self._key_of(path))
            if fmt is None:
                fmt = _read_text(path)[1] if path.is_file() else {"enc": "utf-8", "bom": b"", "nl": "\r\n"}
                self._fmt[self._key_of(path)] = fmt
            text = text.replace("\r\n", "\n").replace("\n", fmt["nl"])
            data, note = _encode(text, fmt)
            if note:
                self.log(f"{path.name}: {note}")
            path.write_bytes(data)

        # ------------------------------------------------------------- misc
        def log(self, text: str) -> None:
            self.notes.append(text)
            win = _WIN.get("win")
            if win is not None:
                try:
                    win.log(text)
                    return
                except Exception:  # noqa: BLE001
                    pass

        def missing_forms(self) -> list[str]:
            return [f for f in self.forms if not self.form_path(f).is_file()]

    return _PascalProject(info)


_WIN: dict = {}


# =============================================================================== language plugin

def _plugin_class():
    from ..languages.base import LanguagePlugin, RunSpec

    class PascalPlugin(LanguagePlugin):
        id = LANG_ID
        display_name = "Object Pascal (Delphi / Lazarus)"
        code_ext = ".pas"
        interpreter_names = []
        case_sensitive = False
        line_comments = ["//"]
        block_comment = ("{", "}")
        string_quotes = ["'"]
        keywords = ("and array as asm begin case class const constructor destructor div do downto else end "
                    "except exports file finalization finally for function goto if implementation in inherited "
                    "initialization inline interface is label library mod nil not object of on or out packed "
                    "procedure program property raise record repeat resourcestring set shl shr string then "
                    "threadvar to try type unit until uses var while with xor private protected public "
                    "published strict override virtual abstract overload reintroduce read write default "
                    "specialize generic").split()
        builtins = ("Integer Cardinal Int64 Byte Word Boolean Char String Double Single Real Extended Currency "
                    "TObject TForm TComponent Self Result True False WriteLn ReadLn Write Read Inc Dec Length "
                    "SetLength High Low Ord Chr IntToStr StrToInt FloatToStr StrToFloat Format ShowMessage "
                    "Exit Break Continue Assigned FreeAndNil Trim UpperCase LowerCase Copy Pos").split()
        supports_debug = False
        foreign_only = True            # not offered for new projects

        def __init__(self):
            self._params: dict[str, str] = {}

        # files ------------------------------------------------------------
        def code_file(self, form_name: str) -> str:
            return f"{form_name}.pas"

        def designer_file(self, form_name: str) -> str:
            for proj in _PROJECTS.values():             # the real form file (.dfm / .lfm / .fmx)
                u = proj.unit(form_name) if hasattr(proj, "unit") else None
                if u is not None and u.form_file is not None:
                    return os.path.relpath(u.form_file, proj.folder).replace("\\", "/")
            return f"{form_name}.dfm"

        def generate_designer(self, form, user_code: str) -> str:
            return ""          # the form file is written by the project (save_form), never generated

        def new_code(self, form, is_startup: bool) -> str:
            cls = "T" + form.name
            return (f"unit {form.name};\n\ninterface\n\nuses\n  Classes, SysUtils, Forms, Controls, StdCtrls;\n\n"
                    f"type\n  {cls} = class(TForm)\n  private\n  public\n  end;\n\nvar\n  {form.name}: {cls};\n\n"
                    "implementation\n\n{$R *.dfm}\n\nend.\n")

        def module_template(self, name: str) -> str:
            return f"unit {name};\n\ninterface\n\nimplementation\n\nend.\n"

        # events -----------------------------------------------------------
        def handler_for(self, form, ctrl, event: str) -> str:
            evmap = form.extra.get("pascal_events") or {}
            lazarus = form.extra.get("pascal_dialect") == "lazarus"
            if ctrl is None:
                owner, ntype, ev = "", None, event
            elif ctrl.type in ("MenuStrip", "ToolStrip"):
                owner, ntype, ev = event, "MenuItem", "Click"
            else:
                owner, ntype, ev = ctrl.name, ctrl.type, event
            h = (evmap.get(owner) or {}).get(ev) or pf.default_handler(owner, ev, ntype, lazarus)
            prop = pf.event_prop(ntype, ev, lazarus) or "OnClick"
            self._params[h.lower()] = pf.event_params(prop, lazarus)
            return h

        def handler_name(self, owner: str, event: str) -> str:
            return pf.default_handler(owner, event, None, False)

        def find_handler(self, code: str, name: str) -> int:
            return _find_any_method(code, name)

        def add_handler(self, code: str, name: str, form, args=None) -> tuple[str, int]:
            cls = form.extra.get("pascal_class") or pf.form_class_of(code)
            params = self._params.get(name.lower(), "Sender: TObject")
            return pf.add_method(code, cls, name, params)

        def rename_symbol(self, code: str, old: str, new: str) -> str:
            return re.sub(rf"\b{re.escape(old)}\b", new, code, flags=re.I)

        def on_file_removed(self, code: str, filename: str) -> str:
            return code

        # run --------------------------------------------------------------
        def find_interpreter(self, configured: str = "") -> str:
            return sys.executable          # the build+run helper (radide/foreign/lazarus.py)

        def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
            proj = _PROJECTS.get(os.path.normcase(str(Path(folder).resolve())))
            target = str(proj.native_file) if proj is not None else str(folder)
            env = dict(os.environ)
            from ..paths import python_root
            repo = str(python_root())
            env["PYTHONPATH"] = repo + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            env["PYTHONIOENCODING"] = "utf-8"
            py = sys.executable
            if Path(py).name.lower() == "pythonw.exe":
                py = str(Path(py).with_name("python.exe"))
            return RunSpec(py, ["-u", "-m", "radide.foreign.lazarus", "run", target], Path(folder), env)

    return PascalPlugin


def _find_any_method(code: str, name: str) -> int:
    rx = re.compile(rf"^\s*(?:class\s+)?(?:procedure|function)\s+\w+\s*\.\s*{re.escape(name)}\b", re.I)
    impl = False
    for i, ln in enumerate(code.split("\n")):
        if re.match(r"^\s*implementation\b", ln, re.I):
            impl = True
        if impl and rx.match(ln):
            return i
    return -1


_PLUGIN = None
_PROJECTS: dict[str, object] = {}


def ensure_plugin():
    """Register the Pascal plugin with the language registry (done when a Pascal project opens)."""
    global _PLUGIN
    from .. import languages
    languages.all_plugins()
    if _PLUGIN is None:
        _PLUGIN = _plugin_class()()
    languages._PLUGINS.setdefault(LANG_ID, _PLUGIN)
    return languages._PLUGINS[LANG_ID]


# =============================================================================== opening in the IDE

def probe_delphi(folder: Path):
    for pat in ("*.groupproj", "*.dproj", "*.dpr"):
        hits = sorted(Path(folder).glob(pat))
        if hits:
            same = [h for h in hits if h.stem.lower() == Path(folder).name.lower()]
            return (same or hits)[0]
    return None


def probe_lazarus(folder: Path):
    for pat in ("*.lpi", "*.lpr"):
        hits = sorted(Path(folder).glob(pat))
        if hits:
            return hits[0]
    return None


def load_any(path: Path) -> tuple[str, list]:
    """(solution name, [project objects]) for a .groupproj/.dproj/.dpr/.lpi/.lpr."""
    path = Path(path).resolve()
    if path.suffix.lower() == ".groupproj":
        infos = read_groupproj(path)
        name = path.stem
    else:
        infos = [load_project_info(path)]
        name = infos[0].name
    return name, [make_project(i) for i in infos]


def open_pascal(win, path: Path) -> bool:
    """Opener registered with radide.features.foreign_projects (Delphi and Lazarus formats)."""
    from PyQt6.QtWidgets import QMessageBox

    from ..solution import Solution, SolutionProject
    path = Path(path).resolve()
    ensure_plugin()
    _WIN["win"] = win
    try:
        name, projects = load_any(path)
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(win, "RAD IDE", f"Cannot open {path.name}:\n{e}")
        return True
    if not projects:
        QMessageBox.warning(win, "RAD IDE", f"{path.name} lists no project that can be opened.")
        return True
    if not win._confirm_close_project():
        return True

    class _ForeignSolution(Solution):
        def save(self, path=None):           # never writes a .radsln into the user's folder
            return self.path

    first = projects[0]
    entries = []
    sln = _ForeignSolution(name, path.parent, [], first.name, None)
    for p in projects:
        rel = os.path.relpath(p.folder, path.parent) if p.folder != path.parent else "."
        entries.append(SolutionProject(p.name, rel.replace("\\", "/")))
        sln._cache[p.name.lower()] = p
        _PROJECTS[os.path.normcase(str(Path(p.folder).resolve()))] = p
    sln.projects = entries
    sln.foreign_file = path
    win.stop_project()
    win._reset()
    win.sln = sln
    for p in projects:
        win._state_for(p)
    win.activate_project(first)
    win._fill_solution()
    project = win.project
    present = [f for f in project.forms if f not in project.missing_forms()]
    if present:
        win.open_designer(project.startup if project.startup in present else present[0])
    elif project.modules:
        win.open_module(project.modules[0])
    try:
        win.toolbox.setEnabled(True)
    except Exception:  # noqa: BLE001
        pass
    win._update_title()
    win._update_actions()
    kinds = {p.info.kind for p in projects}
    label = "Lazarus" if kinds == {"lazarus"} else "Delphi"
    win.log(f"Opened {label} project '{name}' in place from {path} "
            f"({sum(len(p.forms) for p in projects)} form(s), native files kept; nothing written to the folder)")
    for p in projects:
        if p.info.kind == "delphi" and p.info.uses_vcl():
            from .lazarus import find_delphi
            if find_delphi() is None:
                win.log(f"Note: {p.name} is a Delphi {p.info.framework or 'VCL'} application - building it needs "
                        "Delphi. Pascal > Migrate Delphi project to Lazarus makes a copy the free compiler builds.")
    _install_menu(win)
    try:
        win._remember(path)
    except Exception:  # noqa: BLE001
        pass
    return True


# =============================================================================== Pascal menu

def _install_menu(win) -> None:
    if getattr(win, "_pascal_menu", None) is not None:
        return
    from PyQt6.QtGui import QAction
    mb = win.menuBar()
    m = mb.addMenu("&Pascal")
    win._pascal_menu = m

    def act(text, slot):
        a = QAction(text, win)
        a.triggered.connect(slot)
        m.addAction(a)
        return a
    act("&Build project", lambda: _build_active(win))
    act("&Run (build first)", lambda: win.run_project(debug=False))
    m.addSeparator()
    act("&Download Free Pascal + Lazarus (portable)...", lambda: _install_toolchain_ui(win))
    act("Toolchain &status", lambda: _status(win))
    m.addSeparator()
    act("&Migrate Delphi project to Lazarus...", lambda: migrate_ui(win))


def _active_info(win):
    p = getattr(win, "project", None)
    return getattr(p, "info", None)


def _status(win):
    from .lazarus import toolchain_status
    win.log(toolchain_status())


def _proc(win, args: list[str], done=None):
    """Run ``python -m radide.foreign.lazarus <args>`` without blocking, output to the Output window."""
    from PyQt6.QtCore import QProcess, QProcessEnvironment
    proc = QProcess(win)
    env = QProcessEnvironment.systemEnvironment()
    from ..paths import python_root
    repo = str(python_root())
    env.insert("PYTHONPATH", repo)
    env.insert("PYTHONIOENCODING", "utf-8")
    proc.setProcessEnvironment(env)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.readyReadStandardOutput.connect(
        lambda: [win.log(line) for line in bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
                 .splitlines() if line.strip()])
    proc.finished.connect(lambda code, _s: (done(code) if done else None))
    py = sys.executable
    if Path(py).name.lower() == "pythonw.exe":
        py = str(Path(py).with_name("python.exe"))
    proc.start(py, ["-u", "-m", "radide.foreign.lazarus", *args])
    win._pascal_proc = proc
    return proc


def _build_active(win):
    info = _active_info(win)
    if info is None:
        win.log("The active project is not a Delphi/Lazarus project")
        return
    win.save_all()
    _proc(win, ["build", str(info.file)], lambda c: win.log("Build succeeded" if c == 0 else "Build FAILED"))


def _install_toolchain_ui(win):
    from PyQt6.QtWidgets import QMessageBox
    from .lazarus import find_lazarus, toolchain_dir
    if find_lazarus() is not None and (toolchain_dir() / "lazbuild.exe").is_file():
        win.log("Lazarus is already installed in " + str(toolchain_dir()))
        return
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen" and QMessageBox.question(
            win, "RAD IDE", "Download the official Lazarus 4.8 + Free Pascal 3.2.2 installer (about 220 MB) from "
                            "SourceForge and unpack it (portable, no admin) into\n" + str(toolchain_dir()) + " ?") \
            != QMessageBox.StandardButton.Yes:
        return
    _proc(win, ["install"], lambda c: win.log("Toolchain ready" if c == 0 else "Toolchain download FAILED"))


# =============================================================================== migration: Delphi -> Lazarus

_DELPHI_ONLY_PROPS = {"oldcreateorder", "pixelsperinch", "textheight", "explicitleft", "explicittop",
                      "explicitwidth", "explicitheight", "iscontrol", "designsize", "stylename", "touch.",
                      "margins.", "alignwithmargins", "stylelements", "parentbackground", "textheight",
                      "texthint", "font.charset", "bevelkind", "ctl3d", "parentctl3d",
                      "mainformontaskbar", "glassframe."}


def migrate_to_lazarus(info: PascalProjectInfo, dest: Path, log=print) -> Path:
    """Copy a Delphi project into *dest* as a Lazarus project (.lpi/.lpr, .lfm forms, LCL units).
    Properties the LCL does not know are removed from the copies (reported). Returns the .lpi."""
    import shutil
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    src = info.file.parent
    files = [info.main_source] + [u.pas for u in info.units] + list(info.others)
    names = []
    for f in files:
        if not f.is_file():
            continue
        text, fmt = _read_text(f)
        text = _lcl_source(text, f.suffix.lower() == ".dpr")
        out = dest / (f.stem + ".lpr" if f.suffix.lower() == ".dpr" else f.name)
        out.write_text(text, encoding="utf-8")
        names.append(out.name)
    for u in info.units:
        if u.form_file is None:
            continue
        raw = u.form_file.read_bytes()
        text = pf.binary_dfm_to_text(raw) if pf.is_binary_dfm(raw) else _read_text(u.form_file)[0]
        text, dropped = _lcl_form(text)
        (dest / (u.pas.stem + ".lfm")).write_text(text, encoding="utf-8")
        if dropped:
            log(f"{u.form_file.name}: removed Delphi-only properties: {', '.join(sorted(dropped))}")
    for extra in list(src.glob("*.inc")) + list(src.glob("*.ico")):
        shutil.copy2(extra, dest / extra.name)
    res = dest / (info.main_source.stem + ".res")         # {$R *.res}: the Delphi one, else an empty resource
    if (src / res.name).is_file():
        shutil.copy2(src / res.name, res)
    elif not res.exists():
        res.write_bytes(b"\x00\x00\x00\x00\x20\x00\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00" + b"\x00" * 16)
    lpr = info.main_source.stem + ".lpr"
    units_xml = f'      <Unit>\n        <Filename Value="{lpr}"/>\n        <IsPartOfProject Value="True"/>\n      </Unit>\n'
    for u in info.units:
        units_xml += (f'      <Unit>\n        <Filename Value="{u.pas.name}"/>\n        <IsPartOfProject Value="True"/>\n'
                      f'        <ComponentName Value="{u.form_name}"/>\n        <HasResources Value="True"/>\n'
                      '        <ResourceBaseClass Value="Form"/>\n      </Unit>\n')
    for o in info.others:
        if o.suffix.lower() in (".pas", ".pp"):
            units_xml += (f'      <Unit>\n        <Filename Value="{o.name}"/>\n        <IsPartOfProject Value="True"/>\n'
                          '      </Unit>\n')
    gui = bool(info.units)
    lpi = dest / (info.main_source.stem + ".lpi")
    lpi.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<CONFIG>
  <ProjectOptions>
    <Version Value="12"/>
    <General>
      <Title Value="{info.title or info.name}"/>
      <Scaled Value="True"/>
      <ResourceType Value="res"/>
    </General>
    <RequiredPackages>
{'      <Item>' + chr(10) + '        <PackageName Value="LCL"/>' + chr(10) + '      </Item>' if gui else ''}
    </RequiredPackages>
    <Units>
{units_xml}    </Units>
  </ProjectOptions>
  <CompilerOptions>
    <Version Value="11"/>
    <Target>
      <Filename Value="{info.main_source.stem}"/>
    </Target>
    <SearchPaths>
      <UnitOutputDirectory Value="lib\\$(TargetCPU)-$(TargetOS)"/>
    </SearchPaths>
    <Parsing>
      <SyntaxOptions>
        <SyntaxMode Value="Delphi"/>
      </SyntaxOptions>
    </Parsing>
{'    <Linking>' + chr(10) + '      <Options>' + chr(10) + '        <Win32>' + chr(10) + '          <GraphicApplication Value="True"/>' + chr(10) + '        </Win32>' + chr(10) + '      </Options>' + chr(10) + '    </Linking>' if gui else ''}
  </CompilerOptions>
</CONFIG>
""", encoding="utf-8")
    (dest / "MIGRATED_FROM_DELPHI.txt").write_text(
        f"Migrated by RAD IDE from {info.file}\nThe original Delphi project was not changed.\n", encoding="utf-8")
    log(f"Lazarus project written: {lpi}")
    return lpi


_UNIT_MAP = {"winapi.windows": "LCLIntf, LCLType", "windows": "LCLIntf, LCLType", "winapi.messages": "LMessages",
             "messages": "LMessages", "vcl.imaging.pngimage": "", "vcl.imaging.jpeg": "", "pngimage": "",
             "jpeg": "", "system.actions": "", "vcl.actnlist": "ActnList", "system.imagelist": "",
             "vcl.imglist": "ImgList", "vcl.themes": "", "vcl.styles": "", "variants": "Variants"}


def _lcl_source(text: str, program: bool) -> str:
    def fix_uses(m):
        items = [x.strip() for x in re.sub(r"\{[^}]*\}", "", m.group(2)).split(",")]
        out = []
        for it in items:
            if not it:
                continue
            name = it.split()[0]
            rest = it[len(name):]
            low = name.lower()
            if low in _UNIT_MAP:
                if _UNIT_MAP[low]:
                    out.extend(_UNIT_MAP[low].split(", "))
                continue
            short = re.sub(r"^(System|Winapi|Vcl|Data|Xml|Vcl\.Samples)\.", "", name)
            short = re.sub(r"^(Imaging|Samples)\.", "", short)
            out.append(short + rest)
        seen, uniq = set(), []
        for o in out:
            if o.split()[0].lower() not in seen:
                seen.add(o.split()[0].lower())
                uniq.append(o)
        if program and not any(u.lower() == "interfaces" for u in uniq):
            uniq.insert(0, "Interfaces")
        return m.group(1) + "\n  " + ",\n  ".join(uniq) + ";"
    text = re.sub(r"(\buses\b)(.*?);", fix_uses, text, flags=re.I | re.S)
    text = re.sub(r"\{\$R\s+\*\.dfm\}", "{$R *.lfm}", text, flags=re.I)
    text = re.sub(r"^\s*Application\.MainFormOnTaskbar\s*:=.*\n", "", text, flags=re.I | re.M)
    if not re.search(r"\{\$mode\s", text, re.I):
        text = re.sub(r"^(\s*(?:unit|program)\s+[\w.]+\s*;)", r"\1\n\n{$mode delphi}{$H+}", text, count=1,
                      flags=re.I | re.M)
    return text


def _lcl_form(text: str) -> tuple[str, set]:
    """Drop Delphi-only properties from a form text (the LCL raises on unknown properties)."""
    root = pf.parse_dfm(text)
    w = pf.FormWriter(text, True)
    dropped = set()
    for o in root.walk():
        for p in o.props:
            low = p.name.lower()
            if low in _DELPHI_ONLY_PROPS or any(low.startswith(x) for x in _DELPHI_ONLY_PROPS if x.endswith(".")):
                w.plan.drop(o, p.name)
                dropped.add(p.name)
    out = w.text[:w.root.line_start] + pf._render_obj(w.text, w.root, w.plan, w.nl) + w.text[w.root.end:]
    return out, dropped


def migrate_ui(win) -> None:
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    info = _active_info(win)
    if info is None or info.kind != "delphi":
        QMessageBox.information(win, "RAD IDE", "Open a Delphi project first (File > Open Project...).")
        return
    default = info.file.parent.parent / f"{info.file.parent.name}_Lazarus"
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        dest = default
    else:
        d = QFileDialog.getExistingDirectory(win, "Folder for the Lazarus copy", str(default.parent))
        if not d:
            return
        dest = Path(d) / default.name if Path(d) == default.parent else Path(d)
    try:
        lpi = migrate_to_lazarus(info, dest, win.log)
    except Exception as e:  # noqa: BLE001
        QMessageBox.critical(win, "RAD IDE", f"Migration failed:\n{e}")
        return
    win.log(f"Migrated to {lpi}. Opening it ...")
    open_pascal(win, lpi)


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".groupproj", ".dproj", ".dpr", ".dpk"], open_pascal, "Delphi project",
                    folder_probe=probe_delphi, name="delphi", priority=5)
