# الدرس 6: التجميع والتلخيص: groupby و pivot_table

أهم أسئلة التحليل تبدأ بكلمة **«لكل»**: ما إجمالي المبيعات **لكل** مدينة؟ ما متوسط الراتب **لكل** قسم؟ كم طلبًا **لكل** شهر؟ هذه الأسئلة يجيب عنها **التجميع** (grouping).

> **تشبيه:** `groupby` مثل **فرز الإيصالات في أكوام**: تضع إيصالات كل مدينة في كومة، ثم تجمع أرقام كل كومة على حدة، ثم تكتب النتائج في جدول صغير. الفكرة اسمها: **قسّم ← طبّق ← اجمع** (split - apply - combine).

## البيانات

سنستخدم في هذا الدرس جدول مبيعات صغيرًا:

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "month":   ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb", "Mar", "Mar", "Mar"],
    "city":    ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "product": ["Pen", "Book", "Pen", "Book", "Pen", "Bag", "Bag", "Book", "Pen"],
    "amount":  [500, 320, 150, 640, 210, 900, 1200, 480, 260],
})
sales.groupby("city")["amount"].sum()
```

```text output
city
Alex     1010
Cairo    2340
Giza     1310
Name: amount, dtype: int64
```

اقرأ السطر الأخير هكذا: «جمّع `sales` حسب `city`، وخذ العمود `amount`، واحسب المجموع `sum` لكل مجموعة».

## دوال التلخيص

| الدالة | تحسب |
|---|---|
| `sum()` | المجموع |
| `mean()` | المتوسط |
| `count()` | العدد |
| `min()` / `max()` | أصغر / أكبر قيمة |
| `median()` | الوسيط |
| `nunique()` | عدد القيم المختلفة |

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "month":   ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb", "Mar", "Mar", "Mar"],
    "city":    ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "product": ["Pen", "Book", "Pen", "Book", "Pen", "Bag", "Bag", "Book", "Pen"],
    "amount":  [500, 320, 150, 640, 210, 900, 1200, 480, 260],
})

# %%
sales.groupby("product")["amount"].mean()

# %%
sales.groupby("month")["amount"].sum().sort_values(ascending=False)

# %%
sales.groupby("city")["product"].nunique()
```

```text output
product
Bag     1050.0
Book     480.0
Pen      280.0
Name: amount, dtype: float64
month
Mar    1940
Feb    1750
Jan     970
Name: amount, dtype: int64
city
Alex     2
Cairo    3
Giza     2
Name: product, dtype: int64
```

## عدة إحصائيات مرة واحدة: `agg`

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "city":   ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "amount": [500, 320, 150, 640, 210, 900, 1200, 480, 260],
})
summary = sales.groupby("city")["amount"].agg(["count", "sum", "mean", "max"])
summary

# %%
summary.sort_values("sum", ascending=False).head(1)
```

```text output
       count   sum        mean   max
city                                
Alex       3  1010  336.666667   480
Cairo      3  2340  780.000000  1200
Giza       3  1310  436.666667   900
       count   sum   mean   max
city                           
Cairo      3  2340  780.0  1200
```

ويمكنك تسمية الأعمدة الناتجة بنفسك:

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "city":   ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "amount": [500, 320, 150, 640, 210, 900],
})
sales.groupby("city").agg(orders=("amount", "count"), total=("amount", "sum"))
```

```text output
       orders  total
city                
Alex        2    530
Cairo       2   1140
Giza        2   1050
```

## التجميع بعمودين

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "month":   ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb"],
    "city":    ["Cairo", "Alex", "Cairo", "Cairo", "Alex", "Alex"],
    "amount":  [500, 320, 150, 640, 210, 900],
})
sales.groupby(["month", "city"])["amount"].sum()
```

```text output
month  city 
Feb    Alex     1110
       Cairo     640
Jan    Alex      320
       Cairo     650
Name: amount, dtype: int64
```

## الجدول المحوري: `pivot_table`

النتيجة السابقة صحيحة لكنها طويلة. **الجدول المحوري** (pivot table)، المعروف في Excel، يعرضها كمصفوفة: المدن صفوف والأشهر أعمدة:

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "month":   ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb", "Mar", "Mar", "Mar"],
    "city":    ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "amount":  [500, 320, 150, 640, 210, 900, 1200, 480, 260],
})
table = sales.pivot_table(index="city", columns="month", values="amount", aggfunc="sum")
table = table[["Jan", "Feb", "Mar"]]       # ترتيب الأشهر زمنيًا بدل الأبجدي
table

# %%
table["Total"] = table.sum(axis=1)
table.sort_values("Total", ascending=False)
```

```text output
month  Jan  Feb   Mar
city                 
Alex   320  210   480
Cairo  500  640  1200
Giza   150  900   260
month  Jan  Feb   Mar  Total
city                        
Cairo  500  640  1200   2340
Giza   150  900   260   1310
Alex   320  210   480   1010
```

- `index`: ما يصبح صفوفًا، و`columns`: ما يصبح أعمدة، و`values`: ما نحسبه، و`aggfunc`: كيف نحسبه.
- `table.sum(axis=1)` تجمع **أفقيًا** (كل صف)، و`axis=0` (الافتراضي) تجمع رأسيًا (كل عمود).

## النسب المئوية

```python notebook run
# %%
import pandas as pd

sales = pd.DataFrame({
    "city":   ["Cairo", "Alex", "Giza", "Cairo", "Alex", "Giza"],
    "amount": [500, 320, 150, 640, 210, 900],
})
by_city = sales.groupby("city")["amount"].sum()
share = (by_city / by_city.sum() * 100).round(1)
share
```

```text output
city
Alex     19.5
Cairo    41.9
Giza     38.6
Name: amount, dtype: float64
```

## اختبر نفسك

```quiz
{"question": "ماذا يحسب sales.groupby(\"city\")[\"amount\"].mean()؟", "choices": ["متوسط كل المبيعات", "متوسط المبيعات لكل مدينة", "عدد المدن", "أكبر مدينة"], "answer": 1, "explanation": "groupby يقسم الصفوف حسب المدينة، ثم mean تحسب المتوسط لكل مجموعة."}
```

```quiz
{"question": "في pivot_table، ما الذي يحدده المعامل columns؟", "choices": ["القيم التي نحسبها", "ما يصبح أعمدة في الجدول الناتج", "دالة التجميع", "عدد الأعمدة"], "answer": 1, "explanation": "index للصفوف، وcolumns للأعمدة، وvalues للقيم، وaggfunc للدالة."}
```

```quiz
{"question": "ما وظيفة agg([\"sum\", \"mean\"])؟", "choices": ["ترتيب الجدول", "حساب عدة إحصائيات لكل مجموعة مرة واحدة", "حذف الأعمدة", "دمج جدولين"], "answer": 1, "explanation": "agg تطبق عدة دوال تلخيص وتعرض كل واحدة في عمود."}
```

## الخلاصة

- `df.groupby("col")["value"].sum()`: قسّم ← طبّق ← اجمع.
- `agg` لعدة إحصائيات، ويمكن تسمية النواتج: `agg(total=("amount", "sum"))`.
- `pivot_table(index=..., columns=..., values=..., aggfunc=...)` للجداول المحورية.
- `sum(axis=1)` للمجموع الأفقي، والقسمة على المجموع الكلي للنسب المئوية.
