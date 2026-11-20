<?php

namespace App\Database\Seeds;

use App\Models\ProductModel;
use CodeIgniter\Database\Seeder;

class ProductSeeder extends Seeder
{
    public function run(): void
    {
        $products = model(ProductModel::class);
        $rows     = [
            ['name' => 'Mechanical keyboard', 'sku' => 'KB-100', 'price' => 79.90, 'stock' => 12, 'description' => 'Hot-swappable switches, RGB.'],
            ['name' => 'Wireless mouse', 'sku' => 'MS-200', 'price' => 24.50, 'stock' => 3, 'description' => 'Silent buttons, USB-C.'],
            ['name' => '27" monitor', 'sku' => 'MN-270', 'price' => 229.00, 'stock' => 0, 'description' => '1440p, 144 Hz.'],
            ['name' => 'USB-C hub', 'sku' => 'HB-007', 'price' => 39.99, 'stock' => 25, 'description' => '7 ports, 100 W power delivery.'],
        ];

        foreach ($rows as $row) {
            if ($products->where('sku', $row['sku'])->first() === null) {
                $products->insert($row);
            }
        }
    }
}
