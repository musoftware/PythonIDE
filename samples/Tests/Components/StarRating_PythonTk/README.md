# StarRating_PythonTk - a form that uses the StarRating component package

Language: **python-tk (Tkinter)**. Form1 has two `StarRating` controls from the external package
[`../StarRating`](../StarRating/) (`rateFood`: 5 stars with ShowValue; `rateService`: 6 blue circles), a Reset
button and a result label. Handlers: `rateFood_ValueChanged`, `rateService_ValueChanged` (update the label) and
`btnReset_Click` (calls the package methods `Reset()` and `SetValue(1)`).

`starrating_tk.py` is the package runtime the IDE copied into the project when it was saved, so the program also runs
without the IDE (`python Form1.py`). `Form1_designer.py` is generated: it imports the runtime, creates the
controls with `StarRating(parent, Value=..., MaxStars=..., ...)` and connects the events with `rad_bind`.

How to try it:

1. Install the package first (Tools > Component Packages > Install Component Package (.radcomp)... >
   `samples/Tests/Components/StarRating.radcomp`), otherwise the designer shows the two controls as red boxes
   "package not installed" (their properties are kept).
2. File > Open Project > this folder, open Form1 [Design]: the stars are drawn by the package's `designer.py`.
3. F5: click the stars - the label shows `Food: 4/5  Service: 4/6`; Reset gives `Food: 0/5  Service: 1/6`.

Tested headless (scratch copy): the form was created, `rateFood.Value = 5` raised ValueChanged (label
`Food: 5/5`), the Reset button gave `Food: 0/5  Service: 1/6`.
