# RatingBar_PythonQt

A python-qt project that uses the multi-target **RatingBar** component package (`../RatingBar`), installed for this project only (`.radide/components/RatingBar`).

* `Form1` has two RatingBar controls (rateFood, rateService), a ValueChanged handler for each and a Reset button that calls `Reset()` / `SetValue(1)`.
* The control is created through its python-qt runtime (`ratingbar_qt.py`, copied into the project).

Open the folder in RAD IDE and press F5: clicking a star updates the label; Reset sets 0 and 1 stars.
