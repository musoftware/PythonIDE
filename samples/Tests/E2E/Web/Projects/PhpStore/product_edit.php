<?php
require __DIR__ . '/lib.php';
require_login();
$id = (int)($_GET['id'] ?? 0);
$st = db()->prepare('SELECT * FROM products WHERE id = ?');
$st->execute([$id]);
$row = $st->fetch();
if (!$row) { http_response_code(404); exit('Not found'); }
$errors = []; $name = $row['name']; $price = $row['price'];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    [$errors, $name, $price] = validate_product($_POST);
    if (!$errors) {
        db()->prepare('UPDATE products SET name = ?, price = ? WHERE id = ?')->execute([$name, $price, $id]);
        header('Location: /products.php');
        exit;
    }
    http_response_code(422);
}
layout_top('Edit product');
echo '<h1>Edit product</h1>';
require __DIR__ . '/product_form.php';
?>
<form method="post" action="/product_delete.php" class="delete" onsubmit="return confirm('Delete?')">
  <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>">
  <input type="hidden" name="id" value="<?= $id ?>">
  <button type="submit">Delete</button>
</form>
<?php layout_bottom();
