""".editorconfig support (https://editorconfig.org + the .NET keys):

* effective(path)                  the settings that apply to a file (all .editorconfig files up to root=true)
* set_value(file, section, key, v) edit one key in place (comments, order and other sections are kept)
* set_severity(file, rule, sev)    ``dotnet_diagnostic.<ID>.severity = error|warning|suggestion|silent|none``
* rule_severities(path)            {rule id: severity} configured for a file (+ category / all-analyzer keys)
* for_project(folder)              the .editorconfig Visual Studio would create / edit for a project or solution

Severities use the .editorconfig words; Roslyn's DiagnosticSeverity maps as Error->error, Warning->warning,
Info->suggestion, Hidden->silent (and "none" turns a rule off)."""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

SEVERITIES = ["error", "warning", "suggestion", "silent", "none"]
SEVERITY_TITLES = {"error": "Error", "warning": "Warning", "suggestion": "Suggestion", "silent": "Silent",
                   "none": "None", "default": "Default"}
ROSLYN_TO_EC = {"Error": "error", "Warning": "warning", "Info": "suggestion", "Hidden": "silent"}
CS_SECTION = "[*.cs]"
DOTNET_SECTION = "[*.{cs,vb}]"

_SECTION = re.compile(r"^\s*\[(.+)\]\s*(?:[#;].*)?$")
_PAIR = re.compile(r"^\s*([^=#;\[][^=]*?)\s*[=:]\s*(.*?)\s*$")


def _expand_braces(pat: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", pat)
    if not m:
        return [pat]
    body = m.group(1)
    rng = re.fullmatch(r"(-?\d+)\.\.(-?\d+)", body)
    opts = [str(i) for i in range(int(rng.group(1)), int(rng.group(2)) + 1)] if rng else body.split(",")
    out = []
    for o in opts:
        out += _expand_braces(pat[:m.start()] + o + pat[m.end():])
    return out


def glob_matches(section: str, rel_posix: str) -> bool:
    """editorconfig glob: no '/' -> matches the file name anywhere; '**' crosses folders."""
    for pat in _expand_braces(section):
        if "/" not in pat:
            if fnmatch.fnmatchcase(rel_posix.rsplit("/", 1)[-1], pat):
                return True
            continue
        pat = pat.lstrip("/")
        rx = re.escape(pat).replace(r"\*\*", "\0").replace(r"\*", "[^/]*").replace("\0", ".*").replace(r"\?", "[^/]")
        if re.fullmatch(rx, rel_posix):
            return True
    return False


def parse(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """[(section glob or '' for the preamble, [(key lower, value)])]."""
    out = [("", [])]
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in "#;":
            continue
        m = _SECTION.match(line)
        if m:
            out.append((m.group(1).strip(), []))
            continue
        m = _PAIR.match(line)
        if m:
            val = re.split(r"\s+[#;]", m.group(2), maxsplit=1)[0].strip()
            out[-1][1].append((m.group(1).strip().lower(), val))
    return out


def files_for(path: Path) -> list[Path]:
    """.editorconfig files that apply to *path*, outermost first (stops at root = true)."""
    p = Path(path).resolve()
    found = []
    for d in [p if p.is_dir() else p.parent, *(p if p.is_dir() else p.parent).parents]:
        f = d / ".editorconfig"
        if f.is_file():
            found.append(f)
            try:
                pre = parse(f.read_text(encoding="utf-8-sig", errors="replace"))[0][1]
            except OSError:
                pre = []
            if any(k == "root" and v.lower() == "true" for k, v in pre):
                break
    return list(reversed(found))


def effective(path: Path) -> dict[str, str]:
    """Settings for one file (later sections / nearer files win)."""
    p = Path(path).resolve()
    res: dict[str, str] = {}
    for f in files_for(p):
        try:
            rel = p.relative_to(f.parent).as_posix()
        except ValueError:
            continue
        for sec, pairs in parse(f.read_text(encoding="utf-8-sig", errors="replace"))[1:]:
            if glob_matches(sec, rel):
                for k, v in pairs:
                    res[k] = v
    return res


def rule_severities(path: Path) -> dict[str, str]:
    """{RULE_ID: severity} + {"category:<Category>": sev} + {"*": sev} from the keys that apply to *path*."""
    out = {}
    for k, v in effective(path).items():
        sev = v.split(":")[-1].strip().lower()
        m = re.fullmatch(r"dotnet_diagnostic\.([^.]+)\.severity", k)
        if m:
            out[m.group(1).upper()] = sev
            continue
        m = re.fullmatch(r"dotnet_analyzer_diagnostic\.category-([^.]+)\.severity", k)
        if m:
            out["category:" + m.group(1).lower()] = sev
            continue
        if k == "dotnet_analyzer_diagnostic.severity":
            out["*"] = sev
    return out


def effective_severity(rule_id: str, category: str, default: str, enabled: bool, configured: dict) -> str:
    """Severity Visual Studio shows for a rule ("default" = the analyzer's own default)."""
    rid = rule_id.upper()
    if rid in configured:
        return configured[rid]
    if "category:" + (category or "").lower() in configured:
        return configured["category:" + category.lower()]
    if "*" in configured and enabled:
        return configured["*"]
    if not enabled:
        return "none"
    return ROSLYN_TO_EC.get(default, default.lower() if default else "warning")


def for_project(folder: Path) -> Path:
    """The .editorconfig to edit: the nearest existing one, else a new one in *folder*."""
    folder = Path(folder)
    near = files_for(folder / "x.cs")
    return near[-1] if near else folder / ".editorconfig"


def set_value(file: Path, section: str, key: str, value: str | None) -> bool:
    """Set (or with value None remove) *key* in [section] of *file*; creates the file / section.
    Returns True when the file changed."""
    file = Path(file)
    sec = section.strip()
    if not sec.startswith("["):
        sec = f"[{sec}]"
    try:
        text = file.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    if not lines:
        lines = ["# To learn more about .editorconfig see https://aka.ms/editorconfigdocs", "root = true", ""]
    start = end = None
    for i, line in enumerate(lines):
        m = _SECTION.match(line)
        if m and start is not None and end is None:
            end = i
        if m and f"[{m.group(1).strip()}]" == sec and start is None:
            start = i
    if start is not None and end is None:
        end = len(lines)
    low = key.lower()
    if start is None:
        if value is None:
            return False
        if lines and lines[-1].strip():
            lines.append("")
        lines += [sec, f"{key} = {value}"]
    else:
        hit = None
        for i in range(start + 1, end):
            m = _PAIR.match(lines[i])
            if m and m.group(1).strip().lower() == low:
                hit = i
        if hit is not None:
            if value is None:
                del lines[hit]
            else:
                lines[hit] = f"{key} = {value}"
        elif value is not None:
            ins = end
            while ins > start + 1 and not lines[ins - 1].strip():
                ins -= 1
            lines.insert(ins, f"{key} = {value}")
        else:
            return False
    new = nl.join(lines).rstrip() + nl
    if new == text:
        return False
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(new, encoding="utf-8", newline="")
    return True


def get_value(file: Path, section: str, key: str) -> str | None:
    sec = section.strip().strip("[]")
    try:
        parsed = parse(Path(file).read_text(encoding="utf-8-sig", errors="replace"))
    except OSError:
        return None
    val = None
    for s, pairs in parsed:
        if s == sec:
            for k, v in pairs:
                if k == key.lower():
                    val = v
    return val


def set_severity(file: Path, rule_id: str, severity: str | None, section: str = CS_SECTION) -> bool:
    """severity None / "default" removes the override."""
    sev = None if severity in (None, "", "default") else severity.lower()
    if sev is not None and sev not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}")
    return set_value(file, section, f"dotnet_diagnostic.{rule_id.upper()}.severity", sev)


def set_category_severity(file: Path, category: str, severity: str | None, section: str = CS_SECTION) -> bool:
    sev = None if severity in (None, "", "default") else severity.lower()
    return set_value(file, section, f"dotnet_analyzer_diagnostic.category-{category}.severity", sev)


# ---------------------------------------------------------------- editor settings
def editor_options(path: Path) -> dict:
    """indent / tab size / newline settings of *path* for the code editor."""
    e = effective(path)
    out = {}
    style = e.get("indent_style", "").lower()
    if style in ("space", "tab"):
        out["insertSpaces"] = style == "space"
    size = e.get("indent_size", "")
    tab = e.get("tab_width", "")
    if size.isdigit():
        out["indentSize"] = int(size)
        out["tabSize"] = int(size)
    elif size == "tab" and tab.isdigit():
        out["tabSize"] = int(tab)
    if tab.isdigit() and "tabSize" not in out:
        out["tabSize"] = int(tab)
    if e.get("trim_trailing_whitespace", "").lower() == "true":
        out["trimTrailingWhitespace"] = True
    if e.get("insert_final_newline", "").lower() in ("true", "false"):
        out["insertFinalNewline"] = e["insert_final_newline"].lower() == "true"
    if e.get("end_of_line", "").lower() in ("lf", "crlf", "cr"):
        out["endOfLine"] = e["end_of_line"].lower()
    return out


# ---------------------------------------------------------------- code style options (Code Style tab)
CODE_STYLE = [
    # (key, title, values, section)
    ("csharp_style_var_for_built_in_types", "Use 'var' for built-in types", ["true", "false"], CS_SECTION),
    ("csharp_style_var_when_type_is_apparent", "Use 'var' when the type is apparent", ["true", "false"], CS_SECTION),
    ("csharp_style_var_elsewhere", "Use 'var' elsewhere", ["true", "false"], CS_SECTION),
    ("csharp_using_directive_placement", "'using' directive placement", ["outside_namespace", "inside_namespace"],
     CS_SECTION),
    ("csharp_style_namespace_declarations", "Namespace declarations", ["block_scoped", "file_scoped"], CS_SECTION),
    ("csharp_prefer_braces", "Prefer braces", ["true", "false", "when_multiline"], CS_SECTION),
    ("csharp_style_expression_bodied_methods", "Expression-bodied methods", ["false", "true", "when_on_single_line"],
     CS_SECTION),
    ("csharp_style_expression_bodied_properties", "Expression-bodied properties", ["true", "false",
                                                                                   "when_on_single_line"], CS_SECTION),
    ("dotnet_sort_system_directives_first", "Place 'System' directives first when sorting usings",
     ["true", "false"], DOTNET_SECTION),
    ("dotnet_separate_import_directive_groups", "Separate using directive groups", ["false", "true"], DOTNET_SECTION),
    ("dotnet_style_qualification_for_field", "Qualify field access with 'this'", ["false", "true"], DOTNET_SECTION),
    ("dotnet_style_predefined_type_for_locals_parameters_members",
     "Use language keywords instead of framework type names", ["true", "false"], DOTNET_SECTION),
    ("csharp_new_line_before_open_brace", "New line before open brace", ["all", "none"], CS_SECTION),
]

WHITESPACE = [
    ("indent_style", "Indent style", ["space", "tab"]),
    ("indent_size", "Indent size", ["4", "2", "3", "8", "tab"]),
    ("tab_width", "Tab width", ["4", "2", "8"]),
    ("end_of_line", "End of line", ["crlf", "lf", "cr"]),
    ("insert_final_newline", "Insert final newline", ["false", "true"]),
    ("trim_trailing_whitespace", "Trim trailing whitespace", ["true", "false"]),
    ("charset", "Charset", ["utf-8", "utf-8-bom", "latin1", "utf-16le", "utf-16be"]),
]


__all__ = ["effective", "set_value", "get_value", "set_severity", "set_category_severity", "rule_severities",
           "effective_severity", "for_project", "files_for", "glob_matches", "editor_options", "parse",
           "SEVERITIES", "SEVERITY_TITLES", "ROSLYN_TO_EC", "CODE_STYLE", "WHITESPACE", "CS_SECTION",
           "DOTNET_SECTION"]
