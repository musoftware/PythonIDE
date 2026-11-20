# FastAPI Items (RAD IDE sample)

A CRUD API in **FastAPI** with **SQLAlchemy 2.0 + SQLite**, made from RAD IDE's *New Project > Web > FastAPI App*
template:

| Feature | Where |
|---|---|
| SQLAlchemy engine / session dependency, typed model `Item` (`Mapped[...]`) | `app/database.py`, `app/models.py` |
| Pydantic schemas with validation (`ItemCreate`, `ItemUpdate` with partial updates, `ItemOut`) | `app/schemas.py` |
| `GET /items?q=&skip=&limit=`, `POST /items`, `GET/PUT/DELETE /items/{item_id}`, 404 / 422 errors | `app/main.py` |
| Lifespan: creates the tables and three demo items | `app/main.py` |
| A Jinja2 page that lists the items and adds / deletes them with `fetch()` | `app/templates/index.html` |
| 4 unit tests (`TestClient`, a temporary database) | `tests/test_items.py` |

Not in the sample: `.venv` and `data/items.db` (made on the first run).

## Try it in RAD IDE

1. **File > Open Project** and choose this folder.
2. **Ctrl+F5**: the first run creates `.venv` and installs FastAPI, uvicorn, SQLAlchemy ...; then uvicorn starts
   behind the IDE's server (Preview, Requests). Saving a template reloads the Preview; saving a `.py` file
   restarts uvicorn (the IDE does it: `uvicorn --reload` cannot stop its worker on Windows without a console;
   set `"reload": "framework"` in the `web` block of `project.radproj` to use uvicorn's own reloader).
3. **View > FastAPI**: *Open /docs* (Swagger UI in the Preview - try the API there), *Open /redoc*, the
   *Routes* list (methods, path, view; double-click opens GET routes, path parameters are asked for),
   *Run tests*, *pip install...*.
4. **F5** = debug: breakpoint (F9) in `app/main.py` on `items = session.scalars(...)` in `home()`, reload the Preview.
5. IntelliSense: `request.url_for('` / `app.url_path_for('` list the route names, the templates are completed
   in `TemplateResponse(request, '`; `{{ ` in `index.html` lists `items` / `count`; `|` the Jinja filters.
