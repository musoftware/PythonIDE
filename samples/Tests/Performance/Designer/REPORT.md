# Classic forms designer - performance review (measure, fix, re-measure)

Harness: [`perf_designer.py`](perf_designer.py).

```
.venv\Scripts\python samples\Tests\Performance\Designer\perf_designer.py --runs 5 --tag after --profile
    [--real] [--only startup,codegen,designer,vb6,monaco,run] [--controls 400]
set RADIDE_CODE_ROOT=<folder>   measure another copy of radide (the "before" baseline)
set PERF_OUT=<folder>           results_<tag>_<platform>.json + prof_<tag>_<platform>\<operation>.txt
```

* `time.perf_counter` around each action, then the event loop is settled until idle for 80 ms ("settled" = deferred
  QTimer work included); a 5 ms QTimer heartbeat records the longest freeze; median / p95 over N runs; cProfile top
  lists for every operation over budget (interactive 100 ms, drag frame 16 ms, open 300 ms, start-up).
* Start-up: a fresh process per run. F5: `run_project()` -> first visible window of a process the IDE started
  (windows seen: "Greeter" = VB6/vbrun, "Form1" = Tk).
* Generated projects: copies of `Languages/PythonTk_Form` and `VB_Form` + `BigForm` (400 controls: menu 6x8, tool
  strip, timer, 8 panels with nested group boxes, TabControl 3 pages with group boxes, ListBox with 1000 Items,
  ~150 loose controls) + a 5000-line Python file; VB6 forms of `samples/VB6/Business` and `samples/Tests/VB6Compat`.
* Machine: 16 logical CPUs at 100 % load from other agents during every run - absolute numbers are pessimistic.
  "Before" = the same tree with only the files changed here restored from HEAD. Designer phase: 5 runs after,
  3 runs before (p95 of 3 = about the max).

## Offscreen platform (QT_QPA_PLATFORM=offscreen)

| Operation | Before: median (p95) ms | After: median (p95) ms | Speed-up |
| --- | ---: | ---: | ---: |
| startup.process_wall_to_settled | 11299 (13758) | 6465 (8011) | 1.7x |
| startup.mainwindow_init | 7320 (9345) | 3839 (4808) | 1.9x |
| startup.show | 1749 (2332) | 842 (967) | 2.1x |
| startup.usable | 9321 (12048) | 4821 (5993) | 1.9x |
| startup.settled | 10744 (13181) | 6045 (7509) | 1.8x |
| startup.components_registry | 101 (183) | 60 (100) | 1.7x |
| project.open (PythonTk, 2 forms) | 353 (462) | 239 (336) | 1.5x |
| designer.open small (Form1) | 265 (275) | 165 (172) | 1.6x |
| designer.open big (400 controls) | 2673 (2778), settled 3826 | 1454 (1511), settled 1582 | 1.8x |
| select.click control (Properties tab) | 201 (215) | 9.5 (57) | 21x |
| select.click control (Events tab) | 158 (188) | 11 (13) | 14x |
| select.form (Esc) | 251 (272) | 62 (67) | 4.1x |
| select.multi 50 | 236 (237) | 49 (51) | 4.8x |
| select.from Document Outline | 297 (316) | 3.4 (44) | 88x |
| edit.undo (property, Document Outline shown) | 3814 (3876), settled 5318 | 69 (80) | 56x |
| hover.mouse move (per event) | 9.2 (9.6) | 2.5 (2.6) | 3.6x |
| drag.move 1 control (per mouse move) | 32.9 (33.0) | 8.8 (9.0) | 3.7x |
| drag.move group of 50 (per mouse move) | 37.8 (40.4) | 15.2 (15.4) | 2.5x |
| drag.resize handle (per mouse move) | 35.4 (36.6) | 10.0 (10.1) | 3.6x |
| drag.rubber band (per mouse move) | 7.5 (87.5) | 1.7 (12.6) | 4.3x |
| drag.rubber band release (selects ~50) | 687 (693) | 121 (125) | 5.7x |
| drag.release 1 / group of 50 | 13.3 / 73.1 | 13.2 / 66.5 | 1.0x / 1.1x |
| key.arrow nudge 1 / 50 controls (per key) | 36.9 / 100.2 | 24.3 / 79.4 | 1.5x / 1.3x |
| prop.Text / Font / BackColor (single) | 7.4 / 5.8 / 7.5 | 6.6 / 5.6 / 6.0 | ~1.1x |
| prop.BackColor (50 selected) | 83.6 (84.2) | 67.8 (70.8) | 1.2x |
| prop.form Text | 2002 (2144) | 15.1 (15.5) | 133x |
| edit.undo (property) | 5287 (5298), settled 6919 | 72 (75) | 74x |
| edit.redo (property) | 5278 (5306), settled 6879 | 73 (77) | 73x |
| select.ListBox with 1000 Items | 1886 (1923) | 82 (83) | 23x |
| prop.Items (1000 lines) | 20.8 (21.9) | 16.9 (18.6) | 1.2x |
| edit.add control (Toolbox double-click) | 4577 (4602), settled 6134 | 57.5 (59.2) | 80x |
| edit.copy 50 | 8.3 (9.1) | 7.6 (8.2) | 1.1x |
| edit.paste 50 | 5714 (6058), settled 7551 | 227 (235) | 25x |
| edit.delete 50 | 5232 (5271), settled 6689 | 162 (164) | 32x |
| edit.undo (delete 50) | 6913 (7091), settled 8514 | 179 (187) | 39x |
| view.zoom 150% / back to 100% | 226 / 225 | 228 / 239 | 1.0x |
| view.F7 first time (create code view) | 839 (853) | 264 (270) | 3.2x |
| view.F7 Design->Code | 775 (788), settled 2245 | 218 (218), settled 1143 | 3.6x |
| view.Shift+F7 Code->Design | 751 (758) | 197 (248) | 3.8x |
| view.switch tab -> small form | 2626 (2654) | 207 (210) | 12.7x |
| view.switch tab -> big form | 3731 (3833), settled 5108 | 210 (213) | 17.8x |
| file.save all (big form modified) | 875 (883), settled 2358 | 113 (116) | 7.8x |
| toolbox.search typing (per char) | 5.6 (6.4) | 5.0 (5.5) | 1.1x |
| toolbox.rebuild | 36.5 (36.9) | 6.9 (7.2) | 5.3x |
| codegen.python-tk generate_designer (400 controls) | 779 (820) | 53 (54) | 14.6x |
| codegen.python-qt generate_designer | 657 (688) | 46 (48) | 14.4x |
| codegen.vb-basic / csharp-bridge | 5.6 / 0.9 | 5.4 / 1.4 | - |
| vb6.designer open (each of 11 .frm) | 3631 (3829) | 593 (694) | 6.1x |
| monaco.open 5000-line file (until ready) | 672 (714) | 702 (734) | 1.0x |
| monaco.keystroke round trip | 42 (233) | 17 (337) | noisy |
| monaco.IntelliSense list shown | 443 (729) | 364 (402) | 1.2x |
| monaco.scroll 5000 lines (per rAF frame) | 59 (86) | 54 (86) | 1.1x |
| run.F5 VB6 (vbrun) until window | 573 (668) | 482 (503) | 1.2x |
| run.F5 Python Tk until window | 285 (300) | 279 (280) | 1.0x |

## Normal Windows platform (real windows, no screenshots; before 1 run, after 3 runs)

| Operation | Before ms | After median (p95) ms | Speed-up |
| --- | ---: | ---: | ---: |
| startup.usable / settled | 8356 / 9717 | 6259 / 7565 | 1.3x |
| designer.open big (400 controls) | 1816 | 1513 (1528) | 1.2x |
| select.click control (Properties tab) | 132.5 | 9.8 (57.1) | 13.5x |
| select.from Document Outline | 137 | 5.5 (47.7) | 25x |
| edit.undo (property, Document Outline shown) | 1656 | 74 (75) | 22x |
| drag.move 1 control / group of 50 (per move) | 48.8 / 52.9 | 29.9 / 31.0 | 1.6x / 1.7x |
| drag.resize / rubber band (per move) | 49.9 / 72.8 | 28.9 / 29.7 | 1.7x / 2.5x |
| prop.form Text | 482 | 13.8 | 35x |
| edit.undo / redo (property) | 2045 / 2114 | 76 / 74 | 27x / 28x |
| select.ListBox with 1000 Items | 621 | 81 | 7.6x |
| edit.add control | 2062 | 58 | 36x |
| edit.paste 50 / delete 50 / undo delete | 2424 / 2344 / 2798 | 225 / 162 / 190 | 11x / 14x / 15x |
| view.F7 / Shift+F7 | 349 / 323 | 166 / 153 | 2.1x |
| view.switch tab -> small / big form | 996 / 1139 | 152 / 160 | 6.5x / 7.1x |
| file.save all | 919 | 112 | 8.2x |
| view.zoom 150% | 229 | 248 | 0.9x |

On the real platform text drawing is much cheaper (offscreen font rendering made each icon cost several ms), so the old
code was "only" 1-2.8 s per Undo there instead of 5-9 s. Drag steps on the real platform (~30 ms) are dominated by
the window flush (the rubber band repaints a tiny region and still takes ~30 ms; 1.7 ms offscreen).

## Hotspots found and fixes

| Hotspot (profile evidence) | Fix | File |
| --- | --- | --- |
| Document Outline drew one control icon per control on every rebuild (drawText ~7 ms each): ~4 s per Undo | drawn icons cached per type (mobile icons stay uncached: Material colours can change) | `radide/toolbox.py` |
| Document Outline rebuilt twice per Undo (structureChanged + controlChanged(None)) even hidden behind Solution Explorer (tabbed docks report isVisible()) | rebuilt only when the tree changed; while its tab is hidden it waits for dock.visibilityChanged | `radide/features/doc_outline.py` |
| Sizes gallery rendered the whole form in a hidden designer 250 ms after every change, also behind the Properties tab: 2-3 s after each drag / edit | renders only when really on screen (visibleRegion), and when its tab is shown | `radide/features/variants.py` |
| DesignerView.rebuild recreated all 400 previews on every add / delete / paste / undo / rename (~2 s) | previews whose type, properties and container are unchanged are kept (z-order restored); full rebuild while a visual state / timeline / sample data / language / layout size / phone frame is shown | `radide/designer.py` |
| O(n^2) model queries: Form.find linear, ordered() and descendants() scanned all controls per container, relayout() on every drag step | name index validated on each hit, children_map(), O(n) ordered(); relayout skips forms without docked controls; snap targets once per drag | `radide/model.py`, `radide/layout.py`, `radide/designer.py` |
| Whole transparent overlay repainted on every drag / rubber-band step (repaints every preview under it) | only the old + new selection handles / snaplines / band rectangle | `radide/designer.py` |
| Properties window rebuilt every row and editor widget (combos, font lists) on every selection | rows and editor widgets kept while the property list is the same | `radide/properties.py` |
| Accessibility naming searched the whole grid for a buddy label for each new cell editor (~30 ms each) | grid cell editors skipped | `radide/features/perf_a11y.py` |
| Code generation compiled one regex per event of every control (5460 patterns, re cache 512) | compiled-pattern cache; Python plugins read the handler names once (output byte-identical on 232 form/language cases) | `radide/languages/base.py`, `radide/languages/python_tk.py` |
| Save: path.resolve() per control while loading the per-target emitters | resolved paths cached | `radide/components/codegen.py` |
| Tab switch: three whole-window typed findChildren (PyQt's typed search is slower than an untyped one) | one untyped search | `radide/features/settings.py` |
| Git: the 5 s background refresh ran 4-5 git processes on the UI thread afterwards | the background query also returns the git dir; the listener reuses it | `radide/features/git_panel.py`, `radide/features/git_full.py` |
| Start-up: app style sheet applied after all widgets existed (~2 s re-polish); then setStyle("Fusion") on every theme apply because the style-sheet proxy has no name (~1.7 s, also on each theme change) | theme applied at the start of MainWindow.__init__; identical sheet not re-applied; base style remembered | `radide/app.py`, `radide/theme.py` |
| Start-up: dock_tabbar_fix searched the whole widget tree 24 times; 9 provider registrations each refilled the AI agent / chat lists; light form palette rebuilt per preview | direct children only; one providers_changed for the batch; palette cached | `radide/features/dock_tabbar_fix.py`, `radide/features/ai_web.py`, `radide/theme.py` |

## Tests after the changes

VSParity 116/116; Components IDE_Gaps 27/27, RatingBar_VB6Frm 15/15, RatingBar_Flutter 18/18; Variants
check_variants_model ALL OK (50), test_variants_ui 62/62, check_runtime ALL OK (40); Motion check_motion_core ALL
PASSED (41), test_animations_ui 52/52, test_motion_designer 10/10, test_preview_targets_reorder 47/47, check_vb6
ALL PASSED (15); I18n test_ui_language 25/26 - the failing check ("no Arabic left in the main window": the VS
Code extensions panel keeps Arabic text) fails the same way on the old code. Git panel checked in a live IDE.

## Remaining slow spots

* Start-up still 4.8 s (offscreen) / 6.3 s (real) to a usable window: ~90 feature modules install, AI tool detection
  (shutil.which over PATH, ~25k stat calls), QtWebEngine.
* F7 settles slowly (~1.1 s offscreen, ~0.8 s real): VS Code extension context keys search every dock on each
  tab change (radide/vsx, not touched here).
* Zoom ~0.23 s: QScrollArea.takeWidget re-parents the 400 preview widgets into the zoom host.
* Opening a 400-control form ~1.5 s, paste / delete of 50 ~160-230 ms: each preview is a real Qt widget (~4 ms).
* Monaco: open 0.7 s, scroll ~54 ms / frame offscreen (software rendering, no vsync); unchanged.
* Four application-wide Python event filters cost ~2 us each per Qt event (merging them needs a change in four modules).
* The VS Code extension host (node.exe) keeps running when the IDE process dies (many orphans on this machine).
* Each opened VB6 .vbp project took 2-5 s in the harness (1.1 s alone; 0.65 s of that is a one-time import of the
  project-actions providers).

## الخلاصة بالعربي

قسنا مصمم الفورمات الكلاسيكي بأداة جديدة (perf_designer.py): وقت كل عملية، وأطول تجميد للواجهة، وتقارير cProfile.
الأسباب الرئيسية للبطء كانت:

* لوحة Document Outline كانت ترسم أيقونة لكل كنترول من جديد في كل إعادة بناء، وتتبني مرتين مع كل Undo، حتى وهي مخفية ورا تبويب.
* معرض المقاسات (Sizes) كان بيرسم الفورم كلها بعد كل تعديل وهو مخفي.
* المصمم كان بيعيد إنشاء الـ 400 كنترول مع كل لصق أو حذف أو Undo.
* نافذة الخصائص كانت تبني كل صفوفها من الصفر مع كل ضغطة.
* البحث في قائمة الكنترولات كان يمر على كل الكنترولات في كل خطوة سحب.
* توليد الكود كان يبني آلاف التعبيرات النمطية (regex) من جديد.
* أوامر git كانت بتشتغل على خيط الواجهة كل 5 ثوانٍ.
* ملف تنسيق الثيم كان بيتطبق بعد ما كل الواجهة اتبنت، وبيتعاد مرة تانية.

بعد الإصلاح على فورم فيها 400 كنترول:

* التراجع (Undo) من 5.3 ثانية إلى 72 مللي ثانية.
* إضافة كنترول من 4.6 ثانية إلى 58 مللي ثانية.
* لصق 50 كنترول من 5.7 ثانية إلى 0.23 ثانية.
* التنقل بين تبويبات الفورمات من 3 ثوانٍ إلى 0.2 ثانية.
* اختيار كنترول بالضغط من 200 إلى 10 مللي ثانية.
* السحب من 33 إلى 9 مللي ثانية لكل حركة.
* تشغيل البيئة لحد ما تبقى جاهزة من 9.3 إلى 4.8 ثانية.

كل الاختبارات المطلوبة نجحت، ما عدا فحص واحد في الترجمة كان فاشلاً قبل التعديلات بنفس الشكل.
