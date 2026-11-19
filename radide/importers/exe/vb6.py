"""Visual Basic 5/6 programs (.exe) -> .frm text -> the existing VB6 importer -> RAD IDE project.

A VB6 exe starts with ``push <VBHeader>; call ThunRTMain``.  The VB header ("VB5!") leads to:
  ProjectInfo -> ObjectTable -> one PublicObjectDescriptor per form/module/class (names, object type)
  -> ObjectInfo (+ OptionalObjectInfo for forms) -> the control table (control names, event handler
  table: which events have code), and the GUI table -> the compiled form data of every form.
This module reads those structures (layout per the public "VB image internal structure" documentation),
rebuilds a ``.frm`` per form (form caption/size, controls with their names, types, captions and - when
the compiled property stream is decodable - positions; otherwise a tidy grid) plus empty event
procedures for the events that have code, and hands it to radide/importers/vb6_import.py.
P-code / native code bodies are not decompiled: the report lists the string constants of the program
and the procedures that need rewriting (AI can help from the editor).
Only for programs you wrote, own, or may legally analyse.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from .base import BinaryInfo, ImportResult
from .dotnet import say, set_form_code, set_startup

# control name prefix -> VB class (used when the class GUID is not one we know)
PREFIX_CLASS = [
    (r"^(cmd|command|btn|button)", "VB.CommandButton"), (r"^(txt|text)", "VB.TextBox"),
    (r"^(lbl|label)", "VB.Label"), (r"^(chk|check)", "VB.CheckBox"), (r"^(opt|option)", "VB.OptionButton"),
    (r"^(cbo|cmb|combo)", "VB.ComboBox"), (r"^(lst|list)", "VB.ListBox"), (r"^(fra|frame)", "VB.Frame"),
    (r"^(pic|picture)", "VB.PictureBox"), (r"^(img|image)", "VB.Image"), (r"^(tmr|timer)", "VB.Timer"),
    (r"^(hsb|hscroll)", "VB.HScrollBar"), (r"^(vsb|vscroll)", "VB.VScrollBar"), (r"^(shp|shape)", "VB.Shape"),
    (r"^(lin|line)", "VB.Line"), (r"^(drv|drive)", "VB.DriveListBox"), (r"^(dir)", "VB.DirListBox"),
    (r"^(fil|file)", "VB.FileListBox"), (r"^(dat|data)", "VB.Data"), (r"^(mnu|menu)", "VB.Menu"),
]
DEFAULT_SIZE = {"VB.CommandButton": (1215, 495), "VB.TextBox": (2175, 375), "VB.Label": (1815, 255),
                "VB.CheckBox": (1815, 255), "VB.OptionButton": (1815, 255), "VB.ComboBox": (2175, 315),
                "VB.ListBox": (2175, 1230), "VB.Frame": (3015, 1575), "VB.PictureBox": (1215, 1215),
                "VB.Image": (1215, 1215), "VB.HScrollBar": (2175, 255), "VB.VScrollBar": (255, 1215)}
DEFAULT_EVENT = {"VB.CommandButton": "Click", "VB.TextBox": "Change", "VB.Label": "Click",
                 "VB.CheckBox": "Click", "VB.OptionButton": "Click", "VB.ComboBox": "Click",
                 "VB.ListBox": "Click", "VB.Timer": "Timer", "VB.Menu": "Click", "VB.PictureBox": "Click",
                 "VB.Image": "Click", "VB.Frame": "Click", "VB.HScrollBar": "Change", "VB.VScrollBar": "Change",
                 "VB.Form": "Load"}
HAS_CAPTION = {"VB.CommandButton", "VB.Label", "VB.CheckBox", "VB.OptionButton", "VB.Frame", "VB.Menu",
               "VB.Form"}


# ============================================================================ image access
class Image:
    """Virtual-address reads over a PE file (or a raw buffer + image base, for tests)."""

    def __init__(self, data: bytes, base: int, sections: list[tuple[int, int, int, int]]):
        self.data, self.base, self.sections = data, base, sections   # (va, vsize, raw_off, raw_size)

    @staticmethod
    def from_pe(path: Path) -> "Image":
        import pefile
        pe = pefile.PE(str(path), fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        secs = [(base + s.VirtualAddress, max(s.Misc_VirtualSize, s.SizeOfRawData), s.PointerToRawData,
                 s.SizeOfRawData) for s in pe.sections]
        img = Image(pe.__data__[:], base, secs)
        img.entry = base + pe.OPTIONAL_HEADER.AddressOfEntryPoint
        pe.close()
        return img

    def off(self, va: int) -> int | None:
        for sva, vsize, raw, rsize in self.sections:
            if sva <= va < sva + vsize:
                o = raw + (va - sva)
                return o if va - sva < rsize else None
        return None

    def va(self, off: int) -> int | None:
        for sva, _vs, raw, rsize in self.sections:
            if raw <= off < raw + rsize:
                return sva + (off - raw)
        return None

    def read(self, va: int, n: int) -> bytes:
        o = self.off(va)
        if o is None:
            raise ValueError(f"address {va:#x} outside the image")
        return self.data[o:o + n]

    def u32(self, va: int) -> int:
        return struct.unpack("<I", self.read(va, 4))[0]

    def u16(self, va: int) -> int:
        return struct.unpack("<H", self.read(va, 2))[0]

    def cstr(self, va: int, limit: int = 260) -> str:
        if not va:
            return ""
        raw = self.read(va, limit)
        return raw.split(b"\0", 1)[0].decode("latin-1")

    def valid(self, va: int) -> bool:
        return bool(va) and self.off(va) is not None


IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")


# ============================================================================ structures
def find_header(img: Image) -> int | None:
    ent = getattr(img, "entry", None)
    if ent is not None:
        try:
            code = img.read(ent, 10)
            if code[0] == 0x68:                                  # push imm32
                va = struct.unpack("<I", code[1:5])[0]
                if img.valid(va) and img.read(va, 4) == b"VB5!":
                    return va
        except ValueError:
            pass
    o = img.data.find(b"VB5!")
    return img.va(o) if o >= 0 else None


def parse_vb(img: Image) -> dict:
    """Everything we can read: project, objects (forms/modules/classes), controls, form data blobs."""
    hdr = find_header(img)
    if hdr is None:
        raise ValueError("VB5! header not found")
    h = img.read(hdr, 0x68)
    info: dict = {"header": hdr}
    (lp_sub_main, lp_project, _f1, _f2, _tflags, _tcount, form_count, _ext_count, _thunks, lp_gui,
     _lp_ext, _lp_com, b_desc, b_exe, _b_help, b_name) = struct.unpack_from("<IIIIIIHHIIIIIIII", h, 0x2C)
    info["form_count"] = form_count
    info["has_sub_main"] = bool(lp_sub_main)
    for key, rel in (("description", b_desc), ("exe_name", b_exe), ("project_name", b_name)):
        try:
            info[key] = img.cstr(hdr + rel) if rel and rel < 0x10000 else ""
        except ValueError:
            info[key] = ""
    # ---- ProjectInfo -> ObjectTable
    objects = []
    if img.valid(lp_project):
        lp_objtable = img.u32(lp_project + 0x04)
        lp_native = img.u32(lp_project + 0x20)
        info["native_code"] = bool(lp_native)
        if img.valid(lp_objtable):
            ot = img.read(lp_objtable, 0x54)
            total = struct.unpack_from("<H", ot, 0x2A)[0]
            lp_array = struct.unpack_from("<I", ot, 0x30)[0]
            lp_pname = struct.unpack_from("<I", ot, 0x40)[0]
            if img.valid(lp_pname):
                info["project_name"] = img.cstr(lp_pname) or info.get("project_name", "")
            for k in range(min(total, 512)):
                d = lp_array + k * 0x30
                if not img.valid(d):
                    break
                obj = _object(img, d)
                if obj:
                    objects.append(obj)
    info["objects"] = objects
    # ---- GUI table: compiled form data
    forms_data = []
    if img.valid(lp_gui):
        for k in range(min(form_count, 256)):
            g = lp_gui + k * 0x50
            if not img.valid(g):
                break
            size = img.u32(g)
            if size != 0x50:
                break
            lp_form = img.u32(g + 0x48)
            forms_data.append(lp_form if img.valid(lp_form) else 0)
    info["form_data"] = forms_data
    return info


def _object(img: Image, d: int) -> dict | None:
    lp_info, _r, _pub, _stat, _mpub, _mstat, lp_name, method_count, lp_methods, _sv, ftype, _n = \
        struct.unpack("<12I", img.read(d, 0x30))
    name = img.cstr(lp_name) if img.valid(lp_name) else ""
    if not IDENT.match(name or ""):
        return None
    obj = {"name": name, "type_flags": ftype, "kind": "module", "controls": [], "methods": []}
    if ftype & 0x80:
        obj["kind"] = "form"
    elif ftype & 0x02 and not ftype & 0x80:
        obj["kind"] = "class" if ftype & 0x800 else "module"
    if img.valid(lp_methods):
        for k in range(min(method_count, 512)):
            try:
                p = img.u32(lp_methods + 4 * k)
                if img.valid(p):
                    m = img.cstr(p)
                    if IDENT.match(m):
                        obj["methods"].append(m)
            except ValueError:
                break
    if ftype & 0x80 and img.valid(lp_info):
        opt = lp_info + 0x38                          # OptionalObjectInfo follows ObjectInfo
        try:
            count = img.u32(opt + 0x20)
            lp_ctrls = img.u32(opt + 0x24)
        except ValueError:
            count, lp_ctrls = 0, 0
        if img.valid(lp_ctrls):
            for k in range(min(count, 1024)):
                c = lp_ctrls + k * 0x28
                try:
                    events = img.u16(c + 0x02)
                    lp_events = img.u32(c + 0x14)
                    lp_cname = img.u32(c + 0x1C)
                    index = img.u16(c + 0x0C)
                except ValueError:
                    break
                cname = img.cstr(lp_cname) if img.valid(lp_cname) else ""
                if not IDENT.match(cname or ""):
                    continue
                handled = []
                if img.valid(lp_events):
                    for s in range(min(events, 64)):
                        try:
                            if img.u32(lp_events + 0x18 + 4 * s):
                                handled.append(s)
                        except ValueError:
                            break
                obj["controls"].append({"name": cname, "index": index, "event_slots": handled})
    return obj


# ============================================================================ compiled form data
def _strings_in(blob: bytes) -> list[tuple[int, str]]:
    """Length-prefixed (word) ANSI strings of a compiled form property stream."""
    out = []
    i = 0
    while i + 2 < len(blob):
        n = blob[i] | (blob[i + 1] << 8)
        if 1 <= n <= 255 and i + 2 + n <= len(blob):
            s = blob[i + 2:i + 2 + n]
            if all(32 <= b < 127 or b >= 0xA0 for b in s):
                out.append((i, s.decode("latin-1")))
                i += 2 + n
                continue
        i += 1
    return out


def decode_form_data(img: Image, va: int, known: set[str], max_len: int = 0x8000) -> dict:
    """Best-effort reading of a compiled form: {name: {"caption", "geometry" (l, t, w, h) or None}}.

    The property stream stores each control as its name followed by property opcodes; strings are
    word-length prefixed and Left/Top/Width/Height are 4 consecutive 32-bit twip values right after the
    position opcode (0x04 in the intrinsic controls' tables).  Values are only taken when they look like
    twips (0..65535) - otherwise the caller lays the controls out on a grid."""
    try:
        blob = img.read(va, max_len)
    except ValueError:
        return {}
    out: dict = {}
    strings = _strings_in(blob)
    for k, (pos, txt) in enumerate(strings):
        if txt not in known or txt in out:
            continue
        entry = out.setdefault(txt, {"caption": None, "geometry": None, "pos": pos})
        nxt = strings[k + 1] if k + 1 < len(strings) else None
        if nxt and nxt[0] - pos < 64 + len(txt) and nxt[1] not in known:
            entry["caption"] = nxt[1]
        # geometry: opcode 0x04 followed by 4 int32 twips, in the bytes after the name
        seg = blob[pos + 2 + len(txt):pos + 2 + len(txt) + 160]
        j = seg.find(b"\x04")
        while 0 <= j < len(seg) - 16:
            vals = struct.unpack_from("<4i", seg, j + 1)
            if all(0 <= v <= 65535 for v in vals) and vals[2] > 0 and vals[3] > 0:
                entry["geometry"] = vals
                break
            j = seg.find(b"\x04", j + 1)
    return out


# ============================================================================ .frm text
def vb_class_for(name: str) -> str:
    low = name.lower()
    for rx, cls in PREFIX_CLASS:
        if re.match(rx, low):
            return cls
    return "VB.CommandButton" if low.startswith("b") else "VB.Label"


def build_frm(form: dict, form_data: dict, notes: list[str]) -> tuple[str, int, int]:
    """(frm text, controls placed exactly, controls placed on a grid)."""
    name = form["name"]
    fd = form_data.get(name, {})
    caption = fd.get("caption") or name
    geo = fd.get("geometry")
    cw, ch = (geo[2], geo[3]) if geo else (6000, 4500)
    lines = ["VERSION 5.00", f"Begin VB.Form {name}", f'   Caption         =   "{caption}"',
             f"   ClientHeight    =   {ch}", f"   ClientWidth     =   {cw}", "   ScaleMode       =   1  'Twip",
             "   StartUpPosition =   2  'CenterScreen"]
    exact = grid = 0
    x, y, row_h = 120, 120, 0
    menus = []
    seen = set()
    for c in form["controls"]:
        cname = c["name"]
        if cname == name or cname in seen:
            continue
        seen.add(cname)
        cls = vb_class_for(cname)
        if cls == "VB.Menu":
            menus.append((cname, (form_data.get(cname) or {}).get("caption") or cname))
            continue
        cd = form_data.get(cname, {})
        w, h = DEFAULT_SIZE.get(cls, (1215, 495))
        g = cd.get("geometry")
        if g:
            left, top, w, h = g
            exact += 1
        else:
            if x + w > cw - 120:
                x, y = 120, y + row_h + 120
                row_h = 0
            left, top = x, y
            x += w + 120
            row_h = max(row_h, h)
            grid += 1
        lines.append(f"   Begin {cls} {cname}")
        if cls in HAS_CAPTION or cls == "VB.TextBox":
            cap = cd.get("caption") or cname
            key = "Text" if cls == "VB.TextBox" else "Caption"
            lines.append(f'      {key:<16}=   "{cap}"')
        if cls == "VB.Timer":
            lines.append("      Interval        =   1000")
        lines += [f"      Height          =   {h}", f"      Left            =   {left}",
                  f"      Top             =   {top}", f"      Width           =   {w}", "   End"]
    for mname, mcap in menus:
        lines += [f"   Begin VB.Menu {mname}", f'      Caption         =   "{mcap}"', "   End"]
    lines += ["End", f'Attribute VB_Name = "{name}"']
    # event procedures: the default event of each control whose event table has code
    for c in form["controls"]:
        if not c["event_slots"]:
            continue
        if c["name"] == name:          # Form_Load & co: the RAD IDE form already has <Form>_Load
            notes.append(f"{name}: the form's own events have compiled code - see {name}_Load")
            continue
        cls = "VB.Form" if c["name"] == name else vb_class_for(c["name"])
        ev = DEFAULT_EVENT.get(cls, "Click")
        lines += [f"Private Sub {'Form' if c['name'] == name else c['name']}_{ev}()",
                  "   ' compiled code not decompiled - rewrite this procedure"
                  f" ({len(c['event_slots'])} event(s) with code in the exe)", "End Sub"]
    if grid:
        notes.append(f"{name}: {grid} control(s) placed on a grid (their positions were not decodable)")
    return "\n".join(lines) + "\n", exact, grid


def unicode_strings(data: bytes, minimum: int = 4, limit: int = 400) -> list[str]:
    out = []
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minimum, data):
        s = m.group(0).decode("utf-16-le")
        if s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


# ============================================================================ backend API
def can_handle(info: BinaryInfo) -> bool:
    return getattr(info, "kind", "") == "vb6"


def run(path, info: BinaryInfo, workdir, progress=None, ai_translate: bool = False,
        image: Image | None = None) -> ImportResult:
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    say(progress, "Reading the Visual Basic structures ...")
    try:
        img = image or Image.from_pe(path)
        vb = parse_vb(img)
    except Exception as e:  # noqa: BLE001
        res.add("error", f"The VB5!/VB6 structures could not be read ({e}).")
        return res
    strings = unicode_strings(img.data)
    res.resources["strings"] = strings
    res.resources["vb_project"] = {k: vb.get(k) for k in ("project_name", "exe_name", "description",
                                                          "form_count", "native_code")}
    forms = [o for o in vb["objects"] if o["kind"] == "form"]
    others = [o for o in vb["objects"] if o["kind"] != "form"]
    res.add("exact", f"VB project '{vb.get('project_name') or path.stem}': {len(forms)} form(s), {len(others)} "
                     f"module/class(es); code compiled to {'native code' if vb.get('native_code') else 'P-code'}.")
    if not forms:
        res.add("missing", "No form structure found in the program.")
    # compiled form data blobs, matched to forms in order
    form_data: dict = {}
    known = {f["name"] for f in forms} | {c["name"] for f in forms for c in f["controls"]}
    for va in vb["form_data"]:
        if va:
            form_data.update(decode_form_data(img, va, known))
    src = workdir / "vb6"
    src.mkdir(parents=True, exist_ok=True)
    res.source_dir = src
    notes: list[str] = []
    frm_files = []
    for f in forms:
        text, exact, grid = build_frm(f, form_data, notes)
        p = src / f"{f['name']}.frm"
        p.write_text(text, encoding="latin-1", errors="replace")
        frm_files.append(p)
        res.add("exact" if not grid else "rules",
                f"Form {f['name']}: {len(f['controls'])} control(s) by name"
                + (f", {exact} with their original position" if exact else "")
                + (f", {grid} placed on a grid" if grid else "") + ".")
    for n in notes:
        res.add("warn", n)
    for o in others:
        body = f'Attribute VB_Name = "{o["name"]}"\n' + "".join(
            f"Public Sub {m}()\n   ' compiled code not decompiled\nEnd Sub\n\n" for m in o["methods"])
        (src / f"{o['name']}.bas").write_text(body, encoding="latin-1", errors="replace")
        res.modules.append((f"{o['name']}.bas", body, "vb6"))
    if frm_files:
        vbp = src / f"{re.sub(r'[^A-Za-z0-9_]', '_', vb.get('project_name') or path.stem)}.vbp"
        vbp.write_text("Type=Exe\n" + "".join(f"Form={p.name}\n" for p in frm_files) +
                       f'Startup="{forms[0]["name"]}"\nName="{vb.get("project_name") or path.stem}"\n',
                       encoding="latin-1")
        _import_frms(vbp, workdir, res)
    res.add("missing", "Procedure bodies are compiled (P-code / native) and were not decompiled: the event "
                       "procedures are empty stubs. The program's text constants are listed in the import "
                       f"report resources ({len(strings)} strings).")
    return res


def _import_frms(vbp: Path, workdir: Path, res: ImportResult, language: str = "python-tk") -> None:
    import json
    import shutil
    from ..vb6_import import import_vb6
    from ...languages import get_plugin
    dest = workdir / "vbproject"
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    rep = import_vb6(vbp, dest, language)
    for w in rep.warnings:
        res.add("warn", w)
    if rep.project is None:
        return
    plugin = get_plugin(language)
    for fname in rep.project.forms:
        res.forms.append((fname, json.loads((dest / f"{fname}.form").read_text(encoding="utf-8"))))
        cp = dest / plugin.code_file(fname)
        if cp.exists():
            set_form_code(res, fname, cp.read_text(encoding="utf-8"), language)
    set_startup(res, rep.project.startup)
    res.resources["form_code_language"] = language
    res.add("rules", f".frm rebuilt and imported with the VB6 importer: {rep.forms} form(s), {rep.handlers} "
                     "event procedure stub(s).")
