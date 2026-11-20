<?php

namespace App\Controllers\Api;

use App\Controllers\BaseController;
use App\Models\ProductModel;
use CodeIgniter\HTTP\ResponseInterface;

/**
 * JSON API: GET /api/products[?q=...] and GET /api/products/{id}
 */
class Products extends BaseController
{
    public function index(): ResponseInterface
    {
        $rows = model(ProductModel::class)
            ->search((string) $this->request->getGet('q'))
            ->select('id, name, sku, price, stock')
            ->findAll();

        return $this->response->setJSON(['count' => count($rows), 'data' => $rows]);
    }

    public function show(int $id): ResponseInterface
    {
        $row = model(ProductModel::class)->find($id);
        if ($row === null) {
            return $this->response->setStatusCode(404)->setJSON(['error' => 'Product not found']);
        }

        return $this->response->setJSON(['data' => $row]);
    }
}
