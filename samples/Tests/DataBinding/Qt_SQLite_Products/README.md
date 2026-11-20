# Qt_SQLite_Products

**python-qt (PySide6)** - `Products` dropped twice (Details, then DataGridView: one BindingNavigator, both views share
the position) and `Categories` used as a lookup: ComboBox `cboCategory` (DataSource Categories, DisplayMember Name,
ValueMember Id, DataMember `Products.CategoryId`) and a ListBox bound to Categories.

Tests: two-way binding TextBox / CheckBox / ComboBox <-> grid, number validation (`Price: 'abc' is not a number`),
new rows get the column DEFAULTs, `UpdateAll()` (Save all), `Categories.Find("Id", ...)` in `Products_PositionChanged`.

**Try it:** F5, navigate, change Name / Category / Price / InStock, press *Save all*. `python reset_db.py` resets the data.
