# الدرس 3: أحداث اللعبة: Scene_Load و Update و KeyDown و Collide

**في هذا الدرس ستتعلم:**

- أحداث المشهد: التحميل، وكل إطار، ولوحة المفاتيح، والفأرة.
- أحداث الكائنات: التصادم `Collide` والنقر `Click`.
- أحداث **المجموعة**: حدث واحد لكل العملات `Coin_Collide`.
- المؤقتات: `AddTimer` والحدث `Tick`.

## قائمة الأحداث

اسم الحدث دائمًا **اسم الكائن + `_` + اسم الحدث**، وللمشهد نفسه البادئة `Scene_`:

| الحدث | متى يحدث؟ | المعاملات |
|---|---|---|
| `Scene_Load()` | مرة واحدة عند بدء المشهد (وعند إعادته) | |
| `Scene_Update(dt)` | كل إطار | `dt`: ثواني الإطار |
| `Scene_KeyDown(key)` و `Scene_KeyUp(key)` | ضغط مفتاح أو تركه | `key`: `"left"` و `"space"` و `"a"` و `"enter"` و `"escape"` ... |
| `Scene_MouseDown(x, y, button)` و `Scene_MouseUp(...)` | زر الفأرة | مكان المؤشر ورقم الزر |
| `Scene_Draw(screen)` | بعد رسم المشهد | سطح pygame لترسم عليه بنفسك |
| `Player_Collide(other)` | لمس `Player` كائنًا آخر | `other`: الكائن الآخر |
| `Player_Click()` | نقر على الكائن | |
| `GameTimer_Tick()` | كل فترة المؤقت | |

> **تشبيه:** الأحداث مثل أجراس في مدرسة: جرس بداية اليوم (`Load`)، وجرس كل دقيقة (`Update`)، وجرس عندما يطرق أحد الباب (`KeyDown`). أنت تكتب ماذا يحدث عند كل جرس.

## لوحة المفاتيح بطريقتين

- **حدث** `Scene_KeyDown(key)`: يحدث **مرة واحدة** لحظة الضغط. مناسب للقفز وإطلاق النار والإيقاف المؤقت.
- **فحص** `IsKeyDown("right")` داخل `Scene_Update`: صحيح **طوال** ضغط المفتاح. مناسب للحركة المستمرة.

في المثال التالي مشهد فارغ فيه كائن اسمه `Player`. «تحقق» يضغط السهم الأيمن من الإطار 1 إلى 31 (نصف ثانية)، ثم المسافة في الإطار 40:

<!-- test: {"objects": [{"name": "Player", "x": 100, "y": 300}], "scene": {"gravity": 0}, "keys": "right:1-31,space:40-42"} -->
```game run
SPEED = 120      # بكسل في الثانية


def Scene_KeyDown(key):
    print("ضغطت", key, "في الإطار", game.frame)


def Scene_Update(dt):
    if IsKeyDown("right"):
        Player.x += SPEED * dt
    if IsKeyDown("left"):
        Player.x -= SPEED * dt
    if game.frame == 59:
        print("مكان اللاعب:", round(Player.x))
```

```text output
ضغطت right في الإطار 1
ضغطت space في الإطار 40
مكان اللاعب: 160
```

نصف ثانية × 120 بكسل في الثانية = 60 بكسل، فانتقل اللاعب من 100 إلى 160.

## التصادم: Collide

يحدث `A_Collide(other)` **لحظة** بدء التلامس بين `A` وكائن آخر (مرة واحدة، لا في كل إطار). الكائن الآخر يصلك في `other`، فتفحص اسمه `other.name` أو مجموعته `other.group`.

في المثال: كرة تتحرك يمينًا بسلوك `bounce` (الدرس 6) نحو جدار (منطقة `area` اسمها `Wall`):

<!-- test: {"objects": [{"name": "Ball", "x": 100, "y": 200, "behaviours": [{"type": "bounce", "vx": 300, "vy": 0}]}, {"name": "Wall", "kind": "area", "x": 400, "y": 100, "w": 20, "h": 300}], "scene": {"gravity": 0}, "frames": 60} -->
```game run
hits = 0


def Ball_Collide(other):
    global hits
    hits += 1
    print("الكرة لمست", other.name, "من نوع", other.kind, "في الإطار", game.frame)


def Wall_Collide(other):
    print("الجدار يقول: لمسني", other.name)


def Scene_Update(dt):
    if game.frame == 59:
        print("عدد التصادمات:", hits)
```

```text output
الكرة لمست Wall من نوع area في الإطار 53
الجدار يقول: لمسني Ball
عدد التصادمات: 1
```

- `global hits` تعني: «أريد تعديل المتغير `hits` الموجود خارج الدالة». بدونها تظن Python أنك تنشئ متغيرًا جديدًا داخل الدالة.
- الحدث وقع للطرفين: `Ball_Collide` و `Wall_Collide`.

## حدث المجموعة

لو عندك 20 عملة (`Coin1` ... `Coin20`) فلن تكتب 20 حدثًا! اكتب `Coin_Collide(other)` مرة واحدة: يحدث لأي كائن في المجموعة `Coin`. ولمعرفة أي عملة بالضبط استخدم الحدث من جهة اللاعب، فـ `other` هو العملة:

<!-- test: {"objects": [{"name": "Player", "x": 50, "y": 200, "behaviours": [{"type": "bounce", "vx": 240, "vy": 0}]}, {"name": "Coin1", "x": 150, "y": 200, "w": 16, "h": 16}, {"name": "Coin2", "x": 250, "y": 200, "w": 16, "h": 16}, {"name": "Coin3", "x": 350, "y": 200, "w": 16, "h": 16}], "scene": {"gravity": 0}, "frames": 90} -->
```game run
def Player_Collide(other):
    if other.group == "Coin":
        Destroy(other)
        AddScore(10)
        print("أخذت", other.name, "النقاط =", game.score)


def Scene_Update(dt):
    if game.frame == 89:
        print("بقي من العملات:", len(FindGroup("Coin")))
```

```text output
أخذت Coin1 النقاط = 10
أخذت Coin2 النقاط = 20
أخذت Coin3 النقاط = 30
بقي من العملات: 0
```

- `Destroy(other)` يزيل الكائن من اللعبة.
- `AddScore(10)` يزيد `game.score`.

## المؤقتات: `AddTimer`

`AddTimer("SpawnTimer", 500)` ينشئ مؤقتًا يستدعي `SpawnTimer_Tick()` كل 500 ملّي ثانية. أوقفه بـ `SpawnTimer.stop()` وشغّله بـ `SpawnTimer.start()`. (يمكنك أيضًا إضافة مؤقت من المصمم.)

<!-- test: {"frames": 120} -->
```game run
ticks = 0


def Scene_Load():
    AddTimer("Clock", 500)


def Clock_Tick():
    global ticks
    ticks += 1
    print("تك", ticks, "الزمن", round(game.time, 1))
    if ticks == 3:
        Clock.stop()
```

```text output
تك 1 الزمن 0.5
تك 2 الزمن 1.0
تك 3 الزمن 1.5
```

## الفأرة والنقر

```python
def Scene_MouseDown(x, y, button):
    print("نقرت في", x, y, "بالزر", button)    # 1 = الأيسر، 3 = الأيمن


def StartButton_Click():                       # نقر على الكائن StartButton
    GoToScene("Level1")
```

## أخطاء شائعة

- **نسيان `global`** عند تعديل متغير خارج الدالة: خطأ `UnboundLocalError`.
- **كتابة اسم الحدث خطأ** مثل `player_collide`: لا يُستدعى أبدًا ولا تظهر رسالة. الأسماء حساسة لحالة الأحرف، والأفضل أن تنشئ الحدث بالنقر المزدوج في المصمم.
- **الحركة في `KeyDown`**: الكائن يتحرك خطوة واحدة فقط. للحركة المستمرة استخدم `IsKeyDown` في `Update` (أو سلوكًا جاهزًا).

## تمرين

في مشهد فيه كائن `Player`: كل مرة يُضغط `space` زِد عدّاد القفزات واطبع `قفزة 1` ثم `قفزة 2` ... وعند الضغط على `r` صفّر العدّاد واطبع `تصفير`.

```game exercise
jumps = 0


def Scene_KeyDown(key):
    pass   # space و r
```

<!-- test: {"objects": [{"name": "Player", "x": 100, "y": 100}], "keys": "space:5-6,space:10-11,r:15-16,space:20-21"} -->
```game solution
jumps = 0


def Scene_KeyDown(key):
    global jumps
    if key == "space":
        jumps += 1
        print("قفزة", jumps)
    elif key == "r":
        jumps = 0
        print("تصفير")
```

```text output
قفزة 1
قفزة 2
تصفير
قفزة 1
```

## اختبر نفسك

```quiz
{"question": "أي طريقة أنسب للحركة المستمرة يمينًا ما دام المفتاح مضغوطًا؟", "choices": ["Scene_KeyDown", "IsKeyDown داخل Scene_Update", "Scene_Load", "Player_Click"], "answer": 1, "explanation": "IsKeyDown صحيحة طوال الضغط، و KeyDown تحدث مرة واحدة."}
```

```quiz
{"question": "متى يحدث Player_Collide(other)؟", "choices": ["في كل إطار ما دام التلامس", "لحظة بدء التلامس مرة واحدة", "عند النقر على اللاعب", "عند تحميل المشهد"], "answer": 1, "explanation": "يحدث عند بداية التلامس، ولا يتكرر حتى يبتعدا ثم يتلامسا من جديد."}
```

```quiz
{"question": "كيف تكتب حدثًا واحدًا لكل الكائنات Coin1 و Coin2 و Coin3؟", "choices": ["Coins_Collide", "Coin_Collide", "All_Collide", "لا يمكن"], "answer": 1, "explanation": "حدث المجموعة: اسم المجموعة (الاسم بلا أرقام) + _Collide."}
```

```quiz
{"question": "كم مرة يحدث Tick خلال ثانيتين لمؤقت AddTimer(\"T\", 250)؟", "choices": ["2", "8", "250", "4"], "answer": 1, "explanation": "250 ملّي ثانية = ربع ثانية، أي 4 مرات في الثانية."}
```

## الخلاصة

- أحداث المشهد: `Scene_Load` و `Scene_Update(dt)` و `Scene_KeyDown(key)` و `Scene_MouseDown(x, y, button)`.
- أحداث الكائنات: `<اسم>_Collide(other)` و `<اسم>_Click()`، وأحداث المجموعة مثل `Coin_Collide`.
- `AddTimer(name, ms)` ينشئ مؤقتًا حدثه `<name>_Tick()`، و`global` لتعديل المتغيرات العامة.
