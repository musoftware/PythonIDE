"""radide/extension_points.py and the ratchet on replacing MainWindow's methods (no window, a few seconds).

Unit: providers are asked latest registered first; can_open / open_document / save_documents /
has_modified_documents that raise are logged and never stop the others; a failed save makes Save All
report False; an object without the four methods is refused at registration; solution contributors run in
registration order and a failing one is logged.

Ratchet: features must not replace MainWindow's methods (``win.save_all = wrapper``) any more - they register
with win.extension_points. Every such assignment in radide/ is counted per method; the count may only go
down. After a migration lowers it, write the new numbers with ``--update`` (the test prints them).

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_extension_points.py [--update]
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
BASELINE = Path(__file__).with_name("window_patches_baseline.json")

from radide.extension_points import ExtensionPoints  # noqa: E402

results: list[tuple[str, bool]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


# ------------------------------------------------------------------ unit
class Prov:
    def __init__(self, name, exts, calls, fail=""):
        self.name, self.exts, self.calls, self.fail = name, exts, calls, fail
        self.modified = False

    def _maybe(self, what):
        self.calls.append(f"{self.name}.{what}")
        if self.fail == what:
            raise RuntimeError(f"{self.name} {what} broke")

    def can_open(self, path):
        self._maybe("can_open")
        return Path(path).suffix in self.exts

    def open_document(self, path):
        self._maybe("open_document")
        return f"{self.name}:{Path(path).name}"

    def save_documents(self):
        self._maybe("save_documents")
        return False if self.fail == "save_false" else None

    def has_modified_documents(self):
        self._maybe("has_modified_documents")
        return self.modified


logged: list[str] = []
calls: list[str] = []
ep = ExtensionPoints(logged.append)
a, b = Prov("a", {".x", ".y"}, calls), Prov("b", {".y"}, calls)
ep.add_document_provider(a)
ep.add_document_provider(b)
ep.add_document_provider(a)
ok("a provider registered twice is kept once", ep.document_providers() == [b, a])
ok("the latest registered provider is asked first", ep.open_document(Path("f.y")) == (True, "b:f.y"))
ok("a file of the earlier provider only", ep.open_document(Path("f.x")) == (True, "a:f.x"))
ok("nobody's file -> (False, None)", ep.open_document(Path("f.z")) == (False, None))
ok("nothing modified", ep.any_modified() is False)
a.modified = True
ok("one provider modified -> any_modified", ep.any_modified() is True)
ok("Save All of every provider succeeds", ep.save_documents() is True and logged == [])

calls.clear()
c = Prov("c", {".x"}, calls, fail="can_open")
ep.add_document_provider(c)
ok("can_open that raises: logged, the next provider opens the file",
   ep.open_document(Path("f.x")) == (True, "a:f.x") and any("Prov.can_open" in m for m in logged), logged)
ep.remove_document_provider(c)
logged.clear()
d = Prov("d", {".x"}, calls, fail="open_document")
ep.add_document_provider(d)
ok("open_document that raises: logged, (True, None) - not opened in another editor",
   ep.open_document(Path("f.x")) == (True, None) and any("open_document" in m for m in logged), logged)
ep.remove_document_provider(d)
logged.clear()
e = Prov("e", set(), calls, fail="save_documents")
ep.add_document_provider(e)
calls.clear()
ok("save_documents that raises: logged, the others still save, result False",
   ep.save_documents() is False and "a.save_documents" in calls and any("save_documents" in m for m in logged))
ep.remove_document_provider(e)
f = Prov("f", set(), calls, fail="save_false")
ep.add_document_provider(f)
ok("a provider whose save failed (False) -> Save All False", ep.save_documents() is False)
ep.remove_document_provider(f)
logged.clear()
g = Prov("g", set(), calls, fail="has_modified_documents")
ep.add_document_provider(g)
ok("has_modified_documents that raises: logged, the others still answer",
   ep.any_modified() is True and any("has_modified_documents" in m for m in logged))
ep.remove_document_provider(g)
try:
    ep.add_document_provider(object())
    ok("an object without the four methods is refused", False)
except TypeError as ex:
    ok("an object without the four methods is refused", "can_open" in str(ex), ex)

from radide.extension_points import BINARY_VIEWER, FALLBACK  # noqa: E402
pe = ExtensionPoints(logged.append)
hexv = Prov("hex", {".cur", ".bin", ".nes"}, [])
rom = Prov("rom", {".nes", ".bin"}, [])
icon = Prov("icon", {".cur"}, [])
tform = Prov("tform", {".bin"}, [])
pe.add_document_provider(icon)
pe.add_document_provider(hexv, FALLBACK)          # registered after the editors, still asked last
pe.add_document_provider(rom, BINARY_VIEWER)
pe.add_document_provider(tform)
ok("priority: editors first (latest first), then binary viewers, then the fallback",
   pe.document_providers() == [tform, icon, rom, hexv], [p.name for p in pe.document_providers()])
ok("priority: a file's editor beats the hex fallback registered later (.cur -> icon)",
   pe.open_document(Path("a.cur")) == (True, "icon:a.cur"))
ok("priority: the ROM viewer beats the hex fallback (.nes -> rom)", pe.open_document(Path("g.nes")) == (True, "rom:g.nes"))
ok("priority: an editor beats the ROM viewer (.bin art -> tform)", pe.open_document(Path("x.bin")) == (True, "tform:x.bin"))
pe.remove_document_provider(tform)
ok("remove_document_provider with priorities", pe.open_document(Path("x.bin")) == (True, "rom:x.bin"))

order: list[str] = []
logged.clear()
ep.add_solution_contributor(lambda: order.append("first"), "first")
ep.add_solution_contributor(lambda: 1 / 0, "broken")
ep.add_solution_contributor(lambda: order.append("third"), "third")
ep.fill_solution()
ok("solution contributors run in registration order, a failing one is logged",
   order == ["first", "third"] and any("[broken]" in m for m in logged), (order, logged))


# ------------------------------------------------------------------ ratchet
def main_window_methods() -> set[str]:
    tree = ast.parse((ROOT / "radide" / "app.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    names = {n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return names | {"closeEvent", "restoreState", "showEvent"}      # Qt methods the features wrap too


def _is_win(node) -> bool:
    return (isinstance(node, ast.Name) and node.id == "win") or \
        (isinstance(node, ast.Attribute) and node.attr == "win" and isinstance(node.value, ast.Name)
         and node.value.id == "self")


def count_patches(methods: set[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for p in sorted((ROOT / "radide").rglob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, ast.AnnAssign) else []
            for t in targets:
                if isinstance(t, ast.Attribute) and t.attr in methods and _is_win(t.value):
                    found.setdefault(t.attr, []).append(f"{p.relative_to(ROOT).as_posix()}:{n.lineno}")
    return found


found = count_patches(main_window_methods())
now = {k: len(v) for k, v in sorted(found.items())}
total = sum(now.values())
if "--update" in sys.argv:
    BASELINE.write_text(json.dumps(now, indent=1) + "\n", encoding="utf-8")
    print(f"baseline written: {total} replacements of MainWindow methods")
base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.is_file() else {}
grown = {k: (base.get(k, 0), v) for k, v in now.items() if v > base.get(k, 0)}
ok("no new replacement of a MainWindow method (register with win.extension_points instead)", not grown,
   "; ".join(f"{k}: {o} -> {n} ({', '.join(found[k])})" for k, (o, n) in grown.items()))
shrunk = {k: (v, now.get(k, 0)) for k, v in base.items() if now.get(k, 0) < v}
if shrunk:
    print("NOTE fewer replacements than the baseline - lower it with --update: " +
          ", ".join(f"{k} {o}->{n}" for k, (o, n) in shrunk.items()))
print(f"MainWindow method replacements left: {total} (baseline {sum(base.values())})")

fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
sys.exit(fails)
