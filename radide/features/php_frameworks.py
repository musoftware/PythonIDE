"""PHP frameworks in the IDE: Laravel (engine ``radide/web_site/frameworks/laravel.py``) and CodeIgniter
(``frameworks/codeigniter.py``) - the PhpStorm / "Laravel extension pack" experience.

- **IntelliSense from the project** (framework-aware, rebuilt when the project files change): a completion
  source merged into the language server's results (``MonacoEditor.completion_providers`` - intelephense items
  with the same label are dropped, framework strings show only framework items) for PHP and Blade files, and
  F12 / Ctrl+click on route / view / config / translation / env / asset strings and ``<x-components>``.
  A framework module plugs in with ``complete_items(folder, path, text, line, col) -> list | None`` and
  ``definition(folder, path, text, line, col) -> (file, line) | None``; ``common.framework_of(folder)`` picks it.
- **Blade**: ``*.blade.php`` files open in the ``blade`` Monaco language (``radide/web/blade.js``).
- **Laravel panel** (View > Laravel, Site > Laravel): Artisan (every ``artisan list`` command with an argument /
  option form), Routes (``route:list``; double-click = the controller method), Tinker console (a persistent
  REPL in the booted app, ``laravel_repl.php``), Output. Generate IDE Helper, Migrate, Install Dependencies.
- **Opening a Laravel project** without ``vendor/`` (a clone, a sample): asks to run composer install, create
  ``.env`` + APP_KEY, the SQLite database + migrate, npm install + npm run build.
- **New Project > Web > PHP Web Site**: "Laravel App" / "Laravel API" templates (App Gallery too).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QScrollArea, QSplitter, QTabWidget, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from ..web_site.frameworks import common

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
REPL_PHP = Path(__file__).resolve().parent.parent / "web_site" / "frameworks" / "laravel_repl.php"
BLADE_TRIGGERS = ["@", "<", "-", "'", '"', ".", "$", ">", ":", " ", "/", "("]
PHP_EXTRA_TRIGGERS = ["$", ">", ":", "\\", "/", "'", '"', "*", ".", "<", "("]


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


# ============================================================================ editor integration
def editor_framework(ed) -> tuple[str, Path] | None:
    """(framework id, project folder) of the file of a Monaco editor (cached on the editor)."""
    cached = getattr(ed, "_phpfw", None)
    if cached is not None:
        return cached or None
    root = common.project_root_of(ed.path) if Path(ed.path).is_absolute() else None
    res = (common.framework_of(root), root) if root is not None else None
    ed._phpfw = res or False
    return res


def framework_items(ed, line: int, col: int) -> list[dict] | None:
    """MonacoEditor.completion_providers entry."""
    fw = editor_framework(ed)
    if fw is None or ed.language_id() not in ("php", "blade", "html"):
        return None
    mod = common.framework_module(fw[0])
    fn = getattr(mod, "complete_items", None) if mod is not None else None
    if fn is None:
        return None
    try:
        items = fn(fw[1], ed.path, ed.text(), line, col)
    except Exception as e:  # noqa: BLE001 - completion must never break typing
        print(f"[php frameworks] completion failed: {e}")
        return None
    # project items first, before the language server's ('!' sorts before 0-9 a-z), in the provider's order
    # (config keys as declared, model columns before relations ...)
    for i, it in enumerate(items or []):
        it["sortText"] = "!" + str(it.get("sortText") or f"{i:05d}")
    return items


def framework_definition(ed, line: int, col: int) -> tuple[str, int] | None:
    fw = editor_framework(ed)
    if fw is None:
        return None
    mod = common.framework_module(fw[0])
    fn = getattr(mod, "definition", None) if mod is not None else None
    if fn is None:
        return None
    try:
        return fn(fw[1], ed.path, ed.text(), line, col)
    except Exception as e:  # noqa: BLE001
        print(f"[php frameworks] definition failed: {e}")
        return None


JS_PROVIDERS = """(function () {
  if (window.__radPhpFw) return; window.__radPhpFw = true;
  const obj = window.radChannel && window.radChannel.objects.radPhpFw;
  const editor = window.radEditor;
  if (!obj) return;
  // F12: framework target first (route / view / config ... strings, <x-components>), else the normal one
  editor.addAction({ id: 'rad.phpfw.definition', label: 'Go to Definition', keybindings: [monaco.KeyCode.F12],
    run: ed => { const p = ed.getPosition();
      obj.definition(p.lineNumber - 1, p.column - 1, ok => {
        if (!ok) window.radChannel.objects.rad.jsDefinition(p.lineNumber - 1, p.column - 1); }); } });
  // Ctrl+click: a definition provider whose locations are opened by the IDE (another tab)
  ['php', 'blade'].forEach(lang => monaco.languages.registerDefinitionProvider(lang, {
    provideDefinition: (model, pos) => new Promise(res => {
      if (model !== editor.getModel()) return res(null);
      obj.target(pos.lineNumber - 1, pos.column - 1, t => {
        if (!t) return res(null);
        const r = JSON.parse(t);
        res([{ uri: monaco.Uri.parse('radopen:' + encodeURIComponent(r[0]) + '#' + r[1]),
               range: new monaco.Range(r[1], 1, r[1], 1) }]);
      }); }) }));
  if (monaco.editor.registerEditorOpener) monaco.editor.registerEditorOpener({
    openCodeEditor(source, resource, selectionOrPosition) {
      if (resource.scheme !== 'radopen') return false;
      obj.open(decodeURIComponent(resource.path), parseInt(resource.fragment || '1'));
      return true; } });
})();"""


class EditorBridge(QObject):
    """Published to each Monaco page as ``radPhpFw``."""

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor

    @pyqtSlot(int, int, result=bool)
    def definition(self, line, col):
        t = framework_definition(self.ed, line, col)
        return bool(t) and open_location(self.ed.window(), t[0], t[1])

    @pyqtSlot(int, int, result=str)
    def target(self, line, col):
        t = framework_definition(self.ed, line, col)
        return json.dumps([str(t[0]), int(t[1] or 1)]) if t else ""

    @pyqtSlot(str, int)
    def open(self, path, line):
        open_location(self.ed.window(), path, line)


def open_location(win, path, line: int) -> bool:
    opener = getattr(win, "open_file", None)
    if not callable(opener):
        return False
    try:
        opener(Path(path), int(line or 1))
        return True
    except Exception:  # noqa: BLE001
        return False


def blade_js() -> str:
    try:
        return (WEB_DIR / "blade.js").read_text(encoding="utf-8")
    except OSError:
        return ""


def on_editor_ready(ed) -> None:
    """Blade language for every *.blade.php; providers + F12 for files of framework projects."""
    try:
        is_blade = str(ed.path).lower().endswith(".blade.php")
        if is_blade:
            ed._js(blade_js())
        fw = editor_framework(ed)
        if fw is not None:
            ed._js(JS_PROVIDERS)
            QTimer.singleShot(0, lambda: _warm(fw))
        if is_blade:
            from ..monaco_editor import _path_key, language_overrides
            if not language_overrides().get(_path_key(ed.path)) and ed.language() != "blade":
                ed.set_language("blade", remember=False)
            ed._js(f"radSetTriggers('blade', {json.dumps(BLADE_TRIGGERS)});")
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[php frameworks] editor hook: {e}")


def _warm(fw) -> None:
    mod = common.framework_module(fw[0])
    idx = getattr(mod, "index", None) if mod is not None else None
    if callable(idx):
        try:
            i = idx(fw[1])
            for part in ("routes", "views", "models"):
                fn = getattr(i, part, None)
                if callable(fn):              # (CodeIgniter's index has plain attributes - already built)
                    fn()
        except Exception as e:  # noqa: BLE001
            print(f"[php frameworks] index: {e}")


# ============================================================================ project helpers
def laravel_project(win):
    """The Laravel project to work on: the active one, else the startup project, else any in the solution."""
    cands = [getattr(win, "project", None)]
    sp = getattr(win, "startup_project", None)
    if callable(sp):
        try:
            cands.append(sp())
        except Exception:  # noqa: BLE001
            pass
    cands += list(getattr(getattr(win, "sln", None), "projects", []) or [])
    for p in cands:
        folder = getattr(p, "folder", None)            # unloaded solution entries have no folder
        if folder and common.framework_of(folder) == "laravel":
            return p
    return None


def project_php(win, project) -> str:
    try:
        from .php_tools import project_php as pp
        return pp(win, project)
    except Exception:  # noqa: BLE001
        return common.project_php(project.folder)


# ============================================================================ step runner (setup)
class StepRunner(QObject):
    """Runs commands one after the other (QProcess), output to the IDE's Output window."""
    finished = pyqtSignal(bool)

    def __init__(self, win, steps: list[tuple[str, list[str], str, dict]], title: str = ""):
        super().__init__(win)
        self.win = win
        self.steps = list(steps)
        self.title = title
        self.ok = True
        self.proc: QProcess | None = None
        self.output = ""

    def start(self) -> None:
        self.win.dock_output.show()
        self._next()

    def _next(self) -> None:
        if not self.steps:
            self.win.log(f"------ {self.title}: {'done' if self.ok else 'finished with errors'} ------")
            self.finished.emit(self.ok)
            return
        title, argv, cwd, env = self.steps.pop(0)
        if callable(argv):                      # a Python step
            try:
                argv()
                self.win.log(f"[{self.title}] {title}: done")
            except Exception as e:  # noqa: BLE001
                self.ok = False
                self.win.log(f"*** [{self.title}] {title}: {e}")
            QTimer.singleShot(0, self._next)
            return
        self.win.log(f"------ {title} ------")
        p = QProcess(self)
        p.setWorkingDirectory(cwd)
        e = QProcessEnvironment.systemEnvironment()
        for k, v in (env or {}).items():
            e.insert(k, str(v))
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self._read(p))
        p.finished.connect(lambda code, _s: self._done(p, title, code))
        p.errorOccurred.connect(lambda err: self._failed(p, title, err))
        self.proc = p
        p.start(argv[0], argv[1:])

    def _read(self, p) -> None:
        text = common.ANSI.sub("", bytes(p.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n"))
        self.output += text
        self.win._append_output(text)

    def _done(self, p, title, code) -> None:
        self._read(p)
        if code != 0:
            self.ok = False
            self.win.log(f"*** {title} failed (exit code {code})")
        QTimer.singleShot(0, self._next)

    def _failed(self, p, title, err) -> None:
        if err == QProcess.ProcessError.FailedToStart:
            self.ok = False
            self.win.log(f"*** {title}: cannot start {p.program()}")
            QTimer.singleShot(0, self._next)

    def wait(self, ms: int = 1800000) -> bool:
        from PyQt6.QtCore import QElapsedTimer, QEventLoop
        from PyQt6.QtWidgets import QApplication
        t = QElapsedTimer()
        t.start()
        done = {"v": None}
        self.finished.connect(lambda ok: done.__setitem__("v", ok))
        while done["v"] is None and t.elapsed() < ms:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if self.proc is not None:
                self.proc.waitForFinished(50)
        return bool(done["v"])


def setup_steps(win, project, needs: list[str]) -> list:
    from ..web_site import php_toolchain as tc
    from ..web_site.frameworks import laravel as lv
    folder = Path(project.folder)
    php = project_php(win, project)
    env = tc.composer_env(php)
    ext = common.php_ext_args(php)
    steps = []
    if "vendor" in needs:
        argv = tc.composer_argv(["install", "--no-interaction", "--no-progress", "--no-ansi"], php)
        if argv:
            steps.append(("composer install", argv, str(folder), env))
    if "env" in needs or "key" in needs:
        def env_step():
            if not (folder / ".env").exists() and (folder / ".env.example").exists():
                (folder / ".env").write_bytes((folder / ".env.example").read_bytes())
        steps.append(("create .env from .env.example", env_step, "", {}))
        steps.append(("artisan key:generate", [php, *ext, "artisan", "key:generate", "--force", "--no-interaction"],
                      str(folder), env))
    if "database" in needs:
        def db_step():
            f = folder / "database" / "database.sqlite"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()
        steps.append(("create database/database.sqlite", db_step, "", {}))
        steps.append(("artisan migrate --seed", [php, *ext, "artisan", "migrate", "--seed", "--force",
                                                 "--no-interaction"], str(folder), env))
    npm = _npm()
    if npm and "npm" in needs:
        steps.append(("npm install", [npm, "install", "--no-audit", "--no-fund"], str(folder), env))
    if npm and ("build" in needs or "npm" in needs) and (folder / "package.json").is_file():
        steps.append(("npm run build", [npm, "run", "build"], str(folder), env))
    if "vendor" in needs and lv.composer_requires(folder, "barryvdh/laravel-ide-helper"):
        steps.append(("IDE helper files", lambda: lv.generate_ide_helper(folder, php, None), "", {}))
    return steps


def _npm() -> str:
    import shutil
    return shutil.which("npm.cmd") or shutil.which("npm") or ""


def prepare_project(win, project, ask: bool = True, wait: bool = False) -> StepRunner | None:
    """A Laravel project without vendor/ / .env / database / build: offer to set it up."""
    from ..web_site.frameworks import laravel as lv
    needs = lv.needs_setup(project.folder)
    if not needs:
        return None
    labels = {"vendor": "composer install (vendor/ is missing)", "env": "create .env and APP_KEY",
              "key": "generate APP_KEY", "database": "create the SQLite database and migrate (+ seed)",
              "npm": "npm install", "build": "npm run build (Vite assets)"}
    if ask and not _offscreen():
        msg = "This Laravel project is not ready to run yet:\n\n" + "\n".join("  - " + labels[n] for n in needs) + \
              "\n\nDo it now? (output in the Output window)"
        if QMessageBox.question(win, f"Laravel - {project.name}", msg) != QMessageBox.StandardButton.Yes:
            return None
    runner = StepRunner(win, setup_steps(win, project, needs), f"Prepare {project.name}")
    runner.finished.connect(lambda ok: _after_setup(win, project, ok))
    win._laravel_setup = runner
    runner.start()
    if wait:
        runner.wait()
    return runner


def _after_setup(win, project, ok: bool) -> None:
    try:
        win._fill_solution()
    except Exception:  # noqa: BLE001
        pass
    panel = getattr(win, "laravel_panel", None)
    if panel is not None:
        panel.sync_project(force=True)
    win.statusBar().showMessage(f"Laravel project {'ready' if ok else 'set up with errors'} - press F5 to run it", 8000)


# ============================================================================ argument form
class ArtisanForm(QWidget):
    """Arguments and options of one artisan command."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cmd: dict | None = None
        self.fields: dict[str, QWidget] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.head = QLabel("Choose a command")
        self.head.setWordWrap(True)
        lay.addWidget(self.head)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        lay.addWidget(self.scroll, 1)
        self.preview = QLineEdit()
        self.preview.setPlaceholderText("php artisan ...")
        self.preview.setToolTip("The command line that runs - you can edit it")
        lay.addWidget(self.preview)

    def set_command(self, cmd: dict | None) -> None:
        self.cmd = cmd
        self.fields.clear()
        body = QWidget()
        form = QFormLayout(body)
        if cmd is None:
            self.head.setText("Choose a command")
            self.scroll.setWidget(body)
            self.preview.clear()
            return
        self.head.setText(f"<b>{cmd['name']}</b> - {cmd.get('description', '')}")
        for a in cmd.get("arguments", []):
            e = QLineEdit()
            e.setPlaceholderText(("required" if a["required"] else "optional") + (" (several, space separated)"
                                                                                  if a["array"] else ""))
            e.setToolTip(a.get("description", ""))
            e.textChanged.connect(self.update_preview)
            form.addRow(f"{a['name']}:", e)
            self.fields[a["name"] + ("[]" if a["array"] else "")] = e
        for o in cmd.get("options", []):
            label = f"--{o['name']}" + (f"  (-{o['shortcut']})" if o.get("shortcut") else "")
            if o["value"]:
                e = QLineEdit()
                if o.get("default") not in (None, False, [], ""):
                    e.setPlaceholderText(f"default: {o['default']}")
                e.setToolTip(o.get("description", ""))
                e.textChanged.connect(self.update_preview)
                form.addRow(label + ":", e)
            else:
                e = QCheckBox(o.get("description", "")[:90])
                e.setToolTip(o.get("description", ""))
                e.toggled.connect(self.update_preview)
                form.addRow(label, e)
            self.fields["--" + o["name"]] = e
        self.scroll.setWidget(body)
        self.update_preview()

    def set_values(self, values: dict) -> None:
        for k, v in values.items():
            w = self.fields.get(k) or self.fields.get(k + "[]")
            if isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QLineEdit):
                w.setText(str(v))
        self.update_preview()

    def values(self) -> dict:
        out = {}
        for k, w in self.fields.items():
            if isinstance(w, QCheckBox):
                out[k] = w.isChecked()
            else:
                v = w.text().strip()
                out[k] = v.split() if k.endswith("[]") and v else v
        return out

    def argv(self) -> list[str]:
        from ..web_site.frameworks.laravel import artisan_argv
        if self.cmd is None:
            return []
        return artisan_argv(self.cmd["name"], self.values())

    def update_preview(self, *_a) -> None:
        self.preview.setText("php artisan " + " ".join(_quote(a) for a in self.argv()))


def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or not a) else a


# ============================================================================ Laravel panel
PRESETS = [("make:model -mcr", "make:model", {"--migration": True, "--controller": True, "--resource": True}),
           ("make:controller", "make:controller", {}), ("make:migration", "make:migration", {}),
           ("migrate", "migrate", {}), ("db:seed", "db:seed", {}), ("route:list", "route:list", {}),
           ("tinker", "tinker", {})]


class LaravelPanel(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.project = None
        self.commands: list[dict] = []
        self.proc: QProcess | None = None
        self.last_output = ""
        self.last_exit: int | None = None
        self.repl: QProcess | None = None
        self._repl_buf = ""
        self._repl_wait = False
        self.routes_data: list[dict] = []
        self._queue: list[tuple[list[str], bool]] = []   # (args, quiet) waiting for the running command
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        top = QHBoxLayout()
        self.title = QLabel("No Laravel project")
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        top.addWidget(self.title, 1)
        for text, tip, slot in (("Install Dependencies", "composer install / .env / APP_KEY / database / npm",
                                 lambda: self.project and prepare_project(self.win, self.project, ask=False)),
                                ("Migrate", "php artisan migrate", lambda: self.run_artisan(["migrate", "--force"])),
                                ("IDE Helper", "Regenerate _ide_helper.php / _ide_helper_models.php / .phpstorm.meta.php "
                                 "(laravel-ide-helper) so intelephense knows facades and models", self.ide_helper),
                                ("Refresh", "Read commands and routes again", lambda: self.refresh(force=True))):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, s=slot: s())
            top.addWidget(b)
        lay.addLayout(top)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        # ---- Artisan
        art = QWidget()
        al = QVBoxLayout(art)
        al.setContentsMargins(0, 0, 0, 0)
        pre = QHBoxLayout()
        for label, name, vals in PRESETS:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, n=name, v=vals: self.choose(n, v))
            pre.addWidget(b)
        pre.addStretch(1)
        al.addLayout(pre)
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter commands (make:, migrate, route ...)")
        self.filter.textChanged.connect(self._fill_commands)
        ll.addWidget(self.filter)
        self.cmd_list = QListWidget()
        self.cmd_list.currentItemChanged.connect(self._command_selected)
        self.cmd_list.itemDoubleClicked.connect(lambda _it: self.run_form())
        ll.addWidget(self.cmd_list, 1)
        split.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.form = ArtisanForm()
        rl.addWidget(self.form, 1)
        rb = QHBoxLayout()
        rb.addStretch(1)
        self.run_btn = QPushButton("Run")
        self.run_btn.setDefault(True)
        self.run_btn.clicked.connect(self.run_form)
        rb.addWidget(self.run_btn)
        rl.addLayout(rb)
        split.addWidget(right)
        split.setSizes([260, 420])
        al.addWidget(split, 1)
        self.tabs.addTab(art, "Artisan")
        # ---- Routes
        self.routes = QTreeWidget()
        self.routes.setHeaderLabels(["Method", "URI", "Name", "Action", "Middleware"])
        self.routes.setRootIsDecorated(False)
        self.routes.setSortingEnabled(True)
        self.routes.itemDoubleClicked.connect(lambda it, _c: self.open_route(it))
        self.routes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.routes.customContextMenuRequested.connect(self._route_menu)
        self.tabs.addTab(self.routes, "Routes")
        # ---- Tinker
        tk = QWidget()
        tl = QVBoxLayout(tk)
        tl.setContentsMargins(0, 0, 0, 0)
        self.tinker_out = QPlainTextEdit()
        self.tinker_out.setReadOnly(True)
        self.tinker_out.setMaximumBlockCount(5000)
        self.tinker_out.setStyleSheet("font-family: Consolas, 'Cascadia Mono', monospace;")
        tl.addWidget(self.tinker_out, 1)
        ti = QHBoxLayout()
        ti.addWidget(QLabel(">>>"))
        self.tinker_in = QLineEdit()
        self.tinker_in.setPlaceholderText("PHP - e.g. User::count()   $p = Post::first()   $p->title   (Up/Down = history)")
        self.tinker_in.returnPressed.connect(lambda: self.tinker(self.tinker_in.text()))
        self.tinker_in.installEventFilter(self)
        ti.addWidget(self.tinker_in, 1)
        b = QPushButton("Run")
        b.clicked.connect(lambda: self.tinker(self.tinker_in.text()))
        ti.addWidget(b)
        b = QPushButton("Restart")
        b.setToolTip("Start a new Tinker session (variables are cleared)")
        b.clicked.connect(self.restart_tinker)
        ti.addWidget(b)
        tl.addLayout(ti)
        self.history: list[str] = []
        self._hpos = 0
        self.tabs.addTab(tk, "Tinker")
        # ---- Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(10000)
        self.output.setStyleSheet("font-family: Consolas, 'Cascadia Mono', monospace;")
        self.tabs.addTab(self.output, "Output")

    # ------------------------------------------------------------ state
    def folder(self) -> Path | None:
        return Path(self.project.folder).resolve() if self.project is not None else None

    def php(self) -> str:
        return project_php(self.win, self.project) if self.project is not None else ""

    def sync_project(self, force: bool = False) -> None:
        p = laravel_project(self.win)
        if p is self.project and not force:
            return
        if p is not self.project:
            self.stop_tinker()
        self.project = p
        self.refresh(force=force)

    def refresh(self, force: bool = False) -> None:
        from ..web_site.frameworks import laravel as lv
        if self.project is None:
            self.title.setText("No Laravel project")
            self.status.setText("Open or create a Laravel project (New Project > Web > PHP Web Site > Laravel App).")
            self.commands = []
            self._fill_commands()
            self.routes.clear()
            return
        folder = self.folder()
        self.title.setText(f"Laravel {lv.laravel_version(folder)}: {self.project.name}")
        needs = lv.needs_setup(folder)
        from ..web_site import php_toolchain as tc
        php = self.php()
        self.status.setText(f"PHP {tc.php_version(php) or '?'} ({php})" +
                            (f"   |   not ready: {', '.join(needs)} - click Install Dependencies" if needs else ""))
        if "vendor" in needs:
            self.commands = []
            self._fill_commands()
            self.routes.clear()
            return
        if force or not self.commands:
            self.commands = lv.artisan_commands(folder, php)
            self._fill_commands()
        self.fill_routes()

    def _fill_commands(self, *_a) -> None:
        q = self.filter.text().strip().lower()
        cur = self.cmd_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.cmd_list.currentItem() else ""
        self.cmd_list.blockSignals(True)
        self.cmd_list.clear()
        for c in self.commands:
            if q and q not in c["name"].lower() and q not in c.get("description", "").lower():
                continue
            it = QListWidgetItem(c["name"])
            it.setToolTip(c.get("description", ""))
            it.setData(Qt.ItemDataRole.UserRole, c["name"])
            self.cmd_list.addItem(it)
            if c["name"] == cur:
                self.cmd_list.setCurrentItem(it)
        self.cmd_list.blockSignals(False)

    def command(self, name: str) -> dict | None:
        return next((c for c in self.commands if c["name"] == name), None)

    def _command_selected(self, it, _prev=None) -> None:
        self.form.set_command(self.command(it.data(Qt.ItemDataRole.UserRole)) if it is not None else None)

    def choose(self, name: str, values: dict | None = None) -> bool:
        """Select a command in the Artisan tab (and fill its form)."""
        if not self.commands:
            self.refresh(force=True)
        if name == "tinker":
            self.tabs.setCurrentIndex(2)
            self.start_tinker()
            self.tinker_in.setFocus()
            return True
        self.tabs.setCurrentIndex(0)
        self.filter.setText("")
        for i in range(self.cmd_list.count()):
            if self.cmd_list.item(i).data(Qt.ItemDataRole.UserRole) == name:
                self.cmd_list.setCurrentRow(i)
                self.form.set_values(values or {})
                return True
        return False

    # ------------------------------------------------------------ artisan
    def run_form(self) -> bool:
        text = self.form.preview.text().strip()
        if not text.startswith("php artisan "):
            return False
        from ..web_site.frameworks.backend_common import split_command, unquote_args
        args = unquote_args(split_command(text[len("php artisan "):]))
        if self.form.cmd is not None:
            missing = [a["name"] for a in self.form.cmd.get("arguments", []) if a["required"]
                       and not (self.form.values().get(a["name"]) or self.form.values().get(a["name"] + "[]"))]
            if missing:
                self.win.statusBar().showMessage(f"{self.form.cmd['name']}: enter {', '.join(missing)}", 5000)
                return False
        if args and args[0] == "tinker":
            return self.choose("tinker")
        return self.run_artisan(args)

    def run_artisan(self, args: list[str], wait: bool = False, quiet: bool = False) -> bool:
        """``php artisan <args>`` -> Output tab + Output window. Commands are queued while one runs. *quiet*
        (automatic refreshes such as ide-helper:models after migrate) keeps last_output / last_exit of the
        user's command and does not switch tabs."""
        if self.project is None:
            return False
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self._queue.append((list(args), quiet))  # runs when the current command ends
            self.win.statusBar().showMessage(f"php artisan {' '.join(args)}: queued", 4000)
            if wait:
                self.wait()
            return True
        php = self.php()
        if not php:
            self.win.log("*** PHP was not found (Tools > PHP Versions...)")
            return False
        if args and args[0] in ("migrate", "migrate:fresh", "migrate:refresh", "migrate:reset", "migrate:rollback",
                                "db:seed", "db:wipe") and "--force" not in args:
            args = [*args, "--force"]
        argv = [*common.php_ext_args(php), "artisan", *args, "--no-interaction", "--ansi"]
        if not quiet:
            self.tabs.setCurrentWidget(self.output)
            self.last_output = ""
            self.last_exit = None
        self.output.appendPlainText(f"> php artisan {' '.join(args)}")
        self.win.log(f"[artisan] php artisan {' '.join(args)}")
        p = QProcess(self)
        p.setWorkingDirectory(str(self.folder()))
        e = QProcessEnvironment.systemEnvironment()
        for k, v in common.php_env(php).items():
            e.insert(k, v)
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def read():
            text = common.ANSI.sub("", bytes(p.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n"))
            if not quiet:
                self.last_output += text
            self.output.moveCursor(self.output.textCursor().MoveOperation.End)
            self.output.insertPlainText(text)
            self.output.ensureCursorVisible()
            self.win._append_output(text)

        def done(code, _status):
            read()
            self.output.appendPlainText(f"--- exit code {code} ---\n")
            self.win.log(f"[artisan] {args[0] if args else ''}: exit code {code}")
            if not quiet:
                self.last_exit = code
                if code == 0:
                    self._after_command(args, self.last_output)
            self._next_queued()

        def failed(err):
            if err == QProcess.ProcessError.FailedToStart:
                if not quiet:
                    self.last_exit = -1
                    self.last_output = f"cannot start {php}"
                self.output.appendPlainText(f"*** cannot start {php}\n")
                self.win.log(f"*** [artisan] cannot start {php}")
                self._next_queued()
        p.readyReadStandardOutput.connect(read)
        p.finished.connect(done)
        p.errorOccurred.connect(failed)
        self.proc = p
        p.start(php, argv)
        if wait:
            self.wait()
        return True

    def _next_queued(self) -> None:
        if self._queue:
            args, quiet = self._queue.pop(0)
            self.run_artisan(args, quiet=quiet)              # at once: wait() never sees a gap

    def wait(self, ms: int = 300000) -> int | None:
        if self.proc is not None:
            from PyQt6.QtCore import QElapsedTimer, QEventLoop
            from PyQt6.QtWidgets import QApplication
            t = QElapsedTimer()
            t.start()
            while (self.proc.state() != QProcess.ProcessState.NotRunning or self._queue) and t.elapsed() < ms:
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
                self.proc.waitForFinished(50)
            QApplication.processEvents()
        return self.last_exit

    def _after_command(self, args: list[str], output: str) -> None:
        name = args[0] if args else ""
        if name.startswith("make:") or name.startswith(("install:", "vendor:publish", "breeze:")):
            created = re.findall(r"\[([^\]]+\.php)\]", output)
            try:
                self.win._fill_solution()
            except Exception:  # noqa: BLE001
                pass
            for rel in created[:4]:
                p = Path(rel) if Path(rel).is_absolute() else self.folder() / rel
                if p.is_file():
                    open_location(self.win, p, 1)
        if name.startswith(("migrate", "db:", "make:", "route:", "install:")):
            QTimer.singleShot(0, self.fill_routes)
            if name.startswith(("migrate", "make:model")) and (self.folder() / "_ide_helper_models.php").exists():
                self.run_artisan(["ide-helper:models", "--nowrite"], quiet=True)   # intelephense: new columns

    def ide_helper(self, models_only: bool = False) -> None:
        if self.project is None:
            return
        from ..web_site.frameworks import laravel as lv
        if not lv.composer_requires(self.folder(), "barryvdh/laravel-ide-helper"):
            if _offscreen() or QMessageBox.question(
                    self, "IDE Helper", "Add barryvdh/laravel-ide-helper as a dev dependency (composer require "
                    "--dev) and generate the helper files?") == QMessageBox.StandardButton.Yes:
                runner = StepRunner(self.win, [("laravel-ide-helper", lambda: lv.install_ide_helper(
                    self.folder(), self.php(), self.win.log), "", {})], "IDE Helper")
                runner.start()
            return
        if models_only:
            self.run_artisan(["ide-helper:models", "--nowrite"])
            return
        for args in (["ide-helper:generate"], ["ide-helper:models", "--nowrite"], ["ide-helper:meta"]):
            self.run_artisan(args)                # queued one after the other

    # ------------------------------------------------------------ routes
    def fill_routes(self) -> list[dict]:
        from ..web_site.frameworks import laravel as lv
        self.routes.clear()
        if self.project is None:
            return []
        rows = lv.route_list(self.folder(), self.php())
        if not rows:                                # artisan failed: the static parse still knows a lot
            rows = lv.index(self.folder()).routes()
        self.routes_data = rows
        self.routes.setSortingEnabled(False)
        for r in rows:
            it = QTreeWidgetItem([r.get("method", ""), r.get("uri", ""), r.get("name", ""),
                                  r.get("action", ""), ", ".join(r.get("middleware") or [])])
            it.setData(0, Qt.ItemDataRole.UserRole, r)
            if r.get("file"):
                it.setToolTip(3, f"{r['file']}:{r.get('line')}")
            self.routes.addTopLevelItem(it)
        self.routes.setSortingEnabled(True)
        for i in range(4):
            self.routes.resizeColumnToContents(i)
        return rows

    def open_route(self, it) -> bool:
        r = it.data(0, Qt.ItemDataRole.UserRole) or {}
        if r.get("file"):
            return open_location(self.win, r["file"], r.get("line") or 1)
        return False

    def _route_menu(self, pos) -> None:
        it = self.routes.itemAt(pos)
        if it is None:
            return
        r = it.data(0, Qt.ItemDataRole.UserRole) or {}
        m = QMenu(self)
        m.addAction("Go to Code", lambda: self.open_route(it))
        if "GET" in r.get("method", "") and "{" not in r.get("uri", ""):
            m.addAction("Open in Preview", lambda: self.open_in_preview(r.get("uri", "/")))
        from PyQt6.QtWidgets import QApplication
        if r.get("name"):
            m.addAction("Copy route('name')", lambda: QApplication.clipboard().setText(f"route('{r['name']}')"))
        m.addAction("Copy URI", lambda: QApplication.clipboard().setText(r.get("uri", "")))
        m.exec(self.routes.viewport().mapToGlobal(pos))

    def open_in_preview(self, uri: str) -> str:
        from . import web_workspace as ww
        srv = ww._ensure_server(self.win, self.project.folder)
        if srv is None:
            return ""
        url = srv.url_for(uri if uri.startswith("/") else "/" + uri)
        self.win.web_preview.open_url(url)
        return url

    # ------------------------------------------------------------ tinker
    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if obj is self.tinker_in and ev.type() == QEvent.Type.KeyPress and self.history:
            if ev.key() == Qt.Key.Key_Up:
                self._hpos = max(0, self._hpos - 1)
                self.tinker_in.setText(self.history[self._hpos])
                return True
            if ev.key() == Qt.Key.Key_Down:
                self._hpos = min(len(self.history), self._hpos + 1)
                self.tinker_in.setText(self.history[self._hpos] if self._hpos < len(self.history) else "")
                return True
        return super().eventFilter(obj, ev)

    def start_tinker(self) -> bool:
        if self.repl is not None and self.repl.state() != QProcess.ProcessState.NotRunning:
            return True
        if self.project is None or not (self.folder() / "vendor" / "autoload.php").is_file():
            self.tinker_out.appendPlainText("Tinker needs a Laravel project with vendor/ (Install Dependencies).")
            return False
        php = self.php()
        p = QProcess(self)
        p.setWorkingDirectory(str(self.folder()))
        e = QProcessEnvironment.systemEnvironment()
        for k, v in common.php_env(php).items():
            e.insert(k, v)
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._repl_read)
        p.finished.connect(lambda code, _s: self.tinker_out.appendPlainText(f"[Tinker session ended ({code})]"))
        self.repl = p
        self._repl_buf = ""
        self._repl_wait = True
        self._repl_booting = True                # the banner ends with the first __RADIDE_DONE__
        self.tinker_out.appendPlainText("Starting Tinker ...")
        p.start(php, [*common.php_ext_args(php), str(REPL_PHP), str(self.folder())])
        return True

    def _repl_read(self) -> None:
        p = self.repl
        if p is None:
            return
        self._repl_buf += bytes(p.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
        while "__RADIDE_DONE__\n" in self._repl_buf:
            chunk, self._repl_buf = self._repl_buf.split("__RADIDE_DONE__\n", 1)
            if chunk.strip():
                self.tinker_out.appendPlainText(chunk.rstrip("\n"))
            self._repl_wait = False
            if getattr(self, "_repl_booting", False):
                self._repl_booting = False
                continue
            self.last_tinker = chunk

    def tinker(self, code: str, wait: bool = False) -> str:
        code = code.strip()
        if not code:
            return ""
        if not self.start_tinker():
            return ""
        self.history.append(code)
        self._hpos = len(self.history)
        self.tinker_in.clear()
        self.tabs.setCurrentIndex(2)
        self.tinker_out.appendPlainText(">>> " + code)
        self.last_tinker = None

        def send():
            if self.repl is None or self.repl.state() == QProcess.ProcessState.NotRunning:
                self.last_tinker = ""
                return
            self._repl_wait = True
            self.repl.write((json.dumps({"code": code}) + "\n").encode("utf-8"))
        if self._repl_wait:                      # still booting: send when the banner arrived
            def later():
                if self._repl_wait and self.repl is not None and \
                        self.repl.state() != QProcess.ProcessState.NotRunning:
                    QTimer.singleShot(100, later)
                else:
                    send()
            later()
        else:
            send()
        if wait:
            from PyQt6.QtCore import QElapsedTimer, QEventLoop
            from PyQt6.QtWidgets import QApplication
            t = QElapsedTimer()
            t.start()
            while self.last_tinker is None and t.elapsed() < 60000:
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
                if self.repl is not None:
                    self.repl.waitForReadyRead(50)
            return self.last_tinker or ""
        return ""

    def stop_tinker(self) -> None:
        if self.repl is not None:
            if self.repl.state() != QProcess.ProcessState.NotRunning:
                self.repl.kill()
                self.repl.waitForFinished(3000)
            self.repl = None

    def restart_tinker(self) -> None:
        self.stop_tinker()
        self.tinker_out.clear()
        self.start_tinker()


# ============================================================================ new project dialog (options)
class LaravelOptionsDialog(QDialog):
    """Database choice for a new Laravel project (SQLite / the IDE's local MariaDB or PostgreSQL server)."""

    def __init__(self, parent=None, api: bool = False):
        super().__init__(parent)
        self.setWindowTitle("New Laravel " + ("API" if api else "App"))
        lay = QFormLayout(self)
        self.db = QComboBox()
        self.db.addItem("SQLite (database/database.sqlite - no server)", "sqlite")
        self.db.addItem("MariaDB / MySQL (the IDE's local server)", "mysql")
        self.db.addItem("PostgreSQL (the IDE's local server)", "pgsql")
        lay.addRow("Database:", self.db)
        self.helper = QCheckBox("Install laravel-ide-helper (better IntelliSense for facades and models)")
        self.helper.setChecked(True)
        lay.addRow(self.helper)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)


def local_db_connection(engine: str, database: str, log=print) -> dict | None:
    """Start the IDE's local MariaDB / PostgreSQL server (radide/web_site/dbservers.py) and create *database*
    -> {host, port, database, username, password} for Laravel's DB_* settings (None when it is not possible)."""
    try:
        from ..web_site import dbservers
    except Exception as e:  # noqa: BLE001
        log(f"[laravel] local database servers are not available: {e}")
        return None
    kind = "mysql" if engine in ("mysql", "mariadb") else "postgresql"
    srv = dbservers.servers(log=log)[kind]
    try:
        info = srv.start()
        db = re.sub(r"\W", "_", database.lower()) or dbservers.DATABASE
        try:
            conn = srv._connect() if kind == "mysql" else srv._connect(dbservers.DATABASE)
            try:
                cur = conn.cursor()
                if kind == "mysql":
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                else:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
                    if cur.fetchone() is None:
                        cur.execute(f'CREATE DATABASE "{db}"')
            finally:
                conn.close()
        except Exception as e:  # noqa: BLE001 - use the server's own database
            log(f"[laravel] cannot create database {db} ({e}); using {dbservers.DATABASE}")
            db = dbservers.DATABASE
        return {"host": info.host or "127.0.0.1", "port": info.port, "database": db, "username": info.user,
                "password": srv.password()}
    except Exception as e:  # noqa: BLE001
        log(f"[laravel] cannot start the local {srv.title} server: {e}")
        return None


def _wrap_new_project_templates(win) -> None:
    """New Project > Laravel App / API: ask for the database (SQLite / local MariaDB / PostgreSQL) first."""
    try:
        from ..web_site.project import SiteTemplate, get_template, register_template
        from ..web_site.frameworks import laravel as lv
    except Exception:  # noqa: BLE001
        return
    for tid in ("laravel", "laravel-api"):
        st = get_template(tid)
        if st is None or st.extra.get("laravel_options"):
            continue

        def create(folder, name, _inner=st.create, _api=(tid == "laravel-api")):
            opts = {"db": "sqlite", "ide_helper": True}
            if not _offscreen():
                dlg = LaravelOptionsDialog(win, api=_api)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    raise RuntimeError("cancelled")
                opts["db"] = dlg.db.currentData()
                opts["ide_helper"] = dlg.helper.isChecked()
                if opts["db"] != "sqlite":
                    conn = local_db_connection(opts["db"], name, win.log)
                    if conn is None:
                        QMessageBox.warning(win, "Laravel", "The local database server could not be started - "
                                                            "the project uses SQLite (see the Output window).")
                        opts["db"] = "sqlite"
                    else:
                        opts["db_conn"] = conn
            lv.CREATE_OPTIONS.clear()
            lv.CREATE_OPTIONS.update(opts)
            try:
                return _inner(folder, name)
            finally:
                lv.CREATE_OPTIONS.clear()
        register_template(SiteTemplate(st.id, st.title, st.description, st.plugin_ids, create, st.order, st.icon,
                                       {**st.extra, "laravel_options": True}))


# ============================================================================ install
def _merge_triggers(ed) -> None:
    """Make sure PHP editors of framework projects also trigger on '(' (route(| view(|)."""
    if editor_framework(ed) is not None and ed.language_id() == "php" and getattr(ed, "lsp", None) is not None:
        trig = ((getattr(ed.lsp, "capabilities", None) or {}).get("completionProvider") or {}).get(
            "triggerCharacters") or []
        ed._js(f"radSetTriggers('php', {json.dumps(sorted(set(trig) | set(PHP_EXTRA_TRIGGERS)))});")


def install(win) -> None:
    try:
        from ..monaco_editor import LANGUAGE_CHOICES, MonacoEditor
        MonacoEditor.channel_objects["radPhpFw"] = EditorBridge
        if on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(on_editor_ready)
        providers = getattr(MonacoEditor, "completion_providers", None)
        if providers is not None and framework_items not in providers:
            providers.append(framework_items)
        if ("Blade", "blade") not in LANGUAGE_CHOICES:
            LANGUAGE_CHOICES.append(("Blade", "blade"))
    except ImportError:                       # no QtWebEngine: the built-in editor
        pass
    try:
        from .. import icons
        icons.TEMPLATE_BADGES.setdefault("laravel", ("Lv", "#F9322C"))
        icons.TEMPLATE_BADGES.setdefault("laravel-api", ("API", "#F05340"))
    except Exception:  # noqa: BLE001
        pass
    panel = LaravelPanel(win)
    win.laravel_panel = panel
    d = QDockWidget("Laravel", win)
    d.setObjectName("LaravelPanel")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    try:
        win.tabifyDockWidget(win.dock_output, d)
    except Exception:  # noqa: BLE001
        pass
    d.hide()
    win.dock_laravel = d
    d.visibilityChanged.connect(lambda vis: vis and panel.sync_project())
    act = d.toggleViewAction()
    act.setText("Laravel Panel (Artisan, Routes, Tinker)")
    win.a_laravel = act
    _wrap_new_project_templates(win)
    win.prepare_laravel = lambda project=None, ask=True: prepare_project(win, project or laravel_project(win), ask)
    try:
        from .workbench import register_view
        register_view("laravel", "Laravel", factory=lambda w: w.dock_laravel, area="panel", order=82,
                      tooltip="Laravel: Artisan commands, routes, Tinker")
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import command_palette as cp

        def show(tab: int = 0, cmd: str = ""):
            d.show()
            d.raise_()
            panel.sync_project(force=True)
            panel.tabs.setCurrentIndex(tab)
            if cmd:
                panel.choose(cmd)
        cp.register_command("laravel.artisan", "Laravel: Run Artisan Command...", lambda: show(0), category="Laravel")
        cp.register_command("laravel.routes", "Laravel: Show Routes", lambda: show(1), category="Laravel")
        cp.register_command("laravel.tinker", "Laravel: Open Tinker", lambda: show(2, "tinker"), category="Laravel")
        cp.register_command("laravel.make-model", "Laravel: make:model -mcr", lambda: show(0, "make:model"),
                            category="Laravel")
        cp.register_command("laravel.ide-helper", "Laravel: Generate IDE Helper Files", panel.ide_helper,
                            category="Laravel")
    except Exception:  # noqa: BLE001
        pass

    def later():
        for name in ("View", "Site"):
            m = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") == name), None)
            if m is not None and act not in m.actions():
                m.addSeparator()
                m.addAction(act)
        sig = getattr(win, "web_signals", None)
        if sig is not None:
            sig.siteOpened.connect(lambda p: _site_opened(win, p))
    QTimer.singleShot(0, later)
    try:
        from ..monaco_editor import MonacoEditor
        MonacoEditor.ready_hooks.append(lambda ed: QTimer.singleShot(1500, lambda: _safe(_merge_triggers, ed)))
    except ImportError:
        pass
    timer = QTimer(win)
    timer.setInterval(2000)
    timer.timeout.connect(lambda: d.isVisible() and panel.sync_project())
    timer.start()
    win._laravel_timer = timer
    try:
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(panel.stop_tinker)
    except Exception:  # noqa: BLE001
        pass


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:  # noqa: BLE001 - the editor may be gone
        pass


def _site_opened(win, project) -> None:
    if project is None or common.framework_of(project.folder) != "laravel":
        return
    folder = Path(project.folder)
    from ..web_site.frameworks import laravel as lv
    QTimer.singleShot(0, lambda: _warm(("laravel", folder)))
    if win.project is project:
        for rel in ("routes/web.php", "routes/api.php"):
            if (folder / rel).is_file():
                QTimer.singleShot(0, lambda r=rel: open_location(win, folder / r, 1))
                break
    if lv.needs_setup(folder) and not getattr(project, "_laravel_asked", False):
        project._laravel_asked = True
        if not _offscreen():
            QTimer.singleShot(300, lambda: prepare_project(win, project, ask=True))
    panel = win.laravel_panel
    panel.sync_project(force=True)
    if not getattr(win, "_laravel_shown", False):
        win._laravel_shown = True
        win.dock_laravel.show()


__all__ = ["ArtisanForm", "EditorBridge", "LaravelPanel", "StepRunner", "editor_framework", "framework_definition",
           "framework_items", "install", "laravel_project", "on_editor_ready", "prepare_project"]
