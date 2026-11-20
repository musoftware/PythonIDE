<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1><?= lang('Shop.welcome') ?></h1>

<div class="cards">
    <?php foreach ($products as $product): ?>
        <article class="card">
            <h3><?= esc($product['name']) ?></h3>
            <p class="muted"><?= esc($product['description']) ?></p>
            <p class="price"><?= money($product['price']) ?> <?= stock_badge((int) $product['stock']) ?></p>
        </article>
    <?php endforeach ?>
</div>
<?php if ($soldOut): ?>
    <p class="muted"><?= $soldOut ?> <?= lang('Shop.stock.out') ?></p>
<?php endif ?>
<?= $this->endSection() ?>
