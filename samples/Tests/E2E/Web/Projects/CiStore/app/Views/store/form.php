<?= view('store/top', ['title' => $title]) ?>
<h1><?= esc($title) ?></h1>
<?php foreach ($errors as $e): ?><p class="error"><?= esc($e) ?></p><?php endforeach ?>
<form method="post" class="product">
  <?= csrf_field() ?>
  <label>Name <input name="name" value="<?= esc($p['name'] ?? '') ?>"></label>
  <label>Price <input name="price" value="<?= esc((string) ($p['price'] ?? '')) ?>" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
<?php if ($id): ?>
<form method="post" action="/products/<?= (int) $id ?>/delete" class="delete">
  <?= csrf_field() ?><button type="submit">Delete</button>
</form>
<?php endif ?>
<?= view('store/bottom') ?>
