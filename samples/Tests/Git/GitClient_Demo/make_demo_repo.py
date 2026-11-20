"""Build a throw-away git repository for trying the Git client of RAD IDE.

    python make_demo_repo.py [target folder]        (default: %TEMP%\\RADIDE_GitDemo)

It creates <target>\\Calc (a small Python project, a git repository with authors "Alice" and "Bob",
branches main / feature/mul / docs, a tag) and <target>\\remote.git (a local "server" to push / pull).
Merging feature/mul into main gives a real merge conflict for the 3-way resolver.
Nothing outside <target> is touched; the user / e-mail are set for that repository only.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

V1 = "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n\n\nprint(add(2, 3))\n"
FEATURE = ("def add(a, b):\n    return a + b  # checked\n\n\ndef sub(a, b):\n    return a - b\n\n\n"
           "def mul(a, b):\n    return a * b\n\n\nprint(add(2, 3), mul(2, 3))\n")
MAIN = "def add(a, b):\n    return a + b  # fast\n\n\ndef sub(a, b):\n    return a - b\n\n\nprint('sum =', add(2, 3))\n"


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def author(cwd: Path, name: str):
    git(cwd, "config", "user.name", name)
    git(cwd, "config", "user.email", f"{name.lower()}@example.com")


def main():
    target = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "RADIDE_GitDemo").resolve()
    if target.exists():
        def unlock(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(target, onerror=unlock)
    proj = target / "Calc"
    proj.mkdir(parents=True)
    (proj / "project.radproj").write_text(json.dumps(
        {"name": "Calc", "language": "python-tk", "forms": [], "startup": "", "modules": ["calc.py"]}, indent=2))
    (proj / "calc.py").write_text(V1)
    (proj / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    git(proj, "init", "-b", "main")
    author(proj, "Alice")
    git(proj, "add", "-A")
    git(proj, "commit", "-m", "Initial calculator")
    git(proj, "tag", "-a", "v1.0", "-m", "first version")
    git(proj, "checkout", "-b", "feature/mul")
    (proj / "calc.py").write_text(FEATURE)
    git(proj, "commit", "-am", "Add mul()")
    git(proj, "checkout", "main")
    author(proj, "Bob")
    (proj / "calc.py").write_text(MAIN)
    git(proj, "commit", "-am", "Label the printed sum")
    git(proj, "branch", "docs")
    (proj / "README.txt").write_text("Calc - a demo for the RAD IDE git client\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-m", "Add README")
    git(target, "init", "--bare", "remote.git")
    git(proj, "remote", "add", "origin", str(target / "remote.git"))
    print(f"Demo repository: {proj}\nLocal 'server':  {target / 'remote.git'}\n"
          "Open Calc\\project.radproj in RAD IDE, then follow the README of this sample.")


if __name__ == "__main__":
    main()
