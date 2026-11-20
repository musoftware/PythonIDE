<?php

namespace App\Database\Seeds;

use CodeIgniter\Database\Seeder;

/**
 * php spark db:seed DatabaseSeeder  (Spark panel > db:seed)
 */
class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        $this->call('UserSeeder');
        $this->call('ProductSeeder');
    }
}
