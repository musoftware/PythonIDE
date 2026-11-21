"""Run every core Assembly test (templates, GUI Bridge forms of every flavor, class library, FASM / MASM line
tables, F5 in an external console, Ctrl+F5 path, error rows, IDE).

    python samples/Tests/Assembly/CoreTests/run_all.py

Needs the MinGW-w64 toolchain of the C support (gcc / as / ld / gdb); NASM and FASM are downloaded on the first
build; the MASM cases need Visual Studio with the C++ tools. Projects are created under %TEMP%\radide-asm-tests.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.asm.templates import TEMPLATES      # noqa: E402
WORK = Path(tempfile.gettempdir()) / "radide-asm-tests" / "projects"
STEPS = [
    ["test_templates.py"],
    ["test_form_protocol.py", str(WORK / "nasm_forms")],
    ["test_form_bridge.py", str(WORK / "nasm_forms")],
    ["test_form_flavors.py"],
    ["test_class_library.py"],
    ["test_linetables.py"],
    ["test_external_console.py"],
    ["test_runspec.py", str(WORK / "nasm_console_x64"), str(WORK / "fasm_console_x86"), str(WORK / "gas_console_x64")],
    ["test_errors.py"],
    ["test_ide.py"],
]
failed = []
for step in STEPS:
    print(f"\n######## {' '.join(step)}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / step[0])] + step[1:], capture_output=True, text=True,
                       timeout=900)
    out = r.stdout + r.stderr
    print("\n".join(l for l in out.splitlines() if not l.startswith(("qt.", "js:")))[-3000:])
    n = len(TEMPLATES)
    passed = ("RESULT OK" in out) or (step[0] == "test_templates.py" and f"{n} / {n} passed" in out)
    if not passed:
        failed.append(step[0])
print("\nFAILED:", failed if failed else "none")
sys.exit(1 if failed else 0)
