# الدرس 6: السلوكيات الجاهزة: الحركة بلا كود

**في هذا الدرس ستتعلم:**

- ما هو **السلوك** (behaviour) وكيف تضيفه لكائن من نافذة الخصائص.
- السلوكيات العشرة الجاهزة ومعاملاتها.
- تغيير معاملات السلوك وتشغيله وإيقافه من الكود.
- أحداث السلوكيات: `Jump` و `Bounce` و `Flap`.

## السلوك = حركة جاهزة

**السلوك** قطعة جاهزة تعطي الكائن تصرفًا كاملًا دون أن تكتب سطرًا: يجري ويقفز، أو يرتد عن الجدران، أو يتمشى ذهابًا وإيابًا. تضيف السلوك وتضبط أرقامه، والمحرك ينفّذه في كل إطار.

> **تشبيه:** السلوكيات مثل «مهارات» تعطيها لممثل: مهارة القفز، ومهارة الجري. الممثل يعرف كيف يؤديها، وأنت فقط تقول له السرعة والارتفاع.

لإضافة سلوك: اختر الكائن، ثم في قسم **Behaviours** (السلوكيات) بنافذة الخصائص اضغط **Add Behaviour** (إضافة سلوك) واختر من القائمة، ثم عدّل المعاملات. يمكن أن يكون للكائن أكثر من سلوك.

## السلوكيات العشرة

| السلوك | الاسم في القائمة | المعاملات (القيم الافتراضية) | ماذا يفعل؟ |
|---|---|---|---|
| `platformer` | Platformer (gravity + jump) | `speed` 220، `jump` 520، `jumps` 1 | يمين ويسار وقفز بـ `Space` أو السهم الأعلى، مع الجاذبية. `jumps` = 2 قفزة مزدوجة |
| `keyboard_move` | Keyboard movement | `speed` 200، `keys` both، `axis` both | الأسهم أو `WASD` تحركه في كل اتجاه بلا جاذبية |
| `top_down` | Top-down movement | `speed` 180، `four_way`، `rotate` | حركة من أعلى في 8 اتجاهات (أو 4) |
| `bounce` | Bounce | `vx` 150، `vy` 150 | يتحرك بسرعة ثابتة ويرتد عن حواف العالم والأشياء الصلبة |
| `follow_mouse` | Follow mouse | `speed` 0، `axis` | يتبع مؤشر الفأرة (0 = يلتصق به) |
| `solid` | Solid | - | لا يمر عبره أحد: منصات وجدران |
| `collectible` | Collectible | `score` 1، `sound` | يختفي عندما يلمسه اللاعب ويضيف نقاطًا |
| `enemy_patrol` | Enemy patrol | `speed` 80، `distance` 160، `axis` x، `turn_at_edges` | يتمشى ذهابًا وإيابًا، ويرجع عند حافة المنصة |
| `flap` | Flap (tap to fly up) | `gravity` 1100، `flap` 340، `keys` | يسقط، وكل ضغطة ترفعه (مثل Flappy Bird) |
| `scroll` | Scroll (move at a constant speed) | `speed` 120، `direction` left، `wrap` | يتحرك بسرعة ثابتة: عوائق وأرض وخلفيات متحركة |

**اللاعب** (actor) هو أي كائن له سلوك حركة يتحكم فيه المستخدم: `platformer` أو `keyboard_move` أو `top_down` أو `follow_mouse`. سلوك `collectible` يعمل عند لمس لاعب فقط.

## مثال: حركة بالأسهم بلا كود حركة

كائن `Player` بسلوك `keyboard_move` (السرعة 200). لا نكتب أي كود حركة، فقط نطبع المكان. «تحقق» يضغط السهم الأيمن نصف ثانية ثم السهم الأسفل ربع ثانية:

<!-- test: {"objects": [{"name": "Player", "x": 100, "y": 100, "behaviours": [{"type": "keyboard_move", "speed": 200}]}], "scene": {"gravity": 0}, "keys": "right:0-30,down:30-45", "frames": 50} -->
```game run
def Scene_Update(dt):
    if game.frame in (0, 29, 44):
        print("الإطار", game.frame, "المكان", round(Player.x), round(Player.y))
```

```text output
الإطار 0 المكان 103 100
الإطار 29 المكان 200 100
الإطار 44 المكان 200 150
```

## مثال: كرة ترتد وحدث Bounce

سلوك `bounce` يطلق الحدث `Ball_Bounce()` عند كل ارتداد. هنا نعدّ الارتدادات ونزيد السرعة 10% مع كل واحدة:

<!-- test: {"objects": [{"name": "Ball", "x": 380, "y": 280, "w": 40, "h": 40, "behaviours": [{"type": "bounce", "vx": 400, "vy": 300}]}], "scene": {"gravity": 0}, "frames": 120} -->
```game run
bounces = 0


def Ball_Bounce():
    global bounces
    bounces += 1
    Ball.vx *= 1.1
    Ball.vy *= 1.1
    print("ارتداد", bounces, "في الإطار", game.frame)


def Scene_Update(dt):
    if game.frame == 119:
        print("السرعة الأفقية الآن:", round(abs(Ball.vx)))
```

```text output
ارتداد 1 في الإطار 56
ارتداد 2 في الإطار 57
السرعة الأفقية الآن: 484
```

- `Ball.vx` و `Ball.vy` سرعة الكرة الحالية بالبكسل في الثانية، ويمكنك تغييرهما.
- `*= 1.1` اختصار لـ `Ball.vx = Ball.vx * 1.1`.

## التحكم في السلوك من الكود

| الكود | ماذا يفعل؟ |
|---|---|
| `Player.behaviour("platformer")` | قاموس المعاملات (`None` إذا لم يوجد) |
| `Player.behaviour("platformer")["jump"] = 700` | قفزة أعلى (مثلًا بعد أخذ قوة خاصة) |
| `Player.enable("platformer", False)` | إيقاف السلوك مؤقتًا (مثل لحظة الفوز) |
| `Player.enabled("platformer")` | هل السلوك يعمل؟ |
| `Player.has("collectible")` | هل للكائن هذا السلوك؟ |
| `EnableBehaviour("scroll", False)` | إيقاف السلوك لكل الكائنات (مثل تجميد العالم عند الخسارة) |

مثال: الأعداء في قالب Platformer تتمشى، ثم نجمّدهم كلهم بعد نصف ثانية:

<!-- test: {"template": "platformer", "frames": 60} -->
```game run
start = {}


def Scene_Load():
    for e in FindGroup("Enemy"):
        start[e.name] = e.x


def Scene_Update(dt):
    if game.frame == 30:
        EnableBehaviour("enemy_patrol", False)
        print("تجمّد الأعداء")
        for e in FindGroup("Enemy"):
            print(e.name, "تحرك", round(e.x - start[e.name]), "بكسل")
    if game.frame == 59:
        e = Enemy1
        print("Enemy1 ما زال عند", round(e.x - start["Enemy1"]))
```

```text output
تجمّد الأعداء
Enemy1 تحرك 36 بكسل
Enemy2 تحرك 36 بكسل
Enemy3 تحرك 36 بكسل
Enemy1 ما زال عند 36
```

## أحداث السلوكيات

| الحدث | من أي سلوك؟ | متى؟ |
|---|---|---|
| `Player_Jump()` | `platformer` | لحظة القفز (شغّل صوت القفز هنا) |
| `Ball_Bounce()` | `bounce` | عند كل ارتداد |
| `Bird_Flap()` | `flap` | عند كل رفرفة |
| `Player_OutOfWorld()` | أي كائن | سقط أسفل العالم (اللاعب بلا هذا الحدث يعيد المشهد) |

## أخطاء شائعة

- **اللاعب لا يقفز**: الجاذبية `gravity` للمشهد صفر، أو لا توجد أرض صلبة تحته (`collision` أو سلوك `solid`).
- **العملة لا تختفي**: من يلمسها ليس له سلوك لاعب (`platformer` أو `keyboard_move` ...).
- **سلوكان للحركة معًا** (`platformer` و `keyboard_move`): يتصارعان. اختر واحدًا.

## تمرين

كائن `Player` بسلوك `keyboard_move` (السرعة 100). عند الضغط على `shift` اجعل السرعة 300 (جري)، وعند تركه ارجع إلى 100. اطبع السرعة في كل تغيير بالشكل `السرعة 300`.

```game exercise
def Scene_KeyDown(key):
    pass


def Scene_KeyUp(key):
    pass
```

<!-- test: {"objects": [{"name": "Player", "x": 100, "y": 100, "behaviours": [{"type": "keyboard_move", "speed": 100}]}], "scene": {"gravity": 0}, "keys": "shift:5-20,shift:30-35", "frames": 40} -->
```game solution
def Scene_KeyDown(key):
    if key == "shift":
        Player.behaviour("keyboard_move")["speed"] = 300
        print("السرعة", 300)


def Scene_KeyUp(key):
    if key == "shift":
        Player.behaviour("keyboard_move")["speed"] = 100
        print("السرعة", 100)
```

```text output
السرعة 300
السرعة 100
السرعة 300
السرعة 100
```

## اختبر نفسك

```quiz
{"question": "أي سلوك يناسب أرضية تتحرك يسارًا باستمرار في لعبة جري لا نهائية؟", "choices": ["platformer", "scroll مع wrap", "bounce", "solid"], "answer": 1, "explanation": "scroll يحرك بسرعة ثابتة، و wrap يجعل النسخ تتبادل الأماكن بلا نهاية."}
```

```quiz
{"question": "ماذا تفعل `EnableBehaviour(\"scroll\", False)`؟", "choices": ["تحذف كل الكائنات", "توقف سلوك scroll لكل الكائنات التي لها هذا السلوك", "تشغّل السلوك", "تغيّر السرعة"], "answer": 1, "explanation": "تجمّد كل ما يتحرك بسلوك scroll، مفيد عند الخسارة."}
```

```quiz
{"question": "كيف تجعل اللاعب يقفز قفزة مزدوجة؟", "choices": ["jump = 2", "jumps = 2", "speed = 2", "flap = 2"], "answer": 1, "explanation": "jumps عدد القفزات المسموحة قبل لمس الأرض."}
```

## الخلاصة

- السلوكيات تعطي الكائنات حركة كاملة بلا كود: `platformer` و `keyboard_move` و `top_down` و `bounce` و `enemy_patrol` و `flap` و `scroll` و `collectible` و `solid` و `follow_mouse`.
- `obj.behaviour(name)[param]` يغيّر المعاملات، و`enable` و `EnableBehaviour` يوقفان ويشغّلان.
- أحداث `Jump` و `Bounce` و `Flap` تخبرك بما فعله السلوك.
