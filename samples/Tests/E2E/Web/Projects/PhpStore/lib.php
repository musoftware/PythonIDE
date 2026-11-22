<?php
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
