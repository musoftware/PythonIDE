<?php
// product form (add + edit)
?>
<?php foreach ($errors as $e): ?><p class="error"><?= h($e) ?></p><?php endforeach; ?>
<form method="post" class="product">
  <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>">
  <label>Name <input name="name" value="<?= h($name) ?>" required></label>
  <label>Price <input name="price" value="<?= h((string)$price) ?>" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
