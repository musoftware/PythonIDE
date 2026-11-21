# الدرس 4: حلقات التكرار `do`

لو أردت طباعة جدول الضرب للرقم 7، هل ستكتب عشرة أسطر `print`؟ بالطبع لا! **حلقة التكرار** تنفذ نفس التعليمات عدة مرات. وفي Fortran كل الحلقات تبدأ بالكلمة **`do`**.

> **تشبيه:** الحلقة مثل **عداد اللفات** في سباق الجري: «اجرِ لفة، زد العداد، وإذا لم تصل إلى 10 لفات فاجرِ لفة أخرى».

## حلقة العد `do i = بداية, نهاية`

```fortran run
program table
  implicit none
  integer :: i
  do i = 1, 5
    print '(i0, a, i0)', i, ' x 7 = ', i * 7
  end do
end program table
```

```text output
1 x 7 = 7
2 x 7 = 14
3 x 7 = 21
4 x 7 = 28
5 x 7 = 35
```

- `i` يبدأ من 1، وبعد كل دورة يزيد 1، وتتوقف الحلقة بعد 5 (**النهاية مشمولة**).
- متغير الحلقة يجب أن يكون `integer` ومعرّفًا في الأعلى.

### الخطوة

يمكن تحديد مقدار الزيادة بعدد ثالث، وحتى العد التنازلي:

```fortran run
program steps
  implicit none
  integer :: i
  do i = 0, 20, 5
    write(*, '(i0, a)', advance='no') i, ' '
  end do
  print *
  do i = 5, 1, -1
    write(*, '(i0, a)', advance='no') i, ' '
  end do
  print '(a)', 'Go!'
end program steps
```

```text output
0 5 10 15 20 
5 4 3 2 1 Go!
```

`write(*, صيغة, advance='no')` تطبع **بدون** الانتقال لسطر جديد، فنضع الأرقام بجوار بعضها. و`print *` وحدها تطبع سطرًا فارغًا (تنهي السطر).

## جمع الأرقام: نمط «المجمِّع»

```fortran run
program total
  implicit none
  integer :: i, s
  s = 0
  do i = 1, 100
    s = s + i
  end do
  print '(a, i0)', '1 + 2 + ... + 100 = ', s
end program total
```

```text output
1 + 2 + ... + 100 = 5050
```

> **تذكر:** ابدأ المجمِّع بصفر **قبل** الحلقة. في Fortran المتغير غير المهيأ قد يحتوي أي قيمة عشوائية!

## الحلقة الشرطية `do while`

تستمر ما دام الشرط صحيحًا. مفيدة عندما لا نعرف عدد الدورات مسبقًا:

```fortran run
program doubling
  implicit none
  integer :: money, years
  money = 1000
  years = 0
  do while (money < 10000)
    money = money * 2
    years = years + 1
  end do
  print '(a, i0, a, i0)', 'After ', years, ' years: ', money
end program doubling
```

```text output
After 4 years: 16000
```

## `exit` و`cycle`

- `exit`: اخرج من الحلقة فورًا.
- `cycle`: اترك باقي هذه الدورة وانتقل للدورة التالية.

ومع `do` بدون شروط نصنع حلقة لا تنتهي إلا بـ `exit`:

```fortran run
program sumpos
  implicit none
  integer :: x, s
  s = 0
  do
    read *, x
    if (x == 0) exit          ! الصفر يعني «انتهيت»
    if (x < 0) cycle          ! نتجاهل السالب
    s = s + x
  end do
  print '(a, i0)', 'Sum of positives = ', s
end program sumpos
```

```text input
5
-3
10
-1
7
0
```

```text output
Sum of positives = 22
```

## حلقات متداخلة: مثلث النجوم

```fortran run
program stars
  implicit none
  integer :: row, col
  do row = 1, 4
    do col = 1, row
      write(*, '(a)', advance='no') '*'
    end do
    print *
  end do
end program stars
```

```text output
*
**
***
****
```

## أخطاء شائعة

- **نسيان `end do`:** خطأ `Expecting END PROGRAM statement` أو `END DO statement expected`.
- **تغيير متغير الحلقة داخلها:** `i = i + 1` داخل `do i = ...` خطأ ترجمة في Fortran. استخدم `do while` إن احتجت التحكم يدويًا.
- **حلقة لا تنتهي:** في `do while` نسيت تغيير المتغير الذي في الشرط. أوقف البرنامج بزر **Stop** (أو **Shift+F5**).
- **مجمِّع غير مهيأ:** نتيجة عشوائية. اكتب `s = 0` قبل الحلقة.

## تمارين

### التمرين 1

احسب مضروب الرقم 6 (6! = 1 × 2 × 3 × 4 × 5 × 6) بحلقة `do`:

```fortran exercise
program fact
  implicit none
  integer :: i, f
  ! أكمل
  print '(a, i0)', '6! = ', f
end program fact
```

```fortran solution
program fact
  implicit none
  integer :: i, f
  f = 1
  do i = 1, 6
    f = f * i
  end do
  print '(a, i0)', '6! = ', f
end program fact
```

```text output
6! = 720
```

### التمرين 2

اطبع الأعداد من 1 إلى 20 التي تقبل القسمة على 3، في سطر واحد، باستخدام `cycle`:

```fortran exercise
program threes
  implicit none
  integer :: i
  do i = 1, 20
    ! أكمل
  end do
  print *
end program threes
```

```fortran solution
program threes
  implicit none
  integer :: i
  do i = 1, 20
    if (mod(i, 3) /= 0) cycle
    write(*, '(i0, a)', advance='no') i, ' '
  end do
  print *
end program threes
```

```text output
3 6 9 12 15 18 
```

## اختبر نفسك

```quiz
{"question": "كم مرة تتكرر الحلقة do i = 1, 10, 3؟", "choices": ["3", "4", "10", "مرة واحدة"], "answer": 1, "explanation": "قيم i هي 1 و4 و7 و10، أي 4 مرات."}
```

```quiz
{"question": "ماذا تفعل cycle داخل الحلقة؟", "choices": ["تخرج من الحلقة", "تنتقل للدورة التالية مباشرة", "تعيد الحلقة من البداية", "توقف البرنامج"], "answer": 1, "explanation": "cycle تتخطى باقي الدورة الحالية فقط."}
```

```quiz
{"question": "كيف تطبع دون الانتقال لسطر جديد؟", "choices": ["print *, x, ;", "write(*, '(a)', advance='no') x", "print no x", "لا يمكن"], "answer": 1, "explanation": "advance='no' تبقي المؤشر على نفس السطر."}
```

## الخلاصة

- `do i = a, b [, خطوة]` للعد، والنهاية مشمولة.
- `do while (شرط)` للتكرار ما دام الشرط صحيحًا، و`do` وحدها مع `exit` لحلقة مفتوحة.
- `exit` للخروج، و`cycle` للدورة التالية.
- `advance='no'` للطباعة على نفس السطر.
