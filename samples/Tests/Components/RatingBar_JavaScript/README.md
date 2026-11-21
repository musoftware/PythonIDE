# RatingBar_JavaScript

A javascript project that uses the multi-target **RatingBar** component package (`../RatingBar`), installed for this project only (`.radide/components/RatingBar`).

* `Form1` has two RatingBar controls (rateFood, rateService), a ValueChanged handler for each and a Reset button that calls `Reset()` / `SetValue(1)`.
* The control is created through the python-tk runtime (`ratingbar_tk.py`): the GUI Bridge host draws the form with Tk; the program uses `get` / `set` / `call`.

Open the folder in RAD IDE and press F5: clicking a star updates the label; Reset sets 0 and 1 stars.
