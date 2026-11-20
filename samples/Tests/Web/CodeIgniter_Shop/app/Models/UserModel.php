<?php

namespace App\Models;

use CodeIgniter\Model;

class UserModel extends Model
{
    protected $table         = 'users';
    protected $primaryKey    = 'id';
    protected $returnType    = 'array';
    protected $useTimestamps = true;
    protected $allowedFields = ['name', 'email', 'password_hash'];

    /**
     * The user with this e-mail and password, or null.
     */
    public function check(string $email, string $password): ?array
    {
        $user = $this->where('email', $email)->first();

        return $user !== null && password_verify($password, $user['password_hash']) ? $user : null;
    }
}
