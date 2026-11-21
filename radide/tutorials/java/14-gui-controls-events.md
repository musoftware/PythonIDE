# الدرس 14: الأدوات والأحداث: القوائم والاختيارات والمؤقت

في الدرس السابق استخدمنا مربع النص والزر والعنوان. اليوم نتعرف على أدوات أكثر: **القائمة** `ListBox`، و**القائمة المنسدلة** `ComboBox`، و**مربع الاختيار** `CheckBox`، و**زر الخيار** `RadioButton`، و**المؤقت** `Timer`، مع الرسائل ومربعات الإدخال.

## القائمة `ListBox`

| الكود | معناه |
|---|---|
| `lstNames.addItem("علي")` | يضيف عنصرًا في النهاية |
| `lstNames.removeItem(2)` | يحذف العنصر رقم 2 (الترقيم من 0) |
| `lstNames.clear()` | يحذف كل العناصر |
| `lstNames.getListCount()` | عدد العناصر |
| `lstNames.getListIndex()` | رقم العنصر المختار (`-1` إذا لا يوجد اختيار) |
| `lstNames.getText()` | نص العنصر المختار |
| `lstNames.list(i)` | نص العنصر رقم `i` |

ارسم: `TextBox` باسم `txtItem`، و`Button` باسم `btnAdd`، و`Button` باسم `btnRemove`، و`ListBox` باسم `lstItems`، و`Label` باسم `lblCount`.

<!-- test: {"items": {"lstItems": ["خبز"]}, "set": {"txtItem.Text": "حليب"}, "events": ["btnAdd Click", "btnAdd Click"], "msgbox": ["اكتب اسم العنصر أولًا"], "expect": {"lstItems.ListCount": "2", "lblCount.Text": "عدد العناصر: 2", "txtItem.Text": ""}} -->
```java form run
public class Form1 extends Form1Designer {
    static void updateCount() {
        lblCount.setText("عدد العناصر: " + lstItems.getListCount());
    }

    static void btnAdd_Click(RadEvent e) {
        String item = txtItem.getText().trim();
        if (item.isEmpty()) {
            msgbox("اكتب اسم العنصر أولًا");
            return;
        }
        lstItems.addItem(item);
        txtItem.setText("");
        txtItem.setFocus();
        updateCount();
    }

    static void btnRemove_Click(RadEvent e) {
        int i = lstItems.getListIndex();
        if (i < 0) {
            msgbox("اختر عنصرًا من القائمة أولًا");
            return;
        }
        lstItems.removeItem(i);
        updateCount();
    }
}
```

في الاختبار: القائمة فيها «خبز»، ونكتب «حليب» ونضغط «إضافة» مرتين. المرة الأولى تضيف «حليب» وتمسح المربع، والثانية تجد المربع فارغًا فتظهر الرسالة.

### حدث تغيير الاختيار

الحدث الافتراضي للقائمة هو `SelectedIndexChanged`: يعمل كلما اختار المستخدم عنصرًا آخر.

<!-- test: {"items": {"lstCities": ["Cairo", "Giza", "Aswan"]}, "set": {"lstCities.ListIndex": "2"}, "events": ["lstCities SelectedIndexChanged"], "expect": {"lblChoice.Text": "اخترت: Aswan (رقم 2)"}} -->
```java form run
public class Form1 extends Form1Designer {
    static void Form1_Load(RadEvent e) {
        lstCities.addItem("Cairo");
        lstCities.addItem("Giza");
        lstCities.addItem("Aswan");
    }

    static void lstCities_SelectedIndexChanged(RadEvent e) {
        lblChoice.setText("اخترت: " + lstCities.getText() + " (رقم " + lstCities.getListIndex() + ")");
    }
}
```

## القائمة المنسدلة `ComboBox`

تعمل مثل `ListBox` (نفس `addItem` و`getListIndex` و`getText`)، لكنها تأخذ مساحة سطر واحد وتنسدل عند الضغط. ويمكن ملء عناصرها من المصمم: خاصية **Items** في نافذة الخصائص، عنصر في كل سطر.

<!-- test: {"set": {"cboSize.Text": "كبير", "txtQty.Text": "3"}, "events": ["btnPrice Click"], "expect": {"lblPrice.Text": "السعر: 135 جنيه"}} -->
```java form run
public class Form1 extends Form1Designer {
    static void Form1_Load(RadEvent e) {
        cboSize.addItem("صغير");
        cboSize.addItem("وسط");
        cboSize.addItem("كبير");
    }

    static void btnPrice_Click(RadEvent e) {
        int unit = switch (cboSize.getText()) {
            case "صغير" -> 25;
            case "وسط" -> 35;
            case "كبير" -> 45;
            default -> 0;
        };
        if (unit == 0) {
            lblPrice.setText("اختر الحجم");
            return;
        }
        int qty = toInt(txtQty.getText());
        lblPrice.setText("السعر: " + unit * qty + " جنيه");
    }
}
```

لاحظ أن `switch` في Java يعمل مع النصوص أيضًا (ويقارن بالمحتوى كأنه `equals`).

## مربع الاختيار وزر الخيار

- `CheckBox`: اختيار مستقل (نعم / لا). قيمته في `getValue()`: `"1"` إذا كان مُعلّمًا و`"0"` إذا لم يكن.
- `RadioButton`: مجموعة خيارات لا يُختار منها إلا واحد. قيمته `getValue()` تكون `"True"` للمختار.
- الدالة `toBool(text)` تحول `"1"` و`"True"` إلى `true`.

ارسم `TextBox` باسم `txtText`، و`CheckBox` باسم `chkUpper` (Text: أحرف كبيرة)، و`CheckBox` باسم `chkTrim` (Text: حذف المسافات)، و`RadioButton` باسم `optBrackets` (Text: أقواس)، و`Button` باسم `btnApply`، و`Label` باسم `lblOut`.

<!-- test: {"set": {"txtText.Text": "  hello  ", "chkUpper.Value": "1", "chkTrim.Value": "1", "optBrackets.Value": "True"}, "events": ["btnApply Click"], "expect": {"lblOut.Text": "[HELLO]"}} -->
```java form run
public class Form1 extends Form1Designer {
    static void btnApply_Click(RadEvent e) {
        String s = txtText.getText();
        if (toBool(chkTrim.getValue())) {
            s = s.trim();
        }
        if (toBool(chkUpper.getValue())) {
            s = s.toUpperCase();
        }
        if (toBool(optBrackets.getValue())) {
            s = "[" + s + "]";
        }
        lblOut.setText(s);
    }
}
```

## المؤقت `Timer`

المؤقت أداة **غير مرئية**: تظهر أسفل المصمم وليس على النافذة. كل فترة (خاصية `Interval` بالمللي ثانية، و1000 = ثانية واحدة) يطلق الحدث `Tick` ما دامت خاصيته `Enabled` صحيحة.

ارسم `Timer` باسم `tmrClock` (Interval = 1000، Enabled = False)، و`Label` باسم `lblTime`، و`Button` باسم `btnStart`، و`Button` باسم `btnStop`.

<!-- test: {"events": ["btnStart Click", "tmrClock Tick", "tmrClock Tick", "tmrClock Tick"], "expect": {"lblTime.Text": "00:03", "tmrClock.Enabled": "True"}} -->
```java form run
public class Form1 extends Form1Designer {
    static int seconds = 0;

    static void btnStart_Click(RadEvent e) {
        seconds = 0;
        lblTime.setText("00:00");
        tmrClock.setEnabled(true);
    }

    static void btnStop_Click(RadEvent e) {
        tmrClock.setEnabled(false);
        msgbox("توقفت ساعة الإيقاف عند " + lblTime.getText());
    }

    static void tmrClock_Tick(RadEvent e) {
        seconds++;
        lblTime.setText(String.format("%02d:%02d", seconds / 60, seconds % 60));
    }
}
```

`String.format("%02d", 3)` يطبع العدد الصحيح في خانتين على الأقل مع صفر في البداية (`03`).

## الرسائل ومربعات الإدخال

```java
msgbox("تم الحفظ بنجاح");              // رسالة
String name = input("ما اسمك؟");        // سؤال يرجع النص (فارغ إذا ضغط إلغاء)
```

<!-- test: {"input": ["Hana"], "events": ["btnAsk Click"], "msgbox": ["مرحبًا Hana، اسمك فيه 4 حروف"], "expect": {"lblName.Text": "Hana"}} -->
```java form run
public class Form1 extends Form1Designer {
    static void btnAsk_Click(RadEvent e) {
        String name = input("ما اسمك؟");
        if (name == null || name.isBlank()) {
            return;
        }
        lblName.setText(name);
        msgbox("مرحبًا " + name + "، اسمك فيه " + name.length() + " حروف");
    }
}
```

## أحداث أخرى مفيدة

| الحدث | متى يعمل |
|---|---|
| `Form1_Load` | عند ظهور النموذج |
| `txtX_TextChanged` | كلما تغير النص في مربع النص |
| `chkX_CheckedChanged` | عند تعليم مربع الاختيار أو إلغائه |
| `lstX_DoubleClick` | نقر مزدوج على القائمة |
| `picX_MouseMove` | حركة الفأرة (`e.x` و`e.y`) |
| `Form1_KeyDown` | ضغط مفتاح (`e.keyCode`) |

لترى كل أحداث أداة: اخترها في المصمم، ثم انقر أيقونة **الأحداث** (البرق) في نافذة Properties، وانقر مرتين على الحدث لإنشاء دالته.

## أخطاء شائعة

- **قراءة `getListIndex()` دون فحص `-1`:** إذا لم يختر المستخدم شيئًا ثم استدعيت `removeItem(-1)` فلن يحدث ما تريد. افحص دائمًا `if (i < 0)`.
- **نسيان تفعيل المؤقت:** المؤقت لا يعمل إلا إذا كان `setEnabled(true)`، والفترة `Interval` أكبر من صفر.
- **مقارنة `chkX.getValue().equals("True")`:** قيمة مربع الاختيار `"1"` أو `"0"`، فاستخدم `toBool(...)` التي تقبل الصيغتين.

## تمارين

### التمرين 1

قائمة أرقام: مربع نص `txtNumber`، وزر `btnAdd` يضيف الرقم إلى `lstNumbers`، وزر `btnSum` يكتب مجموع كل الأرقام في `lblSum` بالشكل `المجموع = 60.0`. استخدم `lstNumbers.list(i)` و`lstNumbers.getListCount()`.

<!-- test: {"items": {"lstNumbers": ["10", "20", "30"]}, "events": ["btnSum Click"], "expect": {"lblSum.Text": "المجموع = 60.0"}} -->
```java form exercise
public class Form1 extends Form1Designer {
    static void btnAdd_Click(RadEvent e) {
    }

    static void btnSum_Click(RadEvent e) {
    }
}
```

<!-- test: {"items": {"lstNumbers": ["10", "20", "30"]}, "events": ["btnSum Click"], "expect": {"lblSum.Text": "المجموع = 60.0"}} -->
```java form solution
public class Form1 extends Form1Designer {
    static void btnAdd_Click(RadEvent e) {
        lstNumbers.addItem(txtNumber.getText());
        txtNumber.setText("");
    }

    static void btnSum_Click(RadEvent e) {
        double sum = 0;
        for (int i = 0; i < lstNumbers.getListCount(); i++) {
            sum += toNumber(lstNumbers.list(i));
        }
        lblSum.setText("المجموع = " + sum);
    }
}
```

### التمرين 2

عدّ تنازلي: `Timer` باسم `tmrDown`، و`Label` باسم `lblLeft`، و`Button` باسم `btnGo`. عند الضغط يبدأ العد من 5، ومع كل `Tick` ينقص واحدًا، وعند الصفر يتوقف المؤقت ويكتب `انطلق!`.

<!-- test: {"events": ["btnGo Click", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick"], "expect": {"lblLeft.Text": "انطلق!", "tmrDown.Enabled": "False"}} -->
```java form exercise
public class Form1 extends Form1Designer {
    static int left;

    static void btnGo_Click(RadEvent e) {
    }

    static void tmrDown_Tick(RadEvent e) {
    }
}
```

<!-- test: {"events": ["btnGo Click", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick"], "expect": {"lblLeft.Text": "انطلق!", "tmrDown.Enabled": "False"}} -->
```java form solution
public class Form1 extends Form1Designer {
    static int left;

    static void btnGo_Click(RadEvent e) {
        left = 5;
        lblLeft.setText(left);
        tmrDown.setEnabled(true);
    }

    static void tmrDown_Tick(RadEvent e) {
        left--;
        if (left <= 0) {
            tmrDown.setEnabled(false);
            lblLeft.setText("انطلق!");
        } else {
            lblLeft.setText(left);
        }
    }
}
```

## اختبر نفسك

```quiz
{"question": "ماذا يعني أن lstNames.getListIndex() تساوي -1؟", "choices": ["القائمة فيها عنصر واحد", "لا يوجد عنصر مختار", "آخر عنصر مختار", "القائمة ممتلئة"], "answer": 1, "explanation": "‎-1 تعني أن المستخدم لم يختر أي عنصر."}
```

```quiz
{"question": "أي حدث يطلقه المؤقت Timer كل فترة؟", "choices": ["Click", "Load", "Tick", "Change"], "answer": 2, "explanation": "المؤقت يطلق Tick كل Interval مللي ثانية ما دام Enabled صحيحًا."}
```

```quiz
{"question": "كيف تعرف أن مربع الاختيار chkAgree مُعلّم؟", "choices": ["chkAgree.getText().equals(\"True\")", "toBool(chkAgree.getValue())", "chkAgree == true", "chkAgree.isEnabled()"], "answer": 1, "explanation": "قيمة مربع الاختيار في Value وتكون \"1\" أو \"0\"، وtoBool تحولها إلى true أو false."}
```

## الخلاصة

- `ListBox` و`ComboBox`: `addItem` و`removeItem` و`clear` و`getListCount` و`getListIndex` و`getText` و`list(i)`.
- `CheckBox` و`RadioButton`: `getValue()` مع `toBool(...)`.
- `Timer`: `Interval` و`setEnabled` والحدث `Tick`.
- `msgbox` و`input` للتواصل مع المستخدم، ونافذة Properties تعرض كل الأحداث.
