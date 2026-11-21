"""Results of a runtime check: ``Finding`` (one problem at one line) and ``SimResult`` (the whole run)."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import messages as M


@dataclass
class Finding:
    rule: str                       # sim.*
    file: str
    line: int                       # 1-based (0 = unknown)
    args: dict = field(default_factory=dict)
    severity: str = ""
    addr: int | None = None
    instr: str = ""
    ref: str = ""                   # override of the rule's reference topic (an instruction name)
    col: int = 0
    end_col: int = 0

    def __post_init__(self):
        if not self.severity:
            self.severity = M.severity(self.rule)

    def _args(self) -> dict:
        a = dict(self.args)
        a.setdefault("instr", self.instr)
        return a

    def message(self, lang: str = "en") -> str:
        return M.text(self.rule, "msg", lang, **self._args())

    def why(self, lang: str = "en") -> str:
        return M.text(self.rule, "why", lang, **self._args())

    def fix(self, lang: str = "en") -> str:
        return M.text(self.rule, "fix", lang, **self._args())

    def reference(self) -> dict:
        return M.ref_of(self.rule, self.ref)

    def to_dict(self, lang: str = "en") -> dict:
        """The diagnostics shape shared with radide/asm_lint (docs/ASSEMBLY.md, "Smart checks")."""
        ref = self.reference()
        return {"rule": self.rule, "source": "sim", "file": self.file, "line": self.line, "col": self.col,
                "end_col": self.end_col, "severity": self.severity,
                "message": self.message(lang), "why": self.why(lang), "fix": self.fix(lang),
                "message_en": self.message("en"), "message_ar": self.message("ar"),
                "why_en": self.why("en"), "why_ar": self.why("ar"), "fix_en": self.fix("en"), "fix_ar": self.fix("ar"),
                "ref": ref.get("topic", ""), "ref_url": ref.get("url", ""),
                "addr": self.addr, "instr": self.instr}

    def markdown(self, lang: str = "en", with_english: bool = True) -> str:
        """The full explanation (marker hover / details pane): message, why, how to fix, reference."""
        ref = self.reference()
        sev = {"error": ("Runtime error", "خطأ أثناء التشغيل"), "warning": ("Runtime warning", "تحذير أثناء التشغيل"),
               "info": ("Note", "ملاحظة")}.get(self.severity, ("Note", "ملاحظة"))
        if lang == "ar":
            out = [f"**{sev[1]} {self.rule}** — {self.message('ar')}"]
            if with_english:
                out.append(f"*{self.message('en')}*")
            out += ["", f"**ماذا حدث؟** {self.why('ar')}", "", f"**كيف أصلحه؟** {self.fix('ar')}"]
            if ref.get("url"):
                out += ["", f"[المرجع: {ref.get('title_ar') or ref.get('topic')}]({ref['url']})"]
        else:
            out = [f"**{sev[0]} {self.rule}** — {self.message('en')}", "", f"**What happened?** {self.why('en')}",
                   "", f"**How to fix:** {self.fix('en')}"]
            if ref.get("url"):
                out += ["", f"[Reference: {ref.get('topic', '').upper()}]({ref['url']})"]
        return "\n".join(out)

    def issue_dict(self, lang: str = "en") -> dict:
        """The same shape as radide/asm_lint ``Issue.to_dict`` (0-based line), with ``source = "sim"``."""
        ref = self.reference()
        line0 = max(0, self.line - 1)
        return {"rule": self.rule, "name": self.rule.split(".", 1)[-1], "severity": self.severity, "line": line0,
                "col": self.col, "endLine": line0, "endCol": self.end_col or 1000,
                "message": f"{self.rule}: {self.message(lang)}", "message_en": self.message("en"),
                "message_ar": self.message("ar"), "why": self.why(lang), "fix": self.fix(lang),
                "markdown": self.markdown(lang), "url": ref.get("url", ""), "lesson": "", "mnem": ref.get("topic", ""),
                "source": "sim", "fixes": [], "file": self.file}


@dataclass
class CallLog:
    name: str
    args: str
    result: str
    line: int
    file: str = ""


@dataclass
class SimResult:
    status: str = "ok"              # ok | findings | asm_error | unavailable | unsupported | error
    engine: str = ""                # unicorn | emu8086
    abi: str = ""
    findings: list[Finding] = field(default_factory=list)
    output: str = ""                # what the program printed
    calls: list[CallLog] = field(default_factory=list)
    steps: int = 0
    exit_code: int | None = None
    ended: str = ""                 # return | exit | fault | limit | input | stopped
    note_en: str = ""
    note_ar: str = ""
    errors: list[str] = field(default_factory=list)   # assembler messages (status asm_error)
    entry: str = ""
    lines_run: set = field(default_factory=set)       # (file lower, line) executed at least once

    def note(self, lang: str = "en") -> str:
        return self.note_ar if lang == "ar" and self.note_ar else self.note_en

    def add(self, f: Finding) -> None:
        for g in self.findings:
            if g.rule == f.rule and g.line == f.line and g.file == f.file:
                return
        self.findings.append(f)

    @property
    def problems(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in ("error", "warning")]

    def summary(self, lang: str = "en") -> str:
        n_err = sum(1 for f in self.findings if f.severity == "error")
        n_warn = sum(1 for f in self.findings if f.severity == "warning")
        if self.status in ("asm_error", "unavailable", "unsupported", "error"):
            return self.note(lang)
        if lang == "ar":
            end = {"return": "انتهى البرنامج طبيعياً", "exit": "انتهى البرنامج بالخروج",
                   "fault": "توقف البرنامج بسبب خطأ", "limit": "توقف الفحص عند حد التعليمات",
                   "input": "انتظر البرنامج إدخالاً", "stopped": "توقف الفحص"}.get(self.ended, self.ended)
            return (f"{end} بعد {self.steps} تعليمة"
                    + (f" (رمز الخروج {self.exit_code})" if self.exit_code is not None else "")
                    + f" - أخطاء: {n_err}، تحذيرات: {n_warn}")
        end = {"return": "The program finished normally", "exit": "The program exited",
               "fault": "The program stopped with a fault", "limit": "The check stopped at the instruction limit",
               "input": "The program waited for input", "stopped": "The check was stopped"}.get(self.ended, self.ended)
        return (f"{end} after {self.steps} instructions"
                + (f" (exit code {self.exit_code})" if self.exit_code is not None else "")
                + f" - errors: {n_err}, warnings: {n_warn}")
