<?php
/* Small helpers used by every page: escaping, URLs, redirects, flash messages,
 * CSRF tokens, request input and page layout. */
declare(strict_types=1);

/** A value from app/config.php. */
function config(string $key, $default = null)
{
    return $GLOBALS['config'][$key] ?? $default;
}

/** Escape text for HTML output. ALWAYS use it for data that comes from users or the database. */
function e($value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Absolute URL path of a page inside the site: url('products/') -> '/products/'. */
function url(string $path = ''): string
{
    $base = rtrim((string) config('base_url', ''), '/');
    return $base . '/' . ltrim($path, '/');
}

function redirect(string $path): void
{
    header('Location: ' . url($path), true, 303);
    exit;
}

function is_https(): bool
{
    return (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || (($_SERVER['SERVER_PORT'] ?? '') === '443');
}

function is_post(): bool
{
    return ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST';
}

/** A trimmed string from $_POST (arrays and missing keys give ''). */
function post_str(string $key): string
{
    $v = $_POST[$key] ?? '';
    return is_string($v) ? trim($v) : '';
}

/** A trimmed string from the query string. */
function query_str(string $key): string
{
    $v = $_GET[$key] ?? '';
    return is_string($v) ? trim($v) : '';
}

function client_ip(): string
{
    return (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
}

// ---------------------------------------------------------------- flash messages
/** Queue a message for the next page that is shown. $type: success | info | warning | error */
function flash(string $type, string $message): void
{
    $_SESSION['flash'][] = ['type' => $type, 'message' => $message];
}

/** @return array<int, array{type: string, message: string}> */
function take_flashes(): array
{
    $messages = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return is_array($messages) ? $messages : [];
}

// ---------------------------------------------------------------- CSRF protection
function csrf_token(): string
{
    if (empty($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

/** Hidden input to put in every <form method="post">. */
function csrf_field(): string
{
    return '<input type="hidden" name="csrf_token" value="' . e(csrf_token()) . '">';
}

/** Stop the request (403) unless the posted token matches the session's token. */
function verify_csrf(): void
{
    $sent = $_POST['csrf_token'] ?? '';
    if (!is_string($sent) || $sent === '' || !hash_equals(csrf_token(), $sent)) {
        render_error(403, 'Security check failed',
            'The form has expired or did not come from this site. Go back, reload the page and try again.');
    }
}

// ---------------------------------------------------------------- layout
/** Output the page header (HTML head, navigation, flash messages). */
function page_header(string $title, string $active = ''): void
{
    $user = current_user();
    $flashes = take_flashes();
    require APP_ROOT . '/app/views/header.php';
}

function page_footer(): void
{
    require APP_ROOT . '/app/views/footer.php';
}

/** Show an error page and stop. */
function render_error(int $status, string $title, string $message): void
{
    http_response_code($status);
    page_header($title);
    echo '<section class="card narrow"><h1>' . e($title) . '</h1><p>' . e($message) . '</p>'
        . '<p><a class="btn" href="' . e(url('/')) . '">Home</a></p></section>';
    page_footer();
    exit;
}

/** Field error text under an input (empty string when there is none). */
function field_error(array $errors, string $field): string
{
    return isset($errors[$field]) ? '<p class="field-error">' . e($errors[$field]) . '</p>' : '';
}

/** A local path that is safe to redirect to after login ('/x', never '//evil' or 'http://...'). */
function safe_local_path(?string $path): ?string
{
    if (!is_string($path) || $path === '' || $path[0] !== '/' || str_starts_with($path, '//')
        || str_contains($path, '\\') || preg_match('/[\r\n]/', $path)) {
        return null;
    }
    return $path;
}
?><p class="design-added">added</p>