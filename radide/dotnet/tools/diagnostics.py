"""MSBuild / dotnet build diagnostics -> Error List (Analyze > Run Code Analysis, Build), and the diagnostic id
helpers the Error List context menu uses ("Configure severity", "Show error help", "Suppress").

    parse_build_output(text) -> [BuildDiag]     "File.cs(12,5): warning CA1822: message [proj]"
    diag_id(message) -> "CA1822" | ""          the rule id of an Error List row
    help_url(id)                               learn.microsoft.com page of a CS / CA / IDE rule
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_LINE = re.compile(r"^\s*(?P<file>[^\s(][^(]*?)\((?P<line>\d+)(?:,(?P<col>\d+))?(?:,\d+,\d+)?\)\s*:\s*"
                   r"(?P<sev>error|warning|info|hidden)\s+(?P<id>[A-Za-z]+\d+)\s*:\s*(?P<msg>.*?)"
                   r"(?:\s+\[(?P<proj>[^\]]+\.(?:cs|vb|fs)proj)(?:::[^\]]*)?\])?\s*$", re.I)
_NOFILE = re.compile(r"^\s*(?P<file>[^:]+?)\s*:\s*(?P<sev>error|warning)\s+(?P<id>[A-Za-z]+\d+)\s*:\s*(?P<msg>.*?)"
                     r"(?:\s+\[(?P<proj>[^\]]+)\])?\s*$", re.I)
_ID = re.compile(r"^\s*([A-Za-z]{2,}\d{3,5})\s*:|\b(CS\d{4}|CA\d{4}|IDE\d{4}|BC\d{5}|FS\d{4}|SA\d{4}|xUnit\d{4}|"
                 r"NUnit\d{4}|MSTEST\d{4}|SYSLIB\d{4}|RS\d{4}|S\d{3,4}|NU\d{4}|MSB\d{4}|NETSDK\d{4})\b")


@dataclass
class BuildDiag:
    severity: str            # Error | Warning | Message
    id: str
    message: str
    file: str
    line: int
    col: int = 0
    project: str = ""

    def row_message(self) -> str:
        return f"{self.id}: {self.message}" if self.id else self.message


def parse_build_output(text: str) -> list[BuildDiag]:
    out, seen = [], set()
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if m:
            sev = m.group("sev").lower()
            d = BuildDiag({"error": "Error", "warning": "Warning"}.get(sev, "Message"), m.group("id"),
                          _strip_url(m.group("msg")), m.group("file").strip(), int(m.group("line")),
                          int(m.group("col") or 0), m.group("proj") or "")
        else:
            m = _NOFILE.match(raw)
            if not m or m.group("file").strip().lower().startswith(("http", "build")):
                continue
            d = BuildDiag("Error" if m.group("sev").lower() == "error" else "Warning", m.group("id"),
                          _strip_url(m.group("msg")), "", 0, 0, m.group("proj") or "")
        key = (d.severity, d.id, d.message, d.file.lower(), d.line, d.col)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def _strip_url(msg: str) -> str:
    return re.sub(r"\s*\(https?://[^)]+\)\s*$", "", msg).strip()


def diag_id(message: str) -> str:
    m = _ID.search(message or "")
    return (m.group(1) or m.group(2)) if m else ""


def help_url(rule: str) -> str:
    r = rule.upper()
    low = rule.lower()
    if r.startswith("CS"):
        return f"https://learn.microsoft.com/dotnet/csharp/misc/{low}"
    if r.startswith("CA"):
        return f"https://learn.microsoft.com/dotnet/fundamentals/code-analysis/quality-rules/{low}"
    if r.startswith("IDE"):
        return f"https://learn.microsoft.com/dotnet/fundamentals/code-analysis/style-rules/{low}"
    if r.startswith("BC"):
        return f"https://learn.microsoft.com/dotnet/visual-basic/language-reference/error-messages/{low}"
    if r.startswith("NU"):
        return f"https://learn.microsoft.com/nuget/reference/errors-and-warnings/{low}"
    if r.startswith("NETSDK"):
        return f"https://learn.microsoft.com/dotnet/core/tools/sdk-errors/{low}"
    if r.startswith("SYSLIB"):
        return f"https://learn.microsoft.com/dotnet/fundamentals/syslib-diagnostics/{low}"
    if low.startswith("xunit"):
        return f"https://xunit.net/xunit.analyzers/rules/{rule}"
    return f"https://www.bing.com/search?q={rule}"


def analysis_argv(target, configuration: str = "Debug") -> list[str]:
    """A rebuild that runs every analyzer (Analyze > Run Code Analysis)."""
    from . import sdk
    return [sdk.dotnet() or "dotnet", "build", str(target), "-c", configuration, "-nologo", "--no-incremental",
            "-v:q", "-clp:NoSummary", "-p:RunAnalyzersDuringBuild=true", "-p:EnforceCodeStyleInBuild=true"]


__all__ = ["BuildDiag", "parse_build_output", "diag_id", "help_url", "analysis_argv"]
