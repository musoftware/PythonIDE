<?php
require dirname(__DIR__, 2) . '/app/bootstrap.php';

require_login();
if (!is_post()) {
    render_error(405, 'Method not allowed', 'Products are deleted with the Delete button.');
}
verify_csrf();
$id = filter_var($_POST['id'] ?? '', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
$product = $id ? product_find($id) : null;
if ($product && product_delete($id)) {
    flash('success', 'Product "' . $product['name'] . '" was deleted.');
} else {
    flash('error', 'The product was not found (already deleted?).');
}
redirect('products/');
