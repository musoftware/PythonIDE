"""Static scan for the progress rule: long-running call patterns in radide/ that are not wrapped by
radide/progress.py (see docs/TESTING.md, "Progress for long-running operations").

A hit is a call that usually takes seconds or more:
  * urlopen / urlretrieve (network download),
  * subprocess.run / check_output / check_call / call / Popen(...).wait() whose command literally names a
    build / package tool (npm, npx, pip, composer, cargo, dotnet, flutter, dart, gradle, mvn, pyinstaller,
    git clone/fetch/pull/push, rustup, gem, bundle ...),
  * QProcess.waitForFinished() with no timeout, -1 or more than 5000 ms (blocks the thread that calls it).
A hit is *wrapped* when its enclosing function (or an enclosing def) is the work function of
progress.run_task / run_blocking / run_command / download, takes a ``reporter`` parameter, or is itself
radide/progress.py.  Every other hit must be listed in progress_allowlist.json with the reason
(worker thread, CLI only, probe ...): keys are "path::qualified.function::kind".

    python samples/Tests/UX/progress_rule_scan.py            # print unlisted hits (exit code = count)
    python samples/Tests/UX/progress_rule_scan.py --write    # regenerate the allowlist keeping reasons
"""
from __future__ import annotations

import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ALLOWLIST = os.path.join(HERE, "progress_allowlist.json")
SKIP_PARTS = ("flutterdesign/qtpreview", "__pycache__", "/assets/", "/ring_samples/")
TOOLS = {"npm", "npm.cmd", "npx", "npx.cmd", "pip", "composer", "cargo", "dotnet", "flutter", "dart", "gradle",
         "gradlew", "mvn", "mvnw", "pyinstaller", "rustup", "gem", "bundle", "yarn", "pnpm", "go", "ng",
         "msbuild", "ollama"}
GIT_NET = {"clone", "fetch", "pull", "push"}
SUBPROC = {"run", "check_output", "check_call", "call"}
WRAPPERS = {"run_task", "run_blocking", "run_command", "download"}


def _strings(node) -> list[str]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def _names_tool(cmd) -> str | None:
    words = []
    for s in _strings(cmd):
        words.extend(s.replace("\\", "/").split())
    low = [w.lower().rsplit("/", 1)[-1] for w in words]
    for i, w in enumerate(low):
        base = w[:-4] if w.endswith((".exe", ".cmd", ".bat")) else w
        if base in TOOLS:
            if base == "go" and "install" not in low:
                continue
            return base
        if base == "-m" and i + 1 < len(low) and low[i + 1] in ("pip", "pyinstaller", "venv"):
            return low[i + 1]
        if base == "git" and any(x in GIT_NET for x in low[i + 1:i + 4]):
            return "git-net"
    return None


class Scan(ast.NodeVisitor):
    def __init__(self, rel: str):
        self.rel = rel
        self.stack: list[ast.AST] = []
        self.hits: list[tuple[str, int, str, str]] = []      # key, line, kind, code
        self.wrapped_names: set[str] = set()

    def visit_FunctionDef(self, node):
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    def qual(self) -> str:
        return ".".join(n.name for n in self.stack) or "<module>"

    def _wrapped(self) -> bool:
        for n in self.stack:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if n.name in self.wrapped_names:
                    return True
                args = [a.arg for a in n.args.args + n.args.kwonlyargs]
                if "reporter" in args:
                    return True
        return False

    def visit_Call(self, node):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        owner = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
        kind = None
        if name in ("urlopen", "urlretrieve"):
            kind = "download"
        elif name in SUBPROC and owner in ("subprocess", "sp", ""):
            if owner or name in ("check_output", "check_call"):
                if node.args:
                    tool = _names_tool(node.args[0])
                    if tool:
                        kind = f"tool:{tool}"
        elif name == "waitForFinished":
            arg = node.args[0] if node.args else None
            v = arg.value if isinstance(arg, ast.Constant) else (
                -arg.operand.value if isinstance(arg, ast.UnaryOp) and isinstance(arg.operand, ast.Constant) else None)
            if arg is None or (isinstance(v, (int, float)) and (v < 0 or v > 5000)):
                kind = "waitForFinished"
        if kind and not self._wrapped():
            key = f"{self.rel}::{self.qual()}::{kind}"
            self.hits.append((key, node.lineno, kind, ast.unparse(node)[:120]))
        self.generic_visit(node)


def _collect_wrapped(tree) -> set[str]:
    """Names of functions passed to progress.run_task / run_blocking (first positional or 3rd for run_blocking)."""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if nm in ("run_task", "run_blocking"):
                for a in list(n.args) + [k.value for k in n.keywords if k.arg == "fn"]:
                    if isinstance(a, ast.Name):
                        names.add(a.id)
                    elif isinstance(a, ast.Attribute):
                        names.add(a.attr)
                    elif isinstance(a, ast.Lambda):
                        for c in ast.walk(a.body):
                            if isinstance(c, ast.Call) and isinstance(c.func, (ast.Name, ast.Attribute)):
                                names.add(c.func.id if isinstance(c.func, ast.Name) else c.func.attr)
    return names


def scan(root: str = ROOT) -> list[tuple[str, int, str, str]]:
    hits = []
    base = os.path.join(root, "radide")
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if any(p in "/" + rel for p in SKIP_PARTS) or rel == "radide/progress.py":
                continue
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), filename=rel)
            except (SyntaxError, UnicodeDecodeError):
                continue
            s = Scan(rel)
            s.wrapped_names = _collect_wrapped(tree)
            s.visit(tree)
            hits.extend(s.hits)
    return hits


def load_allowlist() -> dict[str, str]:
    try:
        with open(ALLOWLIST, encoding="utf-8") as f:
            return json.load(f).get("allow", {})
    except (OSError, ValueError):
        return {}


def unlisted(hits=None, allow=None):
    hits = scan() if hits is None else hits
    allow = load_allowlist() if allow is None else allow
    return [h for h in hits if h[0] not in allow]


def stale(hits=None, allow=None):
    hits = scan() if hits is None else hits
    allow = load_allowlist() if allow is None else allow
    keys = {h[0] for h in hits}
    return sorted(k for k in allow if k not in keys)


def main():
    hits = scan()
    allow = load_allowlist()
    if "--write" in sys.argv:
        new = {}
        for key, _line, _kind, _code in sorted(hits):
            new[key] = allow.get(key, "TODO: justify (worker thread / CLI only / probe) or wrap with radide.progress")
        doc = {"note": "Justified exceptions to the progress rule (samples/Tests/UX/progress_rule_scan.py). "
                       "Key: path::function::kind. Value: why this call does not need radide.progress.",
               "allow": new}
        with open(ALLOWLIST, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {len(new)} entries")
        return 0
    bad = unlisted(hits, allow)
    for key, line, kind, code in bad:
        print(f"{key.split('::')[0]}:{line}: {kind}: {code}")
    print(f"{len(hits)} hits, {len(bad)} not wrapped and not allowlisted, {len(stale(hits, allow))} stale allowlist keys")
    return len(bad)


if __name__ == "__main__":
    sys.exit(main())
