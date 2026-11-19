"""Design view for web pages (Expression Web style), built on GrapesJS.

DesignView(win, path) is a tab for .html/.htm/.php files with three modes:
  Design - WYSIWYG canvas + Toolbox (blocks), Layers, CSS Properties (Style Manager), Attributes (traits)
  Split  - the canvas above and the Monaco code below, kept in sync both ways
  Code   - the code only

Saving writes the page back:
  * everything outside <body>...</body> (doctype, <head>, head scripts, PHP before <html>) is kept verbatim;
  * PHP code (<?php ... ?>, <?= ... ?>) and <script>/<style> blocks inside the body are *protected*: they are
    replaced by placeholders before the HTML goes to GrapesJS (a non-editable "code chip" component, an HTML
    comment inside tables/selects, or a token inside attribute values) and put back byte for byte on save;
  * CSS edited in the CSS Properties panel goes to the page's own <style> block in <head>, or - when the page has
    none but links a local stylesheet - to a marked region of that stylesheet, or to a new <style> block;
  * a page whose body was not edited is written back unchanged.

The pure functions (protect / restore / parse_page / compose / format_css) have no Qt dependency and are
unit-tested on their own.
"""
from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

GRAPES_DIR = Path(__file__).resolve().parent.parent / "web" / "grapes"
DESIGNER_HTML = GRAPES_DIR / "designer.html"
DESIGN_EXTS = {".html", ".htm", ".php", ".phtml", ".xhtml"}
BOOTSTRAP_CSS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
REGION_BEGIN = "/* ==== RAD IDE Design View styles (begin) - edited by the CSS Properties panel ==== */"
REGION_END = "/* ==== RAD IDE Design View styles (end) ==== */"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
        "wbr", "keygen", "command"}
RAWTEXT = {"script", "style", "textarea", "title", "xmp", "noembed", "noframes", "iframe", "noscript"}
RAWTEXT.discard("iframe")
RAWTEXT.discard("noscript")
# elements whose content model would move/drop an unknown element (foster parenting, <select> parsing)
TABLE_CTX = {"table", "thead", "tbody", "tfoot", "tr", "colgroup", "select", "optgroup", "datalist"}
P_CLOSERS = {"address", "article", "aside", "blockquote", "div", "dl", "fieldset", "footer", "form", "h1", "h2",
             "h3", "h4", "h5", "h6", "header", "hr", "main", "nav", "ol", "p", "pre", "section", "table", "ul",
             "figure", "details", "menu"}

_TAG_OPEN = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9:_-]*)")
_RAW_CHIP = re.compile(r"<rad-raw\b([^>]*)>(?:\s*</rad-raw\s*>)?", re.I)
_ATTR = re.compile(r"""([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")
_COMMENT_PH = re.compile(r"<!--radphp:(\d+)-->")
_ATTR_PH = re.compile(r"data-radphp-(\d+)(?:=(?:\"\"|''))?")
_TOKEN_PH = re.compile(r"__RADPHP_(\d+)__")


def is_designable(path) -> bool:
    return Path(path).suffix.lower() in DESIGN_EXTS


# ====================================================================== protection of PHP / script blocks
@dataclass
class Protected:
    text: str                                  # the document with placeholders
    blocks: dict[int, str] = field(default_factory=dict)   # id -> original code, byte for byte


def _is_php_open(s: str, i: int) -> bool:
    if s.startswith("<?=", i):
        return True
    if s[i:i + 5].lower() == "<?php":
        return i + 5 >= len(s) or s[i + 5] in " \t\r\n"
    if s.startswith("<?", i):          # short open tag "<? " (not <?xml)
        return i + 2 >= len(s) or s[i + 2] in " \t\r\n"
    return False


def _php_end(s: str, i: int) -> int:
    """Index just after the ?> that closes the PHP block starting at i (len(s) when unterminated)."""
    n = len(s)
    j = i + 2
    while j < n:
        c = s[j]
        if c == "?" and s.startswith("?>", j):
            return j + 2
        if c in "\"'`":
            k = j + 1
            while k < n and s[k] != c:
                k += 2 if s[k] == "\\" else 1
            j = k + 1
            continue
        if c == "#" or s.startswith("//", j):
            k = j
            while k < n and s[k] != "\n" and not s.startswith("?>", k):
                k += 1
            j = k
            continue
        if s.startswith("/*", j):
            k = s.find("*/", j + 2)
            j = n if k < 0 else k + 2
            continue
        if s.startswith("<<<", j):                       # heredoc / nowdoc
            m = re.match(r"<<<[ \t]*(['\"]?)([A-Za-z_]\w*)\1\r?\n", s[j:])
            if m:
                end = re.compile(r"\n[ \t]*" + re.escape(m.group(2)) + r"\b").search(s, j + m.end() - 1)
                j = n if end is None else end.end()
                continue
        j += 1
    return n


def make_label(code: str, limit: int = 70) -> str:
    one = " ".join(code.split())
    return one if len(one) <= limit else one[:limit - 3] + "..."


def _chip(k: int, code: str) -> str:
    return f'<rad-raw data-rad-id="{k}" data-rad-label="{_html.escape(make_label(code), quote=True)}"></rad-raw>'


def protect(text: str) -> Protected:
    """Replace PHP blocks (everywhere) and <script>/<style> blocks (inside the body) by placeholders."""
    out: list[str] = []
    blocks: dict[int, str] = {}
    stack: list[str] = []
    n = len(text)
    i = 0
    state = "text"            # text | tag | attr | comment | raw
    quote = ""
    tagname = ""
    is_end = False
    raw_tag = ""
    no_php = re.sub(r"<\?(?:php|=)?[\s\S]*?(?:\?>|$)", "", text)
    in_body = re.search(r"<body[\s>/]", no_php, re.I) is None

    def add(code: str) -> int:
        k = len(blocks)
        blocks[k] = code
        return k

    def text_placeholder(k: int, code: str) -> str:
        if not in_body:
            return f"__RADPHP_{k}__"
        top = stack[-1] if stack else ""
        if top in TABLE_CTX:
            return f"<!--radphp:{k}-->"
        return _chip(k, code)

    def open_tag(name: str, self_closing: bool):
        nonlocal in_body, state, raw_tag
        if name == "body":
            in_body = True
        top = stack[-1] if stack else ""
        if name in ("li",) and top == "li":
            stack.pop()
        elif name in ("td", "th") and top in ("td", "th"):
            stack.pop()
        elif name == "tr":
            while stack and stack[-1] in ("td", "th", "tr"):
                stack.pop()
        elif name in ("option", "optgroup") and top == "option":
            stack.pop()
        elif name in P_CLOSERS and top == "p":
            stack.pop()
        if name in RAWTEXT:
            state, raw_tag = "raw", name
            return
        if name not in VOID and not self_closing:
            stack.append(name)

    def close_tag(name: str):
        if name in stack:
            while stack:
                if stack.pop() == name:
                    break

    while i < n:
        c = text[i]
        if c == "<" and text.startswith("<?", i) and _is_php_open(text, i):
            end = _php_end(text, i)
            code = text[i:end]
            k = add(code)
            if state == "text":
                out.append(text_placeholder(k, code))
            elif state == "tag":
                out.append(f'data-radphp-{k}=""')
            else:                                   # attr value, comment, raw text
                out.append(f"__RADPHP_{k}__")
            i = end
            continue
        if state == "text":
            if text.startswith("<!--", i):
                state = "comment"
                out.append("<!--")
                i += 4
                continue
            m = _TAG_OPEN.match(text, i) if c == "<" else None
            if m:
                is_end = bool(m.group(1))
                tagname = m.group(2).lower()
                if not is_end and in_body and tagname in ("script", "style"):
                    em = re.compile(r"</%s\s*>" % tagname, re.I).search(text, m.end())
                    end = n if em is None else em.end()
                    code = text[i:end]
                    k = add(code)
                    out.append(text_placeholder(k, code))
                    i = end
                    continue
                out.append(m.group(0))
                i = m.end()
                state = "tag"
                continue
            out.append(c)
            i += 1
            continue
        if state == "comment":
            if text.startswith("-->", i):
                state = "text"
                out.append("-->")
                i += 3
                continue
            out.append(c)
            i += 1
            continue
        if state == "tag":
            if c in "\"'":
                state, quote = "attr", c
            elif c == ">":
                out.append(c)
                i += 1
                state = "text"
                if is_end:
                    close_tag(tagname)
                else:
                    j = len(out) - 2
                    while j >= 0 and out[j].isspace():
                        j -= 1
                    open_tag(tagname, j >= 0 and out[j].endswith("/"))
                continue
            out.append(c)
            i += 1
            continue
        if state == "attr":
            if c == quote:
                state = "tag"
            out.append(c)
            i += 1
            continue
        # raw text element content (<script> in the head, <textarea>, <title>, ...)
        if c == "<" and re.match(r"</%s[\s>/]" % raw_tag, text[i:i + len(raw_tag) + 3], re.I):
            state = "text"
            continue
        out.append(c)
        i += 1

    result = "".join(out)
    # inline style="" attributes are kept as written: GrapesJS would move them into generated #id / class rules
    # (and break the ones that contain PHP). The canvas still shows them (designer.js copies data-radstyle into
    # style) and the Attributes panel edits them as "Inline style".
    result = re.sub(r"""(\s)style(\s*=\s*)("[^"]*"|'[^']*')""", r"\1data-radstyle\2\3", result)
    return Protected(result, blocks)


def _chip_code(attrs: str, blocks: dict[int, str]) -> str | None:
    a = {}
    for m in _ATTR.finditer(attrs):
        a[m.group(1).lower()] = m.group(2) if m.group(2) is not None else (
            m.group(3) if m.group(3) is not None else m.group(4))
    if "data-rad-code" in a:
        return _html.unescape(a["data-rad-code"])
    rid = a.get("data-rad-id", "")
    if rid.isdigit() and int(rid) in blocks:
        return blocks[int(rid)]
    return None


def restore(text: str, blocks: dict[int, str]) -> str:
    """Put the protected code back (inverse of protect)."""
    def closed(code: str, m) -> str:
        # a PHP block that ran to the end of the file ("<?php page_footer();") must be closed when the
        # design put markup after it
        if code.startswith("<?") and not code.rstrip().endswith("?>") and m.string[m.end():].strip():
            return code + ("" if code.endswith("\n") else "\n") + "?>"
        return code

    def chip(m):
        code = _chip_code(m.group(1), blocks)
        return m.group(0) if code is None else closed(code, m)

    def by_id(m):
        k = int(m.group(1))
        return closed(blocks[k], m) if k in blocks else m.group(0)

    text = re.sub(r"(\s)data-radstyle(\s*=)", r"\1style\2", text)
    text = _RAW_CHIP.sub(chip, text)
    text = _COMMENT_PH.sub(by_id, text)
    text = _ATTR_PH.sub(by_id, text)
    text = _TOKEN_PH.sub(by_id, text)
    return text


# ====================================================================== page structure
@dataclass
class PageParts:
    blocks: dict[int, str]
    prefix: str              # protected text up to and including <body ...>
    body: str                # protected body content (what GrapesJS edits)
    suffix: str              # </body> ... end
    has_head: bool = False
    style_span: tuple[int, int] | None = None     # span of the editable <style> content inside prefix
    css: str = ""            # CSS loaded into the CSS Properties panel
    extra_css: str = ""      # other <style> blocks of the head (shown in the canvas only)
    links: list[str] = field(default_factory=list)  # hrefs of <link rel=stylesheet> (as written)
    body_class: str = ""
    css_target: str = "style"     # "style" (page <style>), "sheet" (linked stylesheet region), "new"
    sheet_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


def _attr_value(tag: str, name: str) -> str | None:
    for m in _ATTR.finditer(tag):
        if m.group(1).lower() == name:
            v = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
            return _html.unescape(v)
    return None


def _local_sheet(href: str, page: Path, site_root: Path | None) -> Path | None:
    if not href or "__RADPHP_" in href or re.match(r"^[a-z][a-z0-9+.-]*:|^//", href, re.I):
        return None
    href = href.split("?")[0].split("#")[0]
    if href.startswith("/"):
        base = site_root or page.parent
        p = base / href.lstrip("/")
    else:
        p = page.parent / href
    return p if p.suffix.lower() == ".css" else None


def read_region(sheet_text: str) -> tuple[str, tuple[int, int] | None]:
    b = sheet_text.find(REGION_BEGIN)
    e = sheet_text.find(REGION_END, b + 1) if b >= 0 else -1
    if b < 0 or e < 0:
        return "", None
    start = b + len(REGION_BEGIN)
    return sheet_text[start:e], (start, e)


def parse_page(text: str, path: Path | None = None, site_root: Path | None = None) -> PageParts:
    prot = protect(text)
    p = prot.text
    bm = re.search(r"<body\b[^>]*>", p, re.I)
    if bm:
        ends = [m for m in re.finditer(r"</body\s*>", p, re.I)]
        if ends and ends[-1].start() >= bm.end():
            end = ends[-1].start()
        else:
            hm = list(re.finditer(r"</html\s*>", p, re.I))
            end = hm[-1].start() if hm and hm[-1].start() >= bm.end() else len(p)
        prefix, body, suffix = p[:bm.end()], p[bm.end():end], p[end:]
    else:
        hm = re.search(r"</head\s*>", p, re.I)
        if hm:
            hend = list(re.finditer(r"</html\s*>", p, re.I))
            end = hend[-1].start() if hend and hend[-1].start() >= hm.end() else len(p)
            prefix, body, suffix = p[:hm.end()], p[hm.end():end], p[end:]
        else:
            # a layout include such as footer.php: "... </body></html>" without a start tag
            tails = list(re.finditer(r"</body\s*>|</html\s*>", p, re.I))
            end = tails[0].start() if tails else len(p)
            prefix, body, suffix = "", p[:end], p[end:]
    parts = PageParts(prot.blocks, prefix, body, suffix)
    parts.has_head = re.search(r"</head\s*>", prefix, re.I) is not None
    if bm:
        cls = _attr_value(bm.group(0), "class")
        parts.body_class = "" if cls is None or "__RADPHP_" in cls else cls
    extra = []
    for m in re.finditer(r"<style\b[^>]*>([\s\S]*?)</style\s*>", prefix, re.I):
        content = m.group(1)
        if parts.style_span is None and "__RADPHP_" not in content:
            parts.style_span = (m.start(1), m.end(1))
            parts.css = content
        else:
            extra.append(restore(content, prot.blocks))
    parts.extra_css = "\n".join(extra)
    for m in re.finditer(r"<link\b[^>]*>", prefix, re.I):
        tag = m.group(0)
        rel = (_attr_value(tag, "rel") or "").lower()
        href = _attr_value(tag, "href")
        if "stylesheet" in rel and href:
            parts.links.append(href)
    if parts.style_span is not None:
        parts.css_target = "style"
    else:
        sheet = None
        if path is not None:
            for href in parts.links:
                s = _local_sheet(href, Path(path), site_root)
                if s is not None and s.is_file():
                    sheet = s
                    break
        if sheet is not None:
            parts.css_target, parts.sheet_path = "sheet", sheet
            try:
                parts.css = read_region(sheet.read_text(encoding="utf-8-sig"))[0]
            except OSError:
                parts.css = ""
        else:
            parts.css_target = "new"
    # PHP that opens/closes HTML elements (e.g. if/else around a start tag) cannot be designed safely
    if _unbalanced(body):
        parts.warnings.append("The page body has unbalanced HTML tags (PHP may open or close elements "
                              "conditionally). Editing it in Design view can change its structure - prefer Split or "
                              "Code view for such regions.")
    return parts


def _unbalanced(body: str) -> bool:
    stack: list[str] = []
    for m in re.finditer(r"<(/?)([A-Za-z][A-Za-z0-9-]*)\b[^>]*?(/?)>", re.sub(r"<!--[\s\S]*?-->", "", body)):
        name = m.group(2).lower()
        if name in VOID or m.group(3) or name in ("p", "li", "td", "th", "tr", "option", "rad-raw", "thead",
                                                   "tbody", "tfoot", "dt", "dd", "colgroup", "optgroup"):
            continue
        if m.group(1):
            if not stack or stack[-1] != name:
                return True
            stack.pop()
        else:
            stack.append(name)
    return bool(stack)


# ====================================================================== CSS formatting
def format_css(css: str, indent: str = "  ", base: str = "") -> str:
    """Pretty-print the compact CSS GrapesJS produces: one declaration per line, nested @media blocks."""
    css = css.strip()
    out: list[str] = []
    depth = 0
    buf = ""
    i = 0
    n = len(css)
    quote = ""
    while i < n:
        c = css[i]
        if quote:
            buf += c
            if c == quote and css[i - 1] != "\\":
                quote = ""
            i += 1
            continue
        if c in "\"'":
            quote = c
            buf += c
        elif css.startswith("/*", i):
            e = css.find("*/", i + 2)
            e = n if e < 0 else e + 2
            if buf.strip():
                buf += css[i:e]
            else:
                out.append(base + indent * depth + css[i:e])
            i = e
            continue
        elif c == "{":
            out.append(base + indent * depth + " ".join(buf.split()) + " {")
            depth += 1
            buf = ""
        elif c == "}":
            if buf.strip():
                out.append(base + indent * depth + buf.strip() + ";")
            buf = ""
            depth = max(0, depth - 1)
            out.append(base + indent * depth + "}")
        elif c == ";":
            if buf.strip():
                stmt = buf.strip()
                out.append(base + indent * depth + (stmt if depth == 0 else re.sub(r"\s*:\s*", ": ", stmt, 1)) + ";")
            buf = ""
        else:
            buf += c
        i += 1
    if buf.strip():
        out.append(base + indent * depth + buf.strip())
    return "\n".join(out)


def _css_at_rules(css: str) -> list[str]:
    """@charset / @import statements GrapesJS does not keep."""
    return re.findall(r"@(?:charset|import)\b[^;]*;", css, re.I)


# ====================================================================== composing the saved page
@dataclass
class Composed:
    text: str
    files: dict[Path, str] = field(default_factory=dict)     # other files to write (linked stylesheet)


def compose(parts: PageParts, html: str | None = None, css: str | None = None,
            html_changed: bool = False, css_changed: bool = False) -> Composed:
    prefix, body, suffix = parts.prefix, parts.body, parts.suffix
    files: dict[Path, str] = {}
    body_r = None                  # restored body when the design changed it
    if html_changed and html is not None:
        # GrapesJS trims the body: keep the original leading / trailing white space
        lead = re.match(r"\s*", body).group(0)
        trail = body[len(body.rstrip()):]
        html = _reentity(html, body)
        new = (lead + html.strip() + trail) if html.strip() else "\n"
        body_r = _fix_dangling(restore(new, parts.blocks), restore(body, parts.blocks))
        body = new
    if css_changed and css is not None:
        keep = [r for r in _css_at_rules(parts.css) if r not in css]
        full = "\n".join(keep + ([css] if css.strip() else []))
        if parts.css_target == "style" and parts.style_span is not None:
            s, e = parts.style_span
            line_start = prefix.rfind("\n", 0, s) + 1
            tag_indent = re.match(r"[ \t]*", prefix[line_start:]).group(0)
            content = "\n" + format_css(full, base=tag_indent + "  ") + "\n" + tag_indent if full.strip() else ""
            prefix = prefix[:s] + content + prefix[e:]
        elif parts.css_target == "sheet" and parts.sheet_path is not None:
            try:
                sheet = parts.sheet_path.read_text(encoding="utf-8-sig")
            except OSError:
                sheet = ""
            region = "\n" + format_css(full) + "\n" if full.strip() else "\n"
            _old, span = read_region(sheet)
            if span is None:
                sheet = sheet.rstrip("\n") + ("\n\n" if sheet.strip() else "") + REGION_BEGIN + region + REGION_END + "\n"
            else:
                sheet = sheet[:span[0]] + region + sheet[span[1]:]
            files[parts.sheet_path] = sheet
        elif full.strip():
            hm = re.search(r"</head\s*>", prefix, re.I)
            if hm:
                line_start = prefix.rfind("\n", 0, hm.start()) + 1
                head_indent = prefix[line_start:hm.start()]
                if head_indent.strip():                 # </head> shares its line with other markup
                    line_start, head_indent = hm.start(), ""
                ind = head_indent + "  "
                block = f"{ind}<style>\n{format_css(full, base=ind + '  ')}\n{ind}</style>\n"
                prefix = prefix[:line_start] + block + prefix[line_start:]
            else:
                block = "<style>\n" + format_css(full, base="  ") + "\n</style>\n"
                body = block + body
                if body_r is not None:
                    body_r = block + body_r
    if body_r is None:
        body_r = restore(body, parts.blocks)
    return Composed(restore(prefix, parts.blocks) + body_r + restore(suffix, parts.blocks), files)


_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#[xX][0-9A-Fa-f]+);")


def _reentity(html: str, original: str) -> str:
    """GrapesJS writes &copy; / &middot; / &#1575; as plain characters: put back the entities the page used."""
    for ent in set(_ENTITY.findall(original)):
        ch = _html.unescape(ent)
        if len(ch) == 1 and ch not in "&<>\"'" and ch not in original and ch in html:
            html = html.replace(ch, ent)
    return html


def _tag_balance(body: str) -> tuple[list[str], list[str]]:
    """(end tags without a start tag, start tags never closed) of an HTML fragment (layout includes)."""
    stray: list[str] = []
    stack: list[str] = []
    implicit = {"p", "li", "td", "th", "tr", "option", "thead", "tbody", "tfoot", "dt", "dd", "colgroup",
                "optgroup", "rad-raw"}
    body = re.sub(r"<\?(?:php|=)?[\s\S]*?(?:\?>|$)", "", re.sub(r"<!--[\s\S]*?-->", "", body))
    for m in re.finditer(r"<(/?)([A-Za-z][A-Za-z0-9-]*)\b[^>]*?(/?)>", body):
        name = m.group(2).lower()
        if name in VOID or m.group(3) or name in implicit:
            continue
        if m.group(1):
            if name in stack:
                while stack and stack.pop() != name:
                    pass
            else:
                stray.append(name)
        else:
            stack.append(name)
    return stray, stack


def _fix_dangling(new: str, original: str) -> str:
    """A layout include may open <main> (header.php) or close it (footer.php). The browser parser used by
    GrapesJS adds the missing end tags and drops the stray ones: undo both (on restored text)."""
    stray, unclosed = _tag_balance(original)
    for name in reversed(unclosed):
        pat = re.compile(r"</%s\s*>" % re.escape(name), re.I)
        extra = len(pat.findall(new)) - len(pat.findall(original))
        while extra > 0:
            last = list(pat.finditer(new))[-1]
            new = new[:last.start()] + new[last.end():]
            extra -= 1
    if stray:
        alt = "|".join(map(re.escape, stray))
        missing = any(len(re.findall(r"</%s\s*>" % n, new, re.I)) < len(re.findall(r"</%s\s*>" % n, original, re.I))
                      for n in stray)
        first = re.search(r"</(?:%s)\s*>" % alt, original, re.I)
        if missing and first is not None:
            pre = original[:first.start()].rstrip()
            closers = re.match(r"(?:\s*</(?:%s)\s*>)+" % alt, original[first.start():], re.I).group(0)
            if new.startswith(pre):
                rest = new[len(pre):]
                ws = original[len(pre):first.start()]
                new = pre + ws + closers.lstrip() + (rest if rest[:1] in "\r\n" else "\n" + rest.lstrip(" \t"))
            else:
                new = closers.lstrip() + "\n" + new
    return new


def add_head_link(parts: PageParts, href: str) -> bool:
    """Insert <link rel="stylesheet" href=...> into the head (False when the page has no <head>)."""
    if href in parts.links:
        return True
    hm = re.search(r"</head\s*>", parts.prefix, re.I)
    if not hm:
        return False
    line_start = parts.prefix.rfind("\n", 0, hm.start()) + 1
    indent = re.match(r"[ \t]*", parts.prefix[line_start:]).group(0)
    before = parts.prefix[:hm.start()]
    ins = f'  <link rel="stylesheet" href="{_html.escape(href, quote=True)}">\n' + indent
    if not before.endswith(indent):
        ins = "\n" + ins
    else:
        before = before[:len(before) - len(indent)] if indent else before
        ins = indent + ins
    shift = len(before) + len(ins) - hm.start()
    if parts.style_span is not None and parts.style_span[0] > hm.start():
        parts.style_span = (parts.style_span[0] + shift, parts.style_span[1] + shift)
    parts.prefix = before + ins + parts.prefix[hm.start():]
    parts.links.append(href)
    return True


def canvas_styles(parts: PageParts, path: Path, site_root: Path | None = None) -> list[str]:
    """URLs of the page's stylesheets for the design canvas."""
    from urllib.parse import urljoin
    from urllib.request import pathname2url
    out = []
    for href in parts.links:
        if "__RADPHP_" in href:
            continue
        if re.match(r"^https?:", href, re.I):
            out.append(href)
        elif href.startswith("//"):
            out.append("https:" + href)
        else:
            local = _local_sheet(href, path, site_root)
            if local is not None:
                out.append("file:" + pathname2url(str(local.resolve())))
            elif not re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
                out.append(urljoin("file:" + pathname2url(str(path.parent.resolve())) + "/", href))
    return out


def read_text_file(path: Path) -> tuple[str, dict]:
    """Read a page keeping what is needed to write it back the same way (BOM, line ends)."""
    data = path.read_bytes()
    bom = data.startswith(b"\xef\xbb\xbf")
    try:
        text = data.decode("utf-8-sig")
        enc = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
        enc = "cp1252"
    crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), {"bom": bom, "crlf": crlf, "encoding": enc}


def write_text_file(path: Path, text: str, info: dict) -> None:
    if info.get("crlf"):
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    data = text.encode(info.get("encoding", "utf-8"), errors="replace")
    if info.get("bom"):
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


# ====================================================================== Qt widget
try:
    from PyQt6.QtCore import QEventLoop, QObject, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QAction, QActionGroup, QFont
    from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QPlainTextEdit,
                                 QSplitter, QToolBar, QVBoxLayout, QWidget)
    _HAVE_QT = True
except ImportError:            # pragma: no cover - the pure functions stay usable
    _HAVE_QT = False


def _site_root_for(win, path: Path) -> Path | None:
    proj = getattr(win, "project", None)
    if getattr(proj, "folder", None) is None:
        return None
    try:
        from .project import is_website, site_root
        if not is_website(proj):
            return None
        root = Path(site_root(proj))
    except Exception:  # noqa: BLE001 - web-core helpers missing: no site root ("/x.css" = page folder)
        return None
    try:
        path.resolve().relative_to(root.resolve())
        return root
    except (ValueError, OSError):
        return None


def _plugin_for(win, path: Path):
    try:
        from .project import file_plugin
        return file_plugin(path, getattr(win, "project", None))
    except Exception:  # noqa: BLE001
        pass
    from ..languages import get_plugin
    ext = path.suffix.lower()
    order = ["php-web", "php"] if ext in (".php", ".phtml") else ["static-web", "javascript", "php-web", "php"]
    for pid in order:
        try:
            return get_plugin(pid)
        except Exception:  # noqa: BLE001
            continue
    return getattr(win, "plugin", None)


if _HAVE_QT:
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    class _DesignBridge(QObject):
        def __init__(self, view: "DesignView"):
            super().__init__()
            self.view = view

        @pyqtSlot()
        def jsReady(self):
            self.view._on_ready()

        @pyqtSlot()
        def jsChanged(self):
            self.view._on_design_changed()

        @pyqtSlot(str)
        def jsSelected(self, desc):
            self.view.selectionChanged.emit(desc)

        @pyqtSlot(str, str, str, bool)
        def jsEditRaw(self, cid, rid, code, has_code):
            self.view._edit_raw(cid, rid, code if has_code else None)

    class _Page(QWebEnginePage):
        def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802 - Qt override
            if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                print(f"[design] {message} ({source}:{line})")

    class CodeBlockDialog(QDialog):
        def __init__(self, code: str, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Edit code block")
            self.resize(620, 360)
            self.edit = QPlainTextEdit(code)
            self.edit.setFont(QFont("Consolas", 10))
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.accepted.connect(self.accept)
            bb.rejected.connect(self.reject)
            lay = QVBoxLayout(self)
            lay.addWidget(QLabel("PHP / script code kept verbatim in the page:"))
            lay.addWidget(self.edit)
            lay.addWidget(bb)

    class DesignView(QWidget):
        """Design / Split / Code tab for a web page."""
        modifiedChanged = pyqtSignal(bool)
        selectionChanged = pyqtSignal(str)
        saved = pyqtSignal(str)
        ready = pyqtSignal()

        MODES = ("design", "split", "code")
        DEVICES = (("Desktop", "desktop"), ("Tablet (770)", "tablet"), ("Phone landscape (568)", "mobileLandscape"),
                   ("Phone portrait (320)", "mobilePortrait"))

        def __init__(self, win, path, parent=None, mode: str = "design"):
            super().__init__(parent)
            self.win = win
            self.path = Path(path).resolve()
            self.site_root = _site_root_for(win, self.path)
            self._saved_text, self._file_info = read_text_file(self.path)
            self._text = self._saved_text            # current text of the page (latest known)
            self._parts = parse_page(self._text, self.path, self.site_root)
            self._loaded_text = None                  # text the design canvas was loaded from
            self._design_text = None                  # text the design canvas currently represents
            self._dirty_side = None                   # "design" | "code" | None: where the newest edit is
            self._modified = False
            self._ready = False
            self._mode = "design"
            self._pending_js: list[str] = []
            self._last_composed: Composed | None = None
            self.setProperty("radPath", str(self.path))

            # ---------------- toolbar
            self.toolbar = tb = QToolBar()
            grp = QActionGroup(self)
            self.mode_actions = {}
            for m, text, tip in (("design", "Design", "WYSIWYG design surface"),
                                 ("split", "Split", "Design surface and code, kept in sync"),
                                 ("code", "Code", "Code only")):
                a = QAction(text, self, checkable=True)
                a.setToolTip(tip)
                a.triggered.connect(lambda _=False, m_=m: self.set_mode(m_))
                grp.addAction(a)
                tb.addAction(a)
                self.mode_actions[m] = a
            tb.addSeparator()
            self.device = QComboBox()
            for text, _dev in self.DEVICES:
                self.device.addItem(text)
            self.device.setToolTip("Device size of the design surface")
            self.device.currentIndexChanged.connect(lambda i: self._js(f"radDevice({json.dumps(self.DEVICES[i][1])});"))
            tb.addWidget(self.device)
            tb.addSeparator()
            self.a_undo = tb.addAction("Undo", self.undo)
            self.a_redo = tb.addAction("Redo", self.redo)
            tb.addSeparator()
            self.a_borders = QAction("Borders", self, checkable=True, checked=True)
            self.a_borders.setToolTip("Show the outline of every element")
            self.a_borders.toggled.connect(lambda on: self._js(f"radBorders({json.dumps(on)});"))
            tb.addAction(self.a_borders)
            self.a_panels = QAction("Panels", self, checkable=True, checked=True)
            self.a_panels.setToolTip("Toolbox / Layers / CSS Properties / Attributes panel")
            self.a_panels.toggled.connect(lambda on: self._js(f"radToggleSide({json.dumps(on)});"))
            tb.addAction(self.a_panels)
            self.a_preview = QAction("Preview", self, checkable=True)
            self.a_preview.setToolTip("Preview the page without the editing helpers")
            self.a_preview.toggled.connect(lambda on: self._js(f"radPreview({json.dumps(on)});"))
            tb.addAction(self.a_preview)
            tb.addSeparator()
            self.a_bootstrap = tb.addAction("+ Bootstrap", self.add_bootstrap)
            self.a_bootstrap.setToolTip("Link Bootstrap 5 CSS (CDN) in the page head for the Bootstrap blocks")
            self.a_save = tb.addAction("Save", self.save)
            tb.addSeparator()
            self.css_label = QLabel()
            self.css_label.setProperty("radRole", "muted")
            tb.addWidget(self.css_label)

            self.banner = QLabel()
            self.banner.setWordWrap(True)
            self.banner.setProperty("radRole", "banner")
            self.banner.hide()

            # ---------------- design surface
            self.web = QWebEngineView()
            self.web.setPage(_Page(self.web))
            s = self.web.page().settings()
            for attr in ("LocalContentCanAccessFileUrls", "LocalContentCanAccessRemoteUrls"):
                s.setAttribute(getattr(QWebEngineSettings.WebAttribute, attr), True)
            self._bridge = _DesignBridge(self)
            self._channel = QWebChannel(self.web.page())
            self._channel.registerObject("rad", self._bridge)
            self.web.page().setWebChannel(self._channel)
            self.web.load(QUrl.fromLocalFile(str(DESIGNER_HTML)))

            # ---------------- code
            self.code = None
            self.splitter = QSplitter(Qt.Orientation.Vertical)
            self.splitter.addWidget(self.web)
            self._make_code()

            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            lay.addWidget(tb)
            lay.addWidget(self.banner)
            lay.addWidget(self.splitter, 1)

            self._design_timer = QTimer(self, singleShot=True, interval=250)
            self._design_timer.timeout.connect(self._pull_design)
            self._code_timer = QTimer(self, singleShot=True, interval=700)
            self._code_timer.timeout.connect(self._push_code_to_design)
            self._update_css_label()
            self._show_warnings()
            self.set_mode(mode if mode in self.MODES else "design")

        # ------------------------------------------------------------ setup helpers
        def _make_code(self):
            plugin = _plugin_for(self.win, self.path)
            try:
                from ..editor import make_editor
                self.code = make_editor(plugin, self.path)
            except Exception:  # noqa: BLE001 - fall back to a plain text box
                self.code = QPlainTextEdit()
                self.code.text = self.code.toPlainText
                self.code.setText = self.code.setPlainText
            self.code.setText(self._text)
            if hasattr(self.code, "setModified"):
                self.code.setModified(False)
            sig = getattr(self.code, "textEdited", None) or getattr(self.code, "textChanged", None)
            if sig is not None:
                sig.connect(self._on_code_edited)
            self.splitter.addWidget(self.code)
            self.splitter.setStretchFactor(0, 3)
            self.splitter.setStretchFactor(1, 2)

        def _code_text(self) -> str:
            t = self.code.text() if callable(getattr(self.code, "text", None)) else self.code.toPlainText()
            return t.replace("\r\n", "\n")

        def _set_code_text(self, text: str):
            if self._code_text() == text:
                return
            self._muted_code = True
            try:
                old = self._code_text()
                if hasattr(self.code, "_replace_range"):
                    # replace only the changed middle part: keeps Monaco's undo stack and scroll position
                    a = 0
                    m = min(len(old), len(text))
                    while a < m and old[a] == text[a]:
                        a += 1
                    b = 0
                    while b < m - a and old[len(old) - 1 - b] == text[len(text) - 1 - b]:
                        b += 1

                    def lc(s, pos):
                        line = s.count("\n", 0, pos)
                        return line, pos - (s.rfind("\n", 0, pos) + 1)
                    l1, c1 = lc(old, a)
                    l2, c2 = lc(old, len(old) - b)
                    self.code._replace_range(l1, c1, l2, c2, text[a:len(text) - b])
                else:
                    self.code.setText(text)
            finally:
                self._muted_code = False

        def _show_warnings(self):
            w = list(self._parts.warnings)
            self.banner.setText("  ".join(w))
            self.banner.setVisible(bool(w))

        def _update_css_label(self):
            p = self._parts
            if p.css_target == "style":
                t = "CSS -> <style> of this page"
            elif p.css_target == "sheet" and p.sheet_path is not None:
                try:
                    rel = p.sheet_path.resolve().relative_to(self.path.parent)
                except ValueError:
                    rel = p.sheet_path.name
                t = f"CSS -> {rel} (Design View region)"
            else:
                t = "CSS -> new <style> in this page"
            self.css_label.setText(t)

        # ------------------------------------------------------------ JS plumbing
        def _js(self, code: str, callback=None):
            if callback is None:
                # never let QtWebEngine serialise the completion value (a GrapesJS model is huge and cyclic:
                # converting it freezes the page)
                code = code.rstrip().rstrip(";") + "; void 0;"
            if not self._ready:
                if callback is None:
                    self._pending_js.append(code)
                return
            if callback is None:
                self.web.page().runJavaScript(code)
            else:
                self.web.page().runJavaScript(code, callback)

        def _eval_sync(self, code: str, timeout: int = 5000):
            if not self._ready:
                return None
            box = {}
            loop = QEventLoop(self)

            def done(v):
                box["v"] = v
                loop.quit()
            self.web.page().runJavaScript(code, done)
            QTimer.singleShot(timeout, loop.quit)
            if "v" not in box:
                loop.exec()
            return box.get("v")

        def _on_ready(self):
            self._ready = True
            self._load_design(self._text)
            for code in self._pending_js:
                self.web.page().runJavaScript(code)
            self._pending_js.clear()
            self.ready.emit()

        def is_ready(self) -> bool:
            return self._ready

        def _payload(self) -> dict:
            from urllib.request import pathname2url
            p = self._parts
            base = "file:" + pathname2url(str(self.path.parent)) + "/"
            return {"html": p.body, "css": p.css, "styles": canvas_styles(p, self.path, self.site_root),
                    "extraCss": p.extra_css, "base": base, "bodyClass": p.body_class}

        def _load_design(self, text: str):
            self._parts = parse_page(text, self.path, self.site_root)
            self._loaded_text = text
            self._design_text = text
            self._show_warnings()
            self._update_css_label()
            if self._ready:
                self.web.page().runJavaScript(f"radLoad({json.dumps(self._payload())});")
            if self._dirty_side == "code":
                self._dirty_side = None

        # ------------------------------------------------------------ design <-> code
        def _on_design_changed(self):
            if self._loaded_text is None:
                return
            self._dirty_side = "design"
            self._design_timer.start()

        def _compose_from(self, result) -> Composed | None:
            try:
                d = json.loads(result) if isinstance(result, str) else None
            except ValueError:
                d = None
            if not d:
                return None
            return compose(self._parts, d.get("html"), d.get("css"), bool(d.get("htmlChanged")),
                           bool(d.get("cssChanged")))

        def _pull_design(self):
            if not self._ready:
                return
            self.web.page().runJavaScript("radExport()", self._got_design)

        def _got_design(self, result):
            comp = self._compose_from(result)
            if comp is None:
                return
            self._last_composed = comp
            self._text = self._design_text = comp.text
            if self._mode == "split":
                self._set_code_text(comp.text)
            self._set_modified(comp.text != self._saved_text or self._files_differ(comp))

        def _files_differ(self, comp: Composed) -> bool:
            for p, t in comp.files.items():
                try:
                    if read_text_file(p)[0] != t:
                        return True
                except OSError:
                    return True
            return False

        _muted_code = False

        def _on_code_edited(self, *a):
            if self._muted_code:
                return
            self._text = self._code_text()
            self._dirty_side = "code"
            self._set_modified(self._text != self._saved_text)
            if self._mode == "split":
                self._code_timer.start()

        def _push_code_to_design(self):
            if self._dirty_side == "code" and self._text != self._design_text:
                self._load_design(self._text)
            self._dirty_side = None

        def sync_now(self) -> str:
            """Bring self._text up to date with the newest edit (design or code) and return it."""
            if self._dirty_side == "code" or self._mode == "code":
                self._text = self._code_text()
            elif self._dirty_side == "design" and self._ready:
                self._design_timer.stop()
                comp = self._compose_from(self._eval_sync("radExport()"))
                if comp is not None:
                    self._last_composed = comp
                    self._text = self._design_text = comp.text
            return self._text

        # ------------------------------------------------------------ modes
        def mode(self) -> str:
            return self._mode

        def set_mode(self, mode: str):
            if mode not in self.MODES:
                return
            old = self._mode
            if old != mode:
                text = self.sync_now()
                if mode in ("design", "split") and text != self._design_text:
                    self._load_design(text)
                if mode in ("code", "split"):
                    self._set_code_text(text)
                self._dirty_side = None
            self._mode = mode
            self.mode_actions[mode].setChecked(True)
            self.web.setVisible(mode in ("design", "split"))
            self.code.setVisible(mode in ("code", "split"))
            for a in (self.a_borders, self.a_panels, self.a_preview, self.a_bootstrap, self.a_undo, self.a_redo):
                a.setEnabled(mode != "code")
            self.device.setEnabled(mode != "code")
            if mode == "split":
                h = max(self.splitter.height(), 400)
                self.splitter.setSizes([h * 3 // 5, h * 2 // 5])

        # ------------------------------------------------------------ commands
        def undo(self):
            self._js("radUndo();")

        def redo(self):
            self._js("radRedo();")

        def set_device(self, name: str):
            for i, (_t, dev) in enumerate(self.DEVICES):
                if dev == name:
                    self.device.setCurrentIndex(i)

        def add_bootstrap(self):
            text = self.sync_now()
            parts = parse_page(text, self.path, self.site_root)
            if not add_head_link(parts, BOOTSTRAP_CSS):
                QMessageBox.information(self, "Design View", "This page has no <head> (it is a fragment / include), "
                                        "so Bootstrap must be linked in the page that includes it.")
                return
            new = restore(parts.prefix + parts.body + parts.suffix, parts.blocks)
            if self._dirty_side == "design":
                # keep the canvas (and its undo history); only the head changed
                self._parts.prefix = parts.prefix
                self._parts.links = parts.links
                self._parts.style_span = parts.style_span
                self._js(f"radSetStyles({json.dumps(canvas_styles(self._parts, self.path, self.site_root))}, "
                         f"{json.dumps(self._parts.extra_css)});")
                self._pull_design()
            else:
                self._text = new
                self._load_design(new)
                if self._mode in ("code", "split"):
                    self._set_code_text(new)
                self._set_modified(new != self._saved_text)
            self._update_css_label()

        def _edit_raw(self, cid: str, rid: str, code):
            if code is None:
                code = self._parts.blocks.get(int(rid), "") if rid.isdigit() else ""
            dlg = CodeBlockDialog(code, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            new = dlg.edit.toPlainText()
            if new != code:
                self._js(f"radSetRaw({json.dumps(cid)}, {json.dumps(new)}, {json.dumps(make_label(new))});")

        # ------------------------------------------------------------ modified / save
        def isModified(self) -> bool:  # noqa: N802 - Qt-style API like the editors
            return self._modified

        is_modified = isModified

        def _set_modified(self, v: bool):
            if v != self._modified:
                self._modified = v
                self.modifiedChanged.emit(v)

        def tab_title(self) -> str:
            return f"{self.path.name} [Design]" + ("*" if self._modified else "")

        def save(self) -> bool:
            text = self.sync_now()
            comp = self._last_composed if (self._last_composed is not None and self._last_composed.text == text) else None
            try:
                write_text_file(self.path, text, self._file_info)
                if comp is not None:
                    for p, t in comp.files.items():
                        info = read_text_file(p)[1] if p.exists() else {"encoding": "utf-8"}
                        write_text_file(p, t, info)
            except OSError as e:
                QMessageBox.warning(self, "Design View", f"Could not save {self.path.name}:\n{e}")
                return False
            self._saved_text = text
            self._set_modified(False)
            if hasattr(self.code, "setModified"):
                self.code.setModified(False)
            self._sync_other_editors(text)
            self.saved.emit(str(self.path))
            server = getattr(self.win, "web_server", None)          # live reload of the Preview (web-core)
            if server is not None and hasattr(server, "check_now"):
                QTimer.singleShot(0, server.check_now)
            return True

        def _sync_other_editors(self, text: str):
            """Other open tabs showing the same file (not modified) get the new text."""
            tabs = getattr(self.win, "tabs", None)
            if tabs is None:
                return
            for i in range(tabs.count()):
                w = tabs.widget(i)
                if w is self:
                    continue
                ed = getattr(w, "editor", None)
                p = getattr(ed, "path", None) or getattr(w, "path", None)
                try:
                    same = p is not None and Path(p).resolve() == self.path
                except OSError:
                    same = False
                if same and ed is not None and hasattr(ed, "setText") and not ed.isModified():
                    ed.setText(text)
                    ed.setModified(False)

        def reload_from_disk(self):
            self._saved_text, self._file_info = read_text_file(self.path)
            self._text = self._saved_text
            self._dirty_side = None
            self._load_design(self._text)
            self._set_code_text(self._text)
            self._set_modified(False)

        def maybe_close(self) -> bool:
            """Called before the tab closes: ask to save changes (then the closed view is freed)."""
            if self._modified:
                r = QMessageBox.question(self, "Design View", f"Save changes to {self.path.name}?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                         QMessageBox.StandardButton.Cancel)
                if r == QMessageBox.StandardButton.Cancel:
                    return False
                if r == QMessageBox.StandardButton.Save and not self.save():
                    return False
            tabs = getattr(self.win, "tabs", None)

            def free():
                if tabs is None or tabs.indexOf(self) < 0:
                    self.deleteLater()
            QTimer.singleShot(0, free)
            return True

        # ------------------------------------------------------------ test / automation helpers
        def export_state(self) -> dict | None:
            v = self._eval_sync("radExport()")
            return json.loads(v) if isinstance(v, str) else None

        def run_js(self, code: str, timeout: int = 5000):
            return self._eval_sync(code, timeout)


# ====================================================================== IDE integration
def design_views(win) -> list:
    tabs = getattr(win, "tabs", None)
    if tabs is None or not _HAVE_QT:
        return []
    return [tabs.widget(i) for i in range(tabs.count()) if isinstance(tabs.widget(i), DesignView)]


def open_design_view(win, path, mode: str = "design"):
    """Open (or focus) the Design View tab of a web page."""
    path = Path(path).resolve()
    for dv in design_views(win):
        if dv.path == path:
            win.tabs.setCurrentWidget(dv)
            if mode and mode != dv.mode():
                dv.set_mode(mode)
            return dv
    # an open, modified code tab of the same file: save it first so both views agree
    tabs = win.tabs
    for i in range(tabs.count()):
        w = tabs.widget(i)
        ed = getattr(w, "editor", None)
        p = getattr(ed, "path", None)
        try:
            if p is not None and Path(p).resolve() == path and ed.isModified():
                path.write_text(ed.text(), encoding="utf-8")
                ed.setModified(False)
        except (OSError, AttributeError):
            pass
    dv = DesignView(win, path, mode=mode)

    def retitle(_m=None):
        i = win.tabs.indexOf(dv)
        if i >= 0:
            win.tabs.setTabText(i, dv.tab_title())
    dv.modifiedChanged.connect(retitle)
    dv.selectionChanged.connect(lambda d: win.statusBar().showMessage(d, 4000) if d else None)
    dv.saved.connect(lambda p: win.statusBar().showMessage(f"Saved {Path(p).name}", 3000))
    if hasattr(win, "_show_tab"):
        win._show_tab(dv, dv.tab_title())
    else:
        win.tabs.setCurrentIndex(win.tabs.addTab(dv, dv.tab_title()))
    win.tabs.setTabToolTip(win.tabs.indexOf(dv), str(path))
    return dv


def save_design_views(win) -> int:
    n = 0
    for dv in design_views(win):
        if dv.isModified() and dv.save():
            n += 1
    return n
