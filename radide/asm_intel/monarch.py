"""Monaco (Monarch) syntax highlighting for NASM, MASM, FASM and GAS (Intel and AT&T).

``language_spec(dialect, att)`` returns the JSON-safe description radide/web/editor.html's
``radRegisterMonarch`` registers: the language id (``rad-asm-<dialect>``), the Monarch tokenizer (regular
expressions as strings - Monarch compiles them), the language configuration (comments, brackets, word
pattern) and the folding rules (block start/end pairs, sections, label bodies, comment runs).
"""
from __future__ import annotations

from . import directives, isa
from .engine import FOLD_PAIRS, LABEL_RE, SECTION_RE, WORD_RE

LANG_IDS = {"nasm": "rad-asm-nasm", "masm": "rad-asm-masm", "fasm": "rad-asm-fasm", "gas": "rad-asm-gas",
            "gas-att": "rad-asm-gas"}
ALIASES = {"nasm": ["Assembly (NASM)", "nasm"], "masm": ["Assembly (MASM)", "masm"], "fasm": ["Assembly (FASM)", "fasm"],
           "gas": ["Assembly (GNU as)", "gas"]}

_NUM_RULES = [
    [r"0[xX][0-9a-fA-F_]+\b", "number.hex"],
    [r"\$[0-9][0-9a-fA-F_]*\b", "number.hex"],
    [r"[0-9][0-9a-fA-F_]*[hH]\b", "number.hex"],
    [r"0[bB][01_]+\b", "number.binary"],
    [r"[01_]+[bByY]\b", "number.binary"],
    [r"[0-7_]+[qQoO]\b", "number.octal"],
    [r"\d+\.\d+([eE][\-+]?\d+)?", "number.float"],
    [r"\d+[dD]?\b", "number"],
]


def _instructions() -> list[str]:
    names = set(isa.INSTRUCTIONS)
    for base in isa.ATT_SUFFIXED:
        for suf in isa.ATT_SUFFIX:
            names.add(base + suf)
    names |= {"movzbl", "movzwl", "movzbq", "movzwq", "movsbl", "movswl", "movsbq", "movswq", "movslq", "cltq",
              "cqto", "cltd", "cwtl", "callq", "retq", "leaveq", "pushq", "popq", "jmpq"}
    return sorted(names)


def _registers() -> list[str]:
    return sorted(set(isa.REGISTERS) | {f"st({i})" for i in range(8)})


def language_spec(dialect: str, att: bool = False) -> dict:
    dia = dialect if dialect in LANG_IDS else "nasm"
    dirs = sorted(directives.DIRECTIVES.get(dia, {}))
    preproc = [d for d in dirs if d.startswith("%")]
    plain_dirs = [d for d in dirs if not d.startswith("%")]
    root: list = []
    lid = LANG_IDS[dia]
    if dia == "gas":
        root += [
            [r"/\*", "comment", "@comment"],
            [r"^\s*#\s*(include|define|undef|if|ifdef|ifndef|else|elif|endif|pragma)\b.*$", "keyword.directive"],
            [r"#.*$", "comment"],
            [r"//.*$", "comment"],
        ]
    else:
        root += [[r";.*$", "comment"]]
    root += [
        [r'"', "string", "@dstring"],
        [r"'", "string", "@sstring"] if dia != "gas" else [r"'.", "string"],
    ]
    if dia == "nasm":
        root.append([r"`", "string", "@bstring"])
    if dia == "gas":
        root += [
            [r"%[a-zA-Z][a-zA-Z0-9]*", {"cases": {"@registers_pct": "variable.predefined", "@default": "invalid"}}],
            [r"\$-?(0[xX][0-9a-fA-F]+|\d+)", "number"],
            [r"\$[A-Za-z_.][\w.$]*", "constant"],
            [r"\\[A-Za-z_]\w*", "variable.parameter"],     # macro argument \arg
        ]
    if dia == "nasm":
        root += [[r"%%[A-Za-z_.?][\w.?$@#~]*", "tag"],          # macro-local label
                 [r"%\d+", "variable.parameter"],             # macro parameter
                 [r"%[A-Za-z_][\w]*", {"cases": {"@preproc": "keyword.directive", "@default": "macro"}}],
                 [r"\$\$?(?![0-9A-Fa-f])", "constant"]]
    root += _NUM_RULES
    # label definitions:  name:   .local:   @@:
    root += [
        [r"[A-Za-z_.?$@][\w.?$@#~]*(?=\s*::?(?!=))", {"cases": {"@registers": "variable.predefined",
                                                               "@default": "tag"}}],
        [r"[A-Za-z_.?$@][\w.?$@#~]*", {"cases": {
            "@instructions": "keyword",
            "@registers": "variable.predefined",
            "@directives": "type",
            "@default": "identifier"}}],
        [r"[\[\]]", "@brackets"],
        [r"[{}()<>]", "@brackets"],
        [r"[+\-*/%&|^~!=<>:,]", "operator"],
    ]
    tokenizer = {
        "root": root,
        "dstring": [[r'[^\\"]+', "string"], [r"\\.", "string.escape"], [r'"', "string", "@pop"]],
        "sstring": [[r"[^\\']+", "string"], [r"\\.", "string.escape"], [r"'", "string", "@pop"]],
        "bstring": [[r"[^\\`]+", "string"], [r"\\.", "string.escape"], [r"`", "string", "@pop"]],
        "comment": [[r"\*/", "comment", "@pop"], [r"[^*]+", "comment"], [r"\*", "comment"]],
    }
    if dia in ("nasm", "fasm"):                       # '...' strings do not process escapes there
        tokenizer["sstring"] = [[r"[^']+", "string"], [r"'", "string", "@pop"]]
        if dia == "fasm":
            tokenizer["dstring"] = [[r'[^"]+', "string"], [r'"', "string", "@pop"]]
    if dia == "masm":
        tokenizer["sstring"] = [[r"[^']+", "string"], [r"'", "string", "@pop"]]
        tokenizer["dstring"] = [[r'[^"]+', "string"], [r'"', "string", "@pop"]]
    monarch = {
        "ignoreCase": True,
        "defaultToken": "",
        "tokenPostfix": ".asm",
        "instructions": _instructions(),
        "registers": _registers(),
        "registers_pct": ["%" + r for r in isa.REGISTERS],
        "directives": plain_dirs,
        "preproc": preproc,
        "brackets": [{"open": "[", "close": "]", "token": "delimiter.square"},
                     {"open": "(", "close": ")", "token": "delimiter.parenthesis"},
                     {"open": "{", "close": "}", "token": "delimiter.curly"}],
        "tokenizer": tokenizer,
    }
    line_comment = "#" if dia == "gas" else ";"
    conf = {
        "comments": {"lineComment": line_comment, **({"blockComment": ["/*", "*/"]} if dia == "gas" else {})},
        "brackets": [["[", "]"], ["(", ")"], ["{", "}"]],
        "autoClosingPairs": [{"open": "[", "close": "]"}, {"open": "(", "close": ")"}, {"open": "{", "close": "}"},
                             {"open": '"', "close": '"', "notIn": ["string", "comment"]},
                             {"open": "'", "close": "'", "notIn": ["string", "comment"]}],
        "surroundingPairs": [{"open": "[", "close": "]"}, {"open": "(", "close": ")"}, {"open": '"', "close": '"'},
                             {"open": "'", "close": "'"}],
        "wordPattern": r"(-?\d*\.\d\w*)|(" + WORD_RE[dia] + ")",
    }
    folding = {
        "pairs": [[a, b] for a, b in FOLD_PAIRS.get(dia, [])],
        "section": SECTION_RE[dia],
        "label": LABEL_RE[dia],
        "lineComment": ["#", "//"] if dia == "gas" else [";"],
    }
    return {"id": lid, "aliases": ALIASES[dia], "extensions": [], "monarch": monarch, "conf": conf, "folding": folding,
            "triggers": [".", "%", "["] if dia in ("nasm", "gas") else [".", "["], "dialect": dia, "att": bool(att)}
