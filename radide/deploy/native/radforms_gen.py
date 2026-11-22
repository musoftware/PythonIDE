"""radforms: the IDE's neutral form model (.form JSON) -> the native forms runtime's description + resources.

radforms (radide/runtimes/native/radforms) is a small C99 Win32 library that draws the forms of a native exe
and implements the GUI Bridge client API (radgui.h) in process. This module is shared by every native
builder that uses it (C / C++ / Fortran in win32_c.py; Go, Rust and script hosts can reuse it):

    reasons = unsupported(project, folder)              what radforms cannot draw ([] = everything)
    text, images = description(project, folder)         the form description (see radforms.h)
    rc = write_resources(work, project, folder, cfg, log)   forms.radf + manifest + version + icon + images
    obj = compile_resources(windres, rc, log)           -> app.res.o, linked into the exe

The description is embedded as the RCDATA resource "RADFORMS"; radforms reads it at start-up, so a
program only links radforms.o + app.res.o and runs its event loop (rad_run / rad_next_event).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ...controls import CONTROL_TYPES, DIALOG_TYPES
from ...layout import place_specs, tab_page
from ...model import Form, Project

RADFORMS_DIR = Path(__file__).resolve().parents[2] / "runtimes" / "native" / "radforms"
RADFORMS_C = RADFORMS_DIR / "radforms.c"
RADFORMS_H = RADFORMS_DIR / "radforms.h"

# control types radforms draws (TYPE_NAMES in radforms.c) + the menu-like components handled specially
VISUAL_TYPES = {"Button", "Label", "TextBox", "CheckBox", "RadioButton", "ListBox", "ComboBox", "PictureBox",
                "ProgressBar", "NumericUpDown", "TrackBar", "Panel", "GroupBox", "TabControl", "LinkLabel",
                "StatusBar"}
NONVISUAL_TYPES = {"Timer", "MenuStrip", "ToolStrip", *DIALOG_TYPES}
SUPPORTED_TYPES = VISUAL_TYPES | NONVISUAL_TYPES

# properties / methods radforms implements (rad_set / rad_get / rad_call); used to check user code
SUPPORTED_PROPS = {p.lower() for p in """
    Text Caption SimpleText Left Top Width Height Visible Enabled BackColor ForeColor LinkColor FontName FontSize
    FontBold FontItalic FontUnderline Size Bold Italic Checked Value Minimum Maximum Min Max Items List ListIndex
    SelectedIndex ListCount Count ItemCount NewIndex SelectedItem ReadOnly Locked MaxLength PasswordChar TextAlign
    Alignment Image Picture ToolTip ToolTipText SelStart SelectionStart SelLength SelectionLength SelText
    SelectedText Tag Name Interval Multiline hWnd Focused FileName FileTitle Filter Title InitialDirectory Color
    SelectedPath Description WindowState TopMost Icon Cancel ScaleWidth ScaleHeight StartPosition FormBorderStyle
    """.split()}
SUPPORTED_METHODS = {m.lower() for m in """
    AddItem Add RemoveItem RemoveAt Clear List Item Items IndexOf FindString AppendText SelectAll TabCaption
    PerformClick SetFocus Focus Refresh Move ZOrder BringToFront SendToBack Show Hide ShowDialog ShowOpen ShowSave
    ShowColor ShowFont ShowFolder Start Stop Load Unload Close Activate
    """.split()} | SUPPORTED_PROPS

SKIP_PROPS = {"Name", "Parent", "Left", "Top", "Width", "Height", "Anchor", "Dock", "TabIndex", "DataSource",
              "DataMember", "DisplayMember", "ValueMember", "ArrayName", "ArrayIndex"}
FIRST_PROPS = ("TabPages", "DropDownStyle", "Multiline", "Items", "Minimum", "Maximum", "Interval")
LAST_PROPS = ("Value", "Checked", "SelectedIndex", "Text", "Enabled")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".ico", ".tif", ".tiff"}


def _esc(v) -> str:
    s = str(v)
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


def _val(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    return "" if v is None else str(v)


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{float(v):.4f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------ checks
def form_reasons(form: Form) -> list[str]:
    """Why radforms cannot draw *form* exactly ([] = it can)."""
    out = []
    for c in form.controls:
        if c.type not in SUPPORTED_TYPES and c.type not in module_classes():
            out.append(f"{form.name}.{c.name}: control type {c.type} is not supported by the native runtime")
            continue
        if c.states or c.variants:
            out.append(f"{form.name}.{c.name}: visual states / layout variants are not supported natively")
        if any(str(c.props.get(k) or "") for k in ("DataSource", "DataMember")):
            out.append(f"{form.name}.{c.name}: data binding is not supported natively")
        if c.props.get("ArrayName"):
            out.append(f"{form.name}.{c.name}: control arrays are not supported natively")
        if c.type == "ToolStrip" and any(it.get("Items") for it in c.props.get("Items") or []):
            out.append(f"{form.name}.{c.name}: ToolStrip drop-down buttons are not supported natively")
    for key in ("states", "storyboards", "bindings", "datasources", "animations"):
        if form.extra.get(key):
            out.append(f"{form.name}: {key} (Blend / data) are not supported natively")
    return out


def unsupported(project: Project, folder: Path, lang: str | None = None) -> list[str]:
    """Reasons for the whole project: its forms and forms of another language."""
    out = []
    for name in project.forms:
        flang = project.form_languages.get(name, project.language)
        if lang and flang != lang:
            out.append(f"form {name} is written in {flang}: a native exe has one language")
            continue
        try:
            form = Form.load(project.form_path(name))
        except Exception as e:  # noqa: BLE001 - a broken form: let the normal build report it
            out.append(f"form {name} cannot be read: {e}")
            continue
        out += form_reasons(form)
    return out


_SET_RX = [re.compile(r"""\brad(?:_set(?:_num)?|_get(?:_num)?|::set|::get(?:_num)?)\s*\(\s*["']([^"']*)["']\s*,\s*["']([^"']+)["']"""),
           re.compile(r"""\bcall\s+rad_set\s*\(\s*["']([^"']*)["']\s*,\s*["']([^"']+)["']""", re.I),
           re.compile(r"""\brad_get\s*\(\s*["']([^"']*)["']\s*,\s*["']([^"']+)["']""", re.I)]
_CALL_RX = [re.compile(r"""\brad(?:_call|::call)\s*\(\s*["']([^"']*)["']\s*,\s*["']([^"']+)["']"""),
            re.compile(r"""\b(?:call\s+)?rad_callf?\s*\(\s*["']([^"']*)["']\s*,\s*["']([^"']+)["']""", re.I)]


def code_reasons(texts: dict[str, str]) -> list[str]:
    """Properties / methods used with literal names in the program that radforms does not implement."""
    out, seen = [], set()
    for fname, text in texts.items():
        for rx in _SET_RX:
            for obj, prop in rx.findall(text):
                if prop.lower() not in SUPPORTED_PROPS and (fname, prop.lower()) not in seen:
                    seen.add((fname, prop.lower()))
                    out.append(f"{fname}: property '{prop}' ({obj}) is not supported by the native runtime")
        for rx in _CALL_RX:
            for obj, meth in rx.findall(text):
                if meth.lower() not in SUPPORTED_METHODS and (fname, meth.lower()) not in seen:
                    seen.add((fname, meth.lower()))
                    out.append(f"{fname}: method '{meth}' ({obj}) is not supported by the native runtime")
    return out


# ------------------------------------------------------------------ description
def _tab_order(form: Form) -> list:
    out = []

    def visit(parent):
        kids = sorted(form.children(parent), key=lambda c: int(c.props.get("TabIndex", 0) or 0))
        for c in kids:
            out.append(c)
            if c.ctype.container:
                visit(c.name)
    visit("")
    for c in form.visual():             # orphans (parent missing)
        if c not in out:
            out.append(c)
    return out


def _props(c, images: dict, folder: Path) -> list[tuple[str, str]]:
    items = []
    for k, v in c.props.items():
        if k in SKIP_PROPS or v is None:
            continue
        s = _val(v)
        if s == "" and k not in ("Text",):
            continue
        if k in ("Image", "Picture", "Icon") and s:
            images.setdefault(s, None)
        if k == "TabPage" and c.parent:
            s = str(tab_page(c))
        items.append((k, s))
    order = {k: i for i, k in enumerate(FIRST_PROPS)}
    last = {k: i for i, k in enumerate(LAST_PROPS)}
    items.sort(key=lambda kv: (0, order[kv[0]]) if kv[0] in order else (2, last[kv[0]]) if kv[0] in last else (1, 0))
    return items


def _menu_lines(items: list, depth: int, out: list[str]):
    for it in items or []:
        out.append(f"M\t{depth}\t{_esc(it.get('Name', ''))}\t{_esc(it.get('Text', ''))}")
        if it.get("Items"):
            _menu_lines(it["Items"], depth + 1, out)


def form_lines(form: Form, images: dict, folder: Path) -> list[str]:
    L = [f"F\t{_esc(form.name)}"]
    for k, v in form.props.items():
        if k == "Name":
            continue
        s = _val(v)
        if s == "" and k != "Text":
            continue
        if k == "Icon" and s:
            images.setdefault(s, None)
        L.append(f"P\t{_esc(k)}\t{_esc(s)}")
    menu = form.menu()
    if menu is not None:
        _menu_lines(menu.props.get("Items") or [], 0, L)
    strip = next((c for c in form.nonvisual() if c.type == "ToolStrip"), None)
    if strip is not None:
        for it in strip.props.get("Items") or []:
            L.append(f"T\t{_esc(it.get('Name', ''))}\t{_esc(it.get('Text', ''))}")
    places = place_specs(form)
    for c in _tab_order(form):
        pl = places.get(c.name)
        L.append(f"C\t{c.type}\t{_esc(c.name)}\t{_esc(c.parent)}")
        if pl is not None:
            L.append("L\t" + "\t".join(_num(v) for v in (pl.x, pl.y, pl.w, pl.h, pl.rx, pl.ry, pl.rw, pl.rh)))
        for k, v in _props(c, images, folder):
            L.append(f"P\t{_esc(k)}\t{_esc(v)}")
    for c in form.nonvisual():
        if c.type in ("MenuStrip", "ToolStrip"):
            continue
        L.append(f"C\t{c.type}\t{_esc(c.name)}\t")
        for k, v in _props(c, images, folder):
            L.append(f"P\t{_esc(k)}\t{_esc(v)}")
    return L


def description(project: Project, folder: Path, title: str = "") -> tuple[str, dict[str, Path]]:
    """(form description text, {image value as written in the form: file to embed})."""
    images: dict[str, Path | None] = {}
    L = ["RADF\t1", f"A\t{_esc(title or project.name)}"]
    start = project.startup or (project.forms[0] if project.forms else "")
    if start:
        L.append(f"S\t{_esc(start)}")
    for name in project.forms:
        L += form_lines(Form.load(project.form_path(name)), images, folder)
    found = {}
    for value in images:
        p = Path(value)
        if not p.is_absolute():
            p = Path(folder) / value
        if p.is_file() and p.suffix.lower() in IMAGE_EXT:
            found[value] = p
    return "\n".join(L) + "\n", found


# ------------------------------------------------------------------ resources
MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="{name}" version="{version}"/>
  <description>{desc}</description>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0"
                        processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
    </dependentAssembly>
  </dependency>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, PerMonitor</dpiAwareness>
      <activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>
    </windowsSettings>
  </application>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
      <supportedOS Id="{{1f676c76-80e1-4239-95bb-83d0f6d0da78}}"/>
      <supportedOS Id="{{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}}"/>
      <supportedOS Id="{{35138b9a-5d96-4fbd-8e2d-a2440225f93a}}"/>
    </application>
  </compatibility>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security>
  </trustInfo>
</assembly>
"""


def _xml(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _rc(s: str) -> str:
    return str(s).replace('"', '""').replace("\n", " ")


def write_resources(work: Path, project: Project | None, folder: Path, cfg, log=print, gui: bool = True,
                    icon: Path | None = None) -> Path:
    """Write app.rc and the files it embeds into *work*; returns the .rc path."""
    work.mkdir(parents=True, exist_ok=True)
    nums = cfg.numeric_version()
    commas = ",".join(nums.split("."))
    ident = re.sub(r"[^A-Za-z0-9.]", "", f"RADIDE.{cfg.exe_base()}") or "RADIDE.App"
    (work / "app.manifest").write_text(MANIFEST.format(name=ident, version=nums, desc=_xml(cfg.app_name)),
                                       encoding="utf-8")
    L = ["#pragma code_page(65001)", '1 24 "app.manifest"']
    if icon is not None and Path(icon).is_file():
        shutil.copy2(icon, work / "app.ico")
        L.append('1 ICON "app.ico"')
    if gui and project is not None and project.forms:
        text, images = description(project, folder, cfg.app_name)
        lines = text.rstrip("\n").split("\n")
        for i, (value, path) in enumerate(images.items(), 1):
            res = f"RADIMG{i}"
            dst = f"img{i}{path.suffix.lower()}"
            shutil.copy2(path, work / dst)
            lines.append(f"I\t{_esc(value)}\t{res}")
            L.append(f'{res} RCDATA "{dst}"')
        (work / "forms.radf").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        L.append('RADFORMS RCDATA "forms.radf"')
    exe = cfg.exe_base() + ".exe"
    strings = {"CompanyName": cfg.publisher or cfg.app_name, "FileDescription": cfg.app_name,
               "FileVersion": cfg.version, "InternalName": cfg.exe_base(), "OriginalFilename": exe,
               "ProductName": cfg.app_name, "ProductVersion": cfg.version,
               "LegalCopyright": f"(c) {cfg.publisher}" if cfg.publisher else ""}
    L += ["1 VERSIONINFO", f"FILEVERSION {commas}", f"PRODUCTVERSION {commas}", "FILEFLAGSMASK 0x3f",
          "FILEFLAGS 0x0", "FILEOS 0x40004", "FILETYPE 0x1", "FILESUBTYPE 0x0", "BEGIN",
          '  BLOCK "StringFileInfo"', "  BEGIN", '    BLOCK "040904B0"', "    BEGIN"]
    L += [f'      VALUE "{k}", "{_rc(v)}"' for k, v in strings.items()]
    L += ["    END", "  END", '  BLOCK "VarFileInfo"', "  BEGIN", '    VALUE "Translation", 0x409, 1200', "  END",
          "END", ""]
    rc = work / "app.rc"
    rc.write_text("\n".join(L), encoding="utf-8")
    return rc


def compile_resources(windres: str, rc: Path, log=print) -> Path:
    """windres app.rc -> app.res.o (COFF object linked into the exe)."""
    out = rc.with_name("app.res.o")
    cmd = [windres, "--input-format=rc", "--output-format=coff", "-c", "65001", "-i", rc.name, "-o", out.name]
    log("> " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(rc.parent), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=_tool_env(windres))
    if r.stdout.strip() or r.stderr.strip():
        log((r.stdout + r.stderr).strip())
    if r.returncode != 0 or not out.is_file():
        from ..build import BuildError
        raise BuildError("windres failed (see the output above)")
    return out


def _tool_env(tool: str) -> dict:
    """PATH with the toolchain's bin first (windres runs gcc as its preprocessor)."""
    import os
    env = dict(os.environ)
    env["PATH"] = str(Path(tool).parent) + os.pathsep + env.get("PATH", "")
    return env


__all__ = ["RADFORMS_C", "RADFORMS_DIR", "RADFORMS_H", "SUPPORTED_TYPES", "code_reasons", "compile_resources",
           "description", "form_reasons", "unsupported", "write_resources"]


# ------------------------------------------------------------------ control modules (radforms/controls/*.c)
MODULES_DIR = RADFORMS_DIR / "controls"
_CLASSES_RX = re.compile(r"RF_CLASSES:\s*([\w ,]+)")
_MODULE_RX = re.compile(r"^\s*RF_MODULE\s*\(\s*(\w+)\s*\)", re.M)


def module_classes() -> dict[str, Path]:
    """{class name: module source} of every control module shipped with radforms."""
    out = {}
    for p in sorted(MODULES_DIR.glob("*.c")) if MODULES_DIR.is_dir() else []:
        m = _CLASSES_RX.search(p.read_text(encoding="utf-8", errors="replace"))
        for name in (m.group(1).replace(",", " ").split() if m else []):
            out[name] = p
    return out


def modules_for(types) -> list[Path]:
    """Module sources needed for these control type names (only what a project uses is linked)."""
    mc = module_classes()
    return sorted({mc[t] for t in types if t in mc})


def modules_source(modules) -> str:
    """_radmodules.c: rad_modules_init() registers the classes of the linked modules."""
    names = []
    for p in modules:
        names += _MODULE_RX.findall(Path(p).read_text(encoding="utf-8", errors="replace"))
    L = ["/* AUTO-GENERATED by RAD IDE - registers the radforms control modules linked into this exe */",
         '#include "radforms.h"', ""]
    L += [f"RF_MODULE({n});" for n in names]
    L += ["", "void rad_modules_init(void)", "{"] + [f"    rfmod_{n}();" for n in names] + ["}", ""]
    return "\n".join(L)


def project_types(project: Project) -> set[str]:
    types = set()
    for name in project.forms:
        try:
            types |= {c.type for c in Form.load(project.form_path(name)).controls}
        except Exception:  # noqa: BLE001
            pass
    return types


def build_static_lib(out_dir: Path, cc: str, ar: str = "", log=print) -> Path:
    """libradforms.a (MinGW) with the core, every control module and rf_modules_register_all(), plus
    radforms.h - for programs of other languages (Go cgo, Rust, FreeBASIC, Lua hosts ...) that link it."""
    out_dir = Path(out_dir)
    obj = out_dir / "obj"
    obj.mkdir(parents=True, exist_ok=True)
    ar = ar or str(Path(cc).with_name("ar.exe" if cc.lower().endswith(".exe") else "ar"))
    mods = sorted(MODULES_DIR.glob("*.c")) if MODULES_DIR.is_dir() else []
    allsrc = obj / "rf_modules_all.c"
    allsrc.write_text(modules_source(mods).replace("void rad_modules_init(void)", "void rf_modules_register_all(void)"),
                      encoding="utf-8")
    objs = []
    for src in [RADFORMS_C, *mods, allsrc]:
        o = obj / (Path(src).stem + ".o")
        cmd = [cc, "-std=gnu99", "-c", "-Os", "-ffunction-sections", "-fno-asynchronous-unwind-tables", "-I",
               str(RADFORMS_DIR), str(src), "-o", str(o)]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_tool_env(cc))
        if r.returncode != 0:
            from ..build import BuildError
            raise BuildError(f"{Path(src).name}: {(r.stdout + r.stderr).strip()[-1500:]}")
        objs.append(str(o))
    lib = out_dir / "libradforms.a"
    lib.unlink(missing_ok=True)
    r = subprocess.run([ar, "rcs", str(lib), *objs], capture_output=True, text=True, env=_tool_env(cc))
    if r.returncode != 0:
        from ..build import BuildError
        raise BuildError("ar failed: " + (r.stdout + r.stderr).strip())
    shutil.copy2(RADFORMS_H, out_dir / "radforms.h")
    log(f"Static library: {lib} ({lib.stat().st_size // 1024} KB)")
    return lib


# ------------------------------------------------------------------ machine-readable API (radforms_api.json)
API_JSON = RADFORMS_DIR / "radforms_api.json"
COMMON_PROPS = ["Name", "Text", "Left", "Top", "Width", "Height", "Visible", "Enabled", "BackColor", "ForeColor",
                "FontName", "FontSize", "FontBold", "FontItalic", "FontUnderline", "ToolTip", "Tag", "TabIndex"]
CLASS_PROPS = {
    "Form": ["Text", "Width", "Height", "Left", "Top", "BackColor", "Visible", "Enabled", "WindowState", "TopMost",
             "Icon", "StartPosition", "FormBorderStyle", "MaximizeBox", "MinimizeBox", "ControlBox", "RightToLeft",
             "ScaleMode", "Theme", "Cancel"],
    "Button": ["TextAlign"], "Label": ["TextAlign"], "LinkLabel": ["TextAlign", "LinkColor"],
    "TextBox": ["Multiline", "ReadOnly", "PasswordChar", "MaxLength", "TextAlign", "SelStart", "SelLength", "SelText"],
    "CheckBox": ["Checked", "Value"], "RadioButton": ["Checked", "Value"],
    "ListBox": ["Items", "ListIndex", "SelectedIndex", "ListCount", "SelectedItem"],
    "ComboBox": ["Items", "ListIndex", "SelectedIndex", "ListCount", "SelectedItem", "DropDownStyle"],
    "PictureBox": ["Image", "BorderStyle"], "ProgressBar": ["Minimum", "Maximum", "Value"],
    "NumericUpDown": ["Minimum", "Maximum", "Value"], "TrackBar": ["Minimum", "Maximum", "Value"],
    "Panel": ["BorderStyle"], "GroupBox": [], "TabControl": ["TabPages", "SelectedIndex"], "StatusBar": [],
    "Timer": ["Interval", "Enabled"],
    "OpenFileDialog": ["Title", "Filter", "FileName", "FileTitle", "InitialDirectory"],
    "SaveFileDialog": ["Title", "Filter", "FileName", "FileTitle", "InitialDirectory"],
    "ColorDialog": ["Color"], "FontDialog": ["FontName", "FontSize", "FontBold", "FontItalic"],
    "FolderBrowserDialog": ["SelectedPath", "Description"],
}
CLASS_METHODS = {
    "Form": ["Show", "ShowDialog", "Hide", "Close", "Load", "Unload", "Refresh", "Activate", "Move"],
    "ListBox": ["AddItem", "RemoveItem", "Clear", "List", "IndexOf"],
    "ComboBox": ["AddItem", "RemoveItem", "Clear", "List", "IndexOf"],
    "TextBox": ["Clear", "AppendText", "SelectAll"], "TabControl": ["TabCaption"], "Timer": ["Start", "Stop"],
    **{d: ["ShowDialog", "ShowOpen", "ShowSave", "ShowColor", "ShowFont", "ShowFolder"] for d in DIALOG_TYPES},
}
CONTROL_METHODS = ["SetFocus", "Refresh", "Move", "ZOrder", "BringToFront", "SendToBack", "Show", "Hide",
                   "PerformClick"]

_FUNC_RX = re.compile(r"^RF_API\s+(.+?)\b(\w+)\s*\(([^;]*)\);", re.M | re.S)
_CB_RX = re.compile(r"typedef\s+(.+?)\(RF_CALL\s*\*(\w+)\)\s*\(([^;]*)\);", re.S)
_STRUCT_RX = re.compile(r"typedef struct (\w+) \{(.*?)\} \1;", re.S)
_ENUM_RX = re.compile(r"\b(RF_(?:EV|CLASS|ALIGN)_\w+)\s*=\s*(0x[0-9A-Fa-f]+|\d+)")


def _param(text: str) -> dict:
    text = " ".join(text.split())
    m = re.match(r"(.*?)\(RF_CALL \*(\w+)\)\((.*)\)$", text) or re.match(r"(.*?)\(\*(\w+)\)\((.*)\)$", text)
    if m:
        return {"name": m.group(2), "type": "callback", "returns": m.group(1).strip(),
                "params": [_param(p) for p in _split(m.group(3))]}
    m = re.match(r"(.*?)(\w+)$", text)
    t, n = (m.group(1).strip(), m.group(2)) if m else (text, "")
    return {"name": n, "type": t.replace(" *", "*").replace("* ", "*")}


def _split(params: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in params:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip() and cur.strip() != "void":
        out.append(cur)
    return [p.strip() for p in out if p.strip()]


def api_description() -> dict:
    """The ABI of radforms.h as data: functions, callback types, structs, constants, control classes."""
    head = RADFORMS_H.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", head, flags=re.S)
    ver = re.search(r"#define RF_ABI_VERSION (\d+)", code)
    funcs = [{"name": m.group(2), "returns": " ".join(m.group(1).split()).replace(" *", "*"),
              "params": [_param(p) for p in _split(m.group(3))]} for m in _FUNC_RX.finditer(code)]
    cbs = [{"name": m.group(2), "returns": " ".join(m.group(1).split()),
            "params": [_param(p) for p in _split(m.group(3))]} for m in _CB_RX.finditer(code)]
    structs = []
    for m in _STRUCT_RX.finditer(code):
        fields = []
        body = m.group(2)
        for decl in re.split(r";\s*", body):
            decl = " ".join(decl.split())
            if not decl:
                continue
            if "(" in decl:
                fields.append(_param(decl))
                continue
            first = re.match(r"((?:const\s+)?(?:unsigned\s+long|unsigned|int|double|long|char|void|rf_\w+)\s*\**)\s*(.*)$", decl)
            if not first:
                continue
            base = first.group(1).strip()
            for n in first.group(2).split(","):
                n = n.strip()
                stars = n.count("*")
                fields.append({"name": n.strip("* "), "type": (base + "*" * stars).replace(" *", "*")})
        structs.append({"name": m.group(1), "fields": fields})
    consts = {k: int(v, 0) for k, v in _ENUM_RX.findall(code)}
    for k, v in re.findall(r"#define\s+(RF_\w+|RADFORMS_VERSION)\s+(0x[0-9A-Fa-f]+|\d+)u?\b", code):
        consts[k] = int(v, 0)
    classes = []
    from ...controls import CONTROL_TYPES as CT
    for name in ["Form", "Button", "Label", "TextBox", "CheckBox", "RadioButton", "ListBox", "ComboBox",
                 "PictureBox", "ProgressBar", "NumericUpDown", "TrackBar", "Panel", "GroupBox", "TabControl",
                 "LinkLabel", "StatusBar", "Timer", *DIALOG_TYPES]:
        ct = CT.get(name)
        nonvisual = name in NONVISUAL_TYPES
        events = (["Load", "Activated", "Deactivate", "Resize", "FormClosing", "FormClosed", "Click", "DoubleClick",
                   "MouseDown", "MouseUp", "MouseMove", "MouseWheel", "KeyDown", "KeyUp", "KeyPress"] if name == "Form"
                  else (ct.all_events() if ct else []))
        props = CLASS_PROPS.get(name, []) if name == "Form" or nonvisual else \
            COMMON_PROPS + [p for p in CLASS_PROPS.get(name, []) if p not in COMMON_PROPS]
        classes.append({"name": name, "builtin": True, "container": bool(ct and ct.container),
                        "nonvisual": nonvisual, "properties": props, "events": events,
                        "methods": CLASS_METHODS.get(name, []) + ([] if nonvisual or name == "Form" else CONTROL_METHODS)})
    for cls, src in module_classes().items():
        text = src.read_text(encoding="utf-8", errors="replace")

        def field(key):
            m = re.search(rf"\.{key}\s*=\s*\"([^\"]*)\"", text) or re.search(rf"k\.{key}\s*=\s*\"([^\"]*)\"", text)
            return [x for x in (m.group(1).split(",") if m else []) if x]
        classes.append({"name": cls, "builtin": False, "module": src.name, "container": "RF_CLASS_CONTAINER" in text,
                        "nonvisual": "RF_CLASS_NONVISUAL" in text, "ownerdraw": "RF_CLASS_OWNERDRAW" in text,
                        "properties": COMMON_PROPS + field("properties"), "events": field("events"),
                        "methods": field("methods") + CONTROL_METHODS})
    return {"library": "radforms", "abi_version": int(ver.group(1)) if ver else 0, "header": "radforms.h",
            "calling_convention": "cdecl", "strings": "UTF-8, NUL-terminated; returned strings are valid until "
            "16 more strings are returned", "handles": "rf_handle = opaque pointer",
            "functions": funcs, "callbacks": cbs, "structs": structs, "constants": consts, "classes": classes}


def write_api_json(path: Path | None = None) -> Path:
    import json
    path = Path(path or API_JSON)
    path.write_text(json.dumps(api_description(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_msvc_lib(out_dir: Path, log=print) -> Path | None:
    """radforms.lib for MSVC link / .NET NativeAOT (DirectPInvoke + NativeLibrary) / Rust msvc targets:
    the core + every module, compiled with /Zl so it links with the static (/MT) or dynamic (/MD) CRT.
    None when Visual Studio's C++ tools are not installed."""
    from ...languages.c_bridge import VS_INSTALLER, find_vcvars
    vcvars = find_vcvars()
    if not vcvars:
        log("MSVC (Visual Studio C++ tools) not found: radforms.lib is not built")
        return None
    out_dir = Path(out_dir)
    obj = out_dir / "msvc_obj"
    obj.mkdir(parents=True, exist_ok=True)
    mods = sorted(MODULES_DIR.glob("*.c")) if MODULES_DIR.is_dir() else []
    allsrc = obj / "rf_modules_all.c"
    allsrc.write_text(modules_source(mods).replace("void rad_modules_init(void)", "void rf_modules_register_all(void)"),
                      encoding="utf-8")
    srcs = " ".join(f'"{s}"' for s in [RADFORMS_C, *mods, allsrc])
    lib = out_dir / "radforms.lib"
    bat = obj / "build.bat"
    bat.write_text(f'@echo off\r\nset "PATH={VS_INSTALLER};%PATH%"\r\ncall "{vcvars}" >nul\r\n'
                   f'cl /nologo /c /O1 /Gy /GS- /Zl /utf-8 /TC /W3 /I "{RADFORMS_DIR}" {srcs}\r\n'
                   f'if errorlevel 1 exit /b 1\r\nlib /nologo /OUT:"{lib}" *.obj\r\n', encoding="utf-8")
    r = subprocess.run(["cmd", "/c", str(bat)], cwd=str(obj), capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not lib.is_file():
        log("MSVC build of radforms.lib failed:\n" + (r.stdout + r.stderr).strip()[-2000:])
        return None
    shutil.copy2(RADFORMS_H, out_dir / "radforms.h")
    log(f"MSVC library: {lib} ({lib.stat().st_size // 1024} KB)")
    return lib
