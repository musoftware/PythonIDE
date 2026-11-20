<?php
/* Products: the CRUD module (search, validation, create, update, delete).
 * Copy this file (and public/products/) to add another module, e.g. Customers. */
declare(strict_types=1);

const PRODUCT_SORTS = [
    'name' => 'name COLLATE NOCASE ASC',
    'sku' => 'sku COLLATE NOCASE ASC',
    'price' => 'price_cents ASC',
    'price_desc' => 'price_cents DESC',
    'quantity' => 'quantity ASC',
    'updated' => 'updated_at DESC, id DESC',
];

function product_find(int $id): ?array
{
    $stmt = db()->prepare('SELECT * FROM products WHERE id = :id');
    $stmt->execute([':id' => $id]);
    return $stmt->fetch() ?: null;
}

/**
 * Search by name, SKU or description.
 * @return array{0: array<int, array>, 1: int} [rows of the page, total number of matches]
 */
function product_search(string $query, int $page, int $perPage, string $sort = 'updated'): array
{
    $where = '';
    $params = [];
    if ($query !== '') {
        // escape the LIKE wildcards so "%" or "_" typed by the user match literally
        $like = '%' . strtr($query, ['\\' => '\\\\', '%' => '\\%', '_' => '\\_']) . '%';
        $where = "WHERE name LIKE :q ESCAPE '\\' OR sku LIKE :q ESCAPE '\\' OR description LIKE :q ESCAPE '\\'";
        $params[':q'] = $like;
    }
    $order = PRODUCT_SORTS[$sort] ?? PRODUCT_SORTS['updated'];    // whitelist - never user text in ORDER BY

    $count = db()->prepare("SELECT COUNT(*) FROM products $where");
    $count->execute($params);
    $total = (int) $count->fetchColumn();

    $stmt = db()->prepare("SELECT * FROM products $where ORDER BY $order LIMIT :limit OFFSET :offset");
    foreach ($params as $k => $v) {
        $stmt->bindValue($k, $v);
    }
    $stmt->bindValue(':limit', $perPage, PDO::PARAM_INT);
    $stmt->bindValue(':offset', max(0, ($page - 1) * $perPage), PDO::PARAM_INT);
    $stmt->execute();
    return [$stmt->fetchAll(), $total];
}

/**
 * Validate the product form.
 * @param array $input raw form values (name, sku, price, quantity, description)
 * @return array{0: array, 1: array<string, string>} [clean data for the database, errors]
 */
function product_validate(array $input, ?int $id = null): array
{
    $errors = [];
    $name = trim((string) ($input['name'] ?? ''));
    $sku = strtoupper(trim((string) ($input['sku'] ?? '')));
    $price = str_replace(',', '.', trim((string) ($input['price'] ?? '')));
    $quantity = trim((string) ($input['quantity'] ?? ''));
    $description = trim((string) ($input['description'] ?? ''));

    if ($name === '') {
        $errors['name'] = 'The name is required.';
    } elseif (mb_strlen($name) > 100) {
        $errors['name'] = 'The name can have at most 100 characters.';
    }
    if (!preg_match('/^[A-Z0-9][A-Z0-9-]{1,31}$/', $sku)) {
        $errors['sku'] = 'Use 2-32 letters, digits or dashes (e.g. ABC-100).';
    } else {
        $stmt = db()->prepare('SELECT id FROM products WHERE sku = :sku AND id != :id');
        $stmt->execute([':sku' => $sku, ':id' => $id ?? 0]);
        if ($stmt->fetchColumn() !== false) {
            $errors['sku'] = 'Another product already uses this SKU.';
        }
    }
    if (!preg_match('/^\d{1,9}(\.\d{1,2})?$/', $price)) {
        $errors['price'] = 'Enter a price such as 12 or 12.50.';
    }
    if (!preg_match('/^\d{1,9}$/', $quantity)) {
        $errors['quantity'] = 'Enter a whole number, 0 or more.';
    }
    if (mb_strlen($description) > 1000) {
        $errors['description'] = 'The description can have at most 1000 characters.';
    }

    $cents = 0;
    if (!isset($errors['price'])) {
        [$whole, $fraction] = array_pad(explode('.', $price, 2), 2, '');
        $cents = (int) $whole * 100 + (int) str_pad($fraction, 2, '0');
    }
    $data = [
        'name' => $name,
        'sku' => $sku,
        'price_cents' => $cents,
        'quantity' => (int) $quantity,
        'description' => $description,
    ];
    return [$data, $errors];
}

function product_create(array $data, int $userId): int
{
    $stmt = db()->prepare('INSERT INTO products (name, sku, price_cents, quantity, description, created_by)
                           VALUES (:name, :sku, :price, :qty, :descr, :user)');
    $stmt->execute([
        ':name' => $data['name'], ':sku' => $data['sku'], ':price' => $data['price_cents'],
        ':qty' => $data['quantity'], ':descr' => $data['description'], ':user' => $userId,
    ]);
    return (int) db()->lastInsertId();
}

function product_update(int $id, array $data): void
{
    $stmt = db()->prepare("UPDATE products SET name = :name, sku = :sku, price_cents = :price, quantity = :qty,
                           description = :descr, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = :id");
    $stmt->execute([
        ':name' => $data['name'], ':sku' => $data['sku'], ':price' => $data['price_cents'],
        ':qty' => $data['quantity'], ':descr' => $data['description'], ':id' => $id,
    ]);
}

function product_delete(int $id): bool
{
    $stmt = db()->prepare('DELETE FROM products WHERE id = :id');
    $stmt->execute([':id' => $id]);
    return $stmt->rowCount() > 0;
}

/** Form values of a product row (for the edit form). */
function product_form_values(array $row): array
{
    return [
        'name' => $row['name'],
        'sku' => $row['sku'],
        'price' => number_format($row['price_cents'] / 100, 2, '.', ''),
        'quantity' => (string) $row['quantity'],
        'description' => $row['description'],
    ];
}

/** '2026-01-31 14:05:09.123' (UTC, stored) -> '2026-01-31 14:05' */
function format_time(?string $stamp): string
{
    return substr((string) $stamp, 0, 16);
}

function format_price(int $cents): string
{
    return number_format($cents / 100, 2);
}

function product_stats(): array
{
    $row = db()->query('SELECT COUNT(*) AS products, COALESCE(SUM(quantity), 0) AS units,
                               COALESCE(SUM(price_cents * quantity), 0) AS value_cents,
                               COALESCE(SUM(quantity = 0), 0) AS out_of_stock FROM products')->fetch();
    return array_map('intval', $row);
}
