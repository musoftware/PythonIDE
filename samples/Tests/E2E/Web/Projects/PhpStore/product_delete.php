<?php
require __DIR__ . '/lib.php';
require_login();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit('POST only'); }
csrf_check();
db()->prepare('DELETE FROM products WHERE id = ?')->execute([(int)($_POST['id'] ?? 0)]);
header('Location: /products.php');
