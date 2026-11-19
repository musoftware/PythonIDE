"""RAD Hub worker for VB6/BASIC modules: serves the Subs/Functions of one .bas file.

    python -u vbworker.py <Module.bas>          (cwd = the project folder, PYTHONPATH = IDE root)

Runs on the IDE's VB interpreter (radide.runtimes.vbinterp). MsgBox output goes to stderr
(a worker has no window). Arrays come back as JSON lists, keyed Collections as objects.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDE_ROOT = HERE.parent.parent.parent.parent
sys.path.insert(0, str(HERE.parent / "python"))
if str(IDE_ROOT) not in sys.path:
    sys.path.insert(1, str(IDE_ROOT))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stderr.write("usage: vbworker.py <Module.bas>\n")
        return 2
    import radcall
    from radide.runtimes import vbinterp
    from radide.runtimes.vbparse import VBSyntaxError, parse_module

    path = Path(argv[0])
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    src = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        mod = parse_module(src, path.stem, path.name)
    except VBSyntaxError as e:
        sys.stderr.write(f"{path.name}({e.line}): Syntax error: {e.msg}\n")
        return 1
    it = vbinterp.Interpreter(host=None)
    it.output = lambda s: (sys.stderr.write(vbinterp.to_str(s) + "\n"), sys.stderr.flush())
    # solution references: <Lib>.ref.bas proxy modules of the folder (Lib.Function -> RadCall)
    from radide.languages._refs import proxy_files
    for ref in proxy_files(path.parent, "*.ref.bas"):
        if ref.resolve() == path.resolve():
            continue
        try:
            rmod = parse_module(ref.read_text(encoding="utf-8-sig", errors="replace"),
                                ref.name[:-len(".ref.bas")], ref.name)
        except VBSyntaxError as e:
            sys.stderr.write(f"{ref.name}({e.line}): Syntax error: {e.msg}\n")
            continue
        rst = it.load_module(rmod, False)
        rst.filename = ref.name
        it.objects.setdefault(rst.name.lower(), vbinterp.ModuleProxy(it, rst))
    st = it.load_module(mod, False)
    st.filename = path.name
    it.objects.setdefault(st.name.lower(), vbinterp.ModuleProxy(it, st))
    procs = {k.split(":")[-1].lower(): p for k, p in mod.procs.items()}

    def dispatch(func: str, args: list):
        proc = procs.get(func.lower())
        if proc is None:
            cell = st.vars.get(func.lower())
            if cell is not None:                  # a public module variable
                return vbinterp.vb_to_json(cell.value)
            raise radcall.RadCallError(f"Sub/Function '{func}' was not found in {path.name}")
        try:
            result = it.call_proc(st, proc, [vbinterp.json_to_vb(a) for a in args])
        except vbinterp.VBRuntimeError as e:
            raise radcall.RadCallError(f"VB runtime error {e.number}: "
                                       f"{e.description}") from None
        except vbinterp.EndProgram:
            raise radcall.RadCallError("End was executed inside a called function") from None
        return vbinterp.vb_to_json(result)

    radcall.run_worker(dispatch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
