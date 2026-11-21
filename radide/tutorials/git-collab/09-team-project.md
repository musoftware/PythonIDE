# الدرس 9: مشروع ختامي: يوم عمل في فريق

**في هذا الدرس ستطبّق كل ما تعلمته:**

- مستودع مشترك، وفرع لكل عضو، وإيداعات برسائل واضحة.
- دمج عمل الزملاء، وحل تعارض حقيقي، ووسم الإصدار `v1.0`.
- ورقة مختصرة بكل أوامر Git والتعاون في RAD IDE.

## القصة

سارة وعلي يبنيان برنامج **"قائمة مقهى"** بلغة BASIC. المستودع المشترك على "GitHub" (سنستخدم مستودعًا محليًا بدلًا منه كما في الدرس 5):

1. سارة تنشئ المشروع وتدفعه.
2. علي ينسخه، ويعمل على فرع `feature/prices` يضيف الأسعار.
3. سارة تعمل في الوقت نفسه على فرع `feature/title` يغيّر العنوان، وتعدّل السطر نفسه الذي عدّله علي!
4. يُدمج فرع علي أولًا، ثم فرع سارة فيحدث تعارض تحلّه سارة.
5. يضعان الوسم `v1.0` على الإصدار.

## البرنامج قبل البداية

هذا هو `Module1.bas` كما أنشأته سارة:

```vb run
Sub Main()
    Debug.Print "Cafe Menu"
    Debug.Print "tea"
    Debug.Print "coffee"
End Sub
```

```text output
Cafe Menu
tea
coffee
```

## اليوم كاملًا بالأوامر

كل سطر عليه تعليق بالأمر المقابل في قوائم RAD IDE:

```powershell run
$base = Join-Path $PWD 'cafe-team'
if (Test-Path $base) { Remove-Item $base -Recurse -Force }
New-Item -ItemType Directory $base | Out-Null
Set-Location $base
git init -q --bare -b main github.git

function Use-Person($name) {
    git config user.name $name
    git config user.email "$($name.ToLower())@example.com"
    git config core.autocrlf false
}

# 1) Sara creates the project and pushes it
git clone -q github.git sara 2>&1 | Out-Null
Set-Location sara; Use-Person 'Sara'
Set-Content Module1.bas 'Sub Main()', '    Debug.Print "Cafe Menu"', '    Debug.Print "tea"', '    Debug.Print "coffee"', 'End Sub'
git add .                                   # Stage All
git commit -q -m 'Cafe menu program'        # Commit
git push -q origin main                     # Git > Push
Set-Location ..

# 2) Ali clones, works on feature/prices, pushes his branch
git clone -q github.git ali
Set-Location ali; Use-Person 'Ali'
git switch -q -c feature/prices             # Git > New Branch...
Set-Content Module1.bas 'Sub Main()', '    Debug.Print "Cafe Menu - prices in EGP"', '    Debug.Print "tea 10"', '    Debug.Print "coffee 15"', 'End Sub'
git commit -q -am 'Add prices'
git push -q -u origin feature/prices        # Push (then Create Pull Request...)
Set-Location ..

# 3) Sara works on feature/title at the same time
Set-Location sara
git switch -q -c feature/title
Set-Content Module1.bas 'Sub Main()', '    Debug.Print "Sara and Ali Cafe"', '    Debug.Print "tea"', '    Debug.Print "coffee"', 'End Sub'
git commit -q -am 'New title'

# 4) Ali's pull request is merged into main first
git fetch -q                                # Git > Fetch
git switch -q main
git merge -q origin/feature/prices          # (the pull request is merged)
git push -q

# ... then Sara merges her branch: conflict on the title line
git merge feature/title 2>&1 | Out-Null     # Merge into current branch...
Write-Output "conflict: $(git status --short)"
# Resolve Conflicts... > Result (editable): keep both ideas, then Accept Merge
Set-Content Module1.bas 'Sub Main()', '    Debug.Print "Sara and Ali Cafe - prices in EGP"', '    Debug.Print "tea 10"', '    Debug.Print "coffee 15"', 'End Sub'
git add Module1.bas
git commit -q --no-edit                     # Continue
git tag v1.0                                # Graph > New tag here...
git push -q --tags origin main              # Push

# 5) Ali pulls the release
Set-Location (Join-Path $base 'ali')
git switch -q main
git pull -q                                 # Git > Pull
Write-Output '--- History (graph)'
git log --graph --format='%s' main
Write-Output "--- tag: $(git describe --tags)"
Write-Output '--- Module1.bas on Ali''s computer'
Get-Content Module1.bas
```

```text output
conflict: UU Module1.bas
--- History (graph)
*   Merge branch 'feature/title'
|\
| * New title
* | Add prices
|/
* Cafe menu program
--- tag: v1.0
--- Module1.bas on Ali's computer
Sub Main()
    Debug.Print "Sara and Ali Cafe - prices in EGP"
    Debug.Print "tea 10"
    Debug.Print "coffee 15"
End Sub
```

الرسم البياني هو نفسه ما تراه في تبويب **Graph** (`Ctrl+Alt+H`): خطّان افترقا من `Cafe menu program` ثم التقيا في إيداع الدمج.

## البرنامج في الإصدار v1.0

```vb run
Sub Main()
    Debug.Print "Sara and Ali Cafe - prices in EGP"
    Debug.Print "tea 10"
    Debug.Print "coffee 15"
End Sub
```

```text output
Sara and Ali Cafe - prices in EGP
tea 10
coffee 15
```

## افعلها في البيئة

كرّر القصة بالواجهة مع زميل (أو بنافذتين: **File > New Window**):

1. **سارة:** مشروع BASIC جديد ← `Ctrl+Alt+G` ← **Init Repository** > **Stage All** > **Commit** > **Git > Remotes...** > **Git > Push**.
2. **علي:** `git clone` في **View > Terminal** > **File > Open Folder...** > **Git > New Branch...** باسم `feature/prices` ← عدّل ← **Commit** > **Push** > **Git > GitHub > Create Pull Request...**.
3. **سارة:** فرع `feature/title` ← عدّل سطر العنوان ← **Commit**.
4. بعد دمج طلب علي: سارة تنتقل إلى `main` من شريط الحالة ← **Git > Pull** > **Git > Merge into current branch...** ← `feature/title`.
5. **Resolve Conflicts...** ← اكتب العنوان المدمج في **Result** > **Accept Merge** > **Continue** > **Push**.
6. `Ctrl+Alt+H` ← بالزر الأيمن على آخر إيداع ← **New tag here...** > `v1.0` > **Push**.
7. للمراجعة معًا مباشرة: **Share > Start Collaboration Session...**.

## ورقة مختصرة

| أريد أن... | في RAD IDE | الأمر المقابل |
|---|---|---|
| أبدأ مستودعًا | **Git Changes > Init Repository** | `git init` |
| أرى التغييرات | **Git > Git Changes** (`Ctrl+Alt+G`) | `git status` |
| أجهّز ملفات | **Stage** / **Stage All** | `git add` |
| أودع | رسالة + **Commit** (`Ctrl+Enter`) | `git commit -m` |
| أصحح آخر إيداع | **Git > Amend last commit** | `git commit --amend` |
| أنشئ فرعًا | **Git > New Branch...** (`Ctrl+Alt+Shift+B`) | `git switch -c` |
| أبدّل الفرع | اسم الفرع في شريط الحالة | `git switch` |
| أدمج | **Git > Merge into current branch...** | `git merge` |
| أحل تعارضًا | **Git > Resolve Conflicts...** | تحرير الملف + `git add` |
| ألغي دمجًا | **Abort** / **Git > Abort merge / rebase** | `git merge --abort` |
| أرى السجل | **Git > View History (graph)** (`Ctrl+Alt+H`) | `git log --graph` |
| من كتب السطر؟ | **Git > Blame current file** | `git blame` |
| أضع العمل جانبًا | **Git > Stash All...** / **Stashes** | `git stash` / `git stash pop` |
| ألغي إيداعًا مشتركًا | Graph > **Revert** | `git revert` |
| أربط بـ GitHub | **Git > Remotes...** | `git remote add origin URL` |
| أجلب / أسحب / أدفع | **Git > Fetch** / **Pull** / **Push** / **Sync** | `git fetch` / `git pull` / `git push` |
| طلب سحب | **Git > GitHub > Create Pull Request...** | `gh pr create` |
| تعاون مباشر | **Share > Start Collaboration Session...** | — |
| خادم بعيد | **File > Open Remote > Connect to SSH Host...** | `ssh` |
| حاوية | **Tools > Docker > ...** | `docker build` / `docker compose up` |
| نشر | **Tools > Deploy to Cloud / Git / SSH...** | حسب الخدمة |

## قاموس المصطلحات

| المصطلح | بالإنجليزية |
|---|---|
| مستودع | Repository |
| إيداع | Commit |
| تجهيز | Stage |
| فرع | Branch |
| دمج | Merge |
| إعادة تأسيس | Rebase |
| تعارض | Conflict |
| مستودع بعيد | Remote |
| جلب / سحب / دفع | Fetch / Pull / Push |
| طلب سحب | Pull Request |
| تخزين مؤقت | Stash |
| وسم | Tag |
| حاوية / صورة | Container / Image |
| نشر | Deploy |

## تمرين

### تمرين 1: إصدار ثانٍ

ابدأ من مستودع فيه الإصدار `v1.0`، وأضف في فرع `feature/juice` سطرًا جديدًا، وادمجه في `main`، وضع الوسم `v1.1`، ثم اطبع الوسوم وسطور الملف.

```powershell exercise
$repo = Join-Path $PWD 'ex9'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea 10', 'coffee 15'
git add .
git commit -q -m 'Menu'
git tag v1.0
# فرع، وإيداع، ودمج، ووسم هنا
git tag
Get-Content menu.txt
```

```powershell solution
$repo = Join-Path $PWD 'ex9'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea 10', 'coffee 15'
git add .
git commit -q -m 'Menu'
git tag v1.0
git switch -q -c feature/juice
Add-Content menu.txt 'juice 18'
git commit -q -am 'Add juice'
git switch -q main
git merge -q feature/juice
git tag v1.1
git tag
Get-Content menu.txt
```

```text output
v1.0
v1.1
tea 10
coffee 15
juice 18
```

## اختبر نفسك

```quiz
{"question": "ما الترتيب الصحيح لإضافة ميزة في فريق؟", "choices": ["تعديل main مباشرة ثم Force Push", "فرع ← إيداعات ← Push ← طلب سحب ← مراجعة ← دمج", "Stash ← Reset --hard ← Push", "Clone ← حذف السجل ← Push"], "answer": 1, "explanation": "هذا هو سير العمل المعتاد في الفرق."}
```

```quiz
{"question": "ظهر `UU Module1.bas` بعد الدمج. ماذا تفعل؟", "choices": ["Resolve Conflicts... ثم Accept Merge ثم Continue", "تحذف الملف", "Force Push", "تتجاهله وتودع"], "answer": 0, "explanation": "UU = تعارض غير محلول."}
```

```quiz
{"question": "ما فائدة الوسم `v1.0`؟", "choices": ["يحذف الإيداعات القديمة", "اسم ثابت لإيداع الإصدار ترجع إليه في أي وقت", "يدمج الفروع", "يشفّر المستودع"], "answer": 1, "explanation": "الوسم علامة على إيداع بعينه: إصدار يمكن الرجوع إليه وبناؤه."}
```

## الخلاصة

- يوم عمل الفريق: مستودع مشترك، وفرع لكل ميزة، وPush، وطلب سحب، ودمج، وحل التعارضات، ووسم الإصدار.
- كل زر في قائمة **Git** هو أمر `git` حقيقي؛ تعلّم الاثنين وستفهم ما يحدث دائمًا.
- وللعمل الفوري معًا: **Share**، وللخوادم: **File > Open Remote**، وللشحن والنشر: **Tools > Docker** و **Tools > Deploy to Cloud / Git / SSH...**.
