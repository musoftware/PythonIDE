"""Form localization like VB 2005 (Localizable = True).

Form properties (Properties window, form selected):
    Localizable        True: the form keeps one resource table per language
    Language           (Default) or a language ("Arabic (ar)"): the designer edits that language -
                       Text / ToolTip / Items / TabPages / Columns (and string properties of user controls)
                       typed while a language is selected go to its table, the base values stay
    RightToLeft        text is right-aligned / read right to left (per language)
    RightToLeftLayout  the whole form is mirrored (per language, used with RightToLeft)

Storage: the .form keeps the tables under "resources" -
    {"ar": {"name": "Arabic", "RightToLeft": true, "RightToLeftLayout": true,
            "strings": {"$this.Text": "...", "lblName.Text": "...", "cmbCity.Items": "a;b"}}}
and Save writes one .resx-like JSON per language next to the form: <Form>.<lang>.resx.json.

Generated python-tk / python-qt code embeds the tables and picks the language at start-up:
RADIDE_LANG environment variable, else language.txt next to the program, else the Windows / system UI
language.  A <Form>.<lang>.resx.json next to the program overrides / adds a language (translators).
At run time: self.ApplyLanguage("ar") switches live, self.CurrentLanguage tells the language.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..controls import PropDef

DEFAULT = "(Default)"
LANGUAGES = [("ar", "Arabic"), ("en", "English"), ("fr", "French"), ("de", "German"), ("es", "Spanish"),
             ("it", "Italian"), ("pt", "Portuguese"), ("ru", "Russian"), ("tr", "Turkish"), ("fa", "Persian"),
             ("ur", "Urdu"), ("he", "Hebrew"), ("zh", "Chinese"), ("ja", "Japanese"), ("ko", "Korean"),
             ("hi", "Hindi"), ("id", "Indonesian"), ("nl", "Dutch"), ("pl", "Polish"), ("sv", "Swedish")]
RTL_LANGUAGES = {"ar", "fa", "ur", "he"}
LOCALIZABLE = ("Text", "ToolTip", "Items", "TabPages", "Columns")
FLAGS = ("RightToLeft", "RightToLeftLayout")
GENERATOR = "RAD IDE"


# ====================================================================== model
def language_label(code: str) -> str:
    if not code:
        return DEFAULT
    name = dict(LANGUAGES).get(code, code)
    return f"{name} ({code})"


def language_code(label) -> str:
    """'Arabic (ar)' -> 'ar'; '(Default)' / '' -> ''."""
    s = str(label or "").strip()
    if not s or s == DEFAULT:
        return ""
    m = re.search(r"\(([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)?)\)$", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)?", s):
        return s
    for code, name in LANGUAGES:
        if name.lower() == s.lower():
            return code
    return ""


def resources(form) -> dict:
    res = form.extra.get("resources")
    if not isinstance(res, dict):
        res = {}
        form.extra["resources"] = res
    return res


def table(form, code: str, create: bool = True) -> dict | None:
    res = resources(form)
    t = res.get(code)
    if not isinstance(t, dict):
        if not create:
            return None
        rtl = code.split("-")[0].split("_")[0] in RTL_LANGUAGES
        t = {"name": dict(LANGUAGES).get(code, code), "RightToLeft": rtl, "RightToLeftLayout": rtl, "strings": {}}
        res[code] = t
    if not isinstance(t.get("strings"), dict):
        t["strings"] = {}
    return t


def is_localizable(form) -> bool:
    p = form.props
    return bool(p.get("Localizable") or p.get("RightToLeft") or p.get("RightToLeftLayout"))


def localizable_props(form, ctrl) -> list[str]:
    """Names of the localizable properties of ctrl (None = the form: Text)."""
    if ctrl is None:
        return ["Text"]
    out = [k for k in LOCALIZABLE if k in ctrl.props and isinstance(ctrl.props.get(k), str)]
    try:
        from ..usercontrols import USER_CONTROLS, spec_of
        info = USER_CONTROLS.get(ctrl.type)
        if info is not None:
            out += [p["name"] for p in spec_of(info["data"])["properties"] if p["type"] == "str"]
    except ImportError:
        pass
    return out


def key_of(ctrl, prop: str) -> str:
    return f"{'$this' if ctrl is None else ctrl.name}.{prop}"


def base_strings(form) -> dict:
    """Every localizable value of the form in the default language: {key: value}."""
    out = {key_of(None, "Text"): str(form.props.get("Text", ""))}
    for c in form.controls:
        for prop in localizable_props(form, c):
            out[key_of(c, prop)] = c.props.get(prop, "")
    return out


def flags_for(form, code: str) -> tuple[bool, bool]:
    if code:
        t = table(form, code, create=False)
        if t is not None:
            return bool(t.get("RightToLeft")), bool(t.get("RightToLeftLayout"))
    return bool(form.props.get("RightToLeft")), bool(form.props.get("RightToLeftLayout"))


def rename_keys(form, old: str, new: str) -> None:
    for t in resources(form).values():
        if isinstance(t, dict) and isinstance(t.get("strings"), dict):
            for k in list(t["strings"]):
                if k.split(".", 1)[0] == old:
                    t["strings"][f"{new}.{k.split('.', 1)[1]}"] = t["strings"].pop(k)


def form_defs(form) -> list[PropDef]:
    """Extra form properties for the Properties window."""
    codes = [c for c in resources(form) if c]
    choices = [DEFAULT] + [language_label(c) for c in codes] + \
        [language_label(c) for c, _ in LANGUAGES if c not in codes]
    cur = str(form.props.get("Language") or DEFAULT)
    if cur not in choices:
        choices.append(cur)
    return [
        PropDef("Localizable", "bool", False, "True: the form keeps a resource table per language (Text, "
                "ToolTip, Items...). Pick a Language to translate the form; the program shows the user's "
                "language.", (), "Design"),
        PropDef("Language", "enum", DEFAULT, "The language the designer is editing. (Default) = the base "
                "values; another language: what you type in Text / ToolTip / Items goes to its resource table.",
                tuple(choices), "Design"),
        PropDef("RightToLeft", "bool", False, "Text is read from right to left (Arabic, Hebrew...). Per "
                "language when a Language is selected.", (), "Appearance"),
        PropDef("RightToLeftLayout", "bool", False, "Mirror the whole form (controls placed from the right) "
                "when RightToLeft is True. Per language when a Language is selected.", (), "Layout"),
    ]


def resx_documents(form) -> dict[str, dict]:
    """{lang: .resx.json content} for every language of the form."""
    out = {}
    for code, t in resources(form).items():
        if not code or not isinstance(t, dict):
            continue
        out[code] = {"generator": GENERATOR, "form": form.name, "language": code,
                     "name": t.get("name") or dict(LANGUAGES).get(code, code),
                     "RightToLeft": bool(t.get("RightToLeft")), "RightToLeftLayout": bool(t.get("RightToLeftLayout")),
                     "strings": dict(sorted((t.get("strings") or {}).items()))}
    return out


def write_resx(form, folder: Path) -> list[Path]:
    """Write <Form>.<lang>.resx.json files (and remove the ones of deleted languages we wrote before)."""
    folder = Path(folder)
    docs = resx_documents(form) if form.props.get("Localizable") else {}
    written = []
    for code, doc in docs.items():
        p = folder / f"{form.name}.{code}.resx.json"
        text = json.dumps(doc, indent=2, ensure_ascii=False)
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
        written.append(p)
    for p in folder.glob(f"{form.name}.*.resx.json"):
        code = p.name[len(form.name) + 1:-len(".resx.json")]
        if code not in docs:
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("generator") == GENERATOR:
                    p.unlink()
            except (OSError, ValueError, AttributeError):
                pass
    return written


def import_resx(form, path: Path) -> str:
    """Read a .resx.json into the form's tables; returns the language code."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    code = str(d.get("language") or Path(path).name.split(".")[-3])
    t = table(form, code)
    for k in FLAGS:
        if k in d:
            t[k] = bool(d[k])
    if d.get("name"):
        t["name"] = str(d["name"])
    t["strings"].update({str(k): v for k, v in (d.get("strings") or {}).items()})
    form.props["Localizable"] = True
    return code


def mirror_props(form, ctrl, props: dict) -> dict:
    """Design-time mirror: Left measured from the right edge of the container."""
    from ..layout import client_size
    parent = form.find(ctrl.parent) if ctrl.parent else None
    cw, _ch = client_size(form, parent)
    out = dict(props)
    try:
        out["Left"] = int(cw) - int(props["Left"]) - int(props["Width"])
    except (KeyError, TypeError, ValueError):
        pass
    out["_RTLMirror"] = True        # text alignment: the previews get a right-to-left layout direction
    return out


# ====================================================================== code generation
TK_RUNTIME = '''

def _rad_languages(form, embedded):
    """Languages of a form: the embedded tables + <form>.<lang>.resx.json files next to the program."""
    import glob
    out = list(embedded)
    here = os.path.dirname(os.path.abspath(__file__))
    for p in glob.glob(os.path.join(here, form + ".*.resx.json")):
        code = os.path.basename(p)[len(form) + 1:-len(".resx.json")]
        if code and code not in out:
            out.append(code)
    return out


def _rad_pick_language(available):
    """RADIDE_LANG, else language.txt next to the program, else the user's UI language ("" = default)."""
    import locale
    want = os.environ.get("RADIDE_LANG", "").strip()
    if not want:
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, "language.txt"), encoding="utf-8") as f:
                want = f.read().strip()
        except OSError:
            want = ""
    if not want:
        try:
            import ctypes
            want = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
        except (AttributeError, OSError, ImportError):
            want = ""
    if not want:
        try:
            want = locale.getlocale()[0] or os.environ.get("LANG", "")
        except ValueError:
            want = os.environ.get("LANG", "")
    want = want.split(".")[0].replace("-", "_").lower()
    if want in ("", "default", "(default)"):
        return ""
    low = {a.lower().replace("-", "_"): a for a in available}
    if want in low:
        return low[want]
    return low.get(want.split("_")[0], "")


def _rad_resources(form, lang, embedded):
    """The table of *lang*: embedded + <form>.<lang>.resx.json next to the program (None = no such language)."""
    if not lang:
        return None
    res = None
    if lang in embedded:
        res = dict(embedded[lang])
        res["strings"] = dict(res.get("strings") or {})
    try:
        import json
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, f"{form}.{lang}.resx.json"), encoding="utf-8") as f:
            ext = json.load(f)
        res = res or {"strings": {}}
        res["strings"].update(ext.get("strings") or {})
        for k in ("RightToLeft", "RightToLeftLayout"):
            if k in ext:
                res[k] = bool(ext[k])
    except (OSError, ValueError, AttributeError):
        pass
    return res
'''

QT_EXTRA_RUNTIME = '''

class _RadMirror(QObject):
    """Mirrored (right-to-left) placement of children that have no Anchor / Dock layout."""

    def __init__(self, host):
        super().__init__(host)
        self.host, self.items = host, []
        host.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.host and ev.type() == QEvent.Type.Resize:
            self.apply()
        return False

    def apply(self):
        cw, ch = self.host.width(), self.host.height()
        for w, (x, y, ww, hh, rx, ry, rw, rh) in self.items:
            w.setGeometry(round(x + rx * cw), round(y + ry * ch), max(0, round(ww + rw * cw)),
                          max(0, round(hh + rh * ch)))
'''

COMMON_METHODS = '''
    # ---------------------------------------------------------------- localization
    Languages = {langs!r}

    def ApplyLanguage(self, lang=None, inherit=None):
        """Show the form in a language ("ar", "fr" ...; "" = the default language); None = the user's."""
        langs = _rad_languages({form!r}, _RAD_RESOURCES_{form})
        if lang is None:
            lang = _rad_pick_language(langs)
        res = _rad_resources({form!r}, lang, _RAD_RESOURCES_{form})
        if res is None and inherit is not None:
            rtl, layout = inherit
        elif res is None:
            rtl, layout = {base_rtl!r}, {base_layout!r}
        else:
            rtl, layout = bool(res.get("RightToLeft")), bool(res.get("RightToLeftLayout"))
        for name in {ucs!r}:                       # user controls first: the form's values win
            fn = getattr(getattr(self, name, None), "ApplyLanguage", None)
            if fn is not None:
                fn(lang, (rtl, layout))
        strings = dict(_RAD_DEFAULT_{form})
        if res is not None:
            strings.update(res.get("strings") or {{}})
        for key, value in strings.items():
            try:
                self._loc_set(key, value)
            except Exception:  # noqa: BLE001 - a bad entry must not stop the form
                pass
        self._loc_direction(bool(rtl), bool(rtl and layout))
        self.CurrentLanguage = lang if res is not None else ""
        self.RightToLeft, self.RightToLeftLayout = bool(rtl), bool(rtl and layout)
        return self.CurrentLanguage
'''

TK_METHODS = '''
    def _loc_set(self, key, value):
        obj, _, prop = key.partition(".")
        if obj == "$this":
            if prop == "Text" and "_uc_name" not in self.__dict__:
                self.root.title(value)
            return
        w = self.__dict__.get(obj)
        if w is None:
            return
        if isinstance(getattr(type(w), prop, None), property):      # a user control property
            setattr(w, prop, value)
            return
        var = self.__dict__.get(obj + "_var")
        items = [s.strip() for s in str(value).split(";") if s.strip()]
        if prop == "Text":
            if isinstance(var, tk.StringVar):
                var.set(value)
            elif isinstance(w, tk.Text):
                w.delete("1.0", "end")
                w.insert("1.0", value)
            else:
                w.configure(text=value)
        elif prop == "ToolTip":
            tip = self._loc_tips.get(obj)
            if tip is not None:
                tip.text = value
            elif value:
                self._loc_tips[obj] = _ToolTip(w, value)
        elif prop == "Items":
            if isinstance(w, tk.Listbox):
                w.delete(0, "end")
                for it in items:
                    w.insert("end", it)
            else:
                w.configure(values=items)
        elif prop == "TabPages":
            for i, text in enumerate(items[:len(w.tabs())]):
                w.tab(i, text=text)
        elif prop == "Columns" and hasattr(w, "heading"):
            for i, text in enumerate(items):
                try:
                    w.heading(f"#{{i + 1}}" if w["show"] != "tree" else "#0", text=text)
                except tk.TclError:
                    break

    _LOC_ANCHOR = {{"w": "e", "e": "w", "nw": "ne", "ne": "nw", "sw": "se", "se": "sw"}}

    def _loc_swap_align(self, widget):
        for child in widget.winfo_children():
            if getattr(child, "_rad_uc", False):     # a user control mirrors its own content
                continue
            for opt, table in (("anchor", self._LOC_ANCHOR), ("justify", {{"left": "right", "right": "left"}})):
                try:
                    v = str(child.cget(opt))
                except (tk.TclError, AttributeError):
                    continue
                if v in table:
                    try:
                        child.configure(**{{opt: table[v]}})
                    except tk.TclError:
                        pass
            self._loc_swap_align(child)

    def _loc_direction(self, rtl, mirror):
        if self.__dict__.get("_loc_mirrored", False) != mirror:
            self._loc_mirrored = mirror
            for name, geo in self._places.items():
                geo["x"] = -geo.get("x", 0) - geo.get("width", 0)
                geo["relx"] = 1 - geo.get("relx", 0) - geo.get("relwidth", 0)
                w = self.__dict__.get(name)
                w = getattr(w, "root", w) if "_uc_name" in getattr(w, "__dict__", {{}}) else w
                try:
                    if w is not None and w.winfo_manager() == "place":
                        w.place(**geo)
                except tk.TclError:
                    pass
        if self.__dict__.get("_loc_rtl", False) != rtl:
            self._loc_rtl = rtl
            self._loc_swap_align(self.root)
'''

QT_METHODS = '''
    def _loc_set(self, key, value):
        obj, _, prop = key.partition(".")
        if obj == "$this":
            if prop == "Text" and not hasattr(self, "_uc_name"):
                self.setWindowTitle(str(value))
            return
        w = getattr(self, obj, None)
        if w is None:
            return
        if isinstance(getattr(type(w), prop, None), property):      # a user control property
            setattr(w, prop, value)
            return
        items = [s.strip() for s in str(value).split(";") if s.strip()]
        if prop == "Text":
            if hasattr(w, "setPlainText"):
                w.setPlainText(str(value))
            elif hasattr(w, "setTitle") and not hasattr(w, "setText"):
                w.setTitle(str(value))
            elif hasattr(w, "setText"):
                w.setText(str(value))
        elif prop == "ToolTip":
            w.setToolTip(str(value))
        elif prop == "Items" and hasattr(w, "addItems"):
            w.clear()
            w.addItems(items)
        elif prop == "TabPages" and hasattr(w, "setTabText"):
            for i, text in enumerate(items[:w.count()]):
                w.setTabText(i, text)
        elif prop == "Columns":
            if hasattr(w, "setHorizontalHeaderLabels"):
                w.setHorizontalHeaderLabels(items)
            elif hasattr(w, "setHeaderLabels"):
                w.setHeaderLabels(items)

    def _loc_direction(self, rtl, mirror):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        if getattr(self, "_loc_mirrored", False) == mirror:
            return
        self._loc_mirrored = mirror
        layout_cls = globals().get("_Layout")
        hosts = []
        for name in {names!r}:
            w = getattr(self, name, None)
            host = w.parentWidget() if w is not None else None
            if host is None:
                continue
            found = False
            for cls in (layout_cls, _RadMirror):
                lay = host.findChild(cls, "", Qt.FindChildOption.FindDirectChildrenOnly) if cls else None
                if lay is None:
                    continue
                for i, (iw, spec) in enumerate(lay.items):
                    if iw is w:
                        x, y, ww, hh, rx, ry, rw, rh = spec
                        lay.items[i] = (iw, (-x - ww, y, ww, hh, 1 - rx - rw, ry, rw, rh))
                        found = True
                if found:
                    hosts.append(lay)
                    break
            if not found:
                lay = host.findChild(_RadMirror, "", Qt.FindChildOption.FindDirectChildrenOnly) or _RadMirror(host)
                g = w.geometry()
                lay.items.append((w, (-g.x() - g.width(), g.y(), g.width(), g.height(), 1, 0, 0, 0)))
                hosts.append(lay)
        for lay in dict.fromkeys(hosts):
            lay.apply()
'''


def _insert_before(lines: list[str], pred, new: list[str]) -> bool:
    for i, s in enumerate(lines):
        if pred(s):
            lines[i:i] = new
            return True
    return False


def localize_code(code: str, form, toolkit: str, usercontrol: bool = False) -> str:
    """Add the localization runtime to generated python-tk / python-qt designer code."""
    if not (is_localizable(form) or usercontrol):
        return code
    n = form.name
    loc = bool(form.props.get("Localizable"))
    embedded = {}
    if loc:
        for code_, t in resources(form).items():
            if code_ and isinstance(t, dict):
                embedded[code_] = {"RightToLeft": bool(t.get("RightToLeft")),
                                   "RightToLeftLayout": bool(t.get("RightToLeftLayout")),
                                   "strings": dict(t.get("strings") or {})}
    base = base_strings(form)
    keys = set()
    for t in embedded.values():
        keys |= set(t["strings"])
    # user control instances: a string property mapped to an inner value the user control translates
    # itself is re-applied after the user control's own language switch (the form's value wins)
    ucs = []
    try:
        from ..usercontrols import USER_CONTROLS, spec_of
        ucs = [c.name for c in form.controls if c.type in USER_CONTROLS]
        for c in form.controls:
            info = USER_CONTROLS.get(c.type)
            if info is None:
                continue
            inner = set()
            for t in (info["data"].get("resources") or {}).values():
                if isinstance(t, dict):
                    inner |= set(t.get("strings") or {})
            keys |= {key_of(c, p["name"]) for p in spec_of(info["data"])["properties"]
                     if p["type"] == "str" and p["maps"] in inner}
    except ImportError:
        pass
    default = {k: base[k] for k in sorted(keys) if k in base}
    lines = code.split("\n")
    module = ["", f"_RAD_RESOURCES_{n} = {embedded!r}",
              f"_RAD_DEFAULT_{n} = {default!r}"]
    runtime = TK_RUNTIME.rstrip("\n").split("\n")
    if toolkit == "qt":
        runtime += QT_EXTRA_RUNTIME.rstrip("\n").split("\n")
    if "def _rad_pick_language(" in code:
        runtime = []
    _insert_before(lines, lambda s: s.startswith(f"class {n}Designer"), runtime + module + ["", ""])
    if toolkit == "tk":
        for i, s in enumerate(lines):
            m = re.match(r"^(\s*)_ToolTip\(self\.(\w+), ", s)
            if m:
                lines[i] = f"{m.group(1)}self._loc_tips[{m.group(2)!r}] = " + s[len(m.group(1)):]
        _insert_before(lines, lambda s: s.startswith("        self._places = {}"), ["        self._loc_tips = {}"])
        if usercontrol:
            _insert_before(lines, lambda s: s.startswith("        self._radio = tk.StringVar("),
                           ["        self.root._rad_uc = True"])
        load = "        self.root.after(0, self._ev("
    else:
        load = "        QTimer.singleShot(0, self._ev("
    _insert_before(lines, lambda s: s.startswith(load) and f'"{n}_Load"' in s,
                   ["        self.CurrentLanguage = \"\"",
                    "        self.ApplyLanguage()          # Localizable: the user's language (RADIDE_LANG / "
                    "language.txt / system)"])
    while lines and lines[-1] == "":
        lines.pop()
    names = [c.name for c in form.visual()]
    rtl, layout = bool(form.props.get("RightToLeft")), bool(form.props.get("RightToLeftLayout"))
    methods = COMMON_METHODS.format(form=n, langs=sorted(embedded), base_rtl=rtl, base_layout=layout, ucs=ucs)
    methods += (QT_METHODS.format(names=names) if toolkit == "qt" else TK_METHODS.format())
    lines += methods.rstrip("\n").split("\n")
    lines.append("")
    return "\n".join(lines)


# ====================================================================== designer (IDE)
class LocPreview:
    """Language editing on one DesignerView: localized values are shown and recorded into the selected
    language's table (the base values stay in the form); RTL layout mirrors the design surface."""

    def __init__(self, view):
        self.view = view
        self.doc = view.doc
        self.code = ""
        self.mirrored = False
        self.rtl = False
        self._shadow: dict = {}
        self._busy = False
        view._loc_preview = self
        self.doc.controlChanged.connect(self._changed)
        self.doc.structureChanged.connect(self._structure)
        self.doc.renamed.connect(lambda old, new: rename_keys(self.doc.form, old, new))
        self.doc.display_props = self.display_props
        self.sync(force=True)

    # ------------------------------------------------------------ state
    @property
    def form(self):
        return self.doc.form

    def _capture(self) -> None:
        self._shadow = {}
        for c in self.form.controls:
            self._shadow[id(c)] = {k: c.props.get(k) for k in (*localizable_props(self.form, c),
                                                              "Left", "Top", "Width", "Height")}
        self._shadow["form"] = {k: self.form.props.get(k) for k in ("Text", *FLAGS)}
        self._form_sig = self._form_signature()

    def _form_signature(self) -> str:
        """The form's properties except its size (see _form_changed)."""
        return repr(sorted((k, v) for k, v in self.form.props.items() if k not in ("Width", "Height")))

    def sync(self, force: bool = False) -> None:
        code = language_code(self.form.props.get("Language"))
        if code and not self.form.props.get("Localizable"):
            self.form.props["Localizable"] = True
        if code:
            table(self.form, code)
        rtl, layout = flags_for(self.form, code)
        mirrored = bool(rtl and layout)
        if force or code != self.code or mirrored != self.mirrored or rtl != self.rtl:
            self.code, self.mirrored, self.rtl = code, mirrored, rtl
            self._capture()
            self.refresh()

    def _structure(self) -> None:
        if self._busy:
            return
        self._capture()
        self.refresh()

    # ------------------------------------------------------------ effective values
    def localized(self, ctrl) -> dict:
        """ctrl's props with the selected language's values (and the mirror) applied."""
        props = dict(ctrl.props if ctrl is not None else self.form.props)
        if self.code:
            strings = table(self.form, self.code)["strings"]
            for prop in localizable_props(self.form, ctrl):
                k = key_of(ctrl, prop)
                if k in strings:
                    props[prop] = strings[k]
            if ctrl is None:
                rtl, layout = flags_for(self.form, self.code)
                props["RightToLeft"], props["RightToLeftLayout"] = rtl, layout
        if ctrl is not None and self.mirrored:
            props = mirror_props(self.form, ctrl, props)
        return props

    def display_props(self, ctrl, props) -> dict:
        """What the Properties window shows (hook of FormDocument used by properties.py)."""
        if not self.code and not self.mirrored:
            return props
        out = self.localized(ctrl)
        out.pop("_RTLMirror", None)
        return out

    def design_props(self, ctrl) -> dict:
        if ctrl is None:
            return self.localized(None) if self.code else self.form.props
        return self.localized(ctrl) if self.mirrored else ctrl.props

    def form_props(self) -> dict:
        return self.localized(None) if self.code else self.form.props

    # ------------------------------------------------------------ preview
    def apply(self, ctrl) -> None:
        from ..model import Control
        from ..preview import apply_props
        w = self.view.previews.get(id(ctrl))
        if w is None:
            return
        bp = getattr(self.view, "_blend_preview", None)
        if bp is not None and not (self.code or self.mirrored):
            # no language shown: the Blend preview (visual state / storyboard time) decides what the
            # control shows - the raw values here undid a scrubbed / recorded keyframe position
            bp.apply(ctrl)
            from PyQt6.QtCore import Qt
            w.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.rtl else Qt.LayoutDirection.LeftToRight)
            return
        try:
            apply_props(w, Control(ctrl.type, self.localized(ctrl), ctrl.states)
                        if (self.code or self.mirrored) else ctrl)
        except (TypeError, ValueError, KeyError):
            apply_props(w, ctrl)
        from PyQt6.QtCore import Qt
        w.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.rtl else Qt.LayoutDirection.LeftToRight)

    def refresh(self) -> None:
        for c in self.form.visual():
            self.apply(c)
        try:
            self.view.layout_form()
            self.view.frame.update()
            self.view.overlay.update()
        except (AttributeError, RuntimeError):
            pass

    # ------------------------------------------------------------ recording
    def _changed(self, ctrl) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            if ctrl is None:
                self._form_changed()
            else:
                self._control_changed(ctrl)
        finally:
            self._busy = False

    def _form_changed(self) -> None:
        f = self.form
        before = (self.code, self.mirrored, self.rtl)
        shadow = self._shadow.get("form", {})
        if self.code:
            t = table(f, self.code)
            changed = False
            if f.props.get("Text") != shadow.get("Text"):
                t["strings"]["$this.Text"] = f.props.get("Text", "")
                f.props["Text"] = shadow.get("Text", "")
                changed = True
            for k in FLAGS:
                if k in f.props and f.props.get(k) != shadow.get(k):
                    t[k] = bool(f.props.get(k))
                    if shadow.get(k) is None:
                        f.props.pop(k, None)
                    else:
                        f.props[k] = shadow.get(k)
                    changed = True
            if changed:
                self.doc.set_modified()
        self.sync()
        self._shadow["form"] = {k: f.props.get(k) for k in ("Text", *FLAGS)}
        # only the form's size changed (a resize drag in the designer) and nothing is mirrored: the
        # designer already laid the frame out - re-applying every control and rebuilding the whole
        # Properties grid here made each resize step cost 100-900 ms
        sig = self._form_signature()
        last, self._form_sig = getattr(self, "_form_sig", None), sig
        if sig == last and not self.mirrored and before == (self.code, self.mirrored, self.rtl):
            return
        if before == (self.code, self.mirrored, self.rtl):
            self.refresh()
        win = self.view.window()
        if hasattr(win, "properties"):
            try:
                win.properties.refresh()
            except (AttributeError, RuntimeError):
                pass

    def _control_changed(self, ctrl) -> None:
        shadow = self._shadow.get(id(ctrl))
        if shadow is None:
            self._shadow[id(ctrl)] = {k: ctrl.props.get(k) for k in (*localizable_props(self.form, ctrl),
                                                                      "Left", "Top", "Width", "Height")}
            self.apply(ctrl)
            return
        changed = False
        if self.code:
            strings = table(self.form, self.code)["strings"]
            for prop in localizable_props(self.form, ctrl):
                if prop in ctrl.props and ctrl.props.get(prop) != shadow.get(prop):
                    strings[key_of(ctrl, prop)] = ctrl.props[prop]
                    ctrl.props[prop] = shadow.get(prop)
                    changed = True
        if self.mirrored and ctrl.props.get("Left") != shadow.get("Left"):
            # the designer works in the mirrored picture: Left there = from the right edge
            from ..layout import client_size
            parent = self.form.find(ctrl.parent) if ctrl.parent else None
            cw, _ch = client_size(self.form, parent)
            ctrl.props["Left"] = int(cw) - int(ctrl.props["Left"]) - int(ctrl.props["Width"])
        for k in ("Left", "Top", "Width", "Height"):
            shadow[k] = ctrl.props.get(k)
        if changed:
            self.doc.set_modified()
        self.apply(ctrl)


def attach(view) -> LocPreview:
    lp = getattr(view, "_loc_preview", None)
    if lp is None:
        lp = LocPreview(view)
    return lp


# ====================================================================== Localization editor dialog
def edit_strings(win, view) -> None:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                                 QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                                 QTableWidgetItem, QVBoxLayout)
    doc = view.doc
    form = doc.form
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Localization - {form.name}")
    dlg.resize(820, 520)
    lay = QVBoxLayout(dlg)
    info = QLabel("Every localizable value of the form; type the translation of each language. "
                  "Empty cell = the default value is used. RTL = RightToLeft, Mirror = RightToLeftLayout.")
    info.setWordWrap(True)
    lay.addWidget(info)
    top = QHBoxLayout()
    pick = QComboBox()
    pick.addItems([language_label(c) for c, _ in LANGUAGES])
    add_btn = QPushButton("Add Language")
    rem_btn = QPushButton("Remove Language")
    imp_btn = QPushButton("Import .resx.json...")
    top.addWidget(QLabel("Language:"))
    top.addWidget(pick)
    top.addWidget(add_btn)
    top.addWidget(rem_btn)
    top.addStretch(1)
    top.addWidget(imp_btn)
    lay.addLayout(top)
    flags_row = QHBoxLayout()
    lay.addLayout(flags_row)
    grid = QTableWidget()
    lay.addWidget(grid, 1)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    lay.addWidget(bb)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    work = json.loads(json.dumps(resources(form)))
    flag_boxes: dict = {}

    def langs():
        return [c for c in work if c]

    def fill():
        while flags_row.count():
            it = flags_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        flag_boxes.clear()
        for c in langs():
            t = work[c]
            a, b = QCheckBox(f"{c}: RTL"), QCheckBox("Mirror")
            a.setChecked(bool(t.get("RightToLeft")))
            b.setChecked(bool(t.get("RightToLeftLayout")))
            flags_row.addWidget(a)
            flags_row.addWidget(b)
            flag_boxes[c] = (a, b)
        flags_row.addStretch(1)
        base = base_strings(form)
        cols = ["Key", "Default"] + [language_label(c) for c in langs()]
        grid.clear()
        grid.setColumnCount(len(cols))
        grid.setHorizontalHeaderLabels(cols)
        grid.setRowCount(len(base))
        for r, (k, v) in enumerate(base.items()):
            for col, text in enumerate([k, str(v)]):
                it = QTableWidgetItem(text)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                grid.setItem(r, col, it)
            for j, c in enumerate(langs()):
                grid.setItem(r, 2 + j, QTableWidgetItem(str((work[c].get("strings") or {}).get(k, ""))))
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def collect():
        for j, c in enumerate(langs()):
            strings = {}
            for r in range(grid.rowCount()):
                k = grid.item(r, 0).text()
                it = grid.item(r, 2 + j)
                if it is not None and it.text() != "":
                    strings[k] = it.text()
            work[c]["strings"] = strings
            a, b = flag_boxes.get(c, (None, None))
            if a is not None:
                work[c]["RightToLeft"], work[c]["RightToLeftLayout"] = a.isChecked(), b.isChecked()

    def add_lang():
        collect()
        c = language_code(pick.currentText())
        if c and c not in work:
            rtl = c in RTL_LANGUAGES
            work[c] = {"name": dict(LANGUAGES).get(c, c), "RightToLeft": rtl, "RightToLeftLayout": rtl,
                       "strings": {}}
        fill()

    def remove_lang():
        collect()
        work.pop(language_code(pick.currentText()), None)
        fill()

    def import_file():
        path, _ = QFileDialog.getOpenFileName(dlg, "Import resources", str(doc.path.parent),
                                              "Resources (*.resx.json *.json)")
        if not path:
            return
        collect()
        from ..model import Form
        tmp = Form.from_dict({"props": dict(form.props), "controls": [], "resources": work})
        import_resx(tmp, Path(path))
        work.clear()
        work.update(tmp.extra.get("resources") or {})
        fill()

    add_btn.clicked.connect(add_lang)
    rem_btn.clicked.connect(remove_lang)
    imp_btn.clicked.connect(import_file)
    fill()
    if dlg.exec():
        collect()
        doc.checkpoint()
        form.extra["resources"] = work
        if langs():
            form.props["Localizable"] = True
        if form.props.get("Language") and language_code(form.props["Language"]) not in work:
            form.props["Language"] = DEFAULT
        doc.set_modified()
        doc.controlChanged.emit(None)
        lp = attach(view)
        lp.sync(force=True)


# ====================================================================== install
def install(win) -> None:
    from PyQt6.QtGui import QAction

    def designers():
        for st in win.project_states() if hasattr(win, "project_states") else []:
            yield from st.get("designers", {}).values()
        yield from getattr(win, "designers", {}).values()

    def hook_open(*_a):
        for v in list(designers()):
            if getattr(v, "_loc_preview", None) is None:
                try:
                    attach(v)
                except Exception as e:  # noqa: BLE001 - never break the designer
                    win.log(f"[localization] {e}")

    orig_open = win.open_designer

    def open_designer(name, *a, **kw):
        r = orig_open(name, *a, **kw)
        hook_open()
        return r
    win.open_designer = open_designer

    orig_save = win._save_form

    def save_form(name, *a, **kw):
        r = orig_save(name, *a, **kw)
        try:
            doc = win.docs.get(name)
            if doc is not None and (doc.form.props.get("Localizable") or
                                    list(doc.path.parent.glob(f"{name}.*.resx.json"))):
                write_resx(doc.form, doc.path.parent)
        except Exception as e:  # noqa: BLE001
            win.log(f"[localization] could not write the resource files: {e}")
        return r
    win._save_form = save_form

    def open_editor():
        v = win._current_designer()
        if v is None:
            win.statusBar().showMessage("Open a form designer first.", 4000)
            return
        attach(v)
        edit_strings(win, v)

    act = QAction("&Localization Strings...", win)
    act.setStatusTip("Translate the Text / ToolTip / Items of the form into other languages (Localizable)")
    act.triggered.connect(open_editor)
    win.a_localization = act
    menu = getattr(win, "format_menu", None)
    if menu is not None:
        menu.addSeparator()
        menu.addAction(act)

    def designer_menu(form_name, m, c, _orig=win._designer_menu):
        _orig(form_name, m, c)
        if c is None:
            m.addSeparator()
            m.addAction(act)
    win._designer_menu = designer_menu
