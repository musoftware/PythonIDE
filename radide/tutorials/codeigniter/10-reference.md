# الدرس 10: مرجع سريع: الأوامر والمصطلحات

صفحة واحدة ترجع إليها كلما نسيت أين يوجد أمر أو ماذا تعني كلمة. أوامر القوائم مكتوبة بالإنجليزية كما تظهر في الـ IDE، ومعها اسمها في الواجهة العربية.

## أين أجد ماذا في الـ IDE؟

| English (كما في القوائم) | الاسم في الواجهة العربية | الوظيفة |
|---|---|---|
| File > New Project... > Web > PHP Web Site > CodeIgniter 4 App | ملف > مشروع جديد... > ويب > موقع ويب PHP > CodeIgniter 4 App | إنشاء مشروع جاهز بقاعدة SQLite3 أو MariaDB أو PostgreSQL (الدرس 1) |
| File > Open Folder... | ملف > فتح مجلد... | فتح مشروع موجود، مع `composer install` وإنشاء قاعدة البيانات |
| Ctrl+F5 / Site > Run Site in Preview | الموقع > تشغيل الموقع في المعاينة | تشغيل الموقع بخادم الـ IDE وفتح Preview |
| F5 | بدء تصحيح الأخطاء / متابعة | التشغيل مع Xdebug ونقاط التوقف (الدرس 9) |
| CodeIgniter > Serve | CodeIgniter > تشغيل الموقع (Serve) | مثل Ctrl+F5 من قائمة CodeIgniter |
| CodeIgniter > Routes | CodeIgniter > المسارات | جدول المسارات في لوحة CodeIgniter |
| CodeIgniter > Make ▸ | CodeIgniter > إنشاء ▸ | كل مولّدات `make:*` و**New View...** |
| CodeIgniter > Database ▸ Migrate / Rollback / Migration Status | قاعدة البيانات ▸ تطبيق الترحيلات / تراجع (Rollback) / حالة الترحيلات | التحكم في الترحيلات (الدرس 5) |
| CodeIgniter > Database ▸ Run Seeder (db:seed)... | تشغيل Seeder (db:seed)... | البيانات الأولية |
| CodeIgniter > Clear Cache (cache:clear) | مسح الذاكرة المؤقتة (cache:clear) | مسح الذاكرة المؤقتة |
| CodeIgniter > Show Environment (env) | عرض البيئة (env) | `development` أم `production`؟ |
| View > CodeIgniter Panel (Spark, Routes) | عرض > لوحة CodeIgniter (Spark، المسارات) | تبويبات Spark و Routes و Output (الدرس 2) |
| الزر الأيمن في Solution Explorer (مستكشف الحلول) | | أوامر حسب المجلد: New Controller... و New Model... و New Migration... و Run This Seeder |
| Command Palette... | لوحة الأوامر... | اكتب `CodeIgniter:` |
| View > Databases | عرض > قواعد البيانات | الجداول والبيانات والاستعلامات والمخطط |
| F12 / Ctrl+نقر | الانتقال إلى التعريف | من `'products/index'` إلى القالب، ومن `'Products::edit/$1'` إلى الدالة (الدرس 8) |
| View > Terminal | عرض > الطرفية | تشغيل `php vendor/bin/phpunit` وأي أمر آخر |
| Site > Publish... | الموقع > نشر... | رفع الموقع (الدرس 9) |

## أوامر Spark التي تكررت في الدليل

| الأمر | الوظيفة | من أين في الـ IDE |
|---|---|---|
| `php spark make:controller Products` | متحكم جديد (`--restful` لمتحكم موارد) | الزر الأيمن على `app/Controllers` > **New Controller...** |
| `php spark make:model ProductModel --table products` | نموذج جديد | الزر الأيمن على `app/Models` > **New Model...** |
| `php spark make:migration CreateProductsTable` | ترحيل جديد | الزر الأيمن على `app/Database/Migrations` > **New Migration...** |
| `php spark make:seeder ProductSeeder` | Seeder جديد | الزر الأيمن على `app/Database/Seeds` > **New Seeder...** |
| `php spark make:filter AuthFilter` | مرشح (مثل التحقق من تسجيل الدخول) | الزر الأيمن على `app/Filters` > **New Filter...** |
| `php spark migrate --all` | تطبيق الترحيلات الجديدة | **Migrate** |
| `php spark migrate:rollback` | التراجع عن آخر دفعة | **Rollback** |
| `php spark migrate:status` | حالة الترحيلات | **Migration Status** |
| `php spark db:seed ProductSeeder` | تشغيل Seeder | **Run This Seeder** |
| `php spark routes` | قائمة المسارات | تبويب **Routes** |
| `php spark cache:clear` | مسح الذاكرة المؤقتة | **Clear Cache (cache:clear)** |
| `php spark list` | كل الأوامر | تبويب **Spark** |

لا تحتاج حفظ أي أمر: تبويب **Spark** في لوحة CodeIgniter يعرض كل الأوامر مع استمارة لخياراتها.

## مثال أخير: مسارات presenter

هذه المحاكاة تطبع جدول المسارات التي يولدها `$routes->presenter('products')`، وهو نفس ما تراه في تبويب **Routes**:

```php run
<?php
$name = 'products';
$routes = [
    ['GET',  "$name",               'index'],
    ['GET',  "$name/show/(:num)",   'show/$1'],
    ['GET',  "$name/new",           'new'],
    ['POST', "$name/create",        'create'],
    ['GET',  "$name/edit/(:num)",   'edit/$1'],
    ['POST', "$name/update/(:num)", 'update/$1'],
    ['GET',  "$name/remove/(:num)", 'remove/$1'],
    ['POST', "$name/delete/(:num)", 'delete/$1'],
];
$controller = ucfirst($name);
foreach ($routes as [$method, $uri, $action]) {
    printf("%-5s %-24s %s::%s\n", $method, $uri, $controller, $action);
}
echo count($routes), " مسارات من سطر واحد\n";
```

```text output
GET   products                 Products::index
GET   products/show/(:num)     Products::show/$1
GET   products/new             Products::new
POST  products/create          Products::create
GET   products/edit/(:num)     Products::edit/$1
POST  products/update/(:num)   Products::update/$1
GET   products/remove/(:num)   Products::remove/$1
POST  products/delete/(:num)   Products::delete/$1
8 مسارات من سطر واحد
```

## قاموس المصطلحات

| English | العربية | شرح مختصر |
|---|---|---|
| Framework | إطار عمل | هيكل جاهز وقواعد تبني عليها تطبيقك بدل البدء من الصفر |
| MVC | نموذج - قالب - متحكم | تقسيم الكود إلى بيانات وعرض ومنطق |
| Spark | سبارك | أداة سطر الأوامر في CodeIgniter (`php spark ...`) |
| Route | مسار | ربط طريقة وعنوان (`GET products`) بدالة متحكم |
| Placeholder | عنصر نائب | جزء متغير في المسار: `(:num)` و`(:segment)` و`(:any)` |
| Named route | مسار مسمّى | مسار له اسم تولّد عنوانه بـ `url_to('products.index')` |
| Route group | مجموعة مسارات | مسارات لها بادئة ومرشحات مشتركة |
| Controller | متحكم | صنف يستقبل الطلب ويقرر ماذا يحدث |
| Filter | مرشح | كود يمر به الطلب قبل المتحكم أو بعده (`auth` و`csrf`) |
| View | قالب | ملف في `app/Views` يولّد HTML |
| Layout / Section | تخطيط / فتحة | `extend` و`section` و`renderSection` |
| View Cell | خلية عرض | قطعة قالب لها منطقها الخاص |
| Helper | مساعد | ملف دوال جاهزة: `form` و`url` و`text` |
| Migration | ترحيل | ملف PHP يبني جدولًا أو يعدّله، ويمكن التراجع عنه |
| Forge | الحدّاد | أداة بناء الجداول داخل الترحيلات |
| Batch | دفعة | مجموعة الترحيلات التي طُبقت في Migrate واحد |
| Seeder | بيانات أولية | ملء قاعدة البيانات ببيانات ثابتة أو تجريبية |
| Model | نموذج | صنف يمثل جدولًا: `find` و`insert` و`update` و`delete` |
| `$allowedFields` | الأعمدة المسموحة | قائمة بيضاء للأعمدة التي يُسمح بكتابتها |
| Query Builder | باني الاستعلامات | بناء SQL بالدوال مع استعلامات مُجهّزة |
| Entity | كيان | كائن يمثل صفًا وله دوال |
| Validation rules | قواعد التحقق | قواعد مثل `required` و`min_length[3]` و`decimal` يفصلها خط عمودي |
| Flash data | رسالة فلاش | قيمة في الجلسة تظهر في الطلب التالي فقط |
| CSRF token | رمز CSRF | قيمة سرية في كل نموذج تمنع الطلبات المزوّرة |
| Debug Toolbar | شريط التصحيح | شريط في `development` يعرض الاستعلامات والقوالب والوقت |
| Environment | البيئة | `development` أو `production` في `CI_ENVIRONMENT` |
| `.env` | ملف البيئة | إعدادات الجهاز: قاعدة البيانات و`app.baseURL` |
| Breakpoint | نقطة توقف | سطر يتوقف عنده التنفيذ أثناء التصحيح |

## اختبر نفسك

```quiz
{"question": "أي أمر يتراجع عن آخر دفعة من الترحيلات؟", "choices": ["php spark migrate --all", "php spark migrate:rollback", "php spark db:seed", "php spark routes"], "answer": 1, "explanation": "migrate:rollback (الأمر Rollback في القوائم) يتراجع عن آخر دفعة."}
```

```quiz
{"question": "ما وظيفة المرشح (Filter) في CodeIgniter؟", "choices": ["رسم الجداول", "كود يمر به الطلب قبل المتحكم أو بعده، مثل التحقق من تسجيل الدخول أو CSRF", "ترجمة النصوص", "نشر الموقع"], "answer": 1, "explanation": "المرشحات مثل auth و csrf تفحص الطلب قبل وصوله للمتحكم."}
```

```quiz
{"question": "أين تجد كل أوامر spark مع استمارة لخياراتها؟", "choices": ["Help > About", "تبويب Spark في لوحة CodeIgniter", "Site Settings", "Toolbox"], "answer": 1, "explanation": "تبويب Spark يعرض php spark list، والنقر المزدوج يفتح استمارة الأمر."}
```

## الخلاصة

- قائمة **CodeIgniter** ولوحة **CodeIgniter** والزر الأيمن في **Solution Explorer** تغنيك عن كتابة أوامر Spark.
- **F12** على أسماء القوالب والمسارات، و**F5** للتصحيح، و**Databases** لرؤية البيانات.
- عند أي كلمة لا تتذكرها ارجع إلى القاموس أعلاه أو إلى قاموس دورة PHP.
