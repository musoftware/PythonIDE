# Qt Text Editor (python-qt / PySide6)

A text editor with find / replace, made with the RAD IDE designer for PySide6.

**What it shows**
- MenuStrip -> `QMenuBar` + `QAction`s (`mnuFileOpen_Click` ...), shortcuts set in `frmEditor_Load`.
- `OpenFileDialog` / `SaveFileDialog` components (`ShowDialog()` -> `"OK"`), UTF-8 files.
- The Qt clipboard (Cut / Copy / Paste), Undo / Redo, Upper / Lower case of the selection.
- A find bar: Find Next (wraps around) and Replace All as **one undo step**.
- Zoom in / out, **Right to Left** for Arabic text, a status bar with line / column / words.
- `frmEditor_FormClosing(e)`: "Save the changes?" - `e.Cancel = True` keeps the window open.

**Run**: open the folder, **F5** (PySide6 is installed into the project's Python when needed).
**Publish**: Build > Publish (PyInstaller one-folder program with Qt).

---

# محرر نصوص Qt (بايثون PySide6)

محرر نصوص مع البحث والاستبدال، مصمم بمصمم RAD IDE لمكتبة PySide6.

**ماذا يوضح**: القوائم واختصاراتها، مربعات حوار فتح وحفظ الملفات، الحافظة والتراجع والإعادة، تحويل حالة الأحرف،
البحث والاستبدال الكامل كخطوة تراجع واحدة، التكبير والتصغير، **الكتابة من اليمين لليسار** للنص العربي، وسؤال الحفظ عند الإغلاق.

**التشغيل**: افتح المجلد واضغط **F5**.  **النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
