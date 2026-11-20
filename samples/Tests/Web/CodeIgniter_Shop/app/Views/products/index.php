<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1><?= lang('Shop.products.title') ?></h1>

<div class="toolbar">
    <form method="get" action="<?= url_to('products.index') ?>">
        <input type="search" name="q" value="<?= esc($q) ?>" placeholder="name or SKU">
        <button type="submit">Search</button>
    </form>
    <a class="button" href="<?= url_to('products.new') ?>">+ <?= lang('Shop.products.new') ?></a>
</div>

<?php if ($products === []): ?>
    <p class="muted"><?= lang('Shop.products.empty') ?></p>
<?php else: ?>
<table class="grid">
    <thead>
    <tr>
        <th><?= lang('Shop.fields.name') ?></th>
        <th><?= lang('Shop.fields.sku') ?></th>
        <th class="num"><?= lang('Shop.fields.price') ?></th>
        <th class="num"><?= lang('Shop.fields.stock') ?></th>
        <th></th>
    </tr>
    </thead>
    <tbody>
    <?php foreach ($products as $product): ?>
        <tr>
            <td><?= esc($product['name']) ?></td>
            <td><code><?= esc($product['sku']) ?></code></td>
            <td class="num"><?= money($product['price']) ?></td>
            <td class="num"><?= stock_badge((int) $product['stock']) ?> <?= (int) $product['stock'] ?></td>
            <td class="actions">
                <a href="<?= url_to('products.edit', $product['id']) ?>"><?= lang('Shop.edit') ?></a>
                <?= form_open(url_to('products.delete', $product['id']), ['class' => 'inline', 'onsubmit' => "return confirm('" . lang('Shop.products.confirm') . "')"]) ?>
                    <button type="submit" class="link danger"><?= lang('Shop.delete') ?></button>
                <?= form_close() ?>
            </td>
        </tr>
    <?php endforeach ?>
    </tbody>
</table>
<?= $pager->links() ?>
<?php endif ?>
<?= $this->endSection() ?>
