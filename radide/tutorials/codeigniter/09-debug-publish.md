# الدرس 9: التصحيح والاختبارات والنشر

**في هذا الدرس ستتعلم:**

- قراءة صفحة أخطاء CodeIgniter، و**شريط التصحيح** (Debug Toolbar)، وملفات السجل في `writable/logs`.
- `log_message()` و`d()` و`dd()` للتتبع السريع.
- التصحيح الحقيقي بـ **Xdebug** (F5) في المتحكمات والنماذج والقوالب.
- كتابة **اختبار** وتشغيله بـ PHPUnit.
- تجهيز الموقع للنشر و**Site > Publish...**.

## صفحة الأخطاء وشريط التصحيح

مع `CI_ENVIRONMENT = development` في `.env` يعرض CodeIgniter عند أي استثناء صفحة مفصلة: نوع الخطأ والرسالة، والملف والسطر مع الكود حوله، ومكدس الاستدعاءات (Backtrace)، وبيانات الطلب. ابدأ دائمًا بأول سطر من **كودك أنت** (في `app/`)، لا من `vendor/` أو `system/`.

وفي أسفل يمين كل صفحة يظهر **شريط التصحيح**: أيقونة CodeIgniter صغيرة، انقرها فيفتح شريط فيه:

- **Timeline**: كم استغرق كل جزء من الطلب.
- **Database**: كل استعلامات SQL التي نُفذت ومدة كل منها (مفيد جدًا لاكتشاف الاستعلامات المكررة).
- **Views**: القوالب التي عُرضت.
- **Routes**: المسار الذي طابق الطلب ومعاملاته.
- **Vars**: متغيرات الجلسة والطلب.

> **مهم:** شريط التصحيح وصفحات الأخطاء المفصلة تظهر في `development` فقط. في `production` يرى الزائر صفحة خطأ عامة لا تكشف شيئًا من الكود.

## السجل: writable/logs

كل خطأ يُسجَّل أيضًا في ملف يومي مثل `writable/logs/log-2026-11-21.log`؛ افتحه من Solution Explorer. وتستطيع الكتابة فيه بنفسك:

```php
log_message('info', 'تمت إضافة منتج {id}', ['id' => $id]);
log_message('error', 'فشل الدفع للطلب {order}', ['order' => $orderId]);
```

المستويات من الأخطر للأقل: `emergency` و`alert` و`critical` و`error` و`warning` و`notice` و`info` و`debug`. وأيها يُكتب فعلًا يحدده `$threshold` في `app/Config/Logger.php`.

## d() و dd()

مع CodeIgniter أداة **Kint** لعرض القيم بشكل جميل:

- `d($x)` يعرض القيمة منسقة **ويكمل** التنفيذ.
- `dd($x)` يعرضها **ويوقف** التنفيذ فورًا.

```php
public function index(): string
{
    $list = model(ProductModel::class)->where('price <', 10)->findAll();
    dd($list);                 // مؤقتًا: ماذا رجع الاستعلام فعلًا؟
    return view('products/index', ['products' => $list]);
}
```

مفيد، لكن تذكّر حذف هذه الأسطر بعد الانتهاء.

## التصحيح بـ Xdebug

نفس طريقة دورة PHP (الدرس 15) تمامًا:

1. ضع **نقطة توقف** بـ **F9** (**Toggle Breakpoint** - تبديل نقطة التوقف) داخل `Products::create` مثلًا.
2. اضغط **F5** (**Start Debugging / Continue** - بدء تصحيح الأخطاء / متابعة): يعمل الموقع مع Xdebug. (في أول مرة تعرض الـ IDE تنزيل Xdebug ومحوّل التصحيح؛ ويحتاج المحوّل Node.js.)
3. في المعاينة أرسل نموذج «منتج جديد». يتوقف التنفيذ عند السطر.
4. في **Locals** (المتغيرات المحلية) افتح `$data` لترى ما أُرسل، وفي **Watch** (المراقبة) اكتب `$products->errors()`.
5. **F10** خطوة فوق، و**F11** خطوة إلى الداخل (مثلًا إلى دالة في نموذجك)، و**Shift+F11** خروج، و**F5** متابعة، و**Shift+F5** إيقاف.
6. **Call Stack** (مكدس الاستدعاءات) يبيّن الطريق الذي سلكه الطلب: من `public/index.php` عبر المرشحات إلى متحكمك.

نقاط التوقف تعمل أيضًا داخل **القوالب** في `app/Views`: ضعها على سطر داخل `foreach` لترى قيمة `$p` في كل دورة.

> **تلميح:** لتصحيح أمر Spark استخدم `log_message()` أو `d()`؛ نقاط التوقف مخصصة لطلبات الويب التي تمر بالمعاينة أو المتصفح.

## الاختبارات

**الاختبار الآلي** كود يزور صفحاتك ويتأكد أنها تعمل، فبعد كل تعديل تعرف خلال ثوانٍ هل كسرت شيئًا. مشروع CodeIgniter يأتي جاهزًا بـ **PHPUnit** ومجلد `tests`.

أنشئ `tests/feature/ProductsTest.php`:

```php
<?php

use CodeIgniter\Test\CIUnitTestCase;
use CodeIgniter\Test\DatabaseTestTrait;
use CodeIgniter\Test\FeatureTestTrait;

final class ProductsTest extends CIUnitTestCase
{
    use DatabaseTestTrait;          // قاعدة بيانات اختبار، والترحيلات تُطبق قبل الاختبارات
    use FeatureTestTrait;           // $this->get() و $this->post() على موقعك

    protected $refresh = true;

    public function testProductsPageLoads(): void
    {
        $result = $this->get('products');

        $result->assertOK();
        $result->assertSee('المنتجات');
    }

    public function testInvalidProductIsRejected(): void
    {
        $result = $this->post('products', ['name' => 'قل', 'price' => '-3', 'stock' => '1']);

        $result->assertRedirect();                          // رجع للنموذج
        $this->dontSeeInDatabase('products', ['name' => 'قل']);
    }
}
```

وشغّله من **View > Terminal** (عرض > الطرفية) في مجلد المشروع:

```text
php vendor/bin/phpunit tests/feature/ProductsTest.php
```

اختبار يفشل يعرض اسمه والسطر والسبب. اقرأ الرسالة، أصلح الكود، وأعد التشغيل. (إعدادات قاعدة بيانات الاختبار في `phpunit.dist.xml` وفي `database.tests.*` في `.env`.)

## قبل النشر: البيئة

أهم إعداد قبل النشر هو `CI_ENVIRONMENT`. CodeIgniter يقرأ `.env` سطرًا سطرًا: يتجاهل التعليقات `#`، والمفاتيح بالنقاط مثل `database.default.hostname` تتغلب على قيم ملفات `app/Config`. هذه محاكاة لقراءته:

```php run
<?php
$env = <<<'ENV'
# ملف .env على الاستضافة
CI_ENVIRONMENT = production

app.baseURL = 'https://shop.example.com/'
database.default.DBDriver = MySQLi
database.default.database = shop
# database.default.password = لا تضع كلمة السر في Git!
ENV;

$values = [];
foreach (explode("\n", $env) as $line) {
    $line = trim($line);
    if ($line === '' || str_starts_with($line, '#')) {
        continue;                                    // سطر فارغ أو تعليق
    }
    [$key, $value] = array_map('trim', explode('=', $line, 2));
    $values[$key] = trim($value, "'\"");             // إزالة علامات التنصيص
}

foreach ($values as $k => $v) {
    echo "$k => $v\n";
}
echo $values['CI_ENVIRONMENT'] === 'production' ? "وضع الإنتاج: لا أخطاء مفصلة ولا شريط تصحيح\n" : "وضع التطوير\n";
```

```text output
CI_ENVIRONMENT => production
app.baseURL => https://shop.example.com/
database.default.DBDriver => MySQLi
database.default.database => shop
وضع الإنتاج: لا أخطاء مفصلة ولا شريط تصحيح
```

## قائمة مراجعة قبل النشر

1. على الاستضافة: `.env` خاص بها فيه `CI_ENVIRONMENT = production`، و`app.baseURL` بعنوان موقعك، وبيانات قاعدة البيانات الحقيقية.
2. **جذر الموقع** على الاستضافة يشير إلى مجلد `public` (من لوحة تحكم الاستضافة). إن لم تستطع، لا ترفع `app` و`.env` داخل `public_html` أبدًا.
3. المجلد `writable` قابل للكتابة (السجلات والذاكرة المؤقتة والجلسات).
4. الحزم: ارفع `vendor` كما هو، أو شغّل على الخادم `composer install --no-dev`.
5. شغّل الترحيلات على الخادم: `php spark migrate --all`.
6. **CodeIgniter > Clear Cache (cache:clear)** بعد النشر إن تغيرت الإعدادات.

ثم **Site > Publish...** (الموقع > نشر...) كما في دورة PHP: ملف تعريف (FTP أو FTPS أو SFTP أو مجلد)، ثم **Test Connection** و**Preview** (تشغيل تجريبي يعرض ما سيُرفع) و**Publish**. والنشر **تدريجي**: المرة التالية لا ترفع إلا ما تغيّر. واستثنِ من الرفع `.env` الخاص بجهازك و`writable/database.db` و`writable/logs`.

## أخطاء شائعة

- **صفحة بيضاء أو «Whoops!» على الاستضافة:** هذه صفحة الخطأ العامة في `production`. افتح `writable/logs` على الخادم لتعرف السبب، ولا تشغّل `development` على موقع حقيقي.
- **`Cache unable to write to .../writable/cache/`:** صلاحيات `writable` لا تسمح بالكتابة.
- **الروابط تشير إلى `localhost`:** `app.baseURL` في `.env` الاستضافة خطأ أو غير موجود.
- **`404` لكل الصفحات إلا الرئيسية:** جذر الموقع ليس `public`، أو ملف `public/.htaccess` لم يُرفع.
- **نسيان حذف `dd()`:** الصفحة تتوقف وتعرض بيانات داخلية. ابحث عن `dd(` قبل كل نشر.

## تمرين

في محاكاة قراءة `.env`، بعض الأسطر فيها تعليق في نهايتها مثل `CI_ENVIRONMENT = production # important`. عدّل الكود ليحذف كل ما بعد ` #` (مسافة ثم #) قبل قراءة القيمة.

```php exercise
<?php
$env = "CI_ENVIRONMENT = production # important\napp.indexPage = ''";

$values = [];
foreach (explode("\n", $env) as $line) {
    $line = trim($line);
    // احذف التعليق هنا
    [$key, $value] = array_map('trim', explode('=', $line, 2));
    $values[$key] = trim($value, "'\"");
}
var_dump($values);
```

```php solution
<?php
$env = "CI_ENVIRONMENT = production # important\napp.indexPage = ''";

$values = [];
foreach (explode("\n", $env) as $line) {
    $line = trim($line);
    $pos = strpos($line, ' #');
    if ($pos !== false) {
        $line = trim(substr($line, 0, $pos));
    }
    [$key, $value] = array_map('trim', explode('=', $line, 2));
    $values[$key] = trim($value, "'\"");
}
var_dump($values);
```

```text output
array(2) {
  ["CI_ENVIRONMENT"]=>
  string(10) "production"
  ["app.indexPage"]=>
  string(0) ""
}
```

## اختبر نفسك

```quiz
{"question": "أين تجد سجل أخطاء CodeIgniter؟", "choices": ["public/logs", "writable/logs", "vendor/logs", "app/Config/Logger.php"], "answer": 1, "explanation": "السجلات اليومية في writable/logs، و Logger.php يحدد المستويات التي تُكتب فقط."}
```

```quiz
{"question": "ما الفرق بين d() و dd()؟", "choices": ["لا فرق", "d() تعرض القيمة وتكمل، و dd() تعرضها وتوقف التنفيذ", "dd() للأرقام فقط", "d() تحذف القيمة"], "answer": 1, "explanation": "dd = dump and die: تعرض وتوقف."}
```

```quiz
{"question": "لماذا يجب أن يكون CI_ENVIRONMENT = production على الاستضافة؟", "choices": ["لأنه أسرع فقط", "حتى لا يرى الزوار صفحات الأخطاء المفصلة وشريط التصحيح التي تكشف الكود", "لأن SQLite لا يعمل في development", "لأن Publish يرفض غيره"], "answer": 1, "explanation": "وضع التطوير يكشف الملفات والاستعلامات ومتغيرات الجلسة؛ الإنتاج يعرض صفحة خطأ عامة."}
```

## الخلاصة

- في `development`: صفحة أخطاء مفصلة و**شريط التصحيح** (Database و Views و Routes و Timeline)، والسجل دائمًا في `writable/logs`.
- `log_message()` للسجل، و`d()` و`dd()` للعرض السريع، و**F9** و**F5** للتصحيح بـ Xdebug حتى في القوالب.
- الاختبارات بـ PHPUnit و`FeatureTestTrait`، وتشغيلها من **Terminal**.
- قبل النشر: `production` و`baseURL` وجذر `public` وصلاحيات `writable`، ثم **Site > Publish...**.
