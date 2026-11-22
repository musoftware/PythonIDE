"""PE resources: the resource tree (read / rebuild) and codecs for the standard resource types.

    entries = read_tree(img)                       # [ResEntry(type, name, lang, data, codepage)]
    blob = build_tree(entries, base_rva)           # a complete .rsrc section for that RVA

Codecs (bytes <-> editable model, all round-trip):
    Dialog / DlgControl      DIALOG and DIALOGEX              parse_dialog / build_dialog
    MenuItem                 MENU and MENUEX                  parse_menu / build_menu
    string tables            16-string blocks                 parse_string_block / build_string_blocks
    Accel                    ACCELERATORS                     parse_accel / build_accel
    VersionInfo              VS_VERSIONINFO                   parse_version / build_version
    icons / cursors          GROUP_ICON + ICON (.ico/.cur)    group_to_file / file_to_group
    bitmaps                  DIB <-> .bmp                     dib_to_bmp / bmp_to_dib
    Toolbar                  MFC RT_TOOLBAR (241)             parse_toolbar / build_toolbar
    DlgInit                  MFC RT_DLGINIT (240)             parse_dlginit / build_dlginit
"""
from __future__ import annotations

import functools
import struct
from dataclasses import dataclass, field


NUL = chr(0)


class ResourceFormatError(ValueError):
    """A resource blob (dialog, menu, string table, version ...) is truncated or corrupted."""


def _malformed(fn):
    """Truncated / corrupted resource data raises ResourceFormatError (a ValueError) instead of a bare
    struct.error / IndexError / RecursionError from deep inside the parser."""
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except (struct.error, IndexError, OverflowError, RecursionError, UnicodeError) as e:
            raise ResourceFormatError(f"{fn.__name__}: corrupted resource data ({type(e).__name__}: {e})") from None
    return wrapper

RT_CURSOR, RT_BITMAP, RT_ICON, RT_MENU, RT_DIALOG, RT_STRING, RT_FONTDIR, RT_FONT = 1, 2, 3, 4, 5, 6, 7, 8
RT_ACCELERATOR, RT_RCDATA, RT_MESSAGETABLE, RT_GROUP_CURSOR, RT_GROUP_ICON = 9, 10, 11, 12, 14
RT_VERSION, RT_DLGINCLUDE, RT_PLUGPLAY, RT_VXD, RT_ANICURSOR, RT_ANIICON, RT_HTML, RT_MANIFEST = \
    16, 17, 19, 20, 21, 22, 23, 24
RT_DLGINIT, RT_TOOLBAR = 240, 241

TYPE_NAMES = {RT_CURSOR: "Cursor", RT_BITMAP: "Bitmap", RT_ICON: "Icon", RT_MENU: "Menu", RT_DIALOG: "Dialog",
              RT_STRING: "String Table", RT_FONTDIR: "Font Directory", RT_FONT: "Font",
              RT_ACCELERATOR: "Accelerators", RT_RCDATA: "RCDATA", RT_MESSAGETABLE: "Message Table",
              RT_GROUP_CURSOR: "Cursor Group", RT_GROUP_ICON: "Icon Group", RT_VERSION: "Version",
              RT_DLGINCLUDE: "Dialog Include", RT_PLUGPLAY: "Plug and Play", RT_VXD: "VXD",
              RT_ANICURSOR: "Animated Cursor", RT_ANIICON: "Animated Icon", RT_HTML: "HTML",
              RT_MANIFEST: "Manifest", RT_DLGINIT: "Dialog Init (MFC)", RT_TOOLBAR: "Toolbar (MFC)"}
RC_KEYWORDS = {RT_CURSOR: "CURSOR", RT_BITMAP: "BITMAP", RT_ICON: "ICON", RT_MENU: "MENU", RT_DIALOG: "DIALOG",
               RT_STRING: "STRINGTABLE", RT_FONT: "FONT", RT_ACCELERATOR: "ACCELERATORS", RT_RCDATA: "RCDATA",
               RT_MESSAGETABLE: "MESSAGETABLE", RT_VERSION: "VERSIONINFO", RT_HTML: "HTML",
               RT_TOOLBAR: "TOOLBAR", RT_DLGINIT: "DLGINIT"}


def type_label(t) -> str:
    if isinstance(t, str):
        return t
    return TYPE_NAMES.get(t, f"Type {t}")


def name_label(n) -> str:
    return f'"{n}"' if isinstance(n, str) else str(n)


def lang_label(lang: int) -> str:
    try:
        from PyQt6.QtCore import QLocale
        if lang == 0:
            return "Neutral"
        loc = QLocale(_lcid_to_name(lang)) if _lcid_to_name(lang) else None
        if loc is not None and loc.language() != QLocale.Language.C:
            return f"{QLocale.languageToString(loc.language())} ({lang})"
    except Exception:  # noqa: BLE001
        pass
    return str(lang)


_LCIDS = {0x409: "en_US", 0x809: "en_GB", 0x401: "ar_SA", 0xC01: "ar_EG", 0x407: "de_DE", 0x40C: "fr_FR",
          0x410: "it_IT", 0x40A: "es_ES", 0xC0A: "es_ES", 0x411: "ja_JP", 0x412: "ko_KR", 0x804: "zh_CN",
          0x404: "zh_TW", 0x419: "ru_RU", 0x416: "pt_BR", 0x816: "pt_PT", 0x413: "nl_NL", 0x41F: "tr_TR",
          0x415: "pl_PL", 0x405: "cs_CZ", 0x40E: "hu_HU", 0x41D: "sv_SE", 0x406: "da_DK", 0x414: "nb_NO",
          0x40B: "fi_FI", 0x408: "el_GR", 0x40D: "he_IL", 0x429: "fa_IR", 0x420: "ur_PK", 0x41E: "th_TH"}


def _lcid_to_name(lang: int) -> str:
    return _LCIDS.get(lang, "")


# ============================================================================ tree
@dataclass
class ResEntry:
    type: int | str
    name: int | str
    lang: int
    data: bytes
    codepage: int = 0

    @property
    def key(self) -> tuple:
        return (self.type, self.name, self.lang)


def _rd_name(img, base: int, off: int) -> str:
    n = img.u16(base + off)
    return img.read(base + off + 2, 2 * n).decode("utf-16-le", "replace")


@_malformed
def read_tree(img) -> list[ResEntry]:
    """Every leaf of the resource directory (type -> name -> language)."""
    from .image import DIR_RESOURCE
    base, size = img.directory(DIR_RESOURCE)
    out: list[ResEntry] = []
    if not base:
        return out
    seen = set()

    def entries(off):
        if off in seen or len(seen) > 100000:
            return []
        seen.add(off)
        _c, _t, _ma, _mi, nnamed, nid = struct.unpack("<IIHHHH", img.read(base + off, 16))
        res = []
        for i in range(min(nnamed + nid, 4096)):
            name, target = struct.unpack("<II", img.read(base + off + 16 + 8 * i, 8))
            key = _rd_name(img, base, name & 0x7FFFFFFF) if name & 0x80000000 else name & 0xFFFF
            res.append((key, target))
        return res

    for t, toff in entries(0):
        if not toff & 0x80000000:
            continue
        for n, noff in entries(toff & 0x7FFFFFFF):
            if not noff & 0x80000000:
                continue
            for lang, loff in entries(noff & 0x7FFFFFFF):
                if loff & 0x80000000:
                    continue
                rva, sz, cp, _r = struct.unpack("<IIII", img.read(base + loff, 16))
                try:
                    data = img.read(rva, sz)
                except Exception:  # noqa: BLE001 - a broken leaf is skipped
                    continue
                out.append(ResEntry(t, n, lang if isinstance(lang, int) else 0, data, cp))
    return out


def _sort_key(k):
    return (0, k.upper(), k) if isinstance(k, str) else (1, "", k)


@_malformed
def build_tree(entries: list[ResEntry], base_rva: int) -> bytes:
    """Serialize resources into a .rsrc section placed at *base_rva* (data RVAs depend on it)."""
    tree: dict = {}
    for e in entries:
        tree.setdefault(e.type, {}).setdefault(e.name, {})[e.lang] = e
    types = sorted(tree, key=_sort_key)
    # directory sizes
    dir_size = lambda n: 16 + 8 * n                                          # noqa: E731
    off = dir_size(len(types))
    type_dir_off, name_dir_off = {}, {}
    for t in types:
        type_dir_off[t] = off
        off += dir_size(len(tree[t]))
    for t in types:
        for n in sorted(tree[t], key=_sort_key):
            name_dir_off[(t, n)] = off
            off += dir_size(len(tree[t][n]))
    data_entry_off = {}
    for t in types:
        for n in sorted(tree[t], key=_sort_key):
            for lang in sorted(tree[t][n]):
                data_entry_off[(t, n, lang)] = off
                off += 16
    strings = {}
    for t in types:
        for k in [t] + list(tree[t]):
            if isinstance(k, str) and k not in strings:
                strings[k] = off
                off += 2 + 2 * len(k)
    off = (off + 7) & ~7
    data_off = {}
    for t in types:
        for n in sorted(tree[t], key=_sort_key):
            for lang in sorted(tree[t][n]):
                data_off[(t, n, lang)] = off
                off += (len(tree[t][n][lang].data) + 7) & ~7
    out = bytearray(off)

    def write_dir(at, keys, target_of):
        named = [k for k in keys if isinstance(k, str)]
        ids = [k for k in keys if not isinstance(k, str)]
        struct.pack_into("<IIHHHH", out, at, 0, 0, 4, 0, len(named), len(ids))
        for i, k in enumerate(named + ids):
            name = (0x80000000 | strings[k]) if isinstance(k, str) else k
            struct.pack_into("<II", out, at + 16 + 8 * i, name, target_of(k))

    write_dir(0, types, lambda t: 0x80000000 | type_dir_off[t])
    for t in types:
        names = sorted(tree[t], key=_sort_key)
        write_dir(type_dir_off[t], names, lambda n, t=t: 0x80000000 | name_dir_off[(t, n)])
        for n in names:
            langs = sorted(tree[t][n])
            write_dir(name_dir_off[(t, n)], langs, lambda lg, t=t, n=n: data_entry_off[(t, n, lg)])
            for lang in langs:
                e = tree[t][n][lang]
                struct.pack_into("<IIII", out, data_entry_off[(t, n, lang)], base_rva + data_off[(t, n, lang)],
                                 len(e.data), e.codepage, 0)
                p = data_off[(t, n, lang)]
                out[p:p + len(e.data)] = e.data
    for k, at in strings.items():
        enc = k.encode("utf-16-le")
        struct.pack_into("<H", out, at, len(k))
        out[at + 2:at + 2 + len(enc)] = enc
    return bytes(out)


# ============================================================================ low-level reader
class Reader:
    def __init__(self, data: bytes, p: int = 0):
        self.d = data
        self.p = p

    def take(self, fmt: str):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v if len(v) > 1 else v[0]

    def wstr(self) -> str:
        end = self.p
        while end + 1 < len(self.d) and self.d[end:end + 2] != b"\0\0":
            end += 2
        s = self.d[self.p:end].decode("utf-16-le", "replace")
        self.p = end + 2
        return s

    def sz_or_ord(self):
        if self.p + 2 > len(self.d):
            return None
        first = struct.unpack_from("<H", self.d, self.p)[0]
        if first == 0:
            self.p += 2
            return None
        if first == 0xFFFF:
            self.p += 2
            return self.take("<H")
        return self.wstr()

    def align(self, n: int = 4) -> None:
        self.p = (self.p + n - 1) // n * n


def _w_str(s: str) -> bytes:
    return s.encode("utf-16-le") + b"\0\0"


def _w_sz_or_ord(v) -> bytes:
    if v is None or v == "":
        return b"\0\0"
    if isinstance(v, int):
        return struct.pack("<HH", 0xFFFF, v & 0xFFFF)
    return _w_str(v)


def _pad4(b: bytearray) -> None:
    while len(b) % 4:
        b += b"\0"


# ============================================================================ dialogs
# window / control styles used by the designer
WS_POPUP, WS_CHILD, WS_VISIBLE, WS_DISABLED, WS_CAPTION, WS_BORDER = \
    0x80000000, 0x40000000, 0x10000000, 0x08000000, 0x00C00000, 0x00800000
WS_SYSMENU, WS_THICKFRAME, WS_GROUP, WS_TABSTOP, WS_VSCROLL, WS_HSCROLL = \
    0x00080000, 0x00040000, 0x00020000, 0x00010000, 0x00200000, 0x00100000
WS_MINIMIZEBOX, WS_MAXIMIZEBOX = 0x00020000, 0x00010000
DS_SETFONT, DS_MODALFRAME, DS_CENTER, DS_SHELLFONT = 0x40, 0x80, 0x800, 0x48
ATOMS = {0x80: "Button", 0x81: "Edit", 0x82: "Static", 0x83: "ListBox", 0x84: "ScrollBar", 0x85: "ComboBox"}
ATOM_OF = {v.upper(): k for k, v in ATOMS.items()}


@dataclass
class DlgControl:
    cls: int | str              # atom (0x80 Button ...) or a window class name
    text: int | str | None      # caption, or an ordinal (icon / bitmap id)
    id: int
    style: int
    exstyle: int = 0
    x: int = 0
    y: int = 0
    cx: int = 10
    cy: int = 10
    help_id: int = 0
    extra: bytes = b""

    @property
    def class_name(self) -> str:
        return ATOMS.get(self.cls, f"0x{self.cls:X}") if isinstance(self.cls, int) else self.cls

    @property
    def kind(self) -> str:
        """Designer kind: PushButton, DefPushButton, CheckBox, RadioButton, GroupBox, Edit, Label, Icon,
        Picture, ComboBox, ListBox, ScrollBar, or Custom."""
        c = self.class_name.upper()
        s = self.style
        if c == "BUTTON":
            t = s & 0xF
            return {0: "PushButton", 1: "DefPushButton", 2: "CheckBox", 3: "CheckBox", 4: "RadioButton",
                    5: "CheckBox", 6: "CheckBox", 7: "GroupBox", 9: "RadioButton", 0xB: "PushButton",
                    0xC: "PushButton", 0xD: "DefPushButton", 0xE: "PushButton", 0xF: "PushButton"}.get(t, "PushButton")
        if c == "EDIT":
            return "Edit"
        if c == "STATIC":
            t = s & 0x1F
            if t == 3:
                return "Icon"
            if t in (0xE, 4, 5, 6, 7, 8, 9, 0x10, 0x11, 0x12):
                return "Picture"
            return "Label"
        if c == "COMBOBOX":
            return "ComboBox"
        if c == "LISTBOX":
            return "ListBox"
        if c == "SCROLLBAR":
            return "ScrollBar"
        return "Custom"

    @property
    def caption(self) -> str:
        if isinstance(self.text, int):
            return f"#{self.text}"
        return self.text or ""


@dataclass
class Dialog:
    extended: bool
    style: int
    exstyle: int
    x: int
    y: int
    cx: int
    cy: int
    menu: int | str | None = None
    wclass: int | str | None = None
    title: str = ""
    font_size: int = 0
    font_weight: int = 0
    italic: int = 0
    charset: int = 1
    font_name: str = ""
    help_id: int = 0
    controls: list = field(default_factory=list)

    @property
    def has_font(self) -> bool:
        return bool(self.style & DS_SETFONT)

    def base_units(self) -> tuple[float, float]:
        """Average character width / height of the dialog font at 96 DPI (dialog units -> pixels)."""
        if not self.has_font or not self.font_size:
            return 8.0, 16.0
        pt = max(6, min(int(self.font_size), 36))
        if "segoe" in self.font_name.lower():
            return round(pt * 0.78), round(pt * 1.667)
        return round(pt * 0.75), round(pt * 1.6)


@_malformed
def parse_dialog(data: bytes) -> Dialog:
    r = Reader(data)
    ver, sig = struct.unpack_from("<HH", data, 0)
    if ver == 1 and sig == 0xFFFF:
        r.p = 4
        help_id, exstyle, style, n, x, y, cx, cy = r.take("<IIIHhhhh")
        d = Dialog(True, style, exstyle, x, y, cx, cy, help_id=help_id)
    else:
        style, exstyle, n, x, y, cx, cy = r.take("<IIHhhhh")
        d = Dialog(False, style, exstyle, x, y, cx, cy)
    d.menu = r.sz_or_ord()
    d.wclass = r.sz_or_ord()
    d.title = r.wstr()
    if style & DS_SETFONT:
        d.font_size = r.take("<H")
        if d.extended:
            d.font_weight, d.italic, d.charset = r.take("<HBB")
        d.font_name = r.wstr()
    for _ in range(n):
        r.align(4)
        if r.p >= len(data):
            break
        if d.extended:
            hid, ex, st, x, y, cx, cy, cid = r.take("<IIIhhhhI")
        else:
            st, ex, x, y, cx, cy, cid = r.take("<IIhhhhH")
            hid = 0
        cls = r.sz_or_ord()
        text = r.sz_or_ord()
        extra = b""
        if r.p + 2 <= len(data):
            cnt = r.take("<H")
            if not d.extended and cnt:
                cnt = max(0, cnt - 2)
            extra = bytes(data[r.p:r.p + cnt])
            r.p += cnt
        if cid == 0xFFFF and not d.extended:
            cid = -1
        elif d.extended and cid == 0xFFFFFFFF:
            cid = -1
        d.controls.append(DlgControl(cls if cls is not None else "", text, cid, st, ex, x, y, cx, cy, hid, extra))
    return d


@_malformed
def build_dialog(d: Dialog) -> bytes:
    b = bytearray()
    n = len(d.controls)
    if d.extended:
        b += struct.pack("<HHIIIHhhhh", 1, 0xFFFF, d.help_id, d.exstyle, d.style, n, d.x, d.y, d.cx, d.cy)
    else:
        b += struct.pack("<IIHhhhh", d.style, d.exstyle, n, d.x, d.y, d.cx, d.cy)
    b += _w_sz_or_ord(d.menu) + _w_sz_or_ord(d.wclass) + _w_str(d.title or "")
    if d.style & DS_SETFONT:
        b += struct.pack("<H", d.font_size)
        if d.extended:
            b += struct.pack("<HBB", d.font_weight, d.italic, d.charset)
        b += _w_str(d.font_name)
    for c in d.controls:
        _pad4(b)
        cid = c.id
        if d.extended:
            b += struct.pack("<IIIhhhhI", c.help_id, c.exstyle, c.style, c.x, c.y, c.cx, c.cy, cid & 0xFFFFFFFF)
        else:
            b += struct.pack("<IIhhhhH", c.style, c.exstyle, c.x, c.y, c.cx, c.cy, cid & 0xFFFF)
        cls = c.cls
        if isinstance(cls, str) and cls.upper() in ATOM_OF:
            cls = ATOM_OF[cls.upper()]
        b += _w_sz_or_ord(cls) + _w_sz_or_ord(c.text if c.text is not None else "")
        if d.extended:
            b += struct.pack("<H", len(c.extra)) + c.extra
        else:
            b += struct.pack("<H", len(c.extra) + 2 if c.extra else 0) + c.extra
    return bytes(b)


# ============================================================================ menus
MF_GRAYED, MF_DISABLED, MF_CHECKED, MF_POPUP, MF_MENUBARBREAK, MF_MENUBREAK, MF_END, MF_HELP = \
    0x1, 0x2, 0x8, 0x10, 0x20, 0x40, 0x80, 0x4000
MFT_SEPARATOR, MFT_RIGHTJUSTIFY, MFT_RADIOCHECK = 0x800, 0x4000, 0x200
MFS_GRAYED, MFS_CHECKED, MFS_DEFAULT = 0x3, 0x8, 0x1000


@dataclass
class MenuItem:
    text: str = ""
    id: int = 0
    flags: int = 0             # MENU: MF_* flags without MF_POPUP / MF_END;  MENUEX: dwType
    state: int = 0             # MENUEX: dwState
    help_id: int = 0           # MENUEX popups
    children: list | None = None

    @property
    def is_popup(self) -> bool:
        return self.children is not None

    @property
    def is_separator(self) -> bool:
        return not self.is_popup and (self.flags & MFT_SEPARATOR or (not self.text and self.id == 0))


@dataclass
class Menu:
    extended: bool
    items: list = field(default_factory=list)
    help_id: int = 0


@_malformed
def parse_menu(data: bytes) -> Menu:
    ver, off = struct.unpack_from("<HH", data, 0)
    if ver == 1:
        help_id = struct.unpack_from("<I", data, 4)[0] if off >= 4 else 0
        r = Reader(data, 4 + off)
        m = Menu(True, help_id=help_id)

        def level_ex(depth=0):
            items = []
            while r.p + 14 <= len(data) and depth < 32:
                typ, state, mid, flags = r.take("<IIIH")
                text = r.wstr()
                r.align(4)
                it = MenuItem(text, mid, typ, state)
                if flags & 0x01:
                    it.help_id = r.take("<I")
                    it.children = level_ex(depth + 1)
                items.append(it)
                if flags & MF_END:
                    break
            return items
        m.items = level_ex()
        return m
    r = Reader(data, 4 + off)
    m = Menu(False)

    def level(depth=0):
        items = []
        while r.p + 2 <= len(data) and depth < 32:
            flags = r.take("<H")
            if flags & MF_POPUP:
                it = MenuItem(r.wstr(), 0, flags & ~(MF_POPUP | MF_END))
                it.children = level(depth + 1)
            else:
                mid = r.take("<H")
                it = MenuItem(r.wstr(), mid, flags & ~MF_END)
            items.append(it)
            if flags & MF_END:
                break
        return items
    m.items = level()
    return m


@_malformed
def build_menu(m: Menu) -> bytes:
    b = bytearray()
    if m.extended:
        b += struct.pack("<HHI", 1, 4, m.help_id)

        def level_ex(items):
            for i, it in enumerate(items):
                last = i == len(items) - 1
                flags = (0x01 if it.is_popup else 0) | (MF_END if last else 0)
                b.extend(struct.pack("<IIIH", it.flags, it.state, it.id & 0xFFFFFFFF, flags) + _w_str(it.text))
                _pad4(b)
                if it.is_popup:
                    b.extend(struct.pack("<I", it.help_id))
                    level_ex(it.children or [])
        level_ex(m.items)
        return bytes(b)
    b += struct.pack("<HH", 0, 0)

    def level(items):
        for i, it in enumerate(items):
            last = MF_END if i == len(items) - 1 else 0
            if it.is_popup:
                b.extend(struct.pack("<H", (it.flags & ~MF_END) | MF_POPUP | last) + _w_str(it.text))
                level(it.children or [])
            else:
                b.extend(struct.pack("<HH", (it.flags & ~(MF_END | MF_POPUP)) | last, it.id & 0xFFFF) +
                         _w_str(it.text))
    level(m.items)
    return bytes(b)


def menu_commands(items, path=()) -> list[tuple[int, str]]:
    """[(command id, "File > Exit")] of a menu tree."""
    out = []
    for it in items:
        label = it.text.replace("&", "").split("\t")[0]
        if it.is_popup:
            out += menu_commands(it.children or [], path + (label,))
        elif it.id and not it.is_separator:
            out.append((it.id, " > ".join(path + (label,))))
    return out


# ============================================================================ string tables
@_malformed
def parse_string_block(data: bytes, block_id: int) -> dict[int, str]:
    out = {}
    r = Reader(data)
    for i in range(16):
        if r.p + 2 > len(data):
            break
        n = r.take("<H")
        if n:
            out[(block_id - 1) * 16 + i] = data[r.p:r.p + 2 * n].decode("utf-16-le", "replace")
        r.p += 2 * n
    return out


@_malformed
def build_string_blocks(strings: dict[int, str]) -> dict[int, bytes]:
    """{block id: data} for {string id: text} (blocks of 16 consecutive ids)."""
    blocks: dict[int, dict[int, str]] = {}
    for sid, text in strings.items():
        blocks.setdefault(sid // 16 + 1, {})[sid % 16] = text
    out = {}
    for bid, items in blocks.items():
        b = bytearray()
        for i in range(16):
            t = items.get(i, "")
            b += struct.pack("<H", len(t)) + t.encode("utf-16-le")
        out[bid] = bytes(b)
    return out


# ============================================================================ accelerators
FVIRTKEY, FNOINVERT, FSHIFT, FCONTROL, FALT = 0x01, 0x02, 0x04, 0x08, 0x10


@dataclass
class Accel:
    flags: int
    key: int
    cmd: int

    def key_text(self) -> str:
        parts = []
        if self.flags & FCONTROL:
            parts.append("Ctrl")
        if self.flags & FALT:
            parts.append("Alt")
        if self.flags & FSHIFT:
            parts.append("Shift")
        if self.flags & FVIRTKEY:
            parts.append(VK_NAMES.get(self.key, chr(self.key) if 0x30 <= self.key <= 0x5A else f"VK_0x{self.key:X}"))
        else:
            parts.append(f'"{chr(self.key)}"' if 32 <= self.key < 127 else f"0x{self.key:X}")
        return "+".join(parts)


VK_NAMES = {0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc", 0x20: "Space", 0x21: "PageUp",
            0x22: "PageDown", 0x23: "End", 0x24: "Home", 0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
            0x2D: "Insert", 0x2E: "Delete", **{0x70 + i: f"F{i + 1}" for i in range(24)}}
VK_BY_NAME = {v.upper(): k for k, v in VK_NAMES.items()}


@_malformed
def parse_accel(data: bytes) -> list[Accel]:
    out = []
    for i in range(len(data) // 8):
        f, k, c, _p = struct.unpack_from("<HHHH", data, 8 * i)
        out.append(Accel(f & 0x7F, k, c))
        if f & 0x80:
            break
    return out


@_malformed
def build_accel(items: list[Accel]) -> bytes:
    b = bytearray()
    for i, a in enumerate(items):
        b += struct.pack("<HHHH", (a.flags & 0x7F) | (0x80 if i == len(items) - 1 else 0), a.key, a.cmd, 0)
    return bytes(b)


def parse_key_text(text: str) -> tuple[int, int]:
    """"Ctrl+Shift+F5" -> (flags, key)."""
    flags, key = FVIRTKEY, 0
    for part in [p.strip() for p in text.split("+") if p.strip()]:
        u = part.upper()
        if u in ("CTRL", "CONTROL"):
            flags |= FCONTROL
        elif u == "ALT":
            flags |= FALT
        elif u == "SHIFT":
            flags |= FSHIFT
        elif u in VK_BY_NAME:
            key = VK_BY_NAME[u]
        elif len(part) == 3 and part[0] == part[2] == '"':
            flags &= ~FVIRTKEY
            key = ord(part[1])
        elif len(u) == 1:
            key = ord(u)
        elif u.startswith("VK_0X") or u.startswith("0X"):
            key = int(u.replace("VK_", ""), 16)
        else:
            raise ValueError(f"Unknown key: {part}")
    if not key:
        raise ValueError("No key given.")
    return flags, key


# ============================================================================ version info
VERSION_FIELDS = ("FileVersion", "ProductVersion")


@dataclass
class VersionInfo:
    file_version: tuple = (0, 0, 0, 0)
    product_version: tuple = (0, 0, 0, 0)
    flags_mask: int = 0x3F
    flags: int = 0
    os: int = 0x40004
    file_type: int = 1
    file_subtype: int = 0
    date: int = 0
    strings: dict = field(default_factory=dict)       # "040904b0" -> {key: value}
    translations: list = field(default_factory=list)  # [(lang, codepage)]
    has_fixed: bool = True


def _node(data: bytes, off: int):
    length, vlen, typ = struct.unpack_from("<HHH", data, off)
    r = Reader(data, off + 6)
    key = r.wstr()
    r.align(4)
    if typ == 1:                                   # text value (length in characters, sometimes in bytes)
        raw = data[r.p:min(off + length, r.p + vlen * 2)]
        nul = raw.find(b"\0\0")
        while nul != -1 and nul % 2:
            nul = raw.find(b"\0\0", nul + 1)
        value = (raw[:nul] if nul != -1 else raw).decode("utf-16-le", "replace")
        vbytes = vlen * 2
        if r.p + vbytes > off + length:
            vbytes = vlen
    else:
        value = data[r.p:r.p + vlen]
        vbytes = vlen
    p = (r.p + vbytes + 3) & ~3
    children = []
    end = off + length
    while p + 6 <= end:
        clen = struct.unpack_from("<H", data, p)[0]
        if clen == 0:
            break
        children.append(_node(data, p))
        p = (p + clen + 3) & ~3
    return key, typ, value, children


@_malformed
def parse_version(data: bytes) -> VersionInfo:
    key, _t, value, children = _node(data, 0)
    v = VersionInfo()
    if len(value) >= 52 and struct.unpack_from("<I", value, 0)[0] == 0xFEEF04BD:
        (_sig, _sv, fms, fls, pms, pls, v.flags_mask, v.flags, v.os, v.file_type, v.file_subtype, dms, dls) = \
            struct.unpack_from("<13I", value, 0)
        v.file_version = (fms >> 16, fms & 0xFFFF, fls >> 16, fls & 0xFFFF)
        v.product_version = (pms >> 16, pms & 0xFFFF, pls >> 16, pls & 0xFFFF)
        v.date = (dms << 32) | dls
    else:
        v.has_fixed = False
    for ckey, _ct, _cv, cch in children:
        if ckey == "StringFileInfo":
            for tkey, _tt, _tv, strings in cch:
                v.strings[tkey] = {sk: sv if isinstance(sv, str) else  # a binary node where text belongs
                                   bytes(sv).decode("utf-16-le", "replace").split(NUL, 1)[0]
                                   for sk, _st, sv, _sc in strings}
        elif ckey == "VarFileInfo":
            for vkey, _vt, vval, _vc in cch:
                if vkey == "Translation" and isinstance(vval, (bytes, bytearray)):
                    for i in range(len(vval) // 4):
                        v.translations.append(struct.unpack_from("<HH", vval, 4 * i))
    return v


def _build_node(key: str, value, children: list[bytes], text: bool) -> bytes:
    b = bytearray(6) + _w_str(key)
    _pad4(b)
    if text:
        vb = _w_str(value) if value is not None else b""
        vlen = len(vb) // 2 if value is not None else 0
    else:
        vb = bytes(value or b"")
        vlen = len(vb)
    b += vb
    for c in children:
        _pad4(b)
        b += c
    struct.pack_into("<HHH", b, 0, len(b), vlen, 1 if text else 0)
    return bytes(b)


@_malformed
def build_version(v: VersionInfo) -> bytes:
    fixed = b""
    if v.has_fixed:
        fv, pv = v.file_version, v.product_version
        fixed = struct.pack("<13I", 0xFEEF04BD, 0x10000, (fv[0] << 16) | fv[1], (fv[2] << 16) | fv[3],
                            (pv[0] << 16) | pv[1], (pv[2] << 16) | pv[3], v.flags_mask, v.flags, v.os, v.file_type,
                            v.file_subtype, v.date >> 32, v.date & 0xFFFFFFFF)
    children = []
    if v.strings:
        tables = [_build_node(tkey, None, [_build_node(k, val, [], True) for k, val in items.items()], True)
                  for tkey, items in v.strings.items()]
        children.append(_build_node("StringFileInfo", None, tables, True))
    if v.translations:
        val = b"".join(struct.pack("<HH", lg, cp) for lg, cp in v.translations)
        children.append(_build_node("VarFileInfo", None, [_build_node("Translation", val, [], False)], True))
    return _build_node("VS_VERSION_INFO", fixed, children, False)


def version_string(t: tuple) -> str:
    return ".".join(str(x) for x in t)


def parse_version_string(s: str) -> tuple:
    parts = [int(p) for p in s.replace(",", ".").split(".") if p.strip() != ""]
    parts = (parts + [0, 0, 0, 0])[:4]
    if any(not 0 <= p <= 0xFFFF for p in parts):
        raise ValueError("Each part of a version must be 0..65535.")
    return tuple(parts)


# ============================================================================ icons / cursors
@_malformed
def group_entries(group: bytes) -> list[dict]:
    _r, typ, count = struct.unpack_from("<HHH", group, 0)
    out = []
    for i in range(count):
        o = 6 + 14 * i
        if o + 14 > len(group):
            break
        if typ == 2:                                    # cursor group
            w, h, planes, bits, size, rid = struct.unpack_from("<HHHHIH", group, o)
            out.append({"w": w, "h": h // 2, "colors": 0, "planes": planes, "bits": bits, "size": size, "id": rid})
        else:
            w, h, colors, _res, planes, bits, size, rid = struct.unpack_from("<BBBBHHIH", group, o)
            out.append({"w": w or 256, "h": h or 256, "colors": colors, "planes": planes, "bits": bits,
                        "size": size, "id": rid})
    return out


@_malformed
def group_to_file(group: bytes, images: dict[int, bytes], cursor: bool = False) -> bytes:
    """GROUP_ICON / GROUP_CURSOR + the ICON / CURSOR images -> .ico / .cur file bytes."""
    ents = [e for e in group_entries(group) if e["id"] in images]
    head = struct.pack("<HHH", 0, 2 if cursor else 1, len(ents))
    offset = 6 + 16 * len(ents)
    dir_b, body = bytearray(), bytearray()
    for e in ents:
        img = images[e["id"]]
        hx = hy = 0
        if cursor:
            hx, hy = struct.unpack_from("<HH", img, 0)
            img = img[4:]
        w, h = e["w"], e["h"]
        dir_b += struct.pack("<BBBBHHII", w if w < 256 else 0, h if h < 256 else 0, e["colors"], 0,
                             hx if cursor else e["planes"], hy if cursor else e["bits"], len(img), offset + len(body))
        body += img
    return head + bytes(dir_b) + bytes(body)


@_malformed
def file_to_group(data: bytes, first_id: int, cursor: bool = False) -> tuple[bytes, dict[int, bytes]]:
    """.ico / .cur file -> (group data, {image id: image data}) with image ids from *first_id*."""
    _r, typ, count = struct.unpack_from("<HHH", data, 0)
    if typ not in (1, 2) or not 0 < count < 512:
        raise ValueError("Not an .ico / .cur file.")
    group = bytearray(struct.pack("<HHH", 0, 2 if cursor else 1, count))
    images = {}
    for i in range(count):
        w, h, colors, _res, a, b, size, off = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        img = data[off:off + size]
        rid = first_id + i
        planes, bits = (a, b) if typ == 1 else (1, 0)
        if len(img) >= 40 and struct.unpack_from("<I", img, 0)[0] == 40:
            planes, bits = struct.unpack_from("<HH", img, 12)
        if cursor:
            hx, hy = (a, b) if typ == 2 else (0, 0)
            images[rid] = struct.pack("<HH", hx, hy) + img
            group += struct.pack("<HHHHIH", w or 256, (h or 256) * 2, planes, bits, len(img) + 4, rid)
        else:
            images[rid] = img
            group += struct.pack("<BBBBHHIH", w, h, colors, 0, planes, bits, len(img), rid)
    return bytes(group), images


@_malformed
def dib_to_bmp(dib: bytes) -> bytes:
    hsize = struct.unpack_from("<I", dib, 0)[0]
    if hsize == 12:                                     # BITMAPCOREHEADER
        bits = struct.unpack_from("<H", dib, 10)[0]
        colors = (1 << bits) * 3 if bits <= 8 else 0
        masks = 0
    else:
        bits, comp = struct.unpack_from("<HI", dib, 14)
        used = struct.unpack_from("<I", dib, 32)[0] if hsize >= 36 else 0
        colors = (used or ((1 << bits) if bits <= 8 else 0)) * 4
        masks = 12 if comp in (3, 6) and hsize == 40 else 0
    off = 14 + hsize + colors + masks
    return b"BM" + struct.pack("<IHHI", 14 + len(dib), 0, 0, off) + dib


def bmp_to_dib(bmp: bytes) -> bytes:
    if bmp[:2] != b"BM":
        raise ValueError("Not a .bmp file.")
    return bmp[14:]


def png_or_ico_image(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n"


# ============================================================================ MFC toolbar / dialog init
@dataclass
class Toolbar:
    width: int = 16
    height: int = 15
    ids: list = field(default_factory=list)          # 0 = separator
    version: int = 1


@_malformed
def parse_toolbar(data: bytes) -> Toolbar:
    ver, w, h, n = struct.unpack_from("<HHHH", data, 0)
    ids = list(struct.unpack_from(f"<{n}H", data, 8)) if 8 + 2 * n <= len(data) else []
    return Toolbar(w, h, ids, ver)


@_malformed
def build_toolbar(t: Toolbar) -> bytes:
    return struct.pack("<HHHH", t.version, t.width, t.height, len(t.ids)) + struct.pack(f"<{len(t.ids)}H", *t.ids)


DLGINIT_MSGS = {0x0403: "CB_ADDSTRING", 0x0180: "LB_ADDSTRING", 0x1234: "CBEM_INSERTITEM (MFC)",
                0x0401: "WM_USER+1"}


@dataclass
class DlgInitItem:
    ctrl_id: int
    msg: int
    data: bytes

    @property
    def text(self) -> str:
        return self.data.split(b"\0", 1)[0].decode("mbcs" if _has_mbcs() else "latin-1", "replace")


def _has_mbcs() -> bool:
    try:
        "a".encode("mbcs")
        return True
    except LookupError:
        return False


@_malformed
def parse_dlginit(data: bytes) -> list[DlgInitItem]:
    out, p = [], 0
    while p + 2 <= len(data):
        cid = struct.unpack_from("<H", data, p)[0]
        if cid == 0 or p + 8 > len(data):
            break
        msg, ln = struct.unpack_from("<HI", data, p + 2)
        out.append(DlgInitItem(cid, msg, bytes(data[p + 8:p + 8 + ln])))
        p += 8 + ln
    return out


@_malformed
def build_dlginit(items: list[DlgInitItem]) -> bytes:
    b = bytearray()
    for it in items:
        b += struct.pack("<HHI", it.ctrl_id, it.msg, len(it.data)) + it.data
    return bytes(b + b"\0\0")


def text_item(ctrl_id: int, text: str, msg: int = 0x0403) -> DlgInitItem:
    enc = "mbcs" if _has_mbcs() else "latin-1"
    return DlgInitItem(ctrl_id, msg, text.encode(enc, "replace") + b"\0")
