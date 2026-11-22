"""VB6 -> FreeBASIC translator test: every snippet (snippets.py) runs in the IDE's VB interpreter
(radide/runtimes/vbinterp.py) and as a native exe; the Debug.Print output must be the same.

    .venv\\Scripts\\python samples\\Tests\\Native\\VB6\\translator\\test_translator.py [-k name] [--keep]

All snippets go into one project (one module each) so that one fbc run is enough.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from snippets import SNIPPETS  # noqa: E402

from radide.runtimes.vbinterp import Interpreter, VBRuntimeError  # noqa: E402
from radide.runtimes.vbparse import parse_module  # noqa: E402


def run_interp(src: str, cwd: Path, extra: dict | None = None) -> str:
    out: list[str] = []
    it = Interpreter()
    it.output = out.append
    old = os.getcwd()
    os.chdir(cwd)
    try:
        for fn, code in (extra or {}).items():
            it.load_module(parse_module(code, Path(fn).stem, fn))
        st = it.load_module(parse_module(src, "Module1", "Module1.bas"))
        it.call_by_name("Module1", "Main", [])
    except VBRuntimeError as ex:
        out.append(f"<runtime error {ex.number}: {ex.description}>")
    finally:
        os.chdir(old)
    pending = getattr(it, "_pending_print", "")
    if pending:
        out.append(pending)
    return "\n".join(out)


def build_native(selected, work: Path) -> tuple[dict, list[str], Path | None]:
    from radide.deploy.native import vb6_freebasic as N
    from radide.deploy.native.vb6fb import translate_project
    fbc = N.ensure_fbc(print)
    proj = work / "proj"
    shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    modules, main = [], ["Sub Main()"]
    reasons_by = {}
    fb_root = str(Path(fbc).parent)
    for item in selected:
        name, src = item[0], item[1]
        extra = item[2] if len(item) > 2 else {}
        mod = f"M_{name}.bas"
        body = re.sub(r"(?im)^Sub Main\(\)", f"Public Sub Main_{name}()", src)
        # translatable on its own?
        one = work / f"one_{name}"
        shutil.rmtree(one, ignore_errors=True)
        one.mkdir()
        (one / "Module1.bas").write_text(src, encoding="utf-8")
        for fn, code in extra.items():
            (one / fn).write_text(code, encoding="utf-8")
        (one / "project.radproj").write_text(json.dumps({"name": name, "language": "vb-basic", "forms": [],
                                                          "startup": "Sub Main", "modules": [*extra, "Module1.bas"]}))
        tr = translate_project(one, fb_root=fb_root)
        if tr.reasons:
            reasons_by[name] = tr.reasons
            continue
        (proj / mod).write_text(body, encoding="utf-8")
        for fn, code in extra.items():
            (proj / fn).write_text(code, encoding="utf-8")
            modules.append(fn)
        modules.append(mod)
        main.append(f'    Debug.Print "=== {name}"')
        main.append(f"    Main_{name}")
    main.append("End Sub")
    (proj / "Start.bas").write_text("\n".join(main) + "\n", encoding="utf-8")
    (proj / "project.radproj").write_text(json.dumps({"name": "Snippets", "language": "vb-basic", "forms": [],
                                                       "startup": "Sub Main", "modules": ["Start.bas", *modules]}))
    tr = translate_project(proj, fb_root=fb_root)
    if tr.reasons:
        return reasons_by, tr.reasons, None
    gen = work / "gen"
    shutil.rmtree(gen, ignore_errors=True)
    gen.mkdir()
    for bi in N.RT_DIR.glob("*.bi"):
        shutil.copy2(bi, gen / bi.name)
    (gen / "snippets.bas").write_text(tr.source, encoding="utf-8")
    exe = gen / "snippets.exe"
    p = subprocess.run([fbc, "-s", "gui", "-gen", "gcc", "-O", "2", "-Wc", "-Os", "-x", str(exe), "snippets.bas"], cwd=gen,
                       capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        return reasons_by, N.map_errors(p.stdout + p.stderr, gen / "snippets.bas", tr.line_map) or [p.stdout[-2000:]], None
    return reasons_by, [], exe


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    keep = "--keep" in argv
    only = argv[argv.index("-k") + 1] if "-k" in argv else ""
    selected = [it for it in SNIPPETS if only in it[0]]
    work = Path(tempfile.mkdtemp(prefix="radide_vb6fb_"))
    print("work:", work)
    run_dir = work / "run"
    run_dir.mkdir()
    expected = {it[0]: run_interp(it[1], run_dir, it[2] if len(it) > 2 else None) for it in selected}
    reasons_by, errors, exe = build_native(selected, work)
    passed = failed = 0
    for n, r in reasons_by.items():
        print(f"FAIL {n}: not translated: {r}")
        failed += 1
    if errors:
        print("FAIL compile:", *errors, sep="\n  ")
        return 1
    p = subprocess.run([str(exe)], cwd=run_dir, capture_output=True, timeout=60)
    got_all = p.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    chunks = {}
    for part in got_all.split("=== ")[1:]:
        name, _, rest = part.partition("\n")
        chunks[name.strip()] = rest.rstrip("\n")
    for n, *_ in selected:
        if n in reasons_by:
            continue
        want, got = expected[n].rstrip("\n"), chunks.get(n, "<no output>")
        if want == got:
            passed += 1
            print(f"ok   {n}")
        else:
            failed += 1
            print(f"FAIL {n}")
            wl, gl = want.split("\n"), got.split("\n")
            for i in range(max(len(wl), len(gl))):
                a = wl[i] if i < len(wl) else "<none>"
                b = gl[i] if i < len(gl) else "<none>"
                if a != b:
                    print(f"   interp: {a!r}\n   native: {b!r}")
    print(f"\n{passed}/{passed + failed} snippets identical (exe {exe.stat().st_size // 1024} KB)")
    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
