"""Lesson -> HTML for the IDE's lesson viewer (QWebEngineView, interactive) and for the CHM help files.

Arabic text is right-to-left in Noto Naskh Arabic (radide/web/fonts, SIL OFL; fallback Segoe UI / Tahoma),
code stays left-to-right and is highlighted with Pygments (light "vs" / dark "one-dark" rules, switched by
the class of <body>).  In the viewer the buttons are links to https://radtut.action/<verb>?b=<block> that the
page object intercepts; the CHM version has no IDE buttons (solutions and quizzes still work with plain JS
that the old Internet Explorer engine of hh.exe understands).
"""
from __future__ import annotations

import html
import json
import re

from . import Block, Lesson

ACT = "https://radtut.action/"
FONT_FILE = "NotoNaskhArabic-wght.ttf"
FONT_FAMILY = "Noto Naskh Arabic RAD"
LEXERS = {"vb": "vbnet", "cpp": "cpp"}
LANG_NAMES = {"vb": "BASIC", "cpp": "C++"}

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover - markdown is a dependency of the IDE
    _markdown = None


# ===================================================================== pieces
def md_to_html(text: str) -> str:
    if _markdown is not None:
        return _markdown.markdown(text, extensions=["tables", "sane_lists"], output_format="html")
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):          # minimal fallback
        out.append("<p>" + html.escape(para).replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def highlight(code: str, lang: str) -> str:
    try:
        from pygments import highlight as _hl
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        lexer = get_lexer_by_name(LEXERS.get(lang, "text"))
        return _hl(code, lexer, HtmlFormatter(nowrap=True))
    except Exception:  # noqa: BLE001
        return html.escape(code)


def pygments_css() -> str:
    try:
        from pygments.formatters import HtmlFormatter
        light = HtmlFormatter(style="vs").get_style_defs("body.light pre.hl")
        dark = HtmlFormatter(style="one-dark").get_style_defs("body.dark pre.hl")
    except Exception:  # noqa: BLE001
        return ""
    # the containers get their background from our own palette
    keep = []
    for ln in (light + "\n" + dark).splitlines():
        if re.match(r"\s*body\.(light|dark) pre\.hl\s*\{", ln) or ".hll" in ln or "td.linenos" in ln \
                or "span.linenos" in ln:
            continue
        keep.append(ln)
    return "\n".join(keep)


CSS = """
@font-face { font-family: "%(family)s"; src: url("%(font)s") format("truetype"); font-weight: 400 700; }
body.light { --bg:#fbfaf7; --fg:#1f2328; --muted:#5f6670; --card:#ffffff; --border:#d9dde3; --code:#f5f7fa;
  --accent:#1f6feb; --accent-fg:#ffffff; --ok:#1a7f37; --ok-bg:#e8f5ec; --bad:#c62828; --bad-bg:#fdecea;
  --out:#f2f4f2; --quote:#eef4ff; --chip:#e9eef6; }
body.dark { --bg:#1e1f22; --fg:#e3e5e8; --muted:#9aa0a6; --card:#26282c; --border:#3a3d42; --code:#282c34;
  --accent:#4c8dff; --accent-fg:#ffffff; --ok:#56d364; --ok-bg:#1c3324; --bad:#ff7b72; --bad-bg:#3d1f1f;
  --out:#202225; --quote:#23293a; --chip:#30343b; }
html, body { margin:0; padding:0; }
body { background:var(--bg); color:var(--fg);
  font-family: "%(family)s", "Segoe UI", Tahoma, "Arial", sans-serif; font-size: %(size)spx; line-height: 1.85; }
.page { max-width: 880px; margin: 0 auto; padding: 18px 26px 60px 26px; }
h1 { font-size: 1.75em; line-height:1.4; margin: 0.3em 0 0.6em 0; color: var(--accent); }
h2 { font-size: 1.35em; margin: 1.4em 0 0.5em 0; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
h3 { font-size: 1.12em; margin: 1.2em 0 0.4em 0; }
a { color: var(--accent); }
p, li { text-align: justify; }
code { font-family: Consolas, "Cascadia Mono", "Courier New", monospace; font-size: 0.86em; direction: ltr;
  unicode-bidi: embed; unicode-bidi: isolate; background: var(--chip); padding: 1px 5px; border-radius: 4px; }
blockquote { margin: 1em 0; padding: 8px 14px; background: var(--quote); border-right: 4px solid var(--accent);
  border-radius: 6px; }
blockquote p { margin: 0.3em 0; }
table { border-collapse: collapse; margin: 1em 0; width: 100%%; }
th, td { border: 1px solid var(--border); padding: 5px 9px; vertical-align: top; }
th { background: var(--chip); }
.meta { color: var(--muted); font-size: 0.85em; margin-bottom: 4px; }
.blk { border: 1px solid var(--border); border-radius: 8px; margin: 14px 0; background: var(--card); overflow: hidden; }
.bar { direction: rtl; display: flex; align-items: center; flex-wrap: wrap; gap: 6px; padding: 5px 10px;
  background: var(--chip); border-bottom: 1px solid var(--border); font-size: 0.85em; }
.bar .tag { font-weight: bold; margin-left: auto; }
.btn { display: inline-block; text-decoration: none; cursor: pointer; padding: 1px 12px; border-radius: 5px;
  background: var(--accent); color: var(--accent-fg); border: 0; font: inherit; font-size: 0.95em; }
.btn.sec { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
pre { margin: 0; padding: 10px 14px; overflow-x: auto; direction: ltr; text-align: left;
  font-family: Consolas, "Cascadia Mono", "Courier New", monospace; font-size: 13.5px; line-height: 1.5; }
pre.hl { background: var(--code); }
pre.out { background: var(--out); unicode-bidi: plaintext; white-space: pre-wrap; }
.ex textarea { box-sizing: border-box; width: 100%%; min-height: 160px; border: 0; resize: vertical; direction: ltr;
  text-align: left; padding: 10px 14px; background: var(--code); color: var(--fg); outline: none;
  font-family: Consolas, "Cascadia Mono", "Courier New", monospace; font-size: 13.5px; line-height: 1.5;
  tab-size: 4; }
.result { display: none; padding: 8px 12px; border-top: 1px solid var(--border); }
.result.ok { display: block; background: var(--ok-bg); }
.result.bad { display: block; background: var(--bad-bg); }
.result.busy { display: block; color: var(--muted); }
.result .head { font-weight: bold; }
.result.ok .head { color: var(--ok); }
.result.bad .head { color: var(--bad); }
.sol .solbody { display: none; }
.sol.open .solbody { display: block; }
.quiz { padding: 10px 14px; }
.quiz .q { font-weight: bold; margin-bottom: 6px; }
.quiz .choice { display: block; width: 100%%; text-align: right; margin: 5px 0; padding: 5px 12px; cursor: pointer;
  border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--fg); font: inherit; }
.quiz .choice:hover { border-color: var(--accent); }
.quiz .choice.right { background: var(--ok-bg); border-color: var(--ok); }
.quiz .choice.wrong { background: var(--bad-bg); border-color: var(--bad); }
.quiz .why { display: none; margin-top: 6px; padding: 6px 10px; border-radius: 6px; background: var(--quote); }
.quiz.done .why { display: block; }
.navfoot { display: flex; justify-content: space-between; margin-top: 36px; padding-top: 12px;
  border-top: 1px solid var(--border); }
mark.find { background: #ffe066; color: #000; }
"""

JS = r"""
function radAct(verb, b, extra) {
  var url = '%(act)s' + verb + '?b=' + b + (extra || '');
  if (window.location.protocol !== 'mk:' && window.location.protocol !== 'its:') { window.location.href = url; }
}
function radToggle(id) {
  var e = document.getElementById(id);
  if (!e) return;
  e.className = e.className.indexOf(' open') >= 0 ? e.className.replace(' open', '') : e.className + ' open';
}
function radQuiz(b, i, silent) {
  var box = document.getElementById('q' + b);
  var answer = parseInt(box.getAttribute('data-answer'), 10);
  var choices = box.getElementsByTagName('button');
  for (var k = 0; k < choices.length; k++) {
    var c = choices[k];
    c.className = 'choice' + (k === answer ? ' right' : (k === i ? ' wrong' : ''));
  }
  var res = document.getElementById('qr' + b);
  res.innerHTML = (i === answer ? '<b style="color:var(--ok)">%(right)s</b> ' : '<b style="color:var(--bad)">%(wrong)s</b> ')
      + res.getAttribute('data-why');
  box.className = 'quiz done';
  if (!silent) radAct('quiz', b, '&c=' + i + '&ok=' + (i === answer ? 1 : 0));
}
function radCode(b) { var t = document.getElementById('code' + b); return t ? t.value : null; }
function radSetCode(b, text) { var t = document.getElementById('code' + b); if (t) t.value = text; }
function radResult(b, cls, html) {
  var r = document.getElementById('res' + b);
  if (!r) return;
  r.className = 'result ' + cls; r.innerHTML = html;
}
function radTheme(dark) { document.body.className = dark ? 'dark' : 'light'; }
function radScrollTo(id) { var e = document.getElementById(id); if (e) e.scrollIntoView(); }
"""


# ===================================================================== blocks
def _bar(tag: str, buttons: list[tuple[str, str, str]], chm: bool) -> str:
    parts = [f'<span class="tag">{html.escape(tag)}</span>']
    if not chm:
        for verb, label, cls in buttons:
            parts.append(f'<a class="btn {cls}" href="javascript:void(0)" onclick="{verb}">{html.escape(label)}</a>')
    return '<div class="bar">' + "".join(parts) + "</div>"


def tryable(b: Block) -> bool:
    """Blocks with a "جرّبه" button: runnable examples / solutions, C++ GUI forms and complete C++ programs."""
    if b.runnable:
        return True
    return b.lang == "cpp" and b.role == "plain" and not b.compile_error and \
        (b.gui or bool(re.search(r"\bint\s+main\s*\(", b.code)))


def block_html(b: Block, chm: bool = False, saved_code: str | None = None, quiz_state: int | None = None) -> str:
    n = b.index
    lang_name = LANG_NAMES.get(b.lang, "")
    if b.role == "quiz":
        q = b.quiz
        if not q:
            return f'<pre class="out">{html.escape(b.code)}</pre>'
        btns = "".join(f'<button class="choice" onclick="radQuiz({n},{i})">{html.escape(str(c))}</button>'
                       for i, c in enumerate(q.get("choices", [])))
        why = html.escape(str(q.get("explanation", "")), quote=True)
        return (f'<div class="blk"><div class="bar"><span class="tag">سؤال سريع</span></div>'
                f'<div class="quiz" id="q{n}" data-answer="{int(q.get("answer", 0))}">'
                f'<div class="q">{html.escape(str(q["question"]))}</div>{btns}'
                f'<div class="why" id="qr{n}" data-why="{why}"></div></div></div>')
    if b.lang == "text":
        tag = {"output": "الناتج", "input": "المدخلات (ما يكتبه المستخدم)"}.get(b.role, "")
        bar = f'<div class="bar"><span class="tag">{tag}</span></div>' if tag else ""
        return f'<div class="blk">{bar}<pre class="out">{html.escape(b.code.rstrip())}</pre></div>'
    if b.lang not in ("vb", "cpp"):
        return f'<div class="blk"><pre class="hl">{html.escape(b.code.rstrip())}</pre></div>'
    code_html = f'<pre class="hl">{highlight(b.code.rstrip(), b.lang)}</pre>'
    if b.role == "exercise":
        text = saved_code if saved_code is not None else b.code
        buttons = [(f"radAct('check',{n})", "تحقق ✓", ""), (f"radAct('open',{n})", "افتح في المحرر", "sec"),
                   (f"radAct('reset',{n})", "أعد الكود الأصلي", "sec")]
        body = code_html if chm else (f'<textarea id="code{n}" spellcheck="false" dir="ltr">'
                                      f'{html.escape(text.rstrip())}</textarea>')
        return (f'<div class="blk ex" id="b{n}">{_bar(f"تمرين {lang_name}" + (" (نموذج)" if b.form else ""), buttons, chm)}'
                f'{body}<div class="result" id="res{n}"></div></div>')
    if b.role == "solution":
        buttons = [(f"radAct('try',{n})", "▶ جرّبه", ""), (f"radAct('open',{n})", "افتح في المحرر", "sec")]
        return (f'<div class="blk sol" id="b{n}"><div class="bar"><a class="btn sec" href="javascript:void(0)" '
                f'onclick="radToggle(\'b{n}\')">الحل: اضغط للإظهار / الإخفاء</a></div>'
                f'<div class="solbody">{_bar("الحل", buttons, chm) if not chm else ""}{code_html}</div></div>')
    if tryable(b):
        tag = f"مثال {lang_name}" + (" (نموذج)" if b.form or b.gui else "")
        buttons = [(f"radAct('try',{n})", "▶ جرّبه", ""), (f"radAct('open',{n})", "افتح في المحرر", "sec")]
        return f'<div class="blk" id="b{n}">{_bar(tag, buttons, chm)}{code_html}</div>'
    return f'<div class="blk" id="b{n}">{code_html}</div>'


# ===================================================================== page
def lesson_body(lesson: Lesson, chm: bool = False, saved: dict | None = None) -> str:
    saved = saved or {}
    parts = []
    for kind, item in lesson.items():
        if kind == "md":
            parts.append(md_to_html(item))
        else:
            parts.append(block_html(item, chm, saved.get(item.index)))
    return "\n".join(parts)


def page(body: str, title: str, dark: bool = False, font_url: str = "fonts/" + FONT_FILE, size: int = 17,
         chm: bool = False, charset: str = "utf-8", extra_head: str = "") -> str:
    css = CSS % {"family": FONT_FAMILY, "font": font_url, "size": size} + pygments_css()
    js = JS % {"act": ACT, "right": "إجابة صحيحة!", "wrong": "ليست هذه."}
    compat = '<meta http-equiv="X-UA-Compatible" content="IE=edge">' if chm else ""
    return (f'<!DOCTYPE html>\n<html lang="ar" dir="rtl"><head><meta charset="{charset}">'
            f'<meta http-equiv="Content-Type" content="text/html; charset={charset}">{compat}'
            f"<title>{html.escape(title)}</title><style>{css}</style><script>{js}</script>{extra_head}</head>"
            f'<body class="{"dark" if dark else "light"}"><div class="page">{body}</div></body></html>')


def lesson_page(lesson: Lesson, dark: bool = False, chm: bool = False, saved: dict | None = None,
                font_url: str = "fonts/" + FONT_FILE, size: int = 17, nav: str = "", charset: str = "utf-8") -> str:
    meta = (f'<div class="meta">{html.escape(lesson.course.title_ar)} · الدرس {lesson.number} من '
            f'{len(lesson.course.lessons)} · {lesson.minutes} دقيقة تقريبًا</div>')
    return page(meta + lesson_body(lesson, chm, saved) + nav, lesson.title_ar, dark, font_url, size, chm, charset)


def quiz_json(b: Block) -> str:
    return json.dumps(b.quiz or {}, ensure_ascii=False)


__all__ = ["ACT", "FONT_FILE", "block_html", "highlight", "lesson_body", "lesson_page", "md_to_html", "page",
           "pygments_css", "tryable"]
