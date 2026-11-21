# الدرس 5: استكشاف البيانات وتنظيفها

البيانات الحقيقية **ليست نظيفة أبدًا**: خانات فارغة، وصفوف مكررة، وأرقام مكتوبة كنصوص، وأخطاء إملائية. يقول علماء البيانات إن 80% من وقتهم يذهب في التنظيف! في هذا الدرس نقرأ ملف CSV ونستكشفه وننظفه.

## قراءة ملف CSV

ضع الملف `orders.csv` بجانب الدفتر (في نفس المجلد)، ثم:

```python notebook run
# %%
import pandas as pd

df = pd.read_csv("orders.csv")
df

# #file: orders.csv
order_id,date,customer,city,product,qty,price
1,2026-01-03,Ali,Cairo,Pen,10,5
2,2026-01-03,Sara,alex,Book,2,40
3,2026-01-05,Omar,Cairo,Bag,,150
4,2026-01-07,Mona,Giza,Pen,25,5
5,2026-01-07,Mona,Giza,Pen,25,5
6,2026-01-09,Karim,Alex,Book,1,
7,2026-01-12,Huda,Cairo,Bag,1,150
8,2026-01-15,Ali,Cairo,Book,3,40
```

```text output
   order_id        date customer   city product   qty  price
0         1  2026-01-03      Ali  Cairo     Pen  10.0    5.0
1         2  2026-01-03     Sara   alex    Book   2.0   40.0
2         3  2026-01-05     Omar  Cairo     Bag   NaN  150.0
3         4  2026-01-07     Mona   Giza     Pen  25.0    5.0
4         5  2026-01-07     Mona   Giza     Pen  25.0    5.0
5         6  2026-01-09    Karim   Alex    Book   1.0    NaN
6         7  2026-01-12     Huda  Cairo     Bag   1.0  150.0
7         8  2026-01-15      Ali  Cairo    Book   3.0   40.0
```

> **في هذا الدرس:** السطر `# #file: orders.csv` يفصل ملف البيانات عن الدفتر؛ زر «جرّبه» يضع `orders.csv` بجانب `notebook.ipynb`. وفي عملك الحقيقي ضع ملفاتك في مجلد الدفتر، أو اكتب المسار كاملًا مثل `pd.read_csv(r"C:\data\orders.csv")`.

`NaN` (Not a Number) تعني **قيمة ناقصة**: الخانة كانت فارغة في الملف.

ولقراءة ملفات Excel: `pd.read_excel("file.xlsx")` (تحتاج المكتبة `openpyxl`).

## الاستكشاف: ما الذي في الملف؟

```python notebook run
# %%
import pandas as pd
df = pd.read_csv("orders.csv")

# %%
df.dtypes

# %%
df.isna().sum()           # عدد القيم الناقصة في كل عمود

# %%
int(df.duplicated().sum())    # عدد الصفوف المكررة

# %%
df["city"].value_counts()

# #file: orders.csv
order_id,date,customer,city,product,qty,price
1,2026-01-03,Ali,Cairo,Pen,10,5
2,2026-01-03,Sara,alex,Book,2,40
3,2026-01-05,Omar,Cairo,Bag,,150
4,2026-01-07,Mona,Giza,Pen,25,5
5,2026-01-07,Mona,Giza,Pen,25,5
6,2026-01-09,Karim,Alex,Book,1,
7,2026-01-12,Huda,Cairo,Bag,1,150
8,2026-01-15,Ali,Cairo,Book,3,40
```

```text output
order_id      int64
date            str
customer        str
city            str
product         str
qty         float64
price       float64
dtype: object
order_id    0
date        0
customer    0
city        0
product     0
qty         1
price       1
dtype: int64
0
city
Cairo    4
Giza     2
alex     1
Alex     1
Name: count, dtype: int64
```

ماذا اكتشفنا؟

1. `qty` و`price` من النوع `float64` (عدد عشري) بدل أعداد صحيحة، بسبب القيم الناقصة. والأعمدة النصية نوعها `str` (في إصدارات pandas الأقدم من 3 يظهر `object` بدلًا منها، والمعنى واحد).
2. يوجد `qty` ناقص في صف، و`price` ناقص في صف آخر.
3. `df.duplicated()` لم تجد تكرارًا (`0`) لأن `order_id` مختلف، لكن الطلبين 4 و5 متطابقان في كل شيء آخر!
4. المدينة `alex` مكتوبة بحرف صغير مرة، و`Alex` مرة أخرى، فعُدّت مدينتين.

## التنظيف خطوة بخطوة

```python notebook run
# %%
import pandas as pd
df = pd.read_csv("orders.csv")

# %%
# 1) توحيد كتابة المدن: أول حرف كبير
df["city"] = df["city"].str.strip().str.title()

# 2) حذف الطلبات المكررة (نتجاهل order_id عند المقارنة)
df = df.drop_duplicates(subset=["date", "customer", "product", "qty", "price"])

# 3) السعر الناقص: نملؤه بسعر نفس المنتج من الصفوف الأخرى
df["price"] = df["price"].fillna(df.groupby("product")["price"].transform("max"))

# 4) الكمية الناقصة: نحذف الصف لأننا لا نعرفها
df = df.dropna(subset=["qty"])

# 5) الأنواع الصحيحة
df["qty"] = df["qty"].astype(int)
df["date"] = pd.to_datetime(df["date"])
df

# %%
df.dtypes

# %%
df["city"].value_counts()

# #file: orders.csv
order_id,date,customer,city,product,qty,price
1,2026-01-03,Ali,Cairo,Pen,10,5
2,2026-01-03,Sara,alex,Book,2,40
3,2026-01-05,Omar,Cairo,Bag,,150
4,2026-01-07,Mona,Giza,Pen,25,5
5,2026-01-07,Mona,Giza,Pen,25,5
6,2026-01-09,Karim,Alex,Book,1,
7,2026-01-12,Huda,Cairo,Bag,1,150
8,2026-01-15,Ali,Cairo,Book,3,40
```

```text output
   order_id       date customer   city product  qty  price
0         1 2026-01-03      Ali  Cairo     Pen   10    5.0
1         2 2026-01-03     Sara   Alex    Book    2   40.0
3         4 2026-01-07     Mona   Giza     Pen   25    5.0
5         6 2026-01-09    Karim   Alex    Book    1   40.0
6         7 2026-01-12     Huda  Cairo     Bag    1  150.0
7         8 2026-01-15      Ali  Cairo    Book    3   40.0
order_id             int64
date        datetime64[us]
customer               str
city                   str
product                str
qty                  int64
price              float64
dtype: object
city
Cairo    3
Alex     2
Giza     1
Name: count, dtype: int64
```

| الدالة | وظيفتها |
|---|---|
| `df.isna()` | `True` حيث توجد قيمة ناقصة |
| `df.dropna(subset=[...])` | تحذف الصفوف التي فيها قيم ناقصة في الأعمدة المحددة |
| `df.fillna(قيمة)` | تملأ القيم الناقصة |
| `df.drop_duplicates(subset=[...])` | تحذف الصفوف المكررة |
| `df["c"].astype(int)` | تحوّل نوع العمود |
| `pd.to_datetime(df["c"])` | تحوّل النص إلى تاريخ |
| `df["c"].str.title()` / `.str.strip()` / `.str.lower()` | دوال النصوص على عمود كامل |

> **مهم:** أغلب دوال pandas **ترجع جدولًا جديدًا** ولا تغيّر الأصلي، لذلك نكتب `df = df.dropna(...)`. تمامًا مثل دوال النصوص في Python.

## الفلترة: اختيار الصفوف بشرط

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "customer": ["Ali", "Sara", "Mona", "Huda", "Ali"],
    "city": ["Cairo", "Alex", "Giza", "Cairo", "Cairo"],
    "total": [50, 80, 125, 150, 120],
})

# %%
df[df["total"] > 100]

# %%
df[(df["city"] == "Cairo") & (df["total"] >= 100)]

# %%
df[df["city"].isin(["Alex", "Giza"])]
```

```text output
  customer   city  total
2     Mona   Giza    125
3     Huda  Cairo    150
4      Ali  Cairo    120
  customer   city  total
3     Huda  Cairo    150
4      Ali  Cairo    120
  customer  city  total
1     Sara  Alex     80
2     Mona  Giza    125
```

- الشرط `df["total"] > 100` ينتج عمودًا من `True`/`False`، ووضعه داخل `df[...]` يُبقي الصفوف الصحيحة فقط.
- لربط شرطين استخدم `&` (و) و`|` (أو)، **مع أقواس حول كل شرط**. لا تستخدم `and` و`or` هنا.

## الترتيب

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "customer": ["Ali", "Sara", "Mona", "Huda"],
    "total": [50, 80, 125, 150],
})
df.sort_values("total", ascending=False)

# %%
df.nlargest(2, "total")
```

```text output
  customer  total
3     Huda    150
2     Mona    125
1     Sara     80
0      Ali     50
  customer  total
3     Huda    150
2     Mona    125
```

## حفظ النتيجة

بعد التنظيف احفظ الجدول في ملف جديد (ولا تكتب فوق الملف الأصلي أبدًا):

```python
df.to_csv("orders_clean.csv", index=False)
df.to_excel("orders_clean.xlsx", index=False)    # يحتاج openpyxl
```

`index=False` تمنع كتابة عمود الفهرس `0, 1, 2...` في الملف.

## اختبر نفسك

```quiz
{"question": "ماذا تعني NaN في جدول pandas؟", "choices": ["صفر", "قيمة ناقصة", "نص فارغ دائمًا", "خطأ في الملف"], "answer": 1, "explanation": "NaN تمثل قيمة غير موجودة (خانة فارغة)."}
```

```quiz
{"question": "كيف تختار الصفوف التي فيها city تساوي Cairo و total أكبر من 100؟", "choices": ["df[df.city == \"Cairo\" and df.total > 100]", "df[(df[\"city\"] == \"Cairo\") & (df[\"total\"] > 100)]", "df.loc[\"Cairo\", 100]", "df.filter(\"Cairo\", 100)"], "answer": 1, "explanation": "مع pandas نستخدم & مع أقواس حول كل شرط."}
```

```quiz
{"question": "لماذا نكتب df = df.dropna() وليس df.dropna() فقط؟", "choices": ["لأنها أسرع", "لأن dropna ترجع جدولًا جديدًا ولا تغيّر df", "لأن Python تتطلب ذلك دائمًا", "لا فرق بينهما"], "answer": 1, "explanation": "أغلب دوال pandas ترجع نسخة جديدة، فيجب حفظها في المتغير."}
```

## الخلاصة

- `pd.read_csv` لقراءة الملفات، و`dtypes` و`isna().sum()` و`value_counts()` للاستكشاف.
- `str.title` و`drop_duplicates` و`fillna` و`dropna` و`astype` و`to_datetime` للتنظيف.
- الفلترة `df[شرط]` مع `&` و`|`، والترتيب `sort_values`، والحفظ `to_csv(index=False)`.
