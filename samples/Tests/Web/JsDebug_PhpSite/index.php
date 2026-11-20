<?php
$a = 2;
$b = 3;
$title = "PHP + JavaScript debugging";
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title><?= htmlspecialchars($title) ?></title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1><?= htmlspecialchars($title) ?></h1>
  <p>Breakpoints in <code>index.php</code> stop the server (Xdebug); breakpoints in <code>app.js</code> stop the Preview.</p>
  <input id="a" value="<?= $a ?>"> + <input id="b" value="<?= $b ?>">
  <button id="add">Add</button>
  <p>Result: <span id="result">?</span></p>
  <script src="app.js"></script>
</body>
</html>
