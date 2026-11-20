"""Build the CHM help files: the Arabic courses of radide/tutorials and the IDE manual.

    python tools/build_chm.py                 # all three -> docs/chm/
    python tools/build_chm.py basic cpp       # only some (basic | cpp | manual)
    python tools/build_chm.py --encoding utf-8 --out <dir>      # experiment with the page encoding
    python tools/build_chm.py --verify        # also decompile every CHM with hh.exe -decompile and check it

Output: docs/chm/RADIDE_BASIC_ar.chm, RADIDE_CPP_ar.chm, RADIDE_Manual.chm.

Compiler: hhc.exe (Microsoft HTML Help Workshop) when installed, else chmcmd (Free Pascal), looked up in
%LOCALAPPDATA%\\RADIDE\\toolchains\\lazarus\\fpc\\<ver>\\bin\\<target>, %LOCALAPPDATA%\\RADIDE\\toolchains\\fpc\\...,
%LOCALAPPDATA%\\RADIDE\\tools\\chmcmd and PATH.  --download-chmcmd fetches the official FPC Windows installer
from SourceForge and extracts chmcmd.exe with innoextract into %LOCALAPPDATA%\\RADIDE\\tools\\chmcmd.

Arabic: the HTML Help viewer shows the table of contents, the index, window titles and the search results in
the ANSI code page of the CHM's language.  The books are therefore compiled with Language=0x401 (Arabic -
Saudi Arabia, code page 1256), and the .hhc / .hhk and the pages are written in windows-1256 (characters
outside it become &#NNNN; references, which the IE engine of hh.exe renders).  UTF-8 pages also render (the
<meta charset> wins), but their <title>s - which the compiler copies into the TOC/search lists - turn into
mojibake, so cp1256 is the default (see --encoding).
"""
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from radide import tutorials as T  # noqa: E402
from radide.tutorials import html as TH  # noqa: E402

LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE"
OUT = REPO / "docs" / "chm"
WORK = LOCAL / "chm-build"
FONT = REPO / "radide" / "web" / "fonts" / TH.FONT_FILE
FONT_LICENCE = REPO / "radide" / "web" / "fonts" / "NotoNaskhArabic-OFL.txt"
HELP_DIR = REPO / "radide" / "features" / "help"
BOOKS = {"basic": ("vb-basic", "RADIDE_BASIC_ar.chm"), "cpp": ("cpp", "RADIDE_CPP_ar.chm"),
         "manual": (None, "RADIDE_Manual.chm")}
LANG_ID = "0x401 Arabic (Saudi Arabia)"
FPC_URL = "https://sourceforge.net/projects/freepascal/files/Win32/3.2.2/fpc-3.2.2.win32.and.win64.exe/download"


# ===================================================================== compilers
def find_hhc() -> Path | None:
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base and (Path(base) / "HTML Help Workshop" / "hhc.exe").is_file():
            return Path(base) / "HTML Help Workshop" / "hhc.exe"
    w = shutil.which("hhc")
    return Path(w) if w else None


def find_chmcmd() -> Path | None:
    roots = [LOCAL / "toolchains" / "lazarus", LOCAL / "toolchains" / "fpc", LOCAL / "tools" / "chmcmd"]
    for root in roots:
        if root.is_dir():
            hits = sorted(root.rglob("chmcmd.exe"), key=lambda p: ("x86_64" not in str(p), str(p)))
            if hits:
                return hits[0]
    w = shutil.which("chmcmd")
    return Path(w) if w else None


def download_chmcmd() -> Path | None:
    """The official FPC installer (Inno Setup) -> chmcmd.exe into %LOCALAPPDATA%\\RADIDE\\tools\\chmcmd."""
    import urllib.request
    dest = LOCAL / "tools" / "chmcmd"
    dl = LOCAL / "tools" / "_download"
    dl.mkdir(parents=True, exist_ok=True)
    setup = dl / "fpc-3.2.2.win32.and.win64.exe"
    if not setup.exists():
        print("downloading", FPC_URL)
        urllib.request.urlretrieve(FPC_URL, setup)          # noqa: S310 - fixed https URL
    inno = shutil.which("innoextract") or next(iter((LOCAL / "tools" / "innoextract").rglob("innoextract.exe")), None)
    if not inno:
        print("innoextract is needed to unpack the FPC installer (https://constexpr.org/innoextract/)")
        return None
    tmp = dl / "fpc-extract"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    subprocess.run([str(inno), "-s", "-I", "chmcmd.exe", "-d", str(tmp), str(setup)], check=False)
    hit = next(iter(tmp.rglob("chmcmd.exe")), None)
    if hit is None:
        return None
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hit, dest / "chmcmd.exe")
    return dest / "chmcmd.exe"


def compile_hhp(hhp: Path, log=print) -> bool:
    hhc = find_hhc()
    if hhc is not None:
        r = subprocess.run([str(hhc), hhp.name], cwd=hhp.parent, capture_output=True)
        out = (r.stdout + r.stderr).decode("cp1252", "replace")
        log(out.strip()[-1500:])
        return r.returncode == 1          # hhc returns 1 on success
    chmcmd = find_chmcmd()
    if chmcmd is None:
        log("no CHM compiler: install HTML Help Workshop or run with --download-chmcmd")
        return False
    r = subprocess.run([str(chmcmd), "--verbosity", "1", hhp.name], cwd=hhp.parent, capture_output=True)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    if out.strip():
        log(out.strip()[-1500:])
    return r.returncode == 0


# ===================================================================== writing a book
class Book:
    def __init__(self, name: str, title: str, enc: str, folder: Path):
        self.name, self.title, self.enc, self.folder = name, title, enc, folder
        self.files: list[str] = []
        self.toc: list[tuple[int, str, str]] = []           # (level, title, file)
        self.index: list[tuple[str, str]] = []              # (keyword, file)
        shutil.rmtree(folder, ignore_errors=True)
        (folder / "fonts").mkdir(parents=True, exist_ok=True)
        if FONT.exists():
            shutil.copy2(FONT, folder / "fonts" / FONT.name)
            shutil.copy2(FONT_LICENCE, folder / "fonts" / FONT_LICENCE.name)
            self.files += [f"fonts\\{FONT.name}", f"fonts\\{FONT_LICENCE.name}"]

    def encode(self, text: str) -> bytes:
        return text.encode(self.enc, errors="xmlcharrefreplace")

    def charset(self) -> str:
        return "windows-1256" if self.enc == "cp1256" else "utf-8"

    def write(self, fname: str, page_html: str) -> None:
        page_html = re.sub(r'<meta charset="[^"]*">', f'<meta charset="{self.charset()}">', page_html)
        page_html = re.sub(r'charset=[\w-]+"', f'charset={self.charset()}"', page_html)
        (self.folder / fname).write_bytes(self.encode(page_html))
        self.files.append(fname)

    def sitemap(self, entries, kind: str) -> bytes:
        head = ('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">\n<HTML><HEAD>'
                '<meta http-equiv="Content-Type" content="text/html; charset=windows-1256">'
                "<!-- Sitemap 1.0 --></HEAD><BODY>\n")
        if kind == "toc":
            head += '<OBJECT type="text/site properties"><param name="Window Styles" value="0x800025">' \
                    '<param name="ImageType" value="Folder"></OBJECT>\n'
        out, level = [head, "<UL>\n"], 1
        for lvl, title, f in entries:
            while level < lvl:
                out.append("<UL>\n")
                level += 1
            while level > lvl:
                out.append("</UL>\n")
                level -= 1
            out.append(f'<LI><OBJECT type="text/sitemap"><param name="Name" value="{html.escape(title)}">'
                       f'<param name="Local" value="{f}"></OBJECT>\n')
        out.append("</UL>\n" * level + "</BODY></HTML>\n")
        # the sitemaps are always in the code page of the CHM's language (Arabic: 1256)
        return "".join(out).encode("cp1256", errors="xmlcharrefreplace")

    def finish(self, default: str, chm_name: str) -> Path:
        (self.folder / f"{self.name}.hhc").write_bytes(self.sitemap(self.toc, "toc"))
        idx = sorted(self.index, key=lambda kv: kv[0])
        (self.folder / f"{self.name}.hhk").write_bytes(self.sitemap([(1, k, f) for k, f in idx], "index"))
        hhp = [
            "[OPTIONS]",
            "Compatibility=1.1 or later",
            f"Compiled file={chm_name}",
            f"Contents file={self.name}.hhc",
            f"Index file={self.name}.hhk",
            f"Default topic={default}",
            "Default Window=main",
            "Display compile progress=No",
            "Full-text search=Yes",
            "Binary TOC=No",
            "Binary Index=Yes",
            f"Language={LANG_ID}",
            "Default Font=Tahoma,10,178",
            f"Title={self.title}",
            "",
            "[WINDOWS]",
            f'main="{self.title}","{self.name}.hhc","{self.name}.hhk","{default}","{default}",,,,,0x63520,240,'
            f"0x10184e,[60,40,1180,860],0x0,0x0,,,,,0",
            "",
            "[FILES]",
            *self.files,
            "",
        ]
        hhp_path = self.folder / f"{self.name}.hhp"
        hhp_path.write_bytes("\r\n".join(hhp).encode("cp1256", errors="replace"))
        return hhp_path


# ===================================================================== the courses
def nav_html(prev, nxt) -> str:
    p = (f'<a class="btn sec" href="{prev[0]}">&rarr; {html.escape(prev[1])}</a>' if prev else "<span></span>")
    n = (f'<a class="btn" href="{nxt[0]}">{html.escape(nxt[1])} &larr;</a>' if nxt else "<span></span>")
    return f'<div class="navfoot">{p}{n}</div>'


def build_course(key: str, enc: str, work: Path, log=print) -> Path | None:
    cid, chm_name = BOOKS[key]
    course = T.course(cid)
    if course is None:
        log(f"course {cid} not found")
        return None
    book = Book(f"radide_{key}", course.title_ar, enc, work / key)
    # cover page: description + list of lessons
    rows = "".join(f'<li><a href="{les.id}.html">{html.escape(les.title_ar)}</a> '
                   f'<span class="meta">({les.minutes} دقيقة)</span></li>' for les in course.lessons)
    intro = (f"<h1>{html.escape(course.title_ar)}</h1><p class=\"meta\">{html.escape(course.title_en)}</p>"
             f"<p>{html.escape(course.description_ar or '')}</p>"
             f"<p>هذا الملف نسخة للقراءة من دروس RAD IDE. لتشغيل الأمثلة والتحقق من التمارين افتح الدروس داخل "
             f"البيئة: <b>تعليمات &gt; الدروس</b> (Ctrl+Shift+F1)، ثم اضغط «جرّبه» أو «تحقق».</p>"
             f"<h2>الدروس</h2><ol>{rows}</ol>")
    book.write("index.html", TH.page(intro, course.title_ar, chm=True))
    book.toc.append((1, course.title_ar, "index.html"))
    lessons = course.lessons
    for i, les in enumerate(lessons):
        prev = (f"{lessons[i - 1].id}.html", lessons[i - 1].title_ar) if i > 0 else None
        nxt = (f"{lessons[i + 1].id}.html", lessons[i + 1].title_ar) if i + 1 < len(lessons) else None
        fname = f"{les.id}.html"
        book.write(fname, TH.lesson_page(les, chm=True, nav=nav_html(prev, nxt)))
        book.toc.append((2, f"{les.number}. {les.title_ar}", fname))
        book.index.append((les.title_ar, fname))
        for m in re.finditer(r"^##\s+(.+)$", les.text(), re.M):         # section headings -> index keywords
            kw = re.sub(r"[`*]", "", m.group(1)).strip()
            if kw:
                book.index.append((kw, fname))
    hhp = book.finish("index.html", chm_name)
    return _compile(hhp, chm_name, log)


# ===================================================================== the IDE manual
def split_help_page(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    """(head html, title, [(section title, section html)]) - one topic per <h2>."""
    text = path.read_text(encoding="utf-8")
    head = re.search(r"<head>(.*?)</head>", text, re.S | re.I).group(1)
    head = re.sub(r"<meta charset=[^>]*>", "", head, flags=re.I)
    title = re.sub(r"<[^>]+>", "", re.search(r"<title>(.*?)</title>", head, re.S | re.I).group(1)).strip()
    body = re.search(r"<body[^>]*>(.*)</body>", text, re.S | re.I).group(1)
    parts = re.split(r"(?=<h2[^>]*>)", body)
    intro, sections = parts[0], []
    for p in parts[1:]:
        h = re.sub(r"<[^>]+>", "", re.match(r"<h2[^>]*>(.*?)</h2>", p, re.S | re.I).group(1))
        sections.append((html.unescape(h).strip(), p))
    sections.insert(0, (title, intro))
    return head, title, sections


def build_manual(enc: str, work: Path, log=print) -> Path | None:
    book = Book("radide_manual", "RAD IDE Manual - دليل RAD IDE", enc, work / "manual")
    first = None
    for lang, page_file, dirattr in (("en", HELP_DIR / "index.html", 'dir="ltr" lang="en"'),
                                     ("ar", HELP_DIR / "index_ar.html", 'dir="rtl" lang="ar"')):
        if not page_file.exists():
            continue
        head, title, sections = split_help_page(page_file)
        # in-page links (href="#id") must point at the topic file that now holds the anchor
        where = {}
        for n, (_t, sec_html) in enumerate(sections):
            for m in re.finditer(r'(?:id|name)="([^"]+)"', sec_html):
                where.setdefault(m.group(1), f"{lang}_{n:02d}.html")
        level_files = []
        for n, (sec_title, sec_html) in enumerate(sections):
            fname = f"{lang}_{n:02d}.html"
            sec_html = re.sub(r'href="#([^"]*)"',
                              lambda m: (f'href="{where[m.group(1)]}#{m.group(1)}"' if m.group(1) in where
                                         else f'href="{lang}_00.html"'), sec_html)
            links = []
            if n > 0:
                links.append(f'<a href="{lang}_{n - 1:02d}.html">&larr; {html.escape(sections[n - 1][0])}</a>')
            if n + 1 < len(sections):
                links.append(f'<a href="{lang}_{n + 1:02d}.html">{html.escape(sections[n + 1][0])} &rarr;</a>')
            nav = f'<p style="margin-top:28px;border-top:1px solid #ccc;padding-top:6px">{" | ".join(links)}</p>'
            page_html = (f'<!DOCTYPE html>\n<html {dirattr}><head><meta charset="utf-8">'
                         f'<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
                         f'<meta http-equiv="X-UA-Compatible" content="IE=edge">{head}</head>'
                         f"<body>{sec_html}{nav}</body></html>")
            page_html = re.sub(r"<title>.*?</title>", f"<title>{html.escape(sec_title)}</title>", page_html, 1, re.S)
            book.write(fname, page_html)
            level_files.append((sec_title, fname))
            book.index.append((sec_title, fname))
        book.toc.append((1, title, level_files[0][1]))
        for sec_title, fname in level_files[1:]:
            book.toc.append((2, sec_title, fname))
        first = first or level_files[0][1]
    if first is None:
        log("no manual pages found")
        return None
    hhp = book.finish(first, BOOKS["manual"][1])
    return _compile(hhp, BOOKS["manual"][1], log)


def _compile(hhp: Path, chm_name: str, log) -> Path | None:
    built = hhp.parent / chm_name
    if built.exists():
        built.unlink()
    ok = compile_hhp(hhp, log)
    if not built.exists():
        log(f"FAILED: {chm_name} was not created")
        return None
    if not ok:
        log(f"warning: the compiler reported problems for {chm_name}")
    return built


# ===================================================================== verification
def decompile(chm: Path, dest: Path, timeout: float = 60) -> bool:
    """hh.exe -decompile <dest> <chm> (hh.exe returns before it has finished writing)."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    hh = Path(os.environ.get("WINDIR", r"C:\Windows")) / "hh.exe"
    subprocess.run([str(hh), "-decompile", str(dest), str(chm)], check=False)
    end, last = time.time() + timeout, -1
    while time.time() < end:
        n = sum(1 for _ in dest.rglob("*"))
        if n and n == last:
            return True
        last = n
        time.sleep(0.7)
    return any(dest.rglob("*"))


def verify(chm: Path, key: str, enc: str, work: Path, log=print) -> list[str]:
    """Decompile and check: every page is there and decodes in its charset with the Arabic text intact, the
    TOC (cp1256) names every lesson."""
    problems = []
    dest = work / "_decompiled" / chm.stem
    if not decompile(chm, dest):
        return [f"{chm.name}: hh.exe -decompile produced nothing"]
    src = work / key
    pages = sorted(p.name for p in src.glob("*.html"))
    for name in pages:
        got = dest / name
        if not got.exists():
            problems.append(f"{chm.name}: {name} missing after decompile")
            continue
        if got.read_bytes() != (src / name).read_bytes():
            problems.append(f"{chm.name}: {name} differs after decompile")
        text = got.read_bytes().decode("cp1256" if enc == "cp1256" else "utf-8")
        text = html.unescape(text)
        if key in ("basic", "cpp") and name != "index.html":
            les = T.course(BOOKS[key][0]).lesson(name[:-5])
            if les is not None and les.title_ar not in text:
                problems.append(f"{chm.name}: {name} does not contain its Arabic title")
    hhc = next(iter(dest.glob("*.hhc")), None)
    if hhc is None:
        problems.append(f"{chm.name}: no .hhc after decompile")
    elif key in ("basic", "cpp"):
        toc = html.unescape(hhc.read_bytes().decode("cp1256"))
        for les in T.course(BOOKS[key][0]).lessons:
            if les.title_ar not in toc:
                problems.append(f"{chm.name}: TOC lacks '{les.title_ar}'")
    log(f"verify {chm.name}: {len(pages)} pages, {'OK' if not problems else f'{len(problems)} problem(s)'}")
    return problems


# ===================================================================== main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("books", nargs="*", default=list(BOOKS), help="basic | cpp | manual (default: all)")
    ap.add_argument("--encoding", choices=("cp1256", "utf-8"), default="cp1256", help="page encoding")
    ap.add_argument("--out", default=str(OUT), help="where the .chm files go (default docs/chm)")
    ap.add_argument("--work", default=str(WORK), help="build folder")
    ap.add_argument("--verify", action="store_true", help="decompile with hh.exe and check the result")
    ap.add_argument("--download-chmcmd", action="store_true", help="get chmcmd from the official FPC installer")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.download_chmcmd and find_hhc() is None and find_chmcmd() is None:
        print("chmcmd:", download_chmcmd())
    print("compiler:", find_hhc() or find_chmcmd() or "none")
    out, work = Path(a.out), Path(a.work)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    failed = 0
    for key in a.books:
        if key not in BOOKS:
            print("unknown book", key)
            failed += 1
            continue
        chm = build_manual(a.encoding, work) if key == "manual" else build_course(key, a.encoding, work)
        if chm is None:
            failed += 1
            continue
        final = out / chm.name
        shutil.copy2(chm, final)
        print(f"built {final} ({final.stat().st_size // 1024} KB)")
        if a.verify:
            probs = verify(final, key, a.encoding, work)
            for p in probs:
                print("  " + p)
            failed += bool(probs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
