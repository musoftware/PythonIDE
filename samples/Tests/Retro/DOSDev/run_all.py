"""Run every DOS development test (toolchains first: they download what the others need)."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = ["test_dos_toolchains.py", "test_dos_intel.py", "test_dos_templates.py", "test_dos_compat.py",
         "test_dos_ide.py"]
failed = []
for t in TESTS:
    print(f"===== {t}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / t)], cwd=str(HERE))
    if r.returncode != 0:
        failed.append(t)
print("FAILED:", failed or "none")
sys.exit(1 if failed else 0)
