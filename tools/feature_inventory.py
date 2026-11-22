r"""Feature inventory of the RAD IDE - every user-facing entry point, collected automatically from a running IDE.

    .venv\Scripts\python tools\feature_inventory.py                  # every context x every layout
    .venv\Scripts\python tools\feature_inventory.py --contexts python-tk,web --modes vs

For every project context (samples/Tests/Crawler/crawl_common.CONTEXTS: no project, Python Tk, VB6, C#, web site,
Flask, Flutter, retro console, DOS, pygame, NASM, firmware ECU) and every workbench layout (VS / VS Code / Agent) a
worker process opens the IDE offscreen (QSettings org RADIDE-TEST-CRAWL, cleared before and after) with a sandbox copy
of the project and records, without triggering anything:
  * every QAction of the menu bar and its sub menus (aboutToShow emitted: dynamic menus fill), the menu-bar corner,
  * every tool bar action / widget, every Command Palette command (radide/features/command_palette.py),
  * every context menu: Solution Explorer item of each kind, editor tab, designer (form / control), every dock widget
    with a custom context menu,
  * every dock / tool window, every QShortcut,
plus, once: every dialog class (static scan, tools/feature_static.py), the New Project languages and their templates,
the Options pages, the Publish dialog options (desktop installer + web site).

Writes docs/features/inventory.json and docs/features/INVENTORY.md (grouped by menu).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Crawler"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import crawl_common as C  # noqa: E402

OUT_DIR = ROOT / "docs" / "features"


# ============================================================================================ worker (one context)
def worker(ctx: str, modes: list[str], out_file: Path, sandbox: Path, extras: bool, app: str = "") -> None:
    app = app or "inv-" + ctx
    C.boot(app)
    C._dismiss_timer = C.auto_dismiss()      # modal dialogs that open by themselves are rejected
    w = C.window()
    folder = C.open_context(w, ctx, sandbox)
    res = {"context": ctx, "project_language": getattr(w.project, "language", None) if w.project else None,
           "modes": {}}
    for mode in modes:
        ok = C.set_mode(w, mode)
        C.pump(0.8)
        t = time.time()
        ents = [C.strip(e) for e in C.harvest(w)]
        res["modes"][mode] = {"mode_ok": ok, "entries": ents, "docks": C.docks(w), "shortcuts": C.shortcuts(w),
                              "seconds": round(time.time() - t, 1)}
        print(f"[inventory] {ctx}/{mode}: {len(ents)} entries", flush=True)
    C.set_mode(w, "vs")
    if extras:
        res["extras"] = collect_extras(w, ctx, folder)
    res["dismissed_dialogs"] = list(C.DISMISSED)
    out_file.write_text(json.dumps(res, ensure_ascii=False, default=str), encoding="utf-8")
    try:
        w.close()
        C.pump(0.3)
    except Exception:  # noqa: BLE001
        pass
    C.clear_settings(app)
    try:                                  # the VS Code extension host and other helpers this worker started
        import psutil
        for c in psutil.Process().children(recursive=True):
            c.kill()
    except Exception:  # noqa: BLE001
        pass
    sys.stdout.flush()
    os._exit(0)


def _page_texts(page) -> list[str]:
    from PyQt6.QtWidgets import QAbstractButton, QGroupBox, QLabel
    out = []
    for wd in page.findChildren((QLabel, QAbstractButton, QGroupBox)):
        t = wd.title() if isinstance(wd, QGroupBox) else wd.text()
        t = C.clean(t)
        if t and len(t) < 90 and "<" not in t:
            out.append(t)
    return out


def collect_extras(w, ctx: str, folder) -> dict:
    ex: dict = {}
    try:                                                   # New Project: languages -> templates
        from radide.dialogs import NewProjectDialog
        from PyQt6.QtCore import Qt
        dlg = NewProjectDialog(w)
        langs = OrderedDict()
        for i in range(dlg.langs.topLevelItemCount()):
            g = dlg.langs.topLevelItem(i)
            for j in range(g.childCount()):
                it = g.child(j)
                dlg.langs.setCurrentItem(it)
                C.APP.processEvents()
                tpls = [dlg.templates.item(k).text() for k in range(dlg.templates.count())
                        if not dlg.templates.item(k).isHidden()]
                tids = [str(dlg.templates.item(k).data(Qt.ItemDataRole.UserRole)) for k in
                        range(dlg.templates.count()) if not dlg.templates.item(k).isHidden()]
                langs[f"{g.text(0)} > {it.text(0)}"] = {"id": str(it.data(0, Qt.ItemDataRole.UserRole)),
                                                        "templates": tpls, "template_ids": tids}
        ex["new_project"] = langs
        dlg.deleteLater()
    except Exception as e:  # noqa: BLE001
        ex["new_project_error"] = repr(e)
    try:                                                   # Options pages
        from radide.features.settings import OptionsDialog
        from PyQt6.QtWidgets import QTabWidget
        dlg = OptionsDialog(w)
        pages = OrderedDict()
        tabs = dlg.findChildren(QTabWidget)
        if tabs:
            t = tabs[0]
            for i in range(t.count()):
                pages[C.clean(t.tabText(i))] = _page_texts(t.widget(i))
        ex["options_pages"] = pages
        dlg.deleteLater()
    except Exception as e:  # noqa: BLE001
        ex["options_error"] = repr(e)
    if folder is not None and w.project is not None:       # Publish dialogs
        try:
            from radide.features.installer import PublishDialog
            dlg = PublishDialog(w, Path(w.project.folder), w.project.name)
            ex["publish_desktop"] = C.dialog_controls(dlg) | {"texts": _page_texts(dlg)}
            dlg.deleteLater()
        except Exception as e:  # noqa: BLE001
            ex["publish_desktop_error"] = repr(e)
        try:
            from radide.features.web_tools import PublishDialog as WebPublish
            dlg = WebPublish(w, w.project)
            ex["publish_web"] = C.dialog_controls(dlg) | {"texts": _page_texts(dlg)}
            dlg.deleteLater()
        except Exception as e:  # noqa: BLE001
            ex["publish_web_error"] = repr(e)
    return ex


# ============================================================================================ parent
def run_workers(contexts, modes, scratch: Path, timeout: int) -> dict:
    data = {}
    env = dict(os.environ)
    env.update(C.ENV)
    for ctx in contexts:
        f = scratch / f"inv-{ctx}.json"
        f.unlink(missing_ok=True)
        extras = ctx in ("python-tk", "web")
        cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--worker", ctx, "--modes", ",".join(modes),
               "--out-file", str(f), "--sandbox", str(scratch / "sandbox")] + (["--extras"] if extras else [])
        t = time.time()
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from run_tests import _Job
        for attempt in range(3):           # an offscreen QtWebEngine start-up crash now and then: try again
            with open(scratch / f"inv-{ctx}.log", "a", encoding="utf-8") as log:
                p = subprocess.Popen(cmd + ["--app-name", f"inv-{ctx}-{attempt}"], cwd=str(ROOT), env=env,
                                     stdout=log, stderr=subprocess.STDOUT)
                job = _Job()
                job.assign(p)
                try:
                    rc = p.wait(timeout=timeout)
                    if rc:
                        print(f"[inventory] {ctx}: worker exit code {rc}", flush=True)
                except subprocess.TimeoutExpired:
                    print(f"[inventory] {ctx}: TIMEOUT", flush=True)
                job.terminate()            # WebEngine / extension host processes the worker left behind
                job.close()
            if f.exists():
                break
            time.sleep(2)
        if f.exists():
            data[ctx] = json.loads(f.read_text(encoding="utf-8"))
            print(f"[inventory] {ctx}: done in {time.time() - t:.0f}s", flush=True)
        else:
            data[ctx] = {"context": ctx, "error": "worker failed (see log)", "modes": {}}
            print(f"[inventory] {ctx}: FAILED (log {scratch / f'inv-{ctx}.log'})", flush=True)
    return data


def area_of(e: dict) -> str:
    if e["source"] == "palette":
        return "Command Palette"
    if e["source"] == "context":
        return "Context menu: " + e["path"][0]
    if e["source"] == "toolbar":
        return e["path"][0] if e["path"] else "Toolbar"
    return e["path"][0] if e["path"] else "Menu bar"


def merge(data: dict) -> dict:
    """One item per distinct entry (key), with the contexts / layouts where it appears."""
    import feature_static as FS
    items: dict[str, dict] = {}
    docks: dict[str, dict] = {}
    shortcuts: dict[str, dict] = {}
    for ctx, d in data.items():
        for mode, md in d.get("modes", {}).items():
            for e in md["entries"]:
                if e.get("kind") == "error":
                    e = dict(e, key=f"error|{' > '.join(e['path'])}|{e.get('error', '')}")
                it = items.get(e["key"])
                if it is None:
                    it = items[e["key"]] = {k: e.get(k) for k in ("key", "source", "path", "text", "shortcut", "kind",
                                                                  "id", "checkable", "item_kind", "error", "attr")
                                            if e.get(k) not in (None, "", False)}
                    it["area"] = area_of(e)
                    it["contexts"], it["modes"], it["enabled_in"] = [], [], []
                if ctx not in it["contexts"]:
                    it["contexts"].append(ctx)
                if mode not in it["modes"]:
                    it["modes"].append(mode)
                if e.get("enabled") and f"{ctx}/{mode}" not in it["enabled_in"]:
                    it["enabled_in"].append(f"{ctx}/{mode}")
                if e.get("shortcut") and e["shortcut"] not in shortcuts:
                    shortcuts[e["shortcut"]] = {"key": e["shortcut"], "command": " > ".join(e["path"] + [e["text"]])}
            for dk in md.get("docks", []):
                k = dk["title"] or dk["object"]
                x = docks.setdefault(k, {"title": dk["title"], "object": dk["object"], "widget": dk["widget"],
                                         "contexts": [], "modes": [], "visible_in": []})
                for f, v in (("contexts", ctx), ("modes", mode)):
                    if v not in x[f]:
                        x[f].append(v)
                if dk["visible"]:
                    x["visible_in"].append(f"{ctx}/{mode}")
            for sc in md.get("shortcuts", []):
                shortcuts.setdefault(sc["key"], {"key": sc["key"], "command": f"QShortcut on {sc['parent']}"
                                                 + (f" ({sc['what']})" if sc.get("what") else "")})
    slots = FS.action_slots()
    for it in items.values():
        s = slots.get(it["text"])
        if s:
            it["slots"] = sorted({f for x in s for f in x["functions"]})[:8]
            it["slot_modules"] = sorted({x["module"] for x in s})[:4]
    extras = {}
    for d in data.values():
        for k, v in (d.get("extras") or {}).items():
            extras.setdefault(k, v)
    dialogs = FS.dialog_classes()
    templates = []
    for lang, v in (extras.get("new_project") or {}).items():
        for i, t in enumerate(v["templates"]):
            tid = (v.get("template_ids") or [""] * len(v["templates"]))[i]
            templates.append({"language": lang, "language_id": v["id"], "template": t, "template_id": tid})
    return {"generated": time.strftime("%Y-%m-%d %H:%M"), "contexts": {c: C.CONTEXTS[c][1] for c in data},
            "context_languages": {c: d.get("project_language") for c, d in data.items()},
            "errors": {c: d["error"] for c, d in data.items() if d.get("error")},
            "entries": sorted(items.values(), key=lambda i: (i["area"], i["key"])),
            "docks": sorted(docks.values(), key=lambda x: x["title"]), "shortcuts": sorted(shortcuts.values(),
                                                                                          key=lambda x: x["key"]),
            "dialogs": dialogs, "new_project": extras.get("new_project", {}), "templates": templates,
            "options_pages": extras.get("options_pages", {}),
            "publish": {"desktop": extras.get("publish_desktop"), "web": extras.get("publish_web")}}


def summary(inv: dict) -> dict:
    by_area = defaultdict(int)
    for e in inv["entries"]:
        by_area[e["area"]] += 1
    return {"entries": len(inv["entries"]), "by_area": dict(sorted(by_area.items())), "docks": len(inv["docks"]),
            "shortcuts": len(inv["shortcuts"]), "dialog_classes": len(inv["dialogs"]),
            "new_project_languages": len(inv["new_project"]), "templates": len(inv["templates"]),
            "options_pages": len(inv["options_pages"])}


def write_md(inv: dict, path: Path) -> None:
    s = inv["summary"]
    L = ["# RAD IDE feature inventory", "",
         f"Generated {inv['generated']} by `tools/feature_inventory.py` from a running IDE (offscreen) - do not edit. "
         "Traceability to tests: [TEST_MATRIX.md](TEST_MATRIX.md).", "",
         f"**{s['entries']}** distinct entry points (menu / tool bar / palette / context-menu items), "
         f"**{s['docks']}** docks / tool windows, **{s['shortcuts']}** keyboard shortcuts, **{s['dialog_classes']}** "
         f"dialog classes, **{s['new_project_languages']}** New Project languages with **{s['templates']}** "
         f"templates, **{s['options_pages']}** Options pages.", "",
         "Contexts (a sandbox copy of each project, opened in every layout VS / VS Code / Agent):", ""]
    for c, desc in inv["contexts"].items():
        L.append(f"* `{c}` - {desc}" + (f" (language `{inv['context_languages'].get(c)}`)"
                                        if inv["context_languages"].get(c) else ""))
    if inv.get("errors"):
        L += ["", "Contexts that failed: " + ", ".join(f"`{k}` ({v})" for k, v in inv["errors"].items())]
    L += ["", "## Entry points per area", "", "| Area | Entries |", "|---|---|"]
    for a, n in s["by_area"].items():
        L.append(f"| {a} | {n} |")
    all_ctx = set(inv["contexts"])
    groups = defaultdict(list)
    for e in inv["entries"]:
        groups[e["area"]].append(e)

    def where(e):
        cs = set(e["contexts"])
        ms = set(e["modes"])
        c = "all contexts" if cs == all_ctx else ", ".join(sorted(cs))
        m = "" if ms == {"vs", "vscode", "agent"} else " [" + ",".join(sorted(ms)) + "]"
        return c + m
    for area in sorted(groups):
        L += ["", f"## {area}", "", "| Item | Shortcut | Where |", "|---|---|---|"]
        for e in groups[area]:
            p = " > ".join(e["path"][1:] + [e["text"]]) if e["source"] != "palette" else (
                " > ".join(e["path"][1:] + [e["text"]]) + (f" (`{e['id']}`)" if e.get("id") else ""))
            L.append(f"| {p.replace('|', '/')} | {e.get('shortcut', '')} | {where(e)} |")
    L += ["", "## Docks / tool windows", "", "| Title | Widget | Layouts |", "|---|---|---|"]
    for d in inv["docks"]:
        L.append(f"| {d['title'] or d['object']} | {d['widget']} | {','.join(sorted(d['modes']))} |")
    L += ["", "## Keyboard shortcuts", "", "| Keys | Command |", "|---|---|"]
    for sc in inv["shortcuts"]:
        L.append(f"| `{sc['key']}` | {sc['command'].replace('|', '/')} |")
    L += ["", "## New Project languages and templates", "", "| Language | Templates |", "|---|---|"]
    for lang, v in inv["new_project"].items():
        L.append(f"| {lang} (`{v['id']}`) | {', '.join(v['templates'])} |")
    L += ["", "## Options pages", ""]
    for page, texts in inv["options_pages"].items():
        L.append(f"* **{page}**: " + "; ".join(texts[:40]) + (" ..." if len(texts) > 40 else ""))
    for k, title in (("desktop", "Publish (desktop installer)"), ("web", "Publish (web site)")):
        p = inv["publish"].get(k)
        if p:
            L += ["", f"## {title}", "", f"Dialog `{p['class']}` '{p['title']}'.", ""]
            for f in ("tabs", "combos", "checks", "radios"):
                if p.get(f):
                    L.append(f"* {f}: " + "; ".join(str(x) for x in p[f])[:1500])
    L += ["", "## Dialog classes", "", "| Class | Module | Title |", "|---|---|---|"]
    for d in inv["dialogs"]:
        L.append(f"| {d['class']} | `{d['module']}` | {d['title'].replace('|', '/')} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", default="")
    ap.add_argument("--modes", default=",".join(C.MODES))
    ap.add_argument("--contexts", default=",".join(C.CONTEXTS))
    ap.add_argument("--out-file", default="")
    ap.add_argument("--sandbox", default="")
    ap.add_argument("--extras", action="store_true")
    ap.add_argument("--app-name", default="")
    ap.add_argument("--scratch", default=str(Path(tempfile.gettempdir()) / "radide-inventory"))
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--from-scratch", action="store_true", help="only merge the worker files already in --scratch")
    a = ap.parse_args()
    modes = [m for m in a.modes.split(",") if m]
    if a.worker:
        worker(a.worker, modes, Path(a.out_file), Path(a.sandbox), a.extras, a.app_name)
        return 0
    scratch = Path(a.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    contexts = [c for c in a.contexts.split(",") if c]
    if a.from_scratch:
        data = {c: json.loads((scratch / f"inv-{c}.json").read_text(encoding="utf-8")) for c in contexts
                if (scratch / f"inv-{c}.json").exists()}
    else:
        data = run_workers(contexts, modes, scratch, a.timeout)     # each worker clears its own settings
    inv = merge(data)
    inv["summary"] = summary(inv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "inventory.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(inv, OUT_DIR / "INVENTORY.md")
    print(json.dumps(inv["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
