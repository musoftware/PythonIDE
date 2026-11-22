"""The FeatureMatrix form (fm_project.build_form) as .NET WinForms projects for the native .NET build
(radide/deploy/native/dotnet_winforms.py + RadWinForms.cs RadMotion): C# and PowerShell user code.

    write_project(key, dest)    key "csharp" | "powershell" -> dest / project.radproj + Form1.form + Form1.<ext>
                                + publish.json (dotnet_target, default netfx: the fastest build)

Used by check_fm_dotnet.py (publish with radide.deploy.build.build() and drive with fm_drive)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fm_project as P  # noqa: E402

# Alert -> GoToState("Alert") on the form, Manual -> BeginAnimation("fx8"); the storyboard / size events are
# handled too (not checked by the driver, they show the API)
USER = {
    "csharp": ("csharp-bridge", "Form1.cs", '''// FeatureMatrix: visual state + manual animation from code (native WinForms runtime, RadMotion).
public static partial class Form1
{
    static void btnAlert_Click(RadEvent e)
    {
        Call("Form1", "GoToState", "Alert");
    }

    static void btnManual_Click(RadEvent e)
    {
        Call("Form1", "BeginAnimation", "fx8");
    }

    static void Form1_SizeVariantChanged(RadEvent e)
    {
        Set("Form1", "Tag", Get("Form1", "CurrentSizes"));
    }
}
'''),
    "powershell": ("powershell-bridge", "Form1.ps1", '''# FeatureMatrix: visual state + manual animation from code (native WinForms runtime, RadMotion).
function btnAlert_Click($e) {
    [void](RadInvoke "Form1" "GoToState" "Alert")
}

function btnManual_Click($e) {
    [void](RadInvoke "Form1" "BeginAnimation" "fx8")
}
'''),
}


def write_project(key: str, dest: Path, target: str = "netfx") -> Path:
    lang, fname, code = USER[key]
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    P.build_form().save(dest / "Form1.form")
    (dest / fname).write_text(code, encoding="utf-8")
    (dest / "project.radproj").write_text(json.dumps({"name": "FeatureMatrix", "language": lang, "forms": ["Form1"],
                                                      "startup": "Form1"}, indent=2), encoding="utf-8")
    (dest / "publish.json").write_text(json.dumps({"app_name": "FeatureMatrix", "version": "1.0.0",
                                                   "make_installer": False, "dotnet_target": target}, indent=2),
                                       encoding="utf-8")
    return dest


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "projects"
    for k in USER:
        print(write_project(k, out / ("dotnet-" + k)))
