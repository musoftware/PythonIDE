"""Agent Manager engine (docs/CONTRACTS.md 9.5) - no widgets here, the UI is radide/features/ai_agents.py.

An AgentTask works in a folder (the project) and records everything it does as Steps (plan, messages,
file reads / writes / edits, searches, commands and their results).  Files it changes become FileChanges to
review (accept / reject per file); the original of every touched file is copied first to
`<folder>/.radide/ai/checkpoints/<task id>/` so "Undo all" restores the folder.

Two engines:
  * "builtin" - an agent loop that works with ANY radide.ai provider (Ollama, LM Studio, API keys, even a CLI
    in plain chat mode).  The model calls tools with a small text protocol (one ```tool JSON block per reply):
    list_files, read_file, search, write_file, edit_file, run_command, finish.  Writes and commands wait for the
    user's approval unless the permission mode auto-approves them.
  * "cli" - the official CLI agents (claude, gemini, codex, opencode, qwen, copilot, cursor-agent) run in the
    folder in their own headless agent mode; their JSON events become steps.  Changes are found by comparing a
    snapshot of the folder taken before the run.  In "Ask every time" mode the CLI first runs read-only to make
    a plan; approving the plan runs it with edits allowed.

    from radide.ai import agents
    mgr = agents.manager()
    task = mgr.create("create hello.py printing hello, then run it", folder, provider_id="ollama")
    task.step_added.connect(...); task.approval_needed.connect(...); task.start()
"""
from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal

import importlib

P = importlib.import_module(__package__ + ".providers")   # (radide.ai.providers is shadowed by the function)

WIN = sys.platform == "win32"
NO_WINDOW = 0x08000000 if WIN else 0

PERMISSIONS = ("ask", "auto_edits", "auto_all")
PERMISSION_TITLES = {"ask": "Ask every time", "auto_edits": "Auto-approve edits", "auto_all": "Auto-approve all"}
STATUS_TITLES = {"queued": "Queued", "running": "Running", "waiting": "Needs approval", "done": "Done",
                 "failed": "Failed", "cancelled": "Stopped"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__", ".radide", ".idea",
             ".vs", ".vscode", "dist", "build", ".mypy_cache", ".pytest_cache", ".tox", "vendor", "bin", "obj"}
WRITE_TOOLS = ("write_file", "edit_file")
READ_TOOLS = ("list_files", "read_file", "search")


def _now() -> float:
    return time.time()


# ============================================================================ data
@dataclass
class Step:
    """One entry of a task's conversation.  kind: user, plan, message, read, list, search, write, edit,
    command, web, tool, approval, result, error, info."""
    kind: str
    title: str
    detail: str = ""             # arguments / message text (markdown for messages)
    output: str = ""             # tool result
    status: str = "done"         # running | done | failed | pending (waiting for approval) | rejected
    path: str = ""               # relative file path (file tools)
    diff: str = ""               # unified diff (writes / edits)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    time: float = field(default_factory=_now)
    tool: str = ""
    args: dict = field(default_factory=dict)


@dataclass
class FileChange:
    path: str                    # relative to the task folder ('/' separators)
    existed: bool                # the file existed before the task
    status: str = "pending"      # pending | accepted | rejected
    backup: bool = True          # False: too big to keep a copy (undo impossible)
    deleted: bool = False


@dataclass
class Artifact:
    name: str
    path: str                    # absolute
    kind: str = "markdown"       # markdown | image | text


# ============================================================================ helpers
def rel_path(root: Path, p: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")


def safe_join(root: Path, rel: str) -> Path:
    """Path of `rel` inside root (raises ValueError when it points outside)."""
    rel = (rel or ".").strip().strip('"').strip("'")
    p = Path(rel)
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    r = root.resolve()
    if p != r and r not in p.parents:
        raise ValueError(f"path outside the task folder: {rel}")
    return p


def read_text(p: Path) -> str:
    data = p.read_bytes()
    for enc in ("utf-8", "cp1256", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def unified_diff(before: str | None, after: str | None, rel: str, context: int = 3) -> str:
    a = (before or "").splitlines(keepends=True)
    b = (after or "").splitlines(keepends=True)
    if a and not a[-1].endswith("\n"):
        a[-1] += "\n"
    if b and not b[-1].endswith("\n"):
        b[-1] += "\n"
    d = difflib.unified_diff(a, b, "a/" + rel if before is not None else "/dev/null",
                             "b/" + rel if after is not None else "/dev/null", n=context)
    return "".join(d)


def diff_stats(diff: str) -> tuple[int, int]:
    add = sum(1 for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    rem = sum(1 for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    return add, rem


def iter_files(root: Path, limit: int = 5000):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".radide"))
        for f in sorted(filenames):
            yield Path(dirpath) / f
            n += 1
            if n >= limit:
                return


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if WIN:
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                           creationflags=NO_WINDOW, timeout=10)
        except Exception:  # noqa: BLE001
            pass
    try:
        proc.kill()
    except Exception:  # noqa: BLE001
        pass


class _Bridge(QObject):
    """Runs a function on a worker thread and delivers its result on the UI thread."""
    done = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.done.connect(self._deliver, Qt.ConnectionType.QueuedConnection)
        self._callbacks: dict[int, object] = {}
        self._n = 0

    def run(self, fn, callback):
        self._n += 1
        key = self._n
        self._callbacks[key] = callback

        def work():
            try:
                res = (True, fn())
            except Exception as e:  # noqa: BLE001
                res = (False, f"{type(e).__name__}: {e}")
            self.done.emit(key, res)
        threading.Thread(target=work, daemon=True, name="agent-tool").start()

    def _deliver(self, key, res):
        cb = self._callbacks.pop(key, None)
        if cb is not None:
            cb(*res)


# ============================================================================ checkpoint
class Checkpoint:
    """Originals of the files a task touches: <folder>/.radide/ai/checkpoints/<task>/files/... + manifest.json"""

    MAX_BACKUP = 8 * 1024 * 1024

    def __init__(self, root: Path, task_id: str):
        self.root = Path(root)
        self.dir = self.root / ".radide" / "ai" / "checkpoints" / task_id
        self.manifest: dict[str, dict] = {}
        mf = self.dir / "manifest.json"
        if mf.is_file():
            try:
                self.manifest = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.manifest = {}

    def has(self, rel: str) -> bool:
        return rel in self.manifest

    def _save_manifest(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=1), encoding="utf-8")

    def save(self, rel: str) -> None:
        """Remember the current content of rel (only the first time)."""
        if rel in self.manifest:
            return
        p = self.root / rel
        self.save_bytes(rel, p.read_bytes() if p.is_file() else None)

    def save_bytes(self, rel: str, data: bytes | None, backup: bool = True) -> None:
        if rel in self.manifest:
            return
        entry = {"existed": data is not None or not backup, "backup": backup}
        if data is not None and len(data) <= self.MAX_BACKUP:
            dst = self.dir / "files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        elif data is not None:
            entry["backup"] = False
        self.manifest[rel] = entry
        self._save_manifest()

    def original(self, rel: str) -> bytes | None:
        e = self.manifest.get(rel)
        if e is None:
            p = self.root / rel
            return p.read_bytes() if p.is_file() else None
        if not e.get("existed"):
            return None
        f = self.dir / "files" / rel
        return f.read_bytes() if f.is_file() else None

    def original_text(self, rel: str) -> str | None:
        b = self.original(rel)
        if b is None:
            return None
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return b.decode("cp1252", errors="replace")

    def restore(self, rel: str) -> bool:
        e = self.manifest.get(rel)
        if e is None:
            return False
        p = self.root / rel
        if not e.get("existed"):
            if p.is_file():
                p.unlink()
            return True
        if not e.get("backup", True):
            return False
        src = self.dir / "files" / rel
        if not src.is_file():
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(src.read_bytes())
        return True

    def restore_all(self) -> list[str]:
        return [rel for rel in list(self.manifest) if self.restore(rel)]


class Snapshot:
    """Contents of a folder before a CLI agent runs (to find and undo what it changed)."""

    MAX_FILE = 2 * 1024 * 1024
    MAX_TOTAL = 40 * 1024 * 1024

    def __init__(self, root: Path):
        self.root = Path(root)
        self.stat: dict[str, tuple[int, float]] = {}
        self.data: dict[str, bytes] = {}
        total = 0
        for f in iter_files(self.root, 20000):
            try:
                st = f.stat()
            except OSError:
                continue
            rel = rel_path(self.root, f)
            self.stat[rel] = (st.st_size, st.st_mtime)
            if st.st_size <= self.MAX_FILE and total + st.st_size <= self.MAX_TOTAL:
                try:
                    self.data[rel] = f.read_bytes()
                    total += st.st_size
                except OSError:
                    pass

    def changed(self) -> list[tuple[str, str]]:
        """[(rel, 'added'|'modified'|'deleted')] compared with the folder now."""
        out = []
        now: dict[str, tuple[int, float]] = {}
        for f in iter_files(self.root, 20000):
            try:
                st = f.stat()
            except OSError:
                continue
            now[rel_path(self.root, f)] = (st.st_size, st.st_mtime)
        for rel, st in now.items():
            old = self.stat.get(rel)
            if old is None:
                out.append((rel, "added"))
            elif old != st:
                if rel in self.data:
                    try:
                        if (self.root / rel).read_bytes() == self.data[rel]:
                            continue
                    except OSError:
                        continue
                out.append((rel, "modified"))
        for rel in self.stat:
            if rel not in now:
                out.append((rel, "deleted"))
        return out


# ============================================================================ tool protocol (built-in loop)
BUILTIN_SYSTEM = """You are an autonomous coding agent inside the RAD IDE. You work in this folder: {root}
Operating system: {os}. Shell for run_command: {shell}. Python: {python}.

Do the user's task yourself by calling tools. Call exactly ONE tool per reply, written as a JSON object in a
```tool fenced block, for example:

```tool
{{"tool": "write_file", "path": "hello.py", "content": "print('hello')\\n"}}
```

Tools:
- list_files {{"path": "."}} - list the files of a folder (recursive)
- read_file {{"path": "file"}} - read a text file
- search {{"pattern": "regex", "path": ".", "glob": "*.py"}} - search text in files
- write_file {{"path": "file", "content": "full new content"}} - create or overwrite a file
- edit_file {{"path": "file", "old": "exact existing text", "new": "replacement"}} - replace text in a file
- run_command {{"command": "python hello.py"}} - run a shell command in the folder and get its output
- finish {{"summary": "what you did and the result"}} - the task is complete

Rules: paths are relative to the folder. In your FIRST reply write a short numbered plan, then the first tool
block. After each tool you get its result; then continue with the next tool. Never invent tool results. Do not
ask the user questions - decide yourself. When everything is done and checked, call finish.
{extra}"""

_TOOL_FENCE = re.compile(r"```[ \t]*(tool|json|tool_call|tool_code)?[^\n]*\n(.*?)```", re.S | re.I)
TOOL_NAMES = ("list_files", "read_file", "search", "write_file", "edit_file", "run_command", "finish")
_ALIASES = {"ls": "list_files", "list": "list_files", "list_dir": "list_files", "read": "read_file",
            "cat": "read_file", "grep": "search", "write": "write_file", "create_file": "write_file",
            "edit": "edit_file", "replace": "edit_file", "str_replace": "edit_file", "run": "run_command",
            "bash": "run_command", "shell": "run_command", "exec": "run_command", "execute": "run_command",
            "done": "finish", "complete": "finish", "final_answer": "finish", "answer": "finish"}


def _json_objects(text: str):
    """Balanced {...} substrings of text (string-aware)."""
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, j, in_str, esc = 0, i, False, False
        while j < n:
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield text[i:j + 1]
                    break
            j += 1
        i = j + 1 if depth == 0 else i + 1


def _load(s: str):
    try:
        return json.loads(s, strict=False)
    except ValueError:
        pass
    # common small-model slip: a trailing comma
    try:
        return json.loads(re.sub(r",\s*([}\]])", r"\1", s), strict=False)
    except ValueError:
        return None


def parse_tool_call(text: str) -> tuple[dict | None, str]:
    """-> ({'tool': name, **args} or None, the text without the tool block)."""
    candidates: list[tuple[int, int, str]] = []
    for m in _TOOL_FENCE.finditer(text or ""):
        candidates.append((m.start(), m.end(), m.group(2)))
    if not candidates:
        for s in _json_objects(text or ""):
            k = text.find(s)
            candidates.append((k, k + len(s), s))
    for start, end, body in candidates:
        body = body.strip()
        objs = [body] if body.startswith("{") else list(_json_objects(body))
        for ob in objs:
            obj = _load(ob)
            if not isinstance(obj, dict):
                continue
            name = obj.get("tool") or obj.get("name") or obj.get("function") or obj.get("action")
            if isinstance(name, dict):
                name = name.get("name")
            if not isinstance(name, str):
                continue
            name = _ALIASES.get(name.strip().lower(), name.strip().lower())
            if name not in TOOL_NAMES:
                continue
            args = obj.get("args") or obj.get("arguments") or obj.get("parameters") or obj.get("input") or {}
            if isinstance(args, str):
                args = _load(args) or {}
            call = {k: v for k, v in obj.items() if k not in ("tool", "name", "function", "action", "args",
                                                              "arguments", "parameters", "input")}
            if isinstance(args, dict):
                call.update(args)
            call["tool"] = name
            rest = (text[:start] + text[end:]).strip()
            return call, rest
    return None, (text or "").strip()


def tool_title(call: dict) -> tuple[str, str]:
    """(step kind, title) of a built-in tool call."""
    t = call.get("tool", "")
    p = str(call.get("path") or "")
    if t == "list_files":
        return "list", f"List files in {p or '.'}"
    if t == "read_file":
        return "read", f"Read {p}"
    if t == "search":
        return "search", f"Search \"{call.get('pattern', '')}\""
    if t == "write_file":
        return "write", f"Write {p}"
    if t == "edit_file":
        return "edit", f"Edit {p}"
    if t == "run_command":
        return "command", f"Run: {call.get('command', '')}"
    return "tool", t


# ============================================================================ the task
class AgentTask(QObject):
    """One agent task.  Signals are emitted on the UI thread."""

    step_added = pyqtSignal(object)            # Step
    step_changed = pyqtSignal(object)          # Step
    status_changed = pyqtSignal(str)
    approval_needed = pyqtSignal(object)       # Step (status 'pending')
    changes_changed = pyqtSignal()
    artifacts_changed = pyqtSignal()
    finished = pyqtSignal(str)                 # final status

    def __init__(self, prompt: str, folder, provider_id: str = "", model: str = "", engine: str = "",
                 permission: str = "ask", max_steps: int = 25, title: str = "", parent=None):
        super().__init__(parent)
        self.id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.prompt = prompt.strip()
        self.title = title or _title_of(self.prompt)
        self.root = Path(folder).resolve()
        if not provider_id:
            p, m = P.default("agent")
            provider_id, model = p.id, model or m
        self.provider_id = provider_id
        self.model = model
        prov = self.provider()
        self.engine = engine or ("cli" if prov is not None and prov.kind == "cli" else "builtin")
        self.permission = permission if permission in PERMISSIONS else "ask"
        self.max_steps = max(1, int(max_steps))
        self.status = "queued"
        self.started = 0.0
        self.ended = 0.0
        self.steps: list[Step] = []
        self.changes: dict[str, FileChange] = {}
        self.artifacts: list[Artifact] = []
        self.summary = ""
        self.error = ""
        self.checkpoint = Checkpoint(self.root, self.id)
        self.unread = False
        self._job: P.ChatJob | None = None
        self._bridge = _Bridge(self)
        self._procs: list[subprocess.Popen] = []
        self._runner: _Engine | None = None

    # ------------------------------------------------------------------ info
    def provider(self):
        try:
            return P.get(self.provider_id)
        except KeyError:
            return None

    def provider_name(self) -> str:
        p = self.provider()
        name = p.name if p is not None else self.provider_id
        return name + (f" · {self.model}" if self.model and self.model != "default" else "")

    @property
    def running(self) -> bool:
        return self.status in ("queued", "running", "waiting")

    def pending_approval(self) -> Step | None:
        return next((s for s in reversed(self.steps) if s.status == "pending"), None)

    def task_dir(self) -> Path:
        return self.root / ".radide" / "ai" / "tasks" / self.id

    # ------------------------------------------------------------------ steps
    def add_step(self, kind: str, title: str, **kw) -> Step:
        s = Step(kind, title, **kw)
        self.steps.append(s)
        self.unread = True
        self.step_added.emit(s)
        return s

    def update_step(self, s: Step, **kw) -> None:
        for k, v in kw.items():
            setattr(s, k, v)
        self.step_changed.emit(s)

    def set_status(self, status: str) -> None:
        if status == self.status:
            return
        self.status = status
        self.status_changed.emit(status)
        if status in ("done", "failed", "cancelled"):
            self.ended = _now()
            self._write_walkthrough()
            self.save()
            self.finished.emit(status)

    # ------------------------------------------------------------------ run
    def start(self) -> None:
        if self.status != "queued":
            return
        self.started = _now()
        self.root.mkdir(parents=True, exist_ok=True)
        self.add_step("user", "Task", detail=self.prompt)
        self.set_status("running")
        self._runner = BuiltinEngine(self) if self.engine == "builtin" else CliEngine(self)
        try:
            self._runner.start()
        except Exception as e:  # noqa: BLE001
            self.fail(f"{type(e).__name__}: {e}")

    def stop(self) -> None:
        if not self.running:
            return
        if self._job is not None and not self._job.done:
            self._job.cancel()
        for proc in list(self._procs):
            kill_tree(proc)
        for s in self.steps:
            if s.status in ("running", "pending"):
                self.update_step(s, status="rejected" if s.status == "pending" else "failed",
                                 output=s.output or "stopped")
        self.add_step("info", "Stopped by the user")
        self.set_status("cancelled")

    def fail(self, message: str) -> None:
        self.error = message
        self.add_step("error", "Error", detail=message, status="failed")
        self.set_status("failed")

    def approve(self, step: Step | None = None, always: bool = False) -> None:
        step = step or self.pending_approval()
        if step is None or step.status != "pending" or self._runner is None:
            return
        if always:
            self.permission = "auto_all" if step.kind == "command" else (
                "auto_edits" if self.permission == "ask" else self.permission)
        self.set_status("running")
        self._runner.approved(step, True)

    def reject(self, step: Step | None = None, reason: str = "") -> None:
        step = step or self.pending_approval()
        if step is None or step.status != "pending" or self._runner is None:
            return
        self.set_status("running")
        self._runner.approved(step, False, reason)

    def follow_up(self, text: str) -> bool:
        """Continue a finished task with a new instruction (same checkpoint, same changes list)."""
        text = text.strip()
        if not text or self.running:
            return False
        if self._runner is None:             # a task loaded from the history
            self._runner = BuiltinEngine(self) if self.engine == "builtin" else CliEngine(self)
            if isinstance(self._runner, BuiltinEngine):
                self._runner.messages = [P.Message("user", self.prompt),
                                         P.Message("assistant", self.summary or "(earlier work)")]
            else:
                self._runner.snapshot = Snapshot(self.root)
        self.add_step("user", "Follow-up", detail=text)
        self.status = "running"
        self.status_changed.emit("running")
        self._runner.follow_up(text)
        return True

    # ------------------------------------------------------------------ files
    def record_change(self, rel: str, deleted: bool = False) -> None:
        e = self.checkpoint.manifest.get(rel, {})
        ch = self.changes.get(rel)
        if ch is None:
            ch = FileChange(rel, existed=bool(e.get("existed", True)), backup=bool(e.get("backup", True)))
            self.changes[rel] = ch
        ch.status = "pending"
        ch.deleted = deleted
        if not ch.existed and deleted:          # created then deleted again: nothing left to review
            self.changes.pop(rel, None)
        self.changes_changed.emit()

    def diff_of(self, rel: str) -> str:
        p = self.root / rel
        after = None
        if p.is_file():
            try:
                after = read_text(p)
            except OSError:
                after = None
        before = self.checkpoint.original_text(rel) if self.checkpoint.has(rel) else after
        return unified_diff(before, after, rel)

    def accept_change(self, rel: str) -> None:
        ch = self.changes.get(rel)
        if ch is not None:
            ch.status = "accepted"
            self.changes_changed.emit()
            self.save()

    def reject_change(self, rel: str) -> bool:
        ch = self.changes.get(rel)
        if ch is None:
            return False
        ok = self.checkpoint.restore(rel)
        if ok:
            ch.status = "rejected"
            self.add_step("info", f"Reverted {rel}", path=rel)
            self.changes_changed.emit()
            self.save()
        return ok

    def accept_all(self) -> None:
        for ch in self.changes.values():
            if ch.status == "pending":
                ch.status = "accepted"
        self.changes_changed.emit()
        self.save()

    def undo_all(self) -> list[str]:
        """Restore every touched file from the checkpoint."""
        restored = self.checkpoint.restore_all()
        for rel in restored:
            if rel in self.changes:
                self.changes[rel].status = "rejected"
        self.add_step("info", f"Undo all: restored {len(restored)} file(s) from the checkpoint",
                      detail="\n".join(restored))
        self.changes_changed.emit()
        self.save()
        return restored

    # ------------------------------------------------------------------ artifacts / persistence
    def add_artifact(self, name: str, path: Path, kind: str = "markdown") -> Artifact:
        path = Path(path)
        for a in self.artifacts:
            if a.path == str(path):
                self.artifacts_changed.emit()
                return a
        a = Artifact(name, str(path), kind)
        self.artifacts.append(a)
        self.artifacts_changed.emit()
        return a

    def write_artifact(self, name: str, text: str) -> Artifact:
        d = self.task_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        p.write_text(text, encoding="utf-8")
        return self.add_artifact(name, p, "markdown" if name.endswith(".md") else "text")

    def set_plan(self, text: str) -> None:
        text = text.strip()
        if text:
            self.write_artifact("plan.md", f"# Plan\n\n**Task:** {self.prompt}\n\n{text}\n")

    def _write_walkthrough(self) -> None:
        try:
            lines = [f"# Walkthrough - {self.title}", "", f"**Task:** {self.prompt}", "",
                     f"**Agent:** {self.provider_name()} ({'CLI agent' if self.engine == 'cli' else 'built-in loop'})",
                     f"**Status:** {STATUS_TITLES.get(self.status, self.status)}",
                     f"**Time:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.started))}"
                     f" ({max(0, int(self.ended - self.started))} s)", ""]
            if self.summary:
                lines += ["## Summary", "", self.summary, ""]
            if self.changes:
                lines += ["## Files changed", ""]
                for ch in self.changes.values():
                    add, rem = diff_stats(self.diff_of(ch.path))
                    what = "deleted" if ch.deleted else ("new" if not ch.existed else "modified")
                    lines.append(f"- `{ch.path}` ({what}, +{add} -{rem}) - {ch.status}")
                lines.append("")
            cmds = [s for s in self.steps if s.kind == "command"]
            if cmds:
                lines += ["## Commands", ""]
                for s in cmds:
                    out = (s.output or "").strip()
                    lines.append(f"- `{s.title[5:] if s.title.startswith('Run: ') else s.title}` - {s.status}")
                    if out:
                        lines += ["", "```", out[-1500:], "```", ""]
                lines.append("")
            if self.error:
                lines += ["## Error", "", self.error, ""]
            self.write_artifact("walkthrough.md", "\n".join(lines))
        except OSError:
            pass

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "prompt": self.prompt, "provider": self.provider_id,
                "model": self.model, "engine": self.engine, "permission": self.permission,
                "max_steps": self.max_steps, "status": self.status, "started": self.started, "ended": self.ended,
                "summary": self.summary, "error": self.error, "root": str(self.root),
                "steps": [asdict(s) for s in self.steps],
                "changes": [asdict(c) for c in self.changes.values()],
                "artifacts": [asdict(a) for a in self.artifacts]}

    def save(self) -> None:
        try:
            d = self.task_dir()
            d.mkdir(parents=True, exist_ok=True)
            data = self.to_dict()
            for s in data["steps"]:
                s["output"] = (s.get("output") or "")[-4000:]
            (d / "task.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        except (OSError, TypeError, ValueError):
            pass

    @classmethod
    def load(cls, path: Path, parent=None) -> "AgentTask | None":
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        root = Path(d.get("root") or Path(path).parents[4])
        if not root.is_dir():
            root = Path(path).parents[4]
        t = cls(d.get("prompt", ""), root, d.get("provider", ""), d.get("model", ""), d.get("engine", ""),
                d.get("permission", "ask"), d.get("max_steps", 25), d.get("title", ""), parent)
        t.id = d.get("id", t.id)
        t.checkpoint = Checkpoint(t.root, t.id)
        t.status = d.get("status", "done")
        if t.status in ("queued", "running", "waiting"):
            t.status = "cancelled"
        t.started, t.ended = d.get("started", 0.0), d.get("ended", 0.0)
        t.summary, t.error = d.get("summary", ""), d.get("error", "")
        for s in d.get("steps", []):
            try:
                st = Step(**s)
                if st.status in ("running", "pending"):
                    st.status = "failed"
                t.steps.append(st)
            except TypeError:
                pass
        for c in d.get("changes", []):
            try:
                ch = FileChange(**c)
                t.changes[ch.path] = ch
            except TypeError:
                pass
        for a in d.get("artifacts", []):
            try:
                t.artifacts.append(Artifact(**a))
            except TypeError:
                pass
        t.unread = False
        return t


def _title_of(prompt: str) -> str:
    first = (prompt or "Task").strip().splitlines()[0] if prompt.strip() else "Task"
    return first if len(first) <= 60 else first[:57].rstrip() + "..."


# ============================================================================ engines
class _Engine:
    def __init__(self, task: AgentTask):
        self.task = task

    def start(self):
        raise NotImplementedError

    def approved(self, step: Step, ok: bool, reason: str = ""):
        pass

    def follow_up(self, text: str):
        pass


class BuiltinEngine(_Engine):
    """Agent loop over any provider's chat() with the text tool protocol."""

    MAX_RESULT = 6000
    COMMAND_TIMEOUT = 120

    def __init__(self, task: AgentTask):
        super().__init__(task)
        self.messages: list[P.Message] = []
        self.turns = 0
        self.nudges = 0
        self.msg_step: Step | None = None
        self.pending: tuple[Step, dict, str] | None = None
        self.retries = 0

    def system(self) -> str:
        py = shutil.which("python") or shutil.which("python3") or sys.executable
        extra = ""
        try:
            files = [rel_path(self.task.root, f) for f in iter_files(self.task.root, 60)]
            extra = "\nFiles in the folder now:\n" + ("\n".join(files) if files else "(empty folder)")
        except OSError:
            pass
        return BUILTIN_SYSTEM.format(root=self.task.root, os="Windows" if WIN else sys.platform,
                                     shell="cmd.exe" if WIN else "/bin/sh", python=Path(py).name, extra=extra)

    def start(self):
        self.messages = [P.Message("user", self.task.prompt)]
        self._turn()

    def follow_up(self, text: str):
        self.messages.append(P.Message("user", text))
        self.turns = 0
        self._turn()

    # ---------------------------------------------------------------- model turn
    def _turn(self):
        t = self.task
        if not t.running:
            return
        if self.turns >= t.max_steps:
            t.summary = t.summary or f"Stopped after {t.max_steps} steps (the step limit)."
            t.add_step("info", f"Step limit reached ({t.max_steps})")
            t.set_status("done")
            return
        self.turns += 1
        prov = t.provider()
        if prov is None:
            t.fail(f"Unknown AI provider {t.provider_id}")
            return
        self._compact(14000 if prov.kind == "local" else 60000)
        self.msg_step = t.add_step("message", "Thinking...", status="running")
        try:
            job = prov.chat(self.messages, model=t.model or None, system=self.system(), temperature=0.2,
                            cwd=str(t.root), purpose="agent")
        except Exception as e:  # noqa: BLE001
            t.fail(f"{type(e).__name__}: {e}")
            return
        t._job = job
        job.delta.connect(self._on_delta)
        job.finished.connect(self._on_answer)
        job.failed.connect(self._on_failed)

    def _on_delta(self, _s: str):
        if self.msg_step is not None and self.task._job is not None:
            shown = _strip_partial_tool(self.task._job.text)
            self.task.update_step(self.msg_step, detail=shown, title="Agent")

    def _on_failed(self, err: str):
        t = self.task
        if self.msg_step is not None:
            t.update_step(self.msg_step, status="failed")
        if err == "Cancelled" or not t.running:
            return
        low = err.lower()
        if self.retries < 2 and any(w in low for w in ("in time", "timed out", "timeout", "connection reset",
                                                         "temporarily", "busy", "overloaded", "503", "502")):
            self.retries += 1
            if self.msg_step is not None and self.msg_step in t.steps:
                t.steps.remove(self.msg_step)
                t.step_changed.emit(Step("removed", "", id=self.msg_step.id))
            t.add_step("info", f"The model did not answer ({err.splitlines()[0][:120]}) - retrying "
                               f"({self.retries}/2)...")
            self.turns -= 1
            QTimer.singleShot(1500, self._turn)
            return
        t.fail(err)

    def _on_answer(self, text: str):
        t = self.task
        if not t.running:
            return
        self.retries = 0
        call, rest = parse_tool_call(text)
        if self.msg_step is not None:
            if rest:
                t.update_step(self.msg_step, detail=rest, title="Agent", status="done")
            else:
                t.steps.remove(self.msg_step)
                t.step_changed.emit(Step("removed", "", id=self.msg_step.id))
            if rest and self.turns == 1 and re.search(r"(^|\n)\s*(1[.)]|-|\*)\s+\S", rest):
                self.msg_step.kind = "plan"
                self.msg_step.title = "Plan"
                t.step_changed.emit(self.msg_step)
                t.set_plan(rest)
        self.messages.append(P.Message("assistant", text))
        if call is None:
            self.nudges += 1
            if self.nudges >= 2 or not text.strip():
                t.summary = rest or t.summary
                t.set_status("done")
                return
            self.messages.append(P.Message("user", "Continue: reply with exactly one ```tool block (call a tool, "
                                                   "or finish if the task is complete)."))
            self._turn()
            return
        self.nudges = 0
        if call["tool"] == "finish":
            t.summary = str(call.get("summary") or call.get("result") or rest or "Done.")
            t.add_step("result", "Finished", detail=t.summary)
            t.set_status("done")
            return
        self._tool(call)

    # ---------------------------------------------------------------- tools
    def _needs_approval(self, name: str) -> bool:
        perm = self.task.permission
        if name in WRITE_TOOLS:
            return perm == "ask"
        if name == "run_command":
            return perm != "auto_all"
        return False

    def _tool(self, call: dict):
        t = self.task
        name = call["tool"]
        kind, title = tool_title(call)
        rel = ""
        if call.get("path") not in (None, "", "."):
            try:
                rel = rel_path(t.root, safe_join(t.root, str(call["path"])))
            except ValueError:
                rel = str(call["path"])
        step = t.add_step(kind, title, tool=name, args={k: v for k, v in call.items() if k != "content"},
                          path=rel, status="running")
        if name in WRITE_TOOLS:
            try:
                new_text, before = self._proposed(call)
            except Exception as e:  # noqa: BLE001
                self._result(step, f"Error: {e}", failed=True)
                return
            step.diff = unified_diff(before, new_text, rel or str(call.get("path")))
            call["_new_text"] = new_text
            t.update_step(step, diff=step.diff)
        elif name == "run_command":
            step.detail = str(call.get("command") or "")
        if self._needs_approval(name):
            t.update_step(step, status="pending")
            self.pending = (step, call, name)
            t.set_status("waiting")
            t.approval_needed.emit(step)
            return
        self._execute(step, call)

    def approved(self, step: Step, ok: bool, reason: str = ""):
        if self.pending is None or self.pending[0] is not step:
            return
        _s, call, name = self.pending
        self.pending = None
        if ok:
            self.task.update_step(step, status="running")
            self._execute(step, call)
        else:
            self.task.update_step(step, status="rejected", output="Rejected by the user")
            msg = "The user REJECTED this action" + (f": {reason}" if reason else ".") + \
                  " Do not do it again; choose another way or finish."
            self._feed(step, msg)

    def _proposed(self, call: dict) -> tuple[str, str | None]:
        t = self.task
        p = safe_join(t.root, str(call.get("path") or ""))
        if p.is_dir():
            raise ValueError(f"{call.get('path')} is a folder")
        before = read_text(p) if p.is_file() else None
        if call["tool"] == "write_file":
            content = call.get("content")
            if content is None:
                content = call.get("text") or call.get("code") or ""
            return str(content), before
        if before is None:
            raise ValueError(f"file not found: {call.get('path')} (use write_file to create it)")
        old = str(call.get("old") or call.get("old_text") or call.get("search") or "")
        new = str(call.get("new") if call.get("new") is not None else call.get("new_text") or call.get("replace") or "")
        if not old:
            raise ValueError("edit_file needs 'old' (the exact text to replace)")
        if old not in before:
            # tolerate different line endings / trailing spaces
            norm = before.replace("\r\n", "\n")
            if old.replace("\r\n", "\n") in norm:
                return norm.replace(old.replace("\r\n", "\n"), new, 1), before
            raise ValueError("the 'old' text was not found in the file - read_file it first and copy it exactly")
        return before.replace(old, new, 1), before

    def _execute(self, step: Step, call: dict):
        t = self.task
        name = call["tool"]
        try:
            if name == "list_files":
                root = safe_join(t.root, str(call.get("path") or "."))
                files = [rel_path(t.root, f) for f in iter_files(root, 300)] if root.is_dir() else []
                self._result(step, "\n".join(files) if files else "(no files)")
            elif name == "read_file":
                p = safe_join(t.root, str(call.get("path") or ""))
                if not p.is_file():
                    raise ValueError(f"file not found: {call.get('path')}")
                text = read_text(p)
                self._result(step, text if len(text) <= 20000 else text[:20000] + "\n... (truncated)")
            elif name == "search":
                self._result(step, self._search(call))
            elif name in WRITE_TOOLS:
                p = safe_join(t.root, str(call.get("path") or ""))
                rel = rel_path(t.root, p)
                t.checkpoint.save(rel)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(call["_new_text"], encoding="utf-8", newline="")
                t.record_change(rel)
                add, rem = diff_stats(step.diff)
                t.update_step(step, path=rel)
                self._result(step, f"OK - {'created' if not t.changes[rel].existed else 'updated'} {rel} "
                                   f"(+{add} -{rem} lines)")
                _notify_file_written(p)
            elif name == "run_command":
                self._run_command(step, str(call.get("command") or ""), call)
            else:
                self._result(step, f"Unknown tool {name}", failed=True)
        except Exception as e:  # noqa: BLE001
            self._result(step, f"Error: {e}", failed=True)

    def _search(self, call: dict) -> str:
        t = self.task
        pat = str(call.get("pattern") or call.get("query") or "")
        if not pat:
            raise ValueError("search needs 'pattern'")
        try:
            rx = re.compile(pat, re.I)
        except re.error:
            rx = re.compile(re.escape(pat), re.I)
        root = safe_join(t.root, str(call.get("path") or "."))
        glob = str(call.get("glob") or "")
        hits = []
        for f in iter_files(root, 3000):
            if glob and not fnmatch.fnmatch(f.name, glob):
                continue
            try:
                if f.stat().st_size > 1_000_000:
                    continue
                for i, line in enumerate(read_text(f).splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel_path(t.root, f)}:{i}: {line.strip()[:200]}")
                        if len(hits) >= 100:
                            return "\n".join(hits) + "\n... (more matches)"
            except OSError:
                continue
        return "\n".join(hits) if hits else "(no matches)"

    def _run_command(self, step: Step, command: str, call: dict):
        t = self.task
        if not command.strip():
            self._result(step, "Error: empty command", failed=True)
            return
        timeout = float(call.get("timeout") or self.COMMAND_TIMEOUT)
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", NO_COLOR="1")

        def work():
            proc = subprocess.Popen(command, shell=True, cwd=str(t.root), env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            t._procs.append(proc)
            try:
                out, _ = proc.communicate(timeout=timeout)
                code = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                kill_tree(proc)
                out, _ = proc.communicate()
                code, timed_out = -1, True
            finally:
                if proc in t._procs:
                    t._procs.remove(proc)
            text = out.decode("utf-8", errors="replace") if out else ""
            if "�" in text and out:
                try:
                    text = out.decode("cp1256" if WIN else "latin-1")
                except UnicodeDecodeError:
                    pass
            return code, text.replace("\r\n", "\n"), timed_out

        def done(ok, res):
            if not t.running:
                return
            if not ok:
                self._result(step, f"Error: {res}", failed=True)
                return
            code, text, timed_out = res
            head = f"exit code {code}" + (f" (stopped after {timeout:g} s)" if timed_out else "")
            self._result(step, (text.strip() or "(no output)") + f"\n[{head}]", failed=code != 0)
        t._bridge.run(work, done)

    def _result(self, step: Step, output: str, failed: bool = False):
        t = self.task
        t.update_step(step, output=output, status="failed" if failed else "done")
        self._feed(step, output)

    def _feed(self, step: Step, output: str):
        t = self.task
        if not t.running:
            return
        if len(output) > self.MAX_RESULT:
            output = output[:self.MAX_RESULT // 2] + "\n... (truncated) ...\n" + output[-self.MAX_RESULT // 2:]
        self.messages.append(P.Message("user", f"Result of {step.tool or step.kind} ({step.title}):\n{output}\n\n"
                                               "Continue with the next tool, or finish."))
        QTimer.singleShot(0, self._turn)

    def _compact(self, budget: int = 40000):
        """Shorten old tool results so the conversation stays inside small context windows."""
        total = sum(len(m.content) for m in self.messages)
        i = 1
        while total > budget and i < len(self.messages) - 4:
            m = self.messages[i]
            if len(m.content) > 600:
                total -= len(m.content) - 400
                self.messages[i] = P.Message(m.role, m.content[:300] + "\n... (older content shortened) ...\n"
                                             + m.content[-100:])
            i += 1


def _strip_partial_tool(text: str) -> str:
    """While streaming: hide a tool block (shown as its own step afterwards)."""
    k = re.search(r"```[ \t]*(tool|json|tool_call|tool_code)\b", text, re.I)
    return text[:k.start()].rstrip() if k else text


_written_hooks: list = []


def on_file_written(fn) -> None:
    """fn(Path) is called on the UI thread after an agent wrote a file (the IDE reloads open editors)."""
    _written_hooks.append(fn)


def _notify_file_written(p: Path) -> None:
    for fn in list(_written_hooks):
        try:
            fn(p)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------- CLI engine
CLI_SYSTEM = ("You are running as a coding agent inside the RAD IDE's Agent Manager, in the folder {root}. "
              "Do the task completely by yourself, then finish with a short summary of what you did.")

# provider id -> {phase: args}; phase "plan" = read-only planning, "edits" = edits allowed, "all" = everything
CLI_ARGS = {
    "claude-cli": {"plan": ["--permission-mode", "plan"], "edits": ["--permission-mode", "acceptEdits"],
                   "all": ["--permission-mode", "bypassPermissions"]},
    "gemini-cli": {"plan": ["--approval-mode", "plan"], "edits": ["--approval-mode", "auto_edit"],
                   "all": ["--approval-mode", "yolo"]},
    "qwen-cli": {"plan": ["--approval-mode", "plan"], "edits": ["--approval-mode", "auto-edit"], "all": ["--yolo"]},
    "codex-cli": {"plan": ["--sandbox", "read-only"], "edits": ["--sandbox", "workspace-write"],
                  "all": ["--dangerously-bypass-approvals-and-sandbox"]},
    "opencode-cli": {"plan": ["--agent", "plan"], "edits": [], "all": []},
    "copilot-cli": {"plan": [], "edits": ["--allow-all-tools", "--deny-tool", "shell"], "all": ["--allow-all-tools"]},
    "cursor-cli": {"plan": [], "edits": ["--force"], "all": ["--force"]},
}

_CLAUDE_KIND = {"read": "read", "write": "write", "edit": "edit", "multiedit": "edit", "notebookedit": "edit",
                "bash": "command", "powershell": "command", "glob": "list", "ls": "list", "grep": "search",
                "webfetch": "web", "websearch": "web", "todowrite": "plan", "task": "tool", "agent": "tool",
                # gemini / qwen
                "read_file": "read", "read_many_files": "read", "write_file": "write", "replace": "edit",
                "edit": "edit", "run_shell_command": "command", "shell": "command", "list_directory": "list",
                "glob_tool": "list", "search_file_content": "search", "grep_search": "search",
                "google_web_search": "web", "web_fetch": "web", "write_todos": "plan",
                # opencode / codex
                "patch": "edit", "list": "list", "todo": "plan", "command_execution": "command",
                "file_change": "edit", "web_search": "web", "mcp_tool_call": "tool"}


def _cli_kind(name: str) -> str:
    return _CLAUDE_KIND.get((name or "").lower(), "tool")


def _first(d: dict, *keys) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _cli_title(kind: str, name: str, inp: dict) -> tuple[str, str]:
    """(title, relative-path-or-'') for a CLI tool call."""
    path = _first(inp, "file_path", "absolute_path", "path", "filePath", "notebook_path", "dir_path")
    cmd = _first(inp, "command", "cmd")
    if kind == "command":
        return f"Run: {cmd or name}", ""
    if kind in ("read", "write", "edit"):
        verb = {"read": "Read", "write": "Write", "edit": "Edit"}[kind]
        return f"{verb} {path or name}", path
    if kind == "search":
        return f"Search \"{_first(inp, 'pattern', 'query')}\"", ""
    if kind == "list":
        return f"List {_first(inp, 'pattern', 'path', 'dir_path') or '.'}", ""
    if kind == "web":
        return f"Web: {_first(inp, 'url', 'query', 'prompt')}", ""
    if kind == "plan":
        return "Update plan", ""
    return name or "tool", path


def _tool_output(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                parts.append(str(c.get("text") or c.get("content") or ""))
            else:
                parts.append(str(c))
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("output") or json.dumps(content)[:2000])
    return "" if content is None else str(content)


def _todos_md(todos) -> str:
    out = []
    for t in todos or []:
        if not isinstance(t, dict):
            continue
        st = str(t.get("status", ""))
        mark = "x" if st in ("completed", "done") else (" " if st != "in_progress" else "~")
        out.append(f"- [{mark}] {t.get('content') or t.get('description') or t.get('activeForm') or ''}")
    return "\n".join(out)


class CliEngine(_Engine):
    """Runs an official CLI agent in the task folder and turns its JSON events into steps."""

    def __init__(self, task: AgentTask):
        super().__init__(task)
        self.snapshot: Snapshot | None = None
        self.tools: dict[str, Step] = {}
        self.msg_step: Step | None = None
        self.msg_text = ""
        self.phase = ""
        self.plan_text = ""
        self.plan_step: Step | None = None
        self.prompt = task.prompt

    def start(self):
        t = self.task
        prov = t.provider()
        if prov is None:
            t.fail(f"Unknown AI provider {t.provider_id}")
            return
        ok, why = prov.available()
        if not ok:
            t.fail(f"{prov.name} is not ready: {why}")
            return
        info = t.add_step("info", "Taking a snapshot of the folder (for review and undo)...", status="running")

        def done(ok_, res):
            if not t.running:
                return
            if not ok_:
                t.fail(f"Snapshot failed: {res}")
                return
            self.snapshot = res
            t.update_step(info, title=f"Snapshot of {len(res.stat)} file(s) taken", status="done")
            phase = "plan" if t.permission == "ask" and CLI_ARGS.get(t.provider_id, {}).get("plan") else (
                "edits" if t.permission in ("ask", "auto_edits") else "all")
            self._run(phase, self.prompt)
        t._bridge.run(lambda: Snapshot(t.root), done)

    def follow_up(self, text: str):
        prev = self.task.summary
        self.prompt = (f"Earlier task: {self.task.prompt}\nWhat you did: {prev}\n\nNew instruction: {text}"
                       if prev else text)
        phase = "edits" if self.task.permission in ("ask", "auto_edits") else "all"
        self._run(phase, self.prompt)

    def _run(self, phase: str, prompt: str):
        t = self.task
        self.phase = phase
        prov = t.provider()
        args = list(CLI_ARGS.get(t.provider_id, {}).get(phase, []))
        system = CLI_SYSTEM.format(root=t.root)
        if t.provider_id == "claude-cli":
            args += ["--append-system-prompt", system]
            body = prompt
        else:
            body = f"{system}\n\nTask:\n{prompt}"
        if phase == "plan":
            body += ("\n\nFirst make a concrete step-by-step plan only (files to create or change, commands to "
                     "run). Do not change anything yet - the user will review the plan.")
        t.add_step("info", {"plan": "Planning (read-only)", "edits": "Running - edits allowed",
                            "all": "Running - all actions allowed"}[phase] + f" with {prov.name}")
        self.msg_step, self.msg_text = None, ""
        try:
            job = prov.chat([P.Message("user", body)], model=t.model or None, cwd=str(t.root), purpose="agent",
                            agent_args=args, timeout=1800)
        except Exception as e:  # noqa: BLE001
            t.fail(f"{type(e).__name__}: {e}")
            return
        t._job = job
        job.delta.connect(self._on_delta)
        job.event.connect(self._on_event)
        job.finished.connect(self._on_finished)
        job.failed.connect(self._on_failed)

    # ---------------------------------------------------------------- stream
    def _close_message(self):
        if self.msg_step is not None:
            self.task.update_step(self.msg_step, status="done", detail=self.msg_text.strip())
            if not self.msg_text.strip():
                self.task.steps.remove(self.msg_step)
                self.task.step_changed.emit(Step("removed", "", id=self.msg_step.id))
        self.msg_step, self.msg_text = None, ""

    def _on_delta(self, s: str):
        t = self.task
        if not t.running:
            return
        self.msg_text += s
        if self.msg_step is None:
            self.msg_step = t.add_step("message", "Agent", status="running")
        t.update_step(self.msg_step, detail=self.msg_text)

    def _tool_start(self, tid: str, name: str, inp: dict):
        t = self.task
        self._close_message()
        inp = inp if isinstance(inp, dict) else {"input": inp}
        kind = _cli_kind(name)
        title, path = _cli_title(kind, name, inp)
        rel = ""
        if path:
            try:
                rel = rel_path(t.root, safe_join(t.root, path))
            except ValueError:
                rel = path
            if rel and rel != path:
                title = title.replace(path, rel)
        detail = ""
        if kind == "command":
            detail = _first(inp, "command", "cmd")
        elif kind == "plan":
            md = _todos_md(inp.get("todos"))
            detail = md
            if md:
                t.set_plan(md)
        elif kind not in ("read", "write", "edit"):
            detail = json.dumps(inp, ensure_ascii=False)[:600]
        step = t.add_step(kind if kind != "plan" else "plan", title, detail=detail, tool=name, path=rel,
                          status="running", args={k: (v if len(str(v)) < 400 else str(v)[:400] + "...")
                                                  for k, v in inp.items()})
        if tid:
            self.tools[tid] = step
        return step

    def _tool_end(self, tid: str, output: str, error: bool):
        t = self.task
        step = self.tools.pop(tid, None) if tid else None
        if step is None:
            return
        t.update_step(step, output=(output or "")[-8000:], status="failed" if error else "done")
        if step.kind in ("write", "edit") and step.path:
            self._scan(only=step.path)

    def _on_event(self, obj):
        if not self.task.running or not isinstance(obj, dict):
            return
        pid = self.task.provider_id
        typ = obj.get("type", "")
        try:
            if pid in ("claude-cli", "cursor-cli"):
                if typ in ("assistant", "user"):
                    for c in (obj.get("message") or {}).get("content") or []:
                        if not isinstance(c, dict):
                            continue
                        if c.get("type") == "tool_use":
                            self._tool_start(c.get("id", ""), c.get("name", ""), c.get("input") or {})
                        elif c.get("type") == "tool_result":
                            self._tool_end(c.get("tool_use_id", ""), _tool_output(c.get("content")),
                                           bool(c.get("is_error")))
                        elif c.get("type") == "text" and typ == "assistant" and self.msg_step is None \
                                and c.get("text") and not self._streamed:
                            self._on_delta(c["text"])
                elif typ == "stream_event":
                    self._streamed = True
                elif typ == "system" and obj.get("subtype") == "init" and obj.get("model"):
                    self.task.add_step("info", f"{self.task.provider().name} started (model {obj.get('model')})")
                elif typ == "result":
                    if isinstance(obj.get("result"), str):
                        self.final = obj["result"]
            elif pid in ("gemini-cli", "qwen-cli"):
                if typ == "tool_use":
                    self._tool_start(obj.get("tool_id", ""), obj.get("tool_name", ""), obj.get("parameters") or {})
                elif typ == "tool_result":
                    out = obj.get("output")
                    err = obj.get("error")
                    self._tool_end(obj.get("tool_id", ""), _tool_output(out if out is not None else err),
                                   obj.get("status") not in (None, "success"))
                elif typ == "init" and obj.get("model"):
                    self.task.add_step("info", f"{self.task.provider().name} started (model {obj.get('model')})")
            elif pid == "codex-cli":
                item = obj.get("item") or {}
                it = item.get("type", "")
                if typ == "item.started" and it in ("command_execution", "mcp_tool_call", "web_search"):
                    self._tool_start(item.get("id", ""), it, {"command": item.get("command", ""),
                                                              "query": item.get("query", "")})
                elif typ == "item.completed":
                    if it == "command_execution":
                        if item.get("id") not in self.tools:
                            self._tool_start(item.get("id", ""), it, {"command": item.get("command", "")})
                        self._tool_end(item.get("id", ""), item.get("aggregated_output", ""),
                                       item.get("exit_code") not in (0, None))
                    elif it == "file_change":
                        for ch in item.get("changes") or []:
                            s = self._tool_start("", "file_change", {"path": ch.get("path", "")})
                            self.task.update_step(s, status="done", output=ch.get("kind", ""))
                            if s.path:
                                self._scan(only=s.path)
                    elif it in ("mcp_tool_call", "web_search"):
                        self._tool_end(item.get("id", ""), json.dumps(item.get("result", ""))[:2000], False)
                    elif it == "todo_list":
                        md = _todos_md(item.get("items"))
                        if md:
                            self.task.set_plan(md)
            elif pid == "opencode-cli":
                part = obj.get("part") or {}
                if typ == "tool_use" or part.get("type") == "tool":
                    st = part.get("state") or {}
                    tid = part.get("callID") or part.get("id") or ""
                    if tid not in self.tools:
                        self._tool_start(tid, part.get("tool", ""), st.get("input") or {})
                    if st.get("status") in ("completed", "error"):
                        self._tool_end(tid, _tool_output(st.get("output") or st.get("error")),
                                       st.get("status") == "error")
        except Exception as e:  # noqa: BLE001 - a strange event must not stop the task
            self.task.add_step("info", f"(could not read an event: {e})")

    _streamed = False
    final = ""

    def _on_failed(self, err: str):
        t = self.task
        self._close_message()
        if err == "Cancelled" or not t.running:
            return
        self._scan()
        t.fail(err)

    def _on_finished(self, text: str):
        t = self.task
        if not t.running:
            return
        if self.msg_step is None and text.strip() and not any(s.kind == "message" for s in t.steps[-3:]):
            self._on_delta(text)
        final_text = (self.msg_text or text).strip()
        self._close_message()
        for s in list(self.tools.values()):
            t.update_step(s, status="done")
        self.tools.clear()
        self._scan()
        if self.phase == "plan":
            self.plan_text = text.strip() or final_text
            t.set_plan(self.plan_text)
            self.plan_step = t.add_step("approval", "Review the plan - approve to let the agent make the changes",
                                        detail=self.plan_text, status="pending", tool="plan")
            t.set_status("waiting")
            t.approval_needed.emit(self.plan_step)
            return
        t.summary = text.strip() or final_text or "Done."
        last = next((s for s in reversed(t.steps) if s.kind == "message"), None)
        same = last is not None and last.detail.strip() == t.summary.strip()
        t.add_step("result", "Finished", detail="" if same else t.summary)
        t.set_status("done")

    def approved(self, step: Step, ok: bool, reason: str = ""):
        t = self.task
        if step is not self.plan_step:
            return
        self.plan_step = None
        if not ok:
            t.update_step(step, status="rejected", output="Plan rejected" + (f": {reason}" if reason else ""))
            t.summary = "The plan was rejected."
            t.set_status("cancelled")
            return
        t.update_step(step, status="done", output="Approved")
        phase = "all" if t.permission == "auto_all" else "edits"
        prompt = (f"{t.prompt}\n\nThe user approved this plan - carry it out now:\n{self.plan_text}"
                  + (f"\n\nUser note: {reason}" if reason else ""))
        self._run(phase, prompt)

    # ---------------------------------------------------------------- changes
    def _scan(self, only: str = ""):
        """Compare the folder with the snapshot; record changed files (with their originals) for review."""
        t = self.task
        snap = self.snapshot
        if snap is None:
            return
        if only:
            p = t.root / only
            st = None
            try:
                s = p.stat()
                st = (s.st_size, s.st_mtime)
            except OSError:
                pass
            old = snap.stat.get(only)
            if st is None and old is None:
                return
            if st == old:
                return
            items = [(only, "deleted" if st is None else ("added" if old is None else "modified"))]
        else:
            items = snap.changed()
        for rel, what in items:
            if rel not in t.checkpoint.manifest:
                if what == "added":
                    t.checkpoint.save_bytes(rel, None)
                elif rel in snap.data:
                    t.checkpoint.save_bytes(rel, snap.data[rel])
                else:
                    t.checkpoint.save_bytes(rel, None, backup=False)
            if rel in t.changes and t.changes[rel].status != "pending" and what != "deleted":
                t.changes[rel].status = "pending"
            t.record_change(rel, deleted=what == "deleted")
            if what != "deleted":
                _notify_file_written(t.root / rel)


# ============================================================================ manager
class AgentManager(QObject):
    """All agent tasks of the session (several can run at the same time)."""

    task_added = pyqtSignal(object)
    task_removed = pyqtSignal(object)
    task_changed = pyqtSignal(object)
    notify = pyqtSignal(object, str, str)          # task, kind ('approval' | 'done' | 'failed'), text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks: list[AgentTask] = []
        self.loaded_folders: set[str] = set()

    def create(self, prompt: str, folder, provider_id: str = "", model: str = "", engine: str = "",
               permission: str = "ask", max_steps: int = 25, start: bool = True) -> AgentTask:
        t = AgentTask(prompt, folder, provider_id, model, engine, permission, max_steps, parent=self)
        self._adopt(t)
        if start:
            t.start()
        return t

    def _adopt(self, t: AgentTask, front: bool = True):
        if front:
            self.tasks.insert(0, t)
        else:
            self.tasks.append(t)
        t.status_changed.connect(lambda _s, t=t: self.task_changed.emit(t))
        t.changes_changed.connect(lambda t=t: self.task_changed.emit(t))
        t.approval_needed.connect(lambda s, t=t: self.notify.emit(t, "approval", s.title))
        t.finished.connect(lambda st, t=t: self.notify.emit(t, "done" if st == "done" else st,
                                                            t.summary or t.error or STATUS_TITLES.get(st, st)))
        self.task_added.emit(t)

    def remove(self, t: AgentTask) -> None:
        if t.running:
            t.stop()
        if t in self.tasks:
            self.tasks.remove(t)
            self.task_removed.emit(t)

    def running(self) -> list[AgentTask]:
        return [t for t in self.tasks if t.running]

    def load_history(self, folder) -> list[AgentTask]:
        """Tasks saved earlier in <folder>/.radide/ai/tasks/*/task.json (oldest last)."""
        folder = Path(folder).resolve()
        key = os.path.normcase(str(folder))
        if key in self.loaded_folders:
            return []
        self.loaded_folders.add(key)
        known = {t.id for t in self.tasks}
        out = []
        base = folder / ".radide" / "ai" / "tasks"
        if not base.is_dir():
            return out
        for f in sorted(base.glob("*/task.json"), reverse=True)[:50]:
            t = AgentTask.load(f, parent=self)
            if t is not None and t.id not in known:
                out.append(t)
                self._adopt(t, front=False)
        return out

    def stop_all(self) -> None:
        for t in self.running():
            t.stop()


_manager: AgentManager | None = None


def manager() -> AgentManager:
    global _manager
    if _manager is None:
        _manager = AgentManager()
    return _manager


__all__ = ["PERMISSIONS", "PERMISSION_TITLES", "STATUS_TITLES", "Step", "FileChange", "Artifact", "Checkpoint",
           "Snapshot", "AgentTask", "AgentManager", "BuiltinEngine", "CliEngine", "manager", "parse_tool_call",
           "unified_diff", "diff_stats", "safe_join", "on_file_written", "CLI_ARGS"]
