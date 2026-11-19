"""HTML5 Canvas Game - game projects that play in the browser (CONTRACTS 10.2 / 10.4).

The scenes are the same ``<Scene>.scene`` files as the pygame / Godot games (scene designer, ``is_game``);
their code is ``<Scene>.js`` with the same VB-style handlers as global functions
(``function Player_Collide(other) { ... }``). The project is a *website* project (``kind: "website"``,
static files): F5 starts the IDE's DevServer and shows ``index.html`` in the Preview dock, which runs
``radgame.js`` (radide/games/runtime/radgame.js).  Before every run and after every scene save the runtime
and ``scenes.js`` are refreshed (radide/games/html5.py).
"""
from __future__ import annotations

from pathlib import Path

from ..games import codegen, html5
from ..model import Form, Project
from ..web_site.project import WEBSITE, WebSitePlugin
from .javascript import JS_KEYWORDS

JS_HELPERS = {"GoToScene": "GoToScene(name) - switch to another scene", "RestartScene": "RestartScene()",
              "Quit": "Quit() - stop the game", "AddScore": "AddScore(points)", "PlaySound": "PlaySound(id)",
              "PlayMusic": "PlayMusic(id, loop)", "StopMusic": "StopMusic()",
              "ShowMessage": "ShowMessage(text, seconds)", "IsKeyDown": 'IsKeyDown("left") -> bool',
              "Find": "Find(name) -> object", "FindGroup": 'FindGroup("Coin") -> array',
              "Clone": "Clone(obj, x, y) -> new object", "AddTimer": "AddTimer(name, ms) - <name>_Tick() fires",
              "Random": "Random(a, b) -> integer", "game": "game.score, game.lives, game.vars, game.scene"}


class Html5GamePlugin(WebSitePlugin):
    id = "html5-game"
    display_name = "HTML5 Canvas Game (JavaScript)"
    code_ext = ".js"
    project_kind = ""                 # New Project uses project_templates() (games), the project is a website
    web_kind = "static"
    needs_interpreter = False
    is_game = True
    scene_ext = ".scene"
    project_name_base = "Game"
    tool_names: list[str] = []
    keywords = JS_KEYWORDS
    builtins = list(JS_HELPERS)
    line_comments = ["//"]
    block_comment = ("/*", "*/")

    def tool(self) -> str:
        return "built-in web server"

    def find_interpreter(self, configured: str = "") -> str:
        return ""

    # ------------------------------------------------------------ New Project (Games group)
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games.templates import templates_for
        return [(t.id, (t.title if t.id != "empty" else "Empty Game") + " (HTML5)",
                 t.description.replace("F5 plays it.", "F5 plays it in the Preview window (any browser)."), t.icon)
                for t in templates_for("pygame")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        first, scenes = html5.create_files(folder, name, template or "platformer", name)
        extra = {"web": {"root": ".", "start": "index.html", "port": 0, "live_reload": True},
                 "scenes": scenes, "game": {"title": name, "start_scene": first}}
        project = Project(folder, name, self.id, [], "", [], {}, WEBSITE, [], {}, extra)
        project.save()
        return Project.load(folder)

    # ------------------------------------------------------------ scenes
    def scene_code_file(self, scene: str) -> str:
        return f"{scene}.js"

    def scene_designer_file(self, scene: str) -> str:
        return html5.SCENES_JS

    def new_scene_code(self, scene) -> str:
        return html5.new_scene_code(scene)

    def generate_scene_designer(self, scene) -> str:
        return html5.SCENES_HEADER

    def on_scene_saved(self, folder: Path, scene: str) -> list[Path]:
        return html5.sync_project(Path(folder))

    def scene_handler(self, obj_name: str | None, event: str) -> str:
        return codegen.handler_name(obj_name, event)

    def add_scene_handler(self, code: str, obj_name: str | None, event: str) -> tuple[str, int]:
        name = codegen.handler_name(obj_name, event)
        line = html5.find_handler(code, name)
        if line >= 0:
            return code, line + 1
        return html5.add_handler(code, name)

    # ------------------------------------------------------------ handlers
    def find_handler(self, code: str, name: str) -> int:
        return html5.find_handler(code, name)

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        return html5.add_handler(code, name, args)

    def module_template(self, name: str) -> str:
        return f"// {name}.js - shared game code (add <script src=\"{name}.js\"></script> to index.html)\n"

    # ------------------------------------------------------------ dev server
    def backend(self, server):
        """Called by the DevServer when it starts: refresh radgame.js and scenes.js; the IDE serves the files."""
        try:
            html5.sync_project(Path(server.folder))
        except OSError:
            pass
        return None

    # ------------------------------------------------------------ completion
    def completions(self, code, line, col, path, names=None):
        from .base import Completion
        out = super().completions(code, line, col, path, names)
        have = {c.name for c in out}
        return out + [Completion(k, "function", v) for k, v in JS_HELPERS.items() if k not in have]

    def calltip(self, code, line, col, path, names=None):
        import re
        text = (code.splitlines()[line:line + 1] or [""])[0][:col]
        m = re.search(r"(\w+)\s*\([^()]*$", text)
        return JS_HELPERS.get(m.group(1), "") if m else ""


PLUGIN = Html5GamePlugin()
