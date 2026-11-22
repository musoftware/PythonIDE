<?php
require __DIR__ . '/lib.php';
require_login();
$errors = []; $name = ''; $price = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    [$errors, $name, $price] = validate_product($_POST);
    if (!$errors) {
        db()->prepare('INSERT INTO products (name, price) VALUES (?, ?)')->execute([$name, $price]);
        header('Location: /products.php');
        exit;
    }
    http_response_code(422);
}
layout_top('Add product');
echo '<h1>Add product</h1>';
require __DIR__ . '/product_form.php';
layout_bottom();
