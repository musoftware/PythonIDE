# الدرس 2: المشروعات والحلول ومستكشف الحلول

**في هذا الدرس ستتعلم:**

- إنشاء مشروع جديد من نافذة **New Project** واختيار اللغة والقالب.
- ملفات المشروع: `project.radproj` و `Form1.form` وملف الكود والملف المولَّد.
- الفرق بين **المشروع** (Project) و**الحل** (Solution)، ولماذا يجمع الحل لغات مختلفة.
- مستكشف الحلول: قوائم الزر الأيمن، ومشروع بدء التشغيل، والمراجع (References).

## المشروع والحل: المجلد والخزانة

- **المشروع** (Project) مثل **مجلد ورق** واحد: برنامج واحد بلغة واحدة، فيه نماذجه ووحداته.
- **الحل** (Solution) مثل **الخزانة** التي تضم عدة مجلدات: تطبيق رئيسي، ومكتبة حسابات، وربما موقع ويب، وكل واحد بلغته.

ملف الحل اسمه `<الاسم>.radsln`، وملف المشروع اسمه دائمًا `project.radproj`. عندما تفتح مشروعًا وحده تعامله البيئة كحل "ضمني" فيه مشروع واحد.

## إنشاء مشروع جديد خطوة بخطوة

1. **File > New Project...** (ملف > مشروع جديد...) أو `Ctrl+Shift+N`.
2. في اليسار **شجرة اللغات**: اختر مثلًا **Visual Basic 6 (BASIC)** أو **Python (Tkinter)**. في الأعلى مربع بحث: اكتب `python` أو `console` لتصفية القائمة.
3. في الوسط **القوالب** (Templates):

| القالب | الاسم العربي | ماذا ينشئ؟ |
|---|---|---|
| Windows Application | تطبيق Windows | نموذج فارغ تبدأ منه |
| Dialog Application | تطبيق حوار | نموذج ثابت الحجم فيه رسالة وزرّا موافق وإلغاء |
| Data Entry Form | نموذج إدخال بيانات | عناوين ومربعات نص وقائمة وأزرار حفظ / جديد / حذف |
| Console Application | تطبيق سطر أوامر | بلا نافذة: وحدة كود ونقطة بداية، والناتج في Output |
| Class Library | مكتبة أصناف | دوال عامة تستخدمها مشروعات أخرى عبر Add Reference |

4. في الأسفل:
   - **Name:** (الاسم:) اسم المشروع، مثل `Calculator`.
   - **Location:** (الموقع:) المجلد الذي يُحفظ فيه. زر **Browse...** لاختياره.
   - **Solution:** (الحل:) إما **Create new solution** (إنشاء حل جديد)، أو **Add to solution** إذا كان عندك حل مفتوح.
   - **Place solution and project in the same directory** (وضع الحل والمشروع في نفس المجلد): مناسب للمشروعات الصغيرة.
5. اضغط **OK**.

## ماذا يوجد داخل مجلد المشروع؟

مشروع Windows Application بلغة Python (Tkinter) يحتوي:

| الملف | ما هو؟ | هل أعدّله؟ |
|---|---|---|
| `project.radproj` | وصف المشروع (JSON): الاسم، واللغة، والنماذج، ونموذج البداية | نادرًا، والبيئة تكتبه |
| `Form1.form` | تصميم النموذج (JSON): الأدوات وخصائصها | لا، عدّله من المصمم |
| `Form1.py` | **كودك**: معالجات الأحداث | نعم، هذا ملفك |
| `Form1_designer.py` | كود مولَّد من التصميم عند كل حفظ | **لا**، يُكتب من جديد كل مرة |

هكذا يبدو `project.radproj` لمشروع جديد:

```text
{
  "name": "Demo",
  "language": "python-tk",
  "forms": ["Form1"],
  "startup": "Form1",
  "modules": []
}
```

> ⚠️ **انتبه:** لا تكتب كودك في ملف `_designer`. سيُمسح عند الحفظ التالي لأن البيئة تولّده من التصميم.

## مستكشف الحلول (Solution Explorer)

الشجرة تبدأ بـ **Solution 'الاسم'**، وتحتها المشروعات. **مشروع بدء التشغيل** (StartUp Project) يظهر **بخط عريض**: هو الذي يعمل عند `F5`.

انقر بالزر الأيمن لترى أوامر كل عنصر:

| على... | الأوامر المهمة |
|---|---|
| الحل | **Add > New Project... / Existing Project...**، **Build Solution** (بناء الحل)، **Save All**، **Open Folder in File Explorer** |
| مشروع | **Set as StartUp Project** (تعيين كمشروع بدء التشغيل)، **Add > Windows Form... / Module... / Existing Item... / Reference...**، **Manage Packages...**، **Remove from Solution** (إزالة من الحل)، **Properties** |
| References | **Add Reference...** (إضافة مرجع...)، **Refresh References** |
| نموذج | نقر مزدوج يفتح المصمم، و `F7` يفتح الكود |

الألوان في الشجرة تخبرك بحالة Git: أزرق = معدَّل، أخضر = جديد، أحمر = محذوف.

## مشروع فيه أكثر من وحدة

المشروع الواحد يمكن أن يحتوي عدة وحدات (Modules). أضف وحدة من **Project > Add Module...** (مشروع > إضافة وحدة برمجية...).
المثال التالي مشروع فيه وحدتان: `Module1.bas` فيها `Sub Main`، و `MathLib.bas` فيها دالة عامة:

```vb run
'#file: Module1.bas
Sub Main()
    Debug.Print "2 + 3 = " & Add(2, 3)
    Debug.Print "مربع 7 = " & Square(7)
End Sub
'#file: MathLib.bas
Public Function Add(a As Integer, b As Integer) As Integer
    Add = a + b
End Function

Public Function Square(n As Integer) As Integer
    Square = n * n
End Function
```

```text output
2 + 3 = 5
مربع 7 = 49
```

اضغط «افتح في المحرر» وانظر إلى مستكشف الحلول: ستجد الوحدتين تحت المشروع.

## حل بعدة لغات: Add Reference

هنا تظهر قوة الحل. افترض أن عندك مكتبة حسابات بلغة Python وتطبيقًا بلغة BASIC:

1. **File > Add > New Project...** (ملف > إضافة > مشروع جديد...)، واختر قالب **Class Library** بلغة Python، وسمّه `MathLib`.
2. انقر مشروعك الرئيسي بالزر الأيمن > **Add > Reference...** (إضافة > مرجع...).
3. في لسان **Projects** (المشروعات) علّم `MathLib` واضغط **OK**.
4. الآن اكتب في مشروعك `MathLib.Add(2, 3)` كأنها دالة من لغتك نفسها.

تكتب البيئة ملفات "وسيطة" (Proxy) بلغة مشروعك، وتتولى أداة خفية اسمها **RAD Hub** نقل الاستدعاء بين اللغتين وقت التشغيل. القيم تنتقل بصيغة JSON: أرقام، ونصوص، وقيم منطقية، وقوائم.

## خصائص المشروع

**Project > Project Properties...** (مشروع > خصائص المشروع...) تعرض: اسم المشروع، ولغته، ومجلده، ونوع الناتج (Application أو Class Library)، والمراجع، و**Startup form** (نموذج البداية)، والمفسّر المستخدم.

## أخطاء شائعة

- **الضغط على F5 فيعمل مشروع آخر:** مشروع البدء ليس الذي تظنه. انقر مشروعك بالزر الأيمن > **Set as StartUp Project**.
- **كتابة الكود في ملف `_designer`:** يضيع عند الحفظ التالي.
- **نقل ملفات المشروع يدويًا بمستكشف ويندوز ثم فتح المشروع:** إذا نقلت نموذجًا فانقل ملفاته كلها معًا (`.form` وملف الكود).
- **نسيان Add Reference:** استدعاء `MathLib.Add` بدون مرجع يعطي خطأ "اسم غير معروف".

## تمارين

### تمرين 1: أضف دالة إلى المكتبة

أضف إلى الوحدة `MathLib.bas` دالة `Cube(n)` تُرجع مكعب العدد، واطبع `مكعب 3 = 27`.

```vb exercise
'#file: Module1.bas
Sub Main()
    Debug.Print "مكعب 3 = " & Cube(3)
End Sub
'#file: MathLib.bas
' اكتب الدالة Cube هنا
```

```vb solution
'#file: Module1.bas
Sub Main()
    Debug.Print "مكعب 3 = " & Cube(3)
End Sub
'#file: MathLib.bas
Public Function Cube(n As Integer) As Integer
    Cube = n * n * n
End Function
```

```text output
مكعب 3 = 27
```

### مهمة عملية: حل بمشروعين

1. أنشئ مشروعًا جديدًا **Windows Application** بلغة **Visual Basic 6 (BASIC)** باسم `App`.
2. من **File > Add > New Project...** أضف مشروع **Console Application** باسم `Tools`.
3. لاحظ أن الشجرة أصبحت **Solution 'App'** وتحتها مشروعان، وأن `App` بخط عريض.
4. اجعل `Tools` مشروع البدء، واضغط `Ctrl+F5`، ثم أعد `App` كما كان.

## اختبر نفسك

```quiz
{"question": "أي ملف يجب ألّا تكتب فيه كودك؟", "choices": ["`Form1.py`", "`Form1_designer.py`", "`Module1.bas`", "`MathLib.py`"], "answer": 1, "explanation": "ملف `_designer` يولّده المصمم عند كل حفظ، فأي تعديل فيه يضيع."}
```

```quiz
{"question": "كيف تعرف مشروع بدء التشغيل في مستكشف الحلول؟", "choices": ["لونه أحمر", "مكتوب بخط عريض", "عليه علامة نجمة", "يكون آخر مشروع في الشجرة"], "answer": 1, "explanation": "مشروع البدء (StartUp Project) يظهر بخط عريض، وهو الذي يعمل عند F5."}
```

```quiz
{"question": "مشروعك بلغة BASIC ويريد استخدام دوال مكتبة مكتوبة بـ Python في نفس الحل. ماذا تفعل؟", "choices": ["تعيد كتابة المكتبة بـ BASIC", "Add > Reference... ثم تختار المكتبة من لسان Projects", "تنسخ ملف .py داخل مجلد المشروع", "هذا غير ممكن"], "answer": 1, "explanation": "Add Reference يكتب ملفات وسيطة بلغة مشروعك، و RAD Hub ينقل الاستدعاءات بين اللغتين."}
```

## الخلاصة

- المشروع = برنامج بلغة واحدة (`project.radproj`)، والحل = مجموعة مشروعات (`.radsln`) قد تختلف لغاتها.
- **File > New Project...** (`Ctrl+Shift+N`): لغة + قالب + اسم + موقع.
- مستكشف الحلول: الزر الأيمن فيه كل شيء، ومشروع البدء بخط عريض.
- **Add Reference** يجعل مشروعًا يستدعي دوال مشروع آخر، حتى لو كان بلغة أخرى.
