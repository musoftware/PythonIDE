# الدرس 15: المشروع النهائي: قائمة المهام

نختم الدورة ببرنامج حقيقي تستخدمه كل يوم: **قائمة مهام** بنافذة، تضيف فيها المهام، وتعلّم المنجز منها، وتحفظها في ملف JSON لتجدها عند فتح البرنامج مرة أخرى.

سنستخدم: الهياكل والدوال المرتبطة، والشرائح، والأخطاء، والملفات، والحزمة `encoding/json`، والنوافذ.

## الخطوة 1: المنطق في الكونسول

نبدأ بنوع `TodoList` ونختبره في الكونسول قبل أي واجهة:

```go run
package main

import (
    "encoding/json"
    "errors"
    "fmt"
    "os"
    "strings"
)

type Task struct {
    Title string `json:"title"`
    Done  bool   `json:"done"`
}

type TodoList struct {
    Tasks []Task `json:"tasks"`
}

func (l *TodoList) Add(title string) error {
    title = strings.TrimSpace(title)
    if title == "" {
        return errors.New("عنوان المهمة فارغ")
    }
    l.Tasks = append(l.Tasks, Task{Title: title})
    return nil
}

func (l *TodoList) Toggle(i int) error {
    if i < 0 || i >= len(l.Tasks) {
        return fmt.Errorf("لا توجد مهمة رقم %d", i)
    }
    l.Tasks[i].Done = !l.Tasks[i].Done
    return nil
}

func (l *TodoList) Remove(i int) error {
    if i < 0 || i >= len(l.Tasks) {
        return fmt.Errorf("لا توجد مهمة رقم %d", i)
    }
    l.Tasks = append(l.Tasks[:i], l.Tasks[i+1:]...)
    return nil
}

func (l *TodoList) Remaining() int {
    n := 0
    for _, t := range l.Tasks {
        if !t.Done {
            n++
        }
    }
    return n
}

func (t Task) String() string {
    mark := "[ ]"
    if t.Done {
        mark = "[x]"
    }
    return mark + " " + t.Title
}

func (l *TodoList) Save(path string) error {
    data, err := json.MarshalIndent(l, "", "  ")
    if err != nil {
        return err
    }
    return os.WriteFile(path, data, 0644)
}

func Load(path string) (*TodoList, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return &TodoList{}, err
    }
    var l TodoList
    err = json.Unmarshal(data, &l)
    return &l, err
}

func main() {
    var list TodoList
    list.Add("اشترِ خبزًا")
    list.Add("ذاكر درس Go")
    list.Add("اتصل بجدتك")
    if err := list.Add("   "); err != nil {
        fmt.Println("خطأ:", err)
    }
    list.Toggle(1)
    for _, t := range list.Tasks {
        fmt.Println(t)
    }
    fmt.Println("المتبقي:", list.Remaining())

    if err := list.Save("todo.json"); err != nil {
        fmt.Println(err)
        return
    }
    loaded, err := Load("todo.json")
    if err != nil {
        fmt.Println(err)
        return
    }
    loaded.Remove(0)
    fmt.Println("بعد التحميل والحذف:", len(loaded.Tasks), "مهام")
    fmt.Println(loaded.Tasks[0])
}
```

```text output
خطأ: عنوان المهمة فارغ
[ ] اشترِ خبزًا
[x] ذاكر درس Go
[ ] اتصل بجدتك
المتبقي: 2
بعد التحميل والحذف: 2 مهام
[x] ذاكر درس Go
```

### ما الجديد هنا؟

- **وسوم الهيكل** `` `json:"title"` ``: تخبر الحزمة `encoding/json` باسم الحقل في الملف.
- `json.MarshalIndent` تحول الهيكل إلى نص JSON منسق، و`json.Unmarshal` تعيده هيكلًا.
- الحقول التي تُحفظ يجب أن تبدأ **بحرف كبير** (عامة)، وإلا تتجاهلها `json`.

هكذا يبدو الملف `todo.json` بعد الحفظ:

```text
{
  "tasks": [
    {
      "title": "اشترِ خبزًا",
      "done": false
    },
    ...
  ]
}
```

## الخطوة 2: تصميم النافذة

مشروع جديد: **File ← New Project ← Native ← Go (GUI Bridge)**، القالب **Windows Application**، والاسم `TodoApp`. ارسم:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtTask` | (فارغ) |
| `Button` | `btnAdd` | `إضافة` |
| `ListBox` | `lstTasks` | |
| `Button` | `btnToggle` | `تم / لم يتم` |
| `Button` | `btnRemove` | `حذف` |
| `Label` | `lblStatus` | (فارغ) |

## الخطوة 3: ربط المنطق بالنافذة

ضع النوع `TodoList` ودواله في ملف مستقل `todo.go` (**Project ← Add Module...**)، وضع الأحداث في `Form1.go`. كل الملفات في `package main` فيرى بعضها بعضًا:

```go form run
// #file: Form1.go
package main

import (
    "fmt"
    "log"
)

const dataFile = "todo.json"

var list *TodoList

func refresh() {
    Call("lstTasks", "Clear")
    for _, t := range list.Tasks {
        Call("lstTasks", "AddItem", t.String())
    }
    Set("lblStatus", "Text", fmt.Sprintf("المهام: %d | المتبقي: %d", len(list.Tasks), list.Remaining()))
    if err := list.Save(dataFile); err != nil {
        log.Println("تعذر الحفظ:", err)
    }
}

func selected() int {
    return int(GetNum("lstTasks", "ListIndex"))   // -1 إذا لم يُختر شيء
}

func Form1_Load(e RadEvent) {
    var err error
    list, err = Load(dataFile)
    if err != nil {
        log.Println("بدأنا بقائمة جديدة:", err)
    }
    refresh()
}

func btnAdd_Click(e RadEvent) {
    if err := list.Add(Get("txtTask", "Text")); err != nil {
        MsgBox(err.Error())
        return
    }
    Set("txtTask", "Text", "")
    refresh()
}

func btnToggle_Click(e RadEvent) {
    if err := list.Toggle(selected()); err != nil {
        MsgBox("اختر مهمة من القائمة أولًا")
        return
    }
    refresh()
}

func btnRemove_Click(e RadEvent) {
    if err := list.Remove(selected()); err != nil {
        MsgBox("اختر مهمة من القائمة أولًا")
        return
    }
    refresh()
}
// #file: todo.go
package main

import (
    "encoding/json"
    "errors"
    "fmt"
    "os"
    "strings"
)

type Task struct {
    Title string `json:"title"`
    Done  bool   `json:"done"`
}

type TodoList struct {
    Tasks []Task `json:"tasks"`
}

func (l *TodoList) Add(title string) error {
    title = strings.TrimSpace(title)
    if title == "" {
        return errors.New("عنوان المهمة فارغ")
    }
    l.Tasks = append(l.Tasks, Task{Title: title})
    return nil
}

func (l *TodoList) Toggle(i int) error {
    if i < 0 || i >= len(l.Tasks) {
        return fmt.Errorf("لا توجد مهمة رقم %d", i)
    }
    l.Tasks[i].Done = !l.Tasks[i].Done
    return nil
}

func (l *TodoList) Remove(i int) error {
    if i < 0 || i >= len(l.Tasks) {
        return fmt.Errorf("لا توجد مهمة رقم %d", i)
    }
    l.Tasks = append(l.Tasks[:i], l.Tasks[i+1:]...)
    return nil
}

func (l *TodoList) Remaining() int {
    n := 0
    for _, t := range l.Tasks {
        if !t.Done {
            n++
        }
    }
    return n
}

func (t Task) String() string {
    if t.Done {
        return "[x] " + t.Title
    }
    return "[ ] " + t.Title
}

func (l *TodoList) Save(path string) error {
    data, err := json.MarshalIndent(l, "", "  ")
    if err != nil {
        return err
    }
    return os.WriteFile(path, data, 0644)
}

func Load(path string) (*TodoList, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return &TodoList{}, err
    }
    var l TodoList
    err = json.Unmarshal(data, &l)
    return &l, err
}
```

اضغط **F5**. أضف مهام، واختر واحدة واضغط «تم / لم يتم»، ثم أغلق البرنامج وافتحه من جديد: ستجد مهامك كما تركتها، لأنها محفوظة في `todo.json` داخل مجلد المشروع.

## لماذا هذا التصميم جيد؟

- **فصل المنطق عن الواجهة:** `todo.go` لا يعرف شيئًا عن النوافذ، فيمكن اختباره وحده، أو استخدامه في برنامج كونسول أو خادم ويب.
- **الأخطاء قيم:** كل عملية ترجع `error`، والواجهة تقرر كيف تعرضه (رسالة `MsgBox`).
- **دالة `refresh` واحدة:** بعد أي تغيير نعيد رسم القائمة ونحفظ؛ لا تكرار للكود.

## أفكار للتطوير

- زر «حذف المنجز» يحذف كل المهام التي `Done` فيها `true` (حلقة تبني شريحة جديدة).
- حفظ تاريخ إنشاء كل مهمة باستخدام الحزمة `time`.
- مؤقت `Timer` يذكّرك بالمهام المتبقية كل ساعة (حدث `tmrRemind_Tick`).

## تمرين

### التمرين 1

أضف إلى `TodoList` دالة `ClearDone` تحذف كل المهام المنجزة، واختبرها:

```go exercise
package main

import "fmt"

type Task struct {
    Title string
    Done  bool
}

type TodoList struct {
    Tasks []Task
}

func (l *TodoList) ClearDone() {
    // ابنِ شريحة جديدة فيها المهام غير المنجزة فقط
}

func main() {
    l := TodoList{Tasks: []Task{{"أ", true}, {"ب", false}, {"ج", true}, {"د", false}}}
    l.ClearDone()
    for _, t := range l.Tasks {
        fmt.Println(t.Title)
    }
}
```

```go solution
package main

import "fmt"

type Task struct {
    Title string
    Done  bool
}

type TodoList struct {
    Tasks []Task
}

func (l *TodoList) ClearDone() {
    kept := []Task{}
    for _, t := range l.Tasks {
        if !t.Done {
            kept = append(kept, t)
        }
    }
    l.Tasks = kept
}

func main() {
    l := TodoList{Tasks: []Task{{"أ", true}, {"ب", false}, {"ج", true}, {"د", false}}}
    l.ClearDone()
    for _, t := range l.Tasks {
        fmt.Println(t.Title)
    }
}
```

```text output
ب
د
```

## اختبر نفسك

```quiz
{"question": "لماذا تبدأ حقول Task بحرف كبير (Title, Done)؟", "choices": ["للزينة", "لكي تستطيع encoding/json قراءتها وكتابتها", "لأن Go تمنع الحروف الصغيرة", "لتسريع البرنامج"], "answer": 1, "explanation": "json تتعامل مع الحقول العامة فقط، والحقل العام يبدأ بحرف كبير."}
```

```quiz
{"question": "ما فائدة وضع منطق المهام في todo.go منفصلًا عن الأحداث؟", "choices": ["لا فائدة", "يمكن اختباره وإعادة استخدامه بعيدًا عن الواجهة", "لأن الـ IDE تشترط ذلك", "لتقليل حجم الملف التنفيذي"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يجعل الكود أوضح وأسهل في الاختبار وإعادة الاستخدام."}
```

## الخلاصة وماذا بعد؟

مبروك! أنهيت دورة Go. تعلمت:

- أساسيات اللغة: المتغيرات والشروط والحلقات والدوال.
- أسلوب Go في الأخطاء، والشرائح والخرائط، والنصوص العربية بالـ runes.
- الهياكل والواجهات، و`defer` والملفات وJSON.
- التزامن بالـ goroutines والقنوات.
- الوحدات والحزم، وبرامج النوافذ بمصمم النماذج.

**الخطوة التالية:** جرّب كتابة خادم ويب صغير بالحزمة القياسية `net/http`، فهذا من أقوى مجالات Go. أو انتقل إلى **دورة Rust** لتتعرف على لغة حديثة أخرى تركز على الأمان والسرعة.
