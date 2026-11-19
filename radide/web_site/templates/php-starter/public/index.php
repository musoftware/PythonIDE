<?php
require dirname(__DIR__) . '/app/bootstrap.php';
page_header('Home', 'home');
?>
<section class="hero">
    <h1>Welcome to <?= e(SITE_NAME) ?></h1>
    <p>A starter PHP site: a shared layout (header and footer includes), several pages and a
       contact form with validation and CSRF protection.</p>
    <a class="button" href="/contact.php">Contact us</a>
</section>
<section class="columns">
    <article><h2>Layout includes</h2><p><code>app/views/header.php</code> and <code>footer.php</code>
        are shared by every page.</p></article>
    <article><h2>Pages</h2><p>Add a page: copy <code>public/about.php</code> and add it to the menu in
        <code>app/bootstrap.php</code>.</p></article>
    <article><h2>Contact form</h2><p>Messages are validated and saved to
        <code>data/messages.jsonl</code>, outside the web root.</p></article>
</section>
<?php page_footer();
