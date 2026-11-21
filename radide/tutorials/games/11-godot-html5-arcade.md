# الدرس 11: التصدير إلى Godot وألعاب HTML5 و Arcade و Ring

**في هذا الدرس ستتعرف على:**

- تحويل لعبة pygame إلى مشروع **Godot 4** بأمر واحد.
- مشاريع Godot داخل RAD IDE: التشغيل والتصحيح وفتح محرر Godot.
- ألعاب **HTML5** تعمل في المتصفح بنفس المشاهد.
- قوالب **Python Arcade**، وألعاب **Ring**، والألعاب ثلاثية الأبعاد.

## لماذا Godot؟

**Godot** محرك ألعاب مجاني ومفتوح المصدر وقوي: يصدّر لعبتك إلى Windows و Android و iOS والويب، وفيه أدوات متقدمة للإضاءة والظلال والصوت. RAD IDE تسمح لك بالبداية السهلة بـ pygame، ثم الانتقال إلى Godot عندما تكبر لعبتك، **دون إعادة رسم المشاهد**.

ثبّت Godot 4 (من `godotengine.org`، أو بالأمر `winget install GodotEngine`). تبحث عنه RAD IDE تلقائيًا.

## Game > Export to Godot...

1. افتح مشروع لعبة pygame (مثل Sky Hopper).
2. **Game > Export to Godot...** (لعبة > تصدير إلى Godot...) واختر مجلدًا جديدًا.
3. يكتب الـ IDE مشروع Godot كاملًا:

| في مشروع pygame | يصبح في Godot |
|---|---|
| `Level1.scene` | `Level1.tscn` |
| طبقة بلاط | `TileMap` مع `TileSet` |
| كائن رسومي بورقة حركات | `AnimatedSprite2D` مع `SpriteFrames` |
| نص | `Label` |
| منطقة | `Node2D` |
| طبقة UI | `CanvasLayer` |
| السلوكيات | تعمل كما هي (ملف `radgame_scene.gd` توأم `radgame.py`) |
| الفيزياء | `RigidBody2D` و `StaticBody2D` ومفاصل Godot |
| الجسيمات | `CPUParticles2D` |
| كودك `Level1.py` | `Level1.gd` مترجم إلى GDScript |

**ترجمة الكود:** يترجم الـ IDE كود Python إلى GDScript بقواعد تفهم واجهة `radgame` كلها تقريبًا: الأحداث، و`if` و `for` و `while`، والقوائم والقواميس، و`game.score`، و`Spawn` و `Destroy` و `FindGroup` و `SaveData` والمؤقتات والجسيمات والفيزياء. أي سطر لا يفهمه يبقى تعليقًا `# TODO` فيه سطر Python الأصلي لتترجمه بنفسك (أو بمساعدة مزوّد الذكاء الاصطناعي إن كان مفعّلًا). مثلًا حدث التصادم في قالب Platformer يصبح:

```gdscript
func Player_Collide(other):
	if getp(other, "group") == "Enemy":
		if getp(Player, "vy") > 0 and getp(Player, "bottom") - getp(other, "y") < 14:
			destroy(other)
			setp(Player, "vy", -320)
			add_score(5)
		else:
			LoseLife()
```

> **ملحوظة:** ملفات `.tscn` تُعاد كتابتها في كل تصدير، أما ملفات `.gd` فتُنشأ مرة واحدة فقط ولا يمسها التصدير التالي، فتعديلاتك فيها آمنة.

## مشروع Godot داخل RAD IDE

يمكنك أيضًا البدء مباشرة: **File > New Project... > Games > Godot 4 (GDScript)** بقوالب **Platformer (Godot)** و **Top-down Game (Godot)** و **Empty Godot 2D**. المشاهد نفسها تُرسم في مصمم المشاهد، والكود في `Level1.gd` بنفس أسماء الأحداث:

```gdscript
extends "res://radgame/radgame_scene.gd"

func Scene_Load():
	show_message("Collect the coins!", 2)

func Player_Collide(other):
	if getp(other, "group") == "Coin":
		destroy(other)
		add_score(1)
```

- `F5` يصدّر المشاهد ويشغّل اللعبة **تحت مصحح Godot**: نقاط التوقف `F9` في ملفات `.gd` تعمل.
- `Ctrl+F5` أو **Play** يشغّلانها مباشرة بـ `godot --path`.
- قائمة **Godot** في شريط القوائم (تظهر مع مشاريع Godot) فيها: **Open in Godot Editor** (فتح في محرر Godot)، و**Run the Game in Godot** (تشغيل اللعبة في Godot)، و**Write the Godot Project (project.godot + .tscn)** (كتابة مشروع Godot)، و**Export** لإعدادات التصدير التي تضيفها في محرر Godot (`Project > Export`).

## ألعاب HTML5: نفس اللعبة في المتصفح

**File > New Project... > Games > HTML5 Canvas Game (JavaScript)**. المشاهد نفسها، والمحرك `radgame.js` توأم `radgame.py` بنفس السلوكيات، والكود في `Level1.js`:

```javascript
function Scene_Load() {
  game.score = 0;
}

function Player_Collide(other) {
  if (other.group === "Coin") {
    Destroy(other);
    AddScore(1);
  }
}
```

- `F5` يشغّل خادم التطوير في الـ IDE ويعرض `index.html` في نافذة **Preview**.
- لنشر اللعبة: ارفع مجلد المشروع كما هو (`index.html` و `radgame.js` و `scenes.js` و `assets`) إلى أي استضافة مواقع، فهي ملفات ثابتة.

## Python Arcade: كود فقط

**Python Arcade** قوالب بمكتبة `arcade` الشهيرة (ثبّتها بـ `pip install arcade`). لا يوجد مصمم مشاهد: المستوى خريطة نصية داخل `main.py`، والرسومات مثل قوالب pygame. مناسبة لمن يريد تعلم برمجة الألعاب «من الداخل» بلا محرك جاهز. `F5` يشغّل `main.py` تحت مصحح Python.

## Ring Game

**Ring Game (RingRayLib)**: المشاهد نفسها، والكود بلغة **Ring** في `Level1.ring`:

```text
func Player_Collide oOther
    if oOther.group = "Coin"
        Destroy(oOther)
        AddScore(1)
    ok
```

## ثلاثي الأبعاد

**Python 3D (Ursina)** و **Godot 3D (GDScript)** يستخدمان ملفات `.scene3d` في عارض المشاهد ثلاثية الأبعاد. لهما دليل منفصل، لكن الفكرة واحدة: مشهد، وكائنات بأسماء، وأحداث.

## أيها أختار؟

| تريد... | اختر |
|---|---|
| أسهل بداية وتعلم البرمجة | **Python Game (pygame)** |
| لعبة للهاتف ومتجر Google Play | ابدأ بـ pygame ثم **Export to Godot**، أو Godot مباشرة |
| لعبة يلعبها الناس من رابط | **HTML5 Canvas Game** |
| فهم ما يحدث داخل محرك الألعاب | **Python Arcade** |
| تحب لغة Ring | **Ring Game** |

## أخطاء شائعة

- **"Godot was not found"**: ثبّت Godot 4 وأعد تشغيل الـ IDE.
- **أسطر `# TODO` في ملف `.gd`**: كود لم يُترجم تلقائيًا. ترجمه بنفسك، فهو موجود كتعليق فوقه.
- **لعبة HTML5 بيضاء عند فتح `index.html` من المجلد**: الصور تحتاج خادمًا في بعض المتصفحات. شغّلها بـ `F5` من الـ IDE أو بـ `python -m http.server`.

## اختبر نفسك

```quiz
{"question": "ماذا يحدث لملف Level1.gd عند التصدير إلى Godot مرة ثانية؟", "choices": ["يُعاد كتابته", "يبقى كما هو لأنه يُنشأ مرة واحدة فقط", "يُحذف", "يتحول إلى Python"], "answer": 1, "explanation": "ملفات .tscn تُعاد كتابتها، أما ملفات .gd فهي ملفك وتبقى."}
```

```quiz
{"question": "أي أنواع المشاريع تشترك في نفس ملف المشهد والسلوكيات؟", "choices": ["Arcade و Ursina", "pygame و Godot و HTML5 و Ring", "pygame فقط", "HTML5 فقط"], "answer": 1, "explanation": "المصمم يعمل مع هذه الأنواع الأربعة، ولكل نوع محركه التوأم."}
```

```quiz
{"question": "ماذا يحدث لسطر Python لا يستطيع المترجم تحويله إلى GDScript؟", "choices": ["يفشل التصدير", "يبقى تعليق # TODO فيه السطر الأصلي", "يُحذف بصمت", "يُترك بلغة Python"], "answer": 1, "explanation": "التصدير يكمل، ويترك لك ملاحظة لتترجم السطر بنفسك."}
```

## الخلاصة

- **Game > Export to Godot...** يحوّل المشاهد والرسومات والسلوكيات والكود إلى مشروع Godot 4.
- مشاريع Godot و HTML5 و Ring تستخدم نفس المصمم والمشاهد، و`F5` يشغّل كل نوع بمحركه.
- Arcade للكود الخالص، و Ursina و Godot 3D للألعاب ثلاثية الأبعاد.
