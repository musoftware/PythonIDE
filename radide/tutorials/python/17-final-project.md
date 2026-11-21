# الدرس 17: المشروع النهائي: مدير المهام

حان وقت جمع كل ما تعلمته في برنامج واحد حقيقي: **مدير مهام** بنافذة رسومية، يضيف المهام ويحدد أولويتها، ويعلّم المنجز منها، ويحذفها، و**يحفظها في ملف** فتبقى بعد إغلاق البرنامج.

سنستخدم:

- **الأصناف** (`dataclass`) لتمثيل المهمة وقائمة المهام (الدرس 11).
- **الوحدات**: ملف منفصل للمنطق `tasks.py` وملف للنافذة `Form1.py` (الدرس 12).
- **JSON والاستثناءات** للحفظ والتحميل (الدرس 10).
- **مصمم النماذج وTkinter** للواجهة (الدرسان 13 و14).

## الخطوة 1: التخطيط

قبل كتابة أي كود، فكّر: ما **البيانات**؟ وما **العمليات**؟

- **المهمة** (Task): عنوان، وأولوية، وهل أُنجزت.
- **قائمة المهام** (TaskList): إضافة، وتعليم كمنجزة، وحذف، وإحصائيات، وحفظ، وتحميل.
- **الواجهة**: تعرض القائمة وتستدعي العمليات عند الضغط على الأزرار.

> **مبدأ مهم:** افصل **المنطق** عن **الواجهة**. ملف `tasks.py` لا يعرف شيئًا عن Tkinter، فيمكنك اختباره في الكونسول، أو استخدامه لاحقًا مع واجهة PySide6 أو موقع ويب دون تغيير.

## الخطوة 2: المنطق في `tasks.py` واختباره في الكونسول

أنشئ مشروع **Windows Application** باسم `TaskManager` (Python (Tkinter))، ثم أضف وحدة جديدة من **Project ← Add Module...** باسم `tasks`. لنختبر المنطق أولًا ببرنامج كونسول صغير:

```python run
# #file: main.py
from tasks import TaskList

todo = TaskList()
todo.add("مذاكرة الدرس 17", "عالية")
todo.add("شراء خبز", "منخفضة")
todo.add("تمارين رياضية", "متوسطة")
todo.mark_done(1)
for line in todo.lines():
    print(line)
print(todo.stats())

todo.save("test_tasks.json")
again = TaskList.load("test_tasks.json")
print("بعد التحميل:", len(again.items), "مهام")
print(TaskList.load("no_such_file.json").stats())

# #file: tasks.py
"""منطق مدير المهام: لا يعرف شيئًا عن الواجهة."""
import json
from dataclasses import asdict, dataclass

PRIORITIES = ["عالية", "متوسطة", "منخفضة"]


@dataclass
class Task:
    title: str
    priority: str = "متوسطة"
    done: bool = False

    def __str__(self):
        mark = "✓" if self.done else " "
        return f"[{mark}] {self.title} ({self.priority})"


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title, priority="متوسطة"):
        title = title.strip()
        if not title:
            raise ValueError("عنوان المهمة فارغ")
        if priority not in PRIORITIES:
            priority = "متوسطة"
        task = Task(title, priority)
        self.items.append(task)
        return task

    def mark_done(self, index):
        self.items[index].done = True

    def remove(self, index):
        del self.items[index]

    def lines(self):
        # المهام غير المنجزة أولًا، ثم حسب الأولوية
        order = sorted(self.items, key=lambda t: (t.done, PRIORITIES.index(t.priority)))
        self.items = order
        return [str(t) for t in order]

    def stats(self):
        done = sum(1 for t in self.items if t.done)
        return f"المهام: {len(self.items)} - المنجز: {done} - المتبقي: {len(self.items) - done}"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self.items], f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path):
        tl = cls()
        try:
            with open(path, encoding="utf-8") as f:
                tl.items = [Task(**d) for d in json.load(f)]
        except (FileNotFoundError, ValueError, TypeError):
            pass                     # لا يوجد ملف بعد (أو تالف): ابدأ بقائمة فارغة
        return tl
```

```text output
[ ] مذاكرة الدرس 17 (عالية)
[ ] تمارين رياضية (متوسطة)
[✓] شراء خبز (منخفضة)
المهام: 3 - المنجز: 1 - المتبقي: 2
بعد التحميل: 3 مهام
المهام: 0 - المنجز: 0 - المتبقي: 0
```

لاحظ:

- `lines()` ترتّب المهام: غير المنجزة أولًا، ثم حسب الأولوية. ولأن الواجهة ستعرض العناصر بنفس الترتيب، نحفظ الترتيب الجديد في `self.items` لكي يطابق رقم العنصر في القائمة رقمه في الواجهة.
- `@classmethod` دالة تابعة للصنف نفسه وليس لكائن: `TaskList.load(...)` تنشئ قائمة جديدة من الملف.
- `load` لا تنهار إذا لم يوجد الملف، بل ترجع قائمة فارغة.

## الخطوة 3: تصميم النافذة

افتح **Form1** في المصمم، واجعل `Text` للنموذج `مدير المهام`، وارسم:

| الأداة | Name | Text / Items |
|---|---|---|
| `TextBox` | `txtTitle` | (فارغ) |
| `ComboBox` | `cboPriority` | Items: `عالية;متوسطة;منخفضة` |
| `Button` | `btnAdd` | `أضف` |
| `ListBox` | `lstTasks` | |
| `Button` | `btnDone` | `تم الإنجاز ✓` |
| `Button` | `btnDelete` | `احذف` |
| `Label` | `lblStats` | (فارغ) |

## الخطوة 4: كود النافذة

<!-- test: {"form": {"Text": "مدير المهام", "Width": 460, "Height": 380}, "controls": [["TextBox", "txtTitle", {"Text": "", "Left": 16, "Top": 16, "Width": 220}], ["ComboBox", "cboPriority", {"Items": "عالية;متوسطة;منخفضة", "Left": 246, "Top": 16, "Width": 100}], ["Button", "btnAdd", {"Text": "أضف", "Left": 356, "Top": 14, "Width": 80, "Height": 26}], ["ListBox", "lstTasks", {"Left": 16, "Top": 52, "Width": 330, "Height": 230}], ["Button", "btnDone", {"Text": "تم الإنجاز ✓", "Left": 356, "Top": 52, "Width": 80, "Height": 28}], ["Button", "btnDelete", {"Text": "احذف", "Left": 356, "Top": 88, "Width": 80, "Height": 28}], ["Label", "lblStats", {"Text": "", "Left": 16, "Top": 296, "Width": 420}]], "steps": [["set", "txtTitle", "شراء خبز"], ["select", "cboPriority", 2], ["click", "btnAdd"], ["set", "txtTitle", "مذاكرة الدرس 17"], ["select", "cboPriority", 0], ["click", "btnAdd"], ["set", "txtTitle", "تمارين رياضية"], ["select", "cboPriority", 1], ["click", "btnAdd"], ["select", "lstTasks", 0], ["click", "btnDone"], ["select", "lstTasks", 0], ["click", "btnDelete"]], "msgbox": ["احذف المهمة: تمارين رياضية؟"], "expect": {"lstTasks": "[ ] شراء خبز (منخفضة)|[✓] مذاكرة الدرس 17 (عالية)", "lblStats": "المهام: 2 - المنجز: 1 - المتبقي: 1", "txtTitle": ""}} -->
```python form run
# #file: Form1.py
from tkinter import messagebox

from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from tasks import PRIORITIES, TaskList

DATA_FILE = "tasks.json"


class Form1(Form1Designer):

    def Form1_Load(self):
        self.todo = TaskList.load(DATA_FILE)
        self.cboPriority["values"] = PRIORITIES
        self.cboPriority.current(1)
        self.refresh()

    # ------------------------------------------------ مساعدات
    def refresh(self):
        """أعد ملء القائمة من البيانات، واحفظ الملف."""
        self.lstTasks.delete(0, "end")
        for line in self.todo.lines():
            self.lstTasks.insert("end", line)
        self.lblStats.config(text=self.todo.stats())
        self.todo.save(DATA_FILE)

    def selected_index(self):
        sel = self.lstTasks.curselection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر مهمة من القائمة أولًا")
            return None
        return sel[0]

    # ------------------------------------------------ الأحداث
    def btnAdd_Click(self):
        try:
            self.todo.add(self.txtTitle.get(), self.cboPriority.get())
        except ValueError as e:
            messagebox.showwarning("تنبيه", str(e))
            return
        self.txtTitle_var.set("")
        self.refresh()

    def btnDone_Click(self):
        i = self.selected_index()
        if i is not None:
            self.todo.mark_done(i)
            self.refresh()

    def btnDelete_Click(self):
        i = self.selected_index()
        if i is None:
            return
        title = self.todo.items[i].title
        if messagebox.askyesno("تأكيد", f"احذف المهمة: {title}؟"):
            self.todo.remove(i)
            self.refresh()


if __name__ == "__main__":
    Form1().show()

# #file: tasks.py
"""منطق مدير المهام: لا يعرف شيئًا عن الواجهة."""
import json
from dataclasses import asdict, dataclass

PRIORITIES = ["عالية", "متوسطة", "منخفضة"]


@dataclass
class Task:
    title: str
    priority: str = "متوسطة"
    done: bool = False

    def __str__(self):
        mark = "✓" if self.done else " "
        return f"[{mark}] {self.title} ({self.priority})"


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title, priority="متوسطة"):
        title = title.strip()
        if not title:
            raise ValueError("عنوان المهمة فارغ")
        if priority not in PRIORITIES:
            priority = "متوسطة"
        task = Task(title, priority)
        self.items.append(task)
        return task

    def mark_done(self, index):
        self.items[index].done = True

    def remove(self, index):
        del self.items[index]

    def lines(self):
        order = sorted(self.items, key=lambda t: (t.done, PRIORITIES.index(t.priority)))
        self.items = order
        return [str(t) for t in order]

    def stats(self):
        done = sum(1 for t in self.items if t.done)
        return f"المهام: {len(self.items)} - المنجز: {done} - المتبقي: {len(self.items) - done}"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self.items], f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path):
        tl = cls()
        try:
            with open(path, encoding="utf-8") as f:
                tl.items = [Task(**d) for d in json.load(f)]
        except (FileNotFoundError, ValueError, TypeError):
            pass
        return tl
```

اضغط **F5** وجرّب: أضف ثلاث مهام بأولويات مختلفة، وعلّم واحدة كمنجزة، واحذف أخرى. ثم **أغلق البرنامج وافتحه من جديد**: ستجد مهامك كما تركتها، لأنها محفوظة في `tasks.json` داخل مجلد المشروع.

## الخطوة 5: التصحيح

إذا لم يعمل شيء كما تتوقع:

1. ضع نقطة توقف (**F9**) في `btnDone_Click`.
2. شغّل بـ **F5**، واختر مهمة واضغط الزر.
3. راقب `i` و`self.todo.items` في **Locals**، ونفّذ بـ **F10**.

## أفكار لتطوير المشروع

- **تعديل المهمة** بالنقر المزدوج عليها (`DoubleClick`)، وقراءة العنوان الجديد بـ `simpledialog.askstring`.
- **تاريخ استحقاق** لكل مهمة بأداة `DateTimePicker`، وتلوين المتأخر منها.
- **بحث** بـ `TextBox` وحدث `TextChanged` يعرض المهام المطابقة فقط.
- **نسخة PySide6**: أنشئ مشروع Python (PySide6 / Qt) واستخدم نفس `tasks.py` دون تغيير حرف واحد! هذه فائدة فصل المنطق عن الواجهة.
- **تحويله إلى برنامج exe** لتوزيعه على أصدقائك من **Build ← Publish** (تبني الـ IDE نسخة جاهزة بـ PyInstaller).

## تمارين

### التمرين 1

أضف إلى `TaskList` دالة `clear_done()` تحذف كل المهام المنجزة، واختبرها في الكونسول.

```python exercise
# #file: main.py
from tasks import TaskList

todo = TaskList()
todo.add("أ", "عالية")
todo.add("ب", "منخفضة")
todo.add("ج", "متوسطة")
todo.mark_done(0)
todo.mark_done(2)
todo.clear_done()
print(todo.stats())

# #file: tasks.py
from dataclasses import dataclass

PRIORITIES = ["عالية", "متوسطة", "منخفضة"]


@dataclass
class Task:
    title: str
    priority: str = "متوسطة"
    done: bool = False


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title, priority="متوسطة"):
        self.items.append(Task(title, priority))

    def mark_done(self, index):
        self.items[index].done = True

    def stats(self):
        done = sum(1 for t in self.items if t.done)
        return f"المهام: {len(self.items)} - المنجز: {done} - المتبقي: {len(self.items) - done}"
```

```python solution
# #file: main.py
from tasks import TaskList

todo = TaskList()
todo.add("أ", "عالية")
todo.add("ب", "منخفضة")
todo.add("ج", "متوسطة")
todo.mark_done(0)
todo.mark_done(2)
todo.clear_done()
print(todo.stats())

# #file: tasks.py
from dataclasses import dataclass

PRIORITIES = ["عالية", "متوسطة", "منخفضة"]


@dataclass
class Task:
    title: str
    priority: str = "متوسطة"
    done: bool = False


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title, priority="متوسطة"):
        self.items.append(Task(title, priority))

    def mark_done(self, index):
        self.items[index].done = True

    def clear_done(self):
        self.items = [t for t in self.items if not t.done]

    def stats(self):
        done = sum(1 for t in self.items if t.done)
        return f"المهام: {len(self.items)} - المنجز: {done} - المتبقي: {len(self.items) - done}"
```

```text output
المهام: 1 - المنجز: 0 - المتبقي: 1
```

### التمرين 2

أضف دالة `search(text)` ترجع عناوين المهام التي تحتوي على النص (بدون اعتبار لحالة الأحرف).

```python exercise
# #file: main.py
from tasks import TaskList

todo = TaskList()
for title in ["Buy milk", "Study Python", "buy bread", "Gym"]:
    todo.add(title)
print(todo.search("buy"))

# #file: tasks.py
from dataclasses import dataclass


@dataclass
class Task:
    title: str
    done: bool = False


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title):
        self.items.append(Task(title))

    def search(self, text):
        return []
```

```python solution
# #file: main.py
from tasks import TaskList

todo = TaskList()
for title in ["Buy milk", "Study Python", "buy bread", "Gym"]:
    todo.add(title)
print(todo.search("buy"))

# #file: tasks.py
from dataclasses import dataclass


@dataclass
class Task:
    title: str
    done: bool = False


class TaskList:
    def __init__(self):
        self.items = []

    def add(self, title):
        self.items.append(Task(title))

    def search(self, text):
        text = text.lower()
        return [t.title for t in self.items if text in t.title.lower()]
```

```text output
['Buy milk', 'buy bread']
```

## اختبر نفسك

```quiz
{"question": "لماذا وضعنا منطق المهام في tasks.py منفصلًا عن Form1.py؟", "choices": ["لأن Python لا تسمح بملف كبير", "لكي نختبره وحده ونعيد استخدامه مع واجهات أخرى", "لأن المصمم يتطلب ذلك", "لتسريع البرنامج"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يجعل الكود أسهل في الاختبار وإعادة الاستخدام."}
```

```quiz
{"question": "ماذا تفعل TaskList.load إذا لم يوجد ملف tasks.json؟", "choices": ["ينهار البرنامج", "ترجع قائمة فارغة", "تنشئ مهمة افتراضية", "تسأل المستخدم"], "answer": 1, "explanation": "تلتقط FileNotFoundError وترجع قائمة فارغة."}
```

## الخلاصة

مبروك! لقد أنهيت دورة Python. أصبحت تعرف المتغيرات والشروط والحلقات، والقوائم والقواميس، والدوال والأصناف، والأخطاء والملفات، والوحدات والبيئة الافتراضية، وتصميم النوافذ بـ Tkinter وPySide6، وتصحيح الأخطاء. الخطوة التالية: **ابنِ مشاريعك الخاصة**، فالبرمجة تُتعلم بالممارسة. وإن أحببت تحليل البيانات فابدأ دليل **Jupyter وعلم البيانات** في قائمة الدروس.
