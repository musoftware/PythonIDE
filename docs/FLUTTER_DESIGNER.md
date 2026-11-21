# Flutter Designer - screen format, catalog, code generation and import

The advanced Flutter designer composes **real widget trees** (FlutterFlow style) instead of the VB-style
absolute `.form` layout of CONTRACTS 10.1. This document is the shared contract of the agents working on it:

| Area | Files | Owner |
|---|---|---|
| model | `radide/flutterdesign/model.py` (schema, catalog, tree ops, patches), `codegen.py` (tree -> Dart), `importer.py` + `dart_tools/` (Dart -> tree) | model |
| ui | `radide/flutterdesign/designer.py`, `inspector.py`, `palette.py`, `radide/features/flutter_designer.py` | ui |
| render | `radide/flutterdesign/preview_host/` (Flutter web app that renders a tree), `live.py` | render |
| assets | `radide/flutterdesign/assets.py`, `themes.py`, `animations.py`, `templates/`, samples | assets |

Python code reads the catalog from `radide.flutterdesign.model` (`CATALOG`, `widget_spec()`), the preview host can
get it as JSON: `python -m radide.flutterdesign.model --catalog-json > catalog.json` (or `model.catalog_json()`).

---------------------------------------------------------------------------------------------------------------

## 1. Screen file `<Screen>.fscreen.json`

One file per screen. Convention: `<project>/screens/<Name>.fscreen.json` (any folder of the project works; the
designer opens every `*.fscreen.json`). UTF-8 JSON, written with 1-space indent and keys in the order below.

```json
{
 "version": 1,
 "name": "Login",                       // Dart class name (PascalCase identifier), unique in the project
 "route": "/login",                     // named route; default "/" + snake(name)
 "theme": {                             // optional, per screen (wraps the tree in Theme(...) when not empty)
  "seedColor": "#FF6750A4",             //   ColorScheme.fromSeed
  "brightness": "light",                //   light | dark
  "fontFamily": "Poppins",              //   a Google font (textTheme) - also listed in "fonts"
  "background": "#FFFFFFFF"             //   scaffoldBackgroundColor
 },
 "assets": ["assets/images/background.png"],          // files the screen uses (pubspec flutter/assets)
 "fonts": [{"family": "Poppins", "source": "google"},  // google_fonts package
           {"family": "Brand", "source": "asset",
            "files": [{"asset": "assets/fonts/Brand-Regular.ttf"},
                      {"asset": "assets/fonts/Brand-Bold.ttf", "weight": 700, "style": "normal"}]}],
 "imports": ["package:intl/intl.dart"],   // optional extra imports of the generated file
 "code": {                                // optional, verbatim Dart kept for round-trips (import of hand code)
  "prelude": "final size = MediaQuery.of(context).size;",   // statements before `return` in build()
  "members": "Widget _logo() => const FlutterLogo();"        // extra fields / methods of the State class
 },
 "tree": { "type": "Scaffold", "id": "w1", "props": {}, "slots": {"body": { ... }} }
}
```

### 1.1 Node

```json
{
 "id": "w7",                 // stable, unique in the screen ("w" + number); never reused after delete
 "type": "Container",        // Flutter widget class (catalog key) or "Code"
 "ctor": "asset",            // optional named constructor: Image.asset, ElevatedButton.icon, GridView.count ...
 "name": "txtEmail",         // optional VB-like name: a field in the State class (controllers, values)
 "props": { ... },           // constructor arguments (JSON values, section 2)
 "slots": {"child": {...}},  // named widget parameters: child, body, appBar, title, leading, trailing ...
 "children": [ ... ],        // the list parameter of multi-child widgets (children / tabs / actions ...)
 "events": {"onPressed": "onLogin"},
 "anim": {"type": "fadeInUp", "delayMs": 300, "durationMs": 600, "offsetY": 30}
}
```

Only `id` and `type` are required; empty `props` / `slots` / `children` / `events` and absent `anim` may be
omitted. Rules (checked by `model.validate()`):

- `slots` keys must be slots of the widget's catalog entry. A slot holds **one node**, except slots marked
  `multi` (`AppBar.actions`, `Scaffold.persistentFooterButtons`) which hold a **list of nodes**.
- `children` is allowed only for widgets whose catalog entry has `children` (the Dart parameter name, e.g.
  `"children"`, `"tabs"`); single-child widgets use the `child` slot.
- `Positioned` belongs in a `Stack`, `Expanded` / `Flexible` / `Spacer` in a `Row` / `Column` / `Flex`
  (warnings otherwise, like Flutter's runtime errors).
- `name` must be a Dart identifier, unique in the screen. Widgets whose catalog entry has `needs_name`
  (TextField, Checkbox, Switch, Slider, DropdownButton ...) always get one (`model.insert` assigns `txt1`,
  `chk1` ...): the generated State holds `final txtEmail = TextEditingController();`, `bool chkRemember = false;`
  and the widget is wired with `setState` so the screen works without user code (an unnamed one gets a
  private field `_<id>`, e.g. `_w12`). The value property (`Checkbox.value`, `Slider.value`, ...) is the
  field's initial value.

### 1.2 "Code" nodes (anything the designer does not model)

```json
{"id": "w9", "type": "Code", "props": {"code": "FadeAnimation(1.5, #{slot:child})"},
 "slots": {"child": {"id": "w10", "type": "Text", "props": {"data": "Hi"}}}}
```

`props.code` is a Dart expression emitted verbatim. `#{slot:<name>}` markers are replaced by the generated code
of the node (or list of nodes, rendered `a, b, c`) in `slots[<name>]`, so widgets inside unknown helpers stay
designable. The preview shows a Code node as a dashed placeholder box with its first slot inside it. Collection
`if` / `for` / spread elements and calls like `_buildHeader()` import as Code nodes.

### 1.3 Events

`events` maps a callback parameter of the widget (catalog `events`) to an action:

| value | generated Dart |
|---|---|
| `"onLogin"` | tear-off of a handler method `onLogin` written by the user (section 4) |
| `"nav:/home"` | `() => Navigator.pushNamed(context, '/home')` |
| `"replace:/home"` | `() => Navigator.pushReplacementNamed(context, '/home')` |
| `"push:Home"` | `() => Navigator.push(context, MaterialPageRoute(builder: (context) => const Home()))` |
| `"back"` | `() => Navigator.pop(context)` |
| `"validate:form1"` | `() => form1.currentState!.validate()` (a `Form` named `form1`, section 1.7) |
| `"validate:form1:onSubmit"` | `() { if (form1.currentState!.validate()) { onSubmit(); } }` (`onSubmit` = a handler) |

A button without an `onPressed` event is generated with `onPressed: () {}` (enabled, as designers expect).
Handler signatures come from the catalog (`"onChanged": "String value"` for TextField, `"bool? value"` for
Checkbox, `"int index"` for BottomNavigationBar.onTap ...).

### 1.4 Animations (`anim`)

```json
{"type": "fadeInUp", "delayMs": 400, "durationMs": 600, "offsetX": 0, "offsetY": 30, "curve": "Curves.easeOut",
 "scale": 0.8}
```

`type`: `fadeIn`, `fadeInUp`, `fadeInDown`, `fadeInLeft`, `fadeInRight`, `slideUp`, `slideDown`, `slideLeft`,
`slideRight`, `scaleIn`, `zoomIn`, `bounceIn`. Defaults: `delayMs` 0, `durationMs` 500, offsets 30 px for the
directional types (`offsetY` > 0 = starts below; `fadeInDown` / `fadeInLeft` default to -30), `curve`
`Curves.easeOut`, `scale` 0.8 for scaleIn, 0.3 for zoomIn / bounceIn. `slide*` types move without fading.
An `anim` on `Positioned` / `Expanded` / `Flexible` is generated around their child (they must stay direct
children of their Stack / Flex); the importer lifts it back onto the parent-data widget.
Generated code wraps the widget in `RadFx(...)`, a small helper written by RAD IDE (`lib/radfx.dart`, no
third-party package). The importer also turns `FadeAnimation(delay, child)`-style helpers and animate_do widgets
(`FadeInUp(delay: ..., child: ...)`) into `anim` (`"from": "<original helper>"` records where it came from).

Since the motion work (`flutterdesign/motion.py`, plan `docs/plans/MOTION_VARIANTS_FOLDABLES.md`) an `anim` can
also be an attention seeker, text / colour effect or keyframes, with a trigger:

```json
{"type": "shake", "trigger": "tap", "repeat": 0, "reverse": true}
{"type": "keyframes", "durationMs": 1200, "tracks": {"opacity": [[0, 0], [300, 1, "Curves.easeOut"]],
  "offsetY": [[0, 40], [600, 0]], "scale": [[0, 0.8], [600, 1]], "rotation": [[0, 0], [600, 0.05]],
  "color": [[0, "#FF6750A4"], [1200, "#FF00BFA5"]]}}
{"type": "rotate", "trigger": "manual", "controller": "spinFx"}      // final spinFx = RadFxController();
{"type": "fadeIn", "trigger": "state:expanded"}                       // play: expanded
```

More types: `shake`, `pulse`, `bounce`, `flipX`, `flipY`, `rotate` (`turns`), `swing`, `heartBeat`, `typewriter`,
`colorTo` (`color`), `keyframes` (`tracks`, rotation in turns). `trigger`: `load` (default), `tap`, `hover`,
`longPress`, `visible` (first time on screen), `manual` (a `RadFxController` field, started with the
`play:<name>` event or `name.forward()`), `state:<bool state variable>` (forward when true, back when false).
`repeat`: runs (0 = forever, default 1); `reverse`: play back after each run. Entrance types are hidden until they
play; attention seekers rest at their normal look. `MediaQuery.disableAnimations` (reduced motion) shows the end
state at once. The twelve original types generate exactly the same code as before.

### 1.5 State, timelines, page transitions

```json
"state": [{"name": "expanded", "type": "bool", "init": false}],
"timelines": [{"name": "intro", "durationMs": 1500, "autostart": true, "repeat": false, "reverse": false}],
"transition": {"type": "fade", "durationMs": 300}
```

* State variables are fields of the designer State. A property value
  `{"$when": {"state": "expanded", "on": 200, "off": 100}}` is generated `expanded ? 200 : 100` (implicit
  animation: put it on an `AnimatedContainer` / `AnimatedPadding` / `AnimatedCrossFade` ... property). Events:
  `toggle:expanded` -> `setState(() => expanded = !expanded)`.
* Timelines are `AnimationController`s (`TickerProviderStateMixin`, disposed, `autostart` through
  `radPlay(intro, context)` after the first frame). Transition properties (`FadeTransition.opacity`,
  `SlideTransition.position`, `ScaleTransition.scale`, `RotationTransition.turns`, `SizeTransition.sizeFactor`:
  prop kinds `timeline` / `timeline_offset`) take
  `{"$timeline": "intro", "from": 0, "to": 1, "interval": [0, 0.5], "curve": "Curves.easeOut"}` ->
  `radDrive(intro, 0.0, 1.0, end: 0.5, curve: Curves.easeOut)` (a plain number = `AlwaysStoppedAnimation`).
  A `$timeline` on a plain **number** property (`double` / `int`: `Container.width`, `Opacity.opacity`,
  `Text.maxLines` ...) really animates: the widget is generated inside
  `AnimatedBuilder(animation: intro, builder: (context, child) => Container(width: radDrive(intro, 80.0, 220.0).value))`
  (`.value.round()` for an int, `Listenable.merge([a, b])` for two timelines); the importer turns it back into
  `$timeline` values. Other kinds (colours ...) and parent-data widgets (`Positioned.left` ...) keep the old
  behaviour: a warning and the end value.
  Events: `play:intro` (`intro.forward(from: 0)`), `reverse:intro`.
* `transition` (`fade` | `slideLeft` | `slideUp` | `scale` | `none`): the screen class gets
  `static const transition = RadRouteSpec(...)`; `routes.dart` moves it from `designedRoutes` to
  `designedOnGenerateRoute` and `lib/main.dart` gets `onGenerateRoute: designedOnGenerateRoute`. An event
  `push:Home?transition=slideUp&ms=400` pushes with `RadRoute(...)`.
* Catalog: implicit `AnimatedPadding / Align / Positioned / Scale / Rotation / Slide / Size / DefaultTextStyle /
  CrossFade`, explicit `Fade / Slide / Scale / Rotation / SizeTransition`, `Lottie` (package:lottie, added to
  pubspec) and `RiveAnimation` (package:rive). Previews: the live preview host plays Lottie files with
  package:lottie (`Lottie.network` on the served project asset; a placeholder when it cannot be loaded); the Qt
  preview draws the **first frame** of a `Lottie.asset` file (`flutterdesign/lottie_thumb.py`: shape / solid /
  image / precomp layers, transforms, fills, strokes; masks, mattes, trim paths and effects are ignored) with a
  "Lottie 2.0s" tag, else the placeholder. `RiveAnimation` stays a placeholder in both previews: the current
  package:rive (0.14) renders through rive_native, whose web/wasm and native binaries are fetched by a separate
  `dart run rive_native:setup` step (not by `flutter pub get`), which does not fit the once-per-Flutter-version
  host build; the older 0.13 line (rive_common, what generated projects use) was not added because RAD IDE has no
  original `.riv` file to verify the host with (`.riv` is a binary format made with the Rive editor).

### 1.6 Sizes (layout variants) and foldables

```json
"variants": [{"id": "compact", "label": "Phone", "when": {"maxWidth": 599}, "preview": {"width": 412, "height": 915}},
             {"id": "tabletop", "label": "Half-open", "when": {"posture": "half-opened"},
              "preview": {"device": "galaxy_z_fold6", "posture": "HalfOpened"}}]
// node
"vprops": {"compact": {"padding": {"all": 8}, "$hidden": true}, "tabletop": {"$hidden": false}}
```

`when`: `minWidth`, `maxWidth`, `minHeight`, `maxHeight`, `orientation` (portrait | landscape), `posture`
(flat | half-opened | folded), `span` (single | dual: a hinge, or a fold that is half opened), `fold` (vertical |
horizontal: direction of the fold line). Every matching size applies in list order, the later one wins (like CSS)
- also for `$hidden`, so a widget hidden on `compact` can be shown again on `tabletop`. Generated code uses
`lib/radlayout.dart`: `static const _radSizes = [RadSize('compact', maxWidth: 599), ...]`,
`final rv = RadVariant.of(context, _radSizes);` (MediaQuery size + display features), `rv.pick(base,
[RadV('compact', value), ...])` and `RadShow(hidden: rv.pick(false, [...]), child: ...)`. `RadTwoPane` (slots
`start` / `end`, `paneMode`, `ratio`, `singlePane`, `hingeAware`) splits at the hinge / fold, else at the ratio,
and shows one pane on a narrow screen.

Designer: the second tool bar row has **Edit: All sizes | This size only**, the size being edited (its preview
device is shown, the canvas gets an orange frame), **Sizes** (add a preset set, add / edit / remove sizes) and
**Side-by-side**; foldable devices (`radide/devices.py`: Galaxy Z Fold6 / Flip6, Pixel Fold, Pixel 9 Pro Fold,
Surface Duo 2) add a posture choice and the hinge / crease is drawn. In This size only mode property edits go to
`vprops` (◆ = overridden on this size, ◇ = on another size); right-click a property name for Apply to all sizes,
Reset to base, Copy to, Hide / Show on this size, and to animate the value with a state variable or timeline.
Structural edits (add, move, delete) always change every size. The previews render
`variants_fd.preview_data(screen, active sizes)`; the live host receives the device's display features.

### 1.7 Data widgets: item templates, rich text, forms, radio groups (`flutterdesign/datawidgets.py`)

```json
{"type": "ListView", "ctor": "builder", "props": {"itemCount": 6, "items": ["Apple", "Banana"]},
 "slots": {"itemBuilder": {"type": "ListTile", "slots": {"title": {"type": "Text", "props": {"data": {"$code": "item"}}},
                                                        "subtitle": {"type": "Text", "props": {"data": {"$code": "'Row $index'"}}}}}}}
{"type": "GridView", "ctor": "builder", "props": {"crossAxisCount": 3, "mainAxisSpacing": 8, "itemCount": 9},
 "slots": {"itemBuilder": {...}}}
{"type": "Text", "ctor": "rich", "props": {"spans": [{"text": "Fruit "}, {"text": "Market", "style": {"fontWeight": "FontWeight.bold"}}]}}
{"type": "RichText", "props": {"spans": [...], "style": {...root span style}, "textAlign": "TextAlign.center"}}
{"type": "Form", "name": "form1", "props": {"autovalidateMode": "AutovalidateMode.onUserInteraction"}, "slots": {"child": ...}}
{"type": "TextFormField", "name": "txtEmail", "props": {"validators": [{"rule": "required"}, {"rule": "email"},
   {"rule": "minLength", "value": 8, "message": "At least 8 characters"}, {"rule": "regex", "value": "^[0-9]{7,15}$"}]},
 "events": {"validator": "checkEmail"}}
{"type": "RadioGroup", "name": "rdoPlan", "props": {"groupValue": "free"}, "events": {"onChanged": "planChanged"},
 "slots": {"child": {"type": "Column", "children": [{"type": "RadioListTile", "props": {"value": "free"}, ...},
                                                    {"type": "Radio", "props": {"value": "team"}}]}}}
```

* **ListView.builder / GridView.builder** (ctor `builder`): `itemCount` and one item template in the slot
  `itemBuilder`. The template reads `index` and - when `items` (sample data, a string list) is set - `item`
  (= `items[index % items.length]`) in `$code` values. Generated: `itemBuilder: (context, index) => <template>` or
  a block `{ const items = [...]; final item = items[index % items.length]; return <template>; }`;
  GridView.builder gets `gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount, mainAxisSpacing,
  crossAxisSpacing, childAspectRatio)`. Switching the constructor in the inspector moves the first child into the
  template (and back). Previews: `variants_fd.preview_data` expands the template `itemCount` times (40 at most)
  with `item` / `index` substituted in simple values (`item`, `index`, `'Row ${index + 1}'`, `item.toUpperCase()`
  ...); the first copy keeps the model ids, the others are `<id>~<n>` and select the template when clicked.
* **Text.rich / RichText** (`text_spans` values): `Text.rich(TextSpan(children: [TextSpan(text:, style:), ...]))`
  inherits the DefaultTextStyle; `RichText(text: TextSpan(style: <style>, children: [...]))` does not (give the
  spans a colour). A span that is not `TextSpan(text:, style:)` (WidgetSpan ...) imports as a `{"$code"}` item.
* **Form**: a named Form gets `final form1 = GlobalKey<FormState>();` and `key: form1`; buttons validate it with
  the events `validate:form1` / `validate:form1:onSubmit` (section 1.3). **TextFormField.validators** (rules
  `required`, `email`, `minLength`, `maxLength`, `regex` - the whole text must match - each with an optional
  `message`) and the event `validator` (a custom handler `String? checkX(String? value)` in the events file:
  null = valid) generate `validator: radValidate(const [RadRule.required(), RadRule.email()], custom: checkX)`
  with the helper `lib/radform.dart` (written when used); only a handler: `validator: checkX`. Rules run in order,
  the first message wins, the custom handler runs last; empty text passes every rule except `required`.
* **RadioGroup** (Flutter 3.41 API, no deprecated `groupValue` / `onChanged` on the radios): a named state field
  `String? rdoPlan = 'free';`, `RadioGroup<String>(groupValue: rdoPlan, onChanged: (value) => setState(...))`;
  `Radio(value: 'x')` and `RadioListTile(value: 'x', title: ...)` anywhere inside it.

## 2. Property values

Every property value is plain JSON; the catalog gives each property a **kind** that decides the encoding.
Any property may instead hold **raw Dart**: `{"$code": "MediaQuery.of(context).size.width * .8"}` (emitted
verbatim; the importer uses it for everything it cannot model, so hand code round-trips). Properties that are
not in the catalog are allowed only as `$code` values (extra named arguments such as `key`).

| kind | JSON | Dart |
|---|---|---|
| `string` | `"Login"` | `'Login'` (escaped; use `$code` for interpolation) |
| `int`, `double` | `12`, `12.5`, `"infinity"` | `12`, `12.5`, `double.infinity` |
| `bool` | `true` | `true` |
| `color` | `"#FF8F94FB"` (AARRGGBB), `"Colors.white"`, `"Colors.grey.shade300"`, `"scheme.primary"` | `Color(0xFF8F94FB)`, `Colors.white`, `Colors.grey.shade300`, `Theme.of(context).colorScheme.primary` |
| `enum` | `"MainAxisAlignment.center"` (full name, values in the catalog `ENUMS`) | same |
| `edge_insets` | `{"all": 16}` / `{"h": 20, "v": 8}` / `{"l": 0, "t": 8, "r": 0, "b": 8}` (missing = 0) | `EdgeInsets.all / symmetric / only` |
| `border_radius` | `12` (all corners) / `{"tl": 12, "tr": 12, "bl": 0, "br": 0}` | `BorderRadius.circular(12)` / `BorderRadius.only(...)` |
| `alignment` | `"Alignment.center"` / `{"x": 0, "y": -0.5}` | `Alignment.center` / `Alignment(0, -0.5)` |
| `icon` | `"Icons.email_outlined"`, `"CupertinoIcons.home"` | same |
| `offset` | `[0, 10]` | `Offset(0, 10)` |
| `duration` | `300` (milliseconds) | `Duration(milliseconds: 300)` |
| `string_list` | `["Home", "Search"]` | `['Home', 'Search']` (DropdownButton items ...) |
| `image` | `{"source": "asset", "src": "assets/bg.png"}` / `{"source": "network", "src": "https://..."}` | `AssetImage('...')` / `NetworkImage('...')` |
| `gradient` | `{"type": "linear", "begin": "Alignment.topCenter", "end": "Alignment.bottomCenter", "colors": ["#FF8F94FB", "#998F94FB"], "stops": [0, 1]}`; `{"type": "radial", "center": "Alignment.center", "radius": 0.5, "colors": [...]}`; `{"type": "sweep", ...}` | `LinearGradient / RadialGradient / SweepGradient` |
| `box_shadows` | `[{"color": "#338F94FB", "blur": 20, "spread": 0, "offset": [0, 10]}]` | `[BoxShadow(...)]` |
| `border` | `{"color": "#FFE0E0E0", "width": 1}` (all sides) / `{"top": {...}, "bottom": {...}, "left":..., "right":...}` | `Border.all(...)` / `Border(top: BorderSide(...))` |
| `box_decoration` | `{"color", "gradient", "image": {"source", "src", "fit": "BoxFit.cover"}, "borderRadius", "border", "boxShadow", "shape": "BoxShape.circle"}` | `BoxDecoration(...)` with `DecorationImage(image: ..., fit: ...)` |
| `text_style` | `{"fontSize": 18, "fontWeight": "FontWeight.bold", "color": "#FF1F1F1F", "fontStyle": "FontStyle.italic", "letterSpacing": 1.2, "height": 1.4, "decoration": "TextDecoration.underline", "fontFamily": "Brand", "googleFont": "Poppins", "shadows": [{"color": "#55000000", "blur": 2, "offset": [1, 1]}]}` | `TextStyle(...)`, or `GoogleFonts.getFont('Poppins', ...)` when `googleFont` is set |
| `shape` | `{"type": "rounded", "radius": 12, "side": {"color": "#FFE0E0E0", "width": 1}}` / `{"type": "circle"}` / `{"type": "stadium"}` | `RoundedRectangleBorder(...)` / `CircleBorder()` / `StadiumBorder()` |
| `button_style` | `{"backgroundColor", "foregroundColor", "padding" (edge_insets), "shape" (shape), "elevation", "minimumSize": [w, h], "textStyle"}` | `ElevatedButton.styleFrom(...)` (the style factory of the button class) |
| `input_decoration` | `{"hintText", "labelText", "helperText", "prefixIcon": "Icons.email", "suffixIcon": "Icons.visibility", "border": "none" \| "outline" \| "underline", "borderRadius", "borderColor", "focusedBorderColor", "filled", "fillColor", "contentPadding" (edge_insets), "hintStyle", "labelStyle" (text_style), "isDense"}` | `InputDecoration(...)` with `OutlineInputBorder(...)` etc. |
| `nav_items` | `[{"icon": "Icons.home", "label": "Home", "activeIcon": "Icons.home_filled"}]` | `BottomNavigationBarItem` / `NavigationDestination` list |
| `text_spans` | `[{"text": "Hello ", "style": {text_style}}, {"$code": "WidgetSpan(...)"}]` | `TextSpan(children: [TextSpan(text: ..., style: ...), ...])` |
| `validators` | `[{"rule": "minLength", "value": 8, "message": "..."}]` (section 1.7) | `radValidate(const [RadRule.minLength(8, '...')])` |
| `constraints` | `{"minWidth", "maxWidth", "minHeight", "maxHeight"}` | `BoxConstraints(...)` |
| `code` | `"..."` | verbatim |

Number props accept ints or floats. Colors given as `"#RRGGBB"` are read as opaque. `model.normalize_value(kind,
value)` canonicalises (e.g. `"#rgb"` -> `"#FFRRGGBB"`, upper case).

## 3. Catalog (`model.CATALOG`)

`CATALOG: dict[str, WidgetSpec]`, about 90 widgets in categories *Layout, Scroll, Content, Input, Buttons,
Material, Navigation, Effects, Animation, Cupertino, Special*. `WidgetSpec` fields:

| field | meaning |
|---|---|
| `type`, `category`, `help` | class name, palette group, one-line description |
| `props: dict[str, PropSpec]` | `PropSpec(kind, default, values (enum), positional (index or None), required, group, help)` |
| `slots: dict[str, SlotSpec]` | `SlotSpec(multi=False, required=False, accepts=None)` - named widget parameters |
| `children: str or None` | Dart name of the widget-list parameter (`"children"`, `"tabs"`), None = no children |
| `events: dict[str, str]` | callback parameter -> handler parameter list (`"onChanged": "String value"`) |
| `ctors: dict[str, CtorSpec]` | named constructors (`Image.asset`, `ElevatedButton.icon`, `GridView.count`) with their own props/slots |
| `parent` | expected parent types (`Positioned` -> `("Stack",)`) |
| `needs_name`, `value_prop`, `value_type` | stateful inputs: the State field holding the value |
| `const_ctor` | the Dart constructor is `const` (codegen emits `const` where it can) |
| `library` | `material` / `cupertino` / `widgets` / `google_fonts` |
| `template` | the node `model.new_node(type)` creates (sensible defaults: a Container gets a size, a Text a text) |

Helpers: `widget_spec(type, ctor=None)`, `categories() -> {category: [types]}`, `can_have_child(type)`,
`accepts(parent_type, child_type, where)`, `default_props(type)`, `ENUMS` (enum name -> values),
`catalog_json()`.

## 4. Generated Dart (codegen.py)

`codegen.generate_screen(screen, user_code=None) -> GeneratedScreen(designer_path, designer_code, events_path,
events_code)`; `codegen.write_screen(project_folder, screen)` writes the files, adds missing handler stubs to the
user file, updates `pubspec.yaml` (assets, fonts, `google_fonts`), writes `lib/radfx.dart` and
`lib/screens/routes.dart`; `codegen.write_all(project_folder)` does that for every `*.fscreen.json`.

For `screens/Login.fscreen.json`:

- `lib/screens/login.dart` - **generated, rewritten on every save** (VB designer file): imports,
  `part 'login_events.dart';`, `class Login extends StatefulWidget` (with `static const route = '/login'`) and
  `abstract class LoginDesigner extends State<Login>` holding the named fields, abstract handler declarations,
  `dispose()` and `build()`. Formatted with `dart format` (Flutter SDK), falling back to a built-in formatter.
- `lib/screens/login_events.dart` - **the user's file** (`part of 'login.dart';`):
  `class LoginEvents extends LoginDesigner { @override void onLogin() { ... } }`. Created once; later RAD IDE
  only appends stubs for new handlers. It can use every named widget field (`txtEmail.text`, `chkRemember`).
  Extra imports go into the screen's `"imports"` (part files cannot import).
- `lib/screens/routes.dart` - generated: `final Map<String, WidgetBuilder> designedRoutes = {Login.route: ...}`
  for every screen; RAD IDE Flutter projects merge it into `lib/main.dart` routes.
- `lib/radfx.dart` - the animation helper (`RadFx`), written when a screen uses `anim`.
- `lib/radform.dart` - the validator rules helper (`radValidate`, `RadRule`), written when a TextFormField has
  `validators`. Handlers of the `validator` event are declared `String? checkX(String? value);` and their stubs
  `return null;`.
- `pubspec.yaml` - asset folders of `"assets"` (only folders that exist), asset fonts, and `google_fonts` when a
  text style / the theme uses a Google font.

The generated code is `const`-correct (passes `flutter_lints` with no issues: `flutter analyze` clean) and uses
`BorderRadius.circular`, `EdgeInsets.*`, `ElevatedButton.styleFrom` like hand-written Flutter code.
RAD IDE Flutter projects call `codegen.integrate_rad_project(folder, main_code, has_forms)` from
`radide/languages/flutter.py` `write_project_files`, so saving / running the project regenerates every designed
screen and keeps `...designedRoutes` in `lib/main.dart`; a project made only of screens starts on the first one.
`push:<Screen>` events import the target screen's file automatically.

## 5. Import (importer.py + dart_tools/)

`importer.import_dart(source, class_name=None, previous=None) -> ImportResult(screens: list[dict], report:
list[tuple[level, text]])` and `importer.import_file(path, ...)`. A small Dart CLI built on `package:analyzer`
(`radide/flutterdesign/dart_tools/bin/fsimport.dart`) parses the file (no resolution needed) and prints a JSON
expression tree of every `build()` method; Python maps it onto the catalog. The CLI is compiled once with the
Flutter SDK's `dart compile exe` into `%LOCALAPPDATA%\RADIDE\cache\flutterdesign\` (rebuilt when its source
changes); `importer.ensure_tool()` builds it, `importer.tool_status()` says whether it is ready.

- Constructor calls (with or without `const` / `new`), named constructors, positional + named arguments,
  nested lists, `Colors.*`, `Color(0x..)`, `Color.fromRGBO/fromARGB`, `EdgeInsets.*`, `BorderRadius.*`,
  `BoxDecoration`, gradients, shadows, `TextStyle`, `GoogleFonts.*`, `Icons.*`, `Image.asset/network`,
  `Theme.of(context).colorScheme.*`, navigation closures and handler tear-offs become model values.
- Anything else becomes `{"$code": ...}` (a property) or a `Code` node (a widget), kept verbatim; statements
  before `return` go to `code.prelude`, other class members to `code.members`, imports to `imports`.
- Composite values fall back piece by piece: one unknown colour inside a gradient becomes `{"$code": ...}` in
  the `colors` list, the rest of the BoxDecoration stays designable.
- A `Code` node whose text is a catalog widget call (e.g. pasted `Text(...)`) is imported back as that widget.
- Animation helpers: `RadFx(...)` (round trip), `FadeAnimation(delaySeconds, child)` and animate_do widgets
  (`FadeInUp(duration: ..., delay: ..., from: ..., child: ...)`, default 100 px) become `anim`; their imports are
  dropped when nothing else uses them.
- `static const route` / `routeName` of the widget class gives `route`; State fields bound to inputs
  (`controller: emailController`, `value: chk` + the generated `setState` closure) become widget names.
- `previous` (a screen dict) keeps node ids stable: nodes at the same path with the same type keep their ids.
- The report lists what was imported exactly and what became Code / `$code`; `ImportResult.stats[name]` has
  `exact`, `code_nodes`, `code_props`, `anim_helpers`.
- `importer.import_expression(dart_expr) -> node` imports one pasted widget expression.
- `void main() => runApp(MaterialApp(home: <widget tree>, theme: ThemeData(colorSchemeSeed: ...)))` (also a
  block body) becomes a screen named after `title` (else `Home`) with route `/`; a widget class whose build()
  returns such a MaterialApp is imported as its `home` tree. `home: const HomePage()` of a class of the same file
  is left alone (that class is imported itself). Other MaterialApp arguments are reported as dropped.
- Colours with `.withValues(alpha: a)`, `.withOpacity(a)` and `.withAlpha(n)` on `Color(0x...)`, `Colors.x` and
  `Colors.x.shade300` become `#AARRGGBB` (alpha = round(a * 255)); `TextStyle(shadows: [Shadow(...)])` becomes
  `shadows`. Scheme colours with an alpha stay `$code`.
- Data widgets (section 1.7): `ListView.builder` / `GridView.builder` with `(context, index) => ...` or the
  generated block body, `Text.rich`, `RichText(text: TextSpan(...))`, `radValidate(...)`, `key: <GlobalKey<FormState>
  field>`, the `validate:` closures, `RadioGroup<String>` bindings and the AnimatedBuilder of timeline values.
- The designer name of a plain widget (not in the Dart code) is kept from `previous`.

## 6. Tree operations and undo (model.py)

`Screen` wraps the dict (`Screen.load(path)`, `Screen.new(name, route=None)`, `.save(path)`, `.to_dict()`,
`.find(id)`, `.parent_of(id) -> (parent_node, Where)`, `.walk()`, `.new_id()`, `.validate() -> list[Issue]`).

Every edit is a function returning an applied **Patch** (a list of primitive changes); `model.apply_patch(screen,
patch)` re-applies it and `model.invert(patch)` gives the undo patch - feed them to a `QUndoCommand`:

```python
p = model.insert(screen, parent_id="w3", node=model.new_node("Text", screen), where=Where(index=0))
p = model.move(screen, "w8", "w3", Where(slot="child"))
p = model.wrap(screen, "w8", "Padding", props={"padding": {"all": 16}})   # Padding/Center/Container/Expanded/Column/Row/Stack/SizedBox/Card/...
p = model.unwrap(screen, "w9")          # replace a single-child wrapper (or one-child Column) by its child
p = model.delete(screen, "w8");  p = model.duplicate(screen, "w8")   # fresh ids (+ names) for the copy
p = model.set_prop(screen, "w8", "color", "#FF2196F3")   # value None removes the property
p = model.set_event(screen, "w8", "onPressed", "onLogin");  p = model.set_anim(screen, "w8", {...})
model.apply_patch(screen, model.invert(p))                 # undo
```

`Where` = `Where(index=n)` (children list), `Where(slot="body")`, or `Where(slot="actions", index=n)` (multi slot).
Primitive changes are JSON (`{"op": "put", "parent": id|None, "where": {...}, "old": node|None, "new":
node|None}` and `{"op": "set", "id": id, "field": "props"|"events"|"anim"|"name"|"ctor", "key": k, "old": v,
"new": v}`), so patches can also travel to the preview host.

## 8. Live preview (preview_host/ + live.py)

- **Host**: `radide/flutterdesign/preview_host/` is a Flutter web app (`lib/factory.dart` builds real widgets for
  every catalog type, `values.dart` decodes section 2 values, `theme.dart` themes / fonts, `fx.dart` the entrance
  animations, `nodebox.dart` the per-node wrapper). It is built once with `flutter build web --release` into
  `%LOCALAPPDATA%\RADIDE\flutter-preview-host\<flutter version>-<source hash>\build\web` (about 2 minutes; rebuilt
  only when the host sources or the Flutter version change) - `live.host_ready()`, `live.build_host_sync()`,
  `live.HostBuilder` (async, used by the UI).
- **Server + bridge**: `live.PreviewServer` serves the host at `/` and the project folder at `/project/` (assets,
  fonts). Messages go in through `window.radHost.deliver(json)` and come back through the
  QWebChannel object `radBridge`; the protocol is documented at the top of
  `preview_host/lib/main.dart`. Python sends the whole screen once and then only model patches (section 6),
  debounced (`LivePreview.DEBOUNCE_MS`); a property change is rendered and its new rects are back in about
  50-100 ms.
- **Host -> IDE**: `rects` (global rect of every built node, device rect, zoom), `click` / `dblclick` / `context`
  (deepest node first, with the path to the root), `hover`, `issues` (per node: render errors, unbounded sizes,
  invalid property combinations), `event` (interact mode), `rendered` (latency).
- **Every node** is wrapped in a `NodeBox` (`ValueKey('rad:<id>')`) whose RenderBox is registered by id: rects,
  design-mode hit testing (a click anywhere in a box selects it, Spacers are widened to the Row/Column), error
  mapping. A child that asks for an infinite size (e.g. an `InkWell` without a child inside a `ListView`) is
  given a 48 px error box and reported as an error issue on its node instead of breaking the whole preview.
- **Device**: size / orientation / text scale / dark / RTL / frame (`LivePreview.set_device`, `rotate`), design
  vs interact mode (`set_mode`), `play()` / `stop_animations()`, `select(id, reveal=True)` (scrolls lazy lists
  until the node is built and opens the drawer that contains it).
- **Exact mode**: `LivePreview.start_exact(project, route)` runs `codegen.write_all` + `flutter run -d web-server`
  and shows the real app in the same view; `exact_reload()` (PreviewPane.screen_saved) regenerates and hot
  reloads. The first debug compile takes 40-90 s; a watchdog reloads the page (twice at most) when the app
  connected but created no Flutter view within 25 s. Cold starts are measured by
  `samples/Tests/FlutterDesigner/DataFormsScreens/test_exact_coldstart.py [runs] [--watchdog off]`. With the watchdog off,
  15 cold starts in a row (Flutter 3.41.9, Windows 11) all showed the app on the first load: the Flutter view appeared
  0.3-3 s after the app connected and nothing ever needed a reload. The blank first load did not come back, so the
  watchdog stays as a safety net.
- **Project theme**: the designer reads `screens/app.ftheme.json` (themes.py): the live host gets it through
  `LivePreview.set_app_theme(spec)`, the Qt canvas uses it (as `themes.screen_theme`) when the screen has no theme
  of its own. `FlutterDesigner.refresh_theme()` re-reads it and redraws canvas, inspector swatches and live
  preview; `designer.refresh_project_theme(folder)` refreshes every open designer of a project and is called by
  the App Theme editor after Save.
- **Lottie / Rive**: the host depends on package:lottie (plays `Lottie` nodes from the served project);
  `RiveAnimation` stays a placeholder (see the note in section 1.5).
- `live.PreviewPane` is the ready-made widget (tool bar + view) used by the designer.
