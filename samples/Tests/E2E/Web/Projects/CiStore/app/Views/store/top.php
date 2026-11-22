<?php /** @var string $title */ ?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= esc($title ?? 'RAD Store') ?> - RAD Store</title>
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a>
<?php if (session('user')): ?>
  <span class="user"><?= esc(session('user')) ?></span>
  <form method="post" action="/logout" style="display:inline"><?= csrf_field() ?><button type="submit">Log out</button></form>
<?php else: ?>
  <a href="/login">Log in</a>
<?php endif ?>
</nav>
<main>
