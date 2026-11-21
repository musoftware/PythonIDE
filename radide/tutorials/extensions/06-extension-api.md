# الدرس 6: واجهة الإضافات: أوامر ونوافذ وشريط الحالة

**في هذا الدرس ستتعلم:**

- إضافة **كود** إلى إضافتك بالمفتاح `main` والدالة `activate(api)`.
- أهم ما في الكائن `api`: أمر في القائمة، ونافذة جانبية، ومعلومة في شريط الحالة، وإعدادات.
- لماذا يُزال كل ما أضفته تلقائيًا عند التعطيل، ودور `on_dispose`.
- قواعد الواجهة: الألوان من السمة، وأسماء الوصول.
- فصل **المنطق** عن **الواجهة** لتختبره بسهولة.

## من سمة إلى أداة

في الدرس السابق صنعنا إضافة بلا كود. الآن نضيف ملف Python. في ملف الوصف نكتب `"main"`:

```text
{
  "id": "radide-samples.word-count",
  "name": "Word Count Tools",
  "version": "1.2.0",
  "engines": {"radide": ">=1.0"},
  "main": "extension.py"
}
```

وشكل المجلد:

```text
WordCountTools/
  radide-extension.json
  extension.py      <- فيه activate(api)
  counting.py       <- دوال الحساب (بلا واجهة)
```

هذه الإضافة موجودة كاملة في مجلد البيئة: `samples\Tests\Extensions\WordCountTools`.

## الدالة activate(api)

عندما تُفعَّل الإضافة، تستورد البيئة الملف `extension.py` وتستدعي `activate(api)`. هذا هو الملف الحقيقي للمثال (مختصرًا قليلًا):

```python
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel, QMessageBox

from .counting import count, describe


def activate(api):
    # 1) أمر في القائمة Tools > Word Count مع اختصار
    api.add_action("Tools/Word Count", "Count Words in Active File", lambda: show(api),
                   shortcut="Ctrl+Alt+W")

    # 2) معلومة في شريط الحالة، بلون من السمة الحالية
    label = QLabel("")
    api.theme.role(label, "muted")
    label.setAccessibleName("Word count of the active file")
    api.add_status_widget(label)

    # 3) مؤقت يحدّث العدد، ويُوقف عند التعطيل
    timer = QTimer()
    timer.timeout.connect(lambda: update(api, label))
    timer.start(1500)
    api.on_dispose(timer.stop)
    api.log("ready - Tools > Word Count")


def update(api, label):
    text = api.current_editor_text()
    label.setText("" if text is None else f"{count(text)['words']} words")


def show(api):
    text = api.current_editor_text()
    if text is None:
        QMessageBox.information(api.win, "Word Count", "Open a code file first.")
        return
    QMessageBox.information(api.win, "Word Count", describe(count(text)))
```

لاحظ السطر `from .counting import count, describe`: الإضافة تستطيع استيراد ملفاتها الأخرى **باستيراد نسبي** (بنقطة).

## أهم أعضاء الكائن api

| العضو | ماذا يفعل |
|---|---|
| `api.add_action(menu_path, text, callback, shortcut=None)` | أمر في قائمة، مثل `"Tools/My Tools"`، ويظهر أيضًا في لوحة الأوامر |
| `api.add_toolbar_action(text, callback)` | زر في شريط الأدوات |
| `api.add_dock(title, widget, area="right")` | نافذة جانبية (`left` أو `right` أو `bottom` أو `top`) |
| `api.add_status_widget(widget)` | عنصر في شريط الحالة |
| `api.current_editor_text()` | نص المحرر الحالي، أو `None` |
| `api.log(text)` / `api.status(text)` | سطر في **Output** / رسالة في شريط الحالة |
| `api.settings` | إعدادات خاصة بإضافتك تبقى بين الجلسات |
| `api.theme` | ألوان السمة الحالية: `api.theme.color("text")` و`api.theme.role(widget, "muted")` |
| `api.on_theme_changed(fn)` | استدعاء `fn` بعد كل تغيير للسمة |
| `api.on_dispose(fn)` | استدعاء `fn` عند التعطيل أو إلغاء التثبيت |
| `api.win` | النافذة الرئيسية للبيئة |

## التنظيف التلقائي

كل ما تضيفه **عن طريق `api`** (أوامر، وأزرار، ونوافذ، وعناصر شريط الحالة، واتصالات الإشارات) **يُزال تلقائيًا** عند الضغط على **Disable** أو **Uninstall**، دون إعادة تشغيل البيئة. لكن الأشياء التي تعمل وحدها، مثل **مؤقت** أو **ملف مفتوح** أو **برنامج خارجي**، أوقفها بنفسك في `api.on_dispose(...)`، أو في دالة اختيارية اسمها `deactivate()`.

> **تشبيه:** `api` مثل **غرفة فندق**: كل ما استلمته من الفندق يُجمع عند خروجك. أما الماء الذي تركته مفتوحًا فأغلقه أنت قبل أن تخرج!

## قواعد الواجهة

- **لا تكتب ألوانًا ثابتة** مثل `"#000000"`، فستبدو سيئة في السمة الداكنة. استخدم `api.theme.color(...)` و`api.theme.role(...)`.
- أعطِ العناصر **أسماء وصول** (`setAccessibleName`) لمستخدمي قارئ الشاشة.
- إذا حدث خطأ داخل `activate`، يُسجَّل في نافذة **Tools > Extensions...** وفي **Output**، ويُزال ما كانت الإضافة قد أضافته، وتستمر البيئة في العمل.

## افصل المنطق عن الواجهة

الحساب نفسه موجود في `counting.py` **دون أي واجهة**، ولذلك يمكن تشغيله واختباره كبرنامج عادي:

```python run
import re


def count(text):
    return {"lines": len(text.splitlines()) if text else 0,
            "words": len(re.findall(r"\w+", text or "")),
            "chars": len(text or "")}


def describe(c):
    return f"{c['lines']} lines, {c['words']} words, {c['chars']} characters"


sample = "def hello():\n    print('مرحبا يا عالم')\n"
print(describe(count(sample)))
print(describe(count("")))
```

```text output
2 lines, 6 words, 40 characters
0 lines, 0 words, 0 characters
```

لاحظ أن `\w+` يعدّ الكلمات العربية أيضًا (`مرحبا` و`يا` و`عالم`)، لأن Python يفهم الحروف العربية في التعبيرات النمطية.

## التثبيت والتجربة

**الخطوة 1:** **Tools > Extensions... > Install from Folder...** واختر `samples\Tests\Extensions\WordCountTools`.

**الخطوة 2:** افتح ملف كود، وانظر إلى شريط الحالة (عدد الكلمات)، ثم **Tools > Word Count > Count Words in Active File**.

**الخطوة 3:** في نافذة الإضافات اضغط **Disable**: تختفي القائمة والمعلومة من شريط الحالة فورًا. ثم **Enable** لتعود.

## أخطاء شائعة

- **استيراد مطلق لملف الإضافة:** `from counting import count` قد يفشل. استخدم `from .counting import count`.
- **مؤقت لا يتوقف بعد التعطيل:** سجّل إيقافه بـ `api.on_dispose(timer.stop)`.
- **ألوان ثابتة:** تبدو جيدة في السمة الفاتحة فقط. استخدم `api.theme`.
- **إضافة أمر بـ QAction مباشرة بدل `api.add_action`:** لن يُزال عند التعطيل.

## تمارين

### تمرين 1: عدّ الأسطر غير الفارغة

أضف إلى `count` مفتاحًا جديدًا `"code_lines"` يعدّ الأسطر التي ليست فارغة (بعد حذف المسافات)، واطبعه للنص المعطى.

```python exercise
import re


def count(text):
    return {"lines": len(text.splitlines()) if text else 0,
            "words": len(re.findall(r"\w+", text or ""))}


sample = "x = 1\n\n\ny = 2\n"
print(count(sample))
```

```python solution
import re


def count(text):
    lines = text.splitlines() if text else []
    return {"lines": len(lines),
            "words": len(re.findall(r"\w+", text or "")),
            "code_lines": sum(1 for ln in lines if ln.strip())}


sample = "x = 1\n\n\ny = 2\n"
print(count(sample))
```

```text output
{'lines': 4, 'words': 4, 'code_lines': 2}
```

### تمرين 2 (عملي في البيئة)

انسخ مجلد `WordCountTools` إلى مكان آخر، وغيّر المعرّف إلى `yourname.word-count`، وأضف أمرًا ثانيًا في `activate` اسمه «Count Lines» يعرض عدد الأسطر فقط في `QMessageBox`. ثبّت المجلد وجرّب الأمر، ثم عطّل الإضافة وتأكد أن الأمرين اختفيا.

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تستدعيها البيئة عند تفعيل إضافة فيها كود؟", "choices": ["main()", "start()", "activate(api)", "run()"], "answer": 2, "explanation": "ملف main يحتوي activate(api)، وdeactivate() اختيارية."}
```

```quiz
{"question": "ماذا يحدث لأمر أضفته بـ api.add_action عند تعطيل الإضافة؟", "choices": ["يبقى حتى إعادة التشغيل", "يُزال تلقائيًا فورًا", "يتحول إلى زر", "يُحذف ملف الإضافة"], "answer": 1, "explanation": "كل ما يُضاف عن طريق api يُزال عند Disable أو Uninstall."}
```

```quiz
{"question": "كيف تضمن أن مؤقتًا في إضافتك يتوقف عند تعطيلها؟", "choices": ["لا داعي لذلك", "api.on_dispose(timer.stop)", "بحذف الملف يدويًا", "بإعادة تشغيل الجهاز"], "answer": 1, "explanation": "on_dispose يُستدعى عند التعطيل أو إلغاء التثبيت."}
```

## الخلاصة

- `"main": "extension.py"` + `def activate(api)` = إضافة فيها كود.
- `api.add_action` و`add_dock` و`add_status_widget` و`settings` و`theme` و`log`.
- ما يُضاف عبر `api` يُزال تلقائيًا، وما يعمل وحده أوقفه في `on_dispose`.
- افصل الحساب في ملف بلا واجهة لتختبره بسهولة.
