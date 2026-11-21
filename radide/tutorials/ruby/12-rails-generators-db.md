# الدرس 12: Rails 2: المولّدات وقاعدة البيانات

أغلب تطبيقات الويب تدور حول **بيانات**: كتب، مستخدمون، طلبات. في هذا الدرس نضيف إلى تطبيق المكتبة نموذجًا للكتب مع قاعدة بيانات، ونرى كيف تكتب **المولّدات** (generators) معظم الكود عنا.

> **تشبيه:** المولّد مثل **قالب الكعك**: بدل أن تشكل كل كعكة بيدك، تضغط القالب فتخرج كعكة كاملة الشكل، ثم تزينها كما تحب.

## النموذج وقاعدة البيانات: ActiveRecord

في Rails كل **نموذج** (Model) صنف Ruby يمثل **جدولًا** في قاعدة البيانات، وكل **كائن** منه يمثل **صفًا**:

| Ruby | قاعدة البيانات |
|---|---|
| الصنف `Book` | الجدول `books` |
| كائن `Book` | صف (سجل) في الجدول |
| الخاصية `book.title` | العمود `title` |

المكتبة التي تفعل ذلك اسمها **ActiveRecord**، وهي تكتب أوامر SQL بدلًا منك.

## Scaffold: كل شيء دفعة واحدة

أسرع طريقة لترى Rails تعمل: **Rails > Generate > New Scaffold...** (هيكل كامل جديد...)، واكتب:

- **Name:** `Book`
- **Attributes:** `title:string author:string pages:integer available:boolean`
- اترك **Run db:migrate afterwards** مفعّلًا.

تنفذ الـ IDE `bin/rails generate scaffold Book title:string author:string pages:integer available:boolean` ثم `bin/rails db:migrate`، فتحصل على:

- النموذج `app/models/book.rb`.
- **ترحيل** (migration) في `db/migrate` ينشئ الجدول.
- المتحكم `BooksController` بالإجراءات السبعة: `index` و`show` و`new` و`create` و`edit` و`update` و`destroy`.
- القوالب في `app/views/books`، والسطر `resources :books` في المسارات.

شغّل **Rails > Server** وافتح `/books` في Preview: صفحة كاملة لإضافة الكتب وعرضها وتعديلها وحذفها، دون أن تكتب سطرًا!

> **أنواع الأعمدة:** `string` (نص قصير) و`text` (نص طويل) و`integer` و`decimal` و`boolean` و`date` و`datetime` و`references` (ربط بجدول آخر). تظهر قائمة الأنواع في نافذة المولّد.

## الترحيل (Migration): تاريخ قاعدة البيانات

الترحيل ملف Ruby يصف **تغييرًا** في بنية قاعدة البيانات. هذا ما كتبه المولّد:

```ruby
# db/migrate/20260101120000_create_books.rb
class CreateBooks < ActiveRecord::Migration[8.0]
  def change
    create_table :books do |t|
      t.string :title
      t.string :author
      t.integer :pages
      t.boolean :available

      t.timestamps
    end
  end
end
```

`t.timestamps` تضيف عمودين تلقائيًا: `created_at` و`updated_at`.

أوامر قاعدة البيانات في **Rails > Database**:

| الأمر | معناه |
|---|---|
| **Migrate (db:migrate)** (ترحيل) | ينفذ الترحيلات الجديدة |
| **Rollback (db:rollback)** (تراجع) | يتراجع عن آخر ترحيل |
| **Migration Status (db:migrate:status)** | أي الترحيلات نُفذ وأيها لم يُنفذ |
| **Seed (db:seed)** (تعبئة البيانات) | ينفذ `db/seeds.rb` لإدخال بيانات أولية |
| **Prepare (db:prepare)** | ينشئ قاعدة البيانات ويرحّلها إن لزم |
| **Show in Databases** | يفتح قاعدة بيانات التطبيق في نافذة **Databases** (قواعد البيانات) لترى الجداول والبيانات وتكتب SQL |

وعلى ملف ترحيل في **Solution Explorer** انقر بالزر الأيمن لتجد **Run This Migration** و**Revert This Migration**.

### إضافة عمود لاحقًا

نسينا سنة النشر! من **Rails > Generate > New Migration...** (ترحيل جديد...):

- **Name:** `AddYearToBooks`
- **Columns:** `year:integer`

الاسم بصيغة `AddXToY` يفهمه Rails فيكتب الترحيل كاملًا:

```ruby
class AddYearToBooks < ActiveRecord::Migration[8.0]
  def change
    add_column :books, :year, :integer
  end
end
```

## النموذج: التحقق والعلاقات

افتح `app/models/book.rb` وأضف **قواعد التحقق** (validations): لا يُحفظ كتاب بلا عنوان، وعدد الصفحات رقم موجب:

```ruby
class Book < ApplicationRecord
  belongs_to :category, optional: true
  validates :title, presence: true
  validates :pages, numericality: { greater_than: 0 }, allow_nil: true

  scope :available, -> { where(available: true) }

  def summary
    "#{title} - #{author} (#{pages} صفحة)"
  end
end
```

```ruby
class Category < ApplicationRecord
  has_many :books
  validates :name, presence: true, uniqueness: true
end
```

- `validates` تمنع الحفظ إذا لم تتحقق القاعدة، وتملأ رسائل الخطأ التي يعرضها القالب تلقائيًا.
- `has_many :books` و`belongs_to :category` **علاقات** بين الجداول (يحتاج الكتاب عمود `category_id`: أنشئه بمولّد النموذج `Category name:string` ثم ترحيل `AddCategoryToBooks category:references`).
- `scope` استعلام له اسم: `Book.available`.

> **ميزة في RAD IDE:** اكتب `book.` فيظهر الإكمال التلقائي بأعمدة الجدول من `db/schema.rb` والعلاقات، واضغط **F12** على `category` لتنتقل إلى تعريفها.

## البيانات الأولية: `db/seeds.rb`

```ruby
# db/seeds.rb
Book.destroy_all
[["Ruby للمبتدئين", "منى", 250], ["أسرار Rails", "خالد", 410]].each do |title, author, pages|
  Book.create!(title: title, author: author, pages: pages, available: true)
end
puts "تمت إضافة #{Book.count} كتاب"
```

ثم **Rails > Database > Seed (db:seed)**، وانظر النتيجة في Output ثم في **Show in Databases**.

## أهم استعلامات ActiveRecord

جرّب هذه في **Rails > Console** (الدرس 14):

```ruby
Book.all                                   # كل الكتب
Book.count                                 # العدد
Book.find(1)                               # بالرقم (id)
Book.find_by(title: "أسرار Rails")         # أول كتاب يطابق
Book.where(available: true).order(:title)  # فلترة وترتيب
Book.where("pages > ?", 300)               # شرط بقيمة آمنة
book = Book.new(title: "", pages: -5)
book.valid?                                # false
book.errors.full_messages                  # رسائل الأخطاء
book.update(title: "عنوان جديد", pages: 120)
book.destroy
```

لاحظ `where("pages > ?", 300)`: علامة `?` تجعل Rails تضع القيمة بأمان، فلا تكتب أبدًا قيمة من المستخدم داخل نص SQL مباشرة (هذا يحميك من هجوم SQL Injection).

## المتحكم الذي كتبه Scaffold

نظرة على إجراءين من `BooksController`:

```ruby
class BooksController < ApplicationController
  before_action :set_book, only: %i[show edit update destroy]

  def index
    @books = Book.order(:title)
  end

  def create
    @book = Book.new(book_params)
    if @book.save
      redirect_to @book, notice: "تم حفظ الكتاب"
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def set_book
    @book = Book.find(params[:id])
  end

  def book_params
    params.require(:book).permit(:title, :author, :pages, :available)
  end
end
```

- `params` قاموس بما أرسله المستخدم من النموذج (form) أو الرابط.
- `permit` تسمح فقط بالأعمدة المذكورة (حماية من إرسال أعمدة لا يجب أن يغيرها المستخدم).
- `redirect_to` تنقل المتصفح لصفحة أخرى، و`render` تعرض قالبًا.

## التراجع عن مولّد

أخطأت في الاسم؟ **Rails > Generate > Undo a Generator (rails destroy)...** (تراجع عن مولّد) واختر النوع والاسم، فيحذف Rails الملفات التي أنشأها. إذا كنت قد نفذت الترحيل، فنفذ **Rollback** أولًا.

## أخطاء شائعة

- **`ActiveRecord::PendingMigrationError`:** يوجد ترحيل لم يُنفذ. اختر **Rails > Database > Migrate**.
- **`NoMethodError: undefined method 'year'`:** أضفت العمود في الترحيل لكن لم تنفذه، أو كتبت اسمه خطأ.
- **`ActiveRecord::RecordInvalid`:** استخدمت `create!` و`save!` (بعلامة التعجب) مع بيانات لا تحقق قواعد التحقق، فأثارت Rails خطأ. بدون `!` تُرجع `false` فقط.

## اختبر نفسك

```quiz
{"question": "النموذج Book في Rails يرتبط تلقائيًا بأي جدول؟", "choices": ["Book", "book", "books", "tbl_book"], "answer": 2, "explanation": "الاتفاق: اسم الصنف مفرد بحرف كبير، والجدول جمع بحروف صغيرة."}
```

```quiz
{"question": "ماذا يفعل الأمر db:rollback؟", "choices": ["يحذف قاعدة البيانات", "يتراجع عن آخر ترحيل", "يضيف بيانات أولية", "يشغّل الخادم"], "answer": 1, "explanation": "rollback تعكس آخر ترحيل نُفذ."}
```

```quiz
{"question": "لماذا نكتب where(\"pages > ?\", n) بدل وضع n داخل النص مباشرة؟", "choices": ["لأنه أسرع فقط", "لكي تضع Rails القيمة بأمان وتمنع SQL Injection", "لأن ? إجبارية", "لا فرق"], "answer": 1, "explanation": "علامة ? تجعل القيمة تُمرر منفصلة عن نص SQL فلا يمكن أن تغير معنى الاستعلام."}
```

## الخلاصة

- **New Scaffold...** ينشئ النموذج والترحيل والمتحكم والقوالب والمسارات دفعة واحدة.
- الترحيلات تصف تغييرات قاعدة البيانات، وتُنفذ من **Rails > Database > Migrate**.
- النموذج يحمل قواعد التحقق `validates` والعلاقات `has_many` / `belongs_to`.
- `db/seeds.rb` للبيانات الأولية، و**Show in Databases** لرؤية الجداول داخل الـ IDE.
