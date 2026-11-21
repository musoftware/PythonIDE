"""Checks of the Flutter designer resources (templates, assets, fonts, themes, animations). From the repo root:

    python samples/Tests/FlutterDesigner/TemplateGallery/check_templates.py            # offline checks
    python samples/Tests/FlutterDesigner/TemplateGallery/check_templates.py --analyze  # + flutter analyze of a
                                                                                        #   fresh project made of
                                                                                        #   every template
Fonts are tested from the local cache when present (fonts.add_to_project downloads them otherwise).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from radide.flutterdesign import animations as AN, assets as AS, codegen as CG  # noqa: E402
from radide.flutterdesign import model as M, templates as TP, themes as TH  # noqa: E402

FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


PUBSPEC = """name: probe
publish_to: 'none'
environment:
  sdk: ^3.5.0

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0

flutter:
  uses-material-design: true
"""


def templates_ok():
    ts = TP.list_templates()
    check(len(ts) == 9, f"9 templates listed ({len(ts)})")
    ids = {t.id for t in ts}
    check(ids == {"login", "signup", "onboarding", "profile", "dashboard", "shop", "product", "settings", "chat"},
          "template ids")
    for t in ts:
        scr = t.load()
        errs = [str(i) for i in scr.validate() if i.level == "error"]
        g = CG.generate_screen(scr)
        check(not errs and not g.warnings, f"{t.id}: valid, generates without warnings")
        check(all(TP.asset_path(a).exists() for a in t.assets), f"{t.id}: artwork present")
        check(t.thumbnail is not None, f"{t.id}: thumbnail")
        check(g.uses_anim and g.uses_google_fonts, f"{t.id}: animated, uses its Google font")


def instantiate_ok(folder: Path):
    (folder / "pubspec.yaml").write_text(PUBSPEC, encoding="utf-8")
    s1, p1 = TP.instantiate("login", folder)
    s2, p2 = TP.instantiate("login", folder)            # second copy -> unique name, shared artwork
    check(p1.name == "Login.fscreen.json" and s2.name == "Login2" and s2.route == "/login2",
          f"unique names ({s1.name}, {s2.name} {s2.route})")
    imgs = list((folder / "assets" / "images").glob("*.png"))
    check(len(imgs) == 1, f"identical artwork copied once ({len(imgs)})")
    # a different file with the same name gets a suffix and the screen is rewritten
    (folder / "assets" / "images" / "avatar_2.png").write_bytes(b"not the template file")
    s3, _ = TP.instantiate("profile", folder)
    check("assets/images/avatar_2_2.png" in s3.data["assets"], "clashing asset renamed + references rewritten")
    check("avatar_2_2.png" in json.dumps(s3.tree), "tree points at the renamed asset")
    for t in TP.list_templates():
        if t.id not in ("login", "profile"):
            TP.instantiate(t.id, folder)
    written, warns = CG.write_all(folder)
    pub = (folder / "pubspec.yaml").read_text(encoding="utf-8")
    check("    - assets/images/" in pub, "pubspec registers assets/images/")
    check("google_fonts:" in pub, "pubspec gets google_fonts")
    check(not warns, f"no codegen warnings ({warns[:2]})")
    check((folder / "lib" / "screens" / "routes.dart").exists(), "routes.dart written")


def animations_ok():
    scr = M.Screen(json.loads(TP.get("settings").file.read_text(encoding="utf-8")))
    lv = next(n for n, *_ in scr.walk() if n["type"] == "ListView")
    p = AN.stagger(scr, lv["id"], "fade_right", 100, 80)
    delays = [c.get("anim", {}).get("delayMs", 0) for c in lv["children"] if c.get("anim")]
    check(delays[:3] == [100, 180, 260], f"stagger delays {delays[:3]}")
    M.apply_patch(scr, M.invert(p))
    check(json.loads(TP.get("settings").file.read_text(encoding="utf-8"))["tree"] == scr.to_dict()["tree"],
          "stagger undo restores the tree")
    AN.cascade(scr, None, 0, 100)
    tl = AN.timeline(scr)
    check([t[1] for t in tl][:3] == [0, 100, 200], "cascade re-times in document order")
    a = AN.make_anim("pop", 300)
    check(a == {"type": "scaleIn", "durationMs": 400, "scale": 0.6, "curve": "Curves.easeOutBack",
                "delayMs": 300}, f"preset pop {a}")
    check(AN.to_flutter_animate(AN.make_anim("fade_up", 200)).startswith(".animate(delay: 200.ms).fadeIn("),
          "flutter_animate export")
    check(AN.describe({"type": "fadeInUp", "delayMs": 300}) == "Fade in up 500 ms after 300 ms", "describe")


def assets_ok(folder: Path):
    (folder / "pubspec.yaml").write_text(PUBSPEC, encoding="utf-8")
    src = folder.parent / "My Hero Image.PNG"
    shutil.copy2(TP.asset_path("login_waves.png"), src)
    a = AS.import_asset(folder, src)
    check(a.rel == "assets/images/my_hero_image.png" and a.kind == "image", f"image import {a.rel}")
    svg = folder.parent / "logo.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/>'
                   '</svg>', encoding="utf-8")
    lot = folder.parent / "spinner.json"
    lot.write_text('{"v":"5.7.4","fr":30,"ip":0,"op":60,"w":100,"h":100,"layers":[]}', encoding="utf-8")
    out = AS.import_many(folder, [svg, lot])
    check([x.kind for x in out] == ["svg", "lottie"], "svg + lottie classified")
    pub = (folder / "pubspec.yaml").read_text(encoding="utf-8")
    check("flutter_svg:" in pub and "lottie:" in pub, "svg / lottie packages added")
    check("- assets/svg/" in pub and "- assets/lottie/" in pub and "- assets/images/" in pub, "asset folders")
    again = AS.import_asset(folder, src)
    check(again.rel == a.rel, "re-import of the same file reuses it")
    scr = M.Screen.new("Probe")
    body = scr.tree["slots"]["body"]
    M.replace(scr, body["id"], AS.image_node(scr, a.rel))
    AS.sync_screen_assets(scr)
    scr.save(folder / "screens" / "Probe.fscreen.json")
    check(AS.asset_usages(folder, a.rel) != [], "usage found")
    check(AS.remove_asset(folder, a.rel) is False, "remove refused while used")
    check(AS.remove_asset(folder, out[0].rel) is True, "unused asset removed")
    check(len(AS.list_assets(folder)) == 2, "list_assets")


def themes_ok(folder: Path):
    (folder / "pubspec.yaml").write_text(PUBSPEC, encoding="utf-8")
    t = TH.new_theme(seedColor="#0077B6", variant="fidelity",
                     font={"family": "Lato", "source": "google", "headings": "Playfair Display"},
                     colors={"light": {"secondary": "#FFFF8800"}},
                     inputs={"style": "underline"}, appBar={"transparent": True})
    TH.save(folder, t)
    w = TH.write_project_theme(folder)
    code = (folder / TH.THEME_DART).read_text(encoding="utf-8")
    check(TH.THEME_DART in w and "GoogleFonts.getTextTheme('Playfair Display'" in code, "theme dart + fonts")
    check("DynamicSchemeVariant.fidelity" in code and "UnderlineInputBorder" in code, "variant / input style")
    check("google_fonts:" in (folder / "pubspec.yaml").read_text(encoding="utf-8"), "theme adds google_fonts")
    main = ("import 'package:flutter/material.dart';\n\nclass A {\n  Widget b() => MaterialApp(\n"
            "      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),\n"
            "      darkTheme: ThemeData(colorSchemeSeed: Colors.indigo, brightness: Brightness.dark),\n"
            "      routes: {},\n    );\n}\n")
    m2 = TH.patch_main_theme(main)
    check("theme: AppTheme.light," in m2 and "themeMode: AppTheme.mode," in m2 and
          "import 'theme/app_theme.dart';" in m2 and TH.patch_main_theme(m2) == m2, "main.dart wiring idempotent")
    check(TH.screen_theme(t) == {"seedColor": "#FF0077B6", "brightness": "light", "fontFamily": "Lato"},
          "screen_theme")
    try:
        TH.normalize({"variant": "nope"})
        check(False, "bad variant rejected")
    except ValueError:
        check(True, "bad variant rejected")


def fonts_ok(folder: Path):
    from radide.flutterdesign import fonts as FN
    check(FN.repo_dir("IBM Plex Sans Arabic") == "ibmplexsansarabic", "repo dir name")
    check(FN.style_file_name("Poppins", 700, "italic") == "Poppins-BoldItalic.ttf", "file naming")
    text = PUBSPEC + "  fonts:\n    - family: Old\n      fonts:\n        - asset: a.ttf\n"
    check("family: Old" not in FN.remove_font_block(text, "Old") and
          "  fonts:" not in FN.remove_font_block(text, "Old"), "remove_font_block")
    if "Poppins" not in FN.cached_families():
        print("skip font download test (Poppins not cached)")
        return
    (folder / "pubspec.yaml").write_text(PUBSPEC, encoding="utf-8")
    e = FN.add_to_project(folder, "Poppins", (400, 700))
    pub = (folder / "pubspec.yaml").read_text(encoding="utf-8")
    check(e["source"] == "asset" and "assets/fonts/Poppins/Poppins-Bold.ttf" in pub, "font bundled + registered")
    check((folder / "assets/fonts/Poppins/OFL.txt").exists(), "licence copied")
    e2 = FN.add_to_project(folder, "Poppins", (400, 600))
    pub = (folder / "pubspec.yaml").read_text(encoding="utf-8")
    check(pub.count("family: Poppins") == 1 and "Poppins-SemiBold.ttf" in pub and "Poppins-Bold.ttf" not in pub,
          "re-adding rewrites the family block")
    scr = TP.get("login").load()
    TP.to_asset_fonts(scr, {"Poppins": e2})
    s = json.dumps(scr.tree)
    check('"googleFont"' not in s and '"fontFamily": "Poppins"' in s, "text styles switched to the bundled font")


def analyze(folder: Path):
    from radide.model import Project
    from radide.languages.flutter import FlutterPlugin
    proj = Project(folder, "Probe", "flutter")
    proj.save()
    plugin = FlutterPlugin()
    plugin.write_project_files(proj)
    for t in TP.list_templates():
        TP.instantiate(t.id, folder)
    TH.save(folder, TH.new_theme(font={"family": "Inter"}))
    plugin.write_project_files(proj)
    fl = shutil.which("flutter") or r"C:\flutter\bin\flutter.bat"
    r = subprocess.run([fl, "pub", "get", "--offline"], cwd=folder, capture_output=True, text=True, shell=False)
    r = subprocess.run([fl, "analyze"], cwd=folder, capture_output=True, text=True)
    check("No issues found" in r.stdout, "flutter analyze clean (9 templates + project theme)\n" +
          ("" if "No issues found" in r.stdout else r.stdout[-2000:]))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for d in ("p1", "p2/proj", "p3", "p4", "p5"):
            (tmp / d).mkdir(parents=True)
        templates_ok()
        instantiate_ok(tmp / "p1")
        animations_ok()
        assets_ok(tmp / "p2" / "proj")
        themes_ok(tmp / "p3")
        fonts_ok(tmp / "p4")
        if "--analyze" in sys.argv:
            analyze(tmp / "p5")
    print("failures:", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
