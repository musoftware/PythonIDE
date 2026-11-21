# الدرس 2: التشغيل وأدوات CodeIgniter في الـ IDE

**في هذا الدرس ستتعلم:**

- تشغيل الموقع في **Preview** ومراقبة **Requests**.
- قائمة **CodeIgniter** في شريط القوائم وما فيها.
- **لوحة CodeIgniter**: تبويبات Spark و Routes و Output، واستمارات أوامر Spark.
- أوامر **الزر الأيمن** في Solution Explorer التي تتغير حسب المجلد.
- **لوحة الأوامر** (Command Palette) وشريط **أوامر المشروع**.

## التشغيل

مشروع CodeIgniter في RAD IDE موقع PHP عادي، فكل ما تعلمته في دورة PHP يعمل هنا:

- **Ctrl+F5** (أو **Site > Run Site in Preview** - الموقع > تشغيل الموقع في المعاينة): تشغّل الـ IDE خادم PHP على مجلد `public` مع سكربت `rewrite.php` الخاص بـ CodeIgniter (نفس ما يفعله `php spark serve`)، وتفتح **Preview** (معاينة) على الصفحة الرئيسية.
- **F5**: نفس الشيء **مع Xdebug**، لتتوقف عند نقاط التوقف في المتحكمات والنماذج والقوالب (الدرس 9).
- نافذة **Requests** (الطلبات) تسجل كل طلب: `GET /`، وملفات CSS، وطلبات النماذج، مع رمز الحالة والوقت.
- **التحديث المباشر**: عدّل متحكمًا أو قالبًا واحفظ، فتتحدث المعاينة.

والـ IDE تضبط `app.baseURL` على عنوان خادمها تلقائيًا أثناء التشغيل، فتعمل الروابط التي تولدها `base_url()` و`site_url()` داخل المعاينة دون أن تعدّل `.env`.

## قائمة CodeIgniter

عندما يكون المشروع المفتوح مشروع CodeIgniter تظهر في شريط القوائم قائمة جديدة اسمها **CodeIgniter**، وفيها:

| الأمر | الاسم العربي | وظيفته |
|---|---|---|
| **Serve** | تشغيل الموقع (Serve) | تشغيل الموقع في المعاينة |
| **Routes** | المسارات | كل المسارات في تبويب Routes |
| **Make** ▸ | إنشاء ▸ | المولّدات: **New Controller...** و**New Model...** و**New Migration...** و**New Seeder...** و**New Filter...** و**New Entity...** و**New Command...** و**New Config...** و**New Validation...** و**New View Cell...** و**New View...** |
| **Database** ▸ | قاعدة البيانات ▸ | **Migrate** و**Rollback** و**Migration Status** و**Run Seeder (db:seed)...** |
| **Clear Cache (cache:clear)** | مسح الذاكرة المؤقتة | `php spark cache:clear` |
| **Show Environment (env)** | عرض البيئة (env) | هل الموقع في وضع `development` أم `production`؟ |
| **Composer** ▸ | Composer (حزم PHP) ▸ | `composer install` و`update` و`require` |

كل أمر يشغّل `php spark ...` المناسب بنسخة PHP الخاصة بموقعك، ويظهر الناتج في نافذة **Output** (المخرجات). والمولّدات تعرض نافذة صغيرة للاسم والخيارات، ثم **تفتح الملف الجديد في المحرر** مباشرة.

## لوحة CodeIgniter

افتحها من **View > CodeIgniter Panel (Spark, Routes)** (عرض > لوحة CodeIgniter) أو من قائمة **Site** (الموقع). تظهر أسفل الشاشة بجوار Output. في أعلاها اسم المشروع ونسخة CodeIgniter، وأزرار سريعة:

- **Migrate** و**Seed...** و**Controller...** و**Model...** و**Migration...**
- **More** (المزيد): `composer install` و`composer update`، و**Open .env**، و**Open app/Config/Routes.php**، و**Open Database in the Databases workspace**، و**Run a spark command...** لكتابة أي أمر بيدك.
- **Refresh**: إعادة قراءة الأوامر والمسارات.

وفيها ثلاثة تبويبات:

- **Spark**: **كل** أوامر `php spark list` مجمعة (Database و Generators و CodeIgniter وأوامرك الخاصة). **انقر مرتين** على أمر فتظهر **استمارة** مبنية من `php spark help` لهذا الأمر: خانة لكل معامل، ومربع اختيار أو قائمة لكل خيار، وفي أسفلها سطر الأمر الكامل الذي سيُنفذ. اضغط **Run**.
- **Routes**: جدول المسارات بأعمدة **Method** و**Route** و**Name** و**Handler** و**Filters**. **انقر مرتين** على مسار لتفتح دالة المتحكم الخاصة به. وبالزر الأيمن: **Go to Controller Method** و**Go to Routes.php** و**Open in Preview** (لمسارات GET).
- **Output**: ناتج الأوامر ورمز الخروج.

> **إذا ظهر «vendor/ is missing»:** المشروع بلا حزمه. اضغط **More > composer install**؛ Spark لا يعمل بدونها.

### كيف تبني الاستمارة سطر الأمر؟

الاستمارة تجمع ما اخترته في سطر واحد. هذه محاكاة صغيرة للفكرة:

```php run
<?php
function spark_line(string $command, array $args, array $options): string
{
    $parts = [$command];
    foreach ($args as $value) {
        if ($value !== '') {
            $parts[] = $value;
        }
    }
    foreach ($options as $name => $value) {
        if ($value === true) {
            $parts[] = $name;            // خيار مربع اختيار
        } elseif (is_string($value) && $value !== '') {
            $parts[] = $name;            // خيار له قيمة
            $parts[] = $value;
        }
    }
    return "php spark " . implode(' ', $parts);
}

echo spark_line('make:controller', ['Products'], ['--restful' => 'controller', '--force' => false]), "\n";
echo spark_line('make:model', ['ProductModel'], ['--table' => 'products', '--return' => 'entity']), "\n";
echo spark_line('migrate', [], ['--all' => true]), "\n";
```

```text output
php spark make:controller Products --restful controller
php spark make:model ProductModel --table products --return entity
php spark migrate --all
```

## الزر الأيمن في Solution Explorer: أوامر حسب المكان

هذا أكثر ما يوفر وقتك: **أوامر الزر الأيمن تتغير حسب المجلد أو الملف الذي تنقر عليه**، وتظهر في أعلى القائمة:

| تنقر بالزر الأيمن على | تظهر لك |
|---|---|
| `app/Controllers` | **New Controller...** (متحكم جديد...) بخيار `--restful` |
| `app/Models` | **New Model...** (نموذج جديد...) بخيارات `--table` و`--return`، و**New Entity...** |
| `app/Database/Migrations` | **New Migration...** و**Migrate** و**Rollback** و**Migration Status** |
| ملف ترحيل | **Migrate** |
| `app/Database/Seeds` | **New Seeder...** و**Run Seeder (db:seed)...** |
| ملف Seeder | **Run This Seeder** (تشغيل هذا الـ Seeder) |
| `app/Views` | **New View...** (قالب جديد...) بخانة للتخطيط، و**New View Cell...** |
| `app/Filters` و`app/Entities` و`app/Commands` و`app/Config` و`app/Validation` | المولّد المناسب لكل مجلد |
| `app/Config/Routes.php` | **Routes** |
| جذر المشروع | Serve و Routes وقائمة Database و Clear Cache |

والمولّد يعرف المجلد الفرعي: إذا نقرت على `app/Controllers/Admin` يقترح الاسم `Admin/Products` فيُنشأ المتحكم في المكان الصحيح بالـ namespace الصحيح `App\Controllers\Admin`.

## لوحة الأوامر وشريط أوامر المشروع

- **لوحة الأوامر** (**Command Palette...** - لوحة الأوامر...): اكتب `CodeIgniter:` لترى **CodeIgniter: Spark Commands** و**CodeIgniter: Show Routes** و**CodeIgniter: spark make:controller...** و**CodeIgniter: spark migrate...** وغيرها.
- شريط أدوات **Project Actions** (أوامر المشروع): أزرار سريعة **Serve** و**Routes** و**Migrate**.

## تمرين

دالة `spark_line` في المحاكاة لا تضع علامات تنصيص حول القيم التي فيها مسافات، فيصبح الأمر خطأ. عدّلها لتضع `"..."` حول أي جزء فيه مسافة (كما تفعل استمارة الـ IDE).

```php exercise
<?php
function spark_line(string $command, array $args): string
{
    $parts = array_merge([$command], $args);
    // ضع علامات التنصيص هنا
    return "php spark " . implode(' ', $parts);
}

echo spark_line('db:seed', ['ProductSeeder']), "\n";
echo spark_line('make:migration', ['Add Stock Column']), "\n";
```

```php solution
<?php
function spark_line(string $command, array $args): string
{
    $parts = array_merge([$command], $args);
    $parts = array_map(fn($p) => str_contains($p, ' ') ? "\"$p\"" : $p, $parts);
    return "php spark " . implode(' ', $parts);
}

echo spark_line('db:seed', ['ProductSeeder']), "\n";
echo spark_line('make:migration', ['Add Stock Column']), "\n";
```

```text output
php spark db:seed ProductSeeder
php spark make:migration "Add Stock Column"
```

## اختبر نفسك

```quiz
{"question": "أين تجد قائمة بكل أوامر spark مع استمارة لخياراتها؟", "choices": ["لوحة CodeIgniter > تبويب Spark", "Help > About", "Toolbox", "Site Settings"], "answer": 0, "explanation": "تبويب Spark يعرض كل أوامر php spark list، والنقر المزدوج يفتح استمارة الأمر."}
```

```quiz
{"question": "ماذا يحدث عند النقر مرتين على مسار في تبويب Routes؟", "choices": ["يُحذف المسار", "تُفتح دالة المتحكم الخاصة به في المحرر", "يُنشر الموقع", "لا شيء"], "answer": 1, "explanation": "النقر المزدوج ينقلك إلى الدالة التي تعالج المسار."}
```

```quiz
{"question": "تريد إنشاء Seeder جديد. أين تنقر بالزر الأيمن؟", "choices": ["على public", "على app/Database/Seeds ثم New Seeder...", "على vendor", "على .env"], "answer": 1, "explanation": "أوامر الزر الأيمن تتغير حسب المجلد؛ app/Database/Seeds تعرض New Seeder... و Run Seeder."}
```

## الخلاصة

- **Ctrl+F5** للتشغيل في Preview، و**F5** مع Xdebug، و**Requests** لمراقبة الطلبات.
- قائمة **CodeIgniter**: Serve و Routes و Make و Database و Clear Cache و Composer.
- **لوحة CodeIgniter**: Spark بالاستمارات، و Routes بالنقر المزدوج للكود، و Output.
- **الزر الأيمن** في Solution Explorer يعرض المولّد المناسب لكل مجلد وملف.
