<?php
require dirname(__DIR__) . '/lib.php';
header('Content-Type: application/json; charset=utf-8');
$rows = db()->query('SELECT id, name, price FROM products ORDER BY id')->fetchAll();
foreach ($rows as &$r) { $r['id'] = (int)$r['id']; $r['price'] = (float)$r['price']; }
echo json_encode($rows, JSON_UNESCAPED_UNICODE);
