# الدرس 7: النصوص والملفات

Fortran لغة أرقام قبل كل شيء، لكن أي برنامج حقيقي يحتاج النصوص: أسماء، رسائل، أسطر من ملف. وفي هذا الدرس نتعلم أيضًا **حفظ النتائج في ملف** وقراءتها، وهذا ما تفعله البرامج العلمية دائمًا مع البيانات.

## النصوص ثابتة الطول

```fortran run
program strings
  implicit none
  character(len=10) :: first, last
  character(len=30) :: full

  first = 'Ali'
  last = 'Hassan'
  full = trim(first) // ' ' // trim(last)    ! // تعني دمج النصوص

  print '(a)', '[' // first // ']'
  print '(a)', '[' // trim(full) // ']'
  print '(a, i0)', 'len      = ', len(first)
  print '(a, i0)', 'len_trim = ', len_trim(first)
end program strings
```

```text output
[Ali       ]
[Ali Hassan]
len      = 10
len_trim = 3
```

- `character(len=10)` نص طوله **دائمًا** 10؛ القيمة الأقصر تُكمل بمسافات.
- `//` تدمج النصوص.
- `trim` تحذف المسافات من اليمين، و`len_trim` طول النص بدونها.

> **تشبيه:** `character(len=10)` مثل **علبة بيض فيها 10 خانات**: لو وضعت 3 بيضات تبقى العلبة بطول 10 خانات، والباقي فارغ. و`trim` تقص العلبة على قدر البيض.

## النصوص متغيرة الطول

في Fortran الحديثة يمكن أن يأخذ النص الطول المناسب تلقائيًا:

```fortran run
program dynstr
  implicit none
  character(len=:), allocatable :: s
  s = 'Fortran'
  print '(a, i0)', s // ' has length ', len(s)
  s = s // ' 2018'                ! يكبر النص تلقائيًا
  print '(a, i0)', s // ' has length ', len(s)
end program dynstr
```

```text output
Fortran has length 7
Fortran 2018 has length 12
```

## البحث والتقطيع

```fortran run
program search
  implicit none
  character(len=*), parameter :: text = 'hello world of fortran'
  integer :: p

  p = index(text, 'world')
  print '(a, i0)', 'world at ', p
  print '(a)', text(1:5)                ! من الحرف 1 إلى 5
  print '(a)', text(p:p+4)
  print '(a, i0)', 'missing: ', index(text, 'xyz')
  print '(a)', to_upper(text(1:5))
contains
  function to_upper(s) result(u)
    character(len=*), intent(in) :: s
    character(len=len(s)) :: u
    integer :: i
    u = s
    do i = 1, len(s)
      if (s(i:i) >= 'a' .and. s(i:i) <= 'z') u(i:i) = achar(iachar(s(i:i)) - 32)
    end do
  end function to_upper
end program search
```

```text output
world at 7
hello
world
missing: 0
HELLO
```

- `index(نص, جزء)` مكان الجزء، أو 0 إن لم يوجد.
- `text(a:b)` جزء من النص من الحرف `a` إلى `b`. والحرف الواحد `s(i:i)`.
- `iachar` تعطي رمز الحرف (ASCII)، و`achar` العكس.
- `character(len=*)` في المعامل: «نص بأي طول».

> **العربية:** النصوص في Fortran **بايتات**، والحرف العربي في UTF-8 يأخذ بايتين. لذلك `len('سلام')` تعطي 8 لا 4، والتقطيع `s(1:1)` يقطع نصف حرف! اطبع النص العربي كاملًا كما هو ولا تقطعه.

## تحويل الأرقام إلى نصوص وبالعكس

نستخدم `write` و`read` مع **متغير نصي** بدل الشاشة (يسمى internal file). انتبه: يجب أن يكون **متغيرًا** وليس نصًا مكتوبًا مباشرة:

```fortran run
program convert
  implicit none
  character(len=20) :: buf
  integer :: n, ios
  real(8) :: x

  write(buf, '(i0)') 2025                 ! رقم -> نص
  print '(a)', 'Year: ' // trim(buf)

  buf = '3.75'
  read(buf, *) x                           ! نص -> رقم
  print '(f0.2)', x * 2

  buf = '12abc'
  read(buf, *, iostat=ios) n               ! نص غير صالح
  if (ios /= 0) print '(a)', 'Not a number!'
end program convert
```

```text output
Year: 2025
7.50
Not a number!
```

`iostat=ios` تمنع توقف البرنامج عند الخطأ: إن نجحت القراءة تكون `ios` صفرًا، وإلا قيمة غير صفرية. استخدمها دائمًا مع مدخلات المستخدم.

## الكتابة في ملف والقراءة منه

```fortran run
program files
  implicit none
  integer :: u, i, ios
  real(8) :: x, y, total

  ! 1) الكتابة
  open(newunit=u, file='data.txt', status='replace', action='write')
  do i = 1, 5
    write(u, '(i0, 1x, f0.1)') i, i * 1.5d0
  end do
  close(u)

  ! 2) القراءة حتى نهاية الملف
  total = 0
  open(newunit=u, file='data.txt', status='old', action='read')
  do
    read(u, *, iostat=ios) x, y
    if (ios /= 0) exit                 ! نهاية الملف
    total = total + y
  end do
  close(u)
  print '(a, f0.1)', 'Total of column 2 = ', total
end program files
```

```text output
Total of column 2 = 22.5
```

| التعليمة | معناها |
|---|---|
| `open(newunit=u, file='x', ...)` | افتح الملف، وتختار Fortran رقم وحدة `u` حرًا |
| `status='replace'` | أنشئ ملفًا جديدًا (امسح القديم) |
| `status='old'` | الملف يجب أن يكون موجودًا |
| `write(u, صيغة) ...` | اكتب سطرًا في الملف |
| `read(u, *, iostat=ios) ...` | اقرأ سطرًا؛ `ios < 0` عند نهاية الملف |
| `close(u)` | أغلق الملف |

> **في الـ IDE:** يُنشأ `data.txt` في مجلد المشروع. افتحه من **Solution Explorer** (مستكشف الحلول) أو من **File > Open File...** لترى ما كتبه البرنامج.

## أخطاء شائعة

- **نسيان `trim`:** تظهر مسافات كثيرة في وسط الرسالة.
- **`Fortran runtime error: Cannot open file 'data.txt': No such file`:** `status='old'` والملف غير موجود. تأكد من الاسم والمجلد.
- **`End of file` يوقف البرنامج:** قرأت بعد نهاية الملف بدون `iostat`. أضف `iostat=ios` واخرج عندما تكون غير صفرية.
- **تقطيع نص عربي:** يظهر حرف مشوه. اطبع النص كاملًا.

## تمرين

### التمرين 1

اقرأ أسطرًا من المستخدم (كل سطر رقم)، واكتب كل رقم ومربعه في ملف `squares.txt`، ثم اقرأ الملف واطبع مجموع المربعات. توقف عن القراءة عند نهاية المدخلات:

```fortran exercise
program sq
  implicit none
  integer :: u, n, s, ios, total
  ! أكمل
end program sq
```

```fortran solution
program sq
  implicit none
  integer :: u, n, s, ios, total

  open(newunit=u, file='squares.txt', status='replace', action='write')
  do
    read(*, *, iostat=ios) n
    if (ios /= 0) exit
    write(u, '(i0, 1x, i0)') n, n * n
  end do
  close(u)

  total = 0
  open(newunit=u, file='squares.txt', status='old', action='read')
  do
    read(u, *, iostat=ios) n, s
    if (ios /= 0) exit
    total = total + s
  end do
  close(u)
  print '(a, i0)', 'Sum of squares = ', total
end program sq
```

```text input
1
2
3
4
```

```text output
Sum of squares = 30
```

## اختبر نفسك

```quiz
{"question": "ما الرمز الذي يدمج نصين في Fortran؟", "choices": ["+", "&", "//", ".."], "answer": 2, "explanation": "// هو عامل دمج النصوص."}
```

```quiz
{"question": "ماذا ترجع index('abcdef', 'cd')؟", "choices": ["2", "3", "0", "4"], "answer": 1, "explanation": "cd تبدأ عند الحرف الثالث، والترقيم من 1."}
```

```quiz
{"question": "لماذا نستخدم iostat=ios مع read؟", "choices": ["لتسريع القراءة", "لكي لا يتوقف البرنامج عند خطأ أو نهاية الملف ونعالج ذلك بأنفسنا", "لطباعة الأخطاء", "للكتابة في الملف"], "answer": 1, "explanation": "iostat تعطي رمز الحالة بدل إيقاف البرنامج."}
```

## الخلاصة

- `character(len=n)` نص ثابت الطول، و`character(len=:), allocatable` متغير الطول.
- `//` و`trim` و`len_trim` و`index` و`s(a:b)` لمعالجة النصوص.
- `write(buf, ...)` و`read(buf, *)` للتحويل بين الأرقام والنصوص.
- `open` و`write` و`read(..., iostat=)` و`close` للتعامل مع الملفات.
