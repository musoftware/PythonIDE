# الدرس 3: الإدخال والشروط

البرنامج الذي يحسب نفس الأرقام كل مرة ممل! اليوم نجعل البرنامج **يسأل** المستخدم، ثم **يقرر** ماذا يفعل حسب الإجابة.

## القراءة بـ `read *`

```fortran run
program greet
  implicit none
  character(len=30) :: name
  integer :: age

  print '(a)', 'What is your name?'
  read *, name
  print '(a)', 'How old are you?'
  read *, age
  print '(a, a, a, i0, a)', 'Hello ', trim(name), ', in 5 years you will be ', age + 5, '.'
end program greet
```

```text input
Salma
17
```

```text output
What is your name?
How old are you?
Hello Salma, in 5 years you will be 22.
```

- `read *, متغير` تقرأ قيمة من لوحة المفاتيح وتضعها في المتغير بالنوع المناسب.
- يمكن قراءة عدة قيم معًا: `read *, a, b` ويكتبها المستخدم مفصولة بمسافة أو فاصلة.

> **في الـ IDE:** عند التشغيل بـ **Ctrl+F5** تكتب المدخلات في نافذة الطرفية. وفي صفحة الدرس يأخذ زر «تحقق» المدخلات من مربع `text input`.

> **انتبه:** `read *` تعتبر المسافة والفاصلة **فاصلًا** بين القيم. لو كتب المستخدم «Salma Ali» تُقرأ «Salma» فقط. لقراءة سطر كامل استخدم `read '(a)', name`.

## الشرط `if`

```fortran run
program check
  implicit none
  integer :: mark
  read *, mark
  if (mark >= 50) then
    print '(a)', 'Passed'
  else
    print '(a)', 'Failed'
  end if
end program check
```

```text input
73
```

```text output
Passed
```

الشكل العام:

```fortran
if (شرط) then
  ! إذا تحقق الشرط
else if (شرط آخر) then
  ! إذا تحقق الشرط الثاني
else
  ! في كل الحالات الأخرى
end if
```

وإن كانت التعليمة سطرًا واحدًا يمكن كتابتها مختصرة: `if (x < 0) x = -x`.

## عمليات المقارنة والمنطق

| المعنى | الحديث | القديم (ما زال يعمل) |
|---|---|---|
| يساوي | `==` | `.eq.` |
| لا يساوي | `/=` | `.ne.` |
| أكبر / أصغر | `>` `<` | `.gt.` `.lt.` |
| أكبر أو يساوي / أصغر أو يساوي | `>=` `<=` | `.ge.` `.le.` |
| و / أو / ليس | `.and.` `.or.` `.not.` | |

> **انتبه:** «لا يساوي» في Fortran هي **`/=`** وليست `!=` كما في C. (تذكر أن `!` تبدأ تعليقًا!)

## سلسلة شروط: التقدير

```fortran run
program grade
  implicit none
  integer :: mark
  read *, mark
  if (mark < 0 .or. mark > 100) then
    print '(a)', 'Invalid mark'
  else if (mark >= 85) then
    print '(a)', 'Excellent'
  else if (mark >= 75) then
    print '(a)', 'Very good'
  else if (mark >= 50) then
    print '(a)', 'Pass'
  else
    print '(a)', 'Fail'
  end if
end program grade
```

```text input
78
```

```text output
Very good
```

## الاختيار بـ `select case`

عندما نقارن متغيرًا واحدًا بقيم كثيرة، `select case` أوضح من سلسلة `if`:

```fortran run
program days
  implicit none
  integer :: d
  read *, d
  select case (d)
  case (6, 7)
    print '(a)', 'Weekend'
  case (1:5)
    print '(a)', 'Work day'
  case default
    print '(a)', 'No such day'
  end select
end program days
```

```text input
6
```

```text output
Weekend
```

- `case (6, 7)`: القيمة 6 **أو** 7.
- `case (1:5)`: أي قيمة من 1 إلى 5.
- `case default`: كل ما عدا ذلك.

ويعمل `select case` مع النصوص أيضًا: `case ('yes', 'y')`.

## أخطاء شائعة

| الخطأ | السبب | الحل |
|---|---|---|
| `Expected a right parenthesis in expression` | استخدام `!=` | اكتب `/=` |
| `Unclassifiable statement` في سطر `if` | نسيت `then` | `if (x > 0) then` |
| `Expecting END PROGRAM statement` | نسيت `end if` | أغلق كل `if` بـ `end if` |
| `Fortran runtime error: Bad integer for item 1 in list input` | المستخدم كتب حروفًا بدل رقم | تحقق من المدخلات بـ `iostat` (نتعلمه في درس الملفات) |

## تمارين

### التمرين 1

اقرأ عددًا صحيحًا واطبع `Even` إن كان زوجيًا و`Odd` إن كان فرديًا:

```fortran exercise
program parity
  implicit none
  integer :: n
  read *, n
  ! أكمل
end program parity
```

```fortran solution
program parity
  implicit none
  integer :: n
  read *, n
  if (mod(n, 2) == 0) then
    print '(a)', 'Even'
  else
    print '(a)', 'Odd'
  end if
end program parity
```

```text input
7
```

```text output
Odd
```

### التمرين 2

اقرأ رقمين وعملية (`+` أو `-` أو `*` أو `/`) في ثلاثة أسطر، واطبع الناتج باستخدام `select case`:

```fortran exercise
program calc
  implicit none
  real(8) :: a, b
  character(len=1) :: op
  read *, a
  read *, b
  read *, op
  ! أكمل
end program calc
```

```fortran solution
program calc
  implicit none
  real(8) :: a, b
  character(len=1) :: op
  read *, a
  read *, b
  read *, op
  select case (op)
  case ('+')
    print '(f0.2)', a + b
  case ('-')
    print '(f0.2)', a - b
  case ('*')
    print '(f0.2)', a * b
  case ('/')
    if (b == 0d0) then
      print '(a)', 'Cannot divide by zero'
    else
      print '(f0.2)', a / b
    end if
  case default
    print '(a)', 'Unknown operation'
  end select
end program calc
```

```text input
9
4
*
```

```text output
36.00
```

## اختبر نفسك

```quiz
{"question": "كيف تكتب «لا يساوي» في Fortran الحديثة؟", "choices": ["!=", "<>", "/=", "=/"], "answer": 2, "explanation": "/= هي «لا يساوي»، و! تبدأ تعليقًا."}
```

```quiz
{"question": "ماذا يطابق case (1:5) في select case؟", "choices": ["1 و5 فقط", "أي قيمة من 1 إلى 5", "القيمة 1.5", "لا شيء"], "answer": 1, "explanation": "النقطتان تعنيان مدى من القيم."}
```

```quiz
{"question": "بماذا تنتهي كتلة if متعددة الأسطر؟", "choices": ["endif أو end if", "}", "fi", "next"], "answer": 0, "explanation": "تنتهي بـ end if (ويُقبل endif)."}
```

## الخلاصة

- `read *, x` للقراءة، و`read '(a)', s` لقراءة سطر كامل.
- `if (...) then ... else if ... else ... end if` للقرارات.
- المقارنة: `==` و`/=` و`<` و`>=`، والمنطق: `.and.` و`.or.` و`.not.`.
- `select case` لمقارنة متغير واحد بقيم ومديات كثيرة.
