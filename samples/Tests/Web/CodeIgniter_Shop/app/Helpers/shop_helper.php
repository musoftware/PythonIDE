<?php

/**
 * Shop helper - loaded for every controller by BaseController::$helpers.
 */

if (! function_exists('money')) {
    /**
     * Format an amount with the shop currency (Config\Shop::$currency).
     */
    function money(float|int|string|null $amount): string
    {
        return number_format((float) $amount, 2) . ' ' . esc(config('Shop')->currency);
    }
}

if (! function_exists('stock_badge')) {
    /**
     * A small HTML badge: "in stock", "low stock" or "sold out".
     */
    function stock_badge(int $stock): string
    {
        if ($stock <= 0) {
            return '<span class="badge out">' . lang('Shop.stock.out') . '</span>';
        }
        if ($stock < config('Shop')->lowStock) {
            return '<span class="badge low">' . lang('Shop.stock.low', [$stock]) . '</span>';
        }

        return '<span class="badge ok">' . lang('Shop.stock.ok') . '</span>';
    }
}
