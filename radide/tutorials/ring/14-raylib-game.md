# الدرس 14: لعبتك الأولى بـ RingRayLib

**في هذا الدرس ستتعلم:**

- ما هي **RayLib** وكيف تعمل **حلقة اللعبة** (game loop).
- فتح نافذة والرسم فيها: دوائر ومستطيلات ونصوص.
- قراءة لوحة المفاتيح وتحريك اللاعب.
- اكتشاف **التصادم** وحساب النقاط.
- لعبة كاملة: «التقط الكرة».
- مشروع **Ring Game (RingRayLib)** في RAD IDE ومصمم المشاهد.

## ما هي RayLib؟

**RayLib** مكتبة بسيطة ومشهورة لصنع الألعاب، و**RingRayLib** تربطها بـ Ring وتأتي معها جاهزة. ليس فيها أزرار ومربعات نص مثل RingQt؛ بدلًا من ذلك أنت **ترسم** كل شيء بنفسك عشرات المرات في الثانية.

## حلقة اللعبة

كل لعبة تقريبًا تعمل بنفس الفكرة: حلقة تتكرر حوالي **60 مرة في الثانية**، وفي كل لفة ثلاث خطوات:

1. **اقرأ المدخلات**: هل ضغط اللاعب سهمًا؟
2. **حدّث الحالة**: حرّك الأشياء، واكتشف التصادم، واحسب النقاط.
3. **ارسم**: امسح الشاشة وارسم كل شيء في مكانه الجديد.

> **تشبيه:** حلقة اللعبة مثل كتاب الرسوم المتحركة الذي تقلّب صفحاته بسرعة: كل صفحة (إطار frame) رسمة ثابتة مختلفة قليلًا عن التي قبلها، فيرى المشاهد حركة.

## أول نافذة

<!-- test: {"norun": true} -->
```ring run
load "raylib.ring"

InitWindow(600, 400, "نافذتي الأولى")
SetTargetFPS(60)                     # 60 إطارًا في الثانية

while !WindowShouldClose()           # حتى يغلق اللاعب النافذة
    BeginDrawing()
        ClearBackground(RAYWHITE)
        DrawText("Hello RayLib!", 190, 180, 30, DARKBLUE)
        DrawCircle(300, 300, 40, RED)
    EndDrawing()
end

CloseWindow()
```

| الدالة | العمل |
|---|---|
| `InitWindow(w, h, cTitle)` | تفتح نافذة اللعبة |
| `SetTargetFPS(n)` | عدد الإطارات في الثانية |
| `WindowShouldClose()` | `1` إذا ضغط اللاعب زر الإغلاق أو `Esc` |
| `BeginDrawing()` / `EndDrawing()` | يحيطان بكل أوامر الرسم في الإطار |
| `ClearBackground(color)` | يمسح الشاشة بلون |
| `DrawText(c, x, y, size, color)` | يكتب نصًا |
| `DrawCircle(x, y, r, color)` | يرسم دائرة مركزها `(x, y)` |
| `DrawRectangle(x, y, w, h, color)` | يرسم مستطيلًا ركنه الأعلى الأيسر `(x, y)` |
| `CloseWindow()` | يغلق النافذة |

> **الإحداثيات:** النقطة `(0, 0)` هي **الركن الأعلى الأيسر** من النافذة. `x` يزيد كلما اتجهت يمينًا، و`y` يزيد كلما **نزلت** لأسفل (عكس ما تعلمته في الرياضيات).

> **ملحوظة:** `DrawText` في RayLib يرسم بخط إنجليزي بسيط، ولا يعرض الحروف العربية. لذلك نصوص اللعبة نفسها بالإنجليزية.

الألوان الجاهزة: `RED` و`GREEN` و`BLUE` و`DARKBLUE` و`YELLOW` و`ORANGE` و`BLACK` و`WHITE` و`RAYWHITE` و`GRAY` وغيرها.

## تحريك اللاعب بالأسهم

<!-- test: {"norun": true} -->
```ring run
load "raylib.ring"

InitWindow(600, 400, "Move the box")
SetTargetFPS(60)
nX = 280  nY = 180

while !WindowShouldClose()
    # 1) المدخلات + 2) التحديث
    if IsKeyDown(KEY_RIGHT) nX += 5 ok
    if IsKeyDown(KEY_LEFT)  nX -= 5 ok
    if IsKeyDown(KEY_DOWN)  nY += 5 ok
    if IsKeyDown(KEY_UP)    nY -= 5 ok
    # 3) الرسم
    BeginDrawing()
        ClearBackground(RAYWHITE)
        DrawRectangle(nX, nY, 40, 40, ORANGE)
        DrawText("Use the arrow keys", 10, 10, 20, GRAY)
    EndDrawing()
end
CloseWindow()
```

- `IsKeyDown(key)`: `1` **طوال** ضغط المفتاح (للحركة المستمرة).
- `IsKeyPressed(key)`: `1` في لحظة الضغط فقط (للقفز أو إطلاق النار مرة واحدة).
- أسماء المفاتيح: `KEY_LEFT` و`KEY_RIGHT` و`KEY_UP` و`KEY_DOWN` و`KEY_SPACE` و`KEY_ENTER` و`KEY_A`... إلخ.

## منطق اللعبة بدون رسم

أهم جزء في أي لعبة هو **المنطق**: متى يلتقط اللاعب الكرة؟ نكتبه في دوال صغيرة يمكن اختبارها في الكونسول قبل الرسم. الكرة تُلتقط إذا وصلت إلى ارتفاع المضرب وكانت فوقه أفقيًا:

```ring run
# المضرب: يبدأ من nPaddleX وعرضه 100، والكرة في (nBallX, nBallY)
see caught(250, 300, 385) + nl     # فوق المضرب وفي مستواه
see caught(250, 120, 385) + nl     # بعيدة يسارًا
see caught(250, 300, 100) + nl     # ما زالت في الأعلى

func caught nPaddleX, nBallX, nBallY
    if nBallY >= 370 and nBallX >= nPaddleX and nBallX <= nPaddleX + 100
        return 1
    ok
    return 0
```

```text output
1
0
0
```

ونفس الفكرة لإبقاء اللاعب داخل الشاشة، وهي دالة نسميها عادة `clamp`:

```ring run
see clamp(-30, 0, 500) + nl
see clamp(250, 0, 500) + nl
see clamp(620, 0, 500) + nl

func clamp n, nMin, nMax
    if n < nMin return nMin ok
    if n > nMax return nMax ok
    return n
```

```text output
0
250
500
```

## اللعبة الكاملة: «التقط الكرة»

تسقط كرة من أعلى الشاشة، وأنت تحرك المضرب بالسهمين لتلتقطها. كل كرة تلتقطها تزيد نقاطك وتزيد سرعة الكرة، وإذا سقطت ثلاث كرات تخسر:

<!-- test: {"norun": true} -->
```ring run
load "raylib.ring"

WIDTH = 600  HEIGHT = 400
InitWindow(WIDTH, HEIGHT, "Catch the Ball")
SetTargetFPS(60)

nPaddleX = 250
nBallX = GetRandomValue(20, WIDTH - 20)
nBallY = 0
nSpeed = 3
nScore = 0
nLives = 3

while !WindowShouldClose()
    if nLives > 0
        # المدخلات
        if IsKeyDown(KEY_LEFT)  nPaddleX -= 7 ok
        if IsKeyDown(KEY_RIGHT) nPaddleX += 7 ok
        nPaddleX = clamp(nPaddleX, 0, WIDTH - 100)
        # التحديث
        nBallY += nSpeed
        if caught(nPaddleX, nBallX, nBallY)
            nScore++
            nSpeed += 0.5
            newBall()
        but nBallY > HEIGHT
            nLives--
            newBall()
        ok
    else
        if IsKeyPressed(KEY_ENTER)          # ابدأ من جديد
            nScore = 0  nLives = 3  nSpeed = 3
            newBall()
        ok
    ok
    # الرسم
    BeginDrawing()
        ClearBackground(RAYWHITE)
        DrawCircle(nBallX, nBallY, 12, RED)
        DrawRectangle(nPaddleX, HEIGHT - 20, 100, 12, DARKBLUE)
        DrawText("Score: " + nScore, 10, 10, 24, BLACK)
        DrawText("Lives: " + nLives, WIDTH - 110, 10, 24, MAROON)
        if nLives = 0
            DrawText("GAME OVER - press Enter", 120, 180, 30, RED)
        ok
    EndDrawing()
end
CloseWindow()

func newBall
    nBallX = GetRandomValue(20, WIDTH - 20)
    nBallY = 0

func caught nPaddleX, nBallX, nBallY
    if nBallY >= HEIGHT - 30 and nBallX >= nPaddleX and nBallX <= nPaddleX + 100
        return 1
    ok
    return 0

func clamp n, nMin, nMax
    if n < nMin return nMin ok
    if n > nMax return nMax ok
    return n
```

لتشغيلها في RAD IDE: أنشئ مشروع **Console Application (Ring)** والصق الكود في `main.ring`، ثم `Ctrl+F5`. (أو اضغط «جرّبه».)

### أفكار لتطويرها

- `GetRandomValue(min, max)` تعطي رقمًا عشوائيًا: جرّب كرة لونها عشوائي.
- أضف كرة «ذهبية» تعطي 5 نقاط.
- أضف صوتًا عند الالتقاط: `InitAudioDevice()` ثم `oSound = LoadSound("catch.wav")` ثم `PlaySound(oSound)`.

## مشروع Ring Game في RAD IDE

لألعاب أكبر فيها مراحل وشخصيات، يقدم RAD IDE نوع مشروع خاصًا:

1. **File > New Project...** ثم مجموعة **Games** واختر **Ring Game (RingRayLib)** (لعبة Ring (RingRayLib)).
2. اختر قالبًا: **Platformer (Ring)** (لعبة قفز) أو **Top-down Game (Ring)** (لعبة من أعلى) أو **Empty Game (Ring)** (فارغة).
3. يفتح **مصمم المشاهد** (scene designer): ترسم فيه المرحلة وتضع اللاعب والعملات والأعداء بالفأرة، وتضبط خصائصها من **Properties**.
4. كود كل مشهد في ملف `<Scene>.ring`، والأحداث بأسلوب VB مثل `func Player_Collide oOther`، ومعك دوال جاهزة مثل `AddScore(points)` و`GoToScene(name)` و`ShowMessage(text, seconds)`.
5. `F5` يشغّل اللعبة، ويمكنك وضع نقاط توقف وتتبع الكود كأي برنامج Ring.

## أخطاء شائعة

- **نسيان `BeginDrawing()` و`EndDrawing()`:** لا يظهر شيء في النافذة.
- **الرسم قبل `ClearBackground`:** تظهر آثار الإطارات السابقة خلف الأشياء المتحركة.
- **حلقة بدون `WindowShouldClose()`:** لا تستطيع إغلاق النافذة. أوقفها بـ `Shift+F5`.
- **كتابة نص عربي بـ `DrawText`:** يظهر علامات استفهام.

## تمارين

### التمرين 1: هل خرج من الشاشة؟

اكتب دالة `outside(x, y)` تُرجع `1` إذا كانت النقطة خارج نافذة عرضها 600 وارتفاعها 400، و`0` إذا كانت داخلها.

```ring exercise
see outside(100, 100) + nl
see outside(-5, 100) + nl
see outside(300, 450) + nl

func outside x, y
    # أكمل
```

```ring solution
see outside(100, 100) + nl
see outside(-5, 100) + nl
see outside(300, 450) + nl

func outside x, y
    if x < 0 or x > 600 or y < 0 or y > 400
        return 1
    ok
    return 0
```

```text output
0
1
1
```

### التمرين 2: تصادم دائرتين

دائرتان تتصادمان إذا كانت المسافة بين مركزيهما أقل من مجموع نصفي قطريهما. المسافة = `sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))`. اكتب الدالة `circlesHit`.

```ring exercise
see circlesHit(0, 0, 10, 15, 0, 10) + nl
see circlesHit(0, 0, 10, 50, 0, 10) + nl

func circlesHit x1, y1, r1, x2, y2, r2
    # أكمل
```

```ring solution
see circlesHit(0, 0, 10, 15, 0, 10) + nl
see circlesHit(0, 0, 10, 50, 0, 10) + nl

func circlesHit x1, y1, r1, x2, y2, r2
    nDist = sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1))
    if nDist < r1 + r2
        return 1
    ok
    return 0
```

```text output
1
0
```

> في RayLib دالة جاهزة لهذا: `CheckCollisionCircles(...)`، لكن من المفيد أن تفهم كيف تعمل.

## اختبر نفسك

```quiz
{"question": "ما الخطوات الثلاث في كل لفة من حلقة اللعبة؟", "choices": ["رسم ثم حفظ ثم إغلاق", "قراءة المدخلات ثم تحديث الحالة ثم الرسم", "تحميل ثم تشغيل ثم إيقاف", "طباعة ثم انتظار ثم قراءة"], "answer": 1, "explanation": "المدخلات، ثم التحديث، ثم الرسم: حوالي 60 مرة في الثانية."}
```

```quiz
{"question": "أين تقع النقطة (0, 0) في نافذة RayLib؟", "choices": ["في المنتصف", "الركن الأسفل الأيسر", "الركن الأعلى الأيسر", "الركن الأعلى الأيمن"], "answer": 2, "explanation": "y يزيد كلما نزلنا لأسفل."}
```

```quiz
{"question": "ما الفرق بين IsKeyDown و IsKeyPressed؟", "choices": ["لا فرق", "IsKeyDown طوال الضغط، وIsKeyPressed لحظة الضغط فقط", "IsKeyPressed للفأرة فقط", "IsKeyDown للحروف فقط"], "answer": 1, "explanation": "IsKeyDown للحركة المستمرة، وIsKeyPressed للأفعال التي تحدث مرة واحدة."}
```

## الخلاصة

- `load "raylib.ring"` ثم `InitWindow` وحلقة `while !WindowShouldClose()` و`CloseWindow`.
- كل الرسم بين `BeginDrawing()` و`EndDrawing()`.
- `IsKeyDown` للحركة، و`GetRandomValue` للعشوائية.
- اكتب منطق اللعبة في دوال صغيرة واختبرها، ولمشاريع أكبر استخدم **Ring Game (RingRayLib)**.
