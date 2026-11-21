"""Editor support for AGC assembly (yaYUL syntax): Monarch highlighting, IntelliSense, hover, Go to Definition
and Find All References across every .agc file of a program, and an outline by log section.

A flight program such as Comanche055 is ~90 files ("log sections", one per file) pulled together by MAIN.agc
with ``$FILE.agc`` lines; a symbol defined in ERASABLE_ASSIGNMENTS.agc is used everywhere. ``SymbolIndex``
indexes a folder once (and again when a file changes) so F12 jumps across those files.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from . import isa
from .assembler import split_line

WORD_RE = r"[A-Za-z0-9_.*/=,&$\-]+"
PAGE_RE = re.compile(r"^\s*##?\s*Page\s+(\d+)", re.I)


def _lang() -> str:
    try:
        from ..i18n import language
        return language()
    except Exception:  # noqa: BLE001
        return "en"


# ============================================================================ index
class SymbolIndex:
    """name -> (path, 0-based line, kind, detail) for every label of the .agc files in a folder."""

    def __init__(self):
        self._files: dict[str, tuple[float, list]] = {}
        self._folder: Path | None = None

    def _scan_file(self, path: Path, text: str | None = None) -> list:
        out = []
        if text is None:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return out
        for i, raw in enumerate(text.splitlines()):
            label, op, operand = split_line(raw)
            if not label:
                continue
            opu = op.upper()
            if opu in ("ERASE",):
                kind = "variable"
            elif opu in ("EQUALS", "=", "EBANK=", "SBANK="):
                kind = "constant"
            elif opu in ("OCT", "DEC", "2DEC", "DEC*", "2DEC*", "CADR", "FCADR", "ECADR", "GENADR", "ADRES",
                         "2CADR", "2FCADR", "BBCON", "REMADR", "MM", "VN"):
                kind = "constant"
            else:
                kind = "function"
            detail = (op + " " + operand).strip()[:60]
            out.append((label, i, kind, detail))
        return out

    def files(self, folder: Path) -> list[Path]:
        try:
            return sorted(p for p in Path(folder).glob("*.agc") if p.is_file())
        except OSError:
            return []

    def refresh(self, folder: Path, current: Path | None = None, current_text: str | None = None) -> None:
        folder = Path(folder)
        if self._folder != folder:
            self._files = {}
            self._folder = folder
        seen = set()
        for p in self.files(folder)[:400]:
            key = str(p)
            seen.add(key)
            if current is not None and current_text is not None and p.resolve() == Path(current).resolve():
                self._files[key] = (-1.0, self._scan_file(p, current_text))
                continue
            try:
                mt = os.path.getmtime(p)
            except OSError:
                continue
            old = self._files.get(key)
            if old is None or old[0] != mt:
                self._files[key] = (mt, self._scan_file(p))
        for k in list(self._files):
            if k not in seen:
                del self._files[k]

    def lookup(self, name: str):
        for path, (_mt, syms) in self._files.items():
            for label, line, kind, detail in syms:
                if label == name:
                    return path, line, kind, detail
        return None

    def all(self):
        for path, (_mt, syms) in self._files.items():
            for label, line, kind, detail in syms:
                yield label, path, line, kind, detail


INDEX = SymbolIndex()


def _word_at(line: str, col: int) -> str:
    for m in re.finditer(WORD_RE, line):
        if m.start() <= col <= m.end():
            return m.group(0)
    return ""


def _index_for(path, code: str | None = None) -> SymbolIndex:
    if path:
        p = Path(str(path))
        INDEX.refresh(p.parent, p, code)
    return INDEX


# ============================================================================ features
def completions(code: str, line: int, col: int, path=None) -> list:
    from ..languages.base import Completion
    out = []
    lines = code.splitlines()
    cur = lines[line][:col] if line < len(lines) else ""
    in_operand = bool(re.match(r"^(\S+)?\s+\S+\s+", cur))
    if not in_operand:
        for name in sorted(isa.all_opcodes()):
            out.append(Completion(name, "keyword", isa.INSTRUCTION_DOCS.get(name, ("", ""))[0][:70]))
        for name in sorted(isa.PSEUDO_DOCS):
            out.append(Completion(name, "keyword", isa.PSEUDO_DOCS[name][0][:70]))
        for name in sorted(isa.INTERPRETIVE_DOCS):
            out.append(Completion(name, "function", "interpretive: " + isa.INTERPRETIVE_DOCS[name][0][:60]))
    for name, addr in isa.REGISTERS.items():
        out.append(Completion(name, "variable", f"register {addr:o}"))
    seen = {c.name for c in out}
    idx = _index_for(path, code)
    for label, p, ln, kind, detail in idx.all():
        if label not in seen:
            seen.add(label)
            out.append(Completion(label, kind, f"{detail}  ({Path(p).name}:{ln + 1})"))
    for i, raw in enumerate(lines):                    # the current text (not saved yet)
        label = split_line(raw)[0]
        if label and label not in seen:
            seen.add(label)
            out.append(Completion(label, "variable", f"line {i + 1}"))
    return out


def _vn_hover(word: str, ar: bool) -> str:
    m = re.fullmatch(r"V(\d\d)(?:N(\d\d))?", word.upper())
    if m:
        v = int(m.group(1))
        text = isa.VERBS.get(v)
        out = f"**Verb {v:02d}**: " + (text[1] if (text and ar) else text[0] if text else "?")
        if m.group(2):
            n = int(m.group(2))
            t2 = isa.NOUNS.get(n)
            out += f"  \n**Noun {n:02d}**: " + (t2[1] if (t2 and ar) else t2[0] if t2 else "?")
        return out
    m = re.fullmatch(r"N(\d\d)", word.upper())
    if m and int(m.group(1)) in isa.NOUNS:
        t = isa.NOUNS[int(m.group(1))]
        return f"**Noun {m.group(1)}**: " + (t[1] if ar else t[0])
    m = re.fullmatch(r"P(\d\d)", word.upper())
    if m and int(m.group(1)) in isa.PROGRAMS:
        t = isa.PROGRAMS[int(m.group(1))]
        return f"**{t[0].split(' - ')[0]}**: " + (t[1] if ar else t[0])
    return ""


def hover(code: str, line: int, col: int, path=None) -> str:
    lines = code.splitlines()
    if line >= len(lines):
        return ""
    word = _word_at(lines[line], col)
    if not word:
        return ""
    ar = _lang() == "ar"
    doc = isa.doc_for(word)
    if doc is not None and (word.upper() in isa.REGISTER_DOCS or word.upper() == word):
        en, arabic = doc
        return f"**{word.upper()}**  \n{en}" + (f"  \n{arabic}" if ar else "")
    m = re.fullmatch(r"\$(\S+)", word)
    if m:
        return f"**Include** {m.group(1)} - the log section is assembled here."
    vn = _vn_hover(word, ar)
    comment_part = lines[line].split("#", 1)
    if vn and len(comment_part) > 1 and col >= len(comment_part[0]):
        return vn
    hit = _index_for(path, code).lookup(word)
    if hit is not None:
        p, ln, kind, detail = hit
        return f"**{word}** ({kind}) - {Path(p).name}:{ln + 1}  \n`{detail}`"
    if word.upper() in isa.REGISTERS:
        return f"**{word.upper()}** - register {isa.REGISTERS[word.upper()]:o} (octal)"
    if word.isdigit() and lines[line].split()[:1] and re.search(r"\b(READ|WRITE|RAND|WAND|ROR|WOR|RXOR)\b",
                                                                lines[line].upper()):
        ch = int(word, 8) if all(c in "01234567" for c in word) else int(word)
        if ch in isa.CHANNEL_DOCS:
            en, arabic = isa.CHANNEL_DOCS[ch]
            return f"**Channel {ch:o}**  \n{en}" + (f"  \n{arabic}" if ar else "")
    return vn


def definition(code: str, line: int, col: int, path=None):
    lines = code.splitlines()
    if line >= len(lines):
        return None
    raw = lines[line]
    if raw.strip().startswith("$") and path:
        name = raw.strip()[1:].split("#", 1)[0].strip()
        target = Path(str(path)).parent / name
        if target.exists():
            return (str(target), 0)
    word = _word_at(raw, col)
    if not word:
        return None
    for i, r in enumerate(lines):                      # this file first (unsaved text)
        if split_line(r)[0] == word:
            return (str(path), i) if path else None
    hit = _index_for(path, code).lookup(word)
    if hit is not None:
        return (hit[0], hit[1])
    return None


def references(code: str, line: int, col: int, path=None):
    lines = code.splitlines()
    if line >= len(lines):
        return None
    word = _word_at(lines[line], col)
    if not word:
        return None
    rx = re.compile(r"(?<![A-Za-z0-9_.*/=,&$\-])" + re.escape(word) + r"(?![A-Za-z0-9_.*/=,&$\-])")
    out = []
    files = INDEX.files(Path(str(path)).parent) if path else []
    for f in files[:400]:
        try:
            text = code if path and f.resolve() == Path(str(path)).resolve() else \
                f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, raw in enumerate(text.splitlines()):
            body = raw.split("#", 1)[0]
            for m in rx.finditer(body):
                out.append((str(f), i, m.start()))
    return out


def document_symbols(code: str) -> list[dict]:
    """Outline: "## Page n" sections (the scanned listing pages) or log sections ($includes), labels inside."""
    out: list[dict] = []
    section = None
    for i, raw in enumerate(code.splitlines()):
        m = PAGE_RE.match(raw)
        if m:
            section = {"name": f"Page {m.group(1)}", "kind": "module", "line": i, "detail": "", "children": []}
            out.append(section)
            continue
        s = raw.strip()
        if s.startswith("$"):
            name = s[1:].split("#", 1)[0].strip()
            out.append({"name": Path(name).stem.replace("_", " "), "kind": "module", "line": i,
                        "detail": "log section", "children": []})
            continue
        label, op, operand = split_line(raw)
        if label:
            kind = "variable" if op.upper() == "ERASE" else "constant" if op.upper() in (
                "EQUALS", "=", "OCT", "DEC", "2DEC") else "function"
            item = {"name": label, "kind": kind, "line": i, "detail": (op + " " + operand).strip()[:50],
                    "children": []}
            (section["children"] if section is not None else out).append(item)
    return out


def folding_ranges(code: str) -> list[tuple[int, int]]:
    """Page sections fold."""
    starts = [i for i, raw in enumerate(code.splitlines()) if PAGE_RE.match(raw)]
    n = len(code.splitlines())
    return [(a, (starts[k + 1] - 1 if k + 1 < len(starts) else n - 1)) for k, a in enumerate(starts)
            if (starts[k + 1] - 1 if k + 1 < len(starts) else n - 1) > a]


def monaco_language() -> dict:
    """The Monarch grammar for .agc files (registered with radRegisterMonarch, radide/web/editor.html)."""
    opcodes = sorted(isa.all_opcodes())
    pseudo = sorted(isa.PSEUDO_OPS)
    interp = sorted(isa.INTERPRETIVE)
    tokenizer = {
        "root": [
            [r"##.*$", "comment.doc"],                       # annotations of the transcribed listings
            [r"#.*$", "comment"],
            [r"^\s*\$\S+", "string"],                        # $INCLUDE.agc
            [r"^[^\s#]+", "tag"],                            # label in column 1
            [r"[+-]?\d+(\.\d+)?([EeBb][+-]?\d+)?[Dd]?\b", "number"],
            [r"[A-Za-z0-9_.*/=,&\-]+", {"cases": {"@opcodes": "keyword", "@pseudo": "type",
                                                  "@interp": "keyword.flow", "@registers": "variable.predefined",
                                                  "@default": "identifier"}}],
        ],
    }
    monarch = {"defaultToken": "", "tokenPostfix": ".agc", "ignoreCase": False, "opcodes": opcodes,
               "pseudo": pseudo, "interp": interp, "registers": sorted(isa.REGISTERS), "tokenizer": tokenizer}
    conf = {"comments": {"lineComment": "#"}, "brackets": [], "autoClosingPairs": [],
            "wordPattern": r"(-?\d*\.\d\w*)|(" + WORD_RE + ")"}
    folding = {"pairs": [], "section": r"^\s*##?\s*Page\s+\d+", "label": r"^[^\s#]+", "lineComment": ["#"]}
    return {"id": "rad-agc", "aliases": ["AGC assembly (yaYUL)", "agc"], "extensions": [".agc"],
            "monarch": monarch, "conf": conf, "folding": folding, "triggers": []}


__all__ = ["INDEX", "SymbolIndex", "completions", "definition", "document_symbols", "folding_ranges", "hover",
           "monaco_language", "references"]
