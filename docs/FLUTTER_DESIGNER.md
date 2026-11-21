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
| `text_style` | `{"fontSize": 18, "fontWeight": "FontWeight.bold", "color": "#FF1F1F1F", "fontStyle": "FontStyle.italic", "letterSpacing": 1.2, "height": 1.4, "decoration": "TextDecoration.underline", "fontFamily": "Brand", "googleFont": "Poppins"}` | `TextStyle(...)`, or `GoogleFonts.getFont('Poppins', ...)` when `googleFont` is set |
| `shape` | `{"type": "rounded", "radius": 12, "side": {"color": "#FFE0E0E0", "width": 1}}` / `{"type": "circle"}` / `{"type": "stadium"}` | `RoundedRectangleBorder(...)` / `CircleBorder()` / `StadiumBorder()` |
| `button_style` | `{"backgroundColor", "foregroundColor", "padding" (edge_insets), "shape" (shape), "elevation", "minimumSize": [w, h], "textStyle"}` | `ElevatedButton.styleFrom(...)` (the style factory of the button class) |
| `input_decoration` | `{"hintText", "labelText", "helperText", "prefixIcon": "Icons.email", "suffixIcon": "Icons.visibility", "border": "none" \| "outline" \| "underline", "borderRadius", "borderColor", "focusedBorderColor", "filled", "fillColor", "contentPadding" (edge_insets), "hintStyle", "labelStyle" (text_style), "isDense"}` | `InputDecoration(...)` with `OutlineInputBorder(...)` etc. |
| `nav_items` | `[{"icon": "Icons.home", "label": "Home", "activeIcon": "Icons.home_filled"}]` | `BottomNavigationBarItem` / `NavigationDestination` list |
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
  connected but created no Flutter view within 25 s.
- `live.PreviewPane` is the ready-made widget (tool bar + view) used by the designer.
