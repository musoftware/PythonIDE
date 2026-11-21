# الدرس 15: نماذج PySide6 (Qt)

تعلمنا Tkinter لأنها بسيطة وتأتي مع Python. لكن عندما تريد برامج **بمظهر احترافي حديث**، ودعم ممتاز للعربية والاتجاه من اليمين لليسار، وأدوات متقدمة مثل الجداول والرسوم، فالخيار الأشهر هو **Qt** عبر مكتبة **PySide6** (مكتبة Qt الرسمية لـ Python).

والخبر السعيد: **مصمم النماذج نفسه** يعمل مع Qt! ترسم النافذة بنفس الأدوات، والـ IDE تولّد كود PySide6 بدل Tkinter.

## Tkinter أم PySide6؟

| | Tkinter | PySide6 (Qt) |
|---|---|---|
| التثبيت | مدمجة مع Python | مكتبة خارجية (`pip install PySide6`) |
| الحجم | صغيرة جدًا | كبيرة (عشرات الميجابايت) |
| المظهر | بسيط | حديث واحترافي |
| الأدوات | أساسية | كثيرة جدًا (جداول، رسوم، متصفح ويب...) |
| مناسبة لـ | التعلم والأدوات الصغيرة | التطبيقات الكبيرة والتجارية |

## إنشاء مشروع PySide6

1. **File > New Project**.
2. اختر **Python > Python (PySide6 / Qt)** والقالب **Windows Application**.
3. سمّ المشروع `QtHello`.

إذا لم تكن PySide6 مثبتة في Python التي يعمل بها المشروع، فثبّتها من **Project > Manage Packages...** كما تعلمنا في الدرس 12 (ابحث عن `PySide6`). المفسّر المدمج مع RAD IDE فيه PySide6 جاهزة غالبًا.

ستجد نفس الملفات الثلاثة: `Form1.form` و`Form1_designer.py` (مولَّد) و`Form1.py` (كودك). لكن الكود المولَّد الآن يستخدم أدوات Qt:

| الأداة في المصمم | أداة Qt | القراءة | التغيير |
|---|---|---|---|
| `TextBox` | `QLineEdit` | `self.txtName.text()` | `self.txtName.setText("...")` |
| `Label` | `QLabel` | `self.lblX.text()` | `self.lblX.setText("...")` |
| `Button` | `QPushButton` | `self.btnX.text()` | `self.btnX.setText("...")` |
| `CheckBox` | `QCheckBox` | `self.chkX.isChecked()` | `self.chkX.setChecked(True)` |
| `RadioButton` | `QRadioButton` | `self.optX.isChecked()` | `self.optX.setChecked(True)` |
| `ListBox` | `QListWidget` | `self.lstX.currentRow()` | `self.lstX.addItem("...")` |
| `ComboBox` | `QComboBox` | `self.cboX.currentText()` | `self.cboX.addItems([...])` |
| `NumericUpDown` | `QSpinBox` | `self.numX.value()` | `self.numX.setValue(5)` |

> **قاعدة سهلة:** في Qt القراءة باسم الخاصية (`text()`) والتغيير بـ `set` + اسمها (`setText()`).

## برنامج الترحيب بـ PySide6

ارسم نفس نموذج الدرس 13:

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblPrompt` | `اكتب اسمك:` |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblResult` | (فارغ) |

ثم انقر الزر مرتين واكتب:

<!-- test: {"form": {"Text": "برنامج الترحيب - Qt", "Width": 360, "Height": 200}, "controls": [["Label", "lblPrompt", {"Text": "اكتب اسمك:", "Left": 20, "Top": 20, "Width": 100}], ["TextBox", "txtName", {"Text": "", "Left": 120, "Top": 18, "Width": 200}], ["Button", "btnHello", {"Text": "رحّب بي", "Left": 120, "Top": 52, "Width": 100, "Height": 28}], ["Label", "lblResult", {"Text": "", "Left": 20, "Top": 100, "Width": 300}]], "set": {"txtName": "يوسف"}, "click": ["btnHello"], "expect": {"lblResult": "أهلًا يا يوسف!"}} -->
```python qt form run
import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        self.lblResult.setText("اكتب اسمك ثم اضغط الزر")

    def btnHello_Click(self):
        name = self.txtName.text().strip()
        if name:
            self.lblResult.setText(f"أهلًا يا {name}!")
        else:
            self.lblResult.setText("من فضلك اكتب اسمك أولًا")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

قارنه بنسخة Tkinter: نفس الفكرة تمامًا، والفرق فقط في أسماء الدوال (`text()` بدل `get()`، و`setText()` بدل `config(text=...)`) وفي آخر الملف:

- `QApplication` هو **التطبيق** نفسه، ولا بد أن يوجد مرة واحدة قبل أي نافذة.
- `form.show()` تُظهر النافذة.
- `app.exec()` تبدأ حلقة الأحداث، و`sys.exit(...)` تنهي البرنامج بنفس رمز الخروج عند إغلاق النافذة.

## مربعات الرسائل في Qt: `QMessageBox`

<!-- test: {"form": {"Text": "تأكيد"}, "controls": [["Button", "btnExit", {"Text": "خروج", "Left": 20, "Top": 20, "Width": 120, "Height": 30}], ["Label", "lblStatus", {"Text": "", "Left": 20, "Top": 70, "Width": 300}]], "click": ["btnExit"], "msgbox": ["هل تريد الخروج فعلًا؟"], "expect": {"lblStatus": "وداعًا!"}} -->
```python qt form run
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnExit_Click(self):
        answer = QMessageBox.question(self, "تأكيد", "هل تريد الخروج فعلًا؟")
        if answer == QMessageBox.StandardButton.Yes:
            self.lblStatus.setText("وداعًا!")
            # self.close()   # أزل علامة التعليق لتُغلق النافذة فعلًا
        else:
            self.lblStatus.setText("مرحبًا بعودتك")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

| الدالة | ماذا تعرض |
|---|---|
| `QMessageBox.information(self, عنوان, رسالة)` | معلومة |
| `QMessageBox.warning(...)` | تحذير |
| `QMessageBox.critical(...)` | خطأ |
| `QMessageBox.question(...)` | سؤال، وترجع الزر الذي ضُغط |

ولقراءة نص من المستخدم في نافذة صغيرة: `text, ok = QInputDialog.getText(self, "عنوان", "السؤال")` (من `PySide6.QtWidgets`).

## مثال: محوّل العملات

| الأداة | Name | Text / Items |
|---|---|---|
| `TextBox` | `txtAmount` | `100` |
| `ComboBox` | `cboFrom` | Items: `USD;EUR;EGP` |
| `ComboBox` | `cboTo` | Items: `USD;EUR;EGP` |
| `Button` | `btnConvert` | `حوّل` |
| `Label` | `lblResult` | (فارغ) |
| `ListBox` | `lstHistory` | |

<!-- test: {"form": {"Text": "محوّل العملات", "Width": 380, "Height": 330}, "controls": [["TextBox", "txtAmount", {"Text": "100", "Left": 16, "Top": 16, "Width": 110}], ["ComboBox", "cboFrom", {"Items": "USD;EUR;EGP", "Left": 136, "Top": 16, "Width": 90}], ["ComboBox", "cboTo", {"Items": "USD;EUR;EGP", "Left": 236, "Top": 16, "Width": 90}], ["Button", "btnConvert", {"Text": "حوّل", "Left": 16, "Top": 52, "Width": 100, "Height": 28}], ["Label", "lblResult", {"Text": "", "Left": 130, "Top": 56, "Width": 220}], ["ListBox", "lstHistory", {"Left": 16, "Top": 96, "Width": 340, "Height": 170}]], "steps": [["select", "cboFrom", 0], ["select", "cboTo", 2], ["click", "btnConvert"], ["set", "txtAmount", "abc"], ["click", "btnConvert"]], "expect": {"lblResult": "أدخل مبلغًا صحيحًا", "lstHistory": "100 USD = 5,000.00 EGP"}} -->
```python qt form run
import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401

# كم جنيهًا مصريًا تساوي الوحدة من كل عملة (أرقام للتجربة فقط)
RATES = {"USD": 50.0, "EUR": 54.0, "EGP": 1.0}


class Form1(Form1Designer):

    def Form1_Load(self):
        self.cboTo.setCurrentIndex(2)

    def btnConvert_Click(self):
        try:
            amount = float(self.txtAmount.text())
        except ValueError:
            self.lblResult.setText("أدخل مبلغًا صحيحًا")
            return
        src = self.cboFrom.currentText()
        dst = self.cboTo.currentText()
        result = amount * RATES[src] / RATES[dst]
        line = f"{amount:g} {src} = {result:,.2f} {dst}"
        self.lblResult.setText(line)
        self.lstHistory.addItem(line)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

## العربية والاتجاه من اليمين لليسار في Qt

Qt تدعم العربية بامتياز. لكي تظهر نافذتك كلها من اليمين لليسار (العناوين، ومحاذاة النصوص، وأشرطة التمرير)، أضف سطرًا واحدًا قبل إنشاء النافذة:

```python
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
```

## التوثيق والمساعدة

- **تلميحات الكود:** اكتب `self.txtName.` في المحرر لتظهر لك كل دوال `QLineEdit`.
- توثيق Qt for Python الرسمي: `https://doc.qt.io/qtforpython-6/`.

## أخطاء شائعة

- **`ModuleNotFoundError: No module named 'PySide6'`**: المكتبة غير مثبتة في Python المشروع؛ ثبّتها من **Manage Packages**.
- **خلط أسلوب Tkinter بأسلوب Qt:** `self.txtName.get()` لا توجد في Qt (استخدم `text()`)، و`setText` لا توجد في Tkinter.
- **إنشاء النافذة قبل `QApplication`**: يحدث خطأ `QWidget: Must construct a QApplication before a QWidget`.

## تمارين

### التمرين 1

بـ PySide6: نموذج فيه `TextBox` اسمه `txtWord` وزر `btnUpper` و`Label` اسمه `lblOut`. عند الضغط اعرض الكلمة بأحرف كبيرة.

<!-- test: {"controls": [["TextBox", "txtWord", {"Text": ""}], ["Button", "btnUpper", {"Text": "كبّر"}], ["Label", "lblOut", {}]], "set": {"txtWord": "python"}, "click": ["btnUpper"], "expect": {"lblOut": "PYTHON"}} -->
```python qt form exercise
import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnUpper_Click(self):
        pass


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

<!-- test: {"controls": [["TextBox", "txtWord", {"Text": ""}], ["Button", "btnUpper", {"Text": "كبّر"}], ["Label", "lblOut", {}]], "set": {"txtWord": "python"}, "click": ["btnUpper"], "expect": {"lblOut": "PYTHON"}} -->
```python qt form solution
import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnUpper_Click(self):
        self.lblOut.setText(self.txtWord.text().upper())


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

### التمرين 2

بـ PySide6: `ListBox` اسمه `lstColors` فيه (من `Form1_Load`) الألوان `أحمر` و`أخضر` و`أزرق`، و`Label` اسمه `lblChoice`. عند اختيار لون اعرض `اخترت: أخضر` مثلًا. (الحدث `lstColors_SelectedIndexChanged`، والعنصر الحالي `self.lstColors.currentItem().text()`.)

<!-- test: {"controls": [["ListBox", "lstColors", {}], ["Label", "lblChoice", {}]], "select": {"lstColors": 1}, "expect": {"lblChoice": "اخترت: أخضر", "lstColors": "أحمر|أخضر|أزرق"}} -->
```python qt form exercise
import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def Form1_Load(self):
        pass


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

<!-- test: {"controls": [["ListBox", "lstColors", {}], ["Label", "lblChoice", {}]], "select": {"lstColors": 1}, "expect": {"lblChoice": "اخترت: أخضر", "lstColors": "أحمر|أخضر|أزرق"}} -->
```python qt form solution
import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def Form1_Load(self):
        self.lstColors.addItems(["أحمر", "أخضر", "أزرق"])

    def lstColors_SelectedIndexChanged(self):
        item = self.lstColors.currentItem()
        if item is not None:
            self.lblChoice.setText("اخترت: " + item.text())


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
```

## اختبر نفسك

```quiz
{"question": "كيف تقرأ النص من QLineEdit اسمه txtName؟", "choices": ["self.txtName.get()", "self.txtName.text()", "self.txtName.Text", "self.txtName.value()"], "answer": 1, "explanation": "في Qt القراءة بـ text() والتغيير بـ setText()."}
```

```quiz
{"question": "ما الذي يبدأ حلقة الأحداث في برنامج PySide6؟", "choices": ["form.show()", "app.exec()", "QApplication()", "Form1_Load"], "answer": 1, "explanation": "show تُظهر النافذة فقط، أما app.exec() فتبدأ حلقة الأحداث."}
```

```quiz
{"question": "ما الذي يتغير في مصمم النماذج عند الانتقال من Tkinter إلى PySide6؟", "choices": ["تحتاج مصممًا آخر", "لا شيء تقريبًا: نفس الأدوات، والكود المولَّد هو الذي يتغير", "لا يمكن استخدام الأزرار", "يجب كتابة كود التصميم يدويًا"], "answer": 1, "explanation": "المصمم واحد، والـ IDE تولّد Form1_designer.py بأدوات Qt بدل Tkinter."}
```

## الخلاصة

- مشروع Qt: **Python (PySide6 / Qt) > Windows Application**، ونفس المصمم ونفس أسماء الأحداث.
- القراءة `text()` / `isChecked()` / `currentText()` / `value()`، والتغيير بـ `setText()` وأخواتها.
- `QMessageBox` للرسائل، و`QApplication` + `app.exec()` لتشغيل البرنامج.
- Qt مثالية للعربية: `app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)`.
