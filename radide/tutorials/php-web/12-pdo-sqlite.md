# الدرس 12: قواعد البيانات - PDO و SQLite

**في هذا الدرس ستتعلم:**

- ما هي **قاعدة البيانات**، ولماذا نختار **SQLite** للبداية.
- أوامر SQL الأساسية: `CREATE TABLE` و`INSERT` و`SELECT` و`UPDATE` و`DELETE`.
- الاتصال من PHP بالكائن `PDO`.
- **الاستعلامات المُجهّزة** (prepared statements)، ولماذا تحميك من هجوم **SQL Injection**.
- مساحة **Databases** (قواعد البيانات) في RAD IDE: تصفّح الجداول وتعديلها وتشغيل الاستعلامات.

## قاعدة البيانات: خزانة ملفات منظمة

حتى الآن كانت بياناتنا تضيع مع انتهاء البرنامج (أو تعيش في الجلسة فقط). **قاعدة البيانات** (database) تحفظها بشكل دائم ومنظم:

- **الجدول** (table) مثل ورقة Excel لنوع واحد من البيانات: جدول للكتب، وجدول للمستخدمين.
- **العمود** (column) خاصية: العنوان، والمؤلف، والسعر.
- **الصف** (row) سجل واحد: كتاب واحد.
- **المفتاح الأساسي** (primary key) رقم فريد لكل صف، عادةً العمود `id`.

**SQLite** قاعدة بيانات كاملة في **ملف واحد** (مثل `data/app.sqlite`)، بلا خادم ولا تثبيت، ومدعومة في PHP مباشرة. مثالية للتعلّم وللمواقع الصغيرة والمتوسطة. وعندما يكبر موقعك تنتقل إلى MySQL أو PostgreSQL **بنفس الكود تقريبًا**، لأن `PDO` يتعامل معها كلها بنفس الطريقة.

## أول اتصال وأول جدول

في أمثلة سطر الأوامر نستخدم قاعدة **في الذاكرة** `sqlite::memory:` (تختفي عند انتهاء البرنامج)، وفي الموقع سنستخدم ملفًا:

```php run
<?php
$db = new PDO('sqlite::memory:');
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$db->exec("CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0
)");

$db->exec("INSERT INTO books (title, author, price) VALUES ('الأيام', 'طه حسين', 85)");
$db->exec("INSERT INTO books (title, author, price) VALUES ('اللص والكلاب', 'نجيب محفوظ', 60)");
echo "آخر رقم أُضيف: ", $db->lastInsertId(), "\n";

foreach ($db->query("SELECT id, title, author FROM books") as $row) {
    echo "{$row['id']}. {$row['title']} - {$row['author']}\n";
}
```

```text output
آخر رقم أُضيف: 2
1. الأيام - طه حسين
2. اللص والكلاب - نجيب محفوظ
```

- `new PDO('sqlite:...')` يفتح الاتصال (عبارة الاتصال تسمى DSN).
- `ERRMODE_EXCEPTION` يجعل أي خطأ في SQL **استثناءً** واضحًا بدل أن يمر بصمت. اكتبه دائمًا.
- `exec` لأوامر لا تُرجع صفوفًا، و`query` لأوامر `SELECT`.

## SELECT: السؤال الذي تطرحه على البيانات

```php run
<?php
$db = new PDO('sqlite::memory:', null, null, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
$db->exec("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, author TEXT, price REAL)");
$db->exec("INSERT INTO books (title, author, price) VALUES
    ('الأيام', 'طه حسين', 85), ('اللص والكلاب', 'نجيب محفوظ', 60),
    ('الثلاثية', 'نجيب محفوظ', 240), ('موسم الهجرة إلى الشمال', 'الطيب صالح', 95)");

$rows = $db->query("SELECT title, price FROM books WHERE price < 100 ORDER BY price DESC")->fetchAll();
foreach ($rows as $r) {
    echo "{$r['title']}: {$r['price']}\n";
}
echo "عدد كتب محفوظ: ", $db->query("SELECT COUNT(*) FROM books WHERE author = 'نجيب محفوظ'")->fetchColumn(), "\n";
echo "متوسط السعر: ", $db->query("SELECT AVG(price) FROM books")->fetchColumn(), "\n";
```

```text output
موسم الهجرة إلى الشمال: 95
الأيام: 85
اللص والكلاب: 60
عدد كتب محفوظ: 2
متوسط السعر: 120
```

| الجزء | معناه |
|---|---|
| `SELECT title, price` | الأعمدة المطلوبة (`*` = كل الأعمدة) |
| `FROM books` | من أي جدول |
| `WHERE price < 100` | شرط اختيار الصفوف |
| `ORDER BY price DESC` | الترتيب (`ASC` تصاعدي، `DESC` تنازلي) |
| `COUNT(*)` و`AVG(price)` | دوال تجميع: العدد والمتوسط |

`fetchAll()` تُرجع **مصفوفة من المصفوفات الترابطية** (مثل جدول المنتجات في درس المصفوفات تمامًا)، و`fetchColumn()` قيمة واحدة.

## الخطر: SQL Injection

لنفترض أننا نبحث عن كتاب بكلمة كتبها الزائر، ولصقناها مباشرة في نص SQL:

```php run
<?php
$db = new PDO('sqlite::memory:');
$db->exec("CREATE TABLE users (name TEXT, is_admin INTEGER)");
$db->exec("INSERT INTO users VALUES ('ali', 0), ('admin', 1)");

$input = "x' OR '1'='1";                          // ما كتبه زائر خبيث
$sql = "SELECT name FROM users WHERE name = '$input'";   // خطأ فادح!
echo $sql, "\n";
foreach ($db->query($sql) as $row) {
    echo "تسرّب: ", $row['name'], "\n";
}
```

```text output
SELECT name FROM users WHERE name = 'x' OR '1'='1'
تسرّب: ali
تسرّب: admin
```

النص الخبيث **غيّر معنى الاستعلام** فأصبح «أعطني كل المستخدمين»! وبنفس الحيلة يمكن حذف جداول كاملة.

## الحل: الاستعلامات المُجهّزة

نكتب الاستعلام بـ **علامات مكان** (placeholders) مثل `:name` أو `?`، ثم نرسل القيم **منفصلة**. قاعدة البيانات تتعامل مع القيمة كبيان فقط، ولا تنفّذها كأمر أبدًا:

```php run
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE users (name TEXT, is_admin INTEGER)");

$insert = $db->prepare("INSERT INTO users (name, is_admin) VALUES (:name, :admin)");
$insert->execute(['name' => 'ali', 'admin' => 0]);
$insert->execute(['name' => 'admin', 'admin' => 1]);

$input = "x' OR '1'='1";
$stmt = $db->prepare("SELECT name FROM users WHERE name = ?");
$stmt->execute([$input]);
var_dump($stmt->fetchAll());

$stmt->execute(['ali']);
echo "وجدنا: ", $stmt->fetchColumn(), "\n";
```

```text output
array(0) {
}
وجدنا: ali
```

> **القاعدة الذهبية لقواعد البيانات:** أي قيمة جاءت من الزائر تدخل الاستعلام عبر `prepare` و`execute` **فقط**. لا تلصقها في نص SQL بنفسك أبدًا.

## تعديل وحذف

```php run
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, price REAL)");
$db->exec("INSERT INTO books (title, price) VALUES ('أ', 10), ('ب', 20), ('ج', 30)");

$up = $db->prepare("UPDATE books SET price = price * 2 WHERE price >= ?");
$up->execute([20]);
echo "عُدّل: ", $up->rowCount(), " صف\n";

$del = $db->prepare("DELETE FROM books WHERE id = ?");
$del->execute([1]);
echo "حُذف: ", $del->rowCount(), " صف\n";

foreach ($db->query("SELECT title, price FROM books") as $r) {
    echo "{$r['title']}: {$r['price']}\n";
}
```

```text output
عُدّل: 2 صف
حُذف: 1 صف
ب: 40
ج: 60
```

`rowCount()` عدد الصفوف التي تأثرت. وتحذير مهم: `DELETE FROM books` **بدون `WHERE`** يحذف كل الصفوف!

## في الموقع: ملف قاعدة بيانات

نجمع الاتصال في ملف واحد `db.php` تستخدمه كل الصفحات. الدالة تنشئ الجدول إن لم يكن موجودًا (`IF NOT EXISTS`)، والملف يُحفظ في مجلد `data`:

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"name": "سلمى", "message": "موقع رائع!"}}, {"method": "POST", "path": "/", "data": {"name": "باسم", "message": "<i>شكرًا</i>"}}]} -->
```php web run
// #file: db.php
<?php
function db(): PDO
{
    static $pdo = null;              // اتصال واحد للطلب كله
    if ($pdo === null) {
        $pdo = new PDO('sqlite:' . __DIR__ . '/data/guestbook.sqlite', null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec("CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL
        )");
    }
    return $pdo;
}
// #file: index.php
<?php
require_once __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = trim($_POST['name'] ?? '');
    $message = trim($_POST['message'] ?? '');
    if ($name !== '' && $message !== '') {
        $stmt = db()->prepare("INSERT INTO messages (name, message) VALUES (?, ?)");
        $stmt->execute([$name, $message]);
    }
    header('Location: index.php');
    exit;
}
$messages = db()->query("SELECT name, message FROM messages ORDER BY id DESC")->fetchAll();
?>
<h1>سجل الزوار (<?= count($messages) ?>)</h1>
<?php foreach ($messages as $m): ?>
<p><b><?= htmlspecialchars($m['name']) ?>:</b> <?= htmlspecialchars($m['message']) ?></p>
<?php endforeach; ?>
<form method="post"><input name="name"> <input name="message"> <button>أضف</button></form>
```

بعد رسالتين (لاحظ أن `<i>` ظهرت كنص آمن):

```text output
<h1>سجل الزوار (2)</h1>
<p><b>باسم:</b> &lt;i&gt;شكرًا&lt;/i&gt;</p>
<p><b>سلمى:</b> موقع رائع!</p>
<form method="post"><input name="name"> <input name="message"> <button>أضف</button></form>
```

اجتمع هنا كل ما تعلمناه: `require_once`، والنموذج، ونمط PRG، والاستعلام المُجهّز، و`htmlspecialchars`.

## مساحة Databases في RAD IDE

بعد أن تشغّل المثال وتضيف رسائل، افتح **View > Databases** (عرض > قواعد البيانات) أو اضغط **Ctrl+Alt+D**. تظهر نافذة **Databases** وفيها:

- **ملفات SQLite الموجودة في مجلد المشروع تُكتشف تلقائيًا**: ستجد `guestbook` وتحته جدول `messages`.
- انقر على الجدول بالزر الأيمن:
  - **Open Data** (فتح البيانات): جدول قابل للتعديل؛ عدّل خلية مباشرة، أو أضف صفًا بـ **New Row...**، أو احذف صفوفًا، مع تصفية وترتيب وصفحات.
  - **Schema** (المخطط): الأعمدة وأنواعها والفهارس وأمر `CREATE` الكامل، مع **Add Column...**.
  - **New Query** (استعلام جديد): محرر SQL؛ اكتب `SELECT * FROM messages WHERE name = 'سلمى'` وشغّله وانظر النتائج في جدول.
  - **Export to CSV...** و**Import CSV...** و**Export to SQL...**.
- وعلى قاعدة البيانات نفسها: **New Table...** (جدول جديد بنافذة تصميم)، و**Database Diagram** (مخطط يرسم الجداول والعلاقات بينها)، و**Open in Adminer** (أداة إدارة ويب كاملة تفتح في المعاينة).
- ولإنشاء قاعدة جديدة فارغة: زر **New SQLite Database...** (قاعدة بيانات SQLite جديدة...)، أو **Tools > Databases** (أدوات > قواعد البيانات). ويمكن أيضًا إضافة اتصال MySQL أو PostgreSQL من **Add Connection...** (إضافة اتصال...)، بل وتشغيل خادم MariaDB أو PostgreSQL محلي من **Local Servers**.

> **عادة مفيدة:** صمّم الجدول وجرّب استعلاماتك أولًا في **New Query**، وعندما تعمل انقلها إلى كود PHP داخل `prepare`.

## أخطاء شائعة

- **نسيان `ERRMODE_EXCEPTION`** (في PHP 8 هو الافتراضي، لكن اكتبه صراحة): بدونه في النسخ القديمة يفشل الاستعلام بصمت.
- **`could not find driver`:** امتداد `pdo_sqlite` غير مفعّل. نسخة PHP في الـ IDE مفعّل فيها، وإن استخدمت نسخة أخرى فعّله في `php.ini`.
- **`unable to open database file`:** المجلد غير موجود أو غير قابل للكتابة. تأكد من وجود `data/`.
- **لصق المدخلات في SQL:** ثغرة SQL Injection. استخدم `prepare`.
- **`UPDATE` أو `DELETE` بدون `WHERE`:** يغيّر أو يحذف كل الصفوف.

## تمارين

### تمرين 1: أغلى منتج

أنشئ جدول `products (name, price)` في الذاكرة، وأضف `فأرة 150` و`شاشة 3200` و`سماعة 450` باستعلام مُجهّز، ثم اطبع اسم أغلى منتج وسعره: `شاشة: 3200`.

```php exercise
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE products (name TEXT, price REAL)");
// prepare + execute لكل منتج، ثم SELECT ... ORDER BY price DESC LIMIT 1
```

```php solution
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE products (name TEXT, price REAL)");
$ins = $db->prepare("INSERT INTO products (name, price) VALUES (?, ?)");
foreach ([["فأرة", 150], ["شاشة", 3200], ["سماعة", 450]] as $p) {
    $ins->execute($p);
}
$top = $db->query("SELECT name, price FROM products ORDER BY price DESC LIMIT 1")->fetch(PDO::FETCH_ASSOC);
echo "{$top['name']}: {$top['price']}\n";
```

```text output
شاشة: 3200
```

### تمرين 2: البحث الآمن

ابحث عن الكتب التي يحتوي عنوانها على كلمة يكتبها الزائر باستخدام `LIKE` واستعلام مُجهّز، مرتبة بالعنوان. للكلمة `أيام` يجب أن يظهر `أيام العرب` و`الأيام` (و`LIKE` تبحث عن الكلمة في أي مكان من العنوان).

```php exercise
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE books (title TEXT)");
$db->exec("INSERT INTO books VALUES ('الأيام'), ('اللص والكلاب'), ('أيام العرب')");
$q = "أيام";
// WHERE title LIKE ?  ومرّر "%$q%" إلى execute
```

```php solution
<?php
$db = new PDO('sqlite::memory:', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec("CREATE TABLE books (title TEXT)");
$db->exec("INSERT INTO books VALUES ('الأيام'), ('اللص والكلاب'), ('أيام العرب')");
$q = "أيام";
$stmt = $db->prepare("SELECT title FROM books WHERE title LIKE ? ORDER BY title");
$stmt->execute(["%$q%"]);
foreach ($stmt->fetchAll(PDO::FETCH_COLUMN) as $title) {
    echo $title, "\n";
}
```

```text output
أيام العرب
الأيام
```

> `%` في `LIKE` تعني «أي حروف»: `"%أيام%"` = العنوان يحتوي `أيام` في أي مكان. ولاحظ أننا وضعنا علامات `%` في **القيمة** الممررة إلى `execute`، لا في نص الاستعلام.

## اختبر نفسك

```quiz
{"question": "ما الطريقة الآمنة لإدخال قيمة من الزائر في استعلام SQL؟", "choices": ["لصقها في النص بعلامات تنصيص", "prepare ثم execute مع القيم منفصلة", "htmlspecialchars فقط", "تحويلها لحروف كبيرة"], "answer": 1, "explanation": "الاستعلامات المُجهّزة ترسل القيم منفصلة فلا يمكن أن تغيّر معنى الاستعلام."}
```

```quiz
{"question": "ماذا تُرجع fetchAll() افتراضيًا مع FETCH_ASSOC؟", "choices": ["نصًا واحدًا", "مصفوفة من المصفوفات الترابطية (صف لكل عنصر)", "عددًا", "كائن PDO"], "answer": 1, "explanation": "كل صف مصفوفة ترابطية مفاتيحها أسماء الأعمدة."}
```

```quiz
{"question": "كيف تفتح جدول SQLite لتعدّل بياناته داخل RAD IDE؟", "choices": ["Help > About", "View > Databases ثم الزر الأيمن على الجدول > Open Data", "File > Print", "لا يمكن"], "answer": 1, "explanation": "مساحة Databases (Ctrl+Alt+D) تكتشف ملفات SQLite في المشروع وتفتح الجداول في شبكة قابلة للتعديل."}
```

## الخلاصة

- SQLite قاعدة بيانات في ملف واحد، و`PDO` يتعامل معها ومع MySQL وPostgreSQL بنفس الطريقة.
- `exec` للأوامر، و`query` لـ `SELECT` الثابت، و`prepare/execute` لكل ما فيه مدخلات.
- `fetchAll` و`fetch` و`fetchColumn` لقراءة النتائج، و`rowCount` و`lastInsertId` بعد التعديل والإضافة.
- **View > Databases** لتصفّح الجداول وتعديلها وتشغيل الاستعلامات ورسم المخطط.
