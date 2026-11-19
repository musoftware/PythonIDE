"""AI core (docs/CONTRACTS.md 9.1): messages, streaming jobs, the provider base class, the
registry, per-purpose defaults, secrets and small helpers.

Every provider streams on a worker thread; text reaches the Qt (UI) thread through queued
signals, so the UI never blocks.  Concrete providers live in providers_cli.py (official CLI
agents that log in with the user's own account) and providers_http.py (local servers and
optional API keys)."""
from __future__ import annotations

import os
import re
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Callable, Iterable

from PyQt6.QtCore import QCoreApplication, QEventLoop, QObject, QSettings, Qt, QTimer, pyqtSignal

PURPOSES = ("chat", "complete", "edit", "agent", "commit")
KINDS = ("cli", "local", "api", "web")


class AIError(RuntimeError):
    """A provider failed; the message is meant for the user."""


# ===================================================================== messages
@dataclass
class Message:
    role: str            # "system" | "user" | "assistant"
    content: str

    @staticmethod
    def of(m) -> "Message":
        if isinstance(m, Message):
            return m
        if isinstance(m, dict):
            return Message(str(m.get("role", "user")), str(m.get("content", "")))
        if isinstance(m, (tuple, list)) and len(m) == 2:
            return Message(str(m[0]), str(m[1]))
        return Message("user", str(m))


def normalize(messages, system: str | None = None) -> tuple[str, list[Message]]:
    """-> (system text, [user/assistant messages]).  A str is one user message."""
    if isinstance(messages, (str, Message, dict)):
        messages = [messages]
    msgs = [Message.of(m) for m in (messages or [])]
    sys_parts = [m.content for m in msgs if m.role == "system" and m.content]
    if system:
        sys_parts.insert(0, system)
    rest = [m for m in msgs if m.role != "system"]
    return "\n\n".join(sys_parts), rest


def flatten(messages: list[Message], system: str = "", system_inline: bool = True) -> str:
    """One prompt text for providers that take a single prompt (CLI agents)."""
    parts = []
    if system and system_inline:
        parts.append(f"Instructions:\n{system}\n")
    if len(messages) == 1 and messages[0].role == "user":
        parts.append(messages[0].content)
        return "\n".join(parts)
    if len(messages) > 1:
        parts.append("Conversation so far:\n")
        for m in messages[:-1]:
            who = "User" if m.role == "user" else "Assistant"
            parts.append(f"### {who}\n{m.content}\n")
    if messages:
        last = messages[-1]
        parts.append(("### User\n" if len(messages) > 1 else "") + last.content)
    return "\n".join(parts)


# ===================================================================== jobs
_live_jobs: set = set()             # keep running jobs alive even if the caller drops them


class ChatJob(QObject):
    """One streaming request.  Signals arrive on the thread that created the job (the UI thread):
    delta(str) for each new piece of text, then exactly one of finished(full_text) / failed(message).
    cancel() stops it (failed("Cancelled") is emitted at once).  `event(object)` carries raw JSON
    events of CLI agents (claude stream-json ...) for tools that want the details."""

    delta = pyqtSignal(str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    event = pyqtSignal(object)
    _chunk = pyqtSignal(str)
    _evt = pyqtSignal(object)
    _end = pyqtSignal(bool, str)

    def __init__(self, provider_id: str = "", model: str = "", parent=None):
        super().__init__(parent)
        self.provider_id, self.model = provider_id, model
        self.text = ""
        self.done = False
        self.error = ""
        self.cancelled = False
        self.started_at = time.time()
        self.meta: dict = {}          # usage, session id, command line ... (provider specific)
        self.postprocess: Callable[[str], str] | None = None
        self._stop = threading.Event()
        self._aborts: list[Callable[[], None]] = []
        self._lock = threading.Lock()
        q = Qt.ConnectionType.QueuedConnection
        self._chunk.connect(self._on_chunk, q)
        self._evt.connect(self.event.emit, q)
        self._end.connect(self._on_end, q)

    # ---------------------------------------------------------- worker side (any thread)
    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def emit_delta(self, s: str) -> None:
        if s and not self._stop.is_set():
            self._chunk.emit(s)

    def emit_event(self, obj) -> None:
        if not self._stop.is_set():
            self._evt.emit(obj)

    def on_abort(self, fn: Callable[[], None]) -> None:
        """Register a callable that interrupts the blocking work (close a socket, kill a process)."""
        with self._lock:
            if self._stop.is_set():
                run_now = True
            else:
                self._aborts.append(fn)
                run_now = False
        if run_now:
            _safe(fn)

    def start(self, runner: Callable[["ChatJob"], str | None]) -> "ChatJob":
        """Run runner(job) on a worker thread.  It calls job.emit_delta() and returns the full text
        (or None = the concatenated deltas); an exception becomes failed(str(exc))."""
        _live_jobs.add(self)

        def work():
            try:
                full = runner(self)
                self._end.emit(True, full if full is not None else "\x00")
            except Exception as e:  # noqa: BLE001 - reported to the UI
                msg = str(e) if isinstance(e, AIError) else f"{type(e).__name__}: {e}"
                if not isinstance(e, AIError) and os.environ.get("RADIDE_AI_DEBUG"):
                    traceback.print_exc()
                self._end.emit(False, msg or type(e).__name__)
        threading.Thread(target=work, name=f"ai-{self.provider_id}", daemon=True).start()
        return self

    def fail_soon(self, message: str) -> "ChatJob":
        """Fail asynchronously (so callers can still connect their slots)."""
        _live_jobs.add(self)
        self._end.emit(False, message)
        return self

    # ---------------------------------------------------------- UI side
    def _on_chunk(self, s: str) -> None:
        if self.done:
            return
        self.text += s
        self.delta.emit(s)

    def _on_end(self, ok: bool, payload: str) -> None:
        if self.done:
            return
        self.done = True
        _live_jobs.discard(self)
        if ok:
            full = self.text if payload == "\x00" else payload
            if self.postprocess is not None:
                try:
                    full = self.postprocess(full)
                except Exception:  # noqa: BLE001
                    pass
            self.text = full
            self.finished.emit(full)
        else:
            self.error = payload
            self.failed.emit(payload)

    def cancel(self) -> None:
        if self.done:
            return
        self.cancelled = True
        with self._lock:
            self._stop.set()
            aborts, self._aborts = self._aborts, []
        for fn in aborts:
            _safe(fn)
        self.done = True
        self.error = "Cancelled"
        _live_jobs.discard(self)
        self.failed.emit("Cancelled")

    def elapsed(self) -> float:
        return time.time() - self.started_at


def _safe(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001
        pass


_app_for_scripts = None


def run_sync(job: ChatJob, timeout: float = 60) -> str:
    """Wait for a job (tests / scripts only - never call it on the UI thread of the IDE)."""
    global _app_for_scripts
    if QCoreApplication.instance() is None:
        _app_for_scripts = QCoreApplication(sys.argv[:1])
    if not job.done:
        loop = QEventLoop()
        job.finished.connect(lambda _t: loop.quit())
        job.failed.connect(lambda _e: loop.quit())
        timer = QTimer()
        timer.setSingleShot(True)
        timed_out = []
        timer.timeout.connect(lambda: (timed_out.append(1), loop.quit()))
        timer.start(int(timeout * 1000))
        if not job.done:
            loop.exec()
        timer.stop()
        if timed_out and not job.done:
            job.cancel()
            raise TimeoutError(f"AI job timed out after {timeout:g} s")
    if job.error:
        raise AIError(job.error)
    return job.text


# ===================================================================== settings & secrets
def settings() -> QSettings:
    """The IDE's QSettings (tests use their RADIDE-TEST organisation, like radide.app.ide_settings)."""
    org = QCoreApplication.organizationName()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    return QSettings("RADIDE", "RADIDE")


def _service() -> str:
    org = QCoreApplication.organizationName()
    return org if org.upper().startswith("RADIDE-TEST") else "RADIDE"


def _keyring():
    try:
        import keyring  # type: ignore
        import keyring.errors  # type: ignore  # noqa: F401
        kr = keyring.get_keyring()
        if "fail" in type(kr).__module__.lower() or "null" in type(kr).__name__.lower():
            return None
        return keyring
    except Exception:  # noqa: BLE001
        return None


def secret_backend() -> str:
    """'keyring' (Windows Credential Manager ...) or 'settings' (plain QSettings - less safe)."""
    return "keyring" if _keyring() is not None else "settings"


def get_secret(name: str) -> str:
    kr = _keyring()
    if kr is not None:
        try:
            v = kr.get_password(_service(), name)
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass
    return str(settings().value(f"ai/secret/{name}", "") or "")


def set_secret(name: str, value: str) -> str:
    """Store (or delete when empty) a secret.  Returns the backend used; with 'settings' the
    caller should warn that the key is stored unencrypted."""
    value = (value or "").strip()
    kr = _keyring()
    s = settings()
    if kr is not None:
        try:
            if value:
                kr.set_password(_service(), name, value)
            else:
                try:
                    kr.delete_password(_service(), name)
                except Exception:  # noqa: BLE001 - not stored
                    pass
            s.remove(f"ai/secret/{name}")
            return "keyring"
        except Exception:  # noqa: BLE001 - fall back to settings
            pass
    if value:
        s.setValue(f"ai/secret/{name}", value)
    else:
        s.remove(f"ai/secret/{name}")
    return "settings"


# ===================================================================== provider base
class Provider:
    """Base class.  Subclasses implement _run_chat(job, system, messages, model, opts) on the
    worker thread (emit deltas, return the full text) and fast detection in _detect()."""

    id = ""
    name = ""
    kind = "api"
    description = ""
    install_hint = ""            # how to install the tool / where to get a key
    login_hint = ""              # how to sign in
    homepage = ""
    npm_package = ""             # CLI providers installable with npm
    builtin_models: tuple = ()
    fallback_default = ""
    supports_fim = False
    needs_key = False
    DETECT_TTL = 15.0

    def __init__(self):
        self._avail_cache: tuple[float, tuple[bool, str]] | None = None
        self._models_cache: list[str] | None = None
        self._refreshing = False

    def __repr__(self):
        return f"<ai provider {self.id}>"

    # ---------------------------------------------------------- config
    def config(self, key: str, default=""):
        v = settings().value(f"ai/provider/{self.id}/{key}", default)
        return default if v is None else v

    def set_config(self, key: str, value) -> None:
        s = settings()
        if value in (None, ""):
            s.remove(f"ai/provider/{self.id}/{key}")
        else:
            s.setValue(f"ai/provider/{self.id}/{key}", value)
        self.invalidate()

    @property
    def default_model(self) -> str:
        m = str(self.config("model", "") or "")
        if m:
            return m
        if self.fallback_default:
            return self.fallback_default
        ms = self.models()
        return ms[0] if ms else ""

    def enabled(self) -> bool:
        return str(self.config("enabled", "true")).lower() not in ("0", "false", "no")

    # ---------------------------------------------------------- detection
    def available(self) -> tuple[bool, str]:
        now = time.time()
        c = self._avail_cache
        if c is not None and now - c[0] < self.DETECT_TTL:
            return c[1]
        try:
            res = self._detect()
        except Exception as e:  # noqa: BLE001
            res = (False, f"detection failed: {e}")
        self._avail_cache = (now, res)
        return res

    def _detect(self) -> tuple[bool, str]:
        return True, ""

    def invalidate(self) -> None:
        self._avail_cache = None

    # ---------------------------------------------------------- models
    def models(self) -> list[str]:
        """Known models (fast: cached; a background refresh updates it and emits
        ai.hub.models_changed(provider_id))."""
        if self._models_cache is None:
            cached = settings().value(f"ai/provider/{self.id}/models_cache", None)
            if isinstance(cached, str):
                cached = [cached]
            self._models_cache = [str(m) for m in cached] if cached else list(self.builtin_models)
            self.refresh_models()
        out = list(self._models_cache)
        extra = str(self.config("model", "") or "")
        if extra and extra not in out:
            out.insert(0, extra)
        return out

    def refresh_models(self) -> None:
        """Ask the provider for its models on a worker thread (no-op when it cannot list them)."""
        if self._refreshing or type(self)._list_models is Provider._list_models:
            return
        self._refreshing = True

        def work():
            try:
                ms = self._list_models()
                if ms:
                    self._models_cache = list(dict.fromkeys(ms))
                    hub()._models.emit(self.id, self._models_cache)
            except Exception:  # noqa: BLE001 - keep the cached list
                pass
            finally:
                self._refreshing = False
        threading.Thread(target=work, name=f"ai-models-{self.id}", daemon=True).start()

    def _list_models(self) -> list[str]:
        return []

    # ---------------------------------------------------------- requests
    def chat(self, messages, model: str | None = None, system: str | None = None,
             temperature: float | None = None, max_tokens: int | None = None, cwd: str | None = None,
             **opts) -> ChatJob:
        model = model or self.default_model
        job = ChatJob(self.id, model)
        sys_text, msgs = normalize(messages, system)
        if not msgs:
            return job.fail_soon("Nothing to send (no user message).")
        opts.update(temperature=temperature, max_tokens=max_tokens, cwd=cwd)
        job.meta["purpose"] = opts.get("purpose", "chat")
        return job.start(lambda j: self._run_chat(j, sys_text, msgs, model, opts))

    def _run_chat(self, job: ChatJob, system: str, messages: list[Message], model: str, opts: dict) -> str | None:
        raise AIError(f"{self.name} cannot chat")

    def complete(self, prefix: str, suffix: str = "", language: str = "", model: str | None = None,
                 max_tokens: int = 160) -> ChatJob:
        """Inline completion: the text that goes between prefix and suffix.  Default: a prompt
        to the chat model (providers with FIM override this)."""
        sys_text, user = completion_prompt(prefix, suffix, language)
        job = self.chat([Message("user", user)], model=model, system=sys_text, temperature=0.2,
                        max_tokens=max_tokens, purpose="complete")
        job.postprocess = lambda t: clean_completion(t, prefix, suffix)
        return job

    # ---------------------------------------------------------- UI info
    def status_text(self) -> str:
        ok, why = self.available()
        return ("Ready" if ok else "Unavailable") + (f" - {why}" if why else "")


# ===================================================================== completion helpers
def completion_prompt(prefix: str, suffix: str, language: str, before: int = 3000, after: int = 1200):
    pre = prefix[-before:]
    suf = suffix[:after]
    lang = language or "code"
    system = ("You are a code completion engine inside an IDE. Reply with ONLY the exact text to insert at "
              "<CURSOR> - no explanations, no markdown fences, do not repeat the text before or after the "
              "cursor. Keep it short (finish the current statement or block). If nothing fits, reply with an "
              "empty answer.")
    user = f"Language: {lang}\n\n<CODE>\n{pre}<CURSOR>{suf}\n</CODE>\n\nText to insert at <CURSOR>:"
    return system, user


def clean_completion(text: str, prefix: str = "", suffix: str = "") -> str:
    t = text or ""
    blocks = extract_code_blocks(t)
    if blocks:
        t = blocks[0][1]
    t = t.replace("<CURSOR>", "")
    t = re.sub(r"^\s*</?CODE>\s*", "", t)
    # drop a repeated copy of the current line's beginning
    line_start = prefix.rsplit("\n", 1)[-1]
    if line_start.strip() and t.startswith(line_start):
        t = t[len(line_start):]
    # drop an echoed suffix
    s = suffix.lstrip()
    if s and len(s) > 3:
        k = t.find(s[:min(len(s), 40)])
        if k > 0:
            t = t[:k]
    return t.rstrip() if "\n" in t.strip() else t.rstrip("\n")


_FENCE = re.compile(r"(^|\n)[ \t]*(```+|~~~+)[ \t]*([\w#+.\-]*)[^\n]*\n(.*?)(\n[ \t]*\2[ \t]*(?=\n|$)|$)", re.S)


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Fenced code blocks of a markdown answer -> [(language, code)] (an unclosed last fence counts)."""
    out = []
    for m in _FENCE.finditer(text or ""):
        code = m.group(4)
        if code.strip():
            out.append((m.group(3).lower(), code.rstrip("\n")))
    return out


# ===================================================================== registry & defaults
_providers: dict[str, Provider] = {}
_loaded = False


def register(provider: Provider) -> Provider:
    """Add (or replace) a provider - e.g. the web chats of radide/features/ai_web.py (kind 'web')."""
    _providers[provider.id] = provider
    if _hub is not None:
        _hub.providers_changed.emit()
    return provider


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    if QCoreApplication.instance() is not None:
        hub()                         # create the signal hub on the application's thread
    from . import providers_cli, providers_http
    for p in providers_cli.create() + providers_http.create():
        _providers.setdefault(p.id, p)


def providers(kind: str | None = None) -> list[Provider]:
    _ensure_loaded()
    ps = list(_providers.values())
    return [p for p in ps if p.kind == kind] if kind else ps


def get(provider_id: str) -> Provider:
    _ensure_loaded()
    try:
        return _providers[provider_id]
    except KeyError:
        raise KeyError(f"unknown AI provider {provider_id!r}; known: {', '.join(_providers)}") from None


# best free choices first: local models, then CLI agents signed in with the user's account, then keys
_PREFERENCE = {
    "chat": ("ollama", "lmstudio", "claude-cli", "gemini-cli", "codex-cli", "copilot-cli", "qwen-cli",
             "opencode-cli", "cursor-cli", "openai-compatible", "openrouter", "groq", "deepseek", "mistral",
             "gemini-api", "anthropic", "openai", "xai"),
    "complete": ("ollama", "lmstudio", "openai-compatible", "mistral", "deepseek", "groq", "openrouter",
                 "gemini-api", "openai", "anthropic", "xai", "claude-cli", "gemini-cli", "codex-cli",
                 "opencode-cli", "qwen-cli", "copilot-cli", "cursor-cli"),
    "agent": ("claude-cli", "gemini-cli", "codex-cli", "copilot-cli", "opencode-cli", "qwen-cli", "cursor-cli",
              "ollama", "lmstudio", "anthropic", "openai", "gemini-api", "openrouter", "openai-compatible",
              "deepseek", "groq", "mistral", "xai"),
}
_PREFERENCE["edit"] = _PREFERENCE["chat"]
_PREFERENCE["commit"] = _PREFERENCE["chat"]


def default(purpose: str = "chat") -> tuple[Provider, str]:
    """(provider, model) for a purpose: the user's choice (Tools > Options > AI) or the best
    available free option."""
    if purpose not in PURPOSES:
        purpose = "chat"
    _ensure_loaded()
    s = settings()
    pid = str(s.value(f"ai/default/{purpose}/provider", "") or "")
    model = str(s.value(f"ai/default/{purpose}/model", "") or "")
    if pid and pid in _providers:
        p = _providers[pid]
        return p, model or p.default_model
    order = list(_PREFERENCE.get(purpose, _PREFERENCE["chat"]))
    order += [i for i in _providers if i not in order]
    first = None
    for i in order:
        p = _providers.get(i)
        if p is None or not p.enabled():
            continue
        first = first or p
        if p.kind == "web":
            continue
        ok, _why = p.available()
        if ok:
            return p, p.default_model
    p = first or next(iter(_providers.values()))
    return p, p.default_model


def set_default(purpose: str, provider_id: str, model: str = "") -> None:
    if purpose not in PURPOSES:
        raise ValueError(f"purpose must be one of {PURPOSES}")
    s = settings()
    if provider_id:
        s.setValue(f"ai/default/{purpose}/provider", provider_id)
        s.setValue(f"ai/default/{purpose}/model", model or "")
    else:
        s.remove(f"ai/default/{purpose}/provider")
        s.remove(f"ai/default/{purpose}/model")
    s.sync()
    if _hub is not None:
        _hub.defaults_changed.emit(purpose)


def chat(messages, purpose: str = "chat", **kw) -> ChatJob:
    """Shortcut: chat with the default provider of a purpose."""
    p, model = default(purpose)
    kw.setdefault("model", model)
    return p.chat(messages, purpose=purpose, **kw)


def refresh_all() -> None:
    """Forget cached detection (after installing a CLI / starting Ollama ...)."""
    for p in providers():
        p.invalidate()
        p.refresh_models()


# ===================================================================== hub (app-wide signals)
class _Hub(QObject):
    models_changed = pyqtSignal(str)          # provider id
    defaults_changed = pyqtSignal(str)        # purpose
    providers_changed = pyqtSignal()
    _models = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self._models.connect(self._on_models, Qt.ConnectionType.QueuedConnection)

    def _on_models(self, pid: str, models) -> None:
        try:
            settings().setValue(f"ai/provider/{pid}/models_cache", list(models))
        except Exception:  # noqa: BLE001
            pass
        self.models_changed.emit(pid)


_hub: _Hub | None = None


def hub() -> _Hub:
    global _hub
    if _hub is None:
        _hub = _Hub()
        app = QCoreApplication.instance()
        if app is not None and _hub.thread() is not app.thread():
            _hub.moveToThread(app.thread())
    return _hub


def iter_lines(stream, job: ChatJob) -> Iterable[str]:
    """Lines of a binary stream (HTTP response / pipe) as text, stopping on cancel."""
    import codecs
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    buf = ""
    while not job.stopping:
        try:
            chunk = stream.readline()
        except Exception:  # noqa: BLE001 - socket closed by cancel()
            if job.stopping:
                return
            raise
        if not chunk:
            break
        buf += dec.decode(chunk)
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            yield line.rstrip("\r")
    buf += dec.decode(b"", final=True)
    if buf and not job.stopping:
        yield buf.rstrip("\r")
