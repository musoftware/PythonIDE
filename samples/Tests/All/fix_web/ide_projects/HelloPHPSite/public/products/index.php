<?php
require dirname(__DIR__, 2) . '/app/bootstrap.php';

require_login();
$q = query_str('q');
$sort = array_key_exists(query_str('sort'), PRODUCT_SORTS) ? query_str('sort') : 'updated';
$perPage = (int) config('products_per_page', 10);
$page = max(1, (int) query_str('page'));
[$rows, $total] = product_search($q, $page, $perPage, $sort);
$pages = max(1, (int) ceil($total / $perPage));
if ($page > $pages) {
    $page = $pages;
    [$rows, $total] = product_search($q, $page, $perPage, $sort);
}
$link = fn(array $over) => url('products/?' . http_build_query(array_merge(['q' => $q, 'sort' => $sort], $over)));

page_header('Products', 'products');
?>
<div class="page-head">
    <h1>Products <span class="muted">(<?= $total ?>)</span></h1>
    <a class="btn btn-primary" href="<?= e(url('products/create.php')) ?>">Add product</a>
</div>
<form class="toolbar" method="get" action="<?= e(url('products/')) ?>" role="search">
    <input type="search" name="q" placeholder="Search name, SKU or description" value="<?= e($q) ?>" aria-label="Search">
    <select name="sort" aria-label="Sort by">
        <?php foreach (['updated' => 'Recently updated', 'name' => 'Name', 'sku' => 'SKU', 'price' => 'Price (low first)',
                        'price_desc' => 'Price (high first)', 'quantity' => 'Quantity'] as $key => $label): ?>
            <option value="<?= e($key) ?>"<?= $key === $sort ? ' selected' : '' ?>><?= e($label) ?></option>
        <?php endforeach; ?>
    </select>
    <button class="btn" type="submit">Search</button>
    <?php if ($q !== ''): ?><a href="<?= e(url('products/')) ?>">Clear</a><?php endif; ?>
</form>

<?php if (!$rows): ?>
    <p class="card muted"><?= $q !== '' ? 'No product matches "' . e($q) . '".' : 'No products yet.' ?></p>
<?php else: ?>
<div class="table-wrap">
<table class="table">
    <thead><tr><th>Name</th><th>SKU</th><th class="num">Price</th><th class="num">Qty</th><th>Updated</th><th></th></tr></thead>
    <tbody>
    <?php foreach ($rows as $p): ?>
        <tr>
            <td data-label="Name"><a href="<?= e(url('products/edit.php?id=' . $p['id'])) ?>"><?= e($p['name']) ?></a></td>
            <td data-label="SKU"><code><?= e($p['sku']) ?></code></td>
            <td data-label="Price" class="num"><?= e(format_price((int) $p['price_cents'])) ?></td>
            <td data-label="Qty" class="num<?= (int) $p['quantity'] === 0 ? ' warn' : '' ?>"><?= (int) $p['quantity'] ?></td>
            <td data-label="Updated"><?= e(format_time($p['updated_at'])) ?></td>
            <td class="row-actions">
                <a class="btn btn-small" href="<?= e(url('products/edit.php?id=' . $p['id'])) ?>">Edit</a>
                <form class="inline" method="post" action="<?= e(url('products/delete.php')) ?>"
                      data-confirm="Delete <?= e($p['name']) ?>?">
                    <?= csrf_field() ?>
                    <input type="hidden" name="id" value="<?= (int) $p['id'] ?>">
                    <button class="btn btn-small btn-danger" type="submit">Delete</button>
                </form>
            </td>
        </tr>
    <?php endforeach; ?>
    </tbody>
</table>
</div>
<?php if ($pages > 1): ?>
<nav class="pagination" aria-label="Pages">
    <?php if ($page > 1): ?><a href="<?= e($link(['page' => $page - 1])) ?>">&laquo; Previous</a><?php endif; ?>
    <span>Page <?= $page ?> of <?= $pages ?></span>
    <?php if ($page < $pages): ?><a href="<?= e($link(['page' => $page + 1])) ?>">Next &raquo;</a><?php endif; ?>
</nav>
<?php endif; ?>
<?php endif;
page_footer();
