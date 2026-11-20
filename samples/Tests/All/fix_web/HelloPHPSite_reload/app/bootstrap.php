<?php
/*
 * Included at the top of every page in public/:
 *     require dirname(__DIR__) . '/app/bootstrap.php';
 * Loads the settings and helpers, sends security headers and starts the session.
 */
declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));

$GLOBALS['config'] = require __DIR__ . '/config.php';

require __DIR__ . '/helpers.php';
require __DIR__ . '/db.php';
require __DIR__ . '/auth.php';
require __DIR__ . '/products.php';

if (!extension_loaded('pdo_sqlite')) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=utf-8');
    exit("The PHP extension pdo_sqlite is not enabled.\n"
        . "Enable it in php.ini (extension=pdo_sqlite) or start the server with\n"
        . "php -d extension=pdo_sqlite -S 127.0.0.1:8080 -t public");
}

error_reporting(E_ALL);
// Errors are shown only on the development server (php -S); a real web server never shows
// stack traces or paths to visitors.
ini_set('display_errors', PHP_SAPI === 'cli-server' ? '1' : '0');
ini_set('log_errors', '1');

// ---------------------------------------------------------------- security headers
header('X-Frame-Options: SAMEORIGIN');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');
header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; "
    . "script-src 'self'; form-action 'self'; frame-ancestors 'self'; base-uri 'self'");

// ---------------------------------------------------------------- session
$sessionPath = (string) config('session_path');
if ($sessionPath !== '') {
    if (!is_dir($sessionPath)) {
        @mkdir($sessionPath, 0700, true);
    }
    session_save_path($sessionPath);
}
ini_set('session.use_strict_mode', '1');     // refuse session ids the server did not create
ini_set('session.use_only_cookies', '1');
ini_set('session.use_trans_sid', '0');
session_name((string) config('session_name', 'APPSESSID'));
session_set_cookie_params([
    'lifetime' => 0,
    'path' => url('/'),
    'secure' => is_https(),
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

// idle timeout
$now = time();
$idle = (int) config('session_idle_timeout', 1800);
if (isset($_SESSION['user_id'], $_SESSION['last_activity']) && $now - (int) $_SESSION['last_activity'] > $idle) {
    logout_user();
    flash('warning', 'Your session expired. Please log in again.');
}
$_SESSION['last_activity'] = $now;

// open the database now: the file and its tables are created on the very first request
db();
