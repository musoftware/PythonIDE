<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# OnlineExam - question bank, papers, timed exams and results

An exam system: the examiner keeps a question bank per subject, builds question papers (duration and pass
mark) and reads the results; a student signs in, takes a timed multiple-choice exam and gets a score card
with PASS / FAIL and the questions answered wrongly.

**Demo sign-in:** student `student1` / `student1` (or `student2`), examiner `admin` / `admin`.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmWelcome` | startup form: role OptionButton array, the exams that have a paper, `Me.Hide` |
| `mdiAdmin` | MDI parent, menus two levels deep with separators (Exam > Students > Add / List), InputBox to add a student |
| `frmQuestions` | DAO dynaset editor: |< < > >| array, `MoveLast` / `MoveFirst` for an exact `RecordCount`, `AddNew` / `Edit` / `Update`, `Bookmark = LastModified`, `FindFirst` / `NoMatch`, a TextBox control array for the four answers, delete protection |
| `frmPaper` | two report ListViews (`ListItems.Add` with keys, `SelectedItem`), LEFT JOIN, `db.RecordsAffected` (UPDATE, else INSERT) |
| `frmExam` | questions in a dynamic array of a `Type` with an array member (`ReDim Preserve`), OptionButton array, countdown Timer that ends the exam, ProgressBar, public `Property Get / Let SecondsLeft`, marking and saving with DAO |
| `frmScore` | score card, Shape badge, the wrong answers through a JOIN |
| `frmResults + deExam + rptResults` | MSFlexGrid of results, pass rate (`Format(x, "0%")`), DataReport through a parameterised command |

## VB6 features covered

DAO in code, MDI with nested menus, control arrays (OptionButton, TextBox, CommandButton), user-defined types with arrays, dynamic arrays, Timer countdown, ProgressBar, ListView, MSFlexGrid, Shape, DataEnvironment + DataReport, form properties and public methods, `Hide` / `Show` between forms.

## Database

Tables: Users (Role admin / student), Subjects, Questions (QText, OptA-D, Correct, Marks), Papers (DurationMin, PassPercent), PaperQuestions (SortNo), Results (Answered, Correct, Score, MaxScore, PercentScore, Passed), Answers (Chosen).


## Run it

* In RAD IDE: **File > Open Project** > `OnlineExam.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\OnlineExam\OnlineExam.vbp`
* In Visual Basic 6: open `OnlineExam.vbp`. The DataEnvironment / DataReport `.Dsr` files are hand-written text (no .dsx/.dca companions), so VB6 may offer to rebuild them.

The Access database `exam.mdb` (Jet 4.0) is built from `exam.sql` with
`python samples\VB6\Business\_tools\make_mdb.py OnlineExam` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py OnlineExam` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

نظام امتحانات: يحتفظ الممتحن ببنك أسئلة لكل مادة، ويبني ورقة الامتحان (المدة ودرجة النجاح) ويطّلع على النتائج؛ ويدخل الطالب ليؤدي امتحان اختيار من متعدد بزمن محدد ثم تظهر له بطاقة النتيجة (ناجح/راسب) والأسئلة التي أخطأ فيها.

الدخول التجريبي: الطالب `student1` / `student1`، والممتحن `admin` / `admin`.

يوضح: DAO في الكود، MDI بقوائم من مستويين، مصفوفات أدوات، نوعًا معرفًا يحتوي مصفوفة، مصفوفات ديناميكية ReDim Preserve، مؤقتًا للعد التنازلي، ListView وMSFlexGrid، وDataEnvironment مع DataReport.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `OnlineExam.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\OnlineExam\OnlineExam.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
