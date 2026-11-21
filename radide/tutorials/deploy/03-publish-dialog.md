# الدرس 3: نافذة النشر وإنشاء برنامج التثبيت

**في هذا الدرس ستتعلم:**

- فتح نافذة **Publish / Create Installer** وتعبئة تبويباتها الثلاثة.
- ملف الإعدادات `publish.json` الذي يُحفظ مع المشروع.
- ماذا يحدث عند الضغط على **Publish**: البناء ثم برنامج التثبيت.
- اسم ملف برنامج التثبيت ومكانه.

## فتح النافذة

**Build > Publish / Create Installer...** أو `Ctrl+Alt+F5` (بالعربية: **بناء > نشر / إنشاء برنامج تثبيت...**). الفكرة مثل نافذة **Publish** في Visual Basic 2005، لكن أبسط: نافذة واحدة فيها ثلاثة تبويبات.

## التبويب 1: Application (التطبيق)

| الحقل | معناه |
|---|---|
| **Application name** | اسم البرنامج كما يراه المستخدم، مثل `Hello Setup` |
| **Version** | رقم النسخة، مثل `1.0.0` |
| **Publisher** | اسمك أو اسم شركتك (يظهر في «التطبيقات المثبتة») |
| **Web site** | موقعك (اختياري) |
| **Program file name** | اسم ملف exe دون امتداد (الافتراضي: الاسم دون مسافات) |
| **Icon** | أيقونة `.ico` (أو `.png` تُحوّل تلقائيًا) |
| **Build as** | طريقة البناء: **Automatic (from the startup form's language)** غالبًا، أو Python (PyInstaller)، أو VB6 / BASIC، أو GUI Bridge، أو Ring، أو Flutter، أو **An already built program folder** |
| **Show a console window** | فقط لبرامج سطر الأوامر |

## التبويب 2: Setup (التثبيت)

| الحقل | معناه |
|---|---|
| **Desktop shortcut** | اختصار على سطح المكتب (يستطيع المستخدم إلغاءه) |
| **Start menu shortcut + uninstall shortcut** | اختصار في قائمة ابدأ ومعه إلغاء التثبيت |
| **Offer to start the program at the end of the setup** | تشغيل البرنامج بعد التثبيت |
| **Install for** | **Current user only (no administrator rights needed)** أو **All users (asks for administrator rights)** |
| **Setup languages** | لغات صفحات التثبيت: English وArabic وغيرهما |
| **License file** / **Read-me before install** | صفحة ترخيص، وصفحة معلومات قبل التثبيت |
| **File type** / **File type description** | ربط امتداد ملف ببرنامجك (مثل `.mydoc`) |
| **Output folder** | مكان الناتج (الافتراضي `Publish`) |
| **Also make a portable .zip of the program** | نسخة محمولة أيضًا (الدرس 5) |
| **Make the setup** | ألغِها إذا أردت بناء مجلد البرنامج فقط دون برنامج تثبيت |

> **نصيحة:** اختر **Current user only**. هكذا يُثبّت البرنامج في `%LOCALAPPDATA%\Programs` **دون صلاحيات المسؤول**، فلا تظهر نافذة UAC، وهو ما تفعله برامج كثيرة حديثة مثل VS Code. ويستطيع المستخدم مع ذلك اختيار «كل المستخدمين» في أول صفحة من برنامج التثبيت.

## التبويب 3: Signing and Updates (التوقيع والتحديثات)

التوقيع الرقمي والتحقق من التحديثات، وسنشرحهما في الدرس 5.

## اضغط Publish

تُحفظ إعداداتك في `publish.json`، ثم يعمل النشر **في الخلفية** وسجله في نافذة **Output**:

**1. البناء:** حسب **Build as**. لبرنامج Python: PyInstaller بمجلد واحد (one-folder)، وبالبيئة الافتراضية `.venv` للمشروع إن وُجدت، أو ببيئة بناء خاصة، حتى **لا يُثبّت شيء في Python العام** عندك.

**2. برنامج التثبيت:** سكربت **Inno Setup** يُكتب ويُترجم (الدرس التالي). إذا لم يكن Inno Setup مثبتًا، تنزّله البيئة **مرة واحدة** من صفحته الرسمية وتثبّته بشكل محمول في `%LOCALAPPDATA%\RADIDE\tools\innosetup`، دون صلاحيات مسؤول ودون تغيير في النظام.

**3. الناتج:** في `Publish` داخل المشروع: `<اسم الملف>-<النسخة>-setup.exe`. ولفتح المجلد: **Build > Open Publish Folder** (بناء > فتح مجلد النشر).

## ملف `publish.json`

الإعدادات تُحفظ في ملف `publish.json` **داخل المشروع**، فتنتقل معه إلى أي جهاز. مثال مختصر (من مشروع المثال `samples\Tests\Installer\HelloSetup`):

```text
{
  "app_name": "Hello Setup",
  "version": "1.0.0",
  "publisher": "RAD IDE Samples",
  "app_id": "{6E0A9B52-3C1D-4F7A-9E2B-5A1C0D7F8B31}",
  "exe_name": "HelloSetup",
  "license_file": "LICENSE.txt",
  "output_dir": "Publish",
  "build_kind": "auto",
  "per_user": true,
  "languages": ["English", "Arabic"],
  "make_installer": true,
  "make_zip": false
}
```

لاحظ `app_id`: معرّف فريد (GUID) للبرنامج. **لا تغيّره أبدًا** بعد أول إصدار، وإلا يظن ويندوز أن النسخة الجديدة برنامج آخر، فيظهر برنامجك مرتين في قائمة البرامج المثبتة. ولا تُكتب كلمة مرور الشهادة في هذا الملف أبدًا.

## مثال: اسم ملف برنامج التثبيت

هذا مثال يحسب اسم ملف exe واسم برنامج التثبيت بنفس قواعد البيئة: إذا كان `exe_name` فارغًا، يُؤخذ اسم البرنامج دون مسافات ورموز:

```python run
import re

def exe_base(app_name, exe_name=""):
    name = exe_name or re.sub(r"[^A-Za-z0-9_.-]+", "", app_name.replace(" ", "")) or "App"
    return name[:-4] if name.lower().endswith(".exe") else name

def setup_file(app_name, version, exe_name=""):
    return f"{exe_base(app_name, exe_name)}-{version}-setup.exe"

print(setup_file("Hello Setup", "1.0.0"))
print(setup_file("Temp Converter!", "2.1.0"))
print(setup_file("My App", "1.0.0", exe_name="Calc.exe"))
```

```text output
HelloSetup-1.0.0-setup.exe
TempConverter-2.1.0-setup.exe
Calc-1.0.0-setup.exe
```

## جرّبها الآن

افتح المجلد `samples\Tests\Installer\HelloSetup` (**File > Open Project...**)، ثم `Ctrl+Alt+F5`، وانظر إلى التبويبات الثلاثة، واضغط **Publish**. يُصنع `Publish\HelloSetup-1.0.0-setup.exe`. شغّله: يُثبّت البرنامج دون صلاحيات مسؤول في `%LOCALAPPDATA%\Programs\Hello Setup`، ويظهر في «التطبيقات المثبتة» حيث يمكن إلغاء تثبيته. (احذف مجلد `Publish` بعد التجربة ليبقى المثال نظيفًا.)

## أخطاء شائعة

- **تغيير `app_id`:** يجعل النسخة الجديدة برنامجًا مختلفًا. لا تغيّره.
- **نسيان رفع `Version`:** المستخدم لا يعرف أن هذه نسخة أحدث، والتحقق من التحديثات لا يعمل.
- **«All users» دون حاجة:** يطلب صلاحيات المسؤول، وقد لا يستطيع موظف في شركة تثبيته.
- **مسار مطلق للأيقونة أو الترخيص:** اجعله نسبيًا داخل المشروع حتى يعمل على أي جهاز.

## تمرين

### تمرين 1: الرقم بأربعة أجزاء

ويندوز يحتاج رقم النسخة بأربعة أرقام في معلومات الملف (مثل `1.2.0.0`). اكتب دالة `numeric_version(v)` تحوّل `"1.2"` إلى `"1.2.0.0"` و`"2.0.1-beta"` إلى `"2.0.1.0"`.

```python exercise
import re

def numeric_version(v):
    pass  # أكمل

print(numeric_version("1.2"))
print(numeric_version("2.0.1-beta"))
```

```python solution
import re

def numeric_version(v):
    nums = [int(n) for n in re.findall(r"\d+", v)[:4]] or [1]
    return ".".join(str(n) for n in (nums + [0, 0, 0, 0])[:4])

print(numeric_version("1.2"))
print(numeric_version("2.0.1-beta"))
```

```text output
1.2.0.0
2.0.1.0
```

## اختبر نفسك

```quiz
{"question": "أين تُحفظ إعدادات النشر؟", "choices": ["في سجل ويندوز", "في publish.json داخل المشروع", "في السحابة", "لا تُحفظ"], "answer": 1, "explanation": "تنتقل مع المشروع إلى أي جهاز."}
```

```quiz
{"question": "لماذا لا تغيّر app_id بعد أول إصدار؟", "choices": ["لأنه سر", "لأن ويندوز سيعامل النسخة الجديدة كبرنامج آخر", "لأنه يبطئ البرنامج", "لا مانع"], "answer": 1, "explanation": "المعرّف الثابت يجعل التحديث يحل محل النسخة القديمة."}
```

```quiz
{"question": "ما ميزة Current user only؟", "choices": ["أسرع في التحميل", "التثبيت دون صلاحيات المسؤول في %LOCALAPPDATA%\\Programs", "يعمل دون ويندوز", "يحذف البرامج الأخرى"], "answer": 1, "explanation": "لا تظهر نافذة UAC."}
```

## الخلاصة

- `Ctrl+Alt+F5`: تبويبات **Application** و**Setup** و**Signing and Updates**، ثم **Publish**.
- الإعدادات في `publish.json`، و`app_id` ثابت لا يتغير.
- الناتج `<exe>-<version>-setup.exe` في مجلد `Publish`، وInno Setup يُنزّل تلقائيًا عند الحاجة.
