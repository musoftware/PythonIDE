<?php
require dirname(__DIR__, 2) . '/app/bootstrap.php';

$user = require_login();
$values = ['name' => '', 'sku' => '', 'price' => '', 'quantity' => '0', 'description' => ''];
$errors = [];
if (is_post()) {
    verify_csrf();
    $values = array_map(fn($k) => post_str($k), array_combine(array_keys($values), array_keys($values)));
    [$data, $errors] = product_validate($values);
    if (!$errors) {
        $id = product_create($data, (int) $user['id']);
        flash('success', 'Product "' . $data['name'] . '" was added.');
        redirect('products/edit.php?id=' . $id);
    }
    http_response_code(422);
}
page_header('Add product', 'products');
?>
<p><a href="<?= e(url('products/')) ?>">&laquo; Products</a></p>
<section class="card">
    <h1>Add product</h1>
    <?php $action = url('products/create.php'); $submitLabel = 'Add product';
    require APP_ROOT . '/app/views/product_form.php'; ?>
</section>
<?php page_footer();
?><p class="design-added">added</p>