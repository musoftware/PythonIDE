"""(Re)builds this sample: a RAD IDE Flutter project made of the nine Flutter designer templates plus a gallery
home screen (route "/") that opens each of them. Run from the repository root:

    python samples/Tests/FlutterDesigner/TemplateGallery/build_sample.py

It instantiates the templates (radide/flutterdesign/templates), links their buttons with navigation events,
writes project.radproj and lets the Flutter language plugin generate lib/ (main.dart, screens, routes, radfx).
Fonts load through the google_fonts package at run time. Then: flutter pub get, flutter analyze, flutter build web.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import model as M, templates as TP  # noqa: E402
from radide.flutterdesign.templates.build_templates import A, N, T, box, gap, icon, lin  # noqa: E402

LINKS = {   # template screen -> {handler name: navigation event}
    "Login": {"onSignUp": "nav:/signup", "onLogin": "nav:/dashboard"},
    "SignUp": {"onSignUp": "nav:/dashboard"},
    "Onboarding": {"onSkip": "replace:/login", "onNext": "nav:/login"},
    "Shop": {"onOpenProduct": "nav:/product"},
    "Dashboard": {"onNotifications": "nav:/chat"},
    "Settings": {"onAccount": "nav:/profile"},
}


def gallery_screen() -> M.Screen:
    F = "Poppins"
    tiles = []
    for i, t in enumerate(TP.list_templates()):
        route = M.Screen.load(t.file).route
        tiles.append(box(N("ListTile", {"contentPadding": {"h": 16, "v": 6}},
                           leading=box(icon("dashboard_customize_outlined", "#FF5B5FD9"), w=44, h=44,
                                       radius=14, color="#1F5B5FD9", align="center"),
                           title=T(t.title, 16, "w600", "#FF23233A", F),
                           subtitle=T(t.category, 12, None, "#FF8E8FA6", F),
                           trailing=icon("chevron_right_rounded", "#FFB0B3C5"),
                           events={"onTap": f"nav:{route}"}),
                         color="Colors.white", radius=18, margin={"b": 12}, anim=A("fade_up", 150 + i * 60)))
    tree = N("Scaffold", {"backgroundColor": "#FFF5F6FB"}, body=N("ListView", {"padding": {"all": 0}}, children=[
        box(N("SafeArea", child=N("Padding", {"padding": {"l": 24, "t": 28, "r": 24, "b": 32}}, child=N(
            "Column", {"crossAxisAlignment": "CrossAxisAlignment.start"}, children=[
                T("Template gallery", 30, "w700", "Colors.white", F, anim=A("fade_up", 0)),
                gap(6),
                T("Nine screens designed with the RAD IDE Flutter designer.", 14, None, "#DDFFFFFF", F,
                  anim=A("fade_up", 100)),
            ]))), gradient=lin("#FF5B5FD9", "#FF9D6BF2"), radius={"bl": 32, "br": 32}),
        N("Padding", {"padding": {"l": 20, "t": 20, "r": 20, "b": 20}},
          child=N("Column", {"crossAxisAlignment": "CrossAxisAlignment.stretch"}, children=tiles)),
    ]))
    scr = M.Screen.new("Gallery", "/")
    scr.data["fonts"] = [{"family": F, "source": "google"}]
    scr.tree = json.loads(json.dumps(tree))
    scr.assign_ids(scr.tree)
    return scr


def main() -> int:
    for sub in ("screens", "assets", "lib"):
        if (HERE / sub).exists():
            shutil.rmtree(HERE / sub)
    for f in ("pubspec.yaml", "pubspec.lock", "analysis_options.yaml"):
        (HERE / f).unlink(missing_ok=True)
    from radide.model import Project
    from radide.languages.flutter import FlutterPlugin
    proj = Project(HERE, "TemplateGallery", "flutter")
    proj.save()
    plugin = FlutterPlugin()
    plugin.write_project_files(proj)          # pubspec.yaml / analysis_options / main.dart skeleton
    for t in TP.list_templates():
        scr, path = TP.instantiate(t.id, HERE)
        for n, *_ in scr.walk():
            for ev, h in list((n.get("events") or {}).items()):
                if h in LINKS.get(scr.name, {}):
                    M.set_event(scr, n["id"], ev, LINKS[scr.name][h])
        scr.save(path)
    gallery_screen().save(HERE / "screens" / f"Gallery{M.SCREEN_EXT}")
    written = plugin.write_project_files(proj)
    print("written:", len(written), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
