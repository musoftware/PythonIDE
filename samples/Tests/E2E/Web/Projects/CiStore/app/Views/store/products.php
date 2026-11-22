<?= view('store/top', ['title' => 'Products']) ?>
<h1>Products</h1>
<form method="get" class="search"><input name="q" value="<?= esc($q) ?>" placeholder="Search"><button>Search</button></form>
<?php if (session('user')): ?><p><a class="btn" href="/products/add">Add product</a></p><?php endif ?>
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
<?php foreach ($products as $p): ?>
<tr data-id="<?= (int) $p['id'] ?>"><td class="name"><?= esc($p['name']) ?></td><td><?= number_format((float) $p['price'], 2) ?></td>
<td><?php if (session('user')): ?><a href="/products/<?= (int) $p['id'] ?>/edit">Edit</a><?php endif ?></td></tr>
<?php endforeach ?>
</tbody></table>
<p class="count"><?= count($products) ?> products</p>
<?= view('store/bottom') ?>
