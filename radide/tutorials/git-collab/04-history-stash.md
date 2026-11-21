# الدرس 4: السجل و Blame والتخزين المؤقت والتراجع

**في هذا الدرس ستتعلم:**

- تصفّح **سجل** المشروع ورسمه البياني: **Git > View History (graph)**.
- **Blame**: من كتب هذا السطر، ومتى، ولماذا؟
- **مقارنة** ملف بإيداع قديم.
- **التخزين المؤقت** (Stash): ضع عملك جانبًا لحظة وعُد إليه.
- أدوات التراجع: **Amend** و **Undo last commit** و **Revert** و **Reset**.

## الصندوق الأسود

الطائرات تحمل **صندوقًا أسود** يسجل كل شيء. عندما يحدث خلل، يفتحه المحققون ويعرفون ماذا حدث، ومتى، ومن ضغط أي زر.
سجل Git هو الصندوق الأسود لمشروعك: كل إيداع بتاريخه وكاتبه ورسالته وما تغيّر فيه. ومع **Blame** تعرف قصة كل سطر.

## السجل والرسم البياني

**Git > View History (graph)** (Git > عرض السجل (رسم بياني)) أو `Ctrl+Alt+H` يفتح تبويب **Graph**:

- كل صف إيداع: الرسالة، والكاتب، والتاريخ، والمعرّف المختصر (مثل `a1b2c3d4`).
- الخطوط الملونة على اليسار هي الفروع، وخانة **All branches** تُظهر كل الفروع لا الحالي فقط.
- **انقر إيداعًا** لترى ملفاته وفروقه.

**بالزر الأيمن على إيداع** تظهر قائمة قوية:

| الأمر | ماذا يفعل |
|---|---|
| **View commit details** | تفاصيل الإيداع وملفاته |
| **Compare with working copy** | الفرق بين ذلك الإيداع وملفاتك الآن |
| **New branch from here...** | فرع يبدأ من هذا الإيداع |
| **New tag here...** | وسم (مثل `v1.0`) على هذا الإيداع |
| **Cherry-pick into the current branch** | انسخ هذا الإيداع وحده إلى فرعك |
| **Revert (new commit that undoes it)** | إيداع جديد يلغي أثر هذا الإيداع |
| **Reset current branch to here** | أعِد الفرع إلى هنا: **Keep changes (--mixed)** أو **Keep changes staged (--soft)** أو **Delete changes (--hard)** |
| **Copy commit id** | انسخ المعرّف |

## Blame: قصة كل سطر

- **Git > Blame current file** (Blame للملف الحالي (من كتب كل سطر)): نافذة فيها بجوار كل سطر الكاتب والتاريخ والإيداع.
- **Git > Toggle inline blame in the editor** (تبديل Blame المضمّن في المحرر): يكتب في نهاية السطر الذي عليه المؤشر من عدّله ومتى، بخط باهت، كما في VS Code.

الاسم "Blame" (لوم) مخيف، لكن استخدامه الحقيقي **الفهم**: "لماذا كُتب هذا الشرط؟" فتقرأ رسالة الإيداع الذي أضافه.

## المقارنة

- **Git > Compare current file with commit...** (مقارنة الملف الحالي بإيداع...): اختر إيداعًا فترى الفروق جنبًا إلى جنب.
- **Tools > Compare (Diff) > Compare Current File with Git HEAD**: الفرق بين ملفك وآخر إيداع.

## السجل بالأوامر

```powershell run
$repo = Join-Path $PWD 'history-demo'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config core.autocrlf false
git config user.name 'Sara'
git config user.email 'sara@example.com'
Set-Content prices.txt 'tea=10', 'coffee=12'
git add .
git commit -q -m 'Price list'
git config user.name 'Ali'
Set-Content prices.txt 'tea=10', 'coffee=15'
git commit -q -am 'Raise coffee price'
git tag v1.0                              # New tag here...

Write-Output '--- View History'
git log --format='%s | %an'
Write-Output '--- Blame (who wrote each line)'
git blame --line-porcelain prices.txt | Select-String '^author ' | ForEach-Object { $_.Line.Substring(7) }
Write-Output '--- Compare with the first commit'
git diff HEAD~1 --unified=0 --no-color prices.txt | Where-Object { $_ -match '^[-+][a-z]' }
Write-Output '--- Tags'
git tag
```

```text output
--- View History
Raise coffee price | Ali
Price list | Sara
--- Blame (who wrote each line)
Sara
Ali
--- Compare with the first commit
-coffee=12
+coffee=15
--- Tags
v1.0
```

السطر الأول كتبته سارة، والثاني آخر من عدّله علي. و `-` السطر القديم، و `+` الجديد.

## التخزين المؤقت (Stash)

أنت في منتصف ميزة، والمدير يقول: "أصلح هذا الخطأ العاجل الآن!". عملك غير مكتمل ولا تريد إيداعه.
**Stash** درج تضع فيه أوراقك مؤقتًا: المجلد يعود نظيفًا، وتصلح الخطأ، ثم تُخرج أوراقك وتكمل.

- **Git > Stash All...** (تخزين الكل مؤقتًا...): يحفظ كل التغييرات (حتى الملفات الجديدة) وينظف المجلد. تكتب رسالة تصف ما خزّنته.
- **Git > Stashes** (المخزّنات المؤقتة): تبويب **Stashes** فيه القائمة؛ لكل عنصر **Apply** (استرجاع مع الإبقاء عليه) و **Pop** (استرجاع وحذف) و **Drop** (حذف).

```powershell run
$repo = Join-Path $PWD 'stash-demo'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config core.autocrlf false
git config user.name 'Sara'
git config user.email 'sara@example.com'
Set-Content app.txt 'version 1'
git add .
git commit -q -m 'First version'

Add-Content app.txt 'half-done feature'
Write-Output "working: $((git status --short).Trim())"
git stash push -q -m 'login form, not finished'     # Stash All...
Write-Output "after Stash: [$(git status --short)]"
git stash list --format='%gs'

Set-Content bug.txt 'fixed'                         # the urgent fix
git add .
git commit -q -m 'Urgent fix'

git stash pop -q                                    # Stashes > Pop
Write-Output "after Pop: $((git status --short).Trim())"
Get-Content app.txt
```

```text output
working: M app.txt
after Stash: []
On main: login form, not finished
after Pop: M app.txt
version 1
half-done feature
```

## أدوات التراجع

| الموقف | الأداة | القائمة |
|---|---|---|
| نسيت ملفًا أو أخطأت في رسالة **آخر** إيداع | Amend | **Git > Amend last commit** أو خانة **Amend** بجوار Commit |
| أودعت مبكرًا وتريد إلغاء الإيداع مع **الإبقاء** على التعديلات | Undo last commit | **Git > Undo last commit (keep changes)** |
| إيداع قديم سبّب مشكلة وقد شاركته مع الفريق | Revert | الزر الأيمن في Graph: **Revert (new commit that undoes it)** |
| تريد إعادة الفرع إلى إيداع سابق (محليًا) | Reset | الزر الأيمن: **Reset current branch to here** |

```powershell run
$repo = Join-Path $PWD 'undo-demo'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config core.autocrlf false
git config user.name 'Sara'
git config user.email 'sara@example.com'
Set-Content a.txt 'A'
git add .
git commit -q -m 'Add A'
Set-Content b.txt 'B'
git add .
git commit -q -m 'Add Bb'                           # typo in the message!
git commit -q --amend -m 'Add B'                    # Amend last commit
Write-Output '--- after Amend'
git log --format='%s'

Set-Content c.txt 'C'
git add .
git commit -q -m 'Add C (too early)'
git reset -q --soft HEAD~1                          # Undo last commit (keep changes)
Write-Output '--- after Undo last commit'
git log --format='%s'
git status --short

git commit -q -m 'Add C'
git revert --no-edit HEAD~1 | Out-Null              # Revert 'Add B'
Write-Output '--- after Revert of Add B'
git log --format='%s'
Write-Output "files: $((Get-ChildItem -Name) -join ', ')"
```

```text output
--- after Amend
Add B
Add A
--- after Undo last commit
Add B
Add A
A  c.txt
--- after Revert of Add B
Revert "Add B"
Add C
Add B
Add A
files: a.txt, c.txt
```

لاحظ الفرق: **Undo** حذف الإيداع من السجل وأبقى `c.txt` مجهّزًا (`A`)، أما **Revert** فلم يحذف شيئًا من التاريخ، بل أضاف إيداعًا جديدًا يلغي أثر `Add B`. لذلك **Revert** آمن لما شاركته مع الآخرين.

> ⚠️ **Reset > Delete changes (--hard)** يحذف التعديلات غير المودعة نهائيًا. خزّنها بـ Stash أولًا إن كنت مترددًا.

## أخطاء شائعة

- **Amend لإيداع دفعته (Push) إلى GitHub:** يعيد كتابة تاريخ يملكه زملاؤك. البيئة تحذّرك؛ استخدم إيداعًا جديدًا أو Revert.
- **Reset --hard للتجربة:** يمحو عملك. ابدأ بـ `--mixed` أو Stash.
- **نسيان ما في Stash:** المخزّنات تتراكم. اكتب رسالة واضحة وراجع تبويب **Stashes**.
- **تجاهل رسائل الإيداع:** السجل و Blame مفيدان بقدر وضوح رسائلك.

## تمرين

### تمرين 1: درج سريع

خزّن تعديل `todo.txt` مؤقتًا، ثم أنشئ ملف `hotfix.txt` وأودعه برسالة `Hotfix`، ثم استرجع المخزّن، واطبع السجل وحالة الملفات.

```powershell exercise
$repo = Join-Path $PWD 'ex4'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config core.autocrlf false
git config user.name 'Ali'
git config user.email 'ali@example.com'
Set-Content todo.txt 'buy milk'
git add .
git commit -q -m 'Todo list'
Add-Content todo.txt 'call Sara'
# خزّن، وأصلح، واسترجع هنا
git log --format='%s'
git status --short
```

```powershell solution
$repo = Join-Path $PWD 'ex4'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config core.autocrlf false
git config user.name 'Ali'
git config user.email 'ali@example.com'
Set-Content todo.txt 'buy milk'
git add .
git commit -q -m 'Todo list'
Add-Content todo.txt 'call Sara'
git stash push -q -m 'todo work'
Set-Content hotfix.txt 'ok'
git add .
git commit -q -m 'Hotfix'
git stash pop -q
git log --format='%s'
git status --short
```

```text output
Hotfix
Todo list
 M todo.txt
```

### مهمة عملية

1. في مستودعك، `Ctrl+Alt+H` وتصفّح **Graph**، وجرّب **View commit details** بالزر الأيمن.
2. فعّل **Git > Toggle inline blame in the editor** وتنقّل بين الأسطر.
3. عدّل ملفًا، ثم **Git > Stash All...**، ولاحظ اختفاء التعديل، ثم **Pop** من تبويب **Stashes**.
4. أودع برسالة فيها خطأ إملائي، ثم أصلحها بـ **Git > Amend last commit**.

## اختبر نفسك

```quiz
{"question": "ما فائدة Blame؟", "choices": ["حذف أسطر الآخرين", "معرفة من عدّل كل سطر ومتى وفي أي إيداع", "تسريع Git", "دمج الفروع"], "answer": 1, "explanation": "Blame يعرض الكاتب والتاريخ والإيداع بجوار كل سطر."}
```

```quiz
{"question": "تحتاج إلى إصلاح عاجل وعملك الحالي غير مكتمل. ما الأنسب؟", "choices": ["Stash All ثم الإصلاح ثم Pop", "حذف عملك", "Reset --hard", "إيداع العمل الناقص في main"], "answer": 0, "explanation": "Stash يضع العمل جانبًا مؤقتًا وينظف المجلد."}
```

```quiz
{"question": "إيداع قديم شاركته مع الفريق سبّب خطأً. ما الطريقة الآمنة لإلغائه؟", "choices": ["Amend", "Revert: إيداع جديد يلغي أثره", "Reset --hard ثم Force Push", "حذف المستودع"], "answer": 1, "explanation": "Revert لا يعيد كتابة التاريخ المشترك."}
```

## الخلاصة

- **Git > View History (graph)** (`Ctrl+Alt+H`): الإيداعات والفروع، وقائمة الزر الأيمن فيها Compare و Cherry-pick و Revert و Reset و New tag.
- **Blame** لقصة كل سطر، و **Compare current file with commit...** للمقارنة.
- **Stash All...** و **Stashes** لوضع العمل جانبًا، و **Amend** و **Undo last commit** و **Revert** و **Reset** للتراجع، وأكثرها أمانًا للتاريخ المشترك **Revert**.
