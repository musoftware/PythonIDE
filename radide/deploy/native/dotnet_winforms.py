"""Native build for C# and PowerShell projects: a real WinForms exe, no Python, no GUI Bridge host.

The .form files become WinForms designer code (RadForm_<Form>.InitializeComponent, like Form1.Designer.cs);
the project's code is compiled unchanged against a thin runtime (dotnet/RadWinForms.cs) that keeps the GUI
Bridge client API (lblOut.Text = "Hi", MsgBox, Show("Form2"), radcall ...) but works on the controls
directly. Handlers are found like the bridge does: static methods named <Control>_<Event>.

Publish options (PublishConfig.dotnet_target; each falls back to the others when it cannot be built):

  standalone  (default) dotnet publish self-contained single file, compressed, win-x64: one exe, nothing to
              install (~60 MB). Trimming is off: WinForms is not trim-safe (tested: the program breaks).
  framework   dotnet publish framework-dependent single-file apphost (~200 KB): needs the .NET Desktop Runtime.
  netfx       Roslyn csc (the SDK's csc.dll, or the Microsoft.Net.Compilers.Toolset package from nuget.org when no
              SDK is installed) against the .NET Framework 4.x assemblies of Windows: a ~50 KB exe for the
              .NET Framework 4.8 that is part of Windows 10/11. Not for .NET 5+ APIs or NuGet packages.

Control types come from a data table (dotnet/controls.json + dotnet/*.controls.json + <project>/dotnet.controls.json),
so a control library can add its types (with a project / dll reference) without editing this generator.

PowerShell: the exe hosts a Windows PowerShell 5.1 runspace (System.Management.Automation is part of
Windows) with the project's scripts embedded as resources; the GUI Bridge client Rad.ps1 is loaded unchanged
with RadSend/RadAsk redirected to the WinForms runtime. Scripts that need PowerShell 7 syntax fall back.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from ...controls import CONTROL_TYPES, FORM_EVENTS, parse_anchor
from ...model import Form, Project
from . import NativeUnsupported
from ._forms import copy_data, dir_size, fresh_dir, lit, load_forms, num, problems, rgb, size_text

LANGS = ("csharp-bridge", "powershell-bridge")
NAME = "native WinForms (.NET, no Python)"
HERE = Path(__file__).resolve().parent / "dotnet"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DIALOGS = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")
CONTROL_MAP = HERE / "controls.json"
PROJECT_MAP = "dotnet.controls.json"
TARGETS = ("standalone", "framework", "netfx")
FRAMEWORK_REFS = ("mscorlib.dll", "System.dll", "System.Core.dll", "System.Drawing.dll", "System.Windows.Forms.dll",
                  "Microsoft.CSharp.dll", "System.Xml.dll", "System.Xml.Linq.dll", "System.Data.dll",
                  "System.Net.Http.dll", "System.Numerics.dll", "System.Runtime.Serialization.dll")
GLOBAL_USINGS = ("System", "System.Collections.Generic", "System.IO", "System.Linq", "System.Net.Http",
                 "System.Threading", "System.Threading.Tasks")
# members of Form / Control a field must not hide (such controls get a c_ prefix)
RESERVED = {"Text", "Name", "Left", "Top", "Width", "Height", "Size", "Location", "Controls", "Font", "Icon", "Menu",
            "Visible", "Enabled", "Tag", "Parent", "Handle", "Client", "Tips", "Items", "RadName", "Close", "Show",
            "Hide", "Focus", "Bounds", "Region", "Cursor", "Capture", "Container", "Site", "Events", "Owner",
            "Opacity", "Padding", "Margin", "Dock", "Anchor", "Register", "Wire", "Fire", "F", "Img", "Lines",
            "MenuHeight", "Activate", "Refresh", "Update", "Invalidate", "BackColor", "ForeColor", "Components",
            "InitializeComponent", "Dispose", "Invoke", "Scale", "Select", "Validate", "Layout", "Load", "Closed",
            "Closing", "Shown", "Resize", "Move", "Click", "Paint", "Leave", "Enter", "Created", "Disposing",
            "ClientSize", "ClientRectangle", "WindowState", "TopMost", "ActiveControl", "Modal", "MdiParent"}
TAB_PAGE_X, TAB_PAGE_Y = 2, 24
TOOLSET = "microsoft.net.compilers.toolset"
NUGET = "https://api.nuget.org/v3-flatcontainer"


# ====================================================================== tools
def control_map(folder: Path | None = None) -> dict:
    """.form type -> {"type": .NET type, "codegen"?, "container"?, "nonvisual"?, "props"?, "events"?, "reference"?}
    from dotnet/controls.json + dotnet/*.controls.json + <project>/dotnet.controls.json (later files win);
    the "references" of all files are returned under the key "__references__"."""
    files = [CONTROL_MAP] + sorted(HERE.glob("*.controls.json"))
    if folder is not None and (Path(folder) / PROJECT_MAP).is_file():
        files.append(Path(folder) / PROJECT_MAP)
    out: dict = {}
    refs: dict = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for k, v in (data.get("controls") or {}).items():
            if isinstance(v, dict) and v.get("type"):
                out[k] = v
        for k, v in (data.get("references") or {}).items():
            if isinstance(v, dict):
                base = f.parent
                refs[k] = {kk: str((base / vv).resolve()) if kk in ("project", "dll") and not Path(vv).is_absolute()
                           else vv for kk, vv in v.items()}
    out["__references__"] = refs
    return out


def _local() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RADIDE"


def framework_dir() -> Path | None:
    """The .NET Framework 4.x folder of Windows (the reference assemblies of the net48 build)."""
    win = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Microsoft.NET"
    for sub in ("Framework64", "Framework"):
        d = win / sub / "v4.0.30319"
        if (d / "System.Windows.Forms.dll").is_file() and (d / "mscorlib.dll").is_file():
            return d
    return None


def sma_dll() -> str:
    """System.Management.Automation.dll of Windows PowerShell 5.1 (GAC)."""
    win = os.environ.get("SystemRoot", r"C:\Windows")
    hits = sorted(glob.glob(os.path.join(win, "Microsoft.NET", "assembly", "GAC_MSIL", "System.Management.Automation",
                                         "*", "System.Management.Automation.dll")), reverse=True)
    return hits[0] if hits else ""


def dotnet() -> str:
    try:
        from ...languages.csharp_bridge import dotnet as _d
        return _d()
    except Exception:  # noqa: BLE001
        return shutil.which("dotnet") or ""


def _sdk_dirs() -> list[Path]:
    dn = dotnet()
    if not dn:
        return []
    root = Path(dn).resolve().parent / "sdk"
    dirs = [p for p in root.glob("*") if (p / "Roslyn" / "bincore" / "csc.dll").is_file()]

    def key(p: Path):
        return [int(x) if x.isdigit() else 0 for x in re.split(r"[.-]", p.name)[:4]]
    return sorted(dirs, key=key, reverse=True)


def roslyn(log=print, download: bool = True) -> list[str]:
    """Command prefix of a modern C# compiler (Roslyn): the SDK's csc.dll, else the Microsoft.Net.Compilers.Toolset
    package (MIT, nuget.org) whose net472 csc.exe runs on the .NET Framework of Windows. [] = none."""
    sdks = _sdk_dirs()
    if sdks:
        return [dotnet(), str(sdks[0] / "Roslyn" / "bincore" / "csc.dll")]
    root = _local() / "tools" / "roslyn"
    found = sorted(root.glob("*/tasks/net472/csc.exe"), reverse=True)
    if found:
        return [str(found[0])]
    if not download:
        return []
    try:
        ver = _toolset_version()
        dest = root / ver
        url = f"{NUGET}/{TOOLSET}/{ver}/{TOOLSET}.{ver}.nupkg"
        log(f"Downloading the C# compiler (Roslyn {ver}, MIT) from nuget.org ...")
        tmp = root / f"{TOOLSET}.{ver}.nupkg"
        root.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        with zipfile.ZipFile(tmp) as z:
            for m in z.namelist():
                if m.startswith("tasks/net472/") and not m.endswith("/"):
                    target = (dest / m).resolve()
                    if not str(target).startswith(str(dest.resolve())):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(m) as src, open(target, "wb") as out:
                        shutil.copyfileobj(src, out)
        tmp.unlink(missing_ok=True)
        exe = dest / "tasks" / "net472" / "csc.exe"
        return [str(exe)] if exe.is_file() else []
    except Exception as e:  # noqa: BLE001 - offline: the caller falls back
        log(f"Could not download the C# compiler: {e}")
        return []


def _toolset_version() -> str:
    req = urllib.request.Request(f"{NUGET}/{TOOLSET}/index.json", headers={"User-Agent": "RAD-IDE"})
    with urllib.request.urlopen(req, timeout=60) as r:
        versions = json.loads(r.read().decode("utf-8"))["versions"]
    stable = [v for v in versions if "-" not in v]
    return (stable or versions)[-1]


def _run(cmd, cwd: Path, log, env=None) -> tuple[int, str]:
    log("> " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd[:3]) + (" ..." if len(cmd) > 3 else ""))
    try:
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, env=env, creationflags=NO_WINDOW,
                           timeout=900)
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)
    text = (r.stdout + r.stderr).decode("utf-8", "replace").replace("\r\n", "\n")
    return r.returncode, text


def _quiet_env() -> dict:
    return dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
                DOTNET_CLI_UI_LANGUAGE="en", MSBUILDTERMINALLOGGER="off")


# ====================================================================== check
def _packages(folder: Path) -> list[tuple[str, str]]:
    proj = Path(folder) / "_build" / "csharp" / "RadApp.csproj"
    if not proj.is_file():
        return []
    text = proj.read_text(encoding="utf-8", errors="replace")
    return re.findall(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?', text)


def check(folder, project: Project, cfg) -> list[str]:
    folder = Path(folder)
    lang = _lang(project)
    exts = (".cs",) if lang == "csharp-bridge" else (".ps1",)
    cmap = control_map(folder)
    out = problems(folder, project, lang, {k for k in cmap if not k.startswith("__")}, "WinForms", exts)
    if framework_dir() is None and lang == "powershell-bridge":
        out.append("the .NET Framework 4 of Windows was not found")
    if lang == "powershell-bridge":
        if not sma_dll():
            out.append("Windows PowerShell 5.1 (System.Management.Automation) was not found")
        for name in [m for m in project.modules if m.lower().endswith(".ps1")] + [f + ".ps1" for f in project.forms]:
            p = folder / name
            if p.is_file() and re.search(r"(?im)^\s*#requires\s+-version\s+([6-9]|\d\d)",
                                         p.read_text(encoding="utf-8", errors="replace")):
                out.append(f"{name} requires PowerShell 7 (#Requires -Version)")
    return out


def _lang(project: Project) -> str:
    from ..build import startup_language
    return startup_language(project)


# ====================================================================== WinForms code
class _Gen:
    def __init__(self, form: Form, handlers: set[str], cmap: dict | None = None):
        self.form = form
        self.cmap = cmap or control_map()
        self.handlers = {h.lower() for h in handlers}
        self.fields: dict[str, str] = {}           # control name -> field identifier
        for c in form.controls:
            n = c.name
            ok = re.fullmatch(r"[A-Za-z_]\w*", n) and n not in RESERVED
            self.fields[n] = n if ok else "c_" + re.sub(r"\W", "_", n)

    def f(self, name: str) -> str:
        return "this." + self.fields[name]

    # ---------------------------------------------------------------- pieces
    @staticmethod
    def color(v) -> str | None:
        c = rgb(v)
        return f"System.Drawing.Color.FromArgb({c[0]}, {c[1]}, {c[2]})" if c else None

    @staticmethod
    def align(v, default="MiddleLeft") -> str:
        return {"Left": "MiddleLeft", "Center": "MiddleCenter", "Right": "MiddleRight"}.get(str(v), default)

    def common(self, c, L: list[str], var: str) -> None:
        p = c.props
        L.append(f"{var}.Name = {lit(c.name)};")
        L.append(f"{var}.Location = new System.Drawing.Point({num(p.get('Left'))}, {num(p.get('Top'))});")
        L.append(f"{var}.Size = new System.Drawing.Size({num(p.get('Width'), 75)}, {num(p.get('Height'), 23)});")
        L.append(f"{var}.TabIndex = {num(p.get('TabIndex'))};")
        font = (str(p.get("FontName") or "Segoe UI"), float(p.get("FontSize") or 9), bool(p.get("FontBold")),
                bool(p.get("FontItalic")))
        if font != ("Segoe UI", 9.0, False, False):
            L.append(f"{var}.Font = F({lit(font[0])}, {font[1]:g}F, {str(font[2]).lower()}, {str(font[3]).lower()});")
        for prop in ("BackColor", "ForeColor"):
            col = self.color(p.get(prop))
            if col:
                L.append(f"{var}.{prop} = {col};")
        dock = str(p.get("Dock") or "None")
        if dock in ("Top", "Bottom", "Left", "Right", "Fill"):
            L.append(f"{var}.Dock = System.Windows.Forms.DockStyle.{dock};")
        else:
            edges = parse_anchor(p.get("Anchor", "Top, Left"))
            if edges != {"Top", "Left"}:
                expr = " | ".join(f"System.Windows.Forms.AnchorStyles.{e}" for e in ("Top", "Bottom", "Left", "Right")
                                  if e in edges) or "System.Windows.Forms.AnchorStyles.None"
                L.append(f"{var}.Anchor = (System.Windows.Forms.AnchorStyles)({expr});")
        if p.get("Enabled") is False:
            L.append(f"{var}.Enabled = false;")
        if p.get("Visible") is False:
            L.append(f"{var}.Visible = false;")
            L.append(f"RadApp.MarkHidden({var});")
        if p.get("ToolTip"):
            L.append(f"this.Tips.SetToolTip({var}, {lit(p['ToolTip'])});")

    def entry(self, c) -> dict:
        return self.cmap.get(c.type) or {}

    # container / non-visual come from the control map too, so a library control works even when its designer
    # package is not installed (Form.load gives it a placeholder type)
    def is_nonvisual(self, c) -> bool:
        return bool(c.ctype.nonvisual or self.entry(c).get("nonvisual"))

    def is_container(self, c) -> bool:
        return bool(c.ctype.container or self.entry(c).get("container"))

    def ordered(self) -> list:
        vis = [c for c in self.form.controls if not self.is_nonvisual(c)]
        out: list = []

        def visit(parent: str):
            for c in vis:
                if c.parent == parent and c not in out:
                    out.append(c)
                    if self.is_container(c):
                        visit(c.name)
        visit("")
        for c in vis:                   # orphans (parent missing) go to the form
            if c not in out:
                c.props["Parent"] = ""
                out.append(c)
        return out

    def generic_props(self, c, var: str, L: list[str]) -> None:
        """Mapped properties of a library control: {"FormProp": "NetProp[:enum:Type|:color|:image|:date|:json]"}.
        Lists / objects (ribbon tabs, nodes ...) become JSON text; whole floats become ints."""
        for fprop, spec in (self.entry(c).get("props") or {}).items():
            if fprop not in c.props or c.props[fprop] in (None, ""):
                continue
            v = c.props[fprop]
            target, _, kind = str(spec).partition(":")
            if kind.startswith("enum:"):
                L.append(f"{var}.{target} = {kind[5:]}.{re.sub(r'[^A-Za-z0-9_]', '', str(v))};")
            elif kind == "color":
                col = self.color(v)
                if col:
                    L.append(f"{var}.{target} = {col};")
            elif kind == "image":
                L.append(f"{var}.{target} = Img({lit(v)});")
            elif kind == "date":
                L.append(f"{{ System.DateTime d; if (System.DateTime.TryParse({lit(v)}, System.Globalization.CultureInfo.InvariantCulture, "
                         f"System.Globalization.DateTimeStyles.None, out d)) {var}.{target} = d; }}")
            elif kind == "json" or isinstance(v, (list, dict)):
                L.append(f"{var}.{target} = {lit(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))};")
            elif isinstance(v, float) and v.is_integer() and kind != "float":
                L.append(f"{var}.{target} = {int(v)};")
            elif isinstance(v, bool):
                L.append(f"{var}.{target} = {str(v).lower()};")
            elif isinstance(v, (int, float)):
                L.append(f"{var}.{target} = {v:g};" if isinstance(v, float) else f"{var}.{target} = {v};")
            else:
                L.append(f"{var}.{target} = {lit(v)};")

    def control(self, c) -> list[str]:
        p, var = c.props, self.f(c.name)
        t = self.entry(c).get("codegen") or ""
        L = ["// ", f"// {c.name}", "// "]
        self.common(c, L, var)
        if not t:              # a control of a referenced library: generic code
            if "Text" in p and "Text" not in (self.entry(c).get("props") or {}):
                L.append(f"{var}.Text = {lit(p.get('Text') or '')};")
            self.generic_props(c, var, L)
            return L
        text = str(p.get("Text", "") or "")
        if t in ("Button", "Label", "CheckBox", "RadioButton", "GroupBox", "LinkLabel", "StatusBar", "TextBox"):
            L.append(f"{var}.Text = {lit(text)};")
        if t == "Button":
            if str(p.get("TextAlign", "Center")) != "Center":
                L.append(f"{var}.TextAlign = System.Drawing.ContentAlignment.{self.align(p.get('TextAlign'))};")
            L.append(f"{var}.UseVisualStyleBackColor = {'false' if p.get('BackColor') else 'true'};")
        elif t in ("Label", "LinkLabel", "StatusBar"):
            L.append(f"{var}.AutoSize = false;")
            L.append(f"{var}.TextAlign = System.Drawing.ContentAlignment.{self.align(p.get('TextAlign', 'Left'))};")
            if t == "StatusBar":
                L.append(f"{var}.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;")
                L.append(f"{var}.Padding = new System.Windows.Forms.Padding(4, 0, 0, 0);")
            if t == "LinkLabel":
                col = self.color(p.get("LinkColor"))
                if col:
                    L.append(f"{var}.LinkColor = {col};")
        elif t == "TextBox":
            if p.get("Multiline"):
                L += [f"{var}.Multiline = true;", f"{var}.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;"]
            else:
                L.append(f"{var}.AutoSize = false;")
            if p.get("ReadOnly"):
                L.append(f"{var}.ReadOnly = true;")
            if str(p.get("PasswordChar") or ""):
                L.append(f"{var}.PasswordChar = {chlit(str(p['PasswordChar'])[0])};")
            if num(p.get("MaxLength")) > 0:
                L.append(f"{var}.MaxLength = {num(p.get('MaxLength'))};")
        elif t in ("CheckBox", "RadioButton"):
            if p.get("Checked"):
                L.append(f"{var}.Checked = true;")
            L.append(f"{var}.UseVisualStyleBackColor = true;")
        elif t in ("ListBox", "ComboBox"):
            items = [s.strip() for s in str(p.get("Items") or "").split(";") if s.strip()]
            if t == "ListBox":
                L.append(f"{var}.IntegralHeight = false;")
            else:
                style = {"DropDown": "DropDown", "Simple": "Simple"}.get(str(p.get("DropDownStyle")), "DropDownList")
                L.append(f"{var}.DropDownStyle = System.Windows.Forms.ComboBoxStyle.{style};")
            if items:
                L.append(f"{var}.Items.AddRange(new object[] {{ {', '.join(lit(s) for s in items)} }});")
            if t == "ComboBox" and str(p.get("DropDownStyle")) in ("DropDown", "Simple") and text and text != c.name:
                L.append(f"{var}.Text = {lit(text)};")
        elif t == "PictureBox":
            L.append(f"{var}.SizeMode = System.Windows.Forms.PictureBoxSizeMode.CenterImage;")
            if p.get("Image"):
                L.append(f"{var}.Image = Img({lit(p['Image'])});")
        elif t in ("ProgressBar", "NumericUpDown", "TrackBar"):
            lo, hi = num(p.get("Minimum")), num(p.get("Maximum"), 100)
            hi = max(lo, hi)
            val = min(hi, max(lo, num(p.get("Value"))))
            if t == "TrackBar":
                L.append(f"{var}.AutoSize = false;")
            L += [f"{var}.Minimum = {lo};", f"{var}.Maximum = {hi};", f"{var}.Value = {val};"]
        elif t == "Panel":
            pass
        elif t == "TabControl":
            pages = [s.strip() for s in str(p.get("TabPages") or "").split(";") if s.strip()] or ["TabPage1"]
            cw = max(0, num(p.get("Width")) - 2 * TAB_PAGE_X)
            ch = max(0, num(p.get("Height")) - TAB_PAGE_Y - TAB_PAGE_X)
            for i, title in enumerate(pages):
                pv = f"{var}_page{i}"
                L += [f"{pv}.Text = {lit(title)};", f"{pv}.UseVisualStyleBackColor = true;",
                      f"{pv}.Size = new System.Drawing.Size({cw}, {ch});", f"{var}.Controls.Add({pv});"]
            sel = num(p.get("SelectedIndex"))
            if 0 < sel < len(pages):
                L.append(f"{var}.SelectedIndex = {sel};")
        elif t == "DateTimePicker":
            fmt = {"Long": "Long", "Time": "Time"}.get(str(p.get("Format")), "Short")
            L.append(f"{var}.Format = System.Windows.Forms.DateTimePickerFormat.{fmt};")
            if str(p.get("Value") or "").strip():
                L.append(f"{{ System.DateTime d; if (System.DateTime.TryParse({lit(p['Value'])}, "
                         f"System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, "
                         f"out d)) {var}.Value = d; }}")
        return L

    def tab_pages(self) -> dict[str, list[str]]:
        out = {}
        for c in self.form.controls:
            if c.type == "TabControl":
                pages = [s.strip() for s in str(c.props.get("TabPages") or "").split(";") if s.strip()] or ["TabPage1"]
                out[c.name] = [f"{self.f(c.name)}_page{i}" for i in range(len(pages))]
        return out

    def menu_lines(self, menu) -> tuple[list[str], list[str], list[str]]:
        """(field declarations, creation + setup lines, wiring lines) of a MenuStrip."""
        decl, L, wire = [], [], []
        counter = [0]
        mv = self.f(menu.name)

        def item_var(it) -> str:
            counter[0] += 1
            n = str(it.get("Name") or "")
            ident = re.sub(r"\W", "_", n) if n and re.fullmatch(r"[A-Za-z_]\w*", n) else f"mnuItem{counter[0]}"
            return f"mi_{ident}"

        def build(items, parent_expr):
            vars_ = []
            for it in items or []:
                if it.get("Text") == "-":
                    vars_.append("new System.Windows.Forms.ToolStripSeparator()")
                    continue
                v = item_var(it)
                decl.append(f"private System.Windows.Forms.ToolStripMenuItem {v};")
                L.append(f"this.{v} = new System.Windows.Forms.ToolStripMenuItem();")
                L.append(f"this.{v}.Text = {lit(it.get('Text', ''))};")
                if it.get("Name"):
                    L.append(f"this.{v}.Name = {lit(it['Name'])};")
                    L.append(f"this.Register({lit(it['Name'])}, this.{v});")
                if it.get("Items"):
                    build(it["Items"], f"this.{v}.DropDownItems")
                elif it.get("Name"):
                    wire.append(f"this.Wire(this.{v}, {lit(it['Name'])}, \"Click\");")
                vars_.append(f"this.{v}")
            if vars_:
                L.append(f"{parent_expr}.AddRange(new System.Windows.Forms.ToolStripItem[] {{ {', '.join(vars_)} }});")
        build(menu.props.get("Items"), f"{mv}.Items")
        return decl, L, wire

    # ---------------------------------------------------------------- the form class
    def code(self) -> str:
        form, fp = self.form, self.form.props
        n = form.name
        cls = "RadForm_" + re.sub(r"\W", "_", n)
        W, H = num(fp.get("Width"), 400), num(fp.get("Height"), 300)
        decl: list[str] = []
        create: list[str] = []
        setup: list[str] = []
        wire: list[str] = []
        tail: list[str] = []
        pages = self.tab_pages()
        visual = self.ordered()
        menu = form.menu()
        for c in visual:
            ctype = "global::" + self.entry(c)["type"]
            decl.append(f"private {ctype} {self.fields[c.name]};")
            create.append(f"{self.f(c.name)} = new {ctype}();")
            for pv in pages.get(c.name, []):
                decl.append(f"private System.Windows.Forms.TabPage {pv[5:]};")
                create.append(f"{pv} = new System.Windows.Forms.TabPage();")
        for c in visual:
            setup += self.control(c)
            setup.append(f"this.Register({lit(c.name)}, {self.f(c.name)});")
            events = CONTROL_TYPES[c.type].all_events() if c.type in CONTROL_TYPES else []
            events += [e for e in self.entry(c).get("events", []) if e not in events]
            used = [e for e in events if f"{c.name}_{e}".lower() in self.handlers]
            if used:
                wire.append(f"this.Wire({self.f(c.name)}, {lit(c.name)}, {', '.join(lit(e) for e in used)});")
        # children are added back-most first in the model; WinForms index 0 is the front-most: add in reverse
        parents: dict[str, list] = {}
        for c in visual:
            parents.setdefault(c.parent, []).append(c)
        by_name = {c.name: c for c in form.controls}
        adds = []
        for parent, kids in parents.items():
            page_prop = self.entry(by_name[parent]).get("pageProp") if parent in by_name else None
            for c in reversed(kids):
                if not parent:
                    target = "this.Client"
                elif parent in pages:
                    idx = num(c.props.get("TabPage"))
                    plist = pages[parent]
                    target = plist[idx] if 0 <= idx < len(plist) else plist[0]
                elif page_prop:            # a library container with pages (RmTabStrip ...): AddToPage(i, child)
                    adds.append(f"{self.f(parent)}.AddToPage({max(0, num(c.props.get(page_prop)))}, {self.f(c.name)});")
                    continue
                else:
                    target = self.f(parent)
                adds.append(f"{target}.Controls.Add({self.f(c.name)});")
        for c in [c for c in form.controls if self.is_nonvisual(c)]:
            v = self.f(c.name)
            kind = self.entry(c).get("codegen") or ""
            if kind == "MenuStrip":
                continue
            if not kind:               # a component of a referenced library
                ctype = "global::" + self.entry(c)["type"]
                decl.append(f"private {ctype} {self.fields[c.name]};")
                create.append(f"{v} = new {ctype}();")
                self.generic_props(c, v, setup)
                setup.append(f"this.Register({lit(c.name)}, {v});")
                used = [e for e in self.entry(c).get("events", []) if f"{c.name}_{e}".lower() in self.handlers]
                if used:
                    wire.append(f"this.Wire({v}, {lit(c.name)}, {', '.join(lit(e) for e in used)});")
            elif kind == "Timer":
                decl.append(f"private System.Windows.Forms.Timer {self.fields[c.name]};")
                create.append(f"{v} = new System.Windows.Forms.Timer();")
                setup.append(f"{v}.Interval = {max(1, num(c.props.get('Interval'), 100))};")
                setup.append(f"this.Register({lit(c.name)}, {v});")
                if f"{c.name}_tick".lower() in self.handlers:
                    wire.append(f"this.Wire({v}, {lit(c.name)}, \"Tick\");")
                if c.props.get("Enabled"):
                    tail.append(f"{v}.Enabled = true;")
            elif kind == "Dialog":
                decl.append(f"private RadDialog {self.fields[c.name]};")
                args = [f"Kind = {lit(c.type)}"]
                for k in ("Title", "Filter", "FileName", "InitialDirectory", "Color", "FontName", "SelectedPath"):
                    if k in c.props and c.props[k] not in (None, ""):
                        args.append(f"{k} = {lit(c.props[k])}")
                if "FontSize" in c.props:
                    args.append(f"FontSize = {float(c.props['FontSize'] or 9):g}F")
                create.append(f"{v} = new RadDialog {{ {', '.join(args)} }};")
                setup.append(f"this.Register({lit(c.name)}, {v});")
        menu_decl, menu_setup, menu_wire = ([], [], [])
        if menu is not None and menu.props.get("Items"):
            decl.append(f"private System.Windows.Forms.MenuStrip {self.fields[menu.name]};")
            create.append(f"{self.f(menu.name)} = new System.Windows.Forms.MenuStrip();")
            menu_decl, menu_setup, menu_wire = self.menu_lines(menu)
            decl += menu_decl
        # form events: Load / FormClosing / FormClosed come from RadFormBase's overrides
        fe = [e for e in FORM_EVENTS if f"{n}_{e}".lower() in self.handlers and e not in ("Load", "FormClosing", "FormClosed")]
        mouse = [e for e in fe if e in ("Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseWheel")]
        other = [e for e in fe if e not in mouse]
        if mouse:
            wire.append(f"this.Wire(this.Client, {lit(n)}, {', '.join(lit(e) for e in mouse)});")
        if other:
            wire.append(f"this.Wire(this, {lit(n)}, {', '.join(lit(e) for e in other)});")
        L = [f"/// <summary>Form {n} (generated from {n}.form by RAD IDE - do not edit).</summary>",
             f"public sealed class {cls} : RadFormBase", "{",
             *[f"    {d}" for d in decl], "",
             f"    public {cls}() : base({lit(n)})", "    {", "        InitializeComponent();", "    }", "",
             "    private void InitializeComponent()", "    {"]
        body = list(create)
        if menu is not None and menu_setup:
            body += menu_setup
        body += [f"this.ClientSize = new System.Drawing.Size({W}, {H});",
                 f"this.Client.Bounds = new System.Drawing.Rectangle(0, 0, {W}, {H});"]
        containers = [c for c in visual if self.is_container(c)]
        body += ["this.Client.SuspendLayout();"] + [f"{self.f(c.name)}.SuspendLayout();" for c in containers]
        body += ["this.SuspendLayout();"]
        body += setup
        body += adds
        body += ["// ", f"// {n}", "// ",
                 "this.AutoScaleDimensions = new System.Drawing.SizeF(96F, 96F);",
                 "this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Dpi;",
                 f"this.Text = {lit(fp.get('Text', n))};"]
        col = self.color(fp.get("BackColor"))
        if col:
            body.append(f"this.SetBack({col});")
        body.append("this.StartPosition = System.Windows.Forms.FormStartPosition."
                    + ("CenterScreen" if fp.get("StartPosition", "CenterScreen") == "CenterScreen" else "WindowsDefaultLocation")
                    + ";")
        if fp.get("FormBorderStyle") == "FixedSingle":
            body += ["this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;", "this.MaximizeBox = false;"]
        if fp.get("TopMost"):
            body.append("this.TopMost = true;")
        if fp.get("WindowState") == "Maximized":
            body.append("this.WindowState = System.Windows.Forms.FormWindowState.Maximized;")
        icon = str(fp.get("Icon") or "")
        if icon.lower().endswith(".ico"):
            body.append(f"try {{ this.Icon = new System.Drawing.Icon(RadApp.Res({lit(icon)})); }} catch (System.Exception) {{ }}")
        else:
            body.append("try { this.Icon = System.Drawing.Icon.ExtractAssociatedIcon(System.Windows.Forms.Application.ExecutablePath); } "
                        "catch (System.Exception) { }")
        body.append("this.Controls.Add(this.Client);")
        if menu is not None and menu_setup:
            mv = self.f(menu.name)
            body += [f"{mv}.Name = {lit(menu.name)};", f"this.Controls.Add({mv});", f"this.MainMenuStrip = {mv};",
                     f"this.ClientSize = new System.Drawing.Size({W}, {H} + {mv}.PreferredSize.Height);"]
        body += [f"{self.f(c.name)}.ResumeLayout(false);" for c in reversed(containers)]
        body += ["this.Client.ResumeLayout(false);", "this.ResumeLayout(false);", "this.PerformLayout();"]
        if str(fp.get("RightToLeft", "")).lower() in ("true", "yes", "1"):     # Arabic: mirrored layout
            body += ["this.RightToLeft = System.Windows.Forms.RightToLeft.Yes;", "RadApp.MirrorLayout(this);"]
        refs = self.cmap.get("__references__") or {}
        used = {self.entry(c).get("reference") for c in form.controls} - {None, ""}
        for r in sorted(used):
            init = (refs.get(r) or {}).get("formInit")
            if init:                   # e.g. RadIDE.Controls: the form Theme -> RmThemeManager
                body.append(str(init).replace("{Theme}", lit(fp.get("Theme") or "")))
        body.append("// RAD IDE: event handlers (<Control>_<Event>) and timers")
        body += wire + menu_wire + tail
        L += [f"        {b}" for b in body]
        L += ["    }", "}", ""]
        return "\n".join(L)


def forms_code(forms: list[Form], handlers: set[str], cmap: dict | None = None) -> str:
    out = ["// AUTO-GENERATED by RAD IDE (native WinForms build) from the project's .form files.",
           "#nullable disable", "namespace RadNative", "{"]
    for f in forms:
        out += ["    " + line if line else "" for line in _Gen(f, handlers, cmap).code().splitlines()]
    out.append("}")
    return "\n".join(out) + "\n"


def assembly_info(cfg, project: Project) -> str:
    title = cfg.app_name or project.name
    company = cfg.publisher or title
    v = cfg.numeric_version()
    return "\n".join([
        "// AUTO-GENERATED by RAD IDE: version resource of the exe (Properties > Details).",
        "using System.Reflection;",
        f"[assembly: AssemblyTitle({lit(title)})]",
        f"[assembly: AssemblyProduct({lit(title)})]",
        f"[assembly: AssemblyCompany({lit(company)})]",
        f"[assembly: AssemblyCopyright({lit('(c) ' + cfg.publisher if cfg.publisher else '')})]",
        f"[assembly: AssemblyVersion({lit(v)})]",
        f"[assembly: AssemblyFileVersion({lit(v)})]",
        f"[assembly: AssemblyInformationalVersion({lit(cfg.version or '1.0.0')})]", ""])


def program_cs(project: Project, cfg, forms: list[Form], ps_resources: list[str] | None, handlers: list[str]) -> str:
    startup = project.startup or forms[0].name
    title = cfg.app_name or project.name
    L = ["// AUTO-GENERATED by RAD IDE (native WinForms build): the program's entry point.", "#nullable disable",
         "namespace RadNative", "{", "    static class RadProgram", "    {", "        [System.STAThread]",
         "        static int Main(string[] args)", "        {", "            RadApp.LoadEmbedded();",
         f"            RadApp.Title = {lit(title)};"]
    if ps_resources is None:
        L.append("            RadApp.Handlers = new CsHandlers(typeof(RadProgram).Assembly);")
    else:
        L.append("            var host = new PsHost(new string[] { " + ", ".join(lit(h) for h in handlers) + " });")
        L.append("            RadApp.Handlers = host;")
        for r in ps_resources:
            L.append(f"            host.Load({lit(r)});")
    for f in forms:
        cls = "RadForm_" + re.sub(r"\W", "_", f.name)
        L.append(f"            RadApp.Register({lit(f.name)}, () => new {cls}());")
    L += [f"            return RadApp.Run({lit(startup)});", "        }", "    }", "}", ""]
    return "\n".join(L)


# ====================================================================== build
def _write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8-sig")


def _designers(folder: Path, project: Project, lang: str, src: Path, forms: list[Form]) -> None:
    from ...languages import get_plugin
    plugin = get_plugin(lang)
    for f in forms:
        code_file = folder / plugin.code_file(f.name) if hasattr(plugin, "code_file") else folder / f"{f.name}{plugin.code_ext}"
        user = code_file.read_text(encoding="utf-8", errors="replace") if code_file.is_file() else ""
        _write(src / f"{f.name}_designer{plugin.code_ext}", plugin.generate_designer(f, user))


def chlit(ch: str) -> str:
    return "'" + {"'": "\\'", "\\": "\\\\"}.get(ch, ch) + "'"


def _rsp_arg(a: str) -> str:
    """One csc response-file argument; values with spaces are quoted."""
    if " " not in a:
        return a
    if a.startswith("/") and ":" in a:
        k, v = a.split(":", 1)
        return f'{k}:"{v}"'
    return f'"{a}"'


def _compile_net48(cs_files: list[Path], out_exe: Path, icon: Path | None, log, extra_refs=(), resources=()) -> tuple[bool, str]:
    fw = framework_dir()
    if fw is None:
        return False, "the .NET Framework 4 of Windows was not found"
    csc = roslyn(log)
    if not csc:
        return False, "no C# compiler (install the .NET SDK, or allow the download of the Roslyn compiler)"
    rsp = out_exe.parent.parent / "csc.rsp"
    args = ["/nologo", "/noconfig", "/nostdlib+", "/target:winexe", "/optimize+", "/debug-", "/langversion:latest",
            "/filealign:512", "/platform:anycpu", "/utf8output", "/deterministic+", "/main:RadNative.RadProgram",
            "/nowarn:CS0168,CS0219,CS8981,CS1998,CS0162,CS0414,CS0649,CS0169,CS1701,CS1702", f"/out:{out_exe}"]
    args += [f"/r:{fw / r}" for r in FRAMEWORK_REFS if (fw / r).is_file()]
    args += [f"/r:{r}" for r in extra_refs]
    if icon is not None:
        args.append(f"/win32icon:{icon}")
    for path, name in resources:
        args.append(f"/resource:{path},{name}")
    args += [str(p) for p in cs_files]
    rsp.write_text("\n".join(f'"{a}"' if " " in a and not a.startswith("/") else
                             (a.split(":", 1)[0] + ':"' + a.split(":", 1)[1] + '"' if " " in a else a) for a in args),
                   encoding="utf-8")
    code, text = _run(csc + [f"@{rsp}"], rsp.parent, log, env=_quiet_env())
    return code == 0 and out_exe.is_file(), text


def _compile_sdk(cs_files: list[Path], out_dir: Path, exe_base: str, icon: Path | None, packages, log,
                 standalone: bool = False, trim: bool = False, refs: dict | None = None) -> tuple[bool, str, Path | None]:
    """dotnet publish: standalone = self-contained single file (compressed, native libraries inside), else a
    framework-dependent single-file apphost. trim = PublishTrimmed (WinForms is not trim-safe: off by default)."""
    dn = dotnet()
    if not dn or not _sdk_dirs():
        return False, "the .NET SDK was not found", None
    proj_dir = fresh_dir(out_dir / "sdkproj")
    major = 8
    try:
        from ...languages.csharp_bridge import target_framework
        m = re.match(r"net(\d+)", target_framework())
        if m:
            major = min(int(m.group(1)), 8) if int(m.group(1)) >= 8 else int(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    items = "\n".join(f'    <Compile Include="{p}" />' for p in cs_files)
    pkgs = "\n".join(f'    <PackageReference Include="{n}"' + (f' Version="{v}"' if v else "") + " />" for n, v in packages)
    for r in (refs or {}).values():          # referenced control libraries (control_map "references")
        if r.get("project") and Path(r["project"]).is_file():
            pkgs += f'\n    <ProjectReference Include="{r["project"]}" />'
        elif r.get("dll") and Path(r["dll"]).is_file():
            pkgs += f'\n    <Reference Include="{Path(r["dll"]).stem}"><HintPath>{r["dll"]}</HintPath></Reference>'
    icon_xml = f"<ApplicationIcon>{icon}</ApplicationIcon>" if icon else ""
    mode = ("    <SelfContained>true</SelfContained>\n    <IncludeNativeLibrariesForSelfExtract>true</IncludeNativeLibrariesForSelfExtract>\n"
            "    <EnableCompressionInSingleFile>true</EnableCompressionInSingleFile>\n    <InvariantGlobalization>true</InvariantGlobalization>\n"
            "    <UseSystemResourceKeys>true</UseSystemResourceKeys>\n    <GenerateRuntimeConfigurationFiles>true</GenerateRuntimeConfigurationFiles>\n"
            if standalone else "    <SelfContained>false</SelfContained>\n")
    if trim:
        mode += ("    <PublishTrimmed>true</PublishTrimmed>\n    <_SuppressWinFormsTrimError>true</_SuppressWinFormsTrimError>\n"
                 "    <TrimMode>partial</TrimMode>\n")
    csproj = f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net{major}.0-windows</TargetFramework>
    <UseWindowsForms>true</UseWindowsForms>
    <ImplicitUsings>disable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <LangVersion>latest</LangVersion>
    <AssemblyName>{exe_base}</AssemblyName>
    <RootNamespace>RadNative</RootNamespace>
    <StartupObject>RadNative.RadProgram</StartupObject>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
{mode}    <PublishSingleFile>true</PublishSingleFile>
    <DebugType>none</DebugType>
    <SatelliteResourceLanguages>en</SatelliteResourceLanguages>
    <NoWarn>$(NoWarn);CS0168;CS0219;CS8981;CS1998;CS0162;CS0414;CS0649;CS0169;CA1416</NoWarn>
    {icon_xml}
  </PropertyGroup>
  <ItemGroup>
    <TrimmerRootAssembly Include="{exe_base}" />
  </ItemGroup>
  <ItemGroup>
{items}
{pkgs}
  </ItemGroup>
</Project>
"""
    (proj_dir / f"{exe_base}.csproj").write_text(csproj, encoding="utf-8")
    pub = fresh_dir(out_dir / "sdkout")
    props = []
    for r in (refs or {}).values():          # a multi-targeting library builds (and restores) only what the exe needs
        if r.get("targetsProperty") and r.get("project") and Path(r["project"]).is_file():
            props.append(f"-p:{r['targetsProperty']}=net{major}.0-windows")
    code, text = _run([dn, "publish", str(proj_dir / f"{exe_base}.csproj"), "-c", "Release", "-o", str(pub), "-nologo",
                       "-v", "q", "-clp:NoSummary", *props], proj_dir, log, env=_quiet_env())
    exe = pub / f"{exe_base}.exe"
    return code == 0 and exe.is_file(), text, pub if exe.is_file() else None


def _errors(text: str, src: Path, limit: int = 12) -> list[str]:
    out, seen = [], set()
    for line in text.splitlines():
        if ": error " in line or " error CS" in line or "error MSB" in line:
            line = re.sub(r"\s+\[[^\[\]]*\.csproj\]\s*$", "", line).replace(str(src) + os.sep, "").strip()
            if line not in seen:
                seen.add(line)
                out.append(line)
    return out[:limit] or [l for l in text.strip().splitlines()[-6:]]


def _ps_parse_errors(files: list[Path]) -> list[str]:
    """Syntax errors of the scripts as Windows PowerShell 5.1 sees them (PowerShell 7 syntax is an error)."""
    winps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not winps.is_file() or not files:
        return []
    script = ("$ErrorActionPreference='Stop'; foreach ($f in $args) { $t=$null; $e=$null; "
              "$text=[IO.File]::ReadAllText($f,[Text.Encoding]::UTF8); "
              "[void][System.Management.Automation.Language.Parser]::ParseInput($text,$f,[ref]$t,[ref]$e); "
              "foreach ($x in $e) { [Console]::Out.WriteLine([IO.Path]::GetFileName($f) + '(' + $x.Extent.StartLineNumber + "
              "',' + $x.Extent.StartColumnNumber + '): ' + $x.Message) } }")
    try:
        r = subprocess.run([str(winps), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script,
                            *[str(f) for f in files]], capture_output=True, timeout=120, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [l.strip() for l in r.stdout.decode("utf-8", "replace").splitlines() if l.strip()]


def _copy_library(csproj: Path, dest_root: Path, log) -> Path:
    """Copy a referenced library project (sources only, no bin / obj) into the work folder; returns the copy's csproj."""
    dest = dest_root / csproj.parent.name
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(csproj.parent, dest, ignore=shutil.ignore_patterns("bin", "obj", "*.user", ".vs"))
    return dest / csproj.name


def _library_sources(csproj: Path) -> list[Path]:
    return sorted(p for p in csproj.parent.rglob("*.cs")
                  if not ({"bin", "obj"} & {x.lower() for x in p.relative_to(csproj.parent).parts}))


def library_dll(csproj: Path, name: str, log=print) -> Path | None:
    """The .NET Framework 4.8 build of a control library (for the netfx exe): its sources compiled with Roslyn csc
    against the Framework assemblies of Windows - no SDK, no NuGet - cached by a hash of the sources in
    %LOCALAPPDATA%/RADIDE/cache/dotnet/<name>/<hash>/<name>.dll. None when it cannot be built."""
    import hashlib
    fw = framework_dir()
    srcs = _library_sources(csproj)
    if fw is None or not srcs:
        return None
    h = hashlib.sha256()
    for p in srcs:
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    key = h.hexdigest()[:16]
    out = _local() / "cache" / "dotnet" / name / key / f"{name}.dll"
    if out.is_file():
        return out
    csc = roslyn(log)
    if not csc:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "tmp" / out.name          # same file name: it is the assembly name
    tmp.parent.mkdir(exist_ok=True)
    rsp = out.parent / "csc.rsp"
    args = ["/nologo", "/noconfig", "/nostdlib+", "/target:library", "/optimize+", "/debug-", "/langversion:latest",
            "/filealign:512", "/platform:anycpu", "/utf8output", "/deterministic+", "/nowarn:CS1591,CS0649,CS0169,CS0414",
            f"/out:{tmp}"]
    args += [f"/r:{fw / r}" for r in FRAMEWORK_REFS if (fw / r).is_file()]
    args += [str(p) for p in srcs]
    rsp.write_text("\n".join(_rsp_arg(a) for a in args), encoding="utf-8")
    log(f"Building {name} for the .NET Framework 4.8 (cached) ...")
    code, text = _run(csc + [f"@{rsp}"], out.parent, log, env=_quiet_env())
    if code != 0 or not tmp.is_file():
        log(f"{name}: the .NET Framework build failed:\n  " + "\n  ".join(_errors(text, csproj.parent)))
        return None
    tmp.replace(out)
    rsp.unlink(missing_ok=True)
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return out


def build(folder, project: Project, cfg, work, log, variant: str = "auto", trim: bool = False):
    """Build the exe. variant "auto" = PublishConfig.dotnet_target: "standalone" (self-contained single file, nothing
    to install), "framework" (small apphost, needs the .NET Desktop Runtime) or "netfx" (tiny exe for the .NET
    Framework 4.8 of Windows); each falls back to the others when it cannot be built. ("net48"/"sdk" = netfx/framework.)"""
    from ..build import BuildResult, make_icon
    folder, work = Path(folder).resolve(), Path(work)
    lang = _lang(project)
    reasons = check(folder, project, cfg)
    if reasons:
        raise NativeUnsupported(reasons)
    forms = load_forms(folder, project, lang)
    from ...languages import get_plugin
    plugin = get_plugin(lang)
    handlers = sorted(set(plugin.handlers_in_project(folder, project)))
    root = fresh_dir(work / "native-dotnet")
    src = fresh_dir(root / "src")
    gen = fresh_dir(root / "gen")
    icon = make_icon(folder, cfg, gen, log)
    exe_base = cfg.exe_base()
    shutil.copy2(HERE / "RadWinForms.cs", src / "RadWinForms.cs")
    _write(src / "RadForms.g.cs", forms_code(forms, set(handlers), control_map(folder)))
    _write(src / "AssemblyInfo.g.cs", assembly_info(cfg, project))
    _write(src / "GlobalUsings.g.cs", "\n".join(f"global using {u};" for u in GLOBAL_USINGS) + "\nglobal using static Rad;\n")
    resources: list[tuple[Path, str]] = []
    extra_refs: list[str] = []
    notes: list[str] = []
    if lang == "csharp-bridge":
        for p in sorted(folder.glob("*.cs")):
            if not p.name.lower().endswith("_designer.cs"):
                shutil.copy2(p, src / p.name)
        _designers(folder, project, lang, src, forms)
        _write(src / "RadProgram.g.cs", program_cs(project, cfg, forms, None, handlers))
        packages = _packages(folder)
    else:
        from ...languages.powershell_bridge import CLIENT_DIR, project_files
        names = project_files(folder)
        ps_dir = fresh_dir(root / "ps")
        _designers(folder, project, lang, ps_dir, forms)
        scripts: list[Path] = [CLIENT_DIR / "Rad.ps1", HERE / "RadPsShim.ps1"]
        for n in names:
            p = ps_dir / n if n.lower().endswith("_designer.ps1") else folder / n
            if p.is_file():
                scripts.append(p)
        errs = _ps_parse_errors([s for s in scripts[2:] if s.parent != ps_dir])
        if errs:
            raise NativeUnsupported(["Windows PowerShell 5.1 cannot parse the scripts (PowerShell 7 syntax?): "
                                     + "; ".join(errs[:5])])
        res_names = []
        for i, s in enumerate(scripts):
            name = f"rad.{i:02d}.{s.name}"
            dst = ps_dir / name
            dst.write_text("\ufeff" + s.read_text(encoding="utf-8-sig", errors="replace"), encoding="utf-8")
            resources.append((dst, name))
            res_names.append(name)
        shutil.copy2(HERE / "RadPsHost.cs", src / "RadPsHost.cs")
        _write(src / "RadProgram.g.cs", program_cs(project, cfg, forms, res_names, handlers))
        extra_refs.append(sma_dll())
        packages = []
    cs_files = sorted(src.glob("*.cs"))
    cmap = control_map(folder)
    refs = {k: dict(v) for k, v in cmap["__references__"].items()
            if any((cmap.get(c.type) or {}).get("reference") == k for f in forms for c in f.controls)}
    embedded: list[tuple[Path, str]] = []
    for name, r in refs.items():
        if r.get("project") and Path(r["project"]).is_file():
            # the SDK builds reference a copy (no bin / obj inside the IDE folder, which may be read-only)
            r["project"] = str(_copy_library(Path(r["project"]), root / "lib", log))
        if not (r.get("dll") and Path(r["dll"]).is_file()) and r.get("project") and lang == "csharp-bridge":
            dll = library_dll(Path(r["project"]), name, log)        # netfx: csc into a cached net48 dll
            if dll is not None:
                r["dll"] = str(dll)
        if r.get("dll") and Path(r["dll"]).is_file():
            extra_refs.append(r["dll"])
            embedded.append((Path(r["dll"]), f"radlib.{Path(r['dll']).stem}.dll"))
    target = {"net48": "netfx", "sdk": "framework"}.get(variant, variant)
    if target == "auto":
        target = str(getattr(cfg, "dotnet_target", "standalone") or "standalone").lower()
    if target not in TARGETS:
        target = "standalone"
    if lang == "powershell-bridge":
        order = ["netfx"]           # Windows PowerShell 5.1 is part of Windows: the netfx exe needs nothing else
    else:
        order = [target] + [t for t in ("netfx", "framework", "standalone") if t != target]
        if variant in ("net48", "sdk", "netfx", "framework", "standalone"):
            order = [target]
    if any(not (Path(r.get("dll") or "").is_file()) for r in refs.values()) or packages:
        order = [t for t in order if t != "netfx"] or order
    dist = fresh_dir(work / "dist" / exe_base)
    built, why = None, []
    for t in order:
        if built is not None:
            break
        if t == "netfx":
            if packages:
                why.append("netfx: NuGet packages need the .NET SDK build")
                continue
            out_dir = fresh_dir(root / "net48")
            ok, text = _compile_net48(cs_files, out_dir / f"{exe_base}.exe", icon, log, extra_refs, resources + embedded)
            if ok:
                built = ("net48", out_dir)
                if embedded:
                    log("Control libraries embedded in the exe: " + ", ".join(p.name for p, _ in embedded))
                log(f"Built for the .NET Framework 4.8 of Windows: {exe_base}.exe "
                    f"{size_text((out_dir / f'{exe_base}.exe').stat().st_size)}")
                notes.append("Runs on the .NET Framework 4.8 that is part of Windows 10/11 (nothing to install).")
            else:
                why.append("netfx: " + " | ".join(_errors(text, src)))
                log("The .NET Framework build failed:\n  " + "\n  ".join(_errors(text, src)))
        else:
            standalone = t == "standalone"
            ok, text, out = _compile_sdk(cs_files, root, exe_base, icon, packages, log, standalone, trim, refs)
            if ok and out is not None:
                built = ("standalone" if standalone else "sdk", out)
                log(f"Built with the .NET SDK ({'self-contained single file' if standalone else 'framework-dependent'}): "
                    f"{exe_base}.exe {size_text((out / f'{exe_base}.exe').stat().st_size)}")
                notes.append("One self-contained exe: nothing to install on the user's PC." if standalone else
                             "Needs the .NET Desktop Runtime 8 (https://dotnet.microsoft.com/download/dotnet/8.0) on the user's PC.")
            else:
                why.append(f"{t}: " + " | ".join(_errors(text, src)))
    if built is None:
        raise NativeUnsupported(why or ["no .NET build was possible"])
    kind, out = built
    for f in out.iterdir():
        if f.suffix.lower() in (".exe", ".dll", ".json", ".config") and not f.name.endswith(".deps.json"):
            shutil.copy2(f, dist / f.name)
    data = copy_data(folder, dist, (".cs", ".ps1", ".csproj", ".sln"), out_dir=work.parent)
    if data:
        log("Data files: " + ", ".join(data))
    exe = dist / f"{exe_base}.exe"
    log(f"Native exe: {exe} ({size_text(exe.stat().st_size)}, program folder {size_text(dir_size(dist))}, no Python)")
    return BuildResult(dist, exe.name, f"native-{kind}", notes, python_based=False)


__all__ = ["LANGS", "NAME", "TARGETS", "build", "check", "control_map", "forms_code", "framework_dir", "library_dll", "roslyn",
           "sma_dll"]
