# الدرس 5: قاعدة البيانات والترحيلات

**في هذا الدرس ستتعلم:**

- إعداد الاتصال بقاعدة البيانات في `.env`.
- **الترحيلات** (migrations): بناء الجداول بكود PHP يُحفظ مع المشروع.
- أوامر الـ IDE: **New Migration...** و**Migrate** و**Rollback** و**Migration Status** و**Run This Migration**.
- **البيانات الأولية** (seeders) و**المصانع** (factories) و**Fresh Database + Seed**.
- رؤية الجداول وتعديل البيانات في مساحة **Databases**.

## الاتصال

مشروع RAD IDE الجديد يستخدم SQLite افتراضيًا، والإعداد في `.env`:

```text
DB_CONNECTION=sqlite
# DB_DATABASE تُترك فارغة = database/database.sqlite
```

وإن اخترت MariaDB أو PostgreSQL عند الإنشاء تجد `DB_HOST` و`DB_PORT` و`DB_DATABASE` و`DB_USERNAME` و`DB_PASSWORD` مملوءة لخادم الـ IDE المحلي. وتستطيع تشغيل هذه الخوادم في أي وقت من **Tools > Databases > Start local MariaDB/MySQL** أو **Start local PostgreSQL**.

## الترحيلات: سجل تاريخ قاعدة البيانات

في دورة PHP أنشأنا الجدول بـ `CREATE TABLE IF NOT EXISTS` داخل الكود. المشكلة: كيف تضيف عمودًا جديدًا لاحقًا على جهاز زميلك وعلى الخادم الحقيقي؟ **الترحيل** ملف PHP يصف **تغييرًا واحدًا** على قاعدة البيانات (إنشاء جدول، أو إضافة عمود)، مع طريقة التراجع عنه. الترحيلات مثل **سجل التعديلات في مخطط البيت**: كل تعديل مؤرخ ومرقّم، وأي نسخة من البيت يمكن أن تُبنى بتطبيق السجل بالترتيب.

### إنشاء ترحيل

1. انقر بالزر الأيمن على `database/migrations` واختر **New Migration...** (ترحيل جديد...).
2. الاسم: `create_books_table` (الاسم يهم: `create_X_table` ينشئ جدول `X`، و`add_Y_to_X_table` يعدّله).
3. يُنشأ ملف مثل `2026_11_21_120000_create_books_table.php` ويُفتح. أكمله:

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('books', function (Blueprint $table) {
            $table->id();                                  // id INTEGER PRIMARY KEY
            $table->string('title');
            $table->string('author');
            $table->unsignedSmallInteger('year')->nullable();
            $table->decimal('price', 8, 2)->default(0);
            $table->timestamps();                          // created_at و updated_at
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('books');
    }
};
```

- `up()` ما يحدث عند التطبيق، و`down()` كيف نتراجع عنه.
- `$table->id()` و`string` و`decimal` و`timestamps` تتحول إلى SQL المناسب لقاعدة بياناتك (SQLite أو MySQL أو PostgreSQL) تلقائيًا.

### التطبيق والتراجع

| الأمر في الـ IDE | ما يشغّله | الوظيفة |
|---|---|---|
| **Laravel > Database > Migrate** (تطبيق الترحيلات) | `artisan migrate` | يطبّق كل ترحيل لم يُطبّق بعد |
| **Rollback** (تراجع) | `artisan migrate:rollback` | يتراجع عن آخر دفعة |
| **Migration Status** (حالة الترحيلات) | `artisan migrate:status` | قائمة الترحيلات: طُبّق أم لا |
| الزر الأيمن على ملف ترحيل > **Run This Migration** | `artisan migrate --path=...` | يطبّق هذا الملف وحده |
| **Fresh Database + Seed (migrate:fresh --seed)...** | `artisan migrate:fresh --seed` | **يحذف كل الجداول** ويبنيها من جديد ثم يملؤها (تسأل الـ IDE قبل التنفيذ) |

كيف يعرف Laravel ما طُبّق؟ يحفظ أسماء الترحيلات في جدول خاص اسمه `migrations`. هذه محاكاة للفكرة:

```php run
<?php
$files = ["2026_01_01_create_users_table", "2026_02_10_create_books_table", "2026_03_05_add_isbn_to_books_table"];
$ran = ["2026_01_01_create_users_table"];          // محفوظة في جدول migrations

function migrate(array $files, array &$ran): void
{
    $pending = array_diff($files, $ran);
    if (!$pending) {
        echo "Nothing to migrate.\n";
        return;
    }
    foreach ($pending as $name) {
        echo "Running: $name ... DONE\n";
        $ran[] = $name;
    }
}

migrate($files, $ran);
migrate($files, $ran);
echo count($ran), " migrations ran\n";
```

```text output
Running: 2026_02_10_create_books_table ... DONE
Running: 2026_03_05_add_isbn_to_books_table ... DONE
Nothing to migrate.
3 migrations ran
```

> **قاعدة ذهبية:** لا تعدّل ترحيلًا **طُبّق** على قاعدة بيانات زميل أو على الخادم. أنشئ ترحيلًا جديدًا للتغيير. (أثناء التطوير على جهازك وحدك يمكنك التعديل ثم **Rollback** و**Migrate**، أو **Fresh Database + Seed**.)

### تعديل جدول موجود

**New Migration...** باسم `add_isbn_to_books_table`:

```php
public function up(): void
{
    Schema::table('books', function (Blueprint $table) {
        $table->string('isbn', 20)->nullable()->after('author');
    });
}

public function down(): void
{
    Schema::table('books', function (Blueprint $table) {
        $table->dropColumn('isbn');
    });
}
```

## البيانات الأولية والمصانع

- **Seeder** يملأ قاعدة البيانات ببيانات ثابتة (حساب المدير، والتصنيفات...). أنشئه بالزر الأيمن على `database/seeders` > **New Seeder...**.
- **Factory** يصنع بيانات **تجريبية عشوائية** كثيرة للاختبار. **New Factory...** على `database/factories`.

```php
// database/factories/BookFactory.php
public function definition(): array
{
    return [
        'title' => fake()->sentence(3),
        'author' => fake()->name(),
        'year' => fake()->numberBetween(1950, 2025),
        'price' => fake()->randomFloat(2, 20, 300),
    ];
}

// database/seeders/DatabaseSeeder.php
public function run(): void
{
    \App\Models\Book::factory(30)->create();      // 30 كتابًا تجريبيًا
}
```

ثم **Laravel > Database > Seed (db:seed)** (تعبئة البيانات)، أو **Run Seeder...** لاختيار Seeder معيّن، أو الزر الأيمن على ملف Seeder. (الـ Factory تحتاج النموذج `Book` الذي سننشئه في الدرس القادم.)

## مساحة Databases

بعد **Migrate** افتح **View > Databases** (Ctrl+Alt+D): ملف `database/database.sqlite` مكتشف تلقائيًا، وتحته الجداول: `books` و`users` و`migrations` و`sessions` و`cache`...

- الزر الأيمن على `books` > **Schema** (المخطط): ترى الأعمدة التي أنشأها الترحيل بأنواعها الحقيقية في SQLite.
- **Open Data** (فتح البيانات): بعد `db:seed` ترى الكتب التجريبية، وتستطيع تعديلها.
- **New Query** (استعلام جديد): `SELECT * FROM migrations` لترى سجل الترحيلات بنفسك.
- **Database Diagram** (مخطط قاعدة البيانات): رسم الجداول والعلاقات (المفاتيح الأجنبية).

ومع MariaDB أو PostgreSQL يظهر الاتصال في نفس النافذة من إعدادات المشروع، أو أضفه بـ **Add Connection...**.

## أخطاء شائعة

- **`Database file at path [...database.sqlite] does not exist`:** أنشئ الملف (التجهيز يفعل ذلك: **Laravel > Prepare Project**) أو من **New SQLite Database...** في مساحة Databases بنفس المسار.
- **`table books already exists`:** طبّقت الترحيل سابقًا بطريقة أخرى. استخدم **Migration Status** لترى الحالة، أو **Fresh Database + Seed** على جهاز التطوير.
- **تعديل ترحيل قديم ولا شيء يتغير:** الترحيل المطبّق لا يُعاد. أنشئ ترحيلًا جديدًا.
- **نسيان `down()`:** يصبح التراجع مستحيلًا.

## تمرين

### تمرين: حالة الترحيلات

اكتب دالة `status(array $files, array $ran): void` تطبع لكل ترحيل `[Ran]` أو `[Pending]` ثم اسمه (مثل جدول **Migration Status**).

```php exercise
<?php
function status(array $files, array $ran): void
{
}
status(["create_users_table", "create_books_table"], ["create_users_table"]);
```

```php solution
<?php
function status(array $files, array $ran): void
{
    foreach ($files as $f) {
        echo (in_array($f, $ran, true) ? "[Ran]     " : "[Pending] "), $f, "\n";
    }
}
status(["create_users_table", "create_books_table"], ["create_users_table"]);
```

```text output
[Ran]     create_users_table
[Pending] create_books_table
```

## اختبر نفسك

```quiz
{"question": "ما الذي يحدد الترحيلات التي طُبقت؟", "choices": ["أسماء الملفات فقط", "جدول migrations داخل قاعدة البيانات", "ملف .env", "لا شيء"], "answer": 1, "explanation": "Laravel يسجل اسم كل ترحيل طُبّق في جدول migrations."}
```

```quiz
{"question": "تريد إضافة عمود isbn لجدول طُبّق على الخادم. ماذا تفعل؟", "choices": ["تعدّل ترحيل إنشاء الجدول", "تنشئ ترحيلًا جديدًا add_isbn_to_books_table", "تضيفه يدويًا في الخادم", "تحذف الجدول"], "answer": 1, "explanation": "كل تغيير جديد = ترحيل جديد؛ لا نعدّل ترحيلًا مطبّقًا."}
```

```quiz
{"question": "ماذا يفعل الأمر Fresh Database + Seed؟", "choices": ["يضيف عمودًا", "يحذف كل الجداول ويطبّق كل الترحيلات من جديد ثم يملأ البيانات الأولية", "ينشر الموقع", "ينسخ قاعدة البيانات"], "answer": 1, "explanation": "migrate:fresh --seed يبدأ من الصفر، لذلك تسألك الـ IDE قبل تنفيذه."}
```

## الخلاصة

- الاتصال في `.env`، وSQLite افتراضيًا في `database/database.sqlite`.
- الترحيل = تغيير واحد بـ `up()` و`down()`، يُنشأ بـ **New Migration...** ويُطبّق بـ **Migrate**.
- **Rollback** و**Migration Status** و**Run This Migration** و**Fresh Database + Seed** للتحكم الكامل.
- Seeders و Factories للبيانات الأولية والتجريبية، و**View > Databases** لرؤية النتيجة.
