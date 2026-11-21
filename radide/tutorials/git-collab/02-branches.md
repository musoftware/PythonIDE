# الدرس 2: الفروع والدمج

**في هذا الدرس ستتعلم:**

- ما هو **الفرع** (Branch)، ولماذا نجرّب الأفكار الجديدة في فرع مستقل.
- إنشاء فرع من **Git > New Branch...** والتبديل بين الفروع من **شريط الحالة**.
- **إدارة الفروع** (Manage Branches) وتبويب **Branches**.
- **دمج** فرع في الفرع الحالي (Merge)، ومتى نستخدم **إعادة التأسيس** (Rebase).

## نسخة المسودة

تكتب تقريرًا مهمًا، وتريد تجربة مقدمة جديدة دون أن تفسد النسخة السليمة. فتصوّر نسخة "مسودة" وتجرّب فيها براحتك. إن أعجبتك، تنقل المقدمة إلى النسخة الأصلية. وإن لم تعجبك، ترمي المسودة.
**الفرع** في Git مسودة كهذه، لكنه أذكى: لا ينسخ الملفات فعلًا، بل يتذكر من أين بدأت وما الذي غيّرته.

- الفرع الرئيسي اسمه عادةً `main` (أو `master` في المستودعات القديمة): النسخة السليمة.
- لكل ميزة أو إصلاح فرع خاص: `feature/login` أو `fix/tax`.
- عند الانتهاء **ندمج** (Merge) الفرع في `main`.

## إنشاء فرع في البيئة

> ⚠️ أودع إيداعًا واحدًا على الأقل أولًا؛ وإلا تظهر الرسالة "Make the first commit before creating branches."

1. **Git > New Branch...** (Git > فرع جديد...) أو `Ctrl+Alt+Shift+B`. تفتح نافذة **Create a new branch** (إنشاء فرع جديد):

| الخانة | الاسم العربي | ماذا تكتب |
|---|---|---|
| **Branch name:** | اسم الفرع | مثل `feature/login` |
| **Based on:** | مبني على | الفرع الذي تبدأ منه، عادةً `main` |
| **Checkout branch** | التبديل إلى فرع | علّمها لتنتقل إلى الفرع الجديد فورًا |

2. اضغط **OK**. اسم الفرع الجديد يظهر في **شريط الحالة** أسفل النافذة.
3. اعمل وأودع كالمعتاد: الإيداعات تذهب إلى الفرع الحالي فقط.

**التبديل بين الفروع:** انقر اسم الفرع في **شريط الحالة**، واختر فرعًا آخر أو **New Branch**، تمامًا كما في Visual Studio. الملفات المفتوحة تتغير لتطابق الفرع الذي انتقلت إليه.

> 💡 أودع أو خزّن تغييراتك مؤقتًا (الدرس 4) **قبل** التبديل، حتى لا تنتقل التعديلات غير المحفوظة معك إلى الفرع الآخر.

## إدارة الفروع

**Git > Manage Branches** (Git > إدارة الفروع) يفتح تبويب **Branches** (الفروع) في نافذة Git Changes:

- الفروع **المحلية** والفروع **البعيدة** (على GitHub مثلًا).
- لكل فرع: كم إيداعًا هو **متقدم** (ahead) أو **متأخر** (behind) عن نظيره البعيد.
- قائمة بالزر الأيمن: تبديل، دمج، إعادة تسمية، حذف، تتبّع فرع بعيد.

وتبويب **Graph** (الرسم البياني) يرسم الإيداعات كخطوط ملونة: كل فرع خط، والدمج نقطة يلتقي فيها خطان. افتحه أيضًا من **Git > View History (graph)** (`Ctrl+Alt+H`).

## الدمج

انتهيت من `feature/login` وتريد نقله إلى `main`:

1. انتقل إلى الفرع **الذي سيستقبل** التغييرات: `main` (من شريط الحالة).
2. **Git > Merge into current branch...** (دمج في الفرع الحالي...) واختر `feature/login`.
3. إن لم يعدّل الفرعان السطر نفسه، يتم الدمج تلقائيًا. وإن عدّلاه، يحدث **تعارض** (الدرس 3).

هذا السكربت يجرّب القصة كاملة: `main` فيه ملف، وفرع `feature/discount` يضيف ملفًا ويعدّل آخر، ثم ندمج:

```powershell run
$repo = Join-Path $PWD 'shop'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false

Set-Content price.txt '100'
git add .
git commit -q -m 'Price list'

git switch -q -c feature/discount        # New Branch + Checkout branch
Set-Content discount.txt '10%'
git add .
git commit -q -m 'Add discount'
Write-Output "on branch: $(git branch --show-current)"
Write-Output "files: $((Get-ChildItem -Name) -join ', ')"

git switch -q main                       # status bar: switch to main
Write-Output "on branch: $(git branch --show-current)"
Write-Output "files: $((Get-ChildItem -Name) -join ', ')"

git merge -q feature/discount            # Merge into current branch
Write-Output "after merge: $((Get-ChildItem -Name) -join ', ')"
Write-Output '--- branches'
git branch --format='%(refname:short)'
Write-Output '--- history of main'
git log --format='%s'
```

```text output
on branch: feature/discount
files: discount.txt, price.txt
on branch: main
files: price.txt
after merge: discount.txt, price.txt
--- branches
feature/discount
main
--- history of main
Add discount
Price list
```

لاحظ السحر: عند العودة إلى `main` **اختفى** `discount.txt` من المجلد (لأنه موجود في الفرع الآخر فقط)، ثم عاد بعد الدمج.

بعد الدمج يمكنك حذف الفرع من تبويب **Branches** (الزر الأيمن ثم Delete)، فقد أدّى مهمته.

## الدمج وإعادة التأسيس

| | الدمج (Merge) | إعادة التأسيس (Rebase) |
|---|---|---|
| القائمة | **Git > Merge into current branch...** | **Git > Rebase current branch onto...** |
| ماذا يفعل | يضيف إيداع دمج يجمع الفرعين | ينقل إيداعات فرعك لتبدأ بعد آخر إيداع في الفرع الآخر |
| السجل | يحفظ التاريخ كما حدث | سجل مستقيم أنظف |
| للمبتدئ | **ابدأ به**: آمن دائمًا | لفرعك المحلي فقط، لا لفرع شاركته مع غيرك |

إن حدث تعارض أثناء أي منهما يظهر شريط أعلى نافذة Git Changes فيه **Resolve Conflicts...** و **Continue** و **Abort** (الدرس القادم). وفي القائمة: **Git > Continue merge / rebase** و **Git > Abort merge / rebase**.

## أخطاء شائعة

- **العمل مباشرة على `main`:** اجعل لكل ميزة فرعًا، و `main` يبقى سليمًا دائمًا.
- **الدمج في الاتجاه الخطأ:** انتقل أولًا إلى الفرع **المستقبِل** ثم ادمج فيه.
- **التبديل وفي يدك تعديلات غير مودعة:** أودع أو خزّن مؤقتًا قبل التبديل.
- **أسماء فروع غامضة مثل `test2`:** استخدم `feature/...` و `fix/...` باسم يصف الهدف.
- **Rebase لفرع يعمل عليه زملاؤك:** يعيد كتابة التاريخ ويربكهم. استخدم Merge.

## تمرين

### تمرين 1: فرعان وميزتان

أنشئ فرع `feature/tax` يضيف ملف `tax.txt` (محتواه `14%`)، ثم عُد إلى `main` وادمجه، ثم اطبع أسماء الملفات.

```powershell exercise
$repo = Join-Path $PWD 'ex2'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
Set-Content price.txt '100'
git add .
git commit -q -m 'Price list'
# أنشئ الفرع وأودع فيه ثم ادمجه هنا
Write-Output ((Get-ChildItem -Name) -join ', ')
```

```powershell solution
$repo = Join-Path $PWD 'ex2'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
Set-Content price.txt '100'
git add .
git commit -q -m 'Price list'
git switch -q -c feature/tax
Set-Content tax.txt '14%'
git add .
git commit -q -m 'Add tax'
git switch -q main
git merge -q feature/tax
Write-Output ((Get-ChildItem -Name) -join ', ')
```

```text output
price.txt, tax.txt
```

### مهمة عملية

1. في مشروعك (مستودع من الدرس 1)، **Git > New Branch...** باسم `feature/about` مع **Checkout branch**.
2. أضف نافذة **About** وأودعها.
3. انقر اسم الفرع في شريط الحالة وعُد إلى `main`: لاحظ اختفاء النافذة من **Solution Explorer**.
4. **Git > Merge into current branch...** واختر `feature/about`، ثم افتح **Graph**.

## اختبر نفسك

```quiz
{"question": "لماذا نعمل على ميزة جديدة في فرع مستقل؟", "choices": ["لأن Git يمنع العمل على main", "لنجرّب دون أن نفسد النسخة السليمة، ثم ندمج عندما تكتمل", "لتسريع البرنامج", "لا فائدة من الفروع"], "answer": 1, "explanation": "الفرع مسودة آمنة؛ main يبقى سليمًا."}
```

```quiz
{"question": "تريد دمج `feature/login` في `main`. أين يجب أن تكون قبل Merge into current branch؟", "choices": ["على feature/login", "على main", "لا يهم", "على أي فرع ثالث"], "answer": 1, "explanation": "الدمج يكون في الفرع الحالي، فانتقل إلى الفرع المستقبِل أولًا."}
```

```quiz
{"question": "أين تبدّل بين الفروع بسرعة في RAD IDE؟", "choices": ["بالنقر على اسم الفرع في شريط الحالة", "من Help > About", "بإعادة تشغيل البيئة", "من نافذة Properties"], "answer": 0, "explanation": "اسم الفرع في شريط الحالة قائمة للتبديل وإنشاء فرع جديد."}
```

## الخلاصة

- الفرع مسودة آمنة: **Git > New Branch...** (`Ctrl+Alt+Shift+B`) مع **Checkout branch**.
- التبديل من **شريط الحالة**، وإدارة الفروع من **Git > Manage Branches** وتبويب **Branches**، والرسم من **Graph**.
- للدمج: انتقل إلى الفرع المستقبِل ثم **Git > Merge into current branch...**. ابدأ بـ Merge، واترك Rebase لفروعك المحلية.
