# الدرس 5: النسخة المحمولة والتحديثات والتوقيع

**في هذا الدرس ستتعلم:**

- صنع **نسخة محمولة** (portable) تعمل دون تثبيت.
- إضافة **التحقق من التحديثات** إلى برنامجك بملف `version.json` على موقعك.
- مقارنة أرقام النسخ بشكل صحيح (لماذا `1.10.0` أكبر من `1.9.0`).
- **التوقيع الرقمي** (Authenticode) للبرنامج وبرنامج التثبيت، وأين تُحفظ كلمة المرور.

## النسخة المحمولة (portable)

في نافذة النشر (`Ctrl+Alt+F5`) > تبويب **Setup**، ضع علامة على **Also make a portable .zip of the program**. بعد **Publish** تجد في مجلد `Publish` بجانب برنامج التثبيت ملفًا مثل:

```text
HelloSetup-1.0.0-portable.zip
```

فيه مجلد البرنامج كاملًا. المستخدم يفك الضغط في أي مكان (حتى فلاشة) ويشغّل exe مباشرة. لا اختصارات ولا إلغاء تثبيت، وهذا مناسب لأدوات صغيرة أو أجهزة لا يُسمح فيها بالتثبيت.

> **إذا أردت النسخة المحمولة فقط:** ألغِ علامة **Make the setup**، فيُبنى مجلد البرنامج والـ zip دون برنامج تثبيت.

## التحقق من التحديثات

الفكرة بسيطة: ترفع إلى موقعك ملفًا صغيرًا اسمه `version.json` فيه أحدث نسخة، وبرنامجك يقرؤه ليعرف هل توجد نسخة أحدث:

```text
{"version": "1.2.0", "url": "https://example.com/HelloSetup-1.2.0-setup.exe", "notes": "What is new"}
```

**الإعداد:** تبويب **Signing and Updates**:

- ضع علامة على **The program checks a version.json on the web for a newer version**.
- **version.json URL**: عنوان الملف على موقعك، مثل `https://example.com/myapp/version.json`.
- **Check when the program starts**: التحقق تلقائيًا عند كل تشغيل.

بعد **Publish** تجد `version.json` جاهزًا بجانب برنامج التثبيت. ارفعه مع برنامج التثبيت الجديد إلى موقعك في كل إصدار.

**ماذا يُضاف إلى برنامجك؟**

- برامج Python وVB6 ولغات GUI Bridge: ملف `radupdate.py` يُضمّن في البرنامج. يتحقق في الخلفية عند البدء، وإذا وجد نسخة أحدث يسأل المستخدم «Download it now?». ولقائمة «Check for Updates» في برنامجك: `import radupdate; radupdate.check(interactive=True)`.
- كل البرامج (حتى Ring وFlutter): `CheckForUpdates.ps1` واختصار **Check for Updates** في قائمة ابدأ.

## مقارنة أرقام النسخ

خطأ شائع: مقارنة النسخ **كنصوص**. حرفيًا `"1.10.0" < "1.9.0"` لأن الحرف `1` أصغر من `9`! الصحيح أن نقارن **الأرقام** جزءًا جزءًا:

```python run
def parse(v):
    return tuple(int(x) for x in v.split("-")[0].split("."))

def is_newer(remote, local):
    return parse(remote) > parse(local)

print("مقارنة كنص:", "1.10.0" > "1.9.0")
print("مقارنة كأرقام:", is_newer("1.10.0", "1.9.0"))
print(is_newer("1.2.0", "1.2.0"))
print(is_newer("2.0.0", "1.99.9"))
```

```text output
مقارنة كنص: False
مقارنة كأرقام: True
False
True
```

وهذا مثال يحاكي ما يفعله برنامجك عند البدء: يقرأ `version.json` (هنا نص جاهز بدل الإنترنت) ويقرر:

```python run
import json

CURRENT = "1.0.0"
answer = '{"version": "1.2.0", "url": "https://example.com/HelloSetup-1.2.0-setup.exe", "notes": "إصلاح أخطاء"}'

def parse(v):
    return tuple(int(x) for x in v.split("-")[0].split("."))

info = json.loads(answer)
if parse(info["version"]) > parse(CURRENT):
    print("توجد نسخة أحدث:", info["version"])
    print("الجديد:", info["notes"])
    print("التنزيل من:", info["url"])
else:
    print("لديك أحدث نسخة")
```

```text output
توجد نسخة أحدث: 1.2.0
الجديد: إصلاح أخطاء
التنزيل من: https://example.com/HelloSetup-1.2.0-setup.exe
```

## التوقيع الرقمي (اختياري)

عندما يشغّل المستخدم برنامجًا **غير موقّع** تنزّله من الإنترنت، قد يظهر تحذير ويندوز الأزرق «Windows protected your PC» و«Unknown publisher». **التوقيع الرقمي** يثبت أن البرنامج منك ولم يُعدّل بعدك.

تبويب **Signing and Updates** > **Sign the program and the setup with signtool**:

- **Certificate (.pfx)**: ملف الشهادة، أو
- **Thumbprint**: بصمة شهادة مثبتة في مخزن شهادات ويندوز.

يحتاج ذلك الأداة **signtool** (من Windows SDK) وشهادة توقيع كود تشتريها من جهة معتمدة. البيئة توقّع ملف exe ثم برنامج التثبيت، مع **ختم زمني** (timestamp) حتى يبقى التوقيع صالحًا بعد انتهاء الشهادة.

> **كلمة مرور الشهادة لا تُكتب أبدًا في `publish.json`.** تأتي من متغير البيئة `RADIDE_SIGN_PASSWORD`، أو من مخزن كلمات المرور الآمن في ويندوز (تحفظها من نافذة النشر).

## أخطاء شائعة

- **رفع برنامج التثبيت الجديد ونسيان `version.json`:** البرامج القديمة لن تعرف بالتحديث.
- **رابط `url` خاطئ في `version.json`:** جرّبه في المتصفح قبل الإعلان عن الإصدار.
- **مقارنة النسخ كنصوص:** `1.10` تبدو أصغر من `1.9`. قارن الأرقام.
- **وضع كلمة مرور الشهادة في ملف المشروع:** قد تُرفع إلى Git وتنتشر. استخدم `RADIDE_SIGN_PASSWORD` أو مخزن ويندوز.

## تمرين

### تمرين 1: نسخ تجريبية

النسخ مثل `2.0.0-beta` **أقدم** من `2.0.0` النهائية. عدّل `parse` بحيث ترجع لكل نسخة الأرقام ثم `0` للتجريبية و`1` للنهائية، ثم اطبع `is_newer("2.0.0", "2.0.0-beta")` و`is_newer("2.0.0-beta", "1.9.0")`.

```python exercise
def parse(v):
    return tuple(int(x) for x in v.split("-")[0].split("."))

def is_newer(remote, local):
    return parse(remote) > parse(local)

print(is_newer("2.0.0", "2.0.0-beta"))
print(is_newer("2.0.0-beta", "1.9.0"))
```

```python solution
def parse(v):
    main, _, tag = v.partition("-")
    return tuple(int(x) for x in main.split(".")) + (0 if tag else 1,)

def is_newer(remote, local):
    return parse(remote) > parse(local)

print(is_newer("2.0.0", "2.0.0-beta"))
print(is_newer("2.0.0-beta", "1.9.0"))
```

```text output
True
True
```

## اختبر نفسك

```quiz
{"question": "ما اسم ملف النسخة المحمولة لبرنامج HelloSetup نسخة 1.0.0؟", "choices": ["HelloSetup-1.0.0-setup.exe", "HelloSetup-1.0.0-portable.zip", "portable.exe", "version.json"], "answer": 1, "explanation": "النسخة المحمولة zip بجانب برنامج التثبيت."}
```

```quiz
{"question": "أيهما أحدث: 1.10.0 أم 1.9.0؟", "choices": ["1.9.0", "1.10.0", "متساويان", "لا يمكن المقارنة"], "answer": 1, "explanation": "قارن الأرقام: 10 أكبر من 9."}
```

```quiz
{"question": "أين تُحفظ كلمة مرور شهادة التوقيع؟", "choices": ["في publish.json", "في متغير البيئة RADIDE_SIGN_PASSWORD أو مخزن كلمات المرور في ويندوز", "في الكود", "في version.json"], "answer": 1, "explanation": "الأسرار لا تُكتب في ملفات المشروع."}
```

## الخلاصة

- **Also make a portable .zip**: نسخة تعمل دون تثبيت.
- التحديثات: `version.json` على موقعك + خيار التحقق في تبويب **Signing and Updates**.
- قارن النسخ كأرقام، لا كنصوص.
- التوقيع الرقمي اختياري بـ signtool، وكلمة المرور خارج ملفات المشروع.
