# الدرس 8: نافذة رسومية بـ Fortran في مصمم النماذج

هل تتخيل برنامج Fortran بنافذة وأزرار مثل Visual Basic؟ في RAD IDE هذا ممكن بسهولة! ترسم النافذة في **مصمم النماذج**، وتكتب الحسابات بـ Fortran كما تعلمت، والـ IDE تربط بينهما.

## الفكرة: GUI Bridge

1. **الـ IDE ترسم النافذة** التي صممتها.
2. **برنامج Fortran** يعمل في الخلفية وينتظر الأحداث.
3. عند الضغط على زر اسمه `btnCalc` تُستدعى في برنامجك الإجراء `btnCalc_Click`.
4. داخله تقرأ وتغير الأدوات بإجراءات جاهزة من الوحدة `radgui`.

> **تشبيه:** النافذة مثل **شباك التذاكر** الذي يقف أمامه الناس، وبرنامج Fortran هو **المحاسب** في الداخل. يكتب الزبون طلبه في ورقة (مربع النص) ويضغط الجرس (الزر)، فيحسب المحاسب ويرد بالنتيجة على الشاشة (Label).

الـ IDE تولّد بنفسها الملف `_radmain.f90` (فيه `program` وحلقة الأحداث) وتنسخ `radgui.f90`، لذلك **لا تكتب `program`** في مشروع النوافذ. كود النموذج يكون **وحدة** (module) اسمها `form1_code`.

## إجراءات التعامل مع الأدوات

| الإجراء أو الدالة | وظيفته | مثال |
|---|---|---|
| `rad_get(أداة, خاصية)` | تقرأ خاصية كنص | `s = rad_get('txtA', 'Text')` |
| `call rad_set(أداة, خاصية, نص)` | تغير خاصية | `call rad_set('lblOut', 'Text', 'Hi')` |
| `call rad_call(أداة, دالة, وسيط)` | تستدعي دالة في الأداة | `call rad_call('lstLog', 'AddItem', 'x')` |
| `call rad_msgbox(نص)` | رسالة منبثقة | `call rad_msgbox('Done')` |
| `rad_input(سؤال)` | مربع إدخال | `s = rad_input('Name?')` |
| `rad_num(نص)` | نص إلى `real(8)` (صفر إن لم يكن رقمًا) | `x = rad_num(s)` |
| `rad_str(x)` | `real(8)` إلى نص مختصر | `rad_str(2.5d0)` |
| `call rad_print(نص)` | سطر في نافذة **Output** | `call rad_print('debug')` |
| `call rad_end()` | إنهاء البرنامج | |

> **مهم:** لا تستخدم `print *` في مشروع النوافذ؛ البرنامج يتحدث مع الـ IDE عبر الإخراج القياسي. استخدم `call rad_print(...)` للتتبع.

## مشروعك: محوّل درجات الحرارة

### 1) إنشاء المشروع

1. **File > New Project...** (ملف ← مشروع جديد...).
2. **Native** > **Fortran (GUI Bridge, gfortran)** ← القالب **Windows Application** (تطبيق Windows).
3. سمّه `TempForm`. يفتح **Form1** في وضع التصميم، ومعه ملف الكود `Form1.f90`.

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب الأدوات، وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtC` | `0` |
| `Button` | `btnConvert` | `حوّل إلى فهرنهايت` |
| `Label` | `lblResult` | (فارغ) |
| `ListBox` | `lstHistory` | |

### 3) كتابة الكود

انقر مرتين على الزر، فتضيف الـ IDE الإجراء `btnConvert_Click` إلى `Form1.f90`. أكمل الكود:

<!-- test: {"set": {"txtC.Text": "100"}, "events": ["btnConvert Click", {"txtC.Text": "abc"}, "btnConvert Click"], "expect": {"lblResult.Text": "100 C = 212 F", "lstHistory.Items": "100 -> 212"}, "msgbox": ["Please write a number"]} -->
```fortran form run
module form1_code
  use radgui
  implicit none
contains

  subroutine Form1_Load()
    call rad_set('lblResult', 'Text', 'Write a temperature in C')
  end subroutine Form1_Load

  subroutine btnConvert_Click()
    character(len=:), allocatable :: s
    real(8) :: c, f
    integer :: ios

    s = trim(rad_get('txtC', 'Text'))
    read(s, *, iostat=ios) c
    if (ios /= 0 .or. len(s) == 0) then
      call rad_msgbox('Please write a number')
      return
    end if
    f = c * 9d0 / 5d0 + 32d0
    call rad_set('lblResult', 'Text', s // ' C = ' // rad_str(f) // ' F')
    call rad_call('lstHistory', 'AddItem', s // ' -> ' // rad_str(f))
    call rad_print('converted ' // s)          ! يظهر في نافذة Output
  end subroutine btnConvert_Click

end module form1_code
```

### 4) التشغيل

اضغط **F5**: تترجم الـ IDE المشروع بـ `gfortran` (مع `radgui.f90` والبرنامج المولّد)، ثم تظهر النافذة. اكتب رقمًا واضغط الزر.

قواعد ربط الأحداث:

- اسم الإجراء **`اسمالأداة_اسمالحدث`** مثل `btnConvert_Click`، و**بلا معاملات**.
- كل الإجراءات داخل الوحدة `form1_code` بعد `contains`.
- Fortran لا تفرق بين الحروف الكبيرة والصغيرة في الأسماء، لكن **أسماء الأدوات داخل النصوص** (`'txtC'`) يجب أن تطابق **Name** بالضبط.

لاحظ أننا استخدمنا `read(s, *, iostat=ios)` من الدرس 7 لنتحقق أن المدخل رقم فعلًا، وأن `rad_str` تحول الرقم إلى نص مختصر (`212` بدل `212.000000`).

## مثال ثانٍ: إحصائيات مصفوفة

قوة Fortran في المصفوفات، فلنجعل النافذة تحسب إحصائيات أرقام يكتبها المستخدم مفصولة بفواصل:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtValues` | `4, 8, 15, 16, 23, 42` |
| `Button` | `btnStats` | `احسب` |
| `Label` | `lblSum` | (فارغ) |
| `Label` | `lblMean` | (فارغ) |
| `Label` | `lblMax` | (فارغ) |

<!-- test: {"set": {"txtValues.Text": "4, 8, 15, 16, 23, 42"}, "events": ["btnStats Click"], "expect": {"lblSum.Text": "Sum = 108", "lblMean.Text": "Mean = 18", "lblMax.Text": "Max = 42"}} -->
```fortran form run
module form1_code
  use radgui
  implicit none
contains

  ! تعد الأرقام المفصولة بفواصل في النص
  integer function count_items(s)
    character(len=*), intent(in) :: s
    integer :: i
    count_items = 1
    do i = 1, len_trim(s)
      if (s(i:i) == ',') count_items = count_items + 1
    end do
  end function count_items

  subroutine btnStats_Click()
    character(len=:), allocatable :: s
    real(8), allocatable :: v(:)
    integer :: n, ios

    s = trim(rad_get('txtValues', 'Text'))
    n = count_items(s)
    allocate(v(n))
    read(s, *, iostat=ios) v                  ! يقرأ n أرقام دفعة واحدة
    if (ios /= 0) then
      call rad_msgbox('Write numbers separated by commas')
      return
    end if
    call rad_set('lblSum', 'Text', 'Sum = ' // rad_str(sum(v)))
    call rad_set('lblMean', 'Text', 'Mean = ' // rad_str(sum(v) / n))
    call rad_set('lblMax', 'Text', 'Max = ' // rad_str(maxval(v)))
  end subroutine btnStats_Click

end module form1_code
```

كل ما تعلمناه في الدورة في مكان واحد: المصفوفات الديناميكية (`allocatable`)، ودوال المصفوفات (`sum` و`maxval`)، والدوال (`count_items`)، والقراءة الآمنة بـ `iostat`.

> **نصيحة للتصحيح:** استخدم `call rad_print('n = ' // rad_str(real(n, 8)))` لتتبع القيم في نافذة **Output** أثناء تشغيل النافذة.

## أخطاء شائعة

- **كتابة `program` في `Form1.f90`:** الـ IDE تولد البرنامج الرئيسي بنفسها؛ كود النموذج وحدة فقط.
- **نسيان `use radgui`:** خطأ `Symbol 'rad_set' has no IMPLICIT type`.
- **إرسال رقم مباشرة إلى `rad_set`:** `call rad_set('lblX', 'Text', f)` خطأ نوع؛ حوّله أولًا: `rad_str(f)`.
- **اسم الأداة خطأ في النص:** `rad_get('txtc', ...)` بدل `'txtC'` لا يجد الأداة.
- **`print *` في مشروع النوافذ:** يربك الاتصال؛ استخدم `rad_print`.

## تمرين

### التمرين 1

أضف زرًا `btnClear` يمسح القائمة `lstHistory` (الدالة `Clear`) ويفرغ مربع النص `txtC`:

```fortran form exercise
module form1_code
  use radgui
  implicit none
contains
  subroutine btnClear_Click()
    ! اكتب هنا
  end subroutine btnClear_Click
end module form1_code
```

<!-- test: {"items": {"lstHistory": ["a", "b"]}, "set": {"txtC.Text": "5"}, "events": ["btnClear Click"], "expect": {"lstHistory.ListCount": "0", "txtC.Text": ""}} -->
```fortran form solution
module form1_code
  use radgui
  implicit none
contains
  subroutine btnClear_Click()
    call rad_call('lstHistory', 'Clear', '')
    call rad_set('txtC', 'Text', '')
  end subroutine btnClear_Click
end module form1_code
```

## اختبر نفسك

```quiz
{"question": "أين يُكتب معالج الحدث btnGo_Click في مشروع نوافذ Fortran؟", "choices": ["داخل program", "subroutine بلا معاملات داخل الوحدة form1_code بعد contains", "في ملف radgui.f90", "function ترجع integer"], "answer": 1, "explanation": "كود النموذج وحدة، ومعالجات الأحداث إجراءات بلا معاملات فيها."}
```

```quiz
{"question": "كيف تعرض رقمًا حقيقيًا f في Label؟", "choices": ["call rad_set('lbl', 'Text', f)", "call rad_set('lbl', 'Text', rad_str(f))", "print *, f", "lbl = f"], "answer": 1, "explanation": "rad_set تأخذ نصًا، وrad_str تحول real(8) إلى نص."}
```

## الخلاصة وماذا بعد؟

- مشروع **Windows Application** في **Fortran (GUI Bridge, gfortran)**: ارسم ثم اكتب `subroutine اسمالأداة_الحدث()` داخل الوحدة `form1_code`.
- `rad_get` و`rad_set` و`rad_call` و`rad_msgbox` و`rad_num`/`rad_str` للتعامل مع الأدوات.
- لا `program` ولا `print *` في مشروع النوافذ.

**مبروك! أنهيت دورة أساسيات Fortran.** تعرفت على الأنواع والطباعة المنسقة والشروط والحلقات والمصفوفات والوحدات والملفات، وصنعت نافذة رسومية. إن أعجبتك الحسابات العلمية فابحث عن مكتبات مثل **LAPACK** للجبر الخطي، وموقع **fortran-lang.org** الذي فيه دروس ومدير حزم حديث اسمه **fpm**.
