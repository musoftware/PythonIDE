# StarRating - example component package

A complete external Toolbox control written as a component package (authoring guide:
[`docs/COMPONENTS.md`](../../../../docs/COMPONENTS.md)). It shows every part a package can have:

| File | What it does |
|---|---|
| `component.json` | Manifest: name, version, Toolbox category "Rating & Input", icon, prefix `Rating`, default size, 10 properties (a `custom` property with its own editor, `int` with min/max, `bool`, `color`, `enum`, `padding`, a design-only `multiline`), 2 events (`ValueChanged` = default event, `Hover`), 3 methods, runtimes for python-tk and python-qt. |
| `icon.png` | Toolbox icon. |
| `designer.py` | `paint(painter, rect, props, ctx)`: draws the stars on the design surface with the current property values (Value, MaxStars, Shape, colours, Padding, ShowValue, Caption). |
| `editors.py` | `EDITORS`: `starrating.stars` is an inline editor (clickable stars in the Value cell of the Properties window); `starrating.dialog` shows the modal editor style. |
| `runtime/starrating_tk.py` | python-tk runtime: `class StarRating(tk.Canvas)` (click to rate, hover, Value/MaxStars/StarColor/Enabled properties, `Reset()`, `SetValue()`, `rad_bind()`). |
| `runtime/starrating_qt.py` | python-qt (PySide6) runtime: `class StarRating(QWidget)` with the same API. |
| `help.md` | F1 help. |

`../StarRating.radcomp` is this folder zipped with Export .radcomp (rebuild it after a change:
Tools > Component Packages > Manage... > Export .radcomp, or `radide.components.export_package`).

## Try it

1. Tools > Component Packages > Install Component Package (.radcomp)... and pick
   `samples/Tests/Components/StarRating.radcomp` (or this folder's `component.json` through Manage... >
   Install...). Choose "All Projects".
2. The Toolbox gets a **Rating & Input** group with **Star Rating** (type "star" in the Toolbox search box).
3. Open [`../StarRating_PythonTk`](../StarRating_PythonTk/) or [`../StarRating_PythonQt`](../StarRating_PythonQt/)
   (File > Open Project) and open Form1 in the designer: the two ratings are drawn by `designer.py`.
4. Select `rateFood`: the Properties window shows the package properties by category with their descriptions;
   the Value cell has clickable stars (`editors.py`); changed values are bold, right-click > Reset restores the
   default. Select both ratings to edit `Spacing` of both at once.
5. Events tab: `ValueChanged` (bold, the handler exists) and `Hover`; double-click `Hover` to create
   `rateFood_Hover`. In the code, type `self.rateFood.` to see `Reset`, `SetValue`, `MaxStars`, ... from the
   manifest.
6. F5: the form runs with the runtime of the form's language (copied into the project when you save).
   Click the stars - the label shows the ratings; Reset sets Food to 0 and Service to 1.

To develop the package with hot reload, set `RADIDE_COMPONENT_PATH` to `samples/Tests/Components` **on a copy**
of this folder (never edit the sample itself) and start the IDE: saving any file of the package updates the
Toolbox, the designer and the Properties window at once.

A form of a language without a StarRating runtime (for example vb-basic) still generates: the control becomes a
label "[StarRating: no vb-basic runtime]" and the Output window shows a warning.
