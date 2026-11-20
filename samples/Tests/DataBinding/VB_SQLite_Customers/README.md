# VB_SQLite_Customers

**vb-basic** - the Customers table dropped as Details (labels + text boxes + navigator) and used from VB code:
`Customers.Fill "City = ?", "Cairo"`, `Customers.Fill`, `Customers.Count`, `Customers.Value("Name")`,
`Customers.Value("Balance", i)` in a `For` loop, `Customers.Position = best` (the bound controls follow).

**Try it:** F5, press *Cairo customers*, *All customers*, *Who has most?*; edit a field and press the navigator's Save.
`python reset_db.py` resets the data.
