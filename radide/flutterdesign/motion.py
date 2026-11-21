"""Flutter designer motion: animation triggers, keyframes, screen timelines, state variables, implicit
($when) / explicit ($timeline) property animation and page transitions (plan MOTION_VARIANTS_FOLDABLES.md,
slice F). Plain Python (no Qt): the code generator, the importer, the previews and the tests share it.

Schema (additive to docs/FLUTTER_DESIGNER.md, SCHEMA_VERSION stays 1)::

    node  "anim": {"type": "shake", "trigger": "tap", "repeat": 0, "reverse": true}
          "anim": {"type": "keyframes", "durationMs": 1200, "trigger": "load",
                   "tracks": {"opacity": [[0, 0], [300, 1, "Curves.easeOut"]], "offsetY": [[0, 40], [600, 0]],
                              "scale": [...], "rotation": [...] (turns), "color": [[0, "#FF..."], ...]}}
          "anim": {..., "trigger": "manual", "controller": "heroFx"}    -> final heroFx = RadFxController();
          "anim": {..., "trigger": "state:expanded"}                    -> play: expanded
    screen "state": [{"name": "expanded", "type": "bool", "init": false}]
           "timelines": [{"name": "intro", "durationMs": 1500, "autostart": true, "repeat": false,
                          "reverse": false}]
           "transition": {"type": "fade", "durationMs": 300}
    prop values {"$when": {"state": "expanded", "on": 200, "off": 100}}
                {"$timeline": "intro", "from": 0, "to": 1, "interval": [0, 0.5], "curve": "Curves.easeOut"}
    events "toggle:expanded" "play:intro" "reverse:intro" "push:Home?transition=fade&ms=300"

The generated code uses lib/radfx.dart (``dart/radfx.dart``): RadFx, RadKeyframes, RadFxController, RadRoute,
radDrive / radDriveOffset / radPlay.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from urllib.parse import parse_qsl

from . import model as M

DART_DIR = Path(__file__).with_name("dart")

LEGACY_TYPES = ["fadeIn", "fadeInUp", "fadeInDown", "fadeInLeft", "fadeInRight", "slideUp", "slideDown",
                "slideLeft", "slideRight", "scaleIn", "zoomIn", "bounceIn"]
NEW_TYPES = ["shake", "pulse", "bounce", "flipX", "flipY", "rotate", "swing", "heartBeat", "typewriter",
             "colorTo", "keyframes"]
ENTRANCE = set(LEGACY_TYPES) | {"flipX", "flipY", "typewriter"}
TRIGGERS = ["load", "tap", "hover", "longPress", "visible", "manual"]      # + "state:<bool field>"
KEY_TRACKS = ["opacity", "offsetX", "offsetY", "scale", "rotation", "color"]
TRANSITIONS = ["fade", "slideLeft", "slideUp", "scale", "none"]
STATE_TYPES = {"bool": "false", "int": "0", "double": "0.0", "String": "''"}
TIMELINE_KINDS = ("timeline", "timeline_offset")
# keys of an anim dict the generator understands (others are informational, e.g. "from")
ANIM_KEYS = ("type", "delayMs", "durationMs", "offsetX", "offsetY", "scale", "curve", "trigger", "repeat",
             "reverse", "turns", "color", "tracks", "controller")

_IDENT = re.compile(r"^[A-Za-z_]\w*$")
_EVENT_RX = re.compile(r"^(toggle|play|reverse):([A-Za-z_]\w*)$")
_PUSH_RX = re.compile(r"^push:([A-Za-z_]\w*)(?:\?(.*))?$")


def radfx_source() -> str:
    """lib/radfx.dart of a project (the bundled helper)."""
    return (DART_DIR / "radfx.dart").read_text(encoding="utf-8")


def radlayout_source() -> str:
    return (DART_DIR / "radlayout.dart").read_text(encoding="utf-8")


# =============================================================================================== anim
def is_entrance(anim: dict | None) -> bool:
    return bool(anim) and anim.get("type") in ENTRANCE


def trigger_of(anim: dict | None) -> tuple[str, str | None]:
    """("load" | "tap" | ... | "state", state field or None)."""
    t = str((anim or {}).get("trigger") or "load")
    if t.startswith("state:"):
        return "state", t[6:]
    return t, None


def duration_ms(anim: dict) -> int:
    if anim.get("type") == "keyframes":
        last = 0
        for keys in (anim.get("tracks") or {}).values():
            for k in keys or []:
                if isinstance(k, (list, tuple)) and k:
                    last = max(last, int(k[0]))
        if last:
            return last
    try:
        return max(1, int(anim.get("durationMs", 500)))
    except (TypeError, ValueError):
        return 500


def controller_name(node: dict) -> str:
    """Field name of the RadFxController of a node animated with trigger manual."""
    a = node.get("anim") or {}
    if a.get("controller"):
        return str(a["controller"])
    base = node.get("name") or f"_{node.get('id', 'w0')}"
    return f"{base}Fx"


# ============================================================================================ codegen
def wrap(gen, x, a: dict | None, node: dict | None = None):
    """The RadFx call around the widget expression *x* (codegen.TreeGen.wrap_anim delegates here).

    The named arguments of the original twelve entrance types are emitted exactly as before (screens made
    before triggers / keyframes existed generate byte-identical code)."""
    if not (a and a.get("type")):
        return x
    from . import codegen as CG
    ctx = gen.ctx
    ctx.uses_anim = True
    named = [("type", CG.Lit(f"RadFxType.{a['type']}"))]
    for k in ("delayMs", "durationMs"):
        if a.get(k) not in (None, ""):
            named.append((k, CG.x_num(int(a[k]))))
    for k in ("offsetX", "offsetY", "scale"):
        if a.get(k) is not None:
            named.append((k, CG.x_num(a[k])))
    if a.get("curve"):
        named.append(("curve", CG.Lit(a["curve"])))
    trig, field = trigger_of(a)
    if trig != "load":
        named.append(("trigger", CG.Lit(f"RadFxTrigger.{trig}")))
    if a.get("repeat") not in (None, 1):
        named.append(("repeat", CG.x_num(int(a["repeat"]))))
    if a.get("reverse"):
        named.append(("reverse", CG.Lit("true")))
    if trig == "state" and field:
        named.append(("play", CG.Raw(field)))
    if a.get("turns") is not None:
        named.append(("turns", CG.x_num(a["turns"])))
    if a.get("color") is not None:
        named.append(("color", CG.x_color(a["color"])))
    if a.get("type") == "keyframes" and a.get("tracks"):
        named.append(("keyframes", keyframes_x(a["tracks"])))
    if trig == "manual" or a.get("controller"):
        cname = controller_name(node or {"anim": a})
        ctx.fields[cname] = CG.Field(cname, "RadFxController", "RadFxController()")
        named.append(("controller", CG.Raw(cname)))
    named.append(("child", x))
    return CG.Call("RadFx", named=named)


def keyframes_x(tracks: dict):
    from . import codegen as CG
    named = []
    for tr in KEY_TRACKS:
        keys = tracks.get(tr)
        if not keys:
            continue
        items = []
        for k in keys:
            ms = CG.Lit(str(int(k[0])))
            if tr == "color":
                val = CG.x_color(k[1])
                cls = "RadColorKey"
            else:
                val = CG.x_num(k[1])
                cls = "RadKey"
            args = [ms, val] + ([CG.Lit(k[2])] if len(k) > 2 and k[2] else [])
            items.append(CG.Call(cls, args))
        named.append((tr, CG.Lst(items)))
    return CG.Call("RadKeyframes", named=named, multiline=len(named) > 1)


def when_x(kind: str, v: dict, emit, owner: str = ""):
    """{"$when": {"state", "on", "off"}} -> ``state ? on : off`` (*emit* = codegen.emit_value)."""
    from . import codegen as CG
    w = v["$when"]
    on = emit(kind, w.get("on"), owner) or CG.Lit("null")
    off = emit(kind, w.get("off"), owner) or CG.Lit("null")
    return CG.Raw(f"{w.get('state', 'state')} ? {on.render()} : {off.render()}")


def _offset_src(v) -> str:
    from . import codegen as CG
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        v = (0, 0)
    return f"const Offset({CG.dart_num(v[0])}, {CG.dart_num(v[1])})"


def timeline_x(kind: str, v: dict):
    """{"$timeline": name, from, to, interval, curve} -> radDrive(name, from, to, begin:, end:, curve:)."""
    from . import codegen as CG
    name = v["$timeline"]
    iv = v.get("interval") or [0, 1]
    named = []
    if iv and float(iv[0]) != 0:
        named.append(f"begin: {CG.dart_num(float(iv[0]))}")
    if iv and len(iv) > 1 and float(iv[1]) != 1:
        named.append(f"end: {CG.dart_num(float(iv[1]))}")
    if v.get("curve"):
        named.append(f"curve: {v['curve']}")
    if kind == "timeline_offset":
        args = [name, _offset_src(v.get("from", [0, 1])), _offset_src(v.get("to", [0, 0]))]
        fn = "radDriveOffset"
    else:
        args = [name, CG.dart_num(float(v.get("from", 0))), CG.dart_num(float(v.get("to", 1)))]
        fn = "radDrive"
    return CG.Raw(f"{fn}({', '.join(args + named)})")


def stopped_x(kind: str, v):
    """A plain value for a timeline property: const AlwaysStoppedAnimation(value)."""
    from . import codegen as CG
    if kind == "timeline_offset":
        return CG.Raw(f"const AlwaysStoppedAnimation<Offset>({_offset_src(v)[6:]})")
    try:
        return CG.Raw(f"const AlwaysStoppedAnimation<double>({CG.dart_num(float(v))})")
    except (TypeError, ValueError):
        return None


def is_when(v) -> bool:
    return isinstance(v, dict) and "$when" in v and isinstance(v["$when"], dict)


def is_timeline(v) -> bool:
    return isinstance(v, dict) and isinstance(v.get("$timeline"), str)


def event_action(h: str) -> str | None:
    """Dart closure for the motion event forms (None = not one of them)."""
    m = _EVENT_RX.match(h or "")
    if m:
        verb, name = m.groups()
        if verb == "toggle":
            return f"() => setState(() => {name} = !{name})"
        if verb == "play":
            return f"() => {name}.forward(from: 0)"
        return f"() => {name}.reverse()"
    m = _PUSH_RX.match(h or "")
    if m and m.group(2):
        cls, q = m.group(1), dict(parse_qsl(m.group(2)))
        t = q.get("transition", "fade")
        if t not in TRANSITIONS:
            t = "fade"
        args = [f"builder: (context) => const {cls}()", f"transition: RadTransition.{t}"]
        if q.get("ms") and str(q["ms"]).isdigit() and int(q["ms"]) != 300:
            args.append(f"durationMs: {int(q['ms'])}")
        return f"() => Navigator.push(context, RadRoute({', '.join(args)}))"
    return None


def push_target(h: str) -> str | None:
    m = _PUSH_RX.match(h or "")
    return m.group(1) if m else None


def is_motion_event(h: str) -> bool:
    return bool(_EVENT_RX.match(h or "") or (_PUSH_RX.match(h or "") and "?" in (h or "")))


def state_fields(screen: M.Screen) -> list[dict]:
    return [s for s in (screen.data.get("state") or []) if isinstance(s, dict) and s.get("name")]


def timelines(screen: M.Screen) -> list[dict]:
    return [t for t in (screen.data.get("timelines") or []) if isinstance(t, dict) and t.get("name")]


def state_init(s: dict) -> str:
    """Dart initialiser of a state variable."""
    from . import codegen as CG
    t = s.get("type") or "bool"
    v = s.get("init")
    if v is None:
        return STATE_TYPES.get(t, "null")
    if t == "bool":
        return "true" if v else "false"
    if t == "int":
        return str(int(v))
    if t == "double":
        return CG.dart_num(float(v))
    if t == "String":
        return CG.dart_string(v)
    return str(v)


def designer_members(screen: M.Screen) -> dict:
    """Extra parts of the generated designer State: {"fields": [lines], "init": [lines], "dispose": [names],
    "mixin": str}."""
    out = {"fields": [], "init": [], "dispose": [], "mixin": ""}
    for s in state_fields(screen):
        out["fields"].append(f"  {s.get('type') or 'bool'} {s['name']} = {state_init(s)};")
    tls = timelines(screen)
    if tls:
        out["mixin"] = " with TickerProviderStateMixin"
    for t in tls:
        ms = max(1, int(t.get("durationMs") or 1000))
        out["fields"].append(f"  late final AnimationController {t['name']} = AnimationController(vsync: this, "
                             f"duration: const Duration(milliseconds: {ms}));")
        out["dispose"].append(t["name"])
        if t.get("autostart"):
            opts = []
            if t.get("repeat"):
                opts.append("repeat: true")
            if t.get("reverse"):
                opts.append("reverse: true")
            out["init"].append(f"radPlay({t['name']}, context{''.join(', ' + o for o in opts)});")
    return out


def init_state_block(lines: list[str]) -> list[str]:
    if not lines:
        return []
    body = ["  @override", "  void initState() {", "    super.initState();",
            "    WidgetsBinding.instance.addPostFrameCallback((_) {", "      if (!mounted) return;"]
    body += [f"      {ln}" for ln in lines]
    body += ["    });", "  }", ""]
    return body


def transition_of(screen: M.Screen) -> dict | None:
    t = screen.data.get("transition")
    if isinstance(t, dict) and t.get("type") in TRANSITIONS:
        return t
    return None


def transition_spec(t: dict) -> str:
    ms = int(t.get("durationMs") or 300)
    tail = f", durationMs: {ms}" if ms != 300 else ""
    return f"RadRouteSpec(RadTransition.{t['type']}{tail})"


# ========================================================================================= validation
def validate(screen: M.Screen) -> list[M.Issue]:
    issues: list[M.Issue] = []
    d = screen.data
    states = {s["name"]: s for s in state_fields(screen)}
    tls = {t["name"] for t in timelines(screen)}
    names = screen.names()
    for s in d.get("state") or []:
        n = s.get("name") if isinstance(s, dict) else None
        if not n or not _IDENT.match(str(n)) or n in M.DART_KEYWORDS:
            issues.append(M.Issue("error", None, f"state variable {n!r} is not a Dart identifier"))
        elif s.get("type", "bool") not in STATE_TYPES:
            issues.append(M.Issue("error", None, f"state {n}: type must be one of {', '.join(STATE_TYPES)}"))
        elif n in names:
            issues.append(M.Issue("error", None, f"state {n}: a widget has the same name"))
    for t in d.get("timelines") or []:
        n = t.get("name") if isinstance(t, dict) else None
        if not n or not _IDENT.match(str(n)) or n in M.DART_KEYWORDS:
            issues.append(M.Issue("error", None, f"timeline {n!r} is not a Dart identifier"))
        elif n in states or n in names:
            issues.append(M.Issue("error", None, f"timeline {n}: the name is already used"))
    tr = d.get("transition")
    if tr is not None and (not isinstance(tr, dict) or tr.get("type") not in TRANSITIONS):
        issues.append(M.Issue("error", None, f"transition: type must be one of {', '.join(TRANSITIONS)}"))
    for n, *_ in screen.walk():
        nid = n.get("id")
        a = n.get("anim")
        if a:
            trig, field = trigger_of(a)
            if trig not in TRIGGERS and trig != "state":
                issues.append(M.Issue("error", nid, f"unknown animation trigger {a.get('trigger')!r}"))
            if trig == "state" and (field not in states or states[field].get("type", "bool") != "bool"):
                issues.append(M.Issue("error", nid, f"trigger state:{field}: no bool state variable {field!r}"))
            if a.get("type") == "keyframes" and not a.get("tracks"):
                issues.append(M.Issue("warning", nid, "keyframes animation without tracks"))
            for tr_name, keys in (a.get("tracks") or {}).items():
                if tr_name not in KEY_TRACKS:
                    issues.append(M.Issue("error", nid, f"unknown keyframe track {tr_name!r}"))
                elif not isinstance(keys, list) or not all(isinstance(k, list) and len(k) >= 2 for k in keys):
                    issues.append(M.Issue("error", nid, f"track {tr_name}: keys must be [ms, value(, curve)]"))
            if a.get("type") == "colorTo" and a.get("color") is None:
                issues.append(M.Issue("warning", nid, "colorTo needs a color"))
            if a.get("controller") and not _IDENT.match(str(a["controller"])):
                issues.append(M.Issue("error", nid, f"controller {a['controller']!r} is not a Dart identifier"))
        spec = M.widget_spec(n.get("type", ""), n.get("ctor"))
        for k, v in (n.get("props") or {}).items():
            ps = spec.props.get(k) if spec else None
            if is_when(v):
                st = v["$when"].get("state")
                if st not in states:
                    issues.append(M.Issue("error", nid, f"{k}: $when uses an unknown state variable {st!r}"))
            elif is_timeline(v):
                if v["$timeline"] not in tls:
                    issues.append(M.Issue("error", nid, f"{k}: unknown timeline {v['$timeline']!r}"))
                if ps is not None and ps.kind not in TIMELINE_KINDS:
                    issues.append(M.Issue("warning", nid, f"{k}: only transition properties (FadeTransition."
                                                          f"opacity ...) follow a timeline - the end value is used"))
        for ev, h in (n.get("events") or {}).items():
            m = _EVENT_RX.match(h or "")
            if m:
                verb, name = m.groups()
                if verb == "toggle" and (name not in states or states[name].get("type", "bool") != "bool"):
                    issues.append(M.Issue("error", nid, f"{ev}: toggle:{name} needs a bool state variable"))
                ctrls = {controller_name(x) for x, *_ in screen.walk() if trigger_of(x.get("anim"))[0] ==
                         "manual" or (x.get("anim") or {}).get("controller")}
                if verb in ("play", "reverse") and name not in tls and name not in ctrls:
                    issues.append(M.Issue("error", nid, f"{ev}: {verb}:{name} - no timeline / controller {name!r}"))
    return issues


def handler_ok(h: str) -> bool:
    return bool(_EVENT_RX.match(h or "") or _PUSH_RX.match(h or ""))


# ============================================================================================ preview
def curve(name, t: float) -> float:
    """Python version of the Flutter curves the designer offers (preview maths)."""
    n = str(name or "Curves.easeOut").split(".")[-1]
    t = max(0.0, min(1.0, t))
    if n == "linear":
        return t
    if n == "easeIn":
        return t * t * t
    if n in ("easeInOut", "easeInOutCubic", "ease", "fastOutSlowIn"):
        return 4 * t * t * t if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
    if n == "easeOutBack":
        k = 1.70158
        return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2
    if n == "bounceOut":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + .75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + .9375
        t -= 2.625 / d1
        return n1 * t * t + .984375
    if n == "elasticOut":
        return 1.0 if t == 1 else 2 ** (-10 * t) * math.sin((t * 10 - .75) * (2 * math.pi) / 3) + 1
    if n == "decelerate":
        return 1 - (1 - t) ** 2
    return 1 - (1 - t) ** 3


def _key_value(keys, ms: float):
    keys = [k for k in keys or [] if isinstance(k, (list, tuple)) and len(k) >= 2]
    if not keys:
        return None
    if ms <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if ms <= b[0]:
            span = float(b[0] - a[0])
            t = 1.0 if span <= 0 else (ms - a[0]) / span
            e = curve(b[2] if len(b) > 2 and b[2] else "Curves.linear", t)
            if isinstance(a[1], str) or isinstance(b[1], str):
                return (a[1], b[1], e)            # colours: (from, to, t)
            return a[1] + (b[1] - a[1]) * e
    return keys[-1][1]


def frame(anim: dict, v: float) -> dict:
    """The look of *anim* at controller value *v* (0..1) - radFxFrame() of radfx.dart in Python.
    Keys: opacity, dx, dy, sx, sy, rotation (turns), rx, ry (radians), reveal, tint, color, origin."""
    f = {"opacity": 1.0, "dx": 0.0, "dy": 0.0, "sx": 1.0, "sy": 1.0, "rotation": 0.0, "rx": 0.0, "ry": 0.0,
         "reveal": 1.0, "tint": 0.0, "color": anim.get("color"), "origin": "center"}
    typ = anim.get("type", "fadeIn")
    v = max(0.0, min(1.0, v))
    t = curve(anim.get("curve", "Curves.easeOut"), v)

    def num(k, d):
        x = anim.get(k)
        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else d
    if typ in ("fadeIn", "fadeInUp", "fadeInDown", "fadeInLeft", "fadeInRight", "scaleIn", "zoomIn"):
        f["opacity"] = t
    if typ in ("fadeInUp", "slideUp"):
        f["dy"] = num("offsetY", 30) * (1 - t)
    elif typ in ("fadeInDown", "slideDown"):
        f["dy"] = num("offsetY", -30) * (1 - t)
    elif typ in ("fadeInLeft", "slideRight"):
        f["dx"] = num("offsetX", -30) * (1 - t)
    elif typ in ("fadeInRight", "slideLeft"):
        f["dx"] = num("offsetX", 30) * (1 - t)
    elif typ in ("scaleIn", "zoomIn"):
        s0 = num("scale", 0.8 if typ == "scaleIn" else 0.3)
        f["sx"] = f["sy"] = s0 + (1 - s0) * t
    elif typ == "bounceIn":
        s0 = num("scale", 0.3)
        f["sx"] = f["sy"] = s0 + (1 - s0) * curve("elasticOut", v)
        f["opacity"] = min(1.0, v * 2)
    elif typ == "shake":
        f["dx"] = math.sin(v * math.pi * 8) * num("offsetX", 10) * (1 - v)
    elif typ == "pulse":
        f["sx"] = f["sy"] = 1 + (num("scale", 1.1) - 1) * math.sin(math.pi * v)
    elif typ == "bounce":
        f["dy"] = -abs(num("offsetY", 20)) * abs(math.sin(math.pi * v * 2)) * (1 - v * 0.5)
    elif typ in ("flipX", "flipY"):
        f["rx" if typ == "flipX" else "ry"] = (1 - t) * math.pi / 2
        f["opacity"] = min(1.0, v * 2)
    elif typ == "rotate":
        f["rotation"] = num("turns", 1.0) * t
    elif typ == "swing":
        f["rotation"] = math.sin(v * math.pi * 6) * num("turns", 0.04) * (1 - v)
        f["origin"] = "topCenter"
    elif typ == "heartBeat":
        if v < .14:
            p = v / .14
        elif v < .28:
            p = 1 - (v - .14) / .14
        elif v < .42:
            p = (v - .28) / .14
        elif v < .7:
            p = 1 - (v - .42) / .28
        else:
            p = 0.0
        f["sx"] = f["sy"] = 1 + (num("scale", 1.3) - 1) * p
    elif typ == "typewriter":
        f["reveal"] = t
    elif typ == "colorTo":
        f["tint"] = t
    elif typ == "keyframes":
        tracks = anim.get("tracks") or {}
        ms = v * duration_ms(anim)
        for tr, key in (("opacity", "opacity"), ("offsetX", "dx"), ("offsetY", "dy"), ("rotation", "rotation")):
            x = _key_value(tracks.get(tr), ms)
            if isinstance(x, (int, float)):
                f[key] = float(x)
        s = _key_value(tracks.get("scale"), ms)
        if isinstance(s, (int, float)):
            f["sx"] = f["sy"] = float(s)
        c = _key_value(tracks.get("color"), ms)
        if c is not None:
            f["color"], f["tint"] = c, 1.0
    return f


def rest_value(anim: dict) -> float:
    """Controller value of an animation that is not playing in the designer (final look)."""
    trig, _f = trigger_of(anim)
    return 1.0 if anim.get("type") in ENTRANCE or trig == "state" else 0.0


def value_at(anim: dict, t_ms: float) -> float:
    """Controller value ``t_ms`` after "Play" (every trigger plays once in the designer; repeat / reverse
    honoured, forever = 3 runs)."""
    delay = float(anim.get("delayMs") or 0)
    dur = float(duration_ms(anim))
    runs = int(anim.get("repeat", 1) or 0) or 3
    rev = bool(anim.get("reverse"))
    per = dur * (2 if rev else 1)
    x = t_ms - delay
    if x < 0:
        return 0.0 if trigger_of(anim)[0] == "load" or anim.get("type") not in ENTRANCE else 1.0
    if x >= per * runs:
        return 0.0 if rev else 1.0
    x = x % per
    if x <= dur:
        return x / dur
    return 1 - (x - dur) / dur


def play_length(anim: dict) -> float:
    dur = float(duration_ms(anim))
    runs = int(anim.get("repeat", 1) or 0) or 3
    return float(anim.get("delayMs") or 0) + dur * runs * (2 if anim.get("reverse") else 1)


def resolve_value(v, kind: str = "", state: dict | None = None, t_ms: dict | None = None):
    """A designer preview value for $when / $timeline (other values unchanged)."""
    if is_when(v):
        w = v["$when"]
        return w.get("on") if (state or {}).get(w.get("state")) else w.get("off")
    if is_timeline(v):
        prog = (t_ms or {}).get(v["$timeline"])
        p = 1.0 if prog is None else prog
        iv = v.get("interval") or [0, 1]
        b, e = float(iv[0]), float(iv[1]) if len(iv) > 1 else 1.0
        local = 0.0 if p <= b else 1.0 if p >= e or e <= b else (p - b) / (e - b)
        local = curve(v.get("curve", "Curves.linear"), local)
        frm, to = v.get("from", 0 if kind != "timeline_offset" else [0, 1]), \
            v.get("to", 1 if kind != "timeline_offset" else [0, 0])
        if isinstance(frm, (list, tuple)) and isinstance(to, (list, tuple)):
            return [frm[0] + (to[0] - frm[0]) * local, frm[1] + (to[1] - frm[1]) * local]
        try:
            return float(frm) + (float(to) - float(frm)) * local
        except (TypeError, ValueError):
            return to
    return v


def state_values(screen: M.Screen) -> dict:
    return {s["name"]: s.get("init") for s in state_fields(screen)}
