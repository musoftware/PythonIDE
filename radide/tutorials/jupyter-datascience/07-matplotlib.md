# الدرس 7: الرسوم البيانية بـ matplotlib

«الصورة تساوي ألف كلمة»، وفي تحليل البيانات **الرسم البياني يساوي ألف صف**. نمط يصعب رؤيته في جدول من مئة رقم يظهر فورًا في رسم واحد. أشهر مكتبة رسم في Python هي **matplotlib**، وفي الدفتر تظهر الرسوم **تحت الخلية مباشرة**.

## أول رسم

```python notebook run
# %%
import matplotlib.pyplot as plt

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
sales = [120, 98, 143, 110, 160, 131]

plt.plot(months, sales)
plt.title("Monthly sales")
plt.show()
print("تم الرسم")
```

```text output
تم الرسم
```

شغّل الخلية في الـ IDE فيظهر خط بياني يصعد ويهبط مع المبيعات. لاحظ:

- `import matplotlib.pyplot as plt`: الاسم المختصر `plt` عادة عالمية مثل `pd`.
- `plt.plot(x, y)` ترسم خطًا، و`plt.title` تضع العنوان.
- `plt.show()` تعرض الرسم. في الدفتر تظهر الرسوم حتى بدونها، لكن كتابتها عادة جيدة، وتمنع ظهور نص غريب مثل `[<matplotlib.lines.Line2D at 0x...>]` تحت الخلية.

> **ملحوظة:** في الدروس هنا يظهر في «الناتج» النص المطبوع فقط، أما الرسم نفسه فتراه عندما تضغط «جرّبه» ويُفتح الدفتر في الـ IDE.

## أنواع الرسوم الأساسية

| النوع | الدالة | متى نستخدمه |
|---|---|---|
| خطي | `plt.plot(x, y)` | تغيّر قيمة عبر الزمن |
| أعمدة | `plt.bar(x, y)` | مقارنة فئات (مدن، منتجات) |
| أعمدة أفقية | `plt.barh(y, x)` | فئات أسماؤها طويلة |
| مدرج تكراري | `plt.hist(values, bins=10)` | توزيع القيم (كم قيمة في كل مدى) |
| انتشار | `plt.scatter(x, y)` | العلاقة بين متغيرين |
| دائري | `plt.pie(values, labels=...)` | نسب أجزاء من كل (استخدمه بقلة) |

## الطريقة الاحترافية: `fig, ax`

للتحكم الكامل (عدة رسوم، وأحجام، وتنسيق) استخدم **الشكل** (figure) و**المحاور** (axes):

```python notebook run
# %%
import matplotlib.pyplot as plt

cities = ["Cairo", "Alex", "Giza", "Aswan"]
orders = [340, 210, 180, 60]

fig, ax = plt.subplots(figsize=(6, 3))
bars = ax.bar(cities, orders, color="#2a7ab0")
ax.set_title("Orders per city")
ax.set_xlabel("City")
ax.set_ylabel("Orders")
ax.bar_label(bars)                 # اكتب القيمة فوق كل عمود
ax.grid(axis="y", alpha=0.3)
plt.show()
print("عدد الأعمدة:", len(bars))
```

```text output
عدد الأعمدة: 4
```

- `plt.subplots(figsize=(6, 3))` ينشئ شكلًا عرضه 6 بوصات وارتفاعه 3، فيه محور واحد `ax`.
- كل دوال التنسيق على المحور تبدأ بـ `set_`: `set_title` و`set_xlabel` و`set_ylabel` و`set_ylim`...

## رسمان جنبًا إلى جنب

```python notebook run
# %%
import matplotlib.pyplot as plt

months = ["Jan", "Feb", "Mar", "Apr"]
sales = [120, 98, 143, 110]
cost = [80, 70, 90, 75]

fig, (left, right) = plt.subplots(1, 2, figsize=(9, 3))
left.plot(months, sales, marker="o", label="sales")
left.plot(months, cost, marker="s", label="cost")
left.set_title("Sales vs cost")
left.legend()

profit = [s - c for s, c in zip(sales, cost)]
right.bar(months, profit, color="green")
right.set_title("Profit")
fig.tight_layout()                 # يمنع تداخل العناوين
plt.show()
print("الربح:", profit)
```

```text output
الربح: [40, 28, 53, 35]
```

`label=` مع `legend()` تضيف **مفتاح الرسم** الذي يوضح أي خط لأي بيانات.

## الرسم مباشرة من pandas

جداول pandas تعرف كيف ترسم نفسها (وتستخدم matplotlib في الخلفية):

```python notebook run
# %%
import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame({
    "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    "sales": [120, 98, 143, 110, 160, 131],
    "cost": [80, 70, 90, 75, 101, 88],
})
ax = df.plot(x="month", y=["sales", "cost"], kind="bar", figsize=(6, 3), title="Sales and cost")
ax.set_ylabel("EGP (thousands)")
plt.show()

# %%
df["profit"] = df["sales"] - df["cost"]
df["profit"].plot(kind="hist", bins=4, title="Profit distribution")
plt.show()
df["profit"].describe().round(1)
```

```text output
count     6.0
mean     43.0
std      11.4
min      28.0
25%      36.2
50%      41.5
75%      50.5
max      59.0
Name: profit, dtype: float64
```

`kind` يحدد النوع: `"line"` و`"bar"` و`"barh"` و`"hist"` و`"scatter"` و`"pie"`.

## حفظ الرسم في ملف

```python notebook run
# %%
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 3))
ax.pie([45, 30, 25], labels=["Online", "Store", "Phone"], autopct="%1.0f%%")
ax.set_title("Orders by channel")
fig.savefig("channels.png", dpi=120, bbox_inches="tight")
plt.close(fig)

from pathlib import Path
print("الملف موجود:", Path("channels.png").exists())
```

```text output
الملف موجود: True
```

الصورة تُحفظ في مجلد الدفتر، وتستطيع وضعها في تقرير أو عرض تقديمي. `plt.close(fig)` تغلق الشكل دون عرضه.

## النصوص العربية في الرسوم

matplotlib لا تدعم ربط الحروف العربية واتجاهها تلقائيًا، فقد تظهر الكلمات حروفًا متقطعة معكوسة. الحل الأسهل: اكتب عناوين الرسوم بالإنجليزية. وإن احتجت العربية فاستخدم المكتبتين `arabic-reshaper` و`python-bidi` (ثبّتهما من **Manage Packages**):

```python
import arabic_reshaper
from bidi.algorithm import get_display

def ar(text):
    return get_display(arabic_reshaper.reshape(text))

ax.set_title(ar("المبيعات الشهرية"))
```

## نصائح لرسم واضح

1. **عنوان ومحاور مسماة دائمًا**، ووحدة القياس في اسم المحور.
2. اختر النوع المناسب: الزمن ← خطي، والمقارنة ← أعمدة، والتوزيع ← مدرج.
3. ابدأ محور الأعمدة من الصفر، وإلا بالغت الفروق في عين القارئ.
4. لا تكثر الألوان: لون واحد للبيانات، ولون مختلف لما تريد إبرازه فقط.

## اختبر نفسك

```quiz
{"question": "أي نوع رسم هو الأنسب لعرض تغير المبيعات على مدى 12 شهرًا؟", "choices": ["دائري", "خطي", "انتشار", "مدرج تكراري"], "answer": 1, "explanation": "الرسم الخطي يوضح التغير عبر الزمن."}
```

```quiz
{"question": "ماذا تُرجع plt.subplots(1, 2)؟", "choices": ["محورًا واحدًا", "الشكل fig ومحورين جنبًا إلى جنب", "صورة PNG", "جدول بيانات"], "answer": 1, "explanation": "صف واحد وعمودان: fig ومحوران نرسم على كل منهما."}
```

```quiz
{"question": "كيف تحفظ الرسم في ملف صورة؟", "choices": ["plt.show(\"file.png\")", "fig.savefig(\"file.png\")", "ax.save(\"file.png\")", "df.to_png()"], "answer": 1, "explanation": "savefig تحفظ الشكل بصيغة يحددها الامتداد (png أو jpg أو pdf أو svg)."}
```

## الخلاصة

- `import matplotlib.pyplot as plt`، والرسوم تظهر تحت الخلية في الدفتر.
- `plot` و`bar` و`hist` و`scatter` و`pie` لأنواع الرسوم، و`fig, ax = plt.subplots()` للتحكم الكامل.
- `df.plot(kind=...)` يرسم من pandas مباشرة، و`fig.savefig` يحفظ الصورة.
- عنوان ومحاور واضحة، والعربية تحتاج `arabic-reshaper` و`python-bidi`.
