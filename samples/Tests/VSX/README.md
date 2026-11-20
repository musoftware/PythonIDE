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
