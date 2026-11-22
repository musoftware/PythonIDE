"""Java language plugin (GUI Bridge + JDK).

Project folder: Form1.java (handlers), Form1_designer.java (generated control fields), modules (*.java),
libs/*.jar (libraries - Project > Packages downloads them from Maven Central with their dependencies).
<project>/_build/java holds the client (Rad*.java), the generated RadMain.java and the compiled classes.
Compilation is skipped when no source or library changed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from ..model import Form, Project
from . import _refs_dotnet_java as refs
from .base import Completion, PackageManager
from .bridgebase import CLIENTS, BridgeLanguagePlugin

CLIENT_DIR = CLIENTS / "java"
RADJAVA = CLIENT_DIR / "radjava.py"
BUILD_DIR = "_build/java"
LIBS = "libs"
MANIFEST = "libs/maven.json"
CLIENT_SOURCES = ("Rad.java", "RadControl.java", "RadEvent.java", "RadJson.java")
MAVEN = "https://repo1.maven.org/maven2"
SEARCH = "https://search.maven.org/solrsearch/select?q={q}&rows=25&wt=json"

JAVA_KEYWORDS = """abstract assert boolean break byte case catch char class const continue default do double else
    enum extends final finally float for goto if implements import instanceof int interface long native new
    package private protected public return short static strictfp super switch synchronized this throw throws
    transient try void volatile while true false null var record yield""".split()

RAD_HELPERS = {
    "msgbox": "msgbox(Object text) - message box, returns 1",
    "input": "input(Object prompt) - ask for a text",
    "set": "set(String obj, String prop, Object value) - e.g. set(\"lblOut\", \"Caption\", \"Hi\")",
    "get": "get(String obj, String prop) - read a property as text",
    "getNumber": "getNumber(String obj, String prop) - read a property as a number",
    "call": "call(String obj, String method, Object... args) - e.g. call(\"lstLog\", \"AddItem\", \"x\")",
    "show": "show(String form) - show another form", "hide": "hide(String form) - hide a form",
    "end": "end() - close the program",
    "radcall": "radcall(\"Module.function\", args...) - call a function of a project module (any language)",
    "radcallNumber": "radcallNumber(\"Module.function\", args...) - radcall returning a double",
    "toInt": "toInt(String s) - text to int", "toNumber": "toNumber(String s) - text to double",
    "toBool": "toBool(String s) - \"True\"/\"1\" -> true", "str": "str(Object v) - value as text",
}
CONTROL_MEMBERS = {
    "getText": "String getText()", "setText": "setText(Object v)", "getCaption": "String getCaption()",
    "setCaption": "setCaption(Object v)", "getValue": "String getValue()", "setValue": "setValue(Object v)",
    "getNumber": "double getNumber() - Text as a number", "isEnabled": "boolean isEnabled()",
    "setEnabled": "setEnabled(boolean v)", "isVisible": "boolean isVisible()", "setVisible": "setVisible(boolean v)",
    "getLeft": "int getLeft()", "setLeft": "setLeft(int v)", "getTop": "int getTop()", "setTop": "setTop(int v)",
    "getWidth": "int getWidth()", "setWidth": "setWidth(int v)", "getHeight": "int getHeight()",
    "setHeight": "setHeight(int v)", "getBackColor": "String getBackColor()", "setBackColor": "setBackColor(Object v)",
    "getForeColor": "String getForeColor()", "setForeColor": "setForeColor(Object v)",
    "getListIndex": "int getListIndex()", "setListIndex": "setListIndex(int v)", "getListCount": "int getListCount()",
    "getInterval": "int getInterval()", "setInterval": "setInterval(int v)", "addItem": "addItem(Object item)",
    "removeItem": "removeItem(int index)", "clear": "clear()", "list": "String list(int index)",
    "setFocus": "setFocus()", "move": "move(int left, int top, int width, int height)",
    "showDialog": "String showDialog() - OK/Cancel", "get": "String get(String prop)",
    "set": "set(String prop, Object value)", "call": "String call(String method, Object... args)",
    "show": "show()", "hide": "hide()",
}
EVENT_MEMBERS = {"x": "int", "y": "int", "button": "int", "keyCode": "int", "keyChar": "String",
                 "sender": "String - control name", "name": "String - event name", "args": "String - raw args"}


# ====================================================================== JDK
def _jdk_dirs() -> list[Path]:
    out = []
    jh = os.environ.get("JAVA_HOME")
    if jh:
        out.append(Path(jh) / "bin")
    w = shutil.which("javac")
    if w:
        out.append(Path(w).parent)
    pats = [os.path.expandvars(r"%LOCALAPPDATA%\Java\jdk*\bin"), r"C:\Program Files\Java\jdk*\bin",
            r"C:\Program Files\Eclipse Adoptium\jdk*\bin", r"C:\Program Files\Microsoft\jdk*\bin",
            r"C:\Program Files\Zulu\zulu*\bin", r"C:\Program Files\Amazon Corretto\jdk*\bin"]
    for pat in pats:
        out += [Path(p) for p in sorted(glob.glob(pat), reverse=True)]
    return out


def jdk_bin() -> Path | None:
    exe = ".exe" if os.name == "nt" else ""
    for d in _jdk_dirs():
        if (d / f"javac{exe}").exists() and (d / f"java{exe}").exists():
            return d
    return None


def _tool(name: str) -> str:
    d = jdk_bin()
    return str(d / (name + (".exe" if os.name == "nt" else ""))) if d else ""


# ====================================================================== build
def build_dir(folder: Path) -> Path:
    return Path(folder) / BUILD_DIR


def user_sources(folder: Path) -> list[Path]:
    return sorted(Path(folder).glob("*.java"))


def class_names(folder: Path) -> list[str]:
    return [p.stem for p in user_sources(folder)
            if not p.stem.endswith("_designer") and "." not in p.stem]   # X.ref.java = reference proxy


def classpath(folder: Path) -> str:
    return os.pathsep.join([str(build_dir(folder) / "classes"), str(Path(folder) / LIBS / "*")])


def ensure_build_dir(folder: Path) -> None:
    b = build_dir(folder)
    b.mkdir(parents=True, exist_ok=True)
    for name in CLIENT_SOURCES:
        src, dst = CLIENT_DIR / name, b / name
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copy2(src, dst)
    main = (CLIENT_DIR / "RadMain.java").read_text(encoding="utf-8").replace(
        "/*CLASSES*/", ", ".join(json.dumps(c) for c in class_names(folder)))
    dst = b / "RadMain.java"
    if not dst.exists() or dst.read_text(encoding="utf-8") != main:
        dst.write_text(main, encoding="utf-8")


def _fingerprint(folder: Path) -> str:
    h = hashlib.sha1()
    files = user_sources(folder) + sorted(build_dir(folder).glob("*.java"))
    for p in files:
        h.update(p.name.encode("utf-8") + b"|" + p.read_bytes() + b"|")
    for jar in sorted((Path(folder) / LIBS).glob("*.jar")):
        h.update(jar.name.encode("utf-8") + str(jar.stat().st_size).encode() + b"|")
    return h.hexdigest()


def up_to_date(folder: Path) -> bool:
    stamp = build_dir(folder) / ".inputs"
    return (build_dir(folder) / "classes" / "RadMain.class").exists() and stamp.exists() and \
        stamp.read_text(encoding="utf-8").strip() == _fingerprint(folder)


def build(folder: Path, out=None, force: bool = False) -> int:
    out = out or sys.stdout
    folder = Path(os.path.abspath(folder))
    javac = _tool("javac")
    if not javac:
        print("Java: no JDK (javac) was found. Install one (winget install EclipseAdoptium.Temurin.17.JDK) "
              "or set JAVA_HOME.", file=out, flush=True)
        return 1
    ensure_build_dir(folder)
    if not force and up_to_date(folder):
        print("Java: up to date", file=out, flush=True)
        return 0
    classes = build_dir(folder) / "classes"
    shutil.rmtree(classes, ignore_errors=True)
    classes.mkdir(parents=True)
    sources = [p.name for p in user_sources(folder)] + \
              [f"{BUILD_DIR}/{p.name}" for p in sorted(build_dir(folder).glob("*.java"))]
    argfile = build_dir(folder) / "sources.txt"
    argfile.write_text("\n".join(f'"{s}"' for s in sources), encoding="utf-8")
    cmd = [javac, "-encoding", "UTF-8", "-g", "-nowarn", "-d", str(classes), "-cp", classpath(folder),
           f"@{argfile}"]
    r = subprocess.run(cmd, cwd=str(folder), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, JAVA_TOOL_OPTIONS="-Duser.language=en"))
    text = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if not l.startswith("Picked up JAVA_TOOL"))
    if text.strip():
        print(text.strip(), file=out, flush=True)
    if r.returncode == 0:
        (build_dir(folder) / ".inputs").write_text(_fingerprint(folder), encoding="utf-8")
    return r.returncode


def java_command(folder: Path, *args: str) -> list[str]:
    return [_tool("java") or "java", "-Dfile.encoding=UTF-8", "-XX:TieredStopAtLevel=1", "-XX:+UseSerialGC",
            "-Xshare:auto", "-cp", classpath(Path(os.path.abspath(folder))), "RadMain", *args]


# ====================================================================== Maven Central
def _fetch(url: str, timeout: float = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _repo_path(group: str, artifact: str) -> str:
    return f"{MAVEN}/{group.replace('.', '/')}/{artifact}"


def latest_version(group: str, artifact: str) -> str:
    root = ET.fromstring(_fetch(f"{_repo_path(group, artifact)}/maven-metadata.xml"))
    for tag in ("versioning/release", "versioning/latest"):
        v = root.findtext(tag)
        if v:
            return v.strip()
    versions = [v.text for v in root.iter("version") if v.text]
    if not versions:
        raise RuntimeError(f"no versions of {group}:{artifact} on Maven Central")
    return versions[-1]


class _Pom:
    """The parts of a POM we need, with parent inheritance and ${property} expansion."""
    _cache: dict = {}

    def __init__(self, group: str, artifact: str, version: str, depth: int = 0):
        self.group, self.artifact, self.version = group, artifact, version
        xml = _fetch(f"{_repo_path(group, artifact)}/{version}/{artifact}-{version}.pom")
        root = ET.fromstring(xml)
        ns = re.match(r"\{.*\}", root.tag)
        self.ns = ns.group(0) if ns else ""
        self.root = root
        self.packaging = self._text(root, "packaging") or "jar"
        self.parent = None
        par = root.find(self._q("parent"))
        if par is not None and depth < 10:
            pg, pa, pv = (self._text(par, k) for k in ("groupId", "artifactId", "version"))
            try:
                self.parent = _Pom.get(pg, pa, pv, depth + 1)
            except (urllib.error.URLError, ET.ParseError, OSError):
                self.parent = None
        self.props = dict(self.parent.props) if self.parent else {}
        props = root.find(self._q("properties"))
        if props is not None:
            for p in props:
                self.props[p.tag.replace(self.ns, "")] = (p.text or "").strip()
        self.props.update({"project.groupId": group, "project.artifactId": artifact,
                           "project.version": version, "pom.version": version, "version": version,
                           "project.parent.version": self.parent.version if self.parent else version,
                           "project.parent.groupId": self.parent.group if self.parent else group})
        self.managed = dict(self.parent.managed) if self.parent else {}
        dm = root.find(self._q("dependencyManagement"))
        if dm is not None:
            for d in dm.iter(self._q("dependency")):
                g, a, v = (self.expand(self._text(d, k)) for k in ("groupId", "artifactId", "version"))
                if (self._text(d, "scope") or "") == "import" and (self._text(d, "type") or "") == "pom":
                    try:
                        self.managed.update({k: v2 for k, v2 in _Pom.get(g, a, v, depth + 1).managed.items()
                                             if k not in self.managed})
                    except (urllib.error.URLError, ET.ParseError, OSError):
                        pass
                    continue
                if g and a and v:
                    self.managed[f"{g}:{a}"] = v

    @classmethod
    def get(cls, g, a, v, depth=0):
        key = (g, a, v)
        if key not in cls._cache:
            cls._cache[key] = _Pom(g, a, v, depth)
        return cls._cache[key]

    def _q(self, tag):
        return f"{self.ns}{tag}"

    def _text(self, el, tag):
        t = el.findtext(self._q(tag))
        return t.strip() if t else ""

    def expand(self, s: str) -> str:
        for _ in range(10):
            m = re.search(r"\$\{([^}]+)\}", s or "")
            if not m:
                break
            s = s.replace(m.group(0), self.props.get(m.group(1), ""))
        return s or ""

    def dependencies(self) -> list[tuple[str, str, str]]:
        out = []
        deps = self.root.find(self._q("dependencies"))
        if deps is None:
            return out
        for d in deps.findall(self._q("dependency")):
            scope = self._text(d, "scope") or "compile"
            if scope not in ("compile", "runtime") or self._text(d, "optional") == "true":
                continue
            if (self._text(d, "type") or "jar") not in ("jar", "bundle"):
                continue
            g, a = self.expand(self._text(d, "groupId")), self.expand(self._text(d, "artifactId"))
            v = self.expand(self._text(d, "version")) or self.managed.get(f"{g}:{a}", "")
            v = self.expand(v)
            out.append((g, a, v))
        return out


def _clean_version(v: str) -> str:
    """Maven ranges like [1.2,2.0) -> the lower bound."""
    m = re.match(r"^[\[(]\s*([^,\])]*)", v or "")
    return m.group(1).strip() if m else (v or "")


def _load_manifest(folder: Path) -> dict:
    p = Path(folder) / MANIFEST
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"packages": {}}


def _save_manifest(folder: Path, data: dict) -> None:
    p = Path(folder) / MANIFEST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def maven_add(folder: Path, spec: str) -> int:
    parts = spec.strip().split(":")
    if len(parts) < 2:
        print(f"Maven: use group:artifact[:version], for example com.google.code.gson:gson (got '{spec}')",
              file=sys.stderr)
        return 2
    group, artifact = parts[0], parts[1]
    version = parts[2] if len(parts) > 2 and parts[2] else ""
    libs = Path(folder) / LIBS
    libs.mkdir(parents=True, exist_ok=True)
    try:
        version = version or latest_version(group, artifact)
    except (urllib.error.URLError, ET.ParseError, OSError, RuntimeError) as e:
        print(f"Maven: {group}:{artifact} was not found on Maven Central ({e})", file=sys.stderr)
        return 1
    print(f"Resolving {group}:{artifact}:{version} ...", flush=True)
    queue, seen, jars = [(group, artifact, version, 0)], {}, []
    while queue:
        g, a, v, depth = queue.pop(0)
        if f"{g}:{a}" in seen:
            continue
        v = _clean_version(v)
        if not v:
            try:
                v = latest_version(g, a)
            except (urllib.error.URLError, ET.ParseError, OSError, RuntimeError):
                print(f"  ! {g}:{a}: no version found - skipped", flush=True)
                continue
        seen[f"{g}:{a}"] = v
        try:
            pom = _Pom.get(g, a, v)
        except (urllib.error.URLError, ET.ParseError, OSError) as e:
            if depth == 0:
                print(f"Maven: cannot read the POM of {g}:{a}:{v} ({e})", file=sys.stderr)
                return 1
            print(f"  ! {g}:{a}:{v}: POM not readable - skipped", flush=True)
            continue
        if pom.packaging in ("jar", "bundle", "maven-plugin") or pom.packaging.endswith("jar"):
            name = f"{a}-{v}.jar"
            target = libs / name
            if not target.exists():
                try:
                    data = _fetch(f"{_repo_path(g, a)}/{v}/{name}")
                except (urllib.error.URLError, OSError) as e:
                    print(f"  ! {g}:{a}:{v}: jar download failed ({e})", flush=True)
                    if depth == 0:
                        return 1
                    continue
                tmp = target.with_suffix(".part")
                tmp.write_bytes(data)
                tmp.replace(target)
                print(f"  + {name} ({len(data) // 1024} KB)", flush=True)
            else:
                print(f"  = {name} (already in libs)", flush=True)
            jars.append(name)
        if depth < 8:
            queue += [(dg, da, dv, depth + 1) for dg, da, dv in pom.dependencies() if dg and da]
    data = _load_manifest(folder)
    data["packages"][f"{group}:{artifact}"] = {"version": version, "jars": jars}
    _save_manifest(folder, data)
    print(f"Installed {group}:{artifact}:{version} into {LIBS}/ ({len(jars)} jar(s)).", flush=True)
    return 0


def maven_remove(folder: Path, spec: str) -> int:
    key = ":".join(spec.strip().split(":")[:2])
    data = _load_manifest(folder)
    pkg = data["packages"].pop(key, None)
    if pkg is None:
        print(f"Maven: {key} is not installed (see {MANIFEST})", file=sys.stderr)
        return 1
    still = {j for p in data["packages"].values() for j in p.get("jars", [])}
    for j in pkg.get("jars", []):
        if j not in still and (Path(folder) / LIBS / j).exists():
            (Path(folder) / LIBS / j).unlink()
            print(f"  - {j}")
    _save_manifest(folder, data)
    print(f"Removed {key}.")
    return 0


def maven_list(folder: Path) -> int:
    data = _load_manifest(folder)
    known = set()
    if not data["packages"]:
        print("No Maven packages installed.")
    for k, p in sorted(data["packages"].items()):
        print(f"{k} {p.get('version', '')}  ({', '.join(p.get('jars', []))})")
        known |= set(p.get("jars", []))
    extra = [j.name for j in sorted((Path(folder) / LIBS).glob("*.jar")) if j.name not in known]
    if extra:
        print("Other jars in libs/: " + ", ".join(extra))
    return 0


def maven_search(query: str) -> int:
    q = query.strip()
    if re.fullmatch(r"[\w.\-]+:[\w.\-]+", q):
        g, a = q.split(":")
        q = f'g:"{g}" AND a:"{a}"'
    data, error = None, None
    for _ in range(3):                      # search.maven.org is sometimes slow: retry
        try:
            data = json.loads(_fetch(SEARCH.format(q=urllib.parse.quote(q)), timeout=20))
            break
        except (urllib.error.URLError, OSError, ValueError) as e:
            error = e
    if data is None:
        print(f"Maven search failed: {error}. Browse https://central.sonatype.com/search?q="
              f"{urllib.parse.quote(query)}", file=sys.stderr)
        return 1
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        print("No packages found.")
    for d in docs:
        print(f"{d.get('id', '')} {d.get('latestVersion', d.get('v', ''))}")
    return 0


def cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, folder = argv[0], Path(os.path.abspath(argv[1]))
    if cmd == "build":
        return build(folder, sys.stderr if "--quiet" in argv else sys.stdout, force="--force" in argv)
    if cmd == "pkg" and len(argv) >= 3:
        action, arg = argv[2], (argv[3] if len(argv) > 3 else "")
        if action == "list":
            return maven_list(folder)
        if action == "search":
            return maven_search(arg)
        if action in ("add", "install"):
            return maven_add(folder, arg)
        if action in ("remove", "uninstall"):
            return maven_remove(folder, arg)
    if cmd == "init":
        (folder / LIBS).mkdir(parents=True, exist_ok=True)
        if not (folder / MANIFEST).exists():
            _save_manifest(folder, {"packages": {}})
        print(f"Created {folder / MANIFEST}")
        return 0
    print(f"unknown command: {' '.join(argv)}", file=sys.stderr)
    return 2


# ====================================================================== plugin
class JavaBridgePlugin(BridgeLanguagePlugin):
    id = "java-bridge"
    display_name = "Java (GUI Bridge, JDK)"
    code_ext = ".java"
    tool_names = ["javac"]
    install_hint = "Install a JDK 17+: winget install EclipseAdoptium.Temurin.17.JDK"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    keywords = JAVA_KEYWORDS
    builtins = list(RAD_HELPERS) + ["System", "String", "Math", "Integer", "Double", "Long", "Boolean",
                                    "List", "ArrayList", "Map", "HashMap", "Arrays", "Collections", "Object",
                                    "StringBuilder", "Exception", "RuntimeException", "Thread",
                                    "RadControl", "RadEvent", "Rad"]
    handler_regex = (r"^\s*(?:(?:public|private|protected|static|final|synchronized)\s+)+"
                     r"void\s+(\w+_\w+)\s*\(")
    package_manager = PackageManager(
        name="Maven Central (libs/)", tool=sys.executable,
        list_cmd=[sys.executable, str(RADJAVA), "pkg", ".", "list"],
        search_cmd=[sys.executable, str(RADJAVA), "pkg", ".", "search", "{query}"],
        install_cmd=[sys.executable, str(RADJAVA), "pkg", ".", "add", "{name}:{version}"],
        uninstall_cmd=[sys.executable, str(RADJAVA), "pkg", ".", "remove", "{name}"],
        init_cmd=[sys.executable, str(RADJAVA), "init", "."],
        manifest=MANIFEST,
        search_url="https://central.sonatype.com/search?q={query}")

    def tool(self) -> str:
        return _tool("javac")

    # ------------------------------------------------------------ code templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. A handler is a static method named <Control>_<Event>\n"
                f"// (optionally taking RadEvent e: e.x, e.y, e.button, e.keyCode, e.keyChar).\n"
                f"// Controls are fields of {n}Designer ({n}_designer.java):  lblOut.setText(\"Hi\");  "
                f"lstLog.addItem(\"x\");\n"
                f"// Helpers: msgbox(text), input(prompt), set/get/call(obj, ...), show(\"Form2\"), end(),\n"
                f"//          radcall(\"Module.function\", args...) - call a function of a project module.\n"
                f"public class {n} extends {n}Designer {{\n"
                f"    static void {n}_Load(RadEvent e) {{\n"
                f"        // runs when the form is shown\n"
                f"    }}\n"
                f"}}\n")

    def generate_designer(self, form: Form, user_code: str) -> str:
        n = form.name
        L = [f"// AUTO-GENERATED by RAD IDE from {n}.form - do not edit (changes will be lost).",
             "// The form is drawn by the IDE (GUI Bridge); these fields talk to its controls.",
             f"class {n}Designer extends Rad {{",
             f"    /** The form itself ({n}). */",
             f"    protected static final RadControl me = new RadControl(\"{n}\");"]
        for c in form.controls:
            if c.type == "MenuStrip" or not re.fullmatch(r"[A-Za-z_]\w*", c.name) or c.name in JAVA_KEYWORDS:
                continue
            L.append(f"    protected static final RadControl {c.name} = new RadControl(\"{n}.{c.name}\");"
                     f"  // {c.type}")
        L += ["}", ""]
        return "\n".join(L)

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, r"^\s*(?:(?:public|private|protected|static|final|synchronized)\s+)+"
                                     rf"void\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        idx = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip() == "}"), None)
        stub = [f"    static void {name}(RadEvent e) {{", "        ", "    }"]
        if idx is None:
            lines += ["", f"public class {form.name} extends {form.name}Designer {{"] + stub + ["}"]
            return "\n".join(lines) + "\n", len(lines) - 3
        if idx > 0 and not lines[idx - 1].rstrip().endswith("{") and lines[idx - 1].strip():
            stub.insert(0, "")
        lines[idx:idx] = stub
        return "\n".join(lines) + "\n", idx + len(stub) - 2

    def module_template(self, name: str) -> str:
        return (f"// Module {name}. Its public static methods can be used by every form ({name}.add(2, 3))\n"
                f"// and by other languages of the project through the RAD Hub:\n"
                f"//     radcall(\"{name}.add\", 2, 3)      (same syntax in Java, C#, Python, Ring, ...)\n"
                f"// Arguments and results are JSON values: numbers, strings, booleans, null, lists, maps.\n"
                f"// Libraries: Project > Packages (Maven Central) puts jars in libs/.\n"
                f"public class {name} {{\n"
                f"    public static double add(double a, double b) {{\n"
                f"        return a + b;\n"
                f"    }}\n"
                f"}}\n")

    # ------------------------------------------------------------ References (CONTRACTS 7.2)
    def exported_functions(self, path: Path, text: str) -> list:
        """Public static methods of the public class of the file (``public class MathLib`` in
        MathLib.java; ``main`` and X_Event handlers are skipped). Parameter/return types are kept."""
        return refs.java_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>.ref.java``: class ``<Lib>`` whose static methods forward to the RAD Hub, so the
        consumer writes ``MathLib.add(2, 3)`` (compiled with the project's other *.java files)."""
        return refs.java_proxy(lib, functions)

    def example_function(self, name: str) -> str:
        """One example public method (goes inside the library class, see library_template)."""
        return ("    /** Adds two numbers. */\n"
                "    public static double add(double a, double b) {\n"
                "        return a + b;\n"
                "    }\n")

    def library_template(self, name: str) -> str:
        cls = re.sub(r"\W", "_", name)
        return (f"// Class Library {name}. Its public static methods are the library's public functions:\n"
                f"// a project that references {name} (Add Reference) calls them as native code -\n"
                f"//     {name}.add(2, 3)   in Java, C#, Python, JavaScript ...   {name}_add(2, 3) in Ring\n"
                f"// Arguments and results are JSON values: numbers, strings, booleans, null, lists, maps.\n"
                f"public class {cls} {{\n"
                f"{self.example_function(name)}"
                f"\n"
                f"    /** Returns a greeting. */\n"
                f"    public static String greet(String name) {{\n"
                f"        return \"Hello, \" + name + \"!\";\n"
                f"    }}\n"
                f"}}\n")

    # ------------------------------------------------------------ build / run
    def prepare(self, folder: Path, project: Project) -> None:
        ensure_build_dir(folder)

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{sys.executable}" "{RADJAVA}" build "{Path(os.path.abspath(folder))}"'

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return java_command(folder)

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(os.path.abspath(folder))
        if build(folder, sys.stderr) != 0:
            msg = f"Java worker: compiling {folder.name} failed (see the build output)"
            return [sys.executable, "-c", f"import sys; sys.stderr.write({msg!r} + '\\n'); sys.exit(1)"]
        return java_command(folder, "--worker", Path(module_file).stem)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        names = names or {}
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(\w+)\.\w*$", before)
        if m:
            obj = m.group(1)
            if obj == "Rad":
                return [Completion(k, "function", d) for k, d in RAD_HELPERS.items()]
            if obj in names or obj == "me":
                return [Completion(k, "method", d) for k, d in CONTROL_MEMBERS.items()]
            if obj == "e":
                return [Completion(k, "property", d) for k, d in EVENT_MEMBERS.items()]
            if path:
                return [Completion(n, "function", d) for n, d in refs.proxy_members(Path(path).parent, obj, "java")]
            return []
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in RAD_HELPERS.items()]
        out += [Completion(b, "class") for b in self.builtins if b not in RAD_HELPERS]
        if path:
            out += [Completion(p.name[:-9], "module", "reference (Add Reference)")
                    for p in Path(path).parent.glob("*.ref.java")]
        out += [Completion(n, "control", t) for n, t in names.items()]
        seen = {c.name for c in out}
        for w in re.findall(r"[A-Za-z_]\w{2,}", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(?:(\w+)\.)?(\w+)\s*\([^()]*$", before)
        if not m:
            return ""
        obj, fn = m.group(1), m.group(2)
        if obj and (obj in (names or {}) or obj == "me"):
            return CONTROL_MEMBERS.get(fn, "")
        if obj and path:
            for n, d in refs.proxy_members(Path(path).parent, obj, "java"):
                if n == fn:
                    return d
        return RAD_HELPERS.get(fn, "")


PLUGIN = JavaBridgePlugin()
