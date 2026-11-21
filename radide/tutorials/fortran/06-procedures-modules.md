# الدرس 6: الدوال والإجراءات والوحدات

عندما يكبر البرنامج نقسمه إلى قطع صغيرة لكل منها اسم ووظيفة. في Fortran نوعان من هذه القطع:

| النوع | يرجع قيمة؟ | كيف تستدعيه |
|---|---|---|
| **دالة** `function` | نعم، قيمة واحدة | داخل تعبير: `y = square(x)` |
| **إجراء** `subroutine` | لا (لكن يمكنه تعديل معاملاته) | بالكلمة `call`: `call swap(a, b)` |

> **تشبيه:** الدالة مثل **آلة العصير**: تضع فيها برتقالًا فتخرج كوب عصير (قيمة). والإجراء مثل **عامل النظافة**: لا يعطيك شيئًا في يدك، لكنه يغير حال الغرفة (المعاملات).

## الدوال والإجراءات داخل البرنامج: `contains`

```fortran run
program demo
  implicit none
  integer :: a, b

  print '(a, i0)', 'square(7) = ', square(7)
  a = 3
  b = 8
  call swap(a, b)
  print '(a, i0, a, i0)', 'a = ', a, ', b = ', b

contains

  integer function square(x)
    integer, intent(in) :: x
    square = x * x            ! نضع الناتج في اسم الدالة نفسه
  end function square

  subroutine swap(x, y)
    integer, intent(inout) :: x, y
    integer :: tmp
    tmp = x
    x = y
    y = tmp
  end subroutine swap

end program demo
```

```text output
square(7) = 49
a = 8, b = 3
```

- نكتب الدوال والإجراءات بعد الكلمة **`contains`** في آخر البرنامج.
- في الدالة نضع الناتج في **اسم الدالة** (`square = ...`)، أو نستخدم `result`: `function square(x) result(r)`.
- المعاملات في Fortran **تُمرر بالمرجع**: لذلك استطاع `swap` تغيير `a` و`b` الأصليين.

### `intent`: وعد بما ستفعله بالمعامل

| `intent` | المعنى |
|---|---|
| `intent(in)` | للقراءة فقط؛ المترجم يمنع تعديله |
| `intent(out)` | للكتابة فقط؛ يحمل نتيجة للمستدعي |
| `intent(inout)` | للقراءة والتعديل |

اكتب `intent` دائمًا: تجعل الكود أوضح، ويكتشف المترجم أخطاء مثل تعديل معامل كان يجب أن يبقى ثابتًا.

## إجراء يرجع أكثر من نتيجة

```fortran run
program minmax_demo
  implicit none
  real(8) :: lo, hi, avg

  call stats([3d0, 9d0, 1d0, 7d0], lo, hi, avg)
  print '(a, f0.1, a, f0.1, a, f0.2)', 'min ', lo, '  max ', hi, '  avg ', avg

contains

  subroutine stats(v, mn, mx, mean)
    real(8), intent(in) :: v(:)          ! مصفوفة بأي حجم
    real(8), intent(out) :: mn, mx, mean
    mn = minval(v)
    mx = maxval(v)
    mean = sum(v) / size(v)
  end subroutine stats

end program minmax_demo
```

```text output
min 1.0  max 9.0  avg 5.00
```

`v(:)` معامل مصفوفة **بأي حجم** (assumed shape)، و`size(v)` يعرف حجمها.

## الوحدات `module`: تنظيم الكود في ملفات

**الوحدة** مكان نجمع فيه الثوابت والدوال المرتبطة، ثم نستخدمها في أي برنامج بـ `use`. وهي الطريقة الحديثة لتقسيم المشروع إلى ملفات:

```fortran run
! #file: geometry.f90
module geometry
  implicit none
  real(8), parameter :: pi = 3.14159265358979d0
contains
  real(8) function circle_area(r)
    real(8), intent(in) :: r
    circle_area = pi * r**2
  end function circle_area

  real(8) function rect_area(w, h)
    real(8), intent(in) :: w, h
    rect_area = w * h
  end function rect_area
end module geometry

! #file: main.f90
program shapes
  use geometry               ! نستورد كل ما في الوحدة
  implicit none
  print '(a, f0.3)', 'circle: ', circle_area(1.5d0)
  print '(a, f0.1)', 'rect:   ', rect_area(4d0, 2.5d0)
  print '(a, f0.5)', 'pi:     ', pi
end program shapes
```

```text output
circle: 7.069
rect:   10.0
pi:     3.14159
```

**في الـ IDE:** أضف ملفًا جديدًا من **Project > Add Module...** (مشروع ← إضافة وحدة...) واكتب اسمه `geometry.f90`. والـ IDE ترتب الملفات تلقائيًا عند الترجمة بحيث تُترجم الوحدة **قبل** البرنامج الذي يستخدمها (gfortran يحتاج ذلك لأنه ينتج ملف `geometry.mod` يقرؤه البرنامج).

### استيراد أجزاء محددة

```fortran
use geometry, only: circle_area          ! نستورد دالة واحدة فقط
use geometry, only: area => circle_area  ! ونسميها باسم آخر
```

`only` تجعل واضحًا من أين جاء كل اسم، وتمنع تعارض الأسماء بين الوحدات.

## الدوال التكرارية `recursive`

الدالة التي تستدعي نفسها يجب أن تُعلم بـ `recursive`:

```fortran run
program rec
  implicit none
  print '(a, i0)', 'fib(10) = ', fib(10)
contains
  recursive integer function fib(n) result(r)
    integer, intent(in) :: n
    if (n < 2) then
      r = n
    else
      r = fib(n - 1) + fib(n - 2)
    end if
  end function fib
end program rec
```

```text output
fib(10) = 55
```

## أخطاء شائعة

| الرسالة | السبب | الحل |
|---|---|---|
| `Return type mismatch of function` أو `has no IMPLICIT type` | دالة خارج `contains` أو بلا نوع | ضعها بعد `contains` أو في وحدة |
| `Dummy argument 'x' with INTENT(IN) in variable definition context` | تعديل معامل `intent(in)` | غيّر إلى `inout` أو انسخه لمتغير محلي |
| `Cannot open module file 'geometry.mod'` | البرنامج تُرجم قبل الوحدة | الـ IDE ترتبها؛ تأكد أن الملف مضاف للمشروع |
| `Unclassifiable statement` عند استدعاء إجراء | نسيت `call` | `call swap(a, b)` |

## تمارين

### التمرين 1

اكتب دالة `is_prime(n)` ترجع `logical`، واطبع الأعداد الأولية حتى 30:

```fortran exercise
program primes
  implicit none
  integer :: i
  do i = 2, 30
    if (is_prime(i)) write(*, '(i0, a)', advance='no') i, ' '
  end do
  print *
contains
  logical function is_prime(n)
    integer, intent(in) :: n
    ! أكمل
    is_prime = .true.
  end function is_prime
end program primes
```

```fortran solution
program primes
  implicit none
  integer :: i
  do i = 2, 30
    if (is_prime(i)) write(*, '(i0, a)', advance='no') i, ' '
  end do
  print *
contains
  logical function is_prime(n)
    integer, intent(in) :: n
    integer :: d
    is_prime = n >= 2
    do d = 2, int(sqrt(real(n)))
      if (mod(n, d) == 0) then
        is_prime = .false.
        return
      end if
    end do
  end function is_prime
end program primes
```

```text output
2 3 5 7 11 13 17 19 23 29 
```

### التمرين 2

اكتب إجراء `scale(v, k)` يضرب كل عناصر المصفوفة `v` في `k` (المصفوفة `intent(inout)`):

```fortran exercise
program scaling
  implicit none
  real(8) :: v(3)
  v = [1d0, 2d0, 3d0]
  call scale(v, 10d0)
  print '(3f6.1)', v
contains
  ! اكتب subroutine scale هنا
end program scaling
```

```fortran solution
program scaling
  implicit none
  real(8) :: v(3)
  v = [1d0, 2d0, 3d0]
  call scale(v, 10d0)
  print '(3f6.1)', v
contains
  subroutine scale(v, k)
    real(8), intent(inout) :: v(:)
    real(8), intent(in) :: k
    v = v * k
  end subroutine scale
end program scaling
```

```text output
  10.0  20.0  30.0
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين function وsubroutine؟", "choices": ["لا فرق", "الدالة ترجع قيمة وتُستخدم في تعبير، والإجراء يُستدعى بـ call", "الإجراء أسرع", "الدالة لا تأخذ معاملات"], "answer": 1, "explanation": "function ترجع قيمة، وsubroutine تُستدعى بـ call ويمكنها تعديل معاملاتها."}
```

```quiz
{"question": "ماذا تعني intent(in)؟", "choices": ["المعامل للقراءة فقط", "المعامل للكتابة فقط", "المعامل اختياري", "المعامل مصفوفة"], "answer": 0, "explanation": "intent(in) تمنع تعديل المعامل داخل الإجراء."}
```

```quiz
{"question": "كيف تستخدم وحدة اسمها geometry في برنامجك؟", "choices": ["#include geometry", "import geometry", "use geometry", "call geometry"], "answer": 2, "explanation": "use geometry بعد سطر program مباشرة."}
```

## الخلاصة

- `function` ترجع قيمة، و`subroutine` تُستدعى بـ `call`، وكلاهما بعد `contains`.
- المعاملات تُمرر بالمرجع، و`intent(in/out/inout)` توضح المقصود.
- `module` + `use` لتقسيم المشروع إلى ملفات، و`only` لاستيراد أسماء محددة.
- `recursive` للدوال التي تستدعي نفسها.
