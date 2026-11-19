"""HTTP providers: local model servers (Ollama, LM Studio, any OpenAI-compatible server such as
llama.cpp) and the optional API-key services (OpenAI, Anthropic, Gemini API, OpenRouter, Groq,
DeepSeek, Mistral, xAI).  Only the standard library is used (urllib, streaming SSE / NDJSON)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .providers import (AIError, ChatJob, Message, Provider, clean_completion, completion_prompt, get_secret,
                        iter_lines)

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
USER_AGENT = "RAD-IDE/1.0"


# ===================================================================== http helpers
def _request(url: str, body: dict | None = None, headers: dict | None = None, method: str | None = None,
             timeout: float = 120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = {"User-Agent": USER_AGENT, "Accept": "application/json, text/event-stream"}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method or ("POST" if data else "GET"))
    # local servers must not go through a system proxy
    if urllib.parse.urlparse(url).hostname in ("127.0.0.1", "localhost", "::1"):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def _get_json(url: str, headers: dict | None = None, timeout: float = 8) -> dict:
    with _request(url, headers=headers, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace") or "{}")


def _http_error(name: str, e: Exception, key_hint: str = "") -> AIError:
    if isinstance(e, urllib.error.HTTPError):
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            body = ""
        detail = body
        try:
            j = json.loads(body)
            err = j.get("error", j)
            if isinstance(err, dict):
                detail = err.get("message") or err.get("error") or json.dumps(err)[:300]
            elif isinstance(err, str):
                detail = err
        except Exception:  # noqa: BLE001
            pass
        detail = (detail or e.reason or "").strip()[:500]
        msg = f"{name}: HTTP {e.code} {detail}"
        if e.code in (401, 403):
            msg += f"\nThe API key was rejected. {key_hint or 'Check it in Tools > Options > AI.'}"
        elif e.code == 429:
            msg += "\nRate limit or quota reached - wait a moment or pick another provider."
        elif e.code == 404:
            msg += "\nCheck the model name and the base URL."
        return AIError(msg)
    if isinstance(e, urllib.error.URLError):
        reason = e.reason
        if isinstance(reason, ConnectionRefusedError) or "refused" in str(reason).lower():
            return AIError(f"{name}: the server is not running (connection refused).")
        return AIError(f"{name}: cannot connect ({reason}).")
    if isinstance(e, (socket.timeout, TimeoutError)):
        return AIError(f"{name}: the server did not answer in time.")
    return AIError(f"{name}: {type(e).__name__}: {e}")


def _open_stream(job: ChatJob, name: str, url: str, body: dict, headers: dict | None = None,
                 key_hint: str = "", timeout: float = 180):
    try:
        resp = _request(url, body, headers, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        if job.stopping:
            return None
        raise _http_error(name, e, key_hint) from None
    job.on_abort(resp.close)
    return resp


def _sse(resp, job: ChatJob):
    """Data payloads of a server-sent-events stream (event name kept in the dict as '_event')."""
    event = ""
    for line in iter_lines(resp, job):
        if not line:
            event = ""
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                obj = json.loads(data)
            except ValueError:
                continue
            if isinstance(obj, dict):
                obj.setdefault("_event", event)
            yield obj


def _local_up(url: str, timeout: float = 0.6) -> bool:
    try:
        u = urllib.parse.urlparse(url)
        port = u.port or (443 if u.scheme == "https" else 80)
        with socket.create_connection((u.hostname or "127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


# ===================================================================== OpenAI-compatible
class OpenAICompatible(Provider):
    """/v1/chat/completions with stream=true (SSE).  Used for OpenAI and every compatible service."""

    kind = "api"
    base_url_default = ""
    key_name = ""                 # secret name; "" = no key
    env_keys: tuple = ()
    key_url = ""
    needs_key = True
    fim_path = ""                 # e.g. "/fim/completions" (Mistral), "beta:/completions" (DeepSeek)
    fim_model = ""
    extra_headers: dict = {}

    def base_url(self) -> str:
        return str(self.config("base_url", "") or self.base_url_default).rstrip("/")

    def api_key(self) -> str:
        k = get_secret(self.key_name or self.id) if (self.key_name or self.needs_key) else ""
        if not k:
            for env in self.env_keys:
                if os.environ.get(env):
                    return os.environ[env]
        return k

    def _headers(self) -> dict:
        h = dict(self.extra_headers)
        k = self.api_key()
        if k:
            h["Authorization"] = f"Bearer {k}"
        return h

    def _detect(self):
        if self.needs_key and not self.api_key():
            where = f" (get one at {self.key_url})" if self.key_url else ""
            return False, f"No API key - add it in Tools > Options > AI{where}"
        if not self.base_url():
            return False, "No base URL set"
        return True, ("API key set" if self.needs_key else self.base_url())

    def _list_models(self):
        if self.needs_key and not self.api_key():
            return []
        j = _get_json(self.base_url() + "/models", self._headers())
        data = j.get("data", j.get("models", []))
        ids = [m.get("id") or m.get("name") for m in data if isinstance(m, dict)]
        return sorted(i for i in ids if i)

    @property
    def supports_fim(self):           # type: ignore[override]
        return bool(self.fim_path)

    def _check(self):
        ok, why = self.available()
        if not ok:
            raise AIError(f"{self.name}: {why}")

    def _run_chat(self, job, system, messages, model, opts):
        self._check()
        if not model:
            raise AIError(f"{self.name}: no model chosen (Tools > Options > AI).")
        msgs = ([{"role": "system", "content": system}] if system else []) + \
            [{"role": m.role, "content": m.content} for m in messages]
        body = {"model": model, "messages": msgs, "stream": True}
        if opts.get("temperature") is not None:
            body["temperature"] = opts["temperature"]
        if opts.get("max_tokens"):
            body["max_tokens"] = int(opts["max_tokens"])
        resp = _open_stream(job, self.name, self.base_url() + "/chat/completions", body, self._headers(),
                            self.key_url and f"Get a key at {self.key_url}.")
        if resp is None:
            return ""
        with resp:
            for obj in _sse(resp, job):
                if "error" in obj:
                    e = obj["error"]
                    raise AIError(f"{self.name}: {e.get('message', e) if isinstance(e, dict) else e}")
                for ch in obj.get("choices", []):
                    d = ch.get("delta") or ch.get("message") or {}
                    if d.get("content"):
                        job.emit_delta(d["content"])
                if obj.get("usage"):
                    job.meta["usage"] = obj["usage"]
        return None

    def complete(self, prefix, suffix="", language="", model=None, max_tokens=160):
        if not self.fim_path:
            return super().complete(prefix, suffix, language, model, max_tokens)
        model = model or str(self.config("fim_model", "") or "") or self.fim_model or self.default_model
        job = ChatJob(self.id, model)
        job.meta["purpose"] = "complete"

        def run(j):
            self._check()
            base = self.base_url()
            path = self.fim_path
            if path.startswith("beta:"):                 # DeepSeek: https://api.deepseek.com/beta
                base = base.rsplit("/v1", 1)[0] + "/beta"
                path = path[5:]
            body = {"model": model, "prompt": prefix[-6000:], "suffix": suffix[:2000], "stream": True,
                    "max_tokens": max_tokens, "temperature": 0.2}
            resp = _open_stream(j, self.name, base + path, body, self._headers())
            if resp is None:
                return ""
            with resp:
                for obj in _sse(resp, j):
                    for ch in obj.get("choices", []):
                        t = ch.get("text")
                        if t is None:
                            t = (ch.get("delta") or {}).get("content")
                        if t:
                            j.emit_delta(t)
            return None
        job.postprocess = lambda t: clean_completion(t, prefix, suffix)
        return job.start(run)


class OpenAI(OpenAICompatible):
    id, name = "openai", "OpenAI API"
    base_url_default = "https://api.openai.com/v1"
    env_keys = ("OPENAI_API_KEY",)
    key_url = "https://platform.openai.com/api-keys"
    builtin_models = ("gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini")
    install_hint = "Optional: needs a paid OpenAI API key."


class OpenRouter(OpenAICompatible):
    id, name = "openrouter", "OpenRouter"
    base_url_default = "https://openrouter.ai/api/v1"
    env_keys = ("OPENROUTER_API_KEY",)
    key_url = "https://openrouter.ai/keys"
    builtin_models = ("openrouter/auto", "deepseek/deepseek-chat-v3-0324:free", "meta-llama/llama-3.3-70b-instruct:free")
    extra_headers = {"HTTP-Referer": "https://github.com/radide", "X-Title": "RAD IDE"}
    install_hint = "Free key available; models ending in ':free' cost nothing."


class Groq(OpenAICompatible):
    id, name = "groq", "Groq"
    base_url_default = "https://api.groq.com/openai/v1"
    env_keys = ("GROQ_API_KEY",)
    key_url = "https://console.groq.com/keys"
    builtin_models = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
    install_hint = "Free tier key available."


class DeepSeek(OpenAICompatible):
    id, name = "deepseek", "DeepSeek API"
    base_url_default = "https://api.deepseek.com/v1"
    env_keys = ("DEEPSEEK_API_KEY",)
    key_url = "https://platform.deepseek.com/api_keys"
    builtin_models = ("deepseek-chat", "deepseek-reasoner")
    fim_path = "beta:/completions"
    fim_model = "deepseek-chat"


class Mistral(OpenAICompatible):
    id, name = "mistral", "Mistral (Codestral)"
    base_url_default = "https://api.mistral.ai/v1"
    env_keys = ("MISTRAL_API_KEY",)
    key_url = "https://console.mistral.ai/api-keys"
    builtin_models = ("codestral-latest", "mistral-small-latest", "mistral-large-latest")
    fim_path = "/fim/completions"
    fim_model = "codestral-latest"


class XAI(OpenAICompatible):
    id, name = "xai", "xAI Grok"
    base_url_default = "https://api.x.ai/v1"
    env_keys = ("XAI_API_KEY",)
    key_url = "https://console.x.ai"
    builtin_models = ("grok-3-mini", "grok-3")


class CustomOpenAI(OpenAICompatible):
    id, name = "openai-compatible", "OpenAI-compatible server"
    kind = "local"
    base_url_default = "http://127.0.0.1:8080/v1"
    needs_key = False
    key_name = "openai-compatible"
    description = "Any server that speaks the OpenAI API: llama.cpp server, vLLM, Jan, LocalAI, a custom URL ..."
    install_hint = "Set the base URL (llama.cpp: llama-server -m model.gguf --port 8080)."

    def _detect(self):
        url = self.base_url()
        if not url:
            return False, "No base URL set"
        host = urllib.parse.urlparse(url).hostname or ""
        if host in ("127.0.0.1", "localhost", "::1") and not _local_up(url, 0.3):
            return False, f"No server at {url} - start it or change the base URL"
        return True, url

    def api_key(self):
        return get_secret("openai-compatible")


class LMStudio(CustomOpenAI):
    id, name = "lmstudio", "LM Studio"
    base_url_default = "http://127.0.0.1:1234/v1"
    key_name = "lmstudio"
    description = "Local models served by LM Studio (Developer tab > Start server)."
    install_hint = "Install LM Studio (https://lmstudio.ai), load a model and start the local server."

    def api_key(self):
        return ""


# ===================================================================== Ollama
class Ollama(Provider):
    id, name, kind = "ollama", "Ollama (local)", "local"
    description = "Free local models (no account, works offline)."
    install_hint = "winget install Ollama.Ollama, then: ollama pull qwen2.5-coder:7b"
    homepage = "https://ollama.com"

    def __init__(self):
        super().__init__()
        self._caps: dict[str, list[str]] = {}

    def base_url(self) -> str:
        return str(self.config("base_url", "") or os.environ.get("OLLAMA_HOST", "") or
                   "http://127.0.0.1:11434").rstrip("/").replace("0.0.0.0", "127.0.0.1")

    @staticmethod
    def exe() -> str:
        p = shutil.which("ollama")
        if p:
            return p
        cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        return cand if os.path.isfile(cand) else ""

    def _detect(self):
        if _local_up(self.base_url(), 0.5):
            ms = self._models_cache or []
            if not ms:          # unknown yet (None) or an empty placeholder set by models() before its refresh
                try:
                    ms = self._list_models(timeout=1.5)
                    self._models_cache = ms
                except Exception:  # noqa: BLE001
                    # it answers the port but is busy (loading / generating): not "no model" - the
                    # model list is read again on the next detection or request
                    return True, "running (busy - the model list is read on the first request)"
            if not ms:
                return False, "Ollama runs but has no model - e.g. run: ollama pull qwen2.5-coder:7b"
            return True, f"running, {len(ms)} model(s)"
        if self.exe():
            return True, "installed, not running - it is started on the first request"
        return False, "Not installed. " + self.install_hint

    def _list_models(self, timeout: float = 5):
        j = _get_json(self.base_url() + "/api/tags", timeout=timeout)
        out = []
        for m in j.get("models", []):
            name = m.get("name") or m.get("model")
            fam = " ".join((m.get("details") or {}).get("families") or []).lower()
            if name and "bert" not in fam and "embed" not in name.lower():
                out.append(name)
        return out

    def capabilities(self, model: str) -> list[str]:
        if model not in self._caps:
            try:
                with _request(self.base_url() + "/api/show", {"model": model}, timeout=5) as r:
                    j = json.loads(r.read().decode("utf-8", errors="replace"))
                self._caps[model] = list(j.get("capabilities") or [])
            except Exception:  # noqa: BLE001
                return []
        return self._caps[model]

    @property
    def supports_fim(self):           # type: ignore[override]
        m = self.default_model
        return bool(m) and "insert" in self._caps.get(m, [])

    def ensure_running(self, job: ChatJob | None = None, wait: float = 20) -> None:
        if _local_up(self.base_url(), 0.5):
            return
        exe = self.exe()
        if not exe or str(self.config("autostart", "true")).lower() in ("0", "false"):
            raise AIError("Ollama is not running. Start it (ollama serve) or install it: " + self.install_hint)
        flags = NO_WINDOW | (0x00000008 if sys.platform == "win32" else 0)      # DETACHED_PROCESS
        subprocess.Popen([exe, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
        end = time.time() + wait
        while time.time() < end:
            if job is not None and job.stopping:
                return
            if _local_up(self.base_url(), 0.5):
                self.invalidate()
                return
            time.sleep(0.4)
        raise AIError("Ollama did not start in time (ollama serve).")

    def _pick_model(self, model: str) -> str:
        if model:
            return model
        ms = self._list_models()
        if not ms:
            raise AIError("Ollama has no model. Run in the Terminal: ollama pull qwen2.5-coder:7b")
        return ms[0]

    def _options(self, opts: dict) -> dict:
        o = {}
        if opts.get("temperature") is not None:
            o["temperature"] = opts["temperature"]
        if opts.get("max_tokens"):
            o["num_predict"] = int(opts["max_tokens"])
        ctx = self.config("num_ctx", "")
        if ctx:
            o["num_ctx"] = int(ctx)
        return o

    def _think(self, body: dict, model: str) -> None:
        if "thinking" in self.capabilities(model):
            body["think"] = str(self.config("think", "false")).lower() in ("1", "true", "yes")

    def _stream(self, job: ChatJob, path: str, body: dict, key: str) -> None:
        resp = _open_stream(job, self.name, self.base_url() + path, body)
        if resp is None:
            return
        with resp:
            for line in iter_lines(resp, job):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if obj.get("error"):
                    raise AIError(f"Ollama: {obj['error']}")
                piece = (obj.get("message") or {}).get("content") if key == "message" else obj.get("response")
                if piece:
                    job.emit_delta(piece)
                if obj.get("done"):
                    job.meta["usage"] = {k: obj.get(k) for k in ("prompt_eval_count", "eval_count",
                                                                   "total_duration") if k in obj}
                    break

    def _run_chat(self, job, system, messages, model, opts):
        self.ensure_running(job)
        if job.stopping:
            return ""
        model = self._pick_model(model)
        job.model = model
        msgs = ([{"role": "system", "content": system}] if system else []) + \
            [{"role": m.role, "content": m.content} for m in messages]
        body = {"model": model, "messages": msgs, "stream": True, "options": self._options(opts)}
        self._think(body, model)
        if self.config("keep_alive", ""):
            body["keep_alive"] = self.config("keep_alive", "")
        self._stream(job, "/api/chat", body, "message")
        return None

    def complete(self, prefix, suffix="", language="", model=None, max_tokens=160):
        model = model or str(self.config("complete_model", "") or "") or self.default_model
        job = ChatJob(self.id, model)
        job.meta["purpose"] = "complete"

        def run(j):
            self.ensure_running(j)
            m = self._pick_model(model)
            j.model = m
            opts = {"temperature": 0.2, "max_tokens": max_tokens}
            if "insert" in self.capabilities(m):              # real fill-in-the-middle
                body = {"model": m, "prompt": prefix[-6000:], "suffix": suffix[:2000], "stream": True,
                        "options": self._options(opts)}
                j.meta["fim"] = True
                self._stream(j, "/api/generate", body, "response")
                return None
            sys_text, user = completion_prompt(prefix, suffix, language)
            body = {"model": m, "messages": [{"role": "system", "content": sys_text},
                                             {"role": "user", "content": user}],
                    "stream": True, "options": self._options(opts)}
            self._think(body, m)
            self._stream(j, "/api/chat", body, "message")
            return None
        job.postprocess = lambda t: clean_completion(t, prefix, suffix)
        return job.start(run)


# ===================================================================== Anthropic
class Anthropic(Provider):
    id, name, kind = "anthropic", "Anthropic API", "api"
    needs_key = True
    key_url = "https://console.anthropic.com/settings/keys"
    install_hint = "Optional: needs an Anthropic API key (Claude subscribers can use claude-cli instead, free)."
    builtin_models = ("claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5")

    def base_url(self):
        return str(self.config("base_url", "") or "https://api.anthropic.com").rstrip("/")

    def api_key(self):
        return get_secret("anthropic") or os.environ.get("ANTHROPIC_API_KEY", "")

    def _headers(self):
        return {"x-api-key": self.api_key(), "anthropic-version": "2023-06-01"}

    def _detect(self):
        if not self.api_key():
            return False, f"No API key - add it in Tools > Options > AI (get one at {self.key_url})"
        return True, "API key set"

    def _list_models(self):
        if not self.api_key():
            return []
        j = _get_json(self.base_url() + "/v1/models?limit=100", self._headers())
        return [m["id"] for m in j.get("data", []) if m.get("id")]

    def _run_chat(self, job, system, messages, model, opts):
        ok, why = self.available()
        if not ok:
            raise AIError(f"{self.name}: {why}")
        msgs = []
        for m in messages:                      # the API wants alternating roles
            if msgs and msgs[-1]["role"] == m.role:
                msgs[-1]["content"] += "\n\n" + m.content
            else:
                msgs.append({"role": m.role, "content": m.content})
        body = {"model": model, "messages": msgs, "stream": True,
                "max_tokens": int(opts.get("max_tokens") or 8192)}
        if system:
            body["system"] = system
        if opts.get("temperature") is not None:
            body["temperature"] = opts["temperature"]
        resp = _open_stream(job, self.name, self.base_url() + "/v1/messages", body, self._headers())
        if resp is None:
            return ""
        with resp:
            for obj in _sse(resp, job):
                t = obj.get("type")
                if t == "content_block_delta":
                    d = obj.get("delta") or {}
                    if d.get("type") == "text_delta":
                        job.emit_delta(d.get("text", ""))
                elif t == "error":
                    e = obj.get("error") or {}
                    raise AIError(f"Anthropic: {e.get('message', e)}")
                elif t == "message_delta" and obj.get("usage"):
                    job.meta["usage"] = obj["usage"]
        return None


# ===================================================================== Gemini API
class GeminiAPI(Provider):
    id, name, kind = "gemini-api", "Google Gemini API", "api"
    needs_key = True
    key_url = "https://aistudio.google.com/apikey"
    install_hint = "Free key from Google AI Studio (or use gemini-cli with a Google login)."
    builtin_models = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite")

    def base_url(self):
        return str(self.config("base_url", "") or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    def api_key(self):
        return get_secret("gemini-api") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

    def _detect(self):
        if not self.api_key():
            return False, f"No API key - add it in Tools > Options > AI (free at {self.key_url})"
        return True, "API key set"

    def _list_models(self):
        if not self.api_key():
            return []
        j = _get_json(self.base_url() + "/models?pageSize=200", {"x-goog-api-key": self.api_key()})
        out = []
        for m in j.get("models", []):
            if "generateContent" in (m.get("supportedGenerationMethods") or []):
                out.append(m["name"].split("/", 1)[-1])
        return out

    def _run_chat(self, job, system, messages, model, opts):
        ok, why = self.available()
        if not ok:
            raise AIError(f"{self.name}: {why}")
        contents = [{"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
                    for m in messages]
        body: dict = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        gen = {}
        if opts.get("temperature") is not None:
            gen["temperature"] = opts["temperature"]
        if opts.get("max_tokens"):
            gen["maxOutputTokens"] = int(opts["max_tokens"])
        if gen:
            body["generationConfig"] = gen
        url = f"{self.base_url()}/models/{urllib.parse.quote(model)}:streamGenerateContent?alt=sse"
        resp = _open_stream(job, self.name, url, body, {"x-goog-api-key": self.api_key()},
                            f"Get a free key at {self.key_url}.")
        if resp is None:
            return ""
        with resp:
            for obj in _sse(resp, job):
                if obj.get("error"):
                    raise AIError(f"Gemini API: {obj['error'].get('message', obj['error'])}")
                for c in obj.get("candidates", []):
                    for part in (c.get("content") or {}).get("parts", []):
                        if part.get("text") and not part.get("thought"):
                            job.emit_delta(part["text"])
                if obj.get("usageMetadata"):
                    job.meta["usage"] = obj["usageMetadata"]
        return None


def create() -> list[Provider]:
    return [Ollama(), LMStudio(), CustomOpenAI(), OpenAI(), Anthropic(), GeminiAPI(), OpenRouter(), Groq(),
            DeepSeek(), Mistral(), XAI()]


__all__ = ["Ollama", "LMStudio", "CustomOpenAI", "OpenAICompatible", "OpenAI", "Anthropic", "GeminiAPI",
           "OpenRouter", "Groq", "DeepSeek", "Mistral", "XAI", "create", "Message"]
