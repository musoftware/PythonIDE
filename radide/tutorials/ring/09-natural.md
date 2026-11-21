# الدرس 9: الوراثة والأقواس وأساسيات البرمجة الطبيعية

**في هذا الدرس ستتعلم:**

- **الوراثة** (inheritance) بالكلمة `from`، واستدعاء دالة الأب بـ `super`.
- دوال **الضبط والقراءة** (setters / getters) التلقائية.
- ما يحدث داخل الأقواس `{ }`: `braceStart` و`braceEnd` و`braceExprEval`.
- كيف تكتب «لغة صغيرة» قريبة من كلام البشر: **البرمجة الطبيعية** (Natural Programming).

## الوراثة: `from`

**الوراثة** أن يأخذ صنف جديد كل ما في صنف موجود، ثم يضيف إليه أو يغيّر فيه. الصنف الأصلي يسمى **الأب** (parent)، والجديد يسمى **الابن** (child).

> **تشبيه:** الابن يرث من أبيه لون العينين وطريقة الكلام، لكنه قد يتعلم مهارات جديدة لا يعرفها الأب.

```ring run
aAnimals = [new Dog { cName = "ريكس" }, new Cat { cName = "مشمش" }, new Animal { cName = "حيوان" }]
for oA in aAnimals
    oA.speak()
next

class Animal
    cName = ""
    func speak
        see cName + ": ..." + nl

class Dog from Animal
    func speak
        see cName + ": هاو هاو!" + nl

class Cat from Animal
    func speak
        see cName + ": مياو!" + nl
```

```text output
ريكس: هاو هاو!
مشمش: مياو!
حيوان: ...
```

كل كائن نفّذ نسخته الخاصة من `speak()`؛ وهذا ما يسمى **تعدد الأشكال** (polymorphism).

### `super`: استدعاء دالة الأب

```ring run
oM = new Manager { cName = "هالة"  nSalary = 9000  nBonus = 2000 }
oM.info()

class Employee
    cName = ""
    nSalary = 0
    func info
        see "الموظف: " + cName + nl
        see "الراتب: " + nSalary + nl

class Manager from Employee
    nBonus = 0
    func info
        super.info()           # نفّذ دالة الأب أولًا
        see "المكافأة: " + nBonus + nl
```

```text output
الموظف: هالة
الراتب: 9000
المكافأة: 2000
```

## دوال الضبط والقراءة التلقائية

إذا كان في الصنف خاصية اسمها `age`، ودالة اسمها `setAge`، فإن Ring تستدعي `setAge` **تلقائيًا** كلما كتبت `o.age = قيمة`. وبالمثل تستدعي `getAge` عند قراءة `o.age`. هذا يسمح لنا بفحص القيم وحسابها:

```ring run
oT = new Temperature
oT.celsius = 100
see "100 مئوية = " + oT.fahrenheit + " فهرنهايت" + nl
oT.celsius = -500

class Temperature
    celsius = 0
    fahrenheit = 0

    func setCelsius n
        if n < -273
            see "خطأ: لا توجد درجة حرارة أقل من -273" + nl
            return
        ok
        celsius = n

    func getFahrenheit
        return celsius * 9 / 5 + 32
```

```text output
100 مئوية = 212 فهرنهايت
خطأ: لا توجد درجة حرارة أقل من -273
```

## ماذا يحدث داخل الأقواس؟

عرفنا في الدرس السابق أن `oObject { ... }` تدخلنا إلى الكائن. وRing تعطي الصنف فرصة للتدخل:

| الدالة في الصنف | متى تُستدعى |
|---|---|
| `braceStart` | عند فتح القوس `{` |
| `braceEnd` | عند إغلاق القوس `}` |
| `braceExprEval value` | بعد كل تعبير يُكتب وحده في سطر داخل الأقواس، ومعها قيمته |

```ring run
new Report {
    see "محتوى التقرير" + nl
    42
}

class Report
    func braceStart
        see "===== بداية =====" + nl
    func braceExprEval value
        see "قيمة وصلت: " + value + nl
    func braceEnd
        see "===== نهاية =====" + nl
```

```text output
===== بداية =====
محتوى التقرير
قيمة وصلت: 42
===== نهاية =====
```

## البرمجة الطبيعية: الفكرة

الآن اجمع ما تعلمناه:

1. داخل الأقواس، كتابة اسم خاصية وحدها مثل `forward` **تقرأ** الخاصية، فتستدعي Ring دالة `getForward` إن وُجدت.
2. وكتابة `speed = 5` **تضبط** الخاصية، فتُستدعى `setSpeed`.
3. والكلمات في السطر الواحد تُنفذ بالترتيب من اليسار إلى اليمين.

إذن السطر `move forward` داخل الأقواس يعني: اقرأ `move` ثم اقرأ `forward`. وإذا كتبنا دالتي `getMove` و`getForward`، صار عندنا أمر يُقرأ كالإنجليزية تمامًا!

```ring run
new Robot {
    move forward
    turn left
    move forward
    speed = 5
}

class Robot
    # الكلمات التي سنستخدمها كأوامر (خصائص)
    move forward turn left speed
    cAction = ""

    func getMove
        cAction = "move"
    func getTurn
        cAction = "turn"
    func getForward
        if cAction = "move" see "الروبوت يتقدم خطوة" + nl ok
    func getLeft
        if cAction = "turn" see "الروبوت يدور لليسار" + nl ok
    func setSpeed n
        see "السرعة الآن: " + n + nl
```

```text output
الروبوت يتقدم خطوة
الروبوت يدور لليسار
الروبوت يتقدم خطوة
السرعة الآن: 5
```

> **تشبيه:** كأنك علّمت Ring كلمات جديدة. كل كلمة (خاصية) لها «معنى» (دالة get). عندما تكتب الكلمات متتالية، تنفذ Ring معانيها بالترتيب.

### الأرقام داخل الجمل

باستخدام `braceExprEval` نستطيع التقاط الأرقام المكتوبة بين الكلمات:

```ring run
new ShoppingList {
    buy 3 apples
    buy 2 bananas
    show the list
}

class ShoppingList
    buy apples bananas show the list
    nCount = 0
    aItems = []

    func braceExprEval value
        if isnumber(value) nCount = value ok

    func getApples
        add(aItems, "" + nCount + " تفاحات")
    func getBananas
        add(aItems, "" + nCount + " موزات")
    func getList
        see "قائمة المشتريات:" + nl
        for c in aItems
            see "- " + c + nl
        next
```

```text output
قائمة المشتريات:
- 3 تفاحات
- 2 موزات
```

هذا الأسلوب يُستخدم في Ring لبناء **لغات خاصة بمجال معيّن** (DSL)، مثل وصف الواجهات أو الألعاب أو التقارير بجمل قريبة من كلام البشر. وفي Ring مكتبة كاملة اسمها **Natural Library** (`load "naturallib.ring"`) لبناء لغات طبيعية أكبر؛ تجد أمثلتها في معرض أمثلة Ring (الدرس 15).

> **لماذا عرّفنا `the` و`show` كخصائص؟** لأن كل كلمة داخل الأقواس لا بد أن تكون معروفة، وإلا ظهر خطأ «Using uninitialized variable». الكلمات التي لا تفعل شيئًا (مثل `the`) نعرّفها خصائص بلا دوال.

## أخطاء شائعة

- **نسيان `from` في الوراثة:** `class Dog Animal` لا تعني الوراثة، بل تعرّف خاصية اسمها `Animal`!
- **كلمة غير معرّفة داخل جملة طبيعية:** كل كلمة يجب أن تكون خاصية في الصنف.
- **اسم الدالة لا يطابق اسم الخاصية:** للخاصية `speed` اكتب `setSpeed` و`getSpeed` (حالة الأحرف لا تهم).

## تمارين

### التمرين 1: الأشكال

أنشئ صنفًا أبًا `Shape` فيه دالة `area()` تُرجع 0، وصنفين ابنين: `Square` (فيه `nSide`) و`Circle` (فيه `nRadius`، والمساحة `3 * nRadius * nRadius` للتبسيط). اطبع مساحة كل شكل في القائمة.

```ring exercise
aShapes = [new Square { nSide = 4 }, new Circle { nRadius = 2 }]
for oS in aShapes
    see classname(oS) + ": " + oS.area() + nl
next

class Shape
    func area
        return 0
# أكمل الصنفين Square و Circle
```

```ring solution
aShapes = [new Square { nSide = 4 }, new Circle { nRadius = 2 }]
for oS in aShapes
    see classname(oS) + ": " + oS.area() + nl
next

class Shape
    func area
        return 0

class Square from Shape
    nSide = 0
    func area
        return nSide * nSide

class Circle from Shape
    nRadius = 0
    func area
        return 3 * nRadius * nRadius
```

```text output
square: 16
circle: 12
```

### التمرين 2: المصباح الطبيعي

اكتب صنفًا `Lamp` بحيث تطبع الجملتان `turn lightOn` و`turn lightOff` داخل الأقواس: `المصباح يعمل` ثم `المصباح مطفأ`.

```ring exercise
new Lamp {
    turn lightOn
    turn lightOff
}

class Lamp
    turn lightOn lightOff
    # أضف دالتي getLightOn و getLightOff
```

```ring solution
new Lamp {
    turn lightOn
    turn lightOff
}

class Lamp
    turn lightOn lightOff
    func getLightOn
        see "المصباح يعمل" + nl
    func getLightOff
        see "المصباح مطفأ" + nl
```

```text output
المصباح يعمل
المصباح مطفأ
```

لماذا لم نكتب `turn on` و`turn off` ببساطة؟ لأن `on` و`off` من الكلمات المحجوزة في Ring (تُستخدمان في `switch`). عند تصميم لغة طبيعية اختر كلمات ليست محجوزة.

## اختبر نفسك

```quiz
{"question": "بأي كلمة نجعل صنفًا يرث من صنف آخر؟", "choices": ["extends", "from", "inherits", ":"], "answer": 1, "explanation": "class Dog from Animal تعني أن Dog يرث من Animal."}
```

```quiz
{"question": "إذا كتبنا `o.age = 5` وكان في الصنف دالة setAge، ماذا يحدث؟", "choices": ["خطأ", "تُستدعى setAge تلقائيًا ومعها 5", "تُتجاهل setAge", "تُحذف الخاصية"], "answer": 1, "explanation": "Ring تستدعي setter تلقائيًا عند ضبط الخاصية."}
```

```quiz
{"question": "ما الذي يجعل `move forward` داخل الأقواس يعمل كأمر؟", "choices": ["دوال getMove و getForward في الصنف", "مكتبة خارجية إجبارية", "علامات التنصيص", "الكلمة see"], "answer": 0, "explanation": "قراءة الخاصية داخل الأقواس تستدعي دالة get الخاصة بها."}
```

## الخلاصة

- `class B from A` للوراثة، و`super.method()` لاستدعاء دالة الأب.
- `setX` و`getX` تُستدعيان تلقائيًا عند ضبط الخاصية `x` أو قراءتها.
- `braceStart` و`braceEnd` و`braceExprEval` تتحكم فيما يحدث داخل `{ }`.
- البرمجة الطبيعية = خصائص كلمات + دوال get + الأقواس.
