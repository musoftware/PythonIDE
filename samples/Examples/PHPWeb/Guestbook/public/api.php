<?php
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// GET /api.php  ->  {"total": n, "messages": [{id, name, message, created}, ...]}  (newest 50)
// Try it with the IDE's REST client (Site > REST Client) or open it in the preview.

require __DIR__ . '/../app/bootstrap.php';

header('Content-Type: application/json; charset=utf-8');
$rows = db()->query('SELECT id, name, message, created FROM messages ORDER BY id DESC LIMIT 50')->fetchAll();
echo json_encode(['total' => (int)db()->query('SELECT COUNT(*) FROM messages')->fetchColumn(), 'messages' => $rows],
                 JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
