"""MFC message maps inside a PE file: find them, name their classes (RTTI), describe and edit the entries.

MFC keeps every class's event table in the program as data:

    struct AFX_MSGMAP_ENTRY { UINT nMessage, nCode, nID, nLastID; UINT_PTR nSig; AFX_PMSG pfn; };
                                          // 24 bytes in 32-bit programs, 32 bytes in 64-bit programs
    struct AFX_MSGMAP { const AFX_MSGMAP* (*pfnGetBaseMap)(); const AFX_MSGMAP_ENTRY* lpEntries; };

The entry list ends with an all-zero entry. ``find_message_maps`` scans the data sections for AFX_MSGMAP
structures whose entries look like that (handler pointers into code), follows pfnGetBaseMap to the base
class's map, and names classes through the RTTI of the vtable that holds GetMessageMap().

Edits (applied by radide/pe/document.py with undo, backups and relocation fixes):
    retarget an entry to another function / remove an entry / add an entry (the table is moved to the
    patch section when there is no room).
"""
from __future__ import annotations

import re
import struct
from collections import Counter
from dataclasses import dataclass, field

from .image import PEImage

WM_COMMAND, WM_NOTIFY, WM_REGISTERED = 0x0111, 0x004E, 0xC000
CN_COMMAND, CN_UPDATE_COMMAND_UI = 0, 0xFFFFFFFF
WM_REFLECT_BASE = 0xBC00

WM_NAMES = {
    0x0001: "WM_CREATE", 0x0002: "WM_DESTROY", 0x0003: "WM_MOVE", 0x0005: "WM_SIZE", 0x0006: "WM_ACTIVATE",
    0x0007: "WM_SETFOCUS", 0x0008: "WM_KILLFOCUS", 0x000A: "WM_ENABLE", 0x000F: "WM_PAINT", 0x0010: "WM_CLOSE",
    0x0011: "WM_QUERYENDSESSION", 0x0014: "WM_ERASEBKGND", 0x0015: "WM_SYSCOLORCHANGE", 0x0016: "WM_ENDSESSION",
    0x0018: "WM_SHOWWINDOW", 0x001A: "WM_SETTINGCHANGE", 0x001C: "WM_ACTIVATEAPP", 0x0020: "WM_SETCURSOR",
    0x0021: "WM_MOUSEACTIVATE", 0x0024: "WM_GETMINMAXINFO", 0x002B: "WM_DRAWITEM", 0x002C: "WM_MEASUREITEM",
    0x002D: "WM_DELETEITEM", 0x0030: "WM_SETFONT", 0x0037: "WM_QUERYDRAGICON", 0x004A: "WM_COPYDATA",
    0x004E: "WM_NOTIFY", 0x0053: "WM_HELP", 0x007B: "WM_CONTEXTMENU", 0x007E: "WM_DISPLAYCHANGE",
    0x0081: "WM_NCCREATE", 0x0082: "WM_NCDESTROY", 0x0083: "WM_NCCALCSIZE", 0x0084: "WM_NCHITTEST",
    0x0085: "WM_NCPAINT", 0x0086: "WM_NCACTIVATE", 0x0087: "WM_GETDLGCODE", 0x00A0: "WM_NCMOUSEMOVE",
    0x00A1: "WM_NCLBUTTONDOWN", 0x00A3: "WM_NCLBUTTONDBLCLK", 0x0100: "WM_KEYDOWN", 0x0101: "WM_KEYUP",
    0x0102: "WM_CHAR", 0x0104: "WM_SYSKEYDOWN", 0x0110: "WM_INITDIALOG", 0x0111: "WM_COMMAND",
    0x0112: "WM_SYSCOMMAND", 0x0113: "WM_TIMER", 0x0114: "WM_HSCROLL", 0x0115: "WM_VSCROLL",
    0x0116: "WM_INITMENU", 0x0117: "WM_INITMENUPOPUP", 0x011F: "WM_MENUSELECT", 0x0120: "WM_MENUCHAR",
    0x0121: "WM_ENTERIDLE", 0x0132: "WM_CTLCOLORMSGBOX", 0x0133: "WM_CTLCOLOREDIT", 0x0134: "WM_CTLCOLORLISTBOX",
    0x0135: "WM_CTLCOLORBTN", 0x0136: "WM_CTLCOLORDLG", 0x0137: "WM_CTLCOLORSCROLLBAR", 0x0138: "WM_CTLCOLORSTATIC",
    0x0200: "WM_MOUSEMOVE", 0x0201: "WM_LBUTTONDOWN", 0x0202: "WM_LBUTTONUP", 0x0203: "WM_LBUTTONDBLCLK",
    0x0204: "WM_RBUTTONDOWN", 0x0205: "WM_RBUTTONUP", 0x0206: "WM_RBUTTONDBLCLK", 0x0207: "WM_MBUTTONDOWN",
    0x0208: "WM_MBUTTONUP", 0x020A: "WM_MOUSEWHEEL", 0x020E: "WM_MOUSEHWHEEL", 0x0210: "WM_PARENTNOTIFY",
    0x0211: "WM_ENTERMENULOOP", 0x0212: "WM_EXITMENULOOP", 0x0214: "WM_SIZING", 0x0215: "WM_CAPTURECHANGED",
    0x0216: "WM_MOVING", 0x0218: "WM_POWERBROADCAST", 0x0219: "WM_DEVICECHANGE", 0x0220: "WM_MDICREATE",
    0x0222: "WM_MDIACTIVATE", 0x0231: "WM_ENTERSIZEMOVE", 0x0232: "WM_EXITSIZEMOVE", 0x0233: "WM_DROPFILES",
    0x02A3: "WM_MOUSELEAVE", 0x02E0: "WM_DPICHANGED", 0x0300: "WM_CUT", 0x0301: "WM_COPY", 0x0302: "WM_PASTE",
    0x0303: "WM_CLEAR", 0x0304: "WM_UNDO", 0x0311: "WM_PALETTECHANGED", 0x0312: "WM_HOTKEY",
    0x0317: "WM_PRINT", 0x0318: "WM_PRINTCLIENT", 0x031A: "WM_THEMECHANGED", 0x0363: "WM_IDLEUPDATECMDUI",
    0x0364: "WM_INITIALUPDATE", 0x0365: "WM_COMMANDHELP", 0x0366: "WM_HELPHITTEST", 0x0367: "WM_EXITHELPMODE",
    0x0368: "WM_RECALCPARENT", 0x0369: "WM_SIZECHILD", 0x036A: "WM_KICKIDLE", 0x036B: "WM_QUERYCENTERWND",
    0x036C: "WM_DISABLEMODAL", 0x036D: "WM_FLOATSTATUS", 0x036E: "WM_ACTIVATETOPLEVEL",
    0x0373: "WM_SETMESSAGESTRING (MFC)", 0x0376: "WM_POPMESSAGESTRING (MFC)", 0x0377: "WM_HELPPROMPTADDR (MFC)",
}
BN_NAMES = {0: "BN_CLICKED", 1: "BN_PAINT", 2: "BN_HILITE", 3: "BN_UNHILITE", 4: "BN_DISABLE",
            5: "BN_DOUBLECLICKED", 6: "BN_SETFOCUS", 7: "BN_KILLFOCUS"}
EN_NAMES = {0x100: "EN_SETFOCUS", 0x200: "EN_KILLFOCUS", 0x300: "EN_CHANGE", 0x400: "EN_UPDATE",
            0x500: "EN_ERRSPACE", 0x501: "EN_MAXTEXT", 0x601: "EN_HSCROLL", 0x602: "EN_VSCROLL"}
CBN_NAMES = {1: "CBN_SELCHANGE", 2: "CBN_DBLCLK", 3: "CBN_SETFOCUS", 4: "CBN_KILLFOCUS", 5: "CBN_EDITCHANGE",
             6: "CBN_EDITUPDATE", 7: "CBN_DROPDOWN", 8: "CBN_CLOSEUP", 9: "CBN_SELENDOK", 10: "CBN_SELENDCANCEL"}
LBN_NAMES = {1: "LBN_SELCHANGE", 2: "LBN_DBLCLK", 3: "LBN_SELCANCEL", 4: "LBN_SETFOCUS", 5: "LBN_KILLFOCUS"}
STN_NAMES = {0: "STN_CLICKED", 1: "STN_DBLCLK", 2: "STN_ENABLE", 3: "STN_DISABLE"}
NM_NAMES = {0xFFFFFFFF - i + 1: n for i, n in [(1, "NM_OUTOFMEMORY"), (2, "NM_CLICK"), (3, "NM_DBLCLK"),
                                                 (4, "NM_RETURN"), (5, "NM_RCLICK"), (6, "NM_RDBLCLK"),
                                                 (7, "NM_SETFOCUS"), (8, "NM_KILLFOCUS"), (12, "NM_CUSTOMDRAW"),
                                                 (13, "NM_HOVER")]}
NM_NAMES.update({0xFFFFFF9B: "LVN_ITEMCHANGED", 0xFFFFFF94: "LVN_COLUMNCLICK", 0xFFFFFE6E: "TVN_SELCHANGED",
                 0xFFFFFDDA: "TCN_SELCHANGE", 0xFFFFFD2E: "UDN_DELTAPOS", 0xFFFFFD09: "DTN_DATETIMECHANGE"})

# notification codes that a control kind sends (for "add handler")
EVENTS_FOR_KIND = {
    "PushButton": [(0, "BN_CLICKED"), (5, "BN_DOUBLECLICKED")],
    "DefPushButton": [(0, "BN_CLICKED")],
    "CheckBox": [(0, "BN_CLICKED")],
    "RadioButton": [(0, "BN_CLICKED")],
    "Edit": [(0x300, "EN_CHANGE"), (0x200, "EN_KILLFOCUS"), (0x100, "EN_SETFOCUS"), (0x400, "EN_UPDATE")],
    "ComboBox": [(1, "CBN_SELCHANGE"), (5, "CBN_EDITCHANGE"), (7, "CBN_DROPDOWN"), (2, "CBN_DBLCLK")],
    "ListBox": [(1, "LBN_SELCHANGE"), (2, "LBN_DBLCLK")],
    "Label": [(0, "STN_CLICKED"), (1, "STN_DBLCLK")],
    "Picture": [(0, "STN_CLICKED"), (1, "STN_DBLCLK")],
    "Icon": [(0, "STN_CLICKED")],
    "Custom": [(0, "BN_CLICKED (code 0)")],
    "GroupBox": [],
    "ScrollBar": [],
}


def message_name(msg: int) -> str:
    if msg == WM_REGISTERED:
        return "registered message"
    if msg in WM_NAMES:
        return WM_NAMES[msg]
    if WM_REFLECT_BASE <= msg < WM_REFLECT_BASE + 0x400:
        return "=" + message_name(msg - WM_REFLECT_BASE)
    if 0x400 <= msg < 0x8000:
        return f"WM_USER+{msg - 0x400}"
    if 0x8000 <= msg < 0xC000:
        return f"WM_APP+{msg - 0x8000}"
    return f"0x{msg:04X}"


def code_name(code: int, kind: str = "") -> str:
    if code == CN_UPDATE_COMMAND_UI:
        return "UPDATE_COMMAND_UI"
    k = kind.upper()
    for prefix, table in (("BUTTON", BN_NAMES), ("PUSH", BN_NAMES), ("CHECK", BN_NAMES), ("RADIO", BN_NAMES),
                          ("EDIT", EN_NAMES), ("COMBO", CBN_NAMES), ("LIST", LBN_NAMES), ("LABEL", STN_NAMES),
                          ("STATIC", STN_NAMES), ("PICTURE", STN_NAMES)):
        if k.startswith(prefix) and code in table:
            return table[code]
    if code in EN_NAMES:
        return EN_NAMES[code]
    if code in NM_NAMES:
        return NM_NAMES[code]
    if code == 0:
        return "BN_CLICKED / command"
    return f"code {code:#x}" if code < 0x10000 else f"code {code - 0x100000000}"


@dataclass
class MsgEntry:
    index: int
    va: int                     # address of the entry
    msg: int
    code: int
    id: int
    last_id: int
    sig: int
    pfn: int

    def kind(self) -> str:
        """command / notify / update-ui / message / range"""
        if self.msg == WM_COMMAND:
            if self.code == CN_UPDATE_COMMAND_UI:
                return "update-ui"
            return "range" if self.last_id != self.id else "command"
        if self.msg == WM_NOTIFY:
            return "notify"
        return "message"

    def event_text(self, ctrl_kind: str = "") -> str:
        if self.msg == WM_COMMAND:
            if self.code == CN_UPDATE_COMMAND_UI:
                return "ON_UPDATE_COMMAND_UI"
            if self.code == 0:
                return "BN_CLICKED / ON_COMMAND"
            return code_name(self.code, ctrl_kind)
        if self.msg == WM_NOTIFY:
            return "WM_NOTIFY " + code_name(self.code)
        return message_name(self.msg)

    def macro(self, handler: str = "", names: dict | None = None) -> str:
        h = handler or f"sub_{self.pfn:X}"
        idt = (names or {}).get(self.id, str(self.id))
        lt = (names or {}).get(self.last_id, str(self.last_id))
        if self.msg == WM_COMMAND:
            if self.code == CN_UPDATE_COMMAND_UI:
                return f"ON_UPDATE_COMMAND_UI({idt}, {h})"
            if self.id != self.last_id:
                return f"ON_CONTROL_RANGE({code_name(self.code)}, {idt}, {lt}, {h})"
            if self.code == 0:
                return f"ON_COMMAND / ON_BN_CLICKED({idt}, {h})"
            if self.code in EN_NAMES:
                return f"ON_{EN_NAMES[self.code]}({idt}, {h})"
            return f"ON_CONTROL({code_name(self.code)}, {idt}, {h})"
        if self.msg == WM_NOTIFY:
            rng = f"{idt}, {lt}" if self.id != self.last_id else idt
            return f"ON_NOTIFY({code_name(self.code)}, {rng}, {h})"
        if self.msg == WM_REGISTERED:
            return f"ON_REGISTERED_MESSAGE(*0x{self.sig:X}, {h})"
        name = message_name(self.msg)
        if name.startswith("WM_") and "+" not in name and self.msg < 0x400:
            return f"ON_{name}()  -> {h}"
        return f"ON_MESSAGE({name}, {h})"

    def matches_control(self, ctrl_id: int) -> bool:
        return self.msg in (WM_COMMAND, WM_NOTIFY) and self.id <= (ctrl_id & 0xFFFF) <= self.last_id and \
            not (self.id == 0 and self.last_id == 0 and ctrl_id != 0)


@dataclass
class MsgMap:
    va: int                         # the AFX_MSGMAP structure
    entries_va: int
    get_base_va: int                # pfnGetBaseMap (0 for CCmdTarget)
    entries: list = field(default_factory=list)
    base_map_va: int = 0
    base_label: str = ""            # "mfc140u.dll import" when the base class lives in the MFC DLL
    class_name: str = ""
    getters: list = field(default_factory=list)    # functions returning this map (GetMessageMap / GetThisMessageMap)
    vtable_va: int = 0
    name_guessed: bool = False      # named from a derived class's RTTI (no vtable of its own)

    @property
    def label(self) -> str:
        return self.class_name or f"Class@{self.va:X}"

    def control_ids(self) -> set[int]:
        out = set()
        for e in self.entries:
            if e.msg in (WM_COMMAND, WM_NOTIFY) and e.last_id - e.id < 64:
                out.update(range(e.id, e.last_id + 1))
        return out


# ============================================================================ scanning
def _ranges(img: PEImage, code: bool) -> list[tuple[int, int]]:
    ib = img.image_base
    return [(ib + s.vaddr, ib + s.vaddr + max(s.vsize, s.raw_size)) for s in img.sections
            if bool(s.executable) == code and (s.raw_size or not code)]


def _in(ranges, v: int) -> bool:
    for a, b in ranges:
        if a <= v < b:
            return True
    return False


def entry_size(img: PEImage) -> int:
    return 16 + 2 * img.ptr_size


def read_entries(img: PEImage, va: int, code_ranges, data_ranges, limit: int = 4000) -> list[MsgEntry] | None:
    """The entries of a table at *va*, or None when it does not look like a message map."""
    P = img.ptr_size
    E = 16 + 2 * P
    fmt = "<IIII" + ("QQ" if P == 8 else "II")
    out = []
    try:
        blob = img.read_va(va, E * 64)
    except Exception:  # noqa: BLE001
        return None
    i = 0
    while i < limit:
        if (i + 1) * E > len(blob):
            try:
                blob += img.read_va(va + len(blob), E * 64)
            except Exception:  # noqa: BLE001
                return None
        msg, code, cid, last, sig, pfn = struct.unpack_from(fmt, blob, i * E)
        if sig == 0 and pfn == 0:
            return out if msg == 0 and cid == 0 and last == 0 else None
        if not _in(code_ranges, pfn):
            return None
        if msg > 0xC000 and not WM_REFLECT_BASE <= msg <= 0xBFFF:
            return None
        if cid > 0xFFFF or last > 0xFFFF or cid > last:
            return None
        if sig >= 0x400 and not (msg == WM_REGISTERED and _in(data_ranges, sig)):
            return None
        out.append(MsgEntry(i, va + i * E, msg, code, cid, last, sig, pfn))
        i += 1
    return None


def _returned_pointer(img: PEImage, va: int, depth: int = 0) -> tuple[int, str]:
    """(pointer returned by a tiny 'return &messageMap' function, import label if it jumps to an import)."""
    try:
        b = img.read_va(va, 32)
    except Exception:  # noqa: BLE001
        return 0, ""
    if img.is64:
        if b[:3] == b"\x48\x8D\x05" and b[7] == 0xC3:
            return va + 7 + struct.unpack_from("<i", b, 3)[0], ""
        if b[:2] == b"\xFF\x25":                                    # jmp [rip+x] -> import
            slot = va + 6 + struct.unpack_from("<i", b, 2)[0]
            return 0, _import_label(img, slot)
    else:
        if b[0] == 0xB8 and b[5] == 0xC3:
            return struct.unpack_from("<I", b, 1)[0], ""
        if b[:2] == b"\xFF\x25":
            return 0, _import_label(img, struct.unpack_from("<I", b, 2)[0])
        # unoptimized: push ebp / mov ebp, esp / mov eax, imm / pop ebp / ret
        m = re.match(rb"\x55\x8B\xEC\xB8(....)\x5D\xC3", b, re.S)
        if m:
            return struct.unpack("<I", m.group(1))[0], ""
    if b[0] == 0xE9 and depth < 4:                                  # incremental-link thunk
        return _returned_pointer(img, va + 5 + struct.unpack_from("<i", b, 1)[0], depth + 1)
    if img.is64 and depth < 4:
        m = re.match(rb"\x48\x8D\x05(....)\xC3", b, re.S)
        if m:
            return va + 7 + struct.unpack("<i", m.group(1))[0], ""
    return 0, ""


def _import_label(img: PEImage, slot_va: int) -> str:
    for im in img.imports():
        if img.image_base + im.iat_rva == slot_va:
            return im.label
    return ""


def find_message_maps(img: PEImage, progress=None) -> list[MsgMap]:
    progress = progress or (lambda _m: None)
    P = img.ptr_size
    code_r = _ranges(img, True)
    # tables, vtables and RTTI may also live in the code section (read-only data merged into .text)
    data_r = [(img.image_base, img.image_base + img.size_of_image)]
    ib = img.image_base
    maps: dict[int, MsgMap] = {}
    tables: dict[int, list[MsgEntry] | None] = {}
    fmt = "<" + ("Q" if P == 8 else "I")
    for s in img.sections:
        if not s.raw_size:
            continue
        raw = bytes(img.data[s.raw_ptr:s.raw_ptr + s.raw_size])
        ptrs = [v for (v,) in struct.iter_unpack(fmt, raw[:len(raw) // P * P])]
        base_va = ib + s.vaddr
        for i in range(len(ptrs) - 1):
            q0, q1 = ptrs[i], ptrs[i + 1]
            if q1 < ib or not (q0 == 0 or _in(code_r, q0)) or not _in(data_r, q1):
                continue
            if q1 not in tables:
                tables[q1] = read_entries(img, q1, code_r, data_r)
            ents = tables[q1]
            if not ents or (q0 == 0 and len(ents) < 1):
                continue
            va = base_va + i * P
            maps[va] = MsgMap(va, q1, q0, ents)
    progress(f"{len(maps)} message maps")
    # base classes
    pending = list(maps.values())
    while pending:
        m = pending.pop()
        if not m.get_base_va:
            continue
        ptr, label = _returned_pointer(img, m.get_base_va)
        m.base_label = label
        if ptr and ptr not in maps:
            try:
                q0, q1 = struct.unpack(fmt + fmt[1], img.read_va(ptr, 2 * P))
            except Exception:  # noqa: BLE001
                q0 = q1 = 0
            if q1 and (q0 == 0 or _in(code_r, q0)) and _in(data_r, q1):
                ents = read_entries(img, q1, code_r, data_r)
                if ents is not None:
                    maps[ptr] = MsgMap(ptr, q1, q0, ents)
                    pending.append(maps[ptr])
        if ptr in maps:
            m.base_map_va = ptr
    _name_classes(img, list(maps.values()), code_r, data_r)
    return sorted(maps.values(), key=lambda m: (not m.entries, m.label.lower(), m.va))


# ============================================================================ RTTI class names
def demangle_type(name: str) -> str:
    """'.?AVCMainDlg@@' -> 'CMainDlg', '.?AVInner@Outer@@' -> 'Outer::Inner'."""
    n = name
    for p in (".?AV", ".?AU", ".?AW4", ".?AT"):
        if n.startswith(p):
            n = n[len(p):]
            break
    n = n.rstrip("@")
    parts = [p for p in n.split("@") if p]
    if not parts or any(not re.fullmatch(r"[\w$<>?]+", p) for p in parts):
        return name
    return "::".join(reversed(parts))


def _td_name(img: PEImage, td: int) -> str:
    raw = img.read_va(td + 2 * img.ptr_size, 256)
    return raw.split(b"\0", 1)[0].decode("latin-1")


def _col_class(img: PEImage, col_va: int, data_r) -> tuple[str, int, list] | None:
    """(class name, number of base classes, [class and base class names]) from a RTTI Complete Object
    Locator, or None."""
    ib = img.image_base
    try:
        sig, offset, _cd, td, chd = struct.unpack("<IIIII", img.read_va(col_va, 20))
        if img.is64:
            if sig != 1:
                return None
            self_rva = struct.unpack("<I", img.read_va(col_va + 20, 4))[0]
            if self_rva != col_va - ib:
                return None
            td += ib
            chd += ib
        elif sig != 0:
            return None
        if offset != 0 or not _in(data_r, td):
            return None
        name = _td_name(img, td)
        if not name.startswith(".?A"):
            return None
        nbases, bases = 0, []
        if _in(data_r, chd):
            nbases, arr = struct.unpack("<II", img.read_va(chd + 8, 8))
            if img.is64:
                arr += ib
            for k in range(min(nbases, 64)):
                bcd = struct.unpack("<I", img.read_va(arr + 4 * k, 4))[0] + (ib if img.is64 else 0)
                btd = struct.unpack("<I", img.read_va(bcd, 4))[0] + (ib if img.is64 else 0)
                bases.append(demangle_type(_td_name(img, btd)))
        return demangle_type(name), nbases, bases
    except Exception:  # noqa: BLE001
        return None


def _name_classes(img: PEImage, maps: list[MsgMap], code_r, data_r) -> None:
    if not maps:
        return
    P = img.ptr_size
    ib = img.image_base
    by_ptr = {m.va: m for m in maps}
    # 1) functions that "return &messageMap"
    getters: dict[int, list[int]] = {}
    for s in img.sections:
        if not s.executable or not s.raw_size:
            continue
        raw = bytes(img.data[s.raw_ptr:s.raw_ptr + s.raw_size])
        base = ib + s.vaddr
        if img.is64:
            for mt in re.finditer(rb"\x48\x8D\x05(....)\xC3", raw, re.S):
                tgt = base + mt.start() + 7 + struct.unpack("<i", mt.group(1))[0]
                if tgt in by_ptr:
                    getters.setdefault(tgt, []).append(base + mt.start())
        else:
            for mt in re.finditer(rb"\xB8(....)\xC3", raw, re.S):
                tgt = struct.unpack("<I", mt.group(1))[0]
                if tgt in by_ptr:
                    getters.setdefault(tgt, []).append(base + mt.start())
    func_to_map = {}
    for tgt, fns in getters.items():
        by_ptr[tgt].getters = sorted(fns)
        for f in fns:
            func_to_map[f] = tgt
    if not func_to_map:
        return
    # 2) vtable slots pointing at those functions -> RTTI of the vtable
    fmt = "<" + ("Q" if P == 8 else "I")
    candidates: dict[int, list[tuple[int, str, int, list]]] = {}
    for s in img.sections:
        if not s.raw_size:
            continue
        raw = bytes(img.data[s.raw_ptr:s.raw_ptr + s.raw_size])
        ptrs = [v for (v,) in struct.iter_unpack(fmt, raw[:len(raw) // P * P])]
        base = ib + s.vaddr
        for i, v in enumerate(ptrs):
            if v not in func_to_map:
                continue
            j = i
            info = None
            while j > 0 and i - j < 400:
                cand = ptrs[j - 1]
                if not _in(data_r, cand):
                    break
                info = _col_class(img, cand, data_r)      # the COL may sit in .text too (merged .rdata)
                if info is not None or not _in(code_r, cand):
                    break
                j -= 1
            if info is None:
                continue
            candidates.setdefault(func_to_map[v], []).append((base + j * P, info[0], info[1], info[2]))
    rtti_bases = {}
    for mva, cands in candidates.items():
        vt, name, _nb, bases = min(cands, key=lambda c: (c[2], c[1]))
        by_ptr[mva].class_name = name
        by_ptr[mva].vtable_va = vt
        rtti_bases[mva] = bases
    # 3) base maps without a vtable of their own (inlined constructors): name them from a derived class's
    #    RTTI base class list (the nearest base that has no map name yet)
    used = {m.class_name for m in maps if m.class_name}
    for mva, bases in rtti_bases.items():
        m, rest = by_ptr[mva], list(bases[1:])
        while m.base_map_va in by_ptr and rest:
            bm = by_ptr[m.base_map_va]
            if bm.class_name:
                if bm.class_name in rest:
                    rest = rest[rest.index(bm.class_name) + 1:]
                m = bm
                continue
            pick = next((n for n in rest if n not in used), None)
            if pick is None:
                break
            bm.class_name = pick
            bm.name_guessed = True
            used.add(pick)
            rest = rest[rest.index(pick) + 1:]
            m = bm


# ============================================================================ helpers
def chain(maps: list[MsgMap], m: MsgMap) -> list[MsgMap]:
    """*m* followed by its base classes' maps."""
    by = {x.va: x for x in maps}
    out, seen = [], set()
    while m is not None and m.va not in seen:
        out.append(m)
        seen.add(m.va)
        m = by.get(m.base_map_va)
    return out


def handlers_for_control(maps: list[MsgMap], ctrl_id: int, owner: MsgMap | None = None) -> list[tuple[MsgMap, MsgEntry]]:
    pool = chain(maps, owner) if owner is not None else maps
    return [(m, e) for m in pool for e in m.entries if e.matches_control(ctrl_id)]


def handlers_for_command(maps: list[MsgMap], cmd_id: int) -> list[tuple[MsgMap, MsgEntry]]:
    return [(m, e) for m in maps for e in m.entries if e.msg == WM_COMMAND and e.id <= cmd_id <= e.last_id]


def guess_dialog_owner(maps: list[MsgMap], control_ids: set[int]) -> MsgMap | None:
    """The map whose control-id handlers overlap the dialog's controls most (IDOK / IDCANCEL ignored)."""
    ids = {c for c in control_ids if c not in (-1, 0xFFFF, 1, 2)}
    best, score = None, 0
    for m in maps:
        s = len(ids & m.control_ids())
        if s > score:
            best, score = m, s
    return best


def command_signature(maps: list[MsgMap]) -> int:
    """nSig MFC uses for 'void handler()' commands in this program (AfxSigCmd_v differs between versions)."""
    c = Counter(e.sig for m in maps for e in m.entries
                if e.msg == WM_COMMAND and e.code == 0 and e.id == e.last_id and e.sig < 0x400)
    if c:
        return c.most_common(1)[0][0]
    c = Counter(e.sig for m in maps for e in m.entries if e.msg in (0x0010, 0x0002, 0x000F) and e.sig < 0x400)
    if c:
        return c.most_common(1)[0][0]
    return 0x13                               # AfxSig_vv of MFC 7 and later


def pack_entry(img: PEImage, msg: int, code: int, cid: int, last: int, sig: int, pfn: int) -> bytes:
    return struct.pack("<IIII" + ("QQ" if img.is64 else "II"), msg & 0xFFFFFFFF, code & 0xFFFFFFFF,
                       cid & 0xFFFF, last & 0xFFFF, sig, pfn)


def pointer_slots(img: PEImage, entries_va: int, values: list[tuple]) -> list[int]:
    """RVAs of the pointer fields (pfn, and nSig of registered messages) of a packed entry list."""
    E = entry_size(img)
    P = img.ptr_size
    out = []
    for i, (msg, _c, _i, _l, _s, pfn) in enumerate(values):
        if pfn:
            out.append(entries_va + i * E + 16 + P - img.image_base)
        if msg == WM_REGISTERED:
            out.append(entries_va + i * E + 16 - img.image_base)
    return out
