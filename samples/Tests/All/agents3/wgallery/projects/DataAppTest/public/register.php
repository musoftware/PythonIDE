<?php
require dirname(__DIR__) . '/app/bootstrap.php';

if (current_user()) {
    redirect('/');
}
$errors = [];
$values = ['username' => '', 'email' => ''];
if (is_post()) {
    verify_csrf();
    $values = ['username' => post_str('username'), 'email' => post_str('email')];
    $password = (string) ($_POST['password'] ?? '');
    $confirm = (string) ($_POST['password_confirm'] ?? '');
    $errors = validate_registration($values['username'], $values['email'], $password, $confirm);
    if (!$errors) {
        $user = register_user($values['username'], $values['email'], $password);
        login_user($user);
        flash('success', 'Your account was created. Welcome, ' . $user['username'] . '!');
        redirect('/');
    }
    http_response_code(422);
}
page_header('Register', 'register');
$min = (int) config('password_min_length', 8);
?>
<section class="card narrow">
    <h1>Create an account</h1>
    <form class="form" method="post" action="<?= e(url('register.php')) ?>" novalidate>
        <?= csrf_field() ?>
        <label>User name
            <input name="username" autocomplete="username" required maxlength="30" value="<?= e($values['username']) ?>">
            <?= field_error($errors, 'username') ?>
        </label>
        <label>E-mail
            <input name="email" type="email" autocomplete="email" required maxlength="254" value="<?= e($values['email']) ?>">
            <?= field_error($errors, 'email') ?>
        </label>
        <label>Password (at least <?= $min ?> characters)
            <input name="password" type="password" autocomplete="new-password" required minlength="<?= $min ?>">
            <?= field_error($errors, 'password') ?>
        </label>
        <label>Confirm password
            <input name="password_confirm" type="password" autocomplete="new-password" required>
            <?= field_error($errors, 'password_confirm') ?>
        </label>
        <div class="actions">
            <button class="btn btn-primary" type="submit">Register</button>
            <a href="<?= e(url('login.php')) ?>">Already registered? Log in</a>
        </div>
    </form>
</section>
<?php page_footer();
