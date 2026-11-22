"""VB6 form files (.frm / .frx) - read into the neutral model and WRITE BACK in place.

The .frm text is kept as a list of physical lines (with their own line separators); the
``Begin ... End`` blocks, ``BeginProperty ... EndProperty`` blocks and property lines are located by
line index.  Saving applies only the edits that the designer really made (a moved control changes its
``Left``/``Top`` lines, a new caption its ``Caption`` line, ...); everything else - unknown properties,
third-party OCX controls, comments after values, property order, ``Object = ...`` header lines, the
``Attribute VB_*`` lines and the code - stays byte-for-byte.  A form opened and saved without changes
is byte-identical.

Main entry points::

    doc = parse_frm(text)                      # FrmDoc
    form, info = load_form(text, frm_path, cache_dir)   # neutral Form (+ warnings, frx info)
    head, code = split_code(text)              # header+attributes / code section ("\\n" lines)
    text = join_code(head, code, newline)
    new_text, notes = apply_form_changes(text, base_form, new_form, frm_path)
    text = new_frm_text(form, code)            # a brand-new form (Add Form)

.frx resources (``Frx``): strings (1-byte or 0xFF+WORD length), lists (WORD count, WORD length +
bytes per item) and pictures (12-byte ``lt\\0\\0`` header) are read; changed values are APPENDED to the
.frx and the .frm reference is updated (the old data stays, unreferenced - VB6 compacts it on its next
save), so untouched resources keep their offsets.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from ..components import vb6map as _vb6map
from ..controls import CONTROL_TYPES
from ..model import Control, Form

TWIP = 15
MAX_NESTING = 200           # controls inside containers inside ... (VB6 forms never get near this)
_NL =re.compile(r"\r\n|\n|\r")
_BEGIN = re.compile(r"^(\s*)Begin\s+(\S+)\s+(\S+)\s*$", re.I)
_BEGINPROP = re.compile(r"^(\s*)BeginProperty\s+(\S+)", re.I)
_ENDPROP = re.compile(r"^\s*EndProperty\s*$", re.I)
_END = re.compile(r"^\s*End\s*$", re.I)
_PROP = re.compile(r"^(\s*)([^=\s'][^=]*?)(\s*=\s*)(.*)$")
_FRXREF = re.compile(r'^\$?"([^"]*)":([0-9A-Fa-f]+)')

# OCX libraries used for controls the IDE adds (frm "Object =" / vbp "Object=" lines)
OCX = {
    "MSComDlg": ("{F9043C88-F6F2-101A-A3C9-08002B2F49FB}#1.2#0", "COMDLG32.OCX"),
    "MSComctlLib": ("{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0", "MSCOMCTL.OCX"),
    "MSComCtl2": ("{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0", "MSCOMCT2.OCX"),
    "TabDlg": ("{BDC217C8-ED16-11CD-956C-0000C04E4C0A}#1.1#0", "TABCTL32.OCX"),
    "MSFlexGridLib": ("{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0", "MSFLXGRD.OCX"),
}
FONT_GUID = "{0BE35203-8F91-11CE-9DE3-00AA004BB851}"

# neutral type -> VB6 class written for NEW controls: "vb6": {"class": ...} of the component manifests
# (radide/components/builtin/<Type>/component.json, radide/components/vb6map.py)
NEW_CLASS = _vb6map.new_class_map()
_TEXT_CLASSES = ("vb.textbox", "vb.combobox", "richtextlib.richtextbox")


# ============================================================================ lines
def split_lines(text: str) -> tuple[list[str], list[str]]:
    """Physical lines and the separator after each ("" after the last line without one)."""
    lines, seps, pos = [], [], 0
    for m in _NL.finditer(text):
        lines.append(text[pos:m.start()])
        seps.append(m.group())
        pos = m.end()
    if pos < len(text) or not lines:
        lines.append(text[pos:])
        seps.append("")
    return lines, seps


def join_lines(lines: list[str], seps: list[str]) -> str:
    return "".join(a + b for a, b in zip(lines, seps))


def dominant_newline(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf >= lf else "\n"


# ============================================================================ values
def parse_value(raw: str):
    """Value of a property line: str, int, float, ("frx", file, offset) or the raw token."""
    raw = raw.strip()
    m = _FRXREF.match(raw)
    if m:
        return ("frx", m.group(1), int(m.group(2), 16))
    if raw.startswith('"'):
        out, i = [], 1
        while i < len(raw):
            ch = raw[i]
            if ch == '"':
                if i + 1 < len(raw) and raw[i + 1] == '"':
                    out.append('"')
                    i += 2
                    continue
                break
            out.append(ch)
            i += 1
        return "".join(out)
    raw = raw.split("'")[0].strip()
    m = re.fullmatch(r"&H([0-9A-Fa-f]+)&?", raw)
    if m:
        return int(m.group(1), 16)
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def vb_str(s) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def vb_bool(b) -> str:
    return "-1  'True" if b else "0   'False"


def vb_color(c: str) -> str | None:
    m = re.fullmatch(r"#?([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})", str(c or "").strip())
    if not m:
        return None
    r, g, b = m.groups()
    return f"&H00{b.upper()}{g.upper()}{r.upper()}&"


def color_from_vb(v) -> str:
    if not isinstance(v, int) or v & 0x80000000:
        return ""
    return f"#{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"


# ============================================================================ structure
@dataclass
class FrmProp:
    key: str
    line: int
    raw: str                      # text after "="

    @property
    def value(self):
        return parse_value(self.raw)


@dataclass
class FrmPropBlock:
    name: str
    start: int
    end: int = -1
    props: list = field(default_factory=list)
    blocks: list = field(default_factory=list)

    def prop(self, key: str):
        k = key.lower()
        return next((p for p in self.props if p.key.lower() == k), None)


@dataclass
class FrmBlock:
    cls: str
    name: str
    start: int
    indent: str
    end: int = -1
    props: list = field(default_factory=list)
    pblocks: list = field(default_factory=list)
    children: list = field(default_factory=list)
    parent: "FrmBlock | None" = None

    def prop(self, key: str):
        k = key.lower()
        return next((p for p in self.props if p.key.lower() == k), None)

    def pblock(self, name: str):
        n = name.lower()
        return next((b for b in self.pblocks if b.name.lower() == n), None)

    def get(self, key: str, default=None):
        p = self.prop(key)
        return default if p is None else p.value

    @property
    def index(self):
        v = self.get("Index")
        return v if isinstance(v, int) else None

    @property
    def is_menu(self) -> bool:
        return self.cls.lower() == "vb.menu"

    @property
    def neutral_name(self) -> str:
        return self.name if self.index is None else f"{self.name}_{self.index}"

    def walk(self):
        # pre-order without recursion: a (corrupted) form nested thousands of levels deep must not hit
        # Python's recursion limit
        stack = list(reversed(self.children))
        while stack:
            c = stack.pop()
            yield c
            stack.extend(reversed(c.children))


@dataclass
class FrmDoc:
    lines: list
    seps: list
    root: FrmBlock | None
    header_end: int               # first line after the root End
    attr_end: int                 # first code line (after the Attribute VB_* lines)

    @property
    def newline(self) -> str:
        return dominant_newline(join_lines(self.lines, self.seps))

    def controls(self):
        """Every non-menu block under the form (depth first)."""
        if self.root is None:
            return
        for b in self.root.walk():
            if not b.is_menu:
                yield b

    def find(self, neutral_name: str) -> FrmBlock | None:
        low = neutral_name.lower()
        return next((b for b in self.controls() if b.neutral_name.lower() == low), None)

    def menus(self) -> list[FrmBlock]:
        return [b for b in (self.root.children if self.root else []) if b.is_menu]


def parse_lines(lines: list[str], seps: list[str]) -> FrmDoc:
    stack: list[FrmBlock] = []
    pstack: list[FrmPropBlock] = []
    root = None
    header_end = len(lines)
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if pstack:
            if _ENDPROP.match(line):
                pstack[-1].end = i
                pstack.pop()
            elif _BEGINPROP.match(line):
                pb = FrmPropBlock(_BEGINPROP.match(line).group(2), i)
                pstack[-1].blocks.append(pb)
                pstack.append(pb)
            else:
                m = _PROP.match(line)
                if m:
                    pstack[-1].props.append(FrmProp(m.group(2).strip(), i, m.group(4)))
            i += 1
            continue
        m = _BEGIN.match(line)
        if m and (stack or root is None):
            b = FrmBlock(m.group(2), m.group(3), i, m.group(1))
            if stack:
                b.parent = stack[-1]
                stack[-1].children.append(b)
            else:
                root = b
            stack.append(b)
            i += 1
            continue
        if stack:
            if _BEGINPROP.match(line):
                pb = FrmPropBlock(_BEGINPROP.match(line).group(2), i)
                stack[-1].pblocks.append(pb)
                pstack.append(pb)
            elif _END.match(line):
                stack[-1].end = i
                stack.pop()
                if not stack:
                    header_end = i + 1
                    break
            else:
                m = _PROP.match(line)
                if m:
                    stack[-1].props.append(FrmProp(m.group(2).strip(), i, m.group(4)))
        i += 1
    attr_end = header_end
    while attr_end < len(lines) and re.match(r"\s*Attribute\s+", lines[attr_end], re.I):
        attr_end += 1
    return FrmDoc(lines, seps, root, header_end, attr_end)


def parse_frm(text: str) -> FrmDoc:
    return parse_lines(*split_lines(text))


# ============================================================================ code section
def split_code(text: str) -> tuple[str, str]:
    """(header + Attribute lines exactly as in the file, code section with "\\n" newlines).
    The code section is what the editor shows (VB6 hides the form description too)."""
    lines, seps = split_lines(text)
    doc = parse_lines(lines, seps)
    k = doc.attr_end
    head = join_lines(lines[:k], seps[:k])
    code_lines = lines[k:]
    code_seps = seps[k:]
    if not code_lines:
        return head, ""
    code = "\n".join(code_lines)
    if code_seps and code_seps[-1]:
        code += "\n"
    if code_lines == [""] and not code_seps[-1]:
        code = ""
    return head, code


def join_code(head: str, code: str, newline: str = "\r\n") -> str:
    if head and not head.endswith(("\n", "\r")):
        head += newline
    return head + code.replace("\r\n", "\n").replace("\n", newline)


# ============================================================================ .frx
class Frx:
    """A .frx/.ctx binary resource file: read values at offsets, append new values."""

    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        try:
            self.data = bytearray(self.path.read_bytes()) if self.path and self.path.is_file() else bytearray()
        except OSError:
            self.data = bytearray()
        self.dirty = False

    # -- reading
    def _u16(self, off):
        return struct.unpack_from("<H", self.data, off)[0]

    def _u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def read_bytes_string(self, off: int) -> bytes | None:
        try:
            if off + 12 <= len(self.data) and self.data[off + 4:off + 8] == b"lt\0\0":
                n = self._u32(off + 8)
                return bytes(self.data[off + 12:off + 12 + n])
            b = self.data[off]
            if b == 0xFF:
                n = self._u16(off + 1)
                return bytes(self.data[off + 3:off + 3 + n])
            if b == 0 and off + 4 <= len(self.data):          # 4-byte header (size incl. header)
                n = self._u32(off)
                if 4 <= n <= len(self.data) - off:
                    return bytes(self.data[off + 4:off + n])
            return bytes(self.data[off + 1:off + 1 + b])
        except (IndexError, struct.error):
            return None

    def read_string(self, off: int, encoding: str = "cp1252") -> str | None:
        raw = self.read_bytes_string(off)
        return None if raw is None else raw.decode(encoding, errors="replace").rstrip("\0")

    def read_list(self, off: int, encoding: str = "cp1252") -> list[str] | None:
        def attempt(pos, count):
            items = []
            for _ in range(count):
                if pos + 2 > len(self.data):
                    return None
                n = self._u16(pos)
                pos += 2
                if pos + n > len(self.data):
                    return None
                raw = bytes(self.data[pos:pos + n])
                if any(c < 0x20 and c not in (9,) for c in raw):
                    return None
                items.append(raw.decode(encoding, errors="replace"))
                pos += n
            return items
        try:
            count = self._u16(off)
        except struct.error:
            return None
        got = attempt(off + 2, count)
        if got is None:                                  # list header word after the count
            got = attempt(off + 4, count)
        return got

    def read_picture(self, off: int) -> bytes | None:
        try:
            if self.data[off + 4:off + 8] == b"lt\0\0":
                n = self._u32(off + 8)
                return bytes(self.data[off + 12:off + 12 + n]) or None
        except (IndexError, struct.error):
            pass
        return None

    # -- writing (append)
    def append(self, blob: bytes) -> int:
        off = len(self.data)
        self.data += blob
        self.dirty = True
        return off

    def append_string(self, s: str, encoding: str = "cp1252") -> int:
        raw = s.encode(encoding, errors="replace")
        if len(raw) < 255:
            return self.append(bytes([len(raw)]) + raw)
        return self.append(b"\xff" + struct.pack("<H", min(len(raw), 0xFFFF)) + raw[:0xFFFF])

    def append_list(self, items: list[str], encoding: str = "cp1252") -> int:
        blob = struct.pack("<H", len(items))
        for it in items:
            raw = str(it).encode(encoding, errors="replace")[:0xFFFF]
            blob += struct.pack("<H", len(raw)) + raw
        return self.append(blob)

    def append_picture(self, data: bytes) -> int:
        return self.append(struct.pack("<I", len(data) + 8) + b"lt\0\0" + struct.pack("<I", len(data)) + data)

    def save(self) -> bool:
        if not self.dirty or self.path is None:
            return False
        self.path.write_bytes(bytes(self.data))
        self.dirty = False
        return True


def frx_name_of(doc: FrmDoc, frm_path: Path) -> str:
    """The .frx file name the .frm already references (or <frm stem>.frx)."""
    for i in range(len(doc.lines)):
        m = re.search(r'\$?"([^"]+\.(?:frx|ctx|dsx|pgx))":[0-9A-Fa-f]+', doc.lines[i], re.I)
        if m:
            return m.group(1)
    return Path(frm_path).with_suffix(".frx").name


# ============================================================================ reading -> neutral Form
def _image_to_cache(data: bytes, cache_dir: Path, stem: str) -> str:
    """Store a .frx picture as a file the designer/runtime can show (PNG when Pillow can read it)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        import io

        from PIL import Image
        img = Image.open(io.BytesIO(data))
        out = cache_dir / f"{stem}.png"
        img.save(out)
        return str(out)
    except Exception:  # noqa: BLE001 - unknown/unsupported format: keep the raw bytes
        ext = ".gif" if data[:3] == b"GIF" else ".jpg" if data[:2] == b"\xff\xd8" else ".bmp" \
            if data[:2] == b"BM" else ".bin"
        out = cache_dir / f"{stem}{ext}"
        out.write_bytes(data)
        return str(out)


@dataclass
class LoadInfo:
    warnings: list = field(default_factory=list)
    scale_pixels: bool = False
    frx_name: str = ""


def _frm_objects(doc: FrmDoc, frx: Frx, encoding: str, scale: int):
    """FrmObject tree (radide.importers.vb6_import) with .frx strings resolved."""
    from ..importers.vb6_import import FrmObject

    def build(b: FrmBlock, is_root: bool) -> FrmObject:
        o = FrmObject(b.cls, b.name)
        for p in b.props:
            v = p.value
            k = p.key.lower()
            if isinstance(v, tuple) and k in ("caption", "text", "tooltiptext"):
                s = frx.read_string(v[2], encoding)
                v = s if s is not None else ("frx", p.raw)
            elif isinstance(v, tuple):
                v = ("frx", p.raw)
            elif not is_root and scale != 1 and k in ("left", "top", "width", "height") \
                    and isinstance(v, (int, float)):
                v = v * scale
            o.props[k] = v
        font = b.pblock("Font")
        if font is not None:
            for p in font.props:
                o.font[p.key.lower()] = p.value
        o.pblocks = {pb.name.lower(): pb for pb in b.pblocks}     # ColumnHeaders, Column00, Tabs ...
        for c in b.children:
            o.children.append(build(c, False))
        return o
    return build(doc.root, True)


def load_form(text: str, frm_path: Path, cache_dir: Path | None = None,
              encoding: str = "cp1252") -> tuple[Form | None, LoadInfo]:
    """The neutral Form of a .frm text (None when it has no form description)."""
    from ..importers.python_import import ImportReport
    from ..importers.vb6_import import _FrmConverter
    info = LoadInfo()
    doc = parse_frm(text)
    if doc.root is None:
        info.warnings.append(f"{Path(frm_path).name}: no form description found")
        return None, info
    depth, level = 0, [(doc.root, 0)]
    while level:                    # (iterative) a corrupted file must not reach the recursive converter
        b, d = level.pop()
        depth = max(depth, d)
        level.extend((c, d + 1) for c in b.children)
    if depth > MAX_NESTING:
        raise ValueError(f"{Path(frm_path).name}: controls nested {depth} levels deep (corrupted form file)")
    info.frx_name = frx_name_of(doc, frm_path)
    frx = Frx(Path(frm_path).parent / info.frx_name)
    scalemode = doc.root.get("ScaleMode", 1)
    info.scale_pixels = scalemode == 3
    # positions of controls are stored in the form's ScaleMode; the converter expects twips
    obj = _frm_objects(doc, frx, encoding, TWIP if info.scale_pixels else 1)
    report = ImportReport()

    class Conv(_FrmConverter):
        def _add(self, form, o, parent):
            if o.cls.lower() == "mscomdlg.commondialog":       # the runtime knows the dialogs
                props = CONTROL_TYPES["OpenFileDialog"].default_props(
                    o.name if o.props.get("index") is None else f"{o.name}_{o.props['index']}")
                props["Parent"] = parent
                form.controls.append(Control("OpenFileDialog", props))
                return
            n = len(form.controls)
            super()._add(form, o, parent)
            if o.cls.lower() in ("mscomctllib.statusbar", "comctllib.statusbar") and len(form.controls) > n:
                old = form.controls[n]                      # the runtime has a real StatusBar
                props = CONTROL_TYPES["StatusBar"].default_props(old.name)
                props.update({k: v for k, v in old.props.items() if k in props and k != "Text"})
                props["Text"] = str(o.props.get("simpletext", "") or "")
                props["Dock"] = "Bottom" if o.props.get("align", 2) == 2 else "None"
                form.controls[n] = Control("StatusBar", props)
                self.report.warnings = [w for w in self.report.warnings if f"'{old.name}'" not in w]

    form = Conv(report, Path(frm_path).name).convert(obj)
    info.warnings += report.warnings
    # .frx lists and pictures
    for ctrl in form.controls:
        b = doc.find(ctrl.name)
        if b is None:
            continue
        if ctrl.type in ("ListBox", "ComboBox"):
            v = b.get("List")
            if isinstance(v, tuple):
                items = frx.read_list(v[2], encoding)
                if items is not None:
                    ctrl.props["Items"] = ";".join(items)
        if ctrl.type == "PictureBox":
            v = b.get("Picture")
            if isinstance(v, tuple) and cache_dir is not None:
                data = frx.read_picture(v[2])
                if data:
                    ctrl.props["Image"] = _image_to_cache(data, Path(cache_dir),
                                                          f"{Path(frm_path).stem}_{ctrl.name}")
    info.warnings = [w for w in info.warnings if "stored in .frx" not in w or
                     not any(n in w for n in [c.name for c in form.controls if c.props.get("Image")])]
    return form, info


# ============================================================================ writing
class _Editor:
    def __init__(self, text: str, frm_path: Path, encoding: str):
        self.lines, self.seps = split_lines(text)
        self.nl = dominant_newline(text)
        self.frm_path = Path(frm_path)
        self.encoding = encoding
        self.changed = False
        self.notes: list[str] = []
        self.objects_needed: set[str] = set()
        self.reparse()
        self.frx_name = frx_name_of(self.doc, frm_path)
        self.frx = Frx(self.frm_path.parent / self.frx_name)
        self.scale_pixels = self.doc.root is not None and self.doc.root.get("ScaleMode", 1) == 3

    def reparse(self):
        self.doc = parse_lines(self.lines, self.seps)

    def text(self) -> str:
        return join_lines(self.lines, self.seps)

    # -- primitive edits
    def insert(self, at: int, new_lines: list[str]):
        if not new_lines:
            return
        if at > 0 and at - 1 < len(self.seps) and not self.seps[at - 1]:
            self.seps[at - 1] = self.nl                    # inserting after a last line without newline
        self.lines[at:at] = new_lines
        self.seps[at:at] = [self.nl] * len(new_lines)
        self.changed = True
        self.reparse()

    def delete(self, start: int, end: int):
        del self.lines[start:end + 1]
        del self.seps[start:end + 1]
        self.changed = True
        self.reparse()

    def replace_line(self, i: int, text: str):
        if self.lines[i] != text:
            self.lines[i] = text
            self.changed = True
            self.reparse()

    # -- properties
    def pos(self, px) -> str:
        v = int(round(float(px)))
        return str(v if self.scale_pixels else v * TWIP)

    def _entries(self, b):
        out = [(p.key.lower(), p.line, p.line) for p in b.props]
        out += [(pb.name.lower(), pb.start, pb.end) for pb in b.pblocks]
        return sorted(out, key=lambda e: e[1])

    def set_prop(self, b: FrmBlock, key: str, value: str | None):
        """Set (value = formatted text) or remove (None) a property line of block *b*."""
        p = b.prop(key)
        if p is not None:
            if value is None:
                self.delete(p.line, p.line)
                return
            line = self.lines[p.line]
            m = _PROP.match(line)
            self.replace_line(p.line, m.group(1) + m.group(2) + m.group(3) + value)
            return
        if value is None:
            return
        ind = b.indent + "   "
        entries = self._entries(b)
        at = None
        for name, start, _end in entries:
            if name.lstrip("_") > key.lower().lstrip("_") and not name.startswith("_"):
                at = start
                break
        if at is None:
            at = (entries[-1][2] + 1) if entries else b.start + 1
            first_child = min((c.start for c in b.children), default=None)
            if first_child is not None and at > first_child:
                at = first_child
        self.insert(at, [f"{ind}{key:<16}=   {value}"])

    def set_font(self, b: FrmBlock, changes: dict):
        fb = b.pblock("Font")
        if fb is None:
            name = changes.get("Name", '"MS Sans Serif"')
            ind = b.indent + "   "
            block = [f"{ind}BeginProperty Font {FONT_GUID} ",
                     f"{ind}   Name            =   {name}",
                     f"{ind}   Size            =   {changes.get('Size', '8.25')}",
                     f"{ind}   Charset         =   0",
                     f"{ind}   Weight          =   {changes.get('Weight', '400')}",
                     f"{ind}   Underline       =   0   'False",
                     f"{ind}   Italic          =   {changes.get('Italic', vb_bool(False))}",
                     f"{ind}   Strikethrough   =   0   'False",
                     f"{ind}EndProperty"]
            entries = self._entries(b)
            at = next((s for n, s, _e in entries if n > "font" and not n.startswith("_")), None)
            if at is None:
                at = (entries[-1][2] + 1) if entries else b.start + 1
                first_child = min((c.start for c in b.children), default=None)
                if first_child is not None and at > first_child:
                    at = first_child
            self.insert(at, block)
            return
        for key, value in changes.items():
            fb = self.doc_block(b).pblock("Font")
            p = fb.prop(key)
            if p is not None:
                m = _PROP.match(self.lines[p.line])
                self.replace_line(p.line, m.group(1) + m.group(2) + m.group(3) + value)
            else:
                ind = self.lines[fb.start][:len(self.lines[fb.start]) - len(self.lines[fb.start].lstrip())]
                self.insert(fb.end, [f"{ind}   {key:<16}=   {value}"])

    def doc_block(self, b: FrmBlock) -> FrmBlock:
        """The same block after a reparse (located by its start line's Begin text / root)."""
        if b.parent is None:
            return self.doc.root
        found = self.doc.find(b.neutral_name)
        return found or b

    def frx_ref(self, off: int) -> str:
        return f'"{self.frx_name}":{off:04X}'


def _vb_class(ctrl: Control, ed: "_Editor | None" = None) -> str:
    """VB6 class of a new control: the built-in table, an installed package's ``vb6.class``, else - for a
    component package - a UserControl reference ``<Project>.<Type>`` (its .ctl stand-in is added to the
    .vbp, radide/components/vb6map.py), else a PictureBox."""
    cls = NEW_CLASS.get(ctrl.type) or _vb6map.new_class(ctrl.type)
    if cls:
        return cls
    from ..components import is_component_type
    if is_component_type(ctrl.type):
        return f"{_project_name(ed.frm_path if ed is not None else None)}.{ctrl.type}"
    return "VB.PictureBox"


def _project_name(frm_path) -> str:
    """Name= of the .vbp that lists the form (VB6 names user controls <Project>.<Control>), else Project1."""
    if frm_path is None:
        return "Project1"
    folder = Path(frm_path).parent
    try:
        vbps = sorted(folder.glob("*.vbp"))
    except OSError:
        vbps = []
    fname = Path(frm_path).name.lower()
    best = None
    for v in vbps:
        try:
            text = v.read_text(encoding="cp1252", errors="replace")
        except OSError:
            continue
        name = re.search(r'(?im)^Name="?([^"\r\n]+)"?\s*$', text)
        lists = re.search(r"(?im)^Form=(?:.*[\\/;=\s])?" + re.escape(fname) + r"\s*$", text)
        if name and (lists or best is None):
            best = name.group(1).strip()
            if lists:
                break
    return best or "Project1"


def object_of(lib: str) -> tuple[str, str] | None:
    """(GUID, OCX) of an 'Object =' library: the VB6 OCXs, or a third-party OCX a package declares."""
    return OCX.get(lib) or _vb6map.object_line(lib)


def _text_key(cls: str) -> str:
    if cls.lower().endswith(".statusbar"):
        return "SimpleText"
    return "Text" if cls.lower() in _TEXT_CLASSES else "Caption"


def _prop_edits(ed: _Editor, b_cls: str, ctrl: Control, key: str, value) -> list | None:
    """VB property edits for one changed neutral property: [(vbkey, formatted value | None)]
    or None when the property cannot be represented in a .frm."""
    t = ctrl.type
    cls = b_cls.lower()
    if cls == "vb.line" and key in ("Left", "Top", "Width", "Height", "BackColor"):
        return None                                 # a Line has X1/Y1/X2/Y2, shown as a thin Panel
    if key == "TabPage":
        return None
    if key in ("Left", "Top") and "TabPage" in ctrl.props:        # on an SSTab page (see vb6_import._sstab_children)
        par = ed.doc.find(str(ctrl.props.get("Parent") or ""))
        if par is not None and par.cls.lower() == "tabdlg.sstab":
            from ..controls import TAB_PAGE_X, TAB_PAGE_Y
            v = int(round(float(value))) + (TAB_PAGE_X if key == "Left" else TAB_PAGE_Y)
            units = v if ed.scale_pixels else v * TWIP
            cur = par.get("Tab", 0)
            if key == "Left" and int(ctrl.props.get("TabPage") or 0) != (cur if isinstance(cur, int) else 0):
                units -= 5000 if ed.scale_pixels else 75000          # VB6 parks hidden pages' controls left
            return [(key, str(units))]
    if key in ("Left", "Top", "Width", "Height"):
        if CONTROL_TYPES[t].nonvisual:
            return []
        return [(key, ed.pos(value))]
    comp = _vb6map.prop_edits(t, key, value)      # a component package property: a PropertyBag line
    if comp is not None:
        return comp
    if key == "Text":
        if t in ("ListBox",):
            return []
        s = str(value or "")
        if "\n" in s or len(s) > 255:
            return [(_text_key(cls), ed.frx_ref(ed.frx.append_string(s.replace("\n", "\r\n"), ed.encoding)))]
        return [(_text_key(cls), vb_str(s))]
    if key == "Enabled":
        return [("Enabled", None if value else vb_bool(False))]
    if key == "Visible":
        return [("Visible", None if value else vb_bool(False))]
    if key == "TabIndex":
        return [("TabIndex", str(int(value or 0)))]
    if key == "ToolTip":
        return [("ToolTipText", vb_str(value) if value else None)]
    if key in ("BackColor", "ForeColor"):
        c = vb_color(value)
        return [(key, c)] if c or not value else None
    if key == "Checked":
        if t == "CheckBox":
            return [("Value", "1  'Checked" if value else None)]
        return [("Value", "-1  'True" if value else None)]
    if key == "Multiline":
        return [("MultiLine", vb_bool(True) if value else None)]
    if key == "ReadOnly":
        return [("Locked", vb_bool(True) if value else None)]
    if key == "PasswordChar":
        return [("PasswordChar", vb_str(value) if value else None)]
    if key == "MaxLength":
        return [("MaxLength", str(int(value)) if value else None)]
    if key == "TextAlign" and t == "Label":
        n = {"Left": 0, "Right": 1, "Center": 2}.get(str(value), 0)
        return [("Alignment", None if n == 0 else
                 f"{n}  '{ {1: 'Right Justify', 2: 'Center'}[n] }")]
    if key == "TextAlign":
        return []
    if key == "DropDownStyle":
        return [("Style", "2  'Dropdown List" if value == "DropDownList" else None)]
    vb_name = _vb6map.property_name(t, key)          # "vb6": {"properties": {"Minimum": "Min", ...}}
    if vb_name:
        return [(vb_name, str(int(value)))]
    if key == "Minimum":
        return [("Min", str(int(value)))]
    if key == "Maximum":
        return [("Max", str(int(value)))]
    if key == "Value" and t in ("TrackBar", "NumericUpDown", "ProgressBar"):
        return [("Value", str(int(value)))]
    if key == "Interval":
        return [("Interval", str(int(value)))]
    if key == "Items" and t in ("ListBox", "ComboBox"):
        items = [x for x in str(value or "").split(";") if x != ""]
        if not items:
            return [("List", None), ("ItemData", None)]
        return [("List", ed.frx_ref(ed.frx.append_list(items, ed.encoding))), ("ItemData", None)]
    if key == "Image":
        if not value:
            return [("Picture", None)]
        data = _picture_bytes(Path(value))
        if data is None:
            return None
        return [("Picture", ed.frx_ref(ed.frx.append_picture(data)))]
    if key in ("Name", "Parent", "ArrayName", "ArrayIndex"):
        return []
    return None


def _picture_bytes(path: Path) -> bytes | None:
    """Bytes VB6 can load (BMP/GIF/JPG/ICO/WMF); other formats are converted to BMP."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:2] == b"BM" or data[:3] == b"GIF" or data[:2] == b"\xff\xd8" or data[:4] == b"\0\0\1\0":
        return data
    try:
        import io

        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("RGB")
        out = io.BytesIO()
        img.save(out, "BMP")
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return None


_FONT_KEYS = ("FontName", "FontSize", "FontBold", "FontItalic")


def _font_changes(base: dict, new: dict) -> dict:
    out = {}
    if base.get("FontName") != new.get("FontName") and new.get("FontName"):
        out["Name"] = vb_str(new["FontName"])
    if base.get("FontSize") != new.get("FontSize") and new.get("FontSize"):
        out["Size"] = str(new["FontSize"])
    if bool(base.get("FontBold")) != bool(new.get("FontBold")):
        out["Weight"] = "700" if new.get("FontBold") else "400"
    if bool(base.get("FontItalic")) != bool(new.get("FontItalic")):
        out["Italic"] = vb_bool(bool(new.get("FontItalic")))
    return out


def _apply_props(ed: _Editor, name: str, base_props: dict, ctrl: Control):
    keys = [k for k in dict.fromkeys([*base_props, *ctrl.props]) if base_props.get(k) != ctrl.props.get(k)]
    if not keys:
        return
    font_done = False
    for k in keys:
        b = ed.doc.find(name)
        if b is None:
            return
        if k in _FONT_KEYS:
            if not font_done:
                font_done = True
                ch = _font_changes(base_props, ctrl.props)
                if ch:
                    ed.set_font(b, ch)
            continue
        edits = _prop_edits(ed, b.cls, ctrl, k, ctrl.props.get(k))
        if edits is None:
            ed.notes.append(f"{name}.{k} cannot be stored in a VB6 .frm (kept only in the designer)")
            continue
        for vk, val in edits:
            b = ed.doc.find(name)
            ed.set_prop(b, vk, val)


def _block_lines_for(ed: _Editor, ctrl: Control, indent: str, form: Form) -> list[str]:
    cls = _vb_class(ctrl, ed)
    lib = cls.split(".")[0]
    from ..components import is_component_type
    if object_of(lib) is not None:
        ed.objects_needed.add(lib)
    elif is_component_type(ctrl.type) and not _vb6map.new_class(ctrl.type):
        ed.objects_needed.add("ctl:" + ctrl.type)        # the UserControl stand-in (vb6_project writes it)
        ed.notes.append(f"{ctrl.name}: component {ctrl.type} written as the UserControl {cls} "
                        f"({ctrl.type}.ctl)")
    elif ctrl.type not in NEW_CLASS and not _vb6map.new_class(ctrl.type):
        ed.notes.append(f"{ctrl.name}: {ctrl.type} has no VB6 equivalent - written as {cls}")
    arr = ctrl.props.get("ArrayName")
    name = arr or ctrl.name
    ind = indent + "   "
    props: dict[str, str] = {}
    ctype = CONTROL_TYPES[ctrl.type]
    defaults = ctype.default_props(ctrl.name)
    always = {"Left", "Top", "Width", "Height", "TabIndex", "Text"}
    for k, v in ctrl.props.items():
        if k in _FONT_KEYS or (k not in always and defaults.get(k) == v):
            continue
        if k == "Text" and cls.lower() in ("vb.listbox",):
            continue
        edits = _prop_edits(ed, cls, ctrl, k, v)
        for vk, val in edits or []:
            if val is not None:
                props[vk] = val
    if ctype.nonvisual:
        props.setdefault("Left", "0")
        props.setdefault("Top", "0")
        if cls == "MSComDlg.CommonDialog":
            props.update({"_ExtentX": "847", "_ExtentY": "847", "_Version": "393216"})
    if arr:
        props["Index"] = str(int(ctrl.props.get("ArrayIndex", 0)))
    out = [f"{indent}Begin {cls} {name}"]
    order = sorted(props, key=lambda k: (not k.startswith("_"), k.lower()))
    font = _font_changes(CONTROL_TYPES[ctrl.type].default_props(""), ctrl.props)
    font_lines = []
    if font:
        font_lines = [f"{ind}BeginProperty Font {FONT_GUID} ",
                      f"{ind}   Name            =   {font.get('Name', vb_str('MS Sans Serif'))}",
                      f"{ind}   Size            =   {font.get('Size', '8.25')}",
                      f"{ind}   Charset         =   0",
                      f"{ind}   Weight          =   {font.get('Weight', '400')}",
                      f"{ind}   Underline       =   0   'False",
                      f"{ind}   Italic          =   {font.get('Italic', vb_bool(False))}",
                      f"{ind}   Strikethrough   =   0   'False",
                      f"{ind}EndProperty"]
    placed = False
    for k in order:
        if font_lines and not placed and k.lower() > "font" and not k.startswith("_"):
            out += font_lines
            placed = True
        out.append(f"{ind}{k:<16}=   {props[k]}")
    if font_lines and not placed:
        out += font_lines
    if ctype.container:
        for ch in form.children(ctrl.name):
            out += _block_lines_for(ed, ch, ind, form)
    out.append(f"{indent}End")
    return out


def _insert_point(ed: _Editor, parent: FrmBlock) -> int:
    """Where a new child of *parent* goes: before its first menu, else before its End."""
    menus = [c.start for c in parent.children if c.is_menu]
    return min(menus) if menus else parent.end


def _reindent(lines: list[str], old: str, new: str) -> list[str]:
    return [new + ln[len(old):] if ln.startswith(old) else ln for ln in lines]


# -- menus
def _shape(items) -> list:
    return [(it.get("Name", "") if it.get("Text") != "-" else "-", _shape(it.get("Items") or []))
            for it in items]


def _menu_captions_in_place(ed: _Editor, base_items: list, new_items: list) -> bool:
    """Same menu tree, only captions changed: edit the Caption lines.  False = needs a rebuild."""
    if _shape(base_items) != _shape(new_items):
        return False
    shown = {it.get("Name", "").lower() for it in base_items}
    blocks = [b for b in ed.doc.menus() if b.name.lower() in shown or str(b.get("Caption", "")) == "-"]
    pairs = []

    def walk(bitems, nitems, blks):
        blks = list(blks)
        for bi, ni in zip(bitems, nitems):
            if not blks:
                return False
            b = blks.pop(0)
            if bi.get("Text") != "-" and b.name.lower() != str(bi.get("Name", "")).lower():
                return False
            if bi.get("Text") != ni.get("Text"):
                pairs.append((b.start, ni.get("Text", "")))
            if walk(bi.get("Items") or [], ni.get("Items") or [], [c for c in b.children if c.is_menu]) is False:
                return False
        return True
    if walk(base_items, new_items, blocks) is False:
        return False
    for start, text in sorted(pairs, reverse=True):
        b = next(x for x in ed.doc.root.walk() if x.start == start)
        cap = b.get("Caption", "")
        if str(cap).replace("&", "") != text:
            ed.set_prop(b, "Caption", vb_str(text))
    return True


def _menu_regen(ed: _Editor, base_items: list, new_items: list):
    doc = ed.doc
    root = doc.root
    orig = doc.menus()
    by_name: dict[str, list[FrmBlock]] = {}
    seps_by_parent: dict[int, list[FrmBlock]] = {}

    def index(blocks, parent_key):
        for b in blocks:
            if str(b.get("Caption", "")) == "-":
                seps_by_parent.setdefault(parent_key, []).append(b)
            by_name.setdefault(b.name.lower(), []).append(b)
            index([c for c in b.children if c.is_menu], id(b))
    index(orig, 0)
    represented = {it.get("Name", "").lower() for it in base_items}
    used_names = {b.name.lower() for b in root.walk()}
    counter = [0]

    def own_lines(b: FrmBlock) -> list[str]:
        first_child = min((c.start for c in b.children), default=b.end)
        return ed.lines[b.start + 1:first_child]

    def emit(items, indent, parent_key) -> list[str]:
        out = []
        seps = list(seps_by_parent.get(parent_key, []))
        for it in items:
            ind = indent + "   "
            if it.get("Text") == "-":
                if seps:
                    b = seps.pop(0)
                    out += _reindent([ed.lines[b.start]], b.indent, indent)
                    out += _reindent(own_lines(b), b.indent + "   ", ind)
                else:
                    counter[0] += 1
                    nm = f"mnuSep{counter[0]}"
                    while nm.lower() in used_names:
                        counter[0] += 1
                        nm = f"mnuSep{counter[0]}"
                    used_names.add(nm.lower())
                    out += [f"{indent}Begin VB.Menu {nm} ", f"{ind}Caption         =   \"-\""]
                out.append(f"{indent}End")
                continue
            name = it.get("Name") or "mnuItem"
            cands = by_name.get(name.lower()) or []
            b = cands.pop(0) if cands else None
            if b is not None:
                out += _reindent([ed.lines[b.start]], b.indent, indent)
                body = _reindent(own_lines(b), b.indent + "   ", ind)
                cap = b.get("Caption", "")
                if str(cap).replace("&", "") != it.get("Text", ""):
                    body = [ln if not re.match(r"\s*Caption\s*=", ln, re.I)
                            else f"{ind}Caption         =   {vb_str(it.get('Text', ''))}" for ln in body]
                    if not any(re.match(r"\s*Caption\s*=", ln, re.I) for ln in body):
                        body.insert(0, f"{ind}Caption         =   {vb_str(it.get('Text', ''))}")
                out += body
                kid_key = id(b)
            else:
                out += [f"{indent}Begin VB.Menu {name} ", f"{ind}Caption         =   {vb_str(it.get('Text', ''))}"]
                kid_key = -1
            out += emit(it.get("Items") or [], ind, kid_key)
            out.append(f"{indent}End")
        return out

    new_lines = emit(new_items, root.indent + "   ", 0)
    # top-level menus the designer never showed (invisible, no children): kept verbatim
    for b in orig:
        if b.name.lower() not in represented and str(b.get("Caption", "")) != "-":
            new_lines += ed.lines[b.start:b.end + 1]
    if orig:
        at = orig[0].start
        for b in sorted(orig, key=lambda x: -x.start):
            ed.delete(b.start, b.end)
        ed.insert(at, new_lines)
    else:
        ed.insert(ed.doc.root.end, new_lines)


# -- form properties
def _apply_form_props(ed: _Editor, base: Form, new: Form):
    root = ed.doc.root
    bp, np_ = base.props, new.props
    for k in dict.fromkeys([*bp, *np_]):
        if bp.get(k) == np_.get(k):
            continue
        v = np_.get(k)
        root = ed.doc.root
        if k == "Text":
            ed.set_prop(root, "Caption", vb_str(v))
        elif k in ("Width", "Height"):
            tw = int(round(float(v))) * TWIP
            ed.set_prop(root, "ClientWidth" if k == "Width" else "ClientHeight", str(tw))
            sk = "ScaleWidth" if k == "Width" else "ScaleHeight"
            root = ed.doc.root
            sm = root.get("ScaleMode", 1)
            if root.prop(sk) is not None and sm in (1, 3):
                ed.set_prop(root, sk, str(tw if sm == 1 else int(round(float(v)))))
        elif k == "BackColor":
            c = vb_color(v)
            if c or not v:
                ed.set_prop(root, "BackColor", c)
        elif k == "StartPosition":
            ed.set_prop(root, "StartUpPosition", "2  'CenterScreen" if v == "CenterScreen" else "0  'Manual")
        elif k == "FormBorderStyle":
            ed.set_prop(root, "BorderStyle", "1  'Fixed Single" if v == "FixedSingle" else None)
        elif k == "WindowState":
            ed.set_prop(root, "WindowState", "2  'Maximized" if v == "Maximized" else None)
        elif k == "Name":
            line = ed.lines[root.start]
            m = _BEGIN.match(line)
            ed.replace_line(root.start, f"{m.group(1)}Begin {root.cls} {v}" + line[len(line.rstrip()):])
            for i in range(ed.doc.header_end, ed.doc.attr_end):
                if re.match(r"\s*Attribute\s+VB_Name\s*=", ed.lines[i], re.I):
                    ed.replace_line(i, f"Attribute VB_Name = {vb_str(v)}")
        elif k == "ScaleMode":
            pass
        else:
            ed.notes.append(f"Form.{k} cannot be stored in a VB6 .frm (kept only in the designer)")


def _match_renames(base: Form, new: Form) -> dict[str, str]:
    """old name -> new name for controls renamed in the designer (same type, same place)."""
    bnames = {c.name for c in base.controls}
    nnames = {c.name for c in new.controls}
    gone = [c for c in base.controls if c.name not in nnames and c.type != "MenuStrip"]
    fresh = [c for c in new.controls if c.name not in bnames and c.type != "MenuStrip"]
    out = {}

    def sig(c, strict):
        keys = ("Left", "Top", "Width", "Height", "Parent") if strict else ()
        return (c.type, *[c.props.get(k) for k in keys])
    for strict in (True, False):
        for g in list(gone):
            same = [f for f in fresh if sig(f, strict) == sig(g, strict)]
            if len(same) == 1 and (strict or sum(sig(x, False) == sig(g, False) for x in gone) == 1):
                out[g.name] = same[0].name
                gone.remove(g)
                fresh.remove(same[0])
    return out


def apply_form_changes(text: str, base: Form, new: Form, frm_path: Path,
                       encoding: str = "cp1252") -> tuple[str, list[str], set[str]]:
    """Write the designer's changes (base -> new) into the .frm text.
    Returns (new text, notes, OCX libraries the new controls need).  The .frx is saved
    when a resource changed.  Unchanged forms return *text* itself."""
    if base.snapshot() == new.snapshot():
        return text, [], set()
    ed = _Editor(text, frm_path, encoding)
    if ed.doc.root is None:
        return text, ["no form description - not written"], set()
    renames = _match_renames(base, new)
    bmap = {c.name: c for c in base.controls}
    nmap = {c.name: c for c in new.controls}
    # 1. renames (Begin line + array Index)
    for old, newname in renames.items():
        b = ed.doc.find(old)
        if b is None:
            continue
        nc = nmap[newname]
        vbname = nc.props.get("ArrayName") or newname
        line = ed.lines[b.start]
        m = _BEGIN.match(line)
        ed.replace_line(b.start, f"{m.group(1)}Begin {b.cls} {vbname}" + line[len(line.rstrip()):])
        bmap[newname] = bmap.pop(old)
        b = ed.doc.find(vbname) if nc.props.get("ArrayName") is None else None
        if nc.props.get("ArrayName") is not None:
            b = next((x for x in ed.doc.controls() if x.name == vbname and x.index is None), None)
            if b is not None:
                ed.set_prop(b, "Index", str(int(nc.props.get("ArrayIndex", 0))))
    # 2. deletions
    for name in [n for n in bmap if n not in nmap and bmap[n].type != "MenuStrip"]:
        b = ed.doc.find(name)
        if b is not None:
            ed.delete(b.start, b.end)
    # 3. changed properties, parent moves
    for name, nc in nmap.items():
        bc = bmap.get(name)
        if bc is None or nc.type == "MenuStrip":
            continue
        if bc.props.get("Parent", "") != nc.props.get("Parent", ""):
            b = ed.doc.find(name)
            target = ed.doc.root if not nc.parent else ed.doc.find(nc.parent)
            if b is not None and target is not None:
                block = ed.lines[b.start:b.end + 1]
                old_ind = b.indent
                ed.delete(b.start, b.end)
                target = ed.doc.root if not nc.parent else ed.doc.find(nc.parent)
                ed.insert(_insert_point(ed, target), _reindent(block, old_ind, target.indent + "   "))
        _apply_props(ed, name, bc.props, nc)
    # 4. new controls (containers bring their new children along)
    added = [c for c in new.controls if c.name not in bmap and c.type != "MenuStrip"]
    added_names = {c.name for c in added}
    for c in added:
        if c.parent and c.parent in added_names:
            continue                                   # written inside its new container
        parent = ed.doc.root if not c.parent else ed.doc.find(c.parent)
        if parent is None:
            parent = ed.doc.root
        ed.insert(_insert_point(ed, parent), _block_lines_for(ed, c, parent.indent + "   ", new))
    # 5. menus
    bm, nm = base.menu(), new.menu()
    bitems = bm.props.get("Items", []) if bm else []
    nitems = nm.props.get("Items", []) if nm else []
    if bitems != nitems and not _menu_captions_in_place(ed, bitems, nitems):
        _menu_regen(ed, bitems, nitems)
    # 6. form properties
    _apply_form_props(ed, base, new)
    # 7. OCX header lines for new controls
    for lib in sorted(ed.objects_needed):
        obj = object_of(lib)
        if obj is None:                    # "ctl:<Type>": a UserControl of the project, no Object line
            continue
        guid, ocx = obj
        if not any(guid.lower() in ln.lower() for ln in ed.lines[:ed.doc.root.start]):
            at = 1 if ed.lines and ed.lines[0].upper().startswith("VERSION") else 0
            ed.insert(at, [f'Object = "{guid}"; "{ocx}"'])
    ed.frx.save()
    if not ed.changed:
        return text, ed.notes, ed.objects_needed
    return ed.text(), ed.notes, ed.objects_needed


# ============================================================================ new form
def new_frm_text(form: Form, code: str, newline: str = "\r\n", frm_path: Path | None = None,
                 encoding: str = "cp1252") -> tuple[str, set[str]]:
    """A complete VB6 .frm for a form made in the IDE (Add Form)."""
    name = form.name
    w, h = int(form.props.get("Width", 400)) * TWIP, int(form.props.get("Height", 300)) * TWIP
    head = ["VERSION 5.00", f"Begin VB.Form {name} ",
            f"   Caption         =   {vb_str(form.props.get('Text', name))}",
            f"   ClientHeight    =   {h}", "   ClientLeft      =   60", "   ClientTop       =   345",
            f"   ClientWidth     =   {w}", f"   LinkTopic       =   {vb_str(name)}",
            f"   ScaleHeight     =   {h}", f"   ScaleWidth      =   {w}",
            "   StartUpPosition =   2  'CenterScreen" if form.props.get("StartPosition", "CenterScreen")
            == "CenterScreen" else "   StartUpPosition =   0  'Manual", "End",
            f"Attribute VB_Name = {vb_str(name)}", "Attribute VB_GlobalNameSpace = False",
            "Attribute VB_Creatable = False", "Attribute VB_PredeclaredId = True",
            "Attribute VB_Exposed = False"]
    text = newline.join(head) + newline
    base = Form()
    base.props.update(json_copy(form.props))
    if any(c for c in form.controls):
        base.controls = []
        text2, _notes, libs = apply_form_changes(text, base, form, frm_path or Path(f"{name}.frm"), encoding)
    else:
        text2, libs = text, set()
    return join_code(text2, code, newline), libs


def json_copy(d):
    import json
    return json.loads(json.dumps(d))
