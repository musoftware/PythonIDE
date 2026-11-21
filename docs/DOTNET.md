# .NET in RAD IDE (Visual Studio 2022 parity)

Each area of the .NET support has its own section below (one per feature slice).

## Shared Projects and project templates (`radide/dotnet/shared/`, `radide/dotnet/templates/`)

### API for other slices (Reference Manager "Shared Projects" tab, ...)

`from radide.dotnet.shared import model as SH` (no Qt):

| Call | What it does |
|---|---|
| `SH.SharedProject(path)` | Open a `.shproj` (or its `.projitems`). Attributes: `name`, `path`, `projitems_path`, `language` (`"C#"`/`"VB"`), `guid` (`{UPPER}`), `shared_guid` (lower, no braces), `root_namespace`, `items`; `files()`, `code_files()`, `folders()`, `abs_path(rel)`, `contains(path)` |
| `SH.solution_shared_projects(sln_model)` | Shared projects of a `SlnModel` / `SlnxModel` (`win.sln.model` of a `VsSolution`); each has `.sln_entry` |
| `SH.can_reference(project_file, shared)` | `(ok, reason)`: only same-language projects (C# -> .csproj, VB -> .vbproj), like VS lists them |
| `SH.references_shared(project_file, shared)` | Is the shared project imported by the project? |
| `SH.shared_imports(project_file)` | Absolute `.projitems` paths imported with `Label="Shared"` |
| `SH.add_shared_reference(project_file, shared)` | Writes `<Import Project="..\X\X.projitems" Label="Shared" />` where VS puts it (SDK: before `</Project>`; old-style: before `Microsoft.CSharp.targets`). Returns False if already there; `ValueError` on a language mismatch |
| `SH.remove_shared_reference(project_file, shared)` | Removes that Import |
| `SH.consumers(shared, project_files)` | Projects that import it |
| `SH.create_shared_project(parent, name, "C#"/"VB")` | `<parent>/<name>/<name>.shproj + .projitems` (empty, like VS's template) |
| `SH.add_to_solution(sln_model, shared)` / `SH.remove_from_solution(...)` | `.sln`: `Project("{D954291E-2A0B-460D-934E-DC6B0785DB48}") = ...` (no configuration lines); `.slnx`: `<Project Path=... />` |
| `SH.record_sln_shared_reference(sln_model, project_file, shared)` / `SH.drop_sln_shared_reference(...)` | The `<projitems>*{guid}*SharedItemsImports = 13/4/5` lines VS keeps in `GlobalSection(SharedMSBuildProjectFiles)` of a `.sln` (13 = the shared project, 4 = an old-style consumer, 5 = an SDK-style one); optional, no-op for `.slnx` |
| `shared.add_new_item(template, rel_dir, name)`, `add_existing_item(path, rel_dir)`, `new_folder(rel)`, `exclude(rel)`, `delete(rel)`, `rename_item(rel, new)`, `rename(new_name, consumers, sln_model)` | Edits of the `.projitems` (`$(MSBuildThisFileDirectory)` items) |

Project contexts, `from radide.dotnet.shared import context as CX` (no Qt):

| Call | What it does |
|---|---|
| `CX.solution_contexts(vs_solution, path)` | Contexts of a `.cs`/`.vb` file of the open solution: every consuming project (shared file) or the owning project, x each target framework, with the project's active solution configuration |
| `CX.contexts_for_file(path, project_files, shared_projects=(), names=None)` | The same from plain project files (no IDE) |
| `ProjectContext` | `name`, `tfm`, `multi`, `shared`, `configuration`, `platform`, `project`; `label` (`"WinApp (net8.0-windows)"`), `language`, `symbols(cfg=None, plat=None)` (C#: list, VB: `{name: value}`), `inactive_ranges(text, cfg=None, plat=None)` |
| `CX.project_files(vs_solution)`, `CX.shared_project_of(path, shared_projects)`, `CX.symbols_text(ctx)` | Helpers |

New projects, `from radide.dotnet.templates import catalog as C, create as K` (no Qt):
`C.all_templates()` / `C.find(templates, short_name_or_key, language)`;
`K.create(K.NewProjectRequest(template, name, location, solution_name="", same_dir=False, framework="",
options={}, solution=None))` -> `NewProjectResult(project_file, solution_file, log)` (raises `ValueError` with VS's
message); `K.paths_for(req)`, `K.validate_name(name)`, `K.add_to_solution(sln_file, project_file)`.

UI helpers (Qt) in `radide.dotnet.shared.ui`: `add_shared_reference_dialog(win, project)` (the VS "Add Shared Project
Reference" picker), `shared_projects_of(win)`, `refresh(win)`; `radide.dotnet.shared.ui.SharedReferencesTab(win,
project)` is a ready-made "Shared Projects" tab (checkable list + `apply()`) that a Reference Manager can embed.

### Modules

| Module | Qt | What |
|---|---|---|
| `shared/model.py` | no | `.shproj` / `.projitems` model, consumers (`<Import Label="Shared">`), solution entries |
| `shared/preprocessor.py` | no | DefineConstants per configuration / platform / target framework (SDK implicit symbols `NET8_0`, `NET8_0_OR_GREATER`, `NETCOREAPP`, `NETSTANDARD2_0`, `NETFRAMEWORK`, `NET48`, `WINDOWS`...; VB `DefineDebug` / `DefineTrace`, `CONFIG`, `PLATFORM`, `_MyType`), MSBuild condition evaluation, inactive `#if` / `#If` ranges (nested, `#elif`, `#define`, `#Const`) |
| `shared/context.py` | no | `ProjectContext`: the project contexts of a file (consuming project x target framework) and their symbols / inactive ranges (the single model; `ctxbar.py` only shows it) |
| `shared/ctxbar.py` | yes | the project-context combo above the editor + greying (Monaco decorations / built-in editor extra selections); `CONTEXT_HOOKS` for a language server |
| `shared/ui.py` | yes | Solution Explorer nodes (`solution_ui.TREE_HOOKS`), context menus (`MENU_HOOKS`), dialogs, File menu entry; installed from `vs_ui.install` |
| `templates/catalog.py` | no | installed `dotnet new` templates read from the template engine cache (`~/.templateengine/dotnetcli/<sdk>/templatecache.json`: full names, languages, classifications, parameters with choices / defaults / CLI option names, the frameworks of all template-pack versions), `dotnet new list` text as a fallback; RAD IDE's templates |
| `templates/writers.py` | no | templates `dotnet new` lacks, written like VS2022: Shared Project (C#/VB), Class Library / Console App / Windows Forms App (.NET Framework, C# and VB old-style), WPF App and Windows Service (.NET Framework, C#), Class Library (.NET Standard, C#/VB) |
| `templates/create.py` | no | folders like VS (new solution / same directory / add to the open solution), `dotnet new ...` for CLI templates, the project listed in the .sln/.slnx by a text edit |
| `templates/wizard.py` | yes | VS2022's dialog: Create a new project (recent templates, search, All languages / All platforms / All project types), Configure your new project, Additional information (framework + template options) |

### Solution Explorer and menus

* `.shproj` entries of the .sln / .slnx are shown with a shared-project icon, in their solution folder, with folders
  and files from the `.projitems` (kinds `foreign_shproj`, `foreign_shfolder`, `foreign_shfile`); the root reads
  "Solution 'X' (n of n projects)" counting them, like VS.
* Consumers: Dependencies > Shared Projects (SDK-style) / References (old-style). When the refs slice already lists
  them (`foreign_dep` `shared|...`), its items are reused (no duplicate node).
* Shared project menu: Add > New Item / Existing Item / New Folder / Class; Rename (renames `.shproj` + `.projitems`,
  updates every consumer's Import and the .sln); Remove (from the solution); Edit `<Name>.projitems`; Properties
  (root namespace). Folder: Add, Delete. File: Open, Exclude From Project, Delete, Rename.
* Project menu: Add > Shared Project Reference...; Dependencies: Add Shared Project Reference...
* Solution menu: Add > New Project... opens the wizard; Add > Existing Project... also accepts `.shproj`;
  Add > New Shared Project... File menu: New Project (.NET, Visual Studio 2022)... (Ctrl+Alt+Shift+N).

### Editor project context

A C#/VB file of a shared project (or of a multi-targeted project) gets a combo above the editor listing its
contexts - every consuming project x target framework (`WinApp (net8.0-windows)`, `FxConsole (net48)`) - and the
symbols of the selected one next to it. Code the context does not compile is greyed (re-evaluated 400 ms after an
edit, and when the context changes). Files of ordinary projects with `#if` blocks are greyed for their own context.
Old-style .NET Framework projects get only their DefineConstants (`DEBUG;TRACE`), exactly like MSBuild: the implicit
framework symbols (`NETFRAMEWORK`, `NET48`, ...) come from the .NET SDK targets, so an old-style net48 project compiles
the `#else` branch of `#if NET8_0_OR_GREATER / #elif NETFRAMEWORK / #else`, while an SDK-style net48 project compiles
the `NETFRAMEWORK` one (verified by building and running both in the sample). SDK-style projects get `TRACE;DEBUG`
(or `RELEASE`) from the SDK props before the project body - a plain `<DefineConstants>X</DefineConstants>` replaces
them, as in MSBuild - and the framework symbols after it (unless `DisableImplicitFrameworkDefines`). The context is not passed to csharp-ls (it has no project-context
API); `ctxbar.CONTEXT_HOOKS` is where a server that supports it can be wired.

### Notes

* `dotnet sln add` is not used: it also adds x64 / x86 solution platforms (VS does not) and cannot add a `.shproj`.
  `radide/foreign/msbuild.py project_platform` maps a solution platform a .NET project does not have to AnyCPU (VS).
* `GlobalSection(SharedMSBuildProjectFiles)` is optional (MSBuild ignores it; VS regenerates it). The IDE's Shared
  Project Reference dialog writes / removes the lines with `record_sln_shared_reference` / `drop_sln_shared_reference`.
* Tests: `samples/Tests/DotNet/SharedProjects/make_and_build.py` (back end + MSBuild build of a solution with C#/VB
  shared projects used by .NET 8, SDK-style net48 and .NET Framework 4.8 old-style projects, a multi-targeted
  library, the #if contexts checked against what each built program prints; 67 checks) and `ui_test.py` (IDE).

## References: Reference Manager, reference properties, Object Browser (`radide/dotnet/refs/`)

What Visual Studio 2022 does with references, for the C# / VB / F# projects of a `.sln` / `.slnx` / project
opened in place (`radide/foreign/vs_ui.py` calls in through three small hooks: `add_reference_dialog` delegates
to the Reference Manager, `_fill_deps` calls `fill_extra_deps`, `install` calls `refs.ui.install`).

### Reference Manager (`manager.py`)

Project > Add > Project / Shared Project / COM / Assembly Reference..., or right-click Dependencies / References.
Same layout as VS: category tree on the left, **Search (Ctrl+E)** box, checkable list, details pane (name,
version, target framework, strong name, file), **Browse...**, OK / Cancel. OK writes every checked/unchecked
entry, saves, reloads the project and the C# language server.

| Page | Lists | Writes |
|---|---|---|
| Assemblies > Framework (.NET Framework projects) | `Reference Assemblies\Microsoft\Framework\.NETFramework\vX\RedistList\FrameworkList.xml` (or the `Microsoft.NETFramework.ReferenceAssemblies.netXY` package in the NuGet cache) | `<Reference Include="System.Numerics" />` |
| Assemblies > Framework (SDK projects) | the note VS shows ("All Framework assemblies are already referenced...") + shared frameworks; implicit ones are checked and disabled | `<FrameworkReference Include="Microsoft.AspNetCore.App" />` |
| Assemblies > Extensions | `AssemblyFoldersEx` / `AssemblyFolders` (HKLM + HKCU, 32/64-bit registry views) | `<Reference>` + `HintPath` |
| Assemblies > Recent, Browse > Recent, COM > Recent | QSettings `dotnet/refs/recent*` | |
| Projects > Solution | the other projects (circular references are refused with VS's message) | `<ProjectReference>` (+ `Project`/`Name` in old-style projects) |
| Shared Projects | `radide/dotnet/shared/model.py` `solution_shared_projects` filtered by `can_reference`; fallback: `.shproj` in the `.sln` / folder | the shared slice's `add_shared_reference` (fallback `edits.add_shared_import`) |
| COM > Type Libraries | `HKCR\TypeLib` (hidden/restricted skipped), library name read with `LoadTypeLibEx` + `ITypeLib::GetDocumentation(-1)` | `<COMReference Include="Scripting">` with `WrapperTool`, `VersionMinor`, `VersionMajor`, `Guid`, `Lcid`, `Isolated`, `EmbedInteropTypes=true`; SDK projects get a note that only Visual Studio's MSBuild builds COM references |
| Browse | `.dll` / `.exe` / `.winmd`, validated (CLI header) | `<Reference Include="MathKit"><HintPath>..\MathKit\bin\Debug\net9.0\MathKit.dll</HintPath>` (old-style + strong-named: full identity + `SpecificVersion=False`). A **native DLL** is explained (DllImport / P/Invoke) and can be copied to the output (`<None Include=... Link=... CopyToOutputDirectory=PreserveNewest>`); `.tlb` points to the COM page |

`reference_manager(win, project, tab, exec_=False)` returns the dialog: `select_page("com")`, `check(page, name)`,
`add_browse_file(path)`, `apply()` -> `["+MathKit.dll", "+Scripting (COM)", ...]`. `tab` accepts the old indexes
(0 projects, 1 assemblies, 2 browse) and page ids (`framework`, `extensions`, `projects`, `shared`, `com`, `browse`).

### Solution Explorer

* Dependencies (SDK): Frameworks (implicit + explicit FrameworkReference), Packages, Projects, Assemblies, **COM**,
  **Shared Projects**; References (old-style) lists COM and shared imports too.
* Menus: Dependencies -> Add Project Reference / Add Shared Project Reference / Add COM Reference / Add Assembly
  Reference; a reference -> **Open in Object Browser**, Remove, **Properties** (Alt+Enter).
* **Properties window** (`props.py`): selecting a reference replaces the form grid with "<name> Reference
  Properties": Aliases, Copy Local (`Private`), Embed Interop Types, Specific Version (editable, written back;
  Specific Version = True rewrites a bare name to the full identity like VS, because MSBuild cannot resolve a
  specific version from a bare name; Aliases = global removes the metadata), Path, Version, Identity, Culture,
  Runtime Version, Strong Name, Resolved (read-only). COM: Guid, Lcid, Isolated, Wrapper Tool; project
  references: Reference Output Assembly. `reference_rows()` / `apply_value()` are the Qt-free core.
* **Add > Existing Item...**: the dialog has **Add** and **Add As Link** (`<Compile Include="..\Common\X.cs"
  Link="Folder\X.cs" />`); linked files show at their Link folder with a link icon.

### Object Browser (`object_browser.py`, View > Object Browser, Ctrl+Alt+J)

Browse **My Solution** (each project's resolved references, project outputs, NuGet package assemblies from
`~/.nuget/packages/<id>/<ver>/ref|lib/<tfm>`, mscorlib for .NET Framework, the shared framework reference packs
under `dotnet\packs\*.Ref`) or a **Custom Component Set** (`...`). Assemblies > namespaces > types (nested types
under their parent) > members with C# signatures; the description pane shows the declaration, "Member of",
and the XML documentation (summary, parameters, returns, remarks) from the `.xml` next to the dll. Search
(Enter) finds types and members; Settings > Show Private Members. **Go To Definition** (F12 / double-click) opens
the type decompiled by `radide/dotnet/decompile.py` (ilspycmd, installed from nuget.org only after asking:
"Decompile with ILSpy...") or, without ilspycmd, a metadata-as-source stub (`#region Assembly ...` + signatures
+ `///` summaries) cached under `%LOCALAPPDATA%\RADIDE\cache\metadata-as-source`. Both open read-only.

### Metadata reader (`metadata.py`, pure Python)

ECMA-335 reader of the `#~` tables: assembly identity, public key token, target framework attribute,
references, every TypeDef (kind, base, interfaces, generic parameters, nesting) and members (fields, constants,
enum values, methods/constructors/operators with parameter names, properties/indexers with accessor visibility,
events), C# signatures (aliases, `T?`, generics, arrays, `ref`), XML doc ids (`M:NS.Type.Method(System.Int32)`,
`` `0 `` / ``` ``0 ```), `metadata_as_source(type)`, `is_managed(path)` (headers only), `pe_kind(path)`.
mscorlib (2993 types) loads in 0.07 s; all 12,788 members of System.Windows.Forms decode in about 0.2 s.

### Language server

`lsp_reload.project_file_changed(win, project_file)` (called by `edits.commit`) sends
`workspace/didChangeWatchedFiles` to the C# servers whose workspace holds the project and restarts them so
csharp-ls reloads the project with its new references; open editors are attached to the new server.

### Tests

* `samples/Tests/DotNet/References/tests/test_refs_core.py` - 46 checks, no window: builds MathKit, metadata +
  XML docs + stub, SDK Browse reference -> dotnet build + run, properties round trip, FrameworkReference build,
  native DLL copy, .NET Framework 4.8 project with Framework + Browse + COM (Scripting) + Add As Link built by
  Visual Studio's MSBuild and run, SDK + COM with VS MSBuild, shared imports.
* `samples/Tests/DotNet/References/tests/test_refs_ui.py` - 40 checks in the IDE (qh.py): Reference Manager pages
  and search, Dependencies menus and nodes, Properties window editing, circular reference, Shared Projects page,
  Add As Link, Object Browser (types, members, docs, search, Go To Definition), language server reload.

## Solutions: merging, folders, dependencies, startup, configurations, properties, publish (`radide/dotnet/sln/`)

Everything goes through `radide/dotnet/sln/model.py` `SolutionDoc`, one model for both solution formats:

* **`.sln`** (Format Version 12.00) is parsed into projects, solution folders + solution items, ProjectDependencies,
  NestedProjects, SolutionConfigurationPlatforms and the per-project mapping (ActiveCfg / Build.0 / Deploy.0);
  unknown sections are kept as written. An unchanged file is written back **byte-identical** (BOM, CRLF, section
  and line order); edits re-generate only the changed sections, in Visual Studio's layout.
* **`.slnx`** (VS 2022 17.10+ / SDK 9.0.200+) is read and written in the canonical layout of Visual Studio /
  `dotnet sln migrate`: sorted `<BuildType>`/`<Platform>`, `<Folder Name="/A/B/">` (parents written), Files before
  Projects, `<BuildDependency>`, and the fewest configuration rules (`<BuildType Project="Release" />`,
  `Solution="QA|*"`, `Solution="*|x64"`, single `Debug|x64`; `Project="?"` = not mapped). Converting any `.sln` to
  `.slnx` gives the same text as `dotnet sln migrate` (tested), `.slnx -> .sln -> .slnx` is stable.
* Edits: add any project file (`.csproj .vbproj .fsproj .vcxproj .shproj .sqlproj .wapproj .pyproj .esproj .dcproj
  .wixproj .proj`, with the right type GUID and a mapping for every solution configuration), remove (folders with
  their content), move between folders (cycles refused), add/rename/remove solution folders and solution items,
  ProjectDependencies (circular ones refused), build order (dependencies + `ProjectReference`s), new/rename/remove
  solution configurations and platforms (copying the mapping), per-project configuration/platform/Build/Deploy,
  `import_from(other_solution, guids)` (merge: folders recreated, mapping carried over, dependencies remapped).

`ops.py` applies an edit to the open solution (save + `sync`: new projects loaded, removed ones closed, the tree,
configuration combos and file watcher refreshed). IDE-only state that Visual Studio keeps in its `.suo`
(unloaded projects, multiple startup projects, the active launch profile) is in the solution's IDE state folder
(`%APPDATA%\RADIDE\foreign\<name>-<hash>\solution-ext.json`), never next to the user's files.

### In the IDE (hooks installed by `radide/foreign/vs_ui.install` -> `radide.dotnet.sln.install`)

* **Solution Explorer**: right-click the solution > Add > New Project (`dotnet new` templates + Shared Project),
  Existing Project (any type), **Existing Solution's Projects...** (checklist of the other `.sln/.slnx`, folders
  recreated), **Existing RAD IDE Project...**, New Item / Existing Item (solution items: Directory.Build.props,
  Directory.Packages.props, .editorconfig, global.json, nuget.config...), **New Solution Folder**; Solution
  Configuration > Configuration Manager; Project Dependencies / Project Build Order; Configure Startup Projects;
  **Save Solution As .slnx / .sln** (a lone project: Save Solution File); New Solution from Existing Folders.
  Solution folders: Add (as above, into the folder), Build (its projects), Move To Solution Folder, Rename, Remove.
  Projects: Configure Startup Projects, Build Dependencies, **Unload Project** (greyed "(unloaded)" node in its
  folder, "(5 of 6 projects)", not built or run; Reload Project / Edit Project File / Remove on it), Move To
  Solution Folder, Publish..., Manage User Secrets, Open debug launch profiles UI, Remove from Solution (works for
  `.slnx` too). **Drag & drop** projects and folders onto solution folders / the solution node. Projects of types
  RAD IDE does not load (`.sqlproj` ...) are shown and can be removed; Directory.Build.props/.targets and
  Directory.Packages.props that MSBuild imports are shown in italics (Add to Solution Items).
* **Configuration Manager** (Build menu, solution menu, Project menu): active solution configuration / platform with
  `<New...>` (copy settings from, create new project configurations -> `<Configurations>` of SDK projects) and
  `<Edit...>` (rename / remove), and the project grid (Configuration / Platform with `<New...>`, Build, Deploy).
  Written to the `.sln`/`.slnx` on Close; the toolbar combos follow.
* **Project Dependencies** (tabs Dependencies / Build Order; projects referenced by a `ProjectReference` are shown
  checked and disabled like VS) - writes ProjectSection(ProjectDependencies) / `<BuildDependency>`.
* **Solution Property Pages** (solution > Properties): Startup Project (Current selection / Single / **Multiple
  startup projects** with Action None / Start / Start without debugging and Move Up/Down), Project Dependencies,
  Configuration. With multiple startup projects F5/Ctrl+F5 builds every started project, gives the debugger to
  the first "Start" project and runs the others beside it (output prefixed `[Name]`); Stop stops them all; they are
  bold in Solution Explorer.
* **Project Properties document** (project > Properties, a tab like VS 2022): search box, left navigation,
  Configuration / Platform selectors ("All configurations" writes the unconditional property, a configuration
  writes `<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|AnyCPU'">`), every change written at
  once, format preserving. Pages: Application (output type, target framework, **multi-targeting
  TargetFrameworks**, .NET Framework version for old-style projects, startup object with the classes that have a
  Main, assembly name, default namespace, icon, manifest), Global Usings (ImplicitUsings + `<Using>` items), Build
  (conditional symbols, platform target, nullable, unsafe, optimize, debug symbols, warning level, warnings as
  errors, NoWarn, output paths, documentation file, **pre/post-build events** as `PreBuild`/`PostBuild` targets -
  legacy projects: PreBuildEvent/PostBuildEvent - , language version, overflow checks, deterministic), Package
  (NuGet metadata, generate on build, license, symbols), Code Analysis, Debug (launch profiles UI), Resources
  (create/open `Properties\Resources.resx`), Settings (`Settings.settings`), Signing (SignAssembly, key file,
  **New... creates a .snk** - `signing.py` writes the CryptoAPI PRIVATEKEYBLOB `sn -k` writes, verified by building
  a strong-name signed assembly), User Secrets. Values inherited from Directory.Build.props are shown with
  "Inherited from Directory.Build.props". C++ projects keep the classic dialog.
* **Launch profiles** (`launch.py`, `properties.LaunchProfilesDialog`): `Properties/launchSettings.json` (VB:
  `My Project`), New Project / Executable profile, rename, delete, command line arguments, working directory,
  environment variables, launch browser + URL, app URL. A **profile drop-down** next to the configuration combos
  (with "Open debug launch profiles UI..."). F5/Ctrl+F5 (`run.py`, wraps `vs_ui.run_session`): Project profiles
  run the built output (apphost exe or `dotnet App.dll`) with the profile's arguments / environment
  (ASPNETCORE_URLS from applicationUrl) / working directory (default: the output folder, like VS); Executable
  profiles start `executablePath` (`%VAR%` and `$(TargetDir)`-style macros expanded); with netcoredbg the same
  values go into the launch request; launchBrowser opens the URL. IIS Express profiles fall back to the project.
* **User Secrets** (`secrets.py`): Manage User Secrets adds `<UserSecretsId>` and opens
  `%APPDATA%\Microsoft\UserSecrets\<id>\secrets.json` (what `dotnet user-secrets` uses).
* **Publish** (`publish.py`, `dialogs.PublishDialog`): Folder profiles in `Properties/PublishProfiles/*.pubxml`
  (configuration, target framework, framework-dependent / self-contained, target runtime, single file,
  ReadyToRun, trimming, target location), Save, Publish (`dotnet publish <proj> -p:PublishProfile=<name>`, output
  in the Output window).
* **New Solution from Existing Folders** (File menu, solution menu): every project file below the chosen folders,
  nested in solution folders named after their directories, `.sln` or `.slnx`, then opened.
* **RAD IDE projects in a VS solution**: Add > Existing RAD IDE Project... adds a RAD IDE C# (GUI Bridge) project
  through its build project `_build/csharp/RadApp.csproj` (created when missing) under the RAD project's name, so
  other projects can reference it and `dotnet build` / Visual Studio build it with the solution. A RAD project with
  its own MSBuild project file adds that file. Other RAD languages have no MSBuild project: they stay in `.radsln`
  solutions (not supported in a VS solution).

### Tests (`samples/Tests/DotNet/SolutionManagement`)

* `test_solution_core.py` - 46 checks without the IDE on a copy of Contoso (console, class library, WinForms,
  xUnit in solution folders) + Fabrikam: byte-identical round trip, folders/items/nesting/dependencies (cycles
  refused), build order, configurations (new Staging, Tests not built, rename/remove, platforms), `.slnx` equal
  to `dotnet sln migrate`, `.slnx` round trip and `.slnx -> .sln -> .slnx`, `dotnet sln list` on both, merging
  (twice = no-op, into `.slnx`), `.sqlproj` type GUID, per-configuration properties / build events / usings /
  Directory.Build.props inheritance / multi-targeting round trip, `.snk` key validity, user secrets seen by
  `dotnet user-secrets list`, launch profile resolve, `dotnet build -c QA` (Tests skipped), signed multi-target
  build, run with the profile's args/env/cwd, `dotnet publish` with a `.pubxml` -> single-file exe that runs.
* `test_solution_ui.py` - 64 checks in the IDE (qh.py, offscreen): menus, New Solution Folder, drag & drop,
  rename, solution items, Configuration Manager, Project Dependencies, Add Projects from Solution, Unload/Reload,
  multiple startup + launch profile with **Ctrl+F5 and F5** (netcoredbg), Properties document (search, per
  configuration, usings, build event, inherited values, user secrets, .snk), Launch Profiles UI, Publish, RAD IDE
  C# project, Save As `.slnx` and editing it, New Solution from folders.

### Not done

* The Properties document covers SDK-style and old-style C#/VB/F# projects; `.vcxproj` keeps the existing simple
  dialog (C++ property pages are a separate topic). Resources/Settings open the files in the editor (no
  `.settings` grid designer; `.resx` uses the existing editor).
* Multiple startup projects: only one debugger session at a time (the others run without the debugger, as noted
  in the Output); "Start" of a library is skipped like VS.
* Launch profiles of kind IIS Express / Docker / WSL run as a plain Project profile.
* Publish targets other than Folder (Azure, FTP, IIS, ClickOnce) are not offered.
