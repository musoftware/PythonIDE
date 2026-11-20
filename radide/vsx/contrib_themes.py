"""VS Code colour themes (``contributes.themes``) -> Monaco themes + IDE chrome themes.

A VS Code theme file is JSON(C) with
    "type" / uiTheme   dark | light | hc (hc-black) | hcLight (hc-light)
    "include"          another theme file merged underneath (relative path, recursive)
    "colors"           workbench colours (editor.background, sideBar.background, statusBar.* ...)
    "tokenColors"      TextMate rules [{scope, settings: {foreground, fontStyle}}] - or a path to a .tmTheme
    "semanticTokenColors"  {"selector": colour | {foreground, fontStyle, bold, italic}}

``load_theme(ext, contribution)`` returns a ThemeSpec with
    monaco      {"base", "inherit", "rules", "colors"}         - for monaco.editor.defineTheme
    raw         {"name", "settings": [...]}                    - for vscode-textmate (Registry.setTheme)
    tokens      radide.theme token dict (window, base, tab ... code, chrome) - the whole IDE chrome
``register_all()`` adds every enabled extension's themes to radide.theme (Options > Color theme).
No Qt import at module level."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contrib_common import (enabled_extensions, ext_file, is_dark_color, mix, monaco_color, parse_color,
                             read_jsonc, readable_on, solid)

UI_BASE = {"vs": "vs", "vs-dark": "vs-dark", "hc-black": "hc-black", "hc-light": "hc-light",
           "dark": "vs-dark", "light": "vs", "hc": "hc-black", "hcLight": "hc-light", "hcDark": "hc-black"}


# ============================================================================ default token colours
def _rules(spec) -> list:
    out = []
    for scopes, fg, *style in spec:
        s = {"foreground": fg} if fg else {}
        if style:
            s["fontStyle"] = style[0]
        out.append({"scope": [x.strip() for x in scopes.split(",")], "settings": s})
    return out


# VS Code's Dark+ / Light+ (MIT) - used for TextMate grammars under the built-in IDE themes
DARK_PLUS = _rules([
    ("comment, punctuation.definition.comment", "#6A9955"),
    ("string, meta.embedded.assembly", "#CE9178"),
    ("string.regexp", "#D16969"),
    ("constant.character.escape, constant.character", "#D7BA7D"),
    ("constant.numeric, keyword.other.unit, meta.preprocessor.numeric", "#B5CEA8"),
    ("constant.language, constant.other.color", "#569CD6"),
    ("keyword, storage, storage.type, storage.modifier, keyword.operator.new, keyword.operator.expression, "
     "keyword.operator.cast, keyword.operator.sizeof, keyword.operator.logical.python, keyword.operator.wordlike",
     "#569CD6"),
    ("keyword.control, keyword.other.using, keyword.other.operator, entity.name.operator, "
     "keyword.control.directive, keyword.control.import, keyword.control.from", "#C586C0"),
    ("keyword.operator", "#D4D4D4"),
    ("entity.name.function, support.function, support.constant.handlebars, meta.function-call, "
     "entity.name.function.decorator, meta.decorator", "#DCDCAA"),
    ("entity.name.type, entity.name.class, entity.name.namespace, entity.other.inherited-class, support.type, "
     "support.class, entity.name.scope-resolution, storage.type.cs, storage.type.java, entity.name.type.module",
     "#4EC9B0"),
    ("variable, meta.definition.variable.name, support.variable, entity.name.variable, variable.parameter, "
     "variable.other.readwrite, meta.object-literal.key, support.type.property-name, entity.other.attribute-name",
     "#9CDCFE"),
    ("variable.language, variable.language.this, variable.language.self", "#569CD6"),
    ("variable.other.constant, variable.other.enummember", "#4FC1FF"),
    ("entity.name.tag, meta.preprocessor, entity.name.function.preprocessor, punctuation.definition.template-expression",
     "#569CD6"),
    ("punctuation.definition.tag", "#808080"),
    ("support.constant.property-value, support.constant.font-name, support.constant.media-type, "
     "meta.preprocessor.string", "#CE9178"),
    ("entity.other.attribute-name.class.css, entity.other.attribute-name.id.css", "#D7BA7D"),
    ("entity.name.label", "#C8C8C8"),
    ("markup.heading", "#569CD6", "bold"),
    ("markup.bold", None, "bold"),
    ("markup.italic", None, "italic"),
    ("markup.underline", None, "underline"),
    ("markup.strikethrough", None, "strikethrough"),
    ("markup.inline.raw", "#CE9178"),
    ("markup.inserted", "#B5CEA8"),
    ("markup.deleted", "#CE9178"),
    ("markup.changed", "#569CD6"),
    ("markup.quote", "#6A9955"),
    ("invalid", "#F44747"),
])
LIGHT_PLUS = _rules([
    ("comment, punctuation.definition.comment", "#008000"),
    ("string, meta.embedded.assembly", "#A31515"),
    ("string.regexp", "#811F3F"),
    ("constant.character.escape, constant.character", "#EE0000"),
    ("constant.numeric, keyword.other.unit, meta.preprocessor.numeric", "#098658"),
    ("constant.language, constant.other.color", "#0000FF"),
    ("keyword, storage, storage.type, storage.modifier, keyword.operator.new, keyword.operator.expression, "
     "keyword.operator.cast, keyword.operator.sizeof, keyword.operator.logical.python, keyword.operator.wordlike",
     "#0000FF"),
    ("keyword.control, keyword.other.using, keyword.other.operator, entity.name.operator, "
     "keyword.control.directive, keyword.control.import, keyword.control.from", "#AF00DB"),
    ("keyword.operator", "#000000"),
    ("entity.name.function, support.function, support.constant.handlebars, meta.function-call, "
     "entity.name.function.decorator, meta.decorator", "#795E26"),
    ("entity.name.type, entity.name.class, entity.name.namespace, entity.other.inherited-class, support.type, "
     "support.class, entity.name.scope-resolution, storage.type.cs, storage.type.java, entity.name.type.module",
     "#267F99"),
    ("variable, meta.definition.variable.name, support.variable, entity.name.variable, variable.parameter, "
     "variable.other.readwrite, meta.object-literal.key", "#001080"),
    ("support.type.property-name", "#0451A5"),
    ("entity.other.attribute-name", "#E50000"),
    ("variable.language, variable.language.this, variable.language.self", "#0000FF"),
    ("variable.other.constant, variable.other.enummember", "#0070C1"),
    ("entity.name.tag, punctuation.definition.tag", "#800000"),
    ("meta.preprocessor, entity.name.function.preprocessor, punctuation.definition.template-expression", "#0000FF"),
    ("support.constant.property-value, support.constant.font-name, support.constant.media-type", "#0451A5"),
    ("meta.preprocessor.string", "#A31515"),
    ("entity.name.label", "#000000"),
    ("markup.heading", "#800000", "bold"),
    ("markup.bold", None, "bold"),
    ("markup.italic", None, "italic"),
    ("markup.underline", None, "underline"),
    ("markup.strikethrough", None, "strikethrough"),
    ("markup.inline.raw", "#800000"),
    ("markup.inserted", "#098658"),
    ("markup.deleted", "#A31515"),
    ("markup.changed", "#0451A5"),
    ("markup.quote", "#0451A5"),
    ("invalid", "#CD3131"),
])
HC_BLACK = [dict(r) for r in DARK_PLUS]
HC_BLACK[0] = {"scope": ["comment", "punctuation.definition.comment"], "settings": {"foreground": "#7CA668"}}

BUILTIN_RAW = {"vs": ("#000000", "#FFFFFF", LIGHT_PLUS), "vs-dark": ("#D4D4D4", "#1E1E1E", DARK_PLUS),
               "hc-black": ("#FFFFFF", "#000000", HC_BLACK), "hc-light": ("#292929", "#FFFFFF", LIGHT_PLUS)}


def builtin_raw_theme(monaco_base: str) -> dict:
    """The TextMate theme used for grammars while a built-in IDE theme (Monaco vs / vs-dark / hc-*) is active."""
    fg, bg, rules = BUILTIN_RAW.get(monaco_base, BUILTIN_RAW["vs"])
    return {"name": monaco_base, "settings": [{"settings": {"foreground": fg, "background": bg}}] + rules}


# ============================================================================ theme files
@dataclass
class ThemeSpec:
    ext_id: str
    label: str                     # as shown in Options (unique)
    theme_id: str                  # "<ext id>/<label in the manifest>"
    base: str                      # Monaco base theme: vs | vs-dark | hc-black | hc-light
    dark: bool
    colors: dict = field(default_factory=dict)         # workbench colours (as in the file)
    token_colors: list = field(default_factory=list)   # normalised [{scope: [..], settings: {...}}]
    semantic: dict = field(default_factory=dict)
    semantic_highlighting: bool = False
    path: Path | None = None

    # ---- Monaco
    @property
    def editor_bg(self) -> str:
        default = "#1E1E1E" if self.dark else "#FFFFFF"
        if self.base == "hc-black":
            default = "#000000"
        return solid(self.colors.get("editor.background"), default) or default

    @property
    def editor_fg(self) -> str:
        default = "#D4D4D4" if self.dark else "#000000"
        for k in ("editor.foreground", "foreground"):
            c = solid(self.colors.get(k), self.editor_bg)
            if c:
                return c
        g = _global_settings(self.token_colors)
        return solid(g.get("foreground"), self.editor_bg) or default

    def raw(self) -> dict:
        """The vscode-textmate theme (IRawTheme)."""
        return {"name": self.theme_id, "settings": [{"settings": {"foreground": self.editor_fg,
                                                                  "background": self.editor_bg}}] +
                [r for r in self.token_colors if r.get("scope")]}

    def monaco(self) -> dict:
        """monaco.editor.defineTheme data: TextMate rules for Monarch tokens + workbench colours."""
        bg = self.editor_bg
        rules = [{"token": "", "foreground": self.editor_fg[1:], "background": bg[1:]}]
        direct = set()
        for r in self.token_colors:
            st = r.get("settings") or {}
            for sel in r.get("scope") or []:
                if " " in sel or sel.startswith("-") or not sel:
                    continue
                rule = _monaco_rule(sel, st, bg)
                if rule:
                    rules.append(rule)
                    direct.add(sel)
        matcher = ScopeMatcher(self.token_colors)
        for token, scopes in MONARCH_ALIASES:
            if token in direct:
                continue
            for sc in scopes:
                st = matcher.style(sc)
                if st:
                    rule = _monaco_rule(token, st, bg)
                    if rule:
                        rules.append(rule)
                    break
        for sel, val in (self.semantic or {}).items():          # LSP semantic tokens (Monaco matches by name)
            st = {"foreground": val} if isinstance(val, str) else dict(val) if isinstance(val, dict) else {}
            if isinstance(val, dict):
                styles = [s for s in ("italic", "bold", "underline", "strikethrough") if val.get(s)]
                if styles and "fontStyle" not in st:
                    st["fontStyle"] = " ".join(styles)
            rule = _monaco_rule(sel.replace(":", "."), st, bg)
            if rule:
                rules.append(rule)
        colors = {}
        for k, v in (self.colors or {}).items():
            c = monaco_color(v)
            if c:
                colors[k] = c
        colors.setdefault("editor.background", bg)
        colors.setdefault("editor.foreground", self.editor_fg)
        return {"base": self.base, "inherit": True, "rules": rules, "colors": colors,
                "semanticHighlighting": bool(self.semantic_highlighting)}

    def js_spec(self) -> dict:
        """Everything radide/web/vsx/vsx-contrib.js needs to show this theme in Monaco."""
        return {"id": self.theme_id, "label": self.label, "base": self.base, "monaco": self.monaco(),
                "raw": self.raw(), "background": self.editor_bg}

    # ---- IDE chrome
    def tokens(self) -> dict:
        return chrome_tokens(self)


# Monarch token names (Monaco's built-in languages) -> TextMate scopes to take their style from
MONARCH_ALIASES = [
    ("number", ["constant.numeric"]), ("regexp", ["string.regexp"]),
    ("type", ["entity.name.type", "support.type", "storage.type"]),
    ("type.identifier", ["entity.name.type", "support.class", "entity.name.class"]),
    ("identifier", ["variable.other", "variable"]),
    ("delimiter", ["punctuation", "meta.brace"]), ("delimiter.html", ["punctuation.definition.tag"]),
    ("delimiter.xml", ["punctuation.definition.tag"]),
    ("operator", ["keyword.operator"]), ("operators", ["keyword.operator"]),
    ("tag", ["entity.name.tag"]), ("metatag", ["entity.name.tag", "meta.tag"]),
    ("attribute.name", ["entity.other.attribute-name"]), ("attribute.value", ["string.quoted", "string"]),
    ("annotation", ["meta.decorator", "entity.name.function.decorator", "storage.type.annotation"]),
    ("predefined", ["support.function", "entity.name.function"]),
    ("variable.predefined", ["variable.language", "support.variable"]),
    ("string.key.json", ["support.type.property-name"]), ("string.value.json", ["string"]),
    ("keyword.json", ["constant.language"]), ("string.escape", ["constant.character.escape"]),
    ("string.link", ["markup.underline.link"]), ("keyword.flow", ["keyword.control"]),
]


def _monaco_rule(token: str, st: dict, bg: str) -> dict | None:
    rule = {"token": token}
    fg = solid(st.get("foreground"), bg) if st.get("foreground") else None
    if fg:
        rule["foreground"] = fg[1:]
    b = solid(st.get("background"), bg) if st.get("background") else None
    if b:
        rule["background"] = b[1:]
    fs = st.get("fontStyle")
    if isinstance(fs, str):
        rule["fontStyle"] = " ".join(w for w in fs.split() if w in ("italic", "bold", "underline", "strikethrough"))
    return rule if len(rule) > 1 else None


def _global_settings(token_colors: list) -> dict:
    for r in token_colors:
        if not r.get("scope") and isinstance(r.get("settings"), dict):
            return r["settings"]
    return {}


def _norm_scope(scope) -> list[str]:
    if isinstance(scope, str):
        return [s.strip() for s in scope.split(",") if s.strip()]
    if isinstance(scope, list):
        out = []
        for s in scope:
            if isinstance(s, str):
                out += [x.strip() for x in s.split(",") if x.strip()]
        return out
    return []


def normalize_token_colors(items) -> list:
    out = []
    for r in items or []:
        if not isinstance(r, dict):
            continue
        st = r.get("settings")
        if not isinstance(st, dict):
            continue
        out.append({"scope": _norm_scope(r.get("scope")), "settings": {k: v for k, v in st.items()
                                                                      if isinstance(v, str)}})
    return out


class ScopeMatcher:
    """Minimal TextMate theme matching for one scope (no parent selectors): the most specific simple
    selector that is a dotted prefix of the scope wins; later rules win ties."""

    def __init__(self, token_colors: list):
        self.rules = []
        for i, r in enumerate(token_colors):
            for sel in r.get("scope") or []:
                if sel and " " not in sel and not sel.startswith("-"):
                    self.rules.append((sel, i, r.get("settings") or {}))

    def style(self, scope: str, need: str = "foreground") -> dict | None:
        best = None
        for sel, i, st in self.rules:
            if need and not st.get(need):
                continue
            if scope == sel or scope.startswith(sel + "."):
                key = (sel.count(".") + 1, i)
                if best is None or key > best[0]:
                    best = (key, st)
        return best[1] if best else None

    def fg(self, *scopes, default: str | None = None, bg: str = "#000000") -> str | None:
        for sc in scopes:
            st = self.style(sc)
            if st:
                c = solid(st.get("foreground"), bg)
                if c:
                    return c
        return default


def _read_theme(path: Path, depth: int = 0) -> dict:
    """A theme file with its "include" chain merged (the including file wins)."""
    data = read_jsonc(path, None)
    if not isinstance(data, dict) or depth > 8:
        return {}
    if "settings" in data and "tokenColors" not in data and isinstance(data["settings"], list):   # .tmTheme
        data = {"tokenColors": data["settings"], "name": data.get("name")}
    out = {"colors": {}, "tokenColors": [], "semanticTokenColors": {}}
    inc = data.get("include")
    if isinstance(inc, str):
        base = _read_theme((path.parent / inc).resolve(), depth + 1)
        out["colors"].update(base.get("colors") or {})
        out["tokenColors"] += base.get("tokenColors") or []
        out["semanticTokenColors"].update(base.get("semanticTokenColors") or {})
        for k in ("type", "semanticHighlighting"):
            if k in base:
                out[k] = base[k]
    if isinstance(data.get("colors"), dict):
        out["colors"].update(data["colors"])
    tc = data.get("tokenColors")
    if isinstance(tc, str):                    # a .tmTheme / json file with the rules
        sub = read_jsonc((path.parent / tc).resolve(), {})
        tc = sub.get("settings") or sub.get("tokenColors") if isinstance(sub, dict) else None
    if isinstance(tc, list):
        out["tokenColors"] += tc
    if isinstance(data.get("semanticTokenColors"), dict):
        out["semanticTokenColors"].update(data["semanticTokenColors"])
    for k in ("type", "semanticHighlighting", "name"):
        if k in data:
            out[k] = data[k]
    return out


def load_theme(ext, contribution: dict, label: str | None = None) -> ThemeSpec | None:
    rel = contribution.get("path") if isinstance(contribution, dict) else None
    path = ext_file(ext, rel) if rel else None
    if path is None:
        return None
    data = _read_theme(path)
    if not data:
        return None
    ui = str(contribution.get("uiTheme") or data.get("type") or "vs-dark")
    base = UI_BASE.get(ui, "vs-dark")
    name = str(contribution.get("label") or contribution.get("id") or data.get("name") or path.stem)
    tc = normalize_token_colors(data.get("tokenColors"))
    spec = ThemeSpec(ext_id=ext.id, label=label or name, theme_id=f"{ext.id}/{contribution.get('id') or name}",
                     base=base, dark=base in ("vs-dark", "hc-black"), colors=dict(data.get("colors") or {}),
                     token_colors=tc, semantic=dict(data.get("semanticTokenColors") or {}),
                     semantic_highlighting=bool(data.get("semanticHighlighting")), path=path)
    return spec


# ============================================================================ IDE chrome
def chrome_tokens(spec: ThemeSpec) -> dict:
    """radide.theme tokens derived from the workbench colours (VS Code defaults where a colour is missing)."""
    dark = spec.dark
    C = spec.colors or {}
    ed_bg = spec.editor_bg
    ed_fg = spec.editor_fg

    def g(*keys, default=None, on=None):
        for k in keys:
            c = solid(C.get(k), on or ed_bg) if k in C else None
            if c:
                return c
        return default

    fg = g("foreground", default=ed_fg)
    side = g("sideBar.background", default=mix(ed_bg, "#000000" if dark else "#7F7F7F", 0.12 if dark else 0.10))
    side_fg = g("sideBar.foreground", default=fg)
    act = g("activityBar.background", default=mix(ed_bg, "#FFFFFF", 0.10) if dark else "#2C2C2C")
    act_fg = g("activityBar.foreground", default=readable_on(act))
    title = g("titleBar.activeBackground", default=act)
    title_fg = g("titleBar.activeForeground", default=readable_on(title))
    # VS Code draws only a few accent borders (Dracula: purple panel border); the IDE has a border around every
    # dock / tab, so a neutral one is derived unless the theme is high contrast
    border = g("contrastBorder", default=mix(side, fg, 0.16)) if spec.base.startswith("hc") else mix(side, fg, 0.16)
    sel = g("list.activeSelectionBackground", "editor.selectionBackground", "selection.background",
            default="#094771" if dark else "#0060C0", on=side)
    sel_fg = g("list.activeSelectionForeground", default=readable_on(sel), on=side)
    focus = g("focusBorder", "button.background", default=sel)
    btn = g("button.secondaryBackground", "input.background", "dropdown.background",
            default=mix(side, fg, 0.12))
    btn_fg = g("button.secondaryForeground", "input.foreground", "dropdown.foreground", default=fg, on=btn)
    accent = g("button.background", default=focus)
    accent_fg = g("button.foreground", default=readable_on(accent), on=accent)
    menu = g("menu.background", "dropdown.background", "editorWidget.background", default=side)
    menu_fg = g("menu.foreground", "dropdown.foreground", default=fg, on=menu)
    menu_sel = g("menu.selectionBackground", "list.activeSelectionBackground", default=sel, on=menu)
    menu_sel_fg = g("menu.selectionForeground", "list.activeSelectionForeground", default=readable_on(menu_sel),
                    on=menu)
    tab_bar = g("editorGroupHeader.tabsBackground", default=mix(ed_bg, side, 0.5))
    tab = g("tab.inactiveBackground", default=tab_bar, on=tab_bar)
    tab_fg = g("tab.inactiveForeground", default=mix(fg, tab, 0.35), on=tab)
    tab_sel = g("tab.activeBackground", default=ed_bg, on=tab_bar)
    tab_sel_fg = g("tab.activeForeground", default=fg, on=tab_sel)
    tab_hover = g("tab.hoverBackground", default=mix(tab, tab_sel, 0.5), on=tab)
    status = g("statusBar.background", default="#007ACC")
    status_fg = g("statusBar.foreground", default=readable_on(status), on=status)
    header = g("sideBarSectionHeader.background", "editorGroupHeader.tabsBackground", default=mix(side, fg, 0.06),
               on=side)
    header_fg = g("sideBarSectionHeader.foreground", "sideBarTitle.foreground", default=side_fg, on=header)
    hover = g("editorHoverWidget.background", "editorWidget.background", default=menu)
    hover_fg = g("editorHoverWidget.foreground", "editorWidget.foreground", default=fg, on=hover)
    muted = g("descriptionForeground", default=mix(fg, side, 0.35), on=side)
    link = g("textLink.foreground", "textLink.activeForeground", default="#3794FF" if dark else "#006AB1")
    error = g("errorForeground", "editorError.foreground", default="#F48771" if dark else "#A1260D")
    warn = g("editorWarning.foreground", "list.warningForeground", default="#CCA700" if dark else "#BF8803")
    success = g("gitDecoration.addedResourceForeground", "terminal.ansiGreen", "testing.iconPassed",
                default="#73C991" if dark else "#587C0C")
    disabled = g("disabledForeground", default=mix(fg, side, 0.55), on=side)
    placeholder = g("input.placeholderForeground", default=mix(fg, side, 0.45), on=side)
    alt = g("list.hoverBackground", default=mix(side, fg, 0.05), on=side)
    alt = mix(side, alt, 0.6)
    panel = g("panel.background", default=ed_bg)

    matcher = ScopeMatcher(spec.token_colors)
    base_code = {"keyword": "#569CD6", "builtin": "#4EC9B0", "comment": "#6A9955", "string": "#CE9178",
                 "number": "#B5CEA8", "decorator": "#DCDCAA", "defname": "#DCDCAA", "operator": "#D4D4D4"} if dark \
        else {"keyword": "#0000FF", "builtin": "#2B91AF", "comment": "#008000", "string": "#A31515",
              "number": "#098658", "decorator": "#795E26", "defname": "#795E26", "operator": "#000000"}
    code = {
        "keyword": matcher.fg("keyword.control", "keyword", "storage.type", default=base_code["keyword"], bg=ed_bg),
        "builtin": matcher.fg("support.type", "entity.name.type", "support.class", "support.function",
                              default=base_code["builtin"], bg=ed_bg),
        "comment": matcher.fg("comment", default=base_code["comment"], bg=ed_bg),
        "string": matcher.fg("string.quoted", "string", default=base_code["string"], bg=ed_bg),
        "number": matcher.fg("constant.numeric", "constant", default=base_code["number"], bg=ed_bg),
        "decorator": matcher.fg("entity.name.function.decorator", "meta.decorator", "entity.name.function",
                                default=base_code["decorator"], bg=ed_bg),
        "defname": matcher.fg("entity.name.function", default=base_code["defname"], bg=ed_bg),
        "operator": matcher.fg("keyword.operator", default=ed_fg, bg=ed_bg),
    }
    gutter = g("editorGutter.background", default=ed_bg)
    chrome = {
        "margin": gutter, "margin_bp": mix(gutter, fg, 0.06),
        "line_number": g("editorLineNumber.foreground", default=mix(ed_fg, ed_bg, 0.45)),
        "breakpoint_line": mix(ed_bg, "#E51400", 0.25),
        "current_stmt": g("editor.stackFrameHighlightBackground", default=mix(ed_bg, "#FFCC00", 0.25)),
        "caret_line": g("editor.lineHighlightBackground", default=mix(ed_bg, fg, 0.06)),
    }
    banner = mix(side, warn, 0.22)
    t = dict(
        dark=dark, monaco=spec.base, code=code, chrome=chrome,
        window=side, base=side, alt_base=alt, text=fg, muted=muted,
        button=btn, button_text=btn_fg, border=border, light=mix(side, "#FFFFFF", 0.25), mid=mix(side, fg, 0.25),
        dark_c=mix(side, "#000000", 0.4), shadow="#000000",
        highlight=sel, highlight_text=sel_fg, link=link, link_visited=mix(link, "#C586C0", 0.5),
        accent=accent, accent_text=accent_fg,
        title1=header, title2=header, title_text=header_fg,
        toolbar1=title, toolbar2=act, toolbar_border=border, bar_text=title_fg if parse_color(title_fg) else act_fg,
        menu=menu, menu_text=menu_fg, menu_sel=menu_sel, menu_sel_text=menu_sel_fg,
        menu_border=g("menu.border", "widget.border", default=border, on=menu),
        tab=tab, tab_text=tab_fg, tab_sel=tab_sel, tab_sel_text=tab_sel_fg, tab_hover=tab_hover,
        status=status, status_text=status_fg, header=header, header_text=header_fg,
        tooltip=hover, tooltip_text=hover_fg, calltip=hover, calltip_text=hover_fg,
        note=warn, banner=banner, banner_text=readable_on(banner, mix(warn, "#FFFFFF", 0.6), mix(warn, "#000000", 0.6)),
        banner_border=mix(side, warn, 0.5),
        success=success, error=error, info_back=alt,
        designer_back=ed_bg, category_back=header, stage=mix(ed_bg, "#000000", 0.35),
        heading=code["keyword"], disabled=disabled, placeholder=placeholder,
    )
    # extra (non-standard) tokens other features may use: the VS Code workbench parts
    t.update(activity=act, activity_text=act_fg, sidebar=side, sidebar_text=side_fg, editor_back=ed_bg,
             editor_text=ed_fg, panel=panel)
    t["vsx_theme"] = spec.theme_id
    t["_vsx"] = spec.ext_id
    t["_extension"] = f"vsx:{spec.ext_id}"
    if is_dark_color(side) != dark:          # a "light" theme with a dark sidebar etc.: trust the colours
        t["dark"] = is_dark_color(side)
    return t


# ============================================================================ registration
_registered: dict[str, ThemeSpec] = {}          # IDE theme name -> spec


def collect(extensions=None) -> list[ThemeSpec]:
    """Every theme of the enabled extensions, with unique labels."""
    from .. import theme as T
    exts = enabled_extensions() if extensions is None else extensions
    out: list[ThemeSpec] = []
    taken = set(T.BUILTIN_THEMES)
    for ext in exts:
        for c in ext.contributes_list("themes"):
            if not isinstance(c, dict):
                continue
            try:
                spec = load_theme(ext, c)
            except Exception:  # noqa: BLE001 - a broken theme file is skipped
                spec = None
            if spec is None:
                continue
            label = spec.label
            if label in taken:
                label = f"{label} ({ext.publisher})"
            n = 2
            while label in taken:
                label = f"{spec.label} ({ext.publisher} {n})"
                n += 1
            spec.label = label
            taken.add(label)
            out.append(spec)
    return out


def register_all(extensions=None) -> list[str]:
    """(Re)register every VS Code colour theme as an IDE theme. Returns the theme names."""
    from .. import theme as T
    specs = collect(extensions)
    names = {s.label for s in specs}
    for old in list(_registered):
        if old not in names:
            _registered.pop(old, None)
            T.remove_theme(old)
    for s in specs:
        try:
            T.add_theme(s.label, s.tokens(), base="Dark" if s.dark else "Light")
            _registered[s.label] = s
        except Exception:  # noqa: BLE001
            continue
    return [s.label for s in specs]


def spec_for_theme_name(name: str) -> ThemeSpec | None:
    return _registered.get(name)


def current_spec() -> ThemeSpec | None:
    """The VS Code theme behind the IDE's current theme (None for a built-in theme)."""
    try:
        from .. import theme as T
        return _registered.get(T.current_name())
    except Exception:  # noqa: BLE001
        return None


def registered() -> dict[str, ThemeSpec]:
    return dict(_registered)


__all__ = ["ThemeSpec", "load_theme", "chrome_tokens", "collect", "register_all", "current_spec",
           "spec_for_theme_name", "builtin_raw_theme", "registered", "ScopeMatcher", "DARK_PLUS", "LIGHT_PLUS"]
