"""Flutter designer data widgets check. From the repository root:

    python samples/Tests/FlutterDesigner/DataFormsScreens/check_roundtrip.py

For every screens/*.fscreen.json (ListView.builder / GridView.builder item templates, Text.rich / RichText spans,
Form + TextFormField validators + validate: events, RadioGroup, timeline values on number properties through an
AnimatedBuilder, Lottie): validate, generate the Dart code, import it back with the package:analyzer based
importer, compare the trees (ids aside) and generate again (identical code).
Then hand-written Dart: TextStyle shadows, colours with .withValues(alpha:) / .withOpacity / .withAlpha,
MaterialApp(home: ...) inside main(), and the preview helpers (builder expansion, item template values).
`flutter analyze` and `flutter test` in this folder run the generated code (test/data_forms_test.dart).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import codegen as CG, datawidgets as DW, importer as I, model as M  # noqa: E402
from radide.flutterdesign import variants_fd as VF  # noqa: E402

FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def norm(v):
    if isinstance(v, dict):
        return {k: (re.sub(r",\s*([)\]}])", r"\1", re.sub(r"\s+", "", x)) if k in ("code", "$code") and
                    isinstance(x, str) else norm(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def roundtrip(path: Path):
    scr = M.Screen.load(path)
    errs = [str(i) for i in scr.validate()]
    check(not errs, f"{scr.name}: valid {errs[:3]}")
    gen = CG.generate_screen(scr, None)
    check(not gen.warnings, f"{scr.name}: no codegen warnings {gen.warnings[:3]}")
    res = I.import_dart(gen.designer_code, previous=scr.to_dict())
    back = next((s for s in res.screens if s["name"] == scr.name), None)
    check(back is not None, f"{scr.name}: imported")
    if back is None:
        return
    a, b = norm(M.strip_ids(scr.to_dict()["tree"])), norm(M.strip_ids(M.Screen(back).to_dict()["tree"]))
    check(a == b, f"{scr.name}: tree survives Dart -> import")
    if a != b:
        for x, y in zip(json.dumps(a, indent=1).splitlines(), json.dumps(b, indent=1).splitlines()):
            if x != y:
                print("   expected:", x, "\n   imported:", y)
                break
    for k in ("timelines", "state"):
        check(norm(scr.data.get(k)) == norm(back.get(k)), f"{scr.name}: screen {k} survives")
    stats = res.stats.get(scr.name, {})
    designed = {re.sub(r"\s+", " ", c) for n, *_ in scr.walk() for c in DW._code_values(n)}   # item templates
    extra = [c for c in stats.get("code_props", []) if c.split(": ", 1)[-1] not in designed]
    check(not stats.get("code_nodes") and not extra,
          f"{scr.name}: nothing kept as code {stats.get('code_nodes', [])[:2]} {extra[:2]}")
    check(not back.get("code"), f"{scr.name}: no members / prelude kept as code {back.get('code')}")
    gen2 = CG.generate_screen(M.Screen(back), None)
    check(gen2.designer_code == gen.designer_code, f"{scr.name}: regenerated code identical")
    return gen


def codegen_units():
    scr = M.Screen.load(HERE / "screens" / "SignUp.fscreen.json")
    g = CG.generate_screen(scr, None)
    code = g.designer_code
    check("final form1 = GlobalKey<FormState>();" in code, "Form name -> GlobalKey<FormState> field")
    check("key: form1" in code, "Form key wired")
    check("String? checkPhone(String? value);" in code, "custom validator declared with String? return")
    check("custom: checkPhone" in code and "validator: checkPromo" in code, "custom validator wired")
    check("RadRule.regex('^[0-9]{7,15}\\$', '7 to 15 digits')" in code, "regex rule escaped")
    check("if (form1.currentState!.validate())" in code and "onSubmit();" in code, "validate:form1:onSubmit")
    check("() => form1.currentState!.validate()" in code, "validate:form1")
    check("RadioGroup<String>(" in code and "String? rdoPlan = 'free';" in code, "RadioGroup state field")
    check(g.uses_form and "import '../radform.dart';" in code, "radform.dart imported")
    stub = CG.add_missing_handlers(None, scr, {"checkX": "String? value"}, "SignUp", "sign_up.dart",
                                   {"checkX": "String?"})
    check("String? checkX(String? value) {" in stub and "return null;" in stub, "validator stub returns null")
    check(CG.user_overrides("  @override\n  String? checkX(String? value) {") == {"checkX": "String? value"},
          "user validator override found")
    # validation
    bad = M.Screen({"name": "Bad", "tree": {"type": "Scaffold", "id": "w1", "slots": {"body": {
        "type": "Column", "id": "w2", "children": [
            {"type": "TextFormField", "id": "w3", "name": "t", "props": {"validators": [{"rule": "nope"}]}},
            {"type": "Radio", "id": "w4", "props": {"value": "a"}},
            {"type": "TextButton", "id": "w5", "slots": {"child": {"type": "Text", "id": "w6", "props": {
                "data": "x"}}}, "events": {"onPressed": "validate:missing"}},
            {"type": "ListView", "id": "w7", "ctor": "builder", "props": {"itemCount": 3}, "slots": {
                "itemBuilder": {"type": "Text", "id": "w8", "props": {"data": {"$code": "item"}}}}}]}}}})
    msgs = " | ".join(i.message for i in bad.validate())
    check("unknown rule" in msgs, "validation: unknown validator rule")
    check("inside a RadioGroup" in msgs, "validation: Radio outside a RadioGroup")
    check("no Form named 'missing'" in msgs, "validation: validate: an unknown form")
    check("reads `item`" in msgs, "validation: template reads item without items")
    # timeline on a Positioned number keeps the old behaviour (warning + end value)
    pos = M.Screen({"name": "P", "timelines": [{"name": "t", "durationMs": 500}], "tree": {
        "type": "Stack", "id": "w1", "children": [{"type": "Positioned", "id": "w2", "props": {
            "left": {"$timeline": "t", "from": 0, "to": 10}}, "slots": {"child": {"type": "Text", "id": "w3",
                                                                                 "props": {"data": "x"}}}}]}})
    gp = CG.generate_screen(pos, None, format_code=False)
    check(gp.warnings and "AnimatedBuilder" not in gp.designer_code, "timeline on Positioned.left: warning")


HAND = r'''
import 'package:flutter/material.dart';

void main() {
  runApp(MaterialApp(
    title: 'Shop front',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
    home: Scaffold(
      appBar: AppBar(title: const Text('Shop', style: TextStyle(shadows: [Shadow(color: Colors.black26,
          blurRadius: 4, offset: Offset(0, 2))]))),
      body: Container(
        color: Colors.blue.withValues(alpha: 0.5),
        child: Column(children: [
          Text('a', style: TextStyle(color: const Color(0xFF112233).withOpacity(0.25))),
          Text('b', style: TextStyle(color: Colors.red.shade300.withAlpha(128))),
          Text('c', style: TextStyle(color: Theme.of(context).colorScheme.primary.withValues(alpha: .5))),
          Expanded(child: ListView.builder(itemCount: 3, itemBuilder: (context, index) => Text('Row $index'))),
          Text.rich(TextSpan(children: [TextSpan(text: 'x'), WidgetSpan(child: Icon(Icons.star))])),
        ]),
      ),
    ),
  ));
}
'''


def importer_units():
    res = I.import_dart(HAND)
    scr = next((s for s in res.screens if s["name"] == "ShopFront"), None)
    check(scr is not None, "main(): MaterialApp(home: ...) -> screen ShopFront")
    if scr is None:
        print(res.report)
        return
    check(scr["route"] == "/" and scr["theme"] == {"seedColor": "Colors.teal"}, f"route / and theme {scr['theme']}")
    t = scr["tree"]
    title = t["slots"]["appBar"]["slots"]["title"]
    check(title["props"]["style"] == {"shadows": [{"color": "Colors.black26", "blur": 4, "offset": [0, 2]}]},
          f"TextStyle shadows parsed {title['props'].get('style')}")
    body = t["slots"]["body"]
    check(body["props"]["color"] == "#802196F3", f"Colors.blue.withValues(alpha: 0.5) {body['props']['color']}")
    kids = body["slots"]["child"]["children"]
    check(kids[0]["props"]["style"]["color"] == "#40112233", "Color(..).withOpacity(0.25)")
    check(kids[1]["props"]["style"]["color"] == "#80E57373", f"shade300.withAlpha(128) {kids[1]['props']}")
    check(M.is_code(kids[2]["props"]["style"]["color"]), "scheme colour with alpha stays code")
    lv = kids[3]["slots"]["child"]
    check(lv.get("ctor") == "builder" and lv["props"] == {"itemCount": 3} and
          lv["slots"]["itemBuilder"]["props"]["data"] == {"$code": "'Row $index'"},
          "hand ListView.builder (expression body)")
    check(kids[4].get("ctor") == "rich" and M.is_code(kids[4]["props"]["spans"][1]),
          "Text.rich: WidgetSpan kept as a code span")
    # a block itemBuilder that is not the designer form stays code
    r2 = I.import_expression("ListView.builder(itemCount: 2, itemBuilder: (context, i) { return Text('$i'); })")
    check(r2["type"] == "Code", "other itemBuilder forms stay a Code node")
    r3 = I.import_expression("RichText(text: TextSpan(text: 'plain'))")
    check(M.is_code(r3["props"]["spans"]), "RichText with a plain TextSpan -> spans $code")


def preview_units():
    scr = M.Screen.load(HERE / "screens" / "Catalog.fscreen.json")
    check(VF.needs_resolve(scr), "builder screens are resolved for the previews")
    data = VF.preview_data(scr)
    lv = next(n for n, *_ in M.walk_node(data["tree"]) if n.get("type") == "ListView")
    check(not lv.get("ctor") and len(lv["children"]) == 6, "ListView.builder -> 6 preview children")
    first, third = lv["children"][0], lv["children"][2]
    tile = first["slots"]["child"]
    check(tile["slots"]["title"]["props"]["data"] == "Apple" and
          third["slots"]["child"]["slots"]["title"]["props"]["data"] == "Cherry", "item substituted")
    check(tile["slots"]["leading"]["slots"]["child"]["props"]["data"] == "1", "'${index + 1}' substituted")
    tmpl = M.Screen(scr.to_dict()).find(first["id"])
    check(tmpl is not None and DW.base_id(third["id"]) == first["id"] and "~2" in third["id"],
          "first copy keeps the template ids, the others are <id>~<n>")
    grid = next(n for n, *_ in M.walk_node(data["tree"]) if n.get("type") == "GridView")
    check(grid["ctor"] == "count" and grid["props"]["crossAxisCount"] == 3 and len(grid["children"]) == 9,
          "GridView.builder -> GridView.count preview")
    check(DW.eval_item_code("'${index * 2} of $item'", {"index": 3, "item": "x"}) == "6 of x", "interpolation")
    check(DW.eval_item_code("foo(index)", {"index": 1}) is None, "unknown code is not evaluated")


def main() -> int:
    for path in sorted((HERE / "screens").glob("*" + M.SCREEN_EXT)):
        roundtrip(path)
    codegen_units()
    importer_units()
    preview_units()
    print("failures:", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
