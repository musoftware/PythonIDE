"""React Native via Expo (mobile apps in JavaScript) - CONTRACTS 10.1 (optional item) / 10.4.

The same mobile .form controls as Flutter / Kivy generate React Native JSX:
    <Form>_designer.jsx (generated, class <Form>Designer extends RadForm) + <Form>.jsx (your code: VB-style
    handlers ``btnGo_Click(e) { ... }`` in ``class <Form> extends <Form>Designer``), App.js (generated:
    @react-navigation native stack, one screen per form), radapp.js (runtime).
F5 (radide/features/expo.py): ``npm install`` the first time, then ``npx expo start --web`` with the page in the
Preview dock, or on an Android emulator through Expo Go; saving a file fast-refreshes the app.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from ..mobile import codegen_rn as rn
from ..mobile.codegen_common import SUPPORTED_EVENTS, ensure_types
from ..mobile.rn_runtime import RADAPP_JS
from ..model import Form, Project
from .base import Completion, LanguagePlugin, PackageManager, RunSpec

NODE_HINTS = [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"]


def node_exe() -> str:
    for n in ("node.exe", "node"):
        p = shutil.which(n)
        if p:
            return p
    return next((h for h in NODE_HINTS if Path(h).exists()), "")


def node_tool(name: str) -> str:
    """npm / npx next to node (npm.cmd on Windows), else on PATH."""
    node = node_exe()
    if node:
        for cand in (f"{name}.cmd", name) if os.name == "nt" else (name,):
            p = Path(node).parent / cand
            if p.exists():
                return str(p)
    return shutil.which(f"{name}.cmd") or shutil.which(name) or ""


MEMBERS = {
    "Text": "string - caption / text", "Visible": "bool - shown or hidden", "Enabled": "bool - can be used",
    "BackColor": "'#RRGGBB' - background colour", "ForeColor": "'#RRGGBB' - text colour", "FontSize": "number",
    "Tag": "any value", "Refresh()": "redraw the screen", "Focus()": "focus a text field",
}
TYPE_MEMBERS = {
    "check": {"Checked": "bool - on / off"},
    "value": {"Value": "number - current value", "Minimum": "number", "Maximum": "number"},
    "list": {"Items": "string[] - the items (fields separated by |)", "SelectedIndex": "int (-1 = none)",
             "SelectedItem": "string - text of the selected item", "Count": "number of items",
             "AddItem(item)": "add an item", "InsertItem(index, item)": "insert an item",
             "RemoveAt(index)": "remove an item", "Clear()": "remove every item", "SetItems(list)": "replace the items",
             "Field(i, n)": "field n of item i (\"a|b\" items)"},
    "image": {"Image": "URL string or require('./assets/x.png')"},
    "web": {"Url": "string - the page shown"},
    "timer": {"Interval": "milliseconds", "Enabled": "bool - running", "Start()": "start", "Stop()": "stop"},
}
KIND = {"CheckBox": "check", "RadioButton": "check", "Switch": "check", "MSlider": "value", "TrackBar": "value",
        "ProgressBar": "value", "NumericUpDown": "value", "Timer": "timer", "MImage": "image", "PictureBox": "image",
        "MWebView": "web", **{t: "list" for t in rn.LIST_TYPES}}
FORM_HELPERS = {
    "ShowForm": "this.ShowForm('Form2', args) - open another screen",
    "SwitchForm": "this.SwitchForm('Form2', args) - replace this screen",
    "CloseForm": "this.CloseForm([result]) - close this screen (go back)",
    "FormArgs": "this.FormArgs - the value passed to ShowForm",
    "MsgBox": "this.MsgBox(text, [title]) - message box (await it to wait for OK)",
    "Confirm": "await this.Confirm(text) -> true / false",
    "InputBox": "await this.InputBox(prompt, [title], [value]) -> string or null",
    "Toast": "this.Toast(text) - short message at the bottom of the screen",
    "OpenDrawer": "this.OpenDrawer() - open the side menu",
    "RadApp": "RadApp.data.key - values shared by every screen",
}


class ExpoPlugin(LanguagePlugin):
    id = "expo"
    display_name = "React Native (Expo mobile app)"
    code_ext = ".jsx"
    is_mobile = True              # CONTRACTS 10.4: phone frame + Mobile toolbox group in the designer
    interpreter_names = ["node.exe", "node"]
    interpreter_hints = NODE_HINTS
    supports_debug = False        # F5 runs (Chrome DevTools / React DevTools debug the web page)
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ["'", '"', "`"]
    keywords = """async await break case catch class const continue debugger default delete do else export extends
        false finally for from function if import in instanceof let new null of return static super switch this
        throw true try typeof undefined var void while with yield""".split()
    builtins = ["console", "Math", "JSON", "Date", "Number", "String", "Array", "Object", "Promise", "setTimeout",
                "setInterval", "clearInterval", "fetch", "RadApp", "RadEvent"]
    project_name_base = "ExpoApp"           # New Project dialog: ExpoApp1, ...
    _TEMPLATES = [
        ("expo_app", "React Native (Expo) App", "A React Native app (JavaScript) with two screens: app bar, text "
         "field, button, switch, list and a details screen opened with ShowForm. Runs in the Preview (web) and on "
         "Android with Expo Go; fast refresh on save.", "SP_ComputerIcon"),
    ]
    package_manager = PackageManager(
        name="npm", tool="npm",
        list_cmd=["npm", "ls", "--depth=0"],
        search_cmd=["npm", "search", "{query}"],
        install_cmd=["npx", "expo", "install", "{name}"],
        uninstall_cmd=["npm", "uninstall", "{name}"],
        init_cmd=None, manifest="package.json",
        search_url="https://reactnative.directory/?search={query}")

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(self._TEMPLATES)

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return node_exe()

    # ------------------------------------------------------------- generation
    def generate_designer(self, form: Form, user_code: str) -> str:
        ensure_types()
        return rn.generate_designer(form, self.code_file(form.name))

    def new_code(self, form: Form, is_startup: bool) -> str:
        return rn.new_user_code(form.name, is_startup)

    def module_template(self, name: str) -> str:
        stem = Path(name).stem
        return (f"// Module {stem}: shared functions. Use it from a screen with\n"
                f"//   import {{ greeting }} from './{stem}';\n\n"
                f"export function greeting(who) {{\n  return `Hello, ${{who}}!`;\n}}\n")

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
        return self._find_line(code, rn.HANDLER_RX.format(name=re.escape(name)))

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        """Insert ``name(e) { }`` before the closing brace of ``class <Form>``."""
        lines = code.rstrip("\n").splitlines()
        start = self._find_line(code, rf"^\s*(?:export\s+(?:default\s+)?)?class\s+{re.escape(form.name)}\b")
        end = -1
        if start >= 0:
            for i in range(start + 1, len(lines)):
                if lines[i].rstrip() == "}":
                    end = i
                    break
        if end < 0:
            lines += ["", f"// (handler added by RAD IDE - move it into class {form.name})",
                      f"function {name}(e) {{", "  ", "}"]
            return "\n".join(lines) + "\n", len(lines) - 2
        stub = [f"  {name}(e) {{", "    ", "  }"]
        if end - 1 > start and lines[end - 1].strip():
            stub.insert(0, "")
        lines[end:end] = stub
        return "\n".join(lines) + "\n", end + (2 if stub[0] == "" else 1)

    def on_file_removed(self, code: str, filename: str) -> str:
        stem = Path(filename).stem
        rx = re.compile(rf"^\s*import\s+.*['\"]\./{re.escape(stem)}(?:\.jsx?)?['\"].*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ project files
    def write_project_files(self, project: Project) -> list[str]:
        """(Re)write App.js and radapp.js; package.json / app.json / index.js / babel.config.js when missing;
        copy images used by the forms into assets/. Returns the files written."""
        ensure_types()
        folder = Path(project.folder)
        written: list[str] = []
        forms, images = [], set()
        for name in project.forms:
            if project.form_language(name) != self.id:
                continue
            try:
                form = Form.load(project.form_path(name))
            except Exception:  # noqa: BLE001 - a broken form must not stop the others
                continue
            forms.append((name, str(form.props.get("Text") or name)))
            for c in form.controls:
                img = str(c.props.get("Image") or "").strip()
                if img and not re.match(r"^(https?:)?//|^data:", img):
                    images.add(img)

        def put(rel: str, text: str, only_missing=False):
            p = folder / rel
            if only_missing and p.exists():
                return
            old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
            if old != text:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
                written.append(rel)
        for img in sorted(images):
            src = Path(img) if Path(img).is_absolute() else folder / img
            if src.is_file() and src.parent != folder / "assets":
                dst = folder / "assets" / src.name
                if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                    dst.parent.mkdir(exist_ok=True)
                    shutil.copy2(src, dst)
                    written.append(f"assets/{src.name}")
        slug = rn.slug_of(project.name)
        put("package.json", rn.package_json(slug), only_missing=True)
        put("app.json", rn.app_json(project.name, slug), only_missing=True)
        put("index.js", rn.INDEX_JS, only_missing=True)
        put(".gitignore", rn.GITIGNORE, only_missing=True)
        put("radapp.js", RADAPP_JS)
        put("App.js", rn.generate_app(project.name, forms, project.startup))
        return written

    def regenerate_all(self, project: Project) -> None:
        for name in project.forms:
            if project.form_language(name) != self.id:
                continue
            form = Form.load(project.form_path(name))
            text = self.generate_designer(form, "")
            dp = Path(project.folder) / self.designer_file(name)
            if not dp.exists() or dp.read_text(encoding="utf-8", errors="replace") != text:
                dp.write_text(text, encoding="utf-8")
        self.write_project_files(project)

    # ------------------------------------------------------------ new projects
    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        """New Project > Mobile > React Native (Expo) App."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        project = Project(folder, name, self.id)
        project.extra["expo"] = {"device": "web"}
        for form, body in expo_app_forms():
            form.save(project.form_path(form.name))
            code = rn.new_user_code(form.name, not project.forms, body)
            (folder / self.code_file(form.name)).write_text(code, encoding="utf-8")
            (folder / self.designer_file(form.name)).write_text(self.generate_designer(form, code), encoding="utf-8")
            project.forms.append(form.name)
        project.startup = project.forms[0]
        project.save()
        self.write_project_files(project)
        return project

    # ------------------------------------------------------------------- run
    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        """Plain run (features/expo.py normally runs the app): the Expo dev server for the web."""
        try:
            self.write_project_files(Project.load(folder))
        except Exception:  # noqa: BLE001
            pass
        env = dict(os.environ, BROWSER="none", EXPO_NO_TELEMETRY="1")
        return RunSpec(node_tool("npx") or "npx", ["expo", "start", "--web"], Path(folder), env)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\bthis\.(\w+)\.\w*$", before)
        if m and names and m.group(1) in names:
            kind = KIND.get(names[m.group(1)], "")
            members = dict(TYPE_MEMBERS["timer"]) if kind == "timer" else {**MEMBERS, **TYPE_MEMBERS.get(kind, {})}
            return [Completion(k.split("(")[0], "method" if "(" in k else "property", v) for k, v in members.items()]
        if re.search(r"\bthis\.\w*$", before):
            out = [Completion(n, "control", t) for n, t in (names or {}).items()]
            return out + [Completion(k, "function", v) for k, v in FORM_HELPERS.items() if k != "RadApp"]
        if re.search(r"\.\w*$", before):
            return []
        out = super().completions(code, line, col, path, names)
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\s*\([^()]*$", before)
        return FORM_HELPERS.get(m.group(1), "") if m else ""


# =========================================================================== template
def expo_app_forms() -> list[tuple[Form, str]]:
    """MainScreen (app bar, text field, button, switch, list) + DetailsScreen (opened with ShowForm)."""
    from ..mobile.codegen_templates import _add, _appbar, _form
    f = _form("MainScreen", "My Expo App")
    W = int(f.props["Width"])
    _appbar(f, "My Expo App", "info")
    _add(f, "Label", "lblHello", 16, 72, W - 32, 32, Text="Welcome! Type your name and tap the button.", FontSize=11)
    _add(f, "MTextField", "txtName", 16, 112, W - 32, 52, Text="", Hint="Your name")
    _add(f, "Button", "btnHello", 16, 176, W - 32, 44, Text="Say hello", FontSize=11)
    _add(f, "Switch", "swShout", 16, 228, W - 32, 40, Text="Shout (upper case)")
    _add(f, "MListView", "lstGreetings", 16, 276, W - 32, 300, Items="", ItemTemplate="icon|title|subtitle")
    _add(f, "Button", "btnDetails", 16, 588, W - 32, 44, Text="Open the details screen", FontSize=11)
    main = """  MainScreen_Load(e) {
    this.lblHello.Text = 'Type your name and tap the button.';
  }

  btnHello_Click(e) {
    const name = this.txtName.Text.trim();
    if (!name) {
      this.Toast('Please type your name first');
      return;
    }
    let text = `Hello, ${name}!`;
    if (this.swShout.Checked) text = text.toUpperCase();
    this.lstGreetings.AddItem(`chat|${text}|${new Date().toLocaleTimeString()}`);
    this.txtName.Text = '';
  }

  lstGreetings_Tap(e) {
    this.ShowForm('DetailsScreen', this.lstGreetings.Field(e.Index, 1));
  }

  btnDetails_Click(e) {
    this.ShowForm('DetailsScreen', 'Opened from the button');
  }

  AppBar1_Click(e) {
    this.MsgBox('Made with RAD IDE and React Native (Expo).', 'About');
  }
"""
    d = _form("DetailsScreen", "Details")
    W = int(d.props["Width"])
    _appbar(d, "Details", "", name="AppBar1")
    _add(d, "Label", "lblMessage", 16, 80, W - 32, 40, Text="(message)", FontSize=14, FontBold=True)
    _add(d, "MSlider", "sldSize", 16, 136, W - 32, 40, Minimum=10, Maximum=40, Value=18)
    _add(d, "Label", "lblSize", 16, 180, W - 32, 24, Text="Text size: 18", FontSize=10)
    _add(d, "Button", "btnClose", 16, 224, W - 32, 44, Text="Back", FontSize=11)
    details = """  DetailsScreen_Load(e) {
    this.lblMessage.Text = this.FormArgs || '(no message)';
  }

  sldSize_Changed(e) {
    this.lblMessage.FontSize = e.Value;
    this.lblSize.Text = `Text size: ${e.Value}`;
  }

  btnClose_Click(e) {
    this.CloseForm();
  }
"""
    return [(f, main), (d, details)]


PLUGIN = ExpoPlugin()
