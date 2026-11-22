"""Language-neutral data model for forms, controls and projects.

A form is stored as JSON (*.form). Language plugins read this model and
generate the GUI code for their own language/toolkit.

Controls may live inside containers (Panel/GroupBox): props["Parent"] holds
the container name ("" = the form) and Left/Top are relative to it.
"""
from __future__ import annotations

import errno
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .controls import CONTROL_TYPES, FORM_PROPS, menu_names


# ============================================================================ file reading / writing
class ProjectFileError(ValueError):
    """A .form / project.radproj / .radsln cannot be read: ``reason`` says why in plain words (empty,
    truncated JSON, merge conflict markers, not UTF-8 ...). The file is never written after this error."""

    def __init__(self, path, reason: str):
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"{self.path.name} {reason}")


# what opening a damaged / unreadable .form can raise (MainWindow.open_designer / open_code report these)
FORM_LOAD_ERRORS = (ProjectFileError, OSError, UnicodeError, ValueError, KeyError, TypeError)


_CONFLICT_RE = re.compile(r"^(<{7}|>{7})(?: |$)", re.M)


def read_text_file(path) -> tuple[str, dict]:
    """(text, format) of a project text file. UTF-8 (with or without BOM) and UTF-16 (BOM, or the zero
    bytes of ASCII text) are read; anything else raises ProjectFileError with a clear message. *format*
    keeps the raw bytes, the encoding, the newline style and the trailing newline so a save can write the
    file back the same way."""
    path = Path(path)
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        enc = "utf-16"
    elif len(raw) >= 4 and raw[1] == 0 and raw[3] == 0 and raw[0] != 0:
        enc = "utf-16-le"
    elif len(raw) >= 4 and raw[0] == 0 and raw[2] == 0 and raw[1] != 0:
        enc = "utf-16-be"
    else:
        enc = "utf-8"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError as e:
        if enc.startswith("utf-16"):
            raise ProjectFileError(path, f"is not valid UTF-16 text (offset {e.start}): the file is corrupted") \
                from None
        raise ProjectFileError(path, f"is not UTF-8 text (byte 0x{raw[e.start]:02X} at offset {e.start}): it "
                                     f"was probably saved in an ANSI code page (e.g. Windows-1256 Arabic) - "
                                     f"save it as UTF-8 and open it again") from None
    fmt = {"raw": raw, "encoding": enc, "newline": "\r\n" if "\r\n" in text else ("\n" if "\n" in text else None),
           "trailing": text.endswith("\n"), "ascii": text.isascii()}
    return text, fmt


def read_json_file(path, what: str = "file") -> tuple[object, dict]:
    """(data, format) of a JSON project file; ProjectFileError for an empty, truncated, corrupted or
    conflicted file (git merge markers)."""
    text, fmt = read_text_file(path)
    if not text.strip():
        raise ProjectFileError(path, f"is empty (0 bytes of JSON): it is not a valid {what}")
    m = _CONFLICT_RE.search(text)
    if m and re.search(r"^={7}\s*$", text, re.M):
        line = text.count("\n", 0, m.start()) + 1
        raise ProjectFileError(path, f"contains unresolved git merge conflict markers (line {line}: "
                                     f"'{m.group(1)}'): resolve the conflict (keep one side, remove the "
                                     f"<<<<<<< / ======= / >>>>>>> lines) and open it again")
    if "\x00" in text:
        raise ProjectFileError(path, "contains NUL bytes: the file is corrupted")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProjectFileError(path, f"is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}): the "
                                     f"file may be truncated or corrupted") from None
    except RecursionError:
        raise ProjectFileError(path, "is nested too deeply to be a valid " + what) from None
    return data, fmt


def write_text_safe(path, text: str, encoding: str = "utf-8", newline: str | None = None) -> None:
    """Write *text* (``\\n`` newlines; *newline* None = the platform's) without ever leaving a truncated file:
    the bytes go to a temporary file next to it that replaces it. A read-only file raises PermissionError
    (nothing is written)."""
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        raise PermissionError(errno.EACCES, f"{path.name} is read-only", str(path))
    nl = os.linesep if newline is None else newline
    data = (text.replace("\n", nl) if nl != "\n" else text).encode(encoding)
    write_bytes_safe(path, data)


def write_bytes_safe(path, data: bytes) -> None:
    """Atomic save (radide/safeio.py): temp file + fsync + replace, so a crash, a full disk or a lock leaves
    the old or the new file, never a truncated one. Errors are OSErrors with a readable message (a read-only
    or locked file raises a PermissionError subclass); the last saved version is kept as a backup."""
    from .safeio import atomic_write_bytes
    atomic_write_bytes(Path(path), data, backup=True)


def _encoding_out(fmt: dict | None) -> str:
    enc = (fmt or {}).get("encoding") or "utf-8"
    return "utf-16" if enc in ("utf-16-le", "utf-16-be") else enc


@dataclass(eq=False)
class Control:
    type: str
    props: dict
    # Visual States (Expression Blend, CONTRACTS 8.7): state name -> {property: value}
    states: dict = field(default_factory=dict)
    # Layout variants (radide/variants, plan 1.5): size id -> {property: value} overriding the base design
    variants: dict = field(default_factory=dict)
    # other keys of the control's entry in the .form (written by a newer version) - kept when saving
    extra: dict = field(default_factory=dict, repr=False)
    # properties a placeholder ("package not installed") added when loading: name -> the value added; they
    # are not written back while unchanged, so the control's saved data stays exactly what it was
    added: dict = field(default_factory=dict, repr=False)

    @property
    def name(self) -> str:
        return self.props["Name"]

    @property
    def parent(self) -> str:
        return self.props.get("Parent", "")

    @property
    def ctype(self):
        return CONTROL_TYPES[self.type]

    def to_dict(self) -> dict:
        props = self.props
        if self.added:
            props = {k: v for k, v in props.items() if k not in self.added or self.added[k] != v}
        d = {"type": self.type, "props": props}
        if self.states:
            d["states"] = self.states
        if self.variants:
            d["variants"] = self.variants
        for k, v in self.extra.items():
            if k not in d:
                d[k] = v
        return d

    @staticmethod
    def from_dict(d: dict) -> "Control":
        if not isinstance(d, dict) or not isinstance(d.get("type"), str) or not d["type"]:
            raise ValueError(f"a control entry has no \"type\": {str(d)[:80]}")
        ctype = CONTROL_TYPES.get(d["type"])
        missing = ctype is None
        if missing:                           # unknown type (package / user control not available)
            from .components import missing_type
            ctype = CONTROL_TYPES[d["type"]] = missing_type(d["type"])
        else:
            from .components import MISSING_CATEGORY
            missing = ctype.category == MISSING_CATEGORY
        saved = d.get("props", {})
        if not isinstance(saved, dict):
            raise ValueError(f"the \"props\" of a {d['type']} control is not an object")
        props = ctype.default_props("")
        saved = json.loads(json.dumps(saved))
        added = {k: json.loads(json.dumps(v)) for k, v in props.items() if k not in saved} if missing else {}
        props.update(saved)
        states = d.get("states")
        variants = d.get("variants")
        extra = {k: json.loads(json.dumps(v)) for k, v in d.items()
                 if k not in ("type", "props", "states", "variants")}
        return Control(d["type"], props,
                       json.loads(json.dumps(states)) if isinstance(states, dict) else {},
                       json.loads(json.dumps(variants)) if isinstance(variants, dict) else {},
                       extra, added)


FORM_VERSION = 2      # 2: Button TextAlign defaults to Center (see Form.from_dict)

# Foreign projects (radide/foreign): forms whose source of truth is a native file of another IDE
# (Form1.Designer.cs / .vb, Form1.frm, Unit1.dfm ...).  Each store has handles(path) -> bool,
# load(path) -> Form and save(path, form) -> None; Form.load / Form.save ask them first.
FORM_STORES: list = []


def _form_store(path):
    for st in FORM_STORES:
        try:
            if st.handles(Path(path)):
                return st
        except Exception:  # noqa: BLE001 - a broken store must not break normal .form files
            continue
    return None


@dataclass
class Form:
    props: dict = field(default_factory=lambda: {k: p.default for k, p in FORM_PROPS.items()})
    controls: list[Control] = field(default_factory=list)
    # other top-level keys of the .form (Blend: "states", "storyboards", "datasources", "bindings")
    extra: dict = field(default_factory=dict)
    # problems found while loading (newer format version, repaired entries ...) - the IDE shows them
    warnings: list = field(default_factory=list, compare=False, repr=False)
    # the "version" of the file this form was read from (0 = not read from a file)
    source_version: int = field(default=0, compare=False, repr=False)
    # how the file was read (raw bytes, encoding, newline, the model snapshot just after loading): a save
    # without a change writes the same bytes back; a changed form keeps the encoding and newline style
    source: dict | None = field(default=None, compare=False, repr=False)

    @property
    def name(self) -> str:
        return self.props["Name"]

    # ------------------------------------------------------------ names
    def all_names(self) -> set[str]:
        names = {self.name.lower()}
        for c in self.controls:
            names.add(c.name.lower())
            if c.type in ("MenuStrip", "ToolStrip"):
                names |= {n.lower() for n in menu_names(c.props.get("Items", []))}
        return names

    def unique_name(self, base: str, taken: set[str] | None = None) -> str:
        used = self.all_names() | (taken or set())
        i = 1
        while f"{base}{i}".lower() in used:
            i += 1
        return f"{base}{i}"

    # ------------------------------------------------------------ queries
    def find(self, name: str) -> Control | None:
        # name -> index cache, checked on every hit (the control at that index still has that name and
        # no earlier control does), so edits of self.controls / props["Name"] need no invalidation;
        # the designer asks this for every ancestor of every control on each mouse move
        controls = self.controls
        cache = self.__dict__.get("_find_cache")
        if cache is not None and cache[0] is controls:
            i = cache[1].get(name)
            if i is not None and i < len(controls) and controls[i].props.get("Name") == name \
                    and cache[2] == len(controls):
                return controls[i]
        index: dict = {}
        for i, c in enumerate(controls):
            index.setdefault(c.props.get("Name"), i)
        self.__dict__["_find_cache"] = (controls, index, len(controls))
        i = index.get(name)
        return controls[i] if i is not None else None

    def visual(self) -> list[Control]:
        return [c for c in self.controls if not c.ctype.nonvisual]

    def nonvisual(self) -> list[Control]:
        return [c for c in self.controls if c.ctype.nonvisual]

    def menu(self) -> Control | None:
        for c in self.controls:
            if c.type == "MenuStrip":
                return c
        return None

    def children(self, parent_name: str) -> list[Control]:
        return [c for c in self.visual() if c.parent == parent_name]

    def children_map(self) -> dict[str, list[Control]]:
        """parent name -> its visual children (z-order kept): children() for every container in one pass."""
        kids: dict[str, list[Control]] = {}
        for c in self.controls:
            if not c.ctype.nonvisual:
                kids.setdefault(c.props.get("Parent", ""), []).append(c)
        return kids

    def descendants(self, ctrl: Control, kids: dict | None = None) -> list[Control]:
        kids = self.children_map() if kids is None else kids
        out = []

        def walk(name):
            for ch in kids.get(name, ()):
                out.append(ch)
                walk(ch.name)
        walk(ctrl.name)
        return out

    def abs_pos(self, ctrl: Control) -> tuple[int, int]:
        x, y = int(ctrl.props["Left"]), int(ctrl.props["Top"])
        seen = set()
        p = self.find(ctrl.parent) if ctrl.parent else None
        while p is not None and p.name not in seen:
            seen.add(p.name)
            ox, oy = self.client_offset(p)
            x += int(p.props["Left"]) + ox
            y += int(p.props["Top"]) + oy
            p = self.find(p.parent) if p.parent else None
        return x, y

    @staticmethod
    def client_offset(ctrl: Control) -> tuple[int, int]:
        """Where children's (0, 0) is inside a container (a TabControl's page is below its tabs)."""
        if ctrl.type == "TabControl":
            from .controls import TAB_PAGE_X, TAB_PAGE_Y
            return TAB_PAGE_X, TAB_PAGE_Y
        return 0, 0

    def client_origin(self, ctrl: Control | None) -> tuple[int, int]:
        """Absolute position of the client area of a container (None = the form)."""
        if ctrl is None:
            return 0, 0
        x, y = self.abs_pos(ctrl)
        ox, oy = self.client_offset(ctrl)
        return x + ox, y + oy

    def ordered(self) -> list[Control]:
        """Visual controls with every container before its children (z-order kept)."""
        out: list[Control] = []
        kids = self.children_map()           # one pass instead of a scan of all controls per container

        def visit(parent: str):
            for c in kids.get(parent, ()):
                out.append(c)
                if c.ctype.container:
                    visit(c.name)
        visit("")
        # orphans (parent missing) go to the form
        if len(out) != sum(len(v) for v in kids.values()) or len({id(c) for c in out}) != len(out):
            seen = {id(c) for c in out}
            for c in self.visual():
                if id(c) not in seen:
                    c.props["Parent"] = ""
                    out.append(c)
                    seen.add(id(c))
        return out

    # ------------------------------------------------------------ edits
    def add(self, type_name: str, x: int, y: int, parent: str = "") -> Control:
        ctype = CONTROL_TYPES[type_name]
        prefix = ctype.prefix
        if self.extra.get("camel_names"):        # e.g. C# WinForms (Visual Studio names it button1)
            prefix = prefix[:1].lower() + prefix[1:]
        name = self.unique_name(prefix)
        props = ctype.default_props(name)
        if not ctype.nonvisual:
            props["Left"], props["Top"] = x, y
        props["Parent"] = parent
        ctrl = Control(type_name, props)
        self.controls.append(ctrl)
        return ctrl

    # ------------------------------------------------------------ io
    def to_dict(self) -> dict:
        # a form of a newer format keeps its version number (its unknown data is kept as it is)
        d = {"version": max(FORM_VERSION, self.source_version), "props": self.props,
             "controls": [c.to_dict() for c in self.controls]}
        loaded = (self.source or {}).get("keys", ())
        for k, v in self.extra.items():
            if k not in d and (v not in (None, {}, []) or k in loaded):
                d[k] = v
        return d

    @staticmethod
    def from_dict(d: dict) -> "Form":
        if not isinstance(d, dict):
            raise ValueError("the form file does not contain a JSON object")
        props, controls = d.get("props", {}), d.get("controls", [])
        if props is None:
            props = {}
        if controls is None:
            controls = []
        if not isinstance(props, dict):
            raise ValueError("\"props\" is not an object")
        if not isinstance(controls, list):
            raise ValueError("\"controls\" is not a list")
        try:
            version = int(d.get("version", 1) or 1)
        except (TypeError, ValueError):
            raise ValueError(f"\"version\" is not a number: {d.get('version')!r}") from None
        f = Form()
        f.props.update(props)
        f.controls = [Control.from_dict(c) for c in controls]
        f.source_version = version if version > FORM_VERSION else 0
        if version > FORM_VERSION:
            f.warnings.append(f"the form was saved by a newer RAD IDE (format version {version}; this version "
                              f"reads version {FORM_VERSION}): data this version does not know is kept as it is")
        f._repair()
        if version < 2:
            # version 1 gave Buttons the Label default TextAlign "Left" (captions drawn at the left edge);
            # a Button's caption is centred like in VB / WinForms
            for c in f.controls:
                if c.type == "Button" and c.props.get("TextAlign") == "Left":
                    c.props["TextAlign"] = "Center"
        f.extra = {k: json.loads(json.dumps(v)) for k, v in d.items()
                   if k not in ("version", "props", "controls")}
        return f

    def _repair(self) -> None:
        """Entries a hand edit / merge broke: a control without a Name gets one, positions that are not
        numbers go back to the default (reported in ``warnings``)."""
        if not isinstance(self.props.get("Name"), str) or not self.props.get("Name"):
            self.props["Name"] = "Form1"
            self.warnings.append("the form had no Name: it is called Form1")
        seen: set = set()
        names = {str(c.props.get("Name")).lower() for c in self.controls}
        for c in self.controls:
            n = c.props.get("Name")
            if not isinstance(n, str) or not n or n.lower() in seen:
                i = 1
                while f"{c.ctype.prefix}{i}".lower() in seen | names:
                    i += 1
                new = f"{c.ctype.prefix}{i}"
                self.warnings.append(f"a {c.type} control had " + (f"the duplicate Name '{n}'" if n else "no Name")
                                     + f": it is called {new}")
                c.props["Name"] = n = new
            seen.add(n.lower())
            if not isinstance(c.props.get("Parent", ""), str):
                c.props["Parent"] = ""
            for k in ("Left", "Top", "Width", "Height"):
                if k in c.props and not isinstance(c.props[k], bool):
                    try:
                        v = int(c.props[k])
                        if not isinstance(c.props[k], int):     # "12" / 12.0 -> 12 (geometry is integer)
                            c.props[k] = v
                        continue
                    except (TypeError, ValueError, OverflowError):     # OverflowError: 1e999
                        pass
                    dflt = c.ctype.default_props(n).get(k, 0)
                    self.warnings.append(f"{n}.{k} was not a number ({c.props[k]!r}): set to {dflt}")
                    c.props[k] = dflt

    def snapshot(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def save(self, path: Path) -> None:
        st = _form_store(path) if FORM_STORES else None
        if st is not None:                       # a native form file of a foreign project
            st.save(Path(path), self)
            return
        path = Path(path)
        src = self.source
        if src is not None and src.get("raw") is not None and self.snapshot() == src.get("snapshot"):
            # nothing changed since the file was read: the same bytes (an open -> save is byte-identical)
            try:
                if path.is_file() and path.read_bytes() == src["raw"]:
                    return                       # nothing to write (also fine for a read-only file)
            except OSError:
                pass
            write_bytes_safe(path, src["raw"])
            return
        text = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        newline = None
        if src is not None:
            newline = src.get("newline") or None
            if src.get("trailing"):
                text += "\n"
        write_text_safe(path, text, _encoding_out(src), newline)
        if src is None:                          # a new form: later saves without a change are no-ops
            self.source = src = {"encoding": "utf-8", "newline": None, "trailing": False}
        try:                                     # the file on disk is now this form
            src.update(raw=Path(path).read_bytes(), snapshot=self.snapshot())
        except OSError:
            src["raw"] = None

    @staticmethod
    def load(path: Path) -> "Form":
        st = _form_store(path) if FORM_STORES else None
        if st is not None:
            return st.load(Path(path))
        path = Path(path)
        d, fmt = read_json_file(path, "form file")
        if not isinstance(d, dict):
            raise ProjectFileError(path, "does not contain a form (a JSON object with \"props\" and "
                                         "\"controls\" is expected)")
        from .usercontrols import ensure_types      # user controls of the folder (radide/usercontrols.py)
        ensure_types(d, path.parent)
        from .components import ensure_types as ensure_components   # component packages (radide/components)
        ensure_components(d, path.parent)
        try:
            f = Form.from_dict(d)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            raise ProjectFileError(path, f"is not a valid form file: {e}") from None
        fmt["keys"] = tuple(k for k in d if k not in ("version", "props", "controls"))
        f.source = fmt
        fmt["snapshot"] = f.snapshot()
        return f


@dataclass
class Project:
    """A project folder containing project.radproj + forms + code files."""
    folder: Path
    name: str
    language: str
    forms: list[str] = field(default_factory=list)  # form names
    startup: str = ""
    modules: list[str] = field(default_factory=list)  # plain code files (no form)
    # forms written in another language than the project default: form name -> plugin id
    form_languages: dict[str, str] = field(default_factory=dict)
    # solutions (docs/CONTRACTS.md section 7): "app" | "library", and the names of the
    # projects of the same solution this one references (Add Reference)
    kind: str = "app"
    references: list[str] = field(default_factory=list)
    # proxy files generated for the references: library name -> files (relative to folder)
    reference_files: dict[str, list[str]] = field(default_factory=dict)
    # keys of project.radproj this version does not know (kept when saving)
    extra: dict = field(default_factory=dict, repr=False, compare=False)
    # how project.radproj was read (raw bytes, the dict, encoding, newline): an unchanged project is not
    # rewritten, a changed one keeps the file's encoding and newline style
    source: dict | None = field(default=None, repr=False, compare=False)

    FILE = "project.radproj"
    KINDS = ("app", "library", "website")      # website: CONTRACTS 8.1 (radide/web_site/project.py)
    _KNOWN = ("name", "language", "forms", "startup", "modules", "form_languages", "kind", "references",
              "reference_files")

    @property
    def is_library(self) -> bool:
        return self.kind == "library"

    def to_dict(self) -> dict:
        """The project.radproj content. Keys added for solutions are written only when they
        differ from the default, so files of older projects stay byte-identical."""
        data = {"name": self.name, "language": self.language,
                "forms": self.forms, "startup": self.startup, "modules": self.modules}
        langs = {f: lang for f, lang in self.form_languages.items()
                 if f in self.forms and lang and lang != self.language}
        if langs:
            data["form_languages"] = langs
        if self.kind and self.kind != "app":
            data["kind"] = self.kind
        if self.references:
            data["references"] = list(self.references)
        files = {k: list(v) for k, v in self.reference_files.items() if v}
        if files:
            data["reference_files"] = files
        for k, v in self.extra.items():
            if k not in data and k not in self._KNOWN:
                data[k] = v
        return data

    def save(self) -> None:
        path = self.folder / self.FILE
        data = self.to_dict()
        src = self.source
        if src is not None and src.get("data") == data and path.is_file():
            try:
                if path.read_bytes() == src["raw"]:
                    return                       # unchanged: the file is not rewritten (byte-identical)
            except OSError:
                pass
        ascii_only = src is None or src.get("ascii", True)
        text = json.dumps(data, indent=2, ensure_ascii=ascii_only)
        if src is not None and src.get("trailing"):
            text += "\n"
        write_text_safe(path, text, _encoding_out(src), (src or {}).get("newline") or None)
        try:
            raw = path.read_bytes()
        except OSError:
            return
        if src is None:
            self.source = src = {"ascii": True}
        src.update(raw=raw, data=json.loads(json.dumps(data)))

    @staticmethod
    def load(folder: Path) -> "Project":
        folder = Path(folder)
        d, fmt = read_json_file(folder / Project.FILE, "project file")
        if not isinstance(d, dict):
            raise ProjectFileError(folder / Project.FILE, "is not a valid project file (a JSON object is "
                                                          "expected)")
        langs = d.get("form_languages") or {}
        refs = d.get("references") or []
        rfiles = d.get("reference_files") or {}
        for key in ("forms", "modules"):
            if d.get(key) is not None and not isinstance(d.get(key), list):
                raise ProjectFileError(folder / Project.FILE, f"is not a valid project file: \"{key}\" is "
                                                              f"not a list")
        kind = str(d.get("kind") or "app").lower()
        # tolerant: a missing/empty "name" falls back to the folder name; "language" is required
        name = str(d.get("name") or "").strip() or folder.resolve().name
        language = str(d.get("language") or "").strip()
        if not language:
            raise ProjectFileError(folder / Project.FILE, "has no \"language\" entry")
        forms = [str(f) for f in d.get("forms") or [] if f]
        modules = [str(m) for m in d.get("modules") or [] if m]
        p = Project(folder, name, language, forms, str(d.get("startup") or ""),
                       modules,
                       {str(k): str(v) for k, v in langs.items()} if isinstance(langs, dict) else {},
                       kind if kind in Project.KINDS else "app",
                       [str(r) for r in refs] if isinstance(refs, list) else [],
                       {str(k): [str(f) for f in v] for k, v in rfiles.items() if isinstance(v, list)}
                       if isinstance(rfiles, dict) else {},
                       {k: v for k, v in d.items() if k not in Project._KNOWN})
        fmt["data"] = json.loads(json.dumps(p.to_dict()))
        p.source = fmt
        return p

    def references_project(self, name: str) -> bool:
        return any(r.lower() == name.lower() for r in self.references)

    # ------------------------------------------------------------ languages
    def form_language(self, form_name: str) -> str:
        """Plugin id of a form (forms without an entry use the project language)."""
        return self.form_languages.get(form_name) or self.language

    def set_form_language(self, form_name: str, language: str) -> None:
        if not language or language == self.language:
            self.form_languages.pop(form_name, None)
        else:
            self.form_languages[form_name] = language

    def forms_in(self, language: str) -> list[str]:
        """Forms written in *language* (plugin id)."""
        return [f for f in self.forms if self.form_language(f) == language]

    def form_path(self, form_name: str) -> Path:
        return self.folder / f"{form_name}.form"

    def missing_forms(self) -> list[str]:
        """Forms listed in project.radproj whose .form file does not exist."""
        return [f for f in self.forms if not self.form_path(f).is_file()]
