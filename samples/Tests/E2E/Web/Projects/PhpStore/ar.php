<?php require __DIR__ . '/lib.php';
$count = (int)db()->query('SELECT COUNT(*) FROM products')->fetchColumn(); ?><!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="/assets/site.css"></head>
<body class="rtl">
<nav class="top"><a href="/">English</a> <a href="/products.php">المنتجات</a></nav>
<main>
<h1>مرحبا بكم في متجر راد</h1>
<p id="count">عدد المنتجات: <?= $count ?></p>
</main>
</body>
</html>
