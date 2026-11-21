"""DOS Text-Mode Forms App projects: .tform screens -> generated MAIN.BAS / .PAS / .C / .ASM -> DOS program.
No Qt in here.

A forms project is a DOS project of the dosdev slice (radide/retro/dos: ``project.radproj`` ``"dos"`` block with
``kind`` qbasic / pascal / c / asm) that also holds ``*.tform`` files and a ``"tui"`` block::

    "tui": {"target": "freebasic" | "quickbasic" | "qbasic" | "pascal" | "c" | "asm", "startup": "Main"}

``generate(folder)`` rewrites the main source from the screens (user code regions are kept), ``build(folder)``
generates and builds (dosdev's Builder; the asm target is assembled by RAD IDE's own 8086 assembler when JWasm is
not installed), ``run(folder)`` builds and starts DOSBox-X, ``capture(folder, keys)`` runs the program without a
window, feeds it keys and returns its screen (a B800 dump written by the program itself: ``PROG /DUMPKEYS``).

Command line: ``python -m radide.retro.design.textmode.project generate|build|run|capture <folder>``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .buffer import CellBuffer
from .model import TScreen, load_project_screens, new_screen

TARGETS = {
    # target: (dos kind, main file, generator module, title)
    "freebasic": ("qbasic", "MAIN.BAS", "basic", "FreeBASIC (-lang qb)"),
    "quickbasic": ("qbasic", "MAIN.BAS", "basic", "QuickBASIC 4.5 (your own copy)"),
    "qbasic": ("qbasic", "MAIN.BAS", "basic", "QBasic 1.1 (your own copy, keyboard only)"),
    "pascal": ("pascal", "MAIN.PAS", "pascal", "Free Pascal / Turbo Pascal (Crt)"),
    "c": ("c", "MAIN.C", "c", "OpenWatcom / Turbo C / DJGPP"),
    "asm": ("asm", "MAIN.ASM", "asm", "16-bit assembly (.COM, MASM / TASM / JWasm syntax)"),
}
LANGUAGE = "dos-tuiforms"
EXE_NAME = "TUIAPP"


def language_for(kind: str) -> str:
    """The dosdev language of a forms project (dos-qbasic / dos-pascal / dos-c / dos-asm) - its build, run,
    DOS settings and IntelliSense - or this slice's own plugin when that DOS kind is not installed."""
    lang = {"qbasic": "dos-qbasic", "pascal": "dos-pascal", "c": "dos-c", "asm": "dos-asm"}[kind]
    try:
        from ....languages import get_plugin
        get_plugin(lang)
        return lang
    except (KeyError, ImportError):
        return LANGUAGE


def _radproj(folder: Path) -> dict:
    try:
        return json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def settings(folder) -> dict:
    data = _radproj(folder)
    tui = dict(data.get("tui") or {})
    tui.setdefault("target", "freebasic")
    if tui["target"] not in TARGETS:
        tui["target"] = "freebasic"
    return tui


def generator(target: str):
    from .codegen import asm, basic, c, pascal
    return {"basic": basic, "pascal": pascal, "c": c, "asm": asm}[TARGETS[target][2]]


def generate_text(screens: list[TScreen], target: str, old_text: str = "") -> tuple[str, list[str]]:
    mod = generator(target)
    if TARGETS[target][2] == "basic":
        return mod.generate(screens, old_text, dialect=target)
    return mod.generate(screens, old_text)


def main_file(folder, target: str | None = None) -> Path:
    t = target or settings(folder)["target"]
    return Path(folder) / TARGETS[t][1]


def read_dos_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("cp437").replace("\r\n", "\n")
    except OSError:
        return ""


def write_dos_text(path: Path, text: str) -> None:
    """CRLF line ends and CP437 (the DOS compilers' format; the generated code itself is plain ASCII)."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("cp437", "replace")
    try:
        if path.read_bytes() == data:
            return
    except OSError:
        pass
    path.write_bytes(data)


def generate(folder, log=print) -> tuple[Path, list[str]]:
    """Rewrite the main source of *folder* from its .tform screens. Returns (main file, warnings)."""
    folder = Path(folder)
    target = settings(folder)["target"]
    screens = load_project_screens(folder)
    if not screens:
        raise ValueError("The project has no screens (.tform files).")
    path = main_file(folder, target)
    text, warnings = generate_text(screens, target, read_dos_text(path))
    write_dos_text(path, text)
    for w in warnings:
        log(f"{path.name}: warning: {w}")
    return path, warnings


def create(folder, name: str, target: str = "freebasic", sample: bool = True, cols: int = 80,
           rows: int = 25):
    """A new forms project in *folder*: Main.tform, the generated main file, project.radproj."""
    from ....model import Project
    from ...dos.templates import dos_name
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    kind, main, _mod, _t = TARGETS[target]
    scr = folder / "Main.tform"
    if not scr.exists():
        s = new_screen("Main", cols, rows, sample=sample)
        if sample:
            for c in s.controls:
                if c.type == "Button":
                    c.props["events"] = ["Click"]
            bar = next((c for c in s.controls if c.type == "MenuBar"), None)
            if bar is not None:
                bar.props["menus"] = [
                    {"text": "&File", "items": [{"text": "&About...", "name": "mnuAbout", "shortcut": "F1"},
                                                {"text": "-"},
                                                {"text": "E&xit", "name": "mnuExit", "shortcut": "Alt+X"}]}]
        s.save(scr)
    project = Project(folder, name, language_for(kind), [], Path(main).stem, [main, "Main.tform"])
    project.extra["dos"] = {"kind": kind, "main": main, "exe": dos_name(name, EXE_NAME),
                            "output": "com" if kind == "asm" else "exe",
                            "compiler": {"quickbasic": "quickbasic", "pascal": "fpc", "c": "openwatcom",
                                         "asm": "jwasm"}.get(target, "freebasic")}
    project.extra["tui"] = {"target": target, "startup": "Main"}
    project.save()
    path, _w = generate(folder, log=lambda *_a: None)
    if sample:
        _sample_code(path, target)
    if not (folder / ".gitignore").exists():
        (folder / ".gitignore").write_text("_build/\n*.EXE\n*.COM\n*.OBJ\n*.o\nCWSDPMI.EXE\nSCREEN.BIN\n",
                                           encoding="utf-8")
    return project


SAMPLE_CODE = {
    "basic": {"Button1_Click": '  TuiSetText Label1, "You pressed OK!"',
              "Button2_Click": "  TuiQuit",
              "mnuAbout_Click": '  TuiMsgBox "About", "Made with RAD IDE - Text-Mode Designer"',
              "mnuExit_Click": "  TuiQuit"},
    "pascal": {"Button1_Click": "begin\n  TuiSetText(Label1, 'You pressed OK!');\nend;",
               "Button2_Click": "begin\n  TuiQuit;\nend;",
               "mnuAbout_Click": "begin\n  TuiMsgBox('About', 'Made with RAD IDE - Text-Mode Designer');\nend;",
               "mnuExit_Click": "begin\n  TuiQuit;\nend;"},
    "c": {"Button1_Click": '    tui_set_text(Label1, "You pressed OK!");',
          "Button2_Click": "    tui_quit();",
          "mnuAbout_Click": '    tui_msgbox("About", "Made with RAD IDE - Text-Mode Designer");',
          "mnuExit_Click": "    tui_quit();"},
    "asm": {"Button1_Click": "    mov bx, Label1\n    mov si, offset msg_ok\n    call tui_set_text",
            "Button2_Click": "    call tui_quit",
            "mnuAbout_Click": "    mov si, offset msg_about\n    mov di, offset msg_title\n    call tui_msgbox",
            "mnuExit_Click": "    call tui_quit",
            "declarations": "msg_ok    db 'You pressed OK!', 0\nmsg_about db 'Made with RAD IDE - Text-Mode Designer', 0\n"
                            "msg_title db 'About', 0"},
}


def _sample_code(path: Path, target: str) -> None:
    """Fill the sample's handlers (OK changes the label, Cancel / File > Exit quit, File > About shows a box)."""
    from .codegen.common import BEGIN, END
    code = SAMPLE_CODE[TARGETS[target][2]]
    lines = read_dos_text(path).split("\n")
    out = []
    key = None
    for ln in lines:
        m = BEGIN.match(ln)
        if m and m.group(1) in code:
            key = m.group(1)
            out.append(ln)
            out.extend(code[key].split("\n"))
            continue
        if key is not None:
            if END.match(ln):
                key = None
                out.append(ln)
            continue
        out.append(ln)
    write_dos_text(path, "\n".join(out))


# ------------------------------------------------------------------ build / run
def _project(folder: Path):
    from ....model import Project
    return Project.load(folder)


def build(folder, log=print, download: bool = True) -> tuple[bool, Path | None]:
    """Generate, then build the DOS program. Returns (ok, program path)."""
    folder = Path(folder)
    try:
        generate(folder, log)
    except (ValueError, OSError) as e:
        log(f"error: {e}")
        return False, None
    project = _project(folder)
    from ...dos.build import Builder, output_name, settings_for
    s = settings_for(project)
    if s["kind"] == "asm" and s.get("compiler") == "jwasm":
        from ...dos import toolchain
        if not toolchain.find("jwasm"):
            return build_asm_builtin(folder, s, log)
    b = Builder(folder, project=project, log=log, download=download)
    ok = b.build()
    return ok, (folder / output_name(s)) if ok else None


def build_asm_builtin(folder: Path, s: dict, log=print) -> tuple[bool, Path | None]:
    """The asm target with RAD IDE's own 8086 assembler -> .COM (no toolchain needed)."""
    from ....emu8086.assembler import assemble
    from ....emu8086.dosexe import com_image
    main = folder / s["main"]
    prog = assemble(read_dos_text(main), main.name)
    if not prog.ok:
        for e in prog.errors:
            log(f"{main.name}({getattr(e, 'line', 0)}): error: {e}")
        return False, None
    out = folder / (s["exe"] + ".COM")
    out.write_bytes(com_image(prog))
    log(f"RAD IDE 8086 assembler: {main.name} -> {out.name} ({out.stat().st_size} bytes)")
    return True, out


def keys_com(keys: list[int]) -> bytes:
    """A tiny .COM that puts *keys* (Sim key codes) into the BIOS keyboard buffer (at most 15)."""
    from ....emu8086.assembler import assemble
    from ....emu8086.dosexe import com_image
    from .sim import key_bios
    lines = ["org 100h"]
    for k in keys[:15]:
        scan, asc = key_bios(k)
        lines += ["    mov ah, 05h", f"    mov cx, {(scan << 8) | asc}", "    int 16h"]
    lines += ["    mov ax, 4C00h", "    int 21h"]
    prog = assemble("\n".join(lines) + "\n", "TUIKEYS.ASM")
    if not prog.ok:
        raise ValueError(f"key stuffer: {prog.errors[:3]}")
    return com_image(prog)


def capture(folder, program: str, keys: list[int] | None = None, timeout: int = 60, cols: int = 80,
            log=print) -> CellBuffer | None:
    """Run *program* (in *folder*) in DOSBox-X without a window; with *keys* they are typed first. Returns the
    screen the program dumped (SCREEN.BIN) or None."""
    from ...dos import dosbox
    folder = Path(folder)
    out = folder / "SCREEN.BIN"
    try:
        out.unlink()
    except OSError:
        pass
    cmds = []
    if keys:
        (folder / "_build").mkdir(exist_ok=True)
        (folder / "_build" / "TUIKEYS.COM").write_bytes(keys_com(keys))
        cmds.append("C:\\_build\\TUIKEYS.COM")
        cmds.append(f"{program} /DUMPKEYS")
    else:
        cmds.append(f"{program} /DUMP")
    run = dosbox.DosRun(mounts=[("C", folder)], commands=cmds, cycles="max", sound=False)
    (folder / "_build").mkdir(exist_ok=True)
    dosbox.run_headless(run, folder / "_build", timeout, name="capture.conf", log=log)
    if not out.is_file():
        return None
    return CellBuffer.from_bin(out.read_bytes(), cols)


def run(folder, log=print) -> int:
    """Build and start the program in a DOSBox-X window (the IDE's Run)."""
    folder = Path(folder)
    ok, exe = build(folder, log)
    if not ok or exe is None:
        return 1
    from ...dos import dosbox
    from ...dos.build import settings_for
    s = settings_for(_project(folder))
    r = dosbox.DosRun(mounts=[("C", folder)], commands=[exe.name], cycles=s.get("cycles", "max"),
                      machine=s.get("machine", "svga_s3"), keep_window=False,
                      title=f"{_project(folder).name} - RAD IDE")
    p = dosbox.launch(r, folder / "_build", log=log)
    try:
        return p.wait()
    except KeyboardInterrupt:
        p.terminate()
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, folder = argv[0], Path(argv[1])
    out = lambda t: print(t, flush=True)  # noqa: E731
    if cmd == "generate":
        generate(folder, out)
        return 0
    if cmd == "build":
        return 0 if build(folder, out)[0] else 1
    if cmd == "run":
        return run(folder, out)
    if cmd == "capture":
        ok, exe = build(folder, out)
        if not ok or exe is None:
            return 1
        b = capture(folder, exe.name, log=out)
        print(b.plain_text() if b else "no screen", flush=True)
        return 0 if b else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
