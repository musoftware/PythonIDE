<?= view('store/top', ['title' => 'Log in']) ?>
<h1>Log in</h1>
<?php if ($error): ?><p class="error"><?= esc($error) ?></p><?php endif ?>
<form method="post" action="/login" class="login">
  <?= csrf_field() ?>
  <input type="hidden" name="next" value="<?= esc((string) $next) ?>">
  <label>User name <input name="username"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>
<?= view('store/bottom') ?>
