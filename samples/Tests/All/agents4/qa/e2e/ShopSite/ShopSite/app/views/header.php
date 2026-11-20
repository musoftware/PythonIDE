<?php
/* Page header: included by page_header($title, $active). Variables: $title, $active, $user, $flashes. */
$nav = $user
    ? ['home' => ['Dashboard', url('/')], 'products' => ['Products', url('products/')],
       'account' => ['Account', url('account.php')]]
    : ['home' => ['Home', url('/')], 'login' => ['Log in', url('login.php')],
       'register' => ['Register', url('register.php')]];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="<?= e(config('app_name')) ?> - a PHP + SQLite data application.">
    <title><?= e($title) ?> - <?= e(config('app_name')) ?></title>
    <link rel="stylesheet" href="<?= e(url('assets/css/site.css')) ?>">
    <script src="<?= e(url('assets/js/site.js')) ?>" defer></script>
</head>
<body>
<header class="site-header">
    <div class="container header-row">
        <a class="brand" href="<?= e(url('/')) ?>"><?= e(config('app_name')) ?></a>
        <button class="nav-toggle" type="button" aria-controls="site-nav" aria-expanded="false">Menu</button>
        <nav id="site-nav" class="site-nav">
            <?php foreach ($nav as $key => [$label, $href]): ?>
                <a href="<?= e($href) ?>"<?= $key === $active ? ' class="active" aria-current="page"' : '' ?>><?= e($label) ?></a>
            <?php endforeach; ?>
            <?php if ($user): ?>
                <form class="inline" method="post" action="<?= e(url('logout.php')) ?>">
                    <?= csrf_field() ?>
                    <button class="link-button" type="submit">Log out (<?= e($user['username']) ?>)</button>
                </form>
            <?php endif; ?>
        </nav>
    </div>
</header>
<main class="container">
<?php foreach ($flashes as $f): ?>
    <div class="flash flash-<?= e($f['type']) ?>" role="status"><?= e($f['message']) ?></div>
<?php endforeach; ?>
