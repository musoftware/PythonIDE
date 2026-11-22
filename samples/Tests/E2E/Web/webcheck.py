# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""HTTP checks of the RAD Store, shared by the frozen-exe web journey (journey_web_frozen.py).

Each function takes a stack module (stacks/<name>.py) and an e2e_lib.Browser, raises AssertionError with a
readable detail on a failure and returns a short note."""
from __future__ import annotations

import re


def _ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def features(S) -> dict:
    return getattr(S, "FEATURES", {"db": True, "auth": True, "crud": True, "api": True, "debug": True})


def pages(S, B) -> str:
    R = S.ROUTES
    r = B.get(R["home"])
    _ok(r.status == 200, f"home {r.status}")
    want = "Welcome to RAD Store" if getattr(S, "DESIGN", None) else "RAD Store"
    _ok(want in r.text, f"home page has no {want!r}")
    notes = [f"home {r.status}"]
    if "products" in R:
        r = B.get(R["products"])
        _ok(r.status == 200 and "Laptop" in r.text and "Phone" in r.text, f"products {r.status}: {r.text[:300]}")
        notes.append(f"products {r.status}")
    for key, want in (("css", "css"), ("js", "javascript")):
        if key in R:
            r = B.get(R[key])
            _ok(r.status == 200 and want in r.ctype, f"{key} {r.status} {r.ctype}")
            notes.append(f"{key} {r.status}")
    if getattr(S, "MISSING", "/no-such-page-404"):
        r = B.get(getattr(S, "MISSING", "/no-such-page-404"))
        _ok(r.status == 404, f"missing page gives {r.status}")
        notes.append("missing 404")
    return ", ".join(notes)


def login(S, B, user="admin", password="secret"):
    f = getattr(S, "LOGIN_FIELDS", ("username", "password"))
    return B.submit(S.ROUTES["login"], {f[0]: user, f[1]: password})


def auth(S, B, browser_cls) -> str:
    R = S.ROUTES
    anon = browser_cls(B.base)
    r = anon.get(R["add"], follow=False)
    _ok(r.status in (301, 302, 303, 307, 401, 403), f"anonymous add page answers {r.status}")
    r = login(S, B, "admin", "wrong-password")
    _ok(r.status in (200, 401, 422) and re.search(getattr(S, "LOGIN_ERROR", "Invalid"), r.text, re.I),
        f"wrong password: {r.status} {r.text[:300]}")
    r = login(S, B)
    _ok(r.status == 200 and "Log out" in r.text, f"login: {r.status} chain={r.chain}")
    return "anonymous redirected, wrong password refused, logged in"


def api_rows(S, B):
    r = B.get(S.ROUTES["api"], headers={"Accept": "application/json"})
    return r, (r.json() if r.status == 200 else None)


def crud(S, B) -> str:
    R = S.ROUTES
    nf, pf = getattr(S, "PRODUCT_FIELDS", ("name", "price"))
    n0 = len(api_rows(S, B)[1] or [])
    r = B.submit(R["add"], {nf: "", pf: "5"})
    _ok(re.search(getattr(S, "REQUIRED_ERROR", "Name is required|required|blank|empty"), r.text, re.I)
        and r.status in (200, 400, 422), f"empty name accepted? {r.status}")
    _ok(len(api_rows(S, B)[1] or []) == n0, "an invalid product was saved")
    r = B.submit(R["add"], {nf: "Tablet", pf: "300"})
    _ok(r.status == 200 and "Tablet" in r.text, f"add: {r.status} chain={r.chain}")
    pid = next((p.get("id") for p in api_rows(S, B)[1] or [] if p.get("name") == "Tablet"), None)
    _ok(pid is not None, "Tablet not in the API after add")
    edit = R["edit"].format(id=pid)
    r = B.submit(edit, {nf: "Tablet Pro", pf: "350"}, form_match=getattr(S, "EDIT_FORM_MATCH", ""))
    _ok(r.status == 200 and "Tablet Pro" in r.text, f"edit: {r.status} chain={r.chain}")
    r = B.submit(R.get("delete_page", edit).format(id=pid), {}, form_match=getattr(S, "DELETE_FORM_MATCH", "delete"))
    _ok(r.status == 200 and "Tablet Pro" not in r.text, f"delete: {r.status}")
    return f"validation, add (id {pid}), edit, delete"


def api(S, B) -> str:
    r, rows = api_rows(S, B)
    _ok(r.status == 200 and "json" in r.ctype, f"api {r.status} {r.ctype}")
    _ok(isinstance(rows, list) and {"Laptop", "Phone"} <= {p.get("name") for p in rows}, f"api rows {str(rows)[:200]}")
    return f"{len(rows)} products"


def arabic(S, B) -> str:
    r = B.get(S.ROUTES["ar"])
    _ok(r.status == 200, f"ar {r.status}")
    _ok(re.search(r'<html[^>]*dir="rtl"', r.text) and re.search(r'<html[^>]*lang="ar"', r.text),
        "no <html lang=ar dir=rtl>")
    _ok("متجر" in r.text, "Arabic text missing")
    return "lang=ar dir=rtl"
