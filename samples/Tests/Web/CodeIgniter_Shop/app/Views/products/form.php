<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<h1><?= esc($title) ?></h1>

<?php $action = $product === null ? url_to('products.create') : url_to('products.update', $product['id']); ?>
<?= form_open($action, ['class' => 'form']) ?>
    <label><?= lang('Shop.fields.name') ?>
        <input name="name" value="<?= old('name', $product['name'] ?? '') ?>" required>
    </label>
    <label><?= lang('Shop.fields.sku') ?>
        <input name="sku" value="<?= old('sku', $product['sku'] ?? '') ?>" required>
    </label>
    <div class="row">
        <label><?= lang('Shop.fields.price') ?>
            <input name="price" type="number" step="0.01" min="0" value="<?= old('price', $product['price'] ?? '') ?>" required>
        </label>
        <label><?= lang('Shop.fields.stock') ?>
            <input name="stock" type="number" min="0" value="<?= old('stock', $product['stock'] ?? 0) ?>" required>
        </label>
    </div>
    <label><?= lang('Shop.fields.description') ?>
        <textarea name="description" rows="4"><?= old('description', $product['description'] ?? '') ?></textarea>
    </label>
    <div class="row">
        <button type="submit"><?= lang('Shop.save') ?></button>
        <a href="<?= url_to('products.index') ?>"><?= lang('Shop.cancel') ?></a>
    </div>
<?= form_close() ?>
<?= $this->endSection() ?>
