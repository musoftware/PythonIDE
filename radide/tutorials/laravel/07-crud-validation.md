# الدرس 7: تطبيق CRUD كامل مع التحقق

**في هذا الدرس ستبني** نسخة Laravel من مشروع «مكتبتي» الذي بنيناه في دورة PHP، وستلاحظ كم صار الكود أقصر:

- متحكم موارد كامل: `index` و`create` و`store` و`show` و`edit` و`update` و`destroy`.
- التحقق بـ `$request->validate()` وبصنف **Form Request**.
- **ربط النموذج بالمسار** (Route Model Binding).
- رسائل النجاح، والبحث، والصفحات.

## الخطوة 1: كل الملفات بأمر واحد

إن لم تفعل في الدرس السابق: الزر الأيمن على `app/Models` > **New Model...** باسم `Book` مع **-m** و**-f** و**-r**. ثم أكمل الترحيل (الدرس 5) وشغّل **Laravel > Database > Migrate**، وفي `routes/web.php`:

```php
use App\Http\Controllers\BookController;

Route::redirect('/', '/books');
Route::resource('books', BookController::class);
```

## الخطوة 2: المتحكم

```php
<?php

namespace App\Http\Controllers;

use App\Models\Book;
use Illuminate\Http\Request;

class BookController extends Controller
{
    public function index(Request $request)
    {
        $q = $request->query('q', '');
        $books = Book::query()
            ->when($q !== '', fn($query) => $query->where('title', 'like', "%$q%")
                                                ->orWhere('author', 'like', "%$q%"))
            ->orderBy('title')
            ->paginate(10)
            ->withQueryString();
        return view('books.index', compact('books', 'q'));
    }

    public function create()
    {
        return view('books.create', ['book' => new Book()]);
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'title' => 'required|string|max:200',
            'author' => 'required|string|max:120',
            'year' => 'nullable|integer|min:1000|max:2100',
            'price' => 'required|numeric|min:0',
        ]);
        $book = Book::create($data);
        return redirect()->route('books.index')->with('status', "أُضيف كتاب «{$book->title}»");
    }

    public function show(Book $book)
    {
        return view('books.show', compact('book'));
    }

    public function edit(Book $book)
    {
        return view('books.edit', compact('book'));
    }

    public function update(Request $request, Book $book)
    {
        $data = $request->validate([
            'title' => 'required|string|max:200',
            'author' => 'required|string|max:120',
            'year' => 'nullable|integer|min:1000|max:2100',
            'price' => 'required|numeric|min:0',
        ]);
        $book->update($data);
        return redirect()->route('books.index')->with('status', 'حُفظت التعديلات');
    }

    public function destroy(Book $book)
    {
        $book->delete();
        return redirect()->route('books.index')->with('status', "حُذف كتاب «{$book->title}»");
    }
}
```

لاحظ:

- **`Book $book` في معاملات الدالة** = ربط النموذج بالمسار: Laravel يقرأ `{book}` من العنوان، ويجلب الكتاب بـ `findOrFail` تلقائيًا (أو يرد بـ 404). لم نكتب `find` بأنفسنا!
- **`$request->validate([...])`**: إذا فشل التحقق **يعود** Laravel وحده إلى النموذج السابق مع الأخطاء والقيم القديمة (`old()`)، ولا يكمل الدالة. وإذا نجح يُرجع البيانات **المتحقق منها فقط**.
- **`->with('status', ...)`** رسالة فلاش في الجلسة، يعرضها التخطيط بـ `session('status')` (الدرس 4).
- `when(شرط, دالة)` يضيف جزء البحث للاستعلام فقط عندما توجد كلمة بحث.

## قواعد التحقق: لغة صغيرة

القاعدة `'required|string|max:200'` تعني: مطلوب، ونص، وأقصى طول 200. من أشهر القواعد: `required` و`nullable` و`string` و`integer` و`numeric` و`email` و`min:3` و`max:50` و`unique:books,title` و`exists:categories,id` و`in:a,b,c` و`confirmed` و`date`. و**IntelliSense** في الـ IDE يقترحها عندما تكتب `'title' => 'required|` (الدرس 8).

كيف تُفهم هذه السلسلة؟ إليك مدقق صغير بـ PHP عادية يطبّق بعض القواعد بنفس الصيغة:

```php run
<?php
function validate(array $data, array $rules): array
{
    $errors = [];
    foreach ($rules as $field => $ruleString) {
        $value = trim((string) ($data[$field] ?? ''));
        foreach (explode('|', $ruleString) as $rule) {
            [$name, $param] = array_pad(explode(':', $rule, 2), 2, null);
            $failed = match ($name) {
                'required' => $value === '',
                'numeric' => $value !== '' && !is_numeric($value),
                'min' => $value !== '' && (is_numeric($value) ? $value < $param : mb_strlen($value) < $param),
                'max' => $value !== '' && (is_numeric($value) ? $value > $param : mb_strlen($value) > $param),
                default => false,
            };
            if ($failed) {
                $errors[$field] = "الحقل $field لا يحقق القاعدة $rule";
                break;                     // خطأ واحد لكل حقل يكفي
            }
        }
    }
    return $errors;
}

$rules = ['title' => 'required|max:20', 'price' => 'required|numeric|min:0'];
print_r(validate(['title' => '', 'price' => 'abc'], $rules));
print_r(validate(['title' => 'الأيام', 'price' => '85'], $rules));
```

```text output
Array
(
    [title] => الحقل title لا يحقق القاعدة required
    [price] => الحقل price لا يحقق القاعدة numeric
)
Array
(
)
```

ورسائل Laravel الحقيقية تأتي من ملفات اللغة (`lang/`)، ويمكنك تعريبها.

## Form Request: التحقق في صنف مستقل

لاحظت أن قواعد `store` و`update` مكررة؟ ننقلها إلى صنف واحد. الزر الأيمن على `app/Http` (أو **Laravel > Make**) > **New Form Request...** باسم `BookRequest`:

```php
<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class BookRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;          // أو: return $this->user()?->is_admin;
    }

    public function rules(): array
    {
        return [
            'title' => 'required|string|max:200',
            'author' => 'required|string|max:120',
            'year' => 'nullable|integer|min:1000|max:2100',
            'price' => 'required|numeric|min:0',
        ];
    }
}
```

ثم في المتحكم تصبح الدالتان سطرين:

```php
public function store(BookRequest $request)
{
    $book = Book::create($request->validated());
    return redirect()->route('books.index')->with('status', "أُضيف كتاب «{$book->title}»");
}

public function update(BookRequest $request, Book $book)
{
    $book->update($request->validated());
    return redirect()->route('books.index')->with('status', 'حُفظت التعديلات');
}
```

## الخطوة 3: القوالب

أنشئ بـ **New Blade View...** (مع Layout = `layouts.app`) القوالب: `books.index` و`books.create` و`books.edit` و`books.show`، ونموذجًا مشتركًا `books._form`.

**`books/index.blade.php`:**

```blade
@extends('layouts.app')

@section('title', 'الكتب')

@section('content')
<h1>الكتب ({{ $books->total() }})</h1>

<form method="GET" action="{{ route('books.index') }}">
    <input name="q" value="{{ $q }}" placeholder="بحث بالعنوان أو المؤلف">
    <button>بحث</button>
</form>

<table>
    <tr><th>العنوان</th><th>المؤلف</th><th>السنة</th><th>السعر</th><th></th></tr>
    @forelse ($books as $book)
        <tr>
            <td><a href="{{ route('books.show', $book) }}">{{ $book->title }}</a></td>
            <td>{{ $book->author }}</td>
            <td>{{ $book->year }}</td>
            <td>{{ number_format($book->price, 2) }}</td>
            <td>
                <a href="{{ route('books.edit', $book) }}">تعديل</a>
                <form method="POST" action="{{ route('books.destroy', $book) }}" style="display:inline"
                      onsubmit="return confirm('حذف الكتاب؟')">
                    @csrf
                    @method('DELETE')
                    <button>حذف</button>
                </form>
            </td>
        </tr>
    @empty
        <tr><td colspan="5">لا توجد كتب.</td></tr>
    @endforelse
</table>

{{ $books->links() }}
@endsection
```

**`books/_form.blade.php`** (مشترك بين الإضافة والتعديل):

```blade
@csrf
<label>العنوان <input name="title" value="{{ old('title', $book->title) }}"></label>
@error('title') <span class="error">{{ $message }}</span> @enderror

<label>المؤلف <input name="author" value="{{ old('author', $book->author) }}"></label>
@error('author') <span class="error">{{ $message }}</span> @enderror

<label>السنة <input name="year" value="{{ old('year', $book->year) }}"></label>
<label>السعر <input name="price" value="{{ old('price', $book->price) }}"></label>
@error('price') <span class="error">{{ $message }}</span> @enderror

<button>حفظ</button>
```

**`books/create.blade.php`** و**`books/edit.blade.php`**:

```blade
@extends('layouts.app')
@section('content')
<h1>كتاب جديد</h1>
<form method="POST" action="{{ route('books.store') }}">
    @include('books._form')
</form>
@endsection
```

```blade
@extends('layouts.app')
@section('content')
<h1>تعديل: {{ $book->title }}</h1>
<form method="POST" action="{{ route('books.update', $book) }}">
    @method('PUT')
    @include('books._form')
</form>
@endsection
```

`old('title', $book->title)`: القيمة القديمة بعد فشل التحقق، وإلا قيمة الكتاب (فارغة في الإضافة).

## الخطوة 4: جرّب بأدوات الـ IDE

1. **Ctrl+F5** وافتح `/books`. أضف كتابًا، واترك السعر فارغًا مرة لترى رسالة الخطأ تحت الحقل والقيم باقية.
2. في **Requests** راقب: `POST /books` بالرمز `302` ثم `GET /books/create` (فشل التحقق يعيدك) أو `GET /books` (نجاح). والتعديل `POST /books/3` (مع `_method=PUT` في **Request Body**).
3. املأ بيانات تجريبية: Factory من الدرس 5 ثم **Laravel > Database > Seed (db:seed)**، وجرّب البحث والصفحات.
4. افتح الجدول في **View > Databases** لترى `created_at` و`updated_at` تُملأ تلقائيًا.
5. تبويب **Routes**: انقر مرتين على `books.update` لتصل إلى الدالة.

قارن المجهود بمشروع دورة PHP: CSRF، والتحويل، والفلاش، والتحقق مع القيم القديمة، و404 للكتاب غير الموجود، والصفحات... كلها صارت سطرًا أو أقل.

## أخطاء شائعة

- **التحقق يفشل ولا ترى رسائل:** القالب لا يعرض `@error` أو `$errors`. أضف `@error('field')`.
- **`MethodNotAllowedHttpException`:** نموذج التعديل بدون `@method('PUT')` أو نموذج الحذف بدون `@method('DELETE')`.
- **حقل لا يُحفظ رغم نجاح التحقق:** ليس في `$fillable` في النموذج، أو ليس في قواعد التحقق (فلا يُرجعه `validated()`).
- **`404` عند `/books/5/edit`:** الكتاب رقم 5 غير موجود؛ ربط النموذج يرد 404 تلقائيًا (وهذا صحيح).

## تمرين

### تمرين: قاعدة in

أضف إلى المدقق قاعدة `in:a,b,c` (القيمة يجب أن تكون من القائمة) وجرّبها على الحقل `lang` بالقاعدة `required|in:ar,en`.

```php exercise
<?php
function check_rule(string $value, string $rule): bool
{
    [$name, $param] = array_pad(explode(':', $rule, 2), 2, null);
    return match ($name) {
        'required' => $value !== '',
        default => true,
    };
}
foreach (['ar', 'fr', ''] as $v) {
    $ok = true;
    foreach (explode('|', 'required|in:ar,en') as $r) {
        $ok = $ok && check_rule($v, $r);
    }
    echo "[$v] ", $ok ? "مقبول" : "مرفوض", "\n";
}
```

```php solution
<?php
function check_rule(string $value, string $rule): bool
{
    [$name, $param] = array_pad(explode(':', $rule, 2), 2, null);
    return match ($name) {
        'required' => $value !== '',
        'in' => $value === '' || in_array($value, explode(',', $param), true),
        default => true,
    };
}
foreach (['ar', 'fr', ''] as $v) {
    $ok = true;
    foreach (explode('|', 'required|in:ar,en') as $r) {
        $ok = $ok && check_rule($v, $r);
    }
    echo "[$v] ", $ok ? "مقبول" : "مرفوض", "\n";
}
```

```text output
[ar] مقبول
[fr] مرفوض
[] مرفوض
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث إذا فشل $request->validate()؟", "choices": ["يتوقف الموقع بخطأ", "يعيد Laravel الزائر إلى النموذج مع الأخطاء والقيم القديمة", "يحفظ البيانات رغم ذلك", "يحذف الجلسة"], "answer": 1, "explanation": "التحويل للخلف تلقائي، و old() و @error تعرض القيم والرسائل."}
```

```quiz
{"question": "ما فائدة كتابة Book $book في معاملات دالة المتحكم؟", "choices": ["لا شيء", "يجلب Laravel الكتاب من {book} في العنوان تلقائيًا أو يرد 404", "ينشئ كتابًا جديدًا", "يحذف الكتاب"], "answer": 1, "explanation": "هذا ربط النموذج بالمسار (Route Model Binding)."}
```

```quiz
{"question": "من أين تنشئ صنف BookRequest للتحقق؟", "choices": ["New Form Request... من الزر الأيمن على app/Http أو Laravel > Make", "Tools > Options", "Site > Publish", "Help"], "answer": 0, "explanation": "make:request متاح كأمر New Form Request..."}
```

## الخلاصة

- متحكم الموارد + `Route::resource` + ربط النموذج = CRUD كامل بقليل من الكود.
- التحقق بـ `$request->validate([...])` أو صنف **Form Request** و`$request->validated()`.
- القوالب: `@forelse` و`links()` للصفحات، و`old()` و`@error` و`@csrf` و`@method` في النماذج.
- راقب كل ذلك في **Requests** و**Databases** و**Routes**.
