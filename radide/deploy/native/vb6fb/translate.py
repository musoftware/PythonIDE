"""VB6 code of a RAD IDE "VB6 (BASIC)" project -> one readable FreeBASIC program.

The VB source is parsed with the IDE's own parser (radide/runtimes/vbparse.py) and translated with static
types: Integer/Long/Double/String/Boolean/Date variables become FreeBASIC variables of the same kind
(Integer -> Long like the IDE's interpreter, which does not overflow at 32767; Boolean -> VBBool = Long
-1/0; Date -> Double serial), Variant and undeclared variables become RVar (rt/vbrt_core.bi).

Errors: the runtime raises VB errors by setting vbErrPending; the generated code checks it after every
statement that can fail and jumps to the procedure's handler (On Error GoTo / Resume Next) or returns to
the caller, so an error travels up exactly like in VB; an event procedure that ends with an error shows
the "Run-time error" box (like the IDE's runtime) and the program keeps running.

Anything that cannot be translated is reported as "file(line): reason" - the native build then falls
back to the IDE's VB runtime and lists those reasons.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ....model import Form, Project
from ....runtimes.vbparse import Module, Param, Proc, VBSyntaxError, parse_module, tokenize
from . import forms as F
from .forms import fb_str
from .symbols import reserved

NUMERIC = {"i", "f", "b", "d"}

VB_TYPES = {
    "integer": ("Long", "i"), "long": ("Long", "i"), "byte": ("UByte", "i"), "longlong": ("LongInt", "i"),
    "longptr": ("Long", "i"), "single": ("Single", "f"), "double": ("Double", "f"), "currency": ("Double", "f"),
    "decimal": ("Double", "f"), "string": ("String", "s"), "boolean": ("VBBool", "b"), "date": ("Double", "d"),
    "variant": ("RVar", "v"), "any": ("RVar", "v"), "collection": ("VBCollection", "coll"),
    "new:collection": ("VBCollection", "coll"),
}
TAG_FB = {"i": "Long", "f": "Double", "s": "String", "b": "VBBool", "d": "Double", "v": "RVar"}

VB_CONSTANTS = {
    "vbcrlf": ("(Chr(13, 10))", "s"), "vbnewline": ("(Chr(13, 10))", "s"), "vbcr": ("Chr(13)", "s"),
    "vblf": ("Chr(10)", "s"), "vbtab": ("Chr(9)", "s"), "vbnullstring": ('""', "s"), "vbnullchar": ("Chr(0)", "s"),
    "vbback": ("Chr(8)", "s"), "vbformfeed": ("Chr(12)", "s"), "vbverticaltab": ("Chr(11)", "s"),
}
try:
    from ....runtimes.vbinterp import CONSTANTS as _IC
    for _k, _v in _IC.items():
        if _k not in VB_CONSTANTS and isinstance(_v, (int, float)) and not isinstance(_v, bool):
            VB_CONSTANTS[_k] = (str(int(_v)) if float(_v).is_integer() else repr(_v), "i" if float(_v).is_integer() else "f")
except Exception:  # noqa: BLE001
    pass
VB_CONSTANTS.update({"true": ("VBTrue", "b"), "false": ("VBFalse", "b")})


class Unsupported(Exception):
    def __init__(self, msg, line=0):
        super().__init__(msg)
        self.msg, self.line = msg, line


@dataclass
class E:
    """A translated expression: FreeBASIC code + its type tag."""
    code: str
    t: str                       # i f s b d v | coll | udt:Name | ctl | carr | form | arr | obj:<name> | none
    ctl: object = None           # CtlInfo, ctl id code for "ctl"
    idcode: str = ""
    form: object = None          # FormInfo for "form"
    var: object = None           # VarInfo for arrays / lvalues
    lval: bool = False


@dataclass
class VarInfo:
    name: str
    fb: str
    vbtype: str
    tag: str
    fbtype: str
    dims: list | None = None     # None scalar, [] dynamic array, [(lo, hi), ...] fixed
    scope: str = "local"         # local | param | module | global | const
    byref: bool = True
    const_code: str = ""


@dataclass
class ProcInfo:
    name: str
    fb: str
    kind: str                    # sub | function
    params: list
    ret: VarInfo | None
    mod: "ModInfo"
    proc: Proc
    public: bool = True


@dataclass
class ModInfo:
    name: str
    filename: str
    mod: Module
    form: object = None          # FormInfo of a form module
    vars: dict = field(default_factory=dict)
    procs: dict = field(default_factory=dict)
    spell: dict = field(default_factory=dict)
    explicit: bool = False
    cls: object = None           # ClassInfo of a class module


@dataclass
class Translation:
    source: str = ""                              # the FreeBASIC program
    reasons: list = field(default_factory=list)   # "file(line): why" - not translatable
    line_map: dict = field(default_factory=dict)  # generated line (1-based) -> (vb file, vb line)
    images: list = field(default_factory=list)    # picture files to embed (project-relative)
    title: str = ""
    uses_forms: bool = False
    icon: str = ""                                # the startup form's Icon (exe icon when Publish has none)
    notes: list = field(default_factory=list)     # how motion the native runtime cannot draw exactly is shown


CLASSES: dict = {}          # class lower name -> FreeBASIC type name (set by the Translator being run)


def _tag_of(vbtype: str, types: dict, enums: set) -> tuple[str, str] | None:
    t = (vbtype or "variant").lower()
    if t.startswith("new:") and t[4:] in CLASSES:
        t = t[4:]
    if t in VB_TYPES:
        return VB_TYPES[t]
    if t in enums:
        return ("Long", "i")
    if t in types:
        return (types[t], "udt:" + t)
    if t in CLASSES:
        return (CLASSES[t] + " Ptr", "obj:" + t)
    return None


@dataclass
class ClassInfo:
    name: str                    # VB class name (spelling of the source)
    fb: str                      # FreeBASIC type
    mi: "ModInfo"
    props: dict = field(default_factory=dict)     # lower name -> {"get": ProcInfo, "let": ..., "set": ...}


class Translator:
    def __init__(self, folder: Path, project: Project | None = None, fb_root: str | None = None, cfg=None):
        self.folder = Path(folder)
        self.project = project or Project.load(self.folder)
        self.cfg = cfg
        self.macros, self.globals_ = reserved(fb_root)
        self.reasons: list[str] = []
        self.out: list[str] = []
        self.line_map: dict = {}
        self.mods: list[ModInfo] = []
        self.forms: list[F.FormInfo] = []
        self.form_by_name: dict = {}
        self.types: dict = {}          # udt lower -> fb name
        self.udt_fields: dict = {}     # udt lower -> {field lower: VarInfo}
        self.enums: set = set()
        self.enum_members: dict = {}   # enum lower -> {member lower: const code}
        self.gvars: dict = {}          # public module-level vars / consts / enum members
        self.gprocs: dict = {}
        self.images: list = []
        self.used_fb: set = set()
        self.handlers: dict = {}       # form lower -> {ctl lower|'': {event: wrapper}}
        self.autonew: list[str] = []   # module-level "As New" objects created at the start
        self.classes: dict = {}
        self.wrappers: list[str] = []
        self.uses_fx = False           # BeginAnimation / GoToState ... in the code (rt/vbrt_motion.bi)

    # ------------------------------------------------------------------ helpers
    def reason(self, mod, line, msg):
        fn = mod.filename if isinstance(mod, ModInfo) else str(mod)
        r = f"{fn}({line}): {msg}" if line else f"{fn}: {msg}"
        if r not in self.reasons:
            self.reasons.append(r)

    def safe(self, raw: str, *, local=False) -> str:
        n = re.sub(r"[$%&!#@]$", "", raw)
        if not n.isascii():     # FreeBASIC names are ASCII: sayı -> sayi, محمد -> u645_u62d_u645_u62f
            from ....runtimes.vbparse import id_key
            n = "".join(ch if ch.isascii() else f"u{ord(ch):x}_" for ch in id_key(n)).rstrip("_") or "u_"
            if n[0].isdigit():
                n = "u" + n
        low = n.lower()
        if low in self.macros or (not local and low in self.globals_) or low.startswith("vb_") or \
                low.startswith(("vbx", "rv_")):
            n += "_"
        return n

    def uniq(self, name: str) -> str:
        base, k = name, 2
        while name.lower() in self.used_fb:
            name = f"{base}{k}"
            k += 1
        self.used_fb.add(name.lower())
        return name

    def spell(self, mi: ModInfo, low: str) -> str:
        return mi.spell.get(low, low)

    # ------------------------------------------------------------------ loading
    def load(self):
        p = self.project
        lang = getattr(p, "form_language", lambda _n: p.language)
        forms = []
        for name in p.forms:
            if lang(name) != "vb-basic":
                self.reasons.append(f"{name}: a form in another language ({lang(name)}) - multi-language projects "
                                    "run on the IDE's runtime")
                continue
            path = p.form_path(name) if hasattr(p, "form_path") else self.folder / f"{name}.form"
            try:
                forms.append((name, Form.load(path)))
            except Exception as ex:  # noqa: BLE001
                self.reasons.append(f"{name}.form: cannot be read ({ex})")
        self.forms = F.collect(forms, self.reasons)
        self.form_by_name = {f.name.lower(): f for f in self.forms}
        for fi in self.forms:
            for img in fi.images:
                if img not in self.images:
                    self.images.append(img)
        srcs = []
        for m in p.modules:
            low = m.lower()
            if not low.endswith((".bas", ".cls")):
                continue
            path = self.folder / m
            srcs.append((Path(m).stem, m, path, None))
        for fi in self.forms:
            srcs.append((fi.name, f"{fi.name}.bas", self.folder / f"{fi.name}.bas", fi))
        from ....languages._refs import proxy_files
        if any(True for _ in proxy_files(self.folder, "*.ref.bas")):
            self.reasons.append("solution references (*.ref.bas / RadCall) need the IDE's runtime")
        for name, fn, path, fi in srcs:
            try:
                src = path.read_text(encoding="utf-8-sig", errors="replace") if path.is_file() else ""
            except OSError:
                src = ""
            try:
                mod = parse_module(src, name, fn)
            except VBSyntaxError as e:
                self.reasons.append(f"{fn}({e.line}): syntax error: {e.msg}")
                continue
            mi = ModInfo(name, fn, mod, fi, explicit=mod.option_explicit)
            try:
                for t in tokenize(src):
                    if t.kind == "id" and t.raw and t.value not in mi.spell:
                        mi.spell[t.value] = re.sub(r"[$%&!#@]$", "", t.raw)
            except VBSyntaxError:
                pass
            if mod.is_class:
                if mod.implements:
                    self.reason(mi, 0, "Implements (interfaces) is not supported natively")
                if mod.default_member or mod.enum_member:
                    self.reason(mi, 0, "a default / enumerator member (Attribute VB_UserMemId) is not supported natively")
                cname = mod.vb_name or name
                mi.cls = ClassInfo(cname, "", mi)
            if mod.declares:
                for d in mod.declares:
                    self.reason(mi, d.line, f"Declare {d.kind.title()} {d.name} Lib \"{d.lib}\" (Win32 API calls) "
                                            "is not translated natively yet")
            if mod.events:
                self.reason(mi, 0, "Event declarations are not translated natively")
            self.mods.append(mi)

    # ------------------------------------------------------------------ symbols
    def collect(self):
        CLASSES.clear()
        self.classes = {}
        for mi in self.mods:
            if mi.cls is not None:
                mi.cls.fb = self.uniq(self.safe(mi.cls.name))
                CLASSES[mi.cls.name.lower()] = mi.cls.fb
                self.classes[mi.cls.name.lower()] = mi.cls
        # types / enums first (any module)
        for mi in self.mods:
            for d in mi.mod.decls:
                if d[0] == "type":
                    self.types[d[2]] = self.uniq(self.safe(self.spell(mi, d[2])))
                elif d[0] == "enum":
                    self.enums.add(d[2])
        for mi in self.mods:
            for d in mi.mod.decls:
                if d[0] == "type":
                    fields = {}
                    for m in d[3]:
                        mname, mtyp = m[0], m[1]
                        bounds = m[2] if len(m) > 2 else None
                        tt = _tag_of(mtyp, self.types, self.enums)
                        if mtyp.startswith("string*"):
                            tt = ("String", "s")
                        if tt is None or tt[1] == "coll":
                            self.reason(mi, d[1], f"Type {d[2]}: field {mname} As {mtyp} is not supported natively")
                            tt = ("RVar", "v")
                        fv = VarInfo(mname, self.safe(self.spell(mi, mname), local=True), mtyp, tt[1], tt[0],
                                     dims=bounds and list(bounds), scope="field")
                        fv.fixlen = self.fixlen(mi, d[1], mtyp)
                        fields[mname] = fv
                    self.udt_fields[d[2]] = fields
        for mi in self.mods:
            prefix = mi.name + "_"
            for d in mi.mod.decls:
                kind = d[0]
                if kind == "enum":
                    members = {}
                    for mname, val in d[3]:
                        fb = self.uniq(self.safe(self.spell(mi, mname)))
                        members[mname] = fb
                        vi = VarInfo(mname, fb, "long", "i", "Long", scope="const")
                        vi.const_code = None
                        vi.enum_value = val
                        self.gvars.setdefault(mname, vi)
                    self.enum_members[d[2]] = members
                elif kind == "const":
                    for name, expr in d[2]:
                        public = d[3] and mi.form is None and mi.cls is None
                        fb = self.uniq(self.safe(self.spell(mi, name)) if public else prefix + self.safe(self.spell(mi, name), local=True))
                        vi = VarInfo(name, fb, "", "", "", scope="const")
                        vi.expr, vi.mi = expr, mi
                        (self.gvars if public else mi.vars)[name] = vi
                elif kind == "dim":
                    for name, bounds, typ in d[2]:
                        if name in d[4]:
                            self.reason(mi, d[1], f"WithEvents {name} is not supported natively")
                        if mi.cls is not None:              # a field of the class
                            vi = self.make_var(mi, d[1], name, bounds, typ, "field")
                            mi.vars[name] = vi
                            continue
                        public = d[3] and mi.form is None
                        vi = self.make_var(mi, d[1], name, bounds, typ, "module", public)
                        (self.gvars if public else mi.vars)[name] = vi
            for pname, proc in mi.mod.procs.items():
                if proc.kind not in ("sub", "function") and mi.cls is None:
                    self.reason(mi, proc.line, f"Property {proc.kind.title()} in a standard module is not supported natively")
                    continue
                public = proc.public and mi.form is None and mi.cls is None
                raw = proc.display or pname
                if mi.cls is not None:
                    fb = self.safe(raw, local=True)
                    if pname in ("class_initialize", "class_terminate"):
                        fb = pname
                else:
                    fb = self.uniq(self.safe(raw) if public else prefix + self.safe(raw, local=True))
                params = []
                for prm in proc.params:
                    params.append(self.make_param(mi, proc.line, prm))
                ret = None
                if proc.kind in ("function", "get"):
                    rtyp = self.proc_ret_type(mi, proc)
                    tt = _tag_of(rtyp, self.types, self.enums)
                    if tt is None or tt[1] == "coll":
                        self.reason(mi, proc.line, f"Function {raw} As {rtyp} is not supported natively")
                        tt = ("RVar", "v")
                    ret = VarInfo(pname, "vb_res", rtyp, tt[1], tt[0])
                pi = ProcInfo(pname, fb, proc.kind, params, ret, mi, proc, public)
                mi.procs[pname] = pi
                if mi.cls is not None and proc.kind in ("get", "let", "set"):
                    mi.cls.props.setdefault(pname.split(":", 1)[1], {})[proc.kind] = pi
                    if proc.kind == "get" and params:
                        self.reason(mi, proc.line, f"Property Get {raw} with parameters is not supported natively")
                if mi.cls is not None and pname == "class_terminate" and proc.body:
                    self.reason(mi, proc.line, "Class_Terminate is not run natively (objects are not reference counted)")
                if public:
                    self.gprocs.setdefault(pname, pi)

    def proc_ret_type(self, mi, proc) -> str:
        # the parser drops "As T" of a Function: read it back from the source line
        src = getattr(mi, "_src_lines", None)
        if src is None:
            path = self.folder / mi.filename
            try:
                src = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n").split("\n")
            except OSError:
                src = []
            mi._src_lines = src
        text = ""
        i = proc.line - 1
        while 0 <= i < len(src):
            text += src[i]
            if not src[i].rstrip().endswith(" _"):
                break
            text = text.rstrip()[:-1]
            i += 1
        text = re.sub(r"'.*$", "", text)
        disp = (proc.display or proc.name.split(":")[-1])
        k = text.lower().find(disp.lower())
        k = k + len(disp) - 8 if k >= 0 else text.lower().find("function")
        depth = 0
        j = text.find("(", k + 8)
        if j >= 0:
            for idx in range(j, len(text)):
                if text[idx] == "(":
                    depth += 1
                elif text[idx] == ")":
                    depth -= 1
                    if depth == 0:
                        rest = text[idx + 1:]
                        break
            else:
                rest = ""
        else:
            rest = text[k + 8:]
        m = re.match(r"\s*As\s+([\w.]+)", rest, re.I)
        if m:
            return m.group(1).split(".")[-1].lower()
        nm = proc.display or proc.name
        if nm.endswith("$"):
            return "string"
        if nm.endswith("%") or nm.endswith("&"):
            return "long"
        return "variant"

    def make_var(self, mi, line, name, bounds, typ, scope, public=False) -> VarInfo:
        typ = typ or "variant"
        if name[-1:] in "$%&!#@" and typ == "variant":
            typ = {"$": "string", "%": "integer", "&": "long", "!": "single", "#": "double", "@": "currency"}[name[-1]]
        tt = _tag_of(typ, self.types, self.enums)
        fixlen = 0
        if typ.startswith("string*"):
            fixlen = self.fixlen(mi, line, typ)
            tt = ("String", "s")
        if tt is None:
            self.reason(mi, line, f"Dim {name} As {typ}: object variables (classes, controls, forms, COM) are not "
                                  "supported natively")
            tt = ("RVar", "v")
        raw = self.spell(mi, name)
        autonew = typ.lower().startswith("new:") and tt[1].startswith("obj:")
        if autonew and scope == "field":
            self.reason(mi, line, f"{name} As New (in a class) is not supported natively; create it in Class_Initialize")
        if scope == "module":
            fb = self.uniq(self.safe(raw) if public else mi.name + "_" + self.safe(raw, local=True))
        else:
            fb = self.safe(raw, local=True)
        dims = None
        if bounds is not None:
            dims = list(bounds)
        vi = VarInfo(name, fb, typ, tt[1], tt[0], dims, scope)
        vi.autonew = autonew
        vi.fixlen = fixlen
        return vi

    def fixlen(self, mi, line, typ) -> int:
        """String * n -> n (a constant length; String * CONST_NAME is looked up)."""
        if not typ.startswith("string*"):
            return 0
        n = typ[7:]
        if n.isdigit():
            return int(n)
        self.reason(mi, line, f"String * {n.lstrip('@')}: the length must be a number natively")
        return 1

    def fwd(self, fbtype: str) -> str:
        """Inside a Type body: classes by their forward name."""
        if fbtype.endswith(" Ptr") and fbtype[:-4].lower() in {c.fb.lower() for c in self.classes.values()}:
            return fbtype[:-4] + "_ Ptr"
        return fbtype

    def make_param(self, mi, line, prm: Param) -> VarInfo:
        if prm.paramarray:
            self.reason(mi, line, f"ParamArray {prm.name} is not supported natively")
        vi = self.make_var(mi, line, prm.name, [] if prm.is_array else None, prm.typ, "param")
        vi.byref = prm.byref
        vi.optional = prm.optional
        vi.default = prm.default
        return vi

    # ------------------------------------------------------------------ output
    def emit(self, line: str, src=None):
        self.out.append(line)
        if src is not None:
            self.line_map[len(self.out)] = src

    # ------------------------------------------------------------------ the program
    def run(self) -> Translation:
        self.load()
        self.collect()
        title = self.project.name
        tr = Translation(title=title, images=list(self.images), uses_forms=bool(self.forms))
        saved = self.out
        # procedures first (they register event wrappers, used names, implicit vars ...)
        proc_out: list[str] = []
        self.out = proc_out
        for mi in self.mods:
            self.cur_mod = mi
            if mi.procs:
                self.emit("")
                self.emit(f"' {'=' * 20} {mi.filename}")
            for pi in mi.procs.values():
                try:
                    self.proc(pi)
                except Unsupported as u:
                    self.reason(mi, u.line or pi.proc.line, u.msg)
        self.bind_events()
        proc_map = self.line_map
        self.line_map = {}
        self.out = []
        H = self.out
        self.emit(f"' {title} - generated by RAD IDE from the VB6 project (VB6 -> FreeBASIC native build).")
        self.emit("' Do not edit: it is written again by Build > Publish.")
        self.emit('#include once "vbrt_forms.bi"')
        if self.uses_fx or any(fi.fx_lines for fi in self.forms):
            self.emit('#include once "vbrt_motion.bi"')
        if self.images:
            self.emit('#include once "vbrt_image.bi"')
        self.emit("")
        # classes are used before they are declared (forward types)
        for c in self.classes.values():
            self.emit(f"Type {c.fb}_ As {c.fb}")
        # types
        for mi in self.mods:
            for d in mi.mod.decls:
                if d[0] == "type":
                    self.emit(f"Type {self.types[d[2]]}", (mi.filename, d[1]))
                    for fname, vi in self.udt_fields[d[2]].items():
                        dims = ""
                        if vi.dims:
                            try:
                                dims = "(" + ", ".join(self.bound_code(mi, lo, hi, const=True) for lo, hi in vi.dims) + ")"
                            except Unsupported as u:
                                self.reason(mi, d[1], u.msg)
                        init = f' = "{" " * vi.fixlen}"' if getattr(vi, "fixlen", 0) and not vi.dims else ""
                        self.emit(f"    {vi.fb}{dims} As {self.fwd(vi.fbtype)}{init}")
                    self.emit("End Type")
        # class modules -> Types with member procedures
        for c in self.classes.values():
            mi = c.mi
            self.cur_mod = mi
            self.emit("")
            self.emit(f"' Class {c.name} ({mi.filename})")
            self.emit(f"Type {c.fb}", (mi.filename, 1))
            for vi in mi.vars.values():
                if vi.scope != "field":
                    continue
                try:
                    dims = ""
                    if vi.dims:
                        dims = "(" + ", ".join(self.bound_code(mi, lo, hi, const=True) for lo, hi in vi.dims) + ")"
                    elif vi.dims == []:
                        dims = "(Any)"
                    self.emit(f"    {vi.fb}{dims} As {self.fwd(vi.fbtype)}")
                except Unsupported as u:
                    self.reason(mi, 0, u.msg)
            for pi in mi.procs.values():
                if pi.name == "class_terminate":
                    continue
                self.emit("    Declare " + self.signature(pi, member_decl=True))
            if not any(vi.scope == "field" for vi in mi.vars.values()) and not mi.procs:
                self.emit("    vb_dummy As Long")
            self.emit("End Type")
            self.emit(f"Dim Shared {c.fb}__null(0 To SizeOf({c.fb})) As UByte")
            self.emit(f"Private Function {c.fb}__chk(ByVal p As {c.fb} Ptr) As {c.fb} Ptr   ' Nothing -> error 91")
            self.emit(f"    If p = 0 Then VBRaise(91): Return Cast({c.fb} Ptr, @{c.fb}__null(0))")
            self.emit("    Return p")
            self.emit("End Function")
        # constants / enums
        self.cur_mod = None
        for mi in self.mods:
            self.cur_mod = mi
            for d in mi.mod.decls:
                if d[0] == "enum":
                    self.emit(f"' Enum {self.spell(mi, d[2])}", (mi.filename, d[1]))
                    for mname, val in d[3]:
                        vi = self.gvars.get(mname)
                        try:
                            code = self.expr(val, None).code
                        except Unsupported as u:
                            self.reason(mi, d[1], u.msg)
                            code = "0"
                        self.emit(f"Const {self.enum_members[d[2]][mname]} = {code}")
                elif d[0] == "const":
                    for name, expr in d[2]:
                        vi = mi.vars.get(name) or self.gvars.get(name)
                        self.const_decl(mi, vi, expr, d[1], module=True)
        # ids
        if self.forms:
            self.emit("")
            self.emit("' forms, controls and menu items")
            for fi in self.forms:
                self.emit(f"Const {fi.const} = {fi.id}")
                for ci in fi.ctls.values():
                    self.emit(f"Const {ci.const} = {ci.id}")
                for an, items in fi.arrays.items():
                    lo, hi = min(items), max(items)
                    ids = ", ".join(items[k].const if k in items else "0" for k in range(lo, hi + 1))
                    self.emit(f"Dim Shared {fi.array_const(an)}({lo} To {hi}) As Long = {{{ids}}}")
        # module-level variables
        self.emit("")
        for mi in self.mods:
            self.cur_mod = mi
            for d in mi.mod.decls:
                if d[0] != "dim":
                    continue
                for name, bounds, typ in d[2]:
                    vi = mi.vars.get(name) or self.gvars.get(name)
                    if vi is None or vi.scope != "module":
                        continue
                    if getattr(vi, "autonew", False):
                        self.autonew.append(f"{vi.fb} = New {CLASSES[vi.tag[4:]]}()")
                    try:
                        self.emit(f"Dim Shared {self.decl_text(mi, vi, const_bounds=True)}", (mi.filename, d[1]))
                    except Unsupported as u:
                        self.reason(mi, d[1], u.msg)
        # declarations
        self.emit("")
        for mi in self.mods:
            if mi.cls is not None:
                continue
            for pi in mi.procs.values():
                self.emit("Declare " + self.signature(pi))
        header_len = len(self.out)
        # procedures
        for ln, src in proc_map.items():
            self.line_map[ln + header_len] = src
        self.out.extend(proc_out)
        # event wrappers
        if self.wrappers:
            self.emit("")
            self.emit("' event procedures -> runtime events")
            self.out.extend(self.wrappers)
        # forms
        self.emit("")
        self.emit("Private Sub VBSetupForms()")
        for fi in self.forms:
            for line in F.setup_code(fi, self.handlers.get(fi.name.lower(), {})):
                self.emit(line)
        self.emit("End Sub")
        self.emit("")
        # start
        self.emit("' ---- start")
        self.emit(f"VBInitCore({fb_str(title)})")
        if self.images:
            self.emit("VBUseImages()")
        self.emit("VBSetupForms()")
        for line in self.autonew:
            self.emit(line)
        start = (self.project.startup or "").lower()
        main = None
        for mi in self.mods:
            if "main" in mi.procs and mi.form is None and mi.cls is None:
                main = mi.procs["main"]
                break
        if start in ("sub main", "main") or start not in self.form_by_name:
            if main is None:
                self.reasons.append("no startup form and no Sub Main")
            else:
                self.emit(f"{main.fb}()")
                self.emit("If vbErrPending Then VBUnhandled()")
        else:
            self.emit(f"VBFormShow({self.form_by_name[start].const})")
        self.emit("VBRun()")
        self.out = saved
        tr.source = "\n".join(H) + "\n"
        tr.reasons = self.reasons
        tr.line_map = self.line_map
        tr.images = list(self.images)
        sf = self.form_by_name.get(start) or (self.forms[0] if self.forms else None)
        tr.icon = str(sf.model.props.get("Icon") or "") if sf is not None else ""
        for fi in self.forms:
            if fi.fx_lines:
                try:
                    from ....motion import native_plan
                    tr.notes += native_plan.notes(fi.model, "py")
                except Exception:  # noqa: BLE001 - notes never break a build
                    pass
        return tr

    # ------------------------------------------------------------------ events
    def bind_events(self):
        for mi in self.mods:
            fi = mi.form
            if fi is None:
                continue
            fh = self.handlers.setdefault(fi.name.lower(), {})
            for pname, pi in mi.procs.items():
                if "_" not in pname:
                    continue
                owner, ev = pname.rsplit("_", 1)
                if ev == "completed" and owner in fi.fx_names and owner not in fi.ctls:
                    # <storyboard>_Completed (rt/vbrt_motion.bi posts it when the animation ends)
                    if any(not getattr(p, "optional", False) for p in pi.params):
                        self.reason(mi, pi.proc.line, f"event {pi.proc.display} takes no arguments")
                        continue
                    wrapper = self.uniq(f"vbev_{F._ident(fi.name)}_{F._ident(pi.proc.display or pname)}")
                    self.wrappers += [f"Private Sub {wrapper}(ByRef e As VBEventArgs)",
                                      f"    {self.call_proc(pi, [], None, pi.proc.line).code}", "End Sub"]
                    fh.setdefault(F.FX_DONE_KEY, {})[owner] = wrapper
                    continue
                evname = next((k for k in F.KNOWN_EVENTS if k.lower() == ev), None)
                if evname is None:
                    continue
                if owner == "form":
                    ctype, key, is_arr = "Form", "", False
                    ok = evname in F.FORM_EVENTS
                else:
                    ci = fi.ctls.get(owner)
                    is_arr = owner in fi.arrays and (ci is None or ci.array)
                    if is_arr:
                        ci = next(iter(fi.arrays[owner].values()))
                    if ci is None:
                        continue
                    key = owner
                    ctype = "Menu" if ci.menu else ci.type
                    ok = evname == "Click" if ci.menu else evname in F.EVENTS.get(ci.type, set())
                if not ok:
                    self.reason(mi, pi.proc.line, f"event {pi.proc.display} ({ctype}.{evname}) is not supported natively")
                    continue
                fields = list(F.EVENT_ARGS[evname][1])
                if ctype == "TabControl" and evname == "Click":
                    fields = ["prevTab"]
                if is_arr:
                    fields = ["index"] + fields
                args, pre, post = [], [], []
                for k, p in enumerate(pi.params):
                    if k >= len(fields):
                        if getattr(p, "optional", False):
                            break
                        args.append({"s": '""', "v": "RV_Empty()"}.get(p.tag, "0"))
                        continue
                    f = fields[k]
                    ftag = F.FIELD_TAG[f]
                    fbt = "Single" if f in ("x", "y") else "Long"
                    if p.fbtype == fbt or (p.tag == ftag and not p.byref):
                        args.append(f"e.{f}")
                    elif p.byref and p.fbtype:
                        # ByRef argument of another type (Validate Cancel As Boolean): a temporary copied back,
                        # so the handler's assignment reaches the runtime
                        tmp = f"vbarg{k}"
                        pre.append(f"    Dim {tmp} As {p.fbtype} = {self.conv(E(f'e.{f}', ftag), p.tag)}")
                        post.append(f"    e.{f} = {self.conv(E(tmp, p.tag), ftag)}")
                        args.append(tmp)
                    else:
                        args.append(self.conv(E(f"e.{f}", ftag), p.tag))
                wrapper = self.uniq(f"vbev_{F._ident(fi.name)}_{F._ident(pi.proc.display or pname)}")
                self.wrappers += [f"Private Sub {wrapper}(ByRef e As VBEventArgs)", *pre,
                                  f"    {pi.fb}({', '.join(args)})", *post,
                                  "End Sub"]
                fh.setdefault(key, {})[evname] = wrapper

    # ------------------------------------------------------------------ declarations
    def bound_code(self, mi, lo, hi, const=False, ctx=None) -> str:
        def one(e):
            x = self.expr(e, ctx)
            return self.conv(x, "i")
        return f"{one(lo) if lo is not None else '0'} To {one(hi)}"

    def decl_text(self, mi, vi: VarInfo, const_bounds=False, ctx=None) -> str:
        if vi.dims is None:
            if getattr(vi, "fixlen", 0):
                return f'{vi.fb} As String = "{" " * vi.fixlen}"'
            return f"{vi.fb} As {vi.fbtype}"
        if not vi.dims:
            return f"{vi.fb}() As {vi.fbtype}"
        b = ", ".join(self.bound_code(mi, lo, hi, const_bounds, ctx) for lo, hi in vi.dims)
        return f"{vi.fb}({b}) As {vi.fbtype}"

    def const_decl(self, mi, vi, expr, line, module):
        try:
            x = self.expr(expr, None if module else self.ctx)
        except Unsupported as u:
            self.reason(mi, u.line or line, u.msg)
            x = E("0", "i")
        vi.tag = x.t if x.t in ("i", "f", "s", "b", "d") else "v"
        vi.fbtype = TAG_FB.get(vi.tag, "RVar")
        pure = re.fullmatch(r"[\w\s.+\-*/()&\"]*", x.code) and not re.search(r"\w\(", x.code)
        if module:
            if pure and vi.tag != "v":
                self.emit(f"Const {vi.fb} = {x.code}", (mi.filename, line))
            else:
                self.emit(f"#define {vi.fb} ({x.code})", (mi.filename, line))
        else:
            self.emit(f"    Dim {vi.fb} As {vi.fbtype} = {x.code}", (mi.filename, line))

    def signature(self, pi: ProcInfo, member_decl=False) -> str:
        ps = []
        t = self.fwd if member_decl else (lambda x: x)
        for p in pi.params:
            if p.dims is not None:
                ps.append(f"{p.fb}() As {t(p.fbtype)}")
            else:
                ps.append(f"{'ByRef' if p.byref else 'ByVal'} {p.fb} As {t(p.fbtype)}")
        cls = pi.mod.cls
        if cls is not None:
            owner = "" if member_decl else cls.fb + "."
            if pi.name == "class_initialize":
                return "Constructor()" if member_decl else f"Constructor {cls.fb}()"
            if pi.kind in ("get", "let", "set"):
                if pi.kind == "get":
                    return f"Property {owner}{pi.fb}() As {t(pi.ret.fbtype)}"
                return f"Property {owner}{pi.fb}({', '.join(ps)})"
            if pi.kind == "function":
                return f"Function {owner}{pi.fb}({', '.join(ps)}) As {t(pi.ret.fbtype)}"
            return f"Sub {owner}{pi.fb}({', '.join(ps)})"
        if pi.kind == "function":
            return f"Function {pi.fb}({', '.join(ps)}) As {pi.ret.fbtype}"
        return f"Sub {pi.fb}({', '.join(ps)})"

    # ------------------------------------------------------------------ procedures
    def proc(self, pi: ProcInfo):
        mi, proc = pi.mod, pi.proc
        if mi.cls is not None and pi.name == "class_terminate":
            return
        ctx = Ctx(self, pi)
        self.ctx = ctx
        # pass 1: statements into a buffer (collects locals, implicit vars, labels)
        body = []
        saved, saved_map = self.out, self.line_map
        self.out, self.line_map = body, {}
        self.block(proc.body, ctx, 1)
        body_map = self.line_map
        self.out, self.line_map = saved, saved_map
        gos = ", ".join(f"vb_gr{k}" for k in ctx.gosub_points) or "vb_err"
        res = ", ".join(f"vb_r{k}" for k in range(1, ctx.resume_points + 1)) or "vb_exit"
        body = [b.replace("{GOSUBS}", gos).replace("{RESUMES}", res) for b in body]
        self.emit("")
        self.emit(("Private " if not pi.public and mi.cls is None else "") + self.signature(pi), (mi.filename, proc.line))
        for decl in ctx.decls:
            self.emit(decl[0], decl[1])
        for name, vi in ctx.implicit.items():
            self.emit(f"    Dim {vi.fb} As RVar")
        if pi.ret is not None:
            self.emit(f"    Dim vb_res As {pi.ret.fbtype}")
        for tmp, typ in ctx.temps.items():
            self.emit(f"    Dim {tmp} As {typ}")
        if ctx.uses_handler:
            self.emit("    Dim vb_onerr As Long")
            self.emit("    Dim vb_inerr As Long")
            if ctx.resume_points:
                self.emit("    Dim vb_rs As Long")
        if ctx.gosub:
            self.emit("    Dim vb_gs(1 To 64) As Long")
            self.emit("    Dim vb_gsp As Long")
        base = len(self.out)
        for k, v in body_map.items():
            self.line_map[k + base] = v
        self.out.extend(body)
        self.emit("vb_exit:")
        if ctx.uses_handler:
            self.emit("    If vb_inerr Then VBErrClear()")
        if mi.cls is not None and pi.name == "class_initialize":
            end_kw = "Constructor"
        elif pi.kind in ("get", "let", "set"):
            end_kw = "Property"
        else:
            end_kw = "Function" if pi.kind == "function" else "Sub"
        if pi.ret is not None:
            self.emit("    Return vb_res")
        else:
            self.emit(f"    Exit {end_kw}")
        self.emit("vb_err:")
        if ctx.uses_handler:
            self.emit("    If vb_inerr OrElse vb_onerr = 0 Then Goto vb_exit_err")
            self.emit("    vbErrPending = 0")
            if ctx.resume_next and ctx.resume_points:
                labels = ", ".join(f"vb_r{k}" for k in range(1, ctx.resume_points + 1))
                self.emit(f"    If vb_onerr = -1 Then On vb_rs Goto {labels}")
            hl = [f"vb_onerr = {k} Then vb_inerr = -1: Goto {lab}" for lab, k in ctx.handler_labels.items()]
            for h in hl:
                self.emit(f"    If {h}")
            self.emit("vb_exit_err:")
            self.emit("    vb_inerr = 0")
        if pi.ret is not None:
            self.emit("    Return vb_res")
        self.emit("End " + end_kw)
        self.ctx = None

    def block(self, stmts, ctx, ind):
        for st in stmts:
            try:
                self.stmt(st, ctx, ind)
            except Unsupported as u:
                self.reason(ctx.mi, u.line or st[1], u.msg)

    def check(self, ctx, ind, line):
        """Error check after a statement."""
        pad = "    " * ind
        loc = f"VBErrAt({line}, @{fb_str(ctx.mi.filename)})"
        if ctx.resume_next or ctx.resume_points_wanted:
            ctx.resume_points += 1
            k = ctx.resume_points
            self.emit(f"{pad}If vbErrPending Then {loc}: vb_rs = {k}: Goto vb_err")
            self.emit(f"vb_r{k}:")
        else:
            self.emit(f"{pad}If vbErrPending Then {loc}: Goto vb_err")

    def line(self, ctx, ind, code, line, check=True):
        self.emit("    " * ind + code, (ctx.mi.filename, line))
        if check and (re.search(r"[A-Za-z_]\w*\(", code) or ctx.uses_handler) and                 not code.startswith(("Goto ", "Exit ", "Return")):
            self.check(ctx, ind, line)

    # ------------------------------------------------------------------ statements
    def stmt(self, st, ctx, ind):
        kind, line = st[0], st[1]
        h = getattr(self, "s_" + kind, None)
        if h is None:
            raise Unsupported(f"statement '{kind}' is not supported natively", line)
        h(st, ctx, ind)

    def s_nop(self, st, ctx, ind):
        pass

    def s_label(self, st, ctx, ind):
        self.emit(f"L_{F._ident(st[2])}:", (ctx.mi.filename, st[1]))

    def s_dim(self, st, ctx, ind):
        mi = ctx.mi
        for name, bounds, typ in st[2]:
            if name in st[4]:
                raise Unsupported(f"WithEvents {name} is not supported natively", st[1])
            vi = self.make_var(mi, st[1], name, bounds, typ, "local")
            if name in ctx.locals and ctx.locals[name].scope == "local":
                pass
            ctx.locals[name] = vi
            if vi.dims and not all(self.is_const(lo, ctx) and self.is_const(hi, ctx) for lo, hi in vi.dims):
                # bounds from variables: a dynamic array sized here
                ctx.decls.append((f"    Dim {vi.fb}() As {vi.fbtype}", (mi.filename, st[1])))
                b = ", ".join(self.bound_code(mi, lo, hi, ctx=ctx) for lo, hi in vi.dims)
                self.line(ctx, ind, f"ReDim {vi.fb}({b})", st[1])
                continue
            init = f" = New {CLASSES[vi.tag[4:]]}()" if getattr(vi, "autonew", False) and vi.dims is None else ""
            ctx.decls.append(("    " + ("Static " if st[0] == "static" else "Dim ") + self.decl_text(mi, vi, ctx=ctx) + init,
                              (mi.filename, st[1])))

    def is_const(self, e, ctx) -> bool:
        if e is None:
            return True
        k = e[0]
        if k in ("num", "str", "bool"):
            return True
        if k == "paren":
            return self.is_const(e[2], ctx)
        if k == "unop":
            return self.is_const(e[3], ctx)
        if k == "binop":
            return self.is_const(e[3], ctx) and self.is_const(e[4], ctx)
        if k == "name":
            vi = ctx.lookup_var(e[2]) if ctx else None
            return vi is not None and vi.scope == "const" and vi.tag != "v"
        return False

    s_static = s_dim

    def s_const(self, st, ctx, ind):
        for name, expr in st[2]:
            vi = VarInfo(name, self.safe(self.spell(ctx.mi, name), local=True), "", "", "", scope="const")
            x = self.expr(expr, ctx)
            vi.tag = x.t if x.t in ("i", "f", "s", "b", "d") else "v"
            vi.fbtype = TAG_FB.get(vi.tag, "RVar")
            ctx.locals[name] = vi
            ctx.decls.append((f"    Dim {vi.fb} As {vi.fbtype} = {self.conv(x, vi.tag)}", (ctx.mi.filename, st[1])))

    def s_redim(self, st, ctx, ind):
        for name, bounds, typ in st[2]:
            vi = ctx.lookup_var(name)
            if vi is None:
                vi = self.make_var(ctx.mi, st[1], name, [], typ, "local")
                ctx.locals[name] = vi
                ctx.decls.append((f"    Dim {vi.fb}() As {vi.fbtype}", (ctx.mi.filename, st[1])))
            if vi.dims is None:
                raise Unsupported(f"ReDim {name}: arrays inside a Variant are not supported natively", st[1])
            b = ", ".join(self.bound_code(ctx.mi, lo, hi, ctx=ctx) for lo, hi in bounds)
            self.line(ctx, ind, f"ReDim {'Preserve ' if st[3] else ''}{self.var_ref(vi, ctx)}({b})", st[1])

    def s_erase(self, st, ctx, ind):
        for name in st[2]:
            vi = ctx.lookup_var(name)
            if vi is None or vi.dims is None:
                raise Unsupported(f"Erase {name}: not an array", st[1])
            self.line(ctx, ind, f"Erase {self.var_ref(vi, ctx)}", st[1], check=False)

    def s_assign(self, st, ctx, ind):
        self.assign(st[2], st[3], ctx, ind, st[1])

    def s_set(self, st, ctx, ind):
        target, value = st[2], st[3]
        t = self.expr(target, ctx, want="lvalue")
        if t.t == "coll":
            if value[0] == "new" and value[2].lower() == "collection" or value[0] == "nothing":
                self.line(ctx, ind, f"VBColClear({t.code})", st[1], check=False)
                return
            v = self.expr(value, ctx)
            if v.t == "coll":
                self.line(ctx, ind, f"{t.code} = {v.code}", st[1], check=False)
                return
        v = self.expr(value, ctx)
        if t.t.startswith("obj:") or (t.t == "v" and v.t.startswith("obj:")) or t.t == "setfn":
            self.store(t, v, ctx, ind, st[1])
            return
        raise Unsupported("Set: only Collection and class objects are supported natively", st[1])

    def s_callstmt(self, st, ctx, ind):
        call = st[2]
        target, args = call[2], call[3]
        code = self.call_statement(target, args, ctx, st[1])
        if code is None:
            return
        for c in (code if isinstance(code, list) else [code]):
            self.line(ctx, ind, c, st[1])

    def s_if(self, st, ctx, ind):
        pad = "    " * ind
        first = True
        for cond, body in st[2]:
            c = self.cond(cond, ctx)
            self.emit(f"{pad}{'If' if first else 'ElseIf'} {c} Then", (ctx.mi.filename, st[1]))
            first = False
            self.block(body, ctx, ind + 1)
        if st[3]:
            self.emit(f"{pad}Else")
            self.block(st[3], ctx, ind + 1)
        self.emit(f"{pad}End If")
        if ctx.cond_calls:
            self.check(ctx, ind, st[1])
            ctx.cond_calls = False

    def cond(self, e, ctx) -> str:
        x = self.expr(e, ctx)
        if re.search(r"[A-Za-z_]\w*\(", x.code):
            ctx.cond_calls = True
        if x.t == "b":
            return x.code
        return self.conv(x, "b")

    def s_select(self, st, ctx, ind):
        pad = "    " * ind
        subj = self.expr(st[2], ctx)
        if subj.t in ("ctl",):
            subj = self.ctl_default(subj, ctx, st[1])
        if subj.t not in ("i", "f", "s", "b", "d", "v"):
            raise Unsupported("Select Case on an object", st[1])
        ctx.cond_calls = "(" in subj.code
        if subj.t == "v":
            tmp = ctx.temp("vb_sel", "RVar")
            self.emit(f"{pad}{tmp} = {subj.code}", (ctx.mi.filename, st[1]))
            first = True
            for tests, body in st[3]:
                conds = []
                for t in tests:
                    if t[0] == "eq":
                        conds.append(f"(RV_Cmp({tmp}, {self.conv(self.expr(t[1], ctx), 'v')}) = 0)")
                    elif t[0] == "range":
                        conds.append(f"(RV_Cmp({tmp}, {self.conv(self.expr(t[1], ctx), 'v')}) >= 0 AndAlso "
                                     f"RV_Cmp({tmp}, {self.conv(self.expr(t[2], ctx), 'v')}) <= 0)")
                    else:
                        op = {"=": "=", "<>": "<>", "<": "<", ">": ">", "<=": "<=", ">=": ">="}[t[1]]
                        conds.append(f"(RV_Cmp({tmp}, {self.conv(self.expr(t[2], ctx), 'v')}) {op} 0)")
                self.emit(f"{pad}{'If' if first else 'ElseIf'} {' OrElse '.join(conds)} Then")
                first = False
                self.block(body, ctx, ind + 1)
            if st[4]:
                if first:
                    self.emit(f"{pad}If -1 Then")
                    first = False
                else:
                    self.emit(f"{pad}Else")
                self.block(st[4], ctx, ind + 1)
            if not first:
                self.emit(f"{pad}End If")
            return
        tag = subj.t if subj.t != "b" else "i"
        self.emit(f"{pad}Select Case {self.conv(subj, tag)}", (ctx.mi.filename, st[1]))
        for tests, body in st[3]:
            parts = []
            for t in tests:
                if t[0] == "eq":
                    parts.append(self.conv(self.expr(t[1], ctx), tag))
                elif t[0] == "range":
                    parts.append(f"{self.conv(self.expr(t[1], ctx), tag)} To {self.conv(self.expr(t[2], ctx), tag)}")
                else:
                    parts.append(f"Is {t[1]} {self.conv(self.expr(t[2], ctx), tag)}")
            self.emit(f"{pad}Case {', '.join(parts)}")
            self.block(body, ctx, ind + 1)
        if st[4]:
            self.emit(f"{pad}Case Else")
            self.block(st[4], ctx, ind + 1)
        self.emit(f"{pad}End Select")
        if ctx.cond_calls:
            self.check(ctx, ind, st[1])
            ctx.cond_calls = False

    def s_for(self, st, ctx, ind):
        pad = "    " * ind
        _, line, var, start, stop, step, body = st
        v = self.expr(("name", line, var), ctx, want="lvalue")
        a, b = self.expr(start, ctx), self.expr(stop, ctx)
        s = self.expr(step, ctx) if step is not None else None
        if v.t in ("i", "f"):
            stepc = f" Step {self.conv(s, v.t)}" if s is not None else ""
            self.emit(f"{pad}For {v.code} = {self.conv(a, v.t)} To {self.conv(b, v.t)}{stepc}", (ctx.mi.filename, line))
            ctx.loops.append(("for", None))
            self.block(body, ctx, ind + 1)
            ctx.loops.pop()
            self.emit(f"{pad}Next")
            return
        if v.t != "v":
            raise Unsupported(f"For: the counter {var} must be a number", line)
        n = ctx.new_id()
        endv, stepv = ctx.temp(f"vb_fend{n}", "Double"), ctx.temp(f"vb_fstep{n}", "Double")
        self.emit(f"{pad}{v.code} = {self.conv(a, 'v')}: {endv} = {self.conv(b, 'f')}: "
                  f"{stepv} = {self.conv(s, 'f') if s is not None else '1'}", (ctx.mi.filename, line))
        self.emit(f"{pad}Do While IIf({stepv} >= 0, RV_ToD({v.code}) <= {endv}, RV_ToD({v.code}) >= {endv})")
        ctx.loops.append(("vfor", f"vb_fx{n}"))
        self.block(body, ctx, ind + 1)
        ctx.loops.pop()
        self.emit(f"{pad}    {v.code} = RV_Add({v.code}, RV_D({stepv}))")
        self.emit(f"{pad}Loop")
        self.emit(f"vb_fx{n}:")

    def s_foreach(self, st, ctx, ind):
        pad = "    " * ind
        _, line, var, coll, body = st
        v = self.expr(("name", line, var), ctx, want="lvalue")
        c = self.expr(coll, ctx)
        n = ctx.new_id()
        i = ctx.temp(f"vb_fe{n}", "Long")
        if c.t == "coll":
            self.emit(f"{pad}For {i} = 1 To {c.code}.count", (ctx.mi.filename, line))
            self.emit(f"{pad}    {v.code} = {self.conv(E(f'{c.code}.items({i} - 1)', 'v'), v.t)}")
        elif c.t == "arr":
            self.emit(f"{pad}For {i} = LBound({c.code}) To UBound({c.code})", (ctx.mi.filename, line))
            self.emit(f"{pad}    {v.code} = {self.conv(E(f'{c.code}({i})', c.var.tag), v.t)}")
        else:
            raise Unsupported("For Each works natively over arrays and Collections only", line)
        ctx.loops.append(("for", None))
        self.block(body, ctx, ind + 1)
        ctx.loops.pop()
        self.emit(f"{pad}Next")

    def s_do(self, st, ctx, ind):
        pad = "    " * ind
        _, line, pre, post, body = st
        head = "Do"
        if pre:
            head += f" {pre[0].title()} {self.cond(pre[1], ctx)}"
        self.emit(pad + head, (ctx.mi.filename, line))
        ctx.loops.append(("do", None))
        self.block(body, ctx, ind + 1)
        ctx.loops.pop()
        tail = "Loop"
        if post:
            tail += f" {post[0].title()} {self.cond(post[1], ctx)}"
        self.emit(pad + tail)
        if ctx.cond_calls:
            self.check(ctx, ind, line)
            ctx.cond_calls = False

    def s_with(self, st, ctx, ind):
        obj = self.expr(st[2], ctx, want="object")
        ctx.withs.append(obj)
        self.block(st[3], ctx, ind)
        ctx.withs.pop()

    def s_exit(self, st, ctx, ind):
        what = st[2]
        pad = "    " * ind
        if what in ("sub", "function", "property"):
            self.emit(f"{pad}Goto vb_exit", (ctx.mi.filename, st[1]))
        elif what == "for":
            for kind, lab in reversed(ctx.loops):
                if kind in ("for", "vfor"):
                    self.emit(f"{pad}{'Exit For' if kind == 'for' else 'Goto ' + lab}", (ctx.mi.filename, st[1]))
                    return
            raise Unsupported("Exit For outside a For loop", st[1])
        elif what == "do":
            self.emit(f"{pad}Exit Do", (ctx.mi.filename, st[1]))
        else:
            raise Unsupported(f"Exit {what}", st[1])

    def s_end(self, st, ctx, ind):
        self.emit("    " * ind + "VBEnd()", (ctx.mi.filename, st[1]))

    def s_stop(self, st, ctx, ind):
        pass

    def s_goto(self, st, ctx, ind):
        self.emit("    " * ind + f"Goto L_{F._ident(st[2])}", (ctx.mi.filename, st[1]))

    def s_gosub(self, st, ctx, ind):
        ctx.gosub = True
        n = len(ctx.gosub_points) + 1
        ctx.gosub_points.append(n)
        pad = "    " * ind
        self.emit(f"{pad}vb_gsp += 1: vb_gs(vb_gsp) = {n}: Goto L_{F._ident(st[2])}", (ctx.mi.filename, st[1]))
        self.emit(f"vb_gr{n}:")

    def s_return(self, st, ctx, ind):
        ctx.gosub = True
        pad = "    " * ind
        self.emit(f"{pad}If vb_gsp = 0 Then VBRaise(3): Goto vb_err", (ctx.mi.filename, st[1]))
        ctx.return_lines.append(len(self.out))
        self.emit(f"{pad}vb_gsp -= 1: On vb_gs(vb_gsp + 1) Goto {{GOSUBS}}")

    def s_ongoto(self, st, ctx, ind):
        if st[3] != "goto":
            raise Unsupported("On ... GoSub is not supported natively", st[1])
        x = self.expr(st[2], ctx)
        labels = ", ".join(f"L_{F._ident(l)}" for l in st[4])
        self.line(ctx, ind, f"On {self.conv(x, 'i')} Goto {labels}", st[1], check=False)

    def s_onerror(self, st, ctx, ind):
        target = st[2]
        ctx.uses_handler = True
        pad = "    " * ind
        if target == "next":
            ctx.resume_next = True
            self.emit(f"{pad}vb_onerr = -1", (ctx.mi.filename, st[1]))
        elif target == "0":
            self.emit(f"{pad}vb_onerr = 0", (ctx.mi.filename, st[1]))
        else:
            lab = f"L_{F._ident(target)}"
            k = ctx.handler_labels.setdefault(lab, len(ctx.handler_labels) + 1)
            self.emit(f"{pad}vb_onerr = {k}", (ctx.mi.filename, st[1]))

    def s_resume(self, st, ctx, ind):
        pad = "    " * ind
        target = st[2]
        ctx.uses_handler = True
        if target == "next":
            ctx.resume_next = True
            ctx.resume_points_wanted = True
            self.emit(f"{pad}vb_inerr = 0: VBErrClear(): On vb_rs Goto {{RESUMES}}", (ctx.mi.filename, st[1]))
            ctx.resume_lines.append(len(self.out))
        elif target == "":
            raise Unsupported("Resume (retry the failing statement) is not supported natively; use Resume Next or "
                              "Resume <label>", st[1])
        else:
            self.emit(f"{pad}vb_inerr = 0: VBErrClear(): Goto L_{F._ident(target)}", (ctx.mi.filename, st[1]))

    def s_errorstmt(self, st, ctx, ind):
        self.line(ctx, ind, f"VBRaise({self.conv(self.expr(st[2], ctx), 'i')})", st[1])

    def s_debugprint(self, st, ctx, ind):
        _, line, what, args, seps = st
        if what != "print":
            return
        tmp = ctx.temp("vb_dbg", "String")
        parts = [f'{tmp} = ""']
        for i, a in enumerate(args):
            if a[0] == "call" and a[2][0] == "name" and a[2][2] in ("spc", "tab"):
                n = self.conv(self.expr(a[3][0], ctx), "i") if a[3] else "0"
                parts.append(f"{tmp} &= Space({n})" if a[2][2] == "spc" else f"{tmp} &= VBTabTo({tmp}, {n})")
            else:
                parts.append(f"{tmp} &= {self.conv(self.expr(a, ctx), 's')}")
            if i < len(seps) and seps[i] == "," and (i < len(args) - 1 or len(seps) == len(args)):
                parts.append(f"{tmp} &= Chr(9)")
        nl = "0" if args and len(seps) >= len(args) else "-1"
        for p in parts:
            self.emit("    " * ind + p, (ctx.mi.filename, line))
        self.line(ctx, ind, f"VBDebugOut({tmp}, {nl})", line)

    # files
    def s_open(self, st, ctx, ind):
        _, line, path, mode, access, num, reclen = st
        m = {"input": 1, "output": 2, "append": 3}.get(mode)
        if m is None:
            raise Unsupported(f"Open ... For {mode.title()} (binary / random files) is not supported natively", line)
        self.line(ctx, ind, f"VBOpen({self.conv(self.expr(path, ctx), 's')}, {m}, {self.conv(self.expr(num, ctx), 'i')})", line)

    def s_close(self, st, ctx, ind):
        if not st[2]:
            self.line(ctx, ind, "VBCloseAll()", st[1], check=False)
        for n in st[2]:
            self.line(ctx, ind, f"VBClose({self.conv(self.expr(n, ctx), 'i')})", st[1], check=False)

    def s_fprint(self, st, ctx, ind):
        num = self.conv(self.expr(st[2], ctx), "i")
        items = st[3]
        calls = []
        if not items:
            calls.append(f"VBFWrite({num}, Chr(10))")
        last = ""
        for e, sep in items:
            if e is not None:
                if e[0] == "call" and e[2][0] == "name" and e[2][2] in ("spc", "tab"):
                    n = self.conv(self.expr(e[3][0], ctx), "i") if e[3] else "0"
                    calls.append(f"VBFWrite({num}, Space({n}))" if e[2][2] == "spc" else
                                 (f"VBFTab({num}, {n})" if e[3] else f"VBFZone({num})"))
                else:
                    x = self.expr(e, ctx)
                    if x.t == "ctl":
                        x = self.ctl_default(x, ctx, st[1])
                    if x.t in ("i", "f"):
                        s = f"VBPrintNum({x.code})"
                    elif x.t == "v":
                        s = f"VBPrintV({x.code})"
                    else:
                        s = self.conv(x, "s")
                    calls.append(f"VBFWrite({num}, {s})")
            if sep == ",":
                calls.append(f"VBFZone({num})")
            last = sep
        if items and last == "":
            calls.append(f"VBFWrite({num}, Chr(10))")
        for c in calls:
            self.line(ctx, ind, c, st[1], check=False)
        self.check(ctx, ind, st[1])

    def s_fwrite(self, st, ctx, ind):
        num = self.conv(self.expr(st[2], ctx), "i")
        parts = []
        for e, sep in st[3]:
            if e is None:
                continue
            x = self.expr(e, ctx)
            if x.t == "ctl":
                x = self.ctl_default(x, ctx, st[1])
            if x.t == "s":
                parts.append(f"VBWriteS({x.code})")
            elif x.t in ("i", "f"):
                parts.append(f"VBStrD({x.code})")
            elif x.t == "b":
                parts.append(f'IIf({x.code}, "#TRUE#", "#FALSE#")')
            elif x.t == "d":
                parts.append(f"VBWriteDate({x.code})")
            else:
                parts.append(f"VBWriteV({self.conv(x, 'v')})")
        trailing = bool(st[3]) and st[3][-1][1] != ""
        text = ' & "," & '.join(parts) if parts else '""'
        end = '","' if trailing else "Chr(10)"
        self.line(ctx, ind, f"VBFWrite({num}, {text} & {end})", st[1])

    def s_finput(self, st, ctx, ind):
        num = self.conv(self.expr(st[2], ctx), "i")
        q = ctx.temp("vb_q", "Long")
        s = ctx.temp("vb_qs", "String")
        for target in st[3]:
            t = self.expr(target, ctx, want="lvalue")
            self.line(ctx, ind, f"{s} = VBInputField({num}, {q})", st[1])
            if t.t == "s":
                val = s
            elif t.t in ("i", "f", "b", "d"):
                val = f"VBFieldNum({s})"
            else:
                val = f"VBFieldV({s}, {q})"
            self.store(t, E(val, t.t if t.t in ("s",) else ("f" if t.t != "v" else "v")), ctx, ind, st[1])

    def s_flineinput(self, st, ctx, ind):
        num = self.conv(self.expr(st[2], ctx), "i")
        t = self.expr(st[3], ctx, want="lvalue")
        self.store(t, E(f"VBLineInput({num})", "s"), ctx, ind, st[1])

    def s_rename(self, st, ctx, ind):
        self.line(ctx, ind, f"VBName({self.conv(self.expr(st[2], ctx), 's')}, {self.conv(self.expr(st[3], ctx), 's')})", st[1])

    def s_unload(self, st, ctx, ind):
        x = self.expr(st[2], ctx, want="object")
        if x.t != "form":
            raise Unsupported("Unload of a control (control arrays created at run time) is not supported natively", st[1])
        self.line(ctx, ind, f"VBFormUnload({x.code}, 1)", st[1])

    def s_loadform(self, st, ctx, ind):
        x = self.expr(st[2], ctx, want="object")
        if x.t != "form":
            raise Unsupported("Load of a control array element is not supported natively", st[1])
        self.line(ctx, ind, f"VBFormLoad({x.code})", st[1])

    def s_raiseevent(self, st, ctx, ind):
        raise Unsupported("RaiseEvent (class events) is not supported natively", st[1])

    def s_fget(self, st, ctx, ind):
        raise Unsupported("Get # (binary / random files) is not supported natively", st[1])

    s_fput = s_fget

    def s_fseek(self, st, ctx, ind):
        raise Unsupported("Seek # is not supported natively", st[1])

    # ------------------------------------------------------------------ assignment
    def assign(self, target, value, ctx, ind, line):
        # Mid(s, start, n) = text
        if target[0] == "call" and target[2][0] == "name" and target[2][2] in ("mid", "mid$") and \
                ctx.lookup_var("mid") is None:
            a = target[3]
            s = self.expr(a[0], ctx, want="lvalue")
            if s.t != "s":
                raise Unsupported("Mid() = needs a String variable", line)
            n = self.conv(self.expr(a[2], ctx), "i") if len(a) > 2 else "-1"
            self.line(ctx, ind, f"VBMidSet({s.code}, {self.conv(self.expr(a[1], ctx), 'i')}, {n}, "
                                f"{self.conv(self.expr(value, ctx), 's')})", line)
            return
        t = self.expr(target, ctx, want="lvalue")
        v = self.expr(value, ctx)
        if t.t == "arr" and v.t == "split":
            self.line(ctx, ind, v.code.replace("{ARR}", t.code + "()"), line)
            if t.var.tag != "s":
                raise Unsupported("Split() needs a dynamic String array (Dim a() As String)", line)
            return
        if t.t == "arr":
            raise Unsupported("assigning a whole array is not supported natively", line)
        self.store(t, v, ctx, ind, line)

    def store(self, t: E, v: E, ctx, ind, line):
        if t.t == "prop":                    # control / form property: code holds a template
            setter = t.code
            tag = t.idcode
            self.line(ctx, ind, setter.replace("{V}", self.conv(v, tag)), line)
            return
        if t.t == "setfn":
            self.line(ctx, ind, t.code.replace("{V}", self.conv(v, t.idcode)), line)
            return
        if t.t == "ctl":
            p = F.DEFAULT_PROP.get(t.ctl.type)
            pt = self.ctl_prop(t, p, ctx, line, setter=True)
            self.store(pt, v, ctx, ind, line)
            return
        if t.t.startswith("obj:"):
            self.line(ctx, ind, f"{t.code} = {self.conv(v, t.t)}", line)
            return
        if t.t in ("i", "f", "s", "b", "d", "v") or t.t.startswith("udt:") or t.t == "coll":
            if t.t.startswith("udt:") or t.t == "coll":
                if v.t != t.t:
                    raise Unsupported("type mismatch in an assignment", line)
                self.line(ctx, ind, f"{t.code} = {v.code}", line)
                return
            val = self.conv(v, t.t)
            if t.t == "s" and t.var is not None and getattr(t.var, "fixlen", 0):
                val = f"VBFixStr({val}, {t.var.fixlen})"
            self.line(ctx, ind, f"{t.code} = {val}", line)
            return
        raise Unsupported(f"cannot assign to this target natively ({t.t})", line)

    # ------------------------------------------------------------------ conversions
    def conv(self, x: E, tag: str) -> str:
        if x.t == "ctl":
            x = self.ctl_default(x, self.ctx, 0)
        if x.t == "none":
            raise Unsupported("a Sub has no value")
        if x.t == tag:
            return x.code
        c = x.code
        if tag.startswith("obj:"):
            if x.t == "nothing":
                return "0"
            if x.t == "v":
                return f"Cast({CLASSES[tag[4:]]} Ptr, RV_ToObj({c}))"
            raise Unsupported(f"type mismatch ({self.tagname(x.t)} where an object of class {tag[4:]} is expected)")
        if x.t.startswith("obj:"):
            if tag == "v":
                return f"RV_Obj({c})"
            raise Unsupported(f"an object (class {x.t[4:]}) is used as a value")
        if x.t == "split":
            raise Unsupported("Split() can only be assigned to a String array natively")
        if tag == "v":
            f = {"i": "RV_L", "f": "RV_D", "s": "RV_S", "b": "RV_B", "d": "RV_Dt"}.get(x.t)
            if f:
                return f"{f}({c})"
        elif x.t == "v":
            f = {"i": "RV_ToL", "f": "RV_ToD", "s": "RV_ToS", "b": "RV_ToB", "d": "RV_ToDate"}.get(tag)
            if f:
                return f"{f}({c})"
        elif tag == "i":
            if x.t in ("f", "d"):
                return f"CLng({c})"
            if x.t == "b":
                return c
            if x.t == "s":
                return f"CLng(VBNumS({c}))"
        elif tag == "f":
            if x.t in ("i", "b", "d"):
                return c
            if x.t == "s":
                return f"VBNumS({c})"
        elif tag == "s":
            f = {"i": "VBStrL", "f": "VBStrD", "b": "VBStrB", "d": "VBDateStr"}.get(x.t)
            if f:
                return f"{f}({c})"
        elif tag == "b":
            if x.t in ("i", "f", "d"):
                return f"(({c}) <> 0)"
            if x.t == "s":
                return f"VBBoolS({c})"
        elif tag == "d":
            if x.t in ("i", "f", "b"):
                return c
            if x.t == "s":
                return f"VBDateS({c})"
        raise Unsupported(f"type mismatch ({self.tagname(x.t)} where {self.tagname(tag)} is expected)")

    @staticmethod
    def tagname(t):
        return {"i": "number", "f": "number", "s": "String", "b": "Boolean", "d": "Date", "v": "Variant",
                "coll": "Collection", "form": "Form", "arr": "array", "carr": "control array"}.get(t, t)

    # ------------------------------------------------------------------ expressions
    def expr(self, e, ctx, want="value") -> E:
        if e is None:
            raise Unsupported("missing expression")
        h = getattr(self, "e_" + e[0], None)
        if h is None:
            raise Unsupported(f"expression '{e[0]}' is not supported natively", e[1])
        return h(e, ctx, want)

    def e_num(self, e, ctx, want):
        v = e[2]
        if isinstance(v, float):
            r = repr(v).replace("e+", "e")
            if "e" not in r and "." not in r:
                r += ".0"
            return E(r, "f")
        if abs(v) > 2147483647:
            return E(f"{v}LL", "i")
        return E(str(v), "i")

    def e_str(self, e, ctx, want):
        return E(fb_str(e[2]), "s")

    def e_bool(self, e, ctx, want):
        return E("VBTrue" if e[2] else "VBFalse", "b")

    def e_date(self, e, ctx, want):
        s = e[2]
        for f in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M", "%Y-%m-%d",
                  "%Y-%m-%d %H:%M:%S", "%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p", "%d/%m/%Y"):
            try:
                d = _dt.datetime.strptime(s, f)
                break
            except ValueError:
                continue
        else:
            raise Unsupported(f"date literal #{s}#", e[1])
        if d.year == 1900 and "%Y" not in f:
            d = d.replace(year=1899, month=12, day=30)
        delta = d - _dt.datetime(1899, 12, 30)
        return E(f"({delta.days + delta.seconds / 86400!r})", "d")

    def e_empty(self, e, ctx, want):
        return E("RV_Empty()", "v")

    def e_nothing(self, e, ctx, want):
        return E("0", "nothing")

    def e_paren(self, e, ctx, want):
        x = self.expr(e[2], ctx)
        if x.t == "ctl":
            x = self.ctl_default(x, ctx, e[1])
        return E(f"({x.code})", x.t, x.ctl, x.idcode, x.form, x.var)

    def e_new(self, e, ctx, want):
        c = self.classes.get(e[2].lower())
        if c is not None:
            return E(f"New {c.fb}()", "obj:" + e[2].lower())
        raise Unsupported(f"New {e[2]}: objects are not supported natively (only Collection)", e[1])

    def e_typeof(self, e, ctx, want):
        raise Unsupported("TypeOf ... Is is not supported natively", e[1])

    def e_named(self, e, ctx, want):
        raise Unsupported("named argument outside a call", e[1])

    def e_missing(self, e, ctx, want):
        return E("", "missing")

    def e_me(self, e, ctx, want):
        if ctx is not None and ctx.mi.cls is not None:
            return E("(@This)", "obj:" + ctx.mi.cls.name.lower())
        fi = ctx.mi.form if ctx else None
        if fi is None:
            raise Unsupported("Me outside a form", e[1])
        return E(fi.const, "form", form=fi)

    def e_withobj(self, e, ctx, want):
        if not ctx or not ctx.withs:
            raise Unsupported("'.' outside a With block", e[1])
        return ctx.withs[-1]

    def e_unop(self, e, ctx, want):
        op = e[2]
        x = self.expr(e[3], ctx)
        if x.t == "ctl":
            x = self.ctl_default(x, ctx, e[1])
        if op == "-":
            if x.t in ("i", "f"):
                return E(f"(-{x.code})", x.t)
            if x.t in ("b",):
                return E(f"(-{x.code})", "i")
            if x.t == "d":
                return E(f"(-{x.code})", "d")
            return E(f"RV_Neg({self.conv(x, 'v')})", "v")
        if op == "not":
            if x.t in ("b", "i"):
                return E(f"(Not {x.code})", x.t)
            if x.t in ("f", "d"):
                return E(f"(Not CLng({x.code}))", "i")
            if x.t == "s":
                return E(f"(Not CLng(VBNumS({x.code})))", "i")
            return E(f"RV_Not({self.conv(x, 'v')})", "v")
        raise Unsupported(f"operator {op}", e[1])

    def e_binop(self, e, ctx, want):
        op = e[2]
        a, b = self.expr(e[3], ctx), self.expr(e[4], ctx)
        if op == "is":
            def ptr(x):
                if x.t == "nothing":
                    return "0"
                if x.t.startswith("obj:"):
                    return x.code
                if x.t == "v":
                    return f"RV_ToObj({x.code})"
                raise Unsupported("Is compares objects", e[1])
            return E(f"({ptr(a)} = {ptr(b)})", "b")
        if a.t == "ctl":
            a = self.ctl_default(a, ctx, e[1])
        if b.t == "ctl":
            b = self.ctl_default(b, ctx, e[1])
        for x in (a, b):
            if x.t not in ("i", "f", "s", "b", "d", "v"):
                raise Unsupported(f"operator {op} on {self.tagname(x.t)}", e[1])
        anyv = "v" in (a.t, b.t)
        num = lambda t: t in NUMERIC
        if op == "&":
            return E(f"({self.conv(a, 's')} & {self.conv(b, 's')})", "s")
        if op in ("+", "-", "*"):
            if anyv or (a.t == "s" and b.t == "s" and op != "+") or (op == "+" and "s" in (a.t, b.t) and a.t != b.t):
                if op == "+" and a.t == "s" and b.t == "s":
                    return E(f"({a.code} & {b.code})", "s")
                f = {"+": "RV_Add", "-": "RV_Sub", "*": "RV_Mul"}[op]
                return E(f"{f}({self.conv(a, 'v')}, {self.conv(b, 'v')})", "v")
            if op == "+" and a.t == "s" and b.t == "s":
                return E(f"({a.code} & {b.code})", "s")
            if "d" in (a.t, b.t):
                if op == "-" and a.t == "d" and b.t == "d":
                    return E(f"({a.code} - {b.code})", "f")
                if op in ("+", "-"):
                    return E(f"({self.conv(a, 'f')} {op} {self.conv(b, 'f')})", "d")
            t = "i" if a.t in ("i", "b") and b.t in ("i", "b") else "f"
            if t == "i" and op == "*":          # the IDE's interpreter has no 32-bit overflow
                return E(f"(CLngInt({a.code}) * {b.code})", t)
            return E(f"({self.conv(a, t)} {op} {self.conv(b, t)})", t)
        if op in ("/", "\\", "mod", "^"):
            if anyv or "s" in (a.t, b.t):
                f = {"/": "RV_Div", "\\": "RV_IDiv", "mod": "RV_Mod", "^": "RV_Pow"}[op]
                return E(f"{f}({self.conv(a, 'v')}, {self.conv(b, 'v')})", "v")
            if op == "/":
                return E(f"VBDiv({self.conv(a, 'f')}, {self.conv(b, 'f')})", "f")
            if op == "\\":
                return E(f"VBIDiv({self.conv(a, 'f')}, {self.conv(b, 'f')})", "i")
            if op == "mod":
                return E(f"VBMod({self.conv(a, 'f')}, {self.conv(b, 'f')})", "i")
            return E(f"({self.conv(a, 'f')} ^ {self.conv(b, 'f')})", "f")
        if op in ("=", "<>", "<", ">", "<=", ">="):
            if a.t == "s" and b.t == "s":
                return E(f"({a.code} {op} {b.code})", "b")
            if num(a.t) and num(b.t):
                return E(f"({a.code} {op} {b.code})", "b")
            return E(f"(RV_Cmp({self.conv(a, 'v')}, {self.conv(b, 'v')}) {op} 0)", "b")
        if op == "like":
            return E(f"VBLike({self.conv(a, 's')}, {self.conv(b, 's')})", "b")
        if op in ("and", "or", "xor", "eqv", "imp"):
            if anyv:
                if op in ("eqv", "imp"):
                    raise Unsupported(f"{op.title()} on Variants", e[1])
                f = {"and": "RV_And", "or": "RV_Or", "xor": "RV_Xor"}[op]
                return E(f"{f}({self.conv(a, 'v')}, {self.conv(b, 'v')})", "v")
            t = "b" if a.t == "b" and b.t == "b" else "i"
            x, y = self.conv(a, t), self.conv(b, t)
            if op == "eqv":
                return E(f"(Not ({x} Xor {y}))", t)
            if op == "imp":
                return E(f"((Not {x}) Or {y})", t)
            return E(f"({x} {op.title()} {y})", t)
        raise Unsupported(f"operator {op}", e[1])

    # names -------------------------------------------------------------
    def var_ref(self, vi: VarInfo, ctx) -> str:
        return vi.fb

    def e_name(self, e, ctx, want):
        name = e[2]
        raw = e[3] if len(e) > 3 else name
        base = re.sub(r"[$%&!#@]$", "", name)
        line = e[1]
        # variables
        if ctx is not None:
            if ctx.pi.ret is not None and base == ctx.pi.name.split(":")[-1] and want != "call":
                return E("vb_res", ctx.pi.ret.tag, lval=True)
            vi = ctx.lookup_var(base)
            if vi is not None:
                return self.var_expr(vi, ctx, line)
        else:
            vi = self.cur_mod.vars.get(base) if self.cur_mod else None
            vi = vi or self.gvars.get(base)
            if vi is not None:
                return self.var_expr(vi, ctx, line)
        mi = ctx.mi if ctx else self.cur_mod
        fi = mi.form if mi else None
        if mi is not None and mi.cls is not None and base in mi.cls.props:
            pr = mi.cls.props[base]
            if want == "lvalue":
                setter = pr.get("let") or pr.get("set")
                if setter is None:
                    raise Unsupported(f"property {raw} has no Let", line)
                return E(f"This.{setter.fb} = {{V}}", "setfn", idcode=setter.params[-1].tag if setter.params else "v")
            if "get" in pr:
                return E(f"This.{pr['get'].fb}", pr["get"].ret.tag)
        # controls of this form
        if fi is not None:
            ci = fi.ctls.get(base)
            if ci is not None and not ci.array:
                return E(ci.const, "ctl", ctl=ci, idcode=ci.const)
            if base in fi.arrays:
                return E(fi.array_const(base), "carr", ctl=fi.arrays[base], form=fi)
        # procedures
        pi = self.find_proc(base, mi)
        if pi is not None:
            if want == "call":
                return E(pi.fb, "proc", var=pi)
            return self.call_proc(pi, [], ctx, line)
        # forms
        if base in self.form_by_name:
            f = self.form_by_name[base]
            return E(f.const, "form", form=f)
        if base in self.enum_members:
            return E(base, "enum")
        for m in self.mods:
            if m.name.lower() == base and m.form is None:
                return E(base, "module", var=m)
        if base in ("app", "screen", "clipboard", "err", "debug", "printer"):
            if base == "err" and want not in ("object", "call"):
                return E("VBErr.Number", "i", lval=True)
            return E(base, "sys:" + base)
        if base in VB_CONSTANTS:
            c, t = VB_CONSTANTS[base]
            return E(c, t)
        b = self.builtin(base, [], ctx, line, bare=True)
        if b is not None:
            return b
        if fi is not None and (base in F.FORM_PROPS or base in F.FORM_MOTION):
            return self.form_member(E(fi.const, "form", form=fi), base, [], ctx, line, want)
        if fi is not None and base in fi.fx_names:          # fx8.Begin / Storyboard1.Stop
            return E(fb_str(raw), "fxsb", form=fi)
        # implicit variable (no Option Explicit)
        if ctx is not None and not mi.explicit:
            vi = ctx.implicit.get(base)
            if vi is None:
                vi = VarInfo(base, self.safe(self.spell(mi, base), local=True), "variant", "v", "RVar")
                ctx.implicit[base] = vi
            return E(vi.fb, "v", var=vi, lval=True)
        raise Unsupported(f"'{raw}' is not declared (or not supported natively)", line)

    def var_expr(self, vi: VarInfo, ctx, line) -> E:
        if vi.scope == "const":
            if vi.tag == "" and getattr(vi, "expr", None) is not None:
                x = self.expr(vi.expr, None)
                vi.tag = x.t if x.t in ("i", "f", "s", "b", "d") else "v"
                vi.fbtype = TAG_FB.get(vi.tag, "RVar")
            if getattr(vi, "enum_value", None) is not None and vi.tag == "":
                vi.tag = "i"
            return E(vi.fb, vi.tag or "i")
        if vi.dims is not None:
            return E(vi.fb, "arr", var=vi, lval=True)
        return E(vi.fb, vi.tag, var=vi, lval=True)

    def find_proc(self, name, mi):
        if mi is not None and name in mi.procs:
            return mi.procs[name]
        return self.gprocs.get(name)

    # calls -------------------------------------------------------------
    def e_call(self, e, ctx, want):
        _, line, target, args = e
        if target[0] == "name":
            name = re.sub(r"[$%&!#@]$", "", target[2])
            vi = ctx.lookup_var(name) if ctx else (self.cur_mod.vars.get(name) if self.cur_mod else None) or self.gvars.get(name)
            if ctx is not None and ctx.pi.ret is not None and name == ctx.pi.name.split(":")[-1] and args:
                vi = None
            if vi is not None:
                if vi.dims is not None:
                    return self.index_array(E(vi.fb, "arr", var=vi), args, ctx, line)
                if vi.tag == "coll":
                    return self.coll_item(E(vi.fb, "coll", var=vi), args, ctx, line)
                if vi.tag == "v" and args:
                    raise Unsupported(f"{name}(...): arrays inside a Variant are not supported natively", line)
            mi = ctx.mi if ctx else self.cur_mod
            fi = mi.form if mi else None
            if fi is not None and name in fi.arrays and (vi is None):
                return self.ctl_array_item(fi, name, args, ctx, line)
            pi = self.find_proc(name, mi)
            if pi is not None:
                return self.call_proc(pi, args, ctx, line)
            if fi is not None and name in F.FORM_MOTION:      # GoToState "Alert" inside the form's module
                return self.form_member(E(fi.const, "form", form=fi), name, args, ctx, line, want)
            b = self.builtin(name, args, ctx, line)
            if b is not None:
                return b
            raise Unsupported(f"'{target[3] if len(target) > 3 else name}' is not a known Sub/Function/array", line)
        if target[0] == "member":
            obj = self.expr(target[2], ctx, want="object")
            return self.member(obj, target[3], args, ctx, line, want, called=True)
        base = self.expr(target, ctx)
        if base.t == "carr":
            raise Unsupported("control array", line)
        if base.t == "coll":
            return self.coll_item(base, args, ctx, line)
        if base.t == "ctl" and base.ctl.type in ("ListBox", "ComboBox"):
            raise Unsupported("default member call on a control", line)
        raise Unsupported("call on an expression", line)

    def index_array(self, a: E, args, ctx, line) -> E:
        vi = a.var
        if vi.dims and len(args) != len(vi.dims):
            raise Unsupported(f"{vi.name}: wrong number of subscripts", line)
        idx = []
        for k, arg in enumerate(args):
            x = self.expr(arg, ctx)
            idx.append(f"VBIX({a.code}, {k + 1}, {self.conv(x, 'f') if x.t != 'i' else x.code})")
        tag = vi.tag
        ev = VarInfo(vi.name, vi.fb, vi.vbtype, vi.tag, vi.fbtype)
        ev.fixlen = getattr(vi, "fixlen", 0)
        return E(f"{a.code}({', '.join(idx)})", tag, var=ev, lval=True)

    def coll_item(self, c: E, args, ctx, line) -> E:
        if len(args) != 1:
            raise Unsupported("Collection item needs one key / index", line)
        return E(f"VBColItem({c.code}, {self.conv(self.expr(args[0], ctx), 'v')})", "v")

    def ctl_array_item(self, fi, name, args, ctx, line) -> E:
        if len(args) != 1:
            raise Unsupported(f"{name}(...): control arrays have one index", line)
        items = fi.arrays[name]
        first = items[min(items)]
        arr = fi.array_const(name)
        x = self.expr(args[0], ctx)
        code = f"{arr}(VBIX({arr}, 1, {self.conv(x, 'f') if x.t != 'i' else x.code}))"
        return E(code, "ctl", ctl=first, idcode=code)

    def arg_list(self, pi: ProcInfo, args, ctx, line) -> list[str]:
        params = pi.params
        vals: list = [None] * len(params)
        pos = 0
        for a in args:
            if a[0] == "named":
                for i, p in enumerate(params):
                    if p.name == a[2]:
                        vals[i] = a[3]
                        break
                else:
                    raise Unsupported(f"{pi.proc.display}: no parameter {a[2]}", line)
            else:
                if pos >= len(params):
                    raise Unsupported(f"{pi.proc.display}: too many arguments", line)
                vals[pos] = a if a[0] != "missing" else None
                pos += 1
        out = []
        for p, a in zip(params, vals):
            if a is None:
                if not getattr(p, "optional", False):
                    raise Unsupported(f"{pi.proc.display}: argument {p.name} is not optional", line)
                d = getattr(p, "default", None)
                if p.dims is not None:
                    raise Unsupported("optional array parameter", line)
                if d is not None:
                    out.append(self.conv(self.expr(d, None), p.tag))
                else:
                    out.append({"i": "0", "f": "0", "s": '""', "b": "0", "d": "0", "v": "RV_Missing()"}.get(p.tag, "0"))
                continue
            x = self.expr(a, ctx)
            if p.dims is not None:
                if x.t != "arr":
                    raise Unsupported(f"{pi.proc.display}: {p.name} needs an array", line)
                if x.var.fbtype != p.fbtype:
                    raise Unsupported(f"{pi.proc.display}: array type mismatch for {p.name}", line)
                out.append(f"{x.code}()")
                continue
            if p.tag.startswith("obj:"):
                out.append(self.conv(x, p.tag))
                continue
            if p.tag.startswith("udt:") or p.tag == "coll":
                if x.t != p.tag:
                    raise Unsupported(f"{pi.proc.display}: type mismatch for {p.name}", line)
                out.append(x.code)
                continue
            out.append(self.conv(x, p.tag))
        return out

    def call_proc(self, pi: ProcInfo, args, ctx, line, obj: str = "") -> E:
        a = self.arg_list(pi, args, ctx, line)
        if pi.mod.cls is not None:
            obj = obj or "This."
        code = f"{obj}{pi.fb}({', '.join(a)})"
        if pi.kind == "sub":
            return E(code, "none")
        return E(code, pi.ret.tag)

    def call_statement(self, target, args, ctx, line):
        """A call used as a statement: Foo a, b / obj.Method a / MsgBox "x"."""
        if target[0] == "name":
            name = re.sub(r"[$%&!#@]$", "", target[2])
            mi = ctx.mi
            pi = self.find_proc(name, mi)
            if pi is not None and ctx.lookup_var(name) is None:
                return self.call_proc(pi, args, ctx, line).code
            st = self.statement_builtin(name, args, ctx, line)
            if st is not None:
                return st
            x = self.expr(("call", line, target, args) if args else target, ctx, want="call")
            if x.t in ("none", "i", "f", "s", "b", "d", "v"):
                return x.code
            raise Unsupported(f"'{name}' cannot be called as a statement", line)
        if target[0] == "member":
            obj = self.expr(target[2], ctx, want="object")
            x = self.member(obj, target[3], args, ctx, line, "stmt", called=True)
            if x.t == "noop":
                return None
            return x.code
        x = self.expr(("call", line, target, args), ctx)
        return x.code

    # members -------------------------------------------------------------
    def e_member(self, e, ctx, want):
        _, line, obj, name, raw = e
        o = self.expr(obj, ctx, want="object")
        return self.member(o, name, [], ctx, line, want)

    def member(self, o: E, name, args, ctx, line, want, called=False) -> E:
        name = re.sub(r"[$%&!#@]$", "", name.lower())
        if o.t == "form":
            fi = o.form
            ci = fi.ctls.get(name)
            if ci is not None and not ci.array:
                x = E(ci.const, "ctl", ctl=ci, idcode=ci.const)
                if args:
                    return self.ctl_call_default(x, args, ctx, line)
                return x
            if name in fi.arrays:
                if args:
                    return self.ctl_array_item(fi, name, args, ctx, line)
                return E(fi.array_const(name), "carr", ctl=fi.arrays[name], form=fi)
            return self.form_member(o, name, args, ctx, line, want)
        if o.t == "ctl":
            return self.ctl_member(o, name, args, ctx, line, want)
        if o.t == "fxsb":                                   # a storyboard / animation as an object
            if name in ("begin", "stop") and not args and want != "lvalue":
                self.uses_fx = True
                return E(f"{'VBFxBegin' if name == 'begin' else 'VBFxStopAnim'}({o.form.const}, {o.code})", "b")
            raise Unsupported(f"Storyboard.{name} is not supported natively (Begin / Stop are)", line)
        if o.t == "carr":
            items = o.ctl
            if name == "count":
                return E(str(len(items)), "i")
            if name == "ubound":
                return E(str(max(items)), "i")
            if name == "lbound":
                return E(str(min(items)), "i")
            raise Unsupported(f"control array .{name}", line)
        if o.t.startswith("udt:"):
            fields = self.udt_fields.get(o.t[4:], {})
            fv = fields.get(name)
            if fv is None:
                raise Unsupported(f"Type {o.t[4:]} has no field {name}", line)
            code = f"{o.code}.{fv.fb}"
            if fv.dims is not None:
                a = E(code, "arr", var=fv)
                if args:
                    return self.index_array(a, args, ctx, line)
                return a
            return E(code, fv.tag, var=fv, lval=True)
        if o.t == "coll":
            if name == "count":
                return E(f"{o.code}.count", "i")
            if name == "item":
                return self.coll_item(o, args, ctx, line)
            if name == "add":
                vals = ["RV_Empty()"] * 4
                vals[1] = '""'
                pos = 0
                for a in args:
                    if a[0] == "named":
                        k = ["item", "key", "before", "after"].index(a[2]) if a[2] in ("item", "key", "before", "after") else None
                        if k is None:
                            raise Unsupported(f"Collection.Add {a[2]}:=", line)
                        val = a[3]
                    else:
                        k, val = pos, a
                        pos += 1
                    if val[0] == "missing":
                        continue
                    x = self.expr(val, ctx)
                    vals[k] = self.conv(x, "s" if k == 1 else "v")
                return E(f"VBColAdd({o.code}, {', '.join(vals)})", "none")
            if name == "remove":
                return E(f"VBColRemove({o.code}, {self.conv(self.expr(args[0], ctx), 'v')})", "none")
            raise Unsupported(f"Collection.{name}", line)
        if o.t == "enum":
            m = self.enum_members.get(o.code, {}).get(name)
            if m is None:
                raise Unsupported(f"enum member {name}", line)
            return E(m, "i")
        if o.t == "module":
            mi = o.var
            if name in mi.procs:
                pi = mi.procs[name]
                return self.call_proc(pi, args, ctx, line)
            if name in mi.vars or name in self.gvars:
                vi = mi.vars.get(name) or self.gvars[name]
                x = self.var_expr(vi, ctx, line)
                if args and x.t == "arr":
                    return self.index_array(x, args, ctx, line)
                return x
            raise Unsupported(f"{mi.name}.{name}", line)
        if o.t.startswith("sys:"):
            return self.object_member(o.t[4:], name, args, ctx, line, want)
        if o.t.startswith("obj:") and o.t[4:] in self.classes:
            return self.class_member(o, name, args, ctx, line, want)
        if o.t == "arr" and name in ("count",):
            raise Unsupported("array .Count", line)
        raise Unsupported(f".{name} on {self.tagname(o.t)} is not supported natively", line)

    def class_member(self, o: E, name, args, ctx, line, want) -> E:
        c = self.classes[o.t[4:]]
        mi = c.mi
        ref = o.code if o.code == "(@This)" else f"{c.fb}__chk({o.code})"
        fv = mi.vars.get(name)
        if fv is not None and fv.scope == "field":
            if c.mi is not (ctx.mi if ctx else None) and False:
                pass
            code = f"{ref}->{fv.fb}"
            if fv.dims is not None:
                a = E(code, "arr", var=fv)
                return self.index_array(a, args, ctx, line) if args else a
            return E(code, fv.tag, var=fv, lval=True)
        if name in c.props:
            pr = c.props[name]
            if want == "lvalue":
                setter = pr.get("let") or pr.get("set")
                if setter is None:
                    raise Unsupported(f"{c.name}.{name} is read-only", line)
                return E(f"{ref}->{setter.fb} = {{V}}", "setfn", idcode=setter.params[-1].tag if setter.params else "v")
            if "get" not in pr:
                raise Unsupported(f"{c.name}.{name} has no Property Get", line)
            return E(f"{ref}->{pr['get'].fb}", pr["get"].ret.tag)
        pi = mi.procs.get(name)
        if pi is not None and pi.kind in ("sub", "function"):
            return self.call_proc(pi, args, ctx, line, obj=f"{ref}->")
        raise Unsupported(f"class {c.name} has no member {name}", line)

    def object_member(self, obj, name, args, ctx, line, want) -> E:
        A = lambda i, t: self.conv(self.expr(args[i], ctx), t)
        if obj == "err":
            if name == "number":
                return E("VBErr.Number", "i", lval=True) if want != "lvalue" else E("VBErrSetNumber({V})", "setfn", idcode="i")
            if name == "description":
                return E("VBErr.Description", "s", lval=True)
            if name == "source":
                return E("VBErr.Source", "s", lval=True)
            if name == "lastdllerror":
                return E("VBErr.LastDllError", "i")
            if name == "clear":
                return E("VBErrClear()", "none")
            if name == "raise":
                n = A(0, "i") if args else "0"
                desc = '""'
                for k, a in enumerate(args):
                    if a[0] == "named" and a[2] == "description":
                        desc = self.conv(self.expr(a[3], ctx), "s")
                    elif a[0] != "named" and k == 2 and a[0] != "missing":
                        desc = A(2, "s")
                if args and args[0][0] == "named":
                    n = self.conv(self.expr(args[0][3], ctx), "i")
                return E(f"VBRaise({n}, {desc})", "none")
        if obj == "app":
            ver = (getattr(self.cfg, "version", "") or "1.0.0").split(".") if self.cfg else ["1", "0", "0"]
            ver = (ver + ["0", "0", "0"])[:3]
            vals = {"path": ("vbAppPath", "s"), "title": ("vbAppTitle", "s"),
                    "exename": (fb_str(self.exe_name()), "s"), "previnstance": ("0", "b"),
                    "major": (str(int(ver[0]) if ver[0].isdigit() else 1), "i"),
                    "minor": (str(int(ver[1]) if ver[1].isdigit() else 0), "i"),
                    "revision": (str(int(ver[2]) if ver[2].isdigit() else 0), "i"),
                    "productname": ("vbAppTitle", "s"), "companyname": ('""', "s"), "comments": ('""', "s")}
            if name in vals:
                return E(*vals[name], lval=name == "title")
        if obj == "screen":
            if name == "width":
                return E("VBScreenW()", "i")
            if name == "height":
                return E("VBScreenH()", "i")
            if name in ("twipsperpixelx", "twipsperpixely"):
                return E("15", "i")
            if name == "mousepointer":
                return E("", "noop") if want in ("lvalue", "stmt") else E("0", "i")
        if obj == "clipboard":
            if name == "settext":
                return E(f"VBClipSet({A(0, 's')})", "none")
            if name == "gettext":
                return E("VBClipGet()", "s")
            if name == "clear":
                return E("VBClipClear()", "none")
        if obj == "debug":
            if name == "assert":
                return E("", "noop")
        raise Unsupported(f"{obj.title()}.{name} is not supported natively", line)

    def exe_name(self):
        try:
            return self.cfg.exe_base()
        except Exception:  # noqa: BLE001
            return self.project.name

    def form_member(self, o: E, name, args, ctx, line, want) -> E:
        fid = o.code
        if name == "show":
            modal = self.conv(self.expr(args[0], ctx), "i") if args and args[0][0] != "missing" else "0"
            return E(f"VBFormShow({fid}, {modal})", "none")
        if name == "hide":
            return E(f"VBFormHide({fid})", "none")
        if name == "unload":
            return E(f"VBFormUnload({fid}, 1)", "none")
        if name == "load":
            return E(f"VBFormLoad({fid})", "none")
        if name == "setfocus":
            return E(f"VBSetFocus({fid})", "none")
        if name == "move":
            return self.move_call(fid, args, ctx)
        if name in F.FORM_NOOP_METHODS:
            return E("", "noop")
        if name in F.FORM_MOTION:
            return self.motion_call(fid, name, args, ctx, line, want)
        if name == "animate":
            raise Unsupported("Form.Animate (a preset chosen in code) needs the preset builders at run time - design "
                              "the animation with trigger \"Manual (from code)\" and call BeginAnimation", line)
        if name == "controls":
            raise Unsupported("Form.Controls is not supported natively", line)
        if name == "caption" or name in F.FORM_PROPS:
            prop, tag = F.FORM_PROPS[name]
            if want == "lvalue":
                fn = "VBSetS" if tag == "s" else "VBSetN"
                return E(f"{fn}({fid}, {prop}, {{V}})", "prop", idcode="s" if tag == "s" else "f")
            if tag == "s":
                return E(f"VBGetS({fid}, {prop})", "s")
            return E(f"VBGetN({fid}, {prop})" if tag == "f" else f"CLng(VBGetN({fid}, {prop}))", tag)
        if name in F.FORM_IGNORED_SET and want == "lvalue":
            return E("", "noop")
        raise Unsupported(f"Form.{name} is not supported natively", line)

    def motion_call(self, fid, name, args, ctx, line, want) -> E:
        """BeginAnimation / StopAnimation / GoToState / ApplySizeVariants / CurrentSizes / CurrentState of a form."""
        self.uses_fx = True
        if want == "lvalue":
            raise Unsupported(f"Form.{name} is read-only", line)
        if any(a[0] == "named" for a in args):
            raise Unsupported(f"named arguments in {name}", line)

        def arg(i):
            if len(args) <= i or args[i][0] == "missing":
                return None
            return self.expr(args[i], ctx)
        if name in ("beginanimation", "stopanimation"):
            a = arg(0)
            if a is None:
                raise Unsupported(f"{name} needs the animation / storyboard name", line)
            fn = "VBFxBegin" if name == "beginanimation" else "VBFxStopAnim"
            return E(f"{fn}({fid}, {self.conv(a, 's')})", "b")
        if name == "gotostate":
            a = arg(0)
            if a is None:
                raise Unsupported("GoToState needs the state name", line)
            c = arg(1)
            if c is None:
                return E(f"VBFxGoToState({fid}, {fid}, {self.conv(a, 's')})", "b")
            if c.t == "ctl":
                return E(f"VBFxGoToState({fid}, {c.idcode}, {self.conv(a, 's')})", "b")
            return E(f"VBFxGoToStateN({fid}, {self.conv(c, 's')}, {self.conv(a, 's')})", "b")
        if args:
            raise Unsupported(f"Form.{name} takes no arguments", line)
        if name == "applysizevariants":
            return E(f"VBFxApplySizes({fid})", "b")
        if name == "currentsizes":
            return E(f"VBFxCurrentSizes({fid})", "s")
        return E(f"VBFxCurrentState({fid})", "s")

    def move_call(self, fid, args, ctx):
        vals = []
        for a in args[:4]:
            vals.append("-1e300" if a[0] == "missing" else self.conv(self.expr(a, ctx), "f"))
        return E(f"VBMove({fid}, {', '.join(vals)})", "none")

    def ctl_default(self, x: E, ctx, line) -> E:
        p = F.DEFAULT_PROP.get(x.ctl.type)
        if not p:
            raise Unsupported(f"{x.ctl.name} has no default property", line)
        return self.ctl_prop(x, p, ctx, line)

    def ctl_call_default(self, x, args, ctx, line):
        raise Unsupported(f"{x.ctl.name}(...)", line)

    def ctl_prop(self, x: E, name, ctx, line, setter=False) -> E:
        ci = x.ctl
        idc = x.idcode
        t = ci.type if not ci.menu else "Menu"
        if ci.menu:
            m = {"caption": ("vbpText", "s"), "enabled": ("vbpEnabled", "b"), "checked": ("vbpChecked", "b"),
                 "visible": ("vbpVisible", "b"), "tag": ("vbpTag", "s"), "name": ("vbpName", "s")}.get(name)
            if m is None:
                raise Unsupported(f"menu item .{name} is not supported natively", line)
            prop, tag = m
        else:
            spec = F.PROPS.get(name)
            if spec is None:
                if setter and name in F.IGNORED_SET:
                    return E("", "noop")
                raise Unsupported(f"{ci.name}.{name} ({t}) is not supported natively", line)
            prop, tag, kinds = spec
            if t in F.DIALOGS and name in F.FONT_DIALOG_PROPS:
                kinds = None if t == "FontDialog" else kinds
                if t != "FontDialog":
                    raise Unsupported(f"{ci.name}.{name} ({t})", line)
            elif kinds == "all":
                pass
            elif kinds is None:
                if t not in F.VISUAL and not (t == "Timer" and name == "enabled"):
                    raise Unsupported(f"{ci.name}.{name} ({t}) is not supported natively", line)
            elif t not in kinds:
                if setter and name in F.IGNORED_SET:
                    return E("", "noop")
                raise Unsupported(f"{ci.name}.{name} ({t}) is not supported natively", line)
            if name == "value":
                tag = F.VALUE_TAG.get(t, "i")
            if t == "Timer" and name == "enabled":
                tag = "b"
        if setter:
            fn = "VBSetS" if tag == "s" else "VBSetN"
            return E(f"{fn}({idc}, {prop}, {{V}})", "prop", idcode="s" if tag == "s" else (tag if tag in ("f", "d") else
                                                                                           ("i" if tag != "b" else "b")))
        if tag == "s":
            return E(f"VBGetS({idc}, {prop})", "s")
        if tag in ("f", "d"):
            return E(f"VBGetN({idc}, {prop})", tag)
        return E(f"CLng(VBGetN({idc}, {prop}))", tag)

    def ctl_member(self, x: E, name, args, ctx, line, want) -> E:
        ci = x.ctl
        idc = x.idcode
        t = ci.type if not ci.menu else "Menu"
        A = lambda i, tg: self.conv(self.expr(args[i], ctx), tg)
        if name == "font":
            return E(idc, "font", ctl=ci, idcode=idc)
        if t in ("ListBox", "ComboBox"):
            if name == "additem":
                idx = A(1, "i") if len(args) > 1 and args[1][0] != "missing" else "-1"
                return E(f"VBAddItem({idc}, {A(0, 's')}, {idx})", "none")
            if name == "removeitem":
                return E(f"VBRemoveItem({idc}, {A(0, 'i')})", "none")
            if name == "clear":
                return E(f"VBClear({idc})", "none")
            if name == "list":
                if not args:
                    raise Unsupported("List without an index", line)
                if want == "lvalue":
                    return E(f"VBListSet({idc}, {A(0, 'i')}, {{V}})", "setfn", idcode="s")
                return E(f"VBListGet({idc}, {A(0, 'i')})", "s")
        if t == "TextBox" and name == "clear":
            return E(f"VBClear({idc})", "none")
        if t == "TabControl" and name == "tabcaption":
            if want == "lvalue":
                return E(f"VBTabCaptionSet({idc}, {A(0, 'i')}, {{V}})", "setfn", idcode="s")
            return E(f"VBTabCaption({idc}, {A(0, 'i')})", "s")
        if t in F.DIALOGS:
            meth = {"showopen": f"VBShowFile({idc}, 0)", "showsave": f"VBShowFile({idc}, -1)",
                    "showcolor": f"VBShowColor({idc})", "showfont": f"VBShowFont({idc})",
                    "showfolder": f"VBShowFolder({idc})"}
            if name in meth:
                return E(meth[name], "b")
            if name == "showdialog":
                return E(f"VBShowDialog({idc})", "s")
        if t == "Timer" and name in ("start", "stop"):
            return E(f"VBSetN({idc}, vbpEnabled, {'-1' if name == 'start' else '0'})", "none")
        if name == "setfocus":
            return E(f"VBSetFocus({idc})", "none")
        if name == "refresh":
            return E(f"VBRefresh({idc})", "none")
        if name == "move":
            return self.move_call(idc, args, ctx)
        if name == "zorder":
            return E(f"VBZOrder({idc}, {A(0, 'i') if args else '0'})", "none")
        if name == "gotostate" and not ci.menu:     # a control's own visual state (rt/vbrt_motion.bi)
            if not args or args[0][0] in ("missing", "named"):
                raise Unsupported("GoToState needs the state name", line)
            self.uses_fx = True
            return E(f"VBFxGoToState({ci.form.const}, {idc}, {A(0, 's')})", "b")
        if name == "animate":
            raise Unsupported(f"{ci.name}.Animate (a preset chosen in code) needs the preset builders at run time - "
                              "design the animation with trigger \"Manual (from code)\" and call BeginAnimation", line)
        if args:
            raise Unsupported(f"{ci.name}.{name}(...) is not supported natively", line)
        return self.ctl_prop(x, name, ctx, line, setter=(want == "lvalue"))

    # builtins -------------------------------------------------------------
    def statement_builtin(self, name, args, ctx, line):
        A = lambda i, t: self.conv(self.expr(args[i], ctx), t)
        if name == "msgbox":
            return self.builtin("msgbox", args, ctx, line).code
        if name in ("randomize",):
            return "VBRandomize()"
        if name == "beep":
            return "VBBeep()"
        if name == "doevents":
            return "VBDoEvents()"
        if name == "kill":
            return f"VBKill({A(0, 's')})"
        if name == "mkdir":
            return f"VBMkDir({A(0, 's')})"
        if name == "rmdir":
            return f"VBRmDir({A(0, 's')})"
        if name == "chdir":
            return f"VBChDir({A(0, 's')})"
        if name == "chdrive":
            return None
        if name == "filecopy":
            return f"VBFileCopy({A(0, 's')}, {A(1, 's')})"
        if name == "sleep":
            return f"Sleep_({A(0, 'i')})" if False else f"Sleep {A(0, 'i')}, 1"
        if name == "savesetting" or name == "deletesetting":
            raise Unsupported(f"{name}: the registry is not supported natively", line)
        if name == "sendkeys":
            raise Unsupported("SendKeys is not supported natively", line)
        if name == "appactivate":
            raise Unsupported("AppActivate is not supported natively", line)
        if name == "date" or name == "time":
            raise Unsupported(f"setting the system {name}", line)
        return None

    def builtin(self, name, args, ctx, line, bare=False) -> E | None:
        name = name.rstrip("$")
        n = len(args)
        if any(a[0] == "named" for a in args) and name not in ("msgbox", "inputbox"):
            raise Unsupported(f"named arguments in {name}()", line)

        def A(i, t):
            return self.conv(self.expr(args[i], ctx), t)

        def X(i):
            x = self.expr(args[i], ctx)
            if x.t == "ctl":
                x = self.ctl_default(x, ctx, line)
            return x

        def has(i):
            return n > i and args[i][0] != "missing"

        simple = {
            "len": None, "left": ("VBLeft({0}, {1})", "si", "s"), "right": ("VBRight({0}, {1})", "si", "s"),
            "ucase": ("VBUCase({0})", "s", "s"), "lcase": ("VBLCase({0})", "s", "s"),
            "trim": ("Trim({0})", "s", "s"), "ltrim": ("LTrim({0})", "s", "s"), "rtrim": ("RTrim({0})", "s", "s"),
            "space": ("VBSpace({0})", "i", "s"), "strreverse": ("VBStrReverse({0})", "s", "s"),
            "chr": ("VBChr({0})", "i", "s"), "chrw": ("VBChr({0})", "i", "s"), "chrb": ("VBChr({0})", "i", "s"),
            "asc": ("VBAsc({0})", "s", "i"), "ascw": ("VBAsc({0})", "s", "i"), "ascb": ("VBAsc({0})", "s", "i"),
            "val": ("VBVal({0})", "s", "f"), "str": ("VBStrFn({0})", "f", "s"),
            "sqr": ("VBSqr({0})", "f", "f"), "exp": ("Exp({0})", "f", "f"), "log": ("VBLog({0})", "f", "f"),
            "sin": ("Sin({0})", "f", "f"), "cos": ("Cos({0})", "f", "f"), "tan": ("Tan({0})", "f", "f"),
            "atn": ("Atn({0})", "f", "f"), "sgn": ("VBSgn({0})", "f", "i"),
            "hex": ("VBHex(CLngInt({0}))", "f", "s"), "oct": ("VBOct(CLngInt({0}))", "f", "s"),
            "year": ("VBYear({0})", "d", "i"), "month": ("VBMonth({0})", "d", "i"), "day": ("VBDay({0})", "d", "i"),
            "hour": ("VBHour({0})", "d", "i"), "minute": ("VBMinute({0})", "d", "i"),
            "second": ("VBSecond({0})", "d", "i"), "weekday": ("VBWeekday({0})", "d", "i"),
            "dateserial": ("VBDateSerial({0}, {1}, {2})", "iii", "d"),
            "timeserial": ("VBTimeSerial({0}, {1}, {2})", "iii", "d"),
            "dateadd": ("VBDateAdd({0}, {1}, {2})", "sfd", "d"), "datediff": ("VBDateDiff({0}, {1}, {2})", "sdd", "i"),
            "datepart": ("VBDatePart({0}, {1})", "sd", "i"),
            "datevalue": ("Int({0})", "d", "d"), "timevalue": ("({0} - Int({0}))", "d", "d"),
            "cdate": ("{0}", "d", "d"), "cdbl": ("{0}", "f", "f"), "csng": ("CSng({0})", "f", "f"),
            "cdec": ("{0}", "f", "f"), "ccur": ("VBRound({0}, 4)", "f", "f"),
            "cint": ("CLng({0})", "f", "i"), "clng": ("CLng({0})", "f", "i"), "cbyte": ("CLng({0})", "f", "i"),
            "clnglng": ("CLngInt({0})", "f", "i"),
            "cstr": ("{0}", "s", "s"), "cbool": ("{0}", "b", "b"), "cvar": ("{0}", "v", "v"),
            "rgb": ("(({0}) + ({1}) * 256 + ({2}) * 65536)", "iii", "i"),
            "environ": ("VBEnviron({0})", "s", "s"), "eof": ("VBEOF({0})", "i", "b"), "lof": ("VBLOF({0})", "i", "i"),
            "filelen": ("VBFileLen({0})", "s", "i"), "error": ("VBErrMsg({0})", "i", "s"),
            "monthname": None, "weekdayname": None,
        }
        noarg = {"now": ("VBNow()", "d"), "date": ("VBToday()", "d"), "time": ("VBTimeNow()", "d"),
                 "timer": ("VBTimer()", "f"), "rnd": ("VBRnd()", "f"), "freefile": ("VBFreeFile()", "i"),
                 "curdir": ("VBCurDir()", "s"), "command": ("VBCommand()", "s"), "doevents": ("(VBDoEvents(): 0)", "i"),
                 "err": ("VBErr.Number", "i"), "error": ("VBErr.Description", "s")}
        if bare or n == 0:
            if name in noarg and not (name == "doevents"):
                return E(*noarg[name])
            if name == "doevents" and bare:
                return None
            if bare:
                return None
        if name == "len":
            x = X(0)
            if x.t == "arr" or x.t.startswith("udt:"):
                raise Unsupported("Len() of an array / Type is not supported natively", line)
            return E(f"VBLen({self.conv(x, 's')})", "i")
        if name == "mid":
            ln = f", {A(2, 'i')}" if has(2) else ""
            return E(f"VBMid({A(0, 's')}, {A(1, 'i')}{ln})", "s")
        if name == "instr":
            x0 = X(0)
            if n >= 3 and x0.t in ("i", "f"):
                cmp = A(3, "i") if has(3) else "0"
                return E(f"VBInStr({self.conv(x0, 'i')}, {A(1, 's')}, {A(2, 's')}, {cmp})", "i")
            cmp = A(2, "i") if has(2) else "0"
            return E(f"VBInStr(1, {self.conv(x0, 's')}, {A(1, 's')}, {cmp})", "i")
        if name == "instrrev":
            st = A(2, "i") if has(2) else "-1"
            cmp = A(3, "i") if has(3) else "0"
            return E(f"VBInStrRev({A(0, 's')}, {A(1, 's')}, {st}, {cmp})", "i")
        if name == "replace":
            return E(f"VBReplace({A(0, 's')}, {A(1, 's')}, {A(2, 's')})", "s")
        if name == "string":
            c = X(1)
            ch = self.conv(c, "s") if c.t == "s" else f"VBChr({self.conv(c, 'i')})"
            return E(f"VBStringN({A(0, 'i')}, {ch})", "s")
        if name == "strcomp":
            return E(f"VBStrComp({A(0, 's')}, {A(1, 's')}, {A(2, 'i') if has(2) else '0'})", "i")
        if name == "strconv":
            return E(f"VBStrConv({A(0, 's')}, {A(1, 'i')})", "s")
        if name in ("int", "fix", "abs"):
            x = X(0)
            if x.t == "v":
                f = {"int": "Int", "fix": "Fix", "abs": "Abs"}[name]
                return E(f"{f}(RV_ToD({x.code}))", "f")
            if x.t == "s":
                x = E(f"VBNumS({x.code})", "f")
            if x.t in ("i", "b"):
                return E(f"Abs({x.code})" if name == "abs" else x.code, "i")
            return E(f"{ {'int': 'Int', 'fix': 'Fix', 'abs': 'Abs'}[name] }({self.conv(x, 'f')})", "f")
        if name == "round":
            return E(f"VBRound({A(0, 'f')}, {A(1, 'i') if has(1) else '0'})", "f")
        if name in ("format", "format$"):
            f = A(1, "s") if has(1) else '""'
            x = X(0)
            return E(f"VBFormat({self.conv(x, 'v')}, {f})", "s")
        if name == "formatnumber" or name == "formatcurrency":
            return E(f"VBFormatNumber({A(0, 'f')}, {A(1, 'i') if has(1) else '2'})", "s")
        if name == "formatpercent":
            d = A(1, "i") if has(1) else "2"
            return E(f"(VBFmtNumber({A(0, 'f')} * 100, \"0\" & IIf({d} > 0, \".\" & String({d}, \"0\"), \"\")) & \"%\")", "s")
        if name == "iif":
            c = self.cond(args[0], ctx)
            a, b = X(1), X(2)
            if a.t == b.t and a.t in ("i", "f", "s", "b", "d"):
                return E(f"IIf({c}, {a.code}, {b.code})", a.t)
            if a.t in ("i", "f", "b") and b.t in ("i", "f", "b"):
                return E(f"IIf({c}, {self.conv(a, 'f')}, {self.conv(b, 'f')})", "f")
            return E(f"RV_IIf({c}, {self.conv(a, 'v')}, {self.conv(b, 'v')})", "v")
        if name in ("isnumeric",):
            x = X(0)
            if x.t == "s":
                return E(f"VBIsNumericS({x.code})", "b")
            if x.t == "v":
                return E(f"RV_IsNum({x.code})", "b")
            return E("VBTrue" if x.t in ("i", "f", "b") else "VBFalse", "b")
        if name == "isempty":
            x = X(0)
            return E(f"({x.code}.vt = 0)" if x.t == "v" else "VBFalse", "b")
        if name == "isnull":
            x = X(0)
            return E(f"({x.code}.vt = 1)" if x.t == "v" else "VBFalse", "b")
        if name == "ismissing":
            x = X(0)
            return E(f"({x.code}.vt = 10)" if x.t == "v" else "VBFalse", "b")
        if name == "isarray":
            x = X(0)
            return E("VBTrue" if x.t == "arr" else "VBFalse", "b")
        if name == "isobject":
            x = X(0)
            return E("VBTrue" if x.t.startswith("obj:") else (f"({x.code}.vt = 9)" if x.t == "v" else "VBFalse"), "b")
        if name == "isdate":
            x = X(0)
            if x.t == "d":
                return E("VBTrue", "b")
            if x.t == "s":
                tmp = ctx.temp("vb_dt", "Double")
                return E(f"VBTryDate({x.code}, {tmp})", "b")
            if x.t == "v":
                tmp = ctx.temp("vb_dt", "Double")
                return E(f"IIf({x.code}.vt = 7, -1, IIf({x.code}.vt = 8, VBTryDate({x.code}.s, {tmp}), 0))", "b")
            return E("VBFalse", "b")
        if name in ("typename", "vartype"):
            x = X(0)
            if x.t.startswith("obj:"):
                return E(fb_str(self.classes[x.t[4:]].name), "s") if name == "typename" else E("9", "i")
            if x.t == "v":
                return E(f"RV_TypeName({x.code})" if name == "typename" else f"RV_VarType({x.code})",
                         "s" if name == "typename" else "i")
            vt = x.var.vbtype.lower() if x.var is not None else {"i": "long", "f": "double", "s": "string",
                                                                   "b": "boolean", "d": "date"}.get(x.t, "")
            names = {"integer": ("Integer", 2), "long": ("Long", 3), "single": ("Single", 4), "double": ("Double", 5),
                     "currency": ("Currency", 6), "date": ("Date", 7), "string": ("String", 8),
                     "boolean": ("Boolean", 11), "byte": ("Byte", 17), "longlong": ("LongLong", 20)}
            if x.t == "arr":
                nm, code = names.get(x.var.vbtype.lower(), ("Variant", 12))
                return E(fb_str(nm + "()"), "s") if name == "typename" else E(str(8192 + code), "i")
            if vt in names:
                nm, code = names[vt]
                return E(fb_str(nm), "s") if name == "typename" else E(str(code), "i")
            raise Unsupported(f"{name}() of this value", line)
        if name in ("ubound", "lbound"):
            x = self.expr(args[0], ctx)
            if x.t != "arr":
                raise Unsupported(f"{name.title()}() needs an array variable natively", line)
            d = f", {A(1, 'i')}" if has(1) else ""
            return E(f"{name.title()}({x.code}{d})", "i")
        if name == "split":
            lim = A(2, "i") if has(2) else "-1"
            d = A(1, "s") if has(1) else '" "'
            return E(f"VBSplit({A(0, 's')}, {d}, {{ARR}}, {lim})", "split")
        if name == "join":
            x = self.expr(args[0], ctx)
            if x.t != "arr":
                raise Unsupported("Join() needs an array variable natively", line)
            d = A(1, "s") if has(1) else '" "'
            if x.var.tag == "s":
                return E(f"VBJoin({x.code}(), {d})", "s")
            if x.var.tag == "v":
                return E(f"VBJoinV({x.code}(), {d})", "s")
            raise Unsupported("Join() of a non-String array", line)
        if name == "msgbox":
            vals = [None, None, None]
            pos = 0
            for a in args:
                if a[0] == "named":
                    k = {"prompt": 0, "buttons": 1, "title": 2}.get(a[2])
                    if k is None:
                        continue
                    vals[k] = a[3]
                else:
                    if pos < 3 and a[0] != "missing":
                        vals[pos] = a
                    pos += 1
            p = self.conv(self.expr(vals[0], ctx), "s") if vals[0] else '""'
            b = self.conv(self.expr(vals[1], ctx), "i") if vals[1] else "0"
            t = self.conv(self.expr(vals[2], ctx), "s") if vals[2] else '""'
            return E(f"VBMsgBox({p}, {b}, {t})", "i")
        if name == "inputbox":
            vals = [None, None, None]
            pos = 0
            for a in args:
                if a[0] == "named":
                    k = {"prompt": 0, "title": 1, "default": 2}.get(a[2])
                    if k is not None:
                        vals[k] = a[3]
                else:
                    if pos < 3 and a[0] != "missing":
                        vals[pos] = a
                    pos += 1
            p, t, d = (self.conv(self.expr(v, ctx), "s") if v else '""' for v in vals)
            return E(f"VBInputBox({p}, {t}, {d})", "s")
        if name == "monthname":
            return E(f"VBMonthName({A(0, 'i')}, {A(1, 'b') if has(1) else '0'})", "s")
        if name == "weekdayname":
            return E(f"VBWeekdayName({A(0, 'i')}, {A(1, 'b') if has(1) else '0'})", "s")
        if name == "dir":
            if n == 0:
                return E("VBDirNext()", "s")
            return E(f"VBDir({A(0, 's')}, {A(1, 'i') if has(1) else '0'})", "s")
        if name == "input":
            return E(f"VBInputChars({A(0, 'i')}, {A(1, 'i')})", "s")
        if name == "shell":
            return E(f"VBShell({A(0, 's')}, {A(1, 'i') if has(1) else '1'})", "i")
        if name == "loadpicture":
            x = X(0) if n else E('""', "s")
            if args and args[0][0] == "str" and args[0][2] not in self.images:
                self.images.append(args[0][2])
            return E(self.conv(x, "s"), "s")
        if name in ("createobject", "getobject", "callbyname", "radcall", "array", "choose", "switch", "filter",
                    "getsetting", "getallsettings", "qbcolor", "nz", "objptr", "strptr", "varptr", "partition",
                    "filedatetime", "getattr", "lenb"):
            raise Unsupported(f"{name}() is not supported natively", line)
        spec = simple.get(name)
        if spec:
            tmpl, tags, ret = spec
            if n < len(tags):
                raise Unsupported(f"{name}() needs {len(tags)} arguments", line)
            vals = [A(i, t) for i, t in enumerate(tags)]
            return E(tmpl.format(*vals), ret)
        if name in noarg:
            return E(*noarg[name])
        return None


class Ctx:
    """State of the procedure being translated."""

    def __init__(self, tr: Translator, pi: ProcInfo):
        self.tr, self.pi, self.mi = tr, pi, pi.mod
        self.locals: dict = {p.name: p for p in pi.params}
        self.implicit: dict = {}
        self.decls: list = []
        self.temps: dict = {}
        self.withs: list = []
        self.loops: list = []
        self.uses_handler = False
        self.resume_next = False
        self.resume_points_wanted = False
        self.resume_points = 0
        self.resume_lines: list = []
        self.handler_labels: dict = {}
        self.gosub = False
        self.gosub_points: list = []
        self.return_lines: list = []
        self.cond_calls = False
        self._n = 0
        # does the procedure use On Error Resume Next / Resume Next anywhere? (decides resume points)
        flat = repr(pi.proc.body)
        self.resume_points_wanted = "'onerror', " in flat and ("'next')" in flat)

    def new_id(self):
        self._n += 1
        return self._n

    def temp(self, name, typ):
        self.temps.setdefault(name, typ)
        return name

    def lookup_var(self, name):
        if name in self.locals:
            return self.locals[name]
        if name in self.implicit:
            return self.implicit[name]
        if name in self.mi.vars:
            return self.mi.vars[name]
        return self.tr.gvars.get(name)


def translate_project(folder, project=None, fb_root=None, cfg=None) -> Translation:
    t = Translator(Path(folder), project, fb_root, cfg)
    try:
        res = t.run()
    except Unsupported as u:
        t.reasons.append(u.msg)
        res = Translation(reasons=t.reasons)
    return res


__all__ = ["Translation", "Translator", "translate_project"]
