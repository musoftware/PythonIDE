# RAD IDE feature inventory

Generated 2026-11-22 16:57 by `tools/feature_inventory.py` from a running IDE (offscreen) - do not edit. Traceability to tests: [TEST_MATRIX.md](TEST_MATRIX.md).

**852** distinct entry points (menu / tool bar / palette / context-menu items), **50** docks / tool windows, **89** keyboard shortcuts, **137** dialog classes, **0** New Project languages with **0** templates, **0** Options pages.

Contexts (a sandbox copy of each project, opened in every layout VS / VS Code / Agent):

* `firmware` - firmware ECU project (created by the firmware-ecu plugin) (language `firmware-ecu`)

## Entry points per area

| Area | Entries |
|---|---|
| Analyze | 11 |
| Build | 17 |
| Command Palette | 83 |
| Context menu: Databases (QTreeWidget) | 11 |
| Context menu: Editor tab | 3 |
| Context menu: HexView (HexView) | 6 |
| Context menu: Solution Explorer | 34 |
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
| Toolbar Firmware | 17 |
| Toolbar Mobile | 5 |
| Toolbar Retro Emulator | 2 |
| Toolbar Rust | 5 |
| Toolbar Solution Configurations | 2 |
| Toolbar Standard | 9 |
| Toolbar Toolbar | 40 |
| Tools | 154 |
| View | 65 |
| Window | 5 |

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
| Build > Build: Build Native Exe (`build.native`) |  | all contexts |
| Build > Build: Publish / Create Installer... (`build.publish`) |  | all contexts |
| Claude Code for VS Code > Accept this change (`claude-vscode.acceptProposedHunkFromBar`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Accept Change at Cursor (`claude-vscode.acceptProposedHunk`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-code.acceptProposedDiff`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Accept Proposed Changes (`claude-vscode.acceptProposedDiff`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Add Session Tab to Group (`claude-vscode.addSessionTabToGroup`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Add to Chat (`claude-vscode.addToChat`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Blur input (`claude-vscode.blur`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Focus input (`claude-vscode.focus`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Focus last message (`claude-vscode.focusLastMessage`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Insert @-Mention Reference (`claude-vscode.insertAtMention`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Insert At-Mentioned (`claude-code.insertAtMentioned`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Install Plugin (`claude-vscode.installPlugin`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Logout (`claude-vscode.logout`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Mark Session as Unread (`claude-vscode.markSessionUnread`) |  | all contexts |
| Claude Code for VS Code > Claude Code: New Conversation (`claude-vscode.newConversation`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open Walkthrough (`claude-vscode.openWalkthrough`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open in New Tab (`claude-vscode.editor.open`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open in New Window (`claude-vscode.window.open`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open in Primary Editor (`claude-vscode.primaryEditor.open`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open in Side Bar (`claude-vscode.sidebar.open`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open in Terminal (`claude-vscode.terminal.open`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Open (`claude-vscode.editor.openLast`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Reject Change at Cursor (`claude-vscode.rejectProposedHunk`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-code.rejectProposedDiff`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Reject Proposed Changes (`claude-vscode.rejectProposedDiff`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Rename Session Tab (`claude-vscode.renameSessionTab`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Reopen Closed Session (`claude-vscode.reopenClosedSession`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Show Logs (`claude-vscode.showLogs`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Toggle Focus view (`claude-vscode.toggleFocusView`) |  | all contexts |
| Claude Code for VS Code > Claude Code: Update extension (`claude-vscode.update`) |  | all contexts |
| Claude Code for VS Code > Reject this change (`claude-vscode.rejectProposedHunkFromBar`) |  | all contexts |
| CodeIgniter > CodeIgniter: Show Routes (`codeigniter.routes`) |  | all contexts |
| CodeIgniter > CodeIgniter: Spark Commands (`codeigniter.spark`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark db:seed... (`codeigniter.db:seed`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:controller... (`codeigniter.make:controller`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:migration... (`codeigniter.make:migration`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark make:model... (`codeigniter.make:model`) |  | all contexts |
| CodeIgniter > CodeIgniter: spark migrate... (`codeigniter.migrate`) |  | all contexts |
| Debug > Debug with Extension Debugger (`vsx.debugWithExtension`) |  | all contexts |
| Extensions > Extensions: Check for Extension Updates (`vsx.checkUpdates`) |  | all contexts |
| Extensions > Extensions: Install from VSIX... (`vsx.installVsix`) |  | all contexts |
| Extensions > Extensions: Show Extensions (`vsx.show`) | Ctrl+Shift+X | all contexts |
| Extensions > Extensions: Update All Extensions (`vsx.updateAll`) |  | all contexts |
| Extensions > New Extension Terminal from Profile... (`vsx.newTerminalProfile`) |  | all contexts |
| Extensions > Open Extension URI... (`vsx.openUri`) |  | all contexts |
| Extensions > Restart Extension Host (`vsx.restartExtensionHost`) |  | all contexts |
| Extensions > Show Extension Output (`vsx.showExtensionOutput`) |  | all contexts |
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

## Context menu: Databases (QTreeWidget)

| Item | Shortcut | Where |
|---|---|---|
| Local Servers > Copy MariaDB/MySQL Password |  | all contexts [vs] |
| Local Servers > Copy PostgreSQL Password |  | all contexts [vs] |
| Local Servers > Server Status |  | all contexts [vs] |
| Local Servers > Start local MariaDB/MySQL |  | all contexts [vs] |
| Local Servers > Start local PostgreSQL |  | all contexts [vs] |
| Local Servers > Stop local MariaDB/MySQL |  | all contexts [vs] |
| Local Servers > Stop local PostgreSQL |  | all contexts [vs] |
| Add Connection |  | all contexts [vs] |
| Adminer (login page) |  | all contexts [vs] |
| New SQLite Database |  | all contexts [vs] |
| Refresh |  | all contexts [vs] |

## Context menu: Editor tab

| Item | Shortcut | Where |
|---|---|---|
| Close |  | all contexts |
| Close All |  | all contexts |
| Close All But This |  | all contexts |

## Context menu: HexView (HexView)

| Item | Shortcut | Where |
|---|---|---|
| Copy |  | all contexts |
| Go To Offset |  | all contexts |
| Open in Map Editor |  | all contexts |
| Paste |  | all contexts |
| Select All |  | all contexts |
| Toggle Bookmark |  | all contexts |

## Context menu: Solution Explorer

| Item | Shortcut | Where |
|---|---|---|
| (ecuproj) > Open Firmware & ECU Workbench |  | all contexts |
| (ecuproj_original) > Open With > Firmware & ECU Workbench |  | all contexts |
| (ecuproj_original) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | all contexts |
| (ecuproj_original) > Analyze Firmware |  | all contexts |
| (ecuproj_work) > Open With > Firmware & ECU Workbench |  | all contexts |
| (ecuproj_work) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | all contexts |
| (ecuproj_work) > Analyze Firmware |  | all contexts |
| (module) > Open With > Firmware & ECU Workbench |  | all contexts |
| (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) |  | all contexts |
| (module) > Delete |  | all contexts |
| (module) > Open |  | all contexts |
| (project) > Add > Existing Item |  | all contexts |
| (project) > Add > Module |  | all contexts |
| (project) > Add > Reference |  | all contexts |
| (project) > Add > Windows Form |  | all contexts |
| (project) > Build |  | all contexts |
| (project) > Manage Packages |  | all contexts |
| (project) > Open Firmware & ECU Workbench |  | all contexts |
| (project) > Open Folder in File Explorer |  | all contexts |
| (project) > Properties |  | all contexts |
| (project) > Remove from Solution |  | all contexts |
| (project) > Set as StartUp Project |  | all contexts |
| (references) > Add Reference |  | all contexts |
| (references) > Refresh References |  | all contexts |
| (solution) > Add > Existing Project |  | all contexts |
| (solution) > Add > New Project |  | all contexts |
| (solution) > Set StartUp Project > CrawlEcu |  | all contexts |
| (solution) > Build Solution |  | all contexts |
| (solution) > Open Folder in File Explorer |  | all contexts |
| (solution) > Properties |  | all contexts |
| (solution) > Refresh References |  | all contexts |
| (solution) > Save All |  | all contexts |
| (solution) > Start Debugging / Continue | F5 | all contexts |
| (solution) > Start Without Debugging | Ctrl+F5 | all contexts |

## Context menu: Toolbox (Toolbox)

| Item | Shortcut | Where |
|---|---|---|
| Choose Items |  | all contexts [vs] |
| Collapse All |  | all contexts [vs] |
| Expand All |  | all contexts [vs] |
| Install Component Package |  | all contexts [vs] |
| Show All Items |  | all contexts [vs] |

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
| Debug with Extension Debugger |  | all contexts |
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
| Save All | Ctrl+S | all contexts |
| Save notes.md |  | all contexts |

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
| ROM Hacking > Add Patch |  | all contexts |
| ROM Hacking > Build Patched ROM |  | all contexts |
| ROM Hacking > Capture Edits as Patch |  | all contexts |
| ROM Hacking > Edit Working Copy |  | all contexts |
| ROM Hacking > Open Build Output |  | all contexts |
| ROM Hacking > Patch Manager |  | all contexts |
| ROM Hacking > Set Source ROM |  | all contexts |
| ROM Hacking > View Source ROM (read-only) |  | all contexts |
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
| Django / Flask / FastAPI Panel |  | all contexts |
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
| Claude Code |  | all contexts [agent,vscode] |
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
| More > Calibration Map Editor (full) |  | all contexts |
| More > Correct Checksums |  | all contexts |
| More > Detailed Firmware Analysis |  | all contexts |
| More > Find Checksums (from the original) |  | all contexts |
| More > Import A2L |  | all contexts |
| More > Load Checksum Profile |  | all contexts |
| More > Open Original (read-only hex editor) |  | all contexts |
| More > Open in Ghidra |  | all contexts |
| More > Save Working Copy As (binary) |  | all contexts |
| Analyze |  | all contexts |
| Build |  | all contexts |
| Compare |  | all contexts |
| Find Maps |  | all contexts |
| Map from Selection |  | all contexts |
| QLabel |  | all contexts |
| Save Version |  | all contexts |
| Verify Checksums |  | all contexts |

## Toolbar Mobile

| Item | Shortcut | Where |
|---|---|---|
| Hot Reload | Ctrl+Alt+R | all contexts |
| Hot Restart | Ctrl+Alt+Shift+R | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| Refresh devices |  | all contexts |

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
| Bookmark |  | all contexts |
| Clear |  | all contexts |
| Configure Data Source |  | all contexts |
| Coverage |  | all contexts |
| Debug |  | all contexts |
| Diagram |  | all contexts |
| Find |  | all contexts |
| Forward |  | all contexts |
| Go To |  | all contexts |
| New Query |  | all contexts |
| New Table |  | all contexts |
| Next Bookmark |  | all contexts |
| Open in Adminer |  | all contexts |
| Open in Browser |  | all contexts |
| Overwrite |  | all contexts |
| Preview Data |  | all contexts |
| QCheckBox |  | all contexts |
| QComboBox |  | all contexts |
| QLabel |  | all contexts |
| QLineEdit |  | all contexts |
| Refresh |  | all contexts |
| Refresh (re-read the columns and rows) |  | all contexts |
| Reload (F5 in the page) |  | all contexts |
| Remove Data Source |  | all contexts |
| Rotate |  | all contexts |
| Run |  | all contexts |
| Run All |  | all contexts |
| Run Failed |  | all contexts |
| Stop |  | all contexts |

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
| Extension Views > Claude Code |  | all contexts |
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
| Django / Flask / FastAPI Panel |  | all contexts |
| Document Outline |  | all contexts |
| Error List |  | all contexts |
| Extension Output |  | all contexts |
| Extensions (VS Code) | Ctrl+Shift+X | all contexts |
| Find All References Window |  | all contexts |
| Find Results |  | all contexts |
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
