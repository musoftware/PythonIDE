"""AI Web Chats - CONTRACTS 9.6.

The free web chats (ChatGPT, Gemini, Claude, DeepSeek, Copilot, Perplexity, Grok, Qwen, Le Chat or any URL)
inside the IDE: a dock "AI Web Chats" (View > AI Web Chats, also the globe of the VS Code / Agent activity bar)
with a site switcher.  The user signs in normally on the real site; the login is kept in ONE persistent
QWebEngineProfile stored in %LOCALAPPDATA%\\RADIDE\\webchat (cookies, local storage, permissions).

  * Send context  - the question box + the checked context (selection / current file, Error List, form, git
                    changes, terminal, @mentions) is written into the page's prompt box with JavaScript
                    (textarea or contenteditable editors such as ProseMirror / Quill); "Submit automatically"
                    also presses the site's Send button.  Fallback: the text goes to the clipboard and the page
                    gets the focus, so Ctrl+V pastes it.
  * Grab code     - reads the last (or any) <pre><code> block of the page -> Copy / Insert at cursor /
                    Replace selection / Apply to file (diff preview with Accept / Reject) / New file.
  * Providers     - every site is also an `radide.ai` provider of kind "web" (id "web-<site>"): chat() types the
                    prompt into the page, submits it and streams the answer until it stops changing (best effort,
                    it reads the page like a user would; nothing unofficial is called).

Only the official web pages are used - no reverse-engineered endpoints.  Public helpers:
`panel(win)`, `send_to_web(win, text, site=None, submit=False)`, `profile()`, `profile_dir()`.
"""
from __future__ import annotations

import difflib
import html
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QGuiApplication, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QStackedWidget, QTextBrowser,
                             QToolButton, QVBoxLayout, QWidget)

from .. import theme

APP_TITLE = "AI Web Chats"
PROFILE_NAME = "webchat"


# ============================================================================ sites
@dataclass
class Site:
    id: str
    name: str
    url: str
    inputs: tuple = ()          # CSS selectors of the prompt box (first visible wins; generic fallback after)
    send: tuple = ()            # the Send button
    answers: tuple = ()         # every assistant answer (the last one is read)
    stop: tuple = ()            # visible while the answer is being generated
    custom: bool = False
    auth_hosts: tuple = field(default_factory=tuple)


# generic selectors tried after the site's own ones (and for custom sites)
GENERIC_SEND = ('button[data-testid="send-button"]', 'button[aria-label="Send message"]',
                'button[aria-label="Send prompt"]', 'button[aria-label^="Send"]', 'button[aria-label*="send" i]',
                'button[type="submit"]', 'button[title^="Send"]', '[data-testid*="send" i]')
GENERIC_ANSWERS = ('[data-message-author-role="assistant"]', 'model-response message-content', '.ds-markdown',
                   '[data-content="ai-message"]', '.font-claude-response', '.font-claude-message',
                   '.response-message-content', '.markdown-content', '.prose', '.markdown')
GENERIC_STOP = ('button[data-testid="stop-button"]', 'button[aria-label^="Stop"]', 'button[aria-label*="stop" i]')

SITES: list[Site] = [
    Site("chatgpt", "ChatGPT", "https://chatgpt.com/",
         inputs=("#prompt-textarea", 'div.ProseMirror[contenteditable="true"]', 'textarea[name="prompt-textarea"]'),
         send=('button[data-testid="send-button"]', "#composer-submit-button"),
         answers=('[data-message-author-role="assistant"]',),
         stop=('button[data-testid="stop-button"]',)),
    Site("gemini", "Gemini", "https://gemini.google.com/app",
         inputs=("rich-textarea .ql-editor", 'div.ql-editor[contenteditable="true"]'),
         send=("button.send-button", 'button[aria-label="Send message"]'),
         answers=("model-response message-content", "message-content .markdown", "model-response"),
         stop=('button[aria-label="Stop response"]', "button.send-button.stop")),
    Site("claude", "Claude", "https://claude.ai/new",
         inputs=('div.ProseMirror[contenteditable="true"]', '[data-testid="chat-input"]'),
         send=('button[aria-label="Send message"]', 'button[aria-label="Send Message"]'),
         answers=(".font-claude-response", ".font-claude-message", '[data-is-streaming] .font-claude-message'),
         stop=('button[aria-label="Stop response"]',)),
    Site("deepseek", "DeepSeek", "https://chat.deepseek.com/",
         inputs=("textarea#chat-input", "textarea"),
         send=('div[role="button"][aria-disabled="false"]:has(svg)',),
         answers=(".ds-markdown",), stop=()),
    Site("copilot", "Copilot", "https://copilot.microsoft.com/",
         inputs=("textarea#userInput", "textarea"),
         send=('button[aria-label="Submit message"]', 'button[title="Submit message"]'),
         answers=('[data-content="ai-message"]', '[data-testid="ai-message"]'),
         stop=('button[aria-label="Stop responding"]',)),
    Site("perplexity", "Perplexity", "https://www.perplexity.ai/",
         inputs=("#ask-input", 'div[contenteditable="true"]', "textarea"),
         send=('button[aria-label="Submit"]', 'button[data-testid="submit-button"]'),
         answers=(".prose",), stop=('button[aria-label="Stop"]',)),
    Site("grok", "Grok", "https://grok.com/",
         inputs=('div.ProseMirror[contenteditable="true"]', "textarea"),
         send=('button[type="submit"]', 'button[aria-label="Submit"]'),
         answers=(".message-bubble .response-content-markdown", ".response-content-markdown"),
         stop=('button[aria-label="Stop model response"]',)),
    Site("qwen", "Qwen", "https://chat.qwen.ai/",
         inputs=("textarea#chat-input", "textarea"),
         send=("button#send-message-button", "#send-message-button"),
         answers=(".response-message-content", ".markdown-content"), stop=()),
    Site("lechat", "Mistral Le Chat", "https://chat.mistral.ai/chat",
         inputs=('div.ProseMirror[contenteditable="true"]', "textarea"),
         send=('button[aria-label="Send question"]', 'button[type="submit"]'),
         answers=('[data-message-author-role="assistant"]', ".markdown-container-style"), stop=()),
]

# hosts that may stay in an in-IDE popup window (sign-in flows); other popups open in the external browser
AUTH_HOSTS = ("accounts.google.com", "login.microsoftonline.com", "login.live.com", "login.microsoft.com",
              "appleid.apple.com", "github.com", "auth.openai.com", "auth0.openai.com", "x.com", "twitter.com",
              "api.x.com", "challenges.cloudflare.com", "chat.qwen.ai", "chatgpt.com", "claude.ai")


def settings():
    from .. import ai
    return ai.settings()


def custom_sites() -> list[Site]:
    raw = settings().value("ai/web/custom", "") or ""
    try:
        items = json.loads(raw) if isinstance(raw, str) and raw else []
    except ValueError:
        items = []
    out = []
    for i, it in enumerate(items):
        if isinstance(it, dict) and it.get("url"):
            sid = str(it.get("id") or f"custom{i + 1}")
            out.append(Site(sid, str(it.get("name") or it["url"]), str(it["url"]), custom=True))
    return out


def save_custom_sites(sites: list[Site]) -> None:
    s = settings()
    s.setValue("ai/web/custom", json.dumps([{"id": x.id, "name": x.name, "url": x.url} for x in sites
                                            if x.custom]))
    s.sync()


def all_sites() -> list[Site]:
    return SITES + custom_sites()


def find_site(site_id: str) -> Site | None:
    return next((s for s in all_sites() if s.id == site_id), None)


def normalize_url(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", t):
        t = ("http://" if re.match(r"^(localhost|127\.|\[::1\])", t) else "https://") + t
    return t


# ============================================================================ profile
def profile_dir() -> Path:
    """%LOCALAPPDATA%\\RADIDE\\webchat (RADIDE_WEBCHAT_DIR overrides it - tests)."""
    env = os.environ.get("RADIDE_WEBCHAT_DIR")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "RADIDE" / PROFILE_NAME


_profile = None


def clean_user_agent(ua: str) -> str:
    """The Chrome user agent without the QtWebEngine token (some sign-in pages refuse unknown browsers)."""
    return re.sub(r"\s*QtWebEngine/[\d.]+", "", ua or "").strip()


def profile():
    """The one persistent profile shared by every web chat page (created on first use)."""
    global _profile
    if _profile is not None:
        return _profile
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    root = profile_dir()
    root.mkdir(parents=True, exist_ok=True)
    app = QCoreApplication.instance()
    try:
        from PyQt6.QtWebEngineCore import QWebEngineProfileBuilder
        b = QWebEngineProfileBuilder()
        b.setPersistentStoragePath(str(root / "storage"))
        b.setCachePath(str(root / "cache"))
        b.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        try:
            b.setPersistentPermissionsPolicy(QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk)
        except AttributeError:
            pass
        p = b.createProfile(PROFILE_NAME, app)
    except (ImportError, TypeError):      # Qt < 6.9, or PyQt6 builds where the builder cannot be created
        p = QWebEngineProfile(PROFILE_NAME, app)
        p.setPersistentStoragePath(str(root / "storage"))
        p.setCachePath(str(root / "cache"))
        p.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    if str(settings().value("ai/web/clean_ua", "true")).lower() not in ("0", "false", "no"):
        p.setHttpUserAgent(clean_user_agent(p.httpUserAgent()))
    try:
        p.setDownloadPath(str(Path.home() / "Downloads"))
    except Exception:  # noqa: BLE001
        pass
    st = p.settings()
    A = QWebEngineSettings.WebAttribute
    for attr in (A.JavascriptCanAccessClipboard, A.JavascriptCanPaste, A.LocalStorageEnabled,
                 A.JavascriptCanOpenWindows, A.FullScreenSupportEnabled):
        try:
            st.setAttribute(attr, True)
        except Exception:  # noqa: BLE001
            pass
    p.downloadRequested.connect(_on_download)
    _profile = p
    return p


def _on_download(item) -> None:
    try:
        name = item.downloadFileName() or "download"
        folder = item.downloadDirectory() or str(Path.home() / "Downloads")
        path, _ = QFileDialog.getSaveFileName(None, "Save download", str(Path(folder) / name))
        if not path:
            item.cancel()
            return
        item.setDownloadDirectory(str(Path(path).parent))
        item.setDownloadFileName(Path(path).name)
        item.accept()
    except Exception:  # noqa: BLE001
        pass


def release_profile() -> None:
    """Delete every page, then the profile, so Chromium writes the cookies to disk."""
    global _profile
    p = _profile
    if p is None:
        return
    for pn in list(_PANELS):
        pn.shutdown()
    _profile = None
    try:
        from PyQt6 import sip
        if not sip.isdeleted(p):
            sip.delete(p)
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ page JavaScript
JS_LIB = r"""
(function(){
if (window.__radWeb && window.__radWeb.v === 4) return;
const vis = el => {
  if (!el || !el.getClientRects || !el.getClientRects().length) return false;
  const r = el.getBoundingClientRect();
  // a hidden view (dock not shown yet) has no viewport: then only the CSS decides
  if (window.innerWidth > 60 && (r.width < 2 || r.height < 2)) return false;
  const s = getComputedStyle(el);
  return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
};
const editable = el => !!el && !el.disabled && !el.readOnly && (el.tagName === 'TEXTAREA' ||
  (el.tagName === 'INPUT' && /^(text|search|)$/i.test(el.getAttribute('type') || '')) || el.isContentEditable);
const all = (sels, root) => {
  const out = [];
  for (const s of sels || []) {
    let els; try { els = (root || document).querySelectorAll(s); } catch (e) { continue; }
    for (const el of els) out.push(el);
    if (out.length) break;
  }
  return out;
};
const deep = (sel) => {             // querySelectorAll through open shadow roots
  const out = [], stack = [document];
  while (stack.length) {
    const root = stack.pop();
    try { root.querySelectorAll(sel).forEach(e => out.push(e)); } catch (e) {}
    root.querySelectorAll('*').forEach(e => { if (e.shadowRoot) stack.push(e.shadowRoot); });
  }
  return out;
};
const toEditable = el => {
  if (!el) return null;
  if (editable(el)) return el;
  const inner = el.querySelector('textarea, [contenteditable="true"], [contenteditable=""], [role="textbox"]');
  return editable(inner) ? inner : null;
};
function findInput(sels) {
  for (const el of all(sels)) { const e = toEditable(el); if (e && vis(e)) return e; }
  const a = document.activeElement;
  if (editable(a) && vis(a) && a.tagName !== 'INPUT') return a;
  let best = null, bestScore = -1e9;
  for (const el of deep('textarea, [contenteditable="true"], [contenteditable=""], [role="textbox"], input[type="text"], input:not([type])')) {
    const e = toEditable(el); if (!e || !vis(e)) continue;
    const r = e.getBoundingClientRect();
    const score = r.bottom + Math.min(r.width, 900) / 10 + (e.tagName === 'INPUT' ? -400 : 0);
    if (score > bestScore) { best = e; bestScore = score; }
  }
  return best;
}
const norm = s => (s || '').replace(/\s+/g, ' ').trim();
const valueOf = el => (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') ? el.value : (el.innerText || el.textContent || '');
function setNative(el, v) {
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const d = Object.getOwnPropertyDescriptor(proto, 'value');
  if (d && d.set) d.set.call(el, v); else el.value = v;
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  try { el.setSelectionRange(v.length, v.length); } catch (e) {}
}
function fill(sels, text, append, mode) {
  const el = findInput(sels);
  if (!el) return {ok: false, why: 'no-input'};
  el.focus();
  const tag = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.isContentEditable ? '[contenteditable]' : '');
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    const v = append && el.value.trim() ? el.value.replace(/\s+$/, '') + '\n\n' + text : text;
    setNative(el, v);
    return {ok: true, how: 'value', tag};
  }
  const sel = window.getSelection(), range = document.createRange();
  range.selectNodeContents(el);
  if (append) range.collapse(false);
  sel.removeAllRanges(); sel.addRange(range);
  let how = '';
  if (mode !== 'insert') {
    try {
      const dt = new DataTransfer(); dt.setData('text/plain', text);
      const ev = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
      el.dispatchEvent(ev);
      if (ev.defaultPrevented) how = 'paste';
    } catch (e) {}
  }
  if (!how && mode !== 'text') {
    try { if (document.execCommand('insertText', false, text)) how = 'insertText'; } catch (e) {}
  }
  if (!how) {
    el.textContent = (append ? valueOf(el) + '\n\n' : '') + text;
    el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: text}));
    how = 'textContent';
  }
  return {ok: true, how, tag};
}
function check(sels, sample) {
  const el = findInput(sels);
  if (!el) return {ok: false, len: 0};
  const v = norm(valueOf(el)), s = norm(sample);
  return {ok: !s || v.indexOf(s) >= 0, len: v.length};
}
function submit(sels) {
  for (const b of all(sels)) {
    if (!vis(b) || b.disabled || b.getAttribute('aria-disabled') === 'true') continue;
    b.click(); return {ok: true, how: 'button'};
  }
  return {ok: false, how: 'no-button'};
}
function langOf(pre, code) {
  const cls = ((code && code.className) || '') + ' ' + (pre.className || '');
  let m = cls.match(/(?:language|lang)-([\w#+.\-]+)/);
  if (m) return m[1].toLowerCase();
  const dl = pre.getAttribute('data-language') || (code && code.getAttribute('data-language'));
  if (dl) return dl.toLowerCase();
  let box = pre;
  for (let i = 0; i < 3 && box; i++, box = box.parentElement) {
    const first = norm((box.innerText || '').split('\n')[0]);
    const body = norm(code ? code.innerText : '');
    if (first && first.length <= 20 && /^[A-Za-z][\w#+.\- ]*$/.test(first) && !body.startsWith(first))
      return first.toLowerCase();
  }
  return '';
}
function block(pre) {
  const code = pre.querySelector('code') || pre;
  let text = code.innerText; if (text == null || (!text && code.textContent)) text = code.textContent || '';
  return {lang: langOf(pre, pre.querySelector('code')), code: text.replace(/\n+$/, '')};
}
function codeBlocks() {
  return Array.from(document.querySelectorAll('pre')).filter(p => !(p.parentElement && p.parentElement.closest('pre')))
    .map(block).filter(b => b.code.trim());
}
function md(node) {
  let out = '';
  const kids = n => { for (const c of n.childNodes) walk(c); };
  const walk = n => {
    if (n.nodeType === 3) { out += n.nodeValue; return; }
    if (n.nodeType !== 1) return;
    const t = n.tagName.toUpperCase();
    if (/^(BUTTON|SVG|STYLE|SCRIPT|NOSCRIPT|TEMPLATE|TEXTAREA)$/.test(t)) return;
    if (t === 'PRE') { const b = block(n); const f = b.code.indexOf('```') >= 0 ? '````' : '```';
      out += '\n' + f + b.lang + '\n' + b.code + '\n' + f + '\n'; return; }
    if (t === 'CODE') { out += '`' + n.textContent + '`'; return; }
    if (t === 'BR') { out += '\n'; return; }
    if (/^H[1-6]$/.test(t)) { out += '\n\n' + '#'.repeat(+t[1]) + ' '; kids(n); out += '\n'; return; }
    if (t === 'LI') { const p = n.parentElement;
      out += '\n' + (p && p.tagName === 'OL' ? (Array.prototype.indexOf.call(p.children, n) + 1) + '. ' : '- ');
      kids(n); return; }
    if (t === 'STRONG' || t === 'B') { out += '**'; kids(n); out += '**'; return; }
    if (t === 'EM' || t === 'I') { out += '*'; kids(n); out += '*'; return; }
    if (t === 'TD' || t === 'TH') { kids(n); out += ' | '; return; }
    if (t === 'A') { kids(n); return; }
    const blockish = /^(P|DIV|UL|OL|TABLE|TR|BLOCKQUOTE|SECTION|ARTICLE|HR|HEADER|FOOTER|DL|DT|DD|FIGURE)$/.test(t);
    if (blockish) out += '\n';
    kids(n);
    if (blockish) out += '\n';
  };
  walk(node);
  return out.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}
function answers(sels, stops) {
  const els = all(sels);
  const last = els.length ? els[els.length - 1] : null;
  const busy = all(stops).some(vis);
  return {count: els.length, last: last ? md(last) : '', busy};
}
function tail(marker) {
  const body = document.body ? document.body.innerText : '';
  const k = marker ? body.lastIndexOf(marker) : -1;
  return k < 0 ? '' : body.slice(k + marker.length).trim();
}
window.__radWeb = {v: 4, findInput, fill, check, submit, codeBlocks, answers, tail, md,
  hasInput: sels => !!findInput(sels),
  focusInput: sels => { const e = findInput(sels); if (e) { e.focus(); return true; } return false; }};
})();
"""


def js_call(fn: str, *args) -> str:
    return JS_LIB + f";window.__radWeb.{fn}({', '.join(json.dumps(a) for a in args)});"


def _sels(site: Site, kind: str) -> list[str]:
    own = list(getattr(site, kind))
    if kind == "inputs":
        return own
    extra = {"send": GENERIC_SEND, "answers": GENERIC_ANSWERS, "stop": GENERIC_STOP}[kind]
    return own + [s for s in extra if s not in own]


# ============================================================================ web views
def _make_page_classes():
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    class ChatPage(QWebEnginePage):
        def __init__(self, prof, owner):
            super().__init__(prof, owner)
            self.owner = owner                 # SiteView or PopupWindow
            try:
                self.permissionRequested.connect(self._on_permission)
            except AttributeError:
                pass

        def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802 - keep quiet
            pass

        def createWindow(self, _type):  # noqa: N802
            popup = PopupWindow(self.owner.window())
            return popup.view.page()

        def _on_permission(self, perm):
            try:
                from PyQt6.QtWebEngineCore import QWebEnginePermission
                T = QWebEnginePermission.PermissionType
                t = perm.permissionType()
                if t in (T.ClipboardReadWrite,):
                    perm.grant()
                elif t == T.Notifications:
                    perm.deny()
                elif t in (T.MediaAudioCapture, T.MediaVideoCapture, T.MediaAudioVideoCapture):
                    host = perm.origin().host()
                    what = {T.MediaAudioCapture: "the microphone", T.MediaVideoCapture: "the camera"}.get(
                        t, "the microphone and camera")
                    ok = QMessageBox.question(self.owner.window(), APP_TITLE,
                                              f"{host} wants to use {what}. Allow?") == \
                        QMessageBox.StandardButton.Yes
                    perm.grant() if ok else perm.deny()
                else:
                    perm.deny()
            except Exception:  # noqa: BLE001
                pass

    class SiteView(QWebEngineView):
        def __init__(self, site: Site, parent=None):
            super().__init__(parent)
            self.site = site
            self.loading = False
            self.loaded_once = False
            self.setPage(ChatPage(profile(), self))
            self.loadStarted.connect(self._started)
            self.loadFinished.connect(self._finished)

        def _started(self):
            self.loading = True

        def _finished(self, _ok):
            self.loading = False
            self.loaded_once = True

        def js(self, code: str, callback=None):
            if callback is None:
                self.page().runJavaScript(code)
            else:
                self.page().runJavaScript(code, 0, callback)

    class PopupWindow(QDialog):
        """window.open() of a page: sign-in flows stay here (same profile), other links go to the browser."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Sign in - " + APP_TITLE)
            self.resize(560, 720)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            self.view = QWebEngineView(self)
            self.view.setPage(ChatPage(profile(), self))
            lay.addWidget(self.view)
            self.view.page().windowCloseRequested.connect(self.close)
            self.view.titleChanged.connect(lambda t: self.setWindowTitle(t or APP_TITLE))
            self.view.urlChanged.connect(self._on_url)
            self._decided = False

        def _on_url(self, url: QUrl):
            if self._decided or url.isEmpty() or url.toString() in ("about:blank", ""):
                return
            self._decided = True
            host = url.host().lower()
            if any(host == h or host.endswith("." + h) for h in AUTH_HOSTS) or "auth" in host or "login" in host \
                    or url.scheme() not in ("http", "https"):
                self.show()
                self.raise_()
            else:
                QDesktopServices.openUrl(url)
                QTimer.singleShot(0, self.close)

        def done(self, r):
            try:
                self.view.setPage(None)
            except Exception:  # noqa: BLE001
                pass
            super().done(r)

    return SiteView, PopupWindow


_classes = None


def _view_classes():
    global _classes
    if _classes is None:
        _classes = _make_page_classes()
    return _classes


# ============================================================================ panel
_PANELS: list = []


class WebChatPanel(QWidget):
    """The contents of the "AI Web Chats" dock."""

    status = pyqtSignal(str)

    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.views: dict[str, object] = {}
        self.runs: dict[str, "WebRun"] = {}
        self._closed = False
        _PANELS.append(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        # ---- top bar: site switcher, navigation, address, more
        top = QHBoxLayout()
        top.setContentsMargins(4, 4, 4, 0)
        top.setSpacing(3)
        self.site_box = QComboBox()
        self.site_box.setToolTip("Web chat site (you sign in on the site itself; the login is remembered)")
        self.site_box.setMinimumContentsLength(10)
        self.site_box.activated.connect(self._on_site_activated)
        top.addWidget(self.site_box)
        self.b_back = self._tool("<", "Back", lambda: self._cur() and self._cur().back())
        self.b_fwd = self._tool(">", "Forward", lambda: self._cur() and self._cur().forward())
        self.b_reload = self._tool("Reload", "Reload the page (F5)", self.reload)
        self.b_home = self._tool("Home", "Go to the start page of the site", self.home)
        for b in (self.b_back, self.b_fwd, self.b_reload, self.b_home):
            top.addWidget(b)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Address")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self._go_url)
        self.url_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        top.addWidget(self.url_edit, 1)
        self.b_ext = self._tool("Browser", "Open this page in the external browser", self.open_external)
        top.addWidget(self.b_ext)
        self.b_more = QToolButton()
        self.b_more.setText("⋯")
        self.b_more.setToolTip("More")
        self.b_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # no style menu arrow: it was drawn clipped over the short text
        self.b_more.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")
        more = QMenu(self.b_more)
        more.addAction("Add custom site...", self.add_custom_site)
        self.a_remove_custom = more.addAction("Remove this custom site", self.remove_custom_site)
        more.addSeparator()
        more.addAction("Copy page address", lambda: QGuiApplication.clipboard().setText(self.url_edit.text()))
        more.addAction("Zoom in", lambda: self._zoom(1.1))
        more.addAction("Zoom out", lambda: self._zoom(1 / 1.1))
        more.addAction("Reset zoom", lambda: self._zoom(0))
        more.addSeparator()
        more.addAction("Open profile folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(profile_dir()))))
        more.addAction("Sign out of all sites (delete cookies)...", self.clear_cookies)
        more.aboutToShow.connect(lambda: self.a_remove_custom.setEnabled(bool(self.site() and self.site().custom)))
        self.b_more.setMenu(more)
        top.addWidget(self.b_more)
        lay.addLayout(top)

        # ---- pages
        self.stack = QStackedWidget()
        self.stack.setMinimumHeight(220)
        self.empty = QLabel()
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setText("Choose a site above and sign in normally.\nYour login is kept between sessions.")
        theme.role(self.empty, "muted")
        self.stack.addWidget(self.empty)
        lay.addWidget(self.stack, 1)

        # ---- composer
        comp = QVBoxLayout()
        comp.setContentsMargins(4, 0, 4, 2)
        comp.setSpacing(3)
        self.ask = QPlainTextEdit()
        self.ask.setPlaceholderText("Ask (optional) - the checked context is added; @file:name, @selection, "
                                    "@problems ... work too.  Ctrl+Enter sends.")
        self.ask.setMaximumHeight(56)
        self.ask.setTabChangesFocus(True)
        self.ask.installEventFilter(self)
        comp.addWidget(self.ask)
        row = QHBoxLayout()
        row.setSpacing(3)
        self.b_ctx = QToolButton()
        self.b_ctx.setText("Context ▾")
        self.b_ctx.setToolTip("What \"Send context\" adds to the question")
        self.b_ctx.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.b_ctx.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")
        ctx_menu = QMenu(self.b_ctx)
        self.ctx_actions: dict[str, QAction] = {}
        saved = str(settings().value("ai/web/context", "@selection") or "")
        for mention, label in (("@selection", "Selection (or the current file)"), ("@current", "Current file"),
                               ("@problems", "Problems (Error List)"), ("@form", "Current form (JSON)"),
                               ("@git", "Git changes"), ("@terminal", "Terminal output"),
                               ("@project", "Project files")):
            a = ctx_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(mention in saved.split())
            a.toggled.connect(self._save_ctx)
            self.ctx_actions[mention] = a
        self.b_ctx.setMenu(ctx_menu)
        row.addWidget(self.b_ctx)
        self.b_send = QPushButton("Send context")
        self.b_send.setToolTip("Write the question + context into the page's prompt box (Ctrl+Enter)")
        self.b_send.clicked.connect(lambda: self.send_context())
        row.addWidget(self.b_send)
        self.cb_submit = QCheckBox("Submit")
        self.cb_submit.setToolTip("Also press the site's Send button")
        self.cb_submit.setChecked(str(settings().value("ai/web/submit", "false")).lower() in ("1", "true", "yes"))
        self.cb_submit.toggled.connect(lambda v: settings().setValue("ai/web/submit", "true" if v else "false"))
        row.addWidget(self.cb_submit)
        row.addStretch(1)
        self.b_grab = QToolButton()
        self.b_grab.setText("Grab last code block")
        self.b_grab.setToolTip("Read the last code block of the page: copy, insert or apply it to a file")
        self.b_grab.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.b_grab.clicked.connect(lambda: self.grab_code(last_only=True))
        gm = QMenu(self.b_grab)
        gm.addAction("Grab last code block", lambda: self.grab_code(last_only=True))
        gm.addAction("All code blocks of the page...", lambda: self.grab_code(last_only=False))
        gm.addAction("Copy last answer as Markdown", self.copy_last_answer)
        self.b_grab.setMenu(gm)
        row.addWidget(self.b_grab)
        comp.addLayout(row)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        theme.role(self.msg, "muted")
        comp.addWidget(self.msg)
        lay.addLayout(comp)
        self.status.connect(self.msg.setText)

        self.rebuild_sites()
        theme.changed.connect(self._on_theme)

    # ------------------------------------------------------------------ helpers
    def _tool(self, text, tip, slot) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setAutoRaise(True)
        b.clicked.connect(slot)
        return b

    def eventFilter(self, obj, e):  # noqa: N802
        if obj is self.ask and e.type() == QEvent.Type.KeyPress:
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                    e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.send_context()
                return True
        return super().eventFilter(obj, e)

    def _on_theme(self, *_):
        for w in (self.empty, self.msg):
            theme.role(w, "muted")

    def _save_ctx(self, *_):
        settings().setValue("ai/web/context", " ".join(m for m, a in self.ctx_actions.items() if a.isChecked()))

    def say(self, text: str) -> None:
        self.status.emit(text)

    def _zoom(self, f: float):
        v = self._cur()
        if v is not None:
            v.setZoomFactor(1.0 if f == 0 else max(0.3, min(3.0, v.zoomFactor() * f)))

    # ------------------------------------------------------------------ sites
    def rebuild_sites(self, select: str | None = None) -> None:
        cur = select or (self.site().id if self.site() else str(settings().value("ai/web/site", "chatgpt")))
        self.site_box.blockSignals(True)
        self.site_box.clear()
        for s in all_sites():
            self.site_box.addItem(s.name, s.id)
            self.site_box.setItemData(self.site_box.count() - 1, s.url, Qt.ItemDataRole.ToolTipRole)
        self.site_box.addItem("Custom URL...", "__add__")
        i = self.site_box.findData(cur)
        self.site_box.setCurrentIndex(max(0, i))
        self.site_box.blockSignals(False)

    def site(self) -> Site | None:
        sid = self.site_box.currentData()
        return find_site(sid) if sid and sid != "__add__" else None

    def _on_site_activated(self, _i):
        if self.site_box.currentData() == "__add__":
            if not self.add_custom_site():
                self.rebuild_sites(str(settings().value("ai/web/site", "chatgpt")))
            return
        s = self.site()
        if s is not None:
            self.show_site(s.id)

    def show_site(self, site_id: str, load: bool = True, site: Site | None = None):
        """Make a site current (its page is created and loaded the first time)."""
        s = find_site(site_id) or site
        if s is None:
            return None
        i = self.site_box.findData(site_id)
        if i < 0:
            self.rebuild_sites(site_id)
            i = self.site_box.findData(site_id)
        if i >= 0:
            self.site_box.setCurrentIndex(i)
        settings().setValue("ai/web/site", site_id)
        v = self.views.get(site_id)
        if v is not self._cur():
            self.say("")
        if v is None and load:
            SiteView, _P = _view_classes()
            v = SiteView(s, self.stack)
            v.urlChanged.connect(lambda u, vv=v: self._on_url(vv, u))
            v.titleChanged.connect(lambda _t, vv=v: self._on_title(vv))
            v.loadProgress.connect(lambda p, vv=v: vv is self._cur() and p < 100 and self.say(f"Loading {p}%"))
            v.loadFinished.connect(lambda ok, vv=v: vv is self._cur() and self.say(
                "" if ok else f"Could not load {vv.site.url} - check the connection, then Reload."))
            self.views[site_id] = v
            self.stack.addWidget(v)
            v.load(QUrl(s.url))
        if v is not None:
            self.stack.setCurrentWidget(v)
            self.url_edit.setText(v.url().toString() or s.url)
        return v

    def ensure_loaded(self) -> None:
        if self._cur() is None and not self._closed:
            s = self.site() or SITES[0]
            self.show_site(s.id)

    def _cur(self):
        w = self.stack.currentWidget()
        return w if w is not self.empty else None

    def _on_url(self, view, url: QUrl):
        if view is self._cur():
            self.url_edit.setText(url.toString())

    def _on_title(self, view):
        if view is self._cur():
            self.url_edit.setToolTip(view.title())

    def view_for(self, site_id: str, show: bool = True, site: Site | None = None):
        if show:
            dock = getattr(self.win, "dock_ai_web", None)
            if dock is not None and (not dock.isVisible() or dock.visibleRegion().isEmpty()):
                dock.show()
                dock.raise_()          # it may be a hidden tab next to Solution Explorer / AI Chat
            return self.show_site(site_id, site=site)
        return self.views.get(site_id) or self.show_site(site_id, site=site)

    def reload(self):
        v = self._cur()
        if v is None:
            self.ensure_loaded()
        else:
            v.reload()

    def home(self):
        s, v = self.site(), self._cur()
        if s is not None and v is not None:
            v.load(QUrl(s.url))

    def _go_url(self):
        url = normalize_url(self.url_edit.text())
        if not url:
            return
        v = self._cur()
        if v is None:
            v = self.show_site((self.site() or SITES[0]).id)
        v.load(QUrl(url))

    def open_external(self):
        v = self._cur()
        url = v.url() if v is not None and not v.url().isEmpty() else QUrl((self.site() or SITES[0]).url)
        QDesktopServices.openUrl(url)

    def add_custom_site(self) -> bool:
        dlg = QDialog(self)
        dlg.setWindowTitle("Add custom web chat")
        f = QFormLayout(dlg)
        name, url = QLineEdit(), QLineEdit()
        url.setPlaceholderText("https://... (any chat site, or a local web UI such as Open WebUI)")
        name.setPlaceholderText("Name shown in the list")
        f.addRow("Name:", name)
        f.addRow("URL:", url)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        u = normalize_url(url.text())
        if not u:
            return False
        site = self.add_site(name.text().strip() or QUrl(u).host() or u, u)
        self.show_site(site.id)
        return True

    def add_site(self, name: str, url: str) -> Site:
        cs = custom_sites()
        n = 1
        ids = {s.id for s in cs}
        while f"custom{n}" in ids:
            n += 1
        site = Site(f"custom{n}", name, normalize_url(url), custom=True)
        save_custom_sites(cs + [site])
        self.rebuild_sites(site.id)
        _register_providers()
        return site

    def remove_custom_site(self):
        s = self.site()
        if s is None or not s.custom:
            return
        if QMessageBox.question(self, APP_TITLE, f"Remove the custom site \"{s.name}\"?") != \
                QMessageBox.StandardButton.Yes:
            return
        save_custom_sites([x for x in custom_sites() if x.id != s.id])
        v = self.views.pop(s.id, None)
        if v is not None:
            self.stack.removeWidget(v)
            v.deleteLater()
        self.rebuild_sites(SITES[0].id)
        self.show_site(SITES[0].id)
        _unregister_provider("web-" + s.id)

    def clear_cookies(self):
        if QMessageBox.question(self, APP_TITLE, "Delete the cookies of every web chat site?\n"
                                "You will have to sign in again.") != QMessageBox.StandardButton.Yes:
            return
        p = profile()
        p.cookieStore().deleteAllCookies()
        p.clearHttpCache()
        for v in self.views.values():
            v.reload()
        self.say("Signed out - cookies deleted.")

    # ------------------------------------------------------------------ context -> page
    def checked_mentions(self) -> list[str]:
        return [m for m, a in self.ctx_actions.items() if a.isChecked()]

    def compose(self, question: str | None = None, mentions: list[str] | None = None) -> str:
        from ..ai import context
        q = self.ask.toPlainText() if question is None else question
        ms = list(self.checked_mentions() if mentions is None else mentions)
        if "@selection" in ms and "@current" in ms:
            ms.remove("@selection")
        for m in context.parse_mentions(q):
            if m not in ms:
                ms.append(m)
        ctx = context.gather(self.win, ms) if ms else ""
        q = context.strip_mentions(q).strip() if ms else q.strip()
        if ctx and q:
            return f"{ctx}\n\n{q}"
        return ctx or q

    def send_context(self, text: str | None = None, site_id: str | None = None, submit: bool | None = None,
                     done=None) -> None:
        """Fill the page's prompt box (text=None: the composed question + context)."""
        body = self.compose() if text is None else text
        if not body.strip():
            self.say("Nothing to send - type a question or check some context (select code first).")
            if done:
                done(False, "empty")
            return
        sid = site_id or (self.site() or SITES[0]).id
        view = self.view_for(sid, show=True)
        submit = self.cb_submit.isChecked() if submit is None else submit

        def finished(ok, how):
            if ok:
                self.say(("Sent" if submit else "Written into the prompt box") + f" ({how}).")
                if text is None:
                    self.ask.clear()
            else:
                QGuiApplication.clipboard().setText(body)
                view.setFocus()
                self.say("Could not find the prompt box (sign in first?). The text is on the clipboard - click "
                         "the chat box and press Ctrl+V.")
            if done:
                done(ok, how)
        Filler(view, body, submit, finished).start()

    # ------------------------------------------------------------------ page -> IDE
    def grab_code(self, last_only: bool = True, callback=None) -> None:
        v = self._cur()
        if v is None:
            self.say("Open a chat first.")
            return

        def got(blocks):
            blocks = [(str(b.get("lang", "")), str(b.get("code", ""))) for b in (blocks or [])
                      if isinstance(b, dict)]
            if callback is not None:
                callback(blocks)
                return
            if not blocks:
                self.say("No code block on this page yet.")
                return
            self.say(f"{len(blocks)} code block(s) on the page.")
            dlg = CodeBlockDialog(self.win, blocks if not last_only else blocks[-1:], self)
            dlg.show()
        v.js(js_call("codeBlocks"), got)

    def copy_last_answer(self):
        v = self._cur()
        if v is None:
            return
        s = v.site

        def got(r):
            t = (r or {}).get("last", "") if isinstance(r, dict) else ""
            if t:
                QGuiApplication.clipboard().setText(t)
                self.say("Last answer copied as Markdown.")
            else:
                self.say("No answer found on this page.")
        v.js(js_call("answers", _sels(s, "answers"), _sels(s, "stop")), got)

    # ------------------------------------------------------------------ shutdown
    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        for r in list(self.runs.values()):
            r.abort("The IDE is closing")
        try:
            from PyQt6 import sip
            for v in list(self.views.values()):
                if not sip.isdeleted(v):
                    page = v.page()
                    if page is not None and not sip.isdeleted(page):
                        sip.delete(page)
                    sip.delete(v)
        except Exception:  # noqa: BLE001
            pass
        self.views.clear()
        if self in _PANELS:
            _PANELS.remove(self)


# ============================================================================ filling a page
class Filler(QObject):
    """fill -> check -> (insert fallback -> check) -> optional submit (button, else a real Enter key)."""

    def __init__(self, view, text: str, submit: bool, done, wait_input: float = 25.0):
        super().__init__(view)
        self.view, self.text, self.submit, self.done = view, text, submit, done
        self.site = view.site
        self.deadline = time.time() + wait_input
        self.sample = re.sub(r"\s+", " ", text).strip()[:60]
        self.how = ""

    def start(self):
        QTimer.singleShot(0, self._wait_input)

    def _wait_input(self):
        if self.view.loading or not self.view.loaded_once:
            if time.time() > self.deadline:
                return self._end(False, "page did not load")
            return QTimer.singleShot(400, self._wait_input)
        self.view.js(js_call("hasInput", _sels(self.site, "inputs")), self._has_input)

    def _has_input(self, ok):
        if ok:
            return self._fill("")
        if time.time() > self.deadline:
            return self._end(False, "no prompt box")
        QTimer.singleShot(600, self._wait_input)

    def _fill(self, mode: str):
        self.mode = mode
        self.view.js(js_call("fill", _sels(self.site, "inputs"), self.text, False, mode), self._filled)

    def _filled(self, r):
        if not isinstance(r, dict) or not r.get("ok"):
            return self._end(False, (r or {}).get("why", "fill failed") if isinstance(r, dict) else "fill failed")
        self.how = str(r.get("how", ""))
        QTimer.singleShot(350, lambda: self.view.js(js_call("check", _sels(self.site, "inputs"), self.sample),
                                                    self._checked))

    def _checked(self, r):
        ok = isinstance(r, dict) and r.get("ok")
        if not ok:
            nxt = {"": "insert", "insert": "text"}.get(self.mode)
            if nxt is not None:
                return self._fill(nxt)
            return self._end(False, "the page did not accept the text")
        if not self.submit:
            self.view.js(js_call("focusInput", _sels(self.site, "inputs")))
            self.view.setFocus()
            return self._end(True, self.how)
        QTimer.singleShot(400, lambda: self.view.js(js_call("submit", _sels(self.site, "send")), self._submitted))

    def _submitted(self, r):
        if isinstance(r, dict) and r.get("ok"):
            return self._end(True, self.how + " + send button")
        # no clickable button: a real (trusted) Enter key in the focused prompt box
        self.view.setFocus()
        self.view.js(js_call("focusInput", _sels(self.site, "inputs")))

        def enter():
            target = self.view.focusProxy() or self.view
            for t in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                QCoreApplication.postEvent(target, QKeyEvent(t, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier,
                                                             "\r"))
            self._end(True, self.how + " + Enter")
        QTimer.singleShot(150, enter)

    def _end(self, ok: bool, how: str):
        d, self.done = self.done, None
        if d is not None:
            d(ok, how)
        self.deleteLater()


# ============================================================================ provider kind "web"
class WebRun(QObject):
    """One ai.ChatJob answered by a web chat page."""

    POLL_MS = 700
    STABLE_POLLS = 4
    TIMEOUT = 300.0
    NO_ANSWER = 90.0

    def __init__(self, panel: WebChatPanel, site: Site, job, prompt: str):
        super().__init__(panel)
        self.panel, self.site, self.job, self.prompt = panel, site, job, prompt
        self.view = None
        self.count0, self.last0 = 0, ""
        self.text, self.emitted = "", ""
        self.stable = 0
        self.sent_at = 0.0
        self.finished = False
        self.marker = re.sub(r"\s+", " ", prompt.strip().splitlines()[-1] if prompt.strip() else "")[-50:].strip()
        self.timer = QTimer(self)
        self.timer.setInterval(self.POLL_MS)
        self.timer.timeout.connect(self._poll)
        job.on_abort(self._on_cancel)

    def start(self):
        self.panel.runs[self.site.id] = self
        self.view = self.panel.view_for(self.site.id, show=True, site=self.site)
        if self.view is None:
            return self._fail("the page could not be opened")
        self._snapshot_wait()

    def _snapshot_wait(self):
        if self.finished:
            return
        if self.view.loading or not self.view.loaded_once:
            return QTimer.singleShot(400, self._snapshot_wait)
        self.view.js(js_call("answers", _sels(self.site, "answers"), _sels(self.site, "stop")), self._snap)

    def _snap(self, r):
        if self.finished:
            return
        if isinstance(r, dict):
            self.count0, self.last0 = int(r.get("count", 0) or 0), str(r.get("last", "") or "")
        Filler(self.view, self.prompt, True, self._sent).start()

    def _sent(self, ok, how):
        if self.finished:
            return
        if not ok:
            return self._fail(f"{self.site.name}: could not type into the page ({how}). Open View > {APP_TITLE}, "
                              f"pick {self.site.name} and sign in first.")
        self.job.meta["fill"] = how
        self.sent_at = time.time()
        self.timer.start()

    def _poll(self):
        if self.finished:
            return
        self.view.js(js_call("answers", _sels(self.site, "answers"), _sels(self.site, "stop")), self._got)

    def _got(self, r):
        if self.finished or not isinstance(r, dict):
            return
        count, last, busy = int(r.get("count", 0) or 0), str(r.get("last", "") or ""), bool(r.get("busy"))
        if count > self.count0 or (count and count == self.count0 and last != self.last0):
            cur = last
            self._update(cur, busy)
        elif count == 0 and self.marker:
            self.view.js(js_call("tail", self.marker), lambda t: self._update(str(t or ""), busy))
        else:
            self._update(self.text, busy)

    def _update(self, cur: str, busy: bool):
        if self.finished:
            return
        if cur and cur != self.text:
            if cur.startswith(self.emitted):
                self.job.emit_delta(cur[len(self.emitted):])
                self.emitted = cur
            self.text = cur
            self.stable = 0
        elif cur and not busy:
            self.stable += 1
        waited = time.time() - self.sent_at
        if self.text and self.stable >= self.STABLE_POLLS:
            return self._finish()
        if waited > self.TIMEOUT:
            return self._finish() if self.text else self._fail(f"{self.site.name}: no answer after "
                                                               f"{int(self.TIMEOUT)} s")
        if not self.text and not busy and waited > self.NO_ANSWER:
            self._fail(f"{self.site.name}: no answer was detected on the page (the site may have changed its "
                       "layout - use Grab last code block / Copy last answer instead).")

    def _finish(self):
        if self.finished:
            return
        self.finished = True
        self.timer.stop()
        self.panel.runs.pop(self.site.id, None)
        self.job._end.emit(True, self.text)
        self.deleteLater()

    def _fail(self, msg: str):
        if self.finished:
            return
        self.finished = True
        self.timer.stop()
        self.panel.runs.pop(self.site.id, None)
        self.job._end.emit(False, msg)
        self.deleteLater()

    def abort(self, msg: str):
        self._fail(msg)

    def _on_cancel(self):
        # called by job.cancel() (UI thread): stop polling and press the site's Stop button
        if self.finished:
            return
        self.finished = True
        self.timer.stop()
        self.panel.runs.pop(self.site.id, None)
        try:
            self.view.js(js_call("submit", _sels(self.site, "stop")))
        except Exception:  # noqa: BLE001
            pass
        self.deleteLater()


def _make_provider_class():
    from .. import ai

    class WebChatProvider(ai.Provider):
        kind = "web"
        DETECT_TTL = 2.0

        def __init__(self, site: Site):
            super().__init__()
            self.site = site
            self.id = f"web-{site.id}"
            self.name = f"{site.name} (web)"
            self.homepage = site.url
            self.description = (f"The {site.name} web page inside the IDE (View > {APP_TITLE}). Free with your own "
                                f"{site.name} account - no API key. Answers are read from the page (best effort).")
            self.login_hint = f"Open View > {APP_TITLE}, choose {site.name} and sign in on the page."
            self.install_hint = "Nothing to install."
            self._history: list[tuple[str, str]] = []

        def models(self) -> list[str]:
            return []

        @property
        def default_model(self) -> str:
            return ""

        def _detect(self):
            if not _PANELS:
                return False, f"the IDE window is not open (View > {APP_TITLE})"
            return True, f"answers come from the {self.site.name} page (sign in there first)"

        def chat(self, messages, model=None, system=None, temperature=None, max_tokens=None, cwd=None, **opts):
            job = ai.ChatJob(self.id, "")
            sys_text, msgs = ai.normalize(messages, system)
            if not msgs:
                return job.fail_soon("Nothing to send (no user message).")
            if not _PANELS:
                return job.fail_soon(f"{self.name}: the IDE window with {APP_TITLE} is not open.")
            app = QCoreApplication.instance()
            if app is not None and QThread.currentThread() is not app.thread():
                return job.fail_soon(f"{self.name}: web chats can only be used from the UI thread.")
            panel = _PANELS[-1]
            if self.site.id in panel.runs:
                return job.fail_soon(f"{self.name} is still answering the previous request.")
            prompt = self._prompt(sys_text, msgs)
            job.meta["purpose"] = opts.get("purpose", "chat")
            job.meta["site"] = self.site.url
            from ..ai.providers import _live_jobs
            _live_jobs.add(job)
            run = WebRun(panel, self.site, job, prompt)
            job.finished.connect(lambda t, m=msgs: self._remember(m, t))
            job.finished.connect(lambda _t: _live_jobs.discard(job))
            job.failed.connect(lambda _e: _live_jobs.discard(job))
            QTimer.singleShot(0, run.start)
            return job

        def _prompt(self, sys_text: str, msgs) -> str:
            """Only the new message when the page already holds the earlier conversation."""
            hist = [(m.role, m.content) for m in msgs[:-1]]
            if hist and hist == self._history:
                return msgs[-1].content
            return ai.flatten(msgs, sys_text)

        def _remember(self, msgs, answer: str):
            self._history = [(m.role, m.content) for m in msgs] + [("assistant", answer)]

        def complete(self, prefix, suffix="", language="", model=None, max_tokens=160):
            job = ai.ChatJob(self.id, "")
            return job.fail_soon("Web chats are too slow for inline completion - pick a local model or CLI.")

    return WebChatProvider


_provider_cls = None


def _register_providers() -> None:
    global _provider_cls
    try:
        from .. import ai
        if _provider_cls is None:
            _provider_cls = _make_provider_class()
        from ..ai import providers as _P
        h = getattr(_P, "_hub", None)
        # one providers_changed for the whole batch: each one refilled the agent / chat provider lists
        # (detection of every provider included), nine times at start-up (~1 s)
        was = h.blockSignals(True) if h is not None else None
        changed = False
        try:
            for s in all_sites():
                pid = f"web-{s.id}"
                try:
                    old = ai.get(pid)
                except KeyError:
                    old = None
                if old is None or getattr(old, "site", None) != s:
                    ai.register(_provider_cls(s))
                    changed = True
        finally:
            if h is not None:
                h.blockSignals(was)
                if changed:
                    h.providers_changed.emit()
    except Exception:  # noqa: BLE001 - the AI core is optional for the web chats
        pass


def _unregister_provider(pid: str) -> None:
    try:
        from ..ai.providers import _providers, hub
        _providers.pop(pid, None)
        hub().providers_changed.emit()
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ code blocks -> IDE
def _target_editor(win):
    try:
        from ..ai import context
        return context.current_editor(win)
    except Exception:  # noqa: BLE001
        return None, ""


def _open_editor_for(win, path: Path):
    """The open editor of a file (None when it is not open)."""
    tabs = getattr(win, "tabs", None)
    if tabs is None:
        return None
    want = os.path.normcase(str(path))
    for i in range(tabs.count()):
        w = tabs.widget(i)
        ed = getattr(w, "editor", None)
        for obj in (w, ed):
            p = getattr(obj, "path", None) if obj is not None else None
            if p and not callable(p):
                try:
                    if os.path.normcase(str(Path(p).resolve())) == os.path.normcase(str(Path(want).resolve())):
                        return ed
                except OSError:
                    pass
    return None


def apply_text_to_file(win, path: Path, new_text: str) -> None:
    """Write the accepted text: into the open editor (undoable), else to disk."""
    ed = _open_editor_for(win, path)
    if ed is not None and hasattr(ed, "replaceSelectedText"):
        ed.selectAll()
        ed.replaceSelectedText(new_text)
        return
    path.write_text(new_text, encoding="utf-8")


class DiffDialog(QDialog):
    """Fallback diff preview (Accept / Reject) when radide.ai.diffview is not available."""

    def __init__(self, parent, path: Path, old: str, new: str):
        super().__init__(parent)
        self.setWindowTitle(f"Apply to {path.name}")
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        info = QLabel(f"Review the changes to <b>{html.escape(str(path))}</b>:")
        lay.addWidget(info)
        view = QTextBrowser()
        view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        view.setHtml(self.render(old, new, path.name))
        lay.addWidget(view, 1)
        bb = QDialogButtonBox()
        self.b_accept = bb.addButton("Accept", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton("Reject", QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @staticmethod
    def render(old: str, new: str, name: str) -> str:
        add_bg, del_bg = ("#1E3A1E", "#4B1818") if theme.is_dark() else ("#DDFBE6", "#FDE2E1")
        lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{name}", f"b/{name}",
                                          lineterm="", n=3))
        if not lines:
            return f"<p style='color:{theme.color('muted')}'>No changes - the code is identical.</p>"
        out = []
        for ln in lines:
            e = html.escape(ln) or "&nbsp;"
            if ln.startswith("+") and not ln.startswith("+++"):
                out.append(f"<div style='background:{add_bg}'>{e}</div>")
            elif ln.startswith("-") and not ln.startswith("---"):
                out.append(f"<div style='background:{del_bg}'>{e}</div>")
            elif ln.startswith("@@"):
                out.append(f"<div style='color:{theme.color('link')}'>{e}</div>")
            else:
                out.append(f"<div>{e}</div>")
        return ("<div dir='ltr' style=\"font-family:Consolas,monospace; font-size:9pt; white-space:pre\">"
                + "".join(out) + "</div>")


def review_and_apply(win, path: Path, new_text: str, parent=None) -> bool:
    """Diff preview -> Accept writes the file.  Uses the shared radide.ai.diffview when it exists."""
    path = Path(path)
    try:
        from ..ai.diffview import apply_file_change  # the shared review dialog of 9.3
    except ImportError:
        apply_file_change = None
    if apply_file_change is not None:
        ok = bool(apply_file_change(win, path, new_text, parent=parent, title=f"Apply to {path.name}",
                                    note="Code from the AI web chat"))
        if ok:
            try:
                win.log(f"[AI Web Chats] applied a code block to {path}")
            except Exception:  # noqa: BLE001
                pass
        return ok
    ed = _open_editor_for(win, path)
    if ed is not None:
        old = ed.toPlainText()
    else:
        try:
            old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        except OSError:
            old = ""
    dlg = DiffDialog(parent or win, path, old, new_text)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    apply_text_to_file(win, path, new_text)
    try:
        win.log(f"[AI Web Chats] applied a code block to {path}")
    except Exception:  # noqa: BLE001
        pass
    return True


class CodeBlockDialog(QDialog):
    """Code block(s) read from a web chat page -> Copy / Insert / Replace selection / Apply to file / New file."""

    EXT = {"python": ".py", "py": ".py", "javascript": ".js", "js": ".js", "typescript": ".ts", "ts": ".ts",
           "html": ".html", "css": ".css", "php": ".php", "sql": ".sql", "json": ".json", "ring": ".ring",
           "vb": ".vb", "vbnet": ".vb", "c": ".c", "cpp": ".cpp", "c++": ".cpp", "java": ".java", "go": ".go",
           "rust": ".rs", "bash": ".sh", "sh": ".sh", "powershell": ".ps1", "xml": ".xml", "yaml": ".yml",
           "lua": ".lua", "ruby": ".rb", "csharp": ".cs", "cs": ".cs", "kotlin": ".kt", "markdown": ".md"}

    def __init__(self, win, blocks: list[tuple[str, str]], parent=None):
        super().__init__(parent or win)
        self.win = win
        self.blocks = blocks
        self.setWindowTitle("Code from the web chat")
        self.resize(760, 520)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        for i, (lang, code) in enumerate(blocks):
            first = next((ln.strip() for ln in code.splitlines() if ln.strip()), "")[:40]
            it = QListWidgetItem(f"{i + 1}. {lang or 'code'} - {first}")
            self.list.addItem(it)
        self.list.currentRowChanged.connect(self._show)
        split.addWidget(self.list)
        self.code = QPlainTextEdit()
        self.code.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        f = self.code.font()
        f.setFamily("Consolas")
        self.code.setFont(f)
        self.code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        split.addWidget(self.code)
        split.setSizes([200, 560])
        self.list.setVisible(len(blocks) > 1)
        lay.addWidget(split, 1)
        self.lang = QLabel("")
        theme.role(self.lang, "muted")
        lay.addWidget(self.lang)
        row = QHBoxLayout()
        for text, slot, tip in (("Copy", self.copy, "Copy the code"),
                                ("Insert at cursor", self.insert, "Insert into the active editor"),
                                ("Replace selection", self.replace, "Replace the selected code of the editor"),
                                ("Apply to file...", self.apply, "Replace a whole file (diff preview first)"),
                                ("New file...", self.new_file, "Save the code as a new file")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        row.addWidget(close)
        lay.addLayout(row)
        self.list.setCurrentRow(len(blocks) - 1)
        self._show(len(blocks) - 1)

    def _show(self, i: int):
        if 0 <= i < len(self.blocks):
            lang, code = self.blocks[i]
            self.code.setPlainText(code)
            self.lang.setText(f"Language: {lang}" if lang else "Language: (not given)")

    def current_lang(self) -> str:
        i = self.list.currentRow()
        return self.blocks[i][0] if 0 <= i < len(self.blocks) else ""

    def text(self) -> str:
        return self.code.toPlainText()

    def copy(self):
        QGuiApplication.clipboard().setText(self.text())

    def _editor(self):
        ed, path = _target_editor(self.win)
        if ed is None or not hasattr(ed, "replaceSelectedText"):
            QMessageBox.information(self, APP_TITLE, "Open a code editor first (click in it, then come back).")
            return None, ""
        return ed, path

    def insert(self):
        ed, _ = self._editor()
        if ed is not None:
            try:
                # "insert" keeps the selected code: the block goes right after it
                if isinstance(getattr(ed, "_selection", None), tuple) and hasattr(ed, "setSelection"):
                    l1, c1, l2, c2 = ed._selection
                    end = max((l1, c1), (l2, c2))
                    ed.setSelection(*end, *end)
                elif hasattr(ed, "textCursor") and hasattr(ed, "setTextCursor"):
                    cur = ed.textCursor()
                    cur.setPosition(cur.selectionEnd())
                    ed.setTextCursor(cur)
            except Exception:  # noqa: BLE001
                pass
            ed.replaceSelectedText(self.text())

    def replace(self):
        ed, _ = self._editor()
        if ed is not None:
            ed.replaceSelectedText(self.text())

    def apply(self):
        ed, path = _target_editor(self.win)
        start = path or str(_project_dir(self.win) or Path.home())
        if not path or not Path(path).is_file():
            path, _ = QFileDialog.getOpenFileName(self, "Apply the code to which file?", start)
            if not path:
                return
        else:
            ans = QMessageBox.question(self, APP_TITLE, f"Apply the code to {Path(path).name}?\n\n"
                                       "Yes = this file, No = choose another file.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                       QMessageBox.StandardButton.Cancel)
            if ans == QMessageBox.StandardButton.Cancel:
                return
            if ans == QMessageBox.StandardButton.No:
                path, _ = QFileDialog.getOpenFileName(self, "Apply the code to which file?", start)
                if not path:
                    return
        text = self.text()
        if not text.endswith("\n"):
            text += "\n"
        review_and_apply(self.win, Path(path), text, parent=self)

    def new_file(self):
        ext = self.EXT.get(self.current_lang(), ".txt")
        start = _project_dir(self.win) or Path.home()
        path, _ = QFileDialog.getSaveFileName(self, "New file", str(Path(start) / f"new_file{ext}"))
        if not path:
            return
        text = self.text()
        Path(path).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        opener = getattr(self.win, "open_file", None)
        if callable(opener):
            try:
                opener(Path(path))
            except Exception:  # noqa: BLE001
                pass


def _project_dir(win) -> Path | None:
    try:
        from ..ai import context
        return context.solution_folder(win)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================ public helpers + install
def panel(win) -> WebChatPanel | None:
    return getattr(win, "ai_web", None)


def show(win, site_id: str | None = None) -> WebChatPanel | None:
    p = panel(win)
    dock = getattr(win, "dock_ai_web", None)
    if p is None or dock is None:
        return None
    try:
        from . import workbench
        wb = workbench.get(win)
        if wb is not None and getattr(wb, "mode", "vs") != "vs":
            wb.show_view("webchats")
    except Exception:  # noqa: BLE001
        pass
    dock.show()
    dock.raise_()

    def roomy():
        # a browser needs room: widen / heighten a thin dock once it is laid out
        try:
            if dock.isFloating() or not dock.isVisible():
                return
            if dock.width() < 460:
                win.resizeDocks([dock], [min(560, max(460, win.width() // 3))], Qt.Orientation.Horizontal)
            if dock.height() < win.height() // 2:
                win.resizeDocks([dock], [int(win.height() * 0.62)], Qt.Orientation.Vertical)
        except Exception:  # noqa: BLE001
            pass
    QTimer.singleShot(0, roomy)
    if site_id:
        p.show_site(site_id)
    else:
        p.ensure_loaded()
    return p


def send_to_web(win, text: str, site: str | None = None, submit: bool = False, done=None) -> bool:
    """Write text into a web chat's prompt box (opens the dock)."""
    p = show(win, site)
    if p is None:
        return False
    p.send_context(text, site_id=site, submit=submit, done=done)
    return True


def _send_selection(win):
    p = show(win)
    if p is None:
        return
    p.send_context(p.compose(question="", mentions=["@selection"]))


def install(win) -> None:
    p = WebChatPanel(win)
    d = QDockWidget(APP_TITLE, win)
    d.setObjectName(APP_TITLE)
    d.setWidget(p)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d)
    # a browser needs height: share the tall Solution Explorer / AI Chat slot instead of a thin strip
    near = next((x for x in (getattr(win, "dock_ai_chat", None), getattr(win, "dock_solution", None))
                 if isinstance(x, QDockWidget) and win.dockWidgetArea(x) == Qt.DockWidgetArea.RightDockWidgetArea),
                None)
    if near is not None:
        win.tabifyDockWidget(near, d)
    d.hide()
    d.visibilityChanged.connect(lambda vis: vis and p.ensure_loaded())
    win.dock_ai_web = d
    win.ai_web = p
    a = QAction("AI &Web Chats", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+W"))
    a.setToolTip("ChatGPT, Gemini, Claude, DeepSeek ... in the IDE, with your own account (no API key)")
    a.triggered.connect(lambda: show(win))
    win.a_ai_web = a
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addSeparator()
        view.addAction(a)
        view.addAction(d.toggleViewAction())
        d.toggleViewAction().setText("AI Web Chats (dock)")
        d.toggleViewAction().setVisible(False)
    _register_providers()

    # editor right-click: send the selection to the web chat
    def editor_menu(m, _form_name) -> None:
        m.addSeparator()
        m.addAction("Send Selection to AI Web Chat", lambda: _send_selection(win))
    win.extension_points.on("editor_menu", editor_menu, "AI web")

    win.extension_points.add_shutdown_step(lambda: p.shutdown(), "AI web")
    app = QCoreApplication.instance()
    if app is not None and not getattr(app, "_radide_webchat_hook", False):
        app._radide_webchat_hook = True
        app.aboutToQuit.connect(release_profile)


__all__ = ["SITES", "Site", "WebChatPanel", "CodeBlockDialog", "DiffDialog", "profile", "profile_dir",
           "release_profile", "send_to_web", "show", "panel", "review_and_apply", "apply_text_to_file",
           "all_sites", "custom_sites", "find_site", "clean_user_agent", "js_call", "JS_LIB"]
