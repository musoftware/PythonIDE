# الدرس 16: المشروع النهائي: دفتر العناوين

**في هذا الدرس ستبني:**

برنامجًا كاملًا بنافذة RingQt يحفظ أسماء أصدقائك وأرقام هواتفهم في قاعدة بيانات SQLite: إضافة، وحذف، وبحث فوري أثناء الكتابة. ستستخدم فيه كل ما تعلمته تقريبًا: المتغيرات، والشروط، والحلقات، والقوائم، والنصوص، والدوال، والأصناف، والأحداث، وقواعد البيانات.

## الخطة

نقسم البرنامج إلى جزأين، وهذه عادة المحترفين:

1. **طبقة البيانات** (`contacts.ring`): صنف `ContactsDB` يتعامل مع SQLite فقط، ولا يعرف شيئًا عن النوافذ.
2. **الواجهة** (`Form1.ring`): أحداث النافذة، تطلب من `ContactsDB` ما تحتاجه وتعرضه.

> **تشبيه:** المطعم فيه **مطبخ** (البيانات) و**صالة** (الواجهة). النادل لا يطبخ، والطباخ لا يقابل الزبائن. لو أردت تغيير شكل الصالة لا تحتاج إلى هدم المطبخ.

## الخطوة 1: المشروع والتصميم

أنشئ مشروعًا: **File > New Project... > Ring > Ring (RingQt) > Windows Application**، وسمِّه `AddressBook`. اجعل خاصية `Text` للنموذج `دفتر العناوين`، وضع الأدوات:

| الأداة | `Name` | `Text` / ملاحظات |
|---|---|---|
| Label | `lblName` | `الاسم:` |
| TextBox | `txtName` | |
| Label | `lblPhone` | `الهاتف:` |
| TextBox | `txtPhone` | |
| Button | `btnAdd` | `أضف` |
| Label | `lblSearch` | `بحث:` |
| TextBox | `txtSearch` | |
| ListBox | `lstContacts` | اجعل ارتفاعها كبيرًا |
| Button | `btnDelete` | `احذف المختار` |
| Label | `lblStatus` | (فارغ) لعرض الرسائل |

## الخطوة 2: طبقة البيانات

من **Project > Add Module...** (إضافة وحدة برمجية...) أضف وحدة اسمها `contacts`، فيُنشأ الملف `contacts.ring`. والـ IDE تحمّل كل ملفات `.ring` في المشروع عند التشغيل، فيصبح الصنف متاحًا في `Form1.ring`.

## الخطوة 3: الكود كاملًا

في المثال التالي ملفان: السطر `// #file: contacts.ring` يفصل بينهما (في مشروعك الحقيقي كل ملف في تبويب). اضغط «جرّبه» وسيُنشأ المشروع بالملفين:

<!-- test: {"form": {"Text": "دفتر العناوين", "Width": 420, "controls": {"lblName": {"Type": "Label", "Text": "الاسم:"}, "txtName": {}, "lblPhone": {"Type": "Label", "Text": "الهاتف:"}, "txtPhone": {}, "btnAdd": {"Text": "أضف"}, "lblSearch": {"Type": "Label", "Text": "بحث:"}, "txtSearch": {}, "lstContacts": {}, "btnDelete": {"Text": "احذف المختار"}, "lblStatus": {}}}, "do": ["txtName.setText('علي محمود')", "txtPhone.setText('0100 111')", "btnAdd_Click()", "txtName.setText('سارة أحمد')", "txtPhone.setText('0111 222')", "btnAdd_Click()", "txtName.setText(\"O'Brien\")", "txtPhone.setText('0122 333')", "btnAdd_Click()", "txtName.setText('')", "btnAdd_Click()", "cEmpty = lblStatus.text()", "nAll = '' + lstContacts.count()", "txtSearch.setText('سارة')", "cFound = lstContacts.item(0).text()", "nFound = '' + lstContacts.count()", "txtSearch.setText('')", "lstContacts.setCurrentRow(0, 3)", "btnDelete_Click()"], "expect": {"cEmpty": "اكتب الاسم والهاتف أولًا", "nAll": "3", "nFound": "1", "cFound": "سارة أحمد - 0111 222", "lstContacts.count()": "2", "lblStatus.text()": "تم الحذف. عدد الأسماء: 2", "lstContacts.item(0).text()": "سارة أحمد - 0111 222"}} -->
```ring form run
load "Form1_designer.ring"
load "contacts.ring"

oDB = NULL          # كائن قاعدة البيانات
aIds = []           # رقم (id) كل سطر معروض في القائمة، بنفس الترتيب

func Form1_Load
    oDB = new ContactsDB("contacts.db")
    showContacts("")

func btnAdd_Click
    cName = trim(txtName.text())
    cPhone = trim(txtPhone.text())
    if cName = "" or cPhone = ""
        lblStatus.setText("اكتب الاسم والهاتف أولًا")
        return
    ok
    oDB.add(cName, cPhone)
    txtName.clear()
    txtPhone.clear()
    showContacts(trim(txtSearch.text()))
    lblStatus.setText("تمت إضافة " + cName)

func btnDelete_Click
    nRow = lstContacts.currentRow()
    if nRow < 0
        lblStatus.setText("اختر اسمًا من القائمة أولًا")
        return
    ok
    oDB.delete(aIds[nRow + 1])          # Qt من 0 وقوائم Ring من 1
    showContacts(trim(txtSearch.text()))
    lblStatus.setText("تم الحذف. عدد الأسماء: " + oDB.count())

func txtSearch_TextChanged
    showContacts(trim(txtSearch.text()))

func showContacts cFilter
    lstContacts.clear()
    aIds = []
    for aRow in oDB.search(cFilter)
        lstContacts.addItem(aRow[:name] + " - " + aRow[:phone])
        add(aIds, number(aRow[:id]))
    next

// #file: contacts.ring
load "sqlitelib.ring"

# طبقة البيانات: كل التعامل مع SQLite هنا فقط
class ContactsDB
    oSQL = NULL

    func init cFile
        oSQL = sqlite_init()
        sqlite_open(oSQL, cFile)
        sqlite_execute(oSQL, "CREATE TABLE IF NOT EXISTS contacts (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            phone TEXT NOT NULL)")
        return self

    func add cName, cPhone
        sqlite_execute(oSQL, "INSERT INTO contacts (name, phone) VALUES ('" +
                       sqlText(cName) + "', '" + sqlText(cPhone) + "')")

    func delete nId
        sqlite_execute(oSQL, "DELETE FROM contacts WHERE id = " + nId)

    func search cText
        cSQL = "SELECT id, name, phone FROM contacts"
        if cText != ""
            cSQL += " WHERE name LIKE '%" + sqlText(cText) + "%' OR phone LIKE '%" + sqlText(cText) + "%'"
        ok
        return sqlite_execute(oSQL, cSQL + " ORDER BY name")

    func count
        aRows = sqlite_execute(oSQL, "SELECT COUNT(*) AS n FROM contacts")
        return number(aRows[1][:n])

    func sqlText c
        return substr(c, "'", "''")
```

## الخطوة 4: فهم الكود

### طبقة البيانات `ContactsDB`

- `init` يفتح الملف وينشئ الجدول **إذا لم يكن موجودًا** (`CREATE TABLE IF NOT EXISTS`)، فالبيانات تبقى محفوظة بين مرات التشغيل.
- `add` و`delete` و`search` و`count`: كل دالة أمر SQL واحد. لاحظ `sqlText()` التي تحمي النص من علامة `'` (الاسم `O'Brien` في الاختبار).
- `search` تستخدم `LIKE '%نص%'` للبحث عن النص في أي مكان داخل الاسم أو الهاتف.

### الواجهة `Form1.ring`

- `oDB` و`aIds` متغيران **عامّان** لأن كل الأحداث تحتاجهما.
- `showContacts` دالة واحدة تعيد ملء القائمة، تستدعيها الإضافة والحذف والبحث. هذا يمنع تكرار الكود.
- `aIds`: القائمة تعرض نصوصًا فقط، فنحفظ بجانبها رقم كل سجل لنعرف أي سجل نحذف. السطر رقم `nRow` في `lstContacts` يقابله `aIds[nRow + 1]`.
- `txtSearch_TextChanged` يُنفذ مع **كل حرف** يكتبه المستخدم، فتتصفى القائمة فورًا. أنشئه من تبويب **Events** في نافذة **Properties** بعد اختيار `txtSearch`.

## الخطوة 5: التشغيل والتجربة

اضغط `F5`. أضف ثلاثة أسماء، ثم اكتب جزءًا من اسم في مربع البحث، ثم اختر اسمًا واحذفه. أغلق البرنامج وشغّله مرة أخرى: الأسماء ما زالت موجودة لأنها في الملف `contacts.db` داخل مجلد المشروع. افتح نافذة **Databases** (قواعد البيانات) في الـ IDE لترى الجدول نفسه.

## الخطوة 6: أفكار للتطوير

1. **التعديل:** عند اختيار اسم (`lstContacts_SelectedIndexChanged`) اعرض بياناته في المربعين، وأضف زر `btnSave` ينفّذ `UPDATE`.
2. **التأكيد قبل الحذف:** اسأل المستخدم بنافذة رسالة:

```ring
oMsg = new qMessageBox(Form1) {
    setWindowTitle("تأكيد")
    setText("هل تريد حذف هذا الاسم؟")
    setStandardButtons(QMessageBox_Yes | QMessageBox_No)
}
if oMsg.exec() = QMessageBox_Yes
    # احذف
ok
```

3. **التصدير:** زر يحفظ كل الأسماء في ملف `contacts.csv` بالطريقة التي تعلمناها في الدرس 10.
4. **حقل جديد:** أضف عمود `email` إلى الجدول ومربع نص في النافذة.
5. **التوزيع:** من قائمة **Ring** اختر **Build EXE (Publish)...** لتحويل البرنامج إلى ملف `.exe` ومعه ما يحتاجه من مكتبات، فيعمل على أجهزة ليس عليها Ring.

## تمرين: عدد النتائج

عدّل `showContacts` بحيث تكتب في `lblStatus` عدد النتائج الظاهرة، مثل `النتائج: 2`. (تلميح: `lstContacts.count()` بعد الحلقة.) جرّب ذلك على المشروع الذي أنشأته بزر «جرّبه» أعلاه.

## اختبر نفسك

```quiz
{"question": "لماذا وضعنا كود SQLite في صنف منفصل ContactsDB؟", "choices": ["لأن Ring تشترط ذلك", "لفصل البيانات عن الواجهة فيسهل فهم البرنامج وتعديله", "لأن الصنف أسرع", "لا فائدة من ذلك"], "answer": 1, "explanation": "فصل الطبقات يجعل كل جزء مسؤولًا عن شيء واحد."}
```

```quiz
{"question": "لماذا نحتاج القائمة aIds؟", "choices": ["لترتيب الأسماء", "لنعرف رقم السجل في قاعدة البيانات المقابل لكل سطر في ListBox", "لحفظ كلمات المرور", "لعدّ الضغطات"], "answer": 1, "explanation": "ListBox تعرض نصوصًا فقط، وaIds تربط كل سطر برقم السجل."}
```

```quiz
{"question": "إذا اختار المستخدم السطر الأول في lstContacts (currentRow = 0)، أي عنصر من aIds نستخدم؟", "choices": ["aIds[0]", "aIds[1]", "aIds[-1]", "aIds[len(aIds)]"], "answer": 1, "explanation": "Qt يبدأ من 0 وقوائم Ring من 1، فنضيف 1."}
```

## مبروك!

أنهيت دورة Ring من الصفر. أصبحت تعرف أساسيات اللغة، والبرمجة الكائنية، والبرمجة الطبيعية، والنوافذ بـ RingQt، وقواعد البيانات، والإنترنت، والألعاب. الخطوة التالية: افتح **Help > Ring Samples...**، واختر تطبيقًا يعجبك، وابدأ في تعديله وتطويره. وتذكّر أن أفضل طريقة لتعلم البرمجة هي أن **تبني** أشياء تحبها.
