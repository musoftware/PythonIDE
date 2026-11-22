# VS Code reference data for RAD IDE's extension host

Machine-readable inventories of what VS Code offers extensions, extracted from the real source so that
RAD IDE implements built-in commands, context keys, contribution points and the `vscode` API from the source
instead of guessing.

**Source:** https://github.com/microsoft/vscode, commit `733a99842b0e0e14c3593dfab31fff2035478ba0`
(main, 2026-11-21, `package.json` version 1.148.0; its `vscode.d.ts` is identical to release 1.147.0).
**Licence of the source:** MIT, Copyright (c) Microsoft Corporation. The files here are data derived from it
(identifiers, signatures, English descriptions taken from the source's `localize()` strings); see
THIRD_PARTY_NOTICES.md.

| File | Contents |
|---|---|
| `commands.json` | `apiCommands`: the 59 API commands of `src/vs/workbench/api/common/extHostApiCommands.ts` (+ notebook / interactive ones) with argument names, descriptions and return descriptions; `commands`: 2,808 built-in command ids (`CommandsRegistry.registerCommand`, `registerAction2`, `KeybindingsRegistry.registerCommandAndKeybindingRule`, `MenuRegistry`, editor actions / commands, view-container open commands) with title, category, f1, precondition, default keybinding + when, menus, metadata args; `dynamicCommands`: the ids VS Code creates per view / container (`<viewId>.focus`, `.open`, `workbench.view.extension.<id>` ...) |
| `vscode_api.json` | 2,766 declarations of `src/vscode-dts/vscode.d.ts`: namespaces, functions, events, variables, classes, interfaces, enums with members and signatures; `since` = the first release (of 1.90, 1.94, 1.100, 1.106, 1.120, 1.130, 1.140, 1.147) whose vscode.d.ts has it |
| `context_keys.json` | 1,316 context keys (`new RawContextKey(...)` and `createKey(...)`) with type, default and description |
| `contribution_points.json` | 54 `ExtensionsRegistry.registerExtensionPoint` contribution points with their JSON schema (as far as it is literal), and the 98 menu ids extensions can contribute to (`apiMenus` of menusExtensionPoint.ts) |
| `usage_top_extensions.json` | how often the 200 most downloaded Open VSX extensions (package.json) and 61 extension bundles (incl. Claude Code 2.1.330's extension.js) use commands, API members, context keys, contribution points, menus - only ids and counts |
| `COVERAGE.md`, `coverage.json` | RAD IDE against the inventories: implemented / partial / missing per item, ordered by usage, with before / after numbers (`coverage_before.json` = the state before this folder existed) |

## Regenerating

    # 1. the source (sparse, no tests) + vscode.d.ts of the releases used for "since"
    git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/vscode vscode
    cd vscode && git config core.longpaths true
    git sparse-checkout set --no-cone /package.json /LICENSE.txt "/src/vs/**/*.ts" "!/src/vs/**/test/**" "/src/vscode-dts/*.ts"
    # dts/vscode-<version>.d.ts from https://raw.githubusercontent.com/microsoft/vscode/<version>/src/vscode-dts/vscode.d.ts
    # 2. extract (needs the typescript npm package next to the script; parses the AST, no type check)
    npm install typescript@5.6.3
    VSCODE_COMMIT=<sha> node radide/vsx/reference/tools/extract.js <vscode checkout> <dts dir> radide/vsx/reference
    # 3. usage of popular extensions (network: open-vsx.org)
    python -I radide/vsx/reference/tools/market_scan.py <download dir> usage.json 200 60
    # 4. coverage (runs api_probe.js with Node against radide/vsx/host)
    python radide/vsx/reference/coverage.py --snapshot radide/vsx/reference/coverage_before.json

`api_probe.js` loads the real host (`radide/vsx/host/main.js`), builds the `vscode` object an extension gets and
checks every vscode.d.ts declaration on it (and on real instances of the objects RAD IDE creates: TextDocument,
TextEditor, OutputChannel, TreeView, WebviewPanel, ...).

## Used at run time

* `radide/vsx/host/commands.js` reads `commands.json`: a command id VS Code knows but RAD IDE has no UI for
  resolves to `undefined` (like VS Code without that part); an id nobody knows rejects with
  `command 'x' not found`, as `CommandService.executeCommand` does. `commands.getCommands()` lists the built-ins.
* `radide.vsx.API_LEVEL` (`1.147.0`) is the version `vscode.version` reports and `engines.vscode` is checked
  against: every stable declaration of vscode.d.ts 1.147 exists in the host (see COVERAGE.md for the few that are
  inert because RAD IDE has no such UI).
