<?php

namespace App\Database\Seeds;

use App\Models\UserModel;
use CodeIgniter\Database\Seeder;

class UserSeeder extends Seeder
{
    public function run(): void
    {
        $users = model(UserModel::class);
        if ($users->where('email', 'admin@example.com')->first() !== null) {
            return;
        }
        $users->insert([
            'name'          => 'Admin',
            'email'         => 'admin@example.com',
            'password_hash' => password_hash('secret123', PASSWORD_DEFAULT),
        ]);
    }
}
