# الدرس 2: إعداد المزودين: Ollama وClaude Code وGemini CLI

**في هذا الدرس ستتعلم:**

- فتح صفحة إعدادات الذكاء الاصطناعي وقراءة حالة كل مزود.
- تثبيت **Ollama** وتنزيل نموذج يعمل على جهازك دون إنترنت.
- ربط **Claude Code** و**Gemini CLI** بحسابك دون مفتاح API.
- اختيار **مزود افتراضي لكل غرض** (المحادثة، الإكمال، التعديل، الوكلاء، رسائل الإيداع).
- كيف تبدو الرسالة التي ترسلها البيئة إلى Ollama فعلًا.

## صفحة الإعدادات

افتح **Tools > AI Settings...** (بالعربية: **أدوات > إعدادات الذكاء الاصطناعي...**). هذه الصفحة هي نفسها **Tools > Options... > AI**.

ستجد جدولًا فيه كل المزودين بثلاثة أعمدة:

| العمود | معناه |
|---|---|
| **Provider** (المزوّد) | اسم المزود، مثل Ollama أو Claude Code |
| **Kind** (النوع) | `CLI (account)` أو `Local` أو `API key` أو `Web chat` |
| **Status** (الحالة) | `Ready` (جاهز) أو `Not ready` مع السبب، مثل «غير مثبت» أو «يحتاج تسجيل دخول» |

عندما تختار مزودًا تظهر تفاصيله تحت الجدول: **Model** (النموذج)، و**Base URL** للخوادم المحلية، و**API key** لخدمات المفاتيح، وأزرار مثل **Test** (اختبار) و**Sign in...** (تسجيل الدخول) و**Pull model...** (تنزيل نموذج) و**Install with npm** (التثبيت باستخدام npm).

> **زر Test** يرسل طلبًا صغيرًا جدًا («Reply with exactly: OK») ويعرض الرد. إذا ظهر `OK` فكل شيء يعمل.

## الطريق الأول: Ollama على جهازك (دون إنترنت)

**Ollama** برنامج مجاني يشغّل نماذج الذكاء الاصطناعي على جهازك. بعد التنزيل الأول لا يحتاج إنترنت، وكودك لا يغادر حاسوبك.

**الخطوة 1:** ثبّته من الطرفية (**View > Terminal**، `` Ctrl+` ``):

```text
winget install Ollama.Ollama
```

**الخطوة 2:** نزّل نموذجًا مناسبًا للبرمجة. النموذج الذي تقترحه البيئة:

```text
ollama pull qwen2.5-coder:7b
```

أو من البيئة نفسها: اختر **Ollama** في الجدول ثم اضغط **Pull model...** واكتب اسم النموذج.

**الخطوة 3:** اضغط **Refresh** ثم **Test**. البيئة تشغّل خادم Ollama تلقائيًا (`ollama serve`) إذا لم يكن يعمل.

> **حجم النموذج:** الرقم مثل `7b` يعني 7 مليارات «وزن». النماذج الأكبر أذكى لكنها تحتاج ذاكرة أكبر وتعمل أبطأ. على جهاز متوسط ابدأ بـ `7b` أو أصغر، مثل `qwen2.5-coder:1.5b` للإكمال السريع.

## الطريق الثاني: Claude Code وGemini CLI بحسابك

هذه برامج سطر أوامر رسمية تسجّل فيها الدخول **بحسابك أنت** مرة واحدة، والبيئة تستخدمها بعد ذلك دون مفتاح API:

| البرنامج | التثبيت | تسجيل الدخول |
|---|---|---|
| Claude Code | زر **Install with npm** (الحزمة `@anthropic-ai/claude-code`) | شغّل `claude` في الطرفية ثم `/login` |
| Gemini CLI | زر **Install with npm** (الحزمة `@google/gemini-cli`) | شغّل `gemini` واختر Login with Google (مجاني) |
| Codex CLI | الحزمة `@openai/codex` | `codex login` بحساب ChatGPT |

الزر **Sign in...** يفتح نافذة طرفية فيها أمر الدخول المناسب. بعد الدخول اضغط **Test**.

> **مهم:** برامج CLI تستهلك من **حصة حسابك**، لذلك لا تستخدمها البيئة للإكمال التلقائي أثناء الكتابة إلا إذا طلبته أنت بـ `Alt+\`.

## الطريق الثالث: مفتاح API (اختياري)

إذا كان عندك مفتاح من OpenAI أو Anthropic أو Gemini API أو OpenRouter أو Groq وغيرها، اختر المزود والصق المفتاح في خانة **API key**. يُحفظ المفتاح في **Windows Credential Manager** وليس في ملفات المشروع، ويمكنك حذفه بزر **Remove key**.

## المزود الافتراضي لكل غرض

في أسفل الصفحة مجموعة **Default provider for each purpose** (المزوّد الافتراضي لكل غرض). البيئة تستخدم الذكاء الاصطناعي في خمسة أغراض، ولكل غرض مزود ونموذج:

| الغرض | أين يُستخدم | نصيحة |
|---|---|---|
| Chat | نافذة AI Chat | نموذج قوي (Claude Code أو Gemini CLI أو نموذج محلي كبير) |
| Inline completion | النص الرمادي أثناء الكتابة | نموذج محلي **صغير وسريع** |
| Inline edit (Ctrl+I) | التعديل بالتحديد | نموذج متوسط أو قوي |
| Agents | مدير الوكلاء | أقوى نموذج متاح عندك |
| Commit messages | رسالة الإيداع في Git | أي نموذج سريع |

اترك أي غرض على **Auto** (تلقائي) لتختار البيئة أفضل مزود مجاني متاح.

## ماذا ترسل البيئة إلى Ollama؟

Ollama خادم صغير على جهازك يستمع على العنوان `http://127.0.0.1:11434`. البيئة ترسل إليه طلب HTTP فيه اسم النموذج والرسائل. هذا المثال **يبني** نص الطلب ويطبعه فقط، دون أن يتصل بأي شيء:

```python run
import json

request = {
    "model": "qwen2.5-coder:7b",
    "messages": [
        {"role": "user", "content": "اكتب دالة تجمع رقمين"},
    ],
    "stream": True,
}

url = "http://127.0.0.1:11434" + "/api/chat"
print("POST", url)
print(json.dumps(request, ensure_ascii=False, indent=2))
```

```text output
POST http://127.0.0.1:11434/api/chat
{
  "model": "qwen2.5-coder:7b",
  "messages": [
    {
      "role": "user",
      "content": "اكتب دالة تجمع رقمين"
    }
  ],
  "stream": true
}
```

لاحظ `"stream": true`: معناه «أرسل الإجابة **قطعة قطعة** وأنت تكتبها»، ولهذا ترى الإجابة في البيئة تظهر كلمة كلمة بدل أن تنتظر حتى تكتمل.

## كيف تصل الإجابة قطعة قطعة؟

يرسل Ollama الإجابة أسطرًا، كل سطر كائن JSON فيه جزء صغير من النص، وآخر سطر فيه `"done": true`. هذه المحاكاة تستخدم أسطرًا جاهزة (لا اتصال حقيقي) وتجمع القطع كما تفعل البيئة:

```python run
import json

# أسطر كما يرسلها Ollama (نسخة مختصرة للتجربة)
lines = [
    '{"message": {"content": "def "}, "done": false}',
    '{"message": {"content": "add(a, b):"}, "done": false}',
    '{"message": {"content": " return a + b"}, "done": false}',
    '{"done": true}',
]

answer = ""
for line in lines:
    part = json.loads(line)
    if part.get("done"):
        break
    piece = part["message"]["content"]
    answer += piece
    print("وصلت قطعة:", repr(piece))

print("الإجابة كاملة:", answer)
```

```text output
وصلت قطعة: 'def '
وصلت قطعة: 'add(a, b):'
وصلت قطعة: ' return a + b'
الإجابة كاملة: def add(a, b): return a + b
```

## أخطاء شائعة

- **Ollama is not running:** الخادم متوقف ولم يستطع البدء. افتح الطرفية واكتب `ollama serve`، أو أعد تثبيت Ollama.
- **لا توجد نماذج:** ثبّت Ollama ولم تنزّل أي نموذج. استخدم `ollama pull` أو زر **Pull model...**.
- **Installed but not signed in:** برنامج CLI مثبت لكنك لم تسجل الدخول. اضغط **Sign in...**.
- **نموذج كبير على جهاز ضعيف:** الإجابة بطيئة جدًا أو يتوقف الجهاز. جرّب نموذجًا أصغر.
- **لصق المفتاح في ملف الكود:** لا تكتب مفاتيح API في الكود أبدًا. ضعها في خانة **API key** فقط.

## تمارين

### تمرين 1: طلب لنموذج آخر

عدّل المثال ليستخدم النموذج `qwen2.5-coder:1.5b` ويطلب «اشرح الحلقة for»، وأن يكون `"stream"` بالقيمة `False`. اطبع اسم النموذج وقيمة `stream` فقط.

```python exercise
request = {
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "اكتب دالة تجمع رقمين"}],
    "stream": True,
}
print(request["model"], request["stream"])
```

```python solution
request = {
    "model": "qwen2.5-coder:1.5b",
    "messages": [{"role": "user", "content": "اشرح الحلقة for"}],
    "stream": False,
}
print(request["model"], request["stream"])
```

```text output
qwen2.5-coder:1.5b False
```

### تمرين 2: عدّاد القطع

عدّل محاكاة البث بحيث تطبع في النهاية **عدد القطع** التي وصلت، بدل طباعة كل قطعة.

```python exercise
import json

lines = [
    '{"message": {"content": "مرحبًا"}, "done": false}',
    '{"message": {"content": " يا"}, "done": false}',
    '{"message": {"content": " صديقي"}, "done": false}',
    '{"done": true}',
]
answer = ""
# أكمل: اجمع القطع واحسب عددها
```

```python solution
import json

lines = [
    '{"message": {"content": "مرحبًا"}, "done": false}',
    '{"message": {"content": " يا"}, "done": false}',
    '{"message": {"content": " صديقي"}, "done": false}',
    '{"done": true}',
]
answer = ""
count = 0
for line in lines:
    part = json.loads(line)
    if part.get("done"):
        break
    answer += part["message"]["content"]
    count += 1
print(answer)
print("عدد القطع:", count)
```

```text output
مرحبًا يا صديقي
عدد القطع: 3
```

### تمرين 3 (عملي في البيئة)

افتح **Tools > AI Settings...**، واختر مزودًا حالته **Ready**، ثم اضغط **Test**. بعدها اجعل **Inline completion** يستخدم أصغر نموذج محلي عندك، واترك **Chat** على **Auto**.

## اختبر نفسك

```quiz
{"question": "على أي عنوان يستمع خادم Ollama افتراضيًا؟", "choices": ["http://127.0.0.1:11434", "https://ollama.com", "http://localhost:8080", "http://127.0.0.1:1234"], "answer": 0, "explanation": "Ollama يستمع على المنفذ 11434 على جهازك. أما 1234 فهو المنفذ الافتراضي لـ LM Studio."}
```

```quiz
{"question": "لماذا لا تستخدم البيئة برامج CLI للإكمال التلقائي أثناء الكتابة؟", "choices": ["لأنها لا تفهم الكود", "لأنها تستهلك حصة حسابك وأبطأ، فتُستخدم فقط عند الطلب بـ Alt+\\", "لأنها تحتاج إنترنت دائمًا", "لأنها ممنوعة"], "answer": 1, "explanation": "الإكمال يرسل طلبات كثيرة جدًا، لذلك يُفضّل له نموذج محلي سريع."}
```

```quiz
{"question": "ماذا يعني \"stream\": true في الطلب؟", "choices": ["حفظ المحادثة", "إرسال الإجابة قطعة قطعة أثناء توليدها", "تشغيل الفيديو", "تشفير الرسالة"], "answer": 1, "explanation": "البث يجعل الإجابة تظهر تدريجيًا بدل انتظار اكتمالها."}
```

```quiz
{"question": "أين يُحفظ مفتاح API الذي تكتبه في الإعدادات؟", "choices": ["في ملف project.radproj", "في كود البرنامج", "في Windows Credential Manager", "لا يُحفظ أبدًا"], "answer": 2, "explanation": "المفاتيح لا تُكتب في ملفات المشروع، بل في مخزن كلمات المرور الآمن في ويندوز."}
```

## الخلاصة

- **Tools > AI Settings...** تعرض كل المزودين وحالتهم وتختبرها بزر **Test**.
- Ollama يعمل على جهازك دون إنترنت: `winget install Ollama.Ollama` ثم `ollama pull`.
- Claude Code وGemini CLI يعملان بحسابك بعد تسجيل الدخول مرة واحدة.
- لكل غرض (محادثة، إكمال، تعديل، وكلاء، إيداع) مزود افتراضي، و**Auto** يختار لك.
