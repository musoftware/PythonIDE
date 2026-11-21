"""Run every Text-Mode Designer test (each in its own process).

    python samples/Tests/Retro/DesignTextMode/run_all.py [--no-download] [--skip-ui]
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = ["test_core.py", "test_dosbox.py", "test_mouse.py", "test_ui.py"]


def main() -> int:
    extra = [a for a in sys.argv[1:] if a == "--no-download"]
    tests = [t for t in TESTS if not ("--skip-ui" in sys.argv and t == "test_ui.py")]
    failed = []
    for t in tests:
        print(f"===== {t}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / t)] + (extra if t == "test_dosbox.py" else []))
        if r.returncode != 0:
            failed.append(t)
    print(f"===== {len(tests) - len(failed)}/{len(tests)} test files passed; FAILED: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
