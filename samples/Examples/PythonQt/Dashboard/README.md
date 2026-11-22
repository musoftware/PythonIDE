# System Dashboard (python-qt / PySide6)

A live dashboard: CPU, memory and disk usage, gauges, a history chart and a to-do list.

**What it shows**
- A `Timer` component (QTimer, Enabled at start) refreshing real readings: CPU from `GetSystemTimes`, memory from
  `GlobalMemoryStatusEx` (ctypes), disk from `shutil.disk_usage` (simulated values on other systems).
- `ProgressBar`s with a percent text, a clock and uptime Labels.
- A `TabControl` with three pages (Overview / History / Tasks).
- Custom painting: two `PictureBox`es drawn with `QPainter` through an event filter - arc gauges and a
  three-line history chart.
- A to-do `ListBox` (Add task / Done), Pause / Resume and a "Fast refresh" CheckBox (Timer interval 200 ms).

**Run**: open the folder, **F5**.  **Publish**: Build > Publish (PyInstaller with Qt).

---

# لوحة معلومات النظام (بايثون PySide6)

لوحة معلومات حية: استخدام المعالج والذاكرة والقرص، ومؤشرات دائرية، ورسم بياني للتاريخ، وقائمة مهام.

**ماذا يوضح**: مؤقت Timer يحدّث قراءات حقيقية من النظام، أشرطة تقدم، ساعة ومدة التشغيل، عنصر تبويبات بثلاث صفحات،
رسم مخصص بـ QPainter على عنصر PictureBox، قائمة مهام، وإيقاف مؤقت وتحديث سريع.

**التشغيل**: افتح المجلد واضغط **F5**.  **النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
