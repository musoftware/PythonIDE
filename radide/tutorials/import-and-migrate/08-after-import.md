# الدرس 8: بعد الاستيراد: التقرير وقائمة المهام والاختبار

**في هذا الدرس ستتعلم:**

- قراءة `IMPORT_REPORT.md` و`MIGRATION_REPORT.md` بسرعة.
- تحويل التقرير إلى **قائمة مهام** مرتبة.
- البحث عن الأسطر التي تحتاج تدخلك في الكود.
- خطة اختبار بسيطة للتأكد أن البرنامج الجديد يعمل مثل القديم.
- كيف يساعدك الذكاء الاصطناعي في الإكمال دون أن يفسد ما نجح.

## أقسام التقرير

**تقرير الاستيراد** (`IMPORT_REPORT.md`) يحتوي عادةً:

| القسم | معناه |
|---|---|
| Identification | ماذا اكتُشف: النوع، والمعالج، والمترجم، والمكتبات |
| Result | اللغة الهدف، ومجلد المشروع، والنماذج وعدد الأدوات والأحداث |
| Recovered exactly | ما استُعيد بدقة |
| Translated by rules | ما تُرجم بالقواعد |
| Not recovered (missing) | ما لم يُستعد |
| Notes | ملاحظات مهمة (مثل «Ghidra is not installed») |

و**تقرير الترحيل** (`MIGRATION_REPORT.md`) يبدأ بجدول الحالات (Exact وRules وApproximate وAI وManual TODO)، ثم قائمة لكل حالة مع **الملف ورقم السطر**.

> **ابدأ دائمًا من الأسفل إلى الأعلى:** Manual TODO أولًا، ثم Approximate، ثم AI. أما Exact وRules فراجعها سريعًا.

## من التقرير إلى قائمة مهام

هذا مثال يقرأ تقرير ترحيل **مثاليًا** (نص جاهز) ويستخرج منه المهام اليدوية مرتبة حسب الملف:

```python run
report = """# Migration report - Billing

## Manual TODO

- `Form1.frm:42` GoTo kept as a comment
- `Module1.bas:7` Declare Function with a structure
- `Form1.frm:88` RaiseEvent kept as a comment

## Approximate

- `Form1.frm:15` On Error Resume Next
"""

todo, section = [], ""
for line in report.splitlines():
    if line.startswith("## "):
        section = line[3:]
    elif line.startswith("- `") and section == "Manual TODO":
        where, text = line[3:].split("` ", 1)
        todo.append((where, text))

for where, text in sorted(todo):
    print("[ ]", where, "-", text)
print("عدد المهام اليدوية:", len(todo))
```

```text output
[ ] Form1.frm:42 - GoTo kept as a comment
[ ] Form1.frm:88 - RaiseEvent kept as a comment
[ ] Module1.bas:7 - Declare Function with a structure
عدد المهام اليدوية: 3
```

## البحث في الكود

الأسطر التي لم تُترجم تبقى تعليقات بعلامات واضحة: `# C#:` في استيراد .NET، و`TODO` في الترحيل، و`raise NotImplementedError` في البذور. ابحث عنها كلها:

- **Edit > Find in Files...** (`Ctrl+Shift+F`) واكتب `TODO` أو `# C#:` أو `NotImplementedError`.
- أو **Error List** بعد **Project > Check for Errors** (`Ctrl+Shift+B`).

وهذا المثال يفعل الشيء نفسه على ملفات وهمية في الذاكرة:

```python run
import re

files = {
    "Form1.py": "def cmdSave_Click(self):\n    # TODO (VB6 Form1.frm:42): GoTo Retry\n    pass\n",
    "Form2.py": "def btnOK_Click(self):\n    # C#: this.Invoke(new Action(Refresh));\n    self.root.destroy()\n",
    "Helpers.py": "def total(xs):\n    return sum(xs)\n",
}

marks = re.compile(r"TODO|# C#:|NotImplementedError")
for name, text in files.items():
    for n, line in enumerate(text.splitlines(), 1):
        if marks.search(line):
            print(f"{name}:{n}: {line.strip()}")
```

```text output
Form1.py:2: # TODO (VB6 Form1.frm:42): GoTo Retry
Form2.py:2: # C#: this.Invoke(new Action(Refresh));
```

## خطة الاختبار: «قديم مقابل جديد»

الهدف أن يتصرف البرنامج الجديد **مثل القديم**. اكتب جدولًا صغيرًا لكل نافذة، وجرّب نفس المدخلات في البرنامجين:

| النافذة | الإجراء | المتوقع (من البرنامج القديم) | الجديد |
|---|---|---|---|
| Form1 | اكتب `Sara` واضغط Greet | `Hello, Sara!` | ✓ |
| Form1 | اضغط Greet والخانة فارغة | رسالة «Type your name» | ✓ |
| Form1 | File > Exit | يُغلق البرنامج | ✓ |

ولأهم الحسابات، اكتب **اختبارات** (Test Explorer: **Test > Run All Tests**) حتى تتأكد أن أي تعديل لاحق لا يكسرها.

## الذكاء الاصطناعي: مساعد للإكمال

- حدد سطرًا مثل `# C#: ...` أو دالة بذرة، واضغط `Ctrl+I` واطلب: «ترجم هذا إلى Python بنفس السلوك». راجع الفرق قبل القبول.
- في **AI Chat**: `اشرح ماذا كانت تفعل هذه الدالة من الاستدعاءات والنصوص @selection`.
- **لا تطلب** «أعد كتابة المشروع كله»: ستفقد ما نجح بالقواعد بدقة. اعمل دالة دالة.

## قائمة الإنهاء

1. احفظ إيداعًا في Git مباشرة بعد الاستيراد، قبل أي تعديل (لترجع إليه).
2. أكمل Manual TODO، ثم راجع Approximate وAI.
3. أعد تسمية الأدوات ذات الأسماء التلقائية (`Button1` ...).
4. نفّذ جدول «قديم مقابل جديد» لكل نافذة.
5. احذف ما لا تحتاجه من `_original/` أو أبقه للرجوع (لا يدخل في البرنامج المنشور).

## أخطاء شائعة

- **التعديل قبل الإيداع الأول:** إذا أفسدت شيئًا لا تستطيع المقارنة بما أنتجه المعالج.
- **تجاهل Notes في التقرير:** قد تخبرك أن أداة ناقصة (Ghidra أو ilspycmd) كانت ستعطيك نتيجة أفضل.
- **الاختبار بالنظر فقط:** جدول المدخلات والنتائج المتوقعة أدق بكثير.

## تمرين

### تمرين 1: عدّ الحالات

اكتب برنامجًا يقرأ التقرير المعطى ويطبع عدد البنود في كل قسم (`Manual TODO` و`Approximate`).

```python exercise
report = """## Manual TODO

- `Form1.frm:42` GoTo
- `Form1.frm:88` RaiseEvent

## Approximate

- `Form1.frm:15` On Error Resume Next
"""
# اطبع عدد البنود في كل قسم
```

```python solution
report = """## Manual TODO

- `Form1.frm:42` GoTo
- `Form1.frm:88` RaiseEvent

## Approximate

- `Form1.frm:15` On Error Resume Next
"""
counts, section = {}, ""
for line in report.splitlines():
    if line.startswith("## "):
        section = line[3:]
        counts[section] = 0
    elif line.startswith("- "):
        counts[section] += 1
for name, n in counts.items():
    print(name, ":", n)
```

```text output
Manual TODO : 2
Approximate : 1
```

## اختبر نفسك

```quiz
{"question": "بأي حالات تبدأ المراجعة بعد الترحيل؟", "choices": ["Exact", "Rules", "Manual TODO ثم Approximate ثم AI", "لا داعي للمراجعة"], "answer": 2, "explanation": "ابدأ بما يحتاج تدخلك فعلًا."}
```

```quiz
{"question": "متى تحفظ أول إيداع Git؟", "choices": ["بعد إكمال كل شيء", "مباشرة بعد الاستيراد وقبل أي تعديل", "لا داعي لـ Git", "بعد النشر"], "answer": 1, "explanation": "الإيداع الأول يحفظ ما أنتجه المعالج للمقارنة والرجوع."}
```

```quiz
{"question": "ما أفضل طريقة لاستخدام الذكاء الاصطناعي في إكمال مشروع مستورد؟", "choices": ["إعادة كتابة المشروع كله مرة واحدة", "دالة دالة مع مراجعة الفرق قبل القبول", "عدم استخدامه أبدًا", "حذف التقرير"], "answer": 1, "explanation": "العمل الصغير المراجَع يحافظ على ما نجح بالقواعد."}
```

## الخلاصة

- التقرير خريطتك: ابدأ بـ Manual TODO.
- ابحث في الكود عن `TODO` و`# C#:` و`NotImplementedError`.
- اختبر بجدول «قديم مقابل جديد»، واكتب اختبارات للحسابات المهمة.
- الذكاء الاصطناعي للإكمال الصغير المراجَع، لا لإعادة الكتابة الشاملة.

## قاموس مصطلحات الدليل

| المصطلح | بالعربية |
|---|---|
| Import | استيراد |
| Migrate | ترحيل |
| Decompile | فك الترجمة |
| Disassemble | تفكيك (إلى تعليمات الآلة) |
| Bytecode | الكود الوسيط |
| Resources | الموارد |
| Stub | بذرة (دالة فارغة موثقة) |
| Twip | تويب (وحدة قياس VB6) |
| Report | تقرير |
| Manual TODO | مهمة يدوية |
