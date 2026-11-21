# Component packages

Every Toolbox control is a component package (`component.json` + optional `designer.py`, `editors.py`,
runtimes per language and `help.md`). Authoring guide and JSON schema: [`docs/COMPONENTS.md`](../../../docs/COMPONENTS.md).

| Folder | What it is | How to try it |
|---|---|---|
| [`StarRating`](StarRating/) | Complete external package: manifest with a custom-editor property, designer drawing (`paint`), inline property editor, python-tk and python-qt runtimes, help, icon. `StarRating.radcomp` is the same package zipped for installing. | Tools > Component Packages > Install Component Package (.radcomp)... > `StarRating.radcomp`; the Toolbox gets "Rating & Input" > Star Rating. |
| [`StarRating_PythonTk`](StarRating_PythonTk/) | python-tk form using two StarRatings with ValueChanged handlers and the package methods. | Install the package, open the folder, F5, click the stars / Reset. |
| [`StarRating_PythonQt`](StarRating_PythonQt/) | The same form in python-qt (PySide6). | Same as above. |
| [`RatingBar`](RatingBar/) | Multi-target package: one manifest, a runtime per target - python-tk and python-qt classes, a RingQt class (`ratingbar.ring`), a Flutter widget (`rating_bar.dart`, template), a web template (`ratingbar.js`); VB6 and the GUI Bridge languages use the python-tk class (the IDE draws their forms with Tk). The Toolbox tooltip lists where it runs. | Hover the Toolbox item; open one of the projects below. |
| [`RatingBar_PythonTk`](RatingBar_PythonTk/), [`RatingBar_PythonQt`](RatingBar_PythonQt/), [`RatingBar_VB`](RatingBar_VB/), [`RatingBar_Ring`](RatingBar_Ring/), [`RatingBar_JavaScript`](RatingBar_JavaScript/) | The same form (two RatingBars, ValueChanged handlers, Reset button calling `Reset()` / `SetValue(1)`) in five languages; the package is installed in each project (`.radide/components`). | Open a folder, F5, click the stars and Reset. VB: `rateFood.Value`, JavaScript: `get("rateFood", "Value")`, Ring: `rateFood.value()`. |
