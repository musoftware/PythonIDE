# الدرس 2: التشغيل وأدوات Laravel في الـ IDE

**في هذا الدرس ستتعلم:**

- تشغيل تطبيق Laravel في **Preview** ومراقبة **Requests**.
- قائمة **Laravel** في شريط القوائم وما فيها.
- **لوحة Laravel**: تبويبات Artisan و Routes و Tinker و Output.
- أوامر **الزر الأيمن** في Solution Explorer التي تتغير حسب المجلد.
- **لوحة الأوامر** (Command Palette) وشريط **أوامر المشروع**.

## التشغيل

مشروع Laravel في RAD IDE موقع PHP عادي، فكل ما تعلمته في دورة PHP يعمل هنا:

- **Ctrl+F5** (أو **Site > Run Site in Preview**): تشغّل الـ IDE خادم PHP المدمج على مجلد `public` مع **موجّه Laravel** (`server.php`)، وتفتح **Preview**. ونافذة **Requests** تسجل كل طلب: `GET /`، وملفات CSS و JS، وطلبات النماذج.
- **F5**: نفس الشيء **مع Xdebug** لتتوقف عند نقاط التوقف في المتحكمات والنماذج وحتى قوالب Blade (الدرس 9).
- **التحديث المباشر**: عدّل قالبًا أو متحكمًا واحفظ، فتتحدّث المعاينة.

> **ماذا عن `php artisan serve`؟** لا تحتاجه داخل الـ IDE: الأمر **Serve** في قائمة Laravel يشغّل الموقع بخادم الـ IDE نفسه (مع Requests والتحديث المباشر). وخارج الـ IDE يبقى `php artisan serve` هو الطريقة المعتادة.

## قائمة Laravel

عندما يكون المشروع المفتوح مشروع Laravel تظهر في شريط القوائم قائمة جديدة اسمها **Laravel** (بعد قائمة Project)، وفيها:

| الأمر | وظيفته |
|---|---|
| **Serve** (تشغيل الموقع) | تشغيل الموقع في المعاينة |
| **Tinker** | سطر أوامر PHP داخل تطبيقك (الدرس 6) |
| **Route List** (قائمة المسارات) | كل المسارات في تبويب Routes |
| **Generate App Key (key:generate)** | توليد `APP_KEY` |
| **Link Storage (storage:link)** | ربط `storage/app/public` بـ `public/storage` للملفات المرفوعة |
| **Run Scheduled Tasks (schedule:run)** | تشغيل المهام المجدولة مرة |
| **Start Queue Worker (queue:work)** | تشغيل عامل الطابور (وإيقافه بنفس الأمر) |
| **Regenerate IDE Helper Files** | تحديث ملفات IntelliSense |
| **Make** (إنشاء) ▸ | كل مولّدات `make:*`: متحكم، نموذج، ترحيل، قالب Blade، طلب نموذج، Middleware، سياسة، حدث، وظيفة، بريد... |
| **Database** (قاعدة البيانات) ▸ | **Migrate**، **Rollback**، **Migration Status**، **Fresh Database + Seed**، **Seed (db:seed)**، **Run Seeder...** |
| **Cache** (الذاكرة المؤقتة) ▸ | **Clear All Caches (optimize:clear)** و`config:clear` و`route:cache` ... |
| **Tests** (الاختبارات) ▸ | **New Test...** و**Run Tests** |
| **Composer** ▸ و **npm** ▸ | `composer install/update/require` وسكربتات `npm run ...` |

كل أمر يشغّل `php artisan ...` المناسب بنسخة PHP الخاصة بموقعك، ويظهر الناتج في نافذة **Output**. والأوامر التي تنشئ ملفًا (مثل **New Controller...**) تعرض نافذة صغيرة للاسم والخيارات، ثم **تفتح الملف الجديد في المحرر** مباشرة.

## لوحة Laravel

افتحها من **View > Laravel Panel (Artisan, Routes, Tinker)** (عرض > لوحة Laravel). تظهر في أسفل الشاشة بجوار Output، وفيها:

- **Artisan**: قائمة **بكل** أوامر `artisan` في مشروعك (بما فيها أوامر الحزم التي ثبّتها). اختر أمرًا فتظهر **استمارة** لمعاملاته وخياراته مع شرح كل خيار، ثم شغّله. لا حاجة لحفظ الأوامر وخياراتها!
- **Routes**: جدول المسارات بأعمدة **Method** و**URI** و**Name** و**Action** و**Middleware**. **انقر مرتين** على مسار لتفتح دالة المتحكم الخاصة به. وبالزر الأيمن: **Open in Preview** (لمسارات GET)، و**Copy route('name')**، و**Copy URI**.
- **Tinker**: سطر أوامر تفاعلي داخل تطبيقك (الدرس 6)، مع زر **Restart**.
- **Output**: ناتج الأوامر.

وفي أعلاها أزرار: **Install Dependencies** (التجهيز الكامل)، و**Migrate**، و**IDE Helper**، و**Refresh** (إعادة قراءة الأوامر والمسارات).

## الزر الأيمن في Solution Explorer: أوامر حسب المكان

هنا أكثر ما يوفّر وقتك: **أوامر الزر الأيمن تتغير حسب المجلد أو الملف الذي تنقر عليه**، وتظهر في أعلى القائمة:

| تنقر بالزر الأيمن على | تظهر لك |
|---|---|
| `app/Http/Controllers` | **New Controller...** (متحكم جديد...) بخيارات `--resource` و`--api` و`--model` |
| `app/Models` | **New Model...** (نموذج جديد...) بخيارات: ترحيل `-m`، متحكم `-c`، Factory `-f`، Seeder `-s`، متحكم موارد `-r` |
| `database/migrations` | **New Migration...** و**Migrate** و**Rollback** و**Migration Status** |
| ملف ترحيل | **Run This Migration** (تشغيل هذا الترحيل) و**Rollback This Migration** |
| `resources/views` | **New Blade View...** (قالب Blade جديد...) و**New Component...** |
| ملف `.blade.php` | **Open the Controller That Renders It** (فتح المتحكم الذي يعرض هذا القالب) |
| ملف نموذج في `app/Models` | **Open Migration** و**Open Controller** و**Open Factory** |
| `routes` أو ملف مسارات | **Route List** و`route:cache` و`route:clear` |
| `tests` أو ملف اختبار | **New Test...** و**Run Tests** / **Run This Test** |
| `config` | `config:clear` و`config:cache` |
| جذر المشروع | Serve و Tinker و Route List والمفاتيح والذاكرة المؤقتة وقاعدة البيانات |

والمولّد يعرف المجلد الفرعي: إذا نقرت على `app/Http/Controllers/Admin` يقترح الاسم `Admin/PostController` فيُنشأ المتحكم في المكان الصحيح بالـ namespace الصحيح.

## لوحة الأوامر وشريط أوامر المشروع

- **لوحة الأوامر** (**Command Palette...**): اكتب `Laravel:` لترى أوامر مثل **Laravel: Run Artisan Command...** و**Laravel: Show Routes** و**Laravel: Open Tinker** و**Laravel: make:model -mcr** و**Laravel: Generate IDE Helper Files**، وكل أوامر قائمة Laravel أيضًا.
- شريط أدوات **Project Actions** (أوامر المشروع): أزرار سريعة لأكثر الأوامر استخدامًا (Serve و Tinker و Route List و Migrate) وزر إيقاف.

## كيف يصل الطلب إلى الكود؟

عندما تطلب `/books` يمر الطلب بخطوات ثابتة. المحاكاة التالية بـ PHP عادية تبيّن الفكرة (Laravel يفعلها بشكل أذكى بكثير):

```php run
<?php
// 1) المسارات: طريقة + عنوان => من يعالج
$routes = [
    "GET /" => fn() => "الصفحة الرئيسية",
    "GET /books" => fn() => "قائمة الكتب",
    "POST /books" => fn() => "تم حفظ كتاب",
];

// 2) النواة: تبحث عن المسار وتستدعيه، أو 404
function handle(array $routes, string $method, string $uri): string
{
    $key = "$method $uri";
    if (!isset($routes[$key])) {
        return "404 | Not Found";
    }
    return "200 | " . $routes[$key]();
}

echo handle($routes, "GET", "/books"), "\n";
echo handle($routes, "POST", "/books"), "\n";
echo handle($routes, "GET", "/authors"), "\n";
```

```text output
200 | قائمة الكتب
200 | تم حفظ كتاب
404 | Not Found
```

في Laravel: `public/index.php` يستقبل كل الطلبات، ثم تمر بالـ **Middleware** (الجلسات، و CSRF...)، ثم **المسار** المطابق في `routes/web.php`، ثم **المتحكم**، ثم يُرسل **الرد**. وكل طلب تراه في نافذة **Requests**.

## اختبر نفسك

```quiz
{"question": "أين تجد قائمة بكل أوامر artisan مع استمارة لخياراتها؟", "choices": ["Laravel Panel > تبويب Artisan", "Help > About", "Toolbox", "Site Settings"], "answer": 0, "explanation": "تبويب Artisan في لوحة Laravel يعرض كل الأوامر ويبني استمارة لمعاملات الأمر المختار."}
```

```quiz
{"question": "ماذا يحدث عند النقر مرتين على مسار في تبويب Routes؟", "choices": ["يُحذف المسار", "تُفتح دالة المتحكم الخاصة به في المحرر", "يُنشر الموقع", "لا شيء"], "answer": 1, "explanation": "النقر المزدوج ينقلك إلى كود المسار مباشرة."}
```

```quiz
{"question": "تريد إنشاء نموذج مع ترحيله ومتحكمه. أين تنقر بالزر الأيمن؟", "choices": ["على مجلد public", "على مجلد app/Models ثم New Model... مع -m و -c", "على ملف .env", "على مجلد vendor"], "answer": 1, "explanation": "أوامر الزر الأيمن تتغير حسب المجلد؛ app/Models تعرض New Model... بخياراته."}
```

## الخلاصة

- **Ctrl+F5** للتشغيل في Preview، و**F5** مع Xdebug.
- قائمة **Laravel** فيها Serve و Tinker و Route List وقوائم Make و Database و Cache و Tests و Composer و npm.
- **لوحة Laravel**: Artisan بالاستمارات، و Routes بالنقر المزدوج للكود، و Tinker.
- **الزر الأيمن** في Solution Explorer يعرض المولّدات والأوامر المناسبة لكل مجلد وملف.
