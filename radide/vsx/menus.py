"""``contributes.menus`` of extensions: entries of a menu id (editor/title, editor/context, view/title,
view/item/context, explorer/context, webview/context ...) whose ``when`` holds, ordered like VS Code
(src/vs/platform/actions/common/menuService.ts MenuInfo.compareMenuItems: 'navigation' first, other groups
lexically, groups without a name last; then ``group@order``; then the title), with ``submenus``, command
icons (``$(codicon)``, an image path or {light, dark}) and ``enablement``.

    entries(svc, "view/title", ctx)            -> [Entry]
    fill_menu(svc, qmenu, "view/item/context", ctx, run, inline=False)
    toolbar_entries(svc, "editor/title", ctx)  -> the 'navigation' group (editor/title) / 'inline' (view/item)
No Qt import at module level."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import when as W


@dataclass
class Entry:
    command: str = ""
    submenu: str = ""
    title: str = ""
    group: str = ""
    order: float = 0
    icon: object = None             # "$(name)" | path str | {"light", "dark"} | None
    ext_path: str = ""
    enabled: bool = True
    alt: str = ""
    children: list = field(default_factory=list)


def _title(v) -> str:
    return v.get("value") or v.get("original") or "" if isinstance(v, dict) else str(v or "")


def _exts(svc):
    try:
        return list(svc.extensions)
    except Exception:  # noqa: BLE001
        return []


def command_info(svc) -> dict:
    """command id -> {title, category, icon, enablement, ext_path} of every contributed command."""
    out = {}
    for ext in _exts(svc):
        for c in ext.contributes_list("commands"):
            if isinstance(c, dict) and isinstance(c.get("command"), str):
                out[c["command"]] = {"title": _title(c.get("title")) or c["command"],
                                     "short": _title(c.get("shortTitle")),
                                     "category": _title(c.get("category")), "icon": c.get("icon"),
                                     "enablement": c.get("enablement"), "ext_path": str(ext.path)}
    return out


def _submenus(svc) -> dict:
    out = {}
    for ext in _exts(svc):
        for s in ext.contributes_list("submenus"):
            if isinstance(s, dict) and s.get("id"):
                out[s["id"]] = {"label": _title(s.get("label")) or s["id"], "icon": s.get("icon"),
                                "ext_path": str(ext.path)}
    return out


def _split_group(g: str) -> tuple[str, float]:
    g = str(g or "")
    i = g.rfind("@")
    if i > 0:
        try:
            return g[:i], float(g[i + 1:])
        except ValueError:
            return g[:i], 0
    return g, 0


def _sort_key(e: Entry):
    g = e.group
    return (2 if not g else 0 if g == "navigation" else 1, g.lower(), e.order, e.title.lower())


def entries(svc, menu_id: str, ctx: dict, _depth: int = 0) -> list[Entry]:
    cmds = command_info(svc)
    subs = _submenus(svc)
    out: list[Entry] = []
    seen = set()
    for ext in _exts(svc):
        for m in (ext.contributes.get("menus") or {}).get(menu_id, []) or []:
            if not isinstance(m, dict):
                continue
            try:
                if not W.evaluate(m.get("when"), ctx):
                    continue
            except Exception:  # noqa: BLE001
                continue
            g, order = _split_group(m.get("group", ""))
            if m.get("submenu"):
                sid = m["submenu"]
                info = subs.get(sid, {"label": sid, "icon": None, "ext_path": str(ext.path)})
                kids = entries(svc, sid, ctx, _depth + 1) if _depth < 4 else []
                if kids:
                    out.append(Entry(submenu=sid, title=info["label"], group=g, order=order, icon=info.get("icon"),
                                     ext_path=info.get("ext_path", ""), children=kids))
                continue
            cid = m.get("command")
            if not isinstance(cid, str) or cid not in cmds or (cid, g) in seen:
                continue
            seen.add((cid, g))
            info = cmds[cid]
            enabled = True
            if info.get("enablement"):
                try:
                    enabled = W.evaluate(info["enablement"], ctx)
                except Exception:  # noqa: BLE001
                    enabled = True
            out.append(Entry(command=cid, title=info["title"], group=g, order=order, icon=info.get("icon"),
                             ext_path=info.get("ext_path", ""), enabled=enabled, alt=str(m.get("alt") or "")))
    out.sort(key=_sort_key)
    return out


def toolbar_entries(svc, menu_id: str, ctx: dict) -> list[Entry]:
    """The entries VS Code shows as buttons: group 'navigation' (title menus) or 'inline' (item menus)."""
    want = "inline" if menu_id.endswith("/context") or "/item/" in menu_id else "navigation"
    return [e for e in entries(svc, menu_id, ctx) if e.group == want or e.group.startswith(want + "_")]


def qicon(e: Entry, dark: bool | None = None):
    """QIcon of an entry's icon (codicon / image / {light, dark}), or None."""
    from PyQt6.QtGui import QIcon
    ic = e.icon
    if not ic:
        return None
    if isinstance(ic, str) and ic.startswith("$("):
        from . import codicon
        return codicon.icon(codicon.strip(ic)[1] or "")
    if dark is None:
        try:
            from .. import theme as TH
            dark = TH.is_dark()
        except Exception:  # noqa: BLE001
            dark = True
    p = ic.get("dark" if dark else "light") or ic.get("light") or ic.get("dark") if isinstance(ic, dict) else ic
    if not isinstance(p, str):
        return None
    f = Path(e.ext_path) / p if e.ext_path else Path(p)
    return QIcon(str(f)) if f.is_file() else None


def label(e: Entry) -> str:
    from . import codicon
    return codicon.strip(e.title)[0] or e.title


def fill_menu(svc, menu, menu_id: str, ctx: dict, run, skip_inline: bool = False) -> int:
    """Add the entries to a QMenu (separators between groups). run(command_id) executes. Returns the count."""
    n = 0
    last = None
    for e in entries(svc, menu_id, ctx):
        if skip_inline and e.group == "inline":
            continue
        if last is not None and e.group != last:
            menu.addSeparator()
        last = e.group
        n += _add(menu, e, run)
    return n


def _add(menu, e: Entry, run) -> int:
    if e.submenu:
        sub = menu.addMenu(label(e))
        last = None
        for k in e.children:
            if last is not None and k.group != last:
                sub.addSeparator()
            last = k.group
            _add(sub, k, run)
        return 1
    ic = qicon(e)
    a = menu.addAction(ic, label(e)) if ic is not None else menu.addAction(label(e))
    a.setEnabled(e.enabled)
    a.triggered.connect(lambda _c=False, cid=e.command: run(cid))
    return 1


__all__ = ["Entry", "entries", "toolbar_entries", "fill_menu", "command_info", "qicon", "label"]
