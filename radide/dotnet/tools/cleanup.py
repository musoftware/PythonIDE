"""Code Cleanup (Visual Studio 2022: Analyze > Code Cleanup, Ctrl+K, Ctrl+E) with ``dotnet format`` and
Edit > IntelliSense > Remove and Sort Usings (Ctrl+R, Ctrl+G).

* format_argv(target, profile, include)   the dotnet format command line for a document / project / solution
* PROFILES                                 Visual Studio's profiles mapped to dotnet format sub-commands
* organize_usings(file, text, project)     remove the unnecessary usings (compiler CS8019) and sort the rest;
                                           returns (new text, [removed directives], error)
* sort_usings_text(text)                   plain sorting without a compiler (fallback, also for VB "Imports")
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from . import analyzers, editorconfig, sdk

# id -> (title, [dotnet format argv after "format"])
PROFILES = {
    "full": ("Profile 1 (Full: whitespace, code style and analyzers)", ["--severity", "info"]),
    "whitespace": ("Profile 2 (Format document / whitespace only)", ["whitespace"]),
    "style": ("Code style fixes (IDE rules)", ["style", "--severity", "info"]),
    "analyzers": ("Analyzer fixes (CA and third-party rules)", ["analyzers", "--severity", "info"]),
}


def format_argv(target: Path, profile: str = "full", include: list[Path] | None = None, verify: bool = False,
                diagnostics: list[str] | None = None) -> list[str]:
    """``dotnet format [whitespace|style|analyzers] <sln|proj> [--include files]`` - run it with the target's folder
    as the working directory."""
    sub = list(PROFILES.get(profile, PROFILES["full"])[1])
    argv = [sdk.dotnet() or "dotnet", "format"]
    if sub and not sub[0].startswith("-"):
        argv.append(sub.pop(0))
    argv.append(str(target))
    argv += sub
    if include:                                   # dotnet format wants paths relative to the working folder
        base = Path(target).resolve().parent      # (callers run it in the target's folder)
        rels = []
        for p in include:
            try:
                rels.append(Path(p).resolve().relative_to(base).as_posix())
            except ValueError:
                rels.append(str(p))
        argv += ["--include", *rels]
    if diagnostics:
        argv += ["--diagnostics", *diagnostics]
    if verify:
        argv.append("--verify-no-changes")
    argv += ["-v", "n"]
    return argv


# ---------------------------------------------------------------- Remove and Sort Usings
def compile_inputs(project: Path, timeout: int = 240) -> dict:
    """Sources, compile references and parse options of a project (``dotnet msbuild -getItem``)."""
    d = sdk.msbuild_eval(project, items=["ReferencePathWithRefAssemblies", "Compile"],
                         properties=["LangVersion", "DefineConstants", "Nullable"],
                         targets=["FindReferenceAssembliesForReferences"], timeout=timeout)
    if not d:
        return {}
    items = d.get("Items") or {}
    props = d.get("Properties") or {}
    folder = Path(project).parent
    srcs = []
    for it in items.get("Compile", []):
        p = Path(it.get("FullPath") or folder / it.get("Identity", ""))
        if p.suffix.lower() == ".cs":
            srcs.append(str(p))
    return {"sources": srcs,
            "refs": [it.get("FullPath") or it.get("Identity", "") for it in items.get("ReferencePathWithRefAssemblies", [])],
            "langVersion": props.get("LangVersion", ""),
            "defines": [x for x in props.get("DefineConstants", "").split(";") if x],
            "nullable": props.get("Nullable", "")}


_INPUTS: dict[str, tuple[float, dict]] = {}


def organize_usings(file: Path, text: str | None = None, project: Path | None = None, remove: bool = True,
                    sort: bool = True, log=None) -> tuple[str | None, list[str], str]:
    """(new text or None, removed directives, error). Options from .editorconfig
    (dotnet_sort_system_directives_first, dotnet_separate_import_directive_groups)."""
    file = Path(file)
    if text is None:
        text = sdk.text(file)
    if file.suffix.lower() != ".cs":
        return sort_usings_text(text), [], ""
    project = project or sdk.project_for_file(file)
    ec = editorconfig.effective(file)
    inputs: dict = {}
    if project is not None:
        import time
        key = str(project).lower()
        hit = _INPUTS.get(key)
        mtime = Path(project).stat().st_mtime if Path(project).exists() else 0
        if hit and hit[0] == mtime and time.time() - hit[1].get("_t", 0) < 600:
            inputs = hit[1]
        else:
            inputs = compile_inputs(project)
            inputs["_t"] = time.time()
            _INPUTS[key] = (mtime, inputs)
    if not inputs.get("refs"):
        if remove:
            return sort_usings_text(text) if sort else None, [], ("could not evaluate the project: only sorting "
                                                                   "(restore / build the project first)")
    exe = analyzers.helper_exe(log=log)
    if not exe:
        return sort_usings_text(text) if sort else None, [], "the C# helper could not be built: only sorting"
    req = {"file": str(file), "text": text, "sources": inputs.get("sources", []), "refs": inputs.get("refs", []),
           "langVersion": inputs.get("langVersion", ""), "defines": inputs.get("defines", []),
           "nullable": inputs.get("nullable", ""), "remove": remove, "sort": sort,
           "systemFirst": ec.get("dotnet_sort_system_directives_first", "true").lower() != "false",
           "separateGroups": ec.get("dotnet_separate_import_directive_groups", "false").lower() == "true"}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(req, fh)
        req_path = fh.name
    try:
        code, out = sdk.run([exe, "--usings", req_path], timeout=300)
    finally:
        try:
            Path(req_path).unlink()
        except OSError:
            pass
    i = out.find("{")
    try:
        res = json.loads(out[i:out.rfind("}") + 1]) if i >= 0 else {}
    except ValueError:
        res = {}
    if not res:
        return None, [], "the C# helper failed:\n" + out[-800:]
    if res.get("error"):
        return None, [], res["error"]
    return res.get("text"), res.get("removed") or [], ""


_USING = re.compile(r"^(\s*)(global\s+)?using\s+(static\s+)?([\w.]+\s*=\s*)?([\w.<>,\s]+);\s*$")
_IMPORTS = re.compile(r"^(\s*)Imports\s+(.+?)\s*$", re.I)


def sort_usings_text(text: str, system_first: bool = True) -> str:
    """Sort each contiguous block of using / Imports lines (no semantic check)."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    out, block = [], []

    def key(line):
        m = _USING.match(line)
        if m:
            g, st, alias, name = m.group(2), m.group(3), m.group(4), m.group(5).strip()
            rank = (0 if g else 10) + (3 if alias else 2 if st else 1)
            k = alias.split("=")[0].strip() if alias else name
        else:
            m2 = _IMPORTS.match(line)
            rank, k = 1, (m2.group(2) if m2 else line)
        sysk = 0 if system_first and (k == "System" or k.startswith("System.")) else 1
        return (rank, sysk, k.lower(), k)

    def flush():
        if block:
            uniq = list(dict.fromkeys(block))
            out.extend(sorted(uniq, key=key))
            block.clear()
    for line in lines:
        if _USING.match(line) or _IMPORTS.match(line):
            block.append(line.rstrip())
        else:
            flush()
            out.append(line)
    flush()
    return nl.join(out)


__all__ = ["PROFILES", "format_argv", "organize_usings", "sort_usings_text", "compile_inputs"]
