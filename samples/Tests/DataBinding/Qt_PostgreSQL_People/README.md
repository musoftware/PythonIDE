# Qt_PostgreSQL_People

**python-qt + PostgreSQL** - grid + details of the `people` table on the IDE's local PostgreSQL server (connection
`LocalDb`; PostgreSQL folds the names to lower case: `id`, `name`, ...).

Tests: Fill, grid / TextBox edits, BOOLEAN column -> CheckBox, Add (the `SERIAL` id comes back with `RETURNING`),
Delete, Save, *Reload (Fill)*.

**Try it:** Databases > Local Servers > Start local PostgreSQL; `.venv\Scripts\python setup_db.py`; F5.
