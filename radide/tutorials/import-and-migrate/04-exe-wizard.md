# الدرس 4: استيراد برنامج من ملف exe: المعالج والتعرف على النوع

**في هذا الدرس ستتعلم:**

- صفحات معالج **File > Import > Program (.exe / .dll)...**.
- كيف «يعرف» المعالج نوع البرنامج **دون أن يشغّله**.
- الأنواع التي يدعمها، وما الذي يستعيده من كل نوع.
- خيار الترجمة بالذكاء الاصطناعي.

## متى تحتاج هذا؟

- برنامج كتبته قبل سنوات و**ضاع كوده المصدري**، وبقي ملف `exe` فقط.
- برنامج داخلي في شركتك، تريد إعادة بنائه بلغة حديثة، ومعك الإذن بذلك.

## صفحات المعالج

افتح **File > Import > Program (.exe / .dll)...** (ملف > استيراد > برنامج (.exe / .dll)...):

**الصفحة 1: Import a program.** اختر الملف بزر **Browse...**: ملف `.exe` أو `.dll`، أو `.jar` (Java)، أو `app.asar` (Electron). ثم ضع علامة على **I wrote this program, own it, or am allowed to analyse it**. بدونها لا يكمل المعالج.

**الصفحة 2: What kind of program is it?** يعرض المعالج ما اكتشفه: نوع البرنامج، و32 أو 64 بت، والمترجم، ونوع الواجهة، والأدوات المتاحة (مثل Ghidra). وتحت العنوان: «The file was examined without running it»، أي فُحص الملف دون تشغيله.

**الصفحة 3: Options.**

- **Target language**: لغة المشروع الجديد (Python (Tkinter) غالبًا، أو VB6 أو غيرها).
- **Project folder**: مكان المشروع.
- **Translate machine code / decompiled code to Python with AI**: السماح للذكاء الاصطناعي بترجمة الكود الذي لم تستطع القواعد ترجمته.

**الصفحة 4: Importing.** سجل التقدم. البرامج الكبيرة تأخذ وقتًا.

**الصفحة 5: Import report.** الملخص، وخيار **Open the project now**.

## الأنواع المدعومة

| النوع | كيف يُستعاد |
|---|---|
| .NET (C# / VB.NET) بنماذج WinForms | ILSpy يستعيد كود C#، والنماذج من `InitializeComponent`، ثم ترجمة إلى Python بالقواعد أو بالذكاء الاصطناعي |
| Visual Basic 5/6 | تراكيب النماذج داخل الملف تتحول إلى `.frm` ثم إلى مستورد VB6 |
| Python محزوم (PyInstaller وpy2exe وcx_Freeze) | استخراج ملفات `.pyc` ثم فك ترجمتها ثم مستورد Python |
| Java (`.jar`) | فك ترجمة إلى كود Java (ثم Python بالذكاء الاصطناعي إن سمحت) |
| Electron (`app.asar`) | استخراج مشروع JavaScript |
| برامج أصلية (C وC++ وDelphi ...) | الموارد (النوافذ والقوائم والنصوص والأيقونات) + تفكيك الكود + Ghidra إن وُجد |

## كيف يعرف المعالج النوع دون تشغيله؟

كل نوع ملف له **بصمات** معروفة: بايتات ثابتة في أوله أو في داخله. مثلًا:

| البصمة | المعنى |
|---|---|
| `MZ` في أول بايتين | برنامج ويندوز (PE) |
| `PK` في الأول | ملف مضغوط zip، مثل `.jar` |
| `VB5!` في الداخل مع `MSVBVM60.DLL` | برنامج Visual Basic 5/6 |
| `MEI` متبوعة ببايتات خاصة في آخر الملف | برنامج PyInstaller |
| `System.Windows.Forms` مع رأس CLR | برنامج .NET بنماذج WinForms |

> **تشبيه:** مثل الطبيب الذي يعرف كثيرًا عن المريض من **الأشعة** دون أن يفتح جسمه. المعالج يقرأ الملف كبايتات فقط، ولا يشغّله أبدًا، وهذا أكثر أمانًا.

هذا مثال يتعرف على النوع من بايتات **وهمية** صنعناها في الذاكرة، بنفس الفكرة:

```python run
PYI_COOKIE = b"MEI\x0c\x0b\x0a\x0b\x0e"

def identify(data):
    if data[:2] == b"PK":
        return "Java archive / zip"
    if data[:2] != b"MZ":
        return "ليس برنامج ويندوز"
    if b"VB5!" in data and b"MSVBVM60.DLL" in data.upper():
        return "Visual Basic 5/6"
    if PYI_COOKIE in data:
        return "PyInstaller"
    if b"System.Windows.Forms" in data:
        return ".NET WinForms"
    return "برنامج أصلي (native)"

samples = {
    "a.exe": b"MZ\x90\x00...VB5!...msvbvm60.dll",
    "b.exe": b"MZ\x90\x00...python312.dll..." + PYI_COOKIE,
    "c.exe": b"MZ\x90\x00...System.Windows.Forms...",
    "d.exe": b"MZ\x90\x00...kernel32.dll...",
    "e.jar": b"PK\x03\x04...",
    "f.txt": b"hello",
}
for name, data in samples.items():
    print(name, "->", identify(data))
```

```text output
a.exe -> Visual Basic 5/6
b.exe -> PyInstaller
c.exe -> .NET WinForms
d.exe -> برنامج أصلي (native)
e.jar -> Java archive / zip
f.txt -> ليس برنامج ويندوز
```

المعالج الحقيقي يفعل أكثر من ذلك بكثير: يقرأ رأس PE بمكتبة `pefile` (المعالج، و32/64 بت، وقائمة المكتبات المستوردة، ومعلومات النسخة)، ويبحث عن عشرات البصمات (Delphi وQt وGo وRust وInno Setup وغيرها).

## أخطاء شائعة

- **اختيار برنامج تثبيت (setup.exe) بدل البرنامج نفسه:** برامج التثبيت (Inno Setup وNSIS ...) تحتوي البرنامج مضغوطًا. ثبّت البرنامج أولًا، ثم استورد ملف exe المثبت.
- **توقع كود أصلي كامل من برنامج C++:** البرامج الأصلية لا تحتفظ بالكود المصدري. ستحصل على النوافذ ووصف الوظائف وكود تقريبي (الدرس 7).
- **السماح بالذكاء الاصطناعي لبرنامج سري:** خيار AI يرسل الكود إلى المزود المختار. لبرنامج سري استخدم نموذجًا محليًا أو اترك الخيار مغلقًا.

## تمرين

### تمرين 1: أضف بصمة Delphi

برامج Delphi تحتوي غالبًا النص `TPF0` (بداية بيانات نماذج Delphi). أضف إلى `identify` فحصًا يرجع `"Delphi"` لهذه البصمة (بعد فحص `MZ`)، وجرّبه على العينة المعطاة.

```python exercise
def identify(data):
    if data[:2] != b"MZ":
        return "ليس برنامج ويندوز"
    # أضف فحص Delphi هنا
    return "برنامج أصلي (native)"

print(identify(b"MZ...TPF0...TForm1"))
print(identify(b"MZ...kernel32.dll"))
```

```python solution
def identify(data):
    if data[:2] != b"MZ":
        return "ليس برنامج ويندوز"
    if b"TPF0" in data:
        return "Delphi"
    return "برنامج أصلي (native)"

print(identify(b"MZ...TPF0...TForm1"))
print(identify(b"MZ...kernel32.dll"))
```

```text output
Delphi
برنامج أصلي (native)
```

## اختبر نفسك

```quiz
{"question": "هل يشغّل المعالج البرنامج ليتعرف على نوعه؟", "choices": ["نعم دائمًا", "لا، يفحص الملف كبايتات فقط", "فقط برامج .NET", "فقط إذا وافقت"], "answer": 1, "explanation": "The file was examined without running it."}
```

```quiz
{"question": "ماذا تعني البايتات MZ في أول الملف؟", "choices": ["ملف صورة", "برنامج ويندوز (PE)", "ملف نصي", "ملف zip"], "answer": 1, "explanation": "MZ هي بداية كل برامج ويندوز التنفيذية."}
```

```quiz
{"question": "عندك setup.exe لبرنامج. ماذا تفعل قبل الاستيراد؟", "choices": ["تستورده مباشرة", "تثبّت البرنامج ثم تستورد ملف exe المثبت", "تحذفه", "تغيّر امتداده إلى zip"], "answer": 1, "explanation": "برنامج التثبيت غلاف حول البرنامج الحقيقي."}
```

## الخلاصة

- **File > Import > Program (.exe / .dll)...**: الملف والإقرار، ثم النوع، ثم الخيارات، ثم الاستيراد، ثم التقرير.
- المعالج يتعرف على النوع من البصمات دون تشغيل البرنامج.
- يدعم .NET وVB6 وPython المحزوم وJava وElectron والبرامج الأصلية.
- خيار الذكاء الاصطناعي اختياري، وانتبه للخصوصية.
