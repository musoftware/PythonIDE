# الدرس 9: مشروع: منظّم الملفات بنافذة رسومية

مجلد «التنزيلات» عند معظمنا فوضى: صور ومستندات وأغانٍ وبرامج تثبيت مختلطة. في هذا المشروع نبني برنامجًا بنافذة **يفحص مجلدًا ويرتب ملفاته في مجلدات فرعية حسب النوع**: `صور` و`مستندات` و`صوتيات` و`أخرى`. هذا هو PowerShell في أفضل حالاته: أتمتة عمل ممل، لكن بواجهة سهلة.

> **تشبيه:** البرنامج مثل **عامل البريد** الذي يفرز الرسائل: ينظر إلى كل رسالة (امتداد الملف)، ثم يضعها في الصندوق المناسب.

## 1) المنطق أولًا في الكونسول

القاعدة الذهبية: نجرّب المنطق في سكربت كونسول صغير قبل أن نربطه بالنافذة. نحتاج دالة تعرف **فئة** الملف من امتداده:

```powershell run
function Get-Category([string]$extension) {
    switch ($extension.ToLower()) {
        { $_ -in ".jpg", ".png", ".gif" } { return "صور" }
        { $_ -in ".txt", ".docx", ".pdf" } { return "مستندات" }
        { $_ -in ".mp3", ".wav" } { return "صوتيات" }
        default { return "أخرى" }
    }
}

# مجلد تجريبي فيه ملفات وهمية
$demo = Join-Path (Get-Location) "demo"
New-Item -ItemType Directory -Path $demo -Force | Out-Null
"trip.jpg", "cv.pdf", "song.mp3", "notes.txt", "logo.PNG", "setup.exe" |
    ForEach-Object { Set-Content -Path (Join-Path $demo $_) -Value "x" }

$order = "صور", "مستندات", "صوتيات", "أخرى"
$files = Get-ChildItem -Path $demo -File
foreach ($category in $order) {
    $names = $files | Where-Object { (Get-Category $_.Extension) -eq $category } |
        Sort-Object Name | ForEach-Object { $_.Name }
    if ($names) { "$category ($(@($names).Count)): $($names -join ', ')" }
}

Remove-Item -Path $demo -Recurse -Force     # ننظف بعد التجربة
```

```text output
صور (2): logo.PNG, trip.jpg
مستندات (2): cv.pdf, notes.txt
صوتيات (1): song.mp3
أخرى (1): setup.exe
```

- `switch` مع **كتلة شرط** `{ $_ -in ... }` تختبر هل الامتداد ضمن قائمة. و`.ToLower()` تجعل `.PNG` مثل `.png`.
- `$_.Extension` خاصية في كائن الملف (تذكّر: `Get-ChildItem` تُرجع **كائنات**، لا نصوصًا).
- `@($names).Count` تضمن أن الناتج مصفوفة حتى لو كان فيها ملف واحد.
- رتبنا الفئات بمصفوفة ثابتة `$order` بدل الفرز الأبجدي، لكي يظهر الترتيب نفسه على كل جهاز.

## 2) تصميم النافذة

أنشئ مشروعًا: **File > New Project...** ثم من مجموعة **.NET** اختر **PowerShell (GUI Bridge)** باسم `FileOrganizer`، وارسم:

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblTitle` | `منظّم الملفات` |
| `TextBox` | `txtFolder` | (مسار المجلد) |
| `Button` | `btnDemo` | `أنشئ مجلدًا تجريبيًا` |
| `Button` | `btnScan` | `افحص` |
| `Button` | `btnOrganize` | `رتّب الملفات` |
| `ListBox` | `lstFiles` | |
| `Label` | `lblStatus` | (فارغ) |

اجعل `lstFiles` عريضًا وطويلًا ليتسع لأسماء الملفات.

## 3) الكود

<!-- test: {"events": ["btnScan.Click", "btnDemo.Click", "btnScan.Click", "btnOrganize.Click"], "expect": {"lstFiles.items": "صور/logo.PNG|صور/trip.jpg|مستندات/cv.pdf|مستندات/notes.txt|صوتيات/song.mp3|أخرى/setup.exe", "lblStatus.Text": "تم نقل 6 ملفات إلى 4 مجلدات", "btnOrganize.enabled": "False"}, "msgbox": ["المجلد غير موجود", "تم الترتيب: 6 ملفات"], "captions": {"btnDemo": "أنشئ مجلدًا تجريبيًا", "btnScan": "افحص", "btnOrganize": "رتّب الملفات"}} -->
```powershell form run
$script:order = "صور", "مستندات", "صوتيات", "أخرى"

function Get-Category([string]$extension) {
    switch ($extension.ToLower()) {
        { $_ -in ".jpg", ".png", ".gif" } { return "صور" }
        { $_ -in ".txt", ".docx", ".pdf" } { return "مستندات" }
        { $_ -in ".mp3", ".wav" } { return "صوتيات" }
        default { return "أخرى" }
    }
}

function Get-Folder {
    $path = $txtFolder.Text.Trim()
    if (-not $path -or -not (Test-Path -Path $path -PathType Container)) {
        MsgBox "المجلد غير موجود" | Out-Null
        return $null
    }
    return $path
}

function Form1_Load($e) {
    $btnOrganize.Enabled = $false
    $lblStatus.Text = "اكتب مسار مجلد أو أنشئ مجلدًا تجريبيًا"
}

function btnDemo_Click($e) {
    $demo = Join-Path (Get-Location) "demo"
    if (Test-Path $demo) { Remove-Item -Path $demo -Recurse -Force }
    New-Item -ItemType Directory -Path $demo | Out-Null
    "trip.jpg", "cv.pdf", "song.mp3", "notes.txt", "logo.PNG", "setup.exe" |
        ForEach-Object { Set-Content -Path (Join-Path $demo $_) -Value "x" }
    $txtFolder.Text = $demo
    $lblStatus.Text = "أُنشئ المجلد التجريبي"
}

function btnScan_Click($e) {
    $folder = Get-Folder
    if (-not $folder) { return }
    $lstFiles.Clear()
    $files = @(Get-ChildItem -Path $folder -File)
    foreach ($category in $script:order) {
        $files | Where-Object { (Get-Category $_.Extension) -eq $category } | Sort-Object Name |
            ForEach-Object { $lstFiles.AddItem("$category ← $($_.Name)") }
    }
    $lblStatus.Text = "عدد الملفات: $($files.Count)"
    $btnOrganize.Enabled = ($files.Count -gt 0)
}

function btnOrganize_Click($e) {
    $folder = Get-Folder
    if (-not $folder) { return }
    $lstFiles.Clear()
    $moved = 0
    $used = @{}
    foreach ($category in $script:order) {
        $files = Get-ChildItem -Path $folder -File | Where-Object { (Get-Category $_.Extension) -eq $category } |
            Sort-Object Name
        foreach ($f in $files) {
            $target = Join-Path $folder $category
            if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target | Out-Null }
            Move-Item -Path $f.FullName -Destination $target
            $lstFiles.AddItem("$category/$($f.Name)")
            "نُقل: $($f.Name)"                 # يظهر في Output
            $moved++
            $used[$category] = $true
        }
    }
    $lblStatus.Text = "تم نقل $moved ملفات إلى $($used.Count) مجلدات"
    $btnOrganize.Enabled = $false
    MsgBox "تم الترتيب: $moved ملفات" | Out-Null
}
```

```text output
نُقل: logo.PNG
نُقل: trip.jpg
نُقل: cv.pdf
نُقل: notes.txt
نُقل: song.mp3
نُقل: setup.exe
```

اضغط **F5**، ثم جرّب بالترتيب: **افحص** (والمربع فارغ) فتظهر رسالة «المجلد غير موجود»، ثم **أنشئ مجلدًا تجريبيًا**، ثم **افحص**، ثم **رتّب الملفات**. افتح المجلد `demo` داخل مجلد المشروع بمستكشف ويندوز وانظر إلى المجلدات الجديدة!

> **تحذير:** البرنامج **ينقل ملفات حقيقية**. جرّبه على المجلد التجريبي أولًا، ولا تجربه على مجلد مهم قبل أن تتأكد أنه يعمل كما تريد.

## 4) كيف يعمل البرنامج؟

1. `Form1_Load` تعطّل زر الترتيب: لا معنى للترتيب قبل الفحص.
2. `Get-Folder` دالة مساعدة يستخدمها زران: تتحقق من المسار بـ `Test-Path -PathType Container` (هل هو مجلد موجود؟) وتعرض رسالة إن لم يكن، وتُرجع `$null`.
3. `btnScan_Click` تعرض الملفات في القائمة مرتبة حسب الفئة، وتفعّل زر الترتيب إذا وجدت ملفات.
4. `btnOrganize_Click` تنشئ مجلد كل فئة عند الحاجة فقط، وتنقل الملفات بـ `Move-Item`، وتعدّ ما نقلته.
5. جدول التجزئة `$used` يتذكر الفئات المستخدمة، و`$used.Count` يعطي عدد المجلدات.

لاحظ أن الأحداث قصيرة، والمنطق في دوال صغيرة لكل منها عمل واحد (`Get-Category`، `Get-Folder`). هذا يجعل البرنامج سهل القراءة والتعديل.

## 5) أفكار للتطوير

- أضف فئة `فيديو` للامتدادات `.mp4` و`.mkv`.
- أضف `CheckBox` باسم `chkCopy`: إذا كان مختارًا يُنسخ الملف بـ `Copy-Item` بدل النقل.
- اعرض حجم كل فئة بالكيلوبايت باستخدام `Measure-Object -Property Length -Sum`.

## تمارين

### التمرين 1

أضف فئة **فيديو** للامتدادات `.mp4` و`.mkv` و`.avi`، واجعل الدالة تُرجعها. جرّب الدالة على ملفات تجريبية واطبع فئة كل اسم.

```powershell exercise
function Get-Category([string]$extension) {
    switch ($extension.ToLower()) {
        { $_ -in ".jpg", ".png", ".gif" } { return "صور" }
        default { return "أخرى" }
    }
}

foreach ($name in "movie.MP4", "photo.png", "clip.mkv", "data.csv") {
    "$name => $(Get-Category ([IO.Path]::GetExtension($name)))"
}
```

```powershell solution
function Get-Category([string]$extension) {
    switch ($extension.ToLower()) {
        { $_ -in ".jpg", ".png", ".gif" } { return "صور" }
        { $_ -in ".mp4", ".mkv", ".avi" } { return "فيديو" }
        default { return "أخرى" }
    }
}

foreach ($name in "movie.MP4", "photo.png", "clip.mkv", "data.csv") {
    "$name => $(Get-Category ([IO.Path]::GetExtension($name)))"
}
```

```text output
movie.MP4 => فيديو
photo.png => صور
clip.mkv => فيديو
data.csv => أخرى
```

`[IO.Path]::GetExtension("movie.MP4")` دالة من .NET تُرجع الامتداد `.MP4` من اسم الملف.

### التمرين 2

في نافذة صغيرة: يكتب المستخدم أسماء ملفات مفصولة بفواصل في `txtNames`، ويضغط `btnCount`، فتظهر في `lstSummary` كل فئة مع عدد ملفاتها مثل `صور: 2`، بترتيب الفئات `صور` ثم `مستندات` ثم `أخرى` (والفئة التي ليس فيها ملفات لا تظهر).

<!-- test: {"set": {"txtNames.Text": "a.jpg, b.txt, c.png, d.zip"}, "events": ["btnCount.Click"], "expect": {"lstSummary.items": "صور: 2|مستندات: 1|أخرى: 1"}} -->
```powershell form exercise
function btnCount_Click($e) {
    $names = $txtNames.Text -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}
```

<!-- test: {"set": {"txtNames.Text": "a.jpg, b.txt, c.png, d.zip"}, "events": ["btnCount.Click"], "expect": {"lstSummary.items": "صور: 2|مستندات: 1|أخرى: 1"}, "captions": {"btnCount": "احسب"}} -->
```powershell form solution
function Get-Category([string]$extension) {
    switch ($extension.ToLower()) {
        { $_ -in ".jpg", ".png", ".gif" } { return "صور" }
        { $_ -in ".txt", ".docx", ".pdf" } { return "مستندات" }
        default { return "أخرى" }
    }
}

function btnCount_Click($e) {
    $names = $txtNames.Text -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $counts = @{}
    foreach ($n in $names) {
        $c = Get-Category ([IO.Path]::GetExtension($n))
        $counts[$c] = $counts[$c] + 1
    }
    $lstSummary.Clear()
    foreach ($c in "صور", "مستندات", "أخرى") {
        if ($counts[$c]) { $lstSummary.AddItem("${c}: $($counts[$c])") }
    }
}
```

`$counts[$c] + 1`: إذا لم يكن المفتاح موجودًا فقيمته `$null`، و`$null + 1` = `1`. ولاحظ `${c}:` بالأقواس، لأن `$c:` وحدها يفهمها PowerShell كأنها بادئة نطاق مثل `$script:`.

## اختبر نفسك

```quiz
{"question": "ما فائدة -PathType Container في Test-Path؟", "choices": ["تنشئ المجلد", "تتأكد أن المسار مجلد موجود وليس ملفًا", "تحذف المجلد", "تنسخ المجلد"], "answer": 1, "explanation": "Container تعني مجلدًا، وLeaf تعني ملفًا."}
```

```quiz
{"question": "لماذا عطّلنا زر الترتيب في Form1_Load؟", "choices": ["لأن الأزرار تبدأ معطلة دائمًا", "لكي لا يرتب المستخدم قبل أن يفحص المجلد ويرى ما سيُنقل", "لتسريع البرنامج", "لأن Move-Item لا تعمل عند البداية"], "answer": 1, "explanation": "تفعيل الأزرار وتعطيلها حسب الحالة يمنع المستخدم من الخطأ."}
```

## الخلاصة

- نبني المنطق في دوال صغيرة ونجربه في الكونسول، ثم نربطه بالأحداث.
- `Get-ChildItem -File` و`Test-Path` و`New-Item -ItemType Directory` و`Move-Item` هي أدوات تنظيم الملفات.
- `Enabled` = `$false` / `$true` لتوجيه المستخدم خطوة بخطوة.
- جربنا على مجلد تجريبي قبل أي ملفات حقيقية: عادة مهمة في كل سكربت أتمتة.
