# Tk_SQLite_Customers

**python-tk** - a DataGridView and a BindingNavigator bound to the `Customers` table of `shop.db` (SQLite).

Tests: Fill on load, grid edits (double-click a cell), Add / Delete / Save (parameterized INSERT / UPDATE / DELETE),
`Customers.Search(text, "Name", "Email", "City")`, `Customers.SortBy(column)`, `Customers.Fill("City = ?", "Cairo")`,
the `Customers_PositionChanged` handler and "save the changes?" in `Form1_FormClosing`.

**Try it:** open the folder, look at the designer (real rows), the Data Sources window (Data > Show Data Sources) and
the grid's DataSource property; press F5. `python reset_db.py` puts the original rows back.
