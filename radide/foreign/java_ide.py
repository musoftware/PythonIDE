"""Java projects of other IDEs opened IN PLACE: Maven (pom.xml), Gradle (build.gradle[.kts]),
Eclipse (.project/.classpath), IntelliJ IDEA (.idea + *.iml) and NetBeans (nbproject/ + Swing GUI
Builder .form files, designed here and written back with initComponents() regenerated).

Build/run with the project's own tool: mvnw/mvn, gradlew/gradle (the IDE also finds Gradle
distributions already downloaded by wrappers) or ant for NetBeans; otherwise javac into the IDE
state folder. Debug = JDWP (radide/jdwp_engine.py)."""
from __future__ import annotations

import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from ..model import Form
from ._others_base import (ChainSession, ForeignAdapter, ForeignProject, FormBinding, JavaDebugSession, RunTarget,
                           Step, find_gradle, find_java, find_maven, read_text_keep, show_projects, source_files,
                           tool_env)
from . import _nbform as NB

MAIN_RX = re.compile(r"public\s+static\s+void\s+main\s*\(")


def _strip_ns(root: ET.Element) -> ET.Element:
    for e in root.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return root


def _xml(path: Path) -> ET.Element | None:
    try:
        return _strip_ns(ET.parse(path).getroot())
    except (OSError, ET.ParseError):
        return None


def _props_file(path: Path) -> dict:
    out = {}
    try:
        text = path.read_text(encoding="latin-1")
    except OSError:
        return out
    text = re.sub(r"\\\r?\n\s*", "", text)
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#!":
            continue
        m = re.match(r"([^=:\s]+)\s*[=:]\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).replace("\\:", ":").replace("\\\\", "\\")
    return out


def _expand(v: str, props: dict, depth: int = 0) -> str:
    if depth > 8:
        return v
    return re.sub(r"\$\{([^}]+)\}", lambda m: _expand(props.get(m.group(1), m.group(0)), props, depth + 1), v)


def detect(folder: Path) -> Path | None:
    """The Java project file of a folder (priority: Maven, Gradle, NetBeans, IntelliJ, Eclipse)."""
    f = Path(folder)
    for name in ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"):
        if (f / name).exists():
            return f / name
    if (f / "nbproject" / "project.xml").exists():
        return f / "nbproject" / "project.xml"
    imls = sorted(f.glob("*.iml"))
    if (f / ".idea").is_dir() and imls:
        return imls[0]
    if (f / ".idea").is_dir() and any(f.rglob("*.java")):
        return f / ".idea"
    if (f / ".project").exists() and (f / ".classpath").exists():
        return f / ".project"
    return None


class NbFormBinding(FormBinding):
    kind = "netbeans-form"

    def __init__(self, name: str, native: Path, java: Path | None):
        super().__init__(name, native)
        self.code_path = java

    def load(self) -> Form:
        form, ctx = NB.read_nbform(self.native, self.name)
        if ctx.unsupported:
            self.notes.append(f"{self.native.name}: uses {', '.join(ctx.unsupported)} - text/property edits are "
                              "saved; layout/structure edits need NetBeans")
        return form

    def write(self, form: Form) -> list[str]:
        return NB.write_nbform(self.native, self.code_path, form)

    def handler_name(self, form, ctrl, event: str) -> str:
        cls = ctrl.props.get("NativeClass", "") if ctrl is not None else ""
        lis, method, _par = NB.event_info(cls, event)
        owner = ctrl.name if ctrl is not None else "form"
        return owner + method[:1].upper() + method[1:]

    def find_handler(self, code: str, name: str) -> int:
        for i, line in enumerate(code.splitlines()):
            if re.search(rf"\bvoid\s+{re.escape(name)}\s*\(", line):
                return i
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        found = self.find_handler(code, name)
        if found >= 0:
            return code, found
        # which control/event: name = <owner><Method>
        owner, ctrl = "form", None
        for c in form.controls:
            if name.startswith(c.name) and (ctrl is None or len(c.name) > len(ctrl.name)):
                ctrl = c
        if ctrl is not None:
            owner = ctrl.name
        method = name[len(owner):]
        method = method[:1].lower() + method[1:]
        info = None
        for _ev, (lis, m, par) in list(NB.EVENTS.items()) + [("SelectedIndexChanged", NB.LIST_SEL)]:
            if m == method:
                info = (lis, m, par)
                break
        if info is None:
            info = NB.EVENTS["Click"]
        evs = form.extra.setdefault("NativeEvents", {})
        evs.setdefault(owner, {})[info[1]] = {"listener": info[0], "parameters": info[2], "handler": name}
        new = NB._add_stub(code, name, info[2])
        line = self.find_handler(new, name) + 1
        return new, max(line, 0)


class JavaAdapter(ForeignAdapter):
    kind = "java"
    title = "Java project"
    base_language = "java-bridge"

    def __init__(self, native: Path):
        native = Path(native).resolve()
        if native.name == "project.xml" and native.parent.name == "nbproject":
            root = native.parent.parent
        elif native.is_dir():
            root = native.parent if native.name == ".idea" else native
        else:
            root = native.parent
        super().__init__(native, root)
        self.build = "javac"
        self.src_dirs: list[Path] = []
        self.res_dirs: list[Path] = []
        self.test_dirs: list[Path] = []
        self.libs: list[Path] = []
        self.out_dir = self.state / "classes"
        self.main_class = ""

    # ------------------------------------------------------------ scan
    def scan(self) -> None:
        n, r = self.native, self.root
        low = n.name.lower()
        if low == "pom.xml":
            self._maven()
        elif low.startswith(("build.gradle", "settings.gradle")):
            self._gradle()
        elif low == "project.xml" and n.parent.name == "nbproject":
            self._netbeans()
        elif low.endswith(".iml") or low == ".idea":
            self._intellij()
        else:
            self._eclipse()
        if not self.src_dirs:
            self.src_dirs = [d for d in (r / "src" / "main" / "java", r / "src") if d.is_dir()][:1]
        exts = (".java", ".form", ".xml", ".gradle", ".kts", ".properties", ".iml", ".md")
        if (r / "pubspec.yaml").exists():          # a Flutter project (flutter create writes .idea + .iml)
            exts += (".dart", ".yaml", ".json", ".arb")
        files = source_files(r, exts, extra_names=("pom.xml", ".project", ".classpath", "gradlew", "mvnw"))
        self.modules = [f for f in files if not f.lower().endswith(".form")]
        # NetBeans GUI forms (any Java project can have them)
        for f in files:
            if f.lower().endswith(".form"):
                fp = r / f
                java = fp.with_suffix(".java")
                try:
                    head = fp.read_bytes()[:400]
                except OSError:
                    continue
                if b"<Form" not in head:
                    continue
                self.add_binding(NbFormBinding(fp.stem, fp, java if java.exists() else None))
        mains = self._mains()
        if self.main_class and self.main_class not in mains:
            mains.insert(0, self.main_class)
        elif self.main_class:
            mains.remove(self.main_class)
            mains.insert(0, self.main_class)
        self.targets = [RunTarget(m, "java", {"main": m}) for m in mains]
        if self.build == "gradle" and self._gradle_app():
            self.targets.insert(0, RunTarget("gradle run", "gradle-run", {}))
        self.info.append(f"build: {self.build} ({self.tool() or 'tool not found - javac fallback'}); "
                         f"sources: {', '.join(self.rel(d) for d in self.src_dirs) or '-'}; "
                         f"main classes: {', '.join(mains[:5]) or '-'}")

    def _mains(self) -> list[str]:
        out = []
        for d in self.src_dirs:
            for f in sorted(d.rglob("*.java")):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if MAIN_RX.search(text):
                    pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
                    out.append((pkg.group(1) + "." if pkg else "") + f.stem)
        return out

    def _maven(self):
        self.title, self.build = "Maven project", "maven"
        x = _xml(self.native)
        if x is not None:
            self.name = (x.findtext("artifactId") or self.name).strip()
            props = {e.tag: (e.text or "").strip() for e in (x.find("properties") or [])}
            for path in (".//plugin/configuration/mainClass", ".//plugin/configuration/archive/manifest/mainClass"):
                v = x.findtext(path)
                if v:
                    self.main_class = _expand(v.strip(), props)
                    break
            self.main_class = self.main_class or props.get("exec.mainClass", "") or props.get("start-class", "")
            sd = x.findtext("build/sourceDirectory")
            if sd:
                self.src_dirs = [self.root / _expand(sd.strip(), {"project.basedir": str(self.root),
                                                                 "basedir": str(self.root)})]
        self.src_dirs = self.src_dirs or [d for d in [self.root / "src/main/java"] if d.is_dir()]
        self.res_dirs = [d for d in [self.root / "src/main/resources"] if d.is_dir()]
        self.test_dirs = [d for d in [self.root / "src/test/java"] if d.is_dir()]
        self.classes = self.root / "target" / "classes"

    def _gradle(self):
        self.title, self.build = "Gradle project", "gradle"
        text = self.native.read_text(encoding="utf-8", errors="replace")
        st = next((p for p in (self.root / "settings.gradle", self.root / "settings.gradle.kts") if p.exists()), None)
        if st is not None:
            m = re.search(r"rootProject\.name\s*=\s*['\"]([^'\"]+)", st.read_text(encoding="utf-8", errors="replace"))
            if m:
                self.name = m.group(1)
        m = re.search(r"mainClass(?:Name)?\s*(?:=|\.set\()\s*['\"]([\w.$]+)['\"]", text)
        if m:
            self.main_class = m.group(1)
        self._gradle_text = text
        sub = [d for d in (self.root / "app",) if (d / "build.gradle").exists() or (d / "build.gradle.kts").exists()]
        base = sub[0] if sub and not (self.root / "src").exists() else self.root
        if base is not self.root:
            bt = next((p for p in (base / "build.gradle", base / "build.gradle.kts") if p.exists()))
            t2 = bt.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"mainClass(?:Name)?\s*(?:=|\.set\()\s*['\"]([\w.$]+)['\"]", t2)
            self.main_class = m.group(1) if m else self.main_class
            self._gradle_text += t2
        self.src_dirs = [d for d in [base / "src/main/java"] if d.is_dir()]
        self.res_dirs = [d for d in [base / "src/main/resources"] if d.is_dir()]
        self.test_dirs = [d for d in [base / "src/test/java"] if d.is_dir()]
        self.classes = base / "build" / "classes" / "java" / "main"

    def _gradle_app(self) -> bool:
        return bool(re.search(r"\bapplication\b", getattr(self, "_gradle_text", "")))

    def _netbeans(self):
        self.title, self.build = "NetBeans project", "ant"
        x = _xml(self.native)
        if x is not None:
            nm = x.find(".//data/name")
            if nm is not None and nm.text:
                self.name = nm.text.strip()
        props = _props_file(self.root / "nbproject" / "project.properties")
        props.update(_props_file(self.root / "nbproject" / "private" / "private.properties"))
        self.main_class = props.get("main.class", "")
        srcs = [v for k, v in props.items() if k.startswith("src.") and k.endswith(".dir")]
        self.src_dirs = [self.root / _expand(s, props) for s in srcs if (self.root / _expand(s, props)).is_dir()]
        self.test_dirs = [self.root / _expand(v, props) for k, v in props.items()
                          if k.startswith("test.") and k.endswith(".dir") and (self.root / _expand(v, props)).is_dir()]
        cp = _expand(props.get("javac.classpath", ""), props)
        for part in re.split(r"[;:](?![\\/])", cp):
            p = (self.root / part.strip()) if part.strip() else None
            if p is not None and p.suffix == ".jar" and p.exists():
                self.libs.append(p)
        self.ant = shutil.which("ant") or ""
        if not self.ant:
            self.build = "javac"

    def _intellij(self):
        self.title = "IntelliJ IDEA project"
        iml = self.native if self.native.suffix == ".iml" else next(iter(sorted(self.root.glob("*.iml"))), None)
        if iml is not None:
            self.name = iml.stem
            x = _xml(iml)
            if x is not None:
                for sf in x.iter("sourceFolder"):
                    url = sf.get("url", "").replace("file://$MODULE_DIR$", str(iml.parent))
                    d = Path(url)
                    if not d.is_dir():
                        continue
                    if sf.get("isTestSource") == "true":
                        self.test_dirs.append(d)
                    elif sf.get("type") == "java-resource":
                        self.res_dirs.append(d)
                    else:
                        self.src_dirs.append(d)
                for jar in x.iter("root"):
                    url = jar.get("url", "")
                    m = re.match(r"jar://\$MODULE_DIR\$/(.+?)!/", url)
                    if m and (iml.parent / m.group(1)).exists():
                        self.libs.append(iml.parent / m.group(1))
        ws = self.root / ".idea" / "workspace.xml"
        x = _xml(ws) if ws.exists() else None
        if x is not None:
            for conf in x.iter("configuration"):
                if conf.get("type") == "Application":
                    mc = next((o.get("value") for o in conf.iter("option") if o.get("name") == "MAIN_CLASS_NAME"), "")
                    if mc:
                        self.main_class = mc
                        break
        if (self.root / "pom.xml").exists():
            self.build = "maven"
        elif any((self.root / g).exists() for g in ("build.gradle", "build.gradle.kts")):
            self.build = "gradle"

    def _eclipse(self):
        self.title = "Eclipse project"
        x = _xml(self.root / ".project")
        if x is not None and x.findtext("name"):
            self.name = x.findtext("name").strip()
        cp = _xml(self.root / ".classpath")
        if cp is not None:
            for e in cp.iter("classpathentry"):
                k, p = e.get("kind"), e.get("path", "")
                if k == "src" and (self.root / p).is_dir():
                    (self.test_dirs if "test" in p.lower() else self.src_dirs).append(self.root / p)
                elif k == "lib" and (self.root / p).exists():
                    self.libs.append(self.root / p)
        launch = next(iter(sorted(self.root.glob("*.launch"))), None)
        if launch is not None:
            lx = _xml(launch)
            if lx is not None:
                for a in lx.iter("stringAttribute"):
                    if a.get("key", "").endswith("MAIN_TYPE"):
                        self.main_class = a.get("value", "")

    # ------------------------------------------------------------ build / run
    def tool(self) -> str:
        if self.build == "maven":
            return find_maven(self.root) or find_java("javac")
        if self.build == "gradle":
            return find_gradle(self.root) or find_java("javac")
        if self.build == "ant":
            return getattr(self, "ant", "") or find_java("javac")
        return find_java("javac")

    def _javac_steps(self) -> tuple[list[Step], list[str]]:
        javac = find_java("javac")
        if not javac:
            raise RuntimeError("javac was not found (install a JDK)")
        out = self.out_dir
        out.mkdir(parents=True, exist_ok=True)
        srcs = [str(f) for d in self.src_dirs for f in sorted(d.rglob("*.java"))]
        listing = self.state / "sources.txt"
        listing.write_text("\n".join('"' + s.replace("\\", "/") + '"' for s in srcs), encoding="utf-8")
        cp = [str(out)] + [str(j) for j in self.libs]
        steps = [Step([javac, "-g", "-encoding", "UTF-8", "-d", str(out), "-cp", os.pathsep.join(cp),
                       f"@{listing}"], self.root, tool_env(), f"javac ({len(srcs)} files)")]
        for rd in self.res_dirs:                    # resources next to the classes
            for f in rd.rglob("*"):
                if f.is_file():
                    t = out / f.relative_to(rd)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, t)
        for d in self.src_dirs:                     # non-Java files of the source folders (icons, bundles)
            for f in d.rglob("*"):
                if f.is_file() and f.suffix.lower() not in (".java", ".form"):
                    t = out / f.relative_to(d)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, t)
        return steps, cp

    def build_steps(self, target, debug):
        if target is not None and target.kind == "gradle-run":
            return []
        tool = self.tool()
        self._cp = None
        if self.build == "maven" and tool and "javac" not in Path(tool).name.lower():
            cpfile = self.state / "maven-classpath.txt"
            self._cp_file = cpfile
            return [Step([tool, "-q", "-B", "compile", "dependency:build-classpath",
                          f"-Dmdep.outputFile={cpfile}"], self.root, tool_env(), "mvn compile")]
        if self.build == "gradle" and tool and "javac" not in Path(tool).name.lower():
            return [Step([tool, "-q", "--console=plain", "classes"], self.root, tool_env(), "gradle classes")]
        if self.build == "ant" and getattr(self, "ant", ""):
            return [Step([self.ant, "compile"], self.root, tool_env(), "ant compile")]
        steps, cp = self._javac_steps()
        self._cp = cp
        return steps

    def _classpath(self) -> str:
        if getattr(self, "_cp", None):
            return os.pathsep.join(self._cp)
        if self.build == "maven":
            extra = ""
            f = getattr(self, "_cp_file", None)
            if f is not None and f.exists():
                extra = f.read_text(encoding="utf-8").strip()
            return os.pathsep.join([str(self.root / "target" / "classes")] + ([extra] if extra else []))
        if self.build == "gradle":
            base = self.classes.parent.parent.parent
            return os.pathsep.join([str(self.classes), str(base / "build" / "resources" / "main")])
        if self.build == "ant":
            props = _props_file(self.root / "nbproject" / "project.properties")
            bc = _expand(props.get("build.classes.dir", "build/classes"), props)
            return os.pathsep.join([str(self.root / bc)] + [str(j) for j in self.libs])
        return os.pathsep.join([str(self.out_dir)] + [str(j) for j in self.libs])

    def run_step(self, target, debug, port: int = 0):
        if target is None:
            return None
        if target.kind == "gradle-run":
            g = find_gradle(self.root)
            return Step([g, "-q", "--console=plain", "run"] + (["--debug-jvm"] if debug else []), self.root,
                        tool_env(), "gradle run")
        java = find_java("java")
        agent = [f"-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:{port}"] if port else []
        # the Output window reads UTF-8: without these System.out writes the ANSI code page ("????" for Arabic)
        utf8 = ["-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8",
                "-Dsun.stdout.encoding=UTF-8", "-Dsun.stderr.encoding=UTF-8"]
        # the classpath is known only after the build (maven writes it): resolve it when the step starts
        return _LazyJavaStep([java] + utf8 + agent, self, target.data["main"])

    def debug_session(self, win, target, pre):
        from ..bridgedebug import free_port
        if target.kind == "gradle-run":
            return None
        port = free_port()
        run = self.run_step(target, True, port)
        return ChainSession(pre, lambda: JavaDebugSession(run.resolve(), port, win._all_breakpoints(), win), win)

    def commands(self):
        tool = self.tool()
        out = []
        if self.build == "maven" and tool:
            for goal in ("compile", "test", "package", "clean"):
                out.append((f"mvn {goal}", [Step([tool, "-B", goal], self.root, tool_env(), f"mvn {goal}")]))
        elif self.build == "gradle" and tool:
            for task in ("build", "test", "run", "clean"):
                out.append((f"gradle {task}", [Step([tool, "--console=plain", task], self.root, tool_env(),
                                                    f"gradle {task}")]))
        elif self.build == "ant":
            for task in ("compile", "jar", "test", "clean"):
                out.append((f"ant {task}", [Step([self.ant, task], self.root, tool_env(), f"ant {task}")]))
        out.append(("Compile with javac (IDE)", self._javac_steps()[0] if find_java("javac") else []))
        try:
            from .vscode_folder import vscode_commands
            out += vscode_commands(self.root)
        except Exception:  # noqa: BLE001
            pass
        return out


class _LazyJavaStep(Step):
    """A `java -cp <classpath> Main` step whose classpath is read when it runs."""

    def __init__(self, head: list, adapter: JavaAdapter, main: str):
        super().__init__(list(head), adapter.root, tool_env(), f"java {main}")
        self.adapter, self.main, self.head = adapter, main, list(head)

    def resolve(self) -> Step:
        return Step(self.head + ["-cp", self.adapter._classpath(), self.main], self.cwd, self.env, self.title)

    @property
    def argv(self):                       # noqa: D401 - evaluated when ChainSession starts the step
        return self.head + ["-cp", self.adapter._classpath(), self.main]

    @argv.setter
    def argv(self, v):
        pass


def open_java(win, path: Path) -> bool:
    path = Path(path)
    if path.is_dir():
        hit = detect(path)
        if hit is None:
            return False
        path = hit
    if path.name == ".classpath":
        path = path.parent / ".project"
    adapter = JavaAdapter(path)
    project = ForeignProject(adapter)
    return show_projects(win, [project], project.name, path)


def probe(folder: Path):
    return detect(folder)


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format(["pom.xml"], open_java, "Maven project (pom.xml)", folder_probe=probe, name="maven", priority=6)
    register_format(["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"], open_java, "Gradle project", name="gradle", priority=6)
    register_format([".iml"], open_java, "IntelliJ IDEA module", name="intellij", priority=4)
    register_format([".project", ".classpath"], open_java, "Eclipse project", name="eclipse", priority=4)
    register_format(["project.xml"], open_java, "NetBeans project (nbproject/project.xml)", name="netbeans",
                    priority=4)
    register_format([".form"], open_netbeans_form, "NetBeans GUI form", name="netbeans-form", priority=1)


def open_netbeans_form(win, path: Path) -> bool:
    """A .form file: open the Java project that contains it (or the folder)."""
    p = Path(path).resolve()
    try:
        if b"<Form" not in p.read_bytes()[:400]:
            return False
    except OSError:
        return False
    for d in [p.parent, *p.parents]:
        hit = detect(d)
        if hit is not None:
            return open_java(win, hit)
        if d.parent == d or (d / ".git").exists():
            break
    adapter = JavaAdapter(p.parent)
    adapter.native = p
    project = ForeignProject(adapter)
    return show_projects(win, [project], project.name, p)


__all__ = ["JavaAdapter", "NbFormBinding", "detect", "open_java", "register", "read_text_keep"]
