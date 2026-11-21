"""The Project Properties document of Visual Studio 2022 for SDK-style and legacy .NET projects:
a tab with a search box and a left navigation (Application, Global Usings, Build, Package, Code
Analysis, Debug, Resources, Settings, Signing, User Secrets). Like VS 2022, every change is written
to the project file at once (format preserving, radide/dotnet/sln/msprops.py); configuration
dependent settings follow the Configuration / Platform selectors at the top ("All configurations"
writes the unconditional property).

``LaunchProfilesDialog`` is the Debug > General > "Open debug launch profiles UI" window
(launchSettings.json: Project / Executable profiles, arguments, environment, working directory,
launch browser, app URL).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QMenu,
                             QPlainTextEdit, QPushButton, QScrollArea, QTableWidget,
                             QTableWidgetItem, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import launch, msprops, ops, secrets, signing

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
ALL = "All configurations"


@dataclass
class Spec:
    page: str                 # "Build/General"
    label: str
    name: str                 # MSBuild property ("" = custom row)
    kind: str = "text"        # text | combo | ecombo | bool | multi | file | button
    options: list = field(default_factory=list)       # combo: [(shown, value)]
    per_config: bool = False
    desc: str = ""
    true_value: str = "true"
    false_value: str = "false"
    default: str = ""
    sdk_only: bool = False


OUTPUT_TYPES = [("Console Application", "Exe"), ("Windows Application", "WinExe"), ("Class Library", "Library")]
FRAMEWORKS = ["net9.0", "net8.0", "net9.0-windows", "net8.0-windows", "netstandard2.0", "netstandard2.1", "net48",
              "net472", "net462"]
NULLABLE = [("Disable", "disable"), ("Enable", "enable"), ("Warnings", "warnings"), ("Annotations", "annotations")]
PLATFORM_TARGET = [("Any CPU", "AnyCPU"), ("x86", "x86"), ("x64", "x64"), ("ARM32", "ARM"), ("ARM64", "ARM64")]
DEBUG_TYPES = [("Portable", "portable"), ("Embedded", "embedded"), ("Full", "full"), ("Pdb-only", "pdbonly"),
               ("None", "none")]
ANALYSIS_LEVELS = [("Latest", "latest"), ("Latest recommended", "latest-recommended"), ("Latest all", "latest-all"),
                   ("Latest minimum", "latest-minimum"), ("Preview", "preview"), ("9.0", "9.0"), ("8.0", "8.0"),
                   ("7.0", "7.0"), ("6.0", "6.0"), ("5.0", "5.0")]

SPECS = [
    # Application
    Spec("Application/General", "Output type", "OutputType", "combo", OUTPUT_TYPES,
         desc="Specifies the type of application to build."),
    Spec("Application/General", "Target framework", "TargetFramework", "ecombo", [(f, f) for f in FRAMEWORKS],
         desc="Specifies the version of .NET that the application targets.", sdk_only=True),
    Spec("Application/General", "Target multiple frameworks", "TargetFrameworks", "text",
         desc="Semicolon separated list of frameworks (net8.0;net48). Replaces 'Target framework' "
              "when set (multi-targeting).", sdk_only=True),
    Spec("Application/General", "Target framework version", "TargetFrameworkVersion", "ecombo",
         [(v, v) for v in ("v4.8.1", "v4.8", "v4.7.2", "v4.7.1", "v4.6.2", "v4.5.2", "v4.0", "v3.5")],
         desc=".NET Framework version of this (non-SDK) project."),
    Spec("Application/General", "Startup object", "StartupObject", "ecombo",
         desc="Defines the entry point to be called when the application loads."),
    Spec("Application/General", "Assembly name", "AssemblyName", desc="The name of the output file."),
    Spec("Application/General", "Default namespace", "RootNamespace",
         desc="The root namespace of new files added to the project."),
    Spec("Application/Win32 resources", "Icon", "ApplicationIcon", "file",
         desc="Sets the .ico file to use as your application icon."),
    Spec("Application/Win32 resources", "Manifest", "ApplicationManifest", "file",
         desc="A manifest determines specific settings for an application (app.manifest)."),
    # Global usings
    Spec("Global Usings/General", "Implicit global usings", "ImplicitUsings", "bool", true_value="enable",
         false_value="disable", desc="Enable a set of global usings based on the project type.", sdk_only=True),
    Spec("Global Usings/General", "Manage implicit global usings", "", "usings",
         desc="Add or remove <Using> items (global using directives for every file)."),
    # Build
    Spec("Build/General", "Conditional compilation symbols", "DefineConstants", per_config=True,
         desc="Specifies symbols on which to perform conditional compilation (DEBUG;TRACE)."),
    Spec("Build/General", "Platform target", "PlatformTarget", "combo", PLATFORM_TARGET, per_config=True,
         desc="Specifies the processor to be targeted by the output file."),
    Spec("Build/General", "Nullable", "Nullable", "combo", NULLABLE,
         desc="Specifies the project-wide C# nullable context."),
    Spec("Build/General", "Unsafe code", "AllowUnsafeBlocks", "bool",
         desc="Allow code that uses the 'unsafe' keyword to compile."),
    Spec("Build/General", "Optimize code", "Optimize", "bool", per_config=True,
         desc="Enable compiler optimizations for smaller, faster, and more efficient output."),
    Spec("Build/General", "Debug symbols", "DebugType", "combo", DEBUG_TYPES, per_config=True,
         desc="Specifies the kind of debug symbols produced during build."),
    Spec("Build/Errors and warnings", "Warning level", "WarningLevel", "ecombo",
         [(v, v) for v in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9999")], per_config=True,
         desc="Specifies the level to display for compiler warnings."),
    Spec("Build/Errors and warnings", "Treat warnings as errors", "TreatWarningsAsErrors", "bool", per_config=True,
         desc="Instruct the compiler to treat warnings as errors."),
    Spec("Build/Errors and warnings", "Treat specific warnings as errors", "WarningsAsErrors", per_config=True,
         desc="Semicolon separated warning ids (CS0168;CS0219)."),
    Spec("Build/Errors and warnings", "Suppress specific warnings", "NoWarn", per_config=True,
         desc="Blocks the compiler from generating the specified warnings (1701;1702)."),
    Spec("Build/Output", "Base output path", "BaseOutputPath", "text",
         desc="Specifies the base location for the project's output during build (bin\\).", sdk_only=True),
    Spec("Build/Output", "Output path", "OutputPath", "text", per_config=True,
         desc="Location of the build output for this configuration."),
    Spec("Build/Output", "Documentation file", "GenerateDocumentationFile", "bool",
         desc="Generate a file containing API documentation."),
    Spec("Build/Events", "Pre-build event", "", "prebuild",
         desc="Commands to run before the build starts (Exec of a PreBuild target)."),
    Spec("Build/Events", "Post-build event", "", "postbuild",
         desc="Commands to run after the build completes (Exec of a PostBuild target)."),
    Spec("Build/Advanced", "Language version", "LangVersion", "ecombo",
         [(v, v) for v in ("default", "latest", "latestMajor", "preview", "13.0", "12.0", "11.0", "10.0", "9.0",
                           "8.0", "7.3")], desc="The version of the language available to the code."),
    Spec("Build/Advanced", "Check for arithmetic overflow", "CheckForOverflowUnderflow", "bool", per_config=True,
         desc="Throw exceptions when integer arithmetic produces out of range values."),
    Spec("Build/Advanced", "Deterministic", "Deterministic", "bool", default="true",
         desc="Produce identical compilation output for identical inputs."),
    # Package
    Spec("Package/General", "Generate NuGet package on build", "GeneratePackageOnBuild", "bool",
         desc="Produce a package file during build operations."),
    Spec("Package/General", "Package ID", "PackageId", desc="The case-insensitive package identifier."),
    Spec("Package/General", "Title", "Title", desc="A human-friendly title of the package."),
    Spec("Package/General", "Package Version", "Version", desc="The version of the package (1.0.0)."),
    Spec("Package/General", "Authors", "Authors", desc="A comma-separated list of packages authors."),
    Spec("Package/General", "Company", "Company"),
    Spec("Package/General", "Product", "Product"),
    Spec("Package/General", "Description", "Description", "multi"),
    Spec("Package/General", "Copyright", "Copyright"),
    Spec("Package/General", "Project URL", "PackageProjectUrl"),
    Spec("Package/General", "Icon", "PackageIcon", desc="The icon image for the package (packed file path)."),
    Spec("Package/General", "README", "PackageReadmeFile"),
    Spec("Package/General", "Repository URL", "RepositoryUrl"),
    Spec("Package/General", "Repository type", "RepositoryType"),
    Spec("Package/General", "Tags", "PackageTags", desc="A semicolon-delimited list of tags."),
    Spec("Package/General", "Release notes", "PackageReleaseNotes", "multi"),
    Spec("Package/General", "Assembly version", "AssemblyVersion"),
    Spec("Package/General", "File version", "FileVersion"),
    Spec("Package/General", "Assembly neutral language", "NeutralLanguage"),
    Spec("Package/License", "License expression", "PackageLicenseExpression", desc="SPDX expression (MIT)."),
    Spec("Package/License", "License file", "PackageLicenseFile"),
    Spec("Package/License", "Require license acceptance", "PackageRequireLicenseAcceptance", "bool"),
    Spec("Package/Symbols", "Produce a symbol package", "IncludeSymbols", "bool"),
    Spec("Package/Symbols", "Symbol package format", "SymbolPackageFormat", "combo",
         [("snupkg", "snupkg"), ("symbols.nupkg", "symbols.nupkg")]),
    # Code analysis
    Spec("Code Analysis/All analyzers", "Run on build", "RunAnalyzersDuringBuild", "bool", default="true",
         desc="Run analyzers during build."),
    Spec("Code Analysis/All analyzers", "Run on live analysis", "RunAnalyzersDuringLiveAnalysis", "bool",
         default="true"),
    Spec("Code Analysis/.NET analyzers", "Enforce code style on build", "EnforceCodeStyleInBuild", "bool",
         desc="Produce diagnostics about code style on build."),
    Spec("Code Analysis/.NET analyzers", "Enable .NET analyzers", "EnableNETAnalyzers", "bool", default="true"),
    Spec("Code Analysis/.NET analyzers", "Analysis level", "AnalysisLevel", "combo", ANALYSIS_LEVELS),
    # Debug, resources, settings
    Spec("Debug/General", "Open debug launch profiles UI", "", "launch",
         desc="Launch profiles (launchSettings.json): command line arguments, environment variables, "
              "working directory, launch browser."),
    Spec("Resources/General", "Assembly resources", "", "resources",
         desc="Properties\\Resources.resx: strings, images, icons and files compiled into the assembly."),
    Spec("Settings/General", "Application settings", "", "settings",
         desc="Properties\\Settings.settings: user- and application-scoped settings."),
    # Signing
    Spec("Signing/General", "Sign the assembly", "SignAssembly", "bool",
         desc="Sign the output assembly to give it a strong name."),
    Spec("Signing/General", "Strong name key file", "AssemblyOriginatorKeyFile", "snk",
         desc="Choose or create a strong name key file (.snk)."),
    Spec("Signing/General", "Delay sign only", "DelaySign", "bool",
         desc="The project will not run or be debuggable when delay-signed."),
    Spec("User Secrets/General", "Manage User Secrets", "", "secrets",
         desc="secrets.json under %APPDATA%\\Microsoft\\UserSecrets\\<UserSecretsId> - kept out of the source tree."),
]


class ProjectPropertiesDocument(QWidget):
    """The <Project> Properties tab."""

    def __init__(self, win, project):
        super().__init__()
        self.win, self.project, self.ms = win, project, project.ms
        self.setObjectName("ProjectPropertiesDocument")
        self.rows: list[tuple[Spec, QWidget, object]] = []
        self.editors: dict[str, object] = {}
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search properties (Ctrl+E)")
        self.search.setClearButtonEnabled(True)
        top.addWidget(self.search, 1)
        top.addWidget(QLabel("Configuration:"))
        self.cfg = QComboBox()
        self.cfg.addItems([ALL] + self.ms.configuration_names())
        top.addWidget(self.cfg)
        top.addWidget(QLabel("Platform:"))
        self.plat = QComboBox()
        self.plat.addItems(self.ms.platform_names())
        top.addWidget(self.plat)
        lay.addLayout(top)
        body = QHBoxLayout()
        lay.addLayout(body, 1)
        self.nav = QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setMaximumWidth(220)
        body.addWidget(self.nav)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.form = QVBoxLayout(self.content)
        self.scroll.setWidget(self.content)
        body.addWidget(self.scroll, 1)
        self.headers: dict[str, QLabel] = {}
        self._build()
        self.search.textChanged.connect(self._filter)
        self.nav.currentItemChanged.connect(self._nav)
        self.cfg.currentIndexChanged.connect(lambda _i: self.reload_values())
        self.plat.currentIndexChanged.connect(lambda _i: self.reload_values())

    # ------------------------------------------------------------------ build
    def _applies(self, s: Spec) -> bool:
        if s.sdk_only and not self.ms.is_sdk:
            return False
        if s.name == "TargetFrameworkVersion" and self.ms.is_sdk:
            return False
        if s.page.startswith("Package/") and not self.ms.is_sdk:
            return False
        return True

    def _build(self):
        pages: dict[str, QTreeWidgetItem] = {}
        bold = QFont()
        bold.setBold(True)
        for s in SPECS:
            if not self._applies(s):
                continue
            top_name, _, sub = s.page.partition("/")
            if top_name not in pages:
                pages[top_name] = QTreeWidgetItem(self.nav, [top_name])
                pages[top_name].setData(0, ROLE, s.page)
            if s.page not in self.headers:
                child = QTreeWidgetItem(pages[top_name], [sub])
                child.setData(0, ROLE, s.page)
                h = QLabel(s.page.replace("/", " > "))
                f = QFont()
                f.setBold(True)
                f.setPointSize(f.pointSize() + 2)
                h.setFont(f)
                self.form.addWidget(h)
                self.headers[s.page] = h
            row = QFrame()
            rl = QVBoxLayout(row)
            rl.setContentsMargins(4, 6, 4, 6)
            lbl = QLabel(s.label)
            lbl.setFont(bold)
            rl.addWidget(lbl)
            if s.desc:
                d = QLabel(s.desc)
                d.setWordWrap(True)
                d.setStyleSheet("color: gray;")
                rl.addWidget(d)
            ed = self._editor(s, rl)
            note = QLabel("")
            note.setStyleSheet("color: #8a6d00;")
            note.hide()
            rl.addWidget(note)
            row.note = note
            self.form.addWidget(row)
            self.rows.append((s, row, ed))
            if s.name:
                self.editors[s.name] = ed
        self.form.addStretch(1)
        self.nav.expandAll()
        self.reload_values()

    def _editor(self, s: Spec, rl):
        k = s.kind
        if k in ("combo", "ecombo"):
            w = QComboBox()
            w.setEditable(k == "ecombo")
            w.addItem("", "")
            for shown, val in s.options:
                w.addItem(shown, val)
            if s.name == "StartupObject":
                w.addItems(self._main_classes())
            w.setMaximumWidth(420)
            if k == "ecombo":
                w.lineEdit().editingFinished.connect(lambda s=s, w=w: self._write(s, w.currentText().strip()))
            w.activated.connect(lambda _i, s=s, w=w: self._write(s, self._combo_value(w)))
            rl.addWidget(w)
            return w
        if k == "bool":
            w = QCheckBox("")
            w.toggled.connect(lambda on, s=s: self._write(s, s.true_value if on else
                                                         ("" if s.default in ("", s.false_value) else s.false_value)))
            rl.addWidget(w)
            return w
        if k == "multi":
            w = QPlainTextEdit()
            w.setMaximumHeight(80)
            w.focusOutEvent = lambda ev, s=s, w=w: (self._write(s, w.toPlainText().strip()),
                                                    QPlainTextEdit.focusOutEvent(w, ev))
            rl.addWidget(w)
            return w
        if k in ("prebuild", "postbuild"):
            w = QPlainTextEdit()
            w.setMaximumHeight(90)
            which = "pre" if k == "prebuild" else "post"
            w.focusOutEvent = lambda ev, which=which, w=w: (self.set_build_event(which, w.toPlainText()),
                                                            QPlainTextEdit.focusOutEvent(w, ev))
            rl.addWidget(w)
            self.editors[k] = w
            return w
        if k in ("file", "snk"):
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            e = QLineEdit()
            e.editingFinished.connect(lambda s=s, e=e: self._write(s, e.text().strip()))
            b = QPushButton("Browse...")
            b.clicked.connect(lambda _c=False, s=s, e=e: self._browse(s, e))
            hl.addWidget(e, 1)
            hl.addWidget(b)
            if k == "snk":
                n = QPushButton("New...")
                n.clicked.connect(lambda: self.create_snk())
                hl.addWidget(n)
            rl.addWidget(box)
            return e
        if k == "usings":
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            lst = QListWidget()
            lst.setMaximumHeight(120)
            col = QVBoxLayout()
            add, rm = QPushButton("Add..."), QPushButton("Remove")
            add.clicked.connect(lambda: self._add_using())
            rm.clicked.connect(lambda: lst.currentItem() and self.remove_using(lst.currentItem().text()))
            col.addWidget(add)
            col.addWidget(rm)
            col.addStretch(1)
            hl.addWidget(lst, 1)
            hl.addLayout(col)
            rl.addWidget(box)
            self.editors["usings"] = lst
            return lst
        if k in ("launch", "resources", "settings", "secrets"):
            b = QPushButton({"launch": "Open debug launch profiles UI", "resources": "Create or open assembly resources",
                             "settings": "Create or open application settings",
                             "secrets": "Manage User Secrets"}[k])
            b.setMaximumWidth(320)
            b.clicked.connect({"launch": self.open_launch_profiles, "resources": self.open_resources,
                               "settings": self.open_settings, "secrets": self.manage_secrets}[k])
            rl.addWidget(b)
            self.editors[k] = b
            return b
        w = QLineEdit()
        w.setMaximumWidth(520)
        w.editingFinished.connect(lambda s=s, w=w: self._write(s, w.text().strip()))
        rl.addWidget(w)
        return w

    @staticmethod
    def _combo_value(w: QComboBox) -> str:
        d = w.currentData()
        return d if d not in (None, "") or w.currentText() == "" else w.currentText()

    def _main_classes(self) -> list[str]:
        out = []
        for rel in self.project.modules[:200]:
            if not rel.lower().endswith((".cs", ".vb")):
                continue
            try:
                t = (self.project.folder / rel).read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if re.search(r"\bstatic\s+(?:async\s+)?(?:void|int|Task)\s+Main\s*\(|\bSub\s+Main\s*\(", t):
                ns = re.search(r"\bnamespace\s+([\w.]+)", t)
                cls = re.search(r"\b(?:class|Module)\s+(\w+)", t)
                if cls:
                    out.append(f"{ns.group(1)}.{cls.group(1)}" if ns else cls.group(1))
        return out

    # ------------------------------------------------------------------ values
    def condition(self) -> str:
        if self.cfg.currentText() == ALL:
            return ""
        return msprops.cfg_condition(self.cfg.currentText(), self.plat.currentText())

    def value_of(self, s: Spec) -> tuple[str, str]:
        """(value, note) shown for a property."""
        cond = self.condition() if s.per_config else ""
        v = msprops.get(self.ms, s.name, cond) if cond else None
        note = ""
        if v is None:
            v = msprops.get(self.ms, s.name)
        if v is None and cond:
            cv = [val for c, n, val in self.ms.cond_properties if n == s.name]
            if cv:
                note = "Other configurations have different values"
        if v is None:
            iv, f = msprops.inherited(self.ms, s.name)
            if iv is not None:
                v, note = iv, f"Inherited from {f.name} ({f.parent})"
        return (v if v is not None else s.default), note

    def reload_values(self):
        self._loading = True
        try:
            for s, row, ed in self.rows:
                row.note.hide()
                if s.kind == "usings":
                    ed.clear()
                    ed.addItems([n + ("  (removed)" if rm else "") for n, rm in msprops.usings(self.ms)])
                    continue
                if s.kind in ("prebuild", "postbuild"):
                    ed.setPlainText(msprops.build_event(self.ms, "pre" if s.kind == "prebuild" else "post"))
                    continue
                if not s.name:
                    continue
                v, note = self.value_of(s)
                if note:
                    row.note.setText(note)
                    row.note.show()
                ed.blockSignals(True)
                if isinstance(ed, QComboBox):
                    i = ed.findData(v)
                    if i < 0:
                        i = ed.findText(v)
                    if i >= 0:
                        ed.setCurrentIndex(i)
                    elif ed.isEditable():
                        ed.setEditText(v)
                    else:
                        ed.addItem(v, v)
                        ed.setCurrentIndex(ed.count() - 1)
                elif isinstance(ed, QCheckBox):
                    ed.setChecked(v.lower() in ("true", "enable"))
                elif isinstance(ed, QPlainTextEdit):
                    ed.setPlainText(v)
                elif isinstance(ed, QLineEdit):
                    ed.setText(v)
                ed.blockSignals(False)
        finally:
            self._loading = False

    def _write(self, s: Spec, value: str) -> bool:
        if getattr(self, "_loading", False) or not s.name:
            return False
        cond = self.condition() if s.per_config else ""
        cur = msprops.get(self.ms, s.name, cond) if cond else msprops.get(self.ms, s.name)
        if (cur or "") == (value or ""):
            return False
        if s.name == "TargetFrameworks" and value:          # multi-targeting replaces TargetFramework
            msprops.remove(self.ms, "TargetFramework")
        if s.name == "TargetFramework" and value and msprops.get(self.ms, "TargetFrameworks"):
            msprops.remove(self.ms, "TargetFrameworks")
        changed = msprops.set_value(self.ms, s.name, value, cond or None)
        if changed:
            self._saved(f"{s.name} = {value or '(removed)'}" + (f" [{self.cfg.currentText()}|"
                                                                f"{self.plat.currentText()}]" if cond else ""),
                        tree=s.name in ("OutputType", "TargetFramework", "TargetFrameworks"))
        return changed

    def set_value(self, name: str, value: str, configuration: str = ALL) -> bool:
        """Test/automation entry: set a property as if typed in the page."""
        s = next(x for x in SPECS if x.name == name)
        if s.per_config:
            self.cfg.setCurrentText(configuration)
        return self._write(s, value)

    def _saved(self, what: str, tree: bool = False):
        self.ms.save()
        try:
            self.project.reload()
        except Exception as e:  # noqa: BLE001
            ops._log(self.win, f"*** {self.project.name}: {e}")
        ops._log(self.win, f"{self.project.name}: {what} ({self.ms.path.name})")
        if tree:
            ops.refresh(self.win)
        self.reload_values()

    # ------------------------------------------------------------------ special rows
    def set_build_event(self, which: str, command: str) -> bool:
        if getattr(self, "_loading", False):
            return False
        if msprops.set_build_event(self.ms, which, command):
            self._saved(f"{which}-build event updated")
            return True
        return False

    def _add_using(self):
        ns, ok = QInputDialog.getText(self, "Add global using", "Namespace:")
        if ok and ns.strip():
            self.add_using(ns.strip())

    def add_using(self, ns: str) -> bool:
        try:
            ok = msprops.add_using(self.ms, ns)
        except ValueError as e:
            ops._log(self.win, f"*** {e}")
            return False
        if ok:
            self._saved(f"global using {ns} added")
        return ok

    def remove_using(self, ns: str) -> bool:
        ns = ns.replace("  (removed)", "")
        if msprops.remove_using(self.ms, ns):
            self._saved(f"global using {ns} removed")
            return True
        return False

    def _browse(self, s: Spec, e: QLineEdit):
        filt = {"ApplicationIcon": "Icons (*.ico)", "ApplicationManifest": "Manifests (*.manifest)",
                "AssemblyOriginatorKeyFile": "Strong name keys (*.snk *.pfx)"}.get(s.name, "All files (*)")
        f, _ = QFileDialog.getOpenFileName(self, s.label, str(self.project.folder), filt)
        if f:
            try:
                f = os.path.relpath(f, self.project.folder)
            except ValueError:
                pass
            e.setText(f)
            self._write(s, f)

    def create_snk(self, name: str | None = None) -> Path | None:
        if name is None:
            name, ok = QInputDialog.getText(self, "Create Strong Name Key", "Key file name:",
                                            text=f"{self.project.name}.snk")
            if not ok or not name.strip():
                return None
        p = signing.create_snk(self.project.folder / name.strip())
        msprops.set_value(self.ms, "AssemblyOriginatorKeyFile", p.name)
        msprops.set_value(self.ms, "SignAssembly", "True")
        if not self.ms.is_sdk:
            self.ms.add_item("None", p.name)
        self._saved(f"strong name key {p.name} created; SignAssembly = True")
        return p

    def open_launch_profiles(self):
        return launch_profiles_dialog(self.win, self.project)

    def _props_dir(self) -> Path:
        return self.project.folder / ("My Project" if self.ms.language == "VB" else "Properties")

    def open_resources(self, open_it: bool = True) -> Path:
        p = self._props_dir() / "Resources.resx"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(RESX_TEMPLATE, encoding="utf-8")
            if not self.ms.is_sdk:
                self.ms.add_item("EmbeddedResource", os.path.relpath(p, self.project.folder),
                                 {"Generator": "ResXFileCodeGenerator"})
                self._saved("Resources.resx added")
            ops._log(self.win, f"{self.project.name}: created {p}")
        if open_it:
            self._open_file(p)
        return p

    def open_settings(self, open_it: bool = True) -> Path:
        p = self._props_dir() / "Settings.settings"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            ns = self.ms.root_namespace
            p.write_text(SETTINGS_TEMPLATE.format(ns=ns), encoding="utf-8")
            rel = os.path.relpath(p, self.project.folder)
            self.ms.add_item("None", rel, {"Generator": "SettingsSingleFileGenerator",
                                           "LastGenOutput": "Settings.Designer.cs"})
            self._saved("Settings.settings added")
        if open_it:
            self._open_file(p)
        return p

    def manage_secrets(self, open_it: bool = True) -> Path:
        p = secrets.open_secrets(self.ms)
        try:
            self.project.reload()
        except Exception:  # noqa: BLE001
            pass
        ops._log(self.win, f"{self.project.name}: user secrets {p}")
        if open_it:
            self._open_file(p)
        return p

    def _open_file(self, p: Path):
        try:
            self.win.open_any_file(Path(p))
        except Exception as e:  # noqa: BLE001
            ops._log(self.win, f"*** cannot open {p}: {e}")

    # ------------------------------------------------------------------ search / navigation
    def _filter(self, text: str):
        t = text.strip().lower()
        visible_pages = set()
        for s, row, _ed in self.rows:
            hit = not t or t in s.label.lower() or t in s.desc.lower() or t in s.name.lower() or t in s.page.lower()
            row.setVisible(hit)
            if hit:
                visible_pages.add(s.page)
        for page, h in self.headers.items():
            h.setVisible(page in visible_pages)

    def visible_labels(self) -> list[str]:
        return [s.label for s, row, _e in self.rows if not row.isHidden()]

    def _nav(self, it, _prev):
        if it is None:
            return
        page = it.data(0, ROLE)
        h = self.headers.get(page)
        if h is not None:
            self.scroll.ensureWidgetVisible(h, 0, 0)
            self.scroll.verticalScrollBar().setValue(h.y())

    def maybe_close(self) -> bool:
        return True


RESX_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <xsd:schema id="root" xmlns="" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:msdata="urn:schemas-microsoft-com:xml-msdata">
    <xsd:element name="root" msdata:IsDataSet="true" />
  </xsd:schema>
  <resheader name="resmimetype">
    <value>text/microsoft-resx</value>
  </resheader>
  <resheader name="version">
    <value>2.0</value>
  </resheader>
  <resheader name="reader">
    <value>System.Resources.ResXResourceReader, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
  </resheader>
  <resheader name="writer">
    <value>System.Resources.ResXResourceWriter, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
  </resheader>
</root>
"""

SETTINGS_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<SettingsFile xmlns="http://schemas.microsoft.com/VisualStudio/2004/01/settings" CurrentProfile="(Default)" GeneratedClassNamespace="{ns}.Properties" GeneratedClassName="Settings">
  <Profiles />
  <Settings />
</SettingsFile>
"""


def open_project_properties(win, project):
    """Show (or bring to front) the Properties document of a .NET project."""
    for i in range(win.tabs.count()):
        w = win.tabs.widget(i)
        if isinstance(w, ProjectPropertiesDocument) and w.project is project:
            win.tabs.setCurrentIndex(i)
            w.reload_values()
            return w
    doc = ProjectPropertiesDocument(win, project)
    try:
        doc.setProperty("radProject", win._pkey(project))
    except Exception:  # noqa: BLE001
        pass
    i = win.tabs.addTab(doc, project.name)
    win.tabs.setTabToolTip(i, f"{project.name} Properties ({project.ms.path})")
    win.tabs.setCurrentIndex(i)
    return doc


# ====================================================================== launch profiles UI
class LaunchProfilesDialog(QDialog):
    def __init__(self, win, project):
        super().__init__(win)
        self.win, self.project, self.ms = win, project, project.ms
        self.data = launch.ensure_default(project.folder, project.ms.name, project.ms.language)
        self.setWindowTitle("Launch Profiles")
        self.resize(780, 520)
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        bar = QHBoxLayout()
        self.btn_new = QToolButton()
        self.btn_new.setText("New")
        m = QMenu(self.btn_new)
        m.addAction("Project", lambda: self.new_profile("Project"))
        m.addAction("Executable", lambda: self.new_profile("Executable"))
        self.btn_new.setMenu(m)
        self.btn_new.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        ren, dele = QPushButton("Rename"), QPushButton("Delete")
        ren.clicked.connect(self._rename)
        dele.clicked.connect(lambda: self.delete_profile(self.current()))
        for b in (self.btn_new, ren, dele):
            bar.addWidget(b)
        left.addLayout(bar)
        self.list = QListWidget()
        left.addWidget(self.list, 1)
        lay.addLayout(left, 1)
        self.form_host = QWidget()
        f = QFormLayout(self.form_host)
        self.command = QLabel()
        self.exe = QLineEdit()
        self.args = QPlainTextEdit()
        self.args.setMaximumHeight(70)
        self.cwd = QLineEdit()
        self.env = QTableWidget(0, 2)
        self.env.setHorizontalHeaderLabels(["Name", "Value"])
        self.env.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.env.setMaximumHeight(150)
        env_btns = QHBoxLayout()
        add_env, rm_env = QPushButton("Add"), QPushButton("Remove")
        add_env.clicked.connect(lambda: self.env.insertRow(self.env.rowCount()))
        rm_env.clicked.connect(lambda: self.env.removeRow(self.env.currentRow()))
        env_btns.addWidget(add_env)
        env_btns.addWidget(rm_env)
        env_btns.addStretch(1)
        self.browser = QCheckBox("Launch browser")
        self.url = QLineEdit()
        self.app_url = QLineEdit()
        f.addRow("Command:", self.command)
        f.addRow("Executable:", self.exe)
        f.addRow("Command line arguments:", self.args)
        f.addRow("Working directory:", self.cwd)
        f.addRow("Environment variables:", self.env)
        f.addRow("", env_btns)
        f.addRow("", self.browser)
        f.addRow("Url:", self.url)
        f.addRow("App URL:", self.app_url)
        right = QVBoxLayout()
        right.addWidget(self.form_host, 1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        right.addWidget(box)
        lay.addLayout(right, 3)
        self._cur = ""
        self._fill_list()
        self.list.currentTextChanged.connect(self._switch)
        self.finished.connect(lambda _r: self.save())

    def _fill_list(self, select: str = ""):
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems(launch.profile_names(self.data))
        self.list.blockSignals(False)
        names = launch.profile_names(self.data)
        if names:
            self.list.setCurrentRow(names.index(select) if select in names else 0)
            self._switch(self.list.currentItem().text())

    def current(self) -> str:
        it = self.list.currentItem()
        return it.text() if it else ""

    def _switch(self, name: str):
        if self._cur and self._cur in self.data["profiles"]:
            self._store(self._cur)
        self._cur = name
        p = self.data["profiles"].get(name) or {}
        cmd = p.get("commandName", "Project")
        self.command.setText(cmd)
        self.exe.setText(p.get("executablePath", ""))
        self.exe.setEnabled(cmd == "Executable")
        self.args.setPlainText(p.get("commandLineArgs", ""))
        self.cwd.setText(p.get("workingDirectory", ""))
        self.env.setRowCount(0)
        for k, v in (p.get("environmentVariables") or {}).items():
            r = self.env.rowCount()
            self.env.insertRow(r)
            self.env.setItem(r, 0, QTableWidgetItem(k))
            self.env.setItem(r, 1, QTableWidgetItem(str(v)))
        self.browser.setChecked(bool(p.get("launchBrowser")))
        self.url.setText(p.get("launchUrl", ""))
        self.app_url.setText(p.get("applicationUrl", ""))

    def _store(self, name: str):
        p = dict(self.data["profiles"].get(name) or {})
        for key, val in (("executablePath", self.exe.text().strip() if p.get("commandName") == "Executable" else ""),
                         ("commandLineArgs", self.args.toPlainText().strip()), ("workingDirectory", self.cwd.text().strip()),
                         ("launchUrl", self.url.text().strip()), ("applicationUrl", self.app_url.text().strip())):
            if val:
                p[key] = val
            else:
                p.pop(key, None)
        env = {}
        for r in range(self.env.rowCount()):
            k = self.env.item(r, 0)
            v = self.env.item(r, 1)
            if k is not None and k.text().strip():
                env[k.text().strip()] = v.text() if v is not None else ""
        if env:
            p["environmentVariables"] = env
        else:
            p.pop("environmentVariables", None)
        if self.browser.isChecked():
            p["launchBrowser"] = True
        else:
            p.pop("launchBrowser", None)
        self.data["profiles"][name] = p

    def set_fields(self, args: str = None, cwd: str = None, env: dict | None = None, exe: str = None):
        if args is not None:
            self.args.setPlainText(args)
        if cwd is not None:
            self.cwd.setText(cwd)
        if exe is not None:
            self.exe.setText(exe)
        if env is not None:
            self.env.setRowCount(0)
            for k, v in env.items():
                r = self.env.rowCount()
                self.env.insertRow(r)
                self.env.setItem(r, 0, QTableWidgetItem(k))
                self.env.setItem(r, 1, QTableWidgetItem(v))

    def new_profile(self, command: str, name: str = "") -> str:
        if self._cur:
            self._store(self._cur)
        base = name or ("Profile" if command == "Project" else "Executable")
        n, i = base, 1
        while n in self.data["profiles"]:
            i += 1
            n = f"{base} {i}"
        self.data["profiles"][n] = {"commandName": command}
        self._cur = ""
        self._fill_list(n)
        return n

    def _rename(self):
        old = self.current()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "Rename profile", "Name:", text=old)
        if ok and new.strip() and new.strip() not in self.data["profiles"]:
            self._store(old)
            self.data["profiles"] = {(new.strip() if k == old else k): v for k, v in self.data["profiles"].items()}
            self._cur = ""
            self._fill_list(new.strip())

    def delete_profile(self, name: str):
        if name in self.data["profiles"]:
            del self.data["profiles"][name]
            self._cur = ""
            self._fill_list()

    def save(self) -> Path:
        if self._cur and self._cur in self.data["profiles"]:
            self._store(self._cur)
        p = launch.save(self.project.folder, self.data, self.ms.language)
        ops._log(self.win, f"{self.project.name}: launch profiles saved ({p})")
        try:
            from . import run
            run.refresh_profile_combo(self.win)
        except Exception:  # noqa: BLE001
            pass
        return p


def launch_profiles_dialog(win, project, exec_: bool = True):
    dlg = LaunchProfilesDialog(win, project)
    if exec_ and not OFFSCREEN:
        dlg.exec()
    return dlg
