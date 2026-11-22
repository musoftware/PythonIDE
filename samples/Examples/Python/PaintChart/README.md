# Paint & Live Chart (python-tk)

Draw with the mouse on one tab, watch a live chart on the other.

**What it shows**
- A `TabControl` with two pages, controls placed on each page in the designer.
- **Paint**: a `PictureBox` hosting a Tk canvas; the `picCanvas_MouseDown / MouseMove / MouseUp` handlers
  receive `EventArgs` (`e.X`, `e.Y`).  Pen, Line, Box and Oval tools (RadioButtons) with a rubber band, colors
  from a ComboBox or the `ColorDialog`, pen size from a `TrackBar`, Undo Last Stroke, Clear, Save as PostScript
  (`SaveFileDialog`).
- **Live Chart**: a `Timer` (Interval from a `NumericUpDown`) adds a simulated sensor reading; the chart with a
  grid is redrawn, min / max / average shown in a Label and the last value in a `ProgressBar`.  Start / Stop.

**Run**: open the folder, **F5**.  **Publish**: Build > Publish (PyInstaller).

---

# الرسم والرسم البياني المباشر (بايثون Tkinter)

ارسم بالفأرة في تبويب، وشاهد رسماً بيانياً يتحدث تلقائياً في التبويب الآخر.

**ماذا يوضح**
- عنصر تبويبات TabControl بصفحتين، وعناصر موضوعة على كل صفحة في المصمم.
- **الرسم**: أحداث الفأرة (ضغط / تحريك / رفع) مع إحداثيات `e.X` و `e.Y`، وأدوات القلم والخط والمستطيل والشكل
  البيضاوي، واختيار اللون من قائمة أو من مربع حوار الألوان، وحجم القلم من شريط تمرير، والتراجع والحفظ.
- **الرسم البياني**: مؤقت Timer يضيف قراءة جديدة كل فترة، ويعرض الحد الأدنى والأقصى والمتوسط وشريط تقدم.

**التشغيل**: افتح المجلد واضغط **F5**.  **النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
