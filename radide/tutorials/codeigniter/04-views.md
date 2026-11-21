# الدرس 4: القوالب والتخطيطات والمساعدات

**في هذا الدرس ستتعلم:**

- إنشاء **قالب** (View) بأمر **New View...** وعرضه بـ `view()`.
- تمرير البيانات من المتحكم، والطباعة الآمنة بـ `esc()`.
- **التخطيط المشترك** بـ `$this->extend()` و`$this->section()` و`$this->renderSection()`.
- القطع المشتركة بـ `$this->include()`.
- **المساعدات** (helpers): `form_open()` و`base_url()` و`anchor()`.

## القالب: صفحة HTML فيها فراغات

القالب في CodeIgniter ملف PHP عادي في `app/Views`، فيه HTML مع قليل من PHP لملء **الفراغات**، مثل استمارة مطبوعة تملؤها بالقلم.

1. انقر بالزر الأيمن على `app/Views` > **New View...** (قالب جديد...).
2. الاسم: `products/index`، واترك **Layout** فارغًا الآن، ثم **OK**.

تنشئ الـ IDE الملف `app/Views/products/index.php` وتفتحه. اكتب:

```php
<h1>المنتجات</h1>
<p>نتائج البحث عن: <?= esc($q) ?></p>
<ul>
    <?php foreach ($products as $p): ?>
        <li><?= esc($p['name']) ?> - <?= esc($p['price']) ?> جنيه</li>
    <?php endforeach ?>
</ul>
```

ومن المتحكم:

```php
public function index(): string
{
    $products = [['name' => 'قلم', 'price' => 5], ['name' => 'دفتر', 'price' => 20]];

    return view('products/index', [
        'q'        => (string) $this->request->getGet('q'),
        'products' => $products,
    ]);
}
```

- `view('products/index', [...])`: اسم القالب بلا `.php`، والمجلدات بـ `/`.
- كل **مفتاح** في المصفوفة يصبح **متغيرًا** داخل القالب: `'q'` يصبح `$q`.
- `<?= ... ?>` اختصار `<?php echo ... ?>`، و`foreach (...):` مع `endforeach` صيغة مريحة داخل HTML.

## esc(): الطباعة الآمنة

أي نص جاء من الزائر أو من قاعدة البيانات **اطبعه داخل `esc()`**. لو كتب زائر في البحث `<script>...</script>` وطبعته كما هو، سيعمل الكود في متصفح كل من يفتح الصفحة (هجوم **XSS**). `esc()` تحول الرموز الخاصة إلى نص آمن:

```php run
<?php
// esc() في CodeIgniter تستخدم htmlspecialchars (وتعرف سياقات أخرى مثل 'attr' و 'js' و 'url')
function esc(string $text): string
{
    return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
}

$q = '<script>alert("hi")</script>';
echo "بدون esc: <p>$q</p>\n";
echo "مع esc:   <p>" . esc($q) . "</p>\n";
```

```text output
بدون esc: <p><script>alert("hi")</script></p>
مع esc:   <p>&lt;script&gt;alert(&quot;hi&quot;)&lt;/script&gt;</p>
```

## التخطيط المشترك (Layout)

كل صفحات الموقع لها نفس الرأس والقائمة والتذييل. بدل تكرارها نكتب **تخطيطًا** واحدًا فيه «فتحة» اسمها `content`، وكل صفحة تملأ الفتحة فقط. أنشئ `app/Views/layouts/main.php` بأمر **New View...**:

```php
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <title><?= esc($title ?? 'متجري') ?></title>
</head>
<body>
    <nav><a href="<?= site_url('/') ?>">الرئيسية</a> | <a href="<?= url_to('products.index') ?>">المنتجات</a></nav>
    <main>
        <?= $this->renderSection('content') ?>
    </main>
    <footer>متجري 2026</footer>
</body>
</html>
```

ثم أنشئ صفحة جديدة بـ **New View...** واكتب في خانة **Layout** القيمة `layouts/main`، فتنشئ الـ IDE الهيكل جاهزًا:

```php
<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1>المنتجات</h1>
<?= $this->endSection() ?>
```

- `$this->extend('layouts/main')`: «هذه الصفحة تستخدم هذا التخطيط».
- ما بين `section('content')` و`endSection()` يوضع مكان `renderSection('content')`.
- يمكنك عمل فتحات أخرى، مثل `renderSection('scripts')` لملفات JavaScript خاصة بصفحة.

كيف يعمل ذلك من الداخل؟ هذا موقع صغير فيه **محرك قوالب مصغر** يقلد `extend` و`section` و`renderSection` بـ `ob_start()` (التقاط الناتج):

```php web run
// #file: View.php
<?php
class View
{
    private array $sections = [];
    private ?string $layout = null;
    private ?string $current = null;

    public function render(string $name, array $data = []): string
    {
        extract($data);                       // 'title' => ... تصبح $title
        ob_start();
        include __DIR__ . "/Views/$name.php";
        $out = ob_get_clean();
        if ($this->layout !== null) {         // الصفحة طلبت تخطيطًا
            $layout = $this->layout;
            $this->layout = null;
            return $this->render($layout, $data);
        }
        return $out;
    }

    public function extend(string $layout): string { $this->layout = $layout; return ''; }
    public function section(string $name): string { $this->current = $name; ob_start(); return ''; }
    public function endSection(): string { $this->sections[$this->current] = ob_get_clean(); return ''; }
    public function renderSection(string $name): string { return $this->sections[$name] ?? ''; }
}

function esc(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}
// #file: Views/layouts/main.php
<html dir="rtl">
<title><?= esc($title) ?></title>
<nav>الرئيسية | المنتجات</nav>
<?= $this->renderSection('content') ?>
<footer>متجري 2026</footer>
</html>
// #file: Views/products/index.php
<?= $this->extend('layouts/main') ?>
<?= $this->section('content') ?>
<h1><?= esc($title) ?></h1>
<ul>
<?php foreach ($products as $p): ?>
<li><?= esc($p) ?></li>
<?php endforeach ?>
</ul>
<?= $this->endSection() ?>
// #file: index.php
<?php
require __DIR__ . '/View.php';
echo (new View())->render('products/index', [
    'title'    => 'المنتجات',
    'products' => ['قلم', 'دفتر', '<b>مسطرة</b>'],
]);
```

```text output
<html dir="rtl">
<title>المنتجات</title>
<nav>الرئيسية | المنتجات</nav>
<h1>المنتجات</h1>
<ul>
<li>قلم</li>
<li>دفتر</li>
<li>&lt;b&gt;مسطرة&lt;/b&gt;</li>
</ul>
<footer>متجري 2026</footer>
</html>
```

اضغط «جرّبه» لتفتحه كموقع في الـ IDE، ثم عدّل `Views/layouts/main.php` واحفظ: يتغير شكل الصفحة كلها.

## القطع المشتركة: `include`

قطعة HTML تتكرر في صفحات كثيرة (رسائل النجاح والخطأ مثلًا)؟ ضعها في ملف وأدرجها:

```php
<!-- app/Views/partials/flash.php -->
<?php if (session('message')): ?>
    <div class="alert"><?= esc(session('message')) ?></div>
<?php endif ?>
```

```php
<!-- داخل التخطيط أو أي صفحة -->
<?= $this->include('partials/flash') ?>
```

## المساعدات (Helpers)

**المساعد** ملف فيه دوال صغيرة جاهزة. تحمّله بـ `helper('form')` أو تضيفه مرة واحدة لكل المتحكمات في `BaseController`:

```php
// app/Controllers/BaseController.php
protected $helpers = ['form', 'url'];
```

| الدالة | المساعد | ماذا تفعل |
|---|---|---|
| `base_url('css/site.css')` | url | عنوان كامل لملف في `public` |
| `site_url('products')` | url | عنوان كامل لصفحة في الموقع |
| `anchor('products', 'المنتجات')` | url | وسم `<a>` كامل |
| `form_open('products')` | form | وسم `<form method="post">` **مع حقل CSRF المخفي** تلقائيًا |
| `form_close()` | form | `</form>` |
| `old('name')` | (مدمجة) | القيمة التي كتبها الزائر قبل فشل التحقق (الدرس 7) |
| `csrf_field()` | (مدمجة) | حقل CSRF المخفي إن كتبت `<form>` بيدك |

> **View Cells:** لقطعة لها منطق خاص (مثل «آخر 5 منتجات» في الشريط الجانبي) استخدم **New View Cell...**: صنف صغير مع قالبه، تعرضه بـ `view_cell('LatestProductsCell')`.

## أخطاء شائعة

- **`Invalid file: "products/index.php"`:** اسم القالب أو المجلد خطأ؛ يجب أن يكون الملف `app/Views/products/index.php`، وتكتب `view('products/index')` بلا `.php`.
- **`Undefined variable $products`:** لم تمرر المفتاح `'products'` في مصفوفة `view()`.
- **الصفحة فارغة مع تخطيط:** نسيت `endSection()`، أو اسم الفتحة في `section('content')` لا يطابق `renderSection('content')`.
- **نسيان `esc()`:** ثغرة XSS. كل نص من الزائر أو قاعدة البيانات يُطبع بـ `esc()`.
- **`Call to undefined function form_open()`:** لم تحمّل المساعد `form`. أضفه في `$helpers`.

## تمرين

أضف إلى دالة `esc` المبسطة سياقًا ثانيًا: إذا كان المعامل الثاني `'url'` ترجع النص مشفرًا للعناوين بـ `rawurlencode`، وإلا ترجع `htmlspecialchars` كما هو.

```php exercise
<?php
function esc(string $text, string $context = 'html'): string
{
    return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
}

echo esc('<b>قلم</b>'), "\n";
echo esc('قلم رصاص', 'url'), "\n";
```

```php solution
<?php
function esc(string $text, string $context = 'html'): string
{
    if ($context === 'url') {
        return rawurlencode($text);
    }
    return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
}

echo esc('<b>قلم</b>'), "\n";
echo esc('قلم رصاص', 'url'), "\n";
```

```text output
&lt;b&gt;قلم&lt;/b&gt;
%D9%82%D9%84%D9%85%20%D8%B1%D8%B5%D8%A7%D8%B5
```

## اختبر نفسك

```quiz
{"question": "كيف يصل المتغير $products إلى القالب؟", "choices": ["بكتابة global $products", "بتمرير ['products' => ...] في view()", "يقرؤه القالب من قاعدة البيانات وحده", "من ملف .env"], "answer": 1, "explanation": "كل مفتاح في مصفوفة view() يصبح متغيرًا بنفس الاسم داخل القالب."}
```

```quiz
{"question": "ما الذي يوضع مكان $this->renderSection('content') في التخطيط؟", "choices": ["ملف content.php", "ما كتبته الصفحة بين section('content') و endSection()", "أول سطر في الصفحة", "لا شيء"], "answer": 1, "explanation": "التخطيط فيه فتحة، والصفحة تملؤها بما بين section و endSection."}
```

```quiz
{"question": "لماذا نفضل form_open() على كتابة <form> بأيدينا؟", "choices": ["لأنها أقصر فقط", "لأنها تضيف حقل CSRF المخفي تلقائيًا", "لأن <form> لا تعمل في CodeIgniter", "لأنها تتحقق من المدخلات"], "answer": 1, "explanation": "form_open تضيف رمز CSRF الذي يرفض بدونه CodeIgniter طلبات POST عند تفعيل المرشح csrf."}
```

## الخلاصة

- القوالب في `app/Views`، وتُعرض بـ `view('folder/name', $data)`؛ كل مفتاح يصبح متغيرًا.
- اطبع كل نص بـ `esc()` لتمنع XSS.
- **التخطيط**: `extend` + `section` / `endSection` في الصفحة، و`renderSection` في التخطيط. وخانة **Layout** في **New View...** تكتب الهيكل لك.
- `$this->include()` للقطع المشتركة، و`form_open()` و`site_url()` و`base_url()` من المساعدات.
