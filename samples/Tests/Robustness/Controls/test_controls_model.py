"""Non-default controls (no GUI): component packages, the 29 RAD Modern (Rm*) packages, user controls,
ActiveX/OCX placeholders - and what happens when they are missing, broken, duplicated or of another version.

* registry: built-in packages valid, the 29 Rm* packages registered with Toolbox categories;
* Rm*: every property of every Rm control set to a non-default value of its kind (enum, bool, int, float,
  colour, str, multiline, list ...) survives save + reload; the form generates compilable python-tk /
  python-qt code and code for VB, C#, JavaScript, Ring, Java ...; a python-tk program with every Rm control
  runs (F5 equivalent, window withdrawn);
* an installed package (.radcomp, user scope) and a project package (.radide/components): Toolbox category,
  code generation, runtime copied into the project, the generated python-tk / python-qt programs run;
* package missing when a form is opened: a placeholder, the control's saved data byte-identical after
  editing other controls and saving, every language generates a placeholder instead of crashing; the
  package installed again -> the real control with its saved values;
* package uninstalled while a form using it is open (removed from the Toolbox): placeholder, data kept;
* broken packages (invalid JSON, no name, bad property type, designer.py raising on import, missing runtime
  file): reported in Registry.broken / pkg.errors, never an exception, other packages unaffected;
* conflicts: same name in two sources / two versions in one source / a built-in name -> reported, the
  documented winner used, install of a built-in name refused, downgrade refused;
* version skew: a form saved with a newer package (unknown property) or an older one (missing property):
  unknown values kept, new ones get defaults;
* user controls: used by a form, the user control file missing (placeholder, data kept), back again
  (registered again, the placeholder replaced);
* ActiveX: an unknown OCX on a VB6 form becomes a placeholder that keeps its class and properties; edited
  in place (VB6 project opened natively) the OCX block of the .frm stays byte-identical.

Run:  .venv\\Scripts\\python samples/Tests/Robustness/Controls/test_controls_model.py
"""
import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _nondef_harness import COMP_DIR, COMPONENT_SAMPLES, ROOT, SAMPLES, WORK, check, copy_tree, finish, raises  # noqa: E402

from radide import components as C  # noqa: E402
from radide.components import codegen  # noqa: E402
from radide.controls import CONTROL_TYPES  # noqa: E402
from radide.languages import all_plugins, get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402

for _p in all_plugins():
    codegen.wrap_plugin(_p)
PY = sys.executable
LANGS = ("python-tk", "python-qt", "vb-basic", "csharp-bridge", "javascript", "ring-qt", "java-bridge", "flutter",
         "kivy", "php", "go-bridge")


def gen(form: Form, lang: str) -> str:
    return get_plugin(lang).generate_designer(form, "")


def compiles(code: str, name: str) -> str:
    p = WORK / f"_{name}.py"
    p.write_text(code, encoding="utf-8")
    try:
        py_compile.compile(str(p), doraise=True)
        return ""
    except py_compile.PyCompileError as e:
        return str(e)[:400]


def run_py(folder: Path, code: str, timeout: int = 90, env_extra=None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen", **(env_extra or {}))
    return subprocess.run([PY, "-c", code], cwd=str(folder), capture_output=True, text=True, timeout=timeout, env=env,
                          encoding="utf-8", errors="replace")


def control_dict(path: Path, name: str) -> dict:
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    return next(c for c in d["controls"] if c["props"].get("Name") == name)


# =========================================================================== registry / built-ins
C.REGISTRY.discover()
built = C.builtin_packages()
rm = sorted(n for n in built if n.startswith("Rm"))
check(f"built-in packages load ({len(built)})", len(built) > 60, len(built))
check(f"the 29 RAD Modern Rm* packages are built in ({len(rm)})", len(rm) == 29, rm)
bad = {n: p.errors for n, p in built.items() if p.errors}
check("every built-in manifest validates without errors", not bad, bad)
check("every Rm* package is a control type with a Toolbox category",
      all(n in CONTROL_TYPES and CONTROL_TYPES[n].category for n in rm), [n for n in rm if n not in CONTROL_TYPES])
check("Rm* are generated through their runtime classes (class_runtime)", all(C.class_runtime(built[n]) for n in rm))


# =========================================================================== Rm*: every property, every kind
def other_value(d, cur):
    k = d.kind
    meta = d.meta or {}
    if k == "bool":
        return not bool(cur)
    if k in ("enum", "alignment") and d.choices:
        rest = [c for c in d.choices if c != cur]
        return rest[-1] if rest else cur
    if k == "int":
        hi = meta.get("max")
        v = int(cur or 0) + 1
        return min(v, int(hi)) if hi is not None and v > int(hi) else v
    if k == "float":
        hi = meta.get("max")
        v = float(cur or 0) + 0.5
        return min(v, float(hi)) if hi is not None and v > float(hi) else v
    if k == "color":
        return "#123456" if cur != "#123456" else "#654321"
    if k == "multiline":
        return "line 1\nسطر 2"
    if k == "list":
        return "Alpha;Beta;Gamma"
    if k == "font":
        return "Consolas"
    if k == "str":
        return (str(cur) + " ع") if cur else "Text ع"
    return cur


form = Form()
form.props.update(Name="RmAll", Width=1200, Height=900)
y, edited, kinds = 10, {}, {}
for n in rm:
    c = form.add(n, 10, y)
    y += 20
    for d in CONTROL_TYPES[n].extra:
        v = other_value(d, c.props.get(d.name))
        if v != c.props.get(d.name):
            c.props[d.name] = v
            edited[(c.name, d.name)] = v
            kinds[d.kind] = kinds.get(d.kind, 0) + 1
check(f"Rm*: {len(edited)} properties set to non-default values (kinds {sorted(kinds)})",
      len(edited) > 150 and {"enum", "bool", "int", "color", "str"} <= set(kinds), kinds)
fpath = WORK / "RmAll.form"
form.save(fpath)
back = Form.load(fpath)
lost = [(cn, pn) for (cn, pn), v in edited.items() if back.find(cn).props.get(pn) != v]
check("Rm*: every edited property survives save + reload", not lost, lost[:10])
form.save(fpath)
check("Rm*: an unchanged save after the reload is byte-identical", Form.load(fpath).snapshot() == back.snapshot())
for lang in LANGS:
    try:
        code = gen(back, lang)
        err = compiles(code, f"rm_{lang}") if lang.startswith("python") else ""
        check(f"Rm*: {lang} code generated for the edited form" + (" (compiles)" if lang.startswith("python") else ""),
              code and not err, err)
    except Exception as e:  # noqa: BLE001
        check(f"Rm*: {lang} code generated for the edited form", False, f"{type(e).__name__}: {e}")

# run (F5 equivalent): a python-tk program with every visual Rm control at its defaults, window withdrawn
rmrun = WORK / "RmRun"
rmrun.mkdir()
f2 = Form()
f2.props.update(Name="Form1", Width=1100, Height=900, Text="Rm run")
yy = 5
for n in rm:
    if not CONTROL_TYPES[n].nonvisual:
        f2.add(n, 5, yy)
        yy += 28
tk = get_plugin("python-tk")
(rmrun / tk.designer_file("Form1")).write_text(tk.generate_designer(f2, ""), encoding="utf-8")
(rmrun / tk.code_file("Form1")).write_text(tk.new_code(f2, True), encoding="utf-8")
C.copy_runtimes(rmrun, [f2], lambda _f: "python-tk")
r = run_py(rmrun, "import Form1_designer as d, Form1 as m\nf = m.Form1()\nf.root.withdraw()\nf.root.update()\n"
                  "print('CONTROLS', sum(1 for k in vars(f) if k.startswith('Rm')))\nf.root.destroy()")
check("Rm*: the generated python-tk program with every visual Rm control starts (F5, window withdrawn)",
      r.returncode == 0 and "CONTROLS" in r.stdout, (r.stdout + r.stderr)[-800:])

# =========================================================================== installed package (.radcomp)
pkg = C.install_package(COMPONENT_SAMPLES / "StarRating.radcomp", "user")
check("StarRating.radcomp installs into the (test) user components folder", (COMP_DIR / "StarRating" / "component.json").is_file())
t = CONTROL_TYPES.get("StarRating")
check("the installed package is a control type in its Toolbox category 'Rating & Input'",
      t is not None and t.category == "Rating & Input" and not C.is_missing("StarRating"), getattr(t, "category", None))
check("the package supports python-tk and python-qt", pkg.supports("python-tk") and pkg.supports("python-qt"))
sr = copy_tree(COMPONENT_SAMPLES / "StarRating_PythonTk", "StarRating_PythonTk")
for f in sr.glob("starrating_*.py"):
    f.unlink()                                   # the runtime must be copied by the IDE again
srf = sr / "Form1.form"
raw_sr = srf.read_bytes()
fs = Form.load(srf)
stars = [c for c in fs.controls if c.type == "StarRating"]
check("StarRating_PythonTk/Form1.form opens with real StarRating controls", len(stars) >= 2 and not C.is_missing("StarRating"))
# edit every kind of the package's properties
s0 = stars[0]
vals = {"MaxStars": 7, "ReadOnly": True, "StarColor": "#FF0000", "Shape": "Circle", "Spacing": 9, "Padding": "1, 2, 3, 4",
        "ShowValue": True, "Caption": "note\nline 2", "Value": 6}
s0.props.update(vals)
fs.save(srf)
back = Form.load(srf).find(s0.name)
check("StarRating: int / bool / colour / enum / padding / multiline / custom-editor values survive save + reload",
      all(back.props.get(k) == v for k, v in vals.items()), {k: back.props.get(k) for k in vals})
code = gen(Form.load(srf), "python-tk")
check("StarRating: python-tk code generated and compiles", not compiles(code, "sr_tk") and "StarRating" in code)
code_qt = gen(Form.load(srf), "python-qt")
check("StarRating: python-qt code generated and compiles", not compiles(code_qt, "sr_qt") and "StarRating" in code_qt)
(sr / "Form1_designer.py").write_text(code, encoding="utf-8")
copied = C.copy_runtimes(sr, [Form.load(srf)], lambda _f: "python-tk")
check("StarRating: the runtime is copied into the project on save/run", any("starrating_tk" in c for c in copied), copied)
r = run_py(sr, "import Form1 as m\nf = m.Form1()\nf.root.withdraw()\nf.root.update()\n"
               f"f.{s0.name}.SetValue(2)\nprint('VALUE', f.{s0.name}.Value)\nf.root.destroy()")
check("StarRating: the python-tk program runs and the package methods work (F5, withdrawn)",
      r.returncode == 0 and "VALUE 2" in r.stdout, (r.stdout + r.stderr)[-600:])

# =========================================================================== project package (.radide/components)
rb = copy_tree(COMPONENT_SAMPLES / "RatingBar_PythonQt", "RatingBar_PythonQt")
for f in rb.glob("ratingbar_*.py"):
    f.unlink()
frb = Form.load(rb / "Form1.form")
bars = [c for c in frb.controls if c.type == "RatingBar"]
pkg_rb = C.package_of("RatingBar")
check("RatingBar (project package in .radide/components) loads with the form",
      bars and pkg_rb is not None and pkg_rb.source == "project", getattr(pkg_rb, "source", None))
qt = get_plugin("python-qt")
(rb / qt.designer_file("Form1")).write_text(qt.generate_designer(frb, ""), encoding="utf-8")
C.copy_runtimes(rb, [frb], lambda _f: "python-qt")
r = run_py(rb, "from PySide6.QtWidgets import QApplication\nimport sys\napp = QApplication.instance() or QApplication(sys.argv)\n"
               "import Form1 as m\nf = m.Form1()\n"
               f"print('BAR', type(f.{bars[0].name}).__name__)\n")
check("RatingBar: the generated python-qt (PySide6) program builds the form offscreen",
      r.returncode == 0 and "BAR RatingBar" in r.stdout, (r.stdout + r.stderr)[-600:])

# =========================================================================== package missing / uninstalled
form_open = Form.load(srf)                        # "open in the designer" while the package is removed
orig_star = control_dict(srf, s0.name)
C.uninstall_package("StarRating", "user")
check("uninstalled while a form uses it: the type becomes a 'not installed' placeholder (no KeyError)",
      C.is_missing("StarRating") and form_open.find(s0.name).ctype.category == C.MISSING_CATEGORY)
check("... the Toolbox no longer offers it (placeholder category hidden)", CONTROL_TYPES["StarRating"].category == C.MISSING_CATEGORY)
form_open.find("btnReset").props["Text"] = "Reset!" if form_open.find("btnReset") else None
form_open.save(srf)
check("... saving the open form keeps the StarRating's data exactly", control_dict(srf, s0.name) == orig_star,
      control_dict(srf, s0.name))
raw_before = srf.read_bytes()
fm = Form.load(srf)                               # a fresh open while missing
check("package missing when the form is opened: the form opens with placeholders",
      all(c.ctype.category == C.MISSING_CATEGORY for c in fm.controls if c.type == "StarRating"))
fm.save(srf)
check("package missing: open -> save is byte-identical", srf.read_bytes() == raw_before)
other = next(c for c in fm.controls if c.type != "StarRating")
other.props["Left"] = int(other.props["Left"]) + 1
fm.save(srf)
check("package missing: editing another control keeps the placeholder's props exactly (no defaults added)",
      control_dict(srf, s0.name) == orig_star, set(control_dict(srf, s0.name)["props"]) ^ set(orig_star["props"]))
ph = fm.find(s0.name)
ph.props["Left"] = int(ph.props["Left"]) + 5
fm.save(srf)
moved = control_dict(srf, s0.name)
check("package missing: moving the placeholder writes the new position and keeps everything else",
      moved["props"]["Left"] == int(orig_star["props"]["Left"]) + 5 and
      {k: v for k, v in moved["props"].items() if k != "Left"} == {k: v for k, v in orig_star["props"].items() if k != "Left"},
      moved)
crash = []
for p in all_plugins():
    try:
        p.generate_designer(fm, "")
    except Exception as e:  # noqa: BLE001
        crash.append(f"{p.id}: {type(e).__name__}: {e}")
check(f"package missing: all {len(all_plugins())} language plugins generate code without crashing", not crash, crash[:5])
check("package missing: python-tk generates a visible placeholder with a warning",
      "not installed" in gen(fm, "python-tk"))
C.install_package(COMPONENT_SAMPLES / "StarRating.radcomp", "user")
fr = Form.load(srf)
s1 = fr.find(s0.name)
check("package installed again: the control is real again with its saved values",
      not C.is_missing("StarRating") and s1.props.get("MaxStars") == 7 and s1.props.get("Shape") == "Circle",
      {k: s1.props.get(k) for k in vals})

# =========================================================================== broken packages (dev path)
dev = WORK / "devpkgs"
dev.mkdir()


def pkgdir(folder, manifest, files=None):
    d = dev / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "component.json").write_text(manifest if isinstance(manifest, str) else json.dumps(manifest), encoding="utf-8")
    for k, v in (files or {}).items():
        (d / k).parent.mkdir(parents=True, exist_ok=True)
        (d / k).write_text(v, encoding="utf-8")
    return d


base = {"schemaVersion": 1, "version": "1.0.0", "category": "Robustness", "kind": "visual",
        "properties": [{"name": "Level", "type": "int", "default": 1}], "events": [{"name": "Changed"}]}
pkgdir("BadJson", "{ \"name\": \"BadJson\", ")
pkgdir("NoName", dict(base))
pkgdir("BadPropType", dict(base, name="BadPropType", properties=[{"name": "X", "type": "spaceship", "default": 1}]))
pkgdir("BoomDesigner", dict(base, name="BoomDesigner", designer="designer.py"),
       {"designer.py": "raise RuntimeError('designer.py exploded on import')\n"})
pkgdir("NoRuntime", dict(base, name="NoRuntime", targets={"python-tk": {"file": "runtime/missing_tk.py", "class": "NoRuntime"}}))
pkgdir("GoodOne", dict(base, name="GoodOne"))
os.environ["RADIDE_COMPONENT_PATH"] = str(dev)
e = raises(C.REGISTRY.discover)
check("broken packages in the search path: discover() does not raise", e is None, e)
broken = dict(C.REGISTRY.broken)
check("invalid component.json is reported in Registry.broken (not valid JSON)",
      any("BadJson" in k and "JSON" in v for k, v in broken.items()), broken)
check("a manifest without a name is reported in Registry.broken", any("NoName" in k for k in broken), broken)
check("the other packages still load (GoodOne is a control type)", "GoodOne" in CONTROL_TYPES and not C.is_missing("GoodOne"))
bp = C.REGISTRY.get("BadPropType")
check("an unknown property type is reported in the package errors", bp is not None and any("spaceship" in x for x in bp.errors),
      getattr(bp, "errors", None))
bd = C.REGISTRY.get("BoomDesigner")
mod = bd.designer_module() if bd else "missing"
check("designer.py raising on import: module() returns None and the error is kept (no exception)",
      bd is not None and mod is None and any("exploded" in x for x in bd.errors), getattr(bd, "errors", None))
check("... the control is still usable (a type with the default renderer)", "BoomDesigner" in CONTROL_TYPES)
nr = C.REGISTRY.get("NoRuntime")
check("a missing runtime file is reported in the package errors", nr is not None and any("missing_tk" in x for x in nr.errors),
      getattr(nr, "errors", None))
fb = Form()
fb.props["Name"] = "FB"
fb.add("BoomDesigner", 5, 5)
fb.add("NoRuntime", 5, 40)
try:
    code = gen(fb, "python-tk")
    check("broken packages on a form: python-tk generation does not crash (placeholder for the missing runtime)",
          not compiles(code, "fb_tk"))
except Exception as ex:  # noqa: BLE001
    check("broken packages on a form: python-tk generation does not crash", False, f"{type(ex).__name__}: {ex}")

# =========================================================================== conflicts
pkgdir("DupA", dict(base, name="DupCtl", version="1.0.0"))
pkgdir("DupB", dict(base, name="DupCtl", version="3.0.0"))
ucopy = COMP_DIR / "DupCtl"
ucopy.mkdir()
(ucopy / "component.json").write_text(json.dumps(dict(base, name="DupCtl", version="9.0.0")), encoding="utf-8")
pkgdir("Button", dict(base, name="Button"))
C.REGISTRY.discover()
win = C.REGISTRY.get("DupCtl")
conf = C.REGISTRY.conflicts
check("two packages with the same name: the conflict is reported", sum("DupCtl" in x for x in conf) >= 2, conf)
check("... the dev source wins over the user source, then the higher version (3.0.0)",
      win is not None and win.source == "dev" and win.version == "3.0.0", getattr(win, "summary", lambda: None)())
check("a package named like a built-in control (Button) is ignored and reported",
      any(x.startswith("Button") and "built-in" in x for x in conf) and C.package_of("Button").builtin)
e = raises(lambda: C.install_package(dev / "Button", "user"), C.ComponentError)
check("installing a package with a built-in name is refused", e is not None and "built-in" in str(e), e)
shutil.rmtree(ucopy)
shutil.rmtree(dev / "Button")

# =========================================================================== version skew
v1 = WORK / "VerCtl_v1"
v2 = WORK / "VerCtl_v2"
for d, ver, props in ((v1, "1.0.0", [{"name": "A", "type": "int", "default": 1}]),
                      (v2, "2.0.0", [{"name": "A", "type": "int", "default": 1}, {"name": "B", "type": "str", "default": "bee"}])):
    d.mkdir()
    (d / "component.json").write_text(json.dumps(dict(base, name="VerCtl", version=ver, properties=props)), encoding="utf-8")
C.install_package(v2, "user")
vf = Form()
vf.props["Name"] = "VerForm"
vc = vf.add("VerCtl", 5, 5)
vc.props.update(A=5, B="saved by v2", C="from v3")     # C: a property of a newer version
vf.save(WORK / "VerForm.form")
e = raises(lambda: C.install_package(v1, "user"), C.ComponentError)
check("installing an older version over a newer one is refused (no silent downgrade)", e is not None and "newer" in str(e), e)
C.install_package(v1, "user", allow_downgrade=True)
check("downgrade with allow_downgrade=True installs version 1.0.0", C.REGISTRY.get("VerCtl").version == "1.0.0")
fv = Form.load(WORK / "VerForm.form")
fv.props["Text"] = "edited with v1"
fv.save(WORK / "VerForm.form")
p1 = control_dict(WORK / "VerForm.form", vc.name)["props"]
check("older package: properties it does not know (B of v2, C of v3) are kept when the form is saved",
      p1.get("B") == "saved by v2" and p1.get("C") == "from v3" and p1.get("A") == 5, p1)
C.install_package(v2, "user")
v2f = WORK / "VerOld.form"
v2f.write_text(json.dumps({"version": 2, "props": {"Name": "VerOld"}, "controls": [
    {"type": "VerCtl", "props": {"Name": "VerCtl1", "Left": 1, "Top": 1, "Width": 50, "Height": 20, "A": 3}}]}), encoding="utf-8")
fo = Form.load(v2f)
check("newer package: a form saved with version 1 gets the new property's default (B = 'bee'), A kept",
      fo.find("VerCtl1").props.get("B") == "bee" and fo.find("VerCtl1").props.get("A") == 3)

# =========================================================================== user controls
uc = copy_tree(SAMPLES / "Tests" / "UserControls" / "UC_PythonQt_AddressBox", "UC_AddressBox")
from radide import usercontrols as UCM  # noqa: E402
fu = Form.load(uc / "Form1.form")
uct = sorted({c.type for c in fu.controls if c.type in UCM.USER_CONTROLS})
check("a form using user controls opens with them registered", "AddressBox" in uct, uct)
codeu = gen(fu, "python-qt")
check("user controls: python-qt code generated and compiles", not compiles(codeu, "uc_qt"))
inst = next(c for c in fu.controls if c.type == "AddressBox")
orig_inst = control_dict(uc / "Form1.form", inst.name)
hidden = uc / "AddressBox.form.hidden"
(uc / "AddressBox.form").rename(hidden)
UCM.unregister("AddressBox")
check("user control unregistered while a form uses it: placeholder instead of a KeyError",
      C.is_missing("AddressBox") and inst.ctype.category == C.MISSING_CATEGORY)
raw_u = (uc / "Form1.form").read_bytes()
fu2 = Form.load(uc / "Form1.form")
fu2.save(uc / "Form1.form")
check("user control file missing: the form opens and an unchanged save is byte-identical", (uc / "Form1.form").read_bytes() == raw_u)
next(c for c in fu2.controls if c.type != "AddressBox").props["Top"] = 3
fu2.save(uc / "Form1.form")
check("user control file missing: editing another control keeps the instance's data exactly",
      control_dict(uc / "Form1.form", inst.name) == orig_inst)
hidden.rename(uc / "AddressBox.form")
fu3 = Form.load(uc / "Form1.form")
check("user control file back: registered again (the placeholder is replaced)",
      "AddressBox" in UCM.USER_CONTROLS and not C.is_missing("AddressBox") and
      next(c for c in fu3.controls if c.type == "AddressBox").ctype.category != C.MISSING_CATEGORY)

# =========================================================================== ActiveX / OCX
from radide.foreign import vb6_project as V  # noqa: E402
from radide.importers.vb6_import import import_vb6  # noqa: E402

ocx = WORK / "Ocx"
ocx.mkdir()
FRM = ('VERSION 5.00\r\nObject = "{AAAA0000-1111-2222-3333-444455556666}#1.0#0"; "ACMEGRID.OCX"\r\n'
       'Begin VB.Form frmX \r\n   Caption         =   "X"\r\n   ClientHeight    =   3000\r\n   ClientWidth     =   4500\r\n'
       '   Begin AcmeGridLib.FancyGrid Grid1 \r\n      Height          =   1500\r\n      Left            =   120\r\n'
       '      TabIndex        =   0\r\n      Top             =   120\r\n      Width           =   3000\r\n'
       '      _ExtentX        =   5292\r\n      _Version        =   65536\r\n      Rows            =   7\r\n'
       '      Theme           =   "Ocean"\r\n   End\r\n   Begin VB.CommandButton cmdOk \r\n      Caption         =   "OK"\r\n'
       '      Height          =   495\r\n      Left            =   1200\r\n      TabIndex        =   1\r\n      Top             =   2000\r\n'
       '      Width           =   1215\r\n   End\r\nEnd\r\nAttribute VB_Name = "frmX"\r\nPrivate Sub cmdOk_Click()\r\nEnd Sub\r\n')
(ocx / "frmX.frm").write_bytes(FRM.encode("cp1252"))
(ocx / "Ocx2.vbp").write_bytes(b'Type=Exe\r\nObject={AAAA0000-1111-2222-3333-444455556666}#1.0#0; ACMEGRID.OCX\r\n'
                               b'Form=frmX.frm\r\nStartup="frmX"\r\nName="Ocx2"\r\n')
rep = import_vb6(ocx / "Ocx2.vbp", WORK / "OcxImported", "python-tk")
fi = Form.load(WORK / "OcxImported" / "frmX.form")
g = fi.find("Grid1")
check("VB6 import: an unknown OCX becomes a placeholder and the report says so",
      g is not None and any("Grid1" in w and "placeholder" in w for w in rep.warnings), rep.warnings[:3])
check("VB6 import: the placeholder keeps the OCX class and its saved properties",
      g is not None and g.props.get("ActiveXClass") == "AcmeGridLib.FancyGrid"
      and g.props.get("ActiveXProperties", {}).get("theme") == "Ocean", g.props if g else None)
check("VB6 import: the imported form generates python-tk code", not compiles(gen(fi, "python-tk"), "ocx_tk"))
mdir, nat = V.build_mirror(ocx / "Ocx2.vbp", WORK / "OcxMirror")
fx = Form.load(Path(mdir) / "frmX.form")
fx.find("cmdOk").props["Text"] = "Okay"
fx.save(Path(mdir) / "frmX.form")
V.sync_mirror(mdir)
new = (ocx / "frmX.frm").read_bytes().decode("cp1252")
ocx_block = FRM[FRM.index("   Begin AcmeGridLib"):FRM.index("   Begin VB.CommandButton")]
check("VB6 opened in place: after editing another control the unknown OCX block of the .frm is byte-identical",
      ocx_block in new and 'Caption         =   "Okay"' in new, new[:400])
check("VB6 opened in place: the Object= line of the .vbp is kept",
      b"ACMEGRID.OCX" in (ocx / "Ocx2.vbp").read_bytes())

os.environ.pop("RADIDE_COMPONENT_PATH", None)

# =========================================================================== Publish: native or fallback
from radide.deploy.build import fallback_kind  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.deploy.native import builder_for  # noqa: E402
from radide.model import Control, Project  # noqa: E402

C.REGISTRY.discover()
for lang in ("vb-basic", "c-bridge", "csharp-bridge", "rust-bridge", "go-bridge"):
    mod = builder_for(lang)
    if mod is None:
        check(f"Publish {lang}: a native builder exists", False)
        continue
    res = {}
    for case in ("package", "missing", "rm"):
        d = WORK / f"pub_{lang}_{case}"
        d.mkdir()
        f = Form()
        f.props.update(Name="Form1", Text="t")
        f.add("Button", 5, 5)
        if case == "package":
            f.add("StarRating", 5, 40)
        elif case == "rm":
            f.add("RmGauge", 5, 40)
        else:
            f.controls.append(Control.from_dict({"type": "GhostPkg", "props": {"Name": "Ghost1", "Left": 5, "Top": 40,
                                                                             "Width": 40, "Height": 20}}))
        f.save(d / "Form1.form")
        pl = get_plugin(lang)
        (d / pl.code_file("Form1")).write_text(pl.new_code(f, True), encoding="utf-8")
        (d / pl.designer_file("Form1")).write_text(pl.generate_designer(f, ""), encoding="utf-8")
        Project(d, "T", lang, ["Form1"], "Form1").save()
        try:
            res[case] = list(mod.check(d, Project.load(d), PublishConfig()))
        except Exception as ex:  # noqa: BLE001
            res[case] = ex
    check(f"Publish {lang}: an installed package without a native runtime -> native check gives a reason "
          f"(falls back to {fallback_kind(lang)})", isinstance(res["package"], list) and res["package"], res["package"])
    check(f"Publish {lang}: a missing-package placeholder -> a reason, no exception",
          isinstance(res["missing"], list) and any("GhostPkg" in r for r in res["missing"]), res["missing"])
    if lang != "vb-basic":
        check(f"Publish {lang}: RmGauge is built natively (no reason)", res["rm"] == [], res["rm"])

finish()
