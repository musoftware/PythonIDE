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
