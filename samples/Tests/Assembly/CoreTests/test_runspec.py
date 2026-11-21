"""Ctrl+F5 path: plugin.run_spec -> radide.runtimes.bridge --build 'python -m radide.asm.build' -- _radapp.exe"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))      # the RAD IDE folder
from radide.languages import get_plugin
from radide.model import Project

ok_all = True
for folder in map(Path, sys.argv[1:]):
    project = Project.load(folder)
    plugin = get_plugin(project.language)
    spec = plugin.run_spec(folder, project.startup, "")
    r = subprocess.run([spec.program] + spec.args, cwd=spec.cwd, env=spec.env, input="5\n", capture_output=True,
                       text=True, timeout=120)
    out = r.stdout + r.stderr
    ok = r.returncode == 0 and "Build succeeded" in out
    ok_all &= ok
    print(f"=== {folder.name} rc={r.returncode} {'OK' if ok else 'FAIL'}")
    print("\n".join(l for l in out.splitlines() if not l.startswith(">"))[-800:])
print("RESULT", "OK" if ok_all else "FAIL")
