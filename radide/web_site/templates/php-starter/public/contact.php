<?php
require dirname(__DIR__) . '/app/bootstrap.php';

$values = ['name' => '', 'email' => '', 'message' => ''];
$errors = [];
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    foreach ($values as $k => $_) {
        $values[$k] = is_string($_POST[$k] ?? null) ? trim($_POST[$k]) : '';
    }
    if (!csrf_valid()) {
        http_response_code(403);
        $errors['form'] = 'The form expired. Please send it again.';
    } elseif (($_POST['website'] ?? '') !== '') {      // honeypot field: only bots fill it
        $errors['form'] = 'Your message could not be sent.';
    } else {
        if ($values['name'] === '' || mb_strlen($values['name']) > 100) {
            $errors['name'] = 'Please enter your name (at most 100 characters).';
        }
        if (filter_var($values['email'], FILTER_VALIDATE_EMAIL) === false) {
            $errors['email'] = 'Please enter a valid e-mail address.';
        }
        if (mb_strlen($values['message']) < 10 || mb_strlen($values['message']) > 5000) {
            $errors['message'] = 'The message must have 10 to 5000 characters.';
        }
    }
    if (!$errors) {
        $dir = APP_ROOT . '/data';
        if (!is_dir($dir)) {
            mkdir($dir, 0700, true);
        }
        $record = $values + ['date' => date('c'), 'ip' => $_SERVER['REMOTE_ADDR'] ?? ''];
        file_put_contents($dir . '/messages.jsonl', json_encode($record, JSON_UNESCAPED_UNICODE) . "\n",
            FILE_APPEND | LOCK_EX);
        flash('Thank you, ' . $values['name'] . '! Your message was sent.');
        header('Location: /contact.php', true, 303);
        exit;
    }
    if (http_response_code() === 200) {
        http_response_code(422);
    }
}
$err = fn(string $f) => isset($errors[$f]) ? '<span class="error">' . e($errors[$f]) . '</span>' : '';
page_header('Contact', 'contact');
?>
<h1>Contact</h1>
<?php if (isset($errors['form'])): ?><div class="notice error-box"><?= e($errors['form']) ?></div><?php endif; ?>
<form class="contact" method="post" action="/contact.php" novalidate>
    <input type="hidden" name="csrf_token" value="<?= e(csrf_token()) ?>">
    <label>Name <input name="name" maxlength="100" required value="<?= e($values['name']) ?>"><?= $err('name') ?></label>
    <label>E-mail <input name="email" type="email" required value="<?= e($values['email']) ?>"><?= $err('email') ?></label>
    <label>Message <textarea name="message" rows="6" required><?= e($values['message']) ?></textarea><?= $err('message') ?></label>
    <label class="hp" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
    <button class="button" type="submit">Send</button>
</form>
<?php page_footer();
