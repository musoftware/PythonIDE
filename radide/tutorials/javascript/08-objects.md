# الدرس 8: الكائنات وJSON والنصوص

**في هذا الدرس ستتعلم:**

- إنشاء **كائن** (object) بخصائص، وقراءتها وتعديلها.
- الدوال داخل الكائن (دوال الكائن methods).
- المرور على خصائص الكائن، ومصفوفة من الكائنات.
- **التفكيك** (destructuring) و**النشر** `...`.
- تحويل البيانات إلى **JSON** والعكس.
- أهم دوال النصوص.

## ما هو الكائن؟

المصفوفة تحفظ قيمًا مرقّمة، أما **الكائن** فيحفظ قيمًا لها **أسماء**. كل اسم مع قيمته يسمى **خاصية** (property).

> **تشبيه:** الكائن مثل **بطاقة الهوية**: فيها «الاسم: سارة»، «العمر: 22»، «المدينة: الجيزة». لكل معلومة عنوان واضح بدل رقم.

```js run
const student = {
    name: "سارة",
    age: 22,
    city: "الجيزة",
    passed: true,
};

console.log(student.name);
console.log(student["city"]);
student.age = 23;              // تعديل
student.email = "sara@example.com";   // إضافة خاصية جديدة
delete student.passed;         // حذف خاصية
console.log(student);
```

```text output
سارة
الجيزة
{ name: 'سارة', age: 23, city: 'الجيزة', email: 'sara@example.com' }
```

- نصل إلى الخاصية بالنقطة `student.name` أو بالأقواس `student["name"]`. الأقواس مفيدة عندما يكون اسم الخاصية في متغير.
- قراءة خاصية غير موجودة تعطي `undefined` ولا تعطي خطأ.

## دوال الكائن (methods)

```js run
const account = {
    owner: "خالد",
    balance: 500,
    deposit(amount) {
        this.balance += amount;
    },
    report() {
        return `رصيد ${this.owner}: ${this.balance} جنيه`;
    },
};

account.deposit(250);
console.log(account.report());
```

```text output
رصيد خالد: 750 جنيه
```

الكلمة `this` داخل دالة الكائن تعني «هذا الكائن نفسه»، فـ `this.balance` هي رصيد هذا الحساب.

## المرور على الخصائص

```js run
const prices = { tea: 10, coffee: 25, juice: 18 };

for (const key in prices) {
    console.log(key, "=", prices[key]);
}
console.log(Object.keys(prices));
console.log(Object.values(prices));
for (const [item, price] of Object.entries(prices)) {
    console.log(`${item}: ${price}`);
}
```

```text output
tea = 10
coffee = 25
juice = 18
[ 'tea', 'coffee', 'juice' ]
[ 10, 25, 18 ]
tea: 10
coffee: 25
juice: 18
```

## مصفوفة من الكائنات

هذا هو الشكل الأكثر شيوعًا للبيانات في البرامج الحقيقية (قائمة منتجات، قائمة طلاب...):

```js run
const products = [
    { name: "قلم", price: 5, stock: 120 },
    { name: "دفتر", price: 20, stock: 0 },
    { name: "حقيبة", price: 350, stock: 7 },
];

const available = products.filter((p) => p.stock > 0);
console.log(available.map((p) => p.name).join("، "));

const value = products.reduce((sum, p) => sum + p.price * p.stock, 0);
console.log("قيمة المخزون:", value);

const expensive = products.find((p) => p.price > 100);
console.log(expensive.name);
```

```text output
قلم، حقيبة
قيمة المخزون: 3050
حقيبة
```

## التفكيك والنشر

**التفكيك** يستخرج الخصائص إلى متغيرات في سطر واحد، و**النشر** `...` ينسخ الخصائص:

```js run
const user = { name: "ليلى", age: 30, role: "مديرة" };

const { name, role } = user;
console.log(name, "-", role);

const [first, second] = ["أ", "ب", "ج"];
console.log(first, second);

const updated = { ...user, age: 31, city: "دمياط" };
console.log(updated);
console.log(user.age);
```

```text output
ليلى - مديرة
أ ب
{ name: 'ليلى', age: 31, role: 'مديرة', city: 'دمياط' }
30
```

لاحظ أن `updated` نسخة جديدة، والكائن الأصلي `user` لم يتغير.

## JSON: لغة تبادل البيانات

**JSON** (JavaScript Object Notation) صيغة نصية لحفظ البيانات وإرسالها، تشبه كائنات JavaScript. تستخدمها كل المواقع تقريبًا لتبادل البيانات بين الخادم والمتصفح، وتستخدمها RAD IDE نفسها في ملفات المشاريع.

```js run
const book = { title: "تعلم البرمجة", pages: 250, tags: ["js", "node"] };

const text = JSON.stringify(book);          // كائن -> نص
console.log(text);
console.log(typeof text);

const back = JSON.parse(text);              // نص -> كائن
console.log(back.tags[1]);

console.log(JSON.stringify({ a: 1, b: [1, 2] }, null, 2));
```

```text output
{"title":"تعلم البرمجة","pages":250,"tags":["js","node"]}
string
node
{
  "a": 1,
  "b": [
    1,
    2
  ]
}
```

- `JSON.stringify(obj)` تحوّل الكائن إلى نص، والمعامل الثالث (`2`) يضيف مسافات لتنسيق جميل.
- `JSON.parse(text)` تحوّل النص إلى كائن. في JSON يجب أن تكون أسماء الخصائص والنصوص بين علامتي تنصيص مزدوجة `"`.

## أهم دوال النصوص

```js run
const s = "  Hello, JavaScript World  ";
const t = s.trim();
console.log(`[${t}]`);
console.log(t.toUpperCase());
console.log(t.toLowerCase());
console.log(t.includes("Java"));
console.log(t.startsWith("Hello"), t.endsWith("!"));
console.log(t.indexOf("World"));
console.log(t.slice(7, 17));
console.log(t.replace("World", "عالم"));
console.log("a-b-c".replaceAll("-", "+"));
console.log("7".padStart(3, "0"));
console.log("ها".repeat(3));
console.log("مرحبًا".length);
```

```text output
[Hello, JavaScript World]
HELLO, JAVASCRIPT WORLD
hello, javascript world
true
true false
18
JavaScript
Hello, JavaScript عالم
a+b+c
007
هاهاها
6
```

> **ملحوظة عن العربية:** `"مرحبًا".length` تعطي `6` لأن التنوين على الباء حرف مستقل في الحاسوب. التشكيل يُحسب حروفًا!

النصوص في JavaScript **لا تتغير**: كل هذه الدوال ترجع نصًا جديدًا ولا تعدّل الأصل.

## أخطاء شائعة

- **قراءة خاصية من `undefined`:** إن كان `user.address` غير موجود فإن `user.address.city` تعطي `TypeError: Cannot read properties of undefined`. استخدم السلسلة الاختيارية `user.address?.city` التي تعطي `undefined` بهدوء.
- **JSON غير صالح:** `JSON.parse("{name: 'x'}")` تعطي `SyntaxError` لأن JSON يحتاج علامات تنصيص مزدوجة حول الأسماء والنصوص.
- **نسخ الكائن بالإسناد:** `const b = a;` لا ينسخ الكائن، بل يجعل الاسمين يشيران إلى الكائن نفسه. للنسخ استخدم `{ ...a }`.

## تمارين

### التمرين 1

أنشئ كائن `car` فيه `brand` و`year` و`price`، ثم أضف خاصية `color`، واطبع جملة تصفه.

```js exercise
// الناتج المطلوب: سيارة تويوتا موديل 2020 لونها أبيض وسعرها 450000
```

```js solution
const car = { brand: "تويوتا", year: 2020, price: 450000 };
car.color = "أبيض";
console.log(`سيارة ${car.brand} موديل ${car.year} لونها ${car.color} وسعرها ${car.price}`);
```

```text output
سيارة تويوتا موديل 2020 لونها أبيض وسعرها 450000
```

### التمرين 2

من مصفوفة الطلاب، اطبع أسماء الناجحين (الدرجة 50 فأكثر) مرتبين حسب الدرجة تنازليًا، بالشكل `الاسم (الدرجة)`.

```js exercise
const students = [
    { name: "علي", mark: 45 },
    { name: "منى", mark: 88 },
    { name: "سعيد", mark: 67 },
    { name: "هالة", mark: 93 },
];
// هالة (93)
// منى (88)
// سعيد (67)
```

```js solution
const students = [
    { name: "علي", mark: 45 },
    { name: "منى", mark: 88 },
    { name: "سعيد", mark: 67 },
    { name: "هالة", mark: 93 },
];
const passed = students.filter((s) => s.mark >= 50).sort((a, b) => b.mark - a.mark);
for (const s of passed) {
    console.log(`${s.name} (${s.mark})`);
}
```

```text output
هالة (93)
منى (88)
سعيد (67)
```

### التمرين 3

عُدّ تكرار كل كلمة في الجملة وخزّنه في كائن، ثم اطبعه بـ `JSON.stringify`.

```js exercise
const sentence = "أنا أحب البرمجة وأنا أحب القراءة";
// {"أنا":1,"أحب":2,"البرمجة":1,"وأنا":1,"القراءة":1}
```

```js solution
const sentence = "أنا أحب البرمجة وأنا أحب القراءة";
const counts = {};
for (const w of sentence.split(" ")) {
    counts[w] = (counts[w] || 0) + 1;
}
console.log(JSON.stringify(counts));
```

```text output
{"أنا":1,"أحب":2,"البرمجة":1,"وأنا":1,"القراءة":1}
```

## اختبر نفسك

```quiz
{"question": "كيف تقرأ الخاصية `price` من الكائن `item`؟", "choices": ["`item(price)`", "`item.price`", "`item->price`", "`item::price`"], "answer": 1, "explanation": "نستخدم النقطة `item.price` أو الأقواس `item[\"price\"]`."}
```

```quiz
{"question": "ماذا تفعل `JSON.stringify`؟", "choices": ["تحوّل نص JSON إلى كائن", "تحوّل الكائن إلى نص بصيغة JSON", "تطبع الكائن", "تحذف خصائص الكائن"], "answer": 1, "explanation": "`stringify` من كائن إلى نص، و`parse` العكس."}
```

```quiz
{"question": "ما الذي تعطيه `\"abc\".toUpperCase()`؟", "choices": ["\"abc\"", "\"ABC\"", "\"Abc\"", "خطأ"], "answer": 1, "explanation": "تحوّل كل الحروف إلى حروف كبيرة وترجع نصًا جديدًا."}
```

## الخلاصة

- الكائن `{ اسم: قيمة, ... }` يجمع بيانات مترابطة، و`this` داخل دالة الكائن تعني الكائن نفسه.
- `Object.keys` و`Object.values` و`Object.entries` للمرور على الخصائص.
- التفكيك `const { a, b } = obj` والنشر `{ ...obj }`.
- `JSON.stringify` و`JSON.parse` للتحويل بين الكائنات والنصوص.
- دوال النصوص مثل `trim` و`includes` و`replace` و`padStart` ترجع نصًا جديدًا.
