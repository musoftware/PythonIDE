"""Tell the open retro editors that a file changed on disk (shared by the retro slices, docs/RETRO.md).

Any tool that writes into a ROM / binary calls ``file_changed(win, path, source=self)``.  Every open tab
widget (and dock widget) that has a ``retro_path`` attribute equal to *path* (or lists *path* in a
``retro_watch`` attribute, e.g. the tile set of a map) and a ``reload_from_disk()`` method is reloaded,
except *source*.  Code that is not a tab can subscribe with ``subscribe(win, callback)``;
the callback gets ``(path, source)``.
"""
from __future__ import annotations

from pathlib import Path


def _same(a, b) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, TypeError, ValueError):
        return False


def subscribe(win, callback) -> None:
    subs = getattr(win, "retro_file_listeners", None)
    if subs is None:
        subs = []
        win.retro_file_listeners = subs
    if callback not in subs:
        subs.append(callback)


def unsubscribe(win, callback) -> None:
    subs = getattr(win, "retro_file_listeners", None) or []
    if callback in subs:
        subs.remove(callback)


def open_widgets(win) -> list:
    out = []
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        out += [tabs.widget(i) for i in range(tabs.count())]
    try:
        from PyQt6.QtWidgets import QDockWidget
        out += [d.widget() for d in win.findChildren(QDockWidget) if d.widget() is not None]
    except Exception:  # noqa: BLE001
        pass
    return out


def file_changed(win, path, source=None) -> int:
    """Reload every other editor of *path*; returns how many were refreshed."""
    if win is None:
        return 0
    n = 0
    for w in open_widgets(win):
        if w is None or w is source:
            continue
        paths = [getattr(w, "retro_path", None)] + list(getattr(w, "retro_watch", None) or [])
        fn = getattr(w, "reload_from_disk", None)
        if callable(fn) and any(rp is not None and _same(rp, path) for rp in paths):
            try:
                fn()
                n += 1
            except Exception as e:  # noqa: BLE001 - one editor must not stop the others
                try:
                    win.log(f"[retro] reloading {path} failed: {e}")
                except Exception:  # noqa: BLE001
                    pass
    for cb in list(getattr(win, "retro_file_listeners", None) or []):
        try:
            cb(Path(path), source)
            n += 1
        except Exception as e:  # noqa: BLE001
            try:
                win.log(f"[retro] listener failed: {e}")
            except Exception:  # noqa: BLE001
                pass
    return n
