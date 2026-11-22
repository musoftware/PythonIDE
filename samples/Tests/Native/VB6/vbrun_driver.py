"""Replays a scenario (scenarios.py) on the IDE's VB runtime (radide/runtimes/vbrun.py, Tk) in this process and
prints {"debug": [...], "reads": [...]} as JSON - the reference the native exe is compared with.

    python vbrun_driver.py <project folder> <scenario name>
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE))

from scenarios import SCENARIOS  # noqa: E402

from radide.runtimes import vbrun  # noqa: E402
from radide.runtimes.vbinterp import to_str  # noqa: E402


def main():
    folder, name = Path(sys.argv[1]), sys.argv[2]
    steps = json.loads(sys.argv[3]) if len(sys.argv) > 3 else SCENARIOS[name]
    debug, reads = [], []
    rt = vbrun.Runtime(folder)
    rt.interp.output = debug.append
    rt.end = lambda: None                       # never os._exit while the test runs
    rt.load()
    start = rt.forms[rt.project.startup.lower()]
    start.load()
    start.vb_call("show", [])

    def pump(sec):
        t = time.time()
        while time.time() - t < sec:
            rt.root.update()
            time.sleep(0.01)

    def target(spec):
        vf = start
        if "." in spec:
            fn, spec = spec.split(".", 1)
            vf = rt.forms[fn.lower()]
            vf.load()
        m = re.fullmatch(r"(\w+)\((\d+)\)", spec)
        if m:
            arr = vf.controls[m.group(1).lower()]
            return vf, arr.items[int(m.group(2))], m.group(1), int(m.group(2))
        if spec.lower() in rt.forms:
            return rt.forms[spec.lower()], rt.forms[spec.lower()], spec, None
        return vf, vf.controls[spec.lower()], spec, None

    def run(steps):
        for st in steps:
            kind = st[0]
            if kind == "wait":
                pump(st[1])
                continue
            if kind == "menu":
                rt.run_handler(start, f"{st[1]}_Click", "Click")
                pump(0.05)
                continue
            vf, c, nm, idx = target(st[1])
            if kind == "set":
                c.vb_set("text", st[2])
            elif kind == "click":
                t = getattr(c, "type", "")
                if t == "CheckBox":
                    c.vb_set("value", 0 if c.vb_get("value") else 1)
                elif t == "RadioButton":
                    c.vb_set("value", True)
                elif idx is not None:
                    rt.run_handler(vf, f"{nm}_Click", "Click", index=idx)
                else:
                    rt.fire(vf, c.name, "Click")
            elif kind == "select":
                c.vb_set("listindex", st[2])
            elif kind == "read":
                if isinstance(c, vbrun.VBForm):
                    reads.append(to_str(c.vb_get("caption")))
                elif getattr(c, "type", "") == "ListBox":
                    n = int(c.vb_get("listcount"))
                    reads.append("|".join(to_str(c.vb_call("list", [i])) for i in range(n)))
                elif getattr(c, "type", "") in ("TextBox", "ComboBox", "StatusBar"):
                    reads.append(to_str(c.vb_get("simpletext" if c.type == "StatusBar" else "text")))
                else:
                    reads.append(to_str(c.vb_get("caption")))
            elif kind == "modal":
                rt.root.after(500, lambda sub=st[2]: run(sub))
                rt.fire(vf, c.name, "Click")
            pump(0.05)

    pump(0.3)
    run(steps)
    print(json.dumps({"debug": debug, "reads": reads}, ensure_ascii=False))


if __name__ == "__main__":
    main()
