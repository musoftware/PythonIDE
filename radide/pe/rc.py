"""Resources <-> .rc script + resource files.

    export_rc(entries, folder, "app")      # app.rc + res/*.ico/.bmp/.cur/.bin (numeric ids and styles)
    entries = import_rc("app.rc")          # parses the script (and the files it names) back

The importer understands what the exporter writes and the common hand-written statements: DIALOG / DIALOGEX
(CONTROL and the LTEXT / PUSHBUTTON / EDITTEXT ... shortcuts), MENU / MENUEX, STRINGTABLE, ACCELERATORS,
VERSIONINFO, ICON / CURSOR / BITMAP / RCDATA / user types from files, small inline data blocks, LANGUAGE,
#define (also from #include "local.h") and the usual Windows style constants.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from . import resources as R

# ============================================================================ export
def _q(s: str) -> str:
    return '"' + s.replace('"', '""').replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t") + '"'


def _name(n) -> str:
    return _q(n) if isinstance(n, str) else str(n)


def _cls(c) -> str:
    if isinstance(c, int):
        return _q(R.ATOMS.get(c, f"#{c}"))
    return _q(c)


def _text(t) -> str:
    if isinstance(t, int):
        return str(t)
    return _q(t or "")


def _dialog_rc(name, d: R.Dialog) -> list[str]:
    out = [f"{_name(name)} {'DIALOGEX' if d.extended else 'DIALOG'} {d.x}, {d.y}, {d.cx}, {d.cy}"
           + (f", {d.help_id}" if d.extended and d.help_id else "")]
    out.append(f"STYLE 0x{d.style:08X}")
    if d.exstyle:
        out.append(f"EXSTYLE 0x{d.exstyle:08X}")
    if d.title:
        out.append(f"CAPTION {_q(d.title)}")
    if d.menu is not None:
        out.append(f"MENU {_name(d.menu)}")
    if d.wclass is not None:
        out.append(f"CLASS {_name(d.wclass)}")
    if d.has_font:
        f = f"FONT {d.font_size}, {_q(d.font_name)}"
        if d.extended:
            f += f", {d.font_weight}, {d.italic}, 0x{d.charset:X}"
        out.append(f)
    out.append("BEGIN")
    for c in d.controls:
        line = (f"    CONTROL {_text(c.text)}, {c.id}, {_cls(c.cls)}, 0x{c.style:08X}, {c.x}, {c.y}, {c.cx}, {c.cy}")
        if c.exstyle or c.help_id:
            line += f", 0x{c.exstyle:08X}"
        if d.extended and c.help_id:
            line += f", {c.help_id}"
        out.append(line)
    out.append("END")
    return out


def _menu_rc(name, m: R.Menu) -> list[str]:
    out = [f"{_name(name)} {'MENUEX' if m.extended else 'MENU'}", "BEGIN"]

    def level(items, ind):
        pad = "    " * ind
        for it in items:
            if it.is_popup:
                if m.extended:
                    out.append(f"{pad}POPUP {_q(it.text)}, {it.id}, 0x{it.flags:X}, 0x{it.state:X}, {it.help_id}")
                else:
                    out.append(f"{pad}POPUP {_q(it.text)}" + _menu_flags(it.flags))
                out.append(pad + "BEGIN")
                level(it.children or [], ind + 1)
                out.append(pad + "END")
            elif m.extended:
                out.append(f"{pad}MENUITEM {_q(it.text)}, {it.id}, 0x{it.flags:X}, 0x{it.state:X}")
            elif it.is_separator and not it.flags & ~R.MFT_SEPARATOR:
                out.append(f"{pad}MENUITEM SEPARATOR")
            else:
                out.append(f"{pad}MENUITEM {_q(it.text)}, {it.id}" + _menu_flags(it.flags))
    level(m.items, 1)
    out.append("END")
    return out


_MENU_OPTS = [(R.MF_GRAYED, "GRAYED"), (R.MF_DISABLED, "INACTIVE"), (R.MF_CHECKED, "CHECKED"),
              (R.MF_MENUBARBREAK, "MENUBARBREAK"), (R.MF_MENUBREAK, "MENUBREAK"), (R.MF_HELP, "HELP")]


def _menu_flags(flags: int) -> str:
    opts = [n for bit, n in _MENU_OPTS if flags & bit]
    return (", " + ", ".join(opts)) if opts else ""


def _accel_rc(name, items: list[R.Accel]) -> list[str]:
    out = [f"{_name(name)} ACCELERATORS", "BEGIN"]
    for a in items:
        key = str(a.key) if a.flags & R.FVIRTKEY else _q(chr(a.key))
        opts = ["VIRTKEY" if a.flags & R.FVIRTKEY else "ASCII"]
        opts += [n for bit, n in ((R.FCONTROL, "CONTROL"), (R.FSHIFT, "SHIFT"), (R.FALT, "ALT"),
                                  (R.FNOINVERT, "NOINVERT")) if a.flags & bit]
        out.append(f"    {key}, {a.cmd}, {', '.join(opts)}")
    out.append("END")
    return out


def _version_rc(name, v: R.VersionInfo) -> list[str]:
    fv, pv = v.file_version, v.product_version
    out = [f"{_name(name)} VERSIONINFO",
           f" FILEVERSION {fv[0]},{fv[1]},{fv[2]},{fv[3]}", f" PRODUCTVERSION {pv[0]},{pv[1]},{pv[2]},{pv[3]}",
           f" FILEFLAGSMASK 0x{v.flags_mask:X}", f" FILEFLAGS 0x{v.flags:X}", f" FILEOS 0x{v.os:X}",
           f" FILETYPE 0x{v.file_type:X}", f" FILESUBTYPE 0x{v.file_subtype:X}", "BEGIN"]
    if v.strings:
        out += ['    BLOCK "StringFileInfo"', "    BEGIN"]
        for key, items in v.strings.items():
            out += [f"        BLOCK {_q(key)}", "        BEGIN"]
            out += [f"            VALUE {_q(k)}, {_q(val)}" for k, val in items.items()]
            out.append("        END")
        out.append("    END")
    if v.translations:
        out += ['    BLOCK "VarFileInfo"', "    BEGIN",
                '        VALUE "Translation", ' + ", ".join(f"0x{lg:X}, {cp}" for lg, cp in v.translations),
                "    END"]
    out.append("END")
    return out


def _fname(t, n, lang, ext) -> str:
    tn = re.sub(r"\W", "_", R.type_label(t)).lower()
    nn = re.sub(r"\W", "_", str(n))
    return f"{tn}_{nn}_{lang}{ext}"


def export_rc(entries: list[R.ResEntry], folder, base: str = "resources") -> Path:
    folder = Path(folder)
    res_dir = folder / "res"
    res_dir.mkdir(parents=True, exist_ok=True)
    lines = ["// Resources exported by RAD IDE (PE / MFC workbench). Numbers are kept as in the program.",
             "// Re-import with File > Import .rc in the workbench, or compile with rc.exe.", ""]
    icons = {e.name: e.data for e in entries if e.type == R.RT_ICON and isinstance(e.name, int)}
    cursors = {e.name: e.data for e in entries if e.type == R.RT_CURSOR and isinstance(e.name, int)}
    by_lang: dict[int, list[R.ResEntry]] = {}
    for e in entries:
        by_lang.setdefault(e.lang, []).append(e)
    for lang in sorted(by_lang):
        lines += [f"LANGUAGE 0x{lang & 0x3FF:X}, 0x{lang >> 10:X}", ""]
        strings: dict[int, str] = {}
        for e in by_lang[lang]:
            t = e.type
            try:
                if t in (R.RT_ICON, R.RT_CURSOR):
                    continue                                   # written with their groups
                if t == R.RT_DIALOG:
                    lines += _dialog_rc(e.name, R.parse_dialog(e.data))
                elif t == R.RT_MENU:
                    lines += _menu_rc(e.name, R.parse_menu(e.data))
                elif t == R.RT_STRING and isinstance(e.name, int):
                    strings.update(R.parse_string_block(e.data, e.name))
                    continue
                elif t == R.RT_ACCELERATOR:
                    lines += _accel_rc(e.name, R.parse_accel(e.data))
                elif t == R.RT_VERSION:
                    lines += _version_rc(e.name, R.parse_version(e.data))
                elif t in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR):
                    cur = t == R.RT_GROUP_CURSOR
                    fn = _fname(t, e.name, lang, ".cur" if cur else ".ico")
                    (res_dir / fn).write_bytes(R.group_to_file(e.data, cursors if cur else icons, cur))
                    lines.append(f'{_name(e.name)} {"CURSOR" if cur else "ICON"} "res/{fn}"')
                elif t == R.RT_BITMAP:
                    fn = _fname(t, e.name, lang, ".bmp")
                    (res_dir / fn).write_bytes(R.dib_to_bmp(e.data))
                    lines.append(f'{_name(e.name)} BITMAP "res/{fn}"')
                else:
                    ext = {R.RT_MANIFEST: ".manifest", R.RT_HTML: ".html"}.get(t, ".bin")
                    fn = _fname(t, e.name, lang, ext)
                    (res_dir / fn).write_bytes(e.data)
                    tt = _q(t) if isinstance(t, str) else str(t)
                    lines.append(f'{_name(e.name)} {tt} "res/{fn}"')
            except Exception:  # noqa: BLE001 - an undecodable resource is kept as a file
                fn = _fname(t, e.name, lang, ".bin")
                (res_dir / fn).write_bytes(e.data)
                lines.append(f'{_name(e.name)} {_q(t) if isinstance(t, str) else t} "res/{fn}"')
            lines.append("")
        if strings:
            lines += ["STRINGTABLE", "BEGIN"]
            lines += [f"    {sid}, {_q(txt)}" for sid, txt in sorted(strings.items())]
            lines += ["END", ""]
    path = folder / f"{base}.rc"
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return path


# ============================================================================ import
CONSTANTS = {
    "WS_OVERLAPPED": 0, "WS_POPUP": 0x80000000, "WS_CHILD": 0x40000000, "WS_MINIMIZE": 0x20000000,
    "WS_VISIBLE": 0x10000000, "WS_DISABLED": 0x08000000, "WS_CLIPSIBLINGS": 0x04000000,
    "WS_CLIPCHILDREN": 0x02000000, "WS_MAXIMIZE": 0x01000000, "WS_CAPTION": 0x00C00000, "WS_BORDER": 0x00800000,
    "WS_DLGFRAME": 0x00400000, "WS_VSCROLL": 0x00200000, "WS_HSCROLL": 0x00100000, "WS_SYSMENU": 0x00080000,
    "WS_THICKFRAME": 0x00040000, "WS_GROUP": 0x00020000, "WS_TABSTOP": 0x00010000, "WS_MINIMIZEBOX": 0x00020000,
    "WS_MAXIMIZEBOX": 0x00010000, "WS_OVERLAPPEDWINDOW": 0x00CF0000, "WS_POPUPWINDOW": 0x80880000,
    "WS_EX_DLGMODALFRAME": 0x1, "WS_EX_TOPMOST": 0x8, "WS_EX_ACCEPTFILES": 0x10, "WS_EX_TRANSPARENT": 0x20,
    "WS_EX_TOOLWINDOW": 0x80, "WS_EX_WINDOWEDGE": 0x100, "WS_EX_CLIENTEDGE": 0x200, "WS_EX_CONTEXTHELP": 0x400,
    "WS_EX_RIGHT": 0x1000, "WS_EX_RTLREADING": 0x2000, "WS_EX_STATICEDGE": 0x20000, "WS_EX_APPWINDOW": 0x40000,
    "WS_EX_LAYOUTRTL": 0x400000,
    "DS_ABSALIGN": 0x1, "DS_SYSMODAL": 0x2, "DS_LOCALEDIT": 0x20, "DS_SETFONT": 0x40, "DS_MODALFRAME": 0x80,
    "DS_NOIDLEMSG": 0x100, "DS_SETFOREGROUND": 0x200, "DS_3DLOOK": 0x4, "DS_FIXEDSYS": 0x8, "DS_NOFAILCREATE": 0x10,
    "DS_CONTROL": 0x400, "DS_CENTER": 0x800, "DS_CENTERMOUSE": 0x1000, "DS_CONTEXTHELP": 0x2000,
    "DS_SHELLFONT": 0x48,
    "BS_PUSHBUTTON": 0, "BS_DEFPUSHBUTTON": 1, "BS_CHECKBOX": 2, "BS_AUTOCHECKBOX": 3, "BS_RADIOBUTTON": 4,
    "BS_3STATE": 5, "BS_AUTO3STATE": 6, "BS_GROUPBOX": 7, "BS_AUTORADIOBUTTON": 9, "BS_OWNERDRAW": 0xB,
    "BS_LEFTTEXT": 0x20, "BS_ICON": 0x40, "BS_BITMAP": 0x80, "BS_LEFT": 0x100, "BS_RIGHT": 0x200,
    "BS_CENTER": 0x300, "BS_TOP": 0x400, "BS_BOTTOM": 0x800, "BS_VCENTER": 0xC00, "BS_PUSHLIKE": 0x1000,
    "BS_MULTILINE": 0x2000, "BS_FLAT": 0x8000,
    "ES_LEFT": 0, "ES_CENTER": 1, "ES_RIGHT": 2, "ES_MULTILINE": 4, "ES_UPPERCASE": 8, "ES_LOWERCASE": 0x10,
    "ES_PASSWORD": 0x20, "ES_AUTOVSCROLL": 0x40, "ES_AUTOHSCROLL": 0x80, "ES_NOHIDESEL": 0x100,
    "ES_READONLY": 0x800, "ES_WANTRETURN": 0x1000, "ES_NUMBER": 0x2000,
    "SS_LEFT": 0, "SS_CENTER": 1, "SS_RIGHT": 2, "SS_ICON": 3, "SS_BLACKRECT": 4, "SS_GRAYRECT": 5,
    "SS_WHITERECT": 6, "SS_BLACKFRAME": 7, "SS_GRAYFRAME": 8, "SS_WHITEFRAME": 9, "SS_SIMPLE": 0xB,
    "SS_LEFTNOWORDWRAP": 0xC, "SS_BITMAP": 0xE, "SS_ETCHEDHORZ": 0x10, "SS_ETCHEDVERT": 0x11,
    "SS_ETCHEDFRAME": 0x12, "SS_NOPREFIX": 0x80, "SS_NOTIFY": 0x100, "SS_CENTERIMAGE": 0x200,
    "SS_SUNKEN": 0x1000,
    "CBS_SIMPLE": 1, "CBS_DROPDOWN": 2, "CBS_DROPDOWNLIST": 3, "CBS_OWNERDRAWFIXED": 0x10, "CBS_AUTOHSCROLL": 0x40,
    "CBS_SORT": 0x100, "CBS_HASSTRINGS": 0x200, "CBS_NOINTEGRALHEIGHT": 0x400, "CBS_DISABLENOSCROLL": 0x800,
    "LBS_NOTIFY": 1, "LBS_SORT": 2, "LBS_NOREDRAW": 4, "LBS_MULTIPLESEL": 8, "LBS_HASSTRINGS": 0x40,
    "LBS_USETABSTOPS": 0x80, "LBS_NOINTEGRALHEIGHT": 0x100, "LBS_MULTICOLUMN": 0x200, "LBS_EXTENDEDSEL": 0x800,
    "LBS_DISABLENOSCROLL": 0x1000, "LBS_NOSEL": 0x4000, "LBS_STANDARD": 0xA00003,
    "SBS_HORZ": 0, "SBS_VERT": 1,
    "IDOK": 1, "IDCANCEL": 2, "IDABORT": 3, "IDRETRY": 4, "IDIGNORE": 5, "IDYES": 6, "IDNO": 7, "IDCLOSE": 8,
    "IDHELP": 9, "IDC_STATIC": -1, "VS_VERSION_INFO": 1,
    "LANG_NEUTRAL": 0, "SUBLANG_NEUTRAL": 0, "SUBLANG_DEFAULT": 1, "LANG_ENGLISH": 9, "SUBLANG_ENGLISH_US": 1,
    "SUBLANG_ENGLISH_UK": 2, "LANG_ARABIC": 1, "SUBLANG_ARABIC_SAUDI_ARABIA": 1, "SUBLANG_ARABIC_EGYPT": 3,
    "LANG_GERMAN": 7, "LANG_FRENCH": 0xC, "LANG_SPANISH": 0xA, "LANG_JAPANESE": 0x11, "LANG_CHINESE": 4,
    "VK_BACK": 8, "VK_TAB": 9, "VK_RETURN": 0xD, "VK_ESCAPE": 0x1B, "VK_SPACE": 0x20, "VK_PRIOR": 0x21,
    "VK_NEXT": 0x22, "VK_END": 0x23, "VK_HOME": 0x24, "VK_LEFT": 0x25, "VK_UP": 0x26, "VK_RIGHT": 0x27,
    "VK_DOWN": 0x28, "VK_INSERT": 0x2D, "VK_DELETE": 0x2E,
    **{f"VK_F{i}": 0x6F + i for i in range(1, 25)},
    "VOS_NT_WINDOWS32": 0x40004, "VOS__WINDOWS32": 4, "VFT_APP": 1, "VFT_DLL": 2, "VFT2_UNKNOWN": 0,
    "VS_FFI_FILEFLAGSMASK": 0x3F,
}

# shortcut statements: name -> (class, default style, has text)
SHORTCUTS = {
    "LTEXT": ("Static", 0x50020000, True), "RTEXT": ("Static", 0x50020002, True),
    "CTEXT": ("Static", 0x50020001, True), "PUSHBUTTON": ("Button", 0x50010000, True),
    "DEFPUSHBUTTON": ("Button", 0x50010001, True), "CHECKBOX": ("Button", 0x50010002, True),
    "AUTOCHECKBOX": ("Button", 0x50010003, True), "RADIOBUTTON": ("Button", 0x50000004, True),
    "AUTORADIOBUTTON": ("Button", 0x50000009, True), "STATE3": ("Button", 0x50010005, True),
    "AUTO3STATE": ("Button", 0x50010006, True), "GROUPBOX": ("Button", 0x50000007, True),
    "PUSHBOX": ("Button", 0x5001000A, True), "ICON": ("Static", 0x50000003, True),
    "EDITTEXT": ("Edit", 0x50810000, False), "COMBOBOX": ("ComboBox", 0x50000000, False),
    "LISTBOX": ("ListBox", 0x50800001, False), "SCROLLBAR": ("ScrollBar", 0x50000000, False),
}


class RcError(ValueError):
    pass


_TOKEN = re.compile(r'''\s*(?:(?P<str>L?"(?:[^"]|"")*")|(?P<num>0[xX][0-9a-fA-F]+[lLuU]*|\d+[lLuU]*)|
                        (?P<id>[A-Za-z_][\w.]*)|(?P<op>[,|(){}+\-~]))''', re.X)


def _unescape(s: str) -> str:
    body = s[2:-1] if s.startswith("L") else s[1:-1]
    body = body.replace('""', '"')
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            n = body[i + 1]
            if n in "nrt\\\"0a":
                out.append({"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "0": "\0", "a": "\a"}[n])
                i += 2
                continue
            if n == "x":
                m = re.match(r"[0-9a-fA-F]{1,4}", body[i + 2:])
                if m:
                    out.append(chr(int(m.group(), 16)))
                    i += 2 + len(m.group())
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


class _Tokens:
    def __init__(self, text: str):
        self.toks: list[tuple[str, str, int]] = []
        for ln_no, line in enumerate(text.splitlines(), 1):
            s = line.split("//")[0] if '"' not in line else _strip_comment(line)
            pos = 0
            while pos < len(s):
                m = _TOKEN.match(s, pos)
                if not m or m.end() == pos:
                    if s[pos:].strip() == "":
                        break
                    raise RcError(f"line {ln_no}: cannot read '{s[pos:].strip()[:30]}'")
                kind = m.lastgroup
                self.toks.append((kind, m.group(kind), ln_no))
                pos = m.end()
        self.i = 0

    def peek(self, k: int = 0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else ("eof", "", 0)

    def next(self):
        t = self.peek()
        self.i += 1
        return t

    def accept(self, value: str) -> bool:
        if self.peek()[1].upper() == value.upper() and self.peek()[0] in ("id", "op"):
            self.i += 1
            return True
        return False

    def expect(self, value: str) -> None:
        if not self.accept(value):
            k, v, ln = self.peek()
            raise RcError(f"line {ln}: expected {value}, found '{v}'")


def _strip_comment(line: str) -> str:
    inq = False
    for i, ch in enumerate(line):
        if ch == '"':
            inq = not inq
        elif not inq and line.startswith("//", i):
            return line[:i]
    return line


def _preprocess(text: str, folder: Path, symbols: dict, depth: int = 0) -> str:
    out = []
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    skip = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            d = s[1:].strip()
            if d.startswith(("ifdef", "ifndef", "if ", "if(")):
                skip.append(False)
            elif d.startswith("endif") and skip:
                skip.pop()
            elif d.startswith("define"):
                parts = d.split(None, 2)
                if len(parts) == 3:
                    try:
                        symbols[parts[1]] = _eval_text(parts[2].split("//")[0].strip(), symbols)
                    except RcError:
                        pass
            elif d.startswith("include") and depth < 4:
                m = re.search(r'"([^"]+)"', d)
                if m and (folder / m.group(1)).is_file():
                    _preprocess((folder / m.group(1)).read_text(encoding="utf-8", errors="replace"), folder,
                                symbols, depth + 1)
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def _eval_text(text: str, symbols: dict) -> int:
    t = _Tokens(text)
    return _expr(t, symbols)


def _atom(t: _Tokens, symbols: dict) -> int:
    k, v, ln = t.next()
    if k == "num":
        return int(v.rstrip("lLuU"), 0)
    if k == "op" and v == "(":
        x = _expr(t, symbols)
        t.expect(")")
        return x
    if k == "op" and v == "-":
        return -_atom(t, symbols)
    if k == "op" and v == "~":
        return ~_atom(t, symbols)
    if k == "id":
        if v.upper() == "NOT":
            return ~_atom(t, symbols)
        if v in symbols:
            return symbols[v]
        if v in CONSTANTS:
            return CONSTANTS[v]
        raise RcError(f"line {ln}: unknown name '{v}' (add a #define for it)")
    raise RcError(f"line {ln}: expected a number, found '{v}'")


def _expr(t: _Tokens, symbols: dict) -> int:
    v = _atom(t, symbols)
    while t.peek()[0] == "op" and t.peek()[1] in ("|", "+", "-"):
        op = t.next()[1]
        rhs = _atom(t, symbols)
        v = v | rhs if op == "|" else v + rhs if op == "+" else v - rhs
    return v


def _style_expr(t: _Tokens, symbols: dict, base: int = 0) -> int:
    """rc style expressions: a | b | NOT c (NOT clears bits)."""
    v = base
    first = True
    while True:
        if t.peek()[1].upper() == "NOT":
            t.next()
            v &= ~_atom(t, symbols)
        else:
            x = _atom(t, symbols)
            v = x if first and base == 0 else v | x
        first = False
        if t.peek()[1] == "|":
            t.next()
            continue
        if t.peek()[1] in ("+", "-"):
            op = t.next()[1]
            x = _atom(t, symbols)
            v = v + x if op == "+" else v - x
            continue
        return v & 0xFFFFFFFF


def _num_or_name(t: _Tokens, symbols: dict):
    k, v, ln = t.peek()
    if k == "str":
        t.next()
        return _unescape(v)
    if k == "id" and v not in symbols and v not in CONSTANTS:
        t.next()
        return v.upper()                                    # named resource (rc stores names uppercase)
    return _expr(t, symbols)


def _string(t: _Tokens) -> str:
    k, v, ln = t.next()
    if k != "str":
        raise RcError(f"line {ln}: expected a string, found '{v}'")
    return _unescape(v)


def _comma(t: _Tokens) -> bool:
    return t.accept(",")


def _begin(t: _Tokens) -> None:
    if not (t.accept("BEGIN") or t.accept("{")):
        k, v, ln = t.peek()
        raise RcError(f"line {ln}: expected BEGIN, found '{v}'")


def _end(t: _Tokens) -> bool:
    return t.accept("END") or t.accept("}")


def _at_end(t: _Tokens) -> bool:
    return t.peek()[1].upper() in ("END", "}")


def import_rc(path, text: str | None = None) -> list[R.ResEntry]:
    path = Path(path)
    folder = path.parent
    symbols: dict[str, int] = {}
    src = text if text is not None else path.read_text(encoding="utf-8-sig", errors="replace")
    t = _Tokens(_preprocess(src, folder, symbols))
    entries: list[R.ResEntry] = []
    lang = 0x409
    strings: dict[int, dict[int, str]] = {}
    icon_next = {R.RT_ICON: 1, R.RT_CURSOR: 1}

    def add(rtype, name, data):
        entries.append(R.ResEntry(rtype, name, lang, bytes(data)))

    def read_file(name: str) -> bytes:
        p = (folder / name)
        if not p.is_file():
            raise RcError(f"file not found: {name}")
        return p.read_bytes()

    while t.peek()[0] != "eof":
        k, v, ln = t.peek()
        u = v.upper()
        if k == "id" and u == "LANGUAGE":
            t.next()
            p = _expr(t, symbols)
            _comma(t)
            s = _expr(t, symbols)
            lang = (s << 10) | p
            continue
        if k == "id" and u == "STRINGTABLE":
            t.next()
            while t.peek()[1].upper() not in ("BEGIN", "{"):
                t.next()
            _begin(t)
            while not _end(t):
                sid = _expr(t, symbols)
                _comma(t)
                strings.setdefault(lang, {})[sid] = _string(t)
            continue
        name = _num_or_name(t, symbols)
        k2, typ, ln2 = t.next()
        ut = typ.upper()
        if k2 == "id" and ut in ("DIALOG", "DIALOGEX"):
            add(R.RT_DIALOG, name, R.build_dialog(_parse_dialog(t, symbols, ut == "DIALOGEX")))
        elif k2 == "id" and ut in ("MENU", "MENUEX"):
            add(R.RT_MENU, name, R.build_menu(_parse_menu(t, symbols, ut == "MENUEX")))
        elif k2 == "id" and ut == "ACCELERATORS":
            add(R.RT_ACCELERATOR, name, R.build_accel(_parse_accel(t, symbols)))
        elif k2 == "id" and ut == "VERSIONINFO":
            add(R.RT_VERSION, name, R.build_version(_parse_version(t, symbols)))
        elif k2 == "id" and ut in ("ICON", "CURSOR"):
            fn = _string(t)
            cur = ut == "CURSOR"
            img_type = R.RT_CURSOR if cur else R.RT_ICON
            used = [e.name for e in entries if e.type == img_type and isinstance(e.name, int)]
            first = max([icon_next[img_type] - 1] + used) + 1
            group, images = R.file_to_group(read_file(fn), first, cur)
            for rid, data in images.items():
                add(img_type, rid, data)
            icon_next[img_type] = first + len(images)
            add(R.RT_GROUP_CURSOR if cur else R.RT_GROUP_ICON, name, group)
        elif k2 == "id" and ut == "BITMAP":
            add(R.RT_BITMAP, name, R.bmp_to_dib(read_file(_string(t))))
        elif k2 == "id" and ut == "TOOLBAR":
            w = _expr(t, symbols)
            _comma(t)
            h = _expr(t, symbols)
            _begin(t)
            ids = []
            while not _end(t):
                kw = t.next()[1].upper()
                ids.append(_expr(t, symbols) if kw == "BUTTON" else 0)
            add(R.RT_TOOLBAR, name, R.build_toolbar(R.Toolbar(w, h, ids)))
        else:
            # RCDATA, a user type (number or name) or a known keyword with a file / data block
            if k2 == "num":
                rtype = int(typ.rstrip("lLuU"), 0)
            elif k2 == "str":
                rtype = _unescape(typ).upper()
            elif ut in ("RCDATA",):
                rtype = R.RT_RCDATA
            elif ut == "DLGINIT":
                rtype = R.RT_DLGINIT
            elif ut == "HTML":
                rtype = R.RT_HTML
            elif ut == "MESSAGETABLE":
                rtype = R.RT_MESSAGETABLE
            elif ut == "FONT":
                rtype = R.RT_FONT
            elif typ in symbols:
                rtype = symbols[typ]
            else:
                rtype = typ.upper()
            while t.peek()[0] == "id" and t.peek()[1].upper() in ("PRELOAD", "LOADONCALL", "MOVEABLE",
                                                                  "DISCARDABLE", "PURE", "IMPURE", "FIXED"):
                t.next()
            if t.peek()[0] == "str":
                add(rtype, name, read_file(_string(t)))
            else:
                add(rtype, name, _parse_data_block(t, symbols))
    for lg, items in strings.items():
        for bid, data in sorted(R.build_string_blocks(items).items()):
            entries.append(R.ResEntry(R.RT_STRING, bid, lg, data))
    return entries


def _parse_data_block(t: _Tokens, symbols: dict) -> bytes:
    _begin(t)
    out = bytearray()
    while not _end(t):
        k, v, ln = t.peek()
        if k == "str":
            t.next()
            s = _unescape(v)
            out += s.encode("utf-16-le") if v.startswith("L") else s.encode("latin-1", "replace")
        elif k == "op" and v == ",":
            t.next()
        else:
            raw = v
            n = _expr(t, symbols)
            out += struct.pack("<I", n & 0xFFFFFFFF) if raw.upper().endswith("L") else \
                struct.pack("<H", n & 0xFFFF)
    return bytes(out)


def _parse_dialog(t: _Tokens, symbols: dict, ex: bool) -> R.Dialog:
    while t.peek()[0] == "id" and t.peek()[1].upper() in ("DISCARDABLE", "MOVEABLE", "PURE", "PRELOAD",
                                                          "LOADONCALL", "IMPURE", "FIXED"):
        t.next()
    x = _expr(t, symbols)
    _comma(t)
    y = _expr(t, symbols)
    _comma(t)
    cx = _expr(t, symbols)
    _comma(t)
    cy = _expr(t, symbols)
    help_id = 0
    if _comma(t):
        help_id = _expr(t, symbols)
    d = R.Dialog(ex, 0x80C800C0 if not ex else 0x80C800C0, 0, x, y, cx, cy, help_id=help_id)
    style_set = False
    while True:
        k, v, ln = t.peek()
        u = v.upper()
        if u == "STYLE":
            t.next()
            d.style = _style_expr(t, symbols)
            style_set = True
        elif u == "EXSTYLE":
            t.next()
            d.exstyle = _style_expr(t, symbols)
        elif u == "CAPTION":
            t.next()
            d.title = _string(t)
            if not style_set:
                d.style |= R.WS_CAPTION
        elif u == "MENU":
            t.next()
            d.menu = _num_or_name(t, symbols)
        elif u == "CLASS":
            t.next()
            d.wclass = _num_or_name(t, symbols)
        elif u == "FONT":
            t.next()
            d.font_size = _expr(t, symbols)
            _comma(t)
            d.font_name = _string(t)
            if _comma(t):
                d.font_weight = _expr(t, symbols)
                if _comma(t):
                    d.italic = _expr(t, symbols)
                    if _comma(t):
                        d.charset = _expr(t, symbols)
        elif u in ("LANGUAGE", "VERSION", "CHARACTERISTICS"):
            t.next()
            _expr(t, symbols)
            if _comma(t):
                _expr(t, symbols)
        else:
            break
    if d.font_name:
        d.style |= R.DS_SETFONT
    _begin(t)
    while not _end(t):
        d.controls.append(_parse_control(t, symbols, ex))
    return d


def _parse_control(t: _Tokens, symbols: dict, ex: bool) -> R.DlgControl:
    k, v, ln = t.next()
    kw = v.upper()
    if kw == "CONTROL":
        text = _string(t) if t.peek()[0] == "str" else _expr(t, symbols)
        _comma(t)
        cid = _expr(t, symbols)
        _comma(t)
        cls = _string(t) if t.peek()[0] == "str" else _expr(t, symbols)
        _comma(t)
        style = _style_expr(t, symbols, base=R.WS_CHILD | R.WS_VISIBLE)
        _comma(t)
        x = _expr(t, symbols)
        _comma(t)
        y = _expr(t, symbols)
        _comma(t)
        cx = _expr(t, symbols)
        _comma(t)
        cy = _expr(t, symbols)
        exs = hid = 0
        if _comma(t):
            exs = _style_expr(t, symbols)
            if _comma(t):
                hid = _expr(t, symbols)
        if isinstance(cls, str) and cls.upper() in R.ATOM_OF:
            cls = R.ATOM_OF[cls.upper()]
        return R.DlgControl(cls, text, cid, style | R.WS_CHILD, exs, x, y, cx, cy, hid)
    if kw not in SHORTCUTS:
        raise RcError(f"line {ln}: unknown dialog statement '{v}'")
    cls, style, has_text = SHORTCUTS[kw]
    text = ""
    if has_text:
        text = _string(t) if t.peek()[0] == "str" else _expr(t, symbols)
        _comma(t)
    cid = _expr(t, symbols)
    _comma(t)
    x = _expr(t, symbols)
    _comma(t)
    y = _expr(t, symbols)
    _comma(t)
    cx = _expr(t, symbols) if not (kw == "ICON" and _at_comma_end(t)) else 0
    cy = 0
    if _comma(t):
        cy = _expr(t, symbols)
    exs = 0
    if _comma(t):
        style = _style_expr(t, symbols, base=style)
        if _comma(t):
            exs = _style_expr(t, symbols)
    if kw == "EDITTEXT" and not ex:
        exs = exs
    return R.DlgControl(R.ATOM_OF[cls.upper()], text, cid, style, exs, x, y, cx, cy)


def _at_comma_end(t: _Tokens) -> bool:
    return False


def _parse_menu(t: _Tokens, symbols: dict, ex: bool) -> R.Menu:
    while t.peek()[0] == "id" and t.peek()[1].upper() in ("DISCARDABLE", "MOVEABLE", "PURE", "PRELOAD",
                                                          "LOADONCALL", "IMPURE", "FIXED"):
        t.next()
    m = R.Menu(ex)
    _begin(t)

    def opt_flags() -> int:
        f = 0
        while _comma(t):
            k, v, ln = t.next()
            names = {n: bit for bit, n in _MENU_OPTS}
            if v.upper() in names:
                f |= names[v.upper()]
            else:
                raise RcError(f"line {ln}: unknown menu option '{v}'")
        return f

    def level() -> list:
        items = []
        while not _end(t):
            k, v, ln = t.next()
            u = v.upper()
            if u == "MENUITEM":
                if t.peek()[1].upper() == "SEPARATOR":
                    t.next()
                    items.append(R.MenuItem("", 0, R.MFT_SEPARATOR if ex else 0))
                    continue
                text = _string(t)
                if ex:
                    it = R.MenuItem(text)
                    if _comma(t):
                        it.id = _expr(t, symbols)
                        if _comma(t):
                            it.flags = _style_expr(t, symbols)
                            if _comma(t):
                                it.state = _style_expr(t, symbols)
                    items.append(it)
                else:
                    _comma(t)
                    cid = _expr(t, symbols)
                    items.append(R.MenuItem(text, cid, opt_flags()))
            elif u == "POPUP":
                text = _string(t)
                if ex:
                    it = R.MenuItem(text)
                    if _comma(t):
                        it.id = _expr(t, symbols)
                        if _comma(t):
                            it.flags = _style_expr(t, symbols)
                            if _comma(t):
                                it.state = _style_expr(t, symbols)
                                if _comma(t):
                                    it.help_id = _expr(t, symbols)
                else:
                    it = R.MenuItem(text, 0, opt_flags())
                _begin(t)
                it.children = level()
                items.append(it)
            else:
                raise RcError(f"line {ln}: unknown menu statement '{v}'")
        return items
    m.items = level()
    return m


def _parse_accel(t: _Tokens, symbols: dict) -> list[R.Accel]:
    _begin(t)
    out = []
    while not _end(t):
        k, v, ln = t.peek()
        if k == "str":
            t.next()
            s = _unescape(v)
            if s.startswith("^") and len(s) == 2:
                key, flags = ord(s[1].upper()) - 0x40, 0
            else:
                key, flags = ord(s[0]), 0
        else:
            key, flags = _expr(t, symbols), 0
        _comma(t)
        cmd = _expr(t, symbols)
        while _comma(t):
            o = t.next()[1].upper()
            flags |= {"VIRTKEY": R.FVIRTKEY, "ASCII": 0, "NOINVERT": R.FNOINVERT, "SHIFT": R.FSHIFT,
                      "CONTROL": R.FCONTROL, "ALT": R.FALT}.get(o, 0)
        if flags & R.FVIRTKEY and k == "str":
            key = ord(_unescape(v)[0].upper())
        out.append(R.Accel(flags, key, cmd))
    return out


def _parse_version(t: _Tokens, symbols: dict) -> R.VersionInfo:
    v = R.VersionInfo()

    def quad():
        parts = [_expr(t, symbols)]
        while _comma(t):
            parts.append(_expr(t, symbols))
        return tuple((parts + [0, 0, 0, 0])[:4])
    while not t.peek()[1].upper() in ("BEGIN", "{"):
        k, w, ln = t.next()
        u = w.upper()
        if u == "FILEVERSION":
            v.file_version = quad()
        elif u == "PRODUCTVERSION":
            v.product_version = quad()
        elif u == "FILEFLAGSMASK":
            v.flags_mask = _style_expr(t, symbols)
        elif u == "FILEFLAGS":
            v.flags = _style_expr(t, symbols)
        elif u == "FILEOS":
            v.os = _style_expr(t, symbols)
        elif u == "FILETYPE":
            v.file_type = _style_expr(t, symbols)
        elif u == "FILESUBTYPE":
            v.file_subtype = _style_expr(t, symbols)
        else:
            raise RcError(f"line {ln}: unknown VERSIONINFO statement '{w}'")
    _begin(t)
    while not _end(t):
        t.expect("BLOCK")
        block = _string(t)
        _begin(t)
        if block == "StringFileInfo":
            while not _end(t):
                t.expect("BLOCK")
                key = _string(t)
                items = v.strings.setdefault(key, {})
                _begin(t)
                while not _end(t):
                    t.expect("VALUE")
                    name = _string(t)
                    _comma(t)
                    items[name] = _string(t) if t.peek()[0] == "str" else str(_expr(t, symbols))
        else:
            while not _end(t):
                t.expect("VALUE")
                name = _string(t)
                vals = []
                while _comma(t):
                    vals.append(_expr(t, symbols))
                if name == "Translation":
                    v.translations += [(vals[i], vals[i + 1]) for i in range(0, len(vals) - 1, 2)]
    return v
