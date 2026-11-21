# الدرس 5: قاعدة البيانات والترحيلات والبيانات الأولية

**في هذا الدرس ستتعلم:**

- إعداد الاتصال بقاعدة البيانات في `.env` (SQLite3 أو MariaDB أو PostgreSQL).
- **الترحيلات** (migrations): بناء الجداول بكود PHP يُحفظ مع المشروع.
- **Migrate** و**Rollback** و**Migration Status** من القوائم والزر الأيمن.
- **البيانات الأولية** (seeders) و**Run This Seeder**.
- رؤية الجداول والبيانات في مساحة **Databases**.

## الاتصال

إذا أنشأت المشروع بـ SQLite3 (الدرس 1) فالاتصال جاهز في `.env`:

```ini
database.default.database = database.db
database.default.DBDriver = SQLite3
database.default.foreignKeys = true
```

والملف نفسه `writable/database.db` يُنشأ عند أول ترحيل. ولو اخترت MariaDB أو PostgreSQL ستجد `hostname` و`username` و`password` و`port` مكتوبة لخادم الـ IDE المحلي. وتستطيع فتحها من **CodeIgniter Panel > More > Open .env**.

> **لماذا `.env` وليس `app/Config/Database.php`؟** القيم في `.env` تخص هذا الجهاز فقط وتتغلب على `Database.php`. على الاستضافة تكتب `.env` آخر بقاعدة بيانات أخرى، دون تعديل الكود.

## الترحيلات: سجل تاريخ قاعدة البيانات

بدل أن تنشئ الجداول بيدك (وتنسى ماذا فعلت، ويحتاج زميلك أن يكرر نفس الخطوات)، تكتب كل تغيير في **ملف ترحيل**. الترحيلات مثل **دفتر وصفات مرقّم**: أي جهاز جديد ينفذ الوصفات بالترتيب فيصل لنفس قاعدة البيانات.

1. انقر بالزر الأيمن على `app/Database/Migrations` > **New Migration...** (ترحيل جديد...).
2. الاسم: `CreateProductsTable`، ثم **OK**.

تشغّل الـ IDE `php spark make:migration CreateProductsTable` وتفتح ملفًا اسمه يبدأ بالتاريخ والوقت، مثل `2026-11-21-101500_CreateProductsTable.php` (التاريخ يحدد **الترتيب**). اكتب فيه:

```php
<?php

namespace App\Database\Migrations;

use CodeIgniter\Database\Migration;

class CreateProductsTable extends Migration
{
    public function up(): void
    {
        $this->forge->addField([
            'id'         => ['type' => 'INTEGER', 'unsigned' => true, 'auto_increment' => true],
            'name'       => ['type' => 'VARCHAR', 'constraint' => 120],
            'price'      => ['type' => 'DECIMAL', 'constraint' => '10,2', 'default' => 0],
            'stock'      => ['type' => 'INTEGER', 'default' => 0],
            'created_at' => ['type' => 'DATETIME', 'null' => true],
            'updated_at' => ['type' => 'DATETIME', 'null' => true],
        ]);
        $this->forge->addPrimaryKey('id');
        $this->forge->createTable('products');
    }

    public function down(): void
    {
        $this->forge->dropTable('products');
    }
}
```

- `up()`: ماذا يفعل الترحيل (إنشاء الجدول).
- `down()`: كيف نتراجع عنه (حذف الجدول). اكتبها دائمًا!
- `$this->forge` (**Forge** = «الحدّاد») يبني الجداول بنفس الكود مهما كان نوع قاعدة البيانات.
- `created_at` و`updated_at` يملؤهما النموذج تلقائيًا (الدرس 6).

ثم طبّق الترحيل بأي طريقة:

- **CodeIgniter > Database > Migrate** (تطبيق الترحيلات)، أو
- زر **Migrate** في لوحة CodeIgniter أو في شريط Project Actions، أو
- الزر الأيمن على ملف الترحيل > **Migrate**.

كلها تشغّل `php spark migrate --all`، ويظهر في Output:

```text
Running all new migrations...
	Running: (App) 2026-11-21-101500_App\Database\Migrations\CreateProductsTable
Migrations complete.
```

## كيف يعرف CodeIgniter ما الذي طُبّق؟

يحتفظ بجدول اسمه `migrations` يسجل فيه كل ترحيل طُبّق، ورقم **الدفعة** (batch): كل مرة تضغط Migrate تصبح دفعة جديدة، و**Rollback** يتراجع عن **آخر دفعة** فقط. هذه محاكاة بـ PDO و SQLite في الذاكرة:

```php run
<?php
$db = new PDO('sqlite::memory:');
$db->exec('CREATE TABLE migrations (version TEXT, class TEXT, batch INTEGER)');

// ملفات الترحيل في المجلد: الاسم => [up, down]
$files = [
    '2026-11-01-000001_CreateProducts' => ['CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)', 'DROP TABLE products'],
    '2026-11-02-000001_CreateUsers'    => ['CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)', 'DROP TABLE users'],
];

function migrate(PDO $db, array $files): void
{
    $done = $db->query('SELECT version FROM migrations')->fetchAll(PDO::FETCH_COLUMN);
    $batch = (int) $db->query('SELECT MAX(batch) FROM migrations')->fetchColumn() + 1;
    foreach ($files as $version => [$up, $down]) {
        if (in_array($version, $done, true)) {
            continue;                                   // طُبّق سابقًا: لا يُعاد
        }
        $db->exec($up);
        $db->prepare('INSERT INTO migrations VALUES (?, ?, ?)')->execute([$version, 'App', $batch]);
        echo "Running: $version (batch $batch)\n";
    }
}

function rollback(PDO $db, array $files): void
{
    $batch = (int) $db->query('SELECT MAX(batch) FROM migrations')->fetchColumn();
    $rows = $db->query("SELECT version FROM migrations WHERE batch = $batch ORDER BY version DESC")
               ->fetchAll(PDO::FETCH_COLUMN);
    foreach ($rows as $version) {
        $db->exec($files[$version][1]);
        $db->prepare('DELETE FROM migrations WHERE version = ?')->execute([$version]);
        echo "Rolling back: $version\n";
    }
}

function tables(PDO $db): string
{
    $t = $db->query("SELECT name FROM sqlite_master WHERE type='table' AND name <> 'migrations' ORDER BY name")
            ->fetchAll(PDO::FETCH_COLUMN);
    return 'الجداول: ' . (implode(', ', $t) ?: '(لا شيء)') . "\n";
}

migrate($db, array_slice($files, 0, 1));   // اليوم: ترحيل واحد
migrate($db, $files);                      // غدًا: أضفنا ترحيلًا ثانيًا
echo tables($db);
rollback($db, $files);                     // تراجع عن آخر دفعة فقط
echo tables($db);
migrate($db, $files);                      // Migrate مرة أخرى
echo tables($db);
```

```text output
Running: 2026-11-01-000001_CreateProducts (batch 1)
Running: 2026-11-02-000001_CreateUsers (batch 2)
الجداول: products, users
Rolling back: 2026-11-02-000001_CreateUsers
الجداول: products
Running: 2026-11-02-000001_CreateUsers (batch 2)
الجداول: products, users
```

ومن الـ IDE:

- **Rollback** (تراجع): `php spark migrate:rollback`.
- **Migration Status** (حالة الترحيلات): جدول بكل الترحيلات، ومتى طُبّق كل منها ورقم دفعته.

> **قاعدة ذهبية:** لا تعدّل ترحيلًا **طُبّق** وشاركته مع غيرك. تريد إضافة عمود؟ أنشئ ترحيلًا جديدًا (`AddSkuToProducts`) فيه `$this->forge->addColumn('products', [...])`.

## البيانات الأولية (Seeders)

**Seeder** يملأ الجداول ببيانات تحتاجها دائمًا (حساب المدير، والتصنيفات) أو بيانات للتجربة:

1. الزر الأيمن على `app/Database/Seeds` > **New Seeder...** باسم `ProductSeeder`.
2. اكتب:

```php
<?php

namespace App\Database\Seeds;

use CodeIgniter\Database\Seeder;

class ProductSeeder extends Seeder
{
    public function run(): void
    {
        $this->db->table('products')->insertBatch([
            ['name' => 'قلم',   'price' => 5,  'stock' => 100],
            ['name' => 'دفتر',  'price' => 20, 'stock' => 40],
            ['name' => 'مسطرة', 'price' => 8,  'stock' => 0],
        ]);
    }
}
```

3. الزر الأيمن على الملف نفسه > **Run This Seeder** (تشغيل هذا الـ Seeder)، أو **CodeIgniter > Database > Run Seeder (db:seed)...** واختيار الصنف من القائمة.

ولتشغيل عدة Seeders بالترتيب أنشئ `DatabaseSeeder` يستدعيها: `$this->call('UserSeeder'); $this->call('ProductSeeder');`. هذا هو الصنف الذي تعرضه الـ IDE تلقائيًا عند فتح مشروع منسوخ.

## مساحة Databases

بعد أي `migrate` أو `db:seed` تضيف الـ IDE ملف `writable/database.db` إلى مساحة **Databases** (قواعد البيانات) تلقائيًا. افتحها من **View > Databases** أو **CodeIgniter Panel > More > Open Database in the Databases workspace**:

- **Open Data** (فتح البيانات): ترى المنتجات الثلاثة وتستطيع تعديلها مباشرة.
- **New Query** (استعلام جديد): جرّب `SELECT * FROM migrations` لترى سجل الترحيلات بنفسك.
- **Database Diagram** (مخطط قاعدة البيانات): رسم الجداول والعلاقات.

## أخطاء شائعة

- **`Unable to connect to the database`:** إعدادات `.env` خطأ، أو خادم MariaDB / PostgreSQL متوقف. مع SQLite تأكد أن `DBDriver = SQLite3` بالضبط.
- **Migrate لا يفعل شيئًا:** الترحيل طُبّق سابقًا. افتح **Migration Status**.
- **`table products already exists`:** أنشأت الجدول بيدك قبل الترحيل. احذفه من Databases ثم Migrate.
- **نسيان `down()`:** يصبح Rollback مستحيلًا.
- **`vendor/ is missing`:** Spark يحتاج الحزم: **More > composer install**.

## تمرين

في محاكاة الترحيلات أضف دالة `status()` تطبع لكل ملف ترحيل سطرًا: الاسم ثم `yes (batch N)` إن كان مطبّقًا أو `no` إن لم يكن (مثل **Migration Status**).

```php exercise
<?php
$db = new PDO('sqlite::memory:');
$db->exec('CREATE TABLE migrations (version TEXT, class TEXT, batch INTEGER)');
$db->exec("INSERT INTO migrations VALUES ('2026-11-01-000001_CreateProducts', 'App', 1)");

$files = ['2026-11-01-000001_CreateProducts', '2026-11-02-000001_CreateUsers'];

function status(PDO $db, array $files): void
{
    // اكتب الكود هنا
}

status($db, $files);
```

```php solution
<?php
$db = new PDO('sqlite::memory:');
$db->exec('CREATE TABLE migrations (version TEXT, class TEXT, batch INTEGER)');
$db->exec("INSERT INTO migrations VALUES ('2026-11-01-000001_CreateProducts', 'App', 1)");

$files = ['2026-11-01-000001_CreateProducts', '2026-11-02-000001_CreateUsers'];

function status(PDO $db, array $files): void
{
    $done = $db->query('SELECT version, batch FROM migrations')->fetchAll(PDO::FETCH_KEY_PAIR);
    foreach ($files as $version) {
        echo $version, ': ', isset($done[$version]) ? "yes (batch {$done[$version]})" : 'no', "\n";
    }
}

status($db, $files);
```

```text output
2026-11-01-000001_CreateProducts: yes (batch 1)
2026-11-02-000001_CreateUsers: no
```

## اختبر نفسك

```quiz
{"question": "ما الذي يحدد ترتيب تنفيذ الترحيلات؟", "choices": ["حجم الملف", "التاريخ والوقت في بداية اسم الملف", "ترتيبها في Solution Explorer يدويًا", "عشوائي"], "answer": 1, "explanation": "make:migration يضع التاريخ والوقت في بداية الاسم، فتُنفذ الترحيلات بترتيب إنشائها."}
```

```quiz
{"question": "طبّقت ترحيلين في مرتين منفصلتين، ثم ضغطت Rollback. ماذا يحدث؟", "choices": ["يُتراجع عن الترحيلين", "يُتراجع عن آخر دفعة فقط (الترحيل الثاني)", "تُحذف قاعدة البيانات", "لا شيء"], "answer": 1, "explanation": "كل Migrate دفعة جديدة، و Rollback يتراجع عن آخر دفعة."}
```

```quiz
{"question": "تريد إضافة عمود sku لجدول products المطبّق سابقًا. ماذا تفعل؟", "choices": ["تعدّل ترحيل CreateProductsTable", "تنشئ ترحيلًا جديدًا يضيف العمود بـ addColumn", "تحذف قاعدة البيانات كل مرة", "تكتبه في .env"], "answer": 1, "explanation": "الترحيل المطبّق لا يُعاد؛ كل تغيير جديد ترحيل جديد."}
```

## الخلاصة

- الاتصال في `.env`، و SQLite3 لا يحتاج خادمًا (`writable/database.db`).
- **New Migration...** على `app/Database/Migrations`، ثم `up()` و`down()` بـ Forge، ثم **Migrate**.
- **Rollback** يتراجع عن آخر دفعة، و**Migration Status** يعرض الحالة.
- **New Seeder...** و**Run This Seeder** للبيانات الأولية، ومساحة **Databases** لرؤية النتيجة.
