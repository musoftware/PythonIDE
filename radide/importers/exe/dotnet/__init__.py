""".NET programs (C# / VB.NET, WinForms) -> RAD IDE project (docs/CONTRACTS.md 10.3).

1. ``ilspycmd`` (the ILSpy command line, a dotnet tool installed into %LOCALAPPDATA%\\RADIDE\\tools)
   decompiles the assembly into a C# project (kept as the import's ``source_dir``).
2. Every WinForms ``Form`` class: ``InitializeComponent`` is read statement by statement and becomes a
   neutral ``.form`` (controls, Location/Size/Text/Font/colours/Anchor/Dock, menus, tool bars, tab pages,
   containers, event wiring).
3. Event handler bodies and the other methods of the form are translated to Python (python-tk) by rules
   for the common WinForms / BCL APIs (MessageBox.Show, Text/Checked/Items..., Convert/Parse, string and
   Math methods, if/for/foreach/while/switch/try).  Lines the rules do not know stay in the code as
   ``# C#: ...`` comments; with ``ai_translate`` the user's AI provider (radide.ai) rewrites the methods
   that still contain such lines.

The C-like parser and the Python emitter are shared with java.py (Swing rules subclass them).
Only for programs you wrote, own, or may legally analyse.

Package layout (one job per module; each imports only the ones above it, so there are no cycles):

    common.py           say, run_tool, download, ai_rewrite, pystr, py_ident, save_json (+ PY_RESERVED)
    cs_lexer.py         Tok, ParseError, tokenize (C# / Java tokens)
    cs_parser.py        Parser: C# (and Java) statements / expressions -> tuple AST (+ keyword tables)
    py_emitter.py       PyEmitter: AST -> Python lines; Untranslatable, cs_format_spec, cs_date_format,
                        COLOR_NAMES, EVENT_MAP, the P_* precedence levels and the other emitter tables
    winforms_reader.py  WinFormsClass, find_classes, class_methods / class_fields, brace matching,
                        parse_winforms (InitializeComponent -> neutral .form) and its value helpers (_lit, ...)
    form_translate.py   translate_form_class (form methods -> target code), set_form_code, set_startup
    ilspy.py            find_ilspycmd, install_ilspycmd, decompile, _bundle_extract (single-file bundles)
    __init__.py         the importer backend (can_handle, run, convert_csharp_tree)

Every name of the former single-file module (public and private, e.g. ``from .dotnet import _lit``) is
re-exported here by the plain imports below, so ``dotnet.<name>`` keeps working for every caller.
"""
from __future__ import annotations

# json ... urllib, find_tool, tools_dir: names of the former single-file module, kept (see __all__)
import json
import keyword
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from ..base import BinaryInfo, ImportResult, ai_translate as _base_ai_translate, find_tool, tools_dir
from .common import PY_RESERVED, ai_rewrite, download, py_ident, pystr, run_tool, save_json, say
from .cs_lexer import _ESC, _NUM, _OPS, ParseError, Tok, _unescape, tokenize
from .cs_parser import ASSIGN_OPS, BINARY_PREC, MODIFIERS, STMT_KEYWORDS, TYPE_KEYWORDS, Parser
from .py_emitter import (COLOR_NAMES, CS_FMT, DEFAULTS, EVENT_MAP, P_ADD, P_AND, P_ATOM, P_BAND, P_BOR, P_BXOR,
                         P_CMP, P_COND, P_MUL, P_NOT, P_OR, P_SHIFT, P_UNARY, PY_OPS, TYPE_KIND, PyEmitter,
                         Untranslatable, cs_date_format, cs_format_spec)
from .winforms_reader import (ALIGN_MAP, APPROX_TYPES, FIELD_RE, IGNORED_TYPES, MENU_ITEM_TYPES, METHOD_RE,
                              WINFORMS_TYPES, WinFormsClass, _color, _depth, _enum_last, _lit, _match_brace,
                              _mnemonic, _qual, _strip_this, brace_matches, class_fields, class_methods,
                              find_classes, parse_params, parse_winforms)
from .form_translate import _drop_stray_pass, set_form_code, set_startup, translate_form_class
from .ilspy import ILSPY_VERSIONS, _bundle_extract, decompile, find_ilspycmd, install_ilspycmd

# `from .dotnet import *` exports exactly what the single-file module exported (its public names) ...
__all__ = [
    "ALIGN_MAP", "APPROX_TYPES", "ASSIGN_OPS", "BINARY_PREC", "BinaryInfo", "COLOR_NAMES", "CS_FMT", "DEFAULTS",
    "EVENT_MAP", "FIELD_RE", "IGNORED_TYPES", "ILSPY_VERSIONS", "ImportResult", "MENU_ITEM_TYPES", "METHOD_RE",
    "MODIFIERS", "PY_OPS", "PY_RESERVED", "P_ADD", "P_AND", "P_ATOM", "P_BAND", "P_BOR", "P_BXOR", "P_CMP",
    "P_COND", "P_MUL", "P_NOT", "P_OR", "P_SHIFT", "P_UNARY", "ParseError", "Parser", "Path", "PyEmitter",
    "STMT_KEYWORDS", "TYPE_KEYWORDS", "TYPE_KIND", "Tok", "Untranslatable", "WINFORMS_TYPES", "WinFormsClass",
    "ai_rewrite", "annotations", "brace_matches", "can_handle", "class_fields", "class_methods",
    "convert_csharp_tree", "cs_date_format", "cs_format_spec", "decompile", "download", "find_classes",
    "find_ilspycmd", "find_tool", "install_ilspycmd", "json", "keyword", "os", "parse_params", "parse_winforms",
    "py_ident", "pystr", "re", "run", "run_tool", "save_json", "say", "set_form_code", "set_startup", "shutil",
    "subprocess", "tokenize", "tools_dir", "translate_form_class", "urllib",
]
# ... and the private helpers stay importable by name (from .dotnet import _lit, _match_brace, ...).
_PRIVATE_REEXPORTS = (_ESC, _NUM, _OPS, _base_ai_translate, _bundle_extract, _color, _depth, _drop_stray_pass,
                      _enum_last, _lit, _match_brace, _mnemonic, _qual, _strip_this, _unescape)



# ============================================================================ backend API
def can_handle(info: BinaryInfo) -> bool:
    return getattr(info, "kind", "") == "dotnet"


def run(path, info: BinaryInfo, workdir, progress=None, ai_translate: bool = False) -> ImportResult:
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    d = getattr(info, "details", {}) or {}
    assembly = Path(d["managed_dll"]) if d.get("managed_dll") else path
    if d.get("bundle") and not d.get("managed_dll"):
        say(progress, "Extracting the .NET single-file bundle ...")
        main = _bundle_extract(path, workdir)
        if main is None:
            res.add("error", "Could not read the .NET single-file bundle.")
            return res
        assembly = main
        res.add("info", f"Single-file bundle: main assembly {main.name} extracted.")
    src_dir, log = decompile(assembly, workdir / "csharp", progress)
    if src_dir is None:
        res.add("error", log)
        return res
    res.source_dir = src_dir
    res.add("exact", f"Decompiled {assembly.name} to a C# project with ILSpy ({sum(1 for _ in src_dir.rglob('*.cs'))}"
                     " .cs files) - kept in the project's _original folder.")
    return convert_csharp_tree(src_dir, res, progress, ai_translate)


def convert_csharp_tree(src_dir: Path, res: ImportResult, progress=None, ai_translate: bool = False,
                        language: str = "python-tk") -> ImportResult:
    """Decompiled (or original) C# sources -> forms + Python code in *res*."""
    classes: list[WinFormsClass] = []
    startup = ""
    for f in sorted(src_dir.rglob("*.cs")):
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        m = re.search(r"Application\.Run\s*\(\s*new\s+([\w.]+)\s*\(", text)
        if m:
            startup = m.group(1).split(".")[-1]
        classes += find_classes(text, f)
    # merge partial classes (Form1.cs + Form1.Designer.cs when importing sources)
    merged: dict[str, WinFormsClass] = {}
    for c in classes:
        if c.name in merged:
            merged[c.name].body += "\n" + c.body
            if not merged[c.name].base:
                merged[c.name].base = c.base
        else:
            merged[c.name] = c
    form_classes = [c for c in merged.values() if "InitializeComponent" in c.body and
                    re.search(r"\bvoid\s+InitializeComponent\s*\(", c.body) and
                    (c.base.split(".")[-1] in ("Form", "UserControl") or "Controls.Add" in c.body)]
    all_forms = {c.name for c in form_classes}
    if not form_classes:
        res.add("missing", "No WinForms form found (console, WPF or library assembly) - the C# code is in "
                           "_original; translate it with AI from the editor.")
    if startup and startup in all_forms:
        form_classes.sort(key=lambda c: c.name != startup)
    set_startup(res, startup if startup in all_forms else (form_classes[0].name if form_classes else ""))
    res.resources["form_code_language"] = language
    total_t = total_u = 0
    for cls in form_classes:
        say(progress, f"Reading form {cls.name} ...")
        try:
            parsed = parse_winforms(cls, all_forms)
        except Exception as e:  # noqa: BLE001
            res.add("error", f"{cls.name}: InitializeComponent could not be read ({e})")
            continue
        if parsed is None:
            continue
        form_dict, wiring, notes = parsed
        for n in notes:
            res.add("warn", n)
        res.forms.append((cls.name, form_dict))
        nctl = len(form_dict["controls"])
        res.add("exact", f"Form {cls.name}: {nctl} control(s), title, size, positions, fonts, colours, "
                         f"anchors and {len(wiring)} event handler(s) from InitializeComponent.")
        say(progress, f"Translating the code of {cls.name} to Python ...")
        try:
            tr = translate_form_class(cls, form_dict, wiring, all_forms, language)
        except Exception as e:  # noqa: BLE001
            res.add("error", f"{cls.name}: code translation failed ({e}); the C# stays in _original.")
            continue
        t, u = tr["stats"]
        total_t += t
        total_u += u
        code = tr["code"]
        ai_used = False
        if ai_translate and u:
            partial = [m for m, s in tr["methods"] if s == "partial"]
            ctx = ("Target: a python-tk RAD IDE form class. Controls are self.<Name>; TextBox text is "
                   "self.<Name>_var.get()/set(), Label/Button text self.<Name>.config(text=...), CheckBox "
                   "self.<Name>_var, ListBox is a tk.Listbox. Keep every method name and signature; "
                   "return the WHOLE class file.\nControls: " +
                   ", ".join(f"{c['props']['Name']} ({c['type']})" for c in form_dict["controls"]) +
                   "\nOriginal C# of the methods still marked '# C#:':\n" +
                   "\n\n".join(tr["csharp"].get(m.split(" ")[0], "") for m in partial))
            new, who = ai_rewrite(code, "partly translated Python (C# lines in comments)", ctx, progress)
            if new and "class " + cls.name in new:
                try:
                    compile(new, f"{cls.name}.py", "exec")
                    code = new
                    ai_used = True
                    res.add("ai", f"{cls.name}: {len(partial)} method(s) with untranslated lines rewritten by "
                                  f"AI ({who}).")
                except SyntaxError as e:
                    res.add("warn", f"{cls.name}: the AI answer did not compile ({e}); rules kept.")
            else:
                res.add("warn", f"{cls.name}: AI translation not used - {who}")
        try:
            compile(code, f"{cls.name}.py", "exec")
        except SyntaxError as e:
            res.add("warn", f"{cls.name}.py: generated code has a syntax error at line {e.lineno}: {e.msg}")
        set_form_code(res, cls.name, code, language, tr["handlers"])
        done = [m for m, s in tr["methods"] if s == "rules"]
        part = [m for m, s in tr["methods"] if s == "partial"]
        if done:
            res.add("rules", f"{cls.name}: translated to Python by rules: " + ", ".join(done))
        if part and not ai_used:
            res.add("missing", f"{cls.name}: some lines kept as '# C#:' comments in " + ", ".join(part) +
                               " (enable AI translation or rewrite them).")
    # non-form classes: kept as C# modules for reference, plus AI translation of small ones when allowed
    others = [c for c in merged.values() if c not in form_classes and c.name not in ("Program", "Resources",
                                                                                     "Settings",
                                                                                     "ApplicationConfiguration")]
    for c in others[:40]:
        src = c.file.read_text(encoding="utf-8-sig", errors="replace") if c.file else c.body
        rel = c.file.relative_to(src_dir).as_posix() if c.file else f"{c.name}.cs"
        res.modules.append((rel, src, "csharp"))
    if others:
        res.add("info", f"{len(others)} other class(es) kept as C# for reference: "
                        + ", ".join(c.name for c in others[:12]) + (" ..." if len(others) > 12 else ""))
    res.resources["translation_stats"] = {"statements_translated": total_t, "statements_commented": total_u}
    res.resources["notes"] = ("resources[form_code][<form>] is the complete user code (handlers + fields + helper "
                              "methods) for the form_code_language plugin; handlers holds the bodies for others.")
    return res
