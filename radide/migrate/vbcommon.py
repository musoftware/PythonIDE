"""Shared pieces of the VB6 translators (Python and VB.NET): project context, original spelling of
identifiers, comments by line, VB6 event -> neutral event mapping, and report notes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..runtimes import vbparse

# report levels (MIGRATION_REPORT.md): exact copy / converted by rules / approximate rule / AI / manual TODO
LEVELS = ("exact", "rules", "approx", "ai", "manual", "info")


@dataclass
class Note:
    level: str
    file: str
    line: int
    text: str

    def where(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file


class Notes:
    def __init__(self):
        self.items: list[Note] = []
        self._seen: set = set()

    def add(self, level: str, file: str, line: int, text: str) -> None:
        key = (level, file, line, text)
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append(Note(level if level in LEVELS else "info", file, int(line or 0), text))

    def extend(self, other: "Notes") -> None:
        for n in other.items:
            self.add(n.level, n.file, n.line, n.text)

    def of(self, level: str) -> list[Note]:
        return [n for n in self.items if n.level == level]


# ----------------------------------------------------------------------------- identifiers & comments
_ID_RX = re.compile(r'"(?:[^"\n]|"")*"|\'[^\n]*|\b([A-Za-z_][A-Za-z0-9_]*)')


def casemap_of(text: str, into: dict | None = None) -> dict:
    """lower-case identifier -> spelling of its first occurrence outside strings/comments."""
    out = into if into is not None else {}
    for m in _ID_RX.finditer(text):
        w = m.group(1)
        if w and w.lower() not in out:
            out[w.lower()] = w
    return out


def comments_of(text: str) -> dict[int, tuple[str, bool]]:
    """{line: (comment text without the quote, whole_line)} for VB source (1-based lines)."""
    out = {}
    for i, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        s = raw.strip()
        low = s.lower()
        if low.startswith("rem ") or low == "rem":
            out[i] = (s[3:].strip(), True)
            continue
        in_str = False
        for j, ch in enumerate(raw):
            if ch == '"':
                in_str = not in_str
            elif ch == "'" and not in_str:
                body = raw[j + 1:].rstrip()
                if re.match(r"\s*Attribute\s+VB_", raw, re.I):
                    break
                out[i] = (body.strip(), raw[:j].strip() == "")
                break
    return out


def proc_ranges(text: str) -> list[tuple[int, int, str]]:
    """(first line, last line, name) of each Sub/Function/Property in VB source (1-based)."""
    out, start, name = [], 0, ""
    head = re.compile(r"^\s*(?:(?:Public|Private|Friend|Static|Global)\s+)*(?:Sub|Function|Property\s+(?:Get|Let|Set))"
                      r"\s+(\w+)", re.I)
    end = re.compile(r"^\s*End\s+(?:Sub|Function|Property)\b", re.I)
    for i, ln in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if not start:
            m = head.match(ln)
            if m:
                start, name = i, m.group(1)
        elif end.match(ln):
            out.append((start, i, name))
            start = 0
    return out


def strip_suffix(name: str) -> str:
    return name.rstrip("$%&!#@")


# ----------------------------------------------------------------------------- events
# neutral (RAD IDE / WinForms) event names for VB6 events, per neutral control type
def vb_event_to_neutral(ctype: str, vb_event: str) -> str | None:
    from ..runtimes.vbrun import VB_EVENT
    ev = vb_event.lower()
    if ctype == "Form":
        return {"load": "Load", "activate": "Activated", "deactivate": "Deactivate", "resize": "Resize",
                "unload": "FormClosing", "queryunload": "FormClosing", "terminate": "FormClosed",
                "click": "Click", "dblclick": "DoubleClick", "keydown": "KeyDown", "keyup": "KeyUp",
                "keypress": "KeyPress", "mousedown": "MouseDown", "mouseup": "MouseUp",
                "mousemove": "MouseMove", "initialize": "Load"}.get(ev)
    for table in (VB_EVENT.get(ctype, {}), VB_EVENT["*"]):
        for neutral, vb in table.items():
            if vb and vb.lower() == ev:
                return neutral
    if ctype == "TrackBar" and ev in ("scroll", "change"):
        return "ValueChanged"
    return None


# ----------------------------------------------------------------------------- context
@dataclass
class CtlInfo:
    name: str               # name in the neutral form (Command1_0 for an element of a control array)
    type: str               # neutral control type
    multiline: bool = False
    array: str = ""         # control array name ("" = not in an array)
    index: int = 0


@dataclass
class FormInfo:
    name: str
    form: object                                    # model.Form
    controls: dict = field(default_factory=dict)    # lower -> CtlInfo (single controls)
    arrays: dict = field(default_factory=dict)      # lower array name -> (Name, type, {index: CtlInfo})
    file: str = ""

    @staticmethod
    def of(form, file: str = "") -> "FormInfo":
        fi = FormInfo(form.name, form, file=file)
        for c in form.controls:
            arr = c.props.get("ArrayName")
            info = CtlInfo(c.name, c.type, bool(c.props.get("Multiline")), str(arr or ""),
                           int(c.props.get("ArrayIndex", 0) or 0))
            if arr:
                name, typ, items = fi.arrays.setdefault(str(arr).lower(), (str(arr), c.type, {}))
                items[info.index] = info
            else:
                fi.controls[c.name.lower()] = info
        return fi


@dataclass
class ModInfo:
    name: str
    kind: str                                         # "bas" | "cls" | "frm"
    members: dict = field(default_factory=dict)       # lower -> (display, what, type, public)
    file: str = ""
    module: object = None                             # vbparse.Module


class ProjectContext:
    """Everything the translators need to know about the whole VB6 project."""

    def __init__(self):
        self.forms: dict[str, FormInfo] = {}
        self.modules: dict[str, ModInfo] = {}          # .bas / .cls / forms' code modules by lower name
        self.casemap: dict[str, str] = {}
        self.title = "Project1"

    def spell(self, lower: str, fallback: str = "") -> str:
        return self.casemap.get(lower.lower(), fallback or lower)

    def public_member(self, lower: str):
        """(ModInfo, display, what, type) of a Public member of a standard module (.bas)."""
        for mi in self.modules.values():
            if mi.kind != "bas":
                continue
            m = mi.members.get(lower)
            if m and m[3]:
                return mi, m[0], m[1], m[2]
        return None

    def is_class(self, lower: str) -> bool:
        mi = self.modules.get(lower)
        return mi is not None and mi.kind == "cls"

    def add_module(self, name: str, kind: str, text: str, file: str = "") -> ModInfo:
        casemap_of(text, self.casemap)
        mi = ModInfo(name, kind, file=file)
        try:
            mod = vbparse.parse_module(text, name, file)
        except vbparse.VBSyntaxError:
            mod = None
        mi.module = mod
        if mod is not None:
            for p in mod.procs.values():
                base = p.name.split(":")[-1]
                what = "proc" if p.kind in ("sub", "function") else "prop"
                mi.members[base] = (strip_suffix(p.display or self.spell(base)), what, p.kind, p.public)
            for d in mod.decls:
                if d[0] in ("dim", "static"):
                    for nm, bounds, typ in d[2]:
                        mi.members[nm] = (self.spell(nm), "array" if bounds is not None else "var", typ, d[3])
                elif d[0] == "const":
                    for nm, _e in d[2]:
                        mi.members[nm] = (self.spell(nm), "const", "", d[3])
                elif d[0] == "enum":
                    mi.members[d[2]] = (self.spell(d[2]), "enum", "", True)
                    for mname, _v in d[3]:
                        mi.members[mname] = (self.spell(mname), "enumval", d[2], True)
                elif d[0] == "type":
                    mi.members[d[2]] = (self.spell(d[2]), "type", "", True)
            for dec in mod.declares:
                mi.members[dec.name] = (self.spell(dec.name), "declare", dec.kind, dec.public)
        self.modules[name.lower()] = mi
        return mi


def read_text(path: Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")
