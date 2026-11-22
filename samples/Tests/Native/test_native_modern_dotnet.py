"""RadIDE.Controls (radide/runtimes/dotnet/RadIDE.Controls) in native .NET builds: the RAD Modern showcase
(samples/Modern/DotNetShowcase - ribbon, side bar, tabs, grid, gauges, toggles, toast, message box, docking, themes)
is published as one exe without Python, "standalone" (self-contained .NET 8) and "netfx" (.NET Framework 4.8 of
Windows, the library embedded in the exe), started and driven:

  * UI Automation: controls by AutomationId (= control Name), ribbon / side bar / tab / status bar items as accessible
    children (LegacyIAccessible DoDefaultAction - the same objects screen readers use)
  * window messages: BM_CLICK on Rm buttons / toggles / tiles, WM_SETTEXT on the inner edit of RmTextBox,
    WM_KEYDOWN on the slider, WM_GETTEXT on labels the handlers write
  * PrintWindow of the program's own window (never the screen) to check the theme colours

Also: the control map covers every Rm type of docs/plans/MODERN_CONTROLS.md, generated code (AddToPage, form Theme),
the cached net48 library build, and - when the designer packages radide/components/builtin/Rm*/ exist - that their
property / event names are the ones the map translates. Only processes the test started are touched.

    .venv\\Scripts\\python samples/Tests/Native/test_native_modern_dotnet.py      (RADIDE_TEST_SHOTS=<dir> keeps the PNGs)
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

import _win as W  # noqa: E402
from radide.deploy import build as B  # noqa: E402
from radide.deploy import config as C  # noqa: E402
from radide.deploy.native import dotnet_winforms as D  # noqa: E402
from radide.model import Form, Project  # noqa: E402

SHOWCASE = ROOT / "samples" / "Modern" / "DotNetShowcase"
TITLE = "RAD Modern Showcase"
RESULTS: list[tuple[str, bool]] = []
SIZES: dict[str, int] = {}
SPEC_TYPES = ["RmButton", "RmToggle", "RmTextBox", "RmComboBox", "RmCheckBox", "RmRadioButton", "RmProgress", "RmSlider",
              "RmGauge", "RmPanel", "RmGroupPanel", "RmTabStrip", "RmSideBar", "RmNavigationPane", "RmRibbon", "RmStatusBar",
              "RmGrid", "RmTreeView", "RmListView", "RmDatePicker", "RmTimePicker", "RmCalendar", "RmTile", "RmDockPanel",
              "RmDockWindow", "RmToast", "RmBalloonTip", "RmSuperTooltip", "RmMessageBox"]

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p,
                            wintypes.UINT]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
CHILDPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumChildWindows.argtypes = [wintypes.HWND, CHILDPROC, wintypes.LPARAM]
WM_KEYDOWN, WM_KEYUP, VK_RIGHT = 0x0100, 0x0101, 0x27
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:500]}]"), flush=True)
    return bool(cond)


# ---------------------------------------------------------------------- window helpers
class Shot:
    """PrintWindow of one window (the program's own) -> pixels; optionally saved as PNG."""

    def __init__(self, hwnd: int, path: Path | None = None):
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        self.w, self.h = r.right - r.left, r.bottom - r.top
        hdc = user32.GetDC(hwnd)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, self.w, self.h)
        gdi32.SelectObject(mdc, bmp)
        user32.PrintWindow(hwnd, mdc, 2)                      # PW_RENDERFULLCONTENT

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("a", wintypes.LONG), ("b", wintypes.LONG), ("c", wintypes.DWORD),
                        ("d", wintypes.DWORD)]
        bi = BIH(ctypes.sizeof(BIH), self.w, -self.h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = (ctypes.c_ubyte * (self.w * self.h * 4))()
        gdi32.GetDIBits(mdc, bmp, 0, self.h, buf, ctypes.byref(bi), 0)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(hwnd, hdc)
        self.px = bytes(buf)
        if path is not None:
            self.save(path)

    def rgb(self, x: int, y: int) -> tuple[int, int, int]:
        i = (y * self.w + x) * 4
        return self.px[i + 2], self.px[i + 1], self.px[i]

    def luma(self, x: int, y: int) -> float:
        r, g, b = self.rgb(x, y)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def save(self, path: Path) -> None:
        rows = []
        for y in range(self.h):
            row = bytearray(self.px[y * self.w * 4:(y + 1) * self.w * 4])
            row[0::4], row[2::4] = row[2::4], row[0::4]
            rows.append(b"\x00" + bytes(row))

        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(b"".join(rows), 6)) + chunk(b"IEND", b""))


def child_windows(hwnd: int, cls: str = "") -> list[int]:
    out = []

    def cb(h, _):
        if cls:
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(h, buf, 64)
            if cls.lower() not in buf.value.lower():
                return True
        out.append(h)
        return True
    user32.EnumChildWindows(hwnd, CHILDPROC(cb), 0)
    return out


def client_point(hwnd: int, x: int, y: int) -> int:
    return (y << 16) | (x & 0xFFFF)


def window_size(hwnd: int) -> tuple[int, int]:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.right - r.left, r.bottom - r.top


class Driver:
    def __init__(self, uia, main: int, pid: int):
        self.uia, self.U, self.main, self.pid = uia, uia.U, main, pid
        self.root = uia.root(main)

    def el(self, automation_id: str):
        return self.uia.find(self.root, automation_id)

    def hwnd(self, automation_id: str) -> int:
        return self.uia.hwnd(self.root, automation_id)

    def item(self, control_id: str, name: str):
        """An accessible item (ribbon / side bar / tab / status bar) by name, inside one control."""
        parent = self.el(control_id)
        return self.uia.find(parent, name=name) if parent else None

    def invoke(self, control_id: str, name: str) -> bool:
        # (a loaded machine: the accessible item can be rebuilt between finding it and invoking it -
        # UIA_E_ELEMENTNOTAVAILABLE - so find it again and retry for a while)
        def once():
            el = self.item(control_id, name)
            if not el:
                return False
            pat = el.GetCurrentPattern(self.U.UIA_LegacyIAccessiblePatternId)
            if not pat:
                return False
            pat.QueryInterface(self.U.IUIAutomationLegacyIAccessiblePattern).DoDefaultAction()
            return True
        return bool(W.wait(once, 10))


# ---------------------------------------------------------------------- build
def copy_project(tmp: Path) -> Path:
    dst = tmp / SHOWCASE.name
    shutil.copytree(SHOWCASE, dst, ignore=shutil.ignore_patterns("Publish", "_build", "__pycache__"))
    return dst


def exe_files(dist: Path) -> list[str]:
    return sorted(f.name for f in dist.iterdir())


def no_python(dist: Path) -> list[str]:
    return [str(f.relative_to(dist)) for f in dist.rglob("*")
            if (f.name.lower().startswith("python") and f.name.lower().endswith(".dll")) or f.suffix.lower() in (".pyd", ".pyc")]


def test_map_and_codegen(tmp: Path) -> None:
    cmap = D.control_map()
    missing = [t for t in SPEC_TYPES if t not in cmap]
    check(f"control map: all {len(SPEC_TYPES)} Rm types of the spec are mapped to RadIDE.Controls", not missing, missing)
    check("control map: every Rm type references the RadIDE.Controls library",
          all(cmap[t].get("reference") == "RadIDE.Controls" and cmap[t]["type"] == "RadIDE.Controls." + t for t in SPEC_TYPES if t in cmap))
    ref = cmap["__references__"].get("RadIDE.Controls") or {}
    check("control map: the library reference is the project in radide/runtimes/dotnet (exists)",
          Path(ref.get("project", "")).is_file() and "runtimes" in ref.get("project", ""), ref)
    check("control map: containers with pages declare pageProp (RmTabStrip, RmNavigationPane)",
          cmap["RmTabStrip"].get("pageProp") == "TabPage" and cmap["RmNavigationPane"].get("pageProp") == "TabPage")
    check("control map: non-visual components (RmToast, RmMessageBox, RmSuperTooltip, RmBalloonTip)",
          all(cmap[t].get("nonvisual") for t in ("RmToast", "RmMessageBox", "RmSuperTooltip", "RmBalloonTip")))
    folder = copy_project(tmp / "gen")
    project = Project.load(folder)
    cfg = C.load(folder, folder.name)
    check("check(): the showcase is fully translatable (no reasons)", not D.check(folder, project, cfg), D.check(folder, project, cfg))
    form = Form.load(folder / "MainForm.form")
    code = D.forms_code([form], {"MainForm_Load", "RmRibbon1_ItemClick", "tglDark_CheckedChanged"}, cmap)
    check("codegen: Rm controls are created with their library type",
          "new global::RadIDE.Controls.RmRibbon()" in code and "new global::RadIDE.Controls.RmToast()" in code)
    check("codegen: JSON-valued properties are written as JSON text (ribbon Tabs)",
          'this.RmRibbon1.Tabs = "[{\\"Text\\": \\"Home\\"' in code, [l for l in code.splitlines() if ".Tabs =" in l][:1])
    check("codegen: enum / colour / date properties", "RadIDE.Controls.RmButtonKind.Accent" in code
          and "this.tileSales.TileColor = System.Drawing.Color.FromArgb(43, 87, 154);" in code and "this.dtpDate.Value = d;" in code)
    check("codegen: page children go through AddToPage(page, control)", "this.RmTabStrip1.AddToPage(1, this.gridProducts);" in code
          and "this.navProps.AddToPage(1, this.lblColors);" in code)
    check("codegen: the form Theme reaches RmThemeManager (formInit)",
          'global::RadIDE.Controls.RmThemeManager.ApplyFormTheme(this, "Light");' in code)
    check("codegen: item events are wired (RmRibbon1 ItemClick)", 'this.Wire(this.RmRibbon1, "RmRibbon1", "ItemClick");' in code)
    t = time.time()
    dll = D.library_dll(Path(ref["project"]), "RadIDE.Controls", log=lambda *_: None)
    check("library_dll: the net48 build of RadIDE.Controls exists (csc, cached)", dll is not None and dll.is_file(), dll)
    t2 = time.time()
    dll2 = D.library_dll(Path(ref["project"]), "RadIDE.Controls", log=lambda *_: None)
    check(f"library_dll: second call is the cache ({time.time() - t2:.2f}s, first {t2 - t:.1f}s)", dll2 == dll and time.time() - t2 < 2)


def test_packages_match() -> None:
    """When the designer packages exist, their props / events must be the ones the .NET map knows."""
    cmap = D.control_map()
    from radide.controls import COMMON_PROPS
    common = {p.name for p in COMMON_PROPS} | {"Parent", "TabPage", "Style", "AccentColor"}
    pkgs = sorted((ROOT / "radide" / "components" / "builtin").glob("Rm*/component.json"))
    if not pkgs:
        print("NOTE designer packages radide/components/builtin/Rm*/ not there yet - name cross-check skipped")
        return
    bad = []
    for p in pkgs:
        data = json.loads(p.read_text(encoding="utf-8"))
        name = data.get("name") or p.parent.name
        entry = cmap.get(name)
        if entry is None:
            bad.append(f"{name}: not mapped")
            continue
        props = set(entry.get("props") or {})
        for pr in data.get("properties") or []:
            n = pr.get("name") if isinstance(pr, dict) else str(pr)
            if n and n not in props and n not in common and n != "Text":
                bad.append(f"{name}.{n} (property)")
        events = set(entry.get("events") or [])
        for ev in data.get("events") or []:
            n = ev.get("name") if isinstance(ev, dict) else str(ev)
            if n and n not in events and n not in ("Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseEnter",
                                                    "MouseLeave", "KeyDown", "KeyUp", "KeyPress", "GotFocus", "LostFocus",
                                                    "TextChanged", "Resize", "MouseWheel"):
                bad.append(f"{name}.{n} (event)")
    check(f"designer packages ({len(pkgs)}): every property / event name is translated by the .NET map", not bad, bad)
    import re
    src = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "radide" / "runtimes" / "dotnet" / "RadIDE.Controls" / "src").glob("*.cs"))
    have = {n.lower() for n in re.findall(r"public\s+(?:new\s+|override\s+|virtual\s+|static\s+)*[\w<>\[\],? ]+?\s+(\w+)\s*\(", src)}
    missing = []
    for p in pkgs:
        data = json.loads(p.read_text(encoding="utf-8"))
        for m in data.get("methods") or []:
            n = m.get("name") if isinstance(m, dict) else str(m)
            if n and n.lower() not in have:
                missing.append(f"{data.get('name')}.{n}")
    check("designer packages: every method has a public method of that name in RadIDE.Controls (Call by name)", not missing, missing)


def build_variant(tmp: Path, variant: str):
    folder = copy_project(tmp / variant)
    cfg = C.load(folder, folder.name)
    lines: list[str] = []
    t = time.time()
    if variant == "standalone":
        res = B.build(folder, cfg, log=lines.append)          # the IDE path: kind auto -> native, publish.json target
    else:
        res = D.build(folder, Project.load(folder), cfg, tmp / f"work_{variant}", lines.append, variant=variant)
    exe = res.dist / res.exe
    kind = {"standalone": "native-standalone", "netfx": "native-net48", "framework": "native-sdk"}[variant]
    check(f"{variant}: builds ({res.kind}, {time.time() - t:.0f}s)", res.kind == kind and exe.is_file(), lines[-8:])
    SIZES[variant] = exe.stat().st_size
    check(f"{variant}: one exe (+ readme.txt), the library inside it, no Python",
          exe_files(res.dist) == sorted([res.exe, "readme.txt"]) and not no_python(res.dist), exe_files(res.dist))
    if variant == "netfx":
        data = exe.read_bytes()
        check("netfx: RadIDE.Controls is an embedded resource of the exe (radlib.RadIDE.Controls.dll)",
              b"radlib.RadIDE.Controls.dll" in data and any("embedded" in l for l in lines), lines[-6:])
        check(f"netfx: exe size {SIZES[variant] / 1024:.0f} KB (< 1 MB)", SIZES[variant] < 1024 * 1024, SIZES[variant])
    if variant == "standalone":
        check(f"standalone: exe size {SIZES[variant] / 1048576:.1f} MB (< 90 MB, self-contained)", SIZES[variant] < 90 * 1048576)
    return exe


# the VB.NET test project (a curated sample): net8.0-windows WinForms with RmRibbon / RmToggle / RmGauge and Handles
VB_SAMPLE = Path(__file__).resolve().parent / "VBNet" / "RmVb"
VBPROJ = (VB_SAMPLE / "RmVb.vbproj").read_text(encoding="utf-8")
VBCODE = (VB_SAMPLE / "Form1.vb").read_text(encoding="utf-8")


VB_DESIGNER = """<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _
Partial Class Form1
    Inherits System.Windows.Forms.Form

    Private components As System.ComponentModel.IContainer

    <System.Diagnostics.DebuggerStepThrough()> _
    Private Sub InitializeComponent()
        Me.RmButton1 = New RadIDE.Controls.RmButton()
        Me.SuspendLayout()
        '
        'RmButton1
        '
        Me.RmButton1.Kind = RadIDE.Controls.RmButtonKind.Accent
        Me.RmButton1.Location = New System.Drawing.Point(12, 12)
        Me.RmButton1.Name = "RmButton1"
        Me.RmButton1.Size = New System.Drawing.Size(120, 32)
        Me.RmButton1.TabIndex = 0
        Me.RmButton1.Text = "Save"
        Me.RmButton1.Image = "icon:save"
        '
        'Form1
        '
        Me.ClientSize = New System.Drawing.Size(400, 300)
        Me.Controls.Add(Me.RmButton1)
        Me.Name = "Form1"
        Me.Text = "Form1"
        Me.ResumeLayout(False)

    End Sub

    Friend WithEvents RmButton1 As RadIDE.Controls.RmButton
End Class
"""


def test_vs_designer(tmp: Path) -> None:
    """A Visual Studio VB.NET form with RadIDE.Controls opened in place: read, edit, add, save (winforms_vb + winforms_rm)."""
    if not list((ROOT / "radide" / "components" / "builtin").glob("RmButton/component.json")):
        print("NOTE designer packages not installed - VS designer round trip skipped")
        return
    from radide.components import REGISTRY
    REGISTRY.ensure_loaded()
    from radide.foreign import winforms_vb  # noqa: F401  (registers the VB dialect)
    folder = tmp / "VsVb"
    folder.mkdir(parents=True)
    (folder / "App.vbproj").write_text(VBPROJ.replace("<StartupObject>RmVb.Program</StartupObject>", ""), encoding="utf-8")
    (folder / "Form1.vb").write_text("Public Class Form1\nEnd Class\n", encoding="utf-8")
    (folder / "Form1.Designer.vb").write_text(VB_DESIGNER, encoding="utf-8")
    form = Form.load(folder / "Form1.Designer.vb")
    b = next((c for c in form.controls if c.name == "RmButton1"), None)
    check("VS designer: New RadIDE.Controls.RmButton() is read as the RmButton control with its properties",
          b is not None and b.type == "RmButton" and b.props.get("Kind") == "Accent" and b.props.get("Image") == "icon:save",
          b and (b.type, b.props.get("Kind"), b.props.get("Image")))
    if b is None:
        return
    b.props["Kind"] = "Outline"
    g = form.add("RmGauge", 150, 60)
    g.props.update({"Value": 72, "Unit": "%", "Kind": "Linear"})
    form.add("RmToast", 0, 0)
    form.save(folder / "Form1.Designer.vb")
    text = (folder / "Form1.Designer.vb").read_text(encoding="utf-8")
    check("VS designer: a changed property is written (Kind = RadIDE.Controls.RmButtonKind.Outline)",
          "Me.RmButton1.Kind = RadIDE.Controls.RmButtonKind.Outline" in text, text[:600])
    check("VS designer: a new Rm control is written with its mapped properties (RmGauge1 Kind / Unit / Value)",
          "Me.RmGauge1 = New RadIDE.Controls.RmGauge()" in text and "Me.RmGauge1.Kind = RadIDE.Controls.RmGaugeKind.Linear" in text
          and 'Me.RmGauge1.Unit = "%"' in text and "Me.RmGauge1.Value = 72" in text and "Me.Controls.Add(Me.RmGauge1)" in text)
    check("VS designer: a non-visual Rm component has no Name / Controls.Add",
          "Me.RmToast1 = New RadIDE.Controls.RmToast()" in text and "Me.RmToast1.Name" not in text and "Controls.Add(Me.RmToast1)" not in text)
    proj = (folder / "App.vbproj").read_text(encoding="utf-8")
    check("VS designer: saving adds lib\\RadIDE.Controls.dll + the Reference to the .vbproj",
          (folder / "lib" / "RadIDE.Controls.dll").is_file() and '<Reference Include="RadIDE.Controls">' in proj, proj)
    back = Form.load(folder / "Form1.Designer.vb")
    g2 = next((c for c in back.controls if c.name == "RmGauge1"), None)
    check("VS designer: the saved form reads back (RmGauge1 Value 72, Kind Linear)",
          g2 is not None and g2.type == "RmGauge" and g2.props.get("Value") == 72 and g2.props.get("Kind") == "Linear",
          g2 and (g2.type, g2.props.get("Value"), g2.props.get("Kind")))


def test_vbnet(tmp: Path) -> None:
    """VB.NET: a Visual Studio-style project gets lib\\RadIDE.Controls.dll + <Reference> (winforms_rm.ensure_reference,
    what the WinForms designer does when an Rm control is put on a form), builds with dotnet, runs and reacts."""
    from radide.foreign import winforms_cs, winforms_rm as R
    check("VB/C# WinForms projects: the toolbox profile offers the Rm controls (RadIDE.Controls.*)",
          "RmRibbon" in winforms_cs.WinFormsCSPlugin.designer_profile["allowed"]
          and winforms_cs.WinFormsCSPlugin.designer_profile["labels"]["RmGrid"] == "RadIDE.Controls.RmGrid")
    check("VB/C#: item events get the EventHandler(Of RmItemEventArgs) signature",
          winforms_cs.handler_signature("ItemClick") == "RadIDE.Controls.RmItemEventArgs"
          and winforms_cs.handler_signature("Click") == "EventArgs")
    check("VB/C#: target frameworks (net48 / net8.0-windows / unsupported)",
          R.target_of("<TargetFramework>net48</TargetFramework>") == "net48"
          and R.target_of("<TargetFramework>net9.0-windows</TargetFramework>") == "net8.0-windows"
          and R.target_of("<TargetFrameworkVersion>v4.7.2</TargetFrameworkVersion>") == "net48"
          and R.target_of("<TargetFramework>net6.0-windows</TargetFramework>") == "")
    if not D._sdk_dirs():
        print("NOTE no .NET SDK: VB.NET build skipped")
        return
    folder = tmp / "RmVb"
    folder.mkdir(parents=True)
    (folder / "RmVb.vbproj").write_text(VBPROJ, encoding="utf-8")
    (folder / "Form1.vb").write_text(VBCODE, encoding="utf-8")
    (folder / "Form1.Designer.vb").write_text("' designer (the code is in Form1.vb for this test)\n", encoding="utf-8")
    line = R.ensure_reference(folder / "Form1.Designer.vb", log=lambda *_: None)
    text = (folder / "RmVb.vbproj").read_text(encoding="utf-8")
    check("VB.NET: ensure_reference adds lib\\RadIDE.Controls.dll (net8.0-windows) + <Reference HintPath>",
          (folder / "lib" / "RadIDE.Controls.dll").is_file() and "<HintPath>lib\\RadIDE.Controls.dll</HintPath>" in text, line)
    check("VB.NET: a second call changes nothing", R.ensure_reference(folder / "Form1.Designer.vb") is None
          and (folder / "RmVb.vbproj").read_text(encoding="utf-8") == text)
    r = subprocess.run([D.dotnet(), "build", str(folder / "RmVb.vbproj"), "-c", "Release", "-nologo", "-v", "q", "-o", str(folder / "out")],
                       capture_output=True, text=True, env=D._quiet_env(), timeout=600)
    exe = folder / "out" / "RmVb.exe"
    if not check("VB.NET: the project builds with the library (dotnet build)", r.returncode == 0 and exe.is_file(),
                 (r.stdout + r.stderr)[-800:]):
        return
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        main = W.wait(lambda: next((x for x in W.top_windows(p.pid) if W.text(x) == "RmVb"), 0), 30)
        if not check("VB.NET: the program starts", main):
            return
        uia = W.UIA()
        d = Driver(uia, main, p.pid)
        tgl, lbl = W.wait(lambda: d.hwnd("RmToggle1"), 5), W.wait(lambda: d.hwnd("lblOut"), 5)
        W.click(tgl)
        check("VB.NET: RmToggle CheckedChanged (Handles clause) -> handler", W.wait(lambda: W.text(lbl) == "Toggle: True", 5), W.text(lbl))
        d.invoke("RmRibbon1", "Run")
        check("VB.NET: RmRibbon ItemClick (RmItemEventArgs.ItemName)", W.wait(lambda: W.text(lbl) == "Ribbon: btnRun", 5), W.text(lbl))
        W.close(main)
        W.wait(lambda: p.poll() is not None, 10)
    finally:
        if p.poll() is None:
            p.kill()


# ---------------------------------------------------------------------- run + drive
def drive(exe: Path, tag: str, shots: Path) -> None:
    uia = W.UIA()
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        main = W.wait(lambda: next((h for h in W.top_windows(p.pid) if W.text(h) == TITLE), 0), 40)
        if not check(f"{tag}: main window '{TITLE}' appears", main, W.top_windows(p.pid)):
            return
        d = Driver(uia, main, p.pid)
        h = {n: W.wait(lambda n=n: d.hwnd(n), 5) or 0 for n in ("RmRibbon1", "RmSideBar1", "RmTabStrip1", "RmStatusBar1")}
        check(f"{tag}: MainForm_Load ran (status bar panel 'Loaded')", W.wait(lambda: d.item("RmStatusBar1", "Loaded"), 8))
        time.sleep(0.8)
        s = Shot(main, shots / f"{tag}_1_dashboard.png")
        bw, bh = s.w, s.h
        # a gauge / tile really painted (owner-drawn, not blank): the Sales tile is blue
        tx, ty = 250, 230
        check(f"{tag}: owner-drawn tiles are painted (Sales tile is blue)", s.rgb(tx, ty)[2] > 120 and s.rgb(tx, ty)[0] < 90,
              s.rgb(tx, ty))
        # the controls of each page (hidden pages are not in the UI Automation tree): visit them with the side bar
        pages = {"Dashboard": ("sldCpu", "lblDash", "tileMail", "gaugeCpu"),
                 "Products": ("btnAddRow", "btnGroup", "lblRows", "gridProducts"),
                 "Controls": ("lblLog", "lblTheme", "tglDark", "btnToast", "btnAsk", "btnExport", "txtName"),
                 "Docking": ("dockMain", "dwExplorer")}
        for item, names in pages.items():
            d.invoke("RmSideBar1", item)
            for n in names:
                h[n] = W.wait(lambda n=n: d.hwnd(n), 5) or 0
        check(f"{tag}: every control found by AutomationId (pages visited with the side bar)", all(h.values()),
              [k for k, v in h.items() if not v])
        if not all(h.values()):
            return
        log = lambda: W.text(h["lblLog"])                                     # noqa: E731
        # tabs through accessibility
        check(f"{tag}: tab 'Controls' invoked through UI Automation", d.invoke("RmTabStrip1", "Controls"))
        check(f"{tag}: SelectedIndexChanged -> status bar panel 'Page: Controls'",
              W.wait(lambda: d.item("RmStatusBar1", "Page: Controls"), 5))
        # buttons, toast
        W.click(h["btnToast"])
        check(f"{tag}: RmButton Click (BM_CLICK) -> handler (lblLog = Toast shown)", W.wait(lambda: log() == "Toast shown", 5), log())
        toast = W.wait(lambda: next((x for x in W.top_windows(p.pid) if W.text(x) == "Saved"), 0), 5)
        check(f"{tag}: RmToast.Show -> a toast window 'Saved' appears", toast)
        if toast:
            check(f"{tag}: the toast closes by itself (Duration 4000 ms)",
                  W.wait(lambda: not any(W.text(x) == "Saved" for x in W.top_windows(p.pid)), 12))
        # text box: the inner edit of RmTextBox
        edits = child_windows(h["txtName"], "edit")
        check(f"{tag}: RmTextBox hosts a real edit control", edits, edits)
        if edits:
            W.set_text(edits[0], "Ali")
            check(f"{tag}: RmTextBox TextChanged -> lblLog = Hello, Ali", W.wait(lambda: log() == "Hello, Ali", 5), log())
        # toggle -> Dark theme, checked by pixels of the program's own window
        W.click(h["tglDark"])
        check(f"{tag}: RmToggle CheckedChanged -> Me.Theme = Dark (lblTheme)", W.wait(lambda: W.text(h["lblTheme"]) == "Theme: Dark", 5),
              W.text(h["lblTheme"]))
        time.sleep(0.8)
        s = Shot(main, shots / f"{tag}_2_dark.png")
        sx, sy = 100, s.h - 200                                    # inside the side bar
        check(f"{tag}: Dark theme painted (side bar luma {s.luma(sx, sy):.2f} < 0.3)", s.luma(sx, sy) < 0.3, s.rgb(sx, sy))
        W.click(h["tglDark"])
        check(f"{tag}: toggle back -> Light", W.wait(lambda: W.text(h["lblTheme"]) == "Theme: Light", 5))
        time.sleep(0.6)
        s = Shot(main)
        check(f"{tag}: Light theme painted again (side bar luma {s.luma(sx, sy):.2f} > 0.7)", s.luma(sx, sy) > 0.7, s.rgb(sx, sy))
        # ribbon items through accessibility
        check(f"{tag}: ribbon item 'Office' invoked", d.invoke("RmRibbon1", "Office"))
        check(f"{tag}: RmRibbon ItemClick (ItemName thOffice) -> Theme: Office", W.wait(lambda: W.text(h["lblTheme"]) == "Theme: Office", 5),
              W.text(h["lblTheme"]))
        time.sleep(0.6)
        s = Shot(main, shots / f"{tag}_3_office.png")
        r, g, b = s.rgb(s.w // 2, s.h - 12)                       # status bar = Office accent blue
        check(f"{tag}: Office theme painted (blue status bar {r},{g},{b})", b > 120 and r < 80, (r, g, b))
        d.invoke("RmRibbon1", "Light")
        check(f"{tag}: ribbon 'Light' -> Theme: Light", W.wait(lambda: W.text(h["lblTheme"]) == "Theme: Light", 5))
        # split button drop-down: mouse on the arrow part, then the menu item (UI Automation, process-wide)
        bw2, bh2 = window_size(h["btnExport"])
        W.user32.PostMessageW(h["btnExport"], WM_LBUTTONDOWN, 1, client_point(h["btnExport"], bw2 - 8, bh2 // 2))
        W.user32.PostMessageW(h["btnExport"], WM_LBUTTONUP, 0, client_point(h["btnExport"], bw2 - 8, bh2 // 2))
        excel = W.wait(lambda: uia.find(uia.uia.GetRootElement(), name="Excel", pid=p.pid), 10)
        if not excel:                    # the press went nowhere (the program was busy): once more
            W.user32.PostMessageW(h["btnExport"], WM_LBUTTONDOWN, 1, client_point(h["btnExport"], bw2 - 8, bh2 // 2))
            W.user32.PostMessageW(h["btnExport"], WM_LBUTTONUP, 0, client_point(h["btnExport"], bw2 - 8, bh2 // 2))
            excel = W.wait(lambda: uia.find(uia.uia.GetRootElement(), name="Excel", pid=p.pid), 15)
        if excel:
            pat = excel.GetCurrentPattern(uia.U.UIA_InvokePatternId)
            if pat:
                pat.QueryInterface(uia.U.IUIAutomationInvokePattern).Invoke()
            else:
                excel.GetCurrentPattern(uia.U.UIA_LegacyIAccessiblePatternId).QueryInterface(
                    uia.U.IUIAutomationLegacyIAccessiblePattern).DoDefaultAction()
        check(f"{tag}: split button drop-down -> DropDownItemClicked (Export: Excel)", excel and W.wait(lambda: log() == "Export: Excel", 15),
              log())
        # message box (modal): answer Yes through its RmButton
        time.sleep(0.8)                             # the split button menu has closed
        # (a loaded machine: wait until the drop-down really is gone - a click while it is open only closes it)
        W.wait(lambda: not [x for x in W.top_windows(p.pid) if x != main and W.text(x) != "Saved"], 8)
        W.click(h["btnAsk"])
        box = W.wait(lambda: next((x for x in W.top_windows(p.pid) if W.text(x) == "RAD Modern"), 0), 25)
        if not box and log() == "Export: Excel":        # the click went nowhere (the program was busy): once more
            W.click(h["btnAsk"])
            box = W.wait(lambda: next((x for x in W.top_windows(p.pid) if W.text(x) == "RAD Modern"), 0), 25)
        check(f"{tag}: RmMessageBox.Show opens a themed dialog 'RAD Modern'", box)
        if box:
            # (no PrintWindow of the modal dialog: capturing it from another process sometimes leaves its buttons
            # without clicks on the .NET Framework - a test artefact, not seen with real input)
            yes = W.wait(lambda: uia.hwnd(uia.root(box), "btnYes"), 5)
            check(f"{tag}: the dialog has a 'Yes' RmButton", yes)
            if yes:
                time.sleep(0.5)                     # the dialog finishes showing (modal loop running)
                W.click(yes)
                if not W.wait(lambda: not user32.IsWindowVisible(box), 3):
                    el = uia.find(uia.root(box), "btnYes")       # the accessible default action of the RmButton
                    if el:
                        el.GetCurrentPattern(uia.U.UIA_LegacyIAccessiblePatternId).QueryInterface(
                            uia.U.IUIAutomationLegacyIAccessiblePattern).DoDefaultAction()
            check(f"{tag}: Show returns the answer (lblLog = Answer: Yes)", W.wait(lambda: log() == "Answer: Yes", 15), log())
            W.wait(lambda: not user32.IsWindow(box) or not user32.IsWindowVisible(box), 10)
        # grid
        W.click(h["btnAddRow"])
        check(f"{tag}: RmGrid.AddRow -> Count 7 (lblRows)", W.wait(lambda: W.text(h["lblRows"]) == "7 rows", 15), W.text(h["lblRows"]))
        W.wait(lambda: log() == "Row added", 10)          # the AddRow handler has finished
        W.click(h["btnGroup"])
        grouped = W.wait(lambda: log() == "Grouped by category", 15)
        if not grouped and log() == "Row added":         # the click went nowhere (the program was busy): once more
            W.click(h["btnGroup"])
            grouped = W.wait(lambda: log() == "Grouped by category", 15)
        check(f"{tag}: RmGrid GroupBy = Category", grouped, log())
        W.click(h["btnGroup"])
        # side bar -> tab change
        check(f"{tag}: side bar item 'Products' invoked", d.invoke("RmSideBar1", "Products"))
        check(f"{tag}: RmSideBar ItemClick (sbProducts) -> handler", W.wait(lambda: log() == "Side bar: sbProducts", 5), log())
        check(f"{tag}: ... and the tab strip shows the Data page (grid visible)", W.wait(lambda: user32.IsWindowVisible(h["gridProducts"]), 3))
        Shot(main, shots / f"{tag}_6_data.png")
        # slider -> gauge (keyboard)
        d.invoke("RmTabStrip1", "Dashboard")
        time.sleep(0.4)
        for _ in range(3):
            W.user32.PostMessageW(h["sldCpu"], WM_KEYDOWN, VK_RIGHT, 0)
            W.user32.PostMessageW(h["sldCpu"], WM_KEYUP, VK_RIGHT, 0)
        check(f"{tag}: RmSlider ValueChanged (arrow keys) -> gauge + label (CPU 45%)",
              W.wait(lambda: W.text(h["lblDash"]) == "CPU 45%", 5), W.text(h["lblDash"]))
        W.click(h["tileMail"])
        check(f"{tag}: RmTile Click -> handler", W.wait(lambda: log() == "Tile: Mail (read)", 5), log())
        # docking page
        d.invoke("RmTabStrip1", "Docking")
        check(f"{tag}: RmDockPanel shows its tool windows (Explorer visible)", W.wait(lambda: user32.IsWindowVisible(h["dwExplorer"]), 5))
        time.sleep(0.6)
        Shot(main, shots / f"{tag}_7_docking.png")
        check(f"{tag}: window size kept ({bw}x{bh})", (bw, bh) == window_size(main))
        # right to left last: WinForms gives the controls new window handles when RightToLeft changes
        check(f"{tag}: ribbon check item 'Right to left' invoked", d.invoke("RmRibbon1", "Right to left"))
        time.sleep(1.0)
        # (the window handles are recreated: on a loaded machine that takes a while - retry until UI Automation
        # answers for the new window)
        def new_driver():
            m = next((x for x in W.top_windows(p.pid) if W.text(x) == TITLE), 0)
            return Driver(uia, m, p.pid) if m else None
        d = W.wait(new_driver, 20) or d
        main = d.main if hasattr(d, "main") else main
        W.wait(lambda: d.invoke("RmTabStrip1", "Controls"), 15)
        lbl = W.wait(lambda: d.hwnd("lblLog"), 15)
        check(f"{tag}: ... -> Me.RightToLeft = True (lblLog)", lbl and W.wait(lambda: W.text(lbl) == "Right to left: True", 15),
              W.text(lbl) if lbl else "")
        time.sleep(0.6)
        s = Shot(main, shots / f"{tag}_8_rtl.png")
        r, g, b = s.rgb(s.w - 100, s.h // 2)                   # the side bar moved to the right edge
        check(f"{tag}: RTL mirrors the layout (side bar now on the right: {r},{g},{b})", (r + g + b) / 3 > 200 and abs(r - b) < 20, (r, g, b))
        W.close(main)
        check(f"{tag}: closing the main window ends the program", W.wait(lambda: p.poll() is not None, 10))
    finally:
        if p.poll() is None:
            p.kill()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="radnative_modern_"))
    keep = os.environ.get("RADIDE_TEST_SHOTS")
    shots = Path(keep) if keep else tmp / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    try:
        test_map_and_codegen(tmp)
        test_packages_match()
        test_vbnet(tmp)
        test_vs_designer(tmp)
        if not D._sdk_dirs():
            print("NOTE no .NET SDK: only the netfx variant is built")
        else:
            exe = build_variant(tmp, "standalone")
            drive(exe, "standalone", shots)
        exe = build_variant(tmp, "netfx")
        drive(exe, "netfx", shots)
        if D._sdk_dirs():
            build_variant(tmp, "framework")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nSizes:")
    for k, v in SIZES.items():
        print(f"  {k}: {v / 1024:.1f} KB")
    if keep:
        print(f"Screenshots: {shots}")
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
