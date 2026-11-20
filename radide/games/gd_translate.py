"""Translate the Python code of a pygame game scene (``<Scene>.py``, radgame API) to GDScript for the
Godot export (``<Scene>.gd`` extends res://radgame/radgame_scene.gd).

Rule based, for the radgame API subset a RAD IDE game uses: module constants and variables, functions
and VB-style handlers, ``if / elif / else``, ``for`` (lists, ``range``, ``dict.items()``), ``while``,
arithmetic and comparisons, f-strings, lists / tuples / dicts, list comprehensions in assignments,
``global``; the objects of the scene by name (``Player.y = 250`` -> ``setp(Player, "y", 250)``),
``game.score`` / ``game.vars`` / ``game.time``, ``Spawn`` / ``Destroy`` / ``FindGroup``, ``AddScore``,
``SaveData`` / ``LoadData``, ``PlaySound``, ``EnableBehaviour`` / ``obj.enable()`` /
``obj.behaviour()``, timers (``Timer1.start()``, ``Timer1.interval``), ``Random``, ``math.*``,
particles (``Emit`` / ``Burst``) and physics (``ApplyImpulse`` / ``SetVelocity``).

A statement the rules cannot translate is kept as a ``# TODO`` comment with the Python line(s) - or,
when an AI translator is given (``ai=callable(python_snippet, context) -> gdscript | None``, see
:func:`ai_translator`), translated by the user's AI provider (radide.ai) and marked so.

    gd, report = translate("Scene1", code, scene_dict)

Pure Python (no Qt) - used by radide.games.godot_export and the tests.
"""
from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from dataclasses import dataclass, field

# -------------------------------------------------------------------------------------------- tables
# radgame helpers -> GDScript runtime helpers (radgame_scene.gd)
API_FUNCS = {
    "Spawn": "spawn", "Destroy": "destroy", "Clone": "clone_obj", "Find": "find", "FindGroup": "find_group",
    "AddScore": "add_score", "PlaySound": "play_sound", "PlayMusic": "play_music", "StopMusic": "stop_music",
    "ShowMessage": "show_message", "IsKeyDown": "key_down", "GoToScene": "go_to_scene",
    "RestartScene": "restart_scene", "Quit": "quit_game", "SaveData": "save_data", "LoadData": "load_data",
    "AddTimer": "add_timer", "Random": "randi_range", "EnableBehaviour": "enable_behaviour_all",
    "Emit": "emit_particles", "Burst": "burst_particles", "StopEmitter": "stop_emitter",
    "ApplyImpulse": "apply_impulse", "ApplyForce": "apply_force", "SetVelocity": "set_body_velocity",
    "SetTile": "set_tile", "SetTerrain": "set_terrain",
}
PY_FUNCS = {"print": "print", "len": "len", "abs": "abs", "min": "min", "max": "max", "int": "int",
            "float": "float", "str": "str", "round": "round", "range": "range", "bool": "bool"}
MATH_FUNCS = {"sin": "sin", "cos": "cos", "tan": "tan", "asin": "asin", "acos": "acos", "atan": "atan",
              "atan2": "atan2", "sqrt": "sqrt", "floor": "floori", "ceil": "ceili", "fabs": "abs", "pow": "pow",
              "exp": "exp", "log": "log", "radians": "deg_to_rad", "degrees": "rad_to_deg", "copysign": "",
              "isclose": "is_equal_approx"}
MATH_CONSTS = {"pi": "PI", "tau": "TAU", "inf": "INF", "e": "exp(1.0)"}
RANDOM_FUNCS = {"randint": "randi_range", "uniform": "randf_range", "random": "randf"}
GAME_ATTRS = {"score": "score", "lives": "lives", "vars": "vars", "time": "game_time", "frame": "frame"}
GAME_METHODS = {"go_to_scene": "go_to_scene", "restart_scene": "restart_scene", "quit": "quit_game",
                "play_sound": "play_sound", "show_message": "show_message", "save_value": "save_data",
                "load_value": "load_data"}
# object methods -> runtime helper taking the object first
OBJ_METHODS = {"show": "show_obj", "hide": "hide_obj", "enable": "enable_behaviour", "enabled": "behaviour_enabled",
               "behaviour": "behaviour", "has": "has_behaviour", "destroy": "destroy", "start": "timer_start",
               "stop": "timer_stop", "move_to": "move_to", "distance_to": "distance_to", "overlaps": "overlaps",
               "contains": "contains", "play": "play_anim", "has_animation": "has_animation",
               "emit": "emit_particles_from", "burst": "burst_from"}
STR_METHODS = {"upper": "to_upper", "lower": "to_lower", "strip": "strip_edges", "startswith": "begins_with",
               "endswith": "ends_with", "replace": "replace", "split": "split", "join": "join", "find": "find",
               "format": "format", "title": "capitalize", "isdigit": "is_valid_int", "zfill": "pad_zeros",
               "lstrip": "lstrip", "rstrip": "rstrip"}
LIST_METHODS = {"append": "append", "pop": "pop_back", "remove": "erase", "insert": "insert", "clear": "clear",
                "extend": "append_array", "index": "find", "count": "count", "sort": "sort", "reverse": "reverse",
                "copy": "duplicate", "get": "get", "keys": "keys", "values": "values", "update": "merge"}
SKIP_IMPORTS = {"math", "random", "radgame", "os", "sys", "pygame"}
# names of Node / Node2D / CanvasItem and of GDScript a translated script must not reuse
GD_RESERVED = {
    "var", "func", "const", "signal", "match", "extends", "class_name", "static", "enum", "self", "tool", "preload",
    "await", "yield", "in", "is", "as", "and", "or", "not", "PI", "TAU", "INF", "NAN", "breakpoint", "super",
    "print", "range", "len", "str", "int", "float", "bool", "max", "min", "abs", "sin", "cos", "tan", "sqrt",
    "pow", "floor", "ceil", "round", "load", "char", "type_string", "show", "hide", "draw", "queue_free",
    "get_name", "set_name", "rotate", "translate", "scale", "position", "name", "owner", "visible", "rotation",
    "transform", "modulate", "process_mode", "free", "get_parent", "add_child", "remove_child", "notification",
    "set", "get", "call", "emit_signal", "connect", "get_tree", "z_index", "global_position", "get_node",
    "has_node", "duplicate", "look_at", "to_local", "to_global", "get_viewport", "init", "ready", "update",
    "input", "skew", "material", "top_level", "Vector2", "Color", "Array", "Dictionary", "String", "Node",
    "Object", "Rect2", "OS", "Input", "Time", "JSON", "Engine", "randi", "randf", "lerp", "clamp", "sign",
    "wrap", "snapped", "deg_to_rad", "rad_to_deg", "is_instance_valid", "typeof", "instance_from_id", "hash",
    "str_to_var", "var_to_str", "get_class", "is_class", "has_method", "set_process", "get_index", "move_child",
    "pass", "return", "break", "continue", "if", "elif", "else", "for", "while", "true", "false", "null", "void",
}
OBJ_ATTRS = {"x", "y", "w", "h", "width", "height", "right", "bottom", "center", "rotation", "visible", "group",
             "name", "text", "vx", "vy", "alive", "data", "props", "on_ground", "z", "scale", "flip_x",
             "animation", "interval", "enabled", "spawned", "template", "hitbox", "angular_velocity"}

_PREC = {ast.Or: 1, ast.And: 2, ast.Not: 3, "cmp": 4, ast.BitOr: 5, ast.BitXor: 6, ast.BitAnd: 7,
         ast.LShift: 8, ast.RShift: 8, ast.Add: 9, ast.Sub: 9, ast.Mult: 10, ast.Div: 10, ast.Mod: 10,
         ast.FloorDiv: 10, "unary": 11, ast.Pow: 12}
_BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%", ast.BitOr: "|",
           ast.BitXor: "^", ast.BitAnd: "&", ast.LShift: "<<", ast.RShift: ">>"}
_CMPOPS = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
           ast.In: "in", ast.Is: "==", ast.IsNot: "!="}


class Untranslatable(Exception):
    pass


@dataclass
class Report:
    translated: int = 0                      # statements translated by the rules
    todo: list = field(default_factory=list)  # (line, python text) kept as comments
    ai: list = field(default_factory=list)    # (line, python text) translated by AI
    renamed: dict = field(default_factory=dict)

    def lines(self) -> list[str]:
        out = [f"{self.translated} statement(s) translated by rules"]
        if self.ai:
            out.append(f"{len(self.ai)} statement(s) translated by AI (marked '# AI:')")
        if self.todo:
            out.append(f"{len(self.todo)} statement(s) kept as '# TODO' comments (translate them by hand):")
            out += [f"  line {ln}: {txt.strip().splitlines()[0][:90]}" for ln, txt in self.todo[:30]]
        if self.renamed:
            out.append("renamed (names of the Godot runtime): " +
                       ", ".join(f"{a} -> {b}" for a, b in sorted(self.renamed.items())))
        return out


def runtime_taken() -> set[str]:
    try:
        from .godot_export import runtime_names
        names = runtime_names()
    except Exception:  # noqa: BLE001
        names = set()
    return names | GD_RESERVED


def _lit(node) -> bool:
    """A constant expression usable for a GDScript const."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _lit(node.operand)
    if isinstance(node, (ast.Tuple, ast.List)):
        return all(_lit(e) for e in node.elts)
    if isinstance(node, ast.BinOp):
        return _lit(node.left) and _lit(node.right)
    return False


# -------------------------------------------------------------------------------------------- translator
class Translator:
    def __init__(self, scene_name: str, code: str, scene: dict | None = None, ai=None):
        self.scene_name = scene_name
        self.code = code
        self.src = code.splitlines()
        self.scene = scene or {}
        self.ai = ai
        self.report = Report()
        self.objects = {o.get("name") for ly in self.scene.get("layers") or [] for o in ly.get("objects") or []
                        if o.get("name")}
        self.timers = {t.get("name") for t in self.scene.get("timers") or [] if t.get("name")}
        self.used_objects: set[str] = set()
        self.used_timers: set[str] = set()
        self.taken = runtime_taken()
        self.comments: dict[int, str] = {}
        self.full_comments: set[int] = set()
        self.module_vars: set[str] = set()
        self.module_funcs: set[str] = set()
        self.locals: set[str] = set()
        self.declared: set[str] = set()
        self.tmp = 0
        self._last_line = 0

    # ---- names
    def gd_name(self, name: str) -> str:
        if name in self.taken:
            self.report.renamed[name] = name + "_"
            return name + "_"
        return name

    def _scan_comments(self) -> None:
        try:
            for tok in tokenize.generate_tokens(io.StringIO(self.code).readline):
                if tok.type == tokenize.COMMENT:
                    line = tok.start[0]
                    self.comments[line] = tok.string.lstrip("#").strip()
                    if not self.src[line - 1][:tok.start[1]].strip():
                        self.full_comments.add(line)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass

    def _lead_comments(self, node, ind: str) -> list[str]:
        """Full-line comments between the previous statement and *node*."""
        out = []
        for ln in range(self._last_line + 1, node.lineno):
            if ln in self.full_comments:
                text = self.comments[ln]
                if text.startswith("noqa") or text.startswith("type:"):
                    continue
                out.append(f"{ind}# {text}" if text else f"{ind}#")
        return out

    def _tail(self, node) -> str:
        c = self.comments.get(node.lineno)
        if c and node.lineno not in self.full_comments and not c.startswith("noqa"):
            c = re.sub(r"\s*noqa.*$", "", c)
            return f"   # {c}" if c else ""
        return ""

    # ---- expressions
    def prec(self, node) -> int:
        if isinstance(node, ast.BoolOp):
            return _PREC[type(node.op)]
        if isinstance(node, ast.UnaryOp):
            return _PREC[ast.Not] if isinstance(node.op, ast.Not) else _PREC["unary"]
        if isinstance(node, ast.Compare):
            return _PREC["cmp"]
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.FloorDiv):
                return 99                      # becomes a call
            if isinstance(node.op, ast.Pow):
                return 99
            if isinstance(node.op, ast.Mod) and isinstance(node.left, (ast.Constant, ast.JoinedStr)) and \
                    isinstance(getattr(node.left, "value", None), str):
                return _PREC[ast.Mod]
            return _PREC.get(type(node.op), 0)
        if isinstance(node, ast.IfExp):
            return 0
        return 99

    def sub(self, node, parent_prec: int, right: bool = False) -> str:
        s = self.expr(node)
        p = self.prec(node)
        if p < parent_prec or (right and p == parent_prec and p < 99):
            return f"({s})"
        return s

    def is_object(self, node) -> bool:
        return isinstance(node, ast.Name) and (node.id in self.objects or node.id in self.timers)

    def expr(self, n) -> str:  # noqa: C901 - one case per node type
        if isinstance(n, ast.Constant):
            v = n.value
            if v is None:
                return "null"
            if v is True:
                return "true"
            if v is False:
                return "false"
            if isinstance(v, str):
                return json.dumps(v, ensure_ascii=False)
            if isinstance(v, (int, float)):
                return repr(v)
            raise Untranslatable(f"constant {v!r}")
        if isinstance(n, ast.Name):
            if n.id in self.objects:
                self.used_objects.add(n.id)
                return n.id
            if n.id in self.timers:
                self.used_timers.add(n.id)
                return n.id
            if n.id == "game":
                return "self"
            return self.gd_name(n.id)
        if isinstance(n, ast.Attribute):
            return self.attribute(n)
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.FloorDiv):
                if isinstance(n.right, ast.Constant) and type(n.right.value) is int:
                    return f"floori({self.sub(n.left, 10)} / {n.right.value}.0)"
                return f"floori({self.sub(n.left, 10)} / float({self.expr(n.right)}))"
            if isinstance(n.op, ast.Pow):
                return f"pow({self.expr(n.left)}, {self.expr(n.right)})"
            if isinstance(n.op, ast.MatMult):
                raise Untranslatable("@ operator")
            p = self.prec(n)
            op = _BINOPS[type(n.op)]
            right = n.right
            if isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
                r = self.expr(right)
                if isinstance(right, ast.Tuple):
                    r = "[" + ", ".join(self.expr(e) for e in right.elts) + "]"
                return f"{self.expr(n.left)} % {r}"
            return f"{self.sub(n.left, p)} {op} {self.sub(right, p, right=True)}"
        if isinstance(n, ast.UnaryOp):
            if isinstance(n.op, ast.Not):
                return f"not {self.sub(n.operand, _PREC[ast.Not])}"
            op = {ast.USub: "-", ast.UAdd: "+", ast.Invert: "~"}[type(n.op)]
            return f"{op}{self.sub(n.operand, _PREC['unary'])}"
        if isinstance(n, ast.BoolOp):
            p = self.prec(n)
            op = " and " if isinstance(n.op, ast.And) else " or "
            return op.join(self.sub(v, p, right=i > 0) for i, v in enumerate(n.values))
        if isinstance(n, ast.Compare):
            parts = []
            left = n.left
            for op, right in zip(n.ops, n.comparators):
                if isinstance(op, ast.NotIn):
                    parts.append(f"not ({self.sub(left, 5)} in {self.sub(right, 5)})")
                else:
                    parts.append(f"{self.sub(left, 5)} {_CMPOPS[type(op)]} {self.sub(right, 5)}")
                left = right
            return " and ".join(parts) if len(parts) == 1 else " and ".join(f"({p})" for p in parts)
        if isinstance(n, ast.IfExp):
            return f"{self.sub(n.body, 1)} if {self.sub(n.test, 1)} else {self.sub(n.orelse, 0)}"
        if isinstance(n, (ast.List, ast.Tuple)):
            if any(isinstance(e, ast.Starred) for e in n.elts):
                raise Untranslatable("*unpacking")
            return "[" + ", ".join(self.expr(e) for e in n.elts) + "]"
        if isinstance(n, ast.Dict):
            if any(k is None for k in n.keys):
                raise Untranslatable("**unpacking")
            return "{" + ", ".join(f"{self.expr(k)}: {self.expr(v)}" for k, v in zip(n.keys, n.values)) + "}"
        if isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Slice):
                s = n.slice
                if s.step is not None:
                    raise Untranslatable("slice step")
                lo = self.expr(s.lower) if s.lower is not None else "0"
                if s.upper is None:
                    return f"{self.sub(n.value, 99)}.slice({lo})"
                return f"{self.sub(n.value, 99)}.slice({lo}, {self.expr(s.upper)})"
            return f"{self.sub(n.value, 99)}[{self.expr(n.slice)}]"
        if isinstance(n, ast.Call):
            return self.call(n)
        if isinstance(n, ast.JoinedStr):
            return self.fstring(n)
        raise Untranslatable(type(n).__name__)

    def fstring(self, n: ast.JoinedStr) -> str:
        parts = []
        for v in n.values:
            if isinstance(v, ast.Constant):
                parts.append(json.dumps(str(v.value), ensure_ascii=False))
            elif isinstance(v, ast.FormattedValue):
                inner = self.expr(v.value)
                spec = ""
                if v.format_spec is not None:
                    spec = "".join(str(x.value) for x in v.format_spec.values if isinstance(x, ast.Constant))
                if spec and re.fullmatch(r"0?\d*(\.\d+)?[dfsx]", spec):
                    parts.append(f'("%{spec}" % {inner})')
                elif spec:
                    raise Untranslatable(f"format spec {spec!r}")
                else:
                    parts.append(f"str({inner})")
        return " + ".join(parts) if parts else '""'

    def attribute(self, n: ast.Attribute) -> str:
        v = n.value
        if isinstance(v, ast.Name) and v.id == "game":
            if n.attr in GAME_ATTRS:
                return GAME_ATTRS[n.attr]
            raise Untranslatable(f"game.{n.attr}")
        if isinstance(v, ast.Name) and v.id == "math":
            if n.attr in MATH_CONSTS:
                return MATH_CONSTS[n.attr]
            raise Untranslatable(f"math.{n.attr}")
        return f'getp({self.expr(v)}, "{n.attr}")'

    def args(self, n: ast.Call) -> list[str]:
        if n.keywords:
            raise Untranslatable("keyword arguments")
        if any(isinstance(a, ast.Starred) for a in n.args):
            raise Untranslatable("*args")
        return [self.expr(a) for a in n.args]

    def call(self, n: ast.Call) -> str:  # noqa: C901
        f = n.func
        if isinstance(f, ast.Name):
            name = f.id
            if name in API_FUNCS and name not in self.module_funcs:
                a = self.args(n)
                if name == "Random" and len(a) == 2:
                    return f"randi_range(int({a[0]}), int({a[1]}))"
                if name == "Destroy" and a:
                    return f"destroy({a[0]})"
                return f"{API_FUNCS[name]}({', '.join(a)})"
            if name in self.module_funcs:
                return f"{self.gd_name(name)}({', '.join(self.args(n))})"
            if name in PY_FUNCS:
                a = self.args(n)
                if name == "round" and len(a) == 2:
                    return f"snappedf({a[0]}, pow(10, -{a[1]}))"
                if name == "int" and len(a) == 1:
                    return f"int({a[0]})"
                if name == "str" and not a:
                    return '""'
                return f"{PY_FUNCS[name]}({', '.join(a)})"
            if name == "list" and len(n.args) == 1:
                return f"Array({self.expr(n.args[0])})"
            if name == "dict" and not n.args and not n.keywords:
                return "{}"
            if name == "sum" and len(n.args) == 1 and not isinstance(n.args[0], (ast.GeneratorExp, ast.ListComp)):
                return f"{self.sub(n.args[0], 99)}.reduce(func(a, b): return a + b, 0)"
            if name == "isinstance":
                raise Untranslatable("isinstance")
            raise Untranslatable(f"call of {name}()")
        if isinstance(f, ast.Attribute):
            recv, m = f.value, f.attr
            if isinstance(recv, ast.Name) and recv.id == "math":
                fn = MATH_FUNCS.get(m)
                if not fn:
                    if m == "hypot" and len(n.args) == 2:
                        a = self.args(n)
                        return f"Vector2({a[0]}, {a[1]}).length()"
                    raise Untranslatable(f"math.{m}")
                return f"{fn}({', '.join(self.args(n))})"
            if isinstance(recv, ast.Name) and recv.id == "random":
                if m in RANDOM_FUNCS:
                    a = self.args(n)
                    if m == "randint":
                        return f"randi_range(int({a[0]}), int({a[1]}))"
                    return f"{RANDOM_FUNCS[m]}({', '.join(a)})"
                if m == "choice" and len(n.args) == 1:
                    return f"{self.sub(n.args[0], 99)}.pick_random()"
                raise Untranslatable(f"random.{m}")
            if isinstance(recv, ast.Name) and recv.id == "game":
                if m in GAME_METHODS:
                    return f"{GAME_METHODS[m]}({', '.join(self.args(n))})"
                raise Untranslatable(f"game.{m}()")
            if isinstance(recv, ast.Attribute) and isinstance(recv.value, ast.Name) and recv.value.id == "game" \
                    and recv.attr == "vars":
                r = "vars"
                a = self.args(n)
                if m in ("get", "keys", "values", "has", "clear", "erase"):
                    return f"{r}.{m}({', '.join(a)})"
                if m == "pop" and a:
                    return f"dict_pop({r}, {', '.join(a)})"
                if m == "update":
                    return f"{r}.merge({a[0]}, true)"
            obj = self.is_object(recv) or (m in OBJ_METHODS and m not in STR_METHODS and m not in LIST_METHODS)
            if obj and m in OBJ_METHODS:
                a = self.args(n)
                if m in ("start", "stop") and a:
                    raise Untranslatable(f".{m}(...)")
                return f"{OBJ_METHODS[m]}({', '.join([self.expr(recv)] + a)})"
            if self.is_object(recv):
                raise Untranslatable(f"{recv.id}.{m}()")
            a = self.args(n)
            r = self.sub(recv, 99)
            if m == "items" and not a:
                raise Untranslatable(".items() outside a for loop")
            if m == "pop":
                if len(a) == 2 or (a and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                    return f"dict_pop({r}, {', '.join(a)})"          # dict.pop(key[, default])
                return f"{r}.pop_at({a[0]})" if a else f"{r}.pop_back()"
            if m == "update":
                return f"{r}.merge({a[0]}, true)"
            if m == "format":
                fmt = recv
                if isinstance(fmt, ast.Constant) and isinstance(fmt.value, str):
                    i = iter(range(1000))
                    text = re.sub(r"\{\}", lambda _m: "{%d}" % next(i), fmt.value)
                    return f"{json.dumps(text, ensure_ascii=False)}.format([{', '.join(a)}])"
                raise Untranslatable("str.format")
            if m == "join" and len(a) == 1:
                return f"{r}.join(PackedStringArray({a[0]}))"
            if m in STR_METHODS:
                return f"{r}.{STR_METHODS[m]}({', '.join(a)})"
            if m in LIST_METHODS:
                return f"{r}.{LIST_METHODS[m]}({', '.join(a)})"
            raise Untranslatable(f".{m}()")
        raise Untranslatable("call")

    # ---- statements
    def fallback(self, node, ind: str, why: str) -> list[str]:
        text = "\n".join(self.src[node.lineno - 1:getattr(node, "end_lineno", node.lineno)])
        base = min((len(ln) - len(ln.lstrip()) for ln in text.splitlines() if ln.strip()), default=0)
        snippet = "\n".join(ln[base:] for ln in text.splitlines())
        if self.ai is not None:
            try:
                gd = self.ai(snippet, f"GDScript 4 for a RAD IDE scene script that extends radgame_scene.gd "
                                      f"(helpers: getp(obj, attr), setp(obj, attr, v), spawn, destroy, add_score, "
                                      f"play_sound, save_data, load_data, find_group, enable_behaviour_all). "
                                      f"Python could not be translated by rules: {why}")
            except Exception:  # noqa: BLE001
                gd = None
            if gd and gd.strip():
                self.report.ai.append((node.lineno, snippet))
                out = [f"{ind}# AI: translated from Python line {node.lineno} (check it)"]
                out += [ind + ln.replace("    ", "\t") for ln in gd.strip("\n").splitlines()]
                return out
        self.report.todo.append((node.lineno, snippet))
        out = [f"{ind}# TODO translate (Python line {node.lineno}: {why}):"]
        out += [f"{ind}# {ln}" for ln in snippet.splitlines()]
        return out

    def block(self, body, ind: str) -> list[str]:
        out = []
        for s in body:
            out += self.stmt(s, ind)
        if not any(ln.strip() and not ln.strip().startswith("#") for ln in out):
            out.append(f"{ind}pass")
        return out

    def stmt(self, s, ind: str) -> list[str]:
        lead = self._lead_comments(s, ind)
        self._last_line = max(self._last_line, s.lineno)
        try:
            body = self._stmt(s, ind)
            if not isinstance(s, (ast.If, ast.For, ast.While, ast.FunctionDef)):
                self.report.translated += 1
        except Untranslatable as e:
            body = self.fallback(s, ind, str(e))
        self._last_line = max(self._last_line, getattr(s, "end_lineno", s.lineno))
        return lead + body

    def _target(self, t, value: str, ind: str, aug: str | None = None) -> list[str]:
        """Assignment to one target (Name / Attribute / Subscript)."""
        if isinstance(t, ast.Name):
            if t.id in self.objects or t.id in self.timers:
                raise Untranslatable(f"assignment to the scene object {t.id}")
            name = self.gd_name(t.id)
            if aug:
                return [f"{ind}{name} {aug}= {value}" if aug != "//" else
                        f"{ind}{name} = floori({name} / float({value}))"]
            if t.id in self.locals and t.id not in self.declared:
                self.declared.add(t.id)
                return [f"{ind}var {name} = {value}"]
            return [f"{ind}{name} = {value}"]
        if isinstance(t, ast.Attribute):
            if isinstance(t.value, ast.Name) and t.value.id == "game":
                if t.attr not in GAME_ATTRS or t.attr == "time":
                    raise Untranslatable(f"game.{t.attr} =")
                g = GAME_ATTRS[t.attr]
                if aug == "//":
                    return [f"{ind}{g} = floori({g} / float({value}))"]
                return [f"{ind}{g} {aug or ''}= {value}"]
            o = self.expr(t.value)
            if aug:
                op = {"//": None}.get(aug, aug)
                cur = f'getp({o}, "{t.attr}")'
                new = f"floori({cur} / float({value}))" if op is None else f"{cur} {aug} {value}"
                return [f'{ind}setp({o}, "{t.attr}", {new})']
            return [f'{ind}setp({o}, "{t.attr}", {value})']
        if isinstance(t, ast.Subscript):
            target = self.expr(t)
            if aug == "//":
                return [f"{ind}{target} = floori({target} / float({value}))"]
            return [f"{ind}{target} {aug or ''}= {value}"]
        raise Untranslatable("assignment target")

    def _stmt(self, s, ind: str) -> list[str]:  # noqa: C901
        tail = self._tail(s)
        if isinstance(s, ast.Expr):
            if isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                return [f"{ind}# {ln}".rstrip() for ln in s.value.value.strip().splitlines()]
            if not isinstance(s.value, ast.Call):
                raise Untranslatable("expression statement")
            return [f"{ind}{self.expr(s.value)}{tail}"]
        if isinstance(s, (ast.Assign, ast.AnnAssign)):
            targets = s.targets if isinstance(s, ast.Assign) else [s.target]
            if s.value is None:
                return [f"{ind}var {self.gd_name(s.target.id)}"] if isinstance(s.target, ast.Name) else []
            if isinstance(s.value, ast.ListComp) and len(targets) == 1 and isinstance(targets[0], ast.Name):
                return self._listcomp(targets[0], s.value, ind)
            out = []
            for t in targets:
                if isinstance(t, (ast.Tuple, ast.List)):
                    out += self._unpack(t, s.value, ind)
                else:
                    out += self._target(t, self.expr(s.value), ind)
            if out:
                out[-1] += tail
            return out
        if isinstance(s, ast.AugAssign):
            if isinstance(s.op, ast.Pow):
                raise Untranslatable("**=")
            op = "//" if isinstance(s.op, ast.FloorDiv) else _BINOPS[type(s.op)]
            out = self._target(s.target, self.expr(s.value) if op != "//" else self.expr(s.value), ind, aug=op)
            out[-1] += tail
            return out
        if isinstance(s, ast.If):
            out = [f"{ind}if {self.expr(s.test)}:{tail}"]
            out += self.block(s.body, ind + "\t")
            orelse = s.orelse
            while len(orelse) == 1 and isinstance(orelse[0], ast.If):
                e = orelse[0]
                out += self._lead_comments(e, ind)
                self._last_line = max(self._last_line, e.lineno)
                out.append(f"{ind}elif {self.expr(e.test)}:{self._tail(e)}")
                out += self.block(e.body, ind + "\t")
                orelse = e.orelse
            if orelse:
                out.append(f"{ind}else:")
                out += self.block(orelse, ind + "\t")
            return out
        if isinstance(s, ast.While):
            if s.orelse:
                raise Untranslatable("while ... else")
            return [f"{ind}while {self.expr(s.test)}:{tail}"] + self.block(s.body, ind + "\t")
        if isinstance(s, ast.For):
            if s.orelse:
                raise Untranslatable("for ... else")
            it = s.iter
            if isinstance(s.target, ast.Name):
                head = f"{ind}for {self.gd_name(s.target.id)} in {self.expr(it)}:{tail}"
                return [head] + self.block(s.body, ind + "\t")
            if isinstance(s.target, ast.Tuple) and len(s.target.elts) == 2 and all(
                    isinstance(e, ast.Name) for e in s.target.elts):
                k, v = (self.gd_name(e.id) for e in s.target.elts)
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr == "items":
                    d = self.sub(it.func.value, 99)
                    head = [f"{ind}for {k} in {d}:{tail}", f"{ind}\tvar {v} = {d}[{k}]"]
                    return head + self.block(s.body, ind + "\t")
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "enumerate" \
                        and len(it.args) == 1:
                    seq = self.sub(it.args[0], 99)
                    head = [f"{ind}for {k} in range(len({seq})):{tail}", f"{ind}\tvar {v} = {seq}[{k}]"]
                    return head + self.block(s.body, ind + "\t")
            raise Untranslatable("for with several targets")
        if isinstance(s, ast.Return):
            return [f"{ind}return" + (f" {self.expr(s.value)}" if s.value is not None else "") + tail]
        if isinstance(s, ast.Pass):
            return [f"{ind}pass{tail}"]
        if isinstance(s, ast.Break):
            return [f"{ind}break{tail}"]
        if isinstance(s, ast.Continue):
            return [f"{ind}continue{tail}"]
        if isinstance(s, (ast.Global, ast.Nonlocal)):
            return []
        if isinstance(s, (ast.Import, ast.ImportFrom)):
            mod = s.module if isinstance(s, ast.ImportFrom) else s.names[0].name
            mod = (mod or "").split(".")[0]
            if mod in SKIP_IMPORTS or mod.endswith("_designer"):
                return []
            raise Untranslatable(f"import {mod}")
        if isinstance(s, ast.Assert):
            return [f"{ind}assert({self.expr(s.test)}){tail}"]
        if isinstance(s, ast.Delete):
            out = []
            for t in s.targets:
                if isinstance(t, ast.Subscript) and not isinstance(t.slice, ast.Slice):
                    out.append(f"{ind}{self.sub(t.value, 99)}.erase({self.expr(t.slice)})")
                else:
                    raise Untranslatable("del")
            return out
        raise Untranslatable(type(s).__name__)

    def _unpack(self, t, value, ind: str) -> list[str]:
        elts = t.elts
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(elts):
            names = {e.id for e in elts if isinstance(e, ast.Name)}
            reads = {n.id for v in value.elts for n in ast.walk(v) if isinstance(n, ast.Name)}
            vals = [self.expr(v) for v in value.elts]
            out = []
            if names & reads:                  # a, b = b, a: through temporaries
                tmps = []
                for v in vals:
                    self.tmp += 1
                    tmps.append(f"_t{self.tmp}")
                    out.append(f"{ind}var {tmps[-1]} = {v}")
                vals = tmps
            for e, v in zip(elts, vals):
                out += self._target(e, v, ind)
            return out
        self.tmp += 1
        tmp = f"_t{self.tmp}"
        out = [f"{ind}var {tmp} = {self.expr(value)}"]
        for i, e in enumerate(elts):
            out += self._target(e, f"{tmp}[{i}]", ind)
        return out

    def _listcomp(self, target, comp: ast.ListComp, ind: str) -> list[str]:
        if len(comp.generators) != 1 or comp.generators[0].is_async:
            raise Untranslatable("nested comprehension")
        g = comp.generators[0]
        if not isinstance(g.target, ast.Name):
            raise Untranslatable("comprehension target")
        out = self._target(target, "[]", ind)
        name = self.gd_name(target.id)
        out.append(f"{ind}for {self.gd_name(g.target.id)} in {self.expr(g.iter)}:")
        inner = ind + "\t"
        for cond in g.ifs:
            out.append(f"{inner}if {self.expr(cond)}:")
            inner += "\t"
        out.append(f"{inner}{name}.append({self.expr(comp.elt)})")
        return out

    # ---- functions / module
    def function(self, fn: ast.FunctionDef) -> list[str]:
        if fn.decorator_list:
            raise Untranslatable("decorators")
        a = fn.args
        if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs:
            raise Untranslatable("special parameters")
        params = [p.arg for p in a.args]
        defaults = [None] * (len(params) - len(a.defaults)) + list(a.defaults)
        ps = []
        for p, d in zip(params, defaults):
            ps.append(self.gd_name(p) + (f" = {self.expr(d)}" if d is not None else ""))
        globals_ = {n for s in ast.walk(fn) if isinstance(s, ast.Global) for n in s.names}
        assigned = set()
        for s in ast.walk(fn):
            if isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                ts = s.targets if isinstance(s, ast.Assign) else [s.target]
                for t in ts:
                    for e in ([t] if isinstance(t, ast.Name) else getattr(t, "elts", [])):
                        if isinstance(e, ast.Name):
                            assigned.add(e.id)
        loop_vars = {s.target.id for s in ast.walk(fn) if isinstance(s, ast.For) and isinstance(s.target, ast.Name)}
        self.locals = assigned - globals_ - set(params) - loop_vars
        self.declared = set()
        # hoist locals whose first assignment is not at the top level of the function
        top_first = set()
        seen = set()
        for s in fn.body:
            for node in ast.walk(s):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in self.locals \
                        and node.id not in seen:
                    seen.add(node.id)
                    if isinstance(s, (ast.Assign, ast.AnnAssign)) and node in [
                            x for t in (s.targets if isinstance(s, ast.Assign) else [s.target])
                            for x in ([t] if isinstance(t, ast.Name) else getattr(t, "elts", []))]:
                        top_first.add(node.id)
        hoisted = sorted(self.locals - top_first)
        doc = ast.get_docstring(fn)
        out = []
        ret = ""
        out.append(f"func {self.gd_name(fn.name)}({', '.join(ps)}){ret}:{self._tail(fn)}")
        body = list(fn.body)
        self._last_line = fn.lineno
        if doc and body and isinstance(body[0], ast.Expr):
            out += [f"\t# {ln}".rstrip() for ln in doc.splitlines()]
            self._last_line = body[0].end_lineno
            body = body[1:]
        for h in hoisted:
            out.append(f"\tvar {self.gd_name(h)}")
            self.declared.add(h)
        out += self.block(body, "\t")
        self.locals = set()
        return out

    def translate(self) -> str:
        self._scan_comments()
        try:
            tree = ast.parse(self.code)
        except SyntaxError as e:
            self.report.todo.append((e.lineno or 0, f"syntax error: {e}"))
            return self.header() + [f"# the Python code has a syntax error ({e}); nothing was translated", ""]
        self.module_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        globals_ = {n for s in ast.walk(tree) if isinstance(s, ast.Global) for n in s.names}
        body_lines: list[str] = []
        doc = ast.get_docstring(tree)
        stmts = list(tree.body)
        if doc and stmts and isinstance(stmts[0], ast.Expr):
            self._last_line = stmts[0].end_lineno
            stmts = stmts[1:]
        decls: list[str] = []
        for s in stmts:
            if isinstance(s, ast.FunctionDef):
                lead = self._lead_comments(s, "")
                body_lines += ["", ""] + lead
                try:
                    body_lines += self.function(s)
                except Untranslatable as e:
                    body_lines += self.fallback(s, "", str(e))
                self._last_line = s.end_lineno
            elif isinstance(s, (ast.Assign, ast.AnnAssign)) and not isinstance(s.value, ast.ListComp):
                lead = self._lead_comments(s, "")
                self._last_line = s.end_lineno
                targets = s.targets if isinstance(s, ast.Assign) else [s.target]
                try:
                    decls += lead + self._module_assign(targets, s.value, globals_, self._tail(s))
                    self.report.translated += 1
                except Untranslatable as e:
                    decls += self.fallback(s, "", str(e))
            elif isinstance(s, (ast.Import, ast.ImportFrom)):
                try:
                    decls += self._stmt(s, "")
                except Untranslatable as e:
                    decls += self.fallback(s, "", str(e))
                self._last_line = s.end_lineno
            elif isinstance(s, ast.If) and isinstance(s.test, ast.Compare) and \
                    isinstance(s.test.left, ast.Name) and s.test.left.id == "__name__":
                self._last_line = s.end_lineno
            else:
                decls += self.fallback(s, "", f"module-level {type(s).__name__}")
                self._last_line = s.end_lineno
        out = self.header(doc)
        refs = []
        for o in sorted(self.used_objects):
            refs += [f"var {o}: Node:", "\tget:", f'\t\treturn find("{o}")']
        for t in sorted(self.used_timers):
            refs += [f"var {t}: Dictionary:", "\tget:", f'\t\treturn timers.get("{t}", {{}})']
        if refs:
            out += ["", "# the objects of the scene used by this code (as in <Scene>_designer.py)"] + refs
        if decls:
            out += [""] + decls
        out += body_lines
        return out

    def _module_assign(self, targets, value, globals_, tail: str) -> list[str]:
        out = []
        for t in targets:
            if isinstance(t, ast.Name):
                pairs = [(t, value)]
            elif isinstance(t, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) and \
                    len(t.elts) == len(value.elts) and all(isinstance(e, ast.Name) for e in t.elts):
                pairs = list(zip(t.elts, value.elts))
            else:
                raise Untranslatable("module-level assignment")
            for name, v in pairs:
                kw = "const" if (name.id.isupper() and name.id not in globals_ and _lit(v)) else "var"
                self.module_vars.add(name.id)
                out.append(f"{kw} {self.gd_name(name.id)} = {self.expr(v)}")
        if out:
            out[-1] += tail
        return out

    def header(self, doc: str | None = None) -> list[str]:
        out = [f"# {self.scene_name} - translated from {self.scene_name}.py by RAD IDE (Export to Godot).",
               "# Edit freely: this file is created once and kept on the next export. The scene "
               f"{self.scene_name}.tscn is generated from {self.scene_name}.scene."]
        if doc:
            out += ["#"] + [f"# {ln}".rstrip() for ln in doc.splitlines()]
        out.append('extends "res://radgame/radgame_scene.gd"')
        return out


def translate(scene_name: str, code: str, scene: dict | None = None, ai=None) -> tuple[str, Report]:
    """Python scene code -> (GDScript text, Report)."""
    t = Translator(scene_name, code, scene, ai)
    lines = t.translate()
    text = "\n".join(lines).rstrip("\n") + "\n"
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text, t.report


def ai_configured() -> bool:
    """True when the user chose an AI provider for editing / chat (Tools > Options > AI)."""
    try:
        from .. import ai
        s = ai.settings()
        return bool(s.value("ai/default/edit/provider", "") or s.value("ai/default/chat/provider", ""))
    except Exception:  # noqa: BLE001
        return False


def ai_translator(timeout: float = 120):
    """A callable for ``translate(ai=...)`` that asks the user's AI provider, or None when no provider is
    configured or available."""
    if not ai_configured():
        return None
    try:
        from .. import ai
        p, model = ai.default("edit")
        ok, _why = p.available()
        if not ok:
            return None
    except Exception:  # noqa: BLE001
        return None

    def run(snippet: str, context: str) -> str | None:
        prompt = ("Translate this Python (pygame radgame API) into GDScript 4. Answer with ONE code block, "
                  "no explanations, use tabs for indentation, keep the same names.\n"
                  f"Context: {context}\n```python\n{snippet}\n```")
        job = p.chat([ai.Message("user", prompt)], model=model or None,
                     system="You translate small game code snippets from Python to Godot 4 GDScript.")
        text = ai.run_sync(job, timeout=timeout)
        blocks = ai.extract_code_blocks(text)
        return blocks[0][1] if blocks else None
    return run


__all__ = ["translate", "Translator", "Report", "Untranslatable", "ai_translator", "ai_configured", "API_FUNCS"]
