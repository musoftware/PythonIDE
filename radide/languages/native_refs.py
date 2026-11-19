"""References (docs/CONTRACTS.md section 7) for the native languages: C, C++, Rust, Fortran, Go.

Library side: parse the public functions of a code file (with their parameter *types*, so that
the RAD Hub worker can convert the JSON arguments and call plain native functions such as
``double Add(double a, double b)``).
Consumer side: generate proxy files whose functions forward to the language's radcall client.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..references import ExportedFunction, is_proxy_file, proxy_header

# ============================================================================ common
_EVENTS: set[str] | None = None


def _event_names() -> set[str]:
    names = {"click", "load", "change", "textchanged", "tick", "dblclick", "doubleclick", "unload",
             "selectedindexchanged", "valuechanged", "checkedchanged", "resize", "cellchanged"}
    try:
        from ..controls import CONTROL_TYPES, FORM_EVENTS
        names |= {e.lower() for e in FORM_EVENTS}
        for ct in CONTROL_TYPES.values():
            names |= {e.lower() for e in ct.all_events()}
    except Exception:  # noqa: BLE001 - the control catalogue is edited by other agents
        pass
    return names


def is_handler(name: str) -> bool:
    """True for event handler names <Owner>_<Event> (cmdGo_Click, Form1_Load)."""
    global _EVENTS
    if "_" not in name.strip("_"):
        return False
    if _EVENTS is None:
        _EVENTS = _event_names()
    return name.rsplit("_", 1)[1].lower() in _EVENTS


def is_public_name(name: str) -> bool:
    return bool(name) and not name.startswith("_") and not is_handler(name) and \
        not name.lower().startswith(("rad_", "radcall"))


def ident(name: str, reserved: set[str] | frozenset = frozenset(), suffix: str = "_") -> str:
    """A valid identifier made from *name* (keywords get *suffix*)."""
    n = re.sub(r"\W", "_", str(name).lstrip("*&@$%.")) or "arg"
    if n[0].isdigit():
        n = "a" + n
    while n in reserved:
        n += suffix
    return n


def unique_params(params: list[str], reserved: set[str] | frozenset = frozenset(),
                  lower: bool = False) -> list[str]:
    out: list[str] = []
    for i, p in enumerate(params):
        n = ident(p, reserved) if p else f"a{i + 1}"
        key = n.lower() if lower else n
        while key in ((x.lower() for x in out) if lower else out):
            n += "_"
            key = n.lower() if lower else n
        out.append(n)
    return out


def blank_code(text: str, line: str = "//", block: tuple[str, str] | None = ("/*", "*/"),
               quotes: str = "\"'", raw_lifetimes: bool = False) -> str:
    """Replace comments and the inside of string literals by spaces (same length, newlines kept),
    so that positions in the result match the original text."""
    out = list(text)
    i, n = 0, len(text)

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "
    while i < n:
        c = text[i]
        if line and text.startswith(line, i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif block and text.startswith(block[0], i):
            j = text.find(block[1], i + len(block[0]))
            j = n if j < 0 else j + len(block[1])
            blank(i, j)
            i = j
        elif c in quotes:
            if raw_lifetimes and c == "'":
                m = re.match(r"'(\\.[^']*|[^\\'])'", text[i:])
                if not m:                       # a lifetime ('a) - not a char literal
                    i += 1
                    continue
                blank(i + 1, i + m.end() - 1)
                i += m.end()
                continue
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            blank(i + 1, j)
            i = j + 1
        else:
            i += 1
    return "".join(out)


def doc_before(text: str, pos: int, line: str = "//", block: tuple[str, str] | None = ("/*", "*/")) -> str:
    """First meaningful line of the comment right above position *pos* of *text*."""
    before = text[:pos].rstrip()
    lines: list[str] = []
    if block and before.endswith(block[1]):
        start = before.rfind(block[0])
        if start >= 0:
            lines = before[start + len(block[0]):-len(block[1])].splitlines()
    else:
        for ln in reversed(before.splitlines()):
            s = ln.strip()
            if not s.startswith(line):
                break
            lines.insert(0, s[len(line):])
    for ln in lines:
        s = ln.strip().lstrip("*!/").strip()
        if s and not set(s) <= set("-=*#/!"):
            return s
    return ""


def split_top(text: str, sep: str = ",") -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [p.strip() for p in out if p.strip()]


def target_of(fn: ExportedFunction) -> str:
    return f"{fn.module}.{fn.name}" if fn.module else fn.name


def c_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def proxy_files(folder: Path, project, exts: tuple[str, ...]) -> list[str]:
    """Generated reference proxy files (relative names) of a project with one of *exts*."""
    out: list[str] = []
    for files in (getattr(project, "reference_files", None) or {}).values():
        for f in files:
            if f.lower().endswith(exts) and (Path(folder) / f).is_file() and f not in out:
                out.append(f)
    try:
        for p in sorted(Path(folder).iterdir()):
            if p.is_file() and p.name.lower().endswith(exts) and p.name not in out and \
                    (".ref." in p.name or p.stem.endswith("_ref")) and is_proxy_file(p):
                out.append(p.name)
    except OSError:
        pass
    return out


def proxy_extra(fn: ExportedFunction) -> str:
    """'name(a, b) - doc' for comments."""
    return f"{fn.name}({', '.join(fn.params)})" + (f" - {fn.doc}" if fn.doc else "")


# ============================================================================ C / C++ library side
C_RESERVED = set("""auto break case char const continue default do double else enum extern float for goto if
    inline int long register restrict return short signed sizeof static struct switch typedef union unsigned
    void volatile while bool true false alignas alignof asm catch class constexpr decltype delete explicit
    export friend mutable namespace new noexcept nullptr operator private protected public template this
    throw try typeid typename using virtual main""".split())
_NUM_TYPES = {"int", "long", "short", "unsigned", "signed", "float", "double", "size_t", "ssize_t",
              "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
              "intptr_t", "uintptr_t", "ptrdiff_t"}


@dataclass
class CFunc:
    name: str
    ret: str                                   # return type text ("" for RADFUNC)
    params: list[tuple[str, str]] = field(default_factory=list)   # (type, name)
    param_text: str = ""
    radfunc: bool = False
    nargs: int = 0                             # RADFUNC: highest argv index + 1
    extern_c: bool = False
    doc: str = ""
    pos: int = 0


def c_type_kind(t: str, cpp: bool) -> str | None:
    """num | bool | str (char*) | cppstr | json (rad::Value) | void | None (unsupported)."""
    s = re.sub(r"\b(const|volatile|register|struct)\b", " ", t)
    s = re.sub(r"\s+", " ", s).strip()
    stars = s.count("*")
    ref = "&" in s
    base = s.replace("*", " ").replace("&", " ").split()
    if not base:
        return None
    if base == ["void"] and not stars:
        return "void"
    if cpp and base in (["std::string"], ["string"]) and not stars:
        return "cppstr"
    if cpp and base in (["rad::Value"],) and not stars:
        return "json"
    if ref:
        return None
    if base == ["char"] and stars == 1:
        return "str"
    if stars:
        return None
    if base in (["bool"], ["_Bool"]):
        return "bool"
    if all(b in _NUM_TYPES for b in base):
        return "num"
    return None


def _c_param(p: str) -> tuple[str, str] | None:
    p = p.split("=")[0].strip()                 # C++ default argument
    p = re.sub(r"\[\s*\]$", "*", p)
    m = re.match(r"^(.*?)([A-Za-z_]\w*)\s*$", p, re.S)
    if not m or not m.group(1).strip():
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip(), m.group(2)


def c_functions(text: str, cpp: bool = False, header: bool = False) -> list[CFunc]:
    """Top-level function definitions (and, for headers, prototypes) of C/C++ source text."""
    clean = blank_code(text)
    clean = re.sub(r"(?m)^[ \t]*#(?:.*\\\n)*.*$", lambda m: re.sub(r"[^\n]", " ", m.group(0)), clean)
    out: list[CFunc] = []
    n = len(clean)
    i, start, extern_c = 0, 0, 0               # extern "C" { ... } blocks are transparent
    rx = re.compile(r"^(?P<ret>.*?)\b(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^()]*)\)\s*"
                    r"(?:const\s*|noexcept\s*|throw\s*\(\s*\)\s*)*$", re.S)

    def header_of(a: int, b: int):
        seg = clean[a:b]
        lead = len(seg) - len(seg.lstrip())
        return seg.strip(), a + lead
    while i < n:
        c = clean[i]
        if c == "{":
            seg, segpos = header_of(start, i)
            if re.fullmatch(r'extern\s*"\s*"', seg):
                extern_c += 1
                i += 1
                start = i
                continue
            m = rx.match(seg)
            body_end = _match_brace(clean, i)
            if m:
                f = _c_func(m, segpos, text, cpp, extern_c > 0)
                if f is not None:
                    if f.radfunc:
                        body = clean[i:body_end]
                        idx = [int(x) for x in re.findall(r"\bargv\s*\[\s*(\d+)\s*\]", body)]
                        f.nargs = max(idx) + 1 if idx else 0
                    out.append(f)
            i = body_end
            start = i
            continue
        if c == "}":
            if extern_c:
                extern_c -= 1
            start = i + 1
        elif c == ";":
            if header:
                seg, segpos = header_of(start, i)
                m = rx.match(seg)
                if m and "(" not in m.group("ret") and "=" not in m.group("ret"):
                    f = _c_func(m, segpos, text, cpp, extern_c > 0)
                    if f is not None and not f.radfunc:
                        out.append(f)
            start = i + 1
        i += 1
    return out


def _match_brace(clean: str, i: int) -> int:
    depth = 0
    for j in range(i, len(clean)):
        if clean[j] == "{":
            depth += 1
        elif clean[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    return len(clean)


def _c_func(m, pos: int, text: str, cpp: bool, extern_c: bool) -> CFunc | None:
    ret = re.sub(r"\s+", " ", m.group("ret")).strip()
    name = m.group("name")
    params = m.group("params").strip()
    if name == "RADFUNC" and not ret:
        fname = params.strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", fname):
            return None
        return CFunc(fname, "", [], "", radfunc=True, doc=doc_before(text, pos), pos=pos)
    if name in C_RESERVED or not ret or name.startswith("operator"):
        return None
    words = ret.replace("*", " * ").replace("&", " & ").split()
    if any(w in ("static", "inline", "constexpr", "typedef", "template", "return", "else", "virtual",
                 "friend", "#define", "__inline", "__forceinline") for w in words):
        return None
    if re.search(r'\bextern\s*"\s*"', ret):
        extern_c = True
        ret = re.sub(r'\bextern\s*"\s*"\s*', "", ret).strip()
    ret = re.sub(r"\bextern\b\s*", "", ret).strip()
    if "::" in name or re.search(r"[<>=]", ret):
        return None
    plist: list[tuple[str, str]] = []
    if params and params != "void":
        for p in split_top(params):
            if p == "...":
                return None
            pp = _c_param(p)
            if pp is None:
                return None
            plist.append(pp)
    return CFunc(name, ret, plist, re.sub(r"\s+", " ", params), extern_c=extern_c,
                 doc=doc_before(text, pos), pos=pos)


def c_callable(f: CFunc, cpp: bool) -> bool:
    """Can the generated worker call *f* (all types convertible)?"""
    if f.radfunc:
        return True
    if c_type_kind(f.ret, cpp) is None:
        return False
    return all(c_type_kind(t, cpp) not in (None, "void") for t, _ in f.params)


def c_exports(path: Path, text: str, cpp: bool) -> list[ExportedFunction]:
    header = Path(path).suffix.lower() in (".h", ".hpp", ".hh", ".hxx")
    module = Path(path).stem
    out: list[ExportedFunction] = []
    seen: set[str] = set()
    for f in c_functions(text, cpp, header):
        if f.name in seen or not is_public_name(f.name) or f.name == "main" or not c_callable(f, cpp):
            continue
        seen.add(f.name)
        if f.radfunc:
            params = [f"arg{i + 1}" for i in range(f.nargs)]
            kind = "function"
        else:
            params = [p for _, p in f.params]
            kind = "sub" if c_type_kind(f.ret, cpp) == "void" else "function"
        out.append(ExportedFunction(name=f.name, params=params, module=module, doc=f.doc, kind=kind))
    return out


def c_worker_wrappers(funcs: list[CFunc], cpp: bool) -> tuple[list[str], dict[str, str]]:
    """Declarations + wrappers for the worker main; returns (lines, {name: C function to dispatch to})."""
    L: list[str] = []
    entry: dict[str, str] = {}
    for f in funcs:
        if f.radfunc:
            L.append(f"RADFUNC({f.name});")
            entry[f.name] = f.name
            continue
        if not c_callable(f, cpp):
            continue
        ext = 'extern "C" ' if (cpp and f.extern_c) else ""
        L.append(f"{ext}{f.ret} {f.name}({f.param_text or ('void' if not cpp else '')});")
        w = f"rad_x_{f.name}"
        n = len(f.params)
        L += [f"static const char *{w}(int argc, const char **argv)", "{"]
        L.append("    const char *res;")
        if n:
            L.append(f'    if (argc < {n}) return rad_fail("{f.name} needs {n} argument{"s" if n > 1 else ""}");')
        else:
            L.append("    (void)argc;")
        L.append("    (void)argv;")
        call_args, frees = [], []
        for i, (t, _p) in enumerate(f.params):
            k = c_type_kind(t, cpp)
            if k == "num":
                call_args.append(f"({_strip_const(t)})rad_json_num(argv[{i}])")
            elif k == "bool":
                L.append(f"    int b{i} = rad_x_bool(argv[{i}]);")
                call_args.append(f"b{i} != 0")
            elif k == "str":
                L.append(f"    char *s{i} = rad_x_dup(rad_json_str(argv[{i}]));")
                call_args.append(f"s{i}")
                frees.append(f"    free(s{i});")
            elif k == "cppstr":
                L.append(f"    std::string s{i} = rad_json_str(argv[{i}]);")
                call_args.append(f"s{i}")
            elif k == "json":
                call_args.append(f"rad::Value(argv[{i}])")
        call = f"{f.name}({', '.join(call_args)})"
        rk = c_type_kind(f.ret, cpp)
        if rk == "void":
            L += [f"    {call};", '    res = "null";']
        elif rk == "num":
            L.append(f"    res = rad_json_numtext((double)({call}));")
        elif rk == "bool":
            L.append(f'    res = ({call}) ? "true" : "false";')
        elif rk == "str":
            L += [f"    {{ const char *r = {call};", '      res = r ? rad_json_quote(r) : "null"; }']
        elif rk == "cppstr":
            L += [f"    {{ std::string r = {call};", "      res = rad_json_quote(r.c_str()); }"]
        elif rk == "json":
            L += [f"    {{ rad::Value r = {call};", "      res = rad_x_keep(r.json().c_str()); }"]
        L += frees + ["    return res;", "}", ""]
        entry[f.name] = w
    return L, entry


def _strip_const(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\bconst\b", " ", t)).strip()


C_WORKER_HELPERS = [
    "static char *rad_x_dup(const char *s)",
    "{",
    "    size_t n = strlen(s ? s : \"\") + 1;",
    "    char *p = (char *)malloc(n);",
    "    if (p) memcpy(p, s ? s : \"\", n);",
    "    return p;",
    "}",
    "static int rad_x_bool(const char *json)",
    "{",
    "    while (*json == ' ') json++;",
    "    if (strncmp(json, \"true\", 4) == 0) return 1;",
    "    if (strncmp(json, \"false\", 5) == 0 || strncmp(json, \"null\", 4) == 0) return 0;",
    "    return rad_json_num(json) != 0;",
    "}",
    "static const char *rad_x_keep(const char *json)",
    "{",
    "    static char *kept = 0;",
    "    free(kept);",
    "    kept = rad_x_dup(json);",
    "    return kept;",
    "}",
    "",
]


# ============================================================================ C / C++ consumer side
def c_reference_proxy(lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
    L_ = ident(lib, C_RESERVED)
    hdr = proxy_header(lib)
    guard = f"RADREF_{L_.upper()}_H"
    H = [f"/* {hdr}",
         f" * Reference to the project {lib}. Include it and call the functions of {lib} as C functions:",
         f" *     #include \"{L_}.ref.h\"",
         f" *     double x = {L_}_<Func>_num(2, 3);          numbers in, number out",
         f" *     const char *s = {L_}_<Func>_str(\"a\", \"b\");  texts in, text out",
         f" *     const char *j = {L_}_<Func>(\"2\", \"\\\"text\\\"\");  JSON texts in, JSON text out",
         " * On error the JSON/text variants return \"\" and the _num variant 0; rad_error() says why.",
         " * Returned strings live in a ring of static buffers: copy them if you keep them. */",
         f"#ifndef {guard}", f"#define {guard}", "", '#include "radgui.h"', "",
         "#ifdef __cplusplus", 'extern "C" {', "#endif", ""]
    C = [f"/* {hdr} */", "#include <stdlib.h>", "#include <string.h>", '#include "radgui.h"',
         f'#include "{L_}.ref.h"', "",
         "typedef struct { char *p; size_t n, cap; } radref_sb;", "",
         "static void radref_put(radref_sb *b, const char *s)", "{",
         "    size_t k = strlen(s ? s : \"\");",
         "    if (b->n + k + 1 > b->cap) {",
         "        size_t cap = (b->n + k + 1) * 2 + 64;",
         "        char *p = (char *)realloc(b->p, cap);",
         "        if (!p) return;",
         "        b->p = p; b->cap = cap;", "    }",
         "    memcpy(b->p + b->n, s ? s : \"\", k);", "    b->n += k;", "    b->p[b->n] = 0;", "}", "",
         "static void radref_arg(radref_sb *b, int i, const char *json)", "{",
         "    radref_put(b, i ? \", \" : \"[\");", "    radref_put(b, json && *json ? json : \"null\");", "}", "",
         "static const char *radref_go(const char *target, radref_sb *b)", "{",
         "    const char *r;", "    if (!b->p) radref_put(b, \"[\");", "    radref_put(b, \"]\");",
         "    r = radcall(target, b->p);", "    free(b->p);", "    return r;", "}", ""]
    seen: set[str] = set()
    for fn in functions:
        base = ident(f"{L_}_{fn.name}", C_RESERVED)
        if base in seen:
            continue
        seen.add(base)
        ps = unique_params(fn.params, C_RESERVED | {"rr_", "radref_sb"})
        tgt = c_string(target_of(fn))
        sig_j = ", ".join(f"const char *{p}" for p in ps) or "void"
        sig_n = ", ".join(f"double {p}" for p in ps) or "void"
        H += [f"/* {proxy_extra(fn)} */",
              f"const char *{base}({sig_j});",
              f"double {base}_num({sig_n});",
              f"const char *{base}_str({sig_j});", ""]
        for suffix, sig, conv, ret_t, wrap in (
                ("", sig_j, "{}", "const char *", "{}"),
                ("_num", sig_n, "rad_json_numtext({})", "double ", "rad_json_num({})"),
                ("_str", sig_j, "rad_json_quote({})", "const char *", "rad_json_str({})")):
            C += [f"{ret_t}{base}{suffix}({sig})", "{", "    radref_sb rr_ = {0, 0, 0};"]
            C += [f"    radref_arg(&rr_, {i}, {conv.format(p)});" for i, p in enumerate(ps)]
            if suffix == "":
                C.append(f"    return radref_go({tgt}, &rr_);")
            else:
                C += [f"    {{ const char *r = radref_go({tgt}, &rr_);",
                      f"      return {wrap.format('r')}; }}"]
            C += ["}", ""]
    H += ["#ifdef __cplusplus", "}", "#endif", "", "#endif", ""]
    return {f"{L_}.ref.h": "\n".join(H), f"{L_}.ref.c": "\n".join(C)}


def cpp_reference_proxy(lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
    L_ = ident(lib, C_RESERVED)
    guard = f"RADREF_{L_.upper()}_HPP"
    H = [f"// {proxy_header(lib)}",
         f"// Reference to the project {lib}: call its functions as C++ functions of namespace {L_}.",
         f"//     #include \"{L_}.ref.hpp\"",
         f"//     double x = {L_}::<Func>(2, 3);                 rad::Value converts to double",
         f"//     std::string s = {L_}::<Func>(\"a\").str();      .str() .num() .boolean() .json()",
         "// Arguments may be numbers, bool, text (const char* / std::string), rad::Value or std::vector.",
         "// A failed call throws std::runtime_error (rad_error() text).",
         f"#ifndef {guard}", f"#define {guard}", "", '#include "radgui.hpp"', "", f"namespace {L_} {{", ""]
    seen: set[str] = set()
    for fn in functions:
        name = ident(fn.name, C_RESERVED)
        if name in seen:
            continue
        seen.add(name)
        ps = unique_params(fn.params, C_RESERVED)
        tps = [f"T{i}" for i in range(len(ps))]
        H.append(f"/// {proxy_extra(fn)}")
        if ps:
            H.append("template <" + ", ".join(f"class {t}" for t in tps) + ">")
        H.append(f"inline rad::Value {name}(" + ", ".join(f"const {t} &{p}" for t, p in zip(tps, ps)) + ")")
        H += ["{", f"    return rad::invoke({c_string(target_of(fn))}, {{" +
              ", ".join(f"rad::to_json({p})" for p in ps) + "});", "}", ""]
    H += [f"}}  // namespace {L_}", "", "#endif", ""]
    return {f"{L_}.ref.hpp": "\n".join(H)}


# ============================================================================ Rust
RUST_RESERVED = set("""as async await break const continue crate dyn else enum extern false fn for if impl in let
    loop match mod move mut pub ref return self Self static struct super trait true type unsafe use where while
    abstract become box do final macro override priv typeof unsized virtual yield try""".split())
_RUST_NUM = {"f64", "f32", "i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32", "u64", "u128", "usize"}
_RUST_RET_OK = _RUST_NUM - {"i128", "u128"} | {"bool", "String", "&str", "&'static str", "Json", "()", "Vec<Json>",
                                              "Vec<f64>", "Vec<i64>", "Vec<String>", "Option<Json>"}


@dataclass
class RustFunc:
    name: str
    params: list[tuple[str, str]]      # (name, type)
    ret: str                           # "" = ()
    legacy: bool = False               # pub fn f(args: &[Json])
    doc: str = ""


def _rust_norm(t: str) -> str:
    return re.sub(r"\s+", "", t)


def rust_arg_expr(t: str, i: int) -> tuple[str, str] | None:
    """(setup statement, call expression) converting args[i] to type t."""
    t = _rust_norm(t)
    get = f"args.get({i}).cloned().unwrap_or(Json::Null)"
    if t in _RUST_NUM:
        return "", f"({get}.as_f64() as {t})"
    if t == "bool":
        return "", f"{get}.as_bool()"
    if t == "String":
        return "", f"{get}.as_str()"
    if t in ("&str", "&String"):
        return f"let s{i} = {get}.as_str();", f"&s{i}"
    if t == "Json":
        return "", get
    if t == "&Json":
        return f"let j{i} = {get};", f"&j{i}"
    vec = re.fullmatch(r"(&)?(?:Vec<(\w+)>|\[(\w+)\])", t)
    if vec:
        inner = vec.group(2) or vec.group(3)
        if vec.group(3) and not vec.group(1):
            return None
        conv = {"Json": "x.clone()", "String": "x.as_str()", "bool": "x.as_bool()"}.get(inner)
        if conv is None and inner in _RUST_NUM:
            conv = f"(x.as_f64() as {inner})"
        if conv is None:
            return None
        setup = f"let v{i}: Vec<{inner}> = match {get} {{ Json::Arr(a) => a.iter().map(|x| {conv}).collect(), " \
                f"_ => Vec::new() }};"
        return setup, (f"&v{i}" if vec.group(1) else f"v{i}")
    return None


def _rust_ret_ok(r: str) -> bool:
    r = _rust_norm(r)
    if not r or r in _RUST_RET_OK:
        return True
    m = re.fullmatch(r"Result<(.+),(String|&'static str|&str|Box<dynstd::error::Error>)>", r)
    if m:
        return _rust_ret_ok(m.group(1))
    return False


def rust_functions(text: str) -> list[RustFunc]:
    clean = blank_code(text, raw_lifetimes=True)
    out: list[RustFunc] = []
    rx = re.compile(r"\bpub\s+fn\s+([A-Za-z_]\w*)\s*\(", re.M)
    depth_at = _depth_map(clean)
    for m in rx.finditer(clean):
        if depth_at(m.start()) != 0:
            continue
        name = m.group(1)
        # parameters up to the matching ')'
        j, d = m.end(), 1
        while j < len(clean) and d:
            d += {"(": 1, ")": -1}.get(clean[j], 0)
            j += 1
        params_text = clean[m.end():j - 1]
        rest = clean[j:j + 400]
        rm = re.match(r"\s*(?:->\s*(?P<ret>[^{;]+?))?\s*(?:where\b[^{]*)?[{;]", rest, re.S)
        if rm is None:
            continue
        ret = (rm.group("ret") or "").strip()
        plist = []
        bad = False
        for p in split_top(params_text):
            if ":" not in p:
                bad = True
                break
            pn, pt = p.split(":", 1)
            pn = pn.replace("mut ", "").strip()
            plist.append((pn, pt.strip()))
        if bad:
            continue
        legacy = len(plist) == 1 and _rust_norm(plist[0][1]) == "&[Json]"
        out.append(RustFunc(name, plist, ret, legacy, doc_before(text, _line_start(text, m.start()), "//")))
    return out


def _line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def _depth_map(clean: str):
    marks: list[tuple[int, int]] = []
    d = 0
    for i, c in enumerate(clean):
        if c == "{":
            d += 1
            marks.append((i, d))
        elif c == "}":
            d -= 1
            marks.append((i, d))

    def depth(pos: int) -> int:
        lo, hi, best = 0, len(marks) - 1, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if marks[mid][0] < pos:
                best = marks[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return best
    return depth


def rust_callable(f: RustFunc) -> bool:
    if f.legacy:
        return True
    return _rust_ret_ok(f.ret) and all(rust_arg_expr(t, i) is not None for i, (_n, t) in enumerate(f.params))


def rust_exports(path: Path, text: str) -> list[ExportedFunction]:
    out = []
    module = Path(path).stem
    for f in rust_functions(text):
        if not is_public_name(f.name) or f.name == "main" or not rust_callable(f):
            continue
        params = ["args"] if f.legacy else [n for n, _ in f.params]
        kind = "sub" if _rust_norm(f.ret) in ("", "()") else "function"
        out.append(ExportedFunction(name=f.name, params=params, module=module, doc=f.doc, kind=kind))
    return out


def rust_dispatch_arm(f: RustFunc, modpath: str) -> str:
    if f.legacy:
        return f'        "{f.name}" => Some({modpath}::{f.name}(args).reply()),'
    setups, calls = [], []
    for i, (_n, t) in enumerate(f.params):
        s, c = rust_arg_expr(t, i)
        if s:
            setups.append(s)
        calls.append(c)
    call = f"{modpath}::{f.name}({', '.join(calls)}).reply()"
    if not setups:
        return f'        "{f.name}" => Some({call}),'
    return f'        "{f.name}" => Some({{ {" ".join(setups + [call])} }}),'


def rust_reference_proxy(lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
    L_ = ident(lib, RUST_RESERVED)
    out = [f"// {proxy_header(lib)}",
           f"// Reference to the project {lib}. Use it from a form or module:",
           f"//     use crate::{L_};",
           f"//     let x = {L_}::<func>(2, 3).as_f64();      // Json result (.as_f64 .as_str .as_bool ...)",
           f"//     match {L_}::try_<func>(2, 3) {{ Ok(v) => ..., Err(e) => ... }}",
           "// The plain function panics when the call fails; try_<func> returns Result<Json, String>.",
           "#![allow(non_snake_case, dead_code, unused_imports)]", "",
           "use crate::radgui::{radcall, Json};", ""]
    seen: set[str] = set()
    for fn in functions:
        name = re.sub(r"\W", "_", fn.name)
        if name in seen or not name:
            continue
        seen.add(name)
        nm = f"r#{name}" if name in RUST_RESERVED and name not in ("self", "Self", "crate", "super") else name
        ps = unique_params(fn.params, RUST_RESERVED | {"args"})
        sig = ", ".join(f"{p}: impl Into<Json>" for p in ps)
        call_args = ", ".join(f"{p}.into()" for p in ps)
        out += [f"/// {proxy_extra(fn)}",
                f"pub fn {nm}({sig}) -> Json {{",
                f"    match try_{name}({', '.join(ps)}) {{",
                "        Ok(v) => v,",
                f"        Err(e) => panic!(\"{target_of(fn)}: {{}}\", e),",
                "    }", "}", "",
                f"/// {proxy_extra(fn)} (returns the error instead of panicking)",
                f"pub fn try_{name}({sig}) -> Result<Json, String> {{",
                f"    radcall({c_string(target_of(fn))}, &[{call_args}])", "}", ""]
    return {f"{L_}_ref.rs": "\n".join(out)}


# ============================================================================ Fortran
@dataclass
class FProc:
    name: str
    kind: str                       # function | sub
    args: list[str]
    result: str                     # result variable (functions)
    types: dict[str, str] = field(default_factory=dict)      # var (lower) -> kind code
    intents: dict[str, str] = field(default_factory=dict)
    arrays: set[str] = field(default_factory=set)
    prefix_type: str = ""
    doc: str = ""
    nargs: int = 0                  # legacy f(args): highest args(i) index


_F_TYPE = re.compile(
    r"^\s*(?P<t>real\s*\*\s*8|real\s*\(\s*(?:kind\s*=\s*)?(?:8|c_double|dp|real64)\s*\)|double\s+precision"
    r"|real\s*\*\s*4|real\s*\(\s*(?:kind\s*=\s*)?(?:4|c_float|sp|real32)\s*\)|real"
    r"|integer\s*\*\s*8|integer\s*\(\s*(?:kind\s*=\s*)?(?:8|c_long_long|int64|c_int64_t)\s*\)"
    r"|integer\s*\(\s*(?:kind\s*=\s*)?(?:4|c_int|int32)\s*\)|integer"
    r"|logical(?:\s*\(\s*(?:kind\s*=\s*)?4\s*\))?"
    r"|character\s*(?:\(\s*(?:len\s*=\s*)?(?:\*|:|\d+)\s*\)|\*\s*\(\s*\*\s*\)|\*\s*\d+)?)"
    r"(?P<attrs>(?:\s*,\s*[^:]+?)*)\s*::\s*(?P<names>.+)$", re.I)


def _f_kind(t: str) -> str:
    t = re.sub(r"\s+", "", t.lower())
    if t.startswith("character"):
        return "s"
    if t.startswith("logical"):
        return "l"
    if t.startswith("integer"):
        return "i8" if re.search(r"8|int64|long", t) else "i4"
    if t.startswith("double") or re.search(r"real(\*8|\(.*(8|double|dp|64).*\))", t):
        return "r8"
    return "r4"


def _f_lines(text: str) -> list[tuple[str, int]]:
    """Logical lines (continuations joined, comments removed) with their first physical line index."""
    out: list[tuple[str, int]] = []
    cur, first = "", 0
    for i, raw in enumerate(text.splitlines()):
        s = _f_strip_comment(raw).rstrip()
        if cur:
            s = s.lstrip()
            if s.startswith("&"):
                s = s[1:]
        else:
            first = i
        if s.endswith("&"):
            cur += s[:-1]
            continue
        cur += s
        for part in _split_semicolons(cur):
            out.append((part, first))
        cur = ""
    if cur:
        out.append((cur, first))
    return out


def _f_strip_comment(line: str) -> str:
    q = ""
    for i, c in enumerate(line):
        if q:
            if c == q:
                q = ""
        elif c in "\"'":
            q = c
        elif c == "!":
            return line[:i]
    return line


def _split_semicolons(s: str) -> list[str]:
    return [p for p in s.split(";")] if ";" in s and "'" not in s and '"' not in s else [s]


_F_PROC = re.compile(r"^\s*(?P<pre>(?:(?:pure|elemental|recursive|impure|module)\s+)*"
                     r"(?P<ptype>(?:real|integer|logical|double\s+precision|character)[^:]*?)?\s*"
                     r"(?:(?:pure|elemental|recursive|impure)\s+)*)"
                     r"(?P<kind>function|subroutine)\s+(?P<name>\w+)\s*(?:\((?P<args>[^)]*)\))?"
                     r"\s*(?:result\s*\(\s*(?P<res>\w+)\s*\))?\s*(?:bind\s*\(.*\))?\s*$", re.I)


def fortran_module(text: str) -> tuple[str, list[FProc], set[str], set[str], bool]:
    """(module name, module procedures, public names, private names, default private)."""
    lines = _f_lines(text)
    phys = text.splitlines()
    modname = ""
    procs: list[FProc] = []
    public: set[str] = set()
    private: set[str] = set()
    default_private = False
    stack: list[FProc | None] = []
    in_interface = 0
    contains = False
    for s, li in lines:
        low = s.strip().lower()
        if not low:
            continue
        if not modname:
            m = re.match(r"^module\s+(?!procedure\b)(\w+)\s*$", low)
            if m:
                modname = m.group(1)
            continue
        if re.match(r"^(abstract\s+)?interface\b", low):
            in_interface += 1
            continue
        if re.match(r"^end\s*interface\b", low):
            in_interface -= 1
            continue
        if in_interface:
            continue
        if re.match(r"^end\s*(function|subroutine)\b", low) or (low == "end" and stack):
            if stack:
                stack.pop()
            continue
        if re.match(r"^end\s*module\b", low) or (low == "end" and not stack):
            break
        m = _F_PROC.match(s)
        if m and contains:
            args = [a.strip() for a in (m.group("args") or "").split(",") if a.strip()]
            kind = "function" if m.group("kind").lower() == "function" else "sub"
            p = FProc(m.group("name"), kind, args, (m.group("res") or m.group("name")),
                      prefix_type=(m.group("ptype") or "").strip(),
                      doc=_f_doc(phys, li))
            if not stack:
                procs.append(p)
                stack.append(p)
            else:
                stack.append(None)
            continue
        if not stack:
            if low == "contains":
                contains = True
            elif low == "private":
                default_private = True
            elif low == "public":
                default_private = False
            else:
                vm = re.match(r"^(public|private)\s*(?:::)?\s*(.+)$", low)
                if vm and not re.match(r"^(public|private)\s*,", low):
                    names = {n.strip() for n in re.split(r",", vm.group(2)) if re.fullmatch(r"\w+", n.strip())}
                    (public if vm.group(1) == "public" else private).update(names)
            continue
        cur = stack[-1]
        if cur is None or len(stack) != 1:
            continue
        if low == "contains":         # internal procedures follow (pushed as None)
            continue
        tm = _F_TYPE.match(s)
        if tm:
            k = _f_kind(tm.group("t"))
            attrs = tm.group("attrs").lower()
            intent = re.search(r"intent\s*\(\s*(in\s*out|inout|out|in)\s*\)", attrs)
            dim = "dimension" in attrs
            for nm in re.finditer(r"(\w+)\s*(\([^)]*\))?\s*(?:=[^,]*)?", tm.group("names")):
                n = nm.group(1).lower()
                cur.types[n] = k
                if intent:
                    cur.intents[n] = re.sub(r"\s+", "", intent.group(1))
                if dim or nm.group(2):
                    cur.arrays.add(n)
    # legacy function(args): count args(i)
    for p in procs:
        if [a.lower() for a in p.args] == ["args"] and "args" in p.arrays:
            idx = [int(x) for x in re.findall(r"\bargs\s*\(\s*(\d+)\s*\)", text, re.I)]
            p.nargs = max(idx) if idx else 0
    return modname, procs, public, private, default_private


def _f_doc(phys: list[str], li: int) -> str:
    j = li - 1
    block: list[str] = []
    while j >= 0 and phys[j].strip().startswith("!"):
        block.insert(0, phys[j].strip().lstrip("!").strip())
        j -= 1
    for b in block:
        if b and not set(b) <= set("-=*!#"):
            return b
    return ""


def f_is_legacy(p: FProc) -> bool:
    return p.kind == "function" and [a.lower() for a in p.args] == ["args"] and "args" in p.arrays


def f_result_kind(p: FProc) -> str | None:
    if p.kind == "sub":
        return "void"
    if p.prefix_type:
        return _f_kind(p.prefix_type)
    return p.types.get(p.result.lower())


def f_callable(p: FProc) -> bool:
    if f_is_legacy(p):
        return True
    if f_result_kind(p) is None:
        return False
    for a in p.args:
        a = a.lower()
        if a not in p.types or a in p.arrays or p.intents.get(a, "in") != "in":
            return False
    return True


def fortran_public(text: str) -> tuple[str, list[FProc]]:
    mod, procs, public, private, default_private = fortran_module(text)
    out = []
    for p in procs:
        n = p.name.lower()
        if n in private or (default_private and n not in public):
            continue
        out.append(p)
    return mod, out


def fortran_exports(path: Path, text: str) -> list[ExportedFunction]:
    module = Path(path).stem
    _mod, procs = fortran_public(text)
    out = []
    for p in procs:
        if not is_public_name(p.name) or not f_callable(p):
            continue
        params = [f"arg{i + 1}" for i in range(p.nargs)] if f_is_legacy(p) else list(p.args)
        out.append(ExportedFunction(name=p.name, params=params, module=module, doc=p.doc,
                                    kind="sub" if p.kind == "sub" else "function"))
    return out


_F_ARG = {"r8": "rad_num(args({i}))", "r4": "real(rad_num(args({i})))", "i4": "int(rad_num(args({i})))",
          "i8": "int(rad_num(args({i})), 8)", "l": "rad_tbool(args({i}))", "s": "trim(args({i}))"}
_F_RET = {"r8": "rad_jnum({})", "r4": "rad_jnum(real({}, 8))", "i4": "rad_jnum(real({}, 8))",
          "i8": "rad_jnum(real({}, 8))", "l": "rad_jbool({})", "s": "rad_jstr({})"}


def fortran_worker_case(p: FProc, alias: str) -> list[str]:
    """Lines of the select-case branch that calls *p* (renamed *alias* by the use statement)."""
    L = [f"    case ('{p.name.lower()}')"]
    if f_is_legacy(p):
        return L + [f"      call rad_wk_reply({alias}(args))"]
    n = len(p.args)
    ind = "      "
    if n:
        L += [f"      if (size(args) < {n}) then",
              f"        call rad_wk_fail('{p.name} needs {n} argument{'s' if n > 1 else ''}')", "      else"]
        ind = "        "
    exprs = [_F_ARG[p.types[a.lower()]].format(i=i + 1) for i, a in enumerate(p.args)]
    if p.kind == "sub":
        call = f"call {alias}(" + (", &\n" + ind + "    ").join(exprs) + ")"
        L += [ind + call, ind + "call rad_wk_reply('null')"]
    else:
        inner = f"{alias}(" + (", &\n" + ind + "    ").join(exprs) + ")"
        L.append(ind + "call rad_wk_reply(" + _F_RET[f_result_kind(p)].format(inner) + ")")
    if n:
        L.append("      end if")
    return L


def fortran_reference_proxy(lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
    L_ = ident(lib)
    if not L_[0].isalpha():
        L_ = "r" + L_
    mod = f"{L_.lower()}_ref"
    names: list[tuple[ExportedFunction, str, list[str]]] = []
    seen: set[str] = set()
    for fn in functions:
        base = ident(f"{L_}_{fn.name}").replace("__", "_")[:59]
        if base.lower() in seen:
            continue
        seen.add(base.lower())
        ps = unique_params(fn.params, {"rad_res", "r"}, lower=True)
        ps = [p if p[0].isalpha() else "a" + p for p in ps]
        names.append((fn, base, ps))
    out = [f"! {proxy_header(lib)}",
           f"! Reference to the project {lib}. In a form's module:   use {mod}",
           f"!     x = {L_}_<func>_num(2d0, 3d0)      ! real(8) result",
           f"!     s = {L_}_<func>_str('a', 'b')      ! text result",
           f"!     j = {L_}_<func>(2, 'text')         ! JSON text result",
           "! Arguments may be integer, real, real(8), logical or character values.",
           "! On error the result is '' (or 0) and rad_error() says why.",
           f"module {mod}", "  use radgui", "  implicit none", "  private"]
    if names:
        pub = []
        for _fn, base, _ps in names:
            pub += [base, base + "_num", base + "_str"]
        out.append("  public :: " + ", &\n    ".join(pub))
    out.append("contains")
    for fn, base, ps in names:
        decl = f"    class(*), intent(in) :: {', '.join(ps)}" if ps else ""
        arglist = ", ".join(ps)
        if ps:
            json = "'[' // " + " // ', ' // &\n      ".join(f"rad_jany({p})" for p in ps) + " // ']'"
        else:
            json = "'[]'"
        out += ["", f"  ! {proxy_extra(fn)}",
                f"  function {base}({arglist}) result(rad_res)"]
        if decl:
            out.append(decl)
        out += ["    character(len=:), allocatable :: rad_res",
                f"    rad_res = radcall('{target_of(fn)}', {json})",
                f"  end function {base}", "",
                f"  function {base}_num({arglist}) result(rad_res)"]
        if decl:
            out.append(decl)
        out += ["    real(8) :: rad_res", f"    rad_res = rad_num({base}({arglist}))",
                f"  end function {base}_num", "",
                f"  function {base}_str({arglist}) result(rad_res)"]
        if decl:
            out.append(decl)
        out += ["    character(len=:), allocatable :: rad_res", f"    rad_res = rad_jtext({base}({arglist}))",
                f"  end function {base}_str"]
    out += ["", f"end module {mod}", ""]
    return {f"{L_}_ref.f90": "\n".join(out)}


# ============================================================================ Go
GO_RESERVED = set("""break case chan const continue default defer else fallthrough for func go goto if import
    interface map package range return select struct switch type var any""".split())


def go_functions(text: str) -> list[tuple[str, list[str], bool, str, bool]]:
    """(name, param names, returns_value, doc, variadic) of top-level functions (no methods/generics)."""
    clean = blank_code(text, quotes="\"'`")
    out = []
    for m in re.finditer(r"^func\s+([A-Za-z_]\w*)\s*\(", clean, re.M):
        j, d = m.end(), 1
        while j < len(clean) and d:
            d += {"(": 1, ")": -1}.get(clean[j], 0)
            j += 1
        ptext = clean[m.end():j - 1]
        rest = clean[j:j + 300]
        rm = re.match(r"\s*([^{]*)\{", rest)
        results = rm.group(1).strip() if rm else ""
        segs = split_top(ptext)
        names: list[str] = []
        variadic = "..." in ptext
        if segs and all(len(s.split()) == 1 for s in segs):
            names = [f"p{i + 1}" for i in range(len(segs))]           # unnamed parameters (types only)
        else:
            names = [s.split()[0] for s in segs]
        returns = bool(results) and re.sub(r"[()\s]", "", results) != "error"
        out.append((m.group(1), names, returns, doc_before(text, m.start(), "//"), variadic))
    return out


def go_exports(path: Path, text: str) -> list[ExportedFunction]:
    module = Path(path).stem
    out = []
    for name, params, returns, doc, _var in go_functions(text):
        if not name[0].isupper() or is_handler(name) or name.startswith(("Rad", "RAD")):
            continue
        out.append(ExportedFunction(name=name, params=params, module=module, doc=doc,
                                    kind="function" if returns else "sub"))
    return out


def go_reference_proxy(lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
    L_ = ident(lib, GO_RESERVED)
    fields, funcs, init = [], [], []
    seen: set[str] = set()
    for fn in functions:
        name = ident(fn.name, GO_RESERVED)
        if name in seen:
            continue
        seen.add(name)
        ps = unique_params(fn.params, GO_RESERVED | {"radcall", "radcallE"})
        variadic = bool(fn.params) and ("..." in fn.params[-1] or fn.params[-1].lstrip().startswith("*"))
        if variadic:
            sig = ", ".join([f"{p} any" for p in ps[:-1]] + [f"{ps[-1]} ...any"])
            args = f"{ps[0]}..." if len(ps) == 1 else f"append([]any{{{', '.join(ps[:-1])}}}, {ps[-1]}...)..."
        else:
            sig = ", ".join(f"{p} any" for p in ps)
            args = ", ".join(ps)
        tgt = c_string(target_of(fn))
        call_args = f"{tgt}, {args}" if args else tgt
        fields += [f"\t// {proxy_extra(fn)}", f"\t{name} func({sig}) any",
                   f"\t// {name}E is {name} returning the error instead of panicking",
                   f"\t{name}E func({sig}) (any, error)"]
        init += [f"\t{name}: {L_}_{name},", f"\t{name}E: {L_}_{name}E,"]
        funcs += [f"// {L_}_{name} calls {proxy_extra(fn)} (panics when the call fails)",
                  f"func {L_}_{name}({sig}) any {{ return radcall({call_args}) }}", "",
                  f"// {L_}_{name}E calls {target_of(fn)} and returns the error",
                  f"func {L_}_{name}E({sig}) (any, error) {{ return radcallE({call_args}) }}", ""]
    out = [f"// {proxy_header(lib)}",
           f"// Reference to the project {lib}: call its functions as {L_}.<Func>(args...) (or {L_}_<Func>).",
           "// Results are JSON values (float64, string, bool, nil, []any, map[string]any).",
           "package main", "",
           f"// {L_} is the referenced project {lib}.",
           f"var {L_} = struct {{", *fields, "}{", *init, "}", "", *funcs]
    return {f"{L_}_ref.go": "\n".join(out).rstrip() + "\n"}
