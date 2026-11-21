# الدرس 2: متجر Open VSX: البحث والتثبيت والتحديث

**في هذا الدرس ستتعلم:**

- استخدام نافذة **Extensions** للبحث في متجر Open VSX.
- قراءة بطاقة الإضافة وصفحة **التفاصيل** قبل التثبيت.
- التثبيت، والتعطيل، وإلغاء التثبيت، والتحديث.
- تثبيت ملف `.vsix`، والعمل دون إنترنت.

## فتح النافذة

اضغط `Ctrl+Shift+X` أو افتح **View > Extensions (VS Code)** (عرض > الإضافات (VS Code)). في تخطيط VS Code تظهر النافذة في الشريط الجانبي مثل VS Code تمامًا.

في النافذة ثلاثة تبويبات:

| التبويب | بالعربية | ماذا فيه |
|---|---|---|
| Marketplace | المتجر | البحث في Open VSX |
| Installed | مثبّت | الإضافات المثبتة عندك (مع عددها) |
| Updates | التحديثات | الإضافات التي لها نسخة أحدث |

## البحث

اكتب في مربع **Search Extensions in Open VSX** كلمة مثل `dracula` أو `python` أو `icons`. يمكنك أيضًا:

- اختيار **تصنيف** (Themes، Programming Languages، Snippets ...) من القائمة **All categories**.
- تغيير **الترتيب**: `Relevance` (الصلة)، أو `Most downloads` (الأكثر تنزيلًا)، أو `Rating` (التقييم)، أو `Recently published` (الأحدث).
- الضغط على **Load more** لعرض نتائج إضافية.

كل نتيجة **بطاقة** فيها: الأيقونة، والاسم، والناشر، وعدد التنزيلات، والتقييم، وزر **Install**.

## صفحة التفاصيل: اقرأ قبل أن تثبّت

اضغط على اسم الإضافة لتفتح صفحة **Details** (التفاصيل) في منطقة المحرر. فيها:

- ملف **README** (شرح الإضافة) و**CHANGELOG** (سجل التغييرات).
- **المساهمات** (contributions): ماذا تضيف الإضافة (سمات، لغات، أوامر ...)، و**أيها تدعمه البيئة**.
- **الاعتماديات** (dependencies): إضافات أخرى تحتاجها، وتُثبَّت معها تلقائيًا.
- **منتقي النسخة**: لتثبيت نسخة أقدم إذا كانت الأحدث لا تناسبك.

> **تشبيه:** صفحة التفاصيل مثل **مكونات المنتج** على علبة الطعام. اقرأها قبل الشراء، خصوصًا قسم «ما تدعمه البيئة».

## التثبيت والإدارة

- **Install**: تُنزَّل الإضافة وتُفحص بصمتها (SHA256) إن كانت منشورة، وتُثبّت مع اعتمادياتها.
- في تبويب **Installed**: **Disable** (تعطيل) و**Enable** (تفعيل) و**Uninstall** (إلغاء التثبيت).
- السمات والأيقونات واللغات تعمل **فورًا**. أما الإضافات التي فيها كود فقد يظهر شريط **Restart required** وزر **Reload** لإعادة تشغيل «مضيف الإضافات».

## التحديثات

تفحص البيئة التحديثات مرة في كل جلسة في الخلفية، فيظهر الرقم بجانب تبويب **Updates**. ويمكنك الفحص يدويًا من قائمة النافذة: **Check for Extension Updates**.

## تثبيت ملف VSIX

ملف `.vsix` هو إضافة VS Code مضغوطة في ملف واحد (مثل ملف zip). قد تحصل عليه من زميل أو من موقع الإضافة. لتثبيته:

- **Tools > Install Extension from VSIX...**، أو
- قائمة نافذة الإضافات > **Install from VSIX...**.

## دون إنترنت

كل ما تبحث عنه أو تفتح تفاصيله يُحفظ في **ذاكرة مؤقتة** (cache). إذا انقطع الإنترنت، تعرض النافذة النتائج المحفوظة. ولمسح هذه الذاكرة: قائمة النافذة > **Clear Marketplace Cache**.

## مثال: كيف تبدو نتائج البحث من الداخل؟

البيئة تسأل Open VSX عبر الإنترنت، فيرد بنص JSON فيه قائمة إضافات. هذا مثال بنتائج **جاهزة** (دون اتصال) يرتبها حسب عدد التنزيلات كما تفعل البيئة عند اختيار الترتيب بالتنزيلات:

```python run
import json

answer = """{"extensions": [
  {"namespace": "dracula-theme", "name": "theme-dracula", "version": "2.25.1", "downloadCount": 900000},
  {"namespace": "zhuangtongfa", "name": "material-theme", "version": "3.19.0", "downloadCount": 700000},
  {"namespace": "ryanolsonx", "name": "solarized", "version": "2.0.3", "downloadCount": 120000}
]}"""

data = json.loads(answer)
items = sorted(data["extensions"], key=lambda e: e["downloadCount"], reverse=True)
for e in items:
    ext_id = e["namespace"] + "." + e["name"]
    print(f"{ext_id} {e['version']} - {e['downloadCount']:,} تنزيل")
```

```text output
dracula-theme.theme-dracula 2.25.1 - 900,000 تنزيل
zhuangtongfa.material-theme 3.19.0 - 700,000 تنزيل
ryanolsonx.solarized 2.0.3 - 120,000 تنزيل
```

## أخطاء شائعة

- **تثبيت إضافة عشوائية:** انظر إلى الناشر وعدد التنزيلات وتاريخ آخر تحديث، واقرأ README.
- **الظن أن الإضافة لم تعمل:** بعض الإضافات (السمات مثلًا) تحتاج أن **تختارها** بعد التثبيت. سنرى ذلك في الدرس التالي.
- **تجاهل Restart required:** الإضافة التي فيها كود لا تعمل نسختها الجديدة حتى تضغط **Reload**.
- **إضافة لا تظهر في البحث:** المتجر هنا **Open VSX** وليس متجر Microsoft. بعض الإضافات منشورة في متجر Microsoft فقط، ويمكنك تثبيتها من ملف `.vsix` إذا كان ترخيصها يسمح.

## تمارين

### تمرين 1: فلترة النتائج

من النتائج نفسها، اطبع معرّفات الإضافات التي تنزيلاتها **أكثر من 500,000** فقط.

```python exercise
extensions = [
    {"namespace": "dracula-theme", "name": "theme-dracula", "downloadCount": 900000},
    {"namespace": "zhuangtongfa", "name": "material-theme", "downloadCount": 700000},
    {"namespace": "ryanolsonx", "name": "solarized", "downloadCount": 120000},
]
# اطبع المعرّفات التي تنزيلاتها أكثر من 500000
```

```python solution
extensions = [
    {"namespace": "dracula-theme", "name": "theme-dracula", "downloadCount": 900000},
    {"namespace": "zhuangtongfa", "name": "material-theme", "downloadCount": 700000},
    {"namespace": "ryanolsonx", "name": "solarized", "downloadCount": 120000},
]
for e in extensions:
    if e["downloadCount"] > 500000:
        print(e["namespace"] + "." + e["name"])
```

```text output
dracula-theme.theme-dracula
zhuangtongfa.material-theme
```

### تمرين 2 (عملي في البيئة)

افتح `Ctrl+Shift+X`، وابحث عن `dracula`، وافتح صفحة **Details** للإضافة الأشهر، واقرأ قسم المساهمات. ثبّتها، ثم تأكد أنها ظهرت في تبويب **Installed**.

## اختبر نفسك

```quiz
{"question": "ما الذي يُعرض في صفحة Details؟", "choices": ["README والمساهمات والاعتماديات والنسخ", "كلمة مرور المتجر", "كود البيئة نفسها", "قائمة مشاريعك"], "answer": 0, "explanation": "صفحة التفاصيل تعرض كل ما تحتاجه لتقرر التثبيت."}
```

```quiz
{"question": "ما ملف .vsix؟", "choices": ["صورة", "إضافة VS Code مضغوطة في ملف واحد", "مشروع RAD IDE", "قاعدة بيانات"], "answer": 1, "explanation": "ملف .vsix هو حزمة إضافة VS Code، ويُثبّت من Tools > Install Extension from VSIX..."}
```

```quiz
{"question": "ماذا يحدث إذا انقطع الإنترنت وأنت تبحث في المتجر؟", "choices": ["تتوقف البيئة", "تُعرض النتائج المحفوظة في الذاكرة المؤقتة", "تُحذف الإضافات", "لا شيء يظهر أبدًا"], "answer": 1, "explanation": "النتائج والتفاصيل تُحفظ لتعمل النافذة دون إنترنت."}
```

## الخلاصة

- `Ctrl+Shift+X`: تبويبات **Marketplace** و**Installed** و**Updates**.
- اقرأ صفحة **Details** قبل التثبيت، خصوصًا ما تدعمه البيئة.
- **Install** يثبّت الإضافة مع اعتمادياتها، و**Disable/Uninstall** من تبويب Installed.
- ملفات `.vsix` تُثبّت من **Tools > Install Extension from VSIX...**.
