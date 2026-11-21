"""Run the ROM workbench tests:  python samples/Tests/Retro/RomTools/run_all.py"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
failed = []
for name, ok_mark in (("test_rom_core.py", "RESULT OK"), ("test_hex_ui.py", "FAILED: none")):
    print(f"\n######## {name}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / name)], capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    print("\n".join(l for l in out.splitlines() if not l.startswith(("qt.", "js:", "This plugin")))[-4000:])
    if ok_mark not in out or r.returncode != 0:
        failed.append(name)
print("\nALL OK" if not failed else f"\nFAILED: {failed}")
sys.exit(1 if failed else 0)
