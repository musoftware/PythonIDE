# RAD IDE samples

* `Hello*` - small first projects, one per language (they are also copied into the release).
* `Examples/<Language>/<Name>` - complete example programs that exercise what the IDE supports for each language.
  Open one with File > Open Project... or Help > Example Projects... (also on the Start Page), run it with F5 and
  make an exe with Build > Publish. Every example has a README.md (English + Arabic).
* `Tests/` - the automated tests and the test projects they use.

## Examples in compiled languages (C, C++, C#, Java, Go, Rust, Fortran)

The same six programs exist in several languages, with the same form layout, so they are easy to compare:

| Example | What it shows | C | C++ | C# | Java | Go | Rust | Fortran |
|---|---|---|---|---|---|---|---|---|
| Notepad | menus, Open / Save / Font dialogs, clipboard, find / replace, status bar, multi-line text | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Calculator | 24 buttons, keyboard input (KeyPress), error handling | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contacts | ListBox + details, add / edit / delete / search, a database file (TSV, SQLite via a Python module and RAD Hub, XML, CSV, JSON) | ✓ | ✓ (SQLite) | ✓ (XML) | ✓ (CSV) | ✓ (JSON) | ✓ | |
| SalesChart | a chart drawn with Panels, MouseDown with coordinates, Timer animation, TrackBar, ColorDialog, CSV | ✓ | | ✓ | | ✓ | | ✓ |
| StarCatcher | a game: Timer loop, KeyDown / KeyUp, MouseMove, collision, score, best score file | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ |
| SettingsDemo | three forms, a modal dialog (ShowDialog), settings saved to a file, Arabic (right-to-left) text | | ✓ | ✓ | ✓ | | | ✓ |
| WordStats | a console tool: arguments, file I/O, exit codes | ✓ | ✓ | | | ✓ | ✓ (cargo) | ✓ |

`VBNet/Calculator` is a Visual Studio-style VB.NET Windows Forms App (`.vbproj`, `Form1.Designer.vb` written by RAD
IDE's WinForms designer, `Handles` clauses) made with File > New Project > .NET and opened in place.

The forms are drawn by the IDE (GUI Bridge) while the code runs in the language's own compiler/runtime; Build >
Publish turns C, C++, Fortran, Go and Rust projects into small native exes (radforms, no Python), C# into a WinForms
exe and Java into a Swing exe with a trimmed runtime. `Tests/Examples/test_examples_compiled.py` opens, builds, runs,
publishes and starts every one of them (`Tests/Examples/results_compiled.md`).

## أمثلة اللغات المُترجَمة (C وC++ وC# وJava وGo وRust وFortran)

نفس البرامج الستة موجودة بعدة لغات وبنفس تصميم النماذج لتسهل المقارنة: المفكرة، الآلة الحاسبة، جهات الاتصال،
مخطط المبيعات، لعبة صائد النجوم، بطاقات التهنئة (عدة نماذج وحوار إعدادات ونص عربي)، وأداة كونسول لإحصاء الكلمات.
افتح أي مثال من ملف > فتح مشروع أو من مساعدة > أمثلة المشاريع، وشغّله بـ F5، واصنع ملف exe من البناء > النشر.
لكل مثال ملف README.md بالإنجليزية والعربية.

## Examples in scripting, web, game, assembly, DOS and retro languages

| Folder | Examples | What they show |
|---|---|---|
| `Python` (Tkinter) | Notepad, Calculator, Contacts, PaintChart, SettingsMultiForm, DataNotebook | menus + Open/Save/Font dialogs + clipboard + find; button grid + keyboard + a code module; Data Sources binding over SQLite (navigator, bound grid, validation, CSV); mouse drawing + Timer live chart; modal second form, JSON settings, English/Arabic RTL switch; a Jupyter notebook |
| `PythonQt` (PySide6) | TextEditor, Inventory, Dashboard | menus, dialogs, find/replace, RTL; SQLite grid + modal add/edit form; Timer, progress bars, QPainter charts, tabs |
| `PythonGames` | BreakoutGame (pygame), CoinCollector (arcade), CapitalsQuiz (Kivy), CrystalMaze3D (Ursina) | scene designer, keyboard, collisions, saved best score, phone-designer screens, 3D scene view |
| `PythonWeb` | FlaskGuestbook, DjangoLibrary, FastApiTasks | form + SQLite + list/delete, admin, ModelForm, REST API + fetch page, unit tests, Local folder publish profile |
| `Web` | CityGuideSite, SpaceDodgerHtml5 | static multi-page site with JS validation, localStorage and an Arabic RTL page; HTML5 canvas game from the scene designer |
| `JavaScript`, `TypeScript` | Notepad, Calculator, Contacts, FocusTimer; UnitConverter, TodoList, QuizGame | GUI Bridge forms on Node.js: menus, dialogs, ComboBox/grid, Timer, JSON / SQLite storage, a modal second form |
| `PHP`, `PHPWeb`, `NodeWeb` | Invoice, ContactsPDO, TextTools; Guestbook; QuickPoll | PHP forms (PDO SQLite), a PHP + SQLite site, an Express site with a JSON API |
| `Perl`, `Lua`, `Ruby`, `PowerShell`, `RubyWeb` | TextStats, ExpenseTracker, LogViewer; Calculator, GuessGame, Notes; Contacts, UnitConverter, Pomodoro; SystemInfo, FileOrganizer, PasswordGen; Guestbook (Sinatra) | regex tools, CSV/JSON storage, Timer, modal settings form, Arabic UI, CIM queries, code modules; Lua and simple PowerShell forms publish as tiny native exes |
| `Ring` | RingNotepad, RingContacts (RingQt), RingDataTool (console), RingGuestbook (web), RingPong (RingRayLib) | menus/toolbar/dialogs, SQLite + modal settings + Arabic, console statistics, HTTP form + JSON API, a game from the scene designer; ring2exe publish |
| `Dart`, `Flutter` | TipCalculator, WordScramble; TodoDesigner | Dart GUI Bridge forms with Timer/TrackBar; a Flutter visual-designer app with two screens, RTL and a widget test |
| `Godot`, `Mobile` | GemHunter2D; ShoppingListExpo | a 2D game designed in RAD IDE and exported to Godot 4; a React Native (Expo) app from the phone designer |
| `Assembly` | NasmCalculator, NasmBaseConverter, FasmTemperature, MasmTextTools, GasGuessNumber, Emu8086BubbleSort | assembly forms (GUI Bridge) and console tools for NASM, FASM, MASM (ml64), GNU as; a .COM program in the built-in 8086 emulator |
| `DOS` | QBasicArtMenu, PascalPhoneBook, CPixelPainter, AsmSysInfo, BatchToolbox, TuiOrderForm | QBasic (FreeBASIC), Pascal file I/O, C mode 13h painting, 16-bit asm .COM, batch menus, a text-mode form app from the TUI designer - run in DOSBox-X |
| `Retro` | Atari2600Runner, NesStarCatcher, GameBoyGarden, C64RasterScroller, ZxBorderArt | DASM, ca65, RGBDS, sjasmplus programs with original tiles/sprites, run in the IDE's emulators (Stella, Mesen, VICE) |

`Tests/Examples/test_examples_scripting.py` opens every one of these in the designer, builds it, runs it (the
program's own window and main interaction; HTTP requests for web stacks; emulator hooks for DOS/retro) and publishes
it with Build > Publish. The latest table is in `Tests/Examples/results.md`.

## أمثلة لغات السكربت والويب والألعاب والتجميع ودوس والأجهزة القديمة

برامج كاملة بلغات Python (Tkinter وQt)، وألعاب Python (pygame وarcade وKivy وUrsina)، ومواقع Flask وDjango
وFastAPI، ومواقع HTML ولعبة HTML5، وJavaScript وTypeScript وPHP وNode.js وPerl وLua وRuby (ومواقع Sinatra)
وPowerShell وRing وDart وFlutter وGodot وExpo، ولغات التجميع NASM وFASM وMASM وGNU as ومحاكي 8086، وبرامج دوس
(QBasic وPascal وC والتجميع وملفات الدفعات ونماذج الوضع النصي)، وألعاب أتاري 2600 ونينتندو NES وجيم بوي وكومودور 64
وZX Spectrum. تجدها في مساعدة > أمثلة المشاريع (وفي صفحة البداية) بعناوين عربية؛ افتح المثال وشغّله بـ F5 وانشره من
البناء > النشر. لكل مثال ملف README.md بالإنجليزية والعربية، ويختبرها جميعًا الملف
`Tests/Examples/test_examples_scripting.py`.
