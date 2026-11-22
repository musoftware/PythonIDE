<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Guestbook - a PHP web site with a SQLite database (RAD IDE example).
// GET  /            the form and the messages, newest first, PAGE_SIZE per page (?page=2 ...)
// POST /            action=add (name, message) or action=delete (id) - CSRF protected, then a redirect
//                   (Post/Redirect/Get) so a page reload never posts twice
// GET  /?lang=ar    Arabic interface, right-to-left layout;  /api.php returns the messages as JSON

require __DIR__ . '/../app/bootstrap.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $flash = 'expired';
    if (csrf_ok()) {
        $action = $_POST['action'] ?? '';
        if ($action === 'add') {
            $name = trim((string)($_POST['name'] ?? ''));
            $message = trim((string)($_POST['message'] ?? ''));
            if ($name === '' || $message === '' || mb_strlen($name) > 60 || mb_strlen($message) > 1000) {
                $flash = 'bad';
            } else {
                $st = db()->prepare('INSERT INTO messages (name, message) VALUES (?, ?)');
                $st->execute([$name, $message]);
                $_SESSION['mine'][] = (int)db()->lastInsertId();
                $flash = 'thanks';
            }
        } elseif ($action === 'delete') {
            $id = (int)($_POST['id'] ?? 0);
            if (in_array($id, my_ids(), true)) {
                db()->prepare('DELETE FROM messages WHERE id = ?')->execute([$id]);
                $_SESSION['mine'] = array_values(array_diff(my_ids(), [$id]));
                $flash = 'deleted';
            }
        }
    }
    $_SESSION['flash'] = $flash;
    header('Location: index.php', true, 303);
    exit;
}

$total = (int)db()->query('SELECT COUNT(*) FROM messages')->fetchColumn();
$pages = max(1, (int)ceil($total / PAGE_SIZE));
$page = min($pages, max(1, (int)($_GET['page'] ?? 1)));
$st = db()->prepare('SELECT * FROM messages ORDER BY id DESC LIMIT ? OFFSET ?');
$st->bindValue(1, PAGE_SIZE, PDO::PARAM_INT);
$st->bindValue(2, ($page - 1) * PAGE_SIZE, PDO::PARAM_INT);
$st->execute();
$messages = $st->fetchAll();
$flash = $_SESSION['flash'] ?? '';
unset($_SESSION['flash']);
$rtl = lang() === 'ar';
?>
<!DOCTYPE html>
<html lang="<?= lang() ?>" dir="<?= $rtl ? 'rtl' : 'ltr' ?>">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= e(t('title')) ?></title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<main>
    <header>
        <h1><?= e(t('title')) ?></h1>
        <a class="lang" href="?lang=<?= $rtl ? 'en' : 'ar' ?>"><?= e(t('other')) ?></a>
    </header>

    <?php if ($flash): ?>
        <p class="flash <?= $flash === 'thanks' || $flash === 'deleted' ? 'ok' : 'err' ?>"><?= e(t($flash)) ?></p>
    <?php endif; ?>

    <form method="post" class="card">
        <input type="hidden" name="csrf" value="<?= e(csrf_token()) ?>">
        <input type="hidden" name="action" value="add">
        <label><?= e(t('name')) ?> <input name="name" maxlength="60" required dir="auto"></label>
        <label><?= e(t('message')) ?> <textarea name="message" rows="3" maxlength="1000" required dir="auto"></textarea></label>
        <button type="submit"><?= e(t('sign')) ?></button>
    </form>

    <p class="muted"><?= $total ?> <?= e(t('count')) ?></p>

    <?php if (!$messages): ?>
        <p class="muted"><?= e(t('empty')) ?></p>
    <?php endif; ?>

    <?php foreach ($messages as $m): ?>
        <article class="card msg" id="m<?= (int)$m['id'] ?>">
            <div class="meta"><strong dir="auto"><?= e($m['name']) ?></strong> · <time><?= e($m['created']) ?> UTC</time></div>
            <p dir="auto"><?= nl2br(e($m['message'])) ?></p>
            <?php if (in_array((int)$m['id'], my_ids(), true)): ?>
                <form method="post" class="del">
                    <input type="hidden" name="csrf" value="<?= e(csrf_token()) ?>">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="id" value="<?= (int)$m['id'] ?>">
                    <button type="submit"><?= e(t('delete')) ?></button>
                </form>
            <?php endif; ?>
        </article>
    <?php endforeach; ?>

    <nav class="pager">
        <?php if ($page > 1): ?><a href="?page=<?= $page - 1 ?>"><?= e(t('newer')) ?></a><?php endif; ?>
        <span><?= $page ?> / <?= $pages ?></span>
        <?php if ($page < $pages): ?><a href="?page=<?= $page + 1 ?>"><?= e(t('older')) ?></a><?php endif; ?>
    </nav>
    <footer class="muted">(c) 2026 Musoftware - https://musoftwares.com - MIT License</footer>
</main>
</body>
</html>
