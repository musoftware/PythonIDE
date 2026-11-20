"""Run VB / BASIC unit tests of a RAD IDE project (Test Explorer convention).

    python -m radide.testing.vbtest <project-folder> <out.json> [Module.bas::TestName ...]

Convention (VB-easy): a code module whose file name starts or ends with "Test" (TestMath.bas,
MathTests.bas) holds public Subs named Test... (Sub TestAdd()). A test fails when it raises a run-time
error or an assertion fails. Assertions available inside test modules:
    Assert condition [, message]        AssertEqual expected, actual [, message]
    AssertTrue condition [, message]    AssertFalse condition [, message]    Fail message
The project's other (non-form) modules are loaded too, so tests can call their functions.
"""
from __future__ import annotations

import io
import json
import sys
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path


def is_test_module(name: str) -> bool:
    stem = Path(name).stem.lower()
    return Path(name).suffix.lower() == ".bas" and (stem.startswith("test") or stem.endswith("test")
                                                     or stem.endswith("tests"))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0]).resolve()
    out = argv[1]
    wanted = set(argv[2:])
    from ..runtimes.vbinterp import Interpreter, VBRuntimeError, to_bool, to_str, vb_compare
    from ..runtimes.vbparse import VBSyntaxError, parse_module

    class AssertFailed(VBRuntimeError):
        pass

    def _fail(msg="Assertion failed"):
        raise AssertFailed(9001, to_str(msg) or "Assertion failed")

    def a_true(cond, msg=""):
        if not to_bool(cond):
            _fail(msg or "Assert failed: condition is False")
        return 0

    def a_false(cond, msg=""):
        if to_bool(cond):
            _fail(msg or "AssertFalse failed: condition is True")
        return 0

    def a_equal(expected, actual, msg=""):
        try:
            same = vb_compare(expected, actual) == 0
        except Exception:  # noqa: BLE001
            same = expected == actual
        if not same:
            _fail((to_str(msg) + ": " if msg else "") + f"expected <{to_str(expected)}> but was <{to_str(actual)}>")
        return 0

    it = Interpreter(host=None)
    it.builtins.update({"assert": a_true, "asserttrue": a_true, "assertfalse": a_false,
                        "assertequal": a_equal, "fail": _fail})
    printed = io.StringIO()
    it.output = lambda s: printed.write(to_str(s) + "\n")
    results = []
    files = sorted(p for p in folder.glob("*.bas") if p.is_file())
    tests = []
    for path in files:
        try:
            src = path.read_text(encoding="utf-8-sig", errors="replace")
            mod = parse_module(src, path.stem, path.name)
        except VBSyntaxError as e:
            if is_test_module(path.name):
                results.append({"id": f"{path.name}::<load>", "state": "error", "duration": 0.0,
                                "message": f"{path.name}({e.line}): Syntax error: {e.msg}", "output": "",
                                "file": str(path), "line": e.line})
            continue
        try:
            st = it.load_module(mod, False)
        except Exception as e:  # noqa: BLE001 - a module whose declarations fail
            results.append({"id": f"{path.name}::<load>", "state": "error", "duration": 0.0,
                            "message": str(e), "output": "", "file": str(path), "line": 1})
            continue
        if is_test_module(path.name):
            for proc in mod.procs.values():
                disp = proc.display or proc.name
                if proc.kind == "sub" and disp.lower().startswith("test") and not proc.params:
                    tests.append((path, st, proc, disp))
    for path, st, proc, disp in tests:
        tid = f"{path.name}::{disp}"
        if wanted and tid not in wanted:
            continue
        printed.seek(0)
        printed.truncate()
        t0 = time.perf_counter()
        state, msg = "passed", ""
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                it.call_proc(st, proc, [])
        except AssertFailed as e:
            state, msg = "failed", getattr(e, "description", "") or str(e)
        except VBRuntimeError as e:
            state = "failed"
            msg = f"Run-time error {getattr(e, 'number', '')}: {getattr(e, 'description', '') or e}"
            if getattr(e, "line", 0):
                msg += f" (line {e.line})"
        except Exception:  # noqa: BLE001
            state, msg = "error", traceback.format_exc()[-4000:]
        results.append({"id": tid, "state": state, "duration": time.perf_counter() - t0, "message": msg,
                        "output": printed.getvalue() + buf.getvalue(), "file": str(path), "line": proc.line})
    Path(out).write_text(json.dumps({"framework": "vb", "results": results}), encoding="utf-8")
    failed = sum(r["state"] != "passed" for r in results)
    print(f"{len(results)} test(s), {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
