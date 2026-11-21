# الدرس 12: أدوات أكثر: القوائم والاختيارات والمؤقت

**في هذا الدرس ستتعلم:**

- أداة القائمة **ListBox** (في RingQt: `qListWidget`): الإضافة والحذف ومعرفة العنصر المختار.
- القائمة المنسدلة **ComboBox** ومربع الاختيار **CheckBox** وزر الخيار **RadioButton**.
- **المؤقت** Timer وحدث `Tick`، وشريط التقدم **ProgressBar**.
- بناء برنامج «قائمة المهام» كاملًا.

## جدول سريع بالأدوات

| الأداة في Toolbox | صنف RingQt | أهم الدوال |
|---|---|---|
| ListBox | `qListWidget` | `addItem(c)` و`count()` و`currentRow()` و`item(n).text()` و`takeItem(n)` و`clear()` |
| ComboBox | `qComboBox` | `addItem(c, 0)` و`currentText()` و`currentIndex()` و`setCurrentIndex(n)` |
| CheckBox | `qCheckBox` | `isChecked()` و`setChecked(true)` |
| RadioButton | `qRadioButton` | `isChecked()` و`setChecked(true)` |
| ProgressBar | `qProgressBar` | `setValue(n)` و`value()` و`setRange(min, max)` |
| Timer | `qTimer` | `start()` و`stop()` و`setInterval(ms)` |

> **مهم:** ترقيم العناصر في أدوات Qt يبدأ من **0** وليس من 1 كما في قوائم Ring. فالعنصر الأول في `qListWidget` هو `item(0)`، و`currentRow()` تُرجع `-1` إذا لم يُختر شيء.

## قائمة المهام: الخطوة الأولى

أنشئ مشروعًا جديدًا (**File > New Project... > Ring > Ring (RingQt) > Windows Application**)، وصمّم:

| الأداة | `Name` | `Text` |
|---|---|---|
| TextBox | `txtTask` | (فارغ) |
| Button | `btnAdd` | `أضف` |
| Button | `btnRemove` | `احذف المختار` |
| ListBox | `lstTasks` | |
| Label | `lblCount` | (فارغ) |

ثم اضغط مرتين على كل زر واكتب:

<!-- test: {"form": {"Text": "قائمة المهام", "controls": {"btnAdd": {"Text": "أضف"}, "btnRemove": {"Text": "احذف المختار"}}}, "do": ["txtTask.setText('ذاكر Ring')", "btnAdd_Click()", "txtTask.setText('')", "btnAdd_Click()", "txtTask.setText('مارس الرياضة')", "btnAdd_Click()", "txtTask.setText('اقرأ كتابًا')", "btnAdd_Click()", "lstTasks.setCurrentRow(1, 3)", "btnRemove_Click()"], "expect": {"lstTasks.count()": "2", "lstTasks.item(1).text()": "اقرأ كتابًا", "lblCount.text()": "عدد المهام: 2", "txtTask.text()": ""}} -->
```ring form run
load "Form1_designer.ring"

func Form1_Load
    updateCount()

func btnAdd_Click
    cTask = trim(txtTask.text())
    if cTask = ""
        return              # لا نضيف مهمة فارغة
    ok
    lstTasks.addItem(cTask)
    txtTask.clear()          # امسح المربع استعدادًا لمهمة جديدة
    updateCount()

func btnRemove_Click
    nRow = lstTasks.currentRow()
    if nRow < 0
        return              # لم يختر المستخدم شيئًا
    ok
    lstTasks.takeItem(nRow)
    updateCount()

func updateCount
    lblCount.setText("عدد المهام: " + lstTasks.count())
```

لاحظ الدالة `updateCount`: دالة عادية (ليست حدثًا) نستدعيها من أكثر من مكان بدل تكرار نفس السطر.

## حدث اختيار عنصر من القائمة

عندما يختار المستخدم عنصرًا يقع الحدث `SelectedIndexChanged`. لإنشائه اختر الأداة في المصمم، ثم في نافذة **Properties** (الخصائص) افتح تبويب **Events** (الأحداث) واضغط مرتين على `SelectedIndexChanged` (أو كليك يمين على الأداة في المصمم ثم **Events**):

<!-- test: {"form": {"Text": "الفواكه", "controls": {"lstFruits": {"Items": "تفاح;موز;مانجو"}}}, "do": ["lstFruits.setCurrentRow(2, 3)"], "expect": {"lblChoice.text()": "اخترت: مانجو (العنصر رقم 2)"}} -->
```ring form run
load "Form1_designer.ring"

func lstFruits_SelectedIndexChanged
    nRow = lstFruits.currentRow()
    if nRow >= 0
        lblChoice.setText("اخترت: " + lstFruits.item(nRow).text() + " (العنصر رقم " + nRow + ")")
    ok
```

هنا ملأنا القائمة من المصمم: خاصية `Items` في **Properties**، والعناصر مفصولة بفاصلة منقوطة `;` مثل `تفاح;موز;مانجو`.

## القائمة المنسدلة ومربع الاختيار وأزرار الخيار

نافذة طلب بيتزا: `cboSize` (ComboBox، خاصية `Items` = `صغيرة;وسط;كبيرة`)، و`chkCheese` (CheckBox، `Text` = `جبنة إضافية`)، و`optDelivery` و`optPickup` (RadioButton)، وزر `btnOrder`، وعنوان `lblTotal`:

<!-- test: {"form": {"Text": "طلب بيتزا", "controls": {"cboSize": {"Items": "صغيرة;وسط;كبيرة"}, "chkCheese": {"Text": "جبنة إضافية"}, "optDelivery": {"Text": "توصيل للمنزل"}, "optPickup": {"Text": "استلام من المطعم"}, "btnOrder": {"Text": "احسب"}}}, "do": ["cboSize.setCurrentIndex(2)", "chkCheese.setChecked(true)", "optDelivery.setChecked(true)", "btnOrder_Click()"], "expect": {"lblTotal.text()": "بيتزا كبيرة: 165 جنيهًا"}} -->
```ring form run
load "Form1_designer.ring"

func Form1_Load
    optPickup.setChecked(true)

func btnOrder_Click
    aPrices = [80, 110, 140]                    # قائمة Ring: تبدأ من 1
    nPrice = aPrices[cboSize.currentIndex() + 1] # ComboBox: يبدأ من 0
    if chkCheese.isChecked()
        nPrice += 15
    ok
    if optDelivery.isChecked()
        nPrice += 10
    ok
    lblTotal.setText("بيتزا " + cboSize.currentText() + ": " + nPrice + " جنيهًا")
```

لاحظ `currentIndex() + 1`: حوّلنا ترقيم Qt (يبدأ من 0) إلى ترقيم قائمة Ring (يبدأ من 1).

أزرار الخيار (RadioButton) الموجودة في نفس الحاوية تعمل كمجموعة: اختيار واحد منها يلغي اختيار الباقي تلقائيًا. لعمل مجموعتين منفصلتين ضع كل مجموعة داخل **GroupBox**.

## المؤقت Timer

**المؤقت** أداة غير مرئية تطلق الحدث `Tick` كل فترة. اسحب **Timer** من Toolbox (يظهر أسفل المصمم لأنه لا يُرى في النافذة)، واجعل:

- `Name` = `tmrCount`، و`Interval` = `1000` (بالمللي ثانية، أي ثانية واحدة)، و`Enabled` = `False`.

ثم صمّم زرًا `btnStart` وعنوانًا `lblTime` وشريط تقدم `prgTime`:

<!-- test: {"form": {"Text": "العد التنازلي", "controls": {"btnStart": {"Text": "ابدأ"}, "tmrCount": {"Interval": 1000, "Enabled": false}}}, "do": ["btnStart_Click()", "tmrCount_Tick()", "tmrCount_Tick()", "tmrCount_Tick()"], "expect": {"lblTime.text()": "باقي 7 ثوانٍ", "prgTime.value()": "3"}} -->
```ring form run
load "Form1_designer.ring"

nSeconds = 10

func btnStart_Click
    nSeconds = 10
    prgTime.setRange(0, 10)
    prgTime.setValue(0)
    lblTime.setText("باقي 10 ثوانٍ")
    tmrCount.start()

func tmrCount_Tick
    nSeconds--
    prgTime.setValue(10 - nSeconds)
    if nSeconds <= 0
        tmrCount.stop()
        lblTime.setText("انتهى الوقت!")
    else
        lblTime.setText("باقي " + nSeconds + " ثوانٍ")
    ok
```

بعد ثلاث ثوانٍ تكون `prgTime.value()` مساوية `3` من مدى `0` إلى `10`، فيظهر الشريط ممتلئًا بنسبة 30%. الشريط يحسب النسبة بنفسه من `setRange` و`setValue`.

## أخطاء شائعة

- **الخلط بين ترقيم Ring وترقيم Qt:** قوائم Ring تبدأ من 1، وأدوات Qt تبدأ من 0.
- **نسيان فحص `currentRow() < 0`:** يحدث خطأ عند محاولة حذف عنصر لم يُختر.
- **مؤقت لا يعمل:** تأكد من `Enabled` = `True` أو استدعاء `start()`، ومن أن اسم الدالة `tmrCount_Tick` يطابق اسم المؤقت.
- **`addItem` في ComboBox:** في RingQt تأخذ معاملين: `addItem("نص", 0)`.

## تمارين

### التمرين 1: نقل بين قائمتين

نافذة فيها `lstLeft` (خاصية `Items` = `أحمد;منى;كريم`)، و`lstRight`، وزر `btnMove`. عند الضغط انقل العنصر المختار من اليسار إلى اليمين.

<!-- test: {"form": {"Text": "نقل", "controls": {"lstLeft": {"Items": "أحمد;منى;كريم"}, "btnMove": {"Text": ">>"}}}, "do": ["lstLeft.setCurrentRow(1, 3)", "btnMove_Click()"], "expect": {"lstLeft.count()": "2", "lstRight.count()": "1", "lstRight.item(0).text()": "منى"}} -->
```ring form exercise
load "Form1_designer.ring"

func btnMove_Click
    nRow = lstLeft.currentRow()
    # إذا كان هناك اختيار: أضف نصه إلى lstRight ثم احذفه من lstLeft
```

<!-- test: {"form": {"Text": "نقل", "controls": {"lstLeft": {"Items": "أحمد;منى;كريم"}, "btnMove": {"Text": ">>"}}}, "do": ["lstLeft.setCurrentRow(1, 3)", "btnMove_Click()"], "expect": {"lstLeft.count()": "2", "lstRight.count()": "1", "lstRight.item(0).text()": "منى"}} -->
```ring form solution
load "Form1_designer.ring"

func btnMove_Click
    nRow = lstLeft.currentRow()
    if nRow >= 0
        lstRight.addItem(lstLeft.item(nRow).text())
        lstLeft.takeItem(nRow)
    ok
```

### التمرين 2: الموافقة على الشروط

نافذة فيها `chkAgree` (CheckBox بنص `أوافق على الشروط`) وزر `btnNext`. اجعل الزر معطلًا في البداية، ويتفعل فقط عندما يختار المستخدم المربع (الحدث `CheckedChanged`).

<!-- test: {"form": {"Text": "الشروط", "controls": {"chkAgree": {"Text": "أوافق على الشروط"}, "btnNext": {"Text": "التالي"}}}, "do": ["cBefore = '' + btnNext.isEnabled()", "chkAgree.setChecked(true)"], "expect": {"cBefore": "0", "btnNext.isEnabled()": "1"}} -->
```ring form exercise
load "Form1_designer.ring"

func Form1_Load
    btnNext.setEnabled(false)

func chkAgree_CheckedChanged
    # فعّل الزر أو عطّله حسب chkAgree.isChecked()
```

<!-- test: {"form": {"Text": "الشروط", "controls": {"chkAgree": {"Text": "أوافق على الشروط"}, "btnNext": {"Text": "التالي"}}}, "do": ["cBefore = '' + btnNext.isEnabled()", "chkAgree.setChecked(true)"], "expect": {"cBefore": "0", "btnNext.isEnabled()": "1"}} -->
```ring form solution
load "Form1_designer.ring"

func Form1_Load
    btnNext.setEnabled(false)

func chkAgree_CheckedChanged
    btnNext.setEnabled(chkAgree.isChecked())
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع `lstTasks.currentRow()` إذا لم يختر المستخدم أي عنصر؟", "choices": ["0", "1", "-1", "NULL"], "answer": 2, "explanation": "أدوات Qt تبدأ من 0، و-1 تعني لا يوجد اختيار."}
```

```quiz
{"question": "ما الحدث الذي يطلقه المؤقت Timer؟", "choices": ["Click", "Tick", "Load", "Change"], "answer": 1, "explanation": "المؤقت يطلق Tick كل Interval مللي ثانية."}
```

```quiz
{"question": "كيف تملأ ListBox بعناصر من المصمم؟", "choices": ["خاصية Items مفصولة بـ ;", "لا يمكن إلا بالكود", "خاصية Text", "خاصية Name"], "answer": 0, "explanation": "اكتب العناصر في Items مفصولة بفاصلة منقوطة."}
```

## الخلاصة

- ListBox: `addItem` و`currentRow` و`item(n).text()` و`takeItem` و`count`.
- ComboBox: `currentIndex` و`currentText`، وCheckBox/RadioButton: `isChecked`.
- Timer: `Interval` و`start()` و`stop()` وحدث `Tick`.
- أدوات Qt تبدأ من 0، وقوائم Ring من 1.
