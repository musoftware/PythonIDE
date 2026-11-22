"""Native build for Java projects: real Swing forms, a jlink-trimmed Java runtime and a jpackage launcher exe -
no Python, no GUI Bridge host, nothing to install on the user's PC.

The .form files become Swing code (RadForm_<Form>.initComponents, NetBeans-style); the project's classes compile
unchanged: the GUI Bridge client API (lblOut.setText("Hi"), msgbox, show("Form2"), radcall ...) is provided by
java/Rad.java on top of java/RadSwing.java (VB-style properties on the Swing components, Anchor/Dock layout,
handlers = static methods <Control>_<Event> found by reflection, like RadMain.java).

Packaging (smallest that reliably runs Swing on Windows):
  jdeps   -> the modules the program needs (java.base + java.desktop for a plain form program)
  jlink   -> a private runtime with only those modules (--strip-debug --compress --strip-native-commands,
             no headers/man pages; the .lib and UCRT forwarders Windows 10+ already has are removed)
  jpackage --type app-image -> <App>.exe launcher + app\\ + runtime\\ (official JDK tool; no WiX needed)
GraalVM native-image was evaluated (docs/NATIVE_BUILD.md): Swing on Windows needs the MSVC toolchain
(Visual Studio Build Tools, not open source) and reflection/JNI configuration; it is not used.

The JDK is the one the IDE uses for Java projects (java_bridge.jdk_bin(): JAVA_HOME / PATH / common folders),
then the IDE's private JDKs under %LOCALAPPDATA%\\RADIDE\\tools\\jdk*; it must have jlink + jpackage and be
able to link (jmods, or a JDK 24+ linkable run-time image).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from ...controls import CONTROL_TYPES, FORM_EVENTS
from ...layout import place_specs
from ...model import Form, Project
from . import NativeUnsupported
from ._forms import copy_data, dir_size, fresh_dir, lit, load_forms, num, problems, rgb, size_text

LANGS = ("java-bridge",)
NAME = "native Swing (jlink runtime + jpackage exe, no Python)"
HERE = Path(__file__).resolve().parent / "java"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TEST_HOOK_ENV = "RADIDE_NATIVE_TEST_HOOK"        # =1 at build time: test builds get RadTestHook (never releases)

VISUAL = {"Button", "Label", "TextBox", "CheckBox", "RadioButton", "ListBox", "ComboBox", "PictureBox", "ProgressBar",
          "NumericUpDown", "TrackBar", "Panel", "GroupBox", "TabControl", "DateTimePicker", "LinkLabel", "StatusBar"}
DIALOGS = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FolderBrowserDialog")
SUPPORTED = VISUAL | {"Timer", "MenuStrip"} | set(DIALOGS)
CLIENT_KEEP = ("RadControl.java", "RadEvent.java", "RadJson.java")     # bridge client files used unchanged
ALIGN = {"Left": "SwingConstants.LEFT", "Center": "SwingConstants.CENTER", "Right": "SwingConstants.RIGHT"}


# ====================================================================== JDK
class Jdk:
    def __init__(self, home: Path):
        self.home = home
        self.bin = home / "bin"
        self.version = 0
        rel = home / "release"
        if rel.is_file():
            m = re.search(r'JAVA_VERSION="(\d+)', rel.read_text(encoding="utf-8", errors="replace"))
            if m:
                self.version = int(m.group(1))

    def tool(self, name: str) -> str:
        p = self.bin / f"{name}.exe"
        return str(p) if p.is_file() else ""

    def can_link(self) -> bool:
        if not (self.tool("jlink") and self.tool("jpackage") and self.tool("javac") and self.tool("jdeps")):
            return False
        return (self.home / "jmods" / "java.base.jmod").is_file() or self.version >= 24

    def __repr__(self):
        return f"JDK {self.version} ({self.home})"


def jdks() -> list[Jdk]:
    homes: list[Path] = []
    try:
        from ...languages.java_bridge import _jdk_dirs, jdk_bin
        first = jdk_bin()
        if first:
            homes.append(Path(first).parent)
        homes += [Path(d).parent for d in _jdk_dirs()]
    except Exception:  # noqa: BLE001
        pass
    tools = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RADIDE" / "tools"
    for d in sorted(tools.glob("jdk*/*/bin/javac.exe"), reverse=True) + sorted(tools.glob("jdk*/bin/javac.exe"), reverse=True):
        homes.append(d.parent.parent)
    out, seen = [], set()
    for h in homes:
        k = str(h.resolve()).lower() if h.exists() else ""
        if k and k not in seen:
            seen.add(k)
            out.append(Jdk(h.resolve()))
    return out


def find_jdk() -> Jdk | None:
    """The IDE's Java JDK when it can jlink/jpackage, else the first one that can."""
    return next((j for j in jdks() if j.can_link()), None)


# ====================================================================== check
def check(folder, project: Project, cfg) -> list[str]:
    folder = Path(folder)
    out = problems(folder, project, "java-bridge", SUPPORTED, "Swing", (".java",))
    for n in project.forms:
        p = folder / f"{n}.java"
        if p.is_file() and re.search(r"\bRadJson\.parse\b.*RAD_HUB|System\.getenv\(\"RAD_HUB\"\)",
                                     p.read_text(encoding="utf-8", errors="replace")):
            out.append(f"{n}.java talks to the RAD Hub directly")
    if find_jdk() is None:
        out.append("no JDK with jlink + jpackage (JDK 17+ with jmods, or JDK 24+) was found")
    return out


# ====================================================================== Swing code
class _Gen:
    def __init__(self, form: Form, handlers: set[str]):
        self.form = form
        self.handlers = {h.lower() for h in handlers}
        self.places = place_specs(form)
        self.vars: dict[str, str] = {c.name: "c_" + re.sub(r"\W", "_", c.name) for c in form.controls}

    def used(self, owner: str, events) -> list[str]:
        return [e for e in events if f"{owner}_{e}".lower() in self.handlers]

    @staticmethod
    def color(v) -> str | None:
        c = rgb(v)
        return f"rgb({c[0]}, {c[1]}, {c[2]})" if c else None

    def control(self, c, parent_expr: str) -> list[str]:
        p, t, v = c.props, c.type, self.vars[c.name]
        text = str(p.get("Text", "") or "")
        outer = v
        L = [f"// {c.name} ({t})"]
        if t == "Button":
            L += [f"JButton {v} = new JButton({lit(text)});", f"{v}.setMargin(new Insets(1, 2, 1, 2));"]
            if str(p.get("TextAlign", "Center")) != "Center":
                L.append(f"{v}.setHorizontalAlignment({ALIGN.get(str(p.get('TextAlign')), 'SwingConstants.CENTER')});")
        elif t in ("Label", "LinkLabel", "StatusBar"):
            L += [f"JLabel {v} = new JLabel({lit(text)});",
                  f"{v}.setHorizontalAlignment({ALIGN.get(str(p.get('TextAlign', 'Left')), 'SwingConstants.LEFT')});"]
            if t == "StatusBar":
                L.append(f"{v}.setBorder(BorderFactory.createCompoundBorder(sunken(), BorderFactory.createEmptyBorder(0, 4, 0, 0)));")
            if t == "LinkLabel":
                col = self.color(p.get("LinkColor")) or "rgb(0, 102, 204)"
                L += [f"{v}.setForeground({col});", f"{v}.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));"]
        elif t == "TextBox":
            if p.get("Multiline"):
                L += [f"JTextArea {v} = new JTextArea({lit(text)});", f"{v}.setLineWrap(true);", f"{v}.setWrapStyleWord(true);"]
                outer = v + "_sp"
                L.append(f"JScrollPane {outer} = scroll({v});")
            elif str(p.get("PasswordChar") or ""):
                ch = str(p["PasswordChar"])[0]
                L += [f"JPasswordField {v} = new JPasswordField({lit(text)});",
                      f"{v}.setEchoChar({lit(ch)}.charAt(0));"]
            else:
                L.append(f"JTextField {v} = new JTextField({lit(text)});")
            if p.get("ReadOnly"):
                L.append(f"{v}.setEditable(false);")
        elif t in ("CheckBox", "RadioButton"):
            cls = "JCheckBox" if t == "CheckBox" else "JRadioButton"
            L.append(f"{cls} {v} = new {cls}({lit(text)}, {str(bool(p.get('Checked'))).lower()});")
            if t == "RadioButton":
                L.append(f"radioGroup({parent_expr}).add({v});")
        elif t == "ListBox":
            items = [s.strip() for s in str(p.get("Items") or "").split(";") if s.strip()]
            L.append(f"DefaultListModel<String> {v}_m = new DefaultListModel<>();")
            L += [f"{v}_m.addElement({lit(s)});" for s in items]
            L += [f"JList<String> {v} = new JList<>({v}_m);", f"{v}.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);"]
            outer = v + "_sp"
            L.append(f"JScrollPane {outer} = scroll({v});")
        elif t == "ComboBox":
            items = [s.strip() for s in str(p.get("Items") or "").split(";") if s.strip()]
            L.append(f"JComboBox<String> {v} = new JComboBox<>(new String[] {{ {', '.join(lit(s) for s in items)} }});")
            if str(p.get("DropDownStyle")) in ("DropDown", "Simple"):
                L.append(f"{v}.setEditable(true);")
                if text and text != c.name:
                    L.append(f"{v}.getEditor().setItem({lit(text)});")
            L.append(f"{v}.setSelectedIndex(-1);")
        elif t == "PictureBox":
            L += [f"JLabel {v} = new JLabel();", f"{v}.setHorizontalAlignment(SwingConstants.CENTER);"]
            if p.get("Image"):
                L.append(f"{v}.setIcon(image({lit(p['Image'])}));")
        elif t in ("ProgressBar", "NumericUpDown", "TrackBar"):
            lo, hi = num(p.get("Minimum")), max(num(p.get("Minimum")), num(p.get("Maximum"), 100))
            val = min(hi, max(lo, num(p.get("Value"))))
            if t == "ProgressBar":
                L += [f"JProgressBar {v} = new JProgressBar({lo}, {hi});", f"{v}.setValue({val});"]
            elif t == "NumericUpDown":
                L.append(f"JSpinner {v} = new JSpinner(new SpinnerNumberModel({val}, {lo}, {hi}, 1));")
            else:
                L.append(f"JSlider {v} = new JSlider({lo}, {hi}, {val});")
        elif t in ("Panel", "GroupBox"):
            L.append(f"JPanel {v} = new JPanel(new RadSwing.RadLayout());")
            if t == "GroupBox":
                L.append(f"{v}.setBorder(BorderFactory.createTitledBorder({lit(text)}));")
        elif t == "TabControl":
            pages = [s.strip() for s in str(p.get("TabPages") or "").split(";") if s.strip()] or ["TabPage1"]
            L.append(f"JTabbedPane {v} = new JTabbedPane();")
            for i, title in enumerate(pages):
                L += [f"JPanel {v}_page{i} = new JPanel(new RadSwing.RadLayout());", f"{v}.addTab({lit(title)}, {v}_page{i});"]
            sel = num(p.get("SelectedIndex"))
            if 0 < sel < len(pages):
                L.append(f"{v}.setSelectedIndex({sel});")
        elif t == "DateTimePicker":
            fmt = {"Long": "dd MMMM yyyy", "Time": "HH:mm:ss"}.get(str(p.get("Format")), "yyyy-MM-dd")
            L += [f"JSpinner {v} = new JSpinner(new SpinnerDateModel());",
                  f"{v}.setEditor(new JSpinner.DateEditor({v}, {lit(fmt)}));"]
            if str(p.get("Value") or "").strip():
                L.append(f"try {{ {v}.setValue(new java.text.SimpleDateFormat(\"yyyy-MM-dd\").parse({lit(str(p['Value'])[:10])})); }} "
                         f"catch (Exception ignored) {{ }}")
        # common properties
        font = (str(p.get("FontName") or "Segoe UI"), float(p.get("FontSize") or 9), bool(p.get("FontBold")),
                bool(p.get("FontItalic")))
        L.append(f"{v}.setFont(font({lit(font[0])}, {font[1]:g}f, {str(font[2]).lower()}, {str(font[3]).lower()}));")
        if t == "LinkLabel":
            L.append(f"{v}.setFont(underline({v}.getFont()));")
        bg = self.color(p.get("BackColor"))
        if bg:
            L += [f"{v}.setBackground({bg});", f"{v}.setOpaque(true);"]
        fg = self.color(p.get("ForeColor"))
        if fg and t != "LinkLabel":
            L.append(f"{v}.setForeground({fg});")
        if p.get("Enabled") is False:
            L.append(f"{v}.setEnabled(false);")
            if outer != v:
                L.append(f"{outer}.setEnabled(false);")
        if p.get("ToolTip"):
            L.append(f"{v}.setToolTipText({lit(p['ToolTip'])});")
        L.append(f"reg({lit(c.name)}, {lit(t)}, {v}, {outer});")
        pl = self.places.get(c.name)
        if pl is not None:
            nums = ", ".join(f"{x:g}" for x in (pl.x, pl.y, pl.w, pl.h, pl.rx, pl.ry, pl.rw, pl.rh))
        else:
            nums = f"{num(p.get('Left'))}, {num(p.get('Top'))}, {num(p.get('Width'))}, {num(p.get('Height'))}, 0, 0, 0, 0"
        self._place.append((c, f"place({outer}, {parent_expr}, {nums});"))
        if p.get("Visible") is False:
            self._hidden.append(f"hidden({lit(c.name)});")
        used = self.used(c.name, CONTROL_TYPES[t].all_events())
        if used:
            self._wire.append(f"wire({v}, {lit(c.name)}, {', '.join(lit(e) for e in used)});")
        return L

    def menu(self, menu) -> list[str]:
        L = ["JMenuBar menuBar = new JMenuBar();"]
        counter = [0]

        def build(items, parent: str, top: bool):
            for it in items or []:
                if it.get("Text") == "-":
                    if not top:
                        L.append(f"{parent}.addSeparator();")
                    continue
                counter[0] += 1
                var = f"mi{counter[0]}"
                if it.get("Items"):
                    L.append(f"JMenu {var} = new JMenu({lit(it.get('Text', ''))});")
                    build(it["Items"], var, False)
                else:
                    L.append(f"JMenuItem {var} = new JMenuItem({lit(it.get('Text', ''))});")
                    if it.get("Name"):
                        self._wire.append(f"wire(items.get({lit(it['Name'])}).comp, {lit(it['Name'])}, \"Click\");")
                if it.get("Name"):
                    L.append(f"reg({lit(it['Name'])}, \"MenuItem\", {var}, null);")
                L.append(f"{parent}.add({var});")
        build(menu.props.get("Items"), "menuBar", True)
        L.append("setJMenuBar(menuBar);")
        return L

    def code(self) -> str:
        form, fp = self.form, self.form.props
        n = form.name
        cls = "RadForm_" + re.sub(r"\W", "_", n)
        W, H = num(fp.get("Width"), 400), num(fp.get("Height"), 300)
        self._place, self._wire, self._hidden = [], [], []
        body = [f"setTitle({lit(fp.get('Text', n))});"]
        col = self.color(fp.get("BackColor"))
        if col:
            body.append(f"client.setBackground({col});")
        menu = form.menu()
        if menu is not None and menu.props.get("Items"):
            body += self.menu(menu)
        pages: dict[str, int] = {}
        for c in form.ordered():
            if c.parent and form.find(c.parent) is not None and form.find(c.parent).type == "TabControl":
                idx = num(c.props.get("TabPage"))
                pcount = len([s for s in str(form.find(c.parent).props.get("TabPages") or "").split(";") if s.strip()]) or 1
                parent_expr = f"{self.vars[c.parent]}_page{idx if 0 <= idx < pcount else 0}"
            elif c.parent:
                parent_expr = self.vars[c.parent]
            else:
                parent_expr = "client"
            body += self.control(c, parent_expr)
            pages[c.name] = 0
        # Swing: the first added component is the front-most; the model lists the back-most first
        by_parent: dict[str, list] = {}
        for c, line in self._place:
            by_parent.setdefault(c.parent, []).append(line)
        for lines in by_parent.values():
            body += list(reversed(lines))
        for c in form.nonvisual():
            v = self.vars[c.name]
            if c.type == "Timer":
                iv = max(1, num(c.props.get("Interval"), 100))
                body += [f"javax.swing.Timer {v} = new javax.swing.Timer({iv}, null);", f"{v}.setInitialDelay({iv});",
                         f"reg({lit(c.name)}, \"Timer\", {v}, null);"]
                if f"{c.name}_tick".lower() in self.handlers:
                    self._wire.append(f"wire({v}, {lit(c.name)}, \"Tick\");")
                if c.props.get("Enabled"):
                    self._hidden.append(f"{v}.start();")
            elif c.type in DIALOGS:
                args = [lit(c.name), lit(c.type)]
                for k in ("Title", "Filter", "FileName", "InitialDirectory", "Color", "SelectedPath"):
                    if c.props.get(k) not in (None, ""):
                        args += [lit(k), lit(c.props[k])]
                body.append(f"dialog({', '.join(args)});")
        fe = [e for e in FORM_EVENTS if f"{n}_{e}".lower() in self.handlers and e not in ("Load", "FormClosing", "FormClosed")]
        mouse = [e for e in fe if e in ("Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseWheel",
                                        "KeyDown", "KeyUp", "KeyPress")]
        other = [e for e in fe if e not in mouse]
        if mouse:
            body += ["client.setFocusable(true);", f"wire(client, {lit(n)}, {', '.join(lit(e) for e in mouse)});"]
        if other:
            body.append(f"wire(this, {lit(n)}, {', '.join(lit(e) for e in other)});")
        body += self._wire + self._hidden
        body.append(f"setClientSize({W}, {H});")
        if fp.get("FormBorderStyle") == "FixedSingle":
            body.append("setResizable(false);")
        if fp.get("TopMost"):
            body.append("setAlwaysOnTop(true);")
        if fp.get("StartPosition", "CenterScreen") == "CenterScreen":
            body.append("setLocationRelativeTo(null);")
        else:
            body.append("setLocationByPlatform(true);")
        if fp.get("WindowState") == "Maximized":
            body.append("setExtendedState(MAXIMIZED_BOTH);")
        icon = str(fp.get("Icon") or "")
        if icon:
            body.append(f"{{ ImageIcon ic = image({lit(icon)}); if (ic != null && ic.getIconWidth() > 0) setIconImage(ic.getImage()); }}")
        L = [f"/** Form {n} (generated from {n}.form by RAD IDE - do not edit). */",
             f"final class {cls} extends RadSwing.FormBase {{",
             f"    {cls}() {{", f"        super({lit(n)});", "        initComponents();", "    }", "",
             "    private void initComponents() {"]
        L += [f"        {b}" for b in body]
        L += ["    }", "}", ""]
        return "\n".join(L)


def forms_code(forms: list[Form], handlers: set[str]) -> str:
    out = ["// AUTO-GENERATED by RAD IDE (native Swing build) from the project's .form files.",
           "import java.awt.*;", "import javax.swing.*;", ""]
    for f in forms:
        out.append(_Gen(f, handlers).code())
    return "\n".join(out)


def main_java(project: Project, cfg, forms: list[Form], classes: list[str], hook: bool) -> str:
    startup = project.startup or forms[0].name
    L = ["// AUTO-GENERATED by RAD IDE (native Swing build): the program's entry point.",
         "public final class RadMainNative {", "    public static void main(String[] args) {",
         f"        RadSwing.init({lit(cfg.app_name or project.name)}{''.join(', ' + lit(c) for c in classes)});"]
    for f in forms:
        L.append(f"        RadSwing.register({lit(f.name)}, RadForm_{re.sub(chr(92) + 'W', '_', f.name)}::new);")
    if hook:
        L.append("        RadTestHook.start();")
    L += [f"        RadSwing.run({lit(startup)});", "    }", "}", ""]
    return "\n".join(L)


# ====================================================================== build
def _run(cmd, cwd: Path, log) -> tuple[int, str]:
    log("> " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd[:2]) + (" ..." if len(cmd) > 2 else ""))
    try:
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, creationflags=NO_WINDOW, timeout=900,
                           env=dict(os.environ, JAVA_TOOL_OPTIONS="-Duser.language=en"))
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)
    text = (r.stdout + r.stderr).decode("utf-8", "replace").replace("\r\n", "\n")
    text = "\n".join(l for l in text.splitlines() if not l.startswith("Picked up JAVA_TOOL_OPTIONS"))
    return r.returncode, text


def _version(cfg) -> str:
    nums = [int(n) for n in re.findall(r"\d+", cfg.version or "")[:3]] or [1]
    nums = (nums + [0, 0])[:3]
    if nums[0] < 1:
        nums[0] = 1
    return ".".join(str(n) for n in nums)


def build(folder, project: Project, cfg, work, log):
    from ..build import BuildResult, make_icon
    folder, work = Path(folder).resolve(), Path(work)
    reasons = check(folder, project, cfg)
    if reasons:
        raise NativeUnsupported(reasons)
    jdk = find_jdk()
    log(f"Java: {jdk}")
    from ...languages import get_plugin
    from ...languages.java_bridge import CLIENT_DIR, class_names
    plugin = get_plugin("java-bridge")
    forms = load_forms(folder, project, "java-bridge")
    handlers = set(plugin.handlers_in_project(folder, project))
    hook = os.environ.get(TEST_HOOK_ENV) == "1"
    root = fresh_dir(work / "native-java")
    src, classes = fresh_dir(root / "src"), fresh_dir(root / "classes")
    for p in sorted(folder.glob("*.java")):
        if not p.stem.endswith("_designer"):
            shutil.copy2(p, src / p.name)
    for f in forms:
        code = (folder / f"{f.name}.java").read_text(encoding="utf-8", errors="replace") if (folder / f"{f.name}.java").is_file() else ""
        (src / f"{f.name}_designer.java").write_text(plugin.generate_designer(f, code), encoding="utf-8")
    for name in CLIENT_KEEP:
        shutil.copy2(CLIENT_DIR / name, src / name)
    for name in ("Rad.java", "RadSwing.java") + (("RadTestHook.java",) if hook else ()):
        shutil.copy2(HERE / name, src / name)
    (src / "RadForms_g.java").write_text(forms_code(forms, handlers), encoding="utf-8")
    (src / "RadMainNative.java").write_text(main_java(project, cfg, forms, class_names(folder), hook), encoding="utf-8")
    libs = sorted((folder / "libs").glob("*.jar"))
    cp = os.pathsep.join(str(j) for j in libs)
    argfile = root / "sources.txt"
    argfile.write_text("\n".join(f'"{p.as_posix()}"' for p in sorted(src.glob("*.java"))), encoding="utf-8")
    cmd = [jdk.tool("javac"), "-encoding", "UTF-8", "-nowarn", "-g:none", "--release", str(jdk.version), "-d", str(classes)]
    if cp:
        cmd += ["-cp", cp]
    code, text = _run(cmd + [f"@{argfile}"], root, log)
    if code != 0:
        errs = [l.replace(str(src) + os.sep, "") for l in text.splitlines() if ": error:" in l][:10]
        raise NativeUnsupported(["javac: " + " | ".join(errs or text.strip().splitlines()[-5:])])
    inp = fresh_dir(root / "input")
    manifest = root / "MANIFEST.MF"
    manifest.write_text("Main-Class: RadMainNative\n" + (f"Class-Path: {' '.join('libs/' + j.name for j in libs)}\n" if libs else ""),
                        encoding="utf-8")
    code, text = _run([jdk.tool("jar"), "--create", "--file", str(inp / "app.jar"), "--manifest", str(manifest), "-C",
                       str(classes), "."], root, log)
    if code != 0:
        raise NativeUnsupported(["jar: " + text.strip()[-400:]])
    if libs:
        (inp / "libs").mkdir()
        for j in libs:
            shutil.copy2(j, inp / "libs" / j.name)
    # modules the program needs
    dcmd = [jdk.tool("jdeps"), "--ignore-missing-deps", "--print-module-deps", "--multi-release", str(jdk.version)]
    if cp:
        dcmd += ["--class-path", cp]
    code, text = _run(dcmd + [str(inp / "app.jar")], root, log)
    mods = text.strip().splitlines()[-1].strip() if code == 0 and text.strip() else "java.base,java.desktop"
    if not re.fullmatch(r"[\w.,]+", mods):
        mods = "java.base,java.desktop"
    if "java.desktop" not in mods.split(","):
        mods += ",java.desktop"
    log(f"Modules: {mods}")
    rt = root / "runtime"
    shutil.rmtree(rt, ignore_errors=True)
    code, text = _run([jdk.tool("jlink"), "--add-modules", mods, "--strip-debug", "--no-header-files", "--no-man-pages",
                       "--compress=" + ("zip-9" if jdk.version >= 21 else "2"), "--strip-native-commands",
                       "--output", str(rt)], root, log)
    if code != 0:
        raise NativeUnsupported(["jlink: " + text.strip()[-500:]])
    for f in list((rt / "lib").glob("*.lib")) + list((rt / "bin").glob("api-ms-win-*.dll")) + [rt / "bin" / "ucrtbase.dll"]:
        f.unlink(missing_ok=True)       # linker libs; the UCRT is part of Windows 10/11
    gen = fresh_dir(root / "gen")
    icon = make_icon(folder, cfg, gen, log)
    exe_base = cfg.exe_base()
    out = fresh_dir(root / "image")
    jp = [jdk.tool("jpackage"), "--type", "app-image", "--name", exe_base, "--input", str(inp), "--main-jar", "app.jar",
          "--main-class", "RadMainNative", "--runtime-image", str(rt), "--dest", str(out), "--app-version", _version(cfg),
          "--description", cfg.app_name or project.name, "--java-options", "-XX:+UseSerialGC",
          "--java-options", "-XX:TieredStopAtLevel=1", "--java-options", "-Dfile.encoding=UTF-8"]
    if cfg.publisher:
        jp += ["--vendor", cfg.publisher]
    if icon is not None:
        jp += ["--icon", str(icon)]
    if hook:
        jp.append("--win-console")
    code, text = _run(jp, root, log)
    image = out / exe_base
    if code != 0 or not (image / f"{exe_base}.exe").is_file():
        raise NativeUnsupported(["jpackage: " + text.strip()[-500:]])
    dist = work / "dist" / exe_base
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(image, dist)
    data = copy_data(folder, dist, (".java", ".class", ".jar"), out_dir=work.parent)
    if data:
        log("Data files: " + ", ".join(data))
    exe = dist / f"{exe_base}.exe"
    log(f"Native exe: {exe} (launcher {size_text(exe.stat().st_size)}, program folder {size_text(dir_size(dist))} "
        f"with its own Java runtime, no Python)")
    notes = ["Java program with its own trimmed Java runtime (jlink): nothing to install on the user's PC."]
    return BuildResult(dist, exe.name, "native-jlink", notes, python_based=False)


__all__ = ["LANGS", "NAME", "build", "check", "find_jdk", "forms_code", "jdks"]
