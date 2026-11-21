"""Create, build and run every Assembly template."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests"     # projects are created here

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))      # the RAD IDE folder
from radide.languages import get_plugin
from radide.asm.templates import TEMPLATES
from radide.asm.build import Builder, read_diagnostics

root = WORK / "projects"
only = sys.argv[1:]
results = []
for t in TEMPLATES:
    if only and t.id not in only:
        continue
    folder = root / t.id
    shutil.rmtree(folder, ignore_errors=True)
    plugin = get_plugin(t.plugin)
    project = plugin.create_new_project(folder, "Demo" + t.id.split("_")[0].title(), t.id)
    logs = []
    ok = Builder(folder, log=logs.append).build()
    run_out = ""
    if ok and not t.forms:
        exe = folder / "_radapp.exe"
        argv = plugin.run_command(folder, project) if t.settings.get("output") == "dll" else [str(exe)]
        try:
            r = subprocess.run(argv, input="7\n", capture_output=True, text=True, timeout=30, cwd=folder)
            run_out = (r.stdout + r.stderr).strip().replace("\n", " | ")
            ok = ok and r.returncode == 0
        except subprocess.TimeoutExpired as e:
            run_out = "TIMEOUT (message box?) " + str((e.stdout or b"")[:200])
    results.append((t.id, ok, run_out))
    print(f"=== {t.id}: {'OK' if ok else 'FAIL'}\n    run: {run_out}")
    if not ok:
        print("\n".join(logs))
        print(read_diagnostics(folder))
print(sum(r[1] for r in results), "/", len(results), "passed")
