# الدرس 5: المستودعات البعيدة و GitHub وطلبات السحب

**في هذا الدرس ستتعلم:**

- ما هو **المستودع البعيد** (Remote)، ومعنى `origin`.
- **الدفع** (Push) و**الجلب** (Fetch) و**السحب** (Pull) و**المزامنة** (Sync).
- ربط مشروعك بـ GitHub من **Git > Remotes...**، وتسجيل الدخول بـ GitHub CLI.
- **طلب السحب** (Pull Request): اقتراح دمج فرعك ومراجعته قبل الدمج.

## المكتبة المركزية

حتى الآن كان الألبوم (المستودع) على جهازك وحدك. لكن في فريق، يحتاج كل شخص إلى نسخة، ويحتاج الجميع إلى مكان **مشترك** يجمع العمل.
تخيّل **مكتبة مركزية**: كل موظف عنده نسخته في مكتبه، وفي آخر اليوم:

- يرسل صفحاته الجديدة إلى المكتبة: **Push** (دفع).
- يسأل المكتبة "ما الجديد؟" دون أن يغيّر أوراقه: **Fetch** (جلب).
- يأخذ الجديد ويضيفه إلى أوراقه: **Pull** (سحب) = Fetch ثم Merge.

المكتبة المركزية هي **المستودع البعيد**، ويكون عادةً على **GitHub** أو GitLab أو خادم شركتك. واسمه الافتراضي `origin`.

## ربط المشروع بـ GitHub

1. أنشئ مستودعًا فارغًا على موقع GitHub (زر **New repository**) وانسخ رابطه، مثل `https://github.com/you/shop.git`.
2. في RAD IDE: **Git > Remotes...** (Git > المستودعات البعيدة...). نافذة **Remotes** فيها جدول **Name** و **URL**.
3. أضف مستودعًا: الاسم `origin` والرابط الذي نسخته.
4. **Git > Push** (Git > دفع (Push)): أول مرة تسأل البيئة إلى أي مستودع بعيد، ثم تؤكد: "Push branch 'main' to origin?".

### تسجيل الدخول

GitHub يطلب إثبات هويتك عند الدفع:

- **Git > GitHub > Download GitHub CLI...** (تنزيل GitHub CLI...): تنزّل البيئة أداة `gh` الرسمية إلى مجلدها الخاص.
- **Git > GitHub > Sign in (gh auth login)...** (تسجيل الدخول): يفتح المتصفح لتأذن للجهاز. بعدها يعمل Push و Pull بلا كلمات مرور.

> 💡 البيئة لا تخزّن كلمة مرورك ولا تسجّل الدخول نيابةً عنك. وإن فشل الاتصال تشرح لك السبب بلغة بسيطة (لا إنترنت، أو لم تسجّل الدخول، أو لا صلاحية لك على المستودع).

### نسخ مستودع موجود (Clone)

لتبدأ العمل على مستودع موجود على GitHub: افتح **View > Terminal** واكتب:

```text
git clone https://github.com/someone/project.git
```

ثم **File > Open Folder...** واختر المجلد الذي أُنشئ. البيئة تتعرّف على نوع المشروع وعلى Git تلقائيًا.

## أوامر الشبكة

| الأمر | القائمة | ماذا يفعل |
|---|---|---|
| Fetch | **Git > Fetch** (جلب) | يعرف ما الجديد في البعيد، **دون** تغيير ملفاتك. تبويب **Branches** يُظهر "behind 2" |
| Pull | **Git > Pull** (سحب) | Fetch ثم دمج الجديد في فرعك |
| Pull (rebase) | **Git > Pull (rebase)** | Fetch ثم وضع إيداعاتك بعد الجديد (سجل مستقيم) |
| Push | **Git > Push** (دفع) | يرسل إيداعاتك إلى البعيد |
| Sync | **Git > Sync (pull, then push)** (مزامنة) | Pull ثم Push بضغطة واحدة |
| Force Push | **Git > Force Push (with lease)...** | يستبدل الفرع البعيد بفرعك. **خطر**، ونسخة "with lease" ترفض إن كان زميل قد دفع شيئًا لم تره |

وفي نافذة **Git Changes** زرّا **Pull** و **Push** أيضًا، مع شريط تقدم. البيئة **لا تتصل بالشبكة أبدًا إلا عندما تضغط أنت**.

## جرّبها: فريق من شخصين على جهاز واحد

بدل GitHub نستخدم مجلدًا على جهازك كـ"مكتبة مركزية" (مستودع `--bare` بلا ملفات عمل). الأوامر هي نفسها تمامًا مع GitHub:

```powershell run
$base = Join-Path $PWD 'team'
if (Test-Path $base) { Remove-Item $base -Recurse -Force }
New-Item -ItemType Directory $base | Out-Null
Set-Location $base
git init -q --bare -b main server.git           # the "GitHub" repository

# Sara starts the project and pushes it
git clone -q server.git sara 2>&1 | Out-Null
Set-Location sara
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10'
git add .
git commit -q -m 'Menu'
git push -q origin main                         # Git > Push
Set-Location ..

# Ali clones it (git clone ... then File > Open Folder)
git clone -q server.git ali
Set-Location ali
git config user.name 'Ali'
git config user.email 'ali@example.com'
git config core.autocrlf false
Add-Content menu.txt 'coffee=15'
git commit -q -am 'Add coffee'
git push -q                                     # Git > Push
Set-Location ..

# Sara gets Ali's work
Set-Location sara
git fetch -q                                    # Git > Fetch
Write-Output "after Fetch: $(git status --short --branch)"
git pull -q                                     # Git > Pull
Write-Output "after Pull:  $(git status --short --branch)"
Get-Content menu.txt
git log --format='%s | %an'
```

```text output
after Fetch: ## main...origin/main [behind 1]
after Pull:  ## main...origin/main
tea=10
coffee=15
Add coffee | Ali
Menu | Sara
```

بعد **Fetch** عرفت سارة أنها متأخرة إيداعًا واحدًا (`behind 1`) دون أن تتغير ملفاتها، وبعد **Pull** وصلها عمل علي.

## طلب السحب (Pull Request)

في الفرق لا يدمج أحد في `main` مباشرة. بل:

1. تعمل على فرع، مثل `feature/coffee`، وتدفعه (**Push**).
2. **Git > GitHub > Create Pull Request...** (إنشاء طلب سحب...). نافذة **Create Pull Request**:

| الخانة | المعنى |
|---|---|
| **Branch:** | فرعك |
| **Into (base):** | الفرع الذي تريد الدمج فيه، عادةً `main` |
| **Title:** | عنوان الطلب (تملؤه البيئة برسالة آخر إيداع) |
| **Description:** | اشرح ما غيّرته ولماذا |
| **Draft** | مسودة: "ما زلت أعمل عليه، لا تراجعوه بعد" |

إن لم يكن فرعك على GitHub بعد، تسألك البيئة: "Push it first?".

3. زملاؤك يراجعون الكود ويعلّقون على GitHub، ثم يدمجونه.
4. **Git > GitHub > Pull Requests and Issues** (طلبات السحب والمشكلات): تبويب **GitHub** في نافذة Git Changes يعرض طلبات السحب والمشكلات (Issues)، ويمكنك فتح طلب زميلك على جهازك (checkout) لتجرّبه قبل الموافقة.

## أخطاء شائعة

- **"rejected ... fetch first" عند Push:** زميلك دفع قبلك. اعمل **Pull** أولًا (وحل أي تعارض)، ثم **Push**. أو استخدم **Sync**.
- **Force Push لحل المشكلة السابقة:** يمحو عمل زميلك! لا تستخدمه على فرع مشترك.
- **"Authentication failed":** سجّل الدخول من **Git > GitHub > Sign in (gh auth login)...**.
- **العمل أسبوعًا بلا Pull:** تتراكم التعارضات. اسحب كل صباح.
- **دفع كلمات مرور أو ملفات `.env`:** راجع `.gitignore` قبل أول Push؛ ما يصل إلى GitHub العام يراه الجميع.

## تمرين

### تمرين 1: دورك في الفريق

أكمل السكربت: علي يضيف `juice=18` ويدفع، ثم سارة تسحب وتطبع القائمة.

```powershell exercise
$base = Join-Path $PWD 'team2'
if (Test-Path $base) { Remove-Item $base -Recurse -Force }
New-Item -ItemType Directory $base | Out-Null
Set-Location $base
git init -q --bare -b main server.git
git clone -q server.git sara 2>&1 | Out-Null
Set-Location sara
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10'
git add .
git commit -q -m 'Menu'
git push -q origin main
Set-Location ..
git clone -q server.git ali
# علي يضيف ويدفع، ثم سارة تسحب هنا
Get-Content (Join-Path $base 'sara\menu.txt')
```

```powershell solution
$base = Join-Path $PWD 'team2'
if (Test-Path $base) { Remove-Item $base -Recurse -Force }
New-Item -ItemType Directory $base | Out-Null
Set-Location $base
git init -q --bare -b main server.git
git clone -q server.git sara 2>&1 | Out-Null
Set-Location sara
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10'
git add .
git commit -q -m 'Menu'
git push -q origin main
Set-Location ..
git clone -q server.git ali
Set-Location ali
git config user.name 'Ali'
git config user.email 'ali@example.com'
git config core.autocrlf false
Add-Content menu.txt 'juice=18'
git commit -q -am 'Add juice'
git push -q
Set-Location (Join-Path $base 'sara')
git pull -q
Get-Content (Join-Path $base 'sara\menu.txt')
```

```text output
tea=10
juice=18
```

### مهمة عملية

1. أنشئ مستودعًا فارغًا على GitHub.
2. **Git > GitHub > Sign in (gh auth login)...** ثم **Git > Remotes...** وأضف `origin`.
3. **Git > Push**، وافتح صفحة المستودع لترى ملفاتك.
4. أنشئ فرعًا وعدّل شيئًا وادفعه، ثم **Git > GitHub > Create Pull Request...**.

## اختبر نفسك

```quiz
{"question": "ما الفرق بين Fetch و Pull؟", "choices": ["لا فرق", "Fetch يعرف ما الجديد دون تغيير ملفاتك، و Pull يجلبه ويدمجه في فرعك", "Fetch يرسل إيداعاتك", "Pull يحذف الفرع البعيد"], "answer": 1, "explanation": "Pull = Fetch + Merge."}
```

```quiz
{"question": "رفض GitHub دفعك لأن زميلك دفع قبلك. ما الصحيح؟", "choices": ["Force Push", "Pull ثم Push (أو Sync)", "حذف المستودع البعيد", "إعادة تثبيت Git"], "answer": 1, "explanation": "اجلب عمل زميلك وادمجه أولًا، ثم ادفع."}
```

```quiz
{"question": "ما هو طلب السحب (Pull Request)؟", "choices": ["أمر يسحب الملفات من GitHub", "اقتراح دمج فرعك في main ليُراجَع قبل الدمج", "طريقة لحذف الإيداعات", "اسم آخر لـ Fetch"], "answer": 1, "explanation": "تنشئه من Git > GitHub > Create Pull Request..."}
```

## الخلاصة

- المستودع البعيد (`origin`) مكتبة مركزية: **Git > Remotes...** للربط، و **Sign in (gh auth login)** للدخول.
- **Fetch** يعرف الجديد، و **Pull** يجلبه ويدمجه، و **Push** يرسل عملك، و **Sync** يفعل الاثنين. تجنّب **Force Push** على الفروع المشتركة.
- العمل الجماعي: فرع ← Push ← **Create Pull Request...** ← مراجعة ← دمج، وتبويب **GitHub** يعرض الطلبات والمشكلات.
