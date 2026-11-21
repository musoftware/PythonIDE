# Component packages

Every Toolbox control is a component package (`component.json` + optional `designer.py`, `editors.py`,
runtimes per language and `help.md`). Authoring guide and JSON schema: [`docs/COMPONENTS.md`](../../../docs/COMPONENTS.md).

| Folder | What it is | How to try it |
|---|---|---|
| [`StarRating`](StarRating/) | Complete external package: manifest with a custom-editor property, designer drawing (`paint`), inline property editor, python-tk and python-qt runtimes, help, icon. `StarRating.radcomp` is the same package zipped for installing. | Tools > Component Packages > Install Component Package (.radcomp)... > `StarRating.radcomp`; the Toolbox gets "Rating & Input" > Star Rating. |
| [`StarRating_PythonTk`](StarRating_PythonTk/) | python-tk form using two StarRatings with ValueChanged handlers and the package methods. | Install the package, open the folder, F5, click the stars / Reset. |
| [`StarRating_PythonQt`](StarRating_PythonQt/) | The same form in python-qt (PySide6). | Same as above. |
