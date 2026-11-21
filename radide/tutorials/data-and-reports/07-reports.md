# الدرس 7: مصمم التقارير

**في هذا الدرس ستتعلم:**

- ما هو **التقرير المقسّم إلى أشرطة** (Banded report): رأس التقرير، ورأس الصفحة، والتفاصيل، والمجموعات، والتذييل.
- إنشاء تقرير بالمعالج من **Project > Add Report...**، ثم تعديله في **مصمم التقارير**.
- مصدر بيانات التقرير، والمعاملات، والمجموعات، والتعبيرات مثل `Sum("Amount")`.
- عرض التقرير في برنامجك بأداة `ReportViewer`، وتصديره PDF و Excel وطباعته.

## الفاتورة المطبوعة

انظر إلى أي فاتورة أو كشف درجات مطبوع:

- في **أعلى الورقة الأولى**: اسم الشركة وشعارها. هذا **رأس التقرير** (Report Header).
- في **أعلى كل صفحة**: عناوين الأعمدة. هذا **رأس الصفحة** (Page Header).
- **سطر لكل صنف**: هذه **التفاصيل** (Detail)، تتكرر لكل صف من البيانات.
- **مجموعات**: "قسم الأدوات المكتبية" ثم أصنافه ثم مجموعها. هذا **رأس المجموعة وتذييلها** (Group Header / Footer).
- في **أسفل كل صفحة**: "صفحة 1 من 3". هذا **تذييل الصفحة** (Page Footer).
- في **النهاية**: الإجمالي الكلي. هذا **تذييل التقرير** (Report Footer).

كل جزء منها **شريط** (Band)، والمصمم يرسمها شرائط أفقية تضع فيها العناصر.

## إنشاء تقرير بالمعالج

1. افتح مشروعك، واختر **Project > Add Report...** (مشروع > إضافة تقرير...).
2. اختر النوع:
   - **Report Wizard (table with groups and totals)**: جدول جاهز بمجموعات ومجاميع.
   - **Blank report**: تقرير فارغ تصممه بنفسك.
3. **Data Source...** (مصدر بيانات...): من أين تأتي الصفوف؟
   - **استعلام SQL** على اتصال (SQLite مدمج؛ MySQL و PostgreSQL بمكتباتهما).
   - **ملف CSV أو JSON**.
   - **صفوف من الكود**: البرنامج يعطيها بـ `ReportViewer1.SetData(rows)`.
4. **Fields (in column order):** علّم الحقول ورتبها.
5. اختر **حقل التجميع** (أو `(none)`)، وخيارات:
   - **Totals for number fields** (المجاميع للحقول الرقمية).
   - **Add a bar chart in the report footer** (إضافة مخطط أعمدة في تذييل التقرير).
   - **Right to left (Arabic)** (من اليمين لليسار): تقرير عربي.
   - **Landscape** (أفقي): ورقة بالعرض.
6. **OK**: يُنشأ ملف `Report1.rpt.json` ويفتح في المصمم، وتُنسخ مكتبة التشغيل `radreport.py` إلى مشروعك.

التقارير تظهر في مستكشف الحلول تحت عقدة **Reports**؛ انقر التقرير مرتين لفتحه.

## مصمم التقارير

| الجزء | ما فيه |
|---|---|
| **شريط الأدوات** | **Save** و **Undo** و **Redo**، و **Data Source...** و **Parameters...** و **Groups...**، و **Zoom** و **Snap to grid**، و **Preview** |
| **Report Items** (يسار أعلى) | العناصر: Text و Field و Expression و Line و Box و Image و Barcode و QR Code و Chart و Page N of M و Date |
| **Field List** (يسار أسفل) | حقول مصدر البيانات: اسحب حقلًا إلى شريط Detail |
| **سطح التصميم** (الوسط) | الأشرطة وعناصرها؛ اسحب حافة الشريط لتغيير ارتفاعه |
| **الخصائص** (يمين) | خصائص العنصر أو الشريط أو التقرير المحدد |
| لسان **Preview** (أسفل) | التقرير الحقيقي بالبيانات، صفحة صفحة |

الزر الأيمن على السطح: **Delete** و **Duplicate** (`Ctrl+D`) و **Bring to Front** و **Send to Back** و **Band Properties** و **Insert Group...** و **Report Properties**.

## التعبيرات

عنصر **Expression** (أو نص فيه `{...}`) يحسب قيمة. التعبيرات صغيرة وسهلة:

| التعبير | المعنى |
|---|---|
| `Qty * Price` | قيمة السطر |
| `Fields["Unit Price"]` | حقل في اسمه مسافة |
| `Sum("Amount")`، `Count()`، `Avg("Grade")`، `Min` و `Max` | مجاميع المجموعة أو التقرير (حسب الشريط الذي توضع فيه) |
| `RunningSum("Amount")`، `RowNumber` | مجموع متراكم، ورقم السطر |
| `PageNumber`، `TotalPages` | رقم الصفحة وعددها |
| `Now()`، `Today()` | الوقت والتاريخ |
| `IIf(Grade >= 50, "ناجح", "راسب")` | شرط |
| `Format(Amount, "N2")` | تنسيق رقم بخانتين عشريتين |
| `Parameters.Year` | معامل يعطيه البرنامج |

مثال نص: `الإجمالي: {Format(Sum("Amount"), "N2")} جنيه`.

## المعاملات والمجموعات

- **Parameters...** (المعاملات...): قيم يعطيها البرنامج قبل التشغيل، مثل رقم العميل. في SQL تُكتب `:CustomerId`، وفي التعبيرات `Parameters.CustomerId`.
- **Groups...** (المجموعات...): حقول التجميع من الخارج إلى الداخل (مثل القسم ثم المورد). لكل مجموعة رأس وتذييل، والصفوف تُرتب بها تلقائيًا.

## التقرير في برنامجك

### على نموذج: أداة `ReportViewer`

ضع `ReportViewer` من صندوق الأدوات، واختر التقرير في خصائصه. في المصمم يرسم معاينة التقرير مباشرة. وعند التشغيل يعرض التقرير بأزرار الصفحات والطباعة.

### من الكود (Python)

```python
import radreport

r = radreport.Report("Invoice.rpt.json")
r.Parameters["CustomerId"] = 3
r.ExportPdf("invoice.pdf")          # وأيضًا ExportHtml و ExportCsv و ExportExcel
r.Print()                           # نافذة الطباعة

radreport.show("Invoice.rpt.json")  # نافذة معاينة
```

التصدير إلى Excel يحتاج `openpyxl`، والباركود `python-barcode`، و QR `qrcode`. والنص العربي يُشكَّل ويُرتب صحيحًا.

> 💡 أداة `ReportViewer` تعمل في نماذج **Python (Tkinter)** و **Python (PySide6 / Qt)**. ومن أي مشروع تستطيع تصميم التقرير ومعاينته في المصمم.

## الأشرطة بكود بسيط

التقرير المقسّم في النهاية: رأس، ثم سطر لكل صف، ومع تغيّر قيمة حقل التجميع يُطبع تذييل المجموعة ورأس المجموعة التالية، وفي النهاية الإجمالي. هذا برنامج BASIC يطبع "تقرير مبيعات" بالمنطق نفسه:

```vb run
Sub Main()
    Dim cn, rs
    Dim group As String, groupSum As Long, total As Long
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=sales.db"
    cn.Execute "DROP TABLE IF EXISTS Sales"
    cn.Execute "CREATE TABLE Sales (Id INTEGER PRIMARY KEY, Dept TEXT, Item TEXT, Amount INTEGER)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Pens', 120)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Novel', 300)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Paper', 80)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Atlas', 450)"

    Debug.Print "=== تقرير المبيعات ==="
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Dept, Item, Amount FROM Sales ORDER BY Dept, Item", cn
    Do While Not rs.EOF
        If rs("Dept") <> group Then
            If group <> "" Then Debug.Print "  مجموع " & group & ": " & groupSum
            group = rs("Dept")
            groupSum = 0
            Debug.Print "[" & group & "]"
        End If
        Debug.Print "  " & rs("Item") & " " & rs("Amount")
        groupSum = groupSum + rs("Amount")
        total = total + rs("Amount")
        rs.MoveNext
    Loop
    Debug.Print "  مجموع " & group & ": " & groupSum
    Debug.Print "الإجمالي: " & total
    rs.Close
    cn.Close
End Sub
```

```text output
=== تقرير المبيعات ===
[Books]
  Atlas 450
  Novel 300
  مجموع Books: 750
[Office]
  Paper 80
  Pens 120
  مجموع Office: 200
الإجمالي: 950
```

في مصمم التقارير تحصل على هذا كله (وبشكل مطبوع جميل) من المعالج: حقل التجميع `Dept`، و **Totals for number fields**.

## أخطاء شائعة

- **حقل المجموع في شريط Detail:** `Sum("Amount")` في Detail يعطي قيمة السطر فقط تقريبًا. ضعه في تذييل المجموعة أو التقرير.
- **ترتيب البيانات لا يتبع المجموعات:** المجموعات ترتب الصفوف بنفسها؛ لا تحتاج `ORDER BY` لحقل التجميع، لكن أضفه للترتيب داخل المجموعة.
- **تقرير فارغ في Preview:** مصدر البيانات لا يعيد صفوفًا، أو يحتاج قيمة معامل. جرّب **Data Source...** و **Test**.
- **التصدير إلى Excel يفشل:** ثبّت `openpyxl` من **Manage Packages...**.

## تمرين

### تمرين 1: عدد الأصناف في كل قسم

عدّل التقرير ليطبع لكل قسم سطرًا واحدًا فقط بعدد أصنافه ومجموعه، باستخدام `GROUP BY` بدل الحلقة اليدوية: `Books: 2 أصناف، 750`.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=sales.db"
    cn.Execute "DROP TABLE IF EXISTS Sales"
    cn.Execute "CREATE TABLE Sales (Id INTEGER PRIMARY KEY, Dept TEXT, Item TEXT, Amount INTEGER)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Pens', 120)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Novel', 300)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Paper', 80)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Atlas', 450)"
    Set rs = CreateObject("ADODB.Recordset")
    ' أكمل
    cn.Close
End Sub
```

```vb solution
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=sales.db"
    cn.Execute "DROP TABLE IF EXISTS Sales"
    cn.Execute "CREATE TABLE Sales (Id INTEGER PRIMARY KEY, Dept TEXT, Item TEXT, Amount INTEGER)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Pens', 120)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Novel', 300)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Office', 'Paper', 80)"
    cn.Execute "INSERT INTO Sales (Dept, Item, Amount) VALUES ('Books', 'Atlas', 450)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Dept, COUNT(*) AS N, SUM(Amount) AS S FROM Sales GROUP BY Dept ORDER BY Dept", cn
    Do While Not rs.EOF
        Debug.Print rs("Dept") & ": " & rs("N") & " أصناف، " & rs("S")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
Books: 2 أصناف، 750
Office: 2 أصناف، 200
```

### مهمة عملية: كشف درجات عربي

1. في مشروع **Python (Tkinter)** شغّل مثال الدرس 3 (بلغة BASIC في مشروع آخر) أو أنشئ `school.db` من نافذة Databases بجدول `Students`.
2. **Project > Add Report...** > **Report Wizard** > **Data Source...**: استعلام `SELECT Name, City, Grade FROM Students`.
3. التجميع بـ `City`، وفعّل **Totals for number fields** و **Right to left (Arabic)**.
4. في المصمم أضف عنصر **Expression** في Detail: `IIf(Grade >= 50, "ناجح", "راسب")`.
5. افتح لسان **Preview**، ثم ضع `ReportViewer` على `Form1` واختر التقرير، وشغّل.

## اختبر نفسك

```quiz
{"question": "أي شريط يتكرر مرة لكل صف من البيانات؟", "choices": ["Report Header", "Detail", "Page Footer", "Report Footer"], "answer": 1, "explanation": "Detail يُطبع لكل صف، والرؤوس والتذييلات حول المجموعات والصفحات والتقرير."}
```

```quiz
{"question": "تريد الإجمالي الكلي في نهاية التقرير. أين تضع `Sum(\"Amount\")`؟", "choices": ["في Detail", "في Report Footer", "في Page Header", "في Field List"], "answer": 1, "explanation": "المجموع في تذييل التقرير يجمع كل الصفوف، وفي تذييل المجموعة يجمع صفوف المجموعة."}
```

```quiz
{"question": "كيف يصدّر برنامج Python التقرير إلى PDF؟", "choices": ["`radreport.Report(\"R.rpt.json\").ExportPdf(\"r.pdf\")`", "بطباعة الشاشة", "بنسخ الملف", "لا يمكن"], "answer": 0, "explanation": "مكتبة radreport المنسوخة في المشروع فيها ExportPdf و ExportHtml و ExportCsv و ExportExcel و Print."}
```

## الخلاصة

- التقرير أشرطة: Report / Page / Group Header، و Detail لكل صف، والتذييلات.
- **Project > Add Report...**: المعالج (مصدر بيانات، حقول، تجميع، مجاميع، مخطط، عربي، أفقي) أو تقرير فارغ.
- المصمم: Report Items و Field List والخصائص و **Preview**، و **Parameters...** و **Groups...**.
- التعبيرات: `Sum` و `Count` و `IIf` و `Format` و `PageNumber`، والعرض بـ `ReportViewer` أو `radreport` من الكود.
