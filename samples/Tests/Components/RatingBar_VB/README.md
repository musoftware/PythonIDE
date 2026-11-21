# RatingBar_VB

A vb-basic project that uses the multi-target **RatingBar** component package (`../RatingBar`), installed for this project only (`.radide/components/RatingBar`).

* `Form1` has two RatingBar controls (rateFood, rateService), a ValueChanged handler for each and a Reset button that calls `Reset()` / `SetValue(1)`.
* The control is created through the python-tk runtime (`ratingbar_tk.py`): the VB runtime draws VB6 forms with Tk.

Open the folder in RAD IDE and press F5: clicking a star updates the label; Reset sets 0 and 1 stars.
