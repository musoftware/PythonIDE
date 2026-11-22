# RAD IDE feature inventory

Generated 2026-11-22 14:54 by `tools/feature_inventory.py` from a running IDE (offscreen) - do not edit. Traceability to tests: [TEST_MATRIX.md](TEST_MATRIX.md).

**790** distinct entry points (menu / tool bar / palette / context-menu items), **46** docks / tool windows, **89** keyboard shortcuts, **137** dialog classes, **0** New Project languages with **0** templates, **0** Options pages.

Contexts (a sandbox copy of each project, opened in every layout VS / VS Code / Agent):

* `none` - no project open (Start Page)
* `firmware` - firmware ECU project (created by the firmware-ecu plugin)

Contexts that failed: `firmware` (worker failed (see log))

## Entry points per area

| Area | Entries |
|---|---|
| Analyze | 11 |
| Build | 17 |
| Command Palette | 83 |
| Context menu: Databases (QTreeWidget) | 11 |
| Context menu: Editor tab | 3 |
| Context menu: Toolbox (Toolbox) | 5 |
| Data | 4 |
| Debug | 42 |
| Edit | 36 |
| File | 41 |
| Format | 25 |
| Git | 31 |
| Help | 58 |
| Menu bar corner | 3 |
| Project | 57 |
| Share | 8 |
| Site | 36 |
| Test | 9 |
| Toolbar Activity Bar | 19 |
| Toolbar Debug | 4 |
| Toolbar Expo | 5 |
| Toolbar Mobile | 5 |
| Toolbar Retro Emulator | 2 |
| Toolbar Rust | 5 |
| Toolbar Solution Configurations | 2 |
| Toolbar Standard | 9 |
| Toolbar Toolbar | 35 |
| Tools | 154 |
| View | 65 |
| Window | 5 |

## Analyze

| Item | Shortcut | Where |
|---|---|---|
| Code Cleanup > Configure Code Cleanup |  | none |
| Code Cleanup > Run Code Cleanup on Document | Ctrl+K, Ctrl+E | none |
| Code Cleanup > Run Code Cleanup on Project |  | none |
| Code Cleanup > Run Code Cleanup on Solution |  | none |
| Run Code Analysis > On Current Project |  | none |
| Run Code Analysis > On Solution | Alt+F11 | none |
| Configure Code Analysis (.editorconfig) |  | none |
| Decompile Assembly |  | none |
| Go To Decompiled Definition |  | none |
| Remove and Sort Usings | Ctrl+R, Ctrl+G | none |
| Show Generated Files (Source Generators) |  | none |

## Build

| Item | Shortcut | Where |
|---|---|---|
| Mobile App > Android APK |  | none |
| Mobile App > Android APK (debug, faster) |  | none |
| Mobile App > Android App Bundle (Google Play) |  | none |
| Mobile App > Cancel Build |  | none |
| Mobile App > Create Foldable Emulator |  | none |
| Mobile App > Web site |  | none |
| Mobile App > Windows EXE |  | none |
| Build Native Exe |  | none |
| Build Project |  | none |
| Build Solution | Ctrl+Shift+B | none |
| Clean Solution |  | none |
| Configuration Manager |  | none |
| Open Publish Folder |  | none |
| Publish / Create Installer | Ctrl+Alt+F5 | none |
| Publish Selection |  | none |
| Rebuild Solution |  | none |
| Refresh References |  | none |

## Command Palette

| Item | Shortcut | Where |
|---|---|---|
| AI > Agent Manager: New Task (`agents.new`) |  | none |
| AI > Agent Manager: Show (`agents.show`) |  | none |
| AI > Agent Manager: Stop All Tasks (`agents.stop_all`) |  | none |
| Build > Build: Build Native Exe (`build.native`) |  | none |
| Build > Build: Publish / Create Installer... (`build.publish`) |  | none |
| Claude Code for VS Code > Accept this change (`claude-vscode.acceptProposedHunkFromBar`) |  | none |
| Claude Code for VS Code > Claude Code: Accept Change at Cursor (`claude-vscode.acceptProposedHunk`) |  | none |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-code.acceptProposedDiff`) |  | none |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-vscode.acceptProposedDiff`) |  | none |
| Claude Code for VS Code > Claude Code: Add Session Tab to Group (`claude-vscode.addSessionTabToGroup`) |  | none |
| Claude Code for VS Code > Claude Code: Add to Chat (`claude-vscode.addToChat`) |  | none |
| Claude Code for VS Code > Claude Code: Blur input (`claude-vscode.blur`) |  | none |
| Claude Code for VS Code > Claude Code: Focus input (`claude-vscode.focus`) |  | none |
| Claude Code for VS Code > Claude Code: Focus last message (`claude-vscode.focusLastMessage`) |  | none |
| Claude Code for VS Code > Claude Code: Insert @-Mention Reference (`claude-vscode.insertAtMention`) |  | none |
| Claude Code for VS Code > Claude Code: Insert At-Mentioned (`claude-code.insertAtMentioned`) |  | none |
| Claude Code for VS Code > Claude Code: Install Plugin (`claude-vscode.installPlugin`) |  | none |
| Claude Code for VS Code > Claude Code: Logout (`claude-vscode.logout`) |  | none |
| Claude Code for VS Code > Claude Code: Mark Session as Unread (`claude-vscode.markSessionUnread`) |  | none |
| Claude Code for VS Code > Claude Code: New Conversation (`claude-vscode.newConversation`) |  | none |
| Claude Code for VS Code > Claude Code: Open Walkthrough (`claude-vscode.openWalkthrough`) |  | none |
| Claude Code for VS Code > Claude Code: Open in New Tab (`claude-vscode.editor.open`) |  | none |
| Claude Code for VS Code > Claude Code: Open in New Window (`claude-vscode.window.open`) |  | none |
| Claude Code for VS Code > Claude Code: Open in Primary Editor (`claude-vscode.primaryEditor.open`) |  | none |
| Claude Code for VS Code > Claude Code: Open in Side Bar (`claude-vscode.sidebar.open`) |  | none |
| Claude Code for VS Code > Claude Code: Open in Terminal (`claude-vscode.terminal.open`) |  | none |
| Claude Code for VS Code > Claude Code: Open (`claude-vscode.editor.openLast`) |  | none |
| Claude Code for VS Code > Claude Code: Reject Change at Cursor (`claude-vscode.rejectProposedHunk`) |  | none |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-code.rejectProposedDiff`) |  | none |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-vscode.rejectProposedDiff`) |  | none |
| Claude Code for VS Code > Claude Code: Rename Session Tab (`claude-vscode.renameSessionTab`) |  | none |
| Claude Code for VS Code > Claude Code: Reopen Closed Session (`claude-vscode.reopenClosedSession`) |  | none |
| Claude Code for VS Code > Claude Code: Show Logs (`claude-vscode.showLogs`) |  | none |
| Claude Code for VS Code > Claude Code: Toggle Focus view (`claude-vscode.toggleFocusView`) |  | none |
| Claude Code for VS Code > Claude Code: Update extension (`claude-vscode.update`) |  | none |
| Claude Code for VS Code > Reject this change (`claude-vscode.rejectProposedHunkFromBar`) |  | none |
| CodeIgniter > CodeIgniter: Show Routes (`codeigniter.routes`) |  | none |
| CodeIgniter > CodeIgniter: Spark Commands (`codeigniter.spark`) |  | none |
| CodeIgniter > CodeIgniter: spark db:seed... (`codeigniter.db:seed`) |  | none |
| CodeIgniter > CodeIgniter: spark make:controller... (`codeigniter.make:controller`) |  | none |
| CodeIgniter > CodeIgniter: spark make:migration... (`codeigniter.make:migration`) |  | none |
| CodeIgniter > CodeIgniter: spark make:model... (`codeigniter.make:model`) |  | none |
| CodeIgniter > CodeIgniter: spark migrate... (`codeigniter.migrate`) |  | none |
| Debug > Debug with Extension Debugger (`vsx.debugWithExtension`) |  | none |
| Extensions > Extensions: Check for Extension Updates (`vsx.checkUpdates`) |  | none |
| Extensions > Extensions: Install from VSIX... (`vsx.installVsix`) |  | none |
| Extensions > Extensions: Show Extensions (`vsx.show`) | Ctrl+Shift+X | none |
| Extensions > Extensions: Update All Extensions (`vsx.updateAll`) |  | none |
| Extensions > New Extension Terminal from Profile... (`vsx.newTerminalProfile`) |  | none |
| Extensions > Open Extension URI... (`vsx.openUri`) |  | none |
| Extensions > Restart Extension Host (`vsx.restartExtensionHost`) |  | none |
| Extensions > Show Extension Output (`vsx.showExtensionOutput`) |  | none |
| Go > Go to Line/Column... (`workbench.gotoLine`) |  | none |
| Laravel > Laravel: Generate IDE Helper Files (`laravel.ide-helper`) |  | none |
| Laravel > Laravel: Open Tinker (`laravel.tinker`) |  | none |
| Laravel > Laravel: Run Artisan Command... (`laravel.artisan`) |  | none |
| Laravel > Laravel: Show Routes (`laravel.routes`) |  | none |
| Laravel > Laravel: make:model -mcr (`laravel.make-model`) |  | none |
| Preferences > Color Theme: Blue (`workbench.theme.Blue`) |  | none |
| Preferences > Color Theme: Dark (`workbench.theme.Dark`) |  | none |
| Preferences > Color Theme: High Contrast (`workbench.theme.High Contrast`) |  | none |
| Preferences > Color Theme: Light (`workbench.theme.Light`) |  | none |
| Preferences > Color Theme: System (`workbench.theme.System`) |  | none |
| Preferences > File Icon Theme... (`workbench.action.selectIconTheme`) |  | none |
| Project > Flutter: Add Google Font... (`flutter.fonts`) |  | none |
| Project > Flutter: Add New Screen (visual designer)... (`flutter.newScreen`) |  | none |
| Project > Flutter: App Theme... (`flutter.theme`) |  | none |
| Project > Flutter: Import Screen from Dart... (`flutter.importScreen`) |  | none |
| Project > Flutter: Project Assets... (`flutter.assets`) |  | none |
| Project > Project: Add Report... (`reports.add`) |  | none |
| Rails > Rails: Edit Credentials (`rails.credentials`) |  | none |
| Rails > Rails: Open Console (`rails.console`) |  | none |
| Rails > Rails: Show Models (`rails.models`) |  | none |
| Rails > Rails: Show Routes (`rails.routes`) |  | none |
| View > Focus Active Editor (`workbench.focusEditor`) |  | none |
| View > Show AI Chat (`workbench.view.chat`) |  | none |
| View > Show AI Web Chats (`workbench.view.webchats`) |  | none |
| View > Show Agents (`workbench.view.agents`) |  | none |
| View > Show Databases (`workbench.view.databases`) |  | none |
| View > Show Explorer (`workbench.view.explorer`) |  | none |
| View > Show Run and Debug (`workbench.view.run`) |  | none |
| View > Show Search (`workbench.view.search`) |  | none |
| View > Show Source Control (`workbench.view.scm`) |  | none |

## Context menu: Databases (QTreeWidget)

| Item | Shortcut | Where |
|---|---|---|
| Local Servers > Copy MariaDB/MySQL Password |  | none [vs] |
| Local Servers > Copy PostgreSQL Password |  | none [vs] |
| Local Servers > Server Status |  | none [vs] |
| Local Servers > Start local MariaDB/MySQL |  | none [vs] |
| Local Servers > Start local PostgreSQL |  | none [vs] |
| Local Servers > Stop local MariaDB/MySQL |  | none [vs] |
| Local Servers > Stop local PostgreSQL |  | none [vs] |
| Add Connection |  | none [vs] |
| Adminer (login page) |  | none [vs] |
| New SQLite Database |  | none [vs] |
| Refresh |  | none [vs] |

## Context menu: Editor tab

| Item | Shortcut | Where |
|---|---|---|
| Close |  | none |
| Close All |  | none |
| Close All But This |  | none |

## Context menu: Toolbox (Toolbox)

| Item | Shortcut | Where |
|---|---|---|
| Choose Items |  | none [vs] |
| Collapse All |  | none [vs] |
| Expand All |  | none [vs] |
| Install Component Package |  | none [vs] |
| Show All Items |  | none [vs] |

## Data

| Item | Shortcut | Where |
|---|---|---|
| Add New Data Source |  | none |
| Preview Data |  | none |
| Refresh Data Sources |  | none |
| Show Data Sources | Alt+Shift+D | none |

## Debug

| Item | Shortcut | Where |
|---|---|---|
| Assembly Checks > Assembly Checks Window |  | none |
| Assembly Checks > Check Selection |  | none |
| Assembly Checks > Check This Procedure |  | none |
| Assembly Checks > Check by Running | Ctrl+Shift+F5 | none |
| Assembly Checks > Explain This Line | Ctrl+Shift+F1 | none |
| Assembly Checks > What-If Console |  | none |
| Mobile > Always Use the Dart Debugger for F5 |  | none |
| Mobile > Hot Reload | Ctrl+Alt+R | none |
| Mobile > Hot Restart | Ctrl+Alt+Shift+R | none |
| Mobile > Refresh devices |  | none |
| Windows > Call Stack |  | none |
| Windows > Disassembly | Alt+8 | none |
| Windows > Immediate |  | none |
| Windows > Locals |  | none |
| Windows > Memory 1 | Alt+6 | none |
| Windows > Registers | Alt+5 | none |
| Windows > Stack |  | none |
| Windows > Threads | Ctrl+Alt+H | none |
| Windows > Watch |  | none |
| 8086: Stop at First Instruction |  | none |
| Attach to Process | Ctrl+Alt+P | none |
| Break All |  | none |
| Break on Exceptions |  | none |
| Breakpoint Condition | Alt+F9 | none |
| Breakpoint Settings (Condition, Hit Count, Log) |  | none |
| CPU (OllyDbg Style) | Alt+C | none |
| CPU View at First Stop |  | none |
| Debug Expo Web Page (js-debug) |  | none |
| Debug with Extension Debugger |  | none |
| Go To Disassembly |  | none |
| Install Delve (Go Debugger) |  | none |
| Run to Cursor | Ctrl+F10 | none |
| Start Debugging / Continue | F5 | none |
| Start Without Debugging | Ctrl+F5 | none |
| Step Into | F11 | none |
| Step Into Instruction | Ctrl+Alt+F11 | none |
| Step Out | Shift+F11 | none |
| Step Over | F10 | none |
| Step Over Instruction | Ctrl+Alt+F10 | none |
| Stop Debugging | Shift+F5 | none |
| Toggle Breakpoint | F9 | none |
| Watch |  | none |

## Edit

| Item | Shortcut | Where |
|---|---|---|
| AI > Add Comments |  | none |
| AI > Edit with AI |  | none |
| AI > Explain |  | none |
| AI > Fix |  | none |
| AI > Generate Docs |  | none |
| AI > Generate Tests |  | none |
| AI > Inline Completions |  | none |
| AI > Refactor |  | none |
| AI > Suggest Inline Completion |  | none |
| IntelliSense > Remove and Sort Usings |  | none |
| IntelliSense > Sort Usings |  | none |
| Refactor > Extract Method |  | none |
| Refactor > Extract Variable |  | none |
| Refactor > Find All References |  | none |
| Refactor > Quick Actions and Refactorings |  | none |
| Refactor > Rename |  | none |
| Copy | Ctrl+C | none |
| Cut | Ctrl+X | none |
| Delete |  | none |
| Emmet: Expand Abbreviation |  | none |
| Find | Ctrl+F | none |
| Find Next | F3 | none |
| Find Previous | Shift+F3 | none |
| Find in Files | Ctrl+Shift+F | none |
| Format Document | Alt+Shift+F, Ctrl+K, Ctrl+D | none |
| Format on Save |  | none |
| Go to Definition | F12 | none |
| Go to Line | Ctrl+G | none |
| Insert Snippet |  | none |
| Language Mode |  | none |
| Open as PHP |  | none |
| Paste | Ctrl+V | none |
| Redo | Ctrl+Y | none |
| Replace | Ctrl+H | none |
| Select All | Ctrl+A | none |
| Undo | Ctrl+Z | none |

## File

| Item | Shortcut | Where |
|---|---|---|
| Add > Existing Project |  | none |
| Add > New Project |  | none |
| Import > Program (.exe / .dll) |  | none |
| Import > Python GUI Program (Tkinter / Qt) |  | none |
| Import > Visual Basic 6 Project (.vbp / .frm) |  | none |
| New Image > Cursor (.cur) |  | none |
| New Image > Icon (.ico) |  | none |
| New Image > Image (.png / .bmp) |  | none |
| New Notebook > Blank Notebook (.ipynb) |  | none |
| New Notebook > Data Science Starter (pandas + matplotlib) |  | none |
| New Notebook > Import Python Script as Notebook |  | none |
| New Notebook > Open Notebook |  | none |
| Open Remote > Recent SSH Hosts > (no saved hosts) |  | none |
| Open Remote > Build on Remote |  | none |
| Open Remote > Connect to SSH Host |  | none |
| Open Remote > Disconnect |  | none |
| Open Remote > Open Folder in Dev Container |  | none |
| Open Remote > Open WSL Folder |  | none |
| Open Remote > Reload Remote File |  | none |
| Open Remote > Remote Explorer |  | none |
| Open Remote > Remote Terminal |  | none |
| Open Remote > Run Remote Command |  | none |
| Open Remote > Run on Remote |  | none |
| Open Remote > Stop Remote Command |  | none |
| Open in Hex Editor > Current File |  | none |
| Open in Hex Editor > File |  | none |
| Recent Projects and Solutions > (no recent projects) |  | none |
| App Gallery |  | none |
| Close Solution |  | none |
| Exit |  | none |
| Migrate Project |  | none |
| New Project | Ctrl+Shift+N | none |
| New Project (.NET, Visual Studio 2022) | Ctrl+Alt+Shift+N | none |
| New Solution from Existing Folders |  | none |
| New Window | Ctrl+Alt+N | none |
| Open File | Ctrl+O | none |
| Open Folder | Ctrl+K, Ctrl+O | none |
| Open Project | Ctrl+Shift+O | none |
| Open in Design View |  | none |
| Save |  | none |
| Save All | Ctrl+S | none |

## Format

| Item | Shortcut | Where |
|---|---|---|
| Align > Bottoms |  | none |
| Align > Centers |  | none |
| Align > Lefts |  | none |
| Align > Middles |  | none |
| Align > Rights |  | none |
| Align > Tops |  | none |
| Align > to Grid |  | none |
| Center in Form > Horizontally |  | none |
| Center in Form > Vertically |  | none |
| Horizontal Spacing > Decrease |  | none |
| Horizontal Spacing > Increase |  | none |
| Horizontal Spacing > Make Equal |  | none |
| Horizontal Spacing > Remove |  | none |
| Make Same Size > Both |  | none |
| Make Same Size > Height |  | none |
| Make Same Size > Size to Grid |  | none |
| Make Same Size > Width |  | none |
| Order > Bring to Front |  | none |
| Order > Send to Back |  | none |
| Vertical Spacing > Decrease |  | none |
| Vertical Spacing > Increase |  | none |
| Vertical Spacing > Make Equal |  | none |
| Vertical Spacing > Remove |  | none |
| Localization Strings |  | none |
| Lock Controls |  | none |

## Git

| Item | Shortcut | Where |
|---|---|---|
| GitHub > Create Pull Request |  | none |
| GitHub > Download GitHub CLI |  | none |
| GitHub > Pull Requests and Issues |  | none |
| GitHub > Sign in (gh auth login) |  | none |
| Abort merge / rebase |  | none |
| Amend last commit |  | none |
| Blame current file |  | none |
| Commit All |  | none |
| Compare current file with commit |  | none |
| Continue merge / rebase |  | none |
| Edit .gitignore |  | none |
| Fetch |  | none |
| Force Push (with lease) |  | none |
| Git Changes |  | none |
| Git Settings |  | none |
| Manage Branches |  | none |
| Merge into current branch |  | none |
| New Branch | Ctrl+Alt+Shift+B | none |
| Pull |  | none |
| Pull (rebase) |  | none |
| Push |  | none |
| Rebase current branch onto |  | none |
| Remotes |  | none |
| Resolve Conflicts |  | none |
| Stash All |  | none |
| Stashes |  | none |
| Sync (pull, then push) |  | none |
| Tags |  | none |
| Toggle inline blame in the editor |  | none |
| Undo last commit (keep changes) |  | none |
| View History (graph) | Ctrl+Alt+H | none |

## Help

| Item | Shortcut | Where |
|---|---|---|
| Help Files (CHM) > AI in RAD IDE (Arabic guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > BASIC course (Arabic, CHM) |  | none |
| Help Files (CHM) > C++ course (Arabic, CHM) |  | none |
| Help Files (CHM) > Car Diagnostics: OBD-II, Warning Lights and Service Functions (Arabic, CHM) |  | none |
| Help Files (CHM) > CodeIgniter 4 in RAD IDE (Guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > DOS Programming: QBasic, Pascal, C, Assembly and Visual Designers (Arabic, CHM) |  | none |
| Help Files (CHM) > Deploy and Publish in RAD IDE (Arabic guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > ECU and Firmware Files: Analysis and Calibration Editing (Arabic, CHM) |  | none |
| Help Files (CHM) > Extensions in RAD IDE (Arabic guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Flutter Mobile Apps in RAD IDE (guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Fortran Basics (Arabic, CHM) |  | none |
| Help Files (CHM) > Import and Migrate in RAD IDE (Arabic guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Jupyter Notebooks and Data Science in RAD IDE (Arabic, CHM) |  | none |
| Help Files (CHM) > Laravel in RAD IDE (Guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Assembly from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn C from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn C# from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Dart from Scratch (to Flutter) (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Go from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Java from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn JavaScript and TypeScript with Node.js (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Lua from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Perl from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn PowerShell from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Python from Scratch to Desktop Apps (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Ring from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Ruby from Scratch, then Ruby on Rails (Arabic, CHM) |  | none |
| Help Files (CHM) > Learn Rust from Scratch (Arabic, CHM) |  | none |
| Help Files (CHM) > Making Games in RAD IDE (guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Node.js and Front-end Guide for RAD IDE (Arabic, CHM) |  | none |
| Help Files (CHM) > Old NASA Programs: the Apollo Guidance Computer and Classic Fortran (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Guide: Data and Reports (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Guide: Debugging and Testing (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Guide: Git and Collaboration (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Guide: The Form Designer (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Guide: Workbench Basics (Arabic, CHM) |  | none |
| Help Files (CHM) > RAD IDE Manual (CHM) |  | none |
| Help Files (CHM) > Retro Games: ROM Hacking and Programming the Atari 2600, NES and Game Boy (Arabic, CHM) |  | none |
| Help Files (CHM) > Solutions and References in RAD IDE (Arabic guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Visual Studio Projects in RAD IDE (Guide) (Arabic, CHM) |  | none |
| Help Files (CHM) > Web Development with PHP from Scratch (Arabic, CHM) |  | none |
| About |  | none |
| Check for Updates |  | none |
| Check for Updates Automatically |  | none |
| Context Help | F1 | none |
| Example Projects |  | none |
| Install Another Version |  | none |
| Keyboard Shortcuts |  | none |
| PE / MFC Workbench Guide |  | none |
| Python Documentation |  | none |
| Qt for Python (PySide6) Documentation |  | none |
| RAD IDE Help | Ctrl+F1 | none |
| Ring Documentation |  | none |
| Ring Samples |  | none |
| RingQt / Qt 5 Class Reference |  | none |
| Tkinter Documentation |  | none |
| Tutorials (Arabic lessons) | Ctrl+Shift+F1 | none |
| VB6 Language Reference |  | none |

## Menu bar corner

| Item | Shortcut | Where |
|---|---|---|
| Agent |  | none |
| Code |  | none |
| VS |  | none |

## Project

| Item | Shortcut | Where |
|---|---|---|
| ECU Project > Analyze (workbench) |  | none |
| ECU Project > Build ECU Project |  | none |
| ECU Project > Build Settings |  | none |
| ECU Project > Build in Workbench |  | none |
| ECU Project > Checksum Toolkit (any file) |  | none |
| ECU Project > Checksums |  | none |
| ECU Project > Compare with Original |  | none |
| ECU Project > Compare with Original (workbench) |  | none |
| ECU Project > Edit Working Copy |  | none |
| ECU Project > Export Modification Report |  | none |
| ECU Project > Export Patch (IPS / BPS) |  | none |
| ECU Project > Find Maps (workbench) |  | none |
| ECU Project > Import Patch |  | none |
| ECU Project > Open Build Output |  | none |
| ECU Project > Open Workbench |  | none |
| ECU Project > Set Original |  | none |
| ECU Project > Verify Checksums |  | none |
| ECU Project > Verify Checksums (workbench) |  | none |
| ECU Project > Versions |  | none |
| ECU Project > View Original (read-only) |  | none |
| Firmware Analysis > Analyze |  | none |
| Firmware Analysis > Make Working Copy |  | none |
| Firmware Analysis > Open Labels |  | none |
| Firmware Analysis > Open Notes |  | none |
| Firmware Analysis > Set Original |  | none |
| Firmware Analysis > Verify Original |  | none |
| ROM Hacking > Add Patch |  | none |
| ROM Hacking > Build Patched ROM |  | none |
| ROM Hacking > Capture Edits as Patch |  | none |
| ROM Hacking > Edit Working Copy |  | none |
| ROM Hacking > Open Build Output |  | none |
| ROM Hacking > Patch Manager |  | none |
| ROM Hacking > Set Source ROM |  | none |
| ROM Hacking > View Source ROM (read-only) |  | none |
| Add 3D Scene |  | none |
| Add Existing Item |  | none |
| Add Module |  | none |
| Add New Screen (Flutter designer) |  | none |
| Add Reference |  | none |
| Add Report |  | none |
| Add User Control |  | none |
| Add Windows Form |  | none |
| Build EXE |  | none |
| Check for Errors | Ctrl+Shift+B | none |
| DOS Project Settings |  | none |
| DOS Settings |  | none |
| Flutter App Theme |  | none |
| Flutter Assets |  | none |
| Flutter Fonts (Google Fonts) |  | none |
| Generate Form with AI |  | none |
| Import Flutter Screen from Dart |  | none |
| Manage Packages |  | none |
| Open Project Folder |  | none |
| Project Properties |  | none |
| Resources |  | none |
| Set as StartUp Project |  | none |
| User Control Properties and Events |  | none |

## Share

| Item | Shortcut | Where |
|---|---|---|
| Follow Participant > (no session) |  | none |
| Copy Invite Link |  | none |
| End Collaboration Session |  | none |
| Guests Read-only |  | none |
| Join Collaboration Session |  | none |
| Live Share Window |  | none |
| Save Shared File on Host |  | none |
| Start Collaboration Session |  | none |

## Site

| Item | Shortcut | Where |
|---|---|---|
| Docker > Build Image |  | none |
| Docker > Compose Down |  | none |
| Docker > Compose Up |  | none |
| Docker > Docker Panel |  | none |
| Docker > Generate Dockerfile / Compose / Dev Container |  | none |
| Docker > Lint Dockerfile |  | none |
| Open in Installed Browser > Chrome |  | none |
| Open in Installed Browser > Default browser |  | none |
| Open in Installed Browser > Edge |  | none |
| Open in Installed Browser > Firefox |  | none |
| App Gallery |  | none |
| Build Production (npm run build) |  | none |
| CodeIgniter Panel (Spark, Routes) |  | none |
| Databases | Ctrl+Alt+D | none |
| Deploy to Cloud / Git / SSH |  | none |
| Django / Flask / FastAPI Panel |  | none |
| Laravel Panel (Artisan, Routes, Tinker) |  | none |
| Lighthouse Report |  | none |
| New File |  | none |
| New Folder |  | none |
| New Front-end App (React, Vue, Svelte, Angular) |  | none |
| Open Database in Adminer |  | none |
| Open in Browser | Ctrl+Alt+B | none |
| Preview |  | none |
| Publish | Ctrl+Alt+P | none |
| Publish Preview (dry run) |  | none |
| REST Client | Ctrl+Alt+K | none |
| Rails Panel (Console, Routes, Models) |  | none |
| Reports |  | none |
| Requests |  | none |
| Restart Web Server |  | none |
| Run Site in Preview |  | none |
| SEO Report |  | none |
| Site Settings |  | none |
| Stop Web Server |  | none |
| SuperPreview | Ctrl+Alt+B | none |

## Test

| Item | Shortcut | Where |
|---|---|---|
| Clear Coverage Results |  | none |
| Debug Selected Test |  | none |
| Refresh Tests |  | none |
| Run All Tests | Ctrl+R, A | none |
| Run All Tests with Coverage |  | none |
| Run Failed Tests |  | none |
| Run Tests in Current File | Ctrl+R, T | none |
| Show Code Coverage Colouring |  | none |
| Test Explorer | Ctrl+E, T | none |

## Toolbar Activity Bar

| Item | Shortcut | Where |
|---|---|---|
| AI Chat |  | none [agent,vscode] |
| AI Web Chats |  | none [agent,vscode] |
| Agents |  | none [agent,vscode] |
| Claude Code |  | none [agent,vscode] |
| Databases |  | none [vscode] |
| Editor |  | none [agent] |
| Explorer |  | none [agent,vscode] |
| Extensions |  | none [agent,vscode] |
| Live Share |  | none [agent,vscode] |
| Manage |  | none [agent,vscode] |
| Packages |  | none [vscode] |
| QWidget |  | none [agent,vscode] |
| Remote Explorer |  | none [vscode] |
| Ring Samples |  | none [agent,vscode] |
| Run and Debug |  | none [vscode] |
| Search |  | none [agent,vscode] |
| Source Control |  | none [agent,vscode] |
| Testing |  | none [vscode] |
| Tutorials |  | none [agent,vscode] |

## Toolbar Debug

| Item | Shortcut | Where |
|---|---|---|
| Step Into | F11 | none |
| Step Out | Shift+F11 | none |
| Step Over | F10 | none |
| Toggle Breakpoint | F9 | none |

## Toolbar Expo

| Item | Shortcut | Where |
|---|---|---|
| Close the Emulator |  | none |
| Open in Browser |  | none |
| QComboBox |  | none |
| QLabel |  | none |
| Refresh devices |  | none |

## Toolbar Mobile

| Item | Shortcut | Where |
|---|---|---|
| Hot Reload | Ctrl+Alt+R | none |
| Hot Restart | Ctrl+Alt+Shift+R | none |
| QComboBox |  | none |
| QLabel |  | none |
| Refresh devices |  | none |

## Toolbar Retro Emulator

| Item | Shortcut | Where |
|---|---|---|
| QComboBox |  | none |
| QLabel |  | none |

## Toolbar Rust

| Item | Shortcut | Where |
|---|---|---|
| Clippy |  | none |
| QComboBox |  | none |
| QLabel |  | none |
| Reload |  | none |
| Test |  | none |

## Toolbar Solution Configurations

| Item | Shortcut | Where |
|---|---|---|
| QComboBox |  | none |
| QLabel |  | none |

## Toolbar Standard

| Item | Shortcut | Where |
|---|---|---|
| Design | Ctrl+Shift+D | none |
| New Project | Ctrl+Shift+N | none |
| Open Project | Ctrl+Shift+O | none |
| Redo | Ctrl+Y | none |
| Save All | Ctrl+S | none |
| Split | Ctrl+Alt+Shift+D | none |
| Start Debugging / Continue | F5 | none |
| Stop Debugging | Shift+F5 | none |
| Undo | Ctrl+Z | none |

## Toolbar Toolbar

| Item | Shortcut | Where |
|---|---|---|
| Local Servers > Copy MariaDB/MySQL Password |  | none |
| Local Servers > Copy PostgreSQL Password |  | none |
| Local Servers > Server Status |  | none |
| Local Servers > Start local MariaDB/MySQL |  | none |
| Local Servers > Start local PostgreSQL |  | none |
| Local Servers > Stop local MariaDB/MySQL |  | none |
| Local Servers > Stop local PostgreSQL |  | none |
| New > Add Connection (SQLite / MySQL / PostgreSQL) |  | none |
| New > New SQLite Database |  | none |
| Add New Data Source |  | none |
| Back |  | none |
| Clear |  | none |
| Configure Data Source |  | none |
| Coverage |  | none |
| Debug |  | none |
| Diagram |  | none |
| Forward |  | none |
| New Query |  | none |
| New Table |  | none |
| Open in Adminer |  | none |
| Open in Browser |  | none |
| Preview Data |  | none |
| QCheckBox |  | none |
| QComboBox |  | none |
| QLabel |  | none |
| QLineEdit |  | none |
| Refresh |  | none |
| Refresh (re-read the columns and rows) |  | none |
| Reload (F5 in the page) |  | none |
| Remove Data Source |  | none |
| Rotate |  | none |
| Run |  | none |
| Run All |  | none |
| Run Failed |  | none |
| Stop |  | none |

## Tools

| Item | Shortcut | Where |
|---|---|---|
| Car Connection > Bus Monitor |  | none |
| Car Connection > Connect to Car |  | none |
| Car Connection > Demo Car (Simulator) |  | none |
| Car Connection > Disconnect |  | none |
| Car Connection > Find Control Units |  | none |
| Compare (Diff) > Compare Current File with |  | none |
| Compare (Diff) > Compare Current File with Clipboard |  | none |
| Compare (Diff) > Compare Current File with Git HEAD |  | none |
| Compare (Diff) > Compare Current File with Saved |  | none |
| Compare (Diff) > Compare Files |  | none |
| Component Packages > Choose Toolbox Items |  | none |
| Component Packages > Hot Reload (package development) |  | none |
| Component Packages > Install Component Package (.radcomp) |  | none |
| Component Packages > Manage Component Packages |  | none |
| Component Packages > Reload Packages |  | none |
| Composer > Dump Autoload (composer dump-autoload) |  | none |
| Composer > Install (composer install) |  | none |
| Composer > Open composer.json |  | none |
| Composer > Remove Package |  | none |
| Composer > Require Package |  | none |
| Composer > Show Outdated Packages |  | none |
| Composer > Update (composer update) |  | none |
| Composer > Validate composer.json |  | none |
| Databases > Local Servers > Copy MariaDB/MySQL Password |  | none |
| Databases > Local Servers > Copy PostgreSQL Password |  | none |
| Databases > Local Servers > Server Status |  | none |
| Databases > Local Servers > Start local MariaDB/MySQL |  | none |
| Databases > Local Servers > Start local PostgreSQL |  | none |
| Databases > Local Servers > Stop local MariaDB/MySQL |  | none |
| Databases > Local Servers > Stop local PostgreSQL |  | none |
| Databases > Add Connection |  | none |
| Databases > Database Diagram |  | none |
| Databases > Databases | Ctrl+Alt+D | none |
| Databases > New Query |  | none |
| Databases > New SQLite Database |  | none |
| Databases > Open in Adminer |  | none |
| Databases > Start local MariaDB/MySQL |  | none |
| Databases > Start local PostgreSQL |  | none |
| Docker > Build Image |  | none |
| Docker > Compose Down |  | none |
| Docker > Compose Up |  | none |
| Docker > Docker Panel |  | none |
| Docker > Generate Dockerfile / Compose / Dev Container |  | none |
| Docker > Lint Dockerfile |  | none |
| Firmware & ECU > Calibration Maps > Compare Two Binaries (Maps) |  | none |
| Firmware & ECU > Calibration Maps > Find Maps in a Binary |  | none |
| Firmware & ECU > Calibration Maps > Open Binary in Map Editor |  | none |
| Firmware & ECU > Calibration Maps > Open Binary with an A2L |  | none |
| Firmware & ECU > Calibration Maps > Open rusEFI / Speeduino Tune (msq + ini) |  | none |
| Firmware & ECU > Analyze Firmware File |  | none |
| Firmware & ECU > Compare Firmware Files |  | none |
| Firmware & ECU > Create Synthetic Test Firmware |  | none |
| Firmware & ECU > Firmware Converter (HEX / S-record / ELF / split / merge) |  | none |
| Firmware & ECU > Getting Started |  | none |
| Firmware & ECU > New ECU Project |  | none |
| Firmware & ECU > New ECU Project (Demo Firmware) |  | none |
| Firmware & ECU > Open EEPROM Dump (read-only) |  | none |
| Firmware & ECU > Open Firmware in Workbench |  | none |
| Image Editor > Add to Project Resources |  | none |
| Image Editor > New Icon |  | none |
| Image Editor > New Image |  | none |
| Image Editor > Open Image |  | none |
| Image Editor > Set as Application Icon |  | none |
| Image Editor > Set as Form Icon |  | none |
| Keymap > Emacs (basic) |  | none |
| Keymap > VS Code |  | none |
| Keymap > Vim |  | none |
| Keymap > Visual Studio |  | none |
| Language > English |  | none |
| Language > العربية |  | none |
| Macros > Macro Explorer |  | none |
| Macros > Record Temporary Macro / Stop | Ctrl+Shift+R | none |
| Macros > Run Temporary Macro | Ctrl+Alt+Shift+P | none |
| Macros > Save Temporary Macro |  | none |
| NuGet Package Manager > Manage NuGet Packages for Solution |  | none |
| NuGet Package Manager > Package Manager Console |  | none |
| NuGet Package Manager > Package Manager Settings |  | none |
| Retro > Apollo AGC > Assembly Listing |  | none |
| Retro > Apollo AGC > Build with yaYUL |  | none |
| Retro > Apollo AGC > DSKY Panel |  | none |
| Retro > Apollo AGC > DSKY Verbs, Nouns and Programs |  | none |
| Retro > Apollo AGC > Open Apollo Source |  | none |
| Retro > Apollo AGC > Virtual AGC Toolchain |  | none |
| Retro > DOS Programming > Build DOS Program |  | none |
| Retro > DOS Programming > DOS Interrupt Reference |  | none |
| Retro > DOS Programming > DOS Project Settings |  | none |
| Retro > DOS Programming > DOS Toolchains |  | none |
| Retro > DOS Programming > Open Symbol Map |  | none |
| Retro > DOS Programming > Run in DOSBox-X |  | none |
| Retro > DOS Programming > Run in DOSBox-X Debugger |  | none |
| Retro > DOS Programming > Run in My QBasic |  | none |
| Retro > DOS Programming > Run with Captured Output |  | none |
| Retro > DOS Programming > Show Last DOS Screen |  | none |
| Retro > Game Designers > New Atari 2600 Screen |  | none |
| Retro > Game Designers > New DOS Mode 13h Screen |  | none |
| Retro > Game Designers > New Design for This Project |  | none |
| Retro > Game Designers > New Game Boy Map |  | none |
| Retro > Game Designers > New NES Screen / Level |  | none |
| Retro > Game Designers > Open Game Design |  | none |
| Retro > Graphics & Text > Atari 2600 Playfield Editor |  | none |
| Retro > Graphics & Text > New Text Table |  | none |
| Retro > Graphics & Text > New Tile Sheet (8 KB CHR) |  | none |
| Retro > Graphics & Text > Script Dump / Insert |  | none |
| Retro > Graphics & Text > Text Table Editor (.tbl) |  | none |
| Retro > Graphics & Text > Tile Editor (Open ROM / Binary) |  | none |
| Retro > Graphics & Text > Tile Map Editor |  | none |
| Retro > Graphics & Text > View Current File as Tiles |  | none |
| Retro > Legacy Fortran > Card Deck View |  | none |
| Retro > Legacy Fortran > Compiler Preset |  | none |
| Retro > Legacy Fortran > Convert to Free Form |  | none |
| Retro > Legacy Fortran > Explain Legacy Constructs |  | none |
| Retro > ROM Workbench > Apply Patch |  | none |
| Retro > ROM Workbench > Compare Files |  | none |
| Retro > ROM Workbench > Create Patch (IPS / BPS / UPS) |  | none |
| Retro > ROM Workbench > Fix Header Checksum of a File |  | none |
| Retro > ROM Workbench > Open in Hex Editor |  | none |
| Retro > ROM Workbench > ROM Info |  | none |
| Retro > Retro Development > Disassemble ROM into Project |  | none |
| Retro > Retro Development > Import Labels into Hints |  | none |
| Retro > Retro Development > Re-disassemble with Hints |  | none |
| Retro > Retro Development > Rebuild Check (compare with the original) |  | none |
| Retro > Retro Development > Retro Toolchains |  | none |
| Retro > Text-Mode (DOS) > Build & Run in DOSBox-X |  | none |
| Retro > Text-Mode (DOS) > Generate Code |  | none |
| Retro > Text-Mode (DOS) > New ANSI Art |  | none |
| Retro > Text-Mode (DOS) > New Text-Mode Screen |  | none |
| Retro > Text-Mode (DOS) > Open Screen or Art |  | none |
| Retro > Text-Mode (DOS) > Test Run (simulator) |  | none |
| Retro > Text-Mode (DOS) > Use Current Art as Splash Screen |  | none |
| Retro > Text-Mode (DOS) > View Code |  | none |
| Retro > Debug ROM in Emulator |  | none |
| Retro > Emulators |  | none |
| Retro > Reload ROM in Emulator | Ctrl+Alt+Shift+F5 | none |
| Retro > Run ROM in Emulator |  | none |
| AI Settings |  | none |
| Accessibility Check |  | none |
| Ask AI about the Selection |  | none |
| Assembly Toolchains |  | none |
| Car Diagnostics |  | none |
| Car Fault Guide |  | none |
| Car Service Functions |  | none |
| Code Snippets Manager |  | none |
| Deploy to Cloud / Git / SSH |  | none |
| Extensions |  | none |
| Install Extension from VSIX |  | none |
| Install Web Language Servers (HTML/CSS/JSON/PHP/JS/TS) |  | none |
| Interpreter Path |  | none |
| Language Servers and Debuggers |  | none |
| Options |  | none |
| PE / MFC Resource Workbench |  | none |
| PHP Versions |  | none |
| REST Client | Ctrl+Alt+K | none |
| Rust Settings |  | none |
| VS Code Extensions (Open VSX) |  | none |

## View

| Item | Shortcut | Where |
|---|---|---|
| Extension Views > Claude Code |  | none |
| Layout > Agent |  | none |
| Layout > Next Layout |  | none |
| Layout > Reset Current Layout |  | none |
| Layout > Toggle Panel | Ctrl+J | none |
| Layout > Toggle Side Bar | Ctrl+B | none |
| Layout > VS Code |  | none |
| Layout > Visual Studio |  | none |
| Layout > Zen Mode |  | none |
| Zoom > 100% |  | none |
| Zoom > 150% |  | none |
| Zoom > 200% |  | none |
| Zoom > 300% |  | none |
| Zoom > 400% |  | none |
| Zoom > 50% |  | none |
| Zoom > 75% |  | none |
| Zoom > Zoom In  (Ctrl+Wheel) |  | none |
| Zoom > Zoom Out |  | none |
| 8086 Emulator |  | none |
| AI Chat | Ctrl+Alt+I | none |
| AI Web Chats | Ctrl+Alt+W | none |
| AI Web Chats (dock) |  | none |
| Agent Manager | Ctrl+Alt+M | none |
| Animations |  | none |
| Call Stack |  | none |
| Code | F7 | none |
| CodeIgniter Panel (Spark, Routes) |  | none |
| Command Palette | Ctrl+Shift+P | none |
| Data |  | none |
| Data Sources |  | none |
| Databases | Ctrl+Alt+D | none |
| Design | Ctrl+Shift+D | none |
| Designer | Shift+F7 | none |
| Django / Flask / FastAPI Panel |  | none |
| Document Outline |  | none |
| Error List |  | none |
| Extension Output |  | none |
| Extensions (VS Code) | Ctrl+Shift+X | none |
| Find All References Window |  | none |
| Find Results |  | none |
| Framework Tools |  | none |
| Git Changes | Ctrl+Alt+G | none |
| Immediate |  | none |
| Laravel Panel (Artisan, Routes, Tinker) |  | none |
| Locals |  | none |
| New Agent Task |  | none |
| Notebook Variables |  | none |
| Object Browser | Ctrl+Alt+J | none |
| Objects and Timeline |  | none |
| Output |  | none |
| Package Manager Console |  | none |
| Preview |  | none |
| Problems Explained |  | none |
| Properties |  | none |
| Quick Open (Go to File) | Ctrl+P | none |
| Rails Panel (Console, Routes, Models) |  | none |
| Remote Explorer |  | none |
| Requests |  | none |
| Retro Debugger |  | none |
| Sizes |  | none |
| Solution Explorer |  | none |
| States |  | none |
| Tab Order |  | none |
| Terminal | Ctrl+` | none |
| Toolbox |  | none |

## Window

| Item | Shortcut | Where |
|---|---|---|
| Auto Hide |  | none |
| Auto Hide All |  | none |
| Remove Split |  | none |
| Split Editor Down |  | none |
| Split Editor Right |  | none |

## Docks / tool windows

| Title | Widget | Layouts |
|---|---|---|
| AI Chat | ChatPanel | agent,vs,vscode |
| AI Web Chats | WebChatPanel | agent,vs,vscode |
| Agent Manager | AgentManagerWidget | agent,vs,vscode |
| Animations | QScrollArea | agent,vs,vscode |
| CPU | CpuView | agent,vs,vscode |
| Call Stack |  | agent,vs,vscode |
| Claude Code |  | agent,vscode |
| CodeIgniter | CodeIgniterPanel | agent,vs,vscode |
| Data | QScrollArea | agent,vs,vscode |
| Data Sources | QScrollArea | agent,vs,vscode |
| Databases | DatabasesPanel | agent,vs,vscode |
| Disassembly | DisassemblyView | agent,vs,vscode |
| Docker | DockerPanel | agent,vs,vscode |
| Document Outline | QStackedWidget | agent,vs,vscode |
| Error List | QTreeWidget | agent,vs,vscode |
| Extension Output | OutputPanel | agent,vs,vscode |
| Extensions | ExtensionsView | agent,vs,vscode |
| Find Results | QTreeWidget | agent,vs,vscode |
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
| Preview | PreviewPane | agent,vs,vscode |
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
| `Ctrl+Shift+T` | QShortcut on MainWindow |
| `Ctrl+Shift+Tab` | QShortcut on MainWindow |
| `Ctrl+Shift+X` | View > Extensions (VS Code) |
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

## Options pages


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
