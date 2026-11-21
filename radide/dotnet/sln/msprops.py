"""MSBuild project edits used by the Project Properties document (format preserving, text based, on a
``radide.foreign.msbuild.MSBuildProject``):

* unconditional and per-configuration properties (``<PropertyGroup Condition="'$(Configuration)|
  $(Platform)'=='Debug|AnyCPU'">`` - the exact spelling Visual Studio 2022 writes), set / remove;
* global usings (``<Using Include="..." />``), build events (SDK: ``PreBuild`` / ``PostBuild``
  targets with ``<Exec Command>``; legacy: ``PreBuildEvent`` / ``PostBuildEvent`` properties);
* Directory.Build.props / Directory.Build.targets: the files MSBuild imports for a project (nearest
  one walking up from the project folder) and the values a project inherits from them.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...foreign.msbuild import MSBuildProject, TextFile, xml_escape, xml_unescape


def cfg_condition(cfg: str, plat: str) -> str:
    return f"'$(Configuration)|$(Platform)'=='{cfg}|{plat}'"


def _norm(cond: str) -> str:
    return re.sub(r"\s+", "", cond or "").lower()


def _groups(ms: MSBuildProject):
    return ms._groups("PropertyGroup")


def _group_condition(open_tag: str) -> str:
    m = re.search(r"\bCondition\s*=\s*(['\"])(.*?)\1", open_tag, re.S)
    return xml_unescape(m.group(2)) if m else ""


def get(ms: MSBuildProject, name: str, cond: str | None = None) -> str | None:
    """The value written in the project (None = not written). *cond*: a PropertyGroup condition."""
    if not cond:
        v = ms.properties.get(name)
        return v
    want = _norm(cond)
    hit = None
    for c, n, v in ms.cond_properties:
        if n == name and _norm(c) == want:
            hit = v
    return hit


def effective(ms: MSBuildProject, name: str, cond: str | None = None, default: str = "") -> str:
    v = get(ms, name, cond) if cond else None
    if v is None:
        v = get(ms, name)
    if v is None:
        v, _f = inherited(ms, name)
    return v if v is not None else default


def set_value(ms: MSBuildProject, name: str, value: str, cond: str | None = None) -> bool:
    """Write *name* = *value* (empty value: remove the element). True when the text changed."""
    if value is None or value == "":
        return remove(ms, name, cond)
    if not cond:
        if ms.set_property(name, value):
            return True
        if ms.properties.get(name) == value:
            return False
        return _new_group(ms, "", name, value)
    want = _norm(cond)
    text = ms.file.text
    for g in _groups(ms):
        if _norm(_group_condition(g[2])) != want:
            continue
        body = text[g[3]:g[4]]
        m = re.search(rf"<{name}(\s[^>]*)?>(.*?)</{name}\s*>", body, re.S)
        if m:
            if xml_unescape(m.group(2)) == value:
                return False
            a, b = g[3] + m.start(2), g[3] + m.end(2)
            ms.file.text = text[:a] + xml_escape(value) + text[b:]
        else:
            m2 = re.search(rf"<{name}\s*/>", body)
            if m2:
                a, b = g[3] + m2.start(), g[3] + m2.end()
                ms.file.text = text[:a] + f"<{name}>{xml_escape(value)}</{name}>" + text[b:]
            else:
                indent = ms._indent_at(g[0]) + ms._indent_unit()
                last = list(re.finditer(r"<(\w+)(?:\s[^>]*)?>.*?</\1\s*>|<\w+[^>]*/>", body, re.S))
                nl = ms.file.newline
                if last:
                    end = g[3] + last[-1].end()
                    ms.file.text = text[:end] + f"{nl}{indent}<{name}>{xml_escape(value)}</{name}>" + text[end:]
                else:
                    close = g[4]
                    ms.file.text = (text[:g[3]] + f"{nl}{indent}<{name}>{xml_escape(value)}</{name}>{nl}"
                                    + ms._indent_at(g[0]) + text[close:])
        ms.parse()
        return True
    return _new_group(ms, cond, name, value)


def _new_group(ms: MSBuildProject, cond: str, name: str, value: str) -> bool:
    text, nl, unit = ms.file.text, ms.file.newline, ms._indent_unit()
    groups = _groups(ms)
    if groups:
        anchor = groups[-1][1]
        indent = ms._indent_at(groups[-1][0])
    else:
        m = re.search(r"<Project\b[^>]*>", text)
        anchor = m.end() if m else 0
        indent = unit
    attr = f' Condition="{xml_escape(cond)}"' if cond else ""
    blank = nl if ms.is_sdk else ""
    block = (f"{nl}{blank}{indent}<PropertyGroup{attr}>{nl}{indent}{unit}<{name}>{xml_escape(value)}</{name}>"
             f"{nl}{indent}</PropertyGroup>")
    ms.file.text = text[:anchor] + block + text[anchor:]
    ms.parse()
    return True


def remove(ms: MSBuildProject, name: str, cond: str | None = None) -> bool:
    """Remove the property element(s) (and a PropertyGroup left empty)."""
    want = _norm(cond) if cond else ""
    changed = False
    for g in reversed(_groups(ms)):
        gc = _norm(_group_condition(g[2]))
        if gc != want:
            continue
        text = ms.file.text
        body = text[g[3]:g[4]]
        m = re.search(rf"[ \t]*<{name}(\s[^>]*)?(?:/>|>.*?</{name}\s*>)[ \t]*(\r?\n)?", body, re.S)
        if not m or (m.group(1) and "Condition" in m.group(1)):
            continue
        a, b = g[3] + m.start(), g[3] + m.end()
        ms.file.text = text[:a] + text[b:]
        changed = True
        _drop_empty_group(ms)
        break
    if changed:
        ms.parse()
    return changed


def _drop_empty_group(ms: MSBuildProject) -> None:
    for g in reversed(_groups(ms)):
        t = ms.file.text
        if g[3] == g[4] or t[g[3]:g[4]].strip():
            continue
        gs, ge = g[0], g[1]
        ls = ms._line_start(gs)
        if t[ls:gs].strip() == "":
            gs = ls
            m = re.match(r"[ \t]*\r?\n", t[ge:])
            if m:
                ge += m.end()
        if t[:gs].endswith(ms.file.newline * 2):
            gs -= len(ms.file.newline)
        ms.file.text = t[:gs] + t[ge:]


# ====================================================================== global usings
def usings(ms: MSBuildProject) -> list[tuple[str, bool]]:
    """[(namespace, removed)] from <Using Include>/<Using Remove> items."""
    out = [(xml_unescape(i.include), False) for i in ms.explicit("Using")]
    out += [(xml_unescape(i.include), True) for i in ms.explicit("Using", "Remove")]
    return out


def add_using(ms: MSBuildProject, ns: str) -> bool:
    ns = ns.strip()
    if not re.fullmatch(r"[A-Za-z_][\w.]*", ns):
        raise ValueError(f"'{ns}' is not a namespace")
    return ms.add_item("Using", ns)


def remove_using(ms: MSBuildProject, ns: str) -> bool:
    return ms.remove_item("Using", ns)


# ====================================================================== build events
_TARGET_RX = r'<Target\s+Name="{name}"[^>]*>\s*<Exec\s+Command="(.*?)"\s*/>\s*</Target>'


def build_event(ms: MSBuildProject, which: str) -> str:
    """which = 'pre' | 'post'. The command line(s) of the build event."""
    if not ms.is_sdk:
        return ms.prop("PreBuildEvent" if which == "pre" else "PostBuildEvent")
    name = "PreBuild" if which == "pre" else "PostBuild"
    m = re.search(_TARGET_RX.format(name=name), ms.file.text, re.S)
    return _unent(m.group(1)) if m else ""


def _ent(s: str) -> str:
    return xml_escape(s).replace("\r\n", "&#xD;&#xA;").replace("\n", "&#xD;&#xA;")


def _unent(s: str) -> str:
    return xml_unescape(s.replace("&#xD;&#xA;", "\n").replace("&#xA;", "\n").replace("&#xD;", ""))


def set_build_event(ms: MSBuildProject, which: str, command: str) -> bool:
    command = (command or "").strip("\r\n")
    if not ms.is_sdk:
        name = "PreBuildEvent" if which == "pre" else "PostBuildEvent"
        return set_value(ms, name, command)
    name = "PreBuild" if which == "pre" else "PostBuild"
    when = 'BeforeTargets="PreBuildEvent"' if which == "pre" else 'AfterTargets="PostBuildEvent"'
    text, nl, unit = ms.file.text, ms.file.newline, ms._indent_unit()
    m = re.search(r"[ \t]*" + _TARGET_RX.format(name=name) + r"[ \t]*(\r?\n)?", text, re.S)
    if m:
        if not command:
            a = m.start()
            if text[:a].endswith(nl * 2):
                a -= len(nl)
            ms.file.text = text[:a] + text[m.end():]
        else:
            s, e = m.span(1)
            if _unent(m.group(1)) == command:
                return False
            ms.file.text = text[:s] + _ent(command) + text[e:]
        ms.parse()
        return True
    if not command:
        return False
    block = (f"{nl}{unit}<Target Name=\"{name}\" {when}>{nl}{unit}{unit}<Exec Command=\"{_ent(command)}\" />{nl}"
             f"{unit}</Target>{nl}")
    end = text.rfind("</Project>")
    if end < 0:
        return False
    ls = text.rfind("\n", 0, end) + 1
    ms.file.text = text[:ls] + block + text[ls:]
    ms.parse()
    return True


# ====================================================================== Directory.Build.*
def directory_build_files(folder: Path, stop: Path | None = None) -> list[Path]:
    """Directory.Build.props and Directory.Build.targets MSBuild imports for a project in *folder*
    (the nearest of each, walking up)."""
    out = []
    for name in ("Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props"):
        cur = Path(folder).resolve()
        while True:
            p = cur / name
            if p.is_file():
                out.append(p)
                break
            if stop is not None and cur == Path(stop).resolve().parent:
                break
            if cur.parent == cur:
                break
            cur = cur.parent
    return out


_INHERIT_CACHE: dict = {}


def inherited(ms: MSBuildProject, name: str) -> tuple[str | None, Path | None]:
    """(value, file) of a property set in a Directory.Build.props above the project."""
    for p in directory_build_files(ms.folder):
        if p.name != "Directory.Build.props":
            continue
        try:
            st = p.stat().st_mtime_ns
            key = (str(p), st)
            props = _INHERIT_CACHE.get(key)
            if props is None:
                dp = MSBuildProject(p, TextFile.read(p))
                props = dict(dp.properties)
                _INHERIT_CACHE[key] = props
        except (OSError, ValueError):
            continue
        if name in props:
            return props[name], p
    return None, None
