"""Static facts about the IDE's user-facing entry points, read from the source (no Qt):

* dialog_classes()   every QDialog / QWizard / QMessageBox subclass in radide/ (module, class, title literal)
* action_slots()     clean action text -> [(module, function names)] from calls such as
                     ``menu.addAction("Build Solution", self.build_solution)``, ``self._act("&Run", self.run)``,
                     ``QAction("Text", ...)`` + ``.triggered.connect(fn)``, ``Action("id", "Title", fn)``,
                     ``register_command("id", "Title", fn)`` (lambdas: the functions they call)
Used by tools/feature_inventory.py (inventory.json) and tools/test_matrix.py (which tests call those functions).
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "radide"
DIALOG_BASES = {"QDialog", "QWizard", "QMessageBox", "QInputDialog", "QFileDialog", "QProgressDialog",
                "QColorDialog", "QFontDialog"}
SKIP_PARTS = {"__pycache__", "reference", "third_party", "node_modules", "ring_samples"}


def clean(text: str) -> str:
    text = (text or "").split("\t", 1)[0]
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&").replace("...", "").strip()


def _py_files():
    for p in sorted(PKG.rglob("*.py")):
        if SKIP_PARTS & set(p.parts):
            continue
        yield p


def _parse(p: Path):
    try:
        return ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def _mod(p: Path) -> str:
    return ".".join(p.relative_to(ROOT).with_suffix("").parts)


def _base_name(b) -> str:
    if isinstance(b, ast.Name):
        return b.id
    if isinstance(b, ast.Attribute):
        return b.attr
    return ""


def dialog_classes() -> list[dict]:
    """QDialog subclasses, also indirect ones (a class deriving from another dialog class of radide)."""
    classes: dict[str, dict] = {}
    bases: dict[str, list[str]] = {}
    for p in _py_files():
        tree = _parse(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            key = f"{_mod(p)}.{node.name}"
            bases[key] = [_base_name(b) for b in node.bases]
            title = ""
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "setWindowTitle" and sub.args):
                    a = sub.args[0]
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        title = a.value
                        break
                    if isinstance(a, ast.JoinedStr):
                        title = "".join(v.value for v in a.values if isinstance(v, ast.Constant))
                        break
            classes[key] = {"module": _mod(p), "class": node.name, "title": title, "line": node.lineno,
                            "bases": bases[key]}
    names = {k.rsplit(".", 1)[1]: k for k in classes}
    dialog: set[str] = set()
    changed = True
    while changed:
        changed = False
        for k, bs in bases.items():
            if k in dialog:
                continue
            if any(b in DIALOG_BASES or (b in names and names[b] in dialog) for b in bs):
                dialog.add(k)
                changed = True
    return [classes[k] for k in sorted(dialog)]


def _called_names(node) -> list[str]:
    """Function names a slot expression refers to: self.build -> build; lambda: self.x(1) -> x."""
    out = []
    if isinstance(node, ast.Attribute):
        out.append(node.attr)
    elif isinstance(node, ast.Name):
        out.append(node.id)
    elif isinstance(node, ast.Lambda):
        for sub in ast.walk(node.body):
            if isinstance(sub, ast.Call):
                f = sub.func
                if isinstance(f, ast.Attribute):
                    out.append(f.attr)
                elif isinstance(f, ast.Name):
                    out.append(f.id)
    elif isinstance(node, ast.Call):            # functools.partial(fn, ...)
        for a in node.args[:1]:
            out += _called_names(a)
    return [n for n in out if n not in ("emit", "trigger", "show", "raise_", "setCurrentIndex", "get", "print",
                                         "str", "len", "Path", "setFocus", "self", "win", "isEnabled")]


def _str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


ACTION_FUNCS = {"addAction", "_act", "act", "A", "add", "QAction", "_a", "action", "make_action", "_action",
                "add_action", "menu_action", "_add_action", "item"}


def action_slots() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}

    def put(text, names, p, line):
        t = clean(text)
        if not t or not names:
            return
        out.setdefault(t, []).append({"module": _mod(p), "functions": sorted(set(names)), "line": line})

    for p in _py_files():
        tree = _parse(p)
        if tree is None:
            continue
        # QAction variables: a = QAction("Text", ...); a.triggered.connect(fn)
        var_text: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                f = node.value.func
                fname = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if fname in ACTION_FUNCS and node.value.args:
                    t = _str(node.value.args[0])
                    if t is not None:
                        for tg in node.targets:
                            if isinstance(tg, ast.Name):
                                var_text[tg.id] = t
                            elif isinstance(tg, ast.Attribute):
                                var_text[tg.attr] = t
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            args = node.args
            if fname in ACTION_FUNCS and len(args) >= 2:
                # addAction("Text", slot) / addAction(icon, "Text", slot)
                if _str(args[0]) is not None:
                    put(args[0].value, _called_names(args[1]), p, node.lineno)
                elif len(args) >= 3 and _str(args[1]) is not None:
                    put(args[1].value, _called_names(args[2]), p, node.lineno)
            elif fname in ("Action", "register_command", "Command") and len(args) >= 3 and _str(args[1]) is not None:
                put(args[1].value, _called_names(args[2]), p, node.lineno)
            elif fname == "connect" and args and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) and f.value.attr == "triggered":
                holder = f.value.value
                hname = holder.id if isinstance(holder, ast.Name) else holder.attr if isinstance(
                    holder, ast.Attribute) else ""
                if hname in var_text:
                    put(var_text[hname], _called_names(args[0]), p, node.lineno)
            for kw in node.keywords:            # addAction("Text", triggered=fn) / Action(..., run=fn)
                if kw.arg in ("triggered", "run", "callback", "slot") and args and _str(args[0]) is not None:
                    put(args[0].value, _called_names(kw.value), p, node.lineno)
    return out


if __name__ == "__main__":
    d = dialog_classes()
    s = action_slots()
    print(len(d), "dialog classes;", len(s), "action texts with slots")
