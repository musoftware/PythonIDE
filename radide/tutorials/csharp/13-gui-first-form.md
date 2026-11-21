# الدرس 13: أول نافذة رسومية بـ C# في مصمم النماذج

حتى الآن كانت برامجنا في الكونسول: نص يُطبع ونص يُقرأ. اليوم نبني برنامجًا **بنافذة وأزرار ومربعات نص**، بطريقة Visual Basic الشهيرة: ترسم النافذة بالسحب والإفلات، ثم تكتب كود C# الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث (Event-Driven Programming)

في الكونسول البرنامج هو الذي يقود: يسأل ثم ينتظر ثم يكمل بالترتيب. أما في البرامج الرسومية فـ **المستخدم** هو الذي يقود: قد يضغط أي زر في أي وقت. لذلك نكتب الكود على شكل **معالجات أحداث** (event handlers): دالة لكل حدث تقول «عندما يحدث كذا، افعل كذا».

> **تشبيه:** برنامج الكونسول مثل **موظف يملأ معك استمارة** بأسئلة مرتبة. البرنامج الرسومي مثل **النادل في المطعم**: لا يفعل شيئًا حتى تناديه، فإذا طلبت «عصير» أحضره، وإذا طلبت «الحساب» أحضر الحساب.

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

مشاريع C# الرسومية في RAD IDE تعمل بفكرة بسيطة اسمها **GUI Bridge**:

1. **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج.
2. **برنامجك** (يبنيه `dotnet`) يعمل في الخلفية وينتظر الأحداث.
3. عندما يضغط المستخدم زرًا اسمه `btnHello`، ترسل الـ IDE الحدث، فتُستدعى دالتك `btnHello_Click`.
4. داخل الدالة تقرأ الأدوات وتغيرها بكود C# عادي: `lblResult.Text = "مرحبا";`.

## مشروعك الأول خطوة بخطوة

### 1) إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد...) أو `Ctrl+Shift+N`.
2. من قائمة اللغات اختر **C# (GUI Bridge, .NET)**، ومن القوالب **Windows Application** (تطبيق Windows).
3. سمِّ المشروع `HelloForm` واضغط **OK**.

تفتح الـ IDE النموذج **Form1** في **المصمم** (Designer)، ومعه ثلاثة ملفات في **Solution Explorer** (مستكشف الحلول):

| الملف | ما فيه | هل أعدّله؟ |
|---|---|---|
| `Form1.form` | تصميم النافذة (الأدوات ومواضعها وخصائصها) | من المصمم فقط |
| `Form1.cs` | **كودك**: معالجات الأحداث | نعم |
| `Form1_designer.cs` | حقل C# لكل أداة، تولّده الـ IDE تلقائيًا | لا، يُعاد توليده عند الحفظ |

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب إلى النموذج الأدوات التالية، ثم غيّر خاصية **Name** لكل أداة من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblResult` | (فارغ) |

> **نصيحة:** اعتد على البادئات في الأسماء: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار، و`tmr` للمؤقت. ستعرف نوع الأداة من اسمها فورًا في الكود.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE دالة الحدث `btnHello_Click` في `Form1.cs` وتنقلك إليها. اكتب الكود التالي (أو اضغط «جرّبه» فوقه لترى المشروع جاهزًا):

<!-- test: {"set": {"txtName.Text": "ريم"}, "events": ["btnHello Click"], "expect": {"lblResult.Text": "أهلًا يا ريم!"}} -->
```csharp form run
public static partial class Form1
{
    static void Form1_Load(RadEvent e)          // تعمل مرة واحدة عند ظهور النافذة
    {
        lblResult.Text = "اكتب اسمك ثم اضغط الزر";
    }

    static void btnHello_Click(RadEvent e)      // تعمل عند الضغط على الزر
    {
        string name = txtName.Text.Trim();
        if (name == "")
            lblResult.Text = "من فضلك اكتب اسمك أولًا";
        else
            lblResult.Text = $"أهلًا يا {name}!";
    }
}
```

### 4) التشغيل

اضغط **F5**. تبني الـ IDE المشروع بـ `dotnet build` (أول مرة تأخذ بضع ثوانٍ)، ثم تظهر نافذتك. اكتب اسمك (مثلًا «ريم») واضغط الزر، فيظهر: **أهلًا يا ريم!**

لاحظ:

- اسم الدالة يجب أن يكون بالضبط **`اسمالأداة_اسمالحدث`** مثل `btnHello_Click`، وأن تكون `static void`. هكذا تربطها الـ IDE بالحدث.
- المعامل `RadEvent e` اختياري، وفيه معلومات عن الحدث (مثل `e.X` و`e.Y` لموضع الفأرة).
- `Form1_Load` حدث خاص بالنموذج يعمل عند ظهوره، ومكانه المناسب لضبط القيم الابتدائية.
- لا يوجد `Main` في كودك! الـ IDE تضيف برنامج البداية `RadMain.cs` وحلقة الأحداث تلقائيًا.
- `public static partial class Form1`: الكلمة `partial` تعني أن الصنف مقسوم على ملفين: كودك في `Form1.cs`، والحقول المولّدة في `Form1_designer.cs`.

## الأدوات في الكود

كل أداة في النموذج أصبحت **حقلًا** في الصنف `Form1` بنفس اسمها، ولها خصائص ودوال:

| الكود | معناه |
|---|---|
| `txtName.Text` | النص المكتوب في مربع النص (قراءة وكتابة) |
| `lblResult.Text = "..."` | تغيير نص العنوان |
| `btnSave.Enabled = false` | تعطيل الزر |
| `lblTitle.Visible = false` | إخفاء الأداة |
| `lblResult.ForeColor = "255"` | لون الخط (أحمر، انظر الألوان بالأسفل) |
| `txtName.SetFocus()` | نقل المؤشر إلى الأداة |

ومن أي مكان في الكود يمكنك استخدام الدوال المساعدة:

| الدالة | وظيفتها |
|---|---|
| `MsgBox("...")` | رسالة منبثقة |
| `InputBox("سؤال")` | مربع إدخال يرجع النص |
| `ToNumber(text)` / `ToInt(text)` | تحويل نص إلى رقم (صفر إذا لم يكن رقمًا) |
| `End()` | إنهاء البرنامج |

وأي شيء تطبعه بـ `Console.WriteLine` يظهر في نافذة **Output**، وهذا مفيد جدًا لتتبع ما يحدث.

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

ثم اكتب الكود. لاحظ الدالة المساعدة العادية `Calculate` التي تمنع تكرار الكود في الأزرار الأربعة، تمامًا كما تعلمنا في درس الدوال:

<!-- test: {"set": {"txtA.Text": "7", "txtB.Text": "2"}, "events": ["btnDiv Click"], "expect": {"lblResult.Text": "الناتج = 3.5"}} -->
```csharp form run
public static partial class Form1
{
    // دالة مساعدة عادية (ليست حدثًا): تقرأ الرقمين وتحسب وتعرض الناتج
    static void Calculate(char op)
    {
        double a = ToNumber(txtA.Text);
        double b = ToNumber(txtB.Text);
        if (op == '/' && b == 0)
        {
            lblResult.Text = "لا يمكن القسمة على صفر";
            return;
        }
        double result = op switch
        {
            '+' => a + b,
            '-' => a - b,
            '*' => a * b,
            _ => a / b
        };
        lblResult.Text = $"الناتج = {result}";
        Console.WriteLine($"{a} {op} {b} = {result}");   // يظهر في Output
    }

    static void btnAdd_Click(RadEvent e) => Calculate('+');
    static void btnSub_Click(RadEvent e) => Calculate('-');
    static void btnMul_Click(RadEvent e) => Calculate('*');
    static void btnDiv_Click(RadEvent e) => Calculate('/');
}
```

```text output
7 / 2 = 3.5
```

جرّب: اكتب `7` و`2` واضغط `÷`، فيظهر **الناتج = 3.5**، ويظهر في نافذة Output السطر `7 / 2 = 3.5`.

## المتغيرات بين الأحداث

برنامجك يظل يعمل طوال ظهور النافذة، لذلك **الحقول الثابتة** (`static`) في الصنف تحتفظ بقيمتها بين ضغطة وأخرى:

<!-- test: {"set": {"txtPassword.Text": "1234"}, "events": ["btnLogin Click", "btnLogin Click", "btnLogin Click"], "expect": {"lblStatus.Text": "تم إيقاف المحاولات", "btnLogin.Enabled": "False"}} -->
```csharp form run
public static partial class Form1
{
    static int attempts = 0;     // يحتفظ بقيمته بين الأحداث

    static void btnLogin_Click(RadEvent e)
    {
        if (txtPassword.Text == "cs2026")
        {
            lblStatus.Text = "تم الدخول بنجاح";
            lblStatus.ForeColor = "32768";    // أخضر داكن
            return;
        }
        attempts++;
        lblStatus.Text = $"كلمة مرور خاطئة ({attempts} من 3)";
        lblStatus.ForeColor = "255";      // أحمر
        if (attempts >= 3)
        {
            btnLogin.Enabled = false;
            lblStatus.Text = "تم إيقاف المحاولات";
        }
    }
}
```

الألوان تُكتب بصيغة Visual Basic: رقم يساوي `R + G × 256 + B × 65536`، فالأحمر `255`، والأخضر الداكن `32768`، والأزرق `16711680`، والأسود `0`، والأبيض `16777215`.

هنا رسمنا `TextBox` باسم `txtPassword` (اجعل خاصيته `PasswordChar` تساوي `*` لكي تُخفى الحروف)، و`Button` باسم `btnLogin`، و`Label` باسم `lblStatus`.

> **مهم:** المتغيرات المحلية داخل الدالة تُنشأ من جديد مع كل حدث. أما الحقل `static int attempts` فيبقى طوال عمر البرنامج.

## أخطاء شائعة

### اسم الدالة لا يطابق اسم الأداة

إذا سمّيت الزر `btnHello` وكتبت الدالة `btnhello_Click` أو `Button1_Click`، **لن يحدث شيء** عند الضغط ولن يظهر خطأ. الحل الأسهل: انقر مرتين على الأداة في المصمم ودع الـ IDE تكتب اسم الدالة بنفسها.

### تعديل `Form1_designer.cs` بيدك

هذا الملف يُعاد توليده كلما حفظت النموذج، فتضيع تعديلاتك. اكتب كودك في `Form1.cs` فقط.

### أداة في الكود غير موجودة في النموذج

إذا كتبت `lblTotal.Text = "..."` ولا توجد أداة اسمها `lblTotal` يظهر خطأ البناء `CS0103: The name 'lblTotal' does not exist in the current context`. أضف الأداة في المصمم أو صحح الاسم.

## تمارين

### التمرين 1

برنامج «محوّل درجات الحرارة»: مربع نص `txtC` للدرجة المئوية، وزر `btnConvert`، وعنوان `lblF`. عند الضغط اكتب في العنوان الدرجة بالفهرنهايت (`C × 9 ÷ 5 + 32`) بالشكل `98.6 °F`.

<!-- test: {"set": {"txtC.Text": "37"}, "events": ["btnConvert Click"], "expect": {"lblF.Text": "98.6 °F"}} -->
```csharp form exercise
public static partial class Form1
{
    static void btnConvert_Click(RadEvent e)
    {
        // اقرأ txtC.Text واحسب ثم اكتب في lblF.Text
    }
}
```

<!-- test: {"set": {"txtC.Text": "37"}, "events": ["btnConvert Click"], "expect": {"lblF.Text": "98.6 °F"}} -->
```csharp form solution
public static partial class Form1
{
    static void btnConvert_Click(RadEvent e)
    {
        double c = ToNumber(txtC.Text);
        double f = c * 9 / 5 + 32;
        lblF.Text = $"{f} °F";
    }
}
```

### التمرين 2

عدّاد ضغطات: زر `btnClick` وزر `btnReset` وعنوان `lblCount`. كل ضغطة على `btnClick` تزيد العدد واحدًا وتعرضه، و`btnReset` يعيده إلى صفر.

<!-- test: {"events": ["btnClick Click", "btnClick Click", "btnClick Click"], "expect": {"lblCount.Text": "3"}} -->
```csharp form exercise
public static partial class Form1
{
    static void btnClick_Click(RadEvent e)
    {
    }

    static void btnReset_Click(RadEvent e)
    {
    }
}
```

<!-- test: {"events": ["btnClick Click", "btnClick Click", "btnClick Click"], "expect": {"lblCount.Text": "3"}} -->
```csharp form solution
public static partial class Form1
{
    static int count = 0;

    static void btnClick_Click(RadEvent e)
    {
        count++;
        lblCount.Text = count.ToString();
    }

    static void btnReset_Click(RadEvent e)
    {
        count = 0;
        lblCount.Text = "0";
    }
}
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["Save_Click", "btnSave_Click", "Click_btnSave", "OnSave"], "answer": 1, "explanation": "الاسم دائمًا اسمالأداة_اسمالحدث، والنقر المزدوج في المصمم يكتبه لك."}
```

```quiz
{"question": "في أي ملف تكتب كود معالجات الأحداث؟", "choices": ["Form1_designer.cs", "Form1.cs", "Form1.form", "RadMain.cs"], "answer": 1, "explanation": "Form1.cs ملفك، أما Form1_designer.cs فتولّده الـ IDE من جديد عند كل حفظ."}
```

```quiz
{"question": "كيف يحتفظ البرنامج بقيمة بين ضغطة وأخرى؟", "choices": ["بمتغير محلي داخل الدالة", "بحقل static في الصنف Form1", "لا يمكن", "بكتابتها في Label فقط"], "answer": 1, "explanation": "البرنامج يظل يعمل، والحقول الثابتة تبقى طوال عمره، أما المتغيرات المحلية فتُنشأ من جديد مع كل حدث."}
```

## الخلاصة

- مشروع **C# (GUI Bridge, .NET)**: الـ IDE ترسم النافذة، وبرنامجك يعالج الأحداث.
- معالج الحدث `static void اسمالأداة_الحدث(RadEvent e)` في `Form1.cs`، و`Form1_Load` عند الظهور.
- الأدوات حقول: `txtName.Text` و`lblResult.Text = ...` و`btnX.Enabled = false`.
- `MsgBox` و`InputBox` و`ToNumber` دوال مساعدة، و`Console.WriteLine` يكتب في Output.
