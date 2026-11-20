"""Plays the exported SkyHopper in Godot headless with tests/autopilot.gd (a scripted player) and prints
what happened: title screen, gates spawning, the score going up, game over, best score, restart.

    python tests/run_autopilot.py [score to reach, default 6]

The project is copied to a temporary folder first (the autopilot is added there as an autoload), so this
sample stays unchanged; the temporary copy and its Godot user data are removed afterwards."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

here = Path(__file__).resolve().parent.parent
godot = shutil.which("godot") or shutil.which("godot4")
if not godot:
    sys.exit("Godot 4 was not found in PATH")
tmp = Path(tempfile.mkdtemp(prefix="skyhopper_autopilot_"))
work = tmp / "game"
shutil.copytree(here, work, ignore=shutil.ignore_patterns(".godot", "tests"))
shutil.copy2(here / "tests" / "autopilot.gd", work / "autopilot.gd")
pg = work / "project.godot"
text = pg.read_text(encoding="utf-8").replace('config/name="', 'config/name="RADTEST_')
pg.write_text(text + '\n[autoload]\n\nAutopilot="*res://autopilot.gd"\n', encoding="utf-8")
name = next(ln.split('"')[1] for ln in text.splitlines() if ln.startswith("config/name="))
env = dict(os.environ, AP_SCORE=sys.argv[1] if len(sys.argv) > 1 else "6")
try:
    subprocess.run([godot, "--headless", "--path", str(work), "--import"], capture_output=True, timeout=300)
    r = subprocess.run([godot, "--headless", "--path", str(work)], capture_output=True, text=True, timeout=600,
                       env=env)
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if "AUTOPILOT" in ln or "ERROR" in ln]
    print("\n".join(lines))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    appdata = os.environ.get("APPDATA")
    if appdata:
        shutil.rmtree(Path(appdata) / "Godot" / "app_userdata" / name, ignore_errors=True)
