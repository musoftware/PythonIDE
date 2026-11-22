# Invoice (PHP desktop form)

A desktop invoice calculator written in PHP - the IDE draws the form (GUI Bridge), PHP runs the handlers.

**What it shows**
- A `DataGridView` of invoice lines: `rad_call('grdLines', 'AddItem', $item, $qty, $price, $total)` (one
  argument per cell), `Clear`, `Rows`, `TextMatrix`.
- `NumericUpDown` quantity, a `ComboBox` VAT rate, a `CheckBox` discount rule (10% over 1000), totals recalculated
  on every change; Enter in the price box adds the line (`KeyPress`, `$e['args']`).
- Validation with `rad_msgbox`; File > Save as Text uses a `SaveFileDialog` and `file_put_contents`.
- The money math as plain functions in the module `InvoiceCalc.php` (`totals`, `lineTotal`, `invoiceText`).

**Run**: open the folder, **F5** (PHP 8 - the IDE finds it or downloads a portable PHP).
**Publish**: Build > Publish (GUI Bridge program, Python inside; PHP needed on the PC).

---

# الفاتورة (نموذج سطح مكتب بلغة PHP)

حاسبة فواتير لسطح المكتب مكتوبة بلغة PHP؛ بيئة التطوير ترسم النموذج وPHP تنفذ معالجات الأحداث.

**ماذا يوضح**
- جدول `DataGridView` لبنود الفاتورة (كل خلية في معامل مستقل).
- كمية بـ `NumericUpDown`، ونسبة ضريبة من قائمة منسدلة، وخصم 10% فوق 1000، وإعادة حساب الإجماليات مع كل تغيير، وزر Enter يضيف البند.
- التحقق من المدخلات برسائل، وحفظ الفاتورة كملف نصي بمربع حوار الحفظ.
- العمليات الحسابية في وحدة `InvoiceCalc.php`.

**التشغيل**: افتح المجلد واضغط **F5** (يحتاج PHP 8، وبيئة التطوير تجده أو تنزله).
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج PHP على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
