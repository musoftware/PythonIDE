<?php
require dirname(__DIR__) . '/app/bootstrap.php';

$user = current_user();
page_header($user ? 'Dashboard' : 'Welcome', 'home');

if ($user):
    $stats = product_stats();
    [$recent] = product_search('', 1, 5, 'updated');
?>
<h1>Hello, <?= e($user['username']) ?></h1>
<section class="stats">
    <div class="stat"><span class="stat-value"><?= $stats['products'] ?></span><span class="stat-label">Products</span></div>
    <div class="stat"><span class="stat-value"><?= $stats['units'] ?></span><span class="stat-label">Units in stock</span></div>
    <div class="stat"><span class="stat-value"><?= e(format_price($stats['value_cents'])) ?></span><span class="stat-label">Stock value</span></div>
    <div class="stat"><span class="stat-value"><?= $stats['out_of_stock'] ?></span><span class="stat-label">Out of stock</span></div>
</section>
<section class="card">
    <div class="card-head">
        <h2>Recently updated</h2>
        <a href="<?= e(url('products/create.php')) ?>" class="btn btn-primary">Add product</a>
    </div>
    <?php if (!$recent): ?>
        <p class="muted">No products yet. <a href="<?= e(url('products/create.php')) ?>">Add the first one.</a></p>
    <?php else: ?>
        <ul class="plain-list">
            <?php foreach ($recent as $p): ?>
                <li><a href="<?= e(url('products/edit.php?id=' . $p['id'])) ?>"><?= e($p['name']) ?></a>
                    <span class="muted"><?= e($p['sku']) ?> &middot; <?= e(format_price((int) $p['price_cents'])) ?></span></li>
            <?php endforeach; ?>
        </ul>
    <?php endif; ?>
</section>
<?php else: ?>
<section class="hero">
    <h1><?= e(config('app_name')) ?></h1>
    <p>A complete PHP + SQLite data application: accounts, secure login and a products catalogue
       with search, add, edit and delete.</p>
    <p>
        <a href="<?= e(url('register.php')) ?>" class="btn btn-primary">Create an account</a>
        <a href="<?= e(url('login.php')) ?>" class="btn">Log in</a>
    </p>
</section>
<section class="features">
    <div class="card"><h2>Secure by default</h2><p>password_hash, session id regeneration, CSRF tokens,
        prepared statements, escaped output and login throttling.</p></div>
    <div class="card"><h2>CRUD module</h2><p>List, search, sort and paginate products; add, edit and
        delete them with server-side validation.</p></div>
    <div class="card"><h2>No server setup</h2><p>One SQLite file in <code>data/</code>, created with its
        tables on the first request. Run it with <code>php -S</code>.</p></div>
</section>
<?php endif;
page_footer();
?><p class="design-added">added</p>