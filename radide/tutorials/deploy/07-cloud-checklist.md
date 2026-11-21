# الدرس 7: السحابة وDocker وقائمة مراجعة الإصدار

**في هذا الدرس ستتعلم:**

- النشر إلى خدمات السحابة: Vercel وNetlify وGitHub Pages وAzure وAWS وRender وRailway وخادم SSH.
- لماذا لا تسجّل البيئة الدخول إلى حساباتك بنفسها، وكيف تسجّل أنت.
- **Docker**: إنشاء `Dockerfile` و`compose.yaml` وحاوية التطوير لمشروعك.
- **قائمة مراجعة** قبل كل إصدار، وبرنامج صغير يتحقق منها.

## النشر إلى السحابة

**Site > Deploy to Cloud / Git / SSH...** (بالعربية: **الموقع > النشر إلى السحابة / Git / SSH...**)، وهو موجود أيضًا في **Tools**. أنشئ ملف تعريف واختر الهدف:

| الهدف | كيف يعمل |
|---|---|
| Vercel | أداة `vercel` |
| Netlify | أداة `netlify-cli` |
| GitHub Pages | `git push` إلى فرع `gh-pages` |
| Azure App Service | أداة `az` |
| AWS | Elastic Beanstalk بأداة `eb` / `aws`، أو موقع ثابت على S3 |
| Render / Railway | `git push`، أو رابط النشر في Render، أو `railway up` |
| خادم SSH | رفع بـ rsync أو SFTP، ثم أوامر على الخادم (مثل إعادة تشغيل الخدمة) |

**قواعد مهمة تتبعها البيئة:**

- **لا تسجّل الدخول إلى حساباتك أبدًا.** قبل النشر تشغّل أمر قراءة فقط (مثل `vercel whoami` أو `az account show` أو `aws sts get-caller-identity`)، وإذا فشل تتوقف برسالة واضحة: «Sign in first: run `<الأداة> login` in the Terminal». سجّل أنت الدخول في **الطرفية** مرة واحدة.
- **لكل هدف معاينة** (Preview / Dry Run): الأوامر التي ستعمل والملفات التي سترفع، دون أي تغيير.
- **الأوامر لا تنتظر إدخالًا**: إذا كان الدخول ناقصًا تفشل فورًا بدل أن تتجمد.
- **الأسرار** (كلمات المرور والرموز وروابط النشر) لا تُحفظ في `project.radproj`.

## Docker

**Docker** يضع موقعك وكل ما يحتاجه في **حاوية** (container) تعمل بنفس الطريقة على أي جهاز أو خادم. من **Tools > Docker** (أو **Site > Docker**):

| الأمر | ماذا يفعل |
|---|---|
| Generate Dockerfile / Compose / Dev Container... | يكتشف نوع مشروعك (Django وFlask وFastAPI وExpress وPHP وLaravel وASP.NET وSpring وRails وGo وموقع ثابت ...) ويكتب `Dockerfile` و`.dockerignore` و`compose.yaml` (مع قاعدة بيانات اختيارية) و`.devcontainer/devcontainer.json` |
| Docker Panel | الصور والحاويات والسجلات، وتشغيل وإيقاف |
| Build Image / Compose Up / Compose Down | البناء والتشغيل |
| Lint Dockerfile | فحص الملف (بفاحص مدمج، وhadolint يُنزّل عند الحاجة) |

البيئة **لا تثبّت Docker** (يحتاج صلاحيات المسؤول)، بل تستخدم `docker` أو `podman` إذا كان موجودًا. والبرامج المكتبية (Tkinter وQt وVB6 ...) لا تُوضع في حاويات؛ هذه للمواقع والخدمات. أمثلة جاهزة مجرّبة في `samples\Tests\Deploy`.

## قائمة مراجعة الإصدار

قبل أن تنشر أي إصدار، مرّ على هذه القائمة:

1. **رقم النسخة** أكبر من الإصدار السابق (`1.0.0` ثم `1.0.1` أو `1.1.0`).
2. **`app_id` لم يتغير** منذ أول إصدار.
3. **جرّبت البرنامج المنشور** على جهاز أو حساب آخر ليس فيه Python.
4. **الأيقونة والاسم والناشر** صحيحة.
5. **لا أسرار** في الكود ولا في `publish.json` (كلمات مرور، مفاتيح API).
6. **`version.json`** محدّث ومرفوع مع برنامج التثبيت إن كنت تستخدم التحديثات.
7. للمواقع: **Preview** أولًا، وبيانات الموقع الحية في **Exclude**.
8. **إيداع Git** ووسم (tag) بالنسخة: **Git > Tags**.

## مثال: فاحص قائمة المراجعة

هذا برنامج صغير يفحص إعدادات النشر قبل الإصدار ويطبع المشاكل:

```python run
import re

def check_release(cfg, previous_version, previous_app_id):
    problems = []

    def nums(v):
        return tuple(int(x) for x in re.findall(r"\d+", v))

    if nums(cfg["version"]) <= nums(previous_version):
        problems.append(f"النسخة {cfg['version']} ليست أكبر من {previous_version}")
    if cfg["app_id"] != previous_app_id:
        problems.append("تغيّر app_id: سيظهر البرنامج مرتين في قائمة البرامج المثبتة")
    if not cfg.get("publisher"):
        problems.append("اسم الناشر فارغ")
    if any(k in str(cfg).lower() for k in ("password", "secret")):
        problems.append("يبدو أن في الإعدادات كلمة مرور أو سرًا")
    return problems

cfg = {"app_name": "Hello Setup", "version": "1.0.0", "publisher": "",
       "app_id": "{AAAA}", "sign": {"password": "1234"}}
for p in check_release(cfg, previous_version="1.0.0", previous_app_id="{6E0A}"):
    print("-", p)
```

```text output
- النسخة 1.0.0 ليست أكبر من 1.0.0
- تغيّر app_id: سيظهر البرنامج مرتين في قائمة البرامج المثبتة
- اسم الناشر فارغ
- يبدو أن في الإعدادات كلمة مرور أو سرًا
```

## أخطاء شائعة

- **انتظار أن تسجّل البيئة الدخول إلى Vercel أو Azure:** سجّل أنت في الطرفية (`vercel login`، `az login` ...).
- **النشر دون Preview:** المعاينة تريك الأوامر والملفات قبل أي تغيير.
- **وضع برنامج مكتبي في Docker:** Docker للمواقع والخدمات. للبرامج المكتبية استخدم برنامج التثبيت.
- **تخطي قائمة المراجعة لأن «التعديل صغير»:** أغلب مشاكل الإصدارات تأتي من تعديلات صغيرة.

## تمرين

### تمرين 1: إصدار سليم

عدّل الإعدادات في المثال بحيث لا تظهر أي مشكلة: نسخة أكبر، ونفس `app_id` السابق، واسم ناشر، ودون كلمة مرور. اطبع «جاهز للإصدار» إذا كانت القائمة فارغة.

```python exercise
import re

def check_release(cfg, previous_version, previous_app_id):
    problems = []

    def nums(v):
        return tuple(int(x) for x in re.findall(r"\d+", v))

    if nums(cfg["version"]) <= nums(previous_version):
        problems.append("النسخة ليست أكبر")
    if cfg["app_id"] != previous_app_id:
        problems.append("تغيّر app_id")
    if not cfg.get("publisher"):
        problems.append("اسم الناشر فارغ")
    if any(k in str(cfg).lower() for k in ("password", "secret")):
        problems.append("سر في الإعدادات")
    return problems

cfg = {"version": "1.0.0", "publisher": "", "app_id": "{AAAA}", "sign": {"password": "1234"}}
print(check_release(cfg, "1.0.0", "{6E0A}") or "جاهز للإصدار")
```

```python solution
import re

def check_release(cfg, previous_version, previous_app_id):
    problems = []

    def nums(v):
        return tuple(int(x) for x in re.findall(r"\d+", v))

    if nums(cfg["version"]) <= nums(previous_version):
        problems.append("النسخة ليست أكبر")
    if cfg["app_id"] != previous_app_id:
        problems.append("تغيّر app_id")
    if not cfg.get("publisher"):
        problems.append("اسم الناشر فارغ")
    if any(k in str(cfg).lower() for k in ("password", "secret")):
        problems.append("سر في الإعدادات")
    return problems

cfg = {"version": "1.0.1", "publisher": "RAD IDE Samples", "app_id": "{6E0A}", "sign": {"enabled": False}}
print(check_release(cfg, "1.0.0", "{6E0A}") or "جاهز للإصدار")
```

```text output
جاهز للإصدار
```

## اختبر نفسك

```quiz
{"question": "هل تسجّل البيئة الدخول إلى حسابك في Vercel أو Azure؟", "choices": ["نعم تلقائيًا", "لا، تتحقق فقط وتطلب منك تسجيل الدخول في الطرفية", "فقط مع GitHub", "تطلب كلمة المرور وتحفظها في المشروع"], "answer": 1, "explanation": "أمر قراءة فقط للتحقق، ثم رسالة Sign in first إن لزم."}
```

```quiz
{"question": "لأي نوع من المشاريع يناسب Docker؟", "choices": ["البرامج المكتبية مثل Tkinter", "المواقع والخدمات مثل Django وExpress وPHP", "ألعاب pygame", "مشاريع VB6"], "answer": 1, "explanation": "البرامج المكتبية تُنشر ببرنامج تثبيت."}
```

```quiz
{"question": "أي بند ليس من قائمة مراجعة الإصدار؟", "choices": ["رفع رقم النسخة", "عدم تغيير app_id", "تجربة البرنامج على جهاز آخر", "تغيير اسم المشروع في كل إصدار"], "answer": 3, "explanation": "الاسم والمعرّف يبقيان ثابتين بين الإصدارات."}
```

## الخلاصة

- **Deploy to Cloud / Git / SSH...**: أهداف سحابية كثيرة، مع معاينة، ودون تسجيل دخول نيابة عنك.
- **Tools > Docker** يكتب ملفات Docker لمشاريع الويب ويديرها.
- قبل كل إصدار: النسخة، و`app_id`، والتجربة، والأسرار، و`version.json`، وGit.

## قاموس مصطلحات الدليل

| المصطلح | بالعربية |
|---|---|
| Deploy / Publish | نشر |
| Installer / Setup | برنامج تثبيت |
| Portable | محمول (دون تثبيت) |
| Silent install | تثبيت صامت |
| Code signing | توقيع الكود |
| Certificate | شهادة |
| Dry run / Preview | معاينة (تشغيل تجريبي) |
| Incremental upload | رفع تدريجي |
| Container | حاوية |
| Release | إصدار |
