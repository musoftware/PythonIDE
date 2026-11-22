# VSX (VS Code extensions / Open VSX) tests

## Market (install / registry / Extensions view) - `test_vsx_market.py`

    python samples\Tests\VSX\test_vsx_market.py [out_dir] [--onscreen]

Runs against the real https://open-vsx.org (network required) with a real `MainWindow`.
Everything is installed into a temporary folder (`RADIDE_VSX_ROOT`); QSettings use `RADIDE-TEST` and are
cleared at the end. `--onscreen` gives meaningful `widget.grab()` screenshots (the offscreen platform has
no fonts). Checks (57): engines.vscode ranges against the emulated API level (`radide.vsx.API_LEVEL`),
safe .vsix unpacking (path traversal, absolute paths, device names, symlinks refused), package.nls
localisation (English / Arabic), search + paging + categories, the Extensions view and details page,
installs, dependencies, uninstall, Install from VSIX, enable / disable events, update check + update,
offline cache.

Extensions the test downloads (nothing is committed; all are small):

| Extension | Why |
|---|---|
| `dracula-theme.theme-dracula` 2.24.2, then updated to the latest | a colour theme; update check |
| `xabikos.JavaScriptSnippets` | a snippet pack (engines `0.10.x` - legacy range) |
| `dunstontc.viml` | a language + TextMate grammar pack |
| `mtxr.sqltools-driver-sqlite` | an extension with `extensionDependencies` (pulls `mtxr.sqltools`; uninstalling the driver removes the orphan) |
| `redhat.vscode-yaml` (registry query only) | latest needs `^1.91`; the newest compatible older version is picked |

### `hello-vsx/extension`

A tiny test extension (MIT, written for these tests): `package.json` with `%key%` strings,
`package.nls.json` + `package.nls.ar.json` (Arabic), a Python snippet (`hellomain`), a dark colour theme,
a `configuration` setting, icon, README and CHANGELOG, and `extensionDependencies` on
`dracula-theme.theme-dracula`. The test packs it into a .vsix at run time with
`radide.vsx.package.pack_vsix()` and installs it with Install from VSIX (the dependency comes from Open VSX).

## Declarative contributions (themes / grammars / languages / snippets / icons / keys / settings) - `test_vsx_contrib.py`

    python samples\Tests\VSX\test_vsx_contrib.py [out_dir] [--onscreen]

Code under test: `radide/vsx/contrib_*.py` and `radide/web/vsx/vsx-contrib.js` (TextMate tokenising in Monaco
with the bundled vscode-textmate 9.3.2 + vscode-oniguruma 2.0.1, both MIT - licences next to them in
`radide/web/vsx/`). Real `MainWindow`, scratch `RADIDE_VSX_ROOT`, `RADIDE-TEST` QSettings (cleared at the end).
Offscreen runs point `QT_QPA_FONTDIR` at `C:\Windows\Fonts` so the screenshots have readable text.
The .vsix files are cached in `%LOCALAPPDATA%\RADIDE\tools\vsx-test-cache` (nothing is committed).
Checks (50): JSONC + colour helpers; theme `include` + `semanticTokenColors`; Dracula applied at start-up to
the whole IDE (palette, style sheet, status bar) and to Monaco (editor background, comment colour of TextMate
tokens); TOML opens as `toml` (file extension + `Cargo.lock` file name), grammar scopes, language
configuration (toggle line comment uses `#`); a grammar injection; keybindings to a Monaco command (with a
`resourceExtname` when clause) and to an IDE command with args; snippets (array prefixes, insertion, suggest
widget); switching to One Dark Pro, to the built-in Dark theme (Dark+ colours for TextMate tokens) and to a
light VS Code theme; Options "VS Code Extensions" page (settings form per extension -> `<vsx root>\settings.json`);
Material icons in Solution Explorer (website folder tree); disable / enable refreshes themes and icons.

| Extension (Open VSX, MIT) | Why |
|---|---|
| `dracula-theme.theme-dracula` | colour theme -> Monaco theme + IDE chrome (screenshots `02_*`) |
| `zhuangtongfa.material-theme` | One Dark Pro: theme switching (`05_*`) |
| `nifty.nifty-toml` | TOML language + TextMate grammar + language-configuration (its code part needs the host) |
| `xabikos.JavaScriptSnippets` | snippet pack (`04_*`) |
| `PKief.material-icon-theme` | SVG file icon theme -> Solution Explorer (`01_*`) |

### `contrib-test/extension`

A small declarative-only test extension (MIT, written for these tests): language `radtest` (`.radt`,
`Radtestfile`) with a JSONC `language-configuration.json`, a TextMate grammar plus an injection grammar
(`TODO` inside comments), a light colour theme that `include`s a base theme and has `semanticTokenColors`,
snippets with array prefixes, three keybindings (Monaco command with a when clause, IDE command with args, a
chord) and a `configuration` with boolean / enum / string / integer / number / array settings. The test zips
it into a .vsix at run time.

Font-glyph icon themes (e.g. `file-icons.file-icons`) work too; their WOFF2 fonts are converted to TTF with
fontTools and need the optional `brotli` module (without it those glyphs fall back to the IDE's icons).

## Extension host (extension code: commands, providers, language servers, debuggers) - `test_vsx_host.py`

    python samples\Tests\VSX\test_vsx_host.py <scratch folder>

Code under test: `radide/vsx/host/*.js` (the Node extension host and its `vscode` API), `radide/vsx/bridge.py`
(JSON-RPC), `radide/vsx/host_ide.py` (IDE wiring), `radide/vsx/lsp_client.py`, `radide/vsx/debuggers.py`,
`radide/vsx/lsp_fallback.py`, `radide/vsx/when.py`. Real `MainWindow`, `RADIDE_VSX_ROOT` = `<scratch>\vsx_host_test\vsxroot`,
`RADIDE-TEST` QSettings (cleared at the end). Needs Node.js and npm (npm installs `vscode-languageclient@9.0.1`,
`vscode-languageserver@9.0.1`, `vscode-languageserver-textdocument@1.0.12` - all MIT - into the scratch copy of
`mini-lsp`; nothing is committed). Dialogs are answered by a timer (the real QMessageBox / quick pick / input
box widgets are used). Screenshots `vsx_host_*.png` (widget.grab()). Checks (56): activation events
(onStartupFinished, onLanguage, onCommand, onDebug), contributed commands in the Command Palette, status bar
item, message box with items, quick pick, input box with validateInput, configuration update + change event,
completion (snippet item), hover, definition, formatting, diagnostics (Monaco markers), code actions + their
WorkspaceEdit, registerTextEditorCommand + TextEditorEdit, document events, an unsupported API failing softly,
editor/context menu, tree view in a dock (children + item command with arguments), the vscode-languageclient
extension (diagnostics / completion / hover from its server), F5 with a declarative debugger (breakpoint, stack,
locals), an inline debug adapter served by the host (relay.js), debug events reaching the extension, and the LSP
fallback (the extension's server run by `radide/lsp.py`).

These test extensions are written for RAD IDE (MIT) and packed into .vsix files at run time:

| Folder | What it exercises |
|---|---|
| `hello-commands` | commands, status bar, messages, quick pick, input box, output channel, configuration, globalState, document events, completion / hover / definition / formatting / code action providers, a diagnostic collection, `setLanguageConfiguration`, a tree view, editor/context + commandPalette menus with `when`, an unsupported (proposed) API, `createWebviewTextEditorInset` |
| `mini-lsp` | the standard `vscode-languageclient/node` client (`TransportKind.ipc`) + a `vscode-languageserver` server (`server.js`): completion, hover, push diagnostics, formatting; language `minilang` (`.mini`) |
| `mini-debug` | `contributes.debuggers` with `program` + `runtime: node` (`adapter.js`, a tiny DAP adapter), a configuration provider filling an empty configuration from the active editor, a `${command:PickProgram}` variable, an inline adapter (`DebugAdapterInlineImplementation`, setting `miniDebug.inline`), custom DAP events |

Real Open VSX extensions: the host was not run with downloaded third-party extension code in this test (the
agent's sandbox did not allow executing it). A static scan of `redhat.vscode-yaml` 2.1, `christian-kohler.path-intellisense`
2.8 and `ms-vscode.mock-debug` 0.52 found that every `vscode.*` API member they reference is implemented by
`radide/vsx/host/api.js`; `radide/vsx/lsp_fallback.py` finds the YAML server (`dist/languageserver.js`). Try them
from the Extensions view (Open VSX) - their output goes to View > Extension Output.

## QA through the real IDE, like a user - `test_vsx_qa.py`

    python samples\Tests\VSX\test_vsx_qa.py <out_dir> [--onscreen]

Starts `MainWindow` with an **empty** scratch `RADIDE_VSX_ROOT` (and a scratch `RADIDE_EXTENSIONS_DIR` holding the
IDE's own sample extensions from `samples/Tests/Extensions`) and does everything live through the UI: Ctrl+Shift+X,
typing a search, clicking **Install** on the Open VSX cards (Dracula, One Dark Pro, nifty TOML, JavaScript (ES6)
snippets, Material Icon Theme), **Uninstall** on the Installed tab, the details tab, choosing Dracula in
Tools > Options (IDE chrome + Monaco), TOML grammar colours, the `clg` snippet in the suggest widget, Material icons
in Solution Explorer, **Install from VSIX** of `hello-commands` and `mini-lsp` -> "Restart required" banner ->
**Reload** starts the extension host -> the command runs from the Command Palette and from its status bar item ->
language-server diagnostics (Monaco markers) and completions (suggest widget); the IDE's own Extensions dialog;
the Arabic UI (no English UI words in the Extensions view / details page; extension content such as a
description "Snippets" is *not* translated). Writes `extension_host_log.txt` (activations of the real Open VSX
extensions with code: `nifty.nifty-toml`, `pkief.material-icon-theme`) and `arabic_missing.json`.
QSettings: organisation `RADIDE-TEST`, application `RADIDE-TEST-VSXQA` (own registry key, so another test that
clears `RADIDE-TEST\RADIDE-TEST` at the same time cannot wipe the theme setting mid-run); cleared at the end.
Use `--onscreen` for screenshots of Monaco (offscreen `widget.grab()` of web views is blank).
Checks: 61.

## Workbench APIs (the former no-op mocks) - `test_vsx_workbench.py`

    python samples\Tests\VSX\test_vsx_workbench.py <out_dir> [Claude Code extension folder or .vsix]

Code under test: `radide/vsx/host/workbench.js` (FileSystemProvider registry + `workspace.fs` routing, `window.tabGroups`,
`vscode.diff`, process / Pseudoterminal terminals with shell integration), `radide/vsx/host/services.js` (URI handlers,
file decorations, authentication, tasks, custom editors, notebooks, comments / tests / scm / chat objects) and
`radide/vsx/workbench_ui.py` (Diff tabs with the extensions' `editor/title` buttons, editable temp copies of virtual
documents, the "Extension Terminals" dock, Extensions > Open Extension URI..., decorations on editor tabs, Monaco
visible ranges). Test extension `workbench-api/` (MIT, written for this test). With a Claude Code extension (an
unpacked folder is packed without its 370 MB CLI binary) the test also plays the CLI: `claude_open_diff.js` reads the
extension's lock file (`CLAUDE_CONFIG_DIR` is a scratch folder), calls the MCP tool `openDiff`, clicks
"Accept Proposed Changes" on the Diff tab, expects `FILE_SAVED` + the contents, then calls `close_tab`.
Scratch `RADIDE_VSX_ROOT`, `RADIDE-TEST` QSettings (cleared at the end), `RADIDE_NO_BROWSER=1`, `widget.grab()` only.
Checks: 74 (86 with Claude Code).

## VS Code reference: built-in commands, context keys, contribution points - `test_vsx_reference.py`

    python samples\Tests\VSX\test_vsx_reference.py <out_dir> [Claude Code .vsix]

Code under test: the inventories in `radide/vsx/reference/` (extracted from microsoft/vscode, see its README and
`COVERAGE.md`), `radide/vsx/host/commands.js` (API commands and workbench commands that need extension-host state,
"command 'x' not found" for unknown ids), `radide/vsx/host/treeview.js` (TreeView: handles, reveal, events,
message / title / description / badge), `radide/vsx/views_ui.py` (view containers in the activity bar / panel /
secondary side bar, tree panes, view/title and view/item/context menus, viewsWelcome, when clauses of views),
`radide/vsx/menus.py` (VS Code menu ordering, submenus, enablement, icons), `radide/vsx/context_keys.py`
(config.*, view.<id>.visible, focus keys, editorHas*Provider ...), `radide/vsx/ide_commands.py` (workbench commands
in the IDE: openSettings with a query, problems, side bar / panel / auxiliary bar toggles, extensions ...), the
editor/title bar on every editor tab (`workbench_ui.EditorTitleBar`) and the raised API level (`radide.vsx.API_LEVEL`
1.147.0: the test extension needs `^1.100.0`). Test extension `reference-test/` (MIT, written for this test).
With a Claude Code .vsix the Command Palette entries are clicked like a user would: Open in Side Bar (the view lands in
the secondary side bar), the same again after an extension-host restart with the side bar dock closed (the reported
"Open in Side Bar does nothing" case), Open in New Tab, Open in New Window (the panel floats as its own window), Focus
input, New Conversation, Show Logs, and the Claude button in the editor title bar.
Scratch `RADIDE_VSX_ROOT`, `RADIDE-TEST` QSettings (cleared before / after), `RADIDE_NO_BROWSER=1`, `widget.grab()` only.
Checks: 70 (86 with Claude Code).

## Command Palette, editor commands, keybindings, settings - `test_vsx_palette.py`

    python samples\Tests\VSX\test_vsx_palette.py <scratch>

VS Code parity of the quick input (`radide/features/command_palette.py`): `>` commands (extension commands with
category + keybinding, commandPalette `when` / `enablement` hide them until the context keys are set, VS Code's own
palette commands that RAD IDE runs from `radide/vsx/vscode_commands.py`, recently used first, fuzzy highlight), `@`
symbols (language server / plugin outline / declaration scan), `:` line, `#` workspace symbols, `view `, `task `
(`.vscode/tasks.json`, JSONC), `debug ` (`launch.json`), `ext install`, `edt `, `?`. Editor commands run on Monaco
from an extension (`vscode.commands.executeCommand('editor.action.commentLine' | 'cursorDown' | 'type' | 'undo' |
'editor.fold' | 'editor.action.toggleWordWrap' | 'actions.find' | 'workbench.action.zoomIn' ...)`) and from the IDE
(`radide/vsx/editor_commands.py`, ids in `radide/vsx/reference/monaco_commands.json`). Navigation history
(`workbench.action.navigateBack / Forward`, `radide/vsx/navigation.py`), `reopenClosedEditor`, user
`keybindings.json` with `-command` removal (`radide/vsx/user_keybindings.py`), the Keyboard Shortcuts and Settings
pages (`radide/vsx/settings_ui.py`: search, `@ext:`, `@modified`, editing), and the Extensions panel retranslating
when the UI language goes back to English. Test extension `palette-test/` (MIT). `RADIDE-TEST-VSX2` QSettings.

## Claude Code in RAD IDE (workspace, IDE MCP tools, agent context) - `test_vsx_claude.py`

    python samples\Tests\VSX\test_vsx_claude.py <scratch> <Anthropic.claude-code .vsix>

No real Claude conversation: `claude_mcp_client.js` plays the Claude CLI towards the extension's MCP WebSocket
server (lock file in a scratch `CLAUDE_CONFIG_DIR`). Checks that opening a project after start-up restarts the
extension host so Claude Code's session folder / lock file `workspaceFolders` / CLI cwd are the project folder (not
the home folder), `RADIDE_CLI` / `RADIDE_WORKSPACE` in the host environment, the RAD IDE section in
`.claude/CLAUDE.md` (user text kept), every IDE tool of Claude Code 2.1 (`getDiagnostics` with the IDE's Error List
problems, `openDiff` Accept -> `FILE_SAVED` / Reject -> `DIFF_REJECTED`, `close_tab`, `closeAllDiffTabs`,
`executeCode`), `selection_changed` when the user selects text, `at_mentioned` from Insert At-Mentioned,
`vscode.open` with a selection, and a file written on disk by the agent reaching the open editor.

## Real extensions from Open VSX (network) - `test_vsx_matrix.py`

    python samples\Tests\VSX\test_vsx_matrix.py <scratch> [ext.id ...]

NETWORK TEST. Installs popular extensions (Prettier, ESLint, Error Lens, Todo Tree, Path Intellisense, Code Spell
Checker, Live Server, Material Icon Theme, One Dark Pro, Dracula, Markdown All in One, YAML, XML, Ruff, Pyright,
Python, GitLens, Go, rust-analyzer, clangd, Java) into a scratch root, opens a multi-language project and records
installed version, activation, registered commands, a safe command run and unsupported API per extension
(`matrix.json` / `matrix.md` in the scratch folder). Skips when Open VSX is unreachable.

## Headless commands for agents - `radide/agent_cli.py`

`RADIDE.exe --check | --build | --run [--timeout S] | --publish [--native] | --info <project|solution|folder>`
(source: `python -m radide ...`) open the target like the IDE, print the Output window and exit 0 / 1.
