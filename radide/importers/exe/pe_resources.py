"""Windows PE resources -> RAD IDE forms (docs/CONTRACTS.md 10.3).

Reads DIALOG / DIALOGEX templates (-> neutral .form with dialog units converted to pixels),
MENU / MENUEX (-> MenuStrip items), STRINGTABLE, VERSIONINFO, icons (-> .ico files) and the manifest.

    res = read_resources(path)          # PEResources
    form_dict, ids = dialog_to_form(res.dialogs[0], res, "frmMain")
    result = run(path, info, workdir, progress, ai_translate=False)   # backend interface (10.4)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from .base import ImportResult, safe_name

RT_ICON, RT_MENU, RT_DIALOG, RT_STRING, RT_RCDATA, RT_GROUP_ICON, RT_VERSION, RT_MANIFEST = 3, 4, 5, 6, 10, 14, 16, 24

# window / control styles
WS_CHILD, WS_VISIBLE, WS_DISABLED, WS_THICKFRAME = 0x40000000, 0x10000000, 0x08000000, 0x00040000
WS_BORDER, WS_VSCROLL, WS_HSCROLL = 0x00800000, 0x00200000, 0x00100000
DS_SETFONT, DS_CENTER = 0x40, 0x800
ES_CENTER, ES_RIGHT, ES_MULTILINE, ES_PASSWORD, ES_READONLY = 0x1, 0x2, 0x4, 0x20, 0x800
SS_TYPEMASK = 0x1F
ATOMS = {0x80: "Button", 0x81: "Edit", 0x82: "Static", 0x83: "ListBox", 0x84: "ScrollBar", 0x85: "ComboBox"}

PREFIX = {"Button": "btn", "Label": "lbl", "TextBox": "txt", "CheckBox": "chk", "RadioButton": "opt",
          "ListBox": "lst", "ComboBox": "cbo", "GroupBox": "grp", "PictureBox": "pic", "ProgressBar": "prg",
          "TrackBar": "trk", "ListView": "lvw", "TreeView": "tvw", "TabControl": "tab", "DateTimePicker": "dtp",
          "LinkLabel": "lnk", "StatusBar": "sta", "NumericUpDown": "nud", "Panel": "pnl"}
# standard dialog command ids
STD_IDS = {1: "OK", 2: "Cancel", 3: "Abort", 4: "Retry", 5: "Ignore", 6: "Yes", 7: "No", 8: "Close", 9: "Help"}


# ============================================================================ data
@dataclass
class DlgItem:
    cls: str            # "Button", "Edit", "Static", ... or a window class name
    text: str           # caption, or "#<ordinal>" for an icon/bitmap ordinal
    id: int
    style: int
    exstyle: int
    x: int
    y: int
    cx: int
    cy: int


@dataclass
class Dialog:
    id: int | str
    style: int
    exstyle: int
    x: int
    y: int
    cx: int
    cy: int
    menu: int | str | None
    wclass: int | str | None
    title: str
    font_size: int = 0
    font_name: str = ""
    items: list = field(default_factory=list)
    extended: bool = False

    def base_units(self) -> tuple[float, float]:
        """Average character width/height of the dialog font at 96 DPI (GetDialogBaseUnits)."""
        if not (self.style & DS_SETFONT) or not self.font_size:
            return 8.0, 16.0                       # system font
        pt = max(6, min(int(self.font_size), 36))
        if "segoe" in self.font_name.lower():
            return round(pt * 0.78), round(pt * 1.667)   # Segoe UI 9 -> 7 x 15
        return round(pt * 0.75), round(pt * 1.6)          # MS Shell Dlg 8 -> 6 x 13

    def px(self, x: int, y: int) -> tuple[int, int]:
        bx, by = self.base_units()
        return int(round(x * bx / 4)), int(round(y * by / 8))


@dataclass
class PEResources:
    dialogs: list = field(default_factory=list)      # [Dialog]
    menus: dict = field(default_factory=dict)        # id -> [items]   (MenuStrip format, with "Id")
    strings: dict = field(default_factory=dict)      # id -> text
    version: dict = field(default_factory=dict)      # CompanyName, ProductName, FileVersion, ...
    icons: list = field(default_factory=list)        # [(name, ico bytes)]
    manifest: str = ""
    rcdata: dict = field(default_factory=dict)       # name -> bytes (small ones only)
    bitmaps: list = field(default_factory=list)      # [id]
    accelerators: int = 0


# ============================================================================ low-level readers
class _Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.p = 0

    def u16(self) -> int:
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def i16(self) -> int:
        v = struct.unpack_from("<h", self.d, self.p)[0]
        self.p += 2
        return v

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def u8(self) -> int:
        v = self.d[self.p]
        self.p += 1
        return v

    def wstr(self) -> str:
        end = self.p
        while end + 1 < len(self.d) and self.d[end:end + 2] != b"\x00\x00":
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
            return self.u16()
        return self.wstr()

    def align(self, n: int = 4) -> None:
        self.p = (self.p + n - 1) & ~(n - 1)


def parse_dialog(data: bytes, res_id) -> Dialog:
    r = _Reader(data)
    ext = len(data) >= 4 and struct.unpack_from("<HH", data, 0) == (1, 0xFFFF)
    if ext:
        r.u16(), r.u16()
        r.u32()                      # helpID
        exstyle, style = r.u32(), r.u32()
    else:
        style, exstyle = r.u32(), r.u32()
    count = r.u16()
    x, y, cx, cy = r.i16(), r.i16(), r.i16(), r.i16()
    menu, wclass, title = r.sz_or_ord(), r.sz_or_ord(), r.wstr()
    dlg = Dialog(res_id, style, exstyle, x, y, cx, cy, menu, wclass, title, extended=ext)
    if style & DS_SETFONT:
        dlg.font_size = r.u16()
        if ext:
            r.u16(), r.u8(), r.u8()          # weight, italic, charset
        dlg.font_name = r.wstr()
    for _ in range(count):
        r.align(4)
        if r.p + 18 > len(data):
            break
        if ext:
            r.u32()                          # helpID
            iex, ist = r.u32(), r.u32()
        else:
            ist, iex = r.u32(), r.u32()
        ix, iy, icx, icy = r.i16(), r.i16(), r.i16(), r.i16()
        iid = r.u32() if ext else r.u16()
        cls = r.sz_or_ord()
        text = r.sz_or_ord()
        extra = r.u16() if r.p + 2 <= len(data) else 0
        r.p += extra
        cls_name = ATOMS.get(cls, f"#{cls}") if isinstance(cls, int) else (cls or "")
        txt = f"#{text}" if isinstance(text, int) else (text or "")
        if iid in (0xFFFF, 0xFFFFFFFF):
            iid = -1
        dlg.items.append(DlgItem(cls_name, txt, iid, ist, iex, ix, iy, icx, icy))
    return dlg


def parse_menu(data: bytes) -> list:
    """MENU / MENUEX resource -> [{"Text", "Name"?, "Id", "Items"?}] (names are filled later)."""
    r = _Reader(data)
    version = r.u16()
    if version == 1:                     # MENUEX
        offset = r.u16()
        r.p += offset

        def level_ex():
            items = []
            while r.p + 14 <= len(data):
                mtype, mid = r.u32(), (r.u32(), r.u32())[1]
                flags = r.u16()
                text = r.wstr()
                r.align(4)
                if mtype & 0x800:
                    item = {"Text": "-"}
                else:
                    item = {"Text": text, "Id": mid}
                if flags & 0x01:
                    r.u32()              # helpID
                    item["Items"] = level_ex()
                items.append(item)
                if flags & 0x80:
                    break
            return items
        return level_ex()
    r.u16()                              # header size

    def level():
        items = []
        while r.p + 4 <= len(data):
            opt = r.u16()
            if opt & 0x10:               # MF_POPUP
                text = r.wstr()
                item = {"Text": text, "Items": level()}
            else:
                mid = r.u16()
                text = r.wstr()
                item = {"Text": "-"} if (mid == 0 and not text) or opt & 0x800 else {"Text": text, "Id": mid}
            items.append(item)
            if opt & 0x80:               # MF_END
                break
        return items
    return level()


def parse_string_block(data: bytes, block_id: int) -> dict:
    out, r = {}, _Reader(data)
    for i in range(16):
        if r.p + 2 > len(data):
            break
        n = r.u16()
        if n:
            out[(block_id - 1) * 16 + i] = data[r.p:r.p + n * 2].decode("utf-16-le", "replace")
            r.p += n * 2
    return out


# ============================================================================ read everything
def _entry_id(entry):
    if entry.name is not None:
        return str(entry.name)
    return entry.struct.Id


def _data(pe, leaf) -> bytes:
    ds = leaf.data.struct
    return pe.get_data(ds.OffsetToData, ds.Size)


def _leaves(pe, type_id):
    """(resource id, data bytes) for every language leaf of a resource type."""
    root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    if root is None:
        return
    for t in root.entries:
        if t.struct.Id != type_id or t.name is not None:
            continue
        for e in getattr(t, "directory", None).entries if hasattr(t, "directory") else []:
            rid = _entry_id(e)
            langs = getattr(e, "directory", None)
            if langs is None:
                continue
            for lang in langs.entries[:1]:      # first language only
                try:
                    yield rid, _data(pe, lang)
                except Exception:  # noqa: BLE001
                    continue


def read_resources(path) -> PEResources:
    import pefile
    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        return read_from_pe(pe)
    finally:
        pe.close()


def read_from_pe(pe) -> PEResources:
    res = PEResources()
    for rid, data in _leaves(pe, RT_DIALOG):
        try:
            res.dialogs.append(parse_dialog(data, rid))
        except Exception:  # noqa: BLE001 - a broken template is skipped
            continue
    for rid, data in _leaves(pe, RT_MENU):
        try:
            res.menus[rid] = parse_menu(data)
        except Exception:  # noqa: BLE001
            continue
    for rid, data in _leaves(pe, RT_STRING):
        if isinstance(rid, int):
            res.strings.update(parse_string_block(data, rid))
    for _rid, data in _leaves(pe, RT_MANIFEST):
        res.manifest = data.decode("utf-8", "replace")
        break
    for rid, data in _leaves(pe, RT_RCDATA):
        if len(data) <= 4 * 1024 * 1024:
            res.rcdata[str(rid)] = data
    res.bitmaps = [rid for rid, _ in _leaves(pe, 2)]
    res.accelerators = sum(1 for _ in _leaves(pe, 9))
    # icons: group -> .ico file
    icons = {rid: data for rid, data in _leaves(pe, RT_ICON)}
    for gid, data in _leaves(pe, RT_GROUP_ICON):
        try:
            res.icons.append((f"icon_{gid}", _build_ico(data, icons)))
        except Exception:  # noqa: BLE001
            continue
    # version info
    try:
        import pefile
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        for fi in getattr(pe, "FileInfo", None) or []:
            for entry in fi:
                for st in getattr(entry, "StringTable", None) or []:
                    for k, v in st.entries.items():
                        k = k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)
                        v = v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
                        if v.strip():
                            res.version[k] = v.strip()
    except Exception:  # noqa: BLE001
        pass
    return res


def _build_ico(group: bytes, icons: dict) -> bytes:
    _res, typ, count = struct.unpack_from("<HHH", group, 0)
    entries = []
    for i in range(count):
        w, h, colors, _r, planes, bits, size, iid = struct.unpack_from("<BBBBHHIH", group, 6 + i * 14)
        img = icons.get(iid)
        if img is None:
            continue
        entries.append((w, h, colors, planes, bits, img))
    out = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    blob = b""
    for w, h, colors, planes, bits, img in entries:
        out += struct.pack("<BBBBHHII", w, h, colors, 0, planes, bits, len(img), offset + len(blob))
        blob += img
    if not entries:
        raise ValueError("empty icon group")
    return out + blob


# ============================================================================ dialog -> form
def _ctrl_type(item: DlgItem) -> tuple[str | None, dict, str]:
    """(neutral type or None to skip, extra props, note)."""
    cls = item.cls.lower()
    st = item.style
    props: dict = {}
    if cls == "button":
        kind = st & 0x0F
        if kind in (2, 3, 5, 6):
            return "CheckBox", props, ""
        if kind in (4, 9):
            return "RadioButton", props, ""
        if kind == 7:
            return "GroupBox", props, ""
        return "Button", props, ("owner-drawn button" if kind == 11 else "")
    if cls == "edit" or cls.startswith("richedit") or cls == "sysipaddress32":
        if st & ES_MULTILINE or cls.startswith("richedit"):
            props["Multiline"] = True
        if st & ES_PASSWORD:
            props["PasswordChar"] = "*"
        if st & ES_READONLY:
            props["ReadOnly"] = True
        return "TextBox", props, ("rich edit -> multiline TextBox" if cls.startswith("richedit") else "")
    if cls == "static":
        t = st & SS_TYPEMASK
        if t in (3, 0x0E):              # SS_ICON / SS_BITMAP
            return "PictureBox", props, ""
        if t in (4, 5, 6, 7, 8, 9):     # black/gray/white rect + frames
            return "Panel", props, "static rectangle/frame -> Panel"
        if t in (0x10, 0x11, 0x12):     # etched frames / lines
            return ("Panel", props, "etched line -> Panel") if item.cx > 2 and item.cy > 2 else (None, props, "")
        props["TextAlign"] = {1: "Center", 2: "Right"}.get(t, "Left")
        return "Label", props, ""
    if cls == "listbox":
        return "ListBox", props, ""
    if cls in ("combobox", "comboboxex32"):
        props["DropDownStyle"] = "DropDownList" if (st & 0x3) == 3 else "DropDown"
        return "ComboBox", props, ""
    if cls == "scrollbar":
        return None, props, "scroll bar skipped"
    table = {"msctls_progress32": "ProgressBar", "msctls_trackbar32": "TrackBar",
             "syslistview32": "ListView", "systreeview32": "TreeView", "systabcontrol32": "TabControl",
             "sysdatetimepick32": "DateTimePicker", "sysmonthcal32": "DateTimePicker", "syslink": "LinkLabel",
             "msctls_statusbar32": "StatusBar", "msctls_updown32": None, "msctls_hotkey32": "TextBox",
             "sysanimate32": "PictureBox", "toolbarwindow32": None}
    if cls in table:
        t = table[cls]
        return t, props, ("" if t else f"{item.cls} skipped (no equivalent control)")
    return "Panel", props, f"custom window class '{item.cls}' -> Panel placeholder"


def _menu_items(items: list, prefix: str, taken: set, id_map: dict) -> list:
    out = []
    for it in items:
        if it.get("Text") == "-":
            out.append({"Text": "-"})
            continue
        raw = it.get("Text", "")
        text = raw.split("\t")[0].replace("&&", "\x00").replace("&", "").replace("\x00", "&")
        base = prefix + safe_name(text, "Item")
        name, i = base, 2
        while name.lower() in taken:
            name, i = f"{base}{i}", i + 1
        taken.add(name.lower())
        d = {"Text": text, "Name": name}
        if "\t" in raw:
            d["Shortcut"] = raw.split("\t", 1)[1]
        if it.get("Items"):
            d["Items"] = _menu_items(it["Items"], name, taken, id_map)
        elif it.get("Id"):
            id_map[it["Id"]] = name
        out.append(d)
    return out


def menu_to_items(items: list, taken: set | None = None) -> tuple[list, dict]:
    """Resource menu -> (MenuStrip Items, {command id: item name})."""
    id_map: dict = {}
    return _menu_items(items, "mnu", taken if taken is not None else set(), id_map), id_map


def dialog_to_form(dlg: Dialog, res: PEResources | None, name: str, notes: list | None = None) -> tuple[dict, dict]:
    """A dialog template -> (form dict, {control id: control name, "menu": {id: item}})."""
    from ...model import Form
    notes = notes if notes is not None else []
    form = Form()
    form.props["Name"] = name
    form.props["Text"] = dlg.title or name
    w, h = dlg.px(dlg.cx, dlg.cy)
    form.props["Width"], form.props["Height"] = max(w, 80), max(h, 40)
    form.props["FormBorderStyle"] = "Sizable" if dlg.style & WS_THICKFRAME else "FixedSingle"
    form.props["StartPosition"] = "CenterScreen"
    ids: dict = {}
    taken = {name.lower()}
    prev_label = ""
    made = []                                    # (ctrl, item, abs rect)
    font = dlg.font_name if dlg.font_name and not dlg.font_name.lower().startswith("ms shell") else ""
    for item in dlg.items:
        ctype, extra, note = _ctrl_type(item)
        if note:
            notes.append(f"{name}: {note}")
        if ctype is None:
            continue
        text = item.text if not item.text.startswith("#") else ""
        clean = text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")
        if ctype in ("Button", "CheckBox", "RadioButton", "GroupBox", "LinkLabel") and clean.strip():
            stem = safe_name(clean)
        elif ctype == "Button" and item.id in STD_IDS:
            stem = STD_IDS[item.id]
        elif ctype == "Label" and clean.strip():
            stem = safe_name(clean)
        elif ctype in ("TextBox", "ComboBox", "ListBox", "NumericUpDown", "DateTimePicker", "TrackBar") and prev_label:
            stem = safe_name(prev_label)
        else:
            stem = str(item.id) if item.id >= 0 else ""
        base = PREFIX.get(ctype, ctype[:3].lower()) + (stem or "")
        cname, i = base, 2
        if not stem:
            cname, i = f"{base}1", 2
            while cname.lower() in taken:
                cname, i = f"{base}{i}", i + 1
        while cname.lower() in taken:
            cname, i = f"{base}{i}", i + 1
        taken.add(cname.lower())
        x, y = dlg.px(item.x, item.y)
        cw, ch = dlg.px(item.cx, item.cy)
        ctrl = form.add(ctype, x, y)
        ctrl.props["Name"] = cname
        if "Text" in ctrl.props:
            ctrl.props["Text"] = clean
        ctrl.props["Width"], ctrl.props["Height"] = max(cw, 4), max(ch, 4)
        if not item.style & WS_VISIBLE:
            ctrl.props["Visible"] = False
        if item.style & WS_DISABLED:
            ctrl.props["Enabled"] = False
        if font and "FontName" in ctrl.props:
            ctrl.props["FontName"] = font
        for k, v in extra.items():
            if k in ctrl.props:
                ctrl.props[k] = v
        if ctype == "PictureBox" and item.text.startswith("#") and (item.style & SS_TYPEMASK) == 3:
            ctrl.props["Image"] = f"icon_{item.text[1:]}.png"      # written by the wizard from the .ico
            ctrl.props["Width"], ctrl.props["Height"] = max(cw, 32), max(ch, 32)
        if item.id >= 0:
            ids[item.id] = cname
        made.append((ctrl, item, (x, y, cw, ch)))
        prev_label = clean if ctype == "Label" else ""
    # Win32 group boxes do not own controls: controls inside a group box's rectangle become its children
    groups = [(c, r) for c, _i, r in made if c.type == "GroupBox"]
    for ctrl, _item, (x, y, cw, ch) in made:
        if ctrl.type == "GroupBox":
            continue
        for g, (gx, gy, gw, gh) in groups:
            if gx <= x and gy <= y and x + cw <= gx + gw and y + ch <= gy + gh:
                ctrl.props["Parent"] = g.name
                ctrl.props["Left"], ctrl.props["Top"] = x - gx, y - gy
                break
    # tab order follows the template order
    for i, (ctrl, _item, _r) in enumerate(made):
        if "TabIndex" in ctrl.props:
            ctrl.props["TabIndex"] = i
    # menu attached to the dialog
    if dlg.menu is not None and res is not None:
        items = res.menus.get(dlg.menu)
        if items is None:
            notes.append(f"{name}: menu {dlg.menu} not found in the resources")
        else:
            m = form.add("MenuStrip", 0, 0)
            m.props["Items"], ids["menu"] = menu_to_items(items, taken)
    return form.to_dict(), ids


def form_with_menu(items: list, name: str, title: str, width: int = 640, height: int = 420) -> tuple[dict, dict]:
    """A main window form that only has a menu (programs that build their window in code)."""
    from ...model import Form
    form = Form()
    form.props.update(Name=name, Text=title or name, Width=width, Height=height)
    m = form.add("MenuStrip", 0, 0)
    m.props["Items"], idmap = menu_to_items(items, {name.lower()})
    return form.to_dict(), {"menu": idmap}


# ============================================================================ backend interface
def form_name_for(dlg: Dialog, used: set) -> str:
    base = "frm" + safe_name(dlg.title, f"Dialog{dlg.id}")
    name, i = base, 2
    while name.lower() in used:
        name, i = f"{base}{i}", i + 1
    used.add(name.lower())
    return name


def forms_from_resources(res: PEResources, result: ImportResult, product: str = "") -> dict:
    """Add one form per dialog (+ a main window for menus no dialog uses) to *result*.
    Returns {"dialogs": {form: {"id": dialog id, "controls": {...}}}, "menus": {form: {cmd id: item}}}."""
    used: set = set()
    maps = {"dialogs": {}, "menus": {}}
    used_menus = set()
    for dlg in res.dialogs:
        name = form_name_for(dlg, used)
        notes: list = []
        fd, ids = dialog_to_form(dlg, res, name, notes)
        menu_ids = ids.pop("menu", {})
        if dlg.menu is not None:
            used_menus.add(dlg.menu)
        result.forms.append((name, fd))
        maps["dialogs"][name] = {"id": dlg.id, "controls": ids, "title": dlg.title}
        if menu_ids:
            maps["menus"][name] = menu_ids
        n = len(fd["controls"])
        result.add("exact", f"Form {name}: dialog {dlg.id} '{dlg.title}' with {n} control(s) "
                            f"({'DIALOGEX' if dlg.extended else 'DIALOG'}, font {dlg.font_name or 'system'} "
                            f"{dlg.font_size or ''}, dialog units converted to pixels)")
        for note in dict.fromkeys(notes):
            result.add("warn", note)
    for mid, items in res.menus.items():
        if mid in used_menus:
            continue
        name = "frmMain" if "frmmain" not in used else f"frmMenu{mid}"
        used.add(name.lower())
        fd, ids = form_with_menu(items, name, product or "Main window")
        result.forms.append((name, fd))
        maps["menus"][name] = ids.get("menu", {})
        result.add("exact", f"Form {name}: menu resource {mid} (the program creates its main window in code; "
                            "only the menu bar could be recovered)")
    return maps


def can_handle(info) -> bool:
    types = set(info.details.get("resource_types") or [])
    return bool({"DIALOG", "MENU"} & types)


def run(path, info, workdir, progress, ai_translate: bool = False) -> ImportResult:
    """Resources only: forms from dialogs/menus + strings/version/icons."""
    result = ImportResult()
    progress = progress or (lambda _s: None)
    progress("Reading PE resources (dialogs, menus, strings, icons) ...")
    try:
        res = read_resources(path)
    except Exception as e:  # noqa: BLE001
        result.add("error", f"Cannot read resources: {e}")
        return result
    fill_result(res, result, info)
    return result


def fill_result(res: PEResources, result: ImportResult, info=None) -> dict:
    product = res.version.get("ProductName") or (Path(info.path).stem if info is not None and info.path else "")
    maps = forms_from_resources(res, result, product)
    result.resources.update({
        "strings": res.strings, "version": res.version, "icons": res.icons, "manifest": res.manifest,
        "dialog_ids": maps["dialogs"], "menu_ids": maps["menus"],
        "rcdata_names": sorted(res.rcdata),
    })
    if res.strings:
        result.add("exact", f"{len(res.strings)} string(s) from the STRINGTABLE (kept in strings.py / the report)")
    if res.version:
        result.add("exact", "Version information: " + ", ".join(f"{k}={v}" for k, v in list(res.version.items())[:6]))
    if res.icons:
        result.add("exact", f"{len(res.icons)} icon(s) extracted (.ico)")
    if res.bitmaps:
        result.add("missing", f"{len(res.bitmaps)} bitmap resource(s) not converted")
    if res.accelerators:
        result.add("info", "Keyboard accelerator table found (shortcuts are shown in the menu texts)")
    if not res.dialogs and not res.menus:
        result.add("missing", "No DIALOG or MENU resources: the window layout is created in code and cannot be "
                              "recovered from resources")
    return maps
