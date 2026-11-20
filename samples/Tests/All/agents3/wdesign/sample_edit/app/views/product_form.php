<?php
/* The add / edit product form. Variables: $values (field => text), $errors (field => message),
 * $action (form URL), $submitLabel. */
?>
<form method="post" action="<?= e($action) ?>" novalidate="" class="form">
    <?= csrf_field() ?>
    <div class="grid-2">
        <label>Name
            <input type="text" name="name" maxlength="100" required value="<?= e($values['name'] ?? '') ?>" <?= isset($errors['name']) ? 'aria-invalid="true"' : '' ?>/>
            <?= field_error($errors, 'name') ?>
        </label>
        <label>SKU
            <input type="text" name="sku" maxlength="32" required placeholder="ABC-100" value="<?= e($values['sku'] ?? '') ?>" <?= isset($errors['sku']) ? 'aria-invalid="true"' : '' ?>/>
            <?= field_error($errors, 'sku') ?>
        </label>
        <label>Price
            <input type="text" name="price" inputmode="decimal" required placeholder="0.00" value="<?= e($values['price'] ?? '') ?>" <?= isset($errors['price']) ? 'aria-invalid="true"' : '' ?>/>
            <?= field_error($errors, 'price') ?>
        </label>
        <label>Quantity in stock
            <input type="number" name="quantity" min="0" step="1" required value="<?= e($values['quantity'] ?? '0') ?>" <?= isset($errors['quantity']) ? 'aria-invalid="true"' : '' ?>/>
            <?= field_error($errors, 'quantity') ?>
        </label>
    </div>
    <label>Description
        <textarea name="description" rows="4" maxlength="1000" <?= isset($errors['description']) ? 'aria-invalid="true"' : '' ?>><?= e($values['description'] ?? '') ?></textarea>
        <?= field_error($errors, 'description') ?>
    </label>
    <div class="actions">
        <button type="submit" class="btn btn-primary"><?= e($submitLabel) ?></button>
        <a href="<?= e(url('products/')) ?>" class="btn">Cancel</a>
    </div>
</form>
<p class="design-added">added</p>
