"""Official CLI agents that sign in with the user's own account or subscription - no API key:
Claude Code (claude), Gemini CLI (gemini, free with a Google login), OpenAI Codex CLI (codex, ChatGPT
login), GitHub Copilot CLI (copilot), Qwen Code (qwen), opencode (free models built in) and
Cursor CLI (cursor-agent).  Each runs in its documented non-interactive mode; the prompt goes on
stdin where the CLI supports it.  npm shims (.cmd / .ps1) are resolved to `node script.js` so no
cmd.exe quoting is involved."""
from __future__ import annotations

import codecs
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .providers import AIError, ChatJob, Provider, flatten

WIN = sys.platform == "win32"
NO_WINDOW = 0x08000000 if WIN else 0
HOME = Path.home()

_which_cache: dict[str, list[str] | None] = {}


def _npm_shim_target(cmd_path: str) -> list[str] | None:
    """`node <script>` behind an npm .cmd shim (so the prompt never passes through cmd.exe)."""
    try:
        text = Path(cmd_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'"%(?:~)?dp0%\\?([^"]+?)"\s+%\*', text)
    if not m:
        return None
    script = Path(cmd_path).parent / m.group(1).lstrip("\\")
    if not script.is_file():
        return None
    node = Path(cmd_path).parent / "node.exe"
    node_s = str(node) if node.is_file() else (shutil.which("node") or "")
    if not node_s:
        return None
    try:                       # a native binary launched through a shim ("#!" absent) runs directly
        head = script.read_bytes()[:2]
        if head == b"MZ":
            return [str(script)]
    except OSError:
        pass
    return [node_s, str(script)]


def find_command(names, override: str = "") -> list[str] | None:
    """argv prefix to start a CLI, or None.  Cached (detection must be fast)."""
    key = "|".join(names) + "|" + override
    if key in _which_cache:
        return _which_cache[key]
    found: list[str] | None = None
    cands = [override] if override else []
    for n in names:
        cands.append(n)
    for c in cands:
        if not c:
            continue
        p = c if os.path.isfile(c) else shutil.which(c)
        if not p and WIN:
            for ext in (".cmd", ".exe", ".ps1"):
                p = shutil.which(c + ext)
                if p:
                    break
        if not p:
            continue
        low = p.lower()
        if WIN and low.endswith(".ps1"):
            cmd = p[:-4] + ".cmd"
            if os.path.isfile(cmd):
                p, low = cmd, cmd.lower()
            else:
                found = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", p]
                break
        if WIN and low.endswith((".cmd", ".bat")):
            found = _npm_shim_target(p) or [p]
        elif WIN and not os.path.splitext(low)[1]:
            # extension-less npm (sh) shim next to a .cmd
            cmd = p + ".cmd"
            found = (_npm_shim_target(cmd) or [cmd]) if os.path.isfile(cmd) else [p]
        else:
            found = [p]
        break
    _which_cache[key] = found
    return found


def clear_cache() -> None:
    _which_cache.clear()


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


_AUTH_WORDS = ("login", "log in", "sign in", "signin", "not authenticated", "unauthenticated", "auth",
               "credential", "api key", "apikey", "401", "403", "oauth", "token expired", "/login")
_QUOTA_WORDS = ("quota", "rate limit", "ratelimit", "429", "usage limit", "exhausted", "too many requests")


class CliProvider(Provider):
    kind = "cli"
    exe_names: tuple = ()
    output = "text"                 # "text" | "jsonl"
    prompt_on_stdin = True
    login_files: tuple = ()         # any existing -> signed in
    login_env: tuple = ()
    builtin_models = ("default",)
    fallback_default = "default"
    install_cmd = ""
    login_cmd = ""                  # command to run in a console window to sign in

    def command(self) -> list[str] | None:
        return find_command(self.exe_names, str(self.config("path", "") or ""))

    def invalidate(self):
        super().invalidate()
        self._auth_failed = ""
        clear_cache()

    def signed_in(self) -> bool | None:
        """True / False when it can be told from files or env vars, None = unknown."""
        if any(os.environ.get(e) for e in self.login_env):
            return True
        if not self.login_files:
            return None
        return any((HOME / f).exists() for f in self.login_files)

    def _detect(self):
        cmd = self.command()
        if not cmd:
            how = f"npm install -g {self.npm_package}" if self.npm_package else self.install_cmd
            return False, f"Not installed. Install: {how}" if how else "Not installed"
        if getattr(self, "_auth_failed", ""):
            return False, f"Sign-in needed (the last request was refused) - {self.login_hint}"
        s = self.signed_in()
        if s is False:
            return False, f"Installed but not signed in - {self.login_hint}"
        return True, "Installed" + (", signed in" if s else (f" ({self.login_hint})" if self.login_hint else ""))

    # ------------------------------------------------------------ to override
    def build(self, prompt: str, model: str, system: str, opts: dict) -> tuple[list[str], str | None]:
        """-> (extra args after the command, stdin text or None)"""
        raise NotImplementedError

    def parse(self, obj: dict, job: ChatJob, state: dict) -> None:
        """Handle one JSON event (jsonl output): emit deltas, set state['final'] / state['error']."""

    def system_inline(self) -> bool:
        return True

    # ------------------------------------------------------------ run
    def _run_chat(self, job, system, messages, model, opts):
        cmd = self.command()
        if not cmd:
            ok, why = self.available()
            raise AIError(f"{self.name}: {why}")
        model = "" if model in ("", "default", None) else model
        prompt = flatten(messages, system, self.system_inline())
        args, stdin_text = self.build(prompt, model, system, opts)
        argv = cmd + args
        cwd = opts.get("cwd") or self._neutral_dir()
        env = dict(os.environ, NO_COLOR="1", FORCE_COLOR="0", TERM="dumb", PYTHONIOENCODING="utf-8")
        env.update(self.extra_env())
        job.meta["argv"] = [a if len(a) < 200 else a[:60] + "..." for a in argv]
        job.meta["cwd"] = cwd
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=NO_WINDOW)
        except OSError as e:
            raise AIError(f"{self.name}: cannot start {argv[0]}: {e}") from None
        job.on_abort(lambda: kill_tree(proc))
        err_buf: list[bytes] = []

        def read_err():
            for chunk in iter(lambda: proc.stderr.read1(4096) if hasattr(proc.stderr, "read1")
                              else proc.stderr.read(4096), b""):
                err_buf.append(chunk)
                if sum(map(len, err_buf)) > 65536:
                    del err_buf[0]
        threading.Thread(target=read_err, daemon=True).start()
        try:
            if stdin_text is not None:
                proc.stdin.write(stdin_text.encode("utf-8"))
            proc.stdin.close()
        except OSError:
            pass
        state: dict = {"final": None, "error": None, "text": []}
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
        timeout = float(opts.get("timeout") or self.config("timeout", 600) or 600)
        timer = threading.Timer(timeout, lambda: (state.__setitem__("timeout", True), kill_tree(proc)))
        timer.daemon = True
        timer.start()
        try:
            if self.output == "jsonl":
                buf = ""
                for raw in iter(proc.stdout.readline, b""):
                    if job.stopping:
                        break
                    buf += dec.decode(raw)
                    if not buf.endswith("\n"):
                        continue
                    line, buf = buf.strip(), ""
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        state.setdefault("noise", []).append(line)
                        continue
                    if isinstance(obj, dict):
                        job.emit_event(obj)
                        self.parse(obj, job, state)
            else:
                read = proc.stdout.read1 if hasattr(proc.stdout, "read1") else proc.stdout.read
                for raw in iter(lambda: read(4096), b""):
                    if job.stopping:
                        break
                    t = dec.decode(raw).replace("\r\n", "\n")
                    if t:
                        state["text"].append(t)
                        job.emit_delta(t)
            code = proc.wait()
        finally:
            timer.cancel()
        if job.stopping:
            return ""
        stderr = b"".join(err_buf).decode("utf-8", errors="replace")
        if state.get("timeout"):
            raise AIError(f"{self.name}: no answer after {timeout:g} s (stopped).")
        if state["error"]:
            raise AIError(self._explain(str(state["error"]), stderr))
        if code != 0 and not (state["final"] or "".join(state["text"]).strip() or job.text):
            noise = "\n".join(state.get("noise", [])[-5:])
            raise AIError(self._explain(f"exit code {code}", stderr + "\n" + noise))
        if state["final"] is not None:
            return state["final"]
        return None

    def extra_env(self) -> dict:
        return {}

    def _neutral_dir(self) -> str:
        d = Path(tempfile.gettempdir()) / "radide-ai"
        d.mkdir(exist_ok=True)
        return str(d)

    def _explain(self, what: str, stderr: str) -> str:
        noise = ("DeprecationWarning", "--trace-deprecation", "True color", "Ripgrep is not available",
                 "exitCode:", "Loaded cached credentials", "Warning: Basic terminal", "Warning: 256-color")
        lines = []
        for ln in re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", stderr or "").splitlines():
            s = ln.strip()
            if not s or s in ("}", "{") or s.startswith("at ") or any(n in s for n in noise):
                continue
            lines.append(s)
        tail = "\n".join(dict.fromkeys(lines[-6:])).strip()
        msg = f"{self.name} failed: {what}"
        if tail and tail not in what:
            msg += f"\n{tail[-1200:]}"
        low = (what + " " + tail).lower()
        if "or newer is required" in low or "please update" in low or "upgrade" in low:
            how = f"npm install -g {self.npm_package}@latest" if self.npm_package else "update it"
            msg += f"\n-> This version of the CLI is too old. Update it: {how}  (Tools > Options > AI > Install / update)"
        elif any(w in low for w in _QUOTA_WORDS):
            msg += "\n-> The account's quota / rate limit was reached. Wait, or choose another provider."
        elif any(w in low for w in _AUTH_WORDS) and self.login_hint:
            self._auth_failed = msg
            self._avail_cache = None
            msg += f"\n-> You need to sign in (again): {self.login_hint}. Then press Test in Tools > Options > AI."
        return msg


# ===================================================================== concrete CLIs
class ClaudeCli(CliProvider):
    id, name = "claude-cli", "Claude Code (claude)"
    description = "Claude Code with your Claude Pro/Max subscription (no API key)."
    exe_names = ("claude",)
    npm_package = "@anthropic-ai/claude-code"
    login_cmd = "claude"
    login_hint = "run `claude` once in the Terminal and sign in with /login"
    login_files = (".claude/.credentials.json",)
    login_env = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    output = "jsonl"
    builtin_models = ("default", "sonnet", "opus", "haiku")

    def signed_in(self):
        s = super().signed_in()
        if s:
            return True
        try:                 # macOS/Linux keep the token in the keychain; ~/.claude.json has the account
            return '"oauthAccount"' in (HOME / ".claude.json").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

    def system_inline(self):
        return False

    def build(self, prompt, model, system, opts):
        args = ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--no-session-persistence"]
        if model:
            args += ["--model", model]
        if opts.get("agent_args"):
            args += list(opts["agent_args"])
        else:
            args += ["--tools", ""]            # plain chat: no tools, no permission prompts
            if system:
                args += ["--append-system-prompt", system]
        return args, prompt

    def parse(self, obj, job, state):
        t = obj.get("type")
        if t == "stream_event":
            ev = obj.get("event") or {}
            if ev.get("type") == "content_block_delta":
                d = ev.get("delta") or {}
                if d.get("type") == "text_delta":
                    state["streamed"] = True
                    job.emit_delta(d.get("text", ""))
        elif t == "assistant" and not state.get("streamed"):
            for c in (obj.get("message") or {}).get("content", []):
                if c.get("type") == "text":
                    job.emit_delta(c.get("text", ""))
        elif t == "system" and obj.get("subtype") == "init":
            job.meta["session_id"] = obj.get("session_id")
            job.meta["cli_model"] = obj.get("model")
        elif t == "result":
            job.meta["usage"] = obj.get("usage")
            job.meta["cost_usd"] = obj.get("total_cost_usd")
            if obj.get("is_error"):
                state["error"] = obj.get("result") or obj.get("subtype") or "error"
            elif isinstance(obj.get("result"), str):
                state["final"] = obj["result"]


class GeminiCli(CliProvider):
    id, name = "gemini-cli", "Gemini CLI (gemini)"
    description = "Google Gemini CLI - free tier with a personal Google login."
    exe_names = ("gemini",)
    npm_package = "@google/gemini-cli"
    login_cmd = "gemini"
    login_hint = "run `gemini` once in the Terminal and choose 'Login with Google'"
    login_files = (".gemini/oauth_creds.json",)
    login_env = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI")
    output = "jsonl"
    builtin_models = ("default", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite")

    def build(self, prompt, model, system, opts):
        args = ["-o", "stream-json"]
        if model:
            args += ["-m", model]
        args += list(opts.get("agent_args") or ["--approval-mode", "plan"])
        args += ["--skip-trust", "-p", " "]        # the prompt itself comes on stdin
        return args, prompt

    def parse(self, obj, job, state):
        t = obj.get("type")
        if t == "message" and obj.get("role") == "assistant":
            c = obj.get("content")
            if isinstance(c, str):
                job.emit_delta(c)
        elif t == "init":
            job.meta["session_id"] = obj.get("session_id")
            job.meta["cli_model"] = obj.get("model")
        elif t == "error":
            state["error"] = obj.get("message") or json.dumps(obj)[:300]
        elif t == "result":
            job.meta["usage"] = obj.get("stats")
            if obj.get("status") not in (None, "success"):
                e = obj.get("error") or {}
                state["error"] = e.get("message") if isinstance(e, dict) else str(e or obj.get("status"))


class CodexCli(CliProvider):
    id, name = "codex-cli", "OpenAI Codex CLI (codex)"
    description = "OpenAI Codex CLI with your ChatGPT plan (Sign in with ChatGPT)."
    exe_names = ("codex",)
    npm_package = "@openai/codex"
    login_cmd = "codex login"
    login_hint = "run `codex login` in the Terminal (Sign in with ChatGPT)"
    login_files = (".codex/auth.json",)
    login_env = ("OPENAI_API_KEY", "CODEX_API_KEY")
    output = "jsonl"
    builtin_models = ("default", "gpt-5-codex", "gpt-5", "o4-mini")

    def build(self, prompt, model, system, opts):
        args = ["exec", "--json", "--skip-git-repo-check", "--color", "never"]
        if model:
            args += ["-m", model]
        args += list(opts.get("agent_args") or ["--sandbox", "read-only"])
        args.append("-")                              # read the prompt from stdin
        return args, prompt

    def parse(self, obj, job, state):
        t = obj.get("type", "")
        item = obj.get("item") or {}
        if t in ("item.completed", "item.updated") and item.get("type") in ("agent_message", "assistant_message"):
            text = item.get("text", "")
            seen = state.setdefault("seen", {})
            prev = seen.get(item.get("id"), "")
            if text.startswith(prev):
                job.emit_delta(text[len(prev):])
            seen[item.get("id")] = text
        elif t == "turn.failed":
            state["error"] = (obj.get("error") or {}).get("message", "turn failed")
        elif t == "error":
            state["error"] = obj.get("message") or "error"
        elif t == "turn.completed":
            job.meta["usage"] = obj.get("usage")
        msg = obj.get("msg") or {}                      # older event format
        if msg.get("type") == "agent_message_delta":
            job.emit_delta(msg.get("delta", ""))
        elif msg.get("type") == "error":
            state["error"] = msg.get("message", "error")


class CopilotCli(CliProvider):
    id, name = "copilot-cli", "GitHub Copilot CLI (copilot)"
    description = "GitHub Copilot CLI with your Copilot plan (Copilot Free works)."
    exe_names = ("copilot",)
    npm_package = "@github/copilot"
    login_cmd = "copilot"
    login_hint = "run `copilot` in the Terminal and type /login"
    login_env = ("GH_TOKEN", "GITHUB_TOKEN", "COPILOT_GITHUB_TOKEN")
    prompt_on_stdin = False
    builtin_models = ("default", "claude-sonnet-4.5", "gpt-5")

    def build(self, prompt, model, system, opts):
        if len(prompt) > 30000:
            prompt = prompt[-30000:]
        args = ["-p", prompt, "--no-color"]
        if model:
            args += ["--model", model]
        args += list(opts.get("agent_args") or [])
        return args, None


class QwenCli(CliProvider):
    id, name = "qwen-cli", "Qwen Code (qwen)"
    description = "Qwen Code - free daily requests with a qwen.ai login."
    exe_names = ("qwen",)
    npm_package = "@qwen-code/qwen-code"
    login_cmd = "qwen"
    login_hint = "run `qwen` once in the Terminal and sign in (Qwen OAuth)"
    login_files = (".qwen/oauth_creds.json",)
    login_env = ("DASHSCOPE_API_KEY",)
    builtin_models = ("default", "qwen3-coder-plus")

    def build(self, prompt, model, system, opts):
        args = []
        if model:
            args += ["-m", model]
        args += list(opts.get("agent_args") or [])
        args += ["-p", " "]
        return args, prompt


class OpencodeCli(CliProvider):
    id, name = "opencode-cli", "opencode"
    description = "opencode - includes free models (opencode/*-free), or your own providers."
    exe_names = ("opencode",)
    npm_package = "opencode-ai"
    login_cmd = "opencode auth login"
    login_hint = "free models need no login; for others run `opencode auth login`"
    output = "jsonl"
    builtin_models = ("default", "opencode/big-pickle", "opencode/deepseek-v4-flash-free")

    def _list_models(self):
        cmd = self.command()
        if not cmd:
            return []
        r = subprocess.run(cmd + ["models"], capture_output=True, timeout=40, creationflags=NO_WINDOW,
                           cwd=self._neutral_dir())
        ms = [ln.strip() for ln in r.stdout.decode("utf-8", errors="replace").splitlines()
              if "/" in ln and " " not in ln.strip()]
        return ["default"] + ms if ms else []

    def build(self, prompt, model, system, opts):
        args = ["run", "--format", "json"]
        if model:
            args += ["-m", model]
        args += list(opts.get("agent_args") or [])
        return args, prompt

    def parse(self, obj, job, state):
        t = obj.get("type")
        part = obj.get("part") or {}
        if t == "text" or part.get("type") == "text":
            pid = part.get("id") or obj.get("id") or ""
            text = part.get("text", "")
            seen = state.setdefault("seen", {})
            prev = seen.get(pid, "")
            if text.startswith(prev):
                job.emit_delta(text[len(prev):])
            else:
                job.emit_delta(text)
            seen[pid] = text
        elif t == "error":
            e = obj.get("error") or {}
            if isinstance(e, dict):
                e = (e.get("data") or {}).get("message") or e.get("message") or e.get("name") or json.dumps(e)[:300]
            state["error"] = str(e)
        elif t == "step_finish":
            job.meta["usage"] = part.get("tokens")


class CursorCli(CliProvider):
    id, name = "cursor-cli", "Cursor CLI (cursor-agent)"
    description = "Cursor's agent CLI with your Cursor account."
    exe_names = ("cursor-agent", "agent")
    install_cmd = "see https://cursor.com/cli (Windows: inside WSL)"
    login_cmd = "cursor-agent login"
    login_hint = "run `cursor-agent login` in the Terminal"
    login_env = ("CURSOR_API_KEY",)
    output = "jsonl"
    prompt_on_stdin = False

    def build(self, prompt, model, system, opts):
        args = ["-p", "--output-format", "stream-json", "--stream-partial-output"]
        if model:
            args += ["--model", model]
        args += list(opts.get("agent_args") or [])
        args.append(prompt[-30000:])
        return args, None

    def parse(self, obj, job, state):
        ClaudeCli.parse(self, obj, job, state)        # same event shapes (assistant / result)


def create() -> list[Provider]:
    return [ClaudeCli(), GeminiCli(), CodexCli(), CopilotCli(), QwenCli(), OpencodeCli(), CursorCli()]


__all__ = ["CliProvider", "ClaudeCli", "GeminiCli", "CodexCli", "CopilotCli", "QwenCli", "OpencodeCli",
           "CursorCli", "find_command", "kill_tree", "create"]
