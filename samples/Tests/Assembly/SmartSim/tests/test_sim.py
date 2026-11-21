"""Headless tests of the runtime checks (radide/asm_sim): Check by running, Explain this line, What-if.

Run:  python samples/Tests/Assembly/SmartSim/tests/test_sim.py
Needs NASM (the IDE downloads it: Tools > Assembly Toolchains) and the 'unicorn' + 'capstone' pip packages.

* every program in ../buggy has ``; EXPECT: sim.rule`` on the line where the mistake must be reported;
* the programs in ../correct must run without a runtime error / warning and print the expected text;
* every finding has English + Arabic message / why / fix and a reference link;
* explanations of a set of instructions (values before -> after, flag reasons, jump taken / not taken);
* Check This Procedure / Check Selection / a module without main / an unsupported dialect.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
ROOT = SAMPLE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.asm_sim import check as CK  # noqa: E402
from radide.asm_sim.explain import condition_text, explain_step  # noqa: E402
from radide.asm_sim.whatif import parse_values, whatif  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
ARABIC = re.compile(r"[؀-ۿ]")


def check(name: str, ok, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(ok)


def expectations(text: str) -> dict:
    out = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = re.search(r"EXPECT:\s*(.*)$", line)
        if m:
            for rule in m.group(1).split():
                out[rule] = i
    return out


def test_buggy():
    for p in sorted((SAMPLE / "buggy").glob("*.asm")):
        text = p.read_text(encoding="utf-8")
        exp = expectations(text)
        t0 = time.time()
        r = CK.check(text, str(p), stdin="3\n", max_steps=400_000)
        got = {(f.rule, f.line) for f in r.findings}
        missing = [(rule, ln) for rule, ln in exp.items() if (rule, ln) not in got]
        check(f"buggy/{p.name}: {', '.join(exp)} at the right line ({time.time() - t0:.1f}s)", not missing,
              f"missing {missing}; got {sorted(got)}; status {r.status} {r.note_en}")
        for f in r.findings:
            texts = [f.message("en"), f.why("en"), f.fix("en"), f.message("ar"), f.why("ar"), f.fix("ar")]
            ok = all(texts) and all("{" not in t for t in texts) and ARABIC.search(f.why("ar")) and \
                not ARABIC.search(f.why("en")) and f.reference().get("url")
            if not ok:
                check(f"buggy/{p.name}: {f.rule} texts complete (en + ar + reference)", False, texts)
                break
        else:
            check(f"buggy/{p.name}: texts complete (en + ar + reference)", bool(r.findings))


CORRECT_OUTPUT = {"procedures_x64.asm": "sum = 108, average = 18, copy[5] = 42",
                  "cdecl_x86.asm": "12 * 12 = 144", "linux_syscalls.asm": "Hello from Linux!", "dos_sum.asm": "",
                  "tail_call_x64.asm": "tail call"}


def test_correct():
    for p in sorted((SAMPLE / "correct").glob("*.asm")):
        r = CK.check(p.read_text(encoding="utf-8"), str(p))
        bad = [(f.rule, f.line, f.message()) for f in r.problems]
        check(f"correct/{p.name}: no runtime findings ({r.abi}, {r.ended})", not bad and r.status == "ok", bad)
        want = CORRECT_OUTPUT.get(p.name, "")
        if want:
            check(f"correct/{p.name}: output", want in r.output, r.output)
    # the IDE's own templates / samples
    for rel in ("CoreNasmConsoleX64/main.asm", "CoreNasmConsoleX86/main.asm", "CoreNasmWinApi/main.asm",
                "Emu8086SumArray/main.asm", "Emu8086Factorial/main.asm", "Emu8086BubbleSort/main.asm"):
        p = SAMPLE.parent / rel
        r = CK.check(p.read_text(encoding="utf-8"), str(p), stdin="6\n")
        check(f"sample {rel}: no runtime findings", not r.problems and r.status == "ok",
              [(f.rule, f.line) for f in r.findings] + [r.note_en])
    p = SAMPLE.parent / "CoreNasmConsoleX64/main.asm"
    r = CK.check(p.read_text(encoding="utf-8"), str(p), stdin="6\n")
    check("CoreNasmConsoleX64: output with the given input", "6 squared is 36" in r.output and "= 21" in r.output,
          r.output)
    check("CoreNasmConsoleX64: calls logged with their line", any(c.name == "scanf" and c.line == 44 for c in r.calls),
          [(c.name, c.line) for c in r.calls])


def test_scopes():
    p = SAMPLE / "correct" / "procedures_x64.asm"
    text = p.read_text(encoding="utf-8")
    line = next(i for i, s in enumerate(text.splitlines(), 1) if s.startswith("sum:")) + 3
    r = CK.check(text, str(p), proc_line=line, init_regs={"rcx": 0, "rdx": 3})
    check("Check This Procedure: sum(NULL, 3) -> null pointer read", any(f.rule == "sim.null_deref" for f in r.findings),
          [(f.rule, f.line) for f in r.findings])
    check("Check This Procedure: entry is the procedure", r.entry == "sum", r.entry)
    r = CK.check(text, str(p), proc_line=line, init_regs={"rcx": 0x10000020, "rdx": 0})
    check("Check This Procedure: sum(p, 0) returns 0 cleanly", r.status == "ok" and r.exit_code == 0,
          (r.status, r.exit_code, [(f.rule, f.line) for f in r.findings]))
    src = text.splitlines()
    l1 = next(i for i, s in enumerate(src, 1) if "cdq" in s)
    r = CK.check(text, str(p), lines=(l1 - 1, l1 + 3), init_regs={"rax": 100})
    check("Check Selection: runs only the selected lines", r.status == "ok" and r.steps <= 6 and r.ended == "return",
          (r.status, r.steps, r.ended))
    stats = SAMPLE.parent / "CourseNumberAnalyzer" / "stats.asm"
    r = CK.check(stats.read_text(encoding="utf-8"), str(stats))
    check("a module without main explains how to check one procedure", r.status == "error" and "procedure" in r.note_en
          and ARABIC.search(r.note_ar), r.note_en)
    fasm = SAMPLE.parent / "CoreFasmX64" / "main.asm"
    r = CK.check(fasm.read_text(encoding="utf-8"), str(fasm))
    check("FASM source: unsupported with a bilingual note", r.status == "unsupported" and ARABIC.search(r.note_ar),
          r.note_en)
    r = CK.check("default rel\nglobal main\nsection .text\nmain:\n  mov eax, [nothere]\n  ret\n", "bad.asm")
    check("assembler errors are reported instead of running", r.status == "asm_error" and r.errors, r.errors)


def test_explain():
    p = SAMPLE / "correct" / "procedures_x64.asm"
    text = p.read_text(encoding="utf-8")
    src = text.splitlines()
    ln = next(i for i, s in enumerate(src, 1) if "add eax, [rcx + rbx*4]" in s)
    info = CK.explain_line(text, str(p), ln, iteration=1)
    st = info["steps"][0] if info["steps"] else {}
    check("explain_line: 6 executions, the 2nd one explained", info["ok"] and info["count"] == 6 and
          info["iteration"] == 2, (info["ok"], info["count"], info["iteration"], info["note_en"]))
    check("explain_line: EAX 4 -> 12 (4 + 8)", "EAX: 4 -> 0xc (12)" in st.get("summary_en", ""), st.get("summary_en"))
    check("explain_line: Arabic summary", ARABIC.search(st.get("summary_ar", "")) and "EAX" in st.get("summary_ar", ""),
          st.get("summary_ar"))
    ln = next(i for i, s in enumerate(src, 1) if "cmp ebx, edx" in s)
    info = CK.explain_line(text, str(p), ln, iteration=-1)
    j = info["steps"][0].get("jump") if info["steps"] else None
    check("explain_line: the last 'cmp ebx, edx' -> 'jge .done' is taken (6 >= 6)",
          j and j["taken"] and "6 >= 6 is true" in j["en"] and ARABIC.search(j["ar"]), j)
    info = CK.explain_line(text, str(p), 4)
    check("explain_line on a comment line says there is nothing to explain", not info["ok"] and info["note_en"],
          info)
    dos = SAMPLE / "correct" / "dos_sum.asm"
    t = dos.read_text(encoding="utf-8")
    ln = next(i for i, s in enumerate(t.splitlines(), 1) if "add ax, [si]" in s)
    info = CK.explain_line(t, str(dos), ln, iteration=-1)
    st = info["steps"][0] if info["steps"] else {}
    check("explain_line 8086: last 'add ax, [si]' AX 100 -> 150", info["ok"] and "AX: 0x64 (100) -> 0x96 (150)" in
          st.get("summary_en", ""), st.get("summary_en"))


WHATIF = [
    # code, values, bits, expected english substrings, expected arabic substrings
    ("add eax, ebx", "eax=5 ebx=7", 32, ["EAX: 5 -> 0xc (12)", "ZF=0", "CF=0", "no carry"], ["لا يوجد حمل", "ليس صفراً"]),
    ("add al, 1", "al=0xFF", 32, ["AL: 0xff", "-> 0", "ZF=1", "CF=1", "does not fit in 8 bits"], ["حمل بدون إشارة"]),
    ("sub eax, 7", "eax=5", 32, ["CF=1", "borrow: 5 < 7", "SF=1"], ["استلاف"]),
    ("inc ax", "ax=0x7FFF", 16, ["OF=1", "signed overflow", "INC does not change CF"], ["فيضان بإشارة"]),
    ("xor ecx, ecx", "ecx=9", 32, ["ECX: 9 -> 0", "ZF=1", "XOR always clears CF"], ["الطريقة المعتادة لتصفيره"]),
    ("shl eax, 1", "eax=0x80000001", 32, ["CF = the last bit shifted out (1)", "EAX: 0x80000001"], ["آخر بت"]),
    ("cmp ecx, 10\njl less\nless:", "ecx=3", 32, ["'jl less' will be TAKEN", "3 < 10 is true"], ["سيقفز"]),
    ("cmp ecx, 10\njae big\nbig:", "ecx=-1", 32, ["'jae big' will be TAKEN", "(unsigned)", "4294967295 >= 10"], ["بدون إشارة"]),
    ("test eax, eax\njz zero\nzero:", "eax=0", 32, ["'jz zero' will be TAKEN", "test eax, eax"], ["سيقفز"]),
    ("mov ecx, 1\nl1: loop l1", "", 32, ["NOT taken", "counter becomes 0"], ["لن يقفز"]),
    ("lea rax, [rbx+rbx*4]", "rbx=3", 64, ["RAX: 0 -> 0xf (15)", "no memory is read"], ["لا تُقرأ الذاكرة"]),
    ("push rax\npop rbx", "rax=42", 64, ["RBX: 0 -> 0x2a (42)", "top of the stack"], ["قمة المكدس"]),
    ("mov [rbx], eax", "rbx=0x2000 eax=0x11223344", 64, ["[0x2000] (4 bytes): 0 -> 0x11223344"], ["انسخ"]),
    ("mul ebx", "eax=0x80000000 ebx=2", 32, ["EDX: 0 -> 1", "CF=OF=1"], ["النصف العلوي"]),
]


def test_whatif():
    regs, flags, mem = parse_values("eax=5, ebx=0x10 cl='A' CF=1 [0x2000]=1,2,3 dx=-1 si=10h")
    check("parse_values: registers / flags / memory", regs == {"eax": 5, "ebx": 16, "cl": 65, "dx": -1, "si": 16} and
          flags == {"CF": 1} and mem == {0x2000: b"\x01\x02\x03"}, (regs, flags, mem))
    for code, values, bits, en, ar in WHATIF:
        r = whatif(code, values, bits)
        all_en = " | ".join(s.get("summary_en", "") + " " + s.get("what_en", "") + " " +
                            " ".join(x["en"] for x in s.get("flags", [])) + " " +
                            ((s.get("jump") or {}).get("en", "")) for s in r["steps"])
        all_ar = " | ".join(s.get("summary_ar", "") + " " + s.get("what_ar", "") + " " +
                            " ".join(x["ar"] for x in s.get("flags", [])) + " " +
                            ((s.get("jump") or {}).get("ar", "")) for s in r["steps"])
        miss = [x for x in en if x not in all_en] + [x for x in ar if x not in all_ar]
        check(f"what-if {code.splitlines()[0]!r} ({values}): explanation", not r["error"] and not miss,
              f"missing {miss}; error {r['error']}; text {all_en[:400]}")
    r = whatif("xor ecx, ecx\ndiv ecx", "eax=10", 32)
    check("what-if: divide error explained in both languages", "Divide error" in r["error"] and
          ARABIC.search(r.get("error_ar", "")), r)
    r = whatif("mov ax, 5\nadd ax, bx", "bx=3", 16)
    check("what-if 16-bit: AX 5 -> 8", r["regs"].get("ax") == 8, r["regs"])
    r = whatif("mov eax, [nolabel]", "", 32)
    check("what-if: assembler error is shown", r["error"] and not r["steps"], r["error"])
    c = condition_text("jg", 0x0)
    check("condition_text jg with no flags set: taken", c["taken"] and "ZF=0" in c["en"], c)
    info = explain_step("cmp rcx, 0", {"rcx": 0, "eflags": 0}, {"rcx": 0, "eflags": 0x44}, next_ins="jle done")
    check("explain_step: cmp + jle prediction from given registers (debugger state)",
          info["jump"]["taken"] and "0 <= 0 is true" in info["jump"]["en"], info["jump"])


def test_fallbacks():
    stats = SAMPLE.parent / "CourseNumberAnalyzer" / "stats.asm"
    text = stats.read_text(encoding="utf-8")
    ln = next(i for i, s in enumerate(text.splitlines(), 1) if "add eax, [rcx + r8*4]" in s)
    info = CK.explain_line(text, str(stats), ln, init_regs={"rcx": 0x10000020, "rdx": 2})
    check("explain_line in a module without main runs the line's procedure", info["ok"] and info["count"] == 2,
          (info["ok"], info["count"], info["note_en"]))
    saved = CK.unicorn_available
    CK.unicorn_available = lambda: False
    try:
        p = SAMPLE / "correct" / "procedures_x64.asm"
        r = CK.check(p.read_text(encoding="utf-8"), str(p))
        check("without unicorn: status unavailable with an English + Arabic note", r.status == "unavailable" and
              "Unicorn" in r.note_en and ARABIC.search(r.note_ar), (r.status, r.note_en))
        d = SAMPLE / "correct" / "dos_sum.asm"
        r = CK.check(d.read_text(encoding="utf-8"), str(d))
        check("without unicorn: 8086 programs are still checked", r.status == "ok" and r.engine == "emu8086", r.status)
    finally:
        CK.unicorn_available = saved


def test_dicts():
    p = SAMPLE / "buggy" / "divide_by_zero.asm"
    r = CK.check(p.read_text(encoding="utf-8"), str(p))
    f = next(x for x in r.findings if x.rule == "sim.div_zero")
    d = f.issue_dict("ar")
    check("issue_dict: asm_lint shape (0-based line, source sim, markdown, url)",
          d["line"] == f.line - 1 and d["source"] == "sim" and d["markdown"].startswith("**") and d["url"] and
          ARABIC.search(d["message"]), d)
    d = f.to_dict("en")
    check("to_dict: both languages", d["message_ar"] and d["why_en"] and d["fix_ar"] and d["ref"] == "div", d)


if __name__ == "__main__":
    if not CK.unicorn_available():
        print("unicorn / capstone are not installed: pip install unicorn capstone")
        sys.exit(2)
    for fn in (test_buggy, test_correct, test_scopes, test_explain, test_whatif, test_fallbacks, test_dicts):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} raised", False, repr(e))
    ok = sum(1 for _n, c, _d in RESULTS if c)
    print(f"\n{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)
