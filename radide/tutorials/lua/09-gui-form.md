# الدرس 9: أول نافذة Lua في مصمم النماذج

حان وقت النوافذ والأزرار! في RAD IDE ترسم النافذة بالسحب والإفلات كما في Visual Basic، ثم تكتب بلغة Lua الكود الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث

في البرنامج الرسومي **المستخدم** هو الذي يقرر ماذا يحدث ومتى: يكتب، يضغط، يختار. لذلك نكتب **معالجات أحداث** (event handlers): دالة لكل **حدث** (event).

> **تشبيه:** البرنامج الرسومي مثل **جهاز التحكم عن بعد**: كل زر مربوط بعمل معين، ولا يحدث شيء حتى يُضغط زر.

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

1. الـ IDE **ترسم النافذة** التي صممتها.
2. برنامج Lua يعمل في الخلفية وينتظر.
3. عند الضغط على زر اسمه `btnHello` تستدعي الـ IDE دالتك العامة `btnHello_Click(e)`.
4. داخل الدالة تقرأ الأدوات وتغيرها بالجدول الخاص `ui`.

| الكتابة | وظيفتها |
|---|---|
| `ui.txtName.Text` | تقرأ النص المكتوب في `txtName` |
| `ui.lblOut.Text = "مرحبا"` | تغيّر خاصية |
| `ui.lstLog:AddItem("سطر")` | تستدعي دالة في الأداة (لاحظ النقطتين `:`) |
| `rad.get("txtA", "Text")` / `rad.set(...)` | نفس الشيء بكتابة الدوال |
| `rad.getnum("txtA", "Text")` | تقرأ الخاصية كرقم |
| `msgbox("تم")` | رسالة منبثقة |
| `rad.input("ما اسمك؟")` | مربع إدخال |
| `rad.quit()` | تنهي البرنامج |

و`print` داخل الأحداث تكتب في نافذة **Output** للتتبع.

> **مهم:** دوال الأحداث في Lua تكون **عامة** (بدون `local`)، لكي يجدها الجسر باسمها.

## خطوة بخطوة: برنامج الترحيب

1. **File > New Project...** ثم **Scripting > Lua (GUI Bridge)**، وسمّه `HelloLua`.
2. من **Toolbox** (صندوق الأدوات) ارسم الأدوات التالية وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblOut` | (فارغ) |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |

3. **انقر مرتين** على الزر، فتنشئ الـ IDE الدالة `btnHello_Click(e)` في `Form1.lua`. اكتب:

<!-- test: {"set": {"txtName.Text": "يوسف"}, "events": ["btnHello.Click"], "expect": {"lblOut.Text": "أهلًا يا يوسف!"}, "captions": {"btnHello": "رحّب بي"}} -->
```lua form run
-- Event handlers for Form1.
function Form1_Load(e)                -- عند ظهور النافذة
  ui.lblOut.Text = "اكتب اسمك ثم اضغط الزر"
end

function btnHello_Click(e)            -- عند الضغط على الزر
  local name = ui.txtName.Text
  if name == "" then
    ui.lblOut.Text = "من فضلك اكتب اسمك أولًا"
  else
    ui.lblOut.Text = "أهلًا يا " .. name .. "!"
  end
end
```

4. اضغط **F5**، اكتب اسمك واضغط الزر.

- اسم الدالة = **اسم الأداة + `_` + اسم الحدث**، بنفس حالة الأحرف.
- `Form1_Load` تعمل مرة واحدة عند ظهور النافذة.
- الـ IDE تولّد ملف `_radmain.lua` يحمّل كودك ويستقبل الأحداث، فلا تكتب أنت حلقة الانتظار.

## آلة حاسبة صغيرة

ارسم `txtA` و`txtB` والأزرار `btnAdd` و`btnMul` و`btnDiv` و`lblResult`:

<!-- test: {"set": {"txtA.Text": "9", "txtB.Text": "4"}, "events": ["btnDiv.Click"], "expect": {"lblResult.Text": "الناتج = 2.25"}, "captions": {"btnAdd": "+", "btnMul": "×", "btnDiv": "÷"}} -->
```lua form run
local function show(value)
  if value == math.floor(value) then value = math.floor(value) end   -- 8.0 تظهر 8
  ui.lblResult.Text = "الناتج = " .. value
  print("الناتج: " .. value)                                          -- في Output
end

local function numbers()
  return rad.getnum("txtA", "Text"), rad.getnum("txtB", "Text")
end

function btnAdd_Click(e)
  local a, b = numbers()
  show(a + b)
end

function btnMul_Click(e)
  local a, b = numbers()
  show(a * b)
end

function btnDiv_Click(e)
  local a, b = numbers()
  if b == 0 then
    msgbox("لا يمكن القسمة على صفر")
    return
  end
  show(a / b)
end
```

```text output
الناتج: 2.25
```

الدوال المساعدة `show` و`numbers` **محلية** (`local`) لأنها ليست أحداثًا، أما دوال الأحداث فعامة.

## القوائم (ListBox)

ارسم `txtItem` و`btnAdd` و`btnRemove` و`lstItems` و`lblCount`:

<!-- test: {"events": [{"set": {"txtItem.Text": "حليب"}}, "btnAdd.Click", {"set": {"txtItem.Text": "خبز"}}, "btnAdd.Click", {"set": {"txtItem.Text": "جبن"}}, "btnAdd.Click", {"set": {"lstItems.ListIndex": "1"}}, "btnRemove.Click"], "expect": {"lstItems.items": "حليب|جبن", "lblCount.Text": "العناصر: 2"}, "captions": {"btnAdd": "أضف", "btnRemove": "احذف المختار"}} -->
```lua form run
local function update_count()
  ui.lblCount.Text = "العناصر: " .. rad.getnum("lstItems", "ListCount")
end

function btnAdd_Click(e)
  local item = ui.txtItem.Text
  if item ~= "" then
    ui.lstItems:AddItem(item)
    ui.txtItem.Text = ""
    update_count()
  end
end

function btnRemove_Click(e)
  local index = rad.getnum("lstItems", "ListIndex")
  if index >= 0 then
    ui.lstItems:RemoveItem(index)
    update_count()
  else
    msgbox("اختر عنصرًا أولًا")
  end
end
```

> **انتبه:** ترقيم عناصر القائمة في الأداة يبدأ من **0** (`ListIndex` للعنصر الأول = 0)، مع أن جداول Lua تبدأ من 1. القائمة هنا أداة رسومية بقواعد Visual Basic.

## المؤقت (Timer)

ارسم `Timer` باسم `tmrTick` و`lblTime`، ثم:

<!-- test: {"events": ["tmrTick.Tick", "tmrTick.Tick"], "expect": {"lblTime.Text": "الثواني: 2", "tmrTick.enabled": "True"}} -->
```lua form run
seconds = 0          -- متغير عام: يحتفظ بقيمته بين الأحداث

function Form1_Load(e)
  rad.set("tmrTick", "Interval", 1000)
  rad.set("tmrTick", "Enabled", "True")
end

function tmrTick_Tick(e)
  seconds = seconds + 1
  ui.lblTime.Text = "الثواني: " .. seconds
end
```

المتغير `seconds` في أعلى الملف يبقى بين الأحداث لأن البرنامج يظل يعمل طوال ظهور النافذة (ويمكن أن يكون `local` في أعلى الملف أيضًا، فيراه كل ما في الملف).

## أخطاء شائعة

- **`local function btnHello_Click`**: الدالة المحلية لا يراها الجسر، فلن يحدث شيء عند الضغط. اجعل دوال الأحداث عامة.
- **`ui.lstItems.AddItem("x")`** بنقطة بدل النقطتين: يعمل في جسر RAD IDE أيضًا، لكن العادة في Lua هي `:` لاستدعاء دوال الكائنات.
- **جمع نصوص الأدوات**: `ui.txtA.Text + ui.txtB.Text` قد يعمل بالصدفة لأن Lua تحوّل النص الرقمي، لكنه يفشل إذا كان المربع فارغًا. استخدم `rad.getnum`.

## تمارين

### التمرين 1

برنامج «مربع العدد»: يكتب المستخدم عددًا في `txtNum` ويضغط `btnSquare`، فيظهر في `lblResult`: `مربع 7 هو 49`.

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}} -->
```lua form exercise
function btnSquare_Click(e)
end
```

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}, "captions": {"btnSquare": "احسب المربع"}} -->
```lua form solution
function btnSquare_Click(e)
  local n = rad.getnum("txtNum", "Text")
  ui.lblResult.Text = "مربع " .. n .. " هو " .. n * n
end
```

### التمرين 2

زر `btnRoll` يرمي حجري نرد: يظهر في `lblDice` الرقمان ومجموعهما مثل `3 + 5 = 8`، وإذا تساوى الرقمان تظهر رسالة `مزدوج!`. (للاختبار: نثبّت البذرة العشوائية في `Form1_Load` بـ `math.randomseed(1)`.)

<!-- test: {"events": ["btnRoll.Click"], "expect": {"lblDice.Text": "re:[1-6] \\+ [1-6] = \\d+"}} -->
```lua form exercise
function Form1_Load(e)
  math.randomseed(1)
end

function btnRoll_Click(e)
  -- math.random(1, 6)
end
```

<!-- test: {"events": ["btnRoll.Click"], "expect": {"lblDice.Text": "re:[1-6] \\+ [1-6] = \\d+"}, "captions": {"btnRoll": "ارمِ النرد"}} -->
```lua form solution
function Form1_Load(e)
  math.randomseed(1)
end

function btnRoll_Click(e)
  local a, b = math.random(1, 6), math.random(1, 6)
  ui.lblDice.Text = a .. " + " .. b .. " = " .. a + b
  if a == b then msgbox("مزدوج!") end
end
```

## اختبر نفسك

```quiz
{"question": "لماذا تُكتب دوال الأحداث في Lua بدون local؟", "choices": ["لأنها أسرع", "لكي يجدها الجسر باسمها كدوال عامة", "لأن local ممنوعة في Lua", "لا فرق"], "answer": 1, "explanation": "الجسر يبحث عن الدالة العامة btnHello_Click بالاسم."}
```

```quiz
{"question": "ما رقم أول عنصر في ListBox (خاصية ListIndex)؟", "choices": ["1", "0", "-1", "حسب اللغة"], "answer": 1, "explanation": "أداة القائمة تتبع قواعد Visual Basic: أول عنصر 0، و-1 تعني لا يوجد اختيار."}
```

## الخلاصة

- معالج الحدث دالة عامة باسم `اسمالأداة_الحدث(e)`.
- `ui.txtName.Text` للقراءة، و`ui.lblOut.Text = ...` للكتابة، و`ui.lst:AddItem(...)` للدوال.
- `rad.getnum` للأرقام، و`msgbox` و`rad.input` للحوار.
- المتغيرات في أعلى الملف تبقى بين الأحداث.
