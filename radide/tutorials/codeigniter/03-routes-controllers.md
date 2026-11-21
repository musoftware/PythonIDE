# الدرس 3: المسارات والمتحكمات

**في هذا الدرس ستتعلم:**

- تعريف المسارات في `app/Config/Routes.php`: `$routes->get` و`$routes->post`.
- **العناصر النائبة** `(:num)` و`(:segment)` وكيف تصل إلى دالة المتحكم.
- **المسارات المسماة** والدالة `url_to()`.
- إنشاء **متحكم** بأمر **New Controller...** وقراءة بيانات الطلب.
- **مجموعات المسارات** و**مسارات الموارد**، ورؤية كل المسارات في تبويب **Routes**.

## أبسط مسار

المسار يشبه **لوحة الإرشادات** في مبنى: «من يطلب `/products` يذهب إلى مكتب `Products` غرفة `index`». افتح `app/Config/Routes.php`:

```php
<?php

use CodeIgniter\Router\RouteCollection;

/**
 * @var RouteCollection $routes
 */
$routes->get('/', 'Home::index');
$routes->get('hello', 'Home::hello');
```

- `$routes->get('hello', 'Home::hello')` تعني: طلب `GET /hello` تعالجه الدالة `hello` في المتحكم `Home`.
- الصيغة دائمًا `'Controller::method'`.

وأضف الدالة في `app/Controllers/Home.php`:

```php
<?php

namespace App\Controllers;

class Home extends BaseController
{
    public function index(): string
    {
        return view('welcome_message');
    }

    public function hello(): string
    {
        return 'مرحبًا من CodeIgniter!';
    }
}
```

احفظ، ثم اكتب في شريط عنوان المعاينة `/hello`. الدالة تُرجع نصًا فيصل للمتصفح كما هو، و`view('welcome_message')` تُرجع القالب `app/Views/welcome_message.php`.

## العناصر النائبة: أجزاء متغيرة في العنوان

نريد `/products/7` و`/products/15`... بمسار واحد. نكتب **عنصرًا نائبًا** مكان الرقم، و`$1` تعني «القيمة الأولى التي التقطتها»:

```php
$routes->get('products/(:num)', 'Products::show/$1');
$routes->get('category/(:segment)', 'Products::category/$1');
```

```php
public function show(int $id): string
{
    return "المنتج رقم $id";
}
```

| العنصر النائب | يطابق | مثال |
|---|---|---|
| `(:num)` | أرقام فقط | `/products/42` |
| `(:segment)` | أي جزء بلا `/` | `/category/books` |
| `(:alpha)` | حروف إنجليزية فقط | `/lang/ar` |
| `(:alphanum)` | حروف وأرقام | `/code/A12` |
| `(:any)` | أي شيء حتى مع `/` | `/files/2026/01/a.pdf` |

كيف يطابق CodeIgniter العنوان مع النمط؟ يحوّل كل عنصر نائب إلى **تعبير نمطي** (regular expression). المحاكاة التالية تفعل نفس الشيء:

```php run
<?php
const PLACEHOLDERS = [
    '(:num)'     => '([0-9]+)',
    '(:segment)' => '([^/]+)',
    '(:any)'     => '(.*)',
];

function match_route(string $pattern, string $handler, string $uri): ?string
{
    $regex = '#^' . strtr($pattern, PLACEHOLDERS) . '$#u';
    if (!preg_match($regex, $uri, $m)) {
        return null;
    }
    // $1, $2 ... في الـ handler تُستبدل بما التقطناه
    for ($i = 1; $i < count($m); $i++) {
        $handler = str_replace('$' . $i, $m[$i], $handler);
    }
    return $handler;
}

var_dump(match_route('products/(:num)', 'Products::show/$1', 'products/42'));
var_dump(match_route('products/(:num)', 'Products::show/$1', 'products/abc'));
var_dump(match_route('users/(:segment)/orders/(:num)', 'Orders::show/$1/$2', 'users/sara/orders/5'));
```

```text output
string(17) "Products::show/42"
NULL
string(19) "Orders::show/sara/5"
```

لاحظ أن `products/abc` **لا يطابق** `(:num)`، فيرد CodeIgniter بصفحة **404**. هذا يحمي دالتك من قيم غير متوقعة.

## المسارات المسماة

بدل كتابة العناوين يدويًا في كل قالب، أعطِ المسار **اسمًا** بالخيار `as`، وولّد عنوانه بـ `url_to()`:

```php
$routes->get('products/(:num)/edit', 'Products::edit/$1', ['as' => 'products.edit']);

// في متحكم أو قالب:
$url = url_to('products.edit', 7);                // http://127.0.0.1:8123/products/7/edit
return redirect()->route('products.edit', [7]);
```

إذا غيرت العنوان لاحقًا إلى `items/(:num)/edit` لا تعدّل شيئًا آخر. و**IntelliSense** في الـ IDE يقترح أسماء المسارات عند كتابة `url_to('` (الدرس 8).

## إنشاء متحكم

1. في Solution Explorer انقر بالزر الأيمن على `app/Controllers`.
2. اختر **New Controller...** (متحكم جديد...).
3. الاسم: `Products`، واترك **RESTful** على `(none)`، ثم **OK**.

تشغّل الـ IDE `php spark make:controller Products` وتفتح الملف الجديد. اكتب فيه:

```php
<?php

namespace App\Controllers;

class Products extends BaseController
{
    public function index(): string
    {
        $q = (string) $this->request->getGet('q');      // ?q=قلم
        return view('products/index', ['q' => $q]);
    }

    public function show(int $id): string
    {
        return "تفاصيل المنتج رقم $id";
    }
}
```

- كل متحكم يرث `BaseController`، وفيه `$this->request` (الطلب) و`$this->response` (الرد).
- `$this->request->getGet('q')` بدل `$_GET['q']`، و`getPost('name')` بدل `$_POST['name']`.
- الدالة تُرجع **نصًا** (عادة ناتج `view()`) أو **رد تحويل** (`redirect()`).

## مجموعات المسارات

مسارات كثيرة تبدأ بنفس الكلمة؟ ضعها في **مجموعة**، وأضف لها **مرشحًا** (filter) مثل التحقق من تسجيل الدخول مرة واحدة:

```php
$routes->group('products', ['filter' => 'auth'], static function ($routes) {
    $routes->get('/', 'Products::index', ['as' => 'products.index']);
    $routes->get('new', 'Products::new', ['as' => 'products.new']);
    $routes->post('/', 'Products::create', ['as' => 'products.create']);
    $routes->get('(:num)/edit', 'Products::edit/$1', ['as' => 'products.edit']);
    $routes->post('(:num)', 'Products::update/$1', ['as' => 'products.update']);
    $routes->post('(:num)/delete', 'Products::delete/$1', ['as' => 'products.delete']);
});
```

هذه بالضبط مسارات مثال المتجر `CodeIgniter_Shop`. والمرشح `auth` صنف في `app/Filters` (تنشئه بـ **New Filter...**) يُسجل في `app/Config/Filters.php`.

## مسارات الموارد

تطبيقات CRUD تحتاج دائمًا نفس العمليات، فيولّدها CodeIgniter بسطر واحد:

```php
$routes->presenter('products');   // صفحات HTML: index, show, new, create, edit, update, remove, delete
$routes->resource('api/products'); // واجهة JSON: GET, POST, PUT/PATCH, DELETE
```

ومعها متحكم من **New Controller...** مع **RESTful** = `presenter` أو `controller`، فيُنشأ بكل الدوال فارغة جاهزة لتملأها.

> **التوجيه التلقائي (Auto Routing):** في CodeIgniter 4 هو **مُطفأ** افتراضيًا لأسباب أمنية: أي دالة لا مسار لها لا يمكن الوصول إليها. اترك الأمر هكذا، واكتب مساراتك صراحة.

## تبويب Routes

بعد أي تعديل في `Routes.php` افتح **CodeIgniter > Routes** (أو لوحة CodeIgniter > تبويب **Routes**). ترى كل مسار بطريقته وعنوانه واسمه والمتحكم ومرشحاته. انقر مرتين على أي سطر لتذهب إلى دالة المتحكم، أو بالزر الأيمن **Open in Preview** لتفتح الصفحة مباشرة.

## أخطاء شائعة

- **`404 - Can't find a route for 'get: hello'`:** لا يوجد مسار لهذا العنوان والطريقة. راجع تبويب Routes؛ ربما كتبت `post` بدل `get`.
- **`Controller or its method is not found: \App\Controllers\Product::index`:** اسم المتحكم في المسار (`Product`) لا يطابق اسم الصنف أو الملف (`Products`). الأسماء حساسة لحالة الأحرف.
- **نسيان `$1`:** `'Products::show'` بدل `'Products::show/$1'` فلا يصل الرقم إلى الدالة.
- **ترتيب المسارات:** المسار `products/(:segment)` قبل `products/new` يلتقط `new` كأنه منتج. ضع المسارات الثابتة أولًا.

## تمرين

أضف العنصر النائب `(:alpha)` (حروف إنجليزية فقط) إلى المحاكاة، بحيث يطابق `lang/ar` ولا يطابق `lang/a1`.

```php exercise
<?php
const PLACEHOLDERS = [
    '(:num)'     => '([0-9]+)',
    '(:segment)' => '([^/]+)',
    // أضف (:alpha) هنا
];

function matches(string $pattern, string $uri): bool
{
    return (bool) preg_match('#^' . strtr($pattern, PLACEHOLDERS) . '$#', $uri);
}

var_dump(matches('lang/(:alpha)', 'lang/ar'));
var_dump(matches('lang/(:alpha)', 'lang/a1'));
```

```php solution
<?php
const PLACEHOLDERS = [
    '(:num)'     => '([0-9]+)',
    '(:segment)' => '([^/]+)',
    '(:alpha)'   => '([a-zA-Z]+)',
];

function matches(string $pattern, string $uri): bool
{
    return (bool) preg_match('#^' . strtr($pattern, PLACEHOLDERS) . '$#', $uri);
}

var_dump(matches('lang/(:alpha)', 'lang/ar'));
var_dump(matches('lang/(:alpha)', 'lang/a1'));
```

```text output
bool(true)
bool(false)
```

## اختبر نفسك

```quiz
{"question": "ماذا تعني $1 في 'Products::show/$1'؟", "choices": ["الدالة الأولى في المتحكم", "القيمة الأولى التي التقطها العنصر النائب من العنوان", "رقم السطر", "اسم المسار"], "answer": 1, "explanation": "$1 تُستبدل بما طابقه أول عنصر نائب، وتُمرر للدالة كمعامل."}
```

```quiz
{"question": "أي عنوان يطابق 'products/(:num)'؟", "choices": ["products/abc", "products/12", "products/", "products/12/edit"], "answer": 1, "explanation": "(:num) أرقام فقط، والنمط كامل من البداية للنهاية."}
```

```quiz
{"question": "لماذا نستخدم url_to('products.edit', 7) بدل كتابة '/products/7/edit'؟", "choices": ["أسرع في التنفيذ", "إذا تغير العنوان في Routes.php تتغير كل الروابط تلقائيًا", "لأن كتابة العنوان ممنوعة", "لا فرق"], "answer": 1, "explanation": "الروابط تُولّد من اسم المسار، فتغيير العنوان في مكان واحد يكفي."}
```

## الخلاصة

- المسارات في `app/Config/Routes.php` بالصيغة `$routes->get('uri', 'Controller::method')`.
- العناصر النائبة `(:num)` و`(:segment)` و`(:any)` تلتقط أجزاء العنوان، و`$1` تمررها للدالة.
- سمِّ المسارات بـ `['as' => '...']` وولّد روابطها بـ `url_to()`.
- **New Controller...** على `app/Controllers` ينشئ المتحكم، وتبويب **Routes** ينقلك إلى كود أي مسار.
