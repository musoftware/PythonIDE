"""Component package controls in VB6 .frm files (export + round-trip import).

A VB6 project (VB6Project/RatingDemo.vbp + Form1.frm) is opened in place (radide.foreign.vb6_project mirror);
two package controls are added to Form1 and the project is saved (sync_mirror):

* RatingBar (samples/Tests/Components/RatingBar) has no VB6 class: it is written as a UserControl reference
  ``Begin RatingDemo.RatingBar rate1`` with its manifest properties as property lines (MaxStars = 7,
  StarColor = &H000000FF&, ReadOnly = -1 'True); RatingBar.ctl (a VB6 UserControl stand-in with the same
  properties, PropertyBag persistence, the ValueChanged event and the method stubs) is written and listed in
  the .vbp (UserControl=RatingBar.ctl).
* LedLight (packages/LedLight, a package made for this test) declares its VB6 equivalent in the manifest
  (``"vb6": {"class": "LedLib.Led", "library": "LedLib", "object": "{GUID}#1.0#0; LEDLIB.OCX", ...}``): it is
  written as ``Begin LedLib.Led led1`` and the Object = line goes to the .frm and the .vbp.
* Not VB.PictureBox any more.
* The .frm is read back (frm_writer.load_form = what reopening the project does): both controls come back
  with their types, geometry and property values; changing a property later edits only its line, and a
  default value removes the line (like VB6's PropertyBag).

Run:  python samples/Tests/Components/RatingBar_VB6Frm/check_vb6_frm.py
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
os.environ["RADIDE_COMPONENT_PATH"] = str(HERE / "packages") + ";" + str(HERE.parent / "RatingBar")
os.environ["RADIDE_COMPONENTS_DIR"] = str(HERE / "_no_user_components")

from radide import components as C  # noqa: E402
from radide.controls import CONTROL_TYPES  # noqa: E402
from radide.model import Form  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:2000]}]"), flush=True)


VBP = """Type=Exe
Form=Form1.frm
Startup="Form1"
Command32=""
Name="RatingDemo"
HelpContextID="0"
CompatibleMode="0"
MajorVer=1
MinorVer=0
RevisionVer=0
AutoIncrementVer=0
ServerSupportFiles=0
CompilationType=0
"""

FRM = """VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Rating demo"
   ClientHeight    =   3000
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   4500
   LinkTopic       =   "Form1"
   ScaleHeight     =   3000
   ScaleWidth      =   4500
   StartUpPosition =   2  'CenterScreen
   Begin VB.Label lblInfo
      Caption         =   "Rate it"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   2000
   End
End
Attribute VB_Name = "Form1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub rate1_ValueChanged()
    lblInfo.Caption = "Rating: " & rate1.Value
End Sub
"""


def setup() -> Path:
    shutil.rmtree(HERE / "_no_user_components", ignore_errors=True)
    proj = HERE / "VB6Project"
    shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir()
    (proj / "RatingDemo.vbp").write_bytes(VBP.replace("\n", "\r\n").encode("cp1252"))
    (proj / "Form1.frm").write_bytes(FRM.replace("\n", "\r\n").encode("cp1252"))
    C.REGISTRY.discover()
    check("packages loaded (RatingBar, LedLight)", C.is_component_type("RatingBar") and
          C.is_component_type("LedLight"), [p.name for p in C.REGISTRY.all(False)])
    return proj


def main():
    proj = setup()
    from radide.foreign import vb6_project as V
    from radide.foreign.frm_writer import load_form
    mdir, _native = V.build_mirror(proj / "RatingDemo.vbp", HERE / "_mirror")
    fpath = mdir / "Form1.form"
    form = Form.load(fpath)
    rb = form.add("RatingBar", 16, 40, "")
    rb.props.update(Name="rate1", Width=140, Height=28, MaxStars=7, StarColor="#FF0000", ReadOnly=True)
    led = form.add("LedLight", 170, 40, "")
    led.props.update(Name="led1", On=True, Color="#00C000", Width=24, Height=24)
    form.save(fpath)
    msgs = V.sync_mirror(mdir)
    frm = (proj / "Form1.frm").read_bytes().decode("cp1252")
    vbp = (proj / "RatingDemo.vbp").read_bytes().decode("cp1252")
    check("RatingBar written as a UserControl reference (not VB.PictureBox)",
          "Begin RatingDemo.RatingBar rate1" in frm and "VB.PictureBox" not in frm, frm)
    block = frm.split("Begin RatingDemo.RatingBar rate1", 1)[1].split("   End", 1)[0]
    check("its manifest properties are property lines", "MaxStars        =   7" in block and
          "StarColor       =   &H000000FF&" in block and "ReadOnly        =   -1  'True" in block and
          "Value " not in block and "EmptyColor" not in block, block)
    check("geometry in twips", "Left            =   240" in block and "Width           =   2100" in block, block)
    ctl = proj / "RatingBar.ctl"
    ctext = ctl.read_text(encoding="cp1252") if ctl.is_file() else ""
    check("RatingBar.ctl stand-in written and listed in the .vbp", "UserControl=RatingBar.ctl" in vbp and
          "Begin VB.UserControl RatingBar" in ctext and "Public Property Let MaxStars(ByVal New_MaxStars As Long)"
          in ctext and 'PropBag.ReadProperty("StarColor", m_def_StarColor)' in ctext and
          "Event ValueChanged()" in ctext and "Public Sub SetValue(ByVal value As Variant)" in ctext, (vbp, ctext))
    check("LedLight written as its declared VB6 class + Object line",
          "Begin LedLib.Led led1" in frm and 'Object = "{6C0F7E10-3B7E-4C1E-9A65-2B5E7C1D0A11}#1.0#0"; "LEDLIB.OCX"'
          in frm and "Object={6C0F7E10-3B7E-4C1E-9A65-2B5E7C1D0A11}#1.0#0; LEDLIB.OCX" in vbp, (frm[:600], vbp))
    led_block = frm.split("Begin LedLib.Led led1", 1)[1].split("   End", 1)[0]
    check("LedLight properties use the manifest's VB6 names (On -> LightOn)", "LightOn         =   -1  'True" in
          led_block and "Color           =   &H0000C000&" in led_block, led_block)
    check("user code kept", "lblInfo.Caption = \"Rating: \" & rate1.Value" in frm, frm[-300:])
    # ---- round trip: read the .frm back
    f2, info = load_form(frm, proj / "Form1.frm")
    r2 = next((c for c in f2.controls if c.name == "rate1"), None)
    l2 = next((c for c in f2.controls if c.name == "led1"), None)
    check("import: rate1 is a RatingBar again", r2 is not None and r2.type == "RatingBar", [(c.name, c.type) for c in f2.controls])
    check("import: property values and geometry round-trip", r2 is not None and r2.props.get("MaxStars") == 7 and
          r2.props.get("StarColor") == "#FF0000" and r2.props.get("ReadOnly") is True and
          r2.props.get("Value") == 3 and (r2.props["Left"], r2.props["Top"], r2.props["Width"]) == (16, 40, 140),
          r2.props if r2 else None)
    check("import: led1 is a LedLight with On / Color", l2 is not None and l2.type == "LedLight" and
          l2.props.get("On") is True and l2.props.get("Color") == "#00C000", l2.props if l2 else None)
    check("import: no placeholder warnings", not [w for w in info.warnings if "rate1" in w or "led1" in w],
          info.warnings)
    # ---- edit again: one property changed, one back to its default
    form = Form.load(fpath)
    for c in form.controls:
        if c.name == "rate1":
            c.props["MaxStars"] = 5          # the default -> the line goes away
            c.props["Value"] = 4
    form.save(fpath)
    V.sync_mirror(mdir)
    frm2 = (proj / "Form1.frm").read_bytes().decode("cp1252")
    b2 = frm2.split("Begin RatingDemo.RatingBar rate1", 1)[1].split("   End", 1)[0]
    check("edit: changed property line written, default removes the line", "Value           =   4" in b2 and
          "MaxStars" not in b2 and "StarColor       =   &H000000FF&" in b2, b2)
    check("edit: the .ctl is not duplicated in the .vbp",
          (proj / "RatingDemo.vbp").read_bytes().decode("cp1252").count("UserControl=") == 1, "")
    # ---- a new form (Add Form) with a package control: new_frm_text
    from radide.foreign.frm_writer import new_frm_text
    nf = Form()
    nf.props.update(Name="Form2", Text="Second", Width=300, Height=200)
    c = nf.add("RatingBar", 8, 8, "")
    c.props.update(Name="rateB", Value=1)
    text, libs = new_frm_text(nf, "", "\r\n", proj / "Form2.frm")
    check("new form: UserControl reference + ctl request", "Begin RatingDemo.RatingBar rateB" in text and
          "Value           =   1" in text and "ctl:RatingBar" in libs, (text, libs))
    print("sync messages:", msgs)
    shutil.rmtree(HERE / "_mirror", ignore_errors=True)
    shutil.rmtree(HERE / "_no_user_components", ignore_errors=True)
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    CONTROL_TYPES  # noqa: B018 - the catalogue is imported before the packages load
    main()
