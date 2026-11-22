"""The FeatureMatrix form as a VB6 (vb-basic) project for the native FreeBASIC build (fm_project.build_form(vb=True):
cmdShake, cmdMove, cmdColor, cmdHover, cmdAlert, cmdManual ...).

    write_project(dest)    -> dest / project.radproj + Form1.form + Form1.bas (VB user code)

User code: cmdAlert_Click -> GoToState "Alert" (form state + lblTitle's own Alert state), cmdManual_Click ->
Me.BeginAnimation "fx8".  The other VB motion API calls are compiled too (Form1.BeginAnimation, StopAnimation,
CurrentState, CurrentSizes, <storyboard>_Completed, Form_SizeVariantChanged) so the translator covers them.
Used by check_fm_vb6.py; the curated copy lives in FeatureMatrix_VB6/."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fm_project as P  # noqa: E402

CODE = '''Option Explicit
' FeatureMatrix (VB6 -> FreeBASIC native exe): visual state + manual animation from code.

Private Sub cmdAlert_Click()
    GoToState "Alert"
    Debug.Print "state: " & Me.CurrentState
End Sub

Private Sub cmdManual_Click()
    Me.BeginAnimation "fx8"
End Sub

Private Sub fx8_Completed()
    Debug.Print "fx8 completed"
End Sub

Private Sub Form_SizeVariantChanged()
    Debug.Print "sizes: " & Form1.CurrentSizes
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Form1.StopAnimation "fx7"
End Sub
'''


def write_project(dest: Path) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    P.build_form(vb=True).save(dest / "Form1.form")
    (dest / "Form1.bas").write_text(CODE, encoding="utf-8")
    (dest / "project.radproj").write_text(json.dumps({"name": "FeatureMatrix_VB6", "language": "vb-basic",
                                                      "forms": ["Form1"], "startup": "Form1", "modules": []},
                                                     indent=2), encoding="utf-8")
    return dest


if __name__ == "__main__":
    print(write_project(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "FeatureMatrix_VB6"))
