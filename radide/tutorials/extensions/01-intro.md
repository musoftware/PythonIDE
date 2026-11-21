# الدرس 1: ما الإضافات؟ نوعان في RAD IDE

**في هذا الدرس ستتعرف على:**

- معنى **الإضافة** (Extension) ولماذا تحتاجها.
- النوعين الموجودين في البيئة: **إضافات VS Code** و**إضافات RAD IDE**.
- أين تجد كل نوع في القوائم.
- كيف تبدأ البيئة دون أي إضافة إذا حدثت مشكلة.

## الإضافة مثل تطبيقات الهاتف

الهاتف الجديد فيه تطبيقات أساسية، وأنت تضيف ما تحتاجه من المتجر: لعبة، أو قاموس، أو خلفية جديدة. **الإضافة** في البيئة بالفكرة نفسها: حزمة صغيرة تضيف ميزة لم تكن موجودة، مثل:

- **سمة لونية** (Theme) تغيّر ألوان البيئة والمحرر.
- **سمة أيقونات** تعطي كل نوع ملف أيقونة مميزة في **Solution Explorer**.
- **دعم لغة**: تلوين الكود ومقتطفات جاهزة لها.
- **أداة** جديدة في القوائم، أو نافذة جانبية، أو معلومة في شريط الحالة.

## النوع الأول: إضافات VS Code (من متجر Open VSX)

**Open VSX** (`https://open-vsx.org`) متجر مفتوح لإضافات VS Code، تستخدمه أيضًا برامج مثل VSCodium. البيئة تستطيع تثبيت هذه الإضافات وتشغيل أغلب ما فيها:

| ما تدعمه البيئة من إضافات VS Code | أمثلة |
|---|---|
| السمات اللونية | Dracula، One Dark Pro، Solarized |
| سمات أيقونات الملفات | Material Icon Theme، vscode-icons |
| اللغات والقواعد اللغوية والمقتطفات | دعم لغات جديدة في المحرر |
| الإضافات التي فيها كود JavaScript | تعمل في «مضيف إضافات» يستخدم Node.js |

أين تجدها؟

- **View > Extensions (VS Code)** أو `Ctrl+Shift+X` (بالعربية: **عرض > الإضافات (VS Code)**).
- **Tools > VS Code Extensions (Open VSX)...** (أدوات > إضافات VS Code (Open VSX)...).
- **Tools > Install Extension from VSIX...** لتثبيت ملف `.vsix` موجود عندك (أدوات > تثبيت إضافة من ملف VSIX...).

## النوع الثاني: إضافات RAD IDE (بلغة Python)

هذه إضافات مكتوبة خصيصًا للبيئة بلغة **Python**. كل إضافة **مجلد** فيه ملف وصف اسمه `radide-extension.json`، وقد يكون فيه كود Python. تستطيع أن:

- تضيف أوامر إلى القوائم، ونوافذ، وأزرارًا في شريط الأدوات وشريط الحالة.
- تسجّل سمات لونية، ولغات، ومزودي ذكاء اصطناعي، وأدوات لصندوق الأدوات (Toolbox).

أين تجدها؟ **Tools > Extensions...** (أدوات > الإضافات...)، وفيها أزرار **Install from Folder...** و**Install from Zip...** و**Install from Git URL...**.

> **الفرق باختصار:** إضافات VS Code جاهزة بالآلاف وتجلبها من المتجر. إضافات RAD IDE تكتبها أنت أو زملاؤك بلغة Python لتخصيص البيئة كما تريد، وسنكتب واحدة في الدرسين 5 و6.

## أين تُحفظ الإضافات؟

| النوع | المجلد |
|---|---|
| إضافات RAD IDE | `%APPDATA%\RADIDE\extensions\<id>` |
| إضافات VS Code | مجلد إضافات VSX للبيئة، ويُفتح من قائمة نافذة الإضافات |

## إذا تعطلت البيئة بسبب إضافة

كل إضافة تعمل في «غرفة معزولة»: إذا حدث فيها خطأ، يُكتب الخطأ في نافذة **Output** وفي نافذة الإضافات، وتبقى البيئة والإضافات الأخرى تعمل. ومع ذلك، إذا أردت أن تبدأ البيئة **دون أي إضافة**، عرّف متغير البيئة `RADIDE_SAFE_MODE` بالقيمة `1` قبل تشغيلها:

```text
set RADIDE_SAFE_MODE=1
run.bat
```

## مثال: معرّف الإضافة

كل إضافة لها **معرّف** (id) فريد من جزأين يفصل بينهما نقطة: **الناشر** ثم **الاسم**، مثل `dracula-theme.theme-dracula`. هذا مثال يفصل المعرّف إلى جزأيه:

```python run
ids = ["dracula-theme.theme-dracula", "PKief.material-icon-theme", "radide-samples.word-count"]

for ext_id in ids:
    publisher, name = ext_id.split(".", 1)
    print("الناشر:", publisher, "| الاسم:", name)
```

```text output
الناشر: dracula-theme | الاسم: theme-dracula
الناشر: PKief | الاسم: material-icon-theme
الناشر: radide-samples | الاسم: word-count
```

## أخطاء شائعة

- **الخلط بين النافذتين:** إضافات VS Code في **View > Extensions (VS Code)**، وإضافات RAD IDE في **Tools > Extensions...**. وتظهر إضافات RAD IDE أيضًا في تبويب **Installed** بنافذة VS Code، لكن إدارتها من نافذتها الخاصة.
- **تثبيت إضافات من مصدر مجهول:** الإضافة برنامج يعمل بصلاحياتك. ثبّت من مصادر تثق بها فقط.
- **توقع أن كل إضافات VS Code تعمل:** السمات والأيقونات واللغات تعمل جيدًا. أما الإضافات التي تعتمد على أجزاء خاصة جدًا بـ VS Code فقد تعمل جزئيًا فقط.

## تمرين

### تمرين 1: من المعرّف إلى صفحة المتجر

صفحة أي إضافة في متجر Open VSX عنوانها `https://open-vsx.org/extension/<الناشر>/<الاسم>`. اكتب برنامجًا يطبع عنوان الصفحة لكل معرّف في القائمة.

```python exercise
ids = ["dracula-theme.theme-dracula", "PKief.material-icon-theme"]
# اطبع عنوان صفحة كل إضافة
```

```python solution
ids = ["dracula-theme.theme-dracula", "PKief.material-icon-theme"]
for ext_id in ids:
    publisher, name = ext_id.split(".", 1)
    print(f"https://open-vsx.org/extension/{publisher}/{name}")
```

```text output
https://open-vsx.org/extension/dracula-theme/theme-dracula
https://open-vsx.org/extension/PKief/material-icon-theme
```

## اختبر نفسك

```quiz
{"question": "أين تجد متجر إضافات VS Code في البيئة؟", "choices": ["Tools > Extensions...", "View > Extensions (VS Code) أو Ctrl+Shift+X", "Help > About", "File > Import"], "answer": 1, "explanation": "Ctrl+Shift+X يفتح نافذة إضافات VS Code (Open VSX). أما Tools > Extensions... فلإضافات RAD IDE."}
```

```quiz
{"question": "بأي لغة تُكتب إضافات RAD IDE الخاصة؟", "choices": ["JavaScript فقط", "Python", "C++", "لا تحتوي كودًا أبدًا"], "answer": 1, "explanation": "إضافات RAD IDE مجلد فيه radide-extension.json وكود Python اختياري."}
```

```quiz
{"question": "ماذا يفعل RADIDE_SAFE_MODE=1؟", "choices": ["يحذف كل الإضافات", "يبدأ البيئة دون تحميل أي إضافة", "يحدّث الإضافات", "يغيّر السمة"], "answer": 1, "explanation": "الوضع الآمن يتخطى الإضافات كلها دون حذفها."}
```

## الخلاصة

- الإضافة حزمة تضيف ميزة: سمة، أيقونات، لغة، أداة.
- **إضافات VS Code** من متجر Open VSX: `Ctrl+Shift+X`.
- **إضافات RAD IDE** بلغة Python: **Tools > Extensions...**.
- كل إضافة معزولة، و`RADIDE_SAFE_MODE=1` يبدأ البيئة دونها.
