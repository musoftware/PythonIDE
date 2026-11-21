"""Names defined outside the analysed file: included files, the other assembly files of the project, the
8086 emulator's built-in emu8086.inc and the known Win32 / C runtime functions (no Qt).

Uses radide/asm_intel/index.py (project_files / parse_file / resolve_include, cached by mtime); the result of
one project folder is kept for a few seconds so typing in a big project does not walk the folder each time.
"""
from __future__ import annotations

import time
from pathlib import Path

from ..asm_intel import apis
from ..asm_intel.index import parse, parse_file, project_files, resolve_include

KNOWN_FUNCS = {n.lower() for n in apis.APIS} | {
    "printf", "scanf", "puts", "putchar", "getchar", "exit", "_exit", "malloc", "free", "strlen", "strcpy",
    "memcpy", "memset", "fflush", "gets", "fgets", "sprintf", "atoi", "abort", "__main", "_printf", "_scanf",
    "_puts", "_exit", "__imp_exitprocess",
}
NORETURN = {"exitprocess", "exit", "_exit", "abort", "exitthread", "fatalappexita", "fatalappexit", "_cexit_never",
            "__imp_exitprocess", "__imp__exitprocess@4", "_exitprocess@4", "longjmp", "terminateprocess_self",
            "__stack_chk_fail", "_exitprocess"}

_CACHE: dict[str, tuple[float, "ProjectSymbols"]] = {}
TTL = 4.0


class ProjectSymbols:
    def __init__(self, path, includes: list[tuple[str, int]], dialect: str, case: bool):
        self.case = case
        self.include_names: set[str] = set()      # defined in included files (visible without extern)
        self.include_macros: set[str] = set()
        self.other_names: dict[str, str] = {}     # defined in other project files -> file name
        self.unresolved: list[str] = []
        self.dialect = dialect
        p = Path(str(path)) if path else None
        for name, _line in includes:
            low = name.lower().replace("\\", "/").split("/")[-1]
            f = resolve_include(name, p) if p is not None else None
            if f is None and low in ("emu8086.inc", "rad8086.inc"):
                try:
                    from ..emu8086.includes import builtin_include
                    text = builtin_include(low) or ""
                except Exception:  # noqa: BLE001
                    text = ""
                if text:
                    self._add_module(parse(text, "masm"), self.include_names)
                    continue
            if f is None:
                self.unresolved.append(name)
                continue
            r = parse_file(f, dialect if f.suffix.lower() != ".s" else None)
            if r is None:
                self.unresolved.append(name)
                continue
            self._add_module(r[0], self.include_names)
            for sub, _l in r[0].includes[:20]:
                g = resolve_include(sub, f)
                rr = parse_file(g, dialect) if g is not None else None
                if rr is not None:
                    self._add_module(rr[0], self.include_names)
                elif not sub.lower().endswith(("emu8086.inc",)):
                    self.unresolved.append(sub)
        if p is not None:
            try:
                me = p.resolve()
            except OSError:
                me = p
            for f in project_files(p)[:200]:
                try:
                    if f.resolve() == me:
                        continue
                except OSError:
                    continue
                r = parse_file(f, dialect if f.suffix.lower() not in (".s",) else None)
                if r is None:
                    continue
                names: set[str] = set()
                self._add_module(r[0], names)
                for n in names:
                    self.other_names.setdefault(n, f.name)

    def _add_module(self, mod, target: set) -> None:
        for s in mod.symbols:
            if s.kind in ("label", "proc", "data", "const", "extern", "macro", "local", "struct"):
                target.add(s.name if self.case else s.name.lower())
                if s.kind == "macro":
                    self.include_macros.add(s.name.lower())
        for n in list(mod.globals) + list(mod.externs):
            target.add(n if self.case else n.lower())

    def key(self, name: str) -> str:
        return name if self.case else name.lower()

    def included(self, name: str) -> bool:
        return self.key(name) in self.include_names

    def other_file(self, name: str) -> str:
        return self.other_names.get(self.key(name), "")


def project_symbols(path, includes, dialect: str, case: bool) -> ProjectSymbols:
    key = f"{path}|{dialect}|{case}|{sorted(n for n, _ in includes)}"
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < TTL:
        return hit[1]
    ps = ProjectSymbols(path, includes, dialect, case)
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[key] = (now, ps)
    return ps


def known_function(name: str) -> bool:
    n = name.strip("[]").lower()
    return n in KNOWN_FUNCS or apis.lookup(name) is not None


def is_noreturn(name: str) -> bool:
    n = name.strip("[]").lower()
    n2 = n.replace("__imp_", "").replace("_imp__", "").lstrip("_").split("@")[0]
    return n in NORETURN or n2 in NORETURN
