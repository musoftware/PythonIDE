"""Conditional compilation for the editor's "project context" (no Qt here).

* ``implicit_symbols(tfm, language)``   - the symbols the .NET SDK defines for a target framework
  (NET8_0, NET8_0_OR_GREATER ... NETCOREAPP, NETSTANDARD2_0, NETFRAMEWORK, NET48, WINDOWS ...).
* ``define_constants(ms, configuration, platform, tfm)`` - DefineConstants of an MSBuild project for a
  configuration / platform / target framework: the property groups are evaluated in order (conditions
  on $(Configuration), $(Platform), $(TargetFramework)), ``$(DefineConstants);X`` accumulates, SDK-style
  projects add DEBUG/RELEASE + TRACE and the framework symbols, VB adds DefineDebug / DefineTrace,
  CONFIG, PLATFORM and ``_MyType``.
* ``inactive_ranges(text, symbols, language)`` - 0-based (first, last) line ranges that the selected
  context does not compile (between #if / #elif / #else / #endif, C# and VB syntax, nested, with
  ``#define`` / ``#undef`` / ``#Const``). The directive lines themselves stay active (like VS).
"""
from __future__ import annotations

import re

# ----------------------------------------------------------------------------- framework symbols
_NETCORE_VERSIONS = ["1.0", "1.1", "2.0", "2.1", "2.2", "3.0", "3.1"]
_NET_VERSIONS = ["5.0", "6.0", "7.0", "8.0", "9.0", "10.0"]
_NETSTANDARD = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "2.0", "2.1"]
_NETFX = ["20", "35", "40", "45", "451", "452", "46", "461", "462", "47", "471", "472", "48", "481"]


def _u(v: str) -> str:
    return v.replace(".", "_")


def parse_tfm(tfm: str) -> tuple[str, str, str]:
    """('netcore'|'net'|'netstandard'|'netfx'|'', version, os) for a target framework moniker."""
    t = (tfm or "").strip().lower()
    os_part = ""
    if "-" in t:
        t, os_part = t.split("-", 1)
    m = re.fullmatch(r"netcoreapp(\d+\.\d+)", t)
    if m:
        return "netcore", m.group(1), os_part
    m = re.fullmatch(r"netstandard(\d+\.\d+)", t)
    if m:
        return "netstandard", m.group(1), os_part
    m = re.fullmatch(r"net(\d+\.\d+)", t)
    if m:
        return "net", m.group(1), os_part
    m = re.fullmatch(r"net(\d{2,3})", t)
    if m:
        return "netfx", m.group(1), os_part
    m = re.fullmatch(r"v?(\d)\.(\d)(?:\.(\d))?", t)          # TargetFrameworkVersion v4.8
    if m:
        return "netfx", "".join(g for g in m.groups() if g), os_part
    return "", "", os_part


def implicit_symbols(tfm: str) -> list[str]:
    """Preprocessor symbols the SDK defines for *tfm* (SDK-style projects only)."""
    fam, ver, os_part = parse_tfm(tfm)
    out: list[str] = []
    if fam in ("net", "netcore"):
        out.append("NETCOREAPP")
        if fam == "net":
            out.append("NET")
            out.append("NET" + _u(ver))
            for v in _NET_VERSIONS:
                if float(v) <= float(ver):
                    out.append(f"NET{_u(v)}_OR_GREATER")
            out += [f"NETCOREAPP{_u(v)}_OR_GREATER" for v in _NETCORE_VERSIONS]
        else:
            out.append("NETCOREAPP" + _u(ver))
            out += [f"NETCOREAPP{_u(v)}_OR_GREATER" for v in _NETCORE_VERSIONS if float(v) <= float(ver)]
    elif fam == "netstandard":
        out += ["NETSTANDARD", "NETSTANDARD" + _u(ver)]
        out += [f"NETSTANDARD{_u(v)}_OR_GREATER" for v in _NETSTANDARD if float(v) <= float(ver)]
    elif fam == "netfx":
        out += ["NETFRAMEWORK", "NET" + ver]
        num = lambda s: float(s[0] + "." + s[1:]) if len(s) > 1 else float(s)   # noqa: E731
        out += [f"NET{v}_OR_GREATER" for v in _NETFX if num(v) <= num(ver)]
    if os_part:
        m = re.match(r"([a-z]+)([\d.]*)", os_part)
        if m:
            osn = m.group(1).upper()
            osn = {"MACCATALYST": "MACCATALYST", "IOS": "IOS", "ANDROID": "ANDROID", "WINDOWS": "WINDOWS",
                   "MACOS": "MACOS", "TVOS": "TVOS", "BROWSER": "BROWSER"}.get(osn, osn)
            out.append(osn)
            if m.group(2):
                out.append(f"{osn}{_u(m.group(2))}_OR_GREATER")
            elif osn == "WINDOWS":
                out.append("WINDOWS7_0_OR_GREATER")
    return out


# ----------------------------------------------------------------------------- MSBuild evaluation
def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _expand(s: str, props: dict) -> str:
    return re.sub(r"\$\((\w+)\)", lambda m: props.get(m.group(1), ""), s or "")


def eval_condition(cond: str, props: dict) -> bool:
    """MSBuild conditions as projects write them: 'a' == 'b', !=, and / or, parentheses,
    Exists(...) (False), '$(X)' == ''. Unknown shapes count as True (like a permissive evaluator)."""
    if not cond or not cond.strip():
        return True
    s = _expand(cond, props)
    tokens = re.findall(r"'[^']*'|==|!=|\(|\)|\band\b|\bor\b|\bAND\b|\bOR\b|\bAnd\b|\bOr\b|!|"
                        r"Exists\s*\([^)]*\)|HasTrailingSlash\s*\([^)]*\)|[^\s()'=!]+", s)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def value(t):
        return t[1:-1].strip().lower() if t.startswith("'") else t.strip().lower()

    def atom():
        t = take() if peek() is not None else "'true'"
        if t == "(":
            v = expr()
            if peek() == ")":
                take()
            return v
        if t == "!":
            return not atom()
        if t.lower().startswith("exists"):
            return False
        if t.lower().startswith("hastrailingslash"):
            return True
        if peek() in ("==", "!="):
            op = take()
            r = take() if peek() is not None else "''"
            return (value(t) == value(r)) if op == "==" else (value(t) != value(r))
        return value(t) == "true"

    def conj():
        v = atom()
        while peek() is not None and peek().lower() == "and":
            take()
            v = atom() and v
        return v

    def expr():
        v = conj()
        while peek() is not None and peek().lower() == "or":
            take()
            v = conj() or v
        return v
    try:
        return bool(expr())
    except (IndexError, ValueError):
        return True


def define_constants(ms, configuration: str = "Debug", platform: str = "AnyCPU", tfm: str = "") -> list[str]:
    """Preprocessor symbols of an MSBuild project (radide.foreign.msbuild.MSBuildProject) for a context.
    VB symbols come back as plain names too (their values are in ``vb_constants``)."""
    return list(vb_constants(ms, configuration, platform, tfm).keys()) if ms.language == "VB" else \
        _cs_symbols(ms, configuration, platform, tfm)


def _evaluate(ms, configuration: str, platform: str, tfm: str, seed: str = "") -> dict:
    """The project's property groups evaluated in order; *seed*: DefineConstants before the project body."""
    platform = "AnyCPU" if platform in ("Any CPU", "") else platform
    props = {"Configuration": configuration, "Platform": platform, "TargetFramework": tfm,
             "MSBuildProjectName": ms.name, "DefineConstants": seed}
    root = getattr(ms, "root", None)
    if root is None:
        return props
    for el in root:
        if _local(el.tag) != "PropertyGroup" or not eval_condition(el.get("Condition", ""), props):
            continue
        for p in el:
            name = _local(p.tag)
            if not name or not eval_condition(p.get("Condition", ""), props):
                continue
            if name in ("Configuration", "Platform", "TargetFramework") and p.get("Condition"):
                continue                       # defaults like <Configuration Condition="'$(Configuration)'==''">
            if name in ("TargetFramework",) and tfm:
                continue
            props[name] = _expand((p.text or "").strip(), props)
    return props


def _split_cs(value: str) -> list[str]:
    return [s.strip() for s in re.split(r"[;,]", value or "") if s.strip() and "=" not in s]


def _cs_symbols(ms, configuration, platform, tfm) -> list[str]:
    # SDK-style: Microsoft.NET.Sdk.CSharp.props sets DefineConstants=$(DefineConstants);TRACE (+DEBUG / RELEASE)
    # before the project body, so a plain <DefineConstants>X</DefineConstants> replaces them; the framework symbols
    # (NET8_0, NETFRAMEWORK, NET48 ...) are added by the SDK targets after it. Old-style (non-SDK) .NET Framework
    # projects get neither: only their own DefineConstants - "#if NETFRAMEWORK" is false there, and MSBuild
    # agrees (a shared file's #else branch is what an old-style net48 project compiles).
    seed = ""
    if ms.is_sdk:
        c = configuration.lower()
        seed = "TRACE;DEBUG" if c == "debug" else ("TRACE;RELEASE" if c == "release" else "TRACE")
    props = _evaluate(ms, configuration, platform, tfm, seed)
    syms = _split_cs(props.get("DefineConstants", ""))
    if ms.is_sdk and props.get("DisableImplicitFrameworkDefines", "").lower() != "true":
        syms += implicit_symbols(tfm or (ms.target_frameworks[:1] or [""])[0])
    return list(dict.fromkeys(syms))


def vb_constants(ms, configuration: str = "Debug", platform: str = "AnyCPU", tfm: str = "") -> dict:
    """VB conditional compilation constants {name: value} (True/False/number/string)."""
    props = _evaluate(ms, configuration, platform, tfm)
    out: dict = {}
    if ms.is_sdk:
        if configuration.lower() == "debug":
            out["DEBUG"] = True
        out["TRACE"] = True
        if configuration.lower() == "release":
            out["RELEASE"] = True
        for s in implicit_symbols(tfm or (ms.target_frameworks[:1] or [""])[0]):
            out[s] = True
    if props.get("DefineDebug", "").lower() == "true":
        out["DEBUG"] = True
    if props.get("DefineTrace", "").lower() == "true":
        out["TRACE"] = True
    out["CONFIG"] = configuration
    out["PLATFORM"] = props.get("Platform", "AnyCPU")
    if props.get("MyType"):
        out["_MyType"] = props["MyType"]
    for part in re.split(r",", props.get("DefineConstants", "")):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = (x.strip() for x in part.split("=", 1))
            out[k] = _vb_literal(v)
        elif ";" in part:
            for s in part.split(";"):
                if s.strip():
                    out[s.strip()] = True
        else:
            out[part] = True
    return out


def _vb_literal(v: str):
    v = v.strip()
    if v.lower() == "true" or v == "-1":
        return True
    if v.lower() == "false" or v == "0":
        return False
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        return v


# ----------------------------------------------------------------------------- expressions
def _eval_cs(expr: str, syms: set) -> bool:
    expr = re.sub(r"//.*$", "", expr).strip()
    tokens = re.findall(r"&&|\|\||==|!=|!|\(|\)|[A-Za-z_]\w*", expr)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom():
        t = take()
        if t == "!":
            return not atom()
        if t == "(":
            v = orx()
            if peek() == ")":
                take()
            return v
        if t == "true":
            return True
        if t == "false":
            return False
        return t in syms

    def eq():
        v = atom()
        while peek() in ("==", "!="):
            op = take()
            r = atom()
            v = (v == r) if op == "==" else (v != r)
        return v

    def andx():
        v = eq()
        while peek() == "&&":
            take()
            r = eq()
            v = v and r
        return v

    def orx():
        v = andx()
        while peek() == "||":
            take()
            r = andx()
            v = v or r
        return v
    try:
        return bool(orx()) if tokens else False
    except IndexError:
        return False


def _eval_vb(expr: str, consts: dict):
    expr = re.sub(r"\s+Then\s*$", "", re.sub(r"'.*$", "", expr), flags=re.I).strip()
    tokens = re.findall(r'"[^"]*"|<>|<=|>=|=|<|>|\(|\)|[A-Za-z_]\w*|-?\d+', expr)
    pos = 0
    low_consts = {k.lower(): v for k, v in consts.items()}

    def peek():
        return tokens[pos].lower() if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom():
        t = take()
        tl = t.lower()
        if tl == "not":
            v = atom()
            return (not v) if isinstance(v, bool) else ~int(v or 0)
        if t == "(":
            v = orx()
            if peek() == ")":
                take()
            return v
        if tl == "true":
            return True
        if tl == "false":
            return False
        if tl == "nothing":
            return None
        if t.startswith('"'):
            return t[1:-1]
        if re.fullmatch(r"-?\d+", t):
            return int(t)
        return low_consts.get(tl, None)

    def norm(v):
        return False if v is None else v

    def cmp():
        v = atom()
        while peek() in ("=", "<>", "<", ">", "<=", ">="):
            op = take()
            r = atom()
            a, b = norm(v), norm(r)
            if isinstance(a, bool) and isinstance(b, int) and not isinstance(b, bool):
                a = -1 if a else 0
            if isinstance(b, bool) and isinstance(a, int) and not isinstance(a, bool):
                b = -1 if b else 0
            try:
                v = {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
            except TypeError:
                v = False
        return v

    def andx():
        v = cmp()
        while peek() in ("and", "andalso"):
            take()
            r = cmp()
            v = _truthy(v) and _truthy(r)
        return v

    def orx():
        v = andx()
        while peek() in ("or", "orelse", "xor"):
            op = take().lower()
            r = andx()
            v = (_truthy(v) != _truthy(r)) if op == "xor" else (_truthy(v) or _truthy(r))
        return v
    try:
        return _truthy(orx()) if tokens else False
    except IndexError:
        return False


def _truthy(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v)
    return bool(v)


# ----------------------------------------------------------------------------- regions
_CS_DIR = re.compile(r"^\s*#\s*(if|elif|else|endif|define|undef)\b(.*)$")
_VB_DIR = re.compile(r"^\s*#\s*(if|elseif|else\s*if|else|end\s*if|const)\b(.*)$", re.I)


def inactive_ranges(text: str, symbols, language: str = "C#") -> list[tuple[int, int]]:
    """0-based inclusive (first, last) line ranges of code that the context does not compile.
    *symbols*: iterable of names (C#) or {name: value} (VB; a plain iterable means True)."""
    vb = language.upper() in ("VB", "VB.NET", "VISUALBASIC")
    if vb:
        consts = dict(symbols) if isinstance(symbols, dict) else {s: True for s in symbols}
    else:
        syms = set(symbols.keys() if isinstance(symbols, dict) else symbols)
    lines = text.splitlines()
    # stack entries: [parent_active, this_branch_active, any_branch_taken]
    stack: list[list[bool]] = []
    active = True
    out: list[tuple[int, int]] = []
    start = None

    def close(i):
        nonlocal start
        if start is not None and i - 1 >= start:
            out.append((start, i - 1))
        start = None

    for i, line in enumerate(lines):
        m = (_VB_DIR if vb else _CS_DIR).match(line)
        if m:
            d = re.sub(r"\s+", "", m.group(1).lower())
            arg = m.group(2)
            close(i)
            if d == "if":
                cond = (_eval_vb(arg, consts) if vb else _eval_cs(arg, syms)) if active else False
                stack.append([active, cond, cond])
                active = active and cond
            elif d in ("elif", "elseif") and stack:
                par, _cur, taken = stack[-1]
                cond = (not taken) and par and (_eval_vb(arg, consts) if vb else _eval_cs(arg, syms))
                stack[-1] = [par, cond, taken or cond]
                active = par and cond
            elif d == "else" and stack:
                par, _cur, taken = stack[-1]
                cond = par and not taken
                stack[-1] = [par, cond, True]
                active = cond
            elif d == "endif" and stack:
                par = stack.pop()[0]
                active = par
            elif active and not vb and d in ("define", "undef"):
                name = arg.strip().split("//")[0].strip()
                (syms.add if d == "define" else syms.discard)(name)
            elif active and vb and d == "const":
                mm = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)$", arg)
                if mm:
                    consts[mm.group(1)] = _eval_vb_value(mm.group(2), consts)
            if not active:
                start = i + 1
            continue
        if not active and start is None:
            start = i
    if not active:
        close(len(lines))
    return out


def _eval_vb_value(expr: str, consts: dict):
    e = re.sub(r"'.*$", "", expr).strip()
    lit = _vb_literal(e)
    if not isinstance(lit, str) or e.startswith('"'):
        return lit
    return _eval_vb(e, consts)


def inactive_lines(text: str, symbols, language: str = "C#") -> set[int]:
    return {n for a, b in inactive_ranges(text, symbols, language) for n in range(a, b + 1)}


def has_conditionals(text: str) -> bool:
    return bool(re.search(r"^\s*#\s*(if|If|IF)\b", text, re.M))


__all__ = ["implicit_symbols", "parse_tfm", "eval_condition", "define_constants", "vb_constants",
           "inactive_ranges", "inactive_lines", "has_conditionals"]

