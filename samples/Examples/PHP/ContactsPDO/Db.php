<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module Db - SQLite access for the Contacts (PDO) example. Every query is a prepared statement.
// Needs the pdo_sqlite extension (on in the PHP the IDE downloads / finds).

$GLOBALS['pdo'] = null;

function db_open(string $file): void
{
    $pdo = new PDO('sqlite:' . $file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec('CREATE TABLE IF NOT EXISTS contacts (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    name    TEXT NOT NULL,
                    phone   TEXT NOT NULL DEFAULT \'\',
                    city    TEXT NOT NULL DEFAULT \'\',
                    notes   TEXT NOT NULL DEFAULT \'\',
                    created TEXT NOT NULL DEFAULT (date(\'now\')))');
    $GLOBALS['pdo'] = $pdo;
}

function db_count(): int
{
    return (int)$GLOBALS['pdo']->query('SELECT COUNT(*) FROM contacts')->fetchColumn();
}

function db_get(int $id): ?array
{
    $st = $GLOBALS['pdo']->prepare('SELECT * FROM contacts WHERE id = ?');
    $st->execute([$id]);
    return $st->fetch() ?: null;
}

/** Contacts whose name, phone or city contains $text, by name. */
function db_find(string $text): array
{
    $like = '%' . trim($text) . '%';
    $st = $GLOBALS['pdo']->prepare('SELECT id, name, city FROM contacts
                                    WHERE name LIKE ? OR phone LIKE ? OR city LIKE ? ORDER BY name');
    $st->execute([$like, $like, $like]);
    return $st->fetchAll();
}

/** Insert ($id = 0) or update; returns the id. */
function db_save(int $id, array $c): int
{
    $pdo = $GLOBALS['pdo'];
    if ($id === 0) {
        $st = $pdo->prepare('INSERT INTO contacts (name, phone, city, notes) VALUES (?, ?, ?, ?)');
        $st->execute([$c['name'], $c['phone'], $c['city'], $c['notes']]);
        return (int)$pdo->lastInsertId();
    }
    $st = $pdo->prepare('UPDATE contacts SET name = ?, phone = ?, city = ?, notes = ? WHERE id = ?');
    $st->execute([$c['name'], $c['phone'], $c['city'], $c['notes'], $id]);
    return $id;
}

function db_delete(int $id): void
{
    $GLOBALS['pdo']->prepare('DELETE FROM contacts WHERE id = ?')->execute([$id]);
}
