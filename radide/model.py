"""Language-neutral data model for forms, controls and projects.

A form is stored as JSON (*.form). Language plugins read this model and
generate the GUI code for their own language/toolkit.

Controls may live inside containers (Panel/GroupBox): props["Parent"] holds
the container name ("" = the form) and Left/Top are relative to it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .controls import CONTROL_TYPES, FORM_PROPS, menu_names


@dataclass(eq=False)
class Control:
    type: str
    props: dict
    # Visual States (Expression Blend, CONTRACTS 8.7): state name -> {property: value}
    states: dict = field(default_factory=dict)
    # Layout variants (radide/variants, plan 1.5): size id -> {property: value} overriding the base design
    variants: dict = field(default_factory=dict)

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
        d = {"type": self.type, "props": self.props}
        if self.states:
            d["states"] = self.states
        if self.variants:
            d["variants"] = self.variants
        return d

    @staticmethod
    def from_dict(d: dict) -> "Control":
        ctype = CONTROL_TYPES[d["type"]]
        props = ctype.default_props("")
        props.update(json.loads(json.dumps(d.get("props", {}))))
        states = d.get("states")
        variants = d.get("variants")
        return Control(d["type"], props,
                       json.loads(json.dumps(states)) if isinstance(states, dict) else {},
                       json.loads(json.dumps(variants)) if isinstance(variants, dict) else {})


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
        for c in self.controls:
            if c.name == name:
                return c
        return None

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

    def descendants(self, ctrl: Control) -> list[Control]:
        out = []
        for ch in self.children(ctrl.name):
            out.append(ch)
            out += self.descendants(ch)
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

        def visit(parent: str):
            for c in self.children(parent):
                out.append(c)
                if c.ctype.container:
                    visit(c.name)
        visit("")
        # orphans (parent missing) go to the form
        for c in self.visual():
            if c not in out:
                c.props["Parent"] = ""
                out.append(c)
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
        d = {"version": FORM_VERSION, "props": self.props,
             "controls": [c.to_dict() for c in self.controls]}
        for k, v in self.extra.items():
            if k not in d and v not in (None, {}, []):
                d[k] = v
        return d

    @staticmethod
    def from_dict(d: dict) -> "Form":
        f = Form()
        f.props.update(d.get("props", {}))
        f.controls = [Control.from_dict(c) for c in d.get("controls", [])]
        if int(d.get("version", 1) or 1) < 2:
            # version 1 gave Buttons the Label default TextAlign "Left" (captions drawn at the left edge);
            # a Button's caption is centred like in VB / WinForms
            for c in f.controls:
                if c.type == "Button" and c.props.get("TextAlign") == "Left":
                    c.props["TextAlign"] = "Center"
        f.extra = {k: json.loads(json.dumps(v)) for k, v in d.items()
                   if k not in ("version", "props", "controls")}
        return f

    def snapshot(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def save(self, path: Path) -> None:
        st = _form_store(path) if FORM_STORES else None
        if st is not None:                       # a native form file of a foreign project
            st.save(Path(path), self)
            return
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> "Form":
        st = _form_store(path) if FORM_STORES else None
        if st is not None:
            return st.load(Path(path))
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        from .usercontrols import ensure_types      # user controls of the folder (radide/usercontrols.py)
        ensure_types(d, Path(path).parent)
        from .components import ensure_types as ensure_components   # component packages (radide/components)
        ensure_components(d, Path(path).parent)
        return Form.from_dict(d)


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
        (self.folder / self.FILE).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def load(folder: Path) -> "Project":
        folder = Path(folder)
        d = json.loads((folder / Project.FILE).read_text(encoding="utf-8"))
        langs = d.get("form_languages") or {}
        refs = d.get("references") or []
        rfiles = d.get("reference_files") or {}
        if not isinstance(d, dict):
            raise ValueError(f"{folder / Project.FILE} is not a valid project file")
        kind = str(d.get("kind") or "app").lower()
        # tolerant: a missing/empty "name" falls back to the folder name; "language" is required
        name = str(d.get("name") or "").strip() or folder.resolve().name
        language = str(d.get("language") or "").strip()
        if not language:
            raise ValueError(f"{folder / Project.FILE} has no \"language\" entry")
        forms = [str(f) for f in d.get("forms") or [] if f]
        modules = [str(m) for m in d.get("modules") or [] if m]
        return Project(folder, name, language, forms, str(d.get("startup") or ""),
                       modules,
                       {str(k): str(v) for k, v in langs.items()} if isinstance(langs, dict) else {},
                       kind if kind in Project.KINDS else "app",
                       [str(r) for r in refs] if isinstance(refs, list) else [],
                       {str(k): [str(f) for f in v] for k, v in rfiles.items() if isinstance(v, list)}
                       if isinstance(rfiles, dict) else {},
                       {k: v for k, v in d.items() if k not in Project._KNOWN})

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
