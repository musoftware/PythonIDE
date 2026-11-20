<?php
/* PDO connection to the SQLite database and the schema (migrations).
 * Every query in this app uses prepared statements with bound parameters -
 * never build SQL by concatenating user input. */
declare(strict_types=1);

function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
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
