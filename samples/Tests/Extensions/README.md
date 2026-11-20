# Example extensions

Two extensions written against the RAD IDE Plugin API ([docs/PLUGIN_API.md](../../../docs/PLUGIN_API.md)).

| Folder | Kind | What it shows |
|---|---|---|
| [`SolarizedTheme`](SolarizedTheme/) | declarative (no code) | `contributes.themes`: two colour themes (Solarized Dark based on Dark, Solarized Light based on Light) in JSON files. They appear in Tools > Options > Color theme and View > theme menus like the built-in themes. |
| [`WordCountTools`](WordCountTools/) | code (`main: extension.py`) | `activate(api)`: a **Tools > Word Count** sub-menu (Ctrl+Alt+W counts lines/words/characters of the active code file), a **Scratch Notes** dock whose text is kept in the extension's own settings, a live word count in the status bar (themed with `api.theme.role`), a timer stopped through `api.on_dispose`, and a helper sub-module imported with `from .counting import ...`. |

How to try them:

1. **Tools > Extensions...** > **Install from Folder...** and choose `SolarizedTheme` (or `WordCountTools`).
   The extension is copied to `%APPDATA%\RADIDE\extensions\<id>` and starts at once - no restart.
2. Theme: Tools > Options > Environment > Color theme > *Solarized Dark*.
   Word Count: open a code file, then Tools > Word Count > Count Words in Active File, or look at the status bar.
3. In the Extensions window select the extension and press **Disable** (its menu, dock, status-bar label or
   themes disappear at once), **Enable**, or **Uninstall**.
4. To try the other install routes, zip a folder (`Install from Zip...`) or push it to a git repository
   (`Install from Git URL...`, any https:// / ssh:// / file:// URL).

These were tested for real by an offscreen IDE test: install from folder (before start-up), zip and a local git
repository (`file://`, also an upgrade 1.0.0 -> 1.0.1), live enable/disable/uninstall, a deliberately broken
extension (its exception is recorded and shown in the Extensions window; the IDE and the other extensions keep
working), an invalid manifest (rejected with the list of problems).
