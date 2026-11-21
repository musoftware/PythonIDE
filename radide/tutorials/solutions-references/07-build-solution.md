# الدرس 7: بناء الحل وتنظيمه ونصائح عملية

**في هذا الدرس ستتعلم:**

- أوامر قائمة **Build** للحلول، وماذا يفعل كل أمر.
- **ترتيب البناء**: لماذا تُبنى المكتبات أولًا.
- حل يجمع **برنامجًا مكتبيًا وموقع ويب**.
- خصائص الحل، ونصائح لتنظيم حل كبير.

## قائمة Build

| الأمر | بالعربية | ماذا يفعل |
|---|---|---|
| Build Solution (`Ctrl+Shift+B`) | بناء الحل | يحفظ كل شيء، ويحدّث ملفات الوكيل، ثم يبني كل مكتبة تحتاج بناء (C# وJava وC وRust ...) |
| Build Project | بناء المشروع | يبني المشروع الحالي فقط |
| Refresh References | تحديث المراجع | يعيد كتابة ملفات الوكيل فقط |
| Rebuild Solution / Clean Solution | إعادة بناء الحل / تنظيف الحل | لحلول Visual Studio المفتوحة في مكانها (`.sln`): إعادة البناء من الصفر، وحذف ناتج البناء |

ورسائل البناء تظهر في نافذة **Output** هكذا:

```text
------ Build started: solution 'Shop' ------
PriceLib: dotnet build ...
App: nothing to build (Python (Tkinter))
```

لاحظ أن مشاريع **التطبيقات** لا تُبنى هنا (تُبنى عند تشغيلها)، وأن اللغات التي لا تحتاج ترجمة (مثل Python) تظهر «nothing to build».

## ترتيب البناء

إذا كان `App` يستخدم `PriceLib`، و`PriceLib` يستخدم `TaxLib`، فيجب بناء `TaxLib` أولًا، ثم `PriceLib`، ثم `App`. البيئة تحسب هذا الترتيب تلقائيًا: **كل مشروع بعد المشاريع التي يستخدمها**. وهذه الطريقة اسمها **الترتيب الطوبولوجي** (topological sort).

> **تشبيه:** مثل ارتداء الملابس: الجوارب قبل الحذاء، والقميص قبل السترة. لا يهم ترتيب الجوارب والقميص بينهما، لكن كل شيء بعد ما يعتمد عليه.

هذا مثال يحسب ترتيب البناء بنفس الفكرة التي تستخدمها البيئة:

```python run
refs = {"App": ["PriceLib", "Reports"], "PriceLib": ["TaxLib"], "Reports": ["TaxLib"], "TaxLib": []}

def build_order(refs):
    order, state = [], {}

    def visit(name):
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            raise ValueError("reference cycle at " + name)
        state[name] = "visiting"
        for lib in refs[name]:
            visit(lib)
        state[name] = "done"
        order.append(name)

    for name in refs:
        visit(name)
    return order

print(" -> ".join(build_order(refs)))
```

```text output
TaxLib -> PriceLib -> Reports -> App
```

## حل فيه برنامج مكتبي وموقع ويب

الحل لا يقتصر على البرامج المكتبية. يمكن أن يجمع مثلًا:

- `App`: برنامج **Python (Tkinter)** للموظفين.
- `Web`: **موقع ويب** للعملاء.
- `Core`: مكتبة فيها الحسابات المشتركة.

وتختار ما يعمل عند `F5` بـ **Set as StartUp Project**: الموقع يعمل في المعاينة وخادم التطوير، والبرنامج المكتبي يفتح نافذته. انظر المثال `samples\Tests\Solutions\Desktop_And_Website` (افتح `Mixed.radsln`).

## خصائص الحل

بالزر الأيمن على **Solution 'Shop'** > **Properties** (الخصائص): اسم الحل، ومشروع البدء، وقائمة المشاريع. ومن نفس القائمة: **Open Folder in File Explorer** و**Save All**.

## نصائح لتنظيم حل كبير

1. **مكتبة لكل مسؤولية:** الحسابات في مكتبة، والوصول للبيانات في مكتبة، والواجهة في مشروع.
2. **الواجهة تعتمد على المكتبات، وليس العكس:** المكتبة لا تعرف شيئًا عن النوافذ.
3. **أسماء واضحة وفريدة:** `PriceLib` و`DataLib` أفضل من `Lib1` و`Lib2`.
4. **وثّق الدوال العامة:** التعليق التوثيقي (`/// <summary>` في C#، وdocstring في Python) ينتقل إلى الوكيل ويظهر في الإكمال التلقائي لمن يستخدم المكتبة.
5. **اختبر المكتبات وحدها:** المكتبة بلا واجهة سهلة الاختبار (**Test > Run All Tests**).
6. **ضع الحل كله في Git** (`Ctrl+Alt+G`)، فملف `.radsln` وملفات `project.radproj` نصوص صغيرة يسهل تتبع تغييرها.

## أخطاء شائعة

- **انتظار أن يبني Build Solution التطبيقات:** التطبيقات تُبنى عند تشغيلها بـ `F5` أو عند النشر.
- **مرجع دائري يوقف حساب الترتيب:** رسالة «reference cycle» تعني أن مشروعين يعتمد كل منهما على الآخر. انقل الجزء المشترك إلى مكتبة ثالثة.
- **مكتبة بلغة تحتاج مترجمًا غير مثبت:** البناء يفشل ويظهر السبب في **Output**. ثبّت الأداة (مثل .NET SDK أو MinGW) من **Tools > Language Servers and Debuggers...** أو من صفحة اللغة.

## تمرين

### تمرين 1: اكتشف الدائرة

أضف إلى `refs` مرجعًا يجعل `TaxLib` يعتمد على `App`، ثم شغّل `build_order` داخل `try` واطبع رسالة الخطأ.

```python exercise
refs = {"App": ["PriceLib"], "PriceLib": ["TaxLib"], "TaxLib": []}

def build_order(refs):
    order, state = [], {}

    def visit(name):
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            raise ValueError("reference cycle at " + name)
        state[name] = "visiting"
        for lib in refs[name]:
            visit(lib)
        state[name] = "done"
        order.append(name)

    for name in refs:
        visit(name)
    return order

print(build_order(refs))
```

```python solution
refs = {"App": ["PriceLib"], "PriceLib": ["TaxLib"], "TaxLib": ["App"]}

def build_order(refs):
    order, state = [], {}

    def visit(name):
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            raise ValueError("reference cycle at " + name)
        state[name] = "visiting"
        for lib in refs[name]:
            visit(lib)
        state[name] = "done"
        order.append(name)

    for name in refs:
        visit(name)
    return order

try:
    print(build_order(refs))
except ValueError as e:
    print("خطأ:", e)
```

```text output
خطأ: reference cycle at App
```

## اختبر نفسك

```quiz
{"question": "ماذا يبني Build Solution في حل RAD IDE؟", "choices": ["كل التطبيقات والمكتبات", "المكتبات التي تحتاج ترجمة، بعد تحديث الوكلاء", "مشروع البدء فقط", "لا شيء"], "answer": 1, "explanation": "التطبيقات تُبنى عند تشغيلها."}
```

```quiz
{"question": "بأي ترتيب تُبنى المشاريع؟", "choices": ["أبجديًا", "كل مشروع بعد المشاريع التي يستخدمها", "عشوائيًا", "حسب الحجم"], "answer": 1, "explanation": "الترتيب الطوبولوجي: المكتبات أولًا."}
```

```quiz
{"question": "أين تظهر رسائل البناء؟", "choices": ["في Solution Explorer", "في نافذة Output", "في شريط العنوان", "في ملف .radsln"], "answer": 1, "explanation": "Output تعرض كل خطوة بناء ونتيجتها."}
```

## الخلاصة

- **Build Solution** (`Ctrl+Shift+B`): حفظ، ثم تحديث الوكلاء، ثم بناء المكتبات.
- الترتيب تلقائي: كل مشروع بعد ما يعتمد عليه.
- الحل قد يجمع برامج مكتبية ومواقع ومكتبات بلغات مختلفة.
- نظّم: مكتبة لكل مسؤولية، والواجهة تعتمد على المكتبات.

## قاموس مصطلحات الدليل

| المصطلح | بالعربية |
|---|---|
| Solution | حل |
| Project | مشروع |
| Class Library | مكتبة أصناف (فئات) |
| StartUp Project | مشروع البدء |
| Reference | مرجع |
| Proxy | وكيل |
| Worker | عامل |
| Circular reference | مرجع دائري |
| Build order | ترتيب البناء |
| Exception | استثناء |
