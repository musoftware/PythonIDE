"""Flutter designer data widgets: ListView.builder / GridView.builder item templates, Text.rich / RichText spans,
Form + TextFormField validators (lib/radform.dart) and RadioGroup (docs/FLUTTER_DESIGNER.md section 1.7).
Plain Python (no Qt): the code generator, the importer, the previews and the tests share it.

Schema (additive, SCHEMA_VERSION stays 1)::

    ListView.builder  {"type": "ListView", "ctor": "builder", "props": {"itemCount": 20, "items": ["A", "B"]},
                       "slots": {"itemBuilder": <template node>}}      (GridView.builder: + crossAxisCount ...)
        the template reads the variables ``index`` and ``item`` (= items[index % items.length]) in $code values:
        {"$code": "item"}, {"$code": "'Row ${index + 1}'"}
    Text.rich / RichText  "spans": [{"text": "Hello ", "style": {...text_style}}, {"$code": "WidgetSpan(...)"}]
    Form              {"type": "Form", "name": "form1"}               -> final form1 = GlobalKey<FormState>();
    TextFormField     "validators": [{"rule": "required"}, {"rule": "minLength", "value": 8, "message": "..."},
                                     {"rule": "regex", "value": "^[0-9]+$"}], "events": {"validator": "checkX"}
    events            "validate:form1" / "validate:form1:onSubmit"     (onSubmit runs when every field is valid)
    RadioGroup        {"type": "RadioGroup", "name": "rdoSize", "props": {"groupValue": "M"},
                       "slots": {"child": Column(Radio / RadioListTile(value: ...) ...)}}
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from . import model as M

DART_DIR = Path(__file__).with_name("dart")
BUILDER_CTOR = "builder"
GRID_DELEGATE_KEYS = ("crossAxisCount", "mainAxisSpacing", "crossAxisSpacing", "childAspectRatio")
PREVIEW_MAX_ITEMS = 40          # copies of an item template the previews build
COPY_SEP = "~"                  # preview copies of a template: "<id>~<index>" (index >= 1)
RULE_DEFAULTS = {"required": "This field is required", "email": "Enter a valid e-mail address",
                 "minLength": "Enter at least {n} characters", "maxLength": "Enter at most {n} characters",
                 "regex": "Invalid format"}

_VALIDATE_RX = re.compile(r"^validate:([A-Za-z_]\w*)(?::([A-Za-z_]\w*))?$")


def radform_source() -> str:
    """lib/radform.dart of a project (the bundled helper)."""
    return (DART_DIR / "radform.dart").read_text(encoding="utf-8")


# ============================================================================================== model
def is_builder(node: dict) -> bool:
    return node.get("type") in ("ListView", "GridView") and node.get("ctor") == BUILDER_CTOR


def base_id(node_id: str | None) -> str | None:
    """The model id of a preview node (copies of an item template are "<id>~<n>")."""
    if not node_id:
        return node_id
    return str(node_id).split(COPY_SEP, 1)[0]


def validate_event(h: str) -> tuple[str, str | None] | None:
    """("form1", "onSubmit" | None) of a validate: event, None for other handlers."""
    m = _VALIDATE_RX.match(h or "")
    return (m.group(1), m.group(2)) if m else None


def handler_ok(h: str) -> bool:
    return validate_event(h) is not None


def event_action(h: str) -> str | None:
    """Dart closure of a validate: event (None = not one)."""
    v = validate_event(h)
    if v is None:
        return None
    form, then = v
    if then:
        return f"() {{ if ({form}.currentState!.validate()) {{ {then}(); }} }}"
    return f"() => {form}.currentState!.validate()"


def template_vars(node: dict) -> set[str]:
    """The item template variables (index / item) a template's Dart values read."""
    out = set()
    for n, *_ in M.walk_node(node):
        for v in _code_values(n):
            for name in ("index", "item"):
                if re.search(rf"(?<![\w.$]){name}\b|\${name}\b|\$\{{[^}}]*\b{name}\b", v):
                    out.add(name)
    return out


def _code_values(n: dict):
    for v in (n.get("props") or {}).values():
        yield from _codes_in(v)
    if n.get("type") == "Code":
        yield str((n.get("props") or {}).get("code") or "")


def _codes_in(v):
    if isinstance(v, dict):
        if M.is_code(v):
            yield str(v["$code"])
        else:
            for x in v.values():
                yield from _codes_in(x)
    elif isinstance(v, list):
        for x in v:
            yield from _codes_in(x)


# ============================================================================================ codegen
def text_spans_x(spans, style=None):
    """TextSpan(style: ..., children: [TextSpan(text: ..., style: ...), ...])."""
    from . import codegen as CG
    if M.is_code(spans):
        return CG.Raw(spans["$code"])
    items = []
    for sp in spans or []:
        if M.is_code(sp):
            items.append(CG.Raw(sp["$code"]))
        elif isinstance(sp, dict):
            items.append(CG.Call("TextSpan", named=[("text", CG.x_str(sp.get("text"))),
                                                    ("style", CG.x_text_style(sp.get("style")))]))
    return CG.Call("TextSpan", named=[("style", CG.x_text_style(style)), ("children", CG.Lst(items))])


def spans_use_google_fonts(spans) -> bool:
    return any(isinstance(sp, dict) and isinstance(sp.get("style"), dict) and sp["style"].get("googleFont")
               for sp in spans or [] if not M.is_code(sp))


def rule_x(r):
    from . import codegen as CG
    if M.is_code(r):
        return CG.Raw(r["$code"])
    rule = r.get("rule")
    msg = [CG.x_str(r["message"])] if r.get("message") not in (None, "") else []
    if rule in ("minLength", "maxLength"):
        try:
            n = int(r.get("value") or 0)
        except (TypeError, ValueError):
            n = 0
        return CG.Call(f"RadRule.{rule}", [CG.Lit(str(n))] + msg)
    if rule == "regex":
        return CG.Call("RadRule.regex", [CG.x_str(str(r.get("value") or ""))] + msg)
    return CG.Call(f"RadRule.{rule if rule in ('required', 'email') else 'required'}", msg)


def validator_x(rules, custom: str | None):
    """validator: radValidate(const [RadRule...], custom: handler) / a handler tear-off / None."""
    from . import codegen as CG
    if M.is_code(rules):
        return CG.Raw(rules["$code"])
    rules = [r for r in rules or [] if isinstance(r, dict)]
    if not rules:
        return CG.Raw(custom) if custom else None
    named = [("custom", CG.Raw(custom))] if custom else []
    return CG.Call("radValidate", [CG.Lst([rule_x(r) for r in rules])], named, const_ctor=False)


def builder_closure(gen, node: dict):
    """itemBuilder: (context, index) => template  /  a block declaring the sample ``items`` and ``item``."""
    from . import codegen as CG
    tmpl = (node.get("slots") or {}).get("itemBuilder")
    body = gen.node(tmpl).render() if isinstance(tmpl, dict) else "const SizedBox.shrink()"
    items = (node.get("props") or {}).get("items")
    if isinstance(items, list) and items:
        lst = CG.x_string_list(items).render(True)
        uses_item = isinstance(tmpl, dict) and "item" in template_vars(tmpl)
        ignore = "" if uses_item else "// ignore: unused_local_variable\n"
        return CG.Raw(f"(context, index) {{\nconst items = {lst};\n{ignore}"
                      f"final item = items[index % items.length];\nreturn {body};\n}}")
    if M.is_code(items):
        return CG.Raw(f"(context, index) {{\nfinal items = {items['$code']};\n"
                      f"final item = items[index % items.length];\nreturn {body};\n}}")
    return CG.Raw(f"(context, index) => {body}")


def grid_delegate_x(props: dict, emit):
    from . import codegen as CG
    named = [(k, emit(k, props[k])) for k in GRID_DELEGATE_KEYS if props.get(k) is not None]
    if not any(k == "crossAxisCount" for k, _ in named):
        named.insert(0, ("crossAxisCount", CG.Lit("2")))
    return CG.Call("SliverGridDelegateWithFixedCrossAxisCount", named=named)


# ========================================================================================= validation
def validate(screen: M.Screen) -> list[M.Issue]:
    issues: list[M.Issue] = []
    forms = {n.get("name") for n, *_ in screen.walk() if n.get("type") == "Form" and n.get("name")}
    for n, parent, _w, _d in screen.walk():
        nid, t = n.get("id"), n.get("type")
        for ev, h in (n.get("events") or {}).items():
            v = validate_event(h)
            if v and v[0] not in forms:
                issues.append(M.Issue("error", nid, f"{ev}: validate:{v[0]} - no Form named {v[0]!r}"))
        rules = (n.get("props") or {}).get("validators")
        if t == "TextFormField" and isinstance(rules, list):
            for r in rules:
                if M.is_code(r):
                    continue
                if not isinstance(r, dict) or r.get("rule") not in M.VALIDATOR_RULES:
                    issues.append(M.Issue("error", nid, f"validators: unknown rule {r!r} "
                                                        f"({', '.join(M.VALIDATOR_RULES)})"))
                elif r["rule"] in ("minLength", "maxLength") and not isinstance(r.get("value"), int):
                    issues.append(M.Issue("error", nid, f"validators: {r['rule']} needs an integer value"))
                elif r["rule"] == "regex":
                    try:
                        re.compile(str(r.get("value") or ""))
                    except re.error as e:
                        issues.append(M.Issue("error", nid, f"validators: bad regex ({e})"))
        if t in ("Radio", "RadioListTile") and not any(p.get("type") == "RadioGroup"
                                                        for p in screen.path_of(nid)[:-1]):
            issues.append(M.Issue("warning", nid, f"{t} should be inside a RadioGroup"))
        if is_builder(n):
            tmpl = (n.get("slots") or {}).get("itemBuilder")
            if isinstance(tmpl, dict):
                for m, *_ in M.walk_node(tmpl):
                    spec = M.CATALOG.get(m.get("type", ""))
                    if spec is not None and spec.needs_name:
                        issues.append(M.Issue("warning", m.get("id"), f"{m.get('type')} in an item template: "
                                                                      "every item shares one state field"))
                if "item" in template_vars(tmpl) and not (n.get("props") or {}).get("items"):
                    issues.append(M.Issue("error", nid, "the item template reads `item` but the list has no items"))
    return issues


# ============================================================================================ preview
_INTERP = re.compile(r"\$\{([^}]*)\}|\$([A-Za-z_]\w*)")


def _eval_simple(expr: str, env: dict):
    """index / item / index + 1 / item.toString() / item.length / numbers - None when not understood."""
    e = expr.strip()
    while e.startswith("(") and e.endswith(")"):
        e = e[1:-1].strip()
    m = re.fullmatch(r"([A-Za-z_]\w*)(?:\.toString\(\)|\.toUpperCase\(\)|\.toLowerCase\(\)|\.length)?", e)
    if m and m.group(1) in env:
        v = env[m.group(1)]
        if e.endswith(".toUpperCase()"):
            return str(v).upper()
        if e.endswith(".toLowerCase()"):
            return str(v).lower()
        if e.endswith(".length"):
            return len(str(v))
        if e.endswith(".toString()"):
            return str(v)
        return v
    m = re.fullmatch(r"(index)\s*([+\-*])\s*(\d+)|(\d+)\s*([+\-*])\s*(index)", e)
    if m and "index" in env:
        a = env["index"]
        if m.group(1):
            op, n = m.group(2), int(m.group(3))
        else:
            op, n = m.group(5), int(m.group(4))
        return a + n if op == "+" else a - n if op == "-" else a * n
    if re.fullmatch(r"-?\d+(\.\d+)?", e):
        return float(e) if "." in e else int(e)
    return None


def eval_item_code(code: str, env: dict):
    """The preview value of a Dart value in an item template (env: index / item); None = not evaluated."""
    s = str(code).strip()
    m = re.fullmatch(r"(['\"])(.*)\1", s, re.S)
    if m:
        body = m.group(2)
        ok = True

        def sub(mm):
            nonlocal ok
            v = _eval_simple(mm.group(1) if mm.group(1) is not None else mm.group(2), env)
            if v is None:
                ok = False
                return mm.group(0)
            return str(v)
        out = _INTERP.sub(sub, body).replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")
        return out if ok else None
    return _eval_simple(s, env)


def _resolve_template(node: dict, env: dict, suffix: str) -> dict:
    out = copy.deepcopy(node)
    for n, *_ in M.walk_node(out):
        if suffix and n.get("id"):
            n["id"] = f"{n['id']}{suffix}"
        spec = M.widget_spec(n.get("type", ""), n.get("ctor"))
        pr = n.get("props") or {}
        for k, v in list(pr.items()):
            if M.is_code(v):
                r = eval_item_code(v["$code"], env)
                if r is not None:
                    kind = spec.props[k].kind if spec and k in spec.props else ""
                    pr[k] = str(r) if kind == "string" else r
    return out


def needs_expand(data: dict) -> bool:
    return any(is_builder(n) for n, *_ in M.walk_node(data.get("tree") or {}))


def expand_builders(data: dict) -> dict:
    """The previews' copy of *data*: every ListView.builder / GridView.builder becomes a ListView /
    GridView.count with ``itemCount`` copies of its template (max PREVIEW_MAX_ITEMS) where index / item are
    substituted; the first copy keeps the model ids, the others get "<id>~<n>"."""
    out = copy.deepcopy(data)

    def rec(n: dict):
        for c, _w in list(M._iter_children(n)):
            rec(c)
        if not is_builder(n):
            return
        pr = n.get("props") or {}
        tmpl = (n.get("slots") or {}).pop("itemBuilder", None)
        items = pr.get("items") if isinstance(pr.get("items"), list) else []
        try:
            count = int(pr.get("itemCount", 5 if not items else len(items)))
        except (TypeError, ValueError):
            count = len(items) or 5
        count = max(0, min(PREVIEW_MAX_ITEMS, count))
        kids = []
        if isinstance(tmpl, dict):
            for i in range(count):
                env = {"index": i}
                if items:
                    env["item"] = items[i % len(items)]
                kids.append(_resolve_template(tmpl, env, f"{COPY_SEP}{i}" if i else ""))
        n["children"] = kids
        if not n.get("slots"):
            n.pop("slots", None)
        keep = {k: v for k, v in pr.items() if k not in ("itemCount", "items")}
        if n["type"] == "ListView":
            n.pop("ctor")
        else:
            n["ctor"] = "count"
            keep.setdefault("crossAxisCount", 2)
        n["props"] = keep
    rec(out["tree"])
    return out
