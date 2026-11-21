# الدرس 14: المشروع النهائي - موقع إدارة الكتب (CRUD)

**في هذا الدرس ستبني موقعًا كاملًا** لإدارة مكتبة صغيرة، تجتمع فيه كل دروس الدورة:

- عرض الكتب في جدول مع **بحث** بالعنوان أو المؤلف.
- **إضافة** كتاب و**تعديله** و**حذفه** (هذه العمليات الأربع تسمى **CRUD**: Create, Read, Update, Delete).
- التحقق من المدخلات مع رسائل أخطاء، ورسائل نجاح (فلاش) بعد كل عملية.
- قاعدة بيانات **SQLite** عبر **PDO** واستعلامات مُجهّزة.
- **الأمان**: `htmlspecialchars` لكل مخرج، ورمز **CSRF** لكل نموذج POST، والحذف بطلب POST فقط.
- قالب مشترك (رأس وتذييل) وملف تنسيق.

## خريطة المشروع

```text
Library/
├── inc/
│   ├── db.php          ← الاتصال، وإنشاء الجدول، ودوال البيانات
│   ├── functions.php   ← الجلسة، e()، redirect()، flash()، CSRF، التحقق
│   ├── header.php      ← رأس الصفحات + رسالة الفلاش
│   ├── footer.php
│   └── book_form.php   ← نموذج الكتاب (مشترك بين الإضافة والتعديل)
├── data/library.sqlite ← تُنشأ تلقائيًا عند أول طلب
├── index.php           ← القائمة والبحث     (Read)
├── create.php          ← إضافة كتاب          (Create)
├── edit.php            ← تعديل كتاب          (Update)
├── delete.php          ← حذف كتاب            (Delete)
└── site.css
```

## الخطوة 1: إنشاء المشروع في RAD IDE

1. **File > New Project...** ثم **Web > PHP Web Site > PHP Empty Site**، واسم المشروع `Library`.
2. احذف الملفات التي لا نحتاجها (`about.php` ومجلدي `css` و`js`): بالزر الأيمن على الملف **Delete** (حذف).
3. أنشئ المجلد `inc`: بالزر الأيمن على المشروع **Add > New Folder...**.
4. أضف الملفات: بالزر الأيمن على المجلد **Add > New File...**، واختر النوع **PHP Page** (أو **CSS Style Sheet** لملف التنسيق).
5. انسخ محتوى كل ملف من الكتلة الكاملة في آخر الدرس، أو اضغط **«جرّبه»** عليها لتنشئ الـ IDE المشروع كله في خطوة واحدة.

## الخطوة 2: طبقة البيانات (`inc/db.php`)

كل ما يخص قاعدة البيانات في ملف واحد. الصفحات لا تكتب SQL بنفسها، بل تستدعي دوالًا واضحة الأسماء:

```php
function find_book(int $id): ?array
{
    $stmt = db()->prepare("SELECT * FROM books WHERE id = ?");
    $stmt->execute([$id]);
    return $stmt->fetch() ?: null;
}

function search_books(string $q): array
{
    $stmt = db()->prepare("SELECT * FROM books WHERE title LIKE :q OR author LIKE :q ORDER BY title");
    $stmt->execute(['q' => "%$q%"]);
    return $stmt->fetchAll();
}
```

- `fetch()` تُرجع `false` إذا لم يوجد الصف، و`?: null` تحوّلها إلى `null` (النوع `?array` يعني «مصفوفة أو null»).
- علامة المكان المسماة `:q` تُستخدم مرتين ونمرر قيمتها مرة واحدة.
- `save_book` تكتب `INSERT` أو `UPDATE` حسب وجود `$id`، فتخدم الإضافة والتعديل معًا.

## الخطوة 3: الأمان والأدوات (`inc/functions.php`)

```php
function csrf_field(): string
{
    $_SESSION['csrf'] ??= bin2hex(random_bytes(16));
    return '<input type="hidden" name="csrf" value="' . $_SESSION['csrf'] . '">';
}

function verify_csrf(): void
{
    if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) {
        http_response_code(403);
        exit('طلب غير صالح');
    }
}
```

**ما هو CSRF؟** تخيّل أن موقعًا خبيثًا وضع في صفحته نموذجًا مخفيًا يرسل `POST` إلى `delete.php` في موقعك. إذا زارك المدير وهو مسجّل دخوله، سيرسل متصفحه الطلب **بجلسته** فيُحذف الكتاب دون علمه! الحل: **رمز سري عشوائي** يُحفظ في الجلسة ويُوضع حقلًا مخفيًا في كل نموذج من نماذجنا. الموقع الخبيث لا يعرف الرمز، فيُرفض طلبه بالرمز `403`.

- `random_bytes(16)` رمز عشوائي آمن، و`bin2hex` تحوّله إلى 32 حرفًا.
- `hash_equals` مقارنة آمنة تستغرق نفس الوقت دائمًا (لا تكشف الرمز بالتوقيت).
- `never` نوع إرجاع `redirect()`: الدالة لا تعود أبدًا لأنها تنتهي بـ `exit`.

## الخطوة 4: القالب والنموذج المشترك

`inc/header.php` يعرض رسالة الفلاش في كل الصفحات بسطرين فقط:

```php
<?php if ($msg = flash()): ?>
<p class="flash"><?= e($msg) ?></p>
<?php endif; ?>
```

و`inc/book_form.php` نموذج واحد تستخدمه صفحتا الإضافة والتعديل. كل صفحة تجهّز المتغيرين `$book` (القيم) و`$errors` ثم تضمّنه. هكذا أي حقل جديد (مثل «عدد الصفحات») يُضاف في مكان واحد.

> **عرض التصميم:** افتح `index.php` في **Design View** (Ctrl+Shift+D)، وجرّب تحسين الجدول والعناوين أو أضف صورة شعار من **Toolbox**. حلقة `foreach` وكل وسوم PHP تظهر كشرائح محمية لا تنكسر. وللألوان والخطوط عدّل `site.css` وشاهد المعاينة تتحدّث فورًا.

## الخطوة 5: صفحات العمليات

كل صفحة تتبع نفس الترتيب الواضح:

1. `require_once` لملف الأدوات (الجلسة وقاعدة البيانات).
2. إذا كان الطلب `POST`: `verify_csrf()`، ثم التحقق، ثم الحفظ، ثم `flash()` و`redirect()` (نمط PRG).
3. تجهيز `$title` ثم القالب والمحتوى.

ولاحظ في `edit.php`: إذا لم يوجد الكتاب نرد بالرمز `404`، وفي `delete.php` نرفض أي طلب غير `POST` بالرمز `405`. **الحذف عبر رابط `GET` خطأ شائع**: محركات البحث وبرامج «تسريع التصفح» تفتح الروابط تلقائيًا فتحذف بياناتك!

## المشروع كاملًا

اضغط **«جرّبه»** لتنشئ الـ IDE المشروع وتشغّله في المعاينة:

<!-- test: {"requests": [{"path": "/create.php"}, {"method": "POST", "path": "/create.php", "data": {"title": "الأيام", "author": "طه حسين", "year": "1929", "price": "85", "csrf": "{{field:csrf}}"}}, {"path": "/create.php"}, {"method": "POST", "path": "/create.php", "data": {"title": "اللص والكلاب", "author": "نجيب محفوظ", "year": "1961", "price": "60", "csrf": "{{field:csrf}}"}}, {"path": "/edit.php?id=2"}, {"method": "POST", "path": "/edit.php?id=2", "data": {"title": "اللص والكلاب", "author": "نجيب محفوظ", "year": "1961", "price": "75", "csrf": "{{field:csrf}}"}}, {"method": "POST", "path": "/delete.php", "data": {"id": "1", "csrf": "{{field:csrf}}"}}], "mask": {"value=\"[0-9a-f]{32}\"": "value=\"CSRF_TOKEN\""}, "start": "index.php"} -->
```php web run
// #file: inc/db.php
<?php
// الاتصال بقاعدة البيانات وإنشاء الجدول عند أول تشغيل
function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $dir = __DIR__ . '/../data';
        if (!is_dir($dir)) {
            mkdir($dir, 0777, true);
        }
        $pdo = new PDO('sqlite:' . $dir . '/library.sqlite', null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec("CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            price REAL NOT NULL DEFAULT 0
        )");
    }
    return $pdo;
}

function find_book(int $id): ?array
{
    $stmt = db()->prepare("SELECT * FROM books WHERE id = ?");
    $stmt->execute([$id]);
    return $stmt->fetch() ?: null;
}

function search_books(string $q): array
{
    $stmt = db()->prepare("SELECT * FROM books WHERE title LIKE :q OR author LIKE :q ORDER BY title");
    $stmt->execute(['q' => "%$q%"]);
    return $stmt->fetchAll();
}

function save_book(array $book, ?int $id = null): void
{
    $data = [$book['title'], $book['author'], $book['year'], $book['price']];
    if ($id === null) {
        $sql = "INSERT INTO books (title, author, year, price) VALUES (?, ?, ?, ?)";
    } else {
        $sql = "UPDATE books SET title = ?, author = ?, year = ?, price = ? WHERE id = ?";
        $data[] = $id;
    }
    db()->prepare($sql)->execute($data);
}
// #file: inc/functions.php
<?php
// يُضمَّن في أول كل صفحة: الجلسة، وقاعدة البيانات، والدوال المساعدة
session_start();
require_once __DIR__ . '/db.php';

function e($s): string
{
    return htmlspecialchars((string) $s);
}

function redirect(string $url): never
{
    header("Location: $url");
    exit;
}

function flash(?string $message = null): string
{
    if ($message !== null) {
        $_SESSION['flash'] = $message;
        return '';
    }
    $m = $_SESSION['flash'] ?? '';
    unset($_SESSION['flash']);
    return $m;
}

function csrf_field(): string
{
    $_SESSION['csrf'] ??= bin2hex(random_bytes(16));
    return '<input type="hidden" name="csrf" value="' . $_SESSION['csrf'] . '">';
}

function verify_csrf(): void
{
    if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) {
        http_response_code(403);
        exit('طلب غير صالح');
    }
}

function validate_book(array $in, array &$errors): array
{
    $book = [
        'title' => trim($in['title'] ?? ''),
        'author' => trim($in['author'] ?? ''),
        'year' => trim($in['year'] ?? ''),
        'price' => trim($in['price'] ?? ''),
    ];
    if ($book['title'] === '') {
        $errors[] = 'العنوان مطلوب';
    }
    if ($book['author'] === '') {
        $errors[] = 'اسم المؤلف مطلوب';
    }
    if ($book['year'] !== '' && (!ctype_digit($book['year']) || (int) $book['year'] > 2100)) {
        $errors[] = 'سنة النشر غير صحيحة';
    }
    if (!is_numeric($book['price']) || (float) $book['price'] < 0) {
        $errors[] = 'السعر يجب أن يكون رقمًا موجبًا';
    }
    return $book;
}
// #file: inc/header.php
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= e($title) ?> - مكتبتي</title>
    <link rel="stylesheet" href="site.css">
</head>
<body>
<header><a href="index.php">📚 مكتبتي</a> <a href="create.php">+ كتاب جديد</a></header>
<main>
<?php if ($msg = flash()): ?>
<p class="flash"><?= e($msg) ?></p>
<?php endif; ?>
// #file: inc/footer.php
</main>
</body>
</html>
// #file: inc/book_form.php
<?php if ($errors): ?>
<ul class="errors">
<?php foreach ($errors as $err): ?>
    <li><?= e($err) ?></li>
<?php endforeach; ?>
</ul>
<?php endif; ?>
<form method="post">
    <?= csrf_field() ?>
    <label>العنوان <input name="title" value="<?= e($book['title']) ?>"></label>
    <label>المؤلف <input name="author" value="<?= e($book['author']) ?>"></label>
    <label>السنة <input name="year" value="<?= e($book['year']) ?>"></label>
    <label>السعر <input name="price" value="<?= e($book['price']) ?>"></label>
    <button>حفظ</button>
</form>
// #file: index.php
<?php
require_once __DIR__ . '/inc/functions.php';
$q = trim($_GET['q'] ?? '');
$books = search_books($q);
$title = 'الكتب';
require __DIR__ . '/inc/header.php';
?>
<h1>الكتب (<?= count($books) ?>)</h1>
<form method="get"><input name="q" value="<?= e($q) ?>"> <button>بحث</button></form>
<table>
    <tr><th>العنوان</th><th>المؤلف</th><th>السنة</th><th>السعر</th><th></th></tr>
<?php foreach ($books as $b): ?>
    <tr>
        <td><?= e($b['title']) ?></td>
        <td><?= e($b['author']) ?></td>
        <td><?= e($b['year']) ?></td>
        <td><?= number_format($b['price'], 2) ?></td>
        <td>
            <a href="edit.php?id=<?= $b['id'] ?>">تعديل</a>
            <form method="post" action="delete.php" class="inline">
                <?= csrf_field() ?><input type="hidden" name="id" value="<?= $b['id'] ?>">
                <button>حذف</button>
            </form>
        </td>
    </tr>
<?php endforeach; ?>
</table>
<?php require __DIR__ . '/inc/footer.php'; ?>
// #file: create.php
<?php
require_once __DIR__ . '/inc/functions.php';
$errors = [];
$book = ['title' => '', 'author' => '', 'year' => '', 'price' => ''];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();
    $book = validate_book($_POST, $errors);
    if (!$errors) {
        save_book($book);
        flash("أُضيف كتاب «{$book['title']}»");
        redirect('index.php');
    }
}
$title = 'كتاب جديد';
require __DIR__ . '/inc/header.php';
?>
<h1>كتاب جديد</h1>
<?php require __DIR__ . '/inc/book_form.php'; ?>
<?php require __DIR__ . '/inc/footer.php'; ?>
// #file: edit.php
<?php
require_once __DIR__ . '/inc/functions.php';
$id = (int) ($_GET['id'] ?? 0);
$book = find_book($id);
if ($book === null) {
    http_response_code(404);
    exit('الكتاب غير موجود');
}
$errors = [];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();
    $book = validate_book($_POST, $errors);
    if (!$errors) {
        save_book($book, $id);
        flash("حُفظت التعديلات على «{$book['title']}»");
        redirect('index.php');
    }
}
$title = 'تعديل كتاب';
require __DIR__ . '/inc/header.php';
?>
<h1>تعديل: <?= e($book['title']) ?></h1>
<?php require __DIR__ . '/inc/book_form.php'; ?>
<?php require __DIR__ . '/inc/footer.php'; ?>
// #file: delete.php
<?php
require_once __DIR__ . '/inc/functions.php';
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit('الحذف يكون بطلب POST فقط');
}
verify_csrf();
$book = find_book((int) ($_POST['id'] ?? 0));
if ($book !== null) {
    db()->prepare("DELETE FROM books WHERE id = ?")->execute([$book['id']]);
    flash("حُذف كتاب «{$book['title']}»");
}
redirect('index.php');
// #file: site.css
body { font-family: Tahoma, sans-serif; margin: 0; background: #f6f7f9; }
header { background: #1f3d7a; padding: 12px 24px; }
header a { color: #fff; margin-left: 18px; text-decoration: none; }
main { max-width: 860px; margin: 20px auto; background: #fff; padding: 20px; border-radius: 8px; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #ddd; padding: 6px; text-align: right; }
label { display: block; margin: 8px 0; }
.flash { background: #e6f4ea; padding: 8px; border-radius: 6px; }
.errors { color: #b00020; }
form.inline { display: inline; }
```

هذا ما تعرضه `index.php` بعد سيناريو كامل: إضافة «الأيام» ثم «اللص والكلاب»، وتعديل سعر الثاني إلى 75، ثم حذف الأول (قيمة رمز CSRF الحقيقية عشوائية، ووضعنا مكانها `CSRF_TOKEN`):

```text output
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>الكتب - مكتبتي</title>
    <link rel="stylesheet" href="site.css">
</head>
<body>
<header><a href="index.php">📚 مكتبتي</a> <a href="create.php">+ كتاب جديد</a></header>
<main>
<p class="flash">حُذف كتاب «الأيام»</p>
<h1>الكتب (1)</h1>
<form method="get"><input name="q" value=""> <button>بحث</button></form>
<table>
    <tr><th>العنوان</th><th>المؤلف</th><th>السنة</th><th>السعر</th><th></th></tr>
    <tr>
        <td>اللص والكلاب</td>
        <td>نجيب محفوظ</td>
        <td>1961</td>
        <td>75.00</td>
        <td>
            <a href="edit.php?id=2">تعديل</a>
            <form method="post" action="delete.php" class="inline">
                <input type="hidden" name="csrf" value="CSRF_TOKEN"><input type="hidden" name="id" value="2">
                <button>حذف</button>
            </form>
        </td>
    </tr>
</table>
</main>
</body>
</html>
```

## الخطوة 6: جرّب المشروع بأدوات الـ IDE

1. **أضف كتبًا** من «+ كتاب جديد». جرّب ترك العنوان فارغًا أو كتابة سعر سالب لترى رسائل التحقق.
2. راقب **Requests**: بعد كل حفظ ترى `POST /create.php` بالرمز `302` ثم `GET /index.php` بالرمز `200` (نمط PRG). افتح تبويب **Request Body** لطلب الـ POST لترى الحقل المخفي `csrf`.
3. افتح **View > Databases** (Ctrl+Alt+D): ستجد `library` وتحته جدول `books`. **Open Data** يعرض الكتب؛ عدّل سعرًا مباشرة في الشبكة ثم حدّث المعاينة لترى التعديل في الموقع.
4. من **New Query** جرّب: `SELECT author, COUNT(*) AS n, SUM(price) FROM books GROUP BY author`.
5. اختر حجم **Phone** في المعاينة: هل الجدول مقروء؟ حسّن `site.css` (مثلًا `table { font-size: 14px; }`).
6. جرّب الأمان: في المعاينة اكتب عنوانًا مثل `/delete.php` مباشرة (طلب GET): يجب أن ترى «الحذف يكون بطلب POST فقط». وأضف كتابًا عنوانه `<b>تجربة</b>`: يجب أن يظهر النص بالوسوم كما هي، لا بخط عريض.

## تحديات لتطوير المشروع

- أضف عمود «عدد الصفحات» (`pages`): عدّل `CREATE TABLE` (أو أضف العمود من **Schema > Add Column...** في مساحة Databases)، ثم `save_book` و`validate_book` و`book_form.php` والجدول.
- أضف ترتيبًا بالضغط على عنوان العمود (`index.php?sort=price`) مع **قائمة مسموحة** لأسماء الأعمدة (لا تلصق اسم العمود من الزائر في SQL أبدًا).
- أضف تسجيل دخول من الدرس 10 بحيث لا يضيف أو يحذف إلا المدير.
- قسّم القائمة إلى صفحات (`LIMIT 10 OFFSET ...`).

## تمارين

### تمرين 1: قيمة المكتبة

اكتب دالة `library_value(array $books): float` تُرجع مجموع الأسعار، واطبعها منسقة برقمين عشريين.

```php exercise
<?php
function library_value(array $books): float
{
    return 0;
}
$books = [
    ["title" => "الأيام", "price" => 85],
    ["title" => "اللص والكلاب", "price" => 75],
    ["title" => "الثلاثية", "price" => 240.5],
];
echo number_format(library_value($books), 2), "\n";
```

```php solution
<?php
function library_value(array $books): float
{
    return array_sum(array_column($books, "price"));
}
$books = [
    ["title" => "الأيام", "price" => 85],
    ["title" => "اللص والكلاب", "price" => 75],
    ["title" => "الثلاثية", "price" => 240.5],
];
echo number_format(library_value($books), 2), "\n";
```

```text output
400.50
```

### تمرين 2: ترتيب آمن

دالة `order_by(string $sort): string` تُرجع جزء SQL للترتيب، ولا تقبل إلا `title` أو `price` أو `year`، وأي قيمة أخرى تُرجع `ORDER BY title`. جرّبها بقيمة خبيثة.

```php exercise
<?php
function order_by(string $sort): string
{
    return "ORDER BY $sort";      // خطر! أصلحها بقائمة مسموحة
}
echo order_by("price"), "\n";
echo order_by("title; DROP TABLE books"), "\n";
```

```php solution
<?php
function order_by(string $sort): string
{
    $allowed = ["title", "price", "year"];
    if (!in_array($sort, $allowed, true)) {
        $sort = "title";
    }
    return "ORDER BY $sort";
}
echo order_by("price"), "\n";
echo order_by("title; DROP TABLE books"), "\n";
```

```text output
ORDER BY price
ORDER BY title
```

## اختبر نفسك

```quiz
{"question": "ما معنى CRUD؟", "choices": ["أربع لغات برمجة", "الإنشاء والقراءة والتعديل والحذف", "نوع من قواعد البيانات", "أداة في الـ IDE"], "answer": 1, "explanation": "Create, Read, Update, Delete: العمليات الأساسية على البيانات."}
```

```quiz
{"question": "لماذا يكون الحذف بطلب POST مع رمز CSRF وليس برابط GET؟", "choices": ["لأن GET أبطأ", "لأن الروابط قد تُفتح تلقائيًا أو من موقع خبيث فتحذف البيانات", "لأن GET لا يصل إلى PHP", "لا فرق"], "answer": 1, "explanation": "الطلبات التي تغيّر البيانات تكون POST مع رمز سري يمنع الطلبات المزوّرة."}
```

```quiz
{"question": "أين تعدّل بيانات جدول books مباشرة دون كتابة SQL؟", "choices": ["View > Databases ثم Open Data", "Site > Publish", "Help > About", "Toolbox"], "answer": 0, "explanation": "مساحة Databases تفتح الجدول في شبكة قابلة للتعديل."}
```

## الخلاصة

- بنيت موقع CRUD كاملًا: قائمة وبحث وإضافة وتعديل وحذف.
- فصلت طبقة البيانات (`db.php`) عن الأدوات (`functions.php`) عن القالب والصفحات.
- طبّقت قواعد الأمان: `htmlspecialchars`، والاستعلامات المُجهّزة، وCSRF، والحذف بـ POST، والقوائم المسموحة.
- استخدمت أدوات الـ IDE: المعاينة، وRequests، وDatabases، وDesign View.
- بقي أن نتعلم كيف **نصحح** الأخطاء خطوة بخطوة وكيف **ننشر** الموقع على الإنترنت: الدرس القادم.
