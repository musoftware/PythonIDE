"""Flutter language plugin (Dart, mobile apps) - CONTRACTS 10.1 / 10.4.

A Flutter project is a normal RAD IDE project whose folder is also a Flutter project:
pubspec.yaml, lib/main.dart (generated routes), lib/radapp.dart (runtime), and for every form
lib/<form>.dart (user code) + lib/<form>_designer.dart (generated). Platform folders (android/,
windows/, web/) are created on demand with ``flutter create`` the first time the app runs on / is built
for that platform. Running, hot reload, devices and builds live in radide/features/mobile.py.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..mobile import codegen_dart as cg
from ..mobile.codegen_common import SUPPORTED_EVENTS, ensure_types, snake
from ..model import Form, Project
from .base import Completion, LanguagePlugin, PackageManager, RunSpec

FLUTTER_HINTS = [r"C:\flutter\bin\flutter.bat", r"C:\src\flutter\bin\flutter.bat",
                 str(Path.home() / "flutter" / "bin" / "flutter.bat"), r"C:\tools\flutter\bin\flutter.bat"]


def flutter_exe() -> str:
    """flutter(.bat) - PATH first, then the usual install folders."""
    for name in ("flutter.bat", "flutter"):
        p = shutil.which(name)
        if p:
            return p
    for h in FLUTTER_HINTS:
        if Path(h).exists():
            return h
    return ""


def flutter_root() -> str:
    exe = flutter_exe()
    return str(Path(exe).resolve().parent.parent) if exe else ""


def dart_exe() -> str:
    root = flutter_root()
    if root:
        p = Path(root) / "bin" / "cache" / "dart-sdk" / "bin" / ("dart.exe" if os.name == "nt" else "dart")
        if p.exists():
            return str(p)
    return shutil.which("dart") or ""


def package_name(project_name: str) -> str:
    """Dart package name (lowercase_with_underscores, not a keyword)."""
    s = snake(project_name)
    if s in ("flutter", "test", "dart", "async", "core", "io", "material"):
        s += "_app"
    return s


# members offered after "<control>." in the code editor (IntelliSense)
COMMON_MEMBERS = {"text": "String - caption / text", "visible": "bool - shown or hidden",
                  "enabled": "bool - can be used", "backColor": "Color? - background colour (call refresh())",
                  "foreColor": "Color? - text colour (call refresh())", "fontSize": "double? - text size",
                  "refresh()": "redraw after changing colours / font", "tag": "Object? - any value"}
TYPE_MEMBERS = {
    "RadTextControl": {"controller": "TextEditingController of the field"},
    "RadCheckControl": {"checked": "bool - on / off"},
    "RadValueControl": {"value": "double - current value", "minimum": "double", "maximum": "double"},
    "RadListControl": {"items": "List<String> - the items", "selectedIndex": "int - selected item (-1 = none)",
                       "selectedItem": "String - text of the selected item", "count": "int - number of items",
                       "addItem(item)": "add an item", "insertItem(index, item)": "insert an item",
                       "removeAt(index)": "remove an item", "clear()": "remove every item",
                       "setItems(list)": "replace the items", "field(i, n)": "field n of item i (\"a|b\" items)"},
    "RadImageControl": {"image": "String - assets/<file> or a https:// URL"},
    "RadWebControl": {"url": "String - the page shown"},
}
FORM_HELPERS = {
    "ShowForm": "ShowForm('Form2', [args]) - open another screen",
    "SwitchForm": "SwitchForm('Form2', [args]) - replace this screen",
    "CloseForm": "CloseForm([result]) - close this screen (go back)",
    "FormArgs": "FormArgs - the value passed to ShowForm",
    "MsgBox": "MsgBox(text, [title]) - message box",
    "Confirm": "await Confirm(text) -> bool - Yes / No question",
    "InputBox": "await InputBox(prompt) -> String? - ask for a text",
    "Toast": "Toast(text) - short message at the bottom of the screen",
    "RadApp.data": "RadApp.data['key'] - values shared by every screen",
}


class FlutterPlugin(LanguagePlugin):
    id = "flutter"
    display_name = "Flutter (Dart mobile app)"
    code_ext = ".dart"
    is_mobile = True              # CONTRACTS 10.4: phone frame + Mobile toolbox group in the designer
    module_dir = "lib/"           # Add Module puts .dart files under lib/
    interpreter_names = ["flutter.bat", "flutter"]
    interpreter_hints = FLUTTER_HINTS
    supports_debug = True         # breakpoints (F9): features/mobile.py debugs with flutter debug_adapter
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ["'", '"']
    keywords = """abstract as assert async await break case catch class const continue covariant default
        deferred do dynamic else enum export extends extension external factory false final finally for
        Function get hide if implements import in interface is late library mixin new null on operator
        part required rethrow return sealed set show static super switch sync this throw true try typedef
        var void when while with yield int double num String bool List Map Set Future Stream Object""".split()
    builtins = ["print", "setState", "context", "Navigator", "Colors", "Icons", "Color", "Text", "ShowForm",
                "SwitchForm", "CloseForm", "FormArgs", "MsgBox", "Confirm", "InputBox", "Toast", "RadApp",
                "debugPrint", "Future", "Duration", "DateTime"]
    # New Project dialog: templates of the Mobile group (id, title, description, icon)
    project_name_base = "FlutterApp"        # New Project dialog: FlutterApp1, ...
    _TEMPLATES = [
        ("flutter_app", "Flutter App", "A mobile app with one screen: app bar, text field, button and a list. "
         "Runs on Android, Windows and the web; hot reload on save.", "SP_ComputerIcon"),
        ("flutter_tabs", "Flutter App (tabs + drawer)", "Bottom navigation with three pages, a side drawer "
         "menu, a floating action button and a second screen opened with ShowForm.", "SP_FileDialogDetailedView"),
    ]

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        """(id, title, description, icon) of the New Project dialog (Mobile group)."""
        return list(self._TEMPLATES)

    # ------------------------------------------------------------------ files
    def code_file(self, form_name: str) -> str:
        return f"lib/{snake(form_name)}.dart"

    def designer_file(self, form_name: str) -> str:
        return f"lib/{snake(form_name)}_designer.dart"

    # ------------------------------------------------------------- generation
    def generate_designer(self, form: Form, user_code: str) -> str:
        ensure_types()
        return cg.generate_designer(form, user_code, Path(self.code_file(form.name)).name)

    def new_code(self, form: Form, is_startup: bool) -> str:
        return cg.new_user_code(form.name, Path(self.code_file(form.name)).name,
                                Path(self.designer_file(form.name)).name, is_startup)

    def module_template(self, name: str) -> str:
        return (f"// Module {name}: shared functions and values. Use it from a screen with\n"
                f"//   import '{Path(name).stem}.dart';\n\n"
                f"String greeting(String who) => 'Hello, $who!';\n")

    # ---------------------------------------------------------------- events
    def events_for(self, ctrl):
        if ctrl is None:
            return ["Load"]
        if ctrl.type in ("MenuStrip", "ToolStrip"):
            return super().events_for(ctrl)
        evs = [e for e in super().events_for(ctrl) if e in SUPPORTED_EVENTS]
        if ctrl.type == "Timer":
            return ["Tick"]
        if not evs and ctrl.type in ("Label", "PictureBox", "MImage", "MIcon", "Card"):
            evs = ["Click"]
        return evs

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*(?:void|Future<void>|FutureOr<void>)\s+{re.escape(name)}\s*\(")

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        """Insert ``void <name>() { }`` at the end of class <Form>Code."""
        lines = code.rstrip("\n").splitlines()
        start = self._find_line(code, rf"^class\s+{re.escape(form.name)}Code\b")
        end = -1
        if start >= 0:
            for i in range(start + 1, len(lines)):
                if lines[i].rstrip() == "}":
                    end = i
                    break
        if end < 0:                      # no class (user changed it): append a new class part
            lines += ["", f"// (handler added by RAD IDE - move it into class {form.name}Code)",
                      f"void {name}({self._handler_params(form, name)}) {{", "  ", "}"]
            return "\n".join(lines) + "\n", len(lines) - 2
        stub = [f"  void {name}({self._handler_params(form, name)}) {{", "    ", "  }"]
        if end - 1 > start and lines[end - 1].strip():
            stub.insert(0, "")
        lines[end:end] = stub
        cursor = end + (2 if stub[0] == "" else 1)
        return "\n".join(lines) + "\n", cursor

    @staticmethod
    def _handler_params(form: Form, name: str) -> str:
        """'RadEvent e' for events that carry data (list row tapped: e.Index, AppBar action: e.Action)."""
        owner, _, event = name.rpartition("_")
        ctrl = form.find(owner) if owner else None
        if ctrl is not None and (ctrl.type, event) in cg.EVENT_ARG_TYPES:
            return "RadEvent e"
        return ""

    def on_file_removed(self, code: str, filename: str) -> str:
        name = Path(filename).name
        rx = re.compile(rf"^\s*import\s+['\"](?:package:[^/]+/)?{re.escape(name)}['\"].*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ project files
    def write_project_files(self, project: Project) -> list[str]:
        """(Re)write the generated project-level files: lib/main.dart, lib/radapp.dart, pubspec.yaml /
        analysis_options.yaml / test when missing, assets used by the forms. Returns the files written."""
        ensure_types()
        folder = Path(project.folder)
        (folder / "lib").mkdir(parents=True, exist_ok=True)
        written = []
        forms, webview, images = [], False, set()
        for name in project.forms:
            try:
                form = Form.load(project.form_path(name))
            except Exception:  # noqa: BLE001 - a broken form must not stop the others
                continue
            if project.form_language(name) != self.id:
                continue
            forms.append((name, Path(self.code_file(name)).name, cg.form_route(form)))
            for c in form.controls:
                if c.type == "MWebView":
                    webview = True
                img = str(c.props.get("Image") or "").strip()
                if img and not re.match(r"^(https?:)?//", img) and not img.startswith("assets/"):
                    images.add(img)
        pkg = package_name(project.name)

        def put(rel: str, text: str, only_missing=False):
            p = folder / rel
            if only_missing and p.exists():
                return
            old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
            if old != text:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
                written.append(rel)
        # assets: copy images referenced with a project-relative / absolute path into assets/
        for img in sorted(images):
            src = Path(img) if Path(img).is_absolute() else folder / img
            if src.is_file():
                dst = folder / "assets" / src.name
                if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                    dst.parent.mkdir(exist_ok=True)
                    shutil.copy2(src, dst)
                    written.append(f"assets/{src.name}")
        has_assets = (folder / "assets").is_dir() and any((folder / "assets").iterdir())
        put("pubspec.yaml", cg.pubspec(pkg, webview=webview, assets=has_assets), only_missing=True)
        self._update_pubspec(folder, webview, has_assets, written)
        put("analysis_options.yaml", cg.ANALYSIS_OPTIONS, only_missing=True)
        put("test/widget_test.dart", cg.widget_test(pkg), only_missing=True)
        put(".gitignore", ".dart_tool/\nbuild/\n.flutter-plugins\n.flutter-plugins-dependencies\n*.iml\n.idea/\n",
            only_missing=True)
        put("lib/radapp.dart", cg.RADAPP)
        if webview:
            put("lib/radwebview.dart", cg.RADWEBVIEW)
        seed = str(project.extra.get("theme_color") or "")
        main = cg.generate_main(project.name, forms, project.startup, seed)
        if webview:
            main = main.replace("import 'package:flutter/material.dart';\n",
                                "import 'package:flutter/material.dart';\n\nimport 'radwebview.dart';\n", 1)
            main = main.replace("void main() => runApp(const RadMobileApp());",
                                "void main() {\n  radInstallWebView();\n  runApp(const RadMobileApp());\n}")
        put("lib/main.dart", main)
        return written

    @staticmethod
    def _update_pubspec(folder: Path, webview: bool, assets: bool, written: list) -> None:
        p = folder / "pubspec.yaml"
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            return
        new = text
        if webview and not re.search(r"^\s+webview_flutter\s*:", new, re.M):
            new = re.sub(r"^(dependencies:\s*\n(?:[ \t]+.*\n)*?[ \t]+sdk: flutter\s*\n)",
                         r"\1  webview_flutter: ^4.9.0\n", new, count=1, flags=re.M)
        if assets and not re.search(r"^\s+- assets/\s*$", new, re.M):
            if re.search(r"^  assets:\s*$", new, re.M):
                new = re.sub(r"^(  assets:\s*\n)", r"\1    - assets/\n", new, count=1, flags=re.M)
            elif re.search(r"^flutter:\s*$", new, re.M):
                new = re.sub(r"^(flutter:\s*\n)", r"\1  assets:\n    - assets/\n", new, count=1, flags=re.M)
        if new != text:
            p.write_text(new, encoding="utf-8")
            written.append("pubspec.yaml")

    def regenerate_all(self, project: Project) -> None:
        """Rewrite every designer file of the project's Flutter forms and the project files."""
        for name in project.forms:
            if project.form_language(name) != self.id:
                continue
            code_path = Path(project.folder) / self.code_file(name)
            if not code_path.exists():
                continue
            form = Form.load(project.form_path(name))
            text = self.generate_designer(form, code_path.read_text(encoding="utf-8"))
            dp = Path(project.folder) / self.designer_file(name)
            if not dp.exists() or dp.read_text(encoding="utf-8", errors="replace") != text:
                dp.write_text(text, encoding="utf-8")
        self.write_project_files(project)

    # ------------------------------------------------------------ new projects
    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        """New Project > Mobile > Flutter App / Flutter App (tabs + drawer)."""
        from ..mobile.codegen_templates import build_flutter_project
        return build_flutter_project(self, Path(folder), name, template or "flutter_app")

    # ------------------------------------------------------------------- run
    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        """Plain run (used when features/mobile.py is not loaded): flutter run on Windows."""
        exe = interpreter or flutter_exe() or "flutter"
        return RunSpec(exe, ["run", "-d", "windows", "--target", "lib/main.dart"], Path(folder))

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return flutter_exe()

    @property
    def package_manager(self) -> PackageManager:
        fl = flutter_exe() or "flutter"
        return PackageManager(
            name="pub", tool=fl,
            list_cmd=[fl, "pub", "deps", "--style=compact"],
            search_cmd=None,
            install_cmd=[fl, "pub", "add", "{name}:{version}"],
            uninstall_cmd=[fl, "pub", "remove", "{name}"],
            init_cmd=None, manifest="pubspec.yaml",
            search_url="https://pub.dev/packages?q={query}")

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\.\w*$", before)
        if m and names and m.group(1) in names:
            cls = cg.STATE_CLASS.get(names[m.group(1)], "RadControl")
            members = dict(COMMON_MEMBERS)
            members.update(TYPE_MEMBERS.get(cls, {}))
            if names[m.group(1)] == "Timer":
                members = {"enabled": "bool - running", "interval": "int - milliseconds",
                           "start()": "start the timer", "stop()": "stop the timer"}
            return [Completion(k.split("(")[0], "method" if "(" in k else "property", v) for k, v in members.items()]
        if m:
            return []
        out = super().completions(code, line, col, path, names)
        have = {c.name for c in out}
        out += [Completion(k, "function", v) for k, v in FORM_HELPERS.items() if k not in have]
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\s*\([^()]*$", before)
        if m and m.group(1) in FORM_HELPERS:
            return FORM_HELPERS[m.group(1)]
        return ""


def flutter_analyze(folder: Path, timeout: int = 300) -> tuple[int, str]:
    """Run ``flutter analyze`` (after an offline pub get when needed); (exit code, output)."""
    exe = flutter_exe()
    if not exe:
        return 1, "Flutter is not installed"
    folder = Path(folder)
    if not (folder / ".dart_tool" / "package_config.json").exists():
        pub_get(folder)
    r = subprocess.run([exe, "analyze", "--no-pub"], cwd=str(folder), capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def pub_get(folder: Path, timeout: int = 300) -> tuple[int, str]:
    """``flutter pub get --offline`` (fast, from the pub cache), online when that fails."""
    exe = flutter_exe()
    out = ""
    for args in (["pub", "get", "--offline"], ["pub", "get"]):
        r = subprocess.run([exe, *args], cwd=str(folder), capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        out += (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return 0, out
    return 1, out


def list_devices(timeout: int = 60) -> list[dict]:
    """``flutter devices --machine`` -> [{id, name, targetPlatform, emulator, ...}]."""
    exe = flutter_exe()
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "devices", "--machine"], capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return []
    text = r.stdout or ""
    i = text.find("[")
    try:
        return json.loads(text[i:]) if i >= 0 else []
    except ValueError:
        return []


PLUGIN = FlutterPlugin()
