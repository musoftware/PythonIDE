"""The FeatureMatrix project for Java (java-bridge): fm_project.build_form() + Java user code
(btnAlert -> GoToState("Alert"), btnManual -> BeginAnimation("fx8")), scaffolded like samples/Tests/Native/Java/NativeJava.

    write_project(dest) -> dest / project.radproj + publish.json + Form1.form + Form1.java
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fm_project as P  # noqa: E402

USER_JAVA = '''// FeatureMatrix (Java): visual state + manual animation from code (GUI Bridge client API).
public class Form1 extends Form1Designer {
    static void btnAlert_Click(RadEvent e) {
        call("Form1", "GoToState", "Alert");
    }

    static void btnManual_Click(RadEvent e) {
        call("Form1", "BeginAnimation", "fx8");
    }
}
'''


def write_project(dest: Path) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    P.build_form().save(dest / "Form1.form")
    (dest / "Form1.java").write_text(USER_JAVA, encoding="utf-8")
    (dest / "project.radproj").write_text(json.dumps({"name": "FeatureMatrix", "language": "java-bridge",
                                                      "forms": ["Form1"], "startup": "Form1"}, indent=2),
                                          encoding="utf-8")
    (dest / "publish.json").write_text(json.dumps({"app_name": "FeatureMatrix", "version": "1.0.0",
                                                   "make_installer": False}, indent=2), encoding="utf-8")
    return dest


if __name__ == "__main__":
    print(write_project(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "projects" / "java"))
