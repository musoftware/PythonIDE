<?php
require __DIR__ . '/lib.php';
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    // demo account: admin / secret
    if (($_POST['username'] ?? '') === 'admin' && password_verify($_POST['password'] ?? '', password_hash('secret', PASSWORD_DEFAULT))) {
        session_regenerate_id(true);
        $_SESSION['user'] = 'admin';
        $next = $_POST['next'] ?? '/products.php';
        header('Location: ' . (str_starts_with($next, '/') ? $next : '/products.php'));
        exit;
    }
    $error = 'Invalid user name or password';
    http_response_code(401);
}
layout_top('Log in');
?>
<h1>Log in</h1>
<?php if ($error): ?><p class="error"><?= h($error) ?></p><?php endif; ?>
<form method="post" class="login">
  <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>">
  <input type="hidden" name="next" value="<?= h($_GET['next'] ?? '/products.php') ?>">
  <label>User name <input name="username" autocomplete="username"></label>
  <label>Password <input name="password" type="password" autocomplete="current-password"></label>
  <button type="submit">Log in</button>
</form>
<?php layout_bottom();
