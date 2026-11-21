# الدرس 9: تقسيم الموقع إلى ملفات وقالب مشترك

**في هذا الدرس ستتعلم:**

- تضمين ملف داخل آخر بـ `require` و`include` و`require_once`.
- صنع **قالب مشترك** (رأس وتذييل) لكل صفحات الموقع.
- ملف للدوال المساعدة يُستخدم في كل الصفحات.
- استخدام `__DIR__` لمسارات لا تنكسر، وفكرة مجلد `public`.

## المشكلة: تكرار نفس الكود

موقع من 10 صفحات، في كل صفحة نفس الرأس (الشعار والقائمة) ونفس التذييل. إذا أردت إضافة رابط للقائمة ستعدّل 10 ملفات! الحل: نضع الأجزاء المشتركة في ملفات مستقلة، و«نستدعيها» في كل صفحة، مثل قطع الليغو.

## require و include

```php run
// #file: main.php
<?php
require 'config.php';
require 'helpers.php';

echo SITE_NAME, "\n";
echo money(1500), "\n";
// #file: config.php
<?php
const SITE_NAME = "متجر الواحة";
// #file: helpers.php
<?php
function money(float $v): string
{
    return number_format($v, 2) . " ج.م";
}
```

```text output
متجر الواحة
1,500.00 ج.م
```

`require 'helpers.php';` يضع محتوى الملف **مكان السطر** كأنك كتبته هناك. الفرق بين الأوامر:

| الأمر | إذا لم يوجد الملف | إذا ضُمّن مرتين |
|---|---|---|
| `require` | خطأ قاتل ويتوقف البرنامج | يُضمَّن مرتين |
| `include` | تحذير ويكمل البرنامج | يُضمَّن مرتين |
| `require_once` | خطأ قاتل | يُضمَّن **مرة واحدة فقط** |

> **نصيحة:** استخدم `require_once` لملفات الدوال والإعدادات (حتى لا يحدث `Cannot redeclare function`)، و`require` لأجزاء القالب التي تطبع HTML.

## قالب مشترك: header و footer

ننشئ مجلدًا اسمه `inc` للأجزاء المشتركة. في Solution Explorer: انقر بالزر الأيمن على المشروع واختر **Add > New Folder...** (إضافة > مجلد جديد...)، ثم انقر على المجلد بالزر الأيمن و**Add > New File...** لإضافة الملفات.

<!-- test: {"requests": [{"path": "/index.php"}, {"path": "/about.php"}], "all": true} -->
```php web run
// #file: inc/header.php
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title><?= e($title) ?> - مكتبتي</title></head>
<body>
<nav><a href="index.php">الرئيسية</a> | <a href="about.php">من نحن</a></nav>
<main>
// #file: inc/footer.php
</main>
<footer>جميع الحقوق محفوظة</footer>
</body>
</html>
// #file: inc/functions.php
<?php
function e($s): string
{
    return htmlspecialchars((string) $s);
}
// #file: index.php
<?php
require_once __DIR__ . '/inc/functions.php';
$title = 'الرئيسية';
require __DIR__ . '/inc/header.php';
?>
<h1>أهلًا بك في مكتبتي</h1>
<?php require __DIR__ . '/inc/footer.php'; ?>
// #file: about.php
<?php
require_once __DIR__ . '/inc/functions.php';
$title = 'من نحن';
require __DIR__ . '/inc/header.php';
?>
<h1>من نحن</h1>
<p>مكتبة صغيرة لمحبي القراءة.</p>
<?php require __DIR__ . '/inc/footer.php'; ?>
```

الصفحتان تشتركان في نفس الرأس والتذييل، والعنوان `$title` يختلف:

```text output
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>الرئيسية - مكتبتي</title></head>
<body>
<nav><a href="index.php">الرئيسية</a> | <a href="about.php">من نحن</a></nav>
<main>
<h1>أهلًا بك في مكتبتي</h1>
</main>
<footer>جميع الحقوق محفوظة</footer>
</body>
</html>

<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>من نحن - مكتبتي</title></head>
<body>
<nav><a href="index.php">الرئيسية</a> | <a href="about.php">من نحن</a></nav>
<main>
<h1>من نحن</h1>
<p>مكتبة صغيرة لمحبي القراءة.</p>
</main>
<footer>جميع الحقوق محفوظة</footer>
</body>
</html>
```

لاحظ ثلاثة أشياء:

1. المتغير `$title` المعرّف في الصفحة **مرئي** داخل `header.php`، لأن التضمين ليس دالة؛ الملف يُلصق في نفس المكان.
2. الآن تعديل القائمة في `header.php` يغيّر كل الصفحات مرة واحدة.
3. استخدمنا `__DIR__` (مسار مجلد الملف الحالي) لبناء المسار.

## لماذا __DIR__ ؟

المسار النسبي `require 'inc/header.php'` يُحسب من **مجلد العمل الحالي**، وقد يختلف حسب الصفحة التي بدأ منها الطلب (مثلًا صفحة داخل مجلد فرعي `admin/`). أما `__DIR__ . '/inc/header.php'` فيبدأ دائمًا من مجلد الملف الذي كُتب فيه السطر، فلا ينكسر:

```php run
// #file: main.php
<?php
require __DIR__ . '/lib/paths.php';
echo show_dir(), "\n";
// #file: lib/paths.php
<?php
function show_dir(): string
{
    return basename(__DIR__);   // اسم مجلد هذا الملف
}
```

```text output
lib
```

## مجلد public: ما يراه الزائر فقط

في المواقع الحقيقية نفصل الملفات إلى جزأين:

```text
MySite/
├── app/            ← الدوال والإعدادات وكلمات سر قاعدة البيانات (لا يصلها المتصفح)
│   ├── bootstrap.php
│   └── views/header.php
├── data/           ← قاعدة البيانات
└── public/         ← جذر الموقع (Web root): الصفحات والصور و CSS فقط
    ├── index.php
    └── css/site.css
```

ثم من **Site > Site Settings...** نجعل **Web root** هو `public`. بهذا لا يستطيع أحد أن يطلب `/app/config.php` من المتصفح. والصفحة داخل `public` تصل للمجلد الأعلى هكذا: `require __DIR__ . '/../app/bootstrap.php';`

هذا بالضبط تنظيم القالب **PHP + SQLite Data App** في الـ IDE، وتنظيم أطر العمل مثل Laravel وCodeIgniter.

## أخطاء شائعة

- **`Failed opening required`:** المسار خطأ. اطبع `__DIR__` لتعرف أين أنت، واستخدمه في المسار.
- **`Cannot redeclare function`:** ضمّنت ملف الدوال مرتين بـ `require`. استخدم `require_once`.
- **مسافة أو سطر قبل `<?php` في ملف الدوال:** تُطبع في الصفحة وتمنع لاحقًا إرسال الترويسات (`headers already sent`) عند استخدام الجلسات أو التحويل. اجعل `<?php` أول شيء في الملف.

## تمارين

### تمرين 1: ملف ثوابت

أنشئ ملف `settings.php` فيه ثابتان `APP_NAME = "مدونتي"` و`APP_VERSION = "1.0"`، وضمّنه في `main.php` واطبع `مدونتي (1.0)`.

```php exercise
// #file: main.php
<?php
// require_once ...
// #file: settings.php
<?php
```

```php solution
// #file: main.php
<?php
require_once __DIR__ . '/settings.php';
echo APP_NAME . " (" . APP_VERSION . ")\n";
// #file: settings.php
<?php
const APP_NAME = "مدونتي";
const APP_VERSION = "1.0";
```

```text output
مدونتي (1.0)
```

### تمرين 2: صفحة جديدة بالقالب

صفحة `contact.php` تستخدم نفس الرأس البسيط `inc/top.php` (يطبع `<h1>` بالعنوان) وتطبع تحته `<p>راسلنا</p>`.

<!-- test: {"requests": [{"path": "/contact.php"}]} -->
```php web exercise
// #file: inc/top.php
<h1><?= htmlspecialchars($title) ?></h1>
// #file: contact.php
<?php
$title = 'اتصل بنا';
?>
<p>راسلنا</p>
```

<!-- test: {"requests": [{"path": "/contact.php"}]} -->
```php web solution
// #file: inc/top.php
<h1><?= htmlspecialchars($title) ?></h1>
// #file: contact.php
<?php
$title = 'اتصل بنا';
require __DIR__ . '/inc/top.php';
?>
<p>راسلنا</p>
```

```text output
<h1>اتصل بنا</h1>
<p>راسلنا</p>
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين require و include إذا لم يوجد الملف؟", "choices": ["لا فرق", "require يوقف البرنامج بخطأ، و include يعطي تحذيرًا ويكمل", "include يوقف البرنامج", "كلاهما يتجاهل الخطأ"], "answer": 1, "explanation": "require للملفات الضرورية: غيابها خطأ قاتل."}
```

```quiz
{"question": "لماذا نكتب __DIR__ في مسار التضمين؟", "choices": ["للزينة", "ليبدأ المسار من مجلد الملف نفسه فلا ينكسر", "لتسريع PHP", "لأنه إلزامي"], "answer": 1, "explanation": "__DIR__ مسار مجلد الملف الحالي، فالمسار يصح من أي صفحة بدأ الطلب."}
```

```quiz
{"question": "ما فائدة جعل Web root هو مجلد public؟", "choices": ["الملفات خارجه (الإعدادات وقاعدة البيانات) لا يصلها المتصفح", "يجعل الموقع أسرع", "يغيّر لغة الموقع", "لا فائدة"], "answer": 0, "explanation": "الزائر يستطيع طلب ما داخل جذر الموقع فقط."}
```

## الخلاصة

- `require_once` لملفات الدوال والإعدادات، و`require` لأجزاء القالب.
- القالب المشترك (header / footer) يوفّر التكرار ويوحّد شكل الموقع.
- ابنِ المسارات بـ `__DIR__`.
- ضع الصفحات فقط في `public`، والباقي خارجه.
