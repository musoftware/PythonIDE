<?php
session_start();
$title = 'Products';
$rows = [['a' => 'Pen'], ['a' => 'Book']];
$opts = ['x', 'y'];
$user = $_SESSION['user'] ?? 'guest'; // who ?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title><?= htmlspecialchars($title) ?></title>
  <style>
    body {
      font-family: sans-serif;
    }
    .card:hover {
      color: red;
    }
    .title {
      letter-spacing: 2px;
    }
    @media (max-width: 600px) {
      .card {
        padding: 2px;
      }
    }
  </style>
  <script>var who = "<?= $user ?>";</script>
</head>
<body class="home">
  <?php if (!empty($_SESSION['flash'])): ?><div class="flash"><?= $_SESSION['flash'] ?></div><?php endif; ?>
  <h1 class="title <?= $user === 'guest' ? 'muted' : '' ?>">Hello <?= htmlspecialchars($user) ?>!</h1>
  <a href="item.php?id=<?= 3 ?>" <?php if (true) echo 'target="_blank"'; ?>>Item</a>
  <div class="card" style="color: <?= 'blue' ?>">Card text</div>
  <table class="grid">
    <?php foreach ($rows as $r): ?>
    <tr><td><?= $r['a'] ?></td><td>x</td></tr>
    <?php endforeach; ?>
  </table>
  <select name="s"><?php foreach ($opts as $o): ?><option><?= $o ?></option><?php endforeach ?></select>
  <form method="post" action="login.php">
    <input type="hidden" name="csrf" value="<?= $_SESSION['csrf'] ?? '' ?>">
    <input name="email" type="email" placeholder="Email">
    <button type="submit">Sign in</button>
  </form>
  <script>
    document.querySelector('h1').addEventListener('click', () => console.log(1 < 2));
  </script>
</body>
</html>
