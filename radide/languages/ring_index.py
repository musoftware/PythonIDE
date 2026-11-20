"""Ring language index for IntelliSense (no Qt here: also usable from tools and tests).

Everything the editor knows about Ring comes from the Ring installation itself
(``C:\\ring\\ring`` or ``RING_HOME``), so it matches the installed version:

* keywords                - ``language/include/scanner.h``
* core C functions        - ``RING_API_REGISTER("name", ...)`` in ``language/src/*.c``
* extension C functions   - ``extensions/*/*.cf`` prototypes (RingLibCurl, RingRayLib, RingAllegro, RingLibSDL,
                            RingOpenGL, RingFreeGLUT, RingLibUI, RingLibUV, RingTilengine, RingStbImage, RingZip,
                            RingPostgreSQL, RingThreads, RingCJSON, RingPDFGen, ...) and the registered names of the
                            hand-written ones (RingSQLite, RingMySQL, RingODBC, RingOpenSSL, RingInternet,
                            RingWinAPI, RingSockets, RingMurmurHash, RingWinCReg, ...)
* Ring-code libraries     - every ``libraries/*`` and ``extensions/*`` ``.ring`` / ``.rh`` file: functions, classes,
                            methods, attributes and constants with their file and line (Go to Definition)
* RingQt                  - classes/methods of ``guilib/classes/ring_qt.ring`` + the C++ signatures of
                            ``radide/ringqt_index.py`` (the ``.cf`` class definitions)
* documentation           - ``documents/build/html/_sources/*.txt``: the "Syntax:" lines (signature + result),
                            the section text (description) and the page#anchor used by F1

The result is cached in ``%LOCALAPPDATA%/RADIDE/ring_index.json`` (rebuilt when the installation changes).
``parse_source`` (the Ring parser used for the user's own files too) lives here as well.
"""
from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

INDEX_VERSION = "ring-index-5"

# ============================================================================ installation
FALLBACK_KEYWORDS = """again and but bye call case catch class def do done else elseif end endclass endfor
    endfunc endfunction endif endpackage endswitch endtry endwhile exit for foreach from func function get give
    if import in load loop new next not off ok on or other package private put return see step switch to try
    while break continue self this super changeringkeyword changeringoperator loadsyntax enablehashcomments
    disablehashcomments""".split()
CONSTANT_WORDS = ["true", "false", "nl", "null", "tab", "cr", "sysargv", "ccatcherror", "ringoptionalfunctions"]
_INTERNAL_KEYWORDS = {"bracestart", "braceexpreval", "braceerror", "bracenewline", "braceend", "ringvm_see",
                      "ringvm_give", "ringvm_errorhandler", "main", "init", "operator"}


def ring_home() -> Path | None:
    """The Ring installation folder (the one with bin/ring.exe, libraries, extensions, documents)."""
    cands = [os.environ.get("RING_HOME", ""), os.environ.get("RING", ""), r"C:\ring\ring", r"C:\ring"]
    for c in cands:
        if not c:
            continue
        p = Path(c)
        for root in (p, p / "ring"):
            if (root / "bin").is_dir() and ((root / "libraries").is_dir() or (root / "language").is_dir()):
                return root
    import shutil
    exe = shutil.which("ring")
    if exe:
        root = Path(exe).resolve().parent.parent
        if (root / "libraries").is_dir():
            return root
    return None


def docs_dir(home: Path | None = None) -> Path | None:
    home = home or ring_home()
    if home is None:
        return None
    for d in (home / "documents" / "build" / "html", home / "docs" / "build" / "html", home / "documents" / "html"):
        if (d / "index.html").is_file():
            return d
    return None


def ring_version(home: Path | None = None) -> str:
    home = home or ring_home()
    if home is not None:
        try:
            t = (home / "language" / "include" / "state.h").read_text(encoding="utf-8", errors="replace")
            m = re.search(r'RING_STATE_VERSION\s+"([\d.]+)"', t)
            if m:
                return m.group(1)
        except OSError:
            pass
    return "1.24"


def _cache_file() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE"
    base.mkdir(parents=True, exist_ok=True)
    return base / "ring_index.json"


# ============================================================================ Ring source parser
@dataclass
class Sym:
    name: str
    kind: str                       # function | class | method | attribute | variable | parameter | constant | package
    line: int                       # 0-based
    col: int = 0
    end: int = -1                   # last line of a function / class (0-based)
    params: list = field(default_factory=list)
    parent: str = ""                # class of a method / attribute, base class of a class
    doc: str = ""
    rhs: str = ""                   # variables: the assigned expression (type inference)
    private: bool = False


@dataclass
class Scope:
    func: Sym
    cls: str                        # "" for a top-level function
    locals: dict = field(default_factory=dict)       # lname -> Sym (parameters too)


@dataclass
class Module:
    funcs: dict = field(default_factory=dict)        # lname -> Sym
    classes: dict = field(default_factory=dict)      # lname -> Sym (kind class) with .methods / .attrs below
    methods: dict = field(default_factory=dict)      # lclass -> {lname: Sym}
    attrs: dict = field(default_factory=dict)        # lclass -> {lname: Sym}
    globals: dict = field(default_factory=dict)      # lname -> Sym
    loads: list = field(default_factory=list)        # (file name, line, col)
    scopes: list = field(default_factory=list)       # Scope, in source order
    packages: list = field(default_factory=list)     # Sym
    braces: list = field(default_factory=list)       # (line, col, expr) of "expr {" object-access blocks

    def scope_at(self, line: int) -> Scope | None:
        for s in self.scopes:
            if s.func.line <= line <= s.func.end:
                return s
        return None

    def class_at(self, line: int) -> str:
        """The class whose body contains *line* ("" outside classes)."""
        best = ""
        for c in self.classes.values():
            if c.line <= line <= c.end:
                best = c.name
        return best


def mask(text: str) -> str:
    """*text* with comments and string contents replaced by spaces (newlines and quotes kept), so that
    positions stay the same and code can be scanned with regular expressions."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "#" or (ch == "/" and text.startswith("//", i)):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif ch == "/" and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif ch in "\"'`":
            j = text.find(ch, i + 1)
            j = n - 1 if j < 0 else j
            for k in range(i + 1, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


RX_FUNC = re.compile(r"^(?:func|def|function)\s+([A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)\s*(?:\((.*?)\)|(.*))$", re.I)
RX_CLASS = re.compile(r"^class\s+([A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)(?:\s*(?:from|:|<)\s*([\w.]+))?", re.I)
RX_PACKAGE = re.compile(r"^package\s+([\w.]+)", re.I)
RX_LOAD = re.compile(r"""^\s*load\s+(?:package\s+)?(["'`])(.+?)\1""", re.I)
RX_ASSIGN = re.compile(r"^([A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)\s*(?:[-+*/%|&^]|<<|>>)?=(?!=)\s*(.*)$")
RX_NEW = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*new\s+([\w.]+)", re.I)
RX_FOR = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s*(?:=|\bin\b)", re.I)
RX_BRACE = re.compile(r"([A-Za-z_][\w.]*(?:\(\))?)\s*\{")
RX_NEWBRACE = re.compile(r"\bnew\s+([\w.]+)\s*(?:\([^()]*\))?\s*\{", re.I)
_KW = set(FALLBACK_KEYWORDS) | set(CONSTANT_WORDS)


def _comment_doc(orig: list[str], masked: list[str], line: int) -> str:
    """The comment lines just above a definition (or the first comment line of its body)."""
    block: list[str] = []
    i = line - 1
    while i >= 0 and not masked[i].strip() and orig[i].strip():
        s = orig[i].strip()
        if s.startswith(("#", "//")):
            block.insert(0, s.lstrip("#/").strip())
        elif s.startswith(("/*", "*")):
            block.insert(0, s.strip("/* ").strip())
        else:
            break
        i -= 1
    if not block:
        for j in range(line + 1, min(line + 3, len(orig))):
            s = orig[j].strip()
            if s.startswith(("#", "//")) and not masked[j].strip():
                block.append(s.lstrip("#/").strip())
                break
            if s:
                break
    return " ".join(b for b in block if b and not set(b) <= set("=-*#~"))[:400]


def _split_params(text: str) -> list[str]:
    out = []
    for p in (text or "").split(","):
        p = p.strip()
        m = re.match(r"^([A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)", p)
        if m:
            out.append(m.group(1))
    return out


def parse_source(text: str) -> Module:
    """Parse Ring code: functions, classes (methods, attributes), globals, locals per function, loads."""
    mod = Module()
    masked = mask(text)
    mlines = masked.split("\n")
    olines = text.split("\n")
    cur_class: Sym | None = None
    cur_func: Scope | None = None
    in_private = False
    last_def: Sym | None = None          # function / class whose end is still open
    for i, mline in enumerate(mlines):
        s = mline.strip()
        if not s:
            continue
        indent = len(mline) - len(mline.lstrip())
        low = s.lower()
        word = re.match(r"\w*", low).group()
        m = RX_FUNC.match(s) if word in ("func", "def", "function") else None
        if m:
            name = m.group(1)
            params = _split_params(m.group(2) if m.group(2) is not None else m.group(3))
            if last_def is not None and last_def.end < 0:
                last_def.end = i - 1
            if cur_func is not None and cur_func.func.end < 0:
                cur_func.func.end = i - 1
            doc = _comment_doc(olines, mlines, i)
            if cur_class is not None:
                sym = Sym(name, "method", i, 0, params=params,
                          parent=cur_class.name, doc=doc, private=in_private)
                mod.methods.setdefault(cur_class.name.lower(), {}).setdefault(name.lower(), sym)
            else:
                sym = Sym(name, "function", i, 0, params=params, doc=doc)
                mod.funcs.setdefault(name.lower(), sym)
            sym.col = olines[i].lower().find(name.lower(), indent)
            sc = Scope(sym, cur_class.name if cur_class is not None else "")
            for p in params:
                sc.locals[p.lower()] = Sym(p, "parameter", i, olines[i].lower().find(p.lower(), sym.col + len(name)))
            mod.scopes.append(sc)
            cur_func = sc
            last_def = sym
            continue
        m = RX_CLASS.match(s) if word == "class" else None
        if m:
            if cur_func is not None and cur_func.func.end < 0:
                cur_func.func.end = i - 1
            if cur_class is not None and cur_class.end < 0:
                cur_class.end = i - 1
            if last_def is not None and last_def.end < 0:
                last_def.end = i - 1
            name = m.group(1)
            sym = Sym(name, "class", i, olines[i].lower().find(name.lower()), parent=(m.group(2) or "").split(".")[-1],
                      doc=_comment_doc(olines, mlines, i))
            mod.classes.setdefault(name.lower(), sym)
            mod.methods.setdefault(name.lower(), {})
            mod.attrs.setdefault(name.lower(), {})
            cur_class, cur_func, in_private, last_def = sym, None, False, sym
            continue
        if word in ("endclass", "endpackage") or (word == "package" and RX_PACKAGE.match(s)):
            if cur_func is not None and cur_func.func.end < 0:
                cur_func.func.end = i - 1
            if cur_class is not None and cur_class.end < 0:
                cur_class.end = i
            cur_class, cur_func, in_private = None, None, False
            if word == "package":
                pm = RX_PACKAGE.match(s)
                mod.packages.append(Sym(pm.group(1), "package", i, indent))
            continue
        if word in ("endfunc", "endfunction"):
            if cur_func is not None:
                cur_func.func.end = i
            cur_func = None
            continue
        if word == "private" and cur_class is not None and low == "private":
            in_private = True
            continue
        if word == "load":
            lm = RX_LOAD.match(olines[i])
            if lm:
                mod.loads.append((lm.group(2), i, olines[i].find(lm.group(2))))
            continue
        # ---------------------------------------------------------------- variables
        target: dict
        kind = "variable"
        if cur_func is not None:
            target = cur_func.locals
        elif cur_class is not None:
            target = mod.attrs.setdefault(cur_class.name.lower(), {})
            kind = "attribute"
        else:
            target = mod.globals
        am = RX_ASSIGN.match(s)
        if am and am.group(1).lower() not in _KW:
            name = am.group(1)
            rhs = olines[i][indent + am.start(2):indent + am.end(2)].strip() if i < len(olines) else am.group(2)
            target.setdefault(name.lower(), Sym(name, kind, i, indent, rhs=rhs,
                                                parent=cur_class.name if kind == "attribute" else "",
                                                private=in_private and kind == "attribute"))
            if cur_func is None and cur_class is None and name.isupper():
                target[name.lower()].kind = "constant"
            # more statements on the line:  x = 0  y = 0   (Ring needs no separator between statements)
            first = True
            for xm in re.finditer(r"(?<=[\w\)\]\"'`])\s+([A-Za-z_]\w*)\s*=(?![=>])\s*(\S[^=]*?)(?=\s+[A-Za-z_]\w*\s*=(?![=>])|$)",
                                  s[am.end(1):]):
                xn = xm.group(1)
                base = indent + am.end(1)
                if first:                        # the first statement's value ends where the next one starts
                    first = False
                    sym0 = target.get(name.lower())
                    if sym0 is not None and sym0.line == i:
                        sym0.rhs = olines[i][indent + am.start(2):base + xm.start()].strip()
                if xn.lower() in _KW or xn.lower() in target:
                    continue
                target[xn.lower()] = Sym(xn, kind, i, base + xm.start(1),
                                         rhs=olines[i][base + xm.start(2):base + xm.end(2)].strip(),
                                         parent=cur_class.name if kind == "attribute" else "",
                                         private=in_private and kind == "attribute")
        elif cur_func is None and cur_class is not None and re.fullmatch(r"[A-Za-z_]\w*(\s+[A-Za-z_]\w*)*", s):
            for wm in re.finditer(r"[A-Za-z_]\w*", s):        # attribute declarations:  x y z
                if wm.group().lower() not in _KW:
                    target.setdefault(wm.group().lower(), Sym(wm.group(), "attribute", i, indent + wm.start(),
                                                              parent=cur_class.name, private=in_private))
        # a second statement on the line:  x = new Foo  y = new Bar
        for nm in RX_NEW.finditer(s):
            if nm.group(1).lower() not in target and nm.group(1).lower() not in _KW:
                target[nm.group(1).lower()] = Sym(nm.group(1), kind, i, indent + nm.start(),
                                                  rhs="new " + nm.group(2), parent=cur_class.name if kind == "attribute" else "")
        for fm in RX_FOR.finditer(s):
            if fm.group(1).lower() not in target:
                target[fm.group(1).lower()] = Sym(fm.group(1), kind, i, indent + fm.start(1))
        for bm in RX_BRACE.finditer(s):
            mod.braces.append((i, indent + bm.end(), bm.group(1)))
        for bm in RX_NEWBRACE.finditer(s):
            mod.braces.append((i, indent + bm.end(), "new " + bm.group(1)))
    n = len(mlines) - 1
    if cur_func is not None and cur_func.func.end < 0:
        cur_func.func.end = n
    if cur_class is not None and cur_class.end < 0:
        cur_class.end = n
    if last_def is not None and last_def.end < 0:
        last_def.end = n
    for c in mod.classes.values():
        if c.end < 0:
            c.end = n
    for sc in mod.scopes:
        if sc.func.end < 0:
            sc.func.end = n
    return mod


# ============================================================================ index building
_SKIP_DIRS = {"samples", "sample", "tests", "test", "examples", "example", "apps", "applications", "android",
              "webassembly", "microcontroller", "tutorial", "ringqt6", "ringhttplib32", "codegen", "libdepwin",
              "build", "tools", "converter", "docs", "cpptest", "binupdate", "events", "qml", "wasm"}
_SKIP_FILES = {"ring_qt_light.ring", "ring_qt_core.ring", "test.ring", "gendoc.ring"}
_C_FILE_MAX = 3_000_000
RX_REGISTER = re.compile(r'RING_API_REGISTER\w*\s*\(\s*"(\w+)"')
RX_PROTO = re.compile(r"^\s*([A-Za-z_][\w\s\*&:<>,]*?[\s\*&])\s*(\w+)\s*\(([^()]*)\)\s*;?\s*$")
RX_SECTION_UL = re.compile(r"^(=+|-+|~+|\^+|\*+)\s*$")
RX_SYNTAX = re.compile(r"^\s*([A-Za-z_]\w*)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*(?:-+>\s*(.*))?$")
RX_DOC_PROTO = re.compile(r"^\*\s+``(.+?)``\s*$")
RX_DOC_CONST = re.compile(r"^\*\s+``([A-Z][A-Z0-9_]+)``\s*$")


def _slug(title: str) -> str:
    """docutils make_id: the HTML anchor of a section title."""
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return re.sub(r"^[^a-z]+", "", s)


def _load_closure(home: Path) -> dict[str, list[str]]:
    """bin/load/<name>.ring -> every library file (lower-case absolute path) it loads, recursively."""
    out: dict[str, list[str]] = {}
    load_dir = home / "bin" / "load"
    if not load_dir.is_dir():
        return out

    def resolve(name: str, base: Path) -> Path | None:
        name = name.replace("\\", "/")
        cands = [base / name.lstrip("/"), (base / name.lstrip("/")).resolve()]
        if name.startswith("/"):
            cands.insert(0, Path(str(base) + name))
        cands.append(load_dir / name)
        for c in cands:
            try:
                if c.is_file():
                    return c.resolve()
            except OSError:
                continue
        return None

    for lf in sorted(load_dir.glob("*.ring")):
        seen: list[str] = []
        stack = [lf.resolve()]
        while stack and len(seen) < 400:
            f = stack.pop()
            key = str(f).lower()
            if key in seen:
                continue
            seen.append(key)
            try:
                t = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"""(?im)^\s*load\s+(?:package\s+)?["'](.+?)["']""", t):
                r = resolve(m.group(1), f.parent)
                if r is not None:
                    stack.append(r)
            for m in re.finditer(r"""(?i)loadlib(?:file)?\s*\(\s*["'](.+?)["']""", t):
                seen.append("dll:" + m.group(1).lower())
        out[lf.name.lower()] = seen
    return out


def _docs_index(dd: Path) -> tuple[dict, dict, dict]:
    """(functions, constants, topics) from the Sphinx sources: name -> info."""
    funcs: dict[str, dict] = {}
    consts: dict[str, dict] = {}
    topics: dict[str, str] = {}                     # lower word -> "page.html#anchor" (classes, sections)
    src = dd / "_sources"
    if not src.is_dir():
        return funcs, consts, topics
    for f in sorted(src.glob("*.txt")):
        page = f.stem + ".html"
        if f.stem.startswith("whatisnew"):
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        funcsdoc = "funcsdoc" in f.stem or f.stem in ("qtclassesdoc",)
        title, anchor, para, page_title = "", "", "", ""
        syntax_next = False
        in_code = False
        code_indent = 0
        lang_functions = False
        for i, raw in enumerate(lines):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            st = raw.strip()
            if st and RX_SECTION_UL.match(nxt) and len(nxt.strip()) >= len(st) - 1 and not RX_SECTION_UL.match(st) \
                    and not raw.startswith((" ", "\t")):
                title, anchor, para = st, _slug(st), ""
                page_title = page_title or st
                lang_functions = f.stem == "reference" and st.lower() == "language functions"
                in_code = syntax_next = False
                m = re.match(r"^(\w+)(?:\(\))?\s+(class|function|functions|command|statement|keyword)s?$", st, re.I)
                if m:
                    topics.setdefault(m.group(1).lower(), f"{page}#{anchor}")
                continue
            if RX_SECTION_UL.match(st) and st:
                continue
            if st.startswith(".. code-block::") or st == "::":
                in_code, code_indent = True, -1
                continue
            if in_code:
                if not st:
                    continue
                ind = len(raw) - len(raw.lstrip())
                if code_indent < 0:
                    code_indent = ind
                if ind == 0:
                    in_code = False
                else:
                    if syntax_next or lang_functions:
                        m = RX_SYNTAX.match(raw)
                        if m and m.group(1).lower() not in _KW_SKIP:
                            name = m.group(1)
                            sig = f"{name}({m.group(2).strip()})" + (f" ---> {m.group(3).strip()}" if m.group(3) else "")
                            e = funcs.setdefault(name.lower(), {"n": name, "s": [], "d": "", "u": f"{page}#{anchor}"})
                            if sig not in e["s"] and len(e["s"]) < 8:
                                e["s"].append(sig)
                            if not lang_functions and e["u"].startswith("reference.html"):
                                e["u"], e["d"] = f"{page}#{anchor}", ""      # the chapter beats the summary list
                            if not e["d"] and para and not lang_functions:
                                e["d"] = para
                    continue
            if st.lower().rstrip(":") == "syntax":
                syntax_next = True
                continue
            if st.lower().startswith(("example", "output")):
                syntax_next = False
            if funcsdoc:
                m = RX_DOC_CONST.match(st)
                if m:
                    consts.setdefault(m.group(1).lower(), {"n": m.group(1), "u": f"{page}#{anchor}",
                                                           "lib": page_title})
                    continue
                m = RX_DOC_PROTO.match(st)
                if m and f.stem != "qtclassesdoc":
                    pm = RX_PROTO.match(m.group(1))
                    if pm:
                        name = pm.group(2)
                        ret = re.sub(r"\s+", " ", pm.group(1)).strip()
                        args = "" if pm.group(3).strip() == "void" else re.sub(r"\s+", " ", pm.group(3).strip())
                        e = funcs.setdefault(name.lower(), {"n": name, "s": [], "d": "", "u": f"{page}#{anchor}"})
                        sig = f"{name}({args}) -> {ret}"
                        if sig not in e["s"] and len(e["s"]) < 8:
                            e["s"].append(sig)
                        if not e.get("lib"):
                            e["lib"] = page_title.replace(" Functions Reference", "")
                    continue
                m = re.match(r"^(\w+) Class$", title)
                if m and f.stem == "qtclassesdoc":
                    topics.setdefault(m.group(1).lower(), f"{page}#{anchor}")
            if st and not st.startswith((".. ", ":", "*", "|")) and not raw.startswith((" ", "\t")) and len(para) < 300:
                if not para:
                    para = st
                elif not para.endswith((".", ":")):
                    para += " " + st
    return funcs, consts, topics


_KW_SKIP = {"if", "for", "while", "see", "give", "return", "func", "def", "class", "new", "load", "switch", "try"}


def _parse_cf(path: Path) -> tuple[dict, dict, set]:
    """C functions (non-class prototypes), constants and class names of an extension .cf file."""
    funcs: dict[str, dict] = {}
    consts: dict[str, dict] = {}
    classes: set[str] = set()
    block = ""
    in_class = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return funcs, consts, classes
    for i, raw in enumerate(lines):
        st = raw.strip()
        low = st.lower()
        if block:
            if low == "</" + block + ">":
                block = ""
            elif block == "constant" and re.fullmatch(r"[A-Za-z_]\w*", st):
                consts.setdefault(st.lower(), {"n": st, "f": str(path), "l": i})
            continue
        if low in ("<comment>", "<code>", "<runcode>", "<struct>", "<constant>", "<filter>", "<cdef>", "<funcstart>"):
            block = low[1:-1]
            if block == "funcstart":
                block = ""          # <funcstart>prefix is on one line
            continue
        if low == "<class>":
            in_class = True
            continue
        if low == "</class>":
            in_class = False
            continue
        if in_class:
            m = re.match(r"^name:\s*(\w+)", st, re.I)
            if m:
                classes.add(m.group(1).lower())
            continue
        if not st or st.startswith(("<", "#", "//")):
            continue
        m = RX_PROTO.match(st)
        if m:
            name = m.group(2)
            ret = re.sub(r"\s+", " ", m.group(1)).strip()
            args = "" if m.group(3).strip() == "void" else re.sub(r"\s+", " ", m.group(3).strip())
            funcs.setdefault(name.lower(), {"n": name, "s": [f"{name}({args}) -> {ret}"], "f": str(path), "l": i})
    return funcs, consts, classes


def _iter_lib_files(home: Path):
    for top in ("libraries", "extensions"):
        base = home / top
        if not base.is_dir():
            continue
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d.lower() not in _SKIP_DIRS and not d.startswith("."))
            for fn in sorted(files):
                low = fn.lower()
                if low.endswith((".ring", ".rh", ".cf", ".c", ".cpp")) and low not in _SKIP_FILES:
                    yield Path(dirpath) / fn


def _lib_name(home: Path, path: Path) -> str:
    try:
        rel = path.relative_to(home)
    except ValueError:
        return ""
    parts = rel.parts
    return parts[1] if len(parts) > 2 else (parts[0] if parts else "")


def build_index(home: Path) -> dict:
    from .. import ringqt_index as rq
    data: dict = {"home": str(home), "version": ring_version(home), "keywords": [], "functions": {},
                  "classes": {}, "constants": {}, "topics": {}, "loads": {}, "libs": {}}
    # ---------------------------------------------------------------- keywords
    kws: list[str] = []
    try:
        t = (home / "language" / "include" / "scanner.h").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"RING_KEYWORDS\s*\[\s*\]\s*=\s*\{(.*?)\}", t, re.S) or re.search(r'\{\s*("IF".*?)\}', t, re.S)
        if m:
            kws = [k.lower() for k in re.findall(r'"(\w+)"', m.group(1)) if k.lower() not in _INTERNAL_KEYWORDS]
    except OSError:
        pass
    data["keywords"] = sorted(set(kws or FALLBACK_KEYWORDS) | {"self", "this", "super"} - _INTERNAL_KEYWORDS)
    funcs = data["functions"]
    consts = data["constants"]
    classes = data["classes"]
    # ---------------------------------------------------------------- load files
    closure = _load_closure(home)
    data["loads"] = {k: [x for x in v if not x.startswith("dll:")] for k, v in closure.items()}
    file_to_load: dict[str, str] = {}
    dll_to_load: dict[str, str] = {}
    for lname, files in sorted(closure.items(), key=lambda kv: len(kv[1])):
        for f in files:
            if f.startswith("dll:"):
                dll_to_load.setdefault(f[4:].replace("lib", "", 1) if f[4:].startswith("lib") else f[4:], lname)
            else:
                file_to_load.setdefault(f, lname)

    def load_for(path: Path) -> str:
        return file_to_load.get(str(path.resolve()).lower(), "")

    # ---------------------------------------------------------------- core C functions
    src = home / "language" / "src"
    if src.is_dir():
        for cf in sorted(src.glob("*.c")):
            try:
                t = cf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name in RX_REGISTER.findall(t):
                if name.startswith("ringvm_") and name in ("ringvm_see", "ringvm_give"):
                    continue
                funcs.setdefault(name.lower(), {"n": name, "s": [], "lib": "core", "load": ""})
    for k in ("see", "give"):
        funcs.pop(k, None)
    # ---------------------------------------------------------------- extension / library files
    ext_classes: dict[str, set] = {}
    lib_files = list(_iter_lib_files(home))
    for path in lib_files:
        low = path.name.lower()
        lib = _lib_name(home, path)
        if low.endswith(".cf"):
            if lib.lower() == "ringqt":
                continue                    # RingQt classes come from radide/ringqt_index.py
            fns, cs, cls = _parse_cf(path)
            ext_classes.setdefault(lib, set()).update(cls)
            ldn = _ext_load(path, home, closure)
            for k, v in fns.items():
                if k not in funcs:
                    v.update(lib=lib, load=ldn)
                    funcs[k] = v
            for k, v in cs.items():
                if k not in consts:
                    v.update(lib=lib, load=ldn)
                    consts[k] = v
    for path in lib_files:
        low = path.name.lower()
        if not low.endswith((".c", ".cpp")):
            continue
        lib = _lib_name(home, path)
        if lib.lower() in ("ringqt", "ringopengl") or "ring" not in low:
            continue
        try:
            if path.stat().st_size > _C_FILE_MAX:
                continue
            t = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        prefixes = tuple(c + "_" for c in ext_classes.get(lib, ()))
        ldn = _ext_load(path, home, closure)
        for name in RX_REGISTER.findall(t):
            k = name.lower()
            if k in funcs or (prefixes and k.startswith(prefixes)) or k.startswith(("get_", "new_", "destroy_", "set_")):
                continue
            funcs[k] = {"n": name, "s": [], "lib": lib, "load": ldn}
    # Ring-code files: functions, classes, constants (file + line for Go to Definition)
    for path in lib_files:
        low = path.name.lower()
        if not low.endswith((".ring", ".rh")):
            continue
        try:
            if path.stat().st_size > 2_500_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lib = _lib_name(home, path)
        ldn = load_for(path) or _ext_load(path, home, closure)
        mod = parse_source(text)
        fpath = str(path)
        for k, s in mod.funcs.items():
            if re.search(r"(^test_|_test$|^test\d*$|^main$)", k):
                continue
            e = funcs.get(k)
            sig = f"{s.name}({', '.join(s.params)})"
            if e is None:
                funcs[k] = {"n": s.name, "s": [sig], "d": s.doc, "lib": lib, "load": ldn, "f": fpath, "l": s.line}
            elif "f" not in e or e["f"].lower().endswith(".cf"):
                e.update(f=fpath, l=s.line)          # a Ring wrapper of a C function: go to the Ring code
                if not e.get("d") and s.doc:
                    e["d"] = s.doc
        for k, c in mod.classes.items():
            if k in classes:
                continue
            meths = {mk: {"n": m.name, "s": [f"{m.name}({', '.join(m.params)})"], "d": m.doc, "l": m.line}
                     for mk, m in mod.methods.get(k, {}).items() if not m.private}
            attrs = {ak: {"n": a.name, "l": a.line, "r": a.rhs[:80]}
                     for ak, a in mod.attrs.get(k, {}).items() if not a.private and ak != "pobject"}
            classes[k] = {"n": c.name, "p": c.parent, "d": c.doc, "lib": lib, "load": ldn, "f": fpath, "l": c.line,
                          "m": meths, "a": attrs}
        for k, g in mod.globals.items():
            if (g.kind == "constant" or low.endswith(".rh")) and k not in consts:
                consts[k] = {"n": g.name, "lib": lib, "load": ldn, "f": fpath, "l": g.line}
    # ---------------------------------------------------------------- RingQt C++ signatures
    try:
        qt = rq.load_index().get("classes", {})
    except Exception:  # noqa: BLE001 - RingQt is optional
        qt = {}
    for k, c in qt.items():
        e = classes.setdefault(k, {"n": c["name"], "p": c.get("parent", ""), "d": "", "lib": "ringqt",
                                   "load": "guilib.ring", "m": {}, "a": {}})
        if not e.get("p") and c.get("parent"):
            e["p"] = c["parent"]
        e["qt"] = 1
        for mname, sig in c.get("methods", {}).items():
            me = e["m"].setdefault(mname.lower(), {"n": mname, "s": []})
            me["s"] = [sig]
    # ---------------------------------------------------------------- documentation
    dd = docs_dir(home)
    if dd is not None:
        dfuncs, dconsts, topics = _docs_index(dd)
        data["topics"] = topics
        for k, d in dfuncs.items():
            e = funcs.get(k)
            if e is None:
                if not d["s"]:
                    continue
                e = funcs[k] = {"n": d["n"], "s": [], "lib": d.get("lib", "") or "docs", "load": ""}
            ring_style = [s for s in d["s"] if "--->" in s or " -> " not in s]
            if ring_style or not e.get("s"):
                e["s"] = (ring_style or d["s"]) + [s for s in e.get("s", []) if s not in d["s"]][:2]
            if d.get("d") and not e.get("d"):
                e["d"] = d["d"]
            e["u"] = d["u"]
            if d["n"] != d["n"].lower() and e["n"] == e["n"].lower():
                e["n"] = d["n"]
        for k, d in dconsts.items():
            consts.setdefault(k, {"n": d["n"], "lib": d.get("lib", ""), "load": ""})["u"] = d["u"]
    for k in data["keywords"]:
        funcs.pop(k, None)
    for e in funcs.values():
        if len(e.get("s", [])) > 1:          # documented "name(...) ---> result" lines first
            e["s"] = sorted(e["s"], key=lambda s: "--->" not in s)
        if e.get("lib") == "core":
            e["n"] = e["n"].lower()
    data["libs"] = {lname: lname for lname in closure}
    return data


def _ext_load(path: Path, home: Path, closure: dict) -> str:
    """The bin/load name that brings the extension/library folder of *path*."""
    lib = _lib_name(home, path).lower()
    if not lib:
        return ""
    best = ""
    for lname, files in closure.items():
        for f in files:
            if f.startswith("dll:"):
                continue
            if f"\\{lib}\\" in f or f"/{lib}/" in f:
                if not best or len(closure[lname]) < len(closure[best]):
                    best = lname
                break
    return best


def _stamp(home: Path) -> str:
    parts = [INDEX_VERSION, str(home)]
    for p in [home / "bin" / "ring.exe", home / "bin" / "ring", home / "libraries", home / "extensions",
              home / "documents" / "build" / "html" / "_sources", home / "bin" / "load"]:
        try:
            parts.append(str(int(p.stat().st_mtime)))
        except OSError:
            parts.append("-")
    for base in (home / "libraries", home / "extensions"):
        try:
            parts.append(str(sum(int(d.stat().st_mtime) for d in base.iterdir() if d.is_dir())))
        except OSError:
            pass
    return "|".join(parts)


_LOCK = threading.Lock()
_DATA: dict | None = None
EMPTY = {"home": "", "version": "", "keywords": sorted(FALLBACK_KEYWORDS), "functions": {}, "classes": {},
         "constants": {}, "topics": {}, "loads": {}, "libs": {}}


def load(rebuild: bool = False) -> dict:
    """The index (built on first use, then read from the cache file)."""
    global _DATA
    with _LOCK:
        if _DATA is not None and not rebuild:
            return _DATA
        home = ring_home()
        if home is None:
            _DATA = dict(EMPTY)
            return _DATA
        stamp = _stamp(home)
        cache = _cache_file()
        if cache.exists() and not rebuild:
            try:
                data = json.loads(cache.read_text(encoding="utf-8"))
                if data.get("stamp") == stamp:
                    _DATA = data
                    return data
            except (OSError, ValueError):
                pass
        try:
            data = build_index(home)
        except Exception:  # noqa: BLE001 - never break the editor
            import traceback
            traceback.print_exc()
            data = dict(EMPTY)
        data["stamp"] = stamp
        try:
            tmp = cache.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, cache)
        except OSError:
            pass
        _DATA = data
        return data


def loaded() -> bool:
    return _DATA is not None


def warm_up() -> None:
    """Build / read the index in a background thread (the first completion is then instant)."""
    threading.Thread(target=load, daemon=True, name="ring-index").start()


def doc_url(entry: dict | None) -> str:
    """Absolute local path (or the online manual) of a docs 'page.html#anchor'."""
    if not entry or not entry.get("u"):
        return ""
    dd = docs_dir()
    if dd is not None:
        page, _, anchor = entry["u"].partition("#")
        return str(dd / page) + (f"#{anchor}" if anchor else "")
    return f"https://ring-lang.github.io/doc{ring_version()}/{entry['u']}"


def doc_topic(word: str) -> str:
    """F1: 'page.html#anchor' for a function / class / constant / keyword of the docs, or ''."""
    w = (word or "").lower()
    if not w:
        return ""
    data = load()
    for table in ("functions", "constants"):
        e = data.get(table, {}).get(w)
        if e and e.get("u"):
            return e["u"]
    t = data.get("topics", {}).get(w)
    if t:
        return t
    kw = KEYWORD_DOCS.get(w)
    if kw:
        return kw[1]
    c = data.get("classes", {}).get(w)
    if c and c.get("qt"):
        return data.get("topics", {}).get(w, "")
    return ""


# keyword -> (short description, docs page#anchor)
KEYWORD_DOCS = {
    "see": ("see <expression> - print a value (also: ? <expression> prints it with a new line)", "getting_started.html#hello-world"),
    "give": ("give <variable> - read a line from the keyboard into a variable", "getinput.html#give-command"),
    "load": ('load "file.ring" - use the functions and classes of another source file or library', "programstructure.html#load-command"),
    "func": ("func <name> [params] - define a function (or a method after a class)", "functions.html#define-functions"),
    "def": ("def <name> [params] - define a function (same as func)", "functions.html#define-functions"),
    "function": ("function <name> [params] - define a function (same as func)", "functions.html#define-functions"),
    "class": ("class <Name> [from <Parent>] - define a class; the functions after it are its methods", "oop.html#classes-and-objects"),
    "from": ("class <Name> from <Parent> - inheritance", "oop.html#inheritance"),
    "new": ("new <ClassName>[(args)] - create an object", "oop.html#classes-and-objects"),
    "if": ("if <condition> ... [but|elseif <condition> ...] [else ...] ok", "controlstructures.html#branching"),
    "but": ("but <condition> - else-if branch of an if statement", "controlstructures.html#branching"),
    "elseif": ("elseif <condition> - else-if branch of an if statement", "controlstructures.html#branching"),
    "else": ("else - the last branch of an if / switch", "controlstructures.html#branching"),
    "ok": ("ok - ends an if statement", "controlstructures.html#branching"),
    "for": ("for x = start to end [step n] ... next   /   for x in list ... next", "controlstructures.html#looping"),
    "in": ("for x in <list or string> ... next", "controlstructures.html#for-in-loop"),
    "to": ("for x = start to end ... next", "controlstructures.html#looping"),
    "step": ("for x = start to end step n ... next", "controlstructures.html#using-the-step-option"),
    "next": ("next - ends a for loop", "controlstructures.html#looping"),
    "while": ("while <condition> ... end", "controlstructures.html#looping"),
    "end": ("end - ends a while loop / a do ... again loop", "controlstructures.html#looping"),
    "do": ("do ... again <condition> - loop that runs at least once", "controlstructures.html#do-again-loop"),
    "again": ("do ... again <condition>", "controlstructures.html#do-again-loop"),
    "switch": ("switch <expression> on <value> ... other ... off", "controlstructures.html#branching"),
    "on": ("on <value> - a case of a switch statement", "controlstructures.html#branching"),
    "other": ("other - the default case of a switch statement", "controlstructures.html#branching"),
    "off": ("off - ends a switch statement", "controlstructures.html#branching"),
    "try": ("try ... catch ... done - catch runtime errors (cCatchError holds the message)", "controlstructures.html#exceptions"),
    "catch": ("catch - the error handler of try (cCatchError holds the message)", "controlstructures.html#exceptions"),
    "done": ("done - ends try / catch", "controlstructures.html#exceptions"),
    "return": ("return [value] - leave the function (with a value)", "functions.html#return-value"),
    "exit": ("exit [n] - leave n loops", "controlstructures.html#exit-command"),
    "loop": ("loop [n] - jump to the next iteration of the loop", "controlstructures.html#loop-command"),
    "bye": ("bye - end the program", "controlstructures.html#exit-command"),
    "package": ("package <name> - put the next classes in a package", "oop.html#packages"),
    "import": ("import <package> - use the classes of a package without its name", "oop.html#packages"),
    "private": ("private - the next attributes / methods of the class are private", "oop.html#private-attributes-and-methods"),
    "call": ("call <variable>() - call the function whose name is stored in a variable", "functions.html#call-command"),
    "self": ("self - the current object inside a method", "oop.html#using-self-attribute"),
    "this": ("this - the current object inside a method (also inside braces)", "oop.html#using-this-in-the-class-region"),
    "super": ("super - the parent class (super.method())", "oop.html#inheritance"),
    "nl": ("nl - the new line string", "variables.html"),
    "null": ("null - an empty string / no value", "variables.html"),
    "true": ("true = 1", "variables.html"),
    "false": ("false = 0", "variables.html"),
    "endfunc": ("endfunc - optional end of a function", "functions.html"),
    "endclass": ("endclass - optional end of a class", "oop.html"),
    "endif": ("endif - ends an if statement (same as ok)", "controlstructures.html"),
    "endfor": ("endfor - ends a for loop (same as next)", "controlstructures.html"),
    "endwhile": ("endwhile - ends a while loop (same as end)", "controlstructures.html"),
    "endswitch": ("endswitch - ends a switch (same as off)", "controlstructures.html"),
    "endtry": ("endtry - ends try / catch (same as done)", "controlstructures.html"),
    "break": ("break - leave the loop (same as exit)", "controlstructures.html"),
    "continue": ("continue - next iteration (same as loop)", "controlstructures.html"),
    "foreach": ("foreach x in list ... next", "controlstructures.html#for-in-loop"),
    "get": ("get <variable> - read input (same as give)", "getinput.html"),
    "put": ("put <expression> - print (same as see)", "getting_started.html"),
    "case": ("case <value> - a case of a switch (same as on)", "controlstructures.html"),
}
