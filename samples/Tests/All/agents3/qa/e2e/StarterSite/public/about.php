<?php
require dirname(__DIR__) . '/app/bootstrap.php';
page_header('About', 'about');
?>
<h1>About</h1>
<p><?= e(SITE_NAME) ?> was created with the RAD IDE App Gallery (PHP Starter Site).</p>
<p>Replace this text with information about you, your company or your project.</p>
<?php page_footer();
