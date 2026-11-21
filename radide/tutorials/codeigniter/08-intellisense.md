# الدرس 8: IntelliSense والانتقال إلى التعريف

**في هذا الدرس ستتعلم:**

- الاقتراحات التي تقرؤها الـ IDE **من مشروعك أنت**: أسماء القوالب والمسارات والإعدادات والترجمات وأعمدة الجداول وقواعد التحقق.
- **F12** و**Ctrl+نقر** للانتقال من نص مثل `'products/index'` إلى ملفه.
- كيف تعرف الـ IDE هذه الأسماء، وماذا تفعل إن لم تظهر الاقتراحات.

## IntelliSense يعرف مشروعك

محرر PHP في RAD IDE يعمل مع خادم اللغة **intelephense** (الدوال والأصناف والمتغيرات). وفوقه طبقة **خاصة بـ CodeIgniter** تقرأ ملفات مشروعك وتتحدث **فور** تعديلها: أضف مسارًا أو قالبًا أو مفتاح ترجمة أو عمودًا في ترحيل، فيظهر في الاقتراحات مباشرة.

جرّب في أي متحكم أو قالب، والمؤشر داخل علامات التنصيص:

| تكتب | تقترح الـ IDE |
|---|---|
| `view('` | أسماء القوالب: `products/index` و`layouts/main`... |
| `$this->extend('` و`$this->include('` | القوالب أيضًا |
| `$this->section('` و`renderSection('` | أسماء الفتحات المستخدمة في المشروع (`content`...) |
| `url_to('` و`route_to('` و`redirect()->route('` | أسماء المسارات: `products.index` و`products.edit`... |
| `site_url('` و`base_url('` و`redirect()->to('` | العناوين وملفات `public` |
| `config('` ثم `config('App')->` | أصناف الإعدادات ثم خصائصها |
| `lang('` | مفاتيح الترجمة من `app/Language`: `Shop.products.title`... |
| `helper('` | أسماء المساعدات (`form` و`url` و`text`...)، وبعدها دوالها |
| `service('` | أسماء الخدمات (`request` و`session` و`validation`...) |
| `model('` | أصناف النماذج: `ProductModel`... |
| `->where('` و`->like('` و`->orderBy('` و`$row['` | أعمدة الجدول (من الترحيلات و`$allowedFields` وقاعدة SQLite نفسها) |
| `'price' => 'required|` (في قواعد التحقق) | أسماء القواعد مع شرح كل قاعدة: `decimal` و`min_length[]`... |
| `env('` | مفاتيح ملف `.env` |
| `$routes->get('x', '` (في `Routes.php`) | `Controller::method` لكل دوال متحكماتك |

جرّب الآن:

1. افتح `app/Controllers/Products.php`، واكتب في دالة `index` السطر `return view('` ثم توقف: تظهر قائمة قوالبك.
2. اكتب في `ProductModel` داخل `$validationRules` النص `'stock' => 'required|` ثم توقف: تظهر القواعد مع شرح كل واحدة.
3. في قالب، اكتب `<?= url_to('` : تظهر أسماء مساراتك.

## F12: من النص إلى الملف

ضع المؤشر على أي نص من هذه الأنواع واضغط **F12** (**Go to Definition** - الانتقال إلى التعريف) أو **Ctrl+نقر**:

| المؤشر على | تنتقل إلى |
|---|---|
| `view('products/form')` | الملف `app/Views/products/form.php` |
| `url_to('products.edit', ...)` | سطر المسار في `app/Config/Routes.php` |
| `'Products::edit/$1'` في `Routes.php` | الدالة `edit` في المتحكم |
| `lang('Shop.products.title')` | المفتاح في `app/Language/ar/Shop.php` (أو لغة الموقع الحالية) |
| `config('Shop')` | الملف `app/Config/Shop.php` |
| `model(ProductModel::class)` | صنف النموذج |

وعلى أي كلمة أخرى (صنف أو دالة عادية) يعمل F12 العادي من intelephense. وهذا مع تبويب **Routes** (النقر المزدوج) يجعلك تتنقل في المشروع كله دون البحث في المجلدات.

## كيف تعرف الـ IDE أسماء المسارات؟

ببساطة: تقرأ `Routes.php` وتبحث عن الخيار `'as' => '...'`، وتتذكر رقم السطر لتستخدمه مع F12. (ومع ذلك تستدعي `php spark routes` في تبويب Routes لتعرض المسارات كما يراها CodeIgniter فعلًا.) هذه محاكاة صغيرة للفكرة:

```php run
<?php
$routesFile = <<<'PHP'
<?php
$routes->get('/', 'Home::index', ['as' => 'home']);
$routes->get('login', 'Auth::login', ['as' => 'login']);
$routes->group('products', static function ($routes) {
    $routes->get('/', 'Products::index', ['as' => 'products.index']);
    $routes->get('(:num)/edit', 'Products::edit/$1', ['as' => 'products.edit']);
});
PHP;

$names = [];
foreach (explode("\n", $routesFile) as $i => $line) {
    if (preg_match("/->(get|post|put|delete)\('([^']*)',\s*'([^']+)'.*'as'\s*=>\s*'([^']+)'/", $line, $m)) {
        $names[$m[4]] = ['line' => $i + 1, 'method' => strtoupper($m[1]), 'handler' => $m[3]];
    }
}

// المستخدم كتب url_to('pro  => نقترح ما يبدأ بـ pro
$typed = 'pro';
foreach ($names as $name => $info) {
    if (str_starts_with($name, $typed)) {
        echo "$name  ({$info['method']} {$info['handler']}, سطر {$info['line']})\n";
    }
}
```

```text output
products.index  (GET Products::index, سطر 5)
products.edit  (GET Products::edit/$1, سطر 6)
```

## الترجمات: lang()

الأفضل أن تكتب نصوص الواجهة في ملفات ترجمة لتدعم أكثر من لغة (مثال المتجر يفعل ذلك في `app/Language/en/Shop.php`). ملف العربية `app/Language/ar/Shop.php` مصفوفة متداخلة:

```php
<?php

return [
    'products' => [
        'title' => 'المنتجات',
        'saved' => 'تم حفظ {0}',
    ],
];
```

و`lang('Shop.products.saved', ['قلم'])` تقرأ: الملف `Shop`، ثم المفتاح `products`، ثم `saved`، وتضع القيم مكان `{0}`. المحاكاة:

```php run
<?php
$files = [
    'Shop' => [
        'products' => ['title' => 'المنتجات', 'saved' => 'تم حفظ {0}'],
        'save' => 'حفظ',
    ],
];

function lang(array $files, string $key, array $args = []): string
{
    $parts = explode('.', $key);           // Shop.products.saved
    $value = $files;
    foreach ($parts as $p) {
        if (!is_array($value) || !isset($value[$p])) {
            return $key;                   // مفتاح غير موجود: يرجع النص كما هو
        }
        $value = $value[$p];
    }
    foreach ($args as $i => $arg) {
        $value = str_replace('{' . $i . '}', $arg, $value);
    }
    return $value;
}

echo lang($files, 'Shop.products.title'), "\n";
echo lang($files, 'Shop.products.saved', ['قلم رصاص']), "\n";
echo lang($files, 'Shop.products.missing'), "\n";
```

```text output
المنتجات
تم حفظ قلم رصاص
Shop.products.missing
```

لاحظ السطر الأخير: المفتاح الخطأ **لا يسبب خطأ**، بل يظهر النص نفسه في الصفحة. ولهذا اقتراحات `lang('` في الـ IDE مفيدة جدًا: تمنعك من الأخطاء الإملائية في المفاتيح. واللغة المستخدمة يحددها `$defaultLocale` في `app/Config/App.php`.

## إن لم تظهر الاقتراحات

- **تأكد أن المشروع مشروع CodeIgniter مفتوح** (فيه `spark` و`vendor`). بدون `vendor` لا تعمل بعض الاقتراحات: **More > composer install**.
- **المؤشر خارج علامات التنصيص؟** اقتراحات الأسماء تظهر داخل `'...'` فقط.
- **اضغط Ctrl+Space** لطلب الاقتراحات يدويًا.
- **أعمدة الجدول لا تظهر:** طبّق الترحيلات (**Migrate**) أو أضف الأعمدة إلى `$allowedFields`.
- **Refresh** في لوحة CodeIgniter يعيد قراءة الأوامر والمسارات.

## اختبر نفسك

```quiz
{"question": "كتبت view(' في متحكم. ماذا تقترح الـ IDE؟", "choices": ["أسماء الجداول", "أسماء القوالب الموجودة في app/Views", "أوامر spark", "لا شيء"], "answer": 1, "explanation": "الـ IDE تقرأ مجلد app/Views وتقترح أسماء القوالب بصيغة products/index."}
```

```quiz
{"question": "ماذا يحدث عند F12 على 'Products::edit/$1' داخل Routes.php؟", "choices": ["يُشغّل المسار", "تُفتح الدالة edit في متحكم Products", "يُحذف السطر", "يُفتح القالب"], "answer": 1, "explanation": "F12 على handler في Routes.php ينقلك إلى دالة المتحكم."}
```

```quiz
{"question": "كتبت lang('Shop.prodcts.title') بخطأ إملائي. ماذا يظهر في الصفحة؟", "choices": ["خطأ قاتل", "النص Shop.prodcts.title نفسه", "صفحة 404", "لا شيء"], "answer": 1, "explanation": "المفتاح غير الموجود يُطبع كما هو؛ اقتراحات الـ IDE تحميك من هذا الخطأ."}
```

## الخلاصة

- الـ IDE تقرأ مشروعك وتقترح: القوالب، والمسارات، والإعدادات، والترجمات، والمساعدات، والخدمات، والنماذج، والأعمدة، وقواعد التحقق، ومفاتيح `.env`.
- **F12** و**Ctrl+نقر** على هذه النصوص ينقلانك إلى ملفاتها، وعلى `Controller::method` إلى الدالة.
- الاقتراحات تتحدث فور تعديل الملفات، و**Ctrl+Space** يطلبها يدويًا.
