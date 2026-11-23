# Extension points: how a feature takes part in the IDE

A feature (`radide/features/*.py`, an extension, a foreign project format) **never replaces a method of the main
window** (`win.save_all = wrapper`, `win.closeEvent = ...`). It registers with `win.extension_points`
(`radide/extension_points.py`), and `MainWindow` calls the extension points at fixed places.

Why: the old wrappers formed a hidden chain whose order was the alphabetical order of the feature files. One
wrapper that forgot to call the original, or dropped its result, silently broke every wrapper below it. That
was not hypothetical. A `.cur` file opened in the hex view instead of the image editor. A report opened
from Solution Explorer returned `None`. And the Save All command (Ctrl+S) never reached the wrappers at all.

`samples/Tests/Architecture/ExtensionPoints/test_extension_points.py` counts `win.<method> = ...` assignments in
`radide/`. The count is **0**, and the test fails if it grows.

## What to use

| You want to ... | Use | Notes |
|---|---|---|
| open your file type (File > Open, Solution Explorer) and take part in Save All / "Save changes?" | `add_document_provider(obj, priority)` | `obj` has `can_open(path)`, `open_document(path)`, `save_documents() -> bool \| None`, `has_modified_documents()`. Priorities: `EDITOR` (default), `BINARY_VIEWER`, `FALLBACK`. A file's own editor always wins over a viewer that takes any binary file. |
| add nodes to Solution Explorer | `add_solution_contributor(fn)` | `fn()` runs after every refill. |
| do something before / after Save All | `add_save_listener(fn, before=None)` | `fn(ok)` runs after every save: the command, Ctrl+S, save before run. `before()` runs first. |
| stop the IDE from closing | `add_close_guard(fn)` | `fn() -> False` keeps it open. Guards are asked before the save question, latest registered first. |
| clean up when the IDE closes | `add_shutdown_step(fn)` | Runs after the close is accepted, in registration order. |
| run the project yourself on F5 | `add_run_handler(fn)` | `fn(debug) -> True` means "I ran it", and the window will not run it. Return `False` after a pre-step such as writing project files. Asked latest first. |
| show your own Project > Properties | `add_properties_dialog(fn)` | `fn(project) -> True` means it was handled. |
| follow the lifecycle | `on(event, fn)` | See the events below. An unknown event name raises `ValueError`. |

## Events (`on(name, fn)`)

| Event | Arguments | When |
|---|---|---|
| `project_opening` | `folder` | `open_project` starts, before anything is loaded |
| `project_opened` | | `open_project` returned |
| `project_activated` | | `activate_project` returned. `win.project` may now be another project of the solution. |
| `projects_reset` | | `_reset` starts, before the solution's documents are dropped |
| `actions_updated` | | `_update_actions` finished. Set the state of your own commands or the Edit commands here. |
| `designer_opening` / `designer_opened` | `name` | around opening a form's designer |
| `form_opened` | `name, newly_loaded` | `open_designer` / `open_code` succeeded |
| `form_load_failed` | `name, error` | a damaged `.form`. With no handler registered, the error is raised. |
| `form_saving` / `form_saved` | `name` / `name, completed` | around writing a form |
| `project_saving` / `project_saved` | — / `completed` | around writing the active project |
| `file_saved` | `ok` | File > Save of the current tab |
| `designer_menu` | `form_name, menu, control` | after the window built the designer's right-click menu |
| `editor_menu` | `menu, form_name` | after the window built a code editor's right-click menu |
| `code_view_requested` | `name, codeview` | `_codeview` returned a code editor, new or cached |
| `module_view_shown` | `filename, moduleview` | `open_module` showed a module editor |
| `title_updated`, `layout_restored` | | after `_update_title` / `restoreState` |
| `output_logged` | `text` | a line went to the Output window. Errors in these handlers go to stderr, never back to the Output. |
| `session_created` | `session, debug, plugin` | a run / debug session was made |
| `debug_pausing` / `debug_paused` | `info` | before / after the window shows a stop |
| `debug_resuming` / `debug_resumed` | | around continue |
| `program_finished` | `code, session` | the program ended |

## Rules

* A handler that raises is logged to the Output window and never stops the IDE or the other handlers. The same
  error from the same handler is logged only once, because `actions_updated` runs very often.
* Do not wrap `win.open_file` either. It comes from `web_workspace`, and merging it into `MainWindow` is the
  next step. The wrappers still on it are marked `TODO(stage B)`.
* Other helpers on the window: `win.no_save_questions()` is a context manager with no "Save changes?" inside it.
  `win.temp_breakpoints` holds extra breakpoints for one start.
* To check a feature: `samples/Tests/Architecture/ExtensionPoints/` has characterization tests for every kind
  of participant. Add a row or a case there when you add one.
