"""FeatureMatrix on the VB6 native build (VB6 -> FreeBASIC, rt/vbrt_motion.bi): animations, visual states and
layout variants must play in the published exe itself - no fallback to the bundled VB runtime.

    .venv\\Scripts\\python samples\\Tests\\FeatureMatrix\\check_fm_vb6.py [--keep]

1. fm_vb6.write_project() writes the project (curated copy: FeatureMatrix_VB6/), radide.deploy.build.build()
   publishes it: the result must be the "native" kind (FreeBASIC exe, no Python);
2. fm_drive.drive() checks every feature on the running exe's own window (controls found by their dialog
   control id = 1000 + the id of the generated FreeBASIC Const), then again with RADIDE_REDUCED_MOTION=1.
Only the processes started here are touched."""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["RADIDE_NO_BROWSER"] = "1"

import fm_drive  # noqa: E402
import fm_vb6  # noqa: E402

w = fm_drive.w
user32 = ctypes.windll.user32


def control_ids(gen: Path) -> dict:
    """VB control name -> dialog control id (1000 + the runtime id of the generated Const CTL_Form1_<name>)."""
    src = next(gen.glob("*.bas")).read_text(encoding="utf-8")
    return {m.group(1): 1000 + int(m.group(2)) for m in re.finditer(r"^Const CTL_Form1_(\w+) = (\d+)$", src, re.M)}


def make_find(ids: dict):
    def find(form, names):
        out = {}

        def cb(c, _l):
            cid = user32.GetDlgCtrlID(c)
            for n, i in ids.items():
                if i == cid and n not in out:
                    out[n] = c
            return True
        user32.EnumChildWindows(form, w.WNDENUMPROC(cb), 0)
        return out
    return find


def vb_form_window(pid, _name, timeout=10.0):
    """The VB program's form: its top-level window of class RADVBForm (no radforms.name property)."""
    return w.wait(lambda: next((h for h in w.top_windows(pid) if w.class_name(h) == "RADVBForm"), None), timeout)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    keep = "--keep" in argv
    proj = fm_vb6.write_project(HERE / "FeatureMatrix_VB6")
    work = Path(tempfile.mkdtemp(prefix="radide_fm_vb6_"))
    rep = fm_drive.Report("VB6 native")
    try:
        from radide.deploy import build as B
        from radide.deploy.config import PublishConfig
        cfg = PublishConfig()
        cfg.app_name = "FeatureMatrix_VB6"
        cfg.output_dir = str(work / "out")
        cfg.make_installer = False
        log: list[str] = []
        t = time.time()
        res = B.build(proj, cfg, log=log.append)
        if not rep.ok("published as the native FreeBASIC exe (no vbrun fallback)", res.kind == "native",
                      f"{res.kind}: " + " | ".join(l for l in log if l.startswith("  - ") or "error" in l.lower())[:1500]):
            return 1
        print(f"built in {time.time() - t:.1f}s: {res.dist / res.exe}")
        exe = res.dist / res.exe
        files = [p.name.lower() for p in res.dist.rglob("*")]
        rep.ok("no Python in the program folder", not any(f.startswith("python") and f.endswith(".dll") for f in files)
               and "_internal" not in files, files)
        gen = work / "out" / "build" / "native_vb6"
        if not gen.is_dir():
            gen = next((p for p in work.rglob("native_vb6") if p.is_dir()), gen)
        find = make_find(control_ids(gen))
        fm_drive.w.form_window = vb_form_window          # this process only: VB forms have no radforms.name
        fm_drive.drive(exe, rep, vb=True, find=find)
        fm_drive.drive(exe, rep, vb=True, env_extra={"RADIDE_REDUCED_MOTION": "1"}, find=find)
    finally:
        if keep:
            print("work:", work)
        else:
            shutil.rmtree(work, ignore_errors=True)
    ok = sum(1 for r in rep.rows if r[1])
    print(f"\n{ok}/{len(rep.rows)} FeatureMatrix checks passed (VB6 native)")
    for f, good, d in rep.rows:
        if not good:
            print(f"  FAIL {f}  {d}")
    return 0 if ok == len(rep.rows) else 1


if __name__ == "__main__":
    sys.exit(main())
