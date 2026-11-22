"""Native builds: the published program is a small native .exe with NO Python inside.

Build > Publish uses a native builder when one exists for the startup form's language
(PublishConfig.prefer_native, on by default); when a builder cannot translate something it raises
NativeUnsupported with the reasons, they are logged, and the build falls back to the previous kind
(vbrun / bridge), so a project never stops building.

One module per language family in this package, each with:

    LANGS: tuple[str, ...]                      project language ids it builds (e.g. "c-bridge", "vb-basic")
    NAME: str                                   shown in the Output, e.g. "native Win32 (MinGW-w64)"
    def check(folder, project, cfg) -> list[str]   reasons it cannot build this project ([] = it can);
                                                   missing tools are NOT a reason (build() downloads them)
    def build(folder, project, cfg, work, log) -> radide.deploy.build.BuildResult
                                                   raise NativeUnsupported(reasons) to fall back

Priority: the smallest exe that still behaves like the project does in the IDE.
"""
from __future__ import annotations

import importlib

# module names in this package, tried in order (a missing module is simply skipped)
MODULES = ("vb6_freebasic", "win32_c", "dotnet_winforms", "java_native", "go_native", "rust_native",
           "script_embed", "node_sea", "webview")


class NativeUnsupported(Exception):
    def __init__(self, reasons):
        self.reasons = [reasons] if isinstance(reasons, str) else list(reasons)
        super().__init__("; ".join(self.reasons))


def _modules():
    for name in MODULES:
        try:
            yield importlib.import_module(f"{__name__}.{name}")
        except Exception:  # noqa: BLE001 - a missing or broken builder must never stop Publish
            continue


def builder_for(lang: str):
    """The native builder module for a project language id, or None."""
    for m in _modules():
        if lang in getattr(m, "LANGS", ()):
            return m
    return None


def native_languages() -> dict[str, str]:
    """language id -> builder NAME (for the Publish dialog)."""
    out = {}
    for m in _modules():
        for lang in getattr(m, "LANGS", ()):
            out.setdefault(lang, getattr(m, "NAME", m.__name__))
    return out


__all__ = ["MODULES", "NativeUnsupported", "builder_for", "native_languages"]
