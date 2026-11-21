# الدرس 4: اللغات والقواعد اللغوية والمقتطفات

**في هذا الدرس ستتعلم:**

- ماذا يحدث عندما تثبّت إضافة VS Code تضيف **لغة**.
- معنى **القاعدة اللغوية** (Grammar) بأسلوب TextMate، وكيف تلوّن الكود.
- **المقتطفات** (Snippets): قوالب كود جاهزة تُكتب باختصار.
- الإضافات التي فيها كود، و«مضيف الإضافات».

## ماذا تضيف إضافة «لغة»؟

إضافة اللغة في VS Code تحتوي غالبًا على ثلاثة أشياء، والبيئة تفهمها كلها:

| المساهمة | المعنى | ماذا تفعل البيئة بها |
|---|---|---|
| `languages` | اسم اللغة وامتدادات ملفاتها، والتعليقات والأقواس | تفتح الملف باللغة الصحيحة، وتغلق الأقواس تلقائيًا |
| `grammars` | القاعدة اللغوية (TextMate) | تلوّن الكود بدقة كما في VS Code |
| `snippets` | المقتطفات | تظهر في قائمة الإكمال أثناء الكتابة |

مثال: بعد تثبيت إضافة للغة **TOML**، أي ملف `.toml` يُفتح ملوّنًا، وتعمل التعليقات بـ `Ctrl+/`، وتظهر مقتطفاتها.

## القاعدة اللغوية: كيف «يفهم» المحرر الألوان؟

المحرر لا يفهم البرنامج كما يفهمه المترجم. هو فقط يقسّم النص إلى **قطع** (tokens) بالتعبيرات النمطية، ويعطي كل قطعة **نطاقًا** (scope) مثل `comment.line` أو `string.quoted` أو `keyword.control`. ثم تعطي **السمة** لكل نطاق لونًا (كما رأينا في الدرس السابق).

> **تشبيه:** القاعدة اللغوية مثل **قلم التظليل** في يد طالب: يظلل التعريفات بالأصفر والأمثلة بالأخضر، دون أن يفهم الدرس كله. السمة هي **ألوان الأقلام** نفسها.

هذا مثال مبسّط جدًا لنفس الفكرة: قواعد بالتعبيرات النمطية، لكل قاعدة نطاق، تُطبَّق على سطر من لغة صغيرة:

```python run
import re

rules = [
    ("comment.line", r"#.*"),
    ("string.quoted", r'"[^"]*"'),
    ("keyword.control", r"\b(?:if|else|print)\b"),
    ("constant.numeric", r"\b\d+\b"),
]

line = 'if x > 10 print "كبير" # تعليق'
pattern = "|".join(f"(?P<g{i}>{rx})" for i, (_s, rx) in enumerate(rules))

for m in re.finditer(pattern, line):
    scope = rules[int(m.lastgroup[1:])][0]
    print(f"{scope:18} {m.group()}")
```

```text output
keyword.control    if
constant.numeric   10
keyword.control    print
string.quoted      "كبير"
comment.line       # تعليق
```

القواعد الحقيقية لـ TextMate أغنى بكثير: فيها **بداية ونهاية** (begin/end) لكتل مثل النصوص متعددة الأسطر، ولغات **مضمّنة** (مثل CSS داخل HTML). البيئة تستخدم المكتبة نفسها التي يستخدمها VS Code (vscode-textmate)، فتطابق الألوان ما تراه هناك.

## المقتطفات (Snippets)

المقتطف قالب له **بادئة** (prefix). تكتب البادئة في المحرر فتظهر في قائمة الإكمال، وعند اختيارها يُكتب القالب كاملًا والمؤشر في أول خانة تحتاج تعديلًا.

مقتطف VS Code يُكتب هكذا (ملف JSON في الإضافة):

```text
"For loop": {
  "prefix": "fori",
  "body": ["for ${1:i} in range(${2:10}):", "    ${0:pass}"],
  "description": "for loop with range"
}
```

- `${1:i}`: الخانة الأولى وقيمتها المبدئية `i`، تنتقل إليها أولًا، ثم `Tab` إلى `${2:10}`.
- `${0}`: مكان المؤشر في النهاية.

وللبيئة أيضًا مقتطفاتها الخاصة: **Edit > Insert Snippet...** و**Tools > Code Snippets Manager...**.

هذا مثال يملأ قالب مقتطف بقيمه المبدئية، كما يظهر عند أول إدراج:

```python run
import re

body = ["for ${1:i} in range(${2:10}):", "    ${0:pass}"]

def expand(lines):
    text = "\n".join(lines)
    return re.sub(r"\$\{\d+:([^}]*)\}", r"\1", text)

print(expand(body))
```

```text output
for i in range(10):
    pass
```

## الإضافات التي فيها كود

بعض إضافات VS Code فيها كود JavaScript (أوامر، وخوادم لغات، ومصححات). هذه تعمل في **مضيف الإضافات** (Extension Host)، وهو برنامج Node.js منفصل تشغّله البيئة. لذلك:

- تحتاج **Node.js** مثبتًا.
- رسائل هذه الإضافات تظهر في **View > Extension Output**.
- أوامرها تظهر في لوحة الأوامر (`Ctrl+Shift+P`).
- بعض المصححات تعمل من **Debug > Debug with Extension Debugger**.
- بعد تحديث إضافة فيها كود، اضغط **Reload** في شريط **Restart required**.

## أخطاء شائعة

- **الملف لا يتلون بعد التثبيت:** أغلق الملف وافتحه من جديد، أو تأكد من أن امتداده ضمن امتدادات اللغة في صفحة **Details**.
- **مقتطفات لا تظهر:** المقتطفات مرتبطة بلغة. تأكد أن لغة الملف صحيحة (**Edit > Language Mode...**).
- **إضافة فيها كود لا تعمل:** ثبّت Node.js، وانظر في **Extension Output**.

## تمارين

### تمرين 1: قاعدة جديدة

أضف إلى مثال التلوين قاعدة للنطاق `keyword.operator` تلتقط العلامات `>` و`<` و`=`، ثم شغّل البرنامج على السطر نفسه. ضع القاعدة الجديدة **آخر** القائمة.

```python exercise
import re

rules = [
    ("comment.line", r"#.*"),
    ("string.quoted", r'"[^"]*"'),
    ("keyword.control", r"\b(?:if|else|print)\b"),
    ("constant.numeric", r"\b\d+\b"),
]
line = 'if x > 10 print "كبير" # تعليق'
pattern = "|".join(f"(?P<g{i}>{rx})" for i, (_s, rx) in enumerate(rules))
for m in re.finditer(pattern, line):
    print(f"{rules[int(m.lastgroup[1:])][0]:18} {m.group()}")
```

```python solution
import re

rules = [
    ("comment.line", r"#.*"),
    ("string.quoted", r'"[^"]*"'),
    ("keyword.control", r"\b(?:if|else|print)\b"),
    ("constant.numeric", r"\b\d+\b"),
    ("keyword.operator", r"[<>=]"),
]
line = 'if x > 10 print "كبير" # تعليق'
pattern = "|".join(f"(?P<g{i}>{rx})" for i, (_s, rx) in enumerate(rules))
for m in re.finditer(pattern, line):
    print(f"{rules[int(m.lastgroup[1:])][0]:18} {m.group()}")
```

```text output
keyword.control    if
keyword.operator   >
constant.numeric   10
keyword.control    print
string.quoted      "كبير"
comment.line       # تعليق
```

### تمرين 2: مقتطف دالة

اكتب جسم مقتطف لدالة Python بالشكل `def ${1:name}(${2:args}):` ثم سطر `    ${0:pass}`، واطبع نتيجة `expand` له.

```python exercise
import re

def expand(lines):
    return re.sub(r"\$\{\d+:([^}]*)\}", r"\1", "\n".join(lines))

body = []  # اكتب أسطر المقتطف
print(expand(body))
```

```python solution
import re

def expand(lines):
    return re.sub(r"\$\{\d+:([^}]*)\}", r"\1", "\n".join(lines))

body = ["def ${1:name}(${2:args}):", "    ${0:pass}"]
print(expand(body))
```

```text output
def name(args):
    pass
```

## اختبر نفسك

```quiz
{"question": "ما وظيفة القاعدة اللغوية (Grammar)؟", "choices": ["ترجمة البرنامج", "تقسيم الكود إلى قطع لها نطاقات تلوّنها السمة", "تشغيل البرنامج", "حفظ الملفات"], "answer": 1, "explanation": "القاعدة تعطي كل قطعة نطاقًا، والسمة تعطي النطاق لونًا."}
```

```quiz
{"question": "في المقتطف، ماذا يعني ${1:i}؟", "choices": ["تعليق", "الخانة الأولى التي ينتقل إليها المؤشر وقيمتها المبدئية i", "خطأ في الصياغة", "رقم السطر"], "answer": 1, "explanation": "الخانات المرقمة يتنقل بينها المؤشر بـ Tab."}
```

```quiz
{"question": "ماذا تحتاج إضافات VS Code التي فيها كود JavaScript؟", "choices": ["لا شيء", "Node.js لتشغيل مضيف الإضافات", "Python 2", "اتصالًا دائمًا بالإنترنت"], "answer": 1, "explanation": "مضيف الإضافات برنامج Node.js منفصل."}
```

## الخلاصة

- إضافة اللغة = `languages` + `grammars` + `snippets`.
- القاعدة اللغوية تقسّم الكود إلى قطع بنطاقات، والسمة تلوّن النطاقات.
- المقتطفات قوالب ببادئة وخانات `${1:...}`.
- الإضافات التي فيها كود تعمل في مضيف Node.js، ورسائلها في **Extension Output**.
