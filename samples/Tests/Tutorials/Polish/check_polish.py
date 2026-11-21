"""Checks of the tutorials polish pass (radide/tutorials, radide/tutorials/html.py, tools/build_chm.py).

    python samples/Tests/Tutorials/Polish/check_polish.py            # fast checks (no CHM compiler needed)
    python samples/Tests/Tutorials/Polish/check_polish.py --chm      # also build + verify two CHM books

1. every course loads, every lesson file exists, every quiz block is valid JSON (question / choices / answer);
2. the code blocks (everything but quiz blocks) of every lesson that exists in git HEAD are byte-identical to
   HEAD - wording edits must never touch code, so the course checkers keep passing;
3. Arabic terms: class = صنف (فئة only as the "also called" note of a glossary), method = دالة (no تابع for
   a method in the JavaScript / Rust lessons);
4. code names in section headings are in backticks (VB keywords, PHP / Dart / C keywords, assembly mnemonics);
5. English menu paths ("File > New Project...") are left-to-right isolates in the lesson HTML: a span with
   unicode-bidi: isolate in the viewer, an inline-block in the CHM (IE engine); code spans are not touched;
6. the new lessons (form-designer 12 / 13, flutter-mobile 13) are registered, render in both modes and have
   their sections and quizzes; the assembly course covers the native debugger windows.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402
from radide.tutorials import html as TH  # noqa: E402

FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.M | re.S)
RESULTS: list[tuple[str, bool, str]] = []
# courses owned by another workflow (VS2022 .NET support): only loaded, not judged
FOREIGN = {"visual-studio-projects"}


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    return bool(ok)


def prose(md: str) -> str:
    """The lesson without its code blocks (quiz blocks are kept: they are Arabic text for the learner)."""
    return FENCE.sub(lambda m: m.group(0) if m.group(1).strip().startswith("quiz") else "", md)


def code_blocks(md: str) -> list[str]:
    return [m.group(0) for m in FENCE.finditer(md) if not m.group(1).strip().startswith("quiz")]


def git_head(path: Path) -> str | None:
    rel = path.relative_to(REPO).as_posix()
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True)
    return r.stdout.decode("utf-8").replace("\r\n", "\n") if r.returncode == 0 else None


# ------------------------------------------------------------------------------------------------ 1 + 2
def check_courses() -> None:
    courses = T.courses()
    check("courses load", len(courses) >= 35, f"{len(courses)} courses")
    missing, bad_quiz, changed, lessons = [], [], [], 0
    for c in courses:
        data = json.loads((c.folder / "course.json").read_text(encoding="utf-8"))
        for x in data["lessons"]:
            if not (c.folder / x["file"]).is_file():
                missing.append(f"{c.id}/{x['file']}")
        for les in c.lessons:
            lessons += 1
            md = les.text().replace("\r\n", "\n")
            for b in les.blocks():
                if b.lang == "quiz" and b.quiz is None:
                    bad_quiz.append(f"{c.id}/{les.file}:{b.line}")
            old = git_head(les.path)
            if old is not None and code_blocks(old) != code_blocks(md):
                changed.append(f"{c.id}/{les.file}")
    check("every lesson file exists", not missing, ", ".join(missing[:5]))
    check("every quiz block is valid JSON", not bad_quiz, ", ".join(bad_quiz[:5]))
    check("code blocks unchanged against git HEAD", not changed, ", ".join(changed[:8]) or f"{lessons} lessons")


# ------------------------------------------------------------------------------------------------ 3
CLASS_WORDS = re.compile(r"(?<![ء-ي])(?:[وبلف]|ال|لل|بال|وال)?(?:فئة|فئات|فئت\w*)")
CATEGORY_OK = {  # فئة that means "category" (of files, settings, plots), not "class"
    "data-and-reports", "jupyter-datascience", "node-frontend", "powershell", "form-designer"}


def check_terms() -> None:
    bad = []
    for c in T.courses():
        if c.id in FOREIGN or c.id in CATEGORY_OK:
            continue
        files = [les.path for les in c.lessons] + [c.folder / "course.json"]
        for p in files:
            text = p.read_text(encoding="utf-8")
            text = prose(text) if p.suffix == ".md" else text
            for ln in text.splitlines():
                if CLASS_WORDS.search(ln) and not re.search(r"أيضًا|بعض الكتب|يُسمّى|ويُسمى|تُسمى", ln):
                    bad.append(f"{c.id}/{p.name}: {ln.strip()[:70]}")
    check("class = صنف outside glossary notes", not bad, " | ".join(bad[:4]))
    bad = []
    for cid in ("javascript", "rust"):
        c = T.course(cid)
        for les in c.lessons:
            for ln in prose(les.text()).splitlines():
                # تابع / توابع as a noun for "method" (not "تابع الدروس" = continue, not متابعة)
                for m in re.finditer(r"(?<![ء-ي])(?:[وبل]|ال)?(?:تابع|توابع|تابعًا|تابعان)(?![ء-ي])", ln):
                    tail = ln[m.end():m.end() + 12]
                    if re.match(r"\s*(?:مع|الدروس|التقدم|نافذة)", tail) or "أيضًا" in ln:
                        continue
                    bad.append(f"{cid}/{les.file}: {ln.strip()[:70]}")
    check("method = دالة in JavaScript / Rust", not bad, " | ".join(bad[:4]))
    notes = 0
    for cid, fname in (("vb-basic", "24-glossary.md"), ("dart", "13-glossary.md"), ("javascript", "17-glossary.md"),
                       ("cpp", "29-glossary.md"), ("java", "17-glossary.md"), ("python", "18-glossary.md")):
        t = (T.course(cid).folder / fname).read_text(encoding="utf-8")
        notes += bool(re.search(r"فئة", t)) and bool(re.search(r"طريقة|تابع", t))
    check("glossaries mention the alternative terms", notes == 6, f"{notes}/6 glossaries")


# ------------------------------------------------------------------------------------------------ 4
CODE_WORDS = set("""Dim ReDim Const ElseIf IIf InStr MsgBox InputBox Debug.Print Err.Raise ByRef ByVal Form_Load
KeyPress SetFocus TextBox ListBox ComboBox CheckBox OptionButton vbCrLf Variant elif elseif foreach printf qsort
mov lea cmp xchg movsx movzx cmovcc equ struct setState htmlspecialchars var_dump print_r array_map
array_filter __DIR__ StringBuffer DataFrame MessageBoxA ExitProcess""".split())


def check_headings() -> None:
    bad, total = [], 0
    for c in T.courses():
        if c.id in FOREIGN:
            continue
        for les in c.lessons:
            for m in re.finditer(r"^#{2,4}\s+(.+)$", prose(les.text()), re.M):
                total += 1
                bare = re.sub(r"`[^`]*`", "", m.group(1))
                bare = re.sub(r"\([A-Za-z][A-Za-z-]*(?: [A-Za-z-]+)+\)", "", bare)    # "(pass by reference)"
                words = {w.rstrip(":),.؟") for w in re.findall(r"[A-Za-z_][\w.]*", bare)}
                hit = words & CODE_WORDS
                if hit:
                    bad.append(f"{c.id}/{les.file}: {m.group(1)[:60]}")
    check("code names in headings are in backticks", not bad, " | ".join(bad[:4]) or f"{total} headings")
    t = (T.course("vb-basic").folder / "07-conditions.md").read_text(encoding="utf-8")
    check("VB heading sample: `Select Case`", "## `Select Case`:" in t and "## `If ... Then ... End If`" in t)


# ------------------------------------------------------------------------------------------------ 5
def check_bidi() -> None:
    h = TH.md_to_html("> **File > New Project...** (ملف > مشروع جديد...). ثم `a > b` و View > Other Windows > Animations")
    check("menu path -> ltr isolate span",
          '<span class="ltr" dir="ltr">File &gt; New Project...</span>' in h
          and '<span class="ltr" dir="ltr">View &gt; Other Windows &gt; Animations</span>' in h, h[:120])
    check("Arabic path and code span untouched", "(ملف &gt; مشروع جديد...)" in h and "<code>a &gt; b</code>" in h)
    h = TH.md_to_html("افتح **Debug > Start Without Debugging** - ثم")
    check("trailing dash stays outside the span", '>Debug &gt; Start Without Debugging</span></strong> - ثم' in h, h)
    q = TH._inline("من **Tools > Options...** الآن")
    check("quiz text gets the span too", 'class="ltr"' in q, q)
    les = T.course("ide-basics").lessons[0]
    viewer, chm = TH.lesson_page(les), TH.lesson_page(les, chm=True)
    check("viewer CSS isolates .ltr", re.search(r"\.ltr \{[^}]*unicode-bidi: isolate", viewer) is not None)
    check("CHM CSS makes .ltr an inline-block", re.search(r"\.ltr \{ display: inline-block", chm) is not None)
    # every bold English menu path of every lesson is inside an ltr span
    left, spans = [], 0
    for c in T.courses():
        for les in c.lessons:
            body = TH.lesson_body(les)
            spans += body.count('class="ltr"')
            for m in re.finditer(r"<strong>([A-Z][\w .]*(?: &gt; [\w .]+)+)</strong>", body):
                left.append(f"{c.id}/{les.file}: {m.group(1)[:40]}")
    check("all bold menu paths are isolated", not left and spans > 900, " | ".join(left[:3]) or f"{spans} spans")
    sys.path.insert(0, str(REPO / "tools"))
    import build_chm as B
    nav = B.nav_html(("a.html", "Tools > Options..."), None)
    check("CHM navigation links isolate menu paths", 'class="ltr"' in nav, nav)


# ------------------------------------------------------------------------------------------------ 6
def check_new_lessons() -> None:
    fd, fm = T.course("form-designer"), T.course("flutter-mobile")
    for c, lid, needles in (
            (fd, "12-animations-sizes", ["View > Animations", "Add Animation", "Preview all on load",
                                         "This size only", "Add Size...", "Reset to base", "View > Sizes",
                                         "BeginAnimation", "CurrentSizes"]),
            (fd, "13-component-packages", ["Tools > Component Packages", ".radcomp", "Choose Toolbox Items...",
                                           "component.json", "User Control -> Package", "Hot Reload"]),
            (fm, "13-foldables", ["galaxy_z_fold6", "Posture", "Half-open", "TwoPane", "HingeAware",
                                  "Controls cross the hinge:", "Create Foldable Emulator", "Foldable set"])):
        les = c.lesson(lid)
        if not check(f"{c.id}/{lid} registered", les is not None):
            continue
        text = les.text()
        miss = [n for n in needles if n not in text]
        check(f"{c.id}/{lid} covers its topics", not miss, ", ".join(miss))
        quizzes = [b for b in les.blocks() if b.lang == "quiz"]
        check(f"{c.id}/{lid} has quizzes", len(quizzes) >= 3 and all(b.quiz for b in quizzes), str(len(quizzes)))
        check(f"{c.id}/{lid} title matches its heading", les.heading().endswith(les.title_ar), les.heading())
        try:
            TH.lesson_page(les), TH.lesson_page(les, chm=True)
            ok = True
        except Exception as e:  # noqa: BLE001
            ok = False
            print(e)
        check(f"{c.id}/{lid} renders (viewer + CHM)", ok)
        check(f"{c.id}/{lid} is found by the lesson search", any(x[1].id == lid for x in T.search(needles[0])))
    asm = T.course("assembly").lesson("14-debugging").text()
    check("assembly course covers Registers / Disassembly / Memory / Stack windows",
          all(w in asm for w in ("**Registers** (`Alt+5`)", "**Disassembly** (`Alt+8`)", "**Memory 1** (`Alt+6`)",
                                 "**Stack**")))


def check_chm() -> None:
    sys.path.insert(0, str(REPO / "tools"))
    r = subprocess.run([sys.executable, str(REPO / "tools" / "build_chm.py"), "form-designer", "flutter-mobile",
                        "--verify"], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-1500:])
    check("CHM build + verify (form-designer, flutter-mobile)", r.returncode == 0, r.stderr[-300:])


def main() -> int:
    check_courses()
    check_terms()
    check_headings()
    check_bidi()
    check_new_lessons()
    if "--chm" in sys.argv:
        check_chm()
    failed = [n for n, ok, _d in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
