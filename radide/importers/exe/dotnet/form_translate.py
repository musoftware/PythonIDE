"""Form class -> user code: the methods of a WinForms form translated to a python-tk (or other target) class,
and the ImportResult helpers that store a form's code and the startup form."""
from __future__ import annotations

import re

from ..base import ImportResult
from .common import py_ident, PY_RESERVED
from .cs_lexer import ParseError
from .cs_parser import Parser
from .py_emitter import DEFAULTS, PyEmitter, Untranslatable
from .winforms_reader import class_fields, class_methods, parse_params, WinFormsClass


# ============================================================================ class -> python-tk user code
def translate_form_class(cls: WinFormsClass, form_dict: dict, wiring: dict, all_forms: set[str],
                         language: str = "python-tk", emitter_cls=None, skip_methods: set | None = None,
                         java: bool = False) -> dict:
    """Build the python-tk user code of one form.

    Returns {"code": str, "handlers": {name: [body lines]}, "methods": [(name, status)],
    "stats": (translated, commented), "csharp": {method: source}, "imports": set}.
    *wiring* maps a neutral handler name to a method name of the class or to ("inline", body source)."""
    from ....languages import get_plugin
    from ....model import Form
    from ....controls import event_args, menu_names as _menu_names
    form = Form.from_dict(form_dict)
    controls = {c.name: c.type for c in form.controls}
    menus = set()
    for c in form.controls:
        if c.type in ("MenuStrip", "ToolStrip"):
            menus |= set(_menu_names(c.props.get("Items", [])))
    multiline = {c.name for c in form.controls if c.type == "TextBox" and c.props.get("Multiline")}
    skip = {"InitializeComponent", "Dispose", "initComponents", "main"} | set(skip_methods or ())
    methods = [m for m in class_methods(cls.body) if m["name"] not in skip]
    ctor = [m for m in methods if m["name"] == cls.name]
    methods = [m for m in methods if m["name"] != cls.name]
    fields_raw = {k: v for k, v in class_fields(cls.body).items() if k not in controls and k != "components"
                  and k not in menus}
    emitter_fields = {}
    emitter_cls = emitter_cls or PyEmitter
    probe = emitter_cls()
    for k, (typ, _init) in fields_raw.items():
        emitter_fields[k] = probe.kind_of_type(typ)
    method_names = {m["name"] for m in methods}
    em = emitter_cls(controls, cls.name, emitter_fields, method_names, multiline, menus, all_forms)

    plugin = get_plugin(language)
    code = plugin.new_code(form, False)
    handlers: dict[str, list[str]] = {}
    status: list[tuple[str, str]] = []
    csharp: dict[str, str] = {}

    def translate(m, params_override=None) -> tuple[list[str], int, int]:
        em.locals = [{}]
        for typ, pname in parse_params(m["params"]):
            em.declare(pname, em.kind_of_type(typ))
        before_t, before_u = em.translated, em.untranslated
        try:
            stmts = Parser(m["body"], java).statements()
            lines = em.body(stmts, 0)
        except Exception as e:  # noqa: BLE001 - keep the C# as comments
            lines = [f"# C#: {ln.strip()}" for ln in m["body"].strip().splitlines() if ln.strip()] + \
                [f"# (could not translate: {e})", "pass"]
            em.untranslated += 1
        return lines, em.translated - before_t, em.untranslated - before_u

    # fields -> class attributes
    field_lines = []
    for k, (typ, init) in fields_raw.items():
        val = DEFAULTS.get(probe.kind_of_type(typ), "None")
        if init:
            try:
                val, _k = em.ex(Parser(init, java).expr())
            except (ParseError, Untranslatable):
                val = f"None  # C#: {init}"
        field_lines.append(f"    {py_ident(k)} = {val}")

    by_name = {m["name"]: m for m in methods}
    handled_methods: dict[str, str] = {}
    handler_blocks: list[tuple[str, list[str], str | None]] = []
    for handler, meth in wiring.items():
        if isinstance(meth, tuple):                     # inline body (lambda / anonymous listener)
            body_src = meth[1]
            only = re.fullmatch(r"\s*(?:(?:\w+\.)?this\.)?(\w+)\s*\(\s*\w*\s*\)\s*;?\s*", body_src)
            if only and only.group(1) in by_name and only.group(1) not in handled_methods:
                meth = only.group(1)                   # e -> btnGreet_Click(): the method IS the handler
            else:
                body, _t, u = translate({"params": "", "body": body_src})
                status.append((handler, "rules" if u == 0 else "partial"))
                csharp[handler] = body_src
                handler_blocks.append((handler, body, None))
                handlers[handler] = body
                continue
        m = by_name.get(meth)
        if m is None:
            continue
        csharp[meth] = m["header"] + " {" + m["body"] + "}"
        if meth in handled_methods:
            body = [f"self.{handled_methods[meth]}()"]
        else:
            body, t, u = translate(m)
            status.append((meth, "rules" if u == 0 else "partial"))
            handled_methods[meth] = handler
        handler_blocks.append((handler, body, meth))
        handlers[handler] = body
    # constructor body (after InitializeComponent) -> Load handler prefix
    if ctor:
        body_text = re.sub(r"\bInitializeComponent\s*\(\s*\)\s*;", "", ctor[0]["body"])
        if body_text.strip():
            lines, t, u = translate({**ctor[0], "body": body_text})
            load = f"{cls.name}_Load"
            prev = handlers.get(load)
            handlers[load] = lines + ([] if prev is None else prev)
            if prev is None:
                handler_blocks.insert(0, (load, lines, None))
            else:
                handler_blocks = [(h, handlers[h] if h == load else b, mm) for h, b, mm in handler_blocks]
            status.append((cls.name + " (constructor)", "rules" if u == 0 else "partial"))
    # other methods -> helper methods
    helper_src = []
    for m in methods:
        if m["name"] in handled_methods and handled_methods[m["name"]] == m["name"]:
            continue
        if m["name"] in handled_methods:
            # handler named differently: keep the original method too (called by the handler)
            pass
        csharp[m["name"]] = m["header"] + " {" + m["body"] + "}"
        params = parse_params(m["params"])
        if m["name"] in handled_methods:
            continue
        lines, t, u = translate(m)
        status.append((m["name"], "rules" if u == 0 else "partial"))
        pnames = [py_ident(p[1]) for p in params]
        is_handler_sig = len(params) == 2 and params[0][0].split(".")[-1] in ("object", "Object") and \
            params[1][0].endswith("EventArgs")
        sig = "self, sender=None, e=None" if is_handler_sig else ", ".join(["self"] + pnames)
        helper_src.append(f"    def {py_ident(m['name']) if m['name'] in PY_RESERVED else m['name']}({sig}):")
        helper_src += ["        " + ln if ln.strip() else "" for ln in lines]
        helper_src.append("")

    # assemble the user code
    for handler, body, _meth in handler_blocks:
        ev = handler.rsplit("_", 1)[-1]
        idx = plugin.find_handler(code, handler)
        if idx >= 0:
            lines = code.splitlines()
            if idx + 1 < len(lines) and lines[idx + 1].strip() == "pass":     # the stub body
                del lines[idx + 1]
            lines[idx + 1:idx + 1] = ["        " + ln if ln.strip() else "" for ln in body]
            code = "\n".join(lines) + "\n"
            continue
        code, line = plugin.add_handler(code, handler, form, event_args(ev))
        lines = code.splitlines()
        if line < len(lines) and lines[line].strip() == "pass":
            lines[line:line + 1] = ["        " + ln if ln.strip() else "" for ln in body]
        else:
            k = plugin.find_handler(code, handler)
            lines[k + 1:k + 2] = ["        " + ln if ln.strip() else "" for ln in body]
        code = "\n".join(lines) + "\n"
    if field_lines:
        code = code.replace('    """Write your event handlers here."""\n',
                            '    """Write your event handlers here."""\n\n    # fields of the original form\n'
                            + "\n".join(field_lines) + "\n", 1)
    if helper_src:
        idx = code.find("\n\nif __name__")
        block = "\n    # ---- methods of the original form ----\n\n" + "\n".join(helper_src).rstrip() + "\n"
        code = code[:idx] + "\n" + block + code[idx:] if idx >= 0 else code + block
    if em.imports:
        imports = sorted(em.imports, key=lambda s: (s.startswith("from"), s))
        first_nl = code.find("\n")
        code = "\n".join(imports) + "\n" + code if first_nl < 0 else \
            code[:first_nl + 1] + "\n".join(imports) + "\n" + code[first_nl + 1:]
    # a Load stub that is still empty is fine; make sure there is no 'pass' after real code
    code = _drop_stray_pass(code)
    return {"code": code, "handlers": handlers, "methods": status, "stats": (em.translated, em.untranslated),
            "csharp": csharp, "imports": set(em.imports)}


def _drop_stray_pass(code: str) -> str:
    lines = code.splitlines()
    out = []
    for i, ln in enumerate(lines):
        if ln.strip() == "pass" and out:
            prev = next((x for x in reversed(out) if x.strip()), "")
            ind = len(ln) - len(ln.lstrip())
            pind = len(prev) - len(prev.lstrip())
            if prev.strip() and not prev.rstrip().endswith(":") and not prev.strip().startswith("#") and \
                    pind == ind:
                continue
        out.append(ln)
    return "\n".join(out) + "\n"


# ============================================================================ result helpers
def set_form_code(res: ImportResult, form: str, code: str, language: str, handlers: dict | None = None) -> None:
    """Record the complete user code of *form* (resources["form_code"], used by the wizard when the project
    language is resources["form_code_language"]) and its handler bodies in the wizard's format
    {"ctrl.Event" / ".Load": [python lines]} (used for the other languages)."""
    res.resources.setdefault("form_code", {})[form] = code
    res.resources["form_code_language"] = language
    if handlers:
        out = {}
        for name, body in handlers.items():
            owner, _, event = name.rpartition("_")
            key = f".{event}" if owner == form else f"{owner}.{event}"
            # the full code is used for *language*; other languages get the rules translation as comments
            out[key] = [("comment", f"({language}) {ln}") for ln in body if ln.strip()] + [("python", "pass")]
        res.handlers[form] = out


def set_startup(res: ImportResult, form: str) -> None:
    res.resources["startup"] = form
    res.resources["startup_form"] = form
