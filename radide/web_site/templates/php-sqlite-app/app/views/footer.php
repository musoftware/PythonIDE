<?php /* Page footer: included by page_footer(). */ ?>
</main>
<footer class="site-footer">
    <div class="container">
        &copy; <?= date('Y') ?> <?= e(config('app_name')) ?> &middot; PHP <?= e(PHP_VERSION) ?> + <?= db_driver() === 'mysql' ? 'MySQL' : 'SQLite' ?>
        &middot; made with RAD IDE
    </div>
</footer>
</body>
</html>
