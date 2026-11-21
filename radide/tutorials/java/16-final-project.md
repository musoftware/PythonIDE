# الدرس 16: المشروع النهائي: دفتر الدرجات

حان وقت جمع كل ما تعلمته في برنامج حقيقي مفيد: **دفتر درجات** بنافذة رسومية، يضيف فيه المعلم الطلاب ودرجاتهم، ويحذف ويعدّل، ويرى المتوسط وأعلى درجة وعدد الناجحين، وتُحفظ البيانات في ملف لتجدها عند فتح البرنامج مرة أخرى.

سنستخدم: الأصناف و`record` (درس 10)، و`ArrayList` (درس 8)، والنصوص (درس 9)، والملفات والاستثناءات (درس 12)، والنماذج والأحداث (الدرسان 13 و14)، وتقسيم البرنامج على ملفين (درس 15).

## 1) التخطيط قبل الكود

قبل أن تكتب سطرًا واحدًا، اسأل: ما **البيانات**؟ وما **الأفعال**؟

- **البيانات:** طالب له اسم (`name`) ودرجة من 100 (`grade`).
- **الأفعال:** إضافة طالب، وحذفه، وحساب الإحصائيات (المتوسط، والأعلى، وعدد الناجحين)، وحفظ الكل في ملف، والتحميل عند البدء.

> **نصيحة:** افصل **البيانات والمنطق** عن **الواجهة**. الصنف `Student` لا يعرف شيئًا عن الأزرار، والنموذج لا يعرف كيف يُحفظ الطلاب في الملف. هكذا يسهل تعديل كل جزء وحده.

## 2) إنشاء المشروع ورسم النافذة

1. **File > New Project...** (ملف > مشروع جديد...)، ثم **Java (GUI Bridge, JDK)** و**Windows Application**، واسم المشروع `GradeBook`.
2. اجعل خاصية **Text** للنموذج `دفتر الدرجات`.
3. ارسم الأدوات التالية:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `TextBox` | `txtGrade` | (فارغ) |
| `Button` | `btnAdd` | `إضافة` |
| `ListBox` | `lstStudents` | |
| `Button` | `btnDelete` | `حذف` |
| `Label` | `lblStats` | (فارغ) |

4. أضف ملف كود جديدًا للصنف: **Project > Add Module...** (مشروع > إضافة وحدة برمجية...) باسم `Student`، فيصبح عندك `Student.java`.

## 3) صنف البيانات والتخزين: `Student.java`

```java
// Student.java - طالب واحد + الحفظ والتحميل من ملف CSV
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public record Student(String name, int grade) {
    public boolean passed() {
        return grade >= 50;
    }

    @Override
    public String toString() {                 // ما يظهر في ListBox
        return name + " - " + grade + (passed() ? "" : " (راسب)");
    }

    public String toLine() {                   // سطر في الملف: سلمى,95
        return name + "," + grade;
    }

    public static Student fromLine(String line) {
        int comma = line.lastIndexOf(',');
        return new Student(line.substring(0, comma), Integer.parseInt(line.substring(comma + 1).trim()));
    }

    public static List<Student> load(Path file) {
        List<Student> list = new ArrayList<>();
        try {
            for (String line : Files.readAllLines(file)) {
                if (!line.isBlank()) {
                    list.add(fromLine(line));
                }
            }
        } catch (IOException e) {
            // أول تشغيل: لا يوجد ملف بعد
        }
        return list;
    }

    public static void save(Path file, List<Student> students) {
        List<String> lines = new ArrayList<>();
        for (Student s : students) {
            lines.add(s.toLine());
        }
        try {
            Files.write(file, lines);
        } catch (IOException e) {
            System.out.println("تعذّر الحفظ: " + e.getMessage());
        }
    }
}
```

لاحظ `lastIndexOf(',')`: نبحث عن **آخر** فاصلة، فإذا احتوى الاسم على فاصلة (مثل «علي, الابن») لا يتلف السطر.

## 4) كود النموذج: `Form1.java`

اضغط **جرّبه** لترى المشروع كاملًا بالملفين (السطر `// #file: Student.java` يفصل بينهما في الدرس):

<!-- test: {"events": [{"txtName.Text": "Salma", "txtGrade.Text": "95"}, "btnAdd Click", {"txtName.Text": "Karim", "txtGrade.Text": "40"}, "btnAdd Click", {"txtName.Text": "Nour", "txtGrade.Text": "75"}, "btnAdd Click", {"txtName.Text": "Bad", "txtGrade.Text": "120"}, "btnAdd Click", {"lstStudents.ListIndex": "1"}, "btnDelete Click"], "msgbox": ["الدرجة يجب أن تكون رقمًا من 0 إلى 100"], "expect": {"lstStudents.ListCount": "2", "lstStudents.Items": "Salma - 95|Nour - 75", "lblStats.Text": "الطلاب: 2 | المتوسط: 85.0 | الأعلى: Salma (95) | الناجحون: 2"}} -->
```java form run
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class Form1 extends Form1Designer {
    static final Path FILE = Path.of("grades.csv");
    static List<Student> students = new ArrayList<>();

    static void Form1_Load(RadEvent e) throws Exception {
        Files.deleteIfExists(FILE);          // نبدأ هذا المثال بدفتر فارغ
        students = Student.load(FILE);
        refreshList();
    }

    // يعيد ملء القائمة من البيانات ويحدّث الإحصائيات ثم يحفظ
    static void refreshList() {
        lstStudents.clear();
        for (Student s : students) {
            lstStudents.addItem(s);
        }
        lblStats.setText(stats());
        Student.save(FILE, students);
    }

    static String stats() {
        if (students.isEmpty()) {
            return "لا يوجد طلاب بعد";
        }
        int sum = 0, passed = 0;
        Student best = students.get(0);
        for (Student s : students) {
            sum += s.grade();
            if (s.passed()) {
                passed++;
            }
            if (s.grade() > best.grade()) {
                best = s;
            }
        }
        double avg = Math.round(sum * 10.0 / students.size()) / 10.0;
        return "الطلاب: " + students.size() + " | المتوسط: " + avg + " | الأعلى: " + best.name()
                + " (" + best.grade() + ") | الناجحون: " + passed;
    }

    static void btnAdd_Click(RadEvent e) {
        String name = txtName.getText().trim();
        if (name.isEmpty()) {
            msgbox("اكتب اسم الطالب أولًا");
            return;
        }
        int grade;
        try {
            grade = Integer.parseInt(txtGrade.getText().trim());
        } catch (NumberFormatException ex) {
            grade = -1;
        }
        if (grade < 0 || grade > 100) {
            msgbox("الدرجة يجب أن تكون رقمًا من 0 إلى 100");
            return;
        }
        students.add(new Student(name, grade));
        txtName.setText("");
        txtGrade.setText("");
        txtName.setFocus();
        refreshList();
    }

    static void btnDelete_Click(RadEvent e) {
        int i = lstStudents.getListIndex();
        if (i < 0 || i >= students.size()) {
            msgbox("اختر طالبًا من القائمة أولًا");
            return;
        }
        Student removed = students.remove(i);
        System.out.println("حُذف " + removed.name());
        refreshList();
    }
}
// #file: Student.java
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public record Student(String name, int grade) {
    public boolean passed() {
        return grade >= 50;
    }

    @Override
    public String toString() {
        return name + " - " + grade + (passed() ? "" : " (راسب)");
    }

    public String toLine() {
        return name + "," + grade;
    }

    public static Student fromLine(String line) {
        int comma = line.lastIndexOf(',');
        return new Student(line.substring(0, comma), Integer.parseInt(line.substring(comma + 1).trim()));
    }

    public static List<Student> load(Path file) {
        List<Student> list = new ArrayList<>();
        try {
            for (String line : Files.readAllLines(file)) {
                if (!line.isBlank()) {
                    list.add(fromLine(line));
                }
            }
        } catch (IOException e) {
        }
        return list;
    }

    public static void save(Path file, List<Student> students) {
        List<String> lines = new ArrayList<>();
        for (Student s : students) {
            lines.add(s.toLine());
        }
        try {
            Files.write(file, lines);
        } catch (IOException e) {
            System.out.println("تعذّر الحفظ: " + e.getMessage());
        }
    }
}
```

```text output
حُذف Karim
```

في الاختبار: نضيف ثلاثة طلاب، ثم نحاول إضافة درجة `120` فتظهر رسالة الخطأ، ثم نحذف «Karim» (الطالب رقم 1)، فيبقى طالبان متوسطهما `85.0`.

> **ملحوظة:** في المثال يحذف `Form1_Load` الملف عند البدء لكي يبدأ المثال دائمًا بدفتر فارغ. في برنامجك الحقيقي **احذف** السطر `Files.deleteIfExists(FILE);` لكي تبقى الدرجات محفوظة بين مرة وأخرى. ولاحظ `throws Exception` في توقيع `Form1_Load`: معالج الحدث دالة عادية، ويجوز أن يعلن الاستثناءات المفحوصة.

## 5) كيف يعمل البرنامج؟

1. **عند البدء** (`Form1_Load`): يُحمّل الطلاب من `grades.csv` إلى القائمة `students`.
2. **مصدر الحقيقة** هو `List<Student> students` وليس `ListBox`. الـ `ListBox` مجرد **عرض** لها، تعيد `refreshList()` بناءه بعد كل تغيير.
3. `lstStudents.addItem(s)` تقبل أي كائن وتعرض نتيجة `toString()` الخاصة به، ولذلك كتبنا `toString` في `Student`.
4. **رقم العنصر في `ListBox`** يطابق رقمه في `students` لأننا نملؤهما بنفس الترتيب، لذلك `students.remove(lstStudents.getListIndex())` تحذف الطالب المختار.
5. **الحفظ التلقائي:** كل تغيير يمر عبر `refreshList()` التي تحفظ الملف، فلا تضيع الدرجات إذا أُغلق البرنامج فجأة.

## 6) جرّب وصحّح

- ضع نقطة توقف (F9) في `btnDelete_Click` واضغط F5، ثم اختر طالبًا واضغط «حذف»، وراقب في **Locals** قيمة `i` وحجم `students` قبل السطر وبعده (F10).
- افتح الملف `grades.csv` من مجلد المشروع لترى كيف تُخزّن الدرجات. ويمكنك فتحه في Excel أيضًا!

## 7) أفكار للتطوير (تحدَّ نفسك)

1. **التقدير:** أضف للصنف دالة `letter()` ترجع «ممتاز» و«جيد جدًا»... حسب الدرجة، واعرضها في `toString()`.
2. **الترتيب:** زر يرتب الطلاب من الأعلى درجة: `students.sort(Comparator.comparingInt(Student::grade).reversed())`.
3. **البحث:** مربع نص `txtSearch` وحدث `txtSearch_TextChanged` يعرض فقط الطلاب الذين تحتوي أسماؤهم النص.
4. **التعديل:** عند اختيار طالب (`lstStudents_SelectedIndexChanged`) تظهر بياناته في المربعين، وزر `btnUpdate` يحفظ التعديل.
5. **JSON:** أضف مكتبة Gson من **Project > Manage Packages...** (درس 15) واحفظ الدفتر بصيغة JSON.

## تمرين: الناجحون والراسبون

أضف زرًا `btnReport` يكتب في `lblStats` عدد الناجحين والراسبين بالشكل `ناجح: 2 - راسب: 1`.

<!-- test: {"events": [{"txtName.Text": "A", "txtGrade.Text": "90"}, "btnAdd Click", {"txtName.Text": "B", "txtGrade.Text": "30"}, "btnAdd Click", {"txtName.Text": "C", "txtGrade.Text": "50"}, "btnAdd Click", "btnReport Click"], "expect": {"lblStats.Text": "ناجح: 2 - راسب: 1"}} -->
```java form exercise
import java.util.ArrayList;
import java.util.List;

public class Form1 extends Form1Designer {
    static List<Student> students = new ArrayList<>();

    static void btnAdd_Click(RadEvent e) {
        students.add(new Student(txtName.getText(), toInt(txtGrade.getText())));
        lstStudents.addItem(txtName.getText());
    }

    static void btnReport_Click(RadEvent e) {
        // اكتب هنا: ناجح: X - راسب: Y
    }
}
// #file: Student.java
public record Student(String name, int grade) {
    public boolean passed() {
        return grade >= 50;
    }
}
```

<!-- test: {"events": [{"txtName.Text": "A", "txtGrade.Text": "90"}, "btnAdd Click", {"txtName.Text": "B", "txtGrade.Text": "30"}, "btnAdd Click", {"txtName.Text": "C", "txtGrade.Text": "50"}, "btnAdd Click", "btnReport Click"], "expect": {"lblStats.Text": "ناجح: 2 - راسب: 1"}} -->
```java form solution
import java.util.ArrayList;
import java.util.List;

public class Form1 extends Form1Designer {
    static List<Student> students = new ArrayList<>();

    static void btnAdd_Click(RadEvent e) {
        students.add(new Student(txtName.getText(), toInt(txtGrade.getText())));
        lstStudents.addItem(txtName.getText());
    }

    static void btnReport_Click(RadEvent e) {
        int passed = 0;
        for (Student s : students) {
            if (s.passed()) {
                passed++;
            }
        }
        lblStats.setText("ناجح: " + passed + " - راسب: " + (students.size() - passed));
    }
}
// #file: Student.java
public record Student(String name, int grade) {
    public boolean passed() {
        return grade >= 50;
    }
}
```

## اختبر نفسك

```quiz
{"question": "لماذا نحتفظ بالطلاب في List<Student> ولا نعتمد على ListBox وحدها؟", "choices": ["لأن ListBox بطيئة", "لأن القائمة هي مصدر البيانات الحقيقي والـ ListBox مجرد عرض لها", "لأن ListBox لا تقبل النصوص", "لا يوجد سبب"], "answer": 1, "explanation": "فصل البيانات عن العرض يجعل الحفظ والإحصائيات والترتيب سهلًا."}
```

```quiz
{"question": "ماذا يظهر في ListBox عند lstStudents.addItem(s) حيث s كائن Student؟", "choices": ["اسم الصنف فقط", "نتيجة s.toString()", "خطأ ترجمة", "عنوان الكائن في الذاكرة دائمًا"], "answer": 1, "explanation": "addItem تقبل أي كائن وتعرض نصه من toString()، ولذلك أعدنا تعريفها."}
```

```quiz
{"question": "لماذا استخدمنا lastIndexOf(',') في fromLine؟", "choices": ["أسرع من split", "لكي لا يتلف السطر إذا احتوى الاسم على فاصلة", "لحذف الفاصلة", "لا فائدة"], "answer": 1, "explanation": "الدرجة دائمًا بعد آخر فاصلة، وكل ما قبلها هو الاسم."}
```

## مبروك!

أنهيت دورة Java. تعلمت المتغيرات والشروط والحلقات والدوال والمصفوفات والمجموعات والنصوص والأصناف والوراثة والواجهات والاستثناءات والملفات، وبنيت برامج رسومية كاملة، وتعرفت على Maven وGradle، واستخدمت المصحح.

**ماذا بعد؟**

- افتح مشروع Maven أو Gradle حقيقيًا من GitHub في RAD IDE وتصفّح كوده.
- تعمق في **Streams** و**Lambdas** (`students.stream().filter(...)`)، وفي اختبارات **JUnit**.
- جرّب دورة **C#**: ستجدها قريبة جدًا من Java، وستنتقل إليها بسرعة.
