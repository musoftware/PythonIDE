# Flask Todo (RAD IDE sample)

A todo list in **Flask 3** made from RAD IDE's *New Project > Web > Flask App* template (application factory):

| Feature | Where |
|---|---|
| Application factory `create_app()` with config classes | `app/__init__.py`, `config.py` |
| SQLite with the standard `sqlite3` module, one connection per request (`flask.g`), a `flask init-db` command | `app/db.py` |
| Blueprint `todos`: list with filter (all / active / done), add, toggle, edit, delete, clear completed, flash messages | `app/todos.py`, `app/templates/todos/` |
| Blueprint `api` (`/api`): JSON `GET/POST /api/todos`, `PATCH/DELETE /api/todos/<id>` | `app/api.py` |
| Jinja templates with inheritance, `url_for()`, `get_flashed_messages()` | `app/templates/` |
| 3 unit tests (Flask test client) | `tests/test_todos.py` |

Not in the sample: `.venv` and `instance/todo.sqlite` (made on the first run).

## Try it in RAD IDE

1. **File > Open Project** and choose this folder.
2. **Ctrl+F5**: the first run creates `.venv` and installs Flask; then `flask --app app --debug run` starts
   behind the IDE's server (Preview, Requests). Save a template: the Preview reloads. Save a `.py` file:
   Werkzeug's reloader restarts the app and the Preview reloads when it is back.
3. **View > Flask**: *flask routes*, the *Endpoints* list (double-click = open in the Preview; URL arguments
   such as `<int:todo_id>` are asked for), *Run flask command...* `init-db` (three example todos),
   *Run tests*, *pip install...*, *flask shell* (Terminal).
4. **F5** = debug: breakpoint (F9) in `app/todos.py` on `todos = db.execute(...)`, reload the Preview.
5. IntelliSense: `url_for('` lists the endpoints (`todos.index`, `todos.toggle`, `api.list_todos` ...),
   `url_for('static', filename='` the static files, `render_template('` the templates; in templates
   `{{ ` lists the variables the view passes (`todos`, `show`, `left`, `site_name`) and Flask's globals,
   `|` the Jinja filters, `{% ` the tags. F12 on an endpoint name opens its view function.
