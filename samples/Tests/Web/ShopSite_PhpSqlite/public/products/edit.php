<?php
require dirname(__DIR__, 2) . '/app/bootstrap.php';

require_login();
$id = filter_var($_GET['id'] ?? '', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
$product = $id ? product_find($id) : null;
if (!$product) {
    render_error(404, 'Product not found', 'The product does not exist (it may have been deleted).');
}
$values = product_form_values($product);
$errors = [];
if (is_post()) {
    verify_csrf();
    $values = array_map(fn($k) => post_str($k), array_combine(array_keys($values), array_keys($values)));
    [$data, $errors] = product_validate($values, $id);
    if (!$errors) {
        product_update($id, $data);
        flash('success', 'Product "' . $data['name'] . '" was saved.');
        redirect('products/');
    }
    http_response_code(422);
}
page_header('Edit ' . $product['name'], 'products');
?>
<p><a href="<?= e(url('products/')) ?>">&laquo; Products</a></p>
<section class="card">
    <div class="card-head">
        <h1>Edit product</h1>
        <form class="inline" method="post" action="<?= e(url('products/delete.php')) ?>"
              data-confirm="Delete <?= e($product['name']) ?>?">
            <?= csrf_field() ?>
            <input type="hidden" name="id" value="<?= (int) $product['id'] ?>">
            <button class="btn btn-danger" type="submit">Delete</button>
        </form>
    </div>
    <p class="muted">Created <?= e(format_time($product['created_at'])) ?> &middot; updated <?= e(format_time($product['updated_at'])) ?> (UTC)</p>
    <?php $action = url('products/edit.php?id=' . $product['id']); $submitLabel = 'Save changes';
    require APP_ROOT . '/app/views/product_form.php'; ?>
</section>
<?php page_footer();
