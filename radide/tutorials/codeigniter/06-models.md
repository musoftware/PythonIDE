# الدرس 6: النماذج و Query Builder

**في هذا الدرس ستتعلم:**

- إنشاء **نموذج** (Model) بأمر **New Model...** وخصائصه المهمة.
- القراءة: `find()` و`findAll()` و`where()` و`first()` و`like()` و`orderBy()`.
- الكتابة: `insert()` و`update()` و`save()` و`delete()`.
- **Query Builder**: بناء استعلامات SQL بالدوال، ولماذا هو آمن.
- **الكيانات** (Entities) باختصار.

## النموذج: موظف المخزن

في دورة PHP كتبنا `PDO` و`prepare` و`execute` في كل صفحة. **النموذج** يجمع كل ذلك في صنف واحد لكل جدول، مثل **موظف مخزن**: تطلب منه «هات المنتج رقم 5» أو «احفظ هذا المنتج» دون أن تعرف أين الرفوف.

1. الزر الأيمن على `app/Models` > **New Model...** (نموذج جديد...).
2. الاسم: `ProductModel`، و**Table** = `products`، و**Return type** = `array`، ثم **OK**.

تشغّل الـ IDE `php spark make:model ProductModel --table products --return array` وتفتح الملف. اضبط خصائصه:

```php
<?php

namespace App\Models;

use CodeIgniter\Model;

class ProductModel extends Model
{
    protected $table          = 'products';
    protected $primaryKey     = 'id';
    protected $returnType     = 'array';
    protected $useTimestamps  = true;                          // يملأ created_at و updated_at
    protected $allowedFields  = ['name', 'price', 'stock'];    // الأعمدة المسموح كتابتها
}
```

| الخاصية | معناها |
|---|---|
| `$table` | اسم الجدول |
| `$primaryKey` | المفتاح الأساسي (عادة `id`) |
| `$returnType` | شكل الصف المرجع: `array` أو `object` أو صنف كيان |
| `$allowedFields` | **قائمة بيضاء**: أي عمود ليس فيها يُتجاهل عند الحفظ |
| `$useTimestamps` | تعبئة `created_at` و`updated_at` تلقائيًا |
| `$useSoftDeletes` | الحذف «الناعم»: يكتب `deleted_at` بدل حذف الصف فعلًا |

## القراءة

في أي متحكم:

```php
$products = model(ProductModel::class);       // أو new ProductModel()

$one   = $products->find(5);                              // صف واحد أو null
$all   = $products->findAll();                            // كل الصفوف
$cheap = $products->where('price <', 10)->findAll();      // شرط
$first = $products->where('stock', 0)->first();           // أول صف يطابق
$found = $products->like('name', 'قلم')->orderBy('price', 'DESC')->findAll(10);
$count = $products->where('stock >', 0)->countAllResults();
$page  = $products->paginate(10);                         // صفحة من 10، ومعها $products->pager
```

لاحظ **السلسلة**: كل دالة (`where` ثم `like` ثم `orderBy`) تضيف جزءًا للاستعلام، والأخيرة (`findAll` أو `first`) **تنفذه**.

## الكتابة

```php
$id = $products->insert(['name' => 'ممحاة', 'price' => 3, 'stock' => 50]);   // يرجع رقم الصف الجديد
$products->update($id, ['price' => 4]);
$products->save(['id' => $id, 'stock' => 45]);    // save: تحديث إن وُجد id، وإلا إدراج
$products->delete($id);
```

## Query Builder: SQL بالدوال

خلف النموذج يعمل **Query Builder**: يبني جملة SQL من الدوال، ويرسل القيم **منفصلة** عن نص الجملة (استعلام مُجهّز)، فلا يمكن حقن SQL مهما كتب الزائر. تستطيع استخدامه مباشرة لجدول بلا نموذج:

```php
$db = db_connect();
$rows = $db->table('products')
           ->select('name, price')
           ->where('price >=', 5)
           ->orderBy('name')
           ->get()
           ->getResultArray();
```

هذا موقع مصغر لفكرته: صنف صغير يبني الجملة والقيم، ثم ينفذها بـ PDO على SQLite في الذاكرة:

```php run
<?php
class MiniBuilder
{
    private array $wheres = [];
    private array $binds = [];
    private string $order = '';

    public function __construct(private PDO $db, private string $table) {}

    public function where(string $field, mixed $value): static
    {
        // 'price <' => price < ?     'stock' => stock = ?
        $op = preg_match('/\s*(<=|>=|<>|<|>|=)$/', $field, $m) ? $m[1] : '=';
        $col = trim(preg_replace('/\s*(<=|>=|<>|<|>|=)$/', '', $field));
        $this->wheres[] = "$col $op ?";
        $this->binds[] = $value;
        return $this;                     // يرجع نفسه: هذا ما يسمح بالسلسلة
    }

    public function orderBy(string $col, string $dir = 'ASC'): static
    {
        $this->order = " ORDER BY $col $dir";
        return $this;
    }

    public function sql(): string
    {
        $where = $this->wheres ? ' WHERE ' . implode(' AND ', $this->wheres) : '';
        return "SELECT * FROM {$this->table}$where{$this->order}";
    }

    public function findAll(): array
    {
        $st = $this->db->prepare($this->sql());
        $st->execute($this->binds);
        return $st->fetchAll(PDO::FETCH_ASSOC);
    }
}

$db = new PDO('sqlite::memory:');
$db->exec("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER)");
$db->exec("INSERT INTO products (name, price, stock) VALUES ('قلم', 5, 100), ('دفتر', 20, 40), ('مسطرة', 8, 0)");

$q = (new MiniBuilder($db, 'products'))->where('price <', 10)->where('stock >', 0)->orderBy('price', 'DESC');
echo $q->sql(), "\n";
foreach ($q->findAll() as $p) {
    echo "- {$p['name']} ({$p['price']})\n";
}

// محاولة حقن SQL: تصبح مجرد نص يُبحث عنه
$evil = "x' OR '1'='1";
$rows = (new MiniBuilder($db, 'products'))->where('name', $evil)->findAll();
echo "نتائج الحقن: ", count($rows), "\n";
```

```text output
SELECT * FROM products WHERE price < ? AND stock > ? ORDER BY price DESC
- قلم (5)
نتائج الحقن: 0
```

لاحظ علامات `?` في الجملة: القيم لا تدخل نص SQL أبدًا، ولذلك فشل الحقن.

## دوال خاصة بك في النموذج

استعلام تكرره في أماكن كثيرة؟ ضعه دالة في النموذج نفسه:

```php
public function search(?string $term): static
{
    if ($term !== null && $term !== '') {
        $this->groupStart()->like('name', $term)->orLike('sku', $term)->groupEnd();
    }
    return $this->orderBy('created_at', 'DESC');
}

// في المتحكم:
$list = $this->products->search($q)->paginate(10);
```

هذه الدالة موجودة كما هي في مثال المتجر `CodeIgniter_Shop`. و**IntelliSense** يقترح أسماء الأعمدة داخل `where('` و`like('` و`orderBy('` من الترحيلات ومن قاعدة SQLite نفسها (الدرس 8).

## الكيانات (Entities) باختصار

مع `$returnType = 'array'` تكتب `$p['name']`. ولو أردت كائنات لها دوال، أنشئ **كيانًا**: الزر الأيمن على `app/Entities` > **New Entity...** باسم `Product`، ثم `$returnType = \App\Entities\Product::class`. بعدها تكتب `$p->name`، وتضيف دوال مثل `$p->priceWithTax()`. ابدأ بالمصفوفات، وانتقل للكيانات عندما تحتاجها.

## أخطاء شائعة

- **عمود لا يُحفظ دون أي رسالة:** ليس في `$allowedFields`. هذه حماية مقصودة.
- **`There is no data to insert`:** كل الأعمدة التي أرسلتها خارج `$allowedFields`.
- **`Call to a member function ... on null`:** `find(99)` أرجع `null` لأن الصف غير موجود. تحقق قبل الاستخدام (الدرس 7).
- **نسيان التنفيذ:** `$products->where(...)` وحدها استعلام لم يُنفذ. أكمل بـ `findAll()` أو `first()`.
- **بقايا شروط:** النموذج يمسح الشروط بعد كل تنفيذ، لكن إن بنيت استعلامًا ولم تنفذه ثم استعملت النموذج لاستعلام آخر ستختلط الشروط.

## تمرين

أضف إلى `MiniBuilder` دالة `like(string $col, string $text)` تضيف الشرط `col LIKE ?` مع القيمة `%text%` (مثل `like()` في CodeIgniter).

```php exercise
<?php
class MiniBuilder
{
    private array $wheres = [];
    private array $binds = [];

    public function __construct(private PDO $db, private string $table) {}

    // أضف like هنا

    public function findAll(): array
    {
        $where = $this->wheres ? ' WHERE ' . implode(' AND ', $this->wheres) : '';
        $st = $this->db->prepare("SELECT name FROM {$this->table}$where ORDER BY id");
        $st->execute($this->binds);
        return $st->fetchAll(PDO::FETCH_COLUMN);
    }
}

$db = new PDO('sqlite::memory:');
$db->exec("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)");
$db->exec("INSERT INTO products (name) VALUES ('قلم رصاص'), ('دفتر'), ('قلم حبر')");
echo implode(' | ', (new MiniBuilder($db, 'products'))->like('name', 'قلم')->findAll()), "\n";
```

```php solution
<?php
class MiniBuilder
{
    private array $wheres = [];
    private array $binds = [];

    public function __construct(private PDO $db, private string $table) {}

    public function like(string $col, string $text): static
    {
        $this->wheres[] = "$col LIKE ?";
        $this->binds[] = "%$text%";
        return $this;
    }

    public function findAll(): array
    {
        $where = $this->wheres ? ' WHERE ' . implode(' AND ', $this->wheres) : '';
        $st = $this->db->prepare("SELECT name FROM {$this->table}$where ORDER BY id");
        $st->execute($this->binds);
        return $st->fetchAll(PDO::FETCH_COLUMN);
    }
}

$db = new PDO('sqlite::memory:');
$db->exec("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)");
$db->exec("INSERT INTO products (name) VALUES ('قلم رصاص'), ('دفتر'), ('قلم حبر')");
echo implode(' | ', (new MiniBuilder($db, 'products'))->like('name', 'قلم')->findAll()), "\n";
```

```text output
قلم رصاص | قلم حبر
```

## اختبر نفسك

```quiz
{"question": "أرسلت ['name' => 'قلم', 'secret' => 1] إلى insert() و secret ليس في $allowedFields. ماذا يحدث؟", "choices": ["خطأ قاتل", "يُحفظ name ويُتجاهل secret", "يُحفظ الاثنان", "لا يُحفظ شيء"], "answer": 1, "explanation": "$allowedFields قائمة بيضاء؛ ما ليس فيها يُتجاهل لحماية الأعمدة الحساسة."}
```

```quiz
{"question": "أي سطر يُرجع صفًا واحدًا أو null؟", "choices": ["$products->findAll()", "$products->find(5)", "$products->where('stock', 0)", "$products->orderBy('name')"], "answer": 1, "explanation": "find(id) يرجع صفًا واحدًا بالمفتاح الأساسي، أو null إن لم يوجد."}
```

```quiz
{"question": "لماذا Query Builder آمن من حقن SQL؟", "choices": ["لأنه يحذف علامات التنصيص", "لأنه يرسل القيم منفصلة عن نص الجملة (علامات ?)", "لأنه يعمل مع SQLite فقط", "ليس آمنًا"], "answer": 1, "explanation": "القيم تُربط بالاستعلام المُجهّز ولا تصبح جزءًا من نص SQL."}
```

## الخلاصة

- **New Model...** على `app/Models` بخياري `--table` و`--return`، ثم اضبط `$allowedFields` و`$useTimestamps`.
- القراءة بـ `find` و`findAll` و`where` و`like` و`orderBy` و`first` و`paginate`، والكتابة بـ `insert` و`update` و`save` و`delete`.
- **Query Builder** يبني SQL بالدوال ويمنع الحقن.
- ضع الاستعلامات المتكررة دوالًا في النموذج، والكيانات عندما تحتاج كائنات لها سلوك.
