# الدرس 1: طرق توصيل برنامجك إلى المستخدم

**في هذا الدرس ستتعرف على:**

- لماذا لا يكفي أن «يعمل البرنامج عندي».
- الطرق الأربع لتوصيل البرنامج: ملف EXE، وبرنامج تثبيت، ونسخة محمولة، ونشر على الإنترنت.
- أين تجد كل طريقة في قوائم البيئة.

## «يعمل عندي!»

برنامجك يعمل في البيئة لأن جهازك فيه كل شيء: Python، والمكتبات، وملفات المشروع. أما المستخدم العادي فقد لا يكون عنده Python أصلًا، ولا يعرف ما `pip`. **النشر** (Deployment) هو أن تحوّل مشروعك إلى شيء يعمل عند المستخدم **بضغطة مزدوجة**.

> **تشبيه:** الطبخ في مطبخك سهل، لأن كل الأدوات حولك. أما توصيل الطعام لزبون فيحتاج **علبة** محكمة فيها كل شيء، مع ملصق واضح. النشر هو هذه العلبة.

## الطرق الأربع

| الطريقة | من أين | متى تستخدمها |
|---|---|---|
| **ملف EXE واحد** | **Project > Build EXE...** (مشروع > بناء EXE...) | تجربة سريعة، أو أداة صغيرة ترسلها لزميل |
| **برنامج تثبيت** (setup.exe) | **Build > Publish / Create Installer...** (`Ctrl+Alt+F5`، بالعربية: بناء > نشر / إنشاء برنامج تثبيت...) | برنامج حقيقي لمستخدمين: اختصارات في قائمة ابدأ، وإلغاء تثبيت من الإعدادات |
| **نسخة محمولة** (portable .zip) | خيار في نافذة النشر نفسها | يعمل دون تثبيت، من مجلد أو فلاشة |
| **نشر موقع ويب** | **Site > Publish...** (`Ctrl+Alt+P`) و**Site > Deploy to Cloud / Git / SSH...** | مواقع الويب: FTP وSFTP ومجلد وخدمات سحابية |

وللتطبيقات المحمولة (Flutter وKivy ...) قائمة خاصة: **Build > Mobile App** (تطبيق موبايل) فيها Android APK وAndroid App Bundle وWindows EXE وWeb site. ولها دليلها الخاص.

## أي لغات يمكن نشرها؟

نافذة النشر تختار طريقة البناء تلقائيًا حسب لغة نموذج البدء:

| اللغة | طريقة البناء |
|---|---|
| Python (Tkinter وQt وpygame وKivy وArcade) | PyInstaller |
| Visual Basic 6 (BASIC) | مفسّر BASIC المدمج + ملفات المشروع |
| لغات GUI Bridge (C وC++ وRust وC# وJava وGo ...) | بناء اللغة نفسها + مضيف الواجهة |
| RingQt | `ring2exe` |
| Flutter | `flutter build windows` |
| برنامج مبني مسبقًا | مجلد جاهز تختاره أنت |

## مثال: أي طريقة تناسبني؟

هذا مثال صغير يقترح طريقة النشر حسب نوع المشروع والجمهور:

```python run
def suggest(kind, audience):
    if kind == "website":
        return "Site > Publish... أو Site > Deploy to Cloud / Git / SSH..."
    if audience == "me":
        return "Project > Build EXE..."
    if audience == "usb":
        return "Build > Publish / Create Installer... مع خيار النسخة المحمولة (zip)"
    return "Build > Publish / Create Installer... (setup.exe)"

print(suggest("desktop", "me"))
print(suggest("desktop", "customers"))
print(suggest("desktop", "usb"))
print(suggest("website", "customers"))
```

```text output
Project > Build EXE...
Build > Publish / Create Installer... (setup.exe)
Build > Publish / Create Installer... مع خيار النسخة المحمولة (zip)
Site > Publish... أو Site > Deploy to Cloud / Git / SSH...
```

## أخطاء شائعة

- **إرسال مجلد المشروع للمستخدم:** يحتاج Python ومكتباتك. أرسل EXE أو setup.exe.
- **النشر دون تجربة على جهاز «نظيف»:** جرّب البرنامج المنشور على جهاز آخر (أو حساب مستخدم آخر) لا يوجد فيه Python.
- **نسيان رقم النسخة:** كل إصدار جديد يحتاج رقمًا أكبر (`1.0.0` ثم `1.0.1` ...)، وسنرى لماذا في الدروس القادمة.

## تمرين

### تمرين 1: أضف خيار الموبايل

أضف إلى الدالة `suggest` حالة `kind == "mobile"` ترجع `"Build > Mobile App"`، ثم اطبع الاقتراح لتطبيق موبايل.

```python exercise
def suggest(kind, audience):
    if kind == "website":
        return "Site > Publish..."
    return "Build > Publish / Create Installer..."

print(suggest("mobile", "customers"))
```

```python solution
def suggest(kind, audience):
    if kind == "mobile":
        return "Build > Mobile App"
    if kind == "website":
        return "Site > Publish..."
    return "Build > Publish / Create Installer..."

print(suggest("mobile", "customers"))
```

```text output
Build > Mobile App
```

## اختبر نفسك

```quiz
{"question": "لماذا لا ترسل مجلد المشروع إلى المستخدم؟", "choices": ["لأنه كبير", "لأنه يحتاج Python ومكتباتك مثبتة عنده", "لأنه ممنوع", "لا مانع"], "answer": 1, "explanation": "النشر يضع كل ما يحتاجه البرنامج في EXE أو برنامج تثبيت."}
```

```quiz
{"question": "ما اختصار نافذة النشر وإنشاء برنامج التثبيت؟", "choices": ["Ctrl+Alt+F5", "F5", "Ctrl+S", "Ctrl+Shift+X"], "answer": 0, "explanation": "Build > Publish / Create Installer... = Ctrl+Alt+F5."}
```

```quiz
{"question": "أي طريقة تعمل دون تثبيت من فلاشة؟", "choices": ["برنامج التثبيت فقط", "النسخة المحمولة (portable .zip)", "نشر الموقع", "لا توجد"], "answer": 1, "explanation": "النسخة المحمولة مجلد مضغوط يعمل كما هو."}
```

## الخلاصة

- النشر = تحويل المشروع إلى شيء يعمل عند المستخدم بضغطة مزدوجة.
- **Build EXE** للتجربة السريعة، و**Publish / Create Installer** للبرامج الحقيقية.
- النسخة المحمولة خيار في نافذة النشر، والمواقع من قائمة **Site**.
