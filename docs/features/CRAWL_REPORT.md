# Action crawler report

Run: 2026-11-22 18:29, 6021 s. Results: disabled: 1242, exception: 8, hang: 1, ok: 3198, skipped: 168, stale: 392, unresponsive: 7

| Context / layout | Scope | Entries harvested | Worker restarts |
|---|---|---|---|
| python-tk / vs | all | 957 | 1 |
| none / vs | specific | 757 | 0 |
| python-tk / vscode | specific | 963 | 0 |
| python-tk / agent | specific | 959 | 0 |
| vb6 / vs | specific | 916 | 0 |
| csharp / vs | specific | 896 | 0 |
| web / vs | specific | 792 | 0 |
| flask / vs | specific | 868 | 0 |
| flutter / vs | specific | 959 | 0 |
| retro / vs | specific | 784 | 0 |
| dos / vs | specific | 784 | 0 |
| game / vs | specific | 897 | 0 |
| asm / vs | specific | 892 | 0 |
| firmware / vs | specific | 819 | 0 |

| Action | Context | Result | Dialog | Time (s) | Error |
|---|---|---|---|---|---|
| Start local PostgreSQL | python-tk/vs | hang |  | 25.44 | still running in a nested event loop after 25s |
| Project > Python Commands > Run Tests (unittest) | flask/vs | exception |  | 0.62 | ------ unittest discover: failed (exit code 1) ------ |
| Solution Explorer > (project) > Python > Run Tests (unittest) | flask/vs | exception |  | 0.61 | ------ unittest discover: failed (exit code 1) ------ |
| Toolbar Toolbar > Collision | game/vs | exception |  | 0.6 | TypeError: SceneEditor._toggle_collision() missing 1 required positional argument: 'on' |
| Toolbar Toolbar > Grid | game/vs | exception |  | 0.61 | TypeError: SceneEditor._toggle_grid() missing 1 required positional argument: 'on' |
| Toolbar Toolbar > Snap | game/vs | exception |  | 0.61 | TypeError: SceneEditor._build_ui.<locals>.<lambda>() missing 1 required positional argument: 'on' |
| Tools > Retro > Text-Mode (DOS) > Build & Run in DOSBox-X | python-tk/vs | exception |  | 0.61 | AttributeError: 'builtin_function_or_method' object has no attribute 'path' |
| Tools > Retro > Text-Mode (DOS) > Generate Code | python-tk/vs | exception |  | 0.6 | AttributeError: 'builtin_function_or_method' object has no attribute 'path' |
| Tools > Retro > Text-Mode (DOS) > View Code | python-tk/vs | exception |  | 0.61 | AttributeError: 'builtin_function_or_method' object has no attribute 'path' |
| Command Palette > Preferences > Color Theme: Blue | python-tk/vs | unresponsive |  | 17.24 | UI thread blocked for 17.1s while the action ran |
| Command Palette > Preferences > Color Theme: Dark | python-tk/vs | unresponsive |  | 15.79 | UI thread blocked for 15.7s while the action ran |
| Command Palette > Preferences > Color Theme: High Contrast | python-tk/vs | unresponsive |  | 14.05 | UI thread blocked for 14.0s while the action ran |
| Menu bar corner > Agent | python-tk/vs | unresponsive |  | 10.9 | UI thread blocked for 10.4s while the action ran |
| Menu bar corner > Code | python-tk/vs | unresponsive |  | 12.07 | UI thread blocked for 11.6s while the action ran |
| Project > pygame Commands > Export to Godot | game/vs | unresponsive |  | 10.72 | UI thread blocked for 10.1s while the action ran |
| Toolbar Firmware > More > Find Checksums (from the original) | firmware/vs | unresponsive |  | 13.38 | UI thread blocked for 12.8s while the action ran |
| Analyze > Code Cleanup > Configure Code Cleanup | python-tk/vs | ok |  | 0.61 |  |
| Analyze > Code Cleanup > Run Code Cleanup on Document | python-tk/vs | ok |  | 0.6 |  |
| Analyze > Code Cleanup > Run Code Cleanup on Project | python-tk/vs | ok |  | 0.66 |  |
| Analyze > Code Cleanup > Run Code Cleanup on Solution | python-tk/vs | ok |  | 0.61 |  |
| Analyze > Configure Code Analysis (.editorconfig) | python-tk/vs | ok |  | 0.89 |  |
| Analyze > Decompile Assembly | python-tk/vs | ok |  | 0.62 |  |
| Analyze > Go To Decompiled Definition | python-tk/vs | ok |  | 0.61 |  |
| Analyze > Remove and Sort Usings | python-tk/vs | ok |  | 0.61 |  |
| Analyze > Run Code Analysis > On Current Project | python-tk/vs | ok |  | 0.61 |  |
| Analyze > Run Code Analysis > On Solution | python-tk/vs | ok |  | 0.6 |  |
| Analyze > Show Generated Files (Source Generators) | python-tk/vs | ok |  | 0.61 |  |
| BASIC > Add Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.79 |  |
| BASIC > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.94 |  |
| BASIC > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.8 |  |
| BASIC > Run (F5) | vb6/vs | ok |  | 0.64 |  |
| Build > Build Native Exe | python-tk/vs | ok | Build Native Exe [QMessageBox] | 0.92 |  |
| Build > Build Native Exe | none/vs | ok | Build Native Exe [QMessageBox] | 0.83 |  |
| Build > Build Native Exe | python-tk/vscode | ok | Build Native Exe [QMessageBox] | 0.82 |  |
| Build > Build Native Exe | python-tk/agent | ok | Build Native Exe [QMessageBox] | 0.84 |  |
| Build > Build Native Exe | vb6/vs | ok |  | 0.63 |  |
| Build > Build Native Exe | csharp/vs | ok |  | 0.64 |  |
| Build > Build Native Exe | web/vs | ok | Build Native Exe [QMessageBox] | 0.74 |  |
| Build > Build Native Exe | flask/vs | ok | Build Native Exe [QMessageBox] | 0.81 |  |
| Build > Build Native Exe | flutter/vs | ok | Build Native Exe [QMessageBox] | 0.79 |  |
| Build > Build Native Exe | retro/vs | ok | Build Native Exe [QMessageBox] | 0.73 |  |
| Build > Build Native Exe | dos/vs | ok | Build Native Exe [QMessageBox] | 0.84 |  |
| Build > Build Native Exe | game/vs | ok | Build Native Exe [QMessageBox] | 0.78 |  |
| Build > Build Native Exe | asm/vs | ok | Build Native Exe [QMessageBox] | 0.79 |  |
| Build > Build Native Exe | firmware/vs | ok | Build Native Exe [QMessageBox] | 0.81 |  |
| Build > Build Project | python-tk/vs | ok |  | 0.65 |  |
| Build > Build Project | none/vs | ok |  | 0.61 |  |
| Build > Build Project | python-tk/vscode | ok |  | 0.64 |  |
| Build > Build Project | python-tk/agent | ok |  | 0.66 |  |
| Build > Build Project | vb6/vs | ok |  | 0.63 |  |
| Build > Build Project | csharp/vs | ok |  | 0.66 |  |
| Build > Build Project | web/vs | ok |  | 0.61 |  |
| Build > Build Project | flask/vs | ok |  | 0.63 |  |
| Build > Build Project | flutter/vs | ok |  | 0.71 |  |
| Build > Build Project | retro/vs | ok |  | 0.61 |  |
| Build > Build Project | dos/vs | ok |  | 0.61 |  |
| Build > Build Project | game/vs | ok |  | 0.62 |  |
| Build > Build Project | asm/vs | ok |  | 0.63 |  |
| Build > Build Project | firmware/vs | ok |  | 0.62 |  |
| Build > Build Solution | python-tk/vs | ok |  | 0.63 |  |
| Build > Build Solution | none/vs | ok |  | 0.61 |  |
| Build > Build Solution | python-tk/vscode | ok |  | 0.63 |  |
| Build > Build Solution | python-tk/agent | ok |  | 0.74 |  |
| Build > Build Solution | vb6/vs | ok |  | 0.72 |  |
| Build > Build Solution | csharp/vs | ok |  | 0.63 |  |
| Build > Build Solution | web/vs | ok |  | 0.61 |  |
| Build > Build Solution | flask/vs | ok |  | 0.63 |  |
| Build > Build Solution | flutter/vs | ok |  | 0.7 |  |
| Build > Build Solution | retro/vs | ok |  | 0.62 |  |
| Build > Build Solution | dos/vs | ok |  | 0.62 |  |
| Build > Build Solution | game/vs | ok |  | 0.61 |  |
| Build > Build Solution | asm/vs | ok |  | 0.62 |  |
| Build > Build Solution | firmware/vs | ok |  | 0.61 |  |
| Build > Mobile App > Android APK | python-tk/vs | ok | Build [QMessageBox] | 0.86 |  |
| Build > Mobile App > Android APK | none/vs | ok | Build [QMessageBox] | 0.77 |  |
| Build > Mobile App > Android APK | python-tk/vscode | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Android APK | python-tk/agent | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Android APK | vb6/vs | ok | Build [QMessageBox] | 0.77 |  |
| Build > Mobile App > Android APK | csharp/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Android APK | web/vs | ok | Build [QMessageBox] | 0.73 |  |
| Build > Mobile App > Android APK | flask/vs | ok | Build [QMessageBox] | 0.73 |  |
| Build > Mobile App > Android APK | flutter/vs | ok |  | 0.84 |  |
| Build > Mobile App > Android APK | retro/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Android APK | dos/vs | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Android APK | game/vs | ok | Build [QMessageBox] | 0.74 |  |
| Build > Mobile App > Android APK | asm/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Android APK | firmware/vs | ok | Build [QMessageBox] | 0.8 |  |
| Build > Mobile App > Android APK (debug, faster) | python-tk/vs | ok | Build [QMessageBox] | 0.84 |  |
| Build > Mobile App > Android APK (debug, faster) | none/vs | ok | Build [QMessageBox] | 0.78 |  |
| Build > Mobile App > Android APK (debug, faster) | python-tk/vscode | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Android APK (debug, faster) | python-tk/agent | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Android APK (debug, faster) | vb6/vs | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Android APK (debug, faster) | csharp/vs | ok | Build [QMessageBox] | 0.77 |  |
| Build > Mobile App > Android APK (debug, faster) | web/vs | ok | Build [QMessageBox] | 0.85 |  |
| Build > Mobile App > Android APK (debug, faster) | flask/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Android APK (debug, faster) | flutter/vs | ok | Build [QMessageBox] | 0.76 |  |
| Build > Mobile App > Android APK (debug, faster) | retro/vs | ok | Build [QMessageBox] | 0.74 |  |
| Build > Mobile App > Android APK (debug, faster) | dos/vs | ok | Build [QMessageBox] | 0.78 |  |
| Build > Mobile App > Android APK (debug, faster) | game/vs | ok | Build [QMessageBox] | 0.76 |  |
| Build > Mobile App > Android APK (debug, faster) | asm/vs | ok | Build [QMessageBox] | 0.72 |  |
| Build > Mobile App > Android APK (debug, faster) | firmware/vs | ok | Build [QMessageBox] | 0.8 |  |
| Build > Mobile App > Create Foldable Emulator | python-tk/vs | ok | Create Foldable Emulator [QMessageBox] | 1.03 |  |
| Build > Mobile App > Create Foldable Emulator | none/vs | ok | Create Foldable Emulator [QMessageBox] | 0.98 |  |
| Build > Mobile App > Create Foldable Emulator | python-tk/vscode | ok | Create Foldable Emulator [QMessageBox] | 0.89 |  |
| Build > Mobile App > Create Foldable Emulator | python-tk/agent | ok | Create Foldable Emulator [QMessageBox] | 0.98 |  |
| Build > Mobile App > Create Foldable Emulator | vb6/vs | ok | Create Foldable Emulator [QMessageBox] | 0.89 |  |
| Build > Mobile App > Create Foldable Emulator | csharp/vs | ok | Create Foldable Emulator [QMessageBox] | 0.85 |  |
| Build > Mobile App > Create Foldable Emulator | web/vs | ok | Create Foldable Emulator [QMessageBox] | 0.86 |  |
| Build > Mobile App > Create Foldable Emulator | flask/vs | ok | Create Foldable Emulator [QMessageBox] | 0.81 |  |
| Build > Mobile App > Create Foldable Emulator | flutter/vs | ok | Create Foldable Emulator [QMessageBox] | 0.85 |  |
| Build > Mobile App > Create Foldable Emulator | retro/vs | ok | Create Foldable Emulator [QMessageBox] | 0.89 |  |
| Build > Mobile App > Create Foldable Emulator | dos/vs | ok | Create Foldable Emulator [QMessageBox] | 0.91 |  |
| Build > Mobile App > Create Foldable Emulator | game/vs | ok | Create Foldable Emulator [QMessageBox] | 0.82 |  |
| Build > Mobile App > Create Foldable Emulator | asm/vs | ok | Create Foldable Emulator [QMessageBox] | 0.88 |  |
| Build > Mobile App > Create Foldable Emulator | firmware/vs | ok | Create Foldable Emulator [QMessageBox] | 0.88 |  |
| Build > Mobile App > Web site | python-tk/vs | ok | Build [QMessageBox] | 0.93 |  |
| Build > Mobile App > Web site | none/vs | ok | Build [QMessageBox] | 0.8 |  |
| Build > Mobile App > Web site | python-tk/vscode | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Web site | python-tk/agent | ok | Build [QMessageBox] | 0.82 |  |
| Build > Mobile App > Web site | vb6/vs | ok | Build [QMessageBox] | 0.89 |  |
| Build > Mobile App > Web site | csharp/vs | ok | Build [QMessageBox] | 0.77 |  |
| Build > Mobile App > Web site | web/vs | ok | Build [QMessageBox] | 0.98 |  |
| Build > Mobile App > Web site | flask/vs | ok | Build [QMessageBox] | 0.76 |  |
| Build > Mobile App > Web site | flutter/vs | ok |  | 0.8 |  |
| Build > Mobile App > Web site | retro/vs | ok | Build [QMessageBox] | 0.78 |  |
| Build > Mobile App > Web site | dos/vs | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Web site | game/vs | ok | Build [QMessageBox] | 0.74 |  |
| Build > Mobile App > Web site | asm/vs | ok | Build [QMessageBox] | 0.73 |  |
| Build > Mobile App > Web site | firmware/vs | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Windows EXE | python-tk/vs | ok | Build [QMessageBox] | 0.86 |  |
| Build > Mobile App > Windows EXE | none/vs | ok | Build [QMessageBox] | 0.81 |  |
| Build > Mobile App > Windows EXE | python-tk/vscode | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Windows EXE | python-tk/agent | ok | Build [QMessageBox] | 0.83 |  |
| Build > Mobile App > Windows EXE | vb6/vs | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Windows EXE | csharp/vs | ok | Build [QMessageBox] | 0.76 |  |
| Build > Mobile App > Windows EXE | web/vs | ok | Build [QMessageBox] | 0.72 |  |
| Build > Mobile App > Windows EXE | flask/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Windows EXE | flutter/vs | ok | Build [QMessageBox] | 0.76 |  |
| Build > Mobile App > Windows EXE | retro/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Windows EXE | dos/vs | ok | Build [QMessageBox] | 0.79 |  |
| Build > Mobile App > Windows EXE | game/vs | ok | Build [QMessageBox] | 0.77 |  |
| Build > Mobile App > Windows EXE | asm/vs | ok | Build [QMessageBox] | 0.75 |  |
| Build > Mobile App > Windows EXE | firmware/vs | ok | Build [QMessageBox] | 0.8 |  |
| Build > Open Publish Folder | python-tk/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | none/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | python-tk/vscode | ok |  | 0.61 |  |
| Build > Open Publish Folder | python-tk/agent | ok |  | 0.61 |  |
| Build > Open Publish Folder | vb6/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | csharp/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | web/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | flask/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | flutter/vs | ok |  | 0.6 |  |
| Build > Open Publish Folder | retro/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | dos/vs | ok |  | 0.6 |  |
| Build > Open Publish Folder | game/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | asm/vs | ok |  | 0.61 |  |
| Build > Open Publish Folder | firmware/vs | ok |  | 0.61 |  |
| Build > Publish / Create Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] | 1.17 |  |
| Build > Publish / Create Installer | none/vs | ok | Publish [QMessageBox] | 0.76 |  |
| Build > Publish / Create Installer | python-tk/vscode | ok | Publish EvDemo [PublishDialog] | 0.99 |  |
| Build > Publish / Create Installer | python-tk/agent | ok | Publish EvDemo [PublishDialog] | 0.99 |  |
| Build > Publish / Create Installer | vb6/vs | ok | Publish [QMessageBox] | 0.78 |  |
| Build > Publish / Create Installer | csharp/vs | ok | Publish [QMessageBox] | 0.75 |  |
| Build > Publish / Create Installer | web/vs | ok | Publish Boot Site [PublishDialog] | 0.8 |  |
| Build > Publish / Create Installer | flask/vs | ok | Publish Flask_Todo [PublishDialog] | 0.91 |  |
| Build > Publish / Create Installer | flutter/vs | ok | Publish IdeProj [PublishDialog] | 0.86 |  |
| Build > Publish / Create Installer | retro/vs | ok | Publish NesStarCatcher [PublishDialog] | 0.81 |  |
| Build > Publish / Create Installer | dos/vs | ok | Publish Contacts [PublishDialog] | 0.92 |  |
| Build > Publish / Create Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.86 |  |
| Build > Publish / Create Installer | asm/vs | ok | Publish CoreNasmForms [PublishDialog] | 0.89 |  |
| Build > Publish / Create Installer | firmware/vs | ok | Publish CrawlEcu [PublishDialog] | 0.87 |  |
| Build > Refresh References | python-tk/vs | ok |  | 0.61 |  |
| Build > Refresh References | none/vs | ok |  | 0.61 |  |
| Build > Refresh References | python-tk/vscode | ok |  | 0.61 |  |
| Build > Refresh References | python-tk/agent | ok |  | 0.61 |  |
| Build > Refresh References | vb6/vs | ok |  | 0.61 |  |
| Build > Refresh References | csharp/vs | ok |  | 0.61 |  |
| Build > Refresh References | web/vs | ok |  | 0.61 |  |
| Build > Refresh References | flask/vs | ok |  | 0.61 |  |
| Build > Refresh References | flutter/vs | ok |  | 0.61 |  |
| Build > Refresh References | retro/vs | ok |  | 0.61 |  |
| Build > Refresh References | dos/vs | ok |  | 0.61 |  |
| Build > Refresh References | game/vs | ok |  | 0.61 |  |
| Build > Refresh References | asm/vs | ok |  | 0.61 |  |
| Build > Refresh References | firmware/vs | ok |  | 0.61 |  |
| Command Palette > AI > Agent Manager: New Task | python-tk/vs | ok |  | 0.62 |  |
| Command Palette > AI > Agent Manager: Show | python-tk/vs | ok |  | 0.63 |  |
| Command Palette > AI > Agent Manager: Stop All Tasks | python-tk/vs | ok |  | 0.62 |  |
| Command Palette > BASIC > Add Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.78 |  |
| Command Palette > BASIC > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.97 |  |
| Command Palette > BASIC > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.76 |  |
| Command Palette > BASIC > Run (F5) | vb6/vs | ok |  | 0.65 |  |
| Command Palette > Build > Build: Build Native Exe | python-tk/vs | ok | بناء ملف exe أصلي [QMessageBox] | 1.21 |  |
| Command Palette > Build > Build: Publish / Create Installer... | python-tk/vs | ok | Publish EvDemo [PublishDialog] | 1.48 |  |
| Command Palette > Claude Code for VS Code > Accept this change | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Accept Change at Cursor | python-tk/vs | ok |  | 0.67 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Accept Proposed Changes | python-tk/vs | ok |  | 0.7 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Accept Proposed Changes | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Add Session Tab to Group | python-tk/vs | ok |  | 0.62 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Add to Chat | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Blur input | python-tk/vs | ok |  | 0.6 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Focus input | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Focus last message | python-tk/vs | ok |  | 0.68 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Insert @-Mention Reference | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Insert At-Mentioned | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Install Plugin | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Logout | python-tk/vs | ok |  | 0.7 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Mark Session as Unread | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: New Conversation | python-tk/vs | ok |  | 0.69 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open | python-tk/vs | ok |  | 0.67 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open Walkthrough | python-tk/vs | ok |  | 0.67 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open in New Tab | python-tk/vs | ok |  | 0.65 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open in Primary Editor | python-tk/vs | ok |  | 0.67 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open in Side Bar | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Open in Terminal | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Reject Change at Cursor | python-tk/vs | ok |  | 0.81 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Reject Proposed Changes | python-tk/vs | ok |  | 0.6 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Reject Proposed Changes | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Rename Session Tab | python-tk/vs | ok |  | 0.71 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Reopen Closed Session | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Show Logs | python-tk/vs | ok |  | 0.69 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Toggle Focus view | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Claude Code for VS Code > Claude Code: Update extension | python-tk/vs | ok |  | 0.68 |  |
| Command Palette > Claude Code for VS Code > Reject this change | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > Debug > Debug with Extension Debugger | python-tk/vs | ok |  | 0.72 |  |
| Command Palette > Extensions > Extensions: Check for Extension Updates | python-tk/vs | ok |  | 0.82 |  |
| Command Palette > Extensions > Extensions: Install from VSIX... | python-tk/vs | ok | التثبيت من ملف VSIX [QFileDialog] | 5.02 |  |
| Command Palette > Extensions > Extensions: Show Extensions | python-tk/vs | ok |  | 1.32 |  |
| Command Palette > Extensions > Extensions: Update All Extensions | python-tk/vs | ok |  | 0.68 |  |
| Command Palette > Extensions > New Extension Terminal from Profile... | python-tk/vs | ok |  | 0.91 |  |
| Command Palette > Extensions > Open Extension URI... | python-tk/vs | ok | فتح Extension URI [QInputDialog] | 1.58 |  |
| Command Palette > Extensions > Restart Extension Host | python-tk/vs | ok |  | 1.66 |  |
| Command Palette > Extensions > Show Extension Output | python-tk/vs | ok |  | 0.64 |  |
| Command Palette > Flask > Flask Shell | flask/vs | ok |  | 0.61 |  |
| Command Palette > Flask > New Blueprint | flask/vs | ok |  | 0.68 |  |
| Command Palette > Flask > Routes | flask/vs | ok |  | 0.61 |  |
| Command Palette > Flask > Run Server | flask/vs | ok |  | 0.61 |  |
| Command Palette > Flask > Run flask Command | flask/vs | ok |  | 0.6 |  |
| Command Palette > Flutter > Analyze (flutter analyze) | flutter/vs | ok |  | 0.62 |  |
| Command Palette > Flutter > Build: Build APK (Android) | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > Build: Build Web | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > Build: Build Windows | flutter/vs | ok |  | 0.64 |  |
| Command Palette > Flutter > Clean (flutter clean) | flutter/vs | ok |  | 0.65 |  |
| Command Palette > Flutter > Flutter Doctor | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > Format Code (dart format) | flutter/vs | ok |  | 0.66 |  |
| Command Palette > Flutter > List Devices | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > New Screen (Form) | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.86 |  |
| Command Palette > Flutter > New Widget | flutter/vs | ok |  | 0.68 |  |
| Command Palette > Flutter > Packages: Add Package (pub add) | flutter/vs | ok |  | 0.61 |  |
| Command Palette > Flutter > Packages: pub get | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > Packages: pub outdated | flutter/vs | ok |  | 0.64 |  |
| Command Palette > Flutter > Packages: pub upgrade | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Flutter > Run (flutter run) | flutter/vs | ok |  | 0.94 |  |
| Command Palette > Flutter > Run Tests (flutter test) | flutter/vs | ok |  | 0.63 |  |
| Command Palette > Go > Go to Line/Column... | python-tk/vs | ok |  | 1.15 |  |
| Command Palette > Preferences > Color Theme: Light | python-tk/vs | ok |  | 1.33 |  |
| Command Palette > Preferences > Color Theme: System | python-tk/vs | ok |  | 1.72 |  |
| Command Palette > Preferences > File Icon Theme... | python-tk/vs | ok | سمة أيقونات الملفات [QInputDialog] | 1.53 |  |
| Command Palette > Project > Flutter: Add Google Font... | python-tk/vs | ok | Flutter [QMessageBox] | 1.34 |  |
| Command Palette > Project > Flutter: Add New Screen (visual designer)... | python-tk/vs | ok | Add New Screen [NewScreenDialog] | 2.69 |  |
| Command Palette > Project > Flutter: App Theme... | python-tk/vs | ok | Flutter [QMessageBox] | 1.51 |  |
| Command Palette > Project > Flutter: Import Screen from Dart... | python-tk/vs | ok | Import a Flutter screen [QFileDialog] | 2.43 |  |
| Command Palette > Project > Flutter: Project Assets... | python-tk/vs | ok | Flutter [QMessageBox] | 1.6 |  |
| Command Palette > Project > Project: Add Report... | python-tk/vs | ok | Add Report [AddReportDialog] | 2.02 |  |
| Command Palette > Python > Build EXE / Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] \| File Modification Detected [QMessageBox] | 1.94 |  |
| Command Palette > Python > Create .venv | python-tk/vs | ok |  | 0.62 |  |
| Command Palette > Python > Format and Lint: Fix Lint Problems (ruff check --fix) | python-tk/vs | ok |  | 0.67 |  |
| Command Palette > Python > Format and Lint: Format Project (black) | python-tk/vs | ok | File Modification Detected [QMessageBox] | 1.03 |  |
| Command Palette > Python > Format and Lint: Format Project (ruff) | python-tk/vs | ok |  | 0.64 |  |
| Command Palette > Python > Format and Lint: Lint Project (ruff check) | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > Python > Freeze to requirements.txt | python-tk/vs | ok |  | 0.64 |  |
| Command Palette > Python > List Installed Packages | python-tk/vs | ok |  | 0.64 |  |
| Command Palette > Python > Run Tests (pytest) | python-tk/vs | ok |  | 0.63 |  |
| Command Palette > Python > Run Tests (unittest) | python-tk/vs | ok |  | 0.62 |  |
| Command Palette > View > Focus Active Editor | python-tk/vs | ok |  | 0.61 |  |
| Command Palette > View > Show AI Chat | python-tk/vs | ok |  | 0.84 |  |
| Command Palette > View > Show AI Web Chats | python-tk/vs | ok |  | 0.79 |  |
| Command Palette > View > Show Agents | python-tk/vs | ok |  | 0.73 |  |
| Command Palette > View > Show Databases | python-tk/vs | ok |  | 0.66 |  |
| Command Palette > View > Show Explorer | python-tk/vs | ok |  | 0.98 |  |
| Command Palette > View > Show Run and Debug | python-tk/vs | ok |  | 0.71 |  |
| Command Palette > View > Show Search | python-tk/vs | ok |  | 1.51 |  |
| Command Palette > View > Show Source Control | python-tk/vs | ok |  | 0.68 |  |
| Command Palette > pygame > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.87 |  |
| Command Palette > pygame > Build One-File EXE (PyInstaller) | game/vs | ok |  | 0.61 |  |
| Command Palette > pygame > Export to Godot | game/vs | ok |  | 8.03 |  |
| Command Palette > pygame > Run Game | game/vs | ok |  | 0.62 |  |
| Data > Add New Data Source | python-tk/vs | ok |  | 0.62 |  |
| Data > Add New Data Source | none/vs | ok |  | 0.61 |  |
| Data > Add New Data Source | python-tk/vscode | ok |  | 0.61 |  |
| Data > Add New Data Source | python-tk/agent | ok |  | 0.61 |  |
| Data > Add New Data Source | vb6/vs | ok |  | 0.61 |  |
| Data > Add New Data Source | csharp/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | web/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | flask/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | flutter/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | retro/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | dos/vs | ok |  | 0.61 |  |
| Data > Add New Data Source | game/vs | ok |  | 0.6 |  |
| Data > Add New Data Source | asm/vs | ok |  | 0.61 |  |
| Data > Add New Data Source | firmware/vs | ok |  | 0.61 |  |
| Data > Preview Data | python-tk/vs | ok |  | 0.62 |  |
| Data > Preview Data | none/vs | ok |  | 0.61 |  |
| Data > Preview Data | python-tk/vscode | ok |  | 0.61 |  |
| Data > Preview Data | python-tk/agent | ok |  | 0.61 |  |
| Data > Preview Data | vb6/vs | ok |  | 0.6 |  |
| Data > Preview Data | csharp/vs | ok |  | 0.61 |  |
| Data > Preview Data | web/vs | ok |  | 0.61 |  |
| Data > Preview Data | flask/vs | ok |  | 0.6 |  |
| Data > Preview Data | flutter/vs | ok |  | 0.6 |  |
| Data > Preview Data | retro/vs | ok |  | 0.61 |  |
| Data > Preview Data | dos/vs | ok |  | 0.63 |  |
| Data > Preview Data | game/vs | ok |  | 0.61 |  |
| Data > Preview Data | asm/vs | ok |  | 0.61 |  |
| Data > Preview Data | firmware/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | python-tk/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | none/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | python-tk/vscode | ok |  | 0.6 |  |
| Data > Refresh Data Sources | python-tk/agent | ok |  | 0.61 |  |
| Data > Refresh Data Sources | vb6/vs | ok |  | 0.6 |  |
| Data > Refresh Data Sources | csharp/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | web/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | flask/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | flutter/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | retro/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | dos/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | game/vs | ok |  | 0.6 |  |
| Data > Refresh Data Sources | asm/vs | ok |  | 0.61 |  |
| Data > Refresh Data Sources | firmware/vs | ok |  | 0.61 |  |
| Data > Show Data Sources | python-tk/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | none/vs | ok |  | 0.64 |  |
| Data > Show Data Sources | python-tk/vscode | ok |  | 1.04 |  |
| Data > Show Data Sources | python-tk/agent | ok |  | 0.85 |  |
| Data > Show Data Sources | vb6/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | csharp/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | web/vs | ok |  | 0.63 |  |
| Data > Show Data Sources | flask/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | flutter/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | retro/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | dos/vs | ok |  | 0.96 |  |
| Data > Show Data Sources | game/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | asm/vs | ok |  | 0.62 |  |
| Data > Show Data Sources | firmware/vs | ok |  | 0.63 |  |
| Databases (QTreeWidget) > Add Connection | python-tk/vs | ok | Database Connection [ConnectionDialog] | 1.71 |  |
| Databases (QTreeWidget) > Add Connection | none/vs | ok | Database Connection [ConnectionDialog] | 1.33 |  |
| Databases (QTreeWidget) > Add Connection | vb6/vs | ok | Database Connection [ConnectionDialog] | 1.2 |  |
| Databases (QTreeWidget) > Add Connection | csharp/vs | ok | Database Connection [ConnectionDialog] | 1.03 |  |
| Databases (QTreeWidget) > Add Connection | web/vs | ok | Database Connection [ConnectionDialog] | 1.25 |  |
| Databases (QTreeWidget) > Add Connection | flutter/vs | ok | Database Connection [ConnectionDialog] | 1.32 |  |
| Databases (QTreeWidget) > Add Connection | retro/vs | ok | Database Connection [ConnectionDialog] | 1.14 |  |
| Databases (QTreeWidget) > Add Connection | dos/vs | ok | Database Connection [ConnectionDialog] | 1.52 |  |
| Databases (QTreeWidget) > Add Connection | game/vs | ok | Database Connection [ConnectionDialog] | 1.94 |  |
| Databases (QTreeWidget) > Add Connection | asm/vs | ok | Database Connection [ConnectionDialog] | 1.04 |  |
| Databases (QTreeWidget) > Add Connection | firmware/vs | ok | Database Connection [ConnectionDialog] | 1.2 |  |
| Databases (QTreeWidget) > Adminer (login page) | python-tk/vs | ok |  | 1.59 |  |
| Databases (QTreeWidget) > Adminer (login page) | none/vs | ok |  | 1.56 |  |
| Databases (QTreeWidget) > Adminer (login page) | vb6/vs | ok |  | 1.49 |  |
| Databases (QTreeWidget) > Adminer (login page) | csharp/vs | ok |  | 1.44 |  |
| Databases (QTreeWidget) > Adminer (login page) | web/vs | ok |  | 1.96 |  |
| Databases (QTreeWidget) > Adminer (login page) | flutter/vs | ok |  | 1.47 |  |
| Databases (QTreeWidget) > Adminer (login page) | retro/vs | ok |  | 1.46 |  |
| Databases (QTreeWidget) > Adminer (login page) | dos/vs | ok |  | 1.61 |  |
| Databases (QTreeWidget) > Adminer (login page) | game/vs | ok |  | 1.47 |  |
| Databases (QTreeWidget) > Adminer (login page) | asm/vs | ok |  | 1.38 |  |
| Databases (QTreeWidget) > Adminer (login page) | firmware/vs | ok |  | 1.38 |  |
| Databases (QTreeWidget) > Database Diagram | flask/vs | ok |  | 0.72 |  |
| Databases (QTreeWidget) > Export Database to SQL | flask/vs | ok | Export todo to SQL [QFileDialog] | 0.92 |  |
| Databases (QTreeWidget) > Import CSV into New Table | flask/vs | ok | Import CSV [ImportCsvDialog] | 0.83 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | python-tk/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | none/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | vb6/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | csharp/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | web/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | flutter/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | retro/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | dos/vs | ok |  | 0.63 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | game/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | asm/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy MariaDB/MySQL Password | firmware/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | python-tk/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | none/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | vb6/vs | ok |  | 0.6 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | csharp/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | web/vs | ok |  | 0.6 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | flutter/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | retro/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | dos/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | game/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | asm/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Copy PostgreSQL Password | firmware/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | python-tk/vs | ok | خوادم قواعد البيانات المحلية [QMessageBox] | 1.77 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | none/vs | ok | Local Database Servers [QMessageBox] | 1.27 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | vb6/vs | ok | Local Database Servers [QMessageBox] | 1.24 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | csharp/vs | ok | Local Database Servers [QMessageBox] | 1.23 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | web/vs | ok | Local Database Servers [QMessageBox] | 1.21 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | flutter/vs | ok | Local Database Servers [QMessageBox] | 1.32 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | retro/vs | ok | Local Database Servers [QMessageBox] | 1.31 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | dos/vs | ok | Local Database Servers [QMessageBox] | 1.56 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | game/vs | ok | Local Database Servers [QMessageBox] | 1.29 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | asm/vs | ok | Local Database Servers [QMessageBox] | 1.19 |  |
| Databases (QTreeWidget) > Local Servers > Server Status | firmware/vs | ok | Local Database Servers [QMessageBox] | 1.42 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | python-tk/vs | ok |  | 1.02 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | python-tk/vs | ok |  | 0.67 |  |
| Databases (QTreeWidget) > New Query | flask/vs | ok |  | 0.8 |  |
| Databases (QTreeWidget) > New SQLite Database | python-tk/vs | ok | قاعدة بيانات SQLite جديدة [QFileDialog] | 1.63 |  |
| Databases (QTreeWidget) > New SQLite Database | none/vs | ok | New SQLite database [QFileDialog] | 0.98 |  |
| Databases (QTreeWidget) > New SQLite Database | vb6/vs | ok | New SQLite database [QFileDialog] | 0.92 |  |
| Databases (QTreeWidget) > New SQLite Database | csharp/vs | ok | New SQLite database [QFileDialog] | 0.95 |  |
| Databases (QTreeWidget) > New SQLite Database | web/vs | ok | New SQLite database [QFileDialog] | 0.87 |  |
| Databases (QTreeWidget) > New SQLite Database | flutter/vs | ok | New SQLite database [QFileDialog] | 1.09 |  |
| Databases (QTreeWidget) > New SQLite Database | retro/vs | ok | New SQLite database [QFileDialog] | 0.98 |  |
| Databases (QTreeWidget) > New SQLite Database | dos/vs | ok | New SQLite database [QFileDialog] | 1.05 |  |
| Databases (QTreeWidget) > New SQLite Database | game/vs | ok | New SQLite database [QFileDialog] | 1.38 |  |
| Databases (QTreeWidget) > New SQLite Database | asm/vs | ok | New SQLite database [QFileDialog] | 0.86 |  |
| Databases (QTreeWidget) > New SQLite Database | firmware/vs | ok | New SQLite database [QFileDialog] | 1.09 |  |
| Databases (QTreeWidget) > New Table | flask/vs | ok | New Table [CreateTableDialog] | 0.91 |  |
| Databases (QTreeWidget) > Open in Adminer | flask/vs | ok |  | 1.41 |  |
| Databases (QTreeWidget) > Open in Adminer (new tab) | flask/vs | ok |  | 1.56 |  |
| Databases (QTreeWidget) > Properties | flask/vs | ok | Database Connection [ConnectionDialog] | 1.24 |  |
| Databases (QTreeWidget) > Refresh | python-tk/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Refresh | none/vs | ok |  | 0.6 |  |
| Databases (QTreeWidget) > Refresh | vb6/vs | ok |  | 0.6 |  |
| Databases (QTreeWidget) > Refresh | csharp/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Refresh | web/vs | ok |  | 0.6 |  |
| Databases (QTreeWidget) > Refresh | flask/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Refresh | flutter/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Refresh | retro/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Refresh | dos/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Refresh | game/vs | ok |  | 0.62 |  |
| Databases (QTreeWidget) > Refresh | asm/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Refresh | firmware/vs | ok |  | 0.61 |  |
| Databases (QTreeWidget) > Remove Connection | flask/vs | ok | Remove connection [QMessageBox] | 0.87 |  |
| Debug > 8086: Stop at First Instruction | python-tk/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | none/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | python-tk/vscode | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | python-tk/agent | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | vb6/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | csharp/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | web/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | flask/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | flutter/vs | ok |  | 0.6 |  |
| Debug > 8086: Stop at First Instruction | retro/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | dos/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | game/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | asm/vs | ok |  | 0.61 |  |
| Debug > 8086: Stop at First Instruction | firmware/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Assembly Checks Window | python-tk/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Assembly Checks Window | none/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | python-tk/agent | ok |  | 0.61 |  |
| Debug > Assembly Checks > Assembly Checks Window | vb6/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | csharp/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Assembly Checks Window | web/vs | ok |  | 0.62 |  |
| Debug > Assembly Checks > Assembly Checks Window | flask/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | flutter/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | retro/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | dos/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Assembly Checks Window | game/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | asm/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Assembly Checks Window | firmware/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check Selection | python-tk/vs | ok |  | 0.63 |  |
| Debug > Assembly Checks > Check Selection | none/vs | ok |  | 0.62 |  |
| Debug > Assembly Checks > Check Selection | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | python-tk/agent | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | vb6/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check Selection | csharp/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | web/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | flask/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check Selection | flutter/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | retro/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | dos/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check Selection | game/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check Selection | asm/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check Selection | firmware/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | python-tk/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | none/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | python-tk/agent | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | vb6/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check This Procedure | csharp/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | web/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | flask/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | flutter/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | retro/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check This Procedure | dos/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Check This Procedure | game/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | asm/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check This Procedure | firmware/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Check by Running | python-tk/vs | ok |  | 0.85 |  |
| Debug > Assembly Checks > Check by Running | none/vs | ok |  | 0.75 |  |
| Debug > Assembly Checks > Check by Running | python-tk/vscode | ok |  | 0.73 |  |
| Debug > Assembly Checks > Check by Running | python-tk/agent | ok |  | 0.72 |  |
| Debug > Assembly Checks > Check by Running | vb6/vs | ok |  | 0.71 |  |
| Debug > Assembly Checks > Check by Running | csharp/vs | ok |  | 0.69 |  |
| Debug > Assembly Checks > Check by Running | web/vs | ok |  | 0.71 |  |
| Debug > Assembly Checks > Check by Running | flask/vs | ok |  | 0.75 |  |
| Debug > Assembly Checks > Check by Running | flutter/vs | ok |  | 0.76 |  |
| Debug > Assembly Checks > Check by Running | retro/vs | ok |  | 0.74 |  |
| Debug > Assembly Checks > Check by Running | dos/vs | ok |  | 0.73 |  |
| Debug > Assembly Checks > Check by Running | game/vs | ok |  | 0.7 |  |
| Debug > Assembly Checks > Check by Running | asm/vs | ok |  | 0.7 |  |
| Debug > Assembly Checks > Check by Running | firmware/vs | ok |  | 0.71 |  |
| Debug > Assembly Checks > Explain This Line | python-tk/vs | ok |  | 0.62 |  |
| Debug > Assembly Checks > Explain This Line | none/vs | ok |  | 0.6 |  |
| Debug > Assembly Checks > Explain This Line | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | python-tk/agent | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | vb6/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | csharp/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | web/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | flask/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | flutter/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | retro/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | dos/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | game/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | asm/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > Explain This Line | firmware/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | python-tk/vs | ok |  | 0.64 |  |
| Debug > Assembly Checks > What-If Console | none/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | python-tk/agent | ok |  | 0.62 |  |
| Debug > Assembly Checks > What-If Console | vb6/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | csharp/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | web/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | flask/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | flutter/vs | ok |  | 0.62 |  |
| Debug > Assembly Checks > What-If Console | retro/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | dos/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | game/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | asm/vs | ok |  | 0.61 |  |
| Debug > Assembly Checks > What-If Console | firmware/vs | ok |  | 0.61 |  |
| Debug > Attach to Process | python-tk/vs | ok | Attach to Process [AttachDialog] | 1.41 |  |
| Debug > Attach to Process | none/vs | ok | Attach to Process [AttachDialog] | 0.93 |  |
| Debug > Attach to Process | python-tk/vscode | ok | Attach to Process [AttachDialog] | 0.96 |  |
| Debug > Attach to Process | python-tk/agent | ok | Attach to Process [AttachDialog] | 0.97 |  |
| Debug > Attach to Process | vb6/vs | ok | Attach to Process [AttachDialog] | 0.89 |  |
| Debug > Attach to Process | csharp/vs | ok | Attach to Process [AttachDialog] | 0.94 |  |
| Debug > Attach to Process | web/vs | ok | Attach to Process [AttachDialog] | 0.87 |  |
| Debug > Attach to Process | flask/vs | ok | Attach to Process [AttachDialog] | 0.81 |  |
| Debug > Attach to Process | flutter/vs | ok | Attach to Process [AttachDialog] | 0.94 |  |
| Debug > Attach to Process | retro/vs | ok | Attach to Process [AttachDialog] | 0.89 |  |
| Debug > Attach to Process | dos/vs | ok | Attach to Process [AttachDialog] | 0.9 |  |
| Debug > Attach to Process | game/vs | ok | Attach to Process [AttachDialog] | 0.88 |  |
| Debug > Attach to Process | asm/vs | ok | Attach to Process [AttachDialog] | 0.83 |  |
| Debug > Attach to Process | firmware/vs | ok | Attach to Process [AttachDialog] | 0.95 |  |
| Debug > Break All | python-tk/vs | ok |  | 0.61 |  |
| Debug > Break All | none/vs | ok |  | 0.61 |  |
| Debug > Break All | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Break All | python-tk/agent | ok |  | 0.61 |  |
| Debug > Break All | vb6/vs | ok |  | 0.6 |  |
| Debug > Break All | csharp/vs | ok |  | 0.61 |  |
| Debug > Break All | web/vs | ok |  | 0.61 |  |
| Debug > Break All | flask/vs | ok |  | 0.61 |  |
| Debug > Break All | flutter/vs | ok |  | 0.61 |  |
| Debug > Break All | retro/vs | ok |  | 0.6 |  |
| Debug > Break All | dos/vs | ok |  | 0.61 |  |
| Debug > Break All | game/vs | ok |  | 0.6 |  |
| Debug > Break All | asm/vs | ok |  | 0.61 |  |
| Debug > Break All | firmware/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | python-tk/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | none/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Break on Exceptions | python-tk/agent | ok |  | 0.61 |  |
| Debug > Break on Exceptions | vb6/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | csharp/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | web/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | flask/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | flutter/vs | ok |  | 0.6 |  |
| Debug > Break on Exceptions | retro/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | dos/vs | ok |  | 0.6 |  |
| Debug > Break on Exceptions | game/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | asm/vs | ok |  | 0.61 |  |
| Debug > Break on Exceptions | firmware/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | python-tk/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Condition | none/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | python-tk/agent | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | vb6/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | csharp/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Condition | web/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Condition | flask/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Condition | flutter/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | retro/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | dos/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | game/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Condition | asm/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Condition | firmware/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | python-tk/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | none/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | python-tk/agent | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | vb6/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | csharp/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | web/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | flask/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | flutter/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | retro/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | dos/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | game/vs | ok |  | 0.6 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | asm/vs | ok |  | 0.61 |  |
| Debug > Breakpoint Settings (Condition, Hit Count, Log) | firmware/vs | ok |  | 0.61 |  |
| Debug > CPU (OllyDbg Style) | python-tk/vs | ok |  | 0.86 |  |
| Debug > CPU (OllyDbg Style) | none/vs | ok |  | 0.65 |  |
| Debug > CPU (OllyDbg Style) | python-tk/vscode | ok |  | 0.83 |  |
| Debug > CPU (OllyDbg Style) | python-tk/agent | ok |  | 0.85 |  |
| Debug > CPU (OllyDbg Style) | vb6/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | csharp/vs | ok |  | 0.63 |  |
| Debug > CPU (OllyDbg Style) | web/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | flask/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | flutter/vs | ok |  | 0.66 |  |
| Debug > CPU (OllyDbg Style) | retro/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | dos/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | game/vs | ok |  | 0.64 |  |
| Debug > CPU (OllyDbg Style) | asm/vs | ok |  | 0.63 |  |
| Debug > CPU (OllyDbg Style) | firmware/vs | ok |  | 0.64 |  |
| Debug > CPU View at First Stop | python-tk/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | none/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | python-tk/vscode | ok |  | 0.6 |  |
| Debug > CPU View at First Stop | python-tk/agent | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | vb6/vs | ok |  | 0.6 |  |
| Debug > CPU View at First Stop | csharp/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | web/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | flask/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | flutter/vs | ok |  | 0.6 |  |
| Debug > CPU View at First Stop | retro/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | dos/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | game/vs | ok |  | 0.6 |  |
| Debug > CPU View at First Stop | asm/vs | ok |  | 0.61 |  |
| Debug > CPU View at First Stop | firmware/vs | ok |  | 0.61 |  |
| Debug > Debug Expo Web Page (js-debug) | python-tk/vs | ok | Debug Expo Web Page [QMessageBox] | 0.86 |  |
| Debug > Debug Expo Web Page (js-debug) | none/vs | ok | Debug Expo Web Page [QMessageBox] | 0.81 |  |
| Debug > Debug Expo Web Page (js-debug) | python-tk/vscode | ok | Debug Expo Web Page [QMessageBox] | 0.81 |  |
| Debug > Debug Expo Web Page (js-debug) | python-tk/agent | ok | Debug Expo Web Page [QMessageBox] | 0.81 |  |
| Debug > Debug Expo Web Page (js-debug) | vb6/vs | ok | Debug Expo Web Page [QMessageBox] | 0.77 |  |
| Debug > Debug Expo Web Page (js-debug) | csharp/vs | ok | Debug Expo Web Page [QMessageBox] | 0.75 |  |
| Debug > Debug Expo Web Page (js-debug) | web/vs | ok | Debug Expo Web Page [QMessageBox] | 0.75 |  |
| Debug > Debug Expo Web Page (js-debug) | flask/vs | ok | Debug Expo Web Page [QMessageBox] | 0.74 |  |
| Debug > Debug Expo Web Page (js-debug) | flutter/vs | ok | Debug Expo Web Page [QMessageBox] | 0.78 |  |
| Debug > Debug Expo Web Page (js-debug) | retro/vs | ok | Debug Expo Web Page [QMessageBox] | 0.74 |  |
| Debug > Debug Expo Web Page (js-debug) | dos/vs | ok | Debug Expo Web Page [QMessageBox] | 0.79 |  |
| Debug > Debug Expo Web Page (js-debug) | game/vs | ok | Debug Expo Web Page [QMessageBox] | 0.82 |  |
| Debug > Debug Expo Web Page (js-debug) | asm/vs | ok | Debug Expo Web Page [QMessageBox] | 0.79 |  |
| Debug > Debug Expo Web Page (js-debug) | firmware/vs | ok | Debug Expo Web Page [QMessageBox] | 0.82 |  |
| Debug > Debug with Extension Debugger | python-tk/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | none/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | python-tk/agent | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | vb6/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | csharp/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | web/vs | ok |  | 0.64 |  |
| Debug > Debug with Extension Debugger | flask/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | flutter/vs | ok |  | 0.6 |  |
| Debug > Debug with Extension Debugger | retro/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | dos/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | game/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | asm/vs | ok |  | 0.61 |  |
| Debug > Debug with Extension Debugger | firmware/vs | ok |  | 0.61 |  |
| Debug > Go To Disassembly | python-tk/vs | ok |  | 0.63 |  |
| Debug > Go To Disassembly | none/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | python-tk/vscode | ok |  | 0.83 |  |
| Debug > Go To Disassembly | python-tk/agent | ok |  | 0.85 |  |
| Debug > Go To Disassembly | vb6/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | csharp/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | web/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | flask/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | flutter/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | retro/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | dos/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | game/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | asm/vs | ok |  | 0.62 |  |
| Debug > Go To Disassembly | firmware/vs | ok |  | 0.62 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | python-tk/vs | ok |  | 0.62 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | none/vs | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | python-tk/agent | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | vb6/vs | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | csharp/vs | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | web/vs | ok |  | 0.6 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | flask/vs | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | flutter/vs | ok |  | 0.61 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | retro/vs | ok |  | 0.6 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | dos/vs | ok |  | 0.64 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | game/vs | ok |  | 0.6 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | asm/vs | ok |  | 0.6 |  |
| Debug > Mobile > Always Use the Dart Debugger for F5 | firmware/vs | ok |  | 0.6 |  |
| Debug > Mobile > Refresh devices | python-tk/vs | ok |  | 0.71 |  |
| Debug > Mobile > Refresh devices | none/vs | ok |  | 0.66 |  |
| Debug > Mobile > Refresh devices | python-tk/vscode | ok |  | 0.65 |  |
| Debug > Mobile > Refresh devices | python-tk/agent | ok |  | 0.63 |  |
| Debug > Mobile > Refresh devices | vb6/vs | ok |  | 0.64 |  |
| Debug > Mobile > Refresh devices | csharp/vs | ok |  | 0.63 |  |
| Debug > Mobile > Refresh devices | web/vs | ok |  | 0.66 |  |
| Debug > Mobile > Refresh devices | flask/vs | ok |  | 0.62 |  |
| Debug > Mobile > Refresh devices | flutter/vs | ok |  | 0.64 |  |
| Debug > Mobile > Refresh devices | retro/vs | ok |  | 0.63 |  |
| Debug > Mobile > Refresh devices | dos/vs | ok |  | 0.67 |  |
| Debug > Mobile > Refresh devices | game/vs | ok |  | 0.63 |  |
| Debug > Mobile > Refresh devices | asm/vs | ok |  | 0.63 |  |
| Debug > Mobile > Refresh devices | firmware/vs | ok |  | 0.62 |  |
| Debug > Run to Cursor | python-tk/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | none/vs | ok |  | 0.63 |  |
| Debug > Run to Cursor | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Run to Cursor | python-tk/agent | ok |  | 0.6 |  |
| Debug > Run to Cursor | vb6/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | csharp/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | web/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | flask/vs | ok |  | 0.6 |  |
| Debug > Run to Cursor | flutter/vs | ok |  | 0.6 |  |
| Debug > Run to Cursor | retro/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | dos/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | game/vs | ok |  | 0.6 |  |
| Debug > Run to Cursor | asm/vs | ok |  | 0.61 |  |
| Debug > Run to Cursor | firmware/vs | ok |  | 0.61 |  |
| Debug > Start Debugging / Continue | python-tk/vs | ok |  | 0.67 |  |
| Debug > Start Debugging / Continue | python-tk/vscode | ok |  | 0.88 |  |
| Debug > Start Debugging / Continue | python-tk/agent | ok |  | 0.93 |  |
| Debug > Start Debugging / Continue | vb6/vs | ok |  | 0.65 |  |
| Debug > Start Debugging / Continue | csharp/vs | ok |  | 0.65 |  |
| Debug > Start Debugging / Continue | web/vs | ok |  | 0.63 |  |
| Debug > Start Debugging / Continue | flask/vs | ok |  | 0.65 |  |
| Debug > Start Debugging / Continue | flutter/vs | ok |  | 0.81 |  |
| Debug > Start Debugging / Continue | retro/vs | ok |  | 0.63 |  |
| Debug > Start Debugging / Continue | dos/vs | ok |  | 0.63 |  |
| Debug > Start Debugging / Continue | game/vs | ok |  | 0.63 |  |
| Debug > Start Debugging / Continue | asm/vs | ok |  | 0.68 |  |
| Debug > Start Debugging / Continue | firmware/vs | ok |  | 0.62 |  |
| Debug > Start Without Debugging | python-tk/vs | ok |  | 0.69 |  |
| Debug > Start Without Debugging | python-tk/vscode | ok |  | 0.67 |  |
| Debug > Start Without Debugging | python-tk/agent | ok |  | 0.66 |  |
| Debug > Start Without Debugging | vb6/vs | ok |  | 0.68 |  |
| Debug > Start Without Debugging | csharp/vs | ok |  | 0.65 |  |
| Debug > Start Without Debugging | web/vs | ok |  | 0.61 |  |
| Debug > Start Without Debugging | flask/vs | ok |  | 0.62 |  |
| Debug > Start Without Debugging | flutter/vs | ok |  | 0.79 |  |
| Debug > Start Without Debugging | retro/vs | ok |  | 0.62 |  |
| Debug > Start Without Debugging | dos/vs | ok |  | 0.64 |  |
| Debug > Start Without Debugging | game/vs | ok |  | 0.63 |  |
| Debug > Start Without Debugging | asm/vs | ok |  | 0.67 |  |
| Debug > Start Without Debugging | firmware/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | python-tk/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | none/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Step Into Instruction | python-tk/agent | ok |  | 0.61 |  |
| Debug > Step Into Instruction | vb6/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | csharp/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | web/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | flask/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | flutter/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | retro/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | dos/vs | ok |  | 0.61 |  |
| Debug > Step Into Instruction | game/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | asm/vs | ok |  | 0.6 |  |
| Debug > Step Into Instruction | firmware/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | python-tk/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | none/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Step Over Instruction | python-tk/agent | ok |  | 0.6 |  |
| Debug > Step Over Instruction | vb6/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | csharp/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | web/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | flask/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | flutter/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | retro/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | dos/vs | ok |  | 0.6 |  |
| Debug > Step Over Instruction | game/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | asm/vs | ok |  | 0.61 |  |
| Debug > Step Over Instruction | firmware/vs | ok |  | 0.61 |  |
| Debug > Stop Debugging | web/vs | ok |  | 0.62 |  |
| Debug > Stop Debugging | flask/vs | ok |  | 0.77 |  |
| Debug > Watch | python-tk/vs | ok |  | 0.61 |  |
| Debug > Watch | none/vs | ok |  | 0.62 |  |
| Debug > Watch | python-tk/vscode | ok |  | 2.41 |  |
| Debug > Watch | python-tk/agent | ok |  | 0.61 |  |
| Debug > Watch | vb6/vs | ok |  | 0.61 |  |
| Debug > Watch | csharp/vs | ok |  | 0.61 |  |
| Debug > Watch | web/vs | ok |  | 0.6 |  |
| Debug > Watch | flask/vs | ok |  | 0.6 |  |
| Debug > Watch | flutter/vs | ok |  | 0.61 |  |
| Debug > Watch | retro/vs | ok |  | 0.61 |  |
| Debug > Watch | dos/vs | ok |  | 0.6 |  |
| Debug > Watch | game/vs | ok |  | 0.61 |  |
| Debug > Watch | asm/vs | ok |  | 0.61 |  |
| Debug > Watch | firmware/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | python-tk/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | none/vs | ok |  | 0.6 |  |
| Debug > Windows > Call Stack | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | vb6/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | csharp/vs | ok |  | 0.6 |  |
| Debug > Windows > Call Stack | web/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | flask/vs | ok |  | 0.6 |  |
| Debug > Windows > Call Stack | flutter/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | retro/vs | ok |  | 0.6 |  |
| Debug > Windows > Call Stack | dos/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | game/vs | ok |  | 0.6 |  |
| Debug > Windows > Call Stack | asm/vs | ok |  | 0.61 |  |
| Debug > Windows > Call Stack | firmware/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | python-tk/vs | ok |  | 0.62 |  |
| Debug > Windows > Disassembly | none/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | vb6/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | web/vs | ok |  | 0.6 |  |
| Debug > Windows > Disassembly | flask/vs | ok |  | 0.6 |  |
| Debug > Windows > Disassembly | flutter/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | retro/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | dos/vs | ok |  | 0.6 |  |
| Debug > Windows > Disassembly | game/vs | ok |  | 0.61 |  |
| Debug > Windows > Disassembly | asm/vs | ok |  | 0.6 |  |
| Debug > Windows > Disassembly | firmware/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | python-tk/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | none/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Immediate | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Immediate | vb6/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | web/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | flask/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | flutter/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | retro/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | dos/vs | ok |  | 0.61 |  |
| Debug > Windows > Immediate | game/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | asm/vs | ok |  | 0.6 |  |
| Debug > Windows > Immediate | firmware/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | python-tk/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | none/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Locals | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Locals | vb6/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | csharp/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | web/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | flask/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | flutter/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | retro/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | dos/vs | ok |  | 0.6 |  |
| Debug > Windows > Locals | game/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | asm/vs | ok |  | 0.61 |  |
| Debug > Windows > Locals | firmware/vs | ok |  | 0.6 |  |
| Debug > Windows > Memory 1 | python-tk/vs | ok |  | 0.63 |  |
| Debug > Windows > Memory 1 | none/vs | ok |  | 0.63 |  |
| Debug > Windows > Memory 1 | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Memory 1 | python-tk/agent | ok |  | 0.63 |  |
| Debug > Windows > Memory 1 | vb6/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | csharp/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | web/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | flask/vs | ok |  | 0.61 |  |
| Debug > Windows > Memory 1 | flutter/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | retro/vs | ok |  | 0.61 |  |
| Debug > Windows > Memory 1 | dos/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | game/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | asm/vs | ok |  | 0.62 |  |
| Debug > Windows > Memory 1 | firmware/vs | ok |  | 0.62 |  |
| Debug > Windows > Registers | python-tk/vs | ok |  | 0.65 |  |
| Debug > Windows > Registers | none/vs | ok |  | 0.63 |  |
| Debug > Windows > Registers | python-tk/vscode | ok |  | 0.62 |  |
| Debug > Windows > Registers | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Registers | vb6/vs | ok |  | 0.62 |  |
| Debug > Windows > Registers | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Registers | web/vs | ok |  | 0.62 |  |
| Debug > Windows > Registers | flask/vs | ok |  | 0.61 |  |
| Debug > Windows > Registers | flutter/vs | ok |  | 0.61 |  |
| Debug > Windows > Registers | retro/vs | ok |  | 0.62 |  |
| Debug > Windows > Registers | dos/vs | ok |  | 0.63 |  |
| Debug > Windows > Registers | game/vs | ok |  | 0.62 |  |
| Debug > Windows > Registers | asm/vs | ok |  | 0.61 |  |
| Debug > Windows > Registers | firmware/vs | ok |  | 0.61 |  |
| Debug > Windows > Stack | python-tk/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | none/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Stack | python-tk/agent | ok |  | 0.62 |  |
| Debug > Windows > Stack | vb6/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Stack | web/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | flask/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | flutter/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | retro/vs | ok |  | 0.61 |  |
| Debug > Windows > Stack | dos/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | game/vs | ok |  | 0.61 |  |
| Debug > Windows > Stack | asm/vs | ok |  | 0.62 |  |
| Debug > Windows > Stack | firmware/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | python-tk/vs | ok |  | 0.66 |  |
| Debug > Windows > Threads | none/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | python-tk/vscode | ok |  | 0.61 |  |
| Debug > Windows > Threads | python-tk/agent | ok |  | 0.62 |  |
| Debug > Windows > Threads | vb6/vs | ok |  | 0.62 |  |
| Debug > Windows > Threads | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | web/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | flask/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | flutter/vs | ok |  | 0.62 |  |
| Debug > Windows > Threads | retro/vs | ok |  | 0.61 |  |
| Debug > Windows > Threads | dos/vs | ok |  | 0.64 |  |
| Debug > Windows > Threads | game/vs | ok |  | 0.62 |  |
| Debug > Windows > Threads | asm/vs | ok |  | 0.62 |  |
| Debug > Windows > Threads | firmware/vs | ok |  | 0.62 |  |
| Debug > Windows > Watch | python-tk/vs | ok |  | 0.63 |  |
| Debug > Windows > Watch | none/vs | ok |  | 0.63 |  |
| Debug > Windows > Watch | python-tk/vscode | ok |  | 0.6 |  |
| Debug > Windows > Watch | python-tk/agent | ok |  | 0.61 |  |
| Debug > Windows > Watch | vb6/vs | ok |  | 0.62 |  |
| Debug > Windows > Watch | csharp/vs | ok |  | 0.61 |  |
| Debug > Windows > Watch | web/vs | ok |  | 0.61 |  |
| Debug > Windows > Watch | flask/vs | ok |  | 0.62 |  |
| Debug > Windows > Watch | flutter/vs | ok |  | 0.64 |  |
| Debug > Windows > Watch | retro/vs | ok |  | 0.61 |  |
| Debug > Windows > Watch | dos/vs | ok |  | 0.61 |  |
| Debug > Windows > Watch | game/vs | ok |  | 0.61 |  |
| Debug > Windows > Watch | asm/vs | ok |  | 0.62 |  |
| Debug > Windows > Watch | firmware/vs | ok |  | 0.61 |  |
| Designer > (control) > AI > Generate Event Handler for Button1 | python-tk/vs | ok | Generate Event Handler - Button1 [HandlerDialog] | 0.71 |  |
| Designer > (control) > AI > Generate New Form with AI | python-tk/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.72 |  |
| Designer > (control) > AI > Redesign This Form with AI | python-tk/vs | ok | Redesign Form with AI [GenerateFormDialog] | 0.72 |  |
| Designer > (control) > Add Animation > Attention > Bounce | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Attention > Flip | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Add Animation > Attention > Move | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Add Animation > Attention > Pulse | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Attention > Rotate | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Attention > Shake | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Attention > Zoom | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Add Animation > Color > Color | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Entrance > Fade In | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Entrance > Slide In | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Entrance > Zoom In | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Add Animation > Text > Typewriter | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Bring to Front | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Bring to Front | flutter/vs | ok |  | 0.62 |  |
| Designer > (control) > Bring to Front | asm/vs | ok |  | 0.61 |  |
| Designer > (control) > Copy | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Cut | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Cut | flutter/vs | ok |  | 0.74 |  |
| Designer > (control) > Cut | asm/vs | ok |  | 0.69 |  |
| Designer > (control) > Delete | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > Click | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Events > Click | asm/vs | ok |  | 0.7 |  |
| Designer > (control) > Events > DoubleClick | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Events > DoubleClick | asm/vs | ok |  | 0.71 |  |
| Designer > (control) > Events > GotFocus | python-tk/vs | ok |  | 0.64 |  |
| Designer > (control) > Events > GotFocus | asm/vs | ok |  | 0.71 |  |
| Designer > (control) > Events > KeyDown | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Events > KeyDown | asm/vs | ok |  | 0.72 |  |
| Designer > (control) > Events > KeyPress | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > KeyPress | asm/vs | ok |  | 0.71 |  |
| Designer > (control) > Events > KeyUp | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > KeyUp | asm/vs | ok |  | 0.75 |  |
| Designer > (control) > Events > LostFocus | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Events > LostFocus | asm/vs | ok |  | 0.72 |  |
| Designer > (control) > Events > MouseDown | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > MouseDown | asm/vs | ok |  | 0.76 |  |
| Designer > (control) > Events > MouseEnter | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > MouseEnter | asm/vs | ok |  | 0.7 |  |
| Designer > (control) > Events > MouseLeave | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > MouseLeave | asm/vs | ok |  | 0.7 |  |
| Designer > (control) > Events > MouseMove | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Events > MouseMove | asm/vs | ok |  | 0.7 |  |
| Designer > (control) > Events > MouseUp | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Events > MouseUp | asm/vs | ok |  | 0.73 |  |
| Designer > (control) > Events > MouseWheel | python-tk/vs | ok |  | 0.63 |  |
| Designer > (control) > Events > MouseWheel | asm/vs | ok |  | 0.72 |  |
| Designer > (control) > Layout Size > Add Size | python-tk/vs | ok | إضافة مقاس [QDialog] | 1.48 |  |
| Designer > (control) > Layout Size > All sizes | python-tk/vs | ok |  | 0.64 |  |
| Designer > (control) > Layout Size > Base design | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Layout Size > This size only | python-tk/vs | ok | إضافة مقاس [QDialog] | 1.41 |  |
| Designer > (control) > Lock Controls | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Paste | python-tk/vs | ok |  | 0.64 |  |
| Designer > (control) > Properties | python-tk/vs | ok |  | 0.62 |  |
| Designer > (control) > Send to Back | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > Send to Back | flutter/vs | ok |  | 0.61 |  |
| Designer > (control) > Send to Back | asm/vs | ok |  | 0.62 |  |
| Designer > (control) > View Code | python-tk/vs | ok |  | 0.61 |  |
| Designer > (control) > View Code | flutter/vs | ok |  | 0.75 |  |
| Designer > (control) > View Code | asm/vs | ok |  | 0.7 |  |
| Designer > (form) > AI > Generate Event Handler for Form1 | python-tk/vs | ok | Generate Event Handler - Form1 [HandlerDialog] | 0.67 |  |
| Designer > (form) > AI > Generate Event Handler for Form1 | asm/vs | ok | Generate Event Handler - Form1 [HandlerDialog] | 0.66 |  |
| Designer > (form) > AI > Generate Event Handler for MainScreen | flutter/vs | ok | Generate Event Handler - MainScreen [HandlerDialog] | 0.65 |  |
| Designer > (form) > AI > Generate New Form with AI | python-tk/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.7 |  |
| Designer > (form) > AI > Generate New Form with AI | flutter/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.69 |  |
| Designer > (form) > AI > Generate New Form with AI | asm/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.66 |  |
| Designer > (form) > AI > Redesign This Form with AI | python-tk/vs | ok | Redesign Form with AI [GenerateFormDialog] | 0.72 |  |
| Designer > (form) > AI > Redesign This Form with AI | flutter/vs | ok | Redesign Form with AI [GenerateFormDialog] | 0.67 |  |
| Designer > (form) > AI > Redesign This Form with AI | asm/vs | ok | Redesign Form with AI [GenerateFormDialog] | 0.65 |  |
| Designer > (form) > Add Animation > Attention > Bounce | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Bounce | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Bounce | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Flip | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Flip | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Flip | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Move | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Move | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Move | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Pulse | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Pulse | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Pulse | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Rotate | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Rotate | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Rotate | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Add Animation > Attention > Shake | python-tk/vs | ok |  | 0.64 |  |
| Designer > (form) > Add Animation > Attention > Shake | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Shake | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Attention > Zoom | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Zoom | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Attention > Zoom | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Color > Color | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Color > Color | flutter/vs | ok |  | 0.65 |  |
| Designer > (form) > Add Animation > Color > Color | asm/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Entrance > Fade In | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Entrance > Fade In | flutter/vs | ok |  | 0.77 |  |
| Designer > (form) > Add Animation > Entrance > Fade In | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Add Animation > Entrance > Slide In | python-tk/vs | ok |  | 0.64 |  |
| Designer > (form) > Add Animation > Entrance > Slide In | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Entrance > Slide In | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Entrance > Zoom In | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Entrance > Zoom In | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Entrance > Zoom In | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Add Animation > Text > Typewriter | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Add Animation > Text > Typewriter | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Add Animation > Text > Typewriter | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Add Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 1.97 |  |
| Designer > (form) > Add Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.92 |  |
| Designer > (form) > Add Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.82 |  |
| Designer > (form) > Cut | python-tk/vs | ok |  | 0.83 |  |
| Designer > (form) > Cut | flutter/vs | ok |  | 0.71 |  |
| Designer > (form) > Cut | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Delete | python-tk/vs | ok |  | 0.82 |  |
| Designer > (form) > Delete | flutter/vs | ok |  | 0.73 |  |
| Designer > (form) > Delete | asm/vs | ok |  | 0.67 |  |
| Designer > (form) > Events > Activated | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Events > Activated | asm/vs | ok |  | 0.7 |  |
| Designer > (form) > Events > Click | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Events > Click | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Events > Deactivate | python-tk/vs | ok |  | 0.64 |  |
| Designer > (form) > Events > Deactivate | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Events > DoubleClick | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Events > DoubleClick | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Events > FormClosed | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > FormClosed | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Events > FormClosing | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > FormClosing | asm/vs | ok |  | 0.67 |  |
| Designer > (form) > Events > KeyDown | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Events > KeyDown | asm/vs | ok |  | 0.7 |  |
| Designer > (form) > Events > KeyPress | python-tk/vs | ok |  | 0.64 |  |
| Designer > (form) > Events > KeyPress | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Events > KeyUp | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > KeyUp | asm/vs | ok |  | 0.67 |  |
| Designer > (form) > Events > Load | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Events > Load | flutter/vs | ok |  | 0.71 |  |
| Designer > (form) > Events > Load | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Events > MouseDown | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > MouseDown | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Events > MouseMove | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > MouseMove | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Events > MouseUp | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Events > MouseUp | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Events > MouseWheel | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Events > MouseWheel | asm/vs | ok |  | 0.69 |  |
| Designer > (form) > Events > Resize | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Events > Resize | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Layout Size > Add Size | python-tk/vs | ok | إضافة مقاس [QDialog] | 1.4 |  |
| Designer > (form) > Layout Size > Add Size | flutter/vs | ok | Add Size [QDialog] | 0.91 |  |
| Designer > (form) > Layout Size > Add Size | asm/vs | ok | Add Size [QDialog] | 0.73 |  |
| Designer > (form) > Layout Size > All sizes | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Layout Size > All sizes | flutter/vs | ok |  | 0.62 |  |
| Designer > (form) > Layout Size > All sizes | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Layout Size > Base design | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Layout Size > Base design | flutter/vs | ok |  | 0.65 |  |
| Designer > (form) > Layout Size > Base design | asm/vs | ok |  | 0.62 |  |
| Designer > (form) > Layout Size > This size only | python-tk/vs | ok | إضافة مقاس [QDialog] | 1.36 |  |
| Designer > (form) > Layout Size > This size only | flutter/vs | ok | Add Size [QDialog] | 0.96 |  |
| Designer > (form) > Layout Size > This size only | asm/vs | ok | Add Size [QDialog] | 0.72 |  |
| Designer > (form) > Localization Strings | python-tk/vs | ok |  | 0.61 |  |
| Designer > (form) > Localization Strings | python-tk/vscode | ok |  | 0.61 |  |
| Designer > (form) > Localization Strings | python-tk/agent | ok |  | 0.61 |  |
| Designer > (form) > Localization Strings | vb6/vs | ok |  | 0.6 |  |
| Designer > (form) > Localization Strings | csharp/vs | ok |  | 0.6 |  |
| Designer > (form) > Localization Strings | flutter/vs | ok | Localization - MainScreen [QDialog] | 0.97 |  |
| Designer > (form) > Localization Strings | asm/vs | ok | Localization - Form1 [QDialog] | 0.79 |  |
| Designer > (form) > Lock Controls | python-tk/vs | ok |  | 0.62 |  |
| Designer > (form) > Lock Controls | flutter/vs | ok |  | 0.63 |  |
| Designer > (form) > Lock Controls | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Paste | python-tk/vs | ok |  | 0.73 |  |
| Designer > (form) > Paste | flutter/vs | ok |  | 0.71 |  |
| Designer > (form) > Paste | asm/vs | ok |  | 0.68 |  |
| Designer > (form) > Properties | python-tk/vs | ok |  | 0.63 |  |
| Designer > (form) > Properties | flutter/vs | ok |  | 0.61 |  |
| Designer > (form) > Properties | asm/vs | ok |  | 0.61 |  |
| Designer > (form) > Select All | python-tk/vs | ok |  | 0.77 |  |
| Designer > (form) > Select All | flutter/vs | ok |  | 0.7 |  |
| Designer > (form) > Select All | asm/vs | ok |  | 0.65 |  |
| Designer > (form) > View Code | python-tk/vs | ok |  | 0.76 |  |
| Designer > (form) > View Code | flutter/vs | ok |  | 0.72 |  |
| Designer > (form) > View Code | asm/vs | ok |  | 0.67 |  |
| Edit > AI > Add Comments | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Edit with AI | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Explain | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Fix | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Generate Docs | python-tk/vs | ok |  | 0.6 |  |
| Edit > AI > Generate Tests | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Inline Completions | python-tk/vs | ok |  | 0.64 |  |
| Edit > AI > Refactor | python-tk/vs | ok |  | 0.61 |  |
| Edit > AI > Suggest Inline Completion | python-tk/vs | ok |  | 0.6 |  |
| Edit > Emmet: Expand Abbreviation | python-tk/vs | ok |  | 0.62 |  |
| Edit > Find | python-tk/vs | ok |  | 0.62 |  |
| Edit > Find Next | python-tk/vs | ok |  | 0.61 |  |
| Edit > Find Previous | python-tk/vs | ok |  | 0.61 |  |
| Edit > Find in Files | python-tk/vs | ok | Find and Replace [FindInFilesDialog] | 0.91 |  |
| Edit > Format Document | python-tk/vs | ok |  | 0.61 |  |
| Edit > Format on Save | python-tk/vs | ok |  | 0.63 |  |
| Edit > Go to Definition | python-tk/vs | ok |  | 0.61 |  |
| Edit > Go to Line | python-tk/vs | ok |  | 0.6 |  |
| Edit > Insert Snippet | python-tk/vs | ok |  | 0.6 |  |
| Edit > IntelliSense > Remove and Sort Usings | python-tk/vs | ok |  | 0.61 |  |
| Edit > IntelliSense > Sort Usings | python-tk/vs | ok |  | 0.6 |  |
| Edit > Language Mode | python-tk/vs | ok |  | 0.6 |  |
| Edit > Open as PHP | python-tk/vs | ok |  | 0.61 |  |
| Edit > Paste | python-tk/vs | ok |  | 0.61 |  |
| Edit > Refactor > Extract Method | python-tk/vs | ok |  | 0.6 |  |
| Edit > Refactor > Extract Variable | python-tk/vs | ok |  | 0.6 |  |
| Edit > Refactor > Find All References | python-tk/vs | ok |  | 0.6 |  |
| Edit > Refactor > Quick Actions and Refactorings | python-tk/vs | ok |  | 0.61 |  |
| Edit > Refactor > Rename | python-tk/vs | ok |  | 0.61 |  |
| Edit > Replace | python-tk/vs | ok |  | 0.61 |  |
| Edit > Select All | python-tk/vs | ok |  | 0.68 |  |
| Editor tab > Close | python-tk/vs | ok |  | 0.87 |  |
| Editor tab > Close | none/vs | ok |  | 0.68 |  |
| Editor tab > Close | python-tk/vscode | ok |  | 1.27 |  |
| Editor tab > Close | python-tk/agent | ok |  | 0.68 |  |
| Editor tab > Close | vb6/vs | ok |  | 0.66 |  |
| Editor tab > Close | csharp/vs | ok |  | 0.67 |  |
| Editor tab > Close | web/vs | ok |  | 0.67 |  |
| Editor tab > Close | flutter/vs | ok |  | 0.71 |  |
| Editor tab > Close | retro/vs | ok |  | 0.67 |  |
| Editor tab > Close | dos/vs | ok |  | 0.7 |  |
| Editor tab > Close | game/vs | ok |  | 0.74 |  |
| Editor tab > Close | asm/vs | ok |  | 0.66 |  |
| Editor tab > Close | firmware/vs | ok |  | 0.68 |  |
| Editor tab > Close All | python-tk/vs | ok |  | 0.76 |  |
| Editor tab > Close All | none/vs | ok |  | 0.65 |  |
| Editor tab > Close All | python-tk/vscode | ok |  | 1.08 |  |
| Editor tab > Close All | python-tk/agent | ok |  | 0.72 |  |
| Editor tab > Close All | vb6/vs | ok |  | 0.66 |  |
| Editor tab > Close All | csharp/vs | ok |  | 0.66 |  |
| Editor tab > Close All | web/vs | ok |  | 0.67 |  |
| Editor tab > Close All | flutter/vs | ok |  | 0.68 |  |
| Editor tab > Close All | retro/vs | ok |  | 0.66 |  |
| Editor tab > Close All | dos/vs | ok |  | 0.71 |  |
| Editor tab > Close All | game/vs | ok |  | 0.71 |  |
| Editor tab > Close All | asm/vs | ok |  | 0.66 |  |
| Editor tab > Close All | firmware/vs | ok |  | 0.66 |  |
| Editor tab > Close All But This | python-tk/vs | ok |  | 3.74 |  |
| Editor tab > Close All But This | none/vs | ok |  | 0.61 |  |
| Editor tab > Close All But This | python-tk/vscode | ok |  | 2.08 |  |
| Editor tab > Close All But This | python-tk/agent | ok |  | 1.34 |  |
| Editor tab > Close All But This | vb6/vs | ok |  | 0.83 |  |
| Editor tab > Close All But This | csharp/vs | ok |  | 1.02 |  |
| Editor tab > Close All But This | web/vs | ok |  | 0.68 |  |
| Editor tab > Close All But This | flutter/vs | ok |  | 1.26 |  |
| Editor tab > Close All But This | retro/vs | ok |  | 0.69 |  |
| Editor tab > Close All But This | dos/vs | ok |  | 0.76 |  |
| Editor tab > Close All But This | game/vs | ok |  | 0.89 |  |
| Editor tab > Close All But This | asm/vs | ok |  | 0.87 |  |
| Editor tab > Close All But This | firmware/vs | ok |  | 1.33 |  |
| File > Add > Existing Project | python-tk/vs | ok | Add Existing Project [QFileDialog] | 1.03 |  |
| File > Add > New Project | python-tk/vs | ok | New Project [NewProjectDialog] | 1.92 |  |
| File > App Gallery | python-tk/vs | ok | App Gallery [AppGalleryDialog] | 1.24 |  |
| File > Close Solution | python-tk/vs | ok |  | 0.98 |  |
| File > Import > Program (.exe / .dll) | python-tk/vs | ok | Import Program (.exe / .dll) [ExeImportWizard] | 0.96 |  |
| File > Import > Python GUI Program (Tkinter / Qt) | python-tk/vs | ok | Import Python GUI Program [QFileDialog] | 1.13 |  |
| File > Import > Visual Basic 6 Project (.vbp / .frm) | python-tk/vs | ok | Import Visual Basic 6 Project [QFileDialog] | 1.07 |  |
| File > Migrate Project | python-tk/vs | ok | Migrate Project [MigrateWizard] | 0.96 |  |
| File > New Image > Cursor (.cur) | python-tk/vs | ok | New Image [NewImageDialog] | 0.83 |  |
| File > New Image > Icon (.ico) | python-tk/vs | ok | New Image [NewImageDialog] | 0.84 |  |
| File > New Image > Image (.png / .bmp) | python-tk/vs | ok | New Image [NewImageDialog] | 0.81 |  |
| File > New Notebook > Blank Notebook (.ipynb) | python-tk/vs | ok | New Notebook [QFileDialog] | 0.99 |  |
| File > New Notebook > Data Science Starter (pandas + matplotlib) | python-tk/vs | ok | New Notebook [QFileDialog] | 1.1 |  |
| File > New Notebook > Import Python Script as Notebook | python-tk/vs | ok | Import Python Script as Notebook [QFileDialog] | 1.72 |  |
| File > New Notebook > Open Notebook | python-tk/vs | ok | Open Notebook [QFileDialog] | 1.23 |  |
| File > New Project | python-tk/vs | ok | New Project [NewProjectDialog] | 3.07 |  |
| File > New Project (.NET, Visual Studio 2022) | python-tk/vs | ok | Create a new project [NewProjectWizard] | 1.55 |  |
| File > New Solution from Existing Folders | python-tk/vs | ok | New Solution from Existing Folders [NewSolutionFromFolders] | 0.9 |  |
| File > Open File | python-tk/vs | ok | Open File [QFileDialog] | 1.0 |  |
| File > Open Folder | python-tk/vs | ok | Open Folder [QFileDialog] | 1.04 |  |
| File > Open Project | python-tk/vs | ok | Open Project/Solution [QFileDialog] | 1.07 |  |
| File > Open Remote > Connect to SSH Host | python-tk/vs | ok | Connect to SSH Host [SSHDialog] | 0.83 |  |
| File > Open Remote > Open Folder in Dev Container | python-tk/vs | ok | Folder with .devcontainer [QFileDialog] | 1.0 |  |
| File > Open Remote > Open WSL Folder | python-tk/vs | ok | Open WSL Folder [QDialog] | 1.15 |  |
| File > Open Remote > Remote Explorer | python-tk/vs | ok |  | 0.62 |  |
| File > Open in Design View | python-tk/vs | ok | Open in Design View [QFileDialog] | 1.38 |  |
| File > Open in Hex Editor > Current File | python-tk/vs | ok | Open in Hex Editor [QFileDialog] | 0.97 |  |
| File > Open in Hex Editor > File | python-tk/vs | ok | Open in Hex Editor [QFileDialog] | 1.03 |  |
| File > Recent Projects and Solutions > 1  asm  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\asm-vs\projects\asm | asm/vs | ok |  | 0.87 |  |
| File > Recent Projects and Solutions > 1  csharp  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\csharp-vs\projects\csh | csharp/vs | ok |  | 1.52 |  |
| File > Recent Projects and Solutions > 1  dos  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\dos-vs\projects\dos | dos/vs | ok |  | 1.73 |  |
| File > Recent Projects and Solutions > 1  firmware  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\firmware-vs\projects | firmware/vs | ok |  | 0.85 |  |
| File > Recent Projects and Solutions > 1  flask  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\flask-vs\projects\flask | flask/vs | ok |  | 0.63 |  |
| File > Recent Projects and Solutions > 1  flutter  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\flutter-vs\projects\f | flutter/vs | ok |  | 1.44 |  |
| File > Recent Projects and Solutions > 1  game  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\game-vs\projects\game | game/vs | ok |  | 2.06 |  |
| File > Recent Projects and Solutions > 1  python-tk  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\python-tk-agent\pro | python-tk/agent | ok |  | 1.68 |  |
| File > Recent Projects and Solutions > 1  python-tk  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\python-tk-vs\projec | python-tk/vs | ok |  | 1.57 |  |
| File > Recent Projects and Solutions > 1  python-tk  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\python-tk-vscode\pr | python-tk/vscode | ok |  | 1.63 |  |
| File > Recent Projects and Solutions > 1  retro  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\retro-vs\projects\retro | retro/vs | ok |  | 0.77 |  |
| File > Recent Projects and Solutions > 1  vb6  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\vb6-vs\projects\vb6 | vb6/vs | ok |  | 1.62 |  |
| File > Recent Projects and Solutions > 1  web  -  C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\crawl\run3\sandbox\web-vs\projects\web | web/vs | ok |  | 0.65 |  |
| File > Recent Projects and Solutions > Clear List | python-tk/vs | ok |  | 0.61 |  |
| File > Save All | python-tk/vs | ok |  | 0.67 |  |
| File > Save Form1.form [Design] | python-tk/vs | ok |  | 0.62 |  |
| File > Save MAIN.BAS | dos/vs | ok |  | 0.61 |  |
| File > Save MainScreen.form [Design] | flutter/vs | ok |  | 0.61 |  |
| File > Save frmGreeter.form [Design] | vb6/vs | ok |  | 0.6 |  |
| File > Save index.html | web/vs | ok |  | 0.6 |  |
| File > Save main.py | game/vs | ok |  | 0.61 |  |
| File > Save main.s | retro/vs | ok |  | 0.6 |  |
| File > Save notes.md | firmware/vs | ok |  | 0.64 |  |
| Flask (QTreeWidget) > Copy Name | flask/vs | ok |  | 0.61 |  |
| Flask (QTreeWidget) > Go to View | flask/vs | ok |  | 0.76 |  |
| Flask (QTreeWidget) > Open in Preview | flask/vs | ok |  | 0.61 |  |
| Flask > Flask Shell | flask/vs | ok |  | 0.61 |  |
| Flask > New Blueprint | flask/vs | ok |  | 0.63 |  |
| Flask > Routes | flask/vs | ok |  | 0.61 |  |
| Flask > Run Server | flask/vs | ok |  | 0.61 |  |
| Flask > Run flask Command | flask/vs | ok |  | 0.6 |  |
| Flutter > Analyze (flutter analyze) | flutter/vs | ok |  | 0.62 |  |
| Flutter > Build > Build APK (Android) | flutter/vs | ok |  | 0.62 |  |
| Flutter > Build > Build Web | flutter/vs | ok |  | 0.62 |  |
| Flutter > Build > Build Windows | flutter/vs | ok |  | 0.62 |  |
| Flutter > Clean (flutter clean) | flutter/vs | ok |  | 0.62 |  |
| Flutter > Flutter Doctor | flutter/vs | ok |  | 0.62 |  |
| Flutter > Format Code (dart format) | flutter/vs | ok |  | 0.63 |  |
| Flutter > List Devices | flutter/vs | ok |  | 0.62 |  |
| Flutter > New Screen (Form) | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.83 |  |
| Flutter > New Widget | flutter/vs | ok |  | 0.61 |  |
| Flutter > Packages > Add Package (pub add) | flutter/vs | ok |  | 0.61 |  |
| Flutter > Packages > pub get | flutter/vs | ok |  | 0.63 |  |
| Flutter > Packages > pub outdated | flutter/vs | ok |  | 0.62 |  |
| Flutter > Packages > pub upgrade | flutter/vs | ok |  | 0.62 |  |
| Flutter > Run (flutter run) | flutter/vs | ok |  | 0.94 |  |
| Flutter > Run Tests (flutter test) | flutter/vs | ok |  | 0.62 |  |
| Flutter > Stop Running Command | flutter/vs | ok |  | 1.09 |  |
| Format > Localization Strings | python-tk/vs | ok |  | 0.61 |  |
| Format > Localization Strings | none/vs | ok |  | 0.6 |  |
| Format > Localization Strings | python-tk/vscode | ok |  | 0.6 |  |
| Format > Localization Strings | python-tk/agent | ok |  | 0.61 |  |
| Format > Localization Strings | vb6/vs | ok |  | 0.61 |  |
| Format > Localization Strings | csharp/vs | ok |  | 0.6 |  |
| Format > Localization Strings | web/vs | ok |  | 0.61 |  |
| Format > Localization Strings | flask/vs | ok |  | 0.61 |  |
| Format > Localization Strings | flutter/vs | ok |  | 0.61 |  |
| Format > Localization Strings | retro/vs | ok |  | 0.61 |  |
| Format > Localization Strings | dos/vs | ok |  | 0.61 |  |
| Format > Localization Strings | game/vs | ok |  | 0.61 |  |
| Format > Localization Strings | asm/vs | ok |  | 0.61 |  |
| Format > Localization Strings | firmware/vs | ok |  | 0.61 |  |
| Game > Export to Godot | game/vs | ok |  | 8.37 |  |
| Game > Game Assets Window | game/vs | ok |  | 0.61 |  |
| Game > New Scene | game/vs | ok | New Scene [QInputDialog] | 0.76 |  |
| Game > Open Scene > Level1.scene | game/vs | ok |  | 0.68 |  |
| Game > Open Scene > Level2.scene | game/vs | ok |  | 0.89 |  |
| Game Assets (_AssetTree) > Import | game/vs | ok |  | 0.61 |  |
| Git > Abort merge / rebase | python-tk/vs | ok | Git [QMessageBox] | 1.0 |  |
| Git > Amend last commit | python-tk/vs | ok |  | 0.92 |  |
| Git > Blame current file | python-tk/vs | ok | Git [QMessageBox] | 0.98 |  |
| Git > Commit All | python-tk/vs | ok |  | 0.94 |  |
| Git > Compare current file with commit | python-tk/vs | ok | Git [QMessageBox] | 0.87 |  |
| Git > Continue merge / rebase | python-tk/vs | ok | Git [QMessageBox] | 1.12 |  |
| Git > Edit .gitignore | python-tk/vs | ok | Git [QMessageBox] | 1.07 |  |
| Git > Fetch | python-tk/vs | ok | Git [QMessageBox] | 1.43 |  |
| Git > Git Changes | python-tk/vs | ok |  | 1.72 |  |
| Git > Git Settings | python-tk/vs | ok | Git Settings [QDialog] | 1.76 |  |
| Git > Manage Branches | python-tk/vs | ok |  | 1.02 |  |
| Git > Merge into current branch | python-tk/vs | ok | Git [QMessageBox] | 1.32 |  |
| Git > New Branch | python-tk/vs | ok | Git [QMessageBox] | 1.15 |  |
| Git > Pull | python-tk/vs | ok | Git [QMessageBox] | 1.01 |  |
| Git > Pull (rebase) | python-tk/vs | ok | Git [QMessageBox] | 1.2 |  |
| Git > Rebase current branch onto | python-tk/vs | ok | Git [QMessageBox] | 1.51 |  |
| Git > Remotes | python-tk/vs | ok | Git [QMessageBox] | 1.05 |  |
| Git > Resolve Conflicts | python-tk/vs | ok | Git [QMessageBox] | 1.02 |  |
| Git > Stash All | python-tk/vs | ok | Git [QMessageBox] | 1.37 |  |
| Git > Stashes | python-tk/vs | ok |  | 3.15 |  |
| Git > Tags | python-tk/vs | ok |  | 1.82 |  |
| Git > Toggle inline blame in the editor | python-tk/vs | ok | Git [QMessageBox] | 0.92 |  |
| Git > Undo last commit (keep changes) | python-tk/vs | ok | Git [QMessageBox] | 1.31 |  |
| Git > View History (graph) | python-tk/vs | ok |  | 1.69 |  |
| Help > About | python-tk/vs | ok | RAD IDE [QMessageBox] | 1.1 |  |
| Help > Context Help | python-tk/vs | ok | RAD IDE Help [HelpViewer] | 0.68 |  |
| Help > Example Projects | python-tk/vs | ok | أمثلة المشاريع [ExampleGallery] | 1.28 |  |
| Help > Help Files (CHM) > AI in RAD IDE (Arabic guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > BASIC course (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > C++ course (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Car Diagnostics: OBD-II, Warning Lights and Service Functions (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > CodeIgniter 4 in RAD IDE (Guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > DOS Programming: QBasic, Pascal, C, Assembly and Visual Designers (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Deploy and Publish in RAD IDE (Arabic guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.6 |  |
| Help > Help Files (CHM) > ECU and Firmware Files: Analysis and Calibration Editing (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Extensions in RAD IDE (Arabic guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Flutter Mobile Apps in RAD IDE (guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Fortran Basics (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Import and Migrate in RAD IDE (Arabic guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Jupyter Notebooks and Data Science in RAD IDE (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Laravel in RAD IDE (Guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Assembly from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Learn C from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn C# from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Learn Dart from Scratch (to Flutter) (Arabic, CHM) | python-tk/vs | ok |  | 0.64 |  |
| Help > Help Files (CHM) > Learn Go from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Java from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn JavaScript and TypeScript with Node.js (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Learn Lua from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Perl from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn PowerShell from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Python from Scratch to Desktop Apps (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Learn Ring from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Ruby from Scratch, then Ruby on Rails (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Learn Rust from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.6 |  |
| Help > Help Files (CHM) > Making Games in RAD IDE (guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Node.js and Front-end Guide for RAD IDE (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Old NASA Programs: the Apollo Guidance Computer and Classic Fortran (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > RAD IDE Guide: Data and Reports (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > RAD IDE Guide: Debugging and Testing (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > RAD IDE Guide: Git and Collaboration (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > RAD IDE Guide: The Form Designer (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > RAD IDE Guide: Workbench Basics (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > RAD IDE Manual (CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Retro Games: ROM Hacking and Programming the Atari 2600, NES and Game Boy (Arabic, CHM) | python-tk/vs | ok |  | 0.62 |  |
| Help > Help Files (CHM) > Solutions and References in RAD IDE (Arabic guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.63 |  |
| Help > Help Files (CHM) > Visual Studio Projects in RAD IDE (Guide) (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Help Files (CHM) > Web Development with PHP from Scratch (Arabic, CHM) | python-tk/vs | ok |  | 0.61 |  |
| Help > Keyboard Shortcuts | python-tk/vs | ok | RAD IDE Help [HelpViewer] | 0.79 |  |
| Help > PE / MFC Workbench Guide | python-tk/vs | ok |  | 1.13 |  |
| Help > Python Documentation | python-tk/vs | ok |  | 0.61 |  |
| Help > Qt for Python (PySide6) Documentation | python-tk/vs | ok |  | 0.61 |  |
| Help > RAD IDE Help | python-tk/vs | ok | RAD IDE Help [HelpViewer] | 0.77 |  |
| Help > Ring Documentation | python-tk/vs | ok |  | 0.62 |  |
| Help > Ring Samples | python-tk/vs | ok |  | 3.34 |  |
| Help > RingQt / Qt 5 Class Reference | python-tk/vs | ok |  | 0.62 |  |
| Help > Tkinter Documentation | python-tk/vs | ok |  | 0.61 |  |
| Help > Tutorials (Arabic lessons) | python-tk/vs | ok |  | 1.32 |  |
| Help > VB6 Language Reference | python-tk/vs | ok | RAD IDE Help [HelpViewer] | 0.67 |  |
| Menu bar corner > VS | python-tk/vs | ok |  | 0.66 |  |
| Project > Add Existing Item | python-tk/vs | ok | Add Existing Item [QFileDialog] | 2.56 |  |
| Project > Add Existing Item | none/vs | ok |  | 0.6 |  |
| Project > Add Existing Item | python-tk/vscode | ok | Add Existing Item [QFileDialog] | 1.05 |  |
| Project > Add Existing Item | python-tk/agent | ok | Add Existing Item [QFileDialog] | 1.06 |  |
| Project > Add Existing Item | vb6/vs | ok | Add Existing Item [QFileDialog] | 0.98 |  |
| Project > Add Existing Item | csharp/vs | ok | Add Existing Item [QFileDialog] | 0.99 |  |
| Project > Add Existing Item | web/vs | ok | Add Existing Item [QFileDialog] | 0.84 |  |
| Project > Add Existing Item | flask/vs | ok | Add Existing Item [QFileDialog] | 0.98 |  |
| Project > Add Existing Item | flutter/vs | ok | Add Existing Item [QFileDialog] | 0.86 |  |
| Project > Add Existing Item | retro/vs | ok | Add Existing Item [QFileDialog] | 0.92 |  |
| Project > Add Existing Item | dos/vs | ok | Add Existing Item [QFileDialog] | 1.14 |  |
| Project > Add Existing Item | game/vs | ok | Add Existing Item [QFileDialog] | 1.13 |  |
| Project > Add Existing Item | asm/vs | ok | Add Existing Item [QFileDialog] | 1.0 |  |
| Project > Add Existing Item | firmware/vs | ok | Add Existing Item [QFileDialog] | 0.83 |  |
| Project > Add Module | python-tk/vs | ok | Add Module [AddItemDialog] | 0.84 |  |
| Project > Add Module | none/vs | ok |  | 0.6 |  |
| Project > Add Module | python-tk/vscode | ok | Add Module [AddItemDialog] | 0.81 |  |
| Project > Add Module | python-tk/agent | ok | Add Module [AddItemDialog] | 0.85 |  |
| Project > Add Module | vb6/vs | ok | Add Module [AddItemDialog] | 0.76 |  |
| Project > Add Module | csharp/vs | ok | Add Module [AddItemDialog] | 0.78 |  |
| Project > Add Module | web/vs | ok | Add Module [AddItemDialog] | 0.72 |  |
| Project > Add Module | flask/vs | ok | Add Module [AddItemDialog] | 0.74 |  |
| Project > Add Module | flutter/vs | ok | Add Module [AddItemDialog] | 0.75 |  |
| Project > Add Module | retro/vs | ok | Add Module [AddItemDialog] | 0.72 |  |
| Project > Add Module | dos/vs | ok | Add Module [AddItemDialog] | 0.87 |  |
| Project > Add Module | game/vs | ok | Add Module [AddItemDialog] | 0.8 |  |
| Project > Add Module | asm/vs | ok | Add Module [AddItemDialog] | 0.75 |  |
| Project > Add Module | firmware/vs | ok | Add Module [AddItemDialog] | 0.73 |  |
| Project > Add New Screen (Flutter designer) | flutter/vs | ok | Add New Screen [NewScreenDialog] | 0.87 |  |
| Project > Add Reference | python-tk/vs | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.94 |  |
| Project > Add Reference | none/vs | ok |  | 0.61 |  |
| Project > Add Reference | python-tk/vscode | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.82 |  |
| Project > Add Reference | python-tk/agent | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.83 |  |
| Project > Add Reference | vb6/vs | ok | Reference Manager - Greeter [AddReferenceDialog] | 0.8 |  |
| Project > Add Reference | csharp/vs | ok | Reference Manager - HelloCSharp [AddReferenceDialog] | 0.8 |  |
| Project > Add Reference | web/vs | ok | Reference Manager - Boot Site [AddReferenceDialog] | 0.75 |  |
| Project > Add Reference | flask/vs | ok | Reference Manager - Flask_Todo [AddReferenceDialog] | 0.75 |  |
| Project > Add Reference | flutter/vs | ok | Reference Manager - IdeProj [AddReferenceDialog] | 0.77 |  |
| Project > Add Reference | retro/vs | ok | Reference Manager - NesStarCatcher [AddReferenceDialog] | 0.73 |  |
| Project > Add Reference | dos/vs | ok | Reference Manager - Contacts [AddReferenceDialog] | 0.84 |  |
| Project > Add Reference | game/vs | ok | Reference Manager - Platformer [AddReferenceDialog] | 0.83 |  |
| Project > Add Reference | asm/vs | ok | Reference Manager - CoreNasmForms [AddReferenceDialog] | 0.77 |  |
| Project > Add Reference | firmware/vs | ok | Reference Manager - CrawlEcu [AddReferenceDialog] | 0.72 |  |
| Project > Add Report | python-tk/vs | ok | Add Report [AddReportDialog] | 0.89 |  |
| Project > Add Report | none/vs | ok | Add Report [QMessageBox] | 0.76 |  |
| Project > Add Report | python-tk/vscode | ok | Add Report [AddReportDialog] | 0.88 |  |
| Project > Add Report | python-tk/agent | ok | Add Report [AddReportDialog] | 0.87 |  |
| Project > Add Report | vb6/vs | ok | Add Report [AddReportDialog] | 0.82 |  |
| Project > Add Report | csharp/vs | ok | Add Report [AddReportDialog] | 0.79 |  |
| Project > Add Report | web/vs | ok | Add Report [AddReportDialog] | 0.75 |  |
| Project > Add Report | flask/vs | ok | Add Report [AddReportDialog] | 0.76 |  |
| Project > Add Report | flutter/vs | ok | Add Report [AddReportDialog] | 0.79 |  |
| Project > Add Report | retro/vs | ok | Add Report [AddReportDialog] | 0.76 |  |
| Project > Add Report | dos/vs | ok | Add Report [AddReportDialog] | 0.84 |  |
| Project > Add Report | game/vs | ok | Add Report [AddReportDialog] | 0.88 |  |
| Project > Add Report | asm/vs | ok | Add Report [AddReportDialog] | 0.79 |  |
| Project > Add Report | firmware/vs | ok | Add Report [AddReportDialog] | 0.77 |  |
| Project > Add User Control | python-tk/vs | ok | Add User Control [QDialog] | 0.85 |  |
| Project > Add User Control | none/vs | ok |  | 0.6 |  |
| Project > Add User Control | python-tk/vscode | ok | Add User Control [QDialog] | 0.83 |  |
| Project > Add User Control | python-tk/agent | ok | Add User Control [QDialog] | 0.8 |  |
| Project > Add User Control | vb6/vs | ok | Add User Control [QMessageBox] | 0.76 |  |
| Project > Add User Control | csharp/vs | ok | Add User Control [QMessageBox] | 0.76 |  |
| Project > Add User Control | web/vs | ok | Add User Control [QMessageBox] | 0.71 |  |
| Project > Add User Control | flask/vs | ok | Add User Control [QMessageBox] | 0.71 |  |
| Project > Add User Control | flutter/vs | ok | Add User Control [QMessageBox] | 0.73 |  |
| Project > Add User Control | retro/vs | ok | Add User Control [QMessageBox] | 0.7 |  |
| Project > Add User Control | dos/vs | ok | Add User Control [QMessageBox] | 0.8 |  |
| Project > Add User Control | game/vs | ok | Add User Control [QMessageBox] | 0.84 |  |
| Project > Add User Control | asm/vs | ok | Add User Control [QMessageBox] | 0.74 |  |
| Project > Add User Control | firmware/vs | ok | Add User Control [QMessageBox] | 0.73 |  |
| Project > Add Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 0.91 |  |
| Project > Add Windows Form | python-tk/vscode | ok | Add Windows Form [AddItemDialog] | 0.83 |  |
| Project > Add Windows Form | python-tk/agent | ok | Add Windows Form [AddItemDialog] | 0.85 |  |
| Project > Add Windows Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.83 |  |
| Project > Add Windows Form | csharp/vs | ok | Add Windows Form [AddItemDialog] | 0.8 |  |
| Project > Add Windows Form | web/vs | ok | Add Windows Form [AddItemDialog] | 0.73 |  |
| Project > Add Windows Form | flask/vs | ok | Add Windows Form [AddItemDialog] | 0.73 |  |
| Project > Add Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.75 |  |
| Project > Add Windows Form | retro/vs | ok | Add Windows Form [AddItemDialog] | 0.74 |  |
| Project > Add Windows Form | dos/vs | ok | Add Windows Form [AddItemDialog] | 0.87 |  |
| Project > Add Windows Form | game/vs | ok | Add Windows Form [AddItemDialog] | 0.89 |  |
| Project > Add Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.76 |  |
| Project > Add Windows Form | firmware/vs | ok | Add Windows Form [AddItemDialog] | 0.8 |  |
| Project > BASIC Commands > Add Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.79 |  |
| Project > BASIC Commands > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.91 |  |
| Project > BASIC Commands > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.8 |  |
| Project > BASIC Commands > Run (F5) | vb6/vs | ok |  | 0.66 |  |
| Project > Build EXE | python-tk/vs | ok |  | 4.22 |  |
| Project > Build EXE | none/vs | ok |  | 0.61 |  |
| Project > Build EXE | python-tk/vscode | ok |  | 1.32 |  |
| Project > Build EXE | python-tk/agent | ok |  | 1.43 |  |
| Project > Build EXE | vb6/vs | ok | Build EXE [QMessageBox] | 0.79 |  |
| Project > Build EXE | csharp/vs | ok | Build EXE [QMessageBox] | 0.78 |  |
| Project > Build EXE | web/vs | ok | Locate HTML / CSS / JavaScript Site interpreter [QFileDialog] \| Build EXE [QMessageBox] | 0.93 |  |
| Project > Build EXE | flask/vs | ok |  | 1.04 |  |
| Project > Build EXE | flutter/vs | ok | Build EXE [QMessageBox] | 0.89 |  |
| Project > Build EXE | retro/vs | ok | Build EXE [QMessageBox] | 0.71 |  |
| Project > Build EXE | dos/vs | ok | Build EXE [QMessageBox] | 0.81 |  |
| Project > Build EXE | game/vs | ok | Build EXE [QMessageBox] | 0.8 |  |
| Project > Build EXE | asm/vs | ok | Build EXE [QMessageBox] | 0.91 |  |
| Project > Build EXE | firmware/vs | ok | Build EXE [QMessageBox] | 0.74 |  |
| Project > Check for Errors | python-tk/vs | ok |  | 0.63 |  |
| Project > Check for Errors | none/vs | ok |  | 0.61 |  |
| Project > Check for Errors | python-tk/vscode | ok |  | 0.85 |  |
| Project > Check for Errors | python-tk/agent | ok |  | 0.97 |  |
| Project > Check for Errors | vb6/vs | ok |  | 0.64 |  |
| Project > Check for Errors | csharp/vs | ok |  | 0.63 |  |
| Project > Check for Errors | web/vs | ok |  | 0.63 |  |
| Project > Check for Errors | flask/vs | ok |  | 0.62 |  |
| Project > Check for Errors | flutter/vs | ok |  | 0.64 |  |
| Project > Check for Errors | retro/vs | ok |  | 0.67 |  |
| Project > Check for Errors | dos/vs | ok |  | 0.66 |  |
| Project > Check for Errors | game/vs | ok |  | 0.64 |  |
| Project > Check for Errors | asm/vs | ok |  | 0.94 |  |
| Project > Check for Errors | firmware/vs | ok |  | 0.63 |  |
| Project > DOS Project Settings | python-tk/vs | ok | DOS Project Settings [QMessageBox] | 0.82 |  |
| Project > DOS Project Settings | none/vs | ok | DOS Project Settings [QMessageBox] | 0.79 |  |
| Project > DOS Project Settings | python-tk/vscode | ok | DOS Project Settings [QMessageBox] | 0.77 |  |
| Project > DOS Project Settings | python-tk/agent | ok | DOS Project Settings [QMessageBox] | 0.76 |  |
| Project > DOS Project Settings | vb6/vs | ok | DOS Project Settings [QMessageBox] | 0.84 |  |
| Project > DOS Project Settings | csharp/vs | ok | DOS Project Settings [QMessageBox] | 0.76 |  |
| Project > DOS Project Settings | web/vs | ok | DOS Project Settings [QMessageBox] | 0.74 |  |
| Project > DOS Project Settings | flask/vs | ok | DOS Project Settings [QMessageBox] | 0.76 |  |
| Project > DOS Project Settings | flutter/vs | ok | DOS Project Settings [QMessageBox] | 0.74 |  |
| Project > DOS Project Settings | retro/vs | ok | DOS Project Settings [QMessageBox] | 0.72 |  |
| Project > DOS Project Settings | dos/vs | ok | DOS Project Settings [DosSettingsDialog] | 0.98 |  |
| Project > DOS Project Settings | game/vs | ok | DOS Project Settings [QMessageBox] | 0.79 |  |
| Project > DOS Project Settings | asm/vs | ok | DOS Project Settings [QMessageBox] | 0.75 |  |
| Project > DOS Project Settings | firmware/vs | ok | DOS Project Settings [QMessageBox] | 0.7 |  |
| Project > DOS Settings | python-tk/vs | ok | DOS Settings [QMessageBox] | 0.85 |  |
| Project > DOS Settings | none/vs | ok | DOS Settings [QMessageBox] | 0.79 |  |
| Project > DOS Settings | python-tk/vscode | ok | DOS Settings [QMessageBox] | 0.78 |  |
| Project > DOS Settings | python-tk/agent | ok | DOS Settings [QMessageBox] | 0.8 |  |
| Project > DOS Settings | vb6/vs | ok | DOS Settings [QMessageBox] | 0.78 |  |
| Project > DOS Settings | csharp/vs | ok | DOS Settings [QMessageBox] | 0.78 |  |
| Project > DOS Settings | web/vs | ok | DOS Settings [QMessageBox] | 0.73 |  |
| Project > DOS Settings | flask/vs | ok | DOS Settings [QMessageBox] | 0.82 |  |
| Project > DOS Settings | flutter/vs | ok | DOS Settings [QMessageBox] | 1.16 |  |
| Project > DOS Settings | retro/vs | ok | DOS Settings [QMessageBox] | 0.74 |  |
| Project > DOS Settings | dos/vs | ok | DOS Settings [QMessageBox] | 0.8 |  |
| Project > DOS Settings | game/vs | ok | DOS Settings [QMessageBox] | 0.8 |  |
| Project > DOS Settings | asm/vs | ok | DOS Settings [QMessageBox] | 0.74 |  |
| Project > DOS Settings | firmware/vs | ok | DOS Settings [QMessageBox] | 0.79 |  |
| Project > ECU Project > Analyze (workbench) | firmware/vs | ok |  | 0.74 |  |
| Project > ECU Project > Build ECU Project | firmware/vs | ok |  | 0.63 |  |
| Project > ECU Project > Build Settings | firmware/vs | ok | ECU Build Settings [BuildSettingsDialog] | 0.77 |  |
| Project > ECU Project > Build in Workbench | firmware/vs | ok |  | 0.63 |  |
| Project > ECU Project > Checksum Toolkit (any file) | python-tk/vs | ok | Checksum Toolkit [QFileDialog] | 1.14 |  |
| Project > ECU Project > Checksum Toolkit (any file) | none/vs | ok | Checksum Toolkit [QFileDialog] | 1.06 |  |
| Project > ECU Project > Checksum Toolkit (any file) | python-tk/vscode | ok | Checksum Toolkit [QFileDialog] | 0.95 |  |
| Project > ECU Project > Checksum Toolkit (any file) | python-tk/agent | ok | Checksum Toolkit [QFileDialog] | 0.94 |  |
| Project > ECU Project > Checksum Toolkit (any file) | vb6/vs | ok | Checksum Toolkit [QFileDialog] | 0.9 |  |
| Project > ECU Project > Checksum Toolkit (any file) | csharp/vs | ok | Checksum Toolkit [QFileDialog] | 0.93 |  |
| Project > ECU Project > Checksum Toolkit (any file) | web/vs | ok | Checksum Toolkit [QFileDialog] | 0.83 |  |
| Project > ECU Project > Checksum Toolkit (any file) | flask/vs | ok | Checksum Toolkit [QFileDialog] | 0.87 |  |
| Project > ECU Project > Checksum Toolkit (any file) | flutter/vs | ok | Checksum Toolkit [QFileDialog] | 0.83 |  |
| Project > ECU Project > Checksum Toolkit (any file) | retro/vs | ok | Checksum Toolkit [QFileDialog] | 0.84 |  |
| Project > ECU Project > Checksum Toolkit (any file) | dos/vs | ok | Checksum Toolkit [QFileDialog] | 1.01 |  |
| Project > ECU Project > Checksum Toolkit (any file) | game/vs | ok | Checksum Toolkit [QFileDialog] | 0.95 |  |
| Project > ECU Project > Checksum Toolkit (any file) | asm/vs | ok | Checksum Toolkit [QFileDialog] | 0.9 |  |
| Project > ECU Project > Checksum Toolkit (any file) | firmware/vs | ok | Checksum Toolkit - demo_ecu_mod.bin [ChecksumDialog] | 0.85 |  |
| Project > ECU Project > Checksums | firmware/vs | ok | Checksums - CrawlEcu [ChecksumDialog] | 0.86 |  |
| Project > ECU Project > Compare with Original | firmware/vs | ok |  | 0.68 |  |
| Project > ECU Project > Compare with Original (workbench) | firmware/vs | ok |  | 0.61 |  |
| Project > ECU Project > Edit Working Copy | firmware/vs | ok |  | 0.74 |  |
| Project > ECU Project > Export Modification Report | firmware/vs | ok | Export Modification Report [QFileDialog] | 0.88 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | firmware/vs | ok | Export Patch [QFileDialog] | 0.85 |  |
| Project > ECU Project > Find Maps (workbench) | firmware/vs | ok |  | 3.29 |  |
| Project > ECU Project > Import Patch | firmware/vs | ok | Import Patch [QFileDialog] | 0.83 |  |
| Project > ECU Project > Open Build Output | firmware/vs | ok |  | 0.78 |  |
| Project > ECU Project > Open Workbench | firmware/vs | ok |  | 0.97 |  |
| Project > ECU Project > Set Original | firmware/vs | ok | Choose the Original Firmware File [QFileDialog] | 0.83 |  |
| Project > ECU Project > Verify Checksums | firmware/vs | ok |  | 0.61 |  |
| Project > ECU Project > Verify Checksums (workbench) | firmware/vs | ok |  | 0.61 |  |
| Project > ECU Project > Versions | firmware/vs | ok | Versions - CrawlEcu [VersionsDialog] | 0.81 |  |
| Project > ECU Project > View Original (read-only) | firmware/vs | ok |  | 0.76 |  |
| Project > Flask Commands > Flask Shell | flask/vs | ok |  | 0.62 |  |
| Project > Flask Commands > New Blueprint | flask/vs | ok |  | 0.81 |  |
| Project > Flask Commands > Routes | flask/vs | ok |  | 0.62 |  |
| Project > Flask Commands > Run Server | flask/vs | ok |  | 0.76 |  |
| Project > Flask Commands > Run flask Command | flask/vs | ok |  | 0.6 |  |
| Project > Flutter App Theme | flutter/vs | ok | App Theme [ThemeEditorDialog] | 0.85 |  |
| Project > Flutter Assets | flutter/vs | ok | Project Assets [AssetManagerDialog] | 0.75 |  |
| Project > Flutter Commands > Analyze (flutter analyze) | flutter/vs | ok |  | 0.65 |  |
| Project > Flutter Commands > Build > Build APK (Android) | flutter/vs | ok |  | 0.66 |  |
| Project > Flutter Commands > Build > Build Web | flutter/vs | ok |  | 0.66 |  |
| Project > Flutter Commands > Build > Build Windows | flutter/vs | ok |  | 0.64 |  |
| Project > Flutter Commands > Clean (flutter clean) | flutter/vs | ok |  | 0.65 |  |
| Project > Flutter Commands > Flutter Doctor | flutter/vs | ok |  | 0.63 |  |
| Project > Flutter Commands > Format Code (dart format) | flutter/vs | ok |  | 0.64 |  |
| Project > Flutter Commands > List Devices | flutter/vs | ok |  | 0.65 |  |
| Project > Flutter Commands > New Screen (Form) | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.91 |  |
| Project > Flutter Commands > New Widget | flutter/vs | ok |  | 0.92 |  |
| Project > Flutter Commands > Packages > Add Package (pub add) | flutter/vs | ok |  | 0.64 |  |
| Project > Flutter Commands > Packages > pub get | flutter/vs | ok |  | 0.67 |  |
| Project > Flutter Commands > Packages > pub outdated | flutter/vs | ok |  | 0.68 |  |
| Project > Flutter Commands > Packages > pub upgrade | flutter/vs | ok |  | 0.66 |  |
| Project > Flutter Commands > Run (flutter run) | flutter/vs | ok |  | 0.99 |  |
| Project > Flutter Commands > Run Tests (flutter test) | flutter/vs | ok |  | 0.65 |  |
| Project > Flutter Commands > Stop Running Command | flutter/vs | ok |  | 1.26 |  |
| Project > Flutter Fonts (Google Fonts) | flutter/vs | ok | Google Fonts [FontPickerDialog] | 0.83 |  |
| Project > Generate Form with AI | python-tk/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.69 |  |
| Project > Generate Form with AI | none/vs | ok | AI [QMessageBox] | 0.78 |  |
| Project > Generate Form with AI | python-tk/vscode | ok | Generate Form with AI [GenerateFormDialog] | 0.68 |  |
| Project > Generate Form with AI | python-tk/agent | ok | Generate Form with AI [GenerateFormDialog] | 0.66 |  |
| Project > Generate Form with AI | vb6/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.67 |  |
| Project > Generate Form with AI | csharp/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.67 |  |
| Project > Generate Form with AI | web/vs | ok | AI [QMessageBox] | 0.72 |  |
| Project > Generate Form with AI | flask/vs | ok | AI [QMessageBox] | 0.74 |  |
| Project > Generate Form with AI | flutter/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.66 |  |
| Project > Generate Form with AI | retro/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.66 |  |
| Project > Generate Form with AI | dos/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.74 |  |
| Project > Generate Form with AI | game/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.7 |  |
| Project > Generate Form with AI | asm/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.66 |  |
| Project > Generate Form with AI | firmware/vs | ok | Generate Form with AI [GenerateFormDialog] | 0.65 |  |
| Project > Import Flutter Screen from Dart | flutter/vs | ok | Import a Flutter screen [QFileDialog] | 0.95 |  |
| Project > Manage Packages | python-tk/vs | ok | Manage Packages - EvDemo [PackagesDialog] | 0.88 |  |
| Project > Manage Packages | none/vs | ok | Manage Packages [QMessageBox] | 0.77 |  |
| Project > Manage Packages | python-tk/vscode | ok | Manage Packages - EvDemo [PackagesDialog] | 0.79 |  |
| Project > Manage Packages | python-tk/agent | ok | Manage Packages - EvDemo [PackagesDialog] | 0.81 |  |
| Project > Manage Packages | vb6/vs | ok | Manage Packages [QMessageBox] | 0.77 |  |
| Project > Manage Packages | csharp/vs | ok |  | 0.96 |  |
| Project > Manage Packages | web/vs | ok | Manage Packages [QMessageBox] | 0.72 |  |
| Project > Manage Packages | flask/vs | ok | Manage Packages - Flask_Todo [PackagesDialog] | 0.75 |  |
| Project > Manage Packages | flutter/vs | ok | Manage Packages - IdeProj [PackagesDialog] | 2.09 |  |
| Project > Manage Packages | retro/vs | ok | Manage Packages [QMessageBox] | 0.79 |  |
| Project > Manage Packages | dos/vs | ok | Manage Packages [QMessageBox] | 0.81 |  |
| Project > Manage Packages | game/vs | ok | Manage Packages - Platformer [PackagesDialog] | 0.8 |  |
| Project > Manage Packages | asm/vs | ok | Manage Packages [QMessageBox] | 0.73 |  |
| Project > Manage Packages | firmware/vs | ok | Manage Packages [QMessageBox] | 0.81 |  |
| Project > Open Project Folder | python-tk/vs | ok |  | 0.6 |  |
| Project > Open Project Folder | none/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | python-tk/vscode | ok |  | 0.61 |  |
| Project > Open Project Folder | python-tk/agent | ok |  | 0.61 |  |
| Project > Open Project Folder | vb6/vs | ok |  | 0.6 |  |
| Project > Open Project Folder | csharp/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | web/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | flask/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | flutter/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | retro/vs | ok |  | 0.6 |  |
| Project > Open Project Folder | dos/vs | ok |  | 0.6 |  |
| Project > Open Project Folder | game/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | asm/vs | ok |  | 0.61 |  |
| Project > Open Project Folder | firmware/vs | ok |  | 0.6 |  |
| Project > Project Properties | python-tk/vs | ok | EvDemo Properties [QDialog] | 5.93 |  |
| Project > Project Properties | none/vs | ok |  | 0.61 |  |
| Project > Project Properties | python-tk/vscode | ok | EvDemo Properties [QDialog] | 0.84 |  |
| Project > Project Properties | python-tk/agent | ok | EvDemo Properties [QDialog] | 0.82 |  |
| Project > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.79 |  |
| Project > Project Properties | csharp/vs | ok | HelloCSharp Properties [QDialog] | 0.77 |  |
| Project > Project Properties | web/vs | ok | Site Settings - Boot Site [QDialog] | 0.74 |  |
| Project > Project Properties | flask/vs | ok | Site Settings - Flask_Todo [QDialog] | 0.72 |  |
| Project > Project Properties | flutter/vs | ok | IdeProj Properties [QDialog] | 0.77 |  |
| Project > Project Properties | retro/vs | ok | NesStarCatcher Properties [QDialog] | 0.72 |  |
| Project > Project Properties | dos/vs | ok | Contacts Properties [QDialog] | 0.81 |  |
| Project > Project Properties | game/vs | ok | Platformer Properties [QDialog] | 0.88 |  |
| Project > Project Properties | asm/vs | ok | CoreNasmForms Properties [QDialog] | 0.74 |  |
| Project > Project Properties | firmware/vs | ok | CrawlEcu Properties [QDialog] | 0.74 |  |
| Project > Python Commands > Build EXE / Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] \| File Modification Detected [QMessageBox] | 1.03 |  |
| Project > Python Commands > Build EXE / Installer | python-tk/vscode | ok | Publish EvDemo [PublishDialog] | 0.94 |  |
| Project > Python Commands > Build EXE / Installer | python-tk/agent | ok | Publish EvDemo [PublishDialog] | 1.06 |  |
| Project > Python Commands > Build EXE / Installer | flask/vs | ok | Publish Flask_Todo [PublishDialog] | 0.86 |  |
| Project > Python Commands > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.87 |  |
| Project > Python Commands > Create .venv | python-tk/vs | ok |  | 0.63 |  |
| Project > Python Commands > Create .venv | python-tk/vscode | ok |  | 0.66 |  |
| Project > Python Commands > Create .venv | python-tk/agent | ok |  | 0.62 |  |
| Project > Python Commands > Create .venv | flask/vs | ok |  | 0.61 |  |
| Project > Python Commands > Create .venv | game/vs | ok |  | 0.62 |  |
| Project > Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vs | ok |  | 0.73 |  |
| Project > Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vscode | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/agent | ok |  | 0.71 |  |
| Project > Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) | flask/vs | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Fix Lint Problems (ruff check --fix) | game/vs | ok |  | 0.64 |  |
| Project > Python Commands > Format and Lint > Format Project (black) | python-tk/vs | ok | File Modification Detected [QMessageBox] | 0.85 |  |
| Project > Python Commands > Format and Lint > Format Project (black) | python-tk/vscode | ok |  | 0.64 |  |
| Project > Python Commands > Format and Lint > Format Project (black) | python-tk/agent | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Format Project (black) | flask/vs | ok |  | 0.68 |  |
| Project > Python Commands > Format and Lint > Format Project (black) | game/vs | ok |  | 0.69 |  |
| Project > Python Commands > Format and Lint > Format Project (ruff) | python-tk/vs | ok |  | 0.71 |  |
| Project > Python Commands > Format and Lint > Format Project (ruff) | python-tk/vscode | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Format Project (ruff) | python-tk/agent | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Format Project (ruff) | flask/vs | ok |  | 0.79 |  |
| Project > Python Commands > Format and Lint > Format Project (ruff) | game/vs | ok |  | 0.62 |  |
| Project > Python Commands > Format and Lint > Lint Project (ruff check) | python-tk/vs | ok |  | 0.65 |  |
| Project > Python Commands > Format and Lint > Lint Project (ruff check) | python-tk/vscode | ok |  | 0.65 |  |
| Project > Python Commands > Format and Lint > Lint Project (ruff check) | python-tk/agent | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Lint Project (ruff check) | flask/vs | ok |  | 0.63 |  |
| Project > Python Commands > Format and Lint > Lint Project (ruff check) | game/vs | ok |  | 0.62 |  |
| Project > Python Commands > Freeze to requirements.txt | python-tk/vs | ok |  | 0.66 |  |
| Project > Python Commands > Freeze to requirements.txt | python-tk/vscode | ok |  | 0.63 |  |
| Project > Python Commands > Freeze to requirements.txt | python-tk/agent | ok |  | 0.63 |  |
| Project > Python Commands > Freeze to requirements.txt | flask/vs | ok |  | 0.62 |  |
| Project > Python Commands > Freeze to requirements.txt | game/vs | ok |  | 0.63 |  |
| Project > Python Commands > List Installed Packages | python-tk/vs | ok |  | 0.7 |  |
| Project > Python Commands > List Installed Packages | python-tk/vscode | ok |  | 0.63 |  |
| Project > Python Commands > List Installed Packages | python-tk/agent | ok |  | 0.62 |  |
| Project > Python Commands > List Installed Packages | flask/vs | ok |  | 0.61 |  |
| Project > Python Commands > List Installed Packages | game/vs | ok |  | 0.63 |  |
| Project > Python Commands > Run Tests (pytest) | python-tk/vs | ok |  | 0.64 |  |
| Project > Python Commands > Run Tests (pytest) | python-tk/vscode | ok |  | 0.64 |  |
| Project > Python Commands > Run Tests (pytest) | python-tk/agent | ok |  | 0.62 |  |
| Project > Python Commands > Run Tests (pytest) | flask/vs | ok |  | 0.62 |  |
| Project > Python Commands > Run Tests (pytest) | game/vs | ok |  | 0.62 |  |
| Project > Python Commands > Run Tests (unittest) | python-tk/vs | ok |  | 0.68 |  |
| Project > Python Commands > Run Tests (unittest) | python-tk/vscode | ok |  | 0.63 |  |
| Project > Python Commands > Run Tests (unittest) | python-tk/agent | ok |  | 0.62 |  |
| Project > Python Commands > Run Tests (unittest) | game/vs | ok |  | 0.62 |  |
| Project > Resources | python-tk/vs | ok |  | 0.84 |  |
| Project > Resources | none/vs | ok | Resources [QMessageBox] | 0.82 |  |
| Project > Resources | python-tk/vscode | ok |  | 0.75 |  |
| Project > Resources | python-tk/agent | ok |  | 0.76 |  |
| Project > Resources | vb6/vs | ok |  | 0.74 |  |
| Project > Resources | csharp/vs | ok |  | 0.73 |  |
| Project > Resources | web/vs | ok |  | 0.72 |  |
| Project > Resources | flask/vs | ok |  | 0.73 |  |
| Project > Resources | flutter/vs | ok |  | 0.98 |  |
| Project > Resources | retro/vs | ok |  | 0.71 |  |
| Project > Resources | dos/vs | ok |  | 0.95 |  |
| Project > Resources | game/vs | ok |  | 0.73 |  |
| Project > Resources | asm/vs | ok |  | 0.73 |  |
| Project > Resources | firmware/vs | ok |  | 0.73 |  |
| Project > Set as StartUp Project | python-tk/vs | ok |  | 0.62 |  |
| Project > Set as StartUp Project | none/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | python-tk/vscode | ok |  | 0.62 |  |
| Project > Set as StartUp Project | python-tk/agent | ok |  | 0.61 |  |
| Project > Set as StartUp Project | vb6/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | csharp/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | web/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | flask/vs | ok |  | 0.62 |  |
| Project > Set as StartUp Project | flutter/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | retro/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | dos/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | game/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | asm/vs | ok |  | 0.61 |  |
| Project > Set as StartUp Project | firmware/vs | ok |  | 0.61 |  |
| Project > User Control Properties and Events | python-tk/vs | ok | User Control [QMessageBox] | 1.0 |  |
| Project > User Control Properties and Events | none/vs | ok | User Control [QMessageBox] | 0.83 |  |
| Project > User Control Properties and Events | python-tk/vscode | ok | User Control [QMessageBox] | 0.84 |  |
| Project > User Control Properties and Events | python-tk/agent | ok | User Control [QMessageBox] | 0.8 |  |
| Project > User Control Properties and Events | vb6/vs | ok | User Control [QMessageBox] | 0.75 |  |
| Project > User Control Properties and Events | csharp/vs | ok | User Control [QMessageBox] | 0.75 |  |
| Project > User Control Properties and Events | web/vs | ok | User Control [QMessageBox] | 0.71 |  |
| Project > User Control Properties and Events | flask/vs | ok | User Control [QMessageBox] | 0.69 |  |
| Project > User Control Properties and Events | flutter/vs | ok | User Control [QMessageBox] | 0.74 |  |
| Project > User Control Properties and Events | retro/vs | ok | User Control [QMessageBox] | 0.7 |  |
| Project > User Control Properties and Events | dos/vs | ok | User Control [QMessageBox] | 0.84 |  |
| Project > User Control Properties and Events | game/vs | ok | User Control [QMessageBox] | 0.83 |  |
| Project > User Control Properties and Events | asm/vs | ok | User Control [QMessageBox] | 0.75 |  |
| Project > User Control Properties and Events | firmware/vs | ok | User Control [QMessageBox] | 0.73 |  |
| Project > pygame Commands > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.89 |  |
| Project > pygame Commands > Build One-File EXE (PyInstaller) | game/vs | ok |  | 0.63 |  |
| Project > pygame Commands > Run Game | game/vs | ok |  | 1.03 |  |
| Python > Build EXE / Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] | 0.99 |  |
| Python > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vs | ok |  | 0.63 |  |
| Python > Format and Lint > Format Project (black) | python-tk/vs | ok |  | 0.65 |  |
| Python > Format and Lint > Format Project (ruff) | python-tk/vs | ok |  | 0.63 |  |
| Python > Format and Lint > Lint Project (ruff check) | python-tk/vs | ok |  | 0.62 |  |
| Python > Freeze to requirements.txt | python-tk/vs | ok |  | 0.63 |  |
| Python > List Installed Packages | python-tk/vs | ok |  | 0.63 |  |
| Python > Run Tests (pytest) | python-tk/vs | ok |  | 0.65 |  |
| Python > Run Tests (unittest) | python-tk/vs | ok |  | 0.63 |  |
| Share > Join Collaboration Session | python-tk/vs | ok | Join Collaboration Session [JoinDialog] | 1.24 |  |
| Site > App Gallery | python-tk/vs | ok | App Gallery [AppGalleryDialog] | 1.17 |  |
| Site > App Gallery | none/vs | ok | App Gallery [AppGalleryDialog] | 1.02 |  |
| Site > App Gallery | python-tk/vscode | ok | App Gallery [AppGalleryDialog] | 1.05 |  |
| Site > App Gallery | python-tk/agent | ok | App Gallery [AppGalleryDialog] | 1.19 |  |
| Site > App Gallery | vb6/vs | ok | App Gallery [AppGalleryDialog] | 0.97 |  |
| Site > App Gallery | csharp/vs | ok | App Gallery [AppGalleryDialog] | 0.94 |  |
| Site > App Gallery | web/vs | ok | App Gallery [AppGalleryDialog] | 0.91 |  |
| Site > App Gallery | flask/vs | ok | App Gallery [AppGalleryDialog] | 0.89 |  |
| Site > App Gallery | flutter/vs | ok | App Gallery [AppGalleryDialog] | 0.94 |  |
| Site > App Gallery | retro/vs | ok | App Gallery [AppGalleryDialog] | 0.89 |  |
| Site > App Gallery | dos/vs | ok | App Gallery [AppGalleryDialog] | 1.05 |  |
| Site > App Gallery | game/vs | ok | App Gallery [AppGalleryDialog] | 0.92 |  |
| Site > App Gallery | asm/vs | ok | App Gallery [AppGalleryDialog] | 0.85 |  |
| Site > App Gallery | firmware/vs | ok | App Gallery [AppGalleryDialog] | 0.97 |  |
| Site > Build Production (npm run build) | flask/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | python-tk/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | none/vs | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | python-tk/vscode | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | python-tk/agent | ok |  | 0.64 |  |
| Site > CodeIgniter Panel (Spark, Routes) | vb6/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | csharp/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | web/vs | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | flask/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | flutter/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | retro/vs | ok |  | 0.61 |  |
| Site > CodeIgniter Panel (Spark, Routes) | dos/vs | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | game/vs | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | asm/vs | ok |  | 0.62 |  |
| Site > CodeIgniter Panel (Spark, Routes) | firmware/vs | ok |  | 0.62 |  |
| Site > Databases | python-tk/vs | ok |  | 0.61 |  |
| Site > Databases | none/vs | ok |  | 0.61 |  |
| Site > Databases | python-tk/vscode | ok |  | 2.21 |  |
| Site > Databases | python-tk/agent | ok |  | 1.23 |  |
| Site > Databases | vb6/vs | ok |  | 0.6 |  |
| Site > Databases | csharp/vs | ok |  | 0.61 |  |
| Site > Databases | web/vs | ok |  | 0.6 |  |
| Site > Databases | flask/vs | ok |  | 0.61 |  |
| Site > Databases | flutter/vs | ok |  | 0.61 |  |
| Site > Databases | retro/vs | ok |  | 0.61 |  |
| Site > Databases | dos/vs | ok |  | 0.61 |  |
| Site > Databases | game/vs | ok |  | 0.61 |  |
| Site > Databases | asm/vs | ok |  | 0.61 |  |
| Site > Databases | firmware/vs | ok |  | 0.61 |  |
| Site > Django / Flask / FastAPI Panel | python-tk/vs | ok |  | 0.63 |  |
| Site > Django / Flask / FastAPI Panel | none/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | python-tk/vscode | ok |  | 0.61 |  |
| Site > Django / Flask / FastAPI Panel | python-tk/agent | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | vb6/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | csharp/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | web/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | flutter/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | retro/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | dos/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | game/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | asm/vs | ok |  | 0.62 |  |
| Site > Django / Flask / FastAPI Panel | firmware/vs | ok |  | 0.61 |  |
| Site > Docker > Build Image | python-tk/vs | ok | Docker [QMessageBox] | 0.92 |  |
| Site > Docker > Build Image | none/vs | ok |  | 0.61 |  |
| Site > Docker > Build Image | python-tk/vscode | ok | Docker [QMessageBox] | 0.84 |  |
| Site > Docker > Build Image | python-tk/agent | ok | Docker [QMessageBox] | 0.93 |  |
| Site > Docker > Build Image | vb6/vs | ok | Docker [QMessageBox] | 0.85 |  |
| Site > Docker > Build Image | csharp/vs | ok | Docker [QMessageBox] | 0.88 |  |
| Site > Docker > Build Image | web/vs | ok | Docker [QMessageBox] | 0.84 |  |
| Site > Docker > Build Image | flask/vs | ok | Docker [QMessageBox] | 0.92 |  |
| Site > Docker > Build Image | flutter/vs | ok | Docker [QMessageBox] | 0.84 |  |
| Site > Docker > Build Image | retro/vs | ok | Docker [QMessageBox] | 0.84 |  |
| Site > Docker > Build Image | dos/vs | ok | Docker [QMessageBox] | 1.06 |  |
| Site > Docker > Build Image | game/vs | ok | Docker [QMessageBox] | 0.9 |  |
| Site > Docker > Build Image | asm/vs | ok | Docker [QMessageBox] | 0.83 |  |
| Site > Docker > Build Image | firmware/vs | ok | Docker [QMessageBox] | 0.92 |  |
| Site > Docker > Compose Down | python-tk/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | none/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | python-tk/vscode | ok |  | 0.61 |  |
| Site > Docker > Compose Down | python-tk/agent | ok |  | 0.62 |  |
| Site > Docker > Compose Down | vb6/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | csharp/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | web/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | flask/vs | ok |  | 0.6 |  |
| Site > Docker > Compose Down | flutter/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | retro/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Down | dos/vs | ok |  | 0.62 |  |
| Site > Docker > Compose Down | game/vs | ok |  | 0.6 |  |
| Site > Docker > Compose Down | asm/vs | ok |  | 0.6 |  |
| Site > Docker > Compose Down | firmware/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Up | python-tk/vs | ok | Docker [QMessageBox] | 0.87 |  |
| Site > Docker > Compose Up | none/vs | ok |  | 0.61 |  |
| Site > Docker > Compose Up | python-tk/vscode | ok | Docker [QMessageBox] | 0.99 |  |
| Site > Docker > Compose Up | python-tk/agent | ok | Docker [QMessageBox] | 1.03 |  |
| Site > Docker > Compose Up | vb6/vs | ok | Docker [QMessageBox] | 0.9 |  |
| Site > Docker > Compose Up | csharp/vs | ok | Docker [QMessageBox] | 0.89 |  |
| Site > Docker > Compose Up | web/vs | ok | Docker [QMessageBox] | 0.81 |  |
| Site > Docker > Compose Up | flask/vs | ok | Docker [QMessageBox] | 0.83 |  |
| Site > Docker > Compose Up | flutter/vs | ok | Docker [QMessageBox] | 0.77 |  |
| Site > Docker > Compose Up | retro/vs | ok | Docker [QMessageBox] | 0.95 |  |
| Site > Docker > Compose Up | dos/vs | ok | Docker [QMessageBox] | 0.92 |  |
| Site > Docker > Compose Up | game/vs | ok | Docker [QMessageBox] | 0.85 |  |
| Site > Docker > Compose Up | asm/vs | ok | Docker [QMessageBox] | 0.8 |  |
| Site > Docker > Compose Up | firmware/vs | ok | Docker [QMessageBox] | 0.86 |  |
| Site > Docker > Docker Panel | python-tk/vs | ok |  | 0.63 |  |
| Site > Docker > Docker Panel | none/vs | ok |  | 0.63 |  |
| Site > Docker > Docker Panel | python-tk/vscode | ok |  | 0.81 |  |
| Site > Docker > Docker Panel | python-tk/agent | ok |  | 0.91 |  |
| Site > Docker > Docker Panel | vb6/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | csharp/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | web/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | flask/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | flutter/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | retro/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | dos/vs | ok |  | 0.63 |  |
| Site > Docker > Docker Panel | game/vs | ok |  | 0.62 |  |
| Site > Docker > Docker Panel | asm/vs | ok |  | 0.63 |  |
| Site > Docker > Docker Panel | firmware/vs | ok |  | 0.62 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | python-tk/vs | ok | Generate Docker Files [DockerGenerateDialog] | 1.32 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | none/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.97 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | python-tk/vscode | ok | Generate Docker Files [DockerGenerateDialog] | 1.01 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | python-tk/agent | ok | Generate Docker Files [DockerGenerateDialog] | 1.16 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | vb6/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.93 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | csharp/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.96 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | web/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.89 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | flask/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.93 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | flutter/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.92 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | retro/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.86 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | dos/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.98 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | game/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.97 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | asm/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.88 |  |
| Site > Docker > Generate Dockerfile / Compose / Dev Container | firmware/vs | ok | Generate Docker Files [DockerGenerateDialog] | 0.98 |  |
| Site > Docker > Lint Dockerfile | python-tk/vs | ok | Lint [QMessageBox] | 0.92 |  |
| Site > Docker > Lint Dockerfile | none/vs | ok | Lint [QMessageBox] | 0.88 |  |
| Site > Docker > Lint Dockerfile | python-tk/vscode | ok | Lint [QMessageBox] | 0.88 |  |
| Site > Docker > Lint Dockerfile | python-tk/agent | ok | Lint [QMessageBox] | 1.07 |  |
| Site > Docker > Lint Dockerfile | vb6/vs | ok | Lint [QMessageBox] | 0.83 |  |
| Site > Docker > Lint Dockerfile | csharp/vs | ok | Lint [QMessageBox] | 1.02 |  |
| Site > Docker > Lint Dockerfile | web/vs | ok | Lint [QMessageBox] | 0.81 |  |
| Site > Docker > Lint Dockerfile | flask/vs | ok | Lint [QMessageBox] | 0.8 |  |
| Site > Docker > Lint Dockerfile | flutter/vs | ok | Lint [QMessageBox] | 0.78 |  |
| Site > Docker > Lint Dockerfile | retro/vs | ok | Lint [QMessageBox] | 0.86 |  |
| Site > Docker > Lint Dockerfile | dos/vs | ok | Lint [QMessageBox] | 0.87 |  |
| Site > Docker > Lint Dockerfile | game/vs | ok | Lint [QMessageBox] | 0.84 |  |
| Site > Docker > Lint Dockerfile | asm/vs | ok | Lint [QMessageBox] | 0.81 |  |
| Site > Docker > Lint Dockerfile | firmware/vs | ok | Lint [QMessageBox] | 0.94 |  |
| Site > Flask | flask/vs | ok |  | 0.61 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | python-tk/vs | ok |  | 0.61 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | none/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | python-tk/vscode | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | python-tk/agent | ok |  | 0.64 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | vb6/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | csharp/vs | ok |  | 0.63 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | web/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | flask/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | flutter/vs | ok |  | 0.61 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | retro/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | dos/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | game/vs | ok |  | 0.63 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | asm/vs | ok |  | 0.62 |  |
| Site > Laravel Panel (Artisan, Routes, Tinker) | firmware/vs | ok |  | 0.62 |  |
| Site > Lighthouse Report | python-tk/vs | ok | Site address [QInputDialog] | 0.87 |  |
| Site > Lighthouse Report | none/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Lighthouse Report | python-tk/vscode | ok | Site address [QInputDialog] | 0.8 |  |
| Site > Lighthouse Report | python-tk/agent | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Lighthouse Report | vb6/vs | ok | Site address [QInputDialog] | 0.83 |  |
| Site > Lighthouse Report | csharp/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Lighthouse Report | web/vs | ok |  | 0.62 |  |
| Site > Lighthouse Report | flask/vs | ok |  | 0.66 |  |
| Site > Lighthouse Report | flutter/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Lighthouse Report | retro/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Lighthouse Report | dos/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Lighthouse Report | game/vs | ok | Site address [QInputDialog] | 0.9 |  |
| Site > Lighthouse Report | asm/vs | ok | Site address [QInputDialog] | 0.72 |  |
| Site > Lighthouse Report | firmware/vs | ok | Site address [QInputDialog] | 0.82 |  |
| Site > New File | python-tk/vs | ok | New File [NewFileDialog] | 0.88 |  |
| Site > New File | none/vs | ok |  | 0.61 |  |
| Site > New File | python-tk/vscode | ok | New File [NewFileDialog] | 0.77 |  |
| Site > New File | python-tk/agent | ok | New File [NewFileDialog] | 0.88 |  |
| Site > New File | vb6/vs | ok | New File [NewFileDialog] | 0.79 |  |
| Site > New File | csharp/vs | ok | New File [NewFileDialog] | 0.8 |  |
| Site > New File | web/vs | ok | New File [NewFileDialog] | 0.8 |  |
| Site > New File | flask/vs | ok | New File [NewFileDialog] | 0.76 |  |
| Site > New File | flutter/vs | ok | New File [NewFileDialog] | 1.04 |  |
| Site > New File | retro/vs | ok | New File [NewFileDialog] | 0.76 |  |
| Site > New File | dos/vs | ok | New File [NewFileDialog] | 0.79 |  |
| Site > New File | game/vs | ok | New File [NewFileDialog] | 0.77 |  |
| Site > New File | asm/vs | ok | New File [NewFileDialog] | 0.73 |  |
| Site > New File | firmware/vs | ok | New File [NewFileDialog] | 0.78 |  |
| Site > New Folder | python-tk/vs | ok | New Folder [QInputDialog] | 0.92 |  |
| Site > New Folder | none/vs | ok |  | 0.61 |  |
| Site > New Folder | python-tk/vscode | ok | New Folder [QInputDialog] | 0.78 |  |
| Site > New Folder | python-tk/agent | ok | New Folder [QInputDialog] | 0.84 |  |
| Site > New Folder | vb6/vs | ok | New Folder [QInputDialog] | 0.77 |  |
| Site > New Folder | csharp/vs | ok | New Folder [QInputDialog] | 0.82 |  |
| Site > New Folder | web/vs | ok | New Folder [QInputDialog] | 0.75 |  |
| Site > New Folder | flask/vs | ok | New Folder [QInputDialog] | 0.75 |  |
| Site > New Folder | flutter/vs | ok | New Folder [QInputDialog] | 0.76 |  |
| Site > New Folder | retro/vs | ok | New Folder [QInputDialog] | 0.75 |  |
| Site > New Folder | dos/vs | ok | New Folder [QInputDialog] | 0.78 |  |
| Site > New Folder | game/vs | ok | New Folder [QInputDialog] | 0.79 |  |
| Site > New Folder | asm/vs | ok | New Folder [QInputDialog] | 0.71 |  |
| Site > New Folder | firmware/vs | ok | New Folder [QInputDialog] | 0.77 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | python-tk/vs | ok | New Front-end App [NewFrontendDialog] | 0.89 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | none/vs | ok | New Front-end App [NewFrontendDialog] | 0.84 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | python-tk/vscode | ok | New Front-end App [NewFrontendDialog] | 0.82 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | python-tk/agent | ok | New Front-end App [NewFrontendDialog] | 0.85 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | vb6/vs | ok | New Front-end App [NewFrontendDialog] | 0.78 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | csharp/vs | ok | New Front-end App [NewFrontendDialog] | 0.8 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | web/vs | ok | New Front-end App [NewFrontendDialog] | 0.75 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | flask/vs | ok | New Front-end App [NewFrontendDialog] | 1.0 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | flutter/vs | ok | New Front-end App [NewFrontendDialog] | 0.78 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | retro/vs | ok | New Front-end App [NewFrontendDialog] | 0.82 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | dos/vs | ok | New Front-end App [NewFrontendDialog] | 0.8 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | game/vs | ok | New Front-end App [NewFrontendDialog] | 0.85 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | asm/vs | ok | New Front-end App [NewFrontendDialog] | 0.73 |  |
| Site > New Front-end App (React, Vue, Svelte, Angular) | firmware/vs | ok | New Front-end App [NewFrontendDialog] | 0.85 |  |
| Site > Open Database in Adminer | python-tk/vs | ok | Databases [QMessageBox] | 0.81 |  |
| Site > Open Database in Adminer | none/vs | ok | Databases [QMessageBox] | 0.77 |  |
| Site > Open Database in Adminer | python-tk/vscode | ok | Databases [QMessageBox] | 0.79 |  |
| Site > Open Database in Adminer | python-tk/agent | ok | Databases [QMessageBox] | 0.79 |  |
| Site > Open Database in Adminer | vb6/vs | ok | Databases [QMessageBox] | 0.78 |  |
| Site > Open Database in Adminer | csharp/vs | ok | Databases [QMessageBox] | 0.75 |  |
| Site > Open Database in Adminer | web/vs | ok | Databases [QMessageBox] | 0.75 |  |
| Site > Open Database in Adminer | flask/vs | ok |  | 1.54 |  |
| Site > Open Database in Adminer | flutter/vs | ok | Databases [QMessageBox] | 0.76 |  |
| Site > Open Database in Adminer | retro/vs | ok | Databases [QMessageBox] | 0.76 |  |
| Site > Open Database in Adminer | dos/vs | ok | Databases [QMessageBox] | 0.78 |  |
| Site > Open Database in Adminer | game/vs | ok | Databases [QMessageBox] | 0.76 |  |
| Site > Open Database in Adminer | asm/vs | ok | Databases [QMessageBox] | 0.72 |  |
| Site > Open Database in Adminer | firmware/vs | ok | Databases [QMessageBox] | 0.83 |  |
| Site > Open in Browser | web/vs | ok |  | 0.61 |  |
| Site > Open in Browser | flask/vs | ok |  | 0.61 |  |
| Site > Open in Installed Browser > Chrome | python-tk/vs | ok | Site address [QInputDialog] | 0.91 |  |
| Site > Open in Installed Browser > Chrome | none/vs | ok | Site address [QInputDialog] | 0.83 |  |
| Site > Open in Installed Browser > Chrome | python-tk/vscode | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Chrome | python-tk/agent | ok | Site address [QInputDialog] | 0.81 |  |
| Site > Open in Installed Browser > Chrome | vb6/vs | ok | Site address [QInputDialog] | 0.8 |  |
| Site > Open in Installed Browser > Chrome | csharp/vs | ok | Site address [QInputDialog] | 0.77 |  |
| Site > Open in Installed Browser > Chrome | web/vs | ok |  | 0.61 |  |
| Site > Open in Installed Browser > Chrome | flask/vs | ok |  | 0.62 |  |
| Site > Open in Installed Browser > Chrome | flutter/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Chrome | retro/vs | ok | Site address [QInputDialog] | 0.8 |  |
| Site > Open in Installed Browser > Chrome | dos/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Chrome | game/vs | ok | Site address [QInputDialog] | 0.8 |  |
| Site > Open in Installed Browser > Chrome | asm/vs | ok | Site address [QInputDialog] | 0.77 |  |
| Site > Open in Installed Browser > Chrome | firmware/vs | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Open in Installed Browser > Default browser | python-tk/vs | ok | Site address [QInputDialog] | 0.86 |  |
| Site > Open in Installed Browser > Default browser | none/vs | ok | Site address [QInputDialog] | 0.82 |  |
| Site > Open in Installed Browser > Default browser | python-tk/vscode | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Default browser | python-tk/agent | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Open in Installed Browser > Default browser | vb6/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Default browser | csharp/vs | ok | Site address [QInputDialog] | 0.75 |  |
| Site > Open in Installed Browser > Default browser | web/vs | ok |  | 0.6 |  |
| Site > Open in Installed Browser > Default browser | flask/vs | ok |  | 0.6 |  |
| Site > Open in Installed Browser > Default browser | flutter/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Open in Installed Browser > Default browser | retro/vs | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Open in Installed Browser > Default browser | dos/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Default browser | game/vs | ok | Site address [QInputDialog] | 0.77 |  |
| Site > Open in Installed Browser > Default browser | asm/vs | ok | Site address [QInputDialog] | 0.71 |  |
| Site > Open in Installed Browser > Default browser | firmware/vs | ok | Site address [QInputDialog] | 0.81 |  |
| Site > Open in Installed Browser > Edge | python-tk/vs | ok | Site address [QInputDialog] | 0.88 |  |
| Site > Open in Installed Browser > Edge | none/vs | ok | Site address [QInputDialog] | 0.85 |  |
| Site > Open in Installed Browser > Edge | python-tk/vscode | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Edge | python-tk/agent | ok | Site address [QInputDialog] | 0.86 |  |
| Site > Open in Installed Browser > Edge | vb6/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Edge | csharp/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Open in Installed Browser > Edge | web/vs | ok |  | 0.61 |  |
| Site > Open in Installed Browser > Edge | flask/vs | ok |  | 0.62 |  |
| Site > Open in Installed Browser > Edge | flutter/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Open in Installed Browser > Edge | retro/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Edge | dos/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Edge | game/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > Open in Installed Browser > Edge | asm/vs | ok | Site address [QInputDialog] | 0.73 |  |
| Site > Open in Installed Browser > Edge | firmware/vs | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Open in Installed Browser > Firefox | python-tk/vs | ok | Site address [QInputDialog] | 0.93 |  |
| Site > Open in Installed Browser > Firefox | none/vs | ok | Site address [QInputDialog] | 0.8 |  |
| Site > Open in Installed Browser > Firefox | python-tk/vscode | ok | Site address [QInputDialog] | 0.79 |  |
| Site > Open in Installed Browser > Firefox | python-tk/agent | ok | Site address [QInputDialog] | 0.83 |  |
| Site > Open in Installed Browser > Firefox | vb6/vs | ok | Site address [QInputDialog] | 0.81 |  |
| Site > Open in Installed Browser > Firefox | csharp/vs | ok | Site address [QInputDialog] | 0.74 |  |
| Site > Open in Installed Browser > Firefox | web/vs | ok |  | 0.62 |  |
| Site > Open in Installed Browser > Firefox | flask/vs | ok |  | 0.62 |  |
| Site > Open in Installed Browser > Firefox | flutter/vs | ok | Site address [QInputDialog] | 0.77 |  |
| Site > Open in Installed Browser > Firefox | retro/vs | ok | Site address [QInputDialog] | 0.75 |  |
| Site > Open in Installed Browser > Firefox | dos/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Firefox | game/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > Open in Installed Browser > Firefox | asm/vs | ok | Site address [QInputDialog] | 0.73 |  |
| Site > Open in Installed Browser > Firefox | firmware/vs | ok | Site address [QInputDialog] | 0.82 |  |
| Site > Preview | python-tk/vs | ok |  | 0.61 |  |
| Site > Preview | none/vs | ok |  | 0.62 |  |
| Site > Preview | python-tk/vscode | ok |  | 0.79 |  |
| Site > Preview | python-tk/agent | ok |  | 0.83 |  |
| Site > Preview | vb6/vs | ok |  | 0.63 |  |
| Site > Preview | csharp/vs | ok |  | 0.62 |  |
| Site > Preview | web/vs | ok |  | 0.61 |  |
| Site > Preview | flask/vs | ok |  | 0.61 |  |
| Site > Preview | flutter/vs | ok |  | 0.62 |  |
| Site > Preview | retro/vs | ok |  | 0.62 |  |
| Site > Preview | dos/vs | ok |  | 0.62 |  |
| Site > Preview | game/vs | ok |  | 0.61 |  |
| Site > Preview | asm/vs | ok |  | 0.62 |  |
| Site > Preview | firmware/vs | ok |  | 0.62 |  |
| Site > Publish | python-tk/vs | ok | Publish - EvDemo [PublishDialog] | 1.04 |  |
| Site > Publish | none/vs | ok | Publish [QMessageBox] | 0.82 |  |
| Site > Publish | python-tk/vscode | ok | Publish - EvDemo [PublishDialog] | 0.9 |  |
| Site > Publish | python-tk/agent | ok | Publish - EvDemo [PublishDialog] | 1.18 |  |
| Site > Publish | vb6/vs | ok | Publish - Greeter [PublishDialog] | 0.93 |  |
| Site > Publish | csharp/vs | ok | Publish - HelloCSharp [PublishDialog] | 0.87 |  |
| Site > Publish | web/vs | ok | Publish - Boot Site [PublishDialog] | 0.85 |  |
| Site > Publish | flask/vs | ok | Publish - Flask_Todo [PublishDialog] | 0.8 |  |
| Site > Publish | flutter/vs | ok | Publish - IdeProj [PublishDialog] | 0.89 |  |
| Site > Publish | retro/vs | ok | Publish - NesStarCatcher [PublishDialog] | 0.87 |  |
| Site > Publish | dos/vs | ok | Publish - Contacts [PublishDialog] | 0.92 |  |
| Site > Publish | game/vs | ok | Publish - Platformer [PublishDialog] | 0.94 |  |
| Site > Publish | asm/vs | ok | Publish - CoreNasmForms [PublishDialog] | 0.8 |  |
| Site > Publish | firmware/vs | ok | Publish - CrawlEcu [PublishDialog] | 0.86 |  |
| Site > Publish Preview (dry run) | python-tk/vs | ok | Publish [QMessageBox] \| Publish - EvDemo [PublishDialog] | 1.0 |  |
| Site > Publish Preview (dry run) | none/vs | ok | Publish [QMessageBox] | 0.79 |  |
| Site > Publish Preview (dry run) | python-tk/vscode | ok | Publish [QMessageBox] \| Publish - EvDemo [PublishDialog] | 0.85 |  |
| Site > Publish Preview (dry run) | python-tk/agent | ok | Publish [QMessageBox] \| Publish - EvDemo [PublishDialog] | 0.96 |  |
| Site > Publish Preview (dry run) | vb6/vs | ok | Publish [QMessageBox] \| Publish - Greeter [PublishDialog] | 0.88 |  |
| Site > Publish Preview (dry run) | csharp/vs | ok | Publish [QMessageBox] \| Publish - HelloCSharp [PublishDialog] | 0.84 |  |
| Site > Publish Preview (dry run) | web/vs | ok | Publish [QMessageBox] \| Publish - Boot Site [PublishDialog] | 0.78 |  |
| Site > Publish Preview (dry run) | flask/vs | ok | Publish [QMessageBox] \| Publish - Flask_Todo [PublishDialog] | 0.77 |  |
| Site > Publish Preview (dry run) | flutter/vs | ok | Publish [QMessageBox] \| Publish - IdeProj [PublishDialog] | 0.83 |  |
| Site > Publish Preview (dry run) | retro/vs | ok | Publish [QMessageBox] \| Publish - NesStarCatcher [PublishDialog] | 0.83 |  |
| Site > Publish Preview (dry run) | dos/vs | ok | Publish [QMessageBox] \| Publish - Contacts [PublishDialog] | 0.86 |  |
| Site > Publish Preview (dry run) | game/vs | ok | Publish [QMessageBox] \| Publish - Platformer [PublishDialog] | 0.92 |  |
| Site > Publish Preview (dry run) | asm/vs | ok | Publish [QMessageBox] \| Publish - CoreNasmForms [PublishDialog] | 0.8 |  |
| Site > Publish Preview (dry run) | firmware/vs | ok | Publish [QMessageBox] \| Publish - CrawlEcu [PublishDialog] | 0.8 |  |
| Site > REST Client | python-tk/vs | ok |  | 1.2 |  |
| Site > REST Client | none/vs | ok |  | 1.04 |  |
| Site > REST Client | python-tk/vscode | ok |  | 1.05 |  |
| Site > REST Client | python-tk/agent | ok |  | 0.99 |  |
| Site > REST Client | vb6/vs | ok |  | 0.89 |  |
| Site > REST Client | csharp/vs | ok |  | 0.92 |  |
| Site > REST Client | web/vs | ok |  | 0.88 |  |
| Site > REST Client | flask/vs | ok |  | 0.86 |  |
| Site > REST Client | flutter/vs | ok |  | 0.9 |  |
| Site > REST Client | retro/vs | ok |  | 0.85 |  |
| Site > REST Client | dos/vs | ok |  | 0.93 |  |
| Site > REST Client | game/vs | ok |  | 1.12 |  |
| Site > REST Client | asm/vs | ok |  | 0.81 |  |
| Site > REST Client | firmware/vs | ok |  | 0.92 |  |
| Site > Rails Panel (Console, Routes, Models) | python-tk/vs | ok |  | 0.6 |  |
| Site > Rails Panel (Console, Routes, Models) | none/vs | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | python-tk/vscode | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | python-tk/agent | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | vb6/vs | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | csharp/vs | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | web/vs | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | flask/vs | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | flutter/vs | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | retro/vs | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | dos/vs | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | game/vs | ok |  | 0.62 |  |
| Site > Rails Panel (Console, Routes, Models) | asm/vs | ok |  | 0.61 |  |
| Site > Rails Panel (Console, Routes, Models) | firmware/vs | ok |  | 0.62 |  |
| Site > Reports | python-tk/vs | ok |  | 0.61 |  |
| Site > Reports | none/vs | ok |  | 0.61 |  |
| Site > Reports | python-tk/vscode | ok |  | 0.61 |  |
| Site > Reports | python-tk/agent | ok |  | 0.61 |  |
| Site > Reports | vb6/vs | ok |  | 0.61 |  |
| Site > Reports | csharp/vs | ok |  | 0.61 |  |
| Site > Reports | web/vs | ok |  | 0.6 |  |
| Site > Reports | flask/vs | ok |  | 0.61 |  |
| Site > Reports | flutter/vs | ok |  | 0.61 |  |
| Site > Reports | retro/vs | ok |  | 0.6 |  |
| Site > Reports | dos/vs | ok |  | 0.61 |  |
| Site > Reports | game/vs | ok |  | 0.61 |  |
| Site > Reports | asm/vs | ok |  | 0.61 |  |
| Site > Reports | firmware/vs | ok |  | 0.61 |  |
| Site > Requests | python-tk/vs | ok |  | 0.61 |  |
| Site > Requests | none/vs | ok |  | 0.62 |  |
| Site > Requests | python-tk/vscode | ok |  | 0.61 |  |
| Site > Requests | python-tk/agent | ok |  | 0.62 |  |
| Site > Requests | vb6/vs | ok |  | 0.63 |  |
| Site > Requests | csharp/vs | ok |  | 0.62 |  |
| Site > Requests | web/vs | ok |  | 0.61 |  |
| Site > Requests | flask/vs | ok |  | 0.61 |  |
| Site > Requests | flutter/vs | ok |  | 0.62 |  |
| Site > Requests | retro/vs | ok |  | 0.62 |  |
| Site > Requests | dos/vs | ok |  | 0.62 |  |
| Site > Requests | game/vs | ok |  | 0.62 |  |
| Site > Requests | asm/vs | ok |  | 0.62 |  |
| Site > Requests | firmware/vs | ok |  | 0.62 |  |
| Site > Run Site in Preview | web/vs | ok |  | 0.68 |  |
| Site > Run Site in Preview | flask/vs | ok |  | 0.61 |  |
| Site > SEO Report | python-tk/vs | ok | Site address [QInputDialog] | 0.93 |  |
| Site > SEO Report | none/vs | ok | Site address [QInputDialog] | 0.86 |  |
| Site > SEO Report | python-tk/vscode | ok | Site address [QInputDialog] | 1.03 |  |
| Site > SEO Report | python-tk/agent | ok | Site address [QInputDialog] | 1.16 |  |
| Site > SEO Report | vb6/vs | ok | Site address [QInputDialog] | 0.81 |  |
| Site > SEO Report | csharp/vs | ok | Site address [QInputDialog] | 0.81 |  |
| Site > SEO Report | web/vs | ok |  | 0.61 |  |
| Site > SEO Report | flask/vs | ok |  | 0.61 |  |
| Site > SEO Report | flutter/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > SEO Report | retro/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > SEO Report | dos/vs | ok | Site address [QInputDialog] | 0.82 |  |
| Site > SEO Report | game/vs | ok | Site address [QInputDialog] | 0.91 |  |
| Site > SEO Report | asm/vs | ok | Site address [QInputDialog] | 0.72 |  |
| Site > SEO Report | firmware/vs | ok | Site address [QInputDialog] | 0.84 |  |
| Site > Site Settings | python-tk/vs | ok |  | 0.61 |  |
| Site > Site Settings | none/vs | ok |  | 0.61 |  |
| Site > Site Settings | python-tk/vscode | ok |  | 0.6 |  |
| Site > Site Settings | python-tk/agent | ok |  | 0.61 |  |
| Site > Site Settings | vb6/vs | ok |  | 0.61 |  |
| Site > Site Settings | csharp/vs | ok |  | 0.6 |  |
| Site > Site Settings | web/vs | ok | Site Settings - Boot Site [QDialog] | 0.77 |  |
| Site > Site Settings | flask/vs | ok | Site Settings - Flask_Todo [QDialog] | 0.78 |  |
| Site > Site Settings | flutter/vs | ok |  | 0.61 |  |
| Site > Site Settings | retro/vs | ok |  | 0.61 |  |
| Site > Site Settings | dos/vs | ok |  | 0.6 |  |
| Site > Site Settings | game/vs | ok |  | 0.6 |  |
| Site > Site Settings | asm/vs | ok |  | 0.61 |  |
| Site > Site Settings | firmware/vs | ok |  | 0.6 |  |
| Site > SuperPreview | python-tk/vs | ok | Site address [QInputDialog] | 0.86 |  |
| Site > SuperPreview | none/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > SuperPreview | python-tk/vscode | ok | Site address [QInputDialog] | 0.8 |  |
| Site > SuperPreview | python-tk/agent | ok | Site address [QInputDialog] | 0.86 |  |
| Site > SuperPreview | vb6/vs | ok | Site address [QInputDialog] | 0.8 |  |
| Site > SuperPreview | csharp/vs | ok | Site address [QInputDialog] | 0.78 |  |
| Site > SuperPreview | web/vs | ok | SuperPreview [SuperPreview] | 0.83 |  |
| Site > SuperPreview | flask/vs | ok | SuperPreview [SuperPreview] | 0.83 |  |
| Site > SuperPreview | flutter/vs | ok | Site address [QInputDialog] | 0.76 |  |
| Site > SuperPreview | retro/vs | ok | Site address [QInputDialog] | 0.81 |  |
| Site > SuperPreview | dos/vs | ok | Site address [QInputDialog] | 0.79 |  |
| Site > SuperPreview | game/vs | ok | Site address [QInputDialog] | 0.83 |  |
| Site > SuperPreview | asm/vs | ok | Site address [QInputDialog] | 0.73 |  |
| Site > SuperPreview | firmware/vs | ok | Site address [QInputDialog] | 0.95 |  |
| Solution Explorer > (code) > Add Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 1.36 |  |
| Solution Explorer > (code) > Add Windows Form | python-tk/vscode | ok | Add Windows Form [AddItemDialog] | 0.82 |  |
| Solution Explorer > (code) > Add Windows Form | python-tk/agent | ok | Add Windows Form [AddItemDialog] | 0.84 |  |
| Solution Explorer > (code) > Add Windows Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.78 |  |
| Solution Explorer > (code) > Add Windows Form | csharp/vs | ok | Add Windows Form [AddItemDialog] | 0.79 |  |
| Solution Explorer > (code) > Add Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.84 |  |
| Solution Explorer > (code) > Add Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.77 |  |
| Solution Explorer > (code) > Delete | python-tk/vs | ok | RAD IDE [QMessageBox] | 1.85 |  |
| Solution Explorer > (code) > Delete | python-tk/vscode | ok | RAD IDE [QMessageBox] | 0.8 |  |
| Solution Explorer > (code) > Delete | python-tk/agent | ok | RAD IDE [QMessageBox] | 0.83 |  |
| Solution Explorer > (code) > Delete | vb6/vs | ok | RAD IDE [QMessageBox] | 0.82 |  |
| Solution Explorer > (code) > Delete | csharp/vs | ok | RAD IDE [QMessageBox] | 0.75 |  |
| Solution Explorer > (code) > Delete | flutter/vs | ok | RAD IDE [QMessageBox] | 0.84 |  |
| Solution Explorer > (code) > Delete | asm/vs | ok | RAD IDE [QMessageBox] | 0.77 |  |
| Solution Explorer > (code) > Format This File (ruff) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (code) > Format This File (ruff) | python-tk/vscode | ok |  | 0.64 |  |
| Solution Explorer > (code) > Format This File (ruff) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (code) > Open (Designer) | python-tk/vs | ok |  | 0.81 |  |
| Solution Explorer > (code) > Open (Designer) | python-tk/vscode | ok |  | 0.72 |  |
| Solution Explorer > (code) > Open (Designer) | python-tk/agent | ok |  | 0.81 |  |
| Solution Explorer > (code) > Open (Designer) | vb6/vs | ok |  | 0.66 |  |
| Solution Explorer > (code) > Open (Designer) | csharp/vs | ok |  | 0.67 |  |
| Solution Explorer > (code) > Open (Designer) | flutter/vs | ok |  | 1.31 |  |
| Solution Explorer > (code) > Open (Designer) | asm/vs | ok |  | 0.65 |  |
| Solution Explorer > (code) > Rename | python-tk/vs | ok | إعادة تسمية النموذج [QInputDialog] | 1.36 |  |
| Solution Explorer > (code) > Rename | python-tk/vscode | ok | Rename Form [QInputDialog] | 0.8 |  |
| Solution Explorer > (code) > Rename | python-tk/agent | ok | Rename Form [QInputDialog] | 0.85 |  |
| Solution Explorer > (code) > Rename | vb6/vs | ok | Rename Form [QInputDialog] | 0.8 |  |
| Solution Explorer > (code) > Rename | csharp/vs | ok | Rename Form [QInputDialog] | 0.78 |  |
| Solution Explorer > (code) > Rename | flutter/vs | ok | Rename Form [QInputDialog] | 0.76 |  |
| Solution Explorer > (code) > Rename | asm/vs | ok | Rename Form [QInputDialog] | 0.76 |  |
| Solution Explorer > (code) > View Code | python-tk/vs | ok |  | 0.78 |  |
| Solution Explorer > (code) > View Code | python-tk/vscode | ok |  | 1.39 |  |
| Solution Explorer > (code) > View Code | python-tk/agent | ok |  | 0.68 |  |
| Solution Explorer > (code) > View Code | vb6/vs | ok |  | 0.67 |  |
| Solution Explorer > (code) > View Code | csharp/vs | ok |  | 0.67 |  |
| Solution Explorer > (code) > View Code | flutter/vs | ok |  | 0.71 |  |
| Solution Explorer > (code) > View Code | asm/vs | ok |  | 0.67 |  |
| Solution Explorer > (code) > View Generated Code | python-tk/vs | ok |  | 1.22 |  |
| Solution Explorer > (code) > View Generated Code | python-tk/vscode | ok |  | 0.97 |  |
| Solution Explorer > (code) > View Generated Code | python-tk/agent | ok |  | 0.75 |  |
| Solution Explorer > (code) > View Generated Code | vb6/vs | ok |  | 0.7 |  |
| Solution Explorer > (code) > View Generated Code | csharp/vs | ok |  | 0.7 |  |
| Solution Explorer > (code) > View Generated Code | flutter/vs | ok |  | 0.96 |  |
| Solution Explorer > (code) > View Generated Code | asm/vs | ok |  | 0.71 |  |
| Solution Explorer > (design) > Add Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 1.23 |  |
| Solution Explorer > (design) > Add Windows Form | python-tk/vscode | ok | Add Windows Form [AddItemDialog] | 0.81 |  |
| Solution Explorer > (design) > Add Windows Form | python-tk/agent | ok | Add Windows Form [AddItemDialog] | 0.9 |  |
| Solution Explorer > (design) > Add Windows Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.78 |  |
| Solution Explorer > (design) > Add Windows Form | csharp/vs | ok | Add Windows Form [AddItemDialog] | 0.75 |  |
| Solution Explorer > (design) > Add Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.82 |  |
| Solution Explorer > (design) > Add Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.77 |  |
| Solution Explorer > (design) > Delete | python-tk/vs | ok | RAD IDE [QMessageBox] | 1.24 |  |
| Solution Explorer > (design) > Delete | python-tk/vscode | ok | RAD IDE [QMessageBox] | 0.86 |  |
| Solution Explorer > (design) > Delete | python-tk/agent | ok | RAD IDE [QMessageBox] | 0.92 |  |
| Solution Explorer > (design) > Delete | vb6/vs | ok | RAD IDE [QMessageBox] | 0.76 |  |
| Solution Explorer > (design) > Delete | csharp/vs | ok | RAD IDE [QMessageBox] | 0.75 |  |
| Solution Explorer > (design) > Delete | flutter/vs | ok | RAD IDE [QMessageBox] | 0.83 |  |
| Solution Explorer > (design) > Delete | asm/vs | ok | RAD IDE [QMessageBox] | 0.74 |  |
| Solution Explorer > (design) > Open (Designer) | python-tk/vs | ok |  | 0.8 |  |
| Solution Explorer > (design) > Open (Designer) | python-tk/vscode | ok |  | 0.74 |  |
| Solution Explorer > (design) > Open (Designer) | python-tk/agent | ok |  | 0.73 |  |
| Solution Explorer > (design) > Open (Designer) | vb6/vs | ok |  | 0.67 |  |
| Solution Explorer > (design) > Open (Designer) | csharp/vs | ok |  | 0.67 |  |
| Solution Explorer > (design) > Open (Designer) | flutter/vs | ok |  | 1.1 |  |
| Solution Explorer > (design) > Open (Designer) | asm/vs | ok |  | 0.64 |  |
| Solution Explorer > (design) > Rename | python-tk/vs | ok | إعادة تسمية النموذج [QInputDialog] | 1.19 |  |
| Solution Explorer > (design) > Rename | python-tk/vscode | ok | Rename Form [QInputDialog] | 0.85 |  |
| Solution Explorer > (design) > Rename | python-tk/agent | ok | Rename Form [QInputDialog] | 0.89 |  |
| Solution Explorer > (design) > Rename | vb6/vs | ok | Rename Form [QInputDialog] | 0.76 |  |
| Solution Explorer > (design) > Rename | csharp/vs | ok | Rename Form [QInputDialog] | 0.73 |  |
| Solution Explorer > (design) > Rename | flutter/vs | ok | Rename Form [QInputDialog] | 0.78 |  |
| Solution Explorer > (design) > Rename | asm/vs | ok | Rename Form [QInputDialog] | 0.71 |  |
| Solution Explorer > (design) > View Code | python-tk/vs | ok |  | 0.77 |  |
| Solution Explorer > (design) > View Code | python-tk/vscode | ok |  | 0.74 |  |
| Solution Explorer > (design) > View Code | python-tk/agent | ok |  | 0.8 |  |
| Solution Explorer > (design) > View Code | vb6/vs | ok |  | 0.7 |  |
| Solution Explorer > (design) > View Code | csharp/vs | ok |  | 0.7 |  |
| Solution Explorer > (design) > View Code | flutter/vs | ok |  | 0.78 |  |
| Solution Explorer > (design) > View Code | asm/vs | ok |  | 0.69 |  |
| Solution Explorer > (design) > View Generated Code | python-tk/vs | ok |  | 0.86 |  |
| Solution Explorer > (design) > View Generated Code | python-tk/vscode | ok |  | 0.73 |  |
| Solution Explorer > (design) > View Generated Code | python-tk/agent | ok |  | 0.82 |  |
| Solution Explorer > (design) > View Generated Code | vb6/vs | ok |  | 0.71 |  |
| Solution Explorer > (design) > View Generated Code | csharp/vs | ok |  | 0.67 |  |
| Solution Explorer > (design) > View Generated Code | flutter/vs | ok |  | 0.88 |  |
| Solution Explorer > (design) > View Generated Code | asm/vs | ok |  | 0.7 |  |
| Solution Explorer > (ecuproj) > Open Firmware & ECU Workbench | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (ecuproj_original) > Analyze Firmware | firmware/vs | ok |  | 1.0 |  |
| Solution Explorer > (ecuproj_original) > Open With > Firmware & ECU Workbench | firmware/vs | ok |  | 1.07 |  |
| Solution Explorer > (ecuproj_original) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (ecuproj_work) > Analyze Firmware | firmware/vs | ok |  | 0.68 |  |
| Solution Explorer > (ecuproj_work) > Open With > Firmware & ECU Workbench | firmware/vs | ok |  | 1.05 |  |
| Solution Explorer > (ecuproj_work) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (generated) > Add Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 1.45 |  |
| Solution Explorer > (generated) > Add Windows Form | python-tk/vscode | ok | Add Windows Form [AddItemDialog] | 0.8 |  |
| Solution Explorer > (generated) > Add Windows Form | python-tk/agent | ok | Add Windows Form [AddItemDialog] | 0.84 |  |
| Solution Explorer > (generated) > Add Windows Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.79 |  |
| Solution Explorer > (generated) > Add Windows Form | csharp/vs | ok | Add Windows Form [AddItemDialog] | 0.75 |  |
| Solution Explorer > (generated) > Add Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.91 |  |
| Solution Explorer > (generated) > Add Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.77 |  |
| Solution Explorer > (generated) > Delete | python-tk/vs | ok | RAD IDE [QMessageBox] | 1.31 |  |
| Solution Explorer > (generated) > Delete | python-tk/vscode | ok | RAD IDE [QMessageBox] | 0.8 |  |
| Solution Explorer > (generated) > Delete | python-tk/agent | ok | RAD IDE [QMessageBox] | 0.81 |  |
| Solution Explorer > (generated) > Delete | vb6/vs | ok | RAD IDE [QMessageBox] | 0.77 |  |
| Solution Explorer > (generated) > Delete | csharp/vs | ok | RAD IDE [QMessageBox] | 0.72 |  |
| Solution Explorer > (generated) > Delete | flutter/vs | ok | RAD IDE [QMessageBox] | 0.82 |  |
| Solution Explorer > (generated) > Delete | asm/vs | ok | RAD IDE [QMessageBox] | 0.75 |  |
| Solution Explorer > (generated) > Open (Designer) | python-tk/vs | ok |  | 0.77 |  |
| Solution Explorer > (generated) > Open (Designer) | python-tk/vscode | ok |  | 0.67 |  |
| Solution Explorer > (generated) > Open (Designer) | python-tk/agent | ok |  | 0.69 |  |
| Solution Explorer > (generated) > Open (Designer) | vb6/vs | ok |  | 0.67 |  |
| Solution Explorer > (generated) > Open (Designer) | csharp/vs | ok |  | 0.68 |  |
| Solution Explorer > (generated) > Open (Designer) | flutter/vs | ok |  | 1.68 |  |
| Solution Explorer > (generated) > Open (Designer) | asm/vs | ok |  | 0.67 |  |
| Solution Explorer > (generated) > Rename | python-tk/vs | ok | إعادة تسمية النموذج [QInputDialog] | 1.49 |  |
| Solution Explorer > (generated) > Rename | python-tk/vscode | ok | Rename Form [QInputDialog] | 0.82 |  |
| Solution Explorer > (generated) > Rename | python-tk/agent | ok | Rename Form [QInputDialog] | 0.83 |  |
| Solution Explorer > (generated) > Rename | vb6/vs | ok | Rename Form [QInputDialog] | 0.76 |  |
| Solution Explorer > (generated) > Rename | csharp/vs | ok | Rename Form [QInputDialog] | 0.75 |  |
| Solution Explorer > (generated) > Rename | flutter/vs | ok | Rename Form [QInputDialog] | 0.83 |  |
| Solution Explorer > (generated) > Rename | asm/vs | ok | Rename Form [QInputDialog] | 0.73 |  |
| Solution Explorer > (generated) > View Code | python-tk/vs | ok |  | 0.77 |  |
| Solution Explorer > (generated) > View Code | python-tk/vscode | ok |  | 1.21 |  |
| Solution Explorer > (generated) > View Code | python-tk/agent | ok |  | 0.69 |  |
| Solution Explorer > (generated) > View Code | vb6/vs | ok |  | 0.66 |  |
| Solution Explorer > (generated) > View Code | csharp/vs | ok |  | 0.66 |  |
| Solution Explorer > (generated) > View Code | flutter/vs | ok |  | 0.73 |  |
| Solution Explorer > (generated) > View Code | asm/vs | ok |  | 0.69 |  |
| Solution Explorer > (generated) > View Generated Code | python-tk/vs | ok |  | 0.99 |  |
| Solution Explorer > (generated) > View Generated Code | python-tk/vscode | ok |  | 0.88 |  |
| Solution Explorer > (generated) > View Generated Code | python-tk/agent | ok |  | 0.76 |  |
| Solution Explorer > (generated) > View Generated Code | vb6/vs | ok |  | 0.7 |  |
| Solution Explorer > (generated) > View Generated Code | csharp/vs | ok |  | 0.69 |  |
| Solution Explorer > (generated) > View Generated Code | flutter/vs | ok |  | 0.96 |  |
| Solution Explorer > (generated) > View Generated Code | asm/vs | ok |  | 0.7 |  |
| Solution Explorer > (module) > Delete | python-tk/vs | ok | RAD IDE [QMessageBox] | 1.28 |  |
| Solution Explorer > (module) > Delete | python-tk/vscode | ok | RAD IDE [QMessageBox] | 1.33 |  |
| Solution Explorer > (module) > Delete | python-tk/agent | ok | RAD IDE [QMessageBox] | 0.93 |  |
| Solution Explorer > (module) > Delete | csharp/vs | ok | RAD IDE [QMessageBox] | 0.74 |  |
| Solution Explorer > (module) > Delete | flutter/vs | ok | RAD IDE [QMessageBox] | 0.88 |  |
| Solution Explorer > (module) > Delete | retro/vs | ok | RAD IDE [QMessageBox] | 0.75 |  |
| Solution Explorer > (module) > Delete | dos/vs | ok | RAD IDE [QMessageBox] | 0.8 |  |
| Solution Explorer > (module) > Delete | game/vs | ok | RAD IDE [QMessageBox] | 0.76 |  |
| Solution Explorer > (module) > Delete | firmware/vs | ok | RAD IDE [QMessageBox] | 0.97 |  |
| Solution Explorer > (module) > Format This File (ruff) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (module) > Format This File (ruff) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (module) > Format This File (ruff) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (module) > Format This File (ruff) | game/vs | ok |  | 0.63 |  |
| Solution Explorer > (module) > Open | python-tk/vs | ok |  | 0.84 |  |
| Solution Explorer > (module) > Open | python-tk/vscode | ok |  | 0.71 |  |
| Solution Explorer > (module) > Open | python-tk/agent | ok |  | 0.72 |  |
| Solution Explorer > (module) > Open | csharp/vs | ok |  | 0.69 |  |
| Solution Explorer > (module) > Open | flutter/vs | ok |  | 0.81 |  |
| Solution Explorer > (module) > Open | retro/vs | ok |  | 0.65 |  |
| Solution Explorer > (module) > Open | dos/vs | ok |  | 0.76 |  |
| Solution Explorer > (module) > Open | game/vs | ok |  | 0.67 |  |
| Solution Explorer > (module) > Open | firmware/vs | ok |  | 0.71 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | python-tk/vs | ok |  | 1.83 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | python-tk/vscode | ok |  | 1.37 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | python-tk/agent | ok |  | 1.28 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | csharp/vs | ok |  | 0.98 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | flutter/vs | ok |  | 1.22 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | retro/vs | ok |  | 1.16 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | dos/vs | ok |  | 1.17 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | game/vs | ok |  | 1.11 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench | firmware/vs | ok |  | 1.02 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | python-tk/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | python-tk/vscode | ok |  | 0.6 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | python-tk/agent | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | csharp/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (module) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | firmware/vs | ok |  | 0.6 |  |
| Solution Explorer > (project) > Add > Existing Files | web/vs | ok | Add Existing Files [QFileDialog] | 0.86 |  |
| Solution Explorer > (project) > Add > Existing Files | flask/vs | ok | Add Existing Files [QFileDialog] | 0.87 |  |
| Solution Explorer > (project) > Add > Existing Item | python-tk/vs | ok | إضافة عنصر موجود [QFileDialog] | 1.5 |  |
| Solution Explorer > (project) > Add > Existing Item | python-tk/vscode | ok | Add Existing Item [QFileDialog] | 1.0 |  |
| Solution Explorer > (project) > Add > Existing Item | python-tk/agent | ok | Add Existing Item [QFileDialog] | 0.99 |  |
| Solution Explorer > (project) > Add > Existing Item | vb6/vs | ok | Add Existing Item [QFileDialog] | 0.99 |  |
| Solution Explorer > (project) > Add > Existing Item | csharp/vs | ok | Add Existing Item [QFileDialog] | 0.82 |  |
| Solution Explorer > (project) > Add > Existing Item | flutter/vs | ok | Add Existing Item [QFileDialog] | 1.05 |  |
| Solution Explorer > (project) > Add > Existing Item | retro/vs | ok | Add Existing Item [QFileDialog] | 0.84 |  |
| Solution Explorer > (project) > Add > Existing Item | dos/vs | ok | Add Existing Item [QFileDialog] | 1.17 |  |
| Solution Explorer > (project) > Add > Existing Item | game/vs | ok | Add Existing Item [QFileDialog] | 0.86 |  |
| Solution Explorer > (project) > Add > Existing Item | asm/vs | ok | Add Existing Item [QFileDialog] | 0.81 |  |
| Solution Explorer > (project) > Add > Existing Item | firmware/vs | ok | Add Existing Item [QFileDialog] | 0.93 |  |
| Solution Explorer > (project) > Add > Module | python-tk/vs | ok | Add Module [AddItemDialog] | 1.33 |  |
| Solution Explorer > (project) > Add > Module | python-tk/vscode | ok | Add Module [AddItemDialog] | 0.82 |  |
| Solution Explorer > (project) > Add > Module | python-tk/agent | ok | Add Module [AddItemDialog] | 0.85 |  |
| Solution Explorer > (project) > Add > Module | vb6/vs | ok | Add Module [AddItemDialog] | 0.79 |  |
| Solution Explorer > (project) > Add > Module | csharp/vs | ok | Add Module [AddItemDialog] | 0.76 |  |
| Solution Explorer > (project) > Add > Module | flutter/vs | ok | Add Module [AddItemDialog] | 0.87 |  |
| Solution Explorer > (project) > Add > Module | retro/vs | ok | Add Module [AddItemDialog] | 0.76 |  |
| Solution Explorer > (project) > Add > Module | dos/vs | ok | Add Module [AddItemDialog] | 1.01 |  |
| Solution Explorer > (project) > Add > Module | game/vs | ok | Add Module [AddItemDialog] | 0.77 |  |
| Solution Explorer > (project) > Add > Module | asm/vs | ok | Add Module [AddItemDialog] | 0.74 |  |
| Solution Explorer > (project) > Add > Module | firmware/vs | ok | Add Module [AddItemDialog] | 0.88 |  |
| Solution Explorer > (project) > Add > New File | web/vs | ok | New File [NewFileDialog] | 0.75 |  |
| Solution Explorer > (project) > Add > New File | flask/vs | ok | New File [NewFileDialog] | 0.73 |  |
| Solution Explorer > (project) > Add > New Folder | web/vs | ok | New Folder [QInputDialog] | 0.74 |  |
| Solution Explorer > (project) > Add > New Folder | flask/vs | ok | New Folder [QInputDialog] | 0.73 |  |
| Solution Explorer > (project) > Add > Reference | python-tk/vs | ok | Reference Manager - EvDemo [AddReferenceDialog] | 1.27 |  |
| Solution Explorer > (project) > Add > Reference | python-tk/vscode | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.87 |  |
| Solution Explorer > (project) > Add > Reference | python-tk/agent | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.84 |  |
| Solution Explorer > (project) > Add > Reference | vb6/vs | ok | Reference Manager - Greeter [AddReferenceDialog] | 0.79 |  |
| Solution Explorer > (project) > Add > Reference | csharp/vs | ok | Reference Manager - HelloCSharp [AddReferenceDialog] | 0.78 |  |
| Solution Explorer > (project) > Add > Reference | flutter/vs | ok | Reference Manager - IdeProj [AddReferenceDialog] | 0.87 |  |
| Solution Explorer > (project) > Add > Reference | retro/vs | ok | Reference Manager - NesStarCatcher [AddReferenceDialog] | 0.79 |  |
| Solution Explorer > (project) > Add > Reference | dos/vs | ok | Reference Manager - Contacts [AddReferenceDialog] | 0.91 |  |
| Solution Explorer > (project) > Add > Reference | game/vs | ok | Reference Manager - Platformer [AddReferenceDialog] | 0.76 |  |
| Solution Explorer > (project) > Add > Reference | asm/vs | ok | Reference Manager - CoreNasmForms [AddReferenceDialog] | 0.76 |  |
| Solution Explorer > (project) > Add > Reference | firmware/vs | ok | Reference Manager - CrawlEcu [AddReferenceDialog] | 0.89 |  |
| Solution Explorer > (project) > Add > Windows Form | python-tk/vs | ok | Add Windows Form [AddItemDialog] | 1.27 |  |
| Solution Explorer > (project) > Add > Windows Form | python-tk/vscode | ok | Add Windows Form [AddItemDialog] | 0.8 |  |
| Solution Explorer > (project) > Add > Windows Form | python-tk/agent | ok | Add Windows Form [AddItemDialog] | 0.82 |  |
| Solution Explorer > (project) > Add > Windows Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.81 |  |
| Solution Explorer > (project) > Add > Windows Form | csharp/vs | ok | Add Windows Form [AddItemDialog] | 0.72 |  |
| Solution Explorer > (project) > Add > Windows Form | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.83 |  |
| Solution Explorer > (project) > Add > Windows Form | retro/vs | ok | Add Windows Form [AddItemDialog] | 0.75 |  |
| Solution Explorer > (project) > Add > Windows Form | dos/vs | ok | Add Windows Form [AddItemDialog] | 0.88 |  |
| Solution Explorer > (project) > Add > Windows Form | game/vs | ok | Add Windows Form [AddItemDialog] | 0.74 |  |
| Solution Explorer > (project) > Add > Windows Form | asm/vs | ok | Add Windows Form [AddItemDialog] | 0.72 |  |
| Solution Explorer > (project) > Add > Windows Form | firmware/vs | ok | Add Windows Form [AddItemDialog] | 0.85 |  |
| Solution Explorer > (project) > Add Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.8 |  |
| Solution Explorer > (project) > Analyze (flutter analyze) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (project) > Build | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | vb6/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | csharp/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | flutter/vs | ok |  | 0.73 |  |
| Solution Explorer > (project) > Build | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Build | dos/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Build | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Build | asm/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Build > Build APK (Android) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build > Build Web | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build > Build Windows | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.95 |  |
| Solution Explorer > (project) > Build EXE / Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] | 1.42 |  |
| Solution Explorer > (project) > Build EXE / Installer | python-tk/vscode | ok | Publish EvDemo [PublishDialog] | 0.92 |  |
| Solution Explorer > (project) > Build EXE / Installer | python-tk/agent | ok | Publish EvDemo [PublishDialog] | 0.96 |  |
| Solution Explorer > (project) > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.9 |  |
| Solution Explorer > (project) > Build One-File EXE (PyInstaller) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Clean (flutter clean) | flutter/vs | ok |  | 0.64 |  |
| Solution Explorer > (project) > Create .venv | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Create .venv | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Create .venv | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (project) > Create .venv | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Export to Godot | game/vs | ok |  | 8.29 |  |
| Solution Explorer > (project) > Flask Shell | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Flutter Doctor | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format Code (dart format) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/agent | ok |  | 0.66 |  |
| Solution Explorer > (project) > Format and Lint > Fix Lint Problems (ruff check --fix) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (black) | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (black) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (black) | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (black) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (ruff) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (ruff) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (ruff) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (project) > Format and Lint > Format Project (ruff) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Format and Lint > Lint Project (ruff check) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (project) > Format and Lint > Lint Project (ruff check) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Lint Project (ruff check) | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > Format and Lint > Lint Project (ruff check) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Freeze to requirements.txt | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Freeze to requirements.txt | python-tk/vscode | ok |  | 0.62 |  |
| Solution Explorer > (project) > Freeze to requirements.txt | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > Freeze to requirements.txt | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > List Devices | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > List Installed Packages | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (project) > List Installed Packages | python-tk/vscode | ok |  | 0.62 |  |
| Solution Explorer > (project) > List Installed Packages | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > List Installed Packages | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Manage Packages | python-tk/vs | ok | Manage Packages - EvDemo [PackagesDialog] | 0.87 |  |
| Solution Explorer > (project) > Manage Packages | python-tk/vscode | ok | Manage Packages - EvDemo [PackagesDialog] | 0.82 |  |
| Solution Explorer > (project) > Manage Packages | python-tk/agent | ok | Manage Packages - EvDemo [PackagesDialog] | 0.77 |  |
| Solution Explorer > (project) > Manage Packages | vb6/vs | ok | Manage Packages [QMessageBox] | 0.76 |  |
| Solution Explorer > (project) > Manage Packages | csharp/vs | ok |  | 0.66 |  |
| Solution Explorer > (project) > Manage Packages | flask/vs | ok | Manage Packages - Flask_Todo [PackagesDialog] | 0.8 |  |
| Solution Explorer > (project) > Manage Packages | flutter/vs | ok | Manage Packages - IdeProj [PackagesDialog] | 0.96 |  |
| Solution Explorer > (project) > Manage Packages | retro/vs | ok | Manage Packages [QMessageBox] | 0.77 |  |
| Solution Explorer > (project) > Manage Packages | dos/vs | ok | Manage Packages [QMessageBox] | 0.83 |  |
| Solution Explorer > (project) > Manage Packages | game/vs | ok | Manage Packages - Platformer [PackagesDialog] | 0.72 |  |
| Solution Explorer > (project) > Manage Packages | asm/vs | ok | Manage Packages [QMessageBox] | 0.73 |  |
| Solution Explorer > (project) > Manage Packages | firmware/vs | ok | Manage Packages [QMessageBox] | 0.81 |  |
| Solution Explorer > (project) > New Blueprint | flask/vs | ok |  | 0.68 |  |
| Solution Explorer > (project) > New Screen (Form) | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.83 |  |
| Solution Explorer > (project) > New Widget | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Open Firmware & ECU Workbench | firmware/vs | ok |  | 0.67 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | python-tk/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | python-tk/agent | ok |  | 0.6 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | vb6/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | csharp/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | web/vs | ok |  | 0.6 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | flask/vs | ok |  | 0.6 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | asm/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open Folder in File Explorer | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open in Browser | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Open in Browser | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Packages > Add Package (pub add) | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Packages > pub get | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Packages > pub outdated | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Packages > pub upgrade | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.77 |  |
| Solution Explorer > (project) > Properties | python-tk/vs | ok | EvDemo Properties [QDialog] | 1.36 |  |
| Solution Explorer > (project) > Properties | python-tk/vscode | ok | EvDemo Properties [QDialog] | 0.85 |  |
| Solution Explorer > (project) > Properties | python-tk/agent | ok | EvDemo Properties [QDialog] | 0.97 |  |
| Solution Explorer > (project) > Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.77 |  |
| Solution Explorer > (project) > Properties | csharp/vs | ok | HelloCSharp Properties [QDialog] | 0.74 |  |
| Solution Explorer > (project) > Properties | flutter/vs | ok | IdeProj Properties [QDialog] | 0.82 |  |
| Solution Explorer > (project) > Properties | retro/vs | ok | NesStarCatcher Properties [QDialog] | 0.75 |  |
| Solution Explorer > (project) > Properties | dos/vs | ok | Contacts Properties [QDialog] | 0.79 |  |
| Solution Explorer > (project) > Properties | game/vs | ok | Platformer Properties [QDialog] | 0.75 |  |
| Solution Explorer > (project) > Properties | asm/vs | ok | CoreNasmForms Properties [QDialog] | 0.76 |  |
| Solution Explorer > (project) > Properties | firmware/vs | ok | CrawlEcu Properties [QDialog] | 0.85 |  |
| Solution Explorer > (project) > Python > Build EXE / Installer | flask/vs | ok | Publish Flask_Todo [PublishDialog] | 0.84 |  |
| Solution Explorer > (project) > Python > Create .venv | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Python > Format and Lint > Fix Lint Problems (ruff check --fix) | flask/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Python > Format and Lint > Format Project (black) | flask/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Python > Format and Lint > Format Project (ruff) | flask/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Python > Format and Lint > Lint Project (ruff check) | flask/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Python > Freeze to requirements.txt | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Python > List Installed Packages | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Python > Run Tests (pytest) | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Refresh | web/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Refresh | flask/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Remove from Solution | python-tk/vs | ok | إزالة المشروع [QMessageBox] | 1.21 |  |
| Solution Explorer > (project) > Remove from Solution | python-tk/vscode | ok | Remove Project [QMessageBox] | 0.84 |  |
| Solution Explorer > (project) > Remove from Solution | python-tk/agent | ok | Remove Project [QMessageBox] | 0.84 |  |
| Solution Explorer > (project) > Remove from Solution | vb6/vs | ok | Remove Project [QMessageBox] | 0.75 |  |
| Solution Explorer > (project) > Remove from Solution | csharp/vs | ok | Remove Project [QMessageBox] | 0.77 |  |
| Solution Explorer > (project) > Remove from Solution | web/vs | ok | Remove Project [QMessageBox] | 0.73 |  |
| Solution Explorer > (project) > Remove from Solution | flask/vs | ok | Remove Project [QMessageBox] | 0.75 |  |
| Solution Explorer > (project) > Remove from Solution | flutter/vs | ok | Remove Project [QMessageBox] | 0.8 |  |
| Solution Explorer > (project) > Remove from Solution | retro/vs | ok | Remove Project [QMessageBox] | 0.77 |  |
| Solution Explorer > (project) > Remove from Solution | dos/vs | ok | Remove Project [QMessageBox] | 0.79 |  |
| Solution Explorer > (project) > Remove from Solution | game/vs | ok | Remove Project [QMessageBox] | 0.75 |  |
| Solution Explorer > (project) > Remove from Solution | asm/vs | ok | Remove Project [QMessageBox] | 0.74 |  |
| Solution Explorer > (project) > Remove from Solution | firmware/vs | ok | Remove Project [QMessageBox] | 0.84 |  |
| Solution Explorer > (project) > Routes | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Run (F5) | vb6/vs | ok |  | 0.64 |  |
| Solution Explorer > (project) > Run (flutter run) | flutter/vs | ok |  | 0.81 |  |
| Solution Explorer > (project) > Run Game | game/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Run Server | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Run Tests (flutter test) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Run Tests (pytest) | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (project) > Run Tests (pytest) | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (project) > Run Tests (pytest) | python-tk/agent | ok |  | 0.62 |  |
| Solution Explorer > (project) > Run Tests (pytest) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Run Tests (unittest) | python-tk/vs | ok |  | 0.62 |  |
| Solution Explorer > (project) > Run Tests (unittest) | python-tk/vscode | ok |  | 0.62 |  |
| Solution Explorer > (project) > Run Tests (unittest) | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (project) > Run Tests (unittest) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Run flask Command | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Site Settings | web/vs | ok | Site Settings - Boot Site [QDialog] | 0.78 |  |
| Solution Explorer > (project) > Site Settings | flask/vs | ok | Site Settings - Flask_Todo [QDialog] | 0.81 |  |
| Solution Explorer > (project) > Start Debugging / Continue | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > Start Debugging / Continue | flask/vs | ok |  | 0.87 |  |
| Solution Explorer > (project) > View in Preview | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (project) > View in Preview | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Add Reference | python-tk/vs | ok | Reference Manager - EvDemo [AddReferenceDialog] | 1.37 |  |
| Solution Explorer > (references) > Add Reference | python-tk/vscode | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.89 |  |
| Solution Explorer > (references) > Add Reference | python-tk/agent | ok | Reference Manager - EvDemo [AddReferenceDialog] | 0.88 |  |
| Solution Explorer > (references) > Add Reference | vb6/vs | ok | Reference Manager - Greeter [AddReferenceDialog] | 0.83 |  |
| Solution Explorer > (references) > Add Reference | csharp/vs | ok | Reference Manager - HelloCSharp [AddReferenceDialog] | 0.76 |  |
| Solution Explorer > (references) > Add Reference | flutter/vs | ok | Reference Manager - IdeProj [AddReferenceDialog] | 0.83 |  |
| Solution Explorer > (references) > Add Reference | retro/vs | ok | Reference Manager - NesStarCatcher [AddReferenceDialog] | 0.76 |  |
| Solution Explorer > (references) > Add Reference | dos/vs | ok | Reference Manager - Contacts [AddReferenceDialog] | 0.84 |  |
| Solution Explorer > (references) > Add Reference | game/vs | ok | Reference Manager - Platformer [AddReferenceDialog] | 0.8 |  |
| Solution Explorer > (references) > Add Reference | asm/vs | ok | Reference Manager - CoreNasmForms [AddReferenceDialog] | 0.76 |  |
| Solution Explorer > (references) > Add Reference | firmware/vs | ok | Reference Manager - CrawlEcu [AddReferenceDialog] | 0.85 |  |
| Solution Explorer > (references) > Refresh References | python-tk/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | python-tk/agent | ok |  | 0.62 |  |
| Solution Explorer > (references) > Refresh References | vb6/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | csharp/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | asm/vs | ok |  | 0.61 |  |
| Solution Explorer > (references) > Refresh References | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Add Form | vb6/vs | ok | Add Windows Form [AddItemDialog] | 0.77 |  |
| Solution Explorer > (resources) > Analyze (flutter analyze) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Build > Build APK (Android) | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Build > Build Web | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Build > Build Windows | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.91 |  |
| Solution Explorer > (resources) > Build EXE / Installer | python-tk/vs | ok | Publish EvDemo [PublishDialog] | 1.42 |  |
| Solution Explorer > (resources) > Build EXE / Installer | python-tk/vscode | ok | Publish EvDemo [PublishDialog] | 1.0 |  |
| Solution Explorer > (resources) > Build EXE / Installer | python-tk/agent | ok | Publish EvDemo [PublishDialog] | 1.2 |  |
| Solution Explorer > (resources) > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.85 |  |
| Solution Explorer > (resources) > Build One-File EXE (PyInstaller) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Clean (flutter clean) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Create .venv | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Create .venv | python-tk/vscode | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Create .venv | python-tk/agent | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Create .venv | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Export to Godot | game/vs | ok |  | 6.71 |  |
| Solution Explorer > (resources) > Flutter Doctor | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Format Code (dart format) | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (resources) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Format and Lint > Fix Lint Problems (ruff check --fix) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Format and Lint > Fix Lint Problems (ruff check --fix) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (black) | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (black) | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (black) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (black) | game/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (ruff) | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (ruff) | python-tk/vscode | ok |  | 0.65 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (ruff) | python-tk/agent | ok |  | 0.68 |  |
| Solution Explorer > (resources) > Format and Lint > Format Project (ruff) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Format and Lint > Lint Project (ruff check) | python-tk/vs | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Format and Lint > Lint Project (ruff check) | python-tk/vscode | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Format and Lint > Lint Project (ruff check) | python-tk/agent | ok |  | 0.68 |  |
| Solution Explorer > (resources) > Format and Lint > Lint Project (ruff check) | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Freeze to requirements.txt | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Freeze to requirements.txt | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Freeze to requirements.txt | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Freeze to requirements.txt | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > List Devices | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > List Installed Packages | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > List Installed Packages | python-tk/vscode | ok |  | 0.62 |  |
| Solution Explorer > (resources) > List Installed Packages | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (resources) > List Installed Packages | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > New Screen (Form) | flutter/vs | ok | Add Windows Form [AddItemDialog] | 0.82 |  |
| Solution Explorer > (resources) > New Widget | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Packages > Add Package (pub add) | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Packages > pub get | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Packages > pub outdated | flutter/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Packages > pub upgrade | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Project Properties | vb6/vs | ok | Greeter Properties [QDialog] | 0.8 |  |
| Solution Explorer > (resources) > Run (F5) | vb6/vs | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Run (flutter run) | flutter/vs | ok |  | 0.98 |  |
| Solution Explorer > (resources) > Run Game | game/vs | ok |  | 0.67 |  |
| Solution Explorer > (resources) > Run Tests (flutter test) | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Run Tests (pytest) | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Run Tests (pytest) | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Run Tests (pytest) | python-tk/agent | ok |  | 0.62 |  |
| Solution Explorer > (resources) > Run Tests (pytest) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Run Tests (unittest) | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (resources) > Run Tests (unittest) | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (resources) > Run Tests (unittest) | python-tk/agent | ok |  | 0.64 |  |
| Solution Explorer > (resources) > Run Tests (unittest) | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Add > Existing Project | python-tk/vs | ok | إضافة مشروع موجود [QFileDialog] | 1.44 |  |
| Solution Explorer > (solution) > Add > Existing Project | python-tk/vscode | ok | Add Existing Project [QFileDialog] | 1.12 |  |
| Solution Explorer > (solution) > Add > Existing Project | python-tk/agent | ok | Add Existing Project [QFileDialog] | 0.95 |  |
| Solution Explorer > (solution) > Add > Existing Project | vb6/vs | ok | Add Existing Project [QFileDialog] | 0.93 |  |
| Solution Explorer > (solution) > Add > Existing Project | csharp/vs | ok | Add Existing Project [QFileDialog] | 0.82 |  |
| Solution Explorer > (solution) > Add > Existing Project | web/vs | ok | Add Existing Project [QFileDialog] | 0.86 |  |
| Solution Explorer > (solution) > Add > Existing Project | flask/vs | ok | Add Existing Project [QFileDialog] | 0.82 |  |
| Solution Explorer > (solution) > Add > Existing Project | flutter/vs | ok | Add Existing Project [QFileDialog] | 0.95 |  |
| Solution Explorer > (solution) > Add > Existing Project | retro/vs | ok | Add Existing Project [QFileDialog] | 0.86 |  |
| Solution Explorer > (solution) > Add > Existing Project | dos/vs | ok | Add Existing Project [QFileDialog] | 0.92 |  |
| Solution Explorer > (solution) > Add > Existing Project | game/vs | ok | Add Existing Project [QFileDialog] | 0.99 |  |
| Solution Explorer > (solution) > Add > Existing Project | asm/vs | ok | Add Existing Project [QFileDialog] | 0.81 |  |
| Solution Explorer > (solution) > Add > Existing Project | firmware/vs | ok | Add Existing Project [QFileDialog] | 0.92 |  |
| Solution Explorer > (solution) > Add > New Project | python-tk/vs | ok | New Project [NewProjectDialog] | 2.07 |  |
| Solution Explorer > (solution) > Add > New Project | python-tk/vscode | ok | New Project [NewProjectDialog] | 2.01 |  |
| Solution Explorer > (solution) > Add > New Project | python-tk/agent | ok | New Project [NewProjectDialog] | 1.98 |  |
| Solution Explorer > (solution) > Add > New Project | vb6/vs | ok | New Project [NewProjectDialog] | 1.78 |  |
| Solution Explorer > (solution) > Add > New Project | csharp/vs | ok | New Project [NewProjectDialog] | 1.46 |  |
| Solution Explorer > (solution) > Add > New Project | web/vs | ok | New Project [NewProjectDialog] | 1.95 |  |
| Solution Explorer > (solution) > Add > New Project | flask/vs | ok | New Project [NewProjectDialog] | 1.4 |  |
| Solution Explorer > (solution) > Add > New Project | flutter/vs | ok | New Project [NewProjectDialog] | 1.84 |  |
| Solution Explorer > (solution) > Add > New Project | retro/vs | ok | New Project [NewProjectDialog] | 1.62 |  |
| Solution Explorer > (solution) > Add > New Project | dos/vs | ok | New Project [NewProjectDialog] | 1.85 |  |
| Solution Explorer > (solution) > Add > New Project | game/vs | ok | New Project [NewProjectDialog] | 1.57 |  |
| Solution Explorer > (solution) > Add > New Project | asm/vs | ok | New Project [NewProjectDialog] | 1.5 |  |
| Solution Explorer > (solution) > Add > New Project | firmware/vs | ok | New Project [NewProjectDialog] | 1.6 |  |
| Solution Explorer > (solution) > Build Solution | python-tk/vs | ok |  | 0.65 |  |
| Solution Explorer > (solution) > Build Solution | python-tk/vscode | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Build Solution | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Build Solution | vb6/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Build Solution | csharp/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Build Solution | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Build Solution | flask/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Build Solution | flutter/vs | ok |  | 0.72 |  |
| Solution Explorer > (solution) > Build Solution | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Build Solution | dos/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Build Solution | game/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Build Solution | asm/vs | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Build Solution | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | python-tk/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | python-tk/vscode | ok |  | 0.6 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | python-tk/agent | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | vb6/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | csharp/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | dos/vs | ok |  | 0.6 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | asm/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Open Folder in File Explorer | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Properties | python-tk/vs | ok | Solution 'EvDemo' Properties [QDialog] | 1.23 |  |
| Solution Explorer > (solution) > Properties | python-tk/vscode | ok | Solution 'EvDemo' Properties [QDialog] | 0.92 |  |
| Solution Explorer > (solution) > Properties | python-tk/agent | ok | Solution 'EvDemo' Properties [QDialog] | 0.89 |  |
| Solution Explorer > (solution) > Properties | vb6/vs | ok | Solution 'Greeter' Properties [QDialog] | 0.84 |  |
| Solution Explorer > (solution) > Properties | csharp/vs | ok | Solution 'HelloCSharp' Properties [QDialog] | 0.78 |  |
| Solution Explorer > (solution) > Properties | web/vs | ok | Solution 'Boot Site' Properties [QDialog] | 0.76 |  |
| Solution Explorer > (solution) > Properties | flask/vs | ok | Solution 'Flask_Todo' Properties [QDialog] | 0.81 |  |
| Solution Explorer > (solution) > Properties | flutter/vs | ok | Solution 'IdeProj' Properties [QDialog] | 0.87 |  |
| Solution Explorer > (solution) > Properties | retro/vs | ok | Solution 'NesStarCatcher' Properties [QDialog] | 0.84 |  |
| Solution Explorer > (solution) > Properties | dos/vs | ok | Solution 'Contacts' Properties [QDialog] | 0.87 |  |
| Solution Explorer > (solution) > Properties | game/vs | ok | Solution 'Platformer' Properties [QDialog] | 0.85 |  |
| Solution Explorer > (solution) > Properties | asm/vs | ok | Solution 'CoreNasmForms' Properties [QDialog] | 0.74 |  |
| Solution Explorer > (solution) > Properties | firmware/vs | ok | Solution 'CrawlEcu' Properties [QDialog] | 0.85 |  |
| Solution Explorer > (solution) > Refresh References | python-tk/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Refresh References | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | python-tk/agent | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | vb6/vs | ok |  | 0.6 |  |
| Solution Explorer > (solution) > Refresh References | csharp/vs | ok |  | 0.6 |  |
| Solution Explorer > (solution) > Refresh References | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | flutter/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Refresh References | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | asm/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Refresh References | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Save All | python-tk/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Save All | python-tk/vscode | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Save All | python-tk/agent | ok |  | 0.65 |  |
| Solution Explorer > (solution) > Save All | vb6/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Save All | csharp/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Save All | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Save All | flask/vs | ok |  | 0.6 |  |
| Solution Explorer > (solution) > Save All | flutter/vs | ok |  | 0.72 |  |
| Solution Explorer > (solution) > Save All | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Save All | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Save All | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Save All | asm/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Save All | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > Boot Site | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > Contacts | dos/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > CoreNasmForms | asm/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > CrawlEcu | firmware/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > EvDemo | python-tk/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > EvDemo | python-tk/vscode | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > EvDemo | python-tk/agent | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > Flask_Todo | flask/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Set StartUp Project > Greeter | vb6/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > HelloCSharp | csharp/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > IdeProj | flutter/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > NesStarCatcher | retro/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Set StartUp Project > Platformer | game/vs | ok |  | 0.61 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | python-tk/vs | ok |  | 0.76 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | python-tk/vscode | ok |  | 0.88 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | python-tk/agent | ok |  | 0.85 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | vb6/vs | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | csharp/vs | ok |  | 0.65 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | web/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | flask/vs | ok |  | 0.85 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | flutter/vs | ok |  | 0.87 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | retro/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | dos/vs | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | game/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | asm/vs | ok |  | 0.67 |  |
| Solution Explorer > (solution) > Start Debugging / Continue | firmware/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Without Debugging | python-tk/vs | ok |  | 0.68 |  |
| Solution Explorer > (solution) > Start Without Debugging | python-tk/vscode | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Start Without Debugging | python-tk/agent | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Start Without Debugging | vb6/vs | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Start Without Debugging | csharp/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Start Without Debugging | web/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Without Debugging | flask/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Without Debugging | flutter/vs | ok |  | 0.87 |  |
| Solution Explorer > (solution) > Start Without Debugging | retro/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Without Debugging | dos/vs | ok |  | 0.62 |  |
| Solution Explorer > (solution) > Start Without Debugging | game/vs | ok |  | 0.63 |  |
| Solution Explorer > (solution) > Start Without Debugging | asm/vs | ok |  | 0.64 |  |
| Solution Explorer > (solution) > Start Without Debugging | firmware/vs | ok |  | 0.62 |  |
| Solution Explorer > (webfile) > Copy Full Path | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Copy Full Path | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Copy URL | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Copy URL | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Delete | web/vs | ok | Delete [QMessageBox] | 0.73 |  |
| Solution Explorer > (webfile) > Delete | flask/vs | ok | Delete [QMessageBox] | 0.87 |  |
| Solution Explorer > (webfile) > Open | web/vs | ok |  | 0.66 |  |
| Solution Explorer > (webfile) > Open | flask/vs | ok |  | 0.74 |  |
| Solution Explorer > (webfile) > Open Containing Folder | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Open Containing Folder | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Open With > Firmware & ECU Workbench | web/vs | ok |  | 0.95 |  |
| Solution Explorer > (webfile) > Open With > Firmware & ECU Workbench | flask/vs | ok |  | 1.34 |  |
| Solution Explorer > (webfile) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Open With > Firmware & ECU Workbench (EEPROM, read-only) | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Open in Browser | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Open in Browser | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > Rename | web/vs | ok | Rename [QInputDialog] | 0.75 |  |
| Solution Explorer > (webfile) > Rename | flask/vs | ok | Rename [QInputDialog] | 0.85 |  |
| Solution Explorer > (webfile) > View in Preview | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfile) > View in Preview | flask/vs | ok |  | 0.62 |  |
| Solution Explorer > (webfolder) > Add > Existing Files | web/vs | ok | Add Existing Files [QFileDialog] | 0.88 |  |
| Solution Explorer > (webfolder) > Add > Existing Files | flask/vs | ok | Add Existing Files [QFileDialog] | 1.24 |  |
| Solution Explorer > (webfolder) > Add > New File | web/vs | ok | New File [NewFileDialog] | 0.76 |  |
| Solution Explorer > (webfolder) > Add > New File | flask/vs | ok | New File [NewFileDialog] | 1.05 |  |
| Solution Explorer > (webfolder) > Add > New Folder | web/vs | ok | New Folder [QInputDialog] | 0.72 |  |
| Solution Explorer > (webfolder) > Add > New Folder | flask/vs | ok | New Folder [QInputDialog] | 0.92 |  |
| Solution Explorer > (webfolder) > Delete | web/vs | ok | Delete [QMessageBox] | 0.76 |  |
| Solution Explorer > (webfolder) > Delete | flask/vs | ok | Delete [QMessageBox] | 0.85 |  |
| Solution Explorer > (webfolder) > New Blueprint | flask/vs | ok |  | 0.85 |  |
| Solution Explorer > (webfolder) > Open Folder in File Explorer | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfolder) > Open Folder in File Explorer | flask/vs | ok |  | 0.63 |  |
| Solution Explorer > (webfolder) > Open in Browser | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfolder) > Open in Browser | flask/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfolder) > Rename | web/vs | ok | Rename [QInputDialog] | 0.72 |  |
| Solution Explorer > (webfolder) > Rename | flask/vs | ok | Rename [QInputDialog] | 0.9 |  |
| Solution Explorer > (webfolder) > View in Preview | web/vs | ok |  | 0.61 |  |
| Solution Explorer > (webfolder) > View in Preview | flask/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | python-tk/vs | ok |  | 0.66 |  |
| Test > Clear Coverage Results | none/vs | ok |  | 0.63 |  |
| Test > Clear Coverage Results | python-tk/vscode | ok |  | 0.62 |  |
| Test > Clear Coverage Results | python-tk/agent | ok |  | 0.63 |  |
| Test > Clear Coverage Results | vb6/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | csharp/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | web/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | flask/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | flutter/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | retro/vs | ok |  | 0.63 |  |
| Test > Clear Coverage Results | dos/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | game/vs | ok |  | 0.63 |  |
| Test > Clear Coverage Results | asm/vs | ok |  | 0.62 |  |
| Test > Clear Coverage Results | firmware/vs | ok |  | 0.63 |  |
| Test > Debug Selected Test | python-tk/vs | ok |  | 0.71 |  |
| Test > Debug Selected Test | none/vs | ok |  | 0.6 |  |
| Test > Debug Selected Test | python-tk/vscode | ok |  | 0.61 |  |
| Test > Debug Selected Test | python-tk/agent | ok |  | 0.61 |  |
| Test > Debug Selected Test | vb6/vs | ok |  | 0.6 |  |
| Test > Debug Selected Test | csharp/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | web/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | flask/vs | ok |  | 0.6 |  |
| Test > Debug Selected Test | flutter/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | retro/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | dos/vs | ok |  | 0.62 |  |
| Test > Debug Selected Test | game/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | asm/vs | ok |  | 0.61 |  |
| Test > Debug Selected Test | firmware/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | python-tk/vs | ok |  | 0.63 |  |
| Test > Refresh Tests | none/vs | ok |  | 0.6 |  |
| Test > Refresh Tests | python-tk/vscode | ok |  | 0.61 |  |
| Test > Refresh Tests | python-tk/agent | ok |  | 0.61 |  |
| Test > Refresh Tests | vb6/vs | ok |  | 0.6 |  |
| Test > Refresh Tests | csharp/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | web/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | flask/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | flutter/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | retro/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | dos/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | game/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | asm/vs | ok |  | 0.61 |  |
| Test > Refresh Tests | firmware/vs | ok |  | 0.61 |  |
| Test > Run All Tests | python-tk/vs | ok |  | 0.69 |  |
| Test > Run All Tests | none/vs | ok |  | 0.61 |  |
| Test > Run All Tests | python-tk/vscode | ok |  | 0.65 |  |
| Test > Run All Tests | python-tk/agent | ok |  | 0.65 |  |
| Test > Run All Tests | vb6/vs | ok |  | 0.65 |  |
| Test > Run All Tests | csharp/vs | ok |  | 0.64 |  |
| Test > Run All Tests | web/vs | ok |  | 0.63 |  |
| Test > Run All Tests | flask/vs | ok |  | 0.62 |  |
| Test > Run All Tests | flutter/vs | ok |  | 0.77 |  |
| Test > Run All Tests | retro/vs | ok |  | 0.62 |  |
| Test > Run All Tests | dos/vs | ok |  | 0.66 |  |
| Test > Run All Tests | game/vs | ok |  | 0.61 |  |
| Test > Run All Tests | asm/vs | ok |  | 0.65 |  |
| Test > Run All Tests | firmware/vs | ok |  | 0.63 |  |
| Test > Run All Tests with Coverage | python-tk/vs | ok |  | 0.65 |  |
| Test > Run All Tests with Coverage | none/vs | ok |  | 0.6 |  |
| Test > Run All Tests with Coverage | python-tk/vscode | ok |  | 0.65 |  |
| Test > Run All Tests with Coverage | python-tk/agent | ok |  | 0.63 |  |
| Test > Run All Tests with Coverage | vb6/vs | ok |  | 0.63 |  |
| Test > Run All Tests with Coverage | csharp/vs | ok |  | 0.62 |  |
| Test > Run All Tests with Coverage | web/vs | ok |  | 0.61 |  |
| Test > Run All Tests with Coverage | flask/vs | ok |  | 0.62 |  |
| Test > Run All Tests with Coverage | flutter/vs | ok |  | 0.78 |  |
| Test > Run All Tests with Coverage | retro/vs | ok |  | 0.61 |  |
| Test > Run All Tests with Coverage | dos/vs | ok |  | 0.65 |  |
| Test > Run All Tests with Coverage | game/vs | ok |  | 0.61 |  |
| Test > Run All Tests with Coverage | asm/vs | ok |  | 0.63 |  |
| Test > Run All Tests with Coverage | firmware/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | python-tk/vs | ok |  | 0.67 |  |
| Test > Run Failed Tests | none/vs | ok |  | 0.6 |  |
| Test > Run Failed Tests | python-tk/vscode | ok |  | 0.61 |  |
| Test > Run Failed Tests | python-tk/agent | ok |  | 0.6 |  |
| Test > Run Failed Tests | vb6/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | csharp/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | web/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | flask/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | flutter/vs | ok |  | 0.6 |  |
| Test > Run Failed Tests | retro/vs | ok |  | 0.6 |  |
| Test > Run Failed Tests | dos/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | game/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | asm/vs | ok |  | 0.61 |  |
| Test > Run Failed Tests | firmware/vs | ok |  | 0.6 |  |
| Test > Run Tests in Current File | python-tk/vs | ok |  | 0.67 |  |
| Test > Run Tests in Current File | none/vs | ok |  | 0.61 |  |
| Test > Run Tests in Current File | python-tk/vscode | ok |  | 0.63 |  |
| Test > Run Tests in Current File | python-tk/agent | ok |  | 0.64 |  |
| Test > Run Tests in Current File | vb6/vs | ok |  | 0.62 |  |
| Test > Run Tests in Current File | csharp/vs | ok |  | 0.62 |  |
| Test > Run Tests in Current File | web/vs | ok |  | 0.61 |  |
| Test > Run Tests in Current File | flask/vs | ok |  | 0.61 |  |
| Test > Run Tests in Current File | flutter/vs | ok |  | 0.61 |  |
| Test > Run Tests in Current File | retro/vs | ok |  | 0.62 |  |
| Test > Run Tests in Current File | dos/vs | ok |  | 0.65 |  |
| Test > Run Tests in Current File | game/vs | ok |  | 0.61 |  |
| Test > Run Tests in Current File | asm/vs | ok |  | 0.64 |  |
| Test > Run Tests in Current File | firmware/vs | ok |  | 0.61 |  |
| Test > Show Code Coverage Colouring | python-tk/vs | ok |  | 0.68 |  |
| Test > Show Code Coverage Colouring | none/vs | ok |  | 0.66 |  |
| Test > Show Code Coverage Colouring | python-tk/vscode | ok |  | 0.64 |  |
| Test > Show Code Coverage Colouring | python-tk/agent | ok |  | 0.65 |  |
| Test > Show Code Coverage Colouring | vb6/vs | ok |  | 0.64 |  |
| Test > Show Code Coverage Colouring | csharp/vs | ok |  | 0.64 |  |
| Test > Show Code Coverage Colouring | web/vs | ok |  | 0.64 |  |
| Test > Show Code Coverage Colouring | flask/vs | ok |  | 0.63 |  |
| Test > Show Code Coverage Colouring | flutter/vs | ok |  | 0.65 |  |
| Test > Show Code Coverage Colouring | retro/vs | ok |  | 0.63 |  |
| Test > Show Code Coverage Colouring | dos/vs | ok |  | 0.65 |  |
| Test > Show Code Coverage Colouring | game/vs | ok |  | 0.65 |  |
| Test > Show Code Coverage Colouring | asm/vs | ok |  | 0.64 |  |
| Test > Show Code Coverage Colouring | firmware/vs | ok |  | 0.64 |  |
| Test > Test Explorer | python-tk/vs | ok |  | 0.64 |  |
| Test > Test Explorer | none/vs | ok |  | 0.64 |  |
| Test > Test Explorer | python-tk/vscode | ok |  | 2.56 |  |
| Test > Test Explorer | python-tk/agent | ok |  | 0.86 |  |
| Test > Test Explorer | vb6/vs | ok |  | 0.64 |  |
| Test > Test Explorer | csharp/vs | ok |  | 0.64 |  |
| Test > Test Explorer | web/vs | ok |  | 0.62 |  |
| Test > Test Explorer | flask/vs | ok |  | 0.62 |  |
| Test > Test Explorer | flutter/vs | ok |  | 0.63 |  |
| Test > Test Explorer | retro/vs | ok |  | 0.63 |  |
| Test > Test Explorer | dos/vs | ok |  | 0.69 |  |
| Test > Test Explorer | game/vs | ok |  | 0.62 |  |
| Test > Test Explorer | asm/vs | ok |  | 0.62 |  |
| Test > Test Explorer | firmware/vs | ok |  | 0.63 |  |
| Toolbar Activity Bar > AI Chat | python-tk/vscode | ok |  | 1.5 |  |
| Toolbar Activity Bar > AI Web Chats | python-tk/vscode | ok |  | 1.66 |  |
| Toolbar Activity Bar > Agents | python-tk/vscode | ok |  | 1.52 |  |
| Toolbar Activity Bar > Claude Code | python-tk/vscode | ok |  | 2.24 |  |
| Toolbar Activity Bar > Databases | python-tk/vscode | ok |  | 1.57 |  |
| Toolbar Activity Bar > Editor | python-tk/agent | ok |  | 1.23 |  |
| Toolbar Activity Bar > Explorer | python-tk/vscode | ok |  | 1.91 |  |
| Toolbar Activity Bar > Extensions | python-tk/vscode | ok |  | 1.62 |  |
| Toolbar Activity Bar > Manage | python-tk/vscode | ok |  | 0.62 |  |
| Toolbar Activity Bar > Packages | python-tk/vscode | ok | Manage Packages - EvDemo [PackagesDialog] | 0.85 |  |
| Toolbar Activity Bar > Remote Explorer | python-tk/vscode | ok |  | 1.59 |  |
| Toolbar Activity Bar > Ring Samples | python-tk/vscode | ok |  | 1.01 |  |
| Toolbar Activity Bar > Run and Debug | python-tk/vscode | ok |  | 1.61 |  |
| Toolbar Activity Bar > Search | python-tk/vscode | ok |  | 1.69 |  |
| Toolbar Activity Bar > Source Control | python-tk/vscode | ok |  | 1.62 |  |
| Toolbar Activity Bar > Testing | python-tk/vscode | ok |  | 1.39 |  |
| Toolbar Activity Bar > Tutorials | python-tk/vscode | ok |  | 1.02 |  |
| Toolbar Expo > Refresh devices | python-tk/vs | ok |  | 1.08 |  |
| Toolbar Firmware > Analyze | firmware/vs | ok |  | 0.7 |  |
| Toolbar Firmware > Build | firmware/vs | ok |  | 0.63 |  |
| Toolbar Firmware > Compare | firmware/vs | ok |  | 0.61 |  |
| Toolbar Firmware > Find Maps | firmware/vs | ok |  | 3.79 |  |
| Toolbar Firmware > Map from Selection | firmware/vs | ok | New Map [QInputDialog] | 0.84 |  |
| Toolbar Firmware > More > Calibration Map Editor (full) | firmware/vs | ok |  | 0.86 |  |
| Toolbar Firmware > More > Correct Checksums | firmware/vs | ok |  | 0.62 |  |
| Toolbar Firmware > More > Detailed Firmware Analysis | firmware/vs | ok |  | 1.1 |  |
| Toolbar Firmware > More > Import A2L | firmware/vs | ok | Import A2L [QFileDialog] | 0.96 |  |
| Toolbar Firmware > More > Load Checksum Profile | firmware/vs | ok | Load Checksum Profile [QFileDialog] | 1.05 |  |
| Toolbar Firmware > More > Open Original (read-only hex editor) | firmware/vs | ok |  | 0.66 |  |
| Toolbar Firmware > More > Open in Ghidra | firmware/vs | ok |  | 0.62 |  |
| Toolbar Firmware > More > Save Working Copy As (binary) | firmware/vs | ok | Save Working Copy As (binary) [QFileDialog] | 0.97 |  |
| Toolbar Firmware > Save Version | firmware/vs | ok | Save Version [QInputDialog] | 0.82 |  |
| Toolbar Firmware > Verify Checksums | firmware/vs | ok |  | 0.61 |  |
| Toolbar Mobile > Refresh devices | python-tk/vs | ok |  | 0.68 |  |
| Toolbar Project Actions > Build EXE (Publish) | vb6/vs | ok | Publish Greeter [PublishDialog] | 0.91 |  |
| Toolbar Project Actions > Routes | flask/vs | ok |  | 0.62 |  |
| Toolbar Project Actions > Run Game | game/vs | ok |  | 0.64 |  |
| Toolbar Project Actions > Run Server | flask/vs | ok |  | 0.62 |  |
| Toolbar Project Actions > Run Tests (pytest) | python-tk/vs | ok |  | 0.65 |  |
| Toolbar Project Actions > pub get | flutter/vs | ok |  | 0.63 |  |
| Toolbar Rust > Clippy | python-tk/vs | ok |  | 0.62 |  |
| Toolbar Rust > Reload | python-tk/vs | ok |  | 0.63 |  |
| Toolbar Rust > Test | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Standard > New Project | python-tk/vs | ok | New Project [NewProjectDialog] | 1.94 |  |
| Toolbar Standard > Open Project | python-tk/vs | ok | فتح مشروع/حل [QFileDialog] | 1.46 |  |
| Toolbar Standard > Save All | python-tk/vs | ok |  | 0.9 |  |
| Toolbar Standard > Start Debugging / Continue | python-tk/vs | ok |  | 0.71 |  |
| Toolbar Toolbar > Back | python-tk/vs | ok |  | 0.64 |  |
| Toolbar Toolbar > Bookmark | firmware/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Clear | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Coverage | python-tk/vs | ok |  | 0.68 |  |
| Toolbar Toolbar > Debug | python-tk/vs | ok |  | 0.62 |  |
| Toolbar Toolbar > Diagram | python-tk/vs | ok | قواعد البيانات [QMessageBox] | 1.24 |  |
| Toolbar Toolbar > Erase | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Fill | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Find | firmware/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Fit | game/vs | ok |  | 0.6 |  |
| Toolbar Toolbar > Forward | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Front | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Go To | firmware/vs | ok | Go To Offset [GotoDialog] | 0.83 |  |
| Toolbar Toolbar > Local Servers > Copy MariaDB/MySQL Password | python-tk/vs | ok |  | 0.62 |  |
| Toolbar Toolbar > Local Servers > Copy PostgreSQL Password | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Local Servers > Server Status | python-tk/vs | ok | خوادم قواعد البيانات المحلية [QMessageBox] | 1.71 |  |
| Toolbar Toolbar > Local Servers > Stop local MariaDB/MySQL | python-tk/vs | ok |  | 1.02 |  |
| Toolbar Toolbar > Local Servers > Stop local PostgreSQL | python-tk/vs | ok |  | 0.73 |  |
| Toolbar Toolbar > New > Add Connection (SQLite / MySQL / PostgreSQL) | python-tk/vs | ok | Database Connection [ConnectionDialog] | 1.87 |  |
| Toolbar Toolbar > New > New SQLite Database | python-tk/vs | ok | قاعدة بيانات SQLite جديدة [QFileDialog] | 1.42 |  |
| Toolbar Toolbar > New Query | python-tk/vs | ok | قواعد البيانات [QMessageBox] | 1.19 |  |
| Toolbar Toolbar > New Table | python-tk/vs | ok | قواعد البيانات [QMessageBox] | 1.15 |  |
| Toolbar Toolbar > Next Bookmark | firmware/vs | ok |  | 0.6 |  |
| Toolbar Toolbar > Open in Adminer | python-tk/vs | ok | قواعد البيانات [QMessageBox] | 1.21 |  |
| Toolbar Toolbar > Open in Browser | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Overwrite | firmware/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Paint | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Play | game/vs | ok |  | 0.65 |  |
| Toolbar Toolbar > Rect | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Refresh | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Reload (F5 in the page) | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Rotate | python-tk/vs | ok |  | 0.63 |  |
| Toolbar Toolbar > Run | python-tk/vs | ok |  | 0.62 |  |
| Toolbar Toolbar > Run All | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Run Failed | python-tk/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Select | game/vs | ok |  | 0.61 |  |
| Toolbar Toolbar > Sprite Sheet | game/vs | ok | Sprite Sheet and Animations [SpriteSheetDialog] | 0.84 |  |
| Toolbar Toolbar > Tileset | game/vs | ok | Import Tileset [TilesetDialog] | 0.82 |  |
| Toolbox (Toolbox) > Choose Items | python-tk/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 1.49 |  |
| Toolbox (Toolbox) > Choose Items | none/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.86 |  |
| Toolbox (Toolbox) > Choose Items | python-tk/vscode | ok | Choose Toolbox Items [ChooseItemsDialog] | 1.03 |  |
| Toolbox (Toolbox) > Choose Items | python-tk/agent | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.95 |  |
| Toolbox (Toolbox) > Choose Items | vb6/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.81 |  |
| Toolbox (Toolbox) > Choose Items | csharp/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.83 |  |
| Toolbox (Toolbox) > Choose Items | flutter/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.92 |  |
| Toolbox (Toolbox) > Choose Items | retro/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 1.04 |  |
| Toolbox (Toolbox) > Choose Items | dos/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.99 |  |
| Toolbox (Toolbox) > Choose Items | game/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.87 |  |
| Toolbox (Toolbox) > Choose Items | asm/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.82 |  |
| Toolbox (Toolbox) > Choose Items | firmware/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 1.14 |  |
| Toolbox (Toolbox) > Collapse All | python-tk/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Collapse All | none/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | python-tk/vscode | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Collapse All | python-tk/agent | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | vb6/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | csharp/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | flutter/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | retro/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | dos/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | game/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Collapse All | asm/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Collapse All | firmware/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | python-tk/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | none/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | python-tk/vscode | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Expand All | python-tk/agent | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | vb6/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | csharp/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Expand All | flutter/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Expand All | retro/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | dos/vs | ok |  | 0.63 |  |
| Toolbox (Toolbox) > Expand All | game/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Expand All | asm/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Expand All | firmware/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | python-tk/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Show All Items | none/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | python-tk/vscode | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Show All Items | python-tk/agent | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | vb6/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | csharp/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | flutter/vs | ok |  | 0.62 |  |
| Toolbox (Toolbox) > Show All Items | retro/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | dos/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | game/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | asm/vs | ok |  | 0.61 |  |
| Toolbox (Toolbox) > Show All Items | firmware/vs | ok |  | 0.61 |  |
| Tools > AI Settings | python-tk/vs | ok | Options [OptionsDialog] | 3.72 |  |
| Tools > Accessibility Check | python-tk/vs | ok | Accessibility Check [QDialog] | 0.96 |  |
| Tools > Ask AI about the Selection | python-tk/vs | ok |  | 0.61 |  |
| Tools > Assembly Toolchains | python-tk/vs | ok | Assembly Toolchains [AsmToolchainsDialog] | 1.15 |  |
| Tools > Car Connection > Bus Monitor | python-tk/vs | ok |  | 0.67 |  |
| Tools > Car Connection > Connect to Car | python-tk/vs | ok | Connect to Car [ConnectDialog] | 1.28 |  |
| Tools > Car Connection > Demo Car (Simulator) | python-tk/vs | ok |  | 0.8 |  |
| Tools > Car Connection > Find Control Units | python-tk/vs | ok | Find Control Units [FindEcusDialog] | 0.7 |  |
| Tools > Car Diagnostics | python-tk/vs | ok |  | 2.37 |  |
| Tools > Car Fault Guide | python-tk/vs | ok |  | 1.24 |  |
| Tools > Car Service Functions | python-tk/vs | ok |  | 1.46 |  |
| Tools > Code Snippets Manager | python-tk/vs | ok | Code Snippets Manager [SnippetsDialog] | 1.19 |  |
| Tools > Compare (Diff) > Compare Current File with | python-tk/vs | ok | Compare [QMessageBox] | 1.04 |  |
| Tools > Compare (Diff) > Compare Current File with Clipboard | python-tk/vs | ok | Compare [QMessageBox] | 1.01 |  |
| Tools > Compare (Diff) > Compare Current File with Git HEAD | python-tk/vs | ok | Compare [QMessageBox] | 0.93 |  |
| Tools > Compare (Diff) > Compare Current File with Saved | python-tk/vs | ok | Compare [QMessageBox] | 0.98 |  |
| Tools > Compare (Diff) > Compare Files | python-tk/vs | ok | Compare Files - first (left) file [QFileDialog] | 1.24 |  |
| Tools > Component Packages > Choose Toolbox Items | python-tk/vs | ok | Choose Toolbox Items [ChooseItemsDialog] | 0.95 |  |
| Tools > Component Packages > Hot Reload (package development) | python-tk/vs | ok |  | 0.61 |  |
| Tools > Component Packages > Manage Component Packages | python-tk/vs | ok | Component Packages [ComponentManagerDialog] | 0.92 |  |
| Tools > Component Packages > Reload Packages | python-tk/vs | ok |  | 0.62 |  |
| Tools > Composer > Dump Autoload (composer dump-autoload) | python-tk/vs | ok |  | 1.02 |  |
| Tools > Composer > Open composer.json | python-tk/vs | ok |  | 0.63 |  |
| Tools > Composer > Remove Package | python-tk/vs | ok |  | 0.61 |  |
| Tools > Composer > Require Package | python-tk/vs | ok |  | 0.6 |  |
| Tools > Composer > Show Outdated Packages | python-tk/vs | ok |  | 0.65 |  |
| Tools > Composer > Validate composer.json | python-tk/vs | ok |  | 0.62 |  |
| Tools > Databases > Add Connection | python-tk/vs | ok | Database Connection [ConnectionDialog] | 1.61 |  |
| Tools > Databases > Database Diagram | python-tk/vs | ok | Databases [QMessageBox] | 0.92 |  |
| Tools > Databases > Databases | python-tk/vs | ok |  | 0.61 |  |
| Tools > Databases > Local Servers > Copy MariaDB/MySQL Password | python-tk/vs | ok |  | 0.61 |  |
| Tools > Databases > Local Servers > Copy PostgreSQL Password | python-tk/vs | ok |  | 0.64 |  |
| Tools > Databases > Local Servers > Server Status | python-tk/vs | ok | Local Database Servers [QMessageBox] | 2.42 |  |
| Tools > Databases > Local Servers > Stop local MariaDB/MySQL | python-tk/vs | ok |  | 2.17 |  |
| Tools > Databases > Local Servers > Stop local PostgreSQL | python-tk/vs | ok |  | 1.52 |  |
| Tools > Databases > New Query | python-tk/vs | ok | Databases [QMessageBox] | 0.88 |  |
| Tools > Databases > New SQLite Database | python-tk/vs | ok | New SQLite database [QFileDialog] | 1.09 |  |
| Tools > Databases > Open in Adminer | python-tk/vs | ok | Databases [QMessageBox] | 0.89 |  |
| Tools > Databases > Start local MariaDB/MySQL | python-tk/vs | ok |  | 0.69 |  |
| Tools > Docker > Build Image | python-tk/vs | ok | Docker [QMessageBox] | 1.46 |  |
| Tools > Docker > Compose Down | python-tk/vs | ok |  | 0.63 |  |
| Tools > Docker > Compose Up | python-tk/vs | ok | Docker [QMessageBox] | 1.2 |  |
| Tools > Docker > Docker Panel | python-tk/vs | ok |  | 0.69 |  |
| Tools > Docker > Generate Dockerfile / Compose / Dev Container | python-tk/vs | ok | Generate Docker Files [DockerGenerateDialog] | 1.83 |  |
| Tools > Docker > Lint Dockerfile | python-tk/vs | ok | فحص (Lint) [QMessageBox] | 1.17 |  |
| Tools > Extensions | python-tk/vs | ok | Extensions [ExtensionsDialog] | 1.22 |  |
| Tools > Firmware & ECU > Analyze Firmware File | python-tk/vs | ok | Analyze Firmware File [QFileDialog] | 1.65 |  |
| Tools > Firmware & ECU > Calibration Maps > Compare Two Binaries (Maps) | python-tk/vs | ok | Compare: file A (editable) [QFileDialog] | 2.57 |  |
| Tools > Firmware & ECU > Calibration Maps > Find Maps in a Binary | python-tk/vs | ok | Find Maps in a Binary [QFileDialog] | 1.66 |  |
| Tools > Firmware & ECU > Calibration Maps > Open Binary in Map Editor | python-tk/vs | ok | Open Binary in Map Editor [QFileDialog] | 1.71 |  |
| Tools > Firmware & ECU > Calibration Maps > Open Binary with an A2L | python-tk/vs | ok | Open Binary [QFileDialog] | 3.74 |  |
| Tools > Firmware & ECU > Calibration Maps > Open rusEFI / Speeduino Tune (msq + ini) | python-tk/vs | ok | Open Tune (msq) [QFileDialog] | 1.37 |  |
| Tools > Firmware & ECU > Compare Firmware Files | python-tk/vs | ok | Compare: original / first file [QFileDialog] | 1.2 |  |
| Tools > Firmware & ECU > Create Synthetic Test Firmware | python-tk/vs | ok | Synthetic Test Firmware [QInputDialog] | 0.95 |  |
| Tools > Firmware & ECU > Firmware Converter (HEX / S-record / ELF / split / merge) | python-tk/vs | ok | Firmware Converter [FirmwareConverterDialog] | 0.84 |  |
| Tools > Firmware & ECU > Getting Started | python-tk/vs | ok |  | 0.86 |  |
| Tools > Firmware & ECU > New ECU Project | python-tk/vs | ok | New ECU Project: choose the original file [QFileDialog] | 1.37 |  |
| Tools > Firmware & ECU > New ECU Project (Demo Firmware) | python-tk/vs | ok | New ECU Project [QInputDialog] | 1.04 |  |
| Tools > Firmware & ECU > Open EEPROM Dump (read-only) | python-tk/vs | ok | Open EEPROM Dump (read-only) [QFileDialog] | 6.24 |  |
| Tools > Firmware & ECU > Open Firmware in Workbench | python-tk/vs | ok | Open Firmware in Workbench [QFileDialog] | 2.31 |  |
| Tools > Image Editor > New Icon | python-tk/vs | ok | New Image [NewImageDialog] | 0.99 |  |
| Tools > Image Editor > New Image | python-tk/vs | ok | New Image [NewImageDialog] | 0.97 |  |
| Tools > Image Editor > Open Image | python-tk/vs | ok | Open Image [QFileDialog] | 2.16 |  |
| Tools > Interpreter Path | python-tk/vs | ok | Locate Python (Tkinter) interpreter [QFileDialog] | 1.1 |  |
| Tools > Keymap > Emacs (basic) | python-tk/vs | ok |  | 0.69 |  |
| Tools > Keymap > VS Code | python-tk/vs | ok |  | 0.67 |  |
| Tools > Keymap > Vim | python-tk/vs | ok |  | 0.69 |  |
| Tools > Keymap > Visual Studio | python-tk/vs | ok |  | 0.69 |  |
| Tools > Language > English | python-tk/vs | ok |  | 0.62 |  |
| Tools > Language > العربية | python-tk/vs | ok | اللغة [QMessageBox] | 7.92 |  |
| Tools > Language Servers and Debuggers | python-tk/vs | ok | Language Servers and Debuggers [LanguageServersDialog] | 4.88 |  |
| Tools > Macros > Macro Explorer | python-tk/vs | ok | Macro Explorer [MacroExplorer] | 1.07 |  |
| Tools > Macros > Record Temporary Macro / Stop | python-tk/vs | ok |  | 0.63 |  |
| Tools > Macros > Run Temporary Macro | python-tk/vs | ok |  | 0.63 |  |
| Tools > Macros > Save Temporary Macro | python-tk/vs | ok | Macros [QMessageBox] | 1.18 |  |
| Tools > NuGet Package Manager > Package Manager Console | python-tk/vs | ok |  | 0.71 |  |
| Tools > NuGet Package Manager > Package Manager Settings | python-tk/vs | ok | Options - NuGet Package Manager [QDialog] | 1.14 |  |
| Tools > Options | python-tk/vs | ok | Options [OptionsDialog] | 6.19 |  |
| Tools > PE / MFC Resource Workbench | python-tk/vs | ok | فتح برنامج ويندوز (منضدة PE / MFC) [QFileDialog] | 1.57 |  |
| Tools > PHP Versions | python-tk/vs | ok | PHP Versions [PhpVersionsDialog] | 1.09 |  |
| Tools > REST Client | python-tk/vs | ok |  | 1.42 |  |
| Tools > Retro > Apollo AGC > Assembly Listing | python-tk/vs | ok |  | 0.61 |  |
| Tools > Retro > Apollo AGC > Build with yaYUL | python-tk/vs | ok |  | 0.63 |  |
| Tools > Retro > Apollo AGC > DSKY Panel | python-tk/vs | ok |  | 0.76 |  |
| Tools > Retro > Apollo AGC > DSKY Verbs, Nouns and Programs | python-tk/vs | ok | DSKY Verbs, Nouns and Programs [QDialog] | 1.1 |  |
| Tools > Retro > Apollo AGC > Open Apollo Source | python-tk/vs | ok | Open Apollo Source [QDialog] | 0.9 |  |
| Tools > Retro > Apollo AGC > Virtual AGC Toolchain | python-tk/vs | ok | Virtual AGC Toolchain [QMessageBox] | 0.89 |  |
| Tools > Retro > DOS Programming > Build DOS Program | python-tk/vs | ok | Build DOS Program [QMessageBox] | 0.81 |  |
| Tools > Retro > DOS Programming > DOS Interrupt Reference | python-tk/vs | ok | DOS Interrupt Reference [InterruptReference] | 0.77 |  |
| Tools > Retro > DOS Programming > DOS Project Settings | python-tk/vs | ok | DOS Project Settings [QMessageBox] | 0.91 |  |
| Tools > Retro > DOS Programming > DOS Toolchains | python-tk/vs | ok | DOS Toolchains [DosToolchainsDialog] | 0.76 |  |
| Tools > Retro > DOS Programming > Open Symbol Map | python-tk/vs | ok | Open Symbol Map [QMessageBox] | 0.83 |  |
| Tools > Retro > DOS Programming > Run in DOSBox-X | python-tk/vs | ok | Run in DOSBox-X [QMessageBox] | 0.87 |  |
| Tools > Retro > DOS Programming > Run in DOSBox-X Debugger | python-tk/vs | ok | Run in DOSBox-X Debugger [QMessageBox] | 0.8 |  |
| Tools > Retro > DOS Programming > Run in My QBasic | python-tk/vs | ok | Run in My QBasic [QMessageBox] | 0.78 |  |
| Tools > Retro > DOS Programming > Run with Captured Output | python-tk/vs | ok | Run with Captured Output [QMessageBox] | 0.79 |  |
| Tools > Retro > DOS Programming > Show Last DOS Screen | python-tk/vs | ok | Show Last DOS Screen [QMessageBox] | 0.99 |  |
| Tools > Retro > Debug ROM in Emulator | python-tk/vs | ok | Debug ROM in Emulator [QFileDialog] | 1.63 |  |
| Tools > Retro > Emulators | python-tk/vs | ok | Retro Emulators [EmulatorManager] | 1.37 |  |
| Tools > Retro > Game Designers > New Atari 2600 Screen | python-tk/vs | ok |  | 1.07 |  |
| Tools > Retro > Game Designers > New DOS Mode 13h Screen | python-tk/vs | ok |  | 1.67 |  |
| Tools > Retro > Game Designers > New Game Boy Map | python-tk/vs | ok |  | 0.93 |  |
| Tools > Retro > Game Designers > New NES Screen / Level | python-tk/vs | ok |  | 1.05 |  |
| Tools > Retro > Game Designers > Open Game Design | python-tk/vs | ok | Open Game Design [QFileDialog] | 1.25 |  |
| Tools > Retro > Graphics & Text > Atari 2600 Playfield Editor | python-tk/vs | ok |  | 0.89 |  |
| Tools > Retro > Graphics & Text > New Text Table | python-tk/vs | ok |  | 2.68 |  |
| Tools > Retro > Graphics & Text > New Tile Sheet (8 KB CHR) | python-tk/vs | ok |  | 0.91 |  |
| Tools > Retro > Graphics & Text > Script Dump / Insert | python-tk/vs | ok |  | 1.3 |  |
| Tools > Retro > Graphics & Text > Text Table Editor (.tbl) | python-tk/vs | ok | Open Text Table [QFileDialog] | 1.64 |  |
| Tools > Retro > Graphics & Text > Tile Editor (Open ROM / Binary) | python-tk/vs | ok | Open ROM / Binary in the Tile Editor [QFileDialog] | 2.52 |  |
| Tools > Retro > Graphics & Text > Tile Map Editor | python-tk/vs | ok |  | 1.19 |  |
| Tools > Retro > Graphics & Text > View Current File as Tiles | python-tk/vs | ok |  | 0.62 |  |
| Tools > Retro > Legacy Fortran > Card Deck View | python-tk/vs | ok |  | 0.61 |  |
| Tools > Retro > Legacy Fortran > Compiler Preset | python-tk/vs | ok |  | 0.69 |  |
| Tools > Retro > Legacy Fortran > Convert to Free Form | python-tk/vs | ok |  | 0.6 |  |
| Tools > Retro > Legacy Fortran > Explain Legacy Constructs | python-tk/vs | ok |  | 0.61 |  |
| Tools > Retro > ROM Workbench > Apply Patch | python-tk/vs | ok | Apply Patch [ApplyPatchDialog] | 0.9 |  |
| Tools > Retro > ROM Workbench > Compare Files | python-tk/vs | ok | Compare: first file [QFileDialog] | 1.22 |  |
| Tools > Retro > ROM Workbench > Create Patch (IPS / BPS / UPS) | python-tk/vs | ok | Create Patch [CreatePatchDialog] | 1.11 |  |
| Tools > Retro > ROM Workbench > Fix Header Checksum of a File | python-tk/vs | ok | Fix Header Checksum [QFileDialog] | 1.58 |  |
| Tools > Retro > ROM Workbench > Open in Hex Editor | python-tk/vs | ok | Open in Hex Editor [QFileDialog] | 1.55 |  |
| Tools > Retro > ROM Workbench > ROM Info | python-tk/vs | ok | ROM Info [QFileDialog] | 2.99 |  |
| Tools > Retro > Reload ROM in Emulator | python-tk/vs | ok |  | 0.61 |  |
| Tools > Retro > Retro Development > Disassemble ROM into Project | python-tk/vs | ok | Disassemble ROM into Project [DisassembleDialog] | 0.96 |  |
| Tools > Retro > Retro Development > Import Labels into Hints | python-tk/vs | ok | Import Labels [QMessageBox] | 0.92 |  |
| Tools > Retro > Retro Development > Re-disassemble with Hints | python-tk/vs | ok | Re-disassemble with Hints [QMessageBox] | 0.85 |  |
| Tools > Retro > Retro Development > Rebuild Check (compare with the original) | python-tk/vs | ok | Rebuild Check [QMessageBox] | 0.85 |  |
| Tools > Retro > Retro Development > Retro Toolchains | python-tk/vs | ok | Retro Toolchains [RetroToolchainsDialog] | 1.02 |  |
| Tools > Retro > Run ROM in Emulator | python-tk/vs | ok | Run ROM in Emulator [QFileDialog] | 1.35 |  |
| Tools > Retro > Text-Mode (DOS) > New ANSI Art | python-tk/vs | ok |  | 0.89 |  |
| Tools > Retro > Text-Mode (DOS) > New Text-Mode Screen | python-tk/vs | ok | New Text-Mode Screen [QInputDialog] | 0.88 |  |
| Tools > Retro > Text-Mode (DOS) > Open Screen or Art | python-tk/vs | ok | Open Screen or Art [QFileDialog] | 1.2 |  |
| Tools > Retro > Text-Mode (DOS) > Test Run (simulator) | python-tk/vs | ok | Test Run [QMessageBox] | 0.82 |  |
| Tools > Retro > Text-Mode (DOS) > Use Current Art as Splash Screen | python-tk/vs | ok | Save Art [QFileDialog] | 1.0 |  |
| Tools > Rust Settings | python-tk/vs | ok | Rust Settings [RustSettingsDialog] | 1.13 |  |
| Tools > VS Code Extensions (Open VSX) | python-tk/vs | ok |  | 0.7 |  |
| View > 8086 Emulator | python-tk/vs | ok |  | 0.86 |  |
| View > AI Chat | python-tk/vs | ok |  | 0.61 |  |
| View > AI Web Chats | python-tk/vs | ok |  | 0.68 |  |
| View > Agent Manager | python-tk/vs | ok |  | 0.62 |  |
| View > Animations | python-tk/vs | ok |  | 0.68 |  |
| View > Call Stack | python-tk/vs | ok |  | 0.61 |  |
| View > Code | python-tk/vs | ok |  | 0.85 |  |
| View > CodeIgniter Panel (Spark, Routes) | python-tk/vs | ok |  | 0.63 |  |
| View > Command Palette | python-tk/vs | ok |  | 5.17 |  |
| View > Data | python-tk/vs | ok |  | 0.61 |  |
| View > Data Sources | python-tk/vs | ok |  | 0.62 |  |
| View > Databases | python-tk/vs | ok |  | 0.62 |  |
| View > Designer | python-tk/vs | ok |  | 0.69 |  |
| View > Django / Flask / FastAPI Panel | python-tk/vs | ok |  | 0.62 |  |
| View > Document Outline | python-tk/vs | ok |  | 0.61 |  |
| View > Error List | python-tk/vs | ok |  | 0.61 |  |
| View > Extension Output | python-tk/vs | ok |  | 0.92 |  |
| View > Extension Views > Claude Code | python-tk/vs | ok |  | 1.36 |  |
| View > Extensions (VS Code) | python-tk/vs | ok |  | 0.79 |  |
| View > Find All References Window | python-tk/vs | ok |  | 0.64 |  |
| View > Find Results | python-tk/vs | ok |  | 0.62 |  |
| View > Flask | flask/vs | ok |  | 0.6 |  |
| View > Framework Tools | python-tk/vs | ok |  | 0.62 |  |
| View > Git Changes | python-tk/vs | ok |  | 0.62 |  |
| View > Immediate | python-tk/vs | ok |  | 0.61 |  |
| View > Laravel Panel (Artisan, Routes, Tinker) | python-tk/vs | ok |  | 0.62 |  |
| View > Layout > Agent | python-tk/vs | ok |  | 6.38 |  |
| View > Layout > Next Layout | python-tk/vs | ok |  | 3.53 |  |
| View > Layout > Reset Current Layout | python-tk/vs | ok |  | 0.93 |  |
| View > Layout > VS Code | python-tk/vs | ok |  | 5.59 |  |
| View > Layout > Visual Studio | python-tk/vs | ok |  | 0.61 |  |
| View > Layout > Zen Mode | python-tk/vs | ok |  | 1.12 |  |
| View > Locals | python-tk/vs | ok |  | 0.6 |  |
| View > New Agent Task | python-tk/vs | ok |  | 0.62 |  |
| View > Notebook Variables | python-tk/vs | ok |  | 0.62 |  |
| View > Object Browser | python-tk/vs | ok |  | 0.69 |  |
| View > Objects and Timeline | python-tk/vs | ok |  | 0.61 |  |
| View > Output | python-tk/vs | ok |  | 0.6 |  |
| View > Package Manager Console | python-tk/vs | ok |  | 0.74 |  |
| View > Preview | python-tk/vs | ok |  | 0.63 |  |
| View > Problems Explained | python-tk/vs | ok |  | 0.76 |  |
| View > Properties | python-tk/vs | ok |  | 0.61 |  |
| View > Quick Open (Go to File) | python-tk/vs | ok |  | 0.67 |  |
| View > Rails Panel (Console, Routes, Models) | python-tk/vs | ok |  | 0.64 |  |
| View > Remote Explorer | python-tk/vs | ok |  | 0.62 |  |
| View > Requests | python-tk/vs | ok |  | 0.65 |  |
| View > Retro Debugger | python-tk/vs | ok |  | 0.7 |  |
| View > Sizes | python-tk/vs | ok | DesignerView [DesignerView] | 0.68 |  |
| View > Solution Explorer | python-tk/vs | ok |  | 0.61 |  |
| View > States | python-tk/vs | ok |  | 0.61 |  |
| View > Tab Order | python-tk/vs | ok |  | 0.61 |  |
| View > Terminal | python-tk/vs | ok |  | 0.68 |  |
| View > Toolbox | python-tk/vs | ok |  | 0.61 |  |
| View > Zoom > 100% | python-tk/vs | ok |  | 0.61 |  |
| View > Zoom > 150% | python-tk/vs | ok |  | 0.61 |  |
| View > Zoom > 200% | python-tk/vs | ok |  | 0.6 |  |
| View > Zoom > 300% | python-tk/vs | ok |  | 0.63 |  |
| View > Zoom > 400% | python-tk/vs | ok |  | 0.61 |  |
| View > Zoom > 50% | python-tk/vs | ok | QWidget [QWidget] | 0.69 |  |
| View > Zoom > 75% | python-tk/vs | ok |  | 0.61 |  |
| View > Zoom > Zoom In  (Ctrl+Wheel) | python-tk/vs | ok | QWidget [QWidget] | 0.7 |  |
| View > Zoom > Zoom Out | python-tk/vs | ok |  | 0.61 |  |
| Window > Auto Hide All | python-tk/vs | ok |  | 2.22 |  |
| Window > Remove Split | python-tk/vs | ok |  | 0.61 |  |
| Window > Split Editor Down | python-tk/vs | ok |  | 0.62 |  |
| Window > Split Editor Right | python-tk/vs | ok |  | 0.62 |  |
| pygame > Build EXE / Installer | game/vs | ok | Publish Platformer [PublishDialog] | 0.84 |  |
| pygame > Build One-File EXE (PyInstaller) | game/vs | ok |  | 0.61 |  |
| pygame > Export to Godot | game/vs | ok |  | 8.46 |  |
| pygame > Run Game | game/vs | ok |  | 0.67 |  |
| Build > Mobile App > Android App Bundle (Google Play) | python-tk/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | none/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | python-tk/vscode | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | python-tk/agent | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | vb6/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | csharp/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | web/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | flask/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | retro/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | dos/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | game/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | asm/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Build > Mobile App > Android App Bundle (Google Play) | firmware/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Command Palette > Claude Code for VS Code > Claude Code: Open in New Window | python-tk/vs | skipped |  | 0 | starts a second IDE process |
| Command Palette > Flutter > Build: Build App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Command Palette > Python > Install Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Command Palette > Python > Install Requirements | flask/vs | skipped |  | 0 | downloads / installs software |
| Command Palette > pygame > Install pygame | game/vs | skipped |  | 0 | downloads / installs software |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | none/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | vb6/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | csharp/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | web/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | flutter/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | retro/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | dos/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | game/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | asm/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | firmware/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | none/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | vb6/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | csharp/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | web/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | flutter/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | retro/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | dos/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | game/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | asm/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | firmware/vs | skipped |  | 0 | initializes / starts a database server in the user's data folder (minutes; outside the sandbox) |
| Debug > Install Delve (Go Debugger) | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | none/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | python-tk/vscode | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | python-tk/agent | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | vb6/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | csharp/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | web/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | flask/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | flutter/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | retro/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | dos/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | game/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | asm/vs | skipped |  | 0 | downloads / installs software |
| Debug > Install Delve (Go Debugger) | firmware/vs | skipped |  | 0 | downloads / installs software |
| Designer > (control) > Add Animation > Exit > Fade Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Fade Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Slide Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (control) > Add Animation > Exit > Zoom Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Fade Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Slide Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | python-tk/vscode | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | python-tk/agent | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | vb6/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | csharp/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | flutter/vs | skipped |  | 0 | quits / restarts the IDE |
| Designer > (form) > Add Animation > Exit > Zoom Out | asm/vs | skipped |  | 0 | quits / restarts the IDE |
| File > Exit | python-tk/vs | skipped |  | 0 | quits / restarts the IDE |
| File > New Window | python-tk/vs | skipped |  | 0 | starts a second IDE process |
| Flutter > Build > Build App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Git > Force Push (with lease) | python-tk/vs | skipped |  | 0 | git push / sync changes a remote repository |
| Git > GitHub > Create Pull Request | python-tk/vs | skipped |  | 0 | git push / sync changes a remote repository |
| Git > GitHub > Download GitHub CLI | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Git > GitHub > Pull Requests and Issues | python-tk/vs | skipped |  | 0 | git push / sync changes a remote repository |
| Git > GitHub > Sign in (gh auth login) | python-tk/vs | skipped |  | 0 | signs in to an online service |
| Git > Push | python-tk/vs | skipped |  | 0 | git push / sync changes a remote repository |
| Git > Sync (pull, then push) | python-tk/vs | skipped |  | 0 | git push / sync changes a remote repository |
| Help > Check for Updates | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Help > Check for Updates Automatically | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Help > Install Another Version | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Project > Flutter Commands > Build > Build App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Project > Python Commands > Install Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Project > Python Commands > Install Package | python-tk/vscode | skipped |  | 0 | downloads / installs software |
| Project > Python Commands > Install Package | python-tk/agent | skipped |  | 0 | downloads / installs software |
| Project > Python Commands > Install Package | flask/vs | skipped |  | 0 | downloads / installs software |
| Project > Python Commands > Install Package | game/vs | skipped |  | 0 | downloads / installs software |
| Project > Python Commands > Install Requirements | flask/vs | skipped |  | 0 | downloads / installs software |
| Project > pygame Commands > Install pygame | game/vs | skipped |  | 0 | downloads / installs software |
| Python > Install Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Python > Install Requirements | flask/vs | skipped |  | 0 | downloads / installs software |
| Share > Live Share Window | python-tk/vs | skipped |  | 0 | signs in to an online service |
| Share > Start Collaboration Session | python-tk/vs | skipped |  | 0 | signs in to an online service |
| Site > Deploy to Cloud / Git / SSH | python-tk/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | none/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | python-tk/vscode | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | python-tk/agent | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | vb6/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | csharp/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | web/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | flask/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | retro/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | dos/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | game/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | asm/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Site > Deploy to Cloud / Git / SSH | firmware/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Solution Explorer > (project) > Build > Build App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Solution Explorer > (project) > Install Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Install Package | python-tk/vscode | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Install Package | python-tk/agent | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Install Package | game/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Install pygame | game/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Python > Install Package | flask/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (project) > Python > Install Requirements | flask/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (resources) > Build > Build App Bundle (Google Play) | flutter/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Solution Explorer > (resources) > Install Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (resources) > Install Package | python-tk/vscode | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (resources) > Install Package | python-tk/agent | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (resources) > Install Package | game/vs | skipped |  | 0 | downloads / installs software |
| Solution Explorer > (resources) > Install pygame | game/vs | skipped |  | 0 | downloads / installs software |
| Toolbar Activity Bar > Live Share | python-tk/vscode | skipped |  | 0 | signs in to an online service |
| Toolbox (Toolbox) > Install Component Package | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | none/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | python-tk/vscode | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | python-tk/agent | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | vb6/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | csharp/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | flutter/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | retro/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | dos/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | game/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | asm/vs | skipped |  | 0 | downloads / installs software |
| Toolbox (Toolbox) > Install Component Package | firmware/vs | skipped |  | 0 | downloads / installs software |
| Tools > Component Packages > Install Component Package (.radcomp) | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Tools > Composer > Install (composer install) | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Tools > Composer > Update (composer update) | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Tools > Deploy to Cloud / Git / SSH | python-tk/vs | skipped |  | 0 | publishes to the internet / cloud / FTP / a store |
| Tools > Install Extension from VSIX | python-tk/vs | skipped |  | 0 | downloads / installs software |
| Tools > Install Web Language Servers (HTML/CSS/JSON/PHP/JS/TS) | python-tk/vs | skipped |  | 0 | downloads / installs software |
| pygame > Install pygame | game/vs | skipped |  | 0 | downloads / installs software |
| BASIC > Stop Running Command | vb6/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | python-tk/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | none/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | python-tk/vscode | disabled |  | 0.0 |  |
| Build > Clean Solution | python-tk/agent | disabled |  | 0.0 |  |
| Build > Clean Solution | vb6/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | csharp/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | web/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | flask/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | flutter/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | retro/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | dos/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | game/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | asm/vs | disabled |  | 0.0 |  |
| Build > Clean Solution | firmware/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | python-tk/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | none/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | python-tk/vscode | disabled |  | 0.0 |  |
| Build > Configuration Manager | python-tk/agent | disabled |  | 0.0 |  |
| Build > Configuration Manager | vb6/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | csharp/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | web/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | flask/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | flutter/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | retro/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | dos/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | game/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | asm/vs | disabled |  | 0.0 |  |
| Build > Configuration Manager | firmware/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | python-tk/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | none/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | python-tk/vscode | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | python-tk/agent | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | vb6/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | csharp/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | web/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | flask/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | flutter/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | retro/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | dos/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | game/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | asm/vs | disabled |  | 0.0 |  |
| Build > Mobile App > Cancel Build | firmware/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | python-tk/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | none/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | python-tk/vscode | disabled |  | 0.0 |  |
| Build > Publish Selection | python-tk/agent | disabled |  | 0.0 |  |
| Build > Publish Selection | vb6/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | csharp/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | web/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | flask/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | flutter/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | retro/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | dos/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | game/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | asm/vs | disabled |  | 0.0 |  |
| Build > Publish Selection | firmware/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | python-tk/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | none/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | python-tk/vscode | disabled |  | 0.0 |  |
| Build > Rebuild Solution | python-tk/agent | disabled |  | 0.0 |  |
| Build > Rebuild Solution | vb6/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | csharp/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | web/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | flask/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | flutter/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | retro/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | dos/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | game/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | asm/vs | disabled |  | 0.0 |  |
| Build > Rebuild Solution | firmware/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: Show Routes | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: Spark Commands | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: spark db:seed... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: spark make:controller... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: spark make:migration... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: spark make:model... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > CodeIgniter > CodeIgniter: spark migrate... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Laravel > Laravel: Generate IDE Helper Files | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Laravel > Laravel: Open Tinker | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Laravel > Laravel: Run Artisan Command... | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Laravel > Laravel: Show Routes | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Laravel > Laravel: make:model -mcr | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Rails > Rails: Edit Credentials | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Rails > Rails: Open Console | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Rails > Rails: Show Models | python-tk/vs | disabled |  | 0.0 |  |
| Command Palette > Rails > Rails: Show Routes | python-tk/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Start local MariaDB/MySQL | python-tk/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Start local PostgreSQL | python-tk/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | none/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | vb6/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | csharp/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | web/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | flutter/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | retro/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | dos/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | game/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | asm/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local MariaDB/MySQL | firmware/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | none/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | vb6/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | csharp/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | web/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | flutter/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | retro/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | dos/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | game/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | asm/vs | disabled |  | 0.0 |  |
| Databases (QTreeWidget) > Local Servers > Stop local PostgreSQL | firmware/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | none/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | vb6/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | csharp/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | web/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | flask/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | flutter/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | retro/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | dos/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | game/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | asm/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Reload | firmware/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | none/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | vb6/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | csharp/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | web/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | flask/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | flutter/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | retro/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | dos/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | game/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | asm/vs | disabled |  | 0.0 |  |
| Debug > Mobile > Hot Restart | firmware/vs | disabled |  | 0.0 |  |
| Debug > Start Debugging / Continue | none/vs | disabled |  | 0.0 |  |
| Debug > Start Without Debugging | none/vs | disabled |  | 0.0 |  |
| Debug > Step Into | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Step Into | none/vs | disabled |  | 0.0 |  |
| Debug > Step Into | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Step Into | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Step Into | vb6/vs | disabled |  | 0.0 |  |
| Debug > Step Into | csharp/vs | disabled |  | 0.0 |  |
| Debug > Step Into | web/vs | disabled |  | 0.0 |  |
| Debug > Step Into | flask/vs | disabled |  | 0.0 |  |
| Debug > Step Into | flutter/vs | disabled |  | 0.0 |  |
| Debug > Step Into | retro/vs | disabled |  | 0.0 |  |
| Debug > Step Into | dos/vs | disabled |  | 0.0 |  |
| Debug > Step Into | game/vs | disabled |  | 0.0 |  |
| Debug > Step Into | asm/vs | disabled |  | 0.0 |  |
| Debug > Step Into | firmware/vs | disabled |  | 0.0 |  |
| Debug > Step Out | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Step Out | none/vs | disabled |  | 0.0 |  |
| Debug > Step Out | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Step Out | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Step Out | vb6/vs | disabled |  | 0.0 |  |
| Debug > Step Out | csharp/vs | disabled |  | 0.0 |  |
| Debug > Step Out | web/vs | disabled |  | 0.0 |  |
| Debug > Step Out | flask/vs | disabled |  | 0.0 |  |
| Debug > Step Out | flutter/vs | disabled |  | 0.0 |  |
| Debug > Step Out | retro/vs | disabled |  | 0.0 |  |
| Debug > Step Out | dos/vs | disabled |  | 0.0 |  |
| Debug > Step Out | game/vs | disabled |  | 0.0 |  |
| Debug > Step Out | asm/vs | disabled |  | 0.0 |  |
| Debug > Step Out | firmware/vs | disabled |  | 0.0 |  |
| Debug > Step Over | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Step Over | none/vs | disabled |  | 0.0 |  |
| Debug > Step Over | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Step Over | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Step Over | vb6/vs | disabled |  | 0.0 |  |
| Debug > Step Over | csharp/vs | disabled |  | 0.0 |  |
| Debug > Step Over | web/vs | disabled |  | 0.0 |  |
| Debug > Step Over | flask/vs | disabled |  | 0.0 |  |
| Debug > Step Over | flutter/vs | disabled |  | 0.0 |  |
| Debug > Step Over | retro/vs | disabled |  | 0.0 |  |
| Debug > Step Over | dos/vs | disabled |  | 0.0 |  |
| Debug > Step Over | game/vs | disabled |  | 0.0 |  |
| Debug > Step Over | asm/vs | disabled |  | 0.0 |  |
| Debug > Step Over | firmware/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | none/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Stop Debugging | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Stop Debugging | vb6/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | csharp/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | flutter/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | retro/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | dos/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | game/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | asm/vs | disabled |  | 0.0 |  |
| Debug > Stop Debugging | firmware/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | python-tk/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | none/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | python-tk/vscode | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | python-tk/agent | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | vb6/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | csharp/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | web/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | flask/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | flutter/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | retro/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | dos/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | game/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | asm/vs | disabled |  | 0.0 |  |
| Debug > Toggle Breakpoint | firmware/vs | disabled |  | 0.0 |  |
| Designer > (form) > Copy | python-tk/vs | disabled |  | 0.0 |  |
| Designer > (form) > Copy | flutter/vs | disabled |  | 0.0 |  |
| Designer > (form) > Copy | asm/vs | disabled |  | 0.0 |  |
| Edit > Copy | python-tk/vs | disabled |  | 0.0 |  |
| Edit > Cut | python-tk/vs | disabled |  | 0.0 |  |
| Edit > Delete | python-tk/vs | disabled |  | 0.0 |  |
| Edit > Redo | python-tk/vs | disabled |  | 0.0 |  |
| Edit > Undo | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Build on Remote | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Disconnect | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Recent SSH Hosts > (no saved hosts) | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Reload Remote File | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Remote Terminal | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Run Remote Command | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Run on Remote | python-tk/vs | disabled |  | 0.0 |  |
| File > Open Remote > Stop Remote Command | python-tk/vs | disabled |  | 0.0 |  |
| File > Recent Projects and Solutions > (no recent projects) | none/vs | disabled |  | 0.0 |  |
| File > Save | none/vs | disabled |  | 0.0 |  |
| Flask > Stop Running Command | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | none/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Bottoms | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Bottoms | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | web/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | game/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Bottoms | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | none/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Centers | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Centers | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | web/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | game/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Centers | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | none/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Lefts | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Lefts | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | web/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | game/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Lefts | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | none/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Middles | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Middles | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | web/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | game/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Middles | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | none/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Rights | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Rights | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | web/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | game/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Rights | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | none/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > Tops | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > Tops | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | web/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | flask/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | retro/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | dos/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | game/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | asm/vs | disabled |  | 0.0 |  |
| Format > Align > Tops | firmware/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | python-tk/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | none/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Align > to Grid | python-tk/agent | disabled |  | 0.0 |  |
| Format > Align > to Grid | vb6/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | csharp/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | web/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | flask/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | flutter/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | retro/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | dos/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | game/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | asm/vs | disabled |  | 0.0 |  |
| Format > Align > to Grid | firmware/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | python-tk/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | none/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | python-tk/agent | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | vb6/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | csharp/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | web/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | flask/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | flutter/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | retro/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | dos/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | game/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | asm/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Horizontally | firmware/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | python-tk/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | none/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | python-tk/agent | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | vb6/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | csharp/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | web/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | flask/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | flutter/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | retro/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | dos/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | game/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | asm/vs | disabled |  | 0.0 |  |
| Format > Center in Form > Vertically | firmware/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | python-tk/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | none/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | python-tk/agent | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | vb6/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | csharp/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | web/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | flask/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | flutter/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | retro/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | dos/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | game/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | asm/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Decrease | firmware/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | python-tk/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | none/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | python-tk/agent | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | vb6/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | csharp/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | web/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | flask/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | flutter/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | retro/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | dos/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | game/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | asm/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Increase | firmware/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | python-tk/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | none/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | python-tk/agent | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | vb6/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | csharp/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | web/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | flask/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | flutter/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | retro/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | dos/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | game/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | asm/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Make Equal | firmware/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | python-tk/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | none/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | python-tk/agent | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | vb6/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | csharp/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | web/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | flask/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | flutter/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | retro/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | dos/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | game/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | asm/vs | disabled |  | 0.0 |  |
| Format > Horizontal Spacing > Remove | firmware/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | python-tk/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | none/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Lock Controls | python-tk/agent | disabled |  | 0.0 |  |
| Format > Lock Controls | vb6/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | csharp/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | web/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | flask/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | flutter/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | retro/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | dos/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | game/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | asm/vs | disabled |  | 0.0 |  |
| Format > Lock Controls | firmware/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | python-tk/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | none/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | python-tk/agent | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | vb6/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | csharp/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | web/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | flask/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | flutter/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | retro/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | dos/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | game/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | asm/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Both | firmware/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | python-tk/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | none/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | python-tk/agent | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | vb6/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | csharp/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | web/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | flask/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | flutter/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | retro/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | dos/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | game/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | asm/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Height | firmware/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | python-tk/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | none/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | python-tk/agent | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | vb6/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | csharp/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | web/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | flask/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | flutter/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | retro/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | dos/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | game/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | asm/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Size to Grid | firmware/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | python-tk/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | none/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | python-tk/agent | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | vb6/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | csharp/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | web/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | flask/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | flutter/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | retro/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | dos/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | game/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | asm/vs | disabled |  | 0.0 |  |
| Format > Make Same Size > Width | firmware/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | python-tk/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | none/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | python-tk/agent | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | vb6/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | csharp/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | web/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | flask/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | flutter/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | retro/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | dos/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | game/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | asm/vs | disabled |  | 0.0 |  |
| Format > Order > Bring to Front | firmware/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | python-tk/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | none/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Order > Send to Back | python-tk/agent | disabled |  | 0.0 |  |
| Format > Order > Send to Back | vb6/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | csharp/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | web/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | flask/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | flutter/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | retro/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | dos/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | game/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | asm/vs | disabled |  | 0.0 |  |
| Format > Order > Send to Back | firmware/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | python-tk/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | none/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | python-tk/agent | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | vb6/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | csharp/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | web/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | flask/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | flutter/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | retro/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | dos/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | game/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | asm/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Decrease | firmware/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | python-tk/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | none/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | python-tk/agent | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | vb6/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | csharp/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | web/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | flask/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | flutter/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | retro/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | dos/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | game/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | asm/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Increase | firmware/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | python-tk/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | none/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | python-tk/agent | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | vb6/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | csharp/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | web/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | flask/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | flutter/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | retro/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | dos/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | game/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | asm/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Make Equal | firmware/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | python-tk/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | none/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | python-tk/vscode | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | python-tk/agent | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | vb6/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | csharp/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | web/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | flask/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | flutter/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | retro/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | dos/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | game/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | asm/vs | disabled |  | 0.0 |  |
| Format > Vertical Spacing > Remove | firmware/vs | disabled |  | 0.0 |  |
| Game > Add Sprite from Image | game/vs | disabled |  | 0.0 |  |
| Game > Check Scene | game/vs | disabled |  | 0.0 |  |
| Game > Import Sound | game/vs | disabled |  | 0.0 |  |
| Game > Import Tileset | game/vs | disabled |  | 0.0 |  |
| Game > Play Scene (Ctrl+F5) | game/vs | disabled |  | 0.0 |  |
| Game > Sprite Sheet and Animations | game/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | python-tk/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | none/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Add 3D Scene | python-tk/agent | disabled |  | 0.0 |  |
| Project > Add 3D Scene | vb6/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | csharp/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | web/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | flask/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | flutter/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | retro/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | dos/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | game/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | asm/vs | disabled |  | 0.0 |  |
| Project > Add 3D Scene | firmware/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | python-tk/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | none/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | python-tk/agent | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | vb6/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | csharp/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | web/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | flask/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | retro/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | dos/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | game/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | asm/vs | disabled |  | 0.0 |  |
| Project > Add New Screen (Flutter designer) | firmware/vs | disabled |  | 0.0 |  |
| Project > Add Windows Form | none/vs | disabled |  | 0.0 |  |
| Project > BASIC Commands > Stop Running Command | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Analyze (workbench) | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build ECU Project | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build Settings | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Build in Workbench | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Checksums | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Compare with Original (workbench) | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Edit Working Copy | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Modification Report | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Export Patch (IPS / BPS) | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Find Maps (workbench) | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Import Patch | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Build Output | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Open Workbench | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Set Original | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Verify Checksums (workbench) | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > Versions | asm/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | none/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | vb6/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | csharp/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | web/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | flask/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | flutter/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | retro/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | dos/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | game/vs | disabled |  | 0.0 |  |
| Project > ECU Project > View Original (read-only) | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Analyze | firmware/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Make Working Copy | firmware/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Labels | firmware/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Open Notes | firmware/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Set Original | firmware/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | python-tk/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | none/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | python-tk/agent | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | vb6/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | csharp/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | web/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | flask/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | flutter/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | retro/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | dos/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | game/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | asm/vs | disabled |  | 0.0 |  |
| Project > Firmware Analysis > Verify Original | firmware/vs | disabled |  | 0.0 |  |
| Project > Flask Commands > Stop Running Command | flask/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | python-tk/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | none/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Flutter App Theme | python-tk/agent | disabled |  | 0.0 |  |
| Project > Flutter App Theme | vb6/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | csharp/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | web/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | flask/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | retro/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | dos/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | game/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | asm/vs | disabled |  | 0.0 |  |
| Project > Flutter App Theme | firmware/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | python-tk/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | none/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Flutter Assets | python-tk/agent | disabled |  | 0.0 |  |
| Project > Flutter Assets | vb6/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | csharp/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | web/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | flask/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | retro/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | dos/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | game/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | asm/vs | disabled |  | 0.0 |  |
| Project > Flutter Assets | firmware/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | python-tk/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | none/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | python-tk/agent | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | vb6/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | csharp/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | web/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | flask/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | retro/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | dos/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | game/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | asm/vs | disabled |  | 0.0 |  |
| Project > Flutter Fonts (Google Fonts) | firmware/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | python-tk/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | none/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | python-tk/agent | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | vb6/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | csharp/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | web/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | flask/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | retro/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | dos/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | game/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | asm/vs | disabled |  | 0.0 |  |
| Project > Import Flutter Screen from Dart | firmware/vs | disabled |  | 0.0 |  |
| Project > Python Commands > Stop Running Command | python-tk/vs | disabled |  | 0.0 |  |
| Project > Python Commands > Stop Running Command | python-tk/vscode | disabled |  | 0.0 |  |
| Project > Python Commands > Stop Running Command | python-tk/agent | disabled |  | 0.0 |  |
| Project > Python Commands > Stop Running Command | flask/vs | disabled |  | 0.0 |  |
| Project > Python Commands > Stop Running Command | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Add Patch | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Build Patched ROM | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Capture Edits as Patch | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Edit Working Copy | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Open Build Output | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Patch Manager | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > Set Source ROM | firmware/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | python-tk/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | none/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | python-tk/vscode | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | python-tk/agent | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | vb6/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | csharp/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | web/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | flask/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | flutter/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | retro/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | dos/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | game/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | asm/vs | disabled |  | 0.0 |  |
| Project > ROM Hacking > View Source ROM (read-only) | firmware/vs | disabled |  | 0.0 |  |
| Project > pygame Commands > Stop Running Command | game/vs | disabled |  | 0.0 |  |
| Python > Stop Running Command | python-tk/vs | disabled |  | 0.0 |  |
| Share > Copy Invite Link | python-tk/vs | disabled |  | 0.0 |  |
| Share > End Collaboration Session | python-tk/vs | disabled |  | 0.0 |  |
| Share > Follow Participant > (no session) | python-tk/vs | disabled |  | 0.0 |  |
| Share > Guests Read-only | python-tk/vs | disabled |  | 0.0 |  |
| Share > Save Shared File on Host | python-tk/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | python-tk/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | none/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | python-tk/vscode | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | python-tk/agent | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | vb6/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | csharp/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | web/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | flutter/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | retro/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | dos/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | game/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | asm/vs | disabled |  | 0.0 |  |
| Site > Build Production (npm run build) | firmware/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | python-tk/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | none/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | python-tk/vscode | disabled |  | 0.0 |  |
| Site > Open in Browser | python-tk/agent | disabled |  | 0.0 |  |
| Site > Open in Browser | vb6/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | csharp/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | flutter/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | retro/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | dos/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | game/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | asm/vs | disabled |  | 0.0 |  |
| Site > Open in Browser | firmware/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | python-tk/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | none/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | python-tk/vscode | disabled |  | 0.0 |  |
| Site > Restart Web Server | python-tk/agent | disabled |  | 0.0 |  |
| Site > Restart Web Server | vb6/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | csharp/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | web/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | flask/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | flutter/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | retro/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | dos/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | game/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | asm/vs | disabled |  | 0.0 |  |
| Site > Restart Web Server | firmware/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | python-tk/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | none/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | python-tk/vscode | disabled |  | 0.0 |  |
| Site > Run Site in Preview | python-tk/agent | disabled |  | 0.0 |  |
| Site > Run Site in Preview | vb6/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | csharp/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | flutter/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | retro/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | dos/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | game/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | asm/vs | disabled |  | 0.0 |  |
| Site > Run Site in Preview | firmware/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | python-tk/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | none/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | python-tk/vscode | disabled |  | 0.0 |  |
| Site > Stop Web Server | python-tk/agent | disabled |  | 0.0 |  |
| Site > Stop Web Server | vb6/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | csharp/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | web/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | flask/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | flutter/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | retro/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | dos/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | game/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | asm/vs | disabled |  | 0.0 |  |
| Site > Stop Web Server | firmware/vs | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | python-tk/vs | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | python-tk/vscode | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | python-tk/agent | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | vb6/vs | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | csharp/vs | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | flutter/vs | disabled |  | 0.0 |  |
| Solution Explorer > (code) > Set as Startup Form | asm/vs | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | python-tk/vs | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | python-tk/vscode | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | python-tk/agent | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | vb6/vs | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | csharp/vs | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | flutter/vs | disabled |  | 0.0 |  |
| Solution Explorer > (design) > Set as Startup Form | asm/vs | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | python-tk/vs | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | python-tk/vscode | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | python-tk/agent | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | vb6/vs | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | csharp/vs | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | flutter/vs | disabled |  | 0.0 |  |
| Solution Explorer > (generated) > Set as Startup Form | asm/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | python-tk/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | python-tk/vscode | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | python-tk/agent | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | vb6/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | csharp/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | web/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | flask/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | flutter/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | retro/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | dos/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | game/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | asm/vs | disabled |  | 0.0 |  |
| Solution Explorer > (project) > Set as StartUp Project | firmware/vs | disabled |  | 0.0 |  |
| Toolbar Debug > Step Into | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Debug > Step Out | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Debug > Step Over | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Debug > Toggle Breakpoint | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Expo > Close the Emulator | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Expo > Open in Browser | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Mobile > Hot Reload | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Mobile > Hot Restart | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Project Actions > Stop Running Command | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Standard > Design | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Standard > Redo | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Standard > Split | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Standard > Stop Debugging | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Standard > Undo | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Add New Data Source | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Configure Data Source | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Local Servers > Start local MariaDB/MySQL | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Local Servers > Start local PostgreSQL | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Preview Data | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Redo (Ctrl+Y) | game/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Refresh (re-read the columns and rows) | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Remove Data Source | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Stop | python-tk/vs | disabled |  | 0.0 |  |
| Toolbar Toolbar > Undo (Ctrl+Z) | game/vs | disabled |  | 0.0 |  |
| Tools > Car Connection > Disconnect | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Databases > Local Servers > Start local MariaDB/MySQL | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Databases > Local Servers > Start local PostgreSQL | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Image Editor > Add to Project Resources | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Image Editor > Set as Application Icon | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Image Editor > Set as Form Icon | python-tk/vs | disabled |  | 0.0 |  |
| Tools > NuGet Package Manager > Manage NuGet Packages for Solution | python-tk/vs | disabled |  | 0.0 |  |
| Tools > Retro > Game Designers > New Design for This Project | python-tk/vs | disabled |  | 0.0 |  |
| View > AI Web Chats (dock) | python-tk/vs | disabled |  | 0.0 |  |
| View > Design | python-tk/vs | disabled |  | 0.0 |  |
| View > Layout > Toggle Panel | python-tk/vs | disabled |  | 0.0 |  |
| View > Layout > Toggle Side Bar | python-tk/vs | disabled |  | 0.0 |  |
| Window > Auto Hide | python-tk/vs | disabled |  | 0.0 |  |
| pygame > Stop Running Command | game/vs | disabled |  | 0.0 |  |
| Designer > (control) > AI > Generate Event Handler for AppBar1 | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate Event Handler for Button1 | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate Event Handler for Button1 | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate Event Handler for lblMessage | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate Event Handler for lblName | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate Event Handler for lblYourName | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Generate New Form with AI | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > AI > Redesign This Form with AI | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Bounce | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Flip | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Move | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Pulse | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Rotate | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Shake | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Attention > Zoom | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Color > Color | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Fade In | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Slide In | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Entrance > Zoom In | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Add Animation > Text > Typewriter | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Bring to Front | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Bring to Front | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Bring to Front | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Bring to Front | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Copy | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Cut | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Cut | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Cut | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Cut | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Delete | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > Click | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > Click | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > Click | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > Click | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > Click | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > DoubleClick | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > DoubleClick | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > DoubleClick | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > DoubleClick | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > GotFocus | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > GotFocus | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > GotFocus | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > GotFocus | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyDown | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyDown | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyDown | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyDown | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyPress | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyPress | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyPress | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyPress | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyUp | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyUp | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyUp | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > KeyUp | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > LostFocus | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > LostFocus | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > LostFocus | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > LostFocus | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseDown | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseDown | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseDown | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseDown | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseEnter | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseEnter | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseEnter | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseEnter | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseLeave | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseLeave | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseLeave | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseLeave | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseMove | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseMove | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseMove | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseMove | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseUp | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseUp | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseUp | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseUp | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseWheel | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseWheel | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseWheel | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Events > MouseWheel | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Add Size | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > All sizes | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > Base design | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Layout Size > This size only | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Lock Controls | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Paste | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | flutter/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Properties | asm/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Send to Back | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Send to Back | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Send to Back | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > Send to Back | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > View Code | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > View Code | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > View Code | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (control) > View Code | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate Event Handler for Form1 | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate Event Handler for Form1 | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate Event Handler for Form1 | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate Event Handler for frmGreeter | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate New Form with AI | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate New Form with AI | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate New Form with AI | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Generate New Form with AI | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Redesign This Form with AI | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Redesign This Form with AI | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Redesign This Form with AI | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > AI > Redesign This Form with AI | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Bounce | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Bounce | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Bounce | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Bounce | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Flip | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Flip | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Flip | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Flip | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Move | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Move | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Move | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Move | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Pulse | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Pulse | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Pulse | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Pulse | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Rotate | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Rotate | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Rotate | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Rotate | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Shake | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Shake | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Shake | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Shake | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Zoom | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Zoom | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Zoom | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Attention > Zoom | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Color > Color | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Color > Color | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Color > Color | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Color > Color | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Fade In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Fade In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Fade In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Fade In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Slide In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Slide In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Slide In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Slide In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Zoom In | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Zoom In | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Zoom In | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Entrance > Zoom In | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Text > Typewriter | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Text > Typewriter | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Text > Typewriter | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Animation > Text > Typewriter | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Windows Form | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Windows Form | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Windows Form | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Add Windows Form | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Copy | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Copy | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Copy | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Copy | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Cut | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Cut | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Cut | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Cut | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Delete | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Delete | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Delete | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Delete | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Activated | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Activated | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Activated | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Activated | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Click | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Click | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Click | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Click | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Deactivate | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Deactivate | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Deactivate | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Deactivate | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > DoubleClick | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > DoubleClick | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > DoubleClick | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > DoubleClick | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosed | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosed | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosed | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosed | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosing | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosing | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosing | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > FormClosing | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyDown | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyDown | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyDown | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyDown | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyPress | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyPress | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyPress | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyPress | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyUp | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyUp | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyUp | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > KeyUp | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Load | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Load | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Load | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Load | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseDown | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseDown | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseDown | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseDown | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseMove | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseMove | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseMove | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseMove | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseUp | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseUp | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseUp | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseUp | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseWheel | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseWheel | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseWheel | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > MouseWheel | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Resize | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Resize | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Resize | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Events > Resize | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Add Size | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Add Size | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Add Size | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Add Size | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > All sizes | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > All sizes | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > All sizes | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > All sizes | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Base design | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Base design | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Base design | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > Base design | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > This size only | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > This size only | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > This size only | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Layout Size > This size only | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Lock Controls | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Lock Controls | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Lock Controls | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Lock Controls | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Paste | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Paste | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Paste | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Paste | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Properties | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Properties | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Properties | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Properties | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Select All | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Select All | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Select All | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > Select All | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > View Code | python-tk/vscode | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > View Code | python-tk/agent | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > View Code | vb6/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Designer > (form) > View Code | csharp/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Copy | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Go To Offset | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Open in Map Editor | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Paste | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Select All | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| HexView (HexView) > Toggle Bookmark | firmware/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |
| Python > Create .venv | python-tk/vs | stale |  | 0.0 | wrapped C/C++ object of type QAction has been deleted |

## Dialogs with interactive controls that have no accessible name

* **Add Existing Item [QFileDialog]**: QHeaderView:?
* **Add Existing Project [QFileDialog]**: QHeaderView:?
* **Analyze Firmware File [QFileDialog]**: QHeaderView:?
* **App Gallery [AppGalleryDialog]**: QListWidget:?
* **Assembly Toolchains [AsmToolchainsDialog]**: QHeaderView:?, QPlainTextEdit:?
* **Attach to Process [AttachDialog]**: QHeaderView:?, QTreeWidget:?
* **Checksum Toolkit - demo_ecu_mod.bin [ChecksumDialog]**: QAbstractButton:qt_tableview_cornerbutton
* **Checksum Toolkit [QFileDialog]**: QHeaderView:?
* **Checksums - CrawlEcu [ChecksumDialog]**: QAbstractButton:qt_tableview_cornerbutton
* **Choose Toolbox Items [ChooseItemsDialog]**: QHeaderView:?, QTableWidget:?
* **Code Snippets Manager [SnippetsDialog]**: QListWidget:?
* **Compare Files - first (left) file [QFileDialog]**: QHeaderView:?
* **Compare: file A (editable) [QFileDialog]**: QHeaderView:?
* **Compare: first file [QFileDialog]**: QHeaderView:?
* **Compare: original / first file [QFileDialog]**: QHeaderView:?
* **Component Packages [ComponentManagerDialog]**: QHeaderView:?, QPlainTextEdit:?, QTableWidget:?
* **Connect to Car [ConnectDialog]**: QPlainTextEdit:?
* **Create a new project [NewProjectWizard]**: QComboBox:?, QListWidget:templateList
* **DOS Interrupt Reference [InterruptReference]**: QHeaderView:?, QTextBrowser:?, QTreeWidget:?
* **DOS Toolchains [DosToolchainsDialog]**: QHeaderView:?, QPlainTextEdit:?
* **DSKY Verbs, Nouns and Programs [QDialog]**: QHeaderView:?
* **Debug ROM in Emulator [QFileDialog]**: QHeaderView:?
* **Disassemble ROM into Project [DisassembleDialog]**: QPlainTextEdit:?
* **Find Control Units [FindEcusDialog]**: QAbstractButton:qt_tableview_cornerbutton, QHeaderView:?, QTableWidget:?
* **Find Maps in a Binary [QFileDialog]**: QHeaderView:?
* **Firmware Converter [FirmwareConverterDialog]**: QPlainTextEdit:?
* **Fix Header Checksum [QFileDialog]**: QHeaderView:?
* **Folder with .devcontainer [QFileDialog]**: QHeaderView:?
* **Generate Docker Files [DockerGenerateDialog]**: QHeaderView:?, QTreeWidget:?
* **Generate Form with AI [GenerateFormDialog]**: QListWidget:?
* **Google Fonts [FontPickerDialog]**: QComboBox:?, QListWidget:?
* **Import Python GUI Program [QFileDialog]**: QHeaderView:?
* **Import Python Script as Notebook [QFileDialog]**: QHeaderView:?
* **Import Visual Basic 6 Project [QFileDialog]**: QHeaderView:?
* **Import a Flutter screen [QFileDialog]**: QHeaderView:?
* **Language Servers and Debuggers [LanguageServersDialog]**: QHeaderView:?
* **Localization - Form1 [QDialog]**: QAbstractButton:qt_tableview_cornerbutton, QTableWidget:?
* **Localization - MainScreen [QDialog]**: QAbstractButton:qt_tableview_cornerbutton, QTableWidget:?
* **Locate Python (Tkinter) interpreter [QFileDialog]**: QHeaderView:?
* **Macro Explorer [MacroExplorer]**: QListWidget:?, QPlainTextEdit:?, QSpinBox:?
* **Manage Packages - EvDemo [PackagesDialog]**: QHeaderView:?, QPlainTextEdit:?
* **Manage Packages - Flask_Todo [PackagesDialog]**: QPlainTextEdit:?
* **Manage Packages - IdeProj [PackagesDialog]**: QPlainTextEdit:?
* **Manage Packages - Platformer [PackagesDialog]**: QPlainTextEdit:?
* **New ECU Project: choose the original file [QFileDialog]**: QHeaderView:?
* **New Notebook [QFileDialog]**: QHeaderView:?
* **New Table [CreateTableDialog]**: QAbstractButton:qt_tableview_cornerbutton
* **Open Binary [QFileDialog]**: QHeaderView:?
* **Open Binary in Map Editor [QFileDialog]**: QHeaderView:?
* **Open EEPROM Dump (read-only) [QFileDialog]**: QHeaderView:?
* **Open File [QFileDialog]**: QHeaderView:?
* **Open Firmware in Workbench [QFileDialog]**: QHeaderView:?
* **Open Folder [QFileDialog]**: QHeaderView:?
* **Open Game Design [QFileDialog]**: QHeaderView:?
* **Open Image [QFileDialog]**: QHeaderView:?
* **Open Notebook [QFileDialog]**: QHeaderView:?
* **Open Project/Solution [QFileDialog]**: QHeaderView:?
* **Open ROM / Binary in the Tile Editor [QFileDialog]**: QHeaderView:?
* **Open Screen or Art [QFileDialog]**: QHeaderView:?
* **Open Text Table [QFileDialog]**: QHeaderView:?
* **Open Tune (msq) [QFileDialog]**: QHeaderView:?
* **Open in Design View [QFileDialog]**: QHeaderView:?
* **Open in Hex Editor [QFileDialog]**: QHeaderView:?
* **Options [OptionsDialog]**: QHeaderView:?
* **PHP Versions [PhpVersionsDialog]**: QHeaderView:?, QTreeWidget:?
* **Project Assets [AssetManagerDialog]**: QComboBox:?, QListWidget:?
* **Publish - EvDemo [PublishDialog]**: QHeaderView:?
* **RAD IDE Help [HelpViewer]**: QTextBrowser:?
* **ROM Info [QFileDialog]**: QHeaderView:?
* **Redesign Form with AI [GenerateFormDialog]**: QListWidget:?
* **Retro Emulators [EmulatorManager]**: QHeaderView:?, QPlainTextEdit:?
* **Retro Toolchains [RetroToolchainsDialog]**: QHeaderView:?, QPlainTextEdit:?
* **Run ROM in Emulator [QFileDialog]**: QHeaderView:?
* **Save Art [QFileDialog]**: QHeaderView:?
* **SuperPreview [SuperPreview]**: QComboBox:?, QSpinBox:?
* **Versions - CrawlEcu [VersionsDialog]**: QAbstractButton:qt_tableview_cornerbutton, QPlainTextEdit:?, QTableWidget:?
* **أمثلة المشاريع [ExampleGallery]**: QHeaderView:?, QTextBrowser:?, QTreeWidget:?
* **إضافة عنصر موجود [QFileDialog]**: QHeaderView:?
* **إضافة مشروع موجود [QFileDialog]**: QHeaderView:?
* **التثبيت من ملف VSIX [QFileDialog]**: QHeaderView:?
* **فتح برنامج ويندوز (منضدة PE / MFC) [QFileDialog]**: QHeaderView:?
* **فتح مشروع/حل [QFileDialog]**: QHeaderView:?
* **قاعدة بيانات SQLite جديدة [QFileDialog]**: QHeaderView:?
