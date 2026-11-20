<?php
// A tiny PHP + SQLite page used to test RAD IDE's Docker generator (php:8.3-apache image).
$db = new PDO('sqlite:' . __DIR__ . '/data/visits.sqlite');
$db->exec('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY, at TEXT)');
$db->exec("INSERT INTO visits (at) VALUES (datetime('now'))");
$count = (int)$db->query('SELECT COUNT(*) FROM visits')->fetchColumn();
?>
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PHP in Docker</title></head>
<body>
<h1>Hello from PHP <?= htmlspecialchars(PHP_VERSION) ?></h1>
<p>This page was opened <?= $count ?> time(s).</p>
</body></html>
