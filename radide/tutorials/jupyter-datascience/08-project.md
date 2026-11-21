# الدرس 8: مشروع: تحليل مبيعات متجر وتصدير النتائج

حان وقت تطبيق كل ما تعلمته في تحليل كامل من البداية للنهاية. أنت محلل بيانات في متجر أدوات مكتبية له ثلاثة فروع، والمدير يسألك:

1. ما إجمالي المبيعات والربح في الربع الأول؟
2. أي فرع هو الأفضل؟ وأي منتج؟
3. هل المبيعات تنمو من شهر لآخر؟
4. أعطني رسمًا واحدًا يلخص الوضع.

## الخطوة 0: تجهيز المشروع

1. أنشئ مجلدًا للتحليل، أو مشروعًا جديدًا، وضع فيه ملف البيانات `sales_q1.csv`.
2. **File ← New Notebook ← Blank Notebook (.ipynb)...** واحفظه باسم `sales_analysis.ipynb` في نفس المجلد.
3. اكتب في أول خلية **Markdown** عنوان التحليل وهدفه. التقرير الجيد يشرح نفسه.

## الدفتر كاملًا

```python notebook run
# %% [markdown]
# # تحليل مبيعات الربع الأول 2026
# الهدف: معرفة إجمالي المبيعات والربح، وأفضل فرع ومنتج، واتجاه النمو الشهري.

# %%
# 1) الاستيراد وقراءة البيانات
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("sales_q1.csv", parse_dates=["date"])
print("الصفوف والأعمدة:", df.shape)
df.head()

# %%
# 2) التنظيف: القيم الناقصة والمكررة
print("قيم ناقصة:", int(df.isna().sum().sum()))
print("صفوف مكررة:", int(df.duplicated().sum()))
df = df.drop_duplicates()
df["branch"] = df["branch"].str.strip().str.title()
print("بعد التنظيف:", len(df), "صفًا")

# %%
# 3) أعمدة محسوبة
df["revenue"] = df["qty"] * df["price"]
df["profit"] = df["qty"] * (df["price"] - df["cost"])
df["month"] = df["date"].dt.strftime("%Y-%m")
print(f"إجمالي المبيعات: {df['revenue'].sum():,} جنيه")
print(f"إجمالي الربح: {df['profit'].sum():,} جنيه")
print(f"هامش الربح: {df['profit'].sum() / df['revenue'].sum():.1%}")

# %%
# 4) أفضل فرع
by_branch = df.groupby("branch")[["revenue", "profit"]].sum().sort_values("profit", ascending=False)
by_branch

# %%
# 5) أفضل منتج
by_product = df.groupby("product").agg(units=("qty", "sum"), profit=("profit", "sum"))
by_product.sort_values("profit", ascending=False)

# %%
# 6) النمو الشهري
monthly = df.groupby("month")["revenue"].sum()
growth = (monthly.pct_change() * 100).round(1)
pd.DataFrame({"revenue": monthly, "growth_%": growth})

# %%
# 7) رسم يلخص الوضع
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.5))
monthly.plot(ax=a1, marker="o", title="Revenue per month")
a1.set_ylabel("EGP")
by_branch["profit"].plot(kind="bar", ax=a2, color="#2a7ab0", title="Profit per branch")
a2.set_ylabel("EGP")
fig.tight_layout()
fig.savefig("q1_summary.png", dpi=120)
plt.show()
print("حُفظ الرسم في q1_summary.png")

# %% [markdown]
# ## الخلاصة
# - الفرع الأعلى ربحًا والمنتج الأفضل في الجدولين أعلاه.
# - المبيعات تنمو كل شهر (عمود growth_%).

# #file: sales_q1.csv
date,branch,product,qty,price,cost
2026-01-04,Cairo,Pen,120,5,3
2026-01-06,Alex,Notebook,40,25,15
2026-01-09,Giza,Bag,6,180,120
2026-01-12,Cairo,Notebook,55,25,15
2026-01-15,alex ,Pen,90,5,3
2026-01-20,Giza,Pen,70,5,3
2026-01-20,Giza,Pen,70,5,3
2026-01-25,Cairo,Bag,8,180,120
2026-02-02,Alex,Bag,5,180,120
2026-02-05,Cairo,Pen,150,5,3
2026-02-09,Giza,Notebook,48,25,15
2026-02-14,Cairo,Notebook,70,25,15
2026-02-18,Alex,Pen,110,5,3
2026-02-22,Giza,Bag,9,180,120
2026-02-27,Cairo,Bag,10,180,120
2026-03-03,Alex,Notebook,62,25,15
2026-03-07,Cairo,Pen,170,5,3
2026-03-11,Giza,Pen,95,5,3
2026-03-16,Cairo,Notebook,85,25,15
2026-03-21,Alex,Bag,11,180,120
2026-03-26,Giza,Notebook,58,25,15
2026-03-30,Cairo,Bag,14,180,120
```

```text output
الصفوف والأعمدة: (22, 6)
        date branch   product  qty  price  cost
0 2026-01-04  Cairo       Pen  120      5     3
1 2026-01-06   Alex  Notebook   40     25    15
2 2026-01-09   Giza       Bag    6    180   120
3 2026-01-12  Cairo  Notebook   55     25    15
4 2026-01-15  alex        Pen   90      5     3
قيم ناقصة: 0
صفوف مكررة: 1
بعد التنظيف: 21 صفًا
إجمالي المبيعات: 25,815 جنيه
إجمالي الربح: 9,570 جنيه
هامش الربح: 37.1%
        revenue  profit
branch                 
Cairo     13210    4900
Alex       6430    2380
Giza       6175    2290
          units  profit
product                
Notebook    418    4180
Bag          63    3780
Pen         805    1610
         revenue  growth_%
month                     
2026-01     6295       NaN
2026-02     8570      36.1
2026-03    10950      27.8
حُفظ الرسم في q1_summary.png
```

## قراءة النتائج

- لاحظ كيف كشفت خطوة التنظيف صفًا مكررًا (طلب «Giza Pen» يوم 20 يناير مرتين)، وفرعًا مكتوبًا `alex ` بحرف صغير ومسافة زائدة. لو لم ننظفهما لظهر فرع رابع وهمي ولزادت المبيعات خطأً.
- `pct_change()` تحسب نسبة التغير عن الصف السابق، ولذلك أول شهر قيمته `NaN` (لا يوجد شهر قبله).
- `parse_dates=["date"]` حوّلت عمود التاريخ إلى تاريخ حقيقي عند القراءة، فاستطعنا استخراج الشهر بـ `dt.strftime`.

## التحقق النهائي

قبل التسليم: **↻ Restart && Run All**. إذا عملت كل الخلايا بالترتيب دون أخطاء وظهرت نفس النتائج، فالدفتر جاهز.

## التصدير والمشاركة

من زر **Export** في شريط أدوات الدفتر (أو قائمة **Notebook**):

| الأمر | الناتج | لمن؟ |
|---|---|---|
| **Python Script (.py)...** / **Export as Python Script...** | ملف `.py` فيه كل خلايا الكود، وخلايا Markdown كتعليقات، والخلايا مفصولة بـ `# %%` | لتحويل التحليل إلى برنامج يعمل تلقائيًا كل شهر، أو لإضافته إلى مشروع |
| **HTML Page (.html)...** / **Export as HTML...** | صفحة ويب فيها الكود والنتائج والرسوم | للمدير أو أي شخص ليس عنده Python: يفتحها في المتصفح |

وملف `.ipynb` نفسه يُفتح في Jupyter وVS Code وGoogle Colab وGitHub (يعرضه GitHub بالنتائج مباشرة).

> **العكس أيضًا ممكن:** إذا كان عندك سكربت `.py` مقسم بـ `# %%`، فافتحه دفترًا بأمر **File ← New Notebook ← Import Python Script as Notebook...**.

## أفكار للتوسع

- **تحليل لكل فرع وشهر معًا** بـ `pivot_table(index="branch", columns="month", values="profit", aggfunc="sum")`.
- **أفضل يوم في الأسبوع**: `df["date"].dt.day_name()` ثم `groupby`.
- **قراءة عدة ملفات** (ربع لكل ملف) ودمجها بـ `pd.concat([...])`.
- **تصدير جدول النتائج إلى Excel**: `by_branch.to_excel("q1_branches.xlsx")`.

## اختبر نفسك

```quiz
{"question": "لماذا ظهر NaN في أول صف من عمود growth_%؟", "choices": ["خطأ في البيانات", "لأن أول شهر لا يوجد شهر قبله ليُقارن به", "لأن المبيعات صفر", "لأن الملف ناقص"], "answer": 1, "explanation": "pct_change تقارن كل صف بالصف السابق، والصف الأول ليس له سابق."}
```

```quiz
{"question": "تريد إرسال التحليل بنتائجه ورسومه لمدير لا يملك Python. ماذا تصدّر؟", "choices": ["Python Script (.py)", "HTML Page (.html)", "ملف CSV فقط", "لا يمكن"], "answer": 1, "explanation": "صفحة HTML تُفتح في أي متصفح وفيها الكود والنتائج والرسوم."}
```

```quiz
{"question": "ما فائدة Restart && Run All قبل التسليم؟", "choices": ["تسريع الدفتر", "التأكد أن الدفتر يعمل من البداية بالترتيب دون اعتماد على حالة قديمة", "حذف النتائج", "تصدير HTML"], "answer": 1, "explanation": "تبدأ بنواة فارغة وتشغّل كل شيء بالترتيب كما سيفعل غيرك."}
```

## الخلاصة

أنهيت دليل Jupyter وعلم البيانات! صرت تعرف دورة التحليل الكاملة: **اقرأ ← نظّف ← احسب ← جمّع ← ارسم ← استنتج ← صدّر**، وكلها داخل RAD IDE: الدفاتر، ونافذة متغيرات الدفتر، وpandas، وmatplotlib، والتصدير إلى `.py` و`.html`. الخطوة التالية: حلّل بيانات حقيقية تهمك (مصروفات بيتك، أو درجاتك، أو بيانات مفتوحة من الإنترنت).
