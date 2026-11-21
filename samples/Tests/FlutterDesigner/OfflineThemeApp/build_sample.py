r"""(Re)builds this sample: three Flutter designer templates with their fonts BUNDLED (downloaded once from
Google Fonts into assets/fonts/, SIL Open Font License files copied alongside) and a project theme
(screens/app.ftheme.json -> lib/theme/app_theme.dart, wired into lib/main.dart). Run from the repository root:

    python samples/Tests/FlutterDesigner/OfflineThemeApp/build_sample.py

Needs internet the first time (the fonts are cached in %LOCALAPPDATA%\RADIDE\cache\fonts afterwards).
Then: flutter pub get, flutter analyze, flutter test.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import model as M, templates as TP, themes as TH  # noqa: E402

LINKS = {"Onboarding": {"onSkip": "replace:/login", "onNext": "nav:/login"},
         "Login": {"onSignUp": "nav:/signup"}}


def main() -> int:
    for sub in ("screens", "assets", "lib"):
        if (HERE / sub).exists():
            shutil.rmtree(HERE / sub)
    for f in ("pubspec.yaml", "pubspec.lock", "analysis_options.yaml"):
        (HERE / f).unlink(missing_ok=True)
    from radide.model import Project
    from radide.languages.flutter import FlutterPlugin
    proj = Project(HERE, "OfflineThemeApp", "flutter")
    proj.save()
    plugin = FlutterPlugin()
    plugin.write_project_files(proj)
    for tid, route in (("onboarding", "/"), ("login", None), ("signup", None)):
        scr, path = TP.instantiate(tid, HERE, route=route, offline_fonts=True, font_weights=(400, 600, 700),
                                   progress=print)
        for n, *_ in scr.walk():
            for ev, h in list((n.get("events") or {}).items()):
                if h in LINKS.get(scr.name, {}):
                    M.set_event(scr, n["id"], ev, LINKS[scr.name][h])
        scr.save(path)
    theme = TH.new_theme(seedColor="#FFFF6B8A", variant="vibrant", mode="light",
                         font={"family": "Outfit", "source": "asset", "headingWeight": "FontWeight.w700"},
                         background={"light": "#FFFDFBF7", "dark": "#FF15131A"},
                         buttons={"radius": 16, "height": 54, "elevation": 0,
                                  "textStyle": {"fontSize": 16, "fontWeight": "FontWeight.w600"}},
                         inputs={"style": "filled", "radius": 14, "fillColor": "#FFF6F1F4",
                                 "contentPadding": {"h": 16, "v": 14}},
                         cards={"radius": 20, "elevation": 0})
    TH.save(HERE, theme)
    written = plugin.write_project_files(proj)
    print("written:", len(written), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
