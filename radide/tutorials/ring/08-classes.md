# الدرس 8: الأصناف والكائنات (Classes and Objects)

**في هذا الدرس ستتعلم:**

- ما هو **الصنف** (class) وما هو **الكائن** (object).
- تعريف الخصائص (attributes) والدوال الأعضاء (methods).
- إنشاء الكائن بـ `new`، والمُنشئ `init`.
- الوصول إلى الكائن بالأقواس المعقوصة `{ }`.
- الأعضاء الخاصة `private`.

## الصنف والكائن

- **الصنف** (class) هو **المخطط** أو القالب: يصف ما يملكه الشيء من بيانات وما يستطيع فعله.
- **الكائن** (object) نسخة حقيقية مصنوعة من هذا المخطط.

> **تشبيه:** الصنف مثل **قالب الكعك**، والكائنات هي **قطع الكعك**. القالب واحد، والقطع كثيرة، وكل قطعة يمكن أن تُزيَّن بشكل مختلف.

## أول صنف

```ring
class اسم_الصنف
    الخصائص (متغيرات)
    func دالة_عضو
        ...
```

مثل الدوال، يُكتب الصنف في **آخر** الملف، والكود الذي يستخدمه في الأعلى:

```ring run
oCar = new Car
oCar.cBrand = "نصر"
oCar.nSpeed = 0
oCar.accelerate(40)
oCar.accelerate(30)
oCar.show()

class Car
    cBrand = ""
    nSpeed = 0

    func accelerate n
        nSpeed += n

    func show
        see "السيارة " + cBrand + " تسير بسرعة " + nSpeed + " كم/س" + nl
```

```text output
السيارة نصر تسير بسرعة 70 كم/س
```

- `new Car` تنشئ كائنًا جديدًا من الصنف `Car`.
- النقطة `.` توصلك إلى خصائص الكائن ودواله: `oCar.nSpeed` و`oCar.show()`.
- داخل الدوال الأعضاء نكتب اسم الخاصية مباشرة (`nSpeed`) دون نقطة.

## المُنشئ `init`

الدالة `init` تُستدعى تلقائيًا عند إنشاء الكائن بـ `new` ومعه أقواس. نستخدمها لإعطاء القيم الأولى. ولا بد أن تنتهي بـ `return self`، أي «أرجع الكائن نفسه»:

```ring run
oAcc = new BankAccount("علي", 1000)
oAcc.deposit(500)
oAcc.withdraw(2000)
oAcc.withdraw(300)
oAcc.report()

class BankAccount
    cOwner = ""
    nBalance = 0

    func init cName, nStart
        cOwner = cName
        nBalance = nStart
        return self

    func deposit n
        nBalance += n

    func withdraw n
        if n > nBalance
            see "عذرًا، الرصيد لا يكفي لسحب " + n + nl
            return
        ok
        nBalance -= n

    func report
        see "صاحب الحساب: " + cOwner + "، الرصيد: " + nBalance + nl
```

```text output
عذرًا، الرصيد لا يكفي لسحب 2000
صاحب الحساب: علي، الرصيد: 1200
```

## الأقواس المعقوصة `{ }`

بدل كتابة اسم الكائن قبل كل خاصية، تستطيع **الدخول** إلى الكائن بالأقواس `{ }` والعمل عليه مباشرة. هذه من أجمل ميزات Ring:

```ring run
oPoint = new Point { x = 3  y = 4 }
see oPoint.distance()
see nl

oPoint {
    x = 6
    y = 8
    see "النقطة (" + x + ", " + y + ") تبعد " + distance() + nl
}

class Point
    x = 0
    y = 0
    func distance
        return sqrt(x * x + y * y)
```

```text output
5
النقطة (6, 8) تبعد 10
```

داخل `oPoint { ... }` كأنك أصبحت «داخل» الكائن: `x` تعني `oPoint.x`، و`distance()` تعني `oPoint.distance()`. سنرى في الدرس القادم أن هذه الفكرة هي أساس **البرمجة الطبيعية**.

## كائنات كثيرة في قائمة

```ring run
aStudents = [
    new Student { cName = "علي"   nGrade = 88 },
    new Student { cName = "سارة"  nGrade = 95 },
    new Student { cName = "يوسف"  nGrade = 72 }
]
for oS in aStudents
    oS.print()
next

class Student
    cName = ""
    nGrade = 0
    func print
        see cName + ": " + nGrade + " (" + status() + ")" + nl
    func status
        if nGrade >= 90 return "ممتاز" ok
        return "جيد"
```

```text output
علي: 88 (جيد)
سارة: 95 (ممتاز)
يوسف: 72 (جيد)
```

## الأعضاء الخاصة `private`

كل ما يُكتب بعد الكلمة `private` داخل الصنف لا يمكن الوصول إليه من خارج الصنف. هذا يحمي البيانات من التعديل الخاطئ (ويُسمى **التغليف** encapsulation):

```ring run
oSafe = new Safe
see oSafe.open("0000") + nl
see oSafe.open("1234") + nl

class Safe
    func open cCode
        if cCode = cSecret
            return "تم الفتح"
        ok
        return "رمز خاطئ"

    private
    cSecret = "1234"
```

```text output
رمز خاطئ
تم الفتح
```

لو حاولت كتابة `see oSafe.cSecret` لحصلت على الخطأ `R27 Using private attribute from outside the class`.

## الكائنات تُنسخ عند الإسناد

مثل القوائم، `o2 = o1` تعطيك **نسخة** مستقلة من الكائن:

```ring run
o1 = new Point { x = 1 }
o2 = o1
o2.x = 100
see "o1.x = " + o1.x + nl
see "o2.x = " + o2.x + nl

class Point
    x = 0
```

```text output
o1.x = 1
o2.x = 100
```

## معرفة معلومات عن الكائن

| الدالة | العمل |
|---|---|
| `classname(o)` | اسم صنف الكائن (بأحرف صغيرة) |
| `isobject(x)` | هل هو كائن؟ |
| `attributes(o)` | قائمة بأسماء الخصائص |
| `methods(o)` | قائمة بأسماء الدوال الأعضاء |

## أخطاء شائعة

- **نسيان `return self` في `init`:** فلا تحصل على الكائن كما تتوقع.
- **كتابة الصنف قبل الكود الرئيسي:** الكود بعد `class` يُعتبر جزءًا من الصنف.
- **استخدام خاصية غير معرّفة:** `oCar.nColor` بلا تعريف في الصنف يعطي الخطأ `R12 Error in property name, property not found`.
- **توقع أن `o2 = o1` يشير إلى نفس الكائن:** هو نسخة جديدة.
- **تسمية متغير باسم كلمة محجوزة:** لأن Ring لا تفرّق بين الأحرف الكبيرة والصغيرة، فالمتغير `oR` هو نفسه الكلمة `or`! والسطر `oR = new Rectangle` يعطي `C27 Syntax Error`. سمِّه `oRect` مثلًا. انتبه أيضًا لـ `oN` (= `on`) و`iN` (= `in`) و`tO` (= `to`).

## تمارين

### التمرين 1: المستطيل

أنشئ صنفًا `Rectangle` فيه `nWidth` و`nHeight`، ودالة `area()` ودالة `perimeter()`.

```ring exercise
oRect = new Rectangle { nWidth = 5  nHeight = 3 }
see "المساحة = " + oRect.area() + nl
see "المحيط = " + oRect.perimeter() + nl

class Rectangle
    # أكمل
```

```ring solution
oRect = new Rectangle { nWidth = 5  nHeight = 3 }
see "المساحة = " + oRect.area() + nl
see "المحيط = " + oRect.perimeter() + nl

class Rectangle
    nWidth = 0
    nHeight = 0
    func area
        return nWidth * nHeight
    func perimeter
        return 2 * (nWidth + nHeight)
```

```text output
المساحة = 15
المحيط = 16
```

### التمرين 2: العدّاد

أنشئ صنفًا `Counter` له مُنشئ يأخذ قيمة البداية، ودالتان `up()` و`down()`، ودالة `value()`.

```ring exercise
oC = new Counter(10)
oC.up()
oC.up()
oC.down()
see "القيمة: " + oC.value() + nl

class Counter
    # أكمل
```

```ring solution
oC = new Counter(10)
oC.up()
oC.up()
oC.down()
see "القيمة: " + oC.value() + nl

class Counter
    nValue = 0
    func init nStart
        nValue = nStart
        return self
    func up
        nValue++
    func down
        nValue--
    func value
        return nValue
```

```text output
القيمة: 11
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الصنف والكائن؟", "choices": ["لا علاقة بينهما", "الصنف مخطط، والكائن نسخة مصنوعة منه", "الكائن مخطط، والصنف نسخة منه", "هما نفس الشيء"], "answer": 1, "explanation": "الصنف هو القالب، والكائنات نسخ حقيقية منه."}
```

```quiz
{"question": "ماذا يجب أن تُرجع الدالة init؟", "choices": ["0", "true", "self", "لا شيء"], "answer": 2, "explanation": "init تنتهي بـ return self لتُرجع الكائن الجديد."}
```

```quiz
{"question": "ماذا يعني `oPoint { x = 5 }`؟", "choices": ["إنشاء صنف جديد", "الدخول إلى الكائن oPoint وتغيير خاصيته x", "تعريف دالة", "قائمة جديدة"], "answer": 1, "explanation": "الأقواس المعقوصة تفتح الكائن فنعمل على خصائصه ودواله مباشرة."}
```

## الخلاصة

- `class` لتعريف الصنف، و`new` لإنشاء الكائن، والنقطة للوصول إلى أعضائه.
- `init ... return self` هو المُنشئ.
- `o { ... }` للدخول إلى الكائن، و`private` لإخفاء الأعضاء.
- الكائنات تُنسخ عند الإسناد وتمر بالمرجع إلى الدوال.
