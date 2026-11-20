<?php

namespace App\Controllers;

use App\Models\ProductModel;
use CodeIgniter\Exceptions\PageNotFoundException;
use CodeIgniter\HTTP\RedirectResponse;

/**
 * Products CRUD (route group 'products', protected by the 'auth' filter).
 * Validation rules live in ProductModel::$validationRules.
 */
class Products extends BaseController
{
    protected ProductModel $products;

    public function __construct()
    {
        $this->products = model(ProductModel::class);
    }

    public function index(): string
    {
        $term = (string) $this->request->getGet('q');
        $list = $this->products->search($term)->paginate(config('Shop')->perPage);

        return view('products/index', [
            'title'    => lang('Shop.products.title'),
            'products' => $list,
            'pager'    => $this->products->pager,
            'q'        => $term,
        ]);
    }

    public function new(): string
    {
        return view('products/form', ['title' => lang('Shop.products.new'), 'product' => null]);
    }

    public function create(): RedirectResponse
    {
        $data = $this->request->getPost(['name', 'sku', 'price', 'stock', 'description']);
        if (! $this->products->insert($data)) {
            return redirect()->back()->withInput()->with('errors', $this->products->errors());
        }

        return redirect()->route('products.index')->with('message', lang('Shop.products.saved', [$data['name']]));
    }

    public function edit(int $id): string
    {
        return view('products/form', ['title' => lang('Shop.products.edit'), 'product' => $this->find($id)]);
    }

    public function update(int $id): RedirectResponse
    {
        $this->find($id);
        $data = $this->request->getPost(['name', 'sku', 'price', 'stock', 'description']);
        if (! $this->products->update($id, $data)) {
            return redirect()->back()->withInput()->with('errors', $this->products->errors());
        }

        return redirect()->route('products.index')->with('message', lang('Shop.products.saved', [$data['name']]));
    }

    public function delete(int $id): RedirectResponse
    {
        $this->find($id);
        $this->products->delete($id);

        return redirect()->route('products.index')->with('message', lang('Shop.products.deleted'));
    }

    private function find(int $id): array
    {
        $product = $this->products->find($id);
        if ($product === null) {
            throw PageNotFoundException::forPageNotFound();
        }

        return $product;
    }
}
