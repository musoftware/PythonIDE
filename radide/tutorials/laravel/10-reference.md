# الدرس 10: مرجع سريع: الأوامر والمصطلحات

صفحة واحدة ترجع إليها كلما نسيت أين يوجد أمر أو ماذا تعني كلمة. أوامر القوائم مكتوبة بالإنجليزية كما تظهر في الـ IDE، ومعها اسمها في الواجهة العربية.

## أين أجد ماذا في الـ IDE؟

| English (كما في القوائم) | الاسم في الواجهة العربية | الوظيفة |
|---|---|---|
| File > New Project... > Web > PHP Web Site > Laravel App | ملف > مشروع جديد... > ويب > موقع ويب PHP > Laravel App | إنشاء مشروع Laravel جاهز (الدرس 1) |
| Ctrl+F5 / Site > Run Site in Preview | الموقع > تشغيل الموقع في المعاينة | تشغيل الموقع بخادم الـ IDE وفتح Preview |
| F5 | بدء تصحيح الأخطاء | التشغيل مع Xdebug ونقاط التوقف (الدرس 9) |
| Laravel > Serve | Laravel > تشغيل الموقع (Serve) | مثل Ctrl+F5 من قائمة Laravel |
| Laravel > Tinker | Laravel > Tinker | سطر أوامر PHP داخل تطبيقك (الدرس 6) |
| Laravel > Route List | Laravel > قائمة المسارات | جدول المسارات في تبويب Routes |
| Laravel > Make ▸ | Laravel > إنشاء ▸ | كل مولّدات `make:*` |
| Laravel > Database ▸ Migrate / Rollback / Migration Status | Laravel > قاعدة البيانات ▸ تطبيق الترحيلات / تراجع (Rollback) / حالة الترحيلات | التحكم في الترحيلات (الدرس 5) |
| Laravel > Cache ▸ Clear All Caches (optimize:clear) | Laravel > الذاكرة المؤقتة ▸ | مسح الذاكرة المؤقتة للإعدادات والمسارات والقوالب |
| Laravel > Tests ▸ Run Tests | Laravel > الاختبارات ▸ | تشغيل اختبارات PHPUnit / Pest |
| View > Laravel Panel (Artisan, Routes, Tinker) | عرض > لوحة Laravel | تبويبات Artisan و Routes و Tinker و Output (الدرس 2) |
| الزر الأيمن في Solution Explorer (مستكشف الحلول) | | أوامر تتغير حسب المجلد: New Controller... و New Model... و New Migration... |
| View > Databases | عرض > قواعد البيانات | الجداول والبيانات والاستعلامات والمخطط |
| F12 / Ctrl+نقر | الانتقال إلى التعريف | من `'books.index'` إلى القالب أو المسار (الدرس 8) |
| Site > Publish... | الموقع > نشر... | رفع الموقع (الدرس 9) |

## أوامر Artisan التي تكررت في الدليل

| الأمر | الوظيفة | من أين في الـ IDE |
|---|---|---|
| `php artisan make:controller BookController --resource` | متحكم موارد بسبع دوال | الزر الأيمن على `app/Http/Controllers` > **New Controller...** |
| `php artisan make:model Book -mcr` | نموذج + ترحيل + متحكم موارد | الزر الأيمن على `app/Models` > **New Model...** |
| `php artisan make:migration create_books_table` | ترحيل جديد | الزر الأيمن على `database/migrations` > **New Migration...** |
| `php artisan migrate` | تطبيق الترحيلات الجديدة | **Laravel > Database > Migrate** |
| `php artisan migrate:rollback` | التراجع عن آخر دفعة | **Rollback** |
| `php artisan migrate:fresh --seed` | حذف كل الجداول وإعادة بنائها بالبيانات الأولية | **Fresh Database + Seed** (جهاز التطوير فقط!) |
| `php artisan db:seed` | تشغيل الـ Seeders | **Seed (db:seed)** |
| `php artisan route:list` | قائمة المسارات | تبويب **Routes** |
| `php artisan tinker` | تجربة الكود | تبويب **Tinker** |
| `php artisan make:request StoreBookRequest` | صنف تحقق مستقل | **Make > New Form Request...** |
| `php artisan test` | تشغيل الاختبارات | **Tests > Run Tests** |
| `php artisan optimize:clear` | مسح كل الذاكرة المؤقتة | **Cache > Clear All Caches** |

لا تحتاج حفظ أي أمر: تبويب **Artisan** في لوحة Laravel يعرض كل الأوامر مع استمارة لخياراتها.

## مثال أخير: سبع عمليات متحكم الموارد

هذه المحاكاة تطبع جدول المسارات السبعة التي يولدها `Route::resource('books', BookController::class)`، وهو نفس ما تراه في تبويب **Routes**:

```php run
<?php
$resource = "books";
$routes = [
    ["GET",    "/$resource",             "index",   "قائمة الكل"],
    ["GET",    "/$resource/create",      "create",  "نموذج إضافة"],
    ["POST",   "/$resource",             "store",   "حفظ الجديد"],
    ["GET",    "/$resource/{book}",      "show",    "عرض واحد"],
    ["GET",    "/$resource/{book}/edit", "edit",    "نموذج تعديل"],
    ["PUT",    "/$resource/{book}",      "update",  "حفظ التعديل"],
    ["DELETE", "/$resource/{book}",      "destroy", "حذف"],
];
foreach ($routes as [$method, $uri, $action, $desc]) {
    printf("%-7s %-20s %s.%s\n", $method, $uri, $resource, $action);
}
echo count($routes), " مسارات من سطر واحد\n";
```

```text output
GET     /books               books.index
GET     /books/create        books.create
POST    /books               books.store
GET     /books/{book}        books.show
GET     /books/{book}/edit   books.edit
PUT     /books/{book}        books.update
DELETE  /books/{book}        books.destroy
7 مسارات من سطر واحد
```

## قاموس المصطلحات

| English | العربية | شرح مختصر |
|---|---|---|
| Framework | إطار عمل | هيكل جاهز وقواعد تبني عليها تطبيقك بدل البدء من الصفر |
| Artisan | أرتيزان | أداة سطر الأوامر في Laravel (`php artisan ...`) |
| Route | مسار | ربط طريقة وعنوان (`GET /books`) بالكود الذي يعالجه |
| Named route | مسار مسمّى | مسار له اسم تولّد عنوانه بـ `route('books.index')` |
| Controller | متحكم | صنف يستقبل الطلب ويقرر ماذا يُعرض |
| Resource controller | متحكم موارد | متحكم بالدوال السبع لعمليات CRUD |
| Middleware | وسيط | كود يمر به الطلب قبل المتحكم (الجلسة، CSRF، تسجيل الدخول) |
| View / Blade template | قالب / قالب Blade | ملف `.blade.php` يولّد HTML |
| Layout | تخطيط | قالب مشترك بـ `@extends` و`@section` و`@yield` |
| Component | مكوّن | قطعة قالب قابلة لإعادة الاستخدام `<x-alert>` |
| Migration | ترحيل | ملف PHP يبني جدولًا أو يعدّله، ويمكن التراجع عنه |
| Seeder / Factory | بيانات أولية / مصنع | ملء قاعدة البيانات ببيانات ثابتة / عشوائية للتجربة |
| Model (Eloquent) | نموذج | صنف يمثل جدولًا؛ كل كائن منه صف |
| Mass assignment / `$fillable` | الإسناد الجماعي | الأعمدة المسموح ملؤها من مصفوفة واحدة |
| Relationship | علاقة | `hasMany` و`belongsTo` بين النماذج |
| Route model binding | ربط النموذج بالمسار | Laravel يجلب `{book}` من قاعدة البيانات تلقائيًا |
| Validation | التحقق | فحص المدخلات بقواعد مثل `required` و`max:200` |
| Form Request | طلب نموذج | صنف مستقل لقواعد التحقق |
| Flash message | رسالة فلاش | رسالة في الجلسة تظهر في الطلب التالي فقط |
| CSRF token | رمز CSRF | قيمة سرية في كل نموذج (`@csrf`) تمنع الطلبات المزوّرة |
| Tinker | تينكر | سطر أوامر تفاعلي داخل التطبيق |
| `.env` | ملف البيئة | إعدادات الجهاز: قاعدة البيانات و`APP_DEBUG` و`APP_KEY` |
| Breakpoint | نقطة توقف | سطر يتوقف عنده التنفيذ أثناء التصحيح |
| Feature test | اختبار وظيفي | اختبار يزور صفحات التطبيق ويتحقق من الرد |

## اختبر نفسك

```quiz
{"question": "أي أمر ينشئ النموذج مع ترحيله ومتحكم موارد معًا؟", "choices": ["php artisan make:model Book -mcr", "php artisan migrate", "php artisan route:list", "php artisan tinker"], "answer": 0, "explanation": "الخيارات -m (ترحيل) و-c (متحكم) و-r (متحكم موارد) تنشئ كل الملفات المرتبطة بالنموذج دفعة واحدة."}
```

```quiz
{"question": "لماذا لا تستخدم Fresh Database + Seed على الخادم الحقيقي؟", "choices": ["لأنه بطيء", "لأنه يحذف كل الجداول وبياناتها ثم يعيد بناءها", "لأنه لا يعمل مع SQLite", "لأنه يحتاج Xdebug"], "answer": 1, "explanation": "migrate:fresh يحذف كل الجداول؛ مناسب لجهاز التطوير فقط."}
```

```quiz
{"question": "ما وظيفة Middleware؟", "choices": ["رسم الجداول", "كود يمر به الطلب قبل المتحكم، مثل التحقق من تسجيل الدخول", "تحويل Blade إلى PHP", "نشر الموقع"], "answer": 1, "explanation": "الوسيط يفحص الطلب أو يعدّله قبل وصوله للمتحكم (الجلسات، CSRF، auth)."}
```

## الخلاصة

- قائمة **Laravel** ولوحة **Laravel** والزر الأيمن في **Solution Explorer** تغنيك عن كتابة أوامر Artisan.
- **F12** على أسماء المسارات والقوالب، و**F5** للتصحيح، و**Databases** لرؤية البيانات.
- عند أي كلمة لا تتذكرها ارجع إلى القاموس أعلاه أو إلى قاموس دورة PHP.
