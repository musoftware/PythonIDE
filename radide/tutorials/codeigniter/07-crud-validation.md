# الدرس 7: تطبيق CRUD كامل مع التحقق

**في هذا الدرس ستتعلم:**

- بناء صفحات **CRUD** للمنتجات: القائمة، والإضافة، والتعديل، والحذف.
- **قواعد التحقق** في النموذج: `required|min_length[3]|decimal`...
- العودة للنموذج مع الأخطاء والقيم القديمة: `redirect()->back()->withInput()` و`old()`.
- **رسائل الفلاش** وحماية **CSRF**.
- تجربة كل شيء بأدوات الـ IDE: Routes و Preview و Requests و Databases.

سنكمل على جدول `products` (الدرس 5) والنموذج `ProductModel` (الدرس 6). الخطة مثل أي مشروع حقيقي: **المسارات ← النموذج ← المتحكم ← القوالب**.

## الخطوة 1: المسارات

في `app/Config/Routes.php`:

```php
$routes->group('products', static function ($routes) {
    $routes->get('/', 'Products::index', ['as' => 'products.index']);
    $routes->get('new', 'Products::new', ['as' => 'products.new']);
    $routes->post('/', 'Products::create', ['as' => 'products.create']);
    $routes->get('(:num)/edit', 'Products::edit/$1', ['as' => 'products.edit']);
    $routes->post('(:num)', 'Products::update/$1', ['as' => 'products.update']);
    $routes->post('(:num)/delete', 'Products::delete/$1', ['as' => 'products.delete']);
});
```

احفظ وافتح **CodeIgniter > Routes**: ترى المسارات الستة بأسمائها. صفحات العرض بـ GET، وكل ما **يغير** البيانات (الحفظ والحذف) بـ POST.

## الخطوة 2: قواعد التحقق في النموذج

أضف إلى `ProductModel` (من الدرس 6):

```php
protected $allowedFields = ['name', 'price', 'stock'];

protected $validationRules = [
    'name'  => 'required|min_length[3]|max_length[120]',
    'price' => 'required|decimal|greater_than_equal_to[0]',
    'stock' => 'required|is_natural',
];

protected $validationMessages = [
    'name' => ['min_length' => 'اسم المنتج قصير جدًا.'],
];
```

القواعد **لغة صغيرة**: قواعد يفصلها `|`، وبعضها يأخذ قيمة بين `[ ]`. والنموذج يطبقها **تلقائيًا** في كل `insert()` و`update()` و`save()`: إذا فشلت لا يحفظ ويرجع `false`، وتجد الرسائل في `$model->errors()`.

| القاعدة | معناها |
|---|---|
| `required` | لا يكون فارغًا |
| `min_length[3]` / `max_length[120]` | طول النص |
| `decimal` / `integer` / `numeric` | رقم عشري / صحيح / أي رقم |
| `is_natural` | 0، 1، 2 ... |
| `greater_than_equal_to[0]` | أكبر من أو يساوي 0 |
| `valid_email` | بريد إلكتروني صحيح |
| `in_list[new,used]` | واحدة من قائمة |
| `is_unique[products.sku,id,{id}]` | غير مكرر في الجدول (مع استثناء الصف نفسه عند التعديل) |
| `permit_empty` | مسموح أن يكون فارغًا (وتُتجاهل بقية القواعد حينها) |

و**IntelliSense** يقترح أسماء القواعد وأنت تكتب داخل النص بعد `|` (الدرس 8).

كيف تعمل هذه اللغة من الداخل؟ محاكاة مصغرة لمحرك التحقق:

```php run
<?php
function check_rule(string $rule, string $value): ?string
{
    // 'min_length[3]' => اسم القاعدة 'min_length' والمعامل '3'
    preg_match('/^(\w+)(?:\[(.*)\])?$/', $rule, $m);
    [$name, $param] = [$m[1], $m[2] ?? null];
    $ok = match ($name) {
        'required'                 => trim($value) !== '',
        'min_length'               => mb_strlen($value) >= (int) $param,
        'max_length'               => mb_strlen($value) <= (int) $param,
        'decimal'                  => (bool) preg_match('/^-?\d+(\.\d+)?$/', $value),
        'is_natural'               => ctype_digit($value),
        'greater_than_equal_to'    => is_numeric($value) && $value >= $param,
        default                    => throw new InvalidArgumentException("قاعدة غير معروفة: $name"),
    };
    return $ok ? null : $name;
}

function validate(array $data, array $rules): array
{
    $errors = [];
    foreach ($rules as $field => $ruleText) {
        foreach (explode('|', $ruleText) as $rule) {
            $failed = check_rule($rule, (string) ($data[$field] ?? ''));
            if ($failed !== null) {
                $errors[$field] = "$field: فشلت القاعدة $failed";
                break;                       // أول قاعدة تفشل تكفي لهذا الحقل
            }
        }
    }
    return $errors;
}

$rules = [
    'name'  => 'required|min_length[3]|max_length[120]',
    'price' => 'required|decimal|greater_than_equal_to[0]',
    'stock' => 'required|is_natural',
];

print_r(validate(['name' => 'قل', 'price' => '-3', 'stock' => '10'], $rules));
print_r(validate(['name' => 'قلم رصاص', 'price' => '7.5', 'stock' => ''], $rules));
print_r(validate(['name' => 'قلم رصاص', 'price' => '7.5', 'stock' => '12'], $rules));
```

```text output
Array
(
    [name] => name: فشلت القاعدة min_length
    [price] => price: فشلت القاعدة greater_than_equal_to
)
Array
(
    [stock] => stock: فشلت القاعدة required
)
Array
(
)
```

لاحظ أن `mb_strlen` تعد الحروف العربية صحيحًا (`'قل'` حرفان)، و CodeIgniter يفعل ذلك أيضًا.

## الخطوة 3: المتحكم

انقر بالزر الأيمن على `app/Controllers` > **New Controller...** باسم `Products` واكتب:

```php
<?php

namespace App\Controllers;

use App\Models\ProductModel;
use CodeIgniter\Exceptions\PageNotFoundException;

class Products extends BaseController
{
    protected $helpers = ['form'];

    public function index(): string
    {
        $products = model(ProductModel::class);
        return view('products/index', [
            'products' => $products->orderBy('name')->paginate(10),
            'pager'    => $products->pager,
        ]);
    }

    public function new(): string
    {
        return view('products/form', ['product' => null]);
    }

    public function create()
    {
        $products = model(ProductModel::class);
        $data = $this->request->getPost(['name', 'price', 'stock']);

        if (! $products->insert($data)) {
            // فشل التحقق: ارجع للنموذج بالأخطاء وبما كتبه الزائر
            return redirect()->back()->withInput()->with('errors', $products->errors());
        }
        return redirect()->route('products.index')->with('message', 'تمت إضافة ' . $data['name']);
    }

    public function edit(int $id): string
    {
        return view('products/form', ['product' => $this->findOr404($id)]);
    }

    public function update(int $id)
    {
        $this->findOr404($id);
        $products = model(ProductModel::class);
        $data = $this->request->getPost(['name', 'price', 'stock']);

        if (! $products->update($id, $data)) {
            return redirect()->back()->withInput()->with('errors', $products->errors());
        }
        return redirect()->route('products.index')->with('message', 'تم حفظ التعديل');
    }

    public function delete(int $id)
    {
        model(ProductModel::class)->delete($this->findOr404($id)['id']);
        return redirect()->route('products.index')->with('message', 'تم الحذف');
    }

    private function findOr404(int $id): array
    {
        return model(ProductModel::class)->find($id)
            ?? throw PageNotFoundException::forPageNotFound("لا يوجد منتج رقم $id");
    }
}
```

- `getPost(['name', 'price', 'stock'])`: يأخذ هذه الحقول فقط من النموذج.
- `redirect()->back()->withInput()`: يرجع للصفحة السابقة ويحفظ ما كتبه الزائر لتقرأه `old()`.
- `->with('errors', ...)` و`->with('message', ...)`: **رسائل فلاش** في الجلسة، تظهر في الطلب التالي فقط.
- `PageNotFoundException`: صفحة **404** إذا كان الرقم غير موجود.

## الخطوة 4: القوالب

`app/Views/products/form.php` (بـ **New View...** وخانة **Layout** = `layouts/main`):

```php
<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1><?= $product ? 'تعديل منتج' : 'منتج جديد' ?></h1>

<?php foreach (session('errors') ?? [] as $error): ?>
    <p class="error"><?= esc($error) ?></p>
<?php endforeach ?>

<?= form_open($product ? url_to('products.update', $product['id']) : url_to('products.create')) ?>
    <label>الاسم <input name="name" value="<?= esc(old('name', $product['name'] ?? '')) ?>"></label>
    <label>السعر <input name="price" type="number" step="0.01" value="<?= esc(old('price', $product['price'] ?? '')) ?>"></label>
    <label>المخزون <input name="stock" type="number" value="<?= esc(old('stock', $product['stock'] ?? 0)) ?>"></label>
    <button type="submit">حفظ</button>
<?= form_close() ?>
<?= $this->endSection() ?>
```

و`app/Views/products/index.php`:

```php
<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1>المنتجات</h1>
<?php if (session('message')): ?><p class="ok"><?= esc(session('message')) ?></p><?php endif ?>
<p><a href="<?= url_to('products.new') ?>">+ منتج جديد</a></p>
<table>
    <?php foreach ($products as $p): ?>
        <tr>
            <td><?= esc($p['name']) ?></td>
            <td><?= esc($p['price']) ?></td>
            <td><a href="<?= url_to('products.edit', $p['id']) ?>">تعديل</a></td>
            <td>
                <?= form_open(url_to('products.delete', $p['id'])) ?>
                    <button onclick="return confirm('حذف؟')">حذف</button>
                <?= form_close() ?>
            </td>
        </tr>
    <?php endforeach ?>
</table>
<?= $pager->links() ?>
<?= $this->endSection() ?>
```

> **لماذا الحذف بنموذج وليس برابط؟** الروابط طلبات GET، وقد تفتحها برامج أو محركات بحث وحدها. كل ما يغير البيانات يكون POST مع رمز CSRF.

## حماية CSRF

**CSRF** هجوم يجعل متصفح زائر مسجل الدخول يرسل نموذجًا من موقع آخر دون علمه. الحماية: رمز سري عشوائي في كل نموذج، يرفض الخادم أي POST لا يحمله.

في CodeIgniter فعّلها مرة واحدة في `app/Config/Filters.php`:

```php
public array $globals = [
    'before' => [
        'csrf',
    ],
];
```

و`form_open()` تضيف الحقل المخفي وحدها (أو `csrf_field()` إن كتبت `<form>` بيدك). نموذج بلا رمز يُرد بخطأ **`The action you requested is not allowed.`**

## الفكرة كلها في موقع مصغر

هذا الموقع المصغر بـ PHP عادية يقلد نفس الدورة: التحقق، والعودة بالأخطاء والقيم القديمة، و CSRF، ورسالة الفلاش بعد التحويل. الاختبار يفتح النموذج، ثم يرسله ببيانات خاطئة، ثم ببيانات صحيحة:

<!-- test: {"requests": [{"path": "/new.php"}, {"method": "POST", "path": "/new.php", "data": {"name": "قل", "price": "-3", "csrf": "{{field:csrf}}"}}, {"method": "POST", "path": "/new.php", "data": {"name": "قلم رصاص", "price": "7.5", "csrf": "{{field:csrf}}"}}], "all": true, "mask": {"value=\"[0-9a-f]{32}\"": "value=\"CSRF_TOKEN\""}, "start": "new.php"} -->
```php web run
// #file: inc/boot.php
<?php
session_start();
$_SESSION['csrf'] ??= bin2hex(random_bytes(16));
$_SESSION['products'] ??= [];

function esc(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

// مثل with(): قيمة تُقرأ مرة واحدة ثم تُحذف
function flash(string $key, mixed $default = null): mixed
{
    $v = $_SESSION['_flash'][$key] ?? $default;
    unset($_SESSION['_flash'][$key]);
    return $v;
}

function validate(array $data): array
{
    $errors = [];
    if (mb_strlen(trim($data['name'] ?? '')) < 3) {
        $errors[] = 'اسم المنتج قصير جدًا.';
    }
    if (!is_numeric($data['price'] ?? '') || $data['price'] < 0) {
        $errors[] = 'السعر يجب أن يكون رقمًا أكبر من أو يساوي 0.';
    }
    return $errors;
}
// #file: new.php
<?php
require __DIR__ . '/inc/boot.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($_SESSION['csrf'], $_POST['csrf'] ?? '')) {
        http_response_code(403);
        exit('The action you requested is not allowed.');
    }
    $data = ['name' => $_POST['name'] ?? '', 'price' => $_POST['price'] ?? ''];
    $errors = validate($data);
    if ($errors) {                                   // redirect()->back()->withInput()->with('errors', ...)
        $_SESSION['_flash'] = ['errors' => $errors, 'old' => $data];
        header('Location: new.php');
        exit;
    }
    $_SESSION['products'][] = $data;                 // insert()
    $_SESSION['_flash'] = ['message' => 'تمت إضافة ' . $data['name']];
    header('Location: index.php');                   // redirect()->route('products.index')
    exit;
}
$old = flash('old', []);
?>
<h1>منتج جديد</h1>
<?php foreach (flash('errors', []) as $e): ?>
<p class="error"><?= esc($e) ?></p>
<?php endforeach ?>
<form method="post">
<input type="hidden" name="csrf" value="<?= $_SESSION['csrf'] ?>">
<input name="name" value="<?= esc($old['name'] ?? '') ?>">
<input name="price" value="<?= esc($old['price'] ?? '') ?>">
<button>حفظ</button>
</form>
// #file: index.php
<?php require __DIR__ . '/inc/boot.php'; ?>
<h1>المنتجات</h1>
<?php if ($msg = flash('message')): ?>
<p class="ok"><?= esc($msg) ?></p>
<?php endif ?>
<ul>
<?php foreach ($_SESSION['products'] as $p): ?>
<li><?= esc($p['name']) ?> - <?= esc($p['price']) ?></li>
<?php endforeach ?>
</ul>
```

```text output
<h1>منتج جديد</h1>
<form method="post">
<input type="hidden" name="csrf" value="CSRF_TOKEN">
<input name="name" value="">
<input name="price" value="">
<button>حفظ</button>
</form>

<h1>منتج جديد</h1>
<p class="error">اسم المنتج قصير جدًا.</p>
<p class="error">السعر يجب أن يكون رقمًا أكبر من أو يساوي 0.</p>
<form method="post">
<input type="hidden" name="csrf" value="CSRF_TOKEN">
<input name="name" value="قل">
<input name="price" value="-3">
<button>حفظ</button>
</form>

<h1>المنتجات</h1>
<p class="ok">تمت إضافة قلم رصاص</p>
<ul>
<li>قلم رصاص - 7.5</li>
</ul>
```

لاحظ في الرد الثاني: الأخطاء ظهرت، **والقيم التي كتبها الزائر بقيت** في الحقول (`old`) فلا يعيد كتابتها. وفي الرد الثالث: رسالة الفلاش ظهرت مرة واحدة بعد التحويل.

## الخطوة 5: جرّب بأدوات الـ IDE

1. **Ctrl+F5**، ثم في المعاينة افتح `/products/new`.
2. أرسل النموذج فارغًا: ترى رسائل الأخطاء. وفي نافذة **Requests** ترى `POST /products` برمز **303** (تحويل) ثم `GET /products/new`.
3. أدخل بيانات صحيحة واحفظ: تعود للقائمة مع رسالة «تمت إضافة...».
4. افتح **Databases** > جدول `products` > **Open Data**: المنتج الجديد موجود، و`created_at` ممتلئ تلقائيًا.
5. جرب `/products/999/edit`: صفحة **404** كما توقعنا.

## أخطاء شائعة

- **`The action you requested is not allowed.`:** النموذج بلا رمز CSRF. استخدم `form_open()` أو `csrf_field()`.
- **التحقق يفشل ولا ترى رسائل:** القالب لا يعرض `session('errors')`.
- **الحقول تفرغ بعد فشل التحقق:** نسيت `withInput()` في المتحكم أو `old()` في القالب.
- **حقل لا يُحفظ رغم نجاح التحقق:** ليس في `$allowedFields`.
- **`Call to undefined function form_open()`:** أضف `protected $helpers = ['form'];` في المتحكم أو في `BaseController`.
- **عرض النتيجة بعد POST بدل التحويل:** عند تحديث الصفحة يُرسل النموذج مرة ثانية. حوّل دائمًا بعد الحفظ (نمط Post/Redirect/Get).

## تمرين

أضف إلى محرك التحقق المصغر القاعدة `in_list[...]`: تنجح إذا كانت القيمة واحدة من القيم المفصولة بفاصلة.

```php exercise
<?php
function check_rule(string $rule, string $value): bool
{
    preg_match('/^(\w+)(?:\[(.*)\])?$/', $rule, $m);
    [$name, $param] = [$m[1], $m[2] ?? null];
    return match ($name) {
        'required' => trim($value) !== '',
        // أضف in_list هنا
    };
}

var_dump(check_rule('in_list[new,used]', 'used'));
var_dump(check_rule('in_list[new,used]', 'broken'));
```

```php solution
<?php
function check_rule(string $rule, string $value): bool
{
    preg_match('/^(\w+)(?:\[(.*)\])?$/', $rule, $m);
    [$name, $param] = [$m[1], $m[2] ?? null];
    return match ($name) {
        'required' => trim($value) !== '',
        'in_list'  => in_array($value, explode(',', (string) $param), true),
    };
}

var_dump(check_rule('in_list[new,used]', 'used'));
var_dump(check_rule('in_list[new,used]', 'broken'));
```

```text output
bool(true)
bool(false)
```

## اختبر نفسك

```quiz
{"question": "متى يطبق CodeIgniter قواعد $validationRules الموجودة في النموذج؟", "choices": ["عند فتح الصفحة", "تلقائيًا في insert() و update() و save()", "عند تشغيل migrate فقط", "لا يطبقها إلا يدويًا"], "answer": 1, "explanation": "النموذج يتحقق قبل كل حفظ، ويرجع false مع errors() عند الفشل."}
```

```quiz
{"question": "ما فائدة withInput() في redirect()->back()->withInput()؟", "choices": ["تحفظ ما كتبه الزائر لتعيده old() إلى الحقول", "تحذف الجلسة", "تتحقق من CSRF", "تنشئ مسارًا جديدًا"], "answer": 0, "explanation": "withInput تحفظ المدخلات في الجلسة، و old('name') تقرؤها في القالب."}
```

```quiz
{"question": "لماذا نحذف المنتج بنموذج POST وليس برابط GET؟", "choices": ["لأن الروابط لا تعمل في CodeIgniter", "لأن GET لا يجب أن يغير البيانات، و POST يحمل رمز CSRF", "لأنه أسرع", "لا فرق"], "answer": 1, "explanation": "طلبات GET قد تُفتح وحدها؛ كل تغيير للبيانات يكون POST محميًا بـ CSRF."}
```

## الخلاصة

- **المسارات ← النموذج ← المتحكم ← القوالب**: نفس الترتيب في كل مشروع.
- قواعد التحقق في `$validationRules` تُطبق تلقائيًا عند الحفظ، والأخطاء في `errors()`.
- عند الفشل: `redirect()->back()->withInput()->with('errors', ...)`، وفي القالب `session('errors')` و`old()`.
- بعد النجاح: تحويل مع رسالة فلاش، و CSRF مفعّل في `Filters.php` مع `form_open()`.
