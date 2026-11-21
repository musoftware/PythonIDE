# الدرس 1: ما هو CodeIgniter 4؟ وإنشاء أول مشروع

**في هذا الدرس ستتعلم:**

- ما هو **إطار العمل** CodeIgniter 4، ولماذا يختاره كثيرون.
- فكرة **MVC**: النموذج والقالب والمتحكم.
- إنشاء مشروع جديد من **File > New Project...** في RAD IDE.
- خريطة مجلدات المشروع: أين تضع كل ملف.
- فتح مشروع CodeIgniter موجود (منسوخ من Git مثلًا).

## صندوق عدة خفيف

تخيل أنك تريد تصليح شيء في البيت. تستطيع أن تصنع كل أداة بنفسك (هذا ما فعلناه في دورة PHP: كتبنا الاتصال بقاعدة البيانات، والجلسات، والحماية بأيدينا)، أو تشتري **صندوق عدة** فيه كل الأدوات مرتبة في أماكنها.

**CodeIgniter 4** صندوق عدة **خفيف** للـ PHP:

- **صغير وسريع**: المشروع الجديد بضعة ميجابايتات، ويعمل على أبسط استضافة.
- **سهل التعلم**: قواعد قليلة وواضحة، وكود قريب جدًا من PHP العادي الذي تعرفه.
- **فيه كل الأساسيات**: المسارات، وقاعدة البيانات، والتحقق من المدخلات، والجلسات، وحماية CSRF و XSS، وأداة سطر أوامر اسمها **Spark**.

> **CodeIgniter أم Laravel؟** كلاهما ممتاز. Laravel مطبخ كامل بأجهزة كثيرة، و CodeIgniter صندوق عدة خفيف تفهم كل قطعة فيه بسرعة. ما تتعلمه هنا (المسارات والمتحكمات والترحيلات) ينتقل معك إلى أي إطار عمل.

## فكرة MVC

يقسم CodeIgniter الكود إلى ثلاثة أدوار، مثل مطعم:

| الدور | في المطعم | في CodeIgniter | المجلد |
|---|---|---|---|
| **Controller** (متحكم) | النادل: يستلم الطلب ويوزّع العمل | صنف يستقبل الطلب ويقرر ماذا يحدث | `app/Controllers` |
| **Model** (نموذج) | المخزن: فيه البيانات | صنف يقرأ ويكتب جدولًا في قاعدة البيانات | `app/Models` |
| **View** (قالب) | طريقة تقديم الطبق | ملف HTML فيه قليل من PHP | `app/Views` |

المحاكاة التالية بـ PHP عادية تبين كيف يتعاون الثلاثة (CodeIgniter يفعل ذلك لك بشكل أذكى):

```php run
<?php
// Model: البيانات
class ProductModel
{
    private array $rows = [
        ['id' => 1, 'name' => 'قلم', 'price' => 5],
        ['id' => 2, 'name' => 'دفتر', 'price' => 20],
    ];

    public function findAll(): array
    {
        return $this->rows;
    }
}

// View: طريقة العرض
function view(string $name, array $data): string
{
    $out = "== $name ==\n";
    foreach ($data['products'] as $p) {
        $out .= "- {$p['name']}: {$p['price']} جنيه\n";
    }
    return $out;
}

// Controller: يستلم الطلب ويربط الاثنين
class Products
{
    public function index(): string
    {
        $model = new ProductModel();
        return view('products/index', ['products' => $model->findAll()]);
    }
}

echo (new Products())->index();
```

```text output
== products/index ==
- قلم: 5 جنيه
- دفتر: 20 جنيه
```

لاحظ أن المتحكم **لا يعرف** كيف تُخزن البيانات، والقالب **لا يعرف** من أين جاءت. كل جزء مسؤول عن شيء واحد، فيسهل التعديل والاختبار.

## إنشاء مشروع جديد

1. **File > New Project...** (ملف > مشروع جديد...).
2. على اليسار اختر **Web > PHP Web Site** (ويب > موقع ويب PHP).
3. من القوالب اختر **CodeIgniter 4 App** (عليه شارة برتقالية **CI**).
4. اكتب اسم المشروع (مثلًا `MyShop`) والمجلد، ثم **OK**.
5. تظهر نافذة صغيرة لاختيار **قاعدة البيانات**:
   - **SQLite3 (writable/database.db)**: الأسهل؛ ملف واحد بلا خادم. اختره في هذا الدليل.
   - **MariaDB / MySQL** أو **PostgreSQL**: تشغّل الـ IDE خادمها المحلي وتكتب بيانات الدخول في `.env` تلقائيًا.

تشغّل الـ IDE `composer create-project codeigniter4/appstarter` مع شريط تقدّم (**يحتاج اتصالًا بالإنترنت** في المرة الأولى)، ثم تجهّز ملف `.env` بالقيم المناسبة لجهاز التطوير:

```ini
CI_ENVIRONMENT = development
app.indexPage = ''
database.default.database = database.db
database.default.DBDriver = SQLite3
database.default.DBPrefix =
database.default.foreignKeys = true
```

- `CI_ENVIRONMENT = development` تعرض صفحات أخطاء مفصلة وشريط التصحيح (الدرس 9).
- `app.indexPage = ''` تجعل العناوين نظيفة: `/products` بدل `/index.php/products`.
- ملف قاعدة SQLite يُنشأ في `writable/database.db`.

> **تلميح:** نسخة PHP المستخدمة تأتي من أدوات الـ IDE (`Tools > PHP Versions...`)، و Composer كذلك؛ لا تحتاج تثبيت شيء بنفسك.

## خريطة المشروع

افتح **Solution Explorer** (مستكشف الحلول). أهم ما فيه:

| المسار | ماذا فيه |
|---|---|
| `app/Config/Routes.php` | **المسارات**: أي عنوان يذهب إلى أي متحكم (الدرس 3) |
| `app/Controllers` | المتحكمات، وأولها `Home.php` و`BaseController.php` |
| `app/Models` | النماذج (الدرس 6) |
| `app/Views` | القوالب، وأولها `welcome_message.php` |
| `app/Database/Migrations` | الترحيلات: بناء الجداول بالكود (الدرس 5) |
| `app/Database/Seeds` | البيانات الأولية |
| `app/Config` | كل الإعدادات (`App.php` و`Database.php` و`Filters.php`...) |
| `public` | **جذر الموقع**: `index.php` والصور و CSS. الزائر لا يرى غيره |
| `writable` | ما يكتبه التطبيق: السجلات `logs` والذاكرة المؤقتة `cache` وملف `database.db` |
| `vendor` | كود CodeIgniter نفسه والحزم (لا تعدّل فيه) |
| `spark` | أداة سطر الأوامر: `php spark ...` |
| `.env` | إعدادات هذا الجهاز (لا تُرفع إلى Git) |

لماذا `public` منفصل؟ لأن الزائر يجب ألا يصل أبدًا إلى `app` أو `.env`. جذر الموقع هو `public` فقط، والـ IDE تضبطه هكذا تلقائيًا.

## فتح مشروع موجود

نسخت مشروع CodeIgniter من Git أو من زميل؟ استخدم **File > Open Folder...** (فتح مجلد...): تتعرف الـ IDE على المشروع من ملف `spark` وتعرض إنشاء ملف المشروع. وإذا كان مجلد `vendor` غير موجود (وهو الحال دائمًا في Git) تسألك:

> 'MyShop' needs its Composer packages (vendor/). Run 'composer install' now?

اختر **Yes**. وبعد التثبيت، إذا وجدت ترحيلات ولم توجد قاعدة البيانات بعد، تعرض: **Create the database now?** لتشغيل `php spark migrate --all` ثم `php spark db:seed DatabaseSeeder`. وتنشئ `.env` من القالب إن لم يكن موجودًا.

> **مثال جاهز:** في مجلد أمثلة الـ IDE مشروع متجر كامل `samples/Tests/Web/CodeIgniter_Shop` (منتجات، وتسجيل دخول، وواجهة JSON). افتحه بنفس الطريقة لترى كل ما في هذا الدليل يعمل معًا.

## أخطاء شائعة

- **فشل إنشاء المشروع:** غالبًا لا يوجد اتصال بالإنترنت، أو جدار حماية يمنع Composer. اقرأ نافذة **Output** (المخرجات).
- **وضع ملفاتك في `public`:** الصور و CSS فقط هناك. الكود في `app`.
- **تعديل ملفات `vendor`:** تُمسح عند أول `composer update`. عدّل في `app` دائمًا.
- **رفع `.env` إلى Git:** فيه كلمات سر. ملف `.gitignore` في المشروع يستثنيه فلا تحذف السطر.

## اختبر نفسك

```quiz
{"question": "في أي مجلد تضع المتحكمات؟", "choices": ["public", "app/Controllers", "vendor", "writable"], "answer": 1, "explanation": "المتحكمات في app/Controllers، والنماذج في app/Models، والقوالب في app/Views."}
```

```quiz
{"question": "لماذا جذر الموقع هو public وليس مجلد المشروع كله؟", "choices": ["لأنه أسرع", "حتى لا يصل الزائر إلى app و .env والكود", "لأن Composer يطلب ذلك", "لا يوجد سبب"], "answer": 1, "explanation": "الزائر يرى ما في public فقط؛ الكود والإعدادات وكلمات السر خارج متناوله."}
```

```quiz
{"question": "في MVC، من يقرر ماذا يحدث عند وصول الطلب؟", "choices": ["Model", "View", "Controller", "قاعدة البيانات"], "answer": 2, "explanation": "المتحكم (النادل) يستلم الطلب، ويطلب البيانات من النموذج، ويرسلها للقالب."}
```

## الخلاصة

- **CodeIgniter 4** إطار عمل PHP خفيف وسريع، مبني على **MVC**.
- **File > New Project... > Web > PHP Web Site > CodeIgniter 4 App** ينشئ مشروعًا كاملًا بقاعدة SQLite.
- الكود في `app`، والزائر يرى `public` فقط، وما يكتبه التطبيق في `writable`.
- فتح مشروع موجود يعرض `composer install` ثم إنشاء قاعدة البيانات.
