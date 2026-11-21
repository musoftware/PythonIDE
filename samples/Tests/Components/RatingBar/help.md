# RatingBar

A row of stars the user clicks to rate something. One component package with a runtime for every target:

| Target | Runtime |
|---|---|
| Python (Tkinter) | `runtime/ratingbar_tk.py` - class `RatingBar` |
| Python (PySide6) | `runtime/ratingbar_qt.py` - class `RatingBar` |
| VB6 (vb-basic) and the GUI Bridge languages (C#, Java, JavaScript, ...) | the python-tk runtime (the IDE draws these forms with Tk) |
| Ring (RingQt) | `runtime/ratingbar.ring` - class `RatingBar` |
| Flutter | `runtime/rating_bar.dart` - widget `RatingBar` (template in component.json) |
| Web pages | `runtime/ratingbar.js` + an HTML/CSS template |

Properties: `Value`, `MaxStars`, `ReadOnly`, `StarColor`, `EmptyColor`. Event: `ValueChanged`.
Methods: `Reset()`, `SetValue(value)`.

    Python:     self.rate1.Value = 4          self.rate1.Reset()
    VB6:        rate1.Value = 4               rate1.Reset
    JavaScript: set("rate1", "Value", 4)      call("rate1", "Reset")
    Ring:       rate1.setValue(4)             rate1.reset()
