# الدرس 7: الفيزياء الحقيقية وتأثيرات الجسيمات

**في هذا الدرس ستتعلم:**

- تشغيل **الفيزياء الحقيقية** في المشهد: أجسام تسقط وتتصادم وترتد وتتدحرج.
- أنواع الأجسام: ديناميكي وثابت وحركي، وخصائصها (الكتلة والاحتكاك والمرونة).
- دفع الأجسام من الكود: `ApplyImpulse` و `ApplyForce` و `SetVelocity`.
- **الجسيمات** (particles): نار ودخان وانفجارات وشرر، من المحرر أو من الكود.

## متى تحتاج الفيزياء الحقيقية؟

السلوكيات (الدرس 6) تكفي لمعظم الألعاب: لاعب يجري ويقفز. لكن إذا أردت صناديق تتكدس وتسقط، وكرات تتدحرج على منحدر، وألواحًا معلقة تتأرجح (مثل Angry Birds)، فأنت تحتاج **محرك فيزياء**. تستخدم RAD IDE المكتبة **pymunk** (ثبّتها بالأمر `pip install pymunk`)، وتصدير Godot يستخدم فيزياء Godot نفسها.

> **تشبيه:** السلوكيات مثل ممثل يتظاهر بالسقوط كما يقول المخرج. الفيزياء الحقيقية مثل رمي كرة فعلًا: أنت لا تقرر مسارها، الجاذبية والتصادم يقرران.

## الخطوة 1: فعّل الفيزياء في المشهد

اختر المشهد (انقر في مكان فارغ)، وفي قسم **Physics** بنافذة الخصائص فعّل `enabled`، واضبط الجاذبية `gravity_y` (900 مثلًا). يحفظها المشهد هكذا:

```json
"physics": {"enabled": true, "gravity_x": 0, "gravity_y": 900, "tiles_static": true}
```

`tiles_static` يجعل طبقات البلاط الصلبة جدرانًا ثابتة في عالم الفيزياء.

## الخطوة 2: أعطِ الكائنات أجسامًا

اختر كائنًا، وفي قسم **Physics body** (جسم فيزيائي) اختر:

| الخاصية | القيم | معناها |
|---|---|---|
| `body` | `dynamic` | يتحرك بالجاذبية والتصادم (صندوق، كرة) |
| | `static` | لا يتحرك أبدًا (أرض، جدار) |
| | `kinematic` | تحركه أنت من الكود ويدفع غيره (منصة متحركة) |
| `shape` | `box` أو `circle` أو `poly` | شكل الجسم |
| `mass` | رقم | الكتلة (الأثقل يصعب دفعه) |
| `friction` | 0 إلى 1 | الاحتكاك (الجليد قريب من 0) |
| `elasticity` | 0 إلى 1 | المرونة (1 = كرة مطاطية ترتد كاملًا) |
| `fixed_rotation` | نعم أو لا | يمنع الجسم من الدوران |

ومن قسم Physics للمشهد تضيف **مفاصل** (joints) بين جسمين: `pivot` (محور) و `pin` (قضيب) و `spring` (زنبرك) و `rope` (حبل) و `motor` (محرك).

## مثال: صندوق يسقط على الأرض

مشهد فيه أرض ثابتة `Floor` وصندوق ديناميكي `Box` يبدأ في الهواء:

<!-- test: {"scene": {"gravity": 900, "physics": {"enabled": true, "gravity_x": 0, "gravity_y": 900}}, "objects": [{"name": "Floor", "x": 0, "y": 500, "w": 800, "h": 40, "physics": {"body": "static", "shape": "box", "friction": 0.8}}, {"name": "Box", "x": 380, "y": 100, "w": 40, "h": 40, "physics": {"body": "dynamic", "shape": "box", "mass": 1, "elasticity": 0.0, "fixed_rotation": true}}], "frames": 120} -->
```game run
def Scene_Update(dt):
    if game.frame in (0, 30, 119):
        print("الإطار", game.frame, "الصندوق عند y =", round(Box.y))


def Box_Collide(other):
    print("الصندوق لمس", other.name)
```

```text output
الإطار 0 الصندوق عند y = 100
الإطار 30 الصندوق عند y = 218
الصندوق لمس Floor
الإطار 119 الصندوق عند y = 460
```

في النهاية يستقر الصندوق فوق الأرض تمامًا: `500 - 40 = 460`. لاحظ أن حدث `Collide` يعمل مع الفيزياء كالمعتاد.

## الدفع من الكود

| الدالة | ماذا تفعل؟ |
|---|---|
| `ApplyImpulse(Ball, 0, -400)` | **ضربة** واحدة (مثل ركل الكرة لأعلى) |
| `ApplyForce(Rocket, 0, -2000)` | **دفع مستمر** خلال هذا الإطار، استدعه كل إطار لقوة ثابتة |
| `SetVelocity(Ball, 200, 0)` | يضبط السرعة مباشرة |
| `Ball.x = 100` | ينقل الجسم فورًا (انتقال آني) |

<!-- test: {"scene": {"gravity": 900, "physics": {"enabled": true, "gravity_x": 0, "gravity_y": 900}}, "objects": [{"name": "Ball", "x": 380, "y": 400, "w": 32, "h": 32, "physics": {"body": "dynamic", "shape": "circle", "mass": 1}}], "frames": 40, "keys": "space:1-2"} -->
```game run
top = 999


def Scene_KeyDown(key):
    if key == "space":
        ApplyImpulse(Ball, 0, -600)        # ركلة لأعلى
        print("ركلة!")


def Scene_Update(dt):
    global top
    top = min(top, Ball.y)
    if game.frame == 39:
        print("صعدت الكرة أكثر من 150 بكسل؟", 400 - top > 150)
```

```text output
ركلة!
صعدت الكرة أكثر من 150 بكسل؟ True
```

## الجسيمات (Particles)

**الجسيمات** آلاف النقاط الصغيرة تولد وتتحرك وتختفي، فتصنع نارًا أو دخانًا أو مطرًا أو انفجارًا.

### من المصمم

1. **Add > Particle Editor...** (محرر الجسيمات...): اصنع تأثيرًا وعدّل خصائصه وأنت ترى معاينة حية: معدل الولادة `rate`، والعمر `lifetime`، والسرعة `speed`، والاتجاه `angle` (`-90` = لأعلى) والانتشار `spread`، والجاذبية، والألوان من البداية للنهاية (`#FF6B8B00` الشفافية `00` في الآخر تعني يختفي تدريجيًا)، والحجم.
2. **Add > Particle emitter** (باعث جسيمات): يضع منطقة تبعث التأثير باستمرار من مركزها (مثل نار المخيم).

### من الكود

| الكود | ماذا يفعل؟ |
|---|---|
| `Burst("explosion", x, y)` | دفعة واحدة من الجسيمات (انفجار) |
| `Burst("coin", Player, 30)` | 30 جسيمًا عند مركز اللاعب |
| `e = Emit("smoke", Player)` | دخان مستمر **يتبع** اللاعب |
| `Emit("fire", 400, 500, 2)` | نار لمدة ثانيتين |
| `StopEmitter(e)` | يوقف الباعث فتختفي جسيماته تدريجيًا |

تأثيرات جاهزة بلا محرر: `fire` و `smoke` و `sparkle` و `explosion` و `rain` و `snow` و `trail` و `coin`.

<!-- test: {"objects": [{"name": "Player", "x": 380, "y": 280}], "scene": {"gravity": 0}, "frames": 150} -->
```game run
def Scene_Load():
    global boom
    boom = Burst("explosion", 400, 300, 40)
    print("جسيمات الانفجار:", len(boom.particles))


def Scene_Update(dt):
    if game.frame == 149:
        print("بعد ثانيتين ونصف:", len(boom.particles))
```

```text output
جسيمات الانفجار: 40
بعد ثانيتين ونصف: 0
```

كل جسيم يعيش أقل من ثانيتين ثم يختفي، فيصبح العدد صفرًا.

## أخطاء شائعة

- **لا شيء يسقط**: لم تفعّل `enabled` في قسم Physics للمشهد، أو الجسم `static`.
- **`radgame: radgame_physics is not available`**: ثبّت `pymunk`.
- **الصندوق يدور ويتدحرج بشكل غريب**: فعّل `fixed_rotation`، أو زِد الاحتكاك.
- **اللعبة بطيئة**: آلاف الجسيمات. قلّل `rate` أو `max`.

## تمرين

في المشهد كرة ديناميكية `Ball`. عند الضغط على `right` أعطها سرعة أفقية 300 بـ `SetVelocity` (والسرعة الرأسية 0)، واطبع `انطلقت`. في الإطار 59 اطبع هل تحركت الكرة يمينًا أكثر من 100 بكسل.

```game exercise
def Scene_KeyDown(key):
    pass


def Scene_Update(dt):
    pass
```

<!-- test: {"scene": {"gravity": 0, "physics": {"enabled": true, "gravity_x": 0, "gravity_y": 0}}, "objects": [{"name": "Ball", "x": 100, "y": 300, "w": 32, "h": 32, "physics": {"body": "dynamic", "shape": "circle", "mass": 1}}], "frames": 60, "keys": "right:1-3"} -->
```game solution
def Scene_KeyDown(key):
    if key == "right":
        SetVelocity(Ball, 300, 0)
        print("انطلقت")


def Scene_Update(dt):
    if game.frame == 59:
        print("تحركت أكثر من 100؟", Ball.x - 100 > 100)
```

```text output
انطلقت
تحركت أكثر من 100؟ True
```

## اختبر نفسك

```quiz
{"question": "أي نوع جسم تختاره للأرض التي لا تتحرك؟", "choices": ["dynamic", "static", "kinematic", "circle"], "answer": 1, "explanation": "static ثابت لا يتأثر بالجاذبية أو التصادم."}
```

```quiz
{"question": "ما الفرق بين ApplyImpulse و ApplyForce؟", "choices": ["لا فرق", "Impulse ضربة واحدة، و Force دفع خلال إطار يُكرَّر للقوة المستمرة", "Force للأجسام الثابتة فقط", "Impulse يحذف الجسم"], "answer": 1, "explanation": "الدفعة الآنية مثل الركلة، والقوة مثل محرك صاروخ يعمل باستمرار."}
```

```quiz
{"question": "كيف تصنع دخانًا يتبع اللاعب أينما ذهب؟", "choices": ["Burst(\"smoke\", 0, 0)", "Emit(\"smoke\", Player)", "Player.smoke = True", "AddTimer(\"smoke\")"], "answer": 1, "explanation": "Emit مع كائن بدل الإحداثيات يجعل الباعث يتبعه."}
```

## الخلاصة

- الفيزياء: فعّل `physics.enabled` للمشهد، وأعطِ الكائنات `Physics body` (ديناميكي أو ثابت أو حركي).
- `ApplyImpulse` و `ApplyForce` و `SetVelocity` تحرك الأجسام من الكود.
- الجسيمات: **Particle Editor** و **Particle emitter** في المصمم، و`Burst` و `Emit` و `StopEmitter` في الكود.
