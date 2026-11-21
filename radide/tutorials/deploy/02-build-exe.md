# الدرس 2: بناء ملف EXE واحد

**في هذا الدرس ستتعلم:**

- استخدام **Project > Build EXE...** لصنع ملف `.exe` واحد من مشروع Python.
- ما الأمر الذي تشغّله البيئة فعلًا (PyInstaller)، ومعنى كل خيار فيه.
- أين تجد الملف الناتج، ولماذا يكون كبيرًا.
- كيف يجد برنامجك ملفاته (الصور والبيانات) بعد تحويله إلى EXE.

## الخطوات

**الخطوة 1:** افتح مشروع Python بنافذة (مثلًا **Python (Tkinter)**)، وتأكد أنه يعمل بـ `F5`.

**الخطوة 2:** **Project > Build EXE...** (مشروع > بناء EXE...).

**الخطوة 3:** إذا لم يكن **PyInstaller** مثبتًا، تسألك البيئة: «PyInstaller is not installed ... Install it now with pip (needs internet)?». وافق مرة واحدة.

**الخطوة 4:** راقب نافذة **Output**. في النهاية تظهر رسالة مثل:

```text
------ Build succeeded
EXE created: C:\Projects\TempConverter\dist\TempConverter.exe
```

الملف في المجلد `dist` داخل مشروعك. انسخه وجرّبه بضغطة مزدوجة.

## ماذا تشغّل البيئة؟

البيئة تشغّل PyInstaller بهذه الخيارات تقريبًا:

| الخيار | معناه |
|---|---|
| `--onefile` | ملف EXE **واحد** (يُفك عند التشغيل في مجلد مؤقت) |
| `--windowed` | دون نافذة سوداء (كونسول) خلف برنامجك |
| `--name <اسم المشروع>` | اسم الملف الناتج |
| `--distpath dist` | مكان الملف الناتج |
| `--add-data Resources;Resources` | يضم مجلد `Resources` (صور وأيقونات المشروع) إن وُجد |

هذا مثال يبني قائمة الخيارات نفسها كما تبنيها البيئة لمشروع اسمه `TempConverter`:

```python run
from pathlib import PureWindowsPath

def pyinstaller_args(folder, name, startup_file, has_resources):
    folder = PureWindowsPath(folder)
    args = ["-m", "PyInstaller", "--noconfirm", "--windowed", "--onefile", "--name", name,
            "--distpath", str(folder / "dist"), "--workpath", str(folder / "build")]
    if has_resources:
        args += ["--add-data", f"{folder / 'Resources'};Resources"]
    args.append(str(folder / startup_file))
    return args

for a in pyinstaller_args(r"C:\Projects\TempConverter", "TempConverter", "Form1.py", True):
    print(a)
```

```text output
-m
PyInstaller
--noconfirm
--windowed
--onefile
--name
TempConverter
--distpath
C:\Projects\TempConverter\dist
--workpath
C:\Projects\TempConverter\build
--add-data
C:\Projects\TempConverter\Resources;Resources
C:\Projects\TempConverter\Form1.py
```

## لماذا الملف كبير؟

ملف EXE لبرنامج صغير قد يكون 10 ميجابايت أو أكثر، لأنه يحمل **مفسّر Python** كاملًا ومكتبة الواجهة (Tkinter أو Qt). هذا طبيعي، وهو ثمن أن يعمل البرنامج عند أي مستخدم دون تثبيت Python.

## أين ملفاتي بعد التحويل؟

مع `--onefile` يُفك البرنامج عند التشغيل في **مجلد مؤقت**، ومساره في `sys._MEIPASS`. لذلك إذا كان برنامجك يفتح صورة أو ملف بيانات بجانبه، استخدم دالة مساعدة تعمل في الحالتين (من الكود ومن EXE):

```python run
import sys
from pathlib import Path

def resource(name):
    """مسار ملف من Resources سواء كان البرنامج يعمل من الكود أو من EXE."""
    if getattr(sys, "frozen", False):            # يعمل من EXE صنعه PyInstaller
        base = Path(sys._MEIPASS)
    else:                                         # يعمل من الكود المصدري
        base = Path(".")
    return base / "Resources" / name

print("يعمل من EXE" if getattr(sys, "frozen", False) else "يعمل من الكود المصدري")
print(resource("logo.png").as_posix())
```

```text output
يعمل من الكود المصدري
Resources/logo.png
```

> **انتبه للبيانات التي يكتبها البرنامج:** المجلد المؤقت يُحذف عند الإغلاق، فلا تحفظ فيه شيئًا. احفظ بيانات المستخدم في مجلد مثل `%APPDATA%\اسم البرنامج`.

## ماذا عن اللغات الأخرى؟

- **RingQt:** **Build EXE** يشغّل `ring2exe` (مع `-dist -allruntime -gui -qt`)، والناتج في المجلد `target`.
- **باقي اللغات:** استخدم **Build > Publish / Create Installer...** (الدرس التالي)، فهي تعرف طريقة بناء كل لغة.

## أخطاء شائعة

- **برنامج الحماية يحذّر من الملف:** ملفات `--onefile` غير الموقعة قد تثير شك بعض برامج الحماية. التوقيع الرقمي (الدرس 5) أو برنامج التثبيت يقللان ذلك.
- **«ملف غير موجود» بعد التحويل:** برنامجك يفتح ملفًا بمسار نسبي. استخدم دالة `resource` وضع الملفات في `Resources`.
- **حفظ البيانات بجانب EXE:** مع `--onefile` تُحفظ في مجلد مؤقت وتضيع. استخدم `%APPDATA%`.
- **البناء بنسخة Python غير التي يعمل بها المشروع:** Build EXE يستخدم المفسّر المختار في **Tools > Interpreter Path...**.

## تمرين

### تمرين 1: مكان البيانات

اكتب دالة `data_dir(app_name)` ترجع المسار `APPDATA/app_name` باستخدام متغير البيئة `APPDATA`، وإذا لم يوجد المتغير تستخدم `"."` بدلًا منه. اطبع آخر جزء من المسار للبرنامج `"TempConverter"`.

```python exercise
import os
from pathlib import Path

def data_dir(app_name):
    pass  # أكمل

print(data_dir("TempConverter").name)
```

```python solution
import os
from pathlib import Path

def data_dir(app_name):
    base = os.environ.get("APPDATA", ".")
    return Path(base) / app_name

print(data_dir("TempConverter").name)
```

```text output
TempConverter
```

## اختبر نفسك

```quiz
{"question": "أين يُكتب ملف EXE الذي يصنعه Build EXE؟", "choices": ["في سطح المكتب", "في المجلد dist داخل المشروع", "في مجلد ويندوز", "في Resources"], "answer": 1, "explanation": "الرسالة في Output: EXE created: ...\\dist\\<الاسم>.exe"}
```

```quiz
{"question": "ما فائدة الخيار --windowed؟", "choices": ["تكبير النافذة", "عدم إظهار نافذة الكونسول السوداء خلف البرنامج", "تشغيل البرنامج في متصفح", "ضغط الملف"], "answer": 1, "explanation": "البرامج ذات النوافذ لا تحتاج كونسول."}
```

```quiz
{"question": "أين يجب أن يحفظ البرنامج بيانات المستخدم بعد تحويله إلى EXE واحد؟", "choices": ["في sys._MEIPASS", "في مجلد مثل %APPDATA%\\اسم البرنامج", "في مجلد dist", "لا يحفظ شيئًا"], "answer": 1, "explanation": "المجلد المؤقت يُحذف عند الإغلاق."}
```

## الخلاصة

- **Project > Build EXE...** = PyInstaller بـ `--onefile --windowed`، والناتج في `dist`.
- الملف كبير لأنه يحمل Python معه.
- استخدم `sys._MEIPASS` لملفاتك المضمّنة، و`%APPDATA%` لبيانات المستخدم.
