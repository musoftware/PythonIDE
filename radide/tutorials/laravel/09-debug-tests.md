# الدرس 9: التصحيح والاختبارات والنشر

**في هذا الدرس ستتعلم:**

- قراءة صفحة أخطاء Laravel، وسجل الأخطاء `storage/logs/laravel.log`.
- `dump()` و`dd()` للتتبع السريع.
- التصحيح الحقيقي بـ **Xdebug** (F5) في المتحكمات والنماذج وقوالب Blade.
- كتابة **الاختبارات** وتشغيلها: **New Test...** و**Run Tests** و**Run This Test**.
- أوامر الذاكرة المؤقتة، وقائمة مراجعة قبل النشر.

## صفحة الأخطاء والسجل

مع `APP_DEBUG=true` في `.env` (جهاز التطوير) يعرض Laravel عند أي استثناء صفحة مفصلة: نوع الخطأ والرسالة، والملف والسطر مع الكود حوله، ومكدس الاستدعاءات، وبيانات الطلب. ابدأ دائمًا بأول سطر من **كودك أنت** (في `app/` أو `routes/` أو `resources/views/`)، لا من `vendor/`.

وكل خطأ يُسجَّل أيضًا في `storage/logs/laravel.log`؛ افتحه من Solution Explorer. وتستطيع الكتابة فيه بنفسك:

```php
use Illuminate\Support\Facades\Log;

Log::info('تمت إضافة كتاب', ['id' => $book->id]);
Log::warning('محاولة حذف كتاب غير موجود', ['id' => $id]);
```

## `dump` و `dd`

- `dump($x)` يعرض القيمة منسقة **ويكمل** التنفيذ.
- `dd($x)` (dump and die) يعرضها **ويوقف** التنفيذ فورًا.

```php
public function index()
{
    $books = Book::where('price', '<', 100)->get();
    dd($books->toArray());           // مؤقتًا: ماذا رجع الاستعلام فعلًا؟
    return view('books.index', compact('books'));
}
```

ولرؤية SQL الذي يولّده Eloquent: `dd(Book::where('price', '<', 100)->toRawSql());`. مفيد، لكن تذكّر حذف هذه الأسطر بعد الانتهاء.

## التصحيح بـ Xdebug

نفس طريقة دورة PHP (الدرس 15) تمامًا:

1. ضع **نقطة توقف** بـ **F9** داخل `BookController::store` مثلًا.
2. اضغط **F5** (**Start Debugging / Continue**): يعمل الموقع مع Xdebug. (في أول مرة تعرض الـ IDE تنزيل Xdebug ومحوّل التصحيح؛ ويحتاج المحوّل Node.js.)
3. في المعاينة أرسل نموذج «كتاب جديد». يتوقف التنفيذ عند السطر.
4. في **Locals** افتح `$request` لترى ما أُرسل، وفي **Watch** اكتب `$request->all()` أو `Book::count()`.
5. **F10** خطوة فوق، و**F11** خطوة إلى الداخل (مثلًا إلى دالة في نموذجك)، و**Shift+F11** خروج، و**F5** متابعة، و**Shift+F5** إيقاف.
6. **Call Stack** يبيّن الطريق الذي سلكه الطلب: من `public/index.php` عبر Middleware إلى متحكمك.

نقاط التوقف تعمل أيضًا في **قوالب Blade** (`.blade.php`): ضعها على سطر داخل `@foreach` لترى قيمة `$book` في كل دورة، وفي الترحيلات والـ Seeders عند تشغيلها.

> **تلميح:** لتصحيح أمر Artisan أو Tinker استخدم `Log::info()` أو `dump()`؛ نقاط التوقف مخصصة لطلبات الويب التي تمر بالمعاينة أو المتصفح.

## الاختبارات: موظف يفحص كل شيء في ثوانٍ

**الاختبار الآلي** كود يزور صفحاتك ويتأكد أنها تعمل، فبعد كل تعديل تعرف خلال ثوانٍ هل كسرت شيئًا. Laravel يأتي جاهزًا بـ PHPUnit (أو Pest).

1. الزر الأيمن على `tests/Feature` > **New Test...** (اختبار جديد...) باسم `BookTest`.
2. اكتب:

```php
<?php

namespace Tests\Feature;

use App\Models\Book;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class BookTest extends TestCase
{
    use RefreshDatabase;          // قاعدة بيانات نظيفة لكل اختبار

    public function test_books_page_lists_books(): void
    {
        Book::factory()->create(['title' => 'الأيام']);

        $this->get('/books')
            ->assertOk()
            ->assertSee('الأيام');
    }

    public function test_title_is_required(): void
    {
        $this->post('/books', ['title' => '', 'author' => 'x', 'price' => 10])
            ->assertSessionHasErrors('title');
        $this->assertDatabaseCount('books', 0);
    }

    public function test_book_can_be_deleted(): void
    {
        $book = Book::factory()->create();
        $this->delete("/books/{$book->id}")->assertRedirect('/books');
        $this->assertModelMissing($book);
    }
}
```

3. التشغيل:
   - كل الاختبارات: **Laravel > Tests > Run Tests** (تشغيل الاختبارات) = `php artisan test`.
   - ملف واحد: الزر الأيمن على `BookTest.php` > **Run This Test** (تشغيل هذا الاختبار).
   - والنتائج في نافذة **Output**: علامة ✓ لكل اختبار ناجح، وتفاصيل الفشل مع السطر.

فكرة الاختبار بسيطة: «افعل كذا، ثم **أكّد** (assert) أن النتيجة كذا». إليك محاكاة صغيرة لدوال التأكيد لتفهم ما يحدث:

```php run
<?php
$passed = 0;
$failed = [];

function assert_same($expected, $actual, string $name): void
{
    global $passed, $failed;
    if ($expected === $actual) {
        $passed++;
    } else {
        $failed[] = "$name: المتوقع " . var_export($expected, true) . " والناتج " . var_export($actual, true);
    }
}

function slug(string $title): string
{
    return strtolower(trim(preg_replace('/[^A-Za-z0-9]+/', '-', $title), '-'));
}

assert_same("hello-world", slug("Hello World"), "مسافة");
assert_same("php-8-4", slug("PHP 8.4"), "نقطة");
assert_same("a-b", slug("  a -- b  "), "رموز مكررة");

echo "نجح: {$passed}، فشل: ", count($failed), "\n";
foreach ($failed as $f) {
    echo "✗ $f\n";
}
```

```text output
نجح: 3، فشل: 0
```

## الذاكرة المؤقتة (Cache)

Laravel يخزّن مؤقتًا الإعدادات والمسارات والقوالب المترجمة ليكون أسرع. إذا تصرّف التطبيق كأنه لا يرى تعديلك (خصوصًا بعد تغيير `.env`):

- **Laravel > Cache > Clear All Caches (optimize:clear)** يمسح كل شيء.
- أو أوامر منفردة: `config:clear` و`route:clear` و`view:clear` (وأيضًا من الزر الأيمن على مجلد `config` أو `routes`، و`config:clear` من الزر الأيمن على `.env`).
- وعلى الخادم الحقيقي فقط: **Cache Everything (optimize)** لأقصى سرعة.

## قائمة مراجعة قبل النشر

1. `.env` على الخادم: `APP_ENV=production` و`APP_DEBUG=false` (لا تعرض صفحات الأخطاء المفصلة للزوار!) و`APP_URL` الصحيح وبيانات قاعدة البيانات الحقيقية.
2. `composer install --no-dev --optimize-autoloader` على الخادم.
3. `php artisan migrate --force` ثم `php artisan optimize`.
4. `npm run build` لملفات CSS و JS (أو ارفع `public/build` الناتج).
5. **جذر الموقع** على الخادم = مجلد `public` فقط.
6. صلاحيات الكتابة لمجلدي `storage` و`bootstrap/cache`.
7. شغّل الاختبارات قبل كل نشر: **Run Tests**.

ولرفع الملفات تستطيع استخدام **Site > Publish...** (FTP / SFTP / مجلد) كما في دورة PHP، مع إضافة `node_modules`، و`.env` المحلي، و`storage/logs` إلى **Exclude**. والمواقع الكبيرة تُنشر عادة عبر Git أو خدمات مثل Laravel Forge.

## أخطاء شائعة

- **نقطة التوقف لا تعمل:** شغّلت بـ Ctrl+F5 بدل F5، أو الكود لا يُنفّذ في هذا الطلب (مثلًا التحقق فشل قبل السطر).
- **الاختبار يحذف بياناتك!** `RefreshDatabase` يمسح قاعدة الاختبار. تأكد أن `phpunit.xml` يستخدم قاعدة منفصلة (`DB_DATABASE=:memory:` مع SQLite، وهو الافتراضي في المشاريع الجديدة).
- **`APP_DEBUG=true` على الخادم الحقيقي:** يكشف كودك وإعداداتك للزوار. ممنوع.
- **نسيان `dd()` في الكود:** الصفحة تتوقف عندها للجميع.

## تمرين

### تمرين: دالة تأكيد جديدة

أضف `assert_true(bool $cond, string $name)` تزيد عداد النجاح أو تسجل الفشل، واختبر بها أن `str_contains("Laravel", "ravel")` صحيحة وأن `is_numeric("12a")` خطأ (`!`).

```php exercise
<?php
$passed = 0;
$failed = [];
// function assert_true(...)
assert_true(str_contains("Laravel", "ravel"), "يحتوي");
assert_true(!is_numeric("12a"), "ليس رقمًا");
echo "نجح: {$passed}، فشل: ", count($failed), "\n";
```

```php solution
<?php
$passed = 0;
$failed = [];
function assert_true(bool $cond, string $name): void
{
    global $passed, $failed;
    if ($cond) {
        $passed++;
    } else {
        $failed[] = $name;
    }
}
assert_true(str_contains("Laravel", "ravel"), "يحتوي");
assert_true(!is_numeric("12a"), "ليس رقمًا");
echo "نجح: {$passed}، فشل: ", count($failed), "\n";
```

```text output
نجح: 2، فشل: 0
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين dump() و dd()؟", "choices": ["لا فرق", "dump يعرض ويكمل، dd يعرض ويوقف التنفيذ", "dd أسرع", "dump للمصفوفات فقط"], "answer": 1, "explanation": "dd = dump and die."}
```

```quiz
{"question": "كيف تشغّل ملف اختبار واحد من Solution Explorer؟", "choices": ["الزر الأيمن على الملف > Run This Test", "Site > Publish", "F9", "Help > Tests"], "answer": 0, "explanation": "أوامر الزر الأيمن على ملفات tests تعرض Run This Test."}
```

```quiz
{"question": "ما قيمة APP_DEBUG الصحيحة على الخادم الحقيقي؟", "choices": ["true", "false", "لا يهم", "debug"], "answer": 1, "explanation": "صفحات الأخطاء المفصلة تكشف الكود والإعدادات؛ تُطفأ في الإنتاج."}
```

## الخلاصة

- صفحة الأخطاء و`storage/logs/laravel.log` و`Log::info()` لفهم ما حدث، و`dump`/`dd` للتتبع السريع.
- **F9** و**F5** مع Xdebug في المتحكمات والنماذج وقوالب Blade، و**Locals** و**Watch** و**Call Stack**.
- **New Test...** ثم **Run Tests** أو **Run This Test**، ونتائجها في Output.
- **Clear All Caches** عند الشك، وقائمة المراجعة قبل النشر: `APP_DEBUG=false` وجذر `public` و`migrate --force` و`optimize`.
