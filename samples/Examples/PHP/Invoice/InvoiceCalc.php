<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module InvoiceCalc - the money math of the Invoice example. Pure functions (no form access), so they can
// also be called from other languages of a solution: radcall("InvoiceCalc.lineTotal", 3, 9.5).

function lineTotal($qty, $price): float
{
    return round($qty * $price, 2);
}

/** Subtotal, discount (10% when "discount" is on and the subtotal is over 1000), VAT and total. */
function totals(array $lines, float $taxRate, bool $discount): array
{
    $subtotal = 0.0;
    foreach ($lines as $l) {
        $subtotal += lineTotal($l['qty'], $l['price']);
    }
    $disc = ($discount && $subtotal > 1000) ? round($subtotal * 0.10, 2) : 0.0;
    $tax = round(($subtotal - $disc) * $taxRate / 100, 2);
    return ['subtotal' => $subtotal, 'discount' => $disc, 'tax' => $tax, 'total' => round($subtotal - $disc + $tax, 2)];
}

function money($v): string
{
    return number_format((float)$v, 2, '.', ',');
}

/** The invoice as plain text (what File > Save as Text writes). */
function invoiceText(string $customer, array $lines, float $taxRate, bool $discount): string
{
    $out = "INVOICE\r\nCustomer: $customer\r\nDate: " . date('Y-m-d') . "\r\n\r\n";
    $out .= sprintf("%-30s %5s %12s %12s\r\n", 'Item', 'Qty', 'Price', 'Total');
    foreach ($lines as $l) {
        $out .= sprintf("%-30s %5d %12s %12s\r\n", $l['item'], $l['qty'], money($l['price']),
                        money(lineTotal($l['qty'], $l['price'])));
    }
    $t = totals($lines, $taxRate, $discount);
    $out .= "\r\nSubtotal: " . money($t['subtotal']) . "\r\n";
    if ($t['discount'] > 0) {
        $out .= 'Discount: -' . money($t['discount']) . "\r\n";
    }
    $out .= "VAT $taxRate%: " . money($t['tax']) . "\r\nTOTAL: " . money($t['total']) . "\r\n";
    return $out;
}
