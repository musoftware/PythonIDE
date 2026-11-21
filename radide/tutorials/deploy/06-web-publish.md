# الدرس 6: نشر موقع ويب: FTP وSFTP والمجلدات

**في هذا الدرس ستتعلم:**

- إنشاء **ملف تعريف نشر** (Publish profile) لموقعك.
- طرق النشر: FTP وFTPS وSFTP ومجلد محلي أو مشاركة شبكة.
- **المعاينة** (dry run) قبل الرفع، والرفع **التدريجي** (الملفات المتغيرة فقط).
- **الاستثناءات**: ملفات لا تُرفع أبدًا، مثل قاعدة البيانات الحية.
- أين تُحفظ كلمات المرور.

## فتح نافذة النشر

افتح مشروع موقع (PHP أو HTML أو غيره)، ثم **Site > Publish...** (`Ctrl+Alt+P`، بالعربية: **الموقع > نشر...**). الفكرة مثل **Publish** في WebMatrix.

## ملف تعريف النشر

في أعلى النافذة قائمة ملفات التعريف وأزرار **New** و**Duplicate** و**Delete**. ملف التعريف يحفظ «إلى أين وكيف»، فيمكنك مثلًا أن تصنع واحدًا لخادم التجربة وآخر للموقع الحقيقي.

| الحقل | معناه |
|---|---|
| **Profile name** | اسم ملف التعريف، مثل «الخادم الحقيقي» |
| **Method** | `FTP`، أو `FTPS (explicit TLS)`، أو `SFTP (SSH)`، أو `Local folder / network share` |
| الخادم والمنفذ والمستخدم وكلمة المرور | بيانات الدخول من شركة الاستضافة (المنفذ الافتراضي: 21 لـ FTP، و22 لـ SFTP) |
| المجلد البعيد | مكان الموقع على الخادم، مثل `/public_html` |
| **Destination URL** | عنوان الموقع، ليفتحه زر **Open site** بعد النشر |
| **Local folder** | المجلد الذي يُرفع (جذر الموقع) |
| **Exclude** | أنماط ملفات لا تُرفع (انظر أدناه) |
| **Passive mode** / **Verify the server certificate** | خيارات FTP وFTPS |
| **Delete remote files that were removed locally** | احذف من الخادم ما حذفته من جهازك |

> **أي طريقة أختار؟** **SFTP** إذا كانت الاستضافة تدعمها (مشفرة بالكامل عبر SSH، وتحتاج حزمة `paramiko`). ثم **FTPS**. أما **FTP** العادي فيرسل كلمة المرور دون تشفير، فاستخدمه فقط إذا لم يوجد غيره. و**Local folder** للنشر إلى مجلد على جهازك أو على مشاركة شبكة في الشركة.

## اختبر، ثم عاين، ثم انشر

- **Test Connection**: يتأكد من بيانات الدخول دون رفع أي شيء.
- **Preview** (أو **Site > Publish Preview (dry run)...**): يعرض **ما سيحدث**: الملفات التي ستُرفع (الجديدة والمتغيرة)، وما سيُحذف، والحجم. **لا يتغير شيء** على الخادم.
- **Publish**: الرفع الفعلي مع شريط التقدم.

## الرفع التدريجي

البيئة تتذكر ما رفعته في المرة السابقة (حجم كل ملف ووقت تعديله)، فلا ترفع في المرة التالية إلا **الجديد والمتغير**. وإذا تغير وقت التعديل فقط، تقرر **بصمة المحتوى** (hash) هل تغيّر الملف فعلًا. لذلك نشر تعديل صغير على موقع كبير يأخذ ثواني.

- **Upload all files**: يتجاهل الذاكرة ويرفع كل شيء.
- **Forget publish history**: يمسح الذاكرة، فيُعامل كل شيء كجديد في المرة القادمة.

هذا مثال يحسب خطة الرفع من «ذاكرة» المرة السابقة وحالة الملفات الآن:

```python run
published = {"index.php": 1200, "style.css": 800, "old.html": 300}   # الحجم عند آخر نشر
local = {"index.php": 1200, "style.css": 950, "about.php": 400}      # الحجم الآن

new = sorted(f for f in local if f not in published)
changed = sorted(f for f in local if f in published and local[f] != published[f])
removed = sorted(f for f in published if f not in local)
same = sorted(f for f in local if f in published and local[f] == published[f])

print("جديد:", new)
print("متغير:", changed)
print("محذوف محليًا:", removed)
print("بلا تغيير (لن يُرفع):", same)
print("سيُرفع:", len(new) + len(changed), "ملف")
```

```text output
جديد: ['about.php']
متغير: ['style.css']
محذوف محليًا: ['old.html']
بلا تغيير (لن يُرفع): ['index.php']
سيُرفع: 2 ملف
```

(المثال يقارن الحجم فقط للتبسيط. البيئة تقارن الحجم ووقت التعديل، ثم البصمة عند الحاجة.)

## الاستثناءات: ما لا يُرفع أبدًا

في خانة **Exclude** أنماط (سطر لكل نمط). القائمة الافتراضية تحتوي مثلًا: `.git` و`.radide` و`project.radproj` و`*.radsln` و`__pycache__` و`*.pyc` و`.vscode` و`*.bak` و`*.tmp`، وكذلك **بيانات الموقع الحية** (قاعدة البيانات والجلسات) حتى **لا تستبدل قاعدة البيانات الحقيقية على الخادم** بنسخة التجربة من جهازك.

القاعدة: النمط الذي **فيه** `/` يطابق المسار كله، والنمط الذي **ليس فيه** `/` يطابق أي جزء من المسار. هذا مثال بنفس القاعدة:

```python run
import fnmatch

def is_excluded(rel, patterns):
    parts = rel.split("/")
    for pat in patterns:
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/"):
                return True
        elif any(fnmatch.fnmatch(part, pat) for part in parts):
            return True
    return False

patterns = [".git", "*.bak", "data/*.sqlite", "project.radproj"]
files = ["index.php", "css/site.css", ".git/config", "img/logo.bak",
         "data/app.sqlite", "data/readme.txt", "project.radproj"]
for f in files:
    print("لن يُرفع" if is_excluded(f, patterns) else "يُرفع  ", f)
```

```text output
يُرفع   index.php
يُرفع   css/site.css
لن يُرفع .git/config
لن يُرفع img/logo.bak
لن يُرفع data/app.sqlite
يُرفع   data/readme.txt
لن يُرفع project.radproj
```

## أين تُحفظ كلمات المرور؟

ملفات التعريف تُحفظ في `project.radproj` تحت `"publish"` **دون كلمات المرور**. كلمة المرور إما تُحفظ في إعدادات المستخدم على جهازك (خيار **Save password**؛ مموّهة وليست مشفرة تشفيرًا قويًا)، أو تُسأل عنها في كل مرة. وزر **Forget** يحذف المحفوظة.

## أخطاء شائعة

- **رفع قاعدة بيانات التجربة فوق الحقيقية:** تأكد أن ملفات البيانات في **Exclude**. والقائمة الافتراضية تحميك من أشهرها.
- **النشر دون Preview:** خصوصًا مع **Delete remote files that were removed locally**. عاين أولًا دائمًا.
- **FTP عادي على شبكة عامة:** كلمة المرور تمر دون تشفير. استخدم SFTP أو FTPS.
- **المجلد البعيد الخطأ:** الموقع يُرفع لكنه لا يظهر. تأكد من مجلد الجذر لدى الاستضافة (`public_html` أو `www` أو `htdocs`).

## تمرين

### تمرين 1: استثناء مجلد السجلات

أضف نمطًا يستثني كل ملفات المجلد `logs` (مثل `logs/today.log`)، ونمطًا يستثني كل ملفات `.env` أينما كانت، ثم اطبع الملفات التي **ستُرفع** فقط.

```python exercise
import fnmatch

def is_excluded(rel, patterns):
    parts = rel.split("/")
    for pat in patterns:
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/"):
                return True
        elif any(fnmatch.fnmatch(part, pat) for part in parts):
            return True
    return False

patterns = [".git"]
files = ["index.php", "logs/today.log", "config/.env", ".env", "about.php"]
# أضف الأنماط واطبع ما سيُرفع
```

```python solution
import fnmatch

def is_excluded(rel, patterns):
    parts = rel.split("/")
    for pat in patterns:
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/"):
                return True
        elif any(fnmatch.fnmatch(part, pat) for part in parts):
            return True
    return False

patterns = [".git", "logs/*", ".env"]
files = ["index.php", "logs/today.log", "config/.env", ".env", "about.php"]
for f in files:
    if not is_excluded(f, patterns):
        print(f)
```

```text output
index.php
about.php
```

## اختبر نفسك

```quiz
{"question": "ماذا يفعل زر Preview في نافذة نشر الموقع؟", "choices": ["يرفع كل الملفات", "يعرض ما سيُرفع ويُحذف دون تغيير أي شيء", "يحذف الموقع", "يفتح المتصفح فقط"], "answer": 1, "explanation": "المعاينة (dry run) لا تغيّر شيئًا على الخادم."}
```

```quiz
{"question": "أي طريقة نشر أكثر أمانًا؟", "choices": ["FTP", "SFTP (SSH)", "كلها متساوية", "إرسال الملفات بالبريد"], "answer": 1, "explanation": "SFTP مشفرة بالكامل، وFTP العادي يرسل كلمة المرور دون تشفير."}
```

```quiz
{"question": "لماذا تستثني القائمة الافتراضية بيانات الموقع الحية؟", "choices": ["لتسريع الرفع فقط", "حتى لا تُستبدل قاعدة البيانات الحقيقية على الخادم بنسخة التجربة", "لأنها ملفات كبيرة", "لا تستثنيها"], "answer": 1, "explanation": "البيانات الحية على الخادم أهم من نسخة التجربة على جهازك."}
```

## الخلاصة

- **Site > Publish...** (`Ctrl+Alt+P`): ملفات تعريف بـ FTP أو FTPS أو SFTP أو مجلد.
- **Test Connection** ثم **Preview** ثم **Publish**.
- الرفع تدريجي: الجديد والمتغير فقط.
- **Exclude** يحمي ملفات لا يجب رفعها، وكلمات المرور ليست في ملف المشروع.
