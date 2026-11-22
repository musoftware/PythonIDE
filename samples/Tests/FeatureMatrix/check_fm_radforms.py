"""FeatureMatrix on every radforms native family: C, C++, Fortran, Rust, Go, Lua, JavaScript (Node.js SEA).

    .venv\\Scripts\\python samples/Tests/FeatureMatrix/check_fm_radforms.py [c cpp fortran rust go lua js] [--scratch DIR]

For each language: fm_project.write_project() -> the builder's check() has no reasons -> build.build() must
give the native kind (no bridge fallback) -> fm_drive.drive() on the running exe (animations, visual states,
layout variants) + a reduced-motion run. A missing toolchain is reported as SKIP (not a failure).
Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO), str(HERE), str(HERE.parent / "Native")]
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import fm_drive  # noqa: E402
import fm_project  # noqa: E402
from radide.deploy import build  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.deploy.native import builder_for  # noqa: E402
from radide.model import Project  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SCRATCH = Path(sys.argv[sys.argv.index("--scratch") + 1]) if "--scratch" in sys.argv else \
    Path(tempfile.mkdtemp(prefix="radide_fm_rf_"))
if "--scratch" in sys.argv:
    args = [a for a in args if a != str(SCRATCH)]
LANGS = args or list(fm_project.USER)
totals: dict[str, tuple[int, int]] = {}
fails = 0


def run(key: str):
    global fails
    rep = fm_drive.Report(key)
    src = fm_project.write_project(key, SCRATCH / "proj" / key)
    project = Project.load(src)
    mod = builder_for(project.language)
    reasons = mod.check(src, project, PublishConfig()) if mod else ["no native builder"]
    tool = [r for r in reasons if "not found" in r.lower() or "install" in r.lower()]
    if tool and len(tool) == len(reasons):
        print(f"SKIP [{key}] toolchain missing: {tool}", flush=True)
        totals[key] = (0, 0)
        return
    rep.ok("check(): no fallback reasons", not reasons, reasons)
    out = SCRATCH / "pub" / key
    shutil.rmtree(out, ignore_errors=True)
    log: list[str] = []
    try:
        res = build.build(src, PublishConfig(app_name=f"FM{key}", output_dir=str(out)), log=log.append)
    except Exception as e:  # noqa: BLE001
        rep.ok("build", False, f"{e} " + " | ".join(log[-6:]))
        res = None
    if res is not None and rep.ok("native kind (no fallback)", res.kind == "native" and not res.python_based,
                                  res.kind + " | " + " | ".join(x for x in log if "fall" in x.lower())[:500]):
        exe = res.dist / res.exe
        fm_drive.drive(exe, rep)
        fm_drive.drive(exe, rep, env_extra={"RADIDE_REDUCED_MOTION": "1"})
    n_ok = sum(1 for r in rep.rows if r[1])
    totals[key] = (n_ok, len(rep.rows))
    fails += len(rep.rows) - n_ok


for k in LANGS:
    run(k)
print("\nFeatureMatrix radforms:", ", ".join(f"{k} {a}/{b}" if b else f"{k} SKIP" for k, (a, b) in totals.items()))
sys.exit(fails)
