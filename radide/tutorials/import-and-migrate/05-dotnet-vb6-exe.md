# الدرس 5: برامج .NET وVB6 المترجمة

**في هذا الدرس ستتعلم:**

- كيف يستعيد المعالج برنامج **.NET** (C# أو VB.NET) بنماذج Windows Forms.
- مقارنة حقيقية: كود C# الأصلي، والكود الذي كتبه المعالج بلغة Python.
- ماذا يُستعاد من برنامج **Visual Basic 6** المترجم، وما الذي لا يُستعاد.
- ماذا تفعل بالأسطر التي بقيت تعليقات `# C#: ...`.

## برامج .NET: الأفضل حظًا

برامج .NET تحتفظ داخلها بوصف كامل تقريبًا للكود (لغة وسيطة اسمها IL)، ولذلك تُستعاد بدقة عالية جدًا. المعالج يعمل بثلاث مراحل:

**المرحلة 1: فك الترجمة.** الأداة **ILSpy** (نسختها لسطر الأوامر `ilspycmd`، تُثبّت في `%LOCALAPPDATA%\RADIDE\tools`) تستعيد مشروع C# كاملًا من الملف، ويُحفظ في المجلد `_original` داخل المشروع الجديد.

**المرحلة 2: النماذج.** الدالة `InitializeComponent` في كل نموذج تُقرأ سطرًا سطرًا، فتتحول إلى ملف `.form`: الأدوات، والمواقع، والأحجام، والنصوص، والخطوط، والألوان، والقوائم، وربط الأحداث.

**المرحلة 3: الكود.** كود الأحداث يُترجم إلى Python بقواعد لأشهر دوال WinForms و.NET (`MessageBox.Show` و`Text` و`Checked` و`Items` و`Convert` ...). وأي سطر لا تعرفه القواعد يبقى في الكود تعليقًا يبدأ بـ `# C#:`، وإذا سمحت بالذكاء الاصطناعي يعيد كتابة الدوال التي فيها هذه الأسطر.

## مقارنة حقيقية

هذا جزء من كود برنامج صغير بلغة C# (موجود مع البيئة في `samples\Tests\ExeImport\WinForms_DotNet\source`):

```csharp
private void btnGreet_Click(object sender, EventArgs e)
{
    string name = txtName.Text.Trim();
    if (name == "")
    {
        MessageBox.Show("Please type a name", "Hello");
        return;
    }
    if (chkUpper.Checked)
    {
        name = name.ToUpper();
    }
    count++;
    lblResult.Text = "Hello, " + name + "! (" + count.ToString() + ")";
    lstLog.Items.Add(name);
    MessageBox.Show("Hello, " + name + "!", "Greeting");
}
```

بنينا البرنامج إلى `WinHello.exe`، ثم استوردناه بالمعالج إلى **Python (Tkinter)**. هذا الكود الذي كتبه المعالج (من الملف `Form1.py` في المشروع الناتج، مختصرًا قليلًا). جرّبه: اكتب اسمًا واضغط الزر.

<!-- test: {"controls": [["TextBox", "txtName"], ["CheckBox", "chkUpper", {"Text": "Upper case"}], ["Button", "btnGreet", {"Text": "Greet"}], ["Label", "lblResult"], ["ListBox", "lstLog"]], "set": {"txtName": "Sara"}, "click": ["btnGreet"], "expect": {"lblResult": "Hello, Sara! (1)", "lstLog": "Sara"}, "msgbox": ["Hello, Sara!"]} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from tkinter import messagebox


class Form1(Form1Designer):
    """Write your event handlers here."""

    # fields of the original form
    count = 0

    def Form1_Load(self):
        self.lblResult.config(text="Ready")

    def btnGreet_Click(self):
        text = self.txtName_var.get().strip()
        if text == "":
            messagebox.showinfo("Hello", "Please type a name")
            return
        if self.chkUpper_var.get():
            text = text.upper()
        self.count += 1
        self.lblResult.config(text="Hello, " + text + "! (" + str(self.count) + ")")
        self.lstLog.insert("end", text)
        messagebox.showinfo("Greeting", "Hello, " + text + "!")


if __name__ == "__main__":
    Form1().show()
```

قارن سطرًا بسطر:

| C# | Python الذي كتبه المعالج |
|---|---|
| `txtName.Text.Trim()` | `self.txtName_var.get().strip()` |
| `MessageBox.Show(text, title)` | `messagebox.showinfo(title, text)` |
| `chkUpper.Checked` | `self.chkUpper_var.get()` |
| `name.ToUpper()` | `text.upper()` |
| `count++` | `self.count += 1` |
| `count.ToString()` | `str(self.count)` |
| `lstLog.Items.Add(name)` | `self.lstLog.insert("end", text)` |

وفي تقرير هذا الاستيراد (`IMPORT_REPORT.md`) تحت **Translated by rules**: «translated to Python by rules: exitToolStripMenuItem_Click, btnGreet_Click, lstLog_DoubleClick, Form1_Load»، أي أن كل الأحداث تُرجمت بالقواعد دون حاجة للذكاء الاصطناعي.

## برامج Visual Basic 6 المترجمة

برنامج VB6 المترجم يبدأ بتعليمة تستدعي `ThunRTMain` من مكتبة `MSVBVM60.DLL`، ويحمل داخله **رأسًا** يبدأ بالبصمة `VB5!`. من هذا الرأس يصل المعالج إلى جداول البرنامج:

- **أسماء** النماذج والوحدات والأصناف.
- **أدوات** كل نموذج: أسماؤها وأنواعها ونصوصها، ومواقعها إذا أمكن قراءتها (وإلا تُرتب في شبكة مرتبة).
- **الأحداث التي فيها كود** (مثل `cmdOK_Click`).

ثم يكتب ملف `.frm` لكل نموذج، ويمرره إلى مستورد VB6 الذي رأيناه في الدرس 2.

**ما لا يُستعاد:** **جسم** الكود نفسه. برامج VB6 مترجمة إما إلى P-code أو إلى كود آلة أصلي، والمعالج لا يفك ترجمتهما. لكن التقرير يعطيك **النصوص الثابتة** الموجودة في البرنامج (رسائل، وعناوين، وأسماء ملفات)، و**قائمة الإجراءات** التي تحتاج إعادة كتابة. هذه النصوص تساعدك كثيرًا على تخمين ما كان يفعله كل زر، ويمكنك أن تطلب من الذكاء الاصطناعي في المحرر المساعدة في إعادة كتابتها.

هذا مثال يبحث عن بصمة `VB5!` في بايتات وهمية، ويستخرج النصوص المقروءة كما يفعل التقرير:

```python run
import re

data = b"MZ\x90\x00\x00VB5!\x01\x00frmMain\x00\x00Hello from VB6\x00\x07\x01cmdOK\x00Total: \x00"

offset = data.find(b"VB5!")
print("رأس VB5! عند البايت:", offset)

strings = re.findall(rb"[ -~]{5,}", data)
for s in strings:
    print("نص:", s.decode("ascii"))
```

```text output
رأس VB5! عند البايت: 5
نص: frmMain
نص: Hello from VB6
نص: cmdOK
نص: Total:
```

النمط `[ -~]{5,}` معناه «5 حروف مقروءة متتالية أو أكثر». لاحظ أن البصمة `VB5!` نفسها لم تظهر، لأنها 4 حروف فقط.

## أخطاء شائعة

- **برنامج .NET يظهر كبرنامج أصلي:** بعض برامج .NET الحديثة ملف `exe` صغير بجانبه ملف `.dll` يحتوي البرنامج الفعلي. ضع الملفين في نفس المجلد قبل الاستيراد، أو استورد ملف `.dll` مباشرة.
- **ilspycmd غير مثبت:** يحتاج .NET SDK. المعالج يخبرك في صفحة النوع بالأدوات الناقصة.
- **حذف أسطر `# C#:` دون فهمها:** كل سطر منها كود أصلي لم يُترجم. ترجمه يدويًا أو بـ `Ctrl+I`.
- **توقع كود VB6 كاملًا من exe:** ستحصل على النماذج والأحداث والنصوص، والكود تكتبه من جديد.

## تمارين

### تمرين 1: نصوص أقصر

عدّل النمط ليقبل النصوص من **4 حروف** على الأقل، ثم اطبع عدد النصوص التي وجدها والنصوص نفسها. هل ظهرت البصمة `VB5!` الآن؟

```python exercise
import re

data = b"MZ\x90\x00\x00VB5!\x01\x00frmMain\x00\x00Hello from VB6\x00\x07\x01cmdOK\x00Total: \x00"
strings = re.findall(rb"[ -~]{5,}", data)
print("عدد النصوص:", len(strings))
```

```python solution
import re

data = b"MZ\x90\x00\x00VB5!\x01\x00frmMain\x00\x00Hello from VB6\x00\x07\x01cmdOK\x00Total: \x00"
strings = re.findall(rb"[ -~]{4,}", data)
print("عدد النصوص:", len(strings))
for s in strings:
    print(s.decode("ascii"))
```

```text output
عدد النصوص: 5
VB5!
frmMain
Hello from VB6
cmdOK
Total: 
```

### تمرين 2: من C# إلى Python بيدك

ترجم هذا الكود من C# إلى Python كما يفعل المعالج: `string s = "  Ahmed ".Trim().ToUpper(); Console.WriteLine(s.Length);`

```python exercise
# اكتب الترجمة هنا
```

```python solution
s = "  Ahmed ".strip().upper()
print(len(s))
```

```text output
5
```

## اختبر نفسك

```quiz
{"question": "أي أداة يستخدمها المعالج لفك ترجمة برامج .NET؟", "choices": ["Ghidra", "ILSpy (ilspycmd)", "pycdc", "capstone"], "answer": 1, "explanation": "ilspycmd يستعيد مشروع C# من الملف."}
```

```quiz
{"question": "ماذا يعني سطر يبدأ بـ # C#: في الكود المستورد؟", "choices": ["تعليق للزينة", "سطر C# أصلي لم تعرفه القواعد، ويحتاج ترجمة", "خطأ في البيئة", "سطر محذوف"], "answer": 1, "explanation": "هذه الأسطر تترجمها يدويًا أو بالذكاء الاصطناعي."}
```

```quiz
{"question": "ما الذي لا يستعيده المعالج من برنامج VB6 مترجم؟", "choices": ["أسماء النماذج", "أسماء الأدوات", "جسم كود الأحداث", "النصوص الثابتة"], "answer": 2, "explanation": "P-code وكود الآلة لا يُفك ترجمتهما؛ تحصل على الأحداث الفارغة والنصوص."}
```

## الخلاصة

- .NET: ILSpy ثم النماذج من `InitializeComponent` ثم ترجمة الكود بالقواعد (والذكاء الاصطناعي اختياريًا).
- الكود الناتج قريب جدًا من الأصل، وما لم يُترجم يبقى `# C#: ...`.
- VB6 المترجم: النماذج والأدوات والأحداث والنصوص، أما جسم الكود فتعيد كتابته.
