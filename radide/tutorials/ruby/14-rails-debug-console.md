# الدرس 14: Rails 4: التنقيح والطرفية التفاعلية والاختبارات

التطبيق يعمل، لكن كيف تعرف **لماذا** لا يظهر كتاب معين؟ وكيف تتأكد أن تعديلًا جديدًا لم يكسر شيئًا قديمًا؟ في هذا الدرس نتعرف على ثلاث أدوات يستخدمها كل مطوري Rails يوميًا، وكلها في قائمة **Rails** داخل RAD IDE.

> **تشبيه:** المصحح (debugger) مثل **زر الإيقاف المؤقت في مباراة مسجلة**: توقف اللقطة وتنظر إلى موقع كل لاعب. والطرفية التفاعلية مثل **غرفة التجارب في المختبر**: تجرب أي شيء بأمان قبل أن تضعه في المنتج. والاختبارات مثل **قائمة الفحص قبل إقلاع الطائرة**.

## 1) التنقيح (Debugging) بنقاط التوقف

1. افتح `app/controllers/books_controller.rb`.
2. انقر في الهامش بجانب السطر `@books = Book.order(:title)` أو اضغط **F9** (**Toggle Breakpoint**، تبديل نقطة التوقف)، فتظهر نقطة حمراء.
3. اختر **Rails > Debug (F5: rails server under rdbg)** (تنقيح) أو اضغط **F5**. يبدأ الخادم تحت مصحح Ruby الرسمي `rdbg` (حزمة `debug`)، وتتصل به الـ IDE.
4. افتح `/books` في **Preview**. يتوقف التطبيق عند السطر، ويتلون السطر بالأصفر.

الآن يمكنك:

| الأداة | الاختصار | وظيفتها |
|---|---|---|
| **Step Over** (خطوة فوق) | F10 | نفّذ السطر الحالي وانتقل للتالي |
| **Step Into** (خطوة إلى الداخل) | F11 | ادخل داخل الدالة المستدعاة |
| **Continue** (متابعة) | F5 | أكمل حتى نقطة التوقف التالية |
| **Locals** (المتغيرات المحلية) | | قيم المتغيرات الحالية مثل `@books` و`params` |
| **Watch** (المراقبة) | | تعبيرات تكتبها لتراقب قيمتها |
| **Call Stack** (مكدس الاستدعاءات) | | سلسلة الدوال التي أوصلتنا إلى هنا |

نقاط التوقف تعمل أيضًا في النماذج (`app/models`) وفي **قوالب ERB** نفسها.

### طريقة سريعة: `debugger` في الكود

يمكنك أيضًا أن تكتب الكلمة `debugger` في أي سطر، فيتوقف التطبيق عندها كأنها نقطة توقف:

```ruby
def show
  @book = Book.find(params[:id])
  debugger if @book.pages.nil?   # توقف فقط في الحالة الغريبة
end
```

> **تذكير:** احذف `debugger` قبل أن ترفع الكود. ويمكنك أيضًا الطباعة في السجل: `Rails.logger.info "pages=#{@book.pages}"`، وتظهر في Output.

## 2) الطرفية التفاعلية: Rails Console

اختر **Rails > Console (rails console)** (الطرفية التفاعلية). تفتح **Rails Panel** على تبويب **Console**: سطر أوامر Ruby والتطبيق كله محمّل، بنماذجه وقاعدة بياناته. اكتب سطرًا واضغط Enter:

```ruby
Book.count
Book.first
Book.where(available: true).pluck(:title)
b = Book.new(title: "تجربة", pages: 10)
b.save
Book.last.title
Book.last.destroy
```

- كل سطر يُنفذ فورًا وتظهر نتيجته، ومعه أمر SQL الذي نفذته ActiveRecord (مفيد جدًا لتتعلم SQL).
- الطرفية تبقى مفتوحة بين الأوامر، فالمتغير `b` يبقى متاحًا للسطر التالي.
- في نفس اللوحة تبويب **Routes** (المسارات) وتبويب **Models** (النماذج) بأعمدتها وعلاقاتها.

> **انتبه:** الطرفية تعمل على قاعدة بيانات التطوير الحقيقية. `destroy` تحذف فعلًا! للتجربة الآمنة: `Book.transaction { ...; raise ActiveRecord::Rollback }` يلغي كل التغييرات في النهاية.

## 3) الاختبارات (Tests)

الاختبار برنامج صغير يتأكد أن جزءًا من تطبيقك يعمل كما تتوقع. Rails تستخدم مكتبة **Minitest**، والاختبارات في المجلد `test`.

### اختبار نموذج

```ruby
# test/models/book_test.rb
require "test_helper"

class BookTest < ActiveSupport::TestCase
  test "لا يُحفظ كتاب بلا عنوان" do
    book = Book.new(pages: 100)
    assert_not book.save
  end

  test "الملخص يحتوي العنوان والمؤلف" do
    book = Book.new(title: "Ruby", author: "منى", pages: 50)
    assert_equal "Ruby - منى (50 صفحة)", book.summary
  end
end
```

### اختبار متحكم

```ruby
# test/controllers/books_controller_test.rb
require "test_helper"

class BooksControllerTest < ActionDispatch::IntegrationTest
  test "صفحة الكتب تفتح" do
    get books_url
    assert_response :success
  end
end
```

التشغيل:

- **Rails > Tests > Run Tests (bin/rails test)** (تشغيل الاختبارات): كل الاختبارات، والنتيجة في Output.
- انقر بالزر الأيمن على ملف اختبار في **Solution Explorer** واختر **Run This Test File**.
- نافذة **Test Explorer** (مستكشف الاختبارات) تعرض كل اختبار بعلامة نجاح أو فشل.

`assert` تعني «تأكد أن...»، و`assert_equal متوقع, فعلي` تقارن قيمتين. وفكرة الاختبار نفسها يمكنك أن تجربها بـ Ruby العادية:

```ruby run
require "minitest"
require "stringio"

def summary(title, author)
  "#{title} - #{author}"
end

class SummaryTest < Minitest::Test
  def test_summary
    assert_equal "Ruby - منى", summary("Ruby", "منى")
  end

  def test_not_empty
    refute_empty summary("", "")
  end
end

# نشغّل الاختبارات ونلتقط تقريرها، ثم نطبع سطر النتيجة فقط (بقية التقرير فيه زمن التنفيذ)
report = StringIO.new
$stdout = report
Minitest.run(["--seed", "1"])
$stdout = STDOUT
puts report.string[/^\d+ runs, .*/]
```

```text output
2 runs, 3 assertions, 0 failures, 0 errors, 0 skips
```

جرّب أن تغيّر `"Ruby - منى"` إلى نص آخر وشغّل مرة أخرى: سترى `1 failures`، وهذا بالضبط ما يحدث في Test Explorer عندما يكسر تعديلٌ شيئًا.

## 4) أدوات أخرى في قائمة Rails

- **Bundler > Add Gem (bundle add)...** (إضافة Gem): يضيف حزمة إلى `Gemfile` ويثبتها، مثل `devise` لتسجيل الدخول.
- **Edit Credentials (credentials:edit)** (تعديل الأسرار): يفك تشفير `config/credentials.yml.enc` في تبويب محرر، وعند الحفظ يشفره من جديد. ضع هنا مفاتيح الخدمات وكلمات المرور، واقرأها في الكود بـ `Rails.application.credentials.dig(:smtp, :password)`.
- **Notes (TODO / FIXME)** (الملاحظات): يجمع كل تعليقات `# TODO` و`# FIXME` في المشروع.
- **About (rails about)** (حول التطبيق): إصدارات Ruby وRails وقاعدة البيانات.

## أخطاء شائعة

- **المصحح لا يتوقف:** تأكد أنك شغلت بـ **Debug** (F5) وليس **Server** (Ctrl+F5)، وأن الصفحة التي فتحتها تمر فعلًا بالسطر.
- **الاختبار يفشل بسبب بيانات قديمة:** الاختبارات تستخدم قاعدة بيانات منفصلة، وبياناتها من `test/fixtures`. عدّل الـ fixtures لتطابق قواعد التحقق الجديدة.
- **الطرفية لا ترى تعديلي:** إذا عدّلت نموذجًا والطرفية مفتوحة، اكتب `reload!` لتعيد تحميل الكود.

## اختبر نفسك

```quiz
{"question": "ما الفرق بين Rails > Server وRails > Debug؟", "choices": ["لا فرق", "Debug يشغّل الخادم تحت المصحح فتعمل نقاط التوقف", "Server أبطأ", "Debug يحذف قاعدة البيانات"], "answer": 1, "explanation": "Debug (F5) يشغل rails server تحت rdbg وتتصل الـ IDE به، أما Server فتشغيل عادي."}
```

```quiz
{"question": "أين تجرب أوامر مثل Book.count بسرعة؟", "choices": ["في قالب ERB", "في Rails Console", "في routes.rb", "في Gemfile"], "answer": 1, "explanation": "Rails Console طرفية Ruby والتطبيق محمّل فيها."}
```

```quiz
{"question": "ماذا تفعل assert_equal 5, x؟", "choices": ["تجعل x يساوي 5", "تنجح فقط إذا كانت قيمة x تساوي 5", "تطبع 5", "تحذف x"], "answer": 1, "explanation": "assert_equal تقارن القيمة المتوقعة بالفعلية ويفشل الاختبار إذا اختلفتا."}
```

## الخلاصة

- **F9** لنقطة توقف و**Rails > Debug** (F5) للتشغيل تحت `rdbg`، ثم F10 / F11 / Locals / Watch.
- **Rails > Console** لتجربة النماذج وقاعدة البيانات سطرًا سطرًا، و`reload!` بعد تعديل الكود.
- الاختبارات في `test/`، وتُشغل من **Rails > Tests** أو من **Test Explorer**.
- **Edit Credentials** للأسرار المشفرة، و**Bundler** للحزم.
