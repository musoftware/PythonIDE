"""Unit tests of the built-in quick fixes (radide/quickfix): the provider registry, merging with a language server's
code actions, and every language's providers - no window, no network, nothing installed (installers.DRY_RUN).

    python samples/Tests/Editor/test_quickfix_providers.py [scratch folder]

Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_qfunit_")) / "qf_unit"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:600]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


from radide import quickfix as Q  # noqa: E402
from radide.editkit import apply_edits_to_text  # noqa: E402
from radide.quickfix import installers, lang_python  # noqa: E402

installers.DRY_RUN = True


def write(rel: str, text: str) -> Path:
    p = SCRATCH / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def acts(path: Path, text: str, line: int, col: int, diags=None, cheap=False):
    ctx = Q.make_context(text, path, line, col, diags, cheap=cheap)
    return Q.collect(ctx)


def titles(lst):
    return [a.title for a in lst]


def applied(a, path, text):
    return apply_edits_to_text(text, a.file_edits(path))


def first(lst, needle):
    return next((a for a in lst if needle in a.title), None)


# ============================================================================ registry
calls = []


def fake(ctx):
    calls.append(ctx.word)
    return [Q.Action("Fake fix", edits=ctx.edit([[0, 0, 0, 0, "// fixed\n"]])),
            Q.Action("fake FIX", edits=ctx.edit([[0, 0, 0, 0, "// other\n"]])),              # same title -> dropped
            Q.Action("Same result", edits=ctx.edit([[0, 0, 0, 0, "// fixed\n"]])),           # same edit -> dropped
            Q.Action("Preferred one", preferred=True, edits=ctx.edit([[0, 0, 0, 0, "// p\n"]]))]


def broken(_ctx):
    raise RuntimeError("boom")


Q.register("zzlang", fake)
Q.register(("zzlang",), broken)
Q.register("zzlang", fake)                                    # registered once
p = write("reg/x.zz", "hello world\n")
ctx = Q.make_context("hello world\n", p, 0, 2, language="zzlang")
got = Q.collect(ctx)
ok("registry: provider called once with the word under the caret", calls == ["hello"], calls)
ok("registry: a failing provider is skipped", len(got) == 2, titles(got))
ok("registry: duplicates by title and by resulting text dropped", titles(got) == ["Preferred one", "Fake fix"],
   titles(got))
ok("registry: preferred first", got and got[0].preferred)
Q.unregister(fake)
Q.unregister(broken)
ok("registry: unregister", Q.collect(Q.make_context("x", p, 0, 0, language="zzlang")) == [])

# merge with the server's actions
srv = [{"title": "Server: using System.Text;", "kind": "quickfix",
        "edit": {"changes": {p.resolve().as_uri(): [{"range": {"start": {"line": 0, "character": 0},
                                                             "end": {"line": 0, "character": 0}},
                                                   "newText": "// fixed\n"}]}}},
       {"title": "Extract method", "kind": "refactor.extract", "command": {"command": "x", "title": "x"}}]
mine = [Q.Action("using System.Text;", edits={str(p): [[0, 0, 0, 0, "// fixed\n"]]}),
        Q.Action("Built-in only", edits={str(p): [[0, 0, 0, 0, "// b\n"]]})]
m = Q.merge(mine, srv, "hello world\n", p)
ok("merge: the server's action wins over a built-in one with the same edit", titles(m) == [
    "Server: using System.Text;", "Extract method", "Built-in only"], titles(m))
ok("merge: kinds grouped (quickfix / refactor)", [a.kind for a in m] == ["quickfix", "refactor", "quickfix"],
   [a.kind for a in m])
ok("merge: server actions keep their LSP payload", m[0].lsp is srv[0] and m[1].lsp is srv[1])

# diagnostics messages -> names
for msg, want in (("undefined name 'np'", "np"), ('"yaml" is not defined', "yaml"),
                  ('Import "yaml" could not be resolved', "yaml"),
                  ("The name 'MessageBox' does not exist in the current context", "MessageBox"),
                  ("The type or namespace name 'List<>' could not be found (are you missing a using directive?)",
                   "List"),
                  ("Cannot find module 'lodash' or its corresponding type declarations.", "lodash"),
                  ("failed to resolve: use of undeclared type `HashMap`", "HashMap"),
                  ("undefined: strings", "strings"), ("ArrayList cannot be resolved to a type", "ArrayList")):
    names = Q.unresolved_names(msg)
    ok(f"diagnostic names: {msg[:40]}", any(n.split("<")[0] == want for n in names), names)

# ============================================================================ Python
py_root = SCRATCH / "pyproj"
write("pyproj/helpers.py", "def greet(name):\n    return 'hi ' + name\n\nCOLORS = ['red']\n")
write("pyproj/requirements.txt", "requests\n")
fake_py = str(py_root / ".venv" / "Scripts" / "python.exe")
write("pyproj/.venv/Scripts/python.exe", "")                     # Run uses the project's .venv
lang_python._SITE[fake_py] = {"requests"}                        # what the venv has installed
ok("python: the interpreter is the project's .venv", installers.python_for(None, py_root / "main.py") == fake_py,
   installers.python_for(None, py_root / "main.py"))
src = '"""Main module."""\nimport os\n\nx = np.array([1, 2])\n'
f = write("pyproj/main.py", src)
r = acts(f, src, 3, 5)
ok("python: np -> import numpy as np (preferred)", r and r[0].title == "import numpy as np", titles(r))
ok("python: numpy is not installed -> also the pip action", first(r, "Install 'numpy' with pip") is not None, titles(r))
ok("python: the import goes after the existing imports",
   r and applied(r[0], f, src) == '"""Main module."""\nimport os\nimport numpy as np\n\nx = np.array([1, 2])\n',
   r and applied(r[0], f, src))
src = "p = Path('x')\nd = defaultdict(list)\n"
f = write("pyproj/b.py", src)
r = acts(f, src, 0, 5)
ok("python: Path -> from pathlib import Path", r and r[0].title == "from pathlib import Path", titles(r))
ok("python: no 'Create function' next to a real import", not first(r, "Create function"), titles(r))
src2 = "from collections import OrderedDict\n\nd = defaultdict(list)\n"
r = acts(f, src2, 2, 5)
ok("python: joins an existing 'from collections import ...'",
   r and applied(r[0], f, src2).startswith("from collections import OrderedDict, defaultdict\n"),
   r and applied(r[0], f, src2))
src = "print(greet('a'))\n"
f = write("pyproj/c.py", src)
r = acts(f, src, 0, 8)
ok("python: a project function -> from helpers import greet", first(r, "from helpers import greet") is not None,
   titles(r))
src = "import yaml\nimport requests\n"
f = write("pyproj/d.py", src)
r = acts(f, src, 0, 9)
a = first(r, "Install 'PyYAML' with pip")
ok("python: import yaml (not installed) -> Install 'PyYAML' with pip", a is not None, titles(r))
ok("python: pip action previews the command into the .venv + requirements.txt",
   a is not None and fake_py in a.detail and "PyYAML" in a.detail and "requirements.txt" in a.detail,
   a and a.detail)
ok("python: import requests (installed) -> no pip action", not acts(f, src, 1, 10), titles(acts(f, src, 1, 10)))
installers.LAST.clear()
if a is not None:
    a.run(None, None)
ok("python: pip install runs with the venv's python (dry run)",
   installers.LAST and installers.LAST[-1]["argv"] == [fake_py, "-m", "pip", "install", "PyYAML"], installers.LAST)
ok("python: requirements.txt got PyYAML",
   "PyYAML" in (py_root / "requirements.txt").read_text(encoding="utf-8").splitlines(),
   (py_root / "requirements.txt").read_text(encoding="utf-8"))
ok("python: requirements.txt not duplicated", not installers.add_requirement(py_root, "pyyaml"))
r = acts(f, "import cv2\n", 0, 8)
ok("python: cv2 -> opencv-python", first(r, "opencv-python") is not None, titles(r))
r = acts(f, "x = foo\n", 0, 5, [{"line": 0, "col": 4, "endLine": 0, "endCol": 7, "message": "undefined name 'json'"}])
ok("python: the name from a diagnostic (json) -> import json", first(r, "import json") is not None, titles(r))
src = "def main():\n    total = compute(1, b)\n"
r = acts(f, src, 1, 13, [{"line": 1, "col": 12, "endLine": 1, "endCol": 19, "message": "undefined name 'compute'"}])
ok("python: Create function 'compute' (args from the call)",
   r and r[0].title == "Create function 'compute'" and applied(r[0], f, src).startswith("def compute(arg1, b):\n    pass"),
   r and applied(r[0], f, src))
src = "class A:\n    def go(self):\n        self.helper(3)\n\n\nx = 1\n"
r = acts(f, src, 2, 14)
ok("python: self.helper(...) -> Create method in the class",
   r and "    def helper(self, arg1):\n        pass\n" in applied(r[0], f, src)
   and applied(r[0], f, src).index("def helper") < applied(r[0], f, src).index("x = 1"), r and applied(r[0], f, src))
ok("python: light bulb (cheap) still finds np", first(acts(write("pyproj/e.py", "np.zeros(3)\n"),
                                                           "np.zeros(3)\n", 0, 1, cheap=True), "import numpy") is not None)

# ============================================================================ C# / VB
rad = SCRATCH / "RadCs"
write("RadCs/project.radproj", json.dumps({"name": "RadCs", "language": "csharp-bridge", "forms": ["Form1"]}))
cs = ('public static partial class Form1\n{\n    static void RmButton1_Click(RadEvent e)\n    {\n'
      '        MessageBox.Show("Hello", "Title");\n    }\n}\n')
f = write("RadCs/Form1.cs", cs)
diag = [{"line": 4, "col": 8, "endLine": 4, "endCol": 18,
         "message": "The name 'MessageBox' does not exist in the current context"}]
r = acts(f, cs, 4, 10, diag)
ok("RAD C#: MessageBox -> 'Use the RAD helper MsgBox(...)' first", r and r[0].title.startswith(
    "Use the RAD helper MsgBox(...)"), titles(r))
ok("RAD C#: applying rewrites the call to MsgBox(text)", r and 'MsgBox("Hello");' in applied(r[0], f, cs),
   r and applied(r[0], f, cs))
using = first(r, "using System.Windows.Forms")
ok("RAD C#: 'using System.Windows.Forms;' is shown disabled with the reason", using is not None and using.disabled
   and "console process" in using.title, using and (using.title, using.disabled))
r = acts(f, cs.replace("MessageBox.Show", "msgbox"), 4, 10)
ok("RAD C#: msgbox -> Change to 'MsgBox'", r and r[0].title == "Change 'msgbox' to 'MsgBox'", titles(r))
r = acts(f, cs.replace('MessageBox.Show("Hello", "Title");', "var l = new List<int>();"), 4, 22)
ok("RAD C#: List<int> needs nothing (implicit usings of RadApp.csproj)", not [a for a in r if "using" in a.title],
   titles(r))
r = acts(f, cs.replace('MessageBox.Show("Hello", "Title");', "var sb = new StringBuilder();"), 4, 24)
ok("RAD C#: StringBuilder -> using System.Text;", r and r[0].title == "using System.Text;", titles(r))
r = acts(f, cs.replace('MessageBox.Show("Hello", "Title");', 'var s = JsonConvert.SerializeObject(1);'), 4, 18)
pk = first(r, "Install package 'Newtonsoft.Json'")
ok("RAD C#: JsonConvert -> Install package 'Newtonsoft.Json' from NuGet", pk is not None, titles(r))
installers.LAST.clear()
if pk is not None:
    class _Ed:                                  # a minimal editor: the using is added after the install
        buf = cs

        def text(self):
            return self.buf

        def setText(self, t):
            self.buf = t
    fake_ed = _Ed()
    pk.run(None, fake_ed)
    ok("RAD C#: after the install the using is added", "using Newtonsoft.Json;" in fake_ed.buf, fake_ed.buf[:80])
ok("RAD C#: the package goes into _build/csharp/RadApp.csproj (dry run)",
   installers.LAST and installers.LAST[-1]["argv"][1:3] == ["add", str(rad / "_build" / "csharp" / "RadApp.csproj")]
   and installers.LAST[-1]["argv"][-1] == "Newtonsoft.Json", installers.LAST)
r = acts(f, cs.replace('MessageBox.Show("Hello", "Title");', "FooBarWidget w;"), 4, 10)
ok("RAD C#: an unknown type -> Search NuGet.org", first(r, "Search NuGet.org for 'FooBarWidget'") is not None,
   titles(r))
r = acts(f, cs, 2, 22)
ok("RAD C#: the RAD type RadEvent / a handler name -> no fix", not acts(f, cs, 2, 35) and not r,
   (titles(r), titles(acts(f, cs, 2, 35))))
ok("RAD C#: a call of an own method (not a type) -> no NuGet search",
   not first(acts(f, cs.replace('MessageBox.Show("Hello", "Title");', "UpdateTotals();"), 4, 10), "NuGet"))
ok("RAD C#: light bulb (cheap) does not offer the network search",
   not first(acts(f, cs.replace('MessageBox.Show("Hello", "Title");', "FooBarWidget w;"), 4, 10, cheap=True),
             "Search"))
loose = "class A\n{\n    void F() { var l = new List<int>(); }\n}\n"
f = write("loose/A.cs", loose)
r = acts(f, loose, 2, 28)
ok("C# loose file: List -> using System.Collections.Generic; (preferred)",
   r and r[0].title == "using System.Collections.Generic;", titles(r))
ok("C# loose file: the using goes on top", r and applied(r[0], f, loose).startswith(
    "using System.Collections.Generic;\n\nclass A"), r and applied(r[0], f, loose))
ok("C# loose file: fully qualified alternative", first(r, "System.Collections.Generic.List") is not None, titles(r))
gen = "class A\n{\n    static void F()\n    {\n        DoIt(1);\n    }\n}\n"
r = acts(f, gen, 4, 9, [{"line": 4, "col": 8, "endLine": 4, "endCol": 12,
                         "message": "The name 'DoIt' does not exist in the current context"}])
ok("C#: Create method 'DoIt' (static, inside the class)", r and r[0].title == "Create method 'DoIt'"
   and "    static void DoIt(object arg1)\n" in applied(r[0], f, gen), r and applied(r[0], f, gen))
vb = "Module M\n    Sub Main()\n        Dim sb As New StringBuilder()\n    End Sub\nEnd Module\n"
f = write("loose/M.vb", vb)
r = acts(f, vb, 2, 25)
ok("VB.NET: StringBuilder -> Imports System.Text", r and r[0].title == "Imports System.Text"
   and applied(r[0], f, vb).startswith("Imports System.Text\n"), titles(r))

# ============================================================================ JavaScript / TypeScript
write("web/package.json", json.dumps({"name": "w"}))
write("web/src/util.ts", "export function greet(n: string) { return n; }\nexport default class Store {}\n")
src = "import _ from 'lodash';\nimport fs from 'fs';\n"
f = write("web/src/a.js", src)
r = acts(f, src, 0, 17)
ok("JS: lodash not in node_modules -> Install 'lodash' with npm", r and r[0].title == "Install 'lodash' with npm",
   titles(r))
ok("JS: a node builtin needs nothing", not acts(f, src, 1, 17))
installers.LAST.clear()
if r:
    r[0].run(None, None)
ok("JS: npm install runs in the package.json folder (dry run)", installers.LAST and installers.LAST[-1]["argv"][1:] ==
   ["install", "lodash"] and Path(installers.LAST[-1]["cwd"]) == SCRATCH / "web", installers.LAST)
(SCRATCH / "web" / "node_modules" / "lodash").mkdir(parents=True)
ok("JS: installed -> no action", not acts(f, src, 0, 17), titles(acts(f, src, 0, 17)))
src = "import { readFileSync } from 'fs';\n\nconsole.log(greet('x'));\n"
f = write("web/src/b.ts", src)
r = acts(f, src, 2, 14)
ok("TS: a project export -> import { greet } from './util';", r and applied(r[0], f, src).splitlines()[1] ==
   "import { greet } from './util';", r and applied(r[0], f, src))
src = "import express from 'express';\n"
f = write("web/src/c.ts", src)
r = acts(f, src, 0, 22)
ok("TS: express -> npm install + the @types variant", first(r, "Install 'express' with npm") is not None and
   first(r, "@types/express") is not None, titles(r))

# ============================================================================ Rust / Go / Java / PHP
write("rs/Cargo.toml", '[package]\nname = "x"\nversion = "0.1.0"\n\n[dependencies]\nrand = "0.8"\n')
src = "fn main() {\n    let m: HashMap<i32, i32> = HashMap::new();\n}\n"
f = write("rs/src/main.rs", src)
r = acts(f, src, 1, 12)
ok("Rust: HashMap -> use std::collections::HashMap;", r and r[0].title == "use std::collections::HashMap;"
   and applied(r[0], f, src).startswith("use std::collections::HashMap;\n"), titles(r))
src = "use serde_json::Value;\nuse rand::Rng;\n"
f = write("rs/src/lib.rs", src)
r = acts(f, src, 0, 6)
ok("Rust: serde_json not in Cargo.toml -> cargo add serde_json", r and r[0].title == "Add crate 'serde_json' (cargo add)",
   titles(r))
ok("Rust: rand is a dependency -> nothing", not acts(f, src, 1, 6), titles(acts(f, src, 1, 6)))
write("go/go.mod", "module example.com/app\n\ngo 1.22\n\nrequire github.com/google/uuid v1.6.0\n")
src = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println(strings.ToUpper("x"))\n}\n'
f = write("go/main.go", src)
r = acts(f, src, 5, 15)
ok("Go: strings.ToUpper -> import \"strings\" into the import list",
   r and 'import (\n\t"fmt"\n\t"strings"\n)' in applied(r[0], f, src), r and applied(r[0], f, src))
src = 'package main\n\nimport (\n\t"github.com/gorilla/mux"\n\t"github.com/google/uuid"\n)\n'
f = write("go/srv.go", src)
r = acts(f, src, 3, 10)
ok("Go: github.com/gorilla/mux not in go.mod -> go get", r and r[0].title == "go get github.com/gorilla/mux",
   titles(r))
ok("Go: a required module -> nothing", not acts(f, src, 4, 10))
src = "package app;\n\npublic class A {\n    ArrayList<String> items;\n}\n"
f = write("java/A.java", src)
r = acts(f, src, 3, 6)
ok("Java: ArrayList -> import java.util.ArrayList; after the package line",
   r and applied(r[0], f, src).startswith("package app;\n\nimport java.util.ArrayList;\n"), r and applied(r[0], f, src))
write("php/composer.json", json.dumps({"autoload": {"psr-4": {"App\\": "src/"}}}))
write("php/src/Models/User.php", "<?php\nnamespace App\\Models;\n\nclass User {}\n")
src = "<?php\nnamespace App\\Http;\n\nuse Monolog\\Logger;\n\n$u = new User();\n"
f = write("php/src/Http/Ctl.php", src)
r = acts(f, src, 3, 6)
ok("PHP: Monolog not autoloaded -> composer require monolog/monolog",
   r and r[0].title == "Install 'monolog/monolog' with Composer", titles(r))
r = acts(f, src, 5, 11)
ok("PHP: User of the project -> use App\\Models\\User;", r and r[0].title == "use App\\Models\\User;"
   and "use App\\Models\\User;" in applied(r[0], f, src).splitlines(), r and applied(r[0], f, src))

fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
sys.exit(fails)
