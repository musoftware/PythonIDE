# الدرس 10: مشروع: لعبة اختبار المعلومات

نجمع في هذا المشروع الجداول والدوال والأحداث في لعبة صغيرة: **سؤال وأربعة أزرار للإجابة**، ونقاط تزيد مع كل إجابة صحيحة، ورسالة في النهاية.

## 1) تصميم النافذة

أنشئ مشروعًا: **File > New Project... > Lua (GUI Bridge)** باسم `QuizLua`، وارسم:

| الأداة | Name | ملاحظات |
|---|---|---|
| `Label` | `lblQuestion` | عريض، خط كبير (`FontSize` = 14) |
| `Button` | `btnA` | |
| `Button` | `btnB` | |
| `Button` | `btnC` | |
| `Button` | `btnD` | |
| `Label` | `lblScore` | النقاط |
| `Label` | `lblFeedback` | «صح» أو «خطأ» |
| `Button` | `btnRestart` | `ابدأ من جديد` |

نصوص الأزرار الأربعة سيكتبها الكود في كل سؤال.

## 2) البيانات: جدول الأسئلة

نبدأ بالمنطق وحده في الكونسول. كل سؤال جدول فيه النص والاختيارات ورقم الإجابة الصحيحة:

```lua run
local questions = {
  {q = "ما عاصمة مصر؟", choices = {"الإسكندرية", "القاهرة", "أسوان", "طنطا"}, answer = 2},
  {q = "كم يساوي 7 × 8؟", choices = {"54", "56", "64", "48"}, answer = 2},
  {q = "أي هذه لغة برمجة؟", choices = {"Lua", "HTML", "Word", "PNG"}, answer = 1},
}

local score = 0
local my_answers = {2, 3, 1}       -- إجابات تجريبية
for i, item in ipairs(questions) do
  local chosen = my_answers[i]
  local ok = chosen == item.answer
  if ok then score = score + 1 end
  print(i .. ") " .. item.q .. " => " .. item.choices[chosen] .. (ok and " ✓" or " ✗"))
end
print("النتيجة: " .. score .. " من " .. #questions)
```

```text output
1) ما عاصمة مصر؟ => القاهرة ✓
2) كم يساوي 7 × 8؟ => 64 ✗
3) أي هذه لغة برمجة؟ => Lua ✓
النتيجة: 2 من 3
```

`(ok and " ✓" or " ✗")` حيلة Lua المعروفة بدل العامل الثلاثي: إذا كان `ok` صحيحًا فالنتيجة `" ✓"`، وإلا `" ✗"`.

## 3) اللعبة بنافذة

<!-- test: {"events": ["btnB.Click", "btnC.Click", "btnA.Click"], "expect": {"lblScore.Text": "النقاط: 2 من 3", "lblFeedback.Text": "صح! أحسنت", "lblQuestion.Text": "انتهت اللعبة", "btnA.enabled": "False"}, "msgbox": ["انتهت اللعبة! نتيجتك 2 من 3"], "captions": {"btnRestart": "ابدأ من جديد"}} -->
```lua form run
local questions = {
  {q = "ما عاصمة مصر؟", choices = {"الإسكندرية", "القاهرة", "أسوان", "طنطا"}, answer = 2},
  {q = "كم يساوي 7 × 8؟", choices = {"54", "56", "64", "48"}, answer = 2},
  {q = "أي هذه لغة برمجة؟", choices = {"Lua", "HTML", "Word", "PNG"}, answer = 1},
}
local BUTTONS = {"btnA", "btnB", "btnC", "btnD"}

local current, score = 1, 0

local function set_buttons_enabled(on)
  for _, b in ipairs(BUTTONS) do rad.set(b, "Enabled", on and "True" or "False") end
end

local function show_question()
  local item = questions[current]
  ui.lblQuestion.Text = current .. ") " .. item.q
  for i, b in ipairs(BUTTONS) do
    rad.set(b, "Text", item.choices[i])
  end
  ui.lblScore.Text = "النقاط: " .. score .. " من " .. #questions
end

local function finish()
  ui.lblQuestion.Text = "انتهت اللعبة"
  ui.lblScore.Text = "النقاط: " .. score .. " من " .. #questions
  set_buttons_enabled(false)
  msgbox("انتهت اللعبة! نتيجتك " .. score .. " من " .. #questions)
end

local function choose(n)
  if n == questions[current].answer then
    score = score + 1
    ui.lblFeedback.Text = "صح! أحسنت"
  else
    local item = questions[current]
    ui.lblFeedback.Text = "خطأ، الإجابة: " .. item.choices[item.answer]
  end
  current = current + 1
  if current > #questions then finish() else show_question() end
end

local function start()
  current, score = 1, 0
  ui.lblFeedback.Text = ""
  set_buttons_enabled(true)
  show_question()
end

function Form1_Load(e) start() end
function btnA_Click(e) choose(1) end
function btnB_Click(e) choose(2) end
function btnC_Click(e) choose(3) end
function btnD_Click(e) choose(4) end
function btnRestart_Click(e) start() end
```

اضغط **F5** والعب! لاحظ أن الأحداث الستة كلها سطر واحد، والعمل الحقيقي في الدوال المحلية. هكذا يبقى الكود منظمًا مهما كبرت اللعبة.

## 4) كيف تجري اللعبة؟

1. `Form1_Load` تستدعي `start` فتعرض السؤال الأول.
2. كل زر يستدعي `choose` برقمه.
3. `choose` تقارن، وتحدّث النقاط والرسالة، ثم تنتقل للسؤال التالي أو تنهي اللعبة.
4. `finish` تعطّل الأزرار الأربعة (`Enabled` = `False`) لكي لا يستمر اللعب.

## 5) التتبع بالمصحح

ضع نقطة توقف (**F9**) على السطر `if n == questions[current].answer then` وشغّل بـ **F5**. عند الضغط على أي إجابة يتوقف البرنامج، وترى في نافذة **Locals** قيم `n` و`current` و`score`. اضغط **F10** (خطوة فوق) لتتابع سطرًا سطرًا.

## أفكار للتطوير

- **خلط الأسئلة** في `start`: بدّل كل عنصر مع عنصر عشوائي (`math.random`).
- **مؤقت** لكل سؤال: `Timer` يعد تنازليًا من 10، وعند الصفر يُحسب السؤال خطأ.
- **قراءة الأسئلة من ملف** بصيغة `السؤال|اختيار1|اختيار2|اختيار3|اختيار4|رقم الإجابة` (الدرس 6 والدرس 8).

## تمرين

أضف إلى اللعبة **أعلى نتيجة** (`best`): بعد كل لعبة، إذا كانت النتيجة أكبر من `best` احفظها، واعرضها في `lblBest` بالشكل `أعلى نتيجة: N`. للتبسيط، اختبر الفكرة في لعبة من سؤال واحد.

<!-- test: {"events": ["btnA.Click", "btnRestart.Click", "btnB.Click", "btnRestart.Click", "btnA.Click"], "expect": {"lblBest.Text": "أعلى نتيجة: 1"}} -->
```lua form exercise
local questions = {{q = "2 + 2 = ؟", choices = {"4", "5"}, answer = 1}}
local current, score, best = 1, 0, 0

local function finish()
  -- حدّث best واعرضها في lblBest
end

local function choose(n)
  if n == questions[current].answer then score = score + 1 end
  current = current + 1
  if current > #questions then finish() end
end

function btnA_Click(e) choose(1) end
function btnB_Click(e) choose(2) end
function btnRestart_Click(e) current, score = 1, 0 end
```

<!-- test: {"events": ["btnA.Click", "btnRestart.Click", "btnB.Click", "btnRestart.Click", "btnA.Click"], "expect": {"lblBest.Text": "أعلى نتيجة: 1"}, "captions": {"btnA": "4", "btnB": "5", "btnRestart": "من جديد"}} -->
```lua form solution
local questions = {{q = "2 + 2 = ؟", choices = {"4", "5"}, answer = 1}}
local current, score, best = 1, 0, 0

local function finish()
  if score > best then best = score end
  ui.lblBest.Text = "أعلى نتيجة: " .. best
end

local function choose(n)
  if n == questions[current].answer then score = score + 1 end
  current = current + 1
  if current > #questions then finish() end
end

function btnA_Click(e) choose(1) end
function btnB_Click(e) choose(2) end
function btnRestart_Click(e) current, score = 1, 0 end
```

## اختبر نفسك

```quiz
{"question": "ما قيمة (false and \"نعم\" or \"لا\")؟", "choices": ["نعم", "لا", "false", "nil"], "answer": 1, "explanation": "false and أي شيء = false، ثم false or \"لا\" = \"لا\"."}
```

```quiz
{"question": "لماذا جعلنا choose وstart دوال محلية والأحداث عامة؟", "choices": ["لأن Lua تشترط ذلك", "الأحداث يجب أن يجدها الجسر، والمساعدات تبقى داخل الملف فلا تتعارض مع غيرها", "لتسريع البرنامج", "لا يوجد سبب"], "answer": 1, "explanation": "الأحداث عامة ليستدعيها الجسر، والدوال المساعدة محلية لتنظيم الكود."}
```

## الخلاصة

- خزّنا الأسئلة في جدول من الجداول، وجربنا المنطق في الكونسول أولًا.
- الأحداث قصيرة تستدعي دوالًا محلية تحمل العمل الحقيقي.
- غيّرنا نصوص الأزرار وتفعيلها من الكود بـ `rad.set(btn, "Text", ...)` و`Enabled`.
- F9 وF5 وF10 ونافذة Locals لتتبع اللعبة أثناء تشغيلها.
