<?php
/* The add / edit product form. Variables: $values (field => text), $errors (field => message),
 * $action (form URL), $submitLabel. */
?>
<form class="form" method="post" action="<?= e($action) ?>" novalidate>
    <?= csrf_field() ?>
    <div class="grid-2">
        <label>Name
            <input name="name" maxlength="100" required value="<?= e($values['name'] ?? '') ?>"
                   <?= isset($errors['name']) ? 'aria-invalid="true"' : '' ?>>
            <?= field_error($errors, 'name') ?>
        </label>
        <label>SKU
            <input name="sku" maxlength="32" required placeholder="ABC-100" value="<?= e($values['sku'] ?? '') ?>"
                   <?= isset($errors['sku']) ? 'aria-invalid="true"' : '' ?>>
            <?= field_error($errors, 'sku') ?>
        </label>
        <label>Price
            <input name="price" inputmode="decimal" required placeholder="0.00" value="<?= e($values['price'] ?? '') ?>"
                   <?= isset($errors['price']) ? 'aria-invalid="true"' : '' ?>>
            <?= field_error($errors, 'price') ?>
        </label>
        <label>Quantity in stock
            <input name="quantity" type="number" min="0" step="1" required value="<?= e($values['quantity'] ?? '0') ?>"
                   <?= isset($errors['quantity']) ? 'aria-invalid="true"' : '' ?>>
            <?= field_error($errors, 'quantity') ?>
        </label>
    </div>
    <label>Description
        <textarea name="description" rows="4" maxlength="1000"
                  <?= isset($errors['description']) ? 'aria-invalid="true"' : '' ?>><?= e($values['description'] ?? '') ?></textarea>
        <?= field_error($errors, 'description') ?>
    </label>
    <div class="actions">
        <button class="btn btn-primary" type="submit"><?= e($submitLabel) ?></button>
        <a class="btn" href="<?= e(url('products/')) ?>">Cancel</a>
    </div>
</form>
