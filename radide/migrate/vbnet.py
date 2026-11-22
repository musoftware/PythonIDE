"""VB.NET WinForms (Form1.vb + Form1.Designer.vb) -> neutral forms, and VB.NET code -> VB6 by rules.

* Forms: the designer's InitializeComponent is rewritten line by line into C# syntax and read by the
  WinForms parser of the .exe importer (radide/importers/exe/dotnet.parse_winforms), so C# and VB.NET forms
  give exactly the same .form model.  ``Handles X.Event`` clauses become the event wiring.
* Code: VB.NET statements that VB6 does not have (Dim x As T = v, +=, Return, MessageBox.Show,
  .Items.Add, .Checked, x.ToString("0.0"), $"..{x}..", Try/Catch, AndAlso, For i As Integer ...) are rewritten
  as VB6.  The VB6 text runs on the bundled VB6 interpreter (vb-basic target) and is also the input of the
  VB6 -> Python translator (python-tk / python-qt targets).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .vbcommon import Notes, read_text

# WinForms event -> neutral event (same names as the RAD IDE controls)
EVENT_NEUTRAL = {"Click": "Click", "DoubleClick": "DoubleClick", "TextChanged": "TextChanged",
                 "CheckedChanged": "CheckedChanged", "SelectedIndexChanged": "SelectedIndexChanged",
                 "ValueChanged": "ValueChanged", "Tick": "Tick", "Load": "Load", "Shown": "Load",
                 "FormClosing": "FormClosing", "FormClosed": "FormClosed", "Resize": "Resize",
                 "Activated": "Activated", "Deactivate": "Deactivate", "KeyDown": "KeyDown", "KeyUp": "KeyUp",
                 "KeyPress": "KeyPress", "MouseDown": "MouseDown", "MouseUp": "MouseUp", "MouseMove": "MouseMove",
                 "MouseEnter": "MouseEnter", "MouseLeave": "MouseLeave", "Enter": "GotFocus", "Leave": "LostFocus",
                 "GotFocus": "GotFocus", "LostFocus": "LostFocus", "Scroll": "ValueChanged"}


# ============================================================================ designer: VB -> C# syntax
def _vb_value_to_cs(v: str) -> str:
    out, i = [], 0
    while i < len(v):
        ch = v[i]
        if ch == '"':
            j = i + 1
            buf = ""
            while j < len(v):
                if v[j] == '"':
                    if j + 1 < len(v) and v[j + 1] == '"':
                        buf += '\\"'
                        j += 2
                        continue
                    break
                buf += "\\\\" if v[j] == "\\" else v[j]
                j += 1
            out.append('"' + buf + '"')
            if j + 1 < len(v) and v[j + 1] in "cC":        # "x"c char literal
                j += 1
            i = j + 1
            continue
        out.append(ch)
        i += 1
    s = "".join(out)
    # outside strings only (strings are already C#): split on string literals
    parts = re.split(r'("(?:[^"\\]|\\.)*")', s)
    for k in range(0, len(parts), 2):
        p = parts[k]
        p = re.sub(r"\bGlobal\.", "", p)
        p = re.sub(r"\bMe\.", "this.", p)
        p = re.sub(r"\bMyBase\.", "base.", p)
        p = re.sub(r"\bTrue\b", "true", p)
        p = re.sub(r"\bFalse\b", "false", p)
        p = re.sub(r"\bNothing\b", "null", p)
        p = re.sub(r"\bOr\b", "|", p)
        p = re.sub(r"\bAnd\b", "&", p)
        p = re.sub(r"&H([0-9A-Fa-f]+)&?", r"0x\1", p)
        p = re.sub(r"(\d+(?:\.\d+)?)!", r"\1F", p)
        p = re.sub(r"(\d+(?:\.\d+)?)R\b", r"\1", p)
        p = re.sub(r"(\d+(?:\.\d+)?)D\b", r"\1M", p)
        p = re.sub(r"\bCType\(", "CType(", p)
        p = re.sub(r"\bNew\s+([\w.]+)\s*\(\)\s*\{", r"new \1[] {", p)
        p = re.sub(r"\bNew\s+", "new ", p)
        p = re.sub(r"\bObject\[\]", "object[]", p)
        parts[k] = p
    s = "".join(parts)
    # CType(x, T) -> ((T)(x))
    while True:
        m = re.search(r"\bCType\(", s)
        if not m:
            break
        depth, j, comma = 1, m.end(), -1
        while j < len(s) and depth:
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
            elif s[j] == "," and depth == 1:
                comma = j
            j += 1
        if comma < 0:
            break
        x, t = s[m.end():comma].strip(), s[comma + 1:j - 1].strip()
        s = s[:m.start()] + f"(({t})({x}))" + s[j:]
    return s


def designer_vb_to_cs(ic_body: str) -> str:
    """Body of a VB.NET InitializeComponent -> C# statements."""
    out = []
    for raw in ic_body.replace("\r\n", "\n").split("\n"):
        s = raw.strip()
        if not s or s.startswith("'"):
            continue
        m = re.match(r"AddHandler\s+(.+?),\s*AddressOf\s+(.+)$", s, re.I)
        if m:
            out.append(f"{_vb_value_to_cs(m.group(1))} += new System.EventHandler({_vb_value_to_cs(m.group(2))});")
            continue
        out.append(_vb_value_to_cs(s) + ";")
    return "\n".join(out)


# ============================================================================ VB.NET code structure
@dataclass
class VbMethod:
    name: str
    kind: str              # sub | function
    params: str
    ret: str
    handles: list          # ["btnConvert.Click", "MyBase.Load"]
    body: list             # [(line number in the file, text)]
    line: int
    modifiers: str = ""


@dataclass
class VbClass:
    name: str
    base: str = ""
    fields: list = field(default_factory=list)     # [(line, text)]
    methods: list = field(default_factory=list)
    designer_ic: str = ""
    file: str = ""
    other: list = field(default_factory=list)      # [(line, text)] not understood (properties, nested types)


_METHOD_RX = re.compile(r"^\s*((?:(?:Public|Private|Protected|Friend|Shared|Overrides|Overridable|Overloads|"
                        r"Async|Static|Shadows|NotOverridable|MustOverride)\s+)*)(Sub|Function)\s+(\w+)\s*"
                        r"(?:\((.*)\))?\s*(?:As\s+([\w.()]+(?:\(Of [^)]*\))?))?\s*(?:Handles\s+(.+))?$", re.I)


def parse_vb_classes(text: str, file: str = "") -> list[VbClass]:
    """Classes of a VB.NET file with their methods (bodies as numbered lines)."""
    lines = text.replace("\r\n", "\n").split("\n")
    classes: list[VbClass] = []
    cur: VbClass | None = None
    meth: VbMethod | None = None
    depth_prop = 0
    i = 0
    while i < len(lines):
        raw = lines[i]
        ln = i + 1
        s = raw.strip()
        # line continuation " _"
        while s.endswith(" _") and i + 1 < len(lines):
            i += 1
            s = s[:-2] + " " + lines[i].strip()
        i += 1
        # leading attributes (classic VS designer: "<DesignerGenerated()> _ Partial Class X",
        # "<DebuggerStepThrough()> _ Private Sub InitializeComponent()") - and a BOM on line 1
        s = re.sub(r"^﻿?\s*(?:<[^<>]*>\s*)+(?=\S)", "", s.lstrip("﻿"))
        low = s.lower()
        if cur is None:
            m = re.match(r"^(?:(?:Public|Private|Friend|Partial|NotInheritable|MustInherit)\s+)*(?:Class|Module)\s+"
                         r"(\w+)", s, re.I)
            if m:
                cur = VbClass(m.group(1), file=file)
                if "module " in low.split("'")[0] and "class " not in low:
                    cur.base = "Module"
            continue
        if meth is not None:
            if re.match(r"^End\s+(Sub|Function)\b", s, re.I):
                cur.methods.append(meth)
                meth = None
            else:
                meth.body.append((ln, raw))
            continue
        if depth_prop:
            cur.other.append((ln, raw))
            if re.match(r"^End\s+(Property|Enum|Structure|Class|Event)\b", s, re.I):
                depth_prop -= 1
            continue
        if re.match(r"^End\s+(Class|Module)\b", s, re.I):
            classes.append(cur)
            cur = None
            continue
        m = re.match(r"^Inherits\s+([\w.]+)", s, re.I)
        if m:
            cur.base = m.group(1)
            continue
        if not s or s.startswith("'") or s.startswith("<") and s.endswith(">") or s.startswith("#"):
            continue
        m = _METHOD_RX.match(s.split(" '")[0] if " '" in s else s)
        if m and not re.search(r"\bDeclare\b", s, re.I) and not re.match(r".*\b(Event|Delegate)\b", s, re.I):
            meth = VbMethod(m.group(3), m.group(2).lower(), m.group(4) or "", m.group(5) or "",
                            [h.strip() for h in (m.group(6) or "").split(",") if h.strip()], [], ln,
                            m.group(1) or "")
            if re.search(r"\bMustOverride\b", s, re.I):
                cur.methods.append(meth)
                meth = None
            continue
        if re.match(r"^(?:(?:Public|Private|Protected|Friend|Shared|ReadOnly|WriteOnly|Default|Overrides)\s+)*"
                    r"(Property|Enum|Structure|Class)\b", s, re.I) and not re.search(r"\bProperty\b.*\)\s*As\s+\w+\s*=",
                                                                                     s, re.I):
            if re.match(r".*\bProperty\b", s, re.I) and not re.search(r"\b(Get|Set)\b", s, re.I) and \
                    re.search(r"\bAuto\b|=|As\s+\w+\s*$", s, re.I) and "ReadOnly" not in s:
                cur.fields.append((ln, s))           # auto-implemented property
                continue
            cur.other.append((ln, raw))
            depth_prop += 1
            continue
        cur.fields.append((ln, s))
    if cur is not None:
        classes.append(cur)
    return classes


def load_vb_form(code_file: Path, designer_file: Path | None) -> tuple[VbClass | None, dict | None, dict, list]:
    """(class, form_dict, wiring {neutral handler: method}, notes) of one VB.NET form."""
    from ..importers.exe import dotnet
    code = read_text(code_file)
    classes = parse_vb_classes(code, code_file.name)
    designer = read_text(designer_file) if designer_file and designer_file.exists() else ""
    dclasses = parse_vb_classes(designer, designer_file.name) if designer else []
    if not classes and not dclasses:
        return None, None, {}, ["no class found"]
    main = classes[0] if classes else dclasses[0]
    ic = None
    for c in dclasses + classes:
        if c.name == main.name:
            for m in c.methods:
                if m.name.lower() == "initializecomponent":
                    ic = m
            if c.base and not main.base:
                main.base = c.base
    if ic is None:
        return main, None, {}, [f"{main.name}: no InitializeComponent (not a designer form)"]
    main.designer_ic = "\n".join(t for _l, t in ic.body)
    main.methods = [m for m in main.methods if m.name.lower() != "initializecomponent"]
    cs_body = designer_vb_to_cs(main.designer_ic)
    fake = dotnet.WinFormsClass(main.name, main.base or "Form", "private void InitializeComponent() {\n" +
                                cs_body + "\n}\n", designer_file or code_file)
    parsed = dotnet.parse_winforms(fake, {main.name})
    if parsed is None:
        return main, None, {}, [f"{main.name}: InitializeComponent could not be read"]
    form_dict, wiring, notes = parsed
    ctl_names = {c["props"]["Name"].lower(): c["props"]["Name"] for c in form_dict["controls"]}
    for m in main.methods:
        for h in m.handles:
            owner, _, ev = h.rpartition(".")
            neutral = EVENT_NEUTRAL.get(ev)
            if neutral is None:
                notes.append(f"{m.name}: event {h} has no RAD IDE equivalent")
                continue
            if owner.lower() in ("mybase", "me", main.name.lower()):
                wiring[f"{main.name}_{neutral}"] = m.name
            elif owner.lower() in ctl_names:
                wiring[f"{ctl_names[owner.lower()]}_{neutral}"] = m.name
            else:
                notes.append(f"{m.name}: Handles {h} - unknown control")
    return main, form_dict, wiring, notes


# ============================================================================ VB.NET -> VB6 code
_MB_BUTTONS = {"ok": "vbOKOnly", "okcancel": "vbOKCancel", "yesno": "vbYesNo", "yesnocancel": "vbYesNoCancel",
               "retrycancel": "vbRetryCancel", "abortretryignore": "vbAbortRetryIgnore"}
_MB_ICON = {"warning": "vbExclamation", "exclamation": "vbExclamation", "error": "vbCritical", "stop": "vbCritical",
            "hand": "vbCritical", "information": "vbInformation", "asterisk": "vbInformation",
            "question": "vbQuestion", "none": ""}
_NET_FMT = {"F": "0.", "N": "#,##0.", "P": "0.", "C": "$#,##0."}


def _split_args(s: str) -> list[str]:
    out, depth, cur, q = [], 0, "", False
    for ch in s:
        if ch == '"':
            q = not q
        if not q:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
                continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _close_paren(s: str, i: int) -> int:
    """Index of the ) matching the ( at s[i]."""
    depth, q = 0, False
    for j in range(i, len(s)):
        ch = s[j]
        if ch == '"':
            q = not q
        elif not q:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return j
    return -1


def _receiver_start(s: str, dot: int) -> int:
    """Start of the expression before s[dot] == '.' (identifier chain or parenthesised expression)."""
    j = dot - 1
    while True:
        if j >= 0 and s[j] == ")":
            depth, q = 0, False
            while j >= 0:
                ch = s[j]
                if ch == '"':
                    q = not q
                elif not q:
                    if ch == ")":
                        depth += 1
                    elif ch == "(":
                        depth -= 1
                        if depth == 0:
                            break
                j -= 1
            j -= 1
            continue
        if j >= 0 and s[j] == '"':
            j -= 1
            while j >= 0 and s[j] != '"':
                j -= 1
            j -= 1
            continue
        k = j
        while k >= 0 and (s[k].isalnum() or s[k] in "_."):
            k -= 1
        if k == j:
            return j + 1
        j = k
        if j >= 0 and s[j] == ")":
            continue
        return j + 1


def _net_format(fmt: str) -> str:
    """.NET numeric format ("F2", "N0", "0.00") -> VB6 Format string."""
    m = re.fullmatch(r"([FfNnPpCcDd])(\d*)", fmt)
    if not m:
        return fmt
    k, n = m.group(1).upper(), int(m.group(2) or (2 if m.group(1).upper() in "FNPC" else 0))
    if k == "D":
        return "0" * max(1, n)
    base = _NET_FMT[k]
    out = (base + "0" * n) if n else base.rstrip(".")
    return out + ("%" if k == "P" else "")


class VbNetToVb6:
    """Rewrite VB.NET method bodies as VB6 (statement by statement, keeping comments)."""

    def __init__(self, controls: dict, form_name: str, file: str, notes: Notes, methods: set | None = None):
        self.controls = {k.lower(): v for k, v in controls.items()}   # lower name -> neutral type
        self.form = form_name
        self.file = file
        self.notes = notes
        self.methods = {m.lower() for m in (methods or set())}
        self.tmp = 0

    def note(self, level, line, text):
        self.notes.add(level, self.file, line, text)

    # ------------------------------------------------------------------ expressions
    def expr(self, s: str, line: int) -> str:
        if not s:
            return s
        s = self._interp(s, line)
        parts = re.split(r'("(?:[^"]|"")*"c?)', s)
        for k in range(0, len(parts), 2):
            parts[k] = self._expr_code(parts[k], line)
        s = "".join(p[:-1] if p.endswith('"c') and p.startswith('"') else p for p in parts)
        s = self._methods(s, line)
        return s

    def _expr_code(self, p: str, line: int) -> str:
        p = re.sub(r"\bAndAlso\b", "And", p)
        p = re.sub(r"\bOrElse\b", "Or", p)
        p = re.sub(r"(\w[\w.()]*)\s+IsNot\s+Nothing", r"Not \1 Is Nothing", p)
        p = re.sub(r"\bIsNot\b", "<>", p)
        p = re.sub(r"\bControlChars\.CrLf\b|\bEnvironment\.NewLine\b|\bControlChars\.NewLine\b", "vbCrLf", p)
        p = re.sub(r"\bControlChars\.Tab\b", "vbTab", p)
        p = re.sub(r"\bControlChars\.Lf\b", "vbLf", p)
        p = re.sub(r"\bControlChars\.Cr\b", "vbCr", p)
        p = re.sub(r"\bControlChars\.Quote\b", 'Chr(34)', p)
        p = re.sub(r"\b(?:DateTime|Date)\.Now\b", "Now", p)
        p = re.sub(r"\b(?:DateTime|Date)\.Today\b", "Date", p)
        p = re.sub(r"\bMath\.PI\b", "3.14159265358979", p)
        p = re.sub(r"\bString\.Empty\b", '""', p)
        p = re.sub(r"\bDialogResult\.(Yes|No|OK|Cancel|Retry|Abort|Ignore)\b",
                   lambda m: "vb" + {"OK": "OK"}.get(m.group(1), m.group(1)), p)
        p = re.sub(r"\bMessageBoxButtons\.(\w+)", lambda m: _MB_BUTTONS.get(m.group(1).lower(), "vbOKOnly"), p)
        p = re.sub(r"\bMessageBoxIcon\.(\w+)", lambda m: _MB_ICON.get(m.group(1).lower(), "") or "0", p)
        p = re.sub(r"\bMe\.Text\b", "Me.Caption", p)
        p = re.sub(r"\bDirectCast\(([^,]+),\s*[\w.]+\)", r"\1", p)
        p = re.sub(r"\bCType\(([^,]+),\s*(Integer|Short|Long|Byte)\)", r"CInt(\1)", p)
        p = re.sub(r"\bCType\(([^,]+),\s*(Double|Single|Decimal)\)", r"CDbl(\1)", p)
        p = re.sub(r"\bCType\(([^,]+),\s*String\)", r"CStr(\1)", p)
        p = re.sub(r"\b(?:Integer|Int32|Long|Int64|Short)\.Parse\(", "CInt(", p)
        p = re.sub(r"\bConvert\.ToInt(?:16|32|64)\(", "CInt(", p)
        p = re.sub(r"\b(?:Double|Single|Decimal)\.Parse\(", "CDbl(", p)
        p = re.sub(r"\bConvert\.To(?:Double|Single|Decimal)\(", "CDbl(", p)
        p = re.sub(r"\bConvert\.ToString\(", "CStr(", p)
        p = re.sub(r"\bString\.IsNullOrEmpty\(([^()]+)\)", r"(Len(\1) = 0)", p)
        p = re.sub(r"\bMath\.Round\(", "Round(", p)
        p = re.sub(r"\bMath\.Abs\(", "Abs(", p)
        p = re.sub(r"\bMath\.Sqrt\(", "Sqr(", p)
        p = re.sub(r"\bMath\.Floor\(", "Int(", p)
        p = re.sub(r"\bMath\.Truncate\(", "Fix(", p)
        p = re.sub(r"\bMath\.Pow\(([^,]+),\s*([^)]+)\)", r"(\1) ^ (\2)", p)
        p = re.sub(r"\bApplication\.DoEvents\(\)", "DoEvents", p)
        p = re.sub(r"\bApplication\.StartupPath\b", "App.Path", p)
        # controls: .Items.Count / .SelectedIndex / .SelectedItem / .Checked
        p = re.sub(r"\b(\w+)\.Items\.Count\b", r"\1.ListCount", p)
        p = re.sub(r"\b(\w+)\.SelectedIndex\b", r"\1.ListIndex", p)
        p = re.sub(r"\b(\w+)\.SelectedItem\b", r"\1.Text", p)
        p = re.sub(r"\b(\w+)\.Items\((.+?)\)", r"\1.List(\2)", p)
        p = re.sub(r"\bMe\.(\w+)\.", lambda m: (m.group(1) + ".") if m.group(1).lower() in self.controls else m.group(0), p)
        p = re.sub(r"\b(\w+)\.Checked\b", lambda m: self._checked(m.group(1)), p)
        p = re.sub(r"\bNew\s+List\(Of\s+[\w.]+\)(?:\(\))?", "New Collection", p)
        return p

    def _checked(self, name: str) -> str:
        t = self.controls.get(name.lower())
        if t == "CheckBox":
            return f"({name}.Value = 1)"
        return f"{name}.Value"

    def _interp(self, s: str, line: int) -> str:
        """$"Total {x:F2}" -> "Total " & Format(x, "0.00")"""
        out, i = "", 0
        while i < len(s):
            if s[i] == "$" and i + 1 < len(s) and s[i + 1] == '"':
                j, pieces, buf = i + 2, [], ""
                while j < len(s):
                    ch = s[j]
                    if ch == '"':
                        if j + 1 < len(s) and s[j + 1] == '"':
                            buf += '""'
                            j += 2
                            continue
                        break
                    if ch == "{":
                        if j + 1 < len(s) and s[j + 1] == "{":
                            buf += "{"
                            j += 2
                            continue
                        k, depth = j + 1, 1
                        while k < len(s) and depth:
                            depth += {"{": 1, "}": -1}.get(s[k], 0)
                            k += 1
                        inner = s[j + 1:k - 1]
                        if buf:
                            pieces.append(f'"{buf}"')
                            buf = ""
                        e, _, fmt = inner.partition(":")
                        e = self.expr(e.strip(), line)
                        pieces.append(f'Format({e}, "{_net_format(fmt)}")' if fmt else f"({e})" if " " in e else e)
                        j = k
                        continue
                    if ch == "}" and j + 1 < len(s) and s[j + 1] == "}":
                        buf += "}"
                        j += 2
                        continue
                    buf += ch
                    j += 1
                if buf or not pieces:
                    pieces.append(f'"{buf}"')
                out += " & ".join(pieces)
                i = j + 1
                continue
            out += s[i]
            i += 1
        return out

    def _methods(self, s: str, line: int) -> str:
        """receiver.Method(args) rewrites that need the receiver expression."""
        rules = ("ToString", "ToUpper", "ToLower", "Trim", "Length", "Substring", "Contains", "IndexOf",
                 "Replace", "StartsWith", "EndsWith", "Focus", "Clear", "Add", "AddRange", "RemoveAt", "Count",
                 "Show", "Close", "PadLeft", "PadRight", "Split")
        # "Count" of anything but .Items stays as it is (Collection.Count exists in VB6)
        for _guard in range(60):
            m = None
            for mm in re.finditer(r"\.(" + "|".join(rules) + r")\b", s):
                # skip matches inside strings
                if s[:mm.start()].count('"') % 2:
                    continue
                m = mm
                break
            if m is None:
                break
            dot = m.start()
            name = m.group(1)
            start = _receiver_start(s, dot)
            recv = s[start:dot]
            after = m.end()
            args, end = [], after
            if after < len(s) and s[after] == "(":
                close = _close_paren(s, after)
                args = _split_args(s[after + 1:close])
                end = close + 1
            rec_low = recv.lower()
            rep = None
            if rec_low.endswith(".items") and name in ("Add", "AddRange", "Clear", "RemoveAt", "Count"):
                ctl = recv[:-6]
                rep = {"Add": f"{ctl}.AddItem {args[0]}" if args else None, "Clear": f"{ctl}.Clear",
                       "RemoveAt": f"{ctl}.RemoveItem {args[0]}" if args else None,
                       "Count": f"{ctl}.ListCount"}.get(name)
                if name == "AddRange":
                    rep = None
                    self.note("manual", line, f"{recv}.AddRange - add the items one by one with AddItem")
            elif rec_low in ("messagebox",) and name == "Show":
                rep = self._msgbox(args)
            elif name == "ToString":
                rep = f'Format({recv}, "{_net_format(args[0].strip(chr(34)))}")' if args else f"CStr({recv})"
            elif name in ("ToUpper", "ToLower", "Trim"):
                rep = f"{ {'ToUpper': 'UCase', 'ToLower': 'LCase', 'Trim': 'Trim'}[name]}({recv})"
            elif name == "Length":
                rep = f"Len({recv})"
            elif name == "Substring" and args:
                rep = f"Mid({recv}, ({args[0]}) + 1{', ' + args[1] if len(args) > 1 else ''})"
            elif name == "Contains" and args:
                rep = f"(InStr({recv}, {args[0]}) > 0)"
            elif name == "IndexOf" and args:
                rep = f"(InStr({recv}, {args[0]}) - 1)"
            elif name == "Replace" and len(args) == 2:
                rep = f"Replace({recv}, {args[0]}, {args[1]})"
            elif name == "StartsWith" and args:
                rep = f"(Left({recv}, Len({args[0]})) = {args[0]})"
            elif name == "EndsWith" and args:
                rep = f"(Right({recv}, Len({args[0]})) = {args[0]})"
            elif name == "PadLeft" and args:
                rep = f"Right(Space({args[0]}) & {recv}, {args[0]})"
            elif name == "PadRight" and args:
                rep = f"Left({recv} & Space({args[0]}), {args[0]})"
            elif name == "Split" and args:
                rep = f"Split({recv}, {args[0]})"
            elif name == "Focus":
                rep = f"{recv}.SetFocus"
            elif name == "Clear" and self.controls.get(recv.lower()) == "TextBox":
                rep = f"{recv}.Text = \"\""
            elif name == "Close" and rec_low in ("me", ""):
                rep = "Unload Me"
            elif name == "Show" and rec_low and rec_low not in self.controls:
                rep = f"{recv}.Show{' ' + args[0] if args else ''}"
            if rep is None:
                # keep it (marked so that the loop does not find it again)
                s = s[:dot] + "\x01" + s[dot + 1:]
                continue
            s = s[:start] + rep + s[end:]
        return s.replace("\x01", ".")

    def _msgbox(self, args) -> str:
        if not args:
            return 'MsgBox ""'
        text = args[0]
        title = args[1] if len(args) > 1 else ""
        flags = [a for a in args[2:4] if a and a != "0"]
        flag = " + ".join(flags) if flags else ""
        out = f"MsgBox({text}"
        if flag or title:
            out += f", {flag or 'vbOKOnly'}"
        if title:
            out += f", {title}"
        return out + ")"

    # ------------------------------------------------------------------ statements
    def body(self, method: VbMethod, is_function: bool) -> list[tuple[int, str]]:
        """VB6 lines (line number of the original, text) of one method body."""
        out: list[tuple[int, str]] = []
        tries: list[dict] = []
        pending_dims: list[tuple[int, str]] = []
        base = min([len(r) - len(r.lstrip()) for _l, r in method.body if r.strip()] or [0])
        for ln, raw in method.body:
            ind = "    " + raw[min(base, len(raw) - len(raw.lstrip())):len(raw) - len(raw.lstrip())]
            s = raw.strip()
            comment = ""
            code = s
            q = False
            for j, ch in enumerate(s):
                if ch == '"':
                    q = not q
                elif ch == "'" and not q:
                    code, comment = s[:j].rstrip(), s[j:]
                    break
            if not code:
                out.append((ln, ind + comment))
                continue
            for new in self.stmt(code, ln, method, is_function, tries, pending_dims):
                out.append((ln, ind + new))
            if comment and out:
                out[-1] = (out[-1][0], out[-1][1] + "  " + comment)
        return [(a, "    " + b) for a, b in pending_dims] + out

    def stmt(self, s: str, ln: int, method: VbMethod, is_function: bool, tries: list, dims: list) -> list[str]:
        low = s.lower()
        # Dim x As T = v / Dim x = v / Dim x As New T(...)
        m = re.match(r"^(Dim|Static|Const)\s+(\w+)(\(\))?(?:\s+As\s+(New\s+)?([\w.]+(?:\(Of [^)]*\))?)(\([^)]*\))?)?\s*"
                     r"(?:=\s*(.+))?$", s, re.I)
        if m:
            kw, name, arr, new, typ, ctor, init = m.groups()
            typ = self.vb6_type(typ or "")
            if kw.lower() == "const":
                return [f"Const {name}{' As ' + typ if typ else ''} = {self.expr(init or '0', ln)}"]
            out = [f"{kw} {name}{arr or ''}{' As ' + ('New ' if new else '') + typ if typ else ''}"]
            if init is not None:
                if arr and init.strip().startswith("{"):
                    out.append(f"{name} = Array({self.expr(init.strip()[1:-1], ln)})")
                else:
                    out.append(f"{name} = {self.expr(init, ln)}")
            return out
        if re.match(r"^Dim\s+\w+\s*,", s, re.I):
            return [re.sub(r"\bAs\s+(\w+)", lambda mm: "As " + self.vb6_type(mm.group(1)), s)]
        # compound assignment
        m = re.match(r"^([\w.()]+)\s*(\+=|-=|\*=|/=|&=|\\=)\s*(.+)$", s)
        if m:
            tgt, op, val = m.groups()
            return [f"{self.expr(tgt, ln)} = {self.expr(tgt, ln)} {op[0]} {self._paren(self.expr(val, ln))}"]
        # Return
        m = re.match(r"^Return\b\s*(.*)$", s, re.I)
        if m:
            if is_function and m.group(1):
                return [f"{method.name} = {self.expr(m.group(1), ln)}", "Exit Function"]
            return ["Exit Function" if is_function else "Exit Sub"]
        # For i As Integer = a To b / For Each x As T In c
        m = re.match(r"^For\s+(\w+)\s+As\s+(\w+)\s*=\s*(.+)$", s, re.I)
        if m:
            dims.append((ln, f"Dim {m.group(1)} As {self.vb6_type(m.group(2))}"))
            return [f"For {m.group(1)} = {self.expr(m.group(3), ln)}"]
        m = re.match(r"^For\s+Each\s+(\w+)\s+As\s+([\w.]+(?:\(Of [^)]*\))?)\s+In\s+(.+)$", s, re.I)
        if m:
            dims.append((ln, f"Dim {m.group(1)}"))
            return [f"For Each {m.group(1)} In {self.expr(m.group(3), ln)}"]
        if re.match(r"^End\s+While$", s, re.I):
            return ["Wend"]
        if re.match(r"^(Continue|Exit)\s+(For|Do|While)$", s, re.I) and low.startswith("continue"):
            self.note("manual", ln, f"'{s}' has no VB6 equivalent - restructure the loop")
            return [f"' TODO: {s}"]
        if re.match(r"^Exit\s+While$", s, re.I):
            self.note("manual", ln, "'Exit While' has no VB6 equivalent - use a Do While loop with Exit Do")
            return [f"' TODO: {s}"]
        # Try / Catch / Finally
        if low == "try":
            self.tmp += 1
            tries.append({"n": self.tmp, "state": "try", "ex": ""})
            self.note("approx", ln, "Try/Catch became On Error GoTo (an error in the Catch block itself is not caught)")
            return [f"On Error GoTo Catch{self.tmp}"]
        m = re.match(r"^Catch\b(?:\s+(\w+)(?:\s+As\s+[\w.]+)?)?(?:\s+When\s+.+)?$", s, re.I)
        if m and tries:
            t = tries[-1]
            t["state"], t["ex"] = "catch", (m.group(1) or "")
            return [f"GoTo EndTry{t['n']}", f"Catch{t['n']}:"]
        if low == "finally" and tries:
            t = tries[-1]
            first = t["state"] == "try"
            t["state"] = "finally"
            self.note("approx", ln, "Finally block runs after Try/Catch (not when the Try block exits early)")
            return ([f"GoTo EndTry{t['n']}", f"Catch{t['n']}:", f"Resume EndTry{t['n']}"] if first
                    else [f"Resume EndTry{t['n']}"]) + [f"EndTry{t['n']}:"] + ["On Error GoTo 0"]
        if low == "end try" and tries:
            t = tries.pop()
            if t["state"] == "finally":
                return []
            if t["state"] == "try":
                return [f"Catch{t['n']}:", f"EndTry{t['n']}:", "On Error GoTo 0"]
            return [f"Resume EndTry{t['n']}", f"EndTry{t['n']}:", "On Error GoTo 0"]
        if tries and tries[-1]["ex"]:
            ex = tries[-1]["ex"]
            s = re.sub(rf"\b{re.escape(ex)}\.Message\b", "Err.Description", s)
            s = re.sub(rf"\b{re.escape(ex)}\.ToString\(\)", "Err.Description", s)
        if re.match(r"^Throw\b", s, re.I):
            self.note("approx", ln, "Throw became Err.Raise")
            return ['Err.Raise vbObjectError + 1, , "error"']
        if re.match(r"^Using\b|^End Using$|^SyncLock\b|^End SyncLock$|^AddHandler\b|^RemoveHandler\b|^RaiseEvent\b",
                    s, re.I):
            self.note("manual", ln, f"'{s}' has no VB6 equivalent")
            return [f"' TODO (VB.NET): {s}"]
        # If Not Double.TryParse(a, b) Then  ->  b = Val(a) : If Not IsNumeric(a) Then
        m = re.search(r"\b(?:Double|Integer|Int32|Single|Decimal|Long)\.TryParse\(", s)
        if m:
            close = _close_paren(s, m.end() - 1)
            args = _split_args(s[m.end():close])
            if len(args) >= 2:
                a, b = self.expr(args[0], ln), args[-1].strip()
                b = re.sub(r"^(?:out\s+)?(?:ByRef\s+)?", "", b)
                rest = s[:m.start()] + f"IsNumeric({a})" + s[close + 1:]
                self.note("approx", ln, "TryParse became Val() + IsNumeric() (text such as '12abc' gives 12)")
                conv = "CInt" if "Int" in m.group(0) or "Long" in m.group(0) else "Val"
                return [f"{b} = {conv}(Val({a}))" if conv == "CInt" else f"{b} = Val({a})", self.expr(rest, ln)]
        # Select Case / If / ElseIf / While / Do: expressions inside
        m = re.match(r"^(If|ElseIf)\s+(.+?)\s+Then(\s+.*)?$", s, re.I)
        if m:
            tail = m.group(3) or ""
            if tail.strip():
                inner = self.stmt(tail.strip(), ln, method, is_function, tries, dims)
                return [f"{m.group(1)} {self.expr(m.group(2), ln)} Then {': '.join(inner)}"]
            return [f"{m.group(1)} {self.expr(m.group(2), ln)} Then"]
        m = re.match(r"^(Select\s+Case|While|Do\s+While|Do\s+Until|Loop\s+While|Loop\s+Until|Case)\s+(.+)$", s, re.I)
        if m:
            if m.group(1).lower() == "case" and m.group(2).lower() == "else":
                return ["Case Else"]
            return [f"{m.group(1)} {self.expr(m.group(2), ln)}"]
        if re.match(r"^(End\s+(If|Select|With)|Else|Do|Loop|Next(\s+\w+)?|Exit\s+(Sub|Function|For|Do))$", s, re.I):
            return [s]
        # call / assignment
        m = re.match(r"^([\w.()]+(?:\([^=]*\))?)\s*=\s*(.+)$", s)
        if m and not s.lower().startswith(("if ", "call ")):
            tgt, val = m.groups()
            tgt_v6 = self.expr(tgt, ln)
            if tgt_v6.startswith("(") and tgt_v6.endswith(".Value = 1)"):       # chk.Checked = v
                name = tgt_v6[1:].split(".")[0]
                return [f"{name}.Value = IIf({self.expr(val, ln)}, 1, 0)"]
            return [f"{tgt_v6} = {self.expr(val, ln)}"]
        out = self.expr(s, ln)
        # a call with parentheses as a statement: Foo(a, b) -> Call Foo(a, b) is valid VB6
        m = re.match(r"^([\w.]+)\((.*)\)$", out)
        if m and not out.lower().startswith(("msgbox(",)):
            name = m.group(1)
            if name.lower() in self.methods or "." not in name:
                return [f"Call {out}" if m.group(2).strip() else name]
            return [f"{name} {m.group(2)}" if m.group(2).strip() else name]
        if out.lower().startswith("msgbox("):
            inner = out[7:-1]
            return [f"MsgBox {inner}"]
        return [out]

    @staticmethod
    def _paren(e: str) -> str:
        return f"({e})" if re.search(r"[-+*/&<>=]| And | Or ", e) and not (e.startswith("(") and e.endswith(")")) \
            else e

    @staticmethod
    def vb6_type(t: str) -> str:
        if not t:
            return ""
        base = t.split("(")[0].split(".")[-1]
        return {"Short": "Integer", "Int16": "Integer", "Int32": "Long", "Int64": "Long", "UInteger": "Long",
                "Char": "String", "Object": "Variant", "Decimal": "Currency", "DateTime": "Date",
                "List": "Collection", "Dictionary": "Collection"}.get(base, base)


def vbnet_form_to_vb6(cls: VbClass, form_dict: dict, wiring: dict, file: str, notes: Notes) -> tuple[str, dict]:
    """The VB6 code module of a VB.NET form: (text, {vb6 line -> original line})."""
    from ..runtimes.vbevents import vb_event_name
    controls = {c["props"]["Name"]: c["type"] for c in form_dict["controls"]}
    conv = VbNetToVb6(controls, cls.name, file, notes, {m.name for m in cls.methods})
    lines: list[tuple[int, str]] = [(0, "Option Explicit"), (0, "")]
    init: list[tuple[int, str]] = []
    for ln, f in cls.fields:
        m = re.match(r"^(?:(?:Private|Public|Friend|Protected|Dim|Shared|ReadOnly|WithEvents)\s+)+(\w+)(\(\))?"
                     r"(?:\s+As\s+(New\s+)?([\w.]+(?:\(Of [^)]*\))?)(\([^)]*\))?)?\s*(?:=\s*(.+))?$", f, re.I)
        if not m:
            m2 = re.match(r"^(?:(?:Private|Public|Friend)\s+)?Const\s+(\w+)(?:\s+As\s+(\w+))?\s*=\s*(.+)$", f, re.I)
            if m2:
                lines.append((ln, f"Private Const {m2.group(1)} = {conv.expr(m2.group(3), ln)}"))
                continue
            notes.add("manual", file, ln, f"field not translated: `{f}`")
            lines.append((ln, f"' TODO (VB.NET): {f}"))
            continue
        name, arr, new, typ, _ctor, val = m.groups()
        if name.lower() in {k.lower() for k in controls}:
            continue
        t = conv.vb6_type(typ or "")
        lines.append((ln, f"Private {name}{arr or ''}{' As ' + ('New ' if new else '') + t if t else ''}"))
        if val is not None:
            init.append((ln, f"    {name} = {conv.expr(val, ln)}"))
    # handlers: method -> [(control, neutral)] from the wiring
    by_method: dict[str, list] = {}
    for handler, meth in wiring.items():
        if isinstance(meth, str):
            owner, _, neutral = handler.rpartition("_")
            by_method.setdefault(meth, []).append((owner, neutral))
    load_written = False
    for m in cls.methods:
        is_fn = m.kind == "function"
        body = conv.body(m, is_fn)
        targets = by_method.get(m.name, [])
        lines.append((0, ""))
        if not targets:
            params = re.sub(r"\bAs\s+([\w.]+)", lambda mm: "As " + conv.vb6_type(mm.group(1)), m.params)
            params = re.sub(r"\bByVal\s+", "ByVal ", params)
            head = f"Private {'Function' if is_fn else 'Sub'} {m.name}({params})"
            if is_fn and m.ret:
                head += f" As {conv.vb6_type(m.ret)}"
            lines.append((m.line, head))
            lines += body
            lines.append((m.line, f"End {'Function' if is_fn else 'Sub'}"))
            continue
        # one VB6 event procedure per handled event; the first holds the code, the others call it
        first = None
        for owner, neutral in targets:
            if owner == cls.name:
                vb_ev = vb_event_name("Form", neutral) or neutral
                pname = f"Form_{vb_ev}"
            else:
                vb_ev = vb_event_name(controls.get(owner, "Button"), neutral) or neutral
                pname = f"{owner}_{vb_ev}"
            if pname.endswith("_Load") and pname.startswith("Form"):
                load_written = True
            if first is None:
                first = pname
                lines.append((m.line, f"Private Sub {pname}()"))
                if pname == "Form_Load":
                    lines += init
                    init = []
                lines += body
                lines.append((m.line, "End Sub"))
            else:
                lines += [(m.line, f"Private Sub {pname}()"), (m.line, f"    {first}"), (m.line, "End Sub")]
        if m.params.strip() and not re.fullmatch(r"\s*(ByVal\s+)?sender\s+As\s+[\w.]+\s*,\s*(ByVal\s+)?e\s+As\s+[\w.]+\s*",
                                                 m.params, re.I):
            notes.add("approx", file, m.line, f"{m.name}: event parameters ({m.params}) are not available in VB6")
    if init and not load_written:
        lines += [(0, ""), (0, "Private Sub Form_Load()")] + init + [(0, "End Sub")]
    for ln, raw in cls.other:
        if raw.strip():
            notes.add("manual", file, ln, f"not translated: `{raw.strip()}`")
    text = "\n".join(t for _l, t in lines) + "\n"
    linemap = {i + 1: ln for i, (ln, _t) in enumerate(lines)}
    return text, linemap
