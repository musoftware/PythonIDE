"""Error List lines for animations / layout sizes on the non-Python targets (plan MOTION_VARIANTS_FOLDABLES,
slice D): what Ring, Flutter, Kivy, React Native and WinForms show differently (preset fallbacks, no
foldable API) and the form formats that cannot keep them (Delphi / Lazarus / Qt .ui / NetBeans forms).
The Python targets are covered by the Animations panel (features/animations_panel.py)."""
from __future__ import annotations

from pathlib import Path

# foreign form formats that keep only their own file: animations / sizes are not saved there
FOREIGN_MARKS = {"pascal_dialect": "Delphi / Lazarus", "NativeEvents": "NetBeans", "qt_ui": "Qt Designer (.ui)"}


def form_issues(form, plugin_id: str) -> list[tuple[str, str]]:
    from .. import fxtargets as fx
    has_any = fx.has_motion(form) or bool((form.extra.get("variants") or {}).get("sizes"))
    if not has_any:
        return []
    for key, label in FOREIGN_MARKS.items():
        if key in form.extra or (key == "qt_ui" and str(form.extra.get("source", "")).lower().endswith(".ui")):
            return [("Warning", f"Animations / layout sizes are not saved in {label} forms (the IDE keeps them only "
                                f"while the form is open)")]
    if plugin_id in fx.NOT_APPLICABLE:
        return [("Info", fx.NOT_APPLICABLE[plugin_id])]
    target = fx.PLUGIN_TARGETS.get(plugin_id)
    if target is None:
        return []
    return fx.issues(form, target)


def diags(win) -> list:
    """Error List provider (win.diag_providers)."""
    proj = getattr(win, "project", None)
    if proj is None:
        return []
    from .. import fxtargets as fx
    from ..tools import Diag
    out = []
    docs = getattr(win, "docs", {}) or {}
    for name in list(getattr(proj, "forms", []) or []):
        try:
            plugin = win.plugin_for_form(name)
            pid = getattr(plugin, "id", "")
            if pid not in fx.PLUGIN_TARGETS and pid not in fx.NOT_APPLICABLE:
                continue
            if name in docs:
                form = docs[name].form
            else:
                path = Path(proj.form_path(name))
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if '"animations"' not in text and '"variants"' not in text:
                    continue
                from ..model import Form
                form = Form.load(path)
            for sev, msg in form_issues(form, pid):
                out.append(Diag("Warning" if sev == "Info" else sev, msg, f"{name}.form", 1))
        except Exception:  # noqa: BLE001 - never break the Error List
            continue
    return out


def install(win) -> None:
    providers = win.__dict__.setdefault("diag_providers", [])
    if diags not in providers:
        providers.append(diags)
