"""DOS blocks of the tutorials (course "dos-programming"): projects, captured runs in DOSBox-X and checks.

Fence info strings (dos-programming/tools/check_lessons.py documents the same format):

* ```` ```dos-qbasic run ```` / ``dos-pascal`` / ``dos-c`` / ``dos-asm`` / ``dos-batch``: a whole program. "Try it"
  writes it into a new DOS project of the matching New Project > DOS type (the "hello" template with its main
  file replaced: MAIN.BAS / MAIN.PAS / MAIN.C / MAIN.ASM / MAIN.BAT), opens it and runs it captured in
  DOSBox-X (``python -m radide.retro.dos.run <folder> --capture``): the program's output appears in the Output
  window. "Check" builds it with the free compiler (FreeBASIC -lang qb, Free Pascal i8086-msdos, Open Watcom,
  JWasm), runs it without a window and looks for the following ```` ```text output ```` lines, in order, in what
  the program printed (standard output) or left on its text screen.
* ``exercise`` blocks are checked against their ``solution``'s expected output (or must build when there is none).
* hidden ``<!-- test: {...} -->``: ``"keys"`` typed for the program (RADKEYS syntax: ``~`` Enter, `````` ` `````` Esc,
  ``_`` Space), ``"com": true`` (.COM output), ``"model"``, ``"mode13": true`` (a 256-colour mode 13h frame must
  be captured), ``"screen": true`` (standard output is not redirected: only the text screen is compared - for
  programs that draw with LOCATE / COLOR), ``"build_only": true``, ``"error_line": N`` (the build must fail with
  an Error List row at line N of the main file), ``"timeout"``.

Without DOSBox-X / the compiler (nothing downloaded yet, offline) the result says what is missing.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

LANGS = ("dos-qbasic", "dos-pascal", "dos-c", "dos-asm", "dos-batch")
KINDS = {"dos-qbasic": "qbasic", "dos-pascal": "pascal", "dos-c": "c", "dos-asm": "asm", "dos-batch": "batch"}
HELLO = {"qbasic": "dosqb_hello", "pascal": "dostp_hello", "c": "dostc_hello", "asm": "dosasm_hello",
         "batch": "dosbat_hello"}
# highlighting: html.py LEXERS (qbasic, pascal, c, tasm for JWasm / MASM syntax, batch)
MISSING_DOSBOX = "DOSBox-X غير مثبت: نزّله من Tools > Retro > Emulators... (أو Tools > DOS Toolchains...)"


def kind_of(block) -> str:
    return KINDS.get(block.lang, "qbasic")


def default_file(block) -> str:
    from ..retro.dos.templates import BY_ID
    return BY_ID[HELLO[kind_of(block)]].main


def reads_stdin(block) -> bool:
    return False                          # input comes from the hidden test's "keys" (typed in DOSBox-X)


# ===================================================================== projects ("جرّبه")
def make_project(block, files: dict[str, str], dest: Path, name: str):
    """A DOS project of the block's type with the block as its main file (other ``#file:`` parts beside it)."""
    from ..languages import get_plugin
    from ..model import Project
    from ..retro.dos import build as B
    from ..retro.dos.templates import BY_ID, write_dos_text
    kind = kind_of(block)
    dest = Path(dest)
    plugin = get_plugin(B.LANGUAGE_OF_KIND[kind])
    plugin.create_new_project(dest, name, HELLO[kind])
    main = BY_ID[HELLO[kind]].main
    for fname, text in files.items():
        write_dos_text(dest / (main if fname == default_file(block) else fname), text)
    spec = block.check_target().spec or {}
    project = Project.load(dest)
    dos = project.extra.setdefault("dos", {})
    if spec.get("com"):
        dos["output"] = "com"
    if spec.get("model"):
        dos["model"] = spec["model"]
    for fname in files:
        if fname != default_file(block) and fname not in project.modules:
            project.modules.append(fname)
    project.save()
    return project


def capture_args(block) -> list[str]:
    """Extra arguments of ``radide.retro.dos.run`` for "Try it": a captured run with the lesson's keys."""
    spec = block.check_target().spec or {}
    args = ["--capture", "--timeout", str(int(spec.get("timeout", 25)))]
    if spec.get("keys"):
        args += ["--keys", str(spec["keys"])]
    return args


# ===================================================================== build + captured run
def build_folder(folder: Path, log: list) -> tuple[bool, dict, str]:
    """Build the DOS project in *folder* -> (ok, settings, main file)."""
    from ..model import Project
    from ..retro.dos import build as B
    project = Project.load(folder)
    ok = B.Builder(folder, project, log=log.append).build()
    s = B.settings_for(Project.load(folder))
    return ok, s, s["main"]


def build_block(block, code: str | None, work: Path, block_files, log: list):
    """Write *block* (or *code*) into a new DOS project in *work* and build it -> (ok, folder, settings, main)."""
    shutil.rmtree(work, ignore_errors=True)
    make_project(block, block_files(block, code), work, "Lesson")
    ok, s, main = build_folder(work, log)
    return ok, Path(work), s, main


def screen_run(run, folder: Path, cmd: str, keys: str, timeout: int) -> dict:
    """Like dosbox.capture_text but without redirecting standard output (a program that draws with LOCATE /
    COLOR / PRINT must write to the screen): the text screen is saved by RADSCR.COM afterwards."""
    from ..retro.dos import dosbox, helpers
    tools = folder / "_build" / "radtools"
    helpers.write_helpers(tools)
    for f in ("_SCREEN.TXT", "_SCR13.RAW"):
        try:
            (folder / f).unlink()
        except OSError:
            pass
    rel = os.path.relpath(tools, folder).replace("/", "\\")
    pre = [f"C:\\{rel}\\RADCAP.COM"] + ([f"C:\\{rel}\\RADKEYS.COM {keys}"] if keys else [])
    run.commands = list(run.commands) + pre + [cmd, f"C:\\{rel}\\RADSCR.COM"]
    rc, timed_out = dosbox.run_headless(run, folder / "_build", timeout, log=lambda *_a: None)
    res = {"rc": rc, "timed_out": timed_out, "stdout": "", "screen": "", "graphics": None}
    try:
        res["screen"] = (folder / "_SCREEN.TXT").read_bytes().decode("cp437", "replace")
    except OSError:
        pass
    if (folder / "_SCR13.RAW").is_file():
        res["graphics"] = str(folder / "_SCR13.RAW")
    return res


def capture(folder: Path, s: dict, spec: dict) -> dict:
    """Run the built program of *folder* headless in DOSBox-X -> {"rc", "timed_out", "stdout", "screen", ...}."""
    from ..retro.dos import build as B
    from ..retro.dos import dosbox
    cmd = ("CALL " + s["main"]) if s["kind"] == "batch" else B.output_name(s)
    run = dosbox.DosRun(mounts=[("C", folder)], path=["Z:\\BIN", "Z:\\DOS"])
    keys, timeout = str(spec.get("keys", "")), int(spec.get("timeout", 25))
    if spec.get("screen"):
        return screen_run(run, folder, cmd, keys, timeout)
    return dosbox.capture_text(run, folder, cmd, keys=keys, timeout=timeout, log=lambda *_a: None)


def lines_of(text: str) -> list[str]:
    rows = [ln.rstrip() for ln in (text or "").replace("\r\r\n", "\n").replace("\r\n", "\n").split("\n")]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def contains(hay: list[str], needle: list[str]) -> bool:
    """*needle* (lines) appears as a run of consecutive lines in *hay*."""
    needle = list(needle)
    while needle and not needle[0]:
        needle.pop(0)
    if not needle:
        return True
    return any(hay[i:i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def shown_output(r: dict) -> str:
    out = "\n".join(lines_of(r.get("stdout", "")))
    scr = "\n".join(x for x in lines_of(r.get("screen", "")) if x.strip())
    if scr and scr.strip() != out.strip():
        out = (out + "\n" if out else "") + "------ الشاشة ------\n" + scr
    return out


def tools_missing(kind: str, download: bool = True) -> str:
    """"" or what is missing to build and run a block of *kind*. Like the IDE's first DOS build, the free
    compiler and DOSBox-X are downloaded (official builds, SHA-256 checked) when *download* and still missing."""
    from ..retro.dos import toolchain
    quiet = lambda *_a: None  # noqa: E731
    comp = toolchain.COMPILER_FOR_KIND.get(kind)
    if comp and not toolchain.ensure_for(comp, log=quiet, download=download):
        try:
            title = toolchain.RELEASES[comp].title
        except Exception:  # noqa: BLE001
            title = comp
        return f"المترجم {title} غير مثبت: Tools > DOS Toolchains... ينزّله"
    try:
        have = toolchain.dosbox_exe(download=download, log=quiet)
    except Exception:  # noqa: BLE001
        have = ""
    return "" if have else MISSING_DOSBOX


def run_and_compare(block, target, folder: Path, s: dict, main: str, ok: bool, log: list,
                    expected: str | None = ...) -> tuple[bool, str, list]:
    """(passed, program output, problems) for a built project (shared with tools/check_lessons.py).
    *expected*: the output to look for (default: the ```text output``` attached to *target*)."""
    from ..retro.dos import build as B
    from ..retro.dos import helpers
    spec = target.spec or {}
    if "error_line" in spec:
        diags = B.read_diagnostics(folder).get("diags", [])
        rows = [d for d in diags if d["severity"] == "Error" and d["file"].upper() == main.upper()
                and d["line"] == spec["error_line"]]
        good = not ok and bool(rows)
        return good, "\n".join(log[-12:]), [] if good else ["كان المتوقع خطأ بناء في السطر %s" % spec["error_line"]]
    if not ok:
        return False, "\n".join(log[-15:]), ["فشل البناء (الأخطاء بالأسفل وفي قائمة الأخطاء)"]
    if spec.get("build_only") or (block.role == "exercise" and target is block):
        return True, "\n".join(log[-6:]), []
    r = capture(folder, s, spec)
    out = shown_output(r)
    if r["timed_out"]:
        return False, out, ["انتهت المهلة: هل ينتظر البرنامج مفاتيح أخرى؟"]
    problems = []
    if spec.get("mode13"):
        st = helpers.mode13_stats(r["graphics"]) if r["graphics"] else {}
        if not st or st.get("nonzero", 0) < 1000:
            problems.append("لم تُلتقط صورة للوضع 13h")
    if expected is ...:
        expected = target.expected
    if expected is not None:
        want = lines_of(expected)
        if not (contains(lines_of(r["stdout"]), want) or contains(lines_of(r["screen"]), want)):
            problems.append("المخرجات لا تطابق المطلوب")
    return not problems, out, problems


# ===================================================================== checks ("تحقق")
def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    target = block.check_target()
    missing = tools_missing(kind_of(block))
    if missing:
        return CheckResult(False, "", target.expected, [missing])
    log: list[str] = []
    if folder:                                       # the learner edits the opened project: check its files
        ok, s, main = build_folder(Path(folder), log)
        where = Path(folder)
    else:
        ok, where, s, main = build_block(block, code, Path(work), block_files, log)
    good, out, problems = run_and_compare(block, target, where, s, main, ok, log)
    note = ""
    if good and target.expected is None:
        note = "نجح البناء." if (target.spec or {}).get("build_only") or block.role == "exercise" \
            else "يعمل البرنامج في DOSBox-X بلا أخطاء."
    return CheckResult(good, out, target.expected, problems, note)


def available() -> dict:
    from ..retro.dos import toolchain
    return {k: bool(toolchain.find(c)) for k, c in toolchain.COMPILER_FOR_KIND.items() if c} | \
        {"dosbox-x": bool(toolchain.dosbox_exe())}


__all__ = ["KINDS", "LANGS", "available", "build_block", "capture", "capture_args", "check",
           "contains", "default_file", "kind_of", "lines_of", "make_project", "reads_stdin", "run_and_compare"]
