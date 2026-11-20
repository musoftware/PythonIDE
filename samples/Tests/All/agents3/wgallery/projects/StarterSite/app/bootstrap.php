<?php
/* Included by every page: settings, helpers, session (for CSRF tokens and flash messages). */
declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
const SITE_NAME = 'Starter Site';

header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: SAMEORIGIN');
header('Referrer-Policy: same-origin');

ini_set('session.use_strict_mode', '1');
session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax']);
session_start();

/** Escape text for HTML. */
function e($value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function csrf_token(): string
{
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function csrf_valid(): bool
{
    $sent = $_POST['csrf_token'] ?? '';
    return is_string($sent) && $sent !== '' && hash_equals(csrf_token(), $sent);
}

function flash(?string $message = null): ?string
{
    if ($message !== null) {
        $_SESSION['flash'] = $message;
        return null;
    }
    $m = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return $m;
}

/** Layout: page_header('About', 'about') ... page_footer(). */
function page_header(string $title, string $active = ''): void
{
    $pages = ['home' => ['Home', '/'], 'about' => ['About', '/about.php'], 'contact' => ['Contact', '/contact.php']];
    $message = flash();
    require APP_ROOT . '/app/views/header.php';
}

function page_footer(): void
{
    require APP_ROOT . '/app/views/footer.php';
}
