# الدرس 9: الأصناف والكائنات (Classes)

**في هذا الدرس ستتعلم:**

- ما هو **الصنف** (class) ولماذا نحتاجه.
- **المُنشئ** `constructor` والخصائص والتوابع.
- الخصائص الخاصة `#` والخصائص المحسوبة `get` و`set`.
- **الوراثة** بـ `extends` و`super`.
- التوابع الثابتة `static`.

## لماذا الأصناف؟

في الدرس السابق أنشأنا كائن حساب بنكي واحدًا. لكن ماذا لو احتجنا إلى ألف حساب، كلها لها الخصائص والتوابع نفسها؟ نكتب **قالبًا** مرة واحدة، ونصنع منه ما نشاء من الكائنات.

> **تشبيه:** **الصنف** مثل **قالب الكعك**، و**الكائنات** هي الكعكات. القالب واحد، لكن يمكن أن تصنع منه كعكات كثيرة، ولكل كعكة حشوتها الخاصة.

## أول صنف

```js run
class Student {
    constructor(name, grade) {
        this.name = name;
        this.grade = grade;
    }

    introduce() {
        return `أنا ${this.name} في الصف ${this.grade}`;
    }
}

const s1 = new Student("يوسف", 3);
const s2 = new Student("مريم", 5);
console.log(s1.introduce());
console.log(s2.introduce());
console.log(s2.name);
```

```text output
أنا يوسف في الصف 3
أنا مريم في الصف 5
مريم
```

- `class Student { ... }` يعرّف الصنف. المتعارف عليه أن يبدأ اسم الصنف بحرف كبير.
- `constructor(...)` **المُنشئ**: دالة تُنفَّذ تلقائيًا عند إنشاء كائن جديد، ونضع فيها القيم الأولى للخصائص.
- `new Student("يوسف", 3)` تصنع كائنًا جديدًا من الصنف، ونسمّيه أيضًا **نسخة** (instance).
- `this` داخل الصنف تعني «الكائن الحالي».

## مثال: حساب بنكي

```js run
class BankAccount {
    #balance = 0;          // خاصية خاصة: لا يمكن الوصول إليها من خارج الصنف

    constructor(owner) {
        this.owner = owner;
    }

    deposit(amount) {
        if (amount <= 0) {
            console.log("المبلغ يجب أن يكون موجبًا");
            return;
        }
        this.#balance += amount;
    }

    withdraw(amount) {
        if (amount > this.#balance) {
            console.log("الرصيد غير كافٍ");
            return;
        }
        this.#balance -= amount;
    }

    get balance() {        // خاصية للقراءة فقط
        return this.#balance;
    }
}

const acc = new BankAccount("سلمى");
acc.deposit(1000);
acc.withdraw(300);
acc.withdraw(5000);
acc.deposit(-5);
console.log(`${acc.owner}: ${acc.balance}`);
```

```text output
الرصيد غير كافٍ
المبلغ يجب أن يكون موجبًا
سلمى: 700
```

- الخاصية التي يبدأ اسمها بـ `#` **خاصة** (private): لا يستطيع أحد من خارج الصنف أن يكتب `acc.#balance = 1000000`. هكذا نحمي البيانات من التعديل الخاطئ، وهذه الفكرة اسمها **التغليف** (encapsulation).
- `get balance()` تجعل `acc.balance` تُقرأ مثل الخاصية العادية، لكنها في الحقيقة دالة. ولأننا لم نكتب `set balance(...)` فلا يمكن تغييرها من الخارج.

## الوراثة: `extends` و`super`

**الوراثة** (inheritance) تعني أن نبني صنفًا جديدًا فوق صنف موجود، فيأخذ كل ما فيه ويضيف عليه أو يغيّره:

```js run
class Shape {
    constructor(name) {
        this.name = name;
    }
    area() {
        return 0;
    }
    describe() {
        return `${this.name}: المساحة ${this.area().toFixed(2)}`;
    }
}

class Rectangle extends Shape {
    constructor(w, h) {
        super("مستطيل");      // استدعاء مُنشئ الصنف الأب
        this.w = w;
        this.h = h;
    }
    area() {
        return this.w * this.h;
    }
}

class Circle extends Shape {
    constructor(r) {
        super("دائرة");
        this.r = r;
    }
    area() {
        return Math.PI * this.r ** 2;
    }
}

const shapes = [new Rectangle(3, 4), new Circle(1), new Shape("شكل مجهول")];
for (const sh of shapes) {
    console.log(sh.describe());
}
console.log(shapes[0] instanceof Shape);
```

```text output
مستطيل: المساحة 12.00
دائرة: المساحة 3.14
شكل مجهول: المساحة 0.00
true
```

- `class Rectangle extends Shape` تعني: المستطيل **نوع من** الأشكال.
- `super(...)` تستدعي مُنشئ الصنف الأب، ويجب استدعاؤها قبل استخدام `this`.
- عندما يكتب الصنف الابن تابعًا بالاسم نفسه (`area`) فإنه **يعيد تعريفه** (override). لاحظ أن `describe` المكتوبة مرة واحدة في `Shape` استدعت `area` الصحيحة لكل شكل. هذه الفكرة اسمها **تعدد الأشكال** (polymorphism).
- `instanceof` تسأل: هل هذا الكائن من هذا الصنف (أو من أبنائه)؟

## التوابع الثابتة `static`

التابع الثابت يخص الصنف نفسه، لا الكائنات، فنستدعيه باسم الصنف:

```js run
class Temperature {
    static toFahrenheit(c) {
        return c * 9 / 5 + 32;
    }
}
console.log(Temperature.toFahrenheit(25));
```

```text output
77
```

`Math.max` و`JSON.parse` و`Number.isInteger` كلها أمثلة على توابع ثابتة.

## `toString`: كيف يظهر كائنك نصًا

```js run
class Point {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
    toString() {
        return `(${this.x}, ${this.y})`;
    }
}
const p = new Point(3, -2);
console.log(`النقطة ${p}`);
console.log(p);
```

```text output
النقطة (3, -2)
Point { x: 3, y: -2 }
```

## أخطاء شائعة

- **نسيان `new`:** `const s = Student("x", 1);` تعطي `TypeError: Class constructor Student cannot be invoked without 'new'`.
- **نسيان `this`:** داخل التابع اكتب `this.name` لا `name` وحدها.
- **استخدام `this` قبل `super`:** في مُنشئ الصنف الابن يعطي `ReferenceError: Must call super constructor in derived class before accessing 'this'`.
- **الوصول إلى خاصية `#`:** من خارج الصنف يعطي خطأ صياغة (SyntaxError) قبل أن يعمل البرنامج.

## تمارين

### التمرين 1

اكتب صنفًا `Counter` فيه خاصية `count` تبدأ من 0، وتابعان: `increment()` يزيدها 1، و`reset()` يعيدها إلى 0.

```js exercise
// const c = new Counter();
// c.increment(); c.increment(); c.increment();
// console.log(c.count);   // 3
// c.reset();
// console.log(c.count);   // 0
```

```js solution
class Counter {
    constructor() {
        this.count = 0;
    }
    increment() {
        this.count++;
    }
    reset() {
        this.count = 0;
    }
}
const c = new Counter();
c.increment(); c.increment(); c.increment();
console.log(c.count);
c.reset();
console.log(c.count);
```

```text output
3
0
```

### التمرين 2

اكتب صنفًا `Animal` له `name` وتابع `speak()` يرجع `"... يصدر صوتًا"`، ثم صنفين يرثان منه: `Dog` يرجع `"... ينبح"`، و`Cat` يرجع `"... يموء"`. اطبع صوت كل حيوان في المصفوفة.

```js exercise
// const zoo = [new Dog("ركس"), new Cat("مشمش"), new Animal("ببغاء")];
// ركس ينبح
// مشمش يموء
// ببغاء يصدر صوتًا
```

```js solution
class Animal {
    constructor(name) {
        this.name = name;
    }
    speak() {
        return `${this.name} يصدر صوتًا`;
    }
}
class Dog extends Animal {
    speak() {
        return `${this.name} ينبح`;
    }
}
class Cat extends Animal {
    speak() {
        return `${this.name} يموء`;
    }
}
const zoo = [new Dog("ركس"), new Cat("مشمش"), new Animal("ببغاء")];
for (const a of zoo) {
    console.log(a.speak());
}
```

```text output
ركس ينبح
مشمش يموء
ببغاء يصدر صوتًا
```

## اختبر نفسك

```quiz
{"question": "متى يُنفَّذ `constructor`؟", "choices": ["عند تعريف الصنف", "عند إنشاء كائن جديد بـ `new`", "عند استدعاء أي تابع", "عند انتهاء البرنامج"], "answer": 1, "explanation": "المُنشئ يُنفَّذ تلقائيًا مرة واحدة لكل كائن جديد."}
```

```quiz
{"question": "ما معنى `class B extends A`؟", "choices": ["B نسخة من A", "B يرث كل خصائص A وتوابعه", "A يرث من B", "B و A صنفان لا علاقة بينهما"], "answer": 1, "explanation": "`extends` تعني الوراثة: الصنف B يبني فوق الصنف A."}
```

```quiz
{"question": "لماذا نبدأ اسم الخاصية بـ `#`؟", "choices": ["لتسريع البرنامج", "لجعلها خاصة لا يمكن الوصول إليها من خارج الصنف", "لجعلها ثابتة", "لطباعتها"], "answer": 1, "explanation": "`#` تجعل الخاصية خاصة بالصنف، وهذا هو التغليف."}
```

## الخلاصة

- `class` قالب، و`new` تصنع كائنًا منه، و`constructor` يجهّز خصائصه.
- `#` للخصائص الخاصة، و`get` لخاصية محسوبة.
- `extends` للوراثة، و`super(...)` لاستدعاء مُنشئ الأب، وإعادة تعريف التوابع تعطي تعدد الأشكال.
- `static` لتوابع تخص الصنف نفسه.
