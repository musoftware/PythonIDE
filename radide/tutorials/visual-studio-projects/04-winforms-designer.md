# الدرس 4: مصمم Windows Forms ذهابًا وإيابًا

أهم ما يميز RAD IDE مع مشاريع Visual Studio: تفتح نموذج **Windows Forms** (`Form1.cs`) في **مصمم النماذج**، فتسحب الأدوات وتغير الخصائص، ثم تحفظ، فيُكتب التغيير في `Form1.Designer.cs` **بنفس الأسلوب الذي يكتبه Visual Studio**. هذا ما نسميه «ذهابًا وإيابًا» (round trip).

> **تشبيه:** تخيّل مترجمًا فوريًا بينك وبين زميل يتكلم لغة أخرى. أنت تتكلم بلغتك (السحب والإفلات في المصمم)، والمترجم ينقل كلامك بلغة زميلك (كود C# في `Form1.Designer.cs`) **كلمة بكلمة**، دون أن يغير شيئًا قاله زميلك من قبل. ثم يفتح زميلك المشروع في Visual Studio فيفهم كل شيء.

## الملفات الثلاثة للنموذج

| الملف | ما فيه | من يكتبه؟ |
|---|---|---|
| `Form1.cs` | **كودك**: معالجات الأحداث وأي منطق | أنت |
| `Form1.Designer.cs` | الدالة `InitializeComponent()`: إنشاء الأدوات وخصائصها وربط الأحداث | المصمم (في Visual Studio وفي RAD IDE) |
| `Form1.resx` | الموارد: الصور والأيقونات وعناصر القوائم | المصمم |

وهذا شكل مختصر لملف `Form1.Designer.cs`:

```csharp
partial class Form1
{
    private void InitializeComponent()
    {
        this.btnHello = new System.Windows.Forms.Button();
        this.txtName = new System.Windows.Forms.TextBox();
        this.SuspendLayout();
        //
        // btnHello
        //
        this.btnHello.Location = new System.Drawing.Point(12, 41);
        this.btnHello.Name = "btnHello";
        this.btnHello.Size = new System.Drawing.Size(120, 30);
        this.btnHello.Text = "رحّب";
        this.btnHello.Click += new System.EventHandler(this.btnHello_Click);
        // ...
        this.Controls.Add(this.btnHello);
        this.Controls.Add(this.txtName);
        this.ResumeLayout(false);
    }

    private System.Windows.Forms.Button btnHello;
    private System.Windows.Forms.TextBox txtName;
}
```

## فتح النموذج في المصمم

1. في **Solution Explorer** انقر مرتين على `Form1.cs`، أو انقر بالزر الأيمن عليه واختر **View Designer** (عرض المصمم).
2. يظهر النموذج في المصمم، ومعه **Toolbox** (صندوق الأدوات) بأسماء أدوات Windows Forms (`Button` و`TextBox` و`DataGridView`...)، ونافذة **Properties** (الخصائص) بأسماء .NET (`Location.X` و`Size.Width` و`Font.Bold`...).
3. للتنقل بين التصميم والكود: **View > Code** (عرض > الكود) أو `F7`، و**View > Designer** (عرض > المصمم) أو `Shift+F7`.

## ماذا يُكتب عند الحفظ؟

المصمم يقرأ `InitializeComponent` تعليمةً تعليمة، ويحفظ مكان كل تعليمة بالضبط. وعند الحفظ (`Ctrl+S`) **يرقّع** (patch) الملف في المواضع التي تغيرت فقط:

| ما فعلته في المصمم | ما يتغير في `Form1.Designer.cs` |
|---|---|
| غيّرت خاصية (مثل `Text`) | تُعاد كتابة **تلك التعليمة فقط** |
| أعدت خاصية إلى قيمتها الافتراضية | تُحذف تعليمتها |
| أضفت أداة جديدة | تعريف حقل + `new` + كتلة خصائص بأسلوب Visual Studio + `Controls.Add` |
| حذفت أداة | كل التعليمات التي تذكرها وتعريف حقلها |
| غيّرت اسم أداة (`Name`) | يتغير الاسم في `InitializeComponent` والحقول (وتبقى أسماء معالجات الأحداث كما هي، مثل Visual Studio) |
| عناصر قوائم وصور وتلميحات | تُكتب في الأماكن المناسبة وفي `Form1.resx` |

وكل ما لا يفهمه المصمم (تعليقات، و`#region`، وأدوات خاصة، وكود كتبته بيدك خارج `InitializeComponent`) **يبقى كما هو حرفيًا**. ويحترم المصمم أسلوب الملف: إذا كان يكتب `this.` والأسماء الكاملة `System.Windows.Forms.Button` فسيكتب الأدوات الجديدة بنفس الطريقة.

## إنشاء معالج حدث

1. في المصمم **انقر مرتين** على الزر `btnHello`.
2. تضيف الـ IDE إلى `Form1.cs` الدالة:

```csharp
private void btnHello_Click(object sender, EventArgs e)
{

}
```

3. وتضيف إلى `Form1.Designer.cs` سطر الربط:

```csharp
this.btnHello.Click += new System.EventHandler(this.btnHello_Click);
```

4. اكتب الكود داخل الدالة:

```csharp
private void btnHello_Click(object sender, EventArgs e)
{
    MessageBox.Show("أهلًا يا " + txtName.Text);
}
```

لأحداث أخرى: اختر الأداة، ثم انقر أيقونة **الأحداث** (البرق) في نافذة Properties، وانقر مرتين على الحدث (مثل `TextChanged` أو `KeyDown`). يكتب المصمم التوقيع الصحيح لكل حدث (`KeyEventArgs` و`MouseEventArgs`...).

> **مهم:** هنا الكود هو كود **Windows Forms الحقيقي** (`MessageBox.Show` و`txtName.Text`)، وليس كود GUI Bridge الذي تعلمته في دورة C# (`MsgBox` و`static void ... (RadEvent e)`). مشروع Visual Studio يبقى مشروع Visual Studio.

## إضافة نموذج جديد

انقر بالزر الأيمن على المشروع: **Add > New Item...** واختر **Windows Form** واكتب الاسم `SettingsForm`. تُنشأ الملفات `SettingsForm.cs` و`SettingsForm.Designer.cs`، وتفتحه في المصمم. ولعرضه من النموذج الرئيسي:

```csharp
private void btnSettings_Click(object sender, EventArgs e)
{
    using var dlg = new SettingsForm();
    dlg.ShowDialog(this);
}
```

## التجربة: ذهاب وإياب حقيقي

1. افتح مشروع Windows Forms من Visual Studio في RAD IDE (**File > Open Project...**).
2. افتح `Form1` في المصمم، وغيّر `Text` لأحد الأزرار، وأضف `CheckBox` جديدًا، ثم احفظ.
3. افتح مجلد المشروع في Git (أو قارن الملف): ستجد التغيير في سطرين أو ثلاثة فقط من `Form1.Designer.cs`، وباقي الملف لم يتغير.
4. افتح المشروع في Visual Studio: يظهر النموذج بالتعديلات، ويمكنك المتابعة هناك.
5. عدّل في Visual Studio وارجع إلى RAD IDE: تقرأ الـ IDE الملف من جديد وتعرض التعديلات.

> **نصيحة:** إذا عدّلت الملف خارج الـ IDE وهي مفتوحة، استخدم الزر الأيمن على المشروع ثم **Reload Project**، لتقرأ الـ IDE الملفات من القرص.

## أخطاء شائعة

- **كتابة كودك داخل `InitializeComponent`:** قد يكون آمنًا في RAD IDE، لكن Visual Studio يعيد كتابة هذه الدالة ويحذفه. اكتب كودك في `Form1.cs` (مثلًا في المُنشئ بعد `InitializeComponent();` أو في `Form1_Load`).
- **حذف معالج الحدث من `Form1.cs` وحده:** يبقى سطر الربط `+= ...btnHello_Click` في `Form1.Designer.cs` فيفشل البناء (`CS1061`). احذف الحدث من نافذة Properties، أو احذف السطرين معًا.
- **نسيان الإطار الصحيح:** مشاريع Windows Forms الحديثة تحتاج `<TargetFramework>net8.0-windows</TargetFramework>` و`<UseWindowsForms>true</UseWindowsForms>` في `.csproj`.

## اختبر نفسك

```quiz
{"question": "أي ملف يكتبه المصمم عند حفظ نموذج Windows Forms؟", "choices": ["Form1.cs", "Form1.Designer.cs (وForm1.resx للموارد)", "Program.cs", ".sln"], "answer": 1, "explanation": "المصمم يكتب InitializeComponent في Form1.Designer.cs، وكودك في Form1.cs لا يلمسه إلا لإضافة معالجات الأحداث."}
```

```quiz
{"question": "غيّرت خاصية Text لزر واحد وحفظت. ماذا يتغير في Form1.Designer.cs؟", "choices": ["يُعاد توليد الملف كله", "تعليمة Text لهذا الزر فقط", "لا شيء", "يُحذف الملف"], "answer": 1, "explanation": "المصمم يرقّع ما تغير فقط، ويبقى الباقي مطابقًا للأصل بايتًا ببايت."}
```

```quiz
{"question": "ما اختصار التنقل من المصمم إلى الكود؟", "choices": ["F5", "F7", "F9", "Ctrl+B"], "answer": 1, "explanation": "View > Code هو F7، وView > Designer هو Shift+F7."}
```

## الخلاصة

- انقر مرتين على `Form1.cs` (أو **View Designer**) لفتح النموذج في المصمم.
- الحفظ يرقّع `Form1.Designer.cs` في المواضع المتغيرة فقط وبأسلوب Visual Studio، وكل ما لا يفهمه المصمم يبقى كما هو.
- النقر المزدوج على أداة ينشئ المعالج في `Form1.cs` وسطر الربط في `Form1.Designer.cs`.
- المشروع يبقى صالحًا لـ Visual Studio في الاتجاهين.
