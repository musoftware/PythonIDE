<?php

namespace App\Models;

use CodeIgniter\Model;

class ProductModel extends Model
{
    protected $table         = 'products';
    protected $primaryKey    = 'id';
    protected $returnType    = 'array';
    protected $useTimestamps = true;
    protected $allowedFields = ['name', 'sku', 'price', 'stock', 'description'];

    // validation (used by insert() / update() / save(); {id} = the row being updated)
    protected $validationRules = [
        'id'    => 'permit_empty|is_natural_no_zero',    // CI 4.7: a {placeholder} field needs a rule
        'name'  => 'required|min_length[3]|max_length[120]',
        'sku'   => 'required|alpha_dash|max_length[40]|is_unique[products.sku,id,{id}]',
        'price' => 'required|decimal|greater_than_equal_to[0]',
        'stock' => 'required|is_natural',
    ];
    protected $validationMessages = [
        'sku' => ['is_unique' => 'This SKU is already used by another product.'],
    ];

    /**
     * Products whose name or SKU contains $term, newest first.
     */
    public function search(?string $term): static
    {
        if ($term !== null && $term !== '') {
            $this->groupStart()->like('name', $term)->orLike('sku', $term)->groupEnd();
        }

        return $this->orderBy('created_at', 'DESC');
    }
}
