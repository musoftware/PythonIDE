"""Download package.json (top N by downloads) and .vsix bundles (top M under a size cap) from Open VSX and
count which built-in commands / context keys / API members / contribution points they use.
    python -I market_scan.py <download dir> <out json> [N] [M]"""
import json
import re
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

DL = Path(sys.argv[1])
OUT = Path(sys.argv[2])
N = int(sys.argv[3]) if len(sys.argv) > 3 else 200
M = int(sys.argv[4]) if len(sys.argv) > 4 else 60
CAP = 25 * 1024 * 1024
UA = {"User-Agent": "radide-reference-scan/1.0"}
DL.mkdir(parents=True, exist_ok=True)


def get(url, binary=False, timeout=60):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                data = r.read()
            return data if binary else json.loads(data.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(1 + attempt)
    raise err


exts = []
off = 0
while len(exts) < N:
    page = get(f"https://open-vsx.org/api/-/search?sortBy=downloadCount&sortOrder=desc&size=50&offset={off}&includeAllVersions=false")
    batch = page.get("extensions") or []
    if not batch:
        break
    exts.extend(batch)
    off += 50
exts = exts[:N]
print("extensions", len(exts), flush=True)

manifests = {}
for e in exts:
    eid = f"{e['namespace']}.{e['name']}"
    f = DL / "manifests" / (eid + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.is_file():
        try:
            meta = get(f"https://open-vsx.org/api/{e['namespace']}/{e['name']}")
            url = (meta.get("files") or {}).get("manifest")
            man = get(url) if url else {}
            man["_downloadCount"] = meta.get("downloadCount") or e.get("downloadCount")
            man["_download"] = (meta.get("files") or {}).get("download")
            f.write_text(json.dumps(man), "utf-8")
        except Exception as ex:  # noqa: BLE001
            print("manifest fail", eid, ex, flush=True)
            continue
    manifests[eid] = json.loads(f.read_text("utf-8"))
print("manifests", len(manifests), flush=True)

# bundles: the extensions with code (main/browser) - top M whose .vsix is not huge
bundles = {}
count = 0
for eid, man in manifests.items():
    if count >= M:
        break
    if not (man.get("main") or man.get("browser")) or not man.get("_download"):
        continue
    vf = DL / "vsix" / (eid + ".vsix")
    vf.parent.mkdir(parents=True, exist_ok=True)
    if not vf.is_file():
        try:
            req = urllib.request.Request(man["_download"], headers=UA, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as r:
                size = int(r.headers.get("Content-Length") or 0)
            if size > CAP:
                print("skip big", eid, size, flush=True)
                continue
            vf.write_bytes(get(man["_download"], binary=True, timeout=300))
        except Exception as ex:  # noqa: BLE001
            print("vsix fail", eid, ex, flush=True)
            continue
    count += 1
    bundles[eid] = vf
print("bundles", len(bundles), flush=True)

CMD_RE = re.compile(r"executeCommand\(\s*['\"`]([\w.:\-/$]+)['\"`]")
SETCTX_RE = re.compile(r"executeCommand\(\s*['\"`]setContext['\"`]\s*,\s*['\"`]([\w.:\-/]+)['\"`]")
API_RE = re.compile(r"\.(window|workspace|commands|languages|env|debug|tasks|extensions|scm|comments|authentication|l10n|tests|notebooks|chat|lm)\.([A-Za-z_]\w*)")
NEW_RE = re.compile(r"new \w{1,4}\.([A-Z]\w+)\(")

cmd_use, cmd_ext = Counter(), {}
api_use = Counter()
api_ext = Counter()
cls_ext = Counter()
setctx = Counter()
for eid, vf in bundles.items():
    seen_cmd, seen_api, seen_cls = set(), set(), set()
    try:
        z = zipfile.ZipFile(vf)
    except Exception:  # noqa: BLE001
        continue
    for n in z.namelist():
        if not n.startswith("extension/") or not n.endswith(".js") or "/node_modules/" in n and "vscode-languageclient" not in n:
            continue
        if "/webview" in n.lower() or "/media/" in n:
            continue
        info = z.getinfo(n)
        if info.file_size > 40 * 1024 * 1024:
            continue
        try:
            text = z.read(n).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        for m in CMD_RE.finditer(text):
            seen_cmd.add(m.group(1))
        for m in SETCTX_RE.finditer(text):
            setctx[m.group(1)] += 1
        for m in API_RE.finditer(text):
            seen_api.add(m.group(1) + "." + m.group(2))
        for m in NEW_RE.finditer(text):
            seen_cls.add(m.group(1))
    for c in seen_cmd:
        cmd_use[c] += 1
        cmd_ext.setdefault(c, []).append(eid)
    for a in seen_api:
        api_ext[a] += 1
    for c in seen_cls:
        cls_ext[c] += 1

# package.json: contribution points, menus, when-clause context keys, keybinding commands, view container locations
contrib_use = Counter()
menu_use = Counter()
vc_loc = Counter()
when_keys = Counter()
kb_cmds = Counter()
activation = Counter()
engines = Counter()
WORD = re.compile(r"(?<![\w.'\"/-])([A-Za-z_][\w.:-]*)(?=\s*(?:==|!=|=~|&&|\|\||\)|$|\s|<|>|in\b))")


def keys_of(when):
    out = set()
    if not isinstance(when, str):
        return out
    s = re.sub(r"'[^']*'|\"[^\"]*\"|/(?:\\.|[^/])+/[a-z]*", " ", when)
    s = re.sub(r"(==|!=|<=|>=|<|>)\s*[\w.:\-]+", " ", s)
    for tok in re.findall(r"!?\s*([A-Za-z_][\w.:\-]*)", s):
        if tok in ("true", "false", "in", "not"):
            continue
        out.add("config.*" if tok.startswith("config.") else tok)
    return out


for eid, man in manifests.items():
    c = man.get("contributes") or {}
    for k in c:
        contrib_use[k] += 1
    for loc in (c.get("viewsContainers") or {}):
        vc_loc[loc] += 1
    for mid, items in (c.get("menus") or {}).items():
        menu_use[mid] += 1
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                for k in keys_of(it.get("when")):
                    when_keys[k] += 1
    for kb in c.get("keybindings") or [] if isinstance(c.get("keybindings"), list) else []:
        if isinstance(kb, dict):
            for k in keys_of(kb.get("when")):
                when_keys[k] += 1
            cmd = kb.get("command")
            if isinstance(cmd, str) and not any(isinstance(x, dict) and x.get("command") == cmd for x in c.get("commands") or []):
                kb_cmds[cmd] += 1
    for loc, views in (c.get("views") or {}).items():
        for v in views if isinstance(views, list) else []:
            if isinstance(v, dict):
                for k in keys_of(v.get("when")):
                    when_keys[k] += 1
    for cm in c.get("commands") or [] if isinstance(c.get("commands"), list) else []:
        if isinstance(cm, dict):
            for k in keys_of(cm.get("enablement")):
                when_keys[k] += 1
    for a in man.get("activationEvents") or []:
        activation[str(a).split(":")[0]] += 1
    engines[str((man.get("engines") or {}).get("vscode"))] += 1

OUT.write_text(json.dumps({
    "extensions": list(manifests), "bundles": list(bundles),
    "commands": cmd_use.most_common(), "commandUsers": cmd_ext, "setContextKeys": setctx.most_common(200),
    "api": api_ext.most_common(), "classes": cls_ext.most_common(),
    "contributes": contrib_use.most_common(), "menus": menu_use.most_common(), "viewsContainers": vc_loc.most_common(),
    "whenKeys": when_keys.most_common(), "keybindingCommands": kb_cmds.most_common(), "activationEvents": activation.most_common(),
    "engines": engines.most_common(),
}, indent=1), "utf-8")
print("done", flush=True)
