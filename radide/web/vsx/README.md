# radide/web/vsx - VS Code contributions inside Monaco

`vsx-contrib.js` (RAD IDE) is loaded by `../editor.html`; the Python side is `radide/vsx/contrib_runtime.py`.

Bundled third-party files (unmodified npm release builds):

| Folder | Package | Version | Licence |
|---|---|---|---|
| `vscode-textmate/` | [vscode-textmate](https://github.com/microsoft/vscode-textmate) `release/main.js` | 9.3.2 | MIT (`LICENSE.md`) |
| `vscode-oniguruma/` | [vscode-oniguruma](https://github.com/microsoft/vscode-oniguruma) `release/main.js` + `onig.wasm` | 2.0.1 | MIT (`LICENSE.txt`); Oniguruma: BSD-2-Clause (`NOTICES.txt`) |

The Dark+ / Light+ token colours used for TextMate grammars under the built-in IDE themes
(`radide/vsx/contrib_themes.py`) follow VS Code's default themes (MIT).
