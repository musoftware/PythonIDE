# الدرس 11: أول نافذة RingQt في مصمم النماذج

**في هذا الدرس ستتعلم:**

- ما هي **RingQt** وكيف تصنع بها برامج بنوافذ.
- إنشاء مشروع **Windows Application** بلغة Ring في RAD IDE.
- وضع **الأدوات** (عناصر التحكم) على النموذج وضبط خصائصها.
- كتابة **حدث** الضغط على الزر `Click` والتعامل مع النصوص في النافذة.

## ما هي RingQt؟

**RingQt** مكتبة تأتي مع Ring، تربطها بإطار العمل الشهير **Qt** المستخدم في برامج كثيرة حول العالم. بها تصنع نوافذ وأزرارًا ومربعات نص وقوائم.

وفي RAD IDE لا تحتاج إلى كتابة كود إنشاء النافذة بنفسك: **مصمم النماذج** (Form Designer) يسمح لك برسم النافذة بالفأرة كما في Visual Basic، ثم يكتب الـ IDE كود RingQt بدلًا منك في ملف `Form1_designer.ring`. أنت تكتب فقط **ماذا يحدث** عند الضغط على زر وغيره، في الملف `Form1.ring`.

> **تشبيه:** المصمم مثل مهندس الديكور الذي يرتب الأثاث في الغرفة، وأنت تكتب «قواعد البيت»: ماذا يحدث عندما يُفتح الباب أو يُضغط زر النور.

## الخطوة 1: إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد) أو `Ctrl+Shift+N`.
2. من مجموعة **Ring** اختر **Ring (RingQt)**.
3. اختر القالب **Windows Application** (تطبيق Windows).
4. سمِّ المشروع `HelloForm` واضغط **OK** (موافق).

يفتح المصمم وفيه نموذج فارغ اسمه `Form1`. وفي **Solution Explorer** (مستكشف الحلول) ترى:

| الملف | ما فيه |
|---|---|
| `Form1.form` | شكل النافذة وأدواتها وخصائصها (يحفظه المصمم) |
| `Form1_designer.ring` | كود RingQt الذي يولّده الـ IDE من التصميم. **لا تعدّله بيدك**، فهو يُكتب من جديد عند كل حفظ |
| `Form1.ring` | كودك أنت: الأحداث والدوال |

## الخطوة 2: تصميم النافذة

من **Toolbox** (صندوق الأدوات) اسحب إلى النموذج:

1. أداة **Label**، وفي نافذة **Properties** (الخصائص) اجعل `Name` = `lblPrompt` و`Text` = `اكتب اسمك:`.
2. أداة **TextBox**، واجعل `Name` = `txtName` وامسح `Text`.
3. أداة **Button**، واجعل `Name` = `btnHello` و`Text` = `قل مرحبًا`.
4. أداة **Label** ثانية، واجعل `Name` = `lblResult` وامسح `Text`.
5. اضغط على النموذج نفسه، واجعل خاصيته `Text` = `التحية` (هذا عنوان النافذة).

> **عادة جيدة:** ابدأ اسم كل أداة بثلاثة أحرف تدل على نوعها: `btn` للزر، و`txt` لمربع النص، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار. هكذا تعرف نوع الأداة من اسمها في الكود.

## الخطوة 3: كتابة الحدث

**الحدث** (event) شيء يقع للأداة: ضغطة زر، أو تغيير نص، أو تحميل نافذة. نكتب لكل حدث دالة اسمها: **اسم الأداة + `_` + اسم الحدث**.

اضغط **مرتين** على الزر `btnHello` في المصمم. سيفتح الـ IDE الملف `Form1.ring` ويضيف الدالة `btnHello_Click`. اكتب فيها:

<!-- test: {"form": {"Text": "التحية", "controls": {"lblPrompt": {"Type": "Label", "Text": "اكتب اسمك:"}, "txtName": {}, "btnHello": {"Text": "قل مرحبًا"}, "lblResult": {}}}, "do": ["txtName.setText('سارة')", "btnHello_Click()"], "expect": {"lblResult.text()": "أهلًا يا سارة، مرحبًا بك في RingQt!"}} -->
```ring form run
load "Form1_designer.ring"

# Show this form with:  Form1_Show()

# ---------------- Event handlers ----------------

func Form1_Load
    # runs after the form is created
    lblResult.setText("")

func btnHello_Click
    cName = txtName.text()
    lblResult.setText("أهلًا يا " + cName + "، مرحبًا بك في RingQt!")
```

اضغط `F5` (**Debug > Start Debugging / Continue**) أو `Ctrl+F5`. تظهر النافذة؛ اكتب اسمك واضغط الزر.

### ماذا كتبنا؟

- `load "Form1_designer.ring"` يحمّل الكود الذي ولّده المصمم (يكتبه الـ IDE تلقائيًا في أول الملف).
- `Form1_Load` حدث **تحميل النموذج**: يُنفذ مرة واحدة بعد إنشاء النافذة وقبل ظهورها.
- كل أداة متغير باسمها: `txtName` هو مربع النص، و`lblResult` هو العنوان.
- `txtName.text()` تقرأ النص المكتوب في المربع.
- `lblResult.setText("...")` تغيّر النص الظاهر في العنوان.

> **ملحوظة:** في RingQt نقرأ الخاصية بدالة (`text()`) ونغيّرها بدالة تبدأ بـ `set` (`setText()`). هذا أسلوب Qt في كل الأدوات.

## كيف تعمل الأمور من الداخل؟

افتح `Form1_designer.ring` (كليك يمين على النموذج في **Solution Explorer** ثم **View Generated Code**). ستجد شيئًا مثل:

```ring
func Form1_Create
    Form1 = new qWidget()
    Form1.setWindowTitle("التحية")
    ...
    btnHello = new qPushButton(Form1)
    btnHello.setText("قل مرحبًا")
    btnHello.setClickEvent("btnHello_Click()")
```

السطر الأخير هو «الربط»: يقول لـ Qt إنه عند الضغط على الزر نفّذ الدالة `btnHello_Click()`. المصمم يكتب هذا السطر تلقائيًا عندما يجد في كودك دالة بهذا الاسم. وعند التشغيل ينشئ الـ IDE برنامجًا صغيرًا يكتب `oApp = new qApp` ثم `Form1_Show()` ثم `oApp.exec()` الذي يبقي النافذة مفتوحة وينتظر الأحداث.

## مثال 2: حاسبة بسيطة

صمّم نافذة فيها: `txtA` و`txtB` (مربعا نص)، وزر `btnAdd` (`Text` = `+`)، وزر `btnMul` (`Text` = `×`)، وعنوان `lblResult`.

<!-- test: {"form": {"Text": "حاسبة", "controls": {"btnAdd": {"Text": "+"}, "btnMul": {"Text": "×"}}}, "do": ["txtA.setText('6')", "txtB.setText('7')", "btnAdd_Click()", "cSum = lblResult.text()", "btnMul_Click()"], "expect": {"cSum": "الناتج = 13", "lblResult.text()": "الناتج = 42"}} -->
```ring form run
load "Form1_designer.ring"

func btnAdd_Click
    nA = number(txtA.text())
    nB = number(txtB.text())
    lblResult.setText("الناتج = " + (nA + nB))

func btnMul_Click
    nA = number(txtA.text())
    nB = number(txtB.text())
    lblResult.setText("الناتج = " + (nA * nB))
```

تذكّر من الدرس 2: ما في مربع النص **نص** دائمًا، فنحوّله بـ `number()` قبل الحساب.

## مثال 3: تغيير الألوان والخط

كل أداة في RingQt تقبل `setStyleSheet` بصيغة تشبه CSS المستخدمة في صفحات الويب:

<!-- test: {"form": {"Text": "الألوان", "controls": {"btnRed": {"Text": "أحمر"}, "btnGreen": {"Text": "أخضر"}}}, "do": ["btnGreen_Click()"], "expect": {"lblMessage.text()": "اللون الآن: أخضر"}} -->
```ring form run
load "Form1_designer.ring"

func Form1_Load
    lblMessage.setText("اختر لونًا")

func btnRed_Click
    lblMessage.setStyleSheet("color: white; background-color: #C62828; font-size: 16pt;")
    lblMessage.setText("اللون الآن: أحمر")

func btnGreen_Click
    lblMessage.setStyleSheet("color: white; background-color: #2E7D32; font-size: 16pt;")
    lblMessage.setText("اللون الآن: أخضر")
```

ويمكنك أيضًا ضبط الألوان والخط من نافذة **Properties** مباشرة (`BackColor` و`ForeColor` و`FontSize` و`FontBold`)، والمصمم يحوّلها إلى `setStyleSheet` في الكود المولَّد.

## أخطاء شائعة

- **اسم الدالة لا يطابق اسم الأداة:** إذا غيّرت اسم الزر إلى `btnGo` فالدالة يجب أن تكون `btnGo_Click`، وإلا لن يحدث شيء عند الضغط.
- **تعديل `Form1_designer.ring` بيدك:** يضيع تعديلك عند الحفظ التالي. عدّل التصميم من المصمم، والكود في `Form1.ring`.
- **نسيان `number()`:** `txtA.text() + txtB.text()` تلصق النصين (`"6" + "7"` = `"67"`).
- **كتابة `txtName.text` بلا أقواس:** في RingQt `text()` دالة، فلا بد من الأقواس.

## تمارين

### التمرين 1: محوّل العملة

نافذة فيها `txtPounds` (المبلغ بالجنيه)، وزر `btnConvert`، وعنوان `lblDollars`. عند الضغط اقسم المبلغ على 50 واعرض: `المبلغ بالدولار: 10` (للمبلغ 500).

<!-- test: {"form": {"Text": "محوّل العملة", "controls": {"btnConvert": {"Text": "حوّل"}}}, "do": ["txtPounds.setText('500')", "btnConvert_Click()"], "expect": {"lblDollars.text()": "المبلغ بالدولار: 10"}} -->
```ring form exercise
load "Form1_designer.ring"

func btnConvert_Click
    # اقرأ txtPounds، واقسم على 50، واكتب الناتج في lblDollars
```

<!-- test: {"form": {"Text": "محوّل العملة", "controls": {"btnConvert": {"Text": "حوّل"}}}, "do": ["txtPounds.setText('500')", "btnConvert_Click()"], "expect": {"lblDollars.text()": "المبلغ بالدولار: 10"}} -->
```ring form solution
load "Form1_designer.ring"

func btnConvert_Click
    nPounds = number(txtPounds.text())
    lblDollars.setText("المبلغ بالدولار: " + (nPounds / 50))
```

### التمرين 2: عدّاد الضغطات

نافذة فيها زر `btnClick` وعنوان `lblCount`. كل ضغطة تزيد العدد وتعرض: `عدد الضغطات: 3`.

<!-- test: {"form": {"Text": "العدّاد", "controls": {"btnClick": {"Text": "اضغطني"}}}, "do": ["btnClick_Click()", "btnClick_Click()", "btnClick_Click()"], "expect": {"lblCount.text()": "عدد الضغطات: 3"}} -->
```ring form exercise
load "Form1_designer.ring"

nClicks = 0      # متغير عام يحفظ العدد بين الضغطات

func btnClick_Click
    # أكمل
```

<!-- test: {"form": {"Text": "العدّاد", "controls": {"btnClick": {"Text": "اضغطني"}}}, "do": ["btnClick_Click()", "btnClick_Click()", "btnClick_Click()"], "expect": {"lblCount.text()": "عدد الضغطات: 3"}} -->
```ring form solution
load "Form1_designer.ring"

nClicks = 0      # متغير عام يحفظ العدد بين الضغطات

func btnClick_Click
    nClicks++
    lblCount.setText("عدد الضغطات: " + nClicks)
```

## اختبر نفسك

```quiz
{"question": "في أي ملف تكتب كود الأحداث في مشروع RingQt؟", "choices": ["Form1_designer.ring", "Form1.ring", "Form1.form", "project.radproj"], "answer": 1, "explanation": "Form1.ring لكودك، وForm1_designer.ring يولّده الـ IDE من التصميم."}
```

```quiz
{"question": "ما اسم دالة حدث الضغط على زر اسمه btnSave؟", "choices": ["Click_btnSave", "btnSave_Click", "btnSave.Click", "onClick"], "answer": 1, "explanation": "اسم الأداة ثم _ ثم اسم الحدث."}
```

```quiz
{"question": "كيف تقرأ النص المكتوب في مربع النص txtName؟", "choices": ["`txtName.Text`", "`txtName.text()`", "`text(txtName)`", "`txtName.getText`"], "answer": 1, "explanation": "في RingQt نقرأ بدالة text() ونغيّر بدالة setText()."}
```

## الخلاصة

- **File > New Project... > Ring > Ring (RingQt) > Windows Application**.
- صمّم بالسحب من **Toolbox** واضبط `Name` و`Text` من **Properties**.
- اضغط مرتين على الأداة لإنشاء حدثها، واكتب الكود في `Form1.ring`.
- `text()` للقراءة و`setText()` للكتابة، و`number()` قبل الحساب.
