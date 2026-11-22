<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Invoice - a desktop invoice calculator in PHP with a RAD IDE form (GUI Bridge).
// Shows: a DataGridView filled with rad_call(grid, 'AddItem', cell1, cell2, ...), a NumericUpDown, a
// ComboBox (VAT rate), a CheckBox (discount rule), input validation with rad_msgbox, totals recalculated
// on every change, Enter in the price box adds the line (KeyPress), and a SaveFileDialog that writes the
// invoice as a text file. The money math lives in InvoiceCalc.php (plain functions, easy to test).

$GLOBALS['lines'] = [];          // [['item' => ..., 'qty' => ..., 'price' => ...], ...]

function Form1_Load($e)
{
    rad_set('cboTax', 'Text', '14');
    newInvoice();
}

// ------------------------------------------------------------------ lines
function cmdAddLine_Click($e)
{
    $item = trim(rad_get('txtItem', 'Text'));
    $qty = (int)rad_num('numQty', 'Value');
    $price = str_replace(',', '.', trim(rad_get('txtPrice', 'Text')));
    if ($item === '') {
        rad_msgbox('Type the item name.');
        return;
    }
    if (!is_numeric($price) || $price < 0) {
        rad_msgbox('The price must be a positive number.');
        return;
    }
    $GLOBALS['lines'][] = ['item' => $item, 'qty' => $qty, 'price' => (float)$price];
    rad_call('grdLines', 'AddItem', $item, $qty, money((float)$price), money(lineTotal($qty, (float)$price)));
    rad_set('txtItem', 'Text', '');
    rad_set('txtPrice', 'Text', '0');
    rad_set('numQty', 'Value', 1);
    recalc();
}

function txtPrice_KeyPress($e)
{
    if ((explode(' ', $e['args'])[3] ?? '') === 'Return') {      // Enter = Add Line
        cmdAddLine_Click($e);
    }
}

function cmdRemove_Click($e)
{
    if (!$GLOBALS['lines']) {
        return;
    }
    array_pop($GLOBALS['lines']);
    fillGrid();
    recalc();
}

function cboTax_SelectedIndexChanged($e) { recalc(); }
function chkDiscount_CheckedChanged($e) { recalc(); }

// ------------------------------------------------------------------ menu
function mnuNew_Click($e)
{
    newInvoice();
}

function mnuSave_Click($e)
{
    if (!$GLOBALS['lines']) {
        rad_msgbox('The invoice has no lines yet.');
        return;
    }
    rad_set('dlgSave', 'FileName', 'invoice-' . date('Ymd') . '.txt');
    if (rad_call('dlgSave', 'ShowDialog') !== 'OK') {
        return;
    }
    $file = rad_get('dlgSave', 'FileName');
    file_put_contents($file, invoiceText(rad_get('txtCustomer', 'Text'), $GLOBALS['lines'], taxRate(), discountOn()));
    rad_msgbox('Invoice saved to ' . $file);
}

function mnuExit_Click($e)
{
    rad_end();
}

// ------------------------------------------------------------------ helpers
function newInvoice()
{
    $GLOBALS['lines'] = [];
    fillGrid();
    recalc();
}

function fillGrid()
{
    rad_call('grdLines', 'Clear');
    foreach ($GLOBALS['lines'] as $l) {
        rad_call('grdLines', 'AddItem', $l['item'], $l['qty'], money($l['price']), money(lineTotal($l['qty'], $l['price'])));
    }
}

function taxRate(): float { return (float)rad_get('cboTax', 'Text'); }
function discountOn(): bool { return rad_get('chkDiscount', 'Value') === '1'; }

function recalc()
{
    $t = totals($GLOBALS['lines'], taxRate(), discountOn());     // InvoiceCalc.php
    rad_set('lblSubtotal', 'Caption', 'Subtotal: ' . money($t['subtotal'])
        . ($t['discount'] > 0 ? '   Discount: -' . money($t['discount']) : ''));
    rad_set('lblTax', 'Caption', 'VAT ' . taxRate() . '%: ' . money($t['tax']));
    rad_set('lblTotal', 'Caption', 'Total: ' . money($t['total']));
}
