# LanguageFeatures - classic VB6 statements the interpreter now runs

A `Sub Main` program (`Main.bas`) and a class module (`CTally.cls`) that use the VB6 features added to the
bundled interpreter in round 7:

- `GoSub` / `Return`, `On i GoSub a, b, c`
- `Static` variables, `Optional` arguments with defaults, named arguments (`Discount:=0.25`)
- `Format$` user formats (`#,##0.00`, `0.0%`, `0;(0)`, `dddd d mmmm yyyy`, `>`) and named formats (`Standard`)
- `Collection` with keys and `Before:=`
- a class with `Class_Initialize`, `CreateObject("Scripting.Dictionary")` (`CompareMode = vbTextCompare`,
  `d(k) = d(k) + 1`, `Exists`, `Keys`), a default property (`Tally("the")`) and an `Event` handled through
  `WithEvents` (note: real VB6 only allows `WithEvents` in forms and class modules; the RAD interpreter also
  accepts it in a standard module, as used here)
- a `Type` with `String * n` fields written to and read from a **Random** file (`Open ... Len = Len(p)`, `Put`, `Get`,
  `LOF`, `Kill`)
- `On Error GoTo` with `Err.Number` / `Err.Description` for a missing file

How to try it: open this folder (File > Open Project) and press **F5**, or run
`.venv\Scripts\python -m radide.runtimes.vbrun samples\Tests\VB6\LanguageFeatures`. Expected output:

```
red green blue
1       2       3
114.00  85.50   80.00
1,234,567.89    7.5%    (42)
Thursday 15 January 2026        ABC
Cairo Tokyo Rome | Tokyo
the=3   and=2   words=the,cat,and,dog,bird      ticks=8
P001    Keyboard        25.50
P002    Mouse   9.99
P003    Monitor 189.00
Stock value: 2,449.92
Error 53: File not found: <this folder>\does-not-exist.txt
```
