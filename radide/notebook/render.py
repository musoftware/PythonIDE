"""Notebook outputs and markdown to HTML (used by the notebook page and by Export to HTML).

Notebook HTML (pandas tables, markdown, SVG) comes from files that may not be trusted, and the notebook page
talks to the IDE through QWebChannel - so every piece of HTML is sanitised here: no scripts, no event handler
attributes, no javascript: URLs, no frames / objects / forms.
"""
from __future__ import annotations

import base64
import html
import re
from html.parser import HTMLParser

# output mime types in the order Jupyter prefers them
MIME_ORDER = ("text/html", "text/markdown", "image/svg+xml", "image/png", "image/jpeg", "image/gif",
              "text/latex", "application/json", "text/plain")
MAX_TEXT = 200_000                       # characters of a stream shown (the notebook keeps everything)

# ---------------------------------------------------------------------- sanitiser
_DROP_WITH_CONTENT = {"script", "iframe", "object", "embed", "frame", "frameset", "applet", "noscript",
                      "template", "title", "head", "meta", "link", "base"}
_DROP_TAG_ONLY = {"html", "body", "form", "input", "button", "textarea", "select", "option"}
_VOID = {"br", "hr", "img", "col", "area", "source", "track", "wbr", "input", "param"}
_URL_ATTRS = {"href", "src", "xlink:href", "action", "formaction", "background", "poster", "srcset"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out: list[str] = []
        self.skip = 0                     # depth inside a dropped element (script ...)

    @staticmethod
    def _safe_url(v: str) -> bool:
        s = re.sub(r"[\s\x00-\x1f]+", "", html.unescape(v or "")).lower()
        if s.startswith(("javascript:", "vbscript:")):
            return False
        if s.startswith("data:") and not s.startswith("data:image/") or s.startswith("data:image/svg"):
            return False
        return True

    def _attrs(self, attrs) -> str:
        parts = []
        for k, v in attrs:
            k = k.lower()
            if k.startswith("on") or k in ("srcdoc", "formaction"):
                continue
            if k in _URL_ATTRS and v is not None and not self._safe_url(v):
                continue
            if k == "style" and v and re.search(r"expression\s*\(|javascript:|url\s*\(\s*['\"]?\s*javascript",
                                                v, re.I):
                continue
            parts.append(f' {k}' if v is None else f' {k}="{html.escape(v, quote=True)}"')
        return "".join(parts)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip:
            if tag in _DROP_WITH_CONTENT and tag not in _VOID and tag not in ("meta", "link", "base"):
                self.skip += 1
            return
        if tag in _DROP_WITH_CONTENT:
            if tag not in ("meta", "link", "base"):
                self.skip = 1
            return
        if tag in _DROP_TAG_ONLY:
            return
        self.out.append(f"<{tag}{self._attrs(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self.skip or tag in _DROP_WITH_CONTENT or tag in _DROP_TAG_ONLY:
            return
        self.out.append(f"<{tag}{self._attrs(attrs)}/>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip:
            if tag in _DROP_WITH_CONTENT:
                self.skip -= 1
            return
        if tag in _DROP_WITH_CONTENT or tag in _DROP_TAG_ONLY or tag in _VOID:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data.replace("<", "&lt;").replace(">", "&gt;"))

    def handle_entityref(self, name):
        if not self.skip:
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip:
            self.out.append(f"&#{name};")

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        pass

    def unknown_decl(self, data):
        pass

    def handle_pi(self, data):
        pass


def sanitize(markup: str) -> str:
    p = _Sanitizer()
    try:
        p.feed(markup or "")
        p.close()
    except Exception:  # noqa: BLE001 - malformed HTML: show it as text
        return "<pre>" + html.escape(markup or "") + "</pre>"
    return "".join(p.out)


# ---------------------------------------------------------------------- ANSI colours (tracebacks)
_ANSI_COLORS = ["#000000", "#C42B1C", "#0B7B0B", "#A0700A", "#1F5FBF", "#9B2FAE", "#127A8A", "#808080"]
_ANSI_BRIGHT = ["#606060", "#E0443A", "#2EA043", "#C9A20A", "#3B82F6", "#C05BD6", "#1FA5B8", "#C0C0C0"]
_ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")
_OTHER_ESC = re.compile(r"\x1b\[[0-9;?]*[A-Za-ln-z]|\x1b\][^\x07]*\x07")


def strip_ansi(text: str) -> str:
    return _OTHER_ESC.sub("", _ANSI_RE.sub("", text or ""))


def ansi_to_html(text: str) -> str:
    """Escape *text* and turn SGR colour codes into <span style>."""
    text = _OTHER_ESC.sub("", text or "")
    out, pos = [], 0
    fg = bg = None
    bold = False
    open_span = False

    def span():
        nonlocal open_span
        if open_span:
            out.append("</span>")
            open_span = False
        st = []
        if fg:
            st.append(f"color:{fg}")
        if bg:
            st.append(f"background:{bg}")
        if bold:
            st.append("font-weight:bold")
        if st:
            out.append(f'<span style="{";".join(st)}">')
            open_span = True

    for m in _ANSI_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c.isdigit()] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                fg = bg = None
                bold = False
            elif c == 1:
                bold = True
            elif c == 22:
                bold = False
            elif 30 <= c <= 37:
                fg = _ANSI_COLORS[c - 30]
            elif 90 <= c <= 97:
                fg = _ANSI_BRIGHT[c - 90]
            elif c == 39:
                fg = None
            elif 40 <= c <= 47:
                bg = _ANSI_COLORS[c - 40]
            elif 100 <= c <= 107:
                bg = _ANSI_BRIGHT[c - 100]
            elif c == 49:
                bg = None
            elif c in (38, 48) and i + 2 < len(codes) and codes[i + 1] == 5:
                i += 2                                   # 256 colours: ignore, keep text readable
            elif c in (38, 48) and i + 4 < len(codes) and codes[i + 1] == 2:
                r, g, b = codes[i + 2:i + 5]
                if c == 38:
                    fg = f"rgb({r},{g},{b})"
                else:
                    bg = f"rgb({r},{g},{b})"
                i += 4
            i += 1
        span()
    out.append(html.escape(text[pos:]))
    if open_span:
        out.append("</span>")
    return "".join(out)


def apply_carriage_returns(text: str) -> str:
    """tqdm-style progress lines: keep only what follows the last \\r of each line."""
    if "\r" not in text and "\b" not in text:
        return text
    lines = []
    for line in text.split("\n"):
        if "\r" in line:
            line = next((p for p in reversed(line.split("\r")) if p), "")
        if "\b" in line:
            buf: list[str] = []
            for ch in line:
                if ch == "\b":
                    if buf:
                        buf.pop()
                else:
                    buf.append(ch)
            line = "".join(buf)
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------- markdown
def markdown_to_html(text: str, attachments: dict | None = None) -> str:
    try:
        import markdown as md
        body = md.markdown(text or "", extensions=["fenced_code", "tables", "sane_lists"],
                           output_format="html")
    except ImportError:                                 # minimal fallback: headings, bold, code, paragraphs
        body = _mini_markdown(text or "")
    if attachments:                                      # ![x](attachment:image.png)
        def att(m):
            name = m.group(1)
            data = attachments.get(name) or {}
            for mime, b64 in data.items():
                if mime.startswith("image/") and "svg" not in mime:
                    return f'src="data:{mime};base64,{b64 if isinstance(b64, str) else "".join(b64)}"'
            return m.group(0)
        body = re.sub(r'src="attachment:([^"]+)"', att, body)
    return sanitize(body)


def _mini_markdown(text: str) -> str:
    out, para, code = [], [], None
    for line in text.splitlines():
        if line.startswith("```"):
            if code is None:
                code = []
            else:
                out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m or not line.strip():
            if para:
                out.append("<p>" + _inline(" ".join(para)) + "</p>")
                para = []
            if m:
                n = len(m.group(1))
                out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>")
            continue
        para.append(line)
    if para:
        out.append("<p>" + _inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def _inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


# ---------------------------------------------------------------------- outputs
def _text(v) -> str:
    return "".join(v) if isinstance(v, list) else (v or "")


def mime_to_html(mime: str, value, metadata: dict | None = None) -> str:
    v = _text(value) if not isinstance(value, dict) else value
    if mime == "text/html":
        return f'<div class="rad-html">{sanitize(v)}</div>'
    if mime == "text/markdown":
        return f'<div class="rad-md">{markdown_to_html(v)}</div>'
    if mime == "image/svg+xml":
        return f'<div class="rad-img">{sanitize(v)}</div>'
    if mime in ("image/png", "image/jpeg", "image/gif"):
        b64 = re.sub(r"\s+", "", v)
        try:
            base64.b64decode(b64[:64] + "=" * (-len(b64[:64]) % 4))
        except Exception:  # noqa: BLE001
            return '<pre class="rad-err">[invalid image data]</pre>'
        meta = (metadata or {}).get(mime) if isinstance((metadata or {}).get(mime), dict) else (metadata or {})
        size = ""
        if isinstance(meta, dict):
            if meta.get("width"):
                size += f' width="{int(meta["width"])}"'
            if meta.get("height"):
                size += f' height="{int(meta["height"])}"'
        return f'<div class="rad-img"><img src="data:{mime};base64,{b64}"{size} alt="output image"></div>'
    if mime == "application/json":
        import json
        return "<pre>" + html.escape(json.dumps(value, indent=2)[:MAX_TEXT]) + "</pre>"
    return "<pre>" + ansi_to_html(v[:MAX_TEXT]) + "</pre>"


def output_to_html(o: dict) -> str:
    t = o.get("output_type")
    if t == "stream":
        text = apply_carriage_returns(_text(o.get("text")))
        more = ""
        if len(text) > MAX_TEXT:
            more = f'<div class="rad-more">... {len(text) - MAX_TEXT:,} more characters not shown</div>'
            text = text[-MAX_TEXT:]
        cls = "rad-stderr" if o.get("name") == "stderr" else "rad-stdout"
        return f'<pre class="{cls}">{ansi_to_html(text)}</pre>{more}'
    if t == "error":
        tb = o.get("traceback") or []
        body = "\n".join(tb) if tb else f"{o.get('ename', 'Error')}: {o.get('evalue', '')}"
        return f'<pre class="rad-err">{ansi_to_html(body)}</pre>'
    if t in ("display_data", "execute_result"):
        data = o.get("data") or {}
        for mime in MIME_ORDER:
            if mime in data:
                return mime_to_html(mime, data[mime], o.get("metadata"))
        for mime, val in data.items():                       # unknown types: show a note
            if mime.startswith("application/vnd.jupyter.widget"):
                return '<div class="rad-more">[interactive widget - not supported in RAD IDE yet]</div>'
        if data:
            return f'<div class="rad-more">[output of type {html.escape(", ".join(data))} not shown]</div>'
    return ""


def outputs_to_html(outputs: list) -> str:
    return "".join(f'<div class="rad-out">{output_to_html(o)}</div>' for o in outputs or [])


# ---------------------------------------------------------------------- export to HTML
_EXPORT_CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1000px; margin: 24px auto; padding: 0 16px;
       color: #1f1f1f; background: #fff; }
.cell { margin: 12px 0; }
.code { display: flex; gap: 8px; }
.prompt { color: #305f9e; font-family: Consolas, monospace; font-size: 13px; min-width: 64px; text-align: right;
          padding-top: 6px; }
.prompt.out { color: #b0371c; }
.src { flex: 1; background: #f7f7f7; border: 1px solid #e0e0e0; border-radius: 4px; padding: 6px 10px;
       overflow-x: auto; }
.src pre, pre { margin: 0; font-family: Consolas, 'Cascadia Mono', monospace; font-size: 13px; white-space: pre-wrap; }
.outputs { flex: 1; overflow-x: auto; padding: 4px 0; }
.rad-err { background: #fdecea; padding: 6px; }
.rad-stderr { background: #fff5e5; }
table { border-collapse: collapse; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 3px 8px; text-align: right; }
th { background: #f0f0f0; }
img { max-width: 100%; }
.md { padding: 0 72px; }
"""


def _highlight(code: str, language: str) -> str:
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        return highlight(code, get_lexer_by_name(language or "python"), HtmlFormatter(nowrap=True))
    except Exception:  # noqa: BLE001 - pygments missing or unknown language
        return html.escape(code)


def notebook_to_html(nb, title: str) -> str:
    try:
        from pygments.formatters import HtmlFormatter
        pyg_css = HtmlFormatter().get_style_defs(".src")
    except Exception:  # noqa: BLE001
        pyg_css = ""
    lang = nb.language
    parts = []
    for c in nb.cells:
        if c.cell_type == "markdown":
            parts.append(f'<div class="cell md">{markdown_to_html(c.source, c.attachments)}</div>')
        elif c.cell_type == "raw":
            parts.append(f'<div class="cell md"><pre>{html.escape(c.source)}</pre></div>')
        else:
            n = "" if c.execution_count is None else c.execution_count
            parts.append(f'<div class="cell"><div class="code"><div class="prompt">In [{n}]:</div>'
                         f'<div class="src"><pre>{_highlight(c.source, lang)}</pre></div></div>')
            if c.outputs:
                parts.append(f'<div class="code"><div class="prompt out"></div><div class="outputs">'
                             f'{outputs_to_html(c.outputs)}</div></div>')
            parts.append("</div>")
    return (f"<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<style>{_EXPORT_CSS}\n{pyg_css}</style></head>\n<body>\n<h1 style=\"display:none\">{html.escape(title)}"
            f"</h1>\n" + "\n".join(parts) + "\n</body></html>\n")
