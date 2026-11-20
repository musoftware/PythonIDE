# RAD IDE Plugin API (extension API 1.0)

RAD IDE can be extended in two ways:

1. **Extensions** - add-ons that users install with **Tools > Extensions...** (from a folder, a `.zip` or a git
   URL). They live outside the IDE's source in `%APPDATA%\RADIDE\extensions\<id>`, can be enabled, disabled and
   uninstalled at any time without a restart, and cannot break the IDE (every step is isolated). This is the
   way to share a theme, a language, a toolbox control, an AI provider or a small tool.
2. **Built-in modules** - code added to the IDE's own source tree (`radide/features/*.py`,
   `radide/languages/*.py`, ...). Use this when you contribute to RAD IDE itself.

Both use the same building blocks; the sections below show each one.

Examples: [`samples/Tests/Extensions`](../samples/Tests/Extensions/) (`SolarizedTheme` - a declarative theme
extension; `WordCountTools` - a code extension with menu commands, a dock and a status-bar item).

---

## 1. Extension layout

```
my-extension/
  radide-extension.json      required - the manifest
  extension.py               optional - code ("main"), may import sibling modules: from .helpers import x
  themes/dark-blue.json      files referenced by "contributes"
  lang/mylang.py
  ai/myprovider.py
  controls/StarRating/StarRating.form, StarRating.py
```

### 1.1 Manifest `radide-extension.json`

```json
{
  "id": "yourname.word-count",
  "name": "Word Count Tools",
  "version": "1.2.0",
  "description": "Shown in the Extensions window.",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://example.com",
  "engines": {"radide": ">=1.0"},
  "main": "extension.py",
  "contributes": {
    "themes":      [{"name": "Ocean", "file": "themes/ocean.json"}],
    "languages":   [{"module": "lang/mylang.py"}],
    "aiProviders": [{"module": "ai/echo.py"}],
    "toolbox":     [{"name": "StarRating", "folder": "controls/StarRating"}]
  }
}
```

| Key | Rules |
|---|---|
| `id` | required, `publisher.name`, lower case letters / digits / `-` / `_`, at least one dot. It is also the install folder name. |
| `name`, `version` | required; version like `1.0`, `1.2.3`, `2.0.0-beta.1`. Installing the same `id` again replaces (upgrades) it. |
| `engines.radide` | optional; `>=1.0`. An extension that needs a newer API is refused with a clear message. |
| `main` | optional `.py` file inside the extension (see section 2). |
| `contributes` | optional; kinds: `themes`, `languages`, `aiProviders`, `toolbox`, `snippets` (reserved). Every path is relative and must stay inside the extension. |

The manifest is validated on install; all problems are listed at once.

### 1.2 Install, enable, disable, uninstall

- **Tools > Extensions...**: *Install from Folder* (the folder with the manifest, or a folder whose only
  sub-folder has it), *Install from Zip* (`.zip` / `.radext`; checked against path traversal and a 200 MB limit),
  *Install from Git URL* (`git clone --depth 1` of an `https://`, `ssh://`, `git@` or `file://` URL; `.git` is not
  copied). The window shows id, version, author, description, contributions, the install source, the folder and
  every error of the extension; buttons Enable/Disable, Uninstall, Open Folder, Add Control to Project.
- Disabled extensions are listed in `%APPDATA%\RADIDE\extensions\extensions.json` (`{"disabled": [ids]}`).
- `RADIDE_EXTENSIONS_DIR=<folder>` uses another extensions folder (tests, portable setups).
- `RADIDE_SAFE_MODE=1` starts the IDE without any extension.
- From Python (scripts, tests): `from radide import extensions as X` - `X.install(path_or_url)`,
  `X.install_from_folder/zip/git`, `X.set_enabled(id, flag, win)`, `X.uninstall(id)`, `X.installed()`,
  `X.get(id)`, `X.load(id, win)` (apply a just-installed extension), `X.validate_manifest(dict, folder)`.

### 1.3 Loading and error isolation

`radide/features/__init__.py` `install_all(win)` runs:
1. `extensions.preload(win)` - **before** the built-in features: registers themes, languages and AI providers
   of every enabled extension (so the Options dialog, the View menu, New Project and the AI pickers list them);
2. the built-in features (`radide/features/*.py`);
3. `extensions.activate_all(win)` - **after** them: imports each enabled extension's `main` and calls
   `activate(api)`.

Each contribution and each activation runs in its own `try/except`: an exception is stored in the extension's
error list (shown in the Extensions window) and written to the Output window; whatever the extension had already
added through `api` is removed again; the other extensions and the IDE keep running. Exceptions raised later by
commands registered with `api.add_action` are caught the same way.

**Security:** extensions are normal Python code with the user's permissions (like VS Code extensions). The
install dialogs say so; install only extensions from sources you trust.

---

## 2. Code extensions: `activate(api)`

```python
# extension.py
from PyQt6.QtWidgets import QLabel, QMessageBox

def activate(api):
    api.add_action("Tools/My Tools", "Say Hello", lambda: QMessageBox.information(api.win, "Hi", "Hello!"),
                   shortcut="Ctrl+Alt+H")
    label = api.theme.role(QLabel("ready"), "muted")     # themed, follows theme changes
    api.add_status_widget(label)
    api.log("My Tools ready")

def deactivate():           # optional: called on Disable / Uninstall, before the automatic cleanup
    pass
```

A `main` module may instead define `install(win)` - the built-in feature contract (section 7) - but then nothing
is removed automatically on Disable; prefer `activate(api)`.

### 2.1 The `api` object (`radide/extensions/api.py`)

| Member | Purpose |
|---|---|
| `api.win` | the main window (`radide.app.MainWindow`, members listed in docs/CONTRACTS.md section 0: `project`, `docs`, `log`, `open_file`, `open_code`, `_current_code()`, `save_all()`, docks ...) |
| `api.id`, `api.path`, `api.manifest`, `api.version` | the extension's id, install folder (`Path`), manifest dict, API version `"1.0"` |
| `api.settings` | `QSettings` group `extensions/<id>` for the extension's own options |
| `api.log(text)` / `api.status(text)` | Output window line / status-bar message |
| `api.menu(path)` | the menu `"Tools"`, `"Tools/My Sub Menu"` ... (created before *Help* when missing) |
| `api.add_action(menu_path, text, callback, shortcut=None, status_tip="", icon=None)` | a menu command (also found by the Command Palette, Ctrl+Shift+P) |
| `api.add_toolbar_action(text, callback, icon=None, tooltip="")` | a main tool-bar button |
| `api.add_dock(title, widget, area="right"|"left"|"bottom"|"top", object_name="")` | a tool window; `"bottom"` is tabbed with Output |
| `api.add_status_widget(widget, permanent=True)` | a status-bar widget |
| `api.connect(signal, slot)` | connect to any IDE signal; disconnected on Disable |
| `api.on_theme_changed(fn)` | `fn(theme_name)` after every theme switch |
| `api.on_dispose(fn)` | `fn()` on Disable / Uninstall (stop timers, close files, kill processes) |
| `api.theme` | the `radide.theme` module (section 3.2) |
| `api.register_theme(name, data)` / `api.register_language(plugin)` / `api.register_ai_provider(provider)` | the code equivalents of the `contributes` entries |
| `api.current_editor_text()` | text of the active code editor or `None` |

Everything added through these calls is removed automatically on Disable/Uninstall; the extension's modules are
dropped from `sys.modules`, so Enable loads the current code again.

**UI rules:** never hard-code colours. Use `api.theme.color("text")`, `api.theme.role(widget, "muted" | "note" |
"success" | "error" | "link" | "heading" | "banner" | "info" | "help" | "calltip" | "stage" | "sample")`,
`api.theme.css_vars()` for HTML pages, and `api.on_theme_changed` for anything painted by hand. Give widgets
accessible names (`setAccessibleName`).

---

## 3. Themes

### 3.1 Declarative

```json
"contributes": {"themes": [{"name": "Ocean", "file": "themes/ocean.json"}]}
```

`themes/ocean.json`:

```json
{
  "base": "Dark",
  "monaco": "vs-dark",
  "colors": {"window": "#073642", "base": "#002B36", "text": "#93A1A1", "accent": "#268BD2", "status": "#268BD2"},
  "code":   {"keyword": "#859900", "string": "#2AA198", "comment": "#586E75"},
  "chrome": {"margin": "#002B36", "line_number": "#586E75"}
}
```

- `base`: `Light`, `Blue`, `Dark` or `High Contrast` (or another registered theme). Every token you leave out
  comes from the base, so a theme can change just a few colours.
- `colors`: any token of `radide/theme.py` `THEMES["Light"]` (`window base alt_base text muted button
  button_text border light mid dark_c shadow highlight highlight_text link link_visited accent accent_text title1
  title2 title_text toolbar1 toolbar2 toolbar_border bar_text menu menu_text menu_sel menu_sel_text menu_border tab
  tab_text tab_sel tab_sel_text tab_hover status status_text header header_text tooltip tooltip_text calltip
  calltip_text note banner banner_text banner_border success error info_back designer_back category_back stage
  heading disabled placeholder`), as `#RRGGBB`. Unknown tokens are rejected.
- `code`: editor token colours (`keyword builtin comment string number decorator defname operator`);
  `chrome`: editor margins (`margin margin_bp line_number breakpoint_line current_stmt caret_line`);
  `monaco`: `vs`, `vs-dark` or `hc-black`; `dark`: true/false (defaults to the base's).
- The theme appears in Tools > Options > Environment > Color theme. Themes registered at start-up are also in
  the View/layout theme menus; a theme installed while the IDE runs is in Options at once and in those menus after
  the next start. Disabling the extension while its theme is in use switches the IDE back to Light.
- The designed forms always keep the real light Windows look (`theme.FORM_STYLE`), whatever the theme.

### 3.2 `radide.theme` for code

`theme.color(token)`, `theme.current()` (dict), `theme.current_name()`, `theme.is_dark()`,
`theme.role(widget, role)`, `theme.css_vars()`, `theme.monaco_theme()`, signal `theme.changed(str)`,
`theme.apply(name)`.

---

## 4. Languages

A language is a `LanguagePlugin` instance (`radide/languages/base.py`); GUI-Bridge languages (the IDE draws the
forms, the program talks to it over stdin/stdout - docs/CONTRACTS.md section 1) subclass `BridgeLanguagePlugin`
(`radide/languages/bridgebase.py`) or `ScriptBridgePlugin` (`radide/languages/scripting_common.py`).

```json
"contributes": {"languages": [{"module": "lang/mylang.py"}]}
```

```python
# lang/mylang.py
from radide.languages.base import LanguagePlugin

class MyLangPlugin(LanguagePlugin):
    id = "mylang"                     # unique
    display_name = "MyLang"
    code_ext = ".myl"
    interpreter_names = ["mylang"]    # looked up in PATH
    keywords = ["if", "then", "end"]
    line_comments = ["#"]
    # implement what your language supports: generate_designer(form, user_code), new_code(form, is_startup),
    # handler_for / events_for, run_spec(folder, startup_form, interpreter), completions(...),
    # package_manager = PackageManager(...), exported_functions / reference_proxy (Add Reference) ...

PLUGIN = MyLangPlugin()
```

Copy a plugin of the same family as a template: `lua_bridge.py` / `ruby_bridge.py` (script bridge),
`c_bridge.py` (compiled bridge), `python_tk.py` (native GUI). A bridge plugin inside an extension must point
`client_files()` at client libraries shipped in its own folder (`Path(__file__).parent / "client"`), because
`radide/runtimes/clients/<lang>` belongs to the IDE. The id must not collide with an existing language.

**Built-in (contributing to RAD IDE):** put the module in `radide/languages/<name>.py` with `PLUGIN = ...`;
`radide/languages/__init__.py` discovers it automatically.

---

## 5. Toolbox controls

New toolbox controls are **user controls** (`radide/usercontrols.py`): a `.form` designed like a form with
`"kind": "usercontrol"` plus its declared properties and events, and a code file per language
(python-tk / python-qt generate real widgets).

```json
"contributes": {"toolbox": [{"name": "StarRating", "folder": "controls/StarRating"}]}
```

The folder holds `StarRating.form` and `StarRating.py` (the code file name of each supported language, e.g.
`StarRating.py` for python-tk and python-qt). Make them in the IDE (Project > Add User Control, design it, set
Project > User Control Properties and Events) and copy the two files. In Tools > Extensions, *Add Control to
Project...* copies them into the open project, generates the designer file and the control appears in the
Toolbox; it is then used like any user control (properties in the Properties window, events with
`self.RaiseEvent("Changed")` -> the form's `StarRating1_Changed()`).

**Built-in controls** (for the IDE itself) are `ControlType`s in `radide/controls.py` `CONTROL_TYPES`; every
language generator that should support them must be taught to emit them (see docs/CONTRACTS.md section 4).

---

## 6. AI providers

```json
"contributes": {"aiProviders": [{"module": "ai/echo.py"}]}
```

```python
# ai/echo.py
from radide.ai.providers import Provider

class EchoProvider(Provider):
    id = "echo"                  # unique provider id
    name = "Echo (example)"
    kind = "local"               # "cli" | "local" | "api" | "web"
    builtin_models = ("echo-1",)

    def _detect(self):           # fast: (available, reason / install hint)
        return True, ""

    def _run_chat(self, job, system, messages, model, opts):
        text = "You said: " + messages[-1].content
        for word in text.split(" "):
            if job.stopping:      # Stop pressed
                break
            job.emit_delta(word + " ")     # streaming
        return None               # None = the concatenated deltas

PROVIDER = EchoProvider()        # or PROVIDERS = [p1, p2]
```

`_run_chat` runs on a worker thread - never touch widgets there; use `job.emit_delta`, `job.on_abort(fn)` (close
sockets / kill processes on Stop) and `self.config(key)` / `self.set_config(key, value)` for options. The
provider shows up in Tools > Options > AI, the AI Chat picker and every `ai.default(purpose)` choice
(docs/CONTRACTS.md 9.1).

---

## 7. Built-in feature modules (contributing to the IDE)

A file `radide/features/<name>.py` that defines `install(win)` is loaded at start-up (alphabetical order) by
`radide/features/__init__.py`; an exception is logged to the Output window and the IDE continues.

```python
# radide/features/hello.py
from PyQt6.QtGui import QAction

def install(win) -> None:
    act = QAction("Say &Hello", win)
    act.triggered.connect(lambda: win.log("Hello"))
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == "Tools":
            a.menu().addAction(act)
```

Rules (docs/CONTRACTS.md section 0): new features go into their own module; only small targeted edits in shared
files; all UI uses `radide/theme.py`; keep `python -m pyflakes radide tools` clean. Workbench views (VS Code
activity bar / side bar) are registered with `radide.features.workbench.register_view`.

---

## 8. Testing an extension

```python
import os, sys
os.environ.update(QT_QPA_PLATFORM="offscreen", RADIDE_EXTENSIONS_DIR=r"C:\temp\ext-test")
import PyQt6.QtWebEngineWidgets                       # before QApplication
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication
QCoreApplication.setOrganizationName("RADIDE-TEST"); QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
from radide import extensions as X
X.install_from_folder("my-extension")                 # before the window: like an installed extension
from radide.app import MainWindow
win = MainWindow()
ext = X.get("yourname.my-extension")
assert ext.active and not ext.errors, ext.errors
X.set_enabled(ext.id, False, win)                      # everything it added is gone
```

---

## 9. Version history

| API | Changes |
|---|---|
| 1.0 | First version: manifest, themes, languages, AI providers, toolbox user controls, `activate(api)` with menus, tool-bar buttons, docks, status-bar widgets, settings, signal connections and automatic cleanup; install from folder / zip / git; enable / disable / uninstall without restart; safe mode. |
