<?php

namespace App\Models;

use CodeIgniter\Model;

class ProductModel extends Model
{
    protected $table = 'products';
    protected $allowedFields = ['name', 'price'];
    protected $useTimestamps = true;
    protected $returnType = 'array';
    protected $validationRules = [
        'name'  => 'required|max_length[100]',
        'price' => 'required|numeric|greater_than_equal_to[0]',
    ];
}
