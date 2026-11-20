# DataBinding - forms bound to real databases (Data Sources window)

VB 2005 style data binding: **Data > Show Data Sources** (Shift+Alt+D), *Add New Data Source...* (a connection of
the Databases workspace: SQLite, MySQL / MariaDB, PostgreSQL, or an ODBC connection string), then drag a table onto
the form: a BindingNavigator (|< < "1 of 7" > >| Add Delete Save) and a DataGridView, or - right-click the table:
*Drop as Details* - a Label + TextBox / CheckBox per column. The designer shows real rows.

| Folder | Language | What it tests | How to try it |
|---|---|---|---|
| [`Tk_SQLite_Customers`](Tk_SQLite_Customers/) | python-tk | Grid + navigator on `shop.db`; client-side `Search` / `SortBy`, parameterized `Fill("City = ?", "Cairo")`, `Customers_PositionChanged`, save on close. | F5. Double-click a cell to edit, Add / Delete, Save. Type in Search, pick Sort by. `python reset_db.py` restores the rows. |
| [`Qt_SQLite_Products`](Qt_SQLite_Products/) | python-qt (PySide6) | Details view + grid on the same source, a lookup ComboBox (Categories: DisplayMember Name, ValueMember Id, DataMember `Products.CategoryId`), a bound ListBox, `UpdateAll()`, number validation. | F5. Navigate, change the category / price / In stock, press *Save all*. Type `abc` as a price: refused. |
| [`VB_SQLite_Customers`](VB_SQLite_Customers/) | vb-basic | VB code on a data source: `Customers.Fill "City = ?", "Cairo"`, `Customers.Count`, `Customers.Value("Balance", i)`, `Customers.Position = best`. | F5. *Cairo customers*, *All customers*, *Who has most?*; edit a field, navigator Save. |
| [`Tk_MariaDB_People`](Tk_MariaDB_People/) | python-tk + MariaDB | The same binding on the IDE's local MariaDB server (`AUTO_INCREMENT` key read back after insert). | Databases > Local Servers > Start local MariaDB, run `setup_db.py` with the IDE's Python, then F5. |
| [`Qt_PostgreSQL_People`](Qt_PostgreSQL_People/) | python-qt + PostgreSQL | Grid + details on the IDE's local PostgreSQL (`SERIAL` key via `RETURNING`, BOOLEAN column -> CheckBox). | Start local PostgreSQL, run `setup_db.py`, then F5. |

Passwords are never written into a project: F5 from the IDE passes the ones it knows (local servers, remembered
connections) as `RADIDE_DB_<CONNECTION>_PASSWORD`; outside the IDE set that variable, or put
`{"LocalDb": {"password": "..."}}` in a `connections.json` next to the program, or type it when asked.
The samples were built with the IDE's own API (data sources, drop layout, code generation) and their generated
programs were run with scripted clicks (list, edit, add, delete, save, re-read) against SQLite, MariaDB and PostgreSQL.
