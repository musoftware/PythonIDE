# الدرس 2: الأحداث والكود: من الشاشة إلى برنامج يعمل

**في هذا الدرس ستتعرف على:**

- الأحداث: Click و Change و KeyPress و Load.
- مناطق كود المستخدم التي لا تُمحى عند إعادة توليد البرنامج.
- دوال وقت التشغيل لتغيير النصوص والقيم والشاشات.
- البناء والتشغيل في DOSBox-X.

## انقر نقرًا مزدوجًا

انقر نقرًا مزدوجًا على زر **OK** في المصمم: تحفظ RAD IDE الشاشة، وتولّد البرنامج من جديد، وتفتح محرر الكود عند معالج الحدث. في مشروع QBasic يبدو هكذا:

```qb
SUB Button1Click
' >>> USER CODE Button1_Click (kept when the screens are regenerated)
  TuiSetText Label1, "You pressed OK!"
' <<< END USER CODE
END SUB
```

لاحظ أن الاسم `Button1Click` بلا شرطة سفلية: QBasic لا يقبل الشرطة السفلية في الأسماء. أما في باسكال و C والتجميع فالاسم `Button1_Click`.

## مناطق كود المستخدم

كل ما بين السطرين `>>> USER CODE` و `<<< END USER CODE` ملكك. حين تغيّر الشاشة وتحفظها يُكتب باقي الملف من جديد، وتُعاد مناطقك كما هي. وإن حذفت زرًا كان له كود، يبقى الكود في منطقة **orphaned** معلَّقًا (داخل تعليق) حتى لا يضيع.

وهناك مناطق عامة أيضًا: **declarations** للمتغيرات العامة، و **startup** لكود يعمل قبل ظهور الشاشة الأولى، و **general** لدوالك الخاصة.

## الأحداث

| الأداة | الأحداث |
|---|---|
| Button | Click و KeyPress |
| TextBox | Change (عند كل حرف) و KeyPress |
| CheckBox و Option | Click و KeyPress |
| ListBox | Click (Enter أو نقرة) و Change (تغيّر التحديد) و KeyPress |
| عنصر قائمة | Click |
| الشاشة | Load (عند ظهورها) و KeyPress |

في حدث KeyPress يكون رمز المفتاح في المتغير `TuiKey` (أو `tui_key` في C والتجميع)، واجعله صفرًا لإلغاء المفتاح، مثلًا لمنع الحروف في مربع للأرقام فقط.

## دوال وقت التشغيل

| العمل | QBasic | باسكال | C |
|---|---|---|---|
| تغيير النص | `TuiSetText id, s$` | `TuiSetText(id, s)` | `tui_set_text(id, s)` |
| قراءة النص | `TuiGetText$(id)` | `TuiGetText(id)` | `tui_get_text(id)` |
| القيمة (مربع اختيار، خيار، قائمة، تقدم) | `TuiSetValue` و `TuiGetValue` | مثلها | `tui_set_value` و `tui_get_value` |
| إضافة عنصر لقائمة | `TuiAddItem id, s$` | `TuiAddItem(id, s)` | `tui_add_item(id, s)` |
| رسالة | `TuiMsgBox "Title", "Text"` | `TuiMsgBox('Title', 'Text')` | `tui_msgbox("Title", "Text")` |
| شاشة أخرى | `TuiShowScreen About` | `TuiShowScreen(About)` | `tui_show_screen(About)` |
| إنهاء البرنامج | `TuiQuit` | `TuiQuit` | `tui_quit()` |

وفي التجميع تمرَّر القيم في المسجلات: مثلًا `mov bx, Label1` ثم `mov si, offset msg` ثم `call tui_set_text`.

## مثال: إضافة اسم إلى القائمة

```qb
SUB btnAddClick
' >>> USER CODE btnAdd_Click (kept when the screens are regenerated)
  n$ = TuiGetText$(txtName)
  IF LEN(n$) = 0 THEN TuiMsgBox "Contacts", "Type a name first.": EXIT SUB
  TuiAddItem lstContacts, n$
  TuiSetText txtName, ""
  TuiSetText lblInfo, "Added: " + n$
' <<< END USER CODE
END SUB
```

المشروع الكامل في المجلد `samples/Tests/Retro/DesignTUI_Contacts`: شاشتان وشاشة افتتاحية وقوائم.

## البناء والتشغيل

اضغط **F5** أو **Build && Run in DOSBox-X** في شريط المصمم. يُبنى البرنامج بالمترجم المجاني، ثم يعمل في نافذة DOSBox-X: لوحة المفاتيح والفأرة تعملان، و **Tab** ينقل التركيز، و **F10** أو **Alt** مع حرف يفتح القوائم، و **Esc** يضغط زر الإلغاء أو ينهي البرنامج.

```quiz
{"question": "ماذا يحدث لكودك داخل منطقة USER CODE عندما تحرّك زرًا وتحفظ الشاشة؟", "choices": ["يُمحى", "يبقى كما هو", "يُنقل إلى ملف آخر"], "answer": 1, "explanation": "يُعاد توليد باقي الملف، وتُعاد مناطق كود المستخدم كما كتبتها."}
```
