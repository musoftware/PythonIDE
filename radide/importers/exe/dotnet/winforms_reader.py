"""WinForms reader: C# classes / methods / fields found in source text, and InitializeComponent read statement by
statement into a neutral .form (controls, properties, menus, containers, event wiring)."""
from __future__ import annotations

import re
from pathlib import Path

from .cs_parser import Parser
from .py_emitter import COLOR_NAMES, EVENT_MAP


# ============================================================================ WinForms -> .form
WINFORMS_TYPES = {
    "Button": "Button", "Label": "Label", "TextBox": "TextBox", "RichTextBox": "TextBox",
    "MaskedTextBox": "TextBox", "CheckBox": "CheckBox", "RadioButton": "RadioButton", "ListBox": "ListBox",
    "CheckedListBox": "ListBox", "ComboBox": "ComboBox", "PictureBox": "PictureBox",
    "ProgressBar": "ProgressBar", "NumericUpDown": "NumericUpDown", "TrackBar": "TrackBar",
    "HScrollBar": "TrackBar", "VScrollBar": "TrackBar", "Panel": "Panel", "FlowLayoutPanel": "Panel",
    "TableLayoutPanel": "Panel", "SplitContainer": "Panel", "GroupBox": "GroupBox", "Timer": "Timer",
    "MenuStrip": "MenuStrip", "MainMenu": "MenuStrip", "ToolStrip": "ToolStrip", "StatusStrip": "StatusBar",
    "StatusBar": "StatusBar", "TabControl": "TabControl", "TreeView": "TreeView", "ListView": "ListView",
    "DataGridView": "DataGridView", "DataGrid": "DataGridView", "DateTimePicker": "DateTimePicker",
    "MonthCalendar": "DateTimePicker", "LinkLabel": "LinkLabel", "OpenFileDialog": "OpenFileDialog",
    "SaveFileDialog": "SaveFileDialog", "ColorDialog": "ColorDialog", "FontDialog": "FontDialog",
    "FolderBrowserDialog": "FolderBrowserDialog", "WebBrowser": "Panel", "DomainUpDown": "ComboBox",
}
APPROX_TYPES = {"FlowLayoutPanel", "TableLayoutPanel", "SplitContainer", "WebBrowser", "MonthCalendar",
                "DomainUpDown", "HScrollBar", "VScrollBar", "CheckedListBox", "RichTextBox", "MaskedTextBox",
                "DataGrid", "MainMenu"}
MENU_ITEM_TYPES = {"ToolStripMenuItem", "ToolStripButton", "ToolStripSeparator", "ToolStripLabel",
                   "ToolStripDropDownButton", "ToolStripSplitButton", "ToolStripStatusLabel", "ToolStripComboBox",
                   "ToolStripTextBox", "MenuItem", "ToolStripProgressBar"}
IGNORED_TYPES = {"ToolTip", "ImageList", "ErrorProvider", "ContextMenuStrip", "BindingSource", "NotifyIcon",
                 "HelpProvider", "BackgroundWorker", "IContainer", "Container", "ComponentResourceManager",
                 "TabPage", "SplitterPanel", "DataGridViewTextBoxColumn", "DataGridViewCheckBoxColumn",
                 "DataGridViewComboBoxColumn", "DataGridViewButtonColumn", "ColumnHeader", "PrintDocument",
                 "PageSetupDialog", "PrintDialog", "PrintPreviewDialog", "FileSystemWatcher", "SerialPort",
                 "EventLog", "Process", "DataSet", "PerformanceCounter", "ServiceController", "ListViewItem",
                 "TreeNode"}
ALIGN_MAP = {"Left": "Left", "Center": "Center", "Right": "Right"}


def _strip_this(node):
    """('member', ('name','this'), 'x') -> 'x'; ('name', 'x') -> 'x'."""
    if node[0] == "member" and node[1][0] == "name" and node[1][1] in ("this", "base", "Me", "MyBase"):
        return node[2]
    if node[0] == "name":
        return node[1]
    return None


def _lit(node):
    """Python value of a literal-ish node (str/num/bool/enum/color/point/size/font) or None."""
    t = node[0]
    if t == "str":
        return node[1]
    if t == "num":
        s = re.sub(r"[fFdDmMlLuU]+$", "", node[1].replace("_", ""))
        try:
            return int(s, 0) if not re.search(r"[.eE]", s) or s.lower().startswith("0x") else float(s)
        except ValueError:
            return None
    if t == "unary" and node[1] == "-":
        v = _lit(node[2])
        return -v if isinstance(v, (int, float)) else None
    if t == "const":
        return {"true": True, "false": False, "null": None}[node[1]]
    if t == "cast" or t == "paren":
        return _lit(node[-1])
    if t == "member":
        return ("enum", _qual(node))
    if t == "bin" and node[1] == "|":
        a, b = _lit(node[2]), _lit(node[3])
        if isinstance(a, tuple) and isinstance(b, tuple):
            return ("enum", a[1] + "|" + b[1])
    if t == "new":
        base = node[1].split(".")[-1]
        args = [_lit(a) for a in node[2]]
        if base in ("Point", "Size", "SizeF", "PointF", "Padding"):
            return (base, *args)
        if base == "Font":
            return ("Font", *args)
        if base in ("decimal", "Decimal"):
            if node[2] and node[2][0][0] == "newarr" and node[2][0][3]:
                return _lit(node[2][0][3][0])
            return args[0] if args else None
    if t == "call" and node[1][0] == "member":
        q = _qual(node[1])
        args = [_lit(a) for a in node[2]]
        if q.endswith("Color.FromArgb"):
            nums = [x for x in args if isinstance(x, int)]
            if len(nums) >= 3:
                r, g, b = nums[-3:]
                return ("color", f"#{r & 255:02X}{g & 255:02X}{b & 255:02X}")
            if len(nums) == 1:
                v = nums[0]
                return ("color", f"#{(v >> 16) & 255:02X}{(v >> 8) & 255:02X}{v & 255:02X}")
        if q.endswith("Color.FromName") and args and isinstance(args[0], str):
            return ("color", COLOR_NAMES.get(args[0].lower(), ""))
    return None


def _mnemonic(text: str) -> str:
    """'&File' -> 'File', 'Save && Exit' -> 'Save & Exit' (Windows access keys)."""
    return re.sub(r"&(.)", lambda m: m.group(1), text) if "&" in text else text


def _qual(node) -> str:
    if node[0] == "name":
        return node[1]
    if node[0] == "member":
        return _qual(node[1]) + "." + node[2]
    return "?"


def _color(v) -> str:
    if isinstance(v, tuple) and v[0] == "color":
        return v[1]
    if isinstance(v, tuple) and v[0] == "enum":
        last = v[1].split(".")[-1]
        if ".SystemColors." in "." + v[1] or v[1].startswith("SystemColors"):
            return ""
        return COLOR_NAMES.get(last.lower(), "")
    return ""


def _enum_last(v) -> str:
    if isinstance(v, tuple) and v[0] == "enum":
        return v[1].split("|")[-1].split(".")[-1]
    return str(v) if v is not None else ""


class WinFormsClass:
    """One decompiled C# class (a Form or UserControl)."""

    def __init__(self, name: str, base: str, body: str, file: Path | None):
        self.name, self.base, self.body, self.file = name, base, body, file


def find_classes(src: str, file: Path | None = None) -> list[WinFormsClass]:
    out = []
    for m in re.finditer(r"\b(?:public\s+|internal\s+|private\s+|sealed\s+|partial\s+|abstract\s+)*class\s+"
                         r"(\w+)\s*(?::\s*([\w.<>, ]+))?\s*\{", src):
        start = m.end() - 1
        end = _match_brace(src, start)
        if end < 0:
            continue
        out.append(WinFormsClass(m.group(1), (m.group(2) or "").split(",")[0].strip(), src[start + 1:end], file))
    return out


def _match_brace(src: str, start: int) -> int:
    """Index of the } that closes the { at *start* (strings and comments skipped)."""
    depth, i, n = 0, start, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            verbatim = i > 0 and src[i - 1] == "@" or i > 1 and src[i - 2:i] in ("$@", "@$")
            j = i + 1
            while j < n:
                if src[j] == "\\" and not verbatim:
                    j += 2
                    continue
                if src[j] == '"':
                    if verbatim and src.startswith('""', j):
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def brace_matches(src: str, start: int) -> dict[int, int]:
    """{index of '{': index of its '}' (-1 = never closed)} for every '{' that _match_brace(src, start) passes
    over in code (it lexes exactly like _match_brace, so each entry equals _match_brace(src, that index)).
    One linear scan instead of one scan per candidate: a file with thousands of unclosed "class X {"
    lines would otherwise take quadratic time."""
    out: dict[int, int] = {}
    stack: list[int] = []
    i, n = start, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            verbatim = i > 0 and src[i - 1] == "@" or i > 1 and src[i - 2:i] in ("$@", "@$")
            j = i + 1
            while j < n:
                if src[j] == "\\" and not verbatim:
                    j += 2
                    continue
                if src[j] == '"':
                    if verbatim and src.startswith('""', j):
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            stack.append(i)
            out[i] = -1
        elif c == "}" and stack:
            out[stack.pop()] = i
        i += 1
    return out


METHOD_RE = re.compile(
    r"(?m)^[ \t]*((?:(?:public|private|protected|internal|static|virtual|override|async|new|sealed|extern|"
    r"unsafe|partial|final|synchronized|abstract|native|default)\s+)*)(?:<[^>]*>\s*)?([\w.<>\[\],? ]+?)\s+(\w+)\s*"
    r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*(?:where[^{]*|throws[^{]*)?\{")
FIELD_RE = re.compile(r"(?m)^[ \t]*(?:(?:public|private|protected|internal|static|readonly|const|volatile|new|final|"
                      r"transient)\s+)+"
                      r"([\w.<>\[\],? ]+?)\s+(\w+)\s*(?:=\s*([^;]+))?;")


def class_methods(body: str) -> list[dict]:
    """Methods of a class body: [{name, ret, params, body, header}] (nested classes skipped)."""
    out = []
    for m in METHOD_RE.finditer(body):
        ret = m.group(2).strip()
        if ret in ("return", "new", "else", "if", "while", "for", "foreach", "switch", "using", "catch", "lock") or \
                m.group(3) in ("if", "while", "for", "foreach", "switch", "catch", "using", "lock"):
            continue
        # skip methods inside nested types: depth of the match must be 0
        prefix = body[:m.start()]
        if _depth(prefix) != 0:
            continue
        start = m.end() - 1
        end = _match_brace(body, start)
        if end < 0:
            continue
        out.append({"name": m.group(3), "ret": ret, "params": m.group(4).strip(), "body": body[start + 1:end],
                    "header": " ".join(body[m.start():start].split())})
    # constructors
    return out


def _depth(text: str) -> int:
    clean = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', "", text, flags=re.S)
    return clean.count("{") - clean.count("}")


def class_fields(body: str) -> dict[str, tuple[str, str | None]]:
    out = {}
    for m in FIELD_RE.finditer(body):
        if _depth(body[:m.start()]) != 0:
            continue
        typ, name, init = m.group(1).strip(), m.group(2), m.group(3)
        if typ in ("return", "using", "event", "delegate") or "(" in typ:
            continue
        out[name] = (typ, init.strip() if init else None)
    return out


def parse_params(params: str) -> list[tuple[str, str]]:
    out = []
    depth, cur = 0, ""
    for ch in params:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    res = []
    for p in out:
        p = re.sub(r"^\s*(this|ref|out|in|params|final)\s+", "", p.strip())
        p = p.split("=")[0].strip()
        parts = p.rsplit(None, 1)
        if len(parts) == 2:
            res.append((parts[0], parts[1]))
        elif parts:
            res.append(("", parts[0]))
    return res


def parse_winforms(cls: WinFormsClass, all_forms: set[str] | None = None) -> tuple[dict, dict, list] | None:
    """InitializeComponent of *cls* -> (form_dict, wiring {neutral handler: C# method}, notes)."""
    methods = {m["name"]: m for m in class_methods(cls.body)}
    ic = methods.get("InitializeComponent")
    if ic is None:
        return None
    notes: list[str] = []
    p = Parser(ic["body"])
    stmts = p.statements()
    ctrls: dict[str, dict] = {}          # name -> {"wtype", "props", "parent", "order"}
    order: list[str] = []
    menus: dict[str, dict] = {}          # menu item name -> {"Text", "Name", "Items": [names], "type"}
    form = {"Name": cls.name, "Text": cls.name}
    form_extra: dict = {}
    events: list[tuple[str, str, str]] = []     # (owner name or "", event, method)
    tooltips: dict[str, str] = {}
    tabpages: dict[str, dict] = {}       # tab page name -> {"Text", "parent", "index"}
    form_children: list[str] = []
    radio_groups = 0
    del radio_groups

    def target_of(node):
        """Owner of a member chain: ('ctl', name) / ('form', None)."""
        if node[0] == "name" and node[1] in ("this", "base", "Me", "MyBase"):
            return ("form", None)
        n = _strip_this(node)
        if n is not None:
            if n in ctrls or n in menus or n in tabpages:
                return ("ctl", n)
            if node[0] == "name" and n not in ctrls:
                return ("form", None) if n in ("Controls",) else ("ctl", n)
        return (None, None)

    def add_children(parent: str | None, args):
        items = []
        for a in args:
            if a[0] == "newarr":
                items += a[3] or []
            else:
                items.append(a)
        for a in items:
            n = _strip_this(a)
            if n is None:
                continue
            if parent is None:
                form_children.append(n)
                if n in ctrls:
                    ctrls[n]["parent"] = ""
            elif parent in tabpages:
                if n in ctrls:
                    ctrls[n]["parent"] = ("tab", parent)
            elif parent in ctrls:
                if ctrls[parent]["wtype"] == "TabControl" and n in tabpages:
                    tabpages[n]["parent"] = parent
                    tabpages[n]["index"] = sum(1 for t in tabpages.values() if t.get("parent") == parent) - 1
                elif n in ctrls:
                    ctrls[n]["parent"] = parent

    def add_menu_items(owner: str, args):
        items = []
        for a in args:
            if a[0] == "newarr":
                items += a[3] or []
            else:
                items.append(a)
        lst = ctrls[owner]["menu"] if owner in ctrls else menus[owner]["Items"] if owner in menus else None
        if lst is None:
            return
        for a in items:
            n = _strip_this(a)
            if n:
                lst.append(n)

    for st in stmts:
        if st[0] != "expr":
            continue
        e = st[1]
        if e[0] == "assign" and e[1] == "=":
            tgt, val = e[2], e[3]
            # this.x = new T()
            is_field = tgt[0] == "name" or (tgt[0] == "member" and tgt[1] in (("name", "this"), ("name", "Me")))
            if val[0] == "new" and is_field and _strip_this(tgt) is not None and \
                    val[1].split(".")[-1] not in ("Size", "SizeF", "Point", "PointF", "Font", "Padding",
                                                  "Rectangle", "Icon", "Bitmap", "Cursor", "Color"):
                name = _strip_this(tgt)
                wtype = val[1].split(".")[-1].split("<")[0]
                if wtype in MENU_ITEM_TYPES:
                    menus[name] = {"Name": name, "Text": "-" if wtype == "ToolStripSeparator" else name,
                                   "Items": [], "type": wtype}
                elif wtype == "TabPage":
                    tabpages[name] = {"Text": name, "parent": None, "index": 0}
                elif wtype in IGNORED_TYPES:
                    if wtype not in ("IContainer", "Container", "ComponentResourceManager", "TabPage"):
                        notes.append(f"{cls.name}.{name}: {wtype} is not supported - skipped")
                    ctrls.setdefault("__ignored__", {"names": set()})["names"].add(name)
                else:
                    ctrls[name] = {"wtype": wtype, "props": {}, "parent": "", "menu": []}
                    order.append(name)
                continue
            if tgt[0] == "name":            # "Text = ...;" - a form property (designer of .NET 6+, no "this.")
                if tgt[1] not in ctrls and tgt[1] not in menus and tgt[1] not in tabpages:
                    form_extra[tgt[1]] = _lit(val)
                continue
            if tgt[0] != "member":
                continue
            owner_node, prop = tgt[1], tgt[2]
            v = _lit(val)
            # nested: this.x.FlatAppearance.BorderSize ... -> ignore deeper chains except Font
            kind, owner = target_of(owner_node)
            if kind == "form":
                form_extra[prop] = v
            elif kind == "ctl":
                if owner in menus:
                    menus[owner][prop] = v
                elif owner in tabpages:
                    tabpages[owner][prop] = v
                elif owner in ctrls:
                    ctrls[owner]["props"][prop] = v
            continue
        if e[0] == "assign" and e[1] == "+=":
            tgt, val = e[2], e[3]
            if tgt[0] == "name":            # "Load += Form1_Load;" - a form event (designer of .NET 6+)
                ev, kind, owner = tgt[1], "form", None
            elif tgt[0] != "member":
                continue
            else:
                ev = tgt[2]
                kind, owner = target_of(tgt[1])
            meth = None
            if val[0] == "new" and val[2]:
                meth = _strip_this(val[2][0]) if val[2][0][0] in ("name", "member") else None
            elif val[0] in ("name", "member"):
                meth = _strip_this(val)
            if meth is None:
                notes.append(f"{cls.name}: event {ev} wired to an inline lambda - left in the C# source")
                continue
            events.append(("" if kind == "form" else owner or "", ev, meth))
            continue
        if e[0] == "call" and e[1][0] == "member":
            func = e[1]
            mname = func[2]
            recv = func[1]
            # x.Controls.Add(y) / base.Controls.Add(y) / Controls.AddRange(...)
            if mname in ("Add", "AddRange") and recv[0] in ("member", "name") and \
                    (recv[0] == "member" and recv[2] in ("Controls", "TabPages") or recv == ("name", "Controls")):
                owner_node = recv[1] if recv[0] == "member" else ("name", "this")
                if recv[0] == "member" and recv[2] in ("Controls",) and owner_node[0] == "member" and \
                        owner_node[2] in ("Panel1", "Panel2"):            # SplitContainer panels
                    owner_node = owner_node[1]
                kind, owner = target_of(owner_node)
                add_children(None if kind == "form" else owner, e[2])
                continue
            if mname in ("Add", "AddRange") and recv[0] == "member" and recv[2] in ("Items", "DropDownItems",
                                                                                    "MenuItems"):
                kind, owner = target_of(recv[1])
                if owner in menus or owner in ctrls and ctrls[owner]["wtype"] in ("MenuStrip", "ToolStrip",
                                                                                  "StatusStrip", "MainMenu",
                                                                                  "ContextMenuStrip"):
                    add_menu_items(owner, e[2])
                    continue
                if owner in ctrls:
                    vals = []
                    for a in e[2]:
                        if a[0] == "newarr":
                            vals += [_lit(x) for x in a[3] or []]
                        else:
                            vals.append(_lit(a))
                    ctrls[owner]["props"].setdefault("__items", []).extend(
                        str(x) for x in vals if isinstance(x, (str, int, float)))
                continue
            if mname == "SetToolTip" and len(e[2]) == 2:
                n = _strip_this(e[2][0])
                v = _lit(e[2][1])
                if n and isinstance(v, str):
                    tooltips[n] = v
                continue
            if mname == "Add" and recv[0] == "member" and recv[2] == "Columns":
                kind, owner = target_of(recv[1])
                if owner in ctrls:
                    v = _lit(e[2][0]) if e[2] else None
                    vals = [_lit(x) for x in e[2]]
                    txt = next((x for x in vals if isinstance(x, str)), None)
                    if txt is None and isinstance(v, str):
                        txt = v
                    ctrls[owner]["props"].setdefault("__columns", []).append(txt or f"Column{len(ctrls[owner]['props'].get('__columns', [])) + 1}")
                continue
            if mname in ("AddRange",) and recv[0] == "member" and recv[2] == "Columns":
                kind, owner = target_of(recv[1])
                if owner in ctrls:
                    ctrls[owner]["props"].setdefault("__colrefs", []).extend(
                        _strip_this(a) for a in (e[2][0][3] if e[2] and e[2][0][0] == "newarr" else e[2]))
                continue
    ctrls.pop("__ignored__", None)

    # ---- build the neutral form
    from ....controls import CONTROL_TYPES, format_anchor
    w, h = 400, 300
    cs = form_extra.get("ClientSize") or form_extra.get("Size")
    if isinstance(cs, tuple) and len(cs) >= 3:
        w, h = int(cs[1] or w), int(cs[2] or h)
        if "ClientSize" not in form_extra:
            w, h = max(100, w - 16), max(80, h - 39)
    form = {"Name": cls.name, "Text": str(form_extra.get("Text") if isinstance(form_extra.get("Text"), str) else
                                           cls.name), "Width": w, "Height": h}
    bc = _color(form_extra.get("BackColor"))
    if bc:
        form["BackColor"] = bc
    sp = _enum_last(form_extra.get("StartPosition"))
    form["StartPosition"] = "CenterScreen" if sp in ("CenterScreen", "CenterParent", "") else "Manual"
    fb = _enum_last(form_extra.get("FormBorderStyle"))
    if fb.startswith("Fixed") or fb == "None":
        form["FormBorderStyle"] = "FixedSingle"
    if form_extra.get("TopMost") is True:
        form["TopMost"] = True
    if _enum_last(form_extra.get("WindowState")) == "Maximized":
        form["WindowState"] = "Maximized"

    controls: list[dict] = []
    menu_height = 0
    used_names: set[str] = set()

    def menu_tree(names: list[str], depth=0) -> list[dict]:
        items = []
        for n in names:
            m = menus.get(n)
            if m is None or depth > 6:
                continue
            text = m.get("Text")
            if not isinstance(text, str):
                text = n
            item = {"Text": "-" if m["type"] == "ToolStripSeparator" else _mnemonic(text), "Name": n}
            if m["Items"]:
                item["Items"] = menu_tree(m["Items"], depth + 1)
            items.append(item)
        return items

    # tab page offsets: children of a TabPage go to the TabControl with props["TabPage"]
    def parent_info(c):
        par = c["parent"]
        if isinstance(par, tuple):
            tp = tabpages.get(par[1], {})
            return tp.get("parent") or "", tp.get("index", 0)
        return par, None

    for n in order:
        c = ctrls[n]
        wt = c["wtype"]
        nt = WINFORMS_TYPES.get(wt)
        if nt is None:
            notes.append(f"{cls.name}.{n}: unknown control type {wt} - became a Panel placeholder")
            nt = "Panel"
        elif wt in APPROX_TYPES:
            notes.append(f"{cls.name}.{n}: {wt} approximated as {nt}")
        ct = CONTROL_TYPES[nt]
        props = ct.default_props(n)
        pr = c["props"]
        loc, size = pr.get("Location"), pr.get("Size")
        if isinstance(loc, tuple) and len(loc) >= 3 and not ct.nonvisual:
            props["Left"], props["Top"] = int(loc[1] or 0), int(loc[2] or 0)
        if isinstance(size, tuple) and len(size) >= 3 and not ct.nonvisual:
            props["Width"], props["Height"] = int(size[1] or 0), int(size[2] or 0)
        if wt in ("MenuStrip", "MainMenu"):
            props["Items"] = menu_tree(c["menu"])
            if isinstance(size, tuple) and _enum_last(pr.get("Dock")) in ("", "Top") and c["parent"] == "":
                menu_height = max(menu_height, int(size[2] or 24))
            elif c["parent"] == "" and wt == "MenuStrip":
                menu_height = max(menu_height, 24)
        elif wt == "ToolStrip":
            props["Items"] = menu_tree(c["menu"])
        elif wt in ("StatusStrip",):
            labels = [menus[x].get("Text") for x in c["menu"] if x in menus]
            props["Text"] = next((t for t in labels if isinstance(t, str)), "Ready")
            props["Dock"] = "Bottom"
        text = pr.get("Text")
        if isinstance(text, str) and "Text" in props:
            props["Text"] = text if nt in ("TextBox", "ComboBox") else _mnemonic(text)
        elif "Text" in props and not isinstance(text, str):
            props["Text"] = "" if nt in ("TextBox", "ComboBox", "StatusBar") else props.get("Text", n)
        font = pr.get("Font")
        if isinstance(font, tuple) and font[0] == "Font" and "FontName" in props:
            if len(font) > 1 and isinstance(font[1], str):
                props["FontName"] = font[1]
            if len(font) > 2 and isinstance(font[2], (int, float)):
                props["FontSize"] = int(round(font[2]))
            style = " ".join(_enum_last(x) if isinstance(x, tuple) else "" for x in font[3:])
            style += " ".join(str(x[1]) for x in font[3:] if isinstance(x, tuple) and x[0] == "enum")
            props["FontBold"] = "Bold" in style
            props["FontItalic"] = "Italic" in style
        for key in ("BackColor", "ForeColor"):
            col = _color(pr.get(key))
            if col and key in props:
                props[key] = col
        if wt == "LinkLabel" and _color(pr.get("LinkColor")):
            props["LinkColor"] = _color(pr.get("LinkColor"))
        anchor = pr.get("Anchor")
        if isinstance(anchor, tuple) and anchor[0] == "enum" and "Anchor" in props:
            edges = {x.split(".")[-1] for x in anchor[1].split("|")}
            props["Anchor"] = format_anchor(edges) if edges - {"None"} else "None"
        dock = _enum_last(pr.get("Dock"))
        if dock in ("Top", "Bottom", "Left", "Right", "Fill") and "Dock" in props and \
                wt not in ("MenuStrip", "ToolStrip", "MainMenu"):
            props["Dock"] = dock
        for key in ("Enabled", "Visible", "Checked", "ReadOnly", "Multiline"):
            if isinstance(pr.get(key), bool) and key in props:
                props[key] = pr[key]
        if pr.get("CheckState") is not None and "Checked" in props:
            props["Checked"] = _enum_last(pr["CheckState"]) == "Checked"
        if isinstance(pr.get("TabIndex"), int) and "TabIndex" in props:
            props["TabIndex"] = pr["TabIndex"]
        if nt == "TextBox":
            if wt == "RichTextBox":
                props["Multiline"] = True
            if isinstance(pr.get("PasswordChar"), str) and pr["PasswordChar"].strip("\0"):
                props["PasswordChar"] = pr["PasswordChar"][:1]
            if pr.get("UseSystemPasswordChar") is True:
                props["PasswordChar"] = "*"
            if isinstance(pr.get("MaxLength"), int) and pr["MaxLength"] < 32767:
                props["MaxLength"] = pr["MaxLength"]
            al = _enum_last(pr.get("TextAlign"))
            if al and "TextAlign" in props:
                props["TextAlign"] = "Center" if al == "Center" else "Right" if al == "Right" else "Left"
        if "TextAlign" in props and nt in ("Label", "Button", "LinkLabel"):
            al = _enum_last(pr.get("TextAlign"))
            if al:
                props["TextAlign"] = "Center" if "Center" in al else "Right" if "Right" in al else "Left"
        for key in ("Minimum", "Maximum", "Value"):
            if isinstance(pr.get(key), (int, float)) and key in props:
                props[key] = int(pr[key])
        if nt == "Timer":
            if isinstance(pr.get("Interval"), int):
                props["Interval"] = pr["Interval"]
            props["Enabled"] = pr.get("Enabled") is True
        if nt in ("ListBox", "ComboBox") and pr.get("__items"):
            props["Items"] = ";".join(x.replace(";", ",") for x in pr["__items"])
        if nt == "ComboBox":
            props["DropDownStyle"] = "DropDownList" if _enum_last(pr.get("DropDownStyle")) == "DropDownList" \
                else "DropDown"
        if nt in ("ListView", "DataGridView"):
            cols = pr.get("__columns") or []
            if not cols and pr.get("__colrefs"):
                cols = [str(r) for r in pr["__colrefs"] if r]
            if cols:
                props["Columns"] = ";".join(str(x) for x in cols)
        if nt == "DateTimePicker":
            fmt = _enum_last(pr.get("Format"))
            if fmt in ("Short", "Long", "Time"):
                props["Format"] = fmt
        if nt == "TabControl":
            pages = sorted((t for t in tabpages.values() if t.get("parent") == n), key=lambda t: t["index"])
            if pages:
                props["TabPages"] = ";".join(str(t.get("Text") if isinstance(t.get("Text"), str) else "Tab")
                                             for t in pages)
        if nt == "OpenFileDialog" or nt == "SaveFileDialog":
            for key in ("Filter", "Title", "FileName", "InitialDirectory"):
                if isinstance(pr.get(key), str):
                    props[key] = pr[key]
        if n in tooltips and "ToolTip" in props:
            props["ToolTip"] = tooltips[n]
        if pr.get("Image") is not None or pr.get("BackgroundImage") is not None:
            notes.append(f"{cls.name}.{n}: image from the program resources not extracted")
        par, page = parent_info(c)
        props["Parent"] = par if par in ctrls else ""
        if page is not None:
            props["TabPage"] = page
        used_names.add(n)
        controls.append({"type": nt, "props": props})

    # menu strip inside the client area in WinForms, outside it (native menu) in RAD IDE
    if menu_height:
        form["Height"] = max(60, form["Height"] - menu_height)
        for c in controls:
            ct = CONTROL_TYPES[c["type"]]
            if not ct.nonvisual and not c["props"].get("Parent") and c["props"].get("Dock", "None") in ("None",):
                c["props"]["Top"] = max(0, int(c["props"]["Top"]) - menu_height)

    # z-order: WinForms Controls.Add order = front first; .form list = back first
    pos = {n: i for i, n in enumerate(form_children)}
    controls.sort(key=lambda c: -pos.get(c["props"]["Name"], -1) if c["props"]["Name"] in pos else 0)
    # containers must come before their children: keep a stable topological order
    names_order = [c["props"]["Name"] for c in controls]
    by_name = {c["props"]["Name"]: c for c in controls}
    ordered, seen = [], set()

    def place(nm, depth=0):
        if nm in seen or depth > 20:
            return
        par = by_name[nm]["props"].get("Parent") or ""
        if par and par in by_name:
            place(par, depth + 1)
        seen.add(nm)
        ordered.append(by_name[nm])
    for nm in names_order:
        place(nm)

    # ---- event wiring: neutral handler name -> C# method
    wiring: dict[str, str] = {}
    menu_names = set(menus)
    for owner, ev, meth in events:
        nev = EVENT_MAP.get(ev)
        if owner == "" or owner == cls.name:
            nev = nev or ev
            handler = f"{cls.name}_{nev}"
        elif owner in menu_names:
            if ev not in ("Click", "ButtonClick"):
                notes.append(f"{cls.name}.{owner}.{ev}: menu event not supported")
                continue
            handler = f"{owner}_Click"
        elif owner in used_names:
            if nev is None:
                notes.append(f"{cls.name}.{owner}.{ev}: event has no RAD IDE equivalent - handler {meth} "
                             "kept as a method")
                continue
            handler = f"{owner}_{nev}"
        else:
            continue
        wiring.setdefault(handler, meth)
    return {"version": 2, "props": form, "controls": ordered}, wiring, notes
