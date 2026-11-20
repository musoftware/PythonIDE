<?php
require dirname(__DIR__) . '/app/bootstrap.php';

$user = require_login();
$errors = [];
if (is_post()) {
    verify_csrf();
    $current = (string) ($_POST['current_password'] ?? '');
    $new = (string) ($_POST['password'] ?? '');
    $confirm = (string) ($_POST['password_confirm'] ?? '');
    $errors = validate_new_password($new, $confirm);
    if (!$errors) {
        if (change_password((int) $user['id'], $current, $new)) {
            flash('success', 'Your password was changed.');
            redirect('account.php');
        }
        $errors['current_password'] = 'The current password is not correct.';
    }
    http_response_code(422);
}
page_header('Account', 'account');
?>
<section class="card narrow">
    <h1>Account</h1>
    <dl class="details">
        <dt>User name</dt><dd><?= e($user['username']) ?></dd>
        <dt>E-mail</dt><dd><?= e($user['email']) ?></dd>
        <dt>Member since</dt><dd><?= e($user['created_at']) ?> (UTC)</dd>
    </dl>
    <h2>Change password</h2>
    <form class="form" method="post" action="<?= e(url('account.php')) ?>" novalidate>
        <?= csrf_field() ?>
        <label>Current password
            <input name="current_password" type="password" autocomplete="current-password" required>
            <?= field_error($errors, 'current_password') ?>
        </label>
        <label>New password
            <input name="password" type="password" autocomplete="new-password" required>
            <?= field_error($errors, 'password') ?>
        </label>
        <label>Confirm new password
            <input name="password_confirm" type="password" autocomplete="new-password" required>
            <?= field_error($errors, 'password_confirm') ?>
        </label>
        <div class="actions"><button class="btn btn-primary" type="submit">Change password</button></div>
    </form>
</section>
<?php page_footer();
