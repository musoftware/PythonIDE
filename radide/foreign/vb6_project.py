"""Open Visual Basic 6 projects (.vbp) and project groups (.vbg) IN PLACE.

The native files stay authoritative - nothing is written into the user's folder except the
VB6 files themselves (in VB6 format):

* ``VbpFile`` - a .vbp kept as text: ``Form=``/``Module=``/``Class=``/``Reference=``/``Object=`` lines,
  ``Startup``, ``Title``, ``Name``, version keys; only edited lines change (byte-identical otherwise).
* ``NativeVB6`` - the project read from its native files: forms (neutral model via
  ``radide.foreign.frm_writer``), the code sections of the .frm files, modules, classes, user controls,
  related documents, references and components.  ``radide.runtimes.vbrun`` runs a .vbp directly with it.
* The IDE edits a **mirror** of the project under ``%APPDATA%\\RADIDE\\foreign\\vb6-<name>-<hash>``
  (``project.radproj`` + ``<Form>.form`` + ``<Form>.bas`` = code section + module copies).  Every save
  (``sync_mirror``) writes the changes back into the .frm / .frx / .bas / .cls / .vbp files with the
  format-preserving writers (``frm_writer.apply_form_changes``); files nobody changed are not touched.
* ``register()`` adds the formats to ``radide.features.foreign_projects`` (File > Open dispatcher).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..model import Form, Project
from .frm_writer import (dominant_newline, join_code, join_lines, load_form, new_frm_text, split_code,
                         split_lines, vb_str)

STATE_DIR = ".vb6"
FILE_KINDS = ("Form", "Module", "Class", "UserControl", "PropertyPage", "Designer", "UserDocument")
EXT_KIND = {".frm": "Form", ".bas": "Module", ".cls": "Class", ".ctl": "UserControl", ".pag": "PropertyPage",
            ".dsr": "Designer", ".dob": "UserDocument"}
GROUP_TITLES = {"Form": "Forms", "Module": "Modules", "Class": "Class Modules", "UserControl": "User Controls",
                "PropertyPage": "Property Pages", "Designer": "Designers", "UserDocument": "User Documents"}


# ============================================================================ encodings
def decode_vb(raw: bytes, prefer: str | None = None) -> tuple[str, str]:
    """(text, encoding) of a VB6 source file.  VB6 wrote the ANSI code page of the machine
    (cp1252 Western, cp1256 Arabic, ...); the choice is kept so the file is written back the same."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    if prefer:
        try:
            return raw.decode(prefer), prefer
        except (UnicodeDecodeError, LookupError):
            pass
    try:
        return raw.decode("ascii"), "cp1252"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    # runs of 3+ high bytes are words of a non-Latin script (Arabic); Latin text has single accents
    words = len(re.findall(rb"[\xc0-\xff]{3,}", raw))
    singles = len(re.findall(rb"(?<![\x80-\xff])[\x80-\xff](?![\x80-\xff])", raw))
    for enc in (("cp1256", "cp1252") if words > singles else ("cp1252", "cp1256")):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def encode_vb(text: str, encoding: str) -> bytes:
    if encoding == "utf-8-sig":
        return b"\xef\xbb\xbf" + text.encode("utf-8")
    try:
        return text.encode(encoding)
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace")


def to_native_newlines(text: str, newline: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", newline)


def to_mirror_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ============================================================================ .vbp
class VbpFile:
    """A .vbp (or .vbg) as text; edits touch only their own lines."""

    def __init__(self, path: Path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.raw = raw
        text, self.encoding = decode_vb(raw)
        self.lines, self.seps = split_lines(text)
        self.nl = dominant_newline(text) if ("\n" in text or "\r" in text) else "\r\n"
        self.changed = False

    # -- reading
    def _section_end(self) -> int:
        for i, ln in enumerate(self.lines):
            if ln.startswith("["):
                return i
        return len(self.lines)

    def entries(self) -> list[tuple[int, str, str]]:
        out = []
        for i, ln in enumerate(self.lines[:self._section_end()]):
            k, sep, v = ln.partition("=")
            if sep and k.strip():
                out.append((i, k.strip(), v.strip()))
        return out

    def get(self, key: str, default: str = "") -> str:
        k = key.lower()
        for _i, kk, v in self.entries():
            if kk.lower() == k:
                return v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v
        return default

    def values(self, key: str) -> list[tuple[int, str]]:
        k = key.lower()
        return [(i, v) for i, kk, v in self.entries() if kk.lower() == k]

    def text(self) -> str:
        return join_lines(self.lines, self.seps)

    # -- editing
    def _insert(self, at: int, line: str):
        if at > 0 and not self.seps[at - 1]:
            self.seps[at - 1] = self.nl
        self.lines.insert(at, line)
        self.seps.insert(at, self.nl)
        self.changed = True

    def set(self, key: str, value: str, quote: bool = True, after: tuple = ("Name", "Title", "Startup")):
        val = vb_str(value) if quote else str(value)
        k = key.lower()
        for i, kk, v in self.entries():
            if kk.lower() == k:
                new = f"{kk}={val}"
                if self.lines[i] != new:
                    self.lines[i] = new
                    self.changed = True
                return
        ents = self.entries()
        idx = None
        for a in after:
            hits = [i for i, kk, _v in ents if kk.lower() == a.lower()]
            if hits:
                idx = hits[-1] + 1
                break
        if idx is None:
            idx = (ents[-1][0] + 1) if ents else len(self.lines)
        self._insert(idx, f"{key}={val}")

    def remove(self, index: int):
        del self.lines[index]
        del self.seps[index]
        self.changed = True

    def add_file(self, kind: str, value: str):
        ents = self.entries()
        same = [i for i, kk, _v in ents if kk.lower() == kind.lower()]
        if same:
            at = same[-1] + 1
        else:
            files = [i for i, kk, _v in ents if kk in FILE_KINDS or kk in ("Reference", "Object", "Type")]
            at = (max(files) + 1) if files else (1 if ents else 0)
        self._insert(at, f"{kind}={value}")

    def save(self) -> bool:
        if not self.changed:
            return False
        data = encode_vb(self.text(), self.encoding)
        if data != self.raw:
            self.path.write_bytes(data)
            self.raw = data
        self.changed = False
        return True


def vbp_file_entry(kind: str, value: str) -> tuple[str, str]:
    """(VB name, relative path) of a Form=/Module=/Class=/... line value."""
    v = value.strip()
    if ";" in v:
        name, _, rel = v.partition(";")
        return name.strip(), rel.strip().strip('"')
    rel = v.strip('"')
    return Path(rel.replace("\\", "/")).stem, rel


def reference_label(raw: str) -> str:
    """Reference=*\\G{...}#2.0#0#..\\stdole2.tlb#OLE Automation -> OLE Automation (stdole2.tlb)."""
    parts = raw.split("#")
    desc = parts[-1].strip() if len(parts) >= 5 else ""
    lib = Path(parts[-2].replace("\\", "/")).name if len(parts) >= 5 else raw
    return f"{desc} ({lib})" if desc else lib


def object_label(raw: str) -> str:
    """Object={831FDD16-...}#2.0#0; MSCOMCTL.OCX -> MSCOMCTL.OCX."""
    return raw.split(";")[-1].strip().strip('"') if ";" in raw else raw


# ============================================================================ native project
@dataclass
class VB6Item:
    kind: str           # Form | Module | Class | UserControl | ... | RelatedDoc | ResFile32
    name: str           # VB name (Attribute VB_Name)
    rel: str            # as written in the .vbp
    path: Path          # absolute
    line: int = -1      # .vbp line index


@dataclass
class NativeForm:
    name: str
    path: Path
    encoding: str
    text: str
    form: Form | None
    code: str
    warnings: list = field(default_factory=list)


class NativeVB6:
    """A VB6 project read from its native files."""

    def __init__(self, vbp: Path, cache_dir: Path | None = None):
        self.vbp_path = Path(vbp).resolve()
        self.folder = self.vbp_path.parent
        self.vbp = VbpFile(self.vbp_path)
        self.cache_dir = cache_dir
        self.items: list[VB6Item] = []
        for i, k, v in self.vbp.entries():
            if k in FILE_KINDS:
                name, rel = vbp_file_entry(k, v)
                self.items.append(VB6Item(k, name, rel, (self.folder / rel.replace("\\", "/")).resolve(), i))
            elif k in ("RelatedDoc", "ResFile32"):
                rel = v.strip('"')
                self.items.append(VB6Item(k, Path(rel.replace("\\", "/")).name, rel,
                                          (self.folder / rel.replace("\\", "/")).resolve(), i))
        self.forms: dict[str, NativeForm] = {}
        self.warnings: list[str] = []
        for it in self.items:
            if it.kind != "Form":
                continue
            if not it.path.is_file():
                self.warnings.append(f"form file not found: {it.rel}")
                continue
            text, enc = decode_vb(it.path.read_bytes())
            form, info = load_form(text, it.path, cache_dir, enc if enc != "utf-8-sig" else "utf-8")
            _head, code = split_code(text)
            name = form.name if form is not None else it.name
            it.name = name
            self.forms[name.lower()] = NativeForm(name, it.path, enc, text, form, code, info.warnings)
            self.warnings += info.warnings
        for it in self.items:
            if it.kind in ("Module", "Class", "UserControl", "PropertyPage", "Designer", "UserDocument") \
                    and not it.path.is_file():
                self.warnings.append(f"{it.kind.lower()} file not found: {it.rel}")

    # -- info
    @property
    def name(self) -> str:
        return self.vbp.get("Name") or self.vbp_path.stem

    @property
    def startup(self) -> str:
        st = self.vbp.get("Startup")
        if st.lower() in ("sub main", ""):
            return "Sub Main" if st else (next(iter(self.forms.values())).name if self.forms else "")
        f = self.forms.get(st.lower())
        return f.name if f else st

    @property
    def title(self) -> str:
        return self.vbp.get("Title") or self.name

    def references(self) -> list[str]:
        return [v for _i, v in self.vbp.values("Reference")]

    def objects(self) -> list[str]:
        return [v for _i, v in self.vbp.values("Object")]

    def form_names(self) -> list[str]:
        return [f.name for f in self.forms.values() if f.form is not None]

    def code_items(self) -> list[VB6Item]:
        """Modules, classes, user controls, ... (files edited as a whole)."""
        return [it for it in self.items if it.kind in FILE_KINDS and it.kind != "Form" and it.path.is_file()]

    def mirror_names(self) -> dict[str, VB6Item]:
        """file name used for each code item in the IDE (its own file name, made unique)."""
        out: dict[str, VB6Item] = {}
        taken = {f"{n}.bas".lower() for n in self.form_names()} | {f"{n}.frm".lower() for n in self.form_names()} \
            | {f"{n}.form".lower() for n in self.form_names()}
        for it in self.code_items():
            nm = it.path.name
            base, ext = os.path.splitext(nm)
            k = 2
            while nm.lower() in taken or nm.lower() == "project.radproj":
                nm = f"{base}_{k}{ext}"
                k += 1
            taken.add(nm.lower())
            out[nm] = it
        return out

    # -- for the runtime (radide.runtimes.vbrun)
    def project(self) -> Project:
        mods = [m for m in self.mirror_names()]
        return Project(self.folder, re.sub(r"\W", "_", self.name) or "Project1", "vb-basic",
                       self.form_names(), self.startup, mods)

    def form(self, name: str) -> Form:
        return self.forms[name.lower()].form

    def form_code(self, name: str) -> str:
        return self.forms[name.lower()].code

    def module_path(self, mirror_name: str) -> Path:
        return self.mirror_names()[mirror_name].path

    def module_text(self, mirror_name: str) -> str:
        it = self.mirror_names()[mirror_name]
        return to_mirror_text(decode_vb(it.path.read_bytes())[0])


# ============================================================================ mirror (the IDE's view)
def state_root() -> Path:
    env = os.environ.get("RADIDE_FOREIGN_STATE")
    if env:
        return Path(env)
    return Path(os.environ.get("APPDATA") or str(Path.home())) / "RADIDE" / "foreign"


def mirror_dir_for(path: Path) -> Path:
    p = Path(path).resolve()
    h = hashlib.sha1(os.path.normcase(str(p)).encode("utf-8")).hexdigest()[:10]
    stem = re.sub(r"[^\w.-]", "_", p.stem)[:40] or "project"
    return state_root() / f"vb6-{stem}-{h}"


def is_mirror(folder) -> bool:
    try:
        return (Path(folder) / STATE_DIR / "state.json").is_file()
    except (OSError, TypeError):
        return False


def _state(mdir: Path) -> dict:
    return json.loads((Path(mdir) / STATE_DIR / "state.json").read_text(encoding="utf-8"))


def _save_state(mdir: Path, st: dict) -> None:
    (Path(mdir) / STATE_DIR / "state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")


def native_project_file(folder) -> Path | None:
    """The .vbp a mirror folder stands for (None for other folders)."""
    if not is_mirror(folder):
        return None
    return Path(_state(Path(folder))["vbp"])


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_mirror(vbp: Path, mdir: Path | None = None) -> tuple[Path, NativeVB6]:
    """(Re)create the IDE mirror of a .vbp from its native files.  Returns (mirror folder, project)."""
    vbp = Path(vbp).resolve()
    mdir = Path(mdir) if mdir else mirror_dir_for(vbp)
    if mdir.exists():
        shutil.rmtree(mdir, ignore_errors=True)
    base = mdir / STATE_DIR / "base"
    base.mkdir(parents=True, exist_ok=True)
    native = NativeVB6(vbp, mdir / STATE_DIR / "frxcache")
    from ..languages import get_plugin
    plugin = get_plugin("vb-basic")
    st = {"vbp": str(vbp), "forms": {}, "modules": {}, "startup": native.startup, "name": native.name,
          "encoding": native.vbp.encoding}
    for nf in native.forms.values():
        if nf.form is None:
            continue
        nf.form.save(mdir / f"{nf.name}.form")
        nf.form.save(base / f"{nf.name}.form")
        _write(mdir / f"{nf.name}.bas", nf.code)
        _write(base / f"{nf.name}.bas", nf.code)
        _write(mdir / f"{nf.name}.frm", plugin.generate_designer(nf.form, nf.code))
        st["forms"][nf.name] = {"path": str(nf.path), "encoding": nf.encoding}
    for mname, it in native.mirror_names().items():
        text, enc = decode_vb(it.path.read_bytes())
        mt = to_mirror_text(text)
        _write(mdir / mname, mt)
        _write(base / mname, mt)
        st["modules"][mname] = {"path": str(it.path), "kind": it.kind, "name": it.name, "encoding": enc,
                                "newline": dominant_newline(text) if "\n" in text or "\r" in text else "\r\n"}
    project = native.project()
    project.folder = mdir
    project.extra["foreign"] = {"kind": "vb6", "project_file": str(vbp)}
    project.save()
    _save_state(mdir, st)
    return mdir, native


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _module_vb_name(text: str, fallback: str) -> str:
    m = re.search(r'^\s*Attribute\s+VB_Name\s*=\s*"([^"]+)"', text, re.I | re.M)
    return m.group(1) if m else fallback


def _free_native_path(folder: Path, filename: str, mine: set) -> Path:
    p = folder / filename
    stem, ext = os.path.splitext(filename)
    k = 2
    while p.exists() and os.path.normcase(str(p)) not in mine:
        p = folder / f"{stem}{k}{ext}"
        k += 1
    return p


def _rel(path: Path, folder: Path) -> str:
    try:
        return os.path.relpath(path, folder).replace("/", "\\")
    except ValueError:
        return str(path)


def sync_mirror(mdir: Path) -> list[str]:
    """Write the IDE's changes in the mirror back into the native VB6 files.
    Returns messages (files written, notes).  Files without changes are not touched."""
    mdir = Path(mdir)
    st = _state(mdir)
    vbp_path = Path(st["vbp"])
    vbp = VbpFile(vbp_path)
    folder = vbp_path.parent
    base = mdir / STATE_DIR / "base"
    project = Project.load(mdir)
    msgs: list[str] = []
    enc_default = st.get("encoding") or "cp1252"
    nl = vbp.nl
    # ---------------------------------------------------------------- forms
    known = dict(st["forms"])
    gone = [n for n in known if n not in project.forms]
    fresh = [n for n in project.forms if n not in known]
    for old in list(gone):                      # Rename (VB6 keeps the file name)
        if fresh and (base / f"{old}.form").is_file():
            new = fresh.pop(0)
            known[new] = known.pop(old)
            gone.remove(old)
            for ext in (".form", ".bas"):
                src = base / f"{old}{ext}"
                if src.exists():
                    src.replace(base / f"{new}{ext}")
            if st.get("startup", "").lower() == old.lower() and project.startup == new:
                st["startup_renamed_from"] = old
    mine = {os.path.normcase(v["path"]) for v in known.values()} | \
        {os.path.normcase(v["path"]) for v in st["modules"].values()}
    for name in project.forms:
        fpath = mdir / f"{name}.form"
        if not fpath.is_file():
            continue
        now = Form.load(fpath)
        code = _read(mdir / f"{name}.bas")
        entry = known.get(name)
        if entry is None:                                    # Add Form: a new .frm in VB6 format
            target = _free_native_path(folder, f"{name}.frm", mine)
            text, libs = new_frm_text(now, code, nl, target, enc_default)
            target.write_bytes(encode_vb(text, enc_default))
            vbp.add_file("Form", _rel(target, folder))
            for lib in libs:
                _ensure_object(vbp, lib)
            known[name] = {"path": str(target), "encoding": enc_default}
            mine.add(os.path.normcase(str(target)))
            now.save(base / f"{name}.form")
            _write(base / f"{name}.bas", code)
            msgs.append(f"added {target.name} to {vbp_path.name}")
            continue
        bform = Form.load(base / f"{name}.form") if (base / f"{name}.form").is_file() else now
        bcode = _read(base / f"{name}.bas")
        if bform.snapshot() == now.snapshot() and code == bcode:
            continue
        npath = Path(entry["path"])
        raw = npath.read_bytes()
        text, enc = decode_vb(raw, entry.get("encoding"))
        from .frm_writer import apply_form_changes
        new_text, notes, libs = apply_form_changes(text, bform, now, npath,
                                                   enc if enc != "utf-8-sig" else "utf-8")
        msgs += [f"{npath.name}: {n}" for n in notes]
        if code != bcode:
            head, _old_code = split_code(new_text)
            new_text = join_code(head, code, dominant_newline(text))
        for lib in libs:
            _ensure_object(vbp, lib)
        data = encode_vb(new_text, enc)
        if data != raw:
            npath.write_bytes(data)
            msgs.append(f"wrote {npath.name}")
        now.save(base / f"{name}.form")
        _write(base / f"{name}.bas", code)
    for name in gone:                                        # removed from the project (file kept)
        p = os.path.normcase(known[name]["path"])
        for i, v in vbp.values("Form"):
            if os.path.normcase(str((folder / vbp_file_entry("Form", v)[1].replace("\\", "/")).resolve())) == p:
                vbp.remove(i)
                msgs.append(f"removed Form {name} from {vbp_path.name} (file kept)")
                break
        known.pop(name, None)
    st["forms"] = known
    # ---------------------------------------------------------------- modules / classes / ...
    mods = dict(st["modules"])
    for m in project.modules:
        mp = mdir / m
        if not mp.is_file():
            continue
        text = _read(mp)
        entry = mods.get(m)
        if entry is None:                                    # Add Module / Class
            kind = EXT_KIND.get(Path(m).suffix.lower(), "Module")
            target = _free_native_path(folder, Path(m).name, mine)
            target.write_bytes(encode_vb(to_native_newlines(text, nl), enc_default))
            vbname = _module_vb_name(text, Path(m).stem)
            rel = _rel(target, folder)
            vbp.add_file(kind, f"{vbname}; {rel}" if kind in ("Module", "Class") else rel)
            mods[m] = {"path": str(target), "kind": kind, "name": vbname, "encoding": enc_default, "newline": nl}
            mine.add(os.path.normcase(str(target)))
            _write(base / m, text)
            msgs.append(f"added {target.name} to {vbp_path.name}")
            continue
        if text == _read(base / m):
            continue
        npath = Path(entry["path"])
        data = encode_vb(to_native_newlines(text, entry.get("newline") or nl), entry.get("encoding") or enc_default)
        if not npath.exists() or npath.read_bytes() != data:
            npath.write_bytes(data)
            msgs.append(f"wrote {npath.name}")
        _write(base / m, text)
    for m in [m for m in mods if m not in project.modules]:
        p = os.path.normcase(mods[m]["path"])
        kind = mods[m]["kind"]
        for i, v in vbp.values(kind):
            if os.path.normcase(str((folder / vbp_file_entry(kind, v)[1].replace("\\", "/")).resolve())) == p:
                vbp.remove(i)
                msgs.append(f"removed {kind} {mods[m]['name']} from {vbp_path.name} (file kept)")
                break
        mods.pop(m)
    st["modules"] = mods
    # ---------------------------------------------------------------- project properties
    if (project.startup or "") != (st.get("startup") or ""):
        stv = project.startup or ""
        if stv:
            vbp.set("Startup", "Sub Main" if stv.lower() in ("sub main", "main") else stv)
            st["startup"] = stv
            msgs.append(f"Startup = {stv}")
    st.pop("startup_renamed_from", None)
    if vbp.save():
        msgs.append(f"wrote {vbp_path.name}")
    _save_state(mdir, st)
    return msgs


def _ensure_object(vbp: VbpFile, lib: str) -> None:
    if lib.startswith("ctl:"):          # a component package written as a UserControl: its .ctl stand-in
        _ensure_usercontrol(vbp, lib[4:])
        return
    from .frm_writer import object_of
    obj = object_of(lib)
    if obj is None:
        return
    guid, ocx = obj
    if not any(guid.lower() in v.lower() for _i, v in vbp.values("Object")):
        vbp.add_file("Object", f"{guid}; {ocx}")


def _ensure_usercontrol(vbp: VbpFile, type_name: str) -> None:
    """<Type>.ctl next to the .vbp (written once; radide.components.vb6map.usercontrol_source) and its
    ``UserControl=`` line, so VB6 loads a form whose component control is ``Begin <Project>.<Type>``."""
    from ..components.vb6map import usercontrol_source
    folder = Path(vbp.path).parent
    ctl = folder / f"{type_name}.ctl"
    if not any(Path(vbp_file_entry("UserControl", v)[1].replace("\\", "/")).stem.lower() == type_name.lower()
               for _i, v in vbp.values("UserControl")):
        if not ctl.exists():
            ctl.write_bytes(encode_vb(usercontrol_source(type_name, vbp.nl), "cp1252"))
        vbp.add_file("UserControl", ctl.name)


def set_project_properties(mdir: Path, **props) -> list[str]:
    """Edit .vbp keys (Name, Title, Startup, ExeName32, MajorVer, MinorVer, RevisionVer, Description)
    and keep the mirror in step."""
    mdir = Path(mdir)
    st = _state(mdir)
    vbp = VbpFile(Path(st["vbp"]))
    quoted = {"Name", "Title", "Startup", "ExeName32", "Description", "HelpFile", "Command32"}
    for k, v in props.items():
        if v is None:
            continue
        vbp.set(k, str(v), quote=k in quoted)
    msgs = [f"wrote {vbp.path.name}"] if vbp.save() else []
    project = Project.load(mdir)
    if props.get("Startup"):
        project.startup = "Sub Main" if props["Startup"].lower() == "sub main" else props["Startup"]
        st["startup"] = project.startup
    if props.get("Name"):
        st["name"] = props["Name"]
    project.save()
    _save_state(mdir, st)
    return msgs


# ============================================================================ .vbg groups
def parse_vbg(path: Path) -> tuple[list[Path], Path | None]:
    """(project files, startup project) of a VB6 project group."""
    v = VbpFile(path)
    projects, startup = [], None
    for _i, k, val in v.entries():
        if k.lower() in ("project", "startupproject"):
            p = (Path(path).parent / val.strip('"').replace("\\", "/")).resolve()
            projects.append(p)
            if k.lower() == "startupproject":
                startup = p
    return projects, startup


def build_group_mirror(vbg: Path) -> Path:
    """A RAD solution (.radsln) in the state folder with one mirror per project of the group."""
    from ..solution import Solution, SolutionProject
    vbg = Path(vbg).resolve()
    root = mirror_dir_for(vbg)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    projects, startup = parse_vbg(vbg)
    entries, start_name, used = [], "", set()
    for i, p in enumerate(projects):
        if not p.is_file():
            continue
        mdir, native = build_mirror(p, root / f"{i + 1:02d}-{re.sub(r'[^\w.-]', '_', p.stem)}")
        name = re.sub(r"\W", "_", native.name) or p.stem
        while name.lower() in used:
            name += "_"
        used.add(name.lower())
        entries.append(SolutionProject(name, mdir.name))
        if startup is not None and p == startup:
            start_name = name
    sln = Solution(vbg.stem, root, entries, start_name or (entries[0].name if entries else ""))
    sln.save()
    (root / ".vbg").write_text(str(vbg), encoding="utf-8")
    return sln.file


# ============================================================================ IDE integration
def _log(win, text):
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def sync_project_of(win, project) -> list[str]:
    if project is None or not is_mirror(project.folder):
        return []
    try:
        msgs = sync_mirror(Path(project.folder))
    except Exception as e:  # noqa: BLE001 - never lose the IDE's own save
        import traceback
        _log(win, f"*** VB6: could not write back {project.name}: {e}\n{traceback.format_exc()}")
        return []
    for m in msgs:
        _log(win, f"[VB6] {m}")
    return msgs


def install_hooks(win) -> None:
    """Save write-back, Solution Explorer like VB6, VB6 project properties - once per window."""
    if getattr(win, "_vb6_hooks", False):
        return
    win._vb6_hooks = True
    orig_save_proj = win._save_active_project
    orig_save_current = win.save_current
    orig_fill = win._fill_solution
    orig_props = win.project_properties

    def save_active():
        wrote = orig_save_proj()
        sync_project_of(win, win.project)
        return wrote

    def save_current():
        ok = orig_save_current()
        sync_project_of(win, win.project)
        return ok

    def fill():
        orig_fill()
        try:
            decorate_tree(win)
        except Exception as e:  # noqa: BLE001
            _log(win, f"[VB6] Solution Explorer: {e}")

    def props():
        if win.project is not None and is_mirror(win.project.folder):
            return project_properties_dialog(win)
        return orig_props()
    win._save_active_project = save_active
    win.save_current = save_current
    win._fill_solution = fill
    win.project_properties = props
    try:
        win.solution.customContextMenuRequested.disconnect(win._solution_menu)
    except (TypeError, RuntimeError):
        pass
    win.solution.customContextMenuRequested.connect(lambda pos: _context_menu(win, pos))
    win.solution.itemDoubleClicked.connect(lambda item, _c: _on_dclick(win, item))


def _project_items(win):
    from ..features.solution_ui import PROJECT_ROLE, ROLE
    tree = win.solution
    for i in range(tree.topLevelItemCount()):
        root = tree.topLevelItem(i)
        for j in range(root.childCount()):
            pi = root.child(j)
            data = pi.data(0, ROLE)
            key = pi.data(0, PROJECT_ROLE)
            if data and data[0] == "project" and key in win._pstates:
                yield pi, win._pstates[key]["project"], key


def decorate_tree(win) -> None:
    """Regroup a VB6 project's Solution Explorer items the way VB6 shows them."""
    from PyQt6.QtWidgets import QTreeWidgetItem

    from ..features.solution_ui import PROJECT_ROLE, ROLE
    style = win.style()
    from PyQt6.QtWidgets import QStyle
    folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
    file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    link_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)
    for pi, project, key in list(_project_items(win)):
        if not is_mirror(project.folder):
            continue
        st = _state(Path(project.folder))
        vbp = Path(st["vbp"])
        pi.setText(0, f"{project.name} ({vbp.name})")
        pi.setToolTip(0, f"Visual Basic 6 project - opened in place\n{vbp}")
        kids = [pi.child(k) for k in range(pi.childCount())]
        groups: dict[str, QTreeWidgetItem] = {}

        def group(title, kind):
            if title not in groups:
                g = QTreeWidgetItem([title])
                g.setData(0, ROLE, ("vb6group", kind))
                g.setData(0, PROJECT_ROLE, key)
                g.setIcon(0, folder_icon)
                groups[title] = g
            return groups[title]
        order = []
        for it in kids:
            data = it.data(0, ROLE) or ("", "")
            if data[0] == "references":
                if it.childCount() == 0:
                    pi.removeChild(it)
                else:
                    it.setText(0, "Solution References")
                continue
            pi.removeChild(it)
            if data[0] == "design":
                form = data[1]
                entry = st["forms"].get(form)
                fname = Path(entry["path"]).name if entry else f"{form}.frm"
                it.setText(0, f"{form} ({fname})" + ("   (startup)" if form == project.startup else ""))
                for c in [it.child(k) for k in range(it.childCount())]:
                    cd = c.data(0, ROLE) or ("", "")
                    if cd[0] == "generated":
                        it.removeChild(c)
                    elif cd[0] == "code":
                        c.setText(0, f"{form} (Code)")
                group("Forms", "Form").addChild(it)
                order.append("Forms")
            elif data[0] == "module":
                entry = st["modules"].get(data[1])
                kind = entry["kind"] if entry else EXT_KIND.get(Path(data[1]).suffix.lower(), "Module")
                vbname = entry["name"] if entry else Path(data[1]).stem
                fname = Path(entry["path"]).name if entry else data[1]
                it.setText(0, f"{vbname} ({fname})")
                title = GROUP_TITLES.get(kind, "Modules")
                group(title, kind).addChild(it)
                order.append(title)
            else:
                pi.addChild(it)
        for title in ("Forms", "Modules", "Class Modules", "User Controls", "Property Pages", "Designers",
                      "User Documents"):
            if title in groups:
                pi.addChild(groups[title])
        try:
            native = VbpFile(vbp)
        except OSError:
            continue
        docs = [(k, v) for _i, k, v in native.entries() if k in ("RelatedDoc", "ResFile32")]
        if docs:
            g = group("Related Documents", "RelatedDoc")
            for _k, v in docs:
                rel = v.strip('"')
                d = QTreeWidgetItem(g, [Path(rel.replace("\\", "/")).name])
                d.setData(0, ROLE, ("vb6doc", str((vbp.parent / rel.replace("\\", "/")).resolve())))
                d.setData(0, PROJECT_ROLE, key)
                d.setIcon(0, file_icon)
            pi.addChild(g)
        refs = [v for _i, v in native.values("Reference")]
        if refs:
            g = group("References", "Reference")
            for v in refs:
                r = QTreeWidgetItem(g, [reference_label(v)])
                r.setToolTip(0, v)
                r.setData(0, ROLE, ("vb6ref", v))
                r.setData(0, PROJECT_ROLE, key)
                r.setIcon(0, link_icon)
            pi.addChild(g)
        objs = [v for _i, v in native.values("Object")]
        if objs:
            g = group("Components", "Object")
            for v in objs:
                o = QTreeWidgetItem(g, [object_label(v)])
                o.setToolTip(0, v)
                o.setData(0, ROLE, ("vb6obj", v))
                o.setData(0, PROJECT_ROLE, key)
                o.setIcon(0, link_icon)
            pi.addChild(g)
        pi.setExpanded(True)
        for g in groups.values():
            g.setExpanded(g.text(0) not in ("References", "Components"))


def _item_project(win, item):
    from ..features.solution_ui import PROJECT_ROLE
    key = item.data(0, PROJECT_ROLE) if item is not None else None
    st = win._pstates.get(key) if key else None
    return st["project"] if st else None


def _on_dclick(win, item) -> None:
    from ..features.solution_ui import ROLE
    data = item.data(0, ROLE) if item is not None else None
    if not data or data[0] != "vb6doc":
        return
    p = Path(data[1])
    if p.suffix.lower() in (".txt", ".md", ".ini", ".log", ".bas", ".cls", ".htm", ".html", ".xml", ".csv"):
        win.open_any_file(p)
    elif p.exists():
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]
        except OSError as e:
            _log(win, f"[VB6] cannot open {p}: {e}")


def _context_menu(win, pos) -> None:
    from PyQt6.QtWidgets import QMenu

    from ..features.solution_ui import ROLE
    item = win.solution.itemAt(pos)
    project = _item_project(win, item)
    data = item.data(0, ROLE) if item is not None else None
    vb6 = project is not None and is_mirror(project.folder)
    if not vb6 or not data or data[0] not in ("vb6group", "vb6doc", "vb6ref", "vb6obj", "project"):
        win._solution_menu(pos)
        return
    win.activate_project(project)
    m = QMenu(win)
    add = m.addMenu("Add")
    add.addAction("Form...", win.add_form)
    add.addAction("Module...", win.add_module)
    add.addAction("Class Module...", lambda: add_class_dialog(win))
    add.addAction("Existing File...", win.add_existing)
    m.addSeparator()
    if data[0] == "project":
        m.addAction(win.a_run)
        m.addAction("Save Project", win.save_all)
        m.addSeparator()
    m.addAction("Open Folder in File Explorer",
                lambda: os.startfile(str(Path(_state(Path(project.folder))["vbp"]).parent)))  # type: ignore
    m.addAction(f"Open {Path(_state(Path(project.folder))['vbp']).name} as Text",
                lambda: win.open_any_file(Path(_state(Path(project.folder))["vbp"])))
    m.addSeparator()
    m.addAction("Project Properties...", lambda: project_properties_dialog(win))
    m.exec(win.solution.viewport().mapToGlobal(pos))


CLASS_TEMPLATE = """VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "{name}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

"""


def add_class(win, name: str) -> str:
    """Add Class Module: <name>.cls in the mirror; the next save writes it and its Class= line."""
    from ..workspace import add_module
    project = win.project
    filename = f"{name}.cls"
    (Path(project.folder) / filename).write_text(CLASS_TEMPLATE.format(name=name), encoding="utf-8")
    add_module(project, name, filename=filename)
    sync_project_of(win, project)
    win._fill_solution()
    win.open_module(filename)
    return filename


def add_class_dialog(win) -> None:
    from PyQt6.QtWidgets import QInputDialog
    taken = {Path(m).stem.lower() for m in win.project.modules}
    k = 1
    while f"class{k}" in taken:
        k += 1
    name, ok = QInputDialog.getText(win, "Add Class Module", "Class name:", text=f"Class{k}")
    if ok and re.fullmatch(r"[A-Za-z_]\w*", name or ""):
        add_class(win, name)


def project_properties_dialog(win, exec_: bool = True):
    """VB6 Project Properties (General / Make): written back into the .vbp."""
    from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox
    project = win.project
    mdir = Path(project.folder)
    vbp = VbpFile(Path(_state(mdir)["vbp"]))
    dlg = QDialog(win)
    dlg.setWindowTitle(f"{project.name} - Project Properties")
    lay = QFormLayout(dlg)
    lay.addRow("Project file:", QLabel(str(vbp.path)))
    lay.addRow("Project type:", QLabel(vbp.get("Type", "Exe")))
    name = QLineEdit(vbp.get("Name", project.name))
    startup = QComboBox()
    startup.addItems([*project.forms, "Sub Main"])
    startup.setCurrentText("Sub Main" if (project.startup or "").lower() == "sub main" else project.startup)
    title = QLineEdit(vbp.get("Title", project.name))
    exe = QLineEdit(vbp.get("ExeName32", f"{project.name}.exe"))
    desc = QLineEdit(vbp.get("Description", ""))
    vers = []
    for key in ("MajorVer", "MinorVer", "RevisionVer"):
        sb = QSpinBox()
        sb.setRange(0, 9999)
        try:
            sb.setValue(int(vbp.get(key, "0") or 0))
        except ValueError:
            pass
        vers.append((key, sb))
    lay.addRow("Project Name:", name)
    lay.addRow("Startup Object:", startup)
    lay.addRow("Title (App.Title):", title)
    lay.addRow("Exe name:", exe)
    lay.addRow("Description:", desc)
    for key, sb in vers:
        lay.addRow({"MajorVer": "Version Major:", "MinorVer": "Minor:", "RevisionVer": "Revision:"}[key], sb)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    dlg.fields = {"Name": name, "Startup": startup, "Title": title, "ExeName32": exe, "Description": desc,
                  **dict(vers)}

    def apply():
        props = {}
        for k, w in dlg.fields.items():
            new = w.currentText() if isinstance(w, QComboBox) else str(w.value()) if isinstance(w, QSpinBox) \
                else w.text()
            old = vbp.get(k, "")
            if k == "Startup":
                old = "Sub Main" if (project.startup or "").lower() == "sub main" else project.startup
            if new != old and (new or old):
                props[k] = new
        if not props:
            return []
        win.save_all()
        msgs = set_project_properties(mdir, **props)
        if "Startup" in props:
            project.startup = "Sub Main" if props["Startup"].lower() == "sub main" else props["Startup"]
        for m in msgs:
            _log(win, f"[VB6] {m}")
        win._fill_solution()
        return msgs
    dlg.apply = apply
    if exec_ and dlg.exec():
        apply()
    return dlg


def open_vb6(win, path: Path) -> bool:
    """File > Open of a .vbp / .vbg: build the mirror and open it in the IDE."""
    path = Path(path).resolve()
    if not win._confirm_close_project():
        return True                                  # the user kept the open solution
    if win.project is not None:
        win.stop_project()
        win._reset()                                 # the mirror may be the open project: rebuilt below
        win.sln, win.project, win.plugin = None, None, None
    if path.suffix.lower() == ".vbg":
        target = build_group_mirror(path)
        warnings = []
    else:
        mdir, native = build_mirror(path)
        target = mdir
        warnings = native.warnings
    install_hooks(win)
    win.open_project(target, ask=False)
    if win.project is None or not is_mirror(win.project.folder):
        return False
    _log(win, f"Opened Visual Basic 6 {'group' if path.suffix.lower() == '.vbg' else 'project'} {path} in place "
              "(saving writes the VB6 files back; IDE state lives in " f"{state_root()})")
    for w in warnings:
        _log(win, f"[VB6] {w}")
    try:
        win._remember(path)
    except Exception:  # noqa: BLE001
        pass
    return True


def probe_folder(folder: Path):
    try:
        vbg = sorted(Path(folder).glob("*.vbg"))
        if vbg:
            return vbg[0]
        vbp = sorted(Path(folder).glob("*.vbp"))
        return vbp[0] if vbp else None
    except OSError:
        return None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".vbp", ".vbg"], open_vb6, "Visual Basic 6 project / group",
                    folder_probe=probe_folder, name="vb6", priority=10)
