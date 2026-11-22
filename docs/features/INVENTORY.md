# RAD IDE feature inventory

Generated 2026-11-22 17:58 by `tools/feature_inventory.py` from a running IDE (offscreen) - do not edit. Traceability to tests: [TEST_MATRIX.md](TEST_MATRIX.md).

**1297** distinct entry points (menu / tool bar / palette / context-menu items), **51** docks / tool windows, **93** keyboard shortcuts, **137** dialog classes, **63** New Project languages with **229** templates, **10** Options pages.

Contexts (a sandbox copy of each project, opened in every layout VS / VS Code / Agent):

* `none` - no project open (Start Page)
* `python-tk` - Python Tk form project (language `python-tk`)
* `vb6` - VB6 (vb-basic) form project (language `vb-basic`)
* `csharp` - C# form project (language `csharp-bridge`)
* `web` - static web site (language `static-web`)
* `flask` - Python Flask web project (project actions provider) (language `python-flask`)
* `flutter` - Flutter mobile project (language `flutter`)
* `retro` - retro console (NES) project (language `retro-nes`)
* `dos` - DOS QBasic text-mode project (language `dos-qbasic`)
* `game` - pygame scene-designer game (language `pygame`)
* `asm` - NASM assembly form project (language `asm-nasm`)
* `firmware` - firmware ECU project (created by the firmware-ecu plugin) (language `firmware-ecu`)

## Entry points per area

| Area | Entries |
|---|---|
| Analyze | 11 |
| BASIC | 5 |
| Build | 17 |
| Command Palette | 126 |
| Context menu: Databases (QTreeWidget) | 20 |
| Context menu: Designer | 97 |
| Context menu: Editor tab | 3 |
| Context menu: Flask (QTreeWidget) | 3 |
| Context menu: Game Assets (_AssetTree) | 1 |
| Context menu: HexView (HexView) | 6 |
| Context menu: Requests (QTreeWidget) | 4 |
| Context menu: Solution Explorer | 183 |
| Context menu: Toolbox (Toolbox) | 5 |
| Data | 4 |
| Debug | 42 |
| Edit | 36 |
| File | 49 |
| Flask | 6 |
| Flutter | 18 |
| Format | 25 |
| Game | 11 |
| Git | 31 |
| Help | 58 |
| Menu bar corner | 3 |
| Project | 105 |
| Python | 13 |
| Share | 8 |
| Site | 37 |
| Test | 9 |
| Toolbar Activity Bar | 19 |
| Toolbar Debug | 4 |
| Toolbar Expo | 5 |
| Toolbar Firmware | 17 |
| Toolbar Mobile | 5 |
| Toolbar Project Actions | 7 |
| Toolbar Retro Emulator | 2 |
| Toolbar Rust | 5 |
| Toolbar Solution Configurations | 2 |
| Toolbar Standard | 9 |
| Toolbar Toolbar | 55 |
| Tools | 154 |
| View | 66 |
| Window | 5 |
| pygame | 6 |

## Analyze

| Item | Shortcut | Where |
|---|---|---|
| Code Cleanup > Configure Code Cleanup |  | all contexts |
| Code Cleanup > Run Code Cleanup on Document | Ctrl+K, Ctrl+E | all contexts |
| Code Cleanup > Run Code Cleanup on Project |  | all contexts |
| Code Cleanup > Run Code Cleanup on Solution |  | all contexts |
| Run Code Analysis > On Current Project |  | all contexts |
| Run Code Analysis > On Solution | Alt+F11 | all contexts |
| Configure Code Analysis (.editorconfig) |  | all contexts |
| Decompile Assembly |  | all contexts |
| Go To Decompiled Definition |  | all contexts |
| Remove and Sort Usings | Ctrl+R, Ctrl+G | all contexts |
| Show Generated Files (Source Generators) |  | all contexts |

## BASIC

| Item | Shortcut | Where |
|---|---|---|
| Add Form |  | vb6 |
| Build EXE (Publish) |  | vb6 |
| Project Properties |  | vb6 |
| Run (F5) |  | vb6 |
| Stop Running Command |  | vb6 |

## Build

| Item | Shortcut | Where |
|---|---|---|
| Mobile App > Android APK |  | all contexts |
| Mobile App > Android APK (debug, faster) |  | all contexts |
| Mobile App > Android App Bundle (Google Play) |  | all contexts |
| Mobile App > Cancel Build |  | all contexts |
| Mobile App > Create Foldable Emulator |  | all contexts |
| Mobile App > Web site |  | all contexts |
| Mobile App > Windows EXE |  | all contexts |
| Build Native Exe |  | all contexts |
| Build Project |  | all contexts |
| Build Solution | Ctrl+Shift+B | all contexts |
| Clean Solution |  | all contexts |
| Configuration Manager |  | all contexts |
| Open Publish Folder |  | all contexts |
| Publish / Create Installer | Ctrl+Alt+F5 | all contexts |
| Publish Selection |  | all contexts |
| Rebuild Solution |  | all contexts |
| Refresh References |  | all contexts |

## Command Palette

| Item | Shortcut | Where |
|---|---|---|
| AI > Agent Manager: New Task (`agents.new`) |  | all contexts |
| AI > Agent Manager: Show (`agents.show`) |  | all contexts |
| AI > Agent Manager: Stop All Tasks (`agents.stop_all`) |  | all contexts |
| BASIC > Add Form (`projact.basic.add-form`) |  | vb6 |
| BASIC > Build EXE (Publish) (`projact.basic.build-exe`) |  | vb6 |
| BASIC > Project Properties (`projact.basic.properties`) |  | vb6 |
| BASIC > Run (F5) (`projact.basic.run`) |  | vb6 |
| Build > Build: Build Native Exe (`build.native`) |  | all contexts |
| Build > Build: Publish / Create Installer... (`build.publish`) |  | all contexts |
| Claude Code for VS Code > Accept this change (`claude-vscode.acceptProposedHunkFromBar`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Accept Change at Cursor (`claude-vscode.acceptProposedHunk`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-code.acceptProposedDiff`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-vscode.acceptProposedDiff`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Add Session Tab to Group (`claude-vscode.addSessionTabToGroup`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Add to Chat (`claude-vscode.addToChat`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Blur input (`claude-vscode.blur`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Focus input (`claude-vscode.focus`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Focus last message (`claude-vscode.focusLastMessage`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Insert @-Mention Reference (`claude-vscode.insertAtMention`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Insert At-Mentioned (`claude-code.insertAtMentioned`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Install Plugin (`claude-vscode.installPlugin`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Logout (`claude-vscode.logout`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Mark Session as Unread (`claude-vscode.markSessionUnread`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: New Conversation (`claude-vscode.newConversation`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open Walkthrough (`claude-vscode.openWalkthrough`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open in New Tab (`claude-vscode.editor.open`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open in New Window (`claude-vscode.window.open`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open in Primary Editor (`claude-vscode.primaryEditor.open`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open in Side Bar (`claude-vscode.sidebar.open`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open in Terminal (`claude-vscode.terminal.open`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Open (`claude-vscode.editor.openLast`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Reject Change at Cursor (`claude-vscode.rejectProposedHunk`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-code.rejectProposedDiff`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-vscode.rejectProposedDiff`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Rename Session Tab (`claude-vscode.renameSessionTab`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Reopen Closed Session (`claude-vscode.reopenClosedSession`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Show Logs (`claude-vscode.showLogs`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Toggle Focus view (`claude-vscode.toggleFocusView`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Claude Code: Update extension (`claude-vscode.update`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Claude Code for VS Code > Reject this change (`claude-vscode.rejectProposedHunkFromBar`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| CodeIgniter > CodeIgniter: Show Routes (`codeigniter.routes`) |  | all contexts |
| CodeIgniter > CodeIgniter: Spark Commands (`codeigniter.spark`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark db:seed... (`codeigniter.db:seed`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:controller... (`codeigniter.make:controller`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:migration... (`codeigniter.make:migration`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:model... (`codeigniter.make:model`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark migrate... (`codeigniter.migrate`) |  | all contexts |
| Debug > Debug with Extension Debugger (`vsx.debugWithExtension`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Extensions > Extensions: Check for Extension Updates (`vsx.checkUpdates`) |  | all contexts |
| Extensions > Extensions: Install from VSIX... (`vsx.installVsix`) |  | all contexts |
| Extensions > Extensions: Show Extensions (`vsx.show`) | Ctrl+Shift+X | all contexts |
| Extensions > Extensions: Update All Extensions (`vsx.updateAll`) |  | all contexts |
| Extensions > New Extension Terminal from Profile... (`vsx.newTerminalProfile`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Extensions > Open Extension URI... (`vsx.openUri`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Extensions > Restart Extension Host (`vsx.restartExtensionHost`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Extensions > Show Extension Output (`vsx.showExtensionOutput`) |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Flask > Flask Shell (`projact.flask.shell`) |  | flask |
| Flask > New Blueprint (`projact.flask.new-blueprint`) |  | flask |
| Flask > Routes (`projact.flask.routes`) |  | flask |
| Flask > Run Server (`projact.flask.run`) |  | flask |
| Flask > Run flask Command (`projact.flask.command`) |  | flask |
| Flutter > Analyze (flutter analyze) (`projact.flutter.analyze`) |  | flutter |
| Flutter > Build: Build APK (Android) (`projact.flutter.build-apk`) |  | flutter |
| Flutter > Build: Build App Bundle (Google Play) (`projact.flutter.build-appbundle`) |  | flutter |
| Flutter > Build: Build Web (`projact.flutter.build-web`) |  | flutter |
| Flutter > Build: Build Windows (`projact.flutter.build-windows`) |  | flutter |
| Flutter > Clean (flutter clean) (`projact.flutter.clean`) |  | flutter |
| Flutter > Flutter Doctor (`projact.flutter.doctor`) |  | flutter |
| Flutter > Format Code (dart format) (`projact.flutter.format`) |  | flutter |
| Flutter > List Devices (`projact.flutter.devices`) |  | flutter |
| Flutter > New Screen (Form) (`projact.flutter.new-screen`) |  | flutter |
| Flutter > New Widget (`projact.flutter.new-widget`) |  | flutter |
| Flutter > Packages: Add Package (pub add) (`projact.flutter.pub-add`) |  | flutter |
| Flutter > Packages: pub get (`projact.flutter.pub-get`) |  | flutter |
| Flutter > Packages: pub outdated (`projact.flutter.pub-outdated`) |  | flutter |
| Flutter > Packages: pub upgrade (`projact.flutter.pub-upgrade`) |  | flutter |
| Flutter > Run (flutter run) (`projact.flutter.run`) |  | flutter |
| Flutter > Run Tests (flutter test) (`projact.flutter.test`) |  | flutter |
| Go > Go to Line/Column... (`workbench.gotoLine`) |  | all contexts |
| Laravel > Laravel: Generate IDE Helper Files (`laravel.ide-helper`) |  | all contexts |
| Laravel > Laravel: Open Tinker (`laravel.tinker`) |  | all contexts |
| Laravel > Laravel: Run Artisan Command... (`laravel.artisan`) |  | all contexts |
| Laravel > Laravel: Show Routes (`laravel.routes`) |  | all contexts |
| Laravel > Laravel: make:model -mcr (`laravel.make-model`) |  | all contexts |
| Preferences > Color Theme: Blue (`workbench.theme.Blue`) |  | all contexts |
| Preferences > Color Theme: Dark (`workbench.theme.Dark`) |  | all contexts |
| Preferences > Color Theme: High Contrast (`workbench.theme.High Contrast`) |  | all contexts |
| Preferences > Color Theme: Light (`workbench.theme.Light`) |  | all contexts |
| Preferences > Color Theme: System (`workbench.theme.System`) |  | all contexts |
| Preferences > File Icon Theme... (`workbench.action.selectIconTheme`) |  | all contexts |
| Project > Flutter: Add Google Font... (`flutter.fonts`) |  | all contexts |
| Project > Flutter: Add New Screen (visual designer)... (`flutter.newScreen`) |  | all contexts |
| Project > Flutter: App Theme... (`flutter.theme`) |  | all contexts |
| Project > Flutter: Import Screen from Dart... (`flutter.importScreen`) |  | all contexts |
| Project > Flutter: Project Assets... (`flutter.assets`) |  | all contexts |
| Project > Project: Add Report... (`reports.add`) |  | all contexts |
| Python > Build EXE / Installer (`projact.python.publish`) |  | flask, game, python-tk |
| Python > Create .venv (`projact.python.venv-create`) |  | flask, game, python-tk |
| Python > Format and Lint: Fix Lint Problems (ruff check --fix) (`projact.python.ruff-fix`) |  | flask, game, python-tk |
| Python > Format and Lint: Format Project (black) (`projact.python.black`) |  | flask, game, python-tk |
| Python > Format and Lint: Format Project (ruff) (`projact.python.ruff-format`) |  | flask, game, python-tk |
| Python > Format and Lint: Lint Project (ruff check) (`projact.python.ruff-check`) |  | flask, game, python-tk |
| Python > Freeze to requirements.txt (`projact.python.pip-freeze`) |  | flask, game, python-tk |
| Python > Install Package (`projact.python.pip-install`) |  | flask, game, python-tk |
| Python > Install Requirements (`projact.python.pip-install-r`) |  | flask |
| Python > List Installed Packages (`projact.python.pip-list`) |  | flask, game, python-tk |
| Python > Run Tests (pytest) (`projact.python.pytest`) |  | flask, game, python-tk |
| Python > Run Tests (unittest) (`projact.python.unittest`) |  | flask, game, python-tk |
| Rails > Rails: Edit Credentials (`rails.credentials`) |  | all contexts |
| Rails > Rails: Open Console (`rails.console`) |  | all contexts |
| Rails > Rails: Show Models (`rails.models`) |  | all contexts |
| Rails > Rails: Show Routes (`rails.routes`) |  | all contexts |
| View > Focus Active Editor (`workbench.focusEditor`) |  | all contexts |
| View > Show AI Chat (`workbench.view.chat`) |  | all contexts |
| View > Show AI Web Chats (`workbench.view.webchats`) |  | all contexts |
| View > Show Agents (`workbench.view.agents`) |  | all contexts |
| View > Show Databases (`workbench.view.databases`) |  | all contexts |
| View > Show Explorer (`workbench.view.explorer`) |  | all contexts |
| View > Show Run and Debug (`workbench.view.run`) |  | all contexts |
| View > Show Search (`workbench.view.search`) |  | all contexts |
| View > Show Source Control (`workbench.view.scm`) |  | all contexts |
| pygame > Build EXE / Installer (`projact.pygame.publish`) |  | game |
| pygame > Build One-File EXE (PyInstaller) (`projact.pygame.pyinstaller`) |  | game |
| pygame > Export to Godot (`projact.pygame.godot`) |  | game |
| pygame > Install pygame (`projact.pygame.install-pkg`) |  | game |
| pygame > Run Game (`projact.pygame.run`) |  | game |

## Context menu: Databases (QTreeWidget)

| Item | Shortcut | Where |
|---|---|---|
| Local Servers > Copy MariaDB/MySQL Password |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Copy PostgreSQL Password |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Server Status |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Start local MariaDB/MySQL |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Start local PostgreSQL |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Stop local MariaDB/MySQL |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Local Servers > Stop local PostgreSQL |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Add Connection |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Adminer (login page) |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| Database Diagram |  | flask [vs] |
| Export Database to SQL |  | flask [vs] |
| Import CSV into New Table |  | flask [vs] |
| New Query |  | flask [vs] |
| New SQLite Database |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web [vs] |
| New Table |  | flask [vs] |
| Open in Adminer |  | flask [vs] |
| Open in Adminer (new tab) |  | flask [vs] |
| Properties |  | flask [vs] |
| Refresh |  | all contexts [vs] |
| Remove Connection |  | flask [vs] |

## Context menu: Designer

| Item | Shortcut | Where |
|---|---|---|
| (control) > AI > Generate Event Handler for AppBar1 |  | flutter |
| (control) > AI > Generate Event Handler for Button1 |  | python-tk |
| (control) > AI > Generate Event Handler for lblMessage |  | asm |
| (control) > AI > Generate Event Handler for lblName |  | csharp |
| (control) > AI > Generate Event Handler for lblYourName |  | vb6 |
| (control) > AI > Generate New Form with AI |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > AI > Redesign This Form with AI |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Bounce |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Flip |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Move |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Pulse |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Rotate |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Shake |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Attention > Zoom |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Color > Color |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Entrance > Fade In |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Entrance > Slide In |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Entrance > Zoom In |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Exit > Fade Out |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Exit > Slide Out |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Exit > Zoom Out |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Add Animation > Text > Typewriter |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Events > Click |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Events > DoubleClick |  | asm, csharp, python-tk, vb6 |
| (control) > Events > GotFocus |  | asm, csharp, python-tk, vb6 |
| (control) > Events > KeyDown |  | asm, csharp, python-tk, vb6 |
| (control) > Events > KeyPress |  | asm, csharp, python-tk, vb6 |
| (control) > Events > KeyUp |  | asm, csharp, python-tk, vb6 |
| (control) > Events > LostFocus |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseDown |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseEnter |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseLeave |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseMove |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseUp |  | asm, csharp, python-tk, vb6 |
| (control) > Events > MouseWheel |  | asm, csharp, python-tk, vb6 |
| (control) > Layout Size > Add Size |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Layout Size > All sizes |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Layout Size > Base design |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Layout Size > This size only |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Bring to Front |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Copy |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Cut |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Delete |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Lock Controls |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Paste |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Properties |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > Send to Back |  | asm, csharp, flutter, python-tk, vb6 |
| (control) > View Code |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > AI > Generate Event Handler for Form1 |  | asm, csharp, python-tk |
| (form) > AI > Generate Event Handler for MainScreen |  | flutter |
| (form) > AI > Generate Event Handler for frmGreeter |  | vb6 |
| (form) > AI > Generate New Form with AI |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > AI > Redesign This Form with AI |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Bounce |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Flip |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Move |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Pulse |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Rotate |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Shake |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Attention > Zoom |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Color > Color |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Entrance > Fade In |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Entrance > Slide In |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Entrance > Zoom In |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Exit > Fade Out |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Exit > Slide Out |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Exit > Zoom Out |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Animation > Text > Typewriter |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Events > Activated |  | asm, csharp, python-tk, vb6 |
| (form) > Events > Click |  | asm, csharp, python-tk, vb6 |
| (form) > Events > Deactivate |  | asm, csharp, python-tk, vb6 |
| (form) > Events > DoubleClick |  | asm, csharp, python-tk, vb6 |
| (form) > Events > FormClosed |  | asm, csharp, python-tk, vb6 |
| (form) > Events > FormClosing |  | asm, csharp, python-tk, vb6 |
| (form) > Events > KeyDown |  | asm, csharp, python-tk, vb6 |
| (form) > Events > KeyPress |  | asm, csharp, python-tk, vb6 |
| (form) > Events > KeyUp |  | asm, csharp, python-tk, vb6 |
| (form) > Events > Load |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Events > MouseDown |  | asm, csharp, python-tk, vb6 |
| (form) > Events > MouseMove |  | asm, csharp, python-tk, vb6 |
| (form) > Events > MouseUp |  | asm, csharp, python-tk, vb6 |
| (form) > Events > MouseWheel |  | asm, csharp, python-tk, vb6 |
| (form) > Events > Resize |  | asm, csharp, python-tk, vb6 |
| (form) > Layout Size > Add Size |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Layout Size > All sizes |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Layout Size > Base design |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Layout Size > This size only |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Add Windows Form |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Copy |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Cut |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Delete |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Localization Strings |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Lock Controls |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Paste |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Properties |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > Select All |  | asm, csharp, flutter, python-tk, vb6 |
| (form) > View Code |  | asm, csharp, flutter, python-tk, vb6 |

## Context menu: Editor tab

| Item | Shortcut | Where |
|---|---|---|
| Close |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web |
| Close All |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web |
| Close All But This |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web |

## Context menu: Flask (QTreeWidget)

| Item | Shortcut | Where |
|---|---|---|
| Copy Name |  | flask [vs] |
| Go to View |  | flask [vs] |
| Open in Preview |  | flask [vs] |

## Context menu: Game Assets (_AssetTree)

| Item | Shortcut | Where |
|---|---|---|
| Import |  | game [vs] |

## Context menu: HexView (HexView)

| Item | Shortcut | Where |
|---|---|---|
| Copy |  | firmware |
| Go To Offset |  | firmware |
| Open in Map Editor |  | firmware |
| Paste |  | firmware |
| Select All |  | firmware |
| Toggle Bookmark |  | firmware |

## Context menu: Requests (QTreeWidget)

| Item | Shortcut | Where |
|---|---|---|
| Clear |  | flask, web [vscode] |
| Copy All |  | flask, web [vscode] |
| Copy Name: Value |  | flask, web [vscode] |
| Copy Value |  | flask, web [vscode] |

## Context menu: Solution Explorer

| Item | Shortcut | Where |
|---|---|---|
| (code) > Add Windows Form |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > Delete |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > Format This File (ruff) |  | python-tk |
| (code) > Open (Designer) |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > Rename |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > Set as Startup Form |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > View Code |  | asm, csharp, flutter, python-tk, vb6 |
| (code) > View Generated Code |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > Add Windows Form |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > Delete |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > Open (Designer) |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > Rename |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > Set as Startup Form |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > View Code |  | asm, csharp, flutter, python-tk, vb6 |
| (design) > View Generated Code |  | asm, csharp, flutter, python-tk, vb6 |
| (ecuproj) > Open Firmware & ECU Workbench |  | firmware |
| (ecuproj_original) > Open With > Firmware & ECU Workbench |  | firmware |
| (ecuproj_original) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | firmware |
| (ecuproj_original) > Analyze Firmware |  | firmware |
| (ecuproj_work) > Open With > Firmware & ECU Workbench |  | firmware |
| (ecuproj_work) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | firmware |
| (ecuproj_work) > Analyze Firmware |  | firmware |
| (generated) > Add Windows Form |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > Delete |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > Open (Designer) |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > Rename |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > Set as Startup Form |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > View Code |  | asm, csharp, flutter, python-tk, vb6 |
| (generated) > View Generated Code |  | asm, csharp, flutter, python-tk, vb6 |
| (module) > Open With > Firmware & ECU Workbench |  | csharp, dos, firmware, flutter, game, python-tk, retro |
| (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | csharp, dos, firmware, flutter, game, python-tk, retro |
| (module) > Delete |  | csharp, dos, firmware, flutter, game, python-tk, retro |
| (module) > Format This File (ruff) |  | game, python-tk |
| (module) > Open |  | csharp, dos, firmware, flutter, game, python-tk, retro |
| (project) > Add > Existing Files |  | flask, web |
| (project) > Add > Existing Item |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Add > Module |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Add > New File |  | flask, web |
| (project) > Add > New Folder |  | flask, web |
| (project) > Add > Reference |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Add > Windows Form |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Build > Build APK (Android) |  | flutter |
| (project) > Build > Build App Bundle (Google Play) |  | flutter |
| (project) > Build > Build Web |  | flutter |
| (project) > Build > Build Windows |  | flutter |
| (project) > Format and Lint > Fix Lint Problems (ruff check --fix) |  | game, python-tk |
| (project) > Format and Lint > Format Project (black) |  | game, python-tk |
| (project) > Format and Lint > Format Project (ruff) |  | game, python-tk |
| (project) > Format and Lint > Lint Project (ruff check) |  | game, python-tk |
| (project) > Packages > Add Package (pub add) |  | flutter |
| (project) > Packages > pub get |  | flutter |
| (project) > Packages > pub outdated |  | flutter |
| (project) > Packages > pub upgrade |  | flutter |
| (project) > Python > Format and Lint > Fix Lint Problems (ruff check --fix) |  | flask |
| (project) > Python > Format and Lint > Format Project (black) |  | flask |
| (project) > Python > Format and Lint > Format Project (ruff) |  | flask |
| (project) > Python > Format and Lint > Lint Project (ruff check) |  | flask |
| (project) > Python > Build EXE / Installer |  | flask |
| (project) > Python > Create .venv |  | flask |
| (project) > Python > Freeze to requirements.txt |  | flask |
| (project) > Python > Install Package |  | flask |
| (project) > Python > Install Requirements |  | flask |
| (project) > Python > List Installed Packages |  | flask |
| (project) > Python > Run Tests (pytest) |  | flask |
| (project) > Python > Run Tests (unittest) |  | flask |
| (project) > Add Form |  | vb6 |
| (project) > Analyze (flutter analyze) |  | flutter |
| (project) > Build |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Build EXE (Publish) |  | vb6 |
| (project) > Build EXE / Installer |  | game, python-tk |
| (project) > Build One-File EXE (PyInstaller) |  | game |
| (project) > Clean (flutter clean) |  | flutter |
| (project) > Create .venv |  | game, python-tk |
| (project) > Export to Godot |  | game |
| (project) > Flask Shell |  | flask |
| (project) > Flutter Doctor |  | flutter |
| (project) > Format Code (dart format) |  | flutter |
| (project) > Freeze to requirements.txt |  | game, python-tk |
| (project) > Install Package |  | game, python-tk |
| (project) > Install pygame |  | game |
| (project) > List Devices |  | flutter |
| (project) > List Installed Packages |  | game, python-tk |
| (project) > Manage Packages |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6 |
| (project) > New Blueprint |  | flask |
| (project) > New Screen (Form) |  | flutter |
| (project) > New Widget |  | flutter |
| (project) > Open Firmware & ECU Workbench |  | firmware |
| (project) > Open Folder in File Explorer |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (project) > Open in Browser |  | flask, web |
| (project) > Project Properties |  | vb6 |
| (project) > Properties |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (project) > Refresh |  | flask, web |
| (project) > Remove from Solution |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (project) > Routes |  | flask |
| (project) > Run (F5) |  | vb6 |
| (project) > Run (flutter run) |  | flutter |
| (project) > Run Game |  | game |
| (project) > Run Server |  | flask |
| (project) > Run Tests (flutter test) |  | flutter |
| (project) > Run Tests (pytest) |  | game, python-tk |
| (project) > Run Tests (unittest) |  | game, python-tk |
| (project) > Run flask Command |  | flask |
| (project) > Set as StartUp Project |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (project) > Site Settings |  | flask, web |
| (project) > Start Debugging / Continue | F5 | flask, web |
| (project) > View in Preview |  | flask, web |
| (references) > Add Reference |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (references) > Refresh References |  | asm, csharp, dos, firmware, flutter, game, python-tk, retro, vb6 |
| (resources) > Build > Build APK (Android) |  | flutter |
| (resources) > Build > Build App Bundle (Google Play) |  | flutter |
| (resources) > Build > Build Web |  | flutter |
| (resources) > Build > Build Windows |  | flutter |
| (resources) > Format and Lint > Fix Lint Problems (ruff check --fix) |  | game, python-tk |
| (resources) > Format and Lint > Format Project (black) |  | game, python-tk |
| (resources) > Format and Lint > Format Project (ruff) |  | game, python-tk |
| (resources) > Format and Lint > Lint Project (ruff check) |  | game, python-tk |
| (resources) > Packages > Add Package (pub add) |  | flutter |
| (resources) > Packages > pub get |  | flutter |
| (resources) > Packages > pub outdated |  | flutter |
| (resources) > Packages > pub upgrade |  | flutter |
| (resources) > Add Form |  | vb6 |
| (resources) > Analyze (flutter analyze) |  | flutter |
| (resources) > Build EXE (Publish) |  | vb6 |
| (resources) > Build EXE / Installer |  | game, python-tk |
| (resources) > Build One-File EXE (PyInstaller) |  | game |
| (resources) > Clean (flutter clean) |  | flutter |
| (resources) > Create .venv |  | game, python-tk |
| (resources) > Export to Godot |  | game |
| (resources) > Flutter Doctor |  | flutter |
| (resources) > Format Code (dart format) |  | flutter |
| (resources) > Freeze to requirements.txt |  | game, python-tk |
| (resources) > Install Package |  | game, python-tk |
| (resources) > Install pygame |  | game |
| (resources) > List Devices |  | flutter |
| (resources) > List Installed Packages |  | game, python-tk |
| (resources) > New Screen (Form) |  | flutter |
| (resources) > New Widget |  | flutter |
| (resources) > Project Properties |  | vb6 |
| (resources) > Run (F5) |  | vb6 |
| (resources) > Run (flutter run) |  | flutter |
| (resources) > Run Game |  | game |
| (resources) > Run Tests (flutter test) |  | flutter |
| (resources) > Run Tests (pytest) |  | game, python-tk |
| (resources) > Run Tests (unittest) |  | game, python-tk |
| (solution) > Add > Existing Project |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Add > New Project |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Set StartUp Project > Boot Site |  | web |
| (solution) > Set StartUp Project > Contacts |  | dos |
| (solution) > Set StartUp Project > CoreNasmForms |  | asm |
| (solution) > Set StartUp Project > CrawlEcu |  | firmware |
| (solution) > Set StartUp Project > EvDemo |  | python-tk |
| (solution) > Set StartUp Project > Flask_Todo |  | flask |
| (solution) > Set StartUp Project > Greeter |  | vb6 |
| (solution) > Set StartUp Project > HelloCSharp |  | csharp |
| (solution) > Set StartUp Project > IdeProj |  | flutter |
| (solution) > Set StartUp Project > NesStarCatcher |  | retro |
| (solution) > Set StartUp Project > Platformer |  | game |
| (solution) > Build Solution |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Open Folder in File Explorer |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Properties |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Refresh References |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Save All |  | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Start Debugging / Continue | F5 | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (solution) > Start Without Debugging | Ctrl+F5 | asm, csharp, dos, firmware, flask, flutter, game, python-tk, retro, vb6, web |
| (webfile) > Open With > Firmware & ECU Workbench |  | flask, web |
| (webfile) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | flask, web |
| (webfile) > Copy Full Path |  | flask, web |
| (webfile) > Copy URL |  | flask, web |
| (webfile) > Delete |  | flask, web |
| (webfile) > Open |  | flask, web |
| (webfile) > Open Containing Folder |  | flask, web |
| (webfile) > Open in Browser |  | flask, web |
| (webfile) > Rename |  | flask, web |
| (webfile) > View in Preview |  | flask, web |
| (webfolder) > Add > Existing Files |  | flask, web |
| (webfolder) > Add > New File |  | flask, web |
| (webfolder) > Add > New Folder |  | flask, web |
| (webfolder) > Delete |  | flask, web |
| (webfolder) > New Blueprint |  | flask |
| (webfolder) > Open Folder in File Explorer |  | flask, web |
| (webfolder) > Open in Browser |  | flask, web |
| (webfolder) > Rename |  | flask, web |
| (webfolder) > View in Preview |  | flask, web |

## Context menu: Toolbox (Toolbox)

| Item | Shortcut | Where |
|---|---|---|
| Choose Items |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6 |
| Collapse All |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6 |
| Expand All |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6 |
| Install Component Package |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6 |
| Show All Items |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6 |

## Data

| Item | Shortcut | Where |
|---|---|---|
| Add New Data Source |  | all contexts |
| Preview Data |  | all contexts |
| Refresh Data Sources |  | all contexts |
| Show Data Sources | Alt+Shift+D | all contexts |

## Debug

| Item | Shortcut | Where |
|---|---|---|
| Assembly Checks > Assembly Checks Window |  | all contexts |
| Assembly Checks > Check Selection |  | all contexts |
| Assembly Checks > Check This Procedure |  | all contexts |
| Assembly Checks > Check by Running | Ctrl+Shift+F5 | all contexts |
| Assembly Checks > Explain This Line | Ctrl+Shift+F1 | all contexts |
| Assembly Checks > What-If Console |  | all contexts |
| Mobile > Always Use the Dart Debugger for F5 |  | all contexts |
| Mobile > Hot Reload | Ctrl+Alt+R | all contexts |
| Mobile > Hot Restart | Ctrl+Alt+Shift+R | all contexts |
| Mobile > Refresh devices |  | all contexts |
| Windows > Call Stack |  | all contexts |
| Windows > Disassembly | Alt+8 | all contexts |
| Windows > Immediate |  | all contexts |
| Windows > Locals |  | all contexts |
| Windows > Memory 1 | Alt+6 | all contexts |
| Windows > Registers | Alt+5 | all contexts |
| Windows > Stack |  | all contexts |
| Windows > Threads | Ctrl+Alt+H | all contexts |
| Windows > Watch |  | all contexts |
| 8086: Stop at First Instruction |  | all contexts |
| Attach to Process | Ctrl+Alt+P | all contexts |
| Break All |  | all contexts |
| Break on Exceptions |  | all contexts |
| Breakpoint Condition | Alt+F9 | all contexts |
| Breakpoint Settings (Condition, Hit Count, Log) |  | all contexts |
| CPU (OllyDbg Style) | Alt+C | all contexts |
| CPU View at First Stop |  | all contexts |
| Debug Expo Web Page (js-debug) |  | all contexts |
| Debug with Extension Debugger |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Go To Disassembly |  | all contexts |
| Install Delve (Go Debugger) |  | all contexts |
| Run to Cursor | Ctrl+F10 | all contexts |
| Start Debugging / Continue | F5 | all contexts |
| Start Without Debugging | Ctrl+F5 | all contexts |
| Step Into | F11 | all contexts |
| Step Into Instruction | Ctrl+Alt+F11 | all contexts |
| Step Out | Shift+F11 | all contexts |
| Step Over | F10 | all contexts |
| Step Over Instruction | Ctrl+Alt+F10 | all contexts |
| Stop Debugging | Shift+F5 | all contexts |
| Toggle Breakpoint | F9 | all contexts |
| Watch |  | all contexts |

## Edit

| Item | Shortcut | Where |
|---|---|---|
| AI > Add Comments |  | all contexts |
| AI > Edit with AI |  | all contexts |
| AI > Explain |  | all contexts |
| AI > Fix |  | all contexts |
| AI > Generate Docs |  | all contexts |
| AI > Generate Tests |  | all contexts |
| AI > Inline Completions |  | all contexts |
| AI > Refactor |  | all contexts |
| AI > Suggest Inline Completion |  | all contexts |
| IntelliSense > Remove and Sort Usings |  | all contexts |
| IntelliSense > Sort Usings |  | all contexts |
| Refactor > Extract Method |  | all contexts |
| Refactor > Extract Variable |  | all contexts |
| Refactor > Find All References |  | all contexts |
| Refactor > Quick Actions and Refactorings |  | all contexts |
| Refactor > Rename |  | all contexts |
| Copy | Ctrl+C | all contexts |
| Cut | Ctrl+X | all contexts |
| Delete |  | all contexts |
| Emmet: Expand Abbreviation |  | all contexts |
| Find | Ctrl+F | all contexts |
| Find Next | F3 | all contexts |
| Find Previous | Shift+F3 | all contexts |
| Find in Files | Ctrl+Shift+F | all contexts |
| Format Document | Alt+Shift+F, Ctrl+K, Ctrl+D | all contexts |
| Format on Save |  | all contexts |
| Go to Definition | F12 | all contexts |
| Go to Line | Ctrl+G | all contexts |
| Insert Snippet |  | all contexts |
| Language Mode |  | all contexts |
| Open as PHP |  | all contexts |
| Paste | Ctrl+V | all contexts |
| Redo | Ctrl+Y | all contexts |
| Replace | Ctrl+H | all contexts |
| Select All | Ctrl+A | all contexts |
| Undo | Ctrl+Z | all contexts |

## File

| Item | Shortcut | Where |
|---|---|---|
| Add > Existing Project |  | all contexts |
| Add > New Project |  | all contexts |
| Import > Program (.exe / .dll) |  | all contexts |
| Import > Python GUI Program (Tkinter / Qt) |  | all contexts |
| Import > Visual Basic 6 Project (.vbp / .frm) |  | all contexts |
| New Image > Cursor (.cur) |  | all contexts |
| New Image > Icon (.ico) |  | all contexts |
| New Image > Image (.png / .bmp) |  | all contexts |
| New Notebook > Blank Notebook (.ipynb) |  | all contexts |
| New Notebook > Data Science Starter (pandas + matplotlib) |  | all contexts |
| New Notebook > Import Python Script as Notebook |  | all contexts |
| New Notebook > Open Notebook |  | all contexts |
| Open Remote > Recent SSH Hosts > (no saved hosts) |  | all contexts |
| Open Remote > Build on Remote |  | all contexts |
| Open Remote > Connect to SSH Host |  | all contexts |
| Open Remote > Disconnect |  | all contexts |
| Open Remote > Open Folder in Dev Container |  | all contexts |
| Open Remote > Open WSL Folder |  | all contexts |
| Open Remote > Reload Remote File |  | all contexts |
| Open Remote > Remote Explorer |  | all contexts |
| Open Remote > Remote Terminal |  | all contexts |
| Open Remote > Run Remote Command |  | all contexts |
| Open Remote > Run on Remote |  | all contexts |
| Open Remote > Stop Remote Command |  | all contexts |
| Open in Hex Editor > Current File |  | all contexts |
| Open in Hex Editor > File |  | all contexts |
| Recent Projects and Solutions > (no recent projects) |  | all contexts |
| App Gallery |  | all contexts |
| Close Solution |  | all contexts |
| Exit |  | all contexts |
| Migrate Project |  | all contexts |
| New Project | Ctrl+Shift+N | all contexts |
| New Project (.NET, Visual Studio 2022) | Ctrl+Alt+Shift+N | all contexts |
| New Solution from Existing Folders |  | all contexts |
| New Window | Ctrl+Alt+N | all contexts |
| Open File | Ctrl+O | all contexts |
| Open Folder | Ctrl+K, Ctrl+O | all contexts |
| Open Project | Ctrl+Shift+O | all contexts |
| Open in Design View |  | all contexts |
| Save |  | flask, none |
| Save All | Ctrl+S | all contexts |
| Save Form1.form [Design] |  | asm, csharp, python-tk |
| Save MAIN.BAS |  | dos |
| Save MainScreen.form [Design] |  | flutter |
| Save frmGreeter.form [Design] |  | vb6 |
| Save index.html |  | web |
| Save main.py |  | game |
| Save main.s |  | retro |
| Save notes.md |  | firmware |

## Flask

| Item | Shortcut | Where |
|---|---|---|
| Flask Shell |  | flask |
| New Blueprint |  | flask |
| Routes |  | flask |
| Run Server |  | flask |
| Run flask Command |  | flask |
| Stop Running Command |  | flask |

## Flutter

| Item | Shortcut | Where |
|---|---|---|
| Build > Build APK (Android) |  | flutter |
| Build > Build App Bundle (Google Play) |  | flutter |
| Build > Build Web |  | flutter |
| Build > Build Windows |  | flutter |
| Packages > Add Package (pub add) |  | flutter |
| Packages > pub get |  | flutter |
| Packages > pub outdated |  | flutter |
| Packages > pub upgrade |  | flutter |
| Analyze (flutter analyze) |  | flutter |
| Clean (flutter clean) |  | flutter |
| Flutter Doctor |  | flutter |
| Format Code (dart format) |  | flutter |
| List Devices |  | flutter |
| New Screen (Form) |  | flutter |
| New Widget |  | flutter |
| Run (flutter run) |  | flutter |
| Run Tests (flutter test) |  | flutter |
| Stop Running Command |  | flutter |

## Format

| Item | Shortcut | Where |
|---|---|---|
| Align > Bottoms |  | all contexts |
| Align > Centers |  | all contexts |
| Align > Lefts |  | all contexts |
| Align > Middles |  | all contexts |
| Align > Rights |  | all contexts |
| Align > Tops |  | all contexts |
| Align > to Grid |  | all contexts |
| Center in Form > Horizontally |  | all contexts |
| Center in Form > Vertically |  | all contexts |
| Horizontal Spacing > Decrease |  | all contexts |
| Horizontal Spacing > Increase |  | all contexts |
| Horizontal Spacing > Make Equal |  | all contexts |
| Horizontal Spacing > Remove |  | all contexts |
| Make Same Size > Both |  | all contexts |
| Make Same Size > Height |  | all contexts |
| Make Same Size > Size to Grid |  | all contexts |
| Make Same Size > Width |  | all contexts |
| Order > Bring to Front |  | all contexts |
| Order > Send to Back |  | all contexts |
| Vertical Spacing > Decrease |  | all contexts |
| Vertical Spacing > Increase |  | all contexts |
| Vertical Spacing > Make Equal |  | all contexts |
| Vertical Spacing > Remove |  | all contexts |
| Localization Strings |  | all contexts |
| Lock Controls |  | all contexts |

## Game

| Item | Shortcut | Where |
|---|---|---|
| Open Scene > Level1.scene |  | game |
| Open Scene > Level2.scene |  | game |
| Add Sprite from Image |  | game |
| Check Scene |  | game |
| Export to Godot |  | game |
| Game Assets Window |  | game |
| Import Sound |  | game |
| Import Tileset |  | game |
| New Scene |  | game |
| Play Scene (Ctrl+F5) |  | game |
| Sprite Sheet and Animations |  | game |

## Git

| Item | Shortcut | Where |
|---|---|---|
| GitHub > Create Pull Request |  | all contexts |
| GitHub > Download GitHub CLI |  | all contexts |
| GitHub > Pull Requests and Issues |  | all contexts |
| GitHub > Sign in (gh auth login) |  | all contexts |
| Abort merge / rebase |  | all contexts |
| Amend last commit |  | all contexts |
| Blame current file |  | all contexts |
| Commit All |  | all contexts |
| Compare current file with commit |  | all contexts |
| Continue merge / rebase |  | all contexts |
| Edit .gitignore |  | all contexts |
| Fetch |  | all contexts |
| Force Push (with lease) |  | all contexts |
| Git Changes |  | all contexts |
| Git Settings |  | all contexts |
| Manage Branches |  | all contexts |
| Merge into current branch |  | all contexts |
| New Branch | Ctrl+Alt+Shift+B | all contexts |
| Pull |  | all contexts |
| Pull (rebase) |  | all contexts |
| Push |  | all contexts |
| Rebase current branch onto |  | all contexts |
| Remotes |  | all contexts |
| Resolve Conflicts |  | all contexts |
| Stash All |  | all contexts |
| Stashes |  | all contexts |
| Sync (pull, then push) |  | all contexts |
| Tags |  | all contexts |
| Toggle inline blame in the editor |  | all contexts |
| Undo last commit (keep changes) |  | all contexts |
| View History (graph) | Ctrl+Alt+H | all contexts |

## Help

| Item | Shortcut | Where |
|---|---|---|
| Help Files (CHM) > AI in RAD IDE (Arabic guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > BASIC course (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > C++ course (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Car Diagnostics: OBD-II, Warning Lights and Service Functions (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > CodeIgniter 4 in RAD IDE (Guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > DOS Programming: QBasic, Pascal, C, Assembly and Visual Designers (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Deploy and Publish in RAD IDE (Arabic guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > ECU and Firmware Files: Analysis and Calibration Editing (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Extensions in RAD IDE (Arabic guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Flutter Mobile Apps in RAD IDE (guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Fortran Basics (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Import and Migrate in RAD IDE (Arabic guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Jupyter Notebooks and Data Science in RAD IDE (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Laravel in RAD IDE (Guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Assembly from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn C from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn C# from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Dart from Scratch (to Flutter) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Go from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Java from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn JavaScript and TypeScript with Node.js (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Lua from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Perl from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn PowerShell from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Python from Scratch to Desktop Apps (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Ring from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Ruby from Scratch, then Ruby on Rails (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Learn Rust from Scratch (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Making Games in RAD IDE (guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Node.js and Front-end Guide for RAD IDE (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Old NASA Programs: the Apollo Guidance Computer and Classic Fortran (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Guide: Data and Reports (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Guide: Debugging and Testing (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Guide: Git and Collaboration (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Guide: The Form Designer (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Guide: Workbench Basics (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > RAD IDE Manual (CHM) |  | all contexts |
| Help Files (CHM) > Retro Games: ROM Hacking and Programming the Atari 2600, NES and Game Boy (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Solutions and References in RAD IDE (Arabic guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Visual Studio Projects in RAD IDE (Guide) (Arabic, CHM) |  | all contexts |
| Help Files (CHM) > Web Development with PHP from Scratch (Arabic, CHM) |  | all contexts |
| About |  | all contexts |
| Check for Updates |  | all contexts |
| Check for Updates Automatically |  | all contexts |
| Context Help | F1 | all contexts |
| Example Projects |  | all contexts |
| Install Another Version |  | all contexts |
| Keyboard Shortcuts |  | all contexts |
| PE / MFC Workbench Guide |  | all contexts |
| Python Documentation |  | all contexts |
| Qt for Python (PySide6) Documentation |  | all contexts |
| RAD IDE Help | Ctrl+F1 | all contexts |
| Ring Documentation |  | all contexts |
| Ring Samples |  | all contexts |
| RingQt / Qt 5 Class Reference |  | all contexts |
| Tkinter Documentation |  | all contexts |
| Tutorials (Arabic lessons) | Ctrl+Shift+F1 | all contexts |
| VB6 Language Reference |  | all contexts |

## Menu bar corner

| Item | Shortcut | Where |
|---|---|---|
| Agent |  | all contexts |
| Code |  | all contexts |
| VS |  | all contexts |

## Project

| Item | Shortcut | Where |
|---|---|---|
| BASIC Commands > Add Form |  | vb6 |
| BASIC Commands > Build EXE (Publish) |  | vb6 |
| BASIC Commands > Project Properties |  | vb6 |
| BASIC Commands > Run (F5) |  | vb6 |
| BASIC Commands > Stop Running Command |  | vb6 |
| ECU Project > Analyze (workbench) |  | all contexts |
| ECU Project > Build ECU Project |  | all contexts |
| ECU Project > Build Settings |  | all contexts |
| ECU Project > Build in Workbench |  | all contexts |
| ECU Project > Checksum Toolkit (any file) |  | all contexts |
| ECU Project > Checksums |  | all contexts |
| ECU Project > Compare with Original |  | all contexts |
| ECU Project > Compare with Original (workbench) |  | all contexts |
| ECU Project > Edit Working Copy |  | all contexts |
| ECU Project > Export Modification Report |  | all contexts |
| ECU Project > Export Patch (IPS / BPS) |  | all contexts |
| ECU Project > Find Maps (workbench) |  | all contexts |
| ECU Project > Import Patch |  | all contexts |
| ECU Project > Open Build Output |  | all contexts |
| ECU Project > Open Workbench |  | all contexts |
| ECU Project > Set Original |  | all contexts |
| ECU Project > Verify Checksums |  | all contexts |
| ECU Project > Verify Checksums (workbench) |  | all contexts |
| ECU Project > Versions |  | all contexts |
| ECU Project > View Original (read-only) |  | all contexts |
| Firmware Analysis > Analyze |  | all contexts |
| Firmware Analysis > Make Working Copy |  | all contexts |
| Firmware Analysis > Open Labels |  | all contexts |
| Firmware Analysis > Open Notes |  | all contexts |
| Firmware Analysis > Set Original |  | all contexts |
| Firmware Analysis > Verify Original |  | all contexts |
| Flask Commands > Flask Shell |  | flask |
| Flask Commands > New Blueprint |  | flask |
| Flask Commands > Routes |  | flask |
| Flask Commands > Run Server |  | flask |
| Flask Commands > Run flask Command |  | flask |
| Flask Commands > Stop Running Command |  | flask |
| Flutter Commands > Build > Build APK (Android) |  | flutter |
| Flutter Commands > Build > Build App Bundle (Google Play) |  | flutter |
| Flutter Commands > Build > Build Web |  | flutter |
| Flutter Commands > Build > Build Windows |  | flutter |
| Flutter Commands > Packages > Add Package (pub add) |  | flutter |
| Flutter Commands > Packages > pub get |  | flutter |
| Flutter Commands > Packages > pub outdated |  | flutter |
| Flutter Commands > Packages > pub upgrade |  | flutter |
| Flutter Commands > Analyze (flutter analyze) |  | flutter |
| Flutter Commands > Clean (flutter clean) |  | flutter |
| Flutter Commands > Flutter Doctor |  | flutter |
| Flutter Commands > Format Code (dart format) |  | flutter |
| Flutter Commands > List Devices |  | flutter |
| Flutter Commands > New Screen (Form) |  | flutter |
| Flutter Commands > New Widget |  | flutter |
| Flutter Commands > Run (flutter run) |  | flutter |
| Flutter Commands > Run Tests (flutter test) |  | flutter |
| Flutter Commands > Stop Running Command |  | flutter |
| Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) |  | flask, game, python-tk |
| Python Commands > Format and Lint > Format Project (black) |  | flask, game, python-tk |
| Python Commands > Format and Lint > Format Project (ruff) |  | flask, game, python-tk |
| Python Commands > Format and Lint > Lint Project (ruff check) |  | flask, game, python-tk |
| Python Commands > Build EXE / Installer |  | flask, game, python-tk |
| Python Commands > Create .venv |  | flask, game, python-tk |
| Python Commands > Freeze to requirements.txt |  | flask, game, python-tk |
| Python Commands > Install Package |  | flask, game, python-tk |
| Python Commands > Install Requirements |  | flask |
| Python Commands > List Installed Packages |  | flask, game, python-tk |
| Python Commands > Run Tests (pytest) |  | flask, game, python-tk |
| Python Commands > Run Tests (unittest) |  | flask, game, python-tk |
| Python Commands > Stop Running Command |  | flask, game, python-tk |
| ROM Hacking > Add Patch |  | all contexts |
| ROM Hacking > Build Patched ROM |  | all contexts |
| ROM Hacking > Capture Edits as Patch |  | all contexts |
| ROM Hacking > Edit Working Copy |  | all contexts |
| ROM Hacking > Open Build Output |  | all contexts |
| ROM Hacking > Patch Manager |  | all contexts |
| ROM Hacking > Set Source ROM |  | all contexts |
| ROM Hacking > View Source ROM (read-only) |  | all contexts |
| pygame Commands > Build EXE / Installer |  | game |
| pygame Commands > Build One-File EXE (PyInstaller) |  | game |
| pygame Commands > Export to Godot |  | game |
| pygame Commands > Install pygame |  | game |
| pygame Commands > Run Game |  | game |
| pygame Commands > Stop Running Command |  | game |
| Add 3D Scene |  | all contexts |
| Add Existing Item |  | all contexts |
| Add Module |  | all contexts |
| Add New Screen (Flutter designer) |  | all contexts |
| Add Reference |  | all contexts |
| Add Report |  | all contexts |
| Add User Control |  | all contexts |
| Add Windows Form |  | all contexts |
| Build EXE |  | all contexts |
| Check for Errors | Ctrl+Shift+B | all contexts |
| DOS Project Settings |  | all contexts |
| DOS Settings |  | all contexts |
| Flutter App Theme |  | all contexts |
| Flutter Assets |  | all contexts |
| Flutter Fonts (Google Fonts) |  | all contexts |
| Generate Form with AI |  | all contexts |
| Import Flutter Screen from Dart |  | all contexts |
| Manage Packages |  | all contexts |
| Open Project Folder |  | all contexts |
| Project Properties |  | all contexts |
| Resources |  | all contexts |
| Set as StartUp Project |  | all contexts |
| User Control Properties and Events |  | all contexts |

## Python

| Item | Shortcut | Where |
|---|---|---|
| Format and Lint > Fix Lint Problems (ruff check --fix) |  | flask, game, python-tk |
| Format and Lint > Format Project (black) |  | flask, game, python-tk |
| Format and Lint > Format Project (ruff) |  | flask, game, python-tk |
| Format and Lint > Lint Project (ruff check) |  | flask, game, python-tk |
| Build EXE / Installer |  | flask, game, python-tk |
| Create .venv |  | flask, game, python-tk |
| Freeze to requirements.txt |  | flask, game, python-tk |
| Install Package |  | flask, game, python-tk |
| Install Requirements |  | flask |
| List Installed Packages |  | flask, game, python-tk |
| Run Tests (pytest) |  | flask, game, python-tk |
| Run Tests (unittest) |  | flask, game, python-tk |
| Stop Running Command |  | flask, game, python-tk |

## Share

| Item | Shortcut | Where |
|---|---|---|
| Follow Participant > (no session) |  | all contexts |
| Copy Invite Link |  | all contexts |
| End Collaboration Session |  | all contexts |
| Guests Read-only |  | all contexts |
| Join Collaboration Session |  | all contexts |
| Live Share Window |  | all contexts |
| Save Shared File on Host |  | all contexts |
| Start Collaboration Session |  | all contexts |

## Site

| Item | Shortcut | Where |
|---|---|---|
| Docker > Build Image |  | all contexts |
| Docker > Compose Down |  | all contexts |
| Docker > Compose Up |  | all contexts |
| Docker > Docker Panel |  | all contexts |
| Docker > Generate Dockerfile / Compose / Dev Container |  | all contexts |
| Docker > Lint Dockerfile |  | all contexts |
| Open in Installed Browser > Chrome |  | all contexts |
| Open in Installed Browser > Default browser |  | all contexts |
| Open in Installed Browser > Edge |  | all contexts |
| Open in Installed Browser > Firefox |  | all contexts |
| App Gallery |  | all contexts |
| Build Production (npm run build) |  | all contexts |
| CodeIgniter Panel (Spark, Routes) |  | all contexts |
| Databases | Ctrl+Alt+D | all contexts |
| Deploy to Cloud / Git / SSH |  | all contexts |
| Django / Flask / FastAPI Panel |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web |
| Flask |  | flask |
| Laravel Panel (Artisan, Routes, Tinker) |  | all contexts |
| Lighthouse Report |  | all contexts |
| New File |  | all contexts |
| New Folder |  | all contexts |
| New Front-end App (React, Vue, Svelte, Angular) |  | all contexts |
| Open Database in Adminer |  | all contexts |
| Open in Browser | Ctrl+Alt+B | all contexts |
| Preview |  | all contexts |
| Publish | Ctrl+Alt+P | all contexts |
| Publish Preview (dry run) |  | all contexts |
| REST Client | Ctrl+Alt+K | all contexts |
| Rails Panel (Console, Routes, Models) |  | all contexts |
| Reports |  | all contexts |
| Requests |  | all contexts |
| Restart Web Server |  | all contexts |
| Run Site in Preview |  | all contexts |
| SEO Report |  | all contexts |
| Site Settings |  | all contexts |
| Stop Web Server |  | all contexts |
| SuperPreview | Ctrl+Alt+B | all contexts |

## Test

| Item | Shortcut | Where |
|---|---|---|
| Clear Coverage Results |  | all contexts |
| Debug Selected Test |  | all contexts |
| Refresh Tests |  | all contexts |
| Run All Tests | Ctrl+R, A | all contexts |
| Run All Tests with Coverage |  | all contexts |
| Run Failed Tests |  | all contexts |
| Run Tests in Current File | Ctrl+R, T | all contexts |
| Show Code Coverage Colouring |  | all contexts |
| Test Explorer | Ctrl+E, T | all contexts |

## Toolbar Activity Bar

| Item | Shortcut | Where |
|---|---|---|
| AI Chat |  | all contexts [agent,vscode] |
| AI Web Chats |  | all contexts [agent,vscode] |
| Agents |  | all contexts [agent,vscode] |
| Claude Code |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web [agent,vscode] |
| Databases |  | all contexts [vscode] |
| Editor |  | all contexts [agent] |
| Explorer |  | all contexts [agent,vscode] |
| Extensions |  | all contexts [agent,vscode] |
| Live Share |  | all contexts [agent,vscode] |
| Manage |  | all contexts [agent,vscode] |
| Packages |  | all contexts [vscode] |
| QWidget |  | all contexts [agent,vscode] |
| Remote Explorer |  | all contexts [vscode] |
| Ring Samples |  | all contexts [agent,vscode] |
| Run and Debug |  | all contexts [vscode] |
| Search |  | all contexts [agent,vscode] |
| Source Control |  | all contexts [agent,vscode] |
| Testing |  | all contexts [vscode] |
| Tutorials |  | all contexts [agent,vscode] |

## Toolbar Debug

| Item | Shortcut | Where |
|---|---|---|
| Step Into | F11 | all contexts |
| Step Out | Shift+F11 | all contexts |
| Step Over | F10 | all contexts |
| Toggle Breakpoint | F9 | all contexts |

## Toolbar Expo

| Item | Shortcut | Where |
|---|---|---|
| Close the Emulator |  | all contexts |
| Open in Browser |  | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| Refresh devices |  | all contexts |

## Toolbar Firmware

| Item | Shortcut | Where |
|---|---|---|
| More > Calibration Map Editor (full) |  | firmware |
| More > Correct Checksums |  | firmware |
| More > Detailed Firmware Analysis |  | firmware |
| More > Find Checksums (from the original) |  | firmware |
| More > Import A2L |  | firmware |
| More > Load Checksum Profile |  | firmware |
| More > Open Original (read-only hex editor) |  | firmware |
| More > Open in Ghidra |  | firmware |
| More > Save Working Copy As (binary) |  | firmware |
| Analyze |  | firmware |
| Build |  | firmware |
| Compare |  | firmware |
| Find Maps |  | firmware |
| Map from Selection |  | firmware |
| QLabel |  | firmware |
| Save Version |  | firmware |
| Verify Checksums |  | firmware |

## Toolbar Mobile

| Item | Shortcut | Where |
|---|---|---|
| Hot Reload | Ctrl+Alt+R | all contexts |
| Hot Restart | Ctrl+Alt+Shift+R | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| Refresh devices |  | all contexts |

## Toolbar Project Actions

| Item | Shortcut | Where |
|---|---|---|
| Build EXE (Publish) |  | vb6 |
| Routes |  | flask |
| Run Game |  | game |
| Run Server |  | flask |
| Run Tests (pytest) |  | game, python-tk |
| Stop Running Command |  | flask, flutter, game, python-tk, vb6 |
| pub get |  | flutter |

## Toolbar Retro Emulator

| Item | Shortcut | Where |
|---|---|---|
| QComboBox |  | all contexts |
| QLabel |  | all contexts |

## Toolbar Rust

| Item | Shortcut | Where |
|---|---|---|
| Clippy |  | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| Reload |  | all contexts |
| Test |  | all contexts |

## Toolbar Solution Configurations

| Item | Shortcut | Where |
|---|---|---|
| QComboBox |  | all contexts |
| QLabel |  | all contexts |

## Toolbar Standard

| Item | Shortcut | Where |
|---|---|---|
| Design | Ctrl+Shift+D | all contexts |
| New Project | Ctrl+Shift+N | all contexts |
| Open Project | Ctrl+Shift+O | all contexts |
| Redo | Ctrl+Y | all contexts |
| Save All | Ctrl+S | all contexts |
| Split | Ctrl+Alt+Shift+D | all contexts |
| Start Debugging / Continue | F5 | all contexts |
| Stop Debugging | Shift+F5 | all contexts |
| Undo | Ctrl+Z | all contexts |

## Toolbar Toolbar

| Item | Shortcut | Where |
|---|---|---|
| Local Servers > Copy MariaDB/MySQL Password |  | all contexts |
| Local Servers > Copy PostgreSQL Password |  | all contexts |
| Local Servers > Server Status |  | all contexts |
| Local Servers > Start local MariaDB/MySQL |  | all contexts |
| Local Servers > Start local PostgreSQL |  | all contexts |
| Local Servers > Stop local MariaDB/MySQL |  | all contexts |
| Local Servers > Stop local PostgreSQL |  | all contexts |
| New > Add Connection (SQLite / MySQL / PostgreSQL) |  | all contexts |
| New > New SQLite Database |  | all contexts |
| Add New Data Source |  | all contexts |
| Back |  | all contexts |
| Bookmark |  | firmware |
| Clear |  | all contexts |
| Collision |  | game |
| Configure Data Source |  | all contexts |
| Coverage |  | all contexts |
| Debug |  | all contexts |
| Diagram |  | all contexts |
| Erase |  | game |
| Fill |  | game |
| Find |  | firmware |
| Fit |  | game |
| Forward |  | all contexts |
| Front |  | game |
| Go To |  | firmware |
| Grid |  | game |
| New Query |  | all contexts |
| New Table |  | all contexts |
| Next Bookmark |  | firmware |
| Open in Adminer |  | all contexts |
| Open in Browser |  | all contexts |
| Overwrite |  | firmware |
| Paint |  | game |
| Play |  | game |
| Preview Data |  | all contexts |
| QCheckBox |  | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| QLineEdit |  | all contexts |
| Rect |  | game |
| Redo (Ctrl+Y) |  | game |
| Refresh |  | all contexts |
| Refresh (re-read the columns and rows) |  | all contexts |
| Reload (F5 in the page) |  | all contexts |
| Remove Data Source |  | all contexts |
| Rotate |  | all contexts |
| Run |  | all contexts |
| Run All |  | all contexts |
| Run Failed |  | all contexts |
| Select |  | game |
| Snap |  | game |
| Sprite Sheet |  | game |
| Stop |  | all contexts |
| Tileset |  | game |
| Undo (Ctrl+Z) |  | game |

## Tools

| Item | Shortcut | Where |
|---|---|---|
| Car Connection > Bus Monitor |  | all contexts |
| Car Connection > Connect to Car |  | all contexts |
| Car Connection > Demo Car (Simulator) |  | all contexts |
| Car Connection > Disconnect |  | all contexts |
| Car Connection > Find Control Units |  | all contexts |
| Compare (Diff) > Compare Current File with |  | all contexts |
| Compare (Diff) > Compare Current File with Clipboard |  | all contexts |
| Compare (Diff) > Compare Current File with Git HEAD |  | all contexts |
| Compare (Diff) > Compare Current File with Saved |  | all contexts |
| Compare (Diff) > Compare Files |  | all contexts |
| Component Packages > Choose Toolbox Items |  | all contexts |
| Component Packages > Hot Reload (package development) |  | all contexts |
| Component Packages > Install Component Package (.radcomp) |  | all contexts |
| Component Packages > Manage Component Packages |  | all contexts |
| Component Packages > Reload Packages |  | all contexts |
| Composer > Dump Autoload (composer dump-autoload) |  | all contexts |
| Composer > Install (composer install) |  | all contexts |
| Composer > Open composer.json |  | all contexts |
| Composer > Remove Package |  | all contexts |
| Composer > Require Package |  | all contexts |
| Composer > Show Outdated Packages |  | all contexts |
| Composer > Update (composer update) |  | all contexts |
| Composer > Validate composer.json |  | all contexts |
| Databases > Local Servers > Copy MariaDB/MySQL Password |  | all contexts |
| Databases > Local Servers > Copy PostgreSQL Password |  | all contexts |
| Databases > Local Servers > Server Status |  | all contexts |
| Databases > Local Servers > Start local MariaDB/MySQL |  | all contexts |
| Databases > Local Servers > Start local PostgreSQL |  | all contexts |
| Databases > Local Servers > Stop local MariaDB/MySQL |  | all contexts |
| Databases > Local Servers > Stop local PostgreSQL |  | all contexts |
| Databases > Add Connection |  | all contexts |
| Databases > Database Diagram |  | all contexts |
| Databases > Databases | Ctrl+Alt+D | all contexts |
| Databases > New Query |  | all contexts |
| Databases > New SQLite Database |  | all contexts |
| Databases > Open in Adminer |  | all contexts |
| Databases > Start local MariaDB/MySQL |  | all contexts |
| Databases > Start local PostgreSQL |  | all contexts |
| Docker > Build Image |  | all contexts |
| Docker > Compose Down |  | all contexts |
| Docker > Compose Up |  | all contexts |
| Docker > Docker Panel |  | all contexts |
| Docker > Generate Dockerfile / Compose / Dev Container |  | all contexts |
| Docker > Lint Dockerfile |  | all contexts |
| Firmware & ECU > Calibration Maps > Compare Two Binaries (Maps) |  | all contexts |
| Firmware & ECU > Calibration Maps > Find Maps in a Binary |  | all contexts |
| Firmware & ECU > Calibration Maps > Open Binary in Map Editor |  | all contexts |
| Firmware & ECU > Calibration Maps > Open Binary with an A2L |  | all contexts |
| Firmware & ECU > Calibration Maps > Open rusEFI / Speeduino Tune (msq + ini) |  | all contexts |
| Firmware & ECU > Analyze Firmware File |  | all contexts |
| Firmware & ECU > Compare Firmware Files |  | all contexts |
| Firmware & ECU > Create Synthetic Test Firmware |  | all contexts |
| Firmware & ECU > Firmware Converter (HEX / S-record / ELF / split / merge) |  | all contexts |
| Firmware & ECU > Getting Started |  | all contexts |
| Firmware & ECU > New ECU Project |  | all contexts |
| Firmware & ECU > New ECU Project (Demo Firmware) |  | all contexts |
| Firmware & ECU > Open EEPROM Dump (read-only) |  | all contexts |
| Firmware & ECU > Open Firmware in Workbench |  | all contexts |
| Image Editor > Add to Project Resources |  | all contexts |
| Image Editor > New Icon |  | all contexts |
| Image Editor > New Image |  | all contexts |
| Image Editor > Open Image |  | all contexts |
| Image Editor > Set as Application Icon |  | all contexts |
| Image Editor > Set as Form Icon |  | all contexts |
| Keymap > Emacs (basic) |  | all contexts |
| Keymap > VS Code |  | all contexts |
| Keymap > Vim |  | all contexts |
| Keymap > Visual Studio |  | all contexts |
| Language > English |  | all contexts |
| Language > العربية |  | all contexts |
| Macros > Macro Explorer |  | all contexts |
| Macros > Record Temporary Macro / Stop | Ctrl+Shift+R | all contexts |
| Macros > Run Temporary Macro | Ctrl+Alt+Shift+P | all contexts |
| Macros > Save Temporary Macro |  | all contexts |
| NuGet Package Manager > Manage NuGet Packages for Solution |  | all contexts |
| NuGet Package Manager > Package Manager Console |  | all contexts |
| NuGet Package Manager > Package Manager Settings |  | all contexts |
| Retro > Apollo AGC > Assembly Listing |  | all contexts |
| Retro > Apollo AGC > Build with yaYUL |  | all contexts |
| Retro > Apollo AGC > DSKY Panel |  | all contexts |
| Retro > Apollo AGC > DSKY Verbs, Nouns and Programs |  | all contexts |
| Retro > Apollo AGC > Open Apollo Source |  | all contexts |
| Retro > Apollo AGC > Virtual AGC Toolchain |  | all contexts |
| Retro > DOS Programming > Build DOS Program |  | all contexts |
| Retro > DOS Programming > DOS Interrupt Reference |  | all contexts |
| Retro > DOS Programming > DOS Project Settings |  | all contexts |
| Retro > DOS Programming > DOS Toolchains |  | all contexts |
| Retro > DOS Programming > Open Symbol Map |  | all contexts |
| Retro > DOS Programming > Run in DOSBox-X |  | all contexts |
| Retro > DOS Programming > Run in DOSBox-X Debugger |  | all contexts |
| Retro > DOS Programming > Run in My QBasic |  | all contexts |
| Retro > DOS Programming > Run with Captured Output |  | all contexts |
| Retro > DOS Programming > Show Last DOS Screen |  | all contexts |
| Retro > Game Designers > New Atari 2600 Screen |  | all contexts |
| Retro > Game Designers > New DOS Mode 13h Screen |  | all contexts |
| Retro > Game Designers > New Design for This Project |  | all contexts |
| Retro > Game Designers > New Game Boy Map |  | all contexts |
| Retro > Game Designers > New NES Screen / Level |  | all contexts |
| Retro > Game Designers > Open Game Design |  | all contexts |
| Retro > Graphics & Text > Atari 2600 Playfield Editor |  | all contexts |
| Retro > Graphics & Text > New Text Table |  | all contexts |
| Retro > Graphics & Text > New Tile Sheet (8 KB CHR) |  | all contexts |
| Retro > Graphics & Text > Script Dump / Insert |  | all contexts |
| Retro > Graphics & Text > Text Table Editor (.tbl) |  | all contexts |
| Retro > Graphics & Text > Tile Editor (Open ROM / Binary) |  | all contexts |
| Retro > Graphics & Text > Tile Map Editor |  | all contexts |
| Retro > Graphics & Text > View Current File as Tiles |  | all contexts |
| Retro > Legacy Fortran > Card Deck View |  | all contexts |
| Retro > Legacy Fortran > Compiler Preset |  | all contexts |
| Retro > Legacy Fortran > Convert to Free Form |  | all contexts |
| Retro > Legacy Fortran > Explain Legacy Constructs |  | all contexts |
| Retro > ROM Workbench > Apply Patch |  | all contexts |
| Retro > ROM Workbench > Compare Files |  | all contexts |
| Retro > ROM Workbench > Create Patch (IPS / BPS / UPS) |  | all contexts |
| Retro > ROM Workbench > Fix Header Checksum of a File |  | all contexts |
| Retro > ROM Workbench > Open in Hex Editor |  | all contexts |
| Retro > ROM Workbench > ROM Info |  | all contexts |
| Retro > Retro Development > Disassemble ROM into Project |  | all contexts |
| Retro > Retro Development > Import Labels into Hints |  | all contexts |
| Retro > Retro Development > Re-disassemble with Hints |  | all contexts |
| Retro > Retro Development > Rebuild Check (compare with the original) |  | all contexts |
| Retro > Retro Development > Retro Toolchains |  | all contexts |
| Retro > Text-Mode (DOS) > Build & Run in DOSBox-X |  | all contexts |
| Retro > Text-Mode (DOS) > Generate Code |  | all contexts |
| Retro > Text-Mode (DOS) > New ANSI Art |  | all contexts |
| Retro > Text-Mode (DOS) > New Text-Mode Screen |  | all contexts |
| Retro > Text-Mode (DOS) > Open Screen or Art |  | all contexts |
| Retro > Text-Mode (DOS) > Test Run (simulator) |  | all contexts |
| Retro > Text-Mode (DOS) > Use Current Art as Splash Screen |  | all contexts |
| Retro > Text-Mode (DOS) > View Code |  | all contexts |
| Retro > Debug ROM in Emulator |  | all contexts |
| Retro > Emulators |  | all contexts |
| Retro > Reload ROM in Emulator | Ctrl+Alt+Shift+F5 | all contexts |
| Retro > Run ROM in Emulator |  | all contexts |
| AI Settings |  | all contexts |
| Accessibility Check |  | all contexts |
| Ask AI about the Selection |  | all contexts |
| Assembly Toolchains |  | all contexts |
| Car Diagnostics |  | all contexts |
| Car Fault Guide |  | all contexts |
| Car Service Functions |  | all contexts |
| Code Snippets Manager |  | all contexts |
| Deploy to Cloud / Git / SSH |  | all contexts |
| Extensions |  | all contexts |
| Install Extension from VSIX |  | all contexts |
| Install Web Language Servers (HTML/CSS/JSON/PHP/JS/TS) |  | all contexts |
| Interpreter Path |  | all contexts |
| Language Servers and Debuggers |  | all contexts |
| Options |  | all contexts |
| PE / MFC Resource Workbench |  | all contexts |
| PHP Versions |  | all contexts |
| REST Client | Ctrl+Alt+K | all contexts |
| Rust Settings |  | all contexts |
| VS Code Extensions (Open VSX) |  | all contexts |

## View

| Item | Shortcut | Where |
|---|---|---|
| Extension Views > Claude Code |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Layout > Agent |  | all contexts |
| Layout > Next Layout |  | all contexts |
| Layout > Reset Current Layout |  | all contexts |
| Layout > Toggle Panel | Ctrl+J | all contexts |
| Layout > Toggle Side Bar | Ctrl+B | all contexts |
| Layout > VS Code |  | all contexts |
| Layout > Visual Studio |  | all contexts |
| Layout > Zen Mode |  | all contexts |
| Zoom > 100% |  | all contexts |
| Zoom > 150% |  | all contexts |
| Zoom > 200% |  | all contexts |
| Zoom > 300% |  | all contexts |
| Zoom > 400% |  | all contexts |
| Zoom > 50% |  | all contexts |
| Zoom > 75% |  | all contexts |
| Zoom > Zoom In  (Ctrl+Wheel) |  | all contexts |
| Zoom > Zoom Out |  | all contexts |
| 8086 Emulator |  | all contexts |
| AI Chat | Ctrl+Alt+I | all contexts |
| AI Web Chats | Ctrl+Alt+W | all contexts |
| AI Web Chats (dock) |  | all contexts |
| Agent Manager | Ctrl+Alt+M | all contexts |
| Animations |  | all contexts |
| Call Stack |  | all contexts |
| Code | F7 | all contexts |
| CodeIgniter Panel (Spark, Routes) |  | all contexts |
| Command Palette | Ctrl+Shift+P | all contexts |
| Data |  | all contexts |
| Data Sources |  | all contexts |
| Databases | Ctrl+Alt+D | all contexts |
| Design | Ctrl+Shift+D | all contexts |
| Designer | Shift+F7 | all contexts |
| Django / Flask / FastAPI Panel |  | asm, csharp, dos, firmware, flutter, game, none, python-tk, retro, vb6, web |
| Document Outline |  | all contexts |
| Error List |  | all contexts |
| Extension Output |  | csharp, dos, firmware, flask, flutter, none, python-tk, retro, vb6, web |
| Extensions (VS Code) | Ctrl+Shift+X | all contexts |
| Find All References Window |  | all contexts |
| Find Results |  | all contexts |
| Flask |  | flask |
| Framework Tools |  | all contexts |
| Git Changes | Ctrl+Alt+G | all contexts |
| Immediate |  | all contexts |
| Laravel Panel (Artisan, Routes, Tinker) |  | all contexts |
| Locals |  | all contexts |
| New Agent Task |  | all contexts |
| Notebook Variables |  | all contexts |
| Object Browser | Ctrl+Alt+J | all contexts |
| Objects and Timeline |  | all contexts |
| Output |  | all contexts |
| Package Manager Console |  | all contexts |
| Preview |  | all contexts |
| Problems Explained |  | all contexts |
| Properties |  | all contexts |
| Quick Open (Go to File) | Ctrl+P | all contexts |
| Rails Panel (Console, Routes, Models) |  | all contexts |
| Remote Explorer |  | all contexts |
| Requests |  | all contexts |
| Retro Debugger |  | all contexts |
| Sizes |  | all contexts |
| Solution Explorer |  | all contexts |
| States |  | all contexts |
| Tab Order |  | all contexts |
| Terminal | Ctrl+` | all contexts |
| Toolbox |  | all contexts |

## Window

| Item | Shortcut | Where |
|---|---|---|
| Auto Hide |  | all contexts |
| Auto Hide All |  | all contexts |
| Remove Split |  | all contexts |
| Split Editor Down |  | all contexts |
| Split Editor Right |  | all contexts |

## pygame

| Item | Shortcut | Where |
|---|---|---|
| Build EXE / Installer |  | game |
| Build One-File EXE (PyInstaller) |  | game |
| Export to Godot |  | game |
| Install pygame |  | game |
| Run Game |  | game |
| Stop Running Command |  | game |

## Docks / tool windows

| Title | Widget | Layouts |
|---|---|---|
| AI Chat | ChatPanel | agent,vs,vscode |
| AI Web Chats | WebChatPanel | agent,vs,vscode |
| Agent Manager | AgentManagerWidget | agent,vs,vscode |
| Animations | QScrollArea | agent,vs,vscode |
| CPU | CpuView | agent,vs,vscode |
| Call Stack |  | agent,vs,vscode |
| Checksum Report | QWidget | agent,vs,vscode |
| Claude Code |  | agent,vscode |
| CodeIgniter | CodeIgniterPanel | agent,vs,vscode |
| Data | QScrollArea | agent,vs,vscode |
| Data Sources | QScrollArea | agent,vs,vscode |
| Databases | DatabasesPanel | agent,vs,vscode |
| Differences | QWidget | agent,vs,vscode |
| Disassembly | DisassemblyView | agent,vs,vscode |
| Docker | DockerPanel | agent,vs,vscode |
| Document Outline | QStackedWidget | agent,vs,vscode |
| Error List | QTreeWidget | agent,vs,vscode |
| Extension Output | OutputPanel | agent,vs,vscode |
| Extensions | ExtensionsView | agent,vs,vscode |
| Find Results | QTreeWidget | agent,vs,vscode |
| Flask | PyWebPanel | agent,vs,vscode |
| Framework | FrameworkPanel | agent,vs,vscode |
| Game Assets | AssetBrowser | agent,vs,vscode |
| Git Changes | QScrollArea | agent,vs,vscode |
| Immediate | ImmediateWindow | agent,vs,vscode |
| Laravel | LaravelPanel | agent,vs,vscode |
| Live Share | LiveSharePanel | agent,vs,vscode |
| Locals | QTreeWidget | agent,vs,vscode |
| Memory 1 | MemoryView | agent,vs,vscode |
| Notebook Variables | QWidget | agent,vs,vscode |
| Objects and Timeline | QScrollArea | agent,vs,vscode |
| Output | QPlainTextEdit | agent,vs,vscode |
| Potential Maps | QWidget | agent,vs,vscode |
| Preview | PreviewPane | agent,vs,vscode |
| Project | QTreeWidget | agent,vs,vscode |
| Properties | PropertiesPanel | agent,vs,vscode |
| Python Web | PyWebPanel | agent,vs,vscode |
| Rails | RailsPanel | agent,vs,vscode |
| Registers | RegistersView | agent,vs,vscode |
| Remote Explorer | RemoteExplorer | agent,vs,vscode |
| Reports | ReportsPanel | agent,vs,vscode |
| Requests | RequestsPane | agent,vs,vscode |
| Sizes | QScrollArea | agent,vs,vscode |
| Solution Explorer | QTreeWidget | agent,vs,vscode |
| Stack | StackView | agent,vs,vscode |
| States | QScrollArea | agent,vs,vscode |
| Terminal | TerminalWidget | agent,vs,vscode |
| Test Explorer | TestExplorer | agent,vs,vscode |
| Threads | QTreeWidget | agent,vs,vscode |
| Toolbox | Toolbox | agent,vs,vscode |
| Watch | QWidget | agent,vs,vscode |

## Keyboard shortcuts

| Keys | Command |
|---|---|
| `Alt+5` | Debug > Windows > Registers |
| `Alt+6` | Debug > Windows > Memory 1 |
| `Alt+8` | Debug > Windows > Disassembly |
| `Alt+C` | Debug > CPU (OllyDbg Style) |
| `Alt+F11` | Analyze > Run Code Analysis > On Solution |
| `Alt+F9` | Debug > Breakpoint Condition |
| `Alt+Shift+D` | Data > Show Data Sources |
| `Alt+Shift+F, Ctrl+K, Ctrl+D` | Edit > Format Document |
| `Ctrl+/` | QShortcut on CodeEditor |
| `Ctrl+A` | Edit > Select All |
| `Ctrl+Alt+B` | Site > Open in Browser |
| `Ctrl+Alt+D` | View > Databases |
| `Ctrl+Alt+F` | QShortcut on MainWindow |
| `Ctrl+Alt+F10` | Debug > Step Over Instruction |
| `Ctrl+Alt+F11` | Debug > Step Into Instruction |
| `Ctrl+Alt+F5` | Build > Publish / Create Installer |
| `Ctrl+Alt+G` | View > Git Changes |
| `Ctrl+Alt+H` | Git > View History (graph) |
| `Ctrl+Alt+I` | View > AI Chat |
| `Ctrl+Alt+J` | View > Object Browser |
| `Ctrl+Alt+K` | Site > REST Client |
| `Ctrl+Alt+M` | View > Agent Manager |
| `Ctrl+Alt+N` | File > New Window |
| `Ctrl+Alt+P` | Site > Publish |
| `Ctrl+Alt+R` | Debug > Mobile > Hot Reload |
| `Ctrl+Alt+Shift+B` | Git > New Branch |
| `Ctrl+Alt+Shift+D` | Toolbar Standard > Split |
| `Ctrl+Alt+Shift+F5` | Tools > Retro > Reload ROM in Emulator |
| `Ctrl+Alt+Shift+N` | File > New Project (.NET, Visual Studio 2022) |
| `Ctrl+Alt+Shift+P` | Tools > Macros > Run Temporary Macro |
| `Ctrl+Alt+Shift+R` | Debug > Mobile > Hot Restart |
| `Ctrl+Alt+W` | View > AI Web Chats |
| `Ctrl+B` | View > Layout > Toggle Side Bar |
| `Ctrl+Backtab` | QShortcut on MainWindow |
| `Ctrl+C` | Edit > Copy |
| `Ctrl+E, T` | Test > Test Explorer |
| `Ctrl+Enter` | QShortcut on QPlainTextEdit |
| `Ctrl+Esc` | QShortcut on MainWindow |
| `Ctrl+F` | Edit > Find |
| `Ctrl+F1` | Help > RAD IDE Help |
| `Ctrl+F10` | Debug > Run to Cursor |
| `Ctrl+F5` | Debug > Start Without Debugging |
| `Ctrl+F6` | QShortcut on MainWindow |
| `Ctrl+G` | Edit > Go to Line |
| `Ctrl+H` | Edit > Replace |
| `Ctrl+I` | QShortcut on CodeEditor |
| `Ctrl+J` | View > Layout > Toggle Panel |
| `Ctrl+K, Ctrl+E` | Analyze > Code Cleanup > Run Code Cleanup on Document |
| `Ctrl+K, Ctrl+O` | File > Open Folder |
| `Ctrl+O` | File > Open File |
| `Ctrl+P` | View > Quick Open (Go to File) |
| `Ctrl+R, A` | Test > Run All Tests |
| `Ctrl+R, Ctrl+G` | Analyze > Remove and Sort Usings |
| `Ctrl+R, T` | Test > Run Tests in Current File |
| `Ctrl+Return` | QShortcut on QPlainTextEdit |
| `Ctrl+S` | File > Save All |
| `Ctrl+Shift+B` | Project > Check for Errors |
| `Ctrl+Shift+D` | View > Design |
| `Ctrl+Shift+Esc` | QShortcut on MainWindow |
| `Ctrl+Shift+F` | Edit > Find in Files |
| `Ctrl+Shift+F1` | Debug > Assembly Checks > Explain This Line |
| `Ctrl+Shift+F5` | Debug > Assembly Checks > Check by Running |
| `Ctrl+Shift+N` | File > New Project |
| `Ctrl+Shift+O` | File > Open Project |
| `Ctrl+Shift+P` | View > Command Palette |
| `Ctrl+Shift+R` | Tools > Macros > Record Temporary Macro / Stop |
| `Ctrl+Shift+Space` | QShortcut on CodeEditor |
| `Ctrl+Shift+T` | QShortcut on MainWindow |
| `Ctrl+Shift+Tab` | QShortcut on MainWindow |
| `Ctrl+Shift+X` | View > Extensions (VS Code) |
| `Ctrl+Space` | QShortcut on CodeEditor |
| `Ctrl+Tab` | QShortcut on MainWindow |
| `Ctrl+V` | Edit > Paste |
| `Ctrl+X` | Edit > Cut |
| `Ctrl+Y` | Edit > Redo |
| `Ctrl+Z` | Edit > Undo |
| `Ctrl+`` | View > Terminal |
| `Del` | QShortcut on QTableWidget |
| `Esc` | QShortcut on FindBar |
| `F1` | Help > Context Help |
| `F10` | Debug > Step Over |
| `F11` | Debug > Step Into |
| `F12` | Edit > Go to Definition |
| `F3` | Edit > Find Next |
| `F5` | Debug > Start Debugging / Continue |
| `F6` | QShortcut on MainWindow |
| `F7` | View > Code |
| `F9` | Debug > Toggle Breakpoint |
| `Shift+F11` | Debug > Step Out |
| `Shift+F3` | Edit > Find Previous |
| `Shift+F5` | Debug > Stop Debugging |
| `Shift+F6` | QShortcut on MainWindow |
| `Shift+F7` | View > Designer |

## New Project languages and templates

| Language | Templates |
|---|---|
| Visual Basic > Visual Basic 6  (BASIC) (`vb-basic`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Python > Python  (Tkinter) (`python-tk`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Python > Python  (PySide6 / Qt) (`python-qt`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Ring > Ring  (RingQt) (`ring-qt`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Ring > Ring  (Console / Web / Library) (`ring-app`) | Console Application (Ring), Web Application (Ring HTTPLib), Ring Library, WebLib Page Generator (Ring) |
| .NET > C#  (GUI Bridge, .NET) (`csharp-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| .NET > PowerShell  (GUI Bridge) (`powershell-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Java > Java  (GUI Bridge, JDK) (`java-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Web > PHP Web Site (`php-web`) | PHP Empty Site, PHP Starter Site, PHP + SQLite Data App, Laravel App, Laravel API, WordPress, CodeIgniter 4 App |
| Web > HTML / CSS / JavaScript Site (`static-web`) | HTML Bootstrap Site, HTML Empty Site |
| Web > Node.js Web Site  (Express) (`node-web`) | Node.js Empty Site, Node.js Express Site, React (Vite), React + TypeScript (Vite), Vue (Vite), Svelte (Vite), Vanilla JavaScript (Vite), Angular |
| Web > Django  (Python) (`python-django`) | Django App |
| Web > Flask  (Python) (`python-flask`) | Flask App |
| Web > FastAPI  (Python) (`python-fastapi`) | FastAPI App |
| Web > ASP.NET Core Web App (`aspnet-web`) | ASP.NET Core MVC, ASP.NET Core Razor Pages, ASP.NET Core Web API, ASP.NET Core Empty |
| Web > Spring Boot Web App  (Java) (`spring-web`) | Spring Boot MVC + Thymeleaf, Spring Boot REST API |
| Web > Ruby on Rails / Sinatra Web App (`rails-web`) | Ruby on Rails App, Sinatra App (pure Ruby) |
| Web > NestJS Web App  (TypeScript) (`nestjs-web`) | NestJS App, NestJS (nest new) |
| Web & Script > JavaScript  (GUI Bridge, Node.js) (`javascript`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Web & Script > TypeScript  (GUI Bridge, Node.js) (`typescript`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Web & Script > PHP  (GUI Bridge) (`php`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Native > C  (GUI Bridge, gcc / MSVC) (`c-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Native > C++  (GUI Bridge, g++ / MSVC) (`cpp-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Native > Rust  (GUI Bridge, cargo) (`rust-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Native > Rust  (Cargo) (`rust-cargo`) | Console App, Library, GUI App (RAD form), egui Desktop App, Workspace |
| Native > Fortran  (GUI Bridge, gfortran) (`fortran-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Native > Go  (GUI Bridge) (`go-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Assembly > Assembly  (NASM) (`asm-nasm`) | Assembly Console (x64 Windows, NASM), Assembly Console (x86 Windows, NASM), Win32 API (x64, NASM), Assembly Windows Forms (NASM + GUI Bridge), Assembly Class Library (x64 DLL, NASM), Assembly Windows Forms (x86, NASM + GUI Bridge) |
| Assembly > Assembly  (FASM) (`asm-fasm`) | FASM Console (x64), FASM Console (x86), FASM Windows Forms (x64, GUI Bridge) |
| Assembly > Assembly  (MASM) (`asm-masm`) | MASM Console (x64), MASM Console (x86) |
| Assembly > Assembly  (GNU as) (`asm-gas`) | GNU as Console (x64, AT&T syntax), GNU as Console (x64, Intel syntax), GNU as Windows Forms (x64, AT&T syntax, GUI Bridge), GNU as Windows Forms (x64, Intel syntax, GUI Bridge) |
| Assembly > 8086 Assembly  (Emulator) (`emu8086`) | COM Program (org 100h), EXE Program (.model small), Using emu8086.inc, Text-Mode Colours, Keyboard Game |
| Scripting > Lua  (GUI Bridge) (`lua-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Scripting > Ruby  (GUI Bridge) (`ruby-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Scripting > Perl  (GUI Bridge) (`perl-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Scripting > Dart  (GUI Bridge) (`dart-bridge`) | Windows Application, Dialog Application, Data Entry Form, Console Application, Class Library |
| Mobile > Flutter  (Dart mobile app) (`flutter`) | Flutter App, Flutter App (tabs + drawer), Flutter App (visual designer) |
| Mobile > Python Kivy  (mobile app) (`kivy`) | Python Kivy App |
| Mobile > React Native  (Expo mobile app) (`expo`) | React Native (Expo) App |
| Games > Python Game  (pygame) (`pygame`) | Platformer, Top-down Game, Empty Game |
| Games > Godot 4  (GDScript) (`godot`) | Platformer (Godot), Top-down Game (Godot), Empty Godot 2D |
| Games > HTML5 Canvas Game  (JavaScript) (`html5-game`) | Platformer (HTML5), Top-down Game (HTML5), Empty Game (HTML5) |
| Games > Python Arcade  (arcade library) (`python-arcade`) | Arcade Platformer, Arcade Empty Window |
| Games > Ring Game  (RingRayLib) (`ring-game`) | Platformer (Ring), Top-down Game (Ring), Empty Game (Ring) |
| Games > Python 3D  (Ursina) (`python-ursina`) | Ursina 3D Playground, Ursina Empty 3D Scene |
| Games > Godot 3D  (GDScript) (`godot3d`) | Godot 3D Playground, Godot Empty 3D Scene |
| Retro Games > Atari 2600  (DASM) (`retro-atari2600`) | Atari 2600 Game (DASM) |
| Retro Games > NES  (cc65 / ca65) (`retro-nes`) | NES Game (ca65 assembly), NES Game (cc65 C) |
| Retro Games > Game Boy  (RGBDS) (`retro-gameboy`) | Game Boy Game (RGBDS) |
| Retro Games > Commodore 64  (cc65 / ACME) (`retro-c64`) | Commodore 64 (ca65 assembly), Commodore 64 (cc65 C), Commodore 64 (ACME) |
| Retro Games > ZX Spectrum  (sjasmplus) (`retro-zx`) | ZX Spectrum (sjasmplus) |
| Retro > DOS Program  (DOSBox-X) (`retro-dos`) | Existing DOS Program, DOS .COM in Assembly (NASM) |
| Retro > ROM Hacking Project (`retro-romhack`) | ROM Hacking Project, ROM Hacking Project (Demo ROM) |
| DOS > QBasic / QuickBASIC  (DOS) (`dos-qbasic`) | Hello (QBasic), Text-Mode Menu, Mode 13h Graphics, PC Speaker Music, Mouse Painting, Line-Numbered BASIC |
| DOS > Turbo Pascal-style  (DOS) (`dos-pascal`) | Hello (Turbo Pascal style), Text-Mode Menu, Mode 13h Graphics, PC Speaker Music, Mouse (INT 33h) |
| DOS > Turbo C-style  (DOS) (`dos-c`) | Hello (Turbo C style), Text-Mode Menu, Mode 13h Graphics, PC Speaker Music, Mouse (INT 33h), BGI Graphics (initgraph) |
| DOS > DOS Assembly  (16-bit MASM) (`dos-asm`) | Hello (.EXE, .model small), Tiny .COM Program, Text-Mode Menu, Mode 13h Graphics, PC Speaker Music, Mouse (INT 33h) |
| DOS > DOS Batch  (.BAT) (`dos-batch`) | Hello (Batch), CHOICE Menu, Program Launcher |
| DOS > DOS Text-Mode Forms App (`dos-tuiforms`) | Forms App - QBasic / FreeBASIC, Forms App - Pascal (Crt), Forms App - C (OpenWatcom / Turbo C), Forms App - 16-bit Assembly (.COM), Forms App - QuickBASIC 4.5 (your own copy), Forms App - QBasic 1.1 (keyboard only) |
| Space & Science > Apollo AGC Program  (yaYUL) (`agc-yul`) | Hello DSKY (clock + keyboard), Empty AGC Program |
| Space & Science > Fortran 66/77  (fixed form, gfortran -std=legacy) (`fortran-legacy`) | Orbit Table (Fortran 66), Hello, Fortran 77 |
| Firmware > ECU / Firmware Project (`firmware-ecu`) | ECU / Firmware Project, ECU Project (Demo Firmware) |
| Firmware > Firmware / ECU Analysis (`firmware-analysis`) | Firmware / ECU Analysis, Firmware Analysis (Synthetic ARM Image) |

## Options pages

* **Environment**: Color theme:; Workbench layout:; Menu and window font size:; Language:; Start-up and closing; Show the Start Page on startup; Reopen the last solution on startup; Ask before closing with unsaved changes (otherwise they are saved); Backups; Auto-save backup every:; Windows integration; Open files in the running RAD IDE window; File associations for RAD IDE files (.radsln, .radproj, .form ); "Open with" RAD IDE for source and text files; Explorer context menus (Open with RAD IDE, Open folder in RAD IDE); Start Menu shortcut; Desktop shortcut; Status: registered for another location - click Register again.; Register; Unregister
* **Text Editor**: Font:; Size:; Tab / indent width:; Preview:; def Form1_Load(self):
    return 42  # sample
* **Windows Forms Designer**: Grid size:; Snap controls to the grid
* **Languages**: 8086 Assembly (Emulator); ASP.NET Core Web App; Apollo AGC Program (yaYUL); Assembly (FASM); Assembly (GNU as); Assembly (MASM); Assembly (NASM); Atari 2600 (DASM); C (GUI Bridge, gcc / MSVC); C# (GUI Bridge, .NET); C++ (GUI Bridge, g++ / MSVC); Commodore 64 (cc65 / ACME); DOS Assembly (16-bit MASM); DOS Batch (.BAT); DOS Program (DOSBox-X); DOS Text-Mode Forms App; Dart (GUI Bridge); Django (Python); ECU / Firmware Project; FastAPI (Python); Firmware / ECU Analysis; Flask (Python); Flutter (Dart mobile app); Fortran (GUI Bridge, gfortran); Fortran 66/77 (fixed form, gfortran -std=legacy); Game Boy (RGBDS); Go (GUI Bridge); Godot 3D (GDScript); Godot 4 (GDScript); HTML / CSS / JavaScript Site; HTML5 Canvas Game (JavaScript); Java (GUI Bridge, JDK); JavaScript (GUI Bridge, Node.js); Lua (GUI Bridge); NES (cc65 / ca65); NestJS Web App (TypeScript); Node.js Web Site (Express); PHP (GUI Bridge); PHP Web Site; Perl (GUI Bridge) ...
* **VS Code Extensions**: File icon theme:; Extension settings; claudeCode.allowDangerouslySkipPermissions; Allow bypass permissions mode. Recommended only for sandboxes with no internet access.; claudeCode.archiveInactiveSessions; claudeCode.attachOpenFile; claudeCode.attachSelection; claudeCode.autosave; Automatically save files before Claude reads or writes them.; claudeCode.claudeProcessWrapper; Executable path used to launch the Claude process.; claudeCode.contextUsageThreshold; claudeCode.continueAfterReload; claudeCode.disableLoginPrompt; claudeCode.enableNewConversationShortcut; Use the Cmd/Ctrl+N keyboard shortcut to start a new conversation when Claude is focused.; claudeCode.enableReopenClosedSessionShortcut; claudeCode.environmentVariables; claudeCode.escapeStopsClaude; claudeCode.focusView; claudeCode.hideOnboarding; Hide the onboarding checklist in Claude Code.; claudeCode.initialPermissionMode; claudeCode.lockEditorGroups; claudeCode.pinPrompt; claudeCode.preferredLocation; claudeCode.promptSuggestions; claudeCode.respectGitIgnore; claudeCode.scrollToBottomOnSend; claudeCode.showMessageTimestamps; Show when each message was sent. A date line marks where the day changes.; claudeCode.spinnerVerbs; claudeCode.useCtrlEnterToSend; claudeCode.usePythonEnvironment; claudeCode.useTerminal; Launch Claude in the terminal instead of the native UI.
* **AI**: Claude Code (claude); Claude Code with your Claude Pro/Max subscription (no API key).; Status: checking; Use this provider (automatic defaults, pickers); API key:; show; Remove key; Base URL:; Program:; Model:; Let thinking models think (slower, Ollama 'think'); Test; Install with npm; Sign in; Pull model; Refresh; Default provider for each purpose; Chat:; Inline completion:; Inline edit (Ctrl+I):; Agents:; Commit messages:
* **Keyboard**: Editor keymap:
* **Formatting**: Format the document when it is saved (Format on Save); Install Prettier
* **NuGet Package Manager**: Available package sources:; +; ✕; ▲; ▼; Machine-wide package sources:; Name:; Source:; Update; Package Restore; Allow NuGet to download missing packages; Automatically check for missing packages during build; Binding Redirects; Skip applying binding redirects; Package Management; Default package management format:; Allow format selection on first package install; Clear All NuGet Storage
* **Web**: Debug JavaScript in the Preview (F9 in .js files of a web site)

## Publish (desktop installer)

Dialog `PublishDialog` 'Publish EvDemo'.

* tabs: ['Application', 'Setup', 'Signing and Updates']
* combos: ['Current user only (no administrator rights needed)', 'All users (asks for administrator rights)']; ["Automatic (from the startup form's language)", 'Python program (PyInstaller)', 'VB6 / BASIC program', 'GUI Bridge language (C, C#, Java, Go, ...)', 'Ring program (ring2exe)', 'Flutter Windows app', 'An already built program folder']; ['Standalone - one exe, nothing to install (largest)', 'Small - needs the .NET Desktop Runtime', 'Tiny - for the .NET Framework 4.8 of Windows']
* checks: Sign the program and the setup with signtool; The program checks a version.json on the web for a newer version; Check when the program starts; Desktop shortcut (the user can untick it); Start menu shortcut + uninstall shortcut; Offer to start the program at the end of the setup; Make the setup (uncheck to build the program folder only); Also make a portable .zip of the program; Show a console window (command-line programs)

## Publish (web site)

Dialog `PublishDialog` 'Publish - EvDemo'.

* tabs: ['FTP / SFTP / Folder', 'Cloud / Git / SSH']
* combos: ['FTP', 'FTPS (explicit TLS)', 'SFTP (SSH)', 'Local folder / network share']
* checks: Upload all files; Save password; Passive mode; Verify the server certificate; Delete remote files that were removed locally

## Dialog classes

| Class | Module | Title |
|---|---|---|
| DiffReview | `radide.ai.diffview` |  |
| MultiDiffReview | `radide.ai.diffview` |  |
| AssembleDialog | `radide.asm_intel.cpuview.panes` |  |
| ResultsDialog | `radide.asm_intel.cpuview.panes` |  |
| ConnectDialog | `radide.cardiag.link.qt` | Connect to Car |
| FindEcusDialog | `radide.cardiag.link.qt` | Find Control Units |
| ChooseItemsDialog | `radide.components.ui` | Choose Toolbox Items |
| ComponentManagerDialog | `radide.components.ui` | Component Packages |
| AddItemDialog | `radide.dialogs` |  |
| NewProjectDialog | `radide.dialogs` | New Project |
| ReferenceManager | `radide.dotnet.refs.manager` | Reference Manager -  |
| AddNewProject | `radide.dotnet.sln.dialogs` | Add a new project |
| ConfigurationManager | `radide.dotnet.sln.dialogs` | Configuration Manager |
| ImportSolution | `radide.dotnet.sln.dialogs` | Add Projects from  |
| NewSolutionFromFolders | `radide.dotnet.sln.dialogs` | New Solution from Existing Folders |
| ProjectDependencies | `radide.dotnet.sln.dialogs` | Project Dependencies |
| PublishDialog | `radide.dotnet.sln.dialogs` | Publish -  |
| SolutionPropertyPages | `radide.dotnet.sln.dialogs` | Solution '' Property Pages |
| LaunchProfilesDialog | `radide.dotnet.sln.properties` | Launch Profiles |
| NewProjectWizard | `radide.dotnet.templates.wizard` |  |
| EditorConfigDialog | `radide.dotnet.tools.ui` | Configure Code Analysis - .editorconfig |
| GenerateFormDialog | `radide.features.ai_editor` |  |
| HandlerDialog | `radide.features.ai_editor` | Generate Event Handler -  |
| ResultDialog | `radide.features.ai_editor` |  |
| CodeBlockDialog | `radide.features.ai_web` | Code from the web chat |
| DiffDialog | `radide.features.ai_web` | Apply to  |
| PopupWindow | `radide.features.ai_web` |  |
| AppGalleryDialog | `radide.features.app_gallery` | App Gallery |
| AsmToolchainsDialog | `radide.features.asm_build_ui` | Assembly Toolchains |
| RulesDialog | `radide.features.asm_smart_lint` |  |
| ClearCodesDialog | `radide.features.cardiag_scan` |  |
| DatabaseChoice | `radide.features.codeigniter_ide` | CodeIgniter 4 App - database |
| SparkForm | `radide.features.codeigniter_ide` | php spark  |
| AddDataSourceDialog | `radide.features.data_sources` | Add New Data Source |
| ConfigureDialog | `radide.features.data_sources` | Configure  |
| PreviewDialog | `radide.features.data_sources` |  |
| AddColumnDialog | `radide.features.databases` | Add Column -  |
| ConnectionDialog | `radide.features.databases` | Database Connection |
| CreateTableDialog | `radide.features.databases` | New Table |
| ImportCsvDialog | `radide.features.databases` | Import CSV |
| RowDialog | `radide.features.databases` |  |
| AttachDialog | `radide.features.debug_views` | Attach to Process |
| BreakpointDialog | `radide.features.debug_views` | Breakpoint Settings - line  |
| CloudDeployDialog | `radide.features.docker_cloud` | Deploy -  |
| DockerGenerateDialog | `radide.features.docker_cloud` | Generate Docker Files |
| DosScreenDialog | `radide.features.dos_ide` | Last DOS Screen |
| DosSettingsDialog | `radide.features.dos_ide` | DOS Project Settings |
| DosToolchainsDialog | `radide.features.dos_ide` | DOS Toolchains |
| InterruptReference | `radide.features.dos_ide` | DOS Interrupt Reference |
| MacroExplorer | `radide.features.editor_extras` | Macro Explorer |
| SnippetsDialog | `radide.features.editor_extras` | Code Snippets Manager |
| ExampleGallery | `radide.features.example_gallery` |  |
| ExeImportWizard | `radide.features.exe_import` | Import Program (.exe / .dll) |
| ExtensionsDialog | `radide.features.extensions` | Extensions |
| NewScreenDialog | `radide.features.flutter_designer` | Add New Screen |
| BlameDialog | `radide.features.git_full` | Blame -  |
| CompareDialog | `radide.features.git_full` | Compare -  |
| GitignoreDialog | `radide.features.git_full` | .gitignore |
| MergeResolver | `radide.features.git_full` | Merge -  |
| HelpViewer | `radide.features.help` | RAD IDE Help |
| PublishDialog | `radide.features.installer` | Publish  |
| LanguageServersDialog | `radide.features.language_servers` | Language Servers and Debuggers |
| JoinDialog | `radide.features.live_share` | Join Collaboration Session |
| StartDialog | `radide.features.live_share` | Start Collaboration Session |
| MigrateWizard | `radide.features.migrate_wizard` | Migrate Project |
| DetectDialog | `radide.features.open_detect` | Detect Project Type |
| PackagesDialog | `radide.features.packages` | Manage Packages -  |
| LaravelOptionsDialog | `radide.features.php_frameworks` |  |
| PhpVersionsDialog | `radide.features.php_tools` | PHP Versions |
| CredentialsDialog | `radide.features.python_web` |  |
| RailsOptionsDialog | `radide.features.rails_ide` | New Ruby on Rails App |
| ChangesPreview | `radide.features.refactor` |  |
| SSHDialog | `radide.features.remote` | Connect to SSH Host |
| DisassembleDialog | `radide.features.retro_dev` |  |
| RetroToolchainsDialog | `radide.features.retro_dev` |  |
| RustSettingsDialog | `radide.features.rust_ide` | Rust Settings |
| OptionsDialog | `radide.features.settings` | Options |
| AddReferenceDialog | `radide.features.solution_ui` | Reference Manager -  |
| UserControlDialog | `radide.features.user_controls` | User Control Properties and Events -  |
| NewFrontendDialog | `radide.features.web_extras` | New Front-end App |
| PublishDialog | `radide.features.web_tools` | Publish -  |
| NewFileDialog | `radide.features.web_workspace` | New File |
| FirmwareConverterDialog | `radide.firmware.analysis.convert_dialog` | Firmware Converter |
| BlockEditor | `radide.firmware.checksum.ui` | Checksum Block |
| ChecksumDialog | `radide.firmware.checksum.ui` |  |
| ImportOptionsDialog | `radide.firmware.maps.dialogs` |  |
| MapPropertiesDialog | `radide.firmware.maps.dialogs` | Map Properties |
| BuildSettingsDialog | `radide.firmware.project.ui` | ECU Build Settings |
| VersionsDialog | `radide.firmware.project.ui` | Versions -  |
| AssetManagerDialog | `radide.flutterdesign.asset_dialogs` | Project Assets |
| FontPickerDialog | `radide.flutterdesign.asset_dialogs` | Google Fonts |
| ThemeEditorDialog | `radide.flutterdesign.asset_dialogs` | App Theme |
| IconPickerDialog | `radide.flutterdesign.inspector` | Choose an icon |
| KeyframesDialog | `radide.flutterdesign.motion_ui` | Keyframes |
| RowsDialog | `radide.flutterdesign.motion_ui` |  |
| SideBySide | `radide.flutterdesign.motion_ui` | Side-by-side |
| WhenDialog | `radide.flutterdesign.motion_ui` | Animate  |
| SpriteSheetDialog | `radide.games.animation_editor` | Sprite Sheet and Animations |
| TerrainsDialogQt | `radide.games.autotile` | Terrains (auto-tiling) |
| ParticleEditor | `radide.games.particles` | Particle Editor |
| TilesetDialog | `radide.games.tiles` | Import Tileset |
| NewImageDialog | `radide.imaging.editor` | New Image |
| SelectResourceDialog | `radide.imaging.resource_editor` | Select Resource |
| MenuEditor | `radide.menu_editor` |  |
| EditInstructionDialog | `radide.pe.ui` | Edit Instruction |
| FunctionPicker | `radide.pe.ui` |  |
| _AskDialog | `radide.project_actions` |  |
| AddReportDialog | `radide.reports.designer` | Add Report |
| DataSourceDialog | `radide.reports.designer` | Report Data Source |
| GroupsDialog | `radide.reports.designer` | Report Groups |
| ParametersDialog | `radide.reports.designer` | Report Parameters |
| NESPaletteDialog | `radide.retro.design.game.ui` | NES Palettes |
| PixelEditor | `radide.retro.design.game.ui` |  |
| SauceDialog | `radide.retro.design.textmode.ansieditor` | Art Properties (SAUCE) |
| CharPickerDialog | `radide.retro.design.textmode.designer` | Character |
| ItemsDialog | `radide.retro.design.textmode.designer` | List Items |
| MenuEditorDialog | `radide.retro.design.textmode.designer` | Menu Editor |
| TestRunDialog | `radide.retro.design.textmode.designer` |  |
| DosSettingsDialog | `radide.retro.emu.ui` | DOS Settings |
| EmulatorManager | `radide.retro.emu.ui` | Retro Emulators |
| SystemPaletteDialog | `radide.retro.gfx.ui_common` | Choose Color |
| BinaryDialog | `radide.retro.gfx.ui_playfield` |  |
| CompressedDialog | `radide.retro.gfx.ui_romgfx` |  |
| RomPaletteDialog | `radide.retro.gfx.ui_romgfx` |  |
| TilesetDialog | `radide.retro.gfx.ui_tilemap` | Tile Set |
| ApplyPatchDialog | `radide.retro.rom.dialogs` | Apply Patch |
| CreatePatchDialog | `radide.retro.rom.dialogs` | Create Patch |
| GotoDialog | `radide.retro.rom.dialogs` | Go To Offset |
| FindInFilesDialog | `radide.tools` | Find and Replace |
| InputDialog | `radide.vsx.host_ide` |  |
| QuickPickDialog | `radide.vsx.host_ide` |  |
| KeyboardShortcutsPage | `radide.vsx.settings_ui` | Keyboard Shortcuts |
| SettingsPage | `radide.vsx.settings_ui` | Settings |
| RelationDialog | `radide.web_site.db_diagram` | New Relationship (Foreign Key) |
| SqlPreviewDialog | `radide.web_site.db_diagram` |  |
| CodeBlockDialog | `radide.web_site.design` | Edit code block |
| EnvironmentDialog | `radide.web_site.rest_client` | REST Client Environments |
