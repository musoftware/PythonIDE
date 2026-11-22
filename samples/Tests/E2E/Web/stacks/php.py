# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store in plain PHP + SQLite (PDO): New Project > Web > PHP Empty Site."""
TITLE = "PHP + SQLite (PHP Empty Site)"
LANG, TEMPLATE, NAME = "php-web", "php-empty", "PhpStore"
TOOLS = ["php"]
WEBROOT = "."
DB_FILE = "data/store.db"
DESIGN = "index.php"
ROUTES = {
    "home": "/", "products": "/products.php", "add": "/product_add.php", "edit": "/product_edit.php?id={id}",
    "login": "/login.php", "logout": "/logout.php", "ar": "/ar.php", "api": "/api/products.php",
    "css": "/assets/site.css", "js": "/assets/app.js",
}
DEBUG = {"file": "products.php", "match": "$rows = db()", "path": "/products.php", "var": "$q"}
INTELLI = {"file": "products.php", "after": "<?php", "type": "str_rep", "expect": "str_replace",
           "html_file": "index.php", "css_file": "assets/site.css"}
PUBLISH_EXPECT = ["index.php", "products.php", "lib.php", "api/products.php", "assets/site.css", "ar.php"]
PUBLISH_FORBID = ["data/store.db"]


def serve_published(dest, port, php="php"):
    """How the published copy is run (like the host would): php -S on its folder."""
    return [php, "-S", f"127.0.0.1:{port}", "-t", str(dest)], str(dest), None


DB_SQL = """-- RAD Store schema (run from the Databases workspace)
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL
);
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

LIB = r"""<?php
// RAD Store - shared code: database, session, CSRF, auth, layout
declare(strict_types=1);
session_start();

function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $dir = __DIR__ . '/data';
        if (!is_dir($dir)) { mkdir($dir, 0777, true); }
        $pdo = new PDO('sqlite:' . $dir . '/store.db');
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        // first run on a new host: create the schema and the demo rows
        $pdo->exec('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)');
        if ((int)$pdo->query('SELECT COUNT(*) FROM products')->fetchColumn() === 0) {
            $pdo->exec("INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450)");
        }
    }
    return $pdo;
}

function h(?string $s): string { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function csrf_token(): string {
    if (empty($_SESSION['csrf'])) { $_SESSION['csrf'] = bin2hex(random_bytes(16)); }
    return $_SESSION['csrf'];
}

function csrf_check(): void {
    if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) {
        http_response_code(400);
        exit('Bad CSRF token');
    }
}

function user(): ?string { return $_SESSION['user'] ?? null; }

function require_login(): void {
    if (!user()) { header('Location: /login.php?next=' . urlencode($_SERVER['REQUEST_URI'])); exit; }
}

function validate_product(array $in): array {
    $errors = [];
    $name = trim($in['name'] ?? '');
    $price = $in['price'] ?? '';
    if ($name === '') { $errors[] = 'Name is required'; }
    if (!is_numeric($price) || (float)$price < 0) { $errors[] = 'Price must be a positive number'; }
    return [$errors, $name, (float)$price];
}

function layout_top(string $title): void {
    $u = user();
    echo '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">';
    echo '<title>' . h($title) . ' - RAD Store</title><link rel="stylesheet" href="/assets/site.css"></head><body>';
    echo '<nav class="top"><a href="/">Home</a> <a href="/products.php">Products</a> <a href="/ar.php">العربية</a> ';
    echo $u ? '<span class="user">' . h($u) . '</span> <a href="/logout.php">Log out</a>' : '<a href="/login.php">Log in</a>';
    echo '</nav><main>';
}

function layout_bottom(): void { echo '</main><script src="/assets/app.js"></script></body></html>'; }
"""

INDEX = """<?php require __DIR__ . '/lib.php'; ?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products.php">Products</a> <a href="/ar.php">العربية</a> <a href="/login.php">Log in</a></nav>
<main id="home">
</main>
<script src="/assets/app.js"></script>
</body>
</html>
"""

PRODUCTS = r"""<?php
require __DIR__ . '/lib.php';
$q = trim($_GET['q'] ?? '');
$rows = db()->prepare('SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id');
$rows->execute(['%' . $q . '%']);
$products = $rows->fetchAll();
layout_top('Products');
?>
<h1>Products</h1>
<form method="get" action="/products.php" class="search"><input name="q" value="<?= h($q) ?>" placeholder="Search"><button>Search</button></form>
<?php if (user()): ?><p><a class="btn" href="/product_add.php">Add product</a></p><?php endif; ?>
<table id="products">
<thead><tr><th>Name</th><th>Price</th><th></th></tr></thead>
<tbody>
<?php foreach ($products as $p): ?>
<tr data-id="<?= (int)$p['id'] ?>"><td class="name"><?= h($p['name']) ?></td><td class="price"><?= number_format((float)$p['price'], 2) ?></td>
<td><?php if (user()): ?><a href="/product_edit.php?id=<?= (int)$p['id'] ?>">Edit</a><?php endif; ?></td></tr>
<?php endforeach; ?>
</tbody>
</table>
<p class="count"><?= count($products) ?> products</p>
<?php layout_bottom();
"""

FORM_VIEW = r"""<?php
// product form (add + edit)
?>
<?php foreach ($errors as $e): ?><p class="error"><?= h($e) ?></p><?php endforeach; ?>
<form method="post" class="product">
  <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>">
  <label>Name <input name="name" value="<?= h($name) ?>" required></label>
  <label>Price <input name="price" value="<?= h((string)$price) ?>" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
"""

ADD = r"""<?php
require __DIR__ . '/lib.php';
require_login();
$errors = []; $name = ''; $price = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    [$errors, $name, $price] = validate_product($_POST);
    if (!$errors) {
        db()->prepare('INSERT INTO products (name, price) VALUES (?, ?)')->execute([$name, $price]);
        header('Location: /products.php');
        exit;
    }
    http_response_code(422);
}
layout_top('Add product');
echo '<h1>Add product</h1>';
require __DIR__ . '/product_form.php';
layout_bottom();
"""

EDIT = r"""<?php
require __DIR__ . '/lib.php';
require_login();
$id = (int)($_GET['id'] ?? 0);
$st = db()->prepare('SELECT * FROM products WHERE id = ?');
$st->execute([$id]);
$row = $st->fetch();
if (!$row) { http_response_code(404); exit('Not found'); }
$errors = []; $name = $row['name']; $price = $row['price'];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    [$errors, $name, $price] = validate_product($_POST);
    if (!$errors) {
        db()->prepare('UPDATE products SET name = ?, price = ? WHERE id = ?')->execute([$name, $price, $id]);
        header('Location: /products.php');
        exit;
    }
    http_response_code(422);
}
layout_top('Edit product');
echo '<h1>Edit product</h1>';
require __DIR__ . '/product_form.php';
?>
<form method="post" action="/product_delete.php" class="delete" onsubmit="return confirm('Delete?')">
  <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>">
  <input type="hidden" name="id" value="<?= $id ?>">
  <button type="submit">Delete</button>
</form>
<?php layout_bottom();
"""

DELETE = r"""<?php
require __DIR__ . '/lib.php';
require_login();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit('POST only'); }
csrf_check();
db()->prepare('DELETE FROM products WHERE id = ?')->execute([(int)($_POST['id'] ?? 0)]);
header('Location: /products.php');
"""

LOGIN = r"""<?php
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
"""

LOGOUT = r"""<?php
require __DIR__ . '/lib.php';
$_SESSION = [];
session_destroy();
header('Location: /');
"""

AR = r"""<?php require __DIR__ . '/lib.php';
$count = (int)db()->query('SELECT COUNT(*) FROM products')->fetchColumn(); ?><!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="/assets/site.css"></head>
<body class="rtl">
<nav class="top"><a href="/">English</a> <a href="/products.php">المنتجات</a></nav>
<main>
<h1>مرحبا بكم في متجر راد</h1>
<p id="count">عدد المنتجات: <?= $count ?></p>
</main>
</body>
</html>
"""

API = r"""<?php
require dirname(__DIR__) . '/lib.php';
header('Content-Type: application/json; charset=utf-8');
$rows = db()->query('SELECT id, name, price FROM products ORDER BY id')->fetchAll();
foreach ($rows as &$r) { $r['id'] = (int)$r['id']; $r['price'] = (float)$r['price']; }
echo json_encode($rows, JSON_UNESCAPED_UNICODE);
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f7fb; color: #222; }
nav.top { background: #3b3f8f; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-right: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #3b3f8f, #6a5ae0); color: #fff; border-radius: 12px; }
body.rtl { direction: rtl; }
@media (max-width: 600px) { nav.top a { display: inline-block; margin: 4px; } }
"""

JS = """// RAD Store - small enhancements
document.addEventListener('DOMContentLoaded', () => {
  document.body.dataset.ready = '1';
});
"""


def files() -> dict:
    return {"lib.php": LIB, "index.php": INDEX, "products.php": PRODUCTS, "product_form.php": FORM_VIEW,
            "product_add.php": ADD, "product_edit.php": EDIT, "product_delete.php": DELETE, "login.php": LOGIN,
            "logout.php": LOGOUT, "ar.php": AR, "api/products.php": API, "assets/site.css": CSS,
            "assets/app.js": JS}
