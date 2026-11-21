# الدرس 10: مشروع: قائمة المهام بنافذة رسومية

حان وقت أن نجمع كل ما تعلمناه في مشروع واحد مفيد: **مدير مهام** (To-Do List) بنافذة رسومية، يضيف المهام ويحذفها ويحفظها في ملف، فتبقى موجودة عندما تفتح البرنامج مرة أخرى.

سنستخدم: المتغيرات، والشروط، والمصفوفات، والدوال، والأصناف، والملفات، والأحداث.

## 1) تصميم النافذة

أنشئ مشروعًا جديدًا: **File > New Project... > Ruby (GUI Bridge)** باسم `TodoRuby`، ثم ارسم:

| الأداة | Name | Text | ملاحظات |
|---|---|---|---|
| `TextBox` | `txtTask` | (فارغ) | تكتب فيه المهمة |
| `Button` | `btnAdd` | `أضف` | |
| `ListBox` | `lstTasks` | | اجعله كبيرًا |
| `Button` | `btnDone` | `تمّت` | يحذف المهمة المختارة |
| `Button` | `btnClear` | `امسح الكل` | |
| `Label` | `lblCount` | (فارغ) | عدد المهام |

> **نصيحة:** غيّر خاصية **Text** للنموذج نفسه إلى `مهامي` ليظهر العنوان في شريط النافذة.

## 2) فصل المنطق عن الواجهة

فكرة يستخدمها المحترفون: نضع **البيانات والمنطق** في صنف مستقل لا يعرف شيئًا عن النافذة، ونجعل دوال الأحداث قصيرة تتصل بهذا الصنف. ميزة ذلك أنك تستطيع اختبار المنطق في الكونسول قبل رسم أي نافذة.

نبدأ بالصنف وحده ونجربه:

```ruby run
class TodoList
  attr_reader :tasks

  def initialize(file = nil)
    @file = file
    @tasks = []
    @tasks = File.readlines(file, chomp: true).reject(&:empty?) if file && File.exist?(file)
  end

  def add(text)
    text = text.strip
    return false if text.empty? || @tasks.include?(text)
    @tasks << text
    save
    true
  end

  def remove_at(index)
    return nil unless index.between?(0, @tasks.size - 1)
    removed = @tasks.delete_at(index)
    save
    removed
  end

  def clear
    @tasks.clear
    save
  end

  def save
    File.write(@file, @tasks.join("\n")) if @file
  end
end

list = TodoList.new
puts list.add("مذاكرة Ruby")
puts list.add("شراء الخبز")
puts list.add("مذاكرة Ruby")      # مكررة: ترفض
puts list.add("   ")              # فارغة: ترفض
puts list.remove_at(0)
p list.tasks
p list.remove_at(5)
```

```text output
true
true
false
false
مذاكرة Ruby
["شراء الخبز"]
nil
```

- `between?(a, b)` تفحص أن الرقم بين `a` و`b`.
- `delete_at(i)` تحذف العنصر رقم `i` وتُرجعه.
- `reject(&:empty?)` تتخلص من الأسطر الفارغة عند القراءة.

## 3) ربط الصنف بالنافذة

الآن نضع الصنف في `Form1.rb` ومعه دوال الأحداث:

<!-- test: {"events": [{"set": {"txtTask.Text": "مذاكرة Ruby"}}, "btnAdd.Click", {"set": {"txtTask.Text": "شراء الخبز"}}, "btnAdd.Click", {"set": {"txtTask.Text": "شراء الخبز"}}, "btnAdd.Click", {"set": {"lstTasks.ListIndex": "0"}}, "btnDone.Click"], "expect": {"lstTasks.items": "شراء الخبز", "lblCount.Text": "عدد المهام: 1", "txtTask.Text": "شراء الخبز"}, "msgbox": ["المهمة فارغة أو موجودة من قبل", "أحسنت! أنجزت: مذاكرة Ruby"], "captions": {"btnAdd": "أضف", "btnDone": "تمّت", "btnClear": "امسح الكل"}} -->
```ruby form run
class TodoList
  attr_reader :tasks

  def initialize(file = nil)
    @file = file
    @tasks = []
    @tasks = File.readlines(file, chomp: true).reject(&:empty?) if file && File.exist?(file)
  end

  def add(text)
    text = text.strip
    return false if text.empty? || @tasks.include?(text)
    @tasks << text
    save
    true
  end

  def remove_at(index)
    return nil unless index.between?(0, @tasks.size - 1)
    removed = @tasks.delete_at(index)
    save
    removed
  end

  def clear
    @tasks.clear
    save
  end

  def save
    File.write(@file, @tasks.join("\n")) if @file
  end
end

$todo = TodoList.new("tasks.txt")

# يعيد ملء القائمة من البيانات ويحدّث العدد
def refresh
  ui.lstTasks.Clear
  $todo.tasks.each { |t| ui.lstTasks.AddItem(t) }
  ui.lblCount.Text = "عدد المهام: #{$todo.tasks.size}"
end

def Form1_Load(e)
  refresh
end

def btnAdd_Click(e)
  if $todo.add(ui.txtTask.Text)
    ui.txtTask.Text = ""
    refresh
  else
    msgbox "المهمة فارغة أو موجودة من قبل"
  end
end

def btnDone_Click(e)
  index = Rad.get_num("lstTasks", "ListIndex").to_i
  done = $todo.remove_at(index)
  if done
    msgbox "أحسنت! أنجزت: #{done}"
    refresh
  else
    msgbox "اختر مهمة من القائمة أولًا"
  end
end

def btnClear_Click(e)
  $todo.clear
  refresh
end
```

اضغط **F5** وجرّب: أضف مهام، واختر واحدة واضغط «تمّت»، ثم أغلق البرنامج وافتحه مرة أخرى: ستجد المهام كما تركتها، لأنها محفوظة في الملف `tasks.txt` داخل مجلد المشروع.

## 4) كيف يجري البرنامج؟

1. عند التشغيل يُنشأ `$todo` ويقرأ الملف إن وُجد.
2. `Form1_Load` تملأ القائمة بالمهام المحفوظة.
3. كل زر يغيّر البيانات في `$todo` ثم يستدعي `refresh` لتعكس النافذة البيانات.

هذا النمط «غيّر البيانات ثم أعد رسم الواجهة» بسيط ويمنع أخطاء كثيرة، لأن الحقيقة موجودة في مكان واحد فقط: المصفوفة `@tasks`.

## 5) تتبع الأخطاء

- إذا لم يحدث شيء عند الضغط على زر، فتأكد أن اسم الزر في **Properties** يطابق اسم الدالة.
- أضف `puts` داخل الأحداث مؤقتًا: `puts "index = #{index}"` وانظر نافذة **Output**.
- ضع **نقطة توقف** (breakpoint) بالضغط على **F9** على سطر داخل `btnDone_Click`، ثم شغّل بـ **F5**: سيتوقف البرنامج عند الضغط على الزر وترى قيم المتغيرات في نافذة **Locals** (المتغيرات المحلية).

## أفكار لتطوير المشروع

- زر **تعديل** يضع المهمة المختارة في `txtTask` ليعدّلها المستخدم.
- مربع اختيار `chkUrgent`: المهام العاجلة تبدأ بالعلامة `!` وتظهر في أول القائمة (استخدم `sort_by`).
- حفظ تاريخ الإضافة مع كل مهمة: `Time.now.strftime("%Y-%m-%d")`.

## تمرين

أضف زرًا `btnSort` يرتب المهام أبجديًا. أضف إلى الصنف دالة `sort!` ثم اكتب حدث الزر.

<!-- test: {"set": {"txtTask.Text": "ب"}, "events": ["btnAdd.Click", {"set": {"txtTask.Text": "أ"}}, "btnAdd.Click", {"set": {"txtTask.Text": "ج"}}, "btnAdd.Click", "btnSort.Click"], "expect": {"lstTasks.items": "أ|ب|ج"}} -->
```ruby form exercise
class TodoList
  attr_reader :tasks

  def initialize
    @tasks = []
  end

  def add(text)
    @tasks << text.strip unless text.strip.empty?
  end

  # def sort! ...
end

$todo = TodoList.new

def refresh
  ui.lstTasks.Clear
  $todo.tasks.each { |t| ui.lstTasks.AddItem(t) }
end

def btnAdd_Click(e)
  $todo.add(ui.txtTask.Text)
  refresh
end

def btnSort_Click(e)
end
```

<!-- test: {"set": {"txtTask.Text": "ب"}, "events": ["btnAdd.Click", {"set": {"txtTask.Text": "أ"}}, "btnAdd.Click", {"set": {"txtTask.Text": "ج"}}, "btnAdd.Click", "btnSort.Click"], "expect": {"lstTasks.items": "أ|ب|ج"}, "captions": {"btnAdd": "أضف", "btnSort": "رتّب"}} -->
```ruby form solution
class TodoList
  attr_reader :tasks

  def initialize
    @tasks = []
  end

  def add(text)
    @tasks << text.strip unless text.strip.empty?
  end

  def sort!
    @tasks.sort!
  end
end

$todo = TodoList.new

def refresh
  ui.lstTasks.Clear
  $todo.tasks.each { |t| ui.lstTasks.AddItem(t) }
end

def btnAdd_Click(e)
  $todo.add(ui.txtTask.Text)
  refresh
end

def btnSort_Click(e)
  $todo.sort!
  refresh
end
```

الدوال التي تنتهي بعلامة التعجب مثل `sort!` تعني في عُرف Ruby أنها **تعدّل الكائن نفسه**، بينما `sort` بدون علامة تُرجع نسخة جديدة مرتبة.

## اختبر نفسك

```quiz
{"question": "لماذا وضعنا منطق المهام في صنف TodoList مستقل؟", "choices": ["لأن Ruby تشترط ذلك", "لنفصل البيانات عن الواجهة فيسهل اختبارها وتعديلها", "لتسريع النافذة", "لا يوجد سبب"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يسمح باختبار الصنف في الكونسول وتغيير الواجهة دون المساس بالمنطق."}
```

```quiz
{"question": "ما قيمة ListIndex إذا لم يختر المستخدم أي عنصر؟", "choices": ["0", "-1", "nil", "1"], "answer": 1, "explanation": "ListIndex تساوي -1 عندما لا يوجد عنصر مختار، ولذلك تفحص remove_at حدود الفهرس."}
```

## الخلاصة

- صممنا نافذة وربطناها بصنف يحمل البيانات والمنطق.
- نمط «غيّر البيانات ثم استدعِ `refresh`» يجعل الواجهة تعكس البيانات دائمًا.
- حفظنا المهام في ملف داخل مجلد المشروع لتبقى بعد إغلاق البرنامج.
- للتتبع: `puts` في Output، و F9 لنقطة توقف، و F5 للتشغيل مع المصحح.
