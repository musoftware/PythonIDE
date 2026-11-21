"""The editor intelligence on the source files of every Assembly New Project template (radide/asm/templates.py,
written by the core part): dialect / ABI detection, outline, completions, hover and no exceptions.

Run:  python samples/Tests/Assembly/AsmIntel/tests/test_core_templates.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from radide.asm_intel import engine, index  # noqa: E402

EXPECT = {"asm-nasm": "nasm", "asm-fasm": "fasm", "asm-masm": "masm", "asm-gas": "gas"}


def main() -> int:
    try:
        from radide.asm import templates
    except Exception as e:  # noqa: BLE001 - the core part is not there (yet)
        print(f"SKIP: radide.asm.templates not available ({e})")
        return 0
    failed = 0
    for t in templates.TEMPLATES:
        with tempfile.TemporaryDirectory() as d:
            proj = Path(d)
            (proj / "project.radproj").write_text(json.dumps({"name": "T", "language": t.plugin, "asm": t.settings}),
                                                  encoding="utf-8")
            files = []
            for name, src in t.files:
                f = proj / name.format(name="T")
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(src.replace("{name}", "T"), encoding="utf-8")
                files.append(f)
            for f in files:
                if not index.is_asm_path(f):
                    continue
                text = f.read_text(encoding="utf-8")
                problems = []

                class P:                       # the template's plugin (dialect hint)
                    id = t.plugin
                    asm_dialect = EXPECT.get(t.plugin, "")
                dia = index.detect_dialect(f, text, P())
                if dia != EXPECT.get(t.plugin):
                    problems.append(f"dialect {dia}")
                abi = index.abi_of(text, dia, f)
                arch = (t.settings or {}).get("arch", "x64")
                if (arch == "x86") != (abi == "x86"):
                    problems.append(f"abi {abi} for arch {arch}")
                lines = text.split("\n")
                try:
                    syms = engine.document_symbols(text, f, P())
                    for i, ln in enumerate(lines):
                        if ln.strip() and not ln.strip().startswith((";", "#")):
                            col = len(ln) - len(ln.lstrip())
                            engine.completions(text, i, col, f, P())
                            engine.hover(text, i, col + 1, f, P())
                            engine.calltip(text, i, len(ln), f, P())
                    engine.folding_ranges(text, f, P())
                except Exception as e:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    problems.append(f"exception {e}")
                    syms = []
                if not syms and f.suffix.lower() != ".inc":
                    problems.append("empty outline")
                ok = not problems
                failed += 0 if ok else 1
                print(("PASS " if ok else "FAIL ") + f"{t.id}/{f.name} [{dia}, {abi}, {len(syms)} outline items]"
                      + ("" if ok else "  " + "; ".join(problems)))
    print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
