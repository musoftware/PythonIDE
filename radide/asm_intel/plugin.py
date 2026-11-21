"""Hooking the assembly IntelliSense into language plugins and editors.

* ``AsmIntelMixin`` - put it first in the bases of an assembly language plugin
  (``class NasmPlugin(AsmIntelMixin, BridgeLanguagePlugin)``) and set ``asm_dialect = "nasm"`` (or masm / fasm /
  gas). It implements the plugin hooks of radide/languages/base.py: completions, calltip, hover, definition,
  references, document_symbols, plus ``monaco_language(path)`` (the Monarch grammar) and
  ``folding_ranges``.
* ``AsmPluginOverlay`` - wraps any other plugin for one editor of an assembly file (an ``.asm`` / ``.s`` file in a
  C, Rust or Python project, or a loose file opened without a project). radide/monaco_editor.py applies it via
  ``MonacoEditor.plugin_overlays`` (registered by radide/features/asm_ide.py); every other attribute comes from the
  wrapped plugin.
"""
from __future__ import annotations

from pathlib import Path

from . import engine
from .index import detect_dialect, gas_syntax, is_asm_path


class AsmIntelMixin:
    asm_intel = True
    asm_dialect: str = ""                 # nasm | masm | fasm | gas ('' = detect per file)

    # the editor of a plugin instance shared by many files does not know the path in document_symbols():
    # the overlay passes its own path, the mixin sniffs the text
    _asm_path = None

    def _asm_dialect_for(self, path, code: str | None = None) -> str:
        return detect_dialect(path, code, self)

    def completions(self, code, line, col, path=None, names=None):
        try:
            return engine.completions(code, line, col, path or self._asm_path, self)
        except Exception:  # noqa: BLE001 - IntelliSense must never break typing
            return []

    def calltip(self, code, line, col, path=None, names=None):
        try:
            return engine.calltip(code, line, col, path or self._asm_path, self)
        except Exception:  # noqa: BLE001
            return ""

    def hover(self, code, line, col, path=None, names=None):
        try:
            return engine.hover(code, line, col, path or self._asm_path, self)
        except Exception:  # noqa: BLE001
            return ""

    def definition(self, code, line, col, path=None, names=None):
        try:
            return engine.definition(code, line, col, path or self._asm_path, self)
        except Exception:  # noqa: BLE001
            return None

    def references(self, code, line, col, path=None, names=None):
        try:
            return engine.references(code, line, col, path or self._asm_path, self)
        except Exception:  # noqa: BLE001
            return None

    def document_symbols(self, code):
        try:
            return engine.document_symbols(code, self._asm_path, self)
        except Exception:  # noqa: BLE001
            return []

    def folding_ranges(self, code, path=None):
        try:
            return engine.folding_ranges(code, path or self._asm_path, self)
        except Exception:  # noqa: BLE001
            return []

    def monaco_language(self, path) -> dict | None:
        """The Monarch grammar / language configuration for an assembly file (None for other files)."""
        if not is_asm_path(path) and not (self.asm_dialect and Path(str(path)).suffix.lower() in ("", ".txt")):
            return None
        from .monarch import language_spec
        text = None
        try:
            p = Path(str(path))
            if p.is_file() and p.stat().st_size < 2_000_000:
                text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = None
        dia = detect_dialect(path, text, self)
        return language_spec(dia, dia == "gas" and gas_syntax(text or "") == "att")


class AsmPluginOverlay(AsmIntelMixin):
    """One editor's view of *base* with assembly IntelliSense (everything else delegates to *base*)."""

    def __init__(self, base, path):
        object.__setattr__(self, "_asm_base", base)
        object.__setattr__(self, "_asm_path", Path(str(path)))
        text = None
        try:
            if Path(str(path)).is_file():
                text = Path(str(path)).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = None
        dia = detect_dialect(path, text, base)
        object.__setattr__(self, "asm_dialect", dia)
        object.__setattr__(self, "line_comments", ["#"] if dia == "gas" else [";"])
        object.__setattr__(self, "block_comment", ("/*", "*/") if dia == "gas" else None)
        object.__setattr__(self, "string_quotes", ['"', "'"])
        object.__setattr__(self, "case_sensitive", dia != "masm")

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_asm_base"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_asm_base"), name, value)

    @property
    def base_plugin(self):
        return object.__getattribute__(self, "_asm_base")

    def __repr__(self) -> str:
        return f"<AsmPluginOverlay {self.asm_dialect} over {self.base_plugin!r}>"


def overlay_for(plugin, path):
    """MonacoEditor.plugin_overlays entry: an overlay for assembly files whose plugin is not assembly-aware."""
    if plugin is None or getattr(plugin, "asm_intel", False) or not path:
        return None
    p = Path(str(path))
    suffix = p.suffix.lower()
    if suffix == ".inc":
        # .inc is also PHP / Pascal: only when assembly sources sit next to it or its text looks like assembly
        try:
            near = any(f.suffix.lower() in (".asm", ".s", ".nasm", ".fasm") for f in p.parent.iterdir())
        except OSError:
            near = False
        if not near:
            from .index import sniff
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:8000] if p.is_file() else ""
            except OSError:
                text = ""
            if "<?php" in text or not sniff(text):
                return None
    elif not is_asm_path(p):
        return None
    return AsmPluginOverlay(plugin, p)
