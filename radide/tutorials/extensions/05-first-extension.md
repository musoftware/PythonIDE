# الدرس 5: إضافتك الأولى: سمة لونية بلا كود

**في هذا الدرس ستتعلم:**

- شكل مجلد إضافة RAD IDE وملف الوصف `radide-extension.json`.
- قواعد **المعرّف** و**رقم النسخة**.
- كتابة **سمة لونية** بملف JSON فقط، دون أي كود.
- تثبيت الإضافة من مجلد وتجربتها فورًا دون إعادة تشغيل.

## شكل المجلد

أبسط إضافة مجلد فيه ملفان:

```text
ocean-theme/
  radide-extension.json      <- ملف الوصف (إجباري)
  themes/ocean.json          <- ملف السمة
```

## ملف الوصف `radide-extension.json`

```text
{
  "id": "ahmed.ocean-theme",
  "name": "Ocean Theme",
  "version": "1.0.0",
  "description": "سمة زرقاء هادئة",
  "author": "Ahmed",
  "license": "MIT",
  "engines": {"radide": ">=1.0"},
  "contributes": {
    "themes": [{"name": "Ocean", "file": "themes/ocean.json"}]
  }
}
```

| المفتاح | القاعدة |
|---|---|
| `id` | إجباري: `ناشر.اسم` بحروف إنجليزية صغيرة وأرقام و`-` و`_`، وفيه نقطة واحدة على الأقل. وهو أيضًا اسم مجلد التثبيت |
| `name` و`version` | إجباريان. النسخة مثل `1.0` أو `1.2.3` أو `2.0.0-beta.1` |
| `engines.radide` | اختياري: أقل نسخة من واجهة الإضافات تحتاجها، مثل `>=1.0` |
| `main` | اختياري: ملف Python فيه الكود (الدرس التالي) |
| `contributes` | اختياري: ما تضيفه بلا كود: `themes` و`languages` و`aiProviders` و`toolbox` |

> **تثبيت نفس المعرّف مرة أخرى** يستبدل الإضافة القديمة، أي أنه **تحديث**. لذلك ارفع رقم النسخة في كل مرة.

## التحقق من المعرّف والنسخة

البيئة تفحص ملف الوصف عند التثبيت وتعرض **كل** المشاكل مرة واحدة. هذا مثال بنفس قواعد المعرّف والنسخة التي تستخدمها البيئة:

```python run
import re

ID_RX = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")
VERSION_RX = re.compile(r"^\d+(\.\d+){0,3}([-+][0-9A-Za-z.-]+)?$")

def problems(manifest):
    out = []
    if not ID_RX.match(manifest.get("id", "")):
        out.append("معرّف غير صحيح: " + repr(manifest.get("id")))
    if not manifest.get("name"):
        out.append("الاسم مفقود")
    if not VERSION_RX.match(manifest.get("version", "")):
        out.append("نسخة غير صحيحة: " + repr(manifest.get("version")))
    return out

good = {"id": "ahmed.ocean-theme", "name": "Ocean Theme", "version": "1.0.0"}
bad = {"id": "Ocean Theme", "version": "v1"}

print("الأول:", problems(good) or "سليم")
for p in problems(bad):
    print("الثاني:", p)
```

```text output
الأول: سليم
الثاني: معرّف غير صحيح: 'Ocean Theme'
الثاني: الاسم مفقود
الثاني: نسخة غير صحيحة: 'v1'
```

## ملف السمة `themes/ocean.json`

سمة RAD IDE لا تحتاج أن تحدد كل الألوان: تختار **سمة أساس** (`base`) وتغيّر ما تريد فقط:

```text
{
  "base": "Dark",
  "monaco": "vs-dark",
  "colors": {"window": "#0B2942", "base": "#011627", "text": "#D6DEEB",
             "accent": "#7FDBCA", "status": "#0B2942"},
  "code":   {"keyword": "#C792EA", "string": "#ECC48D", "comment": "#637777"},
  "chrome": {"line_number": "#4B6479"}
}
```

| الجزء | معناه |
|---|---|
| `base` | السمة التي تُكمل منها الألوان الناقصة: `Light` أو `Blue` أو `Dark` أو `High Contrast` |
| `monaco` | أساس ألوان المحرر: `vs` أو `vs-dark` أو `hc-black` |
| `colors` | ألوان البيئة: `window` و`base` و`text` و`accent` و`status` وغيرها (القائمة الكاملة في `docs/PLUGIN_API.md`) |
| `code` | ألوان الكود: `keyword` و`builtin` و`comment` و`string` و`number` و`decorator` و`defname` و`operator` |
| `chrome` | هوامش المحرر: `margin` و`line_number` و`caret_line` ... |

الألوان تُكتب بالشكل `#RRGGBB`، وأي اسم لون غير معروف يُرفض عند التثبيت.

## التثبيت والتجربة

**الخطوة 1:** افتح **Tools > Extensions...** (أدوات > الإضافات...).

**الخطوة 2:** اضغط **Install from Folder...** واختر المجلد `ocean-theme`. تُنسخ الإضافة إلى `%APPDATA%\RADIDE\extensions\ahmed.ocean-theme` وتعمل **فورًا**.

**الخطوة 3:** افتح **Tools > Options... > Environment > Color theme** واختر **Ocean**.

> **مثال جاهز:** في مجلد البيئة `samples\Tests\Extensions\SolarizedTheme` إضافة سمتين كاملة (Solarized Dark وSolarized Light). ثبّتها بنفس الطريقة وقارن ملفاتها بما كتبت.

## مثال: إنشاء مجلد الإضافة ببرنامج

إذا كنت تصنع سمات كثيرة، يمكنك إنشاء مجلداتها ببرنامج. هذا المثال يكتب الإضافة في مجلد مؤقت ثم يعرض الملفات التي أنشأها:

```python run
import json
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp()) / "ocean-theme"
(root / "themes").mkdir(parents=True)

manifest = {
    "id": "ahmed.ocean-theme", "name": "Ocean Theme", "version": "1.0.0",
    "contributes": {"themes": [{"name": "Ocean", "file": "themes/ocean.json"}]},
}
theme = {"base": "Dark", "colors": {"accent": "#7FDBCA"}, "code": {"comment": "#637777"}}

(root / "radide-extension.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(root / "themes" / "ocean.json").write_text(json.dumps(theme, indent=2), encoding="utf-8")

for p in sorted(root.rglob("*")):
    if p.is_file():
        print(p.relative_to(root).as_posix())
print("السمات:", [t["name"] for t in manifest["contributes"]["themes"]])
```

```text output
radide-extension.json
themes/ocean.json
السمات: ['Ocean']
```

## أخطاء شائعة

- **معرّف بحروف كبيرة أو مسافات:** `Ahmed.Ocean Theme` مرفوض. الصحيح `ahmed.ocean-theme`.
- **مسار خاطئ للسمة:** المسار في `file` نسبي من مجلد الإضافة، ولا يُسمح أن يخرج منه (مثل `../x.json`).
- **اسم لون غير موجود:** مثل `"background"` بدل `"base"`. راجع قائمة الأسماء في `docs/PLUGIN_API.md`.
- **نسيان رفع النسخة:** التحديث يعمل بنفس المعرّف، لكن رقم النسخة يساعدك أنت ومستخدميك على معرفة الأحدث.

## تمارين

### تمرين 1: صحّح ملف الوصف

ملف الوصف التالي فيه مشكلتان. صحّحه حتى تطبع الدالة «سليم».

```python exercise
import re

ID_RX = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")
VERSION_RX = re.compile(r"^\d+(\.\d+){0,3}([-+][0-9A-Za-z.-]+)?$")

manifest = {"id": "Sara.Desert Theme", "name": "Desert", "version": "1.0 beta"}

ok = bool(ID_RX.match(manifest["id"])) and bool(VERSION_RX.match(manifest["version"]))
print("سليم" if ok else "فيه مشاكل")
```

```python solution
import re

ID_RX = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")
VERSION_RX = re.compile(r"^\d+(\.\d+){0,3}([-+][0-9A-Za-z.-]+)?$")

manifest = {"id": "sara.desert-theme", "name": "Desert", "version": "1.0.0-beta"}

ok = bool(ID_RX.match(manifest["id"])) and bool(VERSION_RX.match(manifest["version"]))
print("سليم" if ok else "فيه مشاكل")
```

```text output
سليم
```

### تمرين 2 (عملي في البيئة)

اصنع المجلد `ocean-theme` بالملفين كما في الدرس، ثبّته من **Install from Folder...**، واختر السمة **Ocean**. غيّر بعدها لون `accent` في `ocean.json`، وارفع النسخة إلى `1.0.1`، وثبّت المجلد مرة أخرى لترى التحديث.

## اختبر نفسك

```quiz
{"question": "أي معرّف صحيح لإضافة RAD IDE؟", "choices": ["Ocean Theme", "ahmed.ocean-theme", "ahmed", "Ahmed.Ocean"], "answer": 1, "explanation": "المعرّف: حروف صغيرة وأرقام و- و_، وفيه نقطة واحدة على الأقل."}
```

```quiz
{"question": "ما فائدة \"base\" في ملف السمة؟", "choices": ["اسم الإضافة", "السمة التي تُكمل منها كل الألوان التي لم تحددها", "حجم الخط", "لغة البرنامج"], "answer": 1, "explanation": "تحدد الألوان التي تريد تغييرها فقط، والباقي من سمة الأساس."}
```

```quiz
{"question": "ماذا يحدث إذا ثبّت إضافة بنفس المعرّف مرة أخرى؟", "choices": ["تُرفض", "تُستبدل القديمة (تحديث)", "تصبح عندك نسختان", "تتوقف البيئة"], "answer": 1, "explanation": "نفس المعرّف = تحديث للإضافة."}
```

## الخلاصة

- الإضافة مجلد فيه `radide-extension.json`، والسمة ملف JSON في `contributes.themes`.
- المعرّف `ناشر.اسم` بحروف صغيرة، والنسخة مثل `1.0.0`.
- سمة RAD IDE تبدأ من `base` وتغيّر ما تريد في `colors` و`code` و`chrome`.
- **Tools > Extensions... > Install from Folder...** ثم اختر السمة من **Options**.
