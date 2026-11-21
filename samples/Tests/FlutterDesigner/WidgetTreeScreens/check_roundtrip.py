"""Regression check for the Flutter designer model (docs/FLUTTER_DESIGNER.md).

For every screens/*.fscreen.json of this sample: generate the Dart code, import it back with the
package:analyzer based importer and compare the trees (ids aside). Run from the repository root:

    python samples/Tests/FlutterDesigner/WidgetTreeScreens/check_roundtrip.py

Then `flutter analyze` and `flutter test` in this folder check the generated code (5 screens build and animate).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import codegen as CG, importer as I, model as M  # noqa: E402


def norm(v):
    if isinstance(v, dict):
        return {k: (re.sub(r",\s*([)\]}])", r"\1", re.sub(r"\s+", "", x)) if k in ("code", "$code") and
                    isinstance(x, str) else norm(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def main() -> int:
    bad = 0
    for path in sorted((HERE / "screens").glob("*" + M.SCREEN_EXT)):
        scr = M.Screen.load(path)
        issues = [i for i in scr.validate() if i.level == "error"]
        gen = CG.generate_screen(scr, None)
        res = I.import_dart(gen.designer_code)
        back = next((s for s in res.screens if s["name"] == scr.name), None)
        same = back is not None and norm(M.strip_ids(scr.to_dict()["tree"])) == \
            norm(M.strip_ids(M.Screen(back).to_dict()["tree"]))
        stats = res.stats.get(scr.name, {})
        print(f"{scr.name:10} {'OK  ' if same and not issues else 'FAIL'} widgets={stats.get('exact')} "
              f"code_nodes={len(stats.get('code_nodes', []))} errors={len(issues)}")
        if not same or issues:
            bad += 1
            print(json.dumps([str(i) for i in issues], indent=1))
    print("failures:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
