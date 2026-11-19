"""Electron / NW.js programs -> static web project (HTML / CSS / JavaScript).

The app's code ships as ``resources/app.asar`` (an archive: 16-byte pickle header + JSON file index + file
data, read here without Node), a ``resources/app`` folder, or NW.js ``package.nw`` (a zip, possibly appended
to nw.exe).  The files are extracted (``app.asar.unpacked`` files too), the main process script and the
window page(s) it loads are found from package.json / ``loadFile`` / ``loadURL``, and the renderer files
become a static web site project (the ``static-web`` plugin); main-process code that needs Node/Electron
APIs is listed in the report.  Only for programs you wrote, own, or may legally analyse.
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import zipfile
from pathlib import Path

from .base import BinaryInfo, ImportResult
from .dotnet import say

TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".cjs", ".css", ".json", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
            ".md", ".txt", ".svg", ".xml"}
WEB_LANG = "static-web"


# ============================================================================ asar
def read_asar_index(path: Path) -> tuple[dict, int]:
    """(file tree, offset of the file data)."""
    with open(path, "rb") as fh:
        head = fh.read(16)
        if len(head) < 16:
            raise ValueError("not an asar archive")
        _four, header_size, _pickle_size, json_size = struct.unpack("<IIII", head)
        raw = fh.read(json_size)
    tree = json.loads(raw.decode("utf-8"))
    return tree, 8 + header_size


def extract_asar(path: Path, out: Path, progress=None, limit_mb: int = 800) -> tuple[int, list[str]]:
    """Extract *path* into *out*; returns (files written, notes)."""
    tree, base = read_asar_index(path)
    unpacked = Path(str(path) + ".unpacked")
    notes: list[str] = []
    count, total = 0, 0
    out.mkdir(parents=True, exist_ok=True)
    root = out.resolve()

    with open(path, "rb") as fh:
        def walk(node: dict, rel: Path):
            nonlocal count, total
            for name, entry in (node.get("files") or {}).items():
                if name in ("", ".", "..") or "/" in name or "\\" in name:
                    continue
                child = rel / name
                dest = (out / child).resolve()
                if not str(dest).startswith(str(root)):
                    continue
                if "files" in entry:
                    walk(entry, child)
                    continue
                if "link" in entry:
                    notes.append(f"symbolic link skipped: {child.as_posix()}")
                    continue
                size = int(entry.get("size", 0))
                dest.parent.mkdir(parents=True, exist_ok=True)
                if entry.get("unpacked"):
                    src = unpacked / child
                    if src.is_file():
                        shutil.copy2(src, dest)
                        count += 1
                    continue
                total += size
                if total > limit_mb * 1024 * 1024:
                    notes.append(f"stopped after {limit_mb} MB")
                    raise StopIteration
                fh.seek(base + int(entry.get("offset", 0)))
                dest.write_bytes(fh.read(size))
                count += 1
                if count % 500 == 0:
                    say(progress, f"Extracted {count} files ...")
        try:
            walk(tree, Path())
        except StopIteration:
            pass
    return count, notes


def _find_app(path: Path, info) -> tuple[str, Path | None]:
    """('asar' | 'dir' | 'zip', location) of the app code."""
    d = getattr(info, "details", {}) or {}
    if path.suffix.lower() == ".asar":
        return "asar", path
    cand = d.get("asar")
    if cand and Path(cand).exists():
        return ("asar" if Path(cand).is_file() else "dir"), Path(cand)
    folder = path.parent
    for c in (folder / "resources" / "app.asar", folder / "resources" / "default_app.asar"):
        if c.is_file() and c.name == "app.asar":
            return "asar", c
    if (folder / "resources" / "app").is_dir():
        return "dir", folder / "resources" / "app"
    if (folder / "package.nw").exists():
        p = folder / "package.nw"
        return ("dir", p) if p.is_dir() else ("zip", p)
    try:                                        # NW.js: zip appended to nw.exe
        with zipfile.ZipFile(path) as z:
            if "package.json" in z.namelist():
                return "zip", path
    except (zipfile.BadZipFile, OSError):
        pass
    return "", None


def _main_and_pages(app: Path) -> tuple[str, list[str], dict]:
    pkg = {}
    try:
        pkg = json.loads((app / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    main = str(pkg.get("main") or "")
    if not main and (app / "index.js").exists():
        main = "index.js"
    pages: list[str] = []
    if isinstance(pkg.get("main"), str) and pkg["main"].endswith((".html", ".htm")):     # NW.js
        pages.append(pkg["main"])
    main_path = app / main if main else None
    if main_path and main_path.is_file() and main_path.suffix in (".js", ".cjs", ".mjs"):
        text = main_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"loadFile\(\s*(?:path\.join\([^,]*,\s*)?['\"`]([^'\"`]+\.html?)['\"`]", text):
            pages.append(str((main_path.parent / m.group(1)).resolve().relative_to(app.resolve()).as_posix())
                         if (main_path.parent / m.group(1)).exists() else m.group(1))
        for m in re.finditer(r"loadURL\(\s*[`'\"]file://[^'\"`]*?([\w./-]+\.html?)", text):
            pages.append(m.group(1))
    if not pages:
        pages = [p.relative_to(app).as_posix() for p in sorted(app.rglob("index.html"))
                 if "node_modules" not in p.parts][:1]
    if not pages:
        pages = [p.relative_to(app).as_posix() for p in sorted(app.rglob("*.html"))
                 if "node_modules" not in p.parts][:3]
    return main, list(dict.fromkeys(pages)), pkg


# ============================================================================ backend API
def can_handle(info: BinaryInfo) -> bool:
    return getattr(info, "kind", "") in ("electron", "nwjs")


def run(path, info: BinaryInfo, workdir, progress=None, ai_translate: bool = False) -> ImportResult:
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    kind, loc = _find_app(path, info)
    if loc is None:
        res.add("error", "The app's code was not found (resources/app.asar, resources/app or package.nw). "
                         "If this is an installer, install the program first and import the installed .exe.")
        return res
    app = workdir / "app"
    if app.exists():
        shutil.rmtree(app, ignore_errors=True)
    say(progress, f"Extracting {loc.name} ...")
    if kind == "asar":
        try:
            n, notes = extract_asar(loc, app, progress)
        except (ValueError, OSError, json.JSONDecodeError) as e:
            res.add("error", f"{loc.name} is not a readable asar archive ({e}).")
            return res
        for x in notes:
            res.add("warn", x)
        res.add("exact", f"Extracted {n} file(s) from {loc.name}.")
    elif kind == "dir":
        shutil.copytree(loc, app, ignore=shutil.ignore_patterns("node_modules"))
        res.add("exact", f"Copied the app folder {loc} (node_modules skipped).")
    else:
        with zipfile.ZipFile(loc) as z:
            root = app.resolve()
            for member in z.namelist():
                dest = (app / member).resolve()
                if not str(dest).startswith(str(root)) or member.endswith("/"):
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(member))
        res.add("exact", f"Extracted the NW.js package {loc.name}.")
    res.source_dir = app
    main, pages, pkg = _main_and_pages(app)
    res.resources["package"] = {k: pkg.get(k) for k in ("name", "productName", "version", "description",
                                                        "main", "author") if pkg.get(k)}
    res.resources["main"] = main
    res.resources["pages"] = pages
    res.resources["project_language"] = WEB_LANG
    res.resources["startup_page"] = pages[0] if pages else ""
    # the web project: every text file outside node_modules (binary assets are listed in resources)
    assets = []
    for f in sorted(app.rglob("*")):
        if not f.is_file() or "node_modules" in f.parts:
            continue
        rel = f.relative_to(app).as_posix()
        if f.suffix.lower() in TEXT_EXT and f.stat().st_size < 2 * 1024 * 1024:
            lang = {".html": "html", ".htm": "html", ".css": "css", ".json": "json", ".ts": "typescript",
                    ".tsx": "typescript"}.get(f.suffix.lower(), "javascript" if f.suffix.lower() in
                                               (".js", ".mjs", ".cjs", ".jsx") else "text")
            res.modules.append((rel, f.read_text(encoding="utf-8", errors="replace"), lang))
        else:
            assets.append(rel)
    res.resources["files"] = assets
    if assets:
        res.add("info", f"{len(assets)} asset file(s) (images, fonts, ...) are in _original/app.")
    if pages:
        res.add("exact", "Window page(s): " + ", ".join(pages) + " - open them in the web designer.")
    else:
        res.add("missing", "No HTML page found: the window may be built by a bundler at run time "
                           "(look for dist/ or build/ folders).")
    if main:
        mtext = (app / main).read_text(encoding="utf-8", errors="replace") if (app / main).is_file() else ""
        apis = sorted(set(re.findall(r"\b(ipcMain|ipcRenderer|BrowserWindow|dialog|Menu|Tray|shell|"
                                     r"require\(['\"](?:fs|child_process|os|path)['\"]\))", mtext)))
        res.add("info", f"Main process script: {main}" + (f" (uses {', '.join(apis)})" if apis else "") +
                " - it runs in Node.js, not in the browser; its window/menu code is not part of the web site.")
    minified = [m[0] for m in res.modules if m[0].endswith(".js") and
                max((len(x) for x in m[1].splitlines()), default=0) > 2000]
    if minified:
        res.add("warn", f"{len(minified)} script(s) are bundled/minified (e.g. {minified[0]}) - use Format "
                        "Document in the editor; original source maps are not included in the app.")
    nm = app / "node_modules"
    if nm.is_dir():
        res.add("info", "node_modules was extracted to _original/app/node_modules (not added to the project).")
    return res
