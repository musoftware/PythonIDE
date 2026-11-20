<?php
/* Users: registration, login (password_hash / password_verify), logout,
 * login throttling and the "current user" of the session. */
declare(strict_types=1);

/** The logged-in user (id, username, email, created_at) or null. */
function current_user(): ?array
{
    static $cache = [];
    $id = $_SESSION['user_id'] ?? null;
    if (!is_int($id)) {
        return null;
    }
    if (!array_key_exists($id, $cache)) {
        $stmt = db()->prepare('SELECT id, username, email, created_at FROM users WHERE id = :id');
        $stmt->execute([':id' => $id]);
        $cache[$id] = $stmt->fetch() ?: null;
        if ($cache[$id] === null) {          // the account was deleted
            unset($_SESSION['user_id']);
        }
    }
    return $cache[$id];
}

/** Send visitors who are not logged in to the login page (and back here afterwards). */
function require_login(): array
{
    $user = current_user();
    if ($user === null) {
        if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
            $_SESSION['intended'] = (string) ($_SERVER['REQUEST_URI'] ?? '');
        }
        flash('info', 'Please log in to continue.');
        redirect('login.php');
    }
    return $user;
}

/** Start an authenticated session: new session id (prevents session fixation) and new CSRF token. */
function login_user(array $user): void
{
    session_regenerate_id(true);
    $_SESSION['user_id'] = (int) $user['id'];
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    $_SESSION['last_activity'] = time();
}

function logout_user(): void
{
    $_SESSION = [];
    session_regenerate_id(true);
}

/**
 * Check a user name (or e-mail) and password.
 * @return array|string the user row on success, otherwise an error message
 */
function attempt_login(string $login, string $password)
{
    $pdo = db();
    $max = (int) config('login_max_attempts', 5);
    $window = (int) config('login_window_seconds', 900);
    $since = time() - $window;
    $pdo->prepare('DELETE FROM login_attempts WHERE attempted_at < :t')->execute([':t' => $since]);

    $stmt = $pdo->prepare('SELECT COUNT(*) FROM login_attempts
                           WHERE attempted_at >= :t AND (ip = :ip OR username = :u)');
    $stmt->execute([':t' => $since, ':ip' => client_ip(), ':u' => $login]);
    if ((int) $stmt->fetchColumn() >= $max) {
        return 'Too many failed login attempts. Please wait ' . (int) ceil($window / 60) . ' minutes and try again.';
    }

    $stmt = $pdo->prepare('SELECT * FROM users WHERE username = :login OR email = :login LIMIT 1');
    $stmt->execute([':login' => $login]);
    $user = $stmt->fetch();

    // verify against a dummy hash when the user does not exist, so both cases take the same time
    $hash = $user['password_hash'] ?? '$2y$10$jkH4bhl7yDc2GiRkwwRPH.DQ79sjYUFQZvLDr9LKTlxLYakkPcDDi';
    if (!password_verify($password, $hash) || !$user) {
        $pdo->prepare('INSERT INTO login_attempts (ip, username, attempted_at) VALUES (:ip, :u, :t)')
            ->execute([':ip' => client_ip(), ':u' => $login, ':t' => time()]);
        return 'Invalid user name or password.';
    }

    if (password_needs_rehash($user['password_hash'], PASSWORD_DEFAULT)) {
        $pdo->prepare('UPDATE users SET password_hash = :h WHERE id = :id')
            ->execute([':h' => password_hash($password, PASSWORD_DEFAULT), ':id' => $user['id']]);
    }
    $pdo->prepare('DELETE FROM login_attempts WHERE username = :u OR ip = :ip')
        ->execute([':u' => $login, ':ip' => client_ip()]);
    return $user;
}

/**
 * Validate the registration form.
 * @return array<string, string> field => error message (empty = valid)
 */
function validate_registration(string $username, string $email, string $password, string $confirm): array
{
    $errors = [];
    if (!preg_match('/^[A-Za-z0-9_.-]{3,30}$/', $username)) {
        $errors['username'] = 'Use 3-30 letters, digits, dots, dashes or underscores.';
    }
    if (strlen($email) > 254 || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
        $errors['email'] = 'Enter a valid e-mail address.';
    }
    $errors += validate_new_password($password, $confirm);
    if (!$errors) {
        $stmt = db()->prepare('SELECT username = :u COLLATE NOCASE AS same_name FROM users
                               WHERE username = :u OR email = :e LIMIT 1');
        $stmt->execute([':u' => $username, ':e' => $email]);
        $row = $stmt->fetch();
        if ($row) {
            if ($row['same_name']) {
                $errors['username'] = 'This user name is already taken.';
            } else {
                $errors['email'] = 'An account with this e-mail already exists.';
            }
        }
    }
    return $errors;
}

/** @return array<string, string> */
function validate_new_password(string $password, string $confirm, string $field = 'password'): array
{
    $min = (int) config('password_min_length', 8);
    if (strlen($password) < $min) {
        return [$field => "The password must have at least $min characters."];
    }
    if (strlen($password) > 72) {
        return [$field => 'The password can have at most 72 characters.'];
    }
    if ($password !== $confirm) {
        return ['password_confirm' => 'The passwords do not match.'];
    }
    return [];
}

function register_user(string $username, string $email, string $password): array
{
    $stmt = db()->prepare('INSERT INTO users (username, email, password_hash) VALUES (:u, :e, :h)');
    $stmt->execute([':u' => $username, ':e' => $email, ':h' => password_hash($password, PASSWORD_DEFAULT)]);
    $id = (int) db()->lastInsertId();
    return ['id' => $id, 'username' => $username, 'email' => $email];
}

function change_password(int $userId, string $current, string $new): bool
{
    $stmt = db()->prepare('SELECT password_hash FROM users WHERE id = :id');
    $stmt->execute([':id' => $userId]);
    $hash = $stmt->fetchColumn();
    if (!is_string($hash) || !password_verify($current, $hash)) {
        return false;
    }
    db()->prepare('UPDATE users SET password_hash = :h WHERE id = :id')
        ->execute([':h' => password_hash($new, PASSWORD_DEFAULT), ':id' => $userId]);
    session_regenerate_id(true);
    return true;
}
