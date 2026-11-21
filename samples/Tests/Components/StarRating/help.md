# StarRating

A row of stars the user clicks to rate something. Clicking the first star again when the rating is 1 clears it.

## Properties

| Property | Type | Default | Description |
|---|---|---|---|
| Value | int (star editor) | 3 | The rating (0 = none). |
| MaxStars | int | 5 | How many stars are drawn (1..10). |
| ReadOnly | bool | False | The user cannot change the rating. |
| StarColor | color | #FFB400 | Colour of the selected stars. |
| EmptyColor | color | #C8CDD5 | Colour of the other stars. |
| Shape | Star / Circle / Square | Star | The figure drawn. |
| Spacing | int | 4 | Pixels between two stars. |
| Padding | padding | 2, 2, 2, 2 | Space inside the control. |
| ShowValue | bool | False | Writes "3/5" after the stars. |
| Caption | multiline (design only) | | A note shown in the designer only. |

## Events

* **ValueChanged** (default) - the rating changed (click, or code that sets `Value`).
* **Hover** - the mouse moved over another star; read `HoverValue`.

## Methods

* `Reset()` - sets `Value` to 0.
* `SetValue(value)` - sets `Value` (clamped to 0..MaxStars).

## Example (Python)

```python
def Rating1_ValueChanged(self):
    self.lblResult.config(text=f"You gave {self.Rating1.Value} stars")   # python-tk
```

Runtimes: **python-tk**, **python-qt**. Other languages get a placeholder label and a warning.
