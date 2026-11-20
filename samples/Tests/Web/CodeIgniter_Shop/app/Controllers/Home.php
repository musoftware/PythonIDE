<?php

namespace App\Controllers;

use App\Models\ProductModel;

class Home extends BaseController
{
    /**
     * The public catalog (GET /).
     */
    public function index(): string
    {
        $products = model(ProductModel::class);

        return view('home/index', [
            'title'    => lang('Shop.catalog'),
            'products' => $products->where('stock >', 0)->orderBy('name')->findAll(),
            'soldOut'  => $products->where('stock', 0)->countAllResults(),
        ]);
    }
}
