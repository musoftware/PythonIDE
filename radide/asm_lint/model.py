"""Issues and quick fixes produced by the analyzer, with their bilingual texts (no Qt)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .rules import RULES, TOPICS, Rule


RLE, PDF = "‫", "‬"          # right-to-left embedding: Arabic lines read right to left in LTR widgets


def rtl(text: str) -> str:
    return RLE + text + PDF if text else text


class _Args(dict):
    """str.format_map helper: a missing placeholder stays visible instead of raising."""

    def __missing__(self, key):
        return "{" + key + "}"


def _fmt(template: str, args: dict) -> str:
    try:
        return template.format_map(_Args(args))
    except (ValueError, IndexError):
        return template


@dataclass
class Fix:
    """A quick fix: text edits on the current file. ``edits`` items: {"range": [l1, c1, l2, c2], "text": str}
    with 0-based lines / columns (the end is exclusive); an insertion has l1 == l2 and c1 == c2."""
    title_en: str
    title_ar: str
    edits: list = field(default_factory=list)

    def title(self, lang: str = "en") -> str:
        return self.title_ar if lang == "ar" and self.title_ar else self.title_en

    def to_dict(self, lang: str = "en") -> dict:
        return {"title": self.title(lang), "title_en": self.title_en, "title_ar": self.title_ar,
                "edits": [dict(e) for e in self.edits]}


@dataclass
class Issue:
    rule: str
    line: int                    # 0-based
    col: int                     # 0-based
    end_col: int
    args: dict = field(default_factory=dict)
    fixes: list = field(default_factory=list)
    severity: str = ""           # effective severity (rule default unless configured)
    end_line: int = -1
    mnem: str = ""               # instruction the issue is about ("Learn more")
    source: str = "lint"         # lint | assembler

    def __post_init__(self):
        if self.end_line < 0:
            self.end_line = self.line
        if not self.severity:
            r = RULES.get(self.rule)
            self.severity = r.severity if r else "warning"
        if self.end_col <= self.col and self.end_line == self.line:
            self.end_col = self.col + 1

    # ------------------------------------------------------------ texts
    @property
    def meta(self) -> Rule | None:
        return RULES.get(self.rule)

    def message(self, lang: str = "en") -> str:
        r = self.meta
        if r is None:
            return str(self.args.get("message", self.rule))
        return _fmt(r.msg_ar if lang == "ar" else r.msg_en, self.args)

    def why(self, lang: str = "en") -> str:
        r = self.meta
        if r is None:
            return ""
        return _fmt(r.why_ar if lang == "ar" else r.why_en, self.args)

    def fix_text(self, lang: str = "en") -> str:
        r = self.meta
        if r is None:
            return ""
        return _fmt(r.fix_ar if lang == "ar" else r.fix_en, self.args)

    def learn_url(self) -> str:
        r = self.meta
        return TOPICS.get(r.topic if r else "isa", TOPICS["isa"])

    def lesson(self) -> str:
        r = self.meta
        return r.lesson if r else ""

    def title(self, lang: str = "en") -> str:
        """'ASM101: message' (the Error List / squiggle text)."""
        return f"{self.rule}: {self.message(lang)}"

    def markdown(self, lang: str = "en", with_english: bool = True) -> str:
        """The full explanation (Monaco hover / Problems panel): message, why, how to fix, Learn more."""
        sev = {"error": ("Error", "خطأ"), "warning": ("Warning", "تحذير"), "info": ("Hint", "تلميح")}.get(
            self.severity, ("Note", "ملاحظة"))
        if lang == "ar":
            out = [rtl(f"**{sev[1]} {self.rule}** — {self.message('ar')}")]
            if with_english:
                out.append(f"*{self.message('en')}*")
            out += ["", rtl(f"**لماذا؟** {self.why('ar')}"), "", rtl(f"**كيف أصلحه؟** {self.fix_text('ar')}")]
            if self.fixes:
                out.append("")
                out.append(rtl("**إصلاح سريع (Ctrl+.):** " + " ، ".join(f.title("ar") for f in self.fixes)))
            out += ["", f"[{rtl('اعرف المزيد')}]({self.learn_url()})"]
        else:
            out = [f"**{sev[0]} {self.rule}** — {self.message('en')}", "", f"**Why?** {self.why('en')}", "",
                   f"**How to fix:** {self.fix_text('en')}"]
            if self.fixes:
                out.append("")
                out.append("**Quick fix (Ctrl+.):** " + ", ".join(f.title("en") for f in self.fixes))
            out += ["", f"[Learn more]({self.learn_url()})"]
        return "\n".join(out)

    def to_dict(self, lang: str = "en") -> dict:
        r = self.meta
        return {"rule": self.rule, "name": r.name if r else "", "severity": self.severity, "line": self.line,
                "col": self.col, "endLine": self.end_line, "endCol": self.end_col,
                "message": self.title(lang) if lang != "ar" else f"{self.rule}: {rtl(self.message('ar'))}",
                "message_en": self.message("en"), "message_ar": self.message("ar"),
                "why": self.why(lang), "fix": self.fix_text(lang), "markdown": self.markdown(lang),
                "url": self.learn_url(), "lesson": self.lesson(), "mnem": self.mnem, "source": self.source,
                "fixes": [f.to_dict(lang) for f in self.fixes]}


def insert_lines(line: int, texts: list[str], indent: str) -> dict:
    """An edit inserting whole lines before *line*."""
    return {"range": [line, 0, line, 0], "text": "".join(indent + t + "\n" for t in texts)}


def replace_line(line: int, old_len: int, texts: list[str], indent: str) -> dict:
    """An edit replacing the code of *line* (up to old_len) with one or more lines."""
    return {"range": [line, 0, line, old_len], "text": "\n".join(indent + t for t in texts)}


def apply_edits(text: str, edits: list[dict]) -> str:
    """Apply edits to *text* (tests and the IDE without Monaco). Edits must not overlap."""
    lines = text.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln) + 1)

    def off(l, c):
        l = max(0, min(l, len(lines) - 1))
        return offs[l] + min(c, len(lines[l]))

    out = text
    for e in sorted(edits, key=lambda e: (e["range"][0], e["range"][1]), reverse=True):
        l1, c1, l2, c2 = e["range"]
        a, b = off(l1, c1), off(l2, c2)
        out = out[:a] + e["text"] + out[b:]
    return out
