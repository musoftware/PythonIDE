# الدرس 10: تصحيح أخطاء الألعاب واختبارها

**في هذا الدرس ستتعلم:**

- قراءة رسالة الخطأ عندما تتوقف اللعبة.
- إيقاف اللعبة عند سطر معيّن بنقطة توقف، وفحص المتغيرات.
- فحص المشهد بالأمر **Check Scene**.
- اختبار اللعبة تلقائيًا بلا نافذة، كما يفعل زر «تحقق».

## عندما تتوقف اللعبة

إذا حدث خطأ في كودك تُغلق نافذة اللعبة، وتظهر في نافذة **Output** (المخرجات) رسالة **Traceback**. اقرأها من **آخرها**:

```text
Traceback (most recent call last):
  ...
  File "Level1.py", line 12, in Player_Collide
    AddScore(other.points)
AttributeError: 'Sprite' object has no attribute 'points'
```

- السطر الأخير: **نوع الخطأ** ورسالته: الكائن ليس له خاصية اسمها `points`.
- السطر قبله: **الملف ورقم السطر واسم الحدث** الذي حدث فيه الخطأ. انقر عليه نقرًا مزدوجًا في نافذة Output ليفتح المحرر على السطر.

أشهر الأخطاء في الألعاب:

| الخطأ | السبب المعتاد |
|---|---|
| `NameError: name 'Playr' is not defined` | اسم كائن أو متغير مكتوب خطأ |
| `UnboundLocalError` | عدّلت متغيرًا عامًّا داخل دالة دون `global` |
| `AttributeError` | خاصية غير موجودة، مثل `Player.speed` (السرعة في السلوك: `Player.behaviour("platformer")["speed"]`) |
| `TypeError: ... takes 0 positional arguments but 1 was given` | نادرًا: الأحداث تقبل معاملات أقل، لكن تأكد من اسم الحدث |

مثال على خطأ مقصود: اسم الكائن مكتوب خطأ. «تحقق» هنا يتوقع هذا الخطأ:

<!-- test: {"objects": [{"name": "Player", "x": 100, "y": 100}], "frames": 5, "error": "NameError: name 'Playr' is not defined"} -->
```game run
def Scene_Load():
    print("قبل الخطأ")
    Playr.x = 200          # خطأ: Playr بدل Player
    print("لن يُطبع هذا السطر")
```

```text output
قبل الخطأ
```

## نقاط التوقف

1. افتح ملف المشهد (`Level1.py`) وضع المؤشر على سطر داخل حدث، واضغط `F9` (أو انقر في الهامش الأيسر): تظهر نقطة حمراء.
2. اضغط `F5` (**بدء تصحيح الأخطاء**). مشاريع pygame تعمل تحت مصحح Python (`debugpy`).
3. عندما يصل التنفيذ إلى السطر تتجمد اللعبة، وترى في نوافذ التصحيح قيم المتغيرات: `other.name` و `game.score` و `Player.x` ...
4. `F10` ينفّذ السطر التالي، و`F11` يدخل داخل الدالة، و`F5` يكمل التشغيل.

> **نصيحة:** نقطة توقف داخل `Scene_Update` توقف اللعبة في **كل إطار**. ضعها داخل شرط، مثل `if game.score == 10:`، أو في حدث نادر مثل `Player_Collide`.

`Ctrl+F5` (**بدء بدون تصحيح الأخطاء**) أو زر **Play** في المصمم يشغّلان بلا مصحح (أسرع).

## print: أبسط أداة

`print()` في أي حدث يكتب في نافذة **Output** واللعبة تعمل. اطبع ما تشك فيه:

```python
def Player_Collide(other):
    print("لمس:", other.name, other.group, "عند", round(Player.x), round(Player.y))
```

## فحص المشهد: Check Scene

**Game > Check Scene** (لعبة > فحص المشهد) يبحث عن مشاكل التصميم قبل التشغيل، مثل:

- اسم مشهد أو كائن غير صالح كمعرّف Python، أو اسمان مكرران.
- ورقة حركات بلا صورة، أو حركة بلا إطارات.
- طبقة تستخدم مجموعة بلاطات غير موجودة.
- سلوك غير معروف.

## الاختبار التلقائي

زر «تحقق» في هذه الدروس يشغّل لعبتك **بلا نافذة** لعدد ثابت من الإطارات، ويضغط مفاتيح في إطارات محددة، ثم يقارن ما طُبع. يمكنك فعل الشيء نفسه لمشروعك من نافذة أوامر داخل مجلد اللعبة، بمتغيرات بيئة يفهمها المحرك:

| المتغير | معناه |
|---|---|
| `SDL_VIDEODRIVER=dummy` | بلا نافذة |
| `RADGAME_FRAMES=300` | أغلق بعد 300 إطار |
| `RADGAME_FIXED_DT=1` | زمن ثابت لكل إطار (نتائج متطابقة كل مرة) |
| `RADGAME_KEYS=right:5-90,space:40-44` | اضغط السهم الأيمن من الإطار 5 إلى 90، و`space` من 40 إلى 44 |
| `RADGAME_SCREENSHOT=end.png` | صورة لآخر إطار |
| `RADGAME_SHOTS=60:a.png,200:b.png` | صور عند إطارات محددة |
| `RADGAME_SAVE=test_save.json` | ملف حفظ منفصل للاختبار |

مثال في PowerShell:

```text
$env:SDL_VIDEODRIVER="dummy"; $env:RADGAME_FRAMES="300"; $env:RADGAME_KEYS="right:5-200"; python main.py
```

والمحرك يسجّل كل حدث **له دالة في كودك** في القائمة `game.events`، و`game.fired("Player_Jump")` يرجع عدد مرات تنفيذه. مثال: نضغط `space` مرتين ونتأكد أن اللاعب قفز مرتين:

<!-- test: {"template": "platformer", "frames": 150, "keys": "space:30-32,space:100-102"} -->
```game run
def Player_Jump():
    print("قفز في الإطار", game.frame)


def Scene_Update(dt):
    if game.frame == 149:
        print("عدد القفزات:", game.fired("Player_Jump"))
        print("الأحداث المسجلة:", [name for f, name, args in game.events if name != "Scene_Update"])
```

```text output
قفز في الإطار 30
قفز في الإطار 100
عدد القفزات: 2
الأحداث المسجلة: ['Player_Jump', 'Player_Jump']
```

`game.events` قائمة من ثلاثيات: (رقم الإطار، اسم الحدث، معاملاته). لاحظ أن `Scene_Update` نفسه مسجل فيها 150 مرة، لذلك استبعدناه.

## تمرين

يوجد خطأ منطقي في هذا الكود: كان المفروض أن يطبع `النقاط 30` بعد جمع العملات الثلاث، لكنه يطبع `النقاط 10`. أصلحه. (تلميح: ماذا يحدث للمتغير `points` في كل مرة؟)

```game exercise
def Player_Collide(other):
    points = 0
    if other.group == "Coin":
        Destroy(other)
        points += 10
        game.score = points


def Scene_Update(dt):
    if game.frame == 89:
        print("النقاط", game.score)
```

<!-- test: {"objects": [{"name": "Player", "x": 50, "y": 200, "behaviours": [{"type": "bounce", "vx": 240, "vy": 0}]}, {"name": "Coin1", "x": 150, "y": 200, "w": 16, "h": 16}, {"name": "Coin2", "x": 250, "y": 200, "w": 16, "h": 16}, {"name": "Coin3", "x": 350, "y": 200, "w": 16, "h": 16}], "scene": {"gravity": 0}, "frames": 90} -->
```game solution
def Player_Collide(other):
    if other.group == "Coin":
        Destroy(other)
        game.score += 10          # نزيد النقاط المحفوظة بدل البدء من صفر كل مرة


def Scene_Update(dt):
    if game.frame == 89:
        print("النقاط", game.score)
```

```text output
النقاط 30
```

## اختبر نفسك

```quiz
{"question": "من أين تبدأ قراءة رسالة Traceback؟", "choices": ["من أولها", "من آخرها: نوع الخطأ، ثم الملف والسطر", "من منتصفها", "لا داعي لقراءتها"], "answer": 1, "explanation": "آخر سطر يقول ما الخطأ، والسطر قبله أين حدث."}
```

```quiz
{"question": "ما مشكلة نقطة توقف داخل Scene_Update بلا شرط؟", "choices": ["لا تعمل أبدًا", "تتوقف اللعبة في كل إطار", "تحذف الكود", "تسرّع اللعبة"], "answer": 1, "explanation": "Scene_Update تُنفَّذ 60 مرة في الثانية."}
```

```quiz
{"question": "أي متغير بيئة يجعل نتائج الاختبار متطابقة في كل تشغيل؟", "choices": ["RADGAME_FRAMES", "RADGAME_FIXED_DT", "RADGAME_SCREENSHOT", "SDL_VIDEODRIVER"], "answer": 1, "explanation": "زمن الإطار الثابت يجعل الحركة نفسها مهما كانت سرعة الجهاز."}
```

## الخلاصة

- Traceback في نافذة Output: آخر سطر نوع الخطأ، والذي قبله الملف والسطر.
- `F9` نقطة توقف، و`F5` تشغيل بالمصحح، و`F10` و `F11` للتنفيذ خطوة خطوة.
- **Game > Check Scene** يفحص التصميم، ومتغيرات `RADGAME_*` و `game.fired` للاختبار التلقائي.
