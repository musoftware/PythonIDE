# الدرس 7: إدارة الإضافات ومشاركتها بأمان

**في هذا الدرس ستتعلم:**

- نافذة **Tools > Extensions...** بالتفصيل: المعلومات، والأخطاء، والأزرار.
- مشاركة إضافتك بملف **zip** أو بمستودع **Git**.
- كيف تحمي البيئة نفسها من ملفات zip الخطيرة.
- مجلد إضافات منفصل للتجارب، والوضع الآمن.
- قائمة أمان قبل تثبيت أي إضافة.

## نافذة الإضافات

افتح **Tools > Extensions...** (أدوات > الإضافات...). في اليسار قائمة إضافات RAD IDE المثبتة، وفي اليمين تفاصيل المختارة:

- المعرّف، والنسخة، والمؤلف، والوصف، والمساهمات.
- **مصدر التثبيت** (مجلد أو zip أو Git) و**مجلد الإضافة**.
- **الأخطاء**: كل خطأ حدث في الإضافة. إذا لم توجد أخطاء ترى «No errors».

والأزرار:

| الزر | بالعربية | الوظيفة |
|---|---|---|
| Disable / Enable | تعطيل / تفعيل | إيقاف الإضافة أو تشغيلها فورًا |
| Uninstall | إلغاء التثبيت | حذفها |
| Open Folder | فتح المجلد | فتح مجلد الإضافة في مستكشف ويندوز |
| Add Control to Project... | | إضافة أداة من الإضافة إلى صندوق أدوات مشروعك |
| Install from Folder... / Zip... / Git URL... | | طرق التثبيت الثلاث |
| Extensions Folder | | فتح مجلد كل الإضافات |
| Plugin API | | فتح توثيق واجهة الإضافات |

## المشاركة بملف zip

اضغط مجلد الإضافة في ملف `.zip` (أو غيّر الامتداد إلى `.radext`)، وأرسله لزميلك. هو يثبّته من **Install from Zip...**.

يمكن أن يكون ملف الوصف في جذر الملف المضغوط، أو داخل مجلد واحد فيه. هذا مثال يضغط مجلد إضافة صغيرًا (في مجلد مؤقت) ويعرض محتوى الملف الناتج:

```python run
import json
import tempfile
import zipfile
from pathlib import Path

work = Path(tempfile.mkdtemp())
ext = work / "hello-ext"
ext.mkdir()
(ext / "radide-extension.json").write_text(json.dumps(
    {"id": "sara.hello", "name": "Hello", "version": "1.0.0", "main": "extension.py"}), encoding="utf-8")
(ext / "extension.py").write_text("def activate(api):\n    api.log('hello')\n", encoding="utf-8")

target = work / "hello-1.0.0.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ext.rglob("*")):
        z.write(p, p.relative_to(work).as_posix())

with zipfile.ZipFile(target) as z:
    for name in z.namelist():
        print(name)
```

```text output
hello-ext/extension.py
hello-ext/radide-extension.json
```

## الحماية من الملفات المضغوطة الخطيرة

قد يحتوي ملف zip خبيث على مسارات مثل `../../Windows/evil.dll` لتكتب **خارج** مجلد الإضافة. البيئة تفحص كل مسار قبل الفك وترفض الملف كله إذا وجدت مسارًا كهذا، وترفض الملفات الأكبر من 200 ميجابايت. هذه الفكرة نفسها في مثال صغير:

```python run
from pathlib import PurePosixPath

def is_safe(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts

for name in ["hello-ext/extension.py", "../../Windows/evil.dll", "/etc/passwd", "a/../../b.txt"]:
    print("مقبول" if is_safe(name) else "مرفوض", name)
```

```text output
مقبول hello-ext/extension.py
مرفوض ../../Windows/evil.dll
مرفوض /etc/passwd
مرفوض a/../../b.txt
```

## المشاركة بمستودع Git

ارفع مجلد الإضافة إلى مستودع (GitHub مثلًا). المستخدم يضغط **Install from Git URL...** ويلصق العنوان. تقبل البيئة عناوين `https://` و`ssh://` و`git@` و`file://`، وتنسخ المستودع بـ `git clone --depth 1` دون مجلد `.git`.

**التحديث:** ارفع النسخة في `radide-extension.json` وادفع التغييرات، فيثبّت المستخدم من نفس العنوان مرة أخرى.

## مجلد للتجارب والوضع الآمن

| متغير البيئة | الوظيفة |
|---|---|
| `RADIDE_EXTENSIONS_DIR=<مجلد>` | استخدام مجلد إضافات آخر، مفيد للتجارب أو للنسخة المحمولة (portable) |
| `RADIDE_SAFE_MODE=1` | بدء البيئة دون أي إضافة |

والإضافات المعطلة تُحفظ قائمتها في `extensions.json` داخل مجلد الإضافات.

## قائمة الأمان قبل التثبيت

الإضافة **برنامج Python** يعمل بصلاحياتك كاملة: يستطيع قراءة ملفاتك وحذفها والاتصال بالإنترنت. لذلك:

1. هل المصدر موثوق؟ (زميل تعرفه، أو مستودع معروف).
2. هل قرأت `radide-extension.json` وملف `main`؟ هل فيه شيء غريب مثل حذف ملفات أو إرسال بيانات؟
3. جرّب أولًا مع `RADIDE_EXTENSIONS_DIR` في مجلد تجارب.
4. راقب **Output** ونافذة الإضافات بعد التثبيت.

## أخطاء شائعة

- **ضغط المجلد الخطأ:** يجب أن يكون `radide-extension.json` في جذر الملف المضغوط أو داخل مجلد واحد فقط، وليس أعمق من ذلك.
- **رفع مجلد `__pycache__` مع الإضافة:** لا ضرر منه، لكنه يكبّر الملف. احذفه قبل الضغط.
- **تثبيت إضافة لأن اسمها جذاب فقط:** اقرأ الكود أولًا.

## تمرين

### تمرين 1: فحص قائمة مسارات

اكتب برنامجًا يمر على قائمة مسارات من ملف مضغوط ويطبع عدد المسارات المرفوضة فقط، باستخدام `is_safe`.

```python exercise
from pathlib import PurePosixPath

def is_safe(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts

names = ["ext/radide-extension.json", "ext/main.py", "../x.py", "ext/../../y.py"]
# اطبع عدد المسارات المرفوضة
```

```python solution
from pathlib import PurePosixPath

def is_safe(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts

names = ["ext/radide-extension.json", "ext/main.py", "../x.py", "ext/../../y.py"]
bad = [n for n in names if not is_safe(n)]
print("مرفوض:", len(bad))
```

```text output
مرفوض: 2
```

### تمرين 2 (عملي في البيئة)

اضغط مجلد `samples\Tests\Extensions\SolarizedTheme` في ملف zip، ثم ثبّته من **Install from Zip...**. افتح نافذة الإضافات وتأكد أن **مصدر التثبيت** صار zip، ثم ألغِ تثبيته.

## اختبر نفسك

```quiz
{"question": "أي طريقة ليست من طرق تثبيت إضافات RAD IDE؟", "choices": ["Install from Folder", "Install from Zip", "Install from Git URL", "Install from Email"], "answer": 3, "explanation": "الطرق الثلاث: مجلد، وzip، وعنوان Git."}
```

```quiz
{"question": "لماذا ترفض البيئة مسارًا مثل ../../evil.dll داخل ملف zip؟", "choices": ["لأنه طويل", "لأنه يكتب خارج مجلد الإضافة", "لأن امتداده dll", "لا ترفضه"], "answer": 1, "explanation": "المسارات التي تخرج من المجلد هجوم معروف (path traversal)."}
```

```quiz
{"question": "ما فائدة RADIDE_EXTENSIONS_DIR؟", "choices": ["حذف الإضافات", "استخدام مجلد إضافات آخر للتجارب أو النسخة المحمولة", "تسريع الإنترنت", "تغيير السمة"], "answer": 1, "explanation": "تجرّب الإضافات في مجلد منفصل دون أن تمس إضافاتك الأساسية."}
```

## الخلاصة

- **Tools > Extensions...** تعرض التفاصيل والأخطاء، وفيها التفعيل والتعطيل والحذف.
- شارك إضافتك بملف zip أو بمستودع Git، وارفع النسخة عند كل تحديث.
- البيئة ترفض الملفات المضغوطة الخطيرة، لكن **قراءة كود الإضافة** مسؤوليتك.

## قاموس مصطلحات الدليل

| المصطلح | بالعربية |
|---|---|
| Extension | إضافة |
| Manifest | ملف الوصف |
| Marketplace | المتجر |
| Theme | سمة |
| Icon theme | سمة أيقونات |
| Grammar | قاعدة لغوية |
| Scope | نطاق |
| Snippet | مقتطف |
| Extension host | مضيف الإضافات |
| Contribution | مساهمة |
