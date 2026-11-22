<?php
require __DIR__ . '/lib.php';
$q = trim($_GET['q'] ?? '');
$rows = db()->prepare('SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id');
$rows->execute(['%' . $q . '%']);
$products = $rows->fetchAll();
layout_top('Products');
?>
<h1>Products</h1>
<form method="get" action="/products.php" class="search"><input name="q" value="<?= h($q) ?>" placeholder="Search"><button>Search</button></form>
<?php if (user()): ?><p><a class="btn" href="/product_add.php">Add product</a></p><?php endif; ?>
<table id="products">
<thead><tr><th>Name</th><th>Price</th><th></th></tr></thead>
<tbody>
<?php foreach ($products as $p): ?>
<tr data-id="<?= (int)$p['id'] ?>"><td class="name"><?= h($p['name']) ?></td><td class="price"><?= number_format((float)$p['price'], 2) ?></td>
<td><?php if (user()): ?><a href="/product_edit.php?id=<?= (int)$p['id'] ?>">Edit</a><?php endif; ?></td></tr>
<?php endforeach; ?>
</tbody>
</table>
<p class="count"><?= count($products) ?> products</p>
<?php layout_bottom();
