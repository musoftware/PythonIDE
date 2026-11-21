# الدرس 13: مقدمة في TypeScript

**في هذا الدرس ستتعلم:**

- ما هي **TypeScript** ولماذا يحبها المبرمجون.
- كتابة **الأنواع** للمتغيرات والدوال.
- الواجهات `interface` والأنواع المخصصة `type`.
- الأنواع الاتحادية والاختيارية، و`enum`.
- الأصناف في TypeScript، والأنواع العامة (Generics) باختصار.
- كيف تشغّل RAD IDE ملفات `.ts`.

## ما هي TypeScript؟

**TypeScript** هي JavaScript **مع أنواع**. تكتب الكود نفسه الذي تعلمته، وتضيف إليه معلومات مثل «هذا المتغير عدد» و«هذه الدالة ترجع نصًا». ثم تتحول إلى JavaScript عادية قبل التشغيل.

> **تشبيه:** JavaScript مثل مطبخ بلا ملصقات على العلب: قد تضع الملح في الشاي بالخطأ ولا تكتشف ذلك إلا عند الشرب. TypeScript تضع **ملصقًا** على كل علبة، فينبهك المحرر قبل أن تخطئ: «هذه علبة ملح، لا سكر!».

الفائدة الكبرى: يكتشف المحرر كثيرًا من الأخطاء **أثناء الكتابة** بدل أن تظهر للمستخدم أثناء التشغيل، ويصبح الإكمال التلقائي (IntelliSense) أذكى بكثير. لذلك تستخدمها أغلب المشاريع الكبيرة مثل Angular وNestJS وVS Code.

## مشروع TypeScript في RAD IDE

1. **File > New Project** ثم **Web & Script > TypeScript**.
2. اختر **Console Application** (أو **Windows Application** لمشروع بنوافذ).
3. تكتب الكود في ملفات `.ts`، وعند التشغيل تحذف RAD IDE الأنواع بالمحوّل المدمج في Node.js 22 (يحتاج Node.js 22.13 أو أحدث)، ولا توجد خطوة بناء منفصلة.

> **مهم:** التشغيل لا يتحقق من الأنواع، بل يحذفها فقط. أخطاء الأنواع تظهر في المحرر (مع خادم لغة TypeScript)، ويمكنك فحص المشروع كله من الطرفية بالأمرين `npm install -D typescript` ثم `npx tsc --noEmit`. تنشئ RAD IDE الملف `tsconfig.json` في المشروع لهذا الغرض.

## أنواع المتغيرات

نكتب النوع بعد اسم المتغير ونقطتين `:`:

```ts run
let userName: string = "عمر";
let age: number = 28;
let isMember: boolean = true;
const scores: number[] = [90, 85, 77];
const tags: Array<string> = ["ts", "node"];

console.log(`${userName} (${age}) عضو: ${isMember}`);
console.log(scores.length, tags.join("+"));

let city = "طنطا";      // استنتاج النوع: TypeScript تعرف وحدها أنه string
console.log(typeof city);
```

```text output
عمر (28) عضو: true
3 ts+node
string
```

لا تحتاج إلى كتابة النوع في كل مكان: إن أعطيت المتغير قيمة أولى **تستنتج** TypeScript نوعه وحدها. ولو كتبت بعدها `city = 5;` لظهر خط أحمر في المحرر: `Type 'number' is not assignable to type 'string'`.

## أنواع الدوال

```ts run
function add(a: number, b: number): number {
    return a + b;
}

const greet = (name: string, title: string = "أستاذ"): string => `أهلًا ${title} ${name}`;

function log(message: string): void {     // void: لا ترجع شيئًا
    console.log("[LOG]", message);
}

console.log(add(2, 3));
console.log(greet("هاني"));
console.log(greet("نادية", "دكتورة"));
log("تم الحفظ");
```

```text output
5
أهلًا أستاذ هاني
أهلًا دكتورة نادية
[LOG] تم الحفظ
```

لو كتبت `add("2", 3)` يرفضها المحرر فورًا، بينما في JavaScript كانت ستعطي `"23"` بصمت!

## الواجهات `interface` والأنواع `type`

**الواجهة** (interface) تصف شكل الكائن: ما خصائصه وما نوع كل منها:

```ts run
interface Product {
    id: number;
    name: string;
    price: number;
    discount?: number;          // ? تعني: خاصية اختيارية
}

function finalPrice(p: Product): number {
    const d = p.discount ?? 0;
    return p.price - p.price * d / 100;
}

const items: Product[] = [
    { id: 1, name: "سماعة", price: 400, discount: 25 },
    { id: 2, name: "شاحن", price: 150 },
];

for (const it of items) {
    console.log(`${it.name}: ${finalPrice(it)}`);
}
```

```text output
سماعة: 300
شاحن: 150
```

و`type` تعطي اسمًا لأي نوع، وأشهر استخدام لها **الأنواع الاتحادية** (union) بالعلامة `|`، أي «واحد من هذه»:

```ts run
type Status = "pending" | "paid" | "shipped";
type Id = number | string;

function statusText(s: Status): string {
    switch (s) {
        case "pending": return "في الانتظار";
        case "paid": return "مدفوع";
        case "shipped": return "تم الشحن";
    }
}

function showId(id: Id): string {
    return typeof id === "number" ? `#${id.toString().padStart(4, "0")}` : id.toUpperCase();
}

console.log(statusText("paid"));
console.log(showId(42));
console.log(showId("ab-7"));
```

```text output
مدفوع
#0042
AB-7
```

لو كتبت `statusText("lost")` يرفضها المحرر لأن `"lost"` ليست من القيم المسموحة. وداخل `showId` تعرف TypeScript بعد فحص `typeof` أن `id` عدد في فرع ونص في الآخر.

## التعداد `enum`

```ts run
enum Direction {
    Up,
    Down,
    Left,
    Right,
}

enum Color {
    Red = "أحمر",
    Green = "أخضر",
}

const move: Direction = Direction.Left;
console.log(move, Direction[move]);
console.log(Color.Green);
```

```text output
2 Left
أخضر
```

## الأصناف في TypeScript

```ts run
class Account {
    private balance: number = 0;

    constructor(public readonly owner: string) {}

    deposit(amount: number): void {
        if (amount <= 0) throw new Error("مبلغ غير صالح");
        this.balance += amount;
    }

    getBalance(): number {
        return this.balance;
    }
}

const acc = new Account("رامي");
acc.deposit(300);
acc.deposit(200);
console.log(`${acc.owner}: ${acc.getBalance()}`);
```

```text output
رامي: 500
```

- `private` تمنع الوصول إلى الخاصية من خارج الصنف (في المحرر). و`readonly` تمنع تغييرها بعد الإنشاء.
- `constructor(public readonly owner: string) {}` اختصار يعرّف الخاصية `owner` ويضع فيها القيمة في سطر واحد.

## الأنواع العامة (Generics) باختصار

أحيانًا تعمل الدالة مع أي نوع، لكنك تريد أن «تتذكر» النوع. نكتب متغير النوع بين `< >`:

```ts run
function firstItem<T>(items: T[]): T | undefined {
    return items[0];
}

const n = firstItem([10, 20, 30]);      // n من النوع number
const s = firstItem(["أ", "ب"]);        // s من النوع string
console.log(n, s);
```

```text output
10 أ
```

## أخطاء شائعة

- **استخدام `any` في كل مكان:** النوع `any` يطفئ فحص الأنواع ويُفقدك فائدة TypeScript. استخدمه نادرًا جدًا.
- **نسيان أن الأنواع تختفي عند التشغيل:** لا تستطيع كتابة `if (x instanceof Product)` لأن `Product` واجهة لا وجود لها في JavaScript الناتجة. افحص الخصائص بدلًا منها.
- **الاعتماد على التشغيل لاكتشاف أخطاء الأنواع:** في RAD IDE يعمل البرنامج حتى مع وجود أخطاء أنواع. راقب الخطوط الحمراء في المحرر، أو استخدم `npx tsc --noEmit`.
- **إصدار Node.js قديم:** تشغيل `.ts` مباشرة يحتاج Node.js 22.13 أو أحدث، وإلا ثبّت الحزمة `typescript` في المشروع.

## تمارين

### التمرين 1

عرّف واجهة `Book` فيها `title` و`author` و`year`، ثم اكتب دالة `describe(b: Book): string` واطبع وصف كتابين.

```ts exercise
// interface Book { ... }
// الأيام - طه حسين (1929)
// زقاق المدق - نجيب محفوظ (1947)
```

```ts solution
interface Book {
    title: string;
    author: string;
    year: number;
}

function describe(b: Book): string {
    return `${b.title} - ${b.author} (${b.year})`;
}

const books: Book[] = [
    { title: "الأيام", author: "طه حسين", year: 1929 },
    { title: "زقاق المدق", author: "نجيب محفوظ", year: 1947 },
];
books.forEach((b) => console.log(describe(b)));
```

```text output
الأيام - طه حسين (1929)
زقاق المدق - نجيب محفوظ (1947)
```

### التمرين 2

اكتب دالة `average(values: number[]): number` ترجع المتوسط، وترجع `0` للمصفوفة الفارغة.

```ts exercise
// console.log(average([4, 8, 9]));  // 7
// console.log(average([]));         // 0
```

```ts solution
function average(values: number[]): number {
    if (values.length === 0) return 0;
    return values.reduce((s, v) => s + v, 0) / values.length;
}
console.log(average([4, 8, 9]));
console.log(average([]));
```

```text output
7
0
```

### التمرين 3

عرّف النوع `Shape` اتحادًا من كائنين: دائرة `{ kind: "circle"; r: number }` ومربع `{ kind: "square"; side: number }`، واكتب دالة `area(s: Shape)` تستخدم `switch` على `kind`.

```ts exercise
// type Shape = ...
// 28.27
// 16.00
```

```ts solution
type Shape = { kind: "circle"; r: number } | { kind: "square"; side: number };

function area(s: Shape): number {
    switch (s.kind) {
        case "circle": return Math.PI * s.r ** 2;
        case "square": return s.side * s.side;
    }
}

console.log(area({ kind: "circle", r: 3 }).toFixed(2));
console.log(area({ kind: "square", side: 4 }).toFixed(2));
```

```text output
28.27
16.00
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين TypeScript وJavaScript؟", "choices": ["لغتان لا علاقة بينهما", "TypeScript هي JavaScript مضافًا إليها الأنواع، وتتحول إلى JavaScript قبل التشغيل", "JavaScript أحدث من TypeScript", "TypeScript تعمل في المتصفح بدون تحويل"], "answer": 1, "explanation": "كل كود JavaScript صالح تقريبًا هو كود TypeScript، والأنواع تُحذف قبل التشغيل."}
```

```quiz
{"question": "ماذا تعني علامة `?` في `discount?: number`؟", "choices": ["أن الخاصية سرية", "أن الخاصية اختيارية وقد تكون غير موجودة", "أن قيمتها عشوائية", "أن نوعها غير معروف"], "answer": 1, "explanation": "الخاصية الاختيارية قد لا تُكتب، وقيمتها حينها `undefined`."}
```

```quiz
{"question": "ما معنى `type Id = number | string`؟", "choices": ["Id عدد ونص معًا", "Id إما عدد أو نص", "Id مصفوفة", "خطأ في الصياغة"], "answer": 1, "explanation": "العلامة `|` تصنع نوعًا اتحاديًا: واحد من الأنواع المذكورة."}
```

```quiz
{"question": "عندما تشغّل RAD IDE ملف `.ts` فيه خطأ أنواع، ماذا يحدث؟", "choices": ["يرفض البرنامج العمل دائمًا", "تُحذف الأنواع ويعمل البرنامج، والخطأ يظهر في المحرر أو مع `tsc --noEmit`", "يُصلح الخطأ تلقائيًا", "يُحذف الملف"], "answer": 1, "explanation": "التشغيل يحذف الأنواع فقط، والفحص مهمة المحرر و`tsc`."}
```

## الخلاصة

- TypeScript = JavaScript + أنواع: `let x: number`، و`function f(a: string): void`.
- `interface` لوصف الكائنات، و`type` للأسماء والاتحادات `|`، و`?` للاختياري، و`enum` للتعداد.
- `private` و`readonly` واختصار خصائص المُنشئ في الأصناف، و`<T>` للأنواع العامة.
- RAD IDE تشغّل `.ts` مباشرة بحذف الأنواع (Node.js 22.13+)، والفحص بالمحرر أو `npx tsc --noEmit`.
