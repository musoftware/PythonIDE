# الدرس 5: المصفوفات: قوة Fortran الحقيقية

**المصفوفة** (array) مجموعة متغيرات من نفس النوع تحت اسم واحد، نصل لكل عنصر برقمه. وهنا تتألق Fortran: يمكنك أن تجمع أو تضرب **مصفوفة كاملة** بسطر واحد دون حلقة، تمامًا كما تكتب المعادلة على الورق.

> **تشبيه:** المصفوفة مثل **صف خزائن** في المدرسة، كل خزانة لها رقم. وFortran تسمح لك أن تقول «ضع كتابًا في **كل** الخزائن» بأمر واحد بدل أن تمر عليها واحدة واحدة.

## تعريف المصفوفة واستخدامها

```fortran run
program marks
  implicit none
  integer :: m(5)
  integer :: i

  m = [70, 85, 92, 60, 78]          ! تعبئة كل العناصر مرة واحدة
  print '(a, i0)', 'First: ', m(1)
  print '(a, i0)', 'Last: ', m(5)
  m(4) = 65                          ! تعديل عنصر
  do i = 1, size(m)
    write(*, '(i0, a)', advance='no') m(i), ' '
  end do
  print *
end program marks
```

```text output
First: 70
Last: 78
70 85 92 65 78 
```

> **مهم جدًا:** الترقيم في Fortran يبدأ من **1** وليس من 0 كما في C وPython. أول عنصر `m(1)` وآخره `m(5)`. ونصل للعنصر بالأقواس العادية `()` وليس `[]`.

يمكنك أيضًا اختيار بداية الترقيم: `real :: temp(-10:10)` مصفوفة من 21 عنصرًا تبدأ من -10.

## دوال المصفوفات الجاهزة

```fortran run
program stats
  implicit none
  real(8) :: x(6)
  x = [4.0d0, 8.0d0, 15.0d0, 16.0d0, 23.0d0, 42.0d0]

  print '(a, f0.1)', 'sum     = ', sum(x)
  print '(a, f0.1)', 'average = ', sum(x) / size(x)
  print '(a, f0.1)', 'max     = ', maxval(x)
  print '(a, f0.1)', 'min     = ', minval(x)
  print '(a, i0)', 'max at  = ', maxloc(x, 1)
  print '(a, i0)', 'count>10= ', count(x > 10)
  print '(a, l1)', 'any>40  = ', any(x > 40)
end program stats
```

```text output
sum     = 108.0
average = 18.0
max     = 42.0
min     = 4.0
max at  = 6
count>10= 4
any>40  = T
```

| الدالة | وظيفتها |
|---|---|
| `size(a)` | عدد العناصر |
| `sum(a)` / `product(a)` | المجموع / حاصل الضرب |
| `maxval(a)` / `minval(a)` | أكبر / أصغر قيمة |
| `maxloc(a, 1)` / `minloc(a, 1)` | **مكان** أكبر / أصغر قيمة |
| `count(شرط)` | كم عنصرًا يحقق الشرط |
| `any(شرط)` / `all(شرط)` | هل عنصر واحد على الأقل / كل العناصر تحقق الشرط |

## العمليات على المصفوفة كاملة

```fortran run
program whole
  implicit none
  integer :: a(4), b(4), c(4)
  a = [1, 2, 3, 4]
  b = [10, 20, 30, 40]

  c = a + b                 ! جمع عنصر مع عنصر
  print '(4i4)', c
  c = a * 2                 ! كل عنصر × 2
  print '(4i4)', c
  c = a**2                  ! تربيع كل عنصر
  print '(4i4)', c
  where (b > 15) c = 0      ! صفّر العناصر حيث b > 15
  print '(4i4)', c
  print '(4i4)', a(2:3)     ! شريحة: العنصران 2 و3
end program whole
```

```text output
  11  22  33  44
   2   4   6   8
   1   4   9  16
   1   0   0   0
   2   3
```

- `a + b` تجمع العناصر المتقابلة بدون حلقة.
- `(4i4)` صيغة تعني «4 أعداد صحيحة كل منها في 4 خانات».
- `a(2:3)` **شريحة** (section) من العنصر 2 إلى 3. و`a(::2)` العناصر الفردية الترتيب.
- `where` شرط يُطبق على كل عنصر.

## المصفوفات الثنائية (المصفوفات الرياضية)

```fortran run
program matrix
  implicit none
  integer :: m(2, 3), t(3, 2)
  integer :: i

  m = reshape([1, 2, 3, 4, 5, 6], [2, 3])
  do i = 1, 2
    print '(3i3)', m(i, :)          ! الصف i كاملًا
  end do
  t = transpose(m)
  print '(a)', 'transpose:'
  do i = 1, 3
    print '(2i3)', t(i, :)
  end do
  print '(a, i0)', 'm(2,3) = ', m(2, 3)
end program matrix
```

```text output
  1  3  5
  2  4  6
transpose:
  1  2
  3  4
  5  6
m(2,3) = 6
```

> **ملاحظة:** Fortran تخزن المصفوفة **عمودًا عمودًا** (column-major)، لذلك ملأت `reshape` العمود الأول بـ 1 و2، ثم الثاني بـ 3 و4. هذا عكس C وPython. وفيها دالة `matmul(a, b)` لضرب المصفوفات رياضيًا.

## المصفوفات الديناميكية `allocatable`

عندما لا نعرف الحجم إلا وقت التشغيل:

```fortran run
program dynamic
  implicit none
  real(8), allocatable :: v(:)
  integer :: n, i

  read *, n
  allocate(v(n))
  do i = 1, n
    read *, v(i)
  end do
  print '(a, i0, a, f0.2)', 'Average of ', n, ' values = ', sum(v) / n
  deallocate(v)
end program dynamic
```

```text input
4
10
20
35
15
```

```text output
Average of 4 values = 20.00
```

- `allocatable :: v(:)` مصفوفة بلا حجم بعد.
- `allocate(v(n))` نحجز لها `n` عنصرًا.
- `deallocate(v)` نحررها (وFortran تحررها تلقائيًا عند نهاية النطاق أيضًا).

## أخطاء شائعة

- **البدء من صفر:** `m(0)` خارج المصفوفة. الترقيم من 1.
- **الخروج عن الحدود:** Fortran لا تفحص الحدود افتراضيًا، فقد تقرأ قيمة عشوائية بصمت! أثناء التعلم أضف خيار المترجم `-fcheck=bounds` فتظهر رسالة واضحة.
- **مصفوفتان بحجمين مختلفين في `a + b`:** خطأ `Shapes for operands at (1) and (2) are not conformable`.
- **استخدام `[]` للوصول:** `m[1]` خطأ؛ الصحيح `m(1)`. الأقواس المربعة فقط لإنشاء القيم `[1, 2, 3]`.

## تمارين

### التمرين 1

لديك درجات 6 طلاب. اطبع عدد الناجحين (50 فأكثر) ومتوسط الدرجات:

```fortran exercise
program class
  implicit none
  integer :: g(6)
  g = [45, 90, 66, 30, 75, 88]
  ! أكمل
end program class
```

```fortran solution
program class
  implicit none
  integer :: g(6)
  g = [45, 90, 66, 30, 75, 88]
  print '(a, i0)', 'Passed: ', count(g >= 50)
  print '(a, f0.2)', 'Average: ', real(sum(g), 8) / size(g)
end program class
```

```text output
Passed: 4
Average: 65.67
```

### التمرين 2

أنشئ مصفوفة فيها مربعات الأعداد من 1 إلى 8 **بدون حلقة `do`** (استخدم `[(i, i = 1, 8)]` ثم العمليات على المصفوفة)، واطبعها:

```fortran exercise
program squares
  implicit none
  integer :: i
  integer :: s(8)
  ! أكمل
  print '(8i4)', s
end program squares
```

```fortran solution
program squares
  implicit none
  integer :: i
  integer :: s(8)
  s = [(i, i = 1, 8)]
  s = s**2
  print '(8i4)', s
end program squares
```

```text output
   1   4   9  16  25  36  49  64
```

`[(i, i = 1, 8)]` اسمها **حلقة ضمنية** (implied do): تنشئ المصفوفة `[1, 2, ..., 8]` في سطر واحد.

## اختبر نفسك

```quiz
{"question": "ما رقم أول عنصر في مصفوفة Fortran افتراضيًا؟", "choices": ["0", "1", "-1", "حسب المترجم"], "answer": 1, "explanation": "الترقيم يبدأ من 1 افتراضيًا."}
```

```quiz
{"question": "ماذا يفعل c = a + b إذا كانت a وb مصفوفتين بنفس الحجم؟", "choices": ["خطأ", "يجمع العناصر المتقابلة", "يدمج المصفوفتين", "يجمع كل العناصر في رقم واحد"], "answer": 1, "explanation": "العمليات تُطبق عنصرًا بعنصر على المصفوفة كاملة."}
```

```quiz
{"question": "أي دالة تعد العناصر التي تحقق شرطًا؟", "choices": ["size", "sum", "count", "maxloc"], "answer": 2, "explanation": "count(a > 10) تعد العناصر الأكبر من 10."}
```

## الخلاصة

- `integer :: a(5)`، والترقيم من 1، والوصول بـ `a(i)`.
- `sum` و`maxval` و`count` و`any` وأخواتها توفر عليك الحلقات.
- العمليات على المصفوفة كاملة (`a + b` و`a * 2` و`where`) والشرائح `a(2:4)`.
- `allocatable` و`allocate` للمصفوفات التي يُعرف حجمها وقت التشغيل.
