"""Site reports (WebMatrix "Reports" workspace): an SEO / site-health crawler over a running site,
an HTML export of the results, and Lighthouse via npx when Node is installed.

No Qt here: `crawl(url, ...)` returns a `Report`; the dock lives in radide/features/web_tools.py.
`LocalSiteServer` serves a folder with `php -S` (or Python's http.server for static sites) when
the IDE's dev server (radide/web_site/server.py) is not running.
"""
from __future__ import annotations

import atexit
import hashlib
import html
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlparse, unquote

SEVERITIES = ("error", "warning", "info")
USER_AGENT = "RADIDE-SiteReport/1.0"
LIMITS = {"title_min": 10, "title_max": 60, "desc_min": 50, "desc_max": 160,
          "page_kb": 300, "slow_ms": 1000, "very_slow_ms": 3000, "max_pages": 200}
PHP_ERROR = re.compile(r"<b>(Fatal error|Parse error|Warning|Notice|Deprecated)</b>:|"
                       r"^(PHP )?(Fatal error|Parse error|Warning|Notice|Deprecated): .+ on line \d+", re.M)


# ====================================================================== data
@dataclass
class Issue:
    severity: str          # error | warning | info
    rule: str              # short rule id, e.g. "missing-title"
    url: str               # the page the issue is on
    message: str
    detail: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Page:
    url: str
    status: int = 0
    ms: int = 0
    size: int = 0
    content_type: str = ""
    title: str = ""
    description: str = ""
    h1: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    error: str = ""
    redirected_to: str = ""
    referrers: list[str] = field(default_factory=list)
    same_as: str = ""          # another URL that returned exactly the same HTML ("/" and "/index.php")


@dataclass
class Report:
    start_url: str
    pages: dict[str, Page] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    started: float = 0.0
    seconds: float = 0.0
    cancelled: bool = False

    def counts(self) -> dict[str, int]:
        c = {s: 0 for s in SEVERITIES}
        for i in self.issues:
            c[i.severity] = c.get(i.severity, 0) + 1
        return c

    def html_pages(self) -> list[Page]:
        return [p for p in self.pages.values() if "html" in p.content_type and not p.same_as]

    def summary(self) -> str:
        c = self.counts()
        return (f"{len(self.html_pages())} page(s), {len(self.pages)} URL(s) checked in {self.seconds:.1f} s: "
                f"{c['error']} error(s), {c['warning']} warning(s), {c['info']} info")


# ====================================================================== HTML parsing
class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self._in_h1 = 0
        self._h1_text: list[str] = []
        self.h1: list[str] = []
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.resources: list[str] = []
        self.imgs_without_alt: list[str] = []
        self.imgs_empty_alt = 0
        self.html_lang = None
        self.canonical = None
        self.base = None
        self.headings: list[int] = []
        self.forms_no_label = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
            if self.title is None:
                self.title = ""
        elif tag == "h1":
            self._in_h1 += 1
            self._h1_text = []
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
            if "charset" in a:
                self.meta["charset"] = a["charset"]
        elif tag == "a" and a.get("href") is not None:
            self.links.append(a["href"])
        elif tag == "img":
            src = a.get("src", "")
            if src:
                self.resources.append(src)
            if "alt" not in a:
                self.imgs_without_alt.append(src or "(no src)")
            elif not a["alt"].strip():
                self.imgs_empty_alt += 1
        elif tag == "script" and a.get("src"):
            self.resources.append(a["src"])
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = a.get("href")
            elif a.get("href") and ("stylesheet" in rel or "icon" in rel):
                self.resources.append(a["href"])
        elif tag == "base" and a.get("href"):
            self.base = a["href"]
        if len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            self._in_h1 -= 1
            self.h1.append(" ".join("".join(self._h1_text).split()))

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h1:
            self._h1_text.append(data)


# ====================================================================== fetching
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def fetch(url: str, timeout: float = 15, method: str = "GET", max_bytes: int = 5_000_000):
    """-> (status, headers dict(lowercase), body bytes, ms, error text)."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    t0 = time.perf_counter()
    try:
        with _opener.open(req, timeout=timeout) as r:
            body = r.read(max_bytes) if method != "HEAD" else b""
            return r.status, {k.lower(): v for k, v in r.headers.items()}, body, \
                int((time.perf_counter() - t0) * 1000), ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read(max_bytes)
        except Exception:  # noqa: BLE001
            body = b""
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, body, \
            int((time.perf_counter() - t0) * 1000), ""
    except Exception as e:  # noqa: BLE001 - connection refused, timeout, bad URL ...
        return 0, {}, b"", int((time.perf_counter() - t0) * 1000), str(getattr(e, "reason", e))


def _decode(body: bytes, ctype: str) -> str:
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
    for enc in ((m.group(1),) if m else ()) + ("utf-8", "cp1252"):
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


def _norm(url: str) -> str:
    url = urldefrag(url)[0]
    p = urlparse(url)
    path = p.path or "/"
    return p._replace(path=path, fragment="").geturl()


# ====================================================================== crawler
def crawl(start_url: str, max_pages: int | None = None, check_external: bool = False,
          progress: Callable[[int, str], None] | None = None, cancelled: Callable[[], bool] | None = None,
          timeout: float = 15, limits: dict | None = None) -> Report:
    """Crawls every same-site page reachable from start_url and checks links, images, scripts and
    stylesheets. Returns a Report with issues sorted by severity."""
    lim = dict(LIMITS, **(limits or {}))
    max_pages = max_pages or lim["max_pages"]
    start_url = _norm(start_url)
    origin = urlparse(start_url).netloc
    rep = Report(start_url, started=time.time())
    queue: list[str] = [start_url]
    queued = {start_url}
    referrers: dict[str, list[str]] = defaultdict(list)
    resources: dict[str, list[str]] = defaultdict(list)    # resource URL -> pages using it
    external: dict[str, list[str]] = defaultdict(list)
    parsed: dict[str, _PageParser] = {}
    by_body: dict[str, str] = {}
    add = rep.issues.append

    while queue and len(rep.html_pages()) < max_pages:
        if cancelled and cancelled():
            rep.cancelled = True
            break
        url = queue.pop(0)
        if progress:
            progress(len(rep.pages), url)
        status, headers, body, ms, err = fetch(url, timeout)
        page = Page(url, status, ms, len(body), headers.get("content-type", ""), error=err)
        rep.pages[url] = page
        if err:
            add(Issue("error", "unreachable", url, "The page could not be loaded", err))
            continue
        if 300 <= status < 400:
            loc = urljoin(url, headers.get("location", ""))
            page.redirected_to = loc
            if urlparse(loc).netloc == origin:
                n = _norm(loc)
                referrers[n].append(url)
                if n not in queued:
                    queued.add(n)
                    queue.append(n)
            continue
        if status >= 400:
            continue                         # reported as broken link below (with referrers)
        if "html" not in page.content_type:
            continue
        digest = hashlib.sha1(body).hexdigest()
        if digest in by_body:
            # the same document under another address: check it once, note the duplicate
            page.same_as = by_body[digest]
            if "canonical" not in _decode(body, page.content_type).lower():
                add(Issue("info", "duplicate-content", url, f"Same content as {page.same_as}",
                          "Link to one address only, or add <link rel=\"canonical\">."))
            continue
        by_body[digest] = url
        text = _decode(body, page.content_type)
        pp = _PageParser()
        try:
            pp.feed(text)
            pp.close()
        except Exception as e:  # noqa: BLE001
            add(Issue("warning", "html-parse", url, "The HTML could not be parsed completely", str(e)))
        parsed[url] = pp
        page.title = " ".join((pp.title or "").split())
        page.description = " ".join(pp.meta.get("description", "").split())
        page.h1 = pp.h1
        base = urljoin(url, pp.base) if pp.base else url
        m = PHP_ERROR.search(text)
        if m:
            end = text.find("\n", m.start())
            line = text[m.start():end if end >= 0 else None]
            add(Issue("error", "php-error", url, "The page shows a PHP error/warning",
                      re.sub(r"<[^>]+>", "", line)[:300]))
        for href in pp.links:
            href = href.strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            full = _norm(urljoin(base, href))
            pr = urlparse(full)
            if pr.scheme not in ("http", "https"):
                continue
            page.links.append(full)
            if pr.netloc == origin:
                referrers[full].append(url)
                if full not in queued:
                    queued.add(full)
                    queue.append(full)
            else:
                external[full].append(url)
        for src in pp.resources:
            src = src.strip()
            if not src or src.startswith("data:"):
                continue
            full = _norm(urljoin(base, src))
            if urlparse(full).scheme in ("http", "https"):
                page.resources.append(full)
                if urlparse(full).netloc == origin or check_external:
                    resources[full].append(url)
        _page_rules(page, pp, add, lim)

    # pages linked but never fetched (max_pages reached) are not reported
    for url, page in rep.pages.items():
        page.referrers = sorted(set(referrers.get(url, [])))
        if page.status >= 400:
            sev = "error"
            where = ", ".join(page.referrers[:5]) or "(start page)"
            add(Issue(sev, "broken-link" if page.status == 404 else f"http-{page.status}", url,
                      f"HTTP {page.status} - {'page not found' if page.status == 404 else 'server error' if page.status >= 500 else 'request refused'}",
                      f"linked from {where}"))
        elif page.redirected_to:
            add(Issue("info", "redirect", url, f"Redirects ({page.status}) to {page.redirected_to}",
                      f"linked from {', '.join(page.referrers[:5])}" if page.referrers else ""))

    # resources (images, scripts, stylesheets)
    for res_url, pages in resources.items():
        if cancelled and cancelled():
            rep.cancelled = True
            break
        if res_url in rep.pages:
            st = rep.pages[res_url].status
            err = rep.pages[res_url].error
        else:
            st, _h, body, ms, err = fetch(res_url, timeout)
            rep.pages[res_url] = Page(res_url, st, ms, len(body), _h.get("content-type", ""), error=err)
            if not err and st < 400 and len(body) > 1024 * 1024 and "image" in _h.get("content-type", ""):
                add(Issue("warning", "large-image", res_url, f"Large image ({len(body) // 1024} KB)",
                          f"used on {', '.join(sorted(set(pages))[:3])}"))
        if err or st >= 400:
            for p in sorted(set(pages)):
                add(Issue("error", "broken-resource", p,
                          f"Missing resource ({'HTTP ' + str(st) if st else err}): {res_url}", ""))
    if check_external:
        for ext_url, pages in external.items():
            if cancelled and cancelled():
                break
            st, _h, _b, _ms, err = fetch(ext_url, timeout, method="HEAD")
            if st in (405, 501):
                st, _h, _b, _ms, err = fetch(ext_url, timeout, max_bytes=1024)
            if err or st >= 400:
                for p in sorted(set(pages)):
                    add(Issue("warning", "broken-external-link", p,
                              f"External link fails ({'HTTP ' + str(st) if st else err}): {ext_url}"))

    # site-wide rules: duplicates
    by_title: dict[str, list[str]] = defaultdict(list)
    by_desc: dict[str, list[str]] = defaultdict(list)
    for p in rep.html_pages():
        if p.status == 200:
            if p.title:
                by_title[p.title.lower()].append(p.url)
            if p.description:
                by_desc[p.description.lower()].append(p.url)
    for urls in by_title.values():
        if len(urls) > 1:
            for u in urls:
                add(Issue("warning", "duplicate-title", u, f"Title is shared by {len(urls)} pages",
                          f"\"{rep.pages[u].title}\" - also on {', '.join(x for x in urls if x != u)[:300]}"))
    for urls in by_desc.values():
        if len(urls) > 1:
            for u in urls:
                add(Issue("warning", "duplicate-description", u,
                          f"Meta description is shared by {len(urls)} pages",
                          f"also on {', '.join(x for x in urls if x != u)[:300]}"))
    if queue and len(rep.html_pages()) >= max_pages:
        add(Issue("info", "crawl-limit", start_url, f"Stopped after {max_pages} pages",
                  f"{len(queue)} more URL(s) were not checked"))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    rep.issues.sort(key=lambda i: (order.get(i.severity, 9), i.rule, i.url))
    rep.seconds = time.time() - rep.started
    return rep


def _page_rules(page: Page, pp: _PageParser, add, lim: dict) -> None:
    url = page.url
    if pp.title is None or not page.title:
        add(Issue("error", "missing-title", url, "The page has no <title>",
                  "Search engines show the title as the link text in results."))
    elif len(page.title) > lim["title_max"]:
        add(Issue("warning", "long-title", url, f"Title is too long ({len(page.title)} characters)",
                  f"Keep it under {lim['title_max']}: \"{page.title}\""))
    elif len(page.title) < lim["title_min"]:
        add(Issue("warning", "short-title", url, f"Title is very short ({len(page.title)} characters)",
                  f"\"{page.title}\""))
    robots = pp.meta.get("robots", "").lower()
    if "noindex" in robots:
        add(Issue("info", "noindex", url, "The page asks search engines not to index it (robots noindex)"))
    if not page.description:
        add(Issue("warning", "missing-description", url, "No <meta name=\"description\">",
                  "Search engines show the description under the title."))
    elif len(page.description) > lim["desc_max"]:
        add(Issue("warning", "long-description", url,
                  f"Meta description is too long ({len(page.description)} characters)",
                  f"Keep it under {lim['desc_max']}."))
    elif len(page.description) < lim["desc_min"]:
        add(Issue("info", "short-description", url,
                  f"Meta description is short ({len(page.description)} characters)"))
    if not pp.h1:
        add(Issue("warning", "missing-h1", url, "The page has no <h1> heading"))
    elif len(pp.h1) > 1:
        add(Issue("warning", "multiple-h1", url, f"The page has {len(pp.h1)} <h1> headings",
                  "; ".join(h[:60] for h in pp.h1)))
    elif not pp.h1[0]:
        add(Issue("warning", "empty-h1", url, "The <h1> heading is empty"))
    prev = 0
    for lvl in pp.headings:
        if prev and lvl > prev + 1:
            add(Issue("info", "heading-skip", url, f"Heading level skipped (h{prev} -> h{lvl})"))
            break
        prev = lvl
    if pp.imgs_without_alt:
        add(Issue("warning", "img-alt", url, f"{len(pp.imgs_without_alt)} image(s) without an alt attribute",
                  ", ".join(pp.imgs_without_alt[:8])))
    if not pp.html_lang:
        add(Issue("info", "missing-lang", url, "<html> has no lang attribute"))
    if "viewport" not in pp.meta:
        add(Issue("warning", "missing-viewport", url, "No <meta name=\"viewport\"> - the page will not adapt to phones"))
    if "charset" not in pp.meta and "content-type" not in pp.meta and "charset" not in page.content_type.lower():
        add(Issue("info", "missing-charset", url, "No character set declared"))
    kb = page.size / 1024
    if kb > lim["page_kb"]:
        add(Issue("warning", "page-size", url, f"Large page ({kb:.0f} KB of HTML)",
                  f"Pages over {lim['page_kb']} KB load slowly on phones."))
    if page.ms > lim["very_slow_ms"]:
        add(Issue("error", "slow-page", url, f"Very slow response ({page.ms} ms)"))
    elif page.ms > lim["slow_ms"]:
        add(Issue("warning", "slow-page", url, f"Slow response ({page.ms} ms)"))


# ====================================================================== export
def report_html(rep: Report) -> str:
    """A self-contained HTML report (WebMatrix-like): summary, issues grouped by rule, pages table."""
    e = html.escape
    c = rep.counts()
    by_rule: dict[tuple[str, str], list[Issue]] = defaultdict(list)
    for i in rep.issues:
        by_rule[(i.severity, i.rule)].append(i)
    rows = []
    for (sev, rule), items in by_rule.items():
        rows.append(f'<tr class="grp"><td colspan="3"><span class="sev {sev}">{sev}</span> '
                    f'<b>{e(rule)}</b> &middot; {len(items)}</td></tr>')
        for i in items:
            rows.append(f'<tr class="{sev}"><td><a href="{e(i.url)}">{e(_short(i.url, rep.start_url))}</a></td>'
                        f'<td>{e(i.message)}</td><td class="d">{e(i.detail)}</td></tr>')
    prow = []
    for p in sorted(rep.pages.values(), key=lambda p: p.url):
        cls = "bad" if (p.error or p.status >= 400) else ""
        prow.append(f'<tr class="{cls}"><td><a href="{e(p.url)}">{e(_short(p.url, rep.start_url))}</a></td>'
                    f'<td>{p.status or e(p.error)}</td><td>{e(p.content_type.split(";")[0])}</td>'
                    f'<td class="n">{p.size / 1024:.1f}</td><td class="n">{p.ms}</td><td>{e(p.title)}</td></tr>')
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(rep.started or time.time()))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Site report - {e(rep.start_url)}</title>
<style>
:root{{--bg:#fff;--fg:#1d2330;--mut:#5b6475;--line:#e3e6ec;--err:#c62828;--warn:#b26a00;--info:#1565c0;--grp:#f4f6f9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181d;--fg:#e6e8ee;--mut:#9aa3b5;--line:#2c313b;--err:#ef6b6b;--warn:#f0b24a;--info:#6ea8ff;--grp:#1f232b}}}}
body{{font:14px/1.45 "Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:24px 16px;max-width:1200px;margin:auto}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:17px;margin:28px 0 8px}} .mut{{color:var(--mut)}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}} .card{{border:1px solid var(--line);border-radius:8px;padding:10px 16px;min-width:110px}}
.card b{{display:block;font-size:24px}} .card.error b{{color:var(--err)}} .card.warning b{{color:var(--warn)}} .card.info b{{color:var(--info)}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}}
th{{color:var(--mut);font-weight:600}} tr.grp td{{background:var(--grp)}} td.d{{color:var(--mut)}} td.n{{text-align:right;font-variant-numeric:tabular-nums}}
.sev{{font-size:11px;text-transform:uppercase;font-weight:700;padding:1px 6px;border-radius:4px;border:1px solid}}
.sev.error{{color:var(--err)}} .sev.warning{{color:var(--warn)}} .sev.info{{color:var(--info)}} tr.bad td{{color:var(--err)}}
a{{color:var(--info)}} .wrap{{overflow-x:auto}}
</style></head><body>
<h1>Site report</h1>
<div class="mut">{e(rep.start_url)} &middot; {when} &middot; {rep.seconds:.1f} s{' &middot; cancelled' if rep.cancelled else ''}</div>
<div class="cards"><div class="card"><b>{len(rep.html_pages())}</b>pages</div>
<div class="card error"><b>{c['error']}</b>errors</div><div class="card warning"><b>{c['warning']}</b>warnings</div>
<div class="card info"><b>{c['info']}</b>info</div></div>
<h2>Issues</h2><div class="wrap"><table><tr><th>Page</th><th>Issue</th><th>Details</th></tr>
{''.join(rows) or '<tr><td colspan="3">No issues found.</td></tr>'}</table></div>
<h2>URLs checked</h2><div class="wrap"><table><tr><th>URL</th><th>Status</th><th>Type</th><th>KB</th><th>ms</th><th>Title</th></tr>
{''.join(prow)}</table></div>
<p class="mut">Generated by RAD IDE.</p></body></html>
"""


def _short(url: str, start: str) -> str:
    a, b = urlparse(url), urlparse(start)
    if a.netloc == b.netloc:
        return (a.path or "/") + (f"?{a.query}" if a.query else "")
    return url


def file_for_url(url: str, root: Path) -> Path | None:
    """The source file in the site folder that serves url (best effort: /, /x.php, /dir/ -> index.*)."""
    root = Path(root)
    path = unquote(urlparse(url).path or "/").lstrip("/")
    cand = root / path
    names = ("index.php", "index.html", "index.htm", "default.php", "default.html")
    try:
        if path == "" or cand.is_dir():
            for n in names:
                if (cand / n).is_file():
                    return cand / n
            return None
        if cand.is_file():
            return cand
        for ext in (".php", ".html", ".htm"):
            if cand.with_suffix(ext).is_file():
                return cand.with_suffix(ext)
        if (root / "index.php").is_file():       # front controller (/products/1 -> index.php)
            return root / "index.php"
    except OSError:
        return None
    return None


# ====================================================================== Lighthouse
def npx_path() -> str | None:
    return shutil.which("npx.cmd") or shutil.which("npx")


def chromium_for_lighthouse() -> str | None:
    """Lighthouse needs Chrome; Edge (Chromium) works as well via CHROME_PATH."""
    try:
        from .superpreview import detect_browsers
        b = detect_browsers()
    except Exception:  # noqa: BLE001
        b = {}
    return b.get("Chrome") or b.get("Edge") or b.get("Brave")


def lighthouse_command(url: str, out_html: Path, categories: str = "") -> tuple[list[str], dict] | None:
    """argv + env for running Lighthouse through npx, or None when npx is not installed."""
    npx = npx_path()
    if not npx:
        return None
    argv = [npx, "--yes", "lighthouse@12", url, "--output=html", f"--output-path={out_html}", "--quiet",
            "--chrome-flags=--headless=new --no-first-run --disable-gpu"]
    if categories:
        argv.append(f"--only-categories={categories}")
    env = dict(os.environ)
    chrome = chromium_for_lighthouse()
    if chrome:
        env["CHROME_PATH"] = chrome
    return argv, env


def run_lighthouse(url: str, out_html: Path, timeout: int = 600, log: Callable[[str], None] = print,
                   categories: str = "") -> bool:
    """Blocking helper (use it from a worker thread). True when the HTML report was written."""
    cmd = lighthouse_command(url, out_html, categories)
    if cmd is None:
        log("Lighthouse needs Node.js (npx was not found on PATH).")
        return False
    argv, env = cmd
    log("Running: " + " ".join(argv[1:]))
    try:
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        log("Lighthouse timed out.")
        return False
    except OSError as e:
        log(f"Cannot start Lighthouse: {e}")
        return False
    tail = (r.stderr or r.stdout or "").strip().splitlines()[-6:]
    if r.returncode != 0 or not Path(out_html).is_file():
        log("Lighthouse failed:\n" + "\n".join(tail))
        return False
    return True


# ====================================================================== fallback server
def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def find_php() -> str | None:
    for cand in (os.environ.get("RADIDE_PHP"), shutil.which("php"), r"C:\tools\php81\php.exe",
                 r"C:\php\php.exe", r"C:\xampp\php\php.exe"):
        if cand and Path(cand).is_file():
            return cand
    return None


class LocalSiteServer:
    """Serves a folder on 127.0.0.1 (php -S when the site has .php files and PHP is installed,
    otherwise python -m http.server). Used when the IDE's DevServer is not running."""

    def __init__(self, root: Path, php: str | None = None):
        self.root = Path(root).resolve()
        self.php = php
        self.proc: subprocess.Popen | None = None
        self.url = ""
        self.kind = ""

    def start(self, timeout: float = 10) -> str:
        port = free_port()
        has_php = any(self.root.rglob("*.php"))
        php = self.php or (find_php() if has_php else None)
        if has_php and php:
            # show PHP errors in the page, like a development server should
            argv = [php, "-d", "display_errors=On", "-d", "error_reporting=E_ALL", "-S", f"127.0.0.1:{port}",
                    "-t", str(self.root)]
            self.kind = "php"
        else:
            argv = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory",
                    str(self.root)]
            self.kind = "static"
        self.proc = subprocess.Popen(argv, cwd=str(self.root), stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"The {self.kind} server exited (code {self.proc.returncode}).")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            self.stop()
            raise RuntimeError("The local server did not start.")
        self.url = f"http://127.0.0.1:{port}/"
        atexit.register(self.stop)
        return self.url

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

