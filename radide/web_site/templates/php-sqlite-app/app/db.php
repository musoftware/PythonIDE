<?php
/* PDO connection to the database (SQLite by default, or MySQL / MariaDB - see
 * 'db_driver' in config.php) and the schema (migrations).
 * Every query in this app uses prepared statements with bound parameters -
 * never build SQL by concatenating user input. */
declare(strict_types=1);

/** 'sqlite' or 'mysql' */
function db_driver(): string
{
    return strtolower((string) config('db_driver', 'sqlite')) === 'mysql' ? 'mysql' : 'sqlite';
}

/** SQL expression for "now" (UTC, with milliseconds) in the current engine. */
function db_now(): string
{
    return db_driver() === 'mysql' ? 'UTC_TIMESTAMP(3)' : "strftime('%Y-%m-%d %H:%M:%f', 'now')";
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }
    if (db_driver() === 'mysql') {
        $c = (array) config('mysql', []);
        $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $c['host'] ?? '127.0.0.1',
                       (int) ($c['port'] ?? 3306), $c['dbname'] ?? '');
        $pdo = new PDO($dsn, (string) ($c['user'] ?? ''), (string) ($c['password'] ?? ''), [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            // emulated prepares: a named parameter may appear twice in one statement (still escaped by
            // PDO with the connection charset; PHP 8.1+ returns native ints)
            PDO::ATTR_EMULATE_PREPARES => true,
        ]);
        $pdo->exec("SET time_zone = '+00:00'");
        migrate_mysql($pdo);
        return $pdo;
    }
    $path = (string) config('db_path');
    $dir = dirname($path);
    if (!is_dir($dir)) {
        mkdir($dir, 0700, true);
    }
    $pdo = new PDO('sqlite:' . $path, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $pdo->exec('PRAGMA foreign_keys = ON');
    $pdo->exec('PRAGMA busy_timeout = 5000');
    migrate($pdo);
    return $pdo;
}

/** Create / upgrade the tables. PRAGMA user_version stores the schema version. */
function migrate(PDO $pdo): void
{
    $version = (int) $pdo->query('PRAGMA user_version')->fetchColumn();
    if ($version < 1) {
        $pdo->beginTransaction();
        $pdo->exec(<<<'SQL'
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            SQL);
        $pdo->exec(<<<'SQL'
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                sku         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
                quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                description TEXT NOT NULL DEFAULT '',
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
            )
            SQL);
        $pdo->exec('CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)');
        $pdo->exec(<<<'SQL'
            CREATE TABLE IF NOT EXISTS login_attempts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ip           TEXT NOT NULL,
                username     TEXT NOT NULL COLLATE NOCASE,
                attempted_at INTEGER NOT NULL
            )
            SQL);
        $pdo->exec('CREATE INDEX IF NOT EXISTS idx_attempts_time ON login_attempts(attempted_at)');
        $pdo->exec('PRAGMA user_version = 1');
        $pdo->commit();
    }
    // Future changes: if ($version < 2) { ALTER TABLE ...; PRAGMA user_version = 2; }
}

/** MySQL / MariaDB: the same tables (utf8mb4_unicode_ci = case-insensitive names and e-mails, like NOCASE). */
function migrate_mysql(PDO $pdo): void
{
    $opts = 'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci';
    $pdo->exec(<<<SQL
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(30) NOT NULL UNIQUE,
            email         VARCHAR(254) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ) $opts
        SQL);
    $pdo->exec(<<<SQL
        CREATE TABLE IF NOT EXISTS products (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            sku         VARCHAR(32) NOT NULL UNIQUE,
            price_cents INT NOT NULL CHECK (price_cents >= 0),
            quantity    INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            description TEXT NOT NULL,
            created_by  INT NULL,
            created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
            updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
            INDEX idx_products_name (name),
            CONSTRAINT fk_products_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        ) $opts
        SQL);
    $pdo->exec(<<<SQL
        CREATE TABLE IF NOT EXISTS login_attempts (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            ip           VARCHAR(45) NOT NULL,
            username     VARCHAR(255) NOT NULL,
            attempted_at BIGINT NOT NULL,
            INDEX idx_attempts_time (attempted_at)
        ) $opts
        SQL);
}
