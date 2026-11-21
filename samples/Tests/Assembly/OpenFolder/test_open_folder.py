"""Headless tests of the Assembly "integration" part (no IDE window):

* File > Open Folder detection (radide/project_detect.py ``_asm``) of every sample folder here: kind "asm",
  the guessed dialect, open in place, create / not create;
* the in-place adapter (radide/foreign/asm_folder.py): run targets, build steps - and a real build + run of the
  NASM, GNU as and FASM folders with the steps the IDE would use (output checked);
* RadASM .rap / WinAsm .wap project files, the foreign-format registry, SASM detection;
* a Visual Studio .vcxproj with MASM items (radide/foreign/msbuild.py lists them; the MinGW fallback note);
* the Windows "Open with" list (radide/shell_integration.py) has the assembly extensions;
* the exe importer's NASM listing (radide/importers/exe/asm_listing.py) of a small gcc program, assembled
  again with NASM (object file).

    python samples/Tests/Assembly/OpenFolder/test_open_folder.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import project_detect as PD  # noqa: E402
from radide.foreign import asm_folder as AF  # noqa: E402

results: dict[str, bool] = {}


def check(name: str, ok: bool, detail: str = "") -> None:
    results[name] = bool(ok)
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"  ({detail})" if detail else ""))


def run_steps(steps) -> tuple[int, str]:
    out = ""
    for s in steps:
        env = dict(os.environ)
        env.update(s.env or {})
        r = subprocess.run([str(a) for a in s.argv], cwd=s.cwd, env=env, capture_output=True)
        out += (r.stdout + r.stderr).decode("utf-8", "replace")
        if r.returncode:
            return r.returncode, out
    return 0, out


# ---------------------------------------------------------------- detection
EXPECT = {"NasmLoose": "nasm", "Nasm32Loose": "nasm", "Gas32Loose": "gas", "MasmLoose": "masm", "FasmLoose": "fasm", "GasLoose": "gas", "Dos8086Loose": "8086",
          "SasmProgram": "nasm", "RadAsmProject": "nasm", "WinAsmProject": "masm"}
for folder, dialect in EXPECT.items():
    det = PD.detect(HERE / folder)
    c = next((x for x in det.candidates() if x.kind == "asm"), None)
    ok = c is not None and c.extra.get("_asm_dialect") == dialect and c.inplace == "loose" and \
        c.default_action == "inplace" and c.confidence >= PD.CONFIDENT
    check(f"detect {folder} -> {dialect}", ok, c.title if c else det.summary())
    if folder in ("RadAsmProject", "WinAsmProject"):
        check(f"detect {folder}: project file", c is not None and c.inplace_file.endswith((".rap", ".wap")),
              c.inplace_file if c else "")
    if folder == "NasmLoose":
        check("detect NasmLoose: can create an asm-nasm project", c is not None and c.can_create and
              c.language == "asm-nasm" and c.radproj().get("asm", {}).get("entry") == "main")
    if folder == "Dos8086Loose":
        check("detect Dos8086Loose: emu8086 project can be created", c is not None and c.language == "emu8086"
              and c.can_create)

# a C project with one .s helper stays a C project
tmp = Path(tempfile.mkdtemp(prefix="asmdetect-"))
try:
    (tmp / "main.c").write_text("int helper(void);\nint main(void){return helper();}\n", encoding="utf-8")
    (tmp / "util.c").write_text("int x;\n", encoding="utf-8")
    (tmp / "helper.s").write_text("    .globl helper\nhelper:\n    xorl %eax, %eax\n    ret\n", encoding="utf-8")
    det = PD.detect(tmp)
    asm = next((x for x in det.candidates() if x.kind == "asm"), None)
    check("C folder with a .s helper is not taken over", asm is None or asm.confidence < PD.CONFIDENT,
          det.summary())
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- dialect guessing
SNIPPETS = {
    "nasm": "section .text\nglobal main\nmain:\n    mov rax, 1\n    ret\n",
    "masm": ".code\nmain PROC\n    mov rax, 1\n    ret\nmain ENDP\nEND\n",
    "fasm": "format PE64 console\nentry start\nsection '.text' code readable executable\nstart:\n    ret\n",
    "gas": "    .globl main\n    .text\nmain:\n    movq $1, %rax\n    ret\n",
    "8086": "org 100h\nmov ah, 9\nlea dx, msg\nint 21h\nret\nmsg db 'x$'\n",
}
for want, text in SNIPPETS.items():
    got = AF.guess_dialect(text)
    check(f"guess_dialect {want}", got == want, got)
check("guess_bits", AF.guess_bits(SNIPPETS["nasm"]) == 64 and AF.guess_bits("bits 32\nmov eax, 1\n") == 32 and
      AF.guess_bits(SNIPPETS["8086"], "8086") == 16)
check("entry points", AF.entry_point(SNIPPETS["masm"], "masm") == "main" and
      AF.entry_point(SNIPPETS["fasm"], "fasm") == "start" and AF.entry_point(SNIPPETS["gas"], "gas") == "main")

# ---------------------------------------------------------------- adapter: targets, build, run
for folder, expect_out in (("NasmLoose", "NASM loose folder: 6 * 7 = 42"), ("GasLoose", "GNU as loose folder: 2026"),
                           ("FasmLoose", "FASM loose folder"), ("MasmLoose", "MASM loose folder: 42"),
                           ("Nasm32Loose", "NASM 32-bit loose folder: 6 * 7 = 42"),      # ld -m i386pe, not gcc -m32
                           ("Gas32Loose", "GNU as 32-bit loose folder: 2026")):
    a = AF.AsmFolderAdapter(HERE / folder)
    a.scan()
    t = a.targets[0] if a.targets else None
    if t is None:
        check(f"adapter {folder}: target", False)
        continue
    tool = {"NasmLoose": "nasm", "GasLoose": "gcc", "FasmLoose": "fasm", "MasmLoose": "ml64", "Nasm32Loose": "nasm",
            "Gas32Loose": "ld"}[folder]
    if folder.endswith("32Loose"):
        check(f"adapter {folder}: links with ld -m i386pe",
              any("i386pe" in [str(x) for x in s.argv] for s in a.build_steps(t, False)) and
              not any("-m32" in [str(x) for x in s.argv] for s in a.build_steps(t, False)))
    if not (AF.find_masm(64)[0] if tool == "ml64" else AF.find_tool(tool)):
        print(f"skip {folder}: {tool} not installed")
        continue
    code, out = run_steps(a.build_steps(t, False))
    if code:
        check(f"adapter {folder}: build", False, out.strip()[:400])
        continue
    run = a.run_step(t, False)
    r = subprocess.run([str(x) for x in run.argv], cwd=run.cwd, capture_output=True, timeout=30)
    got = r.stdout.decode("utf-8", "replace").strip()
    check(f"adapter {folder}: build + run", got == expect_out, got)
    check(f"adapter {folder}: nothing written into the folder",
          not any(p.suffix.lower() in (".obj", ".exe", ".o", ".lnk", ".pdb", ".ilk", ".lst")
                  for p in (HERE / folder).iterdir()))

a = AF.AsmFolderAdapter(HERE / "NasmLoose")
a.scan()
check("adapter NasmLoose: .inc is a module, not a target", "macros.inc" in a.modules and len(a.targets) == 1)
a = AF.AsmFolderAdapter(HERE / "Dos8086Loose")
a.scan()
check("adapter Dos8086Loose: emulator target", bool(a.targets) and a.targets[0].kind == "emu" and
      a.base_language == "emu8086")
a = AF.AsmFolderAdapter(HERE / "MasmLoose")
a.scan()
steps = a.build_steps(a.targets[0], False)
script = Path(str(steps[0].argv[-1])) if steps else None
check("adapter MasmLoose: ml64 step (Visual Studio)", script is not None and script.suffix == ".bat" and
      "ml64" in script.read_text(errors="replace"),
      "ml64 found" if AF.find_masm(64)[0] else "ml64 not installed: the step names ml64 and the log says so")

# ---------------------------------------------------------------- other IDEs' projects
rap = AF.read_ide_project(HERE / "RadAsmProject" / "Hello.rap")
check("RadASM .rap", rap["main"] == "Hello.asm" and rap["assembler"] == "nasm" and "Readme.txt" in rap["files"], rap)
wap = AF.read_ide_project(HERE / "WinAsmProject" / "Hello.wap")
check("WinAsm .wap", wap["main"] == "Hello.asm" and wap["assembler"] == "masm", wap)
a = AF.AsmFolderAdapter(HERE / "RadAsmProject" / "Hello.rap")
a.scan()
check("adapter RadASM: name, modules, target", a.name == "Hello" and a.modules == ["Hello.asm"] and
      a.targets and a.targets[0].data["file"] == "Hello.asm", f"{a.name} {a.modules}")
from radide.features.foreign_projects import find_format, probe_folder  # noqa: E402
check("foreign formats .rap / .wap registered", getattr(find_format("x.rap"), "name", "") == "radasm" and
      getattr(find_format("x.wap"), "name", "") == "winasm")
hit = probe_folder(HERE / "WinAsmProject")
check("folder probe finds Hello.wap", hit is not None and hit[1].name == "Hello.wap")
info = AF.scan_folder(HERE / "SasmProgram")
check("SASM program: CMAIN entry, sasm flag", info.programs and info.programs[0].sasm and
      info.programs[0].entry == "main")

# ---------------------------------------------------------------- Visual Studio + MASM
from radide.foreign import msbuild as MB  # noqa: E402
ms = MB.MSBuildProject.load(HERE / "VsMasmProject" / "VsMasmProject.vcxproj") \
    if hasattr(MB.MSBuildProject, "load") else MB.MSBuildProject(HERE / "VsMasmProject" / "VsMasmProject.vcxproj")
kinds = {f.rel: f.kind for f in ms.files()}
check("vcxproj: MASM item listed", kinds.get("add3.asm") == "MASM" and kinds.get("main.cpp") == "ClCompile", kinds)
det = PD.detect(HERE / "VsMasmProject")
check("vcxproj with MASM detected as Visual Studio C++ / MASM", any("MASM" in c.title for c in det.candidates()),
      det.summary())

# ---------------------------------------------------------------- shell integration
from radide import shell_integration as SI  # noqa: E402
check("Open with: .asm .s .nasm .inc .rap .wap", {".asm", ".s", ".nasm", ".inc", ".rap", ".wap"} <=
      set(SI.OPEN_WITH_BASE))

# ---------------------------------------------------------------- exe -> NASM listing
gcc = AF.find_tool("gcc")
nasm = AF.find_tool("nasm")
if gcc and nasm:
    work = Path(tempfile.mkdtemp(prefix="asmlisting-"))
    try:
        (work / "h.c").write_text('#include <stdio.h>\nint twice(int x){return x*2;}\n'
                                  'int main(void){printf("%d\\n", twice(21)); return 0;}\n', encoding="utf-8")
        env = dict(os.environ, PATH=str(Path(gcc).parent) + os.pathsep + os.environ.get("PATH", ""))
        subprocess.run([gcc, "-O1", "h.c", "-o", "h.exe"], cwd=work, env=env, check=True)
        from radide.importers.exe.asm_listing import export_project  # noqa: E402
        lst = export_project(work / "h.exe", work / "listing")
        text = lst.read_text(encoding="utf-8")
        check("listing: functions, externs, addresses", "main:" in text and "twice:" in text and "extern " in text
              and "; 14000" in text)
        r = subprocess.run([nasm, "-f", "win64", "-o", str(work / "l.obj"), str(lst)], capture_output=True)
        errs = [ln for ln in (r.stdout + r.stderr).decode("utf-8", "replace").splitlines() if ": error:" in ln]
        check("listing assembles again with NASM", r.returncode == 0, "; ".join(errs[:5]))
        det = PD.detect(work / "listing")
        check("listing folder opens as an Assembly folder",
              any(c.kind == "asm" for c in det.candidates()), det.summary())
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    print("skip listing: gcc / nasm not installed")

failed = [k for k, v in results.items() if not v]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
