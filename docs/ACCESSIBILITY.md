# Accessibility

RAD IDE can be used with the keyboard only and with a screen reader (Narrator, NVDA, JAWS), follows the Windows
contrast themes, and the programs it builds expose their controls to UI Automation. The implementation lives in
`radide/features/perf_a11y.py` (naming, keyboard, focus ring, contrast themes), `radide/designer.py` (designer
surface), `radide/properties.py` (Properties grid), `radide/toolbox.py` (Toolbox keys), the native runtime
`radide/runtimes/native/radforms/radforms.c` and the .NET library `radide/runtimes/dotnet/RadIDE.Controls`.
The tests are in `samples/Tests/Accessibility`.

## Keyboard map

### Anywhere in the IDE

| Keys | Action |
|---|---|
| Alt | Select the menu bar (arrow keys move, Enter opens, Esc leaves) |
| Alt + underlined letter | Open that menu (each top-level menu has its own letter) |
| F6 / Shift+F6 | Next / previous window: the editor area, then every visible tool window, then the Auto Hide windows (they slide out and get the focus) |
| Ctrl+F6 | Back to the editor area |
| Ctrl+Tab / Ctrl+Shift+Tab | Next / previous tab of the tab group that has the focus (the documents when the focus is in an editor, also in the code editor) |
| Esc | Close a slid-out Auto Hide window (the focus returns), close a dialog |
| Menu key or Shift+F10 | Context menu of the focused item |
| Ctrl+Shift+Alt+D | Open the current HTML / PHP page in Split view (Design view is Ctrl+Shift+D) |

The commands of the main tool bars are all in the menus or have a shortcut; the tool bars inside tool windows
(Databases, Data Sources, Git Changes ...) are reached with Tab.

### Toolbox

| Keys | Action |
|---|---|
| Up / Down | Move between controls and group headers |
| Enter on a control | Add it to the form shown in the designer (like a double-click) |
| Enter / Space on a group header | Open / close the group; Left closes, Right opens |
| Tab / Shift+Tab | To the search box ("Search Toolbox") and back |

### Form designer

| Keys | Action |
|---|---|
| Tab / Shift+Tab | Select the next / previous control (the component tray follows) |
| Arrow keys | Move the selected controls by 1 pixel |
| Ctrl+arrow | Move to the next grid line or the next edge of another control |
| Shift+arrow / Ctrl+Shift+arrow | Resize (by 1 pixel / to the grid or an edge) |
| Delete | Remove the selection |
| Esc | Select the container of the control, then the form; cancels a drag |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| F7 / Shift+F7 | Code / designer |

A screen reader announces the selection: the designer surface is named "*Button1 (Button) - Form1 designer*"
("*3 controls selected, ...*" for several) and its description gives Left / Top / Width / Height and these keys.

### Properties window

| Keys | Action |
|---|---|
| Tab / Shift+Tab | Object list, Categorized / A-Z, the grid, ... - the grid is **one** Tab stop (no focus trap) |
| Up / Down | Move between properties; a screen reader reads "*Text: Button1*" and the help text |
| Enter or F2 | Edit the value (text) or move into its editor (True/False list, colour, file, anchor ...) |
| Up / Down / Alt+Down in a list editor | Change the value / open the list |
| Esc in an editor | Back to the property row |
| Ctrl+Tab | Properties / Events tabs |
| Enter on an event | Write the handler and show the code (like a double-click) |

### Dialogs

Tab / Shift+Tab go round every field and never get stuck, Enter is the default button, Esc closes, and each field
label has an Alt access key (labels without one get a free letter when the dialog opens; a field made of an edit
and a "..." button takes the focus in its edit).

A focus ring in the theme's highlight colour is drawn around check boxes, radio buttons, combo boxes, sliders and
tool buttons while the keyboard moves the focus (the Fusion style draws none for them).

## Screen readers

* Every tool window, tool bar, editor and field has an accessible name: tool windows by their title (description:
  "F6 / Shift+F6 move between windows"), icon-only buttons by their command, fields by their label, placeholder or
  tool tip, tool bars as "*<title> toolbar*", the document tabs, the Properties grid and its value editors (named
  after their property), the Auto Hide tabs ("*Toolbox (auto-hidden window)*"), the controls of the designed form
  (name + "*Button control ... on the designed form*").
* Toolbox group headers are read as "*Common Controls (expanded)*" instead of the arrow character.
* In the Arabic UI the names are Arabic (switched live with the language; control and property names stay as
  they are).
* Tools > Accessibility Check lists the contrast of the current theme and any focusable widget without a name.

## Contrast themes and text size

* All built-in themes meet WCAG 2.1 AA (4.5:1 text, 3:1 disabled text / selection / focus ring); the High
  Contrast theme meets AAA (7:1). The test computes the pairs the style sheet really paints (dock titles on both
  gradient colours, tool bars, tabs incl. hover, menus, status bar, headers, tool tips, banners, links, errors).
* When a Windows contrast theme is on (Settings > Accessibility > Contrast themes: Aquatic, Desert, Dusk, Night
  sky or your own), RAD IDE builds the theme **Windows Contrast** from the Windows system colours and uses it. Turn
  this off with the setting `accessibility/follow_high_contrast = false`; pick another theme in Tools > Options.
* With twice the normal text size the main dialogs (New Project, Options, Publish, Extensions, Add Form,
  Accessibility Check) clip no text and fit a 1280 x 720 screen.

## Programs built by RAD IDE

**Native exes (radforms, C / C++ / Fortran / Rust / Go / Lua ...)** use real Windows controls, so Windows reports
their names and roles itself. On top of that:

* the tab order follows TabIndex; Space / Enter press the focused button, Space toggles check boxes and toggles;
* a Label's "&Name:" is an access key (UseMnemonic, as in VB / WinForms): Alt+N moves to the next field;
  "&&" shows "&"; `UseMnemonic = False` turns it off;
* `AccessibleName` / `AccessibleDescription` can be set on any control (in the .form or in code:
  `rad_set("lstItems", "AccessibleName", "Items list")`);
* the RAD Modern controls (Rm\*) report a name (Text, the watermark of a text box, else the control name), a role
  (button, check box with its checked state, slider and progress bar with their value, combo box, table, outline,
  tool bar, status bar, page tabs ...) through Dynamic Annotation (IAccPropServices) - no extra DLL.

**.NET builds (RadIDE.Controls)**: each Rm control has an accessible object with role, name and value (slider,
progress, gauge, date picker, calendar, text box), checked state, and its items (ribbon, side bar, tabs, status
bar) as accessible children that UI Automation can invoke. A text box is named by AccessibleName, its watermark or
its Name - never by the text typed into it - and its inner edit, which has the focus, carries the same name.

## Known limits

* PyQt6 does not wrap QAccessible, so the offscreen tests apply Qt's naming rules to the widgets; the real UI
  Automation tree is checked by a child process on the Windows platform plugin (`test_screen_reader.py`, part 5).
* Menu items: 89 items have no access key and 12 menus repeat a key (the letter then cycles; Enter runs it); the
  top-level menus all have unique keys.
* The main tool bars are not Tab stops (as in Visual Studio); their commands are in the menus or on shortcuts.
* The Monaco code editor and other web views (Design View, help) use Chromium's own accessibility; their contents
  are not checked by these tests.
* Native exes: the Rm controls' items (ribbon buttons, grid cells, tree nodes) are not separate accessible objects
  yet (the .NET library has them); a toggle's checked state is updated when the program changes it.
* The designer has no AccessibleName property in the Properties window yet; set it in code or in the .form file.

## Tests

```
.venv\Scripts\python samples\Tests\Accessibility\test_keyboard_ide.py
.venv\Scripts\python samples\Tests\Accessibility\test_screen_reader.py
.venv\Scripts\python samples\Tests\Accessibility\test_contrast_scaling.py
.venv\Scripts\python samples\Tests\Accessibility\test_native_a11y.py
```

Each prints PASS / FAIL lines and a summary; the exit code is the number of failures. They run offscreen with
their own settings (QSettings organisation `RADIDE-TEST-A11Y`, cleared before and after) and only touch the
processes they start.

---

## ملخص بالعربية: إمكانية الوصول

يمكن استخدام RAD IDE بلوحة المفاتيح وحدها ومع قارئات الشاشة (الراوي، NVDA، JAWS)، ويتبع سمات التباين في ويندوز، والبرامج
التي يبنيها تعرض عناصرها لأتمتة واجهة المستخدم (UI Automation).

**لوحة المفاتيح:**

* ‏Alt لشريط القوائم، و‏Alt + الحرف المسطر لفتح قائمة (لكل قائمة رئيسية حرف خاص بها).
* ‏F6 / ‏Shift+F6 للتنقل بين المحرر ونوافذ الأدوات الظاهرة ثم النوافذ المخفية تلقائيًا (تنزلق وتأخذ التركيز)، و‏Ctrl+F6 للعودة إلى المحرر.
* ‏Ctrl+Tab / ‏Ctrl+Shift+Tab للتبديل بين الألسنة (المستندات حتى من محرر الكود).
* صندوق الأدوات: الأسهم للتنقل، ‏Enter يضيف العنصر إلى النموذج، ‏Enter أو المسافة على عنوان مجموعة تفتحها أو تغلقها.
* المصمم: ‏Tab للعنصر التالي، الأسهم للتحريك، ‏Shift+الأسهم لتغيير الحجم، ‏Ctrl+الأسهم للمحاذاة، ‏Delete للحذف، ‏Esc للحاوية.
* نافذة الخصائص: الشبكة محطة ‏Tab واحدة (بلا فخ تركيز)، الأسهم بين الخصائص، ‏Enter أو ‏F2 للتحرير، ‏Esc للعودة، و‏Enter على حدث يكتب معالجه.
* مربعات الحوار: ‏Tab يدور على كل الحقول، ‏Enter للزر الافتراضي، ‏Esc للإغلاق، ولكل حقل مفتاح وصول ‏Alt.
* حلقة تركيز ظاهرة بلون التمييز حول مربعات الاختيار والقوائم المنسدلة والمنزلقات عند التنقل بلوحة المفاتيح.

**قارئات الشاشة:** لكل نافذة وشريط أدوات وحقل اسم مقروء، والمصمم يعلن العنصر المحدد ونوعه وموضعه، وشبكة الخصائص تُقرأ
"الخاصية: القيمة"، والأسماء بالعربية في الواجهة العربية.

**التباين وحجم النص:** كل السمات تحقق WCAG 2.1 AA وسمة التباين العالي تحقق AAA، وعند تشغيل سمة تباين في ويندوز يستخدم
البرنامج سمة "تباين ويندوز" المبنية من ألوان النظام. مع مضاعفة حجم النص لا يُقص أي نص في مربعات الحوار الرئيسية.

**البرامج المبنية:** البرامج الأصلية (radforms) تتبع ترتيب TabIndex، والمسافة و‏Enter تضغط الزر، و"&الاسم:" في التسمية
مفتاح وصول، ويمكن ضبط AccessibleName و‏AccessibleDescription، وعناصر Rm تعلن اسمها ودورها وقيمتها. وفي ‏.NET لكل عنصر Rm
كائن وصول بالدور والاسم والقيمة.

**حدود معروفة:** بعض عناصر القوائم الفرعية بلا مفتاح وصول، وأشرطة الأدوات الرئيسية ليست محطات ‏Tab (أوامرها في القوائم)،
ومحتوى محرر Monaco يعتمد على إمكانية الوصول في Chromium، وعناصر Rm الداخلية (أزرار الشريط، خلايا الجدول) في البرامج
الأصلية ليست كائنات وصول منفصلة بعد.
