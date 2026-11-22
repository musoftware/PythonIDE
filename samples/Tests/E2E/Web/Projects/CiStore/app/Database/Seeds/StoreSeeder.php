<?php

namespace App\Database\Seeds;

use CodeIgniter\Database\Seeder;

class StoreSeeder extends Seeder
{
    public function run()
    {
        if ($this->db->table('products')->countAllResults() === 0) {
            $this->db->table('products')->insertBatch([
                ['name' => 'Laptop', 'price' => 999.5],
                ['name' => 'Phone', 'price' => 450],
            ]);
        }
    }
}
