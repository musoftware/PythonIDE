"""Tests of the assembly analyzer radide/asm_lint (no Qt):

* the corpus (corpus.py): every bad snippet gives its rule ids, no good snippet gives an error or a warning;
* quick fixes: applying the fix produces the expected text and the issue disappears;
* no false positives (errors / warnings) on the repository's assembly samples, the project templates and the
  runnable blocks of the Arabic assembly course;
* every rule has complete English + Arabic texts and no placeholder is left in produced messages;
* assembler message translation, project configuration, suppression comments;
* performance: a 5000+ line file re-analysed after an edit in < 200 ms.

Run:  python samples/Tests/Assembly/SmartLint/test_lint_corpus.py
"""
from __future__ import annotations

import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import corpus  # noqa: E402
from radide.asm_lint import RULES, apply_edits, explain, friendly, lint  # noqa: E402
from radide.asm_lint import config as C  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
ARABIC = re.compile(r"[؀-ۿ]")


def check(name: str, ok, detail="") -> bool:
    RESULTS.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{str(detail)[:900]}]"), flush=True)
    return bool(ok)


def errors_warnings(issues):
    return [i for i in issues if i.severity in ("error", "warning")]


# ============================================================================ 1. corpus
covered = set()
miss = []
for name, opts, code, expected in corpus.BAD:
    got = {i.rule for i in lint(code, None, **opts)}
    covered |= got & expected
    if not expected <= got:
        miss.append((name, sorted(expected - got), sorted(got)))
check(f"corpus: {len(corpus.BAD)} bad snippets give their rule ids", not miss, miss)
fp = []
for name, opts, code in corpus.GOOD:
    bad = errors_warnings(lint(code, None, **opts))
    if bad:
        fp.append((name, [(i.line + 1, i.rule, i.message()) for i in bad]))
check(f"corpus: {len(corpus.GOOD)} good snippets give no error / warning", not fp, fp)
check(f"corpus covers at least 45 rules ({len(covered)} of {len(RULES)})", len(covered) >= 45,
      sorted(set(RULES) - covered))
dialects = {o.get("dialect") for _n, o, _c, _e in corpus.BAD} | {"emu8086" for _n, o, _c, _e in corpus.BAD
                                                                 if o.get("project_lang") == "emu8086"}
check("corpus covers NASM, MASM, FASM, GNU as and emu8086", {"nasm", "masm", "fasm", "gas", "emu8086"} <= dialects,
      dialects)

# ============================================================================ 2. texts
incomplete = [r.id for r in RULES.values() if not all((r.msg_en, r.msg_ar, r.why_en, r.why_ar, r.fix_en, r.fix_ar))]
check("every rule has message / why / fix in English and Arabic", not incomplete, incomplete)
not_arabic = [r.id for r in RULES.values() if not (ARABIC.search(r.fix_ar) and (ARABIC.search(r.why_ar) or
                                                                               re.fullmatch(r"\{\w+\}", r.why_ar)))]
check("Arabic texts are Arabic", not not_arabic, not_arabic)
left = []
for name, opts, code, _e in corpus.BAD:
    for it in lint(code, None, **opts):
        if not (ARABIC.search(it.message("ar")) and ARABIC.search(it.why("ar"))):
            left.append((it.rule, "ar", "no Arabic text: " + it.message("ar")[:60]))
        for lang in ("en", "ar"):
            for txt in (it.message(lang), it.why(lang), it.fix_text(lang)):
                if re.search(r"\{[a-z_]+\}", txt):
                    left.append((it.rule, lang, txt[:80]))
check("no placeholder is left in produced texts", not left, left[:6])
it = lint(corpus.nasm64("    mov eax, bl"), None, dialect="nasm")[0]
md_ar, md_en = it.markdown("ar"), it.markdown("en")
check("Arabic explanation: why + how + English message + Learn more",
      "لماذا" in md_ar and "كيف أصلحه" in md_ar and "Operand sizes" in md_ar and "اعرف المزيد" in md_ar, md_ar)
check("English explanation: Why? / How to fix / Learn more", "**Why?**" in md_en and "How to fix" in md_en and
      "Learn more" in md_en, md_en)
check("explanation links the reference and the course lesson", it.learn_url().startswith("https://") and
      it.lesson() == "03-registers-memory", (it.learn_url(), it.lesson()))

# ============================================================================ 3. quick fixes
FIXES = [
    ("ASM101", corpus.W64, corpus.nasm64("    mov eax, bl"), "movzx eax, bl"),
    ("ASM102", corpus.W64, corpus.nasm64("    mov [val], 1"), "mov dword [val], 1"),
    ("ASM111", corpus.W64, corpus.nasm64("    movsx rax, ecx"), "movsxd rax, ecx"),
    ("ASM112", corpus.W64, corpus.nasm64("    lea rcx, msg\n    call puts"), "lea rcx, [msg]"),
    ("ASM114", corpus.W64, corpus.nasm64("    mov eax, 1\n    push rax\n    push eax\n    pop rax\n    pop rax"),
     "push rax\n    pop rax\n    pop rax"),
    ("ASM117", corpus.W64, corpus.nasm64("    mov eax, 7\n    xor edx, edx\n    div 10"), "mov ecx, 10\n    div ecx"),
    ("ASM119", corpus.W64, corpus.nasm64("    lea rbx, [arr]\n    mov eax, [ebx]"), "mov eax, [rbx]"),
    ("ASM201", corpus.W64, corpus.nasm64("    mov ecx, 3\nagain:\n    dec ecx\n    jnz agian"), "jnz again"),
    ("ASM202", corpus.W64, corpus.nasm64("    lea rcx, [msg]\n    call strlen"), "extern strlen"),
    ("ASM206", corpus.W64, corpus.nasm64("    mov eax, [val]", head=""), "default rel\nglobal main"),
    ("ASM307", corpus.W64, corpus.nasm64("    mov eax, [val]\n    jz .zero\n.zero:"), "test eax, eax\n    jz .zero"),
    ("ASM403", corpus.W64, corpus.nasm64("    mov eax, 100\n    mov ecx, 3\n    div ecx"),
     "xor edx, edx\n    div ecx"),
    ("ASM509", corpus.W64, corpus.nasm64("    mov rcx, [msg]\n    call puts"), "lea rcx, [msg]"),
    ("ASM110", corpus.EMU, corpus.com("    mov ds, 1234h\n    ret"), "mov ax, 1234h\n    mov ds, ax"),
    ("ASM118", corpus.EMU, corpus.com("    push 5\n    pop ax\n    ret"), "mov ax, 5\n    push ax"),
    ("ASM601", corpus.EMU, ".model small\n.stack 100h\n.data\nmsg db 'hi$'\n.code\nstart:\n    mov ah, 9\n"
                           "    mov dx, offset msg\n    int 21h\n    mov ah, 4Ch\n    int 21h\nend start\n",
     "start:\n    mov ax, @data\n    mov ds, ax\n    mov ah, 9"),
    ("ASM602", corpus.EMU, "org 100h\n    mov ah, 2\n    mov dl, 'A'\n    int 21h\n",
     "int 21h\n    mov ah, 4Ch\n    int 21h"),
    ("ASM605", corpus.EMU, corpus.com("    mov ah, 9\n    mov dx, offset text\n    int 21h\n    ret",
                                      "text db 'hello'"), "text db 'hello', '$'"),
    ("ASM101", corpus.GAS, "    .text\n    .globl main\nmain:\n    subq $40, %rsp\n    movl %rax, %rbx\n"
                           "    addq $40, %rsp\n    ret\n", "movq %rax, %rbx"),
]
for rule_id, opts, code, want in FIXES:
    iss = [i for i in lint(code, None, **opts) if i.rule == rule_id]
    if not check(f"{rule_id} has a quick fix", iss and iss[0].fixes, [i.rule for i in lint(code, None, **opts)]):
        continue
    new = apply_edits(code, iss[0].fixes[0].edits)
    ok_text = want in new
    still = [i for i in lint(new, None, **opts) if i.rule == rule_id and i.line == iss[0].line]
    check(f"{rule_id} fix '{iss[0].fixes[0].title('en')}' gives '{want.splitlines()[0]}' and removes the issue",
          ok_text and not still, (new if not ok_text else [s.message() for s in still]))
ar_titles = [f.title("ar") for it in lint(corpus.nasm64("    mov eax, bl"), None, dialect="nasm") for f in it.fixes]
check("quick fix titles exist in Arabic", ar_titles and all(ARABIC.search(t) for t in ar_titles), ar_titles)

# ============================================================================ 4. no false positives
git = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "samples/Tests/Assembly"], cwd=ROOT,
                     capture_output=True, text=True).stdout.split()
skip = ("SmartSim/buggy", "SmartLint/NasmMistakes", "SmartLint/Emu8086Mistakes", "CoreErrorList")
srcs = [ROOT / f for f in git if f.lower().endswith((".asm", ".s")) and not any(s in f for s in skip)]
fps = []
for f in srcs:
    bad = errors_warnings(lint(f.read_text(encoding="utf-8", errors="replace"), f))
    if bad:
        fps.append((f.relative_to(ROOT).as_posix(), [(i.line + 1, i.rule, i.message()) for i in bad]))
check(f"no errors / warnings on {len(srcs)} sample sources", not fps and len(srcs) >= 35, fps)
err_list = ROOT / "samples/Tests/Assembly/CoreErrorList/main.asm"
check("CoreErrorList's deliberate mistake is found", any(i.rule == "ASM116" for i in lint(err_list.read_text(
    encoding="utf-8"), err_list)))
from radide.asm import templates as T  # noqa: E402
tfp = []
for t in T.TEMPLATES:
    for fname, body in t.files:
        if fname.endswith((".asm", ".s")):
            try:
                code = body.format(name="Demo", form="Form1")
            except (KeyError, IndexError, ValueError):
                code = body
            bad = errors_warnings(lint(code, None, dialect=t.settings.get("assembler")))
            if bad:
                tfp.append((t.id, [(i.line + 1, i.rule) for i in bad]))
for flavor in T.FORM_CODE:
    bad = errors_warnings(lint(T.form_code("Form1", flavor), None))
    if bad:
        tfp.append((flavor, [(i.line + 1, i.rule) for i in bad]))
check("no errors / warnings on the project templates", not tfp, tfp)
from radide import tutorials  # noqa: E402
course = tutorials.course("assembly")
blocks = cfp = 0
cfps = []
mistakes = []
for les in course.lessons:
    for b in les.blocks():
        if b.lang not in ("asm", "asm16"):
            continue
        opts = corpus.EMU if b.lang == "asm16" else corpus.W64
        bad = errors_warnings(lint(b.code, None, **opts))
        if b.role in ("run", "solution"):
            blocks += 1
            if bad:
                cfps.append((les.id, b.index, [(i.line + 1, i.rule) for i in bad]))
        elif bad:
            mistakes.append((les.id, sorted({i.rule for i in bad})))
check(f"no errors / warnings on {blocks} runnable course blocks", not cfps and blocks >= 50, cfps)
check("the course's 'this is wrong' examples are recognised (ASM101 ASM102 ASM103)",
      {"ASM101", "ASM102", "ASM103"} <= {r for _l, rs in mistakes for r in rs}, mistakes)

# ============================================================================ 5. assembler messages
MSGS = [
    "main.asm:12: error: invalid combination of opcode and operands",
    "main.asm:7: error: operation size not specified",
    "main.asm(9) : error A2006:undefined symbol : count",
    "main.asm(4) : error A2022:instruction operands must be the same size",
    "error: undefined symbol 'loop1'.",
    "main.s:5: Error: no such instruction: `movz eax,1'",
    "main.s:8: Error: operand type mismatch for `mov'",
    "main.obj:main.asm:(.text+0x11): undefined reference to `printf2'",
    "main.obj : error LNK2019: unresolved external symbol foo referenced in function main",
    "main.asm:3: warning: label alone on a line without a colon might be in error [-w+label-orphan]",
]
unexplained = [m for m in MSGS if explain(m) is None]
check(f"{len(MSGS)} assembler / linker messages get an explanation", not unexplained, unexplained)
f = friendly("main.asm(9) : error A2006:undefined symbol : count", "ar")
check("friendly Arabic text names the symbol and keeps the original", "count" in f and ARABIC.search(f) and
      "A2006" in f, f)
check("explanation of a GAS message has why / fix in Arabic",
      all(ARABIC.search(x) for x in (explain(MSGS[5]).why_ar, explain(MSGS[5]).fix_ar)))

# ============================================================================ 6. configuration and suppression
code = corpus.nasm64("    mov eax, bl\n    mov [val], 1")
check("rule switched off in the configuration", not [i for i in lint(code, None, dialect="nasm",
                                                                      config={"rules": {"ASM101": "off"}})
                                                      if i.rule == "ASM101"])
lv = [i.severity for i in lint(code, None, dialect="nasm", config={"rules": {"ambiguous-memory-size": "info"}})
      if i.rule == "ASM102"]
check("severity changed by rule name", lv == ["info"], lv)
check("analyzer disabled for the project", lint(code, None, dialect="nasm", config={"enabled": False}) == [])
sup = corpus.nasm64("    ; asmlint-disable-next-line ASM101\n    mov eax, bl\n    mov [val], 1   ; asmlint-disable-line")
got = {i.rule for i in lint(sup, None, dialect="nasm")}
check("suppression comments: next line / this line", "ASM101" not in got and "ASM102" not in got, got)
got = {i.rule for i in lint("; asmlint-disable-file ASM102\n" + code, None, dialect="nasm")}
check("suppression comment for the whole file", "ASM102" not in got and "ASM101" in got, got)
import json  # noqa: E402
import tempfile  # noqa: E402
tmp = Path(tempfile.mkdtemp(prefix="asmlint-"))
(tmp / "project.radproj").write_text(json.dumps({"name": "T", "language": "asm-nasm"}), encoding="utf-8")
(tmp / "main.asm").write_text(code, encoding="utf-8")
C.save_project_config(tmp / "main.asm", {"enabled": True, "rules": {"ASM102": "off"}})
saved = json.loads((tmp / "project.radproj").read_text(encoding="utf-8"))
check("project configuration saved in project.radproj (other keys kept)", saved.get("asm_lint", {}).get("rules") ==
      {"ASM102": "off"} and saved.get("language") == "asm-nasm", saved)
got = {i.rule for i in lint(code, tmp / "main.asm")}
check("project configuration applied", "ASM102" not in got and "ASM101" in got, got)

# ============================================================================ 7. performance
def big(n=250):
    out = ["default rel", "global main", "extern printf", "section .data", "    fmt db '%d', 10, 0",
           "    table dd 1, 2, 3, 4, 5, 6, 7, 8", "section .text", "main:", "    push rbx", "    sub rsp, 32"]
    out += [f"    call func{i}" for i in range(n)]
    out += ["    add rsp, 32", "    pop rbx", "    xor eax, eax", "    ret", ""]
    for i in range(n):
        out += [f"func{i}:", "    push rbx", "    sub rsp, 32", "    xor ebx, ebx", "    lea rcx, [table]", ".loop:",
                "    mov eax, [rcx+rbx*4]", "    add eax, ebx", "    cmp eax, 100", "    jg .big", "    inc ebx",
                "    cmp ebx, 8", "    jl .loop", ".big:", "    lea rcx, [fmt]", "    mov edx, eax", "    call printf",
                "    add rsp, 32", "    pop rbx", "    ret", ""]
    return out


lines = big()
lint("\n".join(lines), None, dialect="nasm")
times = []
for k in range(7):
    lines[2500 + 20 * k] += "  ; edited"
    t0 = time.perf_counter()
    res = lint("\n".join(lines), None, dialect="nasm")
    times.append((time.perf_counter() - t0) * 1000)
med = statistics.median(times)
check(f"{len(lines)}-line file re-analysed after an edit in < 200 ms (median {med:.0f} ms)", med < 200 and
      len(lines) >= 5000, [f"{t:.0f}" for t in times])
check("the big correct file has no errors / warnings", not errors_warnings(res), [i.rule for i in res][:5])

ok = sum(1 for _n, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
