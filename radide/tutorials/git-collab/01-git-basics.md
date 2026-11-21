# الدرس 1: أول مستودع: التغييرات والتجهيز والإيداع

**في هذا الدرس ستتعلم:**

- ما هو **Git**، وما معنى **مستودع** (Repository) و**إيداع** (Commit).
- نافذة **Git Changes** (تغييرات Git) في RAD IDE: تهيئة مستودع، وتجهيز الملفات، وكتابة رسالة الإيداع.
- قراءة حالة الملفات: جديد، ومعدّل، ومحذوف، ورؤية **الفروق** (Diff) قبل الإيداع.
- ملف `.gitignore` وإعداد اسمك وبريدك.

## ألبوم الصور

تخيّل أنك تلتقط **صورة** لمشروعك كلما أنجزت خطوة: "أضفت نافذة الدخول"، "أصلحت خطأ الضريبة". كل صورة عليها تاريخ واسم من التقطها وجملة تصفها.
لو أفسدت شيئًا غدًا، تفتح الألبوم وتعود إلى صورة الأمس.

- **Git** هو آلة التصوير والألبوم معًا.
- **المستودع** (Repository) هو الألبوم: مجلد مخفي اسمه `.git` داخل مجلد مشروعك.
- **الإيداع** (Commit) هو صورة واحدة: لقطة لكل ملفات المشروع في لحظة، مع رسالة.
- **التجهيز** (Stage) هو اختيار ما سيظهر في الصورة القادمة: قد تعدّل خمسة ملفات وتودع ثلاثة منها فقط.

## قبل أن تبدأ

1. يجب أن يكون **Git for Windows** مثبتًا (البيئة تبحث عنه في `C:\Program Files\Git`). إن لم يكن، نزّله من موقع git-scm.com.
2. عرّف نفسك مرة واحدة: **Git > Git Settings...** (Git > إعدادات Git...) واكتب الاسم والبريد. هذا ما سيظهر على كل إيداع.

## نافذة Git Changes

افتحها من **Git > Git Changes** (Git > تغييرات Git) أو **View > Git Changes** أو `Ctrl+Alt+G`.

| الجزء | الاسم العربي | المعنى |
|---|---|---|
| زر **Init Repository** | تهيئة مستودع | يظهر إن لم يكن المجلد مستودعًا بعد: ينفّذ `git init` في مجلد المشروع |
| شجرة **Changes** | التغييرات | الملفات المعدّلة التي **لم تُجهّز** بعد |
| شجرة **Staged Changes** | التغييرات المجهّزة | الملفات التي ستدخل الإيداع القادم |
| **Stage** / **Unstage** / **Stage All** | تجهيز / إلغاء التجهيز / تجهيز الكل | نقل الملفات بين الشجرتين |
| مربع **Commit message (Ctrl+Enter to commit)** | رسالة الإيداع | جملة تصف ما فعلته |
| زر **Commit** | إيداع | يلتقط الصورة |
| خانة **Amend** | تعديل | يستبدل آخر إيداع بدل إنشاء إيداع جديد (لتصحيح رسالة نسيت فيها شيئًا) |
| تبويب **Diff** | الفروق | ما تغيّر في الملف المحدد: الأسطر المحذوفة بالأحمر والمضافة بالأخضر |
| تبويب **History** | السجل | الإيداعات السابقة |

وحرف بجوار كل ملف يخبرك بحالته:

| الحرف | المعنى |
|---|---|
| `?` أو `U` | ملف جديد لا يعرفه Git بعد (Untracked) |
| `M` | ملف معدّل (Modified) |
| `A` | ملف أُضيف وجُهّز (Added) |
| `D` | ملف محذوف (Deleted) |

> 💡 الملفات المتغيرة تتلوّن أيضًا في **Solution Explorer**، واسم الفرع الحالي يظهر في **شريط الحالة** أسفل النافذة.

## خطوة بخطوة في البيئة

1. أنشئ مشروعًا جديدًا (**File > New Project...**) أو افتح مجلدًا.
2. `Ctrl+Alt+G` ثم **Init Repository**. أصبح المشروع مستودعًا، وكل ملفاته في **Changes**.
3. اضغط **Stage All**: انتقلت الملفات إلى **Staged Changes**.
4. اكتب في مربع الرسالة: `First version`، ثم **Commit** (أو `Ctrl+Enter`).
5. عدّل سطرًا في `Form1` واحفظ: الملف يظهر في **Changes** بحرف `M`. انقره لترى الفرق في تبويب **Diff**.
6. **Stage** ثم رسالة ثم **Commit**. افتح تبويب **History**: إيداعان.

**Git > Commit All...** (إيداع الكل...) يجهّز كل شيء ويودع في خطوة واحدة.

## جرّبها بالأوامر

كل ما تفعله النافذة هو أوامر `git` حقيقية. هذا السكربت يفعل الخطوات نفسها في مجلد تجريبي اسمه `my-app`. اضغط «جرّبه» ثم شغّله، أو الصق أوامره واحدًا واحدًا في **View > Terminal** (`` Ctrl+` ``):

```powershell run
$repo = Join-Path $PWD 'my-app'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo

git init -q -b main                      # Init Repository
git config user.name 'Sara'              # Git Settings: name
git config user.email 'sara@example.com' # Git Settings: email
git config core.autocrlf false

Set-Content hello.txt 'Hello'
Set-Content price.txt '100'
Write-Output '--- status (before Stage)'
git status --short

git add hello.txt price.txt              # Stage All
git commit -q -m 'First version'         # Commit
Write-Output '--- after the first commit'
git status --short
Set-Content price.txt '120'              # edit a file and save
Write-Output '--- price.txt edited'
git status --short
git add price.txt
git commit -q -m 'New price'
Write-Output '--- History'
git log --format='%s by %an'
```

```text output
--- status (before Stage)
?? hello.txt
?? price.txt
--- after the first commit
--- price.txt edited
 M price.txt
--- History
New price by Sara
First version by Sara
```

لاحظ: بعد الإيداع الأول لا تظهر أي ملفات (لا تغييرات)، وبعد تعديل `price.txt` يظهر بحرف `M`. السجل يعرض **الأحدث أولًا**.

## ملف ‎.gitignore: ما لا يدخل الألبوم

بعض الملفات لا يجب أن تدخل المستودع: مجلدات البناء (`build/` و `dist/`)، وبيئة Python (`.venv/`)، وكلمات المرور. اكتب أسماءها في ملف `.gitignore`.
**Git > Edit .gitignore...** (Git > تحرير ‎.gitignore...) يفتح محررًا فيه **قوالب جاهزة** لكل لغة: علّم القالب واضغط **Add checked templates →**. والبيئة تنشئ ملفًا مبدئيًا عند **Init Repository**.

```powershell run
$repo = Join-Path $PWD 'ignore-demo'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
New-Item -ItemType Directory build | Out-Null
Set-Content build\app.exe 'binary'
Set-Content main.py 'print(1)'
Write-Output '--- without .gitignore'
git status --short --untracked-files=all
Set-Content .gitignore 'build/'
Write-Output '--- with .gitignore'
git status --short --untracked-files=all
```

```text output
--- without .gitignore
?? build/app.exe
?? main.py
--- with .gitignore
?? .gitignore
?? main.py
```

## رسالة إيداع جيدة

| سيئة | جيدة |
|---|---|
| `update` | `Fix tax rounding in invoice total` |
| `asdf` | `Add login form with password check` |
| `changes` | `Rename txtN to txtName` |

القاعدة: جملة قصيرة تقول **ماذا** فعلت، بحيث تفهمها بعد شهر.

## أخطاء شائعة

- **"Not a git repository"** في النافذة: المجلد ليس مستودعًا بعد. اضغط **Init Repository**.
- **الإيداع يفشل ويطلب الاسم والبريد:** املأهما في **Git > Git Settings...**.
- **نسيت تجهيز ملف:** الإيداع يأخذ **Staged Changes** فقط. راجع الشجرتين قبل **Commit**.
- **إيداع كلمات مرور أو مجلد `build`:** أضفها إلى `.gitignore` **قبل** أول إيداع.
- **إيداع كل شيء في إيداع واحد ضخم بعد أسبوع:** أودع بعد كل خطوة صغيرة مكتملة.

## تمرين

### تمرين 1: صورتان في الألبوم

عدّل السكربت حتى ينشئ ملف `notes.txt` ويودعه برسالة `Add notes`، ثم يعدّله ويودعه برسالة `Update notes`، ثم يطبع السجل.

```powershell exercise
$repo = Join-Path $PWD 'ex1'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
# اكتب أوامرك هنا
git log --format='%s'
```

```powershell solution
$repo = Join-Path $PWD 'ex1'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
Set-Content notes.txt 'first'
git add notes.txt
git commit -q -m 'Add notes'
Set-Content notes.txt 'second'
git add notes.txt
git commit -q -m 'Update notes'
git log --format='%s'
```

```text output
Update notes
Add notes
```

### مهمة عملية

1. افتح أي مشروع من مشروعاتك، و `Ctrl+Alt+G`، ثم **Init Repository**.
2. افتح **Git > Edit .gitignore...** وأضف قالب لغتك.
3. **Stage All** ثم أودع برسالة `First version`.
4. عدّل ملفًا، وانقره في **Changes** لترى **Diff**، ثم أودعه.

## اختبر نفسك

```quiz
{"question": "ما هو الإيداع (Commit)؟", "choices": ["رفع المشروع إلى الإنترنت", "لقطة محفوظة لملفات المشروع في لحظة معيّنة مع رسالة", "حذف الملفات القديمة", "تشغيل البرنامج"], "answer": 1, "explanation": "الإيداع صورة في ألبوم المشروع يمكنك العودة إليها."}
```

```quiz
{"question": "عدّلت ثلاثة ملفات وجهّزت (Stage) اثنين منها فقط ثم ضغطت Commit. ماذا يدخل الإيداع؟", "choices": ["الملفات الثلاثة", "الملفان المجهّزان فقط", "لا شيء", "آخر ملف حفظته"], "answer": 1, "explanation": "الإيداع يأخذ Staged Changes فقط."}
```

```quiz
{"question": "ماذا يعني الحرف `M` بجوار ملف في نافذة Git Changes؟", "choices": ["ملف جديد", "ملف معدّل منذ آخر إيداع", "ملف محذوف", "ملف مدموج"], "answer": 1, "explanation": "M = Modified."}
```

## الخلاصة

- Git ألبوم صور للمشروع: المستودع هو الألبوم، والإيداع صورة، والتجهيز اختيار ما يدخل الصورة.
- **Git Changes** (`Ctrl+Alt+G`): **Init Repository**، ثم **Stage** / **Stage All**، ثم رسالة و **Commit**، و **Diff** و **History** للمراجعة.
- **Git > Git Settings...** للاسم والبريد، و **Git > Edit .gitignore...** لما لا يدخل المستودع.
