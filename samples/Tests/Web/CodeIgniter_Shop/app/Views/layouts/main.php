<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= esc($title ?? '') ?> - <?= esc(config('Shop')->siteName) ?></title>
    <link rel="stylesheet" href="<?= base_url('css/shop.css') ?>">
</head>
<body>
<header class="top">
    <a class="brand" href="<?= url_to('home') ?>"><?= esc(config('Shop')->siteName) ?></a>
    <nav>
        <a href="<?= url_to('home') ?>"><?= lang('Shop.catalog') ?></a>
        <?php if (session('user_id')): ?>
            <a href="<?= url_to('products.index') ?>"><?= lang('Shop.products.title') ?></a>
            <?= form_open(url_to('logout'), ['class' => 'inline']) ?>
                <span class="muted"><?= esc(session('user_name')) ?></span>
                <button type="submit" class="link"><?= lang('Shop.login.logout') ?></button>
            <?= form_close() ?>
        <?php else: ?>
            <a href="<?= url_to('login') ?>"><?= lang('Shop.login.title') ?></a>
        <?php endif ?>
        <a href="<?= url_to('api.products') ?>">API</a>
    </nav>
</header>
<main>
    <?= $this->include('partials/flash') ?>
    <?= $this->renderSection('content') ?>
</main>
<footer class="muted">CodeIgniter <?= \CodeIgniter\CodeIgniter::CI_VERSION ?> &middot; PHP <?= PHP_VERSION ?> &middot; RAD IDE sample</footer>
</body>
</html>
