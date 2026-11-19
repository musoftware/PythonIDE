"""Java programs (.jar, .class, or an .exe wrapper such as Launch4j / exe4j / JSmooth) -> RAD IDE project.

1. The jar is found (the file itself, a zip appended to the .exe, or a jar next to it) and rewritten as a
   clean jar.
2. Vineflower (or CFR) - open-source Java decompilers, downloaded once into %LOCALAPPDATA%\\RADIDE\\tools\\java
   - turn it back into Java sources (``source_dir``).
3. Swing frames/dialogs (best effort): ``new JButton(...)``, ``setBounds``, ``setText``, ``setFont``, colours,
   menus, ``addActionListener`` (lambda, method reference or anonymous class) -> neutral ``.form``; frames built
   with a layout manager (GroupLayout, ...) get approximate positions.  Listener bodies and the other methods
   are translated to Python (python-tk) by the shared rules of dotnet.py plus Swing rules; unknown lines stay
   as ``# Java:`` comments (AI rewrites them when allowed).
Only for programs you wrote, own, or may legally analyse.
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from pathlib import Path

from .base import BinaryInfo, ImportResult, find_tool, tools_dir
from .dotnet import (COLOR_NAMES, P_ATOM, ParseError, Parser, PyEmitter, Untranslatable, WinFormsClass,
                     _match_brace, ai_rewrite, class_methods, download, pystr, run_tool, say,
                     set_form_code, set_startup, translate_form_class)

DECOMPILERS = [
    ("vineflower", "https://repo1.maven.org/maven2/org/vineflower/vineflower/1.10.1/vineflower-1.10.1.jar"),
    ("cfr", "https://repo1.maven.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar"),
]

SWING_TYPES = {
    "JButton": "Button", "JToggleButton": "CheckBox", "JLabel": "Label", "JTextField": "TextBox",
    "JFormattedTextField": "TextBox", "JPasswordField": "TextBox", "JTextArea": "TextBox", "JTextPane": "TextBox",
    "JEditorPane": "TextBox", "JCheckBox": "CheckBox", "JRadioButton": "RadioButton", "JComboBox": "ComboBox",
    "JList": "ListBox", "JPanel": "Panel", "JProgressBar": "ProgressBar", "JSlider": "TrackBar",
    "JSpinner": "NumericUpDown", "JTable": "DataGridView", "JTree": "TreeView", "JTabbedPane": "TabControl",
    "Timer": "Timer", "JMenuBar": "MenuStrip", "JToolBar": "ToolStrip",
    # AWT
    "Button": "Button", "Label": "Label", "TextField": "TextBox", "TextArea": "TextBox", "Checkbox": "CheckBox",
    "Choice": "ComboBox", "List": "ListBox", "Panel": "Panel",
}
MENU_TYPES = {"JMenu", "JMenuItem", "JCheckBoxMenuItem", "JRadioButtonMenuItem", "Menu", "MenuItem"}
FRAME_BASES = {"JFrame", "JDialog", "JPanel", "Frame", "Dialog", "JInternalFrame", "JWindow"}
LISTENER_EVENT = {"addActionListener": "Click", "addItemListener": "CheckedChanged",
                  "addChangeListener": "ValueChanged", "addListSelectionListener": "SelectedIndexChanged",
                  "addMouseListener": "Click", "addKeyListener": "KeyDown", "addFocusListener": "GotFocus",
                  "addWindowListener": "FormClosing"}
EVENT_FOR_TYPE = {("Click", "CheckBox"): "CheckedChanged", ("Click", "RadioButton"): "CheckedChanged",
                  ("Click", "ComboBox"): "SelectedIndexChanged", ("Click", "TextBox"): None,
                  ("ValueChanged", "TrackBar"): "ValueChanged", ("ValueChanged", "NumericUpDown"): "ValueChanged"}
PROP_SETTERS = {"setText": "Text", "setSelected": "Checked", "setEnabled": "Enabled", "setVisible": "Visible",
                "setValue": "Value", "setForeground": "ForeColor", "setBackground": "BackColor",
                "setSelectedIndex": "SelectedIndex", "setSelectedItem": "SelectedItem", "setTitle": "Text",
                "setState": "Checked", "setLabel": "Text", "setMaximum": "Maximum", "setMinimum": "Minimum"}
PROP_GETTERS = {"getText": "Text", "isSelected": "Checked", "isEnabled": "Enabled", "isVisible": "Visible",
                "getValue": "Value", "getSelectedIndex": "SelectedIndex", "getSelectedItem": "SelectedItem",
                "getSelectedValue": "SelectedItem", "getState": "Checked", "getLabel": "Text",
                "getTitle": "Text", "getWidth": "Width", "getHeight": "Height", "getX": "Left", "getY": "Top"}


# ============================================================================ Swing translation rules
class SwingEmitter(PyEmitter):
    LANG = "Java"
    FORM_MEMBERS = {"setTitle", "getTitle", "dispose", "setVisible", "repaint", "pack", "setSize"}

    def kind_of_type(self, typ):
        base = (typ or "").split("<")[0].split(".")[-1]
        if base in ("ArrayList", "List", "Vector", "LinkedList", "DefaultListModel"):
            return "list"
        if base in ("HashMap", "Map", "TreeMap", "LinkedHashMap", "Hashtable"):
            return "dict"
        if base == "Random":
            return "random"
        return super().kind_of_type(typ)

    def expr_stmt(self, e):
        if e[0] == "call" and e[1][0] == "member":
            obj, method, args = e[1][1], e[1][2], e[2]
            target = obj
            if obj[0] == "name" and obj[1] in ("this", "super"):
                target = ("name", "this")
            if method in PROP_SETTERS and len(args) == 1 and (self.ctrl_of(target) or self.is_form(target)):
                vcode, vk = self.ex(args[0])
                prop = PROP_SETTERS[method]
                if self.is_form(target) and prop == "Visible":
                    return [f"self.root.deiconify() if {vcode} else self.root.withdraw()"]
                return self.try_setter(("member", target, prop, False), vcode, vk)
            if method == "setEditable" and self.ctrl_of(target) and len(args) == 1:
                return self.try_setter(("member", target, "ReadOnly", False), f"not {self.ex(args[0])[0]}")
            if method == "setBounds" and self.ctrl_of(target) and len(args) == 4:
                n = self.ctrl_of(target)
                vals = [self.ex(a)[0] for a in args]
                return [f"self._places[{pystr(n)}].update(x={vals[0]}, y={vals[1]}, width={vals[2]}, "
                        f"height={vals[3]})", f"self.{n}.place(**self._places[{pystr(n)}])"]
        if e[0] == "call" and e[1][0] == "name" and e[1][1] in PROP_SETTERS and len(e[2]) == 1 and \
                not self.is_local(e[1][1]) and e[1][1] not in self.methods:
            return self.expr_stmt(("call", ("member", ("name", "this"), e[1][1], False), e[2]))
        return super().expr_stmt(e)

    def is_form(self, node):
        if node[0] == "member" and node[2] == "this":           # Outer.this
            return True
        return node in (("name", "this"), ("name", "super")) or super().is_form(node)

    def name(self, n):
        if n == "super":
            return "self", None, P_ATOM
        return super().name(n)

    def call(self, node):
        func = node[1]
        if func[0] == "name" and not self.is_local(func[1]) and func[1] not in self.methods:
            n = func[1]
            if n in ("dispose",):
                return "self.root.destroy()", None, P_ATOM
            if n in ("repaint", "revalidate", "pack", "validate"):
                return "self.root.update_idletasks()", None, P_ATOM
            if n in PROP_GETTERS:
                return self.member(("member", ("name", "this"), PROP_GETTERS[n], False))
        return super().call(node)

    def call_rule(self, obj, method, args):
        target = ("name", "this") if obj in (("name", "this"), ("name", "super")) else obj
        cname = self.ctrl_of(target)
        if cname is not None:
            t = self.controls[cname]
            if method in PROP_GETTERS and not args:
                got = self.control_get(cname, PROP_GETTERS[method])
                if got is not None:
                    return got[0], got[1], P_ATOM
            if method in ("addItem", "add") and t in ("ComboBox", "ListBox") and len(args) == 1:
                code, kind = self.items_call(cname, "Add", args)
                return code, kind, P_ATOM
            if method in ("removeAllItems", "removeAll") and t in ("ComboBox", "ListBox"):
                code, kind = self.items_call(cname, "Clear", args)
                return code, kind, P_ATOM
            if method == "getItemCount" and t in ("ComboBox", "ListBox"):
                return self.member(("member", ("member", target, "Items", False), "Count", False))
            if method == "requestFocus" or method == "requestFocusInWindow":
                return f"self.{cname}.focus_set()", None, P_ATOM
            if method == "doClick":
                return f"self.{cname}.invoke()", None, P_ATOM
            if method == "append" and t == "TextBox":
                arg = self.ex(args[0])[0]
                if cname in self.multiline:
                    return f"self.{cname}.insert(\"end\", {arg})", None, P_ATOM
                return f"self.{cname}_var.set(self.{cname}_var.get() + {arg})", None, P_ATOM
            if method in ("start", "stop") and t == "Timer":
                return f"self.{cname}.{method.capitalize()}()", None, P_ATOM
            if method == "isEmpty":
                pass
            elif method not in ("equals", "toString", "length", "trim"):
                raise Untranslatable(f"{t}.{method}()")
        if self.is_form(target):
            if method in ("dispose",):
                return "self.root.destroy()", None, P_ATOM
            if method in PROP_GETTERS and not args:
                return self.member(("member", ("name", "this"), PROP_GETTERS[method], False))
            if method in ("repaint", "revalidate", "pack"):
                return "self.root.update_idletasks()", None, P_ATOM
        if method == "toString" and not args:
            code, kind = self.ex(obj)
            return (code, "str", P_ATOM) if kind == "str" else (f"str({code})", "str", P_ATOM)
        if method == "length" and not args:
            return f"len({self.ex(obj)[0]})", "int", P_ATOM
        if method == "size" and not args:
            return f"len({self.ex(obj)[0]})", "int", P_ATOM
        if method in ("get",) and len(args) == 1:
            code, kind = self.ex(obj)
            if kind == "list":
                return f"{code}[{self.ex(args[0])[0]}]", None, P_ATOM
            if kind == "dict":
                return f"{code}.get({self.ex(args[0])[0]})", None, P_ATOM
        if method in ("put",) and len(args) == 2:
            code, kind = self.ex(obj)
            if kind == "dict":
                return f"{code}.__setitem__({self.ex(args[0])[0]}, {self.ex(args[1])[0]})", None, P_ATOM
        if method in ("add", "addElement") and len(args) == 1:
            code, kind = self.ex(obj)
            if kind == "list":
                return f"{code}.append({self.ex(args[0])[0]})", None, P_ATOM
        if method == "nextInt":
            code, kind = self.ex(obj)
            if kind == "random":
                if args:
                    return f"{code}.randrange({self.ex(args[0])[0]})", "int", P_ATOM
                return f"{code}.randrange(2147483647)", "int", P_ATOM
        return super().call_rule(obj, method, args)

    def static_call(self, obj, method, args):
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        n = len(args)
        cls = obj[1] if obj[0] == "name" and not self.is_local(obj[1]) else (obj[2] if obj[0] == "member" else None)
        if cls == "JOptionPane":
            self.imports.add("from tkinter import messagebox")
            if method == "showMessageDialog" and n >= 2:
                msg = a(1) if self.ex(args[1])[1] == "str" else f"str({a(1)})"
                title = a(2) if n > 2 else '""'
                kind = self.ex(args[3])[0] if n > 3 else ""
                fn = "showerror" if "ERROR" in kind else "showwarning" if "WARNING" in kind else "showinfo"
                return f"messagebox.{fn}({title}, {msg})", None, P_ATOM
            if method == "showConfirmDialog" and n >= 2:
                title = a(2) if n > 2 else '"Select an Option"'
                return f"(0 if messagebox.askyesno({title}, {a(1)}) else 1)", "int", P_ATOM
            if method == "showInputDialog":
                self.imports.add("from tkinter import simpledialog")
                msg = a(1) if n >= 2 else a(0)
                return f"simpledialog.askstring(\"Input\", {msg})", "str", P_ATOM
        if cls == "JOptionPane" and method is None:
            return None
        if cls in ("Integer", "Long", "Short", "Byte") and method in ("parseInt", "parseLong", "valueOf", "parseShort"):
            return f"int({a(0)})", "int", P_ATOM
        if cls in ("Double", "Float") and method in ("parseDouble", "parseFloat", "valueOf"):
            return f"float({a(0)})", "float", P_ATOM
        if cls == "Boolean" and method in ("parseBoolean", "valueOf"):
            return f"({a(0)}.strip().lower() == \"true\")", "bool", P_ATOM
        if cls in ("String",) and method == "valueOf":
            return f"str({a(0)})", "str", P_ATOM
        if cls in ("Integer", "Double", "Long") and method == "toString":
            return f"str({a(0)})", "str", P_ATOM
        if cls == "System" and method == "exit":
            return "self.root.destroy()", None, P_ATOM
        if cls == "System" and method == "currentTimeMillis":
            self.imports.add("import time")
            return "int(time.time() * 1000)", "int", P_ATOM
        if obj[0] == "member" and obj[1] == ("name", "System") and obj[2] in ("out", "err") and \
                method in ("println", "print", "printf"):
            end = "" if method == "println" else ", end=\"\""
            return f"print({self.arglist(args)}{end})", None, P_ATOM
        if cls == "Math":
            mm = {"max": "max", "min": "min", "abs": "abs", "round": "round"}
            if method in mm:
                return f"{mm[method]}({self.arglist(args)})", None, P_ATOM
            if method == "random":
                self.imports.add("import random")
                return "random.random()", "float", P_ATOM
            if method in ("sqrt", "pow", "floor", "ceil", "sin", "cos", "tan", "log", "log10", "exp"):
                self.imports.add("import math")
                return f"math.{method}({self.arglist(args)})", "float", P_ATOM
        if cls == "Thread" and method == "sleep":
            self.imports.add("import time")
            return f"time.sleep({a(0)} / 1000)", None, P_ATOM
        return super().static_call(obj, method, args)

    def static_member(self, obj, prop):
        if obj[0] == "name" and obj[1] == "JOptionPane":
            return {"YES_OPTION": ("0", "int", P_ATOM), "NO_OPTION": ("1", "int", P_ATOM),
                    "OK_OPTION": ("0", "int", P_ATOM)}.get(prop, (pystr(prop), "str", P_ATOM))
        if obj[0] == "name" and obj[1] == "Color":
            return pystr(COLOR_NAMES.get(prop.lower().replace("_", ""), "")), "str", P_ATOM
        return super().static_member(obj, prop)

    def new(self, node):
        base = node[1].split("<")[0].split(".")[-1]
        if base == "Color" and len(node[2]) >= 3:
            vals = [self.ex(a)[0] for a in node[2][:3]]
            if all(re.fullmatch(r"\d+", v) for v in vals):
                return pystr("#%02X%02X%02X" % tuple(int(v) for v in vals)), "str", P_ATOM
            return f"\"#%02X%02X%02X\" % ({', '.join(vals)})", "str", P_ATOM
        if base in ("ArrayList", "Vector", "LinkedList", "DefaultListModel"):
            return "[]", "list", P_ATOM
        if base in ("HashMap", "TreeMap", "LinkedHashMap", "Hashtable"):
            return "{}", "dict", P_ATOM
        if base in ("Random",):
            self.imports.add("import random")
            return "random.Random()", "random", P_ATOM
        if base in self.forms:
            return f"{base}()", "form", P_ATOM
        return super().new(node)

    def exp(self, node):
        if node[0] == "anon":
            raise Untranslatable("anonymous class")
        return super().exp(node)


# ============================================================================ jar / decompiler
def _clean_jar(path: Path, workdir: Path) -> Path | None:
    """The jar of a .jar/.exe: rewritten without any exe prefix so every decompiler can read it."""
    if path.suffix.lower() == ".class":
        dest = workdir / "input.jar"
        with zipfile.ZipFile(dest, "w") as z:
            z.write(path, path.name)
        return dest
    try:
        src = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        for cand in [path.with_suffix(".jar"), *path.parent.glob("*.jar"), *path.parent.glob("lib/*.jar")]:
            if cand.is_file():
                return _clean_jar(cand, workdir)
        return None
    dest = workdir / (path.stem + ".jar")
    if path.suffix.lower() == ".jar" and src.namelist() and src.getinfo(src.namelist()[0]).header_offset == 0:
        src.close()
        shutil.copy2(path, dest)
        return dest
    with src, zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            out.writestr(info, src.read(info.filename))
    return dest


def find_java() -> str | None:
    java = shutil.which("java")
    if java:
        return java
    home = os.environ.get("JAVA_HOME")
    if home and (Path(home) / "bin" / "java.exe").exists():
        return str(Path(home) / "bin" / "java.exe")
    return None


def ensure_decompiler(progress=None) -> tuple[str, str] | None:
    """(name, jar path) of Vineflower or CFR; downloaded into tools/java when missing."""
    for name, _url in DECOMPILERS:
        found = find_tool(f"{name}.jar") or find_tool(name + ".jar")
        if found and found.lower().endswith(".jar"):
            return name, found
    for name, url in DECOMPILERS:
        dest = tools_dir() / "java" / f"{name}.jar"
        if download(url, dest, progress):
            return name, str(dest)
    return None


def decompile_jar(jar: Path, outdir: Path, progress=None) -> tuple[Path | None, str]:
    java = find_java()
    if not java:
        return None, "Java is not installed (install a JDK/JRE 11+, then retry)."
    dec = ensure_decompiler(progress)
    if dec is None:
        return None, "Could not download a Java decompiler (Vineflower / CFR) - check the internet connection."
    name, jarpath = dec
    outdir.mkdir(parents=True, exist_ok=True)
    say(progress, f"Decompiling {jar.name} with {name} ...")
    log = ""
    for nm, path in [dec] + [(n, find_tool(f"{n}.jar")) for n, _u in DECOMPILERS if n != name]:
        if not path:
            continue
        if nm == "vineflower":
            rc, log = run_tool([java, "-jar", path, "-dgs=1", "-log=WARN", str(jar), str(outdir)], timeout=1800)
        else:
            rc, log = run_tool([java, "-jar", path, str(jar), "--outputdir", str(outdir), "--silent", "true"],
                               timeout=1800)
        # Vineflower writes <name>.jar of sources when the input is a jar
        for z in list(outdir.glob("*.jar")) + list(outdir.glob("*.zip")):
            try:
                with zipfile.ZipFile(z) as zz:
                    for member in zz.namelist():
                        if member.endswith(".java") and ".." not in member and not member.startswith("/"):
                            target = outdir / member
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(zz.read(member))
                z.unlink()
            except zipfile.BadZipFile:
                pass
        if any(outdir.rglob("*.java")):
            return outdir, f"{nm}: {log[-400:]}"
    return None, "the decompiler produced no .java files:\n" + log[-1500:]


# ============================================================================ Swing form extraction
JCLASS_RE = re.compile(r"\b(?:public\s+|final\s+|abstract\s+|static\s+|private\s+|protected\s+)*class\s+(\w+)"
                       r"(?:<[^>]*>)?\s*(?:extends\s+([\w.<>]+))?\s*(?:implements\s+[\w.<>, ]+)?\s*\{")


def java_classes(src: str, file: Path | None) -> list[WinFormsClass]:
    out = []
    for m in JCLASS_RE.finditer(src):
        start = m.end() - 1
        end = _match_brace(src, start)
        if end > 0:
            out.append(WinFormsClass(m.group(1), (m.group(2) or "").split(".")[-1], src[start + 1:end], file))
    return out


def _literal(p_node):
    t = p_node[0]
    if t == "str":
        return p_node[1]
    if t == "num":
        try:
            return int(re.sub(r"[lLfFdD]$", "", p_node[1]))
        except ValueError:
            try:
                return float(re.sub(r"[lLfFdD]$", "", p_node[1]))
            except ValueError:
                return None
    if t == "const":
        return {"true": True, "false": False, "null": None}[p_node[1]]
    if t == "unary" and p_node[1] == "-":
        v = _literal(p_node[2])
        return -v if isinstance(v, (int, float)) else None
    return None


def _name(node):
    if node[0] == "name":
        return node[1]
    if node[0] == "member" and node[1] in (("name", "this"),):
        return node[2]
    return None


def _anon_method_body(text: str) -> str | None:
    m = re.search(r"\bvoid\s+(\w+)\s*\([^)]*\)\s*\{", text)
    if not m:
        return None
    end = _match_brace(text, m.end() - 1)
    return text[m.end():end] if end > 0 else None


def parse_swing(cls: WinFormsClass, src_text: str) -> tuple[dict, dict, list] | None:
    """Constructor / initComponents of a Swing class -> (form_dict, wiring, notes)."""
    from ...controls import CONTROL_TYPES
    methods = class_methods(cls.body)
    setup = [m for m in methods if m["name"] in (cls.name, "initComponents", "initialize", "initUI", "createUI",
                                                 "buildUI", "init", "setupUI", "$$$setupUI$$$")]
    if not setup:
        return None
    notes: list[str] = []
    ctrls: dict[str, dict] = {}
    order: list[str] = []
    menus: dict[str, dict] = {}
    menubar_items: list[str] = []
    form = {"Text": cls.name, "Width": 400, "Height": 300}
    wiring: dict[str, object] = {}
    scroll_of: dict[str, str] = {}          # JScrollPane -> wrapped control
    centred = False
    resizable = True

    def handle(st):
        nonlocal centred, resizable
        if st[0] == "decl":
            for name, init in st[2]:
                if init is not None:
                    handle(("expr", ("assign", "=", ("name", name), init), ""))
            return
        if st[0] in ("block",):
            for x in st[1]:
                handle(x)
            return
        if st[0] != "expr":
            return
        e = st[1]
        if e[0] == "assign" and e[1] == "=" and e[3][0] == "new":
            name = _name(e[2])
            typ = e[3][1].split("<")[0].split(".")[-1]
            args = [_literal(a) for a in e[3][2]]
            if name is None:
                return
            if typ in MENU_TYPES:
                menus[name] = {"Name": name, "Text": next((a for a in args if isinstance(a, str)), name),
                               "Items": []}
            elif typ == "JScrollPane":
                inner = _name(e[3][2][0]) if e[3][2] else None
                ctrls[name] = {"type": "__scroll", "props": {}, "parent": "", "inner": inner}
                if inner:
                    scroll_of[name] = inner
            elif typ in SWING_TYPES:
                ctrls[name] = {"type": typ, "props": {}, "parent": "", "args": args}
                order.append(name)
                if typ == "Timer" and e[3][2]:
                    ctrls[name]["props"]["Interval"] = args[0] if isinstance(args[0], int) else 100
                    if len(e[3][2]) > 1:
                        wire(name, "Tick", e[3][2][1])
            elif typ in ("JSeparator",) and False:
                pass
            return
        if e[0] != "call":
            return
        func, args = e[1], e[2]
        if func[0] == "name":
            obj, method = ("name", "this"), func[1]
        elif func[0] == "member":
            obj, method = func[1], func[2]
        else:
            return
        lits = [_literal(a) for a in args]
        # getContentPane().add(x) / add(x) / panel.add(x)
        recv = _name(obj) if obj not in (("name", "this"), ("name", "super")) else "__form"
        if obj[0] == "call" and obj[1][0] in ("name", "member") and \
                (obj[1][-1] if obj[1][0] == "name" else obj[1][2]) == "getContentPane":
            recv = "__form"
        if recv is None:
            return
        if method == "add" and args:
            child = _name(args[0])
            if child is None:
                return
            if recv in menus:
                menus[recv]["Items"].append(child)
            elif recv in ctrls and ctrls[recv]["type"] == "JMenuBar":
                menubar_items.append(child)
            elif child in menus and recv == "__form":
                menubar_items.append(child)
            elif child in ctrls:
                target = child
                if ctrls[child]["type"] == "__scroll" and ctrls[child].get("inner") in ctrls:
                    inner = ctrls[child]["inner"]
                    ctrls[inner]["props"].update(ctrls[child]["props"])
                    target = inner
                    ctrls[inner]["parent"] = "" if recv == "__form" else recv
                if recv != "__form" and recv in ctrls and ctrls[recv]["type"] == "JTabbedPane":
                    title = lits[0] if isinstance(lits[0], str) else None
                    if len(args) == 2 and isinstance(_literal(args[0]), str):
                        child = _name(args[1])
                        target = child
                        title = _literal(args[0])
                    ctrls[recv].setdefault("tabs", []).append(title or child)
                    if target in ctrls:
                        ctrls[target]["parent"] = recv
                        ctrls[target]["tab"] = len(ctrls[recv]["tabs"]) - 1
                    return
                if target in ctrls and target != child:
                    return
                ctrls[child]["parent"] = "" if recv == "__form" else recv
            return
        if method == "addTab" and recv in ctrls and len(args) >= 2:
            child = _name(args[1])
            ctrls[recv].setdefault("tabs", []).append(lits[0] if isinstance(lits[0], str) else child)
            if child in ctrls:
                ctrls[child]["parent"] = recv
                ctrls[child]["tab"] = len(ctrls[recv]["tabs"]) - 1
            return
        if method == "setJMenuBar":
            mb = _name(args[0]) if args else None
            if mb in ctrls:
                ctrls[mb]["parent"] = ""
            return
        if method == "setViewportView" and recv in ctrls and args:
            inner = _name(args[0])
            ctrls[recv]["inner"] = inner
            return
        if method in LISTENER_EVENT and args:
            wire(recv, LISTENER_EVENT[method], args[0])
            return
        target = ctrls.get(recv) if recv != "__form" else None
        if recv == "__form":
            if method == "setTitle" and isinstance(lits[0], str):
                form["Text"] = lits[0]
            elif method == "setSize" and len(lits) == 2 and all(isinstance(x, int) for x in lits):
                form["Width"], form["Height"] = max(120, lits[0] - 16), max(80, lits[1] - 39)
            elif method == "setBounds" and len(lits) == 4 and all(isinstance(x, int) for x in lits):
                form["Width"], form["Height"] = max(120, lits[2] - 16), max(80, lits[3] - 39)
            elif method == "setLocationRelativeTo":
                centred = True
            elif method == "setResizable" and lits and lits[0] is False:
                resizable = False
            elif method == "setBackground" and args:
                form["BackColor"] = _color_of(args[0])
            return
        if recv in menus:
            if method == "setText" and isinstance(lits[0], str):
                menus[recv]["Text"] = lits[0]
            return
        if target is None:
            return
        pr = target["props"]
        if method == "setBounds" and len(lits) == 4 and all(isinstance(x, int) for x in lits):
            pr["Left"], pr["Top"], pr["Width"], pr["Height"] = lits
        elif method == "setLocation" and len(lits) == 2:
            pr["Left"], pr["Top"] = lits
        elif method == "setSize" and len(lits) == 2:
            pr["Width"], pr["Height"] = lits
        elif method in ("setText", "setLabel") and isinstance(lits[0], str):
            pr["Text"] = lits[0]
        elif method == "setFont" and args and args[0][0] == "new":
            fa = args[0][2]
            fl = [_literal(a) for a in fa]
            if fl and isinstance(fl[0], str):
                pr["FontName"] = fl[0]
            if len(fl) > 2 and isinstance(fl[2], int):
                pr["FontSize"] = int(round(fl[2] * 0.75)) or 9
            style = "".join(str(a) for a in fa[1:2])
            pr["FontBold"] = "BOLD" in style
            pr["FontItalic"] = "ITALIC" in style
        elif method in ("setForeground", "setBackground") and args:
            col = _color_of(args[0])
            if col:
                pr["ForeColor" if method == "setForeground" else "BackColor"] = col
        elif method in ("setEnabled", "setVisible", "setSelected", "setEditable") and isinstance(lits[0], bool):
            key = {"setEnabled": "Enabled", "setVisible": "Visible", "setSelected": "Checked",
                   "setEditable": "ReadOnly"}[method]
            pr[key] = (not lits[0]) if key == "ReadOnly" else lits[0]
        elif method == "setToolTipText" and isinstance(lits[0], str):
            pr["ToolTip"] = lits[0]
        elif method in ("addItem",) and lits and isinstance(lits[0], str):
            pr.setdefault("__items", []).append(lits[0])
        elif method in ("setMaximum", "setMinimum", "setValue") and isinstance(lits[0], int):
            pr[method[3:]] = lits[0]
        elif method == "setDelay" and isinstance(lits[0], int):
            pr["Interval"] = lits[0]
        elif method == "setModel" and args and args[0][0] == "new":
            items = []
            for a in args[0][2]:
                if a[0] == "newarr":
                    items += [_literal(x) for x in a[3] or []]
            if items:
                pr["__items"] = [str(x) for x in items if x is not None]

    def wire(owner: str, event: str, listener):
        if owner is None:
            return
        body = None
        if listener[0] == "lambda":
            b = listener[2]
            body = ("block", b) if b[0] == "block" else b
            src = _src_of(listener)
            body_src = src if src else None
            if body_src is None:
                return
        elif listener[0] == "anon":
            body_src = _anon_method_body(listener[3])
        elif listener[0] == "member" and listener[1] in (("name", "this"),):      # this::onClick
            body_src = f"{listener[2]}();"
        elif listener[0] == "name" and listener[1] == "this":
            notes.append(f"{cls.name}: {owner} listener is the frame itself (implements ...Listener) - "
                         "see actionPerformed in the code")
            return
        else:
            return
        del body
        if body_src is None:
            return
        wiring[(owner, event)] = body_src

    def _src_of(lam):
        """Source text of a lambda's body (from the original text, found by position)."""
        return lam_sources.get(id(lam))

    lam_sources: dict[int, str] = {}
    for m in setup:
        try:
            p = Parser(m["body"], java=True)
            stmts = p.statements()
        except ParseError:
            continue
        _collect_lambdas(stmts, m["body"], p, lam_sources)
        for st in stmts:
            handle(st)

    # ---- neutral controls
    controls = []
    no_bounds = 0
    y = 12
    for n in order:
        c = ctrls[n]
        nt = SWING_TYPES[c["type"]]
        ct = CONTROL_TYPES[nt]
        props = ct.default_props(n)
        args = c.get("args") or []
        pr = c["props"]
        text = pr.get("Text", next((a for a in args if isinstance(a, str)), None))
        if text is not None and "Text" in props:
            props["Text"] = text
        elif "Text" in props and nt in ("TextBox", "ComboBox"):
            props["Text"] = ""
        if c["type"] == "JPasswordField":
            props["PasswordChar"] = "*"
        if c["type"] in ("JTextArea", "TextArea", "JTextPane", "JEditorPane"):
            props["Multiline"] = True
        if nt == "MenuStrip":
            items = []
            for mn in menubar_items:
                items.append(_menu_item(mn, menus))
            props["Items"] = items
            controls.append({"type": nt, "props": props})
            continue
        if nt == "Timer":
            props["Interval"] = int(pr.get("Interval", 100) or 100)
            controls.append({"type": nt, "props": props})
            continue
        if "Left" in pr:
            for k in ("Left", "Top", "Width", "Height"):
                if isinstance(pr.get(k), int):
                    props[k] = pr[k]
        else:
            no_bounds += 1
            props["Left"], props["Top"] = 12, y
            y += props["Height"] + 8
        for k in ("FontName", "FontSize", "FontBold", "FontItalic", "ForeColor", "BackColor", "Enabled", "Visible",
                  "Checked", "ReadOnly", "ToolTip", "Minimum", "Maximum", "Value"):
            if k in pr and k in props:
                props[k] = pr[k]
        if pr.get("__items") and "Items" in props:
            props["Items"] = ";".join(pr["__items"])
        if nt == "TabControl" and c.get("tabs"):
            props["TabPages"] = ";".join(str(t) for t in c["tabs"])
        parent = c.get("parent") or ""
        if parent in ctrls and ctrls[parent]["type"] in SWING_TYPES and parent in order:
            props["Parent"] = parent
            if "tab" in c:
                props["TabPage"] = c["tab"]
        controls.append({"type": nt, "props": props})
    if menubar_items and not any(c["type"] == "MenuStrip" for c in controls):
        controls.append({"type": "MenuStrip", "props": {**CONTROL_TYPES["MenuStrip"].default_props("menuBar1"),
                                                        "Items": [_menu_item(mn, menus) for mn in menubar_items]}})
    if no_bounds:
        notes.append(f"{cls.name}: {no_bounds} control(s) placed by a layout manager - positions approximated "
                     "(stacked); arrange them in the designer")
        form["Height"] = max(form["Height"], y + 12)
    form_props = {"Name": cls.name, "Text": form["Text"], "Width": form["Width"], "Height": form["Height"],
                  "StartPosition": "CenterScreen"}
    if not resizable:
        form_props["FormBorderStyle"] = "FixedSingle"
    if form.get("BackColor"):
        form_props["BackColor"] = form["BackColor"]

    # ---- events -> neutral handler names
    types = {c["props"]["Name"]: c["type"] for c in controls}
    out_wiring: dict[str, object] = {}
    for (owner, event), body_src in wiring.items():
        if owner == "__form":
            handler = f"{cls.name}_{'FormClosing' if event == 'FormClosing' else 'Load'}"
            if event != "FormClosing":
                continue
        elif owner in menus:
            handler = f"{owner}_Click"
        elif owner in types:
            ev = EVENT_FOR_TYPE.get((event, types[owner]), event)
            if ev is None:
                notes.append(f"{cls.name}.{owner}: {event} listener on a {types[owner]} has no RAD IDE event")
                continue
            handler = f"{owner}_{ev}"
        else:
            continue
        out_wiring[handler] = ("inline", body_src)
    return {"version": 2, "props": form_props, "controls": controls}, out_wiring, notes


def _menu_item(name: str, menus: dict, depth: int = 0) -> dict:
    m = menus.get(name, {"Text": name, "Items": []})
    item = {"Text": m.get("Text", name), "Name": name}
    if m.get("Items") and depth < 6:
        item["Items"] = [_menu_item(x, menus, depth + 1) for x in m["Items"]]
    return item


def _color_of(node) -> str:
    if node[0] == "member" and node[1] == ("name", "Color"):
        return COLOR_NAMES.get(node[2].lower().replace("_", ""), "")
    if node[0] == "new" and node[1].split(".")[-1] == "Color":
        vals = [_literal(a) for a in node[2][:3]]
        if len(vals) == 3 and all(isinstance(v, int) for v in vals):
            return "#%02X%02X%02X" % tuple(vals)
    return ""


def _collect_lambdas(stmts, text: str, parser: Parser, out: dict) -> None:
    """Map each lambda node to the source text of its body (needed to re-translate it later)."""
    # lambdas keep their parsed body; re-create source from tokens is not possible, so we take the text
    # between '->' and the end of the argument from the original method body.
    for m in re.finditer(r"(?:\([^()]*\)|\b\w+)\s*->\s*", text):
        start = m.end()
        if start < len(text) and text[start] == "{":
            end = _match_brace(text, start)
            body = text[start + 1:end]
        else:
            depth, j = 0, start
            while j < len(text):
                ch = text[j]
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                elif ch == ";" and depth == 0:
                    break
                j += 1
            body = text[start:j].strip() + ";"
        out.setdefault("__order", []).append(body)

    order = list(out.get("__order", []))

    def walk(node):
        if isinstance(node, tuple):
            if node and node[0] == "lambda":
                if order:
                    out[id(node)] = order.pop(0)
            for x in node:
                walk(x)
        elif isinstance(node, list):
            for x in node:
                walk(x)
    walk(stmts)
    out.pop("__order", None)


# ============================================================================ backend API
def can_handle(info: BinaryInfo) -> bool:
    return getattr(info, "kind", "") == "java"


def run(path, info: BinaryInfo, workdir, progress=None, ai_translate: bool = False) -> ImportResult:
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    say(progress, "Looking for the Java archive ...")
    jar = _clean_jar(path, workdir)
    if jar is None:
        res.add("error", "No Java archive found in the program (the wrapper may download or unpack it at run time).")
        return res
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace") if "META-INF/MANIFEST.MF" in names \
            else ""
    main = re.search(r"^Main-Class:\s*(\S+)", manifest, re.M)
    res.resources["main_class"] = main.group(1) if main else ""
    res.resources["jar"] = str(jar)
    classes = sum(1 for n in names if n.endswith(".class"))
    res.add("info", f"Java archive: {classes} class file(s)" + (f", main class {main.group(1)}" if main else ""))
    src_dir, log = decompile_jar(jar, workdir / "java", progress)
    if src_dir is None:
        res.add("error", log)
        return res
    res.source_dir = src_dir
    files = sorted(src_dir.rglob("*.java"))
    res.add("exact", f"Decompiled to {len(files)} Java source file(s) ({log.split(':')[0]}) - kept in _original.")
    # resources (images, properties) of the jar
    res.resources["files"] = [n for n in names if not n.endswith((".class", "/")) and not n.startswith("META-INF")][:200]
    return convert_java_tree(src_dir, res, progress, ai_translate)


def convert_java_tree(src_dir: Path, res: ImportResult, progress=None, ai_translate: bool = False,
                      language: str = "python-tk") -> ImportResult:
    classes: list[tuple[WinFormsClass, str]] = []
    for f in sorted(src_dir.rglob("*.java")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for c in java_classes(text, f):
            classes.append((c, text))
    frames = [(c, t) for c, t in classes if c.base in FRAME_BASES or
              re.search(r"\bnew\s+(JButton|JLabel|JTextField|Button|Label)\b", c.body)]
    all_forms = {c.name for c, _t in frames}
    main_cls = (res.resources.get("main_class") or "").split(".")[-1]
    frames.sort(key=lambda ct: (ct[0].name != main_cls, ct[0].base not in ("JFrame", "Frame")))
    total_t = total_u = 0
    for cls, text in frames:
        say(progress, f"Reading Swing frame {cls.name} ...")
        try:
            parsed = parse_swing(cls, text)
        except Exception as e:  # noqa: BLE001
            res.add("warn", f"{cls.name}: the window layout could not be read ({e})")
            continue
        if parsed is None or not parsed[0]["controls"]:
            continue
        form_dict, wiring, notes = parsed
        for n in notes:
            res.add("warn", n)
        res.forms.append((cls.name, form_dict))
        res.add("exact" if not any("approximated" in n for n in notes) else "rules",
                f"Form {cls.name}: {len(form_dict['controls'])} control(s) and {len(wiring)} listener(s) from the "
                "Swing code.")
        setup_names = {"initComponents", "initialize", "initUI", "createUI", "buildUI", "setupUI", "$$$setupUI$$$",
                       "main", cls.name}
        try:
            tr = translate_form_class(cls, form_dict, wiring, all_forms, language, SwingEmitter, setup_names,
                                      java=True)
        except Exception as e:  # noqa: BLE001
            res.add("error", f"{cls.name}: code translation failed ({e}); the Java stays in _original.")
            continue
        t, u = tr["stats"]
        total_t += t
        total_u += u
        code = tr["code"]
        if ai_translate and u:
            ctx = ("Target: a python-tk RAD IDE form class (controls are self.<Name>; TextBox text "
                   "self.<Name>_var). Return the whole class file. Original Java:\n" + text[:12000])
            new, who = ai_rewrite(code, "partly translated Python (Java lines in comments)", ctx, progress)
            if new and f"class {cls.name}" in new:
                try:
                    compile(new, cls.name, "exec")
                    code = new
                    res.add("ai", f"{cls.name}: untranslated lines rewritten by AI ({who}).")
                except SyntaxError:
                    res.add("warn", f"{cls.name}: the AI answer did not compile; rules kept.")
            else:
                res.add("warn", f"{cls.name}: AI translation not used - {who}")
        set_form_code(res, cls.name, code, language, tr["handlers"])
        done = [m for m, s in tr["methods"] if s == "rules"]
        part = [m for m, s in tr["methods"] if s == "partial"]
        if done:
            res.add("rules", f"{cls.name}: translated to Python by rules: " + ", ".join(done))
        if part:
            res.add("missing", f"{cls.name}: lines kept as '# Java:' comments in " + ", ".join(part))
    if not frames:
        res.add("missing", "No Swing/AWT window found - the Java sources are in _original (console program or "
                           "another GUI toolkit such as JavaFX/SWT).")
    for c, text in classes[:60]:
        if c.name not in all_forms and c.file is not None:
            rel = c.file.relative_to(src_dir).as_posix()
            if not any(m[0] == rel for m in res.modules):
                res.modules.append((rel, text, "java"))
    set_startup(res, res.forms[0][0] if res.forms else "")
    res.resources["form_code_language"] = language
    res.resources["translation_stats"] = {"statements_translated": total_t, "statements_commented": total_u}
    return res
