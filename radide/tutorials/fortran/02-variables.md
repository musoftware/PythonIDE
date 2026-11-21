# الدرس 2: المتغيرات والأنواع والطباعة المنسقة

**المتغير** صندوق له اسم نضع فيه قيمة. في Fortran نعرّف كل المتغيرات في **أول** البرنامج، بعد `implicit none` وقبل أي تعليمة تنفيذية.

> **تشبيه:** قبل أن يبدأ الطاهي الطبخ يجهز **الأواني** على الطاولة ويكتب على كل إناء ما سيوضع فيه: «سكر»، «دقيق». في Fortran كذلك: نجهز كل الصناديق ونسميها أولًا، ثم نبدأ العمل.

## الأنواع الأساسية

| النوع | ما يخزنه | مثال |
|---|---|---|
| `integer` | عدد صحيح | `42`، `-7` |
| `real` | عدد حقيقي (بفاصلة عشرية) دقة عادية | `3.14` |
| `real(8)` أو `double precision` | عدد حقيقي بدقة مضاعفة | `3.14159265358979d0` |
| `logical` | منطقي: صح أو خطأ | `.true.`، `.false.` |
| `character(len=20)` | نص طوله 20 حرفًا | `'Ahmed'` |
| `complex` | عدد مركب | `(1.0, 2.0)` |

```fortran run
program vars
  implicit none
  integer :: age
  real(8) :: height
  logical :: student
  character(len=20) :: name

  age = 21
  height = 1.75d0
  student = .true.
  name = 'Huda'

  print *, trim(name), age, height, student
end program vars
```

```text output
 Huda          21   1.7500000000000000      T
```

- الصيغة: `النوع :: اسم_المتغير`. ويمكن تعريف عدة متغيرات معًا: `integer :: a, b, c`.
- `trim(name)` تحذف المسافات الزائدة في آخر النص (لأن `name` طوله 20 دائمًا).
- `1.75d0` معناها 1.75 بدقة مضاعفة. الحرف `d` يعني double. لو كتبت `1.75` فقط فهي `real` عادية وتفقد بعض الدقة.
- `logical` تُطبع `T` أو `F`.

## العمليات الحسابية

| العملية | الرمز | مثال | الناتج |
|---|---|---|---|
| جمع وطرح | `+` `-` | `7 - 2` | `5` |
| ضرب | `*` | `6 * 7` | `42` |
| قسمة | `/` | `7 / 2` | `3` (!) |
| أُس | `**` | `2**8` | `256` |
| باقي القسمة | `mod(a, b)` | `mod(7, 2)` | `1` |

> **انتبه:** قسمة عددين صحيحين تعطي عددًا صحيحًا وتحذف الكسر: `7 / 2` = `3`. لو أردت 3.5 اجعل أحدهما حقيقيًا: `7.0 / 2` أو `real(7) / 2`.

## الطباعة المنسقة: تحكم كامل في الشكل

`print *` مريحة لكنها تضع مسافات كثيرة. لشكل دقيق نكتب **صيغة** (format) بدل النجمة:

```fortran run
program formats
  implicit none
  integer :: n
  real(8) :: price, total
  character(len=10) :: item

  n = 3
  price = 12.5d0
  item = 'Tea'
  total = n * price

  print '(a)', 'Invoice'
  print '(a, i0)', 'Count: ', n
  print '(a, f0.2)', 'Price: ', price
  print '(a, a, a, f8.2)', 'Item: ', trim(item), ' total =', total
  print '(i5, i5, i5)', 10, 200, 3000
  print '(a, es12.4)', 'Big: ', 6.02d23
end program formats
```

```text output
Invoice
Count: 3
Price: 12.50
Item: Tea total =   37.50
   10  200 3000
Big:   6.0200E+23
```

| الواصف | معناه | مثال |
|---|---|---|
| `a` | نص | `'(a)'` |
| `i5` | عدد صحيح في 5 خانات | `   10` |
| `i0` | عدد صحيح بأقل عرض ممكن (بلا مسافات) | `3` |
| `f8.2` | عدد حقيقي في 8 خانات منها رقمان بعد الفاصلة | `   37.50` |
| `f0.2` | عدد حقيقي بأقل عرض ورقمين بعد الفاصلة | `12.50` |
| `es12.4` | صيغة علمية | `6.0200E+23` |

> **نصيحة:** `i0` و`f0.2` هما الأكثر استخدامًا للطباعة الجميلة. استخدم `i5` و`f8.2` عندما تريد **أعمدة** مصفوفة في جدول.

## الثوابت بـ `parameter`

```fortran run
program circle
  implicit none
  real(8), parameter :: pi = 3.14159265358979d0
  real(8) :: r, area

  r = 2.0d0
  area = pi * r**2
  print '(a, f0.4)', 'Area = ', area
  ! pi = 3.0d0   خطأ لو أزلنا التعليق: لا يمكن تغيير الثابت
end program circle
```

```text output
Area = 12.5664
```

`parameter` تجعل القيمة **ثابتة**: أي محاولة لتغييرها خطأ ترجمة.

## الدوال الرياضية الجاهزة

```fortran run
program mathfun
  implicit none
  real(8) :: x
  x = 16.0d0
  print '(a, f0.1)', 'sqrt = ', sqrt(x)
  print '(a, f0.1)', 'abs = ', abs(-5.5d0)
  print '(a, i0)', 'max = ', max(3, 9, 4)
  print '(a, i0)', 'mod = ', mod(17, 5)
  print '(a, i0)', 'nint = ', nint(2.7d0)
  print '(a, f0.3)', 'sin = ', sin(0.5d0)
end program mathfun
```

```text output
sqrt = 4.0
abs = 5.5
max = 9
mod = 2
nint = 3
sin = .479
```

لاحظ أن `f0.3` تطبع `.479` بدون صفر قبل الفاصلة. هذا سلوك Fortran القياسي. إن أردت الصفر استخدم عرضًا ثابتًا مثل `f6.3`.

## أخطاء شائعة

- **تعريف متغير بعد تعليمة تنفيذية:** خطأ `Unexpected data declaration statement`. كل التعريفات في الأعلى.
- **`7 / 2` يعطي 3:** قسمة صحيحة. استخدم `7.0d0 / 2`.
- **فقدان الدقة:** `real(8) :: x = 0.1` تخزن 0.1 بدقة عادية أولًا. اكتب `0.1d0`.
- **نص يُقص:** `character(len=3) :: s = 'Ahmed'` يخزن `Ahm` فقط.

## تمارين

### التمرين 1

احسب متوسط ثلاث درجات (80 و90 و75) واطبعه برقمين بعد الفاصلة بالشكل `Average = 81.67`:

```fortran exercise
program avg
  implicit none
  integer :: a, b, c
  real(8) :: average
  a = 80
  b = 90
  c = 75
  ! احسب average واطبعه
end program avg
```

```fortran solution
program avg
  implicit none
  integer :: a, b, c
  real(8) :: average
  a = 80
  b = 90
  c = 75
  average = (a + b + c) / 3.0d0
  print '(a, f0.2)', 'Average = ', average
end program avg
```

```text output
Average = 81.67
```

### التمرين 2

حوّل 100 درجة مئوية إلى فهرنهايت (F = C × 9 / 5 + 32) واطبع `100 C = 212.0 F`:

```fortran exercise
program temp
  implicit none
  real(8) :: c, f
  c = 100.0d0
  ! أكمل
end program temp
```

```fortran solution
program temp
  implicit none
  real(8) :: c, f
  c = 100.0d0
  f = c * 9.0d0 / 5.0d0 + 32.0d0
  print '(f0.0, a, f0.1, a)', c, ' C = ', f, ' F'
end program temp
```

```text output
100. C = 212.0 F
```

لاحظ أن `f0.0` تطبع `100.` بالنقطة. لو أردت `100` بلا نقطة حوّلها لعدد صحيح: `nint(c)` مع `i0`.

## اختبر نفسك

```quiz
{"question": "ما ناتج 7 / 2 إذا كان الرقمان integer؟", "choices": ["3.5", "3", "4", "خطأ"], "answer": 1, "explanation": "قسمة الأعداد الصحيحة تحذف الكسر."}
```

```quiz
{"question": "أي صيغة تطبع عددًا صحيحًا بلا مسافات زائدة؟", "choices": ["i5", "i0", "f0.2", "a"], "answer": 1, "explanation": "i0 تستخدم أقل عرض ممكن."}
```

```quiz
{"question": "كيف تعرّف ثابتًا لا يتغير؟", "choices": ["real(8) :: pi", "real(8), parameter :: pi = 3.14d0", "const pi = 3.14", "final pi"], "answer": 1, "explanation": "الخاصية parameter تجعل القيمة ثابتة."}
```

## الخلاصة

- `integer` و`real(8)` و`logical` و`character(len=n)`، وكلها تُعرّف في أول البرنامج.
- انتبه للقسمة الصحيحة، واكتب الأعداد الحقيقية بـ `d0` للدقة المضاعفة.
- `print '(a, i0, f0.2)'` للطباعة المنسقة، و`parameter` للثوابت.
