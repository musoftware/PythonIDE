<?php
// {{APP_NAME}} - an empty PHP web site. Press F5 in RAD IDE to run it with php -S.
$title = '{{APP_NAME}}';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= htmlspecialchars($title) ?></title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <main>
        <h1><?= htmlspecialchars($title) ?></h1>
        <p>Hello from PHP <?= htmlspecialchars(PHP_VERSION) ?>. The time on the server is
           <strong><?= date('H:i:s') ?></strong>.</p>
        <p>Edit <code>index.php</code> and save: the preview reloads. <a href="about.php">About</a></p>
    </main>
</body>
</html>
