<?php

namespace App\Controllers;

use App\Models\ProductModel;

class Products extends BaseController
{
    private ProductModel $products;

    public function __construct()
    {
        $this->products = model(ProductModel::class);
    }

    private function guard()
    {
        return session('user') ? null : redirect()->to('/login?next=' . urlencode(current_url(true)->getPath()));
    }

    public function index()
    {
        $q = (string) $this->request->getGet('q');
        $rows = $this->products->like('name', $q)->orderBy('id')->findAll();
        return view('store/products', ['products' => $rows, 'q' => $q]);
    }

    public function add()
    {
        if ($r = $this->guard()) {
            return $r;
        }
        if ($this->request->is('post')) {
            $data = $this->request->getPost(['name', 'price']);
            if ($this->products->insert($data) === false) {
                return $this->response->setStatusCode(422)->setBody(view('store/form', [
                    'title' => 'Add product', 'errors' => $this->products->errors(), 'p' => $data, 'id' => null]));
            }
            return redirect()->to('/products');
        }
        return view('store/form', ['title' => 'Add product', 'errors' => [], 'p' => ['name' => '', 'price' => ''], 'id' => null]);
    }

    public function edit(int $id)
    {
        if ($r = $this->guard()) {
            return $r;
        }
        $row = $this->products->find($id);
        if (! $row) {
            throw \CodeIgniter\Exceptions\PageNotFoundException::forPageNotFound();
        }
        if ($this->request->is('post')) {
            $data = $this->request->getPost(['name', 'price']);
            if ($this->products->update($id, $data) === false) {
                return $this->response->setStatusCode(422)->setBody(view('store/form', [
                    'title' => 'Edit product', 'errors' => $this->products->errors(), 'p' => $data, 'id' => $id]));
            }
            return redirect()->to('/products');
        }
        return view('store/form', ['title' => 'Edit product', 'errors' => [], 'p' => $row, 'id' => $id]);
    }

    public function delete(int $id)
    {
        if ($r = $this->guard()) {
            return $r;
        }
        $this->products->delete($id);
        return redirect()->to('/products');
    }

    public function api()
    {
        $rows = $this->products->select('id, name, price')->orderBy('id')->findAll();
        foreach ($rows as &$r) {
            $r['id'] = (int) $r['id'];
            $r['price'] = (float) $r['price'];
        }
        return $this->response->setJSON($rows);
    }

    public function home()
    {
        return $this->response->setBody(file_get_contents(FCPATH . 'home.html'));
    }
}
