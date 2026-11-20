# Tk_MariaDB_People

**python-tk + MariaDB** - grid + details of the `People` table on the IDE's local MariaDB server (connection
`LocalDb`, user `radide`, database `radide`; the password is never stored in the project).

Tests: Fill, edits, a CheckBox on a `TINYINT(1)` column, Add (the `AUTO_INCREMENT` Id is read back), Delete, Save,
*Reload (Fill)*.

**Try it:** Databases > Local Servers > Start local MariaDB/MySQL; run `setup_db.py` with the IDE's Python
(`.venv\Scripts\python setup_db.py`) to create the table; F5 (the IDE passes the password as
`RADIDE_DB_LOCALDB_PASSWORD`).
