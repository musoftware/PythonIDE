# الدرس 8: النقاط والنصوص والصوت والحفظ والمشاهد

**في هذا الدرس ستتعلم:**

- النقاط والأرواح: `game.score` و `game.lives` و `AddScore`.
- كائنات النص التي تتحدث وحدها: `{score}` و `{lives}`.
- رسائل وسط الشاشة: `ShowMessage`.
- الأصوات والموسيقى: `PlaySound` و `PlayMusic`.
- حفظ أفضل نتيجة بعد إغلاق اللعبة: `SaveData` و `LoadData`.
- الانتقال بين المشاهد (المستويات): `GoToScene` و `RestartScene`.

## قيم اللعبة: game

`game` كائن واحد يعيش طوال اللعبة، حتى عند الانتقال من مشهد لآخر:

| الخاصية | معناها |
|---|---|
| `game.score` | النقاط (تبدأ 0) |
| `game.lives` | الأرواح (تبدأ 3) |
| `game.vars` | قاموس لقيمك الخاصة: `game.vars["level"] = 2` |
| `game.frame` و `game.time` | رقم الإطار والزمن في المشهد الحالي |
| `game.scene` | المشهد الحالي |

## نصوص تتحدث وحدها

اكتب في خاصية `text` لكائن نص: `Score: {score}`. المحرك يضع القيمة الحالية مكان `{score}` في كل إطار، فلا تكتب كودًا لتحديث النص! يعمل أيضًا: `{lives}` و `{level}` (اسم المشهد) وأي مفتاح في `game.vars`، مثل `{best}`.

<!-- test: {"template": "platformer", "frames": 1} -->
```game run
def Scene_Load():
    print(ScoreText.display_text(), "|", LivesText.display_text())
    AddScore(5)
    game.lives -= 1
    print(ScoreText.display_text(), "|", LivesText.display_text())
    ScoreText.text = "النقاط {score} - الأفضل {best}"
    game.vars["best"] = 40
    print(ScoreText.display_text())
```

```text output
Score: 0 | Lives: 3
Score: 5 | Lives: 2
النقاط 5 - الأفضل 40
```

- `ScoreText.text` النص كما كتبته (فيه الأقواس)، و`display_text()` النص كما يظهر على الشاشة.
- ضع نصوص النقاط في طبقة **UI** لكي تبقى ثابتة في الزاوية.

## رسالة في وسط الشاشة

```python
ShowMessage("المستوى 2!", 2)        # تظهر ثانيتين ثم تختفي
```

## الأصوات

1. **Game > Import Sound...** (لعبة > استيراد صوت...) واختر ملف `.wav` أو `.ogg`. يُنسخ إلى `assets` ويأخذ **معرّفًا** (id) مثل `jump`.
2. في نافذة **Game Assets** اضغط على الصوت لتسمعه.
3. من الكود:

```python
def Player_Jump():
    PlaySound("jump")               # صوت قصير

def Scene_Load():
    PlayMusic("theme")              # موسيقى خلفية تتكرر
    # StopMusic() لإيقافها
```

سلوك `collectible` له معامل `sound`: يشغّل الصوت وحده عند جمع العملة.

## الحفظ بعد إغلاق اللعبة

المتغيرات تضيع عند إغلاق اللعبة. لحفظ قيمة (أفضل نتيجة، الإعدادات) استخدم:

- `SaveData("best", 12)` يحفظ القيمة في ملف `savegame.json` بجانب اللعبة.
- `LoadData("best", 0)` يقرؤها، و`0` هي القيمة إذا لم تُحفظ من قبل.

<!-- test: {"frames": 1} -->
```game run
def Scene_Load():
    best = LoadData("best", 0)
    print("أفضل نتيجة محفوظة:", best)
    game.score = 17
    if game.score > best:
        SaveData("best", game.score)
        print("رقم قياسي جديد!")
    print("بعد الحفظ:", LoadData("best", 0))
```

```text output
أفضل نتيجة محفوظة: 0
رقم قياسي جديد!
بعد الحفظ: 17
```

> **ملحوظة:** «تحقق» يبدأ كل مرة بملف حفظ جديد، لذلك تبدأ النتيجة المحفوظة من 0. في لعبتك الحقيقية تبقى القيمة بين مرات التشغيل.

## المشاهد والمستويات

اللعبة يمكن أن تتكون من عدة مشاهد: قائمة البداية، والمستوى 1، والمستوى 2، وشاشة النهاية.

1. **Game > New Scene...** (لعبة > مشهد جديد...) واكتب الاسم (`Level2`): ينشئ `Level2.scene` و `Level2.py`.
2. من الكود:

| الكود | ماذا يفعل؟ |
|---|---|
| `GoToScene("Level2")` | ينتقل إلى مشهد آخر (بعد انتهاء الإطار الحالي) |
| `RestartScene()` | يعيد المشهد الحالي من البداية |
| `Quit()` | يغلق اللعبة |

المشهد الأول عند التشغيل يحدده `main.py`: `radgame.run('Level1', ...)`.

عند الانتقال أو الإعادة تُبنى كائنات المشهد من جديد ويُستدعى `Scene_Load` مرة أخرى، لكن `game.score` و `game.lives` و `game.vars` **تبقى**. لذلك نخزن فيها ما يجب أن يعيش بين المستويات:

<!-- test: {"frames": 10} -->
```game run
def Scene_Load():
    game.vars["loads"] = game.vars.get("loads", 0) + 1
    print("تحميل رقم", game.vars["loads"], "- النقاط", game.score)
    if game.vars["loads"] < 3:
        AddScore(10)
        RestartScene()
```

```text output
تحميل رقم 1 - النقاط 0
تحميل رقم 2 - النقاط 10
تحميل رقم 3 - النقاط 20
```

- `game.vars.get("loads", 0)` يقرأ القيمة، وإذا لم توجد يرجع 0.

## أخطاء شائعة

- **النص يظهر `{score}` كما هو**: كتبت `{Score}` بحرف كبير. الأسماء حساسة لحالة الأحرف.
- **الصوت لا يعمل**: معرّف الصوت خطأ (انظر الاسم في Game Assets)، أو جهازك بلا كارت صوت (اللعبة تعمل لكن صامتة).
- **النقاط تعود صفرًا في المستوى التالي**: خزنتها في متغير عادي وأعدت ضبطه في `Scene_Load`. استخدم `game.score`.

## تمرين

في `Scene_Load`: اقرأ عدد مرات اللعب المحفوظ بالمفتاح `plays` (القيمة الافتراضية 0)، وزِده واحدًا، واحفظه، واطبع `مرات اللعب: 1`. ثم ضع في `game.vars["plays"]` نفس الرقم.

```game exercise
def Scene_Load():
    pass   # LoadData و SaveData
```

<!-- test: {"frames": 1} -->
```game solution
def Scene_Load():
    plays = LoadData("plays", 0) + 1
    SaveData("plays", plays)
    game.vars["plays"] = plays
    print("مرات اللعب:", plays)
```

```text output
مرات اللعب: 1
```

## اختبر نفسك

```quiz
{"question": "ماذا يظهر على الشاشة لنص قيمته \"Lives: {lives}\" إذا كانت game.lives = 2؟", "choices": ["Lives: {lives}", "Lives: 2", "Lives: lives", "2"], "answer": 1, "explanation": "المحرك يضع قيمة game.lives مكان {lives} في كل إطار."}
```

```quiz
{"question": "أي قيمة تبقى بعد RestartScene؟", "choices": ["مكان اللاعب", "game.score", "الكائنات المحذوفة", "زمن المشهد game.time"], "answer": 1, "explanation": "game.score و game.lives و game.vars تعيش طوال اللعبة."}
```

```quiz
{"question": "كيف تحفظ أفضل نتيجة بعد إغلاق اللعبة؟", "choices": ["game.vars[\"best\"] = 10", "SaveData(\"best\", 10)", "best = 10", "ShowMessage(\"best\")"], "answer": 1, "explanation": "SaveData يكتب في savegame.json، و LoadData يقرأ."}
```

## الخلاصة

- `game.score` و `game.lives` و `game.vars` تعيش طوال اللعبة، و`{score}` و `{lives}` في النصوص تتحدث وحدها.
- `PlaySound` و `PlayMusic` للأصوات، و`ShowMessage` لرسالة وسط الشاشة.
- `SaveData` و `LoadData` للحفظ الدائم، و`GoToScene` و `RestartScene` للتنقل بين المشاهد.
