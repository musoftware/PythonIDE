"""Redesign Form with AI: merge the AI's form into the current one instead of replacing it.

A model (especially a small local one) answers with the WHOLE form again and easily drops properties,
renames controls or turns a ListBox into a ListView while it was only asked to arrange them. So:

* controls are matched by Name (case-insensitive); a property the AI leaves out keeps its value
* every difference gets a category, the dialog shows them with check boxes:
      layout   Left / Top / Width / Height / Parent / Dock / Anchor / TabIndex (+ the form's Width / Height)
      text     Text (captions)
      other    any other property of a control that stays
      added    a control the form does not have
      removed  a control the AI left out
      retyped  a control whose type the AI changed
* removed and retyped are never applied unless ticked: a control missing from the answer stays as it is
* layout_request() spots "arrange / align / sort / رتب / نظم ..." requests: then only layout is ticked
"""
from __future__ import annotations

import copy
import re

LAYOUT_PROPS = ("Left", "Top", "Width", "Height", "Parent", "Dock", "Anchor", "TabIndex")
FORM_LAYOUT_PROPS = ("Width", "Height")
TEXT_PROPS = ("Text",)
CATEGORIES = ("layout", "text", "other", "added", "removed", "retyped")
CATEGORY_TITLES = {
    "layout": "Positions and sizes",
    "text": "Texts / captions",
    "other": "Other properties",
    "added": "New controls",
    "removed": "Remove controls the AI left out",
    "retyped": "Change control types",
}
SAFE_DEFAULT = {"layout", "text", "other", "added"}

_LAYOUT_WORDS = re.compile(
    r"\b(arrange|align|sort|order|tidy|organi[sz]e|layout|lay\s*out|line\s*up|position|spacing|space\s*out|"
    r"distribute|center|centre|grid|neat)\b|"
    r"(رتب|ترتيب|نظم|تنظيم|نسق|تنسيق|اصطف|محاذ|وسّط|وسط|مسافات|اماكن|أماكن)", re.I)


def layout_request(description: str) -> bool:
    """Is the request only about where the controls are (arrange / align / sort ...)?"""
    return bool(_LAYOUT_WORDS.search(description or ""))


def _eq(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _cat(prop: str) -> str:
    if prop in LAYOUT_PROPS:
        return "layout"
    if prop in TEXT_PROPS:
        return "text"
    return "other"


def plan(current, proposed) -> dict:
    """Differences between the current Form and the AI's Form:
    {"form": [(category, prop, old, new)],
     "changes": [(category, name, prop, old, new)],
     "added": [control], "removed": [name], "retyped": [(name, old_type, new_type)]}"""
    out = {"form": [], "changes": [], "added": [], "removed": [], "retyped": []}
    for k, v in (proposed.props or {}).items():
        if k == "Name" or k not in current.props or _eq(current.props.get(k), v):
            continue
        cat = "layout" if k in FORM_LAYOUT_PROPS else ("text" if k in TEXT_PROPS else "other")
        out["form"].append((cat, k, current.props.get(k), v))
    cur = {c.name.lower(): c for c in current.controls}
    seen = set()
    for c in proposed.controls:
        key = c.name.lower()
        old = cur.get(key)
        if old is None:
            out["added"].append(c)
            continue
        seen.add(key)
        if old.type != c.type:
            out["retyped"].append((old.name, old.type, c.type))
        for k, v in c.props.items():
            if k == "Name" or (k in old.props and _eq(old.props.get(k), v)):
                continue
            if k not in old.props and old.type != c.type:
                continue                    # a property of the new type: part of "retyped"
            out["changes"].append((_cat(k), old.name, k, old.props.get(k), v))
    out["removed"] = [c.name for c in current.controls if c.name.lower() not in seen]
    return out


def counts(p: dict) -> dict:
    n = {c: 0 for c in CATEGORIES}
    for cat, *_r in p["form"]:
        n[cat] += 1
    for cat, *_r in p["changes"]:
        n[cat] += 1
    n["added"] = len(p["added"])
    n["removed"] = len(p["removed"])
    n["retyped"] = len(p["retyped"])
    return n


def merge(current, proposed, accept=SAFE_DEFAULT):
    """A NEW Form: the current one with the accepted categories of the AI's changes applied."""
    from ..model import Form
    accept = set(accept)
    p = plan(current, proposed)
    form = Form.from_dict(copy.deepcopy(current.to_dict()))
    for cat, k, _old, new in p["form"]:
        if cat in accept:
            form.props[k] = new
    by = {c.name.lower(): c for c in form.controls}
    prop_by = {c.name.lower(): c for c in proposed.controls}
    if "retyped" in accept:
        for name, _ot, _nt in p["retyped"]:
            i = next(i for i, c in enumerate(form.controls) if c.name.lower() == name.lower())
            new = copy.deepcopy(prop_by[name.lower()])
            new.props["Name"] = form.controls[i].name
            form.controls[i] = new
            by[name.lower()] = new
    retyped = {n.lower() for n, *_r in p["retyped"]}
    for cat, name, k, _old, new in p["changes"]:
        if cat not in accept:
            continue
        if name.lower() in retyped and "retyped" in accept:
            continue                        # already the AI's control
        c = by.get(name.lower())
        if c is not None:
            c.props[k] = copy.deepcopy(new)
    if "removed" in accept:
        gone = {n.lower() for n in p["removed"]}
        form.controls = [c for c in form.controls if c.name.lower() not in gone]
    if "added" in accept:
        names = {c.name.lower() for c in form.controls}
        for c in p["added"]:
            if c.name.lower() not in names:
                form.controls.append(copy.deepcopy(c))
                names.add(c.name.lower())
    # a Parent that no longer exists -> the form
    names = {c.name for c in form.controls}
    for c in form.controls:
        if c.props.get("Parent") and c.props["Parent"] not in names:
            c.props["Parent"] = ""
    return form


def describe(p: dict, limit: int = 60) -> list[tuple[str, str]]:
    """(category, line) for the dialog's list."""
    rows = []
    for cat, k, old, new in p["form"]:
        rows.append((cat, f"Form.{k}: {old!r} -> {new!r}"))
    for cat, name, k, old, new in p["changes"]:
        rows.append((cat, f"{name}.{k}: {old!r} -> {new!r}"))
    for c in p["added"]:
        rows.append(("added", f"+ {c.name} ({c.type})"))
    for n in p["removed"]:
        rows.append(("removed", f"- {n} (left out by the AI)"))
    for n, ot, nt in p["retyped"]:
        rows.append(("retyped", f"{n}: {ot} -> {nt}"))
    return rows[:limit] + ([("other", f"... {len(rows) - limit} more")] if len(rows) > limit else [])


__all__ = ["CATEGORIES", "CATEGORY_TITLES", "LAYOUT_PROPS", "SAFE_DEFAULT", "counts", "describe",
           "layout_request", "merge", "plan"]
