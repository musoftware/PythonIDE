# Plan: animations, per-size layout variants and foldables

Grounded in the code at commit `ac5477a` (line numbers approximate - re-check before editing).
Implemented in slices A-F by parallel agents; each slice owns its files (see section 4).

## 0. What already exists (build on it)

| Area | What exists | Where |
|---|---|---|
| Keyframe animation for classic forms ("Expression Blend" storyboards) | `form.extra["storyboards"] = [{name, autostart, repeat, autoreverse, tracks:[{target, property, keys:[[ms, value, ease]]}]}]`; runtime `_Storyboard` (Begin/Stop/Pause/Resume/Seek, `<Name>_Completed`); dock "Objects and Timeline" with Record (`RecordBanner`) and Play | `radide/features/timeline.py`: `ANIM_PROPS` ~29, `EASES` ~32, `STORYBOARD_RT` ~34-124, `storyboards_for_code` ~266, `props_at` ~298, `RecordBanner` ~535, `TimelinePanel` ~601, `install` ~1394 |
| Shared Blend runtime + codegen | `COMMON_RT` (`_rad_ease`, `_rad_mix`, `_rad_value_at`), `TK_IO` / `QT_IO` (`_RadIO` get/set of neutral props), `python_blend(form, toolkit)` -> `{runtime, init, after_load, methods}` or None, `BlendPreview` (design-time `design_props`), `PYTHON_PLUGINS` | `radide/features/states.py` |
| Python plugins use it | `PythonTkPlugin._blend()` = `states.python_blend` then `databinding_sql.merge_blend` (chaining precedent); PythonQt inherits; Qt anchors `_Layout` in `LAYOUT_RT` (honours `_rad_held`); Tk `self._places` + `place()` | `radide/languages/python_tk.py` ~678, ~780-788; `python_qt.py` ~101-131, ~327, ~383 |
| VB6 runtime + every GUI-Bridge language | Both build forms by running `PythonTkPlugin.generate_designer` (`runtimes/vbrun.py` ~1597/1661, `runtimes/bridge.py` ~95). Anything added to python-tk codegen automatically works for vb-basic and for C, C++, C#, Dart, Fortran, Go, Java, JS, TS, Lua, Perl, PHP, PowerShell, Ruby, Rust bridge projects. | |
| Design-time override precedent | `LocPreview` (localization): snapshots props, intercepts `doc.controlChanged`, moves edits to an override table, restores base; installs `doc.display_props` (used by `properties.py:_props_dict`) | `radide/features/localization.py` ~579-778, `install` ~919 (wraps `win._designer_menu` ~974) |
| Designer hooks | `DesignerView.design_props`, `form_props`, `blend_recording`, `layout_form`, `on_control_changed`, `live_drag_ok`; `PhoneChrome` = `self.phone` | `radide/designer.py` ~811-944 |
| Devices / orientation (classic mobile forms) | `Device` dataclass, `DEVICES` (5), `ORIENTATIONS`, `safe_area_size`, `MOBILE_FORM_PROPS` (Device/Orientation/Route), `LAYOUT_TYPES`; `PhoneChrome.paint`, `DeviceBar`, `set_orientation`, `_sync_size`, `layout_container`. No per-size overrides exist anywhere. | `radide/mobile/controls.py`, `radide/mobile/frame.py` |
| Flutter designer animations | node `"anim"` with 12 entrance `ANIM_TYPES` (`model.py` ~53); presets/stagger in `flutterdesign/animations.py`; `TreeGen.node` / `wrap_anim` (`codegen.py` ~538-568); `RADFX` constant = `lib/radfx.dart`; importer `_anim` (~949); preview `qtpreview.anim_state`, `preview_host/lib/fx.dart`; inspector `_anim_section`; AnimatedContainer/Opacity/Switcher/Hero in the catalog | `radide/flutterdesign/*` |
| Flutter designer devices | two tuple lists: `flutterdesign/designer.py` ~32 and `flutterdesign/live.py` ~41; `_push_device`, `live.set_device` | |
| Web pages | GrapesJS design view with device combo (`web_site/design.py` ~944) already writes `@media` per device; SuperPreview `PRESETS` (`web_site/superpreview.py` ~36) | |
| Android SDK on this machine | `%LOCALAPPDATA%\Android\Sdk` (emulator, cmdline-tools avdmanager, `system-images/android-36/google_apis_playstore`, AVDs `Medium_Phone`, `ZA_Screens`); Flutter at `C:\flutter`; helpers `features/mobile.py` `sdk_root`, `emulator_exe`, `adb_exe`, `list_avds` | |
| Tests | standalone `samples/Tests/<Area>/<Project>/check_*.py`; Qt UI tests use `samples/Tests/QA/Integration/qh.py` (org `RADIDE-TEST`, app `RADIDE-TEST-<name>`, `QSettings().clear()`, offscreen, `check()/pump()/wait()/window()`); Flutter round-trip precedent `samples/Tests/FlutterDesigner/WidgetTreeScreens/check_roundtrip.py`; each new sample gets a row in `samples/Tests/README.md` | |
| i18n | `radide/i18n/ar.json` `{"strings": {English: Arabic}}`; `tools/extract_ui_strings.py --missing ar`; test `samples/Tests/I18n/ArabicUI/test_ui_language.py` | |

## 1. Contracts (every slice codes against these)

### 1.1 Classic form animation presets: `form.extra["animations"]`
```json
"animations": [
 {"id": "fx1", "target": "Button1",              // "" = the form
  "preset": "slideIn", "params": {"from": "left", "distance": 80},
  "durationMs": 500, "delayMs": 0, "easing": "out",   // linear|in|out|inout|back|elastic|bounce|sine
  "repeat": 1, "autoreverse": false,                   // repeat 0 = forever
  "trigger": {"on": "load",       // load|click|hover|timer|show|hide|after|manual
              "source": "Button2", // control whose event fires it (default = target)
              "intervalMs": 3000,  // timer
              "after": "fx0",      // chained
              "leave": "reverse"}, // hover: reverse|stop|none
  "enabled": true}
],
"motion": {"respectReducedMotion": true}
```
Presets: fadeIn, fadeOut, move (dx/dy), slideIn/slideOut (from), bounce, shake, pulse, rotate, flip (x/y), scaleIn/scaleOut/zoom, colorTo (prop, color), typewriter.

### 1.2 Keyframe extensions (backward compatible, in `COMMON_RT`)
- Key values may be relative: `{"d": -50}` (delta from start), `{"m": 1.1}` (factor), Text `{"reveal": 0..1}` (typewriter); resolved against the start value `_Storyboard._remember()` saves - presets work at every size/variant.
- New easings back, elastic, bounce, sine in `_rad_ease` and `EASES`.
- Virtual track props Rotation, ScaleX, ScaleY only for targets with transforms (Flutter, RN, Kivy, CSS); `expand()` substitutes fallbacks elsewhere (1.4).

### 1.3 `radide/motion/expand.py` -> FxPlan (pure Python)
```python
expand(form, target) -> FxPlan   # target: "py" | "ring" | "kivy" | "rn" | "dart" | "winforms" | "css"
FxPlan = {"storyboards": [{"name": "_fx_fx1", "fx": "fx1", "tracks": [(t, prop, keys)], "repeat": bool,
                           "count": int, "autoreverse": bool, "autostart": bool}],
          "triggers": [{"fx": "fx1", "sb": "_fx_fx1", "on": "click", "source": "Button2", "intervalMs": 0,
                        "after": None, "leave": "reverse"}],
          "fallbacks": [("fx3", "Button1", "Rotate is shown as a wobble on python-tk")],
          "reduced_motion": True}
```
`_fx_` prefix keeps them apart from user storyboards.

### 1.4 Fallback table (owned by `motion/presets.py`)
| Preset | py / vb / bridges / ring / winforms | kivy / rn / dart / css |
|---|---|---|
| rotate | wobble (Left +/-) | real rotation |
| flip | Width -> 0 -> back, Left shifted | ScaleX -1..1 |
| scale | Width/Height around centre + FontSize | transform scale |
| fade on a Tk child widget | blend Fore/BackColor toward parent background, then Visible | opacity |

(Tk child widgets have no alpha: `TK_IO.get` returns 1.0 for Opacity.) Fallbacks must be shown in the Error List, never silent.

### 1.5 Classic form layout variants
`Control` (radide/model.py) gets `variants: dict` (next to `states`), written in `to_dict` when non-empty (so snapshot undo, copy/paste, rename work). Form level:
```json
"variants": {
 "sizes": [
  {"id": "compact",  "label": "Phone",  "when": {"maxWidth": 599},                   "preview": {"width": 400, "height": 800}},
  {"id": "medium",   "label": "Tablet", "when": {"minWidth": 600, "maxWidth": 1023}, "preview": {"width": 800, "height": 1280}},
  {"id": "land",     "label": "Landscape", "when": {"orientation": "landscape"}},
  {"id": "tabletop", "label": "Half-open", "when": {"posture": "half-opened", "fold": "horizontal"},
   "preview": {"device": "galaxy_z_fold6", "orientation": "landscape", "posture": "half-opened"}}],
 "form": {"medium": {"Width": 800, "Height": 1280}}
}
// per control:
{"type": "Button", "props": {...}, "states": {...}, "variants": {"medium": {"Left": 300, "Width": 200, "Visible": false}}}
```
- `when` keys: minWidth, maxWidth, minHeight, maxHeight (client area), orientation (portrait|landscape), posture (folded|half-opened|flat), span (single|dual), fold (vertical|horizontal).
- Matching = CSS cascade: all matching sizes apply in list order, later wins.
- Geometry overrides are absolute at the size's preview size; codegen converts them to per-variant anchor specs via `layout.place_specs(effective_form(...))` so controls still stretch within the range.
- `VARIANT_PROPS`: Left, Top, Width, Height, Anchor, Dock, Visible, Text, FontSize, FontBold, BackColor, ForeColor, TextAlign (+ mobile Align, Spacing, Padding).
- Pure API `radide/variants/model.py`: `sizes(form)`, `overrides(form, ctrl, vid)`, `set_override`, `remove_override`, `matching(sizes, w, h, orientation, posture, span) -> [vid]`, `effective_form(form, size, active) -> Form` (deep copy; base -> `layout.resize_children` -> overrides), `plan(form) -> VariantPlan`:
```python
VariantPlan = {"sizes": [{"id", "when"}], "form": {vid: {prop: v}},
               "controls": {vid: {ctrl: {"props": {...non-geometry...}, "place": Place | None}}}}
```

### 1.6 Foldable devices (extends `mobile/controls.py`; shared pure geometry in new `radide/devices.py`)
- `Device` gains `fold` ("book"|"flip"|"dual"), `fold_axis` ("vertical"|"horizontal" in portrait), `hinge` (dp; 0 = seamless crease), `cover` (w, h) | None, `postures`.
- New mobile form prop `Posture` (Flat|HalfOpened|Folded), shown only for foldables. `screen_size`/`safe_area_size` gain `posture=` (Folded = cover screen).
- `hinge_rect(device_id, orientation, posture) -> (x, y, w, h) | None` in safe-area coords.
- Presets (approximate dp; verify with `avdmanager list device` / specs): galaxy_z_fold6 (inner ~882x1104, cover ~360x860, book), galaxy_z_flip6 (~412x1004, flip, horizontal), pixel_fold (inner ~841x701 landscape-native, cover ~411x797, book), surface_duo2 (2 x ~540x720, dual, hinge ~26dp).

### 1.7 Runtime API for user code (python-tk / python-qt designer class; reachable from VB and bridges)
`self.Animate(target, preset, **opts)`, `self.BeginAnimation("fx1")` / `StopAnimation`, `self.CurrentSizes`, optional `<Form>_SizeVariantChanged`. Test env vars: `RADIDE_POSTURE=half-opened`, `RADIDE_SPAN=dual`, `RADIDE_HINGE=x,y,w,h`, `RADIDE_REDUCED_MOTION=1` (on Windows also `SPI_GETCLIENTAREAANIMATION` via ctypes).

### 1.8 Edit interceptors precedence
Variant "This size only" > Blend Record (states/timeline) > Localization language. Turning on This-size mode switches Blend/timeline Record off; refused (status bar) while `form.props["Language"]` is not Default. Starting Blend Record switches This-size mode off. `doc.display_props` is a single slot: chain it (`prev = doc.display_props`), never replace. `live_drag_ok` must be False in This-size mode.

## 2. Slices

### A - Motion core for classic forms
Owns: `radide/motion/{__init__,presets,model,expand,runtime_py}.py` (new), `radide/features/states.py`, `radide/features/timeline.py`, small additions in `radide/runtimes/vbrun.py`.
1. `presets.py`: `Preset(id, label, group, params_schema, tracks(anim, base_props, form, target))` using relative keys; `CATALOG`, `make`, `describe`; groups Entrance, Exit, Attention, Color, Text; fallback table 1.4.
2. `model.py`: `animations(form)`, `add`, `remove`, `find`, `rename_references(form, old, new)`, `validate(form)` (missing target, `after` cycles, typewriter without Text).
3. `expand.py`: FxPlan (1.3).
4. `states.py`: `COMMON_RT` `_rad_resolve` + new easings; `python_blend`: storyboards + fx storyboards; with triggers append `motion.runtime_py.FX_RT`, init `self._fx = _RadFx(...)`, `FX_METHODS` (Animate, BeginAnimation, StopAnimation); `TK_IO.bind` (Click `<Button-1>`, hover `<Enter>/<Leave>`, add="+"), `QT_IO` event filter (pattern `_RadStateEvents`); Visible set fires show/hide hooks.
5. `timeline.py`: `STORYBOARD_RT` `self.Completed = []` callbacks (chaining), `Count`; new `EASES`; `ANIM_PROPS` unchanged.
6. `runtime_py.py` `FX_RT` `_RadFx`: triggers, timers (`after`/`QTimer`), chains, show/hide (animate then Visible=False on Completed), reduced motion (Seek to end), ad hoc `Animate()`.
7. `vbrun.py`: `VBControl.vb_call` `animate`; `VBForm.vb_call` begin/stopanimation; storyboards as objects with Begin/Stop -> VB `Command1.Animate "shake"`, bridges `CALL Button1 Animate shake`. Document in `docs/CONTRACTS.md`.
Tests `samples/Tests/Motion/`: `check_motion_core.py` (expand every preset per target, relative keys, compile generated tk/qt designers), `Motion_Tk_Presets/`, `Motion_Qt_Presets/` + `check_runtime.py` (fire click, run 1.5 s, assert final geometry/colours; reduced motion), `Motion_VB6/`.
Ship presets/model/expand FIRST - B and D consume them.

### B - Animations panel (UI, design-time preview, final ar.json merge)
Owns: `radide/features/animations_panel.py` (new), `samples/Tests/Motion/test_animations_ui.py`, final merge of all slices' keys into `radide/i18n/ar.json`.
- Dock "Animations" via `states._add_dock(win, "Animations", panel, "dock_animations")`, follows designer; list for selected control (or all); `[+ Add]` preset menu grouped by CATALOG; editors: Trigger + Source + interval + After + hover leave, Duration, Delay, Easing, Repeat (0 = Forever), Auto reverse, Enabled; buttons Preview, Preview all on load, Convert to Storyboard (bake into `extra["storyboards"]` absolute keys), Delete; form checkbox "Respect reduced motion".
- Designer context menu "Add Animation" submenu (wrap `win._designer_menu` like localization).
- Preview: storyboard from `motion.expand(form, "py")`, drive `BlendPreview.of(view).timeline = (sb, ms)` with a QTimer (copy `TimelinePanel._tick/_end_play`), `RecordBanner.set_mode("play", ...)`.
- Edits: `doc.checkpoint()` -> mutate `form.extra` -> `doc.set_modified()`; `rename_references` on `doc.renamed`; Error List shows `validate()` issues and fallbacks.
- Arabic keys: Add Animation=إضافة حركة, Fade In=ظهور تدريجي, Fade Out=اختفاء تدريجي, Move=تحريك, Slide In=انزلاق للداخل, Slide Out=انزلاق للخارج, Bounce=ارتداد, Shake=اهتزاز, Pulse=نبض, Rotate=تدوير, Flip=قلب, Zoom In=تكبير, Zoom Out=تصغير, Color=لون, Typewriter=آلة كاتبة, Trigger=المُشغِّل, On load=عند التحميل, On click=عند النقر, On hover=عند مرور المؤشر, On timer=كل فترة زمنية, On show=عند الإظهار, On hide=عند الإخفاء, After animation=بعد حركة, Manual (from code)=يدويًا (من الشيفرة), Duration (ms)=المدة (مللي ثانية), Delay (ms)=التأخير (مللي ثانية), Repeat=التكرار, Forever=بلا توقف, Auto reverse=عكس تلقائي, Preview all on load=معاينة الكل عند التحميل, Convert to Storyboard=تحويل إلى قصة مصورة, Respect reduced motion=احترام خيار تقليل الحركة.

### C - Layout variants for classic forms (model, designer UI, Python runtime)
Owns: `radide/variants/{__init__,model,runtime_py}.py` (new), `radide/features/variants.py` (new), `radide/model.py`, `radide/designer.py`, `radide/properties.py`, one line in `radide/languages/python_tk.py` `_blend`.
1. `Control.variants` field (to_dict/from_dict).
2. `variants/model.py` API (1.5); default size sets: desktop (Small <640, Medium 640-1023, Large >=1024), phone (Portrait, Landscape), foldable (Folded, Half-open, Flat).
3. `features/variants.py`: sizes bar above each DesignerView with `Edit: [All sizes | This size only]`, size combo, Add Size..., Edit Sizes... dialog, Hide on this size, Side-by-side; `VariantBanner` (copy of RecordBanner, 4px orange frame #F7630C, "This size only: Tablet 800x1280"); `VariantPreview` (LocPreview pattern: edits of VARIANT_PROPS go to `ctrl.variants[vid]` / `extra.variants.form[vid]`, base restored; `design_props`/`form_props` from `effective_form`; All-sizes mode with a size selected previews it, edits go to base; chain `doc.display_props`; `doc.prop_marker(owner, name)` -> ◆ overridden here / ◇ overridden elsewhere; `doc.prop_menu` adds Apply to all sizes, Reset to base, Copy to >, Hide/Show on this size); precedence 1.8; "Sizes" dock gallery of thumbnails (effective_form -> hidden preview widget -> grab, 250 ms debounce, click selects, orange outline on overridden, ghosted hidden); install by wrapping `win.open_designer` like localization.
4. `designer.py`: consult `_variant_preview` in design_props/form_props; `live_drag_ok` False in this-size mode; apply design_props on change; hatch hidden controls.
5. `properties.py`: marker prefix + tooltip in `_refresh_values`; `doc.prop_menu` in `_props_menu`. Additive only; do not touch component-package schema logic (`_defs`).
6. `variants/runtime_py.py` `VARIANTS_RT` `_RadVariants`: Qt Resize event filter / Tk `<Configure>` add="+"; diff matching ids, restore base, apply via `io.set`; geometry via `owner._places` + place_configure (Tk) or `_Layout.items` + `lay.apply()` / setGeometry (Qt); respect `_rad_held`; posture/span from env; `merge_variants(res, form, toolkit)` adds COMMON_RT + IO only if `class _RadIO` absent. TwoPane on desktop toolkits = two placed frames split at Ratio honouring `RADIDE_HINGE`.
7. `python_tk._blend`: `return merge_variants(merge_blend(res, form, toolkit), form, toolkit)` -> python-qt, vbrun and all bridge languages get variants.
Tests `samples/Tests/Variants/`: `check_variants_model.py`, `test_variants_ui.py` (qh.py), `Variants_Qt_Responsive/` + `check_runtime.py` (resize across breakpoints for Qt, Tk, vbrun .frm).
Arabic keys: Edit:=التحرير:, All sizes=كل المقاسات, This size only=هذا المقاس فقط, Sizes=المقاسات, Add Size...=إضافة مقاس..., Edit Sizes...=تحرير المقاسات..., Apply to all sizes=تطبيق على كل المقاسات, Reset to base=إعادة إلى الأساس, Copy to=نسخ إلى, Hide on this size=إخفاء في هذا المقاس, Show on this size=إظهار في هذا المقاس, Overridden on this size=مُعدَّل في هذا المقاس, Overridden on other sizes=مُعدَّل في مقاسات أخرى, Side-by-side=متجاورة, Portrait=عمودي, Small=صغير, Medium=متوسط, Large=كبير, Phone=هاتف, Tablet=جهاز لوحي.

### D - Non-Python targets (animations, variants, TwoPane codegen)
Owns: `radide/languages/ring_qt.py` (+ Ring runtime), `radide/mobile/codegen_dart.py`, `codegen_kivy.py`, `codegen_rn.py`, `rn_runtime.py`, `radide/foreign/winforms_cs.py`/`winforms_vb.py` (generated partial only), `radide/web/grapes/` additions (`radfx.css`, `radfx.js`, "Animate" trait), `radide/web_site/design.py` (orange frame + This size only for GrapesJS devices).
- ring-qt (+ ring-script/app/game): `radfx.ring` runtime (QTimer tick, same easings, triggers via existing event wiring); variants via the existing anchor re-place block with if-chains per size.
- flutter classic: reuse F's `radfx.dart` (RadKeyframes); `RadVariants.match` inside the existing LayoutBuilder, `rv.pick(base, {...})`, `!rv.hides('id')`; TwoPane -> `RadTwoPane` from F's `radlayout.dart`.
- kivy: `kivy.animation.Animation` chains, hover via `Window.bind(mouse_pos)`, Rotate/Scale canvas instructions; variants on root `on_size`; foldable fallback documented.
- expo (RN): `Animated` sequences/timing, useNativeDriver, Pressable onPress/onHoverIn, `AccessibilityInfo.isReduceMotionEnabled()`; `useWindowDimensions()` picks; foldable fallback documented.
- WinForms C#/VB.NET (phase 2, risky): generated `Form1.RadFx.cs/.vb` partial (Timer-based), never touch `.Designer.cs`; OnLoad/OnResize only if the user file doesn't override them (else warn "call RadFx.Attach(this)"); sidecar `Form1.radide.json` for extra.
- Web (GrapesJS): Animate trait -> `class="radfx radfx-bounce"`, `data-radfx-trigger`, `data-radfx-delay`; `radfx.css` (keyframes + prefers-reduced-motion) + `radfx.js` (IntersectionObserver, click/hover/timer, chains) linked on save; orange frame + "This size only" label on non-desktop devices; foldable devices + `@media (horizontal-viewport-segments: 2)` / `(device-posture: folded)` blocks.
- Not applicable (documented in CONTRACTS): godot/godot3d, rust-cargo, web sites without forms (use GrapesJS), vb6 .frm export (vbrun plays it), Delphi/Lazarus/Qt .ui/NetBeans foreign forms (sidecar + Error List warning).
Tests: `samples/Tests/Motion/Targets/`, `samples/Tests/Variants/Targets/` `check_targets.py`; flutter analyze / ring run / dotnet build on temp copies when toolchains exist; web page computed animation names.
Arabic keys: Animate=تحريك, Animate on=التحريك عند.

### E - Foldable devices
Owns: `radide/mobile/controls.py`, `radide/mobile/frame.py`, `radide/mobile/render.py` (TwoPane preview), `radide/features/mobile.py` (AVD helpers), `radide/web_site/superpreview.py` (presets only), new `radide/devices.py`.
1. Device presets + Posture prop (1.6); `form_prop_defs` shows Posture only for foldables; `_sync_size` follows posture.
2. Hinge drawing in `PhoneChrome.paint`: dual = opaque bezel band; book/flip Flat = dashed crease; HalfOpened = crease + gradient shading one half + "Hinge" label; controls crossing a dual hinge get a red dashed outline + Error List warning from pure `hinge_conflicts(form)`.
3. DeviceBar posture buttons; public `PhoneChrome.preview(device, orientation, posture)` (draw a variant's preview device without changing form props; used by C).
4. TwoPane classic control in `mobile/controls.py` (`LAYOUT_TYPES`): PaneMode Auto|Horizontal|Vertical, Ratio 0.5, SinglePane Start|End, HingeAware True; exactly two child containers; `frame.layout_container` splits at `hinge_rect` or Ratio; single screen shows SinglePane only.
5. `features/mobile.py`: `foldable_avd()` creates an AVD (`avdmanager create avd ... -d "<foldable device id>"`, check `avdmanager list device -c` and the image ABI), menu "Create Foldable Emulator", `set_posture(serial, state)` (`adb emu fold/unfold` or `cmd device_state state n`, verify).
6. SuperPreview foldable presets + "dual segments" option.
Tests: `samples/Tests/Mobile/Foldables/check_devices.py`, `test_hinge_ui.py` (qh.py, grab per posture), `samples/Tests/Mobile/Flutter_Foldable/check_foldable.py` (emulator if present, else SKIP; offline widget tests with `tester.view.displayFeatures`).
Arabic keys: Posture=الوضعية, Folded=مطوي, Half-open=نصف مفتوح, Flat=مفتوح بالكامل, Hinge=المفصل, Two Pane=لوحتان, Create Foldable Emulator=إنشاء محاكي قابل للطي, Controls cross the hinge=عناصر تعبر المفصل.

### F - Flutter designer: motion + variants + foldables (`radide/flutterdesign`)
New files: `flutterdesign/motion.py`, `flutterdesign/variants_fd.py`, `flutterdesign/dart/radfx.dart`, `flutterdesign/dart/radlayout.dart`, samples `samples/Tests/FlutterDesigner/MotionScreens/`, `ResponsiveScreens/`. Then hook edits in model.py, codegen.py, importer.py, inspector.py, designer.py, qtpreview.py, live.py, preview_host fx.dart.
1. Schema (additive, SCHEMA_VERSION stays 1; unknown keys already preserved):
```json
"anim": {"type": "shake", "trigger": "tap", "repeat": 0, "reverse": true}
"anim": {"type": "keyframes", "durationMs": 1200, "trigger": "load",
         "tracks": {"opacity": [[0,0],[300,1,"Curves.easeOut"]], "offsetY": [[0,40],[600,0]], "scale": [[0,0.8],[600,1]],
                    "rotation": [[0,0],[600,0.05]], "color": [[0,"#FF..."],[600,"#FF..."]]}}
// screen
"state": [{"name": "expanded", "type": "bool", "init": false}],
"timelines": [{"name": "intro", "durationMs": 1500, "autostart": true, "repeat": false, "reverse": false}],
"transition": {"type": "fade", "durationMs": 300},
"variants": [{"id": "medium", "label": "Tablet", "when": {"minWidth": 600}}, {"id": "tabletop", "when": {"posture": "half-opened"}}]
// node
"vprops": {"medium": {"padding": {"all": 32}, "$hidden": true}}
// prop values
{"$when": {"state": "expanded", "on": 200, "off": 100}}                                        // implicit
{"$timeline": "intro", "from": 0, "to": 1, "interval": [0, 0.5], "curve": "Curves.easeOut"}   // explicit
// events: "toggle:expanded" "play:intro" "reverse:intro" "push:Home?transition=fade&ms=300"
```
New ANIM_TYPES: shake, pulse, bounce, flipX, flipY, rotate, swing, heartBeat, typewriter, colorTo, keyframes. Triggers: load|tap|hover|longPress|visible|manual|state:<field>.
2. Catalog: implicit AnimatedPadding/Align/Positioned/Scale/Rotation/Slide/Size/DefaultTextStyle/CrossFade; explicit Fade/Slide/Scale/Rotation/SizeTransition (animation prop kind `timeline`); Lottie, RiveAnimation (library deps); RadTwoPane (slots start/end), RadShow (internal); validation.
3. Codegen: delegate `wrap_anim` to `motion.wrap`; `$when`/`$timeline`/`vprops` emission (non-const propagation; flutter_lints clean); TickerProviderStateMixin + controllers + dispose + autostart; state fields; `final rv = RadVariant.of(context, _radSizes);`; RadFx triggers (GestureDetector/MouseRegion/visibility), repeat/reverse, TweenSequence keyframes, `MediaQuery.disableAnimationsOf` -> final state, `RadRoute` (fade/slide/scale/none); `radlayout.dart` (RadVariant from size/orientation/displayFeatures -> posture/fold/span, `rv.pick`, RadShow, RadTwoPane via DisplayFeatureSubScreen with ratio fallback); pubspec deps lottie/rive; `onGenerateRoute` only when a screen has a transition (careful main.dart merge).
4. Importer: new RadFx args, RadKeyframes, `rv.pick` -> vprops, RadShow -> $hidden, `cond ? a : b` on a bool state field -> $when, controllers -> timelines, CurvedAnimation drive -> $timeline, Lottie/Rive nodes, RadRoute -> push transition; keep id matching.
5. Preview: qtpreview `anim_state` new types/keyframes, Lottie/Rive placeholders; preview host fx.dart same maths; device message with posture + displayFeatures.
6. UI: inspector anim section (trigger, repeat, keyframe table, timeline picker), Timelines + State sections; toolbar Edit: All sizes / This size only + size combo, orange canvas frame, ◆ markers, row menu Apply to all / Reset to base / Copy to / Hide on this size; side-by-side renders; DEVICES unified via `radide/devices.py` (E) with foldables + posture toggle + hinge drawing.
Tests: MotionScreens/ResponsiveScreens `check_roundtrip.py`, flutter analyze clean, flutter test (motion with disableAnimations; responsive with `tester.view.physicalSize` and `displayFeatures`), TemplateGallery byte-identical regression.
Arabic keys: Timelines=الخطوط الزمنية, Play timeline=تشغيل الخط الزمني, State variables=متغيرات الحالة, Page transition=انتقال الصفحة, Keyframes=الإطارات الرئيسية, Lottie animation=حركة Lottie, Rive animation=حركة Rive (reuse C's size keys and E's posture keys).

## 3. Coverage per plugin
| Plugin | Animations | Variants | Foldable |
|---|---|---|---|
| python-tk, python-qt, arcade, pygame, ursina | A | C | env simulation + TwoPane frames |
| vb-basic (vbrun) | free via Tk generator; VB API in A | free | same |
| all GUI-Bridge languages, javascript, typescript | free; `CALL obj Animate x` | free | same |
| ring-qt family | D | D | ratio fallback |
| flutter (classic) | D | D | D |
| kivy | D | D | fallback |
| expo | D | D | fallback |
| WinForms .Designer.cs | D phase 2 | D phase 2 | n/a |
| other foreign forms | sidecar + warning | sidecar + warning | n/a |
| web sites | GrapesJS radfx (D) | GrapesJS @media + orange frame (D) | viewport segments / posture CSS (D, E) |
| godot, rust-cargo | n/a | n/a | n/a |
| Flutter designer screens | F | F | F |

## 4. Order and file ownership
- Day 1: A (presets/model/expand + COMMON_RT), C (Control.variants + variants/model.py), E (devices, Posture, hinge_rect).
- Then: B (needs A), C UI + runtime, E UI/emulator, D against the contracts, F (new files first, then hook pass).
- Last: D finishes classic Flutter (needs F's Dart files); B merges all ar.json keys and runs `tools/extract_ui_strings.py --missing ar`.
- Ownership: states.py/timeline.py = A; python_tk.py, designer.py, properties.py, model.py = C; mobile/frame.py, mobile/controls.py = E; non-Python codegen = D; flutterdesign/* = F; ar.json final merge = B (others may add their keys with small targeted edits too).

## 5. Risks
1. Three interceptors on `doc.controlChanged` (LocPreview, BlendPreview record, VariantPreview) - enforce 1.8; live drags must not bypass.
2. `doc.display_props` single slot - chain.
3. Anchors + absolute overrides - resolve per variant via place_specs; test resizes across breakpoints; respect `_rad_held`.
4. `python_blend` may return None - variant and fx merges add `_RadIO`/`COMMON_RT` exactly once.
5. Tk has no alpha/rotation - fallbacks visible in the Error List.
6. Flutter const-correctness with rv.pick/$when/$timeline; main.dart merge for transitions; Lottie/Rive pub deps and preview placeholders.
7. Component packages (schema-driven Toolbox/Properties, `radide/components/*`) may be in progress - don't touch `radide/components/*` or `properties.py` `_defs`.
8. WinForms extra doesn't survive `.Designer.cs` - sidecar; OnLoad/OnResize collisions - detect and warn.
9. Foldable dp values approximate - verify; device_state numbers vary by image.
10. Snapshot undo covers `extra` and `Control.variants` only via `to_dict`.

## 6. Follow-up gaps (closed)
- Preview per target: the Animations panel previews with `expand(form, preview_target(win, form))` (python-qt real
  opacity, transform targets scale / rotate through `states.FxEffect`, python-tk / VB / bridges the fallbacks).
  Test `samples/Tests/Motion/test_preview_targets_reorder.py`.
- Reorder animations: Move Up / Move Down + drag in the list over `motion.model.move` (same test).
- The Error List hinge warning refreshes on designer changes (`features/mobile.watch_hinge`); device labels
  translated (`devices.display_name`). Test `samples/Tests/Mobile/Foldables/test_hinge_live.py`.
- Flutter folded posture: fold memory + cover-screen shape heuristic in `RadVariant.compute`; `RadTwoPane`
  converts the hinge to local coordinates (`localHinge`). Test
  `samples/Tests/FlutterDesigner/ResponsiveScreens/test/foldable_posture_test.dart` (flutter test).
- Reduced motion on Windows: mocked `SystemParametersInfoW` (Python runtime, Kivy runtime, a generated tk form),
  one real read-only call; the user's setting is never changed. Test
  `samples/Tests/Motion/check_reduced_motion_windows.py`.
