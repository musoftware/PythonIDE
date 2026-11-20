<?php
require dirname(__DIR__) . '/app/bootstrap.php';

if (current_user()) {
    redirect('/');
}
$errors = [];
$login = '';
if (is_post()) {
    verify_csrf();
    $login = post_str('login');
    $password = (string) ($_POST['password'] ?? '');
    if ($login === '' || $password === '') {
        $errors['form'] = 'Enter your user name (or e-mail) and password.';
    } else {
        $result = attempt_login($login, $password);
        if (is_array($result)) {
            $intended = safe_local_path($_SESSION['intended'] ?? null);
            unset($_SESSION['intended']);
            login_user($result);
            flash('success', 'Welcome back, ' . $result['username'] . '!');
            if ($intended !== null) {
                header('Location: ' . $intended, true, 303);
                exit;
            }
            redirect('/');
        }
        $errors['form'] = $result;
        http_response_code(422);
    }
}
page_header('Log in', 'login');
?>
<section class="card narrow">
    <h1>Log in</h1>
    <?php if (isset($errors['form'])): ?><div role="alert" class="flash flash-error"><?= e($errors['form']) ?></div><?php endif; ?>
    <form method="post" action="<?= e(url('login.php')) ?>" class="form">
        <?= csrf_field() ?>
        <label>User name or e-mail
            <input type="text" name="login" autocomplete="username" required autofocus value="<?= e($login) ?>"/>
        </label>
        <label>Password
            <input type="password" name="password" autocomplete="current-password" required/>
        </label>
        <div class="actions">
            <button type="submit" class="btn btn-primary">Log in</button>
            <a href="<?= e(url('register.php')) ?>">No account yet? Register</a>
        </div>
    </form>
</section>
<?php page_footer();
?><p class="design-added">added</p>