# الدرس 14: الأدوات والأحداث: القوائم والاختيارات والمؤقت

في الدرس السابق صنعنا نوافذ بأزرار ومربعات نص. اليوم نضيف أدوات أكثر: **القائمة** (ListBox)، و**القائمة المنسدلة** (ComboBox)، و**مربع الاختيار** (CheckBox)، و**زر الخيار** (RadioButton)، و**المؤقت** (Timer)، و**شريط التقدم** (ProgressBar).

## القائمة `ListBox`

في Tkinter تصبح `ListBox` أداة `tk.Listbox`. أهم ما تحتاجه:

| العملية | الكود |
|---|---|
| إضافة عنصر في النهاية | `self.lstNames.insert("end", "Ali")` |
| عدد العناصر | `self.lstNames.size()` |
| العنصر رقم `i` | `self.lstNames.get(i)` |
| كل العناصر | `self.lstNames.get(0, "end")` |
| رقم العنصر المحدد | `self.lstNames.curselection()` (صف، فارغ إن لم يُحدد شيء) |
| حذف العنصر `i` | `self.lstNames.delete(i)` |
| مسح الكل | `self.lstNames.delete(0, "end")` |

وحدثها المهم: `SelectedIndexChanged`، ويعمل عندما يختار المستخدم عنصرًا.

### مثال: قائمة المهام

ارسم النموذج:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtTask` | (فارغ) |
| `Button` | `btnAdd` | `أضف` |
| `Button` | `btnRemove` | `احذف المحدد` |
| `ListBox` | `lstTasks` | |
| `Label` | `lblInfo` | (فارغ) |

<!-- test: {"form": {"Text": "مهامي", "Width": 380, "Height": 330}, "controls": [["TextBox", "txtTask", {"Text": "", "Left": 16, "Top": 16, "Width": 220}], ["Button", "btnAdd", {"Text": "أضف", "Left": 246, "Top": 14, "Width": 110, "Height": 26}], ["Button", "btnRemove", {"Text": "احذف المحدد", "Left": 246, "Top": 48, "Width": 110, "Height": 26}], ["ListBox", "lstTasks", {"Left": 16, "Top": 48, "Width": 220, "Height": 200}], ["Label", "lblInfo", {"Text": "", "Left": 16, "Top": 260, "Width": 340}]], "steps": [["set", "txtTask", "مذاكرة"], ["click", "btnAdd"], ["set", "txtTask", "رياضة"], ["click", "btnAdd"], ["set", "txtTask", "قراءة"], ["click", "btnAdd"], ["select", "lstTasks", 1], ["click", "btnRemove"]], "expect": {"lstTasks": "مذاكرة|قراءة", "lblInfo": "عدد المهام: 2", "txtTask": ""}} -->
```python form run
from tkinter import messagebox

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def update_info(self):
        self.lblInfo.config(text=f"عدد المهام: {self.lstTasks.size()}")

    def btnAdd_Click(self):
        task = self.txtTask.get().strip()
        if not task:
            messagebox.showwarning("تنبيه", "اكتب المهمة أولًا")
            return
        self.lstTasks.insert("end", task)
        self.txtTask_var.set("")          # امسح المربع
        self.txtTask.focus_set()          # وأعد المؤشر إليه
        self.update_info()

    def btnRemove_Click(self):
        selected = self.lstTasks.curselection()
        if selected:
            self.lstTasks.delete(selected[0])
            self.update_info()

    def lstTasks_SelectedIndexChanged(self):
        selected = self.lstTasks.curselection()
        if selected:
            print("اخترت:", self.lstTasks.get(selected[0]))


if __name__ == "__main__":
    Form1().show()
```

> **كيف أنشئ دالة حدث غير `Click`؟** حدد الأداة في المصمم، ثم في نافذة **الخصائص** افتح تبويب **Events** (الأحداث)، وانقر مرتين على اسم الحدث (مثل `SelectedIndexChanged`). وأسهل من ذلك: النقر المزدوج على الأداة نفسها ينشئ **حدثها الافتراضي** (للزر `Click`، وللقائمة `SelectedIndexChanged`).

## القائمة المنسدلة `ComboBox`

في Tkinter تصبح `ttk.Combobox`. يمكنك كتابة عناصرها في الخاصية **Items** في المصمم مفصولة بفاصلة منقوطة (مثل `شاي;قهوة;كاكاو`)، أو من الكود:

| العملية | الكود |
|---|---|
| تحديد العناصر | `self.cboCity["values"] = ["Cairo", "Giza"]` |
| النص المختار | `self.cboCity.get()` |
| رقم المختار | `self.cboCity.current()` (`-1` إن لم يُختر شيء) |
| اختيار العنصر رقم `i` | `self.cboCity.current(i)` |

## مربع الاختيار `CheckBox` وزر الخيار `RadioButton`

- كل `CheckBox` له متغير منطقي اسمه `اسمالأداة_var`: `self.chkSugar_var.get()` يرجع `True` أو `False`.
- أزرار الخيار `RadioButton` في النموذج تشترك في متغير واحد اسمه `self._radio`، وقيمته هي **اسم** الزر المختار، مثل `"optLarge"`. لذلك لا يمكن اختيار أكثر من زر في نفس الوقت.
- حدث التغيير لكليهما اسمه `CheckedChanged`.

### مثال: طلب مشروب

| الأداة | Name | Text / Items |
|---|---|---|
| `ComboBox` | `cboDrink` | Items: `شاي;قهوة;كاكاو` |
| `RadioButton` | `optSmall` | `صغير` |
| `RadioButton` | `optLarge` | `كبير` |
| `CheckBox` | `chkSugar` | `سكر` |
| `CheckBox` | `chkMilk` | `لبن` |
| `Button` | `btnOrder` | `اطلب` |
| `Label` | `lblOrder` | (فارغ) |

<!-- test: {"form": {"Text": "المقهى", "Width": 340, "Height": 300}, "controls": [["ComboBox", "cboDrink", {"Items": "شاي;قهوة;كاكاو", "Left": 16, "Top": 16, "Width": 150}], ["RadioButton", "optSmall", {"Text": "صغير", "Left": 16, "Top": 52, "Width": 90}], ["RadioButton", "optLarge", {"Text": "كبير", "Left": 110, "Top": 52, "Width": 90}], ["CheckBox", "chkSugar", {"Text": "سكر", "Left": 16, "Top": 84, "Width": 90}], ["CheckBox", "chkMilk", {"Text": "لبن", "Left": 110, "Top": 84, "Width": 90}], ["Button", "btnOrder", {"Text": "اطلب", "Left": 16, "Top": 120, "Width": 100, "Height": 28}], ["Label", "lblOrder", {"Text": "", "Left": 16, "Top": 164, "Width": 300}]], "steps": [["select", "cboDrink", 1], ["click", "optLarge"], ["click", "chkMilk"], ["click", "btnOrder"]], "expect": {"lblOrder": "قهوة كبير مع لبن - 33 جنيه"}} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401

PRICES = {"شاي": 10, "قهوة": 25, "كاكاو": 20}


class Form1(Form1Designer):

    def Form1_Load(self):
        self.cboDrink.current(0)          # اختر أول مشروب
        self._radio.set("optSmall")       # الحجم الصغير افتراضيًا

    def btnOrder_Click(self):
        drink = self.cboDrink.get()
        price = PRICES[drink]
        size = "كبير" if self._radio.get() == "optLarge" else "صغير"
        if size == "كبير":
            price += 5
        extras = []
        if self.chkSugar_var.get():
            extras.append("سكر")
        if self.chkMilk_var.get():
            extras.append("لبن")
            price += 3
        text = f"{drink} {size}"
        if extras:
            text += " مع " + " و".join(extras)
        self.lblOrder.config(text=f"{text} - {price} جنيه")


if __name__ == "__main__":
    Form1().show()
```

## المؤقت `Timer`

**المؤقت** أداة غير مرئية (تظهر أسفل المصمم وليس على النموذج)، تطلق الحدث `Tick` كل فترة تحددها الخاصية **Interval** بالمللي ثانية (1000 = ثانية واحدة).

| الخاصية / الدالة | المعنى |
|---|---|
| `Interval` | الفترة بالمللي ثانية |
| `Enabled` | هل يعمل الآن؟ `self.tmrClock.Enabled = True` |
| `Start()` و `Stop()` | تشغيل وإيقاف |

### مثال: عدّاد تنازلي مع شريط تقدم

| الأداة | Name | الخصائص |
|---|---|---|
| `Label` | `lblTime` | FontSize = `20` |
| `ProgressBar` | `prgTime` | Maximum = `10` |
| `Button` | `btnStart` | Text = `ابدأ` |
| `Timer` | `tmrCount` | Interval = `1000` |

<!-- test: {"form": {"Text": "عدّاد تنازلي", "Width": 300, "Height": 200}, "controls": [["Label", "lblTime", {"Text": "10", "Left": 20, "Top": 16, "Width": 240, "Height": 40, "FontSize": 20}], ["ProgressBar", "prgTime", {"Maximum": 10, "Value": 0, "Left": 20, "Top": 66, "Width": 240}], ["Button", "btnStart", {"Text": "ابدأ", "Left": 20, "Top": 100, "Width": 100, "Height": 28}], ["Timer", "tmrCount", {"Interval": 1000}]], "steps": [["click", "btnStart"], ["tick", "tmrCount", 10]], "expect": {"lblTime": "انتهى الوقت!", "prgTime": "10"}} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnStart_Click(self):
        self.seconds = 10
        self.lblTime.config(text="10")
        self.prgTime["value"] = 0
        self.tmrCount.Start()
        self.btnStart.config(state="disabled")

    def tmrCount_Tick(self):
        self.seconds -= 1
        self.prgTime["value"] = 10 - self.seconds
        if self.seconds > 0:
            self.lblTime.config(text=str(self.seconds))
        else:
            self.tmrCount.Stop()
            self.lblTime.config(text="انتهى الوقت!")
            self.btnStart.config(state="normal")
            print("انتهى العدّ")


if __name__ == "__main__":
    Form1().show()
```

> **لماذا لا نستخدم حلقة و`time.sleep`؟** لأن النافذة تتجمد! حلقة الأحداث لا تستطيع رسم النافذة أو الاستجابة للفأرة طالما كودك مشغول. المؤقت يعطي النافذة فرصة للتنفس بين كل `Tick` والآخر.

## قاعدة ذهبية: معالجات الأحداث يجب أن تكون سريعة

أي عمل طويل داخل `_Click` يجمّد النافذة حتى ينتهي. للأعمال الطويلة (تحميل ملف كبير مثلًا) قسّمها بمؤقت، أو استخدم `self.root.after(مللي, دالة)` لتأجيل جزء منها.

## أخطاء شائعة

- **`curselection()` ترجع صفًا** وليس رقمًا: اكتب `selected[0]`، وتأكد أولًا أنه غير فارغ.
- **نسيان إيقاف المؤقت:** يستمر `Tick` في العمل إلى الأبد، وقد تصبح القيم سالبة.
- **استخدام اسم الزر في `_radio` بشكل خاطئ:** القيمة هي **Name** الزر (`"optLarge"`) وليست نصه (`"كبير"`).

## تمارين

### التمرين 1

نموذج فيه `ListBox` اسمه `lstNumbers` و`Button` اسمه `btnFill` و`Label` اسمه `lblSum`. عند الضغط: املأ القائمة بالأعداد من 1 إلى 5 (امسحها أولًا)، واعرض مجموعها بالشكل `المجموع: 15`.

<!-- test: {"controls": [["ListBox", "lstNumbers", {}], ["Button", "btnFill", {"Text": "املأ"}], ["Label", "lblSum", {}]], "click": ["btnFill", "btnFill"], "expect": {"lstNumbers": "1|2|3|4|5", "lblSum": "المجموع: 15"}} -->
```python form exercise
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnFill_Click(self):
        pass


if __name__ == "__main__":
    Form1().show()
```

<!-- test: {"controls": [["ListBox", "lstNumbers", {}], ["Button", "btnFill", {"Text": "املأ"}], ["Label", "lblSum", {}]], "click": ["btnFill", "btnFill"], "expect": {"lstNumbers": "1|2|3|4|5", "lblSum": "المجموع: 15"}} -->
```python form solution
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnFill_Click(self):
        self.lstNumbers.delete(0, "end")
        total = 0
        for n in range(1, 6):
            self.lstNumbers.insert("end", n)
            total += n
        self.lblSum.config(text=f"المجموع: {total}")


if __name__ == "__main__":
    Form1().show()
```

### التمرين 2

نموذج فيه `CheckBox` اسمه `chkAgree` بنص `أوافق على الشروط`، و`Button` اسمه `btnNext` و`Label` اسمه `lblMsg`. عند الضغط على الزر: إذا كان المربع محددًا اكتب في العنوان `شكرًا لك`، وإلا اكتب `يجب الموافقة أولًا`.

<!-- test: {"controls": [["CheckBox", "chkAgree", {"Text": "أوافق على الشروط"}], ["Button", "btnNext", {"Text": "التالي"}], ["Label", "lblMsg", {}]], "click": ["chkAgree", "btnNext"], "expect": {"lblMsg": "شكرًا لك"}} -->
```python form exercise
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnNext_Click(self):
        pass


if __name__ == "__main__":
    Form1().show()
```

<!-- test: {"controls": [["CheckBox", "chkAgree", {"Text": "أوافق على الشروط"}], ["Button", "btnNext", {"Text": "التالي"}], ["Label", "lblMsg", {}]], "click": ["chkAgree", "btnNext"], "expect": {"lblMsg": "شكرًا لك"}} -->
```python form solution
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnNext_Click(self):
        if self.chkAgree_var.get():
            self.lblMsg.config(text="شكرًا لك")
        else:
            self.lblMsg.config(text="يجب الموافقة أولًا")


if __name__ == "__main__":
    Form1().show()
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع self.lstTasks.curselection() إذا لم يُحدد أي عنصر؟", "choices": ["-1", "None", "صفًا فارغًا ()", "0"], "answer": 2, "explanation": "ترجع صفًا فارغًا، لذلك نتحقق بـ if selected: قبل استخدام selected[0]."}
```

```quiz
{"question": "مؤقت Interval له 500، كم مرة يُطلق Tick في الثانية؟", "choices": ["مرة", "مرتين", "500 مرة", "نصف مرة"], "answer": 1, "explanation": "500 مللي ثانية = نصف ثانية، أي مرتين في الثانية."}
```

```quiz
{"question": "لماذا لا نستخدم time.sleep داخل معالج حدث لعمل عدّاد؟", "choices": ["لأنها غير موجودة في Python", "لأنها تجمّد النافذة حتى تنتهي", "لأنها أسرع من اللازم", "لأنها تحذف الأدوات"], "answer": 1, "explanation": "حلقة الأحداث لا تعمل أثناء sleep فتتجمد النافذة، والمؤقت هو الحل الصحيح."}
```

## الخلاصة

- `ListBox`: `insert` و`get` و`curselection` و`delete`، وحدث `SelectedIndexChanged`.
- `ComboBox`: `["values"]` و`get()` و`current()`.
- `CheckBox` له `اسمالأداة_var`، وأزرار `RadioButton` تشترك في `self._radio`.
- `Timer` بخاصيتي `Interval` و`Enabled` ودالتي `Start` و`Stop` وحدث `Tick`، ولا نجمّد النافذة أبدًا.
