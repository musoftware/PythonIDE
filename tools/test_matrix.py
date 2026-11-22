r"""Traceability matrix: every item of docs/features/inventory.json -> the tests that cover it.

    .venv\Scripts\python tools\test_matrix.py [--crawl <crawl_results.json>]

Status of an item:
  * covered       a test script under samples/Tests (not the crawler) refers to it directly: the item's text as a
                  string literal (generic words like "Open" / "Delete" only together with their menu's name in the same
                  file), its Command Palette id, the window attribute holding the action (win.a_run), or a function
                  the action calls (tools/feature_static.action_slots: ``self.build_solution`` -> ``build_solution(``)
  * crawler-only  only the action crawler triggered it (smoke: no exception / hang / crash / modal left)
  * NOT covered   nothing
Docks (title), dialog classes (class name), New Project templates (template title), Options pages (page title) and
keyboard shortcuts (key text) are matched by literal too.

The crawler status comes from --crawl (a crawl_results.json of samples/Tests/Crawler/test_action_crawler.py); the last
one used is kept in docs/features/crawl_status.json so the matrix can be regenerated without crawling again.
Writes docs/features/TEST_MATRIX.md and docs/features/test_matrix.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "samples" / "Tests"
DOCS = ROOT / "docs" / "features"
SKIP_DIRS = {"All", "node_modules", ".venv", "__pycache__", "Crawler", ".dart_tool", "build"}
GENERIC = {"open", "close", "delete", "save", "new", "add", "remove", "rename", "properties", "run", "stop", "copy",
           "paste", "cut", "undo", "redo", "refresh", "settings", "options", "help", "about", "start", "build",
           "clean", "edit", "view", "find", "replace", "select all", "close all", "cancel", "ok", "apply", "reset",
           "clear", "export", "import", "import...", "show", "hide", "next", "previous", "back", "forward", "home",
           "up", "down", "left", "right", "top", "bottom", "lefts", "rights", "tops", "bottoms", "middles", "centers",
           "width", "height", "both", "increase", "decrease", "make equal", "horizontally", "vertically", "debug",
           "test", "tests", "format", "tools", "window", "file", "project", "open folder", "code", "designer",
           "terminal", "output", "go", "list", "info", "log", "status", "commit", "pull", "fetch", "push", "branch",
           "merge", "diff", "zoom in", "zoom out", "reset zoom", "portrait", "landscape", "default"}
STOP_SLOTS = {"show", "close", "open", "accept", "reject", "run", "refresh", "trigger", "save", "exec", "setText",
              "toggle", "start", "stop", "clear", "update", "log", "emit", "setVisible", "setEnabled", "activate",
              "_run", "_open", "_show", "go", "act", "run_cli", "open_file", "open_url", "setChecked", "raise_",
              "isChecked", "setFocus", "showMessage", "statusBar", "_act", "addAction", "deleteLater", "hide",
              "copy", "paste", "cut", "undo", "redo", "select_all", "selectAll", "new_project", "window", "_edit",
              "_menu", "menu", "lambda", "partial", "getattr", "setattr", "isinstance", "self", "win", "show_view",
              "_log", "_say", "say", "ask", "confirm", "_call", "call", "invoke", "apply", "reset", "load", "dump"}
AREA_WEIGHT = {"Build": 100, "Debug": 95, "Publish": 95, "Run": 90, "Format": 85, "Context menu: Designer": 85,
               "File": 80, "Project": 75, "Context menu: Solution Explorer": 72, "Edit": 70, "View": 60,
               "Test": 55, "Git": 50, "Site": 50, "Context menu: Editor tab": 50, "Toolbar Standard": 80,
               "Toolbar Debug": 75, "Data": 40, "Tools": 40, "Analyze": 35, "Command Palette": 30, "Help": 20}


def norm(t: str) -> str:
    t = (t or "").split("\t", 1)[0].replace("&&", "\0").replace("&", "").replace("\0", "&").replace("...", "")
    t = t.replace("…", "")
    return re.sub(r"\s+", " ", t).strip().lower()


STR_RE = re.compile(r"""(?:[rRbBuUfF]{0,2})("(?:[^"\\\n]|\\.){1,200}"|'(?:[^'\\\n]|\\.){1,200}')""")


class Corpus:
    def __init__(self):
        self.files: dict[str, dict] = {}
        for p in sorted(TESTS.rglob("*.py")):
            rel = p.relative_to(TESTS)
            if SKIP_DIRS & set(rel.parts[:-1]):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            strings = set()
            for m in STR_RE.finditer(text):
                s = m.group(1)[1:-1]
                n = norm(s)
                if n:
                    strings.add(n)
                    for part in re.split(r"\s*(?:>|:|/|\|)\s*", n):      # "Build > Build Solution", "Build: X"
                        if part:
                            strings.add(part)
            self.files[rel.as_posix()] = {"text": text, "strings": strings,
                                          "idents": set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text))}
        self.string_index: dict[str, set[str]] = defaultdict(set)
        self.ident_index: dict[str, set[str]] = defaultdict(set)
        for f, d in self.files.items():
            for s in d["strings"]:
                self.string_index[s].add(f)
            for i in d["idents"]:
                self.ident_index[i].add(f)

    def by_string(self, s: str) -> set[str]:
        return set(self.string_index.get(norm(s), ()))

    def by_ident(self, name: str) -> set[str]:
        return set(self.ident_index.get(name, ()))


def entry_tests(e: dict, cor: Corpus) -> tuple[set[str], list[str]]:
    why = []
    files: set[str] = set()
    text = norm(e["text"])
    if len(text) >= 3:
        hit = cor.by_string(text)
        if hit and (text in GENERIC or len(text) < 5):
            ctx_words = [norm(p) for p in e["path"] if norm(p) and norm(p) not in ("command palette",)]
            ctx_words = [re.sub(r"^\(|\)$", "", c) for c in ctx_words]
            hit = {f for f in hit if any(c and (c in cor.files[f]["strings"]) for c in ctx_words[-2:])}
        if hit:
            files |= hit
            why.append("text")
    if e.get("id"):
        hit = cor.by_string(e["id"])
        if hit:
            files |= hit
            why.append("command id")
    if e.get("attr"):
        last = e["attr"].split(".")[-1]
        if len(last) > 3:
            hit = {f for f in cor.by_ident(last) if re.search(r"\b" + re.escape(last) + r"\b", cor.files[f]["text"])}
            if hit:
                files |= hit
                why.append("attribute")
    for s in e.get("slots") or []:
        if s in STOP_SLOTS or len(s) < 6 or s.startswith("__"):
            continue
        hit = {f for f in cor.by_ident(s) if re.search(r"\b" + re.escape(s) + r"\s*\(", cor.files[f]["text"])}
        if hit:
            files |= hit
            why.append(f"calls {s}()")
    return files, why


def importance(e: dict, n_ctx: int) -> int:
    area = e["area"]
    path0 = " ".join(e.get("path") or [])
    w = AREA_WEIGHT.get(area, 30)
    if "publish" in (path0 + " " + e["text"]).lower():
        w = max(w, 95)
    if e.get("shortcut"):
        w += 15
    if e["source"] == "toolbar":
        w += 10
    if len(e.get("contexts", [])) >= n_ctx:
        w += 10
    if not e.get("enabled_in"):
        w -= 20
    return w


def load_crawl(path: Path | None) -> dict[str, str]:
    status_file = DOCS / "crawl_status.json"
    if path is not None and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        st: dict[str, dict] = {}
        rank = {"ok": 0, "disabled": 1, "skipped": 2, "stale": 3, "modal-left": 4, "unresponsive": 5, "exception": 6,
                "hang": 7, "crash": 8}
        for r in data["results"]:
            k = r["key"]
            cur = st.get(k)
            # worst result wins, but "ok" anywhere beats "disabled" / "skipped"
            if cur is None or rank.get(r["result"], 9) > rank.get(cur["result"], 9) and r["result"] not in (
                    "disabled", "skipped", "stale") or (cur["result"] in ("disabled", "skipped", "stale")
                                                         and r["result"] == "ok"):
                st[k] = {"result": r["result"], "where": f"{r['context']}/{r['mode']}",
                         "error": (r.get("error") or "")[:300]}
        DOCS.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(st, indent=0, ensure_ascii=False), encoding="utf-8")
    if status_file.exists():
        return json.loads(status_file.read_text(encoding="utf-8"))
    return {}


def build(crawl_path: Path | None) -> dict:
    inv = json.loads((DOCS / "inventory.json").read_text(encoding="utf-8"))
    cor = Corpus()
    crawl = load_crawl(crawl_path)
    n_ctx = len(inv.get("contexts", {}))
    rows = []
    for e in inv["entries"]:
        if e.get("kind") == "error":
            continue
        files, why = entry_tests(e, cor)
        cs = crawl.get(e["key"])
        if files:
            status = "covered"
        elif cs and cs["result"] == "ok":
            status = "crawler-only"
        else:
            status = "NOT covered"
        rows.append({"type": "entry", "key": e["key"], "area": e["area"], "label": " > ".join(e["path"] + [e["text"]]),
                     "shortcut": e.get("shortcut", ""), "status": status, "tests": sorted(files)[:6],
                     "n_tests": len(files), "why": why, "crawl": cs["result"] if cs else "",
                     "crawl_where": cs["where"] if cs else "", "importance": importance(e, n_ctx),
                     "contexts": e.get("contexts", [])})
    # other inventory items
    for d in inv.get("docks", []):
        t = d["title"] or d["object"]
        files = cor.by_string(t) if len(norm(t)) >= 4 else set()
        rows.append({"type": "dock", "key": "dock|" + t, "area": "Docks / tool windows", "label": t,
                     "status": "covered" if files else "NOT covered", "tests": sorted(files)[:6],
                     "n_tests": len(files), "why": ["title"] if files else [], "crawl": "", "importance": 45})
    for d in inv.get("dialogs", []):
        files = {f for f in cor.by_ident(d["class"])}
        if not files and d.get("title") and len(norm(d["title"])) >= 6:
            files = cor.by_string(d["title"])
        rows.append({"type": "dialog", "key": f"dialog|{d['module']}.{d['class']}", "area": "Dialogs",
                     "label": f"{d['class']} ({d['module']})", "status": "covered" if files else "NOT covered",
                     "tests": sorted(files)[:6], "n_tests": len(files), "why": ["class"] if files else [],
                     "crawl": "", "importance": 40})
    for t in inv.get("templates", []):
        files = cor.by_string(t["template"]) & (cor.by_string(t["language_id"]) | cor.by_ident(t["language_id"])) \
            if len(norm(t["template"])) >= 4 else set()
        rows.append({"type": "template", "key": f"template|{t['language_id']}|{t['template']}",
                     "area": "New Project templates", "label": f"{t['language']} > {t['template']}",
                     "status": "covered" if files else "NOT covered", "tests": sorted(files)[:6],
                     "n_tests": len(files), "why": ["template+language"] if files else [], "crawl": "",
                     "importance": 60})
    for page in inv.get("options_pages", {}):
        files = cor.by_string(page) if len(norm(page)) >= 4 else set()
        files = {f for f in files if "option" in cor.files[f]["text"].lower()}
        rows.append({"type": "options", "key": "options|" + page, "area": "Options pages", "label": page,
                     "status": "covered" if files else "NOT covered", "tests": sorted(files)[:6],
                     "n_tests": len(files), "why": ["page"] if files else [], "crawl": "", "importance": 50})
    for sc in inv.get("shortcuts", []):
        k = sc["key"]
        variants = {k, k.replace("+", "+"), k.lower()}
        files = set()
        for v in variants:
            files |= cor.by_string(v)
        rows.append({"type": "shortcut", "key": "shortcut|" + k, "area": "Keyboard shortcuts",
                     "label": f"{k} - {sc['command']}", "status": "covered" if files else "NOT covered",
                     "tests": sorted(files)[:6], "n_tests": len(files), "why": ["key"] if files else [],
                     "crawl": "", "importance": 55})
    summ: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        summ[r["area"]][r["status"]] += 1
    tot = Counter(r["status"] for r in rows)
    return {"inventory_generated": inv.get("generated"), "rows": rows,
            "summary": {a: dict(c) for a, c in sorted(summ.items())}, "totals": dict(tot),
            "test_files": len(cor.files)}


def write_md(m: dict, path: Path) -> None:
    rows = m["rows"]
    t = m["totals"]
    n = len(rows)

    def pct(k):
        return f"{100 * t.get(k, 0) / max(1, n):.0f}%"
    L = ["# Test traceability matrix", "",
         f"Generated by `tools/test_matrix.py` from `docs/features/inventory.json` (inventory of "
         f"{m['inventory_generated']}) and {m['test_files']} test scripts under `samples/Tests` - do not edit.", "",
         f"**{n}** inventory items: **{t.get('covered', 0)}** covered ({pct('covered')}), "
         f"**{t.get('crawler-only', 0)}** crawler-only / smoke ({pct('crawler-only')}), "
         f"**{t.get('NOT covered', 0)}** NOT covered ({pct('NOT covered')}).", "",
         "*covered* = a test refers to the item directly (its text, palette id, window attribute or a function the "
         "action calls); *crawler-only* = only `samples/Tests/Crawler/test_action_crawler.py` triggered it without "
         "an error; *NOT covered* = nothing.", "",
         "## Summary per area", "", "| Area | Items | Covered | Crawler-only | NOT covered |", "|---|---|---|---|---|"]
    for a, c in sorted(m["summary"].items(), key=lambda kv: -sum(kv[1].values())):
        L.append(f"| {a} | {sum(c.values())} | {c.get('covered', 0)} | {c.get('crawler-only', 0)} | "
                 f"{c.get('NOT covered', 0)} |")
    nc = sorted([r for r in rows if r["status"] != "covered" and r["type"] == "entry"],
                key=lambda r: (-r["importance"], r["status"] != "NOT covered", r["label"]))
    L += ["", "## Not covered by a functional test, most important first", "",
          "Order: Build / Debug / Publish / Run / Designer (Format) / File / Project ... first; a shortcut, a tool bar "
          "button or presence in every context raise the rank. Crawler column: the crawler's result (empty = not "
          "crawled).", "", "| # | Item | Area | Shortcut | Status | Crawler |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(nc[:400], 1):
        L.append(f"| {i} | {r['label'].replace('|', '/')} | {r['area']} | {r.get('shortcut', '')} | {r['status']} | "
                 f"{r['crawl']} |")
    if len(nc) > 400:
        L.append(f"| ... | {len(nc) - 400} more in test_matrix.json | | | | |")
    L += ["", "## Full matrix", ""]
    by_area = defaultdict(list)
    for r in rows:
        by_area[r["area"]].append(r)
    for a in sorted(by_area):
        L += ["", f"### {a}", "", "| Item | Status | Tests | Crawler |", "|---|---|---|---|"]
        for r in sorted(by_area[a], key=lambda r: r["label"]):
            tests = ", ".join(f"`{x}`" for x in r["tests"][:3]) + (f" (+{r['n_tests'] - 3})" if r["n_tests"] > 3 else "")
            L.append(f"| {r['label'].replace('|', '/')[:150]} | {r['status']} | {tests} | {r.get('crawl', '')} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crawl", default="", help="crawl_results.json of the action crawler")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    m = build(Path(a.crawl) if a.crawl else None)
    (DOCS / "test_matrix.json").write_text(json.dumps(m, indent=0, ensure_ascii=False), encoding="utf-8")
    write_md(m, DOCS / "TEST_MATRIX.md")
    if not a.quiet:
        print(json.dumps(m["totals"]), f"({len(m['rows'])} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
