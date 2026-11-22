"""Native Swing build (radide/deploy/native/java_native.py) - a Java project becomes a jpackage exe with its own
jlink-trimmed Java runtime, no Python. The exe is started and driven.

    .venv\\Scripts\\python samples/Tests/Native/test_native_java.py

Swing draws its controls itself (no native child windows for Win32 messages), so the test build is made with
RADIDE_NATIVE_TEST_HOOK=1: the exe then also contains RadTestHook (commands on stdin, "R <result>" on stdout).
A second build without the variable is checked to contain no hook (release builds never have it).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

from radide.deploy import build as B  # noqa: E402
from radide.deploy import config as C  # noqa: E402
from radide.deploy.native import builder_for, java_native as J  # noqa: E402
from radide.model import Form, Project  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:500]}]"), flush=True)
    return bool(cond)


def copy_project(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("Publish", "_build", "__pycache__"))
    return dst


def no_python(dist: Path) -> list[str]:
    return [str(f.relative_to(dist)) for f in dist.rglob("*")
            if (f.name.lower().startswith("python") and f.name.lower().endswith(".dll"))
            or f.name.lower().endswith((".pyd", ".pyc", ".pyz")) or f.name == "_internal"]


def jar_names(dist: Path) -> list[str]:
    jar = dist / "app" / "app.jar"
    with zipfile.ZipFile(jar) as z:
        return z.namelist()


class Hook:
    def __init__(self, exe: Path):
        self.p = subprocess.Popen([str(exe)], cwd=str(exe.parent), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def q(self, cmd: str) -> str:
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline().strip()
        return line[2:] if line.startswith("R ") else line

    def wait_for(self, cmd: str, want: str, timeout: float = 10) -> str:
        end, got = time.time() + timeout, ""
        while time.time() < end:
            got = self.q(cmd)
            if got == want:
                return got
            time.sleep(0.1)
        return got


def drive(exe: Path) -> None:
    h = Hook(exe)
    try:
        check("Java: main window 'Native test' appears", h.wait_for("windows", "Native test", 30) == "Native test")
        check("Java: Form1_Load ran", h.wait_for("get lblOut Text", "Loaded", 5) == "Loaded")
        check("Java: design values (txtName World, list 1 item)",
              h.q("get txtName Text") == "World" and h.q("get lstLog ListCount") == "1")
        h.q("type txtName Ali")
        check("Java: TextChanged (typing) -> lblEcho", h.wait_for("get lblEcho Text", "echo:Ali", 5) == "echo:Ali")
        h.q("click btnGreet")
        check("Java: Click + module call (Hello, Ali!)", h.q("get lblOut Text") == "Hello, Ali!")
        check("Java: addItem + getListCount (2 items)", h.q("get lblCount Text") == "2 items" and h.q("get lstLog ListCount") == "2")
        h.q("click chkShout")
        check("Java: CheckBox Value = 1", h.q("get chkShout Value") == "1")
        h.q("click btnGreet")
        check("Java: radcall (HELLO, ALI!)", h.q("get lblOut Text") == "HELLO, ALI!")
        h.q("click btnStart")
        check("Java: Timer ticks 5 times", h.wait_for("get lblTicks Text", "5", 10) == "5")
        time.sleep(0.4)
        check("Java: timer stopped at 5", h.q("get lblTicks Text") == "5" and h.q("get tmrTick Enabled") == "False")
        h.q("menu mnuFileHello")
        check("Java: menu File > Hello", h.q("get lblOut Text") == "Menu clicked")
        h.q("click btnForm2")
        check("Java: show(\"Form2\") opens the second form",
              h.wait_for("windows", "Native test|Second form", 5) == "Native test|Second form")
        check("Java: Form2_Load ran", h.q("get Form2.lblMsg Text") == "Form2 loaded")
        h.q("click Form2.btnBack")
        check("Java: Form2 sets Form1.lblOut and hides itself",
              h.q("get lblOut Text") == "From Form2" and h.wait_for("windows", "Native test", 5) == "Native test")
        check("Java: Anchor Bottom,Right keeps btnClose at the bottom right",
              h.q("get btnClose Left") == "360" and h.q("get btnClose Top") == "290", (h.q("get btnClose Left"), h.q("get btnClose Top")))
        h.p.stdin.write("click btnClose\n")
        h.p.stdin.flush()
        try:
            code = h.p.wait(10)
        except subprocess.TimeoutExpired:
            code = None
        check("Java: end() closes the program (exit code 0)", code == 0, code)
    finally:
        if h.p.poll() is None:
            h.p.kill()
            h.p.wait(5)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="radnative_java_"))
    try:
        check("builder_for java-bridge is java_native", builder_for("java-bridge") is J)
        jdk = J.find_jdk()
        check(f"a JDK with jlink + jpackage is found ({jdk})", jdk is not None)
        folder = copy_project(HERE / "Java" / "NativeJava", tmp / "NativeJava")
        cfg = C.load(folder, folder.name)
        lines: list[str] = []
        os.environ[J.TEST_HOOK_ENV] = "1"
        try:
            res = B.build(folder, cfg, log=lines.append)
        finally:
            os.environ.pop(J.TEST_HOOK_ENV, None)
        check(f"auto build kind is native ({res.kind})", res.kind == "native-jlink", "\n".join(lines[-15:]))
        exe = res.dist / res.exe
        check("exe + private runtime exist", exe.is_file() and (res.dist / "runtime" / "bin" / "server" / "jvm.dll").is_file())
        check("no Python in the program folder", not no_python(res.dist), no_python(res.dist))
        check("runtime has only the needed modules (java.base, java.desktop; no java.sql)",
              "java.desktop" in (res.dist / "runtime" / "release").read_text() and
              "java.sql" not in (res.dist / "runtime" / "release").read_text())
        check("data file copied next to the exe", (res.dist / "readme.txt").is_file())
        total = sum(f.stat().st_size for f in res.dist.rglob("*") if f.is_file())
        check(f"program folder < 60 MB ({total / 1024 / 1024:.1f} MB, launcher {exe.stat().st_size / 1024:.0f} KB)",
              total < 60 * 1024 * 1024)
        check("test build contains RadTestHook", "RadTestHook.class" in jar_names(res.dist))
        drive(exe)
        # release build: no hook
        folder2 = copy_project(HERE / "Java" / "NativeJava", tmp / "Release" / "NativeJava")
        res2 = B.build(folder2, C.load(folder2, folder2.name), log=lambda s: None)
        check("release build has no test hook", "RadTestHook.class" not in jar_names(res2.dist))
        # unsupported control -> check() reason (FontDialog has no Swing dialog)
        form = Form.load(folder2 / "Form1.form")
        form.add("FontDialog", 0, 0).props["Name"] = "dlgFont"
        form.save(folder2 / "Form1.form")
        reasons = J.check(folder2, Project.load(folder2), cfg)
        check("check(): FontDialog is a reason", any("FontDialog" in r for r in reasons), reasons)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
