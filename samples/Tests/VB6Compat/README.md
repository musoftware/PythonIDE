# VB6Compat - real-world VB6 compatibility reproductions

Eight downloaded VB6 student/business projects (bank, financial, electricity bill, calculator, hospital, logic gates,
medical store, online exam - not included here, their licence is unknown) were opened in place, run and migrated.
Each folder below is a small project **written for these tests** that reproduces one group of gaps found in them and
fixed in the IDE. All of them are plain VB6 files (`.vbp`, `.frm`, `.bas`, `.Dsr`); the `shop.mdb` Access database
(tables `Products` and `Users`) was created with Jet 4.0.

Open a `.vbp` with **File > Open Project** (it opens in place) and press **F5**, or run it from a shell:
`.venv\Scripts\python -m radide.runtimes.vbrun samples\Tests\VB6Compat\<Folder>\<Name>.vbp`.
`Debug.Print` lines go to the Output window / stdout.

| Folder | Gap it reproduces (fixed in) | Expected result |
|---|---|---|
| [`ParserAndLanguage`](ParserAndLanguage/) | Line continuation `_` never worked (lexer matched blanks first) - it broke 5 of the 8 projects at load (`If (a) _`, `Declare ... Alias _`); `rs!Field` was lexed as `rs!` (Single suffix); Enum members without `=` crashed the interpreter; `Dim m As MyEnum` was an Object; without `Option Explicit` an undeclared name must read as Empty; `Get 1, , b` without `#`; binary `EOF()` is True only after a short `Get` (radide/runtimes/vbparse.py, vbinterp.py, vbfiles.py, vbrun.py) | `continuation ok`, `sum=6`, `enum: 0 1 10 11 mode=0`, `mode is design`, `undeclared=[] or 4 = 4`, `binary=Hi`, `declare ok: True` |
| [`AdoAccessGrid`](AdoAccessGrid/) | ADO (`New ADODB.Connection/Recordset/Command`) did not exist; Access `.mdb` + Jet 4.0 is 32-bit only; hard-coded database paths of the author's PC; MSFlexGrid was a ListBox (no `TextMatrix`/`ColWidth`); DTPicker was a placeholder (radide/runtimes/vbado.py, vbrun.py, importers/vb6_import.py) | Output `rows=3 fields=6 first=Name`, `stock value=1221.60`, `added Webcam id>3: True`, `filtered=3`, `mouse stock=41 IsNull=False`, `deleted=1`, `cheap: Keyboard;Mouse;`, `error trapped: True`, `grid rows=3 header=Name first=Keyboard`; the form shows the grid with 3 products and a date picker. A stderr note says `D:\OldPc\Shop\shop.mdb` was replaced by the `shop.mdb` next to the program. |
| [`DaoDataControl`](DaoDataControl/) | DAO (`OpenDatabase`, `OpenRecordset`, `FindFirst`/`NoMatch`, `Edit`/`Update`, `TableDefs`) and the intrinsic **Data** control (`DatabaseName`, `RecordSource`, bound `DataSource`/`DataField` controls, |< < > >| navigation) were missing (radide/runtimes/vbado.py, vbdata.py) | `tables: Products Users`, `cheapest: Mouse`, `NoMatch: True`; the form shows Keyboard / 25.5 / 10; the > button moves to Mouse; editing Price and moving saves it; **Add** + typing + **Save** inserts a row (`saved: 4 records`); **Find Monitor** prints `found: Monitor 189 stock 3`. |
| [`OcxControls`](OcxControls/) | SSTab was an empty Panel (children of hidden pages at Left = -75000 twips, invisible); ListView/TreeView were ListBoxes; MonthView/MaskEdBox/Line placeholders or missing; `SSTab1_Click(PreviousTab)` failed with "Argument not optional"; `tvwChild` etc. undefined (radide/importers/vb6_import.py, foreign/frm_writer.py, runtimes/vbrun.py) | In the designer: 3 tab pages (Lists, Grid, Dates) with their controls, ListView columns Product/Price, grid columns Code/Description/Qty, a blue line. F5: `items=2 nodes=2 grid=Description/Item 3 date=2026-01-01 tab=0`, then `tab 0 -> 2 (Dates)`. |
| [`DataEnvironmentReport`](DataEnvironmentReport/) | DataEnvironment (.Dsr connections and commands, `DataEnvironment1.Command1`, `rsCommand1`, parameters) and `DataReport1.Show` (radide/runtimes/vbdata.py) | `Command1 rows=3`, `cheaper than 30: Keyboard Mouse`, `connection open: True`; **Show report** opens a window with the rows of Command1 (the report layout itself is not drawn). Note: the .Dsr files are hand-written text (no .dsx/.dca companions), so VB6 itself would ask to rebuild them. |

How the database part works (radide/runtimes/vbado.py): the VB6 program keeps its connection string; when no 64-bit
Access ODBC driver is installed, a 32-bit `cscript.exe` helper (`%SystemRoot%\SysWOW64`) runs the real ADO with that
connection string (Jet 4.0 / ACE / 32-bit ODBC DSNs / SQL Server) and streams rows back; recordsets are client-side
(Move*, Find, Filter, Sort in Python) and `AddNew` / `Update` / `Delete` / DAO `Edit` become INSERT / UPDATE / DELETE
on the source table (primary key, or all comparable columns). `.db` / `.sqlite` files use sqlite3.

Migration (File > Migrate to python-tk) of these projects: `vbado.py` and the databases are copied next to the
migrated program, `New ADODB.x` becomes `CreateObject("ADODB.x")`, `rs.Fields(0) = x` / `Grid.TextMatrix(r, c) = x`
become `vb_setindexed(...)` (they were Python syntax errors). Known limits: a VB6 project that starts with `Sub Main`
starts with its first form after migration (the report says to call `Main`), and ListView/TreeView object models
(`ListItems.Add`, `Nodes.Add`) are not translated.
