"""Lua language plugin (GUI Bridge). Client library: runtimes/clients/lua/rad.lua."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from .bridgebase import toolchains_root
from .scripting_common import CONTROL_METHODS, ScriptBridgePlugin, _property_names
from .scripting_refs import doc_above, header, is_public, make_export, proxy_params, valid_ident

API = {
    "rad.set": "rad.set(obj, prop, value) - set a property: rad.set(\"lblOut\", \"Caption\", \"Hi\")",
    "rad.get": "rad.get(obj, prop) -> string - read a property: rad.get(\"txtA\", \"Text\")",
    "rad.getnum": "rad.getnum(obj, prop) -> number - read a property as a number",
    "rad.call": "rad.call(obj, method, ...) -> string - e.g. rad.call(\"lstLog\", \"AddItem\", \"x\")",
    "rad.msgbox": "rad.msgbox(text) - message box",
    "rad.input": "rad.input(prompt) -> string - input box",
    "rad.show": "rad.show(form) - show a form",
    "rad.hide": "rad.hide(form) - hide a form",
    "rad.quit": "rad.quit() - quit the program",
    "ui": "ui.<control>.<Prop> / ui.<control>.<Prop> = value / ui.<control>:<Method>(args)",
    "msgbox": "msgbox(text) - message box",
    "radcall": "radcall(\"Module.func\", ...) -> value - call a function of any project module (RAD Hub)",
}
MEMBERS = {k.split(".", 1)[1]: v for k, v in API.items() if k.startswith("rad.")}

# search path for project modules and LuaRocks packages installed with --tree lua_modules
LUA_PATH_SETUP = ("local v=_VERSION:sub(5) "
                  "package.path='./?.lua;./?/init.lua;./lua_modules/share/lua/'..v..'/?.lua;"
                  "./lua_modules/share/lua/'..v..'/?/init.lua;'..package.path "
                  "package.cpath='./lua_modules/lib/lua/'..v..'/?.dll;./lua_modules/lib/lua/'..v..'/?.so;'"
                  "..package.cpath")


class LuaBridgePlugin(ScriptBridgePlugin):
    id = "lua-bridge"
    display_name = "Lua (GUI Bridge)"
    code_ext = ".lua"
    tool_names = ["lua", "lua54", "lua5.4", "lua53", "lua5.3", "luajit", "lua5.1"]
    tool_hints = [r"C:\Program Files (x86)\Lua\5.4\lua.exe", r"C:\Program Files\Lua\5.4\lua.exe",
                  r"C:\Program Files (x86)\Lua\5.1\lua.exe", r"C:\Lua\lua.exe", r"C:\Lua\lua54.exe",
                  str(Path.home() / "AppData/Local/Programs/Lua/bin/lua.exe")]
    toolchain_bins = ["lua/bin", "lua"]
    install_hint = ("Install Lua (winget install DEVCOM.Lua) and add it to PATH, or extract the LuaBinaries "
                    "Win64 zip (+ luarocks.exe) into %LOCALAPPDATA%\\RADIDE\\toolchains\\lua\\bin.")
    handler_regex = r"^\s*function\s+(\w+_\w+)\s*\("
    client_subdir = "lua"
    client_names = ["rad.lua", "radworker.lua", "radcall_helper.py"]
    worker_script = "radworker.lua"
    api = API
    case_sensitive = True
    line_comments = ["--"]
    block_comment = ("--[[", "]]")
    string_quotes = ['"', "'"]
    keywords = """and break do else elseif end false for function goto if in local nil not or repeat
        return then true until while""".split()
    builtins = ["print", "pairs", "ipairs", "tostring", "tonumber", "type", "select", "error", "pcall",
                "xpcall", "require", "setmetatable", "getmetatable", "rawget", "rawset", "next", "assert",
                "string", "table", "math", "os", "io", "utf8", "coroutine", "rad", "ui", "radcall", "msgbox"]
    _lua_versions: dict[str, str] = {}

    def lua_version(self, tool: str) -> str:
        """"5.4"-style version of the Lua interpreter *tool* ("" when it cannot be run)."""
        if tool not in LuaBridgePlugin._lua_versions:
            ver = ""
            try:
                r = subprocess.run([tool, "-v"], capture_output=True, text=True, timeout=15)
                out = r.stdout + r.stderr
                m = re.search(r"\bLua (\d+\.\d+)", out)
                ver = m.group(1) if m else ("5.1" if "LuaJIT" in out else "")
            except (OSError, subprocess.SubprocessError):
                pass
            LuaBridgePlugin._lua_versions[tool] = ver
        return LuaBridgePlugin._lua_versions[tool]

    def luarocks_flags(self) -> list[str]:
        """``--lua-dir <prefix> --lua-version <x.y>`` for the interpreter RAD IDE uses, so LuaRocks
        finds it even when it is not on PATH (e.g. %LOCALAPPDATA%\\RADIDE\\toolchains\\lua\\bin\\lua54.exe)."""
        lua = self.tool()
        if not lua or not Path(lua).is_absolute():
            return []
        exe = Path(lua)
        prefix = exe.parent.parent if exe.parent.name.lower() == "bin" else exe.parent
        ver = self.lua_version(lua)
        return ["--lua-dir", str(prefix)] + (["--lua-version", ver] if ver else [])

    @staticmethod
    def luarocks_env(rocks: str) -> dict[str, str] | None:
        """The stand-alone luarocks.exe from the toolchains folder needs its built-in archive modules
        (no 7z/unzip on Windows): LUAROCKS_CONFIG points to a small config written by RAD IDE."""
        try:
            Path(rocks).resolve().relative_to(toolchains_root().resolve())
        except (ValueError, OSError):
            return None
        cfg = toolchains_root().parent / "luarocks" / "config.lua"
        text = ("-- written by RAD IDE for the stand-alone luarocks.exe in %LOCALAPPDATA%\\RADIDE\\toolchains\n"
                "fs_use_modules = true\n")
        try:
            if not cfg.is_file() or cfg.read_text(encoding="utf-8") != text:
                cfg.parent.mkdir(parents=True, exist_ok=True)
                cfg.write_text(text, encoding="utf-8")
        except OSError:
            return None
        return {"LUAROCKS_CONFIG": str(cfg)}

    @property
    def package_manager(self) -> PackageManager:
        """LuaRocks, installing into the project's lua_modules tree (on the run-time search path)."""
        rocks = self.sibling_tool("luarocks")
        lr = [rocks] + self.luarocks_flags()
        return PackageManager(
            name="LuaRocks", tool=rocks,
            list_cmd=lr + ["list", "--porcelain", "--tree", "lua_modules"],
            search_cmd=lr + ["search", "--porcelain", "{query}"],
            install_cmd=lr + ["install", "--tree", "lua_modules", "{name}", "{version}"],
            uninstall_cmd=lr + ["remove", "--tree", "lua_modules", "{name}"],
            init_cmd=None, manifest="",
            search_url="https://luarocks.org/search?q={query}",
            env=self.luarocks_env(rocks))

    # ------------------------------------------------------------ templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"-- Event handlers for {n}. Global functions named <Control>_<Event> run when the event\n"
                f"-- happens. rad.set / rad.get / rad.call (or ui.txtA.Text, ui.lblOut.Caption = \"x\")\n"
                f"-- work with the controls; radcall(\"Module.func\", ...) calls other project modules.\n\n"
                f"function {n}_Load(e)\n"
                f"  -- runs when the form is shown\n"
                f"end\n")

    def module_template(self, name: str) -> str:
        return (f"-- Module {name}. Use it from Lua code with: local {name} = require(\"{name}\")\n"
                f"-- Other languages call its functions through the RAD Hub: radcall(\"{name}.hello\", \"x\")\n"
                f"-- (arguments and the result are JSON values: numbers, strings, tables).\n"
                f"local M = {{}}\n\n"
                f"function M.hello(who)\n"
                f"  return \"Hello, \" .. who\n"
                f"end\n\n"
                f"return M\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*function\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"function {name}(e)", "  ", "end"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code: str, filename: str) -> str:
        stem = re.escape(Path(filename).stem)
        rx = re.compile(rf"^.*\b(require\s*\(?\s*[\"']{stem}[\"']|dofile\s*\(?\s*[\"'](\./)?{stem}\.lua[\"']).*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ build / run
    def _prefix(self) -> list[str]:
        setup = LUA_PATH_SETUP + f" RAD_PYTHON={sys.executable!r}"
        return ["-e", setup]

    def main_source(self, project: Project):
        L = ["-- AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)",
             "local rad = require(\"rad\")"]
        for f in self.my_forms(project):
            L.append(f"rad.load_file(\"{self.code_file(f)}\")")
        L += ["rad.run()", ""]
        return "_radmain.lua", "\n".join(L)

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [self.tool() or "lua", *self._prefix(), "_radmain.lua"]

    def worker_argv(self, tool: str, folder: Path, module_rel: str) -> list[str]:
        return [tool, *self._prefix(), self.worker_script, module_rel]

    # ------------------------------------------------------------ references (CONTRACTS 7)
    def exported_functions(self, path: Path, text: str, module: str | None = None) -> list:
        """Public functions of a library file: global ``function Name(...)`` and the functions
        of the returned module table (``function M.name(...)`` / ``M.name = function(...)``) -
        what radworker.lua serves. ``local``/``_private`` functions and handlers are skipped."""
        stem = module or Path(path).stem
        lines = text.splitlines()
        code_lines, in_block = [], False
        for line in lines:                      # blank out --[[ block comments ]]
            if in_block:
                in_block = "]]" not in line
                code_lines.append("")
                continue
            if re.match(r"^\s*--\[=*\[", line) and "]]" not in line:
                in_block = True
                code_lines.append("")
                continue
            code_lines.append(line)
        ret = None
        for line in reversed(code_lines):
            s = line.split("--", 1)[0].strip()
            if s:
                m = re.fullmatch(r"return\s+([A-Za-z_]\w*)\s*;?", s)
                ret = m.group(1) if m else None
                break
        out, seen = [], set()
        for i, line in enumerate(code_lines):
            m = (re.match(r"^function\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", line)
                 or re.match(r"^function\s+([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(([^)]*)\)", line)
                 or re.match(r"^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*=\s*function\s*\(([^)]*)\)", line))
            if not m:
                continue
            if m.lastindex == 3:
                if m.group(1) not in (ret, stem):
                    continue
                name, params = m.group(2), m.group(3)
            else:
                name, params = m.group(1), m.group(2)
            if name in seen or not is_public(name):
                continue
            seen.add(name)
            plist = [p.strip() for p in params.split(",") if p.strip()]
            out.append(make_export(name, plist, stem, doc_above(lines, i, ("---", "--"))))
        return out

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>.ref.lua`` returning a table: ``local MathLib = require("MathLib.ref")``
        (rad.lua finds ``*.ref`` files in the project folder) then ``MathLib.Add(2, 3)``."""
        var = re.sub(r"\W", "_", lib)
        if var[:1].isdigit() or var in self.keywords:
            var = "_" + var
        kw = set(self.keywords)
        L = [header(lib, "--").rstrip("\n"),
             f"-- Use it from Lua:  local {var} = require(\"{lib}.ref\")   (or dofile(\"{lib}.ref.lua\"))",
             f"--                   local r = {var}.Name(args)",
             "local rad = require(\"rad\")",
             "local unpack = table.unpack or unpack",
             "",
             "local function call(name, ...)       -- trailing nil arguments are not sent",
             "  local n, args = select(\"#\", ...), { ... }",
             "  while n > 0 and args[n] == nil do n = n - 1 end",
             "  return rad.radcall(name, unpack(args, 1, n))",
             "end",
             "",
             f"local {var} = {{}}",
             ""]
        seen = set()
        for f in functions:
            if not valid_ident(f.name) or f.name in seen:
                continue
            seen.add(f.name)
            params, variadic = proxy_params(f.params, kw | {"self", "call", "rad", "args", "n"})
            if variadic:
                params.append("...")
            plist = ", ".join(params)
            target = f"{f.module}.{f.name}".replace("\\", "\\\\").replace('"', '\\"')
            fwd = ", ".join([f'"{target}"'] + params)
            if f.doc:
                L.append(f"--- {f.doc}")
            if f.name in kw:
                L.append(f"{var}[\"{f.name}\"] = function({plist}) return call({fwd}) end")
            else:
                L.append(f"function {var}.{f.name}({plist}) return call({fwd}) end")
        L += ["", f"return {var}", ""]
        return {f"{lib}.ref.lua": "\n".join(L)}

    def example_function(self, name: str) -> str:
        """Source of a Class Library module *name* with example public functions."""
        return (f"-- Class library {name}. The functions of the returned table can be called from every\n"
                f"-- project that references this library, in its own language, e.g.\n"
                f"--   Python: import {name}; {name}.Add(2, 3)     Lua: local {name} = require(\"{name}.ref\")\n"
                f"local M = {{}}\n\n"
                f"--- Add two numbers.\n"
                f"function M.Add(a, b)\n"
                f"  return a + b\n"
                f"end\n\n"
                f"--- Greeting text for who.\n"
                f"function M.Greet(who)\n"
                f"  return \"Hello, \" .. who .. \"!\"\n"
                f"end\n\n"
                f"return M\n")

    def _ref_libs(self, folder: Path, code: str) -> dict[str, list]:
        """variable/table name -> functions of the reference proxies (*.ref.lua) in *folder*."""
        libs: dict[str, list] = {}
        try:
            files = sorted(folder.glob("*.ref.lua"))
        except OSError:
            return libs
        alias = {}
        for var, mod in re.findall(r"\b(?:local\s+)?([A-Za-z_]\w*)\s*=\s*(?:require|dofile)\s*\(?\s*[\"']([^\"']+)",
                                   code):
            mod = mod[:-4] if mod.endswith(".lua") else mod
            alias.setdefault(mod.lower(), []).append(var)
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "AUTO-GENERATED by RAD IDE (reference to" not in text:
                continue
            lib = f.name[:-len(".ref.lua")]
            funcs = self.exported_functions(f, text, module=lib)
            for var in [lib, *alias.get(f"{lib}.ref".lower(), [])]:
                libs[var] = funcs
        return libs

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\.(\w+)\s*\([^()]*$", before)
        if m and path is not None:
            for f in self._ref_libs(Path(path).parent, code).get(m.group(1), []):
                if f.name == m.group(2):
                    return f"{m.group(1)}.{f.name}({', '.join(f.params)})" + (f" - {f.doc}" if f.doc else "")
        return super().calltip(code, line, col, path, names)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\.\w*$", before)
        if m and m.group(1) not in ("rad", "ui", "e") and path is not None:
            funcs = self._ref_libs(Path(path).parent, code).get(m.group(1))
            if funcs:
                return [Completion(f.name, "function", f"{f.name}({', '.join(f.params)})"
                                   + (f" - {f.doc}" if f.doc else "")) for f in funcs]
        if re.search(r"\brad\.\w*$", before):
            return [Completion(k, "method", v) for k, v in MEMBERS.items()]
        if re.search(r"\bui\.\w*$", before):
            return [Completion(n, "control", t) for n, t in (names or {}).items()]
        if re.search(r"\bui\.\w+[.:]\w*$", before):
            return [Completion(p, "property") for p in _property_names()] + \
                   [Completion(m, "method") for m in CONTROL_METHODS]
        if re.search(r"\be\.\w*$", before):
            return [Completion(k, "property") for k in ("X", "Y", "Button", "KeyCode", "KeyChar", "args")]
        return super().completions(code, line, col, path, names)


PLUGIN = LuaBridgePlugin()
