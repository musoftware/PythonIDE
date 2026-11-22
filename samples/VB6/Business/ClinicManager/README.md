<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# ClinicManager - patients and visits with DAO and the Data control

A small clinic: patient records (add, edit, find, remove with all their visits), the visits of a patient
(weight, blood pressure, pulse, temperature, diagnosis, medicine) and a statistics page with a bar chart.
The medical data is fictional demo data, not advice.

**Demo sign-in:** staff PIN `1234` (asked with an InputBox).

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `modClinic` | `Sub Main` asks for the PIN in a loop (three tries), `DBEngine.Workspaces(0).OpenDatabase`, age calculation with `DateDiff` / `DateSerial` |
| `frmMain` | SSTab: Patients = the intrinsic **Data control** with bound TextBoxes / ComboBoxes (`DataSource` + `DataField`), `Data1_Reposition` ("Patient n of m", age), AddNew / Edit / Update / `Bookmark = LastModified`, `FindFirst` + `NoMatch`, remove patient with a DAO Delete loop; Visits = MSFlexGrid; Statistics = a bar chart made of a Shape control array on a Line axis |
| `frmVisit` | modal dialog prepared by a public Sub (`StartFor`), MaskEdBox for the blood pressure, `Like` patterns, range checks, `Change` event warning, DAO `AddNew` / `rs!Field =` / `Update` |

## VB6 features covered

DAO (Database, Recordset types `dbOpenDynaset` / `dbOpenSnapshot`, `FindFirst`, `NoMatch`, `EditMode`, `LastModified`, `AbsolutePosition`, `RecordCount`, `Delete` + `MoveNext`), the Data control (`DatabaseName`, `RecordSource`, `Refresh`, `Recordset`, Reposition event), bound controls, SSTab, MSFlexGrid, MaskEdBox, DTPicker, Shape / Line charts, InputBox login, `GROUP BY`.

## Database

Tables: Patients (PatientNo, FullName, Gender, BirthDate, Phone, Address, BloodGroup), Visits (VisitDate, WeightKg, BloodPressure, Pulse, TempC, Diagnosis, Medicine), Medicines, Staff (StaffPin).


## Run it

* In RAD IDE: **File > Open Project** > `ClinicManager.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ClinicManager\ClinicManager.vbp`
* In Visual Basic 6: open `ClinicManager.vbp`. It uses only standard VB6 references and controls.

The Access database `clinic.mdb` (Jet 4.0) is built from `clinic.sql` with
`python samples\VB6\Business\_tools\make_mdb.py ClinicManager` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py ClinicManager` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

عيادة صغيرة: ملفات المرضى (إضافة وتعديل وبحث وحذف مع زياراتهم)، زيارات المريض (الوزن والضغط والنبض والحرارة والتشخيص والدواء) وصفحة إحصاءات برسم بياني بالأعمدة. البيانات الطبية وهمية للتجربة وليست نصيحة طبية.

رمز الموظف التجريبي: `1234` (يُطلب في InputBox).

يوضح: DAO وأداة Data المدمجة مع أدوات مربوطة (DataSource وDataField) وحدث Reposition، البحث FindFirst وNoMatch، SSTab وMSFlexGrid وMaskEdBox، ورسمًا بيانيًا بأدوات Shape وLine.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `ClinicManager.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ClinicManager\ClinicManager.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
