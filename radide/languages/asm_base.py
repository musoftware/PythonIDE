"""Shared base of the Assembly language plugins (asm_nasm.py, asm_fasm.py, asm_masm.py, asm_gas.py).

Projects are ordinary RAD projects (project.radproj) whose "asm" entry chooses the assembler, the architecture
and the linker (radide/asm/build.py). Build / Run / Debug go through the GUI Bridge runner
(radide/runtimes/bridge.py): ``--build "python -m radide.asm.build <folder>"`` then ``_radapp.exe`` - as a
console program (no forms: the Output window, stdin from the Program Input bar or an external console) or as a
GUI Bridge program (NASM x64 forms: radide/asm/formgen.py). docs/ASSEMBLY.md has the whole picture.

Editor features (highlighting, IntelliSense, hover, F12, outline) come from the Assembly editor support
(radide/asm_intel: ``AsmIntelMixin`` is the first base class); without it the plugin falls back to its own
keyword lists (``_FallbackIntel``).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..model import Form, Project
from .base import Completion, RunSpec
from .bridgebase import CLIENTS, IDE_ROOT, BridgeLanguagePlugin

ASM_RUNTIME = Path(__file__).resolve().parent.parent / "asm" / "runtime"

X86_MNEMONICS = """mov movzx movsx movsxd lea push pop xchg add sub inc dec neg imul mul idiv div cmp test and or
    xor not shl shr sal sar rol ror rcl rcr jmp je jne jz jnz jg jge jl jle ja jae jb jbe jc jnc jo jno js jns
    call ret leave enter nop int loop loope loopne cmove cmovne cmovg cmovl cmovge cmovle cmova cmovb sete
    setne setg setl seta setb cbw cwde cdqe cwd cdq cqo movsb movsw movsd movsq stosb stosw stosd stosq lodsb
    rep repe repne cld std clc stc bt bts btr bsf bsr popcnt lzcnt tzcnt adc sbb syscall cpuid rdtsc hlt
    movss movsd movaps movups movapd movdqa movdqu addss addsd subss subsd mulss mulsd divss divsd sqrtss
    sqrtsd cvtsi2sd cvtsi2ss cvttsd2si cvttss2si cvtss2sd cvtsd2ss comisd comiss ucomisd pxor xorps xorpd""".split()
X86_REGISTERS = """rax rbx rcx rdx rsi rdi rbp rsp r8 r9 r10 r11 r12 r13 r14 r15 eax ebx ecx edx esi edi ebp esp
    r8d r9d r10d r11d r12d r13d r14d r15d ax bx cx dx si di bp sp al bl cl dl ah bh ch dh sil dil bpl spl r8b
    r9b r10b r11b r12b r13b r14b r15b r8w r9w r10w r11w r12w r13w r14w r15w rip eip xmm0 xmm1 xmm2 xmm3 xmm4
    xmm5 xmm6 xmm7 xmm8 xmm9 xmm10 xmm11 xmm12 xmm13 xmm14 xmm15 cs ds es fs gs ss""".split()
RAD_MACROS = {
    "handler": "handler <Control>_<Event>  - start an event handler (global label + stack frame)",
    "endhandler": "endhandler  - end an event handler (restore registers, ret)",
    "rad_set": "rad_set obj, prop, text  - set a property: rad_set lblOut, \"Text\", \"Hi\"",
    "rad_get": "rad_get obj, prop  -> RAX = text (char*)",
    "rad_set_int": "rad_set_int obj, prop, n  - set a property to an integer (register, number, [mem])",
    "rad_get_int": "rad_get_int obj, prop  -> RAX = integer",
    "rad_call": "rad_call obj, method, args  -> RAX = text (e.g. rad_call lstLog, \"AddItem\", \"x\")",
    "rad_msgbox": "rad_msgbox text  - message box", "rad_input": "rad_input prompt  -> RAX = text typed",
    "rad_show": "rad_show form", "rad_hide": "rad_hide form", "rad_end": "rad_end  - quit the program",
    "rad_print": "rad_print text  - a line in the Output window",
    "rad_arg": "rad_arg n  -> RAX = event argument n (0 X, 1 Y, 2 Button, 3 KeyCode, 4 KeyChar)",
    "rad_str_int": "rad_str_int n  -> RAX = text of the integer n",
    "rad_int_str": "rad_int_str text  -> RAX = integer value of text",
    "radcall": "radcall \"Module.func\", \"[json args]\"  -> RAX = JSON text of the result (RAD Hub)",
}


class _FallbackIntel:
    """Plain keyword completions / outline, used only when the Assembly editor support (radide/asm_intel) is
    missing. With it, AsmIntelMixin gives completions, signature help, hover, F12, references and the outline."""
    asm_intel = False

    def completions(self, code, line, col, path=None, names=None):
        import re
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(r, "variable", "register") for r in self.builtins]
        if getattr(self, "supports_forms", False):
            out += [Completion(k, "function", d) for k, d in RAD_MACROS.items()]
            out += [Completion(n, "control", t) for n, t in (names or {}).items()]
        seen = {c.name.lower() for c in out}
        for w in re.findall(r"^\s*([A-Za-z_.$?@][\w.$?@]*)\s*:", code, re.M):
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(Completion(w, "function", "label"))
        return out

    def calltip(self, code, line, col, path=None, names=None):
        import re
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        w = re.match(r"^\s*(\w+)", before)
        return RAD_MACROS.get(w.group(1).lower(), "") if (w and getattr(self, "supports_forms", False)) else ""

    def document_symbols(self, code: str) -> list[dict]:
        import re
        out = []
        for i, ln in enumerate(code.splitlines()):
            mm = re.match(r"^\s*(?:handler\s+(\w+)|([A-Za-z_$?@][\w$?@]*)\s*:(?![:=]))", ln)
            if mm:
                out.append({"name": mm.group(1) or mm.group(2), "kind": "function", "line": i, "detail": "",
                            "children": []})
        return out


try:                       # editor slice: radide/asm_intel (completions, hover, F12, outline, Monaco grammar)
    from ..asm_intel.plugin import AsmIntelMixin as _IntelBase
except Exception:  # noqa: BLE001 - optional
    _IntelBase = _FallbackIntel


class AsmPluginBase(_IntelBase, BridgeLanguagePlugin):
    """An Assembly dialect. Subclasses set id, display_name, code_ext, assembler and the syntax lists."""
    assembler = "nasm"                 # radide/asm/build.py key
    asm_dialect = "nasm"               # radide/asm_intel dialect (nasm / fasm / masm / gas)
    tool_key = "nasm"                  # radide/asm/toolchain.py key of the assembler
    downloadable = True                # NASM / FASM are downloaded on the first build
    case_sensitive = False
    line_comments = [";"]
    block_comment = None
    string_quotes = ['"', "'", "`"]
    keywords = X86_MNEMONICS
    builtins = X86_REGISTERS
    has_forms = True
    project_name_base = "AsmApp"
    supports_forms = False             # GUI Bridge forms (NASM x64 / x86, FASM x64, GNU as x64)
    form_flavor = "nasm64"             # radide/asm/formgen.py flavor of a new form when nothing else says
    install_hint = ""

    # ------------------------------------------------------------ tools
    @property
    def tool_names(self) -> list[str]:          # type: ignore[override]
        return [self.tool_key]

    def tool(self) -> str:
        from ..asm import toolchain as tc
        exe = tc.find(self.tool_key)
        if exe:
            return exe
        if self.downloadable and self.tool_key in tc.RELEASES:     # downloaded by the first build
            return str(tc.tools_root() / self.tool_key / ("FASM.EXE" if self.tool_key == "fasm" else "nasm.exe"))
        return ""

    def settings(self, project: Project) -> dict:
        from ..asm.build import settings_for
        return settings_for(project, self.id)

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..asm.templates import for_plugin
        return [(t.id, t.title, t.description, t.icon) for t in for_plugin(self.id)]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..asm.templates import BY_ID, for_plugin
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        t = BY_ID.get(template) or for_plugin(self.id)[0]
        if t.forms:
            from ..asm.formgen import flavor_for
            from ..workspace import create_project
            flavor = flavor_for(t.settings) or self.form_flavor
            self._flavor_hint = flavor
            project = create_project(folder, name, self.id)
            self._form_template(project, flavor)
        else:
            import re
            project = Project(folder, name, self.id)
            ident = re.sub(r"\W", "_", name)
            subst = {"{name}": name, "{guard}": ident.upper() + "_H", "{ident}": ident}
            first = ""
            for fname, text in t.files:
                for k, v in subst.items():
                    fname, text = fname.replace(k, v), text.replace(k, v)
                p = folder / fname
                if not p.exists():
                    p.write_text(text, encoding="utf-8")
                if Path(fname).suffix.lower() in (".asm", ".s", ".nasm", ".fasm", ".inc"):
                    project.modules.append(fname)        # (C / Python / C# helpers stay plain files)
                    first = first or fname
            project.startup = Path(first).stem if first else ""
        project.extra["asm"] = dict(t.settings)
        if not (folder / ".gitignore").exists():
            extra = f"{name}.dll\nlib{name}.a\n" if t.settings.get("output") == "dll" else ""
            (folder / ".gitignore").write_text("_build/\n_radapp.exe\n_radmain.asm\n" + extra, encoding="utf-8")
        project.save()
        return project

    def _form_template(self, project: Project, flavor: str = "nasm64") -> None:
        """The Windows Forms template: Form1 with a label, a text box and two buttons."""
        from ..features.templates import _add
        name = project.forms[0]
        fp = project.form_path(name)
        form = Form.load(fp)
        form.props.update(Text="Assembly Windows Forms", Width=430, Height=230)
        _add(form, "Label", "lblMessage", 16, 16, 390, 34, Text="")
        _add(form, "TextBox", "txtNumber", 16, 64, 120, 22, Text="41")
        _add(form, "Button", "btnAdd", 150, 62, 100, 26, Text="Add 1")
        _add(form, "Button", "btnHello", 262, 62, 140, 26, Text="Say hello")
        _add(form, "Label", "lblClicksCaption", 16, 110, 120, 20, Text="Clicks:")
        _add(form, "Label", "lblClicks", 140, 110, 100, 20, Text="0")
        form.save(fp)
        from ..asm.templates import form_code
        code = form_code(name, flavor)
        (project.folder / self.code_file(name)).write_text(code, encoding="utf-8")
        (project.folder / self.designer_file(name)).write_text(self.generate_designer(form, code), encoding="utf-8")
        self.copy_clients(project.folder, flavor)

    def copy_clients(self, folder: Path, flavor: str | None = None) -> None:
        for target, src in self.client_files_for(flavor or self.form_flavor).items():
            try:
                shutil.copy2(src, Path(folder) / target)
            except OSError:
                pass

    # ------------------------------------------------------------ forms / handlers
    def designer_file(self, form_name: str) -> str:
        return f"{form_name}.inc"

    def code_flavor(self, user_code: str) -> str:
        """The flavor a form's code was written for (the runtime include it names), else the plugin's own."""
        from ..asm.formgen import RUNTIME_INCLUDE
        for flavor, inc in RUNTIME_INCLUDE.items():
            if flavor != "nasm64" and inc in (user_code or ""):
                return flavor
        return "nasm64" if "radgui.inc" in (user_code or "") else self.form_flavor

    def project_flavor(self, project: Project) -> str:
        from ..asm.formgen import flavor_for
        return flavor_for(self.settings(project), project.folder, project.forms) or self.form_flavor

    def generate_designer(self, form: Form, user_code: str) -> str:
        from ..asm.formgen import designer_include_for
        return designer_include_for(form, self.code_flavor(user_code))

    def new_code(self, form: Form, is_startup: bool) -> str:
        """An empty form's code: the header of the template + a Load handler (in the flavor of the project
        last prepared / created with this plugin; prepare() rewrites an untouched one of another flavor)."""
        from ..asm.templates import new_form_code
        return new_form_code(form.name, getattr(self, "_flavor_hint", "") or self.form_flavor)

    def find_handler(self, code: str, name: str) -> int:
        import re
        line = self._find_line(code, rf"^\s*handler\s+{re.escape(name)}\b", re.I)
        return line if line >= 0 else self._find_line(code, rf"^\s*{re.escape(name)}\s*:", re.I)

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"handler {name}", "    ", "endhandler"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def handlers_in_project(self, folder: Path, project: Project) -> list[str]:
        from ..asm.formgen import handlers_in
        out: list[str] = []
        for f in project.forms:
            if getattr(project, "form_language", lambda _f: project.language)(f) != self.id:
                continue
            p = Path(folder) / self.code_file(f)
            if p.exists():
                for h in handlers_in(p.read_text(encoding="utf-8", errors="replace")):
                    if h not in out:
                        out.append(h)
        return out

    def client_files(self) -> dict[str, Path]:
        return self.client_files_for(self.form_flavor)

    def client_files_for(self, flavor: str) -> dict[str, Path]:
        """GUI Bridge files copied into a form project of *flavor* (radide/asm/formgen.py)."""
        if not self.supports_forms:
            return {}
        from ..asm.formgen import RUNTIME_INCLUDE
        files = {"radgui.h": CLIENTS / "c" / "radgui.h", "radgui.c": CLIENTS / "c" / "radgui.c",
                 "radasm.c": ASM_RUNTIME / "radasm.c"}
        inc = RUNTIME_INCLUDE.get(flavor, "radgui.inc")
        files[inc] = ASM_RUNTIME / inc
        if flavor == "nasm32":
            files["radcrt32.c"] = ASM_RUNTIME / "radcrt32.c"
        return files

    def main_source(self, project: Project):
        if not self.supports_forms or not project.forms:
            return None
        from ..asm.formgen import main_name, main_program_for
        flavor = self.project_flavor(project)
        return main_name(flavor), main_program_for(self.handlers_in_project(project.folder, project), flavor)

    def prepare(self, folder: Path, project: Project) -> None:
        if not project.forms:                    # console program: no GUI Bridge files
            return
        from ..asm.templates import new_form_code
        flavor = self.project_flavor(project)
        self._flavor_hint = flavor
        for target, src in self.client_files_for(flavor).items():
            shutil.copy2(src, Path(folder) / target)
        main = self.main_source(project)
        if main is not None:
            (Path(folder) / main[0]).write_text(main[1], encoding="utf-8")
        for f in project.forms:
            if getattr(project, "form_language", lambda _f: project.language)(f) != self.id:
                continue
            try:
                form = Form.load(project.form_path(f))
                code_path = Path(folder) / self.code_file(f)
                code = code_path.read_text(encoding="utf-8", errors="replace") if code_path.exists() else ""
                # a form added before the project's flavor was known: its untouched code is rewritten
                if code and self.code_flavor(code) != flavor and any(
                        code == new_form_code(f, other) for other in ("nasm64", "nasm32", "fasm64", "gas64", "gas64i")):
                    code = new_form_code(f, flavor)
                    code_path.write_text(code, encoding="utf-8")
                # Form1.inc may be older than the form (forms edited outside the IDE): rewrite it
                from ..asm.formgen import designer_include_for
                target = Path(folder) / self.designer_file(f)
                text = designer_include_for(form, flavor)
                if not target.exists() or target.read_text(encoding="utf-8", errors="replace") != text:
                    target.write_text(text, encoding="utf-8")
            except (OSError, ValueError, KeyError):
                continue

    # ------------------------------------------------------------ build / run
    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{sys.executable}" -m radide.asm.build "{Path(folder)}"'

    def run_command(self, folder: Path, project: Project) -> list[str]:
        if self.settings(project).get("output") == "dll":     # a class library: run its Python ctypes client
            client = Path(folder) / "UseFromPython.py"
            return [sys.executable, "-u", str(client)] if client.is_file() else \
                [sys.executable, "-c", f"print('{project.name}.dll built')"]
        exe = str(Path(folder) / "_radapp.exe")
        if not project.forms and self.settings(project).get("console") == "external":
            return [sys.executable, "-m", "radide.asm.console", exe]
        return [exe]

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        project = Project.load(folder)
        self.prepare(Path(folder), project)
        args = ["-u", "-m", "radide.runtimes.bridge", str(folder), "--build", self.build_command(folder, project),
                "--"] + self.run_command(folder, project)
        env = dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8",
                   RAD_HANDLERS=",".join(self.handlers_in_project(folder, project)))
        from ..asm import toolchain as tc
        gcc = tc.mingw("gcc")
        if gcc:
            env["PATH"] = str(Path(gcc).parent) + os.pathsep + env.get("PATH", "")
        return RunSpec(sys.executable, args, Path(folder), env)

    def make_session(self, win, spec, debug: bool):
        """MainWindow._make_session hook: F5 on a console project builds, then launches the program under gdb
        (radide/nativedbg.py, native debugger part). None = the IDE's usual session (Ctrl+F5, forms)."""
        try:
            from ..nativedbg import asm_console_session
        except Exception:  # noqa: BLE001 - the native debugger is optional
            return None
        try:
            if self.settings(Project.load(Path(spec.cwd))).get("output") == "dll":
                return None                      # a class library runs its client (Python) the usual way
        except Exception:  # noqa: BLE001
            pass
        return asm_console_session(win, self, spec, debug)

    def debug_info(self, project: Project) -> dict:
        """For the native debugger: what the build produces (docs/ASSEMBLY.md, "Debug information")."""
        s = self.settings(project)
        # NASM / GNU as always; FASM and MASM when the last build added the DWARF lines (radide/asm/linetable.py)
        gdb_lines = s.get("debug", True) and (s["assembler"] in ("nasm", "gas") or
                                              (Path(project.folder) / "_build" / "dwarf.ok").is_file())
        return {"exe": str(Path(project.folder) / "_radapp.exe"), "arch": s["arch"], "assembler": s["assembler"],
                "linker": s["linker"], "line_info": "dwarf" if gdb_lines else
                ("codeview" if s["assembler"] == "masm" else "none"),
                "listings": str(Path(project.folder) / "_build")}

    # ------------------------------------------------------------ modules
    def module_template(self, name: str) -> str:
        return ""
