# Native builds - published programs without Python

Build > Publish uses a *native builder* for the startup form's language when one exists
(`PublishConfig.prefer_native`, on by default; `radide/deploy/native/`). The program becomes a native exe with
**no Python inside**. When a builder cannot translate something (an unsupported control, a feature, a missing
tool), it reports the reasons in the Output window and the build falls back to the previous kind (VB runtime /
GUI Bridge), so a project always builds. Each language family has its own section below.

## .NET - C# and PowerShell (`dotnet_winforms.py`)

The `.form` files become real WinForms designer code (`RadForm_<Form>.InitializeComponent`, the same shape as a
Visual Studio `Form1.Designer.cs`). The project's own code is compiled **unchanged**: the GUI Bridge client API
(`lblOut.Text = "Hi"`, `MsgBox`, `InputBox`, `Show("Form2")`, `Set/Get/Call`, `End()`, `radcall`) is provided by a
thin runtime, `radide/deploy/native/dotnet/RadWinForms.cs`, which works on the controls directly. Handlers are
found exactly as in the IDE: static methods named `<Control>_<Event>` (optionally taking `RadEvent e`).
`radcall("Module.function", ...)` calls a public static method of the program itself (no RAD Hub).

### Publish options (C#) - `PublishConfig.dotnet_target`, Publish dialog "C# program"

| Option | What is published | Size of the test program* | The user's PC needs |
|---|---|---|---|
| `standalone` (default) | `dotnet publish` self-contained single file (`PublishSingleFile`, `SelfContained`, `IncludeNativeLibrariesForSelfExtract`, `EnableCompressionInSingleFile`, `InvariantGlobalization`, win-x64) | **62.8 MB**, one exe | nothing |
| `framework` | framework-dependent single-file apphost (net8.0-windows) | **199 KB** | .NET Desktop Runtime 8 |
| `netfx` | Roslyn `csc` against the .NET Framework 4.x assemblies of Windows (`/target:winexe`, C# latest syntax) | **49.5 KB** | nothing on Windows 10/11 (.NET Framework 4.8 is part of Windows) |

\* `samples/Tests/Native/CSharp/NativeCs`: two forms, menu, 11 controls, timer, a module.

Each option falls back to the others when it cannot be built: code that needs .NET 5+ APIs (ranges,
`System.Text.Json` ...) cannot be compiled for the .NET Framework, NuGet packages (`_build/csharp/RadApp.csproj`)
need the SDK, and without a .NET SDK only `netfx` is possible. The `netfx` compiler is the SDK's
`Roslyn/bincore/csc.dll`; without an SDK the IDE downloads the `Microsoft.Net.Compilers.Toolset` package (MIT) from
nuget.org into `%LOCALAPPDATA%\RADIDE\tools\roslyn` (its `tasks/net472/csc.exe` runs on the .NET Framework).

**Trimming** (`PublishTrimmed`) is *off*: WinForms is not trim-safe. It was tested (`trim=True`,
`_SuppressWinFormsTrimError`, `TrimMode=partial`): the exe shrinks to 41 MB but the program breaks (event handlers,
menus and the second form stop working: 5 of 13 UI checks passed), so it is not offered.

NativeAOT is not used: WinForms does not support it.

### PowerShell

The exe hosts a **Windows PowerShell 5.1** runspace (`System.Management.Automation` is part of Windows) on the UI
thread; the project's `.ps1` files are embedded as resources. The GUI Bridge client `Rad.ps1` is loaded unchanged
and only its `RadSend` / `RadAsk` are redirected (`dotnet/RadPsShim.ps1`) to the WinForms runtime
(`dotnet/RadPsHost.cs`), so `$lblOut.Text = "Hi"`, `RadShow Form2`, `MsgBox`, `radcall` work as in the IDE.
Events raised while a handler runs (Show -> Form2_Load) run as nested pipelines. Size of the test program: **64 KB**,
nothing to install. Trade-offs:

* Scripts are checked with the Windows PowerShell 5.1 parser at build time; PowerShell 7-only syntax (`??`,
  ternary, `#Requires -Version 7`) makes the build fall back to the GUI Bridge build.
* A pwsh 7 host would need the PowerShell SDK (~70 MB+ self-contained) - not worth it while 5.1 is in Windows.
  The alternative "tiny C# stub exe that starts `powershell.exe` with a WinForms .ps1" was not chosen: it shows the
  script source next to the exe, starts slower and the forms would have to be written in PowerShell.

### Control types: a data-driven table

`radide/deploy/native/dotnet/controls.json` maps each `.form` control type to a .NET type:

```json
"Button": {"type": "System.Windows.Forms.Button", "codegen": "Button"}
```

More maps are merged from `radide/deploy/native/dotnet/*.controls.json` and `<project>/dotnet.controls.json` (later
files win), so a control library adds its controls without editing the generator:

```json
{
  "controls": {
    "Ribbon": {"type": "RadIDE.Controls.Ribbon", "reference": "RadIDE.Controls", "container": true,
               "props": {"Text": "Text", "Theme": "Theme:enum:RadIDE.Controls.RibbonTheme", "Accent": "AccentColor:color"},
               "events": ["Click", "TabChanged"]}
  },
  "references": {"RadIDE.Controls": {"project": "../../../../controls/RadIDE.Controls/RadIDE.Controls.csproj",
                                     "dll": "../../../../controls/bin/RadIDE.Controls.dll"}}
}
```

* `codegen` names a built-in emitter (the IDE's standard controls). Entries without it get the generic emitter:
  `new T()`, Name / Location / Size / Font / colours / Anchor / Dock / Enabled / Visible / ToolTip, the mapped
  `props` (`"FormProp": "NetProp"`, `:enum:Type`, `:color`), `Register` by name and `Wire` for the listed `events`
  (any `EventHandler`-shaped event, found by reflection). `nonvisual: true` = a component (no Location / Size).
* `references`: the SDK builds add a `ProjectReference` (or a `Reference` to the dll) and the library is merged into
  the single file; the `netfx` build needs the prebuilt `dll` (copied next to the exe).
* `check()` accepts exactly the types of the merged table; the run-time property protocol (Text, Left, Enabled,
  BackColor ...) works on any `Control`.

### Not translated (falls back to the bridge build, with the reason)

TreeView, ListView, DataGridView, ToolStrip, ActiveX, ReportViewer, mobile controls, user controls and component
packages (until mapped in a `*.controls.json`), Visual States / storyboards / data bindings, `ScaleMode` other than
Pixel, forms in other languages, references to other projects (RAD Hub).

## Java (`java_native.py`)

The `.form` files become Swing code (`RadForm_<Form>.initComponents`); the project's classes compile unchanged
against `java/Rad.java` (same API as the bridge client: `lblOut.setText("Hi")`, `msgbox`, `show("Form2")`,
`radcall` to the program's own classes) on top of `java/RadSwing.java` (VB-style properties on Swing components,
Anchor / Dock layout from `radide/layout.py`, handlers found by reflection like `RadMain.java`). The bridge client's
`RadControl.java`, `RadEvent.java` and `RadJson.java` are used as they are.

Packaging - the smallest option that reliably runs Swing on Windows:

1. `jdeps --print-module-deps` - the modules the program needs (`java.base,java.desktop` for a form program;
   jars in `libs/` are included).
2. `jlink` - a private runtime with only those modules: `--strip-debug --no-header-files --no-man-pages
   --compress (zip-9 on JDK 21+) --strip-native-commands`; `lib/*.lib` and the UCRT forwarders that Windows 10/11
   already has are removed.
3. `jpackage --type app-image` - `<App>.exe` launcher (version resource, icon) + `app\` + `runtime\`.

Test program (`samples/Tests/Native/Java/NativeJava`): launcher **455 KB**, whole folder **39.1 MB** with JDK 17
(a JDK 25 runtime with the same modules is ~49 MB); nothing to install. The JDK is the one the IDE uses for Java
projects (`java_bridge.jdk_bin()`), then `%LOCALAPPDATA%\RADIDE\tools\jdk*`; it needs `jlink` + `jpackage` and
`jmods` (JDK 17-23) or a linkable run-time image (JDK 24+).

**GraalVM native-image** (Community, GPLv2+CE) was evaluated and not used: on Windows it requires the MSVC
toolchain (Visual Studio Build Tools - not open source, admin install), Swing/AWT needs reflection / JNI / resource
configuration from the tracing agent per program, and the exe still ships the AWT DLLs next to it (tens of MB in
total). The route for a future fully standalone single exe is GraalVM native-image + the C `radforms` runtime
through JNI / the FFM API instead of Swing; the Swing route stays the default.

FontDialog (no Swing equivalent) and the controls listed for .NET above fall back to the bridge build.

Test builds only: with `RADIDE_NATIVE_TEST_HOOK=1` at build time the exe also contains `RadTestHook` (commands on
stdin, results on stdout - Swing has no native child windows to drive with window messages). Release builds never
contain it (the test checks this).

## Licences of what the native .NET / Java builds put into a program

* .NET runtime (standalone C#): MIT (.NET Foundation). .NET Framework 4.8: part of Windows.
* Java runtime made by jlink: OpenJDK, GPL v2 with the Classpath Exception (programs may be distributed under any
  licence; keep the `runtime\legal` folder that jlink writes).
* No third-party source code is copied into RAD IDE for these builders (see THIRD_PARTY_NOTICES.md).

## C, C++ and Fortran (`win32_c.py`) - radforms

GUI Bridge projects in **C, C++ and Fortran** are compiled with MinGW-w64 (gcc / g++ / gfortran) into **one static
exe**: the forms are drawn by **radforms** (`radide/runtimes/native/radforms/`), a small C99 Win32 runtime that
implements the GUI Bridge client API (`radgui.h`, `radgui.hpp`, the `radgui` Fortran module) *in process*. The
project's code is compiled **unchanged** - `rad_set("lblOut", "Caption", "Hi")`, `rad::get(...)`,
`call rad_set(...)`, handlers `void cmdOk_Click(void)` / `subroutine cmdOk_Click()` - only the transport differs.

| Language | Example (`samples/Tests/Native/<Lang>/FormsDemo`, 2 forms, 20 controls, menu, timer) | exe size |
|---|---|---|
| C | `gcc -Os`, radforms.c + user .c + generated `_radnative_main.c` | **~80 KB** |
| C++ | `g++ -Os -static` (libstdc++ inside because the code uses `std::string` / `std::vector`) | ~260 KB |
| Fortran | `gfortran -Os -static`, native variant of `radgui.f90` (ISO_C_BINDING) | ~465 KB (static libgfortran) |

* **What goes into the exe** (`radforms_gen.write_resources`): the form description (RCDATA `RADFORMS`), the
  images the forms use (RCDATA), a manifest (Common Controls 6 visual styles, per-monitor-v2 DPI awareness,
  UTF-8 active code page, Windows 7-11 compatibility, asInvoker), the version resource (publisher, product,
  version from Publish) and the icon. MinGW's own `default-manifest.o` is replaced by an empty object found
  first through `-B`, so ours is the only manifest.
* **Standalone**: `-static` (libgcc, libstdc++, libgfortran, winpthread linked in), no `-fdata-sections` (on PE it
  moves zeroed statics from .bss into the file). The test checks the import table lists only Windows system
  DLLs: kernel32, user32, gdi32, comctl32, comdlg32, shell32, ole32 and the Universal CRT
  (`api-ms-win-crt-*` -> ucrtbase, part of Windows 10/11; Windows 7/8.1 get it from Windows Update KB2999226).
  gdiplus.dll, uxtheme.dll and dwmapi.dll are loaded at run time only when needed (images / anti-aliased
  drawing, dark themes).
* **Toolchain**: found like the C plugin finds it (PATH, `%LOCALAPPDATA%\RADIDE\toolchains\mingw64`, MSYS2,
  w64devkit ...). When missing, `win32_c.download_winlibs()` downloads the latest WinLibs UCRT zip from its
  official GitHub release (brechtsanders/winlibs_mingw), checks the SHA-256 GitHub publishes for the asset and
  unpacks it into `%LOCALAPPDATA%\RADIDE\toolchains\mingw64` (portable, no admin rights).
* **Console programs** (no form, a module with its own `main` / `program`) become plain console exes.
* **In-process RAD Hub**: `radcall("Helpers.multiply", ...)` / `rad::hub(...)` to a RADFUNC of the project's
  own C / C++ modules works (the generated main registers them with `rad_register`).
* **Falls back to the GUI Bridge build** (reasons in the Output window) when: a control type radforms does not
  draw (ListView, TreeView, DataGridView, DateTimePicker, ActiveX, ReportViewer, mobile / component-package
  controls without a radforms module), visual states / layout variants / data binding / control arrays /
  ToolStrip drop-downs, a form in another language, references to other projects or `radcall` to modules
  outside the project, a property or method used with a literal name that radforms does not implement
  (`radforms_gen.SUPPORTED_PROPS` / `SUPPORTED_METHODS`), or the compiler failing to appear.

Test: `.venv\Scripts\python samples/Tests/Native/test_native_c.py [scratch]` - publishes the three FormsDemo
projects with `build.build()`, checks kind / size / imports / no Python, starts each exe and drives it with Win32
messages (controls are found by the window property `radforms.name`, a global atom holding the control name),
then builds `libradforms.a` (+ `radforms.lib` with Visual Studio) and drives the handles-ABI demo.

### radforms - one C ABI for every language

`radforms.h` is a plain C header (no C++ in the API, no exceptions crossing it). Rules: cdecl, `int` / `double` /
UTF-8 `char*` (converted to UTF-16 inside) / opaque `rf_handle` / structs whose first member is `size` (they only
grow at the end); returned strings live in a ring of 16 buffers (copy what you keep); single-threaded (call it
from the thread that runs the loop). `RF_ABI_VERSION` (now 1) changes only on incompatible changes;
`rf_abi_version()` returns the linked library's. Every ABI function is marked `RF_API`.

**Machine-readable description**: `radide/runtimes/native/radforms/radforms_api.json` (generated from the header
by `radforms_gen.write_api_json()`; the test fails when it is stale) lists every function (name, return type,
parameters), the callback types, the structs and their fields, the constants (`RF_EV_*`, `RF_CLASS_*`,
`RF_ALIGN_*`, `RF_NONE`) and the control classes with their properties, events and methods - enough to
generate bindings (C#, Go, Rust, FreeBASIC, Java Panama, Lua ...).

Two API layers:

```c
/* 1. names - the GUI Bridge API (what the IDE's C / C++ / Fortran projects use) */
rad_set("lblOut", "Caption", "Hi");  const char *s = rad_get("Form2.txtName", "Text");
rad_call("lstLog", "AddItem", "line");  rad_show("Form2");  rad_show_modal("dlgOptions");  rad_end();
int r = rad_msgbox_ex("Save?", "Editor", 4 + 32);     /* vbYesNo + vbQuestion -> 6 = vbYes */

/* 2. handles + callbacks */
static int RF_CALL on_event(rf_handle h, int id, rf_event_args *a, void *user) {
    if (id == RF_EV_CLICK && strcmp(rf_name(h), "cmdOk") == 0) rf_prop_set(rf_find("lblOut"), "Text", "OK");
    if (id == RF_EV_FORMCLOSING) a->cancel = 1;           /* keep the form open */
    return 1;
}
int main(void) { return rf_run_events(on_event, NULL); }   /* forms from the exe's RADFORMS resource */
```

| Group | Functions |
|---|---|
| loop | `rad_run(dispatch)` (key "obj_event", what the IDE generates), `rf_run_events(fn, user)`, pull: `rad_next_event()` + `rad_done()`; `rad_handlers("a_Click,...")` limits which events are reported; `rf_set_event_handler` |
| forms | `rad_forms_load(text)` (a description in memory instead of the resource), `rad_show`, `rad_hide`, `rad_show_modal`, `rf_show(h, modal)`, `rf_quit` |
| objects | `rf_find("Form.Control")`, `rf_form`, `rf_name`, `rf_type`, `rf_hwnd`, `rf_state`, `rf_create(parent, type, name, x, y, w, h)`, `rf_destroy` |
| properties | `rf_prop_set / _set_num / _get / _get_num`, `rf_invoke(h, method, "a\tb")`; names = VB / WinForms names (Text, Caption, Left ... BackColor "#RRGGBB" or VB number, FontSize, Items "a;b", ListIndex, Checked, Value, Interval, Image, Theme on a form ...) |
| events | `RF_EV_CLICK` ... `RF_EV_FORMCLOSED` (fixed ids), `rf_event_id(name)` (custom names get ids >= 1000), `rf_event_name`, `rf_raise(h, "Expanded", args)`; `rf_event_args`: object, event, x, y, button, delta, key_code (VK), key_name, key_char (UTF-8), cancel |
| dialogs | `rad_msgbox(_ex)`, `rad_input(_ex)`; Open/Save/Color/Font/FolderBrowser dialogs as objects (`rf_invoke(dlg, "ShowDialog", "")` -> "OK"/"Cancel") |
| misc | `radcall` / `rad_register` (in-process functions), `rad_command` / `rad_event_line` / `rad_line_in` / `rad_line_out` (the GUI Bridge line protocol in process: a language host that speaks it only swaps its stdin/stdout calls - the Fortran module does exactly that) |

### Extension points (for the control suite and other languages)

**Control classes** - `rf_register_class(const rf_class *)` adds a class (or replaces one of the same name,
built-ins included); built-in classes are in the same registry (`rf_class_count` / `rf_class_at` /
`rf_find_class`, flag `RF_CLASS_BUILTIN`). A class sets only what it needs:

```c
typedef struct rf_class {
    int size; const char *name; unsigned flags;     /* RF_CLASS_CONTAINER | NONVISUAL | FOCUSABLE | OWNERDRAW */
    const char *win_class; unsigned long style, ex_style;      /* wrap an existing Win32 class (not owner-drawn) */
    int  (*create)(rf_handle, void **state);   void (*destroy)(rf_handle, void *state);
    int  (*set)(rf_handle, void *state, const char *prop, const char *value);   /* 1 = handled */
    const char *(*get)(rf_handle, void *state, const char *prop);               /* NULL = not handled */
    const char *(*invoke)(rf_handle, void *state, const char *method, const char *args);
    void (*paint)(rf_handle, void *state, const rf_paint *p);
    int  (*message)(rf_handle, void *state, unsigned msg, uintptr_t wp, intptr_t lp, intptr_t *result);
    const char *properties, *events, *methods;  /* comma lists (tools, radforms_api.json) */
} rf_class;
```

What a class leaves to the core: geometry / Anchor / Dock, Visible, Enabled, BackColor / ForeColor, fonts (DPI
scaled), Text, Tag and unknown properties (remembered), Tab focus, every mouse / key / focus event, and for
`RF_CLASS_OWNERDRAW` classes: a double-buffered window ("RadFormsCustom") already filled with the parent's
background, hot / pressed / focused state, **hover and press animation** (`rf_paint.hover`, `.press` go 0..1 over
`theme.anim_ms`), Click on mouse-up inside / Space, `WM_PRINTCLIENT` (PrintWindow, automation). Wrapped Win32
classes get their parent notifications (`WM_COMMAND` code, `WM_NOTIFY`) in `message()`. `rf_set_timer(h, id, ms)`
sends `WM_TIMER` to `message()`, `rf_invalidate(h)` repaints, `rf_raise` reports custom events.

**Modules**: one file per control family in `radforms/controls/`, with `RF_MODULE(name) { rf_register_class(...); }`
and a comment line `RF_CLASSES: Name1 Name2`. The IDE builder links only the modules whose classes the
project's forms use and generates `_radmodules.c` with `rad_modules_init()` (a weak symbol the core calls at
start-up; MSVC: `/alternatename`). Users of the static library call `rfmod_<name>()` themselves or
`rf_modules_register_all()`. Reference module: `controls/rf_buttonx.c` (ButtonX: Default / Accent / Outline /
Flat, rounded, animated) - it uses only the public ABI. A form uses a module class like any type
(`C ButtonX bx1` in the description); the IDE designer needs a component package for it (the suite's job).

**Themes**: `rf_theme` = colour table (window, window_text, face, face_text, border, hot, hot_border, pressed,
accent, accent_text, disabled_text, selection, selection_text, input, input_text - COLORREF 0x00BBGGRR), font,
metrics (radius, border_width, padding) and anim_ms. Built in: **Light** (system look for standard controls),
**Dark** (dark title bar via DWM, dark scroll bars / buttons / edits via uxtheme), **Office** (Office 2016 blue),
**Metro** (flat, square). `rf_theme_set(name)` (or the form property `Theme`) repaints everything; standard
controls follow it too (form / label / check box / edit / list colours); `rf_theme_define()` adds your own;
`rf_theme_color("accent")`.

**Drawing** (inside `paint`, device pixels): `rf_px(p, v96)` DPI scaling, `rf_blend(a, b, t)`,
`rf_draw_rect(p, x, y, w, h, fill, border, border_w, radius)` (anti-aliased rounded rectangles), `rf_draw_line`,
`rf_draw_text(p, utf8, x, y, w, h, color, RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS)`,
`rf_draw_image(p, path, ...)`; `p->hdc` is a normal GDI DC for anything else. Why **GDI + GDI+**: both are on
every Windows version, GDI+ has a flat C API that is loaded with `LoadLibrary` only when an image or a rounded
shape is drawn (no import, no size cost), it gives anti-aliasing, alpha and PNG / JPG decoding; text stays on
GDI `DrawTextW` (ClearType, correct Arabic shaping and right-to-left reading). Direct2D / DirectWrite would need
COM vtables in C, more code and the Windows 7 Platform Update for little gain at control sizes.

**DPI**: per-monitor v2 manifest; all geometry is in 96-DPI units and scaled with the window's DPI, fonts are
re-created and the form re-laid out on `WM_DPICHANGED`.

### Libraries for other languages

* `radforms_gen.build_static_lib(out, gcc)` -> **libradforms.a** (MinGW: core + all modules +
  `rf_modules_register_all`, ~120 KB archive; a program only pulls what it uses) + `radforms.h`.
  Link: `gcc app.c -lradforms -static -lcomctl32 -lcomdlg32 -lgdi32 -lole32 -luuid -lshell32 -mwindows`
  (+ `app.res.o` from `write_resources` for the manifest; or embed a manifest yourself).
* `radforms_gen.build_msvc_lib(out)` -> **radforms.lib** (cl /O1 /Gy /GS- **/Zl**: links with /MT or /MD, the
  system import libraries come from `#pragma comment(lib)`); for MSVC, Rust `*-msvc`, and .NET NativeAOT
  (`<DirectPInvoke Include="radforms" />` + `<NativeLibrary Include="radforms.lib" />`).
* Binding notes: C# `[DllImport("radforms", CallingConvention = Cdecl)]` with `byte*`/UTF-8 marshalling and an
  `[UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]` event callback; Go cgo `#cgo LDFLAGS:
  -lradforms -static ...` and an `//export`ed callback; Rust `extern "C"` + `-l static=radforms`; FreeBASIC
  `#inclib "radforms"` + `Declare Function ... Cdecl`; Java Panama (`Linker.nativeLinker()`, upcall stub for the
  callback) or JNI; Lua / QuickJS / mruby hosts call the C functions from their C glue (or speak the line protocol
  through `rad_command` / `rad_event_line`).

### Limits of radforms (today)

* Not drawn: ListView, TreeView, DataGridView, DateTimePicker, ReportViewer, ActiveX, mobile and package controls
  (they make the build fall back). ToolStrip has flat buttons only. Button background colours follow the
  visual style (use ButtonX for coloured buttons). Check box text colour in dark themes needs the classic look.
* Events raised while a handler runs (TextChanged after `rad_set Text`) are delivered after it, as in the GUI
  Bridge. Modal forms need the key or callback loop (pull loops show them modeless).
* RAD Hub calls to other languages / projects are not possible inside one exe.
* Fortran exes carry the static libgfortran runtime (~400 KB).

## VB6 (BASIC) (`vb6_freebasic.py`) - VB6 -> FreeBASIC -> Win32

"VB6 (BASIC)" projects are **translated to FreeBASIC** and compiled into **one small exe** (no Python, no VB
runtime DLL, imports Windows system DLLs only). Before, they were published as the IDE's VB interpreter frozen with
PyInstaller (`vbrun`, ~15 MB folder); that is still the fallback.

| Part | What it is |
|---|---|
| Translator | `radide/deploy/native/vb6fb/translate.py`: the IDE's own VB parser (`runtimes/vbparse.py`) -> one readable `.bas` (kept in `Publish\build\native_vb6\`). Static types: Integer/Long -> `Long` (like the interpreter, no 16-bit overflow), Double/Single/Currency, String (UTF-8), Boolean -> `VBBool` (-1/0), Date -> Double serial; Variant and undeclared variables -> `RVar` |
| Runtime (MIT) | `vb6fb/rt/vbrt_core.bi` (strings counted in characters, Variant, Format, dates, text files, Collection, Err), `vbrt_forms.bi` (forms on plain Win32), `vbrt_image.bi` (pictures through GDI+). Every routine is `Private`, so gcc drops what a program does not use |
| Forms | `vb6fb/forms.py`: every `.form` becomes a table (`VBDefForm` / `VBDef` / `VBDefMenu`); the runtime creates the windows the first time a form is needed (Load / Show / touching one of its controls). The translator only talks to the forms layer through `VBDef*`, `VBGetS/N`, `VBSetS/N`, methods (`VBAddItem` ...) and `VBOn` (events), so the layer can later be backed by another control library (e.g. radforms) without changing the translator |
| Compiler | FreeBASIC 1.10.1 for Windows, 32-bit (`fbc -s gui -gen gcc -O 2 -Wc -Os`); downloaded once from the official SourceForge page into `%LOCALAPPDATA%\RADIDE\tools\freebasic-win` (33 MB, SHA-256 + SHA-1 checked). `RADIDE_FBC_WIN` may point at another `fbc.exe` |
| Resources | comctl32 v6 manifest (visual styles), `dpiAware` (system DPI: the layout is scaled by DPI/96), version info, the Publish icon or the startup form's Icon (PNG converted), pictures embedded as RCDATA |

**Why FreeBASIC and plain Win32** (and not MyFbFramework, the framework behind VisualFBEditor): MyFbFramework is
LGPL with a static-link exception, so it could be used, but it is a large cross-platform framework (a 46 MB
repository, an OOP control layer) - a simple form app is several hundred KB with it, and the generated code would
depend on its object model. Plain Win32 code generated from a small runtime gives 60-150 KB exes and code that the
IDE fully controls (layout pixel for pixel, VB event semantics). FreeBASIC itself is the closest open-source
language to VB (same statements: `Select Case`, `Do ... Loop`, `Open ... For Input`, `Line Input #`, `ReDim
Preserve`, `Type`, `With`, `On x GoTo`, string functions).

**Sizes** (tested projects, `samples/Tests/Native/VB6/`): BASIC_Console 28 KB, BASIC_Form 58 KB, Debug_VB_Expand
60 KB, ArabicForm 65 KB, AnchorsDock 65 KB, MultiForm (2 forms + module) 66 KB, VB_Form 76 KB, HelloVB (menu,
timer, `Format`) 127 KB, ControlsGallery (every control, picture, `Format`) 151 KB. `Format()` alone adds about
60 KB.

### What is translated

* Types, `Dim` / `Static` / `Const` / `Enum` / `Type` (fixed arrays inside, `String * n` fields), `Option Explicit`
  (without it, undeclared variables are Variants), arrays (fixed, dynamic, multi-dimensional, `ReDim [Preserve]`,
  `Erase`, `LBound` / `UBound`, subscript checks -> error 9), `Split` into a String array, `Join`.
* `Sub` / `Function` with `ByRef` / `ByVal`, `Optional` (with defaults, `IsMissing`), named arguments, array
  parameters, recursion, `Exit Sub/Function/For/Do`, `Static` locals.
* **Class modules** (`.cls`): fields, `Sub` / `Function`, `Property Get / Let / Set`, `Class_Initialize`, `Me`,
  `New`, `Dim x As New C`, `Set`, `Nothing`, `Is`, objects in Collections / `For Each`, functions returning objects,
  `TypeName`. Calling a member of `Nothing` raises error 91.
* `If` (block / single line), `Select Case` (`Is`, `To`, lists; Variant subjects too), `For` (also with a Variant
  counter), `For Each` (arrays, Collections), `Do While/Until ... Loop [While/Until]`, `While ... Wend`, `With`
  (UDTs, controls, forms, objects), `GoTo`, labels / line numbers, `GoSub ... Return`, `On x GoTo`, `End`.
* Errors: `On Error GoTo label`, `On Error Resume Next`, `On Error GoTo 0`, `Resume Next`, `Resume label`, `Err`
  (`Number`, `Description`, `Source`, `Raise`, `Clear`), `Error n`, `Error(n)`. An error that no procedure handles
  shows the IDE's "Run-time error" box and the program goes on (like vbrun).
* Strings (Unicode / Arabic, counted in characters): `Len Left Right Mid` (+ `Mid() =`), `InStr InStrRev Replace
  Trim LTrim RTrim UCase LCase Space String StrReverse StrComp StrConv Chr ChrW Asc AscW Val Str CStr Hex Oct Like`,
  `Format` (the IDE's `vbformat.py` rules: named formats, `0 # , . % E+`, sections, dates, `@ & < > !`),
  `FormatNumber / Currency / Percent`.
* Numbers / conversions: `CInt CLng CByte CDbl CSng CCur CBool CDate CVar Int Fix Abs Sgn Sqr Exp Log Sin Cos Tan
  Atn Round Rnd Randomize IIf IsNumeric IsEmpty IsNull IsDate IsArray TypeName VarType RGB`.
* Dates: `Now Date Time Timer Year Month Day Hour Minute Second Weekday DateSerial TimeSerial DateAdd DateDiff
  DatePart DateValue TimeValue MonthName WeekdayName`, date literals `#3/15/2024#`.
* Files: `Open ... For Input/Output/Append`, `Print #` (zones, `;`, `Spc`, `Tab`), `Write #`, `Input #`,
  `Line Input #`, `Input(n, #f)`, `EOF LOF FreeFile Close Reset Kill Name MkDir RmDir ChDir CurDir FileCopy FileLen
  Dir`, Unicode file names; text is written as UTF-8, read as UTF-8 (or the ANSI code page).
* `Debug.Print` / `Print` (to stdout, like the IDE), `MsgBox` (all button / icon constants, return values),
  `InputBox`, `Collection` (`Add` key/before/after, `Item`, `Remove`, `Count`), `App.Path/Title/EXEName/Major/...`,
  `Screen.Width/Height/TwipsPerPixelX`, `Clipboard.SetText/GetText/Clear`, `Environ`, `Command`, `Shell`, `Beep`,
  `DoEvents`, `Sleep`. Relative paths are relative to the program folder (like the IDE).

### Forms coverage

| Control | Properties at run time | Events |
|---|---|---|
| Form | Caption, Left, Top, Width, Height (client size, like the designer), ScaleWidth/Height, Visible, Enabled, BackColor, WindowState, hWnd, Name, Tag; Show [vbModal], Hide, Load, Unload (QueryUnload / Unload Cancel), SetFocus, Move; `Caption = ...` without `Me` in a form module | Load, Activate, Deactivate, Resize, QueryUnload(Cancel, UnloadMode), Unload(Cancel), Terminate, Click, DblClick, MouseDown/Up/Move(Button, Shift, X, Y), KeyDown/Up(KeyCode, Shift), KeyPress(KeyAscii) |
| CommandButton (Button) | Caption, TextAlign, BackColor / ForeColor (owner-drawn when set) | Click + common |
| Label | Caption, Alignment, transparent on coloured containers | Click, DblClick, mouse |
| TextBox | Text, MultiLine, PasswordChar, Locked, MaxLength, SelStart, SelLength, SelText, Alignment | Change, KeyPress (KeyAscii ByRef: change it or set 0), KeyDown/Up, mouse, focus |
| CheckBox / OptionButton | Caption, Value (0/1/2, True/False); options are grouped per container (and per tab page) | Click (Value set from code fires it, like VB) |
| ListBox / ComboBox | AddItem [index], RemoveItem, Clear, List(i) get/set, ListCount, ListIndex, NewIndex, Text, Items; ComboBox styles DropDownList / DropDown / Simple | Click, DblClick, Change (ComboBox) |
| Frame (GroupBox), Panel | Caption, BackColor; children move / hide with the container | Click, mouse |
| PictureBox | Picture (embedded PNG/JPG/BMP/ICO, `LoadPicture`), centred like the IDE | Click, DblClick, mouse |
| ProgressBar, Slider (TrackBar), UpDown (NumericUpDown) | Value, Min, Max | Change |
| Timer | Interval, Enabled, Start / Stop | Timer |
| TabControl (SSTab) | Tab, Tabs, TabCaption(i); children on their page | Click(PreviousTab) |
| DateTimePicker | Value (Date), Year ... Second, Format (Short / Long / Time), Text | Change |
| LinkLabel | Caption, LinkColor (hand cursor) | Click |
| StatusBar | SimpleText / Caption | Click |
| Menus | Caption, Enabled, Checked; `&` access keys, `Text\tCtrl+S` shortcuts | Click |
| Common dialogs | ShowOpen, ShowSave, ShowColor, ShowFont, ShowFolder, ShowDialog; FileName, FileTitle, Filter, DialogTitle, InitDir, Color, FontName/Size/Bold/Italic, SelectedPath, CancelError (error 32755) | - |

Every visual control also has Left, Top, Width, Height, Visible, Enabled, BackColor, ForeColor, FontName /
FontSize / FontBold / FontItalic / FontUnderline (also `.Font.Bold` ...), ToolTipText, TabIndex, TabStop, Tag, Name,
Index, hWnd, SetFocus, Refresh, Move, ZOrder, and the common events Click / DblClick / MouseDown / MouseUp /
MouseMove / KeyDown / KeyUp / KeyPress / GotFocus / LostFocus. Control arrays (`ArrayName` / `ArrayIndex`) work with
`Name(i).Prop`, `Name.Count/LBound/UBound` and `Name_Event(Index As Integer, ...)`. `Form2.Text1.Text` loads Form2
like VB. Layout: creation in TabIndex order (Tab key order), Anchor / Dock with the designer's rules
(`radide/layout.py`) when the form or a container is resized, FormBorderStyle Sizable / FixedSingle,
StartPosition, TopMost, WindowState Maximized, Icon, ScaleMode Twip, RTL reading order for Arabic / Hebrew texts.

### Falls back to vbrun (with "file(line): reason" in the Output)

TreeView, ListView, DataGridView, ToolStrip, ActiveX, ReportViewer, component-package and user controls, mobile
controls; animations / storyboards / visual states / data sources / layout variants in a form; `Declare` (Win32
API), `Event` / `RaiseEvent` / `WithEvents`, `Implements`, default members, `Class_Terminate` with code, Property
Get with parameters, `CreateObject` / COM / `Scripting.FileSystemObject`, Variants holding arrays (`Array()`,
`v = Split(...)`), whole-array assignment, `Open ... For Binary/Random`, `Get` / `Put` / `Seek`, `On x GoSub`,
`Resume` (retry), `Choose` / `Switch`, registry settings, `SendKeys`, the event MouseEnter / MouseLeave / Validate
/ Scroll, `Form.Controls`, multi-language projects / RadCall, and Publish's update check.

Known differences to the IDE's runtime: `Rnd` is VB's generator (repeatable without `Randomize`), not Python's;
`Long` arithmetic is 32-bit (multiplication uses 64 bits; the interpreter has no limit); text files are UTF-8.

### Tests

* `samples/Tests/Native/VB6/translator/test_translator.py` - 33 VB snippets (arithmetic, strings, Unicode,
  Variants, arrays, UDTs, classes, errors / Resume Next, GoSub, Format, dates, files, Collection ...) run in the
  IDE's interpreter and as one native exe; the outputs must be identical.
* `samples/Tests/Native/VB6/test_native_vb6.py` - publishes every project with `radide.deploy.build.build()`,
  checks one exe without Python that imports system DLLs only, replays the same clicks / typing on the exe (window
  messages) and on vbrun (`vbrun_driver.py`) and compares `Debug.Print` output and texts, drives events with
  arguments (KeyPress, MouseDown, DblClick, Change, Tab Click, QueryUnload Cancel), compares the rectangle of every
  control (GetWindowRect at 96 DPI) with the `.form` geometry and the designer (offscreen `DesignerView`), saves
  designer / exe pictures (PrintWindow of the exe's window only) to `_last_report/`, and checks the fallback
  reasons of untranslatable projects. `make_projects.py` writes the projects made in code.

## Rust, Go and Lua (`rust_native.py`, `go_native.py`, `script_embed.py`) - radforms through FFI

In the GUI Bridge design a Rust / Go / Lua program only speaks the bridge line protocol on stdin/stdout and the
IDE's Python/Tk host (`radide/runtimes/bridge.py`) draws the forms - so the `_build\debug\radapp.exe` (Rust) or
`_radapp.exe` (Go) of a normal build shows nothing when it is double-clicked. These builders make **one
standalone exe with the forms inside** (no IDE, no Python, only Windows system DLLs + the UCRT): the project's
code is compiled **unchanged** against a native variant of the language's client whose I/O layer calls radforms
in process, and radforms is linked statically with only the control modules the forms use (`_ffi.py`:
`libradforms.a` + `_radmodules.o` for MinGW, `radforms.lib` (cl /Zl) + `_radmodules.obj` for MSVC; resources by
windres - COFF object for MinGW, `.res` for link.exe).

**Where:** Build > **Build Native Exe** (only the program, into `<project>\Publish\build\dist\<name>\`; no
installer) and Build > Publish (Automatic). After a normal Build Project of a GUI Bridge application the Output
says that its exe needs the IDE (F5) and points to Build Native Exe; the Rust / Go bridge clients print the same
hint in their console when they are started without the IDE.

| Language | Native client | Toolchain | Size (FormsDemo) |
|---|---|---|---|
| Rust (`rust-bridge`) | `radgui.rs` with protocol / GUI / RAD Hub sections replaced by `unsafe extern "C"` calls (`rad_set`, `rad_get`, `rad_next_event` + `rad_obj`/`rad_ev`/`rad_args` ...); JSON + worker sections kept; generated main adds `#![windows_subsystem = "windows"]` and `native_handlers(...)` | cargo (found like the Rust plugin). **x86_64-pc-windows-msvc** when Visual C++ is installed: radforms.lib, link.exe, `+crt-static` (no VCRUNTIME, not even UCRT imports), `/MANIFEST:NO`. Otherwise **x86_64-pc-windows-gnu** (when rustup has it, or `rustup target add` - user-level, no admin): libradforms.a, the IDE's MinGW gcc as linker. `cargo build --release`, profile `opt-level="z"`, `lto=true`, `codegen-units=1`, `panic="abort"`, `strip=true` | 360 KB msvc, 336 KB gnu; RustApp1 (one button) 300 KB |
| Go (`go-bridge`) | `radlib.go` variant using cgo (`C.rad_set` ..., `runtime.LockOSThread()` in `init`, pull event loop) | Go (PATH / `toolchains\go`), cgo with the IDE's MinGW gcc (`toolchains\mingw64`); `go build -trimpath -ldflags "-s -w -H windowsgui -extldflags '-static ... _radmodules.o app.res.o'"`; libraries through `CGO_LDFLAGS` (quoted: paths with spaces work) | 1.75 MB (the Go runtime) |
| Lua (`lua-bridge`) | C host (`_radluahost.c`) + `rad.lua` with a native block (rad.set / get / call / msgbox / input / show / hide / quit / load_file / run backed by C functions; JSON, `ui.<control>` sugar and handler lookup unchanged) | **Lua 5.4.9** (MIT) compiled from the official tarball `https://www.lua.org/ftp/lua-5.4.9.tar.gz` (SHA-256 `2335b6c5...b8e6` checked, downloaded once into `%LOCALAPPDATA%\RADIDE\toolchains\lua-src`, `liblua.a` cached per gcc); MinGW gcc `-Os`, static. The project's `.lua` files (+ pure-Lua rocks in `lua_modules`) are embedded as RCDATA `RADLUA` and found by a `package.searchers` entry; `print` goes to OutputDebugString; a script error shows a message box | 296 KB |

The crate / package is a **copy** in `<Publish>\build\native_rust|native_go` (the project folder is never
written): Rust keeps the project's `[package]` and `[dependencies]` (Cargo.lock copied), replaces `[[bin]]` /
`[profile]`, adds `build = "_radbuild.rs"` (link search, `static=radforms`, the resource and `_radmodules`
objects through `rustc-link-arg-bins`); Go copies `go.mod` / `go.sum` / `vendor`. Cargo's target folder is kept
between builds (a rebuild takes seconds).

**Falls back to the bridge build** (reasons in the Output): `radcall` / references to other projects (RAD Hub),
properties / methods radforms does not implement used with literal names (`set("x", "Blink", ..)`,
`Set(...)`, `rad.set(...)`), unsupported controls (as for C), no forms (console programs), a project `build.rs`
(Rust) or its own cgo (Go), Lua `require` of something that is not a Lua file of the project (C modules / DLL
rocks such as LuaSocket), cargo / Go missing.

**Not done (they stay on the bridge build):** JavaScript / TypeScript with QuickJS and Ruby with mruby - their
bridge clients (`radgui.js`, `rad.rb`) are written against Node / CRuby (process, child_process, sockets,
net/http, JSON gems), so embedding the small engines needs a port of the clients and of the users' expectations
(npm / gems would not work); Perl and PHP are too big to embed small. A host that speaks the bridge line protocol
can use `rad_line_out` / `rad_line_in` (the Fortran builder does) - that is the way for these later.

**Tests:** `samples/Tests/Native/test_native_rust_go_lua.py` (FormsDemo per language in `Rust/`, `Go/`, `Lua/`:
publish, kind native, one exe, size, imports, project folder unchanged, drive with `winauto.py`: text change,
button click, list, timer, combo, check / radio, second form writing back, message box, Arabic text, menu; a new
RustApp1-like project; the GNU Rust target; check() fallbacks; `RAD_TEST_USER_RUST=<folder>` also tests a copy
of that project) and `test_build_native_ui.py` (offscreen IDE: Build > Build Native Exe, the build note, Arabic).