<?php

namespace Config;

use CodeIgniter\Config\BaseConfig;

/**
 * Settings of the shop: config('Shop')->currency, config('Shop')->perPage ...
 * (override them in .env: shop.currency = EUR)
 */
class Shop extends BaseConfig
{
    /**
     * Name shown in the page header.
     */
    public string $siteName = 'CodeIgniter Shop';

    /**
     * Currency code used by money() (app/Helpers/shop_helper.php).
     */
    public string $currency = 'USD';

    /**
     * Products per page in the list.
     */
    public int $perPage = 10;

    /**
     * Products with less stock than this are marked "low stock".
     */
    public int $lowStock = 5;
}
