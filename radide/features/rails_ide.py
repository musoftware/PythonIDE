"""Ruby on Rails in the IDE - the RubyMine / "Rails extension pack" experience (engine:
``radide/web_site/frameworks/rails_index.py``, run / tools: ``rails.py``, menus: the Rails project-actions provider
in ``radide/project_actions_providers/java_ruby.py``).

- **IntelliSense from the project**, merged with ruby-lsp's items (``MonacoEditor.completion_providers``): route
  helpers (``*_path`` / ``*_url`` from ``bin/rails routes``, refreshed when ``config/routes.rb`` changes), model
  columns (``db/schema.rb``) and associations after ``Model.`` / ``record.`` / ``@records.each do |r|``, views and
  partials for ``render``, controller actions (``to: "c#a"``, ``before_action :``), i18n keys for ``t("``,
  ``ENV["``, helpers, ``@vars`` of the controller action in its view; F12 / Ctrl+click on a route helper, a
  ``render "x"``, a model name, a column, an association or a ``@var`` opens its definition.
- **ERB**: ``*.erb`` files open in the ``erb`` Monaco language (``radide/web/erb.js``: HTML + Ruby inside
  ``<% %>``); completions inside ``<%= %>`` are the Rails ones above (the HTML server's items elsewhere).
- **Rails panel** (View > Rails Panel; Rails menu > Console / Routes): *Console* - a persistent ``rails console``
  (``rails_repl.rb`` under ``bin/rails runner``: Ruby with the app loaded, SQL logged), *Routes* (double-click =
  the controller action, right-click = open a GET route in the Preview), *Models* (columns + associations).
- **Credentials**: Rails menu > Edit Credentials decrypts ``config/credentials.yml.enc`` into an editor tab;
  saving it encrypts it again (``Rails.application.credentials.write``).
- **First run**: opening a Rails project that is not ready (New Project, a clone) offers to install what is
  missing - the DevKit, the rails gem, ``rails new``, ``bundle install``, ``db:prepare`` - with the progress in the
  Output window. **Databases**: the app's SQLite database (or its MySQL / PostgreSQL database from
  ``config/database.yml``) is added to the Databases workspace.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from ..web_site.frameworks import rails_index as ri

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
REPL_RB = Path(__file__).resolve().parent.parent / "web_site" / "frameworks" / "rails_repl.rb"
ERB_TRIGGERS = [".", "@", '"', "'", ":", "<", "_", "/", "(", " ", "%", "="]
RUBY_EXTRA_TRIGGERS = [".", "@", '"', "'", ":", "(", "_", "/"]
REPL_MARK = "\x01RADREPL"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


# ============================================================================ editor integration
def editor_rails_root(ed) -> Path | None:
    cached = getattr(ed, "_rails_root", None)
    if cached is not None:
        return cached or None
    root = ri.rails_root_of(ed.path) if Path(ed.path).is_absolute() else None
    ed._rails_root = root or False
    return root


def rails_items(ed, line: int, col: int) -> list[dict] | None:
    """MonacoEditor.completion_providers entry: Rails items for Ruby / ERB files of a Rails app."""
    if ed.language_id() not in ("ruby", "erb", "html"):
        return None
    root = editor_rails_root(ed)
    if root is None:
        return None
    try:
        items = ri.complete_items(root, ed.path, ed.text(), line, col)
    except Exception as e:  # noqa: BLE001 - completion must never break typing
        print(f"[rails] completion failed: {e}")
        return None
    for i, it in enumerate(items or []):
        it["sortText"] = "!" + str(it.get("sortText") or f"{i:05d}")
    return items


def rails_definition(ed, line: int, col: int) -> tuple[str, int] | None:
    root = editor_rails_root(ed)
    if root is None:
        return None
    try:
        return ri.definition(root, ed.path, ed.text(), line, col)
    except Exception as e:  # noqa: BLE001
        print(f"[rails] definition failed: {e}")
        return None


JS_PROVIDERS = """(function () {
  if (window.__radRails) return; window.__radRails = true;
  const obj = window.radChannel && window.radChannel.objects.radRails;
  const editor = window.radEditor;
  if (!obj) return;
  // F12: the Rails target first (route helper, render "x", model, column, @var ...), else the normal one
  editor.addAction({ id: 'rad.rails.definition', label: 'Go to Definition', keybindings: [monaco.KeyCode.F12],
    run: ed => { const p = ed.getPosition();
      obj.definition(p.lineNumber - 1, p.column - 1, ok => {
        if (!ok) window.radChannel.objects.rad.jsDefinition(p.lineNumber - 1, p.column - 1); }); } });
  ['ruby', 'erb'].forEach(lang => monaco.languages.registerDefinitionProvider(lang, {
    provideDefinition: (model, pos) => new Promise(res => {
      if (model !== editor.getModel()) return res(null);
      obj.target(pos.lineNumber - 1, pos.column - 1, t => {
        if (!t) return res(null);
        const r = JSON.parse(t);
        res([{ uri: monaco.Uri.parse('radrails:' + encodeURIComponent(r[0]) + '#' + r[1]),
               range: new monaco.Range(r[1], 1, r[1], 1) }]);
      }); }) }));
  if (monaco.editor.registerEditorOpener) monaco.editor.registerEditorOpener({
    openCodeEditor(source, resource) {
      if (resource.scheme !== 'radrails') return false;
      obj.open(decodeURIComponent(resource.path), parseInt(resource.fragment || '1'));
      return true; } });
})();"""


class EditorBridge(QObject):
    """Published to each Monaco page as ``radRails``."""

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor

    @pyqtSlot(int, int, result=bool)
    def definition(self, line, col):
        t = rails_definition(self.ed, line, col)
        return bool(t) and open_location(self.ed.window(), t[0], t[1])

    @pyqtSlot(int, int, result=str)
    def target(self, line, col):
        t = rails_definition(self.ed, line, col)
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


def erb_js() -> str:
    try:
        return (WEB_DIR / "erb.js").read_text(encoding="utf-8")
    except OSError:
        return ""


def on_editor_ready(ed) -> None:
    """ERB language for every *.erb; Rails providers + F12 for Ruby / ERB files of Rails apps."""
    try:
        is_erb = str(ed.path).lower().endswith((".erb", ".rhtml"))
        if is_erb:
            ed._js(erb_js())
            from ..monaco_editor import _path_key, language_overrides
            if not language_overrides().get(_path_key(ed.path)):
                if ed.language() != "erb":
                    ed.set_language("erb", remember=False)
                else:
                    ed._js("radSetLanguage('erb');")
            ed._js(f"radSetTriggers('erb', {json.dumps(ERB_TRIGGERS)});")
        root = editor_rails_root(ed)
        if root is not None and (is_erb or ed.language_id() == "ruby"):
            ed._js(JS_PROVIDERS)
            QTimer.singleShot(0, lambda: _warm(root))
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[rails] editor hook: {e}")


def _merge_triggers(ed) -> None:
    """Ruby editors of Rails apps also trigger on '(' / '_' (render(| / new_|) besides ruby-lsp's characters."""
    if editor_rails_root(ed) is None or ed.language_id() != "ruby":
        return
    trig = []
    if getattr(ed, "lsp", None) is not None:
        trig = ((getattr(ed.lsp, "capabilities", None) or {}).get("completionProvider") or {}).get(
            "triggerCharacters") or []
    ed._js(f"radSetTriggers('ruby', {json.dumps(sorted(set(trig) | set(RUBY_EXTRA_TRIGGERS)))});")


def _warm(root: Path) -> None:
    try:
        idx = ri.index(root)
        idx.models()
        idx.controllers()
        idx.views()
        idx.schema()
        idx.routes()                       # starts bin/rails routes in the background when needed
    except Exception as e:  # noqa: BLE001
        print(f"[rails] index: {e}")


# ============================================================================ project helpers
def is_rails_project(project) -> bool:
    folder = getattr(project, "folder", None) if project is not None else None
    if not folder:
        return False
    try:
        return ri.is_rails(Path(folder))
    except (OSError, TypeError, ValueError):
        return False


def is_rails_template(project) -> bool:
    """A rails-web project made from the "Ruby on Rails App" template (maybe still empty)."""
    if project is None or getattr(project, "language", "") != "rails-web":
        return False
    try:
        from ..web_site.frameworks.rails import RailsPlugin
        return RailsPlugin.kind_of(project) == "rails"
    except Exception:  # noqa: BLE001
        return False


def rails_project(win, project=None):
    if project is not None:
        return project if is_rails_project(project) else None
    cands = [getattr(win, "project", None)]
    try:
        from .web_workspace import _site_project
        cands.insert(0, _site_project(win))
    except Exception:  # noqa: BLE001
        pass
    for st in list((getattr(win, "_pstates", None) or {}).values()):       # the projects opened in the solution
        if isinstance(st, dict) and st.get("project") is not None:
            cands.append(st["project"])
    for p in cands:
        if is_rails_project(p):
            return p
    return None


def ruby_tools():
    from ..web_site.frameworks import rails as rl
    return rl


def needs_setup(project) -> list[str]:
    """What a Rails project lacks before it can run: devkit, rails, new, bundle, db."""
    rl = ruby_tools()
    f = Path(project.folder)
    out = []
    has_app = (f / "config" / "application.rb").is_file()
    if not has_app:
        if not rl.devkit_installed():
            out.append("devkit")
        if not rl.rails_bin():
            out.append("rails")
        out.append("new")
    bundled = (f / "Gemfile.lock").is_file() and (f / "vendor" / "bundle").is_dir()
    if not has_app or not bundled:
        if has_app and not rl.devkit_installed() and _has_native_gems(f):
            out.append("devkit")
        out.append("bundle")
    yml = ri.read_text(f / "config" / "database.yml")
    sqlite = not has_app or "sqlite3" in yml
    if not has_app or (sqlite and not any((f / "storage" / n).is_file() for n in ("development.sqlite3",))):
        out.append("db")
    return out


def _has_native_gems(folder: Path) -> bool:
    lock = ri.read_text(folder / "Gemfile.lock")
    return any(g in lock for g in ("puma (", "nio4r", "bigdecimal", "sqlite3 (", "bootsnap", "msgpack", "date ("))


def setup_steps(win, project, needs: list[str], db: str = "") -> list:
    rl = ruby_tools()
    plugin = rl.PLUGIN
    folder = Path(project.folder)
    ruby = rl.ruby_exe() or "ruby"
    env = rl.ruby_env(folder)
    steps = []
    if "devkit" in needs:
        steps.append(("Install the DevKit (MSYS2 + gcc, ~400 MB, first time only)", plugin._installer_argv("devkit"),
                      str(folder), env))
    if "rails" in needs:
        steps.append(("gem install rails (private GEM_HOME, first time only)", plugin._installer_argv("rails"),
                      str(folder), env))
    if "new" in needs:
        db = db or str(_web_cfg(project).get("rails_db") or "sqlite3")
        flags = [f for f in rl.RAILS_NEW_FLAGS if not f.startswith("--database")] + [f"--database={db}"]
        keep = folder / "project.radproj"
        saved = keep.read_bytes() if keep.is_file() else None

        def restore_radproj():
            if saved is not None and (not keep.is_file() or keep.read_bytes() != saved):
                keep.write_bytes(saved)
        steps.append((f"rails new . ({db})", [ruby, str(rl.RAILS_GEM_HOME / "bin" / "rails"), "new", ".", "--force",
                                               *flags], str(folder), env))
        steps.append(("keep project.radproj", restore_radproj, "", {}))
        if db in ("postgresql", "mysql", "trilogy"):
            steps.append((f"local {db} server", lambda: configure_local_db(win, project, db), "", {}))
    if "bundle" in needs or "new" in needs:
        steps.append(("bundle config set --local path vendor/bundle",
                      [ruby, "-S", "bundle", "config", "set", "--local", "path", "vendor/bundle"], str(folder), env))
        steps.append(("bundle install", [ruby, "-S", "bundle", "install"], str(folder), env))
    if "db" in needs or "new" in needs:
        steps.append(("bin/rails db:prepare", [ruby, "bin/rails", "db:prepare"], str(folder), env))
    return steps


def _web_cfg(project) -> dict:
    try:
        from ..web_site.project import web_config
        return web_config(project)
    except Exception:  # noqa: BLE001
        return {}


def prepare_project(win, project, ask: bool = True, wait: bool = False, db: str = ""):
    """Offer to install what a Rails project needs (output in the Output window). Returns the StepRunner."""
    needs = needs_setup(project)
    if not needs:
        return None
    labels = {"devkit": "install the RubyInstaller DevKit (MSYS2 + gcc, about 400 MB, once per user)",
              "rails": "gem install rails (once per user)", "new": "rails new . (make the application)",
              "bundle": "bundle install (the app's gems into vendor/bundle)",
              "db": "bin/rails db:prepare (create + migrate the database)"}
    if ask and not _offscreen():
        msg = (f"The Rails project '{project.name}' is not ready to run yet:\n\n" +
               "\n".join("  - " + labels[n] for n in needs) + "\n\nDo it now? (progress in the Output window)")
        if QMessageBox.question(win, "Ruby on Rails", msg) != QMessageBox.StandardButton.Yes:
            return None
    from .php_frameworks import StepRunner
    runner = StepRunner(win, setup_steps(win, project, needs, db), f"Prepare Rails app {project.name}")
    runner.finished.connect(lambda ok: _after_setup(win, project, ok))
    win._rails_setup = runner
    win.log(f"------ Preparing the Rails app '{project.name}': {', '.join(needs)} ------")
    runner.start()
    if wait:
        runner.wait(3600 * 1000)
    return runner


def _after_setup(win, project, ok: bool) -> None:
    try:
        win._fill_solution()
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..project_actions import clear_cache
        clear_cache()
        pm = getattr(win, "project_menus", None)
        if pm is not None and callable(getattr(pm, "rebuild", None)):
            pm.rebuild()
    except Exception:  # noqa: BLE001
        pass
    if ok:
        ensure_database(win, project)
        QTimer.singleShot(0, lambda: _warm(Path(project.folder)))
    panel = getattr(win, "rails_panel", None)
    if panel is not None:
        panel.set_project(project, force=True)
    win.statusBar().showMessage(f"Rails app {'ready' if ok else 'set up with errors (see Output)'} - press F5 to "
                                "run it with the debugger", 10000)


# ============================================================================ databases
def database_config(folder: Path, env: str = "development") -> dict:
    """The *env* section of config/database.yml (simple YAML: anchors / <<: *default merged)."""
    text = ri.read_text(folder / "config" / "database.yml")
    sections: dict[str, dict] = {}
    anchors: dict[str, dict] = {}
    cur = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\w+):\s*(&(\w+))?\s*$", raw)
        if m:
            cur = sections.setdefault(m.group(1), {})
            if m.group(3):
                anchors[m.group(3)] = cur
            continue
        if cur is None:
            continue
        m = re.match(r"^\s+<<:\s*\*(\w+)", raw)
        if m:
            cur.update({k: v for k, v in anchors.get(m.group(1), {}).items() if k not in cur})
            continue
        m = re.match(r"^\s{2}(\w+):\s*(.*?)\s*$", raw)
        if m:
            cur[m.group(1)] = m.group(2).strip("'\"")
    out = dict(sections.get(env) or {})
    return out


def ensure_database(win, project) -> None:
    """The app's development database as a connection of the Databases workspace."""
    panel = getattr(win, "databases", None)
    if panel is None or project is None:
        return
    folder = Path(project.folder)
    cfg = database_config(folder)
    adapter = cfg.get("adapter", "")
    try:
        from ..web_site import databases as D
        if adapter.startswith("sqlite") or not adapter:
            db = folder / (cfg.get("database") or "storage/development.sqlite3")
            if db.is_file() and db.stat().st_size > 0:
                panel.add_sqlite(db, project=project, name="development")
        elif adapter in ("mysql2", "trilogy", "postgresql"):
            kind = "postgresql" if adapter == "postgresql" else "mysql"
            m = panel.manager_for(project)
            if not any(c.kind == kind and c.database == cfg.get("database") for c in m.connections):
                info = D.ConnectionInfo("development", kind, host=cfg.get("host") or "127.0.0.1",
                                        port=int(cfg.get("port") or 0), user=cfg.get("username") or "",
                                        database=cfg.get("database") or "")
                panel.add_connection(info, password=cfg.get("password") or "", project=project)
        panel.refresh()
    except Exception as e:  # noqa: BLE001 - never break the IDE
        win.log(f"[rails] cannot add the app's database to Databases: {e}")


def configure_local_db(win, project, db: str) -> None:
    """New app with MySQL / PostgreSQL: start the IDE's local server and write its connection into
    config/database.yml (development + test)."""
    from .php_frameworks import local_db_connection
    engine = "postgresql" if db == "postgresql" else "mysql"
    conn = local_db_connection(engine, f"{project.name}_development", win.log)
    if conn is None:
        raise RuntimeError(f"the local {engine} server could not be started - edit config/database.yml")
    f = Path(project.folder) / "config" / "database.yml"
    text = ri.read_text(f)
    lines = [f"  host: {conn['host']}", f"  port: {conn['port']}", f"  username: {conn['username']}",
             f"  password: \"{conn['password']}\""]
    text = re.sub(r"(^default:\s*&default\s*\n)", lambda m: m.group(1) + "\n".join(lines) + "\n", text, count=1,
                  flags=re.M)
    text = re.sub(r"^(development:\s*\n(?:\s+.*\n)*?\s+database:\s*)\S+", lambda m: m.group(1) + conn["database"],
                  text, count=1, flags=re.M)
    f.write_text(text, encoding="utf-8", newline="\n")
    win.log(f"[rails] config/database.yml: {engine} on {conn['host']}:{conn['port']} database {conn['database']}")


# ============================================================================ credentials
def edit_credentials(win, project, folder=None) -> bool:
    """Decrypt config/credentials.yml.enc (credentials:show) into an editor tab; saving it encrypts it back."""
    folder = Path(folder or project.folder)
    rl = ruby_tools()
    ruby = rl.ruby_exe()
    if not ruby:
        win.log("*** Ruby was not found")
        return False
    tmpdir = Path(tempfile.gettempdir()) / "radide-rails-credentials"
    tmpdir.mkdir(parents=True, exist_ok=True)
    target = tmpdir / f"{project.name if project is not None else folder.name}.credentials.yml"
    code, out = rl.run([ruby, "bin/rails", "credentials:show"], cwd=folder, env=rl.ruby_env(folder), timeout=120)
    if code != 0:
        if "Missing" in out or "doesn't exist" in out or not (folder / "config" / "credentials.yml.enc").exists():
            out = "# Rails credentials (encrypted into config/credentials.yml.enc when you save)\n" \
                  "# secret_key_base is made by Rails when it is missing.\n"
        else:
            win.log(out)
            win.log("*** bin/rails credentials:show failed (config/master.key missing or wrong?)")
            return False
    target.write_text(out if out.endswith("\n") else out + "\n", encoding="utf-8", newline="\n")
    watcher = _CredentialsWatcher(win, folder, target)
    win._rails_credentials = watcher
    open_location(win, target, 1)
    win.log(f"[rails] credentials opened in {target.name} - save (Ctrl+S) to encrypt them into "
            "config/credentials.yml.enc (the decrypted copy is deleted when its tab is closed or the IDE quits)")
    return True


class _CredentialsWatcher(QObject):
    WRITE = ("content = File.read(ARGV[0]); "
             "Rails.application.credentials.write(content); puts 'credentials saved'")

    def __init__(self, win, folder: Path, target: Path):
        super().__init__(win)
        self.win, self.folder, self.target = win, folder, target
        self.mtime = target.stat().st_mtime
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(1000)
        self.closed_polls = 0

    def check(self):
        if not self.target.exists():
            self.timer.stop()
            return
        m = self.target.stat().st_mtime
        if m != self.mtime:
            self.mtime = m
            self.encrypt()
        if self.win._editor_for_file(str(self.target)) is None:
            self.closed_polls += 1
            if self.closed_polls > 3:                 # the tab was closed: remove the decrypted copy
                self.timer.stop()
                try:
                    self.target.unlink()
                except OSError:
                    pass
        else:
            self.closed_polls = 0

    def encrypt(self) -> bool:
        rl = ruby_tools()
        code, out = rl.run([rl.ruby_exe(), "bin/rails", "runner", self.WRITE, str(self.target)], cwd=self.folder,
                           env=rl.ruby_env(self.folder), timeout=120)
        self.win.log(("[rails] config/credentials.yml.enc updated" if code == 0 and "credentials saved" in out
                      else f"*** saving the credentials failed:\n{out[-1500:]}"))
        return code == 0


# ============================================================================ Rails panel
class RailsPanel(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.project = None
        self.repl: QProcess | None = None
        self._repl_buf = ""
        self.last_answer: dict | None = None
        self.ready = False
        self.history: list[str] = []
        self._hpos = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        top = QHBoxLayout()
        self.title = QLabel("No Rails application")
        top.addWidget(self.title, 1)
        for text, fn in (("Server", self._server), ("Migrate", self._migrate), ("Refresh", lambda: self.refresh(True))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        # console
        con = QWidget()
        cl = QVBoxLayout(con)
        cl.setContentsMargins(0, 0, 0, 0)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        mono = QFont("Consolas", 10)
        self.out.setFont(mono)
        cl.addWidget(self.out, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(">>"))
        self.inp = QLineEdit()
        self.inp.setFont(mono)
        self.inp.setPlaceholderText("Ruby with the app loaded: Product.count, Product.first, Product.create!(name: "
                                    "\"x\") ...  (Enter = run, Up/Down = history)")
        self.inp.returnPressed.connect(lambda: self.eval(self.inp.text()))
        self.inp.installEventFilter(self)
        row.addWidget(self.inp, 1)
        b = QPushButton("Restart")
        b.clicked.connect(self.restart_console)
        row.addWidget(b)
        cl.addLayout(row)
        self.tabs.addTab(con, "Console")
        # routes
        rw = QWidget()
        rl_ = QVBoxLayout(rw)
        rl_.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter routes (path, helper, controller#action)")
        self.filter.textChanged.connect(self._apply_filter)
        rl_.addWidget(self.filter)
        self.routes = QTreeWidget()
        self.routes.setHeaderLabels(["Verb", "Path", "Helper", "Controller#Action"])
        self.routes.setRootIsDecorated(False)
        self.routes.itemDoubleClicked.connect(self._open_route)
        self.routes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.routes.customContextMenuRequested.connect(self._route_menu)
        rl_.addWidget(self.routes, 1)
        self.tabs.addTab(rw, "Routes")
        # models
        self.models = QTreeWidget()
        self.models.setHeaderLabels(["Model / column / association", "Type", "Where"])
        self.models.itemDoubleClicked.connect(self._open_model_item)
        self.tabs.addTab(self.models, "Models")
        self.tabs.currentChanged.connect(lambda _i: _guard(self.refresh))

    # ------------------------------------------------------------ project
    def folder(self) -> Path | None:
        return Path(self.project.folder) if self.project is not None else None

    def set_project(self, project, force: bool = False) -> None:
        if project is self.project and not force:
            return
        if project is not self.project:
            self.stop_console()
        self.project = project
        self.title.setText(f"Rails application: {project.name}  ({project.folder})" if project is not None
                           else "No Rails application")
        self.refresh(force)

    def refresh(self, force: bool = False) -> None:
        f = self.folder()
        if f is None:
            self.routes.clear()
            self.models.clear()
            return
        idx = ri.index(f)
        if force:
            idx._runtime_stamp = None
        if self.tabs.currentIndex() == 1 or force:
            self.fill_routes()
        if self.tabs.currentIndex() == 2 or force:
            self.fill_models()

    def fill_routes(self) -> int:
        f = self.folder()
        self.routes.clear()
        if f is None:
            return 0
        idx = ri.index(f)
        if self.fill_routes not in [getattr(x, "__func__", x) for x in idx.routes_listeners] and \
                not getattr(idx, "_panel_hooked", False):
            idx._panel_hooked = True
            idx.routes_listeners.append(lambda _i: setattr(self, "_routes_dirty", True))
        rows = idx.routes()
        for r in rows:
            helper = f"{r.name}_path" if r.name else ""
            it = QTreeWidgetItem([r.verb, r.path, helper, r.handler])
            it.setData(0, Qt.ItemDataRole.UserRole, r)
            self.routes.addTopLevelItem(it)
        for i in range(4):
            self.routes.resizeColumnToContents(i)
        self._apply_filter()
        return len(rows)

    def _routes_arrived(self):
        if self.tabs.currentIndex() == 1:
            self.fill_routes()

    def _apply_filter(self, *_a):
        t = self.filter.text().lower()
        for i in range(self.routes.topLevelItemCount()):
            it = self.routes.topLevelItem(i)
            it.setHidden(bool(t) and not any(t in it.text(c).lower() for c in range(4)))

    def _open_route(self, it, _col=0) -> bool:
        r = it.data(0, Qt.ItemDataRole.UserRole)
        f = self.folder()
        if r is None or f is None:
            return False
        t = ri.index(f).route_target(r)
        return bool(t) and open_location(self.win, t[0], t[1])

    def _route_menu(self, pos):
        it = self.routes.itemAt(pos)
        if it is None:
            return
        r = it.data(0, Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        m.addAction("Go to Controller Action", lambda: self._open_route(it))
        if r.verb.startswith("GET") and ":" not in r.path:
            m.addAction("Open in Preview", lambda: self.open_in_preview(r.path))
        if r.name:
            from PyQt6.QtWidgets import QApplication
            m.addAction(f"Copy {r.name}_path", lambda: QApplication.clipboard().setText(f"{r.name}_path"))
        m.exec(self.routes.viewport().mapToGlobal(pos))

    def open_in_preview(self, path: str) -> None:
        try:
            from .web_workspace import run_website
            srv = getattr(self.win, "web_server", None)
            if srv is None or getattr(srv, "project", None) is not self.project:
                run_website(self.win, self.project, path=path)
                return
            prev = getattr(self.win, "preview", None) or getattr(self.win, "web_preview", None)
            if prev is not None and callable(getattr(prev, "load_url", None)):
                prev.load_url(srv.url.rstrip("/") + path)
        except Exception as e:  # noqa: BLE001
            self.win.log(f"*** {e}")

    def fill_models(self) -> int:
        f = self.folder()
        self.models.clear()
        if f is None:
            return 0
        idx = ri.index(f)
        n = 0
        for name, md in sorted(idx.models().items()):
            if name != md.name:
                continue
            top = QTreeWidgetItem([name, md.table, f"app/models/{md.file.name}:{md.line}"])
            top.setData(0, Qt.ItemDataRole.UserRole, (str(md.file), md.line))
            self.models.addTopLevelItem(top)
            info = idx.schema().get(md.table) or {}
            for col, (typ, ln) in idx.columns(name).items():
                c = QTreeWidgetItem([col, typ, f"{Path(info.get('file') or 'db/schema.rb').name}:{ln}" if ln else ""])
                c.setData(0, Qt.ItemDataRole.UserRole, (info.get("file") or "", ln))
                top.addChild(c)
            for a in md.assocs.values():
                c = QTreeWidgetItem([a.name, f"{a.kind} -> {a.target}", f"{md.file.name}:{a.line}"])
                c.setData(0, Qt.ItemDataRole.UserRole, (str(md.file), a.line))
                top.addChild(c)
            n += 1
        self.models.expandAll()
        for i in range(3):
            self.models.resizeColumnToContents(i)
        return n

    def _open_model_item(self, it, _col=0):
        d = it.data(0, Qt.ItemDataRole.UserRole)
        if d and d[0]:
            open_location(self.win, d[0], d[1] or 1)

    def _server(self):
        if self.project is not None:
            from .web_workspace import run_website
            run_website(self.win, self.project)

    def _migrate(self):
        f = self.folder()
        if f is None:
            return
        rl = ruby_tools()
        self.out.appendPlainText("$ bin/rails db:migrate")
        code, out = rl.run([rl.ruby_exe(), "bin/rails", "db:migrate"], cwd=f, env=rl.ruby_env(f), timeout=600)
        self.out.appendPlainText(out.strip() or f"(exit code {code})")
        ensure_database(self.win, self.project)

    # ------------------------------------------------------------ console
    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if obj is self.inp and ev.type() == QEvent.Type.KeyPress and self.history:
            if ev.key() == Qt.Key.Key_Up:
                self._hpos = max(0, self._hpos - 1)
                self.inp.setText(self.history[self._hpos])
                return True
            if ev.key() == Qt.Key.Key_Down:
                self._hpos = min(len(self.history), self._hpos + 1)
                self.inp.setText(self.history[self._hpos] if self._hpos < len(self.history) else "")
                return True
        return super().eventFilter(obj, ev)

    def start_console(self) -> bool:
        if self.repl is not None and self.repl.state() != QProcess.ProcessState.NotRunning:
            return True
        f = self.folder()
        if f is None:
            self.out.appendPlainText("Open a Rails application first.")
            return False
        if "bundle" in needs_setup(self.project) or "new" in needs_setup(self.project):
            self.out.appendPlainText("The app's gems are not installed yet (Rails menu > Bundler > bundle install).")
            return False
        rl = ruby_tools()
        p = QProcess(self)
        p.setWorkingDirectory(str(f))
        e = QProcessEnvironment.systemEnvironment()
        for k, v in rl.ruby_env(f).items():
            e.insert(k, str(v))
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(lambda code, _s: self._ended(code))
        self.repl = p
        self._repl_buf = ""
        self.ready = False
        self.out.appendPlainText("Starting the Rails console (bin/rails runner + the IDE's REPL) ...")
        p.start(rl.ruby_exe() or "ruby", ["bin/rails", "runner", str(REPL_RB)])
        return True

    def _ended(self, code):
        self.out.appendPlainText(f"[console ended ({code})]")
        self.ready = False
        if self.last_answer is None:
            self.last_answer = {"error": f"console ended ({code})"}

    def _read(self):
        p = self.repl
        if p is None:
            return
        self._repl_buf += ANSI.sub("", bytes(p.readAllStandardOutput()).decode("utf-8", "replace")
                                   .replace("\r\n", "\n"))
        while "\n" in self._repl_buf:
            line, self._repl_buf = self._repl_buf.split("\n", 1)
            i = line.find(REPL_MARK)
            if i < 0:
                if line.strip():
                    self.out.appendPlainText(line)
                continue
            if i > 0:
                self.out.appendPlainText(line[:i])
            try:
                ans = json.loads(line[i + len(REPL_MARK):])
            except ValueError:
                continue
            if ans.get("ready"):
                self.ready = True
                self.out.appendPlainText(f"Rails {ans.get('rails')} console ({ans.get('env')}), Ruby {ans.get('ruby')} "
                                         "- local variables are kept between lines")
                continue
            if ans.get("out"):
                self.out.appendPlainText(ans["out"].rstrip("\n"))
            if "error" in ans:
                self.out.appendPlainText(f"!! {ans['error']}")
                for bt in ans.get("backtrace") or []:
                    self.out.appendPlainText(f"     {bt}")
            elif "result" in ans:
                self.out.appendPlainText(f"=> {ans['result']}")
            self.last_answer = ans

    def eval(self, code: str, wait: bool = False) -> dict | None:
        code = code.strip()
        if not code:
            return None
        if not self.start_console():
            return None
        self.history.append(code)
        self._hpos = len(self.history)
        self.inp.clear()
        self.tabs.setCurrentIndex(0)
        self.out.appendPlainText(">> " + code)
        self.last_answer = None

        def send():
            if self.repl is None or self.repl.state() == QProcess.ProcessState.NotRunning:
                self.last_answer = {"error": "console not running"}
                return
            if not self.ready:
                QTimer.singleShot(150, send)
                return
            self.repl.write((json.dumps(code) + "\n").encode("utf-8"))
        send()
        if wait:
            from PyQt6.QtCore import QElapsedTimer, QEventLoop
            from PyQt6.QtWidgets import QApplication
            t = QElapsedTimer()
            t.start()
            while self.last_answer is None and t.elapsed() < 180000:
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
                if self.repl is not None:
                    self.repl.waitForReadyRead(50)
            return self.last_answer
        return None

    def stop_console(self) -> None:
        if self.repl is not None:
            if self.repl.state() != QProcess.ProcessState.NotRunning:
                self.repl.kill()
                self.repl.waitForFinished(3000)
            self.repl = None
            self.ready = False

    def restart_console(self) -> None:
        self.stop_console()
        self.out.clear()
        self.start_console()


# ============================================================================ new project options
class RailsOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Ruby on Rails App")
        lay = QFormLayout(self)
        self.db = QComboBox()
        for label, val in (("SQLite (no server - recommended)", "sqlite3"),
                           ("PostgreSQL (the IDE's local server)", "postgresql"),
                           ("MySQL / MariaDB (the IDE's local server, trilogy driver)", "trilogy")):
            self.db.addItem(label, val)
        lay.addRow("Database:", self.db)
        note = QLabel("The first time, the IDE installs the RubyInstaller DevKit (MSYS2 + gcc) and the rails gem "
                      "for your user, then runs rails new, bundle install and db:prepare. Progress: Output window.")
        note.setWordWrap(True)
        lay.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)


NEW_OPTIONS: dict = {}       # tests: {"db": "sqlite3"} skips the dialog


def _wrap_new_project_template(win) -> None:
    try:
        from ..web_site.project import SiteTemplate, get_template, register_template
    except Exception:  # noqa: BLE001
        return
    st = get_template("rails-app")
    if st is None or st.extra.get("rails_options"):
        return

    def create(folder, name, _inner=st.create):
        db = NEW_OPTIONS.get("db", "")
        if not db and not _offscreen():
            dlg = RailsOptionsDialog(win)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                raise RuntimeError("cancelled")
            db = dlg.db.currentData()
        res = dict(_inner(folder, name) or {})
        res["rails_db"] = db or "sqlite3"
        return res
    register_template(SiteTemplate(st.id, st.title, st.description, st.plugin_ids, create, st.order, st.icon,
                                   {**st.extra, "rails_options": True}))


# ============================================================================ install
def install(win) -> None:
    try:
        from ..monaco_editor import LANGUAGE_CHOICES, MONACO_LANG, MonacoEditor
        MONACO_LANG[".erb"] = "erb"
        MONACO_LANG[".rhtml"] = "erb"
        MonacoEditor.channel_objects["radRails"] = EditorBridge
        if on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(on_editor_ready)
            MonacoEditor.ready_hooks.append(lambda ed: QTimer.singleShot(2500, lambda: _safe(_merge_triggers, ed)))
        providers = getattr(MonacoEditor, "completion_providers", None)
        if providers is not None and rails_items not in providers:
            providers.append(rails_items)
        if ("ERB (Embedded Ruby)", "erb") not in LANGUAGE_CHOICES:
            LANGUAGE_CHOICES.append(("ERB (Embedded Ruby)", "erb"))
    except ImportError:                       # no QtWebEngine: the built-in editor
        pass
    try:                                      # HTML IntelliSense in the HTML parts of ERB files
        from .. import lsp
        if "erb" not in lsp.SERVERS and "html" in lsp.SERVERS:
            lsp.SERVERS["erb"] = lsp.SERVERS["html"]
            lsp.SERVER_GROUP["erb"] = "html"
            lsp.LSP_LANGUAGE_ID["erb"] = "html"
    except Exception:  # noqa: BLE001
        pass
    try:
        from .. import icons
        icons.TEMPLATE_BADGES.setdefault("rails-app", ("Rb", "#CC0000"))
    except Exception:  # noqa: BLE001
        pass
    panel = RailsPanel(win)
    win.rails_panel = panel
    d = QDockWidget("Rails", win)
    d.setObjectName("RailsPanel")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    try:
        win.tabifyDockWidget(win.dock_output, d)
    except Exception:  # noqa: BLE001
        pass
    d.hide()
    win.dock_rails = d
    act = d.toggleViewAction()
    act.setText("Rails Panel (Console, Routes, Models)")
    win.a_rails = act

    def show(tab: int = 0, project=None) -> bool:
        p = rails_project(win, project)
        if p is None:
            return False
        panel.set_project(p)
        d.show()
        d.raise_()
        panel.tabs.setCurrentIndex(tab)
        panel.refresh(force=tab != 0)
        return True

    def open_console(project=None) -> bool:
        if not show(0, project):
            return False
        panel.start_console()
        panel.inp.setFocus()
        return True
    win.open_rails_console = open_console
    win.show_rails_routes = lambda project=None: show(1, project)
    win.edit_rails_credentials = lambda project=None, folder=None: edit_credentials(
        win, project or rails_project(win), folder)
    win.rails_db_changed = lambda project=None: ensure_database(win, project or rails_project(win))
    win.show_rails_database = lambda project=None: (ensure_database(win, project or rails_project(win)),
                                                    getattr(win, "dock_databases", None) is not None and
                                                    (win.dock_databases.show(), win.dock_databases.raise_()))
    win.rails_db_system_changed = lambda project, to: (ensure_database(win, project),
                                                       win.log(f"[rails] database system changed to {to}: check "
                                                               "config/database.yml, then Rails > Database > "
                                                               "Prepare"))
    win.prepare_rails = lambda project=None, ask=True, wait=False: prepare_project(
        win, project or getattr(win, "project", None), ask, wait)
    _wrap_new_project_template(win)
    try:
        from .workbench import register_view
        register_view("rails", "Rails", factory=lambda w: w.dock_rails, area="panel", order=83,
                      tooltip="Rails: console, routes, models")
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import command_palette as cp

        def active() -> bool:
            return rails_project(win) is not None
        for cid, title, fn in (("rails.console", "Rails: Open Console", open_console),
                               ("rails.routes", "Rails: Show Routes", lambda: show(1)),
                               ("rails.models", "Rails: Show Models", lambda: show(2)),
                               ("rails.credentials", "Rails: Edit Credentials",
                                lambda: win.edit_rails_credentials())):
            cp.register_command(cid, title, fn, category="Rails", enabled=active)
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
            sig.siteOpened.connect(lambda p: _guard(_site_opened, win, p))
    QTimer.singleShot(0, later)
    timer = QTimer(win)
    timer.setInterval(2000)
    timer.timeout.connect(lambda: _guard(_poll, win))
    timer.start()
    win._rails_timer = timer
    try:
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(panel.stop_console)
        QApplication.instance().aboutToQuit.connect(_cleanup_credentials)
    except Exception:  # noqa: BLE001
        pass


def _cleanup_credentials() -> None:
    d = Path(tempfile.gettempdir()) / "radide-rails-credentials"
    for f in d.glob("*.credentials.yml") if d.is_dir() else []:
        try:
            f.unlink()
        except OSError:
            pass


def _guard(fn, *a):
    """Run a slot body: an exception escaping a Qt slot / timer callback aborts the whole process (PyQt6
    qFatal), so log it instead."""
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"[rails] {getattr(fn, '__name__', fn)} failed: {e}")
        traceback.print_exc()
        return None


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:  # noqa: BLE001 - the editor may be gone
        pass


def _poll(win) -> None:
    """Keep the routes of the active Rails app current (bin/rails routes again after routes.rb is saved)."""
    p = rails_project(win)
    if p is None:
        return
    try:
        ri.index(Path(p.folder)).routes()
    except Exception:  # noqa: BLE001
        pass
    panel = getattr(win, "rails_panel", None)
    if panel is not None and getattr(win, "dock_rails", None) is not None and win.dock_rails.isVisible():
        panel.set_project(p)
        if getattr(panel, "_routes_dirty", False):          # bin/rails routes finished (worker thread)
            panel._routes_dirty = False
            panel._routes_arrived()


def _site_opened(win, project) -> None:
    if project is None or getattr(project, "language", "") != "rails-web":
        return
    if not is_rails_project(project) and not is_rails_template(project):
        return
    folder = Path(project.folder)
    if is_rails_project(project):
        QTimer.singleShot(0, lambda: _warm(folder))
        ensure_database(win, project)
        if win.project is project and (folder / "config" / "routes.rb").is_file() and \
                not getattr(project, "_rails_opened", False):
            project._rails_opened = True
            QTimer.singleShot(0, lambda: open_location(win, folder / "config" / "routes.rb", 1))
    if needs_setup(project) and not getattr(project, "_rails_asked", False):
        project._rails_asked = True
        if not _offscreen():
            QTimer.singleShot(300, lambda: prepare_project(win, project, ask=True))
    panel = win.rails_panel
    if is_rails_project(project):
        panel.set_project(project, force=True)


__all__ = ["EditorBridge", "RailsPanel", "database_config", "edit_credentials", "ensure_database", "install",
           "needs_setup", "on_editor_ready", "prepare_project", "rails_definition", "rails_items", "setup_steps"]
