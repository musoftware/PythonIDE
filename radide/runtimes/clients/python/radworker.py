"""RAD Hub worker for Python: serves the functions of one module file.

    python -u radworker.py <module_file.py>        (cwd = the project folder)

Requests (stdin): {"id": 7, "func": "add", "args": [2, 3]} -> {"id": 7, "result": 5}.
"func" may be a dotted path inside the module ("Helper.method" for a class/static method).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def load_module(path: Path):
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.append(here)
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stderr.write("usage: radworker.py <module.py>\n")
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from radcall import RadCallError, run_worker

    path = Path(argv[0])
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    real_stdout = sys.stdout
    sys.stdout = sys.stderr            # module-level print() must not reach the protocol
    try:
        mod = load_module(path)
    finally:
        sys.stdout = real_stdout
    lower = {n.lower(): n for n in dir(mod)}

    def dispatch(func: str, args: list):
        obj = mod
        for part in func.split("."):
            if not hasattr(obj, part) and obj is mod and part.lower() in lower:
                part = lower[part.lower()]          # VB/Ring callers are case-insensitive
            if not hasattr(obj, part):
                raise RadCallError(f"function '{func}' was not found in {path.name}")
            obj = getattr(obj, part)
        if not callable(obj):
            return obj                              # a module-level value
        return obj(*args)

    run_worker(dispatch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
