# الدرس 3: المسارات والمتحكمات

**في هذا الدرس ستتعلم:**

- تعريف المسارات في `routes/web.php`: `Route::get` و`Route::post` ومعاملات العنوان.
- **المسارات المسماة** والدالة `route()`.
- إنشاء **متحكم** بأمر **New Controller...** وربطه بالمسارات.
- **متحكم الموارد** (resource controller) الذي يغطي CRUD كله بسطر واحد.
- رؤية كل المسارات في تبويب **Routes** والانتقال إلى كودها.

## أبسط مسار

افتح `routes/web.php` (تفتحه الـ IDE تلقائيًا عند فتح مشروع Laravel):

```php
<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

Route::get('/hello', function () {
    return 'مرحبًا من Laravel!';
});
```

احفظ، ثم في المعاينة اكتب العنوان `/hello`. الدالة تُرجع نصًا فيصل للمتصفح كما هو. و`view('welcome')` تُرجع القالب `resources/views/welcome.blade.php`.

## معاملات في العنوان

الجزء بين أقواس معقوصة `{id}` **متغير** يُمرر للدالة:

```php
Route::get('/books/{id}', function (int $id) {
    return "الكتاب رقم $id";
});

Route::get('/hello/{name?}', function (string $name = 'زائر') {
    return "أهلًا يا " . e($name);
});
```

- `/books/7` يعطي «الكتاب رقم 7».
- علامة `?` تجعل المعامل اختياريًا: `/hello` و`/hello/سارة` يعملان.
- `e()` دالة Laravel المختصرة لـ `htmlspecialchars` (الأمان دائمًا!).

ولفهم كيف يطابق Laravel العنوان مع النمط، إليك محاكاة مبسطة بالتعبيرات النمطية:

```php run
<?php
function match_route(string $pattern, string $uri): ?array
{
    // /books/{id} => #^/books/(?P<id>[^/]+)$#
    $regex = "#^" . preg_replace('#\{(\w+)\}#', '(?P<$1>[^/]+)', $pattern) . "$#u";
    if (!preg_match($regex, $uri, $m)) {
        return null;
    }
    return array_filter($m, 'is_string', ARRAY_FILTER_USE_KEY);
}

print_r(match_route("/books/{id}", "/books/42"));
print_r(match_route("/users/{user}/posts/{post}", "/users/sara/posts/5"));
var_dump(match_route("/books/{id}", "/authors/3"));
```

```text output
Array
(
    [id] => 42
)
Array
(
    [user] => sara
    [post] => 5
)
NULL
```

## المسارات المسماة

بدل كتابة العناوين يدويًا في كل مكان، نعطي المسار **اسمًا** ونولّد عنوانه بـ `route()`:

```php
Route::get('/books/{id}', [BookController::class, 'show'])->name('books.show');

// في أي مكان (متحكم أو قالب):
$url = route('books.show', ['id' => 7]);   // http://127.0.0.1:8123/books/7
return redirect()->route('books.show', 7);
```

إذا غيّرت العنوان لاحقًا إلى `/library/{id}` لا تعدّل شيئًا آخر: كل الروابط تُولد من الاسم. و**IntelliSense** في الـ IDE يقترح أسماء المسارات عند كتابة `route('` (الدرس 8).

## المتحكمات

الدوال داخل `web.php` مناسبة للتجارب فقط. في التطبيق الحقيقي نضع المنطق في **متحكم**:

1. في Solution Explorer انقر بالزر الأيمن على `app/Http/Controllers`.
2. اختر **New Controller...** (متحكم جديد...).
3. الاسم: `BookController`، واترك الخيارات فارغة الآن، ثم **OK**.

تشغّل الـ IDE `php artisan make:controller BookController` وتفتح الملف الجديد. أضف إليه دالتين:

```php
<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class BookController extends Controller
{
    public function index()
    {
        $books = ['الأيام', 'اللص والكلاب', 'موسم الهجرة إلى الشمال'];
        return view('books.index', ['books' => $books]);
    }

    public function show(int $id)
    {
        return "تفاصيل الكتاب رقم $id";
    }
}
```

واربطها في `routes/web.php`:

```php
use App\Http\Controllers\BookController;

Route::get('/books', [BookController::class, 'index'])->name('books.index');
Route::get('/books/{id}', [BookController::class, 'show'])->name('books.show');
```

`[BookController::class, 'index']` تعني: «عند هذا المسار استدعِ الدالة `index` من `BookController`». (القالب `books.index` سننشئه في الدرس القادم.)

## متحكم الموارد: CRUD بسطر واحد

تطبيقات CRUD تحتاج دائمًا نفس سبع عمليات. Laravel يولّدها كلها:

1. **New Controller...** باسم `BookController` مع خيار **Resource controller (--resource)** وفي **Model** اكتب `Book`.
2. في `routes/web.php` سطر واحد:

```php
Route::resource('books', BookController::class);
```

ويُنشئ هذا السطر سبعة مسارات:

| الطريقة | العنوان | الدالة | الاسم | الغرض |
|---|---|---|---|---|
| GET | `/books` | `index` | `books.index` | القائمة |
| GET | `/books/create` | `create` | `books.create` | نموذج الإضافة |
| POST | `/books` | `store` | `books.store` | حفظ الجديد |
| GET | `/books/{book}` | `show` | `books.show` | عرض واحد |
| GET | `/books/{book}/edit` | `edit` | `books.edit` | نموذج التعديل |
| PUT/PATCH | `/books/{book}` | `update` | `books.update` | حفظ التعديل |
| DELETE | `/books/{book}` | `destroy` | `books.destroy` | الحذف |

قارن هذا بمشروع دورة PHP: هناك كتبنا `index.php` و`create.php` و`edit.php` و`delete.php` بأيدينا!

## تبويب Routes

افتح **Laravel > Route List** (أو تبويب **Routes** في لوحة Laravel): ستجد المسارات السبعة وغيرها، بأعمدة الطريقة والعنوان والاسم والإجراء والـ Middleware. **انقر مرتين** على `books.edit` لتنتقل إلى دالة `edit` في المتحكم. وبالزر الأيمن على مسار GET اختر **Open in Preview** لتفتحه في المعاينة.

## مجموعات المسارات و Middleware

**الـ Middleware** حارس يقف قبل المتحكم: مثلًا `auth` يرفض غير المسجلين ويحوّلهم لصفحة الدخول (مثل فحص `$_SESSION['user']` الذي كتبناه في دورة PHP، لكن جاهزًا):

```php
Route::middleware('auth')->group(function () {
    Route::resource('books', BookController::class)->except(['index', 'show']);
});
Route::resource('books', BookController::class)->only(['index', 'show']);
```

هنا: أي زائر يرى القائمة والتفاصيل، والإضافة والتعديل والحذف للمسجلين فقط. ولإنشاء Middleware خاص بك: الزر الأيمن على `app/Http/Middleware` (أو قائمة **Laravel > Make**) ثم **New Middleware...**.

## أخطاء شائعة

- **`404 Not Found` لمسار كتبته:** هل حفظت `web.php`؟ هل الطريقة صحيحة (GET أم POST)؟ راجع تبويب Routes. وإن كنت شغّلت `route:cache` سابقًا فشغّل **Laravel > Cache > route:clear**.
- **`Target class [BookController] does not exist`:** نسيت سطر `use App\Http\Controllers\BookController;` في أعلى `web.php`.
- **ترتيب المسارات:** `/books/{id}` قبل `/books/create` يجعل `create` تُفهم كـ `id`! ضع المسارات الثابتة أولًا (`Route::resource` يرتبها لك).
- **`419 Page Expired` عند إرسال نموذج POST:** نسيت `@csrf` داخل النموذج (الدرس 4).

## تمرين

### تمرين: مطابقة معامل اختياري

أكمل الدالة `greet_route(string $uri): string` التي تحاكي المسار `/hello/{name?}`: تُرجع `أهلًا يا NAME` إذا وُجد الاسم، و`أهلًا يا زائر` للعنوان `/hello`، و`404` لغير ذلك.

```php exercise
<?php
function greet_route(string $uri): string
{
    // استخدم preg_match مع النمط #^/hello(?:/([^/]+))?$#
    return "404";
}
echo greet_route("/hello/Sara"), "\n";
echo greet_route("/hello"), "\n";
echo greet_route("/bye"), "\n";
```

```php solution
<?php
function greet_route(string $uri): string
{
    if (!preg_match('#^/hello(?:/([^/]+))?$#', $uri, $m)) {
        return "404";
    }
    $name = $m[1] ?? 'زائر';
    return "أهلًا يا $name";
}
echo greet_route("/hello/Sara"), "\n";
echo greet_route("/hello"), "\n";
echo greet_route("/bye"), "\n";
```

```text output
أهلًا يا Sara
أهلًا يا زائر
404
```

## اختبر نفسك

```quiz
{"question": "كم مسارًا ينشئ `Route::resource('books', BookController::class)` ؟", "choices": ["1", "4", "7", "10"], "answer": 2, "explanation": "سبعة: index و create و store و show و edit و update و destroy."}
```

```quiz
{"question": "ما فائدة تسمية المسار بـ ->name('books.show')؟", "choices": ["تسريع الموقع", "توليد عنوانه بـ route('books.show') دون كتابته يدويًا", "حمايته بكلمة سر", "لا فائدة"], "answer": 1, "explanation": "تغيير العنوان لاحقًا لا يكسر الروابط لأنها تُولد من الاسم."}
```

```quiz
{"question": "أين تنقر بالزر الأيمن لإنشاء متحكم جديد؟", "choices": ["app/Http/Controllers", "public", "storage", "vendor"], "answer": 0, "explanation": "مجلد المتحكمات يعرض New Controller... بخياراته."}
```

## الخلاصة

- `Route::get('/uri', ...)` و`Route::post(...)`، و`{param}` لمعاملات العنوان، و`->name()` للتسمية.
- المتحكمات في `app/Http/Controllers`، تُنشأ بـ **New Controller...** وتُربط بـ `[Controller::class, 'method']`.
- `Route::resource` يولّد مسارات CRUD السبعة.
- تبويب **Routes** يعرض كل المسارات وينقلك إلى كودها بنقرة مزدوجة.
