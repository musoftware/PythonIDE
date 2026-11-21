# الدرس 7: البرامج الأصلية (C وC++ وDelphi) مع Ghidra

**في هذا الدرس ستتعلم:**

- لماذا البرامج الأصلية هي الأصعب في الاستعادة.
- ما الذي يستعيده المعالج منها: **الموارد** (النوافذ والقوائم والنصوص والأيقونات) و**معالجات الأحداث** من كود الآلة.
- تثبيت **Ghidra** لاستعادة كود C تقريبي لكل دالة.
- قراءة الملف الذي فيه «بذور» الدوال غير المستعادة.

## لماذا هي الأصعب؟

برامج C وC++ وDelphi تُترجم مباشرة إلى **لغة الآلة** (تعليمات المعالج). أسماء المتغيرات والتعليقات وشكل الكود تضيع كلها. يبقى:

- **الموارد** (Resources): النوافذ المصممة (dialogs)، والقوائم، وجداول النصوص، والأيقونات، ومعلومات النسخة. هذه تُستعاد **بدقة**.
- **كود الآلة**: يمكن تفكيكه وتحليله، والنتيجة **تقريبية**.

> **تشبيه:** البرنامج الأصلي مثل **كعكة مخبوزة**. تستطيع أن ترى شكلها وزينتها بدقة (الموارد)، وتستطيع أن تخمن مكوناتها بالتذوق (التحليل)، لكنك لن تحصل على ورقة الوصفة الأصلية.

## ماذا يفعل المعالج؟

**1. الموارد:** كل نافذة `DIALOG` أو `DIALOGEX` تصبح نموذجًا `.form` (وحدات النافذة تتحول إلى بكسلات)، والقوائم تصبح قوائم، والنصوص تُحفظ في `strings.py`، والأيقونات تُستخرج إلى ملفات `.ico` و`.png`.

**2. التفكيك (capstone):** يُقرأ كود الآلة (x86 وx64)، وتُكتشف «إجراءات النوافذ» من استدعاءات مثل `DialogBoxParam`. وفي كل إجراء، سلسلة المقارنات على رقم الأداة تُربط بالأزرار وعناصر القائمة.

**3. ترجمة استدعاءات ويندوز بالقواعد:** داخل كل فرع، استدعاءات مثل `GetDlgItemText` و`SetDlgItemText` و`MessageBox` و`EndDialog` و`SendDlgItemMessage(LB_ADDSTRING)` تتحول إلى أفعال معروفة: «اقرأ نص الخانة»، و«اكتب في العنوان»، و«أضف إلى القائمة»، و«أغلق».

**4. Ghidra (إن وُجد):** يستعيد كود C تقريبيًا (pseudo-C) لكل دالة.

**5. الذكاء الاصطناعي (إن سمحت):** يترجم الكود التقريبي إلى Python.

**6. بدون ذلك:** تقرير، و«بذرة» Python موثقة لكل دالة.

## مثال حقيقي: برنامج C صغير

هذا جزء من برنامج C (موجود مع البيئة في `samples\Tests\ExeImport\Native_Greeter\source\app.c`):

```c
case IDC_GREET:
  GetDlgItemTextA(h, IDC_NAME, name, 100);
  sprintf(buf, "Hello, %s!", name);
  SetDlgItemTextA(h, IDC_RESULT, buf);
  SendDlgItemMessageA(h, IDC_LIST, LB_ADDSTRING, 0, (LPARAM)name);
```

بعد بنائه بـ MinGW إلى `Greeter.exe` واستيراده، **دون Ghidra ودون ذكاء اصطناعي**، كتب المعالج هذا المعالج لحدث الزر، من كود الآلة وحده:

```python
    def btnGreet_Click(self):
        your_name = self.txtYourName_var.get()
        text = 'Hello, %s!' % (your_name,)
        self.lblResult.config(text=text)
        self.lstItems.insert('end', your_name)
```

وفي التقرير: «frmGreeter.btnGreet.Click: 4 call(s) translated by rules (GetDlgItemTextA, SendDlgItemMessageA, SetDlgItemTextA, sprintf)». لاحظ أن أسماء الأدوات (`txtYourName` و`lblResult` و`lstItems`) جاءت من **نصوص النافذة** في الموارد.

## الدوال التي لم تُستعد: «البذور»

الدوال التي لا يعرفها المعالج تُكتب في ملف `<اسم البرنامج>_native.py` كبذور موثقة: عنوانها في الذاكرة، وحجمها، والاستدعاءات التي فيها، والنصوص التي تستخدمها. هذا مثال من نفس الاستيراد:

```python
def AboutProc(*args):
    """Native function at 0x1400018C3 (58 bytes, 15 instructions).
    Calls: EndDialog
    """
    # EndDialog(?, 0)
    raise NotImplementedError
```

هذه البذور مثل **خريطة**: تعرف منها ماذا كانت كل دالة تفعل تقريبًا، وتكتبها من جديد بنفسك أو بمساعدة الذكاء الاصطناعي.

## تثبيت Ghidra

**Ghidra** أداة مجانية مفتوحة المصدر لتحليل البرامج، تستعيد كودًا قريبًا من C. المعالج يستخدمها تلقائيًا إذا وجدها:

**الخطوة 1:** نزّل Ghidra من موقعها الرسمي (`https://ghidra-sre.org`) وفك الملف المضغوط في `%LOCALAPPDATA%\RADIDE\tools`، فيصبح عندك مجلد مثل `%LOCALAPPDATA%\RADIDE\tools\ghidra_12.2_PUBLIC`. أو ضعه في أي مكان وعرّف متغير البيئة `GHIDRA_HOME` بمساره.

**الخطوة 2:** Ghidra يحتاج **Java (JDK)** بنسخة معينة (مكتوبة في ملفاته). المعالج يبحث عنها ويعرض في صفحة النوع: «Java for Ghidra: ...».

**الخطوة 3:** أعد الاستيراد. في صفحة **What kind of program is it?** يجب أن ترى مسار Ghidra بدل «not installed».

## مثال: من الأفعال المعروفة إلى Python

المعالج يحوّل كل استدعاء ويندوز إلى «فعل» محايد، ثم يكتب الفعل بلغة المشروع. هذا مثال مبسّط لهذه الخطوة الأخيرة: أفعال جاهزة تتحول إلى أسطر Python:

```python run
actions = [
    ("get_text", "your_name", "txtYourName"),
    ("format", "text", "'Hello, %s!' % (your_name,)"),
    ("set_text", "lblResult", "text"),
    ("list_add", "lstItems", "your_name"),
]

def to_python(act):
    kind = act[0]
    if kind == "get_text":
        return f"{act[1]} = self.{act[2]}_var.get()"
    if kind == "format":
        return f"{act[1]} = {act[2]}"
    if kind == "set_text":
        return f"self.{act[1]}.config(text={act[2]})"
    if kind == "list_add":
        return f"self.{act[1]}.insert('end', {act[2]})"
    return f"# TODO: {kind}"

print("def btnGreet_Click(self):")
for a in actions:
    print("    " + to_python(a))
```

```text output
def btnGreet_Click(self):
    your_name = self.txtYourName_var.get()
    text = 'Hello, %s!' % (your_name,)
    self.lblResult.config(text=text)
    self.lstItems.insert('end', your_name)
```

## أخطاء شائعة

- **توقع كود C++ الأصلي:** لن يعود أبدًا كما كُتب. الهدف مشروع **يعمل بنفس الطريقة**، تكمله أنت.
- **برامج النوافذ المرسومة بالكود فقط:** إذا لم تكن النوافذ في الموارد، يحاول المعالج اكتشاف `CreateWindowEx("BUTTON" ...)`، لكن النتيجة أقل دقة.
- **Ghidra دون Java المناسبة:** لا يعمل. انظر سطر «Java for Ghidra» في صفحة النوع.
- **برامج مضغوطة أو محمية (packers):** تحتاج فك الحماية أولًا، والمعالج لا يكسر الحمايات.

## تمرين

### تمرين 1: فعل جديد

أضف إلى `to_python` الفعل `msgbox` الذي يتحول إلى `messagebox.showinfo(title, text)`، ثم اطبع ترجمة الفعل `("msgbox", "'About'", "'Greeter 1.0'")`، علمًا أن العنصر الثاني هو العنوان والثالث هو النص.

```python exercise
def to_python(act):
    kind = act[0]
    if kind == "set_text":
        return f"self.{act[1]}.config(text={act[2]})"
    return f"# TODO: {kind}"

print(to_python(("msgbox", "'About'", "'Greeter 1.0'")))
```

```python solution
def to_python(act):
    kind = act[0]
    if kind == "set_text":
        return f"self.{act[1]}.config(text={act[2]})"
    if kind == "msgbox":
        return f"messagebox.showinfo({act[1]}, {act[2]})"
    return f"# TODO: {kind}"

print(to_python(("msgbox", "'About'", "'Greeter 1.0'")))
```

```text output
messagebox.showinfo('About', 'Greeter 1.0')
```

## اختبر نفسك

```quiz
{"question": "ما الذي يُستعاد بدقة من برنامج C أو C++؟", "choices": ["أسماء المتغيرات المحلية", "الموارد: النوافذ والقوائم والنصوص والأيقونات", "التعليقات", "الكود المصدري كاملًا"], "answer": 1, "explanation": "الموارد محفوظة كما هي في الملف."}
```

```quiz
{"question": "كيف يجد المعالج Ghidra؟", "choices": ["يجب أن يكون في سطح المكتب", "في %LOCALAPPDATA%\\RADIDE\\tools أو من متغير البيئة GHIDRA_HOME", "يُنزّل تلقائيًا دائمًا", "لا يستخدمه"], "answer": 1, "explanation": "ضعه في مجلد الأدوات أو عرّف GHIDRA_HOME."}
```

```quiz
{"question": "ما الملف <البرنامج>_native.py؟", "choices": ["الكود الأصلي الكامل", "بذور موثقة للدوال التي لم تُستعد: العنوان والاستدعاءات والنصوص", "ملف إعدادات", "نسخة احتياطية من exe"], "answer": 1, "explanation": "البذور خريطة لإعادة كتابة الدوال."}
```

## الخلاصة

- البرامج الأصلية: الموارد تُستعاد بدقة، وكود الآلة يُحلل تقريبيًا.
- استدعاءات ويندوز المعروفة تتحول إلى معالجات أحداث بالقواعد.
- Ghidra (مع JDK) يضيف كود C تقريبيًا، والذكاء الاصطناعي يترجمه إلى Python إن سمحت.
- ما لم يُستعد تجده بذورًا موثقة في `_native.py`.
