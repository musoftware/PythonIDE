# الدرس 6: برامج Python المحزومة بـ PyInstaller

**في هذا الدرس ستتعلم:**

- ماذا يوجد داخل ملف `exe` صنعه **PyInstaller** (أو py2exe أو cx_Freeze).
- مراحل الاستعادة الثلاث: الاستخراج، ثم فك الترجمة، ثم التقاط النوافذ.
- معنى **bytecode** وملفات `.pyc`، ولماذا يهم رقم نسخة Python.
- أمر **File > Import > Python GUI Program** لبرامج Python التي معك كودها.
- مقارنة حقيقية بين البرنامج الأصلي والمشروع الناتج.

## ماذا يفعل PyInstaller؟

PyInstaller لا «يترجم» برنامج Python إلى لغة الآلة. هو يضع في ملف واحد: **مفسّر Python** نفسه، والمكتبات، وبرنامجك بعد تحويله إلى **bytecode** (ملفات `.pyc`). عندما يشغّل المستخدم الملف، يُفك كل ذلك في مجلد مؤقت ويعمل.

> **تشبيه:** مثل حقيبة سفر فيها كل ما تحتاجه: الملابس (المكتبات)، وجواز السفر (المفسّر)، ومذكراتك مكتوبة باختزال (bytecode). من يفتح الحقيبة يجد المذكرات، ويستطيع فك الاختزال إذا عرف طريقته.

## المراحل الثلاث

**المرحلة 1: الاستخراج.** المعالج يقرأ أرشيف PyInstaller داخل الملف (يتعرف عليه من البصمة `MEI` في آخره، كما رأينا في الدرس 4)، ويستخرج ملفات `.pyc` والمكتبات. ويدعم أيضًا py2exe وcx_Freeze.

**المرحلة 2: فك الترجمة.** يحوّل `.pyc` الخاص ببرنامجك إلى كود Python مقروء:

- لنسخ Python حتى 3.8: الأدوات `decompyle3` أو `uncompyle6` إذا كانت مثبتة.
- الأداة `pycdc` (Decompyle++) إذا كانت في `%LOCALAPPDATA%\RADIDE\tools\pycdc`، ويُقبل ناتجها فقط إذا كان كاملًا ويترجم بلا أخطاء.
- **مفكك الترجمة المدمج** في البيئة لنسخ Python من 3.11 إلى 3.13.

**المرحلة 3: التقاط النوافذ.** الكود المستعاد يمر على **مستورد Python** نفسه (المستخدم في **File > Import > Python GUI Program**): يشغّل البرنامج بطريقة خاصة ويلتقط نوافذه وأدواتها بمواقعها الحقيقية، فتتحول إلى ملفات `.form`، والدوال الأصلية تصبح **معالجات أحداث**.

## لماذا يهم رقم نسخة Python؟

الـ bytecode يختلف من نسخة Python إلى أخرى (3.11 غير 3.12 غير 3.13)، ولذلك يجب فك ترجمته **بنفس النسخة** التي صنعته. المعالج يكتشف النسخة من الملف (مثلًا `python312.dll`)، وإذا لم تكن هي نسخة البيئة يبحث عن مفسّر بتلك النسخة على جهازك ويستخدمه عبر `py -3.X`.

هذا مثال يريك ما بداخل كائن الكود الذي يُحفظ في `.pyc`: نترجم سطرين إلى bytecode، ونحفظه بـ `marshal` (الطريقة نفسها التي تُكتب بها ملفات `.pyc`)، ثم نقرؤه ونشغّله:

```python run
import marshal

source = "name = 'Sara'\nprint('Hello, ' + name)"
code = compile(source, "hello.py", "exec")

data = marshal.dumps(code)          # هذا ما يُحفظ داخل ملف .pyc بعد رأسه
print("حجم الكود المحفوظ أكبر من صفر:", len(data) > 0)
print("الأسماء المستخدمة:", code.co_names)

loaded = marshal.loads(data)        # المفكك يبدأ من هنا
exec(loaded)
```

```text output
حجم الكود المحفوظ أكبر من صفر: True
الأسماء المستخدمة: ('name', 'print')
Hello, Sara
```

لاحظ أن **أسماء** المتغيرات والدوال تبقى داخل الـ bytecode (`name` و`print`)، وكذلك النصوص. لهذا يستطيع المفكك أن يعيد كودًا قريبًا جدًا من الأصل.

## مقارنة حقيقية

برنامج Tkinter صغير (موجود مع البيئة في `samples\Tests\ExeImport\PyInstaller_Tk\source\tkhello.py`)، هذا جزء منه:

```python
def greet():
    global count
    name = entry.get().strip()
    if not name:
        messagebox.showinfo("Hello", "Please type a name")
        return
    if upper.get():
        name = name.upper()
    count += 1
    result.config(text=f"Hello, {name}! ({count})")
    log.insert("end", name)
```

بُني بـ `PyInstaller --onefile --windowed` إلى `TkHello.exe`، ثم استُورد بالمعالج. هذا جزء من `Form1.py` الناتج:

```python
    def Button1_Click(self):
        self.greet()

    def greet(self):
        global count
        name = self.entry.get().strip()
        if not name:
            messagebox.showinfo('Hello', 'Please type a name')
            return None
        if self.CheckBox1_var.get():
            name = name.upper()
        count += 1
        self.result.config(text=f'Hello, {name}! ({count})')
        self.log.insert('end', name)
```

وفي التقرير: «Extracted 1 entry script(s), 111 module(s) and 982 data file(s) (Python 3.12)» و«tkhello.py: source rebuilt with built-in decompiler» و«1 window(s) captured with 6 control(s)».

لاحظ:

- الدالة `greet` عادت كما هي تقريبًا، وصارت دالة داخل النموذج (`self.greet`).
- الزر الذي كان `command=greet` صار حدث `Button1_Click` يستدعيها.
- الأدوات التي لم يكن لها اسم في الأصل أخذت أسماء تلقائية (`Button1` و`CheckBox1`). أعد تسميتها في نافذة **Properties** إلى أسماء واضحة.

## برنامج Python معك كوده؟ استخدم Import مباشرة

إذا كان عندك **ملف `.py`** لبرنامج بواجهة Tkinter أو Qt (وليس exe)، فلا داعي لكل ما سبق: **File > Import > Python GUI Program (Tkinter / Qt)...** يلتقط نوافذه ويحوّلها إلى نماذج تعدّلها في المصمم مباشرة.

## أخطاء شائعة

- **فك الترجمة بنسخة Python مختلفة:** النتيجة تفشل أو تكون ناقصة. ثبّت نسخة Python التي صُنع بها البرنامج (المعالج يخبرك بها).
- **برامج محمية أو مشفرة:** بعض الأدوات تشفّر الـ bytecode. المعالج لا يكسر الحمايات.
- **ترك الأسماء التلقائية:** `Button1` و`CheckBox1` تجعل الكود صعب الفهم. أعد التسمية مبكرًا.
- **دوال لم تُستعد:** الدوال التي لم يستطع المفكك المدمج إعادة بنائها تبقى ومعها **disassembly** في تعليقات. أعد كتابتها، أو اسمح للذكاء الاصطناعي بإعادة كتابتها.

## تمرين

### تمرين 1: اقرأ الثوابت

عدّل المثال ليطبع **الأسماء** المستخدمة في الكود `total = price * 2\nprint(total)` ثم يشغّله، بعد أن تضع `price = 7` في أوله.

```python exercise
import marshal

source = "total = price * 2\nprint(total)"
code = compile(source, "calc.py", "exec")
print(code.co_names)
```

```python solution
import marshal

source = "price = 7\ntotal = price * 2\nprint(total)"
code = compile(source, "calc.py", "exec")
print(code.co_names)
exec(marshal.loads(marshal.dumps(code)))
```

```text output
('price', 'total', 'print')
14
```

## اختبر نفسك

```quiz
{"question": "ماذا يضع PyInstaller داخل ملف exe؟", "choices": ["كود آلة مترجمًا من Python", "مفسّر Python والمكتبات وبرنامجك على شكل bytecode", "الكود المصدري كما هو فقط", "لا شيء"], "answer": 1, "explanation": "PyInstaller يحزم المفسّر والمكتبات وملفات .pyc."}
```

```quiz
{"question": "لماذا يجب فك ترجمة .pyc بنفس نسخة Python؟", "choices": ["لأن الـ bytecode يختلف بين نسخ Python", "لأن الملف مشفر", "لأن ويندوز يطلب ذلك", "لا يهم"], "answer": 0, "explanation": "3.11 و3.12 و3.13 لكل منها bytecode مختلف."}
```

```quiz
{"question": "عندك ملف .py لبرنامج Tkinter. أي أمر أنسب؟", "choices": ["File > Import > Program (.exe / .dll)", "File > Import > Python GUI Program (Tkinter / Qt)", "File > Migrate Project", "Build EXE"], "answer": 1, "explanation": "مستورد Python يلتقط النوافذ مباشرة من الكود."}
```

## الخلاصة

- exe من PyInstaller = مفسّر + مكتبات + bytecode.
- الاستعادة: استخراج، ثم فك ترجمة بنفس نسخة Python، ثم التقاط النوافذ.
- الأسماء والنصوص تبقى في الـ bytecode، فيعود الكود قريبًا من الأصل.
- لملفات `.py` استخدم **Import > Python GUI Program** مباشرة.
