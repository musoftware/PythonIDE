# الدرس 9: مشروع كامل: لعبة Sky Hopper خطوة بخطوة

في هذا الدرس نبني لعبة كاملة من نوع «اضغط لتطير»: الروبوت اليراعة **Glim** يطير بين بوابات من الكريستال. كل بوابة تعبرها نقطة، والبوابات تأتي أسرع كلما زادت نقاطك، ولمس الكريستال أو الأرض ينهي الجولة، وأفضل نتيجة تُحفظ. اللعبة الكاملة موجودة في مجلد العيّنات `samples/SkyHopper`، افتحها بـ **File > Open Project...** وقارن بها وأنت تتابع.

ستستخدم كل ما تعلمته: المصمم، والطبقات، وأوراق الحركات، والسلوكيات `flap` و `scroll`، و**قوالب الإنشاء** مع `Spawn`، والمناطق، والمؤقت، والنصوص، والحفظ.

## الخطوة 1: المشروع والمشهد

1. **File > New Project... > Games > Python Game (pygame) > Empty Game** باسم `SkyHopper`.
2. اختر المشهد وغيّر خصائصه: `width` = `400` و `height` = `600` (شاشة طولية مثل الهاتف)، و`background` = `#1A1440`.
3. استورد الصور بـ **Game > Add Sprite from Image...**: السماء، والتلال، والأبراج، والسحابة، وعمودَي الكريستال، والأرض. والأصوات بـ **Game > Import Sound...**: `flap` و `point` و `hit`.

## الخطوة 2: الطبقات وخلفية بعمق (Parallax)

أنشئ أربع طبقات من تبويب **Layers**، من الخلف للأمام:

| الطبقة | النوع | فيها |
|---|---|---|
| `Back` | Sprites | السماء `SkyBack`، والتلال `Hills1` و `Hills2`، والأبراج `Spires1` و `Spires2`، والسحب `Cloud1..3` |
| `Gates` | Sprites | قوالب البوابات: `PillarTop` و `PillarBottom` والمنطقة `Gap` |
| `Front` | Sprites | الأرض `Ground1` و `Ground2`، واللاعب `Player` |
| `UI` | UI | النصوص: `ScoreText` و `TitleText` و `HintText` و `GameOverText` و `ResultText` و `AgainText` |

**خدعة العمق:** أعطِ كل شيء في الخلفية سلوك `scroll` نحو اليسار مع `wrap` = نعم، لكن **بسرعات مختلفة**: التلال البعيدة 18، والأبراج 45، والأرض القريبة 150. البعيد يتحرك ببطء والقريب بسرعة، فتشعر العين بالعمق. وضع من كل شريط **نسختين متجاورتين** (`Hills1` عند x = 0 و `Hills2` عند x = 400): عندما تخرج واحدة من الشاشة تقفز خلف الأخرى، فيبدو الشريط بلا نهاية.

> **تشبيه:** عندما تنظر من نافذة القطار، الأشجار القريبة تمر بسرعة والجبال البعيدة بالكاد تتحرك. هذه هي فكرة Parallax.

جرّب: نطبع مكان التلال والأرض بعد ثانية واحدة (اللعبة في وضع الانتظار والخلفية تتحرك):

<!-- test: {"template": "sample:SkyHopper", "frames": 60} -->
```game run
def Scene_Update(dt):
    if game.frame == 59:
        print("التلال تحركت", round(-Hills1.x), "بكسل")
        print("الأبراج تحركت", round(-Spires1.x), "بكسل")
        print("الأرض تحركت", round(-Ground1.x), "بكسل")
```

```text output
التلال تحركت 18 بكسل
الأبراج تحركت 45 بكسل
الأرض تحركت 150 بكسل
```

## الخطوة 3: اللاعب Glim

1. ورقة الحركات: **Game > Sprite Sheet and Animations...**، الصورة `glim.png` بإطارات 48x40، وحركة اسمها `fly` بالإطارات `0, 1, 2, 1` و `fps` = 14 متكررة.
2. ضع `Player` من الورقة عند (90, 250).
3. أضف له سلوك **Flap (tap to fly up)**: `gravity` 1100، و`flap` 340 (قوة الرفرفة)، و`keys` = `space,up,w`، و`mouse` = نعم (النقر يرفرف أيضًا)، و`tilt` = نعم (يميل لأعلى وأسفل مع سرعته).
4. في **props** أضف `hitbox` = `7`: صندوق التصادم أصغر من الصورة بـ 7 بكسل من كل جانب. هذا يجعل اللعبة **عادلة**: لا تخسر بسبب جناح شفاف لمس الكريستال.

## الخطوة 4: البوابات بقوالب الإنشاء

لا نرسم مئات البوابات! نرسم بوابة **واحدة** كـ **قالب** ونصنع منها نسخًا وقت اللعب:

1. ضع `PillarTop` و `PillarBottom` (صورتا الكريستال) والمنطقة `Gap` (مستطيل غير مرئي في الفتحة بينهما).
2. أعطِ الثلاثة سلوك `scroll` بسرعة 150 **بدون** `wrap`: النسخة تُحذف وحدها عندما تخرج من الشاشة.
3. في **props** لكل واحد اكتب `template` = `1`: القالب نفسه **لا يُرسم ولا يتصادم**، هو مجرد «ختم».
4. من الكود: `Spawn("PillarTop", x, y)` يصنع نسخة حقيقية من القالب في المكان المطلوب ويرجعها.

> **تشبيه:** القالب مثل ختم المطاط: لا يظهر على الورقة، لكن كل ضغطة به تطبع نسخة.

## الخطوة 5: الكود

اللعبة تمر بثلاث **حالات**: `ready` (شاشة العنوان، اللاعب يتمايل)، ثم `playing`، ثم `over` (انتهت). المتغير `state` يحفظ الحالة، وكل حدث يتصرف حسبها. هذه نسخة مختصرة وواضحة من كود العيّنة:

<!-- test: {"template": "sample:SkyHopper", "frames": 200, "keys": "space:5-6"} -->
```game run
import math

GATE_X = 420           # البوابات الجديدة تظهر يمين الشاشة مباشرة
GROUND_Y = 520         # أعلى شريط الأرض
GAP = 150              # ارتفاع الفتحة

state = "ready"        # ready -> playing -> over


def Scene_Load():
    global state
    state = "ready"
    game.score = 0
    game.vars["best"] = LoadData("best", 0)
    Player.enable("flap", False)                 # يحوم في شاشة العنوان
    for t in (ScoreText, GameOverText, ResultText, AgainText):
        t.hide()
    TitleText.show()
    HintText.show()


def Scene_Update(dt):
    if state == "ready":
        Player.y = 250 + 10 * math.sin(game.time * 4)    # تمايل لأعلى وأسفل
    elif state == "playing" and Player.bottom >= GROUND_Y:
        crash()


def Scene_KeyDown(key):
    if key in ("space", "up", "w"):
        if state == "ready":
            start()
        elif state == "over":
            RestartScene()


def start():
    global state
    state = "playing"
    TitleText.hide()
    HintText.hide()
    ScoreText.show()
    Player.enable("flap", True)
    GateTimer.start()
    spawn_gate()
    print("بدأت اللعبة")


def spawn_gate():
    centre = Random(150, 400)                    # مكان الفتحة عشوائي
    top = Spawn("PillarTop", GATE_X, centre - GAP // 2 - PillarTop.height)
    Spawn("PillarBottom", GATE_X, centre + GAP // 2)
    zone = Spawn("Gap", GATE_X + top.width - 10, centre - GAP // 2)
    zone.h = GAP


def GateTimer_Tick():
    spawn_gate()


def Player_Collide(other):
    if state != "playing":
        return
    if other.group in ("PillarTop", "PillarBottom"):
        crash()
    elif other.group == "Gap":                   # عبر الفتحة
        Destroy(other)
        AddScore(1)
        PlaySound("point")


def Player_Flap():
    PlaySound("flap")


def crash():
    global state
    state = "over"
    PlaySound("hit")
    EnableBehaviour("scroll", False)             # العالم يتجمد
    GateTimer.stop()
    if game.score > game.vars["best"]:
        game.vars["best"] = game.score
        SaveData("best", game.score)
    ScoreText.hide()
    for t in (GameOverText, ResultText, AgainText):
        t.show()
    print("انتهت الجولة بنتيجة", game.score, "- الأفضل", game.vars["best"])
```

```text output
بدأت اللعبة
انتهت الجولة بنتيجة 0 - الأفضل 0
```

«تحقق» ضغط `space` مرة واحدة فقط ليبدأ، ثم لم يرفرف، فسقط Glim على الأرض. شرح أهم الأفكار:

- **الحالات**: نفس المفتاح `space` يبدأ اللعبة في `ready`، ويرفرف في `playing` (السلوك يتولى ذلك)، ويعيد اللعب في `over`.
- `Player.enable("flap", False)` يوقف سلوك الرفرفة في شاشة العنوان، و`True` يشغّله عند البدء.
- `Spawn` يرجع النسخة الجديدة، فنستخدم `top.width` لنضع منطقة النقاط بعد العمود، ونغيّر ارتفاعها `zone.h`.
- **المنطقة `Gap`**: لمسها يعني أن Glim عبر الفتحة، فنحذفها (لكي لا تُحسب مرتين) ونضيف نقطة.
- `EnableBehaviour("scroll", False)` يوقف كل ما يتحرك بسلوك `scroll` دفعة واحدة: البوابات والأرض والخلفية.
- النص `ResultText` قيمته `Score {score}    Best {best}`، فيعرض النتيجة والأفضل وحده من `game.score` و `game.vars["best"]`.
- المؤقت `GateTimer` (فترته 1400 ملّي ثانية، يبدأ متوقفًا) أُضيف من المصمم، فهو متاح باسمه في الكود.

## الخطوة 6: طيار آلي للاختبار

كيف تختبر أن البوابات والنقاط تعمل دون أن تلعب بنفسك؟ اكتب **طيارًا آليًا** صغيرًا: يرفرف كلما نزل Glim تحت منتصف الفتحة القادمة. هذه نسخة أقصر من الكود (بلا نصوص ولا أصوات)، والطيار الآلي في `Scene_Update`:

<!-- test: {"template": "sample:SkyHopper", "frames": 600, "keys": "space:5-6"} -->
```game run
import math

GATE_X, GROUND_Y, GAP = 420, 520, 150
state = "ready"


def Scene_Load():
    global state
    state = "ready"
    game.score = 0
    Player.enable("flap", False)


def Scene_KeyDown(key):
    if key == "space" and state == "ready":
        start()


def start():
    global state
    state = "playing"
    Player.enable("flap", True)
    GateTimer.start()
    spawn_gate()


def spawn_gate():
    centre = Random(200, 350)
    top = Spawn("PillarTop", GATE_X, centre - GAP // 2 - PillarTop.height)
    Spawn("PillarBottom", GATE_X, centre + GAP // 2)
    zone = Spawn("Gap", GATE_X + top.width - 10, centre - GAP // 2)
    zone.h = GAP


def GateTimer_Tick():
    spawn_gate()


def Player_Collide(other):
    global state
    if state != "playing":
        return
    if other.group == "Gap":
        Destroy(other)
        AddScore(1)
    elif other.group in ("PillarTop", "PillarBottom"):
        state = "over"
        print("اصطدم بعد", game.score, "نقاط")


def Scene_Update(dt):
    global state
    if state != "playing":
        return
    gaps = [g for g in FindGroup("Gap") if g.right > Player.x]       # الفتحات التي أمامنا
    if gaps:
        target = min(gaps, key=lambda g: g.x).center[1] + 10
    else:
        target = 300
    if Player.center[1] > target and Player.vy > 0:                   # نزل تحت الهدف: رفرف
        Player.vy = -340
    if Player.bottom >= GROUND_Y:
        state = "over"
        print("سقط بعد", game.score, "نقاط")
    if game.frame == 599:
        print("بعد 10 ثوانٍ: النقاط =", game.score, "والحالة =", state)
```

```text output
بعد 10 ثوانٍ: النقاط = 6 والحالة = playing
```

- `min(gaps, key=lambda g: g.x)` أقرب فتحة: الدالة الصغيرة `lambda` تقول «قارن بالمكان x».
- `g.center[1]` إحداثي منتصف الفتحة الرأسي.
- `Player.vy = -340` نفس ما يفعله سلوك `flap` عند الضغط.

هذه طريقة المحترفين في اختبار الألعاب: بوت يلعب، وأرقام تُقارن.

## الخطوة 7: أفكار من العيّنة الكاملة

افتح `samples/SkyHopper/Scene1.py` وستجد إضافات جميلة:

- `harder()`: كل 5 نقاط تزيد سرعة البوابات وتصغر الفتحة.
- الفتحة الجديدة لا تبعد عن السابقة أكثر من 150 بكسل، لكي تكون دائمًا ممكنة العبور.
- بعد الاصطدام يسقط Glim إلى الأرض قبل ظهور «GAME OVER»، ولا يمكن البدء من جديد إلا بعد 0.6 ثانية (لكي لا يضغط اللاعب `space` بالخطأ).

## تمرين: الإيقاف المؤقت

أضف إلى اللعبة مفتاح `p` يوقفها مؤقتًا ويشغّلها: عند الإيقاف أوقف سلوكي `scroll` و `flap` والمؤقت، واطبع `توقف`، وعند الاستئناف شغّلها واطبع `استئناف`. (الحالة الجديدة اسمها `paused`.)

```game exercise
state = "playing"


def Scene_Load():
    GateTimer.start()


def Scene_KeyDown(key):
    pass   # p: playing <-> paused
```

<!-- test: {"template": "sample:SkyHopper", "frames": 60, "keys": "p:10-11,p:30-31"} -->
```game solution
state = "playing"


def Scene_Load():
    GateTimer.start()


def Scene_KeyDown(key):
    global state
    if key != "p":
        return
    if state == "playing":
        state = "paused"
        EnableBehaviour("scroll", False)
        Player.enable("flap", False)
        GateTimer.stop()
        print("توقف")
    elif state == "paused":
        state = "playing"
        EnableBehaviour("scroll", True)
        Player.enable("flap", True)
        GateTimer.start()
        print("استئناف")
```

```text output
توقف
استئناف
```

## اختبر نفسك

```quiz
{"question": "لماذا نعطي الخلفية البعيدة سرعة scroll أقل من الأرض؟", "choices": ["لتوفير الذاكرة", "لصنع إحساس بالعمق (Parallax)", "لأن الصور كبيرة", "لا سبب"], "answer": 1, "explanation": "البعيد يتحرك ببطء والقريب بسرعة، فتشعر العين بالعمق."}
```

```quiz
{"question": "ماذا تعني props template = 1 للكائن PillarTop؟", "choices": ["يُرسم مرتين", "قالب لا يُرسم ولا يتصادم، ونصنع منه نسخًا بـ Spawn", "كائن صلب", "يتحرك وحده"], "answer": 1, "explanation": "القالب مثل ختم: Spawn يطبع منه نسخًا حقيقية."}
```

```quiz
{"question": "لماذا نحذف منطقة Gap بعد أن يلمسها اللاعب؟", "choices": ["لتوفير الذاكرة فقط", "لكي لا تُحسب النقطة أكثر من مرة", "لأنها تسبب الخسارة", "لإيقاف المؤقت"], "answer": 1, "explanation": "الحذف يضمن نقطة واحدة لكل بوابة."}
```

```quiz
{"question": "ما فائدة hitbox = 7 للاعب؟", "choices": ["يكبّر الصورة", "صندوق تصادم أصغر من الصورة فتكون اللعبة أعدل", "يسرّع اللاعب", "يمنع الرفرفة"], "answer": 1, "explanation": "الأجزاء الشفافة حول الصورة لا تسبب الخسارة."}
```

## الخلاصة

- Parallax: طبقات خلفية بسلوك `scroll` و `wrap` وسرعات مختلفة.
- القوالب (`template` = 1) مع `Spawn` تصنع عوائق لا نهائية، و`scroll` بلا `wrap` يحذفها خارج الشاشة.
- متغير الحالة (`ready` و `playing` و `over`) ينظم منطق اللعبة، و`SaveData` يحفظ الأفضل.
- بوت آلي في `Scene_Update` طريقة ممتازة لاختبار اللعبة.
