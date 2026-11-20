<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="<?= e(SITE_NAME) ?> - <?= e($title) ?>">
    <title><?= e($title) ?> | <?= e(SITE_NAME) ?></title>
    <link rel="stylesheet" href="/assets/css/site.css">
</head>
<body>
<header class="top">
    <div class="wrap">
        <a class="logo" href="/"><?= e(SITE_NAME) ?></a>
        <nav>
            <?php foreach ($pages as $key => [$label, $href]): ?>
                <a href="<?= e($href) ?>"<?= $key === $active ? ' class="active"' : '' ?>><?= e($label) ?></a>
            <?php endforeach; ?>
        </nav>
    </div>
</header>
<main class="wrap">
<?php if ($message): ?><div class="notice"><?= e($message) ?></div><?php endif; ?>
