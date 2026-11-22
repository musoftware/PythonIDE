# Inventory - SQLite + modal dialog (python-qt / PySide6)

A stock list on SQLite with a modal Add / Edit dialog that is a second form of the project.

**What it shows**
- `DataGridView` (QTableWidget) filled from SQLite through a code module (`InventoryDb.py`, sqlite3, parameterized
  queries, CHECK / UNIQUE constraints); the database lives in `%APPDATA%\RADExamples\Inventory\inventory.db`.
- Search as you type, a "Low stock only" CheckBox, low-stock rows highlighted, totals in a Label.
- `frmItem` (Project > Add Form) shown **application-modal** with `frmItem.ShowDialog(owner, item)`: a local event
  loop waits until OK (after validation: required fields, number check, unique SKU) or Cancel.
- Edit by double-clicking a row, Delete with a confirmation, File > Export CSV (SaveFileDialog), menu + buttons.

**Run**: open the folder, **F5**.  **Publish**: Build > Publish (PyInstaller with Qt).

---

# المخزون - SQLite ونافذة حوار مشروطة (بايثون PySide6)

قائمة مخزون في قاعدة SQLite مع نافذة إضافة / تعديل مشروطة هي نموذج ثانٍ في المشروع.

**ماذا يوضح**: جدول بيانات يُملأ من SQLite، البحث أثناء الكتابة، تصفية الأصناف قليلة الكمية وتمييزها بلون،
نافذة الصنف المشروطة مع التحقق (الحقول المطلوبة، رقم صحيح للسعر، رمز SKU غير مكرر)، التعديل بالنقر المزدوج،
الحذف مع التأكيد، والتصدير إلى CSV.

**التشغيل**: افتح المجلد واضغط **F5**.  **النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
