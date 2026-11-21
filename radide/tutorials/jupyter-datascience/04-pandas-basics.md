# الدرس 4: مقدمة pandas: Series و DataFrame

**pandas** هي المكتبة الأشهر في Python للتعامل مع **البيانات الجدولية**: جداول بصفوف وأعمدة مثل جداول Excel، لكن بقوة البرمجة. تقرأ ملفات CSV وExcel، وتفلتر وترتّب وتجمّع وتحسب، في أسطر قليلة.

> **تشبيه:** إذا كانت القائمة في Python مثل **عمود واحد** من الأرقام مكتوب على ورقة، فإن DataFrame مثل **ورقة Excel كاملة**: أعمدة لها أسماء، وصفوف لها أرقام، وكل عمود من نوع واحد.

## التثبيت والاستيراد

إذا لم تكن pandas مثبتة في Python الدفتر، ثبّتها من **Project > Manage Packages...** (ابحث عن `pandas`) ثم أعد تشغيل النواة. والعادة المتفق عليها عالميًا أن نستوردها باسم مختصر `pd`:

```python notebook run
# %%
import pandas as pd
pd.__version__ >= "2"
```

```text output
True
```

## Series: عمود واحد

**Series** قائمة من القيم لها **فهرس** (index) يسمّي كل قيمة:

```python notebook run
# %%
import pandas as pd

temps = pd.Series([18, 21, 25, 30], index=["Jan", "Feb", "Mar", "Apr"])
temps

# %%
temps["Mar"]

# %%
temps.mean()

# %%
temps + 2
```

```text output
Jan    18
Feb    21
Mar    25
Apr    30
dtype: int64
np.int64(25)
np.float64(23.5)
Jan    20
Feb    23
Mar    27
Apr    32
dtype: int64
```

لاحظ السطر الأخير `temps + 2`: أضاف 2 إلى **كل** القيم دفعة واحدة دون حلقة `for`. هذه **العمليات المتجهة** (vectorized) سر قوة pandas وسرعتها.

> **ما معنى `np.int64(25)`؟** pandas تخزن الأرقام بأنواع مكتبة **NumPy** السريعة، فيعرض الدفتر القيمة المفردة مع نوعها: `np.int64(25)` هي ببساطة العدد `25`، و`np.float64(23.5)` هي `23.5`. إذا أردتها بلا هذه الإضافة فاكتب `print(temps.mean())` أو `float(temps.mean())`.

## `DataFrame`: جدول كامل

أسهل طريقة لإنشاء DataFrame من قاموس: كل مفتاح اسم عمود، وكل قيمة قائمة بقيم العمود:

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "name": ["Ali", "Sara", "Omar", "Mona", "Karim"],
    "age": [25, 31, 19, 28, 35],
    "city": ["Cairo", "Alex", "Cairo", "Giza", "Alex"],
    "salary": [7000, 9500, 4000, 8200, 12000],
})
df
```

```text output
    name  age   city  salary
0    Ali   25  Cairo    7000
1   Sara   31   Alex    9500
2   Omar   19  Cairo    4000
3   Mona   28   Giza    8200
4  Karim   35   Alex   12000
```

> **في الـ IDE:** يظهر الجدول تحت الخلية **جدولًا منسقًا** بخطوط وألوان، أما هنا في الدرس فنعرض شكله النصي.

الأرقام `0` إلى `4` على اليسار هي **الفهرس**، وتعطيها pandas تلقائيًا.

## نظرة سريعة على الجدول

| الأمر | ماذا يعرض |
|---|---|
| `df.head(n)` | أول `n` صفوف (5 افتراضيًا) |
| `df.tail(n)` | آخر `n` صفوف |
| `df.shape` | (عدد الصفوف، عدد الأعمدة) |
| `df.columns` | أسماء الأعمدة |
| `df.dtypes` | نوع كل عمود |
| `df.info()` | ملخص: الأنواع والقيم الناقصة |
| `df.describe()` | إحصائيات الأعمدة الرقمية |

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "name": ["Ali", "Sara", "Omar", "Mona", "Karim"],
    "age": [25, 31, 19, 28, 35],
    "city": ["Cairo", "Alex", "Cairo", "Giza", "Alex"],
    "salary": [7000, 9500, 4000, 8200, 12000],
})

# %%
df.head(2)

# %%
df.shape

# %%
list(df.columns)

# %%
df.describe()
```

```text output
   name  age   city  salary
0   Ali   25  Cairo    7000
1  Sara   31   Alex    9500
(5, 4)
['name', 'age', 'city', 'salary']
           age        salary
count   5.0000      5.000000
mean   27.6000   8140.000000
std     6.0663   2966.142276
min    19.0000   4000.000000
25%    25.0000   7000.000000
50%    28.0000   8200.000000
75%    31.0000   9500.000000
max    35.0000  12000.000000
```

`describe()` تعطيك في سطر واحد: العدد (`count`)، والمتوسط (`mean`)، والانحراف المعياري (`std`)، وأصغر قيمة (`min`)، والأرباع (`25%` و`50%` وهو الوسيط و`75%`)، وأكبر قيمة (`max`).

## اختيار الأعمدة

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "name": ["Ali", "Sara", "Omar", "Mona", "Karim"],
    "age": [25, 31, 19, 28, 35],
    "salary": [7000, 9500, 4000, 8200, 12000],
})

# %%
df["salary"]            # عمود واحد = Series

# %%
df[["name", "age"]]     # عدة أعمدة = DataFrame (لاحظ القوسين المزدوجين)

# %%
df["salary"].max()
```

```text output
0     7000
1     9500
2     4000
3     8200
4    12000
Name: salary, dtype: int64
    name  age
0    Ali   25
1   Sara   31
2   Omar   19
3   Mona   28
4  Karim   35
np.int64(12000)
```

## اختيار الصفوف: `loc` و `iloc`

- `df.iloc[رقم]` تختار بـ **الموقع** (الصف الأول = 0)، مثل القوائم.
- `df.loc[فهرس]` تختار بـ **اسم الفهرس**، ويمكن معه تحديد الأعمدة: `df.loc[صفوف, أعمدة]`.

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "name": ["Ali", "Sara", "Omar"],
    "age": [25, 31, 19],
    "salary": [7000, 9500, 4000],
})

# %%
df.iloc[0]

# %%
df.loc[1, "name"]

# %%
df.loc[0:1, ["name", "salary"]]
```

```text output
name       Ali
age         25
salary    7000
Name: 0, dtype: object
'Sara'
   name  salary
0   Ali    7000
1  Sara    9500
```

> **انتبه:** `df.loc[0:1]` **تشمل** الصف 1 (لأنها بالأسماء)، بخلاف تقطيع القوائم في Python. أما `df.iloc[0:1]` فلا تشمله، مثل القوائم تمامًا.

## إضافة عمود محسوب

```python notebook run
# %%
import pandas as pd

df = pd.DataFrame({
    "product": ["Pen", "Book", "Bag"],
    "price": [5.0, 40.0, 150.0],
    "qty": [30, 4, 2],
})
df["total"] = df["price"] * df["qty"]
df["tax"] = (df["total"] * 0.14).round(2)
df
```

```text output
  product  price  qty  total   tax
0     Pen    5.0   30  150.0  21.0
1    Book   40.0    4  160.0  22.4
2     Bag  150.0    2  300.0  42.0
```

عملية واحدة على عمودين تُطبّق على كل الصفوف معًا.

## اختبر نفسك

```quiz
{"question": "ما الفرق بين Series و DataFrame؟", "choices": ["لا فرق", "Series عمود واحد، وDataFrame جدول من عدة أعمدة", "DataFrame للنصوص فقط", "Series أسرع دائمًا"], "answer": 1, "explanation": "Series قيم بفهرس (عمود واحد)، وDataFrame مجموعة أعمدة تشترك في نفس الفهرس."}
```

```quiz
{"question": "كيف تختار العمودين name و age معًا؟", "choices": ["df[\"name\", \"age\"]", "df[[\"name\", \"age\"]]", "df.name.age", "df.loc[\"name\", \"age\"]"], "answer": 1, "explanation": "عدة أعمدة تُمرر كقائمة داخل الأقواس، فيظهر قوسان مزدوجان."}
```

```quiz
{"question": "ماذا يعرض df.shape لجدول فيه 20 صفًا و3 أعمدة؟", "choices": ["60", "(3, 20)", "(20, 3)", "20"], "answer": 2, "explanation": "shape = (عدد الصفوف، عدد الأعمدة)."}
```

## الخلاصة

- `import pandas as pd`، وSeries عمود واحد، وDataFrame جدول كامل.
- `head` و`shape` و`columns` و`describe` لنظرة سريعة.
- `df["col"]` و`df[["a", "b"]]` للأعمدة، و`iloc` بالموقع و`loc` بالاسم للصفوف.
- العمليات على الأعمدة تُطبَّق على كل الصفوف دفعة واحدة.
