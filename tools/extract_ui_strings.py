"""Extract the IDE's user-interface strings for translation (radide/i18n).

Scans radide/**/*.py with the ast module and collects the English text passed to
UI calls: QAction / QLabel / QPushButton / QCheckBox / QRadioButton / QGroupBox /
QDockWidget / QMenu constructors, addAction / addMenu / setText / setWindowTitle /
setTitle / setToolTip / setStatusTip / setPlaceholderText / addTab / insertTab /
setTabText / addRow / setHeaderLabels / QMessageBox.* / QInputDialog.* and
_section(...) / tr(...).

  * plain literals             -> "strings"   (exact text, with & mnemonics removed)
  * f-strings / "..".format()  -> "patterns"  (each placeholder becomes {})

Output: radide/i18n/strings_en.json   {"strings": {text: "file:line"}, "patterns": {...}}
Then:   python tools/extract_ui_strings.py --missing ar
        lists texts that radide/i18n/ar.json does not translate yet.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "radide"
OUT = SRC / "i18n" / "strings_en.json"

# method name -> indexes of the string arguments that are user-visible
METHODS = {
    "addAction": (0, 1), "addMenu": (0, 1), "setText": (0,), "setWindowTitle": (0,), "setTitle": (0,),
    "setToolTip": (0,), "setStatusTip": (0,), "setPlaceholderText": (0,), "setWhatsThis": (0,),
    "addTab": (1, 2), "insertTab": (2, 3), "setTabText": (1,), "setTabToolTip": (1,), "addRow": (0,),
    "setHeaderLabels": (0,), "setHorizontalHeaderLabels": (0,), "setVerticalHeaderLabels": (0,),
    "addSection": (0,), "setIconText": (0,), "setLabelText": (0,), "setInformativeText": (0,),
    "setWindowIconText": (0,), "showMessage": (0,), "addButton": (0,), "setButtonText": (1,),
    "information": (1, 2), "warning": (1, 2), "critical": (1, 2), "question": (1, 2), "about": (1, 2),
    "getText": (1, 2), "getItem": (1, 2), "getInt": (1, 2), "getDouble": (1, 2), "getMultiLineText": (1, 2),
    "getOpenFileName": (1,), "getSaveFileName": (1,), "getExistingDirectory": (1,), "getOpenFileNames": (1,),
    "_section": (0,), "tr": (0,), "section": (0,), "_btn": (0,), "_button": (0,), "_label": (0,),
    # the IDE's own helpers (MainWindow._act / _dock, small widget factories)
    "A": (0,), "_act": (0,), "act": (0,), "_dock": (0,), "dock": (0,), "_tool": (0,), "tool": (0,),
    "_check": (0,), "check": (0,), "label": (0,), "section_label": (0,), "_title": (0,), "_item": (0,),
    "add_page": (1,), "addItem": (), "setHeaderLabel": (0,), "QListWidgetItem": (0,),
}
CLASSES = {"QAction": (0, 1), "QLabel": (0,), "QPushButton": (0, 1), "QCheckBox": (0,), "QRadioButton": (0,),
           "QGroupBox": (0,), "QDockWidget": (0,), "QMenu": (0,), "QToolButton": (), "QCommandLinkButton": (0, 1),
           "QMessageBox": (1, 2), "QTreeWidgetItem": (0,)}
KEYWORDS = {"text", "toolTip", "placeholderText", "windowTitle", "title", "statusTip"}

_WORDY = re.compile(r"[A-Za-z]{2,}")


def _clean(s: str) -> str:
    return s


def _const_str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _const_str(node.left), _const_str(node.right)
        if a is not None and b is not None:
            return a + b
    return None


def _pattern(node) -> str | None:
    """f"Open {name}" -> "Open {}" ; "Open {}".format(x) -> "Open {}"."""
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                out.append(str(v.value).replace("{", "{{").replace("}", "}}"))
            else:
                out.append("{}")
        return "".join(out)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"):
        base = _const_str(node.func.value)
        if base is not None:
            return re.sub(r"\{[^{}]*\}", "{}", base)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _pattern(node.left) or _lit_or_hole(node.left), _pattern(node.right) or _lit_or_hole(node.right)
        if a is not None and b is not None and "{}" in a + b:
            return a + b
    return None


def _lit_or_hole(node) -> str | None:
    s = _const_str(node)
    if s is not None:
        return s.replace("{", "{{").replace("}", "}}")
    if isinstance(node, (ast.Name, ast.Attribute, ast.Call, ast.Subscript)):
        return "{}"
    return None


def _visible(s: str) -> bool:
    t = s.replace("&", "").strip()
    if not t or not _WORDY.search(t):
        return False
    if t.startswith(("http://", "https://", "file:")) or re.fullmatch(r"[\w.\-/\\]+\.\w{1,5}", t):
        return False
    if re.fullmatch(r"[A-Z0-9_]+", t) and len(t) > 1 and "_" in t:    # CONSTANT_NAMES
        return False
    if re.fullmatch(r"[a-z_][a-z0-9_]*", t) and "_" in t:              # identifiers
        return False
    if t.startswith(("Q", "#")) and "{" in t and ":" in t:             # style sheets
        return False
    return True


def _norm(s: str) -> str:
    """Remove the & mnemonic (but keep '&&' as a literal '&') and a trailing '\\tShortcut'."""
    s = s.split("\t")[0]
    return re.sub(r"&(?!&)", "", s).replace("&&", "&")


def scan() -> tuple[dict, dict]:
    strings: dict[str, str] = {}
    patterns: dict[str, str] = {}

    def add(node, where):
        s = _const_str(node)
        if s is not None:
            if _visible(s):
                strings.setdefault(_norm(s), where)
            return
        p = _pattern(node)
        if p is not None and _visible(p.replace("{}", "")):
            patterns.setdefault(_norm(p), where)
            return
        if isinstance(node, (ast.List, ast.Tuple)):
            for e in node.elts:
                add(e, where)
        if isinstance(node, ast.IfExp):
            add(node.body, where)
            add(node.orelse, where)

    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts or "runtimes" in path.parts and "clients" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            where = f"{rel}:{node.lineno}"
            name = node.func.attr if isinstance(node.func, ast.Attribute) else (
                node.func.id if isinstance(node.func, ast.Name) else "")
            idx = METHODS.get(name) or CLASSES.get(name) or ()
            for i in idx:
                if i < len(node.args):
                    add(node.args[i], where)
            if name in METHODS or name in CLASSES:
                for kw in node.keywords:
                    if kw.arg in KEYWORDS:
                        add(kw.value, where)
    return dict(sorted(strings.items(), key=lambda kv: kv[0].lower())), \
        dict(sorted(patterns.items(), key=lambda kv: kv[0].lower()))


def main(argv: list[str]) -> int:
    strings, patterns = scan()
    if "--missing" in argv:
        lang = argv[argv.index("--missing") + 1]
        cat = json.loads((SRC / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        miss_s = [s for s in strings if s not in cat.get("strings", {})]
        miss_p = [p for p in patterns if p not in cat.get("patterns", {})]
        json.dump({"strings": miss_s, "patterns": miss_p}, sys.stdout, ensure_ascii=False, indent=1)
        print(f"\n{len(miss_s)} strings and {len(miss_p)} patterns are not translated to '{lang}'.",
              file=sys.stderr)
        return 0
    OUT.write_text(json.dumps({"strings": strings, "patterns": patterns}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"{len(strings)} strings, {len(patterns)} patterns -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
