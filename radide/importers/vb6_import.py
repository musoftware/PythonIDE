"""Import a Visual Basic 6 project (.vbp) or a single form (.frm).

Forms become .form files (twips -> pixels), the VB code is kept as-is for
the "Visual Basic 6 (BASIC)" language (it runs on the bundled interpreter),
or added as commented reference code for other languages.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..controls import CONTROL_TYPES
from ..languages import get_plugin
from ..model import Control, Form, Project
from .python_import import ImportReport

TWIP = 15

CLASS_MAP = {
    "vb.commandbutton": "Button", "vb.label": "Label", "vb.textbox": "TextBox", "vb.checkbox": "CheckBox",
    "vb.optionbutton": "RadioButton", "vb.listbox": "ListBox", "vb.combobox": "ComboBox",
    "vb.frame": "GroupBox", "vb.picturebox": "Panel", "vb.image": "PictureBox", "vb.timer": "Timer",
    "vb.hscrollbar": "TrackBar", "vb.vscrollbar": "TrackBar", "vb.drivelistbox": "ComboBox",
    "vb.dirlistbox": "ListBox", "vb.filelistbox": "ListBox",
    "mscomctllib.progressbar": "ProgressBar", "comctllib.progressbar": "ProgressBar",
    "mscomctllib.slider": "TrackBar", "comctllib.slider": "TrackBar",
    "mscomctl2.updown": "NumericUpDown", "comct2lib.updown": "NumericUpDown",
    "richtextlib.richtextbox": "TextBox", "mscomctllib.listview": "ListBox", "mscomctllib.treeview": "ListBox",
    "msflexgridlib.msflexgrid": "ListBox", "mshierarchicalflexgridlib.mshflexgrid": "ListBox",
    "mscomctllib.tabstrip": "Panel", "tabdlg.sstab": "Panel", "mscomctllib.statusbar": "Label",
    "mscomctllib.toolbar": "Panel", "mscomctllib.imagelist": None, "mscomdlg.commondialog": None,
    "vb.data": None, "mswinsocklib.winsock": None, "mscommlib.mscomm": None, "vb.shape": "Panel",
    "vb.line": None, "vb.ole": "Panel",
}
APPROX = {"vb.drivelistbox", "vb.dirlistbox", "vb.filelistbox", "mscomctllib.listview", "mscomctllib.treeview",
          "msflexgridlib.msflexgrid", "mshierarchicalflexgridlib.mshflexgrid", "mscomctllib.tabstrip",
          "tabdlg.sstab", "mscomctllib.statusbar", "mscomctllib.toolbar", "vb.shape", "vb.ole"}


def read_vb_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1256", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


# ======================================================================= .frm parsing
class FrmObject:
    def __init__(self, cls: str, name: str):
        self.cls, self.name = cls, name
        self.props: dict[str, object] = {}
        self.font: dict[str, object] = {}
        self.children: list[FrmObject] = []


def _value(raw: str):
    raw = raw.strip()
    if raw.startswith('"'):
        end = raw.rfind('"')
        return raw[1:end].replace('""', '"')
    raw = raw.split("'")[0].strip()
    if raw.startswith("$"):
        return ("frx", raw)
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


def parse_frm(text: str) -> tuple[FrmObject | None, str]:
    """Return (form object tree, code text)."""
    lines = text.splitlines()
    stack: list[FrmObject] = []
    root = None
    i = 0
    in_prop = 0
    prop_name = ""
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        m = re.match(r"Begin\s+(\S+)\s+(\S+)", line, re.I)
        if m:
            obj = FrmObject(m.group(1), m.group(2))
            if stack:
                stack[-1].children.append(obj)
            else:
                root = obj
            stack.append(obj)
            continue
        if re.match(r"BeginProperty\s+(\w+)", line, re.I):
            in_prop += 1
            prop_name = re.match(r"BeginProperty\s+(\w+)", line, re.I).group(1).lower()
            continue
        if re.match(r"EndProperty", line, re.I):
            in_prop -= 1
            continue
        if line.lower() == "end" and stack:
            stack.pop()
            if not stack:
                break
            continue
        if stack and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            if in_prop and prop_name == "font":
                stack[-1].font[k.lower()] = _value(v)
            elif not in_prop:
                stack[-1].props[k.lower()] = _value(v)
    code_lines = [ln for ln in lines[i:] if not re.match(r"\s*Attribute\s+VB_", ln, re.I)]
    return root, "\n".join(code_lines).strip("\n") + "\n"


def _color(v) -> str:
    if not isinstance(v, int) or v & 0x80000000:
        return ""
    return f"#{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"


def _px(v, default=0) -> int:
    try:
        return int(round(float(v) / TWIP))
    except (TypeError, ValueError):
        return default


def _bool(v, default=True) -> bool:
    if v is None:
        return default
    try:
        return int(v) != 0
    except (TypeError, ValueError):
        return str(v).lower() == "true"


# ======================================================================= conversion
class _FrmConverter:
    def __init__(self, report: ImportReport, form_label: str):
        self.report = report
        self.label = form_label

    def convert(self, root: FrmObject) -> Form:
        p = root.props
        form = Form()
        form.props.update(Name=root.name, Text=str(p.get("caption", root.name)),
                          Width=_px(p.get("clientwidth", 6000), 400), Height=_px(p.get("clientheight", 4500), 300),
                          ScaleMode="Twip" if int(p.get("scalemode", 1) or 1) == 1 else "Pixel")
        if _color(p.get("backcolor")):
            form.props["BackColor"] = _color(p.get("backcolor"))
        form.props["StartPosition"] = "CenterScreen" if int(p.get("startupposition", 2) or 0) in (1, 2) else "Manual"
        if int(p.get("borderstyle", 2) or 2) in (1, 3):
            form.props["FormBorderStyle"] = "FixedSingle"
        if int(p.get("windowstate", 0) or 0) == 2:
            form.props["WindowState"] = "Maximized"
        menus = [c for c in root.children if c.cls.lower() == "vb.menu"]
        for ch in root.children:
            if ch.cls.lower() != "vb.menu":
                self._add(form, ch, "")
        if menus:
            m = form.add("MenuStrip", 0, 0)
            m.props["Items"] = [self._menu(x) for x in menus if _bool(x.props.get("visible"), True) or x.children]
        return form

    def _menu(self, m: FrmObject) -> dict:
        caption = str(m.props.get("caption", m.name)).replace("&", "")
        if caption == "-":
            return {"Text": "-"}
        d = {"Text": caption, "Name": m.name}
        kids = [self._menu(c) for c in m.children if c.cls.lower() == "vb.menu"]
        if kids:
            d["Items"] = kids
        if "index" in m.props:
            self.report.warnings.append(f"menu control array '{m.name}' imported as a single item")
        return d

    def _add(self, form: Form, o: FrmObject, parent: str) -> None:
        cls = o.cls.lower()
        if cls not in CLASS_MAP:
            self.report.warnings.append(f"{self.label}: ActiveX control '{o.name}' ({o.cls}) is not available - "
                                        "imported as a Panel placeholder")
            ntype = "Panel"
        else:
            ntype = CLASS_MAP[cls]
            if ntype is None:
                self.report.warnings.append(f"{self.label}: '{o.name}' ({o.cls}) has no equivalent yet - skipped")
                return
            if cls in APPROX:
                self.report.warnings.append(f"{self.label}: '{o.name}' ({o.cls}) imported as {ntype} (approximation)")
        p = o.props
        if cls == "vb.picturebox" and not o.children and p.get("picture"):
            ntype = "PictureBox"
        ctype = CONTROL_TYPES[ntype]
        index = p.get("index")
        name = o.name if index is None else f"{o.name}_{index}"
        props = ctype.default_props(name)
        if not ctype.nonvisual:
            props.update(Left=_px(p.get("left", 0)), Top=_px(p.get("top", 0)),
                         Width=max(8, _px(p.get("width", 1200), 80)), Height=max(8, _px(p.get("height", 375), 25)),
                         Enabled=_bool(p.get("enabled"), True), Visible=_bool(p.get("visible"), True),
                         TabIndex=int(p.get("tabindex", 0) or 0), ToolTip=str(p.get("tooltiptext", "") or ""))
        props["Parent"] = parent
        if index is not None:
            props["ArrayName"] = o.name
            props["ArrayIndex"] = int(index)
        text = p.get("caption", p.get("text", ""))
        if isinstance(text, tuple):
            text = ""
            self.report.warnings.append(f"{self.label}: '{name}' text stored in .frx - not imported")
        if "Text" in props:
            props["Text"] = str(text or "")
        if ntype == "TextBox":
            props["Text"] = str(p.get("text", "") if not isinstance(p.get("text"), tuple) else "")
            props["Multiline"] = _bool(p.get("multiline"), False) or cls == "richtextlib.richtextbox"
            props["ReadOnly"] = _bool(p.get("locked"), False)
            props["PasswordChar"] = str(p.get("passwordchar", "") or "")[:1]
            props["MaxLength"] = int(p.get("maxlength", 0) or 0)
        if ntype in ("CheckBox",):
            props["Checked"] = int(p.get("value", 0) or 0) == 1
        if ntype == "RadioButton":
            props["Checked"] = _bool(p.get("value"), False)
        if ntype == "ComboBox":
            props["DropDownStyle"] = "DropDownList" if int(p.get("style", 0) or 0) == 2 else "DropDown"
        if ntype in ("TrackBar", "NumericUpDown", "ProgressBar"):
            props["Minimum"] = int(p.get("min", 0) or 0)
            props["Maximum"] = int(p.get("max", 100 if ntype != "TrackBar" else 32767) or 100)
            props["Value"] = int(p.get("value", 0) or 0)
        if ntype == "Label":
            props["TextAlign"] = {0: "Left", 1: "Right", 2: "Center"}.get(int(p.get("alignment", 0) or 0), "Left")
        if ntype == "Button":
            props["TextAlign"] = "Center"
        if ntype == "Timer":
            props["Interval"] = int(p.get("interval", 0) or 0)
            props["Enabled"] = _bool(p.get("enabled"), True) and props["Interval"] > 0
        if not ctype.nonvisual:
            bg, fg = _color(p.get("backcolor")), _color(p.get("forecolor"))
            if bg:
                props["BackColor"] = bg
            if fg and "ForeColor" in props:
                props["ForeColor"] = fg
            if o.font:
                f = o.font
                if f.get("name"):
                    props["FontName"] = {"MS Sans Serif": "Segoe UI"}.get(str(f["name"]), str(f["name"]))
                if f.get("size"):
                    props["FontSize"] = max(6, int(round(float(f["size"]))))
                props["FontBold"] = int(f.get("weight", 400) or 400) >= 700
                props["FontItalic"] = _bool(f.get("italic"), False)
        if ntype == "PictureBox" and p.get("picture"):
            self.report.warnings.append(f"{self.label}: '{name}' picture is stored in .frx - set Image again")
        form.controls.append(Control(ntype, props))
        self.report.controls += 1
        if ctype.container:
            for ch in o.children:
                self._add(form, ch, name)
        elif o.children:
            for ch in o.children:          # e.g. controls inside an SSTab placeholder
                self._add(form, ch, parent)


# ======================================================================= project
def parse_vbp(path: Path) -> dict:
    info = {"forms": [], "modules": [], "classes": [], "objects": [], "startup": "", "name": path.stem}
    for line in read_vb_text(path).splitlines():
        k, _, v = line.partition("=")
        k = k.strip().lower()
        v = v.strip()
        if k == "form":
            info["forms"].append(v)
        elif k == "module":
            info["modules"].append(v.split(";")[-1].strip())
        elif k == "class":
            info["classes"].append(v.split(";")[-1].strip())
        elif k == "object":
            info["objects"].append(v.split(";")[-1].strip())
        elif k == "startup":
            info["startup"] = v.strip('"')
        elif k == "name":
            info["name"] = v.strip('"')
    return info


def _comment_code(code: str) -> str:
    return "\n".join("# VB6: " + ln if ln.strip() else "" for ln in code.splitlines())


def import_vb6(source: Path, dest: Path, language: str = "vb-basic") -> ImportReport:
    if language in ("python-tk", "python-qt") and not (Path(dest).exists() and any(Path(dest).iterdir())):
        try:            # VB6 code translated to Python by rules (radide/migrate, File > Migrate Project)
            from ..migrate.engine import Options, load_source, migrate
            res = migrate(load_source(Path(source)), Options(language, Path(dest)))
            rep = ImportReport(Project.load(Path(dest)), res.stats.get("forms", 0), res.stats.get("controls", 0),
                               res.stats.get("handlers", 0))
            rep.warnings = [f"{n.where()}: {n.text}" for n in res.notes.items if n.level in ("approx", "manual")]
            rep.warnings.append(f"Full report: {res.report_path}")
            return rep
        except Exception:  # noqa: BLE001 - fall back to the VB6 code kept as comments (below)
            pass
    report = ImportReport()
    if source.suffix.lower() == ".vbp":
        info = parse_vbp(source)
        base = source.parent
    else:
        info = {"forms": [source.name], "modules": [], "classes": [], "objects": [], "startup": "",
                "name": source.stem}
        base = source.parent
    for obj in info["objects"]:
        report.warnings.append(f"project references ActiveX/OCX '{obj}' - its controls become placeholders")
    dest.mkdir(parents=True, exist_ok=True)
    orig = dest / "_original_vb6"
    orig.mkdir(exist_ok=True)
    plugin = get_plugin(language)
    project = Project(dest, re.sub(r"\W", "_", info["name"]) or "VB6Project", language)
    is_vb = language == "vb-basic"
    for frm_rel in info["forms"]:
        frm_path = (base / frm_rel).resolve()
        if not frm_path.exists():
            report.warnings.append(f"form file not found: {frm_rel}")
            continue
        for extra in (frm_path, frm_path.with_suffix(".frx")):
            if extra.exists():
                shutil.copy2(extra, orig / extra.name)
        root, code = parse_frm(read_vb_text(frm_path))
        if root is None:
            report.warnings.append(f"{frm_path.name}: no form definition found")
            continue
        form = _FrmConverter(report, frm_path.name).convert(root)
        name = form.name
        form.save(project.form_path(name))
        project.forms.append(name)
        report.forms += 1
        if is_vb:
            user = code
            report.handlers += len(re.findall(r"^\s*(?:Private|Public)?\s*Sub\s+\w+_\w+\s*\(", code, re.I | re.M))
        else:
            user = plugin.new_code(form, not project.startup)
            for m in re.finditer(r"^\s*(?:Private\s+|Public\s+)?Sub\s+(\w+)_(\w+)\s*\(.*?\)(.*?)^\s*End\s+Sub",
                                 code, re.I | re.M | re.S):
                handler = f"{m.group(1)}_{m.group(2)}"
                user, line = plugin.add_handler(user, handler, form)
                lines = user.splitlines()
                body = [("        # VB6: " if language.startswith("python") else "    # VB6: ") + ln.strip()
                        for ln in m.group(3).strip("\n").splitlines() if ln.strip()]
                lines[line + 1:line + 1] = body
                user = "\n".join(lines) + "\n"
                report.handlers += 1
            user += "\n\n" + _comment_code(code) + "\n"
        (dest / plugin.code_file(name)).write_text(user, encoding="utf-8")
        (dest / plugin.designer_file(name)).write_text(plugin.generate_designer(form, user), encoding="utf-8")
        if not project.startup:
            project.startup = name
    st = info["startup"]
    if st and st.lower() in [f.lower() for f in project.forms]:
        project.startup = next(f for f in project.forms if f.lower() == st.lower())
    elif st.lower() == "sub main" and is_vb:
        project.startup = "Sub Main"
    for kind in ("modules", "classes"):
        for rel in info[kind]:
            path = (base / rel).resolve()
            if not path.exists():
                report.warnings.append(f"{kind[:-1]} file not found: {rel}")
                continue
            shutil.copy2(path, orig / path.name)
            text = read_vb_text(path)
            if is_vb:
                # class modules stay .cls: the interpreter runs them as classes (New, properties, events)
                target = f"{path.stem}.cls" if kind == "classes" else f"{path.stem}.bas"
                (dest / target).write_text(text, encoding="utf-8")
            else:
                target = f"{path.stem}{plugin.code_ext}"
                (dest / target).write_text(plugin.module_template(path.stem) + _comment_code(text) + "\n",
                                           encoding="utf-8")
            project.modules.append(target)
    project.save()
    report.project = project
    if not is_vb:
        report.warnings.append("VB code was added as comments - rewrite it in the target language "
                               "(choose 'Visual Basic 6 (BASIC)' to run it as-is).")
    return report
