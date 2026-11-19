"""IntelliSense data for Ring: RingQt classes/methods parsed from the Ring
installation's *.cf class definitions, and Ring's built-in functions.
The index is cached in %LOCALAPPDATA%/RADIDE/ringqt_index.json."""
from __future__ import annotations

import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

RX_CLASS = re.compile(r"^\s*name:\s*(\w+)", re.I)
RX_PARENT = re.compile(r"^\s*parent:\s*(\w+)", re.I)
RX_METHOD = re.compile(r"^\s*([A-Za-z_][\w:<>\s\*&]*?)[\s\*&]+(\w+)\s*\(([^)]*)\)\s*;?\s*$")
SKIP_BLOCKS = ("<comment>", "<code>", "<runcode>", "<funcstart>", "<cdef>")
TAGS = ("<register>", "</register>", "<class>", "</class>")
INDEX_VERSION = "2"

# common Ring functions that are written in Ring (not C) - with signatures
RING_FUNCS = {
    "see": "see <expression>", "give": "give <variable>", "len": "len(string|list) -> number",
    "add": "add(list, item)", "del": "del(list, index)", "find": "find(list, value [, column]) -> index",
    "sort": "sort(list [, column]) -> list", "reverse": "reverse(list) -> list",
    "substr": "substr(string, substring | start, count | old, new)", "lower": "lower(string)",
    "upper": "upper(string)", "trim": "trim(string)", "left": "left(string, count)",
    "right": "right(string, count)", "number": "number(string) -> number", "string": "string(number) -> string",
    "isstring": "isstring(value)", "isnumber": "isnumber(value)", "islist": "islist(value)",
    "isobject": "isobject(value)", "isnull": "isnull(value)", "type": "type(value) -> string",
    "copy": "copy(string, count)", "random": "random(max) -> number", "clock": "clock() -> number",
    "time": "time() -> string", "date": "date() -> string", "sqrt": "sqrt(number)",
    "pow": "pow(x, y)", "floor": "floor(number)", "ceil": "ceil(number)", "fabs": "fabs(number)",
    "str2list": "str2list(string) -> list", "list2str": "list2str(list) -> string",
    "raise": "raise(message)", "eval": "eval(code)", "char": "char(ascii)", "ascii": "ascii(char)",
    "read": "read(filename) -> string", "write": "write(filename, string)", "fexists": "fexists(filename)",
    "sysget": "sysget(name)", "system": "system(command)", "sleep": "sleep(seconds)",
    "messagebox": "msginfo(title, text)",
}


def ring_root() -> Path | None:
    for c in (os.environ.get("RING_HOME", ""), r"C:\ring\ring", r"C:\ring"):
        if c and (Path(c) / "extensions" / "ringqt" / "classes").exists():
            return Path(c)
    return None


def _cache_file() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE"
    base.mkdir(parents=True, exist_ok=True)
    return base / "ringqt_index.json"


def _parse_cf(path: Path, classes: dict) -> None:
    current = None
    skipping = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        low = line.lower()
        if skipping:
            if low == skipping.replace("<", "</"):
                skipping = None
            continue
        if low in SKIP_BLOCKS:
            skipping = low
            continue
        if low in ("<register>", "</register>"):
            continue
        if low == "<class>":
            current = {"name": "", "parent": "", "methods": {}}
            continue
        if low == "</class>":
            if current and current["name"]:
                classes[current["name"].lower()] = current
            continue
        if current is None:
            continue
        m = RX_CLASS.match(line)
        if m and not current["name"]:
            current["name"] = m.group(1)
            continue
        m = RX_PARENT.match(line)
        if m:
            current["parent"] = m.group(1)
            continue
        m = RX_METHOD.match(line)
        if m and not line.startswith(("#", "//", "if", "RING_")):
            ret, name, args = m.group(1).strip(), m.group(2), m.group(3).strip()
            current["methods"].setdefault(name, f"{name}({'' if args == 'void' else args}) -> {ret}")


def _builtin_functions(root: Path) -> list[str]:
    exe = root / "bin" / "ring.exe"
    if not exe.exists():
        return []
    tmp = _cache_file().with_name("_funcs.ring")
    tmp.write_text("for f in ringvm_cfunctionslist() see f + nl next\n", encoding="utf-8")
    try:
        out = subprocess.run([str(exe), str(tmp)], capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return []
    return [f.strip() for f in out.splitlines() if f.strip() and not f.startswith(("qt_", "ring_"))]


@lru_cache(maxsize=1)
def load_index() -> dict:
    root = ring_root()
    if root is None:
        return {"classes": {}, "functions": []}
    cf_dir = root / "extensions" / "ringqt" / "classes"
    stamp = INDEX_VERSION + ":" + str(int(max((p.stat().st_mtime for p in cf_dir.rglob("*.cf")), default=0)))
    cache = _cache_file()
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if data.get("stamp") == stamp:
                return data
        except Exception:  # noqa: BLE001
            pass
    classes: dict = {}
    for cf in cf_dir.rglob("*.cf"):
        _parse_cf(cf, classes)
    data = {"stamp": stamp, "classes": classes, "functions": _builtin_functions(root)}
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def class_methods(cls: str) -> dict[str, str]:
    """All methods of a RingQt class including inherited ones: name -> signature."""
    classes = load_index()["classes"]
    out: dict[str, str] = {}
    seen = set()
    c = classes.get(cls.lower())
    while c is not None and c["name"].lower() not in seen:
        seen.add(c["name"].lower())
        for name, sig in c["methods"].items():
            out.setdefault(name, sig)
        c = classes.get((c.get("parent") or "").lower())
    return out


def class_names() -> list[str]:
    return ["q" + c["name"][1:] if c["name"].startswith("Q") else c["name"]
            for c in load_index()["classes"].values()]
