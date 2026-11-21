# الدرس 13: أول نافذة رسومية بـ Java في مصمم النماذج

حتى الآن كانت برامجنا في الكونسول: نص يُطبع ونص يُقرأ. اليوم نبني برنامجًا **بنافذة وأزرار ومربعات نص** بطريقة Visual Basic الشهيرة: ترسم النافذة بالسحب والإفلات في مصمم النماذج، ثم تكتب كود Java الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث (Event-Driven Programming)

في الكونسول البرنامج هو الذي يقود: يسأل ثم ينتظر ثم يكمل بالترتيب. أما في البرامج الرسومية فـ **المستخدم** هو الذي يقود: قد يضغط أي زر في أي وقت. لذلك نكتب الكود على شكل **معالجات أحداث** (event handlers): دالة لكل حدث تقول «عندما يحدث كذا، افعل كذا».

> **تشبيه:** برنامج الكونسول مثل **موظف يملأ معك استمارة** بأسئلة مرتبة. البرنامج الرسومي مثل **النادل في المطعم**: لا يفعل شيئًا حتى تناديه، فإذا طلبت «عصير» أحضره، وإذا طلبت «الحساب» أحضر الحساب.

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

مشاريع Java الرسومية في RAD IDE تعمل بفكرة بسيطة اسمها **GUI Bridge**:

1. **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج.
2. **برنامجك** (يترجمه `javac` ويشغله `java`) يعمل في الخلفية وينتظر الأحداث.
3. عندما يضغط المستخدم زرًا اسمه `btnHello`، ترسل الـ IDE الحدث، فتُستدعى دالتك `btnHello_Click`.
4. داخل الدالة تقرأ الأدوات وتغيرها بكود Java عادي: `lblResult.setText("مرحبا");`.

> **ملحوظة:** لا تحتاج إلى تعلم Swing أو JavaFX لتبدأ. الجسر يعطيك أسلوب Visual Basic البسيط، وكودك يبقى Java عاديًا تمامًا.

## مشروعك الأول خطوة بخطوة

### 1) إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد...) أو `Ctrl+Shift+N`.
2. من قائمة اللغات اختر **Java (GUI Bridge, JDK)**، ومن القوالب **Windows Application**.
3. سمِّ المشروع `HelloForm` واضغط **OK**.

تفتح الـ IDE النموذج **Form1** في **المصمم** (Designer)، ومعه ثلاثة ملفات في **Solution Explorer** (مستكشف الحلول):

| الملف | ما فيه | هل أعدّله؟ |
|---|---|---|
| `Form1.form` | تصميم النافذة (الأدوات ومواضعها وخصائصها) | من المصمم فقط |
| `Form1.java` | **كودك**: معالجات الأحداث | نعم |
| `Form1_designer.java` | الصنف `Form1Designer` وفيه حقل لكل أداة، تولّده الـ IDE تلقائيًا | لا، يُعاد توليده عند الحفظ |

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب إلى النموذج الأدوات التالية، ثم غيّر خاصية **Name** لكل أداة من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblResult` | (فارغ) |

> **نصيحة:** اعتد على البادئات في الأسماء: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار، و`tmr` للمؤقت. ستعرف نوع الأداة من اسمها فورًا في الكود.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE دالة الحدث `btnHello_Click` في `Form1.java` وتنقلك إليها. اكتب الكود التالي (أو اضغط «جرّبه» فوقه لترى المشروع جاهزًا):

<!-- test: {"set": {"txtName.Text": "ريم"}, "events": ["btnHello Click"], "expect": {"lblResult.Text": "أهلًا يا ريم!"}} -->
```java form run
public class Form1 extends Form1Designer {
    static void Form1_Load(RadEvent e) {          // تعمل مرة واحدة عند ظهور النافذة
        lblResult.setText("اكتب اسمك ثم اضغط الزر");
    }

    static void btnHello_Click(RadEvent e) {      // تعمل عند الضغط على الزر
        String name = txtName.getText().trim();
        if (name.isEmpty()) {
            lblResult.setText("من فضلك اكتب اسمك أولًا");
        } else {
            lblResult.setText("أهلًا يا " + name + "!");
        }
    }
}
```

### 4) التشغيل

اضغط **F5**. تترجم الـ IDE المشروع بـ `javac` (أول مرة تأخذ بضع ثوانٍ)، ثم تظهر نافذتك. اكتب اسمك (مثلًا «ريم») واضغط الزر، فيظهر: **أهلًا يا ريم!**

لاحظ:

- اسم الدالة يجب أن يكون بالضبط **`اسمالأداة_اسمالحدث`** مثل `btnHello_Click`، وأن تكون `static void`. هكذا تربطها الـ IDE بالحدث.
- المعامل `RadEvent e` اختياري، وفيه معلومات عن الحدث (مثل `e.x` و`e.y` لموضع الفأرة، و`e.keyCode` للمفتاح).
- `Form1_Load` حدث خاص بالنموذج يعمل عند ظهوره، ومكانه المناسب لضبط القيم الابتدائية.
- لا توجد `main` في كودك! الـ IDE تضيف برنامج البداية `RadMain.java` وحلقة الأحداث تلقائيًا في المجلد `_build/java`.
- `public class Form1 extends Form1Designer`: صنفك **يرث** (كما تعلمنا في الدرس 11) من الصنف المولّد `Form1Designer` الذي فيه حقول الأدوات، ولذلك تكتب `txtName` مباشرة.

## الأدوات في الكود

كل أداة في النموذج أصبحت **حقلًا** من النوع `RadControl` بنفس اسمها. وبما أن Java لا تملك «خصائص» مثل C#، نستخدم دوال **getter** و**setter** كما تعلمنا في درس الأصناف:

| الكود | معناه |
|---|---|
| `txtName.getText()` | النص المكتوب في مربع النص |
| `lblResult.setText("...")` | تغيير نص العنوان (يقبل أي قيمة: نصًا أو رقمًا) |
| `txtAge.getNumber()` | نص الأداة محوّلًا إلى رقم `double` (صفر إذا لم يكن رقمًا) |
| `btnSave.setEnabled(false)` | تعطيل الزر |
| `lblTitle.setVisible(false)` | إخفاء الأداة |
| `lblResult.setForeColor(255)` | لون الخط (أحمر، انظر الألوان بالأسفل) |
| `txtName.setFocus()` | نقل المؤشر إلى الأداة |
| `lblX.set("Caption", "...")` / `lblX.get("Width")` | أي خاصية أخرى باسمها |

ومن أي مكان في كود النموذج يمكنك استخدام الدوال المساعدة الموروثة:

| الدالة | وظيفتها |
|---|---|
| `msgbox("...")` | رسالة منبثقة |
| `input("سؤال")` | مربع إدخال يرجع النص |
| `toNumber(text)` / `toInt(text)` | تحويل نص إلى رقم (صفر إذا لم يكن رقمًا) |
| `toBool(text)` | تحويل `"True"` أو `"1"` إلى `true` |
| `end()` | إنهاء البرنامج |

وأي شيء تطبعه بـ `System.out.println` يظهر في نافذة **Output**، وهذا مفيد جدًا لتتبع ما يحدث.

## مثال ثانٍ: آلة حاسبة

ارسم النموذج التالي:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtA` | `0` |
| `TextBox` | `txtB` | `0` |
| `Button` | `btnAdd` | `+` |
| `Button` | `btnSub` | `-` |
| `Button` | `btnMul` | `×` |
| `Button` | `btnDiv` | `÷` |
| `Label` | `lblResult` | (فارغ) |

ثم اكتب الكود. لاحظ الدالة المساعدة العادية `calculate` التي تمنع تكرار الكود في الأزرار الأربعة، تمامًا كما تعلمنا في درس الدوال:

<!-- test: {"set": {"txtA.Text": "7", "txtB.Text": "2"}, "events": ["btnDiv Click"], "expect": {"lblResult.Text": "الناتج = 3.5"}} -->
```java form run
public class Form1 extends Form1Designer {
    // دالة مساعدة عادية (ليست حدثًا): تقرأ الرقمين وتحسب وتعرض الناتج
    static void calculate(char op) {
        double a = toNumber(txtA.getText());
        double b = toNumber(txtB.getText());
        if (op == '/' && b == 0) {
            lblResult.setText("لا يمكن القسمة على صفر");
            return;
        }
        double result = switch (op) {
            case '+' -> a + b;
            case '-' -> a - b;
            case '*' -> a * b;
            default -> a / b;
        };
        lblResult.setText("الناتج = " + result);
        System.out.println(a + " " + op + " " + b + " = " + result);   // يظهر في Output
    }

    static void btnAdd_Click(RadEvent e) { calculate('+'); }
    static void btnSub_Click(RadEvent e) { calculate('-'); }
    static void btnMul_Click(RadEvent e) { calculate('*'); }
    static void btnDiv_Click(RadEvent e) { calculate('/'); }
}
```

```text output
7.0 / 2.0 = 3.5
```

جرّب: اكتب `7` و`2` واضغط `÷`، فيظهر **الناتج = 3.5**، ويظهر في نافذة Output السطر `7.0 / 2.0 = 3.5`. (تذكّر من درس المتغيرات أن Java تطبع `double` دائمًا بنقطة عشرية، فـ `7 + 2` تظهر `9.0`.)

## المتغيرات بين الأحداث

برنامجك يظل يعمل طوال ظهور النافذة، لذلك **الحقول الثابتة** (`static`) في الصنف تحتفظ بقيمتها بين ضغطة وأخرى:

<!-- test: {"set": {"txtPassword.Text": "1234"}, "events": ["btnLogin Click", "btnLogin Click", "btnLogin Click"], "expect": {"lblStatus.Text": "تم إيقاف المحاولات", "btnLogin.Enabled": "False"}} -->
```java form run
public class Form1 extends Form1Designer {
    static int attempts = 0;     // يحتفظ بقيمته بين الأحداث

    static void btnLogin_Click(RadEvent e) {
        if (txtPassword.getText().equals("java2026")) {
            lblStatus.setText("تم الدخول بنجاح");
            lblStatus.setForeColor(32768);    // أخضر داكن
            return;
        }
        attempts++;
        lblStatus.setText("كلمة مرور خاطئة (" + attempts + " من 3)");
        lblStatus.setForeColor(255);          // أحمر
        if (attempts >= 3) {
            btnLogin.setEnabled(false);
            lblStatus.setText("تم إيقاف المحاولات");
        }
    }
}
```

الألوان تُكتب بصيغة Visual Basic: رقم يساوي `R + G × 256 + B × 65536`، فالأحمر `255`، والأخضر الداكن `32768`، والأزرق `16711680`، والأسود `0`، والأبيض `16777215`.

هنا رسمنا `TextBox` باسم `txtPassword` (اجعل خاصيته `PasswordChar` تساوي `*` لكي تُخفى الحروف)، و`Button` باسم `btnLogin`، و`Label` باسم `lblStatus`.

> **مهم:** المتغيرات المحلية داخل الدالة تُنشأ من جديد مع كل حدث. أما الحقل `static int attempts` فيبقى طوال عمر البرنامج.

## أخطاء شائعة

### اسم الدالة لا يطابق اسم الأداة

إذا سمّيت الزر `btnHello` وكتبت الدالة `btnhello_Click` أو `Button1_Click`، **لن يحدث شيء** عند الضغط ولن يظهر خطأ (Java تفرق بين الحروف الكبيرة والصغيرة). الحل الأسهل: انقر مرتين على الأداة في المصمم ودع الـ IDE تكتب اسم الدالة بنفسها.

### مقارنة النصوص بـ `==`

`if (txtPassword.getText() == "java2026")` لن تنجح أبدًا، لأن `==` تقارن **الكائنات** لا المحتوى (تذكّر درس النصوص). استخدم `.equals(...)`.

### تعديل `Form1_designer.java` بيدك

هذا الملف يُعاد توليده كلما حفظت النموذج، فتضيع تعديلاتك. اكتب كودك في `Form1.java` فقط.

### أداة في الكود غير موجودة في النموذج

إذا كتبت `lblTotal.setText("...")` ولا توجد أداة اسمها `lblTotal` يظهر خطأ الترجمة `cannot find symbol ... variable lblTotal`. أضف الأداة في المصمم أو صحح الاسم.

## تمارين

### التمرين 1

برنامج «محوّل درجات الحرارة»: مربع نص `txtC` للدرجة المئوية، وزر `btnConvert`، وعنوان `lblF`. عند الضغط اكتب في العنوان الدرجة بالفهرنهايت (`C × 9 ÷ 5 + 32`) بالشكل `98.6 °F`.

<!-- test: {"set": {"txtC.Text": "37"}, "events": ["btnConvert Click"], "expect": {"lblF.Text": "98.6 °F"}} -->
```java form exercise
public class Form1 extends Form1Designer {
    static void btnConvert_Click(RadEvent e) {
        // اقرأ txtC واحسب ثم اكتب في lblF
    }
}
```

<!-- test: {"set": {"txtC.Text": "37"}, "events": ["btnConvert Click"], "expect": {"lblF.Text": "98.6 °F"}} -->
```java form solution
public class Form1 extends Form1Designer {
    static void btnConvert_Click(RadEvent e) {
        double c = toNumber(txtC.getText());
        double f = c * 9 / 5 + 32;
        lblF.setText(f + " °F");
    }
}
```

### التمرين 2

عدّاد ضغطات: زر `btnClick` وزر `btnReset` وعنوان `lblCount`. كل ضغطة على `btnClick` تزيد العدد واحدًا وتعرضه، و`btnReset` يعيده إلى صفر.

<!-- test: {"events": ["btnClick Click", "btnClick Click", "btnClick Click"], "expect": {"lblCount.Text": "3"}} -->
```java form exercise
public class Form1 extends Form1Designer {
    static void btnClick_Click(RadEvent e) {
    }

    static void btnReset_Click(RadEvent e) {
    }
}
```

<!-- test: {"events": ["btnClick Click", "btnClick Click", "btnClick Click"], "expect": {"lblCount.Text": "3"}} -->
```java form solution
public class Form1 extends Form1Designer {
    static int count = 0;

    static void btnClick_Click(RadEvent e) {
        count++;
        lblCount.setText(count);
    }

    static void btnReset_Click(RadEvent e) {
        count = 0;
        lblCount.setText(0);
    }
}
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["save_Click", "btnSave_Click", "Click_btnSave", "onSave"], "answer": 1, "explanation": "الاسم دائمًا اسمالأداة_اسمالحدث، والنقر المزدوج في المصمم يكتبه لك."}
```

```quiz
{"question": "كيف تغيّر نص العنوان lblResult في Java؟", "choices": ["lblResult.Text = \"x\";", "lblResult.setText(\"x\");", "lblResult = \"x\";", "setText(lblResult)"], "answer": 1, "explanation": "Java تستخدم دوال setter وgetter: setText للكتابة وgetText للقراءة."}
```

```quiz
{"question": "لماذا نكتب class Form1 extends Form1Designer؟", "choices": ["لأن Java تشترط ذلك في كل صنف", "ليرث صنفنا حقول الأدوات والدوال المساعدة من الصنف المولّد", "لتسريع البرنامج", "لا فائدة منها"], "answer": 1, "explanation": "Form1Designer تولّده الـ IDE وفيه حقل لكل أداة، ويرث من Rad الدوال msgbox وtoNumber وغيرها."}
```

## الخلاصة

- مشروع **Java (GUI Bridge, JDK)**: الـ IDE ترسم النافذة، وبرنامجك يعالج الأحداث.
- معالج الحدث `static void اسمالأداة_الحدث(RadEvent e)` في `Form1.java`، و`Form1_Load` عند الظهور.
- الأدوات حقول: `txtName.getText()` و`lblResult.setText(...)` و`btnX.setEnabled(false)`.
- `msgbox` و`input` و`toNumber` دوال مساعدة، و`System.out.println` يكتب في Output.
