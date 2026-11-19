"""AI everywhere (docs/CONTRACTS.md 9.1).

    from radide import ai
    p, model = ai.default("chat")
    job = p.chat([ai.Message("user", "Hello")], model=model)
    job.delta.connect(...); job.finished.connect(...); job.failed.connect(...)

Providers: CLI agents signed in with the user's own account (claude-cli, gemini-cli, codex-cli,
copilot-cli, qwen-cli, opencode-cli, cursor-cli), local models (ollama, lmstudio, openai-compatible)
and optional API keys (openai, anthropic, gemini-api, openrouter, groq, deepseek, mistral, xai).
Web chats (kind "web") are registered by radide/features/ai_web.py through ai.register()."""
from __future__ import annotations

from .providers import (KINDS, PURPOSES, AIError, ChatJob, Message, Provider, chat, clean_completion,
                        completion_prompt, default, extract_code_blocks, flatten, get, get_secret, hub,
                        normalize, providers, refresh_all, register, run_sync, secret_backend, set_default,
                        set_secret, settings)

__all__ = ["KINDS", "PURPOSES", "AIError", "ChatJob", "Message", "Provider", "chat", "clean_completion",
           "completion_prompt", "default", "extract_code_blocks", "flatten", "get", "get_secret", "hub",
           "normalize", "providers", "refresh_all", "register", "run_sync", "secret_backend", "set_default",
           "set_secret", "settings"]
