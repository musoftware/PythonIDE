"""Python Kivy plugin (mobile apps in Python) - CONTRACTS 10.1 / 10.4.

Forms are Kivy screens (KV layout generated into <Form>_designer.py), user code in <Form>.py,
the runtime radkivy.py is copied into the project. F5 runs ``python <Startup>.py`` (a window with the
phone's size); buildozer.spec is written for Android builds (Buildozer runs on Linux / WSL).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..mobile import codegen_kivy as kg
from ..mobile.codegen_common import SUPPORTED_EVENTS, ensure_types, snake
from ..model import Form, Project
from .base import LanguagePlugin, PackageManager, RunSpec


class KivyPlugin(LanguagePlugin):
    id = "kivy"
    display_name = "Python Kivy (mobile app)"
    code_ext = ".py"
    is_mobile = True
    interpreter_names = ["python", "python3", "py"]
    supports_debug = True            # F5/F9: debugpy (DAP) like the Python plugins; pyagent.py fallback
    debug_bp_extras = True
    uses_debugpy = True
    keywords = ["False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
                "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in",
                "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with",
                "yield"]
    builtins = ["print", "len", "range", "str", "int", "float", "list", "dict", "self", "RadEvent"]
    package_manager = PackageManager(
        "pip", "{interpreter}",
        list_cmd=["{interpreter}", "-m", "pip", "list", "--format=freeze", "--disable-pip-version-check"],
        search_cmd=["{interpreter}", "-m", "pip", "index", "versions", "{query}", "--disable-pip-version-check"],
        install_cmd=["{interpreter}", "-m", "pip", "install", "{name}=={version}", "--disable-pip-version-check"],
        uninstall_cmd=["{interpreter}", "-m", "pip", "uninstall", "-y", "{name}"],
        manifest="requirements.txt", search_url="https://pypi.org/search/?q={query}")
    project_name_base = "KivyApp"           # New Project dialog: KivyApp1, ...
    _TEMPLATES = [
        ("kivy_app", "Python Kivy App", "A mobile app written in Python with Kivy: app bar, text field, button, "
         "switch and a list. Runs as a phone-sized window; buildozer.spec for Android.", "SP_ComputerIcon"),
    ]

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        """(id, title, description, icon) of the New Project dialog (Mobile group)."""
        return list(self._TEMPLATES)

    def find_interpreter(self, configured: str = "") -> str:
        """The configured Python, else the IDE's own Python when it has Kivy, else python on PATH."""
        if configured and Path(configured).exists():
            return configured
        import importlib.util
        if importlib.util.find_spec("kivy") is not None:
            return sys.executable
        return super().find_interpreter("") or sys.executable

    # ------------------------------------------------------------ generation
    def generate_designer(self, form: Form, user_code: str) -> str:
        ensure_types()
        return kg.generate_designer(form)

    def new_code(self, form: Form, is_startup: bool) -> str:
        return kg.new_user_code(form.name, is_startup)

    def module_template(self, name: str) -> str:
        return f'"""Module {name}: shared functions. Use it with: import {name}"""\n\n\ndef greeting(who):\n' \
               f'    return f"Hello, {{who}}!"\n'

    # ---------------------------------------------------------------- events
    def events_for(self, ctrl):
        if ctrl is None:
            return ["Load"]
        if ctrl.type == "Timer":
            return ["Tick"]
        evs = [e for e in super().events_for(ctrl) if e in SUPPORTED_EVENTS]
        if not evs and ctrl.type in ("Label", "PictureBox", "MImage", "MIcon", "Card"):
            evs = ["Click"]
        return evs

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s+def\s+{re.escape(name)}\s*\(")

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        owner, _, event = name.rpartition("_")
        ctrl = form.find(owner) if owner else None
        from ..mobile.codegen_dart import EVENT_ARG_TYPES
        with_e = ctrl is not None and (ctrl.type, event) in EVENT_ARG_TYPES
        lines = code.splitlines()
        stub = [f"    def {name}(self, e):" if with_e else f"    def {name}(self):", "        pass", ""]
        idx = self._find_line(code, r"^if\s+__name__\s*==")
        if idx < 0:
            idx = len(lines)
        else:
            while idx > 0 and not lines[idx - 1].strip():
                idx -= 1
            stub = [""] + stub[:-1]
        lines[idx:idx] = stub
        cursor = idx + (2 if stub[0] == "" else 1)
        return "\n".join(lines) + "\n", cursor

    def on_form_added(self, startup_code: str, form_name: str) -> str:
        return startup_code          # radkivy imports a screen when ShowForm(name) opens it

    # ------------------------------------------------------------ project files
    def write_project_files(self, project: Project) -> list[str]:
        folder = Path(project.folder)
        written = []

        def put(rel, text, only_missing=False):
            p = folder / rel
            if only_missing and p.exists():
                return
            if not p.exists() or p.read_text(encoding="utf-8", errors="replace") != text:
                p.write_text(text, encoding="utf-8")
                written.append(rel)
        put("radkivy.py", kg.RUNTIME)
        put("buildozer.spec", kg.buildozer_spec(project.name, snake(project.name).replace("_", "")),
            only_missing=True)
        put("requirements.txt", "kivy>=2.3\n", only_missing=True)
        if project.startup:
            put("main.py", f"# Entry point for Buildozer / Android (python main.py runs the app too).\n"
                           f"from radkivy import run_app\n"
                           f"import {project.startup}  # noqa: F401\n\n"
                           f"run_app({project.startup!r})\n")
        return written

    def regenerate_all(self, project: Project) -> None:
        for name in project.forms:
            if project.form_language(name) != self.id:
                continue
            form = Form.load(project.form_path(name))
            (Path(project.folder) / self.designer_file(name)).write_text(self.generate_designer(form, ""),
                                                                         encoding="utf-8")
        self.write_project_files(project)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..mobile.codegen_templates import kivy_app
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        forms = kivy_app()
        project = Project(folder, name, self.id)
        for form, _code in forms:
            form.save(project.form_path(form.name))
            code = self.new_code(form, True)
            code = code.replace(f"    def {form.name}_Load(self):\n        pass\n", KIVY_TEMPLATE_CODE)
            (folder / self.code_file(form.name)).write_text(code, encoding="utf-8")
            (folder / self.designer_file(form.name)).write_text(self.generate_designer(form, code), encoding="utf-8")
            project.forms.append(form.name)
        project.startup = forms[0][0].name
        project.save()
        self.write_project_files(project)
        return project

    # ------------------------------------------------------------------- run
    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        env = dict(os.environ, PYTHONUNBUFFERED="1", KIVY_NO_ARGS="1")
        try:
            self.write_project_files(Project.load(folder))
        except Exception:  # noqa: BLE001 - run anyway
            pass
        return RunSpec(interpreter, ["-u", self.code_file(startup_form)], folder, env)

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        """Kivy apps are plain Python: the IDE debugs them with debugpy (app._make_session, uses_debugpy);
        without debugpy the line agent pyagent.py of the Python plugins is used."""
        spec = self.run_spec(folder, startup_form, interpreter)
        from .python_tk import AGENT
        spec.env.update(RADDBG_BP=self.breakpoints_env(breakpoints), RADDBG_ROOT=str(folder))
        # main.py imports the start-up screen as a real module (radkivy looks it up in sys.modules)
        main = "main.py" if (Path(folder) / "main.py").exists() else self.code_file(startup_form)
        return RunSpec(interpreter, ["-u", str(AGENT), main], folder, spec.env)


KIVY_TEMPLATE_CODE = """    def MainScreen_Load(self):
        self.lblHello.text = "Type your name and tap the button."

    def btnHello_Click(self):
        name = self.txtName.text.strip()
        if not name:
            self.Toast("Please type your name first")
            return
        text = f"Hello, {name}!"
        if self.swShout.active:
            text = text.upper()
        self.lstGreetings.add_item(text)
        self.txtName.text = ""

    def lstGreetings_Tap(self, e):
        self.MsgBox(e.Text, "You tapped")

    def AppBar1_Click(self, e):
        self.MsgBox("Made with RAD IDE and Kivy.", "About")
"""

PLUGIN = KivyPlugin()
