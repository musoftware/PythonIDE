# الدرس 6: Eloquent و Tinker

**في هذا الدرس ستتعلم:**

- **Eloquent**: التعامل مع جداول قاعدة البيانات **ككائنات** PHP.
- إنشاء نموذج بأمر **New Model...** مع ترحيله ومتحكمه وFactory دفعة واحدة.
- الاستعلامات: `all` و`find` و`where` و`orderBy` و`paginate`، والإضافة والتعديل والحذف.
- **العلاقات**: `hasMany` و`belongsTo`.
- تجربة كل ذلك مباشرة في **Tinker** داخل لوحة Laravel.

## من SQL إلى كائنات

في دورة PHP كتبنا: `$stmt = db()->prepare("SELECT * FROM books WHERE id = ?"); $stmt->execute([$id]);`. مع **Eloquent** نكتب:

```php
$book = Book::find($id);
echo $book->title;
```

كل **صف** في جدول `books` يصبح **كائنًا** من الصنف `Book`، وكل **عمود** خاصية فيه. وEloquent يكتب SQL المُجهّز (الآمن من الحقن) نيابة عنك.

## إنشاء النموذج

1. انقر بالزر الأيمن على `app/Models` واختر **New Model...** (نموذج جديد...).
2. الاسم: `Book`، وفعّل: **Migration (-m)** و**Factory (-f)** و**Seeder (-s)** و**Resource controller (-r)**.
3. **OK**: يُنشأ `app/Models/Book.php`، وترحيل `create_books_table`، و`BookFactory`، و`BookSeeder`، و`BookController` بدوال الموارد السبع.

(وفي لوحة الأوامر يوجد اختصار **Laravel: make:model -mcr**.) إن كنت أنشأت ترحيل `books` في الدرس السابق فلا تفعّل **-m** هذه المرة.

النموذج نفسه قصير جدًا، لأن Laravel يستنتج كل شيء من الاسم: الصنف `Book` يقابل الجدول `books`:

```php
<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Book extends Model
{
    use HasFactory;

    protected $fillable = ['title', 'author', 'year', 'price', 'category_id'];

    protected function casts(): array
    {
        return ['price' => 'decimal:2', 'year' => 'integer'];
    }
}
```

- `$fillable` قائمة الأعمدة **المسموح** ملؤها دفعة واحدة من بيانات النموذج (حماية من «الإسناد الجماعي»: لا يستطيع زائر إرسال `is_admin=1` ليغيّر عمودًا لم تسمح به).
- `casts` تحويل الأنواع تلقائيًا.

> **تنقّل سريع:** الزر الأيمن على `Book.php` في Solution Explorer يعرض **Open Migration** و**Open Controller** و**Open Factory**: تقفز مباشرة إلى الملفات المرتبطة بالنموذج.

## الاستعلامات

```php
$all = Book::all();                                   // كل الكتب (مجموعة Collection)
$book = Book::find(3);                                // بالرقم، أو null
$book = Book::findOrFail(3);                          // بالرقم، أو صفحة 404 تلقائيًا
$cheap = Book::where('price', '<', 100)->orderBy('title')->get();
$count = Book::where('author', 'نجيب محفوظ')->count();
$page = Book::latest()->paginate(10);                 // صفحات من 10 كتب مع روابط التنقل

// إضافة
$b = Book::create(['title' => 'الأيام', 'author' => 'طه حسين', 'price' => 85]);

// تعديل
$b->price = 90;
$b->save();
// أو
$b->update(['price' => 95]);

// حذف
$b->delete();
```

لاحظ «السلسلة»: `where(...)->orderBy(...)->get()` كل دالة تضيف جزءًا للاستعلام، و`get()` تنفذه. النتيجة **مجموعة** (Collection): مصفوفة ذكية فيها دوال مثل `filter` و`map` و`sum` و`pluck`. إليك محاكاة صغيرة بـ PHP عادية تبيّن كيف تعمل هذه السلسلة على مصفوفة:

```php run
<?php
class MiniCollection
{
    public function __construct(private array $items) {}

    public function where(string $key, string $op, $value): static
    {
        return new static(array_values(array_filter($this->items, fn($i) => match ($op) {
            '<' => $i[$key] < $value,
            '>' => $i[$key] > $value,
            '=' => $i[$key] == $value,
        })));
    }

    public function sortBy(string $key): static
    {
        $items = $this->items;
        usort($items, fn($a, $b) => $a[$key] <=> $b[$key]);
        return new static($items);
    }

    public function pluck(string $key): array
    {
        return array_column($this->items, $key);
    }

    public function sum(string $key): float
    {
        return array_sum($this->pluck($key));
    }
}

$books = new MiniCollection([
    ['title' => 'الثلاثية', 'price' => 240],
    ['title' => 'الأيام', 'price' => 85],
    ['title' => 'اللص والكلاب', 'price' => 60],
]);
$cheap = $books->where('price', '<', 100)->sortBy('price');
echo implode('، ', $cheap->pluck('title')), "\n";
echo "المجموع: ", $cheap->sum('price'), "\n";
```

```text output
اللص والكلاب، الأيام
المجموع: 145
```

الفرق: Eloquent يحوّل `where` و`orderBy` إلى **SQL** يُنفّذ في قاعدة البيانات (أسرع بكثير مع آلاف الصفوف)، أما دوال المجموعة بعد `get()` فتعمل في PHP مثل محاكاتنا.

## العلاقات

لنفترض أن لكل كتاب **تصنيفًا** (رواية، تاريخ...). جدول `categories`، وفي `books` عمود `category_id`:

```php
// ترحيل: $table->foreignId('category_id')->nullable()->constrained();

class Category extends Model
{
    public function books()
    {
        return $this->hasMany(Book::class);        // التصنيف له كتب كثيرة
    }
}

class Book extends Model
{
    public function category()
    {
        return $this->belongsTo(Category::class);  // الكتاب ينتمي لتصنيف
    }
}

// الاستخدام
echo $book->category->name;
foreach ($category->books as $b) { ... }
$novels = Category::where('name', 'رواية')->first()->books()->where('price', '<', 100)->get();

// تحميل مسبق لتجنب استعلام لكل كتاب (مشكلة N+1)
$books = Book::with('category')->get();
```

## Tinker: جرّب قبل أن تكتب

**Tinker** سطر أوامر PHP **داخل تطبيقك**: النماذج وقاعدة البيانات والإعدادات كلها جاهزة. افتحه من **Laravel > Tinker** أو تبويب **Tinker** في لوحة Laravel (أو لوحة الأوامر: **Laravel: Open Tinker**)، واكتب سطرًا ثم Enter:

```text
Book::count()
=> 30
$b = Book::create(['title' => 'تجربة', 'author' => 'أنا', 'price' => 10]);
$b->id
=> 31
Book::where('price', '<', 50)->pluck('title')
$b->delete()
=> true
```

(السطر الذي يبدأ بـ `=>` هو الناتج الذي يظهر تحت ما كتبته.) Tinker في الـ IDE **جلسة مستمرة**: المتغيرات (مثل `$b`) تبقى بين الأسطر. وإن غيّرت كود النموذج اضغط **Restart** ليقرأ التعديلات، والسهمان لأعلى ولأسفل يستعيدان الأسطر السابقة. استخدمه لتجربة الاستعلام قبل نقله إلى المتحكم، ولفحص البيانات بسرعة، ولإصلاح صف بعينه.

## أخطاء شائعة

- **`MassAssignmentException` / حقل لا يُحفظ:** العمود ليس في `$fillable`.
- **`Call to a member function ... on null`:** `Book::find(99)` أرجع `null` لأن الكتاب غير موجود. استخدم `findOrFail` في المتحكمات.
- **نسيان `get()`:** `Book::where(...)` وحدها **استعلام لم يُنفّذ** بعد، لا نتائج.
- **مشكلة N+1:** حلقة على 100 كتاب تطبع `$book->category->name` تنفّذ 101 استعلام. استخدم `Book::with('category')`.

## تمرين

### تمرين: دالة avg للمجموعة

أضف إلى `MiniCollection` دالة `avg(string $key): float` (المتوسط)، واطبع متوسط الأسعار للكتب الثلاثة: `128.33` (مقربًا لرقمين).

```php exercise
<?php
class MiniCollection
{
    public function __construct(private array $items) {}

    public function sum(string $key): float
    {
        return array_sum(array_column($this->items, $key));
    }
    // avg
}
$books = new MiniCollection([['price' => 240], ['price' => 85], ['price' => 60]]);
echo round($books->avg('price'), 2), "\n";
```

```php solution
<?php
class MiniCollection
{
    public function __construct(private array $items) {}

    public function sum(string $key): float
    {
        return array_sum(array_column($this->items, $key));
    }

    public function avg(string $key): float
    {
        return count($this->items) ? $this->sum($key) / count($this->items) : 0;
    }
}
$books = new MiniCollection([['price' => 240], ['price' => 85], ['price' => 60]]);
echo round($books->avg('price'), 2), "\n";
```

```text output
128.33
```

## اختبر نفسك

```quiz
{"question": "النموذج Book يقابل أي جدول افتراضيًا؟", "choices": ["Book", "book", "books", "tbl_book"], "answer": 2, "explanation": "Eloquent يستنتج اسم الجدول بصيغة الجمع والحروف الصغيرة: books."}
```

```quiz
{"question": "ما وظيفة $fillable؟", "choices": ["تسريع الاستعلامات", "تحديد الأعمدة المسموح ملؤها دفعة واحدة (حماية من الإسناد الجماعي)", "تشفير الأعمدة", "ترتيب النتائج"], "answer": 1, "explanation": "Book::create($data) لا يملأ إلا الأعمدة المذكورة في $fillable."}
```

```quiz
{"question": "أين تجرّب Book::count() مباشرة داخل التطبيق؟", "choices": ["تبويب Tinker في لوحة Laravel", "نافذة Toolbox", "Site Settings", "Help"], "answer": 0, "explanation": "Tinker سطر أوامر PHP والتطبيق محمّل فيه."}
```

## الخلاصة

- Eloquent: كل صف كائن، وكل عمود خاصية، و`Book::where(...)->get()` بدل SQL اليدوي.
- **New Model...** بخيارات `-m -c -f -s -r` ينشئ النموذج وكل ما يرتبط به، والزر الأيمن على النموذج ينقلك إليها.
- العلاقات: `hasMany` و`belongsTo`، و`with()` لتجنب N+1.
- **Tinker** في لوحة Laravel لتجربة الاستعلامات قبل كتابتها.
