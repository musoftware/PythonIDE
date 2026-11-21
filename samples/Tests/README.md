# Test projects

Projects that the IDE's own test runs created (agent rounds 2-5 and the fix/theme/audit rounds), copied here so the
experiments can be repeated. The folders below are the curated "front door": the best one or two projects per language
and feature. **Every** other test project is in [`All/`](All/INDEX.md) (de-duplicated, same cleaning).

Build output, `node_modules`, `.dart_tool`, `__pycache__`, run-time SQLite files, sessions, `.radide*` state and
binaries were removed; scratchpad paths were replaced by `<test folder>`. Open a folder (or its `.radsln`) with
File > Open Project.

## Languages - a form with controls and handlers

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Languages/PythonTk_Form`](Languages/PythonTk_Form/) | python-tk | Event handlers with event arguments: Button MouseMove(e.X, e.Y), TextBox KeyPress(e.KeyChar), FormClosing(e.Cancel), NumericUpDown/TrackBar ValueChanged; Multiline TextBox, ProgressBar, PictureBox, bold centred Label. | Open the folder, press F5, move the mouse over the button / type in the text box / change the number - the Output window prints `move`, `key`, `num`. |
| [`Languages/PythonQt_Form`](Languages/PythonQt_Form/) | python-qt (PySide6) | Two forms with a menu (File: Clear, Exit; Help: About), ListBox, TextBox, Labels, Close button; handlers recovered from a native exe by the importer. | Press F5, type a name, press Greet: the label shows `Hello, <name>!` and the name is added to the list. Help > About shows a MessageBox. |
| [`Languages/RingQt_Form`](Languages/RingQt_Form/) | ring-qt | Same event-argument test as PythonTk_Form, written in Ring (`func Button1_MouseMove e` ... `e.getx()`), plus a Helpers.ring module. | Press F5 (needs Ring in PATH or the IDE's Ring setup), move the mouse over the button / type - Output shows `move`, `key`, `num`. |
| [`Ring/RingIntelDemo`](Ring/RingIntelDemo/) | ring-app (Ring console) | Ring IntelliSense: completions for the whole Ring stdlib + extensions (RingLibCurl...) + RingQt, members of `new Point`, signature help, hover, F12 into shapes.ring and the Ring library, references, Document Outline, F1, Error List. Also `Ring/RingWebDemo` (RingHTTPLib web app), `Ring/RingLibDemo`, `Ring/RingWebLibDemo` (the new Ring templates). | Open main.ring, type `oP.` (Point members), F12 on QPushButton, F1 on substr; F5 runs. RingWebDemo: F5, open http://localhost:8080. |
| [`Languages/VB_Form`](Languages/VB_Form/) | vb-basic (VB6 dialect) | Two VB forms (.frm + .bas) with a menu, `MsgBox`, `.AddItem`, `Unload Me`, `Dim` declarations - VB code produced by the exe importer. | Press F5, type a name and press Greet. |
| [`Languages/JavaScript_Form`](Languages/JavaScript_Form/) | javascript (GUI Bridge) | A WinForms .NET program translated to a JavaScript RAD form: designer file + handlers in Form1.js. | Press F5 (Node.js needed). Click the buttons; compare with ExeImport/WinForms_DotNet/source/Form1.cs. |
| [`Languages/Cpp_Form`](Languages/Cpp_Form/) | cpp-bridge (GUI Bridge) | Form with two TextBoxes, Add/second Button, result Label and ListBox; `cmdAdd_Click` reads the numbers with `rad::get_num` and writes the sum with `rad::set` - also the C++ debugger (gdb) test project. | F5 (g++ / MinGW). Debug: breakpoint on line 13 of Form1.cpp (`int total = ...`), F5, type 2 and 3, press Add: it stops, Watch `a`, `b`. |
| [`Languages/Rust_Form`](Languages/Rust_Form/) | rust-bridge (GUI Bridge) | Same form in Rust (`get_num`, `set`), built with cargo - also the Rust debugger test project. | F5 (cargo). Debug: breakpoint on line 10 of Form1.rs (`let total = ...`). |
| [`Languages/Fortran_Form`](Languages/Fortran_Form/) | fortran-bridge (GUI Bridge) | Same form in Fortran (module form1_code, `rad_set`) - also the gfortran/gdb debugger test project. | F5 (gfortran). Debug: breakpoint on line 14 of Form1.f90 (`total = a + b`), Watch `a`, `b`. |
| [`Languages/TypeScript_Form`](Languages/TypeScript_Form/) | typescript (GUI Bridge) | Same form in TypeScript (`getNum`, `set`, typed RadEvent) - also the Node inspector debugger test project. | F5 (Node.js; TypeScript is compiled on run). Debug: breakpoint on line 14 of Form1.ts (`const total = ...`). |

## Solutions - References between languages

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Solutions/PyApp_CallsAllLanguages`](Solutions/PyApp_CallsAllLanguages/) | Solution: python-tk app + 19 libraries | One Python app references libraries written in C#, VB6, Ring, JavaScript, TypeScript, C, C++, Rust, Fortran, Perl, Dart, Java, PHP, PowerShell, Python, Python-Qt, Go, Lua and Ruby (Add Reference -> generated proxy modules CsLib.py, RustLib.py ...). | Open `QaSol.radsln`, press F5 (startup = App). `pymain.py` calls `Add`/`Greet` in every library through the RAD Hub. Go/Lua/Ruby need their toolchains (they failed in the original run because they were not installed yet). |
| [`Solutions/AllLanguages_CallPyLib`](Solutions/AllLanguages_CallPyLib/) | Solution: 15 apps -> 1 Python library | Reverse direction: an app in every GUI language (C#, VB6, Ring, JS, TS, PHP, Java, PowerShell, C, C++, Rust, Fortran, Perl, Dart, Python) references the same PyLib and calls PyLib.Add / PyLib.Greet. | Open `RevSol.radsln`, right-click an App_* project > Set as StartUp Project, F5. Each App_*'s module (CsCons.cs, CCons.c, ...) calls PyLib. |
| [`Solutions/CSharp_Java_PowerShell`](Solutions/CSharp_Java_PowerShell/) | Solution: C#, Java, PowerShell, Python | Apps and libraries in the .NET / JVM / PowerShell bridges referencing each other (CsApp -> JLib + PsLib + PyLib, JApp -> CsLib ..., PyApp -> all). | Open `Poly.radsln` (startup CsApp), F5. Switch the startup project to JApp / PsApp / PyApp to try the other directions. |
| [`Solutions/Js_Ts_Php`](Solutions/Js_Ts_Php/) | Solution: JavaScript, TypeScript, PHP, Python | JsApp/TsApp/PhpApp/PyApp call JsLib, TsLib, PhpLib and PyLib (Form1_Load prints J1..J6 / T.. / P..; a call with a wrong argument count must raise a readable error). | Open `RefSol.radsln` (startup PyApp: `check.py`), F5; set JsApp as startup and F5 to see the J1..J6 lines. (Empty Form1.form files were added: the test had created only the code files.) |
| [`Solutions/Python_Ring_VB`](Solutions/Python_Ring_VB/) | Solution: Python, Ring, VB6 | PyApp, RingApp and VBApp each reference PyLib, RingLib and VBLib (Add, Greet, Mul, Shout, Items, Sum, Twice). | Open `Sol.radsln` (startup PyApp), F5: Output prints `PY 5 Hello, Ali 42 ABC ...`. |
| [`Solutions/Perl_Dart`](Solutions/Perl_Dart/) | Solution: Perl, Dart, Python | PyApp, PerlApp and DartApp reference PerlLib, DartLib and PyLib (lists, dictionaries, strings across languages). | Open `Sol1.radsln`, F5 (Perl and Dart SDK needed). |
| [`Solutions/Native_C_Cpp`](Solutions/Native_C_Cpp/) | Solution: C, C++, Python | Native libraries (MathC in C, TextCpp in C++) called from Python, and native apps (CApp, CppApp) calling a Python library. | Open `NativeC.radsln` (startup PyApp), F5: prints ADD/GREET/TWICE/EVEN/SUM3/JOIN/SQ lines and a readable error for a bad call. Needs gcc/g++ (MinGW). |
| [`Solutions/Native_Rust`](Solutions/Native_Rust/) | Solution: Rust, Python | MathRs (Rust library, cargo) called from Python; RsApp (Rust) calling PyLib. | Open `NativeRust.radsln`, F5 (needs cargo). |
| [`Solutions/Native_Fortran`](Solutions/Native_Fortran/) | Solution: Fortran, Python | MathF (Fortran library) called from Python; FApp (Fortran) calling PyLib. | Open `NativeFortran.radsln`, F5 (needs gfortran). |
| [`Solutions/Desktop_And_Website`](Solutions/Desktop_And_Website/) | Solution: desktop app + web site | A python-tk app and a static web site in one solution (startup = Web). | Open `Mixed.radsln`: F5 runs the site in the dev server/preview; set App as startup to run the form. |

## Web sites

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Web/ShopSite_PhpSqlite`](Web/ShopSite_PhpSqlite/) | php-web + SQLite | Complete PHP data app: register/login (password_hash, throttling, CSRF), products CRUD, SQLite database (created on first request), Databases workspace entry, Publish profile. | Open, press F5 (PHP dev server + preview). Register, log in, add products. View > Databases shows `app`. Site > Publish: choose a destination folder for the `Local folder` profile (left empty on purpose). |
| [`Web/StaticBootstrapSite`](Web/StaticBootstrapSite/) | static-web | Bootstrap template from the App Gallery: 3 pages, CSS/JS assets, live reload. | Open, F5. Edit index.html - the preview reloads. Try Design/Split view. |
| [`Web/ExpressSite_Node`](Web/ExpressSite_Node/) | node-web (Express) | Node/Express site with a JSON notes API (data/notes.json) and static front end. | Open, F5 - the IDE runs `npm install` (node_modules was removed) and starts server.js. |
| [`Web/Django_Blog`](Web/Django_Blog/) | python-django (Django 5.2) | Blog: Post/Comment models, admin, class-based CRUD views (author only), comments, sign up / log in, search + pagination, 6 tests, `seed_blog` command; IntelliSense from the project (url names, templates, model lookups, template context), debugpy breakpoints. | Open, Ctrl+F5 (creates `.venv`, installs Django, migrates). View > Django > More > Run command... `seed_blog` (user demo / demo-pass-123). F5 + breakpoint in `blog/views.py`. See its README. |
| [`Web/Flask_Todo`](Web/Flask_Todo/) | python-flask (Flask 3) | Application factory, sqlite3 per request, todos blueprint (filter, add, toggle, edit, delete) + JSON API blueprint, flash messages, 3 tests. | Open, Ctrl+F5 (creates `.venv`). View > Flask: Endpoints, Run flask command... `init-db`, Run tests. F5 + breakpoint in `app/todos.py`. |
| [`Web/FastAPI_Items`](Web/FastAPI_Items/) | python-fastapi (FastAPI + SQLAlchemy 2) | CRUD API with Pydantic validation, SQLite through SQLAlchemy, lifespan seeding, a Jinja page using fetch(), /docs, 4 TestClient tests. | Open, Ctrl+F5 (creates `.venv`). View > FastAPI > Open /docs. F5 + breakpoint in `home()` of `app/main.py`. |
| [`Web/AspNet_App`](Web/AspNet_App/) | aspnet-web (ASP.NET Core MVC, .NET 9) | `dotnet new mvc` app: dotnet watch + Preview, netcoredbg debugging, Framework dock (routes, dotnet CLI / EF, tools), view/action IntelliSense. | Open, Ctrl+F5. F5 + breakpoint in `HomeController.Index`, open `/`. Site > Framework Tools. |
| [`Web/Spring_App`](Web/Spring_App/) | spring-web (Spring Boot 4.2 + Thymeleaf) | start.spring.io project + controllers, Thymeleaf layout/fragments, REST route; dev profile live templates, compile-on-save + devtools restart, JDWP debugging. | Open, Ctrl+F5 (first run downloads Maven + deps). F5 + breakpoint in `HomeController.products`, open `/products`. |
| [`Web/Rails_App`](Web/Rails_App/) | rails-web (Rails 8.1, Ruby 4.0) | `rails new` + scaffold Product; DevKit (MSYS2) + rails gem installed per user by the IDE; routes from `bin/rails routes`, generators panel, `*_path` IntelliSense. | Open, Ctrl+F5 (bundle install, db:prepare, rails server). Try `/products`. |
| [`Web/Sinatra_App`](Web/Sinatra_App/) | rails-web: Sinatra (pure Ruby) | Sinatra 4 + ERB views, form, JSON route - no C compiler needed. | Open, Ctrl+F5 (bundle install into vendor/bundle). |
| [`Web/NestJS_App`](Web/NestJS_App/) | nestjs-web (NestJS 11) | Module/controller/service + products resource; nest start --watch; F5 = ts-node + js-debug breakpoints in .ts; Nest CLI panel. | Open, Ctrl+F5 (npm install first). F5 + breakpoint in `products.controller.ts`, open `/products`. |
| [`Web/SeoReportsSite`](Web/SeoReportsSite/) | php-web: SEO Reports | A site with deliberate SEO / site-health problems: broken link (nope.php), missing stylesheet, image without alt, duplicate titles, two h1, heading skip, missing description, too-long title, missing h1/viewport/lang, PHP warning in the page (err.php), 301 redirect (old.php). | Open, F5, then Site > Reports (SEO): all the problems above are listed (19 issues in our run). |

## Mobile

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Mobile/Expo_ReactNative`](Mobile/Expo_ReactNative/) | React Native / Expo | Two screens (Main, Details) designed as .form files and generated as JSX, with app.json/package.json for Expo. | F5 runs `npm install` (node_modules removed) and Expo (web or Android). |
| [`Mobile/Flutter_Screens`](Mobile/Flutter_Screens/) | flutter | Three screens (Main, Details, About) with routes, AppBar, Drawer, BottomNav, ListView, TextField, Switch, Slider, FAB, and a Helpers.dart module. | Open, pick a device (Windows / Chrome / emulator) in the Device selector, F5 (`flutter run`). Save a change: hot reload. |
| [`Mobile/Flutter_TabsDrawer`](Mobile/Flutter_TabsDrawer/) | flutter | The Tabs + Drawer template: main screen with Drawer, BottomNav (3 tabs as Columns), Details screen. | F5 with a device selected; `flutter analyze`/`flutter test` passed in the original run. |
| [`Mobile/Flutter_PhoneDesigner`](Mobile/Flutter_PhoneDesigner/) | flutter (designer) | All 16 mobile control types on one phone form: AppBar, BottomNav, Card, ListView, Switch, Slider, TextField, Image, Icon, Drawer, TabBar, WebView, Column/Row/Stack, FAB. | Open the form: phone frame, device presets, Portrait/Landscape. (Only the .form - the IDE generates the Dart code when you run it.) |
| [`Mobile/Kivy_App`](Mobile/Kivy_App/) | kivy | A Kivy screen generated from a .form (KV + Python) with working handlers; buildozer.spec for Android. | F5 (pip install kivy). Build > APK needs buildozer (WSL/Linux). |

## Games

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Games/Ring_Platformer`](Games/Ring_Platformer/) | Ring game (radgame.ring) | Platformer template for Ring games, scene designer + Ring handlers. | F5 (Ring). |
| [`Games/Html5_Platformer`](Games/Html5_Platformer/) | HTML5 Canvas game | Platformer template running in the browser (radgame.js, scenes.js). | F5 opens it in the preview / browser. |
| [`Games/Arcade_Platformer`](Games/Arcade_Platformer/) | Python Arcade game | Platformer template for the `arcade` library. | F5 (pip install arcade). |
| [`Games/Pygame_Platformer`](Games/Pygame_Platformer/) | pygame | Two-level platformer made in the scene designer (Level1/Level2 .scene + handlers), radgame runtime. | Open Level1.scene in the scene designer, press Play/F5. Headless: `set SDL_VIDEODRIVER=dummy & set RADGAME_FRAMES=120 & python main.py`. |
| [`Games/Pygame_TopDown`](Games/Pygame_TopDown/) | pygame | Top-down template (Room1). | F5 / Play. |
| [`Games/Pygame_GodotExport`](Games/Pygame_GodotExport/) | pygame + Godot export | A pygame game plus its Godot export (project.godot, Level1.tscn, Level1.gd, radgame_scene.gd). | F5 runs the pygame version; open the folder in Godot 4 to run the exported version. |
| [`Games/Godot_Platformer`](Games/Godot_Platformer/) | godot | Native Godot platformer template (GDScript). | F5 (Godot 4 in PATH). Headless check: `godot --headless --editor --path . --quit` once (imports assets), then `godot --headless --path . --quit-after 120`. |

## Exe import

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`ExeImport/Native_Greeter`](ExeImport/Native_Greeter/) | Exe import: native Win32 (C) | DIALOGEX resource -> forms, menu, About dialog, handlers recovered from machine code (capstone), e.g. btnGreet_Click. | `build.bat` (MinGW) builds Greeter.exe; then File > Import > Program... (or `python ..\reimport.py Greeter.exe out`). `Imported_python-tk` is the project the import produced; F5 it. |
| [`ExeImport/Native_Adder`](ExeImport/Native_Adder/) | Exe import: native window built in code | CreateWindowEx controls (no resources) -> form; handler `int(first) + int(second)` recovered. | `build.bat`, then import Adder.exe. |
| [`ExeImport/WinForms_DotNet`](ExeImport/WinForms_DotNet/) | Exe import: .NET WinForms | ilspycmd decompiles the assembly; InitializeComponent -> .form; C# handlers translated to Python (100% of statements). | `build.bat` (dotnet 9 SDK) -> bin\WinHello.exe; import it. |
| [`ExeImport/PyInstaller_Tk`](ExeImport/PyInstaller_Tk/) | Exe import: PyInstaller | Archive extraction + the built-in bytecode decompiler (Python 3.11-3.13) rebuild tkhello.py; the Python importer turns it into a form. | `build.bat` (PyInstaller in the IDE's .venv) -> dist\TkHello.exe; import it. |
| [`ExeImport/Java_Swing`](ExeImport/Java_Swing/) | Exe import: Java jar | Vineflower decompiles the jar; Swing code -> form; the anonymous ActionListener -> btnGreet_Click. | `build.bat` (JDK) -> JavaHello.jar; import it. |

## Blend (states, storyboards, data binding)

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Blend/Blend_Tk_StatesStoryboards`](Blend/Blend_Tk_StatesStoryboards/) | python-tk: Blend | Visual States (MouseOver/Pressed/Focused/Disabled + custom form state `Big`), two Storyboards (Storyboard1 on click, `Intro` autostart) and data binding (people.json -> ListBox/Label/NumericUpDown, cities.csv -> ComboBox). | Open Form1: View > States / Objects and Timeline / Data panels. F5: hover Button1 (red), press it (storyboard moves it), Button2 toggles the `Big` state. |
| [`Blend/Blend_Qt_StatesStoryboards`](Blend/Blend_Qt_StatesStoryboards/) | python-qt: Blend | Same Blend form generated for python-qt (PySide6). | As above. |
| [`Blend/Blend_Tk_DataBinding`](Blend/Blend_Tk_DataBinding/) | python-tk: Blend | Data source products.json (root `items`) bound to a ListBox, and a `Slide` storyboard. | Open Form1 > Data panel shows the sample data at design time; F5. |

## AI

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`AI/AiGeneratedForm`](AI/AiGeneratedForm/) | python-tk: AI | LoginForm was generated by Project > Generate Form with AI (Ollama gemma4:e4b) during the ai-editor test; Form1 has AI-written handler code. | Open LoginForm in the designer. Try the designer's AI submenu / Ctrl+I in the code (an AI provider must be configured). |

## Debugger

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Debugger/Debug_PhpSite`](Debugger/Debug_PhpSite/) | php-web: debugger (Xdebug) | The PHP + SQLite data app used to test the web-site debugger (Xdebug through DAP). | Open, set a breakpoint in public/index.php, press F5 (Debug): the IDE starts PHP with Xdebug and stops on the request. The SQLite DB is created on the first request. |
| [`Debugger/Debug_PythonTk`](Debugger/Debug_PythonTk/) | python-tk: debugger | Breakpoints, Watch, Immediate eval, conditional breakpoints. | Open MainForm.py, set a breakpoint on line 9 (`print("load done", nX)`), F5: it stops; Watch `nX` = 42, Immediate `nX + 1`. Then put a breakpoint on line 14, Debug > Breakpoint Condition... `i == 5`, click Hello: it stops once with i = 5. |
| [`Debugger/Debug_RingQt`](Debugger/Debug_RingQt/) | ring-qt: debugger | Same as Debug_PythonTk in Ring. | Breakpoint on line 9 of MainForm.ring (`see "load done "...`), F5, Watch `nX`. Conditional: line 14, condition `i = 5`, click Hello. |

## Imaging - Icon Editor and project Resources

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Imaging/FormIconDemo`](Imaging/FormIconDemo/) | python-tk: Icon Editor, Form Icon, Resources | A 32x32 icon drawn pixel by pixel in the Icon Editor, all sizes generated (16-256) into one .ico, set as Form1.Icon and application/installer icon; Resources with a string, an image and the icon, generated `resources.py`. | F5: the window shows the icon in its title bar. Double-click Resources > AppIcon.ico to edit it; Project > Resources. |

## VB6 compatibility (real-world programs)

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`VB6Compat`](VB6Compat/) | VB6 opened in place / F5 / Migrate | Reproductions of the gaps found with 8 downloaded VB6 database programs: line continuation, `rs!Field`, Enums, ADO and DAO over Access `.mdb` (32-bit ADO helper), Data control + bound controls, MSFlexGrid / SSTab / DTPicker / ListView / TreeView / MonthView / Line in the designer and runtime, DataEnvironment + DataReport. | Open a `.vbp` in `VB6Compat/<Folder>` and press F5; expected output in [`VB6Compat/README.md`](VB6Compat/README.md). |

## Component packages (dynamic Toolbox controls)

| Folder | Language / feature | What it tests | How to try it |
|---|---|---|---|
| [`Components/StarRating`](Components/StarRating/) | Component package (docs/COMPONENTS.md) | A complete external control: manifest (custom-editor property, enum, color, padding, design-only text, events, methods), `designer.py` paint, inline Properties editor in `editors.py`, python-tk and python-qt runtimes, help, icon; `Components/StarRating.radcomp` to install it. | Tools > Component Packages > Install Component Package (.radcomp)... > `StarRating.radcomp`: the Toolbox gets "Rating & Input" > Star Rating. |
| [`Components/StarRating_PythonTk`](Components/StarRating_PythonTk/), [`Components/StarRating_PythonQt`](Components/StarRating_PythonQt/) | python-tk / python-qt | A form with two StarRatings (ValueChanged handlers, `Reset()` / `SetValue()` methods); the runtime copied into the project. | Install the package, open the folder, F5, click the stars and Reset. |
| [`Components/RatingBar`](Components/RatingBar/) and `Components/RatingBar_PythonTk`, `_PythonQt`, `_VB`, `_Ring`, `_JavaScript` | python-tk, python-qt, vb-basic, ring-qt, javascript (+ Flutter / web templates) | Code generation through the packages: one package with a runtime per target (VB6 and the bridge languages through the python-tk runtime), the same form in five languages. A target without a runtime gets a greyed Toolbox item, a red "no <target> runtime" strip in the designer, an Output warning and a placeholder in the generated code. | Open a project, F5, click the stars / Reset. |

## Not in the front door (yet)

- **GUI-Bridge forms with controls** exist in the test runs only for C++, Rust, Fortran and TypeScript (above); the C,
  C#, Dart and JavaScript ones were copies of `samples/HelloC`, `HelloCSharp`, `HelloDart`, `HelloJavaScript`. For Go,
  Lua, Ruby, Java, PHP, Perl and PowerShell the tests made only empty forms / libraries: each `App_*` in
  `Solutions/AllLanguages_CallPyLib` compiles, runs and calls a Python library, and `All/agents6/langs` has the
  Go/Lua/Ruby reference matrix.
- **Python app + C# library + VB6 library**: that is `samples/HelloSolution` (the test copies were identical to it).
- WordPress / Laravel gallery sites: only in `All/agents3/wgallery/projects` (Laravel without `vendor` - run
  `composer install`).
