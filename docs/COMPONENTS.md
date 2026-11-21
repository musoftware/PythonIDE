# Component packages - authoring guide

Every control in the RAD IDE Toolbox is a **component package**: a folder that describes the control (its
properties, events and methods), how the designer draws it, how the Properties window edits it, and how each
target language creates it at run time. This is the same idea as Visual Studio's `System.ComponentModel`
(attributes, type converters, `UITypeEditor`), Delphi/Lazarus packages (`RegisterComponents`, property
editors) and Qt Designer custom widget plugins, in one JSON manifest plus optional Python files.

The IDE's own controls are packages too (`radide/components/builtin/<Name>/component.json`, with
`"targets": {"*": {"native": true}}` because the language plugins generate them directly). Packages you
install appear in the Toolbox under their own category, the Properties window and Events tab are built from
the manifest, IntelliSense lists their members, and the form generator writes code that creates them through
the package's runtime for the form's language.

Contents: [1 Package layout](#1-package-layout) - [2 Where packages are found](#2-where-packages-are-found) -
[3 The manifest](#3-the-manifest-componentjson) - [4 Property types](#4-property-types) -
[5 Events and methods](#5-events-and-methods) - [6 Runtimes](#6-runtimes-one-per-target) -
[7 Designer drawing](#7-designer-drawing-designerpy) - [8 Custom property editors](#8-custom-property-editors-editorspy) -
[9 Help](#9-help-helpmd) - [10 Packaging, installing, sharing](#10-packaging-installing-sharing) -
[11 Versions and conflicts](#11-versions-and-conflicts) - [12 Hot reload](#12-developing-a-package-hot-reload) -
[13 Python API](#13-python-api-for-ide-code) - [14 Complete example](#14-complete-example-starrating) -
[15 JSON schema](#15-json-schema)

## 1. Package layout

```text
StarRating/
    component.json        manifest (required)
    icon.png              Toolbox icon, 16..32 px (.png / .svg / .ico) - optional
    designer.py           how it is drawn on the design surface - optional (default renderer otherwise)
    editors.py            custom Properties window editors - optional
    runtime/
        starrating_tk.py  runtime for python-tk
        starrating_qt.py  runtime for python-qt (PySide6)
    help.md               F1 help - optional
```

Only `component.json` is required. Every file the manifest names must be a relative path inside the package
(no `..`, no absolute paths); the validator checks that the files exist.

## 2. Where packages are found

The registry (`radide/components/__init__.py`, `REGISTRY`) loads packages at start-up from, in this order:

| Source | Location | Notes |
|---|---|---|
| `builtin` | `radide/components/builtin/*` | The IDE's own controls. |
| `extension` | enabled extensions with `"contributes": {"components": [{"folder": "components/StarRating"}]}` in `radide-extension.json` | Disabled extensions contribute nothing. |
| `user` | `%APPDATA%\RADIDE\components\*` (`RADIDE_COMPONENTS_DIR` overrides it) | Where "Install for all projects" puts a `.radcomp`. |
| `project` | `<project>/.radide/components/*` | Components that travel with one project ("Install for this project"). Loaded when the project is activated, or when a form that uses an unknown type is opened from that folder. |
| `dev` | folders listed in `RADIDE_COMPONENT_PATH` (separated by `;`) | Packages being developed; hot reload is on by default. Each entry may be a package folder or a folder of packages. |

A form that uses a control whose package is not installed still opens: the control is drawn as a red box
"package not installed", its saved properties are kept unchanged, and generators write a placeholder label
plus a warning.

## 3. The manifest (`component.json`)

```json
{
  "$schema": "../../docs/component.schema.json",
  "schemaVersion": 1,
  "name": "StarRating",
  "displayName": "Star Rating",
  "version": "1.0.0",
  "publisher": "Me",
  "description": "A row of stars the user clicks to rate something.",
  "category": "Rating & Input",
  "icon": "icon.png",
  "prefix": "Rating",
  "defaultSize": [130, 26],
  "kind": "visual",
  "hasText": false,
  "defaultEvent": "ValueChanged",
  "properties": [ {"name": "Value", "type": "int", "default": 3, "category": "Behavior",
                   "description": "The rating shown."} ],
  "events": [ {"name": "ValueChanged", "description": "The Value changed."} ],
  "methods": [ {"name": "Reset", "signature": "Reset()", "description": "Sets Value to 0."} ],
  "targets": {
    "python-tk": {"file": "runtime/starrating_tk.py", "class": "StarRating"},
    "python-qt": {"file": "runtime/starrating_qt.py", "class": "StarRating"}
  },
  "designer": "designer.py",
  "editors": "editors.py",
  "help": "help.md",
  "requires": {"radide": ">=1.0"}
}
```

| Key | Type | Meaning |
|---|---|---|
| `schemaVersion` | 1 | Manifest format version. |
| `name` | identifier, **required** | Control type name stored in `.form` files. Must be unique. |
| `version` | `1.2.3` / `1.2.3-beta`, **required** | Used to choose between two copies of a package (section 11). |
| `displayName` | string | Toolbox label (default: `name`). |
| `publisher`, `description`, `license`, `homepage`, `keywords` | | Shown in Choose Items / the package manager; `description` is the Toolbox tooltip and the Properties description box. |
| `category` | string | Toolbox group (default `General`). The VS 2005 groups (Common Controls, Containers, Menus & Toolbars, Data, Components, Dialogs, Reporting) come first, other groups alphabetically, `General` last. |
| `order` | number | Position inside the group (default 1000). |
| `icon` | file | Toolbox icon; without one a generic component icon is used. |
| `prefix` | identifier | Name of new instances: `Rating1`, `Rating2`... (default `name`). |
| `defaultSize` | `[w, h]` | Size of a new instance (default `[100, 30]`, `[0, 0]` for non-visual). |
| `kind` | `visual` / `container` / `nonvisual` | Containers host child controls; non-visual components live in the component tray under the form (like Timer). |
| `hasText` | bool (true) | The control has the common `Text` property. |
| `commonEvents` | bool (true) | Adds Click, DoubleClick, Mouse*, Key*, GotFocus, LostFocus. |
| `commonProperties` | bool (true) | Reserved: Name/Left/Top/Width/Height/colours/font/Enabled/Visible/ToolTip/TabIndex/Anchor/Dock are always present for visual controls. |
| `overrides` | object | Different defaults for common properties, e.g. `{"Dock": "Bottom", "Height": 22}`. |
| `defaultEvent` | event name | The handler double-clicking the control creates (default: the first event). |
| `properties` / `events` / `methods` | arrays | Sections 4 and 5. |
| `targets` | object | Section 6. |
| `designer`, `editors`, `help` | files | Sections 7, 8, 9. |
| `overrideBuiltin` | bool | Allows a package to replace a built-in control of the same name (otherwise it is ignored with a conflict message). |
| `mobile` | bool | A mobile control (the Toolbox "Mobile" group of phone forms; drawn by `radide/mobile/render.py`). Used by the built-in AppBar, BottomNav, Fab, Card, MListView, Switch, MSlider, MTextField, MImage, MIcon, Drawer, MTabBar, MWebView, Column, Row, Stack. |
| `vb6` | object | VB6 `.frm` import / export mapping: `class` (written for a new control, e.g. `VB.CommandButton`), `library` (its OCX, e.g. `MSComctlLib`), `imports` (VB6 / ActiveX classes imported as this control, any case, e.g. `mscomctllib.listview`), `approx` (the imports that are approximations - the importer warns), `properties` (neutral -> VB6 name of plain integer properties, e.g. `{"Minimum": "Min"}`). Read by `radide/components/vb6map.py` for `radide/importers/vb6_import.py` and `radide/foreign/frm_writer.py`. |
| `requires.radide` | `">=1.0"` | Minimum component API version (`radide.components.API_VERSION`). |
| `x-...` | anything | Vendor data, ignored by the IDE. |

Unknown keys are errors (typos are caught). Errors are listed in the Output window (`[components] ...`), in
the package manager's details box, and an invalid package is refused by Install.

## 4. Property types

Each entry of `properties`:

| Key | Meaning |
|---|---|
| `name` (required) | Property name used in code. |
| `type` (required) | One of the kinds below (aliases accepted). |
| `default` | Default value; its JSON type must fit the kind. Values equal to the default are shown normal, changed values **bold**; right-click > Reset restores the default (like Visual Studio). |
| `description` | Text of the Properties window's description box. |
| `category` | Properties window group (Appearance, Behavior, Layout, Data, Misc...). |
| `displayName` | Label in the grid (default `name`). |
| `choices` | Values of an `enum` / `flags` property. |
| `editor` | Id of a custom editor from the package's `editors.py` (section 8). |
| `min`, `max`, `decimals` | Limits of `int` / `float`. |
| `filter` | File dialog filter for `file` / `image`, e.g. `"CSV files (*.csv)"`. |
| `browsable` | `false` hides the property from the Properties window. |
| `designOnly` | `true` = the value is used by the designer only and never passed to the runtime. |

| Kind (aliases) | Stored value | Properties window editor |
|---|---|---|
| `str` (string, text) | `"text"` | inline text |
| `multiline` | `"line 1\nline 2"` | "..." text dialog |
| `int` (integer) | `12` | inline number, `min`/`max` checked |
| `float` (number, double) | `1.5` | inline number |
| `bool` (boolean) | `true` | True / False list |
| `enum` | `"Value"` | drop-down of `choices` |
| `dock` | `"Fill"` | enum with None/Top/Bottom/Left/Right/Fill |
| `flags` | `"Bold, Italic"` | check list of `choices` |
| `color` (colour) | `"#RRGGBB"`, `""` = system | colour dialog with swatch |
| `font` | `"Segoe UI"` | font list |
| `image` (resource) | `"Resources/a.png"` | file dialog; files outside the project are copied into `Resources/` |
| `file` (path) | `"data/a.csv"` | file dialog (`filter`) |
| `list` (items) | `"a;b;c"` | inline text, items separated by `;` |
| `columns` | `"Name;Age"` | "..." collection editor (one per line) |
| `menu` | `[{"Text", "Name", "Items"}]` | menu editor |
| `padding` (margins) | `"4, 4, 4, 4"` | inline; `4` or `4, 8` are expanded |
| `anchor` | `"Top, Left"` | VS anchor pop-up |
| `alignment` | `"MiddleCenter"` | the 9 positions |
| `gradient` | `"#FFFFFF, #000000, 90"` | start / end colour, angle |
| `shadow` | `"2, 2, 6, #80000000"` | dx, dy, blur, colour |
| `border` | `"1, solid, #808080, 4"` | width, style, colour, radius |
| `dbref` (binding, databinding) | `"Source.Column"` | data binding list (Data Sources window) |
| `event` (handler) | `"Handler"` | handler name |
| `custom` | any JSON | the package's own editor (`editor` is required) |

The helpers in `radide/components/proptypes.py` (`parse_padding`, `parse_gradient`, `parse_shadow`,
`parse_border`, `parse_alignment`, `parse_flags`, `coerce`, `text_of`) have no Qt dependency; runtimes may copy
the few lines they need.

**Multi-select**: when several controls are selected, the Properties window shows only the properties they all
have (never `(Name)`), and a change is applied to every selected control in one undo step.

## 5. Events and methods

```json
"events": [
  {"name": "ValueChanged", "description": "The user changed the Value."},
  {"name": "ItemDrag", "args": "mouse", "description": "e.X, e.Y, e.Button"}
],
"methods": [
  {"name": "SetValue", "signature": "SetValue(value)", "returns": "", "description": "..."}
]
```

* The Events tab lists the package events first (the `defaultEvent` at the top), then the common events
  (unless `"commonEvents": false`). Handlers that exist are bold; double-clicking an event writes the handler
  in the form's language (`rateFood_ValueChanged`) and jumps to it. The `description` is shown in the help box.
* `args`: `none` (default), `mouse` (`e.X`, `e.Y`, `e.Button`), `key` (`e.KeyCode`, `e.KeyChar`), `cancel`
  (`e.Cancel`) - the handler then receives the event-args object like the built-in events.
* IntelliSense: typing `self.rateFood.` (or `Me.rateFood.`) lists the properties, methods (with their
  signature) and events of the manifest.

## 6. Runtimes (one per target)

`targets` maps a language plugin id (`python-tk`, `python-qt`, `ring-qt`, `vb-basic`, ...) to a runtime:

```json
"targets": {
  "python-tk": {"file": "runtime/starrating_tk.py", "class": "StarRating",
                "files": ["runtime/star_helpers.py"], "notes": "needs Pillow"},
  "python":    {"file": "runtime/starrating_any.py", "class": "StarRating"}
}
```

* `file` is the module that defines `class`; `files` are extra files copied with it. Lookup order
  (`radide/components/targets.py`, `chain()`): the plugin id, its toolkit family (`python-tk` for Tk-based
  plugins such as pygame, `python-qt`, `ring-qt`), `python` for every Python toolkit, `bridge` for every GUI
  Bridge language, then the **renderer**: VB6 forms (`vb-basic`, run by the VB runtime) and the GUI Bridge
  languages (C#, Java, JavaScript, C, C++, Go, Rust, Dart, Lua, Perl, PHP, PowerShell, Ruby, Fortran) are drawn
  by the IDE's Tk runtime, so a `python-tk` runtime class serves them too ("via python-tk"), then `*`.
* An entry is one of: `{"native": true}` (built-ins: the language plugin generates it - the per-target code
  of the built-in controls lives in their package folder, `builtin/<Type>/runtime/python_tk.py`,
  `python_qt.py`, `ring_qt.py`, each with `emit(g)`), `{"file", "class"}` (a runtime class),
  `{"emit": "runtime/gen.py"}` (a generator module, any target) or `{"template": {...}}` (declarative
  snippets, any target) - see "Generators and templates" below.
* When the project is saved (Save All / Run), the runtime files of the components its forms use are copied into
  the project folder, so the project runs without the IDE. The generated import falls back to the installed
  package folder (for a user package through `%APPDATA%`/`RADIDE_COMPONENTS_DIR`, for a project package
  relative to the form file) when the copy is missing.
* A target with **no runtime**: the generator writes a placeholder label `[StarRating: no vb-basic runtime]`
  and the Output window shows a warning. The form keeps working in the designer.

**Runtime contract (python-tk / python-qt)** - the generated form code is:

```python
self.rateFood = StarRating(self.root, Value=3, MaxStars=5, ShowValue=True)   # tk: master; qt: parent widget
self.rateFood.rad_bind("ValueChanged", self._ev("rateFood_ValueChanged"))
self.rateFood.place(...)          # tk (Anchor/Dock handled by the form)  /  setGeometry(...) for qt
```

1. `Class(parent, **props)`: every manifest property (except `designOnly`) is passed as a keyword with its
   value, plus the common properties `Text` (when `hasText`), `BackColor`, `ForeColor`, `FontName`,
   `FontSize`, `FontBold`, `FontItalic`, `Enabled` when they differ from the default. Accept `**kwargs` and
   ignore what you do not use.
2. The class is a real widget: a Tk widget for python-tk (`place`, `bind`, `configure` work), a `QWidget` for
   python-qt.
3. `rad_bind(event, callback)` stores the callback; call it when the event happens: `callback()` for an event
   without `args`, `callback(e)` for an event with `args`, where `e` is your own small object with the
   attributes of that kind (`X`, `Y`, `Button` / `KeyCode`, `KeyChar` / `Cancel`; read `e.Cancel` back after
   the call to let the handler cancel). The handler receives `e` unchanged. The common events (Click,
   MouseMove, ...) are bound by the form code itself with the toolkit's normal mechanism.
4. Expose the properties as Python attributes (properties with setters that redraw) and the methods by name,
   so user code can write `self.rateFood.Value = 4` and `self.rateFood.Reset()`.

**VB6 and the GUI Bridge languages** use the python-tk runtime class: VB code and bridge programs reach its
members by their manifest names, case-insensitively - `rate1.Value = 4`, `x = rate1.MaxStars`, `rate1.Reset`
in VB; `set("rate1", "Value", 4)`, `get("rate1", "Value")`, `call("rate1", "SetValue", 2)` over the bridge
(`VBControl._comp_get/_comp_set/_comp_call` in `radide/runtimes/vbrun.py`; values are converted to the
property's type). Package events call `<Control>_<Event>` (a `Sub rate1_ValueChanged()` / `function
rate1_ValueChanged(e)`); an event raised while a bridge handler runs (e.g. by `call("rate1", "Reset")`) is
sent after that handler's `DONE`.

**Runtime contract (ring-qt)** - `"ring-qt": {"file": "runtime/x.ring", "class": "X"}`; the designer file
`load`s the file (copied next to the form on Save All) and writes:

```ring
rate1 = new RatingBar(Form1)                     # init(oParent)
rate1.setValue(3)                                # set<Prop>(value) per property (+ changed common ones)
rate1.radBind("ValueChanged", "rate1_ValueChanged()")   # Ring code to eval when the event happens
rate1.setGeometry(12, 40, 160, 30)
```

The class needs `init(oParent)`, `set<Prop>`, `radBind(cEvent, cCode)` (every event with a handler, common
ones included) and the QWidget methods the form uses (`setGeometry`, `show`, `hide`, `raise`,
`setToolTip`, `setEnabled`): a subclass of a RingQt widget or a class that forwards them (Ring copies objects
on assignment: keep shared state in a global list, as `samples/Tests/Components/RatingBar/runtime/ratingbar.ring`
does).

**Flutter** - a `template` with `widget`: a Dart expression; `{Prop}` is the Dart literal of a property,
`{on_<Event>}` the statements that call the handler; `files` (Dart files) are copied into `lib/` and exported
from `lib/radapp.dart` (the screen designers are `part`s of libraries that import it):

```json
"flutter": {"files": ["runtime/rating_bar.dart"],
            "template": {"widget": "RatingBar(value: {Value}, maxStars: {MaxStars}, onChanged: () {{{on_ValueChanged} }})"}}
```

**Web pages** - a `template` with `html`, `css`, `js` (and `files`); `radide.components.codegen.web_snippet(control)`
returns them filled in, for web page generators (the web workspace has no control-based form designer yet).

### Generators and templates (any target)

`{"emit": "runtime/gen.py"}` - the IDE imports the module at generation time and calls `emit(ctx)`; it returns
the lines (a list) or `{"lines": [...], "handled": ["Event", ...]}` (events it wired itself; the generator
binds the others the usual way). `ctx` (`radide.components.codegen.EmitContext`): `target` (plugin id), `via`
(entry id used), `lang` (`python`/`ring`/`dart`/`js`/`vb`/`json`), `name`, `type`, `props` (all properties,
defaults filled in), `parent` (parent expression), `used` (events with a handler), `entry`, `package`,
`plugin`, `lit(value)` (literal of the target language), `handler(event)`, `add_import(line)` (once per file:
Python imports go before the control's lines, Ring `load`s to the top of the file), `warn(text)`.

`{"template": {...}}` - declarative snippets with `{name}`, `{parent}`, `{left}`, `{top}`, `{width}`, `{height}`,
`{<Prop>}` (literal), `{<Prop>_raw}` (text) placeholders (`{{`/`}}` = a brace):

| key | meaning |
|---|---|
| `imports` | file-level lines, written once (Python: before the control) |
| `create` | lines that create the control |
| `props` | `{"Prop": "setter", "*": "{name}.set{Prop}({value})"}` - one per property (`propsMode: "changed"` = only the ones that differ from the default); common properties only when changed and named |
| `events` | `{"Event": "wiring with {handler} / {event}", "*": ...}` for the events that have a handler |
| `after` | lines written after the setters/events |
| `widget` / `html`, `css`, `js` | Flutter / web (above) |

The generator then adds geometry, ToolTip, Visible and the common events. Errors in package code become a
`WARNING` comment and an Output window warning; generation goes on.

### No runtime for a target

* **Toolbox**: the component is greyed when the shown form's language has no runtime for it; every package's
  tooltip lists "Runs on: ..." / "No runtime for: ..." (`targets.support_text`).
* **Designer**: the control gets a red strip "no <target> runtime", and the Output window names the controls
  (`[components] warning: Form1.rate1 (RatingBar) has no runtime for ...`).
* **Build**: the generated code has a `WARNING` comment and a placeholder label `[RatingBar] no <target> runtime`
  (python-tk, python-qt, ring-qt, Flutter); other plugins get a Label in its place
  (`codegen.placeholder_form`), and the Output window shows the warning on Save All / Run.

Complete multi-target example: `samples/Tests/Components/RatingBar` (python-tk, python-qt, ring-qt, Flutter,
web; VB6 and the bridge languages through python-tk) and the projects `RatingBar_PythonTk`, `_PythonQt`, `_VB`,
`_Ring`, `_JavaScript` next to it.

## 7. Designer drawing (`designer.py`)

Optional; all functions are optional:

```python
def paint(painter, rect, props, ctx):          # simplest: draw with a QPainter
    ...

def create(parent, props, ctx) -> QWidget:     # or build a real Qt widget as the preview
    ...

def apply(widget, props, ctx):                 # update the widget made by create() after a property change
    ...
```

* `props` is the control's property dict; `ctx` has `name`, `type`, `package`, `root` (project folder),
  `resource(path)` (absolute path of a project file) and `icon()`.
* The preview is not interactive (mouse events go to the designer, which selects, moves and resizes it).
* Without `paint`/`create`, the **default renderer** draws a dashed box with the package icon and
  `Name (Type)`. If package code raises, the default renderer is used with the error in red - the IDE keeps
  working. The module is re-imported when the file changes (hot reload).
* `designer.py` runs inside the IDE, so it uses **PyQt6** (the IDE toolkit), whatever the target language.
* The built-in controls draw themselves the same way: `radide/components/builtin/Button/designer.py` creates a
  `QPushButton`, `TabControl/designer.py` a tab bar with a page area, and so on; `radide/preview.py` only
  dispatches (mobile controls and classic controls on a phone form go to `radide/mobile/render.py`, user
  controls to `radide/usercontrols.py`, everything else to the package). The VB look they share (text,
  alignment, Checked, Items, Minimum/Maximum/Value, font, colours, Enabled, the light form palette) is
  `radide.components.classic.apply_classic(widget, props, ctx, special=None, rules=())` - a package that
  wants to look like a built-in control can call it too: `special(widget, props, ctx)` replaces the generic
  "set the text" step, `rules` adds style-sheet declarations (a list, or a function of `props`).
* A property whose value decides which widget `create()` builds (TextBox `Multiline`: `QLineEdit` or
  `QPlainTextEdit`) says `"rebuildPreview": true`; changing it rebuilds the preview.

## 8. Custom property editors (`editors.py`)

```python
EDITORS = {"starrating.stars": StarsEditor(), "starrating.dialog": edit_value_dialog}
```

A property names an editor with `"editor": "starrating.stars"`. An editor is either

* **inline**: an object with `create(parent, value, commit, ctx) -> QWidget` (and optionally
  `set_value(widget, value, ctx)` to update it); the widget lives in the value cell and calls `commit(new)`; or
* **modal**: an object with `edit(parent, value, ctx)` or a plain function `(parent, value, ctx)` returning the
  new value or `None` (cancel); the cell shows a "..." button.

`ctx` gives `name` (property), `propdef`, `props` (all values of the control), `control`, `form`,
`project_folder` and `package`. Use namespaced ids (`<package>.<editor>`). Editors use PyQt6.

## 9. Help (`help.md`)

F1 on a selected control (or its type name in the code editor) opens the package's `help.md`. Document the
properties, events and methods, and an example.

## 10. Packaging, installing, sharing

* **Tools > Component Packages > Manage Component Packages...** (also the "Component Packages..." button of
  the Extension Manager): list of installed packages (tick "Show built-in controls" for all), Install...,
  Uninstall, Export .radcomp..., New Package... (writes a skeleton with tk and qt runtimes), User Control ->
  Package..., Open Folder, Reload.
* A `.radcomp` file is a zip of the package folder (the manifest at the root or in one sub-folder). Install
  asks whether the package is for all projects (`%APPDATA%\RADIDE\components`) or only for the current
  project (`<project>/.radide/components`). The Extension Manager's "Install from file" also accepts
  `.radcomp`. Archives with unsafe paths or more than 100 MB unpacked are refused.
* **Toolbox > right-click > Choose Items...** (like VS "Choose Toolbox Items"): tick which controls the
  Toolbox shows; Browse... installs a `.radcomp`; Reset shows everything again. The Toolbox has a search box
  and collapsible groups (one per `category`).
* **User Control -> Package**: a python-tk / python-qt user control (`radide/usercontrols.py`) becomes a package:
  its declared properties and events become the manifest, its code and designer files the runtime (with an
  adapter class that follows section 6), and a picture of it is the designer drawing.
* **Extensions** can ship packages: put them in the extension folder and list them in
  `radide-extension.json` under `"contributes": {"components": [{"folder": "components/StarRating"}]}`.

Security: `designer.py` and `editors.py` run inside the IDE with your permissions. Install only packages you
trust.

## 11. Versions and conflicts

* A package with the name of a built-in control (or a mobile control) is ignored unless it sets
  `"overrideBuiltin": true`.
* Two non-built-in packages with the same name: the later source wins (`dev` > `project` > `user` >
  `extension`), then the higher `version`. The loser is listed in the Output window (`StarRating: using Star
  Rating 1.1.0 - Project, not Star Rating 1.0.0 - Installed`) and in `REGISTRY.conflicts`.
* Installing an **older** version over a newer one asks first (`allow_downgrade`).
* A user control of the project with the same name wins over a package.
* `requires.radide` greater than the IDE's component API makes the package invalid.

## 12. Developing a package (hot reload)

```bat
set RADIDE_COMPONENT_PATH=D:\work\MyComponents
```

Start the IDE: the packages in that folder are loaded with source `dev` and **hot reload** is on: saving
`component.json`, `designer.py`, `editors.py`, a runtime or the icon reloads the registry, rebuilds the Toolbox,
redraws open designers and refreshes the Properties window. Without the variable, turn it on with Tools >
Component Packages > Hot Reload. Reload Packages reloads by hand.

## 13. Python API (for IDE code)

```python
from radide import components as C
C.REGISTRY.discover()                      # find every package again (fires REGISTRY.on_change listeners)
C.REGISTRY.set_project(folder)             # load a project's .radide/components
C.package_of("StarRating")                 # ComponentPackage (manifest, path, source, version, errors, ...)
C.is_component_type(name), C.is_missing(name)
C.install_package(path_or_radcomp, scope="user" | "project", project_folder=None, allow_downgrade=False)
C.uninstall_package(name, scope="user", project_folder=None)
C.export_package(folder, "StarRating.radcomp"); C.new_package(folder, "MyControl", "Custom")
C.copy_runtimes(project_folder, forms, target_of)
C.validate_manifest(data, folder)          # [] when valid
from radide.components.packaging import export_usercontrol
from radide.components.intellisense import members, member_completions
```

`radide.controls.CONTROL_TYPES` stays the catalogue every generator, the designer and the Properties window
use: the built-in types are built from the built-in packages, and the registry adds, replaces and removes the
other packages' types in it. Code that only knows `CONTROL_TYPES` keeps working.

Language plugins: python-tk and python-qt call `radide.components.codegen.tk_control_lines` /
`qt_control_lines` for package types; other plugins are wrapped by `codegen.wrap_plugin` so package controls
become placeholder labels instead of breaking generation.

## 14. Complete example: StarRating

[`samples/Tests/Components/StarRating`](../samples/Tests/Components/StarRating/) is a complete external
package: a manifest with 10 properties (custom, int, bool, color, enum, padding, multiline design-only), two
events and three methods; `designer.py` (`paint()` draws the stars), `editors.py` (clickable stars inline in the
Value cell, plus a modal editor example), runtimes for python-tk (a `tk.Canvas`) and python-qt (a `QWidget`),
`help.md` and an icon. The test projects
[`StarRating_PythonTk`](../samples/Tests/Components/StarRating_PythonTk/) and
[`StarRating_PythonQt`](../samples/Tests/Components/StarRating_PythonQt/) use it on a form with handlers.

Minimal package to start from (what New Package... writes):

```json
{
  "schemaVersion": 1, "name": "Gauge", "version": "1.0.0", "description": "The Gauge control.",
  "category": "Custom", "defaultSize": [120, 30], "kind": "visual", "hasText": true,
  "properties": [{"name": "Value", "type": "int", "default": 0, "category": "Behavior",
                  "description": "The current value."}],
  "events": [{"name": "ValueChanged", "description": "The Value property changed."}],
  "methods": [],
  "targets": {"python-tk": {"file": "runtime/gauge_tk.py", "class": "Gauge"},
              "python-qt": {"file": "runtime/gauge_qt.py", "class": "Gauge"}},
  "help": "help.md"
}
```

## 15. JSON schema

[`docs/component.schema.json`](component.schema.json) is the JSON Schema (draft 2020-12) of `component.json`;
point `$schema` at it to get validation and completion in editors. It is generated from
`radide/components/schema.py` (`python -m radide.components.schema > docs/component.schema.json`). The IDE's
validator (`validate_manifest`) also checks what a schema cannot express: unique property and event names,
defaults that fit the kind, `enum` defaults that are one of the `choices`, `custom` properties that name an
`editor`, the `defaultEvent`, target ids, `class` given with `file`, files that exist inside the package, and
`requires.radide`.
