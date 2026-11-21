# الدرس 1: ما هو Laravel؟ وإنشاء أول مشروع

**في هذا الدرس ستتعلم:**

- ما هو **إطار العمل** (framework)، ولماذا Laravel.
- فكرة **MVC**: النموذج والعرض والمتحكم.
- إنشاء مشروع Laravel جديد من **File > New Project...** في RAD IDE.
- فتح مشروع Laravel موجود (من Git أو من زميل) وتجهيزه بضغطة واحدة.
- جولة في مجلدات المشروع.

> **قبل أن تبدأ:** هذا الدليل يفترض أنك تعرف أساسيات PHP (المتغيرات، والمصفوفات، والدوال، والأصناف، والنماذج، و PDO). إن لم تكن كذلك فابدأ بدورة **«تطوير مواقع الويب بلغة PHP من الصفر»** في نفس نافذة الدروس.

## إطار العمل: بيت جاهز الهيكل

في دورة PHP بنينا موقع الكتب «من الطوب»: كتبنا بأيدينا الاتصال بقاعدة البيانات، والجلسات، ورموز CSRF، والتحويل، ورسائل الفلاش، والقالب المشترك... **إطار العمل** مثل بيت هيكله جاهز: الأساسات والأعمدة والكهرباء والسباكة موجودة ومختبرة، وأنت تركّز على تصميم الغرف (منطق تطبيقك).

**Laravel** أشهر إطار عمل PHP. يعطيك جاهزًا:

| تحتاجه | ما يقدّمه Laravel |
|---|---|
| ربط العناوين بالكود | **Routes** (المسارات) |
| تنظيم الكود | **Controllers** (المتحكمات) |
| القوالب | **Blade**: قوالب أنظف من PHP داخل HTML |
| قاعدة البيانات | **Migrations** لبناء الجداول، و**Eloquent** للتعامل معها ككائنات |
| الأمان | CSRF والتشفير وكلمات المرور والحماية من XSS و SQL Injection تلقائيًا |
| التحقق من المدخلات | `$request->validate([...])` بقواعد جاهزة |
| أدوات سطر الأوامر | **Artisan**: يولّد الملفات ويشغّل الترحيلات وغيرها |

## MVC: مطعم منظم

يقسم Laravel التطبيق إلى ثلاثة أدوار، مثل مطعم منظم:

- **Model** (النموذج) = **المخزن**: يعرف البيانات ويحفظها ويجلبها (`app/Models/Book.php`).
- **View** (العرض) = **صحن التقديم**: كيف تبدو الصفحة (`resources/views/books/index.blade.php`).
- **Controller** (المتحكم) = **الطاهي**: يستلم الطلب، ويأخذ المكونات من المخزن، ويضعها في الصحن (`app/Http/Controllers/BookController.php`).
- و**Route** (المسار) = **النادل**: يأخذ طلب الزبون (`GET /books`) إلى الطاهي المناسب.

```text
المتصفح --GET /books--> Route --> BookController@index --> Book (Model) --> قاعدة البيانات
المتصفح <---- HTML ---- View (Blade) <---------------------------- البيانات
```

## إنشاء مشروع Laravel جديد

1. **File > New Project...** (ملف > مشروع جديد...).
2. **Web > PHP Web Site** (ويب > موقع ويب PHP)، ثم القالب **Laravel App** (أو **Laravel API** لواجهة JSON فقط).
3. اكتب اسم المشروع مثلًا `LaravelLibrary` ثم **OK**.
4. تظهر نافذة **New Laravel App** فيها:
   - **Database:** اختر **SQLite (database/database.sqlite - no server)** للبداية (بلا خادم)، أو MariaDB / PostgreSQL على **الخادم المحلي للـ IDE** إن أردت.
   - خانة **Install laravel-ide-helper**: اتركها مفعّلة؛ تحسّن IntelliSense كثيرًا (الدرس 8).
5. تبدأ الـ IDE العمل وتعرض التقدّم في نافذة **Output** (المخرجات): `composer create-project laravel/laravel` (تنزيل Laravel، **يحتاج إنترنت** ويأخذ دقائق في أول مرة)، ثم ملف `.env` ومفتاح التطبيق `APP_KEY`، ثم قاعدة البيانات و`artisan migrate`، ثم ملفات IDE Helper.

> **نسخة PHP:** Laravel الحديث يحتاج PHP 8.3 أو أحدث. الـ IDE تختار تلقائيًا أحدث نسخة مثبتة تناسب المشروع، ومن **Tools > PHP Versions...** (أدوات > إصدارات PHP...) تستطيع تثبيت نسخة أحدث. ولكل موقع نسخته في **Site > Site Settings... > PHP version**.

## فتح مشروع Laravel موجود

مشروع منسوخ من GitHub أو من زميل لا يحتوي عادة على `vendor/` (الحزم) ولا `.env` ولا قاعدة البيانات. افتحه بـ **File > Open Project...** أو **File > Open Folder...**: تكتشف الـ IDE أنه Laravel غير جاهز، **وتعرض تجهيزه**:

1. `composer install` (تنزيل الحزم إلى `vendor/`).
2. إنشاء `.env` من `.env.example`، و`artisan key:generate`.
3. إنشاء `database/database.sqlite` ثم `artisan migrate` (و`--seed` إن وُجدت بيانات أولية).
4. `npm install` و`npm run build` إن كان المشروع يستخدم Vite و Tailwind (يحتاج Node.js).

وإن رفضت الآن فالأمر موجود لاحقًا في قائمة **Laravel > Prepare Project (...)...** وفي لوحة Laravel بزر **Install Dependencies**.

> **جرّب على مثال جاهز:** مع الـ IDE مشروع Laravel كامل (مدونة بمستخدمين وتعليقات) في مجلد العينات: `samples/Tests/Web/Laravel_Blog`. انسخه إلى مكان آخر وافتحه وتابع الدروس عليه.

## جولة في المجلدات

افتح **Solution Explorer** (مستكشف الحلول) لترى شجرة المشروع:

```text
LaravelLibrary/
├── app/
│   ├── Http/Controllers/   ← المتحكمات
│   └── Models/             ← النماذج (User.php موجود مسبقًا)
├── bootstrap/app.php       ← إعداد التطبيق (middleware، الاستثناءات)
├── config/                 ← ملفات الإعدادات (app.php، database.php ...)
├── database/
│   ├── migrations/         ← تعريف الجداول
│   ├── seeders/            ← بيانات أولية
│   ├── factories/          ← مصانع بيانات تجريبية
│   └── database.sqlite     ← قاعدة SQLite
├── public/                 ← جذر الموقع (index.php والصور و CSS المبني)
├── resources/views/        ← قوالب Blade
├── routes/
│   ├── web.php             ← مسارات صفحات الموقع
│   └── console.php
├── storage/logs/           ← سجل الأخطاء laravel.log
├── tests/                  ← الاختبارات
├── vendor/                 ← الحزم (لا تعدّل فيها)
├── .env                    ← الإعدادات السرية لهذا الجهاز (لا تُرفع إلى Git)
└── artisan                 ← أداة سطر الأوامر
```

لاحظ أن **جذر الموقع** `public` كما تعلّمنا في دورة PHP: ملفات التطبيق والإعدادات خارج متناول المتصفح.

## ملف .env والإعدادات

`.env` ملف نصي بسيط فيه إعدادات **هذا الجهاز**:

```text
APP_NAME="مكتبتي"
APP_ENV=local
APP_KEY=base64:....
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=sqlite
```

ويقرؤه الكود عبر ملفات `config/`. مثلًا `config('app.name')` يُرجع قيمة `APP_NAME`. فكرة الفصل هذه بسيطة؛ إليك محاكاة صغيرة لها بـ PHP عادية لتفهم ما يحدث في الخلفية:

```php run
<?php
// محاكاة مبسطة: قراءة سطور .env إلى مصفوفة، ثم دالة config مثل Laravel
$envText = "APP_NAME=Library\nAPP_DEBUG=true\nDB_CONNECTION=sqlite\n";
$env = [];
foreach (explode("\n", trim($envText)) as $line) {
    [$key, $value] = explode("=", $line, 2);
    $env[$key] = $value;
}

$config = [
    "app" => ["name" => $env["APP_NAME"] ?? "Laravel", "debug" => ($env["APP_DEBUG"] ?? "false") === "true"],
    "database" => ["default" => $env["DB_CONNECTION"] ?? "mysql"],
];

function config(array $config, string $key)
{
    [$file, $name] = explode(".", $key, 2);
    return $config[$file][$name] ?? null;
}

echo config($config, "app.name"), "\n";
var_dump(config($config, "app.debug"));
echo config($config, "database.default"), "\n";
```

```text output
Library
bool(true)
sqlite
```

في Laravel الحقيقي تكتب فقط `config('app.name')`، والإطار يتولى الباقي.

> **أمان:** `.env` فيه كلمات سر قاعدة البيانات ومفتاح التطبيق؛ لا ترفعه إلى Git أبدًا (موجود في `.gitignore`)، وارفع بدلًا منه `.env.example` بلا أسرار.

## أخطاء شائعة

- **`composer` فشل بسبب الإنترنت:** إنشاء المشروع يحتاج اتصالًا. أعد المحاولة، والـ IDE تستخدم Composer المحمول الخاص بها (**Tools > Composer** و**Tools > PHP Versions... > Install / Update Composer**).
- **`Your PHP version does not satisfy`:** ثبّت PHP أحدث من **Tools > PHP Versions...** واختره في **Site Settings**.
- **صفحة خطأ `No application encryption key`:** ينقص `APP_KEY`. شغّل **Laravel > Generate App Key (key:generate)**.
- **تعديل ملفات داخل `vendor/`:** تضيع مع أول `composer install`. لا تعدّل هناك أبدًا.

## اختبر نفسك

```quiz
{"question": "في MVC، من يستلم الطلب ويجمع البيانات ويختار العرض؟", "choices": ["Model", "View", "Controller", "Migration"], "answer": 2, "explanation": "المتحكم (Controller) هو الطاهي: يستلم الطلب ويستخدم النموذج ويعيد العرض."}
```

```quiz
{"question": "من أين تنشئ مشروع Laravel في RAD IDE؟", "choices": ["Help > About", "File > New Project... > Web > PHP Web Site > Laravel App", "Tools > Options", "Site > Publish"], "answer": 1, "explanation": "قالب Laravel App موجود ضمن قوالب PHP Web Site."}
```

```quiz
{"question": "لماذا لا نرفع ملف .env إلى Git؟", "choices": ["لأنه كبير", "لأنه يحتوي أسرارًا وإعدادات خاصة بالجهاز", "لأن Git لا يقبله", "لا مانع من رفعه"], "answer": 1, "explanation": "فيه APP_KEY وكلمات سر قاعدة البيانات؛ نرفع .env.example بدلًا منه."}
```

## الخلاصة

- Laravel إطار عمل يعطيك المسارات والمتحكمات وBlade وEloquent والأمان جاهزًا، وينظم الكود بنمط MVC.
- **File > New Project... > Web > PHP Web Site > Laravel App** ينشئ مشروعًا كاملًا بقاعدة SQLite.
- فتح مشروع موجود يعرض تجهيزه: composer install، و`.env`، والمفتاح، وقاعدة البيانات، و npm.
- الإعدادات في `.env` و`config/`، والصفحات تبدأ من `routes/web.php`.
