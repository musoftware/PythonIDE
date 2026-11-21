# الدرس 3: السمات اللونية وسمات أيقونات الملفات

**في هذا الدرس ستتعلم:**

- اختيار **سمة لونية** (Color Theme) مثبتة من إضافة VS Code.
- اختيار **سمة أيقونات الملفات** (File Icon Theme) لـ Solution Explorer.
- كيف يتحول ملف سمة VS Code إلى ألوان المحرر وألوان البيئة كلها.
- لماذا تبقى النماذج في المصمم بشكل ويندوز الفاتح دائمًا.

## السمة اللونية

بعد أن تثبّت سمة من المتجر (مثل **Dracula** أو **One Dark Pro**)، اخترها بإحدى الطرق:

- **Tools > Options... > Environment > Color theme** (أدوات > خيارات...).
- **لوحة الأوامر** (**View > Command Palette...**، `Ctrl+Shift+P`) واكتب `Color Theme` ثم اختر الاسم، مثل `Color Theme: Dracula`.
- قوائم السمات في **View > Layout** والتخطيطات.

السمة لا تغيّر ألوان **المحرر** فقط، بل ألوان **البيئة كلها**: القوائم، والتبويبات، والأشرطة الجانبية، وشريط الحالة.

> **ملاحظة:** النماذج التي تصممها في المصمم تبقى بشكل ويندوز الفاتح الحقيقي مهما كانت السمة، لأنها تمثل شكل برنامجك عند المستخدم.

## من أين تأتي الألوان؟ ملف سمة VS Code

ملف السمة في إضافة VS Code ملف JSON فيه جزءان مهمان:

| الجزء | ماذا يحدد | مثال |
|---|---|---|
| `colors` | ألوان واجهة البرنامج | `editor.background` و`statusBar.background` |
| `tokenColors` | ألوان أجزاء الكود | التعليقات، والنصوص، والكلمات المحجوزة |

وكل قاعدة في `tokenColors` لها **نطاق** (scope)، مثل `comment` أو `string` أو `keyword`، و**إعدادات** (settings) فيها اللون. البيئة تحوّل `colors` إلى ألوان واجهتها، و`tokenColors` إلى ألوان محرر Monaco.

هذا مثال يقرأ سمة صغيرة (مكتوبة داخل البرنامج) ويستخرج منها لون الخلفية ولون التعليقات:

```python run
import json

theme_text = """{
  "name": "Mini Night",
  "type": "dark",
  "colors": {"editor.background": "#1E1E2E", "statusBar.background": "#7AA2F7"},
  "tokenColors": [
    {"scope": "comment", "settings": {"foreground": "#6C7086", "fontStyle": "italic"}},
    {"scope": ["string", "string.quoted"], "settings": {"foreground": "#A6E3A1"}},
    {"scope": "keyword", "settings": {"foreground": "#CBA6F7"}}
  ]
}"""

theme = json.loads(theme_text)
print("السمة:", theme["name"], "(" + theme["type"] + ")")
print("خلفية المحرر:", theme["colors"]["editor.background"])

for rule in theme["tokenColors"]:
    scopes = rule["scope"] if isinstance(rule["scope"], list) else [rule["scope"]]
    if "comment" in scopes:
        print("لون التعليقات:", rule["settings"]["foreground"])
```

```text output
السمة: Mini Night (dark)
خلفية المحرر: #1E1E2E
لون التعليقات: #6C7086
```

لاحظ أن `scope` قد يكون نصًا واحدًا أو **قائمة** نطاقات، ولذلك حوّلناه دائمًا إلى قائمة.

## سمة أيقونات الملفات

سمات الأيقونات (مثل **Material Icon Theme** أو **vscode-icons**) تعطي كل ملف أيقونة حسب **اسمه** أو **امتداده**: أيقونة Python لملفات `.py`، وأيقونة خاصة لـ `package.json`، وأيقونة مجلد مختلفة لـ `src` ...

اخترها بإحدى الطرق:

- **Tools > Options...** > تبويب **VS Code Extensions** > **File icon theme:**.
- **لوحة الأوامر** (`Ctrl+Shift+P`) > `File Icon Theme...`.
- اختر `None (RAD IDE icons)` للرجوع إلى أيقونات البيئة الأصلية.

إذا لم تكن اخترت أي سمة أيقونات من قبل، فأول سمة تثبتها تُستخدم تلقائيًا.

## كيف تختار سمة الأيقونات الأيقونة المناسبة؟

مثل VS Code تمامًا، يُبحث بهذا الترتيب: **اسم الملف الكامل** أولًا، ثم **أطول امتداد** (مثل `spec.ts` قبل `ts`)، ثم **اللغة**، ثم الأيقونة الافتراضية. هذا مثال مبسّط لنفس الفكرة:

```python run
file_names = {"package.json": "npm", "Dockerfile": "docker"}
extensions = {"spec.ts": "test-ts", "ts": "typescript", "py": "python"}

def icon_for(name):
    if name in file_names:
        return file_names[name]
    parts = name.split(".")
    for i in range(1, len(parts)):
        ext = ".".join(parts[i:])
        if ext in extensions:
            return extensions[ext]
    return "file"

for n in ["package.json", "app.spec.ts", "app.ts", "main.py", "notes.txt"]:
    print(n, "->", icon_for(n))
```

```text output
package.json -> npm
app.spec.ts -> test-ts
app.ts -> typescript
main.py -> python
notes.txt -> file
```

## أخطاء شائعة

- **تثبيت السمة دون اختيارها:** التثبيت يضيفها إلى القائمة فقط. اخترها من **Options** أو من لوحة الأوامر.
- **تعطيل إضافة سمة مستخدمة حاليًا:** ترجع البيئة إلى سمة **Light**، وهذا طبيعي.
- **سمة أيقونات لا تظهر:** تأكد أنها مفعّلة في تبويب **Installed** ومختارة في **File icon theme:**.

## تمارين

### تمرين 1: لون النصوص

عدّل المثال الأول ليطبع **لون النصوص** (`string`) بدل لون التعليقات. انتبه: نطاقها قائمة.

```python exercise
import json

theme = json.loads("""{"tokenColors": [
  {"scope": "comment", "settings": {"foreground": "#6C7086"}},
  {"scope": ["string", "string.quoted"], "settings": {"foreground": "#A6E3A1"}}
]}""")
# اطبع لون النصوص
```

```python solution
import json

theme = json.loads("""{"tokenColors": [
  {"scope": "comment", "settings": {"foreground": "#6C7086"}},
  {"scope": ["string", "string.quoted"], "settings": {"foreground": "#A6E3A1"}}
]}""")
for rule in theme["tokenColors"]:
    scopes = rule["scope"] if isinstance(rule["scope"], list) else [rule["scope"]]
    if "string" in scopes:
        print("لون النصوص:", rule["settings"]["foreground"])
```

```text output
لون النصوص: #A6E3A1
```

### تمرين 2: أيقونة لملفات الاختبار في Python

أضف إلى مثال الأيقونات قاعدة تعطي الامتداد `test.py` الأيقونة `test-python`، ثم اطبع الأيقونة لـ `calc.test.py` و`calc.py`.

```python exercise
extensions = {"py": "python"}

def icon_for(name):
    parts = name.split(".")
    for i in range(1, len(parts)):
        ext = ".".join(parts[i:])
        if ext in extensions:
            return extensions[ext]
    return "file"

print(icon_for("calc.test.py"))
print(icon_for("calc.py"))
```

```python solution
extensions = {"test.py": "test-python", "py": "python"}

def icon_for(name):
    parts = name.split(".")
    for i in range(1, len(parts)):
        ext = ".".join(parts[i:])
        if ext in extensions:
            return extensions[ext]
    return "file"

print(icon_for("calc.test.py"))
print(icon_for("calc.py"))
```

```text output
test-python
python
```

### تمرين 3 (عملي في البيئة)

ثبّت **Material Icon Theme** من `Ctrl+Shift+X`، ثم اختره من لوحة الأوامر `File Icon Theme...` وانظر إلى Solution Explorer. ارجع بعدها إلى `None (RAD IDE icons)`.

## اختبر نفسك

```quiz
{"question": "أي جزء في ملف سمة VS Code يحدد ألوان أجزاء الكود؟", "choices": ["colors", "tokenColors", "name", "type"], "answer": 1, "explanation": "tokenColors فيها قواعد لكل نطاق (scope) مثل comment وstring."}
```

```quiz
{"question": "بأي ترتيب تبحث سمة الأيقونات عن الأيقونة؟", "choices": ["الامتداد أولًا ثم الاسم", "اسم الملف الكامل، ثم أطول امتداد، ثم اللغة، ثم الافتراضية", "عشوائيًا", "حسب حجم الملف"], "answer": 1, "explanation": "مثل VS Code: الاسم الكامل ثم أطول امتداد."}
```

```quiz
{"question": "هل تتغير ألوان النماذج في المصمم مع السمة الداكنة؟", "choices": ["نعم دائمًا", "لا، تبقى بشكل ويندوز الفاتح لأنها تمثل شكل البرنامج عند المستخدم", "فقط مع سمة Dracula", "فقط بعد إعادة التشغيل"], "answer": 1, "explanation": "النماذج المصممة تحتفظ بشكلها الحقيقي."}
```

## الخلاصة

- السمة اللونية: **Options > Environment > Color theme** أو `Color Theme:` في لوحة الأوامر.
- سمة الأيقونات: **Options > VS Code Extensions > File icon theme** أو `File Icon Theme...`.
- ملف السمة: `colors` لواجهة البيئة، و`tokenColors` لألوان الكود.
