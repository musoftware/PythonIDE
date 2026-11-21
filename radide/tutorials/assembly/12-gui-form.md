# الدرس 12: نموذج رسومي بلغة التجميع عبر GUI Bridge

**في هذا الدرس ستتعلم:**

- إنشاء مشروع **Assembly Windows Forms** وتصميم نافذة بالسحب والإفلات.
- كتابة **معالجات الأحداث** بلغة التجميع: `handler btnHello_Click` ... `endhandler`.
- الحديث مع الأدوات بماكرو `radgui.inc`: `rad_set` و`rad_get_int` و`rad_set_int` و`rad_msgbox` و`rad_call`.
- آلة حاسبة صغيرة وسجل أحداث في قائمة.

## كيف يعمل GUI Bridge؟

بناء نافذة ويندوز بلغة التجميع من الصفر (تسجيل صنف نافذة، وحلقة رسائل، وإجراء نافذة...) يحتاج مئات الأسطر. في RAD IDE يقسَّم العمل:

- **الـ IDE ترسم النموذج** الذي صممته في المصمم (مثل Visual Basic تمامًا).
- **برنامجك بلغة التجميع** يستقبل الأحداث (ضغطة زر، تغيّر نص...) ويغيّر الأدوات بأوامر قصيرة.
- بينهما مكتبة صغيرة بلغة C (`radgui.c` و`radasm.c`) تُربط مع برنامجك، وملف ماكرو `radgui.inc` يجعل استدعاءها سطرًا واحدًا.

> **تشبيه:** المصمم هو مهندس الديكور الذي يجهز الغرفة، وأنت الكهربائي الذي يقرر ماذا يحدث عند الضغط على كل مفتاح.

## إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد).
2. اختر **Assembly** ثم قالب **Assembly Windows Forms (NASM + GUI Bridge)**.
3. سمّه `AsmForms` واضغط **OK**.

يفتح المصمم ومعه `Form1`. اسحب من **Toolbox** (صندوق الأدوات) زرًّا (**Button**) وعنوانًا (**Label**)، وغيّر من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| Button | `btnHello` | `Say hello` |
| Label | `lblOut` | (فارغ) |

اضغط على الزر **مرتين** في المصمم: تفتح الـ IDE ملف الكود `Form1.asm` وتضيف معالجًا فارغًا:

```asm
handler btnHello_Click

endhandler
```

## أول معالج

اكتب الكود التالي كاملًا في `Form1.asm`:

<!-- test: {"form": {"Text": "Hello Assembly", "controls": {"btnHello": {"Text": "Say hello"}}}} -->
```asm form run
%include "radgui.inc"
%include "Form1.inc"         ; يولّده المصمم: أسماء أدوات Form1

section .text

handler btnHello_Click
    rad_set lblOut, "Text", "Hello from x64 assembly!"
endhandler
```

اضغط `F5`: تبني الـ IDE البرنامج (NASM ثم gcc)، وتعرض النموذج. اضغط الزر فيظهر النص.

ماذا حدث؟

- `%include "radgui.inc"` يجلب الماكرو. و`%include "Form1.inc"` يعرّف الأسماء `lblOut` و`btnHello` نصوصًا يعرفها الجسر.
- `handler btnHello_Click` يبدأ دالة باسم **الأداة_الحدث** (مثل VB تمامًا)، ويجهز المكدس (الظل والمحاذاة) ويحفظ `rbx` و`rsi` و`rdi` و`r12`. و`endhandler` يعيدها ويرجع.
- `rad_set أداة, "خاصية", قيمة` يغيّر خاصية في النموذج.

## ماكرو `radgui.inc`

| الماكرو | العمل | الناتج |
|---|---|---|
| `rad_set obj, prop, text` | ضع نصًّا في خاصية | |
| `rad_get obj, prop` | اقرأ خاصية كنص | `rax` = عنوان النص |
| `rad_set_int obj, prop, n` | ضع عددًا (مسجل أو رقم أو `[mem]`) | |
| `rad_get_int obj, prop` | اقرأ خاصية كعدد | `rax` = العدد |
| `rad_call obj, method, args` | استدعِ طريقة (`AddItem` و`Clear` ...) | `rax` = نص |
| `rad_msgbox text` | نافذة رسالة | |
| `rad_input prompt` | اسأل المستخدم | `rax` = النص المكتوب |
| `rad_str_int n` | عدد ← نص | `rax` = عنوان النص |
| `rad_end` | أغلق البرنامج | |

قواعد مهمة:

- كل ماكرو يستدعي دالة، فقد يغيّر `rax` و`rcx` و`rdx` و`r8`-`r11`. احفظ ما تحتاجه في `rbx` أو `rsi` أو `rdi` أو `r12` (المعالج يحفظها لك).
- المعاملات تُحمَّل بالترتيب في `rcx` ثم `rdx` ثم `r8`، فلا تمرر `rcx` أو `rdx` أو `r8` معاملًا ثانيًا أو ثالثًا؛ مرر `rax` أو `rbx` بدلًا منها.

## آلة حاسبة

نموذج فيه مربعا نص `txtA` و`txtB`، وزران `btnAdd` و`btnMul`، وعنوان `lblResult`:

<!-- test: {"form": {"Text": "Calculator", "controls": {"btnAdd": {"Text": "A + B"}, "btnMul": {"Text": "A x B"}, "txtA": {"Text": "6"}, "txtB": {"Text": "7"}}}} -->
```asm form run
%include "radgui.inc"
%include "Form1.inc"

section .text

handler btnAdd_Click
    rad_get_int txtA, "Text"     ; rax = A
    mov rbx, rax                 ; rbx يبقى بعد الماكرو التالي
    rad_get_int txtB, "Text"     ; rax = B
    add rbx, rax
    rad_set_int lblResult, "Text", rbx
endhandler

handler btnMul_Click
    rad_get_int txtA, "Text"
    mov rbx, rax
    rad_get_int txtB, "Text"
    imul rbx, rax
    rad_set_int lblResult, "Text", rbx
endhandler
```

جرّب كتابة أعداد سالبة أو كبيرة: كل الحساب يتم بتعليمات `add` و`imul` التي تعرفها.

## الحالة بين الأحداث وقائمة سجل

المتغيرات في `.data` تبقى بين ضغطة وأخرى. هنا عدّاد ضغطات، وكل ضغطة تضيف سطرًا إلى قائمة `lstLog`، وزر يمسح القائمة:

<!-- test: {"form": {"Text": "Click log", "controls": {"btnClick": {"Text": "Click me"}, "btnClear": {"Text": "Clear"}}}} -->
```asm form run
%include "radgui.inc"
%include "Form1.inc"

section .data
    clicks dq 0

section .text

handler Form1_Load
    rad_set lblCount, "Text", "No clicks yet"
endhandler

handler btnClick_Click
    inc qword [clicks]
    rad_set_int lblCount, "Text", [clicks]
    rad_str_int [clicks]                 ; rax = العدد كنص
    rad_call lstLog, "AddItem", rax
endhandler

handler btnClear_Click
    mov qword [clicks], 0
    rad_call lstLog, "Clear", ""
    rad_set lblCount, "Text", "Cleared"
endhandler
```

- `Form1_Load` يعمل مرة واحدة عند ظهور النموذج.
- `rad_call lstLog, "AddItem", rax` يستدعي طريقة القائمة (مثل `lstLog.AddItem` في VB).

## التصحيح

ضع نقطة توقف (`F9`) على سطر داخل معالج، ثم `F5` واضغط الزر: يتوقف البرنامج، وترى المسجلات في نافذة **Registers** (المسجلات)، وتنفّذ تعليمة تعليمة بـ `F11`. الدرس 14 يشرح نوافذ التصحيح.

## تمرين

صمم نموذجًا لتحويل درجة الحرارة: مربع نص `txtC`، وزر `btnConvert`، وعنوان `lblF`. عند الضغط احسب `F = C * 9 / 5 + 32` واعرضه.

<!-- test: {"form": {"Text": "Celsius to Fahrenheit", "controls": {"btnConvert": {"Text": "Convert"}, "txtC": {"Text": "37"}}}} -->
```asm form exercise
%include "radgui.inc"
%include "Form1.inc"

section .text

handler btnConvert_Click
    rad_get_int txtC, "Text"     ; rax = C
    ; احسب F في rbx ثم اعرضه في lblF
endhandler
```

```asm form solution
%include "radgui.inc"
%include "Form1.inc"

section .text

handler btnConvert_Click
    rad_get_int txtC, "Text"     ; rax = C
    imul rax, rax, 9
    cqo                          ; إشارة rax في rdx (لأعداد سالبة)
    mov rcx, 5
    idiv rcx
    add rax, 32
    mov rbx, rax
    rad_set_int lblF, "Text", rbx
endhandler
```

## اختبر نفسك

```quiz
{"question": "ما اسم معالج حدث الضغط على الزر btnSave؟", "choices": ["Click_btnSave", "btnSave_Click", "btnSave.Click", "onClick"], "answer": 1, "explanation": "الأداة_الحدث، كما في Visual Basic."}
```

```quiz
{"question": "بعد rad_get_int أين تجد العدد؟", "choices": ["rbx", "rcx", "rax", "[rsp]"], "answer": 2, "explanation": "الناتج دائمًا في rax."}
```

```quiz
{"question": "قيمة تحتاجها بعد عدة استدعاءات ماكرو: أين تحفظها داخل المعالج؟", "choices": ["rcx", "rdx", "rbx", "r8"], "answer": 2, "explanation": "rbx (وrsi وrdi وr12) محفوظة ويحفظها المعالج لك؛ الماكرو قد يغيّر rcx وrdx وr8."}
```

## الخلاصة

- المصمم يرسم النموذج، والكود بلغة التجميع يعالج الأحداث عبر GUI Bridge.
- `%include "radgui.inc"` و`%include "Form1.inc"` في أول ملف النموذج.
- `handler أداة_حدث` ... `endhandler`، و`Form1_Load` عند الظهور.
- `rad_set`/`rad_get`/`rad_set_int`/`rad_get_int`/`rad_call`/`rad_msgbox`، والنتائج في `rax`؛ احفظ ما تحتاجه في `rbx`.
