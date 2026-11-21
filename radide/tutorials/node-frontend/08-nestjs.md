# الدرس 8: مشاريع NestJS بلغة TypeScript

**في هذا الدرس ستتعلم:**

- ما هو **NestJS**، ولماذا يناسب الخوادم الكبيرة.
- إنشاء مشروع NestJS من **New Project**، وفهم ملفاته: الوحدة (module) والمتحكم (controller) والخدمة (service).
- التشغيل بـ `Ctrl+F5` في وضع المراقبة، والتصحيح بـ `F5` بنقاط توقف في ملفات `.ts`.
- إنشاء متحكمات وخدمات وموارد كاملة من قائمة **NestJS** دون كتابة أوامر.
- عرض كل مسارات الموقع في نافذة **Framework Tools** وتجربتها بـ REST Client.

## لماذا NestJS؟

في الدرس 3 كتبنا خادم Express في ملف واحد `app.js`. هذا ممتاز لموقع صغير، لكن عندما يكبر المشروع إلى عشرات المسارات تتكدس الأشياء في ملف واحد. **NestJS** إطار مبني فوق Express، مكتوب بـ **TypeScript**، يفرض عليك ترتيبًا واضحًا:

| الجزء | بالعربية | وظيفته |
|---|---|---|
| **Module** | وحدة | صندوق يجمع أجزاء ميزة واحدة (مثل «المنتجات») |
| **Controller** | متحكم | يستقبل الطلبات (`GET /products`) ويرد عليها |
| **Service** | خدمة | المنطق الحقيقي والبيانات: البحث والإضافة والحساب |

> **تشبيه:** المطعم الكبير مقسّم إلى **أقسام** (الوحدات): قسم المشويات وقسم الحلويات. في كل قسم **نادل** (المتحكم) يأخذ الطلب من الزبون ولا يطبخ بنفسه، و**طبّاخ** (الخدمة) يجهّز الطعام. النادل يعرف الطباخ لأن المدير «عيّنه» له، وهذا ما يسميه NestJS **حقن التبعيات** (dependency injection).

## الخطوة 1: إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد...).
2. اختر الفئة **Web** ثم النوع **NestJS Web App (TypeScript)**.
3. اختر أحد القالبين:

| القالب | ما ينشئه |
|---|---|
| **NestJS App** | مشروع صغير جاهز من RAD IDE: وحدة رئيسية، ومتحكم، وخدمة، ومورد **products** فيه واجهة REST. لا يحتاج الإنترنت إلا عند أول تشغيل (`npm install`) |
| **NestJS (nest new)** | المشروع الرسمي الذي ينشئه **Nest CLI** بالأمر `npx @nestjs/cli new` (يحتاج الإنترنت) |

4. اكتب الاسم مثل `ShopApi` واضغط **OK**.

## الخطوة 2: ملفات المشروع

| الملف | ما فيه |
|---|---|
| `src/main.ts` | نقطة البداية: ينشئ التطبيق ويبدأ الاستماع على المنفذ |
| `src/app.module.ts` | الوحدة الرئيسية، تستورد الوحدات الأخرى |
| `src/app.controller.ts` | الصفحة الرئيسية `/` والمسار `/health` |
| `src/products/products.module.ts` | وحدة المنتجات |
| `src/products/products.controller.ts` | مسارات `/products` |
| `src/products/products.service.ts` | قائمة المنتجات ودوال البحث والإضافة |
| `nest-cli.json` و`tsconfig.json` | إعدادات Nest CLI والمترجم |
| `package.json` | السكربتات `start:dev` و`build` و`start:prod`، والحزم |

هذا هو المتحكم كما ينشئه القالب:

```ts
import { Body, Controller, Get, Param, ParseIntPipe, Post } from '@nestjs/common';
import { Product, ProductsService } from './products.service';

@Controller('products')                 // كل مسارات هذا الصنف تبدأ بـ /products
export class ProductsController {
  constructor(private readonly products: ProductsService) {}   // حقن الخدمة

  @Get()                                 // GET /products
  findAll(): Product[] {
    return this.products.findAll();
  }

  @Get(':id')                            // GET /products/2
  findOne(@Param('id', ParseIntPipe) id: number): Product {
    return this.products.findOne(id);
  }

  @Post()                                // POST /products
  create(@Body() body: { name: string; price: number }): Product {
    return this.products.create({ name: body.name, price: Number(body.price) || 0 });
  }
}
```

الكلمات التي تبدأ بـ `@` مثل `@Controller` و`@Get` اسمها **مزخرفات** (decorators): لاصقات تضعها فوق الصنف أو الدالة لتخبر NestJS بمعناها. `@Get(':id')` تعني «هذه الدالة ترد على `GET` إلى `/products/رقم`»، و`@Param('id', ParseIntPipe)` تأخذ الرقم من العنوان وتحوّله من نص إلى عدد. ولاحظ أن المتحكم **لا يحتوي منطقًا**: يمرر كل شيء إلى الخدمة.

## الخدمة: المنطق بلا مزخرفات

الخدمة صنف TypeScript عادي تقريبًا (عليه فقط `@Injectable()` ليستطيع NestJS حقنه). لذلك يمكنك فهمه وتجربته وحده. هذا منطق خدمة المنتجات نفسه دون مزخرفات، شغّله:

```ts run
interface Product { id: number; name: string; price: number; }

class ProductsService {
    private readonly products: Product[] = [
        { id: 1, name: "Keyboard", price: 25 },
        { id: 2, name: "Mouse", price: 12.5 },
    ];

    findAll(): Product[] {
        return this.products;
    }

    findOne(id: number): Product {
        const p = this.products.find((x) => x.id === id);
        if (!p) throw new Error(`Product ${id} not found`);
        return p;
    }

    create(data: Omit<Product, "id">): Product {
        const p = { id: this.products.length + 1, ...data };
        this.products.push(p);
        return p;
    }
}

const service = new ProductsService();
console.log(service.findAll().length);
console.log(service.findOne(2).name);
const added = service.create({ name: "Monitor", price: 150 });
console.log(added.id, added.name);
try {
    service.findOne(9);
} catch (e) {
    console.log("خطأ:", (e as Error).message);
}
```

```text output
2
Mouse
3 Monitor
خطأ: Product 9 not found
```

في المشروع الحقيقي يرمي `findOne` الخطأ `NotFoundException` بدل `Error`، فيحوّله NestJS تلقائيًا إلى رد `404` بصيغة JSON. و`Omit<Product, "id">` نوع معناه «منتج بدون `id`»، لأن الرقم تضعه الخدمة.

## الخطوة 3: التشغيل

اضغط `Ctrl+F5` (**Debug > Start Without Debugging**):

1. في أول مرة تشغّل RAD IDE الأمر `npm install` وتظهر الحزم في **Output** (دقيقة تقريبًا).
2. ثم تشغّل `nest start --watch` (وهو نفسه `npm run start:dev`) على منفذ حر، وتفتح **Preview** على الصفحة الرئيسية.
3. افتح `/products` في شريط عنوان المعاينة: ترى قائمة المنتجات JSON.
4. عدّل اسم منتج في `products.service.ts` واحفظ: يعيد Nest الترجمة والتشغيل وحده (وضع المراقبة، watch mode). حدّث الصفحة لترى التغيير.

وجرّب `POST` من **Tools > REST Client** (الدرس 4) بملف `.http` مثل:

```http
@host = http://127.0.0.1:3000

### كل المنتجات
GET {{host}}/products

### منتج غير موجود (يجب أن يرجع 404)
GET {{host}}/products/99

### إضافة منتج
POST {{host}}/products
Content-Type: application/json

{ "name": "Webcam", "price": 40 }
```

## الخطوة 4: قائمة NestJS والمولّدات

عندما يحتوي المشروع على `@nestjs/core` تظهر في شريط القوائم قائمة **NestJS** فيها:

- **Start (watch mode)** (تشغيل، وضع المراقبة)، و**Start (debug, watch)**، و**Build** (بناء: يترجم إلى المجلد `dist`).
- القائمة الفرعية **Generate** (إنشاء): **New Module...** و**New Controller...** (متحكم جديد...) و**New Service...** و**New Resource...** (مورد جديد...)، ومعها **Gateway** و**Guard** و**Pipe** و**Middleware** وغيرها.
- **Run Tests** (تشغيل الاختبارات) و**Run e2e Tests** و**Lint**.
- **nest info** و**Show Routes** (عرض المسارات).

جرّب أقواها: **NestJS > Generate > New Resource...**:

1. **Name:** اكتب `orders`.
2. **Transport layer:** اترك `rest`.
3. فعّل **Generate CRUD entry points (--crud)** واضغط **OK**.

تشغّل RAD IDE الأمر `nest g resource orders --type rest --crud` وتظهر النتيجة في **Output**. ستجد المجلد `src/orders` فيه وحدة ومتحكم وخدمة وملفات DTO، والمسارات الخمسة جاهزة: `GET` و`POST` و`GET :id` و`PATCH :id` و`DELETE :id`، وأُضيفت الوحدة إلى `app.module.ts` تلقائيًا. والقائمة نفسها تظهر بالزر الأيمن على أي مجلد داخل `src` في **Solution Explorer**، فيُنشأ الملف داخل ذلك المجلد.

## الخطوة 5: نافذة أدوات إطار العمل

افتح **Site > Framework Tools > Routes** (الموقع > أدوات إطار العمل > المسارات) أو **View > Framework Tools**. في تبويب **Routes** جدول بكل المسارات التي وجدتها RAD IDE في المزخرفات: الطريقة والعنوان والدالة والملف.

- انقر مرتين على مسار، أو اختر **Go to Code** من الزر الأيمن، لتنتقل إلى دالته.
- **Open in Preview** يفتح مسارات `GET` في المعاينة، و**Copy Path** ينسخ العنوان.
- تبويب **Nest CLI / npm** (يفتحه **Site > Framework Tools > CLI / Generators**) فيه قائمة أوامر جاهزة للمولّدات وسكربتات npm: اختر أمرًا، واكتب الاسم في **Name:**، ثم **Run**. ويمكنك كتابة أي أمر بنفسك في السطر الذي فوق الناتج.
- تبويب **Tools** يعرض حالة Node.js والمصحح وIntelliSense.

## الخطوة 6: التصحيح بنقاط توقف في TypeScript

1. افتح `src/products/products.service.ts` وضع المؤشر على السطر الأول داخل `findOne`، ثم `F9`.
2. اضغط `F5`. يعمل الخادم بـ `node --inspect-wait -r ts-node/register ... src/main.ts`، ويتصل به مصحح **vscode-js-debug** كما في الدرس 5.
3. افتح `/products/2` في المعاينة. يتوقف التنفيذ في ملف `.ts` نفسه، وترى `id` في **Locals**، وتتنقل بـ `F10` و`F11`.

عندما تحفظ ملف `.ts` أثناء التصحيح تعيد RAD IDE تشغيل الخادم ويتصل المصحح من جديد.

## أخطاء شائعة

- **نسيان إضافة الوحدة إلى `app.module.ts`:** إن أنشأت وحدة بيدك (لا بالمولّد) ولم تضفها إلى `imports` فلن تعمل مساراتها، وتحصل على `404`.
- **نسيان `@Injectable()` على الخدمة:** يظهر خطأ مثل `Nest can't resolve dependencies of the ProductsController`.
- **رقم من العنوان يصل نصًا:** بدون `ParseIntPipe` يكون `id` نصًا `"2"`، فتفشل المقارنة `x.id === id`.
- **تعديل ملفات `dist`:** هي ناتج الترجمة وتُحذف مع كل بناء. عدّل في `src` دائمًا.
- **المنفذ مشغول:** لا تكتب رقم منفذ ثابتًا في `main.ts`. القالب يقرأ `process.env.PORT` الذي تضعه RAD IDE.

## تمرين

أضف إلى `ProductsService` دالتين: `update(id, data)` تغيّر السعر أو الاسم وترجع المنتج بعد التعديل، و`remove(id)` تحذف المنتج وترجع `true`، أو ترجع `false` إن لم يكن موجودًا. (في المتحكم ستربطهما بـ `@Patch(':id')` و`@Delete(':id')`.)

```ts exercise
interface Product { id: number; name: string; price: number; }

class ProductsService {
    private products: Product[] = [
        { id: 1, name: "Keyboard", price: 25 },
        { id: 2, name: "Mouse", price: 12.5 },
    ];

    findAll(): Product[] {
        return this.products;
    }

    update(id: number, data: Partial<Omit<Product, "id">>): Product | undefined {
        // ...
        return undefined;
    }

    remove(id: number): boolean {
        // ...
        return false;
    }
}

const s = new ProductsService();
console.log(s.update(2, { price: 15 })?.price);
console.log(s.update(7, { price: 1 }));
console.log(s.remove(1));
console.log(s.remove(1));
console.log(s.findAll().map((p) => p.name).join(", "));
```

```ts solution
interface Product { id: number; name: string; price: number; }

class ProductsService {
    private products: Product[] = [
        { id: 1, name: "Keyboard", price: 25 },
        { id: 2, name: "Mouse", price: 12.5 },
    ];

    findAll(): Product[] {
        return this.products;
    }

    update(id: number, data: Partial<Omit<Product, "id">>): Product | undefined {
        const p = this.products.find((x) => x.id === id);
        if (!p) return undefined;
        Object.assign(p, data);
        return p;
    }

    remove(id: number): boolean {
        const i = this.products.findIndex((x) => x.id === id);
        if (i === -1) return false;
        this.products.splice(i, 1);
        return true;
    }
}

const s = new ProductsService();
console.log(s.update(2, { price: 15 })?.price);
console.log(s.update(7, { price: 1 }));
console.log(s.remove(1));
console.log(s.remove(1));
console.log(s.findAll().map((p) => p.name).join(", "));
```

```text output
15
undefined
true
false
Mouse
```

`Partial<...>` يجعل كل الخصائص اختيارية، فتستطيع إرسال السعر وحده. و`?.` تعني «إن لم تكن النتيجة `undefined` فخذ `price`».

## اختبر نفسك

```quiz
{"question": "في NestJS، أين يجب أن يكون منطق البحث في المنتجات؟", "choices": ["في المتحكم (Controller)", "في الخدمة (Service)", "في main.ts", "في nest-cli.json"], "answer": 1, "explanation": "المتحكم يستقبل الطلب فقط ويمرره، والمنطق والبيانات في الخدمة."}
```

```quiz
{"question": "ماذا يعني `@Get(':id')` فوق دالة في متحكم عليه `@Controller('products')`؟", "choices": ["الدالة ترد على GET /products/رقم", "الدالة ترد على POST /id", "الدالة تُنفّذ عند بدء الخادم", "لا شيء، مجرد تعليق"], "answer": 0, "explanation": "مسار المتحكم `products` + مسار الدالة `:id`، و`:id` جزء متغير من العنوان."}
```

```quiz
{"question": "أسرع طريقة لإنشاء وحدة ومتحكم وخدمة ومسارات CRUD لميزة جديدة في RAD IDE؟", "choices": ["كتابتها كلها بيدك", "NestJS > Generate > New Resource...", "Site > Publish...", "File > New File"], "answer": 1, "explanation": "New Resource يشغّل `nest g resource` فينشئ كل الملفات ويضيف الوحدة إلى `app.module.ts`."}
```

## الخلاصة

- NestJS يقسّم الخادم إلى **وحدات** و**متحكمات** و**خدمات**، ويحقن الخدمة في المتحكم تلقائيًا.
- أنشئه من **File > New Project > Web > NestJS Web App (TypeScript)**.
- `Ctrl+F5` يشغّل `nest start --watch`، و`F5` يصحح بنقاط توقف في ملفات `.ts`.
- قائمة **NestJS > Generate** تنشئ الملفات، و**Site > Framework Tools > Routes** يعرض كل المسارات.
