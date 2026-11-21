"""``form.extra["animations"]`` (plan 1.1): list helpers, rename and validation. Pure Python."""
from __future__ import annotations

import re

from . import presets as P


def animations(form) -> list[dict]:
    """The form's animation list (created when missing / broken)."""
    lst = form.extra.get("animations")
    if not isinstance(lst, list):
        lst = []
        form.extra["animations"] = lst
    return lst


def motion_settings(form) -> dict:
    m = form.extra.get("motion")
    if not isinstance(m, dict):
        m = {"respectReducedMotion": True}
        form.extra["motion"] = m
    return m


def respect_reduced_motion(form) -> bool:
    m = form.extra.get("motion")
    return bool(m.get("respectReducedMotion", True)) if isinstance(m, dict) else True


def has_animations(form) -> bool:
    lst = form.extra.get("animations")
    return isinstance(lst, list) and any(isinstance(a, dict) and a.get("enabled", True) for a in lst)


def find(form, fx_id: str) -> dict | None:
    return next((a for a in form.extra.get("animations") or [] if isinstance(a, dict) and a.get("id") == fx_id),
                None)


def for_target(form, target: str) -> list[dict]:
    return [a for a in form.extra.get("animations") or [] if isinstance(a, dict)
            and str(a.get("target") or "") == (target or "")]


def new_id(form) -> str:
    taken = {str(a.get("id")) for a in form.extra.get("animations") or [] if isinstance(a, dict)}
    taken |= set(form.all_names()) if hasattr(form, "all_names") else set()
    i = 1
    while f"fx{i}" in taken:
        i += 1
    return f"fx{i}"


def add(form, target: str, preset: str, **kw) -> dict:
    """Append a new animation of *preset* on *target* ("" = the form) and return it."""
    if preset not in P.CATALOG:
        raise KeyError(f"unknown animation preset '{preset}'")
    fx_id = kw.pop("id", None) or new_id(form)
    anim = P.make(preset, target, fx_id, **kw)
    animations(form).append(anim)
    return anim


def remove(form, fx_id: str) -> bool:
    lst = animations(form)
    a = find(form, fx_id)
    if a is None:
        return False
    lst.remove(a)
    for other in lst:                       # chains that started after it now start on load
        trig = other.get("trigger") or {}
        if trig.get("on") == "after" and trig.get("after") == fx_id:
            trig["after"] = None
    return True


def move(form, fx_id: str, delta: int) -> None:
    lst = animations(form)
    a = find(form, fx_id)
    if a is None:
        return
    i = lst.index(a)
    j = max(0, min(len(lst) - 1, i + delta))
    lst.insert(j, lst.pop(i))


def rename_references(form, old: str, new: str) -> int:
    """A control was renamed: animation targets and trigger sources follow. Returns the count."""
    n = 0
    for a in form.extra.get("animations") or []:
        if not isinstance(a, dict):
            continue
        if a.get("target") == old:
            a["target"] = new
            n += 1
        trig = a.get("trigger")
        if isinstance(trig, dict) and trig.get("source") == old:
            trig["source"] = new
            n += 1
    return n


def remove_target(form, name: str) -> int:
    """A control was deleted: drop its animations (and clear triggers it was the source of)."""
    lst = animations(form)
    drop = [a for a in lst if isinstance(a, dict) and a.get("target") == name]
    for a in drop:
        remove(form, a.get("id"))
    for a in lst:
        trig = a.get("trigger")
        if isinstance(trig, dict) and trig.get("source") == name:
            trig["source"] = None
    return len(drop)


_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate(form) -> list[tuple[str, str, str]]:
    """Problems as (fx id, target, message): missing target / source, unknown preset, bad ids,
    ``after`` chains that loop, typewriter on a control without Text."""
    out: list[tuple[str, str, str]] = []
    names = {c.name: c for c in form.visual()} if hasattr(form, "visual") else {}
    lst = [a for a in form.extra.get("animations") or [] if isinstance(a, dict)]
    ids = [str(a.get("id") or "") for a in lst]
    seen: set[str] = set()
    for a in lst:
        fx, tgt = str(a.get("id") or ""), str(a.get("target") or "")
        if not _ID.match(fx):
            out.append((fx, tgt, f"Animation id '{fx}' is not a valid name"))
        elif fx in seen:
            out.append((fx, tgt, f"Animation id '{fx}' is used twice"))
        seen.add(fx)
        if a.get("preset") not in P.CATALOG:
            out.append((fx, tgt, f"Unknown animation preset '{a.get('preset')}'"))
        if tgt and tgt not in names:
            out.append((fx, tgt, f"Animation {fx}: control '{tgt}' does not exist"))
        trig = a.get("trigger") if isinstance(a.get("trigger"), dict) else {}
        on = trig.get("on", "load")
        if on not in P.TRIGGERS:
            out.append((fx, tgt, f"Animation {fx}: unknown trigger '{on}'"))
        src = trig.get("source")
        if on in ("click", "hover") and src and src not in names:
            out.append((fx, tgt, f"Animation {fx}: trigger control '{src}' does not exist"))
        if on == "after":
            after = trig.get("after")
            if not after:
                out.append((fx, tgt, f"Animation {fx}: 'After animation' has no animation to follow"))
            elif after not in ids:
                out.append((fx, tgt, f"Animation {fx}: animation '{after}' to follow does not exist"))
        if on == "timer":
            try:
                if int(trig.get("intervalMs") or 0) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                out.append((fx, tgt, f"Animation {fx}: timer interval must be > 0 ms"))
        if a.get("preset") == "typewriter":
            c = names.get(tgt)
            props = form.props if not tgt else (c.props if c is not None else {})
            if "Text" not in props:
                out.append((fx, tgt, f"Animation {fx}: Typewriter needs a control with Text"))
    # after-chains that loop
    nxt = {str(a.get("id")): (a.get("trigger") or {}).get("after") for a in lst
           if isinstance(a.get("trigger"), dict) and (a.get("trigger") or {}).get("on") == "after"}
    reported: set[str] = set()
    for start in nxt:
        path, cur = [], start
        while cur in nxt and cur not in path:
            path.append(cur)
            cur = nxt[cur]
        if cur in path and cur not in reported:
            loop = path[path.index(cur):]
            reported.update(loop)
            tgt = next((str(a.get("target") or "") for a in lst if a.get("id") == cur), "")
            out.append((cur, tgt, "Animations start each other in a loop: " + " -> ".join(loop + [cur])))
    return out
