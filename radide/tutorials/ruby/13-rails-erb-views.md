# الدرس 13: Rails 3: قوالب ERB والعروض

الصفحة التي يراها المستخدم في Rails تُكتب في ملف **ERB** (Embedded Ruby، أي «روبي مضمّن»): HTML عادي تتخلله أجزاء صغيرة من Ruby. الخبر الجميل أن ERB جزء من Ruby نفسها، فنستطيع أن نتعلمه ونجربه هنا مباشرة قبل أن نستخدمه في Rails.

> **تشبيه:** قالب ERB مثل **شهادة تقدير مطبوعة** فيها فراغات: «تُمنح هذه الشهادة إلى ...... لتفوقه في ......». Ruby تملأ الفراغات بالأسماء الحقيقية قبل أن تُسلم الشهادة.

## الوسمان الأساسيان

| الوسم | معناه |
|---|---|
| `<%= ... %>` | نفّذ كود Ruby **واطبع** نتيجته في الصفحة |
| `<% ... %>` | نفّذ كود Ruby **دون** طباعة (للشروط والحلقات) |
| `<%# ... %>` | تعليق لا يظهر في الصفحة |

## ERB خارج Rails: لنجرّب

مكتبة `erb` تأتي مع Ruby. نكتب القالب في نص، ثم نملؤه بالمتغيرات الموجودة (`binding` تعني «المتغيرات الحالية»):

```ruby run
require "erb"

template = ERB.new(<<~'HTML')
  <h1>مرحبًا يا <%= name %></h1>
  <p>لديك <%= messages %> رسائل جديدة</p>
HTML

name = "سارة"
messages = 3
puts template.result(binding)
```

```text output
<h1>مرحبًا يا سارة</h1>
<p>لديك 3 رسائل جديدة</p>
```

- `<<~'HTML' ... HTML` نص من عدة أسطر (heredoc)، والعلامة `'` تمنع Ruby من تفسير `#{}` داخله.
- `result(binding)` تملأ القالب وتُرجع النص النهائي.

## الحلقات والشروط داخل القالب

```ruby run
require "erb"

books = [
  { title: "Ruby للمبتدئين", pages: 250, available: true },
  { title: "أسرار Rails", pages: 410, available: false }
]

template = ERB.new(<<~'HTML', trim_mode: "-")
  <ul>
  <% books.each do |book| -%>
    <li><%= book[:title] %> (<%= book[:pages] %> صفحة)
  <% if book[:available] -%>
      <span>متاح</span>
  <% else -%>
      <span>مُعار</span>
  <% end -%>
    </li>
  <% end -%>
  </ul>
HTML

puts template.result(binding)
```

```text output
<ul>
  <li>Ruby للمبتدئين (250 صفحة)
    <span>متاح</span>
  </li>
  <li>أسرار Rails (410 صفحة)
    <span>مُعار</span>
  </li>
</ul>
```

- `<% books.each do |book| %>` تبدأ حلقة، و`<% end %>` تنهيها؛ كل ما بينهما يتكرر.
- `-%>` (مع `trim_mode: "-"`) تحذف السطر الفارغ الذي يتركه الوسم، لذلك كتبنا وسوم `<% %>` في أول السطر. في Rails لا يهمك ذلك، فالمسافات الزائدة لا تظهر في المتصفح.

## الأمان: الهروب من HTML

ماذا لو كتب مستخدم في عنوان كتاب: `<script>alert('hack')</script>`؟ إذا طُبع كما هو فسيُنفذ في متصفح كل من يفتح الصفحة! هذا هجوم اسمه **XSS**. الحل: **تهريب** (escape) الرموز الخاصة:

```ruby run
require "erb"
include ERB::Util

title = "<script>alert('hack')</script>"
puts html_escape(title)
puts ERB.new("<p><%= h(title) %></p>").result(binding)
```

```text output
&lt;script&gt;alert(&#39;hack&#39;)&lt;/script&gt;
<p>&lt;script&gt;alert(&#39;hack&#39;)&lt;/script&gt;</p>
```

> **مهم:** في Rails لا تحتاج إلى `h()`، لأن `<%= %>` تهرّب كل شيء **تلقائيًا**. إذا أردت فعلًا طباعة HTML موثوق (كتبته أنت) فاستخدم `raw` أو `html_safe`، ولا تستخدمهما أبدًا مع نص من المستخدم.

## ERB في Rails: قالب قائمة الكتب

هذا قالب `app/views/books/index.html.erb` بعد تعديله:

```erb
<h1>الكتب (<%= @books.size %>)</h1>

<% if notice %>
  <p class="notice"><%= notice %></p>
<% end %>

<table>
  <tr><th>العنوان</th><th>المؤلف</th><th></th></tr>
  <% @books.each do |book| %>
    <tr>
      <td><%= link_to book.title, book %></td>
      <td><%= book.author %></td>
      <td><%= link_to "تعديل", edit_book_path(book) %></td>
    </tr>
  <% end %>
</table>

<%= link_to "كتاب جديد", new_book_path %>
```

## الدوال المساعدة (Helpers)

Rails تعطيك دوال جاهزة تكتب HTML عنك:

| الدالة | تكتب |
|---|---|
| `link_to "نص", path` | رابط `<a href="...">` |
| `image_tag "logo.png"` | صورة `<img>` |
| `form_with model: @book` | نموذج إدخال كامل مرتبط بالكائن |
| `number_to_currency 12.5` | `$12.50` |
| `time_ago_in_words(t)` | «منذ 3 دقائق» |
| `pluralize 3, "book"` | `3 books` |

ونموذج الإدخال `_form.html.erb` الذي كتبه Scaffold:

```erb
<%= form_with model: @book do |f| %>
  <% @book.errors.full_messages.each do |msg| %>
    <p class="error"><%= msg %></p>
  <% end %>

  <%= f.label :title, "العنوان" %>
  <%= f.text_field :title %>

  <%= f.label :pages, "عدد الصفحات" %>
  <%= f.number_field :pages %>

  <%= f.check_box :available %> متاح

  <%= f.submit "حفظ" %>
<% end %>
```

يمكنك أن تكتب دوالك المساعدة في `app/helpers/books_helper.rb`، وهي دوال Ruby عادية:

```ruby
module BooksHelper
  def availability_badge(book)
    book.available ? "متاح" : "مُعار"
  end
end
```

## التخطيط (Layout) والأجزاء (Partials)

- **التخطيط** `app/views/layouts/application.html.erb` هو الإطار المشترك لكل الصفحات (الرأس والقائمة والتذييل)، وفيه السطر `<%= yield %>` الذي يُوضع مكانه قالب الصفحة الحالية. لاحظ: `yield` نفسها التي تعلمناها مع الكتل!
- **الجزء** (partial) قالب صغير يبدأ اسمه بشرطة سفلية مثل `_book.html.erb`، ويُستدعى بـ `<%= render "book", book: book %>` أو باختصار `<%= render @books %>`.

من **Solution Explorer** انقر بالزر الأيمن على مجلد في `app/views` واختر **New View...** (قالب جديد...) أو **New Partial...** (عرض جزئي جديد...).

> **ميزة في RAD IDE:** ملفات `.erb` تفتح بتلوين HTML وRuby معًا، والإكمال التلقائي داخل `<%= %>` يعرف مساراتك (`book_path`)، وأعمدة النماذج، والمتغيرات `@books` التي عرّفها إجراء المتحكم. و**F12** على `render "form"` يفتح الملف `_form.html.erb`.

## تمارين

### التمرين 1

اكتب قالب ERB يطبع جدول ضرب العدد `n` من 1 إلى 3 بالشكل `n × i = ناتج`، كل سطر في `<p>`.

```ruby exercise
require "erb"
n = 4
template = ERB.new(<<~'HTML', trim_mode: "-")
  <%# اكتب الحلقة هنا %>
HTML
puts template.result(binding)
```

```ruby solution
require "erb"
n = 4
template = ERB.new(<<~'HTML', trim_mode: "-")
  <% (1..3).each do |i| -%>
  <p><%= n %> × <%= i %> = <%= n * i %></p>
  <% end -%>
HTML
puts template.result(binding)
```

```text output
<p>4 × 1 = 4</p>
<p>4 × 2 = 8</p>
<p>4 × 3 = 12</p>
```

### التمرين 2

لديك مصفوفة مستخدمين. اطبع اسم كل مستخدم في `<li>`، وأضف بعده ` (مدير)` إذا كان `admin` صحيحًا. وتأكد من تهريب الأسماء بـ `h()`.

```ruby exercise
require "erb"
include ERB::Util
users = [{ name: "منى", admin: true }, { name: "<b>علي</b>", admin: false }]
```

```ruby solution
require "erb"
include ERB::Util
users = [{ name: "منى", admin: true }, { name: "<b>علي</b>", admin: false }]
template = ERB.new(<<~'HTML', trim_mode: "-")
  <% users.each do |u| -%>
  <li><%= h(u[:name]) %><%= " (مدير)" if u[:admin] %></li>
  <% end -%>
HTML
puts template.result(binding)
```

```text output
<li>منى (مدير)</li>
<li>&lt;b&gt;علي&lt;/b&gt;</li>
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين <%= %> و<% %>؟", "choices": ["لا فرق", "<%= %> تطبع النتيجة في الصفحة و<% %> تنفذ فقط", "<% %> تطبع و<%= %> تنفذ فقط", "<%= %> للتعليقات"], "answer": 1, "explanation": "علامة = تعني اطبع النتيجة، وبدونها يُنفذ الكود فقط (مناسب للحلقات والشروط)."}
```

```quiz
{"question": "لماذا تهرّب Rails النصوص في <%= %> تلقائيًا؟", "choices": ["لتسريع الصفحة", "لحماية الموقع من هجوم XSS", "لتغيير اللغة", "لضغط الصفحة"], "answer": 1, "explanation": "التهريب يحوّل < و> إلى رموز آمنة فلا يُنفذ كود JavaScript كتبه مستخدم خبيث."}
```

```quiz
{"question": "بماذا يبدأ اسم ملف الجزء (partial)؟", "choices": ["#", "_", "@", "p_"], "answer": 1, "explanation": "اسم الجزء يبدأ بشرطة سفلية مثل _form.html.erb، ويُستدعى بدونها: render \"form\"."}
```

## الخلاصة

- ERB = HTML + Ruby: `<%= %>` تطبع، و`<% %>` تنفذ، و`<%# %>` تعليق.
- جربنا ERB بمكتبة Ruby نفسها: `ERB.new(text).result(binding)`.
- Rails تهرّب `<%= %>` تلقائيًا لحمايتك من XSS.
- الدوال المساعدة مثل `link_to` و`form_with`، والتخطيط بـ `yield`، والأجزاء بـ `render`.
