"""Component packages in Flutter: a phone form (classic designer + Flutter generator) and a Flutter designer
screen (*.fscreen.json, the widget palette) both use the RatingBar package (samples/Tests/Components/RatingBar,
"flutter" target = a widget template + rating_bar.dart) and user Dart code reads the rating.

1. The RatingBar package is installed into this project (.radide/components); a StarRating control (a
   package without a flutter runtime) gets a placeholder and a warning.
2. Phone form Form1: RatingBar rate1 + Label lblOut + Button btnSet. The generated designer declares
   ``final rate1 = _RadRatingBar('rate1', {...})`` (a RadControl with typed members) and the template uses the
   live values (``rate1.value``) and writes taps back (``rate1['Value'] = v``).
3. Flutter designer: the package is in the palette catalog (group Components) with its properties and
   events; screen RateScreen has a RatingBar node rate2 wired to a handler; the generated screen imports
   ../rating_bar.dart, declares the state field and class; the preview draws it with the package's designer.py.
4. flutter pub get / analyze / test (test/rating_test.dart): tapping the 4th star calls rate1_ValueChanged,
   which reads ``rate1.value`` into lblOut ("Rating: 4"); btnSet sets ``rate1.value = 2`` and the widget
   follows; on the designer screen the handler reads ``rate2.value``.        SKIPs 4 without Flutter

Run:  python samples/Tests/Components/RatingBar_Flutter/check_ratingbar_flutter.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Motion" / "Targets"))

from PyQt6.QtCore import QCoreApplication  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-comp-flutter")
app = QApplication(sys.argv[:1])

from proj import add, mobile_form, write_project  # noqa: E402
from target_tools import flutter_exe, run  # noqa: E402

from radide import components as C  # noqa: E402

RESULTS = []
PKG_SRC = HERE.parent / "RatingBar"
STAR_SRC = HERE.parent / "StarRating"


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:1500]}]"), flush=True)


USER_FORM1 = """// Form1 screen - the RatingBar component package on a phone form.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  void Form1_Load() {}

  void rate1_ValueChanged() {
    lblOut.text = 'Rating: ${rate1.value}';
  }

  void btnSet_Click() {
    rate1.value = 2;
    lblOut.text = 'Set: ${rate1['Value']} of ${rate1.maxStars}';
  }
}
"""

EVENTS_RATE = """// RateScreen screen - event handlers (yours).
part of 'rate_screen.dart';

class RateScreenEvents extends RateScreenDesigner {
  int lastRating = -1;

  @override
  void onRate2ValueChanged() {
    lastRating = rate2.value;
  }
}
"""

TEST = """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:PKG/main.dart';
import 'package:PKG/rating_bar.dart';
import 'package:PKG/screens/rate_screen.dart';

void main() {
  testWidgets('phone form: user code reads and sets the rating', (tester) async {
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.byType(RatingBar), findsOneWidget);
    expect(tester.state<RatingBarState>(find.byType(RatingBar)).value, 3);
    await tester.tap(find.byKey(const ValueKey('star4')));
    await tester.pumpAndSettle();
    expect(find.text('Rating: 4'), findsOneWidget);
    await tester.tap(find.text('Set'));
    await tester.pumpAndSettle();
    expect(find.text('Set: 2 of 5'), findsOneWidget);
    expect(tester.state<RatingBarState>(find.byType(RatingBar)).value, 2);
  });

  testWidgets('designer screen: the handler reads rate2.value', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: RateScreen()));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('star5')));
    await tester.pumpAndSettle();
    final s = tester.state<RateScreenEvents>(find.byType(RateScreen));
    expect(s.lastRating, 5);
    expect(s.rate2.value, 5);
  });
}
"""


def install():
    pc = HERE / ".radide" / "components"
    if pc.exists():
        shutil.rmtree(pc)
    C.install_package(PKG_SRC, scope="project", project_folder=HERE)
    C.install_package(STAR_SRC, scope="project", project_folder=HERE)
    C.REGISTRY.set_project(HERE)
    check("RatingBar and StarRating installed in the project",
          C.is_component_type("RatingBar") and C.is_component_type("StarRating"))


def build_form():
    f = mobile_form("Form1", "small_phone")
    add(f, "Label", "lblOut", 16, 16, 300, 30, Text="Tap a star")
    add(f, "RatingBar", "rate1", 16, 60, 200, 40)
    add(f, "Button", "btnSet", 16, 112, 120, 40, Text="Set")
    add(f, "StarRating", "star1", 16, 170, 160, 30)
    return f


def build_screen():
    from radide.components import dart as D
    from radide.flutterdesign import model as M
    synced = D.sync_catalog()
    check("Flutter designer catalog has the package (Components group)", "RatingBar" in synced and
          M.CATALOG["RatingBar"].category == "Components" and "StarRating" not in M.CATALOG,
          (synced, M.CATALOG.get("RatingBar")))
    spec = M.CATALOG["RatingBar"]
    check("designer properties / events come from the manifest",
          set(spec.props) == {"Value", "MaxStars", "ReadOnly", "StarColor", "EmptyColor"} and
          spec.props["StarColor"].default == "#FFFFB400" and list(spec.events) == ["ValueChanged"], spec.props)
    scr = M.Screen.new("RateScreen")
    col = M.new_node("Column", scr)
    col["children"] = [M.new_node("Text", scr, props={"data": "Rate the app"}), M.new_node("RatingBar", scr)]
    rb = col["children"][1]
    check("a new RatingBar node gets a field name and the defaults", rb.get("name") == "rate1" and
          rb["props"].get("Value") == 3, rb)
    rb["name"] = "rate2"
    rb["props"]["MaxStars"] = 6
    rb["props"]["MaxStars"] = 5
    rb["events"] = {"ValueChanged": "onRate2ValueChanged"}
    scr.data["tree"].setdefault("slots", {})["body"] = col
    issues = [i for i in scr.validate() if i.level == "error"]
    check("the screen validates", not issues, issues)
    (HERE / "screens").mkdir(exist_ok=True)
    scr.save(HERE / "screens" / "rate_screen.fscreen.json")
    return scr


def preview_check(scr):
    from PyQt6.QtGui import QImage, QPainter
    from radide.flutterdesign import qtpreview as Q
    from radide.components import dart as D
    node = scr.data["tree"]["slots"]["body"]["children"][1]
    size = D.preview_size("RatingBar")
    img = QImage(200, 40, QImage.Format.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    D.paint_preview(p, 200, 40, node)
    p.end()
    gold = sum(1 for x in range(0, 200, 2) for y in range(0, 40, 2) if (img.pixel(x, y) & 0xFFFFFF) == 0xFFB400)
    check("designer preview drawn by the package's designer.py (golden stars)", size == (140, 28) and gold > 20,
          (size, gold))
    box = Q._unknown(node, Q.C(0, 400, 0, 400), None, None)
    check("the designer canvas lays it out at the package's default size with the package painter",
          (box.w, box.h) == (140, 28) and box.paint is not None, (box.w, box.h))


def main():
    install()
    f = build_form()
    from radide.components import codegen as CG
    CG.WARNINGS.clear()
    scr = build_screen()
    preview_check(scr)
    write_project(HERE, "flutter", [f], {"Form1": USER_FORM1}, overwrite_user=True)
    (HERE / "lib" / "screens").mkdir(parents=True, exist_ok=True)
    (HERE / "lib" / "screens" / "rate_screen_events.dart").write_text(EVENTS_RATE, encoding="utf-8")
    from radide.flutterdesign import codegen as FCG
    FCG.write_all(HERE)
    from radide.languages import get_plugin
    from radide.model import Project
    get_plugin("flutter").write_project_files(Project.load(HERE))
    d = (HERE / "lib" / "form1_designer.dart").read_text(encoding="utf-8")
    check("phone: state object _RadRatingBar with the properties", "final rate1 = _RadRatingBar(" in d and
          "'Value': 3" in d and "class _RadRatingBar extends RadControl" in d, d[:3000])
    check("phone: typed members (int get value / set value)", "int get value =>" in d and "set value(int v)" in d
          and "String get starColor" in d, "")
    check("phone: template uses live values and writes taps back", "RatingBar(" in d and "value: rate1.value" in d
          and "rate1['Value'] = v;" in d and "_code.rate1_ValueChanged()" in d, d)
    check("phone: StarRating (no flutter runtime) is a placeholder + warning",
          "[StarRating: no flutter runtime]" in d and any("StarRating" in w and "flutter" in w for w in CG.WARNINGS),
          CG.WARNINGS)
    radapp = (HERE / "lib" / "radapp.dart").read_text(encoding="utf-8")
    check("phone: rating_bar.dart copied to lib/ and exported", (HERE / "lib" / "rating_bar.dart").is_file() and
          "export 'rating_bar.dart';" in radapp, "")
    s = (HERE / "lib" / "screens" / "rate_screen.dart").read_text(encoding="utf-8")
    check("designer: screen imports ../rating_bar.dart", "import '../rating_bar.dart';" in s, s[:800])
    check("designer: state field + class", "late final rate2 = _RadRatingBar(" in s and
          "class _RadRatingBar {" in s and "setState(() {})" in s, s)
    check("designer: handler declared and called from the template", "void onRate2ValueChanged();" in s and
          "onRate2ValueChanged();" in s.split("Widget build", 1)[1] and "value: rate2.value" in s, s)
    fl = flutter_exe()
    if not fl:
        print("SKIP flutter analyze / test: Flutter SDK not found")
    else:
        pkg = next(ln.split(":", 1)[1].strip() for ln in (HERE / "pubspec.yaml").read_text().splitlines()
                   if ln.startswith("name:"))
        (HERE / "test").mkdir(exist_ok=True)
        (HERE / "test" / "rating_test.dart").write_text(TEST.replace("PKG", pkg), encoding="utf-8")
        r = run([fl, "pub", "get", "--offline"], cwd=HERE)
        if r.returncode != 0:
            r = run([fl, "pub", "get"], cwd=HERE)
        check("flutter pub get", r.returncode == 0, r.stdout[-800:] + r.stderr[-800:])
        r = run([fl, "analyze", "--no-fatal-infos"], cwd=HERE)
        check("flutter analyze: no issues", r.returncode == 0 and "No issues found" in r.stdout,
              r.stdout[-2500:] + r.stderr[-500:])
        r = run([fl, "test"], cwd=HERE, timeout=900)
        check("flutter test: user code reads / sets the rating (phone form + designer screen)",
              r.returncode == 0 and "All tests passed" in r.stdout, r.stdout[-3000:] + r.stderr[-800:])
        for x in ("build", ".dart_tool"):
            shutil.rmtree(HERE / x, ignore_errors=True)
    from PyQt6.QtCore import QSettings
    QSettings().clear()
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
