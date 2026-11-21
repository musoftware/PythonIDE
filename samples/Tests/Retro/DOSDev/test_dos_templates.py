"""Every DOS template: New Project (plugin.create_new_project) -> build a real DOS program -> run it in DOSBox-X
without a window for a few seconds (keys stuffed with RADKEYS, output redirected to a file + the text screen saved
by RADSCR, mode 13h frames by RADCAP) -> compare with the expected text. Also: the program is a real MZ / COM file,
Error List rows for a broken source of each compiler (file:line), and `run.py --capture`.

    python test_dos_templates.py [filter...]
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from _common import ROOT, WORK, check, skip, summary

from radide.languages import get_plugin
from radide.model import Project
from radide.retro.dos import build as B
from radide.retro.dos import dosbox, helpers, toolchain as T
from radide.retro.dos.templates import TEMPLATES

# template suffix -> (keys, expected text)   (~ = Enter, ` = Esc)
EXPECT = {"hello": ("Ali~", "Welcome to DOS programming, Ali"), "menu": ("1 2 3 4", "Goodbye"),
          "mode13": ("x", "Back in text mode"), "speaker": ("", "Finished"), "mouse": ("`", "finished"),
          "lines": ("", "SUM OF DATA = 150"), "com": ("", "Hello from a .COM program"),
          "bgi": ("x", "Back in text mode"), "launcher": ("", "GAME.EXE was not found")}
EXPECT_KIND = {("asm", "hello"): ("k", "You pressed: k"), ("batch", "hello"): ("", "Done."),
               ("batch", "menu"): ("3", "Goodbye"), ("asm", "menu"): ("1 4", "Goodbye")}
BROKEN = {"qbasic": ("MAIN.BAS", "PRINT \"x\"\r\nY = \r\n", 2), "pascal": ("MAIN.PAS", "program P;\r\nbegin\r\n  x := 1;\r\nend.\r\n", 3),
          "c": ("MAIN.C", "int main(void)\r\n{\r\n    undefined_x = 1;\r\n    return 0;\r\n}\r\n", 3),
          "asm": ("MAIN.ASM", "        .model small\r\n        .code\r\nstart:  movv ax, 1\r\n        end start\r\n", 3)}


def is_dos_program(path) -> bool:
    data = path.read_bytes()
    if path.suffix.upper() == ".COM":
        return 0 < len(data) <= 65280
    return data[:2] == b"MZ" and b"PE\0\0" not in data[:0x400]


def main(filters: list[str]) -> int:
    root = WORK / "templates"
    shutil.rmtree(root, ignore_errors=True)
    if not T.dosbox_exe():
        skip("DOSBox-X runs", "DOSBox-X not installed (test_dos_toolchains.py downloads it)")
    for t in TEMPLATES:
        if filters and not any(f in t.id for f in filters):
            continue
        comp = T.COMPILER_FOR_KIND[t.kind]
        if comp and not T.ensure_for(comp, log=lambda *_: None, download=False):
            skip(f"{t.id} build", f"{comp} not installed (offline)")
            continue
        plugin = get_plugin(B.LANGUAGE_OF_KIND[t.kind])
        folder = root / t.id
        name = "Demo" + t.id.split("_")[1].capitalize()
        project = plugin.create_new_project(folder, name, t.id)
        check(f"{t.id} created", (folder / t.main).is_file() and Project.load(folder).language == plugin.id)
        lines = []
        ok = B.Builder(folder, project, log=lines.append).build()
        s = B.settings_for(Project.load(folder))
        diags = B.read_diagnostics(folder)
        if t.kind == "batch":
            check(f"{t.id} batch check (GOTO / CALL targets)", ok and not diags["diags"], diags)
        else:
            out = folder / B.output_name(s)
            check(f"{t.id} builds a DOS program ({out.name})", ok and out.is_file() and is_dos_program(out),
                  "\n".join(lines[-12:]))
            check(f"{t.id} no errors / warnings", not [d for d in diags["diags"] if d["severity"] != "Message"],
                  diags["diags"])
        if not T.dosbox_exe():
            continue
        suffix = t.id.split("_", 1)[1]
        keys, want = EXPECT_KIND.get((t.kind, suffix), EXPECT[suffix])
        run = dosbox.DosRun(mounts=[("C", folder)], path=["Z:\\BIN", "Z:\\DOS"])
        cmd = ("CALL " + s["main"]) if t.kind == "batch" else B.output_name(s)
        r = dosbox.capture_text(run, folder, cmd, keys=keys, timeout=25, log=lambda *_: None)
        text = r["stdout"] + "\n" + r["screen"]
        check(f"{t.id} runs in DOSBox-X: \"{want}\"", want.lower() in text.lower() and not r["timed_out"],
              repr(text[-500:]))
        if suffix == "mode13" and t.kind in ("pascal", "c", "asm"):
            g = r["graphics"]
            stats = helpers.mode13_stats(g) if g else {}
            check(f"{t.id} mode 13h frame captured (256 colour bars)", g and stats["colours"] >= 200 and
                  stats["nonzero"] > 20000, stats)
            if g:
                helpers.mode13_png(g, WORK / f"{t.id}.png")
    # broken sources -> Error List rows with file:line
    for kind, (fname, text, line) in BROKEN.items():
        comp = T.COMPILER_FOR_KIND[kind]
        if not T.ensure_for(comp, log=lambda *_: None, download=False):
            skip(f"{kind} error row", f"{comp} not installed")
            continue
        folder = root / f"broken_{kind}"
        shutil.rmtree(folder, ignore_errors=True)
        get_plugin(B.LANGUAGE_OF_KIND[kind]).create_new_project(folder, "Broken")
        (folder / fname).write_bytes(text.encode("ascii"))
        ok = B.Builder(folder, log=lambda *_: None).build()
        rows = [d for d in B.read_diagnostics(folder)["diags"] if d["severity"] == "Error"]
        check(f"{kind} compile error -> Error List row {fname}:{line}", not ok and any(
            d["file"].upper() == fname and d["line"] == line for d in rows), rows)
    # the IDE's runner: python -m radide.retro.dos.run --capture
    folder = root / "dosasm_hello"
    if folder.is_dir() and T.dosbox_exe():
        r = subprocess.run([sys.executable, "-m", "radide.retro.dos.run", str(folder), "--capture", "--keys", "z"],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        check("run.py --capture prints the program output", "You pressed: z" in r.stdout, r.stdout[-600:])
    return summary()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
