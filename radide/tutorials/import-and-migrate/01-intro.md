# الدرس 1: فتح أم استيراد أم ترحيل؟ ثلاث طرق لإحضار برنامج قديم

**في هذا الدرس ستتعرف على:**

- الطرق الثلاث لإحضار مشروع أو برنامج قديم إلى RAD IDE، ومتى تستخدم كل واحدة.
- أين تجد كل طريقة في القوائم.
- القاعدة القانونية والأخلاقية قبل استيراد أي برنامج من ملف exe.

## تشبيه: الانتقال إلى بيت جديد

عندك أثاث في بيت قديم وتريد أن تنتقل:

- **الفتح في مكانه:** تزور البيت القديم وتعمل فيه كما هو، دون نقل أي شيء.
- **الاستيراد:** تنقل الأثاث إلى البيت الجديد، وترتبه بنفس الشكل تقريبًا.
- **الترحيل:** تنقل الأثاث **وتجدده**: تغيّر القماش وتعيد الدهان، فيصبح أثاثًا جديدًا يناسب البيت الجديد.

## الطريقة الأولى: الفتح في مكانه (Open)

| من أين | ماذا يحدث |
|---|---|
| **File > Open Project...** (`Ctrl+Shift+O`) | يفتح مشاريع RAD IDE، و**مشاريع البيئات الأخرى في مكانها**: Visual Studio (`.sln` و`.csproj`)، وEclipse، وغيرها |
| **File > Open Folder...** (`Ctrl+K Ctrl+O`) | يفتح أي مجلد كمساحة عمل |

لا يُنشأ أي مشروع جديد، وتبقى ملفاتك كما هي. استخدمها عندما تريد **العمل على المشروع بلغته وأدواته الأصلية**.

## الطريقة الثانية: الاستيراد (Import)

من **File > Import** (ملف > استيراد) ثلاثة أوامر:

| الأمر | بالعربية | ماذا يستورد |
|---|---|---|
| Python GUI Program (Tkinter / Qt)... | برنامج واجهة Python (Tkinter / Qt)... | برنامج Python بواجهة: يشغّله ويلتقط نوافذه ويحوّلها إلى نماذج |
| Visual Basic 6 Project (.vbp / .frm)... | مشروع Visual Basic 6 (.vbp / .frm)... | مشروع VB6 أو نموذج واحد |
| Program (.exe / .dll)... | برنامج (.exe / .dll)... | برنامج مترجم، حتى لو فقدت الكود المصدري |

الاستيراد ينشئ **مشروع RAD IDE جديدًا** فيه نماذج تفتحها في المصمم.

## الطريقة الثالثة: الترحيل (Migrate)

**File > Migrate Project...** (ملف > ترحيل المشروع...) يحوّل مشروعًا من بيئة أخرى إلى مشروع RAD IDE **جديد**، وغالبًا إلى **لغة أخرى**: مثلًا من VB6 إلى Python، أو من C# WinForms إلى Python Qt، أو من VB6 إلى VB.NET. وفي النهاية يكتب **تقرير ترحيل** فيه كل ما تحوّل بدقة وما يحتاج تدخلك.

## كيف تختار؟

| موقفك | الطريقة |
|---|---|
| مشروع Visual Studio وتريد الاستمرار بـ C# | **Open Project** في مكانه |
| مشروع VB6 قديم وتريد تشغيله كما هو | **Import > Visual Basic 6 Project** (يعمل على مفسّر BASIC المدمج) |
| مشروع VB6 وتريد تحويله إلى Python حديث | **Migrate Project** |
| برنامج exe قديم فقدت كوده | **Import > Program (.exe / .dll)** |

## مثال: اقتراح الطريقة من امتداد الملف

هذا مثال صغير يقترح الأمر المناسب من امتداد الملف، بنفس منطق الجدول:

```python run
from pathlib import Path

def suggest(path, change_language=False):
    ext = Path(path).suffix.lower()
    if ext in (".exe", ".dll"):
        return "File > Import > Program (.exe / .dll)..."
    if ext in (".vbp", ".frm"):
        if change_language:
            return "File > Migrate Project..."
        return "File > Import > Visual Basic 6 Project..."
    if ext in (".sln", ".csproj", ".vbproj"):
        return "File > Migrate Project..." if change_language else "File > Open Project..."
    return "File > Open Folder..."

print(suggest("Billing.vbp"))
print(suggest("Billing.vbp", change_language=True))
print(suggest("OldTool.exe"))
print(suggest("Shop.sln"))
print(suggest("notes"))
```

```text output
File > Import > Visual Basic 6 Project...
File > Migrate Project...
File > Import > Program (.exe / .dll)...
File > Open Project...
File > Open Folder...
```

## القاعدة القانونية قبل استيراد exe

معالج استيراد البرامج يطلب منك أن تؤكد: **«I wrote this program, own it, or am allowed to analyse it»**، أي: كتبت هذا البرنامج، أو أملكه، أو مسموح لي بتحليله.

- استورد برامجك أنت (مثلًا لاستعادة كود ضاع منك)، أو برامج شركتك بإذنها.
- تحليل البرامج قد يكون ممنوعًا بترخيصها أو بقانون بلدك. اقرأ الترخيص.
- الكود المستعاد **نقطة بداية**: راجعه قبل استخدامه.

## أخطاء شائعة

- **الترحيل عندما يكفي الفتح:** إذا كنت ستكمل بنفس اللغة، فالفتح في المكان أبسط وأدق.
- **توقع نتيجة مثالية 100%:** الاستيراد والترحيل يحولان معظم الأشياء، لكن يبقى دائمًا جزء تكمله أنت. التقرير يخبرك به.
- **العمل على النسخة الأصلية مباشرة:** احتفظ بنسخة من المشروع الأصلي. معالج الترحيل يعرض نسخه إلى `_original/`.

## تمرين

### تمرين 1: أضف ملفات Delphi

عدّل الدالة `suggest` لتقترح `File > Migrate Project...` لملفات Delphi (`.dpr`) وLazarus (`.lpi`)، ثم اطبع الاقتراح للملفين `Calc.dpr` و`Calc.lpi`.

```python exercise
from pathlib import Path

def suggest(path):
    ext = Path(path).suffix.lower()
    if ext in (".exe", ".dll"):
        return "File > Import > Program (.exe / .dll)..."
    return "File > Open Folder..."

print(suggest("Calc.dpr"))
print(suggest("Calc.lpi"))
```

```python solution
from pathlib import Path

def suggest(path):
    ext = Path(path).suffix.lower()
    if ext in (".exe", ".dll"):
        return "File > Import > Program (.exe / .dll)..."
    if ext in (".dpr", ".lpi"):
        return "File > Migrate Project..."
    return "File > Open Folder..."

print(suggest("Calc.dpr"))
print(suggest("Calc.lpi"))
```

```text output
File > Migrate Project...
File > Migrate Project...
```

## اختبر نفسك

```quiz
{"question": "عندك مشروع Visual Studio بلغة C# وتريد الاستمرار بـ C#. ماذا تستخدم؟", "choices": ["File > Migrate Project...", "File > Open Project... (الفتح في مكانه)", "File > Import > Program", "لا شيء"], "answer": 1, "explanation": "الفتح في المكان يُبقي المشروع بلغته وأدواته الأصلية."}
```

```quiz
{"question": "ما الفرق الأساسي بين الاستيراد والترحيل؟", "choices": ["لا فرق", "الترحيل يكتب مشروعًا جديدًا وغالبًا بلغة أخرى مع تقرير مفصل", "الاستيراد يحذف الأصل", "الترحيل للصور فقط"], "answer": 1, "explanation": "الترحيل يحوّل ويجدد، ويكتب MIGRATION_REPORT.md."}
```

```quiz
{"question": "متى يُسمح لك باستيراد برنامج من ملف exe؟", "choices": ["دائمًا", "إذا كتبته أو تملكه أو مسموح لك بتحليله", "إذا كان مجانيًا", "إذا كان صغيرًا"], "answer": 1, "explanation": "المعالج يطلب تأكيد هذا الشرط قبل البدء."}
```

## الخلاصة

- **Open**: العمل على المشروع في مكانه بلغته الأصلية.
- **Import**: مشروع RAD IDE جديد من مشروع VB6 أو برنامج Python أو ملف exe.
- **Migrate**: مشروع جديد محوّل غالبًا إلى لغة أخرى، مع تقرير.
- استورد فقط ما تملكه أو مسموح لك بتحليله.
