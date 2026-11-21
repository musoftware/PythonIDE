# الدرس 3: حل تعارضات الدمج

**في هذا الدرس ستتعلم:**

- متى يحدث **تعارض الدمج** (Merge conflict)، ولماذا هو أمر طبيعي لا كارثة.
- قراءة **علامات التعارض** `<<<<<<<` و `=======` و `>>>>>>>`.
- **محرر الدمج الثلاثي** في RAD IDE: الوارد، والأساس، والحالي، والنتيجة.
- إنهاء الدمج بـ **Accept Merge** و **Continue**، أو التراجع بـ **Abort**.

## ورقتان مختلفتان للسطر نفسه

سارة وعلي يعملان على قائمة أسعار. سارة غيّرت سعر القهوة إلى 15، وعلي غيّره في الوقت نفسه إلى 20. عند جمع الورقتين، أي سعر نكتب؟
Git ذكي في جمع التغييرات **المختلفة** (سارة عدّلت سطرًا وعلي سطرًا آخر)، لكنه **لا يخمّن** عندما يعدّل الاثنان **السطر نفسه**. فيتوقف ويسألك أنت: هذا هو **التعارض**.

التعارض ليس خطأً في Git ولا فيك؛ إنه سؤال: "أي النسختين تريد؟ أم مزيجًا منهما؟".

## كيف يبدو التعارض

السكربت التالي يصنع تعارضًا حقيقيًا: `main` يغيّر سعر القهوة إلى 15، وفرع `ali-prices` يغيّره إلى 20، ثم ندمج:

```powershell run
$repo = Join-Path $PWD 'cafe'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false

Set-Content menu.txt 'tea=10', 'coffee=12', 'juice=18'
git add .
git commit -q -m 'Menu'

git switch -q -c ali-prices
Set-Content menu.txt 'tea=10', 'coffee=20', 'juice=18'
git commit -q -am 'Ali: coffee 20'

git switch -q main
Set-Content menu.txt 'tea=10', 'coffee=15', 'juice=18'
git commit -q -am 'Sara: coffee 15'

git merge ali-prices 2>&1 | Out-Null       # Merge into current branch
Write-Output '--- status'
git status --short
Write-Output '--- menu.txt'
Get-Content menu.txt
```

```text output
--- status
UU menu.txt
--- menu.txt
tea=10
<<<<<<< HEAD
coffee=15
=======
coffee=20
>>>>>>> ali-prices
juice=18
```

اقرأ الملف هكذا:

| الجزء | المعنى |
|---|---|
| `<<<<<<< HEAD` | بداية نسختك الحالية (**Current**، الفرع الذي أنت عليه: `main`) |
| `coffee=15` | ما في نسختك |
| `=======` | الفاصل |
| `coffee=20` | ما في الفرع الوارد (**Incoming**: `ali-prices`) |
| `>>>>>>> ali-prices` | نهاية النسخة الواردة |

لاحظ أن `tea=10` و `juice=18` لم يتعارضا: لم يتغيرا، فدمجهما Git وحده. والحالة `UU` تعني "معدّل في الطرفين، غير محلول".

## محرر الدمج في RAD IDE

لا تحتاج إلى حذف العلامات بيدك. عندما يحدث تعارض:

1. يظهر **شريط** أعلى نافذة Git Changes يخبرك أن دمجًا جاريًا، وفيه **Resolve Conflicts...** (حل التعارضات...) و **Continue** (متابعة) و **Abort** (إلغاء العملية). أو من **Git > Resolve Conflicts...**.
2. اختر الملف، فتفتح نافذة **Merge - menu.txt**:

```text
+--------------------+--------------------------+--------------------+
| Incoming (theirs)  | Base (common ancestor)   | Current (ours)     |
| coffee=20          | coffee=12                | coffee=15          |
+--------------------+--------------------------+--------------------+
| Result (editable)                                                  |
| tea=10                                                             |
| coffee=15        <- you choose what goes here                      |
| juice=18                                                           |
+--------------------------------------------------------------------+
```

| الجزء أو الزر | الاسم العربي | ماذا يفعل |
|---|---|---|
| **Incoming (theirs)** | الوارد | نسخة الفرع الذي تدمجه |
| **Base (common ancestor)** | الأساس (السلف المشترك) | الملف قبل أن يغيّره أي منكما (`coffee=12`). أظهره بـ **Show base** |
| **Current (ours)** | الحالي | نسختك |
| **Take Incoming ◀** | أخذ الوارد | النتيجة = نسخة الوارد لهذا التعارض |
| **▶ Take Current** | أخذ الحالي | النتيجة = نسختك |
| **Take Both** | أخذ الاثنين | نسختك ثم الوارد (أو **Both (incoming first)**) |
| **Take Base** | أخذ الأساس | العودة إلى الأصل |
| **▲ Prev** / **▼ Next** | السابق / التالي | التنقل بين التعارضات في الملف |
| **All Incoming** / **All Current** | كل الوارد / كل الحالي | لكل التعارضات الباقية دفعة واحدة |
| **Result (editable)** | النتيجة (قابلة للتعديل) | ما سيُكتب في الملف، ويمكنك الكتابة فيه بيدك |
| **Accept Merge** | قبول الدمج | يكتب الملف ويعلّمه محلولًا (`git add`) |

3. بعد حل كل الملفات اضغط **Continue** في الشريط (أو **Git > Continue merge / rebase**): ينشأ إيداع الدمج.
4. ندمت؟ **Abort** يعيد كل شيء كما كان قبل الدمج.

## الحل بالأوامر

اتفقت سارة وعلي على سعر وسط: 18. هذا ما يحدث خلف **Accept Merge** و **Continue**:

```powershell run
$repo = Join-Path $PWD 'cafe2'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10', 'coffee=12', 'juice=18'
git add .
git commit -q -m 'Menu'
git switch -q -c ali-prices
Set-Content menu.txt 'tea=10', 'coffee=20', 'juice=18'
git commit -q -am 'Ali: coffee 20'
git switch -q main
Set-Content menu.txt 'tea=10', 'coffee=15', 'juice=18'
git commit -q -am 'Sara: coffee 15'
git merge ali-prices 2>&1 | Out-Null

# Result (editable): our agreed price, then Accept Merge (= git add)
Set-Content menu.txt 'tea=10', 'coffee=18', 'juice=18'
git add menu.txt
git commit -q --no-edit                  # Continue
Write-Output '--- status'
git status --short
Write-Output '--- menu.txt'
Get-Content menu.txt
Write-Output '--- history'
git log --format='%s' --first-parent
```

```text output
--- status
--- menu.txt
tea=10
coffee=18
juice=18
--- history
Merge branch 'ali-prices'
Sara: coffee 15
Menu
```

## Abort: زر الطوارئ

إن بدا التعارض معقدًا ولست مستعدًا الآن، اضغط **Abort**: كأن الدمج لم يحدث:

```powershell run
$repo = Join-Path $PWD 'cafe3'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Sara'
git config user.email 'sara@example.com'
git config core.autocrlf false
Set-Content menu.txt 'coffee=12'
git add .
git commit -q -m 'Menu'
git switch -q -c other
Set-Content menu.txt 'coffee=20'
git commit -q -am 'other price'
git switch -q main
Set-Content menu.txt 'coffee=15'
git commit -q -am 'my price'
git merge other 2>&1 | Out-Null
Write-Output "during merge: $(git status --short)"
git merge --abort                        # Abort
Write-Output "after Abort: [$(git status --short)]"
Get-Content menu.txt
```

```text output
during merge: UU menu.txt
after Abort: []
coffee=15
```

## كيف تقلّل التعارضات

- **اسحب (Pull) كثيرًا** وادمج `main` في فرعك أولًا بأول (الدرس 5)؛ التعارض الصغير اليوم أسهل من الكبير بعد أسبوع.
- **فروع قصيرة العمر:** ادمج الميزة خلال أيام لا أسابيع.
- **التنسيق عند الحفظ** للفريق كله، حتى لا تتعارض المسافات (دليل التصحيح والاختبار، الدرس 8).
- **تواصلوا:** "سأعدّل ملف الأسعار اليوم".

## أخطاء شائعة

- **إيداع ملف ما زالت فيه علامات `<<<<<<<`:** البرنامج لن يعمل. راجع **Result** قبل **Accept Merge**.
- **أخذ نسختك دائمًا دون قراءة الوارد:** قد تحذف إصلاحًا مهمًا لزميلك. اقرأ الطرفين و **Base**.
- **نسيان Continue:** الملفات محلولة لكن الدمج لم يكتمل؛ الشريط ما زال ظاهرًا.
- **الذعر:** **Abort** يعيدك إلى ما قبل الدمج دائمًا.

## تمرين

### تمرين 1: خذ الاثنين

في هذا التعارض، كل فرع أضاف صنفًا جديدًا في آخر القائمة. الحل الصحيح هو **Take Both**: الصنفان معًا (صنف `main` أولًا). أكمل السكربت ليكتب النتيجة، ويودع، ويطبع الملف.

```powershell exercise
$repo = Join-Path $PWD 'ex3'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10'
git add .
git commit -q -m 'Menu'
git switch -q -c cakes
Set-Content menu.txt 'tea=10', 'cake=25'
git commit -q -am 'Add cake'
git switch -q main
Set-Content menu.txt 'tea=10', 'milk=8'
git commit -q -am 'Add milk'
git merge cakes 2>&1 | Out-Null
# اكتب النتيجة هنا ثم أودع
Get-Content menu.txt
```

```powershell solution
$repo = Join-Path $PWD 'ex3'
if (Test-Path $repo) { Remove-Item $repo -Recurse -Force }
New-Item -ItemType Directory $repo | Out-Null
Set-Location $repo
git init -q -b main
git config user.name 'Ali'
git config user.email 'ali@example.com'
git config core.autocrlf false
Set-Content menu.txt 'tea=10'
git add .
git commit -q -m 'Menu'
git switch -q -c cakes
Set-Content menu.txt 'tea=10', 'cake=25'
git commit -q -am 'Add cake'
git switch -q main
Set-Content menu.txt 'tea=10', 'milk=8'
git commit -q -am 'Add milk'
git merge cakes 2>&1 | Out-Null
Set-Content menu.txt 'tea=10', 'milk=8', 'cake=25'
git add menu.txt
git commit -q --no-edit
Get-Content menu.txt
```

```text output
tea=10
milk=8
cake=25
```

### مهمة عملية

1. في مستودع تجريبي، أنشئ فرعًا وعدّل فيه سطرًا، ثم عدّل السطر نفسه على `main` بقيمة أخرى.
2. **Git > Merge into current branch...**: لاحظ الشريط والحالة `UU`.
3. **Resolve Conflicts...**: جرّب **Take Incoming** ثم **Reset** ثم **Take Both**، ثم اكتب حلًا بيدك في **Result**.
4. **Accept Merge** ثم **Continue**، وافتح **Graph** لترى نقطة التقاء الفرعين.

## اختبر نفسك

```quiz
{"question": "متى يحدث تعارض الدمج؟", "choices": ["كلما دمجنا فرعين", "عندما يعدّل الفرعان السطر نفسه بقيمتين مختلفتين", "عندما يكون الملف كبيرًا", "عندما ننسى رسالة الإيداع"], "answer": 1, "explanation": "التغييرات في أسطر مختلفة تُدمج تلقائيًا؛ السطر نفسه يحتاج قرارك."}
```

```quiz
{"question": "في علامات التعارض، ما الذي يأتي بين `<<<<<<< HEAD` و `=======`؟", "choices": ["نسخة الفرع الوارد", "نسختك الحالية (Current)", "النسخة الأصلية قبل التعديل", "رسالة الإيداع"], "answer": 1, "explanation": "HEAD = الفرع الذي أنت عليه، أي Current."}
```

```quiz
{"question": "بدأت دمجًا وظهرت تعارضات كثيرة ولا تريد حلها الآن. ماذا تفعل؟", "choices": ["تحذف المستودع", "Abort لإلغاء الدمج والعودة إلى ما قبله", "تودع الملفات بالعلامات", "تغلق البيئة"], "answer": 1, "explanation": "Abort (git merge --abort) يعيد كل شيء كما كان."}
```

## الخلاصة

- التعارض سؤال من Git: "أي النسختين؟" عندما يعدّل فرعان السطر نفسه.
- العلامات: `<<<<<<< HEAD` نسختك، `=======` الفاصل، `>>>>>>> branch` النسخة الواردة.
- **Resolve Conflicts...** يفتح المحرر الثلاثي: **Take Incoming** / **Take Current** / **Take Both** / **Take Base** و **Result**، ثم **Accept Merge** و **Continue**، أو **Abort**.
